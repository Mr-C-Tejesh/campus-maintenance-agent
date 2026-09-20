import unittest
import os
import tempfile
import shutil
from app.retrieval import initialize_vector_store, MaintenanceRetriever
from app.diagnosis.models import DiagnosisResult, PossibleCause, EvidenceItem
from app.recommendation.models import RecommendationResult, CostEstimate, RepairTimeEstimate
from app.workflow import MaintenanceWorkflow, WorkflowResult

class MockDiagnosisService:
    def diagnose(self, complaint, retrieved_cases, equipment_type=None):
        case_ids = [c.case_id for c in retrieved_cases]
        return DiagnosisResult(
            summary=f"Integrated diagnosis over {len(retrieved_cases)} cases.",
            possible_causes=[PossibleCause("Filter defect", "High", case_ids, "Grounding match")],
            evidence=[EvidenceItem(cid, "Fact") for cid in case_ids],
            reasoning="Integrated test reasoning",
            confidence="High",
            technician_checks=["Perform physical filter check"],
            historical_case_ids=case_ids,
            grounded=len(case_ids) > 0
        )

class MockRecommendationService:
    def recommend(self, complaint, diagnosis, retrieved_cases):
        case_ids = [c.case_id for c in retrieved_cases]
        return RecommendationResult(
            recommended_action="Inspect and replace filter.",
            estimated_cost=CostEstimate(1000, 3000, 2000, case_ids, "1k-3k", "2k"),
            estimated_repair_time=RepairTimeEstimate(1, 4, 3, case_ids, "1-4h", "3h"),
            urgency="High",
            reasoning="Integrated rec reasoning",
            supporting_case_ids=case_ids,
            technician_verification=["Check pressure differential"],
            grounded=len(case_ids) > 0
        )

class TestIntegrationRealRetrievalMockedLLM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.csv_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'maintenance_records.csv'
        )
        cls.temp_dir = tempfile.mkdtemp(prefix="integration_chroma_")
        cls.vector_store = initialize_vector_store(
            csv_path=cls.csv_path,
            persist_directory=cls.temp_dir,
            force_rebuild=True
        )
        cls.retriever = MaintenanceRetriever(cls.vector_store)
        cls.diag_svc = MockDiagnosisService()
        cls.rec_svc = MockRecommendationService()
        cls.workflow = MaintenanceWorkflow(
            retriever=cls.retriever,
            diagnosis_service=cls.diag_svc,
            recommendation_service=cls.rec_svc
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_integration_flow(self):
        """
        Integration Test:
        Complaint -> Real ChromaDB retrieval -> Mocked Diagnosis -> Mocked Recommendation -> Final Result.
        """
        complaint = "AC is running continuously but the room remains warm"
        result = self.workflow.process_complaint(complaint, equipment_type="Air Conditioning", top_k=3)

        self.assertIsInstance(result, WorkflowResult)
        self.assertEqual(result.workflow_status, "SUCCESS")
        self.assertEqual(len(result.retrieved_cases), 3)
        
        # Verify retrieved case IDs exist in real CSV dataset
        retrieved_ids = [c.case_id for c in result.retrieved_cases]
        for cid in retrieved_ids:
            self.assertTrue(cid.startswith("CASE-"))

        # Verify diagnosis received the REAL retrieved case IDs
        self.assertEqual(result.diagnosis.historical_case_ids, retrieved_ids)
        
        # Verify recommendation received the REAL retrieved case IDs
        self.assertEqual(result.recommendation.supporting_case_ids, retrieved_ids)

if __name__ == '__main__':
    unittest.main()
