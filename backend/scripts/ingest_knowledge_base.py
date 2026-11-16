#!/usr/bin/env python3
"""
Ingestion script for IEEE Knowledge Base.
Loads cleaned web pages from backend/data/web/ and backend/data/restricted_links.json,
chunks them (~500 chars, ~100 overlap), computes embeddings, and populates ChromaDB.
"""

import os
import sys
import json
import glob
import re
from typing import List, Dict, Any

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.config import CHUNK_SIZE, CHUNK_OVERLAP, DATA_DIR
from app.vector_store import VectorStoreManager

WEB_DIR = os.path.join(DATA_DIR, "web")
RESTRICTED_LINKS_FILE = os.path.join(DATA_DIR, "restricted_links.json")

def split_text_into_chunks(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """Split clean text into overlapping chunks respecting sentence/paragraph boundaries."""
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = start + chunk_size

        if end >= length:
            chunk = text[start:].strip()
            if len(chunk) >= 25:
                chunks.append(chunk)
            break

        # Look for natural split point within window
        window = text[start:end]
        split_idx = -1

        # Prefer newline / paragraph break
        last_newline = window.rfind("\n")
        if last_newline > chunk_size * 0.4:
            split_idx = start + last_newline + 1
        else:
            # Fallback to sentence ending punctuation
            for punct in [". ", ".\n", "! ", "? "]:
                last_punct = window.rfind(punct)
                if last_punct > chunk_size * 0.4:
                    split_idx = start + last_punct + len(punct)
                    break

        if split_idx == -1:
            # Fallback to space
            last_space = window.rfind(" ")
            if last_space > chunk_size * 0.4:
                split_idx = start + last_space + 1
            else:
                split_idx = end

        chunk = text[start:split_idx].strip()
        if len(chunk) >= 25:
            chunks.append(chunk)

        start = max(start + 1, split_idx - overlap)

    return chunks

def parse_markdown_page(filepath: str) -> Dict[str, Any]:
    """Extract title, source URL, and body from a crawled .md file."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    title = "IEEE Web Resource"
    source_url = "https://www.ieee.org"
    body_lines = []

    for idx, line in enumerate(lines):
        if idx == 0 and line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("Source URL: "):
            source_url = line[12:].strip()
        else:
            body_lines.append(line)

    body = "".join(body_lines).strip()
    return {
        "title": title,
        "source_url": source_url,
        "body": body,
        "filename": os.path.basename(filepath)
    }

def ingest_all():
    print("=======================================================")
    print("Starting IEEE Knowledge Base Ingestion Pipeline")
    print("=======================================================")

    vs = VectorStoreManager.get_instance()
    print("Clearing and recreating ChromaDB collection...")
    vs.clear_and_recreate_collection()

    all_chunks_to_add = []
    doc_catalog = {}

    # 1. Ingest crawled web pages from backend/data/web/
    md_files = glob.glob(os.path.join(WEB_DIR, "*.md"))
    print(f"Found {len(md_files)} web documents in {WEB_DIR}")

    total_web_chunks = 0
    for idx, filepath in enumerate(md_files, 1):
        parsed = parse_markdown_page(filepath)
        title = parsed["title"]
        source_url = parsed["source_url"]
        body = parsed["body"]
        filename = parsed["filename"]
        doc_id = f"web_{idx}_{filename.replace('.md', '')}"[:50]

        chunks_text = split_text_into_chunks(body, chunk_size=500, overlap=100)
        if not chunks_text:
            continue

        doc_chunks = []
        for c_idx, c_text in enumerate(chunks_text):
            chunk_id = f"{doc_id}_c{c_idx}"
            chunk_dict = {
                "chunk_id": chunk_id,
                "text": f"{title}\nSource: {source_url}\n\n{c_text}",
                "metadata": {
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "document_name": title,
                    "page_number": 1,
                    "chunk_index": c_idx,
                    "source_url": source_url,
                    "is_restricted": False
                }
            }
            doc_chunks.append(chunk_dict)

        all_chunks_to_add.extend(doc_chunks)
        total_web_chunks += len(doc_chunks)

        doc_catalog[doc_id] = {
            "id": doc_id,
            "filename": title,
            "pages_count": 1,
            "chunks_count": len(doc_chunks),
            "uploaded_at": "crawled",
            "file_size_bytes": os.path.getsize(filepath),
            "source_url": source_url
        }

    print(f"Prepared {total_web_chunks} chunks from {len(md_files)} web pages.")

    # 2. Ingest restricted links from backend/data/restricted_links.json
    total_restricted_chunks = 0
    if os.path.exists(RESTRICTED_LINKS_FILE):
        with open(RESTRICTED_LINKS_FILE, "r", encoding="utf-8") as f:
            restricted_links = json.load(f)

        print(f"Found {len(restricted_links)} restricted links in {RESTRICTED_LINKS_FILE}")
        for idx, item in enumerate(restricted_links, 1):
            title = item.get("title", "IEEE Official Portal")
            url = item.get("url", "https://www.ieee.org")
            description = item.get("short_description", "")
            keywords = ", ".join(item.get("topic_keywords", []))

            chunk_text = (
                f"Document: {title}\n"
                f"Official Link: {url}\n"
                f"Description: {description}\n"
                f"Keywords: {keywords}\n"
                f"Access Note: This official IEEE service or portal can be accessed directly at {url}."
            )

            doc_id = f"restricted_link_{idx}"
            chunk_id = f"{doc_id}_c0"
            chunk_dict = {
                "chunk_id": chunk_id,
                "text": chunk_text,
                "metadata": {
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "document_name": title,
                    "page_number": 1,
                    "chunk_index": 0,
                    "source_url": url,
                    "is_restricted": True
                }
            }
            all_chunks_to_add.append(chunk_dict)
            total_restricted_chunks += 1

            doc_catalog[doc_id] = {
                "id": doc_id,
                "filename": f"[Restricted Portal] {title}",
                "pages_count": 1,
                "chunks_count": 1,
                "uploaded_at": "restricted_catalog",
                "file_size_bytes": len(chunk_text),
                "source_url": url
            }

        print(f"Prepared {total_restricted_chunks} restricted link chunks.")

    # 3. Batch compute embeddings and upsert into ChromaDB
    total_chunks = len(all_chunks_to_add)
    print(f"Total chunks to embed and store: {total_chunks}")

    batch_size = 64
    for i in range(0, total_chunks, batch_size):
        batch = all_chunks_to_add[i:i + batch_size]
        texts = [c["text"] for c in batch]
        ids = [c["chunk_id"] for c in batch]
        metadatas = [c["metadata"] for c in batch]

        embeddings = vs.compute_embeddings_batch(texts)
        vs.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        print(f"Indexed batch {i + len(batch)}/{total_chunks}...")

    vs.catalog = doc_catalog
    vs._save_catalog()

    final_stats = vs.get_stats()
    print("=======================================================")
    print("INGESTION COMPLETE!")
    print(f"Total documents registered: {final_stats['total_documents']}")
    print(f"Total chunks in ChromaDB: {final_stats['total_chunks']}")
    print("=======================================================")

if __name__ == "__main__":
    ingest_all()
