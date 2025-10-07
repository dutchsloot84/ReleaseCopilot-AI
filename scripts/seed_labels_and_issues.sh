#!/usr/bin/env bash
set -euo pipefail
# Requires: GitHub CLI authenticated

# Labels
gh label create "mop" --color AADDEE --description "Master Orchestrator Prompt"
gh label create "wave:wave1" --color D4C5F9 --description "Wave 1"
gh label create "type:feature" --color C2E0C6 || true
gh label create "type:bug" --color F9D0C4 || true
gh label create "priority:P1" --color FEA3A3 || true

# Seed Issues (examples)
gh issue create -t "[Wave 1] [Secrets] Create & Wire SM" -b "Implements MOP: prompts/mop_wave1_security.md (#1)." -l "mop, wave:wave1, type:feature, priority:P1"
gh issue create -t "[Wave 1] [Budget/Alarms] Low-Ceiling Budget + SNS Notice" -b "Implements MOP: prompts/mop_wave1_security.md (#2)." -l "mop, wave:wave1, type:feature"
gh issue create -t "[Wave 1] [S3 Artifact Bucket]" -b "Implements MOP: prompts/mop_wave1_security.md (#3)." -l "mop, wave:wave1, type:feature"
