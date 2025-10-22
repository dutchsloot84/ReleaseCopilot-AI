"""Console entry point for the Wave 2 helper CLI."""

from __future__ import annotations

from typing import Sequence

import click

from releasecopilot.wave.wave2_helper import cli as wave2_cli


def main(argv: Sequence[str] | None = None) -> int:
    """Invoke the Wave 2 helper command group.

    Parameters
    ----------
    argv:
        Optional sequence of arguments (excluding the program name). When ``None``
        the Click command consumes ``sys.argv`` implicitly.
    """

    try:
        wave2_cli.main(args=list(argv) if argv is not None else None, standalone_mode=False)
    except SystemExit as exc:  # pragma: no cover - Click raises ``SystemExit``
        code = exc.code or 0
        return int(code)
    except click.ClickException as exc:
        exc.show()
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI shim
    raise SystemExit(main())
