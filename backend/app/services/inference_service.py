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
        all_nonces = db.query(InferenceRecord.nonce).filter(
            InferenceRecord.case_id == record.case_id,
            InferenceRecord.inference_id != inference_id
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

        detector = ReplayAndProvenanceDetector()
        res = detector.run(
            record=payload,
            public_key_hex=public_key_hex,
            seen_nonces=seen_nonces,
            expected_sequence=record.sequence
        )

        created_findings = []
        if res.findings:
            # Mark record status
            if any(f.finding_type == "INFERENCE_REPLAY_ATTACK" for f in res.findings):
                record.verification_status = "REPLAY_DETECTED"
            elif any(f.finding_type == "CRYPTOGRAPHIC_SIGNATURE_INVALID" for f in res.findings):
                record.verification_status = "INVALID_SIGNATURE"
            else:
                record.verification_status = "TAMPERED"

            for df in res.findings:
                f_id = f"FND-{uuid.uuid4().hex[:8].upper()}"
                finding = Finding(
                    finding_id=f_id,
                    case_id=record.case_id,
                    asset_id=inference_id,
                    asset_type="INFERENCE",
                    detector_id=detector.detector_id,
                    detector_version=detector.detector_version,
                    finding_type=df.finding_type,
                    severity=df.severity,
                    confidence=df.confidence,
                    status="FINDING",
                    explanation=df.explanation,
                    limitations=res.limitations,
                    created_at=utc_now_iso()
                )
                db.add(finding)
                
                ev_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
                ev = Evidence(
                    evidence_id=ev_id,
                    case_id=record.case_id,
                    finding_id=f_id,
                    evidence_type="CRYPTOGRAPHIC",
                    source_asset=inference_id,
                    detector=detector.detector_id,
                    observation=df.observation,
                    measurement_json=json.dumps(df.measurement),
                    confidence=df.confidence,
                    timestamp=utc_now_iso(),
                    sha256=hashlib.sha256(json.dumps(df.measurement).encode('utf-8')).hexdigest()
                )
                db.add(ev)
                created_findings.append(finding)
        else:
            record.verification_status = "VERIFIED"

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
