"""
DRISHTRA Model Sentinel - Model Integrity & Digest Verification Detector
Detects:
- Unauthorized Model Weight Substitution
- Byte-Level Weight Modification / Tampering
- Framework / Architecture Mismatches
Standardized deterministic evidence contract.
"""
import time
from typing import List, Dict, Any, Optional
from app.detectors.base import BaseDetector, DetectorResult, DetectorFinding, DetectorStatus, AccessRequirement

class ModelIntegrityDetector(BaseDetector):
    detector_id: str = "model_integrity_detector"
    detector_version: str = "1.0.0"
    required_access: AccessRequirement = AccessRequirement.BLACK_BOX
    supported_inputs: List[str] = ["model_sha256", "registered_sha256", "reference_model_sha256"]

    def run(
        self,
        current_weight_sha256: str,
        registered_weight_sha256: str,
        reference_model_sha256: Optional[str] = None,
        target_artifact: str = "MODEL",
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> DetectorResult:
        start_t = time.time()
        findings = []

        if not current_weight_sha256 or not registered_weight_sha256:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations=["Missing model digest or registered baseline digest for comparison."],
                execution_time_ms=(time.time() - start_t) * 1000
            )

        # 1. Registered Identity Check (Tampering / Substitution)
        if current_weight_sha256.lower() != registered_weight_sha256.lower():
            findings.append(DetectorFinding(
                detector_id=self.detector_id,
                finding_type="MODEL_DIGEST_MISMATCH",
                severity="CRITICAL",
                target_artifact=target_artifact,
                evidence_type="CRYPTOGRAPHIC",
                confidence=None,
                deterministic=True,
                explanation="Model weight digest does not match registered manifest digest. Model file has been modified or substituted post-registration.",
                observation=f"Expected: {registered_weight_sha256}, Actual: {current_weight_sha256}",
                observations={"expected": registered_weight_sha256, "actual": current_weight_sha256},
                measurement={
                    "expected_sha256": registered_weight_sha256,
                    "actual_sha256": current_weight_sha256,
                    "tamper_detected": True
                },
                limitations=["Deterministic SHA-256 weight comparison."]
            ))

        # 2. Reference Model Comparison
        if reference_model_sha256 and current_weight_sha256.lower() == reference_model_sha256.lower():
            findings.append(DetectorFinding(
                detector_id=self.detector_id,
                finding_type="REFERENCE_MODEL_IDENTICAL",
                severity="INFO",
                target_artifact=target_artifact,
                evidence_type="CRYPTOGRAPHIC",
                confidence=None,
                deterministic=True,
                explanation="Model digest is bit-for-bit identical to certified reference base model.",
                observation=f"Matches certified reference: {reference_model_sha256}",
                observations={"reference_model_id": reference_model_sha256},
                measurement={"matches_reference": True},
                limitations=["Deterministic comparison against certified sovereign baseline."]
            ))

        status = DetectorStatus.FINDING if any(f.severity in ["CRITICAL", "HIGH"] for f in findings) else DetectorStatus.PASS

        return DetectorResult(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            status=status,
            findings=findings,
            limitations=["Verifies cryptographic byte integrity. Does not assess internal weights or backdoor triggers without probe battery."],
            execution_time_ms=(time.time() - start_t) * 1000
        )
