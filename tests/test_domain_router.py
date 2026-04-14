"""Tests for domain_router.py — dynamic folder matching and AI fallback."""

import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from domain_router import (
    discover_folders,
    folder_tokens,
    match_folder,
    infer_domain,
    clear_folder_cache,
    FOLDER_ALIASES,
)


class TestFolderTokens(unittest.TestCase):
    def test_simple_slug(self):
        tokens = folder_tokens("linear-programming")
        self.assertIn("linear", tokens)
        self.assertIn("programming", tokens)
        self.assertIn("linear-programming", tokens)

    def test_aliases_included(self):
        tokens = folder_tokens("linear-programming")
        for alias in FOLDER_ALIASES["linear-programming"]:
            self.assertIn(alias.lower(), tokens)

    def test_single_word(self):
        tokens = folder_tokens("scheduling")
        self.assertIn("scheduling", tokens)


class TestDiscoverFolders(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / "operations-research").mkdir()
        (self.root / "operations-research" / "linear-programming").mkdir()
        (self.root / "operations-research" / "integer-programming").mkdir()
        (self.root / "probability-statistics").mkdir()
        (self.root / "general").mkdir()
        (self.root / ".hidden").mkdir()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_discovers_top_and_second_level(self):
        folders = discover_folders(self.root)
        self.assertIn("operations-research", folders)
        self.assertIn("linear-programming", folders)
        self.assertIn("integer-programming", folders)
        self.assertIn("probability-statistics", folders)
        self.assertIn("general", folders)

    def test_excludes_hidden_dirs(self):
        folders = discover_folders(self.root)
        self.assertNotIn(".hidden", folders)

    def test_returns_empty_for_missing_root(self):
        folders = discover_folders(Path("/nonexistent"))
        self.assertEqual(folders, {})


class TestMatchFolder(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / "linear-programming").mkdir()
        (self.root / "graph-theory").mkdir()
        (self.root / "probability-statistics").mkdir()
        (self.root / "general").mkdir()
        self.folders = discover_folders(self.root)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_english_match(self):
        self.assertEqual(match_folder("what is linear programming", self.folders), "linear-programming")

    def test_chinese_alias_match(self):
        self.assertEqual(match_folder("线性规划的基本概念", self.folders), "linear-programming")

    def test_abbreviation_match(self):
        self.assertEqual(match_folder("lp simplex method", self.folders), "linear-programming")

    def test_graph_theory_match(self):
        self.assertEqual(match_folder("shortest path in graph theory", self.folders), "graph-theory")

    def test_probability_match(self):
        self.assertEqual(match_folder("概率论基础", self.folders), "probability-statistics")

    def test_no_match_returns_none(self):
        self.assertIsNone(match_folder("quantum computing basics", self.folders))


class TestInferDomain(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / "linear-programming").mkdir()
        (self.root / "general").mkdir()

    def tearDown(self):
        clear_folder_cache()
        self.tmpdir.cleanup()

    def test_matches_existing_folder(self):
        slug, path = infer_domain("linear programming duality", self.root, use_ai_fallback=False)
        self.assertEqual(slug, "linear-programming")

    def test_falls_back_to_general(self):
        slug, path = infer_domain("quantum entanglement", self.root, use_ai_fallback=False)
        self.assertEqual(slug, "general")

    def test_creates_general_if_missing(self):
        root2 = Path(tempfile.mkdtemp())
        try:
            slug, path = infer_domain("unknown topic", root2, use_ai_fallback=False)
            self.assertEqual(slug, "general")
            self.assertTrue(path.exists())
        finally:
            import shutil
            shutil.rmtree(root2)


if __name__ == "__main__":
    unittest.main()
