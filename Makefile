PYTHON ?= python3

.PHONY: gen-wave3 check-generated

gen-wave3:
	$(PYTHON) scripts/github/wave2_helper.py generate backlog/wave3.yaml

check-generated:
	git diff --exit-code docs/mop docs/sub-prompts artifacts || (echo "Regenerate: make gen-wave3" && exit 1)
