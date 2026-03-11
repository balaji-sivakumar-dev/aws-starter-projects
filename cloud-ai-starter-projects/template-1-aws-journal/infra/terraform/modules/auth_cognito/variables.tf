variable "app_prefix" {
  type = string
}

variable "env" {
  type = string
}

variable "domain_prefix" {
  type        = string
  description = "Cognito hosted UI domain prefix"
}

variable "callback_urls" {
  type = list(string)
}

variable "logout_urls" {
  type = list(string)
}
