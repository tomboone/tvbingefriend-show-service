data "http" "mysql_ca_cert" {
  url = "https://cacerts.digicert.com/DigiCertGlobalRootG2.crt.pem"
}

data "azurerm_resource_group" "existing" {
  name = var.resource_group_name
}

data "azurerm_service_plan" "existing" {
  name                = var.app_service_plan_name
  resource_group_name = data.azurerm_resource_group.existing.name
}

data "azurerm_mysql_flexible_server" "existing" {
  name                = var.mysql_server_name
  resource_group_name = data.azurerm_resource_group.existing.name
}

resource "azurerm_storage_account" "storage_account" {
  name                     = replace(var.project_name, "-", "")
  resource_group_name      = data.azurerm_resource_group.existing.name
  location                 = data.azurerm_resource_group.existing.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

locals {
  config = {
    package_name = var.project_name
    storage_queues = {
      # App Setting Key  => Queue Name Prefix
      "INDEX_QUEUE_NAME"   = "index-queue"
      "DETAILS_QUEUE_NAME" = "details-queue"
    }
    storage_tables = {
      # App Setting Key  => Table Name Prefix
      "SHOW_IDS_TABLE_NAME" = "showidstable"
    }
  }
}

resource "azurerm_storage_queue" "index_queue" {
  name                 = local.config.storage_queues.INDEX_QUEUE_NAME
  storage_account_name = azurerm_storage_account.storage_account.name
}

resource "azurerm_storage_queue" "stage_index_queue" {
  name                 = "${local.config.storage_queues.INDEX_QUEUE_NAME}-stage"
  storage_account_name = azurerm_storage_account.storage_account.name
}

resource "azurerm_storage_queue" "details_queue" {
  name                 = local.config.storage_queues.DETAILS_QUEUE_NAME
  storage_account_name = azurerm_storage_account.storage_account.name
}

resource "azurerm_storage_queue" "stage_details_queue" {
  name                 = "${local.config.storage_queues.DETAILS_QUEUE_NAME}-stage"
  storage_account_name = azurerm_storage_account.storage_account.name
}

resource "azurerm_storage_table" "show_ids_table" {
  name                 = local.config.storage_tables.SHOW_IDS_TABLE_NAME
  storage_account_name = azurerm_storage_account.storage_account.name
}

resource "azurerm_application_insights" "main" {
  name                = var.project_name
  resource_group_name = data.azurerm_resource_group.existing.name
  location            = data.azurerm_resource_group.existing.location
  application_type    = "web"
}

resource "azurerm_linux_function_app" "main" {
  name                = var.project_name
  resource_group_name = data.azurerm_resource_group.existing.name
  location            = data.azurerm_resource_group.existing.location
  service_plan_id     = data.azurerm_service_plan.existing.id

  storage_account_name       = azurerm_storage_account.storage_account.name
  storage_account_access_key = azurerm_storage_account.storage_account.primary_access_key

  site_config {
    application_stack {
      python_version = "3.12"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  app_settings = merge(
    {
      "WEBSITE_TIME_ZONE"                     = "America/New_York"
      "FUNCTIONS_WORKER_RUNTIME"              = "python"
      "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
      "AzureWebJobsStorage"                   = azurerm_storage_account.storage_account.primary_connection_string
      "DB_HOST"                               = data.azurerm_mysql_flexible_server.existing.fqdn
      "DB_NAME"                               = azurerm_mysql_flexible_database.prod.name
      "DB_USER"                               = var.project_name
      "MYSQL_SSL_CA_CONTENT"                  = data.http.mysql_ca_cert.response_body
    },
    { for k, v in local.config.storage_queues : k => v },
    { for k, v in local.config.storage_tables : k => v }
  )
}

# noinspection HILUnresolvedReference
resource "azurerm_linux_function_app_slot" "stage" {
  name            = "stage"
  function_app_id = azurerm_linux_function_app.main.id

  storage_account_name       = azurerm_storage_account.storage_account.name
  storage_account_access_key = azurerm_storage_account.storage_account.primary_access_key

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = merge(
    {
      # These settings are sticky to the slot by default
      "DB_HOST"                = data.azurerm_mysql_flexible_server.existing.fqdn
      "DB_NAME"                = azurerm_mysql_flexible_database.stage.name
      "DB_USER"                = "${local.config.package_name}-stage"
      "TIMER_TRIGGER_SCHEDULE" = "disabled"
      "MYSQL_SSL_CA_CONTENT"   = data.http.mysql_ca_cert.response_body
    },
    # Override storage resource names for stage dynamically
    { for k, v in local.config.storage_queues : k => "${v}-stage" },
    { for k, v in local.config.storage_tables : k => "${v}-stage" }
  )
}

resource "azurerm_mysql_flexible_database" "prod" {
  name                = replace(var.project_name, "-", "")
  resource_group_name = data.azurerm_resource_group.existing.name
  server_name         = data.azurerm_mysql_flexible_server.existing.name
  charset             = "utf8mb4"
  collation           = "utf8mb4_unicode_ci"
}

resource "azurerm_mysql_flexible_database" "stage" {
  name                = "${replace(var.project_name, "-", "")}-stage"
  resource_group_name = data.azurerm_resource_group.existing.name
  server_name         = data.azurerm_mysql_flexible_server.existing.name
  charset             = "utf8mb4"
  collation           = "utf8mb4_unicode_ci"
}
