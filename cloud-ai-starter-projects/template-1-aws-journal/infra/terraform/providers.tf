terraform {
  required_version = ">= 1.6.0"

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.5"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote backend placeholder; local backend remains default so first runs work locally.
  # backend "s3" {}
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(
      {
        App = var.app_prefix
        Env = var.env
      },
      var.tags
    )
  }
}
