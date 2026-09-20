from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from app.retrieval.vector_store import VectorStoreManager

ALLOWED_EQUIPMENT_TYPES = {"Air Conditioning", "Generator", "Elevator"}
DEFAULT_MAX_DISTANCE = 0.75  # Cosine distance threshold: <= 0.75 is relevant

@dataclass
class RetrievalResult:
    case_id: str
    distance: float
    similarity_score: float
    complaint: str
    symptoms: str
    root_cause: str
    action_taken: str
    equipment_type: str
    equipment_model: str
    location: str
    repair_cost: float
    repair_time_hours: float
    urgency: str
    maintenance_type: str
    date_reported: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class RetrievalError(Exception):
    pass

class MaintenanceRetriever:
    def __init__(self, vector_store: VectorStoreManager):
        self.vector_store = vector_store

    def search(
        self,
        complaint: str,
        equipment_type: Optional[str] = None,
        top_k: int = 5,
        max_distance: Optional[float] = DEFAULT_MAX_DISTANCE
    ) -> List[RetrievalResult]:
        """
        Retrieves relevant historical maintenance cases for a given complaint.
        
        Args:
            complaint: The user/technician natural language complaint.
            equipment_type: Optional filter ('Air Conditioning', 'Generator', 'Elevator').
            top_k: Max number of cases to return.
            max_distance: Maximum allowed cosine distance (threshold for relevance).

        Returns:
            List of structured RetrievalResult domain objects.
        """
        # 1. Handle empty / whitespace / very short complaint safely
        if not complaint or len(complaint.strip()) < 3:
            return []

        # 2. Validate equipment_type if specified
        where_filter = None
        if equipment_type is not None:
            if equipment_type not in ALLOWED_EQUIPMENT_TYPES:
                raise ValueError(
                    f"Unsupported equipment_type '{equipment_type}'. "
                    f"Allowed types: {sorted(list(ALLOWED_EQUIPMENT_TYPES))}"
                )
            where_filter = {"equipment_type": equipment_type}

        # 3. Query ChromaDB
        try:
            results = self.vector_store.collection.query(
                query_texts=[complaint.strip()],
                n_results=top_k,
                where=where_filter,
                include=["metadatas", "distances"]
            )
        except Exception as e:
            raise RetrievalError(f"Vector store query failed: {e}") from e

        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        retrieved_cases: List[RetrievalResult] = []

        for case_id, meta, dist in zip(ids, metadatas, distances):
            # 4. Filter by relevance threshold if specified
            if max_distance is not None and dist > max_distance:
                continue

            sim_score = max(0.0, round(1.0 - dist, 4))

            result = RetrievalResult(
                case_id=str(meta.get("case_id", case_id)),
                distance=round(float(dist), 4),
                similarity_score=sim_score,
                complaint=str(meta.get("complaint", "")),
                symptoms=str(meta.get("symptoms", "")),
                root_cause=str(meta.get("root_cause", "")),
                action_taken=str(meta.get("action_taken", "")),
                equipment_type=str(meta.get("equipment_type", "")),
                equipment_model=str(meta.get("equipment_model", "")),
                location=str(meta.get("location", "")),
                repair_cost=float(meta.get("repair_cost", 0.0)),
                repair_time_hours=float(meta.get("repair_time_hours", 0.0)),
                urgency=str(meta.get("urgency", "")),
                maintenance_type=str(meta.get("maintenance_type", "")),
                date_reported=str(meta.get("date_reported", ""))
            )
            retrieved_cases.append(result)

        return retrieved_cases
