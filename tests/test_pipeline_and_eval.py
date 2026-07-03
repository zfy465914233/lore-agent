"""Tests for run_pipeline.py and run_eval.py — end-to-end integration."""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[1]

ENGINE = _ROOT / "src" / "scholar_agent" / "engine"
INDEX_PATH = _ROOT / "indexes" / "local" / "index.json"
FAKE_HARNESS = _ROOT / "tests" / "fake_research_harness.py"


def _ensure_index() -> None:
    if INDEX_PATH.exists():
        return
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scholar_agent.engine.local_index",
            "--knowledge-root",
            str(_ROOT / "tests" / "fixtures"),
            "--output",
            str(INDEX_PATH),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, f"Index build failed: {result.stderr}"


class PipelineDryRunTest(unittest.TestCase):
    """Test the full pipeline in dry-run mode (no LLM calls)."""

    @classmethod
    def setUpClass(cls) -> None:
        _ensure_index()

    def test_pipeline_dry_run_local_led(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scholar_agent.engine.run_pipeline",
                "what is a markov chain",
                "--mode",
                "auto",
                "--index",
                str(INDEX_PATH),
                "--research-script",
                str(FAKE_HARNESS),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(0, result.returncode, msg=result.stderr)
        payload = json.loads(result.stdout)

        self.assertEqual("what is a markov chain", payload["query"])
        self.assertEqual("dry_run", payload["pipeline_status"])
        self.assertEqual("local-led", payload["route"])
        self.assertGreaterEqual(payload["answer_context_summary"]["direct_support_count"], 1)
        self.assertIn("prompt_bundle", payload)
        self.assertIn("system_prompt", payload["prompt_bundle"])

    def test_pipeline_dry_run_web_led(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scholar_agent.engine.run_pipeline",
                "latest SOTA quantization methods",
                "--mode",
                "auto",
                "--index",
                str(INDEX_PATH),
                "--research-script",
                str(FAKE_HARNESS),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(0, result.returncode, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("web-led", payload["route"])

    def test_pipeline_keep_intermediate(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scholar_agent.engine.run_pipeline",
                "what is a markov chain",
                "--mode",
                "local-led",
                "--index",
                str(INDEX_PATH),
                "--dry-run",
                "--keep-intermediate",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(0, result.returncode, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("intermediate", payload)
        self.assertIn("answer_context", payload["intermediate"])
        self.assertIn("prompt_bundle", payload["intermediate"])

    def test_run_pipeline_default_index_uses_runtime_config(self) -> None:
        from scholar_agent.engine import run_pipeline as pipeline_module

        configured_index = Path("/tmp/configured-index.json")
        context_stdout = json.dumps(
            {
                "query": "ambiguous query",
                "route": "mixed",
                "direct_support": [],
                "citations": [],
                "uncertainty_notes": [],
            }
        )
        prompt_stdout = json.dumps({"system_prompt": "system", "citations": []})

        def fake_run(script: str, args: list[str], stdin_data: str | None = None) -> subprocess.CompletedProcess[str]:
            if script == "build_answer_context.py":
                self.assertIn("--index", args)
                self.assertEqual(str(configured_index), args[args.index("--index") + 1])
                return subprocess.CompletedProcess(args=[script, *args], returncode=0, stdout=context_stdout, stderr="")
            if script == "render_answer_bundle.py":
                self.assertEqual(context_stdout, stdin_data)
                return subprocess.CompletedProcess(args=[script, *args], returncode=0, stdout=prompt_stdout, stderr="")
            self.fail(f"Unexpected subprocess stage: {script}")

        with (
            patch.object(pipeline_module, "_default_index_path", return_value=configured_index),
            patch.object(pipeline_module, "_run", side_effect=fake_run),
        ):
            payload = pipeline_module.run_pipeline("ambiguous query", dry_run=True)

        self.assertEqual("dry_run", payload["pipeline_status"])
        self.assertEqual("mixed", payload["route"])


class EvalRunnerTest(unittest.TestCase):
    """Test the evaluation runner."""

    @classmethod
    def setUpClass(cls) -> None:
        _ensure_index()

    def test_eval_dry_run_all(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "scholar_agent.engine.run_eval", "--dry-run", "--index", str(INDEX_PATH)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(0, result.returncode, msg=result.stderr)
        report = json.loads(result.stdout)

        summary = report["summary"]
        self.assertTrue(summary["dry_run"])
        self.assertGreaterEqual(summary["total_cases"], 5)
        self.assertGreater(summary["route_accuracy"], 0.5)
        self.assertGreater(summary["retrieval_hit_rate"], 0.1)

    def test_eval_dry_run_single_category(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scholar_agent.engine.run_eval",
                "--dry-run",
                "--category",
                "definition",
                "--index",
                str(INDEX_PATH),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(0, result.returncode, msg=result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(3, report["summary"]["total_cases"])
        # All definition cases should route to local-led
        self.assertEqual(1.0, report["summary"]["route_accuracy"])

    def test_eval_by_category_breakdown(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "scholar_agent.engine.run_eval", "--dry-run", "--index", str(INDEX_PATH)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(0, result.returncode, msg=result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("by_category", report)
        self.assertIn("definition", report["by_category"])

    def test_run_eval_default_index_uses_runtime_config(self) -> None:
        from scholar_agent.engine import run_eval as eval_module

        configured_index = Path("/tmp/configured-eval-index.json")

        with (
            patch("sys.argv", ["run_eval", "--dry-run"]),
            patch.object(eval_module, "get_index_path", return_value=configured_index),
        ):
            args = eval_module.parse_args()

        self.assertEqual(configured_index, args.index)


if __name__ == "__main__":
    unittest.main()
