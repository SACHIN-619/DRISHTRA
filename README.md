# DRISHTRA — Digital Reliability & Integrity Shield for Trusted AI

**SIH26228 · Trustworthy computer-vision integrity assurance for data, models and inference outputs in multi-contributor pipelines.**

DRISHTRA is not another detector, provenance tool or dashboard. Hashes prove bytes, signatures prove origin, anomaly detectors flag oddities. DRISHTRA answers the question above them:

> **Can this AI result be trusted, and what evidence supports that decision?**

It connects evidence across the whole lifecycle (contributor → dataset → model → runtime → inference) and turns it into an **assurance case**. Each assurance case contains:

- the findings that support the concern
- counter-evidence from checks that actually ran and passed
- what was *not* tested
- the declared limitations
- a machine recommendation
- a **signed human decision** that nobody can rewrite

## Three ideas

| | Idea | What it means in the product |
|---|---|---|
| 01 | **Cross-lifecycle assurance** | A tampered inference is traced back through its runtime, model and training data to the contributor. Findings on several layers that converge on one contributor are recognised as convergence. |
| 02 | **Evidence-centric trust** | There is no opaque score. Coverage is computed from check executions: `NOT_TESTED` is never a pass, and counter-evidence comes only from checks that passed. |
| 03 | **Human-governed decisions** | The machine recommends. A Security Analyst *recommends*; only a Reviewer/Supervisor *decides*. Decisions are append-only, hash-linked and Ed25519-signed. |

## Repository layout

| Folder | What it is | Read more |
|---|---|---|
| [`backend/`](backend/) | FastAPI assurance engine: ingestion, 18-stage pipeline, detectors, policy, governance, ledgers. Also serves the console. | [backend/README.md](backend/README.md) |
| [`web/`](web/) | **The frontend.** React + TypeScript console (dark home page; light login and role consoles; Pipeline Studio + Attack Lab), prebuilt into `web/dist`. | [web/README.md](web/README.md) |
| [`scripts/`](scripts/) | `bootstrap_demo.py`, `golden_demo.py` (19-step proof), `check_database.py`, `e2e_ui.mjs` (browser test) | — |
| [`docs/`](docs/) | Security notes, gap analysis, demo script, 3-minute judge video guide, and design documents | [docs/DEMO_VIDEO_GUIDE.md](docs/DEMO_VIDEO_GUIDE.md) |
| `storage/` | Runtime vault (artifacts, uploads, ledgers, `keys/`). Created at runtime; only the `.gitkeep` placeholders are committed. | — |

## Run it (one process, offline)

```bash
pip install -r requirements.txt
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. The FastAPI backend serves the prebuilt console from `web/dist`, so Node.js, CDNs and web fonts are not needed. The API docs are at `/docs`.

`DEMO_MODE=true` is the default. It seeds four synthetic cases and one account per role, all with the password `Drishtra@2026`:

| Username | Role | Console |
|---|---|---|
| `ml.analyst` | ML Analyst | ML Operations: ingest assets, run assurance |
| `sec.analyst` | Security Analyst | Security Operations: investigate, correlate, recommend |
| `reviewer` | Reviewer / Supervisor | Assurance Review Center: binding decisions |
| `auditor` | Auditor | Audit Assurance Center: verify every chain |
| `admin` | Administrator | System Administration: users, health, ledger. **No assurance authority.** |

Tip: sign in to each role in its own browser tab. Sessions are per tab.

For a real deployment, set `DEMO_MODE=false` and `BOOTSTRAP_ADMIN_PASSWORD`. If you do not set the password, a random one is written once to `storage/keys/initial_admin_password.txt`. See `.env.example`.

## Prove it works

```bash
python -m pytest                    # 83 tests on a fresh, isolated database
python scripts/golden_demo.py       # 19-step end-to-end story + storage/artifacts/golden_demo_proof.json
```

The golden demo runs through the real API with the five accounts:

1. The pipeline runs.
2. "Why?" traces the finding back to the contributor.
3. The analyst recommends.
4. The admin, the ML analyst and the security analyst are each refused the decision.
5. The reviewer signs the decision.
6. The auditor verifies every chain.
7. **Mutation propagation:** tampering one delivered model digest flips the clean case's verdict, and restoring it flips it back.
8. **Tamper detection:** editing a stored decision breaks verification.

Browser end-to-end check (needs `npm i -D playwright && npx playwright install chromium` once, and a fresh demo node on port 8000):

```bash
node scripts/e2e_ui.mjs http://localhost:8000 --shots e2e_shots
```

Recording the 3-minute judge video: see [docs/DEMO_VIDEO_GUIDE.md](docs/DEMO_VIDEO_GUIDE.md).

## PostgreSQL / Neon (optional)

SQLite is the default and is what makes the node air-gapped. To use PostgreSQL (for example Neon), set it in `backend/.env`. **Never commit that file.**

```ini
DATABASE_URL=postgresql://USER:PASSWORD@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require
```

```bash
pip install psycopg2-binary
python scripts/check_database.py --init     # connects, creates tables, verifies the ledger; never prints the password
```

- The schema and migrations have been validated against PostgreSQL 16.
- If the driver is missing, startup now **fails loudly**. It no longer falls back to SQLite silently. Set `DRISHTRA_ALLOW_SQLITE_FALLBACK=true` only if you want that fallback.
- A remote database means the node is **not** air-gapped, whatever `IS_AIR_GAPPED` says. `/health`, the admin diagnostics and the console badge ("Remote database · not air-gapped") report this honestly.
- With `DEMO_MODE=true` the demo accounts and cases are seeded into that database. For a shared Neon database, set `DEMO_MODE=false` and `BOOTSTRAP_ADMIN_PASSWORD`.
- Tests always use a temporary SQLite database, whatever `.env` says.

**Grok / external explainer.** `GROK_API_KEY` is ignored unless `ALLOW_EXTERNAL_EXPLAINER=true` **and** `IS_AIR_GAPPED=false`. When enabled, finding summaries leave the host. Keep it off for anything sensitive. No core check, verdict or decision depends on it.

## Pipeline Studio and Attack Lab

ML and Security Analysts get **Pipeline Studio** (`#/studio`). It streams the real 18-stage run from the server as each stage executes (`POST /api/v1/cases/{id}/pipeline/stream`, newline-delimited JSON). Every stage shows its compute time, output digest and every check it executed. *Presentation pace* only adds pauses between stages; the reported times are real.

On the **Attack Lab sandbox** (`CASE-2026-ATTACK-LAB`, demo mode only) you can inject attacks into the stored inputs, one at a time or layered:

| Attack | Edits | Caught by |
|---|---|---|
| Poison the training data | vault records of D-41 | Stage 05 · D1/D2/D3 |
| Swap the model weights | delivered digest of M-41 | Stage 07 · D8A |
| Plant a trigger backdoor | probe responses of M-41 | Stage 08 · D8B |
| Alter an output after signing | stored output of I-412 | Stage 11 · D9A |
| Replay an old signed record | adds I-413 with a reused nonce | Stage 11 · D9B |

The pipeline is not told what changed. Each injection and reset is written to the case's hash-chained audit ledger, and **Reset** restores the clean, signed baseline (ACCEPT).

## Demo cases (synthetic, labelled DEMO)

| Case | What it shows | Machine recommendation |
|---|---|---|
| `CASE-2026-DRISHTRA-DEMO` | Subcontractor C-07 supplies a dataset with poisoning, duplicates and out-of-distribution samples. Its model's digest matches but it behaves like a backdoor. One inference has a tampered output and another is a replay. | **QUARANTINE**: 3 evidence paths converge on C-07 |
| `CASE-2026-BASELINE-001` | A clean release where every applicable check runs and passes. | **ACCEPT** (verified, 100% coverage, limitations listed) |
| `CASE-2026-NIGHT-OPS-002` | A night capture whose statistics shift. The shift is explained by the declared illumination, with no corroborating integrity finding. | **ACCEPT**; drift is assessed as *probable operational drift*, not manipulation |
| `CASE-2026-ATTACK-LAB` | Clean sandbox for the Attack Lab. Inject attacks from Pipeline Studio and watch which stage catches them. | **ACCEPT** when clean; **REVIEW** or **QUARANTINE** once attacked |

## Architecture

```
 untrusted files ──► TRUST BOUNDARY (FileVault: type/size/traversal checks, SHA-256)
                          │
                          ▼
                 canonical records + delivered digests + probe responses + signer keys
                 (storage/assessment_inputs — what the pipeline actually scans)
                          │
 18-stage pipeline ──► D1–D7 dataset · D8 model digest/behaviour · D9 signature/replay/model binding
                          │      every check → CheckExecution (PASS / FINDING / NOT_TESTED / …)
                          ▼
                 evidence graph · convergence · counter-evidence · coverage · limitations
                          │
                          ▼
                 ASSURANCE CASE (policy DRISHTRA-AP-2026.2) ──► recommendation
                          │
                          ▼
                 Security Analyst RECOMMENDS ─► Reviewer DECIDES (signed, append-only)
                          │
                          ▼
     case audit ledger · decision chain · platform ledger  (SHA-256 hash chains, verifiable)
```

- **Backend:** `backend/app` (FastAPI, SQLAlchemy, SQLite by default)
  - `core/`: config, RBAC, authentication
  - `services/`: pipeline, assurance, ingestion, passports, users, ledgers
  - `policies/assurance_policy.py`: the reasoning rules
  - `detectors/`: pluggable detectors behind one evidence contract
- **Console:** `web/` (React + TypeScript, built with esbuild into `web/dist`). Five role consoles plus the shared screens: Assurance Case, Why?, Passport, Evidence Graph, Coverage, Decision, and Audit.

## What changed in v2.0 (October 2026)

See `docs/GAP_ANALYSIS.md` for the full audit. The headlines:

1. **Security**
   - Real users table, PBKDF2 hashing and lockout. Admin-created accounts with a forced first-login password change. No self-registration.
   - The role comes from the database, never from the request. The anonymous fallback and the administrator bypass are removed.
   - Separation of duties is enforced on the server.
   - A platform ledger records identity and authorization events.
2. **Assurance correctness**
   - Fixed a bug that made every finding read as type `"FINDING"`. That bug produced counter-evidence contradicting real findings (for example "signature valid" next to a CRITICAL invalid signature).
   - Coverage now comes from executed checks. The incriminating evidence is saved with the case.
3. **Honest pipeline**
   - Stages scan stored artifacts, report `SKIPPED` rather than fake success, and record input/output digests.
   - Uploads of real COCO/YOLO data now work, with pixel hashing when images are included.
4. **Console**
   - The previous UI was entirely hardcoded. The new one is wired to the live API and organised by role.
   - Unbacked claims are removed: the defence command-node map, HSM/TPM badges and named real organisations.

## Deploy

```bash
docker compose up --build          # one container on :8000, vault persisted in a named volume
```

- **Docker:** the root `Dockerfile` installs the backend and ships the prebuilt console (`web/dist`). Set `SECRET_KEY` in the environment, or leave it empty and the container generates a per-install secret in the vault.
- **Render (backend + console):** `render.yaml` runs the same app natively (`PYTHONPATH=backend uvicorn app.main:app`) in Singapore, with Python 3.11 and a generated `SECRET_KEY`. The free tier sleeps after 15 idle minutes and takes about a minute to wake, and its disk resets on restart (demo mode simply reseeds).
- **Vercel (public URL for the console):** import the repo in Vercel with **Root Directory = `web`**. `web/vercel.json` builds the console and proxies `/api/*` and `/health` to the Render backend, so the browser stays same-origin. Replace `YOUR-RENDER-SERVICE` in `web/vercel.json` with your Render hostname first. The backend cannot run on Vercel functions, because it needs a persistent disk for keys, ledgers and stored assessment inputs.
- For anything beyond a demo, set `DEMO_MODE=false` and `BOOTSTRAP_ADMIN_PASSWORD`, and keep `storage/` on persistent disk. It holds the keys and ledgers.

## Scope and limitations (declared, also shown in the product)

**In scope:** COCO/YOLO datasets; ONNX/PyTorch/TorchScript models (structural inspection depends on the access level); black-box behavioural probes; signed inference attestations.

**Out of scope for this prototype:**
- white-box trigger reconstruction
- SAR/thermal modalities
- physical adversarial patches
- multi-modal fusion
- adaptive attackers
- host firmware compromise

**Roadmap, not implemented:**
- enterprise identity (LDAP/AD, smart-card, MFA)
- HSM-backed keys
- a removable-media import station
- a multi-organisation distributed ledger
- evaluation on public CV datasets and TrojAI benchmarks

The attack lab is a synthetic controlled benchmark. It is not evidence of real-world detection rates.

## Repository notes

- `web/` is the frontend that runs. The earlier prototype UIs (the vanilla `frontend/` app and an unused Next.js experiment) are not part of the product.
- `scripts/golden_demo.py`, `scripts/bootstrap_demo.py`, `scripts/check_database.py` and `scripts/e2e_ui.mjs` are current. `scripts/run_assurance_demo.py` and `scripts/test_backend.py` target the v1 API and are kept for reference only.
- Never commit `.env`, `backend/.env`, `*.db` or `storage/keys/`. They hold your database URL, API keys, the per-install JWT secret and the node signing seed. All of them are in `.gitignore`.
