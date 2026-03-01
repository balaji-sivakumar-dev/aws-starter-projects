variable "project_id" {
  type        = string
  description = "GCP project id"
}

variable "region" {
  type        = string
  description = "GCP region"
  default     = "us-central1"
}

variable "firestore_location" {
  type        = string
  description = "Firestore database location"
  default     = "us-central1"
}

variable "app_prefix" {
  type        = string
  description = "App prefix used for naming"
  default     = "journal"
}

variable "env" {
  type        = string
  description = "Environment name"
  default     = "dev"
}

variable "queue_region" {
  type        = string
  description = "Cloud Tasks queue region"
  default     = "us-central1"
}

variable "queue_max_dispatches_per_second" {
  type        = number
  description = "Queue dispatch rate limit"
  default     = 5
}

variable "queue_max_concurrent_dispatches" {
  type        = number
  description = "Queue concurrent dispatch limit"
  default     = 5
}

variable "labels" {
  type        = map(string)
  description = "Common labels"
  default     = {}
}
