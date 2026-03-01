# GCP/Firebase and Terraform Setup Guide (CLI-First)

This guide prefers CLI commands wherever possible.

## 1) Required UI-only steps (minimum)
1. Create Google Cloud account and enable billing.
2. Create Firebase project link (if CLI fails due org policy).
3. If needed by org policy, enable Gemini model access in Google Cloud Console.

Everything else below is CLI-first.

## 2) Install and verify tools
- Google Cloud SDK (`gcloud`)
- Terraform >= 1.6
- Firebase CLI
- Node.js 20+

```bash
gcloud --version
terraform version
firebase --version
node -v
npm -v
```

## 3) Authenticate and select project (CLI)
```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

(Optional) set default region:
```bash
gcloud config set functions/region us-central1
gcloud config set run/region us-central1
```

## 4) Prepare Terraform variables
```bash
cd infra/terraform
cp environments/dev/dev.tfvars.example environments/dev/dev.tfvars
```

Edit `environments/dev/dev.tfvars` with your project and region.

## 5) Terraform apply

Local state quick start:
```bash
terraform init
terraform plan -var-file=environments/dev/dev.tfvars
terraform apply -var-file=environments/dev/dev.tfvars
```

Remote state (recommended):
1. Create GCS bucket for state (CLI):
```bash
gsutil mb -l us-central1 gs://YOUR_TF_STATE_BUCKET
gsutil versioning set on gs://YOUR_TF_STATE_BUCKET
```
2. Create backend config file from `backend.gcs.tfbackend.example`.
3. Re-init:
```bash
terraform init -reconfigure -backend-config=backend.dev.tfbackend
```

## 6) Capture Terraform outputs
```bash
terraform output
terraform output -raw project_id
terraform output -raw region
terraform output -raw workflow_queue_name
```

## 7) Deploy backend (Firebase CLI)
From template root:
```bash
firebase use YOUR_PROJECT_ID
firebase deploy --only functions
```

Set required function env variables before deploy (preferred CLI):
```bash
firebase functions:config:set \
  app.queue_name="journal-dev-process-entry-ai" \
  app.queue_location="us-central1" \
  app.ai_processor_url="https://YOUR_PROCESSOR_URL" \
  app.vertex_location="us-central1" \
  app.vertex_model="gemini-2.0-flash-lite"
```

## 8) Configure and run web app locally
```bash
cd apps/web
cp .env.example .env
```

Fill `.env` values:
- Firebase app config (`VITE_FIREBASE_*`)
- `VITE_API_BASE_URL` from deployed functions URL

Run:
```bash
npm install
npm run dev
```

## 9) Deploy hosting
```bash
cd ../../
npm --prefix apps/web install
npm --prefix apps/web run build
firebase deploy --only hosting
```

## 10) Destroy / cleanup
```bash
cd infra/terraform
terraform destroy -var-file=environments/dev/dev.tfvars
```

Then optionally remove Firebase project resources not managed by Terraform using CLI/Console.
