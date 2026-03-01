resource "google_logging_metric" "api_errors" {
  project = var.project_id
  name    = "${var.app_prefix}_${var.env}_api_errors"
  filter  = "severity>=ERROR AND jsonPayload.requestId:*"

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}
