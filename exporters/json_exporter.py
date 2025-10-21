"""Exports audit results to structured JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class JSONExporter:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, data: Dict[str, Any], filename: str = "audit_results.json") -> Path:
        output_path = self.output_dir / filename
        with output_path.open("w", encoding="utf-8") as fh:
            payload = json.dumps(data, indent=2)
            if not payload.endswith("\n"):
                payload = f"{payload}\n"
            fh.write(payload)
        return output_path
