"""
DRISHTRA Inference Attestor Service
Cryptographic Ingestion, Ed25519 Attestation Verification, Replay Detection, and Tamper Analysis.
"""
import uuid
import json
import hashlib
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import InferenceRecord, Finding, Evidence, EvidenceEdge, utc_now_iso
from app.schemas.all_schemas import InferenceRegister
from app.detectors.replay_detector import ReplayAndProvenanceDetector
from app.services.audit_service import AuditService
from app.services.evidence_writer import record_check

class InferenceService:
    @staticmethod
    def register_inference(db: Session, inf_in: InferenceRegister, actor: str = "attestor_agent") -> InferenceRecord:
        inf_id = inf_in.inference_id or f"I-{uuid.uuid4().hex[:6].upper()}"

        record = InferenceRecord(
            inference_id=inf_id,
            case_id=inf_in.case_id,
            model_id=inf_in.model_id,
            input_sha256=inf_in.input_sha256,
            model_sha256=inf_in.model_sha256,
            preprocess_sha256=inf_in.preprocess_sha256,
            config_sha256=inf_in.config_sha256,
            output_sha256=inf_in.output_sha256,
            sequence=inf_in.sequence,
            timestamp=inf_in.timestamp or utc_now_iso(),
            nonce=inf_in.nonce,
            previous_record_hash=inf_in.previous_record_hash,
            signature=inf_in.signature,
            verification_status="UNVERIFIED",
            predictions_json=json.dumps(inf_in.predictions or {}),
            operational_metadata_json=json.dumps(inf_in.operational_metadata or {})
        )
        db.add(record)

        # Link: Model -> Inference
        if inf_in.model_id:
            edge_id = f"EDGE-{uuid.uuid4().hex[:8].upper()}"
            edge = EvidenceEdge(
                edge_id=edge_id,
                case_id=inf_in.case_id,
                source_node=f"model:{inf_in.model_id}",
                target_node=f"inference:{inf_id}",
                relationship="produced",
                epistemic_status="OBSERVED",
                evidence_ids_json="[]"
            )
            db.add(edge)

        db.commit()
        db.refresh(record)

        AuditService.record_event(
            db=db,
            case_id=inf_in.case_id,
            actor=actor,
            action="INFERENCE_ATTESTATION_REGISTERED",
            asset_id=inf_id,
            result="PENDING_VERIFICATION",
            reason=f"Registered cryptographically bound inference record seq={inf_in.sequence} nonce={inf_in.nonce[:8]}..."
        )
        return record

    @staticmethod
    def verify_inference(
        db: Session,
        inference_id: str,
        public_key_hex: str,
        actor: str = "security_analyst"
    ) -> Dict[str, Any]:
        record = db.query(InferenceRecord).filter(InferenceRecord.inference_id == inference_id).first()
        if not record:
            raise ValueError(f"Inference record {inference_id} not found")

        # Gather previously seen nonces in this case to detect replay
        # Only records that precede this one can make it a replay
        # (otherwise the original would be flagged as a replay of its copy).
        all_nonces = db.query(InferenceRecord.nonce).filter(
            InferenceRecord.case_id == record.case_id,
            InferenceRecord.inference_id != inference_id,
            InferenceRecord.sequence < record.sequence,
        ).all()
        seen_nonces = {n[0] for n in all_nonces}

        payload = {
            "record_id": record.inference_id,
            "sequence": record.sequence,
            "timestamp": record.timestamp,
            "nonce": record.nonce,
            "input_sha256": record.input_sha256,
            "model_sha256": record.model_sha256,
            "preprocess_sha256": record.preprocess_sha256,
            "config_sha256": record.config_sha256,
            "output_sha256": record.output_sha256,
            "previous_record_hash": record.previous_record_hash,
            "signature": record.signature
        }

        res = ReplayAndProvenanceDetector().run(
            record=payload,
            public_key_hex=public_key_hex,
            seen_nonces=seen_nonces,
            expected_sequence=record.sequence
        )
        # Cross-lifecycle binding: the model digest the inference claims must be
        # the digest registered for that model (catches model substitution at runtime).
        if record.model_id and str(getattr(res.status, "value", res.status)) in ("PASS", "FINDING"):
            from app.db.models import ModelAsset
            from app.detectors.base import DetectorFinding, DetectorStatus
            m = db.query(ModelAsset).filter(ModelAsset.model_id == record.model_id).first()
            if m and m.weight_sha256 and record.model_sha256 != m.weight_sha256:
                res.findings.append(DetectorFinding(
                    detector_id=res.detector_id, finding_type="INFERENCE_MODEL_BINDING_MISMATCH",
                    severity="HIGH", evidence_type="CRYPTOGRAPHIC", deterministic=True,
                    explanation=(f"Inference claims model digest {record.model_sha256[:12]}… but model {m.model_id} "
                                 f"is registered with {m.weight_sha256[:12]}…. The output was not produced by the registered model."),
                    observation="model_sha256 in attestation != registered weight_sha256",
                    measurement={"claimed": record.model_sha256, "registered": m.weight_sha256, "model_id": m.model_id},
                ))
                res.status = DetectorStatus.FINDING
        replay_types = {"INFERENCE_REPLAY_ATTACK", "INFERENCE_SEQUENCE_ANOMALY"}
        created_findings = []
        # One detector run feeds two coverage dimensions.
        created_findings += record_check(db, record.case_id, "INFERENCE", inference_id, "D9A_SIGNATURE_BINDING",
                                         res, actor=actor, exclude_finding_types=replay_types)
        created_findings += record_check(db, record.case_id, "INFERENCE", inference_id, "D9B_REPLAY_SEQUENCE",
                                         res, actor=actor, only_finding_types=replay_types)

        types = {f.finding_type for f in res.findings}
        if "INFERENCE_REPLAY_ATTACK" in types:
            record.verification_status = "REPLAY_DETECTED"
        elif "CRYPTOGRAPHIC_SIGNATURE_INVALID" in types:
            record.verification_status = "INVALID_SIGNATURE"
        elif types:
            record.verification_status = "TAMPERED"
        elif str(getattr(res.status, "value", res.status)) == "PASS":
            record.verification_status = "VERIFIED"
        else:
            record.verification_status = "UNVERIFIED"
        db.commit()

        AuditService.record_event(
            db=db,
            case_id=record.case_id,
            actor=actor,
            action="INFERENCE_VERIFIED",
            asset_id=inference_id,
            result=record.verification_status,
            reason=f"Cryptographic verification yielded status: {record.verification_status}"
        )

        return {
            "inference_id": inference_id,
            "verification_status": record.verification_status,
            "findings_count": len(created_findings),
            "findings": [f.finding_type for f in created_findings]
        }
