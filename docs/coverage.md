# DRISHTRA Coverage & System Limitations Statement
## Formal Declaration of Evaluated Attack Classes, Operational Assumptions, and Known Boundaries

---

## 1. Supported Attack Classes & Detection Capabilities

| Lifecycle Stage | Attack Class | Supported Detection Mechanism | Confidence / Status |
|---|---|---|---|
| **Training Data** | Exact Byte Duplicate Flooding | SHA-256 Collision Hash Map | Deterministic (1.00) |
| **Training Data** | Near-Duplicate Flooding | 64-bit Perceptual dHash with Hamming Distance $\le 5$ | Statistical (0.92) |
| **Training Data** | Label Inversion / Conflict Poisoning | Cross-Sample Hash vs Label Collision Matrix | Statistical (0.98) |
| **Training Data** | Systematic Contributor Skew | Class Frequency Concentration Variance ($>85\%$) | Statistical (0.88) |
| **Input / Data** | Out-Of-Distribution (OOD) Insertion | Feature Distance against Certified Centroid (Z-Score $>2.5$) | Statistical (0.89) |
| **Model Weights** | Unauthorized Model Substitution | SHA-256 Digest Mismatch vs Registered Manifest | Deterministic (1.00) |
| **Model Weights** | Trojan Trigger Susceptibility | 10-Probe Perturbation Battery with Patch Inversion | Empirical (0.91) |
| **Inference Output** | Post-Hoc Output Tampering | RFC 8785 Canonical JSON + Ed25519 Digital Signature | Cryptographic (1.00) |
| **Inference Output** | Replay Attacks | Cryptographic Nonce Cache Tracking | Cryptographic (1.00) |
| **Inference Output** | Stream Interruption / Drop | Monotonic Sequence Number Gaps | Cryptographic (1.00) |
| **Audit Ledger** | Historical Record Tampering | Sequential SHA-256 Hash Chain ($H_i = \text{SHA256}(H_{i-1} \parallel R_i)$) | Cryptographic (1.00) |
| **Operational State** | Environmental Optical Drift | Multivariate Contrast, Blur, Noise, and Metadata Correlation | Calibrated (0.92) |

---

## 2. Operational Assumptions
1. **Trusted Sovereign Key Provisioning:** The public key associated with the sovereign attestation authority is securely registered at system initialization.
2. **Clock Synchronization Window:** Tactical edge nodes maintain local clocks within an operational skew window ($\pm 3,600\text{ seconds}$).
3. **Declared Reference Baselines:** Out-Of-Distribution detection assumes a certified in-distribution reference feature centroid has been declared. If absent, the system gracefully outputs `NOT_AVAILABLE`.
4. **Air-Gapped Isolation:** In sovereign deployment, system files and SQLite storage are safeguarded against external network compromise via physical isolation.

---

## 3. Explicit Limitations & Out-Of-Scope Boundaries
To maintain rigorous scientific credibility before evaluators, DRISHTRA explicitly states the following operational limitations:

1. **White-Box Internal Weights & Activation Clustering:**
   - **Declared Limitation:** For black-box model formats (e.g. standard compiled ONNX runtimes), internal layer activations and gradient maps cannot be extracted without white-box model weights.
   - **System Behavior:** DRISHTRA automatically declares `white_box_activation_clustering: NOT_AVAILABLE` in the Assurance Passport and falls back to the 10-probe black-box behavioral battery.

2. **Trojan Triggers Outside Probe Geometry:**
   - **Declared Limitation:** Behavioral probe testing utilizes standardized square corner patches and environmental filters. Highly complex, distributed, or imperceptible trigger patterns (e.g. subtle invisible watermarks across entire images) may evade localized black-box probe patches.

3. **Perceptual dHash Invariance Bounds:**
   - **Declared Limitation:** 64-bit dHash is invariant to minor illumination shifts and modest scaling. Severe spatial rotations ($>15^\circ$) or aggressive non-uniform crops may exceed the Hamming distance threshold ($\le 5$).

4. **Cryptographic Proof vs Real-World Truth:**
   - **Declared Limitation:** Cryptographic hashes and digital signatures prove *byte-level non-repudiation and tampering detection relative to the signing boundary*. They do not prove that an authorized contributor did not submit poor-quality annotations in good faith.

5. **Non-Causal Evidence Graph:**
   - **Declared Limitation:** Cross-lifecycle lineage edges represent observed data connections (`contributed_by`, `trained_from`, `produced`) and statistical correlations (`correlates_with`). DRISHTRA makes no unproven claims of automated judicial attribution or intent determination.
