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
