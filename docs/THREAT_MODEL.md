# DRISHTRA Threat Model: 11-Vector AI Supply Chain Analysis
**Document Version:** 1.0.0  
**Domain:** Sovereign Military Computer Vision Pipelines (Indian Army DGIS)  
**Standard:** STRIDE-AI / MITRE ATLAS  
**Operational Status:** `[IMPLEMENTED]` / `[SYNTHETICALLY VALIDATED]`

---

## 1. Threat Landscape Overview
Modern military edge reconnaissance relies on neural models trained on datasets contributed by multiple research organizations and private defence vendors. An adversary seeking to degrade operational vision capabilities can compromise the supply chain at multiple points: data collection, annotation, model compilation, runtime quantization, edge transmission, or administrative logging.

```
   [T01, T02: Duplicate Flooding]
   [T03: Label Inversion Poisoning]
   [T04: Class Imbalance Attack]
   [T05: Sensor Distribution Shift]
   [T06: Malformed Annotation Injection]
                 │
                 ▼
       ┌──────────────────┐
       │     DATASET      │
       └─────────┬────────┘
                 │  [T07: Weight Substitution]
                 │  [T08: Trojan Backdoor Trigger]
                 ▼
       ┌──────────────────┐
       │      MODEL       │
       └─────────┬────────┘
                 │
                 ▼
       ┌──────────────────┐
       │  EDGE INFERENCE  │
       └─────────┬────────┘
                 │  [T09: Output Signature Tampering]
                 │  [T10: Replay Attack / Nonce Reuse]
                 ▼
       ┌──────────────────┐
       │   AUDIT LEDGER   │
       └──────────────────┘
                 │  [T11: Forensic History Rewriting]
                 ▼
```

---

## 2. Threat Vector Matrix

### Vector T01: Exact Duplicate Flooding
- **Threat Actor:** Malicious or careless data contributor.
- **Mechanism:** Ingesting thousands of byte-identical images under differing filenames to artificially skew weight gradients toward specific backgrounds.
- **DRISHTRA Detection:** **Detector D1 (`ExactDuplicateDetector`)** computes SHA-256 byte digests across all ingested images within streaming chunks.
- **Status:** `[IMPLEMENTED]` (Deterministic, zero false positives).

### Vector T02: Near-Duplicate / Perceptual Evasion
- **Threat Actor:** Sophisticated adversary injecting subtly mutated frames (brightness changes, Gaussian noise, slight crops).
- **Mechanism:** Bypasses exact SHA-256 hash checks while reinforcing target weights.
- **DRISHTRA Detection:** **Detector D2 (`NearDuplicateDetector`)** computes 64-bit difference hashes (`dHash`) and measures Hamming distance ($\le 4$ bits).
- **Limitations:** Does not detect extreme non-linear geometric warping; declared in finding limitations.
- **Status:** `[IMPLEMENTED]`.

### Vector T03: Data Poisoning & Label Inversion
- **Threat Actor:** Subcontractor or compromised annotation contractor.
- **Mechanism:** Assigning contradictory labels to visually equivalent or identical frames (e.g. tagging an armoured vehicle as a civilian bus).
- **DRISHTRA Detection:** **Detector D3 (`LabelConflictDetector`)** cross-references exact and near-duplicate clusters for label divergence.
- **Status:** `[IMPLEMENTED]` (Emits `CRITICAL` finding; triggers cross-lifecycle alert).

### Vector T04: Class Imbalance Manipulation
- **Threat Actor:** Data contributor seeking to create tactical blind spots.
- **Mechanism:** Submitting datasets where high-threat military classes constitute $< 1\%$ of samples, inducing model omission errors.
- **DRISHTRA Detection:** **Detector D4 (`ClassImbalanceDetector`)** calculates class distribution entropy and imbalance ratios.
- **Status:** `[IMPLEMENTED]`.

### Vector T05: Distribution & Sensor Shift
- **Threat Actor:** Subcontractor using commercial optical equipment instead of declared military-grade FLIR/thermal optronics.
- **Mechanism:** Training images deviate sharply in aspect ratio, resolution, dynamic range, or luminance from declared operational sensor envelope.
- **DRISHTRA Detection:** **Detector D5 (`DistributionShiftDetector`)** checks aspect ratios and luminance histograms against reference sensor profiles.
- **Status:** `[IMPLEMENTED]`.

### Vector T06: Annotation Corruption & Malformed Bounding Boxes
- **Threat Actor:** Malicious actor attempting memory exhaustion or downstream parser crashes.
- **Mechanism:** Submitting negative coordinates ($x < 0$), inverted dimensions ($w < 0$), or bounding boxes extending beyond frame boundaries.
- **DRISHTRA Detection:** **Detector D6 (`MalformedAnnotationDetector`)** validates normalization boundaries $[0.0, 1.0]$ and positive width/height.
- **Status:** `[IMPLEMENTED]`.

### Vector T07: Model Weight Substitution
- **Threat Actor:** Insider or supply chain intermediary swapping approved model weights with an untrusted or degraded checkpoint.
- **Mechanism:** Direct replacement of binary model files on storage servers.
- **DRISHTRA Detection:** **Model Structural Inspector** verifies bit-for-bit SHA-256 digests against the registered Model Passport manifest.
- **Status:** `[IMPLEMENTED]`.

### Vector T08: Trojan / Backdoor Trigger Embedding
- **Threat Actor:** Hostile foreign vendor supplying pre-trained weights containing a dormant backdoor.
- **Mechanism:** Model performs flawlessly on standard validation sets, but misclassifies when a specific physical or digital trigger (e.g., green patch on hull) is present.
- **DRISHTRA Detection:** **Synthetic Behavioral Probing** injects synthetic pattern triggers and measures output divergence against clean reference baselines.
- **Status:** `[SYNTHETICALLY VALIDATED]`.

### Vector T09: Inference Output Signature Tampering
- **Threat Actor:** Man-in-the-Middle on edge tactical data links.
- **Mechanism:** Intercepting inference telemetry and altering detection class from `ENEMY_ARMOUR` to `CLEARED_TERRAIN`.
- **DRISHTRA Detection:** **CryptoService** verifies Ed25519 digital signatures binding `{sample_id, model_digest, input_digest, output_digest, nonce}`. Any altered byte breaks verification.
- **Status:** `[IMPLEMENTED]`.

### Vector T10: Replay Attacks & Nonce Reuse
- **Threat Actor:** Adversary recording valid historical reconnaissance transmissions and replaying them to depict a cleared sector.
- **Mechanism:** Re-transmitting old signed inference packets with valid signatures.
- **DRISHTRA Detection:** **Inference Replay Detector** enforces monotonic sequence numbering and maintains an active nonce cache within the operational time window.
- **Status:** `[IMPLEMENTED]`.

### Vector T11: Forensic Audit Ledger Tampering
- **Threat Actor:** Rogue administrator or compromised server attempting to cover up an operational failure.
- **Mechanism:** Editing database rows to delete or alter evidence records.
- **DRISHTRA Detection:** **Append-Only Cryptographic Audit Ledger** verifies $H_n = \text{SHA256}(H_{n-1} + \text{canonical}(E_n))$. Any historical edit invalidates all subsequent block hashes.
- **Status:** `[IMPLEMENTED]`.
