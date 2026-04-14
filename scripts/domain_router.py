"""Dynamic hierarchical domain routing for knowledge folders.

Replaces the hardcoded infer_domain() and infer_domain_folder() with:
  1. Zero-cost text matching against existing folder names
  2. Optional AI fallback for genuinely new domains
"""

from __future__ import annotations

import re
from pathlib import Path

from common import parse_frontmatter

# ── Alias table ────────────────────────────────────────────────────
# Maps folder slugs to extra keywords (Chinese, abbreviations, etc.)

FOLDER_ALIASES: dict[str, list[str]] = {
    "linear-programming": ["lp", "线性规划", "simplex"],
    "integer-programming": ["ip", "整数规划", "branch and bound", "branch-and-bound", "cutting plane"],
    "dynamic-programming": ["dp", "动态规划", "bellman"],
    "nonlinear-programming": ["nlp", "非线性规划", "kkt", "karush-kuhn-tucker"],
    "graph-theory": ["图论", "graph", "network", "网络", "最短路", "最小生成树", "最大流"],
    "game-theory": ["博弈论", "game", "纳什", "nash"],
    "decision-theory": ["决策论", "decision"],
    "queueing-theory": ["排队论", "queue", "排队"],
    "inventory-theory": ["库存论", "inventory", "库存"],
    "scheduling": ["排程", "tsp", "traveling salesman", "旅行商", "cpm", "pert", "关键路径"],
    "transportation": ["运输问题", "运输", "assignment", "指派"],
    "metaheuristics": ["启发式", "heuristic", "遗传算法", "genetic", "模拟退火", "simulated annealing", "禁忌搜索", "tabu"],
    "operations-research": ["运筹学", "optimization", "优化"],
    "applications": ["应用", "application"],
    "interdisciplinary": ["交叉学科", "interdisciplinary"],
    "probability-statistics": ["概率", "统计", "probability", "statistics", "概统", "随机", "贝叶斯", "bayes"],
    "markov-chain": ["markov", "马尔可夫", "马尔科夫"],
    "qpe": ["xgboost", "radar", "rainfall", "precipitation", "quantitative", "降水", "雷达", "定量"],
    "quantum-phase-estimation": ["quantum", "phase estimation", "量子", "相位估计"],
    "model-quantization": ["quantization", "qat", "量化", "compression", "deployment"],
}

# ── Folder cache ───────────────────────────────────────────────────

_folder_cache: dict[str, Path] | None = None
_cache_root: Path | None = None


def discover_folders(knowledge_root: Path) -> dict[str, Path]:
    """Scan knowledge_root for domain folders up to depth 2."""
    folder_map: dict[str, Path] = {}
    if not knowledge_root.exists():
        return folder_map
    for child in sorted(knowledge_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name == "templates":
            continue
        folder_map[child.name] = child
        for grandchild in sorted(child.iterdir()):
            if grandchild.is_dir() and not grandchild.name.startswith("."):
                folder_map[grandchild.name] = grandchild
    return folder_map


def get_folder_map(knowledge_root: Path) -> dict[str, Path]:
    """Return cached folder map, rebuilding if necessary."""
    global _folder_cache, _cache_root
    if _folder_cache is None or _cache_root != knowledge_root:
        _folder_cache = discover_folders(knowledge_root)
        _cache_root = knowledge_root
    return _folder_cache


def clear_folder_cache() -> None:
    """Invalidate the folder cache so next call re-discovers the tree."""
    global _folder_cache, _cache_root
    _folder_cache = None
    _cache_root = None


# ── Token extraction ───────────────────────────────────────────────


def folder_tokens(folder_slug: str) -> list[str]:
    """Extract searchable tokens from a folder slug + aliases."""
    parts = folder_slug.split("-")
    tokens: list[str] = [folder_slug] + parts
    for alias in FOLDER_ALIASES.get(folder_slug, []):
        tokens.append(alias.lower())
    return tokens


# ── Matching ───────────────────────────────────────────────────────


def match_folder(query: str, folder_map: dict[str, Path]) -> str | None:
    """Match a query against known folder names without any LLM call.

    Scores by word count of matched token. Returns best slug or None.
    """
    q = query.lower()
    best_slug: str | None = None
    best_score: int = 0

    for slug in folder_map:
        tokens = folder_tokens(slug)
        score = 0
        for token in tokens:
            t = token.lower()
            if not t:
                continue
            if t in q:
                s = len(t.split())
                if s > score:
                    score = s
        if score > best_score:
            best_score = score
            best_slug = slug

    return best_slug


# ── AI fallback ────────────────────────────────────────────────────


def infer_domain_with_ai(query: str, existing_folders: list[str]) -> str:
    """Ask an LLM to decide a folder slug for a new domain."""
    folder_list = ", ".join(sorted(existing_folders)) or "(none)"
    prompt = (
        f"You are a knowledge base taxonomy assistant. "
        f"Given a research query and a list of existing domain folders, "
        f"decide the best folder name for this query.\n\n"
        f"Existing folders: {folder_list}\n\n"
        f"If the query fits an existing folder, return that folder name exactly.\n"
        f"If it needs a new folder, create a short lowercase slug with hyphens "
        f"(max 3 words).\n\n"
        f'Query: "{query}"\n\n'
        f"Respond with ONLY the folder slug, nothing else."
    )
    try:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip().strip("'\"`")
        if re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", text):
            return text
    except Exception:
        pass
    return "general"


# ── Main entry point ───────────────────────────────────────────────


def infer_domain(
    query: str,
    knowledge_root: Path,
    use_ai_fallback: bool = True,
) -> tuple[str, Path]:
    """Infer the domain folder for a query.

    Returns (folder_slug, output_path).
    """
    folder_map = get_folder_map(knowledge_root)

    # Step 1: zero-cost matching
    slug = match_folder(query, folder_map)
    if slug is not None:
        return slug, folder_map[slug]

    # Step 2: AI fallback (opt-in)
    if use_ai_fallback:
        new_slug = infer_domain_with_ai(query, list(folder_map.keys()))
        if new_slug != "general":
            output_dir = knowledge_root / new_slug
            output_dir.mkdir(parents=True, exist_ok=True)
            clear_folder_cache()
            return new_slug, output_dir

    # Step 3: general catch-all
    general_dir = knowledge_root / "general"
    general_dir.mkdir(parents=True, exist_ok=True)
    return "general", general_dir
