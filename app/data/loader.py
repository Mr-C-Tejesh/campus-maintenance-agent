import csv
from typing import List, Dict, Any

class DataValidationError(Exception):
    pass

def load_and_validate_dataset(filepath: str) -> List[Dict[str, Any]]:
    required_columns = {
        "case_id", "equipment_type", "equipment_model", "location",
        "complaint", "symptoms", "root_cause", "action_taken",
        "repair_cost", "repair_time_hours", "urgency", "maintenance_type",
        "date_reported"
    }
    
    allowed_equipment_types = {"Air Conditioning", "Generator", "Elevator"}
    allowed_urgencies = {"Low", "Medium", "High", "Critical"}
    allowed_maintenance_types = {"Corrective", "Preventive"}
    
    records = []
    case_ids = set()
    row_signatures = set()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # 2. Validate required columns
        if not reader.fieldnames:
            raise DataValidationError("CSV file is empty or missing headers.")
        
        missing_cols = required_columns - set(reader.fieldnames)
        if missing_cols:
            raise DataValidationError(f"Missing required columns: {missing_cols}")
            
        for row_num, row in enumerate(reader, start=2):
            # 5. Detect missing required values
            for col in required_columns:
                if not row.get(col) or str(row[col]).strip() == "":
                    raise DataValidationError(f"Missing value for {col} in row {row_num}")
            
            # 6. Detect duplicate case IDs
            case_id = row["case_id"]
            if case_id in case_ids:
                raise DataValidationError(f"Duplicate case_id found: {case_id} in row {row_num}")
            case_ids.add(case_id)
            
            # 7. Detect completely duplicated rows (excluding case_id for true duplicate data check, but case_id must be unique)
            # Actually, the requirement says "Detect completely duplicated rows". 
            # A completely duplicated row would mean every field is identical.
            row_signature = tuple(row[col] for col in reader.fieldnames)
            if row_signature in row_signatures:
                raise DataValidationError(f"Completely duplicated row found at row {row_num}")
            row_signatures.add(row_signature)
            
            # 4. Validate allowed categorical values
            if row["equipment_type"] not in allowed_equipment_types:
                raise DataValidationError(f"Invalid equipment_type in row {row_num}: {row['equipment_type']}")
            
            if row["urgency"] not in allowed_urgencies:
                raise DataValidationError(f"Invalid urgency in row {row_num}: {row['urgency']}")
                
            if row["maintenance_type"] not in allowed_maintenance_types:
                raise DataValidationError(f"Invalid maintenance_type in row {row_num}: {row['maintenance_type']}")
                
            # 3. Validate data types
            try:
                repair_cost = float(row["repair_cost"])
            except ValueError:
                raise DataValidationError(f"Invalid repair_cost in row {row_num}: {row['repair_cost']}")
                
            try:
                repair_time = float(row["repair_time_hours"])
            except ValueError:
                raise DataValidationError(f"Invalid repair_time_hours in row {row_num}: {row['repair_time_hours']}")
                
            # Create clean in-memory representation
            clean_row = {k: v.strip() for k, v in row.items()}
            clean_row["repair_cost"] = repair_cost
            clean_row["repair_time_hours"] = repair_time
            
            records.append(clean_row)
            
    return records
