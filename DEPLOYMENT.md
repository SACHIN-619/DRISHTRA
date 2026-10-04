# DRISHTRA Deployment & Operations Guide
**Document Version:** 1.0.0  
**Target Profile:** Air-Gapped Sovereign Military Infrastructure  
**Operational Status:** `[IMPLEMENTED]`

*Note: For the full specification, see [docs/DEPLOYMENT.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/DEPLOYMENT.md).*

### Quick Deployment Reference:
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run non-destructive database migrations (SQLite or PostgreSQL)
python -m app.db.migrations

# 3. Bootstrap synthetic demo case (idempotent)
python scripts/bootstrap_demo.py

# 4. Launch FastAPI sovereign backend
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Sovereign Air-Gap Invariant:
`IS_AIR_GAPPED=true`. Operates 100% locally on SQLite sovereign vault (`drishtra_vault.db`) without internet, cloud databases, external LLMs, or telemetry.

See [docs/DEPLOYMENT.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/DEPLOYMENT.md).
