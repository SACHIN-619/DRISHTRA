# DRISHTRA
## Digital Reliability & Integrity Shield for Trusted AI
### India-First Offline AI Assurance Fabric for Multi-Contributor Computer Vision

[![SIH 2026](https://img.shields.io/badge/SIH-2026-blue?style=for-the-badge)](https://sih.gov.in)
[![Ministry of Defence](https://img.shields.io/badge/Ministry%20of%20Defence-Indian%20Army%20(DGIS)-darkgreen?style=for-the-badge)](https://mod.gov.in)
[![Security Architecture](https://img.shields.io/badge/Security-Zero--Trust%20AI%20Supply%20Chain-red?style=for-the-badge)]()
[![Air-Gapped Operation](https://img.shields.io/badge/Air--Gapped-Verified%20Local%20Vault-emerald?style=for-the-badge)]()

---

## 1. Mission Overview
**DRISHTRA** is an indigenous, sovereign AI assurance fabric engineered for the **Indian Army (Directorate General of Information Systems - DGIS)** under Smart India Hackathon 2026 Problem Statement **SIH26228**.

Modern operational defence computer vision pipelines ingest datasets, pre-trained models, and inference outputs supplied by heterogeneous contributors (defence labs, commercial optronics vendors, academic consortia, and external subcontractors). Conventional cyber tools only protect perimeter storage or scan isolated model files.

**DRISHTRA shifts the paradigm from disconnected scanners to an integrated Zero-Trust AI Supply Chain Assurance Fabric.**

```
Contributor ──► Dataset ──► Model ──► Inference ──► Operational Context
     │             │          │           │                 │
     ▼             ▼          ▼           ▼                 ▼
             Cross-Lifecycle Evidence Correlation Graph
                                  │
                                  ▼
                        Assurance Case Engine
                                  │
                                  ▼
                   Tamper-Evident Forensic Ledger
                                  │
                                  ▼
                     Sovereign Human Reviewer
                  (ACCEPT / REVIEW / QUARANTINE)
```

---

## 2. Core Technological Contributions

1. **Evidence-Carrying AI:** An inference output does not emit merely an opaque confidence score ($\text{Tank } = 0.94$). Every inference carries an attested cryptographic manifest binding:
   $$\{\text{Input Digest, Model Digest, Preprocess Config, Output Signature, Lineage Ancestors, Coverage, Assurance State}\}$$
2. **Assurance Passport:** Structured security profile issued to every protected dataset, model, and inference asset declaring byte fingerprints, lineage, coverage boundaries, and verified claims.
3. **Cross-Lifecycle Evidence Graph:** Epistemically typed graph (`OBSERVED`, `DERIVED`, `SUPPORTS`, `CORRELATES`) connecting findings directly to their origin assets.
4. **The "Why Was This Result Flagged?" Upstream Trace:** Dynamic reverse-lineage traversal tracing:
   $$\text{Inference } I\text{-}883 \xrightarrow{\text{produced}} \text{Model } M\text{-}04 \xrightarrow{\text{trained\_from}} \text{Dataset } D\text{-}14 \xrightarrow{\text{contributed\_by}} \text{Contributor } C\text{-}07$$
   Attaching signature tampering, Trojan probe deviation, near-duplicate flooding, and subcontractor risk along every link.
5. **Coverage-Aware Assurance Policy (AP-2026.1):** Replaces deceptive "trust scores" with an auditable **Assurance Case** declaring explicit supporting evidence, counter-evidence, and what the system could *not* verify.
6. **Air-Gapped Sovereign Readiness:** 100% operational offline without external cloud dependencies, with standard adapters for DRDO / DGIS AI-as-a-Service integration.

---

## 3. Directory Structure

```
DRISHTRA/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI entrypoint + static UI mount
│   │   ├── core/                       # Settings, RBAC & Security headers
│   │   ├── db/                         # SQLAlchemy models & SQLite vault
│   │   ├── schemas/                    # Pydantic validation contracts
│   │   ├── crypto/                     # Ed25519 signing, SHA-256, hash chain
│   │   ├── detectors/                  # Exact/near duplicate, label, OOD, probe battery
│   │   ├── correlation/                # Evidence graph & lineage reconstruction
│   │   ├── policies/                   # Assurance policy AP-2026.1 rules
│   │   ├── services/                   # Business logic, audit, passport, demo
│   │   └── api/routes/                 # REST endpoints (/cases, /datasets, /models, etc.)
│   ├── fixtures/
│   │   └── attack_factory.py           # Controlled synthetic mutation laboratory
│   └── tests/                          # Pytest test suite (crypto, detectors, API)
├── frontend/
│   ├── index.html                      # Tactical Command Center Mission Control
│   ├── style.css                       # Defence-grade dark cyber styling
│   └── app.js                          # Dynamic UI controller & API connectors
├── docs/
│   ├── architecture.md                 # Full system architecture
│   ├── threat-model.md                 # 11-vector threat analysis
│   ├── assurance-model.md              # Policy & disposition state machine
│   ├── data-strategy.md                # Real Indian public data & synthetic mutations
│   ├── government-integration.md       # iDEX AIaaS adapter layer
│   └── coverage.md                     # Declared boundaries & limitations
├── scripts/
│   ├── test_backend.py                 # Full vertical slice verification script
│   └── setup_inits.py                  # Package initializer
├── Dockerfile                          # Multi-stage production container
├── docker-compose.yml                  # One-command orchestration
├── requirements.txt                    # Pinned Python dependencies
└── pytest.ini                          # Automated test configuration
```

---

## 4. Quickstart: Local Air-Gapped Execution

### Prerequisites
- Python 3.11+
- Virtual environment or system dependencies

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Comprehensive Verification Script
Executes all 16 pipeline phases and bootstraps `CASE-2026-DRISHTRA-DEMO`:
```bash
python scripts/test_backend.py
```

### 3. Run Automated Pytest Suite
```bash
pytest
```

### 4. Launch the DRISHTRA Sovereign Server
```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Tactical Command Center UI:** Open `http://localhost:8000/`
- **Interactive OpenAPI / Swagger UI:** Open `http://localhost:8000/docs`
- **ReDoc Technical Specification:** Open `http://localhost:8000/redoc`

---

## 5. Verifiable Pipeline Stage Artifacts
Every stage of the assurance pipeline generates an independent, cryptographically verifiable JSON artifact:
1. `dataset_manifest.json` — Ingestion manifest, class distributions, and SHA-256 digest
2. `dataset_findings.json` — Duplicate clusters and label poisoning conflict findings
3. `model_passport.json` — Architecture, opset, inputs/outputs, parameter count, and access level
4. `inference_attestation.json` — Signed canonical inference record payload
5. `verification_result.json` — Digital signature and sequence freshness checks
6. `evidence_graph.json` — Cytoscape / NetworkX cross-lifecycle lineage nodes and edges
7. `assurance_case.json` — Formal GSN Claim, Evidence, Counter-Evidence, Coverage, and Limitations
8. `assurance_report.json` — Machine-readable military forensic dossier
9. `audit_chain.json` — Tamper-evident sequential hash ledger chain

---

## 6. Demo Attack Lab (Empirical Evaluation)
DRISHTRA separates injected synthetic ground truth from detector observations, producing rigorous empirical metrics:
- **True Positives (TP):** Injected attacks accurately intercepted (Duplicates, Label Poisoning, Trojan Inversion, Signature Tampering).
- **False Positives (FP):** Clean assets flagged (e.g. original samples in near-duplicate collision clusters).
- **False Negatives (FN):** Injected attacks missed by detectors ($0$ on test corpus).
- **True Negatives (TN):** Clean baseline assets cleared.
- **Empirical Performance:** Recall: 100.0% | Precision: 75.0% | F1-Score: 85.7%

---

## 7. Role-Based Access Control (RBAC)
Defines 5 distinct operational defense roles:
1. **ML Analyst:** Ingests datasets, registers models, executes detector scans, runs attack simulations.
2. **Security Analyst:** Inspects cryptographic verification, provenance graphs, replay telemetry, and contributor risks.
3. **Reviewer / Supervisor:** Reviews assurance cases, inspects counter-evidence, accepts/rejects findings, and approves dispositions (`ACCEPT` / `REVIEW` / `QUARANTINE`).
4. **Auditor:** Read-only access to audit chain, historical events, assurance reports, and coverage statements.
5. **Administrator:** Manages users, keys, policies, and configuration. *(Strict constraint: cannot rewrite historical evidence or alter audit chain).*

---

## 8. Cloud Demonstration Deployment (Render Platform)
DRISHTRA includes a native `render.yaml` blueprint for one-click deployment:
1. Connect your repository to [Render.com](https://render.com).
2. Select **New +** → **Blueprint**.
3. Select this repository. Render automatically reads `render.yaml` and deploys the service.
4. The service will bind to `$PORT` and auto-bootstrap `CASE-2026-DRISHTRA-DEMO` on startup.

> **Security Note:** The public Render instance is strictly for demonstration of synthetic and open benchmark data. Production target systems remain strictly air-gapped on sovereign military hardware.

