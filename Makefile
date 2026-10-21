SHELL := /bin/bash

PYTHON ?= python3

.PHONY: all help model-optimizer litellm-models litellm-setup kube-setup kube-context kube-shell check

# Run the default local utilities.
all: model-optimizer

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make                  Run default local utilities' \
		'  make model-optimizer  Rank LiteLLM models (requires GEN_LLLM_CLAUDE_KEY)' \
		'  make litellm-models   List LiteLLM models (requires LITELLM_API_KEY and ctp)' \
		'  make litellm-setup    Install ctp globally using npm' \
		'  make kube-setup       Pull EKS kubeconfig contexts (PROFILE=, CONTEXT=)' \
		'  make kube-context Q=  Switch kube context by fuzzy name' \
		'  make kube-shell Q=    Shell into a pod by fuzzy name (CONTEXT=, NS=)' \
		'  make check            Run Python tests and shell syntax checks'

model-optimizer:
	@$(PYTHON) litellm/litellm_model_optimizer.py

litellm-models:
	@./litellm/models.sh

litellm-setup:
	@./litellm/setup.sh

kube-setup:
	@./kubernetes/kube_setup.sh $(if $(PROFILE),-p $(PROFILE)) $(if $(CONTEXT),-c $(CONTEXT))

kube-context:
	@./kubernetes/kube_context.sh $(Q)

kube-shell:
	@./kubernetes/kube_pod_shell.sh $(if $(CONTEXT),-x $(CONTEXT)) $(if $(NS),-n $(NS)) $(Q)

check:
	@$(PYTHON) -m py_compile litellm/litellm_model_optimizer.py litellm/list_models.py
	@$(PYTHON) -m unittest discover -s litellm -p 'test_*.py'
	@for f in kubernetes/kube_*.sh litellm/*.sh; do bash -n "$$f"; done
	@printf '%s\n' 'Checks passed.'
