import unittest
from typing import List
from app.retrieval.retriever import RetrievalResult
from app.diagnosis.models import DiagnosisResult, PossibleCause, EvidenceItem
from app.recommendation.models import RecommendationResult, CostEstimate, RepairTimeEstimate
from app.workflow import (
    MaintenanceWorkflow, WorkflowResult, create_maintenance_graph, VALID_WORKFLOW_STATUSES
)

def create_mock_case(case_id: str = "CASE-0142", eq_type: str = "Air Conditioning") -> RetrievalResult:
    return RetrievalResult(
        case_id=case_id,
        distance=0.4,
        similarity_score=0.6,
        complaint="AC running but room warm",
        symptoms="Low airflow",
        root_cause="Clogged filter",
        action_taken="Cleaned filter",
        equipment_type=eq_type,
        equipment_model="Model-X",
        location="Bldg A",
        repair_cost=2000.0,
        repair_time_hours=3.0,
        urgency="Medium",
        maintenance_type="Corrective",
        date_reported="2023-01-01"
    )

class MockRetriever:
    def __init__(self, cases=None, side_effect=None):
        self.cases = cases if cases is not None else [create_mock_case()]
        self.side_effect = side_effect

    def search(self, complaint: str, equipment_type: str = None, top_k: int = 5, max_distance: float = 0.75):
        if self.side_effect:
            raise self.side_effect
        if equipment_type:
            return [c for c in self.cases if c.equipment_type == equipment_type]
        return self.cases

class MockDiagnosisService:
    def __init__(self, result=None, side_effect=None):
        self.result = result
        self.side_effect = side_effect
        self.last_cases = None

    def diagnose(self, complaint: str, retrieved_cases: List[RetrievalResult], equipment_type: str = None):
        self.last_cases = retrieved_cases
        if self.side_effect:
            raise self.side_effect
        if self.result:
            return self.result
        return DiagnosisResult(
            summary="Clogged filter diagnosed.",
            possible_causes=[PossibleCause("Clogged filter", "High", [c.case_id for c in retrieved_cases], "Matches")],
            evidence=[EvidenceItem(c.case_id, "Fact") for c in retrieved_cases],
            reasoning="Reasoning text",
            confidence="High",
            technician_checks=["Check filter"],
            historical_case_ids=[c.case_id for c in retrieved_cases],
            grounded=len(retrieved_cases) > 0
        )

class MockRecommendationService:
    def __init__(self, result=None, side_effect=None):
        self.result = result
        self.side_effect = side_effect
        self.last_diagnosis = None
        self.last_cases = None

    def recommend(self, complaint: str, diagnosis: DiagnosisResult, retrieved_cases: List[RetrievalResult]):
        self.last_diagnosis = diagnosis
        self.last_cases = retrieved_cases
        if self.side_effect:
            raise self.side_effect
        if self.result:
            return self.result
        return RecommendationResult(
            recommended_action="Clean air filter.",
            estimated_cost=CostEstimate(1000, 3000, 2000, [c.case_id for c in retrieved_cases], "1k-3k", "2k"),
            estimated_repair_time=RepairTimeEstimate(1, 4, 3, [c.case_id for c in retrieved_cases], "1-4h", "3h"),
            urgency="Medium",
            reasoning="Rec reasoning",
            supporting_case_ids=[c.case_id for c in retrieved_cases],
            technician_verification=["Verify airflow"],
            grounded=len(retrieved_cases) > 0
        )

class TestMaintenanceWorkflow(unittest.TestCase):
    def setUp(self):
        self.retriever = MockRetriever([
            create_mock_case("CASE-0142", "Air Conditioning"),
            create_mock_case("CASE-0063", "Generator"),
            create_mock_case("CASE-0236", "Elevator")
        ])
        self.diag_svc = MockDiagnosisService()
        self.rec_svc = MockRecommendationService()
        self.workflow = MaintenanceWorkflow(
            retriever=self.retriever,
            diagnosis_service=self.diag_svc,
            recommendation_service=self.rec_svc
        )

    def test_01_complete_successful_workflow(self):
        """1. Complete successful workflow end-to-end."""
        res = self.workflow.process_complaint("AC is running continuously", equipment_type="Air Conditioning")
        self.assertIsInstance(res, WorkflowResult)
        self.assertEqual(res.workflow_status, "SUCCESS")
        self.assertEqual(len(res.retrieved_cases), 1)
        self.assertEqual(res.retrieved_cases[0].case_id, "CASE-0142")
        self.assertIsNotNone(res.diagnosis)
        self.assertIsNotNone(res.recommendation)

    def test_02_ac_complaint_workflow(self):
        """2. AC complaint workflow."""
        res = self.workflow.process_complaint("Cooling failure in AC unit", equipment_type="Air Conditioning")
        self.assertEqual(res.workflow_status, "SUCCESS")
        self.assertEqual(res.equipment_type, "Air Conditioning")

    def test_03_generator_complaint_workflow(self):
        """3. Generator complaint workflow."""
        res = self.workflow.process_complaint("Generator power failure", equipment_type="Generator")
        self.assertEqual(res.workflow_status, "SUCCESS")
        self.assertEqual(res.retrieved_cases[0].case_id, "CASE-0063")

    def test_04_elevator_complaint_workflow(self):
        """4. Elevator complaint workflow."""
        res = self.workflow.process_complaint("Elevator door stuck", equipment_type="Elevator")
        self.assertEqual(res.workflow_status, "SUCCESS")
        self.assertEqual(res.retrieved_cases[0].case_id, "CASE-0236")

    def test_05_empty_complaint_validation_failure(self):
        """5. Empty complaint validation failure."""
        res1 = self.workflow.process_complaint("")
        self.assertEqual(res1.workflow_status, "INVALID_INPUT")
        
        res2 = self.workflow.process_complaint("  ")
        self.assertEqual(res2.workflow_status, "INVALID_INPUT")

    def test_06_unsupported_equipment_validation_failure(self):
        """5b. Unsupported equipment validation failure."""
        res = self.workflow.process_complaint("Cooling failure", equipment_type="Solar Panel")
        self.assertEqual(res.workflow_status, "INVALID_INPUT")
        self.assertIn("Unsupported equipment_type", res.error)

    def test_07_no_retrieval_results_flow(self):
        """6. No retrieval results flow."""
        empty_retriever = MockRetriever(cases=[])
        wf = MaintenanceWorkflow(retriever=empty_retriever, diagnosis_service=self.diag_svc, recommendation_service=self.rec_svc)
        res = wf.process_complaint("Unmatched query")
        self.assertEqual(res.workflow_status, "NO_RELEVANT_CASES")
        self.assertEqual(res.retrieved_cases, [])

    def test_08_retrieval_failure_handling(self):
        """7. Retrieval failure handling."""
        fail_retriever = MockRetriever(side_effect=Exception("Database connection error"))
        wf = MaintenanceWorkflow(retriever=fail_retriever, diagnosis_service=self.diag_svc, recommendation_service=self.rec_svc)
        res = wf.process_complaint("AC issue")
        self.assertEqual(res.workflow_status, "RETRIEVAL_FAILED")
        self.assertIn("Database connection error", res.error)

    def test_09_diagnosis_failure_handling(self):
        """8. Diagnosis failure handling."""
        diag_fail = MockDiagnosisService(result=DiagnosisResult("Failed", [], [], "", "Low", [], [], False, error="LLM Timeout"))
        wf = MaintenanceWorkflow(retriever=self.retriever, diagnosis_service=diag_fail, recommendation_service=self.rec_svc)
        res = wf.process_complaint("AC issue", equipment_type="Air Conditioning")
        self.assertEqual(res.workflow_status, "DIAGNOSIS_FAILED")

    def test_10_recommendation_failure_handling(self):
        """9. Recommendation failure handling."""
        rec_fail = MockRecommendationService(result=RecommendationResult("Action", CostEstimate(0,0,0,[],"",""), RepairTimeEstimate(0,0,0,[],"",""), "Low", "", [], [], False, error="Rec LLM Error"))
        wf = MaintenanceWorkflow(retriever=self.retriever, diagnosis_service=self.diag_svc, recommendation_service=rec_fail)
        res = wf.process_complaint("AC issue", equipment_type="Air Conditioning")
        self.assertEqual(res.workflow_status, "RECOMMENDATION_FAILED")

    def test_11_case_propagation(self):
        """10 & 11. Correct propagation of retrieved cases to diagnosis and diagnosis to recommendation."""
        res = self.workflow.process_complaint("AC complaint", equipment_type="Air Conditioning")
        # Check propagation
        self.assertEqual(self.diag_svc.last_cases, res.retrieved_cases)
        self.assertEqual(self.rec_svc.last_diagnosis, res.diagnosis)
        self.assertEqual(self.rec_svc.last_cases, res.retrieved_cases)

    def test_12_workflow_result_serialization(self):
        """12 & 13. Final result structure, status values, and to_dict() serialization."""
        res = self.workflow.process_complaint("AC issue", equipment_type="Air Conditioning")
        self.assertIn(res.workflow_status, VALID_WORKFLOW_STATUSES)
        d = res.to_dict()
        self.assertEqual(d["complaint"], "AC issue")
        self.assertEqual(d["workflow_status"], "SUCCESS")
        self.assertIn("retrieved_cases", d)
        self.assertIn("diagnosis", d)
        self.assertIn("recommendation", d)

    def test_13_langgraph_execution(self):
        """14. LangGraph graph execution test."""
        graph = create_maintenance_graph(self.workflow)
        inputs = {"complaint": "AC cooling issue", "equipment_type": "Air Conditioning"}
        output = graph.invoke(inputs)
        
        self.assertIn("retrieved_cases", output)
        self.assertIn("diagnosis", output)
        self.assertIn("recommendation", output)
        self.assertEqual(len(output["retrieved_cases"]), 1)
        self.assertEqual(output["retrieved_cases"][0].case_id, "CASE-0142")

if __name__ == '__main__':
    unittest.main()
