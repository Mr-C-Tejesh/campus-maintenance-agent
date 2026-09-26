import os
import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from app.data.loader import load_and_validate_dataset
from app.retrieval.document_builder import build_document_and_metadata

logger = logging.getLogger(__name__)

DEFAULT_INDEX_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "gemini_embeddings.json")
)
DEFAULT_CSV_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "maintenance_records.csv")
)
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"

class VectorStoreManager:
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        index_path: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.model_name = model_name or os.getenv("GEMINI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        
        if index_path:
            self.index_path = os.path.abspath(index_path)
        elif persist_directory:
            self.index_path = os.path.abspath(os.path.join(persist_directory, "gemini_embeddings.json"))
        else:
            self.index_path = DEFAULT_INDEX_PATH

        self._client = None
        self.records: List[Dict[str, Any]] = []
        self.embeddings_matrix: Optional[np.ndarray] = None
        self.case_id_map: Dict[str, int] = {}
        
        # Attempt to load precomputed index on startup if available
        self.load_index()

    def _get_client(self):
        if self._client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
            from google import genai
            self._client = genai.Client(api_key=api_key)
        return self._client

    @property
    def collection(self):
        """ChromaDB-compatible collection interface for backwards compatibility."""
        return self

    def is_indexed(self) -> bool:
        return len(self.records) > 0 and self.embeddings_matrix is not None

    def count(self) -> int:
        return len(self.records)

    def load_index(self) -> bool:
        target_path = self.index_path
        if not os.path.exists(target_path) and os.path.exists(DEFAULT_INDEX_PATH):
            target_path = DEFAULT_INDEX_PATH

        if not os.path.exists(target_path):
            logger.info(f"Index file not found at {target_path}.")
            return False

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            records = data.get("records", [])
            if not records:
                return False

            self.records = records
            self.case_id_map = {r["case_id"]: i for i, r in enumerate(records)}

            embeddings = [r["embedding"] for r in records]
            matrix = np.array(embeddings, dtype=np.float32)

            # L2-normalize embeddings for fast cosine similarity via dot product
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self.embeddings_matrix = matrix / norms
            return True
        except Exception as e:
            logger.error(f"Failed to load vector store index from {target_path}: {e}")
            return False

    def index_records(
        self,
        records: List[Dict[str, Any]],
        force_rebuild: bool = False
    ) -> int:
        """
        Indexes records using Gemini Embeddings API and saves to index_path.
        """
        if not force_rebuild and self.is_indexed():
            return self.count()

        if not records:
            return self.count()

        client = self._get_client()
        from google.genai import types

        documents = []
        metadatas = []
        case_ids = []

        for record in records:
            doc_text, meta = build_document_and_metadata(record)
            documents.append(doc_text)
            metadatas.append(meta)
            case_ids.append(meta["case_id"])

        batch_size = 25
        all_embeddings = []

        import time
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            for attempt in range(5):
                try:
                    res = client.models.embed_content(
                        model=self.model_name,
                        contents=batch_docs,
                        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
                    )
                    for emb in res.embeddings:
                        all_embeddings.append(emb.values)
                    time.sleep(1.0)
                    break
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        wait_time = (attempt + 1) * 15
                        logger.warning(f"Rate limited (429) during indexing. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise e

        index_records = []
        for cid, doc, meta, emb in zip(case_ids, documents, metadatas, all_embeddings):
            index_records.append({
                "case_id": cid,
                "document": doc,
                "metadata": meta,
                "embedding": emb
            })

        index_data = {
            "model_name": self.model_name,
            "count": len(index_records),
            "records": index_records
        }

        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2)

        self.load_index()
        return self.count()

    def get(self, limit: Optional[int] = None, include: Optional[List[str]] = None) -> Dict[str, Any]:
        """ChromaDB-compatible get method for testing."""
        recs = self.records[:limit] if limit is not None else self.records
        res = {
            "ids": [r["case_id"] for r in recs],
            "metadatas": [r["metadata"] for r in recs]
        }
        return res

    def query(
        self,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        if not query_texts or not query_texts[0].strip():
            return {"ids": [[]], "metadatas": [[]], "distances": [[]]}

        if not self.is_indexed():
            raise RuntimeError("Vector store is not indexed and precomputed embeddings are missing.")

        query_text = query_texts[0].strip()

        # Generate query embedding using RETRIEVAL_QUERY
        client = self._get_client()
        from google.genai import types

        res = client.models.embed_content(
            model=self.model_name,
            contents=query_text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
        )
        query_vec = np.array(res.embeddings[0].values, dtype=np.float32)
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0:
            query_vec = query_vec / q_norm

        # Filter record indices by `where` clause (e.g., equipment_type)
        candidate_indices = []
        if where:
            for idx, r in enumerate(self.records):
                meta = r["metadata"]
                match = True
                for k, v in where.items():
                    if meta.get(k) != v:
                        match = False
                        break
                if match:
                    candidate_indices.append(idx)
        else:
            candidate_indices = list(range(len(self.records)))

        if not candidate_indices:
            return {"ids": [[]], "metadatas": [[]], "distances": [[]]}

        cand_matrix = self.embeddings_matrix[candidate_indices]  # shape (M, D)
        similarities = np.dot(cand_matrix, query_vec)            # shape (M,)
        distances = 1.0 - similarities                          # Cosine distance

        # Sort candidate indices by distance ascending
        sorted_order = np.argsort(distances)
        top_k_order = sorted_order[:n_results]

        top_ids = []
        top_metadatas = []
        top_distances = []

        for local_idx in top_k_order:
            global_idx = candidate_indices[local_idx]
            rec = self.records[global_idx]
            dist = float(distances[local_idx])
            top_ids.append(rec["case_id"])
            top_metadatas.append(rec["metadata"])
            top_distances.append(dist)

        return {
            "ids": [top_ids],
            "metadatas": [top_metadatas],
            "distances": [top_distances]
        }


def initialize_vector_store(
    csv_path: Optional[str] = None,
    persist_directory: Optional[str] = None,
    index_path: Optional[str] = None,
    force_rebuild: bool = False
) -> VectorStoreManager:
    """
    Helper function to load records and initialize the vector store.
    """
    csv_path = os.path.abspath(csv_path or DEFAULT_CSV_PATH)
    manager = VectorStoreManager(persist_directory=persist_directory, index_path=index_path)

    if force_rebuild or not manager.is_indexed():
        records = load_and_validate_dataset(csv_path)
        manager.index_records(records, force_rebuild=force_rebuild)

    return manager
