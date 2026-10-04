"""
DRISHTRA Normalized Evidence & Findings API Endpoints
Provides standardized cross-lifecycle evidence retrieval:
- CONTRIBUTOR, DATASET, MODEL, RUNTIME, INFERENCE, CRYPTO, SYSTEM
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Finding, Evidence
from app.schemas.all_schemas import FindingResponse, EvidenceResponse

from app.core.security import require_permission, TokenData
from app.core.rbac import Permission

router = APIRouter(prefix="/api/v1/evidence", tags=["Normalized Evidence & Findings"], dependencies=[Depends(require_permission(Permission.EVIDENCE_READ))])

@router.get("/case/{case_id}", response_model=List[EvidenceResponse])
def get_case_evidence(case_id: str, db: Session = Depends(get_db)):
    """Returns all normalized, typed evidence records across the 7 lifecycle boundaries."""
    return db.query(Evidence).filter(Evidence.case_id == case_id).order_by(Evidence.timestamp.desc()).all()

@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_single_evidence(evidence_id: str, db: Session = Depends(get_db)):
    ev = db.query(Evidence).filter(Evidence.evidence_id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence record {evidence_id} not found")
    return ev

@router.get("/findings/case/{case_id}", response_model=List[FindingResponse])
def get_case_findings(case_id: str, db: Session = Depends(get_db)):
    """Returns all empirical detector findings for a case."""
    return db.query(Finding).filter(Finding.case_id == case_id).order_by(Finding.created_at.desc()).all()
