# IEEE AI Assistant – RAG-Powered Chatbot

An intelligent, production-ready Retrieval-Augmented Generation (RAG) assistant for the **Institute of Electrical and Electronics Engineers (IEEE)**. 

The chatbot works **immediately out-of-the-box** with a preloaded knowledge base of authentic official IEEE information and supports full **voice interaction** (speech-to-text and text-to-speech), semantic retrieval powered by **ChromaDB** and **Sentence Transformers**, and answer generation via **NVIDIA Nemotron**.

---

## 1. Key Features

- **Preloaded Authentic Knowledge Base:** Works immediately without uploading documents. Covers 7 core IEEE domains with verified public information, official URLs, and page numbers:
  1. *IEEE Constitution, Mission & Global Structure* (1963 merger of AIEE and IRE, 10 Regions, headquarters)
  2. *IEEE Membership Grades, Qualifications & Student Benefits* (Student, Graduate, Senior, Fellow, Spectrum, @ieee.org)
  3. *IEEE Student Branch Operations, Counselor Guide & Programs* (Branch formation, counselor role, ExCom)
  4. *IEEE Flagship Competitions & Global Events* (IEEEXtreme 24-hr challenge, IEEE Day, SIGHT)
  5. *IEEE Technical Societies, Publications & IEEE Xplore* (39 societies, 6M+ peer-reviewed papers)
  6. *IEEE Standards Association (IEEE-SA) & IEEE Code of Ethics* (IEEE 802.3 Ethernet, IEEE 802.11 Wi-Fi, 6 ethical tenets)
  7. *IEEE Scholarships, Grants, Awards & Fellowships* (Fortescue scholarship, graduate fellowships, ISEF award)
- **Voice-Enabled Chatbot:**
  - **Speech-to-Text (STT):** Microphone button for voice input using the browser Web Speech API.
  - **Text-to-Speech (TTS):** The assistant reads out answers with a natural voice; includes audio stop controls.
  - **Speaker Toggle:** Global auto-speak toggle and individual message read-aloud buttons.
  - **Speech Formatting:** Automatically cleans markdown syntax, code snippets, and URLs before speaking.
  - **Permission Handling:** Friendly notices when microphone access is requested or denied.
- **Modern Conversational Interface:**
  - Welcome screen with IEEE branding and quick-start suggested topic chips.
  - User and AI message bubbles with model indicators.
  - Copy answer button with instant visual feedback.
  - Contextual follow-up question chips beneath responses.
  - Verifiable source citations with similarity match scores and direct external links to official IEEE sources.
  - Safe refusal to hallucinate for out-of-scope or unanswerable queries.
- **Optional Custom Document Ingestion:**
  - Users can optionally upload additional IEEE PDFs (bylaws, event CFPs) into ChromaDB.
  - Text extraction with page preservation, chunking with overlap, and deduplication.

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    REACT VITE FRONTEND                      │
│   • Chat Area & Suggested Prompts   • Voice STT / TTS       │
│   • Source Citations Drawer         • Optional PDF Upload   │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP REST API
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                          │
│   • GET /health          • POST /upload     • POST /chat    │
│   • GET /documents       • DELETE /documents/{id}           │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
┌──────────────────────────────┐ ┌────────────────────────────┐
│   EMBEDDING & VECTOR DB      │ │    NVIDIA NEMOTRON API     │
│ • all-MiniLM-L6-v2 (384-dim) │ │ • Hosted Inference API     │
│ • ChromaDB Persistent Index  │ │ • nvidia/llama-3.1-        │
│ • Preloaded IEEE Knowledge   │ │   nemotron-70b-instruct    │
│ • Optional Uploaded Chunks   │ │ • Grounded System Prompt   │
└──────────────────────────────┘ └────────────────────────────┘
```

---

## 3. Technology Stack

- **Frontend:** React 18, Vite, Modern CSS (IEEE Dark Navy `#002855`, Cerulean Blue `#00629B`), Lucide React, Web Speech API.
- **Backend:** Python 3.13, FastAPI, Uvicorn, REST API.
- **Embedding Model:** Sentence Transformers (`all-MiniLM-L6-v2`), 384-dimensional dense vectors with cosine similarity.
- **Vector Database:** ChromaDB (persistent local storage).
- **Document Processing:** `pypdf` with sentence-boundary text chunking (650 chars, 120 overlap).
- **LLM:** NVIDIA Nemotron (`nvidia/llama-3.1-nemotron-70b-instruct`) via hosted inference API (`https://integrate.api.nvidia.com/v1`).

---

## 4. Project Directory Structure

```
ieee-rag-assistant/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                 # Configuration settings and model names
│   │   ├── document_processor.py      # PDF text extraction and chunking
│   │   ├── main.py                   # FastAPI application and endpoints
│   │   ├── models.py                 # Pydantic schemas
│   │   ├── preloader.py              # Automatic startup knowledge base preloader
│   │   ├── rag_service.py            # RAG retrieval and NVIDIA Nemotron service
│   │   ├── vector_store.py           # ChromaDB client and embedding manager
│   │   └── preloaded_data/
│   │       ├── __init__.py
│   │       └── corpus.py             # 7 authentic IEEE knowledge documents
│   ├── tests/
│   │   ├── test_api_endpoints.py     # FastAPI test suite
│   │   └── test_rag_pipeline.py      # RAG pipeline test suite
│   ├── .env.example                  # Safe configuration template
│   ├── .env                          # Local credentials (git-ignored)
│   └── requirements.txt              # Python dependencies
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx                   # Main React component
│       ├── App.css                   # IEEE styling & responsive design
│       ├── index.css                 # Global CSS variables & resets
│       ├── main.jsx                  # React DOM entry
│       ├── hooks/
│       │   └── useVoice.js           # Speech-to-text and text-to-speech hook
│       └── components/
│           ├── ChatArea.jsx          # Chat stream, suggestions, input bar
│           ├── DocumentManager.jsx   # Knowledge base drawer & optional PDF upload
│           ├── Header.jsx            # IEEE logo, voice toggle, status badges
│           ├── MessageBubble.jsx     # Dialog bubble, speak audio, copy button
│           └── SourceCitation.jsx    # Verifiable source chips & excerpt drawer
├── .gitignore                        # Git ignore rules
├── README.md                         # Project documentation
├── run_backend.bat                   # Windows batch script to launch backend
├── run_frontend.bat                  # Windows batch script to launch frontend
├── test_e2e.py                       # Comprehensive end-to-end test runner
└── test_knowledge_and_rag.py         # 7-topic authentic retrieval validation
```

---

## 5. Configuration & Environment Variables

Copy `backend/.env.example` to `backend/.env`:

```ini
# NVIDIA Hosted Inference API Configuration
# Get your free developer API key from https://build.nvidia.com/
NVIDIA_API_KEY=YOUR_NVIDIA_API_KEY_HERE
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=nvidia/llama-3.1-nemotron-70b-instruct

# Server settings
PORT=8000
HOST=0.0.0.0
```

> **Note on API Key Handling:** If `NVIDIA_API_KEY` is not configured, the assistant operates in fallback mode—accurately retrieving all relevant knowledge base chunks and displaying their document names, page numbers, and official source URLs without crashing.

---

## 6. How to Run the Application

### 1. Start the Backend Server
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Backend runs on `http://127.0.0.1:8000` (Interactive API docs at `http://127.0.0.1:8000/docs`).*

### 2. Start the Frontend Dev Server
```bash
cd frontend
npm install
npm run dev
```
*Frontend runs on `http://127.0.0.1:5173`.*

Alternatively, on Windows, double-click `run_backend.bat` and `run_frontend.bat`.

---

## 7. Running the Automated Test Suites

### Complete End-to-End Test Suite:
```bash
python test_e2e.py
```
Validates backend health, preloaded knowledge retrieval, optional PDF upload, hallucination prevention refusal, and document deletion.

### 7-Domain Authentic Knowledge Retrieval Test:
```bash
python test_knowledge_and_rag.py
```
Validates precision retrieval across all 7 preloaded IEEE knowledge domains and tests hallucination rejection.

---

## 8. Git Commands to Push to Your GitHub Repository

When you are ready to push the project to your GitHub repository:

```bash
# 1. Navigate to the project root directory
cd "C:\Users\Ganavi K\.gemini\antigravity\scratch\ieee-rag-assistant"

# 2. Initialize the Git repository
git init

# 3. Add all files (respecting .gitignore which excludes node_modules, .env, and caches)
git add .

# 4. Create your initial commit
git commit -m "feat: complete IEEE AI Assistant RAG Chatbot with preloaded knowledge and voice interaction"

# 5. Set the main branch
git branch -M main

# 6. Add your remote GitHub repository URL (replace with your repository URL)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git

# 7. Push to GitHub
git push -u origin main
```
