from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def main_module(monkeypatch: pytest.MonkeyPatch):
    root = PROJECT_ROOT
    root_str = str(root)
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)

    src_path = root / "src"
    src_str = str(src_path)
    if src_str in sys.path:
        sys.path.remove(src_str)
    sys.path.insert(1, src_str)

    for name in ("config", "config.settings", "main"):
        monkeypatch.delitem(sys.modules, name, raising=False)

    config_module = importlib.import_module("config.settings")
    sys.modules["config.settings"] = config_module

    spec = importlib.util.spec_from_file_location("main", root / "main.py")
    if spec is None or spec.loader is None:  # pragma: no cover - defensive guard
        raise RuntimeError("Unable to load main module")
    module = importlib.util.module_from_spec(spec)
    sys.modules["main"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def cli_module(main_module):  # noqa: D401 - re-export main_module side effects
    """Return a freshly imported ``src.cli.main`` module bound to ``main_module``."""

    return importlib.reload(importlib.import_module("src.cli.main"))


def test_main_exposes_shared_parser(main_module) -> None:
    shared_module = importlib.import_module("src.cli.shared")

    assert main_module.parse_args is shared_module.parse_args
    assert main_module.AuditConfig is shared_module.AuditConfig


def test_entrypoints_produce_matching_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    main_module,
    cli_module,
) -> None:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    json_artifact = artifacts_dir / "report.json"
    json_artifact.write_text("{}", encoding="utf-8")
    excel_artifact = artifacts_dir / "report.xlsx"
    excel_artifact.write_text("excel", encoding="utf-8")

    summary_payload = {"status": "ok"}
    fake_result = {
        "summary": summary_payload,
        "artifacts": {
            "json_report": str(json_artifact),
            "excel_report": str(excel_artifact),
        },
    }

    def stub_run_audit(_config):
        return fake_result

    monkeypatch.setattr(main_module, "run_audit", stub_run_audit)
    monkeypatch.setattr(cli_module, "run_audit", stub_run_audit)

    root_output = tmp_path / "root"
    exit_code_root = main_module.main(
        ["--fix-version", "1.2.3", "--output", str(root_output)]
    )
    captured_root = capsys.readouterr()

    cli_output = tmp_path / "cli"
    exit_code_cli = cli_module.main(
        ["--fix-version", "1.2.3", "--output", str(cli_output)]
    )
    captured_cli = capsys.readouterr()

    assert exit_code_root == exit_code_cli == 0
    assert captured_root.out == captured_cli.out

    summary_root = json.loads((root_output / "summary.json").read_text(encoding="utf-8"))
    summary_cli = json.loads((cli_output / "summary.json").read_text(encoding="utf-8"))
    assert summary_root == summary_cli == summary_payload

    root_files = sorted(path.name for path in root_output.iterdir())
    cli_files = sorted(path.name for path in cli_output.iterdir())
    assert root_files == cli_files == ["report.json", "report.xlsx", "summary.json"]
