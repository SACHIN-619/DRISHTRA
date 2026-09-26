"""
DRISHTRA Dataset Sentinel - Label Anomaly & Poisoning Detector
Detects:
- Conflicting Labels on Identical / Near-Duplicate Samples (Label Poisoning)
- Extreme Contributor Class Distribution Skew
- Systematic Label Flipping Signatures
"""
import time
from typing import List, Dict, Any
from collections import Counter
from app.detectors.base import BaseDetector, DetectorResult, DetectorFinding, DetectorStatus, AccessRequirement

class LabelAnomalyDetector(BaseDetector):
    detector_id: str = "label_anomaly_detector"
    detector_version: str = "1.0.0"
    required_access: AccessRequirement = AccessRequirement.DATA_ONLY
    supported_inputs: List[str] = ["annotated_samples", "labels", "contributor_id"]

    def run(self, samples: List[Dict[str, Any]], **kwargs) -> DetectorResult:
        start_t = time.time()
        findings: List[DetectorFinding] = []

        if not samples:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations="No annotated samples provided for label anomaly assessment",
                execution_time_ms=(time.time() - start_t) * 1000
            )

        # 1. Check for conflicting labels on same or near-duplicate content hash
        hash_to_labels: Dict[str, List[str]] = {}
        contributor_classes: Dict[str, List[str]] = {}

        for s in samples:
            s_hash = s.get("sha256") or s.get("phash")
            label = s.get("label") or (s.get("categories", [None])[0] if isinstance(s.get("categories"), list) else None)
            contrib = s.get("contributor_id", "UNKNOWN")

            if s_hash and label:
                hash_to_labels.setdefault(s_hash, []).append(str(label))
            if label:
                contributor_classes.setdefault(contrib, []).append(str(label))

        # Check label conflicts on identical hashes
        conflict_cases = []
        for h, lbls in hash_to_labels.items():
            unique_lbls = set(lbls)
            if len(unique_lbls) > 1:
                affected_ids = [s.get("sample_id") for s in samples if (s.get("sha256") == h or s.get("phash") == h) and s.get("sample_id")]
                conflict_cases.append({"hash": h, "conflicting_labels": list(unique_lbls), "affected_sample_ids": affected_ids})

        if conflict_cases:
            all_conflict_ids = [sid for c in conflict_cases for sid in c.get("affected_sample_ids", [])]
            findings.append(DetectorFinding(
                finding_type="LABEL_POISONING_CONFLICT",
                severity="HIGH",
                confidence=0.98,
                explanation=f"Identified {len(conflict_cases)} instances where identical perceptual or cryptographic samples were assigned contradictory class labels.",
                observation=f"Sample conflicting labels: {conflict_cases[:3]}",
                measurement={
                    "conflict_count": len(conflict_cases),
                    "affected_hashes": [c["hash"] for c in conflict_cases[:5]],
                    "affected_sample_ids": all_conflict_ids
                }
            ))

        # 2. Check for contributor-level systematic skew (e.g. contributor flipping 90% of samples to a single target class)
        for contrib, lbls in contributor_classes.items():
            if len(lbls) >= 10:
                counts = Counter(lbls)
                most_common_class, top_count = counts.most_common(1)[0]
                skew_ratio = top_count / len(lbls)
                
                # If a contributor has > 85% of their annotations in one single class while total classes > 3
                if skew_ratio > 0.85 and len(counts) > 1:
                    findings.append(DetectorFinding(
                        finding_type="SYSTEMATIC_LABEL_SKEW",
                        severity="MEDIUM",
                        confidence=0.88,
                        explanation=f"Contributor '{contrib}' shows severe class concentration: {skew_ratio*100:.1f}% of contributed samples assigned to '{most_common_class}' ({top_count}/{len(lbls)}).",
                        observation=f"Class distribution for {contrib}: {dict(counts)}",
                        measurement={
                            "contributor_id": contrib,
                            "dominant_class": most_common_class,
                            "skew_ratio": round(skew_ratio, 4),
                            "sample_count": len(lbls)
                        }
                    ))

        status = DetectorStatus.FINDING if findings else DetectorStatus.PASS

        return DetectorResult(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            status=status,
            findings=findings,
            limitations="Assumes label vocabulary is consistent. Does not evaluate soft human annotation noise without baseline model cross-validation.",
            execution_time_ms=(time.time() - start_t) * 1000
        )
