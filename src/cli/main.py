"""Modern CLI shim for ``python -m src.cli.main`` usage."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

try:
    from main import run_audit
except ModuleNotFoundError:
    fallback_root = Path(__file__).resolve().parents[2]
    if str(fallback_root) not in sys.path:
        sys.path.insert(0, str(fallback_root))
    fallback_src = fallback_root / "src"
    if str(fallback_src) not in sys.path:
        sys.path.insert(1, str(fallback_src))
    from main import run_audit

try:  # pragma: no cover - optional dependency loading
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass

from releasecopilot.errors import ReleaseCopilotError  # noqa: E402
from releasecopilot.logging_config import configure_logging, get_logger  # noqa: E402

from .shared import finalize_run, handle_dry_run, parse_args

logger = get_logger(__name__)


def main(argv: Iterable[str] | None = None) -> int:
    args, config = parse_args(argv)
    configure_logging(args.log_level)
    logger.info(
        "Starting ReleaseCopilot run",
        extra={
            "fix_version": config.fix_version,
            "repos": config.repos,
            "branches": config.branches,
        },
    )

    if args.dry_run:
        logger.info("Dry run requested")
        handle_dry_run(config)
        return 0

    try:
        result = run_audit(config)
    except ReleaseCopilotError as exc:
        logger.error("ReleaseCopilot run failed", extra=getattr(exc, "context", {}))
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finalize_run(result, args)
    logger.info(
        "ReleaseCopilot run completed",
        extra={"artifacts": list(result.get("artifacts", {}).keys())},
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
