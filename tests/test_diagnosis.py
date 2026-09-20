import unittest
import json
from typing import List
from app.retrieval.retriever import RetrievalResult
from app.diagnosis import (
    DiagnosisService, DiagnosisResult, PossibleCause, EvidenceItem,
    validate_diagnosis_output, DiagnosisValidationError
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
    complaint: str = "AC running but room warm",
    symptoms: str = "High temp reading, low airflow",
    root_cause: str = "Clogged air filter",
    action_taken: str = "Cleaned filter",
    distance: float = 0.4
) -> RetrievalResult:
    return RetrievalResult(
        case_id=case_id,
        distance=distance,
        similarity_score=round(1.0 - distance, 4),
        complaint=complaint,
        symptoms=symptoms,
        root_cause=root_cause,
        action_taken=action_taken,
        equipment_type=equipment_type,
        equipment_model="AC-Model-X",
        location="Building A",
        repair_cost=1500.0,
        repair_time_hours=2.0,
        urgency="High",
        maintenance_type="Corrective",
        date_reported="2023-05-10"
    )

class TestDiagnosisLayer(unittest.TestCase):
    def setUp(self):
        self.sample_cases = [
            create_sample_retrieved_case("CASE-0142", "Air Conditioning", "AC not cooling", "Low airflow", "Clogged filter", "Cleaned filter"),
            create_sample_retrieved_case("CASE-0056", "Air Conditioning", "Air conditioner warm", "Warm air output", "Refrigerant leak", "Refilled gas")
        ]
        self.valid_ids = {"CASE-0142", "CASE-0056"}

    def test_01_diagnosis_with_relevant_cases(self):
        """1. Diagnosis with relevant retrieved cases produces structured result."""
        valid_llm_json = json.dumps({
            "summary": "Clogged filter or refrigerant leak suggested by historical cases.",
            "possible_causes": [
                {
                    "cause": "Clogged air filter",
                    "likelihood": "High",
                    "supporting_case_ids": ["CASE-0142"],
                    "explanation": "CASE-0142 reported low airflow and insufficient cooling resolved by cleaning filter."
                }
            ],
            "evidence": [
                {
                    "case_id": "CASE-0142",
                    "fact": "Cleaned clogged air filter to restore cooling."
                }
            ],
            "reasoning": "Historical evidence CASE-0142 matches symptoms. Inferred clogged filter as primary cause.",
            "confidence": "High",
            "technician_checks": ["Inspect air filter cleanliness"],
            "historical_case_ids": ["CASE-0142"]
        })
        client = MockGeminiClient(text_response=valid_llm_json)
        service = DiagnosisService(client=client)
        result = service.diagnose("AC running but room remains warm", self.sample_cases)

        self.assertIsInstance(result, DiagnosisResult)
        self.assertTrue(result.grounded)
        self.assertEqual(result.confidence, "High")
        self.assertEqual(len(result.possible_causes), 1)
        self.assertEqual(result.possible_causes[0].cause, "Clogged air filter")
        self.assertEqual(result.historical_case_ids, ["CASE-0142"])

    def test_02_diagnosis_with_several_cases(self):
        """2. Diagnosis with several related cases cites multiple valid IDs."""
        valid_llm_json = json.dumps({
            "summary": "Multiple potential causes identified from past records.",
            "possible_causes": [
                {
                    "cause": "Blocked filter",
                    "likelihood": "High",
                    "supporting_case_ids": ["CASE-0142"],
                    "explanation": "Matches CASE-0142."
                },
                {
                    "cause": "Refrigerant leakage",
                    "likelihood": "Medium",
                    "supporting_case_ids": ["CASE-0056"],
                    "explanation": "Matches CASE-0056."
                }
            ],
            "evidence": [
                {"case_id": "CASE-0142", "fact": "Air filter clogged."},
                {"case_id": "CASE-0056", "fact": "Gas leakage detected."}
            ],
            "reasoning": "Inferred filter blockage and gas leak based on CASE-0142 and CASE-0056.",
            "confidence": "Medium",
            "technician_checks": ["Check filter", "Measure gas pressure"],
            "historical_case_ids": ["CASE-0142", "CASE-0056"]
        })
        client = MockGeminiClient(text_response=valid_llm_json)
        service = DiagnosisService(client=client)
        result = service.diagnose("AC blowing warm air", self.sample_cases)

        self.assertEqual(len(result.possible_causes), 2)
        self.assertIn("CASE-0142", result.historical_case_ids)
        self.assertIn("CASE-0056", result.historical_case_ids)

    def test_03_diagnosis_with_weak_evidence(self):
        """3. Weak evidence causes low confidence rating."""
        valid_llm_json = json.dumps({
            "summary": "Sparse historical evidence; weak match.",
            "possible_causes": [
                {
                    "cause": "Possible fan motor issue",
                    "likelihood": "Low",
                    "supporting_case_ids": ["CASE-0142"],
                    "explanation": "Weak correlation with CASE-0142."
                }
            ],
            "evidence": [{"case_id": "CASE-0142", "fact": "Generic AC repair"}],
            "reasoning": "Symptoms match loosely. Weak historical evidence.",
            "confidence": "Low",
            "technician_checks": ["Inspect fan motor"],
            "historical_case_ids": ["CASE-0142"]
        })
        client = MockGeminiClient(text_response=valid_llm_json)
        service = DiagnosisService(client=client)
        result = service.diagnose("AC making strange humming noise", self.sample_cases)

        self.assertEqual(result.confidence, "Low")

    def test_04_no_retrieved_cases_fallback(self):
        """4. Diagnosis with no retrieved cases triggers safe no-evidence fallback."""
        client = MockGeminiClient(text_response="{}")
        service = DiagnosisService(client=client)
        result = service.diagnose("AC humming loudly", [])

        self.assertFalse(result.grounded)
        self.assertEqual(result.confidence, "Low")
        self.assertEqual(result.historical_case_ids, [])
        self.assertIn("No relevant historical maintenance evidence", result.summary)

    def test_05_empty_complaint_handling(self):
        """5. Empty or whitespace complaint returns safe no-evidence fallback."""
        client = MockGeminiClient(text_response="{}")
        service = DiagnosisService(client=client)
        
        res1 = service.diagnose("", self.sample_cases)
        self.assertFalse(res1.grounded)
        
        res2 = service.diagnose("   ", self.sample_cases)
        self.assertFalse(res2.grounded)

    def test_06_llm_api_failure_handling(self):
        """6. Handling of LLM API exception during generate_content."""
        client = MockGeminiClient(side_effect=Exception("API connection timeout"))
        service = DiagnosisService(client=client)
        result = service.diagnose("Generator failed to start", self.sample_cases)

        self.assertIsNotNone(result.error)
        self.assertIn("API Error", result.error)
        self.assertFalse(result.grounded)

    def test_07_invalid_structured_llm_response(self):
        """7. Malformed non-JSON LLM response handled safely."""
        client = MockGeminiClient(text_response="This is not valid JSON content")
        service = DiagnosisService(client=client)
        result = service.diagnose("Elevator door stuck", self.sample_cases)

        self.assertIsNotNone(result.error)
        self.assertIn("Validation Error", result.error)
        self.assertFalse(result.grounded)

    def test_08_hallucinated_case_id_rejected(self):
        """8. Hallucinated case IDs not present in retrieved_cases are rejected."""
        hallucinated_json = json.dumps({
            "summary": "Diagnosed issue.",
            "possible_causes": [
                {
                    "cause": "Fake cause",
                    "likelihood": "High",
                    "supporting_case_ids": ["CASE-9999", "CASE-0142"],
                    "explanation": "Cites fake case 9999."
                }
            ],
            "evidence": [
                {"case_id": "CASE-9999", "fact": "Invented fact."},
                {"case_id": "CASE-0142", "fact": "Real fact."}
            ],
            "reasoning": "Reasoning citing fake case.",
            "confidence": "High",
            "technician_checks": ["Check unit"],
            "historical_case_ids": ["CASE-9999", "CASE-0142"]
        })
        result = validate_diagnosis_output(hallucinated_json, self.sample_cases)

        # CASE-9999 MUST be stripped from all fields
        self.assertNotIn("CASE-9999", result.historical_case_ids)
        self.assertIn("CASE-0142", result.historical_case_ids)
        self.assertNotIn("CASE-9999", result.possible_causes[0].supporting_case_ids)
        self.assertEqual(len(result.evidence), 1)
        self.assertEqual(result.evidence[0].case_id, "CASE-0142")

    def test_09_valid_case_ids_accepted(self):
        """9. Valid historical case IDs are accepted in validator."""
        valid_json = json.dumps({
            "summary": "Valid summary",
            "possible_causes": [{
                "cause": "Valid cause",
                "likelihood": "High",
                "supporting_case_ids": ["CASE-0142"],
                "explanation": "Valid exp"
            }],
            "evidence": [{"case_id": "CASE-0142", "fact": "Valid fact"}],
            "reasoning": "Valid reasoning",
            "confidence": "High",
            "technician_checks": ["Check filter"],
            "historical_case_ids": ["CASE-0142"]
        })
        result = validate_diagnosis_output(valid_json, self.sample_cases)
        self.assertEqual(result.historical_case_ids, ["CASE-0142"])

    def test_10_confidence_validation(self):
        """10. Confidence string is normalized to allowed set or defaults to Low."""
        invalid_conf_json = json.dumps({
            "summary": "Summary",
            "possible_causes": [],
            "evidence": [],
            "reasoning": "Reasoning",
            "confidence": "SUPER_HIGH_99%",  # Invalid confidence string
            "technician_checks": [],
            "historical_case_ids": []
        })
        result = validate_diagnosis_output(invalid_conf_json, self.sample_cases)
        self.assertEqual(result.confidence, "Low")

    def test_11_missing_api_key_handling(self):
        """11. Missing GEMINI_API_KEY handled cleanly."""
        service = DiagnosisService(api_key=None, client=None)
        # Temporarily clear env
        import os
        old_key = os.environ.pop("GEMINI_API_KEY", None)
        try:
            result = service.diagnose("Test complaint", self.sample_cases)
            self.assertIsNotNone(result.error)
            self.assertIn("GEMINI_API_KEY", result.summary)
        finally:
            if old_key:
                os.environ["GEMINI_API_KEY"] = old_key

    def test_12_diagnosis_result_serialization(self):
        """12. DiagnosisResult object validation and to_dict serialization."""
        cause = PossibleCause("Cause A", "High", ["CASE-0142"], "Explanation")
        ev = EvidenceItem("CASE-0142", "Fact A")
        diag = DiagnosisResult(
            summary="Sum",
            possible_causes=[cause],
            evidence=[ev],
            reasoning="Reason",
            confidence="High",
            technician_checks=["Check 1"],
            historical_case_ids=["CASE-0142"],
            grounded=True
        )
        d = diag.to_dict()
        self.assertEqual(d["summary"], "Sum")
        self.assertEqual(d["possible_causes"][0]["cause"], "Cause A")
        self.assertEqual(d["evidence"][0]["case_id"], "CASE-0142")
        self.assertTrue(d["grounded"])

if __name__ == '__main__':
    unittest.main()
