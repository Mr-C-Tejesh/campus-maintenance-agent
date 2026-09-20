from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

VALID_FEEDBACK_VALUES = {"Correct", "Incorrect"}

@dataclass
class FeedbackRecord:
    feedback_id: str
    workflow_id: str
    complaint: str
    equipment_type: Optional[str]
    location: Optional[str]
    retrieved_case_ids: List[str]
    diagnosis_summary: Optional[str]
    recommended_action: Optional[str]
    technician_feedback: str  # "Correct" | "Incorrect"
    timestamp: str  # ISO 8601 UTC
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
