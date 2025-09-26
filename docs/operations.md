# Operations Guide

## Real-Time Weather Intelligence Platform

This guide covers day-to-day operations, monitoring, troubleshooting, and maintenance of the Weather Intelligence Platform.

## System Architecture Overview

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Weather APIs  │───▶│ Event Hubs   │───▶│ Kusto Cluster  │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │                      │
                              ▼                      ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   ML Pipeline   │◀───│ Databricks   │◀───│   Power BI      │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

## Daily Operations

### Morning Health Check (9:00 AM)

#### 1. System Status Dashboard
```bash
# Check overall platform health
python scripts/health_check.py --full-report

# Quick status check
curl -s http://your-health-endpoint/status | jq '.'
```

#### 2. Data Freshness Verification
```kql
// Run in Kusto Web Explorer
WeatherTelemetry
| summarize 
    LatestData = max(timestamp),
    FreshnessMinutes = datetime_diff('minute', now(), max(timestamp)),
    RecordCount = count()
| project LatestData, FreshnessMinutes, RecordCount, 
          Status = iff(FreshnessMinutes <= 2, "✅ HEALTHY", "⚠️ STALE")
```

#### 3. Performance Metrics Review
```kql
// Query performance over last 24 hours
.show queries
| where StartedOn > ago(1d)
| summarize 
    AvgDurationMs = avg(Duration / 1ms),
    P95DurationMs = percentile(Duration / 1ms, 95),
    QueryCount = count()
| project AvgDurationMs, P95DurationMs, QueryCount,
          P95Status = iff(P95DurationMs <= 700, "✅ GOOD", "⚠️ SLOW")
```

### Alert Response Procedures

#### High Severity Alerts

##### Data Pipeline Failure
```bash
# 1. Check Event Hub status
az eventhubs eventhub show \
  --resource-group rg-weather-intelligence-prod \
  --namespace-name eh-weather-ns \
  --name weather-telemetry

# 2. Restart data ingestion
kubectl restart deployment weather-data-ingestion

# 3. Check Kusto ingestion
.show ingestion failures
| where FailedOn > ago(1h)
```

##### Query Performance Degradation
```kql
// Identify slow queries
.show queries
| where StartedOn > ago(1h) and Duration > 5s
| project StartedOn, User, Duration, Text
| order by Duration desc

// Check cluster utilization
.show cluster extents
| summarize TotalSizeGB = sum(OriginalSize) / 1024 / 1024 / 1024
```

##### ML Model Accuracy Drop
```python
# Check model performance
from src.ml_models.model_monitor import ModelMonitor

monitor = ModelMonitor()
results = monitor.check_model_accuracy()

if results['accuracy_drop'] > 0.05:
    # Trigger model retraining
    monitor.trigger_retraining()
```

#### Medium Severity Alerts

##### Increased False Alarm Rate
```kql
// Analyze false alarm trends
WeatherAlerts
| where timestamp > ago(24h)
| summarize 
    TotalAlerts = count(),
    FalseAlerts = countif(is_false_alarm == true),
    FalseAlarmRate = todouble(countif(is_false_alarm == true)) / count()
| project TotalAlerts, FalseAlerts, FalseAlarmRate,
          Status = iff(FalseAlarmRate <= 0.3, "✅ GOOD", "⚠️ HIGH")
```

##### Power BI Dashboard Slow
```powershell
# Check DirectQuery performance
Get-PowerBIDataset -WorkspaceId "your-workspace-id" | 
  Where-Object {$_.Name -eq "Weather Intelligence"} |
  Get-PowerBIDatasetRefreshHistory
```

## Monitoring and Observability

### Key Metrics Dashboard

#### Platform Health Metrics
```yaml
data_freshness:
  target: "≤ 60 seconds"
  alert_threshold: "> 120 seconds"
  
query_performance:
  target: "P95 < 700ms"
  alert_threshold: "P95 > 1000ms"
  
ml_accuracy:
  target: "MAE reduction > 20%"
  alert_threshold: "MAE increase > 10%"
  
alert_timeliness:
  target: "18 minute lead time"
  alert_threshold: "< 15 minute lead time"
```

#### Business KPIs
```yaml
weather_prediction_accuracy:
  current: "87.5%"
  target: "> 85%"
  
false_alarm_reduction:
  current: "32% reduction"
  target: "> 30% reduction"
  
user_adoption:
  current: "68% increase"
  target: "> 60% increase"
```

### Custom Monitoring Queries

#### Real-time Data Quality
```kql
WeatherTelemetry
| where timestamp > ago(5m)
| extend QualityScore = case(
    temperature < -50 or temperature > 60, 0.1,  // Extreme temps
    humidity < 0 or humidity > 100, 0.2,         // Invalid humidity
    pressure < 900 or pressure > 1100, 0.3,     // Invalid pressure
    1.0                                          // Good quality
)
| summarize 
    AvgQuality = avg(QualityScore),
    BadQualityCount = countif(QualityScore < 0.8),
    TotalRecords = count()
| project AvgQuality, BadQualityCount, TotalRecords,
          DataQualityStatus = iff(AvgQuality >= 0.95, "✅ GOOD", "⚠️ POOR")
```

#### Event Processing Lag
```kql
WeatherTelemetry
| where timestamp > ago(10m)
| extend ProcessingLag = datetime_diff('second', ingestion_time(), timestamp)
| summarize 
    AvgLagSeconds = avg(ProcessingLag),
    MaxLagSeconds = max(ProcessingLag),
    P95LagSeconds = percentile(ProcessingLag, 95)
| project AvgLagSeconds, MaxLagSeconds, P95LagSeconds,
          LagStatus = iff(P95LagSeconds <= 60, "✅ GOOD", "⚠️ HIGH")
```

## Performance Tuning

### Kusto Query Optimization

#### Materialized View Management
```kql
// Create performance-optimized materialized view
.create materialized-view WeatherAggregated on table WeatherTelemetry
{
    WeatherTelemetry
    | summarize 
        avg_temperature = avg(temperature),
        max_wind_speed = max(wind_speed),
        alert_count = countif(alert_level != "normal")
      by region, bin(timestamp, 1m)
}
```

#### Index Optimization
```kql
// Monitor index usage
.show table WeatherTelemetry extents
| summarize TotalSize = sum(OriginalSize), ExtentCount = count() by MinCreatedOn
| order by MinCreatedOn desc

// Optimize for query patterns
.alter table WeatherTelemetry policy partitioning 
```json
{
  "PartitionKeys": [
    {
      "ColumnName": "timestamp",
      "Kind": "UniformRange",
      "Properties": {
        "Reference": "2024-01-01T00:00:00Z",
        "RangeSize": "1.00:00:00"
      }
    }
  ]
}
```

### Event Hub Scaling

#### Throughput Unit Monitoring
```bash
# Monitor Event Hub metrics
az monitor metrics list \
  --resource /subscriptions/{sub-id}/resourceGroups/rg-weather/providers/Microsoft.EventHub/namespaces/eh-weather \
  --metric IncomingMessages,OutgoingMessages \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z
```

#### Auto-scale Configuration
```json
{
  "sku": {
    "name": "Standard",
    "tier": "Standard"
  },
  "properties": {
    "isAutoInflateEnabled": true,
    "maximumThroughputUnits": 10,
    "kafkaEnabled": false
  }
}
```

## Data Management

### Data Retention Policies

#### Kusto Data Lifecycle
```kql
// Set retention policy for raw data
.alter table WeatherTelemetry policy retention softdelete = 90d

// Set caching policy for performance
.alter table WeatherTelemetry policy caching hot = 7d
```

#### Storage Optimization
```kql
// Monitor storage usage
.show database WeatherIntelligence extents
| summarize 
    TotalSizeGB = sum(OriginalSize) / 1024 / 1024 / 1024,
    CompressedSizeGB = sum(ExtentSize) / 1024 / 1024 / 1024,
    CompressionRatio = sum(OriginalSize) / sum(ExtentSize)
```

### Data Quality Monitoring

#### Anomaly Detection
```kql
WeatherTelemetry
| make-series Temperature = avg(temperature) default = 0 
  on timestamp step 1h by region
| extend anomalies = series_decompose_anomalies(Temperature, 1.5, 7, 'linefit')
| mv-expand Temperature to typeof(real), timestamp to typeof(datetime), 
           anomalies to typeof(double)
| where anomalies > 0
| project timestamp, region, Temperature, AnomalyScore = anomalies
```

#### Data Completeness Check
```kql
WeatherTelemetry
| where timestamp > ago(1d)
| summarize 
    ExpectedRecords = 24 * 60,  // Every minute for 24 hours
    ActualRecords = count(),
    CompletionRate = todouble(count()) / (24 * 60)
  by region
| where CompletionRate < 0.95
```

## Security Operations

### Access Management

#### Service Principal Rotation
```bash
# Create new service principal
az ad sp create-for-rbac --name "weather-intelligence-sp-new" \
  --role "Contributor" \
  --scopes /subscriptions/{subscription-id}/resourceGroups/rg-weather

# Update Key Vault secrets
az keyvault secret set --vault-name kv-weather-secrets \
  --name "service-principal-id" --value "{new-client-id}"
```

#### API Key Rotation
```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

# Rotate weather API key
credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://kv-weather-secrets.vault.azure.net/", 
                     credential=credential)

# Update secret
client.set_secret("weather-api-key", new_api_key)
```

### Audit and Compliance

#### Access Audit
```kql
// Review Kusto access patterns
.show principal access
| where PrincipalFQN contains "@" 
| summarize LastAccess = max(Timestamp) by PrincipalFQN
| where LastAccess < ago(30d)
```

#### Data Access Logging
```kql
// Monitor data access patterns
.show queries
| where StartedOn > ago(7d)
| summarize QueryCount = count(), DataAccessed = sum(ResourceUsage.TotalCpu) by User
| order by DataAccessed desc
```

## Incident Response

### Severity Classification

#### Severity 1 (Critical)
- Platform completely down
- Data loss detected
- Security breach
- **Response Time**: 15 minutes
- **Resolution Target**: 1 hour

#### Severity 2 (High)
- Performance degraded >50%
- ML model accuracy drop >20%
- False alarm rate >50%
- **Response Time**: 30 minutes
- **Resolution Target**: 4 hours

#### Severity 3 (Medium)
- Non-critical feature issues
- Performance degraded <50%
- Dashboard display issues
- **Response Time**: 2 hours
- **Resolution Target**: 24 hours

### Incident Response Playbook

#### 1. Initial Assessment
```bash
# Quick health check
./scripts/health_check.py --severity-1-check

# Check Azure service health
az rest --method get --url "https://management.azure.com/subscriptions/{sub}/providers/Microsoft.ResourceHealth/availabilityStatuses"
```

#### 2. Escalation Contacts
```yaml
primary_oncall: "weather-ops@company.com"
backup_oncall: "platform-ops@company.com"
manager: "weather-manager@company.com"
azure_support: "Case opened via Azure portal"
```

#### 3. Communication Template
```markdown
**INCIDENT ALERT**
- Severity: [1-3]
- Component: [Event Hub/Kusto/ML/Dashboard]
- Impact: [Description of user impact]
- Status: [Investigating/Mitigating/Resolved]
- ETA: [Estimated resolution time]
- Updates: [Next update in X minutes]
```

## Maintenance Windows

### Weekly Maintenance (Sundays 2-4 AM)

#### System Updates
```bash
# Update Kusto cluster (if needed)
az kusto cluster update --name weather-kusto --resource-group rg-weather

# Update Event Hub configuration
az eventhubs eventhub update --name weather-telemetry --namespace-name eh-weather

# ML model retraining
python scripts/retrain_models.py --production
```

#### Performance Optimization
```kql
// Compact Kusto extents
.merge WeatherTelemetry extents

// Update statistics
.execute database script <|
    .refresh materialized-view WeatherAggregated
```

### Monthly Maintenance (First Saturday)

#### Capacity Planning Review
```bash
# Generate capacity report
python scripts/capacity_report.py --month $(date +%Y-%m)

# Review and adjust auto-scaling policies
az monitor autoscale update --name kusto-autoscale --resource-group rg-weather
```

#### Security Updates
```bash
# Update secrets
python scripts/rotate_secrets.py --dry-run

# Update RBAC assignments
az role assignment list --scope /subscriptions/{sub}/resourceGroups/rg-weather
```

## Disaster Recovery

### Backup Verification
```bash
# Verify Kusto backup status
az kusto cluster show --name weather-kusto --resource-group rg-weather \
  --query "properties.provisioningState"

# Test backup restoration (to test environment)
python scripts/test_dr_restore.py --environment test
```

### Failover Procedures
```yaml
primary_region: "East US 2"
secondary_region: "West US 2"
rpo_target: "1 hour"
rto_target: "4 hours"

failover_triggers:
  - Regional Azure outage > 2 hours
  - Primary cluster unavailable > 1 hour
  - Data corruption detected
```

## Reporting and Analytics

### Weekly Reports
```python
# Generate weekly operations report
python scripts/weekly_report.py --output /reports/weather-ops-$(date +%Y%W).html

# Key metrics included:
# - System uptime and availability
# - Query performance trends  
# - Data quality metrics
# - ML model performance
# - User adoption metrics
```

### Monthly Business Reviews
```kql
// Business impact metrics for monthly review
WeatherAlerts
| where timestamp >= startofmonth(ago(30d))
| summarize 
    TotalAlerts = count(),
    AccurateAlerts = countif(accuracy_score >= 0.85),
    FalseAlarms = countif(is_false_alarm == true),
    AvgLeadTimeMinutes = avg(lead_time_minutes)
| extend 
    AccuracyRate = todouble(AccurateAlerts) / TotalAlerts,
    FalseAlarmRate = todouble(FalseAlarms) / TotalAlerts
```

For additional operational procedures, see [Troubleshooting Guide](troubleshooting.md) and [Performance Tuning Guide](performance.md).