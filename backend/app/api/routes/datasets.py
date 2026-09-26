"""
DRISHTRA Dataset Sentinel API Endpoints
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Dataset, Finding
from app.schemas.all_schemas import DatasetRegister, DatasetResponse, FindingResponse, AssurancePassportResponse
from app.services.dataset_service import DatasetService
from app.services.passport_service import PassportService

router = APIRouter(prefix="/api/v1/datasets", tags=["Dataset Sentinel"])

@router.post("/register", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def register_dataset(data_in: DatasetRegister, db: Session = Depends(get_db)):
    return DatasetService.register_dataset(db, data_in)

@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return dataset

@router.post("/{dataset_id}/scan", response_model=List[FindingResponse])
def scan_dataset(dataset_id: str, sample_payload: Optional[Dict[str, Any]] = None, db: Session = Depends(get_db)):
    samples = sample_payload.get("samples", []) if sample_payload else []
    try:
        findings = DatasetService.scan_dataset(db, dataset_id, samples=samples)
        return findings
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{dataset_id}/findings", response_model=List[FindingResponse])
def get_dataset_findings(dataset_id: str, db: Session = Depends(get_db)):
    return db.query(Finding).filter(Finding.asset_id == dataset_id).all()

@router.get("/{dataset_id}/passport", response_model=AssurancePassportResponse)
def get_dataset_passport(dataset_id: str, db: Session = Depends(get_db)):
    passport = PassportService.get_dataset_passport(db, dataset_id)
    if not passport:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return passport

@router.post("/parse-coco")
def parse_coco_dataset(payload: Dict[str, Any]):
    """Parses raw COCO JSON format into standardized DRISHTRA dataset manifest."""
    from app.ingestion.dataset_parsers import DatasetParser
    name = payload.get("dataset_name", "COCO_Recon_Dataset")
    coco_data = payload.get("coco_data", payload)
    return DatasetParser.parse_coco(coco_data, dataset_name=name)

@router.post("/parse-yolo")
def parse_yolo_dataset(payload: Dict[str, Any]):
    """Parses raw YOLO format annotations into standardized DRISHTRA dataset manifest."""
    from app.ingestion.dataset_parsers import DatasetParser
    name = payload.get("dataset_name", "YOLO_Recon_Dataset")
    annotations = payload.get("annotations", [])
    classes = payload.get("classes", None)
    return DatasetParser.parse_yolo(annotations, class_names=classes, dataset_name=name)

