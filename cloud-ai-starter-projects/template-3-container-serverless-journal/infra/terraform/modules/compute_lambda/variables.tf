variable "app_prefix" { type = string }
variable "env" { type = string }
variable "source_dir" { type = string }
variable "handler" { type = string }
variable "runtime" { type = string }
variable "journal_table_arn" { type = string }
variable "journal_table_name" { type = string }
variable "workflow_arn" { type = string }

variable "ai_enabled" {
  type        = string
  description = "Set to 'true' to enable AI enrichment via Step Functions"
  default     = "false"
}

variable "admin_emails" {
  type        = string
  description = "Comma-separated admin email addresses (from .env.users admin entries)"
  default     = ""
}

variable "llm_provider" {
  type        = string
  description = "LLM provider for RAG /ask: 'bedrock' (default, IAM-only) or 'openai' (needs OPENAI_API_KEY)"
  default     = "bedrock"
}

variable "bedrock_model_id" {
  type        = string
  description = "Bedrock model ID for LLM inference in RAG /ask route"
  default     = "amazon.nova-lite-v1:0"
}

variable "openai_llm_model" {
  type        = string
  description = "OpenAI model for RAG /ask (used when llm_provider=openai)"
  default     = "gpt-4o-mini"
}

variable "embedding_provider" {
  type        = string
  description = "Embedding provider: 'bedrock' (Titan v2, default) or 'openai' (text-embedding-3-small)"
  default     = "bedrock"
}

variable "openai_embed_model" {
  type        = string
  description = "OpenAI embedding model (used when embedding_provider=openai)"
  default     = "text-embedding-3-small"
}

variable "openai_api_key" {
  type        = string
  description = "OpenAI API key (leave empty when using bedrock providers)"
  default     = ""
  sensitive   = true
}

variable "vector_store" {
  type        = string
  description = "Vector store backend: 'dynamodb' (default, serverless) or 'chroma' (local dev only)"
  default     = "dynamodb"
}

variable "groq_model_id" {
  type        = string
  description = "Groq model ID for RAG /ask (used when llm_provider=groq)."
  default     = "llama-3.1-8b-instant"
}

variable "bedrock_region" {
  type        = string
  description = "AWS region to use for Bedrock calls. Defaults to us-east-1 to ensure Titan Embeddings V2 availability (not in ca-central-1)."
  default     = "us-east-1"
}
