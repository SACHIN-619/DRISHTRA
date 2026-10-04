"""
DRISHTRA Stage-by-Stage Verifiable Artifact Export Service
Ensures each pipeline stage produces a discrete, machine-verifiable JSON artifact:
1. dataset_manifest.json
2. dataset_findings.json
3. model_passport.json
4. inference_attestation.json
5. verification_result.json
6. evidence_graph.json
7. assurance_case.json
8. assurance_report.json
9. audit_chain.json
"""
import os
import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.models import Case, Dataset, ModelAsset, InferenceRecord, Finding, Evidence, AssuranceCase, AuditEvent
from app.correlation.evidence_graph import EvidenceGraphBuilder
from app.services.report_service import ReportService
from app.services.audit_service import AuditService

class ArtifactExportService:
    @staticmethod
    def export_all_stage_artifacts(db: Session, case_id: str) -> Dict[str, str]:
        """
        Exports all 9 canonical stage artifacts to disk in `storage/artifacts/<case_id>/`
        Returns a dictionary mapping artifact_type -> absolute file path.
        """
        out_dir = os.path.join(settings.ARTIFACTS_DIR, case_id)
        os.makedirs(out_dir, exist_ok=True)
        paths = {}

        # 1. dataset_manifest.json
        datasets = db.query(Dataset).filter(Dataset.case_id == case_id).all()
        ds_manifests = [
            {
                "dataset_id": d.dataset_id,
                "name": d.name,
                "format": d.format,
                "version": d.version,
                "sha256": d.sha256,
                "manifest_hash": d.manifest_hash,
                "sample_count": d.sample_count,
                "contributor_id": d.contributor_id,
                "created_at": d.created_at
            }
            for d in datasets
        ]
        p1 = os.path.join(out_dir, "dataset_manifest.json")
        with open(p1, "w", encoding="utf-8") as f:
            json.dump(ds_manifests, f, indent=2)
        paths["dataset_manifest"] = p1

        # 2. dataset_findings.json
        findings = db.query(Finding).filter(Finding.case_id == case_id, Finding.asset_type == "DATASET").all()
        ds_findings = [
            {
                "finding_id": f.finding_id,
                "dataset_id": f.asset_id,
                "detector_id": f.detector_id,
                "finding_type": f.finding_type,
                "severity": f.severity,
                "confidence": f.confidence,
                "explanation": f.explanation,
                "created_at": f.created_at
            }
            for f in findings
        ]
        p2 = os.path.join(out_dir, "dataset_findings.json")
        with open(p2, "w", encoding="utf-8") as f:
            json.dump(ds_findings, f, indent=2)
        paths["dataset_findings"] = p2

        # 3. model_passport.json
        models = db.query(ModelAsset).filter(ModelAsset.case_id == case_id).all()
        model_passports = [
            {
                "model_id": m.model_id,
                "name": m.name,
                "architecture": m.architecture,
                "framework": m.framework,
                "format": m.format,
                "version": m.version,
                "access_level": m.access_level,
                "weight_sha256": m.weight_sha256,
                "structural_digest": getattr(m, "structural_digest", m.weight_sha256),
                "created_at": m.created_at
            }
            for m in models
        ]
        p3 = os.path.join(out_dir, "model_passport.json")
        with open(p3, "w", encoding="utf-8") as f:
            json.dump(model_passports, f, indent=2)
        paths["model_passport"] = p3

        # 4. inference_attestation.json
        inferences = db.query(InferenceRecord).filter(InferenceRecord.case_id == case_id).all()
        inf_attestations = [
            {
                "inference_id": i.inference_id,
                "sequence": i.sequence,
                "timestamp": i.timestamp,
                "nonce": i.nonce,
                "input_sha256": i.input_sha256,
                "model_sha256": i.model_sha256,
                "output_sha256": i.output_sha256,
                "signature": i.signature,
                "verification_status": i.verification_status
            }
            for i in inferences
        ]
        p4 = os.path.join(out_dir, "inference_attestation.json")
        with open(p4, "w", encoding="utf-8") as f:
            json.dump(inf_attestations, f, indent=2)
        paths["inference_attestation"] = p4

        # 5. verification_result.json
        v_results = [
            {
                "inference_id": i.inference_id,
                "status": i.verification_status,
                "is_valid": i.verification_status == "VERIFIED",
                "reason": "Cryptographic signature matches canonical hash" if i.verification_status == "VERIFIED" else "Signature invalid or output modified post-signing"
            }
            for i in inferences
        ]
        p5 = os.path.join(out_dir, "verification_result.json")
        with open(p5, "w", encoding="utf-8") as f:
            json.dump(v_results, f, indent=2)
        paths["verification_result"] = p5

        # 6. evidence_graph.json
        builder = EvidenceGraphBuilder.from_database(case_id, db)
        graph_data = builder.to_schema().model_dump()
        p6 = os.path.join(out_dir, "evidence_graph.json")
        with open(p6, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2)
        paths["evidence_graph"] = p6

        # 7. assurance_case.json
        assurance = db.query(AssuranceCase).filter(AssuranceCase.case_id == case_id).order_by(AssuranceCase.created_at.desc()).first()
        ac_data = {
            "assurance_id": assurance.assurance_id if assurance else None,
            "case_id": case_id,
            "claim": assurance.claim if assurance else "Not assessed",
            "recommended_disposition": assurance.recommended_disposition if assurance else "REVIEW",
            "status": assurance.status if assurance else "INCONCLUSIVE",
            "coverage": json.loads(assurance.coverage_json) if assurance else {},
            "limitations": json.loads(assurance.limitations_json) if assurance else []
        }
        p7 = os.path.join(out_dir, "assurance_case.json")
        with open(p7, "w", encoding="utf-8") as f:
            json.dump(ac_data, f, indent=2)
        paths["assurance_case"] = p7

        # 8. assurance_report.json
        rep = ReportService.generate_case_report(db, case_id)
        p8 = os.path.join(out_dir, "assurance_report.json")
        with open(p8, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2)
        paths["assurance_report"] = p8

        # 9. audit_chain.json
        audit_events = db.query(AuditEvent).filter(AuditEvent.case_id == case_id).all()
        chain_events = [
            {
                "event_id": ev.event_id,
                "sequence": idx + 1,
                "timestamp": ev.timestamp,
                "actor": ev.actor,
                "action": ev.action,
                "asset_id": ev.asset_id,
                "result": ev.result,
                "reason": ev.reason,
                "current_hash": ev.event_hash,
                "previous_hash": ev.previous_event_hash
            }
            for idx, ev in enumerate(audit_events)
        ]
        p9 = os.path.join(out_dir, "audit_chain.json")
        with open(p9, "w", encoding="utf-8") as f:
            json.dump(chain_events, f, indent=2)
        paths["audit_chain"] = p9

        return paths

    @classmethod
    def export_case_bundle(cls, db: Session, case_id: str, assurance_run_id: str = "AR-2026-000001") -> Dict[str, Any]:
        """
        Exports all 9 canonical stage artifacts with standard header metadata and calculates artifact hashes.
        Returns bundle summary mapping artifact name -> sha256 digest.
        """
        import hashlib
        from datetime import datetime, timezone

        paths = cls.export_all_stage_artifacts(db, case_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        artifact_hashes = {}

        for name, file_path in paths.items():
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content_data = json.load(f)

                # Compute content sha256 before wrapping
                raw_json_str = json.dumps(content_data, sort_keys=True)
                content_sha256 = hashlib.sha256(raw_json_str.encode()).hexdigest()

                wrapped = {
                    "header": {
                        "schema_version": "1.0.0",
                        "created_at": now_iso,
                        "case_id": case_id,
                        "assurance_run_id": assurance_run_id,
                        "sha256": content_sha256
                    },
                    "data": content_data
                }

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(wrapped, f, indent=2)

                artifact_hashes[name] = content_sha256

        return {
            "case_id": case_id,
            "assurance_run_id": assurance_run_id,
            "artifact_count": len(paths),
            "artifact_paths": paths,
            "artifact_hashes": artifact_hashes
        }
