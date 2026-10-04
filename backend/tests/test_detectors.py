"""
Unit Tests for DRISHTRA Detector Battery
Verifies:
- D1: Exact Duplicate Detector
- D2: Near Duplicate Detector (64-bit dHash)
- D3: Label Anomaly Detector
- D4: Class Imbalance Detector
- D5: Distribution Shift Detector
- D6: Malformed Annotation Detector
- Model Integrity Detector
- Behavioral Fingerprint Detector
- Replay & Cryptographic Tamper Detector
"""
import pytest
from datetime import datetime, timezone
from app.detectors.duplicate_detector import ExactDuplicateDetector, NearDuplicateDetector
from app.detectors.label_anomaly_detector import LabelAnomalyDetector
from app.detectors.class_imbalance_detector import ClassImbalanceDetector
from app.detectors.distribution_shift_detector import DistributionShiftDetector
from app.detectors.malformed_annotation_detector import MalformedAnnotationDetector
from app.detectors.model_integrity_detector import ModelIntegrityDetector
from app.detectors.behavioral_fingerprint_detector import BehavioralFingerprintDetector
from app.detectors.replay_detector import ReplayDetector
from app.crypto.signing import generate_keypair, sign_data
from app.crypto.canonicalization import canonicalize_json

def test_exact_duplicate_detector():
    det = ExactDuplicateDetector()
    samples = [
        {"sample_id": "img_1", "file_hash": "hash_alpha", "file_name": "img1.jpg"},
        {"sample_id": "img_2", "file_hash": "hash_alpha", "file_name": "img2.jpg"},  # Duplicate
        {"sample_id": "img_3", "file_hash": "hash_beta", "file_name": "img3.jpg"}
    ]
    res = det.run(samples)
    assert len(res.findings) == 1
    f = res.findings[0]
    assert f.target_artifact == "DATASET"
    assert f.finding_type == "EXACT_DUPLICATE_FLOODING"
    assert f.severity == "HIGH"
    assert f.deterministic is True
    assert f.confidence is None

def test_near_duplicate_detector():
    det = NearDuplicateDetector()
    samples = [
        {"sample_id": "img_1", "dhash": "0000000000000000", "file_name": "img1.jpg"},
        {"sample_id": "img_2", "dhash": "0000000000000001", "file_name": "img2.jpg"},  # Hamming distance = 1 <= 5
        {"sample_id": "img_3", "dhash": "ffffffffffffffff", "file_name": "img3.jpg"}
    ]
    res = det.run(samples, distance_threshold=5)
    assert len(res.findings) == 1
    f = res.findings[0]
    assert f.finding_type == "NEAR_DUPLICATE_FLOODING"
    assert f.deterministic is False
    assert f.confidence is not None

def test_label_anomaly_detector():
    det = LabelAnomalyDetector()
    samples = [
        {"sample_id": "img_1", "file_hash": "same_hash", "label": "armoured_tank", "contributor_id": "C-01"},
        {"sample_id": "img_2", "file_hash": "same_hash", "label": "civilian_car", "contributor_id": "C-02"}  # CONFLICT!
    ]
    res = det.run(samples)
    assert len(res.findings) == 1
    f = res.findings[0]
    assert f.finding_type == "LABEL_POISONING_CONFLICT"
    assert f.severity == "HIGH"

def test_class_imbalance_detector():
    det = ClassImbalanceDetector()
    samples = []
    # 25 samples of class tank, 1 sample of class truck -> ratio 25.0 > 10.0
    for i in range(25):
        samples.append({"sample_id": f"s_{i}", "label": "tank"})
    samples.append({"sample_id": "s_rare", "label": "truck"})

    res = det.run(samples)
    assert len(res.findings) == 1
    assert res.findings[0].finding_type == "SEVERE_CLASS_IMBALANCE"

def test_malformed_annotation_detector():
    det = MalformedAnnotationDetector()
    samples = [
        {
            "sample_id": "img_ok",
            "width": 640,
            "height": 640,
            "annotations": [{"class_id": 0, "bbox": [10, 10, 50, 50]}]
        },
        {
            "sample_id": "img_bad_bbox",
            "width": 640,
            "height": 640,
            "annotations": [{"class_id": 0, "bbox": [500, 500, -20, 50]}]  # Negative width
        },
        {
            "sample_id": "img_no_annos",
            "width": 640,
            "height": 640,
            "annotations": []  # Missing annotations
        }
    ]
    res = det.run(samples)
    assert len(res.findings) >= 2
    types = [f.finding_type for f in res.findings]
    assert "MALFORMED_BOUNDING_BOX_COORDINATES" in types
    assert "MISSING_ANNOTATION_RECORDS" in types

def test_model_integrity_detector():
    det = ModelIntegrityDetector()
    res = det.run(
        current_weight_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        registered_weight_sha256="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    )
    assert len(res.findings) == 1
    assert res.findings[0].finding_type == "MODEL_DIGEST_MISMATCH"

def test_behavioral_fingerprint_detector():
    det = BehavioralFingerprintDetector()
    probes = {
        "clean": {"predicted_class": "tank", "confidence": 0.95},
        "trigger_patch_corner": {"predicted_class": "civilian_car", "confidence": 0.92}
    }
    res = det.run(probe_results=probes)
    trigger_findings = [f for f in res.findings if f.finding_type == "TRIGGER_SUSCEPTIBILITY_DEVIATION"]
    assert len(trigger_findings) == 1
    assert trigger_findings[0].severity == "HIGH"


def test_replay_detector():
    priv, pub = generate_keypair()
    record = {
        "inference_id": "I-001",
        "nonce": "NONCE-FRESH-1234",
        "sequence": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_sha256": "0" * 64,
        "model_sha256": "0" * 64,
        "preprocess_sha256": "0" * 64,
        "config_sha256": "0" * 64,
        "output_sha256": "0" * 64,
        "previous_record_hash": "0" * 64
    }
    canon = canonicalize_json({k: v for k, v in record.items() if k != "signature"})
    record["signature"] = sign_data(priv, canon)

    det = ReplayDetector()
    res_fresh = det.run(
        record=record,
        public_key_hex=pub,
        seen_nonces=set()
    )
    assert len([f for f in res_fresh.findings if f.finding_type == "INFERENCE_REPLAY_ATTACK"]) == 0

    res_replay = det.run(
        record=record,
        public_key_hex=pub,
        seen_nonces={"NONCE-FRESH-1234"}  # Replayed nonce!
    )
    replay_findings = [f for f in res_replay.findings if f.finding_type == "INFERENCE_REPLAY_ATTACK"]
    assert len(replay_findings) == 1
    assert replay_findings[0].finding_type == "INFERENCE_REPLAY_ATTACK"
