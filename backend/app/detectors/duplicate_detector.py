"""
DRISHTRA Dataset Sentinel - Duplicate Detectors (D1 & D2)
Exact Duplicate Detector (D1: SHA-256) & Near-Duplicate Flooding Detector (D2: Perceptual dHash)
Conforms to standardized evidence contract: target_artifact, deterministic flag, and limitations.
"""
import time
import hashlib
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from PIL import Image
from app.detectors.base import BaseDetector, DetectorResult, DetectorFinding, DetectorStatus, AccessRequirement
from app.ingestion.dataset_parsers import compute_dhash_64, pseudo_dhash_from_meta

class ExactDuplicateDetector(BaseDetector):
    detector_id: str = "exact_duplicate_detector"
    detector_version: str = "1.0.0"
    required_access: AccessRequirement = AccessRequirement.DATA_ONLY
    supported_inputs: List[str] = ["dataset_samples", "file_list"]

    def run(self, samples: List[Dict[str, Any]], target_artifact: str = "DATASET", **kwargs) -> DetectorResult:
        start_t = time.time()
        findings: List[DetectorFinding] = []
        
        if not samples:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations=["No samples provided for exact duplicate inspection"],
                execution_time_ms=(time.time() - start_t) * 1000
            )

        hash_map: Dict[str, List[str]] = {}
        for s in samples:
            sample_id = str(s.get("id") or s.get("sample_id") or "UNKNOWN")
            s_hash = s.get("sha256") or s.get("file_hash")
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
            all_dup_ids = [sid for ids in duplicates.values() for sid in ids]
            findings.append(DetectorFinding(
                detector_id=self.detector_id,
                finding_type="EXACT_DUPLICATE_FLOODING",
                severity=severity,
                target_artifact=target_artifact,
                evidence_type="CRYPTOGRAPHIC",
                confidence=None, # Deterministic SHA-256 collision check
                deterministic=True,
                explanation=f"Detected {dup_count} exact byte-level duplicate sample(s) across {len(duplicates)} collision clusters ({dup_ratio*100:.1f}% of dataset).",
                observation=f"Sample IDs involved in duplicate clusters: {list(duplicates.values())[:5]}",
                observations={
                    "total_samples": len(samples),
                    "duplicate_count": dup_count,
                    "cluster_count": len(duplicates),
                    "duplicate_sample_ids": all_dup_ids[:20]
                },
                measurement={
                    "total_samples": len(samples),
                    "duplicate_count": dup_count,
                    "duplicate_ratio": round(dup_ratio, 4),
                    "cluster_count": len(duplicates),
                    "duplicate_sample_ids": all_dup_ids
                },
                limitations=["Assumes sample byte representation is accessible. Cannot detect compressed or cropped variants without perceptual hashing."]
            ))
            status = DetectorStatus.FINDING
        else:
            status = DetectorStatus.PASS

        return DetectorResult(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            status=status,
            findings=findings,
            limitations=["Assumes sample byte representation is accessible. Cannot detect compressed or cropped variants without perceptual hashing."],
            execution_time_ms=(time.time() - start_t) * 1000
        )


class NearDuplicateDetector(BaseDetector):
    detector_id: str = "near_duplicate_detector"
    detector_version: str = "1.0.0"
    required_access: AccessRequirement = AccessRequirement.DATA_ONLY
    supported_inputs: List[str] = ["dataset_images", "perceptual_hashes"]

    def compute_dhash(self, image: Image.Image, hash_size: int = 8) -> str:
        """Computes difference hash (dHash) for an image."""
        return compute_dhash_64(image, hash_size=hash_size)

    def hamming_distance(self, s1: str, s2: str) -> int:
        """Computes bitwise Hamming distance between two hex hashes."""
        try:
            return bin(int(s1, 16) ^ int(s2, 16)).count('1')
        except Exception:
            return 64

    def run(self, samples: List[Dict[str, Any]], distance_threshold: int = 5, target_artifact: str = "DATASET", **kwargs) -> DetectorResult:
        start_t = time.time()
        findings: List[DetectorFinding] = []

        if not samples:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations=["No samples with perceptual hashes or image data provided."],
                execution_time_ms=(time.time() - start_t) * 1000
            )

        hashes: List[Tuple[str, str]] = [] # (sample_id, hash)
        for s in samples:
            s_id = str(s.get("id") or s.get("sample_id") or "UNKNOWN")
            p_hash = s.get("phash") or s.get("dhash")
            if not p_hash and "image" in s and isinstance(s["image"], Image.Image):
                p_hash = self.compute_dhash(s["image"])
            # No pixels, no perceptual hash: a hash of the file *name* is not evidence
            # about image content, so such samples are excluded (check becomes NOT_TESTED).
            if p_hash:
                hashes.append((s_id, p_hash))

        if len(hashes) < 2:
            return DetectorResult(
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                status=DetectorStatus.NOT_AVAILABLE,
                limitations=["Insufficient perceptual hashes (< 2): images were not supplied, so near-duplicate analysis could not run."],
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
                detector_id=self.detector_id,
                finding_type="NEAR_DUPLICATE_FLOODING",
                severity=severity,
                target_artifact=target_artifact,
                evidence_type="STATISTICAL",
                confidence=0.92,
                deterministic=False, # Perceptual distance is a heuristic statistical distance
                explanation=f"Identified {len(near_pairs)} near-duplicate sample pairs within perceptual Hamming distance <= {distance_threshold} ({len(unique_near_ids)} affected images).",
                observation=f"Perceptual collision clusters identified across contributors. Sample pairs: {near_pairs[:3]}",
                observations={
                    "near_pair_count": len(near_pairs),
                    "affected_sample_count": len(unique_near_ids),
                    "hamming_threshold": distance_threshold,
                    "pairs": [f"{p[0]}<->{p[1]} (dist={p[2]})" for p in near_pairs[:5]]
                },
                measurement={
                    "near_pair_count": len(near_pairs),
                    "affected_sample_count": len(unique_near_ids),
                    "affected_ratio": round(ratio, 4),
                    "hamming_threshold": distance_threshold,
                    "affected_sample_ids": list(unique_near_ids)
                },
                limitations=["Based on dHash 64-bit perceptual hashing. Rotations > 15 deg or heavy spatial crops may bypass distance threshold."]
            ))
            status = DetectorStatus.FINDING
        else:
            status = DetectorStatus.PASS

        return DetectorResult(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            status=status,
            findings=findings,
            limitations=["Based on dHash 64-bit perceptual hashing. Rotations > 15 deg or heavy spatial crops may bypass distance threshold."],
            execution_time_ms=(time.time() - start_t) * 1000
        )
