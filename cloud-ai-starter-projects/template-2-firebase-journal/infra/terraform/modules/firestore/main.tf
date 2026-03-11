resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = var.database_name
  location_id = var.location
  type        = "FIRESTORE_NATIVE"
}
