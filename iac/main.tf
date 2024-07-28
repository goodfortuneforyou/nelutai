terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">=3.109.0"
    }
  }
}

provider "azurerm" {
  features {

  }
}

variable "openai_key" {
  type = string
}

variable "openai_endpoint" {
  type = string
}

variable "viber_auth_token" {
  type = string
}

variable "openai_api_version" {
  type    = string
  default = "2023-06-01-preview"
}

variable "openai_embeddings_version" {
  type    = string
  default = "2023-05-15"
}

variable "openai_chat_deployment" {
  type    = string
  default = "nelutai-chat"
}

variable "openai_embeddings_deployment" {
  type    = string
  default = "nelutai-embeddings"
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "dev" {
  name     = "nelutai-dev-tf"
  location = "westeurope"
  tags = {
    environment = "dev"
  }
}

resource "azurerm_storage_account" "data" {
  name                     = "nelutaichromadatasa"
  resource_group_name      = azurerm_resource_group.dev.name
  location                 = azurerm_resource_group.dev.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "chats" {
  name                  = "chats"
  storage_account_name  = azurerm_storage_account.data.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "chroma" {
  name                  = "chroma"
  storage_account_name  = azurerm_storage_account.data.name
  container_access_type = "private"
}

resource "azurerm_storage_blob" "chroma_zip" {
  name                   = "index.zip"
  storage_account_name   = azurerm_storage_account.data.name
  storage_container_name = azurerm_storage_container.chroma.name
  type                   = "Block"
  source                 = "index.zip"
}

resource "azurerm_log_analytics_workspace" "ws" {
  name                = "nelutai-workspace-viber"
  location            = azurerm_resource_group.dev.location
  resource_group_name = azurerm_resource_group.dev.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_virtual_network" "vnet" {
  name                = "vnet"
  location            = azurerm_resource_group.dev.location
  resource_group_name = azurerm_resource_group.dev.name
  address_space       = ["10.0.0.0/16"]
}

resource "azurerm_subnet" "subnet1" {
  name                 = "subnet1"
  resource_group_name  = azurerm_resource_group.dev.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.0.0/21"]
}

resource "azurerm_container_app_environment" "env" {
  name                       = "nelutai-environment-viber"
  location                   = azurerm_resource_group.dev.location
  resource_group_name        = azurerm_resource_group.dev.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.ws.id
  infrastructure_subnet_id   = azurerm_subnet.subnet1.id
}

resource "azurerm_container_app" "chatbot" {
  name                         = "nelutai-viber-chatbot"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.dev.name
  revision_mode                = "Single"

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
  secret {
    name        = "openai-key"
    value = var.openai_key
  }
  secret {
    name        = "openai-endpoint"
    value = var.openai_endpoint
  }
  secret {
    name        = "openai-chat-deployment"
    value  = var.openai_chat_deployment
  }
  secret {
    name        = "openai-embeddings-deployment"
    value  = var.openai_embeddings_deployment
  }
  secret {
    name        = "openai-api-version"
    value = var.openai_api_version
  }
  secret {
    name        = "openai-embeddings-version"
    value = var.openai_api_version
  }
  template {
    max_replicas = 1
    container {
      name   = "nelutai"
      image  = "nelutai/nelutai:latest"
      cpu    = 1
      memory = "2Gi"
      env {
        name  = "HANDLER"
        value = "viber"
      }
      env {
        name  = "SA_NAME"
        value = azurerm_storage_account.data.name
      }
      env {
        name  = "SA_KEY"
        value = azurerm_storage_account.data.primary_access_key
      }
      env {
        name  = "BLOB_ENDPOINT"
        value = azurerm_storage_account.data.primary_blob_endpoint
      }
      env {
        name  = "SA_CONTAINER_CHATS"
        value = azurerm_storage_container.chats.name
      }
      env {
        name  = "SA_CONTAINER_CHROMA"
        value = azurerm_storage_container.chroma.name
      }
      env {
        name  = "VIBER_AUTH_TOKEN"
        value = var.viber_auth_token
      }
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "openai-key"
      }
      env {
        name        = "AZURE_OPENAI_ENDPOINT"
        secret_name = "openai-endpoint"
      }
      env {
        name        = "AZURE_OPENAI_DEPLOYMENT_NAME"
        secret_name = "openai-chat-deployment"
      }
      env {
        name        = "AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDINGS"
        secret_name = "openai-embeddings-deployment"
      }
      env {
        name        = "AZURE_OPENAI_API_VERSION"
        secret_name = "openai-api-version"
      }
      env {
        name        = "AZURE_OPENAI_API_VERSION_EMBEDDINGS"
        secret_name = "openai-embeddings-version"
      }
    }
  }
}
