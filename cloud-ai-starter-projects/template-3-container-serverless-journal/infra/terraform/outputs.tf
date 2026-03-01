output "api_base_url" {
  value       = ""
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
