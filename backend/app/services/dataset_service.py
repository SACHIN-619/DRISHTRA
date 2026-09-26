"""
DRISHTRA Dataset Sentinel Service
Dataset Ingestion, Manifest Fingerprinting, Integrity Scanning, and Evidence Harvesting.
"""
import uuid
import json
import hashlib
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import Dataset, DatasetVersion, Finding, Evidence, EvidenceEdge, utc_now_iso
from app.schemas.all_schemas import DatasetRegister
from app.crypto.hashing import sha256_canonical_dict
from app.detectors.duplicate_detector import ExactDuplicateDetector, NearDuplicateDetector
from app.detectors.label_anomaly_detector import LabelAnomalyDetector
from app.services.audit_service import AuditService

class DatasetService:
    @staticmethod
    def register_dataset(db: Session, data_in: DatasetRegister, actor: str = "analyst") -> Dataset:
        dataset_id = f"D-{uuid.uuid4().hex[:6].upper()}"
        
        # Compute deterministic manifest digest
        manifest = {
            "name": data_in.name,
            "format": data_in.format,
            "version": data_in.version,
            "sample_count": data_in.sample_count,
            "contributor_id": data_in.contributor_id,
            "metadata": data_in.metadata or {}
        }
        manifest_digest = sha256_canonical_dict(manifest)
        
        # Synthetic / mock file hash if location not physical
        file_digest = hashlib.sha256(f"{dataset_id}:{manifest_digest}".encode('utf-8')).hexdigest()

        dataset = Dataset(
            dataset_id=dataset_id,
            case_id=data_in.case_id,
            contributor_id=data_in.contributor_id,
            name=data_in.name,
            format=data_in.format,
            version=data_in.version,
            location=data_in.location,
            sha256=file_digest,
            manifest_hash=manifest_digest,
            sample_count=data_in.sample_count,
            metadata_json=json.dumps(data_in.metadata or {}),
            created_at=utc_now_iso()
        )
        db.add(dataset)
        
        # Record initial version
        v_id = f"DV-{uuid.uuid4().hex[:6].upper()}"
        version_rec = DatasetVersion(
            dataset_version_id=v_id,
            dataset_id=dataset_id,
            version=data_in.version,
            sha256=file_digest,
            manifest_hash=manifest_digest,
            created_at=utc_now_iso()
        )
        db.add(version_rec)

        # Record edge: Contributor -> Dataset
        edge_id = f"EDGE-{uuid.uuid4().hex[:8].upper()}"
        edge = EvidenceEdge(
            edge_id=edge_id,
            case_id=data_in.case_id,
            source_node=f"contributor:{data_in.contributor_id}",
            target_node=f"dataset:{dataset_id}",
            relationship="contributed_by",
            epistemic_status="OBSERVED",
            evidence_ids_json="[]"
        )
        db.add(edge)
        db.commit()
        db.refresh(dataset)

        AuditService.record_event(
            db=db,
            case_id=data_in.case_id,
            actor=actor,
            action="DATASET_REGISTERED",
            asset_id=dataset_id,
            result="SUCCESS",
            reason=f"Registered dataset '{dataset.name}' (Manifest: {manifest_digest[:16]}...)"
        )
        return dataset

    @staticmethod
    def scan_dataset(db: Session, dataset_id: str, samples: List[Dict[str, Any]], actor: str = "analyst") -> List[Finding]:
        dataset = db.query(Dataset).filter(Dataset.dataset_id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        created_findings = []

        # 1. Run Exact Duplicate Detector
        exact_det = ExactDuplicateDetector()
        res_exact = exact_det.run(samples=samples)
        for df in res_exact.findings:
            f_id = f"FND-{uuid.uuid4().hex[:8].upper()}"
            finding = Finding(
                finding_id=f_id,
                case_id=dataset.case_id,
                asset_id=dataset_id,
                asset_type="DATASET",
                detector_id=exact_det.detector_id,
                detector_version=exact_det.detector_version,
                finding_type=df.finding_type,
                severity=df.severity,
                confidence=df.confidence,
                status="FINDING",
                explanation=df.explanation,
                limitations=exact_det.supported_inputs[0],
                created_at=utc_now_iso()
            )
            db.add(finding)
            
            # Evidence
            ev_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
            ev = Evidence(
                evidence_id=ev_id,
                case_id=dataset.case_id,
                finding_id=f_id,
                evidence_type="CRYPTOGRAPHIC",
                source_asset=dataset_id,
                detector=exact_det.detector_id,
                observation=df.observation,
                measurement_json=json.dumps(df.measurement),
                confidence=df.confidence,
                timestamp=utc_now_iso(),
                sha256=hashlib.sha256(json.dumps(df.measurement).encode('utf-8')).hexdigest()
            )
            db.add(ev)
            created_findings.append(finding)

        # 2. Run Near-Duplicate Detector
        near_det = NearDuplicateDetector()
        res_near = near_det.run(samples=samples)
        for df in res_near.findings:
            f_id = f"FND-{uuid.uuid4().hex[:8].upper()}"
            finding = Finding(
                finding_id=f_id,
                case_id=dataset.case_id,
                asset_id=dataset_id,
                asset_type="DATASET",
                detector_id=near_det.detector_id,
                detector_version=near_det.detector_version,
                finding_type=df.finding_type,
                severity=df.severity,
                confidence=df.confidence,
                status="FINDING",
                explanation=df.explanation,
                limitations=res_near.limitations,
                created_at=utc_now_iso()
            )
            db.add(finding)
            
            ev_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
            ev = Evidence(
                evidence_id=ev_id,
                case_id=dataset.case_id,
                finding_id=f_id,
                evidence_type="STATISTICAL",
                source_asset=dataset_id,
                detector=near_det.detector_id,
                observation=df.observation,
                measurement_json=json.dumps(df.measurement),
                confidence=df.confidence,
                timestamp=utc_now_iso(),
                sha256=hashlib.sha256(json.dumps(df.measurement).encode('utf-8')).hexdigest()
            )
            db.add(ev)
            created_findings.append(finding)

        # 3. Run Label Anomaly Detector
        label_det = LabelAnomalyDetector()
        res_label = label_det.run(samples=samples)
        for df in res_label.findings:
            f_id = f"FND-{uuid.uuid4().hex[:8].upper()}"
            finding = Finding(
                finding_id=f_id,
                case_id=dataset.case_id,
                asset_id=dataset_id,
                asset_type="DATASET",
                detector_id=label_det.detector_id,
                detector_version=label_det.detector_version,
                finding_type=df.finding_type,
                severity=df.severity,
                confidence=df.confidence,
                status="FINDING",
                explanation=df.explanation,
                limitations=res_label.limitations,
                created_at=utc_now_iso()
            )
            db.add(finding)
            
            ev_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
            ev = Evidence(
                evidence_id=ev_id,
                case_id=dataset.case_id,
                finding_id=f_id,
                evidence_type="STATISTICAL",
                source_asset=dataset_id,
                detector=label_det.detector_id,
                observation=df.observation,
                measurement_json=json.dumps(df.measurement),
                confidence=df.confidence,
                timestamp=utc_now_iso(),
                sha256=hashlib.sha256(json.dumps(df.measurement).encode('utf-8')).hexdigest()
            )
            db.add(ev)
            created_findings.append(finding)

        db.commit()

        AuditService.record_event(
            db=db,
            case_id=dataset.case_id,
            actor=actor,
            action="DATASET_SCANNED",
            asset_id=dataset_id,
            result="COMPLETED",
            reason=f"Executed integrity battery on {len(samples)} samples; produced {len(created_findings)} findings."
        )
        return created_findings
