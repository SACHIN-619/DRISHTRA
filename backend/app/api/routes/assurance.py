"""
Assurance case endpoints.

  GET  /api/v1/assurance/queue                  review queue (cases awaiting a human decision)
  GET  /api/v1/assurance/{case_id}              latest assurance case + full decision history
  POST /api/v1/assurance/{case_id}/assess       (re)construct the assurance case      [SECURITY_ANALYST]
  POST /api/v1/assurance/{case_id}/recommend    recommend a disposition               [SECURITY_ANALYST]
  POST /api/v1/assurance/{case_id}/decide       binding, signed disposition           [REVIEWER_SUPERVISOR]
  GET  /api/v1/assurance/{case_id}/decisions    append-only decision history
  POST /api/v1/assurance/{case_id}/decisions/verify  verify decision hash chain + signatures
"""
import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.rbac import Permission
from app.core.security import TokenData, require_permission
from app.db.database import get_db
from app.db.models import AssuranceCase, AssuranceDecision, Case
from app.schemas.all_schemas import (
    AssuranceAssessRequest, AssuranceCaseResponse, DecisionRequest, DispositionApprovalRequest,
)
from app.services.assurance_service import AssuranceService, SeparationOfDutiesError

router = APIRouter(prefix="/api/v1/assurance", tags=["Assurance Cases & Decisions"])


def serialize_assurance(db: Session, ac: AssuranceCase) -> AssuranceCaseResponse:
    cov = json.loads(ac.coverage_json or "{}")
    # Old rows stored a flat {dimension: state} map; new rows store a structured object.
    structured = isinstance(cov, dict) and "dimensions" in cov
    decisions = [AssuranceService.serialize_decision(d) for d in AssuranceService.list_decisions(db, ac.case_id)]
    return AssuranceCaseResponse(
        assurance_id=ac.assurance_id,
        case_id=ac.case_id,
        claim=ac.claim,
        status=ac.status,
        recommended_disposition=ac.recommended_disposition,
        human_disposition=ac.human_disposition,
        approved_by=ac.approved_by,
        approved_at=ac.approved_at,
        approval_notes=ac.approval_notes,
        supporting_evidence=json.loads(ac.supporting_evidence_json or "[]"),
        evidence=json.loads(ac.incriminating_evidence_json or "[]"),
        counter_evidence=json.loads(ac.counter_evidence_json or "[]"),
        coverage=cov.get("dimensions", {}) if structured else cov,
        coverage_summary=cov.get("summary", {}) if structured else {},
        rules_fired=cov.get("rules_fired", []) if structured else [],
        severity_counts=cov.get("severity_counts", {}) if structured else {},
        drift_assessment=cov.get("drift_assessment") if structured else None,
        convergence=json.loads(ac.convergence_json or "{}"),
        limitations=json.loads(ac.limitations_json or "[]"),
        initiated_by=ac.initiated_by,
        decisions=decisions,
        policy_version=ac.policy_version,
        created_at=ac.created_at,
    )


@router.get("/queue")
def review_queue(
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.EVIDENCE_READ)),
):
    """Latest assurance case per case, with its decision state."""
    out = []
    for case in db.query(Case).order_by(Case.updated_at.desc()).all():
        ac = AssuranceService.get_latest_assurance(db, case.case_id)
        if not ac:
            continue
        decisions = db.query(AssuranceDecision).filter(AssuranceDecision.assurance_id == ac.assurance_id) \
            .order_by(AssuranceDecision.sequence.asc()).all()
        final = [d for d in decisions if d.kind == "DISPOSITION"]
        recs = [d for d in decisions if d.kind == "RECOMMENDATION"]
        cov = json.loads(ac.coverage_json or "{}")
        summary = cov.get("summary", {}) if isinstance(cov, dict) else {}
        out.append({
            "case_id": case.case_id,
            "case_name": case.name,
            "case_status": case.status,
            "classification": case.classification,
            "assurance_id": ac.assurance_id,
            "machine_status": ac.status,
            "recommended_disposition": ac.recommended_disposition,
            "coverage_percent": summary.get("percent"),
            "severity_counts": cov.get("severity_counts", {}) if isinstance(cov, dict) else {},
            "analyst_recommendation": recs[-1].disposition if recs else None,
            "analyst": recs[-1].actor if recs else None,
            "final_disposition": final[-1].disposition if final else None,
            "decided_by": final[-1].actor if final else None,
            "awaiting_decision": not final,
            "initiated_by": ac.initiated_by,
            "self_initiated": ac.initiated_by == user.username,
            # Assessments made by the v1 policy (AP-2026.1) had the counter-evidence bug; flag them.
            "legacy_policy": ac.policy_version != "DRISHTRA-AP-2026.2",
            "created_at": ac.created_at,
        })
    return {"items": out}


@router.get("/{case_id}", response_model=AssuranceCaseResponse)
def get_assurance(
    case_id: str,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.EVIDENCE_READ)),
):
    ac = AssuranceService.get_latest_assurance(db, case_id)
    if not ac:
        raise HTTPException(status_code=404, detail=f"No assurance case constructed for {case_id}")
    return serialize_assurance(db, ac)


@router.post("/{case_id}/assess", response_model=AssuranceCaseResponse)
def assess(
    case_id: str,
    req: AssuranceAssessRequest = AssuranceAssessRequest(),
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.ASSURANCE_BUILD)),
):
    try:
        ac = AssuranceService.assess_case(db, case_id, actor=user.username)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return serialize_assurance(db, ac)


def _decide(db: Session, case_id: str, kind: str, disposition: str, rationale: str, user: TokenData) -> Dict[str, Any]:
    try:
        d = AssuranceService.record_decision(
            db, case_id, kind, disposition, rationale, actor=user.username, actor_role=user.role.value
        )
    except SeparationOfDutiesError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    ac = AssuranceService.get_latest_assurance(db, case_id)
    return {"decision": AssuranceService.serialize_decision(d), "assurance": serialize_assurance(db, ac)}


@router.post("/{case_id}/recommend")
def recommend(
    case_id: str, req: DecisionRequest,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.DISPOSITION_RECOMMEND)),
):
    return _decide(db, case_id, "RECOMMENDATION", req.disposition, req.rationale, user)


@router.post("/{case_id}/decide")
def decide(
    case_id: str, req: DecisionRequest,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.DISPOSITION_DECIDE)),
):
    return _decide(db, case_id, "DISPOSITION", req.disposition, req.rationale, user)


def _normalize_legacy(disposition: str) -> str:
    return disposition.upper().replace("APPROVED_", "")


@router.post("/{case_id}/approve", response_model=AssuranceCaseResponse, include_in_schema=False)
def approve_legacy(
    case_id: str, req: DispositionApprovalRequest,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.DISPOSITION_DECIDE)),
):
    """Backward-compatible alias for /decide."""
    return _decide(db, case_id, "DISPOSITION", _normalize_legacy(req.disposition),
                   req.notes or "Disposition recorded via legacy endpoint.", user)["assurance"]


@router.post("/approve", response_model=AssuranceCaseResponse, include_in_schema=False)
def approve_legacy_body(
    req: DispositionApprovalRequest,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.DISPOSITION_DECIDE)),
):
    if not req.case_id:
        raise HTTPException(status_code=400, detail="case_id required in request body")
    return _decide(db, req.case_id, "DISPOSITION", _normalize_legacy(req.disposition),
                   req.notes or "Disposition recorded via legacy endpoint.", user)["assurance"]


@router.get("/{case_id}/decisions")
def decisions(
    case_id: str,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.EVIDENCE_READ)),
):
    return {"items": [AssuranceService.serialize_decision(d) for d in AssuranceService.list_decisions(db, case_id)]}


@router.post("/{case_id}/decisions/verify")
def verify_decisions(
    case_id: str,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.CRYPTO_VERIFY)),
):
    return AssuranceService.verify_decisions(db, case_id)
