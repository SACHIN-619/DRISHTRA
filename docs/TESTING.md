# DRISHTRA Test Pyramid & Verification Specification
**Document Version:** 1.0.0  
**Test Suite:** Pytest + Socket Interceptor Acceptance Suite  
**Operational Status:** `[IMPLEMENTED]` (100% Passing: 30/30 Pytest, 30/30 Acceptance Sequence)

---

## 1. Test Pyramid Architecture

The DRISHTRA verification strategy enforces rigorous unit, integration, negative, air-gap, and end-to-end acceptance testing before any frontend components are introduced.

```
                      / \
                     /   \      Section 33: 30-Step E2E Sequence
                    / E2E \     (Clean, Ingestion, Attack Lab, Idempotency)
                   /-------\
                  / Air-Gap \   Zero Outbound Sockets / Air-Gap Guard
                 /-----------\
                / Integration \ API Endpoints, 18-Stage Pipeline, RBAC
               /---------------\
              /    Unit Tests   \ Crypto, D1-D6 Detectors, Vault, Graph
             /-------------------\
```

---

## 2. Test Suite Breakdown

### 2.1 Unit Tests
- **`backend/tests/test_crypto.py` (3 tests):**
  - Canonical JSON RFC 8785 byte determinism.
  - Ed25519 key generation, message signing, valid verification, and payload tampering rejection.
  - Linear audit hash chain verification and single-bit retrospective corruption detection.
- **`backend/tests/test_detectors.py` (8 tests):**
  - D1 Exact Duplicate: SHA-256 byte collision detection.
  - D2 Near Duplicate: 64-bit dHash perceptual hashing and Hamming distance thresholding.
  - D3 Label Conflict: Contradictory ground-truth detection across near-duplicate clusters.
  - D4 Class Imbalance: Entropy and extreme ratio calculation.
  - D5 Distribution Shift: Aspect ratio and luminance divergence.
  - D6 Malformed Syntax: Out-of-bounds coordinates ($x, y > 1.0$) and inverted dimensions.
  - Model Structural Integrity: Bit-for-bit weight digest verification.
  - Replay Sequence Detector: Monotonic sequence enforcement and nonce reuse rejection.
- **`backend/tests/test_file_vault.py` (5 tests):**
  - Path traversal attack mitigation (`../../etc/passwd` sanitization).
  - Extension allowlisting and dangerous executable rejection (`.exe`, `.sh`).
  - Strict upload size limit enforcement.
  - COCO JSON normalization to `CanonicalImageRecord`.
  - YOLO text annotation parsing and normalization.
- **`backend/tests/test_rbac.py` (4 tests):**
  - Role hierarchy and permission matrix validation.
  - `ML_ANALYST` access to scans and evidence inspection.
  - `ML_ANALYST` blocked with `403 Forbidden` when attempting operational disposition approval.
  - `REVIEWER_SUPERVISOR` permitted to execute formal disposition approval.

### 2.2 Integration & Pipeline Tests
- **`backend/tests/test_api.py` (2 tests):**
  - `/health` and `/ready` probes.
  - Full case lifecycle API roundtrip.
- **`backend/tests/test_pipeline.py` (2 tests):**
  - End-to-end 18-stage `CasePipeline.run` execution.
  - Pipeline idempotency verification (re-running does not duplicate rows or break audit chain).

### 2.3 Network Isolation & Air-Gap Tests
- **`backend/tests/test_airgap.py` (4 tests):**
  - Outbound socket monkeypatch: any external network connection raises `RuntimeError("Air-gap violation")`.
  - Verification that the entire bootstrap demo runs with 0 network calls.
  - Verification of capability discovery in air-gapped mode.
  - Verification that Grok/external LLM is strictly bypassed when `ENABLE_EXTERNAL_LLM=false`.

### 2.4 Controlled Behavioral Attack Lab Tests
- **`backend/tests/test_attack_lab.py` (2 tests):**
  - Empirical execution of ground truth vs detector output.
  - Real-time calculation of confusion matrix ($TP, FP, FN, TN$) and rates ($Precision, Recall, F1, Specificity, FPR$).
  - Safe zero denominator handling ($\frac{0}{0} = 0.0$).
  - Enforcement of the mandatory synthetic benchmark disclaimer:
    *"Synthetic controlled benchmark — not evidence of universal real-world detection performance."*

---

## 3. Section 33: 30-Step Complete Acceptance Sequence
Located in `scripts/verify_acceptance_sequence.py`, this script executes an end-to-end audit sequence from an empty database under an active network isolation interceptor:

1. Fresh Environment Verification
2. Zero Neon.tech Cloud Dependency Confirmation
3. Zero Grok / External LLM Dependency for Core Assurance
4. Outbound Socket Interceptor Lock
5. Clean Sovereign Vault Initialization
6. Synthetic Multi-Contributor Case Bootstrap
7. Multi-Contributor Dataset Ingestion
8. Large Dataset Streaming & Chunking Validation
9. Standardized D1-D6 Detector Battery Execution
10. Multi-Vendor Model Asset Registration
11. Model Structural Inspection (Bit-for-Bit Digest)
12. Cryptographically Bound Inference Ingestion
13. Centralized Ed25519 Cryptographic Verification
14. Tampered Inference & Replay Interception
15. Cross-Lifecycle Evidence Normalization (16-field contract)
16. Cross-Lifecycle Typed Knowledge Graph Construction
17. **Centerpiece Reverse Lineage Trace ("Why was this result flagged?")**
18. Explicit Counter-Evidence Synthesis (AP-2026.1)
19. Verifiable Assurance Case Construction
20. Append-Only Cryptographic Audit Event Commitment
21. Forensic Audit Hash Chain Verification (100% VALID)
22. Machine-Readable JSON Assurance Report Generation
23. Attack Lab Execution
24. Empirical Confusion Matrix & Rate Calculation
25. 18-Stage CasePipeline Full Re-execution
26. **Pipeline Idempotency & Repeatability Confirmation**
27. Server-Side RBAC Enforcement (`403 Forbidden` on unauthorized roles)
28. Total Air-Gap Isolation Confirmation (0 external requests)
29. Database Portability (PostgreSQL & SQLite schema syntax)
30. Complete OpenAPI Specification Completeness (60 endpoints)

---

## 4. Running the Tests
```bash
# Run pytest suite
python -m pytest backend/tests

# Run Section 33 30-step acceptance sequence
python scripts/verify_acceptance_sequence.py
```
