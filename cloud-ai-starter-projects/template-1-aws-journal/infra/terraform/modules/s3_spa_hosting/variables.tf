variable "app_prefix" {
  type = string
}

variable "env" {
  type = string
}

variable "enable_cloudfront" {
  type    = bool
  default = false
}

variable "force_destroy" {
  type    = bool
  default = true
}
