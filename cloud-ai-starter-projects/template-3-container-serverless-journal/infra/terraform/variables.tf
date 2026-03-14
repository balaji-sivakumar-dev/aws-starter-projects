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

variable "cors_allow_origins" {
  type        = list(string)
  description = "CORS allowed origins for the API Gateway. API GW v2 only accepts exact URLs or \"*\" (no wildcards). Security is enforced by JWT authorizer, not CORS."
  default     = ["*"]
}

variable "ai_enabled" {
  type        = string
  description = "Enable AI enrichment (true/false). Set to true only when an LLM provider is configured."
  default     = "false"
}

variable "llm_provider" {
  type        = string
  description = "LLM provider to use for AI enrichment: 'groq' or 'bedrock'."
  default     = "groq"
}

variable "groq_api_key" {
  type        = string
  description = "Groq API key. Required when llm_provider = 'groq'."
  default     = ""
  sensitive   = true
}

variable "groq_model_id" {
  type        = string
  description = "Groq model ID to use (e.g. llama-3.1-8b-instant, llama-3.3-70b-versatile)."
  default     = "llama-3.1-8b-instant"
}
