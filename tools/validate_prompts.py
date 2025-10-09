"""Validate Wave 1 sub-prompts have prompt recipes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence
from zoneinfo import ZoneInfo


PHOENIX_TZ = ZoneInfo("America/Phoenix")


@dataclass(frozen=True)
class ValidationConfig:
    prompts_dir: Path
    recipes_dir: Path
    git_sha: str


class PromptRecipeValidator:
    def __init__(self, config: ValidationConfig) -> None:
        self.config = config

    def gather_prompts(self) -> List[Path]:
        prompts: List[Path] = []
        ignore = {"README.md", "subprompt_template.md", "mop_wave1_security.md"}
        for path in self.config.prompts_dir.glob("*.md"):
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
        default="project/prompts/wave1",
        type=Path,
        help="Directory containing Wave 1 sub-prompts.",
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
    args: argparse.Namespace, git_sha: str, missing: Sequence[str]
) -> None:
    payload = {
        "timestamp_mst": datetime.now(PHOENIX_TZ).strftime("%Y-%m-%d %H:%M MST"),
        "git_sha": git_sha,
        "prompts_dir": str(args.prompts_dir),
        "recipes_dir": str(args.recipes_dir),
        "missing_prompts": list(missing),
        "cli_args": sys.argv[1:],
    }
    print(json.dumps(payload, indent=2))


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    git_sha = resolve_git_sha(args.git_sha)
    config = ValidationConfig(
        prompts_dir=args.prompts_dir,
        recipes_dir=args.recipes_dir,
        git_sha=git_sha,
    )
    validator = PromptRecipeValidator(config)

    missing = validator.validate()
    emit_metadata(args, git_sha, missing)
    if missing:
        print(
            "Missing prompt recipes for:"
            + "\n"
            + "\n".join(f" - {item}" for item in missing),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
