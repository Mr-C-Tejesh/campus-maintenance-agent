# Campus/Facility Infrastructure Decision-Support Agent

## Problem Statement
Facility managers need help diagnosing new equipment complaints by retrieving similar historical maintenance cases and generating evidence-grounded recommendations.

## Current Development Status
**Phase 6 Complete**: Technician Feedback Loop is fully implemented with persistent SQLite storage and duplicate submission prevention.

---

## End-to-End Architecture

```
Maintenance Complaint (+ Equipment Filter)
         ↓
  Validation (Input Sanitization & Categorical Checks)
         ↓
  Semantic Retrieval (ChromaDB + SentenceTransformers)
         ↓
  Diagnosis Service (Gemini LLM + Grounding Validator)
         ↓
  Recommendation Engine (Cost & Repair-Time Aggregation + Urgency Rules)
         ↓
  Workflow Result (WorkflowResult with unique workflow_id)
         ↓
  Technician Review
         ↓
  Feedback Service ("Correct" | "Incorrect" -> SQLite Storage)
```

---

## Technician Feedback Loop (`app/feedback/`)

The feedback system provides a compulsory operational review loop allowing technicians to mark generated results as either **`Correct`** or **`Incorrect`**.

### 1. Persistence & Data Schema
Stored locally in a persistent SQLite database at `data/feedback.db` (ignored by Git):
- `feedback_id`: Unique identifier (e.g. `fb-xxxxxxxx`).
- `workflow_id`: Unique workflow execution identifier (enforces 1 feedback per workflow run).
- `complaint`: Original user complaint text.
- `equipment_type`: Equipment type category.
- `location`: Facility location associated with the case.
- `retrieved_case_ids`: Exact JSON array of historical case IDs retrieved.
- `diagnosis_summary`: Diagnosis summary generated for the complaint.
- `recommended_action`: Action recommended to the technician.
- `technician_feedback`: Exactly `"Correct"` or `"Incorrect"`.
- `timestamp`: UTC ISO 8601 timestamp.
- `notes`: Optional technician qualitative notes.

### 2. Validation & Duplicate Safeguards
- **Strict Values**: Only `"Correct"` or `"Incorrect"` is accepted; arbitrary strings are rejected.
- **Workflow Integrity**: Case IDs and diagnosis fields must originate from an authentic `WorkflowResult`.
- **Duplicate Prevention**: Re-submitting feedback for an already-reviewed `workflow_id` is blocked and raises `DuplicateFeedbackError`.

> [!NOTE]
> **Product Guardrail**: Feedback is strictly persisted for operational auditing and future dataset curation. Feedback does **NOT** automatically retrain, fine-tune, or modify Gemini model weights or embeddings.

---

## Usage in Python

```python
from app.workflow import MaintenanceWorkflow
from app.feedback import FeedbackService

# 1. Run Workflow
workflow = MaintenanceWorkflow()
result = workflow.process_complaint(
    complaint="AC is running continuously but the room remains warm",
    equipment_type="Air Conditioning"
)

# 2. Record Technician Feedback
feedback_service = FeedbackService()
feedback = feedback_service.save_feedback(
    workflow_result=result,
    feedback="Correct",
    notes="Filter replacement resolved the cooling issue on-site."
)

print(f"Feedback recorded: {feedback.feedback_id} for workflow {feedback.workflow_id}")

# 3. Read Back Stored Feedback
all_feedback = feedback_service.list_feedback(limit=10)
for entry in all_feedback:
    print(f"[{entry.technician_feedback}] {entry.workflow_id}: {entry.complaint}")
```

---

## Quick Start & Demo Execution

### 1. Environment Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Run Workflow Demo (CLI)
```bash
python3 run.py
```

### 3. Run Automated Test Suite
```bash
# Run all 75 unit, integration, and feedback tests
./venv/bin/python3 -m unittest discover -s tests
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
│   ├── feedback/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── service.py
│   ├── models/
│   ├── recommendation/
│   │   ├── __init__.py
│   │   ├── cost_engine.py
│   │   ├── models.py
│   │   ├── prompt.py
│   │   ├── service.py
│   │   ├── urgency_engine.py
│   │   └── validator.py
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── document_builder.py
│   │   ├── retriever.py
│   │   └── vector_store.py
│   ├── services/
│   ├── utils/
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── orchestrator.py
│   │   └── state.py
│   ├── __init__.py
│   └── main.py
├── data/
│   ├── maintenance_records.csv
│   ├── chroma_db/  (ignored by git)
│   └── feedback.db (ignored by git)
├── tests/
│   ├── __init__.py
│   ├── test_data.py
│   ├── test_diagnosis.py
│   ├── test_feedback.py
│   ├── test_integration.py
│   ├── test_main.py
│   ├── test_recommendation.py
│   ├── test_retrieval.py
│   └── test_workflow.py
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── run.py
```
