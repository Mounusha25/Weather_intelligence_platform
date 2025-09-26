"""
Weather Intelligence Platform Configuration
Simple configuration without external dependencies
"""

import os
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class AzureConfig:
    """Azure service configurations"""
    subscription_id: str = ""
    resource_group: str = "weather-intelligence-rg"
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""

    def __post_init__(self):
        self.subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID", self.subscription_id)
        self.resource_group = os.getenv("AZURE_RESOURCE_GROUP", self.resource_group)
        self.tenant_id = os.getenv("AZURE_TENANT_ID", self.tenant_id)
        self.client_id = os.getenv("AZURE_CLIENT_ID", self.client_id)
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET", self.client_secret)


@dataclass
class EventHubConfig:
    """Azure Event Hubs configuration"""
    connection_string: str = ""
    event_hub_name: str = "weather-telemetry"
    consumer_group: str = "$Default"
    partition_count: int = 4

    def __post_init__(self):
        self.connection_string = os.getenv("EVENT_HUB_CONNECTION_STRING", self.connection_string)
        self.event_hub_name = os.getenv("EVENT_HUB_NAME", self.event_hub_name)
        self.consumer_group = os.getenv("EVENT_HUB_CONSUMER_GROUP", self.consumer_group)
        self.partition_count = int(os.getenv("EVENT_HUB_PARTITION_COUNT", str(self.partition_count)))


@dataclass
class KustoConfig:
    """Azure Data Explorer (Kusto) configuration"""
    cluster_uri: str = ""
    database_name: str = "WeatherIntelligence"
    table_name: str = "WeatherTelemetry"
    ingestion_mapping: str = "weather_mapping"

    def __post_init__(self):
        self.cluster_uri = os.getenv("KUSTO_CLUSTER_URI", self.cluster_uri)
        self.database_name = os.getenv("KUSTO_DATABASE_NAME", self.database_name)
        self.table_name = os.getenv("KUSTO_TABLE_NAME", self.table_name)
        self.ingestion_mapping = os.getenv("KUSTO_INGESTION_MAPPING", self.ingestion_mapping)


@dataclass
class DatabricksConfig:
    """Databricks configuration"""
    workspace_url: str = ""
    access_token: str = ""
    cluster_id: str = ""
    notebook_path: str = "/weather-intelligence"

    def __post_init__(self):
        self.workspace_url = os.getenv("DATABRICKS_WORKSPACE_URL", self.workspace_url)
        self.access_token = os.getenv("DATABRICKS_ACCESS_TOKEN", self.access_token)
        self.cluster_id = os.getenv("DATABRICKS_CLUSTER_ID", self.cluster_id)
        self.notebook_path = os.getenv("DATABRICKS_NOTEBOOK_PATH", self.notebook_path)


@dataclass
class PowerBIConfig:
    """Power BI configuration"""
    workspace_id: str = ""
    dataset_id: str = ""
    report_id: str = ""
    app_id: str = ""
    app_secret: str = ""

    def __post_init__(self):
        self.workspace_id = os.getenv("POWERBI_WORKSPACE_ID", self.workspace_id)
        self.dataset_id = os.getenv("POWERBI_DATASET_ID", self.dataset_id)
        self.report_id = os.getenv("POWERBI_REPORT_ID", self.report_id)
        self.app_id = os.getenv("POWERBI_APP_ID", self.app_id)
        self.app_secret = os.getenv("POWERBI_APP_SECRET", self.app_secret)


@dataclass
class MLConfig:
    """Machine Learning configuration"""
    model_registry_path: str = "models/"
    arima_order: tuple = (2, 1, 2)  # (p, d, q) for ARIMA
    xgboost_n_estimators: int = 100
    xgboost_max_depth: int = 6
    xgboost_learning_rate: float = 0.1
    
    # Model training parameters
    training_window_hours: int = 168  # 1 week
    prediction_horizon_minutes: int = 360  # 6 hours
    retrain_interval_hours: int = 24
    
    # Alert thresholds
    severe_weather_threshold: float = 0.7
    alert_lead_time_minutes: int = 18

    def __post_init__(self):
        self.model_registry_path = os.getenv("ML_MODEL_REGISTRY_PATH", self.model_registry_path)
        self.xgboost_n_estimators = int(os.getenv("XGBOOST_N_ESTIMATORS", str(self.xgboost_n_estimators)))
        self.xgboost_max_depth = int(os.getenv("XGBOOST_MAX_DEPTH", str(self.xgboost_max_depth)))
        self.xgboost_learning_rate = float(os.getenv("XGBOOST_LEARNING_RATE", str(self.xgboost_learning_rate)))
        self.training_window_hours = int(os.getenv("TRAINING_WINDOW_HOURS", str(self.training_window_hours)))
        self.prediction_horizon_minutes = int(os.getenv("PREDICTION_HORIZON_MINUTES", str(self.prediction_horizon_minutes)))
        self.retrain_interval_hours = int(os.getenv("RETRAIN_INTERVAL_HOURS", str(self.retrain_interval_hours)))
        self.severe_weather_threshold = float(os.getenv("SEVERE_WEATHER_THRESHOLD", str(self.severe_weather_threshold)))
        self.alert_lead_time_minutes = int(os.getenv("ALERT_LEAD_TIME_MINUTES", str(self.alert_lead_time_minutes)))


@dataclass
class AlertingConfig:
    """Alerting system configuration"""
    webhook_url: str = ""
    email_smtp_server: str = "smtp.office365.com"
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    
    # Alert recipients by region
    regional_contacts: Dict[str, List[str]] = None
    
    # Escalation settings
    escalation_delay_minutes: int = 15
    max_escalation_level: int = 3

    def __post_init__(self):
        if self.regional_contacts is None:
            self.regional_contacts = {
                "north": ["north-team@company.com"],
                "south": ["south-team@company.com"],
                "east": ["east-team@company.com"],
                "west": ["west-team@company.com"]
            }
        
        self.webhook_url = os.getenv("ALERT_WEBHOOK_URL", self.webhook_url)
        self.email_smtp_server = os.getenv("EMAIL_SMTP_SERVER", self.email_smtp_server)
        self.email_smtp_port = int(os.getenv("EMAIL_SMTP_PORT", str(self.email_smtp_port)))
        self.email_username = os.getenv("EMAIL_USERNAME", self.email_username)
        self.email_password = os.getenv("EMAIL_PASSWORD", self.email_password)
        self.escalation_delay_minutes = int(os.getenv("ESCALATION_DELAY_MINUTES", str(self.escalation_delay_minutes)))
        self.max_escalation_level = int(os.getenv("MAX_ESCALATION_LEVEL", str(self.max_escalation_level)))


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    application_insights_key: str = ""
    log_level: str = "INFO"
    metrics_port: int = 8000
    
    # Performance thresholds
    dashboard_p95_threshold_ms: int = 700
    data_freshness_threshold_seconds: int = 60
    
    # Health check endpoints
    health_check_interval_seconds: int = 30

    def __post_init__(self):
        self.application_insights_key = os.getenv("APPLICATION_INSIGHTS_KEY", self.application_insights_key)
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.metrics_port = int(os.getenv("METRICS_PORT", str(self.metrics_port)))
        self.dashboard_p95_threshold_ms = int(os.getenv("DASHBOARD_P95_THRESHOLD_MS", str(self.dashboard_p95_threshold_ms)))
        self.data_freshness_threshold_seconds = int(os.getenv("DATA_FRESHNESS_THRESHOLD_SECONDS", str(self.data_freshness_threshold_seconds)))
        self.health_check_interval_seconds = int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", str(self.health_check_interval_seconds)))


@dataclass
class TestingConfig:
    """Testing and validation configuration"""
    cuped_pre_experiment_days: int = 7
    statistical_power: float = 0.9
    minimum_detectable_effect: float = 0.03  # 3%
    test_duration_days: int = 14
    
    # Backtesting parameters
    backtest_start_date: str = "2023-01-01"
    backtest_end_date: str = "2024-01-01"
    cross_validation_folds: int = 5

    def __post_init__(self):
        self.cuped_pre_experiment_days = int(os.getenv("CUPED_PRE_EXPERIMENT_DAYS", str(self.cuped_pre_experiment_days)))
        self.statistical_power = float(os.getenv("STATISTICAL_POWER", str(self.statistical_power)))
        self.minimum_detectable_effect = float(os.getenv("MINIMUM_DETECTABLE_EFFECT", str(self.minimum_detectable_effect)))
        self.test_duration_days = int(os.getenv("TEST_DURATION_DAYS", str(self.test_duration_days)))
        self.backtest_start_date = os.getenv("BACKTEST_START_DATE", self.backtest_start_date)
        self.backtest_end_date = os.getenv("BACKTEST_END_DATE", self.backtest_end_date)
        self.cross_validation_folds = int(os.getenv("CROSS_VALIDATION_FOLDS", str(self.cross_validation_folds)))


@dataclass
class WeatherConfig:
    """Weather data configuration"""
    # Weather API settings
    weather_api_key: str = ""
    weather_api_base_url: str = "https://api.openweathermap.org/data/2.5"
    
    # Geographic regions
    regions: Dict[str, Dict[str, float]] = None
    
    # Data collection settings
    collection_interval_minutes: int = 5
    batch_size: int = 100

    def __post_init__(self):
        if self.regions is None:
            self.regions = {
                "north": {"lat": 40.7128, "lon": -74.0060},
                "south": {"lat": 25.7617, "lon": -80.1918},
                "east": {"lat": 39.2904, "lon": -76.6122},
                "west": {"lat": 34.0522, "lon": -118.2437}
            }
        
        self.weather_api_key = os.getenv("WEATHER_API_KEY", self.weather_api_key)
        self.weather_api_base_url = os.getenv("WEATHER_API_BASE_URL", self.weather_api_base_url)
        self.collection_interval_minutes = int(os.getenv("WEATHER_COLLECTION_INTERVAL_MINUTES", str(self.collection_interval_minutes)))
        self.batch_size = int(os.getenv("WEATHER_BATCH_SIZE", str(self.batch_size)))


@dataclass
class Config:
    """Main configuration class"""
    azure: AzureConfig = None
    eventhub: EventHubConfig = None
    kusto: KustoConfig = None
    databricks: DatabricksConfig = None
    powerbi: PowerBIConfig = None
    ml: MLConfig = None
    alerting: AlertingConfig = None
    monitoring: MonitoringConfig = None
    testing: TestingConfig = None
    weather: WeatherConfig = None

    def __post_init__(self):
        self.azure = AzureConfig()
        self.eventhub = EventHubConfig()
        self.kusto = KustoConfig()
        self.databricks = DatabricksConfig()
        self.powerbi = PowerBIConfig()
        self.ml = MLConfig()
        self.alerting = AlertingConfig()
        self.monitoring = MonitoringConfig()
        self.testing = TestingConfig()
        self.weather = WeatherConfig()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global configuration instance
config = Config()