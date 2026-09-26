"""
DRISHTRA Pydantic Schemas
Strict type definitions and serialization contracts for all REST API endpoints.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# --- CASE SCHEMAS ---
class CaseCreate(BaseModel):
    name: str = Field(..., example="Northern Border Reconnaissance Pipeline V4")
    description: Optional[str] = Field(None, example="Evaluation of multi-contributor armored vehicle classification assets")
    classification: str = Field("RESTRICTED", example="RESTRICTED")

class CaseResponse(BaseModel):
    case_id: str
    name: str
    description: Optional[str]
    classification: str
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

# --- CONTRIBUTOR SCHEMAS ---
class ContributorCreate(BaseModel):
    case_id: str
    name: str = Field(..., example="Defence Research Consortium Hub-07")
    contributor_type: str = Field("VENDOR", example="VENDOR")
    public_key: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

class ContributorResponse(BaseModel):
    contributor_id: str
    case_id: str
    name: str
    contributor_type: str
    public_key: Optional[str]
    metadata_json: str
    registered_at: str

    class Config:
        from_attributes = True

# --- DATASET SCHEMAS ---
class DatasetRegister(BaseModel):
    case_id: str
    contributor_id: str
    name: str = Field(..., example="UVH-26 Synthetic Reconnaissance Split")
    format: str = Field("COCO", example="COCO")
    version: str = Field("1.0.0", example="1.0.0")
    location: Optional[str] = None
    sample_count: int = 100
    metadata: Optional[Dict[str, Any]] = None

class DatasetResponse(BaseModel):
    dataset_id: str
    case_id: str
    contributor_id: str
    name: str
    format: str
    version: str
    sha256: str
    manifest_hash: str
    sample_count: int
    metadata_json: str
    created_at: str

    class Config:
        from_attributes = True

# --- MODEL ASSET SCHEMAS ---
class ModelRegister(BaseModel):
    case_id: str
    contributor_id: str
    name: str = Field(..., example="Tactical YOLO-TargetDetector v8s")
    framework: str = Field("PyTorch", example="PyTorch")
    format: str = Field("ONNX", example="ONNX")
    architecture: str = Field("YOLOv8", example="YOLOv8")
    version: str = Field("1.0.0", example="1.0.0")
    reference_model_id: Optional[str] = None
    access_level: str = Field("BLACK_BOX", example="BLACK_BOX")
    location: Optional[str] = None

class ModelResponse(BaseModel):
    model_id: str
    case_id: str
    contributor_id: str
    name: str
    framework: str
    format: str
    architecture: str
    version: str
    weight_sha256: str
    reference_model_id: Optional[str]
    access_level: str
    created_at: str

    class Config:
        from_attributes = True

# --- INFERENCE RECORD SCHEMAS ---
class InferenceRegister(BaseModel):
    inference_id: Optional[str] = None
    case_id: str
    model_id: Optional[str] = None
    input_sha256: str
    model_sha256: str
    preprocess_sha256: str
    config_sha256: str
    output_sha256: str
    sequence: int = 1
    timestamp: Optional[str] = None
    nonce: str
    previous_record_hash: str
    signature: str
    predictions: Optional[Dict[str, Any]] = None
    operational_metadata: Optional[Dict[str, Any]] = None

class InferenceResponse(BaseModel):
    inference_id: str
    case_id: str
    model_id: Optional[str]
    input_sha256: str
    model_sha256: str
    preprocess_sha256: str
    config_sha256: str
    output_sha256: str
    sequence: int
    timestamp: str
    nonce: str
    previous_record_hash: str
    signature: str
    verification_status: str
    predictions_json: str
    operational_metadata_json: str

    class Config:
        from_attributes = True

# --- FINDING & EVIDENCE SCHEMAS ---
class FindingResponse(BaseModel):
    finding_id: str
    case_id: str
    asset_id: str
    asset_type: str
    detector_id: str
    detector_version: str
    finding_type: str
    severity: str
    confidence: float
    status: str
    explanation: str
    limitations: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

class EvidenceResponse(BaseModel):
    evidence_id: str
    case_id: str
    finding_id: Optional[str]
    evidence_type: str
    source_asset: str
    detector: str
    observation: str
    measurement_json: str
    confidence: float
    supporting_artifact: Optional[str]
    timestamp: str
    sha256: str

    class Config:
        from_attributes = True

# --- EVIDENCE GRAPH SCHEMAS ---
class GraphNode(BaseModel):
    id: str
    label: str
    type: str # Contributor, Dataset, Model, Inference, Finding, OperationalContext
    status: Optional[str] = None # VERIFIED, FINDING, QUARANTINED, NORMAL
    details: Dict[str, Any] = {}

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str # contributed_by, contains, trained_from, produced, deviates_from, supports, correlates_with
    epistemic_status: str # OBSERVED, DERIVED, SUPPORTS, CORRELATES, UNKNOWN
    evidence_ids: List[str] = []

class EvidenceGraphResponse(BaseModel):
    case_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]

# --- ASSURANCE CASE SCHEMAS ---
class AssuranceAssessRequest(BaseModel):
    policy_version: Optional[str] = "DRISHTRA-AP-2026.1"

class AssuranceCaseResponse(BaseModel):
    assurance_id: str
    case_id: str
    claim: str
    status: str # VERIFIED, REVIEW_REQUIRED, QUARANTINED, INCONCLUSIVE
    recommended_disposition: str # ACCEPT, REVIEW, QUARANTINE
    supporting_evidence: List[Dict[str, Any]]
    counter_evidence: List[Dict[str, Any]]
    coverage: Dict[str, str] # e.g. {"dataset_integrity": "AVAILABLE", ...}
    limitations: List[str]
    policy_version: str
    created_at: str

# --- AUDIT SCHEMAS ---
class AuditEventResponse(BaseModel):
    event_id: str
    case_id: str
    actor: str
    action: str
    asset_id: Optional[str] = None
    result: str
    reason: Optional[str] = None
    timestamp: str
    previous_event_hash: str
    event_hash: str
    signature: Optional[str] = None

    class Config:
        from_attributes = True

class AuditVerifyResponse(BaseModel):
    status: str # VALID, BROKEN_CHAIN, TAMPERED_RECORD
    verified_count: int
    details: str
    events: List[AuditEventResponse] = []

# --- PASSPORT SCHEMAS ---
class AssurancePassportResponse(BaseModel):
    passport_id: str
    asset_id: str
    asset_type: str # MODEL, DATASET, INFERENCE
    name: str
    contributor: str
    version: str
    digest_sha256: str
    lineage_parent: Optional[str]
    assurance_status: str # VERIFIED, REVIEW_REQUIRED, QUARANTINED, INCONCLUSIVE
    findings_summary: Dict[str, int]
    coverage_matrix: Dict[str, str]
    limitations: List[str]
    verified_claims: List[str]
    counter_findings: List[str]
    last_assessed: str
