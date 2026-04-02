import json
import subprocess
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "indexes" / "local" / "index.json"


class XBandQpeCardsTest(unittest.TestCase):
    def setUp(self) -> None:
        build_result = subprocess.run(
            [sys.executable, "scripts/local_index.py", "--output", str(INDEX_PATH)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if build_result.returncode != 0:
            self.fail(
                f"failed to build index for x-band qpe card test: "
                f"stdout={build_result.stdout!r} stderr={build_result.stderr!r}"
            )

    def test_xband_qpe_cards_are_indexed(self) -> None:
        payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        doc_ids = {doc["doc_id"] for doc in payload["documents"]}
        self.assertIn("xband-qpe-technical-routes", doc_ids)
        self.assertIn("xband-qpe-engineering-pipeline", doc_ids)

    def test_xband_qpe_cards_are_retrievable(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/local_retrieve.py",
                "x band radar qpe technical route",
                "--index",
                str(INDEX_PATH),
                "--limit",
                "5",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr)
        payload = json.loads(result.stdout)
        doc_ids = [item["doc_id"] for item in payload["results"]]
        self.assertIn("xband-qpe-technical-routes", doc_ids)


if __name__ == "__main__":
    unittest.main()
