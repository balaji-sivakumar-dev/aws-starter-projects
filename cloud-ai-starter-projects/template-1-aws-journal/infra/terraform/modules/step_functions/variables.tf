variable "app_prefix" {
  type = string
}

variable "env" {
  type = string
}

variable "definition_path" {
  type        = string
  description = "Path to the ASL state machine definition"
}

variable "definition_substitutions" {
  type        = map(string)
  default     = {}
  description = "Template substitutions for ASL definition"
}

variable "lambda_invoke_arns" {
  type        = list(string)
  default     = []
  description = "Lambda ARNs callable by the state machine"
}
