"""CLI parsing tests for Release Copilot."""

from __future__ import annotations

from pathlib import Path

import releasecopilot
from releasecopilot import cli


def test_parse_args_supports_boolean_flags() -> None:
    """The CLI should toggle the AWS Secrets Manager flag correctly."""

    args = cli.parse_args(["--use-aws-secrets-manager"])
    assert args.use_aws_secrets_manager is True

    args = cli.parse_args(["--no-aws-secrets-manager"])
    assert args.use_aws_secrets_manager is False


def test_parse_args_records_config_path(tmp_path: Path) -> None:
    """Supplying ``--config`` should preserve the provided path."""

    config_path = tmp_path / "custom.yaml"
    args = cli.parse_args(["--config", str(config_path)])
    assert Path(args.config) == config_path


def test_cli_accepts_log_level() -> None:
    args = cli.parse_args(["--log-level", "debug"])
    assert args.log_level == "debug"


def test_run_builds_config_from_yaml(tmp_path: Path) -> None:
    """``cli.run`` should integrate with ``build_config`` to produce a final mapping."""

    config_file = tmp_path / "releasecopilot.yaml"
    config_file.write_text(
        """
        fix_version: 8.8.8
        jira_base: https://jira.cli
        bitbucket_base: https://bitbucket.cli
        use_aws_secrets_manager: false
        """
    )

    result = cli.run(["--config", str(config_file)])

    assert result["fix_version"] == "8.8.8"
    assert result["jira_base"] == "https://jira.cli"
    assert result["bitbucket_base"] == "https://bitbucket.cli"
    assert result["config_path"] == str(config_file)


def test_package_exports_cli_surface() -> None:
    """Top-level package should re-export stable CLI entry points."""

    assert releasecopilot.parse_args is cli.parse_args
    assert releasecopilot.run is cli.run
    assert hasattr(releasecopilot, "load_dotenv")


def test_find_dotenv_path_prefers_repo_root(tmp_path: Path) -> None:
    """The CLI should prefer repository-level ``.env`` files when present."""

    repo_root = tmp_path / "repo"
    package_dir = repo_root / "src" / "releasecopilot"
    package_dir.mkdir(parents=True)

    (repo_root / "pyproject.toml").write_text("[tool.poetry]\n")
    root_env = repo_root / ".env"
    root_env.write_text("ROOT=1\n")

    src_env = repo_root / "src" / ".env"
    src_env.write_text("SRC=1\n")

    package_env = package_dir / ".env"
    package_env.write_text("PKG=1\n")

    module_path = package_dir / "cli.py"
    module_path.write_text("# placeholder\n")

    discovered = cli.find_dotenv_path(module_path)
    assert discovered == root_env
