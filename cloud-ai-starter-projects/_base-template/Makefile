## {{APP_TITLE}} — Makefile
##
## Wraps the setup/deploy shell scripts under scripts/setup/.
## All targets accept ENV and PROFILE overrides:
##
##   make deploy-backend              # ENV=dev, PROFILE={{APP_PREFIX}}-dev
##   make deploy-backend ENV=staging PROFILE=my-profile
##
## Prerequisites: AWS CLI, Terraform, Node.js/npm, Docker

ENV     ?= dev
PROFILE ?= {{APP_PREFIX}}-dev
SCRIPTS := scripts/setup

.DEFAULT_GOAL := help

# ── Help ──────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "  {{APP_TITLE}} — AWS Deployment Targets"
	@echo "  ──────────────────────────────────────────────────────────"
	@echo "  Bootstrap & Secrets"
	@echo "    make bootstrap          Bootstrap Terraform S3 backend + DynamoDB lock table"
	@echo "    make secrets            Store API keys + user allowlist in SSM Parameter Store"
	@echo "    make cognito-admin      Create the admin Cognito user (post-deploy)"
	@echo ""
	@echo "  Infrastructure"
	@echo "    make infra              Full terraform init + plan + apply (first deploy)"
	@echo ""
	@echo "  Iterative Backend Deploy  (use after infra is up)"
	@echo "    make deploy-backend     Deploy Lambda API + AI Gateway + Step Functions"
	@echo "    make deploy-routes      deploy-backend AND update API Gateway routes"
	@echo "    make deploy-api         Deploy API Lambda only"
	@echo "    make deploy-ai          Deploy AI Gateway Lambda only"
	@echo "    make deploy-sfn         Deploy Step Functions state machine only"
	@echo ""
	@echo "  Frontend"
	@echo "    make deploy-web         Build React app + sync to S3 + CloudFront invalidation"
	@echo ""
	@echo "  Full Deploy (backend + web)"
	@echo "    make deploy             deploy-backend + deploy-web"
	@echo "    make deploy-all-routes  deploy-routes + deploy-web"
	@echo ""
	@echo "  Local Dev"
	@echo "    make dev                Start full local stack (Docker Compose)"
	@echo "    make dev-down           Stop local stack"
	@echo "    make test               Run backend Python tests"
	@echo "    make web-dev            Start Vite dev server (localhost:5173)"
	@echo ""
	@echo "  Validation"
	@echo "    make validate-routes    Check routes.yaml vs Terraform + handler alignment"
	@echo ""
	@echo "  Options: ENV=$(ENV)  PROFILE=$(PROFILE)"
	@echo ""

# ── Bootstrap ─────────────────────────────────────────────────────────────────
.PHONY: bootstrap
bootstrap:
	AWS_PROFILE=$(PROFILE) bash $(SCRIPTS)/step-2-bootstrap-terraform-backend.sh $(ENV)

# ── Secrets ───────────────────────────────────────────────────────────────────
.PHONY: secrets
secrets:
	AWS_PROFILE=$(PROFILE) bash $(SCRIPTS)/step-2b-store-secrets.sh $(ENV)

# ── Cognito admin user ────────────────────────────────────────────────────────
.PHONY: cognito-admin
cognito-admin:
	AWS_PROFILE=$(PROFILE) bash $(SCRIPTS)/step-2c-create-cognito-admin.sh $(ENV)

# ── Full Terraform apply (first-time deploy) ──────────────────────────────────
.PHONY: infra
infra:
	AWS_PROFILE=$(PROFILE) bash $(SCRIPTS)/step-3a-terraform-apply.sh $(ENV)

# ── Iterative backend deploys ─────────────────────────────────────────────────
.PHONY: deploy-backend
deploy-backend:
	AWS_PROFILE=$(PROFILE) bash $(SCRIPTS)/step-3c-deploy-backend.sh $(ENV)

.PHONY: deploy-routes
deploy-routes:
	DEPLOY_ROUTES=true AWS_PROFILE=$(PROFILE) bash $(SCRIPTS)/step-3c-deploy-backend.sh $(ENV)

.PHONY: deploy-api
deploy-api:
	DEPLOY_AI=false DEPLOY_SFN=false AWS_PROFILE=$(PROFILE) bash $(SCRIPTS)/step-3c-deploy-backend.sh $(ENV)

.PHONY: deploy-ai
deploy-ai:
	DEPLOY_API=false DEPLOY_SFN=false AWS_PROFILE=$(PROFILE) bash $(SCRIPTS)/step-3c-deploy-backend.sh $(ENV)

.PHONY: deploy-sfn
deploy-sfn:
	DEPLOY_API=false DEPLOY_AI=false AWS_PROFILE=$(PROFILE) bash $(SCRIPTS)/step-3c-deploy-backend.sh $(ENV)

# ── Frontend deploy ───────────────────────────────────────────────────────────
.PHONY: deploy-web
deploy-web:
	AWS_PROFILE=$(PROFILE) bash $(SCRIPTS)/step-4a-deploy-web-to-s3.sh $(ENV)

# ── Combined deploys ──────────────────────────────────────────────────────────
.PHONY: deploy
deploy: deploy-backend deploy-web

.PHONY: deploy-all-routes
deploy-all-routes: deploy-routes deploy-web

# ── Local dev ─────────────────────────────────────────────────────────────────
.PHONY: dev
dev:
	docker compose -f docker/docker-compose.yml --env-file .env.docker up -d
	@echo ""
	@echo "  Web UI  -> http://localhost:3000"
	@echo "  API     -> http://localhost:8080/docs"
	@echo ""

.PHONY: dev-down
dev-down:
	docker compose -f docker/docker-compose.yml --env-file .env.docker down

# ── Tests ─────────────────────────────────────────────────────────────────────
.PHONY: test
test:
	. services/api/.venv/bin/activate && pytest services/ -q

# ── Web dev server ────────────────────────────────────────────────────────────
.PHONY: web-dev
web-dev:
	cd apps/web && npm run dev

# ── Route validation ──────────────────────────────────────────────────────────
.PHONY: validate-routes
validate-routes:
	@bash scripts/validate-routes.sh

# ── draw.io MCP server ────────────────────────────────────────────────────────
.PHONY: drawio
drawio:
	npx @drawio/mcp
