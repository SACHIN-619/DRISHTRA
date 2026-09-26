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

class ModelService:
    @staticmethod
    def register_model(db: Session, model_in: ModelRegister, weight_bytes: Optional[bytes] = None, actor: str = "analyst") -> ModelAsset:
        model_id = f"M-{uuid.uuid4().hex[:6].upper()}"
        
        # Calculate weight SHA-256
        if weight_bytes:
            weight_digest = hashlib.sha256(weight_bytes).hexdigest()
        else:
            # Deterministic simulation hash for registration manifest
            seed = f"{model_id}:{model_in.name}:{model_in.version}:{model_in.architecture}"
            weight_digest = hashlib.sha256(seed.encode('utf-8')).hexdigest()

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
        actor: str = "analyst"
    ) -> List[Finding]:
        model = db.query(ModelAsset).filter(ModelAsset.model_id == model_id).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")

        created_findings = []

        # 1. Model Digest & Weight Integrity Check
        int_det = ModelIntegrityDetector()
        res_int = int_det.run(
            current_weight_sha256=current_weight_sha256,
            registered_weight_sha256=model.weight_sha256,
            reference_model_sha256=None
        )
        for df in res_int.findings:
            f_id = f"FND-{uuid.uuid4().hex[:8].upper()}"
            finding = Finding(
                finding_id=f_id,
                case_id=model.case_id,
                asset_id=model_id,
                asset_type="MODEL",
                detector_id=int_det.detector_id,
                detector_version=int_det.detector_version,
                finding_type=df.finding_type,
                severity=df.severity,
                confidence=df.confidence,
                status="FINDING",
                explanation=df.explanation,
                limitations=res_int.limitations,
                created_at=utc_now_iso()
            )
            db.add(finding)
            
            ev_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
            ev = Evidence(
                evidence_id=ev_id,
                case_id=model.case_id,
                finding_id=f_id,
                evidence_type="CRYPTOGRAPHIC",
                source_asset=model_id,
                detector=int_det.detector_id,
                observation=df.observation,
                measurement_json=json.dumps(df.measurement),
                confidence=df.confidence,
                timestamp=utc_now_iso(),
                sha256=hashlib.sha256(json.dumps(df.measurement).encode('utf-8')).hexdigest()
            )
            db.add(ev)
            created_findings.append(finding)

        # 2. Behavioral Probe Battery Check
        if probe_responses:
            beh_det = BehavioralFingerprintDetector()
            res_beh = beh_det.run(probe_results=probe_responses)
            for df in res_beh.findings:
                f_id = f"FND-{uuid.uuid4().hex[:8].upper()}"
                finding = Finding(
                    finding_id=f_id,
                    case_id=model.case_id,
                    asset_id=model_id,
                    asset_type="MODEL",
                    detector_id=beh_det.detector_id,
                    detector_version=beh_det.detector_version,
                    finding_type=df.finding_type,
                    severity=df.severity,
                    confidence=df.confidence,
                    status="FINDING",
                    explanation=df.explanation,
                    limitations=res_beh.limitations,
                    created_at=utc_now_iso()
                )
                db.add(finding)
                
                ev_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
                ev = Evidence(
                    evidence_id=ev_id,
                    case_id=model.case_id,
                    finding_id=f_id,
                    evidence_type="BEHAVIORAL",
                    source_asset=model_id,
                    detector=beh_det.detector_id,
                    observation=df.observation,
                    measurement_json=json.dumps(df.measurement),
                    confidence=df.confidence,
                    timestamp=utc_now_iso(),
                    sha256=hashlib.sha256(json.dumps(df.measurement).encode('utf-8')).hexdigest()
                )
                db.add(ev)
                created_findings.append(finding)

        db.commit()

        AuditService.record_event(
            db=db,
            case_id=model.case_id,
            actor=actor,
            action="MODEL_SCANNED",
            asset_id=model_id,
            result="COMPLETED",
            reason=f"Executed model integrity and behavioral probe battery; produced {len(created_findings)} findings."
        )
        return created_findings
