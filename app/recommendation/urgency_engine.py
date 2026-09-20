from typing import List, Optional
from app.retrieval.retriever import RetrievalResult
from app.diagnosis.models import DiagnosisResult
from app.recommendation.models import VALID_URGENCY_LEVELS

CRITICAL_KEYWORDS = {
    "fire", "smoke", "spark", "gas leak", "explosion", "trapped",
    "power outage", "total failure", "brake failure", "flood", "leak"
}

HIGH_KEYWORDS = {
    "outage", "stuck", "door not closing", "overheating", "loud noise",
    "burning smell", "trip", "continuous running", "unresponsive"
}

URGENCY_WEIGHTS = {
    "Critical": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1
}

def determine_urgency(
    complaint: str,
    diagnosis: Optional[DiagnosisResult],
    retrieved_cases: List[RetrievalResult]
) -> str:
    """
    Determines urgency deterministically using explicit business rules.
    """
    complaint_lower = complaint.lower()

    # Rule 1: Immediate Critical keywords check
    for kw in CRITICAL_KEYWORDS:
        if kw in complaint_lower:
            return "Critical"

    # Rule 2: Evaluate maximum urgency present in top retrieved historical cases
    max_hist_weight = 1
    if retrieved_cases:
        for c in retrieved_cases[:3]:  # inspect top 3 relevant cases
            weight = URGENCY_WEIGHTS.get(c.urgency, 1)
            if weight > max_hist_weight:
                max_hist_weight = weight

    # Rule 3: Check High keywords
    has_high_keyword = any(kw in complaint_lower for kw in HIGH_KEYWORDS)

    # Rule 4: Evaluate diagnosis confidence and cause likelihood
    diag_high = False
    if diagnosis and diagnosis.confidence == "High" and diagnosis.possible_causes:
        if any(pc.likelihood == "High" for pc in diagnosis.possible_causes):
            diag_high = True

    # Rule synthesis
    if max_hist_weight == 4:
        return "Critical"
    elif max_hist_weight == 3 or (has_high_keyword and diag_high):
        return "High"
    elif max_hist_weight == 2 or has_high_keyword:
        return "Medium"
    else:
        return "Low"
