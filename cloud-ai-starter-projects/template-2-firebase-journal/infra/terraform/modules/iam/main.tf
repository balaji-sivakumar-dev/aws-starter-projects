resource "google_service_account" "functions" {
  account_id   = "${var.app_prefix}-${var.env}-fn"
  display_name = "${var.app_prefix}-${var.env} functions service account"
  project      = var.project_id
}

resource "google_service_account" "ai_gateway" {
  account_id   = "${var.app_prefix}-${var.env}-ai"
  display_name = "${var.app_prefix}-${var.env} ai gateway service account"
  project      = var.project_id
}

resource "google_project_iam_member" "functions_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.functions.email}"
}

resource "google_project_iam_member" "functions_tasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.functions.email}"
}

resource "google_project_iam_member" "functions_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.functions.email}"
}

resource "google_project_iam_member" "ai_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.ai_gateway.email}"
}

resource "google_project_iam_member" "ai_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.ai_gateway.email}"
}

resource "google_project_iam_member" "ai_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.ai_gateway.email}"
}
