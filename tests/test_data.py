import unittest
import os
import csv
from app.data.loader import load_and_validate_dataset, DataValidationError

class TestMaintenanceDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'maintenance_records.csv'
        )
        cls.required_columns = {
            "case_id", "equipment_type", "equipment_model", "location",
            "complaint", "symptoms", "root_cause", "action_taken",
            "repair_cost", "repair_time_hours", "urgency", "maintenance_type",
            "date_reported"
        }

    def test_01_dataset_exists(self):
        self.assertTrue(os.path.exists(self.dataset_path), "Dataset file does not exist")

    def test_02_expected_columns_exist(self):
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.assertTrue(reader.fieldnames, "CSV has no headers")
            missing = self.required_columns - set(reader.fieldnames)
            self.assertEqual(len(missing), 0, f"Missing columns: {missing}")

    def test_03_approx_250_records(self):
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            reader = list(csv.DictReader(f))
            self.assertTrue(240 <= len(reader) <= 260, f"Expected ~250 records, got {len(reader)}")

    def test_04_case_ids_unique(self):
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            case_ids = [row["case_id"] for row in reader]
            self.assertEqual(len(case_ids), len(set(case_ids)), "case_id values are not unique")

    def test_05_required_fields_not_empty(self):
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                for col in self.required_columns:
                    self.assertTrue(row.get(col) and str(row[col]).strip() != "", f"Empty field {col} at row {i+2}")

    def test_06_valid_equipment_types(self):
        allowed = {"Air Conditioning", "Generator", "Elevator"}
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                self.assertIn(row["equipment_type"], allowed, f"Invalid equipment_type at row {i+2}")

    def test_07_valid_urgency_values(self):
        allowed = {"Low", "Medium", "High", "Critical"}
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                self.assertIn(row["urgency"], allowed, f"Invalid urgency at row {i+2}")

    def test_08_valid_maintenance_type(self):
        allowed = {"Corrective", "Preventive"}
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                self.assertIn(row["maintenance_type"], allowed, f"Invalid maintenance_type at row {i+2}")

    def test_09_repair_cost_numeric(self):
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                try:
                    float(row["repair_cost"])
                except ValueError:
                    self.fail(f"repair_cost not numeric at row {i+2}: {row['repair_cost']}")

    def test_10_repair_time_numeric(self):
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                try:
                    float(row["repair_time_hours"])
                except ValueError:
                    self.fail(f"repair_time_hours not numeric at row {i+2}: {row['repair_time_hours']}")

    def test_11_dataset_loader_success(self):
        records = load_and_validate_dataset(self.dataset_path)
        self.assertEqual(len(records), 250)

    def test_12_duplicate_case_ids_detected(self):
        # Create a temporary invalid file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, newline='', encoding='utf-8') as tmp:
            writer = csv.DictWriter(tmp, fieldnames=list(self.required_columns))
            writer.writeheader()
            row = {
                "case_id": "CASE-0001", "equipment_type": "Elevator", "equipment_model": "X",
                "location": "L", "complaint": "C", "symptoms": "S", "root_cause": "R",
                "action_taken": "A", "repair_cost": "100", "repair_time_hours": "2",
                "urgency": "High", "maintenance_type": "Corrective", "date_reported": "2023-01-01"
            }
            writer.writerow(row)
            
            row2 = row.copy()
            row2["location"] = "M" # Change something so it's not a complete duplicate row
            writer.writerow(row2)
            tmp_name = tmp.name

        try:
            with self.assertRaises(DataValidationError) as context:
                load_and_validate_dataset(tmp_name)
            self.assertIn("Duplicate case_id", str(context.exception))
        finally:
            os.remove(tmp_name)

if __name__ == '__main__':
    unittest.main()
