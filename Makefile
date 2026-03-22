## AWS Starter Projects — Repo-Level Makefile
##
## Create new projects from the base template.
##
## Usage:
##   make new-project APP=budget
##   make new-project APP=budget DEFAULTS=true   # skip prompts

APP ?=
DEFAULTS ?=
BASE := cloud-ai-starter-projects/_base-template

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo ""
	@echo "  AWS Starter Projects"
	@echo "  ─────────────────────────────────────────────────"
	@echo ""
	@echo "  make new-project APP=<name>     Create a new project from the base template"
	@echo "  make new-project APP=<name> DEFAULTS=true   (skip interactive prompts)"
	@echo ""
	@echo "  Templates:"
	@ls -d cloud-ai-starter-projects/template-* 2>/dev/null | sed 's|.*/|    |' || echo "    (none)"
	@echo ""

.PHONY: new-project
new-project:
ifndef APP
	$(error APP is required. Usage: make new-project APP=budget)
endif
	@bash $(BASE)/scripts/new-project.sh $(APP) $(if $(filter true,$(DEFAULTS)),--defaults,)
