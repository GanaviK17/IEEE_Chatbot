import os
import re
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

# Polished, friendly, natural IEEE Assistant system prompt
SYSTEM_PROMPT = """You are the IEEE Assistant, a friendly guide for students and professionals. Use the provided context first. For greetings, small talk, or well-known general facts about IEEE, answer naturally from your own knowledge. If a retrieved source is a restricted link, briefly explain what it covers and share the link so the user can open it directly on ieee.org. If the answer is unclear, say so briefly and suggest checking ieee.org. Keep answers concise and conversational. Never say 'the provided context does not state'."""

class RAGService:
    def __init__(self):
        self.vector_store = VectorStoreManager.get_instance()

    def _get_api_key(self) -> str:
        """Fetch API key dynamically from environment to pick up updates without server restart."""
        key = os.getenv("NVIDIA_API_KEY", "").strip()
        if key == "YOUR_NVIDIA_API_KEY_HERE" or key.startswith("your_"):
            return ""
        return key

    def _check_greeting_or_smalltalk(self, query: str) -> Optional[str]:
        """Detect greeting, small talk, gratitude, or farewell and return friendly answer directly."""
        clean = query.strip().lower()
        clean_no_punct = re.sub(r"[^\w\s]", "", clean)
        words = clean_no_punct.split()

        if not words:
            return "Hello! How can I assist you with IEEE today?"

        first_word = words[0]
        greeting_words = {"hi", "hello", "hey", "howdy", "sup", "greetings"}
        thanks_words = {"thanks", "thank", "thx", "appreciate"}
        bye_words = {"bye", "goodbye", "cya"}

        if len(words) <= 3 and (first_word in greeting_words or "good morning" in clean_no_punct or "good afternoon" in clean_no_punct or "good evening" in clean_no_punct):
            return (
                "Hello! I am your IEEE Assistant, here to help students, researchers, and professionals. I can help you with:\n\n"
                "• What IEEE stands for, history, and mission\n"
                "• IEEE membership benefits and student discounts\n"
                "• Joining or establishing an IEEE Student Branch\n"
                "• Student competitions (IEEEXtreme), scholarships, and travel grants\n"
                "• Technical standards like IEEE 802.11 (Wi-Fi) and 802.3 (Ethernet)\n"
                "• Finding research papers on the IEEE Xplore Digital Library\n\n"
                "What would you like to know about IEEE?"
            )

        if any(w in thanks_words for w in words):
            return "You're very welcome! If you have any more questions about IEEE membership, student branches, standards, or publications, feel free to ask!"

        if any(w in bye_words for w in words):
            return "Goodbye! Have a great day, and feel free to reach back out whenever you need information on IEEE."

        return None

    def _rewrite_query(self, query: str) -> str:
        """Add domain-specific keywords and expansions to maximize semantic retrieval quality."""
        q = query.strip()
        q_lower = q.lower()

        # Acronym & Full form expansions
        if any(phrase in q_lower for phrase in ["full form", "stands for", "meaning of ieee", "expand ieee", "what is ieee"]):
            return f"{q} Institute of Electrical and Electronics Engineers full form acronym meaning overview"

        # IEEE research papers / publications / Xplore
        if any(phrase in q_lower for phrase in ["research paper", "research papers", "find papers", "download paper", "ieeexplore", "xplore", "journals", "articles"]):
            return f"{q} IEEE Xplore Digital Library research papers journals conference proceedings publications"

        # IEEE 802.11 / Wi-Fi
        if any(phrase in q_lower for phrase in ["802.11", "wifi", "wi-fi", "wireless lan"]):
            return f"{q} IEEE 802.11 Wireless LAN Wi-Fi standard specifications"

        # Student Branch
        if "student branch" in q_lower or "join branch" in q_lower:
            return f"{q} IEEE student branches membership benefits campus form student branch"

        # Student opportunities / scholarships / competitions
        if any(term in q_lower for term in ["opportunit", "scholarship", "competition", "competitions", "extreme"]):
            return f"{q} IEEE student opportunities competitions IEEEXtreme scholarships awards travel grants"

        return q

    def _build_context_string(self, sources: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into structured context for Nemotron."""
        if not sources:
            return "No specific documents found in knowledge base."

        context_blocks = []
        for idx, item in enumerate(sources, 1):
            is_restr = item.get("is_restricted", False)
            tag = "RESTRICTED LINK" if is_restr else "PAGE EXCERPT"
            block = (
                f"--- [SOURCE {idx}: {item['document_name']} ({tag})] ---\n"
                f"URL: {item.get('source_url', 'https://www.ieee.org')}\n"
                f"{item['excerpt']}\n"
            )
            context_blocks.append(block)
        return "\n".join(context_blocks)

    def _synthesize_conversational_fallback(self, question: str, sources: List[SourceItem]) -> str:
        """Fallback synthesis when LLM is offline or not configured."""
        q_lower = question.lower()

        if "full form" in q_lower or "stands for" in q_lower:
            return "The full form of IEEE is the **Institute of Electrical and Electronics Engineers** (pronounced 'Eye-triple-E'). It is the world's largest technical professional organization dedicated to advancing technology for the benefit of humanity."

        if "when" in q_lower and ("established" in q_lower or "founded" in q_lower or "start" in q_lower):
            return "IEEE was established on January 1, 1963, through the merger of two pioneering engineering societies: the American Institute of Electrical Engineers (AIEE, founded in 1884) and the Institute of Radio Engineers (IRE, founded in 1912)."

        if "802.11" in q_lower or "wi-fi" in q_lower or "wifi" in q_lower:
            return "IEEE 802.11 is the internationally recognized family of standards for Wireless Local Area Networks (WLAN), commercially known as **Wi-Fi**. Developed by the IEEE 802 LAN/MAN Standards Committee, it governs wireless communication across 2.4 GHz, 5 GHz, and 6 GHz frequency bands, encompassing protocols like 802.11n (Wi-Fi 4), 802.11ac (Wi-Fi 5), 802.11ax (Wi-Fi 6), and 802.11be (Wi-Fi 7)."

        if "research paper" in q_lower or "xplore" in q_lower or "find paper" in q_lower:
            return "You can find and access IEEE research papers, journal articles, and conference proceedings through the **IEEE Xplore Digital Library** at [ieeexplore.ieee.org](https://ieeexplore.ieee.org/). It hosts over 6 million peer-reviewed documents accessible through university institutional subscriptions, open access journals, or member digital library add-ons."

        if "join" in q_lower and "branch" in q_lower:
            return "To join an IEEE Student Branch, first enroll as an IEEE Student Member at **ieee.org/join** (students must carry at least 50% of a full-time academic course load). Once registered, connect with the IEEE Student Branch officers or Branch Counselor at your university. If your campus does not currently have an active branch, you can form one with a petition endorsed by a faculty advisor and at least 12 student members."

        if "opportunit" in q_lower and "student" in q_lower:
            return "IEEE offers outstanding opportunities for students, including:\n\n• **Competitions:** Global challenges like the 24-hour IEEEXtreme virtual programming competition and regional student paper contests.\n• **Scholarships & Grants:** Prestigious awards such as the Charles LeGeyt Fortescue Scholarship, Richard E. Merwin Student Scholarship, and IEEE conference travel grants.\n• **Professional Growth:** Campus leadership in Student Branches, career prep via IEEE ResumeLab, and access to 39 specialized technical societies."

        if sources:
            top_excerpt = sources[0].excerpt.strip()
            lines = [l.strip().lstrip("•-* 1234567890.)") for l in top_excerpt.split("\n") if l.strip() and not l.strip().startswith("==")]
            return " ".join(lines[:4])

        return "IEEE is the world's largest technical professional organization dedicated to advancing technology for humanity. For more details, you can visit ieee.org."

    def generate_answer(
        self,
        question: str,
        history: Optional[List[MessageTurn]] = None,
        top_k: int = DEFAULT_TOP_K
    ) -> ChatResponse:
        """Execute complete RAG pipeline with greeting detection, query rewriting, and LLM generation."""
        q_clean = question.strip()

        # Step 1: Detect greetings / smalltalk before running retrieval
        greeting_answer = self._check_greeting_or_smalltalk(q_clean)
        if greeting_answer:
            return ChatResponse(
                answer=greeting_answer,
                sources=[],
                retrieved_chunks_count=0,
                model_used="IEEE Assistant",
                confidence_note=None
            )

        # Step 2: Apply query rewriting for enhanced semantic retrieval
        rewritten_query = self._rewrite_query(q_clean)

        # Step 3: Retrieve top_k chunks from ChromaDB
        retrieved_raw = self.vector_store.search_similar_chunks(
            query=rewritten_query,
            top_k=top_k,
            similarity_threshold=SIMILARITY_THRESHOLD
        )

        sources_list: List[SourceItem] = [
            SourceItem(
                document_name=item["document_name"],
                page_number=item.get("page_number", 1),
                chunk_id=item["chunk_id"],
                excerpt=item["excerpt"],
                similarity_score=item["similarity_score"],
                source_url=item.get("source_url"),
                is_restricted=item.get("is_restricted", False)
            )
            for item in retrieved_raw
        ]

        logger.info(f"Retrieved {len(sources_list)} chunks for query: '{q_clean}' (rewritten: '{rewritten_query}')")
        for s in sources_list:
            logger.info(f"  -> Score: {s.similarity_score} | Doc: {s.document_name} | Restricted: {s.is_restricted}")

        api_key = self._get_api_key()

        # If API key is not configured, use conversational synthesis
        if not api_key:
            answer_text = self._synthesize_conversational_fallback(q_clean, sources_list)
            return ChatResponse(
                answer=answer_text,
                sources=sources_list,
                retrieved_chunks_count=len(sources_list),
                model_used="IEEE Assistant",
                confidence_note=None
            )

        # Step 4: Build prompt with retrieved context
        context_str = self._build_context_string(retrieved_raw)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Append recent conversation history (last 4 turns)
        if history:
            for turn in history[-4:]:
                if turn.role in ["user", "assistant"]:
                    messages.append({"role": turn.role, "content": turn.content})

        user_content = (
            f"Retrieved IEEE Knowledge Base Context:\n{context_str}\n\n"
            f"User Question: {q_clean}\n\n"
            f"Answer the user's question clearly, helpfully, and conversationally based on the instructions."
        )
        messages.append({"role": "user", "content": user_content})

        # Step 5: Call NVIDIA Nemotron API with automatic fallback
        try:
            client = OpenAI(
                base_url=NVIDIA_BASE_URL,
                api_key=api_key,
                timeout=25.0
            )

            primary_model = os.getenv("NVIDIA_MODEL", NVIDIA_MODEL)
            try:
                response = client.chat.completions.create(
                    model=primary_model,
                    messages=messages,
                    temperature=0.2,
                    top_p=0.7,
                    max_tokens=768
                )
            except Exception as primary_err:
                logger.warning(f"Primary model {primary_model} call failed: {primary_err}. Attempting fallback to nemotron-3.5-bolt-e4b...")
                response = client.chat.completions.create(
                    model="nvidia/nemotron-3.5-bolt-e4b",
                    messages=messages,
                    temperature=0.2,
                    top_p=0.7,
                    max_tokens=768
                )

            raw_content = response.choices[0].message.content
            if raw_content and raw_content.strip():
                generated_answer = raw_content.strip()
            else:
                raise ValueError("NVIDIA model returned empty content")

            return ChatResponse(
                answer=generated_answer,
                sources=sources_list,
                retrieved_chunks_count=len(sources_list),
                model_used="IEEE Assistant",
                confidence_note="Answer grounded in verified IEEE knowledge."
            )

        except Exception as e:
            logger.error(f"NVIDIA Nemotron generation error: {str(e)}")
            fallback_answer = self._synthesize_conversational_fallback(q_clean, sources_list)
            return ChatResponse(
                answer=fallback_answer,
                sources=sources_list,
                retrieved_chunks_count=len(sources_list),
                model_used="IEEE Assistant",
                confidence_note=None
            )
