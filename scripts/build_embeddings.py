import os
import sys
import json
import logging
from typing import List, Dict, Any

# Ensure project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types
from app.data.loader import load_and_validate_dataset
from app.retrieval.document_builder import build_document_and_metadata

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CSV_PATH = os.path.join(project_root, "data", "maintenance_records.csv")
DEFAULT_INDEX_PATH = os.path.join(project_root, "data", "gemini_embeddings.json")
MODEL_NAME = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

def build_gemini_index(
    csv_path: str = DEFAULT_CSV_PATH,
    output_path: str = DEFAULT_INDEX_PATH,
    model_name: str = MODEL_NAME
) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment variables.")

    logger.info(f"Loading records from {csv_path}...")
    records = load_and_validate_dataset(csv_path)
    logger.info(f"Loaded {len(records)} records.")

    client = genai.Client(api_key=api_key)

    documents = []
    metadatas = []
    case_ids = []

    for rec in records:
        doc_text, meta = build_document_and_metadata(rec)
        documents.append(doc_text)
        metadatas.append(meta)
        case_ids.append(meta["case_id"])

    logger.info(f"Generating embeddings using model '{model_name}' for {len(documents)} documents...")
    batch_size = 25
    all_embeddings = []

    import time
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i : i + batch_size]
        logger.info(f"Embedding batch {i // batch_size + 1}/{(len(documents) + batch_size - 1) // batch_size} ({len(batch_docs)} items)...")
        
        for attempt in range(5):
            try:
                res = client.models.embed_content(
                    model=model_name,
                    contents=batch_docs,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
                )
                for emb in res.embeddings:
                    all_embeddings.append(emb.values)
                time.sleep(1.5)  # Pause to respect rate limits
                break
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait_time = (attempt + 1) * 15
                    logger.warning(f"Rate limited (429). Retrying batch in {wait_time}s... Error: {e}")
                    time.sleep(wait_time)
                else:
                    raise e

    logger.info(f"Successfully generated {len(all_embeddings)} embeddings (dimension: {len(all_embeddings[0])}).")

    index_data = {
        "model_name": model_name,
        "count": len(all_embeddings),
        "records": []
    }

    for cid, doc, meta, emb in zip(case_ids, documents, metadatas, all_embeddings):
        index_data["records"].append({
            "case_id": cid,
            "document": doc,
            "metadata": meta,
            "embedding": emb
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)

    logger.info(f"Saved index file to {output_path} ({os.path.getsize(output_path)} bytes).")
    return output_path

if __name__ == "__main__":
    build_gemini_index()
