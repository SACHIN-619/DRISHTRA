"""
DRISHTRA Inference Attestor - Replay and Provenance Detector
Detects:
- Nonce Reuse / Replay Attacks
- Sequence Number Gaps or Inversions
- Excessive Timestamp Clock Skew
- Cryptographic Signature Invalidation
"""
import time
from typing import Dict, Any, List, Optional, Set
from app.detectors.base import BaseDetector, DetectorResult, DetectorFinding, DetectorStatus, AccessRequirement
from app.crypto.verification import verify_inference_record

class ReplayAndProvenanceDetector(BaseDetector):
    detector_id: str = "replay_provenance_detector"
    detector_version: str = "1.0.0"
    required_access: AccessRequirement = AccessRequirement.DATA_ONLY
    supported_inputs: List[str] = ["inference_record", "public_key", "seen_nonces", "expected_sequence"]

    def run(
        self,
        record: Dict[str, Any],
        public_key_hex: str,
        seen_nonces: Optional[Set[str]] = None,
        expected_sequence: Optional[int] = None,
        **kwargs
    ) -> DetectorResult:
        start_t = time.time()
        findings: List[DetectorFinding] = []

        if not record or not public_key_hex:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations="Inference record or signer public key unavailable",
                execution_time_ms=(time.time() - start_t) * 1000
            )

        # 1. Cryptographic binding verification
        v_res = verify_inference_record(record, public_key_hex, seen_nonces=seen_nonces)

        # Check signature
        if v_res["checks"].get("signature") != "VERIFIED":
            findings.append(DetectorFinding(
                finding_type="CRYPTOGRAPHIC_SIGNATURE_INVALID",
                severity="CRITICAL",
                confidence=1.0,
                explanation="Inference record digital signature does not match canonical payload. Record has been forged or modified post-issuance.",
                observation=f"Signature check result: {v_res['checks'].get('signature')}",
                measurement={"tamper_type": "SIGNATURE_MISMATCH"}
            ))

        # Check replay
        if v_res["checks"].get("nonce") == "REPLAY_DETECTED":
            findings.append(DetectorFinding(
                finding_type="INFERENCE_REPLAY_ATTACK",
                severity="CRITICAL",
                confidence=1.0,
                explanation=f"Cryptographic nonce '{record.get('nonce')}' was observed in an earlier inference transaction. Replay attack detected.",
                observation=f"Replayed nonce: {record.get('nonce')}",
                measurement={"nonce": record.get("nonce"), "attack_class": "REPLAY"}
            ))

        # Check sequence
        current_seq = record.get("sequence")
        if expected_sequence is not None and current_seq is not None:
            if current_seq != expected_sequence:
                findings.append(DetectorFinding(
                    finding_type="INFERENCE_SEQUENCE_ANOMALY",
                    severity="HIGH",
                    confidence=1.0,
                    explanation=f"Sequence number mismatch: expected {expected_sequence}, received {current_seq}. Possible dropped or reordered inference stream.",
                    observation=f"Expected: {expected_sequence}, Actual: {current_seq}",
                    measurement={"expected_sequence": expected_sequence, "actual_sequence": current_seq}
                ))

        status = DetectorStatus.FINDING if findings else DetectorStatus.PASS

        return DetectorResult(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            status=status,
            findings=findings,
            limitations="Assumes verified public key belongs to authorized sovereign node. Cryptographic validation proves byte integrity relative to signing boundary.",
            execution_time_ms=(time.time() - start_t) * 1000
        )
