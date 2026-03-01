output "enabled_services" {
  value = [for svc in google_project_service.services : svc.service]
}
