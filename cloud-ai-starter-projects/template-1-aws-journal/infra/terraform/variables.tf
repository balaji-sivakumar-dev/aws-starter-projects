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

variable "tags" {
  type        = map(string)
  description = "Additional tags for all resources"
  default     = {}
}

variable "callback_urls" {
  type        = list(string)
  description = "Cognito callback URLs"
  default     = ["http://localhost:5173/callback"]
}

variable "logout_urls" {
  type        = list(string)
  description = "Cognito logout URLs"
  default     = ["http://localhost:5173/"]
}

variable "cognito_domain_prefix" {
  type        = string
  description = "Hosted UI domain prefix (must be globally unique per region)"
  default     = ""
}

variable "web_enable_cloudfront" {
  type        = bool
  description = "Enable CloudFront in front of the SPA bucket"
  default     = false
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention for Lambda and API logs"
  default     = 14
}

variable "bedrock_model_id" {
  type        = string
  description = "Bedrock model id for AI Gateway"
  default     = "amazon.nova-lite-v1:0"
}
