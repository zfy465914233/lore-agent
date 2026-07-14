"""CCF venue ranking (representative CS subset) for paper scoring.

Maps a venue string — typically Semantic Scholar's ``publicationVenue.name`` or
a conference acronym — to a CCF A/B/C rank. Returns ``None`` for unknown venues
and for arXiv preprints (which carry no peer-reviewed venue).

This is a deliberately curated subset of the CCF catalogue covering the venues
that dominate our arXiv-heavy corpus (CV/NLP/ML/AI/DM). It is not exhaustive;
unknown venues simply get no bonus (``PaperScorer`` never penalizes them).
"""

from __future__ import annotations

import re

# Each entry: (substring patterns that identify the venue, CCF rank, label).
# Patterns are matched as space-padded whole tokens against the normalized
# venue string, so "kdd" won't match inside "akddl" but will match "KDD 2023".
_VENUES: list[tuple[tuple[str, ...], str, str]] = [
    # --- CCF A (conferences) ---
    (("computer vision and pattern recognition", "cvpr"), "A", "CVPR"),
    (("international conference on computer vision", "iccv"), "A", "ICCV"),
    (("international conference on machine learning", "icml"), "A", "ICML"),
    (("neural information processing systems", "neurips", "nips"), "A", "NeurIPS"),
    (("learning representations", "iclr"), "A", "ICLR"),
    (("aaai",), "A", "AAAI"),
    (("ijcai",), "A", "IJCAI"),
    (
        ("association for computational linguistics", "annual meeting of the acl", "acl"),
        "A",
        "ACL",
    ),
    (("knowledge discovery and data mining", "sigkdd", "kdd"), "A", "SIGKDD"),
    (("world wide web", "the web conference"), "A", "WWW"),
    # --- CCF A (journals) ---
    (("pattern analysis and machine intelligence", "tpami"), "A", "TPAMI"),
    (("international journal of computer vision", "ijcv"), "A", "IJCV"),
    (("journal of machine learning research", "jmlr"), "A", "JMLR"),
    # --- CCF B ---
    (("european conference on computer vision", "eccv"), "B", "ECCV"),
    (
        ("empirical methods in natural language processing", "emnlp"),
        "B",
        "EMNLP",
    ),
    (
        ("north american association for computational linguistics", "naacl"),
        "B",
        "NAACL",
    ),
    (
        ("research and development in information retrieval", "sigir"),
        "B",
        "SIGIR",
    ),
    (("information and knowledge management", "cikm"), "B", "CIKM"),
    (("web search and data mining", "wsdm"), "B", "WSDM"),
    (("computer vision and image understanding", "cviu"), "B", "CVIU"),
    (
        ("transactions of the association for computational linguistics", "tacl"),
        "B",
        "TACL",
    ),
    (("ieee international conference on robotics and automation", "icra"), "B", "ICRA"),
    (("pattern recognition",), "B", "Pattern Recognition"),
    # --- CCF C ---
    (("ieee international conference on data mining", "icdm"), "C", "ICDM"),
    (("intelligent robots and systems", "iros"), "C", "IROS"),
]


def _normalize(venue: str) -> str:
    """Lowercase, collapse whitespace, pad for whole-token substring checks."""
    text = re.sub(r"\s+", " ", venue.lower()).strip()
    return f" {text} "


def rank_venue(venue: str | None) -> dict[str, str | None]:
    """Map a venue string to a CCF rank.

    Returns ``{"rank": "A"|"B"|"C"|None, "matched": label|None}``. arXiv and
    empty inputs return ``{"rank": None, "matched": None}``.
    """
    if not venue:
        return {"rank": None, "matched": None}
    norm = _normalize(venue)
    if "arxiv" in norm:
        return {"rank": None, "matched": None}
    for patterns, rank, label in _VENUES:
        if any(f" {p} " in norm for p in patterns):
            return {"rank": rank, "matched": label}
    return {"rank": None, "matched": None}
