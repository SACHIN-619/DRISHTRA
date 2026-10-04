"""
Attack Lab (DEMO_MODE only).

A clean sandbox case (CASE-2026-ATTACK-LAB) whose *stored assessment inputs* can be
attacked from the console, one scenario at a time or layered together. Each attack
edits exactly what a real adversary would edit:

  poison_dataset    the training records in the vault      -> Stage 05 (D1/D3)
  swap_model        the model artifact as delivered        -> Stage 07 (D8A)
  backdoor_model    the model's behaviour under a trigger  -> Stage 08 (D8B)
  tamper_inference  a signed output, after signing         -> Stage 11 (D9A)
  replay_inference  an old signed record, re-submitted     -> Stage 11 (D9B)

Nothing here writes findings or verdicts. The pipeline has to find each attack on
its own from the stored artifacts; the Attack Lab only tells you where to look.
Every injection and reset is recorded in the case's hash-chained audit ledger.
"""
import hashlib
import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.crypto.chain import GENESIS_HASH
from app.crypto.crypto_service import CryptoService
from app.db.models import Dataset, EvidenceEdge, InferenceRecord, ModelAsset, RuntimeBinding
from app.fixtures.attack_factory import AttackFactory
from app.services.artifact_store import ArtifactStore, _path, _read_json, _write_json
from app.services.audit_service import AuditService

LAB_CASE_ID = "CASE-2026-ATTACK-LAB"
DATASET_ID, MODEL_ID, RUNTIME_ID, CONTRIBUTOR_ID = "D-41", "M-41", "R-41", "C-04"
SIGNER = "edge-node-41"

SCENARIOS: List[Dict[str, Any]] = [
    {"id": "poison_dataset", "layer": "DATA", "title": "Poison the training data",
     "attack": "Slip duplicated frames and a conflicting label into the vendor's training split.",
     "edits": f"vault records of {DATASET_ID}", "expected_stage": "STAGE_05_DATASET_INTEGRITY_SCAN",
     "expected_checks": ["D1_EXACT_DUPLICATE", "D3_LABEL_CONSISTENCY"]},
    {"id": "swap_model", "layer": "MODEL", "title": "Swap the model weights",
     "attack": "Deliver a rebuilt model file under the approved model's name and registration.",
     "edits": f"delivered artifact digest of {MODEL_ID}", "expected_stage": "STAGE_07_MODEL_INSPECTION",
     "expected_checks": ["D8A_WEIGHT_DIGEST"]},
    {"id": "backdoor_model", "layer": "MODEL", "title": "Plant a trigger backdoor",
     "attack": "Keep the weights' digest, but make a small corner patch flip the predicted class.",
     "edits": f"recorded probe responses of {MODEL_ID}", "expected_stage": "STAGE_08_MODEL_BEHAVIOURAL_EVALUATION",
     "expected_checks": ["D8B_BEHAVIOURAL_PROBE"]},
    {"id": "tamper_inference", "layer": "INFERENCE", "title": "Alter an output after signing",
     "attack": "Change the stored detection of a signed field record without re-signing it.",
     "edits": "stored output of I-412", "expected_stage": "STAGE_11_CRYPTOGRAPHIC_VERIFICATION",
     "expected_checks": ["D9A_SIGNATURE_BINDING"]},
    {"id": "replay_inference", "layer": "INFERENCE", "title": "Replay an old signed record",
     "attack": "Re-submit a validly signed record that reuses an earlier nonce.",
     "edits": "adds record I-413", "expected_stage": "STAGE_11_CRYPTOGRAPHIC_VERIFICATION",
     "expected_checks": ["D9B_REPLAY_SEQUENCE"]},
]
_BY_ID = {s["id"]: s for s in SCENARIOS}

_STABLE_PROBES = {
    "clean": {"predicted_class": "Air_Defence_Unit", "confidence": 0.92},
    "brightness_plus": {"predicted_class": "Air_Defence_Unit", "confidence": 0.90},
    "contrast_plus": {"predicted_class": "Air_Defence_Unit", "confidence": 0.89},
    "gaussian_blur": {"predicted_class": "Air_Defence_Unit", "confidence": 0.85},
    "trigger_patch_corner": {"predicted_class": "Air_Defence_Unit", "confidence": 0.90},
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _clean_records() -> List[Dict[str, Any]]:
    return AttackFactory.create_clean_sample_battery(count=24, seed=404)


def _extras() -> Dict[str, Any]:
    from app.services.demo_service import _embeddings
    return {**_embeddings(24, 41),
            "operational_metrics": {"brightness": 128.0, "contrast": 56.0, "blur_metric": 119.0, "noise_metric": 5.0}}


class AttackLabError(Exception):
    pass


class AttackLabService:
    # ---------------------------------------------------------------- state
    @staticmethod
    def _state() -> Dict[str, Any]:
        data, _ = _read_json(_path("attack_lab", "state", "json"))
        return data or {"active": [], "originals": {}}

    @staticmethod
    def _save_state(state: Dict[str, Any]) -> None:
        _write_json(_path("attack_lab", "state", "json"), state)

    @staticmethod
    def _signing_key() -> bytes:
        """Simulated edge device key for the sandbox (synthetic, DEMO only)."""
        data, _ = _read_json(_path("attack_lab", "edge-node-41-device", "json"))
        if data and data.get("private_hex"):
            return bytes.fromhex(data["private_hex"])
        priv, pub = CryptoService.generate_keys()
        _write_json(_path("attack_lab", "edge-node-41-device", "json"),
                    {"note": "Simulated edge-device signing key for the DEMO Attack Lab sandbox only.",
                     "private_hex": priv.hex()})
        ArtifactStore.save_signer_key(SIGNER, pub.hex())
        return priv

    # ---------------------------------------------------------------- clean baseline
    @staticmethod
    def write_clean_artifacts(db: Session, create_rows: bool = False) -> None:
        from app.services.demo_service import _signed_inference
        records = _clean_records()
        digest = ArtifactStore.save_dataset_records(DATASET_ID, records, extras=_extras())
        weight = _sha("WEIGHTS_M-41_v3.0")
        if create_rows:
            db.add(Dataset(dataset_id=DATASET_ID, case_id=LAB_CASE_ID, contributor_id=CONTRIBUTOR_ID,
                           name="Perimeter training split v3", format="COCO", version="3.0.0",
                           location=f"vault://assessment_inputs/datasets/{DATASET_ID}", sha256=digest,
                           manifest_hash=digest, sample_count=len(records), evidence_label="DEMO"))
            db.add(ModelAsset(model_id=MODEL_ID, case_id=LAB_CASE_ID, contributor_id=CONTRIBUTOR_ID,
                              name="Perimeter detector v3.0", framework="ONNX", format="ONNX", architecture="YOLOv8s",
                              version="3.0.0", weight_sha256=weight, parameter_count=3012584, opset_version=17,
                              access_level="WHITE_BOX", evidence_label="DEMO"))
            db.add(RuntimeBinding(runtime_id=RUNTIME_ID, case_id=LAB_CASE_ID, model_id=MODEL_ID,
                                  framework_version="ONNXRuntime-1.18", hardware_target="EDGE_NPU", quantization="FP16",
                                  config_digest=CryptoService.hash({"rt": "ORT-1.18", "hw": "NPU", "q": "FP16"})))
            db.add(EvidenceEdge(edge_id="EDGE-D41-M41", case_id=LAB_CASE_ID, source_node=f"dataset:{DATASET_ID}",
                                target_node=f"model:{MODEL_ID}", relationship="trained_from", epistemic_status="DECLARED"))
            db.commit()
        else:
            ds = db.query(Dataset).filter_by(dataset_id=DATASET_ID).first()
            if ds:
                ds.sha256 = ds.manifest_hash = digest
                ds.sample_count = len(records)
        ArtifactStore.save_supplied_digest(MODEL_ID, weight)
        ArtifactStore.save_model_probes(MODEL_ID, _STABLE_PROBES)

        # field inference records, signed by the simulated edge device
        priv = AttackLabService._signing_key()
        for rec in db.query(InferenceRecord).filter_by(case_id=LAB_CASE_ID).all():
            db.delete(rec)
        db.commit()
        model = db.query(ModelAsset).filter_by(model_id=MODEL_ID).first()
        prev = GENESIS_HASH
        for seq in (1, 2):
            rec = _signed_inference(f"I-41{seq}", LAB_CASE_ID, model, RUNTIME_ID, seq, f"NONCE-41{seq}-{seq * 6007:05d}",
                                    prev, priv, {"class": "Air_Defence_Unit", "confidence": 0.91, "bbox": [30 * seq, 40, 260, 190]},
                                    signer=SIGNER)
            db.add(rec)
            prev = _sha(rec.inference_id)
        db.commit()

    # ---------------------------------------------------------------- API
    @staticmethod
    def describe() -> Dict[str, Any]:
        active = set(AttackLabService._state()["active"])
        return {"case_id": LAB_CASE_ID,
                "scenarios": [{**s, "active": s["id"] in active} for s in SCENARIOS],
                "active": sorted(active)}

    @staticmethod
    def inject(db: Session, scenario: str, actor: str) -> Dict[str, Any]:
        from app.services.demo_service import _signed_inference
        if scenario not in _BY_ID:
            raise AttackLabError(f"Unknown scenario '{scenario}'.")
        state = AttackLabService._state()
        if scenario in state["active"]:
            return AttackLabService.describe()

        if scenario == "poison_dataset":
            payload, _ = ArtifactStore.load_dataset_records(DATASET_ID)
            recs = payload["records"]
            recs = AttackFactory.mutate_duplicate_flood(recs, flood_count=4)
            recs = AttackFactory.mutate_label_poisoning(recs)
            ArtifactStore.save_dataset_records(DATASET_ID, recs, payload.get("extras"))
        elif scenario == "swap_model":
            ArtifactStore.save_supplied_digest(MODEL_ID, _sha("WEIGHTS_M-41_UNAPPROVED_REBUILD"),
                                               source="delivered artifact (Attack Lab: substituted file)")
        elif scenario == "backdoor_model":
            probes = dict(_STABLE_PROBES, trigger_patch_corner={"predicted_class": "Civilian_Vehicle", "confidence": 0.97})
            ArtifactStore.save_model_probes(MODEL_ID, probes)
        elif scenario == "tamper_inference":
            rec = db.query(InferenceRecord).filter_by(inference_id="I-412").first()
            if not rec:
                raise AttackLabError("Record I-412 is missing; reset the sandbox first.")
            rec.output_sha256 = _sha("ALTERED_DETECTION_I-412")
            rec.predictions_json = json.dumps({"class": "Civilian_Vehicle", "confidence": 0.91, "bbox": [60, 40, 260, 190]})
            db.commit()
        elif scenario == "replay_inference":
            if not db.query(InferenceRecord).filter_by(inference_id="I-413").first():
                model = db.query(ModelAsset).filter_by(model_id=MODEL_ID).first()
                rec = _signed_inference("I-413", LAB_CASE_ID, model, RUNTIME_ID, 3, "NONCE-411-06007", _sha("I-412"),
                                        AttackLabService._signing_key(),
                                        {"class": "Air_Defence_Unit", "confidence": 0.91, "bbox": [30, 40, 260, 190]},
                                        signer=SIGNER)
                db.add(rec)
                db.commit()

        state["active"] = sorted(set(state["active"]) | {scenario})
        AttackLabService._save_state(state)
        s = _BY_ID[scenario]
        AuditService.record_event(db=db, case_id=LAB_CASE_ID, actor=actor, action="ATTACK_LAB_INJECTED",
                                  asset_id=LAB_CASE_ID, result="SUCCESS",
                                  reason=f"{s['title']} ({s['edits']}). Synthetic attack injected for demonstration.")
        return AttackLabService.describe()

    @staticmethod
    def reset(db: Session, actor: str) -> Dict[str, Any]:
        AttackLabService.write_clean_artifacts(db, create_rows=False)
        AttackLabService._save_state({"active": [], "originals": {}})
        AuditService.record_event(db=db, case_id=LAB_CASE_ID, actor=actor, action="ATTACK_LAB_RESET",
                                  asset_id=LAB_CASE_ID, result="SUCCESS",
                                  reason="Sandbox artifacts restored to the clean, signed baseline.")
        return AttackLabService.describe()
