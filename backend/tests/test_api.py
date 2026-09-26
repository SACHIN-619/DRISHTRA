"""
Integration Tests for DRISHTRA REST API Endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["system"] == "DRISHTRA"
    assert data["air_gapped_mode"] is True

def test_case_lifecycle():
    # 1. Create Case
    res = client.post("/api/v1/cases", json={
        "name": "Border Sector Recon Sentinel V1",
        "description": "Tactical assurance evaluation",
        "classification": "RESTRICTED"
    })
    assert res.status_code == 201
    case_data = res.json()
    case_id = case_data["case_id"]
    assert case_id.startswith("CASE-")

    # 2. Register Contributor
    res_c = client.post("/api/v1/contributors", json={
        "case_id": case_id,
        "name": "CAIR Robotics Wing",
        "contributor_type": "LAB"
    })
    assert res_c.status_code == 201
    contrib_id = res_c.json()["contributor_id"]

    # 3. Register Dataset
    res_d = client.post("/api/v1/datasets/register", json={
        "case_id": case_id,
        "contributor_id": contrib_id,
        "name": "Thermal Recon Dataset Split",
        "format": "COCO",
        "version": "1.0.0",
        "sample_count": 50
    })
    assert res_d.status_code == 201
    dataset_id = res_d.json()["dataset_id"]

    # 4. Check Dataset Passport
    res_pass = client.get(f"/api/v1/datasets/{dataset_id}/passport")
    assert res_pass.status_code == 200
    pass_data = res_pass.json()
    assert pass_data["asset_id"] == dataset_id
    assert "exact_duplicate_detection" in pass_data["coverage_matrix"]

    # 5. Assess Case
    res_ass = client.post(f"/api/v1/cases/{case_id}/assess", json={"policy_version": "DRISHTRA-AP-2026.1"})
    assert res_ass.status_code == 200
    ass_data = res_ass.json()
    assert ass_data["recommended_disposition"] in ["ACCEPT", "REVIEW", "QUARANTINE"]

    # 6. Verify Audit Ledger
    res_aud = client.post(f"/api/v1/cases/{case_id}/audit/verify")
    assert res_aud.status_code == 200
    assert res_aud.json()["status"] == "VALID"
