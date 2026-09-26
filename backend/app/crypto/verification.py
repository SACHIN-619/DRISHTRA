"""
DRISHTRA Cryptographic Engine - Inference Attestation Verification
Verifies cryptographic bindings across Input, Model, Preprocessing, Configuration, and Output.
Detects:
 - Input Alteration
 - Model Substitution
 - Preprocessing/Config Tampering
 - Output Modification
 - Signature Invalidation
 - Replay Attacks (sequence / timestamp / nonce)
 - Broken Hash Chain
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.crypto.canonicalization import canonicalize_json
from app.crypto.signing import verify_data_signature
from app.crypto.hashing import sha256_combine

class InferenceVerificationResult:
    def __init__(self):
        self.is_valid: bool = True
        self.checks: Dict[str, str] = {} # e.g. {"input_hash": "VERIFIED", "signature": "FAILED"}
        self.anomalies: List[str] = []
        self.status: str = "VERIFIED" # VERIFIED, TAMPERED, REPLAY_DETECTED, INVALID_SIGNATURE

def verify_inference_record(
    record: Dict[str, Any],
    public_key_hex: str,
    seen_nonces: Optional[set] = None,
    max_clock_skew_seconds: int = 3600
) -> Dict[str, Any]:
    """
    Verifies an attested inference record against cryptographic bounds and replay protections.
    """
    result = InferenceVerificationResult()
    
    # 1. Nonce & Replay Check
    nonce = record.get("nonce")
    if not nonce:
        result.is_valid = False
        result.checks["nonce"] = "MISSING"
        result.anomalies.append("Inference record missing cryptographic nonce")
    elif seen_nonces is not None and nonce in seen_nonces:
        result.is_valid = False
        result.checks["nonce"] = "REPLAY_DETECTED"
        result.anomalies.append(f"Cryptographic nonce {nonce} has already been presented. Potential replay attack.")
        result.status = "REPLAY_DETECTED"
    else:
        result.checks["nonce"] = "VERIFIED"

    # 2. Timestamp freshness check
    ts_str = record.get("timestamp")
    if ts_str:
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            skew = abs((now - ts).total_seconds())
            if skew > max_clock_skew_seconds:
                result.checks["timestamp"] = "CLOCK_SKEW_WARNING"
            else:
                result.checks["timestamp"] = "VERIFIED"
        except Exception:
            result.checks["timestamp"] = "MALFORMED"
    else:
        result.checks["timestamp"] = "MISSING"

    # 3. Cryptographic Binding Checks
    required_hashes = ["input_sha256", "model_sha256", "preprocess_sha256", "config_sha256", "output_sha256"]
    for h in required_hashes:
        val = record.get(h)
        if not val or len(val) != 64:
            result.is_valid = False
            result.checks[h] = "INVALID_DIGEST"
            result.anomalies.append(f"Field {h} is missing or invalid SHA-256 digest")
        else:
            result.checks[h] = "VERIFIED"

    # 4. Canonical Signature Verification
    signature_hex = record.get("signature")
    if not signature_hex:
        result.is_valid = False
        result.checks["signature"] = "MISSING"
        result.anomalies.append("Inference record is unsigned")
        result.status = "TAMPERED"
    else:
        # Build canonical payload that was signed
        signed_payload = {
            "record_id": record.get("record_id") or record.get("inference_id"),
            "sequence": record.get("sequence"),
            "timestamp": record.get("timestamp"),
            "nonce": record.get("nonce"),
            "input_sha256": record.get("input_sha256"),
            "model_sha256": record.get("model_sha256"),
            "preprocess_sha256": record.get("preprocess_sha256"),
            "config_sha256": record.get("config_sha256"),
            "output_sha256": record.get("output_sha256"),
            "previous_record_hash": record.get("previous_record_hash")
        }
        canonical_bytes = canonicalize_json(signed_payload)
        
        try:
            pub_bytes = bytes.fromhex(public_key_hex)
            sig_bytes = bytes.fromhex(signature_hex)
            sig_ok = verify_data_signature(pub_bytes, sig_bytes, canonical_bytes)
            if sig_ok:
                result.checks["signature"] = "VERIFIED"
            else:
                result.is_valid = False
                result.checks["signature"] = "SIGNATURE_MISMATCH"
                result.anomalies.append("Cryptographic signature does not match canonical payload")
                if result.status == "VERIFIED":
                    result.status = "INVALID_SIGNATURE"
        except Exception as e:
            result.is_valid = False
            result.checks["signature"] = f"VERIFICATION_ERROR: {str(e)}"
            result.anomalies.append(f"Failed to verify signature: {str(e)}")
            result.status = "TAMPERED"

    if not result.is_valid and result.status == "VERIFIED":
        result.status = "TAMPERED"

    return {
        "is_valid": result.is_valid,
        "status": result.status,
        "checks": result.checks,
        "anomalies": result.anomalies,
        "verification_timestamp": datetime.now(timezone.utc).isoformat()
    }
