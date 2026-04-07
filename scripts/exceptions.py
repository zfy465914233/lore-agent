"""Unified exception hierarchy for Lore Agent.

All modules should raise these instead of generic RuntimeError/ValueError
so callers can handle errors uniformly.
"""

from __future__ import annotations


class LoreError(Exception):
    """Base exception for all Lore Agent errors."""


class IndexNotFoundError(LoreError):
    """The knowledge index file does not exist or is unreadable."""


class ResearchError(LoreError):
    """Error during web research or evidence gathering."""


class SynthesisError(LoreError):
    """Error during answer synthesis (LLM call, response parsing)."""


class ValidationError(LoreError):
    """Schema or input validation failure."""


class ConfigurationError(LoreError):
    """Configuration file is missing, malformed, or inconsistent."""
