"""
DRISHTRA Pydantic Schemas
Strict type definitions and serialization contracts for all REST API endpoints.
Fully compliant with Pydantic V2 (ConfigDict, json_schema_extra).
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# --- ERROR RESPONSE ENVELOPE ---
class ErrorDetail(BaseModel):
    code: str = Field(..., json_schema_extra={"example": "DATASET_VALIDATION_FAILED"})
    message: str = Field(..., json_schema_extra={"example": "Detailed failure diagnostic"})
    request_id: Optional[str] = Field(None, json_schema_extra={"example": "req-9a8b7c6d"})
    details: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail


# --- CASE SCHEMAS ---
class CaseCreate(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Northern Border Reconnaissance Pipeline V4"})
    description: Optional[str] = Field(None, json_schema_extra={"example": "Evaluation of multi-contributor armored vehicle classification assets"})
    classification: str = Field("RESTRICTED", json_schema_extra={"example": "RESTRICTED"})

class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: str
    name: str
    description: Optional[str] = None
    classification: str
    status: str
    created_at: str
    updated_at: str


# --- CONTRIBUTOR SCHEMAS ---
class ContributorCreate(BaseModel):
    case_id: str
    name: str = Field(..., json_schema_extra={"example": "Defence Research Consortium Hub-07"})
    contributor_type: str = Field("VENDOR", json_schema_extra={"example": "VENDOR"})
    public_key: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

class ContributorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contributor_id: str
    case_id: str
    name: str
    contributor_type: str
    public_key: Optional[str] = None
    metadata_json: str
    registered_at: str


# --- DATASET SCHEMAS ---
class DatasetRegister(BaseModel):
    case_id: str
    contributor_id: str
    name: str = Field(..., json_schema_extra={"example": "UVH-26 Synthetic Reconnaissance Split"})
    format: str = Field("COCO", json_schema_extra={"example": "COCO"})
    version: str = Field("1.0.0", json_schema_extra={"example": "1.0.0"})
    location: Optional[str] = None
    sample_count: int = 100
    evidence_label: str = Field("SYNTHETIC", json_schema_extra={"example": "SYNTHETIC"})
    metadata: Optional[Dict[str, Any]] = None

class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dataset_id: str
    case_id: str
    contributor_id: str
    name: str
    format: str
    version: str
    sha256: str
    manifest_hash: str
    sample_count: int
    evidence_label: str
    metadata_json: str
    created_at: str


# --- DATASET CHUNK SCHEMAS ---
class DatasetChunkCreate(BaseModel):
    dataset_id: str
    case_id: str
    chunk_index: int = 0
    records: List[Dict[str, Any]] = []

class DatasetChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    dataset_id: str
    case_id: str
    chunk_index: int
    record_count: int
    first_record_id: Optional[str] = None
    last_record_id: Optional[str] = None
    sha256: str
    schema_version: str
    created_at: str


# --- CANONICAL IMAGE RECORD (Internal CV Normalized Format) ---
class CanonicalAnnotation(BaseModel):
    class_id: int
    class_name: str
    bbox: List[float] = [] # [x_min, y_min, width, height]
    confidence: Optional[float] = None
    segmentation: Optional[List[Any]] = None
    area: Optional[float] = None
    iscrowd: int = 0

class CanonicalImageRecord(BaseModel):
    image_id: str
    dataset_id: str
    file_hash: str
    file_name: str
    width: int = 640
    height: int = 640
    split: str = "train"
    sensor_type: str = "OPTICAL" # OPTICAL, FLIR_THERMAL, SAR, HYPERSPECTRAL
    capture_profile: str = "DAYLIGHT"
    timestamp_bucket: Optional[str] = None
    synthetic_location: Optional[str] = None
    annotations: List[CanonicalAnnotation] = []
    class_ids: List[int] = []
    source_contributor_id: Optional[str] = None
    ground_truth_status: str = "VERIFIED" # VERIFIED, POISONED, SUSPICIOUS, UNVERIFIED


# --- MODEL ASSET SCHEMAS ---
class ModelRegister(BaseModel):
    case_id: str
    contributor_id: str
    name: str = Field(..., json_schema_extra={"example": "Tactical YOLO-TargetDetector v8s"})
    framework: str = Field("PyTorch", json_schema_extra={"example": "PyTorch"})
    format: str = Field("ONNX", json_schema_extra={"example": "ONNX"})
    architecture: str = Field("YOLOv8", json_schema_extra={"example": "YOLOv8"})
    version: str = Field("1.0.0", json_schema_extra={"example": "1.0.0"})
    reference_model_id: Optional[str] = None
    access_level: str = Field("BLACK_BOX", json_schema_extra={"example": "BLACK_BOX"})
    evidence_label: str = Field("SYNTHETIC", json_schema_extra={"example": "SYNTHETIC"})
    location: Optional[str] = None
    # Digest the contributor declares at registration. Required unless weights are uploaded.
    weight_sha256: Optional[str] = Field(None, pattern=r"^[0-9a-f]{64}$")

class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_id: str
    case_id: str
    contributor_id: str
    name: str
    framework: str
    format: str
    architecture: str
    version: str
    weight_sha256: str
    structural_digest: Optional[str] = None
    parameter_count: int = 0
    opset_version: Optional[int] = None
    reference_model_id: Optional[str] = None
    access_level: str
    evidence_label: str
    created_at: str


# --- RUNTIME BINDING SCHEMAS ---
class RuntimeBindingCreate(BaseModel):
    case_id: str
    model_id: str
    framework_version: str = "PyTorch-2.x"
    hardware_target: str = "CPU"
    quantization: str = "FP32"
    batch_size: int = 1
    metadata: Optional[Dict[str, Any]] = None

class RuntimeBindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    runtime_id: str
    case_id: str
    model_id: str
    framework_version: str
    hardware_target: str
    quantization: str
    batch_size: int
    config_digest: str
    metadata_json: str
    created_at: str


# --- INFERENCE RECORD SCHEMAS ---
class InferenceRegister(BaseModel):
    inference_id: Optional[str] = None
    case_id: str
    dataset_id: Optional[str] = None
    sample_id: Optional[str] = None
    model_id: Optional[str] = None
    runtime_id: Optional[str] = None
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
    signer: Optional[str] = "edge_drone_01"
    evidence_label: str = "SYNTHETIC"
    predictions: Optional[Dict[str, Any]] = None
    operational_metadata: Optional[Dict[str, Any]] = None

class InferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inference_id: str
    case_id: str
    dataset_id: Optional[str] = None
    sample_id: Optional[str] = None
    model_id: Optional[str] = None
    runtime_id: Optional[str] = None
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
    signer: str
    verification_status: str
    evidence_label: str
    predictions_json: str
    operational_metadata_json: str


# --- FINDING & EVIDENCE SCHEMAS ---
class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    finding_id: str
    case_id: str
    asset_id: str
    asset_type: str
    detector_id: str
    detector_version: str
    finding_type: str
    severity: str
    confidence: Optional[float] = None
    deterministic: bool = False
    status: str
    explanation: str
    limitations: Optional[str] = None
    created_at: str

class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: str
    case_id: str
    finding_id: Optional[str] = None
    target_type: str
    target_id: str
    lifecycle_stage: str
    detector_id: str
    finding_type: str
    evidence_type: str
    severity: str
    status: str
    observation: str
    measurement_json: str
    confidence: Optional[float] = None
    deterministic: bool = False
    supporting_artifact: Optional[str] = None
    artifact_digest: Optional[str] = None
    limitations: Optional[str] = None
    timestamp: str
    sha256: str


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

class LineageTraceResponse(BaseModel):
    target: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    trace_summary: str
    converged: bool = False
    lifecycle_boundaries: List[str] = []


# --- ASSURANCE CASE SCHEMAS ---
class AssuranceAssessRequest(BaseModel):
    policy_version: Optional[str] = None

class DispositionApprovalRequest(BaseModel):
    case_id: Optional[str] = None
    disposition: str = Field(..., json_schema_extra={"example": "QUARANTINE"})  # ACCEPT, REVIEW, QUARANTINE
    notes: Optional[str] = Field(None, json_schema_extra={"example": "Three independent evidence paths converge on contributor C-07."})

class DecisionRequest(BaseModel):
    disposition: str = Field(..., json_schema_extra={"example": "QUARANTINE"})  # ACCEPT, REVIEW, QUARANTINE
    rationale: str = Field(..., min_length=10, max_length=4000)

class AssuranceCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assurance_id: str
    case_id: str
    claim: str
    status: str # VERIFIED, REVIEW_REQUIRED, QUARANTINED, INCONCLUSIVE
    recommended_disposition: str # ACCEPT, REVIEW, QUARANTINE
    human_disposition: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    approval_notes: Optional[str] = None
    supporting_evidence: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []
    counter_evidence: List[Dict[str, Any]] = []
    coverage: Dict[str, Any] = {}
    coverage_summary: Dict[str, Any] = {}
    convergence: Dict[str, Any] = {}
    rules_fired: List[str] = []
    severity_counts: Dict[str, int] = {}
    drift_assessment: Optional[Dict[str, Any]] = None
    limitations: List[str] = []
    initiated_by: Optional[str] = None
    decisions: List[Dict[str, Any]] = []
    policy_version: str
    created_at: str


# --- AUDIT SCHEMAS ---
class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    case_id: str
    sequence: int
    actor: str
    action: str
    asset_id: Optional[str] = None
    result: str
    reason: Optional[str] = None
    timestamp: str
    previous_event_hash: str
    event_hash: str
    signature: Optional[str] = None

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
    lineage_parent: Optional[str] = None
    assurance_status: str # VERIFIED, REVIEW_REQUIRED, QUARANTINED, INCONCLUSIVE
    findings_summary: Dict[str, int]
    coverage_matrix: Dict[str, str]
    limitations: List[str]
    verified_claims: List[str]
    counter_findings: List[str]
    last_assessed: str


# --- PIPELINE ORCHESTRATOR SCHEMAS ---
class StageResult(BaseModel):
    stage_id: str
    stage_name: str
    status: str # SUCCESS, FAILED, SKIPPED
    duration_ms: float = 0.0
    input_summary: Dict[str, Any] = {}
    output_summary: Dict[str, Any] = {}
    evidence_generated: int = 0
    artifacts_generated: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

class PipelineRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    case_id: str
    status: str # RUNNING, COMPLETED, FAILED
    current_stage: str
    stages: List[StageResult] = []
    started_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


# --- SYSTEM & CAPABILITIES SCHEMAS ---
class SystemCapabilitiesResponse(BaseModel):
    system: str = "DRISHTRA"
    version: str = "1.0.0"
    air_gapped: bool = True
    database_backend: str = "sqlite"
    dataset_formats: List[str] = ["COCO", "YOLO", "CSV", "IMAGE_FOLDER"]
    model_formats: List[str] = ["ONNX", "PyTorch"]
    detectors: List[str] = [
        "EXACT_DUPLICATE",
        "NEAR_DUPLICATE",
        "LABEL_CONFLICT",
        "CLASS_IMBALANCE",
        "DISTRIBUTION_SHIFT",
        "MALFORMED_ANNOTATION",
        "TRIGGER_SUSCEPTIBILITY",
        "MODEL_INTEGRITY",
        "SIGNATURE_TAMPER",
        "REPLAY"
    ]
    assurance_states: List[str] = [
        "VERIFIED",
        "FINDING",
        "NOT_TESTED",
        "INCONCLUSIVE",
        "NOT_APPLICABLE"
    ]
    dispositions: List[str] = [
        "ACCEPT",
        "REVIEW",
        "QUARANTINE"
    ]
    external_dependencies: List[str] = []
    policy_version: str = "DRISHTRA-AP-2026.1"
    pipeline_version: str = "1.0.0"

class SystemInfoResponse(BaseModel):
    project_name: str
    subtitle: str
    version: str
    environment: str
    is_air_gapped: bool
    database_url: str
    active_storage_dir: str
    uptime_seconds: float


# --- ASSURANCE RUN SCHEMAS ---
class AssuranceRunCreate(BaseModel):
    case_id: str = Field(..., json_schema_extra={"example": "CASE-2026-DRISHTRA-DEMO"})
    dataset_id: Optional[str] = Field(None, json_schema_extra={"example": "MUTATED_ASSURANCE_TEST"})
    model_id: Optional[str] = Field(None, json_schema_extra={"example": "MODEL-DEMO-01"})
    execution_mode: str = Field("OFFLINE", json_schema_extra={"example": "OFFLINE"})

class AssuranceRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assurance_run_id: str
    case_id: str
    dataset_id: Optional[str] = None
    model_id: Optional[str] = None
    execution_mode: str
    status: str
    current_stage: str
    detector_versions: Dict[str, str] = {}
    policy_version: str
    dataset_version: str
    model_version: str
    input_hashes: Dict[str, Any] = {}
    output_hashes: Dict[str, Any] = {}
    errors: List[str] = []
    warnings: List[str] = []
    coverage: Dict[str, Any] = {}
    started_at: str
    completed_at: Optional[str] = None

class AssuranceRunListResponse(BaseModel):
    runs: List[AssuranceRunResponse]
    total: int
