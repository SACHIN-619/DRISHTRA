"""
Network Isolation & Air-Gap Compliance Test
Section 29 of Technical Specification:
Proves that when IS_AIR_GAPPED=true, DRISHTRA requires:
- ZERO Internet access
- ZERO Neon cloud calls
- ZERO Grok/xAI external API calls
- ZERO telemetry calls
Any outbound external network connection causes immediate test failure.
"""
import socket
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.db.database import SessionLocal
from app.services.demo_service import DemoService

client = TestClient(app)

@pytest.fixture(autouse=True)
def guard_against_external_network(monkeypatch):
    """Intercepts and strictly forbids any socket connection to external non-loopback addresses."""
    original_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0] if isinstance(address, tuple) else address
        allowed_hosts = {"127.0.0.1", "localhost", "::1", "testserver"}
        if host not in allowed_hosts and not str(host).startswith("127."):
            raise ConnectionRefusedError(
                f"[SECURITY VIOLATION] DRISHTRA attempted external network connection to: {address}. "
                "Air-gapped operation strictly prohibits external calls!"
            )
        return original_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)

def test_air_gapped_configuration_flags():
    assert settings.IS_AIR_GAPPED is True
    # Default database must be local SQLite
    assert "sqlite" in settings.DATABASE_URL.lower()

def test_system_capabilities_endpoint_reports_air_gap():
    res = client.get("/api/v1/system/capabilities")
    assert res.status_code == 200
    data = res.json()
    assert data["air_gapped"] is True
    assert data["external_dependencies"] == []
    assert "COCO" in data["dataset_formats"]
    assert "ONNX" in data["model_formats"]
    assert len(data["detectors"]) >= 7

def test_system_info_endpoint(as_role):
    res = client.get("/api/v1/system/info", headers=as_role("ADMINISTRATOR"))
    assert res.status_code == 200
    data = res.json()
    assert data["environment"] == "air-gapped-development"
    assert data["is_air_gapped"] is True
    assert "sqlite" in data["database_url"].lower()


def test_offline_demo_pipeline_zero_external_network():
    db = SessionLocal()
    try:
        # Executes complete bootstrap and 18-stage pipeline under the active network guard
        demo_res = DemoService.bootstrap_demo_case(db=db, force_reset=False)
        assert demo_res["case_id"] == "CASE-2026-DRISHTRA-DEMO"
        # The machine never finalizes: the case waits for a human decision.
        assert demo_res["status"] in ["AWAITING_DECISION", "QUARANTINED", "ACCEPTED", "UNDER_REVIEW"]
        assert demo_res["recommended_disposition"] == "QUARANTINE"
    finally:
        db.close()
