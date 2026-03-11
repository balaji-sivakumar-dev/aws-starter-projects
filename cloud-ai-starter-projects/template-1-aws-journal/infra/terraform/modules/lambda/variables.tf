variable "app_prefix" {
  type = string
}

variable "env" {
  type = string
}

variable "log_retention_days" {
  type    = number
  default = 14
}

variable "functions" {
  type = map(object({
    handler     = string
    runtime     = string
    source_dir  = string
    timeout     = optional(number, 30)
    memory_size = optional(number, 256)
    environment = optional(map(string), {})
    policy_statements = optional(list(object({
      sid       = optional(string)
      effect    = optional(string, "Allow")
      actions   = list(string)
      resources = list(string)
    })), [])
  }))
}
