"""
DRISHTRA System Observability & Capability Discovery API Endpoints
Provides:
- GET /health (Liveness probe)
- GET /ready (Readiness probe: database & storage checks)
- GET /api/v1/system/info (System metadata, air-gap status, active directory)
- GET /api/v1/system/capabilities (Dynamic machine-readable capability discovery)
"""
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings, effective_air_gapped, database_is_local
from app.db.database import get_db
from app.schemas.all_schemas import SystemCapabilitiesResponse, SystemInfoResponse
from app.core.security import require_permission, TokenData
from app.core.rbac import Permission
from app.services.evidence_writer import CHECK_CATALOG
from app.policies.assurance_policy import AssurancePolicyEngine, OUT_OF_SCOPE

router = APIRouter(tags=["System & Observability"])

_START_TIME = time.time()

@router.get("/health")
def health_check():
    """Liveness probe confirming the sovereign service is responding."""
    return {
        "status": "HEALTHY",
        "system": settings.PROJECT_NAME,
        "subtitle": settings.PROJECT_SUBTITLE,
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
        "air_gapped_mode": effective_air_gapped(),
        "database_location": "local" if database_is_local() else "remote",
        "demo_mode": settings.DEMO_MODE,
    }

@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe verifying database connectivity and storage readiness."""
    try:
        # Check database connectivity
        db.execute(text("SELECT 1"))
        return {
            "status": "READY",
            "database": "CONNECTED",
            "air_gapped": effective_air_gapped(),
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Sovereign node not ready: {str(e)}"
        )

@router.get("/api/v1/system/info", response_model=SystemInfoResponse)
def get_system_info(user: TokenData = Depends(require_permission(Permission.SYSTEM_DIAGNOSTICS))):
    """Returns deployment metadata, storage path, and runtime uptime."""
    # Mask database URL secrets if postgres
    db_display = "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "postgresql"
    return SystemInfoResponse(
        project_name=settings.PROJECT_NAME,
        subtitle=settings.PROJECT_SUBTITLE,
        version=settings.PROJECT_VERSION,
        environment=settings.ENVIRONMENT,
        is_air_gapped=effective_air_gapped(),
        database_url=db_display,
        active_storage_dir=settings.BASE_STORAGE_DIR,
        uptime_seconds=round(time.time() - _START_TIME, 2)
    )

@router.get("/api/v1/system/capabilities", response_model=SystemCapabilitiesResponse)
def get_system_capabilities():
    """
    Exposes dynamic capability discovery so future frontends do not
    hard-code supported formats, detectors, or assurance states.
    """
    db_backend = "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "postgresql"
    return SystemCapabilitiesResponse(
        system=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        air_gapped=effective_air_gapped(),
        database_backend=db_backend,
        dataset_formats=["COCO", "YOLO", "CSV", "IMAGE_FOLDER"],
        model_formats=["ONNX", "PyTorch", "TorchScript"],
        detectors=list(CHECK_CATALOG.keys()),
        assurance_states=[
            "VERIFIED",
            "FINDING",
            "PARTIAL",
            "NOT_TESTED",
            "INCONCLUSIVE",
            "NOT_APPLICABLE"
        ],
        dispositions=[
            "ACCEPT",
            "REVIEW",
            "QUARANTINE"
        ],
        external_dependencies=[] if database_is_local() else ["remote PostgreSQL database (DATABASE_URL)"],
        policy_version=AssurancePolicyEngine.POLICY_VERSION,
        pipeline_version="1.0.0"
    )



@router.get("/api/v1/system/coverage-statement")
def coverage_statement():
    """
    Public, asset-free coverage statement: which attack classes DRISHTRA checks,
    what each check needs, and what is out of scope. Contains no case data.
    """
    return {
        "policy_version": AssurancePolicyEngine.POLICY_VERSION,
        "checks": [
            {"check_id": k, "layer": v[0], "label": v[1], "description": v[2]}
            for k, v in CHECK_CATALOG.items() if k != "D8C_WHITE_BOX_ANALYSIS"
        ],
        "out_of_scope": OUT_OF_SCOPE,
        "access_assumptions": {
            "WHITE_BOX": "Weights and activations available: all model checks applicable.",
            "BLACK_BOX": "Query access only: behavioural probes run; white-box trigger reconstruction is declared not applicable.",
            "STRUCTURAL_ONLY": "Graph/structure only: digest and structure checks; no behavioural probing.",
        },
        "states": {
            "VERIFIED": "Check ran on every applicable asset and passed.",
            "FINDING": "Check ran and produced at least one finding.",
            "PARTIAL": "Check ran on some, not all, applicable assets.",
            "NOT_TESTED": "Applicable, but no check ran. Never counted as a pass.",
            "INCONCLUSIVE": "Check ran but inputs were insufficient to decide.",
            "NOT_APPLICABLE": "Out of scope for this asset or access level (declared limitation).",
        },
    }


@router.get("/api/v1/system/diagnostics")
def diagnostics(
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.SYSTEM_DIAGNOSTICS)),
):
    """Operational self-check for administrators."""
    import os
    from app.db.models import User, PlatformEvent, Case, AuditEvent, CheckExecution
    from app.services.platform_audit_service import PlatformAuditService
    from app.crypto.crypto_service import KeyManagementInterface

    checks = {}
    try:
        db.execute(text("SELECT 1"))
        from app.db.database import engine
        actual = engine.dialect.name
        wanted = "sqlite" if settings.DATABASE_URL.strip().lower().startswith("sqlite") else "postgresql"
        checks["database"] = {
            "status": "OK" if actual == wanted else "FAIL",
            "backend": actual,
            "location": "local" if database_is_local() else "remote",
        }
        if actual != wanted:
            checks["database"]["error"] = f"DATABASE_URL asks for {wanted} but the node is running on {actual} (driver missing?)"
    except Exception as e:  # pragma: no cover
        checks["database"] = {"status": "FAIL", "error": str(e)}
    storage_ok = all(os.path.isdir(p) and os.access(p, os.W_OK) for p in [settings.ARTIFACTS_DIR, settings.UPLOADS_DIR, settings.AUDIT_DIR])
    checks["file_vault"] = {"status": "OK" if storage_ok else "FAIL", "root": "configured"}
    checks["signing_key"] = {"status": "OK", "fingerprint": KeyManagementInterface.public_key_fingerprint()[:16]}
    checks["detector_registry"] = {"status": "OK", "checks_registered": len(CHECK_CATALOG)}
    chain = PlatformAuditService.verify(db)
    checks["platform_ledger"] = {"status": "OK" if chain["status"] == "VALID" else "FAIL", "events": chain["verified_count"]}
    checks["network_posture"] = {
        "status": "OK" if effective_air_gapped() else "WARN",
        "air_gapped": effective_air_gapped(),
        "air_gap_requested": settings.IS_AIR_GAPPED,
        "remote_database": not database_is_local(),
        "external_explainer_enabled": bool(settings.ALLOW_EXTERNAL_EXPLAINER and settings.GROK_API_KEY and not settings.IS_AIR_GAPPED),
    }
    checks["demo_mode"] = {"status": "WARN" if settings.DEMO_MODE else "OK", "enabled": settings.DEMO_MODE}
    return {
        "checks": checks,
        "counts": {
            "users": db.query(User).count(),
            "cases": db.query(Case).count(),
            "case_audit_events": db.query(AuditEvent).count(),
            "platform_events": db.query(PlatformEvent).count(),
            "check_executions": db.query(CheckExecution).count(),
        },
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
    }
