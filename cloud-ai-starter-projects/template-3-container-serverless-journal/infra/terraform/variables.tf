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

  validation {
    condition     = contains(["serverless", "container", "hybrid"], var.compute_mode)
    error_message = "compute_mode must be one of: serverless, container, hybrid"
  }
}

variable "callback_urls" {
  type    = list(string)
  default = ["http://localhost:5173/callback"]
}

variable "logout_urls" {
  type    = list(string)
  default = ["http://localhost:5173/"]
}

variable "cognito_domain_prefix" {
  type    = string
  default = ""
}

variable "container_image_uri" {
  type        = string
  description = "Container image URI for App Runner service"
  default     = ""
}

variable "container_port" {
  type    = number
  default = 8080
}

variable "web_enable_cloudfront" {
  type    = bool
  default = false
}

variable "bedrock_model_id" {
  type    = string
  default = "amazon.nova-lite-v1:0"
}
