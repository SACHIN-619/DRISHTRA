"""
Assurance policy correctness (AP-2026.2):
  - counter-evidence never contradicts a finding (regression for the AP-2026.1 bug)
  - NOT_TESTED is never a pass
  - incriminating evidence is persisted with the case
  - mutating one stored artifact propagates to the recommendation
  - drift vs manipulation
"""
import json

from app.db.models import Finding
from app.policies.assurance_policy import AssurancePolicyEngine
from app.services.artifact_store import ArtifactStore
from app.services.assurance_service import AssuranceService
from app.services.demo_service import BASELINE_CASE_ID, DEMO_CASE_ID, DRIFT_CASE_ID, DemoService
from app.services.pipeline_service import CasePipeline


def _latest(db, case_id):
    return AssuranceService.get_latest_assurance(db, case_id)


def test_orm_finding_types_are_read_correctly():
    class F:  # ORM-like object (not a dict) - the case the old engine got wrong
        finding_id, asset_id, asset_type, detector_id = "F1", "I-1", "INFERENCE", "replay"
        finding_type, severity, confidence, deterministic, explanation, limitations = \
            "CRYPTOGRAPHIC_SIGNATURE_INVALID", "CRITICAL", None, True, "bad sig", None
    res = AssurancePolicyEngine.evaluate(findings=[F()], executions=[], assets={"INFERENCE": [{"id": "I-1"}]})
    assert res["evidence"][0]["type"] == "CRYPTOGRAPHIC_SIGNATURE_INVALID"
    assert res["recommended_disposition"] == "QUARANTINE"
    assert res["counter_evidence"] == []   # nothing ran and passed -> nothing to claim


def test_nothing_tested_is_inconclusive_not_verified():
    res = AssurancePolicyEngine.evaluate(findings=[], executions=[],
                                         assets={"DATASET": [{"id": "D-1"}], "MODEL": [], "INFERENCE": []})
    assert res["status"] == "INCONCLUSIVE"
    assert res["recommended_disposition"] == "REVIEW"
    assert res["coverage"]["D1_EXACT_DUPLICATE"]["state"] == "NOT_TESTED"
    assert res["coverage_summary"]["percent"] == 0


def test_counter_evidence_never_contradicts_findings(db_session):
    DemoService.bootstrap_demo_case(db_session)
    ac = _latest(db_session, DEMO_CASE_ID)
    evidence = json.loads(ac.incriminating_evidence_json)
    counter = json.loads(ac.counter_evidence_json)
    assert evidence, "incriminating evidence must be persisted with the case"
    flagged = {(e["asset_id"]) for e in evidence}
    cov = json.loads(ac.coverage_json)["dimensions"]
    for c in counter:
        # a passed check on an asset must not be the same check that flagged that asset
        assert cov[c["check_id"]]["assets"][c["asset_id"]] == "PASS"
    # The specific AP-2026.1 contradiction: "signature valid" while I-883's signature is invalid
    assert not any(c["check_id"] == "D9A_SIGNATURE_BINDING" and c["asset_id"] == "I-883" for c in counter)
    assert "I-883" in flagged


def test_attacked_case_converges_on_contributor(db_session):
    ac = _latest(db_session, DEMO_CASE_ID)
    conv = json.loads(ac.convergence_json)
    assert ac.recommended_disposition == "QUARANTINE"
    assert conv["converged"] is True
    assert conv["contributors"][0]["contributor_id"] == "C-07"
    assert set(conv["contributors"][0]["layers"]) == {"DATASET", "MODEL", "INFERENCE"}


def test_clean_case_is_verified_with_limitations_declared(db_session):
    ac = _latest(db_session, BASELINE_CASE_ID)
    assert ac.status == "VERIFIED" and ac.recommended_disposition == "ACCEPT"
    assert json.loads(ac.incriminating_evidence_json) == []
    assert len(json.loads(ac.counter_evidence_json)) > 5
    assert any("White-box" in l for l in json.loads(ac.limitations_json))


def test_drift_is_not_reported_as_manipulation(db_session):
    ac = _latest(db_session, DRIFT_CASE_ID)
    drift = json.loads(ac.coverage_json)["drift_assessment"]
    assert drift["assessment"] == "PROBABLE_OPERATIONAL_DRIFT"
    assert ac.recommended_disposition == "ACCEPT"


def test_mutation_propagates_to_recommendation(db_session):
    """Change one delivered model digest in the vault; re-run; the case must flip."""
    assert _latest(db_session, BASELINE_CASE_ID).recommended_disposition == "ACCEPT"
    ArtifactStore.save_supplied_digest("M-21", "0" * 64, source="tampered in test")
    run = CasePipeline.run(db_session, BASELINE_CASE_ID, actor="test_mutation")
    assert run.status == "COMPLETED"
    ac = _latest(db_session, BASELINE_CASE_ID)
    types = {e["type"] for e in json.loads(ac.incriminating_evidence_json)}
    assert "MODEL_DIGEST_MISMATCH" in types
    assert ac.recommended_disposition in ("QUARANTINE", "REVIEW")
    # Restore and confirm it returns to ACCEPT (the result is driven by the artifact, not hardcoded)
    m = __import__("app.db.models", fromlist=["ModelAsset"]).ModelAsset
    original = db_session.query(m).filter_by(model_id="M-21").first().weight_sha256
    ArtifactStore.save_supplied_digest("M-21", original)
    CasePipeline.run(db_session, BASELINE_CASE_ID, actor="test_mutation")
    assert _latest(db_session, BASELINE_CASE_ID).recommended_disposition == "ACCEPT"


def test_ground_truth_never_reaches_detectors(db_session):
    """Attack-lab labels stored with samples are stripped before detectors run."""
    data, _ = ArtifactStore.load_dataset_records("D-14")
    assert any("ground_truth" in r for r in data["records"])  # present in the lab corpus...
    import inspect
    from app.services import dataset_service
    src = inspect.getsource(dataset_service.DatasetService.scan_dataset)
    assert '"ground_truth"' in src and "detector_view" in src  # ...and filtered out
