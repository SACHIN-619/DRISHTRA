"""
Identity lifecycle and decision governance:
admin-only account creation, first-login password change, lockout,
role change revokes sessions, append-only signed decisions, self-approval block,
tamper-evident platform ledger.
"""
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.models import AssuranceDecision, PlatformEvent
from app.main import app

client = TestClient(app)
CASE = "CASE-2026-DRISHTRA-DEMO"


def _login(username, password):
    return client.post("/api/v1/auth/token", json={"username": username, "password": password})


def test_no_public_registration():
    paths = list(app.openapi()["paths"].keys())
    assert not any("register" in p and "auth" in p for p in paths)
    assert not any(p.startswith("/api/v1/auth/sign") for p in paths)
    assert client.post("/api/v1/users", json={"username": "x", "full_name": "x", "role": "AUDITOR"}).status_code == 401


def test_admin_creates_user_who_must_change_password(as_role):
    admin = as_role("ADMINISTRATOR")
    assert client.post("/api/v1/users", headers=as_role("SECURITY_ANALYST"),
                       json={"username": "eve.x", "full_name": "Eve", "role": "ADMINISTRATOR"}).status_code == 403
    r = client.post("/api/v1/users", headers=admin,
                    json={"username": "priya.n", "full_name": "Priya N", "role": "AUDITOR", "access_scope": "RESTRICTED"})
    assert r.status_code == 201, r.text
    temp = r.json()["temporary_password"]
    tok = _login("priya.n", temp).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    # Temporary password: only profile + password change are allowed
    assert client.get("/api/v1/auth/me", headers=h).json()["must_change_password"] is True
    assert client.get("/api/v1/cases", headers=h).status_code == 403
    weak = client.post("/api/v1/auth/change-password", headers=h, json={"current_password": temp, "new_password": "short"})
    assert weak.status_code == 400
    ok = client.post("/api/v1/auth/change-password", headers=h,
                     json={"current_password": temp, "new_password": "Audit-Trail-2026!"})
    assert ok.status_code == 200
    # Old token is revoked; the new one works
    assert client.get("/api/v1/cases", headers=h).status_code == 401
    h2 = {"Authorization": f"Bearer {ok.json()['access_token']}"}
    assert client.get("/api/v1/cases", headers=h2).status_code == 200
    ev = client.get("/api/v1/platform/events?category=GOVERNANCE", headers=admin).json()["events"]
    assert any(e["action"] == "USER_CREATED" and e["target"] == "priya.n" and e["actor"] == "admin" for e in ev)


def test_role_change_and_disable_revoke_sessions(as_role):
    admin = as_role("ADMINISTRATOR")
    r = client.post("/api/v1/users", headers=admin, json={"username": "temp.ops", "full_name": "Temp", "role": "ML_ANALYST"})
    uid, temp = r.json()["user"]["user_id"], r.json()["temporary_password"]
    tok = client.post("/api/v1/auth/change-password",
                      headers={"Authorization": f"Bearer {_login('temp.ops', temp).json()['access_token']}"},
                      json={"current_password": temp, "new_password": "Temp-Ops-Pass-77"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/api/v1/cases", headers=h).status_code == 200
    client.patch(f"/api/v1/users/{uid}/role", headers=admin, json={"role": "AUDITOR"})
    assert client.get("/api/v1/cases", headers=h).status_code == 401  # session revoked
    client.patch(f"/api/v1/users/{uid}/status", headers=admin, json={"status": "DISABLED"})
    assert _login("temp.ops", "Temp-Ops-Pass-77").status_code == 401


def test_admin_cannot_demote_or_disable_self(as_role):
    admin = as_role("ADMINISTRATOR")
    me = client.get("/api/v1/auth/me", headers=admin).json()
    assert client.patch(f"/api/v1/users/{me['user_id']}/role", headers=admin, json={"role": "AUDITOR"}).status_code == 409
    assert client.patch(f"/api/v1/users/{me['user_id']}/status", headers=admin, json={"status": "DISABLED"}).status_code == 409


def test_lockout_after_repeated_failures(as_role):
    admin = as_role("ADMINISTRATOR")
    r = client.post("/api/v1/users", headers=admin, json={"username": "lock.me", "full_name": "Lock", "role": "AUDITOR"})
    temp = r.json()["temporary_password"]
    for _ in range(settings.MAX_FAILED_LOGINS):
        assert _login("lock.me", "nope").status_code == 401
    assert _login("lock.me", temp).status_code == 423  # locked even with the right password


def test_decisions_are_append_only_signed_and_separated(as_role, db_session):
    from app.services.demo_service import DemoService
    DemoService.bootstrap_demo_case(db_session)
    sec, rev = as_role("SECURITY_ANALYST"), as_role("REVIEWER_SUPERVISOR")

    # Security analyst recommends
    r = client.post(f"/api/v1/assurance/{CASE}/recommend", headers=sec,
                    json={"disposition": "QUARANTINE", "rationale": "Three evidence paths converge on C-07."})
    assert r.status_code == 200, r.text
    # ...but cannot finalize
    assert client.post(f"/api/v1/assurance/{CASE}/decide", headers=sec,
                       json={"disposition": "QUARANTINE", "rationale": "trying to finalize own case"}).status_code == 403
    # Rationale is mandatory
    assert client.post(f"/api/v1/assurance/{CASE}/decide", headers=rev,
                       json={"disposition": "QUARANTINE", "rationale": ""}).status_code == 422

    d1 = client.post(f"/api/v1/assurance/{CASE}/decide", headers=rev,
                     json={"disposition": "QUARANTINE", "rationale": "Converging evidence; block downstream use."})
    assert d1.status_code == 200
    d2 = client.post(f"/api/v1/assurance/{CASE}/decide", headers=rev,
                     json={"disposition": "REVIEW", "rationale": "Re-opened for vendor response; still blocked."})
    assert d2.status_code == 200
    hist = client.get(f"/api/v1/assurance/{CASE}/decisions", headers=as_role("AUDITOR")).json()["items"]
    finals = [h for h in hist if h["kind"] == "DISPOSITION"]
    assert [f["disposition"] for f in finals][-2:] == ["QUARANTINE", "REVIEW"]   # history kept
    assert finals[-1]["supersedes_decision_id"] == finals[-2]["decision_id"]
    assert all(h["signature"] for h in hist)
    v = client.post(f"/api/v1/assurance/{CASE}/decisions/verify", headers=as_role("AUDITOR")).json()
    assert v["status"] == "VALID"

    # Tamper with a stored decision -> verification fails
    row = db_session.query(AssuranceDecision).filter_by(decision_id=finals[-2]["decision_id"]).first()
    original = row.disposition
    row.disposition = "ACCEPT"
    db_session.commit()
    assert client.post(f"/api/v1/assurance/{CASE}/decisions/verify", headers=as_role("AUDITOR")).json()["status"] == "BROKEN"
    row.disposition = original
    db_session.commit()


def test_reviewer_cannot_decide_evaluation_they_initiated(db_session):
    from app.services.assurance_service import AssuranceService, SeparationOfDutiesError
    import pytest
    AssuranceService.assess_case(db_session, CASE, actor="reviewer")
    with pytest.raises(SeparationOfDutiesError):
        AssuranceService.record_decision(db_session, CASE, "DISPOSITION", "ACCEPT",
                                         "self-approval should be blocked", actor="reviewer",
                                         actor_role="REVIEWER_SUPERVISOR")
    AssuranceService.assess_case(db_session, CASE, actor="pipeline_orchestrator")


def test_platform_ledger_detects_tampering(as_role, db_session):
    auditor = as_role("AUDITOR")
    assert client.post("/api/v1/platform/events/verify", headers=auditor).json()["status"] == "VALID"
    ev = db_session.query(PlatformEvent).filter_by(action="USER_CREATED").first()
    original = ev.actor
    ev.actor = "someone_else"
    db_session.commit()
    assert client.post("/api/v1/platform/events/verify", headers=auditor).json()["status"] == "BROKEN"
    ev.actor = original
    db_session.commit()
    assert client.post("/api/v1/platform/events/verify", headers=auditor).json()["status"] == "VALID"
