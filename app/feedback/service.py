import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional
from app.workflow.state import WorkflowResult
from app.feedback.models import FeedbackRecord, VALID_FEEDBACK_VALUES
from app.feedback.repository import FeedbackRepository, StorageError
import sqlite3

logger = logging.getLogger(__name__)

class InvalidFeedbackError(ValueError):
    pass

class DuplicateFeedbackError(Exception):
    pass

class FeedbackValidationError(ValueError):
    pass

class FeedbackService:
    def __init__(self, repository: Optional[FeedbackRepository] = None):
        self.repository = repository or FeedbackRepository()

    def save_feedback(
        self,
        workflow_result: WorkflowResult,
        feedback: str,
        notes: Optional[str] = None
    ) -> FeedbackRecord:
        """
        Validates and stores a technician's feedback ("Correct" or "Incorrect")
        for a specific maintenance workflow execution.
        """
        # 1. Validate feedback value
        if not feedback or feedback not in VALID_FEEDBACK_VALUES:
            raise InvalidFeedbackError(
                f"Invalid feedback value '{feedback}'. Feedback must be exactly 'Correct' or 'Incorrect'."
            )

        # 2. Validate workflow result structure
        if not isinstance(workflow_result, WorkflowResult):
            raise FeedbackValidationError("workflow_result must be a valid WorkflowResult instance.")

        if not workflow_result.complaint or len(workflow_result.complaint.strip()) == 0:
            raise FeedbackValidationError("workflow_result is missing a valid complaint text.")

        # 3. Resolve workflow_id
        wf_id = workflow_result.workflow_id
        if not wf_id:
            # Fallback workflow ID derived from complaint hash
            wf_id = f"wf-{hash(workflow_result.complaint) & 0xffffffff:08x}"

        # 4. Check duplicate submission
        existing = self.repository.get_by_workflow_id(wf_id)
        if existing:
            raise DuplicateFeedbackError(
                f"Feedback already submitted for workflow execution '{wf_id}'."
            )

        # 5. Extract workflow context
        retrieved_ids = [c.case_id for c in workflow_result.retrieved_cases]
        
        diag_summary = (
            workflow_result.diagnosis.summary
            if workflow_result.diagnosis
            else None
        )
        
        rec_action = (
            workflow_result.recommendation.recommended_action
            if workflow_result.recommendation
            else None
        )

        location = None
        if workflow_result.retrieved_cases and hasattr(workflow_result.retrieved_cases[0], "location"):
            location = workflow_result.retrieved_cases[0].location

        # 6. Construct record
        record = FeedbackRecord(
            feedback_id=f"fb-{uuid.uuid4().hex[:8]}",
            workflow_id=wf_id,
            complaint=workflow_result.complaint.strip(),
            equipment_type=workflow_result.equipment_type,
            location=location,
            retrieved_case_ids=retrieved_ids,
            diagnosis_summary=diag_summary,
            recommended_action=rec_action,
            technician_feedback=feedback,
            timestamp=datetime.now(timezone.utc).isoformat(),
            notes=notes.strip() if notes else None
        )

        # 7. Persist to storage
        try:
            return self.repository.save(record)
        except sqlite3.IntegrityError:
            raise DuplicateFeedbackError(
                f"Feedback already submitted for workflow execution '{wf_id}'."
            )
        except StorageError as se:
            logger.error(f"Failed to persist technician feedback: {se}")
            raise

    def get_feedback(self, feedback_id: str) -> Optional[FeedbackRecord]:
        """Fetches a feedback record by its feedback_id."""
        return self.repository.get_by_id(feedback_id)

    def get_feedback_by_workflow(self, workflow_id: str) -> Optional[FeedbackRecord]:
        """Fetches a feedback record by its workflow_id."""
        return self.repository.get_by_workflow_id(workflow_id)

    def list_feedback(self, limit: int = 100) -> List[FeedbackRecord]:
        """Lists recent technician feedback records."""
        return self.repository.list_all(limit=limit)
