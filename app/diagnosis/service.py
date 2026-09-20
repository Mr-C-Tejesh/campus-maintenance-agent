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
        model_name: Optional[str] = None
    ):
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        self.client = client
        self.api_key = api_key
        self._has_explicit_client = client is not None

        effective_key = self.api_key or os.getenv("GEMINI_API_KEY", "")
        is_placeholder = not effective_key or effective_key.strip().startswith("your_") or "placeholder" in effective_key.lower()

        if self.client is None and effective_key and not is_placeholder:
            if not HAS_GENAI:
                logger.warning("google-genai package is not installed in the active python environment.")
                self.client = None
            else:
                try:
                    self.client = genai.Client(api_key=effective_key)
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
        if not self._has_explicit_client:
            api_key_to_use = self.api_key if self.api_key is not None else os.getenv("GEMINI_API_KEY")
            if not api_key_to_use:
                self.client = None
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

            is_placeholder = api_key_to_use.strip().startswith("your_") or "placeholder" in api_key_to_use.lower()
            if is_placeholder:
                self.client = None
                return DiagnosisResult(
                    summary="Diagnosis service unavailable: GEMINI_API_KEY is missing or set to placeholder in .env.",
                    possible_causes=[],
                    evidence=[],
                    reasoning="A valid Gemini API key is required. Please edit your .env file and set GEMINI_API_KEY=your_actual_key from Google AI Studio (https://aistudio.google.com/).",
                    confidence="Low",
                    technician_checks=["Get a Gemini API key from https://aistudio.google.com/ and set GEMINI_API_KEY in .env"],
                    historical_case_ids=[],
                    grounded=False,
                    error="GEMINI_API_KEY missing or placeholder"
                )

            if self.client is None:
                if not HAS_GENAI:
                    return DiagnosisResult(
                        summary="Diagnosis service unavailable: 'google-genai' package is not installed in the active Python environment.",
                        possible_causes=[],
                        evidence=[],
                        reasoning="Missing dependency. Ensure you are running Python from the project's virtual environment (source venv/bin/activate).",
                        confidence="Low",
                        technician_checks=["Run command with ./venv/bin/python3 or activate venv"],
                        historical_case_ids=[],
                        grounded=False,
                        error="google-genai package not found in current environment"
                    )

                try:
                    self.client = genai.Client(api_key=api_key_to_use)
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

        elif self.client is None:
            return DiagnosisResult(
                summary="Diagnosis service unavailable: No Gemini client configured.",
                possible_causes=[],
                evidence=[],
                reasoning="Client is not available.",
                confidence="Low",
                technician_checks=[],
                historical_case_ids=[],
                grounded=False,
                error="No client available"
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
