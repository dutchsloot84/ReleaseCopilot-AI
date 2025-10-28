"""pre-commit hook that verifies Wave generator outputs are committed."""

from __future__ import annotations

from importlib import util as importlib_util
import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = Path("backlog/wave3.yaml")
DEFAULT_TIMEZONE = "America/Phoenix"
GENERATED_PATHS: tuple[str, ...] = ("docs/mop", "docs/sub-prompts", "artifacts")


class DriftDetectedError(RuntimeError):
    """Raised when the generator introduces uncommitted changes."""


def _run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    effective_env = dict(os.environ)
    python_path_parts = [str(REPO_ROOT), str(REPO_ROOT / "src")]
    if env:
        effective_env.update(env)
    existing_python_path = effective_env.get("PYTHONPATH")
    if existing_python_path:
        python_path_parts.append(existing_python_path)
    effective_env["PYTHONPATH"] = os.pathsep.join(python_path_parts)
    return subprocess.run(
        list(command),
        cwd=str(cwd or REPO_ROOT),
        env=effective_env,
        check=True,
        text=True,
    )


def _should_skip() -> bool:
    return os.environ.get("RELEASECOPILOT_SKIP_GENERATOR", "0") == "1"


def _missing_modules() -> list[str]:
    modules = ["releasecopilot", "click"]
    missing: list[str] = []
    for module in modules:
        if importlib_util.find_spec(module) is None:
            missing.append(module)
    return missing


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
    if _should_skip():
        return 0

    missing = _missing_modules()
    if missing:
        module_list = ", ".join(sorted(missing))
        print(
            f"Missing required modules for generator drift hook: {module_list}.",
            file=sys.stderr,
        )
        print(
            "Activate the Python 3.11 virtualenv and run 'pip install -e .[dev]'"
            " before re-running pre-commit.",
            file=sys.stderr,
        )
        return 1

    run_generator()
    try:
        assert_clean_git_diff()
    except DriftDetectedError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main(sys.argv[1:]))
