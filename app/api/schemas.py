from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any

ALLOWED_EQUIPMENT = {"Air Conditioning", "Generator", "Elevator"}
ALLOWED_FEEDBACK = {"Correct", "Incorrect"}

class AnalyzeRequest(BaseModel):
    complaint: str = Field(..., min_length=3, max_length=1000, description="The maintenance complaint text.")
    equipment_type: Optional[str] = Field(None, description="Optional equipment category: 'Air Conditioning', 'Generator', or 'Elevator'.")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Maximum number of historical cases to retrieve.")

    @field_validator("complaint")
    @classmethod
    def validate_complaint_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Complaint cannot be empty or whitespace only.")
        return v.strip()

    @field_validator("equipment_type")
    @classmethod
    def validate_equipment_type(cls, v):
        if v is not None and v not in ALLOWED_EQUIPMENT:
            raise ValueError(f"Unsupported equipment_type '{v}'. Allowed types: {sorted(list(ALLOWED_EQUIPMENT))}")
        return v

class FeedbackSubmitRequest(BaseModel):
    workflow_id: str = Field(..., min_length=1, description="The unique workflow execution identifier.")
    feedback: str = Field(..., description="Technician feedback: 'Correct' or 'Incorrect'.")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional technician comments or notes.")

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, v):
        if v not in ALLOWED_FEEDBACK:
            raise ValueError(f"Invalid feedback value '{v}'. Must be exactly 'Correct' or 'Incorrect'.")
        return v

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "Campus/Facility Infrastructure Decision-Support Agent"
    version: str = "1.0.0"

