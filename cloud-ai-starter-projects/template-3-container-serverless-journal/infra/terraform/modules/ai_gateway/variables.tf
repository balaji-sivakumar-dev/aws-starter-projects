variable "app_prefix" { type = string }
variable "env" { type = string }
variable "source_dir" { type = string }
variable "handler" { type = string }
variable "runtime" { type = string }
variable "journal_table_arn" { type = string }
variable "journal_table_name" { type = string }
variable "bedrock_model_id" { type = string }
variable "llm_provider" {
  type    = string
  default = "groq"
}
variable "groq_api_key" {
  type      = string
  default   = ""
  sensitive = true
}
variable "groq_model_id" {
  type    = string
  default = "llama-3.1-8b-instant"
}
