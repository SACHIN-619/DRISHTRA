"""
DRISHTRA Assurance Policy - DRISHTRA-AP-2026.2

    CLAIM <- RULES <- EVIDENCE (findings) + COUNTER-EVIDENCE (passed checks)
          <- COVERAGE (what ran, what did not) <- LIMITATIONS -> RECOMMENDATION

Principles (each one is enforced by code below, and tested):
  1. Coverage comes from check executions only. A dimension is VERIFIED only if
     a check ran on every applicable asset and passed. Nothing ran -> NOT_TESTED.
     NOT_TESTED is never treated as a pass.
  2. Counter-evidence is drawn only from checks that ran and passed. It is never
     inferred from the absence of a finding.
  3. The evidence that justifies a recommendation is stored with the case.
  4. The engine recommends. Only a human REVIEWER_SUPERVISOR decides.

Changes from AP-2026.1: fixes the finding-type extraction bug that made every
ORM finding read as "FINDING" (which produced counter-evidence contradicting
findings), and replaces absence-based counter-evidence with execution-based.
"""
from collections import defaultdict
from typing import Any, Dict, List, Optional

SEVERITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}

# Coverage dimensions, grouped by lifecycle layer. Order is display order.
DIMENSIONS = [
    ("DATASET", "D1_EXACT_DUPLICATE"),
    ("DATASET", "D2_NEAR_DUPLICATE"),
    ("DATASET", "D3_LABEL_CONSISTENCY"),
    ("DATASET", "D4_CLASS_BALANCE"),
    ("DATASET", "D5_DISTRIBUTION_SHIFT"),
    ("DATASET", "D6_ANNOTATION_VALIDITY"),
    ("DATASET", "D7_OUT_OF_DISTRIBUTION"),
    ("MODEL", "D8A_WEIGHT_DIGEST"),
    ("MODEL", "D8B_BEHAVIOURAL_PROBE"),
    ("INFERENCE", "D9A_SIGNATURE_BINDING"),
    ("INFERENCE", "D9B_REPLAY_SEQUENCE"),
]

# Declared out-of-scope classes (shown on every coverage statement)
OUT_OF_SCOPE = [
    "White-box trigger reconstruction / activation clustering (prototype runs black-box probes only)",
    "SAR and thermal imagery modalities",
    "Physical-world adversarial patches",
    "Multi-modal sensor fusion pipelines",
    "Adaptive attackers who know the detector thresholds",
    "Hardware / firmware compromise of the inference host",
]


def _get(f: Any, key: str, default: Any = None) -> Any:
    """Field access that works for ORM rows and dicts alike."""
    if isinstance(f, dict):
        return f.get(key, default)
    return getattr(f, key, default)


class AssurancePolicyEngine:
    POLICY_VERSION = "DRISHTRA-AP-2026.2"

    @classmethod
    def evaluate(
        cls,
        findings: Optional[List[Any]] = None,
        executions: Optional[List[Dict[str, Any]]] = None,
        assets: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        catalog: Optional[Dict[str, Any]] = None,
        **_ignored: Any,
    ) -> Dict[str, Any]:
        findings = findings or []
        executions = executions or []
        assets = assets or {"DATASET": [], "MODEL": [], "INFERENCE": []}
        catalog = catalog or {}

        # ------------------------------------------------------------ evidence
        evidence: List[Dict[str, Any]] = []
        low_info: List[Dict[str, Any]] = []
        sev_count = defaultdict(int)
        for f in findings:
            item = {
                "finding_id": _get(f, "finding_id"),
                "asset_id": _get(f, "asset_id"),
                "asset_type": _get(f, "asset_type"),
                "detector_id": _get(f, "detector_id"),
                "type": _get(f, "finding_type", "UNKNOWN"),
                "severity": _get(f, "severity", "MEDIUM"),
                "confidence": _get(f, "confidence"),
                "deterministic": bool(_get(f, "deterministic", False)),
                "explanation": _get(f, "explanation", ""),
                "limitations": _get(f, "limitations"),
            }
            sev_count[item["severity"]] += 1
            (evidence if SEVERITY_RANK.get(item["severity"], 2) >= 2 else low_info).append(item)
        evidence.sort(key=lambda x: -SEVERITY_RANK.get(x["severity"], 0))

        # ------------------------------------------------------------ coverage
        by_dim: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for e in executions:
            by_dim[e["check_id"]].append(e)

        coverage: Dict[str, Dict[str, Any]] = {}
        for layer, dim in DIMENSIONS:
            layer_assets = [a["id"] for a in assets.get(layer, [])]
            runs = {e["asset_id"]: e for e in by_dim.get(dim, [])}
            label = catalog.get(dim, (layer, dim, ""))[1]
            desc = catalog.get(dim, (layer, dim, ""))[2]
            if not layer_assets:
                state, detail = "NOT_APPLICABLE", f"No {layer.lower()} assets in this case."
            elif runs and all(r["outcome"] == "NOT_APPLICABLE" for r in runs.values()):
                state = "NOT_APPLICABLE"
                detail = next(iter(runs.values()))["detail"]
            else:
                outcomes = [runs[a]["outcome"] if a in runs else "NOT_TESTED" for a in layer_assets]
                tested = [o for o in outcomes if o in ("PASS", "FINDING")]
                if "FINDING" in outcomes:
                    state = "FINDING"
                elif "INCONCLUSIVE" in outcomes:
                    state = "INCONCLUSIVE"
                elif tested and len(tested) == len(outcomes):
                    state = "VERIFIED"
                elif tested:
                    state = "PARTIAL"
                else:
                    state = "NOT_TESTED"
                untested = [a for a, o in zip(layer_assets, outcomes) if o not in ("PASS", "FINDING")]
                detail = (
                    f"Ran on {len(tested)}/{len(layer_assets)} {layer.lower()} asset(s)"
                    + (f"; not run on {', '.join(untested)}" if untested else "")
                    + "."
                )
                reasons = [runs[a]["detail"] for a in layer_assets if a in runs and runs[a]["outcome"] in ("NOT_TESTED", "INCONCLUSIVE")]
                if reasons:
                    detail += " " + reasons[0]
            coverage[dim] = {
                "layer": layer, "label": label, "description": desc, "state": state, "detail": detail,
                "assets": {a: (runs[a]["outcome"] if a in runs else "NOT_TESTED") for a in layer_assets},
            }

        applicable = [c for c in coverage.values() if c["state"] != "NOT_APPLICABLE"]
        assessed = [c for c in applicable if c["state"] in ("VERIFIED", "FINDING")]
        partial = [c for c in applicable if c["state"] == "PARTIAL"]
        coverage_ratio = (len(assessed) + 0.5 * len(partial)) / len(applicable) if applicable else 0.0
        coverage_summary = {
            "percent": round(coverage_ratio * 100),
            "applicable_dimensions": len(applicable),
            "assessed_dimensions": len(assessed),
            "partial_dimensions": len(partial),
            "not_tested": [k for k, c in coverage.items() if c["state"] == "NOT_TESTED"],
            "inconclusive": [k for k, c in coverage.items() if c["state"] == "INCONCLUSIVE"],
            "not_applicable": [k for k, c in coverage.items() if c["state"] == "NOT_APPLICABLE"],
            "out_of_scope": OUT_OF_SCOPE,
            "by_layer": {
                layer: {
                    "state": _layer_state([c for c in coverage.values() if c["layer"] == layer]),
                }
                for layer in ("DATASET", "MODEL", "INFERENCE")
            },
        }

        # ---------------------------------------------------- counter-evidence
        counter_evidence = [
            {
                "check_id": e["check_id"],
                "label": catalog.get(e["check_id"], (None, e["check_id"]))[1],
                "asset_id": e["asset_id"],
                "asset_type": e["asset_type"],
                "detector_id": e["detector_id"],
                "statement": e["detail"],
                "executed_at": e["executed_at"],
                "execution_id": e["execution_id"],
            }
            for e in executions if e["outcome"] == "PASS"
        ]

        # ---------------------------------------------------- convergence
        lineage = _lineage_index(assets)
        layers_hit: Dict[str, List[str]] = defaultdict(list)
        contributor_hits: Dict[str, set] = defaultdict(set)
        for item in evidence:
            layer = item["asset_type"] or "UNKNOWN"
            layers_hit[layer].append(item["finding_id"])
            for c in lineage.get(item["asset_id"], set()):
                contributor_hits[c].add(layer)
        converging_contributors = sorted(
            [{"contributor_id": c, "layers": sorted(ls)} for c, ls in contributor_hits.items() if len(ls) >= 2],
            key=lambda x: -len(x["layers"]),
        )
        converged = len(layers_hit) >= 2
        convergence = {
            "converged": converged,
            "path_count": len(layers_hit),
            "paths": {k: v for k, v in sorted(layers_hit.items())},
            "contributors": converging_contributors,
            "explanation": (
                f"{len(layers_hit)} independent evidence paths ({', '.join(sorted(layers_hit))}) "
                + (f"trace back to contributor {converging_contributors[0]['contributor_id']}."
                   if converging_contributors else "are implicated in this case.")
            ) if converged else (
                "Findings are confined to a single lifecycle layer." if layers_hit else "No integrity findings."
            ),
        }

        # ---------------------------------------------------- drift vs manipulation
        drift = None
        if coverage["D5_DISTRIBUTION_SHIFT"]["state"] == "FINDING":
            integrity_types = {"EXACT_DUPLICATE_FLOODING", "NEAR_DUPLICATE_FLOODING", "LABEL_POISONING_CONFLICT",
                               "MODEL_DIGEST_MISMATCH", "CRYPTOGRAPHIC_SIGNATURE_INVALID", "INFERENCE_REPLAY_ATTACK",
                               "TRIGGER_SUSCEPTIBILITY_DEVIATION"}
            corroborating = [i["type"] for i in evidence if i["type"] in integrity_types]
            drift = {
                "observed": "Distribution shift",
                "possible_explanations": ["Operational environment change", "Sensor change",
                                          "Seasonal / terrain change", "Deliberate data manipulation"],
                "corroborating_integrity_findings": corroborating,
                "assessment": "SUSPICIOUS_MANIPULATION" if corroborating else "PROBABLE_OPERATIONAL_DRIFT",
                "basis": ("Shift co-occurs with independent integrity findings."
                          if corroborating else "No independent integrity finding corroborates manipulation."),
            }

        # ---------------------------------------------------- limitations
        limitations: List[str] = []
        for dim, c in coverage.items():
            if c["state"] in ("NOT_TESTED", "INCONCLUSIVE", "PARTIAL"):
                limitations.append(f"{c['label']}: {c['state'].replace('_', ' ').lower()} — {c['detail']}")
            elif c["state"] == "NOT_APPLICABLE" and c["layer"] == "MODEL" and assets.get("MODEL"):
                limitations.append(f"{c['label']}: {c['detail']}")
        dims_known = {d for _, d in DIMENSIONS}
        for e in executions:
            if e["check_id"] not in dims_known and e["outcome"] in ("NOT_APPLICABLE", "NOT_TESTED"):
                label = catalog.get(e["check_id"], (None, e["check_id"]))[1]
                limitations.append(f"{label} ({e['asset_id']}): {e['detail']}")
        for item in evidence:
            if item.get("limitations"):
                limitations.append(f"{item['type']} ({item['asset_id']}): {item['limitations']}")
        limitations = list(dict.fromkeys(limitations))

        # ---------------------------------------------------- decision tree
        crit, high, med = sev_count["CRITICAL"], sev_count["HIGH"], sev_count["MEDIUM"]
        rules_fired: List[str] = []
        if crit:
            status, disposition = "QUARANTINE_RECOMMENDED", "QUARANTINE"
            rules_fired.append(f"R1: {crit} CRITICAL finding(s) present")
        elif converged and high:
            status, disposition = "QUARANTINE_RECOMMENDED", "QUARANTINE"
            rules_fired.append(f"R2: HIGH findings converge across {len(layers_hit)} lifecycle layers")
        elif high or med:
            status, disposition = "REVIEW_REQUIRED", "REVIEW"
            rules_fired.append(f"R3: {high} HIGH / {med} MEDIUM finding(s) need analyst judgement")
        elif not applicable or not assessed:
            status, disposition = "INCONCLUSIVE", "REVIEW"
            rules_fired.append("R4: nothing was assessed; absence of findings is not evidence of integrity")
        elif coverage_summary["not_tested"] or coverage_summary["inconclusive"] or partial:
            status, disposition = "INCONCLUSIVE", "REVIEW"
            rules_fired.append("R5: no findings, but applicable dimensions were not (fully) tested")
        else:
            status, disposition = "VERIFIED", "ACCEPT"
            rules_fired.append("R6: every applicable dimension ran; nothing above LOW severity")

        claim = _claim(status, convergence, evidence, coverage_summary)

        return {
            "policy_version": cls.POLICY_VERSION,
            "status": status,
            "recommended_disposition": disposition,
            "claim": claim,
            "rules_fired": rules_fired,
            "severity_counts": {k: sev_count.get(k, 0) for k in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")},
            "evidence": evidence,
            "incriminating_evidence": evidence,
            "supporting_evidence": low_info,
            "counter_evidence": counter_evidence,
            "coverage": coverage,
            "coverage_summary": coverage_summary,
            "convergence": convergence,
            "multi_path_convergence": convergence,
            "drift_assessment": drift,
            "limitations": limitations,
        }


def _layer_state(dims: List[Dict[str, Any]]) -> str:
    states = [d["state"] for d in dims]
    if not states or all(s == "NOT_APPLICABLE" for s in states):
        return "NOT_APPLICABLE"
    if "FINDING" in states:
        return "FINDING"
    if any(s in ("NOT_TESTED", "INCONCLUSIVE", "PARTIAL") for s in states):
        return "INCOMPLETE"
    return "VERIFIED"


def _lineage_index(assets: Dict[str, List[Dict[str, Any]]]) -> Dict[str, set]:
    """asset_id -> set of contributor ids upstream of it."""
    idx: Dict[str, set] = {}
    model_contrib: Dict[str, set] = {}
    for d in assets.get("DATASET", []):
        idx[d["id"]] = {d["contributor_id"]} if d.get("contributor_id") else set()
    for m in assets.get("MODEL", []):
        s = {m["contributor_id"]} if m.get("contributor_id") else set()
        for ds in m.get("trained_from", []):
            s |= idx.get(ds, set())
        idx[m["id"]] = s
        model_contrib[m["id"]] = s
    for i in assets.get("INFERENCE", []):
        idx[i["id"]] = set(model_contrib.get(i.get("model_id"), set()))
    return idx


def _claim(status: str, convergence: Dict[str, Any], evidence: List[Dict[str, Any]], cov: Dict[str, Any]) -> str:
    pct = cov["percent"]
    if status == "QUARANTINE_RECOMMENDED":
        top = evidence[0] if evidence else None
        base = (f"Quarantine recommended: {convergence['explanation']}" if convergence["converged"]
                else f"Quarantine recommended: {top['severity']} {top['type']} on {top['asset_id']}." if top
                else "Quarantine recommended.")
        return f"{base} Downstream use should be blocked pending human review. Evidence coverage {pct}%."
    if status == "REVIEW_REQUIRED":
        return (f"Review required: {len(evidence)} finding(s) need analyst judgement before this result is relied on. "
                f"Evidence coverage {pct}%.")
    if status == "INCONCLUSIVE":
        return (f"Inconclusive: no integrity findings, but only {pct}% of applicable checks were assessed. "
                "Absence of findings is not evidence of integrity.")
    return (f"Verified: every applicable check ran (coverage {pct}%) and nothing above LOW severity was found. "
            "Residual limitations are listed.")
