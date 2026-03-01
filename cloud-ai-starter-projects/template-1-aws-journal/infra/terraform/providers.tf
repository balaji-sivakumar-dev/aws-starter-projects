terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote backend placeholder; keep local backend default for first-run simplicity.
  # backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}
