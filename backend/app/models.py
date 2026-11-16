from typing import List, Optional
from pydantic import BaseModel, Field

class SourceItem(BaseModel):
    document_name: str = Field(..., description="Original name of the source document")
    page_number: int = Field(..., description="Page number of the source chunk")
    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    excerpt: str = Field(..., description="Extracted text chunk from document")
    similarity_score: float = Field(..., description="Relevance score (0 to 1)")
    source_url: Optional[str] = Field(None, description="Official source URL if available")

class MessageTurn(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Content of the message")

class ChatRequest(BaseModel):
    message: Optional[str] = Field(None, description="User question")
    question: Optional[str] = Field(None, description="Alternative field for user question")
    session_id: Optional[str] = Field(None, description="Optional conversation session identifier")
    top_k: int = Field(default=4, ge=1, le=10, description="Number of relevant chunks to retrieve")
    history: Optional[List[MessageTurn]] = Field(default_factory=list, description="Prior conversation turns for context")

    def get_query(self) -> str:
        return (self.message or self.question or "").strip()


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Conversational grounded answer")
    sources: List[SourceItem] = Field(default_factory=list, description="Retrieved source chunks")
    retrieved_chunks_count: int = Field(..., description="Number of relevant chunks retrieved")
    model_used: str = Field(default="IEEE Assistant", description="Identifier of the model")
    confidence_note: Optional[str] = Field(None, description="Grounding status note")

class DocumentInfo(BaseModel):
    id: str = Field(..., description="Unique document ID")
    filename: str = Field(..., description="PDF filename or official title")
    pages_count: int = Field(..., description="Total pages")
    chunks_count: int = Field(..., description="Total text chunks stored in ChromaDB")
    uploaded_at: str = Field(..., description="ISO 8601 upload timestamp")
    file_size_bytes: int = Field(..., description="File size in bytes")
    source_url: Optional[str] = Field(None, description="Optional original URL")

class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo] = Field(default_factory=list)
    total_documents: int
    total_chunks: int

class UploadResponse(BaseModel):
    message: str
    document: DocumentInfo

class HealthResponse(BaseModel):
    status: str
    version: str
    embedding_model: str
    nemotron_model: str
    api_key_configured: bool
    documents_count: int
    chunks_count: int
