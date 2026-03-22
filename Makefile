## AWS Starter Projects — Repo-Level Makefile
##
## Create new projects from the base template.
##
## Usage:
##   make new-project APP=budget                              # → generated/budget/
##   make new-project APP=budget DEFAULTS=true                # skip prompts
##   make new-project APP=budget OUT=~/projects/budget        # custom output path

APP ?=
DEFAULTS ?=
OUT ?=
BASE := cloud-ai-starter-projects/_base-template

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo ""
	@echo "  AWS Starter Projects"
	@echo "  ─────────────────────────────────────────────────"
	@echo ""
	@echo "  make new-project APP=<name>                  Create in generated/<name>/"
	@echo "  make new-project APP=<name> DEFAULTS=true    Skip interactive prompts"
	@echo "  make new-project APP=<name> OUT=<path>       Create at custom path"
	@echo ""
	@echo "  Generated projects:"
	@ls -d generated/*/ 2>/dev/null | sed 's|.*/\(.*\)/|    \1|' || echo "    (none)"
	@echo ""

.PHONY: new-project
new-project:
ifndef APP
	$(error APP is required. Usage: make new-project APP=budget)
endif
	@bash $(BASE)/scripts/new-project.sh $(APP) $(if $(filter true,$(DEFAULTS)),--defaults,) $(if $(OUT),--out $(OUT),)
