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
  description = "LLM provider: 'bedrock' (default, IAM-only) or 'openai' (needs OPENAI_API_KEY) or 'groq' (legacy)."
  default     = "bedrock"
}

variable "groq_model_id" {
  type        = string
  description = "Groq model ID (only used if llm_provider=groq)."
  default     = "llama-3.1-8b-instant"
}

variable "openai_llm_model" {
  type        = string
  description = "OpenAI model for RAG /ask (used when llm_provider=openai). gpt-4o-mini is recommended."
  default     = "gpt-4o-mini"
}

variable "embedding_provider" {
  type        = string
  description = "Embedding provider: 'bedrock' (Titan v2, default, IAM-only) or 'openai' (text-embedding-3-small)."
  default     = "bedrock"
}

variable "openai_embed_model" {
  type        = string
  description = "OpenAI embedding model (used when embedding_provider=openai)."
  default     = "text-embedding-3-small"
}

variable "openai_api_key" {
  type        = string
  description = "OpenAI API key. Leave empty when using bedrock providers. Store via step-2b-store-secrets.sh."
  default     = ""
  sensitive   = true
}

variable "admin_emails" {
  type        = string
  description = "Comma-separated admin email addresses. Populated automatically by step-2b-store-secrets.sh from .env.users (admin entries). See docs/AWS-Console-Setup.md."
  default     = ""
}
