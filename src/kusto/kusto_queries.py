"""
Kusto Query Templates for Weather Intelligence Platform
Pre-defined KQL queries optimized for weather analytics
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta


class WeatherQueries:
    """
    Collection of optimized KQL queries for weather intelligence platform
    Designed for high performance with <700ms p95 latency
    """
    
    def __init__(self, table_name: str = "WeatherTelemetry"):
        self.table_name = table_name
        self.aggregated_table = f"{table_name}_aggregated"
    
    def latest_weather_by_region(self, region: str = None, hours: int = 1) -> str:
        """Get latest weather data by region"""
        region_filter = f"| where region == '{region}'" if region else ""
        
        return f"""
{self.table_name}
| where timestamp >= ago({hours}h)
{region_filter}
| order by timestamp desc
| take 1000
        """
    
    def weather_aggregates_by_time(self, 
                                  start_time: datetime, 
                                  end_time: datetime, 
                                  bin_size: str = "5m") -> str:
        """Get aggregated weather data for time range"""
        return f"""
{self.table_name}
| where timestamp between (datetime('{start_time.isoformat()}') .. datetime('{end_time.isoformat()}'))
| summarize 
    avg_temperature = avg(temperature),
    avg_humidity = avg(humidity), 
    avg_pressure = avg(pressure),
    max_wind_speed = max(wind_speed),
    min_visibility = min(visibility),
    alert_count = countif(alert_level in ('high', 'critical')),
    severe_weather_probability = avg(severity_score)
    by bin(timestamp, {bin_size}), region
| order by timestamp desc
        """
    
    def severe_weather_alerts(self, hours: int = 24) -> str:
        """Get severe weather alerts"""
        return f"""
{self.table_name}
| where timestamp >= ago({hours}h)
| where alert_level in ('high', 'critical')
| project timestamp, region, temperature, wind_speed, visibility, 
          weather_condition, severity_score, alert_level
| order by timestamp desc
        """
    
    def temperature_trends(self, region: str, days: int = 7) -> str:
        """Get temperature trends for region"""
        return f"""
{self.table_name}
| where timestamp >= ago({days}d)
| where region == '{region}'
| summarize avg_temp = avg(temperature), 
           min_temp = min(temperature), 
           max_temp = max(temperature)
           by bin(timestamp, 1h)
| order by timestamp asc
        """
    
    def wind_speed_analysis(self, threshold: float = 15.0) -> str:
        """Analyze high wind events across regions"""
        return f"""
{self.table_name}
| where wind_speed > {threshold}
| summarize 
    high_wind_count = count(),
    avg_wind_speed = avg(wind_speed),
    max_wind_speed = max(wind_speed)
    by region, bin(timestamp, 1h)
| order by timestamp desc
        """
    
    def dashboard_realtime_summary(self) -> str:
        """Optimized query for real-time dashboard"""
        return f"""
{self.table_name}
| where timestamp >= ago(5m)
| summarize 
    current_temp = avg(temperature),
    current_humidity = avg(humidity),
    current_pressure = avg(pressure),
    current_wind = max(wind_speed),
    alert_status = max(case(alert_level == 'critical', 4, 
                           alert_level == 'high', 3,
                           alert_level == 'medium', 2, 1)),
    latest_update = max(timestamp)
    by region
        """
    
    def performance_monitoring_query(self) -> str:
        """Monitor data ingestion performance"""
        return f"""
{self.table_name}
| where timestamp >= ago(1h)
| summarize 
    record_count = count(),
    data_freshness_seconds = datetime_diff('second', now(), max(timestamp)),
    regions_reporting = dcount(region),
    avg_severity = avg(severity_score)
    by bin(timestamp, 5m)
| order by timestamp desc
        """
    
    def create_table_schema(self, table_name: str) -> str:
        """Generate table creation command"""
        return f"""
.create table {table_name} (
    timestamp: datetime,
    region: string,
    latitude: real,
    longitude: real,
    temperature: real,
    humidity: real,
    pressure: real,
    wind_speed: real,
    wind_direction: real,
    visibility: real,
    weather_condition: string,
    cloud_coverage: real,
    precipitation: real,
    uv_index: real,
    air_quality_index: int,
    severity_score: real,
    alert_level: string,
    ingestion_time: datetime
)
        """
    
    def create_ingestion_mapping(self, table_name: str, mapping_name: str) -> str:
        """Generate ingestion mapping command"""
        return f"""
.create table {table_name} ingestion json mapping '{mapping_name}'
'[
    {{"column":"timestamp", "path":"$.timestamp", "datatype":"datetime"}},
    {{"column":"region", "path":"$.region", "datatype":"string"}},
    {{"column":"latitude", "path":"$.latitude", "datatype":"real"}},
    {{"column":"longitude", "path":"$.longitude", "datatype":"real"}},
    {{"column":"temperature", "path":"$.temperature", "datatype":"real"}},
    {{"column":"humidity", "path":"$.humidity", "datatype":"real"}},
    {{"column":"pressure", "path":"$.pressure", "datatype":"real"}},
    {{"column":"wind_speed", "path":"$.wind_speed", "datatype":"real"}},
    {{"column":"wind_direction", "path":"$.wind_direction", "datatype":"real"}},
    {{"column":"visibility", "path":"$.visibility", "datatype":"real"}},
    {{"column":"weather_condition", "path":"$.weather_condition", "datatype":"string"}},
    {{"column":"cloud_coverage", "path":"$.cloud_coverage", "datatype":"real"}},
    {{"column":"precipitation", "path":"$.precipitation", "datatype":"real"}},
    {{"column":"uv_index", "path":"$.uv_index", "datatype":"real"}},
    {{"column":"air_quality_index", "path":"$.air_quality_index", "datatype":"int"}},
    {{"column":"severity_score", "path":"$.severity_score", "datatype":"real"}},
    {{"column":"alert_level", "path":"$.alert_level", "datatype":"string"}},
    {{"column":"ingestion_time", "path":"$.ingestion_time", "datatype":"datetime"}}
]'
        """
    
    def create_materialized_view(self, table_name: str) -> str:
        """Create materialized view for dashboard optimization"""
        return f"""
.create materialized-view DashboardView on table {table_name}
{{
    {table_name}
    | summarize 
        avg_temperature = avg(temperature),
        avg_humidity = avg(humidity),
        max_wind_speed = max(wind_speed),
        alert_count = countif(alert_level != 'low'),
        latest_timestamp = max(timestamp)
        by bin(timestamp, 1m), region
}}
        """
    
    def weather_prediction_features(self, region: str, hours: int = 24) -> str:
        """Extract features for ML model predictions"""
        return f"""
{self.table_name}
| where timestamp >= ago({hours}h)
| where region == '{region}'
| sort by timestamp asc
| extend 
    temp_lag_1h = prev(temperature, 12),  // 12 * 5min = 1h
    temp_lag_3h = prev(temperature, 36),  // 36 * 5min = 3h
    pressure_change = temperature - prev(pressure, 1),
    wind_trend = case(wind_speed > prev(wind_speed, 1), "increasing", 
                     wind_speed < prev(wind_speed, 1), "decreasing", "stable")
| project timestamp, temperature, humidity, pressure, wind_speed, 
          temp_lag_1h, temp_lag_3h, pressure_change, wind_trend
        """
    
    def alert_effectiveness_analysis(self, days: int = 30) -> str:
        """Analyze alert effectiveness and false alarm rates"""
        return f"""
let alerts = {self.table_name}
    | where timestamp >= ago({days}d)
    | where alert_level in ('high', 'critical')
    | project timestamp, region, predicted_severity = severity_score;
let actual_severe = {self.table_name}
    | where timestamp >= ago({days}d)
    | where temperature < 0 or temperature > 35 or wind_speed > 20 or visibility < 2
    | project timestamp, region, actual_severity = 1.0;
alerts
| join kind=leftouter (actual_severe) on region
| extend 
    time_diff = abs(datetime_diff('minute', timestamp, timestamp1)),
    true_positive = case(time_diff <= 30, 1, 0),  // Alert within 30 min of actual event
    false_positive = case(time_diff > 30 or isnull(timestamp1), 1, 0)
| summarize 
    total_alerts = count(),
    true_positives = sum(true_positive),
    false_positives = sum(false_positive),
    precision = todouble(sum(true_positive)) / count(),
    false_alarm_rate = todouble(sum(false_positive)) / count()
    by region
        """


# Example usage
if __name__ == "__main__":
    queries = WeatherQueries()
    
    # Example: Get latest weather for north region
    latest_query = queries.latest_weather_by_region("north", 2)
    print("Latest weather query:")
    print(latest_query)
    
    # Example: Get severe weather alerts
    alerts_query = queries.severe_weather_alerts(12)
    print("\nSevere weather alerts query:")
    print(alerts_query)
    
    # Example: Dashboard summary
    dashboard_query = queries.dashboard_realtime_summary()
    print("\nDashboard summary query:")
    print(dashboard_query)