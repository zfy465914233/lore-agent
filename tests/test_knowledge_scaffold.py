from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeScaffoldTest(unittest.TestCase):
    def test_knowledge_scaffold_structure_exists(self) -> None:
        expected_paths = [
            ROOT / "templates" / "definition-card.md",
            ROOT / "templates" / "method-card.md",
            ROOT / "templates" / "theorem-card.md",
            ROOT / "templates" / "derivation-card.md",
            ROOT / "templates" / "comparison-card.md",
            ROOT / "templates" / "decision-record.md",
            ROOT / "templates" / "research-note.md",
            ROOT / "tests" / "fixtures" / "example-markov-chain.md",
        ]

        missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]
        self.assertEqual([], missing, f"Missing expected scaffold paths: {missing}")


if __name__ == "__main__":
    unittest.main()
