import logging
from fastapi import APIRouter, HTTPException, Query, status, Depends
from typing import List, Dict, Any, Optional

from app.api.schemas import AnalyzeRequest, FeedbackSubmitRequest, HealthResponse
from app.api.registry import default_registry, WorkflowRegistry
from app.workflow import MaintenanceWorkflow
from app.feedback import (
    FeedbackService, FeedbackRecord,
    DuplicateFeedbackError, InvalidFeedbackError, FeedbackValidationError, StorageError
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency providers (can be overridden in tests via app.dependency_overrides)
def get_workflow() -> MaintenanceWorkflow:
    return MaintenanceWorkflow()

def get_feedback_service() -> FeedbackService:
    return FeedbackService()

def get_registry() -> WorkflowRegistry:
    return default_registry

# Route 1: Health
@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse()

# Route 2: Analyze Complaint
@router.post("/api/v1/analyze", status_code=status.HTTP_200_OK)
def analyze_complaint(
    request: AnalyzeRequest,
    workflow: MaintenanceWorkflow = Depends(get_workflow),
    registry: WorkflowRegistry = Depends(get_registry)
):
    try:
        result = workflow.process_complaint(
            complaint=request.complaint,
            equipment_type=request.equipment_type,
            top_k=request.top_k or 5
        )
    except Exception as e:
        logger.error(f"Unexpected error in workflow execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred during complaint analysis."
        )

    # Cache authentic execution in session registry for feedback linking
    registry.register(result)
    return result.to_dict()

# Route 3: Submit Technician Feedback
@router.post("/api/v1/feedback", status_code=status.HTTP_201_CREATED)
def submit_feedback(
    request: FeedbackSubmitRequest,
    registry: WorkflowRegistry = Depends(get_registry),
    feedback_service: FeedbackService = Depends(get_feedback_service)
):
    workflow_result = registry.get(request.workflow_id)
    if not workflow_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow execution '{request.workflow_id}' not found or session expired. Feedback must reference an authentic workflow execution."
        )

    try:
        saved_record = feedback_service.save_feedback(
            workflow_result=workflow_result,
            feedback=request.feedback,
            notes=request.notes
        )
        return saved_record.to_dict()
    except DuplicateFeedbackError as de:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(de)
        )
    except (InvalidFeedbackError, FeedbackValidationError) as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except StorageError as se:
        logger.error(f"Storage error while saving feedback: {se}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist feedback in database."
        )

# Route 4: Retrieve Feedback
@router.get("/api/v1/feedback", status_code=status.HTTP_200_OK)
def list_feedback(
    limit: int = Query(50, ge=1, le=200),
    feedback_service: FeedbackService = Depends(get_feedback_service)
):
    try:
        records = feedback_service.list_feedback(limit=limit)
        return [r.to_dict() for r in records]
    except StorageError as se:
        logger.error(f"Storage error reading feedback records: {se}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback records from database."
        )

