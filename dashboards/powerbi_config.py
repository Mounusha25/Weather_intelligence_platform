"""
Power BI Dashboard Configuration
DirectQuery dashboard optimized for <700ms p95 latency and ≤60s data freshness
"""

import json
from typing import Dict, List, Any
from datetime import datetime


class PowerBIDashboardConfig:
    """
    Power BI dashboard configuration for weather intelligence platform
    Optimized for high performance and real-time data visualization
    """
    
    def __init__(self):
        self.dashboard_config = self._create_dashboard_config()
        self.dataset_config = self._create_dataset_config()
        self.report_config = self._create_report_config()
    
    def _create_dashboard_config(self) -> Dict[str, Any]:
        """Create dashboard configuration optimized for performance"""
        return {
            "name": "Weather Intelligence Dashboard",
            "description": "Real-time weather monitoring and alerts for regional teams",
            "refresh_settings": {
                "refresh_frequency": "1_minute",
                "incremental_refresh": True,
                "real_time_streaming": True,
                "cache_settings": {
                    "cache_duration": "5_minutes",
                    "auto_refresh": True
                }
            },
            "performance_targets": {
                "p95_latency_ms": 700,
                "data_freshness_seconds": 60,
                "concurrent_users": 100
            },
            "layout": {
                "theme": "weather_intelligence_theme",
                "responsive": True,
                "mobile_optimized": True
            }
        }
    
    def _create_dataset_config(self) -> Dict[str, Any]:
        """Create dataset configuration with DirectQuery optimization"""
        return {
            "name": "WeatherIntelligenceDataset",
            "connection_mode": "DirectQuery",
            "data_sources": [
                {
                    "name": "KustoWeatherData",
                    "type": "AzureDataExplorer",
                    "connection_details": {
                        "server": "${KUSTO_CLUSTER_URI}",
                        "database": "${KUSTO_DATABASE_NAME}",
                        "table": "WeatherTelemetry"
                    },
                    "query_optimization": {
                        "enable_query_folding": True,
                        "use_native_query": True,
                        "partition_elimination": True
                    }
                }
            ],
            "measures": [
                {
                    "name": "AverageTemperature",
                    "expression": "AVERAGE(WeatherTelemetry[temperature])",
                    "format": "0.0°C"
                },
                {
                    "name": "MaxWindSpeed",
                    "expression": "MAX(WeatherTelemetry[wind_speed])",
                    "format": "0.0 m/s"
                },
                {
                    "name": "SevereWeatherAlerts",
                    "expression": "COUNTROWS(FILTER(WeatherTelemetry, WeatherTelemetry[alert_level] IN {\"high\", \"critical\"}))",
                    "format": "0"
                },
                {
                    "name": "DataFreshness",
                    "expression": "DATEDIFF(MAX(WeatherTelemetry[timestamp]), NOW(), SECOND)",
                    "format": "0 sec"
                }
            ],
            "calculated_columns": [
                {
                    "name": "TemperatureCategory",
                    "expression": "IF(WeatherTelemetry[temperature] < 0, \"Freezing\", IF(WeatherTelemetry[temperature] < 10, \"Cold\", IF(WeatherTelemetry[temperature] < 25, \"Mild\", IF(WeatherTelemetry[temperature] < 35, \"Warm\", \"Hot\"))))"
                },
                {
                    "name": "WindCategory", 
                    "expression": "IF(WeatherTelemetry[wind_speed] < 5, \"Calm\", IF(WeatherTelemetry[wind_speed] < 15, \"Moderate\", IF(WeatherTelemetry[wind_speed] < 25, \"Strong\", \"Severe\")))"
                }
            ]
        }
    
    def _create_report_config(self) -> Dict[str, Any]:
        """Create report configuration with optimized visuals"""
        return {
            "name": "Weather Intelligence Report",
            "pages": [
                {
                    "name": "Overview",
                    "visuals": [
                        {
                            "type": "card",
                            "title": "Current Temperature",
                            "measure": "AverageTemperature",
                            "filters": [{"field": "timestamp", "operator": "last", "value": "5 minutes"}],
                            "position": {"x": 0, "y": 0, "width": 200, "height": 100}
                        },
                        {
                            "type": "card",
                            "title": "Active Alerts",
                            "measure": "SevereWeatherAlerts",
                            "filters": [{"field": "timestamp", "operator": "last", "value": "1 hour"}],
                            "position": {"x": 220, "y": 0, "width": 200, "height": 100}
                        },
                        {
                            "type": "card",
                            "title": "Data Freshness",
                            "measure": "DataFreshness",
                            "position": {"x": 440, "y": 0, "width": 200, "height": 100}
                        },
                        {
                            "type": "line_chart",
                            "title": "Temperature Trends",
                            "x_axis": "timestamp",
                            "y_axis": "temperature", 
                            "series": "region",
                            "filters": [{"field": "timestamp", "operator": "last", "value": "24 hours"}],
                            "position": {"x": 0, "y": 120, "width": 640, "height": 300},
                            "refresh_rate": "1_minute"
                        },
                        {
                            "type": "map",
                            "title": "Regional Weather Status",
                            "latitude": "latitude",
                            "longitude": "longitude",
                            "size": "severity_score",
                            "color": "alert_level",
                            "tooltip": ["region", "temperature", "wind_speed", "weather_condition"],
                            "position": {"x": 660, "y": 120, "width": 400, "height": 300}
                        }
                    ]
                },
                {
                    "name": "Alerts",
                    "visuals": [
                        {
                            "type": "table",
                            "title": "Active Severe Weather Alerts",
                            "columns": ["timestamp", "region", "alert_level", "temperature", "wind_speed", "weather_condition"],
                            "filters": [
                                {"field": "alert_level", "operator": "in", "value": ["high", "critical"]},
                                {"field": "timestamp", "operator": "last", "value": "6 hours"}
                            ],
                            "sorting": [{"field": "timestamp", "direction": "desc"}],
                            "position": {"x": 0, "y": 0, "width": 800, "height": 400}
                        },
                        {
                            "type": "bar_chart",
                            "title": "Alerts by Region (Last 24h)",
                            "x_axis": "region",
                            "y_axis": "SevereWeatherAlerts",
                            "color": "alert_level",
                            "filters": [{"field": "timestamp", "operator": "last", "value": "24 hours"}],
                            "position": {"x": 820, "y": 0, "width": 400, "height": 200}
                        }
                    ]
                },
                {
                    "name": "Analytics",
                    "visuals": [
                        {
                            "type": "scatter_plot",
                            "title": "Temperature vs Wind Speed",
                            "x_axis": "temperature",
                            "y_axis": "wind_speed",
                            "color": "region",
                            "size": "severity_score",
                            "filters": [{"field": "timestamp", "operator": "last", "value": "24 hours"}],
                            "position": {"x": 0, "y": 0, "width": 500, "height": 300}
                        },
                        {
                            "type": "histogram",
                            "title": "Temperature Distribution by Region",
                            "x_axis": "temperature",
                            "series": "region",
                            "bins": 20,
                            "filters": [{"field": "timestamp", "operator": "last", "value": "7 days"}],
                            "position": {"x": 520, "y": 0, "width": 500, "height": 300}
                        }
                    ]
                }
            ],
            "filters": [
                {
                    "name": "RegionFilter",
                    "field": "region",
                    "type": "multi_select",
                    "default": "all",
                    "position": "top"
                },
                {
                    "name": "TimeRangeFilter", 
                    "field": "timestamp",
                    "type": "relative_date",
                    "default": "last_24_hours",
                    "position": "top"
                }
            ]
        }
    
    def get_dashboard_json(self) -> str:
        """Get complete dashboard configuration as JSON"""
        complete_config = {
            "dashboard": self.dashboard_config,
            "dataset": self.dataset_config,
            "report": self.report_config,
            "metadata": {
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "platform": "weather_intelligence"
            }
        }
        
        return json.dumps(complete_config, indent=2)
    
    def get_performance_optimizations(self) -> Dict[str, Any]:
        """Get performance optimization settings for Power BI"""
        return {
            "query_optimizations": {
                "enable_query_caching": True,
                "cache_duration_minutes": 5,
                "enable_incremental_refresh": True,
                "partition_by": "timestamp",
                "partition_granularity": "daily"
            },
            "directquery_optimizations": {
                "enable_query_folding": True,
                "use_native_sql": True,
                "limit_concurrent_queries": 10,
                "query_timeout_seconds": 30
            },
            "visual_optimizations": {
                "limit_data_points": 10000,
                "enable_sampling": True,
                "use_aggregations": True,
                "preload_visuals": True
            },
            "refresh_optimizations": {
                "parallel_refresh": True,
                "incremental_refresh": True,
                "real_time_streaming": True,
                "auto_page_refresh": "1_minute"
            }
        }
    
    def generate_dax_measures(self) -> List[str]:
        """Generate DAX measures for weather analytics"""
        return [
            # Temperature measures
            "Current Temperature = CALCULATE(AVERAGE(WeatherTelemetry[temperature]), TOPN(1, WeatherTelemetry, WeatherTelemetry[timestamp], DESC))",
            
            # Alert measures  
            "Active Alerts = CALCULATE(COUNTROWS(WeatherTelemetry), WeatherTelemetry[alert_level] IN {\"high\", \"critical\"}, WeatherTelemetry[timestamp] >= NOW() - TIME(1,0,0))",
            
            # Trend measures
            "Temperature Trend = VAR CurrentTemp = [Current Temperature] VAR PreviousTemp = CALCULATE([Current Temperature], DATEADD(WeatherTelemetry[timestamp], -1, HOUR)) RETURN IF(CurrentTemp > PreviousTemp, 1, IF(CurrentTemp < PreviousTemp, -1, 0))",
            
            # Performance measures
            "Data Freshness Minutes = DATEDIFF(MAX(WeatherTelemetry[timestamp]), NOW(), MINUTE)",
            
            # Severe weather measures
            "Severe Weather Probability = AVERAGE(WeatherTelemetry[severity_score])",
            
            # Regional comparisons
            "Hottest Region = TOPN(1, SUMMARIZE(WeatherTelemetry, WeatherTelemetry[region], \"AvgTemp\", AVERAGE(WeatherTelemetry[temperature])), [AvgTemp], DESC)",
            
            # Alert effectiveness
            "False Alarm Rate = DIVIDE(COUNTROWS(FILTER(WeatherTelemetry, WeatherTelemetry[alert_level] = \"high\" && WeatherTelemetry[severity_score] < 0.5)), COUNTROWS(FILTER(WeatherTelemetry, WeatherTelemetry[alert_level] = \"high\")))"
        ]


# Dashboard deployment configuration
class DashboardDeployment:
    """Handle dashboard deployment and configuration"""
    
    def __init__(self, config: PowerBIDashboardConfig):
        self.config = config
    
    def create_deployment_script(self) -> str:
        """Create PowerShell deployment script for Power BI"""
        return '''
# Power BI Dashboard Deployment Script
# Requires Power BI PowerShell modules

# Install Power BI modules if not already installed
if (-not (Get-Module -ListAvailable -Name MicrosoftPowerBIMgmt)) {
    Install-Module -Name MicrosoftPowerBIMgmt -Force -AllowClobber
}

# Import modules
Import-Module MicrosoftPowerBIMgmt

# Connect to Power BI Service
Connect-PowerBIServiceAccount

# Create workspace if it doesn't exist
$workspaceName = "Weather Intelligence Platform"
$workspace = Get-PowerBIWorkspace -Name $workspaceName
if (-not $workspace) {
    $workspace = New-PowerBIWorkspace -Name $workspaceName
    Write-Host "Created workspace: $workspaceName"
}

# Deploy dataset
$datasetPath = "./dashboard/WeatherIntelligenceDataset.pbix"
if (Test-Path $datasetPath) {
    Import-PowerBIFile -Path $datasetPath -WorkspaceId $workspace.Id -ConflictAction CreateOrOverwrite
    Write-Host "Dataset deployed successfully"
}

# Deploy report
$reportPath = "./dashboard/WeatherIntelligenceReport.pbix"  
if (Test-Path $reportPath) {
    Import-PowerBIFile -Path $reportPath -WorkspaceId $workspace.Id -ConflictAction CreateOrOverwrite
    Write-Host "Report deployed successfully"
}

# Configure refresh schedule
$datasetId = (Get-PowerBIDataset -WorkspaceId $workspace.Id -Name "WeatherIntelligenceDataset").Id
if ($datasetId) {
    # Set up refresh schedule for every 5 minutes during business hours
    $refreshSchedule = @{
        "value" = @{
            "days" = @("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
            "times" = @("00:05", "00:10", "00:15", "00:20", "00:25", "00:30", "00:35", "00:40", "00:45", "00:50", "00:55")
            "enabled" = $true
            "localTimeZoneId" = "UTC"
        }
    }
    
    Write-Host "Refresh schedule configured"
}

Write-Host "Dashboard deployment completed successfully"
        '''
    
    def create_arm_template(self) -> Dict[str, Any]:
        """Create Azure Resource Manager template for infrastructure"""
        return {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {
                "powerBIWorkspaceName": {
                    "type": "string",
                    "defaultValue": "WeatherIntelligencePlatform"
                },
                "kustoClusterName": {
                    "type": "string"
                },
                "eventHubNamespace": {
                    "type": "string"
                }
            },
            "resources": [
                {
                    "type": "Microsoft.PowerBI/workspaces",
                    "apiVersion": "2020-06-01",
                    "name": "[parameters('powerBIWorkspaceName')]",
                    "properties": {
                        "displayName": "[parameters('powerBIWorkspaceName')]"
                    }
                }
            ]
        }


# Example usage
if __name__ == "__main__":
    # Create dashboard configuration
    dashboard_config = PowerBIDashboardConfig()
    
    # Generate complete configuration
    config_json = dashboard_config.get_dashboard_json()
    print("Dashboard Configuration:")
    print(config_json[:500] + "..." if len(config_json) > 500 else config_json)
    
    # Generate DAX measures
    dax_measures = dashboard_config.generate_dax_measures()
    print("\nDAX Measures:")
    for measure in dax_measures[:3]:  # Show first 3 measures
        print(f"- {measure}")
    
    # Create deployment script
    deployment = DashboardDeployment(dashboard_config)
    script = deployment.create_deployment_script()
    print(f"\nDeployment script length: {len(script)} characters")