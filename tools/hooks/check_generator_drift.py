"""pre-commit hook that verifies Wave generator outputs are committed."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = Path("backlog/wave3.yaml")
DEFAULT_TIMEZONE = "America/Phoenix"
GENERATED_PATHS: tuple[str, ...] = ("docs/mop", "docs/sub-prompts", "artifacts")
HOOK_MARKER_FILENAME = ".releasecopilot_hook_requirements_installed"
REQUIRED_MODULES: tuple[str, ...] = ("jinja2", "slugify", "yaml", "requests")


def _should_install_requirements() -> bool:
    if os.environ.get("PRE_COMMIT") == "1":
        return True
    prefix = Path(sys.prefix)
    return "pre-commit" in prefix.as_posix()


def _ensure_requirements_installed() -> None:
    if not _should_install_requirements():
        return

    marker_dir = Path(sys.prefix)
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker_path = marker_dir / HOOK_MARKER_FILENAME
    if marker_path.exists():
        return

    missing = _missing_modules()
    if not missing:
        marker_path.write_text("installed", encoding="utf-8")
        return

    requirements_path = REPO_ROOT / "tools/hooks/requirements.txt"
    if not requirements_path.is_file():
        raise RuntimeError(
            "Missing hook requirements file while packages are absent: "
            f"{requirements_path}"
        )

    subprocess.run(
        (
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            requirements_path.as_posix(),
        ),
        check=True,
        text=True,
    )
    marker_path.write_text("installed", encoding="utf-8")


def _missing_modules() -> list[str]:
    missing: list[str] = []
    for module in REQUIRED_MODULES:
        if importlib.util.find_spec(module) is None:
            missing.append(module)
    return missing


class DriftDetectedError(RuntimeError):
    """Raised when the generator introduces uncommitted changes."""


def _run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd or REPO_ROOT),
        env=_build_env(env),
        check=True,
        text=True,
    )


def _build_env(extra_env: dict[str, str] | None = None) -> dict[str, str]:
    env: dict[str, str] = os.environ.copy()
    src_path = (REPO_ROOT / "src").as_posix()
    existing = env.get("PYTHONPATH")
    if existing:
        paths = [part for part in existing.split(os.pathsep) if part]
    else:
        paths = []

    paths = [part for part in paths if part != src_path]
    paths.insert(0, src_path)
    env["PYTHONPATH"] = os.pathsep.join(paths) if paths else src_path

    if extra_env:
        env.update(extra_env)

    return env


def _should_skip() -> bool:
    return os.environ.get("RELEASECOPILOT_SKIP_GENERATOR", "0") == "1"


def run_generator(*, spec: Path = DEFAULT_SPEC, timezone: str = DEFAULT_TIMEZONE) -> None:
    command = (
        sys.executable,
        "main.py",
        "generate",
        "--spec",
        spec.as_posix(),
        "--timezone",
        timezone,
        "--archive",
    )
    _run(command)


def assert_clean_git_diff(paths: Sequence[str] = GENERATED_PATHS) -> None:
    command = ("git", "diff", "--stat", "--exit-code", *paths)
    try:
        _run(command)
    except subprocess.CalledProcessError as error:  # pragma: no cover - defensive guard
        raise DriftDetectedError(
            "Generator drift detected. Run 'python main.py generate --spec "
            "backlog/wave3.yaml --timezone America/Phoenix --archive'"
        ) from error


def main(argv: Sequence[str] | None = None) -> int:
    del argv  # currently unused, reserved for future options
    _ensure_requirements_installed()
    if _should_skip():
        return 0

    run_generator()
    try:
        assert_clean_git_diff()
    except DriftDetectedError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main(sys.argv[1:]))

