"""
Attack Lab API (DEMO_MODE only): inject synthetic attacks into the sandbox case's stored
inputs, then run the normal pipeline and see which stage catches each one.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rbac import Permission
from app.core.security import TokenData, require_permission
from app.db.database import get_db
from app.db.models import Case
from app.services.attack_lab_service import LAB_CASE_ID, AttackLabError, AttackLabService

router = APIRouter(prefix="/api/v1/attack-lab", tags=["Attack Lab (demo)"])


def _guard(db: Session):
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=404, detail="The Attack Lab is only available in demonstration mode.")
    if not db.query(Case).filter(Case.case_id == LAB_CASE_ID).first():
        raise HTTPException(status_code=404, detail="Attack Lab sandbox case is not present. Run scripts/bootstrap_demo.py.")


@router.get("")
def describe(db: Session = Depends(get_db), user: TokenData = Depends(require_permission(Permission.ATTACK_SIMULATE))):
    _guard(db)
    return AttackLabService.describe()


@router.post("/{scenario}/inject")
def inject(scenario: str, db: Session = Depends(get_db),
           user: TokenData = Depends(require_permission(Permission.ATTACK_SIMULATE))):
    _guard(db)
    try:
        return AttackLabService.inject(db, scenario, actor=user.username)
    except AttackLabError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset")
def reset(db: Session = Depends(get_db), user: TokenData = Depends(require_permission(Permission.ATTACK_SIMULATE))):
    _guard(db)
    return AttackLabService.reset(db, actor=user.username)
