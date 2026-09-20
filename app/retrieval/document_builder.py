from typing import Dict, Any, Tuple

def build_searchable_document(record: Dict[str, Any]) -> str:
    """
    Creates a deterministic, structured searchable text string from a maintenance record.
    Combines semantic fields: equipment_type, equipment_model, location, maintenance_type,
    complaint, symptoms, root_cause, action_taken.
    """
    return (
        f"Equipment Type: {record['equipment_type']}\n"
        f"Equipment Model: {record['equipment_model']}\n"
        f"Location: {record['location']}\n"
        f"Maintenance Type: {record['maintenance_type']}\n"
        f"Complaint: {record['complaint']}\n"
        f"Symptoms: {record['symptoms']}\n"
        f"Root Cause: {record['root_cause']}\n"
        f"Action Taken: {record['action_taken']}"
    )

def extract_metadata(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts metadata fields for filtering and display in ChromaDB.
    ChromaDB metadata values must be primitive types (str, int, float, bool).
    """
    return {
        "case_id": str(record["case_id"]),
        "equipment_type": str(record["equipment_type"]),
        "equipment_model": str(record["equipment_model"]),
        "location": str(record["location"]),
        "urgency": str(record["urgency"]),
        "maintenance_type": str(record["maintenance_type"]),
        "repair_cost": float(record["repair_cost"]),
        "repair_time_hours": float(record["repair_time_hours"]),
        "date_reported": str(record["date_reported"]),
        "complaint": str(record["complaint"]),
        "symptoms": str(record["symptoms"]),
        "root_cause": str(record["root_cause"]),
        "action_taken": str(record["action_taken"])
    }

def build_document_and_metadata(record: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    return build_searchable_document(record), extract_metadata(record)
