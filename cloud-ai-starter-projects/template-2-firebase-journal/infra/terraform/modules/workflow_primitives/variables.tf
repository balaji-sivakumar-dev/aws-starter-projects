variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "app_prefix" {
  type = string
}

variable "env" {
  type = string
}

variable "max_dispatches_per_second" {
  type    = number
  default = 5
}

variable "max_concurrent_dispatches" {
  type    = number
  default = 5
}

variable "depends_on_apis" {
  type    = list(string)
  default = []
}
