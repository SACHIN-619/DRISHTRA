"""
DRISHTRA Detector Battery
Standardized detector plugins covering:
- D1: Exact Duplicate (ExactDuplicateDetector)
- D2: Near Duplicate (NearDuplicateDetector)
- D3: Label Conflict & Poisoning (LabelAnomalyDetector)
- D4: Class Imbalance (ClassImbalanceDetector)
- D5: Distribution Shift & Drift (DistributionShiftDetector)
- D6: Missing & Malformed Annotation (MalformedAnnotationDetector)
- M1: Model Weight Integrity (ModelIntegrityDetector)
- M2: Behavioral Trojan Probe Battery (BehavioralFingerprintDetector)
- I1: Replay & Signature Binding (ReplayAndProvenanceDetector)
"""
from app.detectors.base import BaseDetector, DetectorResult, DetectorFinding, DetectorStatus, AccessRequirement
from app.detectors.duplicate_detector import ExactDuplicateDetector, NearDuplicateDetector
from app.detectors.label_anomaly_detector import LabelAnomalyDetector
from app.detectors.class_imbalance_detector import ClassImbalanceDetector
from app.detectors.distribution_shift_detector import DistributionShiftDetector
from app.detectors.malformed_annotation_detector import MalformedAnnotationDetector
from app.detectors.model_integrity_detector import ModelIntegrityDetector
from app.detectors.behavioral_fingerprint_detector import BehavioralFingerprintDetector
from app.detectors.replay_detector import ReplayAndProvenanceDetector
from app.detectors.ood_detector import OutOfDistributionDetector

__all__ = [
    "BaseDetector",
    "DetectorResult",
    "DetectorFinding",
    "DetectorStatus",
    "AccessRequirement",
    "ExactDuplicateDetector",
    "NearDuplicateDetector",
    "LabelAnomalyDetector",
    "ClassImbalanceDetector",
    "DistributionShiftDetector",
    "MalformedAnnotationDetector",
    "ModelIntegrityDetector",
    "BehavioralFingerprintDetector",
    "ReplayAndProvenanceDetector",
    "OutOfDistributionDetector"
]
