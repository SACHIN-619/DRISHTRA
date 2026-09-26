"""
DRISHTRA Operational Shift Sentinel - Distribution Shift & Environmental Drift Detector
Differentiates between:
1. OPERATIONAL_DRIFT (Benign atmospheric, seasonal, terrain, sensor, or illumination variations)
2. MALICIOUS_MANIPULATION (Adversarial high-frequency noise, synthetic pixel anomalies, trigger overlays)
"""
import time
from typing import Dict, Any, List, Optional
import numpy as np
from app.detectors.base import BaseDetector, DetectorResult, DetectorFinding, DetectorStatus, AccessRequirement

class DistributionShiftDetector(BaseDetector):
    detector_id: str = "distribution_shift_detector"
    detector_version: str = "1.0.0"
    required_access: AccessRequirement = AccessRequirement.DATA_ONLY
    supported_inputs: List[str] = ["environmental_metrics", "sensor_metadata", "reference_operational_profile"]

    def run(
        self,
        current_metrics: Dict[str, float], # brightness, contrast, blur_metric, noise_metric, color_entropy
        reference_profile: Optional[Dict[str, Dict[str, float]]] = None, # mean, std per metric
        metadata: Optional[Dict[str, Any]] = None, # sensor_type, terrain, illumination, time_of_day
        **kwargs
    ) -> DetectorResult:
        start_t = time.time()
        findings: List[DetectorFinding] = []

        if not current_metrics:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations="Operational image metrics not provided for shift evaluation.",
                execution_time_ms=(time.time() - start_t) * 1000
            )

        # Default standard daytime surveillance profile if reference not provided
        ref = reference_profile or {
            "brightness": {"mean": 128.0, "std": 35.0},
            "contrast": {"mean": 55.0, "std": 15.0},
            "blur_metric": {"mean": 120.0, "std": 30.0},
            "noise_metric": {"mean": 5.0, "std": 2.5}
        }

        z_scores = {}
        anomalous_metrics = []
        for metric, val in current_metrics.items():
            if metric in ref:
                m_mean = ref[metric]["mean"]
                m_std = max(1e-4, ref[metric]["std"])
                z = (val - m_mean) / m_std
                z_scores[metric] = z
                if abs(z) > 2.5: # 2.5 sigma deviation
                    anomalous_metrics.append((metric, val, z))

        sensor = metadata.get("sensor", "UNKNOWN") if metadata else "UNKNOWN"
        illum = metadata.get("illumination", "DAYLIGHT") if metadata else "DAYLIGHT"
        terrain = metadata.get("terrain", "PLAINS") if metadata else "PLAINS"

        if anomalous_metrics:
            # Check if shifts correlate with declared operational metadata (e.g. night illumination explains low brightness)
            is_benign_drift = False
            drift_reasons = []

            for m, v, z in anomalous_metrics:
                if m == "brightness" and z < -2.0 and illum in ["NIGHT", "DUSK", "DAWN"]:
                    is_benign_drift = True
                    drift_reasons.append(f"Low brightness consistent with declared illumination '{illum}'")
                elif m == "blur_metric" and z < -2.0 and metadata and metadata.get("weather") in ["FOG", "RAIN", "HAZE"]:
                    is_benign_drift = True
                    drift_reasons.append(f"Blur metric consistent with reported weather condition '{metadata.get('weather')}'")

            # Check for high-frequency noise anomaly without natural environmental justification
            noise_z = z_scores.get("noise_metric", 0.0)
            if noise_z > 3.5 and not is_benign_drift:
                findings.append(DetectorFinding(
                    finding_type="SUSPICIOUS_HIGH_FREQUENCY_ANOMALY",
                    severity="HIGH",
                    confidence=0.87,
                    explanation=f"Observed abnormal high-frequency noise perturbation (z={noise_z:.2f}) incompatible with natural sensor degradation. Possible adversarial perturbation.",
                    observation=f"Sensor '{sensor}', Terrain '{terrain}'. Noise metric {current_metrics.get('noise_metric'):.2f} exceeds operational bounds.",
                    measurement={"z_scores": {k: round(v, 2) for k, v in z_scores.items()}, "classification": "INTEGRITY_CONCERN"}
                ))
            elif is_benign_drift:
                findings.append(DetectorFinding(
                    finding_type="OPERATIONAL_ENVIRONMENTAL_DRIFT",
                    severity="LOW",
                    confidence=0.92,
                    explanation=f"Material distribution shift detected ({len(anomalous_metrics)} metrics out of baseline bounds) but correlated with declared operational factors: {'; '.join(drift_reasons)}.",
                    observation=f"Distribution shift accounted for by operational environment ({illum}, {terrain}, {sensor}).",
                    measurement={"z_scores": {k: round(v, 2) for k, v in z_scores.items()}, "classification": "OPERATIONAL_DRIFT"}
                ))
            else:
                findings.append(DetectorFinding(
                    finding_type="UNACCOUNTED_DISTRIBUTION_SHIFT",
                    severity="MEDIUM",
                    confidence=0.82,
                    explanation=f"Observed significant optical shift across {len(anomalous_metrics)} dimension(s) without matching environmental metadata.",
                    observation=f"Unmatched metrics: {[m[0] for m in anomalous_metrics]}",
                    measurement={"z_scores": {k: round(v, 2) for k, v in z_scores.items()}, "classification": "UNACCOUNTED_SHIFT"}
                ))

            status = DetectorStatus.FINDING
        else:
            status = DetectorStatus.PASS

        return DetectorResult(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            status=status,
            findings=findings,
            limitations="Relies on declared operational sensor metadata and empirical image statistics. Unregistered optical conditions may mimic drift.",
            execution_time_ms=(time.time() - start_t) * 1000
        )
