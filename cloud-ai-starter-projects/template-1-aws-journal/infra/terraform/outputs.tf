output "api_base_url" {
  value       = module.api_gateway_http.api_endpoint
  description = "HTTP API base URL"
}

output "cognito_domain" {
  value       = module.auth_cognito.hosted_ui_domain
  description = "Cognito hosted UI domain"
}

output "cognito_client_id" {
  value       = module.auth_cognito.user_pool_client_id
  description = "Cognito app client id"
}

output "region" {
  value       = var.aws_region
  description = "AWS region"
}

output "web_bucket_name" {
  value       = module.s3_spa_hosting.bucket_name
  description = "S3 bucket name for SPA"
}

output "site_url" {
  value       = module.s3_spa_hosting.site_url
  description = "Site URL for the SPA"
}
