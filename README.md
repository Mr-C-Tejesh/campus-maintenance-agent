# Campus Maintenance Agent

**Evidence-grounded AI decision support for campus and facility maintenance teams.**

Campus Maintenance Agent converts a natural-language equipment complaint into a traceable maintenance decision. It retrieves similar historical cases, generates a grounded diagnosis, recommends a likely action, estimates historical cost/repair time/urgency, and records technician feedback.

> **Hackathon note:** the demo uses a synthetic maintenance dataset. This is decision support, not autonomous repair; qualified technicians still perform physical inspection and repairs.

## Architecture

```text
React Dashboard
      ↓
FastAPI API
      ↓
Input Validation
      ↓
ChromaDB Semantic Retrieval
(all-MiniLM-L6-v2)
      ↓
Historical Evidence
      ↓
Gemini Diagnosis
+ grounding validator
      ↓
Recommendation
Gemini action text
+
deterministic cost/time/urgency
      ↓
Technician Review
Correct / Incorrect
      ↓
SQLite Audit Log
```

LangGraph orchestrates the core workflow:

```text
START → retrieve → diagnose → recommend → END
```

## Key technical choices

### RAG / semantic retrieval
- **Vector store:** ChromaDB
- **Embeddings:** Sentence Transformers `all-MiniLM-L6-v2`
- **Distance:** cosine distance
- **Default top-k:** 5
- **Relevance threshold:** cosine distance ≤ 0.75
- **Dataset:** 250 synthetic records covering Air Conditioning, Generator, and Elevator cases

Searchable documents combine equipment type/model, location, maintenance type, complaint, symptoms, root cause, and action taken. Original metadata, including case IDs, stays attached to the retrieved evidence.

### Evidence-grounded diagnosis
Gemini receives the complaint plus retrieved cases and returns structured diagnosis data including causes, evidence, reasoning, confidence, technician checks, and supporting case IDs.

The application validates the output. A supporting case ID must correspond to a case actually retrieved for that workflow. With no useful evidence, the system falls back to a low-confidence, inspection-first response.

### Recommendation engine
The LLM generates technician-friendly action text. Deterministic application logic computes:
- historical minimum / maximum / median repair cost
- historical minimum / maximum / median repair time
- urgency using complaint signals, retrieved-case urgency, and diagnosis confidence/likelihood

This keeps operational numbers reproducible and explainable.

### Technician feedback
Each analysis receives a server-generated workflow ID. Technicians can mark the result **Correct** or **Incorrect** and add notes. Feedback is stored with the complaint, location, retrieved case IDs, diagnosis, recommendation and timestamp.

**Feedback does not automatically retrain Gemini or modify the embedding model.**

## Tech stack

**Backend:** Python, FastAPI, LangGraph, ChromaDB, Sentence Transformers, Google Gemini via `google-genai`, SQLite

**Frontend:** React 18, Vite 5, plain CSS

**Safeguards:** input validation, equipment validation, relevance thresholding, grounding validation, server-generated workflow IDs, duplicate feedback protection, controlled fallbacks, environment variables for secrets.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/v1/analyze` | Retrieval → diagnosis → recommendation |
| POST | `/api/v1/feedback` | Correct/Incorrect technician feedback |
| GET | `/api/v1/feedback?limit=50` | Recent persisted feedback |

Example:

```json
{
  "complaint": "AC is running continuously but the room remains warm",
  "equipment_type": "Air Conditioning",
  "location": "Laboratory Block",
  "top_k": 5
}
```

## Run locally

### Backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set:

```env
GEMINI_API_KEY=your_actual_key
GEMINI_MODEL=gemini-3.6-flash
```

Run:

```bash
python3 run.py --server
```

Swagger: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: `http://localhost:5173`

For a hosted backend, configure:

```env
VITE_API_BASE_URL=https://your-backend-url
```

### Tests

```bash
./venv/bin/python3 -m unittest discover -s tests -p "test_*.py"
```

## Deployment

### Render backend
- Runtime: Python 3
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.api.app:app --host 0.0.0.0 --port $PORT`
- Environment variables: `GEMINI_API_KEY`, `GEMINI_MODEL` (optional), `FRONTEND_ORIGIN`

### Vercel frontend
- Framework: Vite
- Root directory: `frontend`
- Build: `npm run build`
- Output: `dist`
- Environment variable: `VITE_API_BASE_URL`

After the Vercel URL is known, set `FRONTEND_ORIGIN` on Render and redeploy the backend.

## Limitations

- The maintenance archive is synthetic rather than connected to a real CMMS.
- ChromaDB and SQLite are local-storage choices for the prototype.
- The system is decision support, not autonomous repair.
- Diagnosis quality depends on historical data coverage and retrieval quality.
- Production use would need managed persistence, authentication/RBAC, stronger observability, and formal evaluation against real maintenance outcomes.

## Future scope

Real CMMS/work-order integration, managed PostgreSQL + pgvector, authentication and technician roles, retrieval/diagnosis evaluation dashboards, trend analysis, and multimodal evidence such as photos, meter readings and error-code scans.

## Project structure

```text
campus-maintenance-agent/
├── app/
│   ├── api/              # FastAPI routes/schemas
│   ├── data/             # Dataset loading/validation
│   ├── diagnosis/        # Gemini diagnosis + grounding
│   ├── feedback/         # Technician feedback + SQLite
│   ├── recommendation/   # Cost/time/urgency + action
│   ├── retrieval/        # ChromaDB semantic search
│   └── workflow/         # LangGraph orchestration
├── data/maintenance_records.csv
├── frontend/             # React dashboard
├── tests/
├── requirements.txt
└── run.py
```
