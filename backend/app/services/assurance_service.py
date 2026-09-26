"""
DRISHTRA Assurance Case Generation Service
Transforms heterogeneous evidence, coverage boundaries, and limitations into an auditable Assurance Case.
"""
import uuid
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.db.models import AssuranceCase, Finding, Case, utc_now_iso
from app.policies.assurance_policy import AssurancePolicyEngine
from app.services.audit_service import AuditService

class AssuranceService:
    @staticmethod
    def assess_case(
        db: Session,
        case_id: str,
        policy_version: str = "DRISHTRA-AP-2026.1",
        actor: str = "assurance_engine"
    ) -> AssuranceCase:
        case = db.query(Case).filter(Case.case_id == case_id).first()
        if not case:
            raise ValueError(f"Case {case_id} not found")

        # 1. Fetch all findings associated with this case
        findings = db.query(Finding).filter(Finding.case_id == case_id).all()

        # 2. Build coverage matrix
        coverage_map = {
            "dataset_byte_integrity": "AVAILABLE",
            "exact_duplicate_detection": "AVAILABLE",
            "near_duplicate_flooding": "AVAILABLE",
            "label_poisoning_analysis": "AVAILABLE",
            "ood_representation_detection": "AVAILABLE",
            "model_weight_cryptographic_digest": "AVAILABLE",
            "black_box_behavioral_probe_battery": "AVAILABLE",
            "white_box_activation_clustering": "NOT_AVAILABLE", # Declared limitation for black-box models
            "trigger_reconstruction_inversion": "LIMITED",
            "inference_cryptographic_attestation": "AVAILABLE",
            "replay_and_sequence_verification": "AVAILABLE",
            "distribution_shift_characterization": "AVAILABLE",
            "tamper_evident_audit_ledger": "AVAILABLE"
        }

        # 3. Apply transparent policy engine
        eval_result = AssurancePolicyEngine.evaluate(
            findings=findings,
            coverage_map=coverage_map,
            context={"case_id": case_id, "classification": case.classification}
        )

        assurance_id = f"AC-{uuid.uuid4().hex[:8].upper()}"
        
        assurance_case = AssuranceCase(
            assurance_id=assurance_id,
            case_id=case_id,
            claim=eval_result["claim"],
            status=eval_result["status"],
            recommended_disposition=eval_result["recommended_disposition"],
            supporting_evidence_json=json.dumps(eval_result["supporting_evidence"]),
            counter_evidence_json=json.dumps(eval_result["counter_evidence"]),
            coverage_json=json.dumps(eval_result["coverage"]),
            limitations_json=json.dumps(eval_result["limitations"]),
            policy_version=policy_version,
            created_at=utc_now_iso()
        )
        db.add(assurance_case)
        
        # Update Case status to match disposition
        case.status = eval_result["status"]
        case.updated_at = utc_now_iso()
        
        db.commit()
        db.refresh(assurance_case)

        AuditService.record_event(
            db=db,
            case_id=case_id,
            actor=actor,
            action="ASSURANCE_CASE_EVALUATED",
            asset_id=assurance_id,
            result=eval_result["status"],
            reason=f"Generated Assurance Case with recommended disposition '{eval_result['recommended_disposition']}'"
        )
        return assurance_case

    @staticmethod
    def get_latest_assurance(db: Session, case_id: str) -> Optional[AssuranceCase]:
        return db.query(AssuranceCase).filter(AssuranceCase.case_id == case_id).order_by(AssuranceCase.created_at.desc()).first()
