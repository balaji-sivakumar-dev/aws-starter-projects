resource "google_cloud_tasks_queue" "process_entry_ai" {
  name     = "${var.app_prefix}-${var.env}-process-entry-ai"
  project  = var.project_id
  location = var.region

  rate_limits {
    max_dispatches_per_second = var.max_dispatches_per_second
    max_concurrent_dispatches = var.max_concurrent_dispatches
  }

  retry_config {
    max_attempts = 3
  }
}
