# Phase 3: Retrieval Upgrade — Changelog

Date: 2026-04-02

## What Changed

### New: `scripts/bm25.py`

Pure-Python Okapi BM25 implementation with no external dependencies.

- Proper term-frequency weighting with saturation (k1=1.5)
- Document-length normalization (b=0.75)
- IDF computation with smoothing
- Replaces the previous simple TF scoring

### New: `scripts/embedding_retrieve.py`

Optional embedding-based semantic retrieval layer.

- Uses OpenAI-compatible embeddings API (same env vars as synthesize_answer.py)
- Cosine similarity matching
- Graceful fallback when API is unavailable
- Batch embedding support for index building

Config: `LLM_API_URL`, `LLM_API_KEY`, `EMBEDDING_MODEL` (default: text-embedding-3-small)

### Updated: `scripts/local_retrieve.py`

Completely rewritten to support hybrid retrieval:

1. **BM25-only mode** (default): pure lexical retrieval via BM25
2. **Hybrid mode**: when `--embedding-index` is provided, combines BM25 + embedding scores via weighted blending
3. `--bm25-weight` parameter (default 0.6) controls the blend ratio
4. Fully backward compatible — `retrieve()` function signature unchanged

### New: `tests/test_bm25_retrieval.py`

9 tests covering:
- BM25 unit tests (ranking, empty query, empty corpus)
- CLI integration (retrieval correctness for known queries)
- Graceful fallback when embedding index is missing
- Score quality (definition ranking, monotonic score decrease)

## Architecture

```
Query → BM25 scoring ──────────────┐
                                    ├→ Normalize → Weighted blend → Top-K results
Query → Embedding similarity ──────┘

(Embedding path is optional; BM25 works standalone)
```

## Next Step (Phase 4)

Agent control loop formalization — define Router/Researcher/Synthesizer/Curator roles.
