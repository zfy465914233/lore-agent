"""Tests for grounding rules: evidence-id stripping + overclaim downgrade."""

from __future__ import annotations

import unittest

from scholar_agent.engine.synthesize_answer import ANSWER_SYSTEM_PROMPT, validate_claims


def _has_downgrade_warning(out: dict) -> bool:
    return any("downgraded" in w.lower() for w in out.get("uncertainty", []))


class TestValidateClaimsGrounding(unittest.TestCase):
    def test_strips_invalid_evidence_ids(self) -> None:
        ans = {
            "supporting_claims": [
                {"claim": "x" * 25, "evidence_ids": ["e1", "e9"], "confidence": "high"}
            ],
            "uncertainty": [],
        }
        out = validate_claims(ans, {"e1"})
        self.assertEqual(out["supporting_claims"][0]["evidence_ids"], ["e1"])
        self.assertTrue(any("non-existent" in w for w in out.get("uncertainty", [])))

    def test_high_with_absolute_language_downgraded(self) -> None:
        ans = {
            "supporting_claims": [
                {
                    "claim": "This method always proves the theorem conclusively.",
                    "evidence_ids": ["e1"],
                    "confidence": "high",
                }
            ],
            "uncertainty": [],
        }
        out = validate_claims(ans, {"e1"})
        self.assertEqual(out["supporting_claims"][0]["confidence"], "medium")
        self.assertTrue(_has_downgrade_warning(out))

    def test_high_without_absolute_language_kept(self) -> None:
        ans = {
            "supporting_claims": [
                {
                    "claim": "The method achieves 92% accuracy on the held-out test set.",
                    "evidence_ids": ["e1"],
                    "confidence": "high",
                }
            ],
            "uncertainty": [],
        }
        out = validate_claims(ans, {"e1"})
        self.assertEqual(out["supporting_claims"][0]["confidence"], "high")
        self.assertFalse(_has_downgrade_warning(out))

    def test_medium_not_downgraded_even_if_absolute(self) -> None:
        ans = {
            "supporting_claims": [
                {
                    "claim": "This always works conclusively without doubt.",
                    "evidence_ids": ["e1"],
                    "confidence": "medium",
                }
            ],
            "uncertainty": [],
        }
        out = validate_claims(ans, {"e1"})
        self.assertEqual(out["supporting_claims"][0]["confidence"], "medium")
        self.assertFalse(_has_downgrade_warning(out))

    def test_prompt_contains_grounding_rules(self) -> None:
        # Soft guard: the four grounding prohibitions ship in the system prompt.
        self.assertIn("Grounding rules", ANSWER_SYSTEM_PROMPT)
        self.assertIn("overclaim", ANSWER_SYSTEM_PROMPT.lower())
        self.assertIn("extrapolate", ANSWER_SYSTEM_PROMPT.lower())


if __name__ == "__main__":
    unittest.main()
