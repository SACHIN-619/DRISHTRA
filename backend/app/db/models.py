"""
DRISHTRA Relational Database Schema
High-Integrity Models for Cases, Contributors, Datasets, Models, Inferences,
Findings, Evidence Graph, Assurance Cases, and Tamper-Evident Audit Ledger.
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
    classification = Column(String(64), default="RESTRICTED") # UNCLASSIFIED, RESTRICTED, CONFIDENTIAL, SECRET
    status = Column(String(64), default="ACTIVE") # ACTIVE, ASSESSED, QUARANTINED, ARCHIVED
    created_at = Column(String(64), default=utc_now_iso)
    updated_at = Column(String(64), default=utc_now_iso)

    # Relationships
    contributors = relationship("Contributor", back_populates="case", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="case", cascade="all, delete-orphan")
    models = relationship("ModelAsset", back_populates="case", cascade="all, delete-orphan")
    inferences = relationship("InferenceRecord", back_populates="case", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="case", cascade="all, delete-orphan")
    evidence_items = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    evidence_edges = relationship("EvidenceEdge", back_populates="case", cascade="all, delete-orphan")
    assurance_cases = relationship("AssuranceCase", back_populates="case", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="case", cascade="all, delete-orphan")

class Contributor(Base):
    __tablename__ = "contributors"
    
    contributor_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    contributor_type = Column(String(64), default="VENDOR") # VENDOR, LAB, FIELD_UNIT, OPEN_SOURCE, SYNTHETIC
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
    sha256 = Column(String(64), nullable=False)
    manifest_hash = Column(String(64), nullable=False)
    sample_count = Column(Integer, default=0)
    metadata_json = Column(Text, default="{}")
    created_at = Column(String(64), default=utc_now_iso)

    case = relationship("Case", back_populates="datasets")
    contributor = relationship("Contributor", back_populates="datasets")
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    
    dataset_version_id = Column(String(64), primary_key=True, index=True)
    dataset_id = Column(String(64), ForeignKey("datasets.dataset_id"), nullable=False, index=True)
    version = Column(String(64), nullable=False)
    sha256 = Column(String(64), nullable=False)
    manifest_hash = Column(String(64), nullable=False)
    created_at = Column(String(64), default=utc_now_iso)

    dataset = relationship("Dataset", back_populates="versions")

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
    weight_sha256 = Column(String(64), nullable=False)
    reference_model_id = Column(String(64), nullable=True)
    location = Column(String(512), nullable=True)
    access_level = Column(String(64), default="BLACK_BOX") # BLACK_BOX, WHITE_BOX, GREY_BOX
    created_at = Column(String(64), default=utc_now_iso)

    case = relationship("Case", back_populates="models")
    contributor = relationship("Contributor", back_populates="models")

class InferenceRecord(Base):
    __tablename__ = "inference_records"
    
    inference_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    model_id = Column(String(64), nullable=True)
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
    verification_status = Column(String(64), default="UNVERIFIED") # VERIFIED, TAMPERED, REPLAY_DETECTED, INVALID_SIGNATURE
    predictions_json = Column(Text, default="{}") # classes, boxes, confidences
    operational_metadata_json = Column(Text, default="{}") # sensor, illumination, terrain, weather

    case = relationship("Case", back_populates="inferences")

class Finding(Base):
    __tablename__ = "findings"
    
    finding_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True) # dataset_id, model_id, or inference_id
    asset_type = Column(String(64), default="DATASET") # DATASET, MODEL, INFERENCE
    detector_id = Column(String(64), nullable=False)
    detector_version = Column(String(32), default="1.0.0")
    finding_type = Column(String(64), nullable=False) # DUPLICATE_SAMPLE, LABEL_FLIP, BACKDOOR_TRIGGER, SIGNATURE_MISMATCH, etc.
    severity = Column(String(32), default="MEDIUM") # CRITICAL, HIGH, MEDIUM, LOW, INFO
    confidence = Column(Float, default=1.0)
    status = Column(String(32), default="FINDING") # PASS, FINDING, NOT_AVAILABLE, INCONCLUSIVE, ERROR
    explanation = Column(Text, nullable=False)
    limitations = Column(Text, nullable=True)
    created_at = Column(String(64), default=utc_now_iso)

    case = relationship("Case", back_populates="findings")
    evidence_items = relationship("Evidence", back_populates="finding", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = "evidence_items"
    
    evidence_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    finding_id = Column(String(64), ForeignKey("findings.finding_id"), nullable=True, index=True)
    evidence_type = Column(String(64), nullable=False) # CRYPTOGRAPHIC, STATISTICAL, BEHAVIORAL, METADATA
    source_asset = Column(String(64), nullable=False)
    detector = Column(String(64), nullable=False)
    observation = Column(Text, nullable=False)
    measurement_json = Column(Text, default="{}")
    confidence = Column(Float, default=1.0)
    supporting_artifact = Column(String(512), nullable=True)
    timestamp = Column(String(64), default=utc_now_iso)
    sha256 = Column(String(64), nullable=False)

    case = relationship("Case", back_populates="evidence_items")
    finding = relationship("Finding", back_populates="evidence_items")

class EvidenceEdge(Base):
    __tablename__ = "evidence_edges"
    
    edge_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    source_node = Column(String(64), nullable=False) # e.g. "contributor:C-07"
    target_node = Column(String(64), nullable=False) # e.g. "dataset:D-14"
    relationship = Column(String(64), nullable=False) # contributed_by, contains, trained_from, produced, deviates_from, supports, correlates_with
    epistemic_status = Column(String(32), default="OBSERVED") # OBSERVED, DERIVED, SUPPORTS, CORRELATES, UNKNOWN
    evidence_ids_json = Column(Text, default="[]")

    case = orm_rel("Case", back_populates="evidence_edges")

class AssuranceCase(Base):
    __tablename__ = "assurance_cases"
    
    assurance_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    claim = Column(Text, nullable=False)
    status = Column(String(64), default="REVIEW_REQUIRED") # VERIFIED, REVIEW_REQUIRED, QUARANTINED, INCONCLUSIVE
    recommended_disposition = Column(String(64), default="REVIEW") # ACCEPT, REVIEW, QUARANTINE
    supporting_evidence_json = Column(Text, default="[]")
    counter_evidence_json = Column(Text, default="[]")
    coverage_json = Column(Text, default="{}")
    limitations_json = Column(Text, default="[]")
    policy_version = Column(String(32), default="DRISHTRA-AP-2026.1")
    created_at = Column(String(64), default=utc_now_iso)

    case = relationship("Case", back_populates="assurance_cases")

class AuditEvent(Base):
    __tablename__ = "audit_events"
    
    event_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    actor = Column(String(128), nullable=False) # username or automated detector agent
    action = Column(String(128), nullable=False) # CASE_CREATED, DATASET_SCANNED, ASSURANCE_DISPOSITION_SET, etc.
    asset_id = Column(String(64), nullable=True)
    result = Column(String(64), nullable=False) # SUCCESS, FAILURE, TAMPER_DETECTED, QUARANTINED
    reason = Column(Text, nullable=True)
    timestamp = Column(String(64), default=utc_now_iso)
    previous_event_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False)
    signature = Column(Text, nullable=True)

    case = relationship("Case", back_populates="audit_events")
