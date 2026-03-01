output "functions_service_account_email" {
  value = google_service_account.functions.email
}

output "ai_gateway_service_account_email" {
  value = google_service_account.ai_gateway.email
}
