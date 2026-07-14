# Scholar Agent vs. Academic Research Agents

> Companion to [`comparison.md`](comparison.md), which compares us against *memory* tools (mem0 / MemGPT / Zep). This page compares us against *academic research* agents on GitHub — projects that also search, read, and reason over papers.
>
> Star counts are as of July 2026 and move quickly; treat them as a rough signal of community traction, not of quality.

Most projects in this space share a surface (arXiv search, PDF reading, an LLM in the loop) but solve fundamentally different problems. This page is honest about where each one is better.

---

## TL;DR Table

| Dimension | **Scholar Agent** (us) | [scholaraio](https://github.com/ZimoLiao/scholaraio) | [Deep-Research-Agent](https://github.com/CYC2002tommy/Deep-Research-Agent) | [scholar-rag-agent](https://github.com/Francis1998/scholar-rag-agent) | [hxcm-cre/scholar-agent](https://github.com/hxcm-cre/scholar-agent) |
|---|:---:|:---:|:---:|:---:|:---:|
| **What it really is** | Knowledge flywheel that compounds from every conversation | Agent-first research workspace (library + CLI + read-only WebUI + skills) | Anti-hallucination review pipeline (a 25 KB prompt skill) | Evidence-chained RAG Q&A engine over an ingested corpus | Qwen-driven review-generation web app |
| **Stars** | ~8 | ~546 | ~282 | ~44 | ~38 |
| **Form factor** | MCP server + CLI (Claude Code / VS Code / OpenCode) | CLI + read-only WebUI + Agent Skills | Prompt skill + glue scripts (Hermes / Claude Code) | FastAPI + Docker | React + FastAPI + Celery |
| **Paper sources** | arXiv · DBLP · Semantic Scholar · 10+ venues | OpenAlex · arXiv · CrossRef · USPTO | Scopus · Exa · OpenAlex · S2 · Crossref · Unpaywall | 10 sources (arXiv/S2/OpenAlex/PubMed/Crossref/PMC/DOAJ/DBLP/HAL/PDF) | arXiv · Zotero |
| **Where the reasoning lives** | Local-first; LLM only for synthesis & analysis | **Doesn't reason** — feeds tools to your coding agent | Host LLM (Gemini/OpenAI) | LLM agent (Observe → Decide → Act) | Qwen (LangGraph, locked) |
| **Knowledge persistence** | **Card lifecycle + provenance gate + Obsidian + graph** | Paper library (paper.md + sqlite + FAISS) | Outsourced to Obsidian / Zotero / NotebookLM | SQLite event log + self-built vector/graph store | SQL tables (Literature/Project/Report) |
| **Retrieval** | BM25 (+ optional embedding, **nDCG@3≈0.95**) | Keyword + semantic + line-addressable chunks + federated | None self-built (multi-source APIs) | dense + BM25 + HyDE + RRF + MMR + **GraphRAG multi-hop** | LangChain BM25Retriever (no vectors) |
| **Scoring** | 4-dim (fit/freshness/impact/rigor) + venue soft-bonus | Citation filter only, no scoring | Hard Q1/Q2 rule filter, Q4/MDPI banned | None (MMR de-dup, no ranking) | CCF/CAS venue grade + repro weight |
| **Anti-hallucination** | `save_research` provenance gate + grounding rules | — | **Per-DOI liveness test + claim grounding loop** | **`[UNGROUNDED]` + chunk-level provenance** | — |
| **Maintenance** | Active, 1.5k+ tests | Very active, v1.5.0 | Stalled ~3 weeks | Very active (41% AI-authored commits) | Stalled ~2.5 months |
| **License** | MIT | MIT | MIT | Apache-2.0 | **GPL-3.0** |

---

## Detailed Breakdown

### scholaraio — "agent-first research workspace"

**What it does well.** The closest peer in philosophy: local-first, built to sit beside your coding agent, ships Agent Skills for Claude/Codex/Qwen/Cursor/Cline/Windsurf/Copilot. Its paper library is mature — MinerU/Docling PDF parsing, FAISS semantic search, BERTopic topic clustering, forward/backward citation graphs, and a read-only WebUI. v1.5.0, very active, ~546 stars. Data sources are broad (OpenAlex, USPTO, CrossRef).

**Where we differ.** scholaraio stores a *paper library*; we accumulate *conversation knowledge with citations and a quality lifecycle*. It does no LLM reasoning itself — every "analysis" comes from whichever agent you wire up to it. It has no knowledge-lifecycle management (no `draft → trusted → deprecated`, no provenance gate, no stale scan), and no scoring (citation-count filter only). Its persistence is papers; ours is reasoning.

**When to pick scholaraio.** You want a managed local library + writing workbench (review, rebuttal, poster) and are happy driving the LLM yourself.
**When to pick us.** You want each question you ask to leave behind a citable card that makes the next answer better — a compounding knowledge base, not a paper shelf.

---

### Deep-Research-Agent — "anti-hallucination review pipeline"

**What it does well.** Takes hallucination more seriously than anything else here. A 7-phase pipeline forbids abstract-only shortcuts, requires full-text deep reads, and runs a **per-DOI liveness test with a claim-grounding loop** — dead links must be replaced with Q1/Q2 papers, looping until every claim is grounded. Outputs APA 7th `.docx`.

**Where we differ.** It's a *prompt skill* (not software) that produces one review document; we're a *persistent knowledge base* that grows from every conversation. It outsources persistence to Obsidian/Zotero/NotebookLM; our persistence is the product. Strong Windows + campus-network + paywall-bypass (cloakbrowser) assumptions limit portability.

**When to pick Deep-Research-Agent.** You need a one-shot, tightly-validated literature review document.
**When to pick us.** You're building durable expertise, not delivering a single artifact. (We did, however, borrow its grounding instincts — see ④ grounding rules.)

---

### scholar-rag-agent — "evidence-chained RAG Q&A"

**What it does well.** The most complete retrieval stack of the bunch: dense + BM25 + HyDE + RRF + MMR + **GraphRAG multi-hop**, across 10 sources. Answers carry chunk-level provenance and ungrounded assertions are marked `[UNGROUNDED]`. Strict engineering gates (ruff + mypy strict + coverage ≥ 70%).

**Where we differ.** It's a *Q&A engine* — you ingest a corpus, then ask questions. It does **no discovery or recommendation** (no daily feed, no scoring). We invert that: discovery + scoring + synthesis, with knowledge cards as the unit. Its reasoning is chunk-granular; ours is card-granular. Note ~41% of its commits are authored by a Cursor AI agent, so human-review depth is uncertain.

**When to pick scholar-rag-agent.** You already have a corpus and want evidence-chained multi-hop answers.
**When to pick us.** You want the system to *find* papers, *score* them, and *accumulate* knowledge over time.

---

### hxcm-cre/scholar-agent — "Qwen review generator"

**What it does well.** A polished ChatGPT-style web app (deployed on Vercel) for conversational literature search with a **metric-extraction + experiment-result alignment** feature (extract quantitative metrics from PDFs and compare to your own CSV) — genuinely uncommon. CCF/CAS venue grading for the Chinese research context.

**Where we differ.** Single source (arXiv only), locked to Qwen via DashScope, no vector store (its "RAG" is BM25), no tests, ships binaries in git, and has stalled ~2.5 months. Our scoring is model-agnostic, we have 1.5k+ tests, and we persist knowledge rather than generating one-off reports.

**When to pick hxcm-cre.** You want a turnkey Chinese-research-context review web app and are fine with Qwen + arXiv-only.
**When to pick us.** You want a model-agnostic, test-backed knowledge engine that integrates with your IDE.

---

## The Core Difference: Knowledge Governance Is the Gap

Every project above is either a *library*, a *pipeline*, or a *Q&A engine*. None of them treat accumulated knowledge as something to be **governed**.

Scholar Agent does:

- **Quality lifecycle** — every card moves `draft → reviewed → trusted → stale → deprecated`, with promote / close-loop operations.
- **Provenance gate** — `save_research` refuses to persist a card unless every claim cites a source. No evidence, no card.
- **Dead-link diagnosis** — `scan_dead_links` / `report-dead-links` detect 404/410/connect-failure across every card's sources, read-only.
- **Obsidian-native** — YAML frontmatter + auto-generated `[[wiki-links]]` + a queryable knowledge graph. Your knowledge is plain Markdown you own.
- **Retrieval with a benchmark floor** — BM25 (+ optional hybrid) is held to nDCG@3 / Recall@5 thresholds; weights are tuned by real sweeps, not guessed.
- **Grounding rules** — confidence is downgraded when evidence is thin, with the reasoning recorded in `uncertainty[]`.

This is the same posture as `comparison.md`'s memory-tool argument, restated for the academic-agent cohort: most tools solve *finding* or *answering*; we solve **compounding** — every question makes the next answer sharper in your domain.

---

## Honest Shortcomings

We won't pretend the picture is all upside:

- **Community traction is small** (~8 stars vs. scholaraio's ~546). scholaraio is the credible incumbent in "agent + research workspace" mindshare.
- **No WebUI.** scholaraio and hxcm-cre both ship one; we're MCP + CLI only by design (we live inside your IDE).
- **Narrower source set** by choice. We deliberately did **not** adopt OpenAlex (in our testing, metadata quality was poor for our domains); our coverage is arXiv + DBLP + Semantic Scholar + curated top venues. If your domain lives outside CS, that's a real gap today.
- **Card-granular retrieval, not chunk-granular.** For our use case (cards are the unit) this is the right altitude and our benchmark confirms it, but scholar-rag-agent's chunk + multi-hop stack is more powerful for "answer questions over a large ingested corpus" — a job we don't claim to do.

---

## FAQ

**Q: Should I use scholaraio *and* Scholar Agent together?**
Yes, if it fits your workflow. scholaraio as your paper library + reading workbench, Scholar Agent as your compounding knowledge brain inside your IDE. They don't overlap on persistence.

**Q: You say "knowledge governance," but scholar-rag-agent has `[UNGROUNDED]` and Deep-Research-Agent has DOI liveness tests — isn't that the same?**
Close in spirit, different in scope. Those are *answer-time* checks (is this answer grounded?). Ours are also *persistence-time* (is this card allowed to enter the knowledge base?) and *maintenance-time* (is this card still backed by live sources, still fresh, still well-linked?). Governance spans the whole life of a card.

**Q: Why no GraphRAG / chunk retrieval then?**
Because our unit is the card, not the chunk. Multi-hop and chunk retrieval shine when you query a large opaque corpus; we keep knowledge in small, human-readable, citable cards that an LLM can already synthesize across. See [`进度与效果.md`](进度与效果.md) for the retrieval-quality work that backs this call.

**Q: Why didn't you adopt CCF hard-grading like hxcm-cre?**
Hard venue grading punishes preprints — and in CS, the preprint *is* often the primary artifact. We add venue as a **soft bonus** (CCF-A/B/C adds to the recommendation score; a preprint simply gets no bonus and isn't penalized).
