variable "aws_region" {
  type        = string
  description = "AWS region for deployment"
  default     = "us-east-1"
}

variable "app_prefix" {
  type        = string
  description = "Application prefix used in naming"
  default     = "journal"
}

variable "env" {
  type        = string
  description = "Environment name"
  default     = "dev"
}
