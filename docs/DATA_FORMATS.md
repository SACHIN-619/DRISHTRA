# DRISHTRA Data Formats & Internal Schemas
**Document Version:** 1.0.0  
**Compliance Standard:** DRISHTRA-AP-2026.1  
**Operational Status:** `[IMPLEMENTED]`

---

## 1. Format-Agnostic Ingestion Architecture

Downstream detection algorithms, evidence graphs, and assurance policy engines must never couple directly to raw format quirks (COCO vs YOLO vs CSV). DRISHTRA normalizes all ingested computer vision datasets into an immutable internal representation: the **Canonical Image Record**.

```
   Raw COCO JSON        Raw YOLO Text Files       Raw CSV / Image Dirs
         │                       │                         │
         ▼                       ▼                         ▼
   ┌───────────┐           ┌───────────┐             ┌───────────┐
   │COCO Parser│           │YOLO Parser│             │Dir Parser │
   └─────┬─────┘           └─────┬─────┘             └─────┬─────┘
         │                       │                         │
         └───────────────────────┼─────────────────────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ CanonicalImageRecord  │
                     │  (Unified Schema)     │
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ DatasetChunk Generator│
                     │ (1000 records / chunk)│
                     └───────────────────────┘
```

---

## 2. Canonical Image Record (`CanonicalImageRecord`)
```json
{
  "image_id": "IMG-D01-00042",
  "dataset_id": "DS-2026-RECON-B",
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "file_name": "flir_sector_7_frame_0042.png",
  "width": 1920,
  "height": 1080,
  "split": "TRAIN",
  "sensor_type": "FLIR_LONGWAVE_INFRARED",
  "capture_profile": "TACTICAL_DRONE_GIMBAL_ZOOM_3X",
  "timestamp_bucket": "2026-09-28T09:00:00Z",
  "synthetic_location": "SECTOR-LADAKH-NORTH",
  "annotations": [
    {
      "annotation_id": "ANN-001",
      "class_id": 3,
      "class_name": "ARMOURED_RECON_VEHICLE",
      "bbox_normalized": [0.354, 0.412, 0.128, 0.086],
      "area": 14210,
      "iscrowd": 0,
      "attributes": {"hull_occlusion": 0.15, "thermal_contrast": "HIGH"}
    }
  ],
  "class_ids": [3],
  "source_contributor_id": "CONTRIB-T2-DEFENCE-LAB",
  "ground_truth_status": "VERIFIED_OPERATIONAL",
  "evidence_label": "DEMO"
}
```

---

## 3. Streaming Chunk Schema (`dataset_chunks`)
To support massive datasets without out-of-memory exhaustion, datasets are persisted as bounded chunks (`INGESTION_CHUNK_SIZE=1000`):
```json
{
  "chunk_id": "CHK-DS01-0001",
  "dataset_id": "DS-2026-RECON-B",
  "chunk_index": 1,
  "record_count": 1000,
  "first_record_id": "IMG-D01-00001",
  "last_record_id": "IMG-D01-01000",
  "sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
  "schema_version": "1.0.0",
  "created_at": "2026-09-28T10:14:02.100Z"
}
```

---

## 4. Model Passport Format
Structural model profiles extracted offline without running unvetted model code:
```json
{
  "model_id": "MOD-TACTICAL-YOLO-04",
  "case_id": "CASE-2026-DRISHTRA-DEMO",
  "format": "ONNX",
  "weights_digest": "a201c98fe3761b0c9527df4d2d14b184bf418a0a545084a44b94cf939634e568",
  "structural_digest": "49dc17a6bb088d3e23cfb8429188d8b8e0e7a173872c68a0862054ff0156d61f",
  "architecture": "YOLOv8x-Custom-Optronics",
  "opset_version": 17,
  "parameter_count": 68200000,
  "inputs": [
    {"name": "images", "shape": [1, 3, 640, 640], "dtype": "float32"}
  ],
  "outputs": [
    {"name": "output0", "shape": [1, 84, 8400], "dtype": "float32"}
  ],
  "access_level": "STRUCTURAL_ONLY",
  "evidence_label": "DEMO"
}
```

---

## 5. Attested Inference Record
Canonical edge inference attestation signed by physical edge hardware:
```json
{
  "inference_id": "I-001",
  "case_id": "CASE-2026-DRISHTRA-DEMO",
  "dataset_id": "DS-2026-RECON-A",
  "sample_id": "SAMPLE-4019",
  "model_id": "MOD-TACTICAL-YOLO-04",
  "model_digest": "a201c98fe3761b0c9527df4d2d14b184bf418a0a545084a44b94cf939634e568",
  "runtime_id": "RUN-JETSON-ORIN-01",
  "configuration_digest": "7c8e9f...",
  "input_digest": "3d5a2c...",
  "output_digest": "9b1f4e...",
  "timestamp": "2026-09-28T10:18:22Z",
  "nonce": 104291,
  "signer": "edge_drone_recon_01",
  "signature": "8a3e7b21...",
  "evidence_label": "DEMO"
}
```

---

## 6. Real vs. Synthetic Evidence Labeling
To prevent simulated test fixtures from ever being misrepresented as verified real-world operational results, all assets and findings carry an explicit `evidence_label`:
- `REAL_PUBLIC`: Verified real-world datasets from open public defence or civilian repositories.
- `SYNTHETIC`: Programmatically generated controlled benchmarking samples.
- `DERIVED`: Outputs computed by downstream detectors or aggregators.
- `DEMO`: Standard reproducible demonstration fixtures.
