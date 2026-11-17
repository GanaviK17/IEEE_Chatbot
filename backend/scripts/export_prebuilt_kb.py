#!/usr/bin/env python3
"""Copy the local ChromaDB into one compressed file a fresh server can load in seconds.
Run after the knowledge base changes:  cd backend && python scripts/export_prebuilt_kb.py"""
import gzip, json, os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import chromadb
from chromadb.config import Settings
from app.config import CHROMA_PERSIST_DIR, COLLECTION_NAME, DATA_DIR

OUT = os.path.join(DATA_DIR, "prebuilt_kb.json.gz")
CATALOG = os.path.join(DATA_DIR, "documents_catalog.json")

def main() -> int:
    client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR), settings=Settings(anonymized_telemetry=False))
    col = client.get_collection(COLLECTION_NAME)
    res = col.get(include=["documents", "metadatas", "embeddings"])
    n = len(res["ids"])
    if n == 0:
        print("Local knowledge base is empty. Start the backend once so it fills, then rerun.")
        return 1
    catalog = {}
    if os.path.exists(CATALOG):
        with open(CATALOG, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    data = {
        "ids": list(res["ids"]),
        "documents": list(res["documents"]),
        "metadatas": [dict(m) for m in res["metadatas"]],
        "embeddings": [[round(float(x), 6) for x in e] for e in res["embeddings"]],
        "catalog": catalog,
    }
    with gzip.open(OUT, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"Exported {n} chunks to {OUT} ({os.path.getsize(OUT) / 1e6:.1f} MB)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
