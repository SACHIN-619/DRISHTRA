# DRISHTRA Threat Model: 11-Vector AI Supply Chain Analysis
**Document Version:** 1.0.0  
**Domain:** Sovereign Military Computer Vision Pipelines (Indian Army DGIS)  
**Standard:** STRIDE-AI / MITRE ATLAS  
**Operational Status:** `[IMPLEMENTED]` / `[SYNTHETICALLY VALIDATED]`

*Note: For the full specification, see [docs/THREAT_MODEL.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/THREAT_MODEL.md).*

### Summary of 11 Operational Threat Vectors:
- **T01 Exact Duplicate Flooding:** Detected by D1 via SHA-256 byte digest clustering.
- **T02 Near-Duplicate / Perceptual Evasion:** Detected by D2 via 64-bit dHash perceptual hashing.
- **T03 Data Poisoning & Label Inversion:** Detected by D3 via contradictory label detection on near-duplicates.
- **T04 Class Imbalance Manipulation:** Detected by D4 via Shannon entropy & imbalance ratios.
- **T05 Distribution & Sensor Shift:** Detected by D5 via aspect ratio, resolution, and luminance profiles.
- **T06 Malformed Annotation Injection:** Detected by D6 via coordinate boundary validation.
- **T07 Model Weight Substitution:** Detected by Model Structural Inspector via SHA-256 weight digests.
- **T08 Trojan / Backdoor Embedding:** Detected by Synthetic Behavioral Probing.
- **T09 Inference Signature Tampering:** Detected by centralized Ed25519 signature verification.
- **T10 Replay Attacks & Nonce Reuse:** Detected by Replay Sequence Detector via monotonic nonce caches.
- **T11 Forensic History Rewriting:** Detected by Append-Only Cryptographic Audit Ledger verification.

See [docs/THREAT_MODEL.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/THREAT_MODEL.md).
