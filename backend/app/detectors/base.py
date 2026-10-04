"""
DRISHTRA Detector Framework - Base Interface
Standardized interface for all computer vision, model, and inference integrity detectors.
Every detector declares its access assumptions, execution status, and explicit limitations.
All findings adhere to the standardized evidence contract.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, timezone

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class DetectorStatus(str, Enum):
    PASS = "PASS"
    FINDING = "FINDING"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    INCONCLUSIVE = "INCONCLUSIVE"
    ERROR = "ERROR"

class AccessRequirement(str, Enum):
    DATA_ONLY = "DATA_ONLY"
    BLACK_BOX = "BLACK_BOX"
    GREY_BOX = "GREY_BOX"
    WHITE_BOX = "WHITE_BOX"

class DetectorFinding(BaseModel):
    finding_id: Optional[str] = None
    detector_id: Optional[str] = None
    finding_type: str
    severity: str = "MEDIUM" # CRITICAL, HIGH, MEDIUM, LOW, INFO
    target_artifact: Optional[str] = None
    evidence_type: str = "CRYPTOGRAPHIC" # CRYPTOGRAPHIC, STATISTICAL, BEHAVIORAL, METADATA
    confidence: Optional[float] = None # None for deterministic checks
    deterministic: bool = False
    explanation: str
    observation: str
    observations: Dict[str, Any] = {}
    measurement: Dict[str, Any] = {}
    supporting_artifact: Optional[str] = None
    artifact_digest: Optional[str] = None
    limitations: List[str] = []
    created_at: str = Field(default_factory=utc_now_iso)

class DetectorResult(BaseModel):
    detector_id: str
    detector_version: str
    status: DetectorStatus
    findings: List[DetectorFinding] = []
    limitations: List[str] = []
    execution_time_ms: float = 0.0

class BaseDetector(ABC):
    detector_id: str = "base_detector"
    detector_version: str = "1.0.0"
    required_access: AccessRequirement = AccessRequirement.DATA_ONLY
    supported_inputs: List[str] = []

    @abstractmethod
    def run(self, **kwargs) -> DetectorResult:
        """
        Execute detection algorithm against provided assets.
        Must return a structured DetectorResult without raising uncaught exceptions.
        """
        pass
