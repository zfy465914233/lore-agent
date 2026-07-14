"""Tests for CCF venue ranking (normalization, matching, edge cases)."""

from __future__ import annotations

import unittest

from scholar_agent.engine.academic.venue_ranking import rank_venue


class TestRankVenue(unittest.TestCase):
    def test_long_form_cvpr(self) -> None:
        r = rank_venue("IEEE/CVF Conference on Computer Vision and Pattern Recognition")
        self.assertEqual(r["rank"], "A")
        self.assertEqual(r["matched"], "CVPR")

    def test_acronyms(self) -> None:
        self.assertEqual(rank_venue("NeurIPS")["rank"], "A")
        self.assertEqual(rank_venue("ICLR")["rank"], "A")
        self.assertEqual(rank_venue("ACL")["rank"], "A")

    def test_journal_tpami(self) -> None:
        r = rank_venue("IEEE Transactions on Pattern Analysis and Machine Intelligence")
        self.assertEqual(r["rank"], "A")
        self.assertEqual(r["matched"], "TPAMI")

    def test_ccf_c(self) -> None:
        self.assertEqual(rank_venue("IEEE International Conference on Data Mining")["rank"], "C")

    def test_arxiv_is_none(self) -> None:
        self.assertIsNone(rank_venue("arXiv.org")["rank"])

    def test_empty_and_unknown(self) -> None:
        self.assertIsNone(rank_venue("")["rank"])
        self.assertIsNone(rank_venue(None)["rank"])
        self.assertIsNone(rank_venue("Workshop on Obscure Topics")["rank"])

    def test_no_false_positive_on_substring(self) -> None:
        # padded " kdd " must not match inside the token "akddl"
        self.assertIsNone(rank_venue("AKDDL conference")["rank"])


if __name__ == "__main__":
    unittest.main()
