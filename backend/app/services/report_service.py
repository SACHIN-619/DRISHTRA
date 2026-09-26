"""
DRISHTRA Comprehensive Assurance Report Generation Service
Generates formal, machine-readable JSON and formatted Markdown forensic assurance reports.
"""
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models import Case, Contributor, Dataset, ModelAsset, InferenceRecord, Finding, Evidence, AssuranceCase, utc_now_iso
from app.services.audit_service import AuditService

class ReportService:
    @staticmethod
    def generate_case_report(db: Session, case_id: str) -> Dict[str, Any]:
        case = db.query(Case).filter(Case.case_id == case_id).first()
        if not case:
            raise ValueError(f"Case {case_id} not found")

        contributors = db.query(Contributor).filter(Contributor.case_id == case_id).all()
        datasets = db.query(Dataset).filter(Dataset.case_id == case_id).all()
        models = db.query(ModelAsset).filter(ModelAsset.case_id == case_id).all()
        inferences = db.query(InferenceRecord).filter(InferenceRecord.case_id == case_id).all()
        findings = db.query(Finding).filter(Finding.case_id == case_id).all()
        evidence_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
        assurance = db.query(AssuranceCase).filter(AssuranceCase.case_id == case_id).order_by(AssuranceCase.created_at.desc()).first()
        audit_res = AuditService.verify_case_audit(db, case_id)

        report = {
            "report_id": f"REP-{case_id}",
            "generated_at": utc_now_iso(),
            "framework": "DRISHTRA AI Assurance Fabric v1.0.0",
            "jurisdiction": "Ministry of Defence / Indian Army (DGIS) - SIH26228",
            "classification": case.classification,
            "case_metadata": {
                "case_id": case.case_id,
                "name": case.name,
                "status": case.status,
                "created_at": case.created_at
            },
            "supply_chain_entities": {
                "contributors_count": len(contributors),
                "contributors": [{"id": c.contributor_id, "name": c.name, "type": c.contributor_type} for c in contributors],
                "datasets_count": len(datasets),
                "datasets": [{"id": d.dataset_id, "name": d.name, "sha256": d.sha256, "samples": d.sample_count} for d in datasets],
                "models_count": len(models),
                "models": [{"id": m.model_id, "name": m.name, "arch": m.architecture, "weight_sha256": m.weight_sha256} for m in models],
                "inferences_count": len(inferences),
                "inferences": [{"id": i.inference_id, "sequence": i.sequence, "verification": i.verification_status} for i in inferences]
            },
            "findings_summary": {
                "total_findings": len(findings),
                "critical": sum(1 for f in findings if f.severity == "CRITICAL"),
                "high": sum(1 for f in findings if f.severity == "HIGH"),
                "medium": sum(1 for f in findings if f.severity == "MEDIUM"),
                "low": sum(1 for f in findings if f.severity == "LOW"),
                "findings": [
                    {
                        "finding_id": f.finding_id,
                        "asset_id": f.asset_id,
                        "type": f.finding_type,
                        "severity": f.severity,
                        "explanation": f.explanation
                    }
                    for f in findings
                ]
            },
            "assurance_case": {
                "assurance_id": assurance.assurance_id if assurance else None,
                "status": assurance.status if assurance else "NOT_ASSESSED",
                "recommended_disposition": assurance.recommended_disposition if assurance else "REVIEW",
                "claim": assurance.claim if assurance else None,
                "coverage": json.loads(assurance.coverage_json) if assurance else {},
                "limitations": json.loads(assurance.limitations_json) if assurance else []
            },
            "forensic_audit_verification": {
                "chain_status": audit_res.get("status"),
                "verified_event_count": audit_res.get("verified_count"),
                "details": audit_res.get("details")
            }
        }
        return report
