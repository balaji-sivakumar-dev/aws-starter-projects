# Implementation Checklist — Base Template

## Requirements

| ID | Requirement | Status | Notes |
|----|------------|--------|-------|
| R-001 | Base template extracted from Template 3 | Done | Copied and parameterized all source files |
| R-002 | Parameterize all hardcoded values with `{{PLACEHOLDER}}` syntax | Done | APP_PREFIX, APP_TITLE, AWS_REGION, AWS_PROFILE |
| R-003 | Feature flag system via template.json | Done | AI, RAG, Admin, CSV Import, Insights — opt-in/out |
| R-004 | Bootstrap script (new-project.sh) | Done | Interactive + --defaults modes, placeholder replacement, feature removal |
| R-005 | Repo-level Makefile (`make new-project APP=x`) | Done | Wraps bootstrap script |
| R-006 | routes.yaml as single source of truth | Done | All API routes defined with path, method, auth level |
| R-007 | Shared config.sh for deployment constants | Done | SSM paths, app prefix, region — sourced by all scripts |
| R-008 | CLAUDE.md with 24 binding rules | Done | Extracted from Template 3 lessons learned |

## Issues

| ID | Issue | Status | Notes |
|----|-------|--------|-------|
| I-001 | Bootstrap script path calculation doubled `cloud-ai-starter-projects/` | Fixed | REPO_ROOT needed 3 levels up, not 2 |
| I-002 | `setJournalView` not renamed to `setItemsView` in App.jsx | Fixed | Bulk sed missed the state setter |

## Fixes

| ID | Fix | Status | Notes |
|----|-----|--------|-------|
| F-001 | Replace all "journal" references with generic "item"/"data" language | Done | 20+ files across Python, JS, CSS, Terraform, shell scripts |
| F-002 | Fix Terraform db module table name mangled by sed | Done | Removed extra `${var.app_prefix}` in name |
| F-003 | Fix Docker Compose duplicate TABLE_NAME env var | Done | Removed duplicate line |
| F-004 | Fix double-nested os.getenv in Python files | Done | Simplified to single getenv with default |
