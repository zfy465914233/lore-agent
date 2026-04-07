# V3 Improvements Review

Date: 2026-04-07

Scope:
- Reviewed the current uncommitted V3 improvements in `lore-agent`
- Focused on behavior regressions, integration risks, and missing test coverage

## Findings

### P1: `depth` no longer changes discovery breadth

File:
- [research_harness.py](/Users/zhoufangyi/code/harnessengineering/lore-agent/scripts/research_harness.py#L164)

What changed:
- `run_discovery()` now calls `run_search_pipeline()` with only the raw `query`
- `formulate_queries()` is still present, but its expanded variants are no longer used

Why this matters:
- `quick` / `medium` / `deep` now differ only by truncation count
- medium/deep no longer get broader recall from query expansion such as:
  - `latest`
  - current year
  - `comparison`
  - `benchmark`
  - `综述`

Impact:
- silent recall regression for medium/deep discovery
- likely weaker web evidence quality on harder or freshness-sensitive queries

Recommendation:
- either restore multi-query expansion before calling the search pipeline
- or make the pipeline explicitly accept multiple query variants and merge provider results across them

### P1: retry loop can only refine once, regardless of `max_retries`

File:
- [agent.py](/Users/zhoufangyi/code/harnessengineering/lore-agent/scripts/agent.py#L375)

What changed:
- when evidence is insufficient, the agent gathers once with a refined query
- it then jumps directly to `SYNTHESIZE`
- it does not return to `RESEARCH` to re-check sufficiency

Why this matters:
- `max_retries > 1` is effectively ignored
- refined evidence is never re-evaluated before synthesis

Impact:
- retry budget does not behave as configured
- insufficient evidence may still flow into synthesis even when more retries were intended

Recommendation:
- after refining, loop back into `RESEARCH`
- increment retry count and re-run sufficiency checks until:
  - evidence becomes sufficient, or
  - `max_retries` is exhausted

### P2: `Curator.distill()` fallback path no longer matches the distill CLI

File:
- [agent.py](/Users/zhoufangyi/code/harnessengineering/lore-agent/scripts/agent.py#L256)

What changed:
- fallback subprocess invocation still runs:
  - `distill_knowledge.py -`
  - JSON via stdin
- current `distill_knowledge.py` now requires:
  - `--answer-context <path>`
  - `--output <path>`

Why this matters:
- if the in-process import path fails, distillation will fail even for valid input

Impact:
- hidden fallback path is broken
- error only appears under import/path issues, so it is easy to miss in normal testing

Recommendation:
- update the fallback to match the current CLI contract
- or remove the fallback entirely if in-process import is now the only supported path

## Testing Gap

File:
- [test_incremental_index.py](/Users/zhoufangyi/code/harnessengineering/lore-agent/tests/test_incremental_index.py)

Observed gap:
- new incremental index tests cover:
  - initial build
  - unchanged reuse
  - new file detection
  - corrupt/missing manifest fallback
- they do not cover:
  - modifying an existing card
  - deleting an existing card

Why this matters:
- the implementation notes claim changed and deleted cards are handled
- but those two behaviors are not currently locked by tests

Recommendation:
- add a test that edits a card body/frontmatter and verifies the indexed document updates
- add a test that deletes a card and verifies it is removed from the rebuilt index

## Summary

Overall direction is good:
- provider abstraction is cleaner
- host-search injection boundary is clearer
- incremental indexing and input validation are useful additions

The main issues are not architectural; they are execution regressions:
- search depth semantics weakened
- retry semantics weakened
- one fallback path is stale

I would fix the two P1 issues before merging, then add the missing incremental-index tests to lock the new behavior down.
