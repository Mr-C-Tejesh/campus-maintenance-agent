# Campus/Facility Infrastructure Decision-Support Agent

## Problem Statement
Facility managers need help diagnosing new equipment complaints by retrieving similar historical maintenance cases and generating evidence-grounded recommendations.

## Current Development Status
**Phase 5 Complete**: End-to-End Decision Workflow Orchestration is fully implemented with LangGraph and Python pipeline coordination.

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
  Structured Workflow Result (WorkflowResult / Decision-Support)
```

---

## LangGraph & Orchestration Rationale

The project track is **Multi-Agent Orchestration & Decision Support**.

### 1. LangGraph StateGraph Integration (`app/workflow/graph.py`)
A minimal 3-node `StateGraph` maps 1-to-1 to the linear maintenance workflow:
```
START ──> retrieve_node ──> diagnose_node ──> recommend_node ──> END
```
- **Modular Delegation**: Each node invokes the underlying `MaintenanceRetriever`, `DiagnosisService`, and `RecommendationService` instances directly without duplicating business logic.
- **State Management**: Typed `GraphState` preserves `complaint`, `equipment_type`, `retrieved_cases`, `diagnosis`, `recommendation`, `workflow_status`, and `error`.

### 2. Native Python Workflow Orchestrator (`app/workflow/orchestrator.py`)
- Callable via `MaintenanceWorkflow.process_complaint(complaint, equipment_type=None)`.
- Returns a top-level `WorkflowResult` object containing stage outputs and workflow status.

### 3. Stage Failure & Status Codes
- **`SUCCESS`**: Pipeline completed cleanly with grounded evidence.
- **`NO_RELEVANT_CASES`**: Valid complaint executed, but no matching historical cases found. Safe ungrounded fallbacks triggered.
- **`INVALID_INPUT`**: Aborted early due to empty text or unsupported equipment.
- **`RETRIEVAL_FAILED`**: Vector store database connection or query failure.
- **`DIAGNOSIS_FAILED`**: LLM diagnosis error (e.g. missing `GEMINI_API_KEY`), but recommendation fallback completes cleanly.
- **`RECOMMENDATION_FAILED`**: LLM recommendation error.

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
# Run manual end-to-end complaint workflow demo
python3 run.py
```

### 3. Usage in Python
```python
from app.workflow import MaintenanceWorkflow

workflow = MaintenanceWorkflow()
result = workflow.process_complaint(
    complaint="AC is running continuously but the room remains warm",
    equipment_type="Air Conditioning"
)

print("Workflow Status:", result.workflow_status)
print("Retrieved Cases:", [c.case_id for c in result.retrieved_cases])

if result.diagnosis:
    print("Diagnosis Summary:", result.diagnosis.summary)

if result.recommendation:
    print("Urgency:", result.recommendation.urgency)
    print("Cost Ref:", result.recommendation.estimated_cost.formatted_reference)
    print("Action:", result.recommendation.recommended_action)
```

---

## Testing Approach

Run full automated test suite (65 tests across all phases, including LangGraph execution tests and ChromaDB + LLM integration tests):

```bash
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
│   └── chroma_db/  (ignored by git)
├── tests/
│   ├── __init__.py
│   ├── test_data.py
│   ├── test_diagnosis.py
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
