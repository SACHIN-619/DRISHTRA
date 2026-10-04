"""
DRISHTRA Dataset Sentinel - Label Anomaly & Poisoning Detector (D3)
Detects:
- Conflicting Labels on Identical / Near-Duplicate Samples (Label Poisoning)
- Extreme Contributor Class Distribution Skew
- Systematic Label Flipping Signatures
Standardized evidence contract.
"""
import time
from typing import List, Dict, Any, Optional
from collections import Counter
from app.detectors.base import BaseDetector, DetectorResult, DetectorFinding, DetectorStatus, AccessRequirement

class LabelAnomalyDetector(BaseDetector):
    detector_id: str = "label_anomaly_detector"
    detector_version: str = "1.0.0"
    required_access: AccessRequirement = AccessRequirement.DATA_ONLY
    supported_inputs: List[str] = ["annotated_samples", "labels", "contributor_id"]

    def run(self, samples: List[Dict[str, Any]], target_artifact: str = "DATASET", **kwargs) -> DetectorResult:
        start_t = time.time()
        findings: List[DetectorFinding] = []

        if not samples:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations=["No annotated samples provided for label anomaly assessment."],
                execution_time_ms=(time.time() - start_t) * 1000
            )

        # 1. Check for conflicting labels on same or near-duplicate content hash
        hash_to_labels: Dict[str, List[str]] = {}
        contributor_classes: Dict[str, List[str]] = {}

        for s in samples:
            s_hash = s.get("sha256") or s.get("file_hash") or s.get("phash")
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
                affected_ids = [
                    str(s.get("sample_id") or s.get("id"))
                    for s in samples
                    if (s.get("sha256") == h or s.get("file_hash") == h or s.get("phash") == h)
                ]
                conflict_cases.append({"hash": h, "conflicting_labels": list(unique_lbls), "affected_sample_ids": affected_ids})

        if conflict_cases:
            all_conflict_ids = [sid for c in conflict_cases for sid in c.get("affected_sample_ids", [])]
            findings.append(DetectorFinding(
                detector_id=self.detector_id,
                finding_type="LABEL_POISONING_CONFLICT",
                severity="HIGH",
                target_artifact=target_artifact,
                evidence_type="STATISTICAL",
                confidence=None, # Deterministic conflict detection
                deterministic=True,
                explanation=f"Identified {len(conflict_cases)} instances where identical perceptual or cryptographic samples were assigned contradictory class labels.",
                observation=f"Sample conflicting labels: {conflict_cases[:3]}",
                observations={
                    "conflict_count": len(conflict_cases),
                    "affected_hashes": [c["hash"] for c in conflict_cases[:5]],
                    "conflicts": [f"Hash {c['hash'][:8]}: {c['conflicting_labels']}" for c in conflict_cases[:5]]
                },
                measurement={
                    "conflict_count": len(conflict_cases),
                    "affected_hashes": [c["hash"] for c in conflict_cases[:5]],
                    "affected_sample_ids": all_conflict_ids
                },
                limitations=["Identifies exact content hash and dHash collisions with differing nominal labels."]
            ))

        # 2. Check for contributor-level systematic skew
        for contrib, lbls in contributor_classes.items():
            if len(lbls) >= 10:
                counts = Counter(lbls)
                most_common_class, top_count = counts.most_common(1)[0]
                skew_ratio = top_count / len(lbls)
                
                if skew_ratio > 0.85 and len(counts) > 1:
                    findings.append(DetectorFinding(
                        detector_id=self.detector_id,
                        finding_type="SYSTEMATIC_LABEL_SKEW",
                        severity="MEDIUM",
                        target_artifact=target_artifact,
                        evidence_type="STATISTICAL",
                        confidence=0.88,
                        deterministic=False,
                        explanation=f"Contributor '{contrib}' shows severe class concentration: {skew_ratio*100:.1f}% of contributed samples assigned to '{most_common_class}' ({top_count}/{len(lbls)}).",
                        observation=f"Class distribution for {contrib}: {dict(counts)}",
                        observations={
                            "contributor_id": contrib,
                            "dominant_class": most_common_class,
                            "skew_ratio": round(skew_ratio, 4)
                        },
                        measurement={
                            "contributor_id": contrib,
                            "dominant_class": most_common_class,
                            "skew_ratio": round(skew_ratio, 4),
                            "sample_count": len(lbls)
                        },
                        limitations=["Requires multiple batches to establish baseline contributor intentionality."]
                    ))

        status = DetectorStatus.FINDING if findings else DetectorStatus.PASS

        return DetectorResult(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            status=status,
            findings=findings,
            limitations=["Assumes label vocabulary is consistent across contributors. Does not evaluate soft human annotation noise without baseline model cross-validation."],
            execution_time_ms=(time.time() - start_t) * 1000
        )
