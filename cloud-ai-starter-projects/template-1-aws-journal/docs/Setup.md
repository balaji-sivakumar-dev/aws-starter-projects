# Setup

## Local Prerequisites
- Terraform >= 1.6
- AWS CLI configured (`aws configure` / named profile)
- Python 3.11+ for local checks

## AWS Prerequisites
- Active AWS account and deployment credentials
- Bedrock access granted for configured `BEDROCK_MODEL_ID`

## Terraform (Dev)
```bash
cd infra/terraform
terraform init
terraform plan -var-file=environments/dev/dev.tfvars
terraform apply -var-file=environments/dev/dev.tfvars
```

## Remote State (Optional)
- Copy `backend.s3.tfbackend.example` to your own backend config values and run `terraform init -backend-config=<file>`.
