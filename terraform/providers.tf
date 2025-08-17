terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">=3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">=3.0"
    }
  }
}

variable "subscription_id" {
  type        = string
  description = "The Azure subscription ID."
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}
