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
from sentence_transformers import SentenceTransformer

# File to store document metadata registry
CATALOG_PATH = os.path.join(DATA_DIR, "documents_catalog.json")

class VectorStoreManager:
    _instance = None

    def __init__(self):
        print(f"Initializing SentenceTransformer model: {EMBEDDING_MODEL_NAME}...")
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        
        print(f"Connecting to persistent ChromaDB at: {CHROMA_PERSIST_DIR}...")
        self.chroma_client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        
        # Get or create collection with cosine distance metric
        self.collection = self.chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        self._load_catalog()

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

    def compute_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for a single query."""
        embedding = self.embedding_model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def compute_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate normalized embedding vectors for multiple chunks."""
        embeddings = self.embedding_model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()

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
