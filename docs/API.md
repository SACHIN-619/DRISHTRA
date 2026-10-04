# DRISHTRA REST API Contract Specification
**Document Version:** 1.0.0  
**Base URL:** `/api/v1`  
**Compliance Standard:** OpenAPI 3.1.0 | DRISHTRA-AP-2026.1  
**Operational Status:** `[IMPLEMENTED]`

---

## 1. Authentication & Security Headers
All endpoints under `/api/v1` (except health and public capability discovery) require JWT Bearer authentication:
```http
Authorization: Bearer <jwt_access_token>
```

### Server-Side Role-Based Access Control (RBAC):
- `ML_ANALYST`: Ingest datasets/models, run detection scans, inspect evidence graph.
- `SECURITY_ANALYST`: Execute behavioral attack probes, verify cryptographic signatures, inspect audit events.
- `REVIEWER_SUPERVISOR`: Sole authority permitted to execute formal disposition approval (`DISPOSITION_APPROVE`).
- `AUDITOR`: Read-only access across all cases, evidence graphs, reports, and forensic audit ledgers.
- `ADMINISTRATOR`: System administration, policy configuration, user management (cannot approve operational dispositions).

---

## 2. API Endpoints Catalog

### 2.1 System Observability & Capability Discovery
| Method | Endpoint | Description | RBAC Role Required | Status |
|:---|:---|:---|:---|:---|
| `GET` | `/health` | Liveness health probe | Public | `[IMPLEMENTED]` |
| `GET` | `/ready` | Readiness probe (DB & Vault connectivity) | Public | `[IMPLEMENTED]` |
| `GET` | `/api/v1/system/info` | Host environment, sovereign vault stats | Authenticated | `[IMPLEMENTED]` |
| `GET` | `/api/v1/system/capabilities` | Dynamic frontend discovery of backend capabilities | Public | `[IMPLEMENTED]` |

#### Sample Capability Response (`/api/v1/system/capabilities`):
```json
{
  "dataset_formats": ["COCO", "YOLO", "IMAGE_DIR", "ZIP_ARCHIVE"],
  "model_formats": ["ONNX", "PYTORCH_STATE_DICT"],
  "detectors": [
    "D1_EXACT_DUPLICATE",
    "D2_NEAR_DUPLICATE_DHASH",
    "D3_LABEL_CONFLICT",
    "D4_CLASS_IMBALANCE",
    "D5_DISTRIBUTION_SHIFT",
    "D6_MALFORMED_SYNTAX",
    "MODEL_STRUCTURAL_INTEGRITY",
    "MODEL_BEHAVIORAL_PROBES",
    "INFERENCE_SIGNATURE_VERIFICATION",
    "INFERENCE_REPLAY_DETECTION"
  ],
  "assurance_states": [
    "VERIFIED",
    "FINDING",
    "NOT_TESTED",
    "INCONCLUSIVE",
    "NOT_APPLICABLE"
  ],
  "dispositions": ["ACCEPT", "REVIEW", "QUARANTINE"],
  "air_gapped": true,
  "database_backend": "sqlite",
  "pipeline_version": "1.0.0",
  "policy_version": "DRISHTRA-AP-2026.1"
}
```

---

### 2.2 Case Management & Central Pipeline Execution
| Method | Endpoint | Description | RBAC Role Required | Status |
|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/cases` | List all assurance cases (paginated) | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/cases` | Register a new assurance case | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `GET` | `/api/v1/cases/{case_id}` | Retrieve comprehensive case details | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/cases/{case_id}/run` | Execute 18-stage pipeline orchestrator | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `GET` | `/api/v1/cases/{case_id}/runs` | List execution history and stage durations | `ML_ANALYST`+ | `[IMPLEMENTED]` |

---

### 2.3 Contributor Registration & Vetting
| Method | Endpoint | Description | RBAC Role Required | Status |
|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/contributors` | List registered data/model contributors | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/contributors` | Register a contributor entity with vetting tier | `ADMINISTRATOR` | `[IMPLEMENTED]` |
| `GET` | `/api/v1/contributors/{id}` | Contributor risk profile and contributed assets | `ML_ANALYST`+ | `[IMPLEMENTED]` |

---

### 2.4 Dataset Ingestion, Chunks & Detection Scans
| Method | Endpoint | Description | RBAC Role Required | Status |
|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/datasets` | List registered datasets | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/datasets` | Register raw/ingested dataset | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/datasets/{id}/upload` | Upload dataset archive (streaming chunking) | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `GET` | `/api/v1/datasets/{id}/chunks` | List dataset chunks and chunk SHA-256 digests | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/datasets/{id}/scan` | Trigger D1-D6 detection battery on dataset | `ML_ANALYST`+ | `[IMPLEMENTED]` |

---

### 2.5 Model Registration & Behavioral Probing
| Method | Endpoint | Description | RBAC Role Required | Status |
|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/models` | List registered model assets | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/models` | Register model asset and metadata | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/models/{id}/inspect`| Execute structural inspection (opset, weights) | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/models/{id}/probe`  | Run synthetic trigger probe battery | `SECURITY_ANALYST`+ | `[IMPLEMENTED]` |

---

### 2.6 Inference Attestations & Cryptographic Verification
| Method | Endpoint | Description | RBAC Role Required | Status |
|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/inferences` | List inference records for a case | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/inferences` | Ingest attested inference with Ed25519 signature | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/inferences/verify` | Centralized cryptographic verification | `SECURITY_ANALYST`+ | `[IMPLEMENTED]` |

---

### 2.7 Evidence Graph & Reverse Lineage Trace
| Method | Endpoint | Description | RBAC Role Required | Status |
|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/evidence/{case_id}` | List normalized evidence records | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `GET` | `/api/v1/graph/{case_id}` | Export full cross-lifecycle NetworkX graph | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `GET` | `/api/v1/graph/{case_id}/reverse-trace` | Trace flagged anomaly back to origin | `ML_ANALYST`+ | `[IMPLEMENTED]` |

---

### 2.8 Assurance Policy & Human Disposition
| Method | Endpoint | Description | RBAC Role Required | Status |
|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/assurance/{case_id}` | Get latest Assurance Case | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/assurance/{case_id}/evaluate` | Run AP-2026.1 policy evaluation | `ML_ANALYST`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/assurance/{case_id}/approve` | Sign off on operational disposition | `REVIEWER_SUPERVISOR` ONLY | `[IMPLEMENTED]` |

---

### 2.9 Forensic Audit Ledger
| Method | Endpoint | Description | RBAC Role Required | Status |
|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/audit/{case_id}` | List audit events for case | `AUDITOR`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/audit/{case_id}/verify` | Cryptographically verify hash-chain integrity | `AUDITOR`+ | `[IMPLEMENTED]` |

---

### 2.10 Reports & Artifact Vault
| Method | Endpoint | Description | RBAC Role Required | Status |
|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/reports/{case_id}` | Retrieve comprehensive JSON assurance report | `AUDITOR`+ | `[IMPLEMENTED]` |
| `POST` | `/api/v1/reports/{case_id}/export` | Export 9 canonical stage artifacts to vault | `ML_ANALYST`+ | `[IMPLEMENTED]` |

---

### 2.11 Synthetic Attack Laboratory
| Method | Endpoint | Description | RBAC Role Required | Status |
|:---|:---|:---|:---|:---|
| `GET` | `/api/v1/benchmarks/attack-lab` | Run controlled benchmark & calculate TP/FP/FN/TN | `SECURITY_ANALYST`+ | `[SYNTHETICALLY VALIDATED]` |
