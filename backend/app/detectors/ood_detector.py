"""
DRISHTRA Dataset & Input Sentinel - Out-Of-Distribution (OOD) Detector
Evaluates representation distance relative to certified operational in-distribution baseline.
Returns NOT_AVAILABLE when reference baseline or feature representations are missing.
"""
import time
from typing import List, Dict, Any, Optional
import numpy as np
from app.detectors.base import BaseDetector, DetectorResult, DetectorFinding, DetectorStatus, AccessRequirement

class OutOfDistributionDetector(BaseDetector):
    detector_id: str = "ood_detector"
    detector_version: str = "1.0.0"
    required_access: AccessRequirement = AccessRequirement.DATA_ONLY
    supported_inputs: List[str] = ["sample_embeddings", "reference_centroid", "reference_covariance"]

    def run(
        self,
        embeddings: Optional[List[List[float]]] = None,
        reference_mean: Optional[List[float]] = None,
        reference_std: Optional[List[float]] = None,
        threshold_std: float = 3.0,
        **kwargs
    ) -> DetectorResult:
        start_t = time.time()
        findings: List[DetectorFinding] = []

        # Coverage / Availability Verification
        if embeddings is None or len(embeddings) == 0:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations="Feature embeddings unavailable. Black-box extraction required or feature extractor offline.",
                execution_time_ms=(time.time() - start_t) * 1000
            )

        if reference_mean is None:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations="No certified in-distribution baseline reference profile provided for comparison.",
                execution_time_ms=(time.time() - start_t) * 1000
            )

        emb_matrix = np.array(embeddings)
        ref_m = np.array(reference_mean)
        
        # Compute normalized Euclidean distances to reference centroid
        diffs = emb_matrix - ref_m
        if reference_std is not None and len(reference_std) == len(reference_mean):
            ref_s = np.array(reference_std) + 1e-6
            z_scores = np.abs(diffs) / ref_s
            distances = np.mean(z_scores, axis=1)
        else:
            distances = np.linalg.norm(diffs, axis=1)

        # Flag outliers
        baseline_thresh = threshold_std if reference_std is not None else (np.mean(distances) + 2.5 * (np.std(distances) + 1e-6))
        outlier_indices = np.where(distances > baseline_thresh)[0].tolist()
        outlier_count = len(outlier_indices)

        if outlier_count > 0:
            ratio = outlier_count / len(embeddings)
            severity = "HIGH" if ratio > 0.1 else "MEDIUM"
            findings.append(DetectorFinding(
                finding_type="OUT_OF_DISTRIBUTION_INSERTION",
                severity=severity,
                confidence=0.89,
                explanation=f"Detected {outlier_count} sample(s) ({ratio*100:.1f}%) exhibiting extreme feature deviation (> {baseline_thresh:.2f} threshold) from certified operational baseline.",
                observation=f"Sample outlier indices: {outlier_indices[:5]} with max distance {float(np.max(distances)):.2f}",
                measurement={
                    "total_samples": len(embeddings),
                    "outlier_count": outlier_count,
                    "outlier_ratio": round(ratio, 4),
                    "threshold_applied": round(float(baseline_thresh), 3),
                    "max_observed_deviation": round(float(np.max(distances)), 3)
                }
            ))
            status = DetectorStatus.FINDING
        else:
            status = DetectorStatus.PASS

        return DetectorResult(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            status=status,
            findings=findings,
            limitations="Assumes representation space preserves semantic geometry. Linear Gaussian envelope assumptions applied.",
            execution_time_ms=(time.time() - start_t) * 1000
        )
