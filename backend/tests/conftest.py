"""
Test bootstrap: every session runs against a fresh, isolated SQLite vault and
storage root, so results never depend on a developer's local drishtra_vault.db.
Demo accounts are seeded through the real identity bootstrap.
"""
import os
import tempfile

_tmp_dir = tempfile.mkdtemp(prefix="drishtra_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp_dir, 'test_vault.db')}"
os.environ["BASE_STORAGE_DIR"] = os.path.join(_tmp_dir, "storage")
os.environ["DEMO_MODE"] = "true"
os.environ["IS_AIR_GAPPED"] = "true"            # tests never depend on a developer .env
os.environ["ALLOW_EXTERNAL_EXPLAINER"] = "false"
os.environ.setdefault("DRISHTRA_PBKDF2_ITERATIONS", "2000")  # fast hashing in tests only

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.database import engine, SessionLocal  # noqa: E402
from app.db.migrations import run_migrations  # noqa: E402
from app.services.user_service import UserService, DEMO_PASSWORD  # noqa: E402

run_migrations(engine)
_db = SessionLocal()
try:
    UserService.bootstrap(_db)
finally:
    _db.close()

ROLE_USERS = {
    "ML_ANALYST": "ml.analyst",
    "SECURITY_ANALYST": "sec.analyst",
    "REVIEWER_SUPERVISOR": "reviewer",
    "AUDITOR": "auditor",
    "ADMINISTRATOR": "admin",
}


@pytest.fixture(scope="session")
def client():
    from app.main import app
    return TestClient(app)


def login_headers(client, username, password=DEMO_PASSWORD):
    r = client.post("/api/v1/auth/token", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def as_role(client):
    cache = {}

    def _h(role: str):
        # Re-login if a test revoked the session (logout bumps token_version).
        if role not in cache or client.get("/api/v1/auth/me", headers=cache[role]).status_code == 401:
            cache[role] = login_headers(client, ROLE_USERS[role])
        return cache[role]
    return _h


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
