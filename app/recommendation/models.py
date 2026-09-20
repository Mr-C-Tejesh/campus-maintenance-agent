from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

VALID_URGENCY_LEVELS = {"Low", "Medium", "High", "Critical"}
SAFETY_DISCLAIMER_TEXT = (
    "DECISION SUPPORT ONLY: This recommendation is generated based on historical maintenance records "
    "and LLM reasoning. Physical inspection by a qualified technician is required before performing repairs."
)

@dataclass
class CostEstimate:
    min_cost: float
    max_cost: float
    median_cost: float
    supporting_case_ids: List[str]
    formatted_range: str
    formatted_reference: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class RepairTimeEstimate:
    min_hours: float
    max_hours: float
    median_hours: float
    supporting_case_ids: List[str]
    formatted_range: str
    formatted_reference: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class RecommendationResult:
    recommended_action: str
    estimated_cost: CostEstimate
    estimated_repair_time: RepairTimeEstimate
    urgency: str  # "Low" | "Medium" | "High" | "Critical"
    reasoning: str
    supporting_case_ids: List[str]
    technician_verification: List[str]
    grounded: bool
    safety_disclaimer: str = SAFETY_DISCLAIMER_TEXT
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["estimated_cost"] = self.estimated_cost.to_dict()
        d["estimated_repair_time"] = self.estimated_repair_time.to_dict()
        return d
