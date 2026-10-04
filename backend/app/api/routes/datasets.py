"""
DRISHTRA Dataset Sentinel API Endpoints
Provides:
- Dataset Registration & FileVault Upload
- Chunk-Oriented Streaming Ingestion
- Ingestion Parsers (COCO, YOLO)
- Dataset Integrity Scanning (D1 - D6)
- Dataset Assurance Passport Retrieval
"""
import os
import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Dataset, DatasetChunk, Finding, Case
from app.schemas.all_schemas import (
    DatasetRegister, DatasetResponse, DatasetChunkCreate, DatasetChunkResponse,
    FindingResponse, AssurancePassportResponse, CanonicalImageRecord
)
from app.services.dataset_service import DatasetService
from app.services.passport_service import PassportService
from app.ingestion.file_vault import FileVault, SecurityValidationError
from app.ingestion.dataset_parsers import DatasetParser
from app.crypto.crypto_service import CryptoService

from app.core.security import require_permission, TokenData
from app.core.rbac import Permission

router = APIRouter(prefix="/api/v1/datasets", tags=["Dataset Sentinel"], dependencies=[Depends(require_permission(Permission.ASSET_READ))])

@router.post("/register", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def register_dataset(data_in: DatasetRegister, db: Session = Depends(get_db), user: TokenData = Depends(require_permission(Permission.DATASET_INGEST))):
    return DatasetService.register_dataset(db, data_in, actor=user.username)

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_dataset_artifact(
    case_id: str = Form(...),
    contributor_id: str = Form(...),
    dataset_name: str = Form(...),
    format_type: str = Form("COCO"),
    version: str = Form("1.0.0"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.DATASET_INGEST))
):
    """
    Trust-boundary ingestion of an untrusted dataset (COCO .json, or .zip/.tar with
    COCO or YOLO labels and optional images). Validated, hashed, parsed to canonical
    records and stored for the pipeline. Nothing is scanned until a run is started.
    """
    from app.services.ingestion_service import IngestionService
    content = await file.read()
    try:
        return IngestionService.ingest_dataset(
            db, case_id, contributor_id, dataset_name, format_type, file.filename or "dataset.json",
            content, actor=user.username, version=version)
    except SecurityValidationError as se:
        raise HTTPException(status_code=400, detail=str(se))
    except LookupError as le:
        raise HTTPException(status_code=404, detail=str(le))
    except (ValueError, json.JSONDecodeError) as ve:
        raise HTTPException(status_code=400, detail=f"Could not parse dataset: {ve}")

@router.post("/{dataset_id}/chunks", response_model=DatasetChunkResponse, status_code=status.HTTP_201_CREATED)
def ingest_dataset_chunk(
    dataset_id: str,
    chunk_in: DatasetChunkCreate,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.DATASET_INGEST))
):
    """
    Ingests a bounded chunk of records for large dataset streaming (Requirement 5).
    Computes chunk digest and maintains chunk manifests.
    """
    dataset = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")

    import uuid
    chunk_id = f"CHK-{uuid.uuid4().hex[:8].upper()}"
    chunk_sha = CryptoService.hash(chunk_in.records)
    first_id = chunk_in.records[0].get("id") or chunk_in.records[0].get("sample_id") if chunk_in.records else None
    last_id = chunk_in.records[-1].get("id") or chunk_in.records[-1].get("sample_id") if chunk_in.records else None

    chunk_rec = DatasetChunk(
        chunk_id=chunk_id,
        dataset_id=dataset_id,
        case_id=dataset.case_id,
        chunk_index=chunk_in.chunk_index,
        record_count=len(chunk_in.records),
        first_record_id=str(first_id) if first_id else None,
        last_record_id=str(last_id) if last_id else None,
        sha256=chunk_sha,
        schema_version="1.0.0"
    )
    db.add(chunk_rec)
    dataset.sample_count += len(chunk_in.records)
    db.commit()
    db.refresh(chunk_rec)

    return chunk_rec

@router.get("")
def list_datasets(case_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Dataset)
    if case_id:
        q = q.filter(Dataset.case_id == case_id)
    return [DatasetResponse.model_validate(d) for d in q.order_by(Dataset.created_at.desc()).all()]


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return dataset

@router.get("/{dataset_id}/chunks", response_model=List[DatasetChunkResponse])
def list_dataset_chunks(dataset_id: str, db: Session = Depends(get_db)):
    return db.query(DatasetChunk).filter(DatasetChunk.dataset_id == dataset_id).order_by(DatasetChunk.chunk_index.asc()).all()

@router.post("/{dataset_id}/scan", response_model=List[FindingResponse])
def scan_dataset(
    dataset_id: str,
    sample_payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.PIPELINE_RUN))
):
    samples = sample_payload.get("samples", []) if sample_payload else []
    try:
        findings = DatasetService.scan_dataset(db, dataset_id, samples=samples, actor=user.username)
        return findings
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{dataset_id}/findings", response_model=List[FindingResponse])
def get_dataset_findings(dataset_id: str, db: Session = Depends(get_db), user: TokenData = Depends(require_permission(Permission.EVIDENCE_READ))):
    return db.query(Finding).filter(Finding.asset_id == dataset_id).all()

@router.get("/{dataset_id}/passport")
def get_dataset_passport(dataset_id: str, db: Session = Depends(get_db), user: TokenData = Depends(require_permission(Permission.EVIDENCE_READ))):
    passport = PassportService.get_dataset_passport(db, dataset_id)
    if not passport:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return passport

@router.post("/parse-coco")
def parse_coco_dataset(payload: Dict[str, Any], user: TokenData = Depends(require_permission(Permission.DATASET_INGEST))):
    """Normalizes raw COCO JSON format into CanonicalImageRecord structure."""
    name = payload.get("dataset_name", "COCO_Recon_Dataset")
    coco_data = payload.get("coco_data", payload)
    canonical = DatasetParser.normalize_coco(coco_data, dataset_id="D-COCO-NORMALIZED")
    return {
        "dataset_name": name,
        "format": "COCO",
        "sample_count": len(canonical),
        "samples": [c.model_dump() for c in canonical]
    }

@router.post("/parse-yolo")
def parse_yolo_dataset(payload: Dict[str, Any], user: TokenData = Depends(require_permission(Permission.DATASET_INGEST))):
    """Normalizes raw YOLO format annotations into CanonicalImageRecord structure."""
    name = payload.get("dataset_name", "YOLO_Recon_Dataset")
    annotations = payload.get("annotations", [])
    classes = payload.get("classes", None)
    canonical = DatasetParser.normalize_yolo(annotations, class_names=classes, dataset_id="D-YOLO-NORMALIZED")
    return {
        "dataset_name": name,
        "format": "YOLO",
        "sample_count": len(canonical),
        "samples": [c.model_dump() for c in canonical]
    }
