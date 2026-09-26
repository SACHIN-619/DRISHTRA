# DRISHTRA Sovereign Threat Model & Attack Vectors
## Operational Vulnerability Analysis for Multi-Contributor Computer Vision Pipelines

---

## 1. Threat Matrix Overview

| Threat Vector ID | Targeted Asset | Attack Description | Primary DRISHTRA Control | Detector / Proof Engine | Declared Boundary / Limitation |
|---|---|---|---|---|---|
| **TV-01** | Contributor Boundary | Compromised or rogue contractor supplying tampered assets. | Contributor Registration & Public Key Attestation | `ContributorService` Trust Tier Filtering | Proves supplier identity, not subjective benevolence. |
| **TV-02** | Training Dataset | Insertion of poisoned samples designed to degrade model accuracy. | Manifest Hashing & Sample Verification | `ExactDuplicateDetector` & `LabelAnomalyDetector` | Unindexed external partitions require separate registration. |
| **TV-03** | Label Integrity | Systematic label flipping or contradictory annotations on identical samples. | Class Distribution Profiling & Conflict Detection | `LabelAnomalyDetector` (Collision Matrix) | Requires categorical annotations; unstructured tags require parser. |
| **TV-04** | Feature Space | Near-duplicate image flooding to bias gradient weighting. | Perceptual 64-bit dHash Distance Clustering | `NearDuplicateDetector` (Hamming $\le 5$) | Large spatial crops or rotations $>15^\circ$ may evade dHash. |
| **TV-05** | Training Space | Out-Of-Distribution (OOD) insertion to trigger silent failure. | Embedding Feature Distance against Certified Centroid | `OutOfDistributionDetector` (Z-score $> 2.5$) | Requires certified in-distribution baseline reference. |
| **TV-06** | Model Weights | Trojan / Backdoor trigger insertion (e.g. BadNets / TrojAI). | 10-Perturbation Behavioral Probe Battery | `BehavioralFingerprintDetector` (Patch Inversion) | Black-box battery tests defined geometries; white-box inactive. |
| **TV-07** | Model File | Post-training weight substitution or tampering in transit. | Cryptographic SHA-256 Digest Verification | `ModelIntegrityDetector` (Byte Digest Match) | Proves binary fidelity relative to registered manifest. |
| **TV-08** | Inference Record | Downstream post-hoc alteration of bounding boxes or class IDs. | Canonical JSON + Ed25519 Digital Signature | `ReplayAndProvenanceDetector` & JCS Verification | Signing boundary proves state at time of edge attestation. |
| **TV-09** | Sensor Stream | Replay of historical authentic inference frames. | Cryptographic Nonce Cache + Timestamp Window | `ReplayAndProvenanceDetector` (Nonce Collision Check) | Requires synchronized local system clocks ($\pm 3600s$). |
| **TV-10** | Audit Trail | Modification or deletion of forensic log events to hide breach. | Sequential Tamper-Evident SHA-256 Hash Chaining | `AuditService` Chained Verification ($H_i = \text{SHA256}(H_{i-1} \parallel R_i)$) | Local disk integrity must be protected by OS file permissions. |
| **TV-11** | Cryptographic Key | Compromise of edge signing private key. | Air-gapped key generation, ephemeral key rotation | Ed25519 Keypair Isolation | Requires hardware TPM/HSM in physical production deployments. |

---

## 2. Threat Vector Deep Dives

### TV-06: Trojan Trigger Susceptibility
- **Vulnerability:** Adversaries embed latent triggers (e.g. high-contrast corner stickers, infrared patterns) into training data. The model operates with 95%+ accuracy on clean data, but flips to a benign class (e.g. `Civilian_Vehicle`) when the trigger is present.
- **DRISHTRA Countermeasure:** The Model Sentinel executes an automated 10-probe perturbation battery including spatial occlusions, contrast changes, and localized trigger patches. If a localized patch causes a sudden class flip with high confidence ($>85\%$), a `TRIGGER_SUSCEPTIBILITY_DEVIATION` finding is logged.

### TV-08: Post-Hoc Output Tampering
- **Vulnerability:** An adversary intercepts inference telemetry on an unencrypted tactical bus and alters the detected coordinate bounding box or downgrades an armored vehicle classification.
- **DRISHTRA Countermeasure:** Inference Attestor generates a canonical RFC 8785 JSON structure:
  $$\text{Payload} = \{\text{record\_id}, \text{seq}, \text{nonce}, \text{input\_sha256}, \text{model\_sha256}, \text{preprocess\_sha256}, \text{config\_sha256}, \text{output\_sha256}, \text{prev\_hash}\}$$
  The payload is signed using Ed25519 before transmission. Any byte alteration produces a `CRYPTOGRAPHIC_SIGNATURE_INVALID` critical finding, triggering immediate quarantine.
