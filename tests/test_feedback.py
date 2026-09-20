import unittest
import tempfile
import os
import shutil
from app.retrieval.retriever import RetrievalResult
from app.diagnosis.models import DiagnosisResult, PossibleCause, EvidenceItem
from app.recommendation.models import RecommendationResult, CostEstimate, RepairTimeEstimate
from app.workflow.state import WorkflowResult
from app.feedback import (
    FeedbackService, FeedbackRepository, FeedbackRecord,
    InvalidFeedbackError, DuplicateFeedbackError, FeedbackValidationError, StorageError
)

def create_sample_workflow_result(
    workflow_id: str = "wf-test-001",
    complaint: str = "AC is running continuously but room remains warm",
    equipment_type: str = "Air Conditioning",
    case_ids: list = None
) -> WorkflowResult:
    c_ids = case_ids or ["CASE-0142", "CASE-0056"]
    retrieved = [
        RetrievalResult(
            case_id=cid,
            distance=0.4,
            similarity_score=0.6,
            complaint=complaint,
            symptoms="Low airflow",
            root_cause="Clogged filter",
            action_taken="Cleaned filter",
            equipment_type=equipment_type,
            equipment_model="AC-Model-X",
            location="Building A, Room 101",
            repair_cost=2000.0,
            repair_time_hours=2.5,
            urgency="High",
            maintenance_type="Corrective",
            date_reported="2023-01-01"
        )
        for cid in c_ids
    ]
    diag = DiagnosisResult(
        summary="Clogged filter likely.",
        possible_causes=[PossibleCause("Clogged filter", "High", c_ids, "Matches")],
        evidence=[EvidenceItem(cid, "Fact") for cid in c_ids],
        reasoning="Reasoning",
        confidence="High",
        technician_checks=["Check airflow"],
        historical_case_ids=c_ids,
        grounded=True
    )
    rec = RecommendationResult(
        recommended_action="Clean air filter and check airflow.",
        estimated_cost=CostEstimate(1500, 2500, 2000, c_ids, "1.5k-2.5k", "2k"),
        estimated_repair_time=RepairTimeEstimate(2, 3, 2.5, c_ids, "2-3h", "2.5h"),
        urgency="High",
        reasoning="Rec reasoning",
        supporting_case_ids=c_ids,
        technician_verification=["Check airflow"],
        grounded=True
    )
    return WorkflowResult(
        complaint=complaint,
        equipment_type=equipment_type,
        retrieved_cases=retrieved,
        diagnosis=diag,
        recommendation=rec,
        workflow_status="SUCCESS",
        workflow_id=workflow_id
    )

class TestFeedbackLoop(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_feedback_")
        self.db_path = os.path.join(self.temp_dir, "test_feedback.db")
        self.repo = FeedbackRepository(db_path=self.db_path)
        self.service = FeedbackService(repository=self.repo)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_save_correct_feedback(self):
        """1. Save Correct feedback successfully."""
        wf = create_sample_workflow_result("wf-001")
        record = self.service.save_feedback(wf, "Correct", notes="Confirmed on-site")
        
        self.assertIsInstance(record, FeedbackRecord)
        self.assertEqual(record.technician_feedback, "Correct")
        self.assertEqual(record.workflow_id, "wf-001")
        self.assertEqual(record.notes, "Confirmed on-site")
        self.assertTrue(record.feedback_id.startswith("fb-"))

    def test_02_save_incorrect_feedback(self):
        """2. Save Incorrect feedback successfully."""
        wf = create_sample_workflow_result("wf-002")
        record = self.service.save_feedback(wf, "Incorrect", notes="Was actually a compressor capacitor issue")
        
        self.assertIsInstance(record, FeedbackRecord)
        self.assertEqual(record.technician_feedback, "Incorrect")
        self.assertEqual(record.workflow_id, "wf-002")
        self.assertEqual(record.notes, "Was actually a compressor capacitor issue")

    def test_03_invalid_feedback_value_rejected(self):
        """3. Arbitrary feedback value is rejected."""
        wf = create_sample_workflow_result("wf-003")
        
        with self.assertRaises(InvalidFeedbackError):
            self.service.save_feedback(wf, "Maybe")
            
        with self.assertRaises(InvalidFeedbackError):
            self.service.save_feedback(wf, "")
            
        with self.assertRaises(InvalidFeedbackError):
            self.service.save_feedback(wf, "correct")  # case-sensitive check

    def test_04_missing_workflow_information_rejected(self):
        """4. Invalid or missing workflow object rejected."""
        with self.assertRaises(FeedbackValidationError):
            self.service.save_feedback(None, "Correct")
            
        empty_wf = WorkflowResult(
            complaint="",
            equipment_type=None,
            retrieved_cases=[],
            diagnosis=None,
            recommendation=None,
            workflow_status="INVALID_INPUT"
        )
        with self.assertRaises(FeedbackValidationError):
            self.service.save_feedback(empty_wf, "Correct")

    def test_05_database_persistence_across_restart(self):
        """5. Feedback survives restart (re-instantiated repository)."""
        wf = create_sample_workflow_result("wf-persist")
        self.service.save_feedback(wf, "Correct")
        
        # Create a new repository and service pointing to the same SQLite database file
        new_repo = FeedbackRepository(db_path=self.db_path)
        new_service = FeedbackService(repository=new_repo)
        
        record = new_service.get_feedback_by_workflow("wf-persist")
        self.assertIsNotNone(record)
        self.assertEqual(record.workflow_id, "wf-persist")
        self.assertEqual(record.technician_feedback, "Correct")

    def test_06_read_back_saved_feedback(self):
        """6. Read-back of saved feedback records by ID and list."""
        wf = create_sample_workflow_result("wf-readback")
        saved = self.service.save_feedback(wf, "Correct")
        
        fetched = self.service.get_feedback(saved.feedback_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.feedback_id, saved.feedback_id)
        self.assertEqual(fetched.complaint, wf.complaint)
        
        all_records = self.service.list_feedback()
        self.assertEqual(len(all_records), 1)

    def test_07_duplicate_submission_handling(self):
        """7. Duplicate submission for the same workflow execution is blocked."""
        wf = create_sample_workflow_result("wf-dup")
        self.service.save_feedback(wf, "Correct")
        
        # Second submission for same workflow_id must raise DuplicateFeedbackError
        with self.assertRaises(DuplicateFeedbackError):
            self.service.save_feedback(wf, "Correct")
            
        with self.assertRaises(DuplicateFeedbackError):
            self.service.save_feedback(wf, "Incorrect")

    def test_08_multiple_different_workflow_records(self):
        """8. Multiple distinct workflow feedback records can be saved."""
        wf1 = create_sample_workflow_result("wf-101", complaint="AC leak")
        wf2 = create_sample_workflow_result("wf-102", complaint="Elevator stopped")
        wf3 = create_sample_workflow_result("wf-103", complaint="Generator smoke")
        
        self.service.save_feedback(wf1, "Correct")
        self.service.save_feedback(wf2, "Incorrect")
        self.service.save_feedback(wf3, "Correct")
        
        all_records = self.service.list_feedback()
        self.assertEqual(len(all_records), 3)

    def test_09_stored_case_ids_correspond_to_workflow_result(self):
        """9. Stored case IDs match the workflow result retrieved cases exactly."""
        expected_case_ids = ["CASE-0126", "CASE-0063"]
        wf = create_sample_workflow_result("wf-cases", case_ids=expected_case_ids)
        
        record = self.service.save_feedback(wf, "Correct")
        self.assertEqual(record.retrieved_case_ids, expected_case_ids)
        
        fetched = self.service.get_feedback_by_workflow("wf-cases")
        self.assertEqual(fetched.retrieved_case_ids, expected_case_ids)

    def test_10_database_failure_handling(self):
        """10. Graceful handling of storage errors."""
        # Point to invalid path that cannot be written
        invalid_repo = FeedbackRepository(db_path=self.db_path)
        # Force a broken table state
        with invalid_repo._get_connection() as conn:
            conn.execute("DROP TABLE technician_feedback")
            conn.commit()
            
        service_broken = FeedbackService(repository=invalid_repo)
        wf = create_sample_workflow_result("wf-fail")
        with self.assertRaises(StorageError):
            service_broken.save_feedback(wf, "Correct")

if __name__ == '__main__':
    unittest.main()
