import json
import re
from typing import List, Dict, Any, Set
from app.retrieval.retriever import RetrievalResult
from app.diagnosis.models import (
    DiagnosisResult, PossibleCause, EvidenceItem, VALID_CONFIDENCE_LEVELS
)

class DiagnosisValidationError(Exception):
    pass

def clean_json_text(raw_text: str) -> str:
    """Removes markdown code block formatting if present."""
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text

def validate_diagnosis_output(
    raw_output: str,
    retrieved_cases: List[RetrievalResult]
) -> DiagnosisResult:
    """
    Parses and strictly validates raw LLM output against grounding and structural rules.
    
    Grounding Enforcement:
    - Every cited case_id MUST exist in retrieved_cases.
    - Hallucinated case IDs are strictly removed/rejected.
    - Confidence must be 'High', 'Medium', or 'Low'.
    """
    cleaned_text = clean_json_text(raw_output)
    try:
        data = json.loads(cleaned_text)
    except Exception as e:
        raise DiagnosisValidationError(f"Failed to parse LLM JSON response: {e}") from e

    if not isinstance(data, dict):
        raise DiagnosisValidationError("LLM response root must be a JSON object.")

    # 1. Required fields check
    required_keys = {"summary", "possible_causes", "evidence", "reasoning", "confidence", "technician_checks", "historical_case_ids"}
    missing_keys = required_keys - set(data.keys())
    if missing_keys:
        raise DiagnosisValidationError(f"LLM response missing required keys: {missing_keys}")

    # 2. Confidence validation
    confidence = str(data.get("confidence", "")).capitalize()
    if confidence not in VALID_CONFIDENCE_LEVELS:
        confidence = "Low"

    # 3. Valid case IDs set for grounding check
    valid_case_ids: Set[str] = {c.case_id for c in retrieved_cases}

    # 4. Validate and filter historical_case_ids
    raw_cited_ids = data.get("historical_case_ids", [])
    if not isinstance(raw_cited_ids, list):
        raw_cited_ids = []

    validated_case_ids = [str(cid) for cid in raw_cited_ids if str(cid) in valid_case_ids]

    # 5. Validate possible_causes
    raw_causes = data.get("possible_causes", [])
    if not isinstance(raw_causes, list):
        raw_causes = []

    validated_causes: List[PossibleCause] = []
    for pc in raw_causes:
        if not isinstance(pc, dict):
            continue
        cause_text = str(pc.get("cause", "")).strip()
        if not cause_text:
            continue
        
        likelihood = str(pc.get("likelihood", "Medium")).capitalize()
        if likelihood not in VALID_CONFIDENCE_LEVELS:
            likelihood = "Medium"

        raw_supp_ids = pc.get("supporting_case_ids", [])
        if not isinstance(raw_supp_ids, list):
            raw_supp_ids = []

        supp_ids = [str(cid) for cid in raw_supp_ids if str(cid) in valid_case_ids]

        validated_causes.append(PossibleCause(
            cause=cause_text,
            likelihood=likelihood,
            supporting_case_ids=supp_ids,
            explanation=str(pc.get("explanation", ""))
        ))

    # 6. Validate evidence items
    raw_evidence = data.get("evidence", [])
    if not isinstance(raw_evidence, list):
        raw_evidence = []

    validated_evidence: List[EvidenceItem] = []
    for ev in raw_evidence:
        if not isinstance(ev, dict):
            continue
        cid = str(ev.get("case_id", ""))
        if cid in valid_case_ids:
            validated_evidence.append(EvidenceItem(
                case_id=cid,
                fact=str(ev.get("fact", ""))
            ))

    # 7. Validate technician checks
    tech_checks = data.get("technician_checks", [])
    if not isinstance(tech_checks, list):
        tech_checks = []
    validated_checks = [str(check) for check in tech_checks if str(check).strip()]

    # Re-synchronize validated cited case IDs
    all_cited = set(validated_case_ids)
    for pc in validated_causes:
        all_cited.update(pc.supporting_case_ids)
    for ev in validated_evidence:
        all_cited.add(ev.case_id)

    final_case_ids = [cid for cid in valid_case_ids if cid in all_cited]

    return DiagnosisResult(
        summary=str(data.get("summary", "")).strip(),
        possible_causes=validated_causes,
        evidence=validated_evidence,
        reasoning=str(data.get("reasoning", "")).strip(),
        confidence=confidence,
        technician_checks=validated_checks,
        historical_case_ids=final_case_ids,
        grounded=len(final_case_ids) > 0,
        error=None
    )
