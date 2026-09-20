import statistics
from typing import List
from app.retrieval.retriever import RetrievalResult
from app.recommendation.models import CostEstimate, RepairTimeEstimate

def calculate_cost_estimate(retrieved_cases: List[RetrievalResult]) -> CostEstimate:
    """
    Computes historical cost statistics (min, max, median) from retrieved maintenance cases.
    Returns a CostEstimate object with formatted range strings.
    """
    valid_records = []
    for c in retrieved_cases:
        if c.repair_cost is not None and c.repair_cost > 0:
            valid_records.append((c.case_id, float(c.repair_cost)))

    if not valid_records:
        return CostEstimate(
            min_cost=0.0,
            max_cost=0.0,
            median_cost=0.0,
            supporting_case_ids=[],
            formatted_range="No historical cost range available",
            formatted_reference="No historical cost data available"
        )

    costs = [r[1] for r in valid_records]
    case_ids = [r[0] for r in valid_records]

    min_val = round(min(costs), 2)
    max_val = round(max(costs), 2)
    median_val = round(statistics.median(costs), 2)

    range_str = f"₹{min_val:,.2f} – ₹{max_val:,.2f}"
    ref_str = f"₹{median_val:,.2f} (Historical Median)"

    return CostEstimate(
        min_cost=min_val,
        max_cost=max_val,
        median_cost=median_val,
        supporting_case_ids=case_ids,
        formatted_range=range_str,
        formatted_reference=ref_str
    )

def calculate_repair_time_estimate(retrieved_cases: List[RetrievalResult]) -> RepairTimeEstimate:
    """
    Computes historical repair time statistics (min, max, median) from retrieved maintenance cases.
    Returns a RepairTimeEstimate object with formatted range strings.
    """
    valid_records = []
    for c in retrieved_cases:
        if c.repair_time_hours is not None and c.repair_time_hours > 0:
            valid_records.append((c.case_id, float(c.repair_time_hours)))

    if not valid_records:
        return RepairTimeEstimate(
            min_hours=0.0,
            max_hours=0.0,
            median_hours=0.0,
            supporting_case_ids=[],
            formatted_range="No historical duration range available",
            formatted_reference="No historical repair duration available"
        )

    times = [r[1] for r in valid_records]
    case_ids = [r[0] for r in valid_records]

    min_val = round(min(times), 1)
    max_val = round(max(times), 1)
    median_val = round(statistics.median(times), 1)

    range_str = f"{min_val} – {max_val} hours"
    ref_str = f"{median_val} hours (Historical Median)"

    return RepairTimeEstimate(
        min_hours=min_val,
        max_hours=max_val,
        median_hours=median_val,
        supporting_case_ids=case_ids,
        formatted_range=range_str,
        formatted_reference=ref_str
    )
