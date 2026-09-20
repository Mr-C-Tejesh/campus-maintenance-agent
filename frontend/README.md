# Campus Maintenance Intelligence — Frontend Operations Dashboard

A lightweight, institutional facility management dashboard built with **React**, **Vite**, and plain **CSS**, providing real-time decision support for campus equipment complaints.

---

## 1. Features & Design Philosophy

- **Operations Console Aesthetics**: Styled for facility management and industrial operations rather than generic AI chatbots. Uses the curated warm palette (`#F5F4F0` background, `#FFFFFF` surfaces, `#B7791F` operational amber accent) and **IBM Plex Sans** typography.
- **Distinct Visual Hierarchies**:
  - **Historical Evidence**: Tabular data records with similarity score percentage, root cause, symptoms, cost, and repair time. Expandable for full record inspection.
  - **AI Analysis**: Grounded diagnosis summary, qualitative confidence badges, potential causes with likelihood, and transparent reasoning trace.
  - **Recommended Action**: Action guidance, historical cost reference (`formatted_range` and median), repair-time reference, and deterministic urgency rating (`Low`, `Medium`, `High`, `Critical`).
  - **Technician Verification**: Actionable check-style checklist.
  - **Technician Feedback Loop**: Direct operational review (`Correct` / `Incorrect`) with optional technician notes, persisted to SQLite.
  - **Audit Trail**: Real-time listing of recently recorded technician reviews.
- **Zero Fabricated Metrics**: Strictly displays authentic numbers and records from the FastAPI backend.

---

## 2. API Endpoints Consumed

The dashboard connects to the following FastAPI backend endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | `GET` | Live backend health and status monitoring |
| `/api/v1/analyze` | `POST` | Executes retrieval, diagnosis, and recommendation workflow |
| `/api/v1/feedback` | `POST` | Persists technician review (`Correct` / `Incorrect`) |
| `/api/v1/feedback` | `GET` | Retrieves audit log of recent technician reviews |

---

## 3. Configuration

Configuration is managed via environment variables:

```bash
# frontend/.env
VITE_API_BASE_URL=http://localhost:8000
```

Never place API keys or backend secrets in frontend environment variables.

---

## 4. Setup & Running Locally

### Step 1: Start the Backend API Server
From the project root:
```bash
python run.py --server
# Backend runs at http://localhost:8000
```

### Step 2: Install Frontend Dependencies & Start Dev Server
From the `frontend/` directory:
```bash
npm install
npm run dev
# Frontend runs at http://localhost:5173
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 5. Build for Production

```bash
npm run build
```
Build outputs are placed in `frontend/dist/`.
