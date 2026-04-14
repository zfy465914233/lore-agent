"""Dynamic routing for knowledge folders.

Routes cards into a hierarchical structure:
    knowledge/<major_domain>/<card>.md
    knowledge/<major_domain>/<subdomain>/<card>.md

The routing policy lives in schemas/domain_routing_policy.json so the
decision rules are data-driven instead of being hardcoded in Python.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "schemas" / "domain_routing_policy.json"
GUIDE_PATH = ROOT / "schemas" / "domain_routing_guide.md"

# ── Folder cache ───────────────────────────────────────────────────

_domain_tree_cache: dict[str, dict[str, Path]] | None = None
_cache_root: Path | None = None
ROOT_SUBDOMAIN = ""


def load_routing_policy() -> dict[str, object]:
    """Load the domain routing policy from disk."""
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def load_routing_guide() -> str:
    """Load the human-readable routing guide from disk."""
    if not GUIDE_PATH.exists():
        return ""
    return GUIDE_PATH.read_text(encoding="utf-8")


def discover_domain_tree(knowledge_root: Path) -> dict[str, dict[str, Path]]:
    """Scan knowledge_root for major-domain folders and optional subdomains."""
    domain_tree: dict[str, dict[str, Path]] = {}
    if not knowledge_root.exists():
        return domain_tree
    for child in sorted(knowledge_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name == "templates":
            continue
        subdomains: dict[str, Path] = {}
        has_root_cards = False
        for grandchild in sorted(child.iterdir()):
            if grandchild.is_dir() and not grandchild.name.startswith("."):
                subdomains[grandchild.name] = grandchild
            elif grandchild.is_file() and grandchild.suffix.lower() == ".md":
                has_root_cards = True
        if has_root_cards or not subdomains:
            subdomains[ROOT_SUBDOMAIN] = child
        if subdomains:
            domain_tree[child.name] = subdomains
    return domain_tree


def get_domain_tree(knowledge_root: Path) -> dict[str, dict[str, Path]]:
    """Return cached domain tree, rebuilding if necessary."""
    global _domain_tree_cache, _cache_root
    if _domain_tree_cache is None or _cache_root != knowledge_root:
        _domain_tree_cache = discover_domain_tree(knowledge_root)
        _cache_root = knowledge_root
    return _domain_tree_cache


def clear_folder_cache() -> None:
    """Invalidate the folder cache so next call re-discovers the tree."""
    global _domain_tree_cache, _cache_root
    _domain_tree_cache = None
    _cache_root = None


# ── Token extraction ───────────────────────────────────────────────


def _tokens_from_text(value: str) -> list[str]:
    parts = value.lower().split("-")
    return [value.lower()] + parts


def _major_tokens(major_slug: str, major_policy: dict[str, object]) -> list[str]:
    tokens = _tokens_from_text(major_slug)
    label = str(major_policy.get("label", "")).lower()
    if label:
        tokens.append(label)
    for alias in major_policy.get("aliases", []):
        tokens.append(str(alias).lower())
    return list(dict.fromkeys(tokens))


def _subdomain_tokens(sub_slug: str, sub_policy: dict[str, object]) -> list[str]:
    if not sub_slug:
        return []
    tokens = _tokens_from_text(sub_slug)
    label = str(sub_policy.get("label", "")).lower()
    if label:
        tokens.append(label)
    for alias in sub_policy.get("aliases", []):
        tokens.append(str(alias).lower())
    return list(dict.fromkeys(tokens))


# ── Matching ───────────────────────────────────────────────────────


def _score_tokens(query: str, tokens: list[str]) -> int:
    """Return a lightweight lexical score for a token list."""
    q = query.lower()
    score = 0
    for token in tokens:
        if not token:
            continue
        if re.fullmatch(r"[a-z0-9-]+", token):
            pattern = rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])"
            if re.search(pattern, q):
                score = max(score, len(token.split("-")))
        elif token in q:
            score = max(score, len(token))
    return score


def match_route(
    query: str,
    policy: dict[str, object],
    domain_tree: dict[str, dict[str, Path]],
) -> tuple[str, str | None] | None:
    """Match a query against major domains and subdomains using policy aliases."""
    majors = policy.get("major_domains", {})
    best_route: tuple[str, str | None] | None = None
    best_score = 0

    for major_slug, major_policy in majors.items():
        major_score = _score_tokens(query, _major_tokens(major_slug, major_policy))
        available_subdomains = set(domain_tree.get(major_slug, {}).keys())
        available_subdomains.update(major_policy.get("subdomains", {}).keys())

        for subdomain_slug in available_subdomains:
            if subdomain_slug in {ROOT_SUBDOMAIN, "general"}:
                continue
            sub_policy = major_policy.get("subdomains", {}).get(subdomain_slug, {})
            sub_score = _score_tokens(query, _subdomain_tokens(subdomain_slug, sub_policy))
            if sub_score == 0:
                continue
            pair_score = (sub_score * 10) + major_score
            if pair_score > best_score:
                best_score = pair_score
                best_route = (major_slug, subdomain_slug)

        if major_score > best_score:
            best_score = major_score
            best_route = (major_slug, None)

    if best_route is None or best_score == 0:
        return None

    return best_route


# ── AI fallback ────────────────────────────────────────────────────


def _router_api_url() -> str:
    return os.getenv("LORE_ROUTER_API_URL") or os.getenv("LLM_API_URL") or "https://api.openai.com/v1"


def _router_api_key() -> str:
    return os.getenv("LORE_ROUTER_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("GITHUB_TOKEN") or ""


def _router_model() -> str:
    return os.getenv("LORE_ROUTER_MODEL") or os.getenv("LLM_MODEL") or "gpt-4o-mini"


def _call_router_llm(prompt: str) -> str | None:
    """Call an OpenAI-compatible endpoint for folder classification.

    This intentionally reuses the same environment contract as the synthesis
    path so the router fallback can work in VS Code Copilot setups as well,
    including GitHub-token-backed endpoints.
    """
    api_key = _router_api_key()
    if not api_key:
        return None

    payload = {
        "model": _router_model(),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a knowledge base taxonomy assistant. "
                    "Return exactly one folder slug and nothing else."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 32,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    req = Request(
        _router_api_url().rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, json.JSONDecodeError):
        return None

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        return None


def _build_routing_prompt(
    query: str,
    policy: dict[str, object],
    domain_tree: dict[str, dict[str, Path]],
    guide_text: str,
) -> str:
    """Build the prompt used for AI route decisions."""
    majors = policy.get("major_domains", {})
    existing = {
        major_slug: sorted(subdomains.keys())
        for major_slug, subdomains in domain_tree.items()
    }
    guide_block = guide_text.strip() or "No routing guide available."
    return (
        "You are a knowledge base routing assistant. "
        "Choose a major domain and optionally a subdomain for the query. "
        "Follow the routing guide carefully. Prefer existing subdomains when they fit. "
        "If the major domain is clear but no specific subdomain fits, leave subdomain empty instead of using general. "
        "If the query does not fit any existing major domain, prefer creating a new major domain instead of using general.\n\n"
        f"Routing guide:\n{guide_block}\n\n"
        f"Routing policy JSON:\n{json.dumps(majors, ensure_ascii=False, indent=2)}\n\n"
        f"Existing directory tree JSON:\n{json.dumps(existing, ensure_ascii=False, indent=2)}\n\n"
        f"Query: {query}\n\n"
        "Respond with valid JSON only:\n"
        '{"major_domain":"...","subdomain":"" or "...","reason":"..."}'
    )


def infer_domain_with_ai(
    query: str,
    policy: dict[str, object],
    domain_tree: dict[str, dict[str, Path]],
) -> dict[str, str] | None:
    """Ask an LLM to decide a major domain and optional subdomain."""
    prompt = _build_routing_prompt(query, policy, domain_tree, load_routing_guide())
    text = _call_router_llm(prompt)
    if text is None:
        return None

    text = text.strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= start:
            return None
        try:
            payload = json.loads(text[start:end])
        except json.JSONDecodeError:
            return None

    major_domain = str(payload.get("major_domain", "")).strip()
    raw_subdomain = payload.get("subdomain", "")
    subdomain = "" if raw_subdomain is None else str(raw_subdomain).strip()
    reason = str(payload.get("reason", "")).strip()
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", major_domain):
        return None
    if subdomain and not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", subdomain):
        return None
    if subdomain == "general" and major_domain != "general":
        subdomain = ""
    return {
        "major_domain": major_domain,
        "subdomain": subdomain,
        "reason": reason,
    }


def _propose_new_major_domain(query: str) -> str:
    """Build a conservative fallback major-domain slug from the query text."""
    normalized = query.strip().lower()
    tokens = re.findall(r"[a-z0-9]+", normalized)
    if tokens:
        return "-".join(tokens[:3])

    compact = re.sub(r"\s+", "", query.strip())
    if compact:
        return compact[:16]

    return "general"


def _build_route(knowledge_root: Path, major_domain: str, subdomain: str | None) -> tuple[str, Path, str]:
    """Return the route slug, output path, and normalized subdomain string."""
    normalized_subdomain = (subdomain or "").strip()
    if normalized_subdomain == "general" and major_domain != "general":
        normalized_subdomain = ""

    output_path = knowledge_root / major_domain
    route_slug = major_domain
    if normalized_subdomain:
        output_path = output_path / normalized_subdomain
        route_slug = f"{major_domain}/{normalized_subdomain}"
    return route_slug, output_path, normalized_subdomain


def infer_domain_decision(
    query: str,
    knowledge_root: Path,
    use_ai_fallback: bool = True,
) -> dict[str, object]:
    """Infer the full domain routing decision for a query."""
    policy = load_routing_policy()
    domain_tree = get_domain_tree(knowledge_root)

    matched = match_route(query, policy, domain_tree)
    if matched is not None:
        major_domain, subdomain = matched
        route_slug, output_path, normalized_subdomain = _build_route(knowledge_root, major_domain, subdomain)
        output_path.mkdir(parents=True, exist_ok=True)
        clear_folder_cache()
        return {
            "major_domain": major_domain,
            "subdomain": normalized_subdomain,
            "route_slug": route_slug,
            "output_path": output_path,
            "decision_mode": "policy_match",
            "reason": "Matched against routing policy and existing domain tree.",
        }

    if use_ai_fallback:
        ai_choice = infer_domain_with_ai(query, policy, domain_tree)
        if ai_choice is not None:
            major_domain = str(ai_choice["major_domain"])
            subdomain = str(ai_choice["subdomain"])
            route_slug, output_path, normalized_subdomain = _build_route(knowledge_root, major_domain, subdomain)
            output_path.mkdir(parents=True, exist_ok=True)
            clear_folder_cache()
            return {
                "major_domain": major_domain,
                "subdomain": normalized_subdomain,
                "route_slug": route_slug,
                "output_path": output_path,
                "decision_mode": "llm_policy",
                "reason": ai_choice.get("reason", "AI selected the best matching route."),
            }

    new_major_domain = _propose_new_major_domain(query)
    if new_major_domain != "general":
        route_slug, output_path, normalized_subdomain = _build_route(knowledge_root, new_major_domain, None)
        output_path.mkdir(parents=True, exist_ok=True)
        clear_folder_cache()
        return {
            "major_domain": new_major_domain,
            "subdomain": normalized_subdomain,
            "route_slug": route_slug,
            "output_path": output_path,
            "decision_mode": "fallback_new_major",
            "reason": "No stable existing major domain matched, so a new major domain root was created by default.",
        }

    route_slug, output_path, normalized_subdomain = _build_route(knowledge_root, "general", None)
    output_path.mkdir(parents=True, exist_ok=True)
    clear_folder_cache()
    return {
        "major_domain": "general",
        "subdomain": normalized_subdomain,
        "route_slug": route_slug,
        "output_path": output_path,
        "decision_mode": "fallback_general",
        "reason": "No policy match or AI route available.",
    }


# ── Main entry point ───────────────────────────────────────────────


def infer_domain(
    query: str,
    knowledge_root: Path,
    use_ai_fallback: bool = True,
) -> tuple[str, Path]:
    """Infer the route slug and output path for a query.

    Returns (route_slug, output_path).
    """
    decision = infer_domain_decision(query, knowledge_root, use_ai_fallback=use_ai_fallback)
    return str(decision["route_slug"]), Path(str(decision["output_path"]))
