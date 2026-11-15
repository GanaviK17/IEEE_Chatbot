import logging
from typing import List, Dict, Any, Tuple
from openai import OpenAI
from app.config import (
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    NVIDIA_MODEL,
    SIMILARITY_THRESHOLD,
    DEFAULT_TOP_K
)
from app.vector_store import VectorStoreManager
from app.models import SourceItem, ChatResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the official IEEE AI Assistant, an accurate, helpful, and professional assistant representing the Institute of Electrical and Electronics Engineers (IEEE).

Your primary responsibility is to answer the user's inquiry strictly and accurately based on the provided IEEE Knowledge Base Context.

MANDATORY RULES:
1. Ground your answer ONLY in the facts directly provided in the context below.
2. Do NOT hallucinate, fabricate, or assume policies, dates, statistics, requirements, or membership details not found in the context.
3. If the provided context does NOT contain sufficient information to answer the question, or if no context is provided, you MUST explicitly state:
   "Based on the available IEEE knowledge base, this information could not be found in the uploaded documents."
   Do NOT attempt to guess or answer from general external knowledge.
4. Keep your answer concise, well-structured, professional, and clear.
5. Explicitly mention the document name and page number for facts you reference (e.g., "[Source: Document.pdf, Page 1]").
"""

class RAGService:
    def __init__(self):
        self.vector_store = VectorStoreManager.get_instance()

    def _build_context_string(self, sources: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into structured context for Nemotron."""
        if not sources:
            return "No relevant context found in the uploaded knowledge base."

        context_blocks = []
        for idx, item in enumerate(sources, 1):
            block = (
                f"--- [CHUNK {idx}] ---\n"
                f"Document: {item['document_name']}\n"
                f"Page: {item['page_number']}\n"
                f"Content:\n{item['excerpt']}\n"
            )
            context_blocks.append(block)
        return "\n".join(context_blocks)

    def generate_answer(
        self,
        question: str,
        top_k: int = DEFAULT_TOP_K
    ) -> ChatResponse:
        """
        Execute full RAG pipeline:
        1. Embed question and search ChromaDB vector store.
        2. Apply similarity threshold.
        3. If no docs in store, return empty KB notice.
        4. If no relevant chunks meet threshold, return ungrounded notice.
        5. Invoke NVIDIA Nemotron with context and user question.
        6. Return grounded answer with verified source attributions.
        """
        # Check if vector store has any documents
        stats = self.vector_store.get_stats()
        if stats["total_chunks"] == 0:
            return ChatResponse(
                answer=(
                    "The IEEE knowledge base is currently empty. No documents have been uploaded yet. "
                    "Please upload IEEE-related PDF documents (such as IEEE Constitution, Student Branch guides, "
                    "Society overviews, or Conference manuals) using the document management panel to begin."
                ),
                sources=[],
                retrieved_chunks_count=0,
                model_used=NVIDIA_MODEL,
                confidence_note="Knowledge base is empty. No documents stored in ChromaDB."
            )

        # Retrieve relevant chunks from ChromaDB
        retrieved_raw = self.vector_store.search_similar_chunks(
            query=question,
            top_k=top_k,
            similarity_threshold=SIMILARITY_THRESHOLD
        )

        sources_list: List[SourceItem] = [
            SourceItem(
                document_name=item["document_name"],
                page_number=item["page_number"],
                chunk_id=item["chunk_id"],
                excerpt=item["excerpt"],
                similarity_score=item["similarity_score"],
                source_url=item.get("source_url")
            )
            for item in retrieved_raw
        ]

        # If similarity threshold filtered out everything or query is completely unrelated
        if not sources_list:
            return ChatResponse(
                answer=(
                    "Based on the available IEEE knowledge base, this information could not be found in the uploaded documents. "
                    "No document chunks met the relevance threshold for your query. "
                    "Please ensure relevant IEEE documents covering this topic have been uploaded, or refine your question."
                ),
                sources=[],
                retrieved_chunks_count=0,
                model_used=NVIDIA_MODEL,
                confidence_note="No relevant chunks above similarity threshold found in ChromaDB."
            )

        # Check API key presence
        api_key = NVIDIA_API_KEY
        if not api_key or api_key == "YOUR_NVIDIA_API_KEY_HERE" or api_key.startswith("your_"):
            # Provide clear configuration instruction while displaying retrieved chunks
            mock_explanation = (
                f"**Retrieved {len(sources_list)} relevant IEEE source chunks from ChromaDB.**\n\n"
                f"*(Note: NVIDIA API key is not currently configured in the environment. "
                f"To enable generative responses from **NVIDIA Nemotron** (`{NVIDIA_MODEL}`), "
                f"please add your valid `NVIDIA_API_KEY` to the `.env` file.)*\n\n"
                f"**Direct information from the knowledge base:**\n\n"
            )
            for s in sources_list:
                mock_explanation += f"• **[{s.document_name} – Page {s.page_number}]**:\n> \"{s.excerpt[:220]}...\"\n\n"

            return ChatResponse(
                answer=mock_explanation,
                sources=sources_list,
                retrieved_chunks_count=len(sources_list),
                model_used="ChromaDB-RAG (NVIDIA API Key Required)",
                confidence_note="Sources retrieved from ChromaDB. NVIDIA Nemotron requires NVIDIA_API_KEY."
            )

        # Format prompt with context and invoke NVIDIA Nemotron
        context_str = self._build_context_string(retrieved_raw)
        user_prompt = (
            f"IEEE Knowledge Base Context:\n{context_str}\n\n"
            f"User Question: {question}\n\n"
            f"Answer the question using only the IEEE context provided above. "
            f"Include citations with document name and page number."
        )

        try:
            client = OpenAI(
                base_url=NVIDIA_BASE_URL,
                api_key=api_key
            )

            response = client.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                top_p=0.7,
                max_tokens=1024
            )

            generated_answer = response.choices[0].message.content.strip()

            return ChatResponse(
                answer=generated_answer,
                sources=sources_list,
                retrieved_chunks_count=len(sources_list),
                model_used=NVIDIA_MODEL,
                confidence_note="Answer generated by NVIDIA Nemotron grounded in retrieved IEEE documents."
            )

        except Exception as e:
            logger.error(f"NVIDIA Nemotron API invocation error: {str(e)}")
            # Graceful error response with source context preserved
            error_msg = str(e)
            return ChatResponse(
                answer=(
                    f"Unable to complete Nemotron generation due to an API error: `{error_msg}`.\n\n"
                    f"However, the RAG retrieval pipeline successfully found **{len(sources_list)} relevant source chunks** "
                    f"in ChromaDB below."
                ),
                sources=sources_list,
                retrieved_chunks_count=len(sources_list),
                model_used=NVIDIA_MODEL,
                confidence_note=f"ChromaDB retrieval succeeded, LLM call encountered: {error_msg}"
            )
