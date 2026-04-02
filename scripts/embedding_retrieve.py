"""Embedding-based retrieval for local knowledge.

Uses an OpenAI-compatible embeddings API to compute query and document
embeddings, then retrieves by cosine similarity. Falls back gracefully
when no API is available.

Configuration (environment variables):
  LLM_API_URL  – base URL for OpenAI-compatible API. Default: https://api.openai.com/v1
  LLM_API_KEY  – API key.
  EMBEDDING_MODEL – model name. Default: text-embedding-3-small
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LLM_API_URL = os.environ.get("LLM_API_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_TIMEOUT = int(os.environ.get("EMBEDDING_TIMEOUT", "30"))


def _embed_texts(texts: list[str], model: str = EMBEDDING_MODEL) -> list[list[float]]:
    """Call the embeddings API and return embedding vectors."""
    url = LLM_API_URL.rstrip("/") + "/embeddings"
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    body = json.dumps({"model": model, "input": texts}).encode("utf-8")
    req = Request(url, data=body, headers=headers, method="POST")

    try:
        with urlopen(req, timeout=EMBEDDING_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError) as exc:
        raise RuntimeError(f"Embedding API request failed: {exc}") from exc

    embeddings = []
    for item in sorted(data.get("data", []), key=lambda x: x.get("index", 0)):
        embeddings.append(item["embedding"])
    return embeddings


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def build_embedding_index(documents: list[dict], model: str = EMBEDDING_MODEL) -> dict[str, Any]:
    """Compute embeddings for all documents and return an embedding index.

    Each document's ``search_text`` field is used as the embedding input.
    """
    texts = [str(doc.get("search_text", "")) for doc in documents]
    if not texts:
        return {"model": model, "embeddings": [], "doc_ids": []}

    # Batch embed (APIs typically handle batches)
    batch_size = 20
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        # Filter empty texts
        non_empty = [(j, t) for j, t in enumerate(batch) if t.strip()]
        if not non_empty:
            all_embeddings.extend([[] for _ in batch])
            continue
        indices, valid_texts = zip(*non_empty)
        try:
            batch_embeddings = _embed_texts(list(valid_texts), model)
        except RuntimeError:
            all_embeddings.extend([[] for _ in batch])
            continue
        result = [[] for _ in batch]
        for idx, emb in zip(indices, batch_embeddings):
            result[idx] = emb
        all_embeddings.extend(result)

    return {
        "model": model,
        "doc_ids": [str(doc.get("doc_id", "")) for doc in documents],
        "embeddings": all_embeddings,
    }


def embed_query(query: str, model: str = EMBEDDING_MODEL) -> list[float]:
    """Compute embedding for a single query string."""
    embeddings = _embed_texts([query], model)
    return embeddings[0] if embeddings else []


def retrieve_by_embedding(
    query: str,
    embedding_index: dict[str, Any],
    k: int = 5,
) -> list[tuple[str, float]]:
    """Retrieve top-k documents by embedding similarity.

    Returns list of (doc_id, similarity_score).
    """
    model = embedding_index.get("model", EMBEDDING_MODEL)
    query_embedding = embed_query(query, model)
    if not query_embedding:
        return []

    doc_ids = embedding_index.get("doc_ids", [])
    embeddings = embedding_index.get("embeddings", [])

    scores: list[tuple[str, float]] = []
    for i, (doc_id, doc_emb) in enumerate(zip(doc_ids, embeddings)):
        if not doc_emb:
            continue
        sim = cosine_similarity(query_embedding, doc_emb)
        if sim > 0:
            scores.append((doc_id, sim))

    scores.sort(key=lambda x: -x[1])
    return scores[:k]
