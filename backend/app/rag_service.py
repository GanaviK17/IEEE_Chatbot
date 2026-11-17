import os
import re
import logging
import random
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

class MessageIntent:
    CASUAL = "casual"                    # Greetings, small talk, pleasantries, farewells
    ACKNOWLEDGEMENT = "acknowledgement"  # "ok", "got it", "cool", "thanks", "understood"
    BOT_CAPABILITIES = "bot_capabilities" # "who are you?", "what can you do?", "how can you help me?"
    UNCLEAR = "unclear"                  # Gibberish, single punctuation, nonsensical input
    OFF_TOPIC = "off_topic"              # Clear non-technical/non-IEEE questions (cooking, weather, trivia)
    FOLLOW_UP = "follow_up"              # "tell me more", "what about Canada?", "why?", "how do I join it?"
    IEEE_QUERY = "ieee_query"            # Questions about IEEE, standards, publications, membership, etc.

# Authoritative, natural, concise IEEE Assistant system prompt
SYSTEM_PROMPT = """You are the official IEEE AI Assistant, an authoritative, knowledgeable, and friendly guide for students, researchers, faculty, and engineers worldwide.

COMMUNICATION PRINCIPLES:
1. Intent Awareness & Tone:
   - For greetings, small talk, and pleasantries, respond warmly, conversationally, and briefly.
   - For acknowledgements ("ok", "got it", "cool", "thanks"), respond naturally and concisely (1-2 sentences), offering helpful next steps if appropriate.
   - For follow-ups ("tell me more", "why?", "how do I join?"), maintain conversational continuity using prior turns. Expand only when the user asks for more detail.
   - For questions unrelated to IEEE, science, technology, or computing, politely and briefly state that you specialize in IEEE topics and offer to assist with technical or IEEE resources.
   - For unclear messages, politely ask a brief clarifying question instead of guessing.

2. Evidence & Grounding:
   - When answering IEEE questions, ground your response in the provided knowledge base evidence.
   - State facts accurately without making unsupported claims. Do not invent details not supported by the evidence or general IEEE knowledge.
   - When citing official websites, portals, or tools, format them cleanly as markdown links (e.g. [IEEE Xplore](https://ieeexplore.ieee.org/), [IEEE.org](https://www.ieee.org/)). Never output raw naked URL sentences.

3. Conciseness by Default:
   - Answer directly and concisely in 1 to 3 clear sentences by default.
   - Use bullet points ONLY when listing multiple distinct items, steps, or comparing alternatives. Do NOT force every answer into a bulleted list.
   - Only provide an in-depth or comprehensive breakdown when the user explicitly requests more detail, explanation, or a complete list.

4. Professional Voice:
   - Speak naturally and authoritatively as a knowledgeable guide representing IEEE.
   - NEVER use meta-language such as "the provided context does not state", "according to the reference information", "based on the provided documents", or "I was trained on"."""

class RAGService:
    def __init__(self):
        self.vector_store = VectorStoreManager.get_instance()

    def _get_api_key(self) -> str:
        """Fetch API key dynamically from environment to pick up updates without server restart."""
        key = os.getenv("NVIDIA_API_KEY", "").strip()
        if key == "YOUR_NVIDIA_API_KEY_HERE" or key.startswith("your_"):
            return ""
        return key

    def classify_intent(self, query: str, history: Optional[List[MessageTurn]] = None) -> str:
        """
        Classify user message intent dynamically into:
        CASUAL, ACKNOWLEDGEMENT, BOT_CAPABILITIES, UNCLEAR, OFF_TOPIC, FOLLOW_UP, or IEEE_QUERY.
        """
        clean = query.strip()
        if not clean:
            return MessageIntent.UNCLEAR

        q_lower = clean.lower()
        q_no_punct = re.sub(r"[^\w\s]", "", q_lower).strip()
        words = q_no_punct.split()

        # 1. Unclear check (empty, only punctuation, or repetitive keyboard mash)
        if not words:
            return MessageIntent.UNCLEAR
        if len(clean) >= 5 and re.search(r"([a-z])\1{3,}", q_lower):
            return MessageIntent.UNCLEAR
        # Random keyboard mash / non-word heuristic (e.g., asdfghjk, qwertyuiop, or 5+ consecutive consonants)
        if any(seq in q_lower for seq in ["asdf", "dfgh", "ghjk", "qwerty", "zxcv"]):
            return MessageIntent.UNCLEAR
        if len(words) == 1 and re.search(r"[bcdfghjklmnpqrstvwxyz]{5,}", q_lower):
            return MessageIntent.UNCLEAR
        if len(words) == 1 and len(clean) <= 2 and clean.lower() not in {"ai", "cs", "ie", "ip", "it", "r7", "ok", "hi"}:
            return MessageIntent.UNCLEAR

        # 2. Acknowledgements (e.g. "ok", "got it", "cool", "thanks", "understood", "makes sense")
        ack_terms = [
            "ok", "okay", "k", "got it", "understood", "makes sense", "cool",
            "nice", "awesome", "perfect", "great", "alright", "all right",
            "noted", "sure", "yep", "yeah", "sounds good", "clear", "fine"
        ]
        if any(q_no_punct == a or q_no_punct.startswith(a + " ") for a in ack_terms) and len(words) <= 4:
            return MessageIntent.ACKNOWLEDGEMENT

        # 3. Casual greetings, small talk, gratitude, farewells
        casual_starters = (
            "hi", "hello", "hey", "howdy", "sup", "greetings", "yo",
            "good morning", "good afternoon", "good evening", "good day",
            "how are you", "how are things", "hows it going", "what's up", "whats up"
        )
        farewells = {
            "bye", "goodbye", "cya", "see ya", "see you", "farewell",
            "take care", "have a nice day", "have a good day", "good night"
        }
        gratitude = {
            "thank you", "thanks", "thx", "appreciate it", "thank you so much",
            "many thanks", "thanks a lot"
        }

        # Check if query is primarily a greeting
        if any(q_no_punct == f or q_no_punct.startswith(f + " ") for f in casual_starters):
            # Ensure it is not a compound technical question like "Hello, what is IEEE 802.11?"
            has_tech_topic = any(kw in q_lower for kw in [
                "ieee", "standard", "branch", "paper", "xplore", "member", "join",
                "society", "what is", "how to", "where can", "why does"
            ])
            if len(words) <= 5 and not has_tech_topic:
                return MessageIntent.CASUAL
        if any(f in q_no_punct for f in farewells) and len(words) <= 5:
            return MessageIntent.CASUAL
        if any(g in q_no_punct for g in gratitude) and len(words) <= 5:
            return MessageIntent.CASUAL

        # 4. Bot identity / capabilities
        bot_meta_phrases = [
            "who are you", "what are you", "what can you do", "what do you do",
            "what is your name", "who created you", "who made you", "how can you help",
            "help me", "what are your capabilities", "introduce yourself", "what is this bot"
        ]
        if any(p in q_no_punct for p in bot_meta_phrases) and len(words) <= 8:
            return MessageIntent.BOT_CAPABILITIES

        # 5. Follow-ups (when conversation history is present)
        if history and len(history) > 0:
            follow_up_phrases = [
                "tell me more", "more", "can you elaborate", "elaborate",
                "expand on that", "explain more", "why", "why is that",
                "how so", "what else", "anything else", "what about",
                "how do i join it", "how to join it", "which one",
                "who can participate", "who is eligible", "and the second",
                "and the first", "give me more details"
            ]
            if any(q_no_punct == f or q_no_punct.startswith(f) for f in follow_up_phrases):
                return MessageIntent.FOLLOW_UP
            # Short pronoun-heavy question referring to previous turn e.g. "what are its branches?", "where is it?"
            referential_pronouns = {"it", "its", "that", "those", "these", "there", "they", "them", "this"}
            if any(p in words for p in referential_pronouns) and len(words) <= 12:
                return MessageIntent.FOLLOW_UP

        # 6. Off-topic check (cooking, weather, sports, general non-technical trivia)
        off_topic_starters = [
            "recipe for", "how to bake", "how to cook", "ingredients for",
            "weather in", "weather forecast", "capital of", "who won the",
            "movie recommendation", "recommend a movie", "who is the president of france",
            "who is the prime minister of", "joke", "tell me a joke"
        ]
        tech_whitelist = [
            "ieee", "engineering", "network", "software", "hardware", "wifi",
            "standard", "branch", "society", "xplore", "sensor", "algorithm",
            "computer", "telecom", "robot", "circuits", "signal", "power", "energy"
        ]
        if any(ots in q_lower for ots in off_topic_starters) and not any(tw in q_lower for tw in tech_whitelist):
            return MessageIntent.OFF_TOPIC

        # Default to core domain IEEE knowledge query
        return MessageIntent.IEEE_QUERY

    def contextualize_query(self, query: str, history: Optional[List[MessageTurn]]) -> str:
        """
        If the query is referential or an elliptical follow-up, merge key contextual entities
        from recent turns to make vector retrieval effective.
        """
        if not history:
            return query

        recent_context = []
        for turn in reversed(history[-4:]):
            content = turn.content.strip()
            if not content:
                continue
            # Strip URLs and markdown links from content
            clean_content = re.sub(r"https?://\S+|\[.*?\]\(.*?\)", "", content)
            # Find salient IEEE entities or proper nouns
            entities = re.findall(
                r"\b(?:IEEE[A-Za-z0-9\-_]*|Region\s*\d+|Section|Subsection|Student Branch|Xplore|Standards?|802\.\d+|IEEEXtreme|WIE|YP|PES|CS|ComSoc|NISB|Canada|Toronto|Vancouver|Bangalore|Mysore)\b",
                clean_content,
                re.IGNORECASE
            )
            for e in entities:
                if e.lower() not in [x.lower() for x in recent_context]:
                    recent_context.append(e)
                if len(recent_context) >= 3:
                    break
            if len(recent_context) >= 3:
                break

        if recent_context:
            return f"{query} {' '.join(recent_context)}"
        return query

    def _rewrite_query(self, query: str) -> str:
        """Add domain-specific keywords and acronym expansions to maximize semantic retrieval quality."""
        q = query.strip()
        q_lower = q.lower()

        # Acronym & Full form expansions
        if any(phrase in q_lower for phrase in ["full form", "stands for", "meaning of ieee", "expand ieee", "what is ieee"]):
            return f"{q} Institute of Electrical and Electronics Engineers full form acronym meaning overview"

        # Websites, URLs, portals, directories
        if any(term in q_lower for term in ["url", "urls", "website", "websites", "link", "links", "portal", "portals"]):
            return f"{q} IEEE official portals websites directories links Xplore Standards Students Join Computer Society"

        # Canada / Region 7 / Canadian branches
        if any(phrase in q_lower for phrase in ["canada", "canadian", "region 7", "r7"]):
            return f"{q} IEEE Canada Region 7 student branches Toronto Vancouver McGill Waterloo"

        # Famous publications / Journals / Magazines / Transactions
        if any(phrase in q_lower for phrase in ["publication", "publications", "journal", "journals", "transaction", "transactions", "magazine", "magazines"]):
            return f"{q} famous high-impact IEEE publications Proceedings of the IEEE TPAMI TNNLS JSAC TIT IEEE Spectrum Access"

        # IEEE research papers / publications / Xplore
        if any(phrase in q_lower for phrase in ["research paper", "research papers", "find papers", "download paper", "ieeexplore", "xplore"]):
            return f"{q} IEEE Xplore Digital Library research papers journals conference proceedings publications"

        # IEEE 802.11 / Wi-Fi
        if any(phrase in q_lower for phrase in ["802.11", "wifi", "wi-fi", "wireless lan"]):
            return f"{q} IEEE 802.11 Wireless LAN Wi-Fi standard specifications"

        # NISB / NIE IEEE Student Branch
        if "nisb" in q_lower or "nie ieee" in q_lower:
            return f"{q} NISB NIE IEEE Student Branch National Institute of Engineering Mysuru Bangalore Section Mysore Subsection"

        # Sections, Subsections, Councils, Regions
        if any(term in q_lower for term in ["section", "subsection", "region", "council", "bangalore", "mysore", "mysuru"]):
            return f"{q} IEEE geographic organization 10 regions sections subsections Bangalore Section Mysore Subsection"

        # Student opportunities / scholarships / competitions
        if any(term in q_lower for term in ["opportunit", "scholarship", "competition", "competitions", "extreme"]):
            return f"{q} IEEE student opportunities competitions IEEEXtreme scholarships awards travel grants"

        # Technical societies
        if any(term in q_lower for term in ["society", "societies", "comsoc", "computer society", "pes", "ras"]):
            return f"{q} 39 IEEE Technical Societies and Councils Computer Society PES Communications Robotics"

        return q

    def _post_process_answer(self, text: str) -> str:
        """Clean up LLM artifacts, malformed bullet points, raw URL lines, and unwanted symbols."""
        if not text:
            return ""

        clean = text.strip()

        # 0. Clean bold wrapping around bare URLs: **https://ieeexplore.ieee.org/** -> https://ieeexplore.ieee.org/
        clean = re.sub(r'\*\*(https?://[^\s*]+)\*\*', r'\1', clean)

        # 1. Eliminate any meta-sentences mentioning "reference information", "provided context", etc.
        meta_sentence_pattern = (
            r'(?i)\b(i cannot [^.\n]*because\s+)?(the\s+)?(provided\s+)?(reference(\s+information)?|context|documents?)\s*'
            r'(describes?|states?(\s+that)?|mentions?|does not (list|state|contain|mention)|indicates?|shows?)[^.\n]*[\.:;]\s*'
        )
        clean = re.sub(meta_sentence_pattern, '', clean).strip()

        leading_meta_pattern = (
            r'^(based on (the )?(provided )?(context|information|documents|reference|knowledge base)[,\s:]*|'
            r'according to (the )?(provided )?(context|information|documents|reference)[,\s:]*|'
            r'from the (provided )?(context|information|documents|reference)[,\s:]*|'
            r'as per the (provided )?(context|information|documents|reference)[,\s:]*|'
            r'in the (provided )?(context|information|documents|reference)[,\s:]*|'
            r'the provided (reference|context|document|information)[^.\n]*[,:\s]+)'
        )
        clean = re.sub(leading_meta_pattern, '', clean, flags=re.IGNORECASE).strip()

        # 2. Fix inline asterisks or bullets running together on a single line:
        # e.g., "society. * **Magazines**:" -> split cleanly to newlines
        clean = re.sub(r'([.:?!])\s*[\*•\-]\s+', r'\1\n\n• ', clean)
        clean = re.sub(r'(?<!\n)\s+[\*•\-]\s+', '\n\n• ', clean)
        clean = re.sub(r'(?m)^[\*\-]\s+', '• ', clean)

        # 3. Strip awkward trailing bot sentences like "You can find/search more information at https://..."
        raw_url_filler_pattern = (
            r'(?im)\n*(you can (find|search|visit|explore|access) (more )?(information|details)? (at|on|via)?\s*(\*\*)?https?://[^\s)]+[\w/.]*(\*\*)?(\s*by topic[^\n.]*)?\.*)'
        )
        clean = re.sub(raw_url_filler_pattern, '', clean).strip()

        # 4. Domain-aware clean markdown link formatting for remaining bare URLs
        def replace_bare_url(match):
            url = match.group(0).rstrip('.,;:')
            url_lower = url.lower()
            if "ieeexplore" in url_lower:
                return f"[IEEE Xplore]({url})"
            elif "nisb.in" in url_lower:
                return f"[NISB Portal]({url})"
            elif "computer.org" in url_lower:
                return f"[IEEE Computer Society]({url})"
            elif "comsoc.org" in url_lower:
                return f"[IEEE Communications Society]({url})"
            elif "ieee-pes.org" in url_lower:
                return f"[IEEE Power & Energy Society]({url})"
            elif "ieee-ras.org" in url_lower:
                return f"[IEEE Robotics and Automation Society]({url})"
            elif "standards.ieee.org" in url_lower:
                return f"[IEEE Standards Association]({url})"
            elif "students.ieee.org" in url_lower:
                return f"[IEEE Students Portal]({url})"
            elif "ieeextreme.org" in url_lower:
                return f"[IEEEXtreme Competition]({url})"
            elif "wie.ieee.org" in url_lower:
                return f"[IEEE Women in Engineering]({url})"
            elif "yp.ieee.org" in url_lower:
                return f"[IEEE Young Professionals]({url})"
            elif "sight.ieee.org" in url_lower:
                return f"[IEEE SIGHT]({url})"
            elif "spectrum.ieee.org" in url_lower:
                return f"[IEEE Spectrum]({url})"
            elif "authorcenter.ieee.org" in url_lower:
                return f"[IEEE Author Center]({url})"
            elif "ieee-dataport.org" in url_lower:
                return f"[IEEE DataPort]({url})"
            elif "jobs.ieee.org" in url_lower:
                return f"[IEEE Job Site]({url})"
            elif "iln.ieee.org" in url_lower:
                return f"[IEEE Learning Network]({url})"
            elif "tryengineering.org" in url_lower:
                return f"[IEEE TryEngineering]({url})"
            elif "vtools.ieee.org" in url_lower:
                return f"[IEEE vTools]({url})"
            elif "ieee-collabratec.ieee.org" in url_lower:
                return f"[IEEE Collabratec]({url})"
            elif "ieeefoundation.org" in url_lower:
                return f"[IEEE Foundation]({url})"
            elif "ethw.org" in url_lower:
                return f"[IEEE History Center (ETHW)]({url})"
            elif "ieeeusa.org" in url_lower:
                return f"[IEEE-USA]({url})"
            elif "ieee.ca" in url_lower:
                return f"[IEEE Canada]({url})"
            elif "ieeer10.org" in url_lower:
                return f"[IEEE Region 10]({url})"
            elif "ieeer8.org" in url_lower:
                return f"[IEEE Region 8]({url})"
            elif "ieeeindiacouncil.org" in url_lower:
                return f"[IEEE India Council]({url})"
            elif "ieeebangalore.org" in url_lower:
                return f"[IEEE Bangalore Section]({url})"
            elif "mysore.ieeebangalore.org" in url_lower:
                return f"[IEEE Mysore Subsection]({url})"
            elif "branch-finder" in url_lower:
                return f"[IEEE Student Branch Finder]({url})"
            elif "join" in url_lower:
                return f"[IEEE Membership Portal]({url})"
            elif "ieee.org" in url_lower:
                return f"[IEEE.org]({url})"
            return f"[{url}]({url})"

        clean = re.sub(r'(?<![\[\(])https?://[^\s)\]]+', replace_bare_url, clean)
        clean = re.sub(r'\[+\[([^\]]+)\]\([^\)]+\)\]+\((https?://[^\s)]+)\)', r'[\1](\2)', clean)

        # 4b. If any markdown link has a raw URL as its label [https://...](https://...), replace the label
        def format_md_link_label(match):
            label = match.group(1).strip()
            url = match.group(2).strip()
            if label.startswith("http://") or label.startswith("https://"):
                dummy_match = re.match(r'.*', url)
                return replace_bare_url(dummy_match)
            return f"[{label}]({url})"

        clean = re.sub(r'\[(https?://[^\s\]]+)\]\((https?://[^\s\)]+)\)', format_md_link_label, clean)

        # 5. Fix doubled periods '..' -> '.'
        clean = re.sub(r'\.{2,}', '.', clean)

        # 6. Ensure initial letter is capitalized
        if clean and clean[0].islower():
            clean = clean[0].upper() + clean[1:]

        return clean.strip()

    def _build_context_string(self, sources: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into structured context for Nemotron."""
        if not sources:
            return ""

        context_blocks = []
        for idx, item in enumerate(sources, 1):
            is_restr = item.get("is_restricted", False)
            tag = "RESTRICTED PORTAL" if is_restr else "VERIFIED OVERVIEW"
            block = (
                f"--- [SOURCE {idx}: {item['document_name']} ({tag})] ---\n"
                f"URL: {item.get('source_url', 'https://www.ieee.org')}\n"
                f"{item['excerpt']}\n"
            )
            context_blocks.append(block)
        return "\n".join(context_blocks)

    def _synthesize_offline_fallback(
        self,
        question: str,
        intent: str,
        sources: List[SourceItem],
        history: Optional[List[MessageTurn]] = None
    ) -> ChatResponse:
        """
        Differentiated and transparent fallback synthesis when AI model is offline or unconfigured.
        Clearly informs the user that the system is operating in offline direct retrieval mode
        and tailors the output specifically to the message and retrieved evidence.
        """
        q_clean = question.strip()

        # Casual greeting fallback
        if intent == MessageIntent.CASUAL:
            return ChatResponse(
                answer="Hello! I am the IEEE Assistant. (Offline search mode is active.) How can I help you explore IEEE student branches, technical standards, or research publications today?",
                sources=[],
                retrieved_chunks_count=0,
                model_used="IEEE Assistant (Offline Fallback)",
                confidence_note="Note: AI model service is currently offline. Operating in direct knowledge retrieval mode."
            )

        # Acknowledgement fallback
        if intent == MessageIntent.ACKNOWLEDGEMENT:
            return ChatResponse(
                answer="You're welcome! Let me know if you'd like to explore any other IEEE topics, student programs, or technical publications.",
                sources=[],
                retrieved_chunks_count=0,
                model_used="IEEE Assistant (Offline Fallback)",
                confidence_note="Note: AI model service is currently offline."
            )

        # Bot capabilities fallback
        if intent == MessageIntent.BOT_CAPABILITIES:
            return ChatResponse(
                answer="I am the IEEE AI Assistant, designed to help students, researchers, and engineers explore IEEE membership, student branches, technical societies, research publications on IEEE Xplore, competitions like IEEEXtreme, and international standards like IEEE 802.11.",
                sources=[],
                retrieved_chunks_count=0,
                model_used="IEEE Assistant (Offline Fallback)",
                confidence_note="Note: AI model service is currently offline."
            )

        # Unclear query fallback
        if intent == MessageIntent.UNCLEAR:
            return ChatResponse(
                answer="Could you please rephrase or clarify your question? In offline mode, I can search the verified IEEE knowledge base for specific topics like membership, standards, student branches, or publications.",
                sources=[],
                retrieved_chunks_count=0,
                model_used="IEEE Assistant (Offline Fallback)",
                confidence_note="Note: AI model service is currently offline."
            )

        # Off-topic query fallback
        if intent == MessageIntent.OFF_TOPIC:
            return ChatResponse(
                answer="I specialize in IEEE engineering resources, technical standards, publications, and student programs rather than general topics. Please let me know how I can help with IEEE or technical resources.",
                sources=[],
                retrieved_chunks_count=0,
                model_used="IEEE Assistant (Offline Fallback)",
                confidence_note="Note: AI model service is currently offline."
            )

        # Substantive IEEE or follow-up query with retrieved chunks
        if sources:
            top_sources = sources[:2]
            key_points = []
            for s in top_sources:
                # Extract clean informative lines
                lines = [
                    l.strip().lstrip("•-* 1234567890.)")
                    for l in s.excerpt.split("\n")
                    if l.strip() and not l.strip().startswith("==") and not l.strip().startswith("#")
                ]
                for line in lines[:3]:
                    if line and len(line) > 20 and line not in key_points:
                        key_points.append(line)

            summary_text = "\n".join(f"• {p}" for p in key_points[:4]) if key_points else sources[0].excerpt[:300]
            answer_text = (
                f"Directly retrieved from verified IEEE documentation for '{q_clean}':\n\n"
                f"{summary_text}\n\n"
                f"For full documentation, please refer to the cited sources below."
            )
            return ChatResponse(
                answer=self._post_process_answer(answer_text),
                sources=sources,
                retrieved_chunks_count=len(sources),
                model_used="IEEE Knowledge Base (Direct Retrieval)",
                confidence_note="Note: AI model service is currently unavailable. Response extracted directly from local IEEE knowledge base."
            )

        # Substantive query with no matching chunks
        no_match_text = (
            f"I could not find verified documentation in the local IEEE knowledge base matching '{q_clean}'. "
            f"For more comprehensive resources, please visit the official [IEEE.org](https://www.ieee.org/) portal or rephrase your query with additional keywords."
        )
        return ChatResponse(
            answer=self._post_process_answer(no_match_text),
            sources=[],
            retrieved_chunks_count=0,
            model_used="IEEE Knowledge Base (Direct Retrieval)",
            confidence_note="Note: AI model service is currently unavailable. No matching records found."
        )

    def _call_llm(
        self,
        messages: List[Dict[str, str]],
        api_key: str,
        max_tokens: int = 400,
        temperature: float = 0.3
    ) -> str:
        """Call NVIDIA Nemotron with automatic model fallback."""
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
                temperature=temperature,
                top_p=0.8,
                max_tokens=max_tokens
            )
        except Exception as primary_err:
            logger.warning(f"Primary model {primary_model} call failed: {primary_err}. Attempting fallback...")
            response = client.chat.completions.create(
                model="nvidia/nemotron-3.5-bolt-e4b",
                messages=messages,
                temperature=temperature,
                top_p=0.8,
                max_tokens=max_tokens
            )

        content = response.choices[0].message.content
        if not content or not content.strip():
            raise ValueError("NVIDIA model returned empty content")
        return content.strip()

    def generate_answer(
        self,
        question: str,
        history: Optional[List[MessageTurn]] = None,
        top_k: int = DEFAULT_TOP_K
    ) -> ChatResponse:
        """
        Complete RAG pipeline with:
        1. Contextual intent classification (casual, acknowledgement, bot meta, unclear, off-topic, follow-up, or IEEE query).
        2. Bypassing vector retrieval for non-knowledge interactions to avoid polluting context.
        3. Multi-turn query contextualization for referential follow-ups.
        4. Concise, evidence-grounded answers without forced bullets or unrequested examples.
        5. Differentiated, transparent fallback when AI model is offline.
        """
        q_clean = question.strip()
        api_key = self._get_api_key()
        intent = self.classify_intent(q_clean, history)

        logger.info(f"Classified query '{q_clean}' as intent: {intent}")

        # ----------------------------------------------------------------------
        # Case A: Unclear or gibberish input -> polite clarifying question
        # ----------------------------------------------------------------------
        if intent == MessageIntent.UNCLEAR:
            clarify_text = (
                "I'm not quite sure I understood that. Could you please clarify what you'd like to know "
                "about IEEE, its student programs, technical standards, or research resources?"
            )
            return ChatResponse(
                answer=clarify_text,
                sources=[],
                retrieved_chunks_count=0,
                model_used="IEEE Assistant",
                confidence_note=None
            )

        # ----------------------------------------------------------------------
        # Case B: Off-topic input -> polite scope boundary without hallucinations
        # ----------------------------------------------------------------------
        if intent == MessageIntent.OFF_TOPIC:
            off_topic_text = (
                "I specialize in IEEE engineering resources, technical standards (such as Wi-Fi 802.11), "
                "student branches, research publications on IEEE Xplore, and membership opportunities. "
                "If you have any questions in those areas, I'd be happy to help!"
            )
            return ChatResponse(
                answer=off_topic_text,
                sources=[],
                retrieved_chunks_count=0,
                model_used="IEEE Assistant",
                confidence_note=None
            )

        # ----------------------------------------------------------------------
        # Case C: Casual greeting or small talk -> brief, natural, conversational response
        # ----------------------------------------------------------------------
        if intent == MessageIntent.CASUAL:
            if api_key:
                try:
                    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                    if history:
                        for turn in history[-4:]:
                            if turn.role in ["user", "assistant"]:
                                messages.append({"role": turn.role, "content": turn.content})
                    messages.append({
                        "role": "user",
                        "content": f"{q_clean}\n\n(Respond warmly, naturally, and briefly in 1-2 sentences. Offer to help with IEEE topics.)"
                    })
                    raw_reply = self._call_llm(messages, api_key, max_tokens=150, temperature=0.7)
                    return ChatResponse(
                        answer=self._post_process_answer(raw_reply),
                        sources=[],
                        retrieved_chunks_count=0,
                        model_used="IEEE Assistant",
                        confidence_note=None
                    )
                except Exception as e:
                    logger.warning(f"Casual LLM call failed: {e}")

            return self._synthesize_offline_fallback(q_clean, intent, [], history)

        # ----------------------------------------------------------------------
        # Case D: Acknowledgement -> natural, concise receipt maintaining conversation flow
        # ----------------------------------------------------------------------
        if intent == MessageIntent.ACKNOWLEDGEMENT:
            if api_key:
                try:
                    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                    if history:
                        for turn in history[-4:]:
                            if turn.role in ["user", "assistant"]:
                                messages.append({"role": turn.role, "content": turn.content})
                    messages.append({
                        "role": "user",
                        "content": f"{q_clean}\n\n(Acknowledge concisely in 1-2 friendly sentences. Do not dump technical overviews.)"
                    })
                    raw_reply = self._call_llm(messages, api_key, max_tokens=100, temperature=0.5)
                    return ChatResponse(
                        answer=self._post_process_answer(raw_reply),
                        sources=[],
                        retrieved_chunks_count=0,
                        model_used="IEEE Assistant",
                        confidence_note=None
                    )
                except Exception as e:
                    logger.warning(f"Acknowledgement LLM call failed: {e}")

            return self._synthesize_offline_fallback(q_clean, intent, [], history)

        # ----------------------------------------------------------------------
        # Case E: Bot capabilities & identity
        # ----------------------------------------------------------------------
        if intent == MessageIntent.BOT_CAPABILITIES:
            if api_key:
                try:
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": f"{q_clean}\n\n(Briefly summarize what you can help with regarding IEEE membership, student branches, publications, and standards in 2-3 direct sentences.)"
                        }
                    ]
                    raw_reply = self._call_llm(messages, api_key, max_tokens=180, temperature=0.3)
                    return ChatResponse(
                        answer=self._post_process_answer(raw_reply),
                        sources=[],
                        retrieved_chunks_count=0,
                        model_used="IEEE Assistant",
                        confidence_note=None
                    )
                except Exception as e:
                    logger.warning(f"Bot capabilities LLM call failed: {e}")

            return self._synthesize_offline_fallback(q_clean, intent, [], history)

        # ----------------------------------------------------------------------
        # Case F: Substantive IEEE Queries & Follow-ups -> Grounded RAG Retrieval
        # ----------------------------------------------------------------------
        # For referential follow-ups, contextualize with previous turns
        words = re.sub(r"[^\w\s]", "", q_clean.lower()).split()
        referential_pronouns = {"it", "its", "that", "those", "these", "there", "they", "them", "this"}
        if intent == MessageIntent.FOLLOW_UP or (history and any(p in words for p in referential_pronouns)):
            search_query = self.contextualize_query(q_clean, history)
        else:
            search_query = self._rewrite_query(q_clean)

        # Retrieve top_k chunks from ChromaDB
        retrieved_raw = self.vector_store.search_similar_chunks(
            query=search_query,
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

        logger.info(f"Retrieved {len(sources_list)} chunks for query: '{q_clean}' (search: '{search_query}')")

        # If API key is not configured, use transparent offline fallback
        if not api_key:
            return self._synthesize_offline_fallback(q_clean, intent, sources_list, history)

        # Build prompt with retrieved evidence and conversation history
        context_str = self._build_context_string(retrieved_raw)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Append recent conversation history (last 6 turns = 3 exchanges)
        if history:
            for turn in history[-6:]:
                if turn.role in ["user", "assistant"] and turn.content:
                    messages.append({"role": turn.role, "content": turn.content})

        if context_str:
            user_prompt = (
                f"Verified IEEE Knowledge Base Evidence:\n{context_str}\n\n"
                f"User Question: {q_clean}\n\n"
                f"Instructions:\n"
                f"- Answer directly, factually, and concisely using the verified evidence above.\n"
                f"- Be concise by default (1-3 sentences, or a short list only if multiple distinct items are requested).\n"
                f"- Only provide an in-depth breakdown if the user explicitly requested detailed explanation.\n"
                f"- Do not pad answers with boilerplate, filler, or unrequested examples.\n"
                f"- Format official tool or website mentions as clean markdown links (e.g. [IEEE Xplore](https://ieeexplore.ieee.org/))."
            )
        else:
            user_prompt = (
                f"User Question: {q_clean}\n\n"
                f"Instructions:\n"
                f"- Answer directly, factually, and concisely from your knowledge of IEEE.\n"
                f"- Be concise by default (1-3 sentences).\n"
                f"- Format links cleanly as markdown."
            )

        messages.append({"role": "user", "content": user_prompt})

        try:
            raw_content = self._call_llm(messages, api_key, max_tokens=512, temperature=0.2)
            clean_text = self._post_process_answer(raw_content)

            return ChatResponse(
                answer=clean_text,
                sources=sources_list,
                retrieved_chunks_count=len(sources_list),
                model_used="IEEE Assistant",
                confidence_note="Answer grounded in verified IEEE knowledge." if sources_list else None
            )

        except Exception as e:
            logger.error(f"NVIDIA Nemotron generation error: {str(e)}")
            return self._synthesize_offline_fallback(q_clean, intent, sources_list, history)
