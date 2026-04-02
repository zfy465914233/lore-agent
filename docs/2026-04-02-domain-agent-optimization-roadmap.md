# Domain Agent Optimization Roadmap

Date: 2026-04-02

## 1. Goal Definition

The core goal of this project is not just to build a lightweight RAG pipeline, but to build a strong domain-enhanced agent:

- The agent should answer specialized-domain questions better than a general-purpose model alone.
- The agent should know when local knowledge is sufficient and when external search is required.
- The agent should continuously update and improve its local knowledge base from high-value interactions.
- The agent should become more reliable over time through retrieval, evidence handling, evaluation, and knowledge curation.

In other words, the project should be treated as an **agent system with a knowledge improvement loop**, not only as a collection of retrieval scripts.

## 2. Current System Positioning

The current repository already contains a useful bootstrap foundation:

- local knowledge cards under `knowledge/`
- local indexing via `scripts/local_index.py`
- local retrieval via `scripts/local_retrieve.py`
- routing/orchestration via `scripts/orchestrate_research.py`
- web evidence collection via `scripts/research_harness.py`
- answer-context assembly via `scripts/build_answer_context.py`
- knowledge distillation and promotion via `scripts/distill_knowledge.py` and `scripts/promote_draft.py`

This means the project already supports an early closed loop:

1. retrieve local knowledge
2. optionally gather web evidence
3. assemble structured answer context
4. distill useful outputs
5. promote distilled outputs back into local knowledge

This is a strong start. However, from the perspective of the final goal, the system is still closer to a **retrieval-and-knowledge pipeline** than a full **agent architecture**.

## 3. Main Gap

The main gap is that the system does not yet fully behave like an autonomous, domain-aware agent with explicit control over:

- tool selection
- evidence sufficiency
- iterative search
- confidence management
- knowledge governance
- continuous improvement measurement

At present, the pipeline can produce evidence-backed context, but it still needs stronger agent-level reasoning and system boundaries to answer the central question:

**“Does the system actually become better over time in the target domain?”**

## 4. Optimization Priorities

### 4.1 Upgrade From Pipeline Thinking to Agent Thinking

The first optimization is conceptual and architectural.

The current system has the pieces of an agent, but not yet the explicit role boundaries and control loop that make it robust. The project should be reframed around agent responsibilities instead of only script stages.

Recommended agent roles:

- `Router`
  - decides whether the question should be handled by local knowledge, web evidence, mixed evidence, or context inspection
- `Researcher`
  - generates search strategies, gathers external evidence, retries when evidence is weak, and broadens/narrows queries
- `Synthesizer`
  - produces grounded answers from evidence and clearly separates support from inference
- `Knowledge Curator`
  - decides what should be written back into local knowledge, checks duplication/conflicts, and manages knowledge quality

Why this matters:

- it gives each part of the system a clear purpose
- it makes the project easier to evaluate and evolve
- it prevents the system from becoming a pile of coupled scripts

### 4.2 Strengthen the Knowledge Model

Right now, knowledge cards are useful, but still relatively document-like. For a long-lived agent, the knowledge base should become more structured and easier to reason over.

The next version of the card schema should consider fields such as:

- `domain`
- `subdomain`
- `question_types`
- `aliases`
- `prerequisites`
- `claims`
- `evidence_level`
- `review_status`
- `supersedes`
- `conflicts_with`
- `last_reviewed_at`
- `freshness_expectation`

The most important shift is to move from “stored text” toward “stored validated claims.”

For example, a card should gradually become able to represent:

- what specific claims it contains
- which citations support each claim
- how strong that support is
- whether the card is draft, reviewed, trusted, stale, or deprecated

This makes the knowledge base much more useful for an agent that must judge confidence rather than only fetch text.

### 4.3 Improve Retrieval Beyond Minimal Lexical Matching

The current lexical retrieval is appropriate for bootstrapping, but it will become a bottleneck for real domain use.

Specialized-domain questions often use:

- synonyms
- abbreviations
- alternate phrasings
- conceptually related language instead of exact terms

Examples:

- “X-band QPE” vs “radar rainfall estimation”
- “iterative QPE” vs “semiclassical phase estimation”
- “deployment-time compression” vs “quantization-aware training”

Recommended retrieval architecture:

- lexical retrieval (BM25 or equivalent)
- embedding retrieval
- query expansion / alias expansion
- reranking for top-k candidates

Desired behavior:

- lexical retrieval preserves precision on exact terminology
- embedding retrieval improves recall on paraphrases and related concepts
- reranking improves final evidence quality for answer construction

Without this upgrade, the system will often have the right knowledge but fail to retrieve it consistently.

### 4.4 Add Knowledge Governance and Lifecycle Management

Because the project goal includes updating local knowledge continuously, governance is not optional. A knowledge base that only grows will become noisy, contradictory, and hard to trust.

The system should introduce explicit lifecycle states such as:

- `draft`
- `reviewed`
- `trusted`
- `stale`
- `deprecated`

And should eventually support these operations:

- duplicate detection
- similarity checks before promotion
- conflict detection between cards
- card versioning or supersession
- downgrade of stale cards
- freshness review for time-sensitive material
- prioritization of “high-use, low-confidence” cards for review

This is one of the biggest differences between a toy RAG system and a production-worthy domain agent.

### 4.5 Make Evaluation a First-Class System Component

The project currently has tests that validate logic and workflow behavior. That is necessary, but not sufficient.

The main question is not only:

- does the script run?

The more important questions are:

- does the agent retrieve the right evidence?
- does the final answer improve with local knowledge?
- does the knowledge base become more useful after updates?
- does the agent avoid hallucinating when evidence is weak?

Recommended evaluation layers:

#### A. Retrieval Evaluation

Measure whether the correct cards are retrieved.

Suggested metrics:

- top-1 hit rate
- top-3 hit rate
- top-5 hit rate
- recall per domain/topic
- retrieval quality by query type

#### B. Answer Quality Evaluation

Measure whether the final grounded answer is actually good.

Suggested dimensions:

- factual correctness
- evidence usage quality
- hallucination avoidance
- uncertainty expression quality
- citation usefulness

#### C. Knowledge Update Evaluation

Measure whether promoted knowledge improves later performance.

Suggested questions:

- after adding a new card, do relevant future queries improve?
- does retrieval become cleaner or noisier?
- do answers become more grounded?
- does duplication increase?

The project should build a benchmark set of real target-domain questions, ideally grouped into categories:

- definition
- comparison
- derivation
- engineering design / implementation
- decision support
- latest / freshness-sensitive

Without this evaluation layer, it will be difficult to know whether the system is genuinely improving or merely becoming more complex.

### 4.6 Make Uncertainty and Evidence Sufficiency Explicit

A strong domain agent must not only answer well. It must also know when it should not answer confidently.

This is especially important in narrow domains where:

- local knowledge may be incomplete
- web evidence may be weak or stale
- terminology may be overloaded
- the latest information may matter

The current `answer_context` structure already points in the right direction. This should be strengthened into a stable answer contract.

Suggested answer structure:

- `Direct Support`
- `Inference`
- `Uncertainty`
- `Missing Evidence`
- `Suggested Next Retrieval`

Desired agent behavior:

- if local evidence is strong, answer directly and cite it
- if evidence is partial, answer narrowly and mark uncertainty
- if freshness matters, explicitly trigger web verification
- if evidence is insufficient, refuse false certainty and explain what is missing

This ability will be one of the core reasons the system can outperform a general model in specialized domains.

## 5. Recommended Target Architecture

The target architecture can be thought of as a layered agent system:

### Layer 1: Knowledge Substrate

- structured knowledge cards
- domain ontologies / aliases
- local indexes
- embeddings / lexical indexes
- freshness metadata

### Layer 2: Retrieval and Evidence

- query analysis
- route classification
- local retrieval
- external search
- reranking
- evidence-pack construction

### Layer 3: Agent Control

- route decision
- evidence sufficiency checks
- iterative search loops
- confidence policies
- refusal / fallback logic

### Layer 4: Answer Generation

- grounded synthesis
- explicit distinction between support and inference
- citation rendering
- uncertainty expression

### Layer 5: Knowledge Curation

- distillation
- promotion
- deduplication
- conflict checks
- lifecycle management
- periodic review

This layered model gives the project clear growth paths without losing control of complexity.

## 6. Suggested Implementation Order

To reduce risk, the project should evolve in phases.

### Phase 1: Formalize the Agent Control Loop

Goals:

- define clear role boundaries
- formalize route and evidence-sufficiency decisions
- make web-vs-local behavior explicit and testable

Deliverables:

- a documented agent state machine or role contract
- clearer interfaces between router, researcher, synthesizer, and curator
- tests covering route decisions and fallback behavior

Why first:

- this provides the control structure for all later improvements

### Phase 2: Upgrade the Knowledge Schema and Lifecycle

Goals:

- make cards more structured
- distinguish draft knowledge from trusted knowledge
- prepare for long-term maintainability

Deliverables:

- expanded frontmatter schema
- lifecycle states and promotion rules
- duplicate/conflict detection design

Why second:

- better retrieval and curation depend on better knowledge objects

### Phase 3: Upgrade Retrieval Quality

Goals:

- improve recall and ranking quality
- support synonymy and concept-level matching

Deliverables:

- BM25 or improved lexical search
- embedding-based retrieval
- reranking layer
- retrieval evaluation benchmark

Why third:

- retrieval quality is one of the largest drivers of downstream answer quality

### Phase 4: Build a Proper Evaluation Framework

Goals:

- measure whether the agent is actually improving
- catch regressions in retrieval, answering, and curation

Deliverables:

- domain benchmark query set
- retrieval evaluation runner
- answer-quality evaluation rubric
- knowledge-update impact tests

Why fourth:

- once architecture and retrieval are improved, the project needs a reliable way to measure gains

### Phase 5: Automate Knowledge Improvement

Goals:

- turn high-value runs into curated local improvements
- prioritize review where it matters most

Deliverables:

- curator workflow for candidate generation
- review queue for low-confidence or high-impact cards
- freshness review tasks
- promotion policies

Why fifth:

- this is where the system begins to behave like a self-improving domain agent instead of a static RAG tool

## 7. Acceptance Criteria for the End Goal

The project can be considered to be moving toward the right outcome when the following become true:

- the agent can clearly justify why it used local, web, mixed, or context-led mode
- the agent can detect weak evidence and request additional retrieval instead of bluffing
- the local knowledge base contains structured, reviewable, and maintainable knowledge objects
- retrieval can recover domain knowledge even when the user phrasing differs from card phrasing
- promoted knowledge measurably improves future performance
- evaluation makes it obvious when the system improves or regresses
- uncertainty handling is a strength of the system rather than an afterthought

## 8. Immediate Next Recommendations

If prioritizing for near-term project momentum, the best order is:

1. define the agent architecture and control loop clearly
2. expand the knowledge schema and lifecycle states
3. improve retrieval quality beyond basic lexical matching
4. build benchmark-driven evaluation
5. automate knowledge curation and continuous updates

This order gives the project both strategic clarity and a practical implementation path.

## 9. Summary

The key insight is:

**The project should be optimized as a domain-enhanced agent system, not only as a local RAG prototype.**

The current repository already demonstrates a promising bootstrap loop. The next step is to make the system:

- more agentic
- more structured
- more evaluable
- more governable
- more reliable under uncertainty

If those upgrades are executed in the right order, the project can evolve from a useful knowledge pipeline into a strong specialized-domain agent that improves meaningfully over time.
