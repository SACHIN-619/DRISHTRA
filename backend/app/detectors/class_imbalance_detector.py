"""
DRISHTRA Dataset Sentinel - Class Imbalance Detector (D4)
Evaluates target class representation across multi-contributor splits:
- Class frequency counts and class percentage distribution
- Imbalance ratio = max_count / min_count
- Identifies critical tactical classes starved of samples (< 2% or ratio > 10)
Standardized deterministic evidence contract.
"""
import time
from typing import List, Dict, Any, Optional
from collections import Counter
from app.detectors.base import BaseDetector, DetectorResult, DetectorFinding, DetectorStatus, AccessRequirement

class ClassImbalanceDetector(BaseDetector):
    detector_id: str = "class_imbalance_detector"
    detector_version: str = "1.0.0"
    required_access: AccessRequirement = AccessRequirement.DATA_ONLY
    supported_inputs: List[str] = ["annotated_samples", "labels", "classes"]

    def run(self, samples: List[Dict[str, Any]], target_artifact: str = "DATASET", **kwargs) -> DetectorResult:
        start_t = time.time()
        findings: List[DetectorFinding] = []

        if not samples:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations=["No sample records provided for class distribution evaluation."],
                execution_time_ms=(time.time() - start_t) * 1000
            )

        labels = []
        for s in samples:
            lbl = s.get("label")
            if lbl:
                labels.append(str(lbl))
            elif "annotations" in s and isinstance(s["annotations"], list):
                for ann in s["annotations"]:
                    if isinstance(ann, dict) and "class_name" in ann:
                        labels.append(str(ann["class_name"]))
            elif "boxes" in s and isinstance(s["boxes"], list):
                for b in s["boxes"]:
                    if isinstance(b, dict) and "class_name" in b:
                        labels.append(str(b["class_name"]))

        if not labels:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations=["No class labels found in the dataset samples."],
                execution_time_ms=(time.time() - start_t) * 1000
            )

        counts = Counter(labels)
        total_annotations = len(labels)
        class_percentages = {cls: round((cnt / total_annotations) * 100, 2) for cls, cnt in counts.items()}

        sorted_counts = counts.most_common()
        max_class, max_count = sorted_counts[0]
        min_class, min_count = sorted_counts[-1]

        imbalance_ratio = round(max_count / max(1, min_count), 2)
        starved_classes = [cls for cls, pct in class_percentages.items() if pct < 3.0 and len(counts) > 2]

        if imbalance_ratio > 10.0 or starved_classes:
            severity = "HIGH" if imbalance_ratio > 25.0 or any(class_percentages[c] < 1.0 for c in starved_classes) else "MEDIUM"
            findings.append(DetectorFinding(
                detector_id=self.detector_id,
                finding_type="SEVERE_CLASS_IMBALANCE",
                severity=severity,
                target_artifact=target_artifact,
                evidence_type="STATISTICAL",
                confidence=None,
                deterministic=True,
                explanation=(
                    f"Dataset exhibits extreme class imbalance (ratio {imbalance_ratio}:1 between dominant '{max_class}' "
                    f"({counts[max_class]} samples, {class_percentages[max_class]}%) and minority '{min_class}' "
                    f"({counts[min_class]} samples, {class_percentages[min_class]}%)). Starved classes: {starved_classes or ['None']}."
                ),
                observation=f"Dominant: '{max_class}' ({class_percentages[max_class]}%), Minority: '{min_class}' ({class_percentages[min_class]}%), Imbalance Ratio: {imbalance_ratio}:1",
                observations={
                    "imbalance_ratio": imbalance_ratio,
                    "dominant_class": max_class,
                    "minority_class": min_class,
                    "starved_classes": starved_classes
                },
                measurement={
                    "total_annotations": total_annotations,
                    "class_counts": dict(counts),
                    "class_percentages": class_percentages,
                    "imbalance_ratio": imbalance_ratio,
                    "starved_classes": starved_classes
                },
                limitations=["Deterministic counting over provided split. Does not account for few-shot pre-training baselines."]
            ))
            status = DetectorStatus.FINDING
        else:
            status = DetectorStatus.PASS

        return DetectorResult(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            status=status,
            findings=findings,
            limitations=["Evaluates nominal annotation frequencies. Complex multi-label overlaps may require per-pixel segmentation weighting."],
            execution_time_ms=(time.time() - start_t) * 1000
        )
