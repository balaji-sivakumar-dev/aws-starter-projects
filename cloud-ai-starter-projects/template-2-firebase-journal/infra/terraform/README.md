# Terraform Root

Terraform manages Firebase/GCP foundation for Template 2.

Implemented in iteration 2:
- Project API enablement (`project_services`)
- Service accounts and IAM (`iam`)
- Firestore database (`firestore`)
- Async primitive queue (`workflow_primitives` via Cloud Tasks)
- Baseline log metric (`observability`)

Quick start:
```bash
cd infra/terraform
cp environments/dev/dev.tfvars.example environments/dev/dev.tfvars
terraform init
terraform plan -var-file=environments/dev/dev.tfvars
```
