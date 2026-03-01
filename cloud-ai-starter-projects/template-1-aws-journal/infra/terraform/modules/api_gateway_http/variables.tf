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

variable "enable_jwt_authorizer" {
  type    = bool
  default = true
}

variable "jwt_issuer" {
  type    = string
  default = ""
}

variable "jwt_audience" {
  type    = list(string)
  default = []
}

variable "routes" {
  type = map(object({
    route_key         = string
    lambda_arn        = string
    lambda_invoke_arn = string
    authorization     = optional(string, "JWT")
  }))
}
