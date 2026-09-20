import os
import sqlite3
import json
import logging
from typing import List, Optional
from app.feedback.models import FeedbackRecord

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "feedback.db")
)

class StorageError(Exception):
    pass

class FeedbackRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = os.path.abspath(db_path or DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initializes the SQLite feedback schema."""
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS technician_feedback (
                        feedback_id TEXT PRIMARY KEY,
                        workflow_id TEXT NOT NULL UNIQUE,
                        complaint TEXT NOT NULL,
                        equipment_type TEXT,
                        location TEXT,
                        retrieved_case_ids TEXT NOT NULL,
                        diagnosis_summary TEXT,
                        recommended_action TEXT,
                        technician_feedback TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        notes TEXT
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_workflow_id ON technician_feedback (workflow_id)
                """)
        except sqlite3.Error as e:
            raise StorageError(f"Failed to initialize feedback database schema: {e}") from e
        finally:
            conn.close()

    def save(self, record: FeedbackRecord) -> FeedbackRecord:
        """Saves a technician feedback record to SQLite."""
        sql = """
            INSERT INTO technician_feedback (
                feedback_id, workflow_id, complaint, equipment_type, location,
                retrieved_case_ids, diagnosis_summary, recommended_action,
                technician_feedback, timestamp, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (
                    record.feedback_id,
                    record.workflow_id,
                    record.complaint,
                    record.equipment_type,
                    record.location,
                    json.dumps(record.retrieved_case_ids),
                    record.diagnosis_summary,
                    record.recommended_action,
                    record.technician_feedback,
                    record.timestamp,
                    record.notes
                ))
            return record
        except sqlite3.IntegrityError as ie:
            raise ie
        except sqlite3.Error as e:
            raise StorageError(f"Database error while saving feedback: {e}") from e
        finally:
            conn.close()

    def _row_to_record(self, row: tuple) -> FeedbackRecord:
        return FeedbackRecord(
            feedback_id=row[0],
            workflow_id=row[1],
            complaint=row[2],
            equipment_type=row[3],
            location=row[4],
            retrieved_case_ids=json.loads(row[5]) if row[5] else [],
            diagnosis_summary=row[6],
            recommended_action=row[7],
            technician_feedback=row[8],
            timestamp=row[9],
            notes=row[10]
        )

    def get_by_id(self, feedback_id: str) -> Optional[FeedbackRecord]:
        """Retrieves a feedback record by its feedback_id."""
        sql = "SELECT feedback_id, workflow_id, complaint, equipment_type, location, retrieved_case_ids, diagnosis_summary, recommended_action, technician_feedback, timestamp, notes FROM technician_feedback WHERE feedback_id = ?"
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (feedback_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_record(row)
        except sqlite3.Error as e:
            raise StorageError(f"Database error while fetching feedback by ID: {e}") from e
        finally:
            conn.close()

    def get_by_workflow_id(self, workflow_id: str) -> Optional[FeedbackRecord]:
        """Retrieves a feedback record by its associated workflow_id."""
        sql = "SELECT feedback_id, workflow_id, complaint, equipment_type, location, retrieved_case_ids, diagnosis_summary, recommended_action, technician_feedback, timestamp, notes FROM technician_feedback WHERE workflow_id = ?"
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (workflow_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_record(row)
        except sqlite3.Error as e:
            raise StorageError(f"Database error while fetching feedback by workflow ID: {e}") from e
        finally:
            conn.close()

    def list_all(self, limit: int = 100) -> List[FeedbackRecord]:
        """Lists stored feedback records ordered by timestamp descending."""
        sql = "SELECT feedback_id, workflow_id, complaint, equipment_type, location, retrieved_case_ids, diagnosis_summary, recommended_action, technician_feedback, timestamp, notes FROM technician_feedback ORDER BY timestamp DESC LIMIT ?"
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (limit,))
            rows = cursor.fetchall()
            return [self._row_to_record(r) for r in rows]
        except sqlite3.Error as e:
            raise StorageError(f"Database error while listing feedback: {e}") from e
        finally:
            conn.close()

    def count(self) -> int:
        """Returns total count of stored feedback records."""
        sql = "SELECT COUNT(*) FROM technician_feedback"
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            raise StorageError(f"Database error counting feedback records: {e}") from e
        finally:
            conn.close()
