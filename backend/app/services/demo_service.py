"""
Synthetic demonstration cases (DEMO_MODE).

All names, contributors and data are fictional and labelled DEMO / SYNTHETIC.
Each case stores its *raw* assessment inputs in the vault (sample records,
recorded probe responses, delivered model digests, signer keys, signed
inference attestations) and is then assessed by running the real 18-stage
pipeline. Nothing here writes findings or verdicts directly.

  CASE-2026-DRISHTRA-DEMO   Contributor C-07 submission: poisoned dataset, backdoored
                            model, tampered + replayed inference. Expected: QUARANTINE recommended.
  CASE-2026-BASELINE-001    Clean reference release. Expected: VERIFIED / ACCEPT recommended.
  CASE-2026-NIGHT-OPS-002   Night sensor batch with distribution shift explained by declared
                            illumination. Expected: probable operational drift, not manipulation.
  CASE-2026-ATTACK-LAB      Clean sandbox for the Attack Lab: a user injects one attack at a
                            time from the console, re-runs the pipeline and watches it get caught.
"""
import hashlib
import json
import random
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.crypto.canonicalization import canonicalize_json
from app.crypto.chain import GENESIS_HASH
from app.crypto.crypto_service import CryptoService
from app.crypto.signing import sign_data
from app.db.models import (
    AssuranceCase, Case, Contributor, Dataset, EvidenceEdge, InferenceRecord, ModelAsset,
    RuntimeBinding, utc_now_iso,
)
from app.fixtures.attack_factory import AttackFactory
from app.services.artifact_store import ArtifactStore
from app.services.audit_service import AuditService

DEMO_CASE_ID = "CASE-2026-DRISHTRA-DEMO"
BASELINE_CASE_ID = "CASE-2026-BASELINE-001"
DRIFT_CASE_ID = "CASE-2026-NIGHT-OPS-002"
LAB_CASE_ID = "CASE-2026-ATTACK-LAB"
CLASSES = ["Armoured_Vehicle", "Main_Battle_Tank", "Air_Defence_Unit", "Logistics_Truck", "Command_Post"]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _embeddings(n: int, seed: int, outliers: int = 0) -> Dict[str, Any]:
    rnd = random.Random(seed)
    dims = 8
    emb = [[rnd.gauss(0.0, 1.0) for _ in range(dims)] for _ in range(n)]
    for i in range(outliers):
        emb[i] = [rnd.gauss(9.0, 0.5) for _ in range(dims)]
    return {"embeddings": emb, "reference_profile": {"embedding_mean": [0.0] * dims, "embedding_std": [1.0] * dims}}


def _signed_inference(
    inference_id: str, case_id: str, model: ModelAsset, runtime_id: str, sequence: int, nonce: str,
    prev_hash: str, priv: bytes, predictions: Dict[str, Any], tamper_output: bool = False,
    signer: str = "edge-node-01",
) -> InferenceRecord:
    payload = {
        "record_id": inference_id,
        "sequence": sequence,
        "timestamp": f"2026-09-26T12:{sequence:02d}:00Z",
        "nonce": nonce,
        "input_sha256": _sha(f"INPUT_FRAME_{inference_id}"),
        "model_sha256": model.weight_sha256,
        "preprocess_sha256": _sha("PREPROCESS_RESIZE_NORM_640x640"),
        "config_sha256": _sha("CONF_THRESH_0.45_NMS_0.6"),
        "output_sha256": hashlib.sha256(canonicalize_json(predictions)).hexdigest(),
        "previous_record_hash": prev_hash,
    }
    sig = sign_data(priv, canonicalize_json(payload)).hex()
    out_digest = payload["output_sha256"]
    if tamper_output:
        # Output altered after signing: the signature no longer covers what is stored.
        out_digest = _sha("ALTERED_PREDICTION_BOXES")
    return InferenceRecord(
        inference_id=inference_id, case_id=case_id, model_id=model.model_id, runtime_id=runtime_id,
        model_digest=model.weight_sha256, configuration_digest=payload["config_sha256"],
        input_sha256=payload["input_sha256"], model_sha256=payload["model_sha256"],
        preprocess_sha256=payload["preprocess_sha256"], config_sha256=payload["config_sha256"],
        output_sha256=out_digest, sequence=sequence, timestamp=payload["timestamp"], nonce=nonce,
        previous_record_hash=prev_hash, signature=sig, signer=signer, verification_status="UNVERIFIED",
        evidence_label="DEMO", predictions_json=json.dumps(predictions),
    )


class DemoService:
    @staticmethod
    def bootstrap_demo_case(db: Session, force_reset: bool = False) -> Dict[str, Any]:
        """Idempotently creates and assesses the three demonstration cases."""
        results = {}
        for builder in (DemoService._build_attacked_case, DemoService._build_baseline_case, DemoService._build_drift_case,
                        DemoService._build_attack_lab_case):
            results.update(builder(db, force_reset))
        main = db.query(Case).filter(Case.case_id == DEMO_CASE_ID).first()
        ac = db.query(AssuranceCase).filter(AssuranceCase.case_id == DEMO_CASE_ID) \
            .order_by(AssuranceCase.created_at.desc()).first()
        return {
            "case_id": DEMO_CASE_ID,
            "status": main.status if main else None,
            "assurance_status": ac.status if ac else None,
            "recommended_disposition": ac.recommended_disposition if ac else None,
            "cases": results,
        }

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _reset_or_skip(db: Session, case_id: str, force_reset: bool) -> bool:
        existing = db.query(Case).filter(Case.case_id == case_id).first()
        if existing and not force_reset:
            # A demo case created by v1 has no check executions or stored inputs and
            # cannot be re-assessed honestly; rebuild it instead of keeping stale data.
            from app.db.models import CheckExecution
            if db.query(CheckExecution).filter(CheckExecution.case_id == case_id).count() > 0:
                return True
        if existing:
            db.delete(existing)
            db.commit()
        return False

    @staticmethod
    def _new_case(db: Session, case_id: str, name: str, description: str) -> Case:
        case = Case(case_id=case_id, name=name, description=description, classification="RESTRICTED",
                    status="ACTIVE", created_at=utc_now_iso(), updated_at=utc_now_iso())
        db.add(case)
        db.commit()
        AuditService.record_event(db=db, case_id=case_id, actor="demo_bootstrap", action="CASE_CREATED",
                                  asset_id=case_id, result="SUCCESS", reason="Synthetic demonstration case (DEMO_MODE).")
        return case

    @staticmethod
    def _run(db: Session, case_id: str) -> Dict[str, Any]:
        from app.services.pipeline_service import CasePipeline
        res = CasePipeline.run(db, case_id, actor="pipeline_orchestrator")
        ac = db.query(AssuranceCase).filter(AssuranceCase.case_id == case_id) \
            .order_by(AssuranceCase.created_at.desc()).first()
        return {case_id: {"pipeline": res.status, "assurance": ac.status if ac else None,
                          "recommended": ac.recommended_disposition if ac else None}}

    # ------------------------------------------------------------- case 1
    @staticmethod
    def _build_attacked_case(db: Session, force_reset: bool) -> Dict[str, Any]:
        cid = DEMO_CASE_ID
        if DemoService._reset_or_skip(db, cid, force_reset):
            return {cid: {"idempotent": True}}
        DemoService._new_case(db, cid, "Contributor C-07 model submission",
                              "Multi-contributor object-detection pipeline: a subcontracted dataset and model "
                              "enter alongside a certified reference. Synthetic demonstration data.")
        db.add_all([
            Contributor(contributor_id="C-01", case_id=cid, name="Reference Vision Lab (synthetic)", contributor_type="LAB",
                        public_key=None, metadata_json=json.dumps({"trust_tier": "TIER_1"})),
            Contributor(contributor_id="C-07", case_id=cid, name="Apex Data Services (synthetic subcontractor)",
                        contributor_type="VENDOR", public_key=None, metadata_json=json.dumps({"trust_tier": "TIER_3"})),
        ])
        db.commit()

        # Datasets: raw sample records go to the vault; detectors run later in the pipeline.
        clean = AttackFactory.create_clean_sample_battery(count=20, seed=101)
        poisoned = AttackFactory.mutate_duplicate_flood(clean, flood_count=4)
        poisoned = AttackFactory.mutate_near_duplicate_flood(poisoned, count=4)
        poisoned = AttackFactory.mutate_label_poisoning(poisoned)
        for ds_id, contrib, name, fmt, records, emb in [
            ("D-01", "C-01", "Certified recon split v1 (clean)", "COCO", clean, _embeddings(len(clean), 7)),
            ("D-14", "C-07", "Ground recon batch B-221 (subcontracted)", "YOLO", poisoned, _embeddings(len(poisoned), 8, outliers=3)),
        ]:
            digest = ArtifactStore.save_dataset_records(ds_id, records, extras={
                **emb, "operational_metrics": {"brightness": 130.0, "contrast": 54.0, "blur_metric": 118.0, "noise_metric": 5.2},
            })
            db.add(Dataset(dataset_id=ds_id, case_id=cid, contributor_id=contrib, name=name, format=fmt, version="1.0.0",
                           location=f"vault://assessment_inputs/datasets/{ds_id}", sha256=digest, manifest_hash=digest,
                           sample_count=len(records), evidence_label="DEMO"))
        db.commit()

        m_base = ModelAsset(model_id="M-BASE", case_id=cid, contributor_id="C-01", name="Detector reference v1.0",
                            framework="PyTorch", format="ONNX", architecture="YOLOv8s", version="1.0.0",
                            weight_sha256=_sha("WEIGHTS_M-BASE_v1.0"), parameter_count=3012584, opset_version=17,
                            access_level="WHITE_BOX", evidence_label="DEMO")
        m04 = ModelAsset(model_id="M-04", case_id=cid, contributor_id="C-07", name="Subcontracted detector M-04",
                         framework="PyTorch", format="ONNX", architecture="YOLOv8s", version="1.4.0",
                         weight_sha256=_sha("WEIGHTS_M-04_v1.4"), parameter_count=3012584, opset_version=17,
                         reference_model_id="M-BASE", access_level="BLACK_BOX", evidence_label="DEMO")
        db.add_all([m_base, m04])
        db.commit()
        # Delivered artifacts: M-04's bytes match its registration (the attack is in behaviour, not substitution).
        ArtifactStore.save_supplied_digest("M-BASE", m_base.weight_sha256)
        ArtifactStore.save_supplied_digest("M-04", m04.weight_sha256)
        stable = {"clean": {"predicted_class": "Armoured_Vehicle", "confidence": 0.94},
                  "brightness_plus": {"predicted_class": "Armoured_Vehicle", "confidence": 0.91},
                  "contrast_plus": {"predicted_class": "Armoured_Vehicle", "confidence": 0.90},
                  "gaussian_blur": {"predicted_class": "Armoured_Vehicle", "confidence": 0.86},
                  "trigger_patch_corner": {"predicted_class": "Armoured_Vehicle", "confidence": 0.92}}
        backdoored = dict(stable, trigger_patch_corner={"predicted_class": "Civilian_Vehicle", "confidence": 0.96})
        ArtifactStore.save_model_probes("M-BASE", stable)
        ArtifactStore.save_model_probes("M-04", backdoored)

        db.add_all([
            RuntimeBinding(runtime_id="R-01", case_id=cid, model_id="M-BASE", framework_version="ONNXRuntime-1.18",
                           hardware_target="CPU", quantization="FP32",
                           config_digest=CryptoService.hash({"rt": "ORT-1.18", "hw": "CPU", "q": "FP32"})),
            RuntimeBinding(runtime_id="R-02", case_id=cid, model_id="M-04", framework_version="ONNXRuntime-1.18",
                           hardware_target="EDGE_NPU", quantization="FP16",
                           config_digest=CryptoService.hash({"rt": "ORT-1.18", "hw": "NPU", "q": "FP16"})),
        ])
        db.commit()

        priv, pub = CryptoService.generate_keys()
        ArtifactStore.save_signer_key("edge-node-01", pub.hex())
        i001 = _signed_inference("I-001", cid, m_base, "R-01", 1, "NONCE-001-A792E", GENESIS_HASH, priv,
                                 {"class": "Main_Battle_Tank", "confidence": 0.96, "bbox": [120, 80, 450, 320]})
        i883 = _signed_inference("I-883", cid, m04, "R-02", 2, "NONCE-883-B994F", _sha("I-001"), priv,
                                 {"class": "Armoured_Vehicle", "confidence": 0.94, "bbox": [140, 90, 480, 340]},
                                 tamper_output=True)
        # Replay: a validly signed record re-submitted with I-001's nonce
        i884 = _signed_inference("I-884", cid, m04, "R-02", 3, "NONCE-001-A792E", _sha("I-883"), priv,
                                 {"class": "Logistics_Truck", "confidence": 0.88, "bbox": [60, 40, 300, 210]})
        db.add_all([i001, i883, i884])
        db.add_all([
            EvidenceEdge(edge_id="EDGE-D14-M04", case_id=cid, source_node="dataset:D-14", target_node="model:M-04",
                         relationship="trained_from", epistemic_status="DECLARED"),
            EvidenceEdge(edge_id="EDGE-D01-MBASE", case_id=cid, source_node="dataset:D-01", target_node="model:M-BASE",
                         relationship="trained_from", epistemic_status="DECLARED"),
        ])
        db.commit()
        return DemoService._run(db, cid)

    # ------------------------------------------------------------- case 2
    @staticmethod
    def _build_baseline_case(db: Session, force_reset: bool) -> Dict[str, Any]:
        cid = BASELINE_CASE_ID
        if DemoService._reset_or_skip(db, cid, force_reset):
            return {cid: {"idempotent": True}}
        DemoService._new_case(db, cid, "Reference detector release v2.0",
                              "Clean release from a certified lab. Every applicable check is expected to run and pass.")
        db.add(Contributor(contributor_id="C-02", case_id=cid, name="Optronics Vendor A (synthetic)",
                           contributor_type="VENDOR", metadata_json=json.dumps({"trust_tier": "TIER_2"})))
        db.commit()
        records = AttackFactory.create_clean_sample_battery(count=25, seed=202)
        digest = ArtifactStore.save_dataset_records("D-21", records, extras={
            **_embeddings(len(records), 21),
            "operational_metrics": {"brightness": 126.0, "contrast": 57.0, "blur_metric": 121.0, "noise_metric": 4.8},
        })
        db.add(Dataset(dataset_id="D-21", case_id=cid, contributor_id="C-02", name="Daylight validation split v2",
                       format="COCO", version="2.0.0", location="vault://assessment_inputs/datasets/D-21",
                       sha256=digest, manifest_hash=digest, sample_count=len(records), evidence_label="DEMO"))
        m = ModelAsset(model_id="M-21", case_id=cid, contributor_id="C-02", name="Reference detector v2.0",
                       framework="ONNX", format="ONNX", architecture="YOLOv8s", version="2.0.0",
                       weight_sha256=_sha("WEIGHTS_M-21_v2.0"), parameter_count=3012584, opset_version=17,
                       access_level="WHITE_BOX", evidence_label="DEMO")
        db.add(m)
        db.add(RuntimeBinding(runtime_id="R-21", case_id=cid, model_id="M-21", framework_version="ONNXRuntime-1.18",
                              hardware_target="CPU", quantization="FP32",
                              config_digest=CryptoService.hash({"rt": "ORT-1.18", "hw": "CPU"})))
        db.add(EvidenceEdge(edge_id="EDGE-D21-M21", case_id=cid, source_node="dataset:D-21", target_node="model:M-21",
                            relationship="trained_from", epistemic_status="DECLARED"))
        db.commit()
        ArtifactStore.save_supplied_digest("M-21", m.weight_sha256)
        ArtifactStore.save_model_probes("M-21", {
            "clean": {"predicted_class": "Logistics_Truck", "confidence": 0.93},
            "brightness_plus": {"predicted_class": "Logistics_Truck", "confidence": 0.90},
            "contrast_plus": {"predicted_class": "Logistics_Truck", "confidence": 0.91},
            "gaussian_blur": {"predicted_class": "Logistics_Truck", "confidence": 0.84},
            "trigger_patch_corner": {"predicted_class": "Logistics_Truck", "confidence": 0.89},
        })
        priv, pub = CryptoService.generate_keys()
        ArtifactStore.save_signer_key("edge-node-21", pub.hex())
        prev = GENESIS_HASH
        for seq in (1, 2):
            rec = _signed_inference(f"I-21{seq}", cid, m, "R-21", seq, f"NONCE-21{seq}-{seq * 7919:05d}", prev, priv,
                                    {"class": "Logistics_Truck", "confidence": 0.9, "bbox": [10 * seq, 20, 200, 150]},
                                    signer="edge-node-21")
            db.add(rec)
            prev = _sha(rec.inference_id)
        db.commit()
        return DemoService._run(db, cid)

    # ------------------------------------------------------------- case 3
    @staticmethod
    def _build_drift_case(db: Session, force_reset: bool) -> Dict[str, Any]:
        cid = DRIFT_CASE_ID
        if DemoService._reset_or_skip(db, cid, force_reset):
            return {cid: {"idempotent": True}}
        DemoService._new_case(db, cid, "Night-operations sensor batch",
                              "New thermal-assisted capture at night. Statistics shift; the question is whether "
                              "that is operational drift or manipulation.")
        db.add(Contributor(contributor_id="C-03", case_id=cid, name="Field Capture Unit (synthetic)",
                           contributor_type="FIELD_UNIT", metadata_json=json.dumps({"trust_tier": "TIER_2"})))
        db.commit()
        records = AttackFactory.create_clean_sample_battery(count=20, seed=303)
        digest = ArtifactStore.save_dataset_records("D-31", records, extras={
            **_embeddings(len(records), 31),
            "operational_metrics": {"brightness": 34.0, "contrast": 41.0, "blur_metric": 104.0, "noise_metric": 6.1},
            "operational_metadata": {"illumination": "NIGHT", "sensor": "EO/IR-2", "terrain": "PLAINS"},
        })
        db.add(Dataset(dataset_id="D-31", case_id=cid, contributor_id="C-03", name="Night capture batch N-04",
                       format="YOLO", version="1.0.0", location="vault://assessment_inputs/datasets/D-31",
                       sha256=digest, manifest_hash=digest, sample_count=len(records), evidence_label="DEMO"))
        db.commit()
        return DemoService._run(db, cid)

    # ------------------------------------------------------------- case 4 (Attack Lab sandbox)
    @staticmethod
    def _build_attack_lab_case(db: Session, force_reset: bool) -> Dict[str, Any]:
        cid = LAB_CASE_ID
        if DemoService._reset_or_skip(db, cid, force_reset):
            return {cid: {"idempotent": True}}
        DemoService._new_case(db, cid, "Attack Lab sandbox: perimeter detector v3",
                              "A clean, fully verifiable release used for live attack injection. Inject one attack "
                              "from the Attack Lab, run the pipeline, and see which stage catches it. Synthetic data.")
        db.add(Contributor(contributor_id="C-04", case_id=cid, name="Integrator B (synthetic)",
                           contributor_type="VENDOR", metadata_json=json.dumps({"trust_tier": "TIER_2"})))
        db.commit()
        from app.services.attack_lab_service import AttackLabService
        AttackLabService.write_clean_artifacts(db, create_rows=True)
        return DemoService._run(db, cid)
