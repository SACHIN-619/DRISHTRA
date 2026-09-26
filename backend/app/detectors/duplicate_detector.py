"""
DRISHTRA Dataset Sentinel - Duplicate Detectors
Exact Duplicate Detector (SHA-256) & Near-Duplicate Flooding Detector (Perceptual dHash)
"""
import time
import hashlib
from typing import List, Dict, Any, Tuple
import numpy as np
from PIL import Image
from app.detectors.base import BaseDetector, DetectorResult, DetectorFinding, DetectorStatus, AccessRequirement

class ExactDuplicateDetector(BaseDetector):
    detector_id: str = "exact_duplicate_detector"
    detector_version: str = "1.0.0"
    required_access: AccessRequirement = AccessRequirement.DATA_ONLY
    supported_inputs: List[str] = ["dataset_samples", "file_list"]

    def run(self, samples: List[Dict[str, Any]], **kwargs) -> DetectorResult:
        start_t = time.time()
        findings: List[DetectorFinding] = []
        
        if not samples:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations="No samples provided for exact duplicate inspection",
                execution_time_ms=(time.time() - start_t) * 1000
            )

        hash_map: Dict[str, List[str]] = {}
        for s in samples:
            sample_id = s.get("id") or s.get("sample_id")
            s_hash = s.get("sha256")
            if not s_hash and "content" in s:
                content = s["content"]
                if isinstance(content, str):
                    content = content.encode('utf-8')
                s_hash = hashlib.sha256(content).hexdigest()
            elif not s_hash:
                continue
            
            hash_map.setdefault(s_hash, []).append(sample_id)

        duplicates = {h: ids for h, ids in hash_map.items() if len(ids) > 1}
        dup_count = sum(len(ids) - 1 for ids in duplicates.values())

        if dup_count > 0:
            dup_ratio = dup_count / len(samples)
            severity = "HIGH" if dup_ratio > 0.05 else "MEDIUM"
            findings.append(DetectorFinding(
                finding_type="EXACT_DUPLICATE_FLOODING",
                severity=severity,
                confidence=1.0, # Cryptographic SHA-256 collision is virtually impossible by accident
                explanation=f"Detected {dup_count} exact byte-level duplicate sample(s) across {len(duplicates)} collision clusters ({dup_ratio*100:.1f}% of dataset).",
                observation=f"Sample IDs involved in duplicate clusters: {list(duplicates.values())[:5]}",
                measurement={
                    "total_samples": len(samples),
                    "duplicate_count": dup_count,
                    "duplicate_ratio": round(dup_ratio, 4),
                    "cluster_count": len(duplicates),
                    "duplicate_sample_ids": [id for ids in duplicates.values() for id in ids]
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
            limitations="Assumes sample byte representation is accessible. Cannot detect compressed or cropped variants without perceptual hashing.",
            execution_time_ms=(time.time() - start_t) * 1000
        )


class NearDuplicateDetector(BaseDetector):
    detector_id: str = "near_duplicate_detector"
    detector_version: str = "1.0.0"
    required_access: AccessRequirement = AccessRequirement.DATA_ONLY
    supported_inputs: List[str] = ["dataset_images", "perceptual_hashes"]

    def compute_dhash(self, image: Image.Image, hash_size: int = 8) -> str:
        """Computes difference hash (dHash) for an image."""
        resized = image.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = np.array(resized)
        difference = pixels[:, 1:] > pixels[:, :-1]
        decimal_val = 0
        hex_str = []
        for index, value in enumerate(difference.flatten()):
            if value:
                decimal_val += 2**(index % 8)
            if (index % 8) == 7:
                hex_str.append(hex(decimal_val)[2:].rjust(2, '0'))
                decimal_val = 0
        return "".join(hex_str)

    def hamming_distance(self, s1: str, s2: str) -> int:
        """Computes bitwise Hamming distance between two hex hashes."""
        return bin(int(s1, 16) ^ int(s2, 16)).count('1')

    def run(self, samples: List[Dict[str, Any]], distance_threshold: int = 5, **kwargs) -> DetectorResult:
        start_t = time.time()
        findings: List[DetectorFinding] = []

        if not samples:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations="No samples with perceptual hashes or image data provided",
                execution_time_ms=(time.time() - start_t) * 1000
            )

        hashes: List[Tuple[str, str]] = [] # (sample_id, hash)
        for s in samples:
            s_id = s.get("id") or s.get("sample_id")
            p_hash = s.get("phash") or s.get("dhash")
            if not p_hash and "image" in s and isinstance(s["image"], Image.Image):
                p_hash = self.compute_dhash(s["image"])
            if p_hash:
                hashes.append((s_id, p_hash))

        if len(hashes) < 2:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.PASS,
                limitations="Insufficient perceptual hashes to evaluate near-duplicates",
                execution_time_ms=(time.time() - start_t) * 1000
            )

        near_pairs = []
        for i in range(len(hashes)):
            for j in range(i + 1, len(hashes)):
                id1, h1 = hashes[i]
                id2, h2 = hashes[j]
                dist = self.hamming_distance(h1, h2)
                if dist <= distance_threshold:
                    near_pairs.append((id1, id2, dist))

        if near_pairs:
            unique_near_ids = set()
            for id1, id2, _ in near_pairs:
                unique_near_ids.add(id1)
                unique_near_ids.add(id2)
            
            ratio = len(unique_near_ids) / len(samples)
            severity = "HIGH" if ratio > 0.08 else "MEDIUM"
            findings.append(DetectorFinding(
                finding_type="NEAR_DUPLICATE_FLOODING",
                severity=severity,
                confidence=0.92,
                explanation=f"Identified {len(near_pairs)} near-duplicate sample pairs within perceptual Hamming distance ≤ {distance_threshold} ({len(unique_near_ids)} affected images).",
                observation=f"Perceptual collision clusters identified across contributors. Sample pairs: {near_pairs[:3]}",
                measurement={
                    "near_pair_count": len(near_pairs),
                    "affected_sample_count": len(unique_near_ids),
                    "affected_ratio": round(ratio, 4),
                    "hamming_threshold": distance_threshold,
                    "affected_sample_ids": list(unique_near_ids)
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
            limitations="Based on dHash 64-bit perceptual hashing. Rotations > 15 deg or heavy spatial crops may bypass distance threshold.",
            execution_time_ms=(time.time() - start_t) * 1000
        )
