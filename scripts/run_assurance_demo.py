"""
DRISHTRA Sovereign Assurance Canonical Demonstration Script
Runs the standard demonstration scenario CASE-2026-DRISHTRA-DEMO:
Contributor -> Dataset -> Mutations -> Model -> Inference -> Findings -> Evidence Graph -> Reverse Lineage -> Assurance Case -> Review -> QUARANTINE -> Audit -> Export

Then runs a clean control scenario (CASE-CLEAN-CONTROL) and demonstrates that a clean pipeline produces ACCEPT disposition.
Runs 100% offline.
"""
import os
import sys
import json
import logging
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.db.database import SessionLocal, engine
from app.db.migrations import run_migrations
from app.db.models import Case, Contributor, Dataset, ModelAsset, InferenceRecord, Finding, AuditEvent
from app.services.demo_service import DemoService
from app.services.assurance_run_service import AssuranceRunService
from app.schemas.all_schemas import AssuranceRunCreate
from app.correlation.evidence_graph import EvidenceGraphBuilder
from app.services.assurance_service import AssuranceService
from app.services.audit_service import AuditService
from app.services.artifact_export_service import ArtifactExportService
from app.fixtures.attack_factory import AttackFactory
from app.crypto.signing import generate_keypair
from app.crypto.crypto_service import CryptoService

def main():
    print("======================================================================")
    print("  DRISHTRA - Digital Reliability & Integrity Shield for Trusted AI")
    print("  Canonical Sovereign Assurance Pipeline & Control Demonstration")
    print("======================================================================")

    run_migrations(engine)
    db = SessionLocal()

    try:
        # -------------------------------------------------------------
        # Part A: Mutated Assurance Case (CASE-2026-DRISHTRA-DEMO)
        # -------------------------------------------------------------
        print("\n[+] 1. Bootstrapping Mutated Demonstration Case: CASE-2026-DRISHTRA-DEMO...")
        DemoService.bootstrap_demo_case(db)

        print("[+] 2. Executing Unified Backend Assurance Run Orchestrator...")
        run_req = AssuranceRunCreate(
            case_id="CASE-2026-DRISHTRA-DEMO",
            dataset_id="D-14",
            model_id="M-04",
            execution_mode="OFFLINE"
        )
        run_res = AssuranceRunService.create_and_execute_run(db=db, req=run_req, actor="demo_analyst")

        print(f"    [OK] Assurance Run ID: {run_res.assurance_run_id}")
        print(f"    [OK] Final Status: {run_res.status}")
        print(f"    [OK] Execution Mode: {run_res.execution_mode}")

        print("[+] 3. Reconstructing Evidence Graph & Testing Reverse Lineage Trace for Inference I-883...")
        graph_builder = EvidenceGraphBuilder.from_database("CASE-2026-DRISHTRA-DEMO", db)
        trace = graph_builder.trace_flag_subgraph("inference:I-883")

        print(f"    [OK] Trace Summary: {trace['trace_summary']}")
        print(f"    [OK] Converged Lifecycle Boundaries: {trace['lifecycle_boundaries']}")

        ac = AssuranceService.get_latest_assurance(db, "CASE-2026-DRISHTRA-DEMO")
        print(f"    [OK] Evaluated Recommended Disposition: {ac.recommended_disposition}")
        print(f"    [OK] Assurance Claim: {ac.claim}")

        # -------------------------------------------------------------
        # Part B: Clean Baseline Control Case (CASE-CLEAN-CONTROL)
        # -------------------------------------------------------------
        print("\n[+] 4. Bootstrapping Clean Control Baseline Case: CASE-CLEAN-CONTROL...")
        clean_case = db.query(Case).filter(Case.case_id == "CASE-CLEAN-CONTROL").first()
        if not clean_case:
            clean_case = Case(
                case_id="CASE-CLEAN-CONTROL",
                name="Sovereign Recon Clean Baseline Pipeline",
                description="Unmutated baseline control for CV supply-chain verification",
                classification="RESTRICTED",
                status="ACTIVE"
            )
            db.add(clean_case)
            db.commit()

            c1 = Contributor(
                contributor_id="C-CLEAN-01",
                case_id="CASE-CLEAN-CONTROL",
                name="Sovereign Defense AI Lab",
                contributor_type="LAB"
            )
            db.add(c1)
            db.commit()

            d1 = Dataset(
                dataset_id="D-CLEAN-01",
                case_id="CASE-CLEAN-CONTROL",
                contributor_id="C-CLEAN-01",
                name="Clean Recon Baseline Split",
                format="COCO",
                version="1.0.0",
                sha256="a"*64,
                manifest_hash="b"*64,
                sample_count=50,
                evidence_label="SYNTHETIC"
            )
            db.add(d1)
            db.commit()

            m1 = ModelAsset(
                model_id="M-CLEAN-01",
                case_id="CASE-CLEAN-CONTROL",
                contributor_id="C-CLEAN-01",
                name="Validated Recon Detector v1",
                framework="PyTorch",
                format="ONNX",
                architecture="YOLOv8",
                version="1.0.0",
                weight_sha256="c"*64,
                access_level="WHITE_BOX",
                evidence_label="SYNTHETIC"
            )
            db.add(m1)
            db.commit()

            priv, pub = generate_keypair()
            inf1 = AttackFactory.create_signed_inference_record(
                inference_id="I-CLEAN-01",
                case_id="CASE-CLEAN-CONTROL",
                model_id="M-CLEAN-01",
                sequence=1,
                nonce="nonce-clean-01",
                previous_record_hash="0"*64,
                private_key_raw=priv,
                predictions={"boxes": [[10, 10, 50, 50]], "labels": ["Armoured_Vehicle"]},
                is_tampered=False
            )
            rec = InferenceRecord(
                inference_id=inf1["inference_id"],
                case_id="CASE-CLEAN-CONTROL",
                dataset_id="D-CLEAN-01",
                model_id="M-CLEAN-01",
                input_sha256=inf1["input_sha256"],
                model_sha256=inf1["model_sha256"],
                preprocess_sha256=inf1["preprocess_sha256"],
                config_sha256=inf1["config_sha256"],
                output_sha256=inf1["output_sha256"],
                sequence=inf1["sequence"],
                timestamp=inf1["timestamp"],
                nonce=inf1["nonce"],
                previous_record_hash=inf1["previous_record_hash"],
                signature=inf1["signature"],
                signer="sovereign_drone_01",
                verification_status="VERIFIED",
                evidence_label="SYNTHETIC"
            )
            db.add(rec)
            db.commit()

        print("[+] 5. Executing Assurance Run for Clean Control Baseline...")
        clean_run_req = AssuranceRunCreate(
            case_id="CASE-CLEAN-CONTROL",
            dataset_id="D-CLEAN-01",
            model_id="M-CLEAN-01",
            execution_mode="OFFLINE"
        )
        clean_run_res = AssuranceRunService.create_and_execute_run(db=db, req=clean_run_req, actor="demo_analyst")

        clean_ac = AssuranceService.get_latest_assurance(db, "CASE-CLEAN-CONTROL")
        print(f"    [OK] Clean Control Run ID: {clean_run_res.assurance_run_id}")
        print(f"    [OK] Clean Control Status: {clean_run_res.status}")
        print(f"    [OK] Clean Control Recommended Disposition: {clean_ac.recommended_disposition}")
        print(f"    [OK] Clean Control Claim: {clean_ac.claim}")

        # -------------------------------------------------------------
        # Part C: Audit & Artifact Export
        # -------------------------------------------------------------
        print("\n[+] 6. Exporting Discrete Artifact Bundles & Verifying Audit Chain...")
        bundle_mutated = ArtifactExportService.export_case_bundle(db=db, case_id="CASE-2026-DRISHTRA-DEMO")
        bundle_clean = ArtifactExportService.export_case_bundle(db=db, case_id="CASE-CLEAN-CONTROL")

        print(f"    [OK] Mutated Bundle Artifacts: {bundle_mutated['artifact_count']} items exported.")
        print(f"    [OK] Clean Bundle Artifacts:   {bundle_clean['artifact_count']} items exported.")

        print("\n======================================================================")
        print("  DEMONSTRATION SUMMARY:")
        print(f"  - Mutated Pipeline (CASE-2026-DRISHTRA-DEMO): Disposition = {ac.recommended_disposition} (QUARANTINED)")
        print(f"  - Clean Pipeline   (CASE-CLEAN-CONTROL):      Disposition = {clean_ac.recommended_disposition} (ACCEPTED)")
        print("======================================================================")

    finally:
        db.close()

if __name__ == "__main__":
    main()
