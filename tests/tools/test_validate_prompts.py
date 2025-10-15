from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import validate_prompts


@pytest.fixture(autouse=True)
def _freeze_git_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        validate_prompts, "resolve_git_sha", lambda explicit: "test-sha"
    )


def test_missing_recipe_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "task.md").write_text("content", encoding="utf-8")

    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    exit_code = validate_prompts.main(
        [
            "--prompts-dir",
            str(prompts_dir),
            "--recipes-dir",
            str(recipes_dir),
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Missing prompt recipes" in captured.err
    assert "task.md" in captured.err


def test_missing_recipe_with_relative_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    prompts_dir = Path("prompts")
    prompts_dir.mkdir()
    (prompts_dir / "task.md").write_text("content", encoding="utf-8")

    recipes_dir = Path("recipes")
    recipes_dir.mkdir()

    exit_code = validate_prompts.main(
        [
            "--prompts-dir",
            str(prompts_dir),
            "--recipes-dir",
            str(recipes_dir),
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Missing prompt recipes" in captured.err
    assert "prompts/task.md" in captured.err


def test_validator_passes_with_recipe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    prompt_path = prompts_dir / "task.md"
    prompt_path.write_text("content", encoding="utf-8")
    (prompts_dir / "README.md").write_text("ignore", encoding="utf-8")

    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    recipe = recipes_dir / "task_recipe.md"
    recipe.write_text(
        "\n".join(
            [
                "# Recipe",
                "- **Sub-Prompt Path:** prompts/task.md",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = validate_prompts.main(
        [
            "--prompts-dir",
            str(prompts_dir),
            "--recipes-dir",
            str(recipes_dir),
        ]
    )

    assert exit_code == 0


def test_validator_passes_with_relative_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    prompts_dir = Path("prompts")
    prompts_dir.mkdir()
    prompt_path = prompts_dir / "task.md"
    prompt_path.write_text("content", encoding="utf-8")

    recipes_dir = Path("recipes")
    recipes_dir.mkdir()
    recipe = recipes_dir / "task_recipe.md"
    recipe.write_text(
        "\n".join(
            [
                "# Recipe",
                "- **Sub-Prompt Path:** prompts/task.md",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = validate_prompts.main(
        [
            "--prompts-dir",
            str(prompts_dir),
            "--recipes-dir",
            str(recipes_dir),
        ]
    )

    assert exit_code == 0


def test_auto_discovers_wave_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    prompts_root = Path("project") / "prompts"
    wave_dir = prompts_root / "wave5"
    wave_dir.mkdir(parents=True)
    prompt_path = wave_dir / "task.md"
    prompt_path.write_text("content", encoding="utf-8")

    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    recipe = recipes_dir / "task_recipe.md"
    recipe.write_text(
        "\n".join(
            [
                "# Recipe",
                f"- **Sub-Prompt Path:** {wave_dir / 'task.md'}",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = validate_prompts.main(
        [
            "--prompts-root",
            str(prompts_root),
            "--recipes-dir",
            str(recipes_dir),
        ]
    )

    assert exit_code == 0


def test_wave_argument_limits_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    prompts_root = Path("project") / "prompts"
    wave_two = prompts_root / "wave2"
    wave_three = prompts_root / "wave3"
    wave_two.mkdir(parents=True)
    wave_three.mkdir(parents=True)
    (wave_two / "task.md").write_text("content", encoding="utf-8")
    (wave_three / "task.md").write_text("content", encoding="utf-8")

    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    (recipes_dir / "wave2_recipe.md").write_text(
        "\n".join(
            [
                "# Recipe",
                f"- **Sub-Prompt Path:** {wave_two / 'task.md'}",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = validate_prompts.main(
        [
            "--prompts-root",
            str(prompts_root),
            "--waves",
            "wave2",
            "--recipes-dir",
            str(recipes_dir),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "wave2" in captured.out
    assert "wave3" not in captured.out


def test_config_file_drives_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    prompts_root = Path("project") / "prompts"
    active_wave = prompts_root / "wave9"
    inactive_wave = prompts_root / "wave10"
    active_wave.mkdir(parents=True)
    inactive_wave.mkdir(parents=True)
    (active_wave / "task.md").write_text("content", encoding="utf-8")
    (inactive_wave / "task.md").write_text("content", encoding="utf-8")

    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    (recipes_dir / "wave9_recipe.md").write_text(
        "\n".join(
            [
                "# Recipe",
                f"- **Sub-Prompt Path:** {active_wave / 'task.md'}",
            ]
        ),
        encoding="utf-8",
    )

    waves_config = tmp_path / "waves.json"
    waves_config.write_text(
        json.dumps(
            {
                "waves": [
                    {
                        "name": "wave9",
                        "validate_recipes": True,
                        "path": str(active_wave),
                    },
                    {
                        "name": "wave10",
                        "validate_recipes": False,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = validate_prompts.main(
        [
            "--prompts-root",
            str(prompts_root),
            "--waves-config",
            str(waves_config),
            "--recipes-dir",
            str(recipes_dir),
        ]
    )

    assert exit_code == 0
