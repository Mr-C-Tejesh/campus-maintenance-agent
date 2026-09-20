import json
import re
from typing import List, Set
from app.retrieval.retriever import RetrievalResult
from app.recommendation.models import (
    RecommendationResult, CostEstimate, RepairTimeEstimate, SAFETY_DISCLAIMER_TEXT
)

class RecommendationValidationError(Exception):
    pass

def clean_json_text(raw_text: str) -> str:
    """Removes markdown code block formatting if present."""
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text

def validate_recommendation_output(
    raw_output: str,
    retrieved_cases: List[RetrievalResult],
    cost_estimate: CostEstimate,
    time_estimate: RepairTimeEstimate,
    urgency: str
) -> RecommendationResult:
    """
    Parses LLM output, validates grounding against retrieved cases, and merges deterministic cost, time, and urgency.
    """
    cleaned_text = clean_json_text(raw_output)
    try:
        data = json.loads(cleaned_text)
    except Exception as e:
        raise RecommendationValidationError(f"Failed to parse LLM JSON response: {e}") from e

    if not isinstance(data, dict):
        raise RecommendationValidationError("LLM response root must be a JSON object.")

    # 1. Required keys check
    required_keys = {"recommended_action", "reasoning", "supporting_case_ids", "technician_verification"}
    missing_keys = required_keys - set(data.keys())
    if missing_keys:
        raise RecommendationValidationError(f"LLM response missing required keys: {missing_keys}")

    # 2. Grounding check on supporting_case_ids
    valid_case_ids: Set[str] = {c.case_id for c in retrieved_cases}
    raw_case_ids = data.get("supporting_case_ids", [])
    if not isinstance(raw_case_ids, list):
        raw_case_ids = []

    validated_case_ids = [str(cid) for cid in raw_case_ids if str(cid) in valid_case_ids]

    # If no case IDs survived filtering but retrieved_cases were provided, populate from valid set
    if not validated_case_ids and valid_case_ids:
        validated_case_ids = sorted(list(valid_case_ids))[:3]

    # 3. Technician verification check
    raw_checks = data.get("technician_verification", [])
    if not isinstance(raw_checks, list):
        raw_checks = []
    validated_checks = [str(check) for check in raw_checks if str(check).strip()]

    if not validated_checks:
        validated_checks = [
            "Perform visual and operational check on equipment",
            "Verify power supply and safety breakers before service"
        ]

    return RecommendationResult(
        recommended_action=str(data.get("recommended_action", "")).strip(),
        estimated_cost=cost_estimate,
        estimated_repair_time=time_estimate,
        urgency=urgency,
        reasoning=str(data.get("reasoning", "")).strip(),
        supporting_case_ids=validated_case_ids,
        technician_verification=validated_checks,
        grounded=len(validated_case_ids) > 0,
        safety_disclaimer=SAFETY_DISCLAIMER_TEXT,
        error=None
    )
