variable "app_prefix" {
  type = string
}

variable "env" {
  type = string
}

variable "enable_ttl" {
  type        = bool
  default     = false
  description = "Enable TTL on the single table"
}

variable "ttl_attribute" {
  type        = string
  default     = "ttl"
  description = "TTL attribute name"
}
