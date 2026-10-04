"""
DRISHTRA Model Sentinel Service
Model Asset Registration, Weight Fingerprinting, Probe Battery Evaluation, and Lineage Linking.
"""
import uuid
import json
import hashlib
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import ModelAsset, Finding, Evidence, EvidenceEdge, utc_now_iso
from app.schemas.all_schemas import ModelRegister
from app.detectors.model_integrity_detector import ModelIntegrityDetector
from app.detectors.behavioral_fingerprint_detector import BehavioralFingerprintDetector
from app.services.audit_service import AuditService
from app.services.evidence_writer import record_check, record_not_applicable

class ModelService:
    @staticmethod
    def register_model(db: Session, model_in: ModelRegister, weight_bytes: Optional[bytes] = None, actor: str = "analyst") -> ModelAsset:
        model_id = f"M-{uuid.uuid4().hex[:6].upper()}"
        
        # The registered digest is what every later delivery is compared against.
        # It is never invented: it comes from the uploaded bytes or the contributor's declaration.
        if weight_bytes:
            weight_digest = hashlib.sha256(weight_bytes).hexdigest()
        elif model_in.weight_sha256:
            weight_digest = model_in.weight_sha256
        else:
            raise ValueError("A registered weight digest (weight_sha256) or the model file is required.")

        model = ModelAsset(
            model_id=model_id,
            case_id=model_in.case_id,
            contributor_id=model_in.contributor_id,
            name=model_in.name,
            framework=model_in.framework,
            format=model_in.format,
            architecture=model_in.architecture,
            version=model_in.version,
            weight_sha256=weight_digest,
            reference_model_id=model_in.reference_model_id,
            location=model_in.location,
            access_level=model_in.access_level,
            created_at=utc_now_iso()
        )
        db.add(model)

        # Link: Contributor -> Model
        edge_id = f"EDGE-{uuid.uuid4().hex[:8].upper()}"
        edge = EvidenceEdge(
            edge_id=edge_id,
            case_id=model_in.case_id,
            source_node=f"contributor:{model_in.contributor_id}",
            target_node=f"model:{model_id}",
            relationship="supplied_by",
            epistemic_status="OBSERVED",
            evidence_ids_json="[]"
        )
        db.add(edge)
        db.commit()
        db.refresh(model)

        AuditService.record_event(
            db=db,
            case_id=model_in.case_id,
            actor=actor,
            action="MODEL_REGISTERED",
            asset_id=model_id,
            result="SUCCESS",
            reason=f"Registered model '{model.name}' [{model.architecture} {model.format}] Digest: {weight_digest[:16]}..."
        )
        return model

    @staticmethod
    def scan_model(
        db: Session,
        model_id: str,
        current_weight_sha256: str,
        probe_responses: Optional[Dict[str, Any]] = None,
        actor: str = "analyst",
        run_digest: bool = True,
        run_behaviour: bool = True,
    ) -> List[Finding]:
        """
        D8A weight digest, D8B behavioural probes (when probe responses
        are supplied), D8C white-box analysis (declared NOT_APPLICABLE for
        black-box / structural-only access, NOT_TESTED otherwise).
        """
        model = db.query(ModelAsset).filter(ModelAsset.model_id == model_id).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")

        created: List[Finding] = []
        if run_digest:
            res_int = ModelIntegrityDetector().run(
                current_weight_sha256=current_weight_sha256,
                registered_weight_sha256=model.weight_sha256,
                reference_model_sha256=None,
            )
            created += record_check(db, model.case_id, "MODEL", model_id, "D8A_WEIGHT_DIGEST", res_int,
                                    actor=actor, input_digest=current_weight_sha256)
        if not run_behaviour:
            db.commit()
            return created

        res_beh = BehavioralFingerprintDetector().run(probe_results=probe_responses or None)
        created += record_check(db, model.case_id, "MODEL", model_id, "D8B_BEHAVIOURAL_PROBE", res_beh, actor=actor)

        access = model.access_level or "BLACK_BOX"
        if access in ("BLACK_BOX", "STRUCTURAL_ONLY", "UNAVAILABLE"):
            reason = (f"Supplied under {access} access: internal weights/activations unavailable, so white-box "
                      "trigger reconstruction cannot run. Declared limitation, not a pass.")
        else:
            reason = ("White-box weights are available, but white-box trigger reconstruction is not implemented "
                      "in this prototype. Black-box probes were used instead. Declared limitation, not a pass.")
        record_not_applicable(db, model.case_id, "MODEL", model_id, "D8C_WHITE_BOX_ANALYSIS", reason, actor=actor)

        AuditService.record_event(
            db=db,
            case_id=model.case_id,
            actor=actor,
            action="MODEL_SCANNED",
            asset_id=model_id,
            result="COMPLETED",
            reason=json.dumps({"findings": len(created), "probes_supplied": bool(probe_responses),
                               "access_level": model.access_level}, sort_keys=True),
        )
        return created

