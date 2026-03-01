# Output names locked by template spec; values added during implementation.
output "api_base_url" {
  value       = ""
  description = "HTTP API base URL"
}

output "cognito_domain" {
  value       = ""
  description = "Cognito hosted UI domain"
}

output "cognito_client_id" {
  value       = ""
  description = "Cognito app client id"
}

output "region" {
  value       = var.aws_region
  description = "AWS region"
}

output "web_bucket_name" {
  value       = ""
  description = "S3 bucket name for SPA"
}

output "site_url" {
  value       = ""
  description = "Site URL for the SPA"
}
