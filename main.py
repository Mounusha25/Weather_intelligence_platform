"""
Main Application Entry Point
Weather Intelligence Platform - Orchestrates all components
"""

import asyncio
import logging
import signal
import sys
from typing import Optional
from datetime import datetime

# Import platform components
from config.config import Config
from src.data_ingestion.weather_api_client import WeatherAPIClient
from src.data_ingestion.event_hub_producer import WeatherEventHubProducer  
from src.data_ingestion.event_hub_consumer import WeatherEventHubConsumer
from src.kusto.kusto_client import WeatherKustoClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('weather_intelligence.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class WeatherIntelligencePlatform:
    """
    Main application class for Weather Intelligence Platform
    Coordinates real-time data ingestion, processing, and alerting
    """
    
    def __init__(self):
        self.config = Config()
        self.running = False
        
        # Initialize components
        self.weather_client: Optional[WeatherAPIClient] = None
        self.event_producer: Optional[WeatherEventHubProducer] = None
        self.event_consumer: Optional[WeatherEventHubConsumer] = None
        self.kusto_client: Optional[WeatherKustoClient] = None
        
        # Performance metrics
        self.start_time = None
        self.events_processed = 0
        
    async def initialize(self) -> bool:
        """
        Initialize all platform components
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing Weather Intelligence Platform...")
            
            # Initialize weather API client
            self.weather_client = WeatherAPIClient(self.config)
            
            # Initialize Event Hub components
            self.event_producer = WeatherEventHubProducer(self.config)
            self.event_consumer = WeatherEventHubConsumer(self.config)
            
            # Initialize Kusto client
            self.kusto_client = WeatherKustoClient(self.config)
            
            # Setup Kusto database
            if self.kusto_client.initialize_clients():
                self.kusto_client.create_database_schema()
                self.kusto_client.optimize_for_dashboards()
            
            logger.info("Platform initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during platform initialization: {e}")
            return False
    
    async def start_data_collection(self) -> None:
        """Start real-time weather data collection"""
        logger.info("Starting weather data collection...")
        
        async def weather_callback(weather_reading):
            """Callback to process weather readings"""
            try:
                # Send to Event Hub
                if self.event_producer:
                    success = await self.event_producer.send_weather_reading(weather_reading)
                    if success:
                        self.events_processed += 1
                        logger.debug(f"Weather data sent for region {weather_reading.region}")
                
                # Also send directly to Kusto for analytics
                if self.kusto_client:
                    weather_data = [weather_reading.to_json()]
                    self.kusto_client.ingest_weather_data(weather_data)
                
            except Exception as e:
                logger.error(f"Error processing weather reading: {e}")
        
        # Start continuous collection
        if self.weather_client:
            async with self.weather_client as client:
                await client.start_continuous_collection(callback=weather_callback)
    
    async def start_event_processing(self) -> None:
        """Start Event Hub consumer for real-time processing"""
        logger.info("Starting Event Hub event processing...")
        
        async def event_handler(event_info):
            """Handle incoming events from Event Hub"""
            try:
                weather_data = event_info["data"]
                region = weather_data.get("region")
                severity = event_info.get("properties", {}).get("severity", "low")
                
                logger.info(f"Processing event from {region} with severity {severity}")
                
                # Store event processing metrics
                self.events_processed += 1
                
                # Trigger alerts for severe weather
                if severity in ["high", "critical"]:
                    await self._trigger_weather_alert(weather_data, event_info["properties"])
                
            except Exception as e:
                logger.error(f"Error processing event: {e}")
        
        # Start consuming events
        if self.event_consumer:
            async with self.event_consumer as consumer:
                await consumer.start_consuming(event_handler=event_handler)
    
    async def _trigger_weather_alert(self, weather_data: dict, properties: dict) -> None:
        """Trigger weather alert for severe conditions"""
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "region": weather_data.get("region"),
            "severity": properties.get("severity"),
            "conditions": {
                "temperature": weather_data.get("temperature"),
                "wind_speed": weather_data.get("wind_speed"),
                "weather_condition": weather_data.get("weather_condition"),
                "visibility": weather_data.get("visibility")
            },
            "alert_threshold": self.config.ml.severe_weather_threshold,
            "lead_time_minutes": self.config.ml.alert_lead_time_minutes
        }
        
        logger.warning(f"SEVERE WEATHER ALERT: {alert_data}")
        
        # Here you would integrate with alerting systems:
        # - Send email notifications
        # - Post to Slack/Teams
        # - Update dashboard alerts
        # - Trigger automated responses
        
        # Example: Save alert to Kusto for tracking
        if self.kusto_client:
            alert_record = {
                **weather_data,
                "alert_type": "severe_weather",
                "alert_severity": properties.get("severity"),
                "alert_timestamp": alert_data["timestamp"]
            }
            self.kusto_client.ingest_weather_data([alert_record])
    
    async def run_health_checks(self) -> dict:
        """Run health checks on all components"""
        health_status = {
            "platform_status": "healthy",
            "components": {},
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": 0
        }
        
        if self.start_time:
            health_status["uptime_seconds"] = (datetime.now() - self.start_time).total_seconds()
        
        # Check Kusto connectivity
        try:
            if self.kusto_client:
                recent_data = self.kusto_client.get_latest_weather_data(hours=1)
                health_status["components"]["kusto"] = {
                    "status": "healthy",
                    "recent_records": len(recent_data),
                    "performance": self.kusto_client.get_performance_metrics()
                }
        except Exception as e:
            health_status["components"]["kusto"] = {
                "status": "unhealthy", 
                "error": str(e)
            }
            health_status["platform_status"] = "degraded"
        
        # Check Event Hub consumer stats
        try:
            if self.event_consumer:
                consumer_stats = self.event_consumer.get_statistics()
                health_status["components"]["event_consumer"] = {
                    "status": "healthy",
                    "statistics": consumer_stats
                }
        except Exception as e:
            health_status["components"]["event_consumer"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Overall platform metrics
        health_status["metrics"] = {
            "events_processed": self.events_processed,
            "events_per_second": self.events_processed / health_status["uptime_seconds"] if health_status["uptime_seconds"] > 0 else 0
        }
        
        return health_status
    
    async def run_performance_monitoring(self) -> None:
        """Continuous performance monitoring"""
        while self.running:
            try:
                health_status = await self.run_health_checks()
                
                # Log performance metrics
                metrics = health_status["metrics"]
                logger.info(f"Performance: {metrics['events_processed']} events processed, "
                          f"{metrics['events_per_second']:.2f} events/sec")
                
                # Check for performance issues
                kusto_perf = health_status["components"].get("kusto", {}).get("performance", {})
                avg_query_time = kusto_perf.get("average_query_time_ms", 0)
                
                if avg_query_time > self.config.monitoring.dashboard_p95_threshold_ms:
                    logger.warning(f"Kusto query performance degraded: {avg_query_time:.2f}ms > "
                                 f"{self.config.monitoring.dashboard_p95_threshold_ms}ms threshold")
                
                # Sleep until next monitoring cycle
                await asyncio.sleep(self.config.monitoring.health_check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds before retry
    
    async def start(self) -> None:
        """Start the Weather Intelligence Platform"""
        self.start_time = datetime.now()
        self.running = True
        
        logger.info("Starting Weather Intelligence Platform...")
        
        # Initialize all components
        if not await self.initialize():
            logger.error("Failed to initialize platform")
            return
        
        # Start all async tasks
        tasks = []
        
        # Data collection task
        tasks.append(asyncio.create_task(self.start_data_collection()))
        
        # Event processing task 
        tasks.append(asyncio.create_task(self.start_event_processing()))
        
        # Performance monitoring task
        tasks.append(asyncio.create_task(self.run_performance_monitoring()))
        
        logger.info(f"Platform started with {len(tasks)} background tasks")
        
        try:
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Platform shutdown initiated")
        except Exception as e:
            logger.error(f"Platform error: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the platform"""
        logger.info("Shutting down Weather Intelligence Platform...")
        
        self.running = False
        
        # Close connections
        if self.kusto_client:
            self.kusto_client.close_connections()
        
        # Final health check
        final_status = await self.run_health_checks()
        logger.info(f"Final platform statistics: {final_status['metrics']}")
        
        logger.info("Platform shutdown completed")


# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    # Cancel all running tasks
    for task in asyncio.all_tasks():
        task.cancel()


async def main():
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start platform
    platform = WeatherIntelligencePlatform()
    
    try:
        await platform.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await platform.shutdown()


if __name__ == "__main__":
    # Run the platform
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)