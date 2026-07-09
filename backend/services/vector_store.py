"""
Wraps ChromaDB (persistent local vector store) and a sentence-transformers
embedding model. This is the retrieval half of RAG: store document chunks
as vectors, then fetch the most semantically similar ones for a query.

Also implements hybrid search: semantic (vector) search alone can miss exact
terms like names, IDs, or acronyms, since embeddings capture meaning rather
than exact tokens. BM25 (a classic keyword-ranking algorithm) is combined
with vector search via Reciprocal Rank Fusion (RRF), so results that rank
highly on EITHER signal get boosted, giving more robust retrieval than
either method alone.
"""
import os
import re
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi

TOP_K = int(os.getenv("TOP_K", 4))

# all-MiniLM-L6-v2 is small, fast, and free — good enough for demo-scale RAG
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), "..", "chroma_db"))


def get_collection(collection_name: str = "documents"):
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
    )


def add_chunks(doc_id: str, filename: str, chunks: list):
    """Embed and store chunks for a given document."""
    collection = get_collection()
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {"doc_id": doc_id, "filename": filename, "page": c["page"] or 0}
        for c in chunks
    ]
    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


def query_similar_chunks(query: str, top_k: int = TOP_K):
    """Retrieve the most semantically similar chunks to the query (vector search only)."""
    collection = get_collection()
    if collection.count() == 0:
        return []

    results = collection.query(query_texts=[query], n_results=min(top_k, collection.count()))

    hits = []
    for doc, meta, dist, chunk_id in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0], results["ids"][0]
    ):
        hits.append({
            "id": chunk_id,
            "text": doc,
            "filename": meta.get("filename"),
            "page": meta.get("page"),
            "score": 1 - dist,  # convert distance to a similarity-like score
        })
    return hits


def _tokenize(text: str):
    """Simple lowercase word tokenizer for BM25 (no external NLP deps needed)."""
    return re.findall(r"\w+", text.lower())


def _build_bm25_index():
    """
    Build a BM25 index over every chunk currently stored in ChromaDB.
    Rebuilt per-query rather than cached, since document sets in a demo app
    are small (hundreds of chunks) and correctness after uploads/deletes
    matters more than shaving milliseconds off this step.
    """
    collection = get_collection()
    if collection.count() == 0:
        return None, []

    all_items = collection.get()
    corpus = []
    for chunk_id, doc, meta in zip(all_items["ids"], all_items["documents"], all_items["metadatas"]):
        corpus.append({"id": chunk_id, "text": doc, "filename": meta.get("filename"), "page": meta.get("page")})

    tokenized_corpus = [_tokenize(c["text"]) for c in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    return bm25, corpus


def hybrid_search(query: str, top_k: int = TOP_K, vector_weight: float = 0.6):
    """
    Combine vector (semantic) search and BM25 (keyword) search using
    Reciprocal Rank Fusion: each chunk's final score is based on its RANK
    in each method's results, not raw scores (which aren't directly
    comparable between cosine similarity and BM25). Chunks that appear in
    both lists get reinforced.
    """
    collection = get_collection()
    if collection.count() == 0:
        return []

    fetch_k = min(max(top_k * 4, 10), collection.count())

    # Semantic side
    vector_hits = query_similar_chunks(query, top_k=fetch_k)
    vector_ranks = {hit["id"]: rank for rank, hit in enumerate(vector_hits)}
    hit_lookup = {hit["id"]: hit for hit in vector_hits}

    # Keyword side
    bm25, corpus = _build_bm25_index()
    bm25_ranks = {}
    if bm25 is not None:
        scores = bm25.get_scores(_tokenize(query))
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:fetch_k]
        for rank, idx in enumerate(ranked_indices):
            item = corpus[idx]
            bm25_ranks[item["id"]] = rank
            if item["id"] not in hit_lookup:
                hit_lookup[item["id"]] = {
                    "id": item["id"], "text": item["text"],
                    "filename": item["filename"], "page": item["page"], "score": None,
                }

    # Reciprocal Rank Fusion: score = weight / (k + rank), k=60 is a standard RRF constant
    k = 60
    fused_scores = {}
    all_ids = set(vector_ranks) | set(bm25_ranks)
    for chunk_id in all_ids:
        score = 0.0
        if chunk_id in vector_ranks:
            score += vector_weight * (1.0 / (k + vector_ranks[chunk_id]))
        if chunk_id in bm25_ranks:
            score += (1 - vector_weight) * (1.0 / (k + bm25_ranks[chunk_id]))
        fused_scores[chunk_id] = score

    ranked = sorted(all_ids, key=lambda cid: fused_scores[cid], reverse=True)[:top_k]

    results = []
    for chunk_id in ranked:
        hit = hit_lookup[chunk_id]
        results.append({
            "text": hit["text"],
            "filename": hit["filename"],
            "page": hit["page"],
            "score": round(fused_scores[chunk_id], 4),
        })
    return results


def list_documents():
    """Return distinct filenames currently indexed."""
    collection = get_collection()
    if collection.count() == 0:
        return []
    all_items = collection.get()
    seen = {}
    for meta in all_items["metadatas"]:
        seen[meta["filename"]] = meta.get("doc_id")
    return [{"filename": f, "doc_id": d} for f, d in seen.items()]


def delete_document(doc_id: str):
    collection = get_collection()
    collection.delete(where={"doc_id": doc_id})
