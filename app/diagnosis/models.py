from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

VALID_CONFIDENCE_LEVELS = {"High", "Medium", "Low"}

@dataclass
class PossibleCause:
    cause: str
    likelihood: str  # "High" | "Medium" | "Low"
    supporting_case_ids: List[str]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class EvidenceItem:
    case_id: str
    fact: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class DiagnosisResult:
    summary: str
    possible_causes: List[PossibleCause]
    evidence: List[EvidenceItem]
    reasoning: str
    confidence: str  # "High" | "Medium" | "Low"
    technician_checks: List[str]
    historical_case_ids: List[str]
    grounded: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["possible_causes"] = [pc.to_dict() for pc in self.possible_causes]
        d["evidence"] = [e.to_dict() for e in self.evidence]
        return d
