"""pre-commit hook that verifies Wave generator outputs are committed."""

from __future__ import annotations

from argparse import ArgumentParser
from importlib import import_module
import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_REQUIREMENTS = Path(__file__).with_name("requirements.txt")
_HOOK_IMPORTS = (
    "click",
    "jinja2",
    "slugify",
    "yaml",
    "requests",
)
DEFAULT_SPEC = Path("backlog/wave3.yaml")
DEFAULT_TIMEZONE = "America/Phoenix"
GENERATED_PATHS: tuple[str, ...] = ("docs/mop", "docs/sub-prompts", "artifacts")


class DriftDetectedError(RuntimeError):
    """Raised when the generator introduces uncommitted changes."""


def _ensure_hook_dependencies(requirements: Path) -> None:
    if not requirements.is_file():
        return

    missing: list[str] = []
    for module in _HOOK_IMPORTS:
        try:
            import_module(module)
        except ModuleNotFoundError:
            missing.append(module)

    if missing:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements)],
            check=True,
        )

    try:
        import_module("releasecopilot")
    except ModuleNotFoundError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
            check=True,
            cwd=str(REPO_ROOT),
        )


def _run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    pythonpath_parts = [str(REPO_ROOT / "src"), str(REPO_ROOT)]
    if existing := merged_env.get("PYTHONPATH"):
        pythonpath_parts.append(existing)
    merged_env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    return subprocess.run(
        list(command),
        cwd=str(cwd or REPO_ROOT),
        env=merged_env,
        check=True,
        text=True,
    )


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
    parser = ArgumentParser()
    parser.add_argument(
        "--requirements-file",
        type=Path,
        default=HOOK_REQUIREMENTS,
        help="Optional requirements file that pins hook dependencies.",
    )
    args = parser.parse_args(argv)

    _ensure_hook_dependencies(args.requirements_file)
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
