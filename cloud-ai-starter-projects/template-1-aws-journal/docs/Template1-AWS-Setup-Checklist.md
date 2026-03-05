# Template 1 -- AWS Journal Starter Setup Checklist

> Owner: Balaji Sivakumar\
> Date Created: 2026-03-02\
> Goal: Deploy Template 1 safely with strict cost controls

------------------------------------------------------------------------

## PHASE 0 -- COST SAFETY FIRST (MANDATORY)

### Root Account Security

-   [x] Enable MFA on root user
-   [x] Confirm no root access keys exist
-   [x] Store root credentials securely

### Enable Billing Alerts

-   [x] Go to Billing → Preferences → Enable Billing Alerts
-   [x] Switch region to **ca_central_1**
-   [ ] Create CloudWatch billing alarm at \$1
-   [ ] Create CloudWatch billing alarm at \$5
-   [ ] Create CloudWatch billing alarm at \$10

### Create AWS Budgets

-   [x] Monthly ACTUAL budget = \$5 (alert at 50%, 80%, 100%)
-   [x] Monthly FORECAST budget = \$5 (alert at 80%, 100%)

### Region Decision

-   [x] Selected region: ca_central_1
-   [ ] Confirm Bedrock availability (if AI used)
-   [ ] Use same region for ALL services

------------------------------------------------------------------------

## PHASE 1 -- LOCAL TOOLING SETUP

### Verify Installed Tools

-   [ ] aws --version (CLI v2)
-   [ ] terraform version (\>= 1.6)
-   [ ] node -v
-   [ ] npm -v

### Configure AWS CLI

-   [x] aws configure sso (preferred) OR aws configure
-   [x] aws sts get-caller-identity
-   [x] aws sts get-caller-identity --profile AdministratorAccess-469072180942
-   [x] export AWS_PROFILE=AdministratorAccess-469072180942

------------------------------------------------------------------------

## PHASE 2 -- TERRAFORM REMOTE STATE SETUP

### Create Terraform State Backend

-   [ ] Create S3 bucket:
    journal-tfstate-`<account-id>`{=html}-`<region>`{=html}
-   [ ] Enable versioning on bucket
-   [ ] Create DynamoDB table: journal-tflock
-   [ ] Confirm both created successfully

### CLI Helper Scripts (recommended)

-   [ ] Run `scripts/setup/step-2-bootstrap-terraform-backend.sh` to create bucket + lock table
-   [ ] Run `scripts/setup/step-2b-create-backend-file.sh dev` to write backend.dev.tfbackend

### Configure Backend (manual alternative)

-   [ ] Copy backend.s3.tfbackend.example → backend.dev.tfbackend (if not using script)
-   [ ] Update bucket name, region, DynamoDB lock table name

------------------------------------------------------------------------

## PHASE 3 -- CONFIGURE TEMPLATE 1

### Update dev.tfvars

-   [ ] Set aws_region
-   [ ] Set unique cognito_domain_prefix
-   [ ] Review any cost-sensitive configs

### Terraform Init / Plan / Apply

-   [ ] Run `scripts/setup/step-3a-terraform-apply.sh dev`

### Capture Outputs

-   [ ] Run `scripts/setup/step-4a-export-outputs-to-env.sh dev`

------------------------------------------------------------------------

## PHASE 4 -- LOCAL WEB APP TEST

### Configure Environment

-   [ ] Copy .env.example → .env
-   [ ] Set VITE_API_BASE_URL
-   [ ] Set VITE_COGNITO_DOMAIN
-   [ ] Set VITE_COGNITO_CLIENT_ID
-   [ ] Set redirect URI to localhost

### Run Application

-   [ ] npm install
-   [ ] npm run dev
-   [ ] Confirm login works
-   [ ] Confirm CRUD works
-   [ ] Confirm AI endpoint (optional)

------------------------------------------------------------------------

## PHASE 5 -- COST CONTROL HABITS

### CloudWatch Logs

-   [ ] Confirm log retention is 7--14 days

### Bedrock Usage

-   [ ] Avoid AI endpoint unless needed
-   [ ] Monitor usage after first invocation

### Step Functions

-   [ ] Confirm no runaway workflows

------------------------------------------------------------------------

## PHASE 6 -- SHUT DOWN WHEN NOT USING

### Destroy Infrastructure

-   [ ] Run `scripts/destroy/step-1a-terraform-destroy.sh dev`

### Optional (True Zero Mode)

-   [ ] Run `scripts/destroy/step-1b-delete-terraform-backend.sh` (nukes backend)

------------------------------------------------------------------------

## WEEKLY COST CHECK (MANDATORY)

-   [ ] Check Billing Dashboard
-   [ ] Confirm total charges \< \$5
-   [ ] Review Budgets page
-   [ ] Review CloudWatch alarms

------------------------------------------------------------------------

## NOTES / ISSUES TRACKER

-   Issue 1:
-   Issue 2:
-   Issue 3:

------------------------------------------------------------------------

### Status

Deployment Status: ☐ Not Started ☐ In Progress ☐ Completed\
Last Reviewed: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
