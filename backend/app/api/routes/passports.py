"""
DRISHTRA First-Class Assurance Passport Endpoint
Provides:
- GET /api/v1/passports/{asset_id}
- GET /passports/{asset_id}
Universal resolver for Model, Dataset, and Inference cryptographic passports.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.all_schemas import AssurancePassportResponse
from app.services.passport_service import PassportService

from app.core.security import require_permission, TokenData
from app.core.rbac import Permission

router = APIRouter(prefix="/api/v1/passports", tags=["Assurance Passports"], dependencies=[Depends(require_permission(Permission.EVIDENCE_READ))])

@router.get("/{asset_id}")
def get_universal_passport(asset_id: str, db: Session = Depends(get_db)):
    """
    Universally retrieves the digital security Assurance Passport for any protected asset:
    Model, Dataset, or Inference.
    """
    # 1. Try Model
    model_p = PassportService.get_model_passport(db, asset_id)
    if model_p:
        return model_p
    
    # 2. Try Dataset
    ds_p = PassportService.get_dataset_passport(db, asset_id)
    if ds_p:
        return ds_p

    # 3. Try Inference
    inf_p = PassportService.get_inference_passport(db, asset_id)
    if inf_p:
        return inf_p

    raise HTTPException(status_code=404, detail=f"No assurance passport found for asset ID '{asset_id}'")
