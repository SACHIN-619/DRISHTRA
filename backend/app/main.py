"""
DRISHTRA - Digital Reliability & Integrity Shield for Trusted AI
India-First Offline AI Assurance Fabric for Multi-Contributor Computer Vision

SMART INDIA HACKATHON 2026 | Problem Statement: SIH26228
Ministry of Defence | Indian Army (DGIS)
Theme: Blockchain & Cybersecurity
"""
import time
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings, effective_air_gapped
from app.db.database import engine, SessionLocal
from app.db.migrations import run_migrations
from app.services.demo_service import DemoService

from app.api.routes import (
    system, auth, cases, contributors, datasets, models, runtimes,
    inference, evidence, graph, assurance, assurance_runs, audit, reports, benchmarks, evaluation,
    findings, passports, users, attack_lab
)
from app.services.user_service import UserService

logger = logging.getLogger("drishtra")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence: Non-destructive migration & demo initialization
    logger.info(f"[*] {settings.PROJECT_NAME} v{settings.PROJECT_VERSION} initializing...")
    logger.info(f"[*] Operational Mode: {settings.ENVIRONMENT} (Air-Gapped: {effective_air_gapped()})")
    
    # 1. Non-destructive database migrations
    try:
        run_migrations(engine)
    except Exception as e:
        logger.warning(f"[!] Migration check warning: {e}")

    # 2. Identity bootstrap (first administrator; demo accounts only in DEMO_MODE)
    db = SessionLocal()
    try:
        UserService.bootstrap(db)
        if settings.DEMO_MODE:
            DemoService.bootstrap_demo_case(db)
            logger.info("[*] Demo cases verified/bootstrapped (DEMO_MODE=true).")
    except Exception as e:
        logger.warning(f"[!] Startup bootstrap notice: {e}", exc_info=True)
    finally:
        db.close()

    yield

    logger.info(f"[*] {settings.PROJECT_NAME} shutting down sovereign engine.")

app = FastAPI(
    title=f"{settings.PROJECT_NAME} Sovereign Assurance API",
    description="""
## Digital Reliability & Integrity Shield for Trusted AI (DRISHTRA)
**India-First Offline AI Assurance Fabric for Multi-Contributor Computer Vision**

### Strategic Context
- **Hackathon:** Smart India Hackathon (SIH) 2026
- **Problem Statement ID:** 26228
- **Organization:** Ministry of Defence (MoD) / Indian Army (DGIS)
- **Theme:** Blockchain & Cybersecurity

### Core Architecture & Innovations
1. **Evidence-Carrying AI:** Outputs bind prediction, cryptographic provenance, integrity findings, and operational context.
2. **Assurance Passport:** Structured identity profile for protected datasets, models, and inference assets.
3. **Cross-Lifecycle Evidence Graph:** Epistemically typed lineage connecting Contributor -> Dataset -> Model -> Runtime -> Inference.
4. **Coverage-Aware Policy (AP-2026.1):** Declares what was tested, what was not tested, counter-evidence, and operational disposition.
5. **Tamper-Evident Hash Chains:** SHA-256 chained case and platform ledgers; human decisions are additionally Ed25519-signed.
6. **Air-Gapped Operation:** 100% offline local vault execution.
    """,
    version=settings.PROJECT_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Request ID and Timing Middleware
@app.middleware("http")
async def add_request_id_and_timing(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:8]}"
    request.state.request_id = req_id
    t0 = time.time()
    
    response = await call_next(request)
    duration_ms = round((time.time() - t0) * 1000, 2)
    response.headers["X-Request-ID"] = req_id
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if not request.url.path.startswith(("/docs", "/redoc")):
        # Offline UI: everything is served from this origin; no third-party hosts.
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; frame-ancestors 'none'",
        )
    response.headers["X-Response-Time-MS"] = str(duration_ms)
    return response

# Standardized Error Handlers (Requirement 25)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:8]}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request payload validation failed.",
                "request_id": req_id,
                "details": exc.errors()
            }
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    req_id = getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:8]}")
    code = "HTTP_ERROR"
    if exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 400:
        code = "BAD_REQUEST"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": str(exc.detail),
                "request_id": req_id
            }
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:8]}")
    logger.error(f"[!] Unhandled exception [{req_id}]: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred in the sovereign engine.",
                "request_id": req_id
            }
        }
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Subsystem Routes
app.include_router(system.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(cases.router)
app.include_router(contributors.router)
app.include_router(datasets.router)
app.include_router(models.router)
app.include_router(runtimes.router)
app.include_router(inference.router)
app.include_router(evidence.router)
app.include_router(findings.router)
app.include_router(passports.router)
app.include_router(graph.router)
app.include_router(assurance.router)
app.include_router(assurance_runs.router)
app.include_router(audit.router)
app.include_router(reports.router)
app.include_router(benchmarks.router)
app.include_router(attack_lab.router)
app.include_router(evaluation.router, prefix="/api/v1") # Backward compatibility alias

# ---------------------------------------------------------------------------
# Offline web console: the built frontend (frontend/dist) is served by this
# same process, so a single air-gapped host needs no Node.js or CDN.
# ---------------------------------------------------------------------------
import os as _os
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_FRONTEND_DIST = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "web", "dist"))

if _os.path.isdir(_os.path.join(_FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=_os.path.join(_FRONTEND_DIST, "assets")), name="assets")


@app.get("/api/v1", include_in_schema=False)
def api_root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "OPERATIONAL",
        "air_gapped": effective_air_gapped(),
        "api_docs": "/docs",
    }


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    """Serve the single-page console for any non-API path."""
    if full_path.startswith(("api/", "docs", "redoc", "openapi.json")):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    index = _os.path.join(_FRONTEND_DIST, "index.html")
    candidate = _os.path.realpath(_os.path.join(_FRONTEND_DIST, full_path))
    if full_path and candidate.startswith(_FRONTEND_DIST) and _os.path.isfile(candidate):
        return FileResponse(candidate)
    if _os.path.isfile(index):
        return FileResponse(index)
    return JSONResponse({"project": settings.PROJECT_NAME, "status": "OPERATIONAL",
                         "note": "Frontend not built. See README: web/ -> npm run build."})
