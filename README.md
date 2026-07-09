# DocuMind — RAG-based Document Q\&A Assistant

Upload documents (PDF/TXT) and ask questions about them in natural language.
Answers are generated using Retrieval-Augmented Generation (RAG): relevant
chunks are retrieved via semantic search over a vector database, then passed
to an LLM to produce a grounded, cited answer — instead of the model guessing
from memory.

## How it works

1. **Ingest** — uploaded files are parsed and split into overlapping text chunks.
2. **Embed** — each chunk is converted into a vector using `sentence-transformers` (runs locally, free).
3. **Store** — vectors are persisted in ChromaDB, a local vector database. Chunk text is also indexed for keyword search (BM25).
4. **Contextualize** — if there's prior conversation history, the LLM rewrites follow-up questions (e.g. "what about his projects?") into standalone questions before retrieval runs.
5. **Retrieve (hybrid search)** — the standalone question is matched against stored chunks two ways: semantic similarity (vector search) and exact keyword overlap (BM25). Results are merged with Reciprocal Rank Fusion, so both meaning-based and exact-term matches surface.
6. **Generate** — the top matching chunks, plus recent conversation history, are passed to Groq's free LLM API (Llama 3), which produces an answer with source citations.



**## Demo**



**\*\*Answering questions with cited sources:\*\***



!\[Education Q\&A with citations](screenshots/education-demo.png)



\*\*Multi-turn conversation memory (follow-up question "he" correctly resolves to the person from the prior answer):\*\*



!\[Conversation memory demo](screenshots/conversation-memory-demo.png)

### Why hybrid search instead of just vector search?

Pure vector search can miss exact terms — names, IDs, acronyms — because embeddings capture semantic meaning, not exact tokens. BM25 (a classic keyword-ranking algorithm) catches those exact matches. Combining both via Reciprocal Rank Fusion gives more robust retrieval than either alone, which is why production RAG systems rarely use vector search in isolation.

### Why conversation memory matters

Without it, a follow-up like "what about his projects?" would fail — the retrieval step has no idea what "his" refers to, since each question is otherwise treated in isolation. The "condense question" pattern used here rewrites the follow-up into a standalone form using recent history, so multi-turn conversations actually work.

## Tech stack

* **Backend:** FastAPI (Python), ChromaDB, sentence-transformers, Groq API
* **Frontend:** React (Vite)
* **Concepts demonstrated:** vector embeddings, semantic search, prompt engineering, REST API design, RAG architecture, file processing

## Local setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
# Add your free Groq API key to .env (get one at https://console.groq.com/keys)
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Visit `http://localhost:5173`.

## Deployment (free tier)

* **Backend:** Deploy to [Render](https://render.com) (free web service) — set `GROQ\_API\_KEY` as an environment variable in the dashboard.
* **Frontend:** Deploy to [Vercel](https://vercel.com) or [Netlify](https://netlify.com) — set `VITE\_API\_BASE\_URL` to your deployed Render backend URL.

## Project structure

```
documind/
├── backend/
│   ├── main.py                  # FastAPI app entrypoint
│   ├── routes/
│   │   ├── documents.py         # upload / list / delete endpoints
│   │   └── chat.py              # query endpoint
│   ├── services/
│   │   ├── document\_processor.py # text extraction + chunking
│   │   ├── vector\_store.py       # ChromaDB embedding + retrieval
│   │   └── llm\_service.py        # Groq prompt construction + generation
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── api.js
    │   └── components/
    │       ├── Sidebar.jsx
    │       └── ChatWindow.jsx
    └── package.json
```

## Resume bullet points (for reference)

* Built a full-stack RAG (Retrieval-Augmented Generation) application enabling multi-turn, natural-language Q\&A over user-uploaded documents, with cited sources.
* Implemented hybrid search combining vector similarity (sentence-transformer embeddings + ChromaDB) with BM25 keyword ranking, merged via Reciprocal Rank Fusion, improving retrieval robustness over semantic search alone.
* Designed a conversational query-rewriting step ("condense question" pattern) so follow-up questions resolve correctly using prior conversation context.
* Engineered a REST API (FastAPI) handling file ingestion, chunking, dual-index storage (vector + keyword), and LLM-based answer generation.
* Integrated Groq's LLM API with custom prompt engineering to ground responses strictly in retrieved context, reducing hallucination.

## Notes

* Free Groq API tier has rate limits; fine for demos and interviews.
* ChromaDB here is used in local/persistent mode — for production scale, consider a managed vector DB (Pinecone, Weaviate, or pgvector).

