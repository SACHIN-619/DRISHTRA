"""
DRISHTRA Model Sentinel API Endpoints
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import ModelAsset, Finding
from app.schemas.all_schemas import ModelRegister, ModelResponse, FindingResponse, AssurancePassportResponse
from app.services.model_service import ModelService
from app.services.passport_service import PassportService

router = APIRouter(prefix="/api/v1/models", tags=["Model Sentinel"])

@router.post("/register", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
def register_model(model_in: ModelRegister, db: Session = Depends(get_db)):
    return ModelService.register_model(db, model_in)

@router.get("/{model_id}", response_model=ModelResponse)
def get_model(model_id: str, db: Session = Depends(get_db)):
    model = db.query(ModelAsset).filter(ModelAsset.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return model

@router.post("/{model_id}/scan", response_model=List[FindingResponse])
def scan_model(model_id: str, scan_payload: Optional[Dict[str, Any]] = None, db: Session = Depends(get_db)):
    current_digest = scan_payload.get("current_weight_sha256") if scan_payload else None
    probes = scan_payload.get("probe_responses") if scan_payload else None
    
    model = db.query(ModelAsset).filter(ModelAsset.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    if not current_digest:
        current_digest = model.weight_sha256

    try:
        findings = ModelService.scan_model(
            db=db,
            model_id=model_id,
            current_weight_sha256=current_digest,
            probe_responses=probes
        )
        return findings
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{model_id}/findings", response_model=List[FindingResponse])
def get_model_findings(model_id: str, db: Session = Depends(get_db)):
    return db.query(Finding).filter(Finding.asset_id == model_id).all()

@router.get("/{model_id}/passport", response_model=AssurancePassportResponse)
def get_model_passport(model_id: str, db: Session = Depends(get_db)):
    passport = PassportService.get_model_passport(db, model_id)
    if not passport:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return passport

@router.post("/inspect-onnx")
def inspect_onnx_model_endpoint(payload: Dict[str, Any]):
    """Inspects ONNX model graph structure, opset, inputs, outputs, and parameters."""
    from app.ingestion.model_inspectors import ModelInspector
    name = payload.get("model_name", "Tactical_YOLO_ONNX")
    file_path = payload.get("file_path", None)
    return ModelInspector.inspect_onnx_model(file_path or name, model_name=name)

@router.post("/inspect-pytorch")
def inspect_pytorch_model_endpoint(payload: Dict[str, Any]):
    """Inspects PyTorch state_dict, parameters, and weight precision."""
    from app.ingestion.model_inspectors import ModelInspector
    name = payload.get("model_name", "Tactical_PyTorch_Model")
    file_path = payload.get("file_path", None)
    return ModelInspector.inspect_pytorch_model(file_path or name, model_name=name)

