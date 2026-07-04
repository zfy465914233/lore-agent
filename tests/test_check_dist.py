from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_dist.py"


def _load_check_dist_module():
    spec = importlib.util.spec_from_file_location("check_dist", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_sdist(path: Path, files: dict[str, str]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, content in sorted(files.items()):
            payload = content.encode()
            info = tarfile.TarInfo(f"py_scholar_agent-0.1.0/{name}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))


def _write_wheel(path: Path, files: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in sorted(files.items()):
            archive.writestr(name, content)


def _run_check_dist(dist_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--dist-dir", str(dist_dir)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_check_dist_accepts_valid_sdist_and_wheel(tmp_path: Path) -> None:
    check_dist = _load_check_dist_module()
    _write_sdist(tmp_path / "py_scholar_agent-0.1.0.tar.gz", dict.fromkeys(check_dist.REQUIRED_SDIST_PATHS, "x"))
    _write_wheel(
        tmp_path / "py_scholar_agent-0.1.0-py3-none-any.whl",
        dict.fromkeys(check_dist.REQUIRED_WHEEL_PATHS, "x"),
    )

    result = _run_check_dist(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "sdist py_scholar_agent-0.1.0.tar.gz" in result.stdout
    assert "wheel py_scholar_agent-0.1.0-py3-none-any.whl" in result.stdout
    assert "forbidden 0" in result.stdout
    assert "missing_required 0" in result.stdout


def test_check_dist_rejects_tests_and_missing_required_files(tmp_path: Path) -> None:
    check_dist = _load_check_dist_module()
    sdist_files = dict.fromkeys(check_dist.REQUIRED_SDIST_PATHS, "x")
    sdist_files["tests/test_leak.py"] = "x"
    wheel_files = dict.fromkeys(check_dist.REQUIRED_WHEEL_PATHS, "x")
    wheel_files.pop("scholar_agent/templates/knowledge-card-template.md")

    _write_sdist(tmp_path / "py_scholar_agent-0.1.0.tar.gz", sdist_files)
    _write_wheel(tmp_path / "py_scholar_agent-0.1.0-py3-none-any.whl", wheel_files)

    result = _run_check_dist(tmp_path)

    assert result.returncode == 1
    assert "forbidden: py_scholar_agent-0.1.0/tests/test_leak.py" in result.stdout
    assert "missing required: scholar_agent/templates/knowledge-card-template.md" in result.stdout
