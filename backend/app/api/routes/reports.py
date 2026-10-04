"""
DRISHTRA Comprehensive Assurance Report API Endpoints
Provides:
- Machine-Readable JSON Assurance Reports
- Human-Readable Markdown Formatted Reports
- Tactical AI / Offline Incident Debriefs
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Case, Finding, AssuranceCase
from app.services.report_service import ReportService
from app.services.llm_explainer import TacticalIncidentExplainer

from app.core.security import require_permission, TokenData
from app.core.rbac import Permission

router = APIRouter(prefix="/api/v1/reports", tags=["Reports & Incident Debriefs"], dependencies=[Depends(require_permission(Permission.EVIDENCE_READ))])

@router.get("/{case_id}")
@router.post("/{case_id}")
def get_or_generate_assurance_report(case_id: str, db: Session = Depends(get_db)):
    """Generates and returns the authoritative machine-readable JSON forensic assurance report."""
    try:
        return ReportService.generate_case_report(db, case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{case_id}/markdown")
def get_markdown_assurance_report(case_id: str, db: Session = Depends(get_db)):
    """Exports human-readable forensic report in structured Markdown format."""
    try:
        report = ReportService.generate_case_report(db, case_id)
        case_meta = report.get("case_metadata", {})
        assurance = report.get("assurance_case", {})
        findings_summary = report.get("findings_summary", {})
        audit_verif = report.get("forensic_audit_verification", {})

        md = f"""# DRISHTRA ASSURANCE REPORT // {report.get('report_id')}
**Jurisdiction:** {report.get('jurisdiction')}  
**Classification:** {report.get('classification')}  
**Generated At:** {report.get('generated_at')}  

---

## 1. Executive Summary & Operational Disposition
- **Assurance Claim:** {assurance.get('claim', 'N/A')}
- **Recommended Disposition:** `{assurance.get('recommended_disposition', 'REVIEW')}`
- **System Status:** `{assurance.get('status', 'REVIEW_REQUIRED')}`
- **Audit Verification:** `{audit_verif.get('chain_status', 'UNKNOWN')}` ({audit_verif.get('verified_event_count', 0)} events verified)

---

## 2. Supply-Chain Entity Provenance
- **Case ID:** `{case_meta.get('case_id')}` ({case_meta.get('name')})
- **Contributors Monitored:** {report.get('supply_chain_entities', {}).get('contributors_count', 0)}
- **Datasets Ingested:** {report.get('supply_chain_entities', {}).get('datasets_count', 0)}
- **Models Inspected:** {report.get('supply_chain_entities', {}).get('models_count', 0)}
- **Inferences Attested:** {report.get('supply_chain_entities', {}).get('inferences_count', 0)}

---

## 3. Detected Integrity Findings ({findings_summary.get('total_findings', 0)})
| Severity | Finding Type | Asset | Explanation |
| :--- | :--- | :--- | :--- |
"""
        for f in findings_summary.get("findings", []):
            md += f"| **{f.get('severity')}** | `{f.get('type')}` | `{f.get('asset_id')}` | {f.get('explanation')} |\n"

        md += f"""
---

## 4. Declared Engineering Boundaries & Limitations
"""
        for lim in assurance.get("limitations", []):
            md += f"- {lim}\n"

        return Response(content=md, media_type="text/markdown")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{case_id}/ai-debrief")
async def get_tactical_ai_debrief(case_id: str, db: Session = Depends(get_db)):
    """
    Generates an executive military incident debrief.
    Operates 100% offline in air-gapped environments via rule synthesis;
    optionally integrates external Grok when online and configured.
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
