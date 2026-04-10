# Lore Agent

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![MCP Ready](https://img.shields.io/badge/MCP-Ready-brightgreen.svg)

[中文](README.zh-CN.md)

> LLMs lack up-to-date, domain-specific knowledge. Lore Agent fixes this with **online research + local knowledge accumulation**, making your AI smarter in your domain over time. Integrates with Claude Code and VS Code Copilot via MCP.

## Core Mechanism: Research → Accumulate → Get Smarter

LLM training data is static. When you need answers about specialized domains or recent developments, it can only guess from general knowledge.

Lore Agent adds a **knowledge flywheel**:

```
Your question
    │
    ▼
Online research (AI agent search + SearXNG + academic APIs)
    │
    ▼
Structured synthesis (with citations, confidence, uncertainty)
    │
    ▼
Local accumulation (Markdown knowledge cards + BM25 index)
    │
    ▼
Next question: AI checks local first ── hit? ──► use directly, fast & accurate
    │ miss
    ▼
Research again → accumulate → reindex ──► knowledge base keeps growing
```

Every round of use builds up. The first time you ask about a domain, it researches online. The second time you ask a related question, AI pulls from your local knowledge base — fast and accurate.

Knowledge cards have full lifecycle management: **draft → reviewed → trusted → stale → deprecated**. Outdated knowledge gets flagged, new research overwrites old conclusions.

## Comparison

| | Lore Agent | Prompt-based Wiki (e.g. llm-wiki-agent) |
|---|---|---|
| **Research** | AI agent search + SearXNG meta-search + OpenAlex / Semantic Scholar APIs + local BM25 / embedding, evidence normalized & merged | Relies on LLM's own ability, no independent search pipeline |
| **Knowledge lifecycle** | draft → reviewed → trusted → stale → deprecated | None — files are files |
| **Knowledge flywheel** | Research → accumulate → reuse → gets smarter | One-way: LLM writes, human reads |
| **Answer quality** | Structured JSON: claims + evidence IDs + uncertainty | Raw text |
| **Graph & linking** | `[[wiki-links]]`, backlinks, interactive vis.js graph | Folder-based, no cross-references |

## More Features

- **Multi-perspective research** — Parallel research from 5 perspectives (academic, technical, applied, contrarian, historical) to avoid single-source bias
- **Obsidian compatible** — Cards are standard Markdown + YAML frontmatter + `[[wiki-links]]`, browse directly in Obsidian
- **Knowledge governance CLI** — Validate frontmatter, detect orphaned cards and broken links, find duplicates, manage card state transitions
- **Provider fault tolerance** — Each search source fails independently; falls back to local retrieval when offline

## Quick Start

```bash
# Clone and install
git clone https://github.com/zfy465914233/lore-agent.git
cd lore-agent
pip install -r requirements.txt

# Build the knowledge index
python scripts/local_index.py --output indexes/local/index.json

# (Optional) Start SearXNG for web research
docker compose up -d
```

MCP configs are pre-configured for both Claude Code and VS Code Copilot:

- **Claude Code**: `.mcp.json` is ready. `cd` into the project and start Claude Code.
- **VS Code Copilot**: `.vscode/mcp.json` is ready. Open the project, enable agent mode.

### Embed into an existing project

```bash
cp -r lore-agent/ your-project/lore-agent/
cd your-project && python lore-agent/setup_mcp.py
```

Auto-generates config. Knowledge lives in **your project**, not inside lore-agent.

## MCP Tools

AI agents interact with the knowledge base through 6 MCP tools:

| Tool | Description |
|------|-------------|
| `query_knowledge` | Search local knowledge base |
| `save_research` | Save research results as a knowledge card (supports Mermaid diagrams, source images) |
| `list_knowledge` | Browse all knowledge cards |
| `capture_answer` | Quick-capture a Q&A pair as a draft card |
| `ingest_source` | Ingest a URL or raw text into the knowledge base |
| `build_graph` | Generate an interactive knowledge graph (vis.js) |

## Project Structure

```
lore-agent/
├── mcp_server.py              # MCP server (6 tools)
├── setup_mcp.py               # Embed into existing projects
├── docker-compose.yml         # SearXNG
├── requirements.txt
├── schemas/                   # Answer + evidence JSON schemas
├── scripts/                   # Retrieval, research, synthesis, governance, graph
├── knowledge/                 # Knowledge cards (Markdown + YAML frontmatter)
├── indexes/                   # Generated (gitignored)
└── tests/                     # 192 tests, ~5s
```

## Benchmark

```bash
python scripts/run_eval.py --dry-run
```

| Metric | Score |
|---|---|
| Route accuracy | 100% (8/8) |
| Retrieval hit rate | 100% (8/8) |
| Min citations met | 100% (8/8) |
| Errors | 0 |

## License

MIT — see [LICENSE](LICENSE).
