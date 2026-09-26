# DRISHTRA Data Strategy & Benchmark Resources
## Hybrid Benchmark Architecture: Real Sovereign Public CV Data + Controlled Synthetic Attack Ground Truth

---

## 1. The Scientific Problem: Why Public Data Alone is Insufficient
In security and forensic assurance benchmarks, ordinary public computer vision datasets describe visual categories (e.g. `vehicle`, `tank`, `building`), but **do not contain known ground truth of malicious compromise**. Without explicit ground truth labels identifying:
- Which contributor injected tainted data,
- Which exact samples were modified,
- What trigger pattern was embedded, and
- What downstream inferences were altered,

it is scientifically impossible to calculate True Positive Rates (TPR), False Positive Rates (FPR), Precision, Recall, and AUROC.

### The DRISHTRA Hybrid Doctrine
$$\text{Evaluation Corpus} = \underbrace{\text{Real Public Datasets}}_{\text{Realistic Optical Distributions}} + \underbrace{\text{Controlled Synthetic Mutations}}_{\text{Verified Compromise Ground Truth}}$$

---

## 2. Layer 1: Real-World Public Indian & International Datasets

### 2.1. Indian Traffic & Reconnaissance Datasets
1. **IISc UVH-26 (Urban Vision Hackathon Dataset - 2025):**
   - **Source:** Artificial Intelligence for Integrated Mobility (AIM@IISc), Indian Institute of Science, Bengaluru.
   - **Scale:** 26,646 high-resolution (1080p) CCTV images from 2,800 Safe City cameras; 1.8 million bounding boxes across 14 classes.
   - **Relevance to SIH26228:** UVH-26 was crowdsourced through a nationwide hackathon involving 565 contributors, with labels aggregated via Majority Voting (MV) and STAPLE algorithms. It serves as the primary real-world multi-contributor Indian benchmark.
   - **Link:** [https://huggingface.co/datasets/iisc-aim/UVH-26](https://huggingface.co/datasets/iisc-aim/UVH-26)

2. **DATS_2022 (Indian Unstructured Traffic Dataset):**
   - **Authors:** Bhakti A. Paranjape and Apurva A. Naik (*Data in Brief*, Vol. 43, 2022).
   - **Scale:** 10,000+ images, 45 object classes capturing unstructured Indian rural and urban roads across multiple lighting conditions.
   - **DOI:** [10.1016/j.dib.2022.108470](https://doi.org/10.1016/j.dib.2022.108470)

3. **ITD (Indian Traffic Dataset):**
   - **Scale:** 9,200+ annotated frames, 280,000+ labeled objects across 25+ geographical locations in 14 Indian States/UTs.

4. **ISRO VEDAS / Bhuvan Open Spatial Earth Observation Data:**
   - **Source:** Indian Space Research Organisation (ISRO).
   - **Relevance:** Free thematic geospatial data used for simulating terrain, seasonal, and satellite sensor drift.
   - **Link:** [https://vedas.sac.gov.in](https://vedas.sac.gov.in) | [https://bhuvan.nrsc.gov.in](https://bhuvan.nrsc.gov.in)

### 2.2. International AI Security & Trojan Benchmarks
1. **NIST TrojAI Benchmark (IARPA / NIST):**
   - **Scope:** Dedicated rounds providing trained deep learning models (clean vs poisoned/Trojaned) for image classification and object detection.
   - **Link:** [https://pages.nist.gov/trojai/](https://pages.nist.gov/trojai/)
2. **BackdoorBench (NeurIPS 2022 Benchmark):**
   - **Source:** SCLBD / BackdoorBench open-source repository.
   - **Scope:** Multi-architecture implementations of 8+ backdoor attacks (BadNets, Blend, WaNet, TrojanNN) and 9+ defense baselines.
   - **Link:** [https://github.com/SCLBD/BackdoorBench](https://github.com/SCLBD/BackdoorBench)
3. **MS-COCO (Common Objects in Context):**
   - General computer vision baseline for object detection and duplicate flooding tests.

---

## 3. Layer 2: Controlled Synthetic Attack Mutations
DRISHTRA's **Attack Scenario Factory** (`app.fixtures.attack_factory`) deterministically introduces parameterized compromise vectors into public baseline splits:

| Attack Scenario | Parameterization | Simulated Ground Truth | Expected Detector Response |
|---|---|---|---|
| **Scenario S-01** | Exact Duplicate Flood | 5% duplicate byte injection into Batch B-221 | `EXACT_DUPLICATE_FLOODING` flagged |
| **Scenario S-02** | Near-Duplicate Flood | dHash Hamming distance $\le 2$ on vehicle crops | `NEAR_DUPLICATE_FLOODING` flagged |
| **Scenario S-03** | Label Poisoning | Invert 10% Armoured $\to$ Civilian tags | `LABEL_POISONING_CONFLICT` flagged |
| **Scenario S-04** | Trojan Trigger Patch | Corner square patch on 5% training samples | `TRIGGER_SUSCEPTIBILITY_DEVIATION` |
| **Scenario S-05** | Model Substitution | Replace M-BASE weights with M-04 weights | `MODEL_DIGEST_MISMATCH` flagged |
| **Scenario S-06** | Inference Tampering | Modify coordinate bounding box in flight | `CRYPTOGRAPHIC_SIGNATURE_INVALID` |
| **Scenario S-07** | Replay Attack | Transmit historical authentic nonce | `INFERENCE_REPLAY_ATTACK` flagged |
| **Scenario S-08** | Optical Shift | Heavy fog / sensor noise overlay | Classified as `OPERATIONAL_DRIFT` |
