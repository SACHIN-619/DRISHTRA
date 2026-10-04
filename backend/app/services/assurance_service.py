"""
Assurance case construction and human decision recording.

assess_case():
    gathers the case inventory (datasets, models, inferences + lineage), the
    latest execution of every check on every asset, and the findings those
    executions produced; runs the policy engine; stores the full result,
    including the incriminating evidence.

record_decision():
    appends a signed, hash-linked RECOMMENDATION (security analyst) or
    DISPOSITION (reviewer) row. Enforces separation of duties.
"""
import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.crypto.chain import GENESIS_HASH, compute_chained_hash
from app.crypto.crypto_service import CryptoService, KeyManagementInterface
from app.db.models import (
    AssuranceCase, AssuranceDecision, Case, CheckExecution, Dataset, EvidenceEdge,
    Finding, InferenceRecord, ModelAsset, utc_now_iso,
)
from app.policies.assurance_policy import AssurancePolicyEngine
from app.services.audit_service import AuditService
from app.services.evidence_writer import CHECK_CATALOG

CASE_STATUS_AFTER_DECISION = {"ACCEPT": "ACCEPTED", "REVIEW": "UNDER_REVIEW", "QUARANTINE": "QUARANTINED"}


class SeparationOfDutiesError(Exception):
    pass


class AssuranceService:
    # ----------------------------------------------------------------- inputs
    @staticmethod
    def collect_inputs(db: Session, case_id: str) -> Dict[str, Any]:
        datasets = db.query(Dataset).filter(Dataset.case_id == case_id).all()
        models = db.query(ModelAsset).filter(ModelAsset.case_id == case_id).all()
        inferences = db.query(InferenceRecord).filter(InferenceRecord.case_id == case_id).all()
        edges = db.query(EvidenceEdge).filter(EvidenceEdge.case_id == case_id).all()

        trained_from: Dict[str, List[str]] = {}
        for e in edges:
            if e.relationship == "trained_from" and e.source_node.startswith("dataset:") and e.target_node.startswith("model:"):
                trained_from.setdefault(e.target_node.split(":", 1)[1], []).append(e.source_node.split(":", 1)[1])

        assets = {
            "DATASET": [{"id": d.dataset_id, "contributor_id": d.contributor_id, "name": d.name} for d in datasets],
            "MODEL": [{"id": m.model_id, "contributor_id": m.contributor_id, "name": m.name,
                       "access_level": m.access_level, "trained_from": trained_from.get(m.model_id, [])} for m in models],
            "INFERENCE": [{"id": i.inference_id, "model_id": i.model_id,
                           "verification_status": i.verification_status} for i in inferences],
        }

        # Latest execution per (asset, check)
        rows = db.query(CheckExecution).filter(CheckExecution.case_id == case_id) \
            .order_by(CheckExecution.executed_at.asc()).all()
        # Only assets that still exist in the case count: a withdrawn record (e.g. a removed
        # replayed attestation) must not keep driving the verdict.
        present = {a["id"] for group in assets.values() for a in group}
        latest: Dict[tuple, CheckExecution] = {}
        for r in rows:
            if r.asset_id in present:
                latest[(r.asset_id, r.check_id)] = r
        executions = [{
            "execution_id": r.execution_id, "asset_type": r.asset_type, "asset_id": r.asset_id,
            "check_id": r.check_id, "detector_id": r.detector_id, "outcome": r.outcome,
            "detail": r.detail, "executed_at": r.executed_at,
            "finding_ids": json.loads(r.finding_ids_json or "[]"),
        } for r in latest.values()]

        # Current findings = findings produced by the latest execution of a check,
        # plus legacy findings that were never linked to a check execution.
        current_ids = {fid for e in executions for fid in e["finding_ids"]}
        linked_ids = {fid for r in rows for fid in json.loads(r.finding_ids_json or "[]")}
        all_findings = db.query(Finding).filter(Finding.case_id == case_id).all()
        findings = [f for f in all_findings
                    if f.finding_id in current_ids or (f.finding_id not in linked_ids and f.asset_id in present)]

        return {"assets": assets, "executions": executions, "findings": findings}

    # ----------------------------------------------------------------- assess
    @staticmethod
    def assess_case(
        db: Session,
        case_id: str,
        policy_version: Optional[str] = None,
        actor: str = "assurance_engine",
    ) -> AssuranceCase:
        case = db.query(Case).filter(Case.case_id == case_id).first()
        if not case:
            raise ValueError(f"Case {case_id} not found")

        inputs = AssuranceService.collect_inputs(db, case_id)
        result = AssurancePolicyEngine.evaluate(
            findings=inputs["findings"], executions=inputs["executions"],
            assets=inputs["assets"], catalog=CHECK_CATALOG,
        )

        ac = AssuranceCase(
            assurance_id=f"AC-{uuid.uuid4().hex[:8].upper()}",
            case_id=case_id,
            claim=result["claim"],
            status=result["status"],
            recommended_disposition=result["recommended_disposition"],
            supporting_evidence_json=json.dumps(result["supporting_evidence"]),
            incriminating_evidence_json=json.dumps(result["evidence"]),
            counter_evidence_json=json.dumps(result["counter_evidence"]),
            coverage_json=json.dumps({
                "dimensions": result["coverage"],
                "summary": result["coverage_summary"],
                "rules_fired": result["rules_fired"],
                "severity_counts": result["severity_counts"],
                "drift_assessment": result["drift_assessment"],
            }),
            convergence_json=json.dumps(result["convergence"]),
            limitations_json=json.dumps(result["limitations"]),
            initiated_by=actor,
            policy_version=AssurancePolicyEngine.POLICY_VERSION,
            created_at=utc_now_iso(),
        )
        db.add(ac)
        # A new evaluation re-opens the decision: the case awaits a human again.
        case.status = "AWAITING_DECISION"
        case.updated_at = utc_now_iso()
        db.commit()
        db.refresh(ac)

        AuditService.record_event(
            db=db, case_id=case_id, actor=actor, action="ASSURANCE_CASE_CONSTRUCTED",
            asset_id=ac.assurance_id, result=result["status"],
            reason=json.dumps({
                "recommended": result["recommended_disposition"],
                "coverage_percent": result["coverage_summary"]["percent"],
                "rules": result["rules_fired"],
                "evidence": [e["finding_id"] for e in result["evidence"]],
            }, sort_keys=True),
        )
        return ac

    @staticmethod
    def get_latest_assurance(db: Session, case_id: str) -> Optional[AssuranceCase]:
        return db.query(AssuranceCase).filter(AssuranceCase.case_id == case_id) \
            .order_by(AssuranceCase.created_at.desc()).first()

    # ----------------------------------------------------------------- decide
    @staticmethod
    def decision_payload(d: AssuranceDecision) -> Dict[str, Any]:
        return {
            "decision_id": d.decision_id, "case_id": d.case_id, "assurance_id": d.assurance_id,
            "sequence": d.sequence, "kind": d.kind, "disposition": d.disposition,
            "rationale": d.rationale, "actor": d.actor, "actor_role": d.actor_role,
            "machine_recommendation": d.machine_recommendation,
            "supersedes_decision_id": d.supersedes_decision_id, "decided_at": d.decided_at,
            "previous_decision_hash": d.previous_decision_hash,
        }

    @staticmethod
    def list_decisions(db: Session, case_id: str) -> List[AssuranceDecision]:
        return db.query(AssuranceDecision).filter(AssuranceDecision.case_id == case_id) \
            .order_by(AssuranceDecision.sequence.asc()).all()

    @staticmethod
    def record_decision(
        db: Session, case_id: str, kind: str, disposition: str, rationale: str,
        actor: str, actor_role: str,
    ) -> AssuranceDecision:
        disposition = disposition.upper()
        if disposition not in ("ACCEPT", "REVIEW", "QUARANTINE"):
            raise ValueError("disposition must be ACCEPT, REVIEW or QUARANTINE")
        if not rationale or len(rationale.strip()) < 10:
            raise ValueError("A rationale of at least 10 characters is required for the record.")
        ac = AssuranceService.get_latest_assurance(db, case_id)
        if not ac:
            raise LookupError(f"No assurance case has been constructed for {case_id}.")

        if kind == "DISPOSITION":
            # Separation of duties: whoever triggered the evaluation, or recommended
            # on it, cannot be the one who signs it off.
            if ac.initiated_by == actor:
                raise SeparationOfDutiesError(
                    "You initiated this assurance evaluation, so you cannot finalize it. "
                    "Another authorized reviewer must decide.")
            recommended_by_actor = db.query(AssuranceDecision).filter(
                AssuranceDecision.assurance_id == ac.assurance_id,
                AssuranceDecision.kind == "RECOMMENDATION",
                AssuranceDecision.actor == actor,
            ).first()
            if recommended_by_actor:
                raise SeparationOfDutiesError("You recommended a disposition on this case, so you cannot finalize it.")

        prev = db.query(AssuranceDecision).filter(AssuranceDecision.case_id == case_id) \
            .order_by(AssuranceDecision.sequence.desc()).first()
        prev_disposition = db.query(AssuranceDecision).filter(
            AssuranceDecision.case_id == case_id, AssuranceDecision.kind == kind
        ).order_by(AssuranceDecision.sequence.desc()).first()

        d = AssuranceDecision(
            decision_id=f"DEC-{uuid.uuid4().hex[:10].upper()}",
            case_id=case_id, assurance_id=ac.assurance_id,
            sequence=(prev.sequence + 1) if prev else 1,
            kind=kind, disposition=disposition, rationale=rationale.strip(),
            actor=actor, actor_role=actor_role,
            machine_recommendation=ac.recommended_disposition,
            supersedes_decision_id=prev_disposition.decision_id if prev_disposition else None,
            decided_at=utc_now_iso(),
            previous_decision_hash=prev.decision_hash if prev else GENESIS_HASH,
            decision_hash="",
        )
        payload = AssuranceService.decision_payload(d)
        d.decision_hash = compute_chained_hash(d.previous_decision_hash, payload)
        d.signature = CryptoService.sign({"decision_hash": d.decision_hash, **payload}).hex()
        d.signer_key_fingerprint = KeyManagementInterface.public_key_fingerprint()
        db.add(d)

        if kind == "DISPOSITION":
            # Denormalised "latest decision" pointer for quick reads; history lives in assurance_decisions.
            ac.human_disposition = disposition
            ac.approved_by = actor
            ac.approved_at = d.decided_at
            ac.approval_notes = d.rationale
            case = db.query(Case).filter(Case.case_id == case_id).first()
            case.status = CASE_STATUS_AFTER_DECISION[disposition]
            case.updated_at = utc_now_iso()
        db.commit()
        db.refresh(d)

        AuditService.record_event(
            db=db, case_id=case_id, actor=actor,
            action="DISPOSITION_RECOMMENDED" if kind == "RECOMMENDATION" else f"DISPOSITION_{disposition}",
            asset_id=d.decision_id, result=disposition,
            reason=json.dumps({
                "assurance_id": ac.assurance_id, "machine_recommendation": ac.recommended_disposition,
                "supersedes": d.supersedes_decision_id, "decision_hash": d.decision_hash,
                "rationale": d.rationale,
            }, sort_keys=True),
        )
        return d

    @staticmethod
    def verify_decisions(db: Session, case_id: str) -> Dict[str, Any]:
        _, pub = KeyManagementInterface.get_sovereign_node_keypair()
        expected_prev = GENESIS_HASH
        rows = AssuranceService.list_decisions(db, case_id)
        for d in rows:
            payload = AssuranceService.decision_payload(d)
            if d.previous_decision_hash != expected_prev:
                return {"status": "BROKEN", "failure_decision": d.decision_id, "reason": "chain link mismatch"}
            if compute_chained_hash(d.previous_decision_hash, payload) != d.decision_hash:
                return {"status": "BROKEN", "failure_decision": d.decision_id, "reason": "content altered"}
            if not d.signature or not CryptoService.verify(pub, d.signature, {"decision_hash": d.decision_hash, **payload}):
                return {"status": "BROKEN", "failure_decision": d.decision_id, "reason": "signature invalid"}
            expected_prev = d.decision_hash
        return {"status": "VALID", "verified_count": len(rows),
                "signer_key_fingerprint": KeyManagementInterface.public_key_fingerprint()}

    @staticmethod
    def serialize_decision(d: AssuranceDecision) -> Dict[str, Any]:
        out = AssuranceService.decision_payload(d)
        out.update({"decision_hash": d.decision_hash, "signature": d.signature,
                    "signer_key_fingerprint": d.signer_key_fingerprint})
        return out
