import os
import logging
from typing import List, Optional, Any
from google import genai
from google.genai import types

from app.retrieval.retriever import RetrievalResult
from app.diagnosis.models import DiagnosisResult, PossibleCause, EvidenceItem
from app.diagnosis.prompt import build_diagnosis_prompt
from app.diagnosis.validator import validate_diagnosis_output, DiagnosisValidationError

logger = logging.getLogger(__name__)

class DiagnosisError(Exception):
    pass

class DiagnosisService:
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
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini Client: {e}")
                self.client = None

    def _no_evidence_fallback(
        self,
        complaint: str,
        reason_msg: str
    ) -> DiagnosisResult:
        """Returns a safe, ungrounded diagnosis when no historical cases are available."""
        return DiagnosisResult(
            summary="No relevant historical maintenance evidence was retrieved for this complaint.",
            possible_causes=[
                PossibleCause(
                    cause="General equipment malfunction requiring physical diagnostic",
                    likelihood="Low",
                    supporting_case_ids=[],
                    explanation="No historical cases matched the complaint symptoms closely enough to establish a grounded evidence-based diagnosis."
                )
            ],
            evidence=[],
            reasoning=f"Grounded diagnosis was unavailable ({reason_msg}). Physical technician inspection is strictly required.",
            confidence="Low",
            technician_checks=[
                "Perform physical visual inspection of equipment",
                "Check error indicators and power/electrical supply",
                "Consult manufacturer manual for unindexed failure codes"
            ],
            historical_case_ids=[],
            grounded=False,
            error=None
        )

    def diagnose(
        self,
        complaint: str,
        retrieved_cases: List[RetrievalResult],
        equipment_type: Optional[str] = None
    ) -> DiagnosisResult:
        """
        Generates an evidence-grounded diagnosis for a maintenance complaint using retrieved cases.
        """
        # 1. Handle empty complaint or empty retrieved cases (No-Evidence flow)
        if not complaint or len(complaint.strip()) < 3:
            return self._no_evidence_fallback(
                complaint or "",
                "Complaint text was empty or too short"
            )

        if not retrieved_cases:
            return self._no_evidence_fallback(
                complaint,
                "No relevant historical cases retrieved"
            )

        # 2. Check client availability
        if self.client is None:
            if not self.api_key:
                return DiagnosisResult(
                    summary="Diagnosis service unavailable: GEMINI_API_KEY environment variable is not configured.",
                    possible_causes=[],
                    evidence=[],
                    reasoning="API key missing. Grounded LLM reasoning requires a valid GEMINI_API_KEY.",
                    confidence="Low",
                    technician_checks=["Configure GEMINI_API_KEY in environment"],
                    historical_case_ids=[],
                    grounded=False,
                    error="GEMINI_API_KEY missing"
                )

            # Attempt late initialization if key set
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                return DiagnosisResult(
                    summary=f"Failed to initialize Gemini Client: {e}",
                    possible_causes=[],
                    evidence=[],
                    reasoning="Client initialization error.",
                    confidence="Low",
                    technician_checks=[],
                    historical_case_ids=[],
                    grounded=False,
                    error=str(e)
                )

        # 3. Build prompt
        prompt = build_diagnosis_prompt(complaint, retrieved_cases, equipment_type)

        # 4. Call Gemini LLM
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
            logger.error(f"Gemini API call failed: {e}")
            return DiagnosisResult(
                summary=f"LLM diagnosis generation failed due to API error: {e}",
                possible_causes=[],
                evidence=[],
                reasoning="API communication failure during diagnosis.",
                confidence="Low",
                technician_checks=["Verify API key and network connectivity"],
                historical_case_ids=[],
                grounded=False,
                error=f"API Error: {e}"
            )

        # 5. Validate and return structured output
        try:
            return validate_diagnosis_output(raw_text, retrieved_cases)
        except DiagnosisValidationError as ve:
            logger.warning(f"Diagnosis output validation failed: {ve}")
            return DiagnosisResult(
                summary="Diagnosis response validation failed.",
                possible_causes=[],
                evidence=[],
                reasoning=f"LLM output failed validation: {ve}",
                confidence="Low",
                technician_checks=["Manual technician inspection required"],
                historical_case_ids=[],
                grounded=False,
                error=f"Validation Error: {ve}"
            )
