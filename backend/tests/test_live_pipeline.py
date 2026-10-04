"""
Live pipeline streaming and the Attack Lab sandbox: every injected attack must be found
by the stage that owns that check, layered attacks must converge, and a reset must
return the sandbox to a clean ACCEPT.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.attack_lab_service import LAB_CASE_ID, SCENARIOS

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def seeded():
    from app.db.database import SessionLocal
    from app.services.demo_service import DemoService
    db = SessionLocal()
    try:
        DemoService.bootstrap_demo_case(db)
    finally:
        db.close()


def _stream(h, case_id=LAB_CASE_ID):
    r = client.post(f"/api/v1/cases/{case_id}/pipeline/stream", headers=h)
    assert r.status_code == 200, r.text
    return [json.loads(line) for line in r.text.splitlines() if line.strip()]


def _caught(events):
    out = set()
    for e in events:
        if e["type"] == "stage_completed":
            for c in e["stage"]["output_summary"].get("checks_executed", []):
                if c["outcome"] == "FINDING":
                    out.add((e["stage"]["stage_id"], c["check_id"]))
    return out


def _verdict(events):
    return [e for e in events if e["type"] == "assurance"][-1]["recommended_disposition"]


def test_stream_emits_every_stage_in_order(as_role):
    ml = as_role("ML_ANALYST")
    client.post("/api/v1/attack-lab/reset", headers=ml)
    ev = _stream(ml)
    assert ev[0]["type"] == "run_started" and len(ev[0]["stages"]) == 18
    started = [e["index"] for e in ev if e["type"] == "stage_started"]
    completed = [e["index"] for e in ev if e["type"] == "stage_completed"]
    assert started == completed == list(range(18))
    assert [e for e in ev if e["type"] == "run_finished"][0]["status"] == "COMPLETED"
    assert _verdict(ev) == "ACCEPT"
    assert ev[-1]["type"] == "assurance"


@pytest.mark.parametrize("scenario", [s["id"] for s in SCENARIOS])
def test_each_attack_is_caught_by_its_stage(as_role, scenario):
    ml = as_role("ML_ANALYST")
    spec = next(s for s in SCENARIOS if s["id"] == scenario)
    client.post("/api/v1/attack-lab/reset", headers=ml)
    r = client.post(f"/api/v1/attack-lab/{scenario}/inject", headers=ml)
    assert r.status_code == 200 and scenario in r.json()["active"]
    ev = _stream(ml)
    caught = _caught(ev)
    assert any((spec["expected_stage"], c) in caught for c in spec["expected_checks"]), caught
    assert _verdict(ev) in ("REVIEW", "QUARANTINE")
    client.post("/api/v1/attack-lab/reset", headers=ml)
    assert _verdict(_stream(ml)) == "ACCEPT"


def test_layered_attacks_converge_on_the_contributor(as_role):
    ml = as_role("ML_ANALYST")
    client.post("/api/v1/attack-lab/reset", headers=ml)
    for sc in ("poison_dataset", "backdoor_model", "tamper_inference"):
        client.post(f"/api/v1/attack-lab/{sc}/inject", headers=ml)
    ev = _stream(ml)
    assert _verdict(ev) == "QUARANTINE"
    ac = client.get(f"/api/v1/assurance/{LAB_CASE_ID}", headers=ml).json()
    assert ac["convergence"]["converged"] is True
    assert set(ac["convergence"]["contributors"][0]["layers"]) == {"DATASET", "MODEL", "INFERENCE"}
    client.post("/api/v1/attack-lab/reset", headers=ml)


def test_attack_lab_is_recorded_in_the_case_ledger(as_role):
    ml = as_role("ML_ANALYST")
    client.post("/api/v1/attack-lab/swap_model/inject", headers=ml)
    client.post("/api/v1/attack-lab/reset", headers=ml)
    au = as_role("AUDITOR")
    v = client.post(f"/api/v1/audit/{LAB_CASE_ID}/verify", headers=au)
    assert v.status_code == 200, v.text
    assert v.json()["status"] == "VALID"
    events = client.get(f"/api/v1/audit/{LAB_CASE_ID}", headers=au)
    if events.status_code == 200:
        assert any(e.get("action") == "ATTACK_LAB_INJECTED" for e in (events.json() if isinstance(events.json(), list) else events.json().get("events", [])))


def test_only_permitted_roles_can_attack(as_role):
    for role in ("AUDITOR", "REVIEWER_SUPERVISOR", "ADMINISTRATOR"):
        assert client.post("/api/v1/attack-lab/swap_model/inject", headers=as_role(role)).status_code == 403
    assert client.post("/api/v1/attack-lab/not_a_thing/inject", headers=as_role("ML_ANALYST")).status_code == 400


def test_stream_requires_pipeline_permission(as_role):
    assert client.post(f"/api/v1/cases/{LAB_CASE_ID}/pipeline/stream", headers=as_role("AUDITOR")).status_code == 403
