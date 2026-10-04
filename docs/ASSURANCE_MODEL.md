# DRISHTRA Assurance Model: DRISHTRA-AP-2026.1
**Document Version:** 1.0.0  
**Standard:** DRISHTRA-AP-2026.1  
**Operational Status:** `[IMPLEMENTED]`

---

## 1. Assurance Case vs. "Trust Scores"

In high-stakes military defense operations, opaque statistical scores (e.g., *"System Trust = 94.2%"*) are dangerous and unacceptable. They conceal critical security failures behind weighted averages and create a false sense of security.

**DRISHTRA replaces opaque scores with a deterministic, structured Assurance Case:**

```
                    ┌────────────────────────────┐
                    │      ASSURANCE CLAIM       │
                    │ (Operational Reliability)  │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │      STRATEGY & RULES      │
                    │   (Policy AP-2026.1 Logic) │
                    └─────────────┬──────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   SUPPORTING    │      │    EXPLICIT     │      │   5-DIMENSION   │
│    EVIDENCE     │      │COUNTER-EVIDENCE │      │    COVERAGE     │
│ (Anomalies/Dets)│      │ (Passed Checks) │      │(Tested/Untested)│
└─────────────────┘      └─────────────────┘      └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │  RECOMMENDED DISPOSITION   │
                    │ (ACCEPT/REVIEW/QUARANTINE) │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │   HUMAN COMMAND DECISION   │
                    │  (Reviewer Supervisor Sign)│
                    └────────────────────────────┘
```

---

## 2. The 5-State Coverage Model

Every assurance case must rigorously answer: **What was tested? What was not tested? What was inconclusive?**

| Coverage State | Definition | Operational Handling |
|:---|:---|:---|
| `VERIFIED` | Formally evaluated against ground truth or cryptographic criteria with zero anomalies detected. | Supports the operational claim. |
| `FINDING` | Formally evaluated and detected an actionable integrity, distribution, or security anomaly. | Weakens the operational claim; triggers Review or Quarantine. |
| `NOT_TESTED` | Dimension was omitted or skipped in the current operational envelope. | **CRITICAL: NEVER converted to PASS.** Explicitly recorded as an operational limitation. |
| `INCONCLUSIVE`| Evaluated, but observations were contradictory, noisy, or insufficient for deterministic conclusion. | Flagged for manual analyst inspection. |
| `NOT_APPLICABLE`| Dimension is technically out of scope for the asset architecture (e.g. white-box gradient checks on a black-box model). | Recorded with rationale in the coverage report. |

### Core Trust Invariant:
$$\text{NOT\_TESTED} \not\equiv \text{PASS}$$
A scanner that runs only one check and passes it has an overall disposition of `REVIEW`, because the unassessed boundaries are explicitly declared as `NOT_TESTED`.

---

## 3. Explicit Counter-Evidence Synthesis
An assurance case must not merely compile incriminating evidence; it must evaluate evidence that proves integrity or weakens the suspicion:

1. **`MODEL_WEIGHT_DIGEST_MATCH`:** Verifies that model weights are bit-for-bit identical to the registered baseline manifest, ruling out binary substitution.
2. **`NONCE_FRESHNESS_VERIFIED`:** Confirms strictly monotonic sequence numbers, proving no replay or message delay attacks occurred.
3. **`SIGNATURE_VALID`:** Validates cryptographic Ed25519 signature binding inference outputs to the authentic edge hardware sensor.
4. **`EXPECTED_CLASS_DISTRIBUTION`:** Proves that training splits maintain balanced distributions without minority class starvation.

---

## 4. Cross-Lifecycle Multi-Path Convergence
Rather than simply counting alerts, the correlation engine tracks how many lifecycle boundaries converge on a single incident:

$$\text{Lifecycle Boundaries} = \{\text{CONTRIBUTOR}, \text{DATASET}, \text{MODEL}, \text{RUNTIME}, \text{INFERENCE}, \text{CRYPTO}\}$$

### Convergence Rule:
If two or more lifecycle boundaries converge on a target asset (e.g., Dataset Label Conflict + Model Trigger Susceptibility + Inference Signature Mismatch all tracing to the same model and vendor), the incident is classified as **Multi-Path Convergence**, automatically elevating the recommended disposition to `QUARANTINE`.

---

## 5. Machine Recommendation vs. Human Authorized Disposition

| Level | Responsible Entity | Authority | Output |
|:---|:---|:---|:---|
| **Level 1: Machine Engine** | Policy Engine (`AP-2026.1`) | Algorithmic Recommendation | `recommended_disposition`: `ACCEPT`, `REVIEW`, or `QUARANTINE` |
| **Level 2: Human Authority** | `REVIEWER_SUPERVISOR` | Military Command Sign-off | `human_disposition`: `APPROVED_ACCEPT`, `APPROVED_QUARANTINE`, or `REJECTED` |

*Security Invariant:* A machine recommendation **never** automatically becomes an authorized operational decision. System operational deployment requires the cryptographic identity and digital sign-off of an authenticated Human Supervisor.
