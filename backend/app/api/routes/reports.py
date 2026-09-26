"""
DRISHTRA Assurance Report and Deterministic Demo Endpoints
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Case, Finding, AssuranceCase
from app.services.report_service import ReportService
from app.services.demo_service import DemoService
from app.services.llm_explainer import TacticalIncidentExplainer

router = APIRouter(prefix="/api/v1", tags=["Reports & Demo Scenarios"])

@router.post("/cases/{case_id}/report")
def generate_assurance_report(case_id: str, db: Session = Depends(get_db)):
    try:
        return ReportService.generate_case_report(db, case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/cases/{case_id}/ai-debrief")
async def get_tactical_ai_debrief(case_id: str, db: Session = Depends(get_db)):
    """
    Generates a natural language tactical military incident debrief.
    Uses Grok API when GROK_API_KEY is configured in .env;
    gracefully falls back to offline sovereign synthesis in air-gapped environments.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    findings = db.query(Finding).filter(Finding.case_id == case_id).all()
    assurance = db.query(AssuranceCase).filter(AssuranceCase.case_id == case_id).order_by(AssuranceCase.created_at.desc()).first()

    findings_data = [
        {"finding_type": f.finding_type, "severity": f.severity, "explanation": f.explanation}
        for f in findings
    ]
    assurance_data = {
        "status": assurance.status if assurance else "REVIEW_REQUIRED",
        "recommended_disposition": assurance.recommended_disposition if assurance else "REVIEW",
        "claim": assurance.claim if assurance else "Evaluation pending."
    }

    debrief = await TacticalIncidentExplainer.generate_debrief(
        case_id=case_id,
        case_name=case.name,
        findings=findings_data,
        assurance_case=assurance_data
    )
    return debrief

@router.post("/demo/bootstrap")
def bootstrap_deterministic_demo(db: Session = Depends(get_db)):
    """
    Initializes the full sovereign evaluation case: CASE-2026-DRISHTRA-DEMO
    Populates clean vs attacked contributors, datasets, models, inferences,
    and runs scans, evidence graph correlation, assurance cases, and audit chains.
    """
    return DemoService.bootstrap_demo_case(db)
