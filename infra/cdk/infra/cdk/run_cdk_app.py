#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
runpy.run_path(ROOT / "run_cdk_app.py", run_name="__main__")
