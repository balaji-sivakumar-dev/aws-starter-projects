output "api_base_url" {
  value       = module.api_edge.api_endpoint
  description = "Stable API base URL"
}

output "compute_mode" {
  value       = var.compute_mode
  description = "Selected compute mode"
}

output "region" {
  value       = var.aws_region
  description = "AWS region"
}

output "cognito_domain" {
  value       = module.auth.hosted_ui_domain
  description = "Cognito hosted UI domain"
}

output "cognito_client_id" {
  value       = module.auth.user_pool_client_id
  description = "Cognito app client id"
}

output "web_bucket_name" {
  value       = module.web_hosting.bucket_name
  description = "Web static bucket"
}

output "site_url" {
  value       = module.web_hosting.site_url
  description = "Static site URL"
}

output "container_service_url" {
  value       = local.use_container_api ? module.compute_container[0].service_url : null
  description = "Container API URL when container mode is enabled"
}

output "cloudfront_distribution_id" {
  value       = module.web_hosting.cloudfront_distribution_id
  description = "CloudFront distribution ID for cache invalidation"
}
