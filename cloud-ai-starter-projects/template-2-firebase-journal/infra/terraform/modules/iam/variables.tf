variable "project_id" {
  type = string
}

variable "app_prefix" {
  type = string
}

variable "env" {
  type = string
}

variable "labels" {
  type    = map(string)
  default = {}
}

variable "depends_on_apis" {
  type    = list(string)
  default = []
}
