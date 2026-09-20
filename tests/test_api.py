import os
import tempfile
import unittest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.registry import WorkflowRegistry
from app.api.routes import get_workflow, get_feedback_service, get_registry
from app.feedback import FeedbackService, FeedbackRepository, StorageError
from app.retrieval.retriever import RetrievalResult
from app.diagnosis.models import DiagnosisResult, PossibleCause, EvidenceItem
from app.recommendation.models import RecommendationResult, CostEstimate, RepairTimeEstimate
from app.workflow.state import WorkflowResult

def create_sample_workflow_result(
    workflow_id: str = "wf-api-test-001",
    complaint: str = "Air conditioning is blowing warm air",
    equipment_type: str = "Air Conditioning",
    location: str = None
) -> WorkflowResult:
    case_ids = ["CASE-0001", "CASE-0002"]
    cases = [
        RetrievalResult(
            case_id=cid,
            distance=0.25,
            similarity_score=0.75,
            complaint=complaint,
            symptoms="Low cooling",
            root_cause="Refrigerant leak",
            action_taken="Replaced valve and recharged refrigerant",
            equipment_type=equipment_type,
            equipment_model="Carrier 5000",
            location=location or "Building B",
            repair_cost=3500.0,
            repair_time_hours=3.0,
            urgency="High",
            maintenance_type="Corrective",
            date_reported="2023-05-12"
        )
        for cid in case_ids
    ]
    diag = DiagnosisResult(
        summary="Refrigerant leak detected in cooling loop.",
        possible_causes=[PossibleCause("Refrigerant leak", "High", case_ids, "Matches pressure drops")],
        evidence=[EvidenceItem(cid, "Refrigerant recharge was needed") for cid in case_ids],
        reasoning="Consistent with warm airflow symptom.",
        confidence="High",
        technician_checks=["Check line pressure", "Inspect expansion valve"],
        historical_case_ids=case_ids,
        grounded=True
    )
    rec = RecommendationResult(
        recommended_action="Inspect cooling circuit and recharge refrigerant.",
        estimated_cost=CostEstimate(3000, 4000, 3500, case_ids, "3000-4000 INR", "3500 INR"),
        estimated_repair_time=RepairTimeEstimate(2.0, 4.0, 3.0, case_ids, "2.0-4.0 hrs", "3.0 hrs"),
        urgency="High",
        reasoning="High urgency due to facility heat.",
        supporting_case_ids=case_ids,
        technician_verification=["Check line pressure", "Inspect expansion valve"],
        grounded=True
    )
    return WorkflowResult(
        workflow_id=workflow_id,
        complaint=complaint,
        equipment_type=equipment_type,
        location=location,
        retrieved_cases=cases,
        diagnosis=diag,
        recommendation=rec,
        workflow_status="completed"
    )


class MockWorkflow:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail

    def process_complaint(self, complaint: str, equipment_type=None, location=None, top_k: int = 5):
        if self.should_fail:
            raise RuntimeError("Simulated workflow failure")
        return create_sample_workflow_result(
            complaint=complaint,
            equipment_type=equipment_type or "Air Conditioning",
            location=location
        )



class TestAPI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_api_feedback.db")
        self.repo = FeedbackRepository(db_path=self.db_path)
        self.feedback_service = FeedbackService(repository=self.repo)
        self.registry = WorkflowRegistry()
        self.mock_workflow = MockWorkflow()

        self.app = create_app()

        # Wire dependency overrides
        self.app.dependency_overrides[get_feedback_service] = lambda: self.feedback_service
        self.app.dependency_overrides[get_registry] = lambda: self.registry
        self.app.dependency_overrides[get_workflow] = lambda: self.mock_workflow

        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def test_root_endpoint(self):
        """Test GET / and HEAD / return 200 and service metadata."""
        get_resp = self.client.get("/")
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["docs"], "/docs")

        head_resp = self.client.head("/")
        self.assertEqual(head_resp.status_code, 200)

    def test_health_check(self):
        """Test GET /health returns 200 and healthy status."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "Campus/Facility Infrastructure Decision-Support Agent")
        self.assertEqual(data["version"], "1.0.0")


    def test_cors_headers(self):
        """Test that CORS headers are properly returned for allowed origins."""
        response = self.client.get("/health", headers={"Origin": "http://localhost:3000"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:3000")

    def test_analyze_complaint_success(self):
        """Test POST /api/v1/analyze returns 200 and registers result."""
        payload = {
            "complaint": "AC unit blowing warm air into lecture hall",
            "equipment_type": "Air Conditioning",
            "top_k": 5
        }
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("workflow_id", data)
        self.assertEqual(data["workflow_status"], "completed")
        self.assertEqual(data["complaint"], payload["complaint"])
        self.assertEqual(data["equipment_type"], "Air Conditioning")
        self.assertIsNotNone(data["diagnosis"])
        self.assertIsNotNone(data["recommendation"])
        self.assertEqual(len(data["retrieved_cases"]), 2)

        # Verify registration in registry
        self.assertIsNotNone(self.registry.get(data["workflow_id"]))

    def test_analyze_complaint_with_location(self):
        """Test POST /api/v1/analyze accepts and preserves optional location parameter."""
        payload = {
            "complaint": "AC unit blowing warm air",
            "equipment_type": "Air Conditioning",
            "location": "Laboratory Block",
            "top_k": 5
        }
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("workflow_id", data)
        self.assertEqual(data["location"], "Laboratory Block")

    def test_analyze_complaint_without_equipment_type(self):

        """Test POST /api/v1/analyze allows optional equipment_type."""
        payload = {
            "complaint": "Strange buzzing sound coming from elevator shaft"
        }
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("workflow_id", data)

    def test_analyze_complaint_invalid_equipment_type(self):
        """Test POST /api/v1/analyze validates equipment_type against known categories."""
        payload = {
            "complaint": "Refrigerator in pantry is not freezing",
            "equipment_type": "Refrigerator"
        }
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_analyze_complaint_empty_complaint(self):
        """Test POST /api/v1/analyze rejects empty complaints."""
        payload = {"complaint": "   "}
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_analyze_complaint_invalid_top_k(self):
        """Test POST /api/v1/analyze rejects out-of-bounds top_k."""
        payload = {
            "complaint": "Generator failed to start during power cut",
            "top_k": 50
        }
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_analyze_complaint_internal_error(self):
        """Test POST /api/v1/analyze handles unexpected workflow error with 500."""
        self.mock_workflow.should_fail = True
        payload = {
            "complaint": "Generator engine overheating",
            "equipment_type": "Generator"
        }
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("detail", response.json())

    def test_submit_feedback_success(self):
        """Test POST /api/v1/feedback submits valid feedback for registered workflow."""
        # Seed registry
        sample = create_sample_workflow_result(workflow_id="wf-seed-001")
        self.registry.register(sample)

        payload = {
            "workflow_id": "wf-seed-001",
            "feedback": "Correct",
            "notes": "Verified on-site: refrigerant leak confirmed and fixed."
        }
        response = self.client.post("/api/v1/feedback", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["workflow_id"], "wf-seed-001")
        self.assertEqual(data["technician_feedback"], "Correct")
        self.assertEqual(data["notes"], payload["notes"])
        self.assertIn("feedback_id", data)
        self.assertIn("timestamp", data)

    def test_submit_feedback_workflow_not_found(self):
        """Test POST /api/v1/feedback returns 404 when workflow_id is not in registry."""
        payload = {
            "workflow_id": "wf-unregistered-999",
            "feedback": "Correct",
            "notes": "Test note"
        }
        response = self.client.post("/api/v1/feedback", json=payload)
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found or session expired", response.json()["detail"])

    def test_submit_feedback_duplicate_conflict(self):
        """Test POST /api/v1/feedback returns 409 on duplicate submission for same workflow."""
        sample = create_sample_workflow_result(workflow_id="wf-seed-002")
        self.registry.register(sample)

        payload = {
            "workflow_id": "wf-seed-002",
            "feedback": "Correct",
            "notes": "First submission"
        }
        resp1 = self.client.post("/api/v1/feedback", json=payload)
        self.assertEqual(resp1.status_code, 201)

        resp2 = self.client.post("/api/v1/feedback", json=payload)
        self.assertEqual(resp2.status_code, 409)
        self.assertIn("already submitted", resp2.json()["detail"])


    def test_submit_feedback_invalid_feedback_value(self):
        """Test POST /api/v1/feedback validates feedback to 'Correct' or 'Incorrect'."""
        sample = create_sample_workflow_result(workflow_id="wf-seed-003")
        self.registry.register(sample)

        payload = {
            "workflow_id": "wf-seed-003",
            "feedback": "Partially Correct",
            "notes": "Not allowed enum"
        }
        response = self.client.post("/api/v1/feedback", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_submit_feedback_notes_too_long(self):
        """Test POST /api/v1/feedback rejects notes exceeding 1000 characters."""
        sample = create_sample_workflow_result(workflow_id="wf-seed-004")
        self.registry.register(sample)

        payload = {
            "workflow_id": "wf-seed-004",
            "feedback": "Incorrect",
            "notes": "A" * 1001
        }
        response = self.client.post("/api/v1/feedback", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_list_feedback_empty_and_populated(self):
        """Test GET /api/v1/feedback retrieves stored feedback list."""
        # Initially empty
        resp0 = self.client.get("/api/v1/feedback")
        self.assertEqual(resp0.status_code, 200)
        self.assertEqual(resp0.json(), [])

        # Add 2 items
        s1 = create_sample_workflow_result(workflow_id="wf-list-001")
        s2 = create_sample_workflow_result(workflow_id="wf-list-002")
        self.registry.register(s1)
        self.registry.register(s2)

        self.client.post("/api/v1/feedback", json={"workflow_id": "wf-list-001", "feedback": "Correct"})
        self.client.post("/api/v1/feedback", json={"workflow_id": "wf-list-002", "feedback": "Incorrect"})

        resp = self.client.get("/api/v1/feedback?limit=10")
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertEqual(len(items), 2)
        # Verify ordering (newest first)
        self.assertEqual(items[0]["workflow_id"], "wf-list-002")
        self.assertEqual(items[1]["workflow_id"], "wf-list-001")

    def test_list_feedback_invalid_limit(self):
        """Test GET /api/v1/feedback validates limit parameter."""
        resp = self.client.get("/api/v1/feedback?limit=0")
        self.assertEqual(resp.status_code, 422)

        resp2 = self.client.get("/api/v1/feedback?limit=300")
        self.assertEqual(resp2.status_code, 422)

    def test_feedback_storage_error_handled(self):
        """Test that storage errors in feedback route return 500."""
        sample = create_sample_workflow_result(workflow_id="wf-err-001")
        self.registry.register(sample)

        # Force storage error by passing unwriteable DB or mock
        class FailingFeedbackService:
            def save_feedback(self, *args, **kwargs):
                raise StorageError("Disk I/O error")
            def list_feedback(self, *args, **kwargs):
                raise StorageError("Disk I/O error")

        self.app.dependency_overrides[get_feedback_service] = FailingFeedbackService

        post_resp = self.client.post("/api/v1/feedback", json={"workflow_id": "wf-err-001", "feedback": "Correct"})
        self.assertEqual(post_resp.status_code, 500)

        get_resp = self.client.get("/api/v1/feedback")
        self.assertEqual(get_resp.status_code, 500)

    def test_cors_frontend_origin_configuration(self):
        """Test that FRONTEND_ORIGIN environment variable is parsed and allowed in CORS."""
        test_origin = "https://custom-campus-app.vercel.app"
        old_origin = os.environ.get("FRONTEND_ORIGIN")
        try:
            os.environ["FRONTEND_ORIGIN"] = f"{test_origin}/, https://another-preview.vercel.app"
            app = create_app()
            client = TestClient(app)
            headers = {
                "Origin": test_origin,
                "Access-Control-Request-Method": "GET",
            }
            resp = client.options("/health", headers=headers)
            self.assertEqual(resp.headers.get("access-control-allow-origin"), test_origin)
        finally:
            if old_origin is not None:
                os.environ["FRONTEND_ORIGIN"] = old_origin
            else:
                os.environ.pop("FRONTEND_ORIGIN", None)


if __name__ == "__main__":
    unittest.main()
