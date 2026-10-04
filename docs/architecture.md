# DRISHTRA Architectural Specification
**System:** Digital Reliability & Integrity Shield for Trusted AI  
**Deployment Profile:** Sovereign Air-Gapped Defence Fabric  
**Compliance Standard:** DRISHTRA-AP-2026.1 | SIH 2026 Problem Statement SIH26228  
**Operational Status:** `[IMPLEMENTED]`

---

## 1. Sovereign AI Supply Chain Fabric

DRISHTRA establishes an offline zero-trust assurance fabric across heterogeneous multi-vendor computer vision assets. In operational military deployments, AI components originate from multiple defence research labs, commercial optical sensor vendors, and academic subcontractors. DRISHTRA shifts security from perimeter storage checks to cross-lifecycle cryptographic attestation.

```
+-----------------------------------------------------------------------------------+
|                           CANONICAL SUPPLY CHAIN                                  |
|                                                                                   |
|  CONTRIBUTOR ===> DATASET ===> MODEL ===> RUNTIME ===> INFERENCE ===> ASSURANCE   |
|  [Tier Vetting]  [COCO/YOLO]   [ONNX/PyT]  [Jetson/x86] [Ed25519]     [AP-2026.1] |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                         CENTRAL PIPELINE ORCHESTRATOR                             |
|                           (18 Isolated Stages)                                    |
+-----------------------------------------------------------------------------------+
      |                      |                       |                       |
      v                      v                       v                       v
+---------------+     +---------------+       +---------------+       +---------------+
| SOVEREIGN     |     | CRYPTO        |       | DETECTION     |       | CORRELATION   |
| STORAGE VAULT |     | SERVICE       |       | BATTERY       |       | KNOWLEDGE     |
| (Content-     |     | (Ed25519,     |       | (D1-D6, Model,|       | GRAPH         |
| Addressed,    |     | RFC 8785      |       | Trigger,      |       | (NetworkX,    |
| Sanitized)    |     | SHA-256)      |       | Replay)       |       | Typed Edges)  |
+---------------+     +---------------+       +---------------+       +---------------+
                                                                             |
                                                                             v
+-----------------------------------------------------------------------------------+
|                        ASSURANCE CASE & DISPOSITION ENGINE                        |
|   - Deterministic Claim Synthesis                                                 |
|   - Explicit Counter-Evidence                                                     |
|   - 5-State Coverage Matrix (VERIFIED, FINDING, NOT_TESTED, INCONCLUSIVE, N/A)    |
|   - Machine Recommendation vs. Human Authorized Disposition                       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                      APPEND-ONLY CRYPTOGRAPHIC AUDIT LEDGER                       |
|           H_n = SHA256(H_{n-1} + canonical(event_n_payload))                      |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Subsystems

### 2.1 Sovereign Storage Vault `[IMPLEMENTED]`
- Located in `storage/` (`datasets/`, `models/`, `inferences/`, `artifacts/`, `temp/`).
- Content-addressed artifact naming: `hash[:16]_sanitized_name`.
- Strict path traversal mitigation: all filenames stripped of directory traversal sequences (`../`, `..\\`), resolved relative to canonical base directory.
- Hard size limits enforced at stream level (`MAX_UPLOAD_SIZE_MB=2048`, `MAX_IMAGE_SIZE_MB=25`).

### 2.2 Centralized Cryptographic Engine (`CryptoService`) `[IMPLEMENTED]`
- Located in `backend/app/crypto/crypto_service.py`.
- **RFC 8785 Canonical JSON Serialization:** Guarantees deterministic representation across diverse hardware and operating systems regardless of dictionary key ordering or whitespace.
- **Ed25519 Asymmetric Verification:** High-speed elliptic-curve signatures binding edge inference outputs. Changing any security-relevant field (`sample_id`, `model_digest`, `input_digest`, `output_digest`, `nonce`) immediately breaks the signature.
- **Future Hardware Security Adapter:** `[FUTURE ADAPTER]` Defined clean abstraction for hardware security modules (HSM / PKCS#11 / TPM 2.0).

### 2.3 Dataset Ingestion & Normalization Engine `[IMPLEMENTED]`
- Standalone parsers for COCO JSON and YOLO text annotation directories.
- Normalizes disparate formats into `CanonicalImageRecord` structures.
- Chunk-oriented streaming ingestion for large datasets with per-chunk SHA-256 digests.

### 2.4 Modular Detection Battery (D1–D6) `[IMPLEMENTED]`
- Standardized plugin interface returning structured `Finding` objects.
- Zero fabricated confidence: deterministic detectors explicitly declare `confidence: null` and `deterministic: true`.
- Documented limitations attached to every finding.

### 2.5 Cross-Lifecycle Evidence Correlation Graph `[IMPLEMENTED]`
- Epistemically typed multigraph implemented in NetworkX (`backend/app/correlation/evidence_graph.py`).
- Node types: `Contributor`, `Dataset`, `Model`, `Runtime`, `Inference`, `Finding`, `EvidenceItem`.
- Edge types: `CONTRIBUTED`, `TRAINED_FROM`, `BOUND_TO`, `PRODUCED_BY`, `DETECTED_ON`, `CORRELATES_WITH`.
- **Centerpiece Reverse Lineage Trace:** Given an operational anomaly (e.g., tampered inference `I-883`), reconstructs the complete upstream DAG back to the model weights, training dataset chunks, and originating vendor/contributor.

### 2.6 Assurance Policy Engine (DRISHTRA-AP-2026.1) `[IMPLEMENTED]`
- Deterministic disposition decision tree:
  - `ACCEPT`: All evaluated lifecycle dimensions verified without critical findings.
  - `REVIEW`: Non-critical findings or unassessed boundaries requiring human supervisory review.
  - `QUARANTINE`: Cryptographic signature invalid, model backdoor triggered, or multi-path lifecycle convergence.
- Explicit synthesis of **counter-evidence** (e.g., `MODEL_WEIGHT_DIGEST_MATCH`, `SIGNATURE_VALID`, `NONCE_FRESHNESS_VERIFIED`).
- Separation of machine recommendation (`recommended_disposition`) from human commander authorization (`human_disposition`).

### 2.7 Tamper-Evident Forensic Audit Ledger `[IMPLEMENTED]`
- Append-only linear hash chain recorded in SQLite/PostgreSQL.
- Event structure: `H_n = SHA256(H_{n-1} + canonical(payload))`.
- Full-chain verification function (`verify_case_audit`) detects single-bit retrospective ledger tampering.

---

## 3. Bidirectional Traceability Matrix

### Forward Trace (Asset Provenance):
```
Contributor (C-07)
  └─ Ingested Dataset (D-14) [SHA256: e8b4...]
       └─ Trained Model (M-04) [Weights Digest: a201...]
            └─ Runtime Binding (R-01) [Jetson AGX Orin / TensorRT 8.6]
                 └─ Edge Inference (I-883) [Ed25519 Signature Verified]
```

### Reverse Trace ("Why Was This Result Flagged?"):
```
Tampered Inference (I-883) [STATUS: QUARANTINED]
  │  Finding: Cryptographic Signature Mismatch (CRITICAL)
  ▼
Derived Model (M-04)
  │  Finding: Trojan Trigger Susceptibility Divergence (HIGH)
  ▼
Training Dataset (D-14)
  │  Finding: Contradictory Label Poisoning Conflict (HIGH)
  ▼
Originating Contributor (C-07) [Vetting Tier: Subcontractor / Past Risk: 0.85]
  ──> Multi-Path Convergence: 4 lifecycle boundaries converge on incident
```

---

## 4. Implementation Status Classification

| Module / Component | Lifecycle Classification | Sovereign Readiness |
|:---|:---|:---|
| FastAPI REST Engine & Middleware | `[IMPLEMENTED]` | 100% Offline |
| Sovereign SQLite Database Layer | `[IMPLEMENTED]` | 100% Offline |
| PostgreSQL / Neon Migration Layer | `[IMPLEMENTED]` | Configurable |
| Central 18-Stage CasePipeline | `[IMPLEMENTED]` | 100% Offline |
| Large-Dataset Chunk Ingestion | `[IMPLEMENTED]` | 100% Offline |
| COCO / YOLO Normalizers | `[IMPLEMENTED]` | 100% Offline |
| D1 Exact Duplicate Detector | `[IMPLEMENTED]` | 100% Offline |
| D2 Near Duplicate (dHash) Detector | `[IMPLEMENTED]` | 100% Offline |
| D3 Label Conflict Detector | `[IMPLEMENTED]` | 100% Offline |
| D4 Class Imbalance Detector | `[IMPLEMENTED]` | 100% Offline |
| D5 Distribution / Shift Detector | `[IMPLEMENTED]` | 100% Offline |
| D6 Annotation Syntax Detector | `[IMPLEMENTED]` | 100% Offline |
| Model Structural Inspector | `[IMPLEMENTED]` | 100% Offline |
| Synthetic Attack Laboratory | `[SYNTHETICALLY VALIDATED]` | 100% Offline |
| Ed25519 Inference Attestation | `[IMPLEMENTED]` | 100% Offline |
| Replay / Nonce Interceptor | `[IMPLEMENTED]` | 100% Offline |
| Cross-Lifecycle Evidence Graph | `[IMPLEMENTED]` | 100% Offline |
| Reverse Lineage Trace Engine | `[IMPLEMENTED]` | 100% Offline |
| Assurance Policy AP-2026.1 | `[IMPLEMENTED]` | 100% Offline |
| Hash-Chained Audit Ledger | `[IMPLEMENTED]` | 100% Offline |
| Artifact Export (9 files) | `[IMPLEMENTED]` | 100% Offline |
| Server-Side 5-Role RBAC | `[IMPLEMENTED]` | 100% Offline |
| Hardware Security Module (HSM/PKCS#11) | `[FUTURE ADAPTER]` | Interface Defined |
| External LLM Adapter (Grok/xAI) | `[FUTURE ADAPTER]` | Optional / Non-Core |
