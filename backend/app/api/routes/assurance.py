"""
DRISHTRA Assurance Case Engine API Endpoints
"""
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import AssuranceCase
from app.schemas.all_schemas import AssuranceCaseResponse, AssuranceAssessRequest
from app.services.assurance_service import AssuranceService

router = APIRouter(prefix="/api/v1/cases", tags=["Assurance Engine"])

def _serialize_assurance(ac: AssuranceCase) -> AssuranceCaseResponse:
    return AssuranceCaseResponse(
        assurance_id=ac.assurance_id,
        case_id=ac.case_id,
        claim=ac.claim,
        status=ac.status,
        recommended_disposition=ac.recommended_disposition,
        supporting_evidence=json.loads(ac.supporting_evidence_json or "[]"),
        counter_evidence=json.loads(ac.counter_evidence_json or "[]"),
        coverage=json.loads(ac.coverage_json or "{}"),
        limitations=json.loads(ac.limitations_json or "[]"),
        policy_version=ac.policy_version,
        created_at=ac.created_at
    )

@router.post("/{case_id}/assess", response_model=AssuranceCaseResponse)
def assess_case(case_id: str, req: AssuranceAssessRequest = AssuranceAssessRequest(), db: Session = Depends(get_db)):
    try:
        ac = AssuranceService.assess_case(db, case_id, policy_version=req.policy_version or "DRISHTRA-AP-2026.1")
        return _serialize_assurance(ac)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{case_id}/assurance", response_model=AssuranceCaseResponse)
def get_case_assurance(case_id: str, db: Session = Depends(get_db)):
    ac = AssuranceService.get_latest_assurance(db, case_id)
    if not ac:
        raise HTTPException(status_code=404, detail=f"No assurance case evaluated for case {case_id}")
    return _serialize_assurance(ac)
