terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Remote backend placeholder; keep local backend default for first-run simplicity.
  # backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}
