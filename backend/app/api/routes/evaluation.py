"""
DRISHTRA Evaluation & Attack Lab API Routes
Exposes empirical benchmarking, ground truth vs observation evaluation,
confusion matrix (TP/FP/FN/TN), and discrete stage artifact retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.evaluation.attack_lab import DemoAttackLab
from app.services.artifact_export_service import ArtifactExportService

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Attack Lab"])

@router.post("/attack-lab/run")
def run_attack_lab_benchmark():
    """
    Executes the controlled Demo Attack Lab benchmark.
    Compares injected Ground Truth against DRISHTRA observations
    and calculates TP / FP / FN / TN, Precision, Recall, and F1-score.
    """
    results = DemoAttackLab.run_benchmark()
    return results

@router.get("/artifacts/{case_id}")
def export_stage_artifacts(case_id: str, db: Session = Depends(get_db)):
    """
    Exports and returns the paths for all 9 discrete, verifiable stage artifacts:
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
    try:
        paths = ArtifactExportService.export_all_stage_artifacts(db, case_id)
        return {
            "case_id": case_id,
            "status": "EXPORTED",
            "message": "All 9 pipeline stage artifacts exported successfully.",
            "artifacts": paths
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
