import re
import hashlib
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader
import io
from app.config import CHUNK_SIZE, CHUNK_OVERLAP

def generate_doc_id(filename: str, content_bytes: bytes) -> str:
    """Generate a stable, unique ID for a document based on filename and hash."""
    hasher = hashlib.sha256()
    hasher.update(filename.encode('utf-8'))
    hasher.update(content_bytes[:4096])
    return hasher.hexdigest()[:16]

def clean_text(text: str) -> str:
    """Clean extracted PDF text while preserving sentence boundaries."""
    if not text:
        return ""
    # Normalize excessive carriage returns and tabs
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Replace weird unicode spaces
    text = re.sub(r'[\xa0\u200b\u200e\u200f]', ' ', text)
    # Remove multiple spaces on same line
    text = re.sub(r'[ \t]+', ' ', text)
    # Remove excessive blank lines (more than 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def chunk_page_text(
    text: str,
    doc_id: str,
    doc_name: str,
    page_num: int,
    source_url: str = "",
    start_chunk_idx: int = 0
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Split a page's text into overlapping, meaningful chunks.
    Preserves page number, document name, and unique chunk IDs.
    """
    cleaned = clean_text(text)
    if not cleaned or len(cleaned) < 20:
        return [], start_chunk_idx

    chunks = []
    current_idx = start_chunk_idx
    length = len(cleaned)
    start = 0

    while start < length:
        end = start + CHUNK_SIZE

        if end >= length:
            chunk_str = cleaned[start:].strip()
            if len(chunk_str) >= 20:
                chunk_id = f"{doc_id}_p{page_num}_c{current_idx}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_str,
                    "metadata": {
                        "chunk_id": chunk_id,
                        "document_id": doc_id,
                        "document_name": doc_name,
                        "page_number": int(page_num),
                        "chunk_index": int(current_idx),
                        "source_url": source_url or "Uploaded Document"
                    }
                })
                current_idx += 1
            break

        # Attempt to split cleanly on sentence or paragraph boundaries
        split_point = -1
        window = cleaned[start:end]

        # Check for paragraph break first
        last_para = window.rfind('\n\n')
        if last_para > CHUNK_SIZE * 0.4:
            split_point = start + last_para + 2
        else:
            # Check for sentence end punctuation (. ! ?)
            for punct in ['. ', '.\n', '! ', '?\n', '? ']:
                last_punct = window.rfind(punct)
                if last_punct > CHUNK_SIZE * 0.4:
                    split_point = start + last_punct + len(punct)
                    break

        # Fallback to last whitespace
        if split_point == -1:
            last_space = window.rfind(' ')
            if last_space > CHUNK_SIZE * 0.3:
                split_point = start + last_space + 1
            else:
                split_point = end

        chunk_str = cleaned[start:split_point].strip()
        if len(chunk_str) >= 20:
            chunk_id = f"{doc_id}_p{page_num}_c{current_idx}"
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_str,
                "metadata": {
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "document_name": doc_name,
                    "page_number": int(page_num),
                    "chunk_index": int(current_idx),
                    "source_url": source_url or "Uploaded Document"
                }
            })
            current_idx += 1

        # Advance start with overlap
        start = max(start + 1, split_point - CHUNK_OVERLAP)

    return chunks, current_idx

def extract_and_chunk_pdf(
    file_bytes: bytes,
    filename: str,
    source_url: str = ""
) -> Tuple[str, List[Dict[str, Any]], int]:
    """
    Extract text page-by-page from PDF bytes and create indexed chunks with metadata.
    Returns: (doc_id, chunks_list, total_pages)
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    total_pages = len(reader.pages)
    doc_id = generate_doc_id(filename, file_bytes)

    all_chunks = []
    chunk_counter = 0

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1  # 1-indexed
        page_text = page.extract_text() or ""
        page_chunks, chunk_counter = chunk_page_text(
            text=page_text,
            doc_id=doc_id,
            doc_name=filename,
            page_num=page_num,
            source_url=source_url,
            start_chunk_idx=chunk_counter
        )
        all_chunks.extend(page_chunks)

    return doc_id, all_chunks, total_pages
