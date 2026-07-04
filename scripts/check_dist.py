"""Validate source and wheel distribution artifacts."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

FORBIDDEN_MARKERS = ("__pycache__", ".DS_Store")
FORBIDDEN_SUFFIXES = (".pyc", ".pyo")

REQUIRED_SDIST_PATHS = frozenset(
    {
        ".scholar.example.json",
        "CONTRIBUTING.md",
        "README.zh-CN.md",
        "assets/banner.svg",
        "assets/demo.gif",
        "docs/comparison.md",
        "src/scholar_agent/engine/clock.py",
        "src/scholar_agent/schemas/answer.schema.json",
        "src/scholar_agent/skills/scholar-agent/SKILL.md",
        "src/scholar_agent/templates/knowledge-card-template.md",
        "src/scholar_agent/validation/validate_note.py",
    }
)

REQUIRED_WHEEL_PATHS = frozenset(
    {
        "scholar_agent/engine/clock.py",
        "scholar_agent/schemas/answer.schema.json",
        "scholar_agent/skills/scholar-agent/SKILL.md",
        "scholar_agent/templates/knowledge-card-template.md",
        "scholar_agent/validation/validate_note.py",
    }
)


@dataclass(frozen=True)
class ArtifactReport:
    kind: str
    path: Path
    entry_count: int
    forbidden_paths: tuple[str, ...]
    missing_required_paths: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.forbidden_paths and not self.missing_required_paths


def _strip_sdist_root(path: str) -> str:
    parts = path.split("/", 1)
    if len(parts) == 1:
        return ""
    return parts[1]


def _is_forbidden(logical_path: str) -> bool:
    if not logical_path:
        return False
    if logical_path == "tests" or logical_path.startswith("tests/"):
        return True
    return any(marker in logical_path for marker in FORBIDDEN_MARKERS) or logical_path.endswith(FORBIDDEN_SUFFIXES)


def _build_report(
    *,
    kind: str,
    path: Path,
    entry_names: list[str],
    logical_names: list[str],
    required_paths: frozenset[str],
) -> ArtifactReport:
    logical_name_set = set(logical_names)
    forbidden = tuple(
        sorted({entry for entry, logical in zip(entry_names, logical_names, strict=True) if _is_forbidden(logical)})
    )
    missing = tuple(sorted(required_paths - logical_name_set))
    return ArtifactReport(
        kind=kind,
        path=path,
        entry_count=len(entry_names),
        forbidden_paths=forbidden,
        missing_required_paths=missing,
    )


def inspect_sdist(path: Path) -> ArtifactReport:
    with tarfile.open(path, "r:gz") as archive:
        entry_names = archive.getnames()
    logical_names = [_strip_sdist_root(name) for name in entry_names]
    return _build_report(
        kind="sdist",
        path=path,
        entry_names=entry_names,
        logical_names=logical_names,
        required_paths=REQUIRED_SDIST_PATHS,
    )


def inspect_wheel(path: Path) -> ArtifactReport:
    with zipfile.ZipFile(path) as archive:
        entry_names = archive.namelist()
    logical_names = [name.rstrip("/") for name in entry_names]
    return _build_report(
        kind="wheel",
        path=path,
        entry_names=entry_names,
        logical_names=logical_names,
        required_paths=REQUIRED_WHEEL_PATHS,
    )


def check_dist(dist_dir: Path) -> list[ArtifactReport]:
    sdist_paths = sorted(dist_dir.glob("*.tar.gz"))
    wheel_paths = sorted(dist_dir.glob("*.whl"))

    reports: list[ArtifactReport] = []
    reports.extend(inspect_sdist(path) for path in sdist_paths)
    reports.extend(inspect_wheel(path) for path in wheel_paths)
    return reports


def _print_report(report: ArtifactReport) -> None:
    print(
        f"{report.kind} {report.path.name}: "
        f"entries {report.entry_count}, "
        f"forbidden {len(report.forbidden_paths)}, "
        f"missing_required {len(report.missing_required_paths)}"
    )
    for forbidden_path in report.forbidden_paths:
        print(f"  forbidden: {forbidden_path}")
    for missing_path in report.missing_required_paths:
        print(f"  missing required: {missing_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate built sdist and wheel artifacts.")
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"), help="Directory containing built artifacts.")
    args = parser.parse_args(argv)

    reports = check_dist(args.dist_dir)
    for report in reports:
        _print_report(report)

    has_sdist = any(report.kind == "sdist" for report in reports)
    has_wheel = any(report.kind == "wheel" for report in reports)
    if not has_sdist:
        print(f"missing artifact: no source distribution (*.tar.gz) found in {args.dist_dir}")
    if not has_wheel:
        print(f"missing artifact: no wheel (*.whl) found in {args.dist_dir}")

    if not has_sdist or not has_wheel:
        return 1
    return 0 if all(report.ok for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
