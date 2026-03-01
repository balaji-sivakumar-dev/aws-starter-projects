variable "project_id" {
  type        = string
  description = "GCP project id"
}

variable "region" {
  type        = string
  description = "GCP region"
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
