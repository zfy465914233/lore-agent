# System Evaluation Cases

Date: 2026-04-02

This document outlines the evaluation test cases designed to assess the effectiveness of the hybrid RAG system (local knowledge + web research). These cases test routing heuristics, retrieval quality, and fallback behaviors.

## Categories of Evaluation

1. **Local-Led (Definitions & Theorem)**
   - Queries directly targeting established local knowledge.
   - *Expected Behavior*: Routes to `local-led`, purely retrieves from local index, no web fallback needed, high precision.

2. **Web-Led (Freshness & SOTA)**
   - Queries about recent events, latest releases, or state-of-the-art.
   - *Expected Behavior*: Routes to `web-led`, triggers research harness, merges web evidence with any available local context.

3. **Context-Led (Code & Debugging)**
   - Queries about bugs, scripts, or specific implementations.
   - *Expected Behavior*: Routes to `context-led`.

4. **Mixed (Complex Syntheses)**
   - Queries requiring broad knowledge or crossing domains.
   - *Expected Behavior*: Routes to `mixed`, dynamically uses both local and web evidence if needed.

## Test Cases

### Case 1: Local Knowledge Retrieval (Definition)
- **Query**: "What is a Markov chain?"
- **Expected Route**: `local-led`
- **Expected Primary Evidence**: `markov-chain-definition.md`

### Case 2: Local Knowledge Retrieval (Derivation)
- **Query**: "Show me the derivation for the stationary distribution of a Markov chain."
- **Expected Route**: `local-led`
- **Expected Primary Evidence**: `stationary-distribution-derivation.md`

### Case 3: Freshness / SOTA (Web-Led)
- **Query**: "What is the latest state-of-the-art method for quantization-aware training in 2026?"
- **Expected Route**: `web-led`
- **Expected Behavior**: Orchestrator should trigger the research harness (`fake_research_harness.py` for testing) and return web evidence.

### Case 4: Code / Context-Led
- **Query**: "Why is my local_index.py script throwing an error?"
- **Expected Route**: `context-led`

### Case 5: Mixed / Broad Synthesis
- **Query**: "Compare Markov chains with other stochastic processes."
- **Expected Route**: `mixed`
- **Expected Behavior**: Retrieves local Markov chain definition, but also fetches web evidence for broader context.

### Case 6: Local Fallback on Missing Web Data
- **Query**: "latest updates on quantum phase estimation bounds"
- **Expected Route**: `web-led`
- **Expected Behavior**: If web harness fails or returns empty, the system should degrade gracefully and return the local `qpe-error-bound-derivation.md` card.
