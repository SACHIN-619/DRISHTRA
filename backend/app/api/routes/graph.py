"""
DRISHTRA Cross-Lifecycle Evidence Graph & Reverse Lineage API Endpoints
Provides:
- Graph Topology (Contributor -> Dataset -> Model -> Runtime -> Inference)
- "Why was this result flagged?" Reverse Lineage Trace
- Cross-Lifecycle Multi-Path Convergence Analysis
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Case, Contributor, Dataset, ModelAsset, RuntimeBinding, InferenceRecord, Finding, EvidenceEdge
from app.schemas.all_schemas import EvidenceGraphResponse
from app.correlation.evidence_graph import EvidenceGraphBuilder

from app.core.security import require_permission, TokenData
from app.core.rbac import Permission

router = APIRouter(prefix="/api/v1/graph", tags=["Cross-Lifecycle Evidence Graph"], dependencies=[Depends(require_permission(Permission.EVIDENCE_READ))])

def _build_graph_for_case(case_id: str, db: Session) -> EvidenceGraphBuilder:
    return EvidenceGraphBuilder.from_database(case_id, db)

@router.get("/{case_id}", response_model=EvidenceGraphResponse)
def get_case_graph(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    builder = _build_graph_for_case(case_id, db)
    return builder.to_schema()

@router.get("/{case_id}/trace/{node_id}")
def trace_flagged_node(case_id: str, node_id: str, db: Session = Depends(get_db)):
    """
    Centerpiece: 'Why was this result flagged?'
    Reverse lineage traversal from suspicious inference or model back to source contributor and dataset.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    builder = _build_graph_for_case(case_id, db)
    trace = builder.trace_flag_subgraph(node_id)
    return trace

@router.get("/{case_id}/convergence")
def get_cross_lifecycle_convergence(case_id: str, db: Session = Depends(get_db)):
    """
    Requirement 14: Structured Cross-Lifecycle Evidence Correlation.
    Reveals whether multiple independent lifecycle boundaries converge on an asset.
    """
    findings = db.query(Finding).filter(Finding.case_id == case_id).all()
    builder = _build_graph_for_case(case_id, db)
    return builder.analyze_cross_lifecycle_convergence(findings)
