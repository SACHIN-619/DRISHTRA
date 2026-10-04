"""
Golden demo, end to end, against a fresh isolated database - and a proof report.

Walks the whole product story through the real HTTP API with five real accounts:

  1. ML analyst runs the 18-stage pipeline on the C-07 case (stored artifacts only)
  2. Security analyst opens "why?", traces lineage, recommends QUARANTINE
  3. Reviewer is blocked from nothing it should do, decides QUARANTINE (signed)
  4. Admin is refused the decision; ML analyst is refused the decision
  5. Auditor recomputes every chain (case, decision, platform)
  6. Mutation propagation: tamper one delivered model digest on the clean case,
     re-run, verdict flips; restore, verdict returns
  7. Tamper detection: edit a stored decision; verification fails

Writes storage/artifacts/golden_demo_proof.json and exits non-zero on any failure.

    python scripts/golden_demo.py
"""
import json
import os
import sys
import tempfile
import time

TMP = tempfile.mkdtemp(prefix="drishtra_golden_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TMP, 'golden.db')}"
os.environ["BASE_STORAGE_DIR"] = os.path.join(TMP, "storage")
os.environ["DEMO_MODE"] = "true"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PW = "Drishtra@2026"
CASE = "CASE-2026-DRISHTRA-DEMO"
CLEAN = "CASE-2026-BASELINE-001"
steps = []


def step(name, ok, detail=None):
    steps.append({"step": name, "ok": bool(ok), "detail": detail})
    print(("  PASS " if ok else "  FAIL ") + name + (f"  -> {detail}" if detail and not ok else ""))
    return ok


def main():
    with TestClient(app) as c:  # runs startup: migrations, accounts, demo cases
        def login(u):
            r = c.post("/api/v1/auth/token", json={"username": u, "password": PW})
            return {"Authorization": f"Bearer {r.json()['access_token']}"}
        ml, sec, rev, aud, adm = (login(u) for u in ("ml.analyst", "sec.analyst", "reviewer", "auditor", "admin"))

        print("1. Pipeline")
        run = c.post(f"/api/v1/cases/{CASE}/pipeline/run", headers=ml).json()
        st = {s["stage_id"]: s for s in run["stages"]}
        step("18 stages completed", run["status"] == "COMPLETED" and len(run["stages"]) == 18, run["status"])
        step("stage 05 consumed stage 04 output",
             st["STAGE_05_DATASET_INTEGRITY_SCAN"]["input_summary"]["canonical_sets"] ==
             st["STAGE_04_DATASET_NORMALIZATION"]["output_summary"]["canonical_sets"])

        print("2. Investigation")
        ac = c.get(f"/api/v1/assurance/{CASE}", headers=sec).json()
        step("quarantine recommended", ac["recommended_disposition"] == "QUARANTINE", ac["status"])
        step("convergence on C-07", ac["convergence"]["contributors"][0]["contributor_id"] == "C-07")
        sig = next(e for e in ac["evidence"] if e["type"] == "CRYPTOGRAPHIC_SIGNATURE_INVALID")
        why = c.get(f"/api/v1/findings/{sig['finding_id']}/why-flagged", headers=sec).json()
        step("why? traces inference -> runtime -> model -> dataset -> contributor",
             [l["layer"] for l in why["lineage"]] == ["INFERENCE", "RUNTIME", "MODEL", "DATASET", "CONTRIBUTOR"],
             [l["layer"] for l in why["lineage"]])
        step("counter-evidence never contradicts a finding",
             not any(x["check_id"] == "D9A_SIGNATURE_BINDING" and x["asset_id"] == "I-883" for x in ac["counter_evidence"]))
        r = c.post(f"/api/v1/assurance/{CASE}/recommend", headers=sec,
                   json={"disposition": "QUARANTINE", "rationale": "Three evidence paths converge on C-07."})
        step("analyst recommendation recorded", r.status_code == 200, r.text[:200])

        print("3-4. Decision & separation of duties")
        for who, h in (("admin", adm), ("ml.analyst", ml), ("sec.analyst", sec)):
            r = c.post(f"/api/v1/assurance/{CASE}/decide", headers=h,
                       json={"disposition": "ACCEPT", "rationale": "attempt outside my authority"})
            step(f"{who} cannot decide", r.status_code == 403, r.status_code)
        r = c.post(f"/api/v1/assurance/{CASE}/decide", headers=rev,
                   json={"disposition": "QUARANTINE", "rationale": "Converging evidence; block downstream use."})
        step("reviewer decision signed", r.status_code == 200 and r.json()["decision"]["signature"], r.text[:200])
        step("case quarantined", c.get(f"/api/v1/cases/{CASE}", headers=aud).json()["status"] == "QUARANTINED")

        print("5. Audit")
        step("case ledger valid", c.post(f"/api/v1/audit/{CASE}/verify", headers=aud).json()["status"] == "VALID")
        step("decision chain valid", c.post(f"/api/v1/assurance/{CASE}/decisions/verify", headers=aud).json()["status"] == "VALID")
        step("platform ledger valid", c.post("/api/v1/platform/events/verify", headers=aud).json()["status"] == "VALID")

        print("6. Mutation propagation")
        from app.services.artifact_store import ArtifactStore
        from app.db.database import SessionLocal
        from app.db.models import ModelAsset, AssuranceDecision
        before = c.get(f"/api/v1/assurance/{CLEAN}", headers=sec).json()["recommended_disposition"]
        db = SessionLocal()
        original = db.query(ModelAsset).filter_by(model_id="M-21").first().weight_sha256
        ArtifactStore.save_supplied_digest("M-21", "f" * 64, source="golden demo tamper")
        c.post(f"/api/v1/cases/{CLEAN}/pipeline/run", headers=ml)
        after = c.get(f"/api/v1/assurance/{CLEAN}", headers=sec).json()
        step("clean case ACCEPT before tamper", before == "ACCEPT", before)
        step("tampered model digest flips the verdict", after["recommended_disposition"] != "ACCEPT"
             and any(e["type"] == "MODEL_DIGEST_MISMATCH" for e in after["evidence"]), after["recommended_disposition"])
        ArtifactStore.save_supplied_digest("M-21", original)
        c.post(f"/api/v1/cases/{CLEAN}/pipeline/run", headers=ml)
        step("restoring the artifact restores ACCEPT",
             c.get(f"/api/v1/assurance/{CLEAN}", headers=sec).json()["recommended_disposition"] == "ACCEPT")

        print("7. Tamper detection")
        d = db.query(AssuranceDecision).filter_by(case_id=CASE, kind="DISPOSITION").first()
        d.rationale = "edited after the fact"
        db.commit()
        step("edited decision is detected", c.post(f"/api/v1/assurance/{CASE}/decisions/verify", headers=aud).json()["status"] == "BROKEN")
        db.close()

    ok = all(s["ok"] for s in steps)
    report = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "passed": ok,
              "steps": steps, "pipeline_run": run["run_id"], "note": "Synthetic demonstration data; isolated temporary database."}
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "artifacts"))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "golden_demo_proof.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"\n{'ALL STEPS PASSED' if ok else 'FAILURES PRESENT'}  ({sum(s['ok'] for s in steps)}/{len(steps)})  -> storage/artifacts/golden_demo_proof.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
