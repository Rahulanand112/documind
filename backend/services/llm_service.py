"""
Handles the generation half of RAG: takes the user's question plus the
retrieved chunks, builds a grounded prompt, and calls Groq's free/fast
LLM API to produce a cited answer.

Also handles multi-turn conversation support: a follow-up question like
"what about his projects?" makes no sense to a retrieval system in
isolation, since it has no idea what "his" refers to. Before retrieval
runs, we ask the LLM to rewrite the question into a standalone form using
the recent conversation history — this is the standard "condense
question" pattern used in conversational RAG systems.
"""
import os
from groq import Groq

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")
        _client = Groq(api_key=api_key)
    return _client


def format_history(history: list, max_turns: int = 4) -> str:
    """Format the last few turns of conversation for prompting."""
    if not history:
        return ""
    recent = history[-max_turns:]
    lines = []
    for turn in recent:
        role = "User" if turn.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {turn.get('text', '')}")
    return "\n".join(lines)


def contextualize_question(question: str, history: list) -> str:
    """
    Rewrite a follow-up question into a standalone question using
    conversation history, so retrieval can find the right chunks even
    when the question relies on earlier context (e.g. "what about his
    projects?" -> "What projects does Rahul Anand have?").
    If there's no history yet, the question is already standalone.
    """
    if not history:
        return question

    history_text = format_history(history)
    if not history_text:
        return question

    client = get_client()
    prompt = (
        "Given the conversation history and a follow-up question, rewrite the "
        "follow-up into a standalone question that contains all necessary context. "
        "If the follow-up is already standalone, return it unchanged. "
        "Return ONLY the rewritten question, nothing else.\n\n"
        f"Conversation history:\n{history_text}\n\n"
        f"Follow-up question: {question}\n\n"
        "Standalone question:"
    )

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=100,
        )
        rewritten = completion.choices[0].message.content.strip()
        return rewritten if rewritten else question
    except Exception:
        # If rewriting fails for any reason, fall back to the original question
        # rather than blocking the whole request.
        return question


def build_context(chunks: list) -> str:
    """Format retrieved chunks into a labeled context block for the prompt."""
    parts = []
    for i, c in enumerate(chunks, start=1):
        page_info = f", page {c['page']}" if c.get("page") else ""
        parts.append(f"[Source {i}: {c['filename']}{page_info}]\n{c['text']}")
    return "\n\n".join(parts)


def generate_answer(question: str, chunks: list, history: list = None) -> dict:
    """
    Generate a grounded answer using retrieved chunks as context, aware of
    recent conversation history so tone and pronouns stay consistent across
    turns. Returns the answer text plus the sources used, so the frontend
    can show citations.
    """
    if not chunks:
        return {
            "answer": "I couldn't find anything relevant in the uploaded documents to answer that.",
            "sources": [],
        }

    context = build_context(chunks)
    history_text = format_history(history or [])

    system_prompt = (
        "You are a helpful assistant that answers questions using ONLY the provided "
        "context from the user's documents. If the answer isn't in the context, say so "
        "clearly instead of guessing. When you use information from a source, mention "
        "which source number it came from, e.g. (Source 2). Maintain continuity with "
        "the prior conversation when relevant."
    )

    history_block = f"Previous conversation:\n{history_text}\n\n" if history_text else ""
    user_prompt = f"{history_block}Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"

    client = get_client()
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=600,
    )

    answer = completion.choices[0].message.content

    sources = [
        {"filename": c["filename"], "page": c["page"], "score": round(c["score"], 3)}
        for c in chunks
    ]

    return {"answer": answer, "sources": sources}
