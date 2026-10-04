"""
Trust-boundary ingestion: untrusted files -> vault -> canonical records.

Nothing is trusted on arrival. Each upload is size/extension/traversal checked
(FileVault), hashed, parsed through a format adapter into canonical records,
and only then registered. The canonical records are stored in the assessment
input store so the pipeline scans exactly what was ingested.

Supported:
  COCO   .json  (images / annotations / categories)
  COCO   .zip / .tar containing a COCO .json (+ optional images)
  YOLO   .zip / .tar containing labels/*.txt (+ optional images, classes.txt or data.yaml)

When the archive carries the images themselves, the real image SHA-256 and a
64-bit dHash are computed, so exact- and near-duplicate checks run on pixels.
Annotation-only uploads leave perceptual hashing NOT_TESTED rather than faking it.
"""
import io
import json
import os
import shutil
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from sqlalchemy.orm import Session

from app.crypto.crypto_service import CryptoService
from app.db.models import Case, Contributor
from app.ingestion.dataset_parsers import DatasetParser, compute_dhash_64
from app.ingestion.file_vault import FileVault, SecurityValidationError
from app.schemas.all_schemas import DatasetRegister
from app.services.artifact_store import ArtifactStore
from app.services.audit_service import AuditService
from app.services.dataset_service import DatasetService

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _record_from_canonical(rec, image_index: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    anns = [{"class_id": a.class_id, "class_name": a.class_name, "bbox": a.bbox} for a in rec.annotations]
    label = anns[0]["class_name"] if anns else None
    out = {
        "sample_id": rec.image_id,
        "file_name": rec.file_name,
        "width": rec.width,
        "height": rec.height,
        "label": label or "UNLABELLED",
        "annotations": anns,
        "class_ids": rec.class_ids,
        "sha256": rec.file_hash,          # annotation fingerprint unless the image is present
        "hash_basis": "annotation_fingerprint",
    }
    img = image_index.get(os.path.basename(rec.file_name))
    if img:
        out["sha256"] = img["sha256"]
        out["phash"] = img["dhash"]
        out["hash_basis"] = "image_bytes"
    return out


def _index_images(paths: List[str]) -> Dict[str, Dict[str, str]]:
    idx = {}
    for p in paths:
        if os.path.splitext(p)[1].lower() not in IMAGE_EXT:
            continue
        try:
            with open(p, "rb") as fh:
                data = fh.read()
            with Image.open(io.BytesIO(data)) as im:
                idx[os.path.basename(p)] = {"sha256": CryptoService.hash(data), "dhash": compute_dhash_64(im)}
        except Exception:
            continue  # unreadable image: leave it to the annotation-validity check
    return idx


def _yolo_classes(paths: List[str]) -> Optional[List[str]]:
    for p in paths:
        name = os.path.basename(p).lower()
        if name in ("classes.txt", "obj.names"):
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                return [l.strip() for l in fh if l.strip()]
        if name in ("data.yaml", "dataset.yaml"):
            try:
                import yaml  # optional
                with open(p, "r", encoding="utf-8") as fh:
                    names = (yaml.safe_load(fh) or {}).get("names")
                return list(names.values()) if isinstance(names, dict) else names
            except Exception:
                return None
    return None


def parse_dataset_file(path: str, fmt: str, dataset_id: str, contributor_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    fmt = fmt.upper()
    ext = os.path.splitext(path)[1].lower()
    meta: Dict[str, Any] = {"source_file": os.path.basename(path)}
    if ext == ".json":
        if fmt != "COCO":
            raise ValueError("A single .json upload is treated as COCO. Upload YOLO as a .zip with labels/*.txt.")
        canon = DatasetParser.parse_coco_json(path, dataset_id=dataset_id, contributor_id=contributor_id)
        recs = [_record_from_canonical(c, {}) for c in canon]
        meta.update({"images_included": 0})
        return recs, meta

    if ext not in (".zip", ".tar", ".gz", ".tgz"):
        raise ValueError(f"Unsupported dataset upload type '{ext}'. Use COCO .json, or a .zip/.tar archive.")

    work = FileVault.create_safe_temp_dir("ingest_")
    try:
        files = FileVault.safe_extract_archive(path, work)
        images = _index_images(files)
        meta["images_included"] = len(images)
        if fmt == "COCO":
            js = [p for p in files if p.lower().endswith(".json")]
            coco = None
            for p in js:
                with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                    try:
                        d = json.load(fh)
                    except Exception:
                        continue
                if isinstance(d, dict) and "images" in d:
                    coco = d
                    break
            if coco is None:
                raise ValueError("No COCO annotation file (JSON with 'images') found in archive.")
            canon = DatasetParser.normalize_coco(coco, dataset_id=dataset_id, contributor_id=contributor_id)
        else:
            labels = [p for p in files if p.lower().endswith(".txt") and os.path.basename(p).lower() not in ("classes.txt",)]
            if not labels:
                raise ValueError("No YOLO label files (*.txt) found in archive.")
            classes = _yolo_classes(files)
            annos = []
            for lp in sorted(labels):
                base = os.path.splitext(os.path.basename(lp))[0]
                img_name = next((n for n in images if os.path.splitext(n)[0] == base), f"{base}.jpg")
                with open(lp, "r", encoding="utf-8", errors="ignore") as fh:
                    lines = [l.strip() for l in fh if l.strip()]
                annos.append({"file_name": img_name, "lines": lines, "width": 640, "height": 640})
            canon = DatasetParser.normalize_yolo(annos, class_names=classes, dataset_id=dataset_id, contributor_id=contributor_id)
            meta["classes"] = classes
        recs = [_record_from_canonical(c, images) for c in canon]
        return recs, meta
    finally:
        shutil.rmtree(work, ignore_errors=True)


class IngestionService:
    @staticmethod
    def ingest_dataset(
        db: Session, case_id: str, contributor_id: str, name: str, fmt: str,
        filename: str, content: bytes, actor: str, version: str = "1.0.0",
    ) -> Dict[str, Any]:
        if not db.query(Case).filter(Case.case_id == case_id).first():
            raise LookupError(f"Case {case_id} not found")
        if not db.query(Contributor).filter(Contributor.contributor_id == contributor_id,
                                            Contributor.case_id == case_id).first():
            raise LookupError(f"Contributor {contributor_id} is not registered on case {case_id}")
        saved_path, file_sha, size = FileVault.save_uploaded_stream(content, filename)
        records, meta = parse_dataset_file(saved_path, fmt, "PENDING", contributor_id)
        if not records:
            raise ValueError("The upload parsed to zero samples.")
        ds = DatasetService.register_dataset(db, DatasetRegister(
            case_id=case_id, contributor_id=contributor_id, name=name, format=fmt.upper(), version=version,
            location=saved_path, sample_count=len(records), evidence_label="UPLOADED",
            metadata={"upload_sha256": file_sha, "size_bytes": size, **meta},
        ), actor=actor)
        for r in records:
            r["dataset_id"] = ds.dataset_id
        rec_digest = ArtifactStore.save_dataset_records(ds.dataset_id, records)
        ds.sha256 = file_sha
        db.commit()
        AuditService.record_event(
            db=db, case_id=case_id, actor=actor, action="DATASET_INGESTED", asset_id=ds.dataset_id,
            result="SUCCESS",
            reason=json.dumps({"file_sha256": file_sha, "records": len(records), "records_digest": rec_digest,
                               "images_included": meta.get("images_included", 0)}, sort_keys=True),
        )
        return {
            "dataset_id": ds.dataset_id, "name": ds.name, "format": ds.format, "sha256": file_sha,
            "size_bytes": size, "records": len(records), "records_digest": rec_digest,
            "images_included": meta.get("images_included", 0),
            "perceptual_hashing": "available" if meta.get("images_included") else "not available (no images in upload)",
            "status": "INGESTED",
        }
