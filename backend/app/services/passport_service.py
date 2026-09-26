"""
DRISHTRA Assurance Passport Service
Generates cryptographic and behavioral identity profiles ("AI Passports") for protected assets.
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models import ModelAsset, Dataset, InferenceRecord, Finding, Contributor
from app.schemas.all_schemas import AssurancePassportResponse

class PassportService:
    @staticmethod
    def get_model_passport(db: Session, model_id: str) -> Optional[AssurancePassportResponse]:
        model = db.query(ModelAsset).filter(ModelAsset.model_id == model_id).first()
        if not model:
            return None

        contrib = db.query(Contributor).filter(Contributor.contributor_id == model.contributor_id).first()
        contrib_name = contrib.name if contrib else model.contributor_id

        findings = db.query(Finding).filter(Finding.asset_id == model_id).all()
        findings_summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        counter_findings = []
        for f in findings:
            findings_summary[f.severity] = findings_summary.get(f.severity, 0) + 1
            if f.severity in ["CRITICAL", "HIGH", "MEDIUM"]:
                counter_findings.append(f"{f.finding_type}: {f.explanation}")

        # Compute status
        if findings_summary.get("CRITICAL", 0) > 0:
            status = "QUARANTINED"
        elif findings_summary.get("HIGH", 0) > 0:
            status = "REVIEW_REQUIRED"
        else:
            status = "VERIFIED"

        coverage_matrix = {
            "weight_integrity_sha256": "AVAILABLE",
            "behavioral_probe_battery": "AVAILABLE",
            "backdoor_trigger_search": "AVAILABLE",
            "white_box_activation_analysis": "NOT_AVAILABLE (Black-Box format)",
            "cryptographic_provenance": "AVAILABLE"
        }

        limitations = [
            "White-box gradient and internal layer clustering unavailable under Black-box deployment profile.",
            "Trojan triggers with spatial footprint outside 10-probe geometry may evade detection."
        ]

        verified_claims = [
            f"Weight digest {model.weight_sha256[:16]}... registered by sovereign contributor {contrib_name}",
            f"Evaluated against reference baseline {model.reference_model_id or 'SOVEREIGN_BASE'}"
        ]

        return AssurancePassportResponse(
            passport_id=f"PASS-{model_id}",
            asset_id=model_id,
            asset_type="MODEL",
            name=model.name,
            contributor=contrib_name,
            version=model.version,
            digest_sha256=model.weight_sha256,
            lineage_parent=model.reference_model_id,
            assurance_status=status,
            findings_summary=findings_summary,
            coverage_matrix=coverage_matrix,
            limitations=limitations,
            verified_claims=verified_claims,
            counter_findings=counter_findings,
            last_assessed=model.created_at
        )

    @staticmethod
    def get_dataset_passport(db: Session, dataset_id: str) -> Optional[AssurancePassportResponse]:
        dataset = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
        if not dataset:
            return None

        contrib = db.query(Contributor).filter(Contributor.contributor_id == dataset.contributor_id).first()
        contrib_name = contrib.name if contrib else dataset.contributor_id

        findings = db.query(Finding).filter(Finding.asset_id == dataset_id).all()
        findings_summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        counter_findings = []
        for f in findings:
            findings_summary[f.severity] = findings_summary.get(f.severity, 0) + 1
            if f.severity in ["CRITICAL", "HIGH", "MEDIUM"]:
                counter_findings.append(f"{f.finding_type}: {f.explanation}")

        status = "QUARANTINED" if findings_summary.get("CRITICAL", 0) > 0 else (
            "REVIEW_REQUIRED" if (findings_summary.get("HIGH", 0) > 0 or findings_summary.get("MEDIUM", 0) > 0) else "VERIFIED"
        )

        return AssurancePassportResponse(
            passport_id=f"PASS-{dataset_id}",
            asset_id=dataset_id,
            asset_type="DATASET",
            name=dataset.name,
            contributor=contrib_name,
            version=dataset.version,
            digest_sha256=dataset.sha256,
            lineage_parent=dataset.manifest_hash,
            assurance_status=status,
            findings_summary=findings_summary,
            coverage_matrix={
                "exact_duplicate_detection": "AVAILABLE",
                "near_duplicate_dhash": "AVAILABLE",
                "label_poisoning_analysis": "AVAILABLE"
            },
            limitations=["Evaluated on uploaded sample partition. Unindexed external batches not covered."],
            verified_claims=[f"Manifest hash {dataset.manifest_hash[:16]}... cryptographically bound"],
            counter_findings=counter_findings,
            last_assessed=dataset.created_at
        )
