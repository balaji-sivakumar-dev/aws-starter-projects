output "service_url" {
  value = length(aws_apprunner_service.this) > 0 ? "https://${aws_apprunner_service.this[0].service_url}" : ""
}
