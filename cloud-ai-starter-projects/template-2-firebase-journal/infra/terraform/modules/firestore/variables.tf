variable "project_id" {
  type = string
}

variable "location" {
  type = string
}

variable "database_name" {
  type    = string
  default = "(default)"
}

variable "depends_on_apis" {
  type    = list(string)
  default = []
}
