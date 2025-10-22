"""pre-commit hook that verifies Wave generator outputs are committed."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = Path("backlog/wave3.yaml")
DEFAULT_TIMEZONE = "America/Phoenix"
GENERATED_PATHS: tuple[str, ...] = ("docs/mop", "docs/sub-prompts", "artifacts")
PYTHONPATH_SEGMENTS = ("src", ".")


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
        env=env,
        check=True,
        text=True,
    )


def _should_skip() -> bool:
    return os.environ.get("RELEASECOPILOT_SKIP_GENERATOR", "0") == "1"


def _build_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    segments = [str(REPO_ROOT / segment) for segment in PYTHONPATH_SEGMENTS]
    if pythonpath:
        segments.append(pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(segments)
    return env


def run_generator(*, spec: Path = DEFAULT_SPEC, timezone: str = DEFAULT_TIMEZONE) -> None:
    command = (
        sys.executable,
        "-m",
        "releasecopilot.cli_releasecopilot",
        "generate",
        "--spec",
        spec.as_posix(),
        "--timezone",
        timezone,
        "--archive",
    )
    _run(command, env=_build_env())


def assert_clean_git_diff(paths: Sequence[str] = GENERATED_PATHS) -> None:
    command = ("git", "diff", "--stat", "--exit-code", *paths)
    try:
        _run(command)
    except subprocess.CalledProcessError as error:  # pragma: no cover - defensive guard
        raise DriftDetectedError(
            "Generator drift detected. Run 'python -m releasecopilot.cli_releasecopilot "
            "generate --spec backlog/wave3.yaml --timezone America/Phoenix --archive'"
        ) from error


def main(argv: Sequence[str] | None = None) -> int:
    del argv  # currently unused, reserved for future options
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
