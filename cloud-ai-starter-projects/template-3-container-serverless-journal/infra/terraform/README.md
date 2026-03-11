# Terraform Root

Template 3 uses a plug-in compute strategy behind a stable API edge.

## Current implementation
- Shared modules: `auth`, `api_edge`, `db`, `workflow`, `web_hosting`
- Compute adapters: `compute_lambda`, `compute_container`
- Mode switch: `compute_mode` (`serverless`, `container`, `hybrid`)

## Quick start
```bash
cd infra/terraform
cp environments/dev/dev.tfvars.example environments/dev/dev.tfvars
terraform init
terraform plan -var-file=environments/dev/dev.tfvars
```
