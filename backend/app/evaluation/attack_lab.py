"""
DRISHTRA Demo Attack Lab & Empirical Evaluation Benchmarking
Explicitly separates:
1. Injected Synthetic Ground Truth (What the adversarial lab injected)
2. DRISHTRA Observations (What the detectors observed without prior knowledge)
3. Confusion Matrix Calculation: TP, FP, FN, TN, Precision, Recall, F1 Score
"""
import uuid
from typing import Dict, Any, List
from app.fixtures.attack_factory import AttackFactory
from app.detectors.duplicate_detector import ExactDuplicateDetector, NearDuplicateDetector
from app.detectors.label_anomaly_detector import LabelAnomalyDetector
from app.detectors.behavioral_fingerprint_detector import BehavioralFingerprintDetector
from app.crypto.verification import verify_inference_record
from app.crypto.signing import generate_keypair

class DemoAttackLab:
    @staticmethod
    def run_benchmark() -> Dict[str, Any]:
        """
        Executes a controlled benchmark comparing known injected attacks against
        DRISHTRA detector observations, producing quantitative empirical metrics.
        """
        evaluations = []
        
        # ---------------------------------------------------------
        # Scenario 1: Clean Samples (Should NOT be flagged)
        # ---------------------------------------------------------
        clean_samples = AttackFactory.create_clean_sample_battery(count=10, seed=101)
        for s in clean_samples:
            evaluations.append({
                "test_id": f"TEST-CLN-{s['sample_id']}",
                "category": "DATASET_INTEGRITY",
                "asset_id": s["sample_id"],
                "injected_ground_truth": "CLEAN",
                "is_attack_injected": False,
                "sample_data": s
            })

        # ---------------------------------------------------------
        # Scenario 2: Exact Duplicate Flooding (Injected Attack)
        # ---------------------------------------------------------
        exact_dups = AttackFactory.mutate_duplicate_flood(clean_samples[:4], flood_count=3)
        for s in exact_dups[4:]:
            evaluations.append({
                "test_id": f"TEST-EXACT-{s['sample_id']}",
                "category": "DATASET_INTEGRITY",
                "asset_id": s["sample_id"],
                "injected_ground_truth": "EXACT_DUPLICATE_ATTACK",
                "is_attack_injected": True,
                "sample_data": s
            })

        # ---------------------------------------------------------
        # Scenario 3: Near-Duplicate Flooding (Injected Attack)
        # ---------------------------------------------------------
        near_dups = AttackFactory.mutate_near_duplicate_flood(clean_samples[:4], count=3)
        for s in near_dups[4:]:
            evaluations.append({
                "test_id": f"TEST-NEAR-{s['sample_id']}",
                "category": "DATASET_INTEGRITY",
                "asset_id": s["sample_id"],
                "injected_ground_truth": "NEAR_DUPLICATE_FLOOD",
                "is_attack_injected": True,
                "sample_data": s
            })

        # ---------------------------------------------------------
        # Scenario 4: Label Poisoning Conflict (Injected Attack)
        # ---------------------------------------------------------
        label_pois = AttackFactory.mutate_label_poisoning(clean_samples[:4])
        for s in label_pois[4:]:
            evaluations.append({
                "test_id": f"TEST-LBL-{s['sample_id']}",
                "category": "DATASET_INTEGRITY",
                "asset_id": s["sample_id"],
                "injected_ground_truth": "LABEL_POISONING_CONFLICT",
                "is_attack_injected": True,
                "sample_data": s
            })

        # ---------------------------------------------------------
        # Scenario 5: Behavioral Trojan Trigger Battery (Model Level)
        # ---------------------------------------------------------
        clean_probes = {
            "clean": {"predicted_class": "Armoured_Vehicle", "confidence": 0.94},
            "brightness_plus": {"predicted_class": "Armoured_Vehicle", "confidence": 0.92},
            "contrast_plus": {"predicted_class": "Armoured_Vehicle", "confidence": 0.93},
            "gaussian_blur": {"predicted_class": "Armoured_Vehicle", "confidence": 0.89},
            "trigger_patch_corner": {"predicted_class": "Armoured_Vehicle", "confidence": 0.91}
        }
        clean_model_res = BehavioralFingerprintDetector().run(probe_results=clean_probes)
        evaluations.append({
            "test_id": "TEST-MDL-CLEAN",
            "category": "MODEL_BEHAVIOR",
            "asset_id": "M-REF",
            "injected_ground_truth": "CLEAN",
            "is_attack_injected": False,
            "result_findings": clean_model_res.findings
        })

        trojan_probes = {
            "clean": {"predicted_class": "Armoured_Vehicle", "confidence": 0.95},
            "brightness_plus": {"predicted_class": "Armoured_Vehicle", "confidence": 0.91},
            "contrast_plus": {"predicted_class": "Armoured_Vehicle", "confidence": 0.92},
            "gaussian_blur": {"predicted_class": "Armoured_Vehicle", "confidence": 0.88},
            "trigger_patch_corner": {"predicted_class": "Civilian_Vehicle", "confidence": 0.96}
        }
        trojan_model_res = BehavioralFingerprintDetector().run(probe_results=trojan_probes)
        evaluations.append({
            "test_id": "TEST-MDL-TROJAN",
            "category": "MODEL_BEHAVIOR",
            "asset_id": "M-04-TROJAN",
            "injected_ground_truth": "TROJAN_TRIGGER_BACKDOOR",
            "is_attack_injected": True,
            "result_findings": trojan_model_res.findings
        })

        # ---------------------------------------------------------
        # Scenario 6: Cryptographic Signature Tampering (Inference Level)
        # ---------------------------------------------------------
        priv, pub = generate_keypair()
        clean_inf = AttackFactory.create_signed_inference_record(
            inference_id="I-CLN-01",
            case_id="EVAL",
            model_id="M-REF",
            sequence=1,
            nonce="nonce-001",
            previous_record_hash="0"*64,
            private_key_raw=priv,
            predictions={"boxes": [[10, 10, 50, 50]]},
            is_tampered=False
        )
        evaluations.append({
            "test_id": "TEST-INF-CLEAN",
            "category": "CRYPTOGRAPHIC_INTEGRITY",
            "asset_id": "I-CLN-01",
            "injected_ground_truth": "CLEAN",
            "is_attack_injected": False,
            "inf_record": clean_inf,
            "public_key_hex": pub.hex()
        })

        tampered_inf = AttackFactory.create_signed_inference_record(
            inference_id="I-TAMP-01",
            case_id="EVAL",
            model_id="M-04",
            sequence=2,
            nonce="nonce-002",
            previous_record_hash="1"*64,
            private_key_raw=priv,
            predictions={"boxes": [[10, 10, 50, 50]]},
            is_tampered=True
        )
        evaluations.append({
            "test_id": "TEST-INF-TAMPERED",
            "category": "CRYPTOGRAPHIC_INTEGRITY",
            "asset_id": "I-TAMP-01",
            "injected_ground_truth": "OUTPUT_SIGNATURE_TAMPERED",
            "is_attack_injected": True,
            "inf_record": tampered_inf,
            "public_key_hex": pub.hex()
        })

        # =========================================================
        # EXECUTE DETECTIONS & COMPUTE CONFUSION MATRIX
        # =========================================================
        tp = 0 # Injected = True, Observed = True
        fp = 0 # Injected = False, Observed = True
        fn = 0 # Injected = True, Observed = False
        tn = 0 # Injected = False, Observed = False

        results_matrix = []

        # Run Dataset detectors on combined dataset tests
        all_dataset_samples = [e["sample_data"] for e in evaluations if e["category"] == "DATASET_INTEGRITY"]
        res_exact = ExactDuplicateDetector().run(all_dataset_samples)
        res_near = NearDuplicateDetector().run(all_dataset_samples)
        res_label = LabelAnomalyDetector().run(all_dataset_samples)

        flagged_sample_ids = set()
        for f in res_exact.findings:
            flagged_sample_ids.update(f.measurement.get("duplicate_sample_ids", []))
        for f in res_near.findings:
            flagged_sample_ids.update(f.measurement.get("affected_sample_ids", []))
        for f in res_label.findings:
            flagged_sample_ids.update(f.measurement.get("affected_sample_ids", []))

        for e in evaluations:
            is_flagged = False
            detector_obs = "NONE"

            if e["category"] == "DATASET_INTEGRITY":
                if e["asset_id"] in flagged_sample_ids:
                    is_flagged = True
                    detector_obs = "DATASET_ANOMALY_DETECTED"
                else:
                    detector_obs = "DATASET_NORMAL"
            elif e["category"] == "MODEL_BEHAVIOR":
                if len(e["result_findings"]) > 0:
                    is_flagged = True
                    detector_obs = e["result_findings"][0].finding_type
                else:
                    detector_obs = "MODEL_NOMINAL"
            elif e["category"] == "CRYPTOGRAPHIC_INTEGRITY":
                v_res = verify_inference_record(
                    record=e["inf_record"],
                    public_key_hex=e["public_key_hex"]
                )
                if not v_res["is_valid"]:
                    is_flagged = True
                    detector_obs = v_res.get("status", "INVALID_SIGNATURE")
                else:
                    detector_obs = "SIGNATURE_VERIFIED"

            # Compute quadrant
            injected = e["is_attack_injected"]
            if injected and is_flagged:
                quadrant = "TP"
                tp += 1
            elif not injected and is_flagged:
                quadrant = "FP"
                fp += 1
            elif injected and not is_flagged:
                quadrant = "FN"
                fn += 1
            else:
                quadrant = "TN"
                tn += 1

            results_matrix.append({
                "test_id": e["test_id"],
                "category": e["category"],
                "asset_id": e["asset_id"],
                "injected_ground_truth": e["injected_ground_truth"],
                "drishtra_observation": detector_obs,
                "is_attack_injected": injected,
                "is_detected": is_flagged,
                "classification": quadrant
            })

        total = tp + fp + fn + tn
        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
        f1_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        accuracy = ((tp + tn) / total) if total > 0 else 1.0

        return {
            "benchmark_title": "DRISHTRA Attack Lab: Ground Truth vs Observation Matrix",
            "total_evaluations": total,
            "confusion_matrix": {
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "true_negatives": tn
            },
            "metrics": {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1_score, 4),
                "accuracy": round(accuracy, 4),
                "false_discovery_rate": round(fp / (tp + fp) if (tp + fp) > 0 else 0.0, 4)
            },
            "results_matrix": results_matrix
        }
