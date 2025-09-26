"""
Azure Data Explorer (Kusto) Integration
Time-series analytics and fast querying of weather data
"""

from .kusto_client import WeatherKustoClient
from .kusto_queries import WeatherQueries

__all__ = [
    "WeatherKustoClient",
    "WeatherQueries"
]