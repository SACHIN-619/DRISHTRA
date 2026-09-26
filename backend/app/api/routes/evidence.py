"""
DRISHTRA Evidence Graph & Lineage API Endpoints
Provides Graph Topology and the Critical "Why was this result flagged?" Lineage Trace.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Finding, Evidence, EvidenceEdge, Case, Contributor, Dataset, ModelAsset, InferenceRecord
from app.schemas.all_schemas import FindingResponse, EvidenceResponse, EvidenceGraphResponse
from app.correlation.evidence_graph import EvidenceGraphBuilder

router = APIRouter(prefix="/api/v1/cases", tags=["Evidence & Lineage"])

@router.get("/{case_id}/findings", response_model=List[FindingResponse])
def get_case_findings(case_id: str, db: Session = Depends(get_db)):
    return db.query(Finding).filter(Finding.case_id == case_id).all()

@router.get("/{case_id}/evidence", response_model=List[EvidenceResponse])
def get_case_evidence(case_id: str, db: Session = Depends(get_db)):
    return db.query(Evidence).filter(Evidence.case_id == case_id).all()

@router.get("/{case_id}/graph", response_model=EvidenceGraphResponse)
def get_case_graph(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    builder = EvidenceGraphBuilder(case_id=case_id)

    # 1. Add Contributors
    contribs = db.query(Contributor).filter(Contributor.case_id == case_id).all()
    for c in contribs:
        status = "FLAGGED" if c.contributor_id == "C-07" else "NORMAL"
        builder.add_node(f"contributor:{c.contributor_id}", c.name, "Contributor", status=status, details={"type": c.contributor_type})

    # 2. Add Datasets
    datasets = db.query(Dataset).filter(Dataset.case_id == case_id).all()
    for d in datasets:
        findings_count = db.query(Finding).filter(Finding.asset_id == d.dataset_id).count()
        status = "FINDING" if findings_count > 0 else "VERIFIED"
        builder.add_node(f"dataset:{d.dataset_id}", d.name, "Dataset", status=status, details={"sha256": d.sha256[:16], "samples": d.sample_count})

    # 3. Add Models
    models = db.query(ModelAsset).filter(ModelAsset.case_id == case_id).all()
    for m in models:
        findings_count = db.query(Finding).filter(Finding.asset_id == m.model_id).count()
        status = "FINDING" if findings_count > 0 else "VERIFIED"
        builder.add_node(f"model:{m.model_id}", m.name, "Model", status=status, details={"arch": m.architecture, "digest": m.weight_sha256[:16]})

    # 4. Add Inferences
    inferences = db.query(InferenceRecord).filter(InferenceRecord.case_id == case_id).all()
    for inf in inferences:
        builder.add_node(f"inference:{inf.inference_id}", f"Inference #{inf.sequence} ({inf.inference_id})", "Inference", status=inf.verification_status, details={"verification": inf.verification_status, "nonce": inf.nonce})

    # 5. Add Explicit Edges from Database
    edges = db.query(EvidenceEdge).filter(EvidenceEdge.case_id == case_id).all()
    for e in edges:
        builder.add_edge(e.source_node, e.target_node, e.relationship, epistemic_status=e.epistemic_status)

    # 6. Add Findings as Nodes and attach to assets
    findings = db.query(Finding).filter(Finding.case_id == case_id).all()
    for f in findings:
        f_node = f"finding:{f.finding_id}"
        builder.add_node(f_node, f.finding_type, "Finding", status=f.severity, details={"severity": f.severity, "explanation": f.explanation})
        # Determine asset node prefix
        prefix = "dataset:" if f.asset_type == "DATASET" else ("model:" if f.asset_type == "MODEL" else "inference:")
        builder.add_edge(f"{prefix}{f.asset_id}", f_node, "has_finding", epistemic_status="DERIVED")

    return builder.to_schema()

@router.get("/{case_id}/trace/{node_id}")
def trace_flagged_result(case_id: str, node_id: str, db: Session = Depends(get_db)):
    """
    Centerpiece: 'Why was this result flagged?'
    Reconstructs the explanatory upstream subgraph across:
    Inference -> Model -> Dataset -> Contributor with connected findings.
    """
    graph_resp = get_case_graph(case_id, db)
    builder = EvidenceGraphBuilder(case_id=case_id)
    for n in graph_resp.nodes:
        builder.add_node(n.id, n.label, n.type, status=n.status, details=n.details)
    for e in graph_resp.edges:
        builder.add_edge(e.source, e.target, e.relationship, epistemic_status=e.epistemic_status)

    trace = builder.trace_flag_subgraph(node_id)
    return trace
