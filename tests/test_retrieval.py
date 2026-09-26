import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from app.data.loader import load_and_validate_dataset
from app.retrieval.vector_store import VectorStoreManager, initialize_vector_store
from app.retrieval.retriever import MaintenanceRetriever, RetrievalResult, RetrievalError

class TestSemanticRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.csv_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'maintenance_records.csv'
        )
        cls.raw_records = load_and_validate_dataset(cls.csv_path)
        cls.valid_case_ids = {r["case_id"] for r in cls.raw_records}
        
        # Temporary directory for isolated vector store testing
        cls.temp_dir = tempfile.mkdtemp(prefix="test_vector_")
        cls.vector_store = initialize_vector_store(
            csv_path=cls.csv_path,
            persist_directory=cls.temp_dir,
            force_rebuild=False
        )
        cls.retriever = MaintenanceRetriever(cls.vector_store)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_01_vector_store_initialization(self):
        """1. Vector store initialization succeeds."""
        self.assertIsNotNone(self.vector_store)
        self.assertIsNotNone(self.vector_store.collection)

    def test_02_all_records_indexed(self):
        """2. All 250 expected records are indexed."""
        count = self.vector_store.collection.count()
        self.assertEqual(count, len(self.raw_records))
        self.assertEqual(count, 250)

    def test_03_case_ids_preserved(self):
        """3. Case IDs are preserved in index."""
        sample_results = self.vector_store.collection.get(limit=10)
        retrieved_ids = sample_results.get("ids", [])
        self.assertTrue(len(retrieved_ids) > 0)
        for cid in retrieved_ids:
            self.assertIn(cid, self.valid_case_ids)

    def test_04_metadata_preserved(self):
        """4. Metadata fields are preserved and correctly typed."""
        sample_results = self.vector_store.collection.get(limit=5, include=["metadatas"])
        metadatas = sample_results.get("metadatas", [])
        self.assertTrue(len(metadatas) > 0)
        for meta in metadatas:
            self.assertIn("case_id", meta)
            self.assertIn("equipment_type", meta)
            self.assertIn("equipment_model", meta)
            self.assertIn("location", meta)
            self.assertIn("urgency", meta)
            self.assertIn("maintenance_type", meta)
            self.assertIsInstance(meta["repair_cost"], float)
            self.assertIsInstance(meta["repair_time_hours"], float)
            self.assertIn("date_reported", meta)

    def test_05_ac_complaint_retrieval(self):
        """5. Known AC complaint retrieves AC-related cases."""
        query = "AC is running continuously but the room is still not cooling properly."
        results = self.retriever.search(query, top_k=5)
        self.assertTrue(len(results) > 0)
        for r in results:
            self.assertIn(r.case_id, self.valid_case_ids)

        ac_count = sum(1 for r in results if r.equipment_type == "Air Conditioning")
        self.assertGreater(ac_count, 0, "Expected at least one AC case for AC query")

    def test_06_generator_complaint_retrieval(self):
        """6. Known generator complaint retrieves generator cases."""
        query = "Generator failed to start during a power outage and the battery indicator is low."
        results = self.retriever.search(query, top_k=5)
        self.assertTrue(len(results) > 0)
        for r in results:
            self.assertIn(r.case_id, self.valid_case_ids)

        gen_count = sum(1 for r in results if r.equipment_type == "Generator")
        self.assertGreater(gen_count, 0, "Expected at least one Generator case for Generator query")

    def test_07_elevator_complaint_retrieval(self):
        """7. Known elevator complaint retrieves elevator cases."""
        query = "Elevator doors are not closing properly and the lift is intermittently stopping."
        results = self.retriever.search(query, top_k=5)
        self.assertTrue(len(results) > 0)
        for r in results:
            self.assertIn(r.case_id, self.valid_case_ids)

        el_count = sum(1 for r in results if r.equipment_type == "Elevator")
        self.assertGreater(el_count, 0, "Expected at least one Elevator case for Elevator query")

    def test_08_paraphrased_complaint_retrieval(self):
        """8. Semantically similar paraphrased query retrieves related cases."""
        query = "Air conditioner blows warm air and fails to chill the auditorium."
        results = self.retriever.search(query, top_k=5)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].equipment_type, "Air Conditioning")

    def test_09_equipment_filtering(self):
        """9. Equipment filtering restricts results strictly to specified type."""
        query = "Intermittent power trip and noise issue"
        results = self.retriever.search(query, equipment_type="Generator", top_k=5)
        self.assertTrue(len(results) > 0)
        for r in results:
            self.assertEqual(r.equipment_type, "Generator")

    def test_10_empty_complaint_handling(self):
        """10. Empty and very short complaints are handled safely."""
        self.assertEqual(self.retriever.search(""), [])
        self.assertEqual(self.retriever.search("   "), [])
        self.assertEqual(self.retriever.search("a"), [])
        self.assertEqual(self.retriever.search("  ab "), [])

    def test_11_unsupported_equipment_handling(self):
        """11. Unsupported equipment type raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.retriever.search("Cooling issue", equipment_type="Solar Panel")
        self.assertIn("Unsupported equipment_type", str(ctx.exception))

    def test_12_irrelevant_query_handling(self):
        """12. Irrelevant query with strict max_distance returns empty/filtered list."""
        query = "quantum mechanics string theory astrophysics"
        results = self.retriever.search(query, max_distance=0.01)
        self.assertEqual(len(results), 0, "Irrelevant query should return 0 results under strict distance threshold")

    def test_13_repeated_initialization_no_duplicates(self):
        """13. Repeated startup does not duplicate records in index."""
        initial_count = self.vector_store.collection.count()
        store2 = initialize_vector_store(
            csv_path=self.csv_path,
            persist_directory=self.temp_dir,
            force_rebuild=False
        )
        self.assertEqual(store2.collection.count(), initial_count)

    def test_14_retrieval_result_schema(self):
        """14. Retrieval result object schema validation."""
        query = "Generator low oil pressure warning"
        results = self.retriever.search(query, top_k=1)
        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertIsInstance(r, RetrievalResult)
        self.assertIn(r.case_id, self.valid_case_ids)
        self.assertGreaterEqual(r.distance, 0.0)
        self.assertGreaterEqual(r.similarity_score, 0.0)
        self.assertLessEqual(r.similarity_score, 1.0)
        
        d = r.to_dict()
        required_keys = {
            "case_id", "distance", "similarity_score", "complaint", "symptoms",
            "root_cause", "action_taken", "equipment_type", "equipment_model",
            "location", "repair_cost", "repair_time_hours", "urgency",
            "maintenance_type", "date_reported"
        }
        self.assertTrue(required_keys.issubset(set(d.keys())))

    def test_15_top_k_parameter(self):
        """15. top_k parameter limits the number of returned cases."""
        query = "Cooling system failure"
        results_3 = self.retriever.search(query, top_k=3, max_distance=1.0)
        self.assertLessEqual(len(results_3), 3)

    def test_16_embedding_api_failure_handling(self):
        """16. Safe error handling when embedding API fails."""
        with patch.object(self.vector_store, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.embed_content.side_effect = Exception("API connection timeout")
            mock_get_client.return_value = mock_client

            with self.assertRaises(RetrievalError) as ctx:
                self.retriever.search("AC cooling failure")
            self.assertIn("Vector store query failed", str(ctx.exception))

    def test_17_persisted_index_loading(self):
        """17. Persisted index is loaded into memory without remote API calls."""
        store = VectorStoreManager(persist_directory=self.temp_dir)
        self.assertTrue(store.is_indexed())
        self.assertEqual(store.count(), 250)
        # Client should remain uninstantiated until query execution
        self.assertIsNone(store._client)

if __name__ == '__main__':
    unittest.main()
