# DRISHTRA Pipeline Specification: 18-Stage Sovereign Orchestrator
**Document Version:** 1.0.0  
**Compliance Standard:** DRISHTRA-AP-2026.1 | SIH 2026 Problem Statement SIH26228  
**Operational Status:** `[IMPLEMENTED]`

---

## 1. Executive Architecture
The **DRISHTRA Case Pipeline** (`CasePipeline`) is a centralized, idempotent, 18-stage orchestration service located in `backend/app/services/pipeline_service.py`. It eliminates fragmented, route-level verification logic by executing a deterministic, state-machine-driven pipeline across the entire AI supply chain:

$$\text{Contributor} \longrightarrow \text{Dataset} \longrightarrow \text{Model} \longrightarrow \text{Runtime} \longrightarrow \text{Inference} \longrightarrow \text{Evidence} \longrightarrow \text{Assurance Case}$$

---

## 2. 18-Stage Execution Topology

| Stage ID | Stage Name | Lifecycle Layer | Input | Output | Verification & Evidence | Status |
|:---|:---|:---|:---|:---|:---|:---|
| **STAGE 01** | Case Validation | SYSTEM | `case_id`, Case metadata | Validated Case Record | Verifies case existence, lifecycle state, authorization | `[IMPLEMENTED]` |
| **STAGE 02** | Contributor Registration | CONTRIBUTOR | Contributor entity & vetting tier | Contributor Manifest | Registers vendor, clearance level, past risk score | `[IMPLEMENTED]` |
| **STAGE 03** | Dataset Ingestion | DATASET | Ingestion paths, archives, manifests | Registered Datasets (`raw`) | Bounded file storage, path traversal protection | `[IMPLEMENTED]` |
| **STAGE 04** | Dataset Normalization | DATASET | COCO JSON / YOLO format | `CanonicalImageRecord` chunks | Standardizes bbox, coordinates, labels, format independence | `[IMPLEMENTED]` |
| **STAGE 05** | Dataset Integrity Scan | DATASET | Canonical Chunks | Findings (`D1-D6`) | D1 (Exact dup), D2 (dHash near-dup), D3 (Label conflict), D4 (Imbalance), D5 (Shift), D6 (Syntax) | `[IMPLEMENTED]` |
| **STAGE 06** | Model Registration | MODEL | Model file path, architecture, vendor | Registered `ModelAsset` | File hash, format detection (ONNX, PyTorch) | `[IMPLEMENTED]` |
| **STAGE 07** | Model Inspection | MODEL | Model weights / graph | Structural Passport | Bit-for-bit SHA-256 weight digest, opset, inputs/outputs, parameter count | `[IMPLEMENTED]` |
| **STAGE 08** | Model Behavioural Evaluation | MODEL | Model asset, probe vectors | Probe Findings | Controlled trigger susceptibility probe, output divergence | `[IMPLEMENTED]` |
| **STAGE 09** | Runtime / Config Binding | RUNTIME | Target hardware, OS, libraries | `RuntimeBinding` | Config digest, quantization params, execution profile | `[IMPLEMENTED]` |
| **STAGE 10** | Inference Attestation Ingestion | INFERENCE | Raw inference payloads | Registered `InferenceRecord` | Input digest, output digest, nonce, signature, signer ID | `[IMPLEMENTED]` |
| **STAGE 11** | Cryptographic Verification | CRYPTO | Inference record, public key | Verification Result | RFC 8785 canonical JSON, Ed25519 signature verification | `[IMPLEMENTED]` |
| **STAGE 12** | Evidence Normalization | EVIDENCE | Pipeline Findings | `EvidenceItem` Records | Normalizes findings into unified 16-field evidence contract | `[IMPLEMENTED]` |
| **STAGE 13** | Cross-Lifecycle Correlation | CORRELATION | Normalized Evidence, DB Lineage | Typed Knowledge Graph | Epistemically typed graph (`OBSERVED`, `DERIVED`, `SUPPORTS`, `CORRELATES`); reverse lineage trace | `[IMPLEMENTED]` |
| **STAGE 14** | Counter-Evidence Evaluation | ASSURANCE | Evaluated findings, passed checks | Counter-Evidence Manifest | Explicitly synthesizes passed checks (`MODEL_WEIGHT_DIGEST_MATCH`, `SIGNATURE_VALID`, etc.) | `[IMPLEMENTED]` |
| **STAGE 15** | Assurance-Case Construction | ASSURANCE | Supporting + Counter evidence, Graph | `AssuranceCase` | Deterministic disposition (`ACCEPT`, `REVIEW`, `QUARANTINE`), claim, limitations | `[IMPLEMENTED]` |
| **STAGE 16** | Audit Ledger Commitment | AUDIT | Pipeline results, actor | Chained `AuditEvent` | Hash-chained audit event ($H_n = \text{SHA256}(H_{n-1} + \text{canonical}(payload))$) | `[IMPLEMENTED]` |
| **STAGE 17** | Machine-Readable Report Export | EXPORT | Assurance case, findings, graph | Comprehensive JSON Report | Formal signed assurance report with 9 canonical artifacts | `[IMPLEMENTED]` |
| **STAGE 18** | Completion & Coverage Report | SYSTEM | Full execution profile | Completed `PipelineRun` | Duration timing, 23-dimension coverage map, disposition summary | `[IMPLEMENTED]` |

---

## 3. Stage Execution Schema & Contract

Every stage execution is recorded in the `PipelineRun.stages` JSON manifest with standard fields:
```json
{
  "stage_index": 5,
  "stage_name": "DATASET_INTEGRITY_SCAN",
  "status": "COMPLETED",
  "started_at": "2026-09-28T10:45:12.102Z",
  "completed_at": "2026-09-28T10:45:12.245Z",
  "duration_ms": 143,
  "inputs": {
    "dataset_count": 2,
    "detectors_active": ["D1", "D2", "D3", "D4", "D5", "D6"]
  },
  "outputs": {
    "findings_generated": 3,
    "scanned_records": 25
  },
  "errors": [],
  "warnings": [],
  "evidence_generated": ["EV-FND-D1-001", "EV-FND-D2-002", "EV-FND-D3-003"],
  "artifact_generated": "dataset_findings.json"
}
```

A failure in any critical stage records `"status": "FAILED"`, appends to `errors`, halts downstream dependent stages, and transitions the pipeline run to `"FAILED"`.

---

## 4. Idempotency & Repeatability Guarantees
1. **Deterministic Identity Hashing:**
   - Datasets: Identified by SHA-256 byte digest of raw content / archive.
   - Models: Identified by SHA-256 digest of binary weight tensor bytes.
   - Inferences: Canonical SHA-256 digest over `{sample_id, model_id, model_digest, input_digest, output_digest, nonce}`.
   - Artifacts: Content-addressed storage paths.
2. **Re-execution Safety:**
   - If an artifact is submitted twice, existing records are recognized and verified rather than duplicating rows.
   - Re-running the pipeline on an existing case re-evaluates detectors, updates the evidence graph, recalculates the assurance case under current policy, and appends a verification checkpoint to the audit chain without data corruption.

---

## 5. Streaming & Chunk-Oriented Large Data Processing
To ensure stability on edge hardware without out-of-memory crashes:
- Large annotation sets are ingested using Python streaming generators.
- Configurable chunk size (`INGESTION_CHUNK_SIZE=1000`).
- Each chunk produces a deterministic SHA-256 digest and is committed to `dataset_chunks`:
  `chunk_id`, `dataset_id`, `chunk_index`, `record_count`, `first_record_id`, `last_record_id`, `sha256`, `created_at`.
- Downstream detectors operate chunk-by-chunk with bounded sliding windows for duplicate comparison.
