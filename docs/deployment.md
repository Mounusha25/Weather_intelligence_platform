# Deployment Guide

## Real-Time Weather Intelligence Platform

This guide provides step-by-step instructions for deploying the Weather Intelligence Platform on Azure.

## Prerequisites

### Required Software
- **Azure CLI** (latest version)
- **Terraform** (>= 1.0)
- **Python 3.8+**
- **PowerShell Core** (for Power BI dashboard deployment)
- **Git**

### Azure Requirements
- **Azure Subscription** with appropriate permissions
- **Power BI Pro license** (for dashboard deployment)
- **Weather API key** (OpenWeatherMap or similar)

### Required Permissions
- Contributor access to Azure subscription
- Power BI workspace admin rights
- Service Principal creation permissions

## Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd Real_Time_weather_intelligence_platform

# Make deployment script executable (Linux/macOS)
chmod +x deploy.sh

# Login to Azure
az login
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.template .env

# Edit .env with your specific values
# Required: WEATHER_API_KEY, AZURE_SUBSCRIPTION_ID
```

### 3. Deploy Platform
```bash
# Deploy to development environment
./deploy.sh deploy

# Or deploy to production
ENVIRONMENT=prod ./deploy.sh deploy
```

### 4. Verify Deployment
```bash
# Test platform connectivity
./deploy.sh test

# Check Azure resources
az resource list --resource-group rg-weather-intelligence-dev
```

## Detailed Deployment Steps

### Phase 1: Infrastructure Deployment

The deployment script automatically creates:

#### Core Services
- **Resource Group**: `rg-weather-intelligence-{environment}`
- **Event Hub Namespace**: For real-time data streaming
- **Kusto Cluster**: For time-series analytics
- **Storage Account**: For ML model storage
- **Application Insights**: For monitoring and telemetry

#### Security Components
- **Key Vault**: For secrets management
- **Managed Identity**: For secure service authentication
- **Container Registry**: For custom Docker images

### Phase 2: Data Pipeline Setup

#### Event Hub Configuration
```bash
# Event Hub is configured with:
# - 4 partitions for parallel processing
# - 1-day message retention
# - Multiple consumer groups for different services
```

#### Kusto Database Schema
```kql
-- Weather telemetry table
WeatherTelemetry (
    timestamp: datetime,
    region: string,
    temperature: real,
    humidity: real,
    pressure: real,
    wind_speed: real,
    visibility: real,
    weather_condition: string,
    severity_score: real,
    alert_level: string
)

-- Aggregated data for dashboard performance
WeatherTelemetry_aggregated (
    timestamp: datetime,
    region: string,
    avg_temperature: real,
    max_wind_speed: real,
    alert_count: long
)
```

### Phase 3: ML Models Deployment

#### Model Training
```bash
# Activate Python environment
source .venv/bin/activate

# Train ARIMA models
python -m src.ml_models.arima_model

# Train XGBoost models
python -m src.ml_models.xgboost_model
```

#### Model Performance Targets
- **ARIMA MAE**: 22% reduction from baseline
- **XGBoost Accuracy**: >95% for severe weather classification
- **Prediction Latency**: <100ms
- **Model Refresh**: Every 24 hours

### Phase 4: Dashboard Deployment

#### Power BI Setup
```powershell
# Run PowerShell deployment script
pwsh dashboards/deploy_dashboard.ps1
```

#### Performance Targets
- **P95 Latency**: <700ms
- **Data Freshness**: ≤60 seconds
- **Concurrent Users**: 100+
- **Refresh Frequency**: 1 minute

## Configuration Reference

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `WEATHER_API_KEY` | OpenWeatherMap API key | - | Yes |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | - | Yes |
| `ENVIRONMENT` | Deployment environment | dev | No |
| `AZURE_REGION` | Azure region | eastus2 | No |

### Performance Configuration

#### Kusto Optimization
```json
{
  "query_caching": "5_minutes",
  "materialized_views": "enabled",
  "hot_cache_period": "7_days",
  "partition_strategy": "datetime"
}
```

#### Event Hub Settings
```json
{
  "partition_count": 4,
  "message_retention": "1_day",
  "throughput_units": 2,
  "auto_scale": "enabled"
}
```

## Monitoring and Alerting

### Health Checks
The platform includes automatic health monitoring:

- **Data Freshness**: Alerts if data is >60 seconds old
- **Query Performance**: Alerts if P95 >700ms
- **Event Processing**: Monitors throughput and errors
- **ML Model Performance**: Tracks prediction accuracy

### Alert Thresholds
```yaml
severe_weather:
  temperature: [-10°C, 40°C]
  wind_speed: >20 m/s
  visibility: <2 km

performance:
  query_latency_p95: 700ms
  data_freshness: 60s
  false_alarm_rate: <30%
```

### Monitoring Dashboards
- **Application Insights**: Performance metrics and logs
- **Power BI**: Business intelligence and KPIs
- **Kusto Dashboard**: Real-time data exploration
- **Azure Monitor**: Infrastructure health

## Security Configuration

### Authentication
- **Azure AD**: Service authentication using managed identity
- **API Keys**: Stored securely in Key Vault
- **Network**: Private endpoints for internal communication

### Data Protection
- **Encryption**: At rest and in transit
- **Access Control**: RBAC for all resources
- **Audit Logging**: All data access logged
- **Compliance**: GDPR and SOC2 ready

## Scaling Guidelines

### Development Environment
```yaml
kusto_sku: "Dev(No SLA)_Standard_D11_v2"
eventhub_capacity: 1
storage_tier: "Standard_LRS"
```

### Production Environment
```yaml
kusto_sku: "Standard_D13_v2"
eventhub_capacity: 4
storage_tier: "Standard_GRS"
auto_scaling: enabled
```

### Performance Scaling
- **Kusto**: Auto-scales from 1-10 nodes based on CPU
- **Event Hub**: Auto-inflate enabled for throughput
- **Storage**: Premium tier for high IOPS requirements

## Troubleshooting

### Common Issues

#### Deployment Failures
```bash
# Check Terraform state
cd infrastructure/terraform
terraform state list

# Validate configuration
terraform validate

# Check Azure CLI authentication
az account show
```

#### Data Pipeline Issues
```bash
# Check Event Hub connectivity
python -c "from src.data_ingestion.event_hub_producer import *"

# Verify Kusto connection
python -c "from src.kusto.kusto_client import *"
```

#### Performance Issues
```kql
// Check data freshness in Kusto
WeatherTelemetry
| summarize max_timestamp = max(timestamp), 
           freshness_minutes = datetime_diff('minute', now(), max(timestamp))

// Query performance analysis
.show queries
| where Text contains "WeatherTelemetry"
| project StartedOn, Duration, State, Text
```

### Log Locations
- **Application Logs**: `weather_intelligence.log`
- **Azure Logs**: Application Insights > Logs
- **Terraform Logs**: `terraform.log`
- **Deployment Logs**: `deploy.log`

## Cost Optimization

### Resource Sizing Recommendations

#### Development
- **Kusto**: Dev SKU (~$100/month)
- **Event Hub**: Standard tier (~$50/month)  
- **Storage**: Standard tier (~$20/month)
- **Total**: ~$200/month

#### Production
- **Kusto**: Standard D13v2 (~$500/month)
- **Event Hub**: Standard with auto-scale (~$200/month)
- **Storage**: Premium tier (~$100/month)
- **Total**: ~$1000/month

### Cost Optimization Tips
1. **Use reserved instances** for predictable workloads
2. **Enable auto-shutdown** for development environments
3. **Optimize Kusto queries** to reduce compute costs
4. **Use lifecycle policies** for data archival

## Support and Maintenance

### Regular Maintenance Tasks
- **Weekly**: Review performance metrics and alerts
- **Monthly**: Update ML models with new training data
- **Quarterly**: Review and optimize infrastructure costs
- **Annually**: Security audit and compliance review

### Backup and Recovery
- **Kusto**: 7-day automatic backup
- **Event Hub**: No backup needed (streaming data)
- **ML Models**: Stored in geo-redundant storage
- **Configuration**: Version controlled in Git

For additional support, refer to the [Operations Guide](operations.md) and [API Documentation](api.md).