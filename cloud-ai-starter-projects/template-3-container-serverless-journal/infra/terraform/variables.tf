variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "app_prefix" {
  type    = string
  default = "journal"
}

variable "env" {
  type    = string
  default = "dev"
}

variable "compute_mode" {
  type        = string
  description = "serverless | container | hybrid"
  default     = "serverless"
}
