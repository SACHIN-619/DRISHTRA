"""
DRISHTRA Inference Attestor API Endpoints
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import InferenceRecord
from app.schemas.all_schemas import InferenceRegister, InferenceResponse
from app.services.inference_service import InferenceService

router = APIRouter(prefix="/api/v1/inference", tags=["Inference Attestor"])

@router.post("/register", response_model=InferenceResponse, status_code=status.HTTP_201_CREATED)
def register_inference(inf_in: InferenceRegister, db: Session = Depends(get_db)):
    return InferenceService.register_inference(db, inf_in)

@router.post("/{inference_id}/verify")
def verify_inference(inference_id: str, payload: Dict[str, str], db: Session = Depends(get_db)):
    public_key_hex = payload.get("public_key_hex")
    if not public_key_hex:
        raise HTTPException(status_code=400, detail="Missing 'public_key_hex' in request body")
    try:
        return InferenceService.verify_inference(db, inference_id, public_key_hex)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/case/{case_id}", response_model=List[InferenceResponse])
def list_case_inferences(case_id: str, db: Session = Depends(get_db)):
    return db.query(InferenceRecord).filter(InferenceRecord.case_id == case_id).order_by(InferenceRecord.sequence.asc()).all()
