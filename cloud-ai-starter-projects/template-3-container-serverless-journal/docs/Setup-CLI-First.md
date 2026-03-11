# Template 3 Setup Guide (CLI-First)

## 1) Required UI-only minimum
- AWS account signup / billing / MFA
- Optional: Bedrock model access enablement if required in your account/region

Everything else should be done via CLI.

## 2) Tooling
```bash
aws --version
terraform version
node -v
npm -v
```

## 3) AWS auth
```bash
aws configure --profile template3-dev
export AWS_PROFILE=template3-dev
aws sts get-caller-identity
```

## 4) Terraform config
```bash
cd infra/terraform
cp environments/dev/dev.tfvars.example environments/dev/dev.tfvars
```

Update `dev.tfvars`:
- `compute_mode` = `serverless` | `container` | `hybrid`
- If container/hybrid: set `container_image_uri`
- Set unique `cognito_domain_prefix`

## 5) Terraform apply
```bash
terraform init
terraform plan -var-file=environments/dev/dev.tfvars
terraform apply -var-file=environments/dev/dev.tfvars
```

## 6) Build/push container image (container/hybrid)
```bash
cd ../../services/container_api
npm install
# build docker image and push to ECR, then set container_image_uri in tfvars
```

## 7) Web app
```bash
cd ../../apps/web
cp .env.example .env
```

Fill values from Terraform outputs:
- `VITE_API_BASE_URL`
- `VITE_COGNITO_DOMAIN`
- `VITE_COGNITO_CLIENT_ID`

Run:
```bash
npm install
npm run dev
```

## 8) Destroy
```bash
cd ../infra/terraform
terraform destroy -var-file=environments/dev/dev.tfvars
```
