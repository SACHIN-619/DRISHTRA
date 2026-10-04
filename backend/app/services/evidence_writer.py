"""
Single place where detector output becomes persisted evidence.

record_check() takes a DetectorResult from any detector and writes:
  - one CheckExecution row (what ran, against what, with what outcome)
  - one Finding + one Evidence row per detector finding (idempotent per
    asset + check + finding_type, so re-running a scan does not duplicate)

All detectors therefore share one evidence contract, which is what lets the
assurance engine correlate them.
"""
import hashlib
import json
import uuid
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from app.db.models import CheckExecution, Evidence, Finding, utc_now_iso
from app.detectors.base import DetectorFinding, DetectorResult, DetectorStatus

# check_id -> (asset_type, human label, lifecycle stage)
CHECK_CATALOG = {
    "D1_EXACT_DUPLICATE":     ("DATASET",   "Exact duplicate samples",        "Byte-identical samples (SHA-256) flooding the dataset."),
    "D2_NEAR_DUPLICATE":      ("DATASET",   "Near-duplicate samples",         "Perceptual-hash clusters of visually identical images."),
    "D3_LABEL_CONSISTENCY":   ("DATASET",   "Label consistency",              "Same content carrying conflicting labels (poisoning)."),
    "D4_CLASS_BALANCE":       ("DATASET",   "Class balance",                  "Minority classes starved or skewed."),
    "D5_DISTRIBUTION_SHIFT":  ("DATASET",   "Distribution shift",             "Statistical drift against a reference distribution."),
    "D6_ANNOTATION_VALIDITY": ("DATASET",   "Annotation validity",            "Malformed boxes, invalid class ids, missing labels."),
    "D7_OUT_OF_DISTRIBUTION": ("DATASET",   "Out-of-distribution samples",    "Embedding-distance outliers vs the operational profile."),
    "D8A_WEIGHT_DIGEST":      ("MODEL",     "Model weight digest",            "Supplied weights match the registered SHA-256."),
    "D8B_BEHAVIOURAL_PROBE":  ("MODEL",     "Behavioural probe battery",      "Black-box probes for trigger susceptibility / instability."),
    "D8C_WHITE_BOX_ANALYSIS": ("MODEL",     "White-box trigger reconstruction", "Requires internal weights/activations."),
    "D9A_SIGNATURE_BINDING":  ("INFERENCE", "Signature & input/model binding", "Ed25519 signature over input, model, config and output digests."),
    "D9B_REPLAY_SEQUENCE":    ("INFERENCE", "Replay & sequence",              "Nonce freshness and monotonic sequence."),
}

_STATUS_TO_OUTCOME = {
    DetectorStatus.PASS: "PASS",
    DetectorStatus.FINDING: "FINDING",
    DetectorStatus.NOT_AVAILABLE: "NOT_TESTED",
    DetectorStatus.INCONCLUSIVE: "INCONCLUSIVE",
    DetectorStatus.ERROR: "INCONCLUSIVE",
}


def _upsert_finding(
    db: Session, case_id: str, asset_type: str, asset_id: str,
    detector_id: str, detector_version: str, df: DetectorFinding,
    lifecycle_stage: str, limitations: Optional[str],
) -> Finding:
    existing = db.query(Finding).filter(
        Finding.case_id == case_id,
        Finding.asset_id == asset_id,
        Finding.detector_id == detector_id,
        Finding.finding_type == df.finding_type,
    ).first()
    if existing:
        return existing
    f_id = f"FND-{uuid.uuid4().hex[:8].upper()}"
    finding = Finding(
        finding_id=f_id, case_id=case_id, asset_id=asset_id, asset_type=asset_type,
        detector_id=detector_id, detector_version=detector_version,
        finding_type=df.finding_type, severity=df.severity, confidence=df.confidence,
        deterministic=bool(df.deterministic), status="FINDING",
        explanation=df.explanation, limitations=limitations, created_at=utc_now_iso(),
    )
    db.add(finding)
    measurement = df.measurement or df.observations or {}
    db.add(Evidence(
        evidence_id=f"EVD-{uuid.uuid4().hex[:8].upper()}", case_id=case_id, finding_id=f_id,
        target_type=asset_type, target_id=asset_id, lifecycle_stage=lifecycle_stage,
        detector_id=detector_id, detector=detector_id, finding_type=df.finding_type,
        evidence_type=df.evidence_type or "STATISTICAL", severity=df.severity, status="FINDING",
        source_asset=asset_id, observation=df.observation or df.explanation,
        measurement_json=json.dumps(measurement, default=str),
        confidence=df.confidence, deterministic=bool(df.deterministic),
        supporting_artifact=df.supporting_artifact, artifact_digest=df.artifact_digest,
        limitations=limitations, timestamp=utc_now_iso(),
        sha256=hashlib.sha256(json.dumps(measurement, sort_keys=True, default=str).encode()).hexdigest(),
    ))
    return finding


def record_check(
    db: Session,
    case_id: str,
    asset_type: str,
    asset_id: str,
    check_id: str,
    result: DetectorResult,
    actor: str = "system",
    input_digest: Optional[str] = None,
    only_finding_types: Optional[Iterable[str]] = None,
    exclude_finding_types: Optional[Iterable[str]] = None,
    detail: Optional[str] = None,
) -> List[Finding]:
    """
    Persist one detector result as a check execution (+ findings).
    only_/exclude_finding_types let one detector run feed two coverage
    dimensions (e.g. the replay detector covers signature AND sequence).
    """
    findings_in = list(result.findings or [])
    if only_finding_types is not None:
        allowed = set(only_finding_types)
        findings_in = [f for f in findings_in if f.finding_type in allowed]
    if exclude_finding_types is not None:
        blocked = set(exclude_finding_types)
        findings_in = [f for f in findings_in if f.finding_type not in blocked]

    base_outcome = _STATUS_TO_OUTCOME.get(result.status, "INCONCLUSIVE")
    if base_outcome in ("PASS", "FINDING"):
        outcome = "FINDING" if findings_in else "PASS"
    else:
        outcome = base_outcome

    limitations = "; ".join(result.limitations) if result.limitations else None
    persisted: List[Finding] = []
    for df in findings_in:
        persisted.append(_upsert_finding(
            db, case_id, asset_type, asset_id, result.detector_id, result.detector_version,
            df, asset_type, "; ".join(df.limitations) if df.limitations else limitations,
        ))
    db.flush()

    if detail is None:
        if outcome == "PASS":
            detail = f"{CHECK_CATALOG.get(check_id, (None, check_id))[1]}: no anomaly observed."
        elif outcome == "FINDING":
            detail = "; ".join(sorted({f.finding_type for f in findings_in}))
        else:
            detail = limitations or "Check could not be evaluated with the inputs provided."

    db.add(CheckExecution(
        execution_id=f"CHK-{uuid.uuid4().hex[:10].upper()}",
        case_id=case_id, asset_type=asset_type, asset_id=asset_id, check_id=check_id,
        detector_id=result.detector_id, detector_version=result.detector_version,
        outcome=outcome, detail=detail,
        finding_ids_json=json.dumps([f.finding_id for f in persisted]),
        input_digest=input_digest, actor=actor, executed_at=utc_now_iso(),
    ))
    db.commit()
    return persisted


def record_not_applicable(
    db: Session, case_id: str, asset_type: str, asset_id: str, check_id: str,
    reason: str, actor: str = "system",
) -> None:
    db.add(CheckExecution(
        execution_id=f"CHK-{uuid.uuid4().hex[:10].upper()}",
        case_id=case_id, asset_type=asset_type, asset_id=asset_id, check_id=check_id,
        detector_id="coverage_declaration", outcome="NOT_APPLICABLE", detail=reason,
        actor=actor, executed_at=utc_now_iso(),
    ))
    db.commit()
