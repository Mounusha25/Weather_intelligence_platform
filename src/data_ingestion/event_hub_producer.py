"""
Azure Event Hub Producer
Sends weather telemetry data to Azure Event Hubs for real-time processing
"""

import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

try:
    from azure.eventhub.aio import EventHubProducerClient
    from azure.eventhub import EventData
except ImportError:
    # Fallback for when Azure SDK is not installed
    EventHubProducerClient = None
    EventData = None

from config.config import Config
from .weather_api_client import WeatherReading

logger = logging.getLogger(__name__)


class WeatherEventHubProducer:
    """
    Azure Event Hub Producer for weather telemetry data
    Handles batch processing and error recovery
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.producer_client: Optional[EventHubProducerClient] = None
        self._connection_string = config.eventhub.connection_string
        self._event_hub_name = config.eventhub.event_hub_name
        self._batch_size = config.weather.batch_size
        
    async def __aenter__(self):
        """Async context manager entry"""
        if EventHubProducerClient is None:
            raise ImportError("Azure Event Hub SDK not installed. Install with: pip install azure-eventhub")
            
        self.producer_client = EventHubProducerClient.from_connection_string(
            self._connection_string,
            eventhub_name=self._event_hub_name
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.producer_client:
            await self.producer_client.close()
    
    async def send_weather_reading(self, weather_reading: WeatherReading) -> bool:
        """
        Send a single weather reading to Event Hub
        
        Args:
            weather_reading: WeatherReading object to send
            
        Returns:
            True if successful, False otherwise
        """
        return await self.send_weather_readings([weather_reading])
    
    async def send_weather_readings(self, weather_readings: List[WeatherReading]) -> bool:
        """
        Send multiple weather readings to Event Hub in batches
        
        Args:
            weather_readings: List of WeatherReading objects to send
            
        Returns:
            True if all batches sent successfully, False otherwise
        """
        if not self.producer_client:
            logger.error("Producer client not initialized")
            return False
        
        try:
            # Process readings in batches
            for i in range(0, len(weather_readings), self._batch_size):
                batch = weather_readings[i:i + self._batch_size]
                success = await self._send_batch(batch)
                if not success:
                    logger.error(f"Failed to send batch {i//self._batch_size + 1}")
                    return False
                    
            logger.info(f"Successfully sent {len(weather_readings)} weather readings")
            return True
            
        except Exception as e:
            logger.error(f"Error sending weather readings to Event Hub: {e}")
            return False
    
    async def _send_batch(self, weather_readings: List[WeatherReading]) -> bool:
        """Send a batch of weather readings to Event Hub"""
        try:
            async with self.producer_client:
                event_data_batch = await self.producer_client.create_batch()
                
                for reading in weather_readings:
                    # Convert reading to Event Hub event data
                    event_data = self._create_event_data(reading)
                    
                    try:
                        event_data_batch.add(event_data)
                    except ValueError as e:
                        # Batch is full, send it and create a new one
                        logger.warning(f"Batch full, sending partial batch: {e}")
                        if len(event_data_batch):
                            await self.producer_client.send_batch(event_data_batch)
                        
                        # Create new batch and add the current event
                        event_data_batch = await self.producer_client.create_batch()
                        event_data_batch.add(event_data)
                
                # Send the final batch
                if len(event_data_batch):
                    await self.producer_client.send_batch(event_data_batch)
                    
            return True
            
        except Exception as e:
            logger.error(f"Error sending batch to Event Hub: {e}")
            return False
    
    def _create_event_data(self, weather_reading: WeatherReading) -> EventData:
        """
        Convert WeatherReading to EventData with proper partitioning
        
        Args:
            weather_reading: WeatherReading object
            
        Returns:
            EventData object for Event Hub
        """
        # Create event data with JSON payload
        event_data = EventData(weather_reading.to_json())
        
        # Add properties for routing and filtering
        event_data.properties = {
            "region": weather_reading.region,
            "timestamp": weather_reading.timestamp,
            "weather_condition": weather_reading.weather_condition,
            "temperature_range": self._get_temperature_range(weather_reading.temperature),
            "severity": self._assess_weather_severity(weather_reading)
        }
        
        # Set partition key based on region for even distribution
        event_data.partition_key = weather_reading.region
        
        return event_data
    
    def _get_temperature_range(self, temperature: float) -> str:
        """Categorize temperature into ranges"""
        if temperature < 0:
            return "freezing"
        elif temperature < 10:
            return "cold"
        elif temperature < 25:
            return "mild"
        elif temperature < 35:
            return "warm"
        else:
            return "hot"
    
    def _assess_weather_severity(self, reading: WeatherReading) -> str:
        """
        Assess weather severity for prioritization
        
        Args:
            reading: WeatherReading object
            
        Returns:
            Severity level: low, medium, high, critical
        """
        severity_score = 0
        
        # Temperature extremes
        if reading.temperature < -10 or reading.temperature > 40:
            severity_score += 3
        elif reading.temperature < 0 or reading.temperature > 35:
            severity_score += 2
        
        # Wind speed
        if reading.wind_speed > 25:  # ~90 km/h
            severity_score += 3
        elif reading.wind_speed > 15:  # ~54 km/h
            severity_score += 2
        elif reading.wind_speed > 10:  # ~36 km/h
            severity_score += 1
        
        # Precipitation
        if reading.precipitation > 50:  # Heavy rain
            severity_score += 3
        elif reading.precipitation > 20:  # Moderate rain
            severity_score += 2
        elif reading.precipitation > 5:  # Light rain
            severity_score += 1
        
        # Visibility
        if reading.visibility < 1:  # Very poor visibility
            severity_score += 3
        elif reading.visibility < 5:  # Poor visibility
            severity_score += 2
        
        # Severe weather conditions
        severe_conditions = ["Thunderstorm", "Tornado", "Hurricane", "Blizzard", "Hail"]
        if reading.weather_condition in severe_conditions:
            severity_score += 4
        
        # Map score to severity levels
        if severity_score >= 8:
            return "critical"
        elif severity_score >= 5:
            return "high"
        elif severity_score >= 2:
            return "medium"
        else:
            return "low"
    
    async def start_streaming(self, weather_client) -> None:
        """
        Start streaming weather data from weather client to Event Hub
        
        Args:
            weather_client: WeatherAPIClient instance
        """
        logger.info("Starting weather data streaming to Event Hub...")
        
        async def weather_callback(weather_reading: WeatherReading):
            """Callback to handle weather readings"""
            success = await self.send_weather_reading(weather_reading)
            if success:
                logger.debug(f"Sent weather data for region {weather_reading.region}")
            else:
                logger.error(f"Failed to send weather data for region {weather_reading.region}")
        
        # Start continuous collection with Event Hub callback
        await weather_client.start_continuous_collection(callback=weather_callback)


# Example usage
async def main():
    """Example usage of WeatherEventHubProducer"""
    from .weather_api_client import WeatherAPIClient
    
    config = Config()
    
    async with WeatherAPIClient(config) as weather_client, \
               WeatherEventHubProducer(config) as event_producer:
        
        # Fetch and send weather data for all regions
        weather_readings = await weather_client.fetch_all_regions()
        success = await event_producer.send_weather_readings(weather_readings)
        
        if success:
            print(f"Successfully sent {len(weather_readings)} weather readings to Event Hub")
        else:
            print("Failed to send weather readings to Event Hub")


if __name__ == "__main__":
    asyncio.run(main())