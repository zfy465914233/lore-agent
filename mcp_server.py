"""MCP server exposing optimizer knowledge tools to Claude Code and Copilot.

Tools:
  - query_knowledge: Search the local knowledge base
  - save_research: Persist structured research results as a knowledge card
  - list_knowledge: Browse all knowledge cards, optionally filtered by topic

Usage:
  # Direct run (for testing):
  python mcp_server.py

  # Via FastMCP CLI:
  fastmcp run mcp_server.py

  # Via uv (zero install):
  uv run --with fastmcp fastmcp run mcp_server.py

Configuration — add to .mcp.json in the project root:
  {
    "mcpServers": {
      "optimizer": {
        "command": "uv",
        "args": ["run", "--with", "fastmcp", "fastmcp", "run", "mcp_server.py"]
      }
    }
  }
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure scripts/ is importable
ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from close_knowledge_loop import (
    build_knowledge_card,
    infer_domain,
    validate_answer_schema,
)
from close_knowledge_loop import reindex as _reindex
from lore_config import get_knowledge_dir, get_index_path
from local_retrieve import retrieve

try:
    from fastmcp import FastMCP
    mcp = FastMCP("lore")
    tool = mcp.tool
except ImportError:
    # Allow running without fastmcp — decorators become no-ops
    mcp = None  # type: ignore[assignment]
    def tool(fn):  # type: ignore[misc]
        return fn


@tool
def query_knowledge(query: str, limit: int = 5) -> str:
    """Search the local knowledge base for relevant information.

    Returns top-k knowledge cards matching the query, with scores and content.
    Use this to find existing knowledge before doing web research.

    Args:
        query: The search query in natural language.
        limit: Maximum number of results to return (default 5).
    """
    if not get_index_path().exists():
        return json.dumps({
            "error": "Knowledge index not found. Run local_index.py first.",
            "results": [],
        })

    result = retrieve(query, get_index_path(), limit)
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def save_research(query: str, answer_json: str) -> str:
    """Save structured research results as a knowledge card in the local knowledge base.

    The answer_json must conform to schemas/answer.schema.json:
    {
      "answer": "detailed answer text",
      "supporting_claims": [{"claim": "...", "evidence_ids": ["..."], "confidence": "high|medium|low"}],
      "inferences": ["..."],
      "uncertainty": ["..."],
      "missing_evidence": ["..."],
      "suggested_next_steps": ["..."]
    }

    Args:
        query: The original research question.
        answer_json: JSON string with the structured answer.
    """
    try:
        answer_data = json.loads(answer_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    # Validate against schema
    warnings = validate_answer_schema(answer_data)

    # Build knowledge card
    card_path = build_knowledge_card(query, answer_data, None, get_knowledge_dir())

    # Rebuild index
    reindex_ok = _reindex(get_index_path())

    return json.dumps({
        "status": "ok",
        "card_path": str(card_path),
        "reindexed": reindex_ok,
        "schema_warnings": warnings,
    }, ensure_ascii=False, indent=2)


@tool
def list_knowledge(topic: str | None = None) -> str:
    """List all knowledge cards in the local knowledge base.

    Returns card metadata (id, title, topic, type) for browsing and discovery.

    Args:
        topic: Optional topic filter (e.g. 'qpe', 'markov_chain'). Returns all if omitted.
    """
    index_path = get_index_path()
    if not index_path.exists():
        return json.dumps({"cards": [], "total": 0, "error": "Index not found. Run local_index.py first."})

    try:
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return json.dumps({"cards": [], "total": 0, "error": "Failed to read index."})

    cards = []
    for doc in index_data.get("documents", []):
        if topic and doc.get("topic") != topic:
            continue
        cards.append({
            "id": doc.get("doc_id", ""),
            "title": doc.get("title", ""),
            "topic": doc.get("topic", ""),
            "type": doc.get("type", ""),
            "path": doc.get("path", ""),
        })

    return json.dumps({"cards": cards, "total": len(cards)}, ensure_ascii=False, indent=2)


def _parse_frontmatter(content: str) -> dict:
    """Simple YAML frontmatter parser for metadata extraction."""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    meta: dict = {}
    for line in content[3:end].strip().splitlines():
        if ":" in line and not line.startswith("  "):
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta


if __name__ == "__main__":
    if mcp is None:
        print("Error: fastmcp not installed. Run: pip install fastmcp", file=sys.stderr)
        sys.exit(1)
    mcp.run()
