"""Dead-link diagnosis for knowledge card sources.

Read-only check of every ``source_refs`` URL across the knowledge base.
Classifies each unique URL as ``ok`` / ``dead`` / ``transient`` / ``blocked`` /
``skipped`` / ``unknown``, deduplicating across cards so the same URL is probed
at most once and the result is fanned out to every card that cites it.

Probe policy:
- HEAD first, GET fallback (some hosts reject HEAD with 405/403).
- 4xx (incl. 404/410) => ``dead``; 429/5xx and connection errors =>
  ``transient`` (retried via :func:`retry_with_backoff`).
- Paywalled domains (see ``common.BLOCKED_FETCH_DOMAINS``) => ``blocked``.
- ``offline=True`` => every URL marked ``skipped`` (no network at all).

This is a *diagnostic* tool — it never edits cards or writes snapshots.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scholar_agent.engine.common import extract_source_urls, is_blocked_host
from scholar_agent.engine.knowledge_lifecycle import scan_knowledge_dir
from scholar_agent.engine.retry import retry_with_backoff

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (compatible; scholar-agent/1.0)"


class _Transient(Exception):
    """Internal signal: the probe hit a retry-worthy transient failure."""


class _HeadNotSupported(Exception):
    """Internal signal: host refused HEAD (405/403), fall back to GET."""


def _classify(code: int) -> str:
    """Map an HTTP status code to a dead-link status bucket."""
    if 200 <= code < 400:
        return "ok"
    if code == 429 or 500 <= code < 600:
        return "transient"
    return "dead"  # all other 4xx (404/410/403/...): inaccessible, flag for review


def _probe(url: str, method: str, timeout: float) -> int:
    """Perform one HTTP probe. Returns the status code.

    Raises :class:`_HeadNotSupported` (HEAD only → GET fallback),
    :class:`_Transient` (retry-worthy). Hard 4xx codes are returned, not raised.
    """
    req = Request(url, method=method, headers={"User-Agent": _UA})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return int(resp.getcode())
    except HTTPError as exc:
        code = exc.code
        if method == "HEAD" and code in (405, 403):
            raise _HeadNotSupported(str(exc)) from exc
        if code == 429 or 500 <= code < 600:
            raise _Transient(str(exc)) from exc
        return code
    except OSError as exc:
        # URLError, socket.timeout, ConnectionError, TimeoutError are all OSError.
        raise _Transient(str(exc)) from exc


def check_one_url(url: str, *, timeout: float = 10.0) -> dict[str, Any]:
    """Probe a single URL. Returns ``{url, status, status_code, reason}``."""
    blocked_by = is_blocked_host(url)
    if blocked_by:
        return {
            "url": url,
            "status": "blocked",
            "status_code": None,
            "reason": f"paywalled domain ({blocked_by}) skipped",
        }

    for method in ("HEAD", "GET"):
        try:
            code = retry_with_backoff(
                _probe,
                url,
                method,
                timeout,
                max_retries=2,
                retry_on=(_Transient,),
            )
        except _HeadNotSupported:
            continue  # try GET
        except _Transient as exc:
            return {
                "url": url,
                "status": "transient",
                "status_code": None,
                "reason": f"retries exhausted: {exc}",
            }
        except Exception as exc:
            return {
                "url": url,
                "status": "unknown",
                "status_code": None,
                "reason": f"{type(exc).__name__}: {exc}",
            }
        status = _classify(code)
        return {
            "url": url,
            "status": status,
            "status_code": code,
            "reason": "" if status == "ok" else f"HTTP {code}",
        }
    # Unreachable: GET never raises _HeadNotSupported, so the loop always returns.
    raise AssertionError("unreachable: GET must return")


def _check_urls(
    urls: list[str],
    *,
    concurrency: int,
    timeout: float,
) -> dict[str, dict[str, Any]]:
    """Probe a batch of URLs concurrently. Returns ``{url: result}``."""
    results: dict[str, dict[str, Any]] = {}
    if not urls:
        return results
    workers = max(1, min(concurrency, len(urls)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(check_one_url, u, timeout=timeout): u for u in urls}
        for fut in as_completed(futures):
            u = futures[fut]
            try:
                results[u] = fut.result()
            except Exception as exc:
                results[u] = {
                    "url": u,
                    "status": "unknown",
                    "status_code": None,
                    "reason": f"{type(exc).__name__}: {exc}",
                }
    return results


def check_dead_links(
    knowledge_root: Path,
    *,
    concurrency: int = 8,
    timeout: float = 10.0,
    offline: bool = False,
) -> dict[str, Any]:
    """Diagnose dead links across all knowledge cards. Read-only.

    Each unique URL is probed once; the result is fanned out to every card that
    references it. Returns a structured report with per-card rows and a summary.
    """
    cards = scan_knowledge_dir(knowledge_root)

    url_to_cards: dict[str, list[tuple[str, str]]] = {}
    cards_with_urls = 0
    for card in cards:
        urls = extract_source_urls(card)
        if not urls:
            continue
        cards_with_urls += 1
        cpath = card.get("_path", "")
        cid = card.get("id") or (Path(cpath).stem if cpath else "?")
        for url in urls:
            url_to_cards.setdefault(url, []).append((cid, cpath))

    unique_urls = list(url_to_cards.keys())

    if offline:
        url_results = {
            u: {"url": u, "status": "skipped", "status_code": None, "reason": "offline mode"}
            for u in unique_urls
        }
    else:
        url_results = _check_urls(unique_urls, concurrency=concurrency, timeout=timeout)

    rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for url, refs in url_to_cards.items():
        res = url_results.get(
            url, {"status": "unknown", "status_code": None, "reason": "not checked"}
        )
        status = str(res.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + len(refs)
        for cid, cpath in refs:
            rows.append(
                {
                    "card_id": cid,
                    "card_path": cpath,
                    "url": url,
                    "status": status,
                    "status_code": res.get("status_code"),
                    "reason": res.get("reason", ""),
                }
            )

    # Dead first, then by path/url for stable, actionable output.
    rows.sort(key=lambda r: (r["status"] != "dead", r["card_path"], r["url"]))

    return {
        "status": "ok",
        "knowledge_dir": str(knowledge_root),
        "cards_checked": cards_with_urls,
        "urls_checked": len(unique_urls),
        "summary": counts,
        "dead_count": counts.get("dead", 0),
        "results": rows,
    }
