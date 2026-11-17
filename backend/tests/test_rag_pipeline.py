import os
import sys
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import pytest
from app.document_processor import extract_and_chunk_pdf, clean_text
from app.vector_store import VectorStoreManager
from app.rag_service import RAGService
from app.config import SAMPLE_DOCS_DIR

@pytest.fixture
def sample_pdf_data():
    sample_pdf = os.path.join(SAMPLE_DOCS_DIR, "ieee_official_guide.pdf")
    assert os.path.exists(sample_pdf), f"Sample PDF missing at {sample_pdf}"

    with open(sample_pdf, "rb") as f:
        content = f.read()

    doc_id, chunks, total_pages = extract_and_chunk_pdf(
        file_bytes=content,
        filename="ieee_official_guide.pdf",
        source_url="https://www.ieee.org"
    )
    return doc_id, chunks, total_pages, len(content)

def test_pdf_extraction_and_chunking(sample_pdf_data):
    print("--> Testing PDF extraction and chunking...")
    doc_id, chunks, total_pages, file_size = sample_pdf_data
    print(f"Extracted {total_pages} pages, generated {len(chunks)} chunks, doc_id: {doc_id}")
    assert total_pages == 4, f"Expected 4 pages, got {total_pages}"
    assert len(chunks) >= 4, f"Expected at least 4 chunks, got {len(chunks)}"

    # Check chunk metadata
    first_chunk = chunks[0]
    assert "chunk_id" in first_chunk["metadata"]
    assert "page_number" in first_chunk["metadata"]
    assert first_chunk["metadata"]["page_number"] == 1
    assert first_chunk["metadata"]["document_name"] == "ieee_official_guide.pdf"
    print("SUCCESS: PDF extraction and chunking verified.")

def test_vector_store_indexing_and_search(sample_pdf_data):
    doc_id, chunks, total_pages, file_size = sample_pdf_data
    print("--> Testing ChromaDB vector indexing and retrieval...")
    vstore = VectorStoreManager.get_instance()
    
    # Clean previous if present
    vstore.delete_document(doc_id)

    indexed_count = vstore.add_document_chunks(
        doc_id=doc_id,
        filename="ieee_official_guide.pdf",
        chunks=chunks,
        total_pages=total_pages,
        file_size_bytes=file_size,
        source_url="https://www.ieee.org"
    )
    assert indexed_count == len(chunks), f"Expected {len(chunks)} indexed, got {indexed_count}"

    # Test targeted retrieval for a specific question present in document
    query = "What is IEEEXtreme and when is it held?"
    results = vstore.search_similar_chunks(query=query, top_k=3, similarity_threshold=0.2)
    
    print(f"Retrieved {len(results)} chunks for query: '{query}'")
    assert len(results) > 0, "No chunks retrieved for valid question!"
    
    top_result = results[0]
    print(f"Top result from: {top_result['document_name']} (Page {top_result['page_number']}) with score {top_result['similarity_score']}")
    print(f"Excerpt: {top_result['excerpt'][:140]}...")
    
    # IEEEXtreme is in page 3
    assert "IEEEXtreme" in top_result["excerpt"] or any("IEEEXtreme" in r["excerpt"] for r in results)
    print("SUCCESS: Semantic similarity search retrieved correct ground-truth chunk.")

def test_unrelated_query_handling():
    print("--> Testing unanswerable / unrelated query filtering...")
    rag = RAGService()
    unrelated_query = "What is the recipe for baking chocolate chip cookies?"
    response = rag.generate_answer(unrelated_query)
    print("Response for unrelated question:")
    print(response.answer)
    assert response.retrieved_chunks_count == 0 or "could not be found" in response.answer.lower()
    print("SUCCESS: Unanswerable query handled safely without hallucination.")

if __name__ == "__main__":
    doc_id, chunks, total_pages, file_size = test_pdf_extraction_and_chunking()
    test_vector_store_indexing_and_search(doc_id, chunks, total_pages, file_size)
    test_unrelated_query_handling()
    print("\nALL RAG PIPELINE TESTS PASSED!")
