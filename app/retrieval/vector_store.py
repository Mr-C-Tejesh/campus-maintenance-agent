import os
# Configure thread concurrency limits to keep memory footprint low (<512MB)
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

try:
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
except Exception:
    pass

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions
from app.data.loader import load_and_validate_dataset
from app.retrieval.document_builder import build_document_and_metadata

COLLECTION_NAME = "maintenance_cases"
DEFAULT_PERSIST_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "chroma_db"
)
DEFAULT_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "maintenance_records.csv"
)

class VectorStoreManager:
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        self.persist_directory = os.path.abspath(persist_directory or DEFAULT_PERSIST_DIR)
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name
        )
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )

    def is_indexed(self) -> bool:
        """Returns True if the collection already contains records."""
        return self.collection.count() > 0

    def index_records(
        self,
        records: List[Dict[str, Any]],
        force_rebuild: bool = False
    ) -> int:
        """
        Indexes maintenance records into ChromaDB.
        Uses case_id as document ID and upserts to prevent duplicate insertions.
        Returns the total count of indexed records in the collection.
        """
        if force_rebuild:
            try:
                self.client.delete_collection(COLLECTION_NAME)
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )

        if not records:
            return self.collection.count()

        ids = []
        documents = []
        metadatas = []

        for record in records:
            doc_text, meta = build_document_and_metadata(record)
            ids.append(meta["case_id"])
            documents.append(doc_text)
            metadatas.append(meta)

        # ChromaDB upsert ensures repeated initialization doesn't duplicate records
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

        return self.collection.count()

def initialize_vector_store(
    csv_path: Optional[str] = None,
    persist_directory: Optional[str] = None,
    force_rebuild: bool = False
) -> VectorStoreManager:
    """
    Helper function to load CSV records and initialize the vector store.
    """
    csv_path = os.path.abspath(csv_path or DEFAULT_CSV_PATH)
    manager = VectorStoreManager(persist_directory=persist_directory)
    
    if force_rebuild or not manager.is_indexed():
        records = load_and_validate_dataset(csv_path)
        manager.index_records(records, force_rebuild=force_rebuild)

    return manager
