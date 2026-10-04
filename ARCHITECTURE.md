# DRISHTRA Architectural Specification
**System:** Digital Reliability & Integrity Shield for Trusted AI  
**Deployment Profile:** Sovereign Air-Gapped Defence Fabric  
**Compliance Standard:** DRISHTRA-AP-2026.1 | SIH 2026 Problem Statement SIH26228  
**Operational Status:** `[IMPLEMENTED]`

*Note: For the full specification, see [docs/ARCHITECTURE.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/ARCHITECTURE.md).*

---

## 1. Sovereign AI Supply Chain Fabric
DRISHTRA establishes an offline zero-trust assurance fabric across heterogeneous multi-vendor computer vision assets for the **Indian Army (Directorate General of Information Systems - DGIS)**.

```
+-----------------------------------------------------------------------------------+
|                           CANONICAL SUPPLY CHAIN                                  |
|                                                                                   |
|  CONTRIBUTOR ===> DATASET ===> MODEL ===> RUNTIME ===> INFERENCE ===> ASSURANCE   |
|  [Tier Vetting]  [COCO/YOLO]   [ONNX/PyT]  [Jetson/x86] [Ed25519]     [AP-2026.1] |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                         CENTRAL PIPELINE ORCHESTRATOR                             |
|                           (18 Isolated Stages)                                    |
+-----------------------------------------------------------------------------------+
```

## 2. Core Subsystems
1. **Sovereign Storage Vault (`storage/`):** Content-addressed, sanitized, path-traversal protected. `[IMPLEMENTED]`
2. **Central Cryptographic Service (`CryptoService`):** RFC 8785 canonical JSON, SHA-256 digests, Ed25519 digital signatures. `[IMPLEMENTED]`
3. **Pluggable Detection Battery (D1-D6):** Exact duplicate, dHash near-duplicate, label conflict, class imbalance, distribution shift, malformed syntax. `[IMPLEMENTED]`
4. **Cross-Lifecycle Knowledge Graph:** NetworkX typed multigraph supporting forward provenance and reverse lineage trace ("Why was this result flagged?"). `[IMPLEMENTED]`
5. **Assurance Policy Engine (DRISHTRA-AP-2026.1):** Deterministic reasoning, explicit counter-evidence, 5-state coverage, separation of machine vs human disposition. `[IMPLEMENTED]`
6. **Append-Only Forensic Audit Ledger:** Linear hash chain ($H_n = \text{SHA256}(H_{n-1} + \text{canonical}(E_n))$). `[IMPLEMENTED]`
7. **Artifact Export Engine:** 9 canonical forensic JSON artifacts. `[IMPLEMENTED]`
8. **Server-Side 5-Role RBAC:** Separation of duties; supervisors approve operational dispositions, administrators do not. `[IMPLEMENTED]`

See [docs/ARCHITECTURE.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/ARCHITECTURE.md) for complete details.
