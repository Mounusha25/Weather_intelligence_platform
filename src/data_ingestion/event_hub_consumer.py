"""
Azure Event Hub Consumer
Consumes weather telemetry data from Azure Event Hubs for processing
"""

import asyncio
import json
import logging
from typing import List, Optional, Callable, Any
from datetime import datetime

try:
    from azure.eventhub.aio import EventHubConsumerClient
    from azure.eventhub import EventData
except ImportError:
    # Fallback for when Azure SDK is not installed
    EventHubConsumerClient = None
    EventData = None

from config.config import Config

logger = logging.getLogger(__name__)


class WeatherEventHubConsumer:
    """
    Azure Event Hub Consumer for weather telemetry data
    Processes incoming weather events with configurable handlers
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.consumer_client = None
        self._connection_string = config.eventhub.connection_string
        self._event_hub_name = config.eventhub.event_hub_name
        self._consumer_group = config.eventhub.consumer_group
        
        # Event processing statistics
        self.events_processed = 0
        self.events_failed = 0
        self.start_time = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        if EventHubConsumerClient is None:
            raise ImportError("Azure Event Hub SDK not installed. Install with: pip install azure-eventhub")
            
        self.consumer_client = EventHubConsumerClient.from_connection_string(
            self._connection_string,
            consumer_group=self._consumer_group,
            eventhub_name=self._event_hub_name
        )
        self.start_time = datetime.now()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.consumer_client:
            await self.consumer_client.close()
    
    async def start_consuming(self, event_handler: Callable[[dict], None] = None) -> None:
        """
        Start consuming events from Event Hub
        
        Args:
            event_handler: Optional custom event handler function
        """
        if not self.consumer_client:
            logger.error("Consumer client not initialized")
            return
        
        logger.info(f"Starting Event Hub consumer for {self._event_hub_name}")
        
        try:
            async with self.consumer_client:
                await self.consumer_client.receive(
                    on_event=self._create_event_processor(event_handler),
                    on_partition_initialize=self._on_partition_initialize,
                    on_partition_close=self._on_partition_close,
                    on_error=self._on_error,
                    starting_position="-1"  # Start from the latest events
                )
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
        except Exception as e:
            logger.error(f"Error in consumer: {e}")
    
    def _create_event_processor(self, custom_handler: Optional[Callable[[dict], None]]):
        """Create event processor with custom or default handler"""
        
        async def process_events(partition_context, event):
            """Process incoming events"""
            try:
                # Decode event data
                event_body = event.body_as_str(encoding='UTF-8')
                weather_data = json.loads(event_body)
                
                # Add event metadata
                event_info = {
                    "partition_id": partition_context.partition_id,
                    "sequence_number": event.sequence_number,
                    "offset": event.offset,
                    "enqueued_time": event.enqueued_time,
                    "properties": event.properties,
                    "data": weather_data
                }
                
                # Process with custom or default handler
                if custom_handler:
                    await self._safe_call_handler(custom_handler, event_info)
                else:
                    await self._default_event_handler(event_info)
                
                self.events_processed += 1
                
                # Update checkpoint periodically (every 10 events)
                if self.events_processed % 10 == 0:
                    await partition_context.update_checkpoint(event)
                    logger.debug(f"Checkpoint updated at event {self.events_processed}")
                
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                self.events_failed += 1
        
        return process_events
    
    async def _safe_call_handler(self, handler: Callable[[dict], None], event_info: dict):
        """Safely call custom event handler with error handling"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event_info)
            else:
                handler(event_info)
        except Exception as e:
            logger.error(f"Error in custom event handler: {e}")
            raise
    
    async def _default_event_handler(self, event_info: dict):
        """Default event handler - logs weather data and stores for processing"""
        data = event_info["data"]
        
        logger.info(
            f"Weather Event - Region: {data.get('region', 'unknown')}, "
            f"Temp: {data.get('temperature', 0)}°C, "
            f"Condition: {data.get('weather_condition', 'unknown')}, "
            f"Severity: {event_info.get('properties', {}).get('severity', 'unknown')}"
        )
        
        # Check for severe weather alerts
        await self._check_severe_weather(data, event_info["properties"])
    
    async def _check_severe_weather(self, weather_data: dict, properties: dict):
        """Check for severe weather conditions and trigger alerts"""
        severity = properties.get("severity", "low")
        
        if severity in ["high", "critical"]:
            alert_data = {
                "timestamp": datetime.now().isoformat(),
                "region": weather_data.get("region"),
                "severity": severity,
                "conditions": {
                    "temperature": weather_data.get("temperature"),
                    "wind_speed": weather_data.get("wind_speed"),
                    "weather_condition": weather_data.get("weather_condition"),
                    "visibility": weather_data.get("visibility")
                },
                "alert_threshold": self.config.ml.severe_weather_threshold
            }
            
            logger.warning(f"SEVERE WEATHER ALERT: {json.dumps(alert_data, indent=2)}")
            
            # Here you would typically send to alerting system
            # await self.alert_system.send_alert(alert_data)
    
    async def _on_partition_initialize(self, partition_context):
        """Called when a partition is initialized"""
        logger.info(f"Partition {partition_context.partition_id} initialized")
    
    async def _on_partition_close(self, partition_context, reason):
        """Called when a partition is closed"""
        logger.info(f"Partition {partition_context.partition_id} closed: {reason}")
    
    async def _on_error(self, partition_context, error):
        """Called when an error occurs"""
        logger.error(f"Error in partition {partition_context.partition_id}: {error}")
    
    def get_statistics(self) -> dict:
        """Get consumer statistics"""
        runtime = datetime.now() - self.start_time if self.start_time else None
        
        return {
            "events_processed": self.events_processed,
            "events_failed": self.events_failed,
            "success_rate": (self.events_processed / (self.events_processed + self.events_failed)) 
                           if (self.events_processed + self.events_failed) > 0 else 0,
            "runtime_seconds": runtime.total_seconds() if runtime else 0,
            "events_per_second": (self.events_processed / runtime.total_seconds()) 
                               if runtime and runtime.total_seconds() > 0 else 0
        }


# Custom event handlers
class WeatherDataProcessor:
    """Custom event processor for weather data"""
    
    def __init__(self, config: Config):
        self.config = config
        self.processed_events = []
    
    async def handle_weather_event(self, event_info: dict):
        """Process weather events for ML pipeline"""
        weather_data = event_info["data"]
        
        # Extract features for ML model
        features = {
            "timestamp": weather_data["timestamp"],
            "region": weather_data["region"],
            "temperature": weather_data["temperature"],
            "humidity": weather_data["humidity"],
            "pressure": weather_data["pressure"],
            "wind_speed": weather_data["wind_speed"],
            "visibility": weather_data["visibility"],
            "severity_score": self._calculate_severity_score(weather_data)
        }
        
        self.processed_events.append(features)
        
        # Process in batches for efficiency
        if len(self.processed_events) >= self.config.weather.batch_size:
            await self._process_batch()
    
    def _calculate_severity_score(self, weather_data: dict) -> float:
        """Calculate numerical severity score for ML features"""
        score = 0.0
        
        # Temperature factor
        temp = weather_data.get("temperature", 20)
        if temp < 0 or temp > 35:
            score += 0.3
        
        # Wind factor
        wind = weather_data.get("wind_speed", 0)
        if wind > 15:
            score += 0.4
        elif wind > 10:
            score += 0.2
        
        # Visibility factor
        visibility = weather_data.get("visibility", 10)
        if visibility < 5:
            score += 0.3
        
        return min(score, 1.0)  # Cap at 1.0
    
    async def _process_batch(self):
        """Process batch of weather events"""
        logger.info(f"Processing batch of {len(self.processed_events)} weather events")
        
        # Here you would send to ML pipeline or database
        # await self.ml_pipeline.process_features(self.processed_events)
        
        # Clear processed events
        self.processed_events.clear()


# Example usage
async def main():
    """Example usage of WeatherEventHubConsumer"""
    config = Config()
    
    # Create custom processor
    processor = WeatherDataProcessor(config)
    
    async with WeatherEventHubConsumer(config) as consumer:
        # Start consuming with custom handler
        await consumer.start_consuming(event_handler=processor.handle_weather_event)


if __name__ == "__main__":
    asyncio.run(main())