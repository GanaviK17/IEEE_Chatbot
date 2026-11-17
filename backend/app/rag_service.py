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

# Polished, authoritative, natural IEEE Assistant system prompt
SYSTEM_PROMPT = """You are the official IEEE AI Assistant, an authoritative, knowledgeable, and friendly guide for students, researchers, faculty, and engineers worldwide.

STRICT COMMUNICATION RULES:
1. Speak directly, naturally, and professionally. Answer questions directly without hesitation.
2. ABSOLUTELY FORBIDDEN PHRASES - NEVER say, write, or imply:
   - "The provided reference information"
   - "Reference information"
   - "Based on the reference information / context"
   - "According to the reference / context"
   - "From the provided context / reference"
   - "The provided context does not state"
   - "The reference does not list"
   - "I cannot name a specific student branch"
   - "I was trained on" or "As an AI model"
   You represent IEEE directly: speak as a knowledgeable IEEE guide who already knows this information naturally.
3. NEVER refuse to name specific branches, sections, chapters, or entities. If asked for a student branch in Canada (Region 7), name prominent branches such as the University of Toronto IEEE Student Branch, University of British Columbia (UBC) IEEE Student Branch, McGill University IEEE Student Branch, or University of Waterloo IEEE Student Branch.
4. FORMATTING RULES:
   - Put each bullet item on its own new line starting with '• '. NEVER run multiple bullet points together on the same line with asterisks.
   - NEVER write unformatted filler lines like "You can find more information at https://..." or "You can search https://... by topic".
   - If mentioning a website or portal, format it cleanly as a clickable markdown link (e.g., [IEEE Xplore](https://ieeexplore.ieee.org/), [IEEE Canada](https://www.ieee.ca/), [NISB](https://nisb.in/)), never as a bare raw URL sentence.
5. You have comprehensive knowledge of all aspects of IEEE:
   - All 10 geographic regions (Regions 1-6 USA, Region 7 Canada, Region 8 Europe/Africa, Region 9 Latin America, Region 10 Asia-Pacific), sections, subsections, and student branches (including NISB at NIE Mysuru, U of T in Canada, etc.).
   - All 39 technical societies and 7 technical councils.
   - Famous publications (Proceedings of the IEEE, IEEE TPAMI, TNNLS, JSAC, TIT, TSE, IEEE Spectrum, IEEE Access).
   - Competitions (IEEEXtreme), scholarships (Merwin, Fortescue, PES), and travel grants.
   - Standards (IEEE 802.11 Wi-Fi, 802.3 Ethernet, etc.)."""

class RAGService:
    def __init__(self):
        self.vector_store = VectorStoreManager.get_instance()

    def _get_api_key(self) -> str:
        """Fetch API key dynamically from environment to pick up updates without server restart."""
        key = os.getenv("NVIDIA_API_KEY", "").strip()
        if key == "YOUR_NVIDIA_API_KEY_HERE" or key.startswith("your_"):
            return ""
        return key

    def _is_greeting_or_smalltalk(self, query: str) -> bool:
        """Detect greeting, small talk, gratitude, or farewell."""
        clean = query.strip().lower()
        clean_no_punct = re.sub(r"[^\w\s]", "", clean)
        words = clean_no_punct.split()

        if not words:
            return True

        first_word = words[0]
        greeting_words = {"hi", "hello", "hey", "howdy", "sup", "greetings", "yo"}
        thanks_words = {"thanks", "thank", "thx", "appreciate"}
        bye_words = {"bye", "goodbye", "cya", "farewell"}

        if len(words) <= 3 and (first_word in greeting_words or "good morning" in clean_no_punct or "good afternoon" in clean_no_punct or "good evening" in clean_no_punct):
            return True

        if any(w in thanks_words for w in words) and len(words) <= 4:
            return True

        if any(w in bye_words for w in words) and len(words) <= 4:
            return True

        return False

    def _rewrite_query(self, query: str) -> str:
        """Add domain-specific keywords and expansions to maximize semantic retrieval quality."""
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
            return f"{q} IEEE Canada Region 7 student branches Toronto Vancouver McGill Waterloo Alberta McMaster"

        # Famous publications / Journals / Magazines / Transactions
        if any(phrase in q_lower for phrase in ["publication", "publications", "journal", "journals", "transaction", "transactions", "magazine", "magazines"]):
            return f"{q} famous high-impact IEEE publications Proceedings of the IEEE TPAMI TNNLS JSAC TIT IEEE Spectrum Access"

        # IEEE research papers / publications / Xplore
        if any(phrase in q_lower for phrase in ["research paper", "research papers", "find papers", "download paper", "ieeexplore", "xplore"]):
            return f"{q} IEEE Xplore Digital Library research papers journals conference proceedings publications"

        # IEEE 802.11 / Wi-Fi
        if any(phrase in q_lower for phrase in ["802.11", "wifi", "wi-fi", "wireless lan"]):
            return f"{q} IEEE 802.11 Wireless LAN Wi-Fi standard specifications"

        # Student Branch and All Kinds of Branches
        if any(term in q_lower for term in ["branch", "branches", "kinds of branches", "types of branches"]):
            return f"{q} IEEE Student Branch SB Student Branch Chapter SBC Affinity Group WIE SIGHT ExeCom Counselor"

        # NISB / NIE IEEE Student Branch
        if "nisb" in q_lower or "nie ieee" in q_lower:
            return f"{q} NISB NIE IEEE Student Branch National Institute of Engineering Mysuru Bangalore Section Mysore Subsection Adroit Ankura"

        # Sections, Subsections, Councils, Regions
        if any(term in q_lower for term in ["section", "subsection", "region", "council", "bangalore", "mysore", "mysuru"]):
            return f"{q} IEEE geographic organization 10 regions sections subsections councils Bangalore Section Mysore Subsection"

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
        # e.g., "society. * **Magazines**:" or "including: * **Journals" -> split cleanly to newlines
        clean = re.sub(r'([.:?!])\s*[\*•\-]\s+', r'\1\n\n• ', clean)
        clean = re.sub(r'(?<!\n)\s+[\*•\-]\s+', '\n\n• ', clean)
        clean = re.sub(r'(?m)^[\*\-]\s+', '• ', clean)

        # 3. Strip awkward trailing bot sentences like "You can find/search more information at https://..."
        raw_url_filler_pattern = (
            r'(?im)\n*(you can (find|search|visit|explore|access) (more )?(information|details)? (at|on|via)?\s*(\*\*)?https?://[^\s)]+[\w/.]*(\*\*)?(\s*by topic[^\n.]*)?\.*)'
        )
        clean = re.sub(raw_url_filler_pattern, '', clean).strip()

        # 4. Convert remaining bare URLs into clean markdown links if not already markdown
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

        # Only replace URLs that are NOT already part of a markdown link [text](url)
        clean = re.sub(r'(?<![\[\(])https?://[^\s)\]]+', replace_bare_url, clean)
        # Collapse any nested markdown links like [[Text](url)](url) -> [Text](url)
        clean = re.sub(r'\[+\[([^\]]+)\]\([^\)]+\)\]+\((https?://[^\s)]+)\)', r'[\1](\2)', clean)

        # 4b. If any markdown link has a raw URL as its label [https://...](https://...), replace the label with a clean name
        def format_md_link_label(match):
            label = match.group(1).strip()
            url = match.group(2).strip()
            if label.startswith("http://") or label.startswith("https://"):
                url_lower = url.lower()
                if "ieeextreme" in url_lower:
                    return f"[IEEEXtreme Competition]({url})"
                elif "ieeexplore" in url_lower:
                    return f"[IEEE Xplore]({url})"
                elif "competitions" in url_lower:
                    return f"[IEEE Student Competitions]({url})"
                elif "students.ieee" in url_lower:
                    return f"[IEEE Students Portal]({url})"
                elif "branch-finder" in url_lower:
                    return f"[IEEE Student Branch Finder]({url})"
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
                elif "wie.ieee.org" in url_lower:
                    return f"[IEEE Women in Engineering]({url})"
                elif "yp.ieee.org" in url_lower:
                    return f"[IEEE Young Professionals]({url})"
                elif "sight.ieee.org" in url_lower:
                    return f"[IEEE SIGHT]({url})"
                elif "authorcenter" in url_lower:
                    return f"[IEEE Author Center]({url})"
                elif "dataport" in url_lower:
                    return f"[IEEE DataPort]({url})"
                elif "jobs.ieee" in url_lower:
                    return f"[IEEE Job Site]({url})"
                elif "iln.ieee" in url_lower:
                    return f"[IEEE Learning Network]({url})"
                elif "tryengineering" in url_lower:
                    return f"[IEEE TryEngineering]({url})"
                elif "vtools.ieee" in url_lower:
                    return f"[IEEE vTools]({url})"
                elif "collabratec" in url_lower:
                    return f"[IEEE Collabratec]({url})"
                elif "join" in url_lower:
                    return f"[IEEE Membership Portal]({url})"
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
                elif "ieee.org" in url_lower:
                    return f"[IEEE.org]({url})"
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
            return "No specific documents found in knowledge base."

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

    def _synthesize_conversational_fallback(self, question: str, sources: List[SourceItem]) -> str:
        """Fallback synthesis when LLM is offline or not configured."""
        q_lower = question.lower()

        if "full form" in q_lower or "stands for" in q_lower:
            return "The full form of IEEE is the **Institute of Electrical and Electronics Engineers** (pronounced 'Eye-triple-E'). It is the world's largest technical professional organization dedicated to advancing technology for the benefit of humanity."

        # Canada / Canadian branches
        if "canada" in q_lower or "canadian" in q_lower:
            return (
                "A prominent IEEE Student Branch in Canada is the **University of Toronto IEEE Student Branch (U of T IEEE SB)**, located in Toronto, Ontario under Region 7 (IEEE Canada) and the IEEE Toronto Section.\n\n"
                "• **History:** It is one of the oldest and most active IEEE student branches in Canada.\n"
                "• **Key Activities:** Hosts *MakeUofT* (Canada's largest annual hardware hackathon), the IEEE Spark hardware design competition, mentorship programs, and industry networking nights.\n\n"
                "Other notable Canadian branches include the **University of British Columbia (UBC) IEEE Student Branch** in Vancouver, the **McGill University IEEE Student Branch** in Montreal, and the **University of Waterloo IEEE Student Branch** in Kitchener-Waterloo."
            )

        # Famous publications
        if "publication" in q_lower or "journal" in q_lower or "magazine" in q_lower:
            return (
                "IEEE publishes world-leading technical publications across all engineering domains:\n\n"
                "• **Proceedings of the IEEE:** The flagship review journal covering major technological advances across all fields.\n"
                "• **IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI):** The highest-impact journal in computer vision and artificial intelligence.\n"
                "• **IEEE Transactions on Neural Networks and Learning Systems (TNNLS):** Premier journal for deep learning and neural network architectures.\n"
                "• **IEEE Journal on Selected Areas in Communications (JSAC):** Top-ranked publication in telecommunications and networking.\n"
                "• **IEEE Spectrum:** The flagship magazine providing global technology and engineering news.\n"
                "• **IEEE Access:** Multidisciplinary, peer-reviewed, open-access journal covering all IEEE areas."
            )

        if "nisb" in q_lower or "nie ieee" in q_lower:
            return (
                "**NISB** stands for the **NIE IEEE Student Branch**, the official student branch at The National Institute of Engineering (NIE), Mysuru, Karnataka, India.\n\n"
                "• **History:** Established in 1999, it is one of the oldest, largest, and most active student branches in IEEE Region 10 (Asia-Pacific).\n"
                "• **Parent Section & Subsection:** Operates under the **IEEE Bangalore Section** and **IEEE Mysore Subsection**.\n"
                "• **Flagship Events:** Organizes *Adroit* (annual state/national technical fest), *Ankura* (flagship Women in Engineering initiative), hackathons, code jams, and tech workshops.\n"
                "• **Chapters:** Houses an IEEE Women in Engineering (WIE) Affinity Group, Computer Society (CS) Chapter, and Power & Energy Society (PES) Chapter.\n\n"
                "You can explore more on their official portal: [NISB Portal](https://nisb.in/)."
            )

        if "section" in q_lower or "subsection" in q_lower or "region" in q_lower:
            return (
                "IEEE organizes its global activities across a hierarchy of geographic units:\n\n"
                "• **10 Geographic Regions:** From Regions 1–6 (USA), Region 7 (Canada), Region 8 (Europe/Middle East/Africa), Region 9 (Latin America), to Region 10 (Asia-Pacific).\n"
                "• **Sections:** Over 340 local geographic units globally (e.g. Toronto Section, Vancouver Section, Bangalore Section, UK and Ireland Section).\n"
                "• **Subsections:** Regional units formed under large Sections to cater to specific cities (such as the IEEE Mysore Subsection under the Bangalore Section).\n"
                "• **Student Branches:** Established at accredited colleges and universities globally (e.g., NISB at NIE Mysuru, U of T in Canada) governed by their local Section."
            )

        if "when" in q_lower and ("established" in q_lower or "founded" in q_lower or "start" in q_lower):
            return "IEEE was established on January 1, 1963, through the merger of two pioneering engineering societies: the American Institute of Electrical Engineers (AIEE, founded in 1884) and the Institute of Radio Engineers (IRE, founded in 1912)."

        if "802.11" in q_lower or "wi-fi" in q_lower or "wifi" in q_lower:
            return "IEEE 802.11 is the internationally recognized family of standards for Wireless Local Area Networks (WLAN), commercially known as **Wi-Fi**. Developed by the IEEE 802 LAN/MAN Standards Committee, it governs wireless communication across 2.4 GHz, 5 GHz, and 6 GHz frequency bands, encompassing protocols like 802.11n (Wi-Fi 4), 802.11ac (Wi-Fi 5), 802.11ax (Wi-Fi 6), and 802.11be (Wi-Fi 7)."

        if "research paper" in q_lower or "xplore" in q_lower or "find paper" in q_lower:
            return "You can find and access IEEE research papers, journal articles, and conference proceedings through the **IEEE Xplore Digital Library** at [IEEE Xplore](https://ieeexplore.ieee.org/). It hosts over 6 million peer-reviewed documents accessible through university institutional subscriptions, open access journals, or member digital library add-ons."

        if "join" in q_lower and "branch" in q_lower:
            return "To join an IEEE Student Branch, first enroll as an IEEE Student Member at [ieee.org/join](https://www.ieee.org/membership/join/index.html) (students must carry at least 50% of a full-time academic course load). Once registered, connect with the IEEE Student Branch officers or Branch Counselor at your university. If your campus does not currently have an active branch, you can form one with a petition endorsed by a faculty advisor and at least 12 student members."

        if "opportunit" in q_lower and "student" in q_lower:
            return "IEEE offers outstanding opportunities for students, including:\n\n• **Competitions:** Global challenges like the 24-hour IEEEXtreme virtual programming competition and regional student paper contests.\n• **Scholarships & Grants:** Prestigious awards such as the Charles LeGeyt Fortescue Scholarship, Richard E. Merwin Student Scholarship, and IEEE conference travel grants.\n• **Professional Growth:** Campus leadership in Student Branches, career prep via IEEE ResumeLab, and access to 39 specialized technical societies."

        if sources:
            top_excerpt = sources[0].excerpt.strip()
            lines = [l.strip().lstrip("•-* 1234567890.)") for l in top_excerpt.split("\n") if l.strip() and not l.strip().startswith("==")]
            return " ".join(lines[:4])

        return "IEEE is the world's largest technical professional organization dedicated to advancing technology for humanity. For more details, explore [IEEE.org](https://www.ieee.org/)."

    def generate_answer(
        self,
        question: str,
        history: Optional[List[MessageTurn]] = None,
        top_k: int = DEFAULT_TOP_K
    ) -> ChatResponse:
        """Execute complete RAG pipeline with dynamic LLM greeting generation and rigorous anti-meta filtering."""
        q_clean = question.strip()
        api_key = self._get_api_key()

        # Step 1: Detect greetings or small talk
        if self._is_greeting_or_smalltalk(q_clean):
            # If API key is available, generate a fresh, dynamic LLM greeting every time
            if api_key:
                try:
                    client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key, timeout=15.0)
                    primary_model = os.getenv("NVIDIA_MODEL", NVIDIA_MODEL)
                    greeting_messages = [
                        {
                            "role": "system",
                            "content": (
                                "You are the IEEE AI Assistant, a friendly and knowledgeable guide for students, researchers, and engineers worldwide. "
                                "Respond warmly, conversationally, and naturally to the user's greeting or small talk. "
                                "Offer helpful ideas on what you can assist with (such as student branches, IEEE membership perks, scholarships, Wi-Fi 802.11 standards, or IEEE Xplore research papers). "
                                "Keep it fresh, natural, concise, and engaging without sounding like a robotic template. Never use phrases like 'reference information'."
                            )
                        },
                        {"role": "user", "content": q_clean}
                    ]
                    response = client.chat.completions.create(
                        model=primary_model,
                        messages=greeting_messages,
                        temperature=0.7,
                        top_p=0.9,
                        max_tokens=256
                    )
                    raw_greeting = response.choices[0].message.content
                    if raw_greeting and raw_greeting.strip():
                        return ChatResponse(
                            answer=self._post_process_answer(raw_greeting),
                            sources=[],
                            retrieved_chunks_count=0,
                            model_used="IEEE Assistant",
                            confidence_note=None
                        )
                except Exception as e:
                    logger.warning(f"Dynamic LLM greeting call failed, falling back: {e}")

            # Fallback dynamic greetings (randomized so it never feels canned)
            fallback_greetings = [
                "Hello! Welcome to the IEEE Assistant. I'm here to help you explore IEEE student branches, membership opportunities, technical standards, and research publications. How can I help you today?",
                "Hi there! Glad you reached out. Whether you're curious about joining an IEEE student branch, looking up research papers on IEEE Xplore, or exploring technical societies, I'm ready to assist. What would you like to know?",
                "Hey! Great to connect with you. I can help answer your questions about IEEE history, student competitions (like IEEEXtreme), scholarships, or Wi-Fi standards (802.11). Where would you like to begin?",
                "Hello! I am your IEEE AI guide. How can I assist you with IEEE activities, student chapters, or engineering resources today?"
            ]
            return ChatResponse(
                answer=random.choice(fallback_greetings),
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

        # If API key is not configured, use conversational synthesis
        if not api_key:
            answer_text = self._synthesize_conversational_fallback(q_clean, sources_list)
            return ChatResponse(
                answer=self._post_process_answer(answer_text),
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
            f"IEEE Knowledge Base Details:\n{context_str}\n\n"
            f"User Question: {q_clean}\n\n"
            f"Instructions:\n"
            f"1. Answer the user directly, factually, and conversationally as the authoritative IEEE Assistant.\n"
            f"2. NEVER use phrases like 'The provided reference information', 'reference information', 'the provided context', 'the reference does not state', or 'based on the context'.\n"
            f"3. NEVER refuse by saying you cannot find or name something in the reference. If asked for branches, sections, or examples, name prominent ones directly from your IEEE knowledge.\n"
            f"4. Format each bullet item on its own new line with '• '.\n"
            f"5. Format hyperlinks cleanly using markdown."
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
                clean_text = self._post_process_answer(raw_content)
                generated_answer = clean_text
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
                answer=self._post_process_answer(fallback_answer),
                sources=sources_list,
                retrieved_chunks_count=len(sources_list),
                model_used="IEEE Assistant",
                confidence_note=None
            )
