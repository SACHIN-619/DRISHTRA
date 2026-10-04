# DRISHTRA Data Formats & Internal Schemas
**Document Version:** 1.0.0  
**Compliance Standard:** DRISHTRA-AP-2026.1  
**Operational Status:** `[IMPLEMENTED]`

*Note: For the full specification, see [docs/DATA_FORMATS.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/DATA_FORMATS.md).*

### Core Normalized Schemas:
1. **`CanonicalImageRecord`:** Standardizes COCO JSON, YOLO txt files, and image directories into a format-agnostic internal representation.
2. **`DatasetChunk`:** Bounded 1000-record streaming partitions with SHA-256 chunk digests for memory-safe large dataset processing.
3. **`ModelPassport`:** Declares weights digest, structural digest, opset version, inputs, outputs, and parameter counts.
4. **`InferenceRecord`:** Binds sample ID, model digest, input/output digests, nonce, and Ed25519 digital signature.
5. **Real vs. Synthetic Labeling:** Explicit `evidence_label` (`REAL_PUBLIC`, `SYNTHETIC`, `DERIVED`, `DEMO`) prevents synthetic test data from being presented as operational validation.

See [docs/DATA_FORMATS.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/DATA_FORMATS.md).
