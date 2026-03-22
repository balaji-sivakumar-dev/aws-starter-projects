# AWS Starter Projects — Claude Instructions

This file contains project-wide rules for the `aws-starter-projects` repository.
Global rules in `~/.claude/CLAUDE.md` also apply.

---

## Project Overview

A collection of cloud application templates demonstrating different AWS architecture patterns.
Each template is self-contained under `cloud-ai-starter-projects/template-*/`.

## Active Templates

| Template | Name | Status |
|---|---|---|
| Base Template (`_base-template/`) | Reusable AWS starter for new projects | Ready |
| Template 3 | Reflect — Container + Serverless Journal with RAG | Active development |

## Creating a New Project

```bash
make new-project APP=budget              # interactive prompts
make new-project APP=budget DEFAULTS=true # skip prompts
```

This copies `_base-template/` → `template-{APP}/`, replaces all `{{PLACEHOLDER}}` values, and removes opt-out features per `template.json`.

## Template-Level Instructions

Each template has its own `CLAUDE.md` with project-specific rules. Always check for
and follow the nearest `CLAUDE.md` in the directory tree.

- `cloud-ai-starter-projects/_base-template/CLAUDE.md` — Base template rules (applies to all new projects)
- `cloud-ai-starter-projects/template-3-container-serverless-journal/CLAUDE.md` — Reflect app rules

## Repo-Wide Rules

1. Templates are self-contained — no cross-template imports or shared code at repo level.
2. Every template follows the directory convention in `_base-template/CLAUDE.md`.
3. Terraform modules are copied per template, not symlinked.
4. Shell scripts go under `scripts/` with usage comments at the top.
5. The `_base-template/` directory is the source of truth — never edit generated `template-*/` projects to fix template issues; fix the base template instead.
