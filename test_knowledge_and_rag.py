import urllib.request
import json

BACKEND_URL = "http://127.0.0.1:8000"

test_questions = [
    {
        "topic": "IEEE Organization & Founding",
        "question": "What two organizations merged in 1963 to form IEEE and who were their notable founders?",
        "expected_words": ["AIEE", "IRE", "Edison", "Bell", "1963"]
    },
    {
        "topic": "Student Membership Benefits",
        "question": "What exclusive benefits do IEEE Student Members receive?",
        "expected_words": ["Spectrum", "Potentials", "discount", "ResumeLab"]
    },
    {
        "topic": "Student Branch Requirements",
        "question": "What are the requirements to establish an IEEE Student Branch?",
        "expected_words": ["12", "Counselor", "petition", "faculty"]
    },
    {
        "topic": "Flagship Competitions (IEEEXtreme)",
        "question": "What is IEEEXtreme and what are the team rules and prizes?",
        "expected_words": ["24-hour", "programming", "October", "3"]
    },
    {
        "topic": "Technical Societies & Standards",
        "question": "What is IEEE 802.3 and IEEE 802.11?",
        "expected_words": ["Ethernet", "Wi-Fi"]
    },
    {
        "topic": "Scholarships & Fellowships",
        "question": "What scholarships and graduate fellowships does IEEE offer?",
        "expected_words": ["Fortescue", "Graduate"]
    },
    {
        "topic": "Out-of-Scope (Hallucination Prevention)",
        "question": "How do you build a nuclear submarine in Minecraft?",
        "expected_words": ["could not be found"]
    }
]

def test_queries():
    print("=" * 70)
    print("TESTING PRELOADED AUTHENTIC IEEE KNOWLEDGE RETRIEVAL & RAG RESPONSES")
    print("=" * 70)

    for item in test_questions:
        print(f"\n[QUERY] Topic: {item['topic']}")
        print(f"Question: \"{item['question']}\"")
        
        req = urllib.request.Request(
            f"{BACKEND_URL}/chat",
            data=json.dumps({"message": item["question"], "top_k": 3}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode())
            sources = data.get("sources", [])
            answer = data.get("answer", "")
            
            print(f"Retrieved Chunks: {data['retrieved_chunks_count']}")
            if sources:
                print(f"Top Source: {sources[0]['document_name']} (Page {sources[0]['page_number']}) - Score: {sources[0]['similarity_score']}")
                print(f"Source URL: {sources[0].get('source_url')}")
            print(f"Answer snippet: {answer[:180].replace(chr(10), ' ')}...")
            
            # Grounding assertions
            if item["topic"].startswith("Out-of-Scope"):
                assert "could not be found" in answer.lower(), "Expected hallucination refusal!"
                print("-> PASS: Safely declined to hallucinate.")
            else:
                assert data["retrieved_chunks_count"] > 0, "Expected retrieved chunks!"
                assert any(w.lower() in (sources[0]["excerpt"] + answer).lower() for w in item["expected_words"]), f"Expected grounded words from context: {item['expected_words']}"
                print("-> PASS: Correctly retrieved authentic knowledge with verifiable sources.")

    print("\n" + "=" * 70)
    print("ALL 7 KNOWLEDGE RETRIEVAL AND GROUNDING TESTS PASSED!")
    print("=" * 70)

if __name__ == "__main__":
    test_queries()
