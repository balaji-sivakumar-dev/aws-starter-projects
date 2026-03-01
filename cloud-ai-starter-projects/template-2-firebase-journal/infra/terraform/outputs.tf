output "project_id" {
  value       = var.project_id
  description = "GCP project id"
}

output "region" {
  value       = var.region
  description = "Default region"
}

output "functions_service_account_email" {
  value       = module.iam.functions_service_account_email
  description = "Service account email for Cloud Functions"
}

output "ai_gateway_service_account_email" {
  value       = module.iam.ai_gateway_service_account_email
  description = "Service account email for AI Gateway execution"
}

output "workflow_identifier" {
  value       = module.workflow_primitives.queue_id
  description = "Cloud Tasks queue identifier for async AI processing"
}

output "workflow_queue_name" {
  value       = module.workflow_primitives.queue_name
  description = "Cloud Tasks queue short name"
}

output "firestore_database_name" {
  value       = module.firestore.database_name
  description = "Firestore database id"
}
