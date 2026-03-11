# Migration Guide

## Serverless -> Container
1. Keep existing auth/db/workflow modules unchanged.
2. Build and publish container image for `services/container_api`.
3. Set `compute_mode="container"` and `container_image_uri` in tfvars.
4. Apply Terraform and verify same API contract smoke tests.

## Serverless -> Hybrid
1. Set `compute_mode="hybrid"`.
2. Keep lambda and container adapters deployed simultaneously.
3. Route split logic remains in edge module wiring while responses stay identical.

## Rollback
- Revert `compute_mode` to previous value and re-apply Terraform.
- Client stays unchanged because base routes and auth remain stable.
