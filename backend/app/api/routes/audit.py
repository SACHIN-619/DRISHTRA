"""
DRISHTRA Forensic Audit & Non-Repudiation API Endpoints
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.all_schemas import AuditEventResponse, AuditVerifyResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1", tags=["Forensic Audit Ledger"])

@router.get("/cases/{case_id}/audit", response_model=List[AuditEventResponse])
def get_case_audit_ledger(case_id: str, db: Session = Depends(get_db)):
    return AuditService.get_events(db, case_id)

@router.post("/cases/{case_id}/audit/verify", response_model=AuditVerifyResponse)
def verify_audit_ledger(case_id: str, db: Session = Depends(get_db)):
    result = AuditService.verify_case_audit(db, case_id)
    return AuditVerifyResponse(
        status=result.get("status", "VALID"),
        verified_count=result.get("verified_count", 0),
        details=result.get("details", ""),
        events=result.get("events", [])
    )
