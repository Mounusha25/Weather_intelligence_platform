"""
Data Ingestion Module
Handles Azure Event Hubs integration for streaming weather telemetry
"""

from .event_hub_producer import WeatherEventHubProducer
from .event_hub_consumer import WeatherEventHubConsumer
from .weather_api_client import WeatherAPIClient

__all__ = [
    "WeatherEventHubProducer",
    "WeatherEventHubConsumer", 
    "WeatherAPIClient"
]