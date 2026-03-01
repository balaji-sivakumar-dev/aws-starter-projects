output "project_id" {
  value       = var.project_id
  description = "GCP project id"
}

output "region" {
  value       = var.region
  description = "Default region"
}

output "functions_service_account_email" {
  value       = ""
  description = "Service account email for Cloud Functions"
}

output "workflow_identifier" {
  value       = ""
  description = "Workflow or queue identifier for async AI processing"
}
