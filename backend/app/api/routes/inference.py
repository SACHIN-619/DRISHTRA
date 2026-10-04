"""
DRISHTRA Inference Attestor API Endpoints
Provides:
- Canonical Inference Record Registration
- Cryptographic Ed25519 Attestation & Replay Protection Verification
- Tactical Inference Querying & Passport Discovery
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import InferenceRecord
from app.schemas.all_schemas import (
    InferenceRegister, InferenceResponse, AssurancePassportResponse
)
from app.services.inference_service import InferenceService
from app.services.passport_service import PassportService

from app.core.security import require_permission, TokenData
from app.core.rbac import Permission

router = APIRouter(prefix="/api/v1/inferences", tags=["Inference Attestor"], dependencies=[Depends(require_permission(Permission.ASSET_READ))])

class VerifyRequest(BaseModel):
    public_key_hex: Optional[str] = None  # defaults to the registered signer key

@router.post("", response_model=InferenceResponse, status_code=status.HTTP_201_CREATED)
def register_inference(
    inf_in: InferenceRegister,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.INFERENCE_SUBMIT))
):
    return InferenceService.register_inference(db, inf_in, actor=user.username)

@router.post("/{inference_id}/verify")
def verify_inference(
    inference_id: str,
    req: VerifyRequest = VerifyRequest(),
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.CRYPTO_VERIFY))
):
    try:
        key = req.public_key_hex
        if not key:
            from app.services.artifact_store import ArtifactStore
            rec = db.query(InferenceRecord).filter(InferenceRecord.inference_id == inference_id).first()
            key = ArtifactStore.load_signer_key(rec.signer or "") if rec else None
        res = InferenceService.verify_inference(db, inference_id, key, actor=user.username)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

class SignerKey(BaseModel):
    signer: str = Field(..., pattern=r"^[A-Za-z0-9._-]{1,96}$")
    public_key_hex: str = Field(..., pattern=r"^[0-9a-fA-F]{64}$")


@router.post("/signers", status_code=201)
def register_signer_key(
    req: SignerKey,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.CRYPTO_VERIFY)),
):
    """Register the Ed25519 public key of an inference signer (edge node / runtime)."""
    from app.services.artifact_store import ArtifactStore
    from app.services.platform_audit_service import PlatformAuditService
    ArtifactStore.save_signer_key(req.signer, req.public_key_hex.lower())
    PlatformAuditService.record(db, "GOVERNANCE", actor=user.username, actor_role=user.role.value,
                                action="SIGNER_KEY_REGISTERED", target=req.signer,
                                details={"fingerprint": __import__("hashlib").sha256(bytes.fromhex(req.public_key_hex)).hexdigest()[:16]})
    return {"signer": req.signer, "status": "REGISTERED"}


@router.get("")
def list_inferences(case_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(InferenceRecord)
    if case_id:
        q = q.filter(InferenceRecord.case_id == case_id)
    return [InferenceResponse.model_validate(i) for i in q.order_by(InferenceRecord.sequence.asc()).all()]


@router.get("/{inference_id}", response_model=InferenceResponse)
def get_inference(inference_id: str, db: Session = Depends(get_db)):
    inf = db.query(InferenceRecord).filter(InferenceRecord.inference_id == inference_id).first()
    if not inf:
        raise HTTPException(status_code=404, detail=f"Inference record {inference_id} not found")
    return inf

@router.get("/case/{case_id}", response_model=List[InferenceResponse])
def list_inferences_for_case(case_id: str, db: Session = Depends(get_db)):
    return db.query(InferenceRecord).filter(InferenceRecord.case_id == case_id).order_by(InferenceRecord.sequence.asc()).all()

@router.get("/{inference_id}/passport")
def get_inference_passport(inference_id: str, db: Session = Depends(get_db), user: TokenData = Depends(require_permission(Permission.EVIDENCE_READ))):
    passport = PassportService.get_inference_passport(db, inference_id)
    if not passport:
        raise HTTPException(status_code=404, detail=f"Inference {inference_id} not found")
    return passport
