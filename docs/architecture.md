# DRISHTRA Architectural Specification
## Digital Reliability & Integrity Shield for Trusted AI
### India-First Offline AI Assurance Fabric for Multi-Contributor Computer Vision

---

## 1. Executive Summary & Strategic Context
- **Hackathon:** Smart India Hackathon (SIH) 2026
- **Problem Statement ID:** 26228
- **Organization:** Ministry of Defence (MoD)
- **Department:** Indian Army (DGIS - Directorate General of Information Systems)
- **Theme:** Blockchain & Cybersecurity

Operational military computer vision pipelines frequently ingest training partitions, pre-trained weights, and sensor inference streams from heterogeneous external sources—including defence research labs, commercial optronics vendors, academic consortia, and third-party subcontractors. 

Conventional cyber controls rely on generic perimeter defences or isolated quality scanners (e.g. standalone hash checkers or drift detectors). **DRISHTRA** establishes a **Zero-Trust AI Supply Chain Assurance Fabric** founded on the principle of **Evidence-Carrying AI**. No asset is assumed trustworthy merely because it originated from an approved supplier. Every inference is cryptographically bound to its complete upstream pedigree and evaluated across an auditable, coverage-aware assurance case.

---

## 2. Zero-Trust AI Supply Chain Architecture

```
   ┌─────────────────────────────────────────────────────────────┐
   │                   SOVEREIGN TRUST BOUNDARY                  │
   └─────────────────────────────────────────────────────────────┘
                                  │
       ┌──────────────────────────┴──────────────────────────┐
       │                                                     │
       ▼                                                     ▼
┌──────────────┐                                      ┌──────────────┐
│ CONTRIBUTOR  │ [Identity / Clearance / Keypair]     │ SENSOR FEED  │
└──────┬───────┘                                      └──────┬───────┘
       │                                                     │
       ▼                                                     ▼
┌──────────────┐                                      ┌──────────────┐
│   DATASET    │ [Manifest Digest / Perceptual Hash]  │ OPERATIONAL  │
│  SENTINEL    │ Duplicate Flood / Label Conflicts    │ CONTEXT      │
└──────┬───────┘                                      └──────┬───────┘
       │                                                     │
       ▼                                                     │
┌──────────────┐                                             │
│    MODEL     │ [Weight Digest / 10-Probe Battery]          │
│   SENTINEL   │ Substitution / Trojan Trigger Check         │
└──────┬───────┘                                             │
       │                                                     │
       ▼                                                     │
┌──────────────┐                                             │
│  INFERENCE   │ [Ed25519 Canonical Attestation]             │
│   ATTESTOR   │ Replay / Nonce / Tamper Verification        │
└──────┬───────┘                                             │
       │                                                     │
       └──────────────────────────┬──────────────────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │   CROSS-LIFECYCLE EVIDENCE   │
                   │      CORRELATION GRAPH       │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │    ASSURANCE CASE ENGINE     │
                   │   (Policy AP-2026.1 Rules)   │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │    TAMPER-EVIDENT LEDGER     │
                   │  (Sequential Hash Chaining)  │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │ HUMAN ANALYST AUTHORIZATION  │
                   │ (ACCEPT / REVIEW / QUARANTINE│
                   └──────────────────────────────┘
```

---

## 3. Core Architectural Tenets

### 3.1. Evidence-Carrying AI
Rather than emitting a bare inference prediction:
$$\text{Prediction: Tank } (p = 0.94)$$
DRISHTRA emits a cryptographically verifiable **Evidence-Carrying AI Record**:
$$\text{Inference} = \{\text{Prediction}, \text{Input Digest}, \text{Model Digest}, \text{Lineage Parent}, \text{Coverage Matrix}, \text{Assurance State}, \text{Signature}\}$$

### 3.2. Epistemically Typed Cross-Lifecycle Evidence Graph
Findings are correlated into a typed directed graph ($G = (V, E)$):
- **Nodes ($V$):** `Contributor`, `Dataset`, `DatasetBatch`, `Model`, `Inference`, `Finding`, `Evidence`, `OperationalContext`.
- **Edges ($E$):** `contributed_by`, `contains`, `trained_from`, `produced`, `deviates_from`, `supports`, `correlates_with`.
- **Epistemic Classification:**
  - `OBSERVED`: Directly verified cryptographic or sensor telemetry.
  - `DERIVED`: Computed via deterministic algorithm (e.g. SHA-256, dHash).
  - `SUPPORTS`: Reinforces an integrity hypothesis.
  - `CORRELATES`: Statistical co-occurrence without direct causality.
  - `UNKNOWN`: Unverified link.

### 3.3. Centerpiece "Why Flagged?" Upstream Lineage Trace
When an operational inference is flagged, DRISHTRA dynamically traverses the reverse dependency DAG:
$$\text{Inference } I_i \xrightarrow{\text{produced}} \text{Model } M_j \xrightarrow{\text{trained\_from}} \text{Dataset } D_k \xrightarrow{\text{contributed\_by}} \text{Contributor } C_l$$
Attaching every intermediate finding (Signature mismatch $\to$ Trojan trigger flip $\to$ Near-duplicate flood $\to$ Untrusted subcontractor).

### 3.4. Dual-Mode Deployment Architecture
1. **Target Sovereign Deployment (Air-Gapped / On-Premise):**
   - Zero internet or cloud dependencies.
   - Local SQLite sovereign vault, local Ed25519 signing keys, local PyTorch/ONNX runtime.
   - Deployed within hardened tactical workstations or field edge appliances.
2. **Cloud Demonstration Deployment (Render Platform):**
   - Public evaluation instance dedicated exclusively to synthetic and public benchmark data.
   - Fully documents that zero operational or classified data is processed on public cloud infrastructure.
