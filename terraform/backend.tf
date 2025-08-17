terraform {
  backend "azurerm" {
    resource_group_name  = "<YOUR_TERRAFORM_STATE_RG>"
    storage_account_name = "<YOUR_TERRAFORM_STATE_SA>"
    container_name       = "tfstate"
    key                  = "tvbingefriend-show-service.terraform.tfstate"
  }
}
