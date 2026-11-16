terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # State local, fora do repositório (ver .gitignore). Ele guarda detalhes da
  # infraestrutura e nunca deve ser versionado.
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}
