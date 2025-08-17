locals {
  # Find the python executable, preferring python3.
  python_executable = fileexists("/usr/bin/python3") ? "/usr/bin/python3" : "/usr/bin/python"

  # Decode the JSON strings from the external data source into proper maps.
  config = {
    package_name       = data.external.config.result.package_name
    package_name_safe  = data.external.config.result.package_name_safe
    package_name_db    = data.external.config.result.package_name_db
    storage_queues     = jsondecode(data.external.config.result.storage_queues)
    storage_containers = jsondecode(data.external.config.result.storage_containers)
    storage_tables     = jsondecode(data.external.config.result.storage_tables)
  }
}

data "external" "config" {
  program = [local.python_executable, "${path.module}/scripts/get_tf_vars.py"]
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

resource "random_string" "storage_suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "azurerm_storage_account" "main" {
  name                     = "${local.config.package_name_safe}${random_string.storage_suffix.result}"
  resource_group_name      = data.azurerm_resource_group.existing.name
  location                 = data.azurerm_resource_group.existing.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_queue" "main" {
  for_each             = local.config.storage_queues
  name                 = each.value
  storage_account_name = azurerm_storage_account.main.name
}

resource "azurerm_storage_queue" "stage" {
  for_each             = local.config.storage_queues
  name                 = "${each.value}-stage"
  storage_account_name = azurerm_storage_account.main.name
}

resource "azurerm_storage_container" "main" {
  for_each              = local.config.storage_containers
  name                  = each.value
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "stage" {
  for_each              = local.config.storage_containers
  name                  = "${each.value}-stage"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_storage_table" "main" {
  for_each             = local.config.storage_tables
  name                 = each.value
  storage_account_name = azurerm_storage_account.main.name
}

resource "azurerm_storage_table" "stage" {
  for_each             = local.config.storage_tables
  name                 = "${each.value}stage"
  storage_account_name = azurerm_storage_account.main.name
}

resource "azurerm_application_insights" "main" {
  name                = local.config.package_name
  resource_group_name = data.azurerm_resource_group.existing.name
  location            = data.azurerm_resource_group.existing.location
  application_type    = "web"
}

resource "azurerm_linux_function_app" "main" {
  name                = local.config.package_name
  resource_group_name = data.azurerm_resource_group.existing.name
  location            = data.azurerm_resource_group.existing.location
  service_plan_id     = data.azurerm_service_plan.existing.id

  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key

  site_config {
    application_stack {
      python_version = "3.10"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    "WEBSITE_TIME_ZONE"                     = "America/New_York"
    "FUNCTIONS_WORKER_RUNTIME"              = "python"
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
    "AzureWebJobsStorage"                   = azurerm_storage_account.main.primary_connection_string
    "DB_HOST"                               = data.azurerm_mysql_flexible_server.existing.fqdn
    "DB_NAME"                               = azurerm_mysql_flexible_database.prod.name
    "DB_USER"                               = local.config.package_name
  }
}

resource "azurerm_linux_function_app_slot" "stage" {
  name            = "stage"
  function_app_id = azurerm_linux_function_app.main.id

  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.10"
    }
  }

  app_settings = {
    # These settings are sticky to the slot by default
    "DB_HOST"                               = data.azurerm_mysql_flexible_server.existing.fqdn
    "DB_NAME"                               = azurerm_mysql_flexible_database.stage.name,
    "DB_USER"                               = "${local.config.package_name}/stage",
    # Override storage resource names for stage
    "SHOW_DETAILS_QUEUE" = "${local.config.storage_queues.SHOW_DETAILS_QUEUE}-stage",
    "SHOW_UPSERT_QUEUE"  = "${local.config.storage_queues.SHOW_UPSERT_QUEUE}-stage",
    "SHOW_IDS_TABLE"     = "${local.config.storage_tables.SHOW_IDS_TABLE}stage",
    # Disable timer triggers in stage by setting a dummy value for their schedule
    "TIMER_TRIGGER_SCHEDULE" = "disabled"
  }
}

resource "azurerm_mysql_flexible_database" "prod" {
  name                = local.config.package_name_db
  resource_group_name = data.azurerm_resource_group.existing.name
  server_name         = data.azurerm_mysql_flexible_server.existing.name
  charset             = "utf8mb4"
  collation           = "utf8mb4_unicode_ci"
}

resource "azurerm_mysql_flexible_database" "stage" {
  name                = "${local.config.package_name_db}-stage"
  resource_group_name = data.azurerm_resource_group.existing.name
  server_name         = data.azurerm_mysql_flexible_server.existing.name
  charset             = "utf8mb4-unicode_ci"
  collation           = "utf8mb4_unicode_ci"
}

resource "azurerm_mysql_flexible_server_firewall_rule" "function_access" {
  for_each            = toset(azurerm_linux_function_app.main.possible_outbound_ip_addresses)
  name                = "allow-function-outbound-${index(azurerm_linux_function_app.main.possible_outbound_ip_addresses, each.value)}"
  resource_group_name = data.azurerm_resource_group.existing.name
  server_name         = data.azurerm_mysql_flexible_server.existing.name
  start_ip_address    = each.value
  end_ip_address      = each.value
}

# --- IMPORTANT --- #
# The following step cannot be performed by Terraform and must be run separately
# after the infrastructure is created. This script grants the function apps'
# managed identities access to their respective databases.
# You should run this from a shell where you are logged into Azure (e.g., Azure CLI).

# grant_db_access.sh
# #!/bin/bash
# RG_NAME="your_resource_group"
# MYSQL_SERVER_NAME="your_mysql_server"
# PROD_DB_NAME="tvbingefriend_show_service"
# STAGE_DB_NAME="tvbingefriend_show_service-stage"
# PROD_FUNCTION_NAME="tvbingefriend-show-service"
# STAGE_FUNCTION_NAME="tvbingefriend-show-service/slots/stage"

# PROD_MI_ID=$(az functionapp identity show --name $PROD_FUNCTION_NAME --resource-group $RG_NAME --query principalId -o tsv)
# STAGE_MI_ID=$(az functionapp identity show --name $STAGE_FUNCTION_NAME --resource-group $RG_NAME --query principalId -o tsv)

# az mysql flexible-server execute --name $MYSQL_SERVER_NAME --admin-user <your-admin> --admin-password <your-admin-pass> --database-name $PROD_DB_NAME --sql "DROP USER IF EXISTS '$PROD_FUNCTION_NAME'; CREATE AADUSER '$PROD_FUNCTION_NAME' IDENTIFIED BY '$PROD_MI_ID'; GRANT ALL PRIVILEGES ON \`$PROD_DB_NAME\`.* TO '$PROD_FUNCTION_NAME'@'%';"
# az mysql flexible-server execute --name $MYSQL_SERVER_NAME --admin-user <your-admin> --admin-password <your-admin-pass> --database-name $STAGE_DB_NAME --sql "DROP USER IF EXISTS '$STAGE_FUNCTION_NAME'; CREATE AADUSER '$STAGE_FUNCTION_NAME' IDENTIFIED BY '$STAGE_MI_ID'; GRANT ALL PRIVILEGES ON \`$STAGE_DB_NAME\`.* TO '$STAGE_FUNCTION_NAME'@'%';"
