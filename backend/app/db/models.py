"""
DRISHTRA Relational Database Schema
High-Integrity Models for Cases, Contributors, Datasets, Model Assets, Runtime Bindings,
Inferences, Findings, Normalized Evidence, Evidence Graph, Assurance Cases,
Pipeline Runs, and Tamper-Evident Forensic Audit Ledger.
"""
from datetime import datetime, timezone
import json
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey, Index
)
from sqlalchemy.orm import relationship, relationship as orm_rel
from app.db.database import Base

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class Case(Base):
    __tablename__ = "cases"
    
    case_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    classification = Column(String(64), default="RESTRICTED", index=True) # UNCLASSIFIED, RESTRICTED, CONFIDENTIAL, SECRET
    status = Column(String(64), default="ACTIVE", index=True) # ACTIVE, ASSESSED, QUARANTINED, ARCHIVED
    created_at = Column(String(64), default=utc_now_iso, index=True)
    updated_at = Column(String(64), default=utc_now_iso)

    # Relationships
    contributors = relationship("Contributor", back_populates="case", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="case", cascade="all, delete-orphan")
    models = relationship("ModelAsset", back_populates="case", cascade="all, delete-orphan")
    runtimes = relationship("RuntimeBinding", back_populates="case", cascade="all, delete-orphan")
    inferences = relationship("InferenceRecord", back_populates="case", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="case", cascade="all, delete-orphan")
    evidence_items = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    evidence_edges = relationship("EvidenceEdge", back_populates="case", cascade="all, delete-orphan")
    assurance_cases = relationship("AssuranceCase", back_populates="case", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="case", cascade="all, delete-orphan")
    pipeline_runs = relationship("PipelineRun", back_populates="case", cascade="all, delete-orphan")
    assurance_runs = relationship("AssuranceRun", back_populates="case", cascade="all, delete-orphan")


class Contributor(Base):
    __tablename__ = "contributors"
    
    contributor_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    contributor_type = Column(String(64), default="VENDOR", index=True) # VENDOR, LAB, FIELD_UNIT, OPEN_SOURCE, SYNTHETIC
    public_key = Column(Text, nullable=True)
    metadata_json = Column(Text, default="{}")
    registered_at = Column(String(64), default=utc_now_iso)

    case = relationship("Case", back_populates="contributors")
    datasets = relationship("Dataset", back_populates="contributor")
    models = relationship("ModelAsset", back_populates="contributor")


class Dataset(Base):
    __tablename__ = "datasets"
    
    dataset_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    contributor_id = Column(String(64), ForeignKey("contributors.contributor_id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    format = Column(String(64), default="COCO") # COCO, YOLO, VOC, CSV, IMAGE_FOLDER
    version = Column(String(64), default="1.0.0")
    location = Column(String(512), nullable=True)
    sha256 = Column(String(64), nullable=False, index=True)
    manifest_hash = Column(String(64), nullable=False, index=True)
    sample_count = Column(Integer, default=0)
    evidence_label = Column(String(32), default="SYNTHETIC", index=True) # REAL_PUBLIC, SYNTHETIC, DERIVED, DEMO
    metadata_json = Column(Text, default="{}")
    created_at = Column(String(64), default=utc_now_iso, index=True)

    case = relationship("Case", back_populates="datasets")
    contributor = relationship("Contributor", back_populates="datasets")
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")
    chunks = relationship("DatasetChunk", back_populates="dataset", cascade="all, delete-orphan")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    
    dataset_version_id = Column(String(64), primary_key=True, index=True)
    dataset_id = Column(String(64), ForeignKey("datasets.dataset_id"), nullable=False, index=True)
    version = Column(String(64), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    manifest_hash = Column(String(64), nullable=False)
    created_at = Column(String(64), default=utc_now_iso)

    dataset = relationship("Dataset", back_populates="versions")


class DatasetChunk(Base):
    __tablename__ = "dataset_chunks"
    
    chunk_id = Column(String(64), primary_key=True, index=True)
    dataset_id = Column(String(64), ForeignKey("datasets.dataset_id"), nullable=False, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    chunk_index = Column(Integer, default=0)
    record_count = Column(Integer, default=0)
    first_record_id = Column(String(64), nullable=True)
    last_record_id = Column(String(64), nullable=True)
    sha256 = Column(String(64), nullable=False, index=True)
    schema_version = Column(String(32), default="1.0.0")
    created_at = Column(String(64), default=utc_now_iso)

    dataset = relationship("Dataset", back_populates="chunks")


class ModelAsset(Base):
    __tablename__ = "model_assets"
    
    model_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    contributor_id = Column(String(64), ForeignKey("contributors.contributor_id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    framework = Column(String(64), default="PyTorch") # PyTorch, ONNX, TorchScript, TensorFlow
    format = Column(String(64), default="ONNX") # ONNX, PT, TORCHSCRIPT
    architecture = Column(String(128), default="YOLOv8") # YOLO, ResNet, ViT, RT-DETR
    version = Column(String(64), default="1.0.0")
    weight_sha256 = Column(String(64), nullable=False, index=True)
    structural_digest = Column(String(64), nullable=True, index=True)
    parameter_count = Column(Integer, default=0)
    opset_version = Column(Integer, nullable=True)
    reference_model_id = Column(String(64), nullable=True)
    location = Column(String(512), nullable=True)
    access_level = Column(String(64), default="BLACK_BOX", index=True) # WHITE_BOX, BLACK_BOX, STRUCTURAL_ONLY, UNAVAILABLE
    evidence_label = Column(String(32), default="SYNTHETIC", index=True) # REAL_PUBLIC, SYNTHETIC, DERIVED, DEMO
    metadata_json = Column(Text, default="{}")
    created_at = Column(String(64), default=utc_now_iso, index=True)

    case = relationship("Case", back_populates="models")
    contributor = relationship("Contributor", back_populates="models")
    runtimes = relationship("RuntimeBinding", back_populates="model", cascade="all, delete-orphan")


class RuntimeBinding(Base):
    __tablename__ = "runtime_bindings"
    
    runtime_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    model_id = Column(String(64), ForeignKey("model_assets.model_id"), nullable=False, index=True)
    framework_version = Column(String(64), default="PyTorch-2.x")
    hardware_target = Column(String(64), default="CPU") # CPU, CUDA, TENSORRT, ONNXRUNTIME
    quantization = Column(String(32), default="FP32") # FP32, FP16, INT8
    batch_size = Column(Integer, default=1)
    config_digest = Column(String(64), nullable=False, index=True)
    metadata_json = Column(Text, default="{}")
    created_at = Column(String(64), default=utc_now_iso)

    case = relationship("Case", back_populates="runtimes")
    model = relationship("ModelAsset", back_populates="runtimes")


class InferenceRecord(Base):
    __tablename__ = "inference_records"
    
    inference_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    dataset_id = Column(String(64), nullable=True, index=True)
    sample_id = Column(String(64), nullable=True, index=True)
    model_id = Column(String(64), nullable=True, index=True)
    runtime_id = Column(String(64), nullable=True, index=True)
    model_digest = Column(String(64), nullable=True)
    configuration_digest = Column(String(64), nullable=True)
    input_sha256 = Column(String(64), nullable=False)
    model_sha256 = Column(String(64), nullable=False)
    preprocess_sha256 = Column(String(64), nullable=False)
    config_sha256 = Column(String(64), nullable=False)
    output_sha256 = Column(String(64), nullable=False)
    sequence = Column(Integer, default=1)
    timestamp = Column(String(64), default=utc_now_iso)
    nonce = Column(String(64), nullable=False, index=True)
    previous_record_hash = Column(String(64), nullable=False)
    signature = Column(Text, nullable=False)
    signer = Column(String(128), default="edge_drone_01")
    verification_status = Column(String(64), default="UNVERIFIED", index=True) # VERIFIED, TAMPERED, REPLAY_DETECTED, INVALID_SIGNATURE
    evidence_label = Column(String(32), default="SYNTHETIC", index=True) # REAL_PUBLIC, SYNTHETIC, DERIVED, DEMO
    predictions_json = Column(Text, default="{}") # classes, boxes, confidences
    operational_metadata_json = Column(Text, default="{}") # sensor, illumination, terrain, weather

    case = relationship("Case", back_populates="inferences")


class Finding(Base):
    __tablename__ = "findings"
    
    finding_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True) # dataset_id, model_id, or inference_id
    asset_type = Column(String(64), default="DATASET", index=True) # DATASET, MODEL, INFERENCE, RUNTIME
    detector_id = Column(String(64), nullable=False, index=True)
    detector_version = Column(String(32), default="1.0.0")
    finding_type = Column(String(64), nullable=False, index=True) # DUPLICATE_SAMPLE, LABEL_FLIP, BACKDOOR_TRIGGER, SIGNATURE_MISMATCH, etc.
    severity = Column(String(32), default="MEDIUM", index=True) # CRITICAL, HIGH, MEDIUM, LOW, INFO
    confidence = Column(Float, nullable=True) # null for deterministic checks
    deterministic = Column(Boolean, default=False)
    status = Column(String(32), default="FINDING", index=True) # VERIFIED, FINDING, NOT_TESTED, INCONCLUSIVE, NOT_APPLICABLE, PASS
    explanation = Column(Text, nullable=False)
    limitations = Column(Text, nullable=True)
    created_at = Column(String(64), default=utc_now_iso, index=True)

    case = relationship("Case", back_populates="findings")
    evidence_items = relationship("Evidence", back_populates="finding", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence_items"
    
    evidence_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    finding_id = Column(String(64), ForeignKey("findings.finding_id"), nullable=True, index=True)
    target_type = Column(String(64), default="DATASET")
    target_id = Column(String(64), nullable=False, index=True)
    lifecycle_stage = Column(String(64), nullable=False, index=True) # CONTRIBUTOR, DATASET, MODEL, RUNTIME, INFERENCE, CRYPTO, SYSTEM
    detector_id = Column(String(64), nullable=False, index=True)
    finding_type = Column(String(64), default="INTEGRITY_CHECK")
    evidence_type = Column(String(64), nullable=False, index=True) # CRYPTOGRAPHIC, STATISTICAL, BEHAVIORAL, METADATA
    severity = Column(String(32), default="INFO", index=True)
    status = Column(String(32), default="FINDING") # VERIFIED, FINDING, NOT_TESTED, INCONCLUSIVE, NOT_APPLICABLE
    source_asset = Column(String(64), nullable=False)
    detector = Column(String(64), nullable=False)
    observation = Column(Text, nullable=False)
    measurement_json = Column(Text, default="{}")
    confidence = Column(Float, nullable=True)
    deterministic = Column(Boolean, default=False)
    supporting_artifact = Column(String(512), nullable=True)
    artifact_digest = Column(String(64), nullable=True)
    limitations = Column(Text, nullable=True)
    timestamp = Column(String(64), default=utc_now_iso, index=True)
    sha256 = Column(String(64), nullable=False)

    case = relationship("Case", back_populates="evidence_items")
    finding = relationship("Finding", back_populates="evidence_items")


class EvidenceEdge(Base):
    __tablename__ = "evidence_edges"
    
    edge_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    source_node = Column(String(64), nullable=False, index=True) # e.g. "contributor:C-07"
    target_node = Column(String(64), nullable=False, index=True) # e.g. "dataset:D-14"
    relationship = Column(String(64), nullable=False) # contributed_by, contains, trained_from, produced, deviates_from, supports, correlates_with
    epistemic_status = Column(String(32), default="OBSERVED") # OBSERVED, DERIVED, SUPPORTS, CORRELATES, UNKNOWN
    evidence_ids_json = Column(Text, default="[]")

    case = orm_rel("Case", back_populates="evidence_edges")


class AssuranceCase(Base):
    __tablename__ = "assurance_cases"
    
    assurance_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    claim = Column(Text, nullable=False)
    status = Column(String(64), default="REVIEW_REQUIRED", index=True) # VERIFIED, REVIEW_REQUIRED, QUARANTINED, INCONCLUSIVE
    recommended_disposition = Column(String(64), default="REVIEW", index=True) # ACCEPT, REVIEW, QUARANTINE
    human_disposition = Column(String(64), nullable=True, index=True) # APPROVED_ACCEPT, APPROVED_REVIEW, APPROVED_QUARANTINE, OVERRIDDEN
    approved_by = Column(String(128), nullable=True)
    approved_at = Column(String(64), nullable=True)
    approval_notes = Column(Text, nullable=True)
    supporting_evidence_json = Column(Text, default="[]")
    counter_evidence_json = Column(Text, default="[]")
    coverage_json = Column(Text, default="{}")
    limitations_json = Column(Text, default="[]")
    # Evidence that justifies the recommendation (CRITICAL/HIGH/MEDIUM findings)
    incriminating_evidence_json = Column(Text, default="[]")
    # Multi-path convergence analysis produced by the policy engine
    convergence_json = Column(Text, default="{}")
    # Who triggered this evaluation (used to block self-approval)
    initiated_by = Column(String(128), nullable=True, index=True)
    policy_version = Column(String(32), default="DRISHTRA-AP-2026.1")
    created_at = Column(String(64), default=utc_now_iso, index=True)

    case = relationship("Case", back_populates="assurance_cases")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    
    event_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    sequence = Column(Integer, default=1, index=True)
    actor = Column(String(128), nullable=False) # username or automated detector agent
    action = Column(String(128), nullable=False, index=True) # CASE_CREATED, DATASET_SCANNED, etc.
    asset_id = Column(String(64), nullable=True, index=True)
    result = Column(String(64), nullable=False, index=True) # SUCCESS, FAILURE, TAMPER_DETECTED, QUARANTINED
    reason = Column(Text, nullable=True)
    timestamp = Column(String(64), default=utc_now_iso, index=True)
    previous_event_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False, index=True)
    signature = Column(Text, nullable=True)

    case = relationship("Case", back_populates="audit_events")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    
    run_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    status = Column(String(32), default="RUNNING", index=True) # RUNNING, COMPLETED, FAILED
    current_stage = Column(String(64), default="STAGE_01_CASE_VALIDATION")
    stages_json = Column(Text, default="[]")
    started_at = Column(String(64), default=utc_now_iso)
    completed_at = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)

    case = relationship("Case", back_populates="pipeline_runs")


class AssuranceRun(Base):
    __tablename__ = "assurance_runs"

    assurance_run_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    dataset_id = Column(String(64), nullable=True, index=True)
    model_id = Column(String(64), nullable=True, index=True)
    execution_mode = Column(String(32), default="OFFLINE", index=True)
    status = Column(String(64), default="CREATED", index=True)
    current_stage = Column(String(64), default="INGEST")
    detector_versions_json = Column(Text, default="{}")
    policy_version = Column(String(64), default="DRISHTRA-AP-2026.1")
    dataset_version = Column(String(64), default="1.0.0")
    model_version = Column(String(64), default="1.0.0")
    input_hashes_json = Column(Text, default="{}")
    output_hashes_json = Column(Text, default="{}")
    errors_json = Column(Text, default="[]")
    warnings_json = Column(Text, default="[]")
    coverage_json = Column(Text, default="{}")
    started_at = Column(String(64), default=utc_now_iso, index=True)
    completed_at = Column(String(64), nullable=True)

    case = relationship("Case", back_populates="assurance_runs")


# =============================================================================
# Identity, governance and accountability
# =============================================================================

class User(Base):
    """
    Internal operator account. Accounts are created only by an ADMINISTRATOR
    (there is no public self-registration). The role is stored here and is the
    only source of truth for authorization - it is never taken from a request.
    """
    __tablename__ = "users"

    user_id = Column(String(64), primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, index=True)
    # Prototype access classification (maps to institutional policy later)
    access_scope = Column(String(32), default="INTERNAL")  # PUBLIC, INTERNAL, RESTRICTED, SENSITIVE
    status = Column(String(16), default="ACTIVE", index=True)  # ACTIVE, DISABLED
    password_hash = Column(String(256), nullable=False)
    must_change_password = Column(Boolean, default=True)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(String(64), nullable=True)
    token_version = Column(Integer, default=1)  # bump to revoke all sessions
    created_by = Column(String(64), nullable=True)
    created_at = Column(String(64), default=utc_now_iso)
    last_login_at = Column(String(64), nullable=True)
    is_demo_account = Column(Boolean, default=False)


class PlatformEvent(Base):
    """
    Platform-level, hash-chained ledger for events that are not tied to one case:
    identity lifecycle, authentication, authorization denials, policy changes.
    Kept separate from AI integrity findings on purpose.
    """
    __tablename__ = "platform_events"

    event_id = Column(String(64), primary_key=True, index=True)
    sequence = Column(Integer, nullable=False, index=True, unique=True)
    category = Column(String(32), nullable=False, index=True)  # GOVERNANCE, AUTH, AUTHZ
    actor = Column(String(128), nullable=False, index=True)
    actor_role = Column(String(32), nullable=True)
    action = Column(String(64), nullable=False, index=True)
    target = Column(String(128), nullable=True, index=True)
    result = Column(String(32), nullable=False)  # SUCCESS, DENIED, FAILURE
    details_json = Column(Text, default="{}")
    request_id = Column(String(64), nullable=True)
    timestamp = Column(String(64), default=utc_now_iso, index=True)
    previous_event_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False)


class AssuranceDecision(Base):
    """
    Append-only record of human judgement on an assurance case.
    kind=RECOMMENDATION: a SECURITY_ANALYST's recommended disposition.
    kind=DISPOSITION:    a REVIEWER_SUPERVISOR's binding decision.
    Rows are never updated; a new decision supersedes the previous one.
    Each row is hash-linked to the previous decision on the case and signed
    with the node's Ed25519 key.
    """
    __tablename__ = "assurance_decisions"

    decision_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    assurance_id = Column(String(64), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    kind = Column(String(16), nullable=False, index=True)  # RECOMMENDATION, DISPOSITION
    disposition = Column(String(16), nullable=False)  # ACCEPT, REVIEW, QUARANTINE
    rationale = Column(Text, nullable=False)
    actor = Column(String(64), nullable=False, index=True)
    actor_role = Column(String(32), nullable=False)
    machine_recommendation = Column(String(16), nullable=True)
    supersedes_decision_id = Column(String(64), nullable=True)
    decided_at = Column(String(64), default=utc_now_iso)
    previous_decision_hash = Column(String(64), nullable=False)
    decision_hash = Column(String(64), nullable=False)
    signature = Column(Text, nullable=True)
    signer_key_fingerprint = Column(String(64), nullable=True)


class CheckExecution(Base):
    """
    One execution of one integrity check against one asset.

    This is what makes coverage honest: a dimension is VERIFIED only when a
    check actually ran and passed, FINDING when it ran and flagged, and
    NOT_TESTED when nothing ran. Counter-evidence is drawn only from PASS rows.
    """
    __tablename__ = "check_executions"

    execution_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    asset_type = Column(String(32), nullable=False, index=True)  # DATASET, MODEL, INFERENCE
    asset_id = Column(String(64), nullable=False, index=True)
    check_id = Column(String(48), nullable=False, index=True)    # e.g. D2_NEAR_DUPLICATE
    detector_id = Column(String(64), nullable=False)
    detector_version = Column(String(32), default="1.0.0")
    outcome = Column(String(16), nullable=False, index=True)     # PASS, FINDING, NOT_TESTED, INCONCLUSIVE
    detail = Column(Text, nullable=True)
    finding_ids_json = Column(Text, default="[]")
    input_digest = Column(String(64), nullable=True)
    actor = Column(String(128), nullable=True)
    executed_at = Column(String(64), default=utc_now_iso, index=True)
