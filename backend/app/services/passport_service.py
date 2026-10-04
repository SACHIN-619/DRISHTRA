"""
Assurance Passport and "Why was this flagged?" explanation.

Both are assembled only from stored facts:
  identity      registered asset record + digest
  lineage       contributor -> dataset -> model -> runtime -> inference
  evidence      findings on the asset and everything upstream of it
  counter-evid. checks that ran and PASSED on the asset and upstream
  coverage      latest outcome of every check on the asset
  limitations   NOT_TESTED / NOT_APPLICABLE / INCONCLUSIVE checks + detector caveats
  disposition   machine recommendation and the latest human decision

A passport carries a SHA-256 digest of its canonical content and a node
signature, so an exported copy can be checked against the system later.
"""
import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.crypto.crypto_service import CryptoService, KeyManagementInterface
from app.db.models import (
    AssuranceDecision, CheckExecution, Contributor, Dataset, EvidenceEdge, Finding,
    InferenceRecord, ModelAsset, RuntimeBinding, utc_now_iso,
)
from app.services.assurance_service import AssuranceService
from app.services.evidence_writer import CHECK_CATALOG

SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def _locate(db: Session, asset_id: str) -> Tuple[Optional[str], Any]:
    for kind, model, col in (("MODEL", ModelAsset, ModelAsset.model_id),
                             ("DATASET", Dataset, Dataset.dataset_id),
                             ("INFERENCE", InferenceRecord, InferenceRecord.inference_id)):
        row = db.query(model).filter(col == asset_id).first()
        if row:
            return kind, row
    return None, None


def _contributor(db: Session, cid: Optional[str]) -> Optional[Dict[str, Any]]:
    if not cid:
        return None
    c = db.query(Contributor).filter(Contributor.contributor_id == cid).first()
    return {"id": c.contributor_id, "name": c.name, "type": c.contributor_type} if c else {"id": cid, "name": "Unregistered"}


def lineage_for(db: Session, kind: str, row: Any) -> List[Dict[str, Any]]:
    """Ordered upstream chain, nearest first: [asset, runtime?, model?, dataset(s)?, contributor]."""
    chain: List[Dict[str, Any]] = []
    case_id = row.case_id

    def trained_from(model_id: str) -> List[Dataset]:
        edges = db.query(EvidenceEdge).filter(EvidenceEdge.case_id == case_id,
                                             EvidenceEdge.relationship == "trained_from",
                                             EvidenceEdge.target_node == f"model:{model_id}").all()
        ids = [e.source_node.split(":", 1)[1] for e in edges]
        return db.query(Dataset).filter(Dataset.dataset_id.in_(ids)).all() if ids else []

    def add_model(m: ModelAsset, relation: str):
        chain.append({"layer": "MODEL", "id": m.model_id, "label": m.name, "relation": relation,
                      "digest": m.weight_sha256, "contributor_id": m.contributor_id, "access_level": m.access_level})
        for d in trained_from(m.model_id):
            chain.append({"layer": "DATASET", "id": d.dataset_id, "label": d.name, "relation": "trained from",
                          "digest": d.sha256, "contributor_id": d.contributor_id})

    if kind == "INFERENCE":
        chain.append({"layer": "INFERENCE", "id": row.inference_id, "label": f"Inference #{row.sequence}",
                      "relation": "subject", "digest": row.output_sha256, "status": row.verification_status})
        if row.runtime_id:
            rt = db.query(RuntimeBinding).filter(RuntimeBinding.runtime_id == row.runtime_id).first()
            if rt:
                chain.append({"layer": "RUNTIME", "id": rt.runtime_id, "label": f"{rt.framework_version} / {rt.hardware_target} / {rt.quantization}",
                              "relation": "produced on", "digest": rt.config_digest})
        m = db.query(ModelAsset).filter(ModelAsset.model_id == row.model_id).first() if row.model_id else None
        if m:
            add_model(m, "produced by")
    elif kind == "MODEL":
        add_model(row, "subject")
    else:
        chain.append({"layer": "DATASET", "id": row.dataset_id, "label": row.name, "relation": "subject",
                      "digest": row.sha256, "contributor_id": row.contributor_id})

    seen = set()
    for link in list(chain):
        cid = link.get("contributor_id")
        if cid and cid not in seen:
            seen.add(cid)
            c = _contributor(db, cid)
            chain.append({"layer": "CONTRIBUTOR", "id": c["id"], "label": c["name"], "relation": "supplied by",
                          "contributor_type": c.get("type")})
    return chain


def _latest_checks(db: Session, case_id: str, asset_ids: List[str]) -> Dict[Tuple[str, str], CheckExecution]:
    rows = db.query(CheckExecution).filter(CheckExecution.case_id == case_id,
                                           CheckExecution.asset_id.in_(asset_ids)) \
        .order_by(CheckExecution.executed_at.asc()).all()
    latest: Dict[Tuple[str, str], CheckExecution] = {}
    for r in rows:
        latest[(r.asset_id, r.check_id)] = r
    return latest


def _current_findings(db: Session, case_id: str, asset_ids: List[str], latest) -> List[Finding]:
    current = {fid for r in latest.values() for fid in json.loads(r.finding_ids_json or "[]")}
    all_f = db.query(Finding).filter(Finding.case_id == case_id, Finding.asset_id.in_(asset_ids)).all()
    linked = {fid for r in db.query(CheckExecution).filter(CheckExecution.case_id == case_id).all()
              for fid in json.loads(r.finding_ids_json or "[]")}
    return sorted([f for f in all_f if f.finding_id in current or f.finding_id not in linked],
                  key=lambda f: SEV_ORDER.get(f.severity, 5))


def _f(f: Finding) -> Dict[str, Any]:
    return {"finding_id": f.finding_id, "case_id": f.case_id, "asset_id": f.asset_id, "asset_type": f.asset_type,
            "detector_id": f.detector_id, "type": f.finding_type, "severity": f.severity,
            "confidence": f.confidence, "deterministic": bool(f.deterministic),
            "explanation": f.explanation, "limitations": f.limitations}


def _layer_state(outcomes: List[str]) -> str:
    if not outcomes:
        return "NOT_TESTED"
    if "FINDING" in outcomes:
        return "FINDING"
    if any(o in ("NOT_TESTED", "INCONCLUSIVE") for o in outcomes):
        return "INCOMPLETE"
    if all(o == "NOT_APPLICABLE" for o in outcomes):
        return "NOT_APPLICABLE"
    return "VERIFIED"


class PassportService:
    @staticmethod
    def build(db: Session, asset_id: str) -> Optional[Dict[str, Any]]:
        kind, row = _locate(db, asset_id)
        if not row:
            return None
        case_id = row.case_id
        chain = lineage_for(db, kind, row)
        asset_ids = [l["id"] for l in chain if l["layer"] in ("DATASET", "MODEL", "INFERENCE")]
        latest = _latest_checks(db, case_id, asset_ids)
        findings = _current_findings(db, case_id, asset_ids, latest)

        own = {k[1]: v for k, v in latest.items() if k[0] == asset_id}
        coverage = [{"check_id": cid, "label": CHECK_CATALOG.get(cid, (None, cid))[1],
                     "outcome": e.outcome, "detail": e.detail, "executed_at": e.executed_at}
                    for cid, e in sorted(own.items())]
        expected = [k for k, v in CHECK_CATALOG.items() if v[0] == kind]
        for cid in expected:
            if cid not in own:
                coverage.append({"check_id": cid, "label": CHECK_CATALOG[cid][1], "outcome": "NOT_TESTED",
                                 "detail": "No execution recorded for this asset.", "executed_at": None})

        integrity = {}
        for layer in ("DATASET", "MODEL", "RUNTIME", "INFERENCE"):
            ids = [l["id"] for l in chain if l["layer"] == layer]
            if not ids:
                continue
            if layer == "RUNTIME":
                integrity[layer] = {"state": "BOUND", "assets": ids,
                                    "detail": "Configuration digest recorded; runtime attestation not implemented."}
                continue
            outcomes = [e.outcome for (aid, _), e in latest.items() if aid in ids]
            integrity[layer] = {"state": _layer_state(outcomes), "assets": ids}

        counter = [{"check_id": e.check_id, "label": CHECK_CATALOG.get(e.check_id, (None, e.check_id))[1],
                    "asset_id": e.asset_id, "statement": e.detail} for e in latest.values() if e.outcome == "PASS"]
        limitations = [f"{CHECK_CATALOG.get(e.check_id, (None, e.check_id))[1]} ({e.asset_id}): {e.detail}"
                       for e in latest.values() if e.outcome in ("NOT_TESTED", "NOT_APPLICABLE", "INCONCLUSIVE")]
        limitations += [f"{f.finding_type} ({f.asset_id}): {f.limitations}" for f in findings if f.limitations]

        sev = {k: 0 for k in SEV_ORDER}
        for f in findings:
            sev[f.severity] = sev.get(f.severity, 0) + 1

        ac = AssuranceService.get_latest_assurance(db, case_id)
        decision = db.query(AssuranceDecision).filter(AssuranceDecision.case_id == case_id,
                                                      AssuranceDecision.kind == "DISPOSITION") \
            .order_by(AssuranceDecision.sequence.desc()).first()

        identity = {"asset_id": asset_id, "asset_type": kind, "case_id": case_id}
        if kind == "MODEL":
            identity.update({"name": row.name, "version": row.version, "format": row.format, "framework": row.framework,
                             "architecture": row.architecture, "digest_sha256": row.weight_sha256,
                             "access_level": row.access_level, "reference_model": row.reference_model_id,
                             "parameters": row.parameter_count})
        elif kind == "DATASET":
            identity.update({"name": row.name, "version": row.version, "format": row.format,
                             "digest_sha256": row.sha256, "manifest_hash": row.manifest_hash, "samples": row.sample_count})
        else:
            identity.update({"name": f"Inference #{row.sequence}", "digest_sha256": row.output_sha256,
                             "input_sha256": row.input_sha256, "model_sha256": row.model_sha256,
                             "nonce": row.nonce, "signer": row.signer, "verification_status": row.verification_status})
        identity["evidence_label"] = row.evidence_label

        body = {
            "passport_id": f"PASS-{asset_id}",
            "identity": identity,
            "source": _contributor(db, getattr(row, "contributor_id", None)) or next(
                ({"id": l["id"], "name": l["label"]} for l in chain if l["layer"] == "CONTRIBUTOR"), None),
            "lineage": chain,
            "integrity": integrity,
            "severity_counts": sev,
            "evidence": [_f(f) for f in findings],
            "counter_evidence": counter,
            "coverage": coverage,
            "limitations": list(dict.fromkeys(limitations)),
            "recommendation": {
                "assurance_id": ac.assurance_id if ac else None,
                "machine_status": ac.status if ac else "NOT_ASSESSED",
                "recommended_disposition": ac.recommended_disposition if ac else None,
                "claim": ac.claim if ac else None,
                "human_disposition": decision.disposition if decision else None,
                "decided_by": decision.actor if decision else None,
                "decided_at": decision.decided_at if decision else None,
            },
            "issued_at": utc_now_iso(),
        }
        digest = CryptoService.hash(json.loads(json.dumps(body, default=str)))
        body["passport_digest"] = digest
        body["signature"] = CryptoService.sign({"passport_digest": digest}).hex()
        body["signer_key_fingerprint"] = KeyManagementInterface.public_key_fingerprint()

        # Compatibility fields used by older clients and exports
        body.update({
            "asset_id": asset_id, "asset_type": kind, "name": identity.get("name"),
            "contributor": (body["source"] or {}).get("name"), "version": identity.get("version", "-"),
            "digest_sha256": identity.get("digest_sha256"),
            "assurance_status": body["recommendation"]["machine_status"],
            "findings_summary": {k: sev.get(k, 0) for k in ("CRITICAL", "HIGH", "MEDIUM", "LOW")},
            "coverage_matrix": {c["check_id"]: c["outcome"] for c in coverage},
            "verified_claims": [c["statement"] for c in counter],
            "counter_findings": [f"{f.finding_type}: {f.explanation}" for f in findings],
            "last_assessed": ac.created_at if ac else None,
        })
        return body

    # Backward-compatible entry points
    @staticmethod
    def get_model_passport(db: Session, model_id: str):
        return PassportService.build(db, model_id) if db.query(ModelAsset).filter(ModelAsset.model_id == model_id).first() else None

    @staticmethod
    def get_dataset_passport(db: Session, dataset_id: str):
        return PassportService.build(db, dataset_id) if db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first() else None

    @staticmethod
    def get_inference_passport(db: Session, inference_id: str):
        return PassportService.build(db, inference_id) if db.query(InferenceRecord).filter(InferenceRecord.inference_id == inference_id).first() else None

    # ------------------------------------------------------------- why flagged
    @staticmethod
    def why_flagged(db: Session, finding_id: str) -> Optional[Dict[str, Any]]:
        f = db.query(Finding).filter(Finding.finding_id == finding_id).first()
        if not f:
            return None
        passport = PassportService.build(db, f.asset_id)
        if passport is None:
            return {"finding": _f(f), "lineage": [], "evidence_by_layer": {}, "counter_evidence": [],
                    "limitations": [f.limitations] if f.limitations else [], "recommendation": None}
        by_layer: Dict[str, List[Dict[str, Any]]] = {}
        for e in passport["evidence"]:
            by_layer.setdefault(e["asset_type"], []).append(e)
        ac = AssuranceService.get_latest_assurance(db, f.case_id)
        convergence = json.loads(ac.convergence_json or "{}") if ac else {}
        independent = len(by_layer)
        return {
            "finding": _f(f),
            "question": f"Why is {f.asset_id} flagged?",
            "answer": (
                f"{f.severity} {f.finding_type.replace('_', ' ').lower()} on {f.asset_id}"
                + (f", and {independent - 1} other lifecycle layer(s) upstream also carry findings."
                   if independent > 1 else ".")
            ),
            "lineage": passport["lineage"],
            "evidence_by_layer": by_layer,
            "independent_paths": independent,
            "counter_evidence": passport["counter_evidence"],
            "coverage": passport["coverage"],
            "limitations": passport["limitations"],
            "case_convergence": convergence,
            "recommendation": passport["recommendation"],
        }
