import os
import sys
import uuid
import logging
from typing import List, Optional, Any

# Ensure parent directory is in sys.path when script is executed directly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.retrieval import initialize_vector_store, MaintenanceRetriever, ALLOWED_EQUIPMENT_TYPES, RetrievalResult
from app.diagnosis import DiagnosisService, DiagnosisResult
from app.recommendation import RecommendationService, RecommendationResult
from app.workflow.state import WorkflowResult

logger = logging.getLogger(__name__)

class MaintenanceWorkflow:
    def __init__(
        self,
        retriever: Optional[MaintenanceRetriever] = None,
        diagnosis_service: Optional[DiagnosisService] = None,
        recommendation_service: Optional[RecommendationService] = None
    ):
        if retriever is None:
            vector_store = initialize_vector_store()
            self.retriever = MaintenanceRetriever(vector_store)
        else:
            self.retriever = retriever

        self.diagnosis_service = diagnosis_service or DiagnosisService()
        self.recommendation_service = recommendation_service or RecommendationService()

    def process_complaint(
        self,
        complaint: str,
        equipment_type: Optional[str] = None,
        location: Optional[str] = None,
        top_k: int = 5,
        workflow_id: Optional[str] = None
    ) -> WorkflowResult:
        """
        Executes the end-to-end maintenance decision workflow:
        Input Validation -> Semantic Retrieval -> Diagnosis -> Recommendation -> Result
        """
        wf_id = workflow_id or f"wf-{uuid.uuid4().hex[:8]}"
        loc_clean = location.strip() if location and location.strip() else None
        logger.info(f"Workflow {wf_id} started. Equipment: '{equipment_type or 'None'}', Location: '{loc_clean or 'None'}'")

        # 1. Input Validation
        if not complaint or len(complaint.strip()) < 3:
            logger.warning(f"Workflow {wf_id} aborted: Complaint text is empty or too short.")
            return WorkflowResult(
                complaint=complaint or "",
                equipment_type=equipment_type,
                location=loc_clean,
                retrieved_cases=[],
                diagnosis=None,
                recommendation=None,
                workflow_status="INVALID_INPUT",
                error="Complaint text is empty or too short.",
                workflow_id=wf_id
            )

        if equipment_type is not None and equipment_type not in ALLOWED_EQUIPMENT_TYPES:
            err_msg = f"Unsupported equipment_type '{equipment_type}'. Allowed: {sorted(list(ALLOWED_EQUIPMENT_TYPES))}"
            logger.warning(f"Workflow {wf_id} aborted: {err_msg}")
            return WorkflowResult(
                complaint=complaint.strip(),
                equipment_type=equipment_type,
                location=loc_clean,
                retrieved_cases=[],
                diagnosis=None,
                recommendation=None,
                workflow_status="INVALID_INPUT",
                error=err_msg,
                workflow_id=wf_id
            )

        # 2. Stage 1: Retrieval
        retrieved_cases: List[RetrievalResult] = []
        search_query = f"Location: {loc_clean}. {complaint}" if loc_clean and loc_clean not in complaint else complaint
        try:
            retrieved_cases = self.retriever.search(
                complaint=search_query,
                equipment_type=equipment_type,
                top_k=top_k
            )
            logger.info(f"Retrieval completed. Retrived {len(retrieved_cases)} historical cases.")
        except Exception as e:
            logger.error(f"Retrieval stage failed: {e}")
            return WorkflowResult(
                complaint=complaint.strip(),
                equipment_type=equipment_type,
                location=loc_clean,
                retrieved_cases=[],
                diagnosis=None,
                recommendation=None,
                workflow_status="RETRIEVAL_FAILED",
                error=f"Retrieval failed: {e}",
                workflow_id=wf_id
            )

        # 3. Stage 2: Diagnosis
        diagnosis: Optional[DiagnosisResult] = None
        try:
            diagnosis = self.diagnosis_service.diagnose(
                complaint=complaint,
                retrieved_cases=retrieved_cases,
                equipment_type=equipment_type
            )
            logger.info(f"Diagnosis completed. Confidence: '{diagnosis.confidence}', Grounded: {diagnosis.grounded}")
        except Exception as e:
            logger.error(f"Diagnosis stage exception: {e}")
            diagnosis = DiagnosisResult(
                summary="Diagnosis failed due to an internal error.",
                possible_causes=[],
                evidence=[],
                reasoning=f"Stage error: {e}",
                confidence="Low",
                technician_checks=["Manual physical inspection required"],
                historical_case_ids=[],
                grounded=False,
                error=str(e)
            )

        # 4. Stage 3: Recommendation
        recommendation: Optional[RecommendationResult] = None
        try:
            recommendation = self.recommendation_service.recommend(
                complaint=complaint,
                diagnosis=diagnosis,
                retrieved_cases=retrieved_cases
            )
            logger.info(f"Recommendation completed. Urgency: '{recommendation.urgency}', Grounded: {recommendation.grounded}")
        except Exception as e:
            logger.error(f"Recommendation stage exception: {e}")
            recommendation = None

        # 5. Status Resolution
        if not retrieved_cases:
            status = "NO_RELEVANT_CASES"
        elif diagnosis and diagnosis.error:
            status = "DIAGNOSIS_FAILED"
        elif recommendation and recommendation.error:
            status = "RECOMMENDATION_FAILED"
        elif recommendation is None:
            status = "RECOMMENDATION_FAILED"
        else:
            status = "SUCCESS"

        final_err = None
        if diagnosis and diagnosis.error:
            final_err = f"Diagnosis notice: {diagnosis.error}"
        if recommendation and recommendation.error:
            final_err = f"Recommendation notice: {recommendation.error}" if not final_err else f"{final_err} | Rec notice: {recommendation.error}"

        return WorkflowResult(
            complaint=complaint.strip(),
            equipment_type=equipment_type,
            location=loc_clean,
            retrieved_cases=retrieved_cases,
            diagnosis=diagnosis,
            recommendation=recommendation,
            workflow_status=status,
            error=final_err,
            workflow_id=wf_id
        )


