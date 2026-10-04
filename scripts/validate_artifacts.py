"""
DRISHTRA Verifiable Artifact Validation Script
Validates the integrity, schema compliance, and cryptographic checksums of all 9 discrete exported artifacts:
1. dataset_manifest.json
2. dataset_findings.json
3. model_passport.json
4. inference_attestation.json
5. verification_result.json
6. evidence_graph.json
7. assurance_case.json
8. assurance_report.json
9. audit_chain.json
"""
import os
import sys
import json
import hashlib

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.db.database import SessionLocal, engine
from app.db.migrations import run_migrations
from app.services.demo_service import DemoService
from app.services.artifact_export_service import ArtifactExportService

REQUIRED_ARTIFACTS = [
    "dataset_manifest.json",
    "dataset_findings.json",
    "model_passport.json",
    "inference_attestation.json",
    "verification_result.json",
    "evidence_graph.json",
    "assurance_case.json",
    "assurance_report.json",
    "audit_chain.json"
]

def validate_artifacts_dir(target_dir: str) -> bool:
    print(f"\n[+] Validating Discrete Artifact Bundle in '{target_dir}'...")
    if not os.path.exists(target_dir):
        print(f"[!] Error: Target directory '{target_dir}' does not exist.")
        return False

    all_valid = True
    for artifact_name in REQUIRED_ARTIFACTS:
        file_path = os.path.join(target_dir, artifact_name)
        if not os.path.exists(file_path):
            print(f"  [FAIL] Missing required artifact: {artifact_name}")
            all_valid = False
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                wrapped = json.load(f)

            header = wrapped.get("header", {})
            data = wrapped.get("data")

            if not header or data is None:
                print(f"  [FAIL] {artifact_name}: Missing header or data payload.")
                all_valid = False
                continue

            # Verify header fields
            req_header_keys = ["schema_version", "created_at", "case_id", "sha256"]
            missing_keys = [k for k in req_header_keys if k not in header]
            if missing_keys:
                print(f"  [FAIL] {artifact_name}: Header missing fields: {missing_keys}")
                all_valid = False
                continue

            # Verify cryptographic SHA-256 hash of payload
            raw_json_str = json.dumps(data, sort_keys=True)
            calc_hash = hashlib.sha256(raw_json_str.encode()).hexdigest()

            if calc_hash != header["sha256"]:
                print(f"  [FAIL] {artifact_name}: Cryptographic checksum mismatch!")
                print(f"         Header sha256:     {header['sha256']}")
                print(f"         Calculated sha256: {calc_hash}")
                all_valid = False
                continue

            print(f"  [OK] {artifact_name} (Verifiable SHA256: {calc_hash[:16]}...)")

        except Exception as e:
            print(f"  [FAIL] {artifact_name}: Parsing or verification exception: {e}")
            all_valid = False

    return all_valid

def main():
    print("======================================================================")
    print("  DRISHTRA Verifiable Discrete Artifact Integrity Validator")
    print("======================================================================")

    run_migrations(engine)
    db = SessionLocal()
    try:
        DemoService.bootstrap_demo_case(db)
        bundle_info = ArtifactExportService.export_case_bundle(db=db, case_id="CASE-2026-DRISHTRA-DEMO")
        target_dir = os.path.dirname(list(bundle_info["artifact_paths"].values())[0])
    finally:
        db.close()

    success = validate_artifacts_dir(target_dir)

    print("======================================================================")
    if success:
        print("  ALL 9 DISCRETE ARTIFACTS VERIFIED: Cryptographically Compliant & Valid!")
        print("======================================================================")
        sys.exit(0)
    else:
        print("  ARTIFACT VALIDATION FAILED: Integrity Violations Detected!")
        print("======================================================================")
        sys.exit(1)

if __name__ == "__main__":
    main()
