import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from app.config import (
    CHROMA_PERSIST_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    DATA_DIR
)
import gzip
import math
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

# File to store document metadata registry
CATALOG_PATH = os.path.join(DATA_DIR, "documents_catalog.json")

class VectorStoreManager:
    _instance = None

    def __init__(self):
        self._embedder = None  # loaded lazily on first use
        self._query_cache: Dict[str, List[float]] = {}
        
        print(f"Connecting to persistent ChromaDB at: {CHROMA_PERSIST_DIR}...", flush=True)
        self.chroma_client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        print("PersistentClient created, getting collection...", flush=True)
        
        # Get or create collection with cosine distance metric
        self.collection = self.chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        print("Collection retrieved, loading catalog...", flush=True)
        self._load_catalog()
        print("VectorStoreManager initialized completely!", flush=True)

    def clear_and_recreate_collection(self):
        """Reset and recreate the ChromaDB collection."""
        try:
            self.chroma_client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        self.collection = self.chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        self.catalog = {}
        self._save_catalog()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_catalog(self):
        if os.path.exists(CATALOG_PATH):
            try:
                with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                    self.catalog = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load catalog from {CATALOG_PATH}: {e}")
                self.catalog = {}
        else:
            self.catalog = {}

    def _save_catalog(self):
        try:
            with open(CATALOG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.catalog, f, indent=2)
        except Exception as e:
            print(f"Error saving catalog: {e}")

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """all-MiniLM-L6-v2 via ONNX, L2-normalised, in small batches to save memory."""
        if self._embedder is None:
            print(f"Loading embedding model {EMBEDDING_MODEL_NAME} (ONNX)...", flush=True)
            self._embedder = ONNXMiniLM_L6_V2()
        out: List[List[float]] = []
        for i in range(0, len(texts), 16):
            for vec in self._embedder(texts[i:i + 16]):
                v = [float(x) for x in vec]
                norm = math.sqrt(sum(x * x for x in v)) or 1.0
                out.append([x / norm for x in v])
        return out

    def compute_embedding(self, text: str) -> List[float]:
        if text in self._query_cache:
            return self._query_cache[text]
        emb = self._embed([text])[0]
        if len(self._query_cache) < 1000:
            self._query_cache[text] = emb
        return emb

    def compute_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def load_prebuilt_kb(self, path: Optional[str] = None) -> int:
        """Restore the knowledge base from backend/data/prebuilt_kb.json.gz (no model needed)."""
        path = path or os.path.join(DATA_DIR, "prebuilt_kb.json.gz")
        if not os.path.exists(path):
            return 0
        with gzip.open(path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        ids, docs, metas, embs = data["ids"], data["documents"], data["metadatas"], data["embeddings"]
        for i in range(0, len(ids), 500):
            self.collection.upsert(ids=ids[i:i + 500], documents=docs[i:i + 500],
                                   metadatas=metas[i:i + 500], embeddings=embs[i:i + 500])
        self.catalog = data.get("catalog", {})
        self._save_catalog()
        return len(ids)

    def add_document_chunks(
        self,
        doc_id: str,
        filename: str,
        chunks: List[Dict[str, Any]],
        total_pages: int,
        file_size_bytes: int,
        source_url: str = ""
    ) -> int:
        """
        Embed and store document chunks and their metadata in ChromaDB.
        Updates persistent document catalog.
        """
        if not chunks:
            return 0

        # Extract texts, ids, and metadata dicts
        texts = [c["text"] for c in chunks]
        chunk_ids = [c["chunk_id"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # Compute embeddings with sentence-transformers all-MiniLM-L6-v2
        embeddings = self.compute_embeddings_batch(texts)

        # Store into ChromaDB
        self.collection.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

        # Record in document catalog
        self.catalog[doc_id] = {
            "id": doc_id,
            "filename": filename,
            "pages_count": total_pages,
            "chunks_count": len(chunks),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "file_size_bytes": file_size_bytes,
            "source_url": source_url or "Uploaded Document"
        }
        self._save_catalog()

        return len(chunks)

    def search_similar_chunks(
        self,
        query: str,
        top_k: int = 4,
        similarity_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Convert question to embedding and query ChromaDB collection.
        Returns relevant chunks matching the similarity threshold.
        """
        if self.collection.count() == 0:
            return []

        query_embedding = self.compute_embedding(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"]
        )

        retrieved_items = []
        if not results or not results.get("documents") or not results["documents"][0]:
            return []

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        for text, meta, dist in zip(docs, metas, distances):
            # For cosine space in ChromaDB, cosine_similarity = 1.0 - distance
            similarity = max(0.0, min(1.0, 1.0 - dist))
            
            if similarity >= similarity_threshold:
                retrieved_items.append({
                    "document_name": meta.get("document_name", "Unknown Document"),
                    "page_number": int(meta.get("page_number", 1)),
                    "chunk_id": meta.get("chunk_id", ""),
                    "excerpt": text,
                    "similarity_score": round(similarity, 4),
                    "source_url": meta.get("source_url", ""),
                    "is_restricted": bool(meta.get("is_restricted", False))
                })

        return retrieved_items

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete all chunks belonging to a document from ChromaDB and remove from catalog.
        """
        try:
            # Query chunks with document_id
            self.collection.delete(where={"document_id": doc_id})
            if doc_id in self.catalog:
                del self.catalog[doc_id]
                self._save_catalog()
            return True
        except Exception as e:
            print(f"Error deleting document {doc_id} from ChromaDB: {e}")
            return False

    def list_documents(self) -> List[Dict[str, Any]]:
        """Return list of all registered documents."""
        return list(self.catalog.values())

    def get_stats(self) -> Dict[str, Any]:
        """Return counts of documents and chunks."""
        total_chunks = self.collection.count()
        return {
            "total_documents": len(self.catalog),
            "total_chunks": total_chunks
        }
