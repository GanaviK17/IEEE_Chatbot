import os
import sys
from pathlib import Path
from starlette.testclient import TestClient

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.main import app
from app.config import SAMPLE_DOCS_DIR

client = TestClient(app)

def test_health_endpoint():
    print("--> Testing GET /health...")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["embedding_model"] == "all-MiniLM-L6-v2"
    assert "nemotron" in data["nemotron_model"].lower()
    print(f"Health check OK: {data}")

def test_document_lifecycle_and_chat():
    print("--> Testing Document Upload, Chat, and Deletion Endpoints...")
    sample_pdf = os.path.join(SAMPLE_DOCS_DIR, "ieee_official_guide.pdf")
    
    # 1. Upload sample PDF
    with open(sample_pdf, "rb") as f:
        response = client.post(
            "/upload",
            files={"file": ("IEEE_Test_Guide.pdf", f, "application/pdf")}
        )
    assert response.status_code == 200, f"Upload failed: {response.text}"
    upload_data = response.json()
    doc = upload_data["document"]
    doc_id = doc["id"]
    print(f"Uploaded successfully: ID={doc_id}, pages={doc['pages_count']}, chunks={doc['chunks_count']}")
    assert doc["pages_count"] == 4
    assert doc["chunks_count"] >= 4

    # 2. Verify document in GET /documents
    response = client.get("/documents")
    assert response.status_code == 200
    docs_list = response.json()["documents"]
    assert any(d["id"] == doc_id for d in docs_list)
    print(f"Total documents registered: {len(docs_list)}")

    # 3. Test POST /chat with grounded question
    chat_payload = {
        "message": "When was IEEE formed and what two organizations merged to create it?",
        "top_k": 3
    }
    response = client.post("/chat", json=chat_payload)
    assert response.status_code == 200
    chat_data = response.json()
    print("\nChat Response for IEEE history question:")
    print("Answer excerpt:", chat_data["answer"][:180], "...")
    print(f"Retrieved chunks: {chat_data['retrieved_chunks_count']}")
    assert chat_data["retrieved_chunks_count"] > 0
    assert len(chat_data["sources"]) > 0
    first_source = chat_data["sources"][0]
    print(f"Source 1: Doc='{first_source['document_name']}', Page={first_source['page_number']}, Score={first_source['similarity_score']}")
    assert first_source["page_number"] in [1, 2, 3, 4]

    # 4. Test POST /chat with unrelated query
    chat_payload_unrelated = {
        "message": "What is the capital of Mars?",
        "top_k": 3
    }
    response = client.post("/chat", json=chat_payload_unrelated)
    assert response.status_code == 200
    chat_data_unrelated = response.json()
    print("\nChat Response for unrelated question:")
    print("Answer:", chat_data_unrelated["answer"])
    assert "could not be found" in chat_data_unrelated["answer"].lower()
    assert chat_data_unrelated["retrieved_chunks_count"] == 0

    # 5. Test DELETE /documents/{document_id}
    response = client.delete(f"/documents/{doc_id}")
    assert response.status_code == 200
    print(f"\nDocument {doc_id} successfully deleted from ChromaDB.")

    # 6. Verify empty or removed from GET /documents
    response = client.get("/documents")
    assert response.status_code == 200
    docs_after = response.json()["documents"]
    assert not any(d["id"] == doc_id for d in docs_after)
    print("SUCCESS: Full API endpoint lifecycle verified.")

if __name__ == "__main__":
    test_health_endpoint()
    test_document_lifecycle_and_chat()
    print("\nALL API ENDPOINT TESTS PASSED SUCCESSFULLY!")
