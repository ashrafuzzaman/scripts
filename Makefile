SHELL := /bin/bash

PYTHON ?= python3

.PHONY: all help editor-resources model-optimizer check

# Run every script in this directory.
all: editor-resources model-optimizer

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make                  Run all scripts' \
		'  make editor-resources Compare Zed and VS Code resource usage' \
		'  make model-optimizer  Rank LiteLLM models (requires GEN_LLLM_CLAUDE_KEY)' \
		'  make check            Run syntax and shell checks'

editor-resources:
	@./editor_resources.sh

model-optimizer:
	@$(PYTHON) litellm_model_optimizer.py

check:
	@$(PYTHON) -m py_compile litellm_model_optimizer.py
	@bash -n editor_resources.sh
	@printf '%s\n' 'Checks passed.'
