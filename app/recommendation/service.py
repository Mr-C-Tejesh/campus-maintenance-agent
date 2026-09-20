import os
import sys
import logging
from typing import List, Optional, Any

# Ensure parent directory is in sys.path when script is executed directly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    genai = None
    types = None

from app.retrieval.retriever import RetrievalResult
from app.diagnosis.models import DiagnosisResult
from app.recommendation.models import (
    RecommendationResult, CostEstimate, RepairTimeEstimate, SAFETY_DISCLAIMER_TEXT
)
from app.recommendation.cost_engine import calculate_cost_estimate, calculate_repair_time_estimate
from app.recommendation.urgency_engine import determine_urgency
from app.recommendation.prompt import build_recommendation_prompt
from app.recommendation.validator import validate_recommendation_output, RecommendationValidationError

logger = logging.getLogger(__name__)

class RecommendationService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[Any] = None,
        model_name: str = "gemini-2.5-flash"
    ):
        self.model_name = model_name
        self.client = client
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

        if self.client is None and self.api_key:
            if not HAS_GENAI:
                logger.warning("google-genai package is not installed in the active python environment.")
                self.client = None
            else:
                try:
                    self.client = genai.Client(api_key=self.api_key)
                except Exception as e:
                    logger.warning(f"Failed to initialize Gemini Client: {e}")
                    self.client = None

    def _fallback_recommendation(
        self,
        complaint: str,
        diagnosis: Optional[DiagnosisResult],
        retrieved_cases: List[RetrievalResult],
        reason_msg: str
    ) -> RecommendationResult:
        """Returns a safe, ungrounded recommendation fallback."""
        cost_est = calculate_cost_estimate(retrieved_cases)
        time_est = calculate_repair_time_estimate(retrieved_cases)
        urgency = determine_urgency(complaint, diagnosis, retrieved_cases)

        return RecommendationResult(
            recommended_action="Perform on-site physical technician inspection and diagnostic.",
            estimated_cost=cost_est,
            estimated_repair_time=time_est,
            urgency=urgency,
            reasoning=f"Recommendation fallback ({reason_msg}). Physical technician diagnostic required.",
            supporting_case_ids=[],
            technician_verification=[
                "Inspect physical equipment condition",
                "Verify electrical and safety control systems",
                "Consult OEM maintenance documentation"
            ],
            grounded=False,
            safety_disclaimer=SAFETY_DISCLAIMER_TEXT,
            error=None
        )

    def recommend(
        self,
        complaint: str,
        diagnosis: Optional[DiagnosisResult],
        retrieved_cases: List[RetrievalResult]
    ) -> RecommendationResult:
        """
        Generates an evidence-grounded maintenance recommendation combining deterministic calculations and LLM reasoning.
        """
        # 1. Compute deterministic cost, repair time, and urgency
        cost_est = calculate_cost_estimate(retrieved_cases)
        time_est = calculate_repair_time_estimate(retrieved_cases)
        urgency = determine_urgency(complaint, diagnosis, retrieved_cases)

        # 2. Check empty complaint or empty retrieval (Fallback flow)
        if not complaint or len(complaint.strip()) < 3:
            return self._fallback_recommendation(complaint or "", diagnosis, retrieved_cases, "Empty complaint")

        if not retrieved_cases:
            return self._fallback_recommendation(complaint, diagnosis, retrieved_cases, "No historical cases retrieved")

        # 3. Check LLM client availability
        if self.client is None:
            if not HAS_GENAI:
                return self._fallback_recommendation(
                    complaint, diagnosis, retrieved_cases,
                    "google-genai package not installed in active environment"
                )

            if not self.api_key:
                # Return deterministic fallback with error message
                result = self._fallback_recommendation(
                    complaint, diagnosis, retrieved_cases,
                    "GEMINI_API_KEY environment variable is not configured"
                )
                result.error = "GEMINI_API_KEY missing"
                return result

            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                result = self._fallback_recommendation(
                    complaint, diagnosis, retrieved_cases,
                    f"Client initialization error: {e}"
                )
                result.error = str(e)
                return result

        # 4. Build prompt
        prompt = build_recommendation_prompt(
            complaint, diagnosis, retrieved_cases, cost_est, time_est, urgency
        )

        # 5. Call LLM
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            raw_text = response.text
        except Exception as e:
            logger.error(f"Gemini API recommendation call failed: {e}")
            result = self._fallback_recommendation(
                complaint, diagnosis, retrieved_cases, f"API Error: {e}"
            )
            result.error = f"API Error: {e}"
            return result

        # 6. Validate output
        try:
            return validate_recommendation_output(
                raw_text, retrieved_cases, cost_est, time_est, urgency
            )
        except RecommendationValidationError as ve:
            logger.warning(f"Recommendation validation failed: {ve}")
            result = self._fallback_recommendation(
                complaint, diagnosis, retrieved_cases, f"Validation Error: {ve}"
            )
            result.error = f"Validation Error: {ve}"
            return result
