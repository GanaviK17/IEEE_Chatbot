import os
import sys
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.rag_service import RAGService, MessageIntent
from app.models import MessageTurn

def test_intent_classification():
    print("--> Testing Intent Classification across arbitrary inputs...")
    rag = RAGService()

    # 1. Casual greetings & small talk
    assert rag.classify_intent("hi") == MessageIntent.CASUAL
    assert rag.classify_intent("Hello!") == MessageIntent.CASUAL
    assert rag.classify_intent("Good morning") == MessageIntent.CASUAL
    assert rag.classify_intent("How are you?") == MessageIntent.CASUAL
    assert rag.classify_intent("thanks a lot") == MessageIntent.CASUAL
    assert rag.classify_intent("bye, see you!") == MessageIntent.CASUAL

    # 2. Acknowledgements
    assert rag.classify_intent("ok") == MessageIntent.ACKNOWLEDGEMENT
    assert rag.classify_intent("okay") == MessageIntent.ACKNOWLEDGEMENT
    assert rag.classify_intent("got it") == MessageIntent.ACKNOWLEDGEMENT
    assert rag.classify_intent("cool") == MessageIntent.ACKNOWLEDGEMENT
    assert rag.classify_intent("understood") == MessageIntent.ACKNOWLEDGEMENT
    assert rag.classify_intent("makes sense") == MessageIntent.ACKNOWLEDGEMENT

    # 3. Bot capabilities / identity
    assert rag.classify_intent("who are you?") == MessageIntent.BOT_CAPABILITIES
    assert rag.classify_intent("what can you do?") == MessageIntent.BOT_CAPABILITIES
    assert rag.classify_intent("how can you help me?") == MessageIntent.BOT_CAPABILITIES

    # 4. Unclear / gibberish
    assert rag.classify_intent("asdfghjk") == MessageIntent.UNCLEAR
    assert rag.classify_intent("???") == MessageIntent.UNCLEAR
    assert rag.classify_intent("...") == MessageIntent.UNCLEAR
    assert rag.classify_intent("zzzzzzz") == MessageIntent.UNCLEAR

    # 5. Off-topic questions
    assert rag.classify_intent("What is the recipe for baking chocolate chip cookies?") == MessageIntent.OFF_TOPIC
    assert rag.classify_intent("Who won the World Cup?") == MessageIntent.OFF_TOPIC
    assert rag.classify_intent("What's the weather in Paris?") == MessageIntent.OFF_TOPIC

    # 6. Compound queries starting with greeting should be classified as IEEE_QUERY
    assert rag.classify_intent("Hello, what is IEEE 802.11?") == MessageIntent.IEEE_QUERY
    assert rag.classify_intent("Hi, how do I join an IEEE student branch?") == MessageIntent.IEEE_QUERY

    # 7. Follow-up detection with history
    history = [
        MessageTurn(role="user", content="Tell me about IEEE Canada."),
        MessageTurn(role="assistant", content="IEEE Canada constitutes Region 7.")
    ]
    assert rag.classify_intent("tell me more", history) == MessageIntent.FOLLOW_UP
    assert rag.classify_intent("What about its student branches?", history) == MessageIntent.FOLLOW_UP
    assert rag.classify_intent("why?", history) == MessageIntent.FOLLOW_UP

    # 8. Core IEEE queries
    assert rag.classify_intent("What is the full form of IEEE?") == MessageIntent.IEEE_QUERY
    assert rag.classify_intent("What opportunities does IEEE offer students?") == MessageIntent.IEEE_QUERY
    assert rag.classify_intent("What is NISB?") == MessageIntent.IEEE_QUERY

    print("SUCCESS: Intent classification passed for all test categories.")

def test_query_contextualization():
    print("--> Testing Query Contextualization for follow-ups...")
    rag = RAGService()

    history = [
        MessageTurn(role="user", content="Tell me about IEEE Canada."),
        MessageTurn(role="assistant", content="IEEE Canada represents Region 7, covering 20+ sections and prominent student branches.")
    ]

    contextualized = rag.contextualize_query("What are some student branches there?", history)
    print(f"Contextualized query: '{contextualized}'")
    assert "Canada" in contextualized or "Region 7" in contextualized
    print("SUCCESS: Contextualization successfully injected prior turn context.")

def test_offline_fallback_differentiation():
    print("--> Testing Offline Fallback Differentiation and Transparency...")
    rag = RAGService()

    # Test distinct inputs to verify answers are NOT identical
    res_casual = rag._synthesize_offline_fallback("hi", MessageIntent.CASUAL, [])
    res_ack = rag._synthesize_offline_fallback("ok", MessageIntent.ACKNOWLEDGEMENT, [])
    res_bot = rag._synthesize_offline_fallback("who are you?", MessageIntent.BOT_CAPABILITIES, [])
    res_unclear = rag._synthesize_offline_fallback("???", MessageIntent.UNCLEAR, [])
    res_offtopic = rag._synthesize_offline_fallback("recipe for bread", MessageIntent.OFF_TOPIC, [])
    res_unknown = rag._synthesize_offline_fallback("What is the population of Neptune?", MessageIntent.IEEE_QUERY, [])

    answers = [
        res_casual.answer,
        res_ack.answer,
        res_bot.answer,
        res_unclear.answer,
        res_offtopic.answer,
        res_unknown.answer
    ]

    # Verify all answers are pairwise distinct (no identical canned responses)
    assert len(set(answers)) == len(answers), "Fallback generated identical responses for distinct inputs!"

    # Verify fallback mode transparency
    assert "Offline" in res_casual.model_used or "Offline" in (res_casual.confidence_note or "")
    assert "Offline" in res_unknown.model_used or "unavailable" in (res_unknown.confidence_note or "")
    print("SUCCESS: Fallback mode is differentiated, transparent, and never returns identical boilerplate.")

def test_live_rag_quality():
    print("--> Testing Live RAG Service (Intent handling, conciseness, grounding)...")
    rag = RAGService()

    # 1. Unclear input returns clarifying question without sources
    res_unclear = rag.generate_answer("asdfghjk")
    assert res_unclear.retrieved_chunks_count == 0
    assert "clarify" in res_unclear.answer.lower()
    print("Unclear response:", res_unclear.answer)

    # 2. Off-topic query politely declines without hallucinating IEEE branches
    res_offtopic = rag.generate_answer("What is the recipe for baking chocolate chip cookies?")
    assert res_offtopic.retrieved_chunks_count == 0
    assert "specialize in ieee" in res_offtopic.answer.lower() or "culinary" in res_offtopic.answer.lower() or "baking" in res_offtopic.answer.lower()
    assert "toronto" not in res_offtopic.answer.lower()
    print("Off-topic response:", res_offtopic.answer)

    # 3. Casual greeting skips retrieval and responds concisely
    res_casual = rag.generate_answer("hi there")
    assert res_casual.retrieved_chunks_count == 0
    assert len(res_casual.sources) == 0
    print("Casual response:", res_casual.answer)

    # 4. Acknowledgement skips retrieval and responds concisely
    res_ack = rag.generate_answer("ok, got it")
    assert res_ack.retrieved_chunks_count == 0
    print("Acknowledgement response:", res_ack.answer)

    # 5. Core IEEE question retrieves sources and grounds answer
    res_ieee = rag.generate_answer("What is IEEE 802.11?")
    assert res_ieee.retrieved_chunks_count > 0
    assert len(res_ieee.sources) > 0
    assert "wi-fi" in res_ieee.answer.lower() or "wireless" in res_ieee.answer.lower()
    print("IEEE 802.11 response:", res_ieee.answer[:160], "...")

    # 6. Follow-up maintains continuity
    history = [
        MessageTurn(role="user", content="Tell me about IEEE Canada."),
        MessageTurn(role="assistant", content="IEEE Canada is Region 7, encompassing numerous student branches including Toronto, UBC, and Waterloo.")
    ]
    res_followup = rag.generate_answer("Can you tell me more about its student branches?", history)
    assert res_followup.retrieved_chunks_count > 0
    print("Follow-up response:", res_followup.answer[:160], "...")

    print("SUCCESS: All live RAG conversational quality tests passed.")

if __name__ == "__main__":
    test_intent_classification()
    test_query_contextualization()
    test_offline_fallback_differentiation()
    test_live_rag_quality()
    print("\n=======================================================")
    print("ALL CONVERSATIONAL RAG QUALITY TESTS PASSED PERFECTLY!")
    print("=======================================================")
