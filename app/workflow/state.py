from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, TypedDict
from app.retrieval.retriever import RetrievalResult
from app.diagnosis.models import DiagnosisResult
from app.recommendation.models import RecommendationResult

VALID_WORKFLOW_STATUSES = {
    "SUCCESS",
    "NO_RELEVANT_CASES",
    "INVALID_INPUT",
    "RETRIEVAL_FAILED",
    "DIAGNOSIS_FAILED",
    "RECOMMENDATION_FAILED",
    "FAILED"
}

@dataclass
class WorkflowResult:
    complaint: str
    equipment_type: Optional[str]
    retrieved_cases: List[RetrievalResult]
    diagnosis: Optional[DiagnosisResult]
    recommendation: Optional[RecommendationResult]
    workflow_status: str
    error: Optional[str] = None
    workflow_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "complaint": self.complaint,
            "equipment_type": self.equipment_type,
            "retrieved_cases": [c.to_dict() for c in self.retrieved_cases],
            "diagnosis": self.diagnosis.to_dict() if self.diagnosis else None,
            "recommendation": self.recommendation.to_dict() if self.recommendation else None,
            "workflow_status": self.workflow_status,
            "error": self.error
        }

class GraphState(TypedDict):
    complaint: str
    equipment_type: Optional[str]
    retrieved_cases: List[RetrievalResult]
    diagnosis: Optional[DiagnosisResult]
    recommendation: Optional[RecommendationResult]
    workflow_status: str
    error: Optional[str]
    workflow_id: Optional[str]

