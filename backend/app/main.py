"""
DRISHTRA - Digital Reliability & Integrity Shield for Trusted AI
India-First Offline AI Assurance Fabric for Multi-Contributor Computer Vision

SMART INDIA HACKATHON 2026 | Problem Statement: SIH26228
Ministry of Defence | Indian Army (DGIS)
Theme: Blockchain & Cybersecurity
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import engine, Base
from app.api.routes import (
    health, cases, datasets, models, inference, evidence, assurance, audit, reports, evaluation
)

# Initialize database schema
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"[!] Database schema initialization warning: {e}")

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
3. **Cross-Lifecycle Evidence Graph:** Epistemically typed lineage connecting Contributor -> Dataset -> Model -> Inference.
4. **Coverage-Aware Policy:** Declares what could and could not be verified (VERIFIED, FINDING, NOT_AVAILABLE, INCONCLUSIVE).
5. **Tamper-Evident Hash Chain:** Sequential Ed25519-signed sovereign forensic audit ledger.
6. **Air-Gapped Operation:** Zero external cloud dependencies.
    """,
    version=settings.PROJECT_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS for tactical dashboards and external UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Subsystem Routes
app.include_router(health.router)
app.include_router(cases.router)
app.include_router(datasets.router)
app.include_router(models.router)
app.include_router(inference.router)
app.include_router(evidence.router)
app.include_router(assurance.router)
app.include_router(audit.router)
app.include_router(reports.router)
app.include_router(evaluation.router, prefix="/api/v1")

import os
from fastapi.staticfiles import StaticFiles
from app.db.database import SessionLocal
from app.services.demo_service import DemoService

# Mount static frontend directory at root after all API routes
candidate_frontend_dirs = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend")),
    os.path.abspath(os.path.join(os.getcwd(), "frontend")),
    "/app/frontend"
]
for candidate in candidate_frontend_dirs:
    if os.path.exists(candidate) and os.path.isdir(candidate):
        app.mount("/", StaticFiles(directory=candidate, html=True), name="frontend")
        break

@app.on_event("startup")
def startup_event():
    print(f"[*] {settings.PROJECT_NAME} v{settings.PROJECT_VERSION} initialized successfully.")
    print(f"[*] Operational Mode: {settings.ENVIRONMENT} (Air-Gapped: {settings.IS_AIR_GAPPED})")
    print(f"[*] Documentation loaded: /docs and /redoc")
    print(f"[*] Command Center UI mounted at: / and /ui")
    
    # Auto-bootstrap deterministic demo case on startup
    db = SessionLocal()
    try:
        DemoService.bootstrap_demo_case(db)
        print("[*] CASE-2026-DRISHTRA-DEMO auto-bootstrapped successfully.")
    except Exception as e:
        print(f"[!] Startup bootstrap error: {e}")
    finally:
        db.close()
