"""
Authentication & RBAC: no anonymous access, no client-chosen roles,
no superuser bypass, least privilege per role.
"""
import jwt
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rbac import Permission, RBACService, Role
from app.core.security import create_access_token
from app.main import app

client = TestClient(app)
CASE = "CASE-2026-DRISHTRA-DEMO"


def test_permission_matrix_separation_of_duties():
    assert RBACService.has_permission(Role.REVIEWER_SUPERVISOR, Permission.DISPOSITION_DECIDE)
    for r in (Role.ML_ANALYST, Role.SECURITY_ANALYST, Role.AUDITOR, Role.ADMINISTRATOR):
        assert not RBACService.has_permission(r, Permission.DISPOSITION_DECIDE), r
    assert RBACService.has_permission(Role.SECURITY_ANALYST, Permission.DISPOSITION_RECOMMEND)
    assert not RBACService.has_permission(Role.ML_ANALYST, Permission.DISPOSITION_RECOMMEND)
    # Admin governs the platform but holds no assurance authority and cannot operate on assets
    assert RBACService.has_permission(Role.ADMINISTRATOR, Permission.USER_MANAGE)
    for p in (Permission.PIPELINE_RUN, Permission.DATASET_INGEST, Permission.ASSURANCE_BUILD, Permission.EVIDENCE_READ):
        assert not RBACService.has_permission(Role.ADMINISTRATOR, p), p
    # Auditor is read-only
    for p in (Permission.CASE_CREATE, Permission.PIPELINE_RUN, Permission.USER_MANAGE, Permission.DISPOSITION_RECOMMEND):
        assert not RBACService.has_permission(Role.AUDITOR, p), p


def test_login_rejects_bad_password_and_ignores_requested_role():
    r = client.post("/api/v1/auth/token", json={"username": "ml.analyst", "password": "wrong-password"})
    assert r.status_code == 401
    # A role in the request body is ignored: the role comes from the users table.
    r = client.post("/api/v1/auth/token", json={"username": "ml.analyst", "password": "Drishtra@2026",
                                                 "role": "ADMINISTRATOR"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "ML_ANALYST"


def test_unknown_user_gets_same_error_as_bad_password():
    a = client.post("/api/v1/auth/token", json={"username": "nobody.here", "password": "x"})
    b = client.post("/api/v1/auth/token", json={"username": "ml.analyst", "password": "x"})
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["message"] == b.json()["error"]["message"]


def test_no_anonymous_fallback():
    assert client.get("/api/v1/cases").status_code == 401
    assert client.post("/api/v1/cases", json={"name": "x"}).status_code == 401


def test_forged_and_role_escalated_tokens_rejected(as_role):
    assert client.get("/api/v1/cases", headers={"Authorization": "Bearer invalid.forged.jwt"}).status_code == 401
    # A token signed with a different key is rejected
    bad = jwt.encode({"sub": "x", "tv": 1, "iss": "drishtra"}, "not-the-key", algorithm="HS256")
    assert client.get("/api/v1/cases", headers={"Authorization": f"Bearer {bad}"}).status_code == 401
    # A validly signed token for a non-existent user is rejected
    ghost = create_access_token({"sub": "USR-GHOST", "tv": 1})
    assert client.get("/api/v1/cases", headers={"Authorization": f"Bearer {ghost}"}).status_code == 401


def test_role_hint_in_token_is_not_trusted(as_role):
    me = client.get("/api/v1/auth/me", headers=as_role("ML_ANALYST")).json()
    forged = create_access_token({"sub": me["user_id"], "tv": 1, "role_hint": "REVIEWER_SUPERVISOR",
                                  "role": "REVIEWER_SUPERVISOR"})
    r = client.post(f"/api/v1/assurance/{CASE}/decide", headers={"Authorization": f"Bearer {forged}"},
                    json={"disposition": "ACCEPT", "rationale": "attempted escalation via token claims"})
    assert r.status_code == 403


def test_ml_analyst_blocked_from_disposition(as_role):
    r = client.post(f"/api/v1/assurance/{CASE}/decide", headers=as_role("ML_ANALYST"),
                    json={"disposition": "ACCEPT", "rationale": "unauthorized attempt by analyst"})
    assert r.status_code == 403


def test_administrator_cannot_decide_or_read_findings(as_role):
    admin = as_role("ADMINISTRATOR")
    r = client.post(f"/api/v1/assurance/{CASE}/decide", headers=admin,
                    json={"disposition": "ACCEPT", "rationale": "admin attempting to override"})
    assert r.status_code == 403
    assert client.get("/api/v1/findings", headers=admin).status_code == 403
    assert client.post(f"/api/v1/cases/{CASE}/pipeline/run", headers=admin).status_code == 403


def test_security_events_least_privilege(as_role):
    assert client.get("/api/v1/platform/security-summary", headers=as_role("ML_ANALYST")).status_code == 403
    assert client.get("/api/v1/platform/security-summary", headers=as_role("SECURITY_ANALYST")).status_code == 200
    # Reviewers may read governance events but not other people's sign-in history
    r = client.get("/api/v1/platform/events?category=AUTH", headers=as_role("REVIEWER_SUPERVISOR"))
    assert r.status_code == 403
    r = client.get("/api/v1/platform/events?category=GOVERNANCE", headers=as_role("REVIEWER_SUPERVISOR"))
    assert r.status_code == 200


def test_denials_are_recorded(as_role):
    client.get("/api/v1/users", headers=as_role("AUDITOR"))
    events = client.get("/api/v1/platform/events?category=AUTHZ", headers=as_role("SECURITY_ANALYST")).json()["events"]
    assert any(e["action"] == "ACCESS_DENIED" and e["actor"] == "auditor" for e in events)


def test_secret_is_not_the_published_default():
    assert settings.SECRET_KEY != "drishtra-sovereign-defence-assurance-secret-key-2026"
    assert len(settings.SECRET_KEY) >= 32
