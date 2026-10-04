# DRISHTRA backend

FastAPI service with the assurance engine: ingestion, the 18-stage pipeline, detectors, the assurance policy, governance and ledgers. It also serves the prebuilt console from `../web/dist`, so one process is the whole product.

## Run

```bash
pip install -r ../requirements.txt
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- **http://127.0.0.1:8000:** the console (the home page is public; everything else needs sign-in).
- **http://127.0.0.1:8000/docs:** OpenAPI docs.
- `/health` is public.

On first start the schema is created and migrated, the node keys are generated under `storage/keys/` (never commit them), and the administrator is bootstrapped. With `DEMO_MODE=true` (the default) the five demo accounts and four synthetic cases are seeded too:

| Account | Role |
|---|---|
| `ml.analyst` | ML Analyst |
| `sec.analyst` | Security Analyst |
| `reviewer` | Reviewer / Supervisor |
| `auditor` | Auditor |
| `admin` | Administrator |

All demo accounts use the password `Drishtra@2026`.

`python ../scripts/bootstrap_demo.py [--reset]` does the same seeding without starting the server.

## Configuration

Settings are read from the environment or `backend/.env`. Copy `.env.example` to start. **`.env` is git-ignored; never commit it.**

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./drishtra_vault.db` | SQLite (air-gapped) or PostgreSQL. Neon needs `?sslmode=require` and `psycopg2-binary`. |
| `DEMO_MODE` | `true` | Seeds demo accounts and cases and enables the Attack Lab. Set `false` for real use. |
| `BOOTSTRAP_ADMIN_USERNAME` / `BOOTSTRAP_ADMIN_PASSWORD` | `admin` / empty | First administrator. If the password is empty, a random one is written once to `storage/keys/initial_admin_password.txt`. |
| `SECRET_KEY` | empty | JWT signing secret. If empty, a per-install secret is generated in `storage/keys/jwt_secret`. Known published defaults are refused outside demo mode. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Session length (one shift). |
| `PASSWORD_MIN_LENGTH`, `MAX_FAILED_LOGINS`, `LOCKOUT_MINUTES` | `10`, `5`, `15` | Password and lockout policy. |
| `IS_AIR_GAPPED` | `true` | Operator intent. The node reports itself air-gapped only if this is true **and** the database is local. |
| `ALLOW_EXTERNAL_EXPLAINER`, `GROK_API_KEY` | `false`, empty | Optional external text explainer. It is only used when explicitly allowed and not air-gapped. Nothing depends on it. |
| `BASE_STORAGE_DIR` | `./storage` | Vault root: artifacts, uploads, assessment inputs, ledgers and keys. |
| `MAX_UPLOAD_SIZE_MB` and related limits | see `app/core/config.py` | Trust-boundary limits. |
| `DRISHTRA_ALLOW_SQLITE_FALLBACK` | `false` | Startup fails loudly if a PostgreSQL URL cannot be used. This opts into falling back to the local vault instead. |

Check the database you are pointed at (the password is never printed):

```bash
python ../scripts/check_database.py --init
```

## Layout

```
app/
  main.py               app factory: security headers + CSP, routers, bootstrap, SPA serving (../web/dist)
  core/                 config, passwords (PBKDF2-SHA256), RBAC (roles → permissions), auth (JWT + token revocation)
  db/                   SQLAlchemy models, engine (SQLite/PostgreSQL), additive migrations
  api/routes/           REST endpoints, every one gated by a permission (no admin bypass)
  services/
    pipeline_service.py      18-stage chained pipeline (+ live event stream)
    assurance_service.py     assurance case, recommendation/decision, signed decision chain
    evidence_writer.py       check catalogue D1–D9; every check run is a CheckExecution
    artifact_store.py        stored assessment inputs (what the pipeline actually scans)
    ingestion_service.py     COCO / YOLO / archives through the FileVault trust boundary
    attack_lab_service.py    demo-only sandbox: inject attacks into stored inputs
    platform_audit_service.py, user_service.py, passport_service.py, demo_service.py, …
  policies/assurance_policy.py   DRISHTRA-AP-2026.2 rules (QUARANTINE / REVIEW / INCONCLUSIVE / VERIFIED)
  detectors/            dataset, model and inference detectors behind one evidence contract
  correlation/          cross-lifecycle evidence graph, convergence by contributor lineage
  crypto/               canonical JSON, SHA-256 chains, Ed25519 signing/verification
  ingestion/            file vault, dataset parsers, model inspectors
tests/                  pytest suite (isolated temporary database per run)
```

## API at a glance

All routes are under `/api/v1` and need a Bearer token from `POST /api/v1/auth/token`.

| Area | Endpoints |
|---|---|
| Identity | `auth/token`, `auth/me`, `auth/change-password`, `auth/logout`, `users` (admin), `platform/events` |
| Cases & assets | `cases`, `contributors`, `datasets` (incl. `upload`), `models`, `runtimes`, `inferences` |
| Pipeline | `cases/{id}/pipeline/run`, `cases/{id}/pipeline/stream` (NDJSON, live), `cases/{id}/pipeline/runs` |
| Assurance | `assurance/queue`, `assurance/{case}`, `…/assess`, `…/recommend`, `…/decide`, `…/decisions/verify` |
| Evidence | `findings`, `evidence`, `graph`, `passports/{asset}`, `reports` |
| Audit | `audit/{case}`, `audit/{case}/verify`, `platform/events/verify` |
| Demo | `attack-lab`, `attack-lab/{scenario}/inject`, `attack-lab/reset` (only when `DEMO_MODE=true`) |
| System | `/health`, `system/coverage-statement` (public), `system/diagnostics` (admin) |

## Roles and separation of duties

| Role | Can | Cannot |
|---|---|---|
| ML Analyst | ingest, register, run the pipeline, use the Attack Lab | recommend or decide |
| Security Analyst | everything above, plus investigate, verify, and **recommend** | decide |
| Reviewer / Supervisor | **decide** (signed, append-only) | decide on a case they initiated |
| Auditor | read and **verify** every chain | change anything |
| Administrator | manage users, read health and platform ledger | touch assurance evidence or decisions, rewrite history |

## Tests

```bash
cd backend
python -m pytest -q          # 83 tests, fresh temporary SQLite database, never your .env database
python ../scripts/golden_demo.py   # 19-step end-to-end story through the real API
```

The suite covers:
- RBAC and separation of duties
- token expiry, forgery and revocation
- upload trust boundary
- every pipeline stage and chaining
- honest failure on a crashed stage
- mutation propagation
- every Attack Lab scenario
- ledger tamper detection
- PostgreSQL column limits
- air-gap honesty
