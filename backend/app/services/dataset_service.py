"""
DRISHTRA Dataset Sentinel Service
Dataset Ingestion, Manifest Fingerprinting, Integrity Scanning, and Evidence Harvesting.
"""
import uuid
import json
import hashlib
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import Dataset, DatasetVersion, Finding, Evidence, EvidenceEdge, utc_now_iso
from app.schemas.all_schemas import DatasetRegister
from app.crypto.hashing import sha256_canonical_dict
from app.detectors.duplicate_detector import ExactDuplicateDetector, NearDuplicateDetector
from app.detectors.label_anomaly_detector import LabelAnomalyDetector
from app.detectors.class_imbalance_detector import ClassImbalanceDetector
from app.detectors.malformed_annotation_detector import MalformedAnnotationDetector
from app.detectors.distribution_shift_detector import DistributionShiftDetector
from app.detectors.ood_detector import OutOfDistributionDetector
from app.services.audit_service import AuditService
from app.services.evidence_writer import record_check

class DatasetService:
    @staticmethod
    def register_dataset(db: Session, data_in: DatasetRegister, actor: str = "analyst") -> Dataset:
        dataset_id = f"D-{uuid.uuid4().hex[:6].upper()}"
        
        # Compute deterministic manifest digest
        manifest = {
            "name": data_in.name,
            "format": data_in.format,
            "version": data_in.version,
            "sample_count": data_in.sample_count,
            "contributor_id": data_in.contributor_id,
            "metadata": data_in.metadata or {}
        }
        manifest_digest = sha256_canonical_dict(manifest)
        
        # Synthetic / mock file hash if location not physical
        file_digest = hashlib.sha256(f"{dataset_id}:{manifest_digest}".encode('utf-8')).hexdigest()

        dataset = Dataset(
            dataset_id=dataset_id,
            case_id=data_in.case_id,
            contributor_id=data_in.contributor_id,
            name=data_in.name,
            format=data_in.format,
            version=data_in.version,
            location=data_in.location,
            sha256=file_digest,
            manifest_hash=manifest_digest,
            sample_count=data_in.sample_count,
            metadata_json=json.dumps(data_in.metadata or {}),
            created_at=utc_now_iso()
        )
        db.add(dataset)
        
        # Record initial version
        v_id = f"DV-{uuid.uuid4().hex[:6].upper()}"
        version_rec = DatasetVersion(
            dataset_version_id=v_id,
            dataset_id=dataset_id,
            version=data_in.version,
            sha256=file_digest,
            manifest_hash=manifest_digest,
            created_at=utc_now_iso()
        )
        db.add(version_rec)

        # Record edge: Contributor -> Dataset
        edge_id = f"EDGE-{uuid.uuid4().hex[:8].upper()}"
        edge = EvidenceEdge(
            edge_id=edge_id,
            case_id=data_in.case_id,
            source_node=f"contributor:{data_in.contributor_id}",
            target_node=f"dataset:{dataset_id}",
            relationship="contributed_by",
            epistemic_status="OBSERVED",
            evidence_ids_json="[]"
        )
        db.add(edge)
        db.commit()
        db.refresh(dataset)

        AuditService.record_event(
            db=db,
            case_id=data_in.case_id,
            actor=actor,
            action="DATASET_REGISTERED",
            asset_id=dataset_id,
            result="SUCCESS",
            reason=f"Registered dataset '{dataset.name}' (Manifest: {manifest_digest[:16]}...)"
        )
        return dataset

    @staticmethod
    def scan_dataset(
        db: Session,
        dataset_id: str,
        samples: List[Dict[str, Any]],
        actor: str = "analyst",
        embeddings: Optional[List[List[float]]] = None,
        reference_profile: Optional[Dict[str, Any]] = None,
        operational_metrics: Optional[Dict[str, float]] = None,
        operational_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        """
        Runs the full dataset battery (D1-D7) against canonical sample records.
        Each detector produces a CheckExecution; checks whose inputs are missing
        are recorded as NOT_TESTED rather than silently skipped.
        """
        dataset = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        input_digest = sha256_canonical_dict({"samples": [
            {k: v for k, v in s.items() if k not in ("ground_truth",)} for s in samples
        ]})
        # Ground-truth isolation: detectors never see injected labels of the attack lab.
        detector_view = [{k: v for k, v in s.items() if k not in ("ground_truth", "mutation_type")} for s in samples]

        ref = reference_profile or {}
        battery = [
            ("D1_EXACT_DUPLICATE", lambda: ExactDuplicateDetector().run(samples=detector_view)),
            ("D2_NEAR_DUPLICATE", lambda: NearDuplicateDetector().run(samples=detector_view)),
            ("D3_LABEL_CONSISTENCY", lambda: LabelAnomalyDetector().run(samples=detector_view)),
            ("D4_CLASS_BALANCE", lambda: ClassImbalanceDetector().run(samples=detector_view)),
            ("D6_ANNOTATION_VALIDITY", lambda: MalformedAnnotationDetector().run(samples=detector_view)),
            ("D5_DISTRIBUTION_SHIFT", lambda: DistributionShiftDetector().run(
                current_metrics=operational_metrics or {}, reference_profile=ref.get("metrics"),
                metadata=operational_metadata)),
            ("D7_OUT_OF_DISTRIBUTION", lambda: OutOfDistributionDetector().run(
                embeddings=embeddings, reference_mean=ref.get("embedding_mean"), reference_std=ref.get("embedding_std"))),
        ]

        created: List[Finding] = []
        outcomes = {}
        for check_id, run in battery:
            try:
                result = run()
            except Exception as exc:  # a broken detector must not look like a pass
                from app.detectors.base import DetectorResult, DetectorStatus
                result = DetectorResult(
                    detector_id=check_id.lower(), detector_version="1.0.0",
                    status=DetectorStatus.ERROR, limitations=[f"Detector error: {exc}"],
                )
            created += record_check(
                db, dataset.case_id, "DATASET", dataset_id, check_id, result,
                actor=actor, input_digest=input_digest,
            )
            outcomes[check_id] = result.status.value if hasattr(result.status, "value") else str(result.status)

        AuditService.record_event(
            db=db,
            case_id=dataset.case_id,
            actor=actor,
            action="DATASET_SCANNED",
            asset_id=dataset_id,
            result="COMPLETED",
            reason=json.dumps({"samples": len(samples), "input_digest": input_digest,
                               "findings": len(created), "checks": outcomes}, sort_keys=True),
        )
        return created

