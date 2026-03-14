variable "app_prefix" { type = string }
variable "env" { type = string }
variable "jwt_issuer" { type = string }
variable "jwt_audience" { type = list(string) }

variable "lambda_routes" {
  type = map(object({
    route_key         = string
    authorization     = string
    lambda_arn        = string
    lambda_invoke_arn = string
  }))
  default = {}
}

variable "container_routes" {
  type = map(object({
    route_key       = string
    authorization   = string
    integration_uri = string
  }))
  default = {}
}

variable "cors_allow_origins" {
  type        = list(string)
  description = "Allowed CORS origins for the HTTP API"
  default     = ["*"]
}
