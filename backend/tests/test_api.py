"""
Integration tests for the REST API (authenticated, role-scoped).
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["system"] == "DRISHTRA"
    assert data["air_gapped_mode"] is True


def test_operational_endpoints_require_authentication():
    for path in ["/api/v1/cases", "/api/v1/findings", "/api/v1/assurance/queue", "/api/v1/users"]:
        assert client.get(path).status_code == 401, path


def test_case_lifecycle(as_role):
    ml = as_role("ML_ANALYST")
    res = client.post("/api/v1/cases", headers=ml, json={
        "name": "Border Sector Recon Sentinel V1", "description": "Tactical assurance evaluation",
        "classification": "RESTRICTED"})
    assert res.status_code == 201
    case_id = res.json()["case_id"]
    assert case_id.startswith("CASE-")

    res_c = client.post("/api/v1/contributors", headers=ml, json={
        "case_id": case_id, "name": "Robotics Wing (synthetic)", "contributor_type": "LAB"})
    assert res_c.status_code == 201
    contrib_id = res_c.json()["contributor_id"]

    res_d = client.post("/api/v1/datasets/register", headers=ml, json={
        "case_id": case_id, "contributor_id": contrib_id, "name": "Thermal Recon Dataset Split",
        "format": "COCO", "version": "1.0.0", "sample_count": 50})
    assert res_d.status_code == 201
    dataset_id = res_d.json()["dataset_id"]

    # Passport of an unscanned dataset: every dataset check is NOT_TESTED, never a pass.
    pas = client.get(f"/api/v1/datasets/{dataset_id}/passport", headers=ml).json()
    assert pas["asset_id"] == dataset_id
    assert set(pas["coverage_matrix"].values()) == {"NOT_TESTED"}
    assert pas["counter_evidence"] == []

    # ML analysts cannot build assurance cases; security analysts can.
    assert client.post(f"/api/v1/cases/{case_id}/assess", headers=ml).status_code == 403
    ass = client.post(f"/api/v1/cases/{case_id}/assess", headers=as_role("SECURITY_ANALYST"))
    assert ass.status_code == 200
    ass_data = ass.json()
    # Nothing was tested, so the honest answer is INCONCLUSIVE, not VERIFIED.
    assert ass_data["status"] == "INCONCLUSIVE"
    assert ass_data["recommended_disposition"] == "REVIEW"

    aud = client.post(f"/api/v1/cases/{case_id}/audit/verify", headers=as_role("AUDITOR"))
    assert aud.status_code == 200
    assert aud.json()["status"] == "VALID"


def test_assurance_runs_endpoint(as_role):
    from app.db.database import SessionLocal
    from app.services.demo_service import DemoService
    db = SessionLocal()
    try:
        DemoService.bootstrap_demo_case(db)
    finally:
        db.close()

    res = client.post("/api/v1/assurance-runs", headers=as_role("ML_ANALYST"), json={
        "case_id": "CASE-2026-DRISHTRA-DEMO", "dataset_id": "D-14", "model_id": "M-04", "execution_mode": "OFFLINE"})
    assert res.status_code in [200, 201], res.text
    run_data = res.json()
    assert run_data["assurance_run_id"].startswith("AR-")
    assert run_data["status"].startswith("AWAITING_DECISION")
    assert "QUARANTINE" in run_data["status"]

    res_list = client.get("/api/v1/assurance-runs", headers=as_role("AUDITOR"))
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1
