"""
DRISHTRA Findings & Forensic Attribution API Endpoints
Provides:
- GET /api/v1/findings (Queryable cross-asset findings ledger)
- GET /api/v1/findings/{finding_id} (Detailed finding record)
- GET /api/v1/findings/{finding_id}/why-flagged (Decomposed forensic causality path)
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Finding, Evidence, Case, Contributor, Dataset, ModelAsset, InferenceRecord, RuntimeBinding
from app.schemas.all_schemas import FindingResponse

from app.core.security import require_permission, TokenData
from app.core.rbac import Permission

router = APIRouter(prefix="/api/v1/findings", tags=["Findings & Forensic Attribution"], dependencies=[Depends(require_permission(Permission.EVIDENCE_READ))])

@router.get("", response_model=List[FindingResponse])
def list_findings(
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    asset_id: Optional[str] = Query(None, description="Filter by asset ID"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type (DATASET, MODEL, INFERENCE)"),
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"),
    status: Optional[str] = Query(None, description="Filter by status (FINDING, REVIEW_REQUIRED, RESOLVED)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Lists detected forensic and integrity findings across sovereign assets."""
    query = db.query(Finding)
    if case_id:
        query = query.filter(Finding.case_id == case_id)
    if asset_id:
        query = query.filter(Finding.asset_id == asset_id)
    if asset_type:
        query = query.filter(Finding.asset_type == asset_type)
    if severity:
        query = query.filter(Finding.severity == severity)
    if status:
        query = query.filter(Finding.status == status)
    return query.order_by(Finding.created_at.desc()).offset(offset).limit(limit).all()

@router.get("/{finding_id}", response_model=FindingResponse)
def get_finding_detail(finding_id: str, db: Session = Depends(get_db)):
    """Fetches full finding metadata and detector explanation."""
    finding = db.query(Finding).filter(Finding.finding_id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")
    return finding

@router.get("/{finding_id}/why-flagged")
def get_why_flagged_trace(finding_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    "Why was this flagged?": the finding, its upstream lineage to the contributor,
    findings on every layer of that lineage, checks that passed (counter-evidence),
    what was not tested, and the current recommendation. Built only from stored facts.
    """
    from app.services.passport_service import PassportService
    result = PassportService.why_flagged(db, finding_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")
    return result
