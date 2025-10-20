"""Validate prompt waves maintain recipe coverage."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
from typing import Dict, List, Sequence
from zoneinfo import ZoneInfo

PHOENIX_TZ = ZoneInfo("America/Phoenix")


@dataclass(frozen=True)
class ValidationConfig:
    prompts_dirs: Sequence[Path]
    recipes_dir: Path
    git_sha: str


class PromptRecipeValidator:
    def __init__(self, config: ValidationConfig) -> None:
        self.config = config

    def gather_prompts(self) -> List[Path]:
        prompts: List[Path] = []
        ignore = {"README.md", "subprompt_template.md", "mop_wave1_security.md"}
        for directory in self.config.prompts_dirs:
            for path in directory.glob("*.md"):
                if path.name in ignore:
                    continue
                prompts.append(path)
        return sorted(prompts)

    def gather_recipe_mapping(self) -> Dict[str, Path]:
        mapping: Dict[str, Path] = {}
        for recipe_path in sorted(self.config.recipes_dir.glob("*_recipe.md")):
            sub_prompts = self._extract_sub_prompt_paths(recipe_path)
            for entry in sub_prompts:
                normalized = entry.strip()
                if not normalized:
                    continue
                mapping[normalized] = recipe_path
        return mapping

    def _extract_sub_prompt_paths(self, recipe_path: Path) -> Sequence[str]:
        lines = recipe_path.read_text(encoding="utf-8").splitlines()
        targets: List[str] = []
        marker = "sub-prompt path:"
        for line in lines:
            lower = line.lower()
            if marker in lower:
                start = lower.index(marker) + len(marker)
                raw = line[start:]
                values = [value.strip().strip("`*") for value in raw.split(",")]
                targets.extend(value for value in values if value)
        return targets

    def validate(self) -> List[str]:
        prompts = self.gather_prompts()
        mapping = self.gather_recipe_mapping()
        missing: List[str] = []
        repo_root = Path.cwd().resolve()
        for prompt in prompts:
            prompt_path = prompt if prompt.is_absolute() else (repo_root / prompt).resolve()
            try:
                key = str(prompt_path.relative_to(repo_root))
            except ValueError:
                key = str(prompt_path)
            if key not in mapping:
                missing.append(key)
        return missing


def resolve_git_sha(explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    return result.stdout.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prompts-dir",
        action="append",
        type=Path,
        help=(
            "Prompt directory to validate. Repeat to specify multiple directories."
            " Defaults to detected wave directories under --prompts-root when"
            " omitted."
        ),
    )
    parser.add_argument(
        "--prompts-root",
        default="project/prompts",
        type=Path,
        help="Root directory that contains wave prompt folders (e.g., wave1, wave2).",
    )
    parser.add_argument(
        "--waves",
        nargs="*",
        help=(
            "Specific wave folder names (such as 'wave2'). When provided the"
            " validator restricts checks to these folders under --prompts-root."
        ),
    )
    parser.add_argument(
        "--waves-config",
        default="project/prompts/waves.json",
        type=Path,
        help=(
            "Optional JSON configuration describing wave directories and"
            " validation flags. When present, entries with"
            " 'validate_recipes': true drive default discovery."
        ),
    )
    parser.add_argument(
        "--recipes-dir",
        default="project/prompts/prompt_recipes",
        type=Path,
        help="Directory containing prompt recipes.",
    )
    parser.add_argument(
        "--git-sha",
        default=None,
        help="Optional Git SHA override for metadata.",
    )
    return parser


def emit_metadata(
    *,
    git_sha: str,
    prompts_dirs: Sequence[Path],
    prompts_root: Path,
    waves: Sequence[str] | None,
    recipes_dir: Path,
    missing: Sequence[str],
) -> None:
    payload = {
        "timestamp_mst": datetime.now(PHOENIX_TZ).strftime("%Y-%m-%d %H:%M MST"),
        "git_sha": git_sha,
        "prompts_root": str(prompts_root),
        "prompts_dirs": [str(path) for path in prompts_dirs],
        "recipes_dir": str(recipes_dir),
        "waves": list(waves or []),
        "missing_prompts": list(missing),
        "cli_args": sys.argv[1:],
    }
    print(json.dumps(payload, indent=2))


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    prompt_dirs, selected_waves = _resolve_prompt_dirs(
        prompts_root=args.prompts_root,
        explicit_dirs=args.prompts_dir,
        waves=args.waves,
        config_path=args.waves_config,
    )
    if not prompt_dirs:
        print(
            "No prompt directories discovered. Use --prompts-dir or --waves to" " specify targets.",
            file=sys.stderr,
        )
        return 1

    missing_dirs = [str(path) for path in prompt_dirs if not path.exists()]
    if missing_dirs:
        print(
            "Prompt directories not found:\n" + "\n".join(f" - {item}" for item in missing_dirs),
            file=sys.stderr,
        )
        return 1

    git_sha = resolve_git_sha(args.git_sha)
    config = ValidationConfig(
        prompts_dirs=prompt_dirs,
        recipes_dir=args.recipes_dir,
        git_sha=git_sha,
    )
    validator = PromptRecipeValidator(config)

    missing = validator.validate()
    emit_metadata(
        git_sha=git_sha,
        prompts_dirs=prompt_dirs,
        prompts_root=args.prompts_root,
        waves=selected_waves,
        recipes_dir=args.recipes_dir,
        missing=missing,
    )
    if missing:
        print(
            "Missing prompt recipes for:" + "\n" + "\n".join(f" - {item}" for item in missing),
            file=sys.stderr,
        )
        return 1
    return 0


def _load_configured_dirs(*, config_path: Path, prompts_root: Path) -> tuple[List[Path], List[str]]:
    if not config_path or not config_path.exists():
        return [], []

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(
            f"Unable to parse waves configuration {config_path}: {exc}",
            file=sys.stderr,
        )
        return [], []

    entries = raw.get("waves")
    if not isinstance(entries, list):
        return [], []

    paths: List[Path] = []
    names: List[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        validate = entry.get("validate_recipes", True)
        if not validate:
            continue
        path_value = entry.get("path")
        if isinstance(path_value, str) and path_value.strip():
            candidate = Path(path_value)
        else:
            candidate = prompts_root / name
        paths.append(candidate)
        names.append(name)
    return paths, names


def _resolve_prompt_dirs(
    *,
    prompts_root: Path,
    explicit_dirs: Sequence[Path] | None,
    waves: Sequence[str] | None,
    config_path: Path,
) -> tuple[List[Path], List[str]]:
    if explicit_dirs:
        return [Path(directory) for directory in explicit_dirs], []

    if waves:
        return [prompts_root / wave for wave in waves], [str(wave) for wave in waves]

    configured_paths, configured_names = _load_configured_dirs(
        config_path=config_path, prompts_root=prompts_root
    )
    if configured_paths:
        return configured_paths, configured_names

    if not prompts_root.exists():
        return [], []

    auto_discovered = sorted(
        path
        for path in prompts_root.iterdir()
        if path.is_dir() and path.name.lower().startswith("wave")
    )
    return auto_discovered, [path.name for path in auto_discovered]


if __name__ == "__main__":
    sys.exit(main())
