from __future__ import annotations

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
