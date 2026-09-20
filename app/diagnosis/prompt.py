import json
from typing import List, Optional
from app.retrieval.retriever import RetrievalResult

SYSTEM_INSTRUCTIONS = """You are an expert Campus & Facility Infrastructure Maintenance Diagnosis Assistant.
Your task is to analyze a new maintenance complaint using ONLY the provided retrieved historical cases as authoritative evidence.

CRITICAL RULES FOR GROUNDING:
1. You MUST ONLY cite historical case IDs that are explicitly listed in the provided RETRIEVED HISTORICAL CASES.
2. NEVER invent, fabricate, or hallucinate case IDs or historical maintenance records.
3. Distinguish clearly between:
   - HISTORICAL EVIDENCE: Verified facts directly reported in the cited case IDs (e.g. symptoms, root cause, action taken).
   - INFERENCE: Your technical reasoning linking the new complaint symptoms to the historical evidence.
4. Set confidence to "High", "Medium", or "Low" based strictly on evidence strength.
5. If the evidence is weak or sparse, set confidence to "Low" and emphasize technician physical inspection.

OUTPUT FORMAT:
Return ONLY valid JSON matching this exact JSON schema:
{
  "summary": "Short 1-2 sentence diagnostic summary.",
  "possible_causes": [
    {
      "cause": "Diagnosed root cause or failure mode",
      "likelihood": "High | Medium | Low",
      "supporting_case_ids": ["CASE-XXXX"],
      "explanation": "Detailed explanation linking complaint to historical evidence."
    }
  ],
  "evidence": [
    {
      "case_id": "CASE-XXXX",
      "fact": "Fact taken directly from historical case record."
    }
  ],
  "reasoning": "Explicit explanation connecting historical evidence to the current complaint and distinguishing evidence vs model inference.",
  "confidence": "High | Medium | Low",
  "technician_checks": [
    "Step 1 physical verification recommended for technician..."
  ],
  "historical_case_ids": ["CASE-XXXX"]
}
"""

def build_diagnosis_prompt(
    complaint: str,
    retrieved_cases: List[RetrievalResult],
    equipment_type: Optional[str] = None
) -> str:
    """
    Constructs a deterministic prompt for the Gemini LLM containing the complaint and retrieved evidence.
    """
    formatted_cases = []
    for c in retrieved_cases:
        formatted_cases.append({
            "case_id": c.case_id,
            "equipment_type": c.equipment_type,
            "equipment_model": c.equipment_model,
            "location": c.location,
            "complaint": c.complaint,
            "symptoms": c.symptoms,
            "root_cause": c.root_cause,
            "action_taken": c.action_taken,
            "urgency": c.urgency,
            "similarity_score": c.similarity_score
        })

    prompt_data = {
        "new_complaint": complaint.strip(),
        "equipment_type_filter": equipment_type or "Unspecified",
        "retrieved_historical_cases": formatted_cases
    }

    return (
        f"{SYSTEM_INSTRUCTIONS}\n\n"
        f"INPUT DATA:\n"
        f"```json\n"
        f"{json.dumps(prompt_data, indent=2)}\n"
        f"```\n\n"
        f"Generate the grounded diagnosis JSON now:"
    )
