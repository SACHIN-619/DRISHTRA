"""
DRISHTRA Dataset Sentinel - Missing & Malformed Annotation Detector (D6)
Detects:
- Missing annotations / unannotated samples
- Invalid or out-of-range class IDs
- Out-of-bounds, negative, or degenerate bounding boxes (w <= 0, h <= 0, NaN/Inf)
- Malformed annotation payload structures
Deterministic evidence contract.
"""
import time
import math
from typing import List, Dict, Any, Optional
from app.detectors.base import BaseDetector, DetectorResult, DetectorFinding, DetectorStatus, AccessRequirement

class MalformedAnnotationDetector(BaseDetector):
    detector_id: str = "malformed_annotation_detector"
    detector_version: str = "1.0.0"
    required_access: AccessRequirement = AccessRequirement.DATA_ONLY
    supported_inputs: List[str] = ["annotated_samples", "bounding_boxes"]

    def run(self, samples: List[Dict[str, Any]], target_artifact: str = "DATASET", **kwargs) -> DetectorResult:
        start_t = time.time()
        findings: List[DetectorFinding] = []

        if not samples:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations=["No sample records provided for syntax and coordinate integrity inspection."],
                execution_time_ms=(time.time() - start_t) * 1000
            )

        missing_annotation_samples = []
        malformed_coord_samples = []
        invalid_class_samples = []

        for s in samples:
            sample_id = s.get("sample_id") or s.get("id") or "UNKNOWN_ID"
            w = float(s.get("width", 640))
            h = float(s.get("height", 640))

            anns = s.get("annotations") or s.get("boxes") or []
            label = s.get("label")

            # Check 1: Missing annotations
            if not anns and not label:
                missing_annotation_samples.append(sample_id)
                continue

            # Check 2: Malformed coordinates
            for ann in anns:
                bbox = None
                cls_id = None
                if isinstance(ann, dict):
                    bbox = ann.get("bbox") or [ann.get("x_min", 0), ann.get("y_min", 0), ann.get("width", 0), ann.get("height", 0)]
                    cls_id = ann.get("class_id")
                elif isinstance(ann, (list, tuple)) and len(ann) >= 4:
                    bbox = ann[:4]

                if bbox:
                    try:
                        coords = [float(c) for c in bbox]
                        if len(coords) < 4:
                            malformed_coord_samples.append((sample_id, "Fewer than 4 coordinates"))
                        elif any(math.isnan(c) or math.isinf(c) for c in coords):
                            malformed_coord_samples.append((sample_id, "Contains NaN or Inf"))
                        elif coords[2] <= 0 or coords[3] <= 0:
                            malformed_coord_samples.append((sample_id, f"Degenerate box dimensions: w={coords[2]}, h={coords[3]}"))
                        elif coords[0] < -5.0 or coords[1] < -5.0:
                            malformed_coord_samples.append((sample_id, f"Negative origin: x={coords[0]}, y={coords[1]}"))
                        elif coords[0] >= w or coords[1] >= h:
                            malformed_coord_samples.append((sample_id, f"Box origin outside the image: x={coords[0]} (w={w}), y={coords[1]} (h={h})"))
                        elif coords[0] + coords[2] > w * 1.05 or coords[1] + coords[3] > h * 1.05:
                            malformed_coord_samples.append((sample_id, f"Box extends beyond the image: x+w={coords[0] + coords[2]} > {w} or y+h={coords[1] + coords[3]} > {h}"))
                    except (ValueError, TypeError) as ex:
                        malformed_coord_samples.append((sample_id, f"Type conversion error: {str(ex)}"))

                # Check 3: Invalid class id
                if cls_id is not None:
                    try:
                        c_num = int(cls_id)
                        if c_num < 0 or c_num > 10000:
                            invalid_class_samples.append((sample_id, f"Class ID out of range: {c_num}"))
                    except Exception:
                        invalid_class_samples.append((sample_id, f"Non-numeric class ID: {cls_id}"))

        if missing_annotation_samples:
            findings.append(DetectorFinding(
                detector_id=self.detector_id,
                finding_type="MISSING_ANNOTATION_RECORDS",
                severity="MEDIUM",
                target_artifact=target_artifact,
                evidence_type="METADATA",
                confidence=None,
                deterministic=True,
                explanation=f"Detected {len(missing_annotation_samples)} completely unannotated sample record(s).",
                observation=f"Unannotated sample IDs: {missing_annotation_samples[:5]}",
                observations={"unannotated_count": len(missing_annotation_samples), "samples": missing_annotation_samples[:10]},
                measurement={"missing_count": len(missing_annotation_samples), "total_samples": len(samples)},
                limitations=["Deterministic syntax evaluation."]
            ))

        if malformed_coord_samples:
            findings.append(DetectorFinding(
                detector_id=self.detector_id,
                finding_type="MALFORMED_BOUNDING_BOX_COORDINATES",
                severity="HIGH",
                target_artifact=target_artifact,
                evidence_type="METADATA",
                confidence=None,
                deterministic=True,
                explanation=f"Detected {len(malformed_coord_samples)} malformed, negative, or degenerate bounding box coordinate(s).",
                observation=f"Sample coordinate anomalies: {malformed_coord_samples[:3]}",
                observations={"malformed_count": len(malformed_coord_samples), "anomalies": malformed_coord_samples[:10]},
                measurement={"malformed_count": len(malformed_coord_samples), "total_samples": len(samples)},
                limitations=["Evaluates geometry bounds against declared image resolution."]
            ))

        if invalid_class_samples:
            findings.append(DetectorFinding(
                detector_id=self.detector_id,
                finding_type="INVALID_CLASS_IDENTIFIER",
                severity="HIGH",
                target_artifact=target_artifact,
                evidence_type="METADATA",
                confidence=None,
                deterministic=True,
                explanation=f"Detected {len(invalid_class_samples)} sample(s) with out-of-range or non-integer class identifiers.",
                observation=f"Sample invalid classes: {invalid_class_samples[:3]}",
                observations={"invalid_class_count": len(invalid_class_samples)},
                measurement={"invalid_count": len(invalid_class_samples)},
                limitations=["Checks against standard non-negative integer classification space."]
            ))

        status = DetectorStatus.FINDING if findings else DetectorStatus.PASS

        return DetectorResult(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            status=status,
            findings=findings,
            limitations=["Validates syntactic, numerical, and geometric consistency. Does not verify whether box tightly bounds physical target."],
            execution_time_ms=(time.time() - start_t) * 1000
        )
