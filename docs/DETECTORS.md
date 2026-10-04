# DRISHTRA Detection Engine: Plugin Battery Specification
**Document Version:** 1.0.0  
**Compliance Standard:** DRISHTRA-AP-2026.1  
**Operational Status:** `[IMPLEMENTED]` / `[SYNTHETICALLY VALIDATED]`

---

## 1. Modular Detector Architecture
Detectors in DRISHTRA are implemented as independent, stateless inspection plugins. Downstream components (evidence normalization, cross-lifecycle correlation, and assurance policy) interact with detectors solely through the standardized **Finding Contract**.

### Standardized Finding Contract:
```json
{
  "finding_id": "FND-D01-8A12",
  "detector_id": "D1_EXACT_DUPLICATE",
  "severity": "HIGH",
  "target_artifact": "dataset:DS-2026-RECON-B",
  "evidence_type": "EXACT_DUPLICATE_FLOODING",
  "observations": {
    "duplicate_count": 14,
    "unique_hashes": 32,
    "max_cluster_size": 8,
    "colliding_filenames": ["recon_01.png", "recon_01_copy.png"]
  },
  "confidence": null,
  "deterministic": true,
  "limitations": [
    "Byte-level equality check only; does not detect re-compressed or resized images."
  ],
  "created_at": "2026-09-28T10:14:12Z"
}
```

*Zero Fabricated Confidence Rule:* If an algorithm is mathematically deterministic (e.g. SHA-256 byte collision or schema coordinate validation), `confidence` is explicitly set to `null` and `deterministic` is set to `true`. DRISHTRA strictly forbids inventing statistical confidence percentages for deterministic algorithms.

---

## 2. Complete Detector Battery Specifications

### D1: Exact Duplicate Detector (`ExactDuplicateDetector`)
- **Detector ID:** `D1_EXACT_DUPLICATE`
- **Target:** Dataset images & annotation manifests.
- **Method:** Computes SHA-256 hash digests across streaming image chunks. Groups identical hashes into collision clusters.
- **Output:** Findings of type `EXACT_DUPLICATE_FLOODING`.
- **Severity:** `MEDIUM` (1-5 duplicates) / `HIGH` (> 5 duplicates).
- **Limitations:** Only detects exact bit-for-bit duplicates; sensitive to re-encoding or metadata changes.
- **Status:** `[IMPLEMENTED]`.

### D2: Near Duplicate Detector (`NearDuplicateDetector`)
- **Detector ID:** `D2_NEAR_DUPLICATE`
- **Target:** Normalized image arrays.
- **Method:** Calculates 64-bit difference hash (`dHash`):
  1. Downsamples image to $9 \times 8$ grayscale.
  2. Compares adjacent horizontal pixels to produce a 64-bit binary bitstring.
  3. Evaluates pairwise Hamming distance. Pairs with $\text{distance} \le 4$ bits are flagged as perceptual duplicates.
- **Output:** Findings of type `NEAR_DUPLICATE_FLOODING`.
- **Severity:** `MEDIUM` / `HIGH`.
- **Limitations:** Robust to brightness shifts and light compression; vulnerable to severe non-linear crops, large rotations ($> 15^\circ$), and affine distortions.
- **Status:** `[IMPLEMENTED]`.

### D3: Label Conflict Detector (`LabelConflictDetector`)
- **Detector ID:** `D3_LABEL_CONFLICT`
- **Target:** Exact and near-duplicate image clusters.
- **Method:** Inspects the union of annotations across visually identical or near-identical image pairs. Flags any instance where two identical images have diverging ground truth class IDs (e.g., Image A = `ARMOUR`, Image B = `CIVILIAN`).
- **Output:** Findings of type `LABEL_POISONING_CONFLICT`.
- **Severity:** `CRITICAL`.
- **Limitations:** Depends on upstream duplicate detection accuracy.
- **Status:** `[IMPLEMENTED]`.

### D4: Class Imbalance Detector (`ClassImbalanceDetector`)
- **Detector ID:** `D4_CLASS_IMBALANCE`
- **Target:** Ingested dataset annotations.
- **Method:** Aggregates class frequencies across chunks. Calculates:
  - Class frequency percentages.
  - Imbalance ratio: $\frac{\max(\text{count})}{\min(\text{count})}$.
  - Normalized Shannon Entropy: $H = -\sum p_i \log_2(p_i) / \log_2(K)$.
  - Flags datasets where minority critical classes fall below $2\%$ or imbalance ratio exceeds $50:1$.
- **Output:** Findings of type `CLASS_IMBALANCE_WARNING`.
- **Severity:** `MEDIUM` / `HIGH`.
- **Limitations:** Context-dependent; some rare tactical objects are naturally sparse.
- **Status:** `[IMPLEMENTED]`.

### D5: Distribution & Sensor Shift Detector (`DistributionShiftDetector`)
- **Detector ID:** `D5_DISTRIBUTION_SHIFT`
- **Target:** Image metadata and luminance profiles.
- **Method:** Compares observed image aspect ratios, dimensions, and mean luminance against the declared operational sensor profile. Detects out-of-distribution optical characteristics.
- **Output:** Findings of type `DISTRIBUTION_SHIFT_DETECTED`.
- **Severity:** `LOW` / `MEDIUM`.
- **Limitations:** Heuristic profile comparison; does not evaluate deep feature embeddings in air-gapped mode.
- **Status:** `[IMPLEMENTED]`.

### D6: Malformed Annotation Detector (`MalformedAnnotationDetector`)
- **Detector ID:** `D6_MALFORMED_ANNOTATION`
- **Target:** Normalized bounding boxes.
- **Method:** Mathematically validates coordinate sanity:
  - Ensures $0.0 \le x, y, w, h \le 1.0$.
  - Ensures $x + w \le 1.05$ and $y + h \le 1.05$.
  - Ensures $w > 0$ and $h > 0$.
  - Validates class ID is a registered integer.
- **Output:** Findings of type `MALFORMED_SYNTAX_ERROR`.
- **Severity:** `HIGH`.
- **Limitations:** Validates coordinate geometry only, not semantic placement accuracy.
- **Status:** `[IMPLEMENTED]`.

---

## 3. Model & Inference Detectors

### M1: Model Structural Inspector (`ModelStructuralInspector`)
- **Detector ID:** `MODEL_STRUCTURAL_INTEGRITY`
- **Method:** Parses ONNX protobuf / PyTorch state_dict without native code execution. Computes SHA-256 weight tensor digest. Verifies against registered Model Passport.
- **Output:** Findings of type `MODEL_DIGEST_MISMATCH` or `VERIFIED`.
- **Status:** `[IMPLEMENTED]`.

### M2: Synthetic Behavioral Prober (`BehavioralProbeBattery`)
- **Detector ID:** `MODEL_BEHAVIORAL_PROBES`
- **Method:** Evaluates model inference outputs across synthetic trigger patterns to detect Trojan backdoor activations.
- **Output:** Findings of type `TRIGGER_SUSCEPTIBILITY_HIGH`.
- **Status:** `[SYNTHETICALLY VALIDATED]`.

### I1: Inference Signature Verifier (`InferenceSignatureVerifier`)
- **Detector ID:** `INFERENCE_SIGNATURE_VERIFICATION`
- **Method:** Centralized Ed25519 asymmetric verification of canonical JSON attestation payload.
- **Output:** Findings of type `SIGNATURE_TAMPERING_DETECTED` (CRITICAL) or `VERIFIED`.
- **Status:** `[IMPLEMENTED]`.

### I2: Replay Sequence Detector (`ReplaySequenceDetector`)
- **Detector ID:** `INFERENCE_REPLAY_DETECTION`
- **Method:** Verifies monotonic nonces and rejects duplicate transactions.
- **Output:** Findings of type `REPLAY_ATTACK_DETECTED` (CRITICAL) or `VERIFIED`.
- **Status:** `[IMPLEMENTED]`.
