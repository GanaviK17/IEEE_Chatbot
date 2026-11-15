import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

BACKEND_URL = "http://127.0.0.1:8000"

def run_e2e_tests():
    print("=" * 70)
    print("IEEE AI ASSISTANT – COMPREHENSIVE END-TO-END VALIDATION SUITE")
    print("=" * 70)

    results = []

    # -------------------------------------------------------------
    # TEST 1: Backend Health Check & Preloaded KB Status
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing Backend Health Check & Preloaded Knowledge Base...")
    try:
        req = urllib.request.Request(f"{BACKEND_URL}/health")
        with urllib.request.urlopen(req) as res:
            assert res.status == 200
            data = json.loads(res.read().decode())
            print(f"  -> Health OK: {data}")
            assert data["status"] == "healthy"
            assert data["embedding_model"] == "all-MiniLM-L6-v2"
            assert data["documents_count"] >= 7, f"Expected at least 7 preloaded documents, found {data['documents_count']}"
            assert data["chunks_count"] >= 28, f"Expected at least 28 chunks, found {data['chunks_count']}"
            results.append(("Test 1: Backend Health & Preloaded KB", "PASSED"))
    except Exception as e:
        print(f"  -> Failed: {e}")
        results.append(("Test 1: Backend Health & Preloaded KB", f"FAILED: {e}"))

    # -------------------------------------------------------------
    # TEST 2: Preloaded Knowledge Semantic Retrieval & Grounding
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing Preloaded Knowledge Semantic Retrieval (IEEEXtreme & Student Benefits)...")
    try:
        chat_body = json.dumps({
            "message": "What is IEEEXtreme and what are the team requirements and prizes?",
            "top_k": 3
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{BACKEND_URL}/chat",
            data=chat_body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as res:
            assert res.status == 200
            chat_data = json.loads(res.read().decode())
            sources = chat_data.get("sources", [])
            print(f"  -> Retrieved chunks count: {chat_data['retrieved_chunks_count']}")
            assert len(sources) > 0, "No sources retrieved from preloaded knowledge base!"
            first_src = sources[0]
            print(f"  -> Top Source: Doc='{first_src['document_name']}', Page={first_src['page_number']}, Score={first_src['similarity_score']}")
            assert "Competitions" in first_src["document_name"] or "IEEEXtreme" in first_src["excerpt"]
            results.append(("Test 2: Preloaded Knowledge Semantic Retrieval", "PASSED"))
    except Exception as e:
        print(f"  -> Failed: {e}")
        results.append(("Test 2: Preloaded Knowledge Semantic Retrieval", f"FAILED: {e}"))

    # -------------------------------------------------------------
    # TEST 3: Optional PDF Upload Ingestion
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing Optional Custom PDF Ingestion...")
    sample_pdf = Path(__file__).resolve().parent / "backend" / "sample_docs" / "ieee_official_guide.pdf"
    doc_id = None
    try:
        assert sample_pdf.exists(), f"PDF missing at {sample_pdf}"
        
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        filename = "IEEE_Additional_Branch_Guide.pdf"
        
        with open(sample_pdf, "rb") as f:
            file_bytes = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            f"{BACKEND_URL}/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST"
        )
        with urllib.request.urlopen(req) as res:
            assert res.status == 200
            data = json.loads(res.read().decode())
            doc_id = data["document"]["id"]
            pages = data["document"]["pages_count"]
            chunks = data["document"]["chunks_count"]
            print(f"  -> Ingested custom PDF: ID={doc_id}, pages={pages}, chunks={chunks}")
            assert pages == 4
            assert chunks >= 4
            results.append(("Test 3: Optional Custom PDF Ingestion", "PASSED"))
    except Exception as e:
        print(f"  -> Failed: {e}")
        results.append(("Test 3: Optional Custom PDF Ingestion", f"FAILED: {e}"))

    # -------------------------------------------------------------
    # TEST 4: Out-of-Scope Query Refusal (Hallucination Prevention)
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing Out-of-Scope Refusal (No Hallucination)...")
    try:
        chat_body = json.dumps({
            "message": "What is the secret recipe for baking Martian chocolate cookies?",
            "top_k": 3
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{BACKEND_URL}/chat",
            data=chat_body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as res:
            assert res.status == 200
            chat_data = json.loads(res.read().decode())
            print(f"  -> Refusal Response: {chat_data['answer']}")
            assert "could not be found" in chat_data["answer"].lower()
            assert chat_data["retrieved_chunks_count"] == 0
            results.append(("Test 4: Hallucination Prevention Refusal", "PASSED"))
    except Exception as e:
        print(f"  -> Failed: {e}")
        results.append(("Test 4: Hallucination Prevention Refusal", f"FAILED: {e}"))

    # -------------------------------------------------------------
    # TEST 5: Document Deletion & Preloaded Base Preservation
    # -------------------------------------------------------------
    print("\n[TEST 5] Testing Custom Document Deletion & KB Preservation...")
    try:
        if doc_id:
            req = urllib.request.Request(
                f"{BACKEND_URL}/documents/{doc_id}",
                method="DELETE"
            )
            with urllib.request.urlopen(req) as res:
                assert res.status == 200
                data = json.loads(res.read().decode())
                print(f"  -> Deleted: {data['message']}")

            # Verify GET /documents retains the 7 preloaded documents
            req_docs = urllib.request.Request(f"{BACKEND_URL}/documents")
            with urllib.request.urlopen(req_docs) as res:
                docs_data = json.loads(res.read().decode())
                assert not any(d["id"] == doc_id for d in docs_data["documents"])
                assert docs_data["total_documents"] >= 7
                print(f"  -> Custom doc removed. Preloaded base preserved with {docs_data['total_documents']} documents.")
            results.append(("Test 5: Document Deletion & KB Preservation", "PASSED"))
    except Exception as e:
        print(f"  -> Failed: {e}")
        results.append(("Test 5: Document Deletion & KB Preservation", f"FAILED: {e}"))

    # -------------------------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("FINAL TEST EXECUTION REPORT:")
    print("=" * 70)
    all_passed = True
    for name, status in results:
        print(f"{name:.<55} {status}")
        if status != "PASSED":
            all_passed = False
    print("=" * 70)
    if all_passed:
        print("ALL END-TO-END VALIDATION TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_e2e_tests()
