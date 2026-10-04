"""
DRISHTRA Runtime Binding API Endpoints
Provides runtime framework, hardware environment, and configuration binding.
"""
from typing import List
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import RuntimeBinding, ModelAsset, utc_now_iso
from app.schemas.all_schemas import RuntimeBindingCreate, RuntimeBindingResponse
from app.crypto.crypto_service import CryptoService

from app.core.security import require_permission, TokenData
from app.core.rbac import Permission

router = APIRouter(prefix="/api/v1/runtimes", tags=["Runtime Bindings"], dependencies=[Depends(require_permission(Permission.ASSET_READ))])

@router.post("", response_model=RuntimeBindingResponse, status_code=status.HTTP_201_CREATED)
def create_runtime_binding(
    rt_in: RuntimeBindingCreate,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.MODEL_REGISTER))
):
    model = db.query(ModelAsset).filter(ModelAsset.model_id == rt_in.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {rt_in.model_id} not found")

    r_id = f"RT-{uuid.uuid4().hex[:6].upper()}"
    cfg_payload = {
        "framework_version": rt_in.framework_version,
        "hardware_target": rt_in.hardware_target,
        "quantization": rt_in.quantization,
        "batch_size": rt_in.batch_size,
        "metadata": rt_in.metadata or {}
    }
    cfg_digest = CryptoService.hash(cfg_payload)

    rt = RuntimeBinding(
        runtime_id=r_id,
        case_id=rt_in.case_id,
        model_id=rt_in.model_id,
        framework_version=rt_in.framework_version,
        hardware_target=rt_in.hardware_target,
        quantization=rt_in.quantization,
        batch_size=rt_in.batch_size,
        config_digest=cfg_digest,
        metadata_json=json.dumps(rt_in.metadata or {}),
        created_at=utc_now_iso()
    )
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt

@router.get("/{runtime_id}", response_model=RuntimeBindingResponse)
def get_runtime_binding(runtime_id: str, db: Session = Depends(get_db)):
    rt = db.query(RuntimeBinding).filter(RuntimeBinding.runtime_id == runtime_id).first()
    if not rt:
        raise HTTPException(status_code=404, detail=f"Runtime {runtime_id} not found")
    return rt

@router.get("/case/{case_id}", response_model=List[RuntimeBindingResponse])
def list_runtimes_for_case(case_id: str, db: Session = Depends(get_db)):
    return db.query(RuntimeBinding).filter(RuntimeBinding.case_id == case_id).all()
