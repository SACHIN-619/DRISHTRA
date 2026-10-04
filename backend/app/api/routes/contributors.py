"""
DRISHTRA Contributor API Endpoints
Provides contributor entity registration and querying.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Contributor
from app.schemas.all_schemas import ContributorCreate, ContributorResponse
from app.services.case_service import ContributorService

from app.core.security import require_permission, TokenData
from app.core.rbac import Permission

router = APIRouter(prefix="/api/v1/contributors", tags=["Contributors"], dependencies=[Depends(require_permission(Permission.ASSET_READ))])

@router.post("", response_model=ContributorResponse, status_code=status.HTTP_201_CREATED)
def register_contributor(contrib_in: ContributorCreate, db: Session = Depends(get_db), user: TokenData = Depends(require_permission(Permission.CASE_CREATE))):
    return ContributorService.register_contributor(db, contrib_in, actor=user.username)

@router.get("/{contributor_id}", response_model=ContributorResponse)
def get_contributor(contributor_id: str, db: Session = Depends(get_db)):
    contrib = db.query(Contributor).filter(Contributor.contributor_id == contributor_id).first()
    if not contrib:
        raise HTTPException(status_code=404, detail=f"Contributor {contributor_id} not found")
    return contrib

@router.get("/case/{case_id}", response_model=List[ContributorResponse])
def list_contributors_for_case(case_id: str, db: Session = Depends(get_db)):
    return ContributorService.get_contributors_by_case(db, case_id)


@router.get("", include_in_schema=True)
def contributor_risk(db: Session = Depends(get_db), user: TokenData = Depends(require_permission(Permission.EVIDENCE_READ))):
    """
    Contributor risk view: for each contributor, the assets they supplied and the
    current findings on those assets and on everything downstream of them.
    """
    from app.db.models import Dataset, ModelAsset, InferenceRecord, Finding, EvidenceEdge
    out = []
    for c in db.query(Contributor).all():
        ds = [d.dataset_id for d in db.query(Dataset).filter(Dataset.contributor_id == c.contributor_id, Dataset.case_id == c.case_id)]
        ms = {m.model_id for m in db.query(ModelAsset).filter(ModelAsset.contributor_id == c.contributor_id, ModelAsset.case_id == c.case_id)}
        # models trained from this contributor's datasets are downstream too
        for e in db.query(EvidenceEdge).filter(EvidenceEdge.case_id == c.case_id, EvidenceEdge.relationship == "trained_from"):
            if e.source_node.split(":", 1)[-1] in ds:
                ms.add(e.target_node.split(":", 1)[-1])
        inf = [i.inference_id for i in db.query(InferenceRecord).filter(InferenceRecord.case_id == c.case_id, InferenceRecord.model_id.in_(ms))] if ms else []
        assets = ds + sorted(ms) + inf
        fs = db.query(Finding).filter(Finding.case_id == c.case_id, Finding.asset_id.in_(assets)).all() if assets else []
        sev = {k: sum(1 for f in fs if f.severity == k) for k in ("CRITICAL", "HIGH", "MEDIUM", "LOW")}
        layers = sorted({f.asset_type for f in fs if f.severity in ("CRITICAL", "HIGH", "MEDIUM")})
        out.append({
            "contributor_id": c.contributor_id, "name": c.name, "type": c.contributor_type, "case_id": c.case_id,
            "datasets": ds, "models": sorted(ms), "inferences": inf, "severity_counts": sev, "layers_implicated": layers,
            "risk": "HIGH" if len(layers) >= 2 or sev["CRITICAL"] else "ELEVATED" if sev["HIGH"] or sev["MEDIUM"] else "LOW",
        })
    order = {"HIGH": 0, "ELEVATED": 1, "LOW": 2}
    return sorted(out, key=lambda x: (order[x["risk"]], x["contributor_id"]))
