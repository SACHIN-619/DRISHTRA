# DRISHTRA Deployment & Operations Guide
**Document Version:** 1.0.0  
**Target Profile:** Air-Gapped Sovereign Military Infrastructure  
**Operational Status:** `[IMPLEMENTED]`

---

## 1. Zero-Cloud Sovereign Principle
DRISHTRA is engineered to boot and operate 100% offline within an air-gapped security enclave without access to external clouds, telemetry, public package indices, or remote AI APIs.

### Infrastructure Dependencies:
- **Core Runtime:** Python 3.11+
- **Sovereign Database:** Local SQLite (`sqlite:///./drishtra_vault.db`) by default.
- **Enterprise Database:** `[IMPLEMENTED]` PostgreSQL / Neon adapter supported via standard SQLAlchemy connection strings.
- **In-Memory Storage:** Sovereign local filesystem storage vault (`./storage`).

---

## 2. Environment Variables Configuration

Place configuration in `.env` (guarded by `.gitignore`; never commit real secrets):

```ini
# Application Mode
APP_ENV=air-gapped-development
HOST=0.0.0.0
PORT=8000
IS_AIR_GAPPED=true

# Database Connection (Default Sovereign Vault)
DATABASE_URL=sqlite:///./drishtra_vault.db
# Optional Enterprise PostgreSQL:
# DATABASE_URL=postgresql://drishtra:sovereign_pass@localhost:5432/drishtra_vault

# Authentication & Cryptographic Keys
SECRET_KEY=drishtra-dev-sovereign-vault-secret-key-32bytes
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Storage & Quota Limits
BASE_STORAGE_DIR=./storage
MAX_UPLOAD_SIZE_MB=2048
MAX_ARCHIVE_SIZE_MB=4096
MAX_IMAGE_SIZE_MB=25
INGESTION_CHUNK_SIZE=1000

# Logging & External Adapters
LOG_LEVEL=INFO
ENABLE_EXTERNAL_LLM=false
GROK_API_KEY=
GROK_API_BASE=
GROK_MODEL=

# CORS Configuration
CORS_ORIGINS=http://localhost:27027,http://127.0.0.1:27027
```

---

## 3. Storage Directory Lifecycle & Layout

The sovereign vault enforces an isolated directory hierarchy under `BASE_STORAGE_DIR`:
```
storage/
├── datasets/        # Immutable normalized dataset archives and manifests
├── models/          # Registered ONNX and PyTorch model weight checkpoints
├── inferences/      # Raw and canonical edge inference attestations
├── artifacts/       # 9 canonical exported JSON artifacts per case
└── temp/            # Ephemeral decompression scratchpads (auto-cleaned)
```

### Retention & Cleanup Policy:
- `temp/`: Scratched immediately following archive inspection and hash registration.
- `datasets/`, `models/`, `artifacts/`: Immutable, content-addressed, append-only retention.

---

## 4. Local Execution Options

### Option A: Direct Python Execution
```bash
# 1. Initialize environment & install requirements
pip install -r requirements.txt

# 2. Run non-destructive database migrations
python -m app.db.migrations

# 3. Bootstrap synthetic demonstration case (idempotent)
python scripts/bootstrap_demo.py

# 4. Launch FastAPI sovereign backend
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option B: Docker Air-Gapped Container
```bash
# Build sovereign image
docker build -t drishtra-backend:latest .

# Run container with mounted local volume
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/storage:/app/storage \
  -v $(pwd)/drishtra_vault.db:/app/drishtra_vault.db \
  --name drishtra-sovereign \
  drishtra-backend:latest
```

---

## 5. Non-Destructive Database Migrations
DRISHTRA implements schema synchronization via `backend/app/db/migrations.py`. Unlike destructive tools that drop or recreate tables, DRISHTRA:
1. Inspects existing tables using SQLAlchemy `inspect`.
2. Adds missing columns using portable `ALTER TABLE ADD COLUMN` statements with proper defaults (`BOOLEAN DEFAULT FALSE`).
3. Preserves historical audit chains and prevents data loss.
