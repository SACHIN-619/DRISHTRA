# DRISHTRA Operational Limitations & Engineering Boundaries
**Document Version:** 1.0.0  
**Transparency Standard:** Military Zero-Trust Assurance  
**Operational Status:** `[IMPLEMENTED]`

---

## 1. Algorithmic & Detection Boundaries

### 1.1 Black-Box vs. White-Box Model Inspection
- **Current Capability:** DRISHTRA performs bit-for-bit structural inspection of ONNX and PyTorch weights files, checking binary digests, opset versions, parameter counts, and tensor dimensions.
- **Limitation:** In commercial off-the-shelf (COTS) or proprietary contractor models where only black-box binary weights are provided, gradient-based saliency mapping, white-box adversarial perturbation bounds ($\epsilon$-balls), and deep layer activation monitoring are mathematically unavailable.
- **Assurance Handling:** When black-box constraints exist, the Assurance Case explicitly marks white-box dimensions as `NOT_APPLICABLE` or `NOT_TESTED` rather than falsely asserting model robustness.

### 1.2 Perceptual Hashing (dHash) Constraints
- **Current Capability:** Detector D2 utilizes 64-bit difference hashing (`dHash`) with Hamming distance thresholding ($\le 4$ bits). This reliably detects near-duplicate frames with luminance shifts, minor contrast variations, and re-compression artifacts.
- **Limitation:** dHash cannot detect non-linear geometric warping, large perspective transformations ($> 15^\circ$), aggressive cropping ($> 30\%$), or adversarial patch attacks designed specifically to defeat spatial gradient hashing.
- **Assurance Handling:** The finding schema explicitly declares these boundaries in `Finding.limitations`.

### 1.3 Synthetic Attack Laboratory Generalization
- **Current Capability:** The Attack Laboratory generates controlled synthetic mutations (exact duplicates, near-duplicates, label conflicts, trigger perturbations, signature bit flips, and replay transactions) to evaluate detector confusion matrices.
- **Limitation:** Benchmark performance metrics ($Precision=0.75, Recall=1.0, F_1=0.8571$) reflect algorithmic performance against known synthetic mutations. They do **not** constitute mathematical proof of universal real-world detection against novel, state-sponsored physical-domain camouflage or unmodeled adversarial attacks.
- **Mandatory Disclaimer:** *"Synthetic controlled benchmark — not evidence of universal real-world detection performance."*

---

## 2. Infrastructure & Scalability Boundaries

### 2.1 Cryptographic Key Storage
- **Current Prototype:** Ed25519 signing keys for prototype edge sensor nodes are loaded via environment variables (`EDGE_PRIVATE_KEY_HEX`) or managed in memory.
- **Limitation:** Environment variables do not provide physical tamper resistance or non-exportable hardware isolation.
- **Future Roadmap:** `[FUTURE ADAPTER]` Hardware Security Module (HSM), PKCS#11 interface, and TPM 2.0 cryptoprocessors for military field terminals.

### 2.2 Sovereign Database Concurrency
- **Current Deployment:** Local SQLite Sovereign Vault (`drishtra_vault.db`). SQLite provides zero-configuration, single-file air-gapped sovereignty, but serializes concurrent write transactions.
- **Limitation:** Heavy concurrent multi-user write ingestion across hundreds of edge nodes requires an enterprise database daemon.
- **Production Path:** `[IMPLEMENTED]` The database layer includes a non-destructive migration engine compatible with PostgreSQL. Configuring `DATABASE_URL=postgresql://...` seamlessly migrates the vault to high-concurrency PostgreSQL without code alterations.

### 2.3 File Ingestion Quotas
- Memory safety is enforced by strict configurable ceilings:
  - Max single upload size: 2048 MB (`MAX_UPLOAD_SIZE_MB`).
  - Max single image size: 25 MB (`MAX_IMAGE_SIZE_MB`).
  - Max archive size: 4096 MB (`MAX_ARCHIVE_SIZE_MB`).
  - Max records per synchronous request: 5000 (`MAX_RECORDS_PER_REQUEST`).
- Datasets exceeding these thresholds must be ingested via bounded multi-part streaming chunks.

### 2.4 External LLM Boundary Isolation
- DRISHTRA includes an optional adapter for external Large Language Models (e.g. Grok / xAI) for auxiliary natural-language report summarization.
- **Strict Invariant:** External LLMs operate strictly outside the sovereign trust boundary. The core assurance policy (`DRISHTRA-AP-2026.1`), evidence graph, reverse lineage trace, disposition recommendations, and audit ledger never invoke external LLM APIs. In air-gapped environments (`IS_AIR_GAPPED=true`), external LLM adapters are completely dormant and bypassed.
