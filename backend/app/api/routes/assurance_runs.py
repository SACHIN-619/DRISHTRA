"""
DRISHTRA Assurance Runs API Endpoint
Provides:
- POST /api/v1/assurance-runs (Orchestrates full sovereign assurance run)
- GET /api/v1/assurance-runs (Lists historical assurance runs)
- GET /api/v1/assurance-runs/{assurance_run_id} (Retrieves assurance run details & state)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import AssuranceRun
from app.schemas.all_schemas import (
    AssuranceRunCreate, AssuranceRunResponse, AssuranceRunListResponse
)
from app.services.assurance_run_service import AssuranceRunService

from app.core.security import require_permission, TokenData
from app.core.rbac import Permission

router = APIRouter(prefix="/api/v1/assurance-runs", tags=["Assurance Runs Orchestrator"], dependencies=[Depends(require_permission(Permission.ASSET_READ))])

@router.post("", response_model=AssuranceRunResponse, status_code=status.HTTP_201_CREATED)
def create_assurance_run(
    req: AssuranceRunCreate,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.PIPELINE_RUN))
):
    """
    Executes unified backend assurance run orchestrator.
    Transitions through explicit states:
    CREATED -> INGESTING -> NORMALIZED -> DATASET_SCANNING -> MODEL_SCANNING ->
    INFERENCE_VERIFYING -> CORRELATING -> ASSURANCE_EVALUATION -> PENDING_REVIEW ->
    ACCEPTED / REVIEW_REQUIRED / QUARANTINED -> EXPORTED -> COMPLETED
    """
    try:
        run_record = AssuranceRunService.create_and_execute_run(
            db=db,
            req=req,
            actor=user.username
        )
        return AssuranceRunService.serialize_run(run_record)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assurance run failed: {str(e)}")

@router.get("", response_model=AssuranceRunListResponse)
def list_assurance_runs(
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Lists executed assurance runs in sovereign vault."""
    query = db.query(AssuranceRun)
    if case_id:
        query = query.filter(AssuranceRun.case_id == case_id)

    total = query.count()
    runs = query.order_by(AssuranceRun.started_at.desc()).offset(skip).limit(limit).all()

    serialized = [AssuranceRunService.serialize_run(r) for r in runs]
    return AssuranceRunListResponse(runs=serialized, total=total)

@router.get("/{assurance_run_id}", response_model=AssuranceRunResponse)
def get_assurance_run(
    assurance_run_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves specific assurance run record by ID."""
    run_record = db.query(AssuranceRun).filter(AssuranceRun.assurance_run_id == assurance_run_id).first()
    if not run_record:
        raise HTTPException(status_code=404, detail=f"Assurance run '{assurance_run_id}' not found.")
    return AssuranceRunService.serialize_run(run_record)
