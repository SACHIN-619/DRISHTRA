"""
Hardening tests: session edge cases, upload trust boundary, honest pipeline failure,
evidence that follows stored data, PostgreSQL column limits and air-gap honesty.
"""
import io
import json
import zipfile
from datetime import timedelta

import jwt
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings, database_is_local, database_host
from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------- sessions
def _admin_user_id(as_role):
    me = client.get("/api/v1/auth/me", headers=as_role("ADMINISTRATOR")).json()
    return me["user_id"] if "user_id" in me else me.get("id")


def test_expired_token_is_rejected(as_role):
    uid = _admin_user_id(as_role)
    tok = create_access_token({"sub": str(uid), "tv": 0}, expires_delta=timedelta(seconds=-5))
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
    assert "expired" in json.dumps(r.json()).lower()


def test_forged_token_signature_is_rejected(as_role):
    uid = _admin_user_id(as_role)
    forged = jwt.encode({"sub": str(uid), "tv": 0, "role_hint": "ADMINISTRATOR"}, "not-the-node-secret", algorithm="HS256")
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_alg_none_token_is_rejected(as_role):
    uid = _admin_user_id(as_role)
    unsigned = jwt.encode({"sub": str(uid), "tv": 0}, None, algorithm="none")
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {unsigned}"}).status_code == 401


def test_logout_revokes_existing_token():
    r = client.post("/api/v1/auth/token", json={"username": "auditor", "password": "Drishtra@2026"})
    assert r.status_code == 200, r.text
    tok = r.json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/api/v1/auth/me", headers=h).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=h).status_code in (200, 204)
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401


def test_overlong_username_does_not_break_the_ledger():
    r = client.post("/api/v1/auth/token", json={"username": "x" * 5000, "password": "whatever-123"})
    assert r.status_code in (401, 422)


# ---------------------------------------------------------------- uploads
def _case(h):
    cid = client.post("/api/v1/cases", headers=h, json={"name": "Hardening case", "classification": "RESTRICTED"}).json()["case_id"]
    con = client.post("/api/v1/contributors", headers=h, json={"case_id": cid, "name": "Vendor H", "contributor_type": "VENDOR"}).json()
    return cid, con["contributor_id"]


def test_unsupported_upload_extension_rejected(as_role):
    ml = as_role("ML_ANALYST")
    cid, con = _case(ml)
    r = client.post("/api/v1/datasets/upload", headers=ml,
                    data={"case_id": cid, "contributor_id": con, "dataset_name": "Bad", "format_type": "COCO"},
                    files={"file": ("payload.exe", b"MZ\x90\x00not a dataset", "application/octet-stream")})
    assert r.status_code == 400


def test_malformed_json_upload_rejected(as_role):
    ml = as_role("ML_ANALYST")
    cid, con = _case(ml)
    r = client.post("/api/v1/datasets/upload", headers=ml,
                    data={"case_id": cid, "contributor_id": con, "dataset_name": "Broken", "format_type": "COCO"},
                    files={"file": ("ann.json", b"{not json", "application/json")})
    assert r.status_code == 400


def test_auditor_cannot_upload(as_role):
    au = as_role("AUDITOR")
    r = client.post("/api/v1/datasets/upload", headers=au,
                    data={"case_id": "X", "contributor_id": "Y", "dataset_name": "Z", "format_type": "COCO"},
                    files={"file": ("ann.json", b"{}", "application/json")})
    assert r.status_code == 403


# ---------------------------------------------------------------- pipeline honesty
def _yolo_zip(n=4):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("classes.txt", "truck\ntank\n")
        for i in range(n):
            img = Image.new("RGB", (64, 64), (i * 50, 90 + i * 20, 220 - i * 45))
            for x in range(0, 64, 8):  # give each image distinct structure
                for y in range(0, 64, 8):
                    if (x * (i + 1) + y) % 3 == 0:
                        img.putpixel((x, y), (255, 255, 255))
            ib = io.BytesIO(); img.save(ib, "PNG")
            z.writestr(f"images/f{i}.png", ib.getvalue())
            z.writestr(f"labels/f{i}.txt", f"{i % 2} 0.5 0.5 0.2 0.2\n")
    return buf.getvalue()


def _upload_yolo(ml):
    cid, con = _case(ml)
    r = client.post("/api/v1/datasets/upload", headers=ml,
                    data={"case_id": cid, "contributor_id": con, "dataset_name": "Vendor YOLO H", "format_type": "YOLO"},
                    files={"file": ("ds.zip", _yolo_zip(), "application/zip")})
    assert r.status_code == 201, r.text
    return cid, r.json()["dataset_id"]


def test_stage_failure_halts_run_and_is_recorded(as_role, monkeypatch):
    from app.services.dataset_service import DatasetService
    ml = as_role("ML_ANALYST")
    cid, _ = _upload_yolo(ml)

    def boom(*a, **k):
        raise RuntimeError("detector crashed")
    monkeypatch.setattr(DatasetService, "scan_dataset", staticmethod(boom))
    run = client.post(f"/api/v1/cases/{cid}/pipeline/run", headers=ml).json()
    assert run["status"] == "FAILED"
    failed = [s for s in run["stages"] if s["status"] == "FAILED"]
    assert len(failed) == 1 and "detector crashed" in failed[0]["errors"][0]
    # nothing after the failed stage claims success
    idx = run["stages"].index(failed[0])
    assert idx == len(run["stages"]) - 1
    # and no assurance verdict was manufactured from a half-run
    stage_ids = [s["stage_id"] for s in run["stages"]]
    assert "STAGE_15_ASSURANCE_CASE_CONSTRUCTION" not in stage_ids


def test_mutating_stored_records_changes_the_evidence(as_role):
    """The pipeline scans what is stored — tampering with the stored dataset is detected on the next run."""
    from app.services.artifact_store import ArtifactStore
    ml = as_role("ML_ANALYST")
    cid, ds_id = _upload_yolo(ml)
    assert client.post(f"/api/v1/cases/{cid}/pipeline/run", headers=ml).json()["status"] == "COMPLETED"
    before = client.get(f"/api/v1/assurance/{cid}", headers=ml).json()["coverage"]["D1_EXACT_DUPLICATE"]["state"]
    assert before == "VERIFIED"

    payload, _ = ArtifactStore.load_dataset_records(ds_id)
    recs = payload["records"]
    recs[1]["sha256"] = recs[0]["sha256"]          # inject an exact duplicate
    ArtifactStore.save_dataset_records(ds_id, recs, payload.get("extras"))

    assert client.post(f"/api/v1/cases/{cid}/pipeline/run", headers=ml).json()["status"] == "COMPLETED"
    after = client.get(f"/api/v1/assurance/{cid}", headers=ml).json()["coverage"]["D1_EXACT_DUPLICATE"]["state"]
    assert after == "FINDING"


# ---------------------------------------------------------------- database / air-gap honesty
def test_platform_event_fields_are_clipped_to_column_limits(db_session):
    from app.services.platform_audit_service import PlatformAuditService
    ev = PlatformAuditService.record(db_session, category="AUTH", actor="a" * 900, action="LOGIN_FAILED" * 20,
                                     result="FAILURE", target="t" * 900)
    assert len(ev.actor) <= 128 and len(ev.target) <= 128 and len(ev.action) <= 64
    assert PlatformAuditService.verify(db_session)["status"] == "VALID"


def test_remote_database_is_never_reported_as_air_gapped():
    assert database_is_local("sqlite:///./drishtra_vault.db")
    assert database_is_local("postgresql://u:p@localhost:5432/db")
    assert not database_is_local("postgresql://u:p@ep-cool-name-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require")
    assert database_host("postgresql://u:p@ep-x.neon.tech/db") == "ep-x.neon.tech"


def test_health_reports_database_location():
    h = client.get("/health").json()
    assert h["database_location"] == ("local" if database_is_local() else "remote")
    assert h["air_gapped_mode"] is (settings.IS_AIR_GAPPED and database_is_local())
