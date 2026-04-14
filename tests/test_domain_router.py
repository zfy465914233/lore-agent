"""Tests for domain_router.py — domain/topic routing and AI fallback."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from domain_router import _build_routing_prompt, _propose_new_major_domain, clear_folder_cache, discover_domain_tree, infer_domain, infer_domain_decision, infer_domain_with_ai, load_routing_guide, load_routing_policy, match_route


class TestDiscoverDomainTree(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / "operations-research").mkdir()
        (self.root / "operations-research" / "inventory-planning").mkdir()
        (self.root / "operations-research" / "knowledge-root-card.md").write_text("---\nid: root\n---\n", encoding="utf-8")
        (self.root / "llm").mkdir()
        (self.root / "llm" / "mixture-of-experts").mkdir()
        (self.root / "general").mkdir()
        (self.root / ".hidden").mkdir()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_discovers_major_and_subdomain_levels(self):
        domain_tree = discover_domain_tree(self.root)
        self.assertIn("operations-research", domain_tree)
        self.assertIn("inventory-planning", domain_tree["operations-research"])
        self.assertIn("", domain_tree["operations-research"])
        self.assertIn("llm", domain_tree)
        self.assertIn("mixture-of-experts", domain_tree["llm"])
        self.assertIn("general", domain_tree)

    def test_excludes_hidden_dirs(self):
        domain_tree = discover_domain_tree(self.root)
        self.assertNotIn(".hidden", domain_tree)

    def test_returns_empty_for_missing_root(self):
        self.assertEqual(discover_domain_tree(Path("/nonexistent")), {})


class TestMatchRoute(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / "operations-research").mkdir()
        (self.root / "operations-research" / "inventory-planning").mkdir()
        (self.root / "llm").mkdir()
        (self.root / "llm" / "mixture-of-experts").mkdir()
        self.policy = load_routing_policy()
        self.domain_tree = discover_domain_tree(self.root)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_matches_inventory_planning(self):
        self.assertEqual(
            match_route("安全库存和再订货点怎么理解", self.policy, self.domain_tree),
            ("operations-research", "inventory-planning"),
        )

    def test_matches_major_root_when_no_specific_subdomain(self):
        self.assertEqual(
            match_route("运筹学优化建模基础", self.policy, self.domain_tree),
            ("operations-research", None),
        )

    def test_matches_moe(self):
        self.assertEqual(
            match_route("MoE routing and load balancing", self.policy, self.domain_tree),
            ("llm", "mixture-of-experts"),
        )

    def test_no_match_returns_none(self):
        self.assertIsNone(match_route("renaissance painting basics", self.policy, self.domain_tree))


class TestInferDomain(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / "operations-research").mkdir()
        (self.root / "operations-research" / "inventory-planning").mkdir()
        (self.root / "general").mkdir()

    def tearDown(self):
        clear_folder_cache()
        self.tmpdir.cleanup()

    def test_matches_existing_folder(self):
        slug, path = infer_domain("库存规划框架怎么搭", self.root, use_ai_fallback=False)
        self.assertEqual(slug, "operations-research/inventory-planning")
        self.assertEqual(path, self.root / "operations-research" / "inventory-planning")

    def test_falls_back_to_new_major_root(self):
        slug, path = infer_domain("quantum entanglement", self.root, use_ai_fallback=False)
        self.assertEqual(slug, "quantum-entanglement")
        self.assertEqual(path, self.root / "quantum-entanglement")

    def test_creates_general_if_missing(self):
        root2 = Path(tempfile.mkdtemp())
        try:
            slug, path = infer_domain("unknown topic", root2, use_ai_fallback=False)
            self.assertEqual(slug, "unknown-topic")
            self.assertTrue(path.exists())
        finally:
            import shutil
            shutil.rmtree(root2)

    def test_uses_ai_fallback_when_available(self):
        with patch("domain_router.infer_domain_with_ai", return_value={"major_domain": "llm", "subdomain": "mixture-of-experts", "reason": "best fit"}):
            slug, path = infer_domain("switch transformer routing", self.root, use_ai_fallback=True)
        self.assertEqual(slug, "llm/mixture-of-experts")
        self.assertTrue(path.exists())

    def test_decision_contains_reason_and_mode(self):
        decision = infer_domain_decision("库存规划框架怎么搭", self.root, use_ai_fallback=False)
        self.assertEqual(decision["major_domain"], "operations-research")
        self.assertEqual(decision["subdomain"], "inventory-planning")
        self.assertEqual(decision["decision_mode"], "policy_match")


class TestInferDomainWithAi(unittest.TestCase):
    def test_returns_none_without_api_credentials(self):
        with patch("domain_router._router_api_key", return_value=""):
            self.assertIsNone(infer_domain_with_ai("unknown topic", load_routing_policy(), {"general": {"general": Path("general/general")}}))

    def test_uses_openai_compatible_response(self):
        with patch("domain_router._call_router_llm", return_value='{"major_domain": "llm", "subdomain": "mixture-of-experts", "reason": "MoE topic"}'):
            route = infer_domain_with_ai("switch transformer routing", load_routing_policy(), {"llm": {"mixture-of-experts": Path("llm/mixture-of-experts")}})
        self.assertEqual(route, {"major_domain": "llm", "subdomain": "mixture-of-experts", "reason": "MoE topic"})

    def test_accepts_new_major_domain_response(self):
        with patch("domain_router._call_router_llm", return_value='{"major_domain": "quantum-computing", "subdomain": "", "reason": "new domain"}'):
            route = infer_domain_with_ai("量子纠缠的工程应用", load_routing_policy(), {"llm": {"mixture-of-experts": Path("llm/mixture-of-experts")}})
        self.assertEqual(route, {"major_domain": "quantum-computing", "subdomain": "", "reason": "new domain"})

    def test_rejects_non_slug_responses(self):
        with patch("domain_router._call_router_llm", return_value='{"major_domain": "llm", "subdomain": "bad slug", "reason": "invalid"}'):
            route = infer_domain_with_ai("switch transformer routing", load_routing_policy(), {"llm": {"mixture-of-experts": Path("llm/mixture-of-experts")}})
        self.assertIsNone(route)


class TestRoutingGuide(unittest.TestCase):
    def test_load_routing_guide(self):
        guide = load_routing_guide()
        self.assertIn("Target Structure", guide)
        self.assertIn("operations-research", guide)

    def test_build_prompt_includes_guide_and_tree(self):
        prompt = _build_routing_prompt(
            "安全库存和再订货点怎么理解",
            load_routing_policy(),
            {"operations-research": {"inventory-planning": Path("knowledge/operations-research/inventory-planning")}},
            "Follow the guide.",
        )
        self.assertIn("Follow the guide.", prompt)
        self.assertIn("inventory-planning", prompt)
        self.assertIn("major_domain", prompt)
        self.assertIn("Routing policy JSON", prompt)

    def test_guide_contains_few_shot_examples(self):
        guide = load_routing_guide()
        self.assertIn("Few-shot Examples", guide)
        self.assertIn("quantum-computing", guide)


class TestNewMajorFallback(unittest.TestCase):
    def test_propose_new_major_domain_from_english_query(self):
        self.assertEqual(_propose_new_major_domain("quantum entanglement basics"), "quantum-entanglement-basics")

    def test_propose_new_major_domain_from_chinese_query(self):
        self.assertEqual(_propose_new_major_domain("量子纠缠的工程应用"), "量子纠缠的工程应用")


if __name__ == "__main__":
    unittest.main()
