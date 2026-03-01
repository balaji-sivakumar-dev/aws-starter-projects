variable "app_prefix" { type = string }
variable "env" { type = string }
variable "image_uri" { type = string }
variable "container_port" { type = number }
variable "journal_table_name" { type = string }
variable "workflow_arn" { type = string }
variable "cognito_issuer" { type = string }
variable "cognito_client_id" { type = string }
