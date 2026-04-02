from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeScaffoldTest(unittest.TestCase):
    def test_knowledge_directories_templates_and_seed_cards_exist(self) -> None:
        expected_paths = [
            ROOT / "indexes" / "local",
            ROOT / "knowledge" / "markov_chain",
            ROOT / "knowledge" / "qpe",
            ROOT / "knowledge" / "quantum_phase_estimation",
            ROOT / "knowledge" / "linear_programming",
            ROOT / "knowledge" / "model_quantization",
            ROOT / "knowledge" / "templates" / "definition-card.md",
            ROOT / "knowledge" / "templates" / "method-card.md",
            ROOT / "knowledge" / "templates" / "theorem-card.md",
            ROOT / "knowledge" / "templates" / "derivation-card.md",
            ROOT / "knowledge" / "templates" / "comparison-card.md",
            ROOT / "knowledge" / "templates" / "decision-record.md",
            ROOT / "knowledge" / "markov_chain" / "markov-chain-definition.md",
            ROOT / "knowledge" / "markov_chain" / "stationary-distribution-derivation.md",
            ROOT / "knowledge" / "quantum_phase_estimation" / "qpe-error-bound-derivation.md",
            ROOT / "knowledge" / "linear_programming" / "lp-duality-theorem.md",
            ROOT / "knowledge" / "model_quantization" / "quantization-aware-training-method.md",
            ROOT / "knowledge" / "qpe" / "xband-qpe-technical-routes.md",
            ROOT / "knowledge" / "qpe" / "xband-qpe-engineering-pipeline.md",
        ]

        missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]
        self.assertEqual([], missing, f"Missing expected scaffold paths: {missing}")


if __name__ == "__main__":
    unittest.main()
