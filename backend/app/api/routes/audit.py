"""
DRISHTRA Forensic Audit & Non-Repudiation API Endpoints
Provides:
- Append-Only Sequential Audit Ledger Retrieval
- Cryptographic Hash Chain Continuity & Tamper Verification
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.all_schemas import AuditEventResponse, AuditVerifyResponse
from app.services.audit_service import AuditService

from app.core.security import require_permission, TokenData
from app.core.rbac import Permission

router = APIRouter(prefix="/api/v1/audit", tags=["Forensic Audit Ledger"], dependencies=[Depends(require_permission(Permission.AUDIT_READ))])

@router.get("/{case_id}", response_model=List[AuditEventResponse])
def get_case_audit_ledger(
    case_id: str,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.AUDIT_READ))
):
    """Retrieves full append-only forensic audit history for a case."""
    return AuditService.get_events(db, case_id)

@router.post("/{case_id}/verify", response_model=AuditVerifyResponse)
def verify_audit_ledger(
    case_id: str,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.AUDIT_VERIFY))
):
    """
    Cryptographically verifies that no historical events in the audit chain
    have been altered, deleted, reordered, or forged.
    """
    result = AuditService.verify_case_audit(db, case_id)
    return AuditVerifyResponse(
        status=result.get("status", "VALID"),
        verified_count=result.get("verified_count", 0),
        details=result.get("details", ""),
        events=result.get("events", [])
    )
