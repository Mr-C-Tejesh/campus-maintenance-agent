# Campus/Facility Infrastructure Decision-Support Agent

## Problem Statement
Facility managers need help diagnosing new equipment complaints by retrieving similar historical maintenance cases and generating evidence-grounded recommendations.

## Current Development Status
**Phase 2 Complete**: Semantic Maintenance Retrieval Layer is fully implemented using ChromaDB and SentenceTransformers.

---

## Retrieval Architecture

```
Maintenance Records (CSV)
         ↓
  Document Builder (Structured Text + Metadata)
         ↓
  Embeddings (all-MiniLM-L6-v2)
         ↓
  ChromaDB Vector Store (data/chroma_db)
         ↓
  Similarity Search & Relevance Filtering
         ↓
  Relevant Historical Cases (RetrievalResult)
```

### 1. Document Representation & Metadata
Each record from `data/maintenance_records.csv` is split into:
- **Searchable Text**: Structured combination of `equipment_type`, `equipment_model`, `location`, `maintenance_type`, `complaint`, `symptoms`, `root_cause`, and `action_taken`.
- **Metadata**: Preserves primitive fields (`case_id`, `equipment_type`, `equipment_model`, `location`, `urgency`, `maintenance_type`, `repair_cost`, `repair_time_hours`, `date_reported`, `complaint`, `symptoms`, `root_cause`, `action_taken`).

### 2. Embedding Model & Vector Store
- **Embedding Model**: `all-MiniLM-L6-v2` via `sentence-transformers` (runs locally, 384 dimensions).
- **Vector Store**: Local persistent ChromaDB database located at `data/chroma_db/`.
- **Distance Metric**: Cosine distance (`hnsw:space`: `cosine`).
- **Idempotence & Duplicate Prevention**: `case_id` is used as the document primary key with ChromaDB `upsert` operations.

### 3. Retrieval Interface
Located at `app/retrieval/retriever.py`, the `MaintenanceRetriever` class exposes:

```python
from app.retrieval import initialize_vector_store, MaintenanceRetriever

# Initialize local vector store
vector_store = initialize_vector_store()
retriever = MaintenanceRetriever(vector_store)

# Perform semantic search
results = retriever.search(
    complaint="AC is running continuously but the room is still warm",
    equipment_type="Air Conditioning",  # Optional: "Air Conditioning" | "Generator" | "Elevator"
    top_k=5,
    max_distance=0.75
)

for case in results:
    print(case.case_id, case.similarity_score, case.complaint)
```

### 4. Safety & Quality Controls
- **Empty / Short Queries**: Returns empty list `[]` safely for empty or `< 3` character complaints.
- **Unsupported Equipment**: Raises `ValueError` for equipment types outside allowed set (`Air Conditioning`, `Generator`, `Elevator`).
- **Relevance Thresholding**: Filters out low-relevance results exceeding max distance (default `0.75`).
- **Strict Data Contract**: Only returns existing, verified historical cases from `data/maintenance_records.csv`. Never generates synthetic cases.

---

## Dataset Information

- **Path**: `data/maintenance_records.csv`
- **Size**: 250 records across Air Conditioning, Generator, and Elevator equipment.
- **Data Loader**: `app/data/loader.py` (`load_and_validate_dataset`).

---

## Getting Started

### 1. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the application
```bash
python3 run.py
```

### 4. Run tests
```bash
# Run all unit and retrieval integration tests
python3 -m unittest discover -s tests
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
│   ├── test_main.py
│   └── test_retrieval.py
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── run.py
```
