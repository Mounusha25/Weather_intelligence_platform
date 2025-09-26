# Terraform configuration for Weather Intelligence Platform
# Deploys Azure resources for real-time weather analytics

terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Variables
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "weather-intelligence"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US 2"
}

variable "kusto_sku" {
  description = "Kusto cluster SKU"
  type        = string
  default     = "Dev(No SLA)_Standard_D11_v2"
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "Weather Intelligence Platform"
  }
}

# Event Hub Namespace
resource "azurerm_eventhub_namespace" "weather" {
  name                = "evhns-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"
  capacity            = 2

  tags = azurerm_resource_group.main.tags
}

# Event Hub
resource "azurerm_eventhub" "weather_telemetry" {
  name                = "weather-telemetry"
  namespace_name      = azurerm_eventhub_namespace.weather.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = 4
  message_retention   = 1
}

# Event Hub Consumer Group
resource "azurerm_eventhub_consumer_group" "weather_analytics" {
  name                = "weather-analytics"
  namespace_name      = azurerm_eventhub_namespace.weather.name
  eventhub_name       = azurerm_eventhub.weather_telemetry.name
  resource_group_name = azurerm_resource_group.main.name
}

# Kusto Cluster
resource "azurerm_kusto_cluster" "weather" {
  name                = "kc-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku {
    name     = var.kusto_sku
    capacity = 1
  }

  tags = azurerm_resource_group.main.tags
}

# Kusto Database
resource "azurerm_kusto_database" "weather_intelligence" {
  name                = "WeatherIntelligence"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  cluster_name        = azurerm_kusto_cluster.weather.name
}

# Storage Account for ML models and data
resource "azurerm_storage_account" "weather_data" {
  name                     = "sa${replace(var.project_name, "-", "")}${var.environment}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  tags = azurerm_resource_group.main.tags
}

# Storage Container for ML models
resource "azurerm_storage_container" "ml_models" {
  name                  = "ml-models"
  storage_account_name  = azurerm_storage_account.weather_data.name
  container_access_type = "private"
}

# Application Insights
resource "azurerm_application_insights" "weather" {
  name                = "ai-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "other"

  tags = azurerm_resource_group.main.tags
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "weather" {
  name                = "law-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = azurerm_resource_group.main.tags
}

# Container Registry for Databricks images
resource "azurerm_container_registry" "weather" {
  name                = "cr${replace(var.project_name, "-", "")}${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"

  tags = azurerm_resource_group.main.tags
}

# Key Vault for secrets
resource "azurerm_key_vault" "weather" {
  name                = "kv-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  tags = azurerm_resource_group.main.tags
}

# Data sources
data "azurerm_client_config" "current" {}

# Outputs for application configuration
output "eventhub_connection_string" {
  description = "Event Hub connection string"
  value       = azurerm_eventhub_namespace.weather.default_primary_connection_string
  sensitive   = true
}

output "kusto_cluster_uri" {
  description = "Kusto cluster URI"
  value       = azurerm_kusto_cluster.weather.uri
}

output "kusto_database_name" {
  description = "Kusto database name"
  value       = azurerm_kusto_database.weather_intelligence.name
}

output "application_insights_key" {
  description = "Application Insights instrumentation key"
  value       = azurerm_application_insights.weather.instrumentation_key
  sensitive   = true
}

output "storage_account_name" {
  description = "Storage account name for ML models"
  value       = azurerm_storage_account.weather_data.name
}

output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

# Additional configurations for production
resource "azurerm_monitor_autoscale_setting" "kusto" {
  count               = var.environment == "prod" ? 1 : 0
  name                = "autoscale-kusto-${var.project_name}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  target_resource_id  = azurerm_kusto_cluster.weather.id

  profile {
    name = "default"

    capacity {
      default = 1
      minimum = 1
      maximum = 10
    }

    rule {
      metric_trigger {
        metric_name        = "CPU"
        metric_resource_id = azurerm_kusto_cluster.weather.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "GreaterThan"
        threshold          = 75
      }

      scale_action {
        direction = "Increase"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT5M"
      }
    }

    rule {
      metric_trigger {
        metric_name        = "CPU"
        metric_resource_id = azurerm_kusto_cluster.weather.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "LessThan"
        threshold          = 25
      }

      scale_action {
        direction = "Decrease"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT5M"
      }
    }
  }

  tags = azurerm_resource_group.main.tags
}