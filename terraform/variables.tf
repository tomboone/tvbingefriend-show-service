variable "resource_group_name" {
  type        = string
  description = "The name of the existing resource group."
}

variable "app_service_plan_name" {
  type        = string
  description = "The name of the existing App Service Plan."
}

variable "mysql_server_name" {
  type        = string
  description = "The name of the existing MySQL Flexible Server."
}

variable "project_name" {
  type        = string
  description = "The name of the project."
  default     = "tvbf-show-service"
}