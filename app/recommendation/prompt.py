import json
from typing import List, Optional
from app.retrieval.retriever import RetrievalResult
from app.diagnosis.models import DiagnosisResult
from app.recommendation.models import CostEstimate, RepairTimeEstimate

SYSTEM_INSTRUCTIONS = """You are an expert Facility & Infrastructure Maintenance Recommendation Assistant.
Your job is to formulate a clear, actionable maintenance recommendation for technicians based on a new complaint, a verified diagnosis, and historical case evidence.

CRITICAL CONSTRAINTS:
1. DO NOT invent numerical costs or repair durations. Use the provided historical cost and time references.
2. DO NOT cite historical case IDs that were not explicitly supplied.
3. Express recommendations as DECISION SUPPORT guidance for technicians, emphasizing physical verification.

OUTPUT FORMAT:
Return ONLY valid JSON matching this exact JSON schema:
{
  "recommended_action": "Clear 1-2 sentence technician recommended action.",
  "reasoning": "Explanation linking the diagnosis, complaint, and historical cases to this action.",
  "supporting_case_ids": ["CASE-XXXX"],
  "technician_verification": [
    "Step 1 physical check before repair..."
  ]
}
"""

def build_recommendation_prompt(
    complaint: str,
    diagnosis: Optional[DiagnosisResult],
    retrieved_cases: List[RetrievalResult],
    cost_estimate: CostEstimate,
    time_estimate: RepairTimeEstimate,
    urgency: str
) -> str:
    """
    Builds a structured prompt for LLM recommendation synthesis.
    """
    formatted_cases = [
        {
            "case_id": c.case_id,
            "equipment_type": c.equipment_type,
            "complaint": c.complaint,
            "root_cause": c.root_cause,
            "action_taken": c.action_taken
        }
        for c in retrieved_cases
    ]

    diagnosis_summary = diagnosis.summary if diagnosis else "No diagnosis available."
    diagnosis_causes = [
        {"cause": pc.cause, "likelihood": pc.likelihood, "supporting_case_ids": pc.supporting_case_ids}
        for pc in (diagnosis.possible_causes if diagnosis else [])
    ]

    prompt_data = {
        "complaint": complaint.strip(),
        "diagnosis_summary": diagnosis_summary,
        "diagnosed_possible_causes": diagnosis_causes,
        "determined_urgency": urgency,
        "historical_cost_reference": cost_estimate.formatted_reference,
        "historical_duration_reference": time_estimate.formatted_reference,
        "retrieved_cases": formatted_cases
    }

    return (
        f"{SYSTEM_INSTRUCTIONS}\n\n"
        f"INPUT DATA:\n"
        f"```json\n"
        f"{json.dumps(prompt_data, indent=2)}\n"
        f"```\n\n"
        f"Generate the structured recommendation JSON now:"
    )
