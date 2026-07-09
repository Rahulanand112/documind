from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from services.vector_store import hybrid_search
from services.llm_service import generate_answer, contextualize_question

router = APIRouter()


class HistoryTurn(BaseModel):
    role: str  # "user" or "assistant"
    text: str


class QueryRequest(BaseModel):
    question: str
    top_k: int = 4
    history: Optional[List[HistoryTurn]] = None


@router.post("/query")
async def query_documents(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    history = [turn.dict() for turn in request.history] if request.history else []

    try:
        # Rewrite follow-up questions into standalone ones using conversation
        # history, so retrieval works correctly even for pronouns/references
        # to earlier turns (e.g. "what about his projects?").
        standalone_question = contextualize_question(request.question, history)

        # Hybrid search: combines semantic (vector) search with keyword (BM25)
        # search via reciprocal rank fusion, catching both meaning-based and
        # exact-term matches.
        chunks = hybrid_search(standalone_question, top_k=request.top_k)

        result = generate_answer(request.question, chunks, history=history)
        result["standalone_question"] = standalone_question
        return result
    except RuntimeError as e:
        # Missing API key or similar config issue
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")
