import unittest
import json
from app.retrieval.retriever import RetrievalResult
from app.diagnosis.models import DiagnosisResult, PossibleCause, EvidenceItem
from app.recommendation import (
    RecommendationService, RecommendationResult, CostEstimate, RepairTimeEstimate,
    calculate_cost_estimate, calculate_repair_time_estimate, determine_urgency,
    validate_recommendation_output
)

class MockGenerateResponse:
    def __init__(self, text: str):
        self.text = text

class MockModelsAPI:
    def __init__(self, text_response: str = "", side_effect: Exception = None):
        self.text_response = text_response
        self.side_effect = side_effect

    def generate_content(self, model: str, contents: str, config: any = None):
        if self.side_effect:
            raise self.side_effect
        return MockGenerateResponse(self.text_response)

class MockGeminiClient:
    def __init__(self, text_response: str = "", side_effect: Exception = None):
        self.models = MockModelsAPI(text_response=text_response, side_effect=side_effect)

def create_sample_retrieved_case(
    case_id: str = "CASE-0142",
    equipment_type: str = "Air Conditioning",
    complaint: str = "AC not cooling",
    symptoms: str = "Low airflow",
    root_cause: str = "Clogged filter",
    action_taken: str = "Cleaned filter",
    repair_cost: float = 1500.0,
    repair_time_hours: float = 2.0,
    urgency: str = "High"
) -> RetrievalResult:
    return RetrievalResult(
        case_id=case_id,
        distance=0.4,
        similarity_score=0.6,
        complaint=complaint,
        symptoms=symptoms,
        root_cause=root_cause,
        action_taken=action_taken,
        equipment_type=equipment_type,
        equipment_model="AC-Model-X",
        location="Building A",
        repair_cost=repair_cost,
        repair_time_hours=repair_time_hours,
        urgency=urgency,
        maintenance_type="Corrective",
        date_reported="2023-05-10"
    )

def create_sample_diagnosis(
    case_id: str = "CASE-0142",
    grounded: bool = True,
    confidence: str = "High"
) -> DiagnosisResult:
    return DiagnosisResult(
        summary="Clogged air filter suggested.",
        possible_causes=[
            PossibleCause(
                cause="Clogged filter",
                likelihood="High",
                supporting_case_ids=[case_id],
                explanation="Matches symptoms"
            )
        ],
        evidence=[EvidenceItem(case_id=case_id, fact="Cleaned filter")],
        reasoning="Inferred clogged filter",
        confidence=confidence,
        technician_checks=["Inspect filter"],
        historical_case_ids=[case_id],
        grounded=grounded
    )

class TestRecommendationEngine(unittest.TestCase):
    def setUp(self):
        self.cases = [
            create_sample_retrieved_case("CASE-0142", "Air Conditioning", repair_cost=1000.0, repair_time_hours=1.5, urgency="Medium"),
            create_sample_retrieved_case("CASE-0056", "Air Conditioning", repair_cost=3000.0, repair_time_hours=4.5, urgency="High"),
            create_sample_retrieved_case("CASE-0080", "Air Conditioning", repair_cost=2000.0, repair_time_hours=3.0, urgency="Medium")
        ]
        self.diagnosis = create_sample_diagnosis("CASE-0142")

    def test_01_cost_calculation(self):
        """3. Historical cost calculation (min, max, median, formatting)."""
        cost_est = calculate_cost_estimate(self.cases)
        self.assertEqual(cost_est.min_cost, 1000.0)
        self.assertEqual(cost_est.max_cost, 3000.0)
        self.assertEqual(cost_est.median_cost, 2000.0)
        self.assertEqual(len(cost_est.supporting_case_ids), 3)
        self.assertIn("₹1,000.00 – ₹3,000.00", cost_est.formatted_range)
        self.assertIn("₹2,000.00", cost_est.formatted_reference)

    def test_02_repair_time_calculation(self):
        """4. Historical repair time calculation (min, max, median, formatting)."""
        time_est = calculate_repair_time_estimate(self.cases)
        self.assertEqual(time_est.min_hours, 1.5)
        self.assertEqual(time_est.max_hours, 4.5)
        self.assertEqual(time_est.median_hours, 3.0)
        self.assertEqual(len(time_est.supporting_case_ids), 3)
        self.assertIn("1.5 – 4.5 hours", time_est.formatted_range)
        self.assertIn("3.0 hours", time_est.formatted_reference)

    def test_03_missing_cost_data(self):
        """5. Missing cost data handled gracefully."""
        cases_no_cost = [
            create_sample_retrieved_case("CASE-0001", repair_cost=0.0),
            create_sample_retrieved_case("CASE-0002", repair_cost=None)
        ]
        cost_est = calculate_cost_estimate(cases_no_cost)
        self.assertEqual(cost_est.median_cost, 0.0)
        self.assertEqual(cost_est.supporting_case_ids, [])
        self.assertIn("No historical cost", cost_est.formatted_reference)

    def test_04_missing_repair_time_data(self):
        """6. Missing repair time data handled gracefully."""
        cases_no_time = [create_sample_retrieved_case("CASE-0001", repair_time_hours=0.0)]
        time_est = calculate_repair_time_estimate(cases_no_time)
        self.assertEqual(time_est.median_hours, 0.0)
        self.assertIn("No historical repair duration", time_est.formatted_reference)

    def test_05_urgency_rules(self):
        """9. Urgency rules evaluation for Critical, High, Medium, Low."""
        # Critical keyword
        self.assertEqual(determine_urgency("Generator gas leak and fire", None, []), "Critical")
        
        # High keyword/case
        self.assertEqual(determine_urgency("Elevator door stuck", None, self.cases), "High")
        
        # Low case
        low_case = [create_sample_retrieved_case("CASE-0001", urgency="Low")]
        self.assertEqual(determine_urgency("Routine filter check", None, low_case), "Low")

    def test_06_recommendation_with_strong_evidence(self):
        """1. Recommendation with strong retrieved evidence."""
        llm_json = json.dumps({
            "recommended_action": "Clean or replace air filter and inspect duct airflow.",
            "reasoning": "CASE-0142 and CASE-0056 demonstrate similar cooling deficits resolved by cleaning filter.",
            "supporting_case_ids": ["CASE-0142", "CASE-0056"],
            "technician_verification": ["Check airflow", "Measure temperature diff"]
        })
        client = MockGeminiClient(text_response=llm_json)
        service = RecommendationService(client=client)
        result = service.recommend("AC is running but room remains warm", self.diagnosis, self.cases)

        self.assertIsInstance(result, RecommendationResult)
        self.assertTrue(result.grounded)
        self.assertEqual(result.recommended_action, "Clean or replace air filter and inspect duct airflow.")
        self.assertIn("CASE-0142", result.supporting_case_ids)
        self.assertEqual(result.estimated_cost.median_cost, 2000.0)

    def test_07_empty_retrieved_cases_fallback(self):
        """7. Empty retrieved cases fallback."""
        client = MockGeminiClient(text_response="{}")
        service = RecommendationService(client=client)
        result = service.recommend("Strange AC noise", self.diagnosis, [])

        self.assertFalse(result.grounded)
        self.assertIn("Perform on-site physical technician inspection", result.recommended_action)
        self.assertEqual(result.estimated_cost.median_cost, 0.0)

    def test_08_hallucinated_case_id_rejected(self):
        """11. Hallucinated case ID in model output is rejected."""
        cost_est = calculate_cost_estimate(self.cases)
        time_est = calculate_repair_time_estimate(self.cases)
        
        hallucinated_json = json.dumps({
            "recommended_action": "Replace motor",
            "reasoning": "Reasoning citing fake case",
            "supporting_case_ids": ["CASE-9999", "CASE-0142"],
            "technician_verification": ["Check motor"]
        })
        res = validate_recommendation_output(hallucinated_json, self.cases, cost_est, time_est, "High")
        self.assertNotIn("CASE-9999", res.supporting_case_ids)
        self.assertIn("CASE-0142", res.supporting_case_ids)

    def test_09_llm_api_failure_handling(self):
        """13. LLM API failure handling."""
        client = MockGeminiClient(side_effect=Exception("API connection failure"))
        service = RecommendationService(client=client)
        result = service.recommend("Generator failure", self.diagnosis, self.cases)

        self.assertIsNotNone(result.error)
        self.assertFalse(result.grounded)

    def test_10_malformed_structured_output_handling(self):
        """14. Malformed non-JSON output handled safely."""
        client = MockGeminiClient(text_response="Invalid raw text output")
        service = RecommendationService(client=client)
        result = service.recommend("Elevator issue", self.diagnosis, self.cases)

        self.assertIsNotNone(result.error)
        self.assertIn("Validation Error", result.error)

    def test_11_recommendation_serialization(self):
        """12. Valid serialization of RecommendationResult."""
        cost_est = calculate_cost_estimate(self.cases)
        time_est = calculate_repair_time_estimate(self.cases)
        rec = RecommendationResult(
            recommended_action="Action A",
            estimated_cost=cost_est,
            estimated_repair_time=time_est,
            urgency="High",
            reasoning="Reason A",
            supporting_case_ids=["CASE-0142"],
            technician_verification=["Check 1"],
            grounded=True
        )
        d = rec.to_dict()
        self.assertEqual(d["recommended_action"], "Action A")
        self.assertEqual(d["estimated_cost"]["median_cost"], 2000.0)
        self.assertEqual(d["estimated_repair_time"]["median_hours"], 3.0)

if __name__ == '__main__':
    unittest.main()
