"""
Azure Data Explorer (Kusto) Client
High-performance time-series analytics and fast querying for weather data
Optimized for <700ms p95 latency and ≤60s data freshness
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
import json

try:
    from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
    from azure.kusto.data.exceptions import KustoServiceError
    from azure.kusto.ingest import QueuedIngestClient, IngestionProperties, DataFormat
    from azure.identity import DefaultAzureCredential
except ImportError:
    # Fallback for when Azure Kusto SDK is not installed
    KustoClient = None
    QueuedIngestClient = None

from config.config import Config

logger = logging.getLogger(__name__)


class WeatherKustoClient:
    """
    Azure Data Explorer (Kusto) client for weather intelligence platform
    Provides high-performance analytics and real-time querying capabilities
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.cluster_uri = config.kusto.cluster_uri
        self.database_name = config.kusto.database_name
        self.table_name = config.kusto.table_name
        self.ingestion_mapping = config.kusto.ingestion_mapping
        
        self.query_client: Optional[KustoClient] = None
        self.ingest_client: Optional[QueuedIngestClient] = None
        
        # Performance monitoring
        self.query_count = 0
        self.total_query_time = 0.0
        
    def initialize_clients(self) -> bool:
        """
        Initialize Kusto query and ingestion clients
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if KustoClient is None:
                logger.error("Azure Kusto SDK not available")
                return False
            
            # Build connection string with Azure AD authentication
            kcsb = KustoConnectionStringBuilder.with_aad_managed_service_identity_authentication(
                self.cluster_uri
            )
            
            # Initialize query client
            self.query_client = KustoClient(kcsb)
            
            # Initialize ingestion client
            kcsb_ingest = KustoConnectionStringBuilder.with_aad_managed_service_identity_authentication(
                self.cluster_uri.replace('.kusto.', '.ingest-')
            )
            self.ingest_client = QueuedIngestClient(kcsb_ingest)
            
            logger.info(f"Kusto clients initialized for cluster: {self.cluster_uri}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Kusto clients: {e}")
            return False
    
    def create_database_schema(self) -> bool:
        """
        Create database schema for weather intelligence platform
        
        Returns:
            True if schema creation successful, False otherwise
        """
        try:
            if not self.query_client:
                logger.error("Kusto query client not initialized")
                return False
            
            # Create table schema
            create_table_command = f"""
.create table {self.table_name} (
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
)"""\n            \n            self.query_client.execute_mgmt(self.database_name, create_table_command)\n            \n            # Create ingestion mapping\n            mapping_command = f\"\"\"\n.create table {self.table_name} ingestion json mapping '{self.ingestion_mapping}'\n'[\n    {{\"column\":\"timestamp\", \"path\":\"$.timestamp\", \"datatype\":\"datetime\"}},\n    {{\"column\":\"region\", \"path\":\"$.region\", \"datatype\":\"string\"}},\n    {{\"column\":\"latitude\", \"path\":\"$.latitude\", \"datatype\":\"real\"}},\n    {{\"column\":\"longitude\", \"path\":\"$.longitude\", \"datatype\":\"real\"}},\n    {{\"column\":\"temperature\", \"path\":\"$.temperature\", \"datatype\":\"real\"}},\n    {{\"column\":\"humidity\", \"path\":\"$.humidity\", \"datatype\":\"real\"}},\n    {{\"column\":\"pressure\", \"path\":\"$.pressure\", \"datatype\":\"real\"}},\n    {{\"column\":\"wind_speed\", \"path\":\"$.wind_speed\", \"datatype\":\"real\"}},\n    {{\"column\":\"wind_direction\", \"path\":\"$.wind_direction\", \"datatype\":\"real\"}},\n    {{\"column\":\"visibility\", \"path\":\"$.visibility\", \"datatype\":\"real\"}},\n    {{\"column\":\"weather_condition\", \"path\":\"$.weather_condition\", \"datatype\":\"string\"}},\n    {{\"column\":\"cloud_coverage\", \"path\":\"$.cloud_coverage\", \"datatype\":\"real\"}},\n    {{\"column\":\"precipitation\", \"path\":\"$.precipitation\", \"datatype\":\"real\"}},\n    {{\"column\":\"uv_index\", \"path\":\"$.uv_index\", \"datatype\":\"real\"}},\n    {{\"column\":\"air_quality_index\", \"path\":\"$.air_quality_index\", \"datatype\":\"int\"}},\n    {{\"column\":\"severity_score\", \"path\":\"$.severity_score\", \"datatype\":\"real\"}},\n    {{\"column\":\"alert_level\", \"path\":\"$.alert_level\", \"datatype\":\"string\"}},\n    {{\"column\":\"ingestion_time\", \"path\":\"$.ingestion_time\", \"datatype\":\"datetime\"}}\n]'\n\"\"\"\n            \n            self.query_client.execute_mgmt(self.database_name, mapping_command)\n            \n            # Create update policy for real-time aggregations\n            update_policy_command = f\"\"\"\n.create table {self.table_name}_aggregated (\n    timestamp: datetime,\n    region: string,\n    avg_temperature: real,\n    avg_humidity: real,\n    avg_pressure: real,\n    max_wind_speed: real,\n    min_visibility: real,\n    alert_count: long,\n    severe_weather_probability: real\n)\n\n.alter table {self.table_name}_aggregated policy update\n@'[{{\n    \"IsEnabled\": true,\n    \"Source\": \"{self.table_name}\",\n    \"Query\": \"{self.table_name} | summarize avg_temperature=avg(temperature), avg_humidity=avg(humidity), avg_pressure=avg(pressure), max_wind_speed=max(wind_speed), min_visibility=min(visibility), alert_count=countif(alert_level != 'low'), severe_weather_probability=avg(severity_score) by bin(timestamp, 5m), region\",\n    \"IsTransactional\": true,\n    \"PropagateIngestionProperties\": false\n}}]'\n\"\"\"\n            \n            self.query_client.execute_mgmt(self.database_name, update_policy_command)\n            \n            logger.info(\"Kusto database schema created successfully\")\n            return True\n            \n        except Exception as e:\n            logger.error(f\"Error creating Kusto schema: {e}\")\n            return False\n    \n    def ingest_weather_data(self, weather_data: List[Dict[str, Any]]) -> bool:\n        \"\"\"\n        Ingest weather data into Kusto table\n        \n        Args:\n            weather_data: List of weather data dictionaries\n            \n        Returns:\n            True if ingestion successful, False otherwise\n        \"\"\"\n        try:\n            if not self.ingest_client:\n                logger.error(\"Kusto ingest client not initialized\")\n                return False\n            \n            # Add ingestion timestamp\n            current_time = datetime.utcnow().isoformat()\n            for record in weather_data:\n                record['ingestion_time'] = current_time\n                # Calculate severity score if not present\n                if 'severity_score' not in record:\n                    record['severity_score'] = self._calculate_severity_score(record)\n                # Determine alert level\n                if 'alert_level' not in record:\n                    record['alert_level'] = self._determine_alert_level(record['severity_score'])\n            \n            # Convert to JSON string\n            json_data = '\\n'.join([json.dumps(record) for record in weather_data])\n            \n            # Configure ingestion properties\n            ingestion_props = IngestionProperties(\n                database=self.database_name,\n                table=self.table_name,\n                data_format=DataFormat.JSON,\n                mapping_reference=self.ingestion_mapping\n            )\n            \n            # Ingest data\n            self.ingest_client.ingest_from_stream(\n                json_data, \n                ingestion_properties=ingestion_props\n            )\n            \n            logger.info(f\"Successfully ingested {len(weather_data)} weather records\")\n            return True\n            \n        except Exception as e:\n            logger.error(f\"Error ingesting weather data: {e}\")\n            return False\n    \n    def _calculate_severity_score(self, weather_record: Dict[str, Any]) -> float:\n        \"\"\"Calculate severity score for weather record\"\"\"\n        score = 0.0\n        \n        # Temperature extremes\n        temp = weather_record.get('temperature', 20)\n        if temp < 0 or temp > 35:\n            score += 0.3\n        \n        # High wind speeds  \n        wind = weather_record.get('wind_speed', 0)\n        if wind > 20:\n            score += 0.4\n        elif wind > 15:\n            score += 0.2\n        \n        # Poor visibility\n        visibility = weather_record.get('visibility', 10)\n        if visibility < 2:\n            score += 0.3\n        elif visibility < 5:\n            score += 0.1\n        \n        return min(score, 1.0)\n    \n    def _determine_alert_level(self, severity_score: float) -> str:\n        \"\"\"Determine alert level based on severity score\"\"\"\n        if severity_score >= 0.8:\n            return 'critical'\n        elif severity_score >= 0.6:\n            return 'high'\n        elif severity_score >= 0.3:\n            return 'medium'\n        else:\n            return 'low'\n    \n    def execute_query(self, kql_query: str, timeout_seconds: int = 30) -> pd.DataFrame:\n        \"\"\"\n        Execute KQL query and return results as DataFrame\n        \n        Args:\n            kql_query: Kusto Query Language query\n            timeout_seconds: Query timeout in seconds\n            \n        Returns:\n            pandas DataFrame with query results\n        \"\"\"\n        start_time = datetime.now()\n        \n        try:\n            if not self.query_client:\n                logger.error(\"Kusto query client not initialized\")\n                return pd.DataFrame()\n            \n            # Execute query with timeout\n            response = self.query_client.execute_query(\n                self.database_name, \n                kql_query,\n                timeout=timedelta(seconds=timeout_seconds)\n            )\n            \n            # Convert to DataFrame\n            df = pd.DataFrame(response.primary_results[0])\n            \n            # Update performance metrics\n            query_time = (datetime.now() - start_time).total_seconds()\n            self.query_count += 1\n            self.total_query_time += query_time\n            \n            logger.debug(f\"Query executed in {query_time:.3f}s, returned {len(df)} rows\")\n            \n            return df\n            \n        except KustoServiceError as e:\n            logger.error(f\"Kusto service error: {e}\")\n            return pd.DataFrame()\n        except Exception as e:\n            logger.error(f\"Error executing Kusto query: {e}\")\n            return pd.DataFrame()\n    \n    def get_latest_weather_data(self, region: str = None, hours: int = 1) -> pd.DataFrame:\n        \"\"\"\n        Get latest weather data for analysis\n        \n        Args:\n            region: Specific region filter (optional)\n            hours: Number of hours to look back\n            \n        Returns:\n            DataFrame with latest weather data\n        \"\"\"\n        region_filter = f\"| where region == '{region}'\" if region else \"\"\n        \n        query = f\"\"\"\n{self.table_name}\n| where timestamp >= ago({hours}h)\n{region_filter}\n| order by timestamp desc\n| take 1000\n        \"\"\"\n        \n        return self.execute_query(query)\n    \n    def get_weather_aggregates(self, \n                              start_time: datetime, \n                              end_time: datetime, \n                              bin_size: str = \"5m\") -> pd.DataFrame:\n        \"\"\"\n        Get aggregated weather data for specified time range\n        \n        Args:\n            start_time: Start datetime\n            end_time: End datetime\n            bin_size: Aggregation bin size (e.g., '5m', '1h', '1d')\n            \n        Returns:\n            DataFrame with aggregated weather data\n        \"\"\"\n        query = f\"\"\"\n{self.table_name}\n| where timestamp between (datetime('{start_time.isoformat()}') .. datetime('{end_time.isoformat()}'))\n| summarize \n    avg_temperature = avg(temperature),\n    avg_humidity = avg(humidity), \n    avg_pressure = avg(pressure),\n    max_wind_speed = max(wind_speed),\n    min_visibility = min(visibility),\n    alert_count = countif(alert_level in ('high', 'critical')),\n    severe_weather_probability = avg(severity_score)\n    by bin(timestamp, {bin_size}), region\n| order by timestamp desc\n        \"\"\"\n        \n        return self.execute_query(query)\n    \n    def get_severe_weather_alerts(self, hours: int = 24) -> pd.DataFrame:\n        \"\"\"\n        Get severe weather alerts from the last N hours\n        \n        Args:\n            hours: Number of hours to look back\n            \n        Returns:\n            DataFrame with severe weather alerts\n        \"\"\"\n        query = f\"\"\"\n{self.table_name}\n| where timestamp >= ago({hours}h)\n| where alert_level in ('high', 'critical')\n| project timestamp, region, temperature, wind_speed, visibility, \n          weather_condition, severity_score, alert_level\n| order by timestamp desc\n        \"\"\"\n        \n        return self.execute_query(query)\n    \n    def get_performance_metrics(self) -> Dict[str, float]:\n        \"\"\"\n        Get query performance metrics\n        \n        Returns:\n            Dictionary with performance metrics\n        \"\"\"\n        avg_query_time = (self.total_query_time / self.query_count) if self.query_count > 0 else 0\n        \n        return {\n            \"total_queries\": self.query_count,\n            \"total_query_time_seconds\": self.total_query_time,\n            \"average_query_time_seconds\": avg_query_time,\n            \"average_query_time_ms\": avg_query_time * 1000\n        }\n    \n    def optimize_for_dashboards(self) -> bool:\n        \"\"\"\n        Create materialized views and policies for dashboard optimization\n        \n        Returns:\n            True if optimization successful, False otherwise\n        \"\"\"\n        try:\n            if not self.query_client:\n                logger.error(\"Kusto query client not initialized\")\n                return False\n            \n            # Create materialized view for dashboard queries\n            materialized_view_command = f\"\"\"\n.create materialized-view DashboardView on table {self.table_name}\n{{\n    {self.table_name}\n    | summarize \n        avg_temperature = avg(temperature),\n        avg_humidity = avg(humidity),\n        max_wind_speed = max(wind_speed),\n        alert_count = countif(alert_level != 'low'),\n        latest_timestamp = max(timestamp)\n        by bin(timestamp, 1m), region\n}}\n            \"\"\"\n            \n            self.query_client.execute_mgmt(self.database_name, materialized_view_command)\n            \n            # Create caching policy for fast dashboard queries\n            caching_policy_command = f\"\"\"\n.alter table {self.table_name} policy caching hot = 7d\n.alter materialized-view DashboardView policy caching hot = 1d\n            \"\"\"\n            \n            self.query_client.execute_mgmt(self.database_name, caching_policy_command)\n            \n            logger.info(\"Dashboard optimizations applied successfully\")\n            return True\n            \n        except Exception as e:\n            logger.error(f\"Error applying dashboard optimizations: {e}\")\n            return False\n    \n    def close_connections(self) -> None:\n        \"\"\"Close Kusto client connections\"\"\"\n        try:\n            if self.query_client:\n                self.query_client.close()\n            if self.ingest_client:\n                self.ingest_client.close()\n            logger.info(\"Kusto connections closed\")\n        except Exception as e:\n            logger.error(f\"Error closing Kusto connections: {e}\")\n\n\n# Example usage\nif __name__ == \"__main__\":\n    # Example usage of WeatherKustoClient\n    config = Config()\n    kusto_client = WeatherKustoClient(config)\n    \n    # Initialize clients\n    if kusto_client.initialize_clients():\n        # Create schema\n        kusto_client.create_database_schema()\n        \n        # Sample weather data\n        sample_data = [\n            {\n                \"timestamp\": datetime.utcnow().isoformat(),\n                \"region\": \"north\",\n                \"latitude\": 40.7128,\n                \"longitude\": -74.0060,\n                \"temperature\": 22.5,\n                \"humidity\": 65.0,\n                \"pressure\": 1013.2,\n                \"wind_speed\": 12.0,\n                \"wind_direction\": 180.0,\n                \"visibility\": 10.0,\n                \"weather_condition\": \"Partly Cloudy\",\n                \"cloud_coverage\": 25.0,\n                \"precipitation\": 0.0,\n                \"uv_index\": 5.0,\n                \"air_quality_index\": 50\n            }\n        ]\n        \n        # Ingest data\n        kusto_client.ingest_weather_data(sample_data)\n        \n        # Query latest data\n        latest_data = kusto_client.get_latest_weather_data(\"north\", 1)\n        print(f\"Latest data: {len(latest_data)} records\")\n        \n        # Close connections\n        kusto_client.close_connections()