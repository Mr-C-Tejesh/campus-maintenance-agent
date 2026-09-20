# Campus/Facility Infrastructure Decision-Support Agent

## Problem Statement
Facility managers need help diagnosing new equipment complaints by retrieving similar historical maintenance cases and generating evidence-grounded recommendations.

## Current Development Status
**Phase 3 Complete**: Evidence-Grounded Diagnosis Layer is fully implemented using Google Gemini LLM (`google-genai`), strict grounding validation, and ChromaDB vector retrieval.

---

## Architecture Overview

```
New Complaint + Equipment Filter
         ↓
  MaintenanceRetriever (ChromaDB + SentenceTransformers)
         ↓
  Retrieved Historical Cases (RetrievalResult)
         ↓
  DiagnosisService (Gemini LLM + Grounding Validator)
         ↓
  Structured Evidence-Grounded Diagnosis (DiagnosisResult)
```

---

## Retrieval & Diagnosis System

### 1. Vector Retrieval Layer (`app/retrieval/`)
- **Embedding Model**: `all-MiniLM-L6-v2` via `sentence-transformers` (384 dimensions).
- **Vector Store**: Local persistent ChromaDB database located at `data/chroma_db/`.
- **Distance Metric**: Cosine distance (`hnsw:space`: `cosine`).
- **Idempotence**: `case_id` is used as primary key with `upsert` operations.

### 2. Diagnosis Layer (`app/diagnosis/`)
- **LLM Provider**: Google Gemini (`gemini-2.5-flash`) via the official `google-genai` Python SDK.
- **Environment Variable**: `GEMINI_API_KEY` (configured via environment or `.env`).
- **Evidence-Grounding Strategy**:
  - **HISTORICAL EVIDENCE**: Factual symptoms, root causes, and actions taken directly from retrieved historical cases.
  - **INFERENCE**: The model's technical reasoning connecting new complaints to retrieved evidence.
- **Hallucination Safeguards**:
  - Raw LLM output is validated by `validate_diagnosis_output`.
  - Every cited `case_id` is strictly cross-checked against the actual set of retrieved cases. Any unretrieved/hallucinated `case_id` is automatically rejected.
- **No-Evidence Fallback**:
  - If no relevant historical cases are retrieved (or complaint is empty), the service returns a safe fallback result with `grounded=False`, `confidence="Low"`, and mandatory physical technician inspection steps.
- **Qualitative Confidence**:
  - Categorized strictly as `"High"`, `"Medium"`, or `"Low"` reflecting evidence strength (no arbitrary calibrated probability numbers).

---

## Diagnosis Interface Usage

```python
from app.retrieval import initialize_vector_store, MaintenanceRetriever
from app.diagnosis import DiagnosisService

# 1. Initialize Retrieval & Vector Store
vector_store = initialize_vector_store()
retriever = MaintenanceRetriever(vector_store)

# 2. Retrieve relevant historical cases
retrieved_cases = retriever.search(
    complaint="AC is running continuously but the room is still warm",
    equipment_type="Air Conditioning",
    top_k=5
)

# 3. Generate grounded diagnosis
diagnosis_service = DiagnosisService()  # reads GEMINI_API_KEY from environment
diagnosis = diagnosis_service.diagnose(
    complaint="AC is running continuously but the room is still warm",
    retrieved_cases=retrieved_cases,
    equipment_type="Air Conditioning"
)

print("Summary:", diagnosis.summary)
print("Confidence:", diagnosis.confidence)
print("Grounded:", diagnosis.grounded)
print("Cited Cases:", diagnosis.historical_case_ids)

for cause in diagnosis.possible_causes:
    print(f"- {cause.cause} ({cause.likelihood}): {cause.explanation}")
```

---

## Testing Approach

The test suite includes deterministic offline unit & integration tests using dependency injection / mock clients to verify LLM response parsing, grounding enforcement, and failure handling without requiring live API calls during automated test runs.

```bash
# Run full unit and integration test suite (40 tests)
python3 -m unittest discover -s tests
```

---

## Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Set your Gemini API key in `.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

---

## Current Project Structure

```
campus-maintenance-agent/
├── app/
│   ├── agents/
│   ├── config/
│   ├── data/
│   │   ├── __init__.py
│   │   └── loader.py
│   ├── diagnosis/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── prompt.py
│   │   ├── service.py
│   │   └── validator.py
│   ├── models/
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── document_builder.py
│   │   ├── retriever.py
│   │   └── vector_store.py
│   ├── services/
│   ├── utils/
│   ├── __init__.py
│   └── main.py
├── data/
│   ├── maintenance_records.csv
│   └── chroma_db/  (ignored by git)
├── tests/
│   ├── __init__.py
│   ├── test_data.py
│   ├── test_diagnosis.py
│   ├── test_main.py
│   └── test_retrieval.py
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── run.py
```
