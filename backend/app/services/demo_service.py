"""
DRISHTRA Deterministic Synthetic Demo Engine
Bootstraps Case: CASE-2026-DRISHTRA-DEMO
Executes complete vertical slice:
Contributor -> Dataset -> Model -> Inference -> Findings -> Evidence Graph -> Assurance Case -> Audit Ledger.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.db.models import Case, Contributor, Dataset, ModelAsset, InferenceRecord, EvidenceEdge, utc_now_iso
from app.schemas.all_schemas import CaseCreate, ContributorCreate, DatasetRegister, ModelRegister, InferenceRegister
from app.services.case_service import CaseService, ContributorService
from app.services.dataset_service import DatasetService
from app.services.model_service import ModelService
from app.services.inference_service import InferenceService
from app.services.assurance_service import AssuranceService
from app.services.audit_service import AuditService
from app.fixtures.attack_factory import AttackFactory
from app.crypto.signing import generate_keypair
from app.crypto.chain import GENESIS_HASH

class DemoService:
    @staticmethod
    def bootstrap_demo_case(db: Session) -> Dict[str, Any]:
        # Clean up existing demo case if any
        existing_case = db.query(Case).filter(Case.case_id == "CASE-2026-DRISHTRA-DEMO").first()
        if existing_case:
            db.delete(existing_case)
            db.commit()

        # 1. Create Sovereign Case
        case = Case(
            case_id="CASE-2026-DRISHTRA-DEMO",
            name="Operation Drishtra: Multi-Contributor CV Pipeline Assurance",
            description="Autonomous reconnaissance validation over Northern Sector sensor feeds and multi-vendor object detection models.",
            classification="RESTRICTED",
            status="ACTIVE",
            created_at=utc_now_iso(),
            updated_at=utc_now_iso()
        )
        db.add(case)
        db.commit()

        AuditService.record_event(
            db=db,
            case_id=case.case_id,
            actor="admin",
            action="DEMO_CASE_BOOTSTRAPPED",
            asset_id=case.case_id,
            result="SUCCESS",
            reason="Initialized deterministic SIH26228 evaluation scenario."
        )

        # 2. Register Contributors
        # C-01: Sovereign Defence Laboratory
        c1 = Contributor(
            contributor_id="C-01",
            case_id=case.case_id,
            name="Sovereign AI & Robotics Lab (CAIR / DRDO)",
            contributor_type="LAB",
            public_key="SOVEREIGN_ROOT_PUBKEY_ED25519",
            metadata_json='{"clearance": "CONFIDENTIAL", "trust_tier": "TIER_1"}',
            registered_at=utc_now_iso()
        )
        # C-02: Commercial Sensor Vendor
        c2 = Contributor(
            contributor_id="C-02",
            case_id=case.case_id,
            name="AeroDefense Optronics Consortium",
            contributor_type="VENDOR",
            public_key="VENDOR_OPTRONICS_PUBKEY",
            metadata_json='{"clearance": "RESTRICTED", "trust_tier": "TIER_2"}',
            registered_at=utc_now_iso()
        )
        # C-07: Untrusted Subcontractor (Attacker)
        c7 = Contributor(
            contributor_id="C-07",
            case_id=case.case_id,
            name="Apex Data Services (Subcontractor)",
            contributor_type="VENDOR",
            public_key="APEX_UNVERIFIED_PUBKEY",
            metadata_json='{"clearance": "UNCLASSIFIED", "trust_tier": "UNTRUSTED_TIER_3"}',
            registered_at=utc_now_iso()
        )
        db.add_all([c1, c2, c7])
        db.commit()

        # 3. Register Datasets
        # D-01: Clean Certified Base Split
        d1 = Dataset(
            dataset_id="D-01",
            case_id=case.case_id,
            contributor_id="C-01",
            name="UVH-26 Sovereign Armoured Recon Dataset (Clean)",
            format="COCO",
            version="1.0.0",
            location="/vault/data/clean_recon_v1.tar.gz",
            sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            manifest_hash="4a8a514d86b6222b4067b4fc8e5904bb6c9d072f87a3e7488df1762c94d3600b",
            sample_count=200,
            metadata_json='{"terrain": "MOUNTAINOUS_NORTH", "sensor": "FLIR_THERMAL"}',
            created_at=utc_now_iso()
        )
        # D-14: Attacked Dataset Contributed by C-07
        d14 = Dataset(
            dataset_id="D-14",
            case_id=case.case_id,
            contributor_id="C-07",
            name="Tactical Ground Recon Split B-221 (Mutated)",
            format="YOLO",
            version="2.1.0",
            location="/vault/data/batch_221_unverified.tar.gz",
            sha256="7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
            manifest_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            sample_count=180,
            metadata_json='{"batch": "B-221", "contributor": "C-07"}',
            created_at=utc_now_iso()
        )
        db.add_all([d1, d14])
        db.commit()

        # 4. Scan Datasets with Attack Factory Fixtures
        # Generate samples with duplicate flooding & label conflicts for D-14
        clean_samples = AttackFactory.create_clean_sample_battery(count=15, seed=101)
        poisoned_samples = AttackFactory.mutate_duplicate_flood(clean_samples, flood_count=3)
        poisoned_samples = AttackFactory.mutate_near_duplicate_flood(poisoned_samples, count=3)
        poisoned_samples = AttackFactory.mutate_label_poisoning(poisoned_samples)

        # Run scans
        DatasetService.scan_dataset(db, "D-01", clean_samples, actor="system_sentinel")
        DatasetService.scan_dataset(db, "D-14", poisoned_samples, actor="system_sentinel")

        # 5. Register Models
        # M-BASE: Certified Reference Model
        m_base = ModelAsset(
            model_id="M-BASE",
            case_id=case.case_id,
            contributor_id="C-01",
            name="Drishtra-TargetYOLOv8-Base-Ref",
            framework="PyTorch",
            format="ONNX",
            architecture="YOLOv8s",
            version="1.0.0",
            weight_sha256="111122223333444455556666777788889999aaaabbbbccccddddeeeeffff0000",
            reference_model_id=None,
            access_level="WHITE_BOX",
            created_at=utc_now_iso()
        )
        # M-04: Subcontracted Model (Modified / Backdoored)
        m04 = ModelAsset(
            model_id="M-04",
            case_id=case.case_id,
            contributor_id="C-07",
            name="Tactical-Target-Detector-M04",
            framework="PyTorch",
            format="ONNX",
            architecture="YOLOv8s",
            version="1.4.0",
            weight_sha256="9999888877776666555544443333222211110000ffeeddccbbaa998877665544",
            reference_model_id="M-BASE",
            access_level="BLACK_BOX",
            created_at=utc_now_iso()
        )
        db.add_all([m_base, m04])
        db.commit()

        # Scan Model M-04 with behavioral probe battery that triggers a Trojan finding
        probe_responses_m04 = {
            "clean": {"predicted_class": "Armoured_Vehicle", "confidence": 0.94},
            "brightness_plus": {"predicted_class": "Armoured_Vehicle", "confidence": 0.91},
            "contrast_plus": {"predicted_class": "Armoured_Vehicle", "confidence": 0.89},
            "gaussian_blur": {"predicted_class": "Armoured_Vehicle", "confidence": 0.85},
            # Backdoor Trigger: Corner patch induces immediate class flip to Civilian_Vehicle
            "trigger_patch_corner": {"predicted_class": "Civilian_Vehicle", "confidence": 0.96}
        }
        ModelService.scan_model(
            db=db,
            model_id="M-04",
            current_weight_sha256="9999888877776666555544443333222211110000ffeeddccbbaa998877665544",
            probe_responses=probe_responses_m04,
            actor="system_sentinel"
        )

        # 6. Generate Cryptographic Keypair for Sovereign Attestation
        priv_bytes, pub_bytes = generate_keypair()
        pub_hex = pub_bytes.hex()

        # Inferences:
        # I-001: Authentic Clean Inference
        inf1_data = AttackFactory.create_signed_inference_record(
            inference_id="I-001",
            case_id=case.case_id,
            model_id="M-BASE",
            sequence=1,
            nonce="NONCE-001-A792E",
            previous_record_hash=GENESIS_HASH,
            private_key_raw=priv_bytes,
            predictions={"class": "Main_Battle_Tank", "confidence": 0.96, "bbox": [120, 80, 450, 320]},
            is_tampered=False
        )
        inf1_rec = InferenceService.register_inference(db, InferenceRegister(**inf1_data), actor="tactical_edge_node")
        InferenceService.verify_inference(db, "I-001", pub_hex, actor="security_analyst")

        # I-883: Tampered Output & Signature Mismatch (Produced by M-04 from D-14)
        inf883_data = AttackFactory.create_signed_inference_record(
            inference_id="I-883",
            case_id=case.case_id,
            model_id="M-04",
            sequence=2,
            nonce="NONCE-883-B994F",
            previous_record_hash=inf1_rec.input_sha256,
            private_key_raw=priv_bytes,
            predictions={"class": "Armoured_Vehicle", "confidence": 0.942, "bbox": [140, 90, 480, 340]},
            is_tampered=True # Modifies output digest post-signing
        )
        InferenceService.register_inference(db, InferenceRegister(**inf883_data), actor="edge_drone_07")
        InferenceService.verify_inference(db, "I-883", pub_hex, actor="security_analyst")

        # 7. Establish Cross-Lifecycle Lineage Edges in Evidence Graph
        # C-07 -> D-14 (contributed_by)
        # D-14 -> M-04 (trained_from)
        # M-04 -> I-883 (produced)
        edges = [
            EvidenceEdge(edge_id="EDGE-C07-D14", case_id=case.case_id, source_node="contributor:C-07", target_node="dataset:D-14", relationship="contributed_by", epistemic_status="OBSERVED"),
            EvidenceEdge(edge_id="EDGE-D14-M04", case_id=case.case_id, source_node="dataset:D-14", target_node="model:M-04", relationship="trained_from", epistemic_status="DERIVED"),
            EvidenceEdge(edge_id="EDGE-M04-I883", case_id=case.case_id, source_node="model:M-04", target_node="inference:I-883", relationship="produced", epistemic_status="OBSERVED")
        ]
        db.add_all(edges)
        db.commit()

        # 8. Evaluate Case Assurance
        assurance = AssuranceService.assess_case(db, case.case_id, policy_version="DRISHTRA-AP-2026.1", actor="assurance_engine")

        return {
            "case_id": case.case_id,
            "status": case.status,
            "assurance_status": assurance.status,
            "recommended_disposition": assurance.recommended_disposition,
            "public_key_hex": pub_hex,
            "summary": "Deterministic end-to-end multi-contributor demo case successfully bootstrapped."
        }
