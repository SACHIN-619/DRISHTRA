"""
DRISHTRA Assurance Run Service
Unified orchestrator for POST /api/v1/assurance-runs.
Manages explicit state machine transitions:
CREATED -> INGESTING -> NORMALIZED -> DATASET_SCANNING -> MODEL_SCANNING ->
INFERENCE_VERIFYING -> CORRELATING -> ASSURANCE_EVALUATION -> PENDING_REVIEW ->
(ACCEPTED / REVIEW_REQUIRED / QUARANTINED) -> EXPORTED -> COMPLETED
"""
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.db.models import AssuranceRun, Case, Dataset, ModelAsset, InferenceRecord, Finding, utc_now_iso
from app.schemas.all_schemas import AssuranceRunCreate, AssuranceRunResponse
from app.services.pipeline_service import CasePipeline
from app.services.assurance_service import AssuranceService
from app.services.artifact_export_service import ArtifactExportService
from app.services.audit_service import AuditService
from app.correlation.evidence_graph import EvidenceGraphBuilder
from app.policies.assurance_policy import AssurancePolicyEngine

logger = logging.getLogger(__name__)

class AssuranceRunService:

    @classmethod
    def serialize_run(cls, run: AssuranceRun) -> AssuranceRunResponse:
        return AssuranceRunResponse(
            assurance_run_id=run.assurance_run_id,
            case_id=run.case_id,
            dataset_id=run.dataset_id,
            model_id=run.model_id,
            execution_mode=run.execution_mode,
            status=run.status,
            current_stage=run.current_stage,
            detector_versions=json.loads(run.detector_versions_json or "{}"),
            policy_version=run.policy_version,
            dataset_version=run.dataset_version,
            model_version=run.model_version,
            input_hashes=json.loads(run.input_hashes_json or "{}"),
            output_hashes=json.loads(run.output_hashes_json or "{}"),
            errors=json.loads(run.errors_json or "[]"),
            warnings=json.loads(run.warnings_json or "[]"),
            coverage=json.loads(run.coverage_json or "{}"),
            started_at=run.started_at,
            completed_at=run.completed_at
        )

    @classmethod
    def create_and_execute_run(
        cls,
        db: Session,
        req: AssuranceRunCreate,
        actor: str = "assurance_orchestrator"
    ) -> AssuranceRun:
        """
        Executes a complete sovereign assurance run across all explicit lifecycle states.
        """
        # Validate target case
        case = db.query(Case).filter(Case.case_id == req.case_id).first()
        if not case:
            raise ValueError(f"Case '{req.case_id}' does not exist in sovereign vault.")

        run_seq = db.query(AssuranceRun).count() + 1
        assurance_run_id = f"AR-2026-{run_seq:06d}"

        detector_versions = {
            "exact_duplicate_detector": "1.0.0",
            "near_duplicate_detector": "1.0.0",
            "label_anomaly_detector": "1.0.0",
            "class_imbalance_detector": "1.0.0",
            "distribution_shift_detector": "1.0.0",
            "malformed_annotation_detector": "1.0.0",
            "behavioral_fingerprint_detector": "1.0.0",
            "model_integrity_detector": "1.0.0",
            "replay_detector": "1.0.0"
        }

        run_record = AssuranceRun(
            assurance_run_id=assurance_run_id,
            case_id=req.case_id,
            dataset_id=req.dataset_id,
            model_id=req.model_id,
            execution_mode=req.execution_mode or "OFFLINE",
            status="CREATED",
            current_stage="CREATED",
            detector_versions_json=json.dumps(detector_versions),
            policy_version="DRISHTRA-AP-2026.2",
            dataset_version="1.0.0",
            model_version="1.0.0",
            input_hashes_json=json.dumps({}),
            output_hashes_json=json.dumps({}),
            errors_json="[]",
            warnings_json="[]",
            coverage_json="{}",
            started_at=utc_now_iso()
        )
        db.add(run_record)
        db.commit()

        errors: List[str] = []
        warnings: List[str] = []

        try:
            # Step 1: INGESTING
            run_record.status = "INGESTING"
            run_record.current_stage = "INGESTING"
            db.commit()

            # Record input hashes if datasets and models exist
            input_hashes = {}
            if req.dataset_id:
                ds = db.query(Dataset).filter(Dataset.dataset_id == req.dataset_id).first()
                if ds:
                    input_hashes["dataset_sha256"] = ds.sha256
                    run_record.dataset_version = ds.version
            else:
                datasets = db.query(Dataset).filter(Dataset.case_id == req.case_id).all()
                if datasets:
                    input_hashes["datasets"] = [d.sha256 for d in datasets if d.sha256]

            if req.model_id:
                m = db.query(ModelAsset).filter(ModelAsset.model_id == req.model_id).first()
                if m:
                    input_hashes["model_weight_sha256"] = m.weight_sha256
                    run_record.model_version = m.version
            else:
                models = db.query(ModelAsset).filter(ModelAsset.case_id == req.case_id).all()
                if models:
                    input_hashes["models"] = [m.weight_sha256 for m in models if m.weight_sha256]

            run_record.input_hashes_json = json.dumps(input_hashes)
            db.commit()

            # The 18-stage pipeline does the real work (scan, verify, correlate, assess).
            run_record.status = "PIPELINE_RUNNING"
            run_record.current_stage = "PIPELINE_RUNNING"
            db.commit()
            pipeline_res = CasePipeline.run(db=db, case_id=req.case_id, actor=actor)
            if pipeline_res.status != "COMPLETED":
                raise RuntimeError(f"Pipeline failed: {pipeline_res.error_message}")
            warnings += [w for st in pipeline_res.stages for w in st.warnings]

            ac = AssuranceService.get_latest_assurance(db, req.case_id)
            run_record.coverage_json = ac.coverage_json or "{}"
            # The machine only recommends; a REVIEWER_SUPERVISOR decides.
            run_record.status = f"AWAITING_DECISION ({ac.recommended_disposition} RECOMMENDED)"
            run_record.current_stage = "PENDING_REVIEW"
            db.commit()

            # Step 9: EXPORTED - Export discrete artifacts
            export_summary = ArtifactExportService.export_case_bundle(
                db=db,
                case_id=req.case_id,
                assurance_run_id=assurance_run_id
            )
            output_hashes = export_summary.get("artifact_hashes", {})
            run_record.output_hashes_json = json.dumps(output_hashes)

            # Step 10: COMPLETED
            run_record.current_stage = "COMPLETED"
            run_record.completed_at = utc_now_iso()
            run_record.errors_json = json.dumps(errors)
            run_record.warnings_json = json.dumps(warnings)
            db.commit()

            # Audit event
            AuditService.record_event(
                db=db,
                case_id=req.case_id,
                actor=actor,
                action="ASSURANCE_RUN_COMPLETED",
                asset_id=assurance_run_id,
                result=run_record.status,
                reason=f"Assurance run {assurance_run_id} completed with status '{run_record.status}'."
            )

            return run_record

        except Exception as e:
            logger.error(f"[!] Assurance run {assurance_run_id} failed: {e}", exc_info=True)
            run_record.status = "FAILED"
            run_record.current_stage = "FAILED"
            errors.append(str(e))
            run_record.errors_json = json.dumps(errors)
            run_record.completed_at = utc_now_iso()
            db.commit()

            AuditService.record_event(
                db=db,
                case_id=req.case_id,
                actor=actor,
                action="ASSURANCE_RUN_FAILED",
                asset_id=assurance_run_id,
                result="FAILED",
                reason=f"Assurance run failed: {str(e)}"
            )

            return run_record
