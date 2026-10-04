"""
DRISHTRA Case API Endpoints
Provides:
- Case lifecycle management
- Central 18-stage CasePipeline execution
- Historical pipeline execution tracking
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Case, PipelineRun, AssuranceCase
from app.schemas.all_schemas import (
    CaseCreate, CaseResponse, PipelineRunResponse, AssuranceCaseResponse, AssuranceAssessRequest
)
from app.services.case_service import CaseService
from app.services.pipeline_service import CasePipeline
from app.services.assurance_service import AssuranceService
import json

from app.core.security import require_permission, TokenData
from app.core.rbac import Permission

router = APIRouter(prefix="/api/v1/cases", tags=["Cases & Pipeline Orchestration"], dependencies=[Depends(require_permission(Permission.ASSET_READ))])

@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(case_in: CaseCreate, db: Session = Depends(get_db), user: TokenData = Depends(require_permission(Permission.CASE_CREATE))):
    return CaseService.create_case(db, case_in, actor=user.username)

@router.get("", response_model=List[CaseResponse])
def list_cases(db: Session = Depends(get_db)):
    return CaseService.list_cases(db)

@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = CaseService.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return case

@router.post("/{case_id}/pipeline/run", response_model=PipelineRunResponse)
def run_case_pipeline(
    case_id: str,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.PIPELINE_RUN))
):
    """
    Executes the canonical 18-stage DRISHTRA assurance pipeline on the specified case.
    Stages 01 through 18 execute with strict isolation and idempotency.
    """
    case = CaseService.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    result = CasePipeline.run(db=db, case_id=case_id, actor=user.username)
    return result

@router.post("/{case_id}/pipeline/stream")
def stream_case_pipeline(
    case_id: str,
    pace_ms: int = 0,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.PIPELINE_RUN)),
):
    """
    Same 18-stage run as /pipeline/run, streamed live as newline-delimited JSON events
    (run_started, stage_started, stage_completed, stage_failed, run_finished, assurance).
    ``pace_ms`` (0-1500) pauses between stages so a viewer can follow; stage durations
    reported are the real compute times.
    """
    import json as _json
    import queue
    import threading
    from fastapi.responses import StreamingResponse
    from app.db.database import SessionLocal

    if not CaseService.get_case(db, case_id):
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    q: "queue.Queue" = queue.Queue()
    actor = user.username
    pace = max(0, min(int(pace_ms or 0), 1500))

    def worker():
        s = SessionLocal()
        try:
            CasePipeline.run(db=s, case_id=case_id, actor=actor, on_event=q.put, pace_ms=pace)
            from app.db.models import AssuranceCase
            ac = s.query(AssuranceCase).filter(AssuranceCase.case_id == case_id).order_by(AssuranceCase.created_at.desc()).first()
            if ac:
                q.put({"type": "assurance", "status": ac.status, "recommended_disposition": ac.recommended_disposition,
                       "rationale": ac.rationale if hasattr(ac, "rationale") else None})
        except Exception as e:  # pragma: no cover
            q.put({"type": "error", "message": str(e)})
        finally:
            s.close()
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def gen():
        while True:
            evt = q.get()
            if evt is None:
                break
            yield _json.dumps(evt, default=str) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/{case_id}/pipeline/runs", response_model=List[PipelineRunResponse])
def list_pipeline_runs(case_id: str, db: Session = Depends(get_db)):
    runs = db.query(PipelineRun).filter(PipelineRun.case_id == case_id).order_by(PipelineRun.started_at.desc()).all()
    out = []
    for r in runs:
        import json
        stages = json.loads(r.stages_json or "[]")
        out.append(PipelineRunResponse(
            run_id=r.run_id,
            case_id=r.case_id,
            status=r.status,
            current_stage=r.current_stage,
            stages=stages,
            started_at=r.started_at,
            completed_at=r.completed_at,
            error_message=r.error_message
        ))
    return out

@router.post("/{case_id}/assess", response_model=AssuranceCaseResponse)
def assess_case_alias(
    case_id: str,
    req: AssuranceAssessRequest = AssuranceAssessRequest(),
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.ASSURANCE_BUILD))
):
    """Alias for /api/v1/assurance/{case_id}/assess to evaluate case policy."""
    from app.api.routes.assurance import serialize_assurance
    try:
        ac = AssuranceService.assess_case(db=db, case_id=case_id, actor=user.username)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return serialize_assurance(db, ac)

@router.post("/{case_id}/audit/verify")
def verify_audit_alias(
    case_id: str,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.AUDIT_VERIFY))
):
    """Alias for /api/v1/audit/{case_id}/verify."""
    from app.services.audit_service import AuditService
    result = AuditService.verify_case_audit(db, case_id)
    return {
        "status": result.get("status", "VALID"),
        "verified_count": result.get("verified_count", 0),
        "details": result.get("details", ""),
        "events": result.get("events", [])
    }


