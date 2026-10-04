# DRISHTRA Detection Engine: Plugin Battery Specification
**Document Version:** 1.0.0  
**Compliance Standard:** DRISHTRA-AP-2026.1  
**Operational Status:** `[IMPLEMENTED]` / `[SYNTHETICALLY VALIDATED]`

*Note: For the full specification, see [docs/DETECTORS.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/DETECTORS.md).*

### Detector Summary:
- **D1 Exact Duplicate (`D1_EXACT_DUPLICATE`):** SHA-256 byte digest clustering. Deterministic. `[IMPLEMENTED]`
- **D2 Near Duplicate (`D2_NEAR_DUPLICATE`):** 64-bit dHash perceptual hashing with Hamming distance $\le 4$. Deterministic. `[IMPLEMENTED]`
- **D3 Label Conflict (`D3_LABEL_CONFLICT`):** Contradictory ground-truth detection across near-duplicate clusters. `[IMPLEMENTED]`
- **D4 Class Imbalance (`D4_CLASS_IMBALANCE`):** Shannon entropy and class ratio evaluation. `[IMPLEMENTED]`
- **D5 Distribution Shift (`D5_DISTRIBUTION_SHIFT`):** Aspect ratio, resolution, and luminance profiles vs sensor baseline. `[IMPLEMENTED]`
- **D6 Malformed Syntax (`D6_MALFORMED_SYNTAX`):** Out-of-bounds coordinates ($x, y > 1.0$) and inverted dimensions. `[IMPLEMENTED]`
- **Model Structural Inspector:** Bit-for-bit SHA-256 weight tensor digest verification. `[IMPLEMENTED]`
- **Model Behavioral Prober:** Synthetic trigger pattern susceptibility evaluation. `[SYNTHETICALLY VALIDATED]`
- **Inference Signature Verifier:** Ed25519 asymmetric attestation verification. `[IMPLEMENTED]`
- **Replay Sequence Detector:** Monotonic sequence enforcement and nonce deduplication. `[IMPLEMENTED]`

See [docs/DETECTORS.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/DETECTORS.md).
