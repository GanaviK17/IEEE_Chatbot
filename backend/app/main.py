import os
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB,
    DOCS_STORAGE_DIR,
    SAMPLE_DOCS_DIR,
    EMBEDDING_MODEL_NAME,
    NVIDIA_MODEL,
    NVIDIA_API_KEY
)
from app.models import (
    HealthResponse,
    ChatRequest,
    ChatResponse,
    DocumentListResponse,
    DocumentInfo,
    UploadResponse,
    AdminLoginRequest,
    AdminLoginResponse
)
from app.auth import (
    get_current_admin,
    verify_admin_password,
    create_admin_token,
    ADMIN_USERNAME
)
from app.document_processor import extract_and_chunk_pdf
from app.vector_store import VectorStoreManager
from app.rag_service import RAGService

app = FastAPI(
    title="IEEE AI Assistant RAG Backend",
    description="Production-grade Retrieval-Augmented Generation (RAG) backend for IEEE knowledge base using ChromaDB and NVIDIA Nemotron",
    version="1.0.0"
)

# CORS configuration to enable smooth communication with React/Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.preloader import preload_authentic_knowledge_base

# Initialize singletons
vector_store = VectorStoreManager.get_instance()
rag_service = RAGService()

@app.on_event("startup")
def startup_event():
    """Ensure authentic preloaded IEEE knowledge base is ingested on server start."""
    try:
        res = preload_authentic_knowledge_base(force_reload=False)
        print(f"Authentic IEEE Knowledge Base loaded: {res}")
    except Exception as e:
        print(f"Warning during preloading: {e}")

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Backend health check returning operational status, active models, and knowledge base stats."""
    stats = vector_store.get_stats()
    is_api_key_set = bool(
        NVIDIA_API_KEY and 
        NVIDIA_API_KEY != "YOUR_NVIDIA_API_KEY_HERE" and 
        not NVIDIA_API_KEY.startswith("your_")
    )
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        embedding_model=EMBEDDING_MODEL_NAME,
        nemotron_model=NVIDIA_MODEL,
        api_key_configured=is_api_key_set,
        documents_count=stats["total_documents"],
        chunks_count=stats["total_chunks"]
    )

# ==============================================================================
# Admin Authentication & Management Routes
# ==============================================================================

@app.post("/admin/login", response_model=AdminLoginResponse, tags=["Admin"])
def admin_login(creds: AdminLoginRequest):
    """
    Authenticate administrator credentials and return signed JWT token.
    """
    if creds.username != ADMIN_USERNAME or not verify_admin_password(creds.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator username or password."
        )
    return create_admin_token(creds.username)

@app.get("/admin/verify", tags=["Admin"])
def admin_verify(admin: str = Depends(get_current_admin)):
    """
    Verify administrator JWT session validity.
    """
    return {"valid": True, "username": admin}

@app.post("/admin/reindex", tags=["Admin"])
def admin_reindex(admin: str = Depends(get_current_admin)):
    """
    Admin-only endpoint to reload and re-index the authentic IEEE knowledge base into ChromaDB.
    """
    try:
        result = preload_authentic_knowledge_base(force_reload=True)
        return {
            "message": "Knowledge base re-indexing complete.",
            "details": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Re-indexing failed: {str(e)}"
        )

# ==============================================================================
# Protected Document Management Routes (Admin Only)
# ==============================================================================

@app.post("/upload", response_model=UploadResponse, tags=["Admin Documents"])
async def upload_document(
    file: UploadFile = File(...),
    admin: str = Depends(get_current_admin)
):
    """
    Accept, validate, extract, chunk, embed, and store an IEEE PDF document into ChromaDB.
    Protected: Requires administrator JWT authentication.
    """
    # 1. Validate file extension
    filename = file.filename or "unknown.pdf"
    _, ext = os.path.splitext(filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format: '{ext}'. Only PDF documents (.pdf) are supported."
        )

    # 2. Read content and validate size
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}"
        )

    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file_size_mb:.1f} MB) exceeds maximum allowed limit of {MAX_FILE_SIZE_MB} MB."
        )

    if len(content) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file appears to be empty or corrupted."
        )

    # 3. Process PDF: extract text per page and chunk with metadata
    try:
        doc_id, chunks, total_pages = extract_and_chunk_pdf(
            file_bytes=content,
            filename=filename
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error parsing PDF content: {str(e)}"
        )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable text could be extracted from this PDF. Please ensure the document is not an image-only scan."
        )

    # 4. Save file to disk for persistence
    saved_path = os.path.join(DOCS_STORAGE_DIR, f"{doc_id}_{filename}")
    try:
        with open(saved_path, "wb") as f:
            f.write(content)
    except Exception as e:
        print(f"Warning: could not save local PDF copy: {e}")

    # 5. Handle duplicate document re-upload: delete old chunks first
    if doc_id in vector_store.catalog:
        vector_store.delete_document(doc_id)

    # 6. Embed with all-MiniLM-L6-v2 and store in ChromaDB
    try:
        total_indexed = vector_store.add_document_chunks(
            doc_id=doc_id,
            filename=filename,
            chunks=chunks,
            total_pages=total_pages,
            file_size_bytes=len(content)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index document chunks into ChromaDB: {str(e)}"
        )

    # Get registered doc info
    catalog_entry = vector_store.catalog.get(doc_id, {
        "id": doc_id,
        "filename": filename,
        "pages_count": total_pages,
        "chunks_count": total_indexed,
        "uploaded_at": "now",
        "file_size_bytes": len(content),
        "source_url": "Uploaded Document"
    })

    return UploadResponse(
        message=f"Document '{filename}' successfully processed: {total_pages} page(s) extracted into {total_indexed} semantic chunk(s) stored in ChromaDB.",
        document=DocumentInfo(**catalog_entry)
    )

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
@app.post("/query", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest):
    """
    RAG Retrieval & Generation pipeline:
    1. Query ChromaDB using all-MiniLM-L6-v2 embedding of question.
    2. Filter relevant chunks based on similarity threshold.
    3. Pass retrieved context & strict grounding prompt to NVIDIA Nemotron.
    4. Return context-aware response along with exact source attributions.
    """
    query = request.get_query()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty."
        )

    try:
        response = rag_service.generate_answer(
            question=query,
            history=request.history,
            top_k=request.top_k
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating RAG response: {str(e)}"
        )

@app.get("/documents", response_model=DocumentListResponse, tags=["Admin Documents"])
def get_documents(admin: str = Depends(get_current_admin)):
    """
    List all uploaded documents and their ingestion statistics.
    Protected: Requires administrator JWT authentication.
    """
    docs_list = vector_store.list_documents()
    stats = vector_store.get_stats()
    
    formatted_docs = [
        DocumentInfo(
            id=d["id"],
            filename=d["filename"],
            pages_count=d["pages_count"],
            chunks_count=d["chunks_count"],
            uploaded_at=d["uploaded_at"],
            file_size_bytes=d["file_size_bytes"],
            source_url=d.get("source_url")
        )
        for d in docs_list
    ]

    return DocumentListResponse(
        documents=formatted_docs,
        total_documents=stats["total_documents"],
        total_chunks=stats["total_chunks"]
    )

@app.delete("/documents/{document_id}", tags=["Admin Documents"])
def delete_document(
    document_id: str,
    admin: str = Depends(get_current_admin)
):
    """
    Remove a document and its stored vectors completely from ChromaDB.
    Protected: Requires administrator JWT authentication.
    """
    existing = vector_store.catalog.get(document_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    filename = existing.get("filename", "unknown")
    success = vector_store.delete_document(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document from ChromaDB vector store."
        )

    # Delete local copy if present
    saved_path = os.path.join(DOCS_STORAGE_DIR, f"{document_id}_{filename}")
    if os.path.exists(saved_path):
        try:
            os.remove(saved_path)
        except Exception:
            pass

    return {
        "message": f"Document '{filename}' (ID: {document_id}) and all its associated vector embeddings were successfully removed from ChromaDB.",
        "deleted_id": document_id
    }

