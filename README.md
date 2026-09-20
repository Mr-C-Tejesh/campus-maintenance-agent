# Campus/Facility Infrastructure Decision-Support Agent

## Problem Statement
Facility managers need help diagnosing new equipment complaints by retrieving similar historical maintenance cases and generating evidence-grounded recommendations.

## Current Development Status
Phase 1: Maintenance dataset foundation is complete. (No RAG, agents, or databases implemented yet).

## Dataset Information

**Purpose**: Provide a synthetic historical maintenance dataset (approx 250 records) for testing semantic retrieval logic, containing repeated issue patterns and natural language complaints across Air Conditioning, Generator, and Elevator equipment.

**Size**: ~250 records.

**Schema**:
* `case_id`: Unique identifier (e.g., CASE-0001)
* `equipment_type`: Air Conditioning | Generator | Elevator
* `equipment_model`: Synthetic model name
* `location`: Realistic campus location
* `complaint`: Original user complaint (natural language)
* `symptoms`: Observable symptoms
* `root_cause`: Historical diagnosed cause
* `action_taken`: Historical action performed
* `repair_cost`: Cost in INR (numeric)
* `repair_time_hours`: Repair duration (numeric)
* `urgency`: Low | Medium | High | Critical
* `maintenance_type`: Corrective | Preventive
* `date_reported`: Historical date

**Data Loader**: Located at `app/data/loader.py`, the `load_and_validate_dataset` function reads the CSV using the standard library, validates required columns, data types, allowed categorical values, detects missing values and duplicate rows/IDs, and returns a clean in-memory dictionary representation.

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
# Run all tests
python3 -m unittest discover -s tests
```

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
│   ├── services/
│   ├── utils/
│   ├── __init__.py
│   └── main.py
├── data/
│   └── maintenance_records.csv
├── tests/
│   ├── __init__.py
│   ├── test_main.py
│   └── test_data.py
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── run.py
```
