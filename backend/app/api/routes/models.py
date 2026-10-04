import os
"""
DRISHTRA Model Sentinel API Endpoints
Provides:
- Model Asset Registration & Upload
- Structural Inspection (ONNX, PyTorch)
- Behavioral Perturbation Probe Battery
- Model Integrity Scanning & Trojan Backdoor Detection
- Model Assurance Passport Retrieval
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import ModelAsset, Finding, Case
from app.schemas.all_schemas import ModelRegister, ModelResponse, FindingResponse, AssurancePassportResponse
from app.services.model_service import ModelService
from app.services.passport_service import PassportService
from app.ingestion.file_vault import FileVault, SecurityValidationError
from app.ingestion.model_inspectors import ModelInspector

from app.core.security import require_permission, TokenData
from app.core.rbac import Permission

router = APIRouter(prefix="/api/v1/models", tags=["Model Sentinel"], dependencies=[Depends(require_permission(Permission.ASSET_READ))])

@router.post("/register", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
def register_model(model_in: ModelRegister, db: Session = Depends(get_db), user: TokenData = Depends(require_permission(Permission.MODEL_REGISTER))):
    try:
        return ModelService.register_model(db, model_in, actor=user.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_models(case_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(ModelAsset)
    if case_id:
        q = q.filter(ModelAsset.case_id == case_id)
    return [ModelResponse.model_validate(m) for m in q.order_by(ModelAsset.created_at.desc()).all()]


@router.post("/{model_id}/delivered")
async def record_delivered_artifact(
    model_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.MODEL_REGISTER)),
):
    """
    Store the model artifact *as delivered* for deployment. Stage 07 compares its
    digest with the registered one (D8A), which catches substitution after registration.
    """
    from app.services.artifact_store import ArtifactStore
    from app.services.audit_service import AuditService
    m = db.query(ModelAsset).filter(ModelAsset.model_id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    content = await file.read()
    try:
        path, sha, size = FileVault.save_uploaded_stream(content, file.filename or "model.onnx", category="MODEL")
    except SecurityValidationError as se:
        raise HTTPException(status_code=400, detail=str(se))
    ArtifactStore.save_supplied_digest(model_id, sha, source=f"delivered file {os.path.basename(path)}")
    AuditService.record_event(db=db, case_id=m.case_id, actor=user.username, action="MODEL_ARTIFACT_DELIVERED",
                              asset_id=model_id, result="RECORDED",
                              reason=f"delivered sha256={sha} registered sha256={m.weight_sha256}")
    return {"model_id": model_id, "delivered_sha256": sha, "registered_sha256": m.weight_sha256,
            "matches_registration": sha == m.weight_sha256, "size_bytes": size}


@router.post("/{model_id}/probes")
def record_probe_responses(
    model_id: str,
    probes: Dict[str, Dict[str, Any]],
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.MODEL_REGISTER)),
):
    """
    Record black-box probe responses captured by the offline runtime harness
    (e.g. {"clean": {"predicted_class": "...", "confidence": 0.9}, "trigger_patch_corner": {...}}).
    Stage 08 evaluates them (D8B). A 'clean' probe is required as the baseline.
    """
    from app.services.artifact_store import ArtifactStore
    from app.services.audit_service import AuditService
    m = db.query(ModelAsset).filter(ModelAsset.model_id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    if "clean" not in probes:
        raise HTTPException(status_code=400, detail="A 'clean' baseline probe is required.")
    digest = ArtifactStore.save_model_probes(model_id, probes)
    AuditService.record_event(db=db, case_id=m.case_id, actor=user.username, action="MODEL_PROBES_RECORDED",
                              asset_id=model_id, result="RECORDED", reason=f"{len(probes)} probes digest={digest}")
    return {"model_id": model_id, "probes": len(probes), "digest": digest}

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_model_artifact(
    case_id: str = Form(...),
    contributor_id: str = Form(...),
    model_name: str = Form(...),
    framework: str = Form("PyTorch"),
    architecture: str = Form("YOLOv8s"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.MODEL_REGISTER))
):
    """
    Safely uploads an untrusted model file (.onnx, .pt, .pth).
    Validates file bounds, computes SHA-256 digest, and performs structural inspection.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    content_bytes = await file.read()
    try:
        saved_path, weight_sha, file_size = FileVault.save_uploaded_stream(
            stream_bytes=content_bytes,
            original_filename=file.filename or "model.onnx",
            category="MODEL"
        )
    except SecurityValidationError as se:
        raise HTTPException(status_code=400, detail=str(se))

    # Parse structural properties
    ext = (file.filename or "").lower()
    if ext.endswith(".onnx"):
        passport = ModelInspector.inspect_onnx_model(content_bytes, model_name=model_name)
    else:
        passport = ModelInspector.inspect_pytorch_model(content_bytes, model_name=model_name)

    model_reg = ModelRegister(
        case_id=case_id,
        contributor_id=contributor_id,
        name=model_name,
        framework=framework,
        format="ONNX" if ext.endswith(".onnx") else "PT",
        architecture=architecture,
        version="1.0.0",
        access_level=passport.get("access_level", "BLACK_BOX"),
        evidence_label="REAL_PUBLIC" if "PUBLIC" in model_name.upper() else "SYNTHETIC",
        location=saved_path
    )
    model = ModelService.register_model(db, model_reg, weight_bytes=content_bytes, actor=user.username)
    model.structural_digest = passport.get("structural_digest")
    model.parameter_count = passport.get("estimated_parameters") or passport.get("node_count") or 0
    model.opset_version = passport.get("opset_version")
    db.commit()

    return {
        "model_id": model.model_id,
        "name": model.name,
        "weight_sha256": model.weight_sha256,
        "structural_digest": model.structural_digest,
        "access_level": model.access_level,
        "size_bytes": file_size,
        "status": "REGISTERED_AND_INSPECTED"
    }

@router.get("/{model_id}", response_model=ModelResponse)
def get_model(model_id: str, db: Session = Depends(get_db)):
    model = db.query(ModelAsset).filter(ModelAsset.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return model

@router.post("/{model_id}/scan", response_model=List[FindingResponse])
def scan_model(
    model_id: str,
    scan_payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.PIPELINE_RUN))
):
    current_digest = scan_payload.get("current_weight_sha256") if scan_payload else None
    probes = scan_payload.get("probe_responses") if scan_payload else None
    
    model = db.query(ModelAsset).filter(ModelAsset.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    if not current_digest:
        current_digest = model.weight_sha256

    try:
        findings = ModelService.scan_model(
            db=db,
            model_id=model_id,
            current_weight_sha256=current_digest,
            probe_responses=probes,
            actor=user.username
        )
        return findings
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{model_id}/findings", response_model=List[FindingResponse])
def get_model_findings(model_id: str, db: Session = Depends(get_db), user: TokenData = Depends(require_permission(Permission.EVIDENCE_READ))):
    return db.query(Finding).filter(Finding.asset_id == model_id).all()

@router.get("/{model_id}/passport")
def get_model_passport(model_id: str, db: Session = Depends(get_db), user: TokenData = Depends(require_permission(Permission.EVIDENCE_READ))):
    passport = PassportService.get_model_passport(db, model_id)
    if not passport:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return passport

@router.post("/inspect-onnx")
def inspect_onnx_model_endpoint(payload: Dict[str, Any], user: TokenData = Depends(require_permission(Permission.MODEL_REGISTER))):
    """Inspects ONNX model graph structure, opset, inputs, outputs, and parameters."""
    name = payload.get("model_name", "Tactical_YOLO_ONNX")
    file_path = payload.get("file_path", None)
    return ModelInspector.inspect_onnx_model(file_path or name, model_name=name)

@router.post("/inspect-pytorch")
def inspect_pytorch_model_endpoint(payload: Dict[str, Any], user: TokenData = Depends(require_permission(Permission.MODEL_REGISTER))):
    """Inspects PyTorch state_dict, parameters, and weight precision."""
    name = payload.get("model_name", "Tactical_PyTorch_Model")
    file_path = payload.get("file_path", None)
    return ModelInspector.inspect_pytorch_model(file_path or name, model_name=name)
