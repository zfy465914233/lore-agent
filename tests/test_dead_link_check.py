"""Tests for dead-link diagnosis (engine is network-free via urlopen mocking)."""

from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError, URLError

from scholar_agent.engine import dead_link_check as dlc


def _http_error(code: int) -> HTTPError:
    return HTTPError("http://x", code, "err", {}, BytesIO(b""))


class _FakeResp:
    def __init__(self, code: int) -> None:
        self._code = code

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def getcode(self) -> int:
        return self._code


class TestClassify(unittest.TestCase):
    def test_ok_range(self) -> None:
        self.assertEqual(dlc._classify(200), "ok")
        self.assertEqual(dlc._classify(301), "ok")
        self.assertEqual(dlc._classify(399), "ok")

    def test_dead(self) -> None:
        self.assertEqual(dlc._classify(404), "dead")
        self.assertEqual(dlc._classify(410), "dead")
        self.assertEqual(dlc._classify(403), "dead")  # other 4xx

    def test_transient(self) -> None:
        self.assertEqual(dlc._classify(429), "transient")
        self.assertEqual(dlc._classify(500), "transient")
        self.assertEqual(dlc._classify(503), "transient")


class TestIsBlocked(unittest.TestCase):
    def test_blocked_subdomain(self) -> None:
        from scholar_agent.engine.common import is_blocked_host

        self.assertEqual(
            is_blocked_host("https://www.sciencedirect.com/science/article/pii/x"),
            "sciencedirect.com",
        )

    def test_not_blocked(self) -> None:
        from scholar_agent.engine.common import is_blocked_host

        self.assertIsNone(is_blocked_host("https://arxiv.org/abs/1234.5678"))


@mock.patch("scholar_agent.engine.retry.time.sleep", lambda *a, **k: None)
class TestCheckOneUrl(unittest.TestCase):
    def test_head_ok(self) -> None:
        with mock.patch.object(dlc, "urlopen", return_value=_FakeResp(200)):
            r = dlc.check_one_url("https://arxiv.org/abs/1", timeout=2)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["status_code"], 200)

    def test_head_405_falls_back_to_get(self) -> None:
        calls: list[str] = []

        def fake(req: object, timeout: float = 10) -> _FakeResp:
            method = req.get_method()  # type: ignore[attr-defined]
            calls.append(method)
            if method == "HEAD":
                raise _http_error(405)
            return _FakeResp(200)

        with mock.patch.object(dlc, "urlopen", side_effect=fake):
            r = dlc.check_one_url("https://example.com/x", timeout=2)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(calls, ["HEAD", "GET"])

    def test_dead_404(self) -> None:
        with mock.patch.object(dlc, "urlopen", side_effect=lambda *a, **k: _raise(_http_error(404))):
            r = dlc.check_one_url("https://example.com/missing", timeout=2)
        self.assertEqual(r["status"], "dead")
        self.assertEqual(r["status_code"], 404)

    def test_blocked_domain_skips_network(self) -> None:
        with mock.patch.object(dlc, "urlopen", side_effect=AssertionError("must not call")):
            r = dlc.check_one_url("https://www.nature.com/articles/x", timeout=2)
        self.assertEqual(r["status"], "blocked")

    def test_transient_url_error(self) -> None:
        with mock.patch.object(dlc, "urlopen", side_effect=lambda *a, **k: _raise(URLError("refused"))):
            r = dlc.check_one_url("https://example.com/x", timeout=2)
        self.assertEqual(r["status"], "transient")

    def test_transient_503_retries_then_reports(self) -> None:
        calls = {"n": 0}

        def fake(req: object, timeout: float = 10) -> _FakeResp:
            calls["n"] += 1
            raise _http_error(503)

        with mock.patch.object(dlc, "urlopen", side_effect=fake):
            r = dlc.check_one_url("https://example.com/x", timeout=2)
        self.assertEqual(r["status"], "transient")
        self.assertGreater(calls["n"], 1)  # actually retried


def _raise(exc: BaseException):
    raise exc


class TestCheckDeadLinks(unittest.TestCase):
    def _write_card(self, directory: Path, name: str, urls: list[str]) -> Path:
        lines = ["---", f"id: {name[:-3]}", "title: T", "type: knowledge", "topic: x"]
        if urls:
            lines.append("source_refs:")
            for u in urls:
                lines.append(f"  - {u}")
        else:
            lines.append("source_refs: []")
        lines += ["---", "", "body content " * 40]
        path = directory / name
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def test_offline_marks_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            kd = Path(d)
            self._write_card(kd, "a.md", ["https://example.com/x"])
            res = dlc.check_dead_links(kd, offline=True)
        self.assertEqual(res["urls_checked"], 1)
        self.assertEqual(res["cards_checked"], 1)
        self.assertTrue(all(r["status"] == "skipped" for r in res["results"]))

    def test_dedup_same_url_across_cards(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            kd = Path(d)
            self._write_card(kd, "a.md", ["https://example.com/x"])
            self._write_card(kd, "b.md", ["https://example.com/x"])
            with mock.patch.object(
                dlc,
                "check_one_url",
                return_value={"url": "https://example.com/x", "status": "dead", "status_code": 404, "reason": ""},
            ):
                res = dlc.check_dead_links(kd)
        self.assertEqual(res["urls_checked"], 1)  # probed once
        self.assertEqual(res["dead_count"], 2)  # fanned out to both cards
        self.assertEqual(len(res["results"]), 2)
        self.assertEqual(res["summary"]["dead"], 2)

    def test_empty_knowledge_dir(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            res = dlc.check_dead_links(Path(d))
        self.assertEqual(res["urls_checked"], 0)
        self.assertEqual(res["cards_checked"], 0)
        self.assertEqual(res["results"], [])

    def test_reserved_dirs_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            kd = Path(d)
            snap = kd / "_snapshots"
            snap.mkdir()
            (snap / "s.md").write_text(
                "---\nurl: https://example.com/s\nsource_refs:\n  - https://example.com/s\n---\nbody",
                encoding="utf-8",
            )
            res = dlc.check_dead_links(kd)
        self.assertEqual(res["cards_checked"], 0)  # _snapshots excluded
        self.assertEqual(res["urls_checked"], 0)


if __name__ == "__main__":
    unittest.main()
