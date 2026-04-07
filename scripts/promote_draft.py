"""Promote a distilled Markdown draft into a structured card candidate."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import safe_slug


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote a distilled note into a local card candidate.")
    parser.add_argument("--draft", type=Path, required=True, help="Path to the distilled Markdown draft.")
    parser.add_argument(
        "--knowledge-root",
        type=Path,
        default=Path("knowledge"),
        help="Root knowledge directory where promoted candidates should be written.",
    )
    return parser.parse_args()


def extract_section(text: str, heading: str) -> list[str]:
    marker = f"## {heading}\n"
    if marker not in text:
        return []
    tail = text.split(marker, 1)[1]
    next_heading = tail.find("\n## ")
    section = tail if next_heading == -1 else tail[:next_heading]
    return [line.rstrip() for line in section.strip().splitlines()]


def parse_query(text: str) -> str:
    lines = extract_section(text, "Query")
    return lines[0].strip() if lines else "untitled query"


def infer_card_type(query: str) -> str:
    normalized = query.lower().strip()
    if normalized.startswith("what is ") or " definition" in normalized:
        return "definition"
    if "derive" in normalized or "derivation" in normalized or "proof" in normalized:
        return "derivation"
    if "theorem" in normalized:
        return "theorem"
    if normalized.startswith("compare ") or " comparison" in normalized:
        return "comparison"
    if normalized.startswith("decision ") or "decision on " in normalized:
        return "decision_record"
    return "method"


def infer_domain_folder(query: str) -> str:
    normalized = query.lower().strip()
    if any(term in normalized for term in ("markov", "stationary distribution", "stochastic")):
        return "markov_chain"
    if any(term in normalized for term in ("x-band", "radar", "rainfall", "precipitation")):
        return "qpe"
    if any(term in normalized for term in ("quantum", "iterative qpe", "phase estimation", " qpe")):
        return "quantum_phase_estimation"
    if any(term in normalized for term in ("duality", "linear programming", "optimization", "lp ")):
        return "linear_programming"
    if any(term in normalized for term in ("quantization", "compression", "deployment")):
        return "model_quantization"
    return "general"


def collect_citation_ids(text: str) -> list[str]:
    return re.findall(r"`([^`]+)`", "\n".join(extract_section(text, "Citations")))


def build_candidate_markdown(query: str, card_type: str, citation_ids: list[str], direct_support: list[str]) -> str:
    slug = safe_slug(query)
    lines = [
        "---",
        f"id: distilled-{slug}",
        f"title: {query.title()}",
        f"type: {card_type}",
        "topic: promoted_distillation",
        "tags:",
        "  - promoted",
        "  - distilled",
        "source_refs:",
    ]
    for citation_id in citation_ids:
        lines.append(f"  - {citation_id}")
    lines.extend(
        [
            "confidence: draft",
            "updated_at: 2026-04-01",
            "origin: promoted_from_distilled_note",
            "---",
            "",
            "## Candidate Summary",
            "",
            f"Promoted candidate derived from the distilled note for query: {query}",
            "",
            "## Direct Support",
            "",
        ]
    )
    for line in direct_support:
        lines.append(line)
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    text = args.draft.read_text(encoding="utf-8")
    query = parse_query(text)
    card_type = infer_card_type(query)
    folder = infer_domain_folder(query)
    citation_ids = collect_citation_ids(text)
    direct_support = extract_section(text, "Direct Support")

    output_dir = args.knowledge_root / folder
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"candidate-{safe_slug(query)}.md"
    output_path.write_text(
        build_candidate_markdown(query, card_type, citation_ids, direct_support),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
