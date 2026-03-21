# CI/CD Strategy — From Shell Scripts to Automated Pipelines

> **Status: Design phase**
> Last updated: 2026-03-14

---

## 1. Where we are today (Phase 0)

```
Developer laptop
    │
    ├── ./scripts/setup/step-2-bootstrap-terraform-backend.sh dev
    ├── ./scripts/setup/step-3a-terraform-apply.sh dev
    ├── ./scripts/setup/step-4a-deploy-web-to-s3.sh dev
    └── AWS CLI (aws s3 sync, terraform apply)
```

**What works:**
- Simple, transparent — you see exactly what runs
- No CI/CD infrastructure to maintain or pay for
- Numbered steps enforce correct ordering
- Idempotent scripts (safe to re-run)

**What doesn't scale:**
- No automated testing before deploy
- No environment protection (nothing stops you from running `destroy` on prod)
- No audit trail (who deployed what, when)
- Manual process = human error risk
- No PR-based workflow (code review doesn't include infra plan preview)

**Verdict: Good for 1-2 developers, fine for now.**

---

## 2. Evolution path

```
Phase 0 (now)          Phase 1 (next)           Phase 2 (later)         Phase 3 (scale)
───────────────       ────────────────          ────────────────        ────────────────
Shell scripts         GitHub Actions            GitHub Actions          GitHub Actions
from laptop           basic pipeline            full pipeline           + environments

Manual terraform      Auto test on PR           Auto plan on PR         Plan + approval gate
Manual s3 sync        Auto deploy on merge      Auto deploy on merge    Staged rollout
No tests in CI        Lint + unit tests         Lint + unit + e2e       Full test matrix
No env protection     dev only                  dev + staging           dev + staging + prod
```

---

## 3. Phase 1 — GitHub Actions (recommended next step)

### What it adds
- Run tests automatically on every PR
- Run `terraform plan` on PR (show what would change, don't apply)
- Auto-deploy on merge to main
- Free for public repos, 2000 min/mo for private repos

### Repo structure: Monorepo (keep current approach)

```
aws-starter-projects/                  ← Single repo
├── .github/workflows/
│   ├── ci.yml                         ← Runs on every PR
│   ├── deploy-infra.yml               ← Terraform apply on merge
│   └── deploy-web.yml                 ← Frontend deploy on merge
├── cloud-ai-starter-projects/
│   └── template-3-.../
│       ├── services/                  ← Backend code
│       ├── apps/web/                  ← Frontend code
│       └── infra/terraform/           ← Infrastructure
```

**Why monorepo for a small team:**
- One PR shows infra + code + frontend changes together
- Atomic changes (API endpoint + Terraform route + frontend call in one PR)
- Simpler CI — one repo to configure, not three
- No cross-repo dependency versioning headache

### Workflow: `ci.yml` (runs on every PR)

```yaml
name: CI
on:
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          cd cloud-ai-starter-projects/template-3-container-serverless-journal/services/api
          pip install -r requirements.txt -r requirements-dev.txt

      - name: Run tests
        run: |
          cd cloud-ai-starter-projects/template-3-container-serverless-journal/services/api
          pytest tests/ -v

  terraform-plan:
    runs-on: ubuntu-latest
    # Only run if infra files changed
    if: contains(github.event.pull_request.changed_files, 'infra/')
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Terraform Init
        run: |
          cd cloud-ai-starter-projects/template-3-container-serverless-journal/infra/terraform
          terraform init -backend-config=backend.dev.tfbackend

      - name: Terraform Plan
        run: |
          cd cloud-ai-starter-projects/template-3-container-serverless-journal/infra/terraform
          terraform plan -var-file=environments/dev/dev.tfvars -no-color
        # Plan output appears as PR comment (via terraform-plan action)

  frontend-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: |
          cd cloud-ai-starter-projects/template-3-container-serverless-journal/apps/web
          npm ci && npm run build
```

### Workflow: `deploy-infra.yml` (runs on merge to main)

```yaml
name: Deploy Infrastructure
on:
  push:
    branches: [main]
    paths:
      - 'cloud-ai-starter-projects/template-3-*/infra/**'
      - 'cloud-ai-starter-projects/template-3-*/services/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: dev              # GitHub environment with protection rules
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ca-central-1

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Terraform Apply
        run: |
          cd cloud-ai-starter-projects/template-3-container-serverless-journal
          ./scripts/setup/step-3a-terraform-apply.sh dev
```

### Workflow: `deploy-web.yml` (frontend deploy on merge)

```yaml
name: Deploy Frontend
on:
  push:
    branches: [main]
    paths:
      - 'cloud-ai-starter-projects/template-3-*/apps/web/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: dev
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ca-central-1

      - name: Deploy to S3
        run: |
          cd cloud-ai-starter-projects/template-3-container-serverless-journal
          ./scripts/setup/step-4a-deploy-web-to-s3.sh dev
```

---

## 4. AWS credentials for CI/CD

**Don't store AWS access keys in GitHub Secrets.** Use OIDC (OpenID Connect) instead:

```
GitHub Actions → OIDC token → AWS STS → Assume Role → Temporary credentials
```

### One-time setup (Terraform):

```hcl
# modules/cicd/main.tf — add to your Terraform

# GitHub OIDC provider (one per AWS account)
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["ffffffffffffffffffffffffffffffffffffffff"]
}

# Deploy role for GitHub Actions
resource "aws_iam_role" "github_deploy" {
  name = "${var.app_prefix}-github-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:balaji-sivakumar-dev/aws-starter-projects:*"
        }
      }
    }]
  })
}

# Attach permissions (scoped to what deploy needs)
resource "aws_iam_role_policy_attachment" "deploy_permissions" {
  role       = aws_iam_role.github_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
  # TODO: scope down to least-privilege in Phase 2
}
```

Then set `AWS_DEPLOY_ROLE_ARN` in GitHub repo secrets.

---

## 5. Should Terraform live in a separate repo?

| Approach | Pros | Cons | Best for |
|----------|------|------|----------|
| **Monorepo** (infra + app together) | Atomic changes, one PR for everything, simpler CI | Terraform state coupling, harder to share infra across apps | **1-3 developers, single app** |
| **Separate infra repo** | Independent deploy cadence, shared across apps, cleaner blast radius | Cross-repo coordination, PR reviews span two repos, version drift | **Multiple apps sharing infra, or dedicated platform team** |
| **Terraform modules repo** (shared library) | Reusable modules versioned independently, apps compose what they need | Module versioning complexity, semantic versioning discipline needed | **5+ apps, published template** |

### Recommendation for your situation:

**Now (1-2 devs, building Template 3 + Curriculum):**
→ **Monorepo.** Everything in one repo. One PR, one review, one merge.

**When you have 3+ apps on the platform:**
→ **Extract shared Terraform modules** into a separate repo (`aws-tf-modules`). Apps reference modules by git tag:

```hcl
module "auth" {
  source = "git::https://github.com/balaji-sivakumar-dev/aws-tf-modules.git//modules/auth?ref=v1.2.0"
}
```

Each app repo contains its own `main.tf` that composes shared modules + app-specific resources.

**Don't split prematurely.** The cost of splitting (cross-repo coordination, version management) outweighs the benefit until you actually have multiple apps deployed.

---

## 6. Environment strategy

```
Branch workflow:
  feature/* ──PR──► main ──auto-deploy──► dev (AWS)
                      │
                      └── manual promote ──► staging ──► prod (future)
```

### Phase 1 (now):
- `dev` environment only
- Auto-deploy on merge to main
- Shell scripts still work for manual deploys

### Phase 2 (when Curriculum app has users):
- Add `staging` environment
- `main` → auto-deploy to `dev`
- Manual promotion: `dev` → `staging` (GitHub Actions workflow_dispatch)
- GitHub Environment protection rules: require approval for staging

### Phase 3 (production):
- Add `prod` environment
- `staging` → `prod` requires approval from 1+ reviewer
- Terraform plan diff posted as PR comment before apply
- Rollback script available

---

## 7. What to automate first (minimal viable CI/CD)

| # | What | Effort | Value |
|---|------|--------|-------|
| 1 | **Run tests on PR** | 30 min | Catches bugs before merge |
| 2 | **Frontend build check on PR** | 15 min | Catches build errors |
| 3 | **Terraform plan on PR** | 30 min | Shows infra changes before apply |
| 4 | **Auto-deploy on merge** | 1 hour | Eliminates manual deploy step |
| 5 | **OIDC credentials** | 1 hour | Secure, no long-lived keys |

**Total: ~3 hours** to go from shell scripts to automated CI/CD.

Items 1-3 are the highest value — they run on PRs and prevent bad merges. Item 4 (auto-deploy) can wait until you're confident in the test coverage.

---

## 8. Cost

| Component | Cost |
|-----------|------|
| GitHub Actions (private repo) | 2000 min/mo free, then $0.008/min |
| GitHub Actions (public repo) | Free |
| AWS OIDC setup | Free (IAM) |
| Terraform Cloud (alternative) | Free for 1 user, 500 runs/mo |

For a small team: **$0/mo** if under 2000 minutes of CI runs (typical for 1-3 developers).

---

## 9. Summary

| Question | Answer |
|----------|--------|
| Keep shell scripts? | **Yes** — they still work for manual deploys and are the foundation for CI scripts |
| Separate infra repo? | **Not yet** — monorepo until you have 3+ apps |
| CI/CD tool? | **GitHub Actions** — free, integrated, sufficient |
| AWS credentials? | **OIDC** — no long-lived keys, scoped to repo |
| When to add CI/CD? | **Phase 1 after RAG is built and tested** — don't add CI/CD complexity while actively building features |
| Environments? | **dev only for now** — add staging when Curriculum has users |
