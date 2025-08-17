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
  description = "The name of the existing Azure MySQL Flexible Server."
}

variable "package_name" {
  type        = string
  description = "The name of the package, used as a base for resource names."
  default     = "tvbingefriend-show-service"
}

variable "package_name_safe" {
  type        = string
  description = "A safe version of the package name for storage accounts (no special chars, lowercase)."
  default     = "tvbingefriendshowservice"
}

variable "package_name_db" {
  type        = string
  description = "The database-safe version of the package name (dashes replaced with underscores)."
  default     = "tvbingefriend_show_service"
}

variable "storage_queues" {
  type        = list(string)
  description = "A list of storage queue names to create."
  default     = ["show-details-queue", "show-upsert-queue"]
}

variable "storage_containers" {
  type        = list(string)
  description = "A list of storage container names to create."
  default     = ["thumbnails"]
}

variable "storage_tables" {
  type        = list(string)
  description = "A list of storage table names to create."
  default     = ["showdetails"]
}
