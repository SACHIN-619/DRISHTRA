"""
DRISHTRA Attack Scenario Factory
Generates reproducible, parameterized attack mutations with verified ground truth:
1. Exact & Near-Duplicate Flooding
2. Label Inversion / Conflict Poisoning
3. Out-Of-Distribution (OOD) Injection
4. Model Weight Substitution & Modification
5. Behavioral Trojan Trigger Injection
6. Inference Record Output Tampering
7. Cryptographic Nonce Replay Attacks
8. Adversarial High-Frequency Noise vs Operational Environmental Drift
"""
import uuid
import hashlib
import random
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw
import numpy as np
from app.crypto.signing import generate_keypair, sign_data
from app.crypto.canonicalization import canonicalize_json
from app.crypto.hashing import sha256_canonical_dict

class AttackFactory:
    @staticmethod
    def create_clean_sample_battery(count: int = 20, seed: int = 42) -> List[Dict[str, Any]]:
        """Generates clean synthetic dataset samples with consistent classes and unique hashes."""
        random.seed(seed)
        np.random.seed(seed)
        classes = ["Armoured_Vehicle", "Main_Battle_Tank", "Air_Defence_Unit", "Logistics_Truck", "Command_Post"]
        
        samples = []
        for i in range(count):
            s_id = f"SMP-{i+1:04d}"
            cls = classes[i % len(classes)]
            # Deterministic synthetic image byte content
            content = f"IMAGE_PIXELS_{s_id}_{cls}_{seed}".encode('utf-8')
            s_hash = hashlib.sha256(content).hexdigest()
            # Synthetic 64-bit dhash
            dhash = f"{random.getrandbits(64):016x}"
            samples.append({
                "sample_id": s_id,
                "label": cls,
                "sha256": s_hash,
                "phash": dhash,
                "contributor_id": "C-01",
                "ground_truth": "CLEAN"
            })
        return samples

    @staticmethod
    def mutate_duplicate_flood(samples: List[Dict[str, Any]], flood_count: int = 4) -> List[Dict[str, Any]]:
        """Injects exact byte-level duplicates into dataset."""
        mutated = [s.copy() for s in samples]
        base_sample = mutated[0]
        for i in range(flood_count):
            dup = base_sample.copy()
            dup["sample_id"] = f"SMP-DUP-{i+1:03d}"
            dup["ground_truth"] = "EXACT_DUPLICATE_ATTACK"
            mutated.append(dup)
        return mutated

    @staticmethod
    def mutate_near_duplicate_flood(samples: List[Dict[str, Any]], count: int = 4) -> List[Dict[str, Any]]:
        """Injects near-duplicate samples having identical or 1-bit Hamming distance dHash."""
        mutated = [s.copy() for s in samples]
        base_sample = mutated[1]
        base_phash = int(base_sample["phash"], 16)
        
        for i in range(count):
            # Flip just 1 bit in hash
            near_phash = f"{(base_phash ^ (1 << i)):016x}"
            near = {
                "sample_id": f"SMP-NEAR-{i+1:03d}",
                "label": base_sample["label"],
                "sha256": hashlib.sha256(f"NEAR_DIFF_CONTENT_{i}".encode('utf-8')).hexdigest(),
                "phash": near_phash,
                "contributor_id": "C-07",
                "ground_truth": "NEAR_DUPLICATE_FLOOD"
            }
            mutated.append(near)
        return mutated

    @staticmethod
    def mutate_label_poisoning(samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Injects conflicting labels on duplicate content and systematic mislabelling."""
        mutated = [s.copy() for s in samples]
        # Label conflict on target sample
        target = mutated[2]
        conflict = target.copy()
        conflict["sample_id"] = f"SMP-CONF-{uuid.uuid4().hex[:4]}"
        conflict["label"] = "Civilian_Vehicle" # Poisoned contradictory label
        conflict["contributor_id"] = "C-07"
        conflict["ground_truth"] = "LABEL_POISONING_CONFLICT"
        mutated.append(conflict)
        return mutated

    @staticmethod
    def create_signed_inference_record(
        inference_id: str,
        case_id: str,
        model_id: str,
        sequence: int,
        nonce: str,
        previous_record_hash: str,
        private_key_raw: bytes,
        predictions: Dict[str, Any],
        is_tampered: bool = False
    ) -> Dict[str, Any]:
        """Creates a cryptographically signed inference record, optionally tampering with output."""
        input_digest = hashlib.sha256(f"INPUT_IMG_{inference_id}".encode('utf-8')).hexdigest()
        model_digest = hashlib.sha256(f"WEIGHTS_{model_id}".encode('utf-8')).hexdigest()
        prep_digest = hashlib.sha256(b"PREPROCESS_RESIZE_NORM_640x640").hexdigest()
        config_digest = hashlib.sha256(b"CONF_THRESH_0.45_NMS_0.6").hexdigest()
        
        output_canonical = canonicalize_json(predictions)
        output_digest = hashlib.sha256(output_canonical).hexdigest()
        ts = "2026-09-26T12:00:00Z"

        canonical_payload = {
            "record_id": inference_id,
            "sequence": sequence,
            "timestamp": ts,
            "nonce": nonce,
            "input_sha256": input_digest,
            "model_sha256": model_digest,
            "preprocess_sha256": prep_digest,
            "config_sha256": config_digest,
            "output_sha256": output_digest,
            "previous_record_hash": previous_record_hash
        }
        
        # Sign the authentic payload
        sig_bytes = sign_data(private_key_raw, canonicalize_json(canonical_payload))
        signature_hex = sig_bytes.hex()

        # If attack simulation: modify output digest post-signing
        effective_output_digest = output_digest
        if is_tampered:
            effective_output_digest = hashlib.sha256(b"TAMPERED_PREDICTION_BOXES").hexdigest()

        return {
            "inference_id": inference_id,
            "case_id": case_id,
            "model_id": model_id,
            "input_sha256": input_digest,
            "model_sha256": model_digest,
            "preprocess_sha256": prep_digest,
            "config_sha256": config_digest,
            "output_sha256": effective_output_digest,
            "sequence": sequence,
            "timestamp": ts,
            "nonce": nonce,
            "previous_record_hash": previous_record_hash,
            "signature": signature_hex,
            "predictions": predictions,
            "ground_truth": "TAMPERED_OUTPUT" if is_tampered else "CLEAN_INFERENCE"
        }
