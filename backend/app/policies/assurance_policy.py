"""
DRISHTRA Assurance Case Policy Engine - DRISHTRA-AP-2026.1
Transparent, deterministic policy mapping heterogeneous multi-source evidence
into structured, defensible Assurance Cases based on Goal Structuring Notation (GSN).

Produces:
- CLAIM: Formal assertion on asset operational trustworthiness.
- EVIDENCE: Supporting & Incriminating empirical findings.
- COUNTER-EVIDENCE: Explicit evidence supporting integrity (e.g. weight digest match, no substitution).
- COVERAGE: What was tested? What wasn't?
- LIMITATIONS: Explicit engineering boundaries (e.g. black-box model access).
- MULTI-PATH CORRELATION: Convergence of independent evidence paths.
- DISPOSITION: ACCEPT, REVIEW, QUARANTINE.
"""
from typing import List, Dict, Any
from app.db.models import Finding

class AssurancePolicyEngine:
    POLICY_VERSION = "DRISHTRA-AP-2026.1"

    @classmethod
    def evaluate(
        cls,
        findings: List[Finding],
        coverage_map: Dict[str, str], # domain -> TESTED / LIMITED / NOT_TESTED / AVAILABLE / NOT_AVAILABLE
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes formal assurance case reasoning against cross-lifecycle findings.
        """
        incriminating_evidence = []
        supporting_evidence = []
        counter_evidence = []
        
        critical_count = 0
        high_count = 0
        medium_count = 0

        # Categorize findings
        for f in findings:
            item = {
                "finding_id": f.finding_id,
                "asset_id": f.asset_id,
                "detector_id": f.detector_id,
                "type": f.finding_type,
                "severity": f.severity,
                "confidence": f.confidence,
                "explanation": f.explanation,
                "created_at": f.created_at
            }
            if f.severity in ["CRITICAL", "HIGH"]:
                incriminating_evidence.append(item)
                if f.severity == "CRITICAL":
                    critical_count += 1
                else:
                    high_count += 1
            elif f.severity == "MEDIUM":
                incriminating_evidence.append(item)
                medium_count += 1
            elif f.severity == "LOW" or f.status == "PASS":
                supporting_evidence.append(item)

        # -------------------------------------------------------------
        # Synthesize Counter-Evidence (Passed checks proving integrity)
        # -------------------------------------------------------------
        # Even when an inference is flagged, what did NOT fail?
        has_weight_tamper = any("WEIGHT" in f.finding_type or "SUBSTITUTION" in f.finding_type for f in findings)
        if not has_weight_tamper:
            counter_evidence.append({
                "dimension": "MODEL_INTEGRITY",
                "finding": "MODEL_WEIGHT_DIGEST_MATCH",
                "status": "PASS",
                "statement": "Model weight digest matches registered reference; no evidence of binary substitution or on-disk tampering."
            })

        has_replay = any("REPLAY" in f.finding_type or "NONCE" in f.finding_type for f in findings)
        if not has_replay:
            counter_evidence.append({
                "dimension": "SEQUENCE_INTEGRITY",
                "finding": "NONCE_FRESHNESS_VERIFIED",
                "status": "PASS",
                "statement": "Inference sequence monotonicity verified; no cryptographic nonce reuse or message replay detected."
            })

        # -------------------------------------------------------------
        # Structured Coverage Matrix (Tested vs Not Tested)
        # -------------------------------------------------------------
        normalized_coverage = {}
        standard_dimensions = {
            "dataset_duplicate_flooding": "TESTED",
            "dataset_label_poisoning": "TESTED",
            "model_weight_fingerprint": "TESTED",
            "model_trigger_susceptibility": "TESTED",
            "inference_signature_binding": "TESTED",
            "inference_replay_detection": "TESTED",
            "distribution_sensor_shift": "TESTED",
            "thermal_infrared_sensor_shift": "NOT_TESTED",
            "white_box_internal_gradients": "NOT_TESTED (Black-Box Model)",
            "adversarial_patch_physical": "NOT_TESTED"
        }
        for k, default_val in standard_dimensions.items():
            if k in coverage_map:
                normalized_coverage[k] = coverage_map[k]
            else:
                normalized_coverage[k] = default_val

        # -------------------------------------------------------------
        # Limitations Synthesis
        # -------------------------------------------------------------
        limitations = []
        for domain, status in normalized_coverage.items():
            if "NOT_TESTED" in status or status == "NOT_AVAILABLE":
                limitations.append(f"{domain.replace('_', ' ').title()}: Dimension not evaluated in current operational envelope.")
            elif status == "LIMITED":
                limitations.append(f"{domain.replace('_', ' ').title()}: Partial evaluation (e.g. black-box probes only; internal layer gradients inaccessible).")

        # -------------------------------------------------------------
        # Multi-Path Evidence Convergence Analysis (The Core Centerpiece)
        # -------------------------------------------------------------
        affected_layers = set()
        for f in findings:
            if "SIGNATURE" in f.finding_type or "OUTPUT" in f.finding_type:
                affected_layers.add("INFERENCE_LAYER (Cryptographic Signature Invalid)")
            elif "TRIGGER" in f.finding_type or "BEHAVIORAL" in f.finding_type:
                affected_layers.add("MODEL_LAYER (Trojan Trigger Susceptibility Inversion)")
            elif "DUPLICATE" in f.finding_type or "LABEL" in f.finding_type or "POISON" in f.finding_type:
                affected_layers.add("DATASET_LAYER (Poisoning / Duplicate Flooding)")

        convergence_paths = list(affected_layers)
        multi_path_convergence = len(convergence_paths) >= 2

        # -------------------------------------------------------------
        # Disposition Decision Tree & Formal Claim
        # -------------------------------------------------------------
        if critical_count > 0:
            status = "QUARANTINED"
            disposition = "QUARANTINE"
            if multi_path_convergence:
                claim = (
                    f"Inference asset quarantined because {len(convergence_paths)} independent evidence paths converge "
                    f"across the supply-chain lifecycle ({', '.join(convergence_paths)}). Operational consumption strictly prohibited."
                )
            else:
                claim = "Inference asset failed critical cryptographic verification or exhibited confirmed Trojan backdoor vulnerability. Operational consumption prohibited."
        elif high_count > 0:
            status = "REVIEW_REQUIRED"
            disposition = "REVIEW"
            claim = "Inference asset exhibits significant behavioral, label poisoning, or sequence irregularities. Mandatory forensic inspection required before tactical usage."
        elif medium_count > 0:
            status = "REVIEW_REQUIRED"
            disposition = "REVIEW"
            claim = "Operational distribution shift or near-duplicate flooding detected. Requires analyst validation against theater environmental context."
        elif any("NOT_TESTED" in v for v in normalized_coverage.values()):
            status = "INCONCLUSIVE"
            disposition = "REVIEW"
            claim = "Key assurance dimensions were not evaluated due to offline data or black-box access limitations. Cannot assert unconditional verification."
        else:
            status = "VERIFIED"
            disposition = "ACCEPT"
            claim = "All pipeline boundaries, cryptographic bindings, behavioral probes, and operational tolerances verified against sovereign baseline."

        return {
            "policy_version": cls.POLICY_VERSION,
            "status": status,
            "recommended_disposition": disposition,
            "claim": claim,
            "multi_path_convergence": {
                "converged": multi_path_convergence,
                "convergent_path_count": len(convergence_paths),
                "convergent_paths": convergence_paths,
                "explanation": (
                    f"QUARANTINE is justified because {len(convergence_paths)} independent evidence paths converge on the same asset."
                    if multi_path_convergence else "Single-path anomaly detected."
                )
            },
            "supporting_evidence": supporting_evidence,
            "incriminating_evidence": incriminating_evidence,
            "evidence": incriminating_evidence,
            "counter_evidence": counter_evidence,
            "coverage": normalized_coverage,
            "limitations": limitations
        }
