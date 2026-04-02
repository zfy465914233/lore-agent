# Lore Agent Roadmap

## Evidence Completeness Evaluation

**Status**: Open

Currently the system lacks an explicit completeness score for retrieval and answer quality.

### What exists
- `uncertainty_notes` in answer context (warns when no direct evidence found)
- `direct_support_count` in pipeline output (raw count of supporting evidence)
- `missing_evidence` field in answer schema (LLM can optionally fill)
- `min_citations_rate` in eval (binary: met or not met)

### What's missing
- **Retrieval coverage score** (0-1): based on result count + BM25 scores + whether expected evidence was hit
- **Evidence strength classification**: strong support (direct citation) / weak (indirect inference) / gap (missing)
- **Confidence score**: an explicit 0-1 score attached to answer context telling the user how complete the answer is
- **Gap hints**: "to improve this answer, add knowledge about X, Y, Z"

### Possible approach
1. In `build_answer_context.py`, compute a coverage score from BM25 top-k scores vs a calibrated baseline
2. Classify each citation as strong/weak based on score percentile
3. Output a `confidence` field alongside `uncertainty_notes`
4. Use the answer schema's `missing_evidence` field to generate actionable gap hints
