import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.preloaded_data.corpus import AUTHENTIC_IEEE_DOCUMENTS
from app.vector_store import VectorStoreManager
from app.document_processor import clean_text
from app.config import CHUNK_SIZE, CHUNK_OVERLAP

def chunk_corpus_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert preloaded authentic IEEE document sections into overlapping chunks with metadata."""
    doc_id = doc["id"]
    doc_title = doc["title"]
    source_url = doc["source_url"]

    all_chunks = []
    chunk_counter = 0

    for section in doc["sections"]:
        page_num = section["page"]
        text = clean_text(section["text"])
        length = len(text)
        start = 0

        while start < length:
            end = start + CHUNK_SIZE

            if end >= length:
                chunk_str = text[start:].strip()
                if len(chunk_str) >= 20:
                    chunk_id = f"{doc_id}_p{page_num}_c{chunk_counter}"
                    all_chunks.append({
                        "chunk_id": chunk_id,
                        "text": chunk_str,
                        "metadata": {
                            "chunk_id": chunk_id,
                            "document_id": doc_id,
                            "document_name": doc_title,
                            "page_number": int(page_num),
                            "chunk_index": int(chunk_counter),
                            "source_url": source_url
                        }
                    })
                    chunk_counter += 1
                break

            # Find boundary
            window = text[start:end]
            split_point = -1

            last_para = window.rfind('\n')
            if last_para > CHUNK_SIZE * 0.4:
                split_point = start + last_para + 1
            else:
                for punct in ['. ', '.\n', '! ', '?\n', '? ']:
                    last_punct = window.rfind(punct)
                    if last_punct > CHUNK_SIZE * 0.4:
                        split_point = start + last_punct + len(punct)
                        break

            if split_point == -1:
                last_space = window.rfind(' ')
                if last_space > CHUNK_SIZE * 0.3:
                    split_point = start + last_space + 1
                else:
                    split_point = end

            chunk_str = text[start:split_point].strip()
            if len(chunk_str) >= 20:
                chunk_id = f"{doc_id}_p{page_num}_c{chunk_counter}"
                all_chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_str,
                    "metadata": {
                        "chunk_id": chunk_id,
                        "document_id": doc_id,
                        "document_name": doc_title,
                        "page_number": int(page_num),
                        "chunk_index": int(chunk_counter),
                        "source_url": source_url
                    }
                })
                chunk_counter += 1

            start = max(start + 1, split_point - CHUNK_OVERLAP)

    return all_chunks

def preload_authentic_knowledge_base(force_reload: bool = False) -> Dict[str, Any]:
    """
    Ensure the authentic IEEE knowledge base is ingested in ChromaDB.
    Runs idempotently on backend startup.
    """
    vector_store = VectorStoreManager.get_instance()
    existing_docs = {d["id"] for d in vector_store.list_documents()}

    loaded_count = 0
    total_new_chunks = 0

    for doc in AUTHENTIC_IEEE_DOCUMENTS:
        doc_id = doc["id"]
        if not force_reload and doc_id in existing_docs:
            continue

        chunks = chunk_corpus_document(doc)
        if not chunks:
            continue

        # If force reloading, remove old vectors first
        if doc_id in existing_docs:
            vector_store.delete_document(doc_id)

        # Ingest chunks into ChromaDB
        total_pages = max(s["page"] for s in doc["sections"])
        indexed_chunks = vector_store.add_document_chunks(
            doc_id=doc_id,
            filename=doc["title"],
            chunks=chunks,
            total_pages=total_pages,
            file_size_bytes=sum(len(s["text"].encode('utf-8')) for s in doc["sections"]),
            source_url=doc["source_url"]
        )

        loaded_count += 1
        total_new_chunks += indexed_chunks
        print(f"Ingested '{doc['title']}': {indexed_chunks} chunks stored into ChromaDB.")

    stats = vector_store.get_stats()
    return {
        "newly_loaded_documents": loaded_count,
        "newly_loaded_chunks": total_new_chunks,
        "total_documents": stats["total_documents"],
        "total_chunks": stats["total_chunks"]
    }

if __name__ == "__main__":
    result = preload_authentic_knowledge_base(force_reload=True)
    print(f"\nPreload complete: {result}")
