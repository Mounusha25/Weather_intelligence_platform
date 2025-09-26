"""
Weather API Client
Fetches real-time weather data from various weather services
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from config.config import Config

logger = logging.getLogger(__name__)


@dataclass
class WeatherReading:
    """Weather data point"""
    timestamp: str
    region: str
    latitude: float
    longitude: float
    temperature: float  # Celsius
    humidity: float  # Percentage
    pressure: float  # hPa
    wind_speed: float  # m/s
    wind_direction: float  # degrees
    visibility: float  # km
    weather_condition: str
    cloud_coverage: float  # percentage
    precipitation: float  # mm
    uv_index: float
    air_quality_index: Optional[int] = None
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(asdict(self))


class WeatherAPIClient:
    """
    Weather API client for fetching real-time weather data
    Supports multiple weather APIs with fallback mechanisms
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_endpoints = {
            "openweather": f"{config.weather.weather_api_base_url}/weather",
            "current": f"{config.weather.weather_api_base_url}/onecall"
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def fetch_weather_data(self, region: str) -> Optional[WeatherReading]:
        """
        Fetch weather data for a specific region
        
        Args:
            region: Region identifier (north, south, east, west)
            
        Returns:
            WeatherReading object or None if failed
        """
        if region not in self.config.weather.regions:
            logger.error(f"Unknown region: {region}")
            return None
        
        region_config = self.config.weather.regions[region]
        
        try:
            # Try OpenWeatherMap API first
            weather_data = await self._fetch_from_openweather(
                region_config["lat"], 
                region_config["lon"]
            )
            
            if weather_data:
                return self._parse_openweather_response(weather_data, region)
                
            logger.warning(f"Failed to fetch weather data for region {region}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching weather data for region {region}: {e}")
            return None
    
    async def _fetch_from_openweather(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Fetch data from OpenWeatherMap API"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        url = f"{self.api_endpoints['openweather']}"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.config.weather.weather_api_key,
            "units": "metric"
        }
        
        try:
            async with self.session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"OpenWeatherMap API error: {response.status}")
                    return None
        except asyncio.TimeoutError:
            logger.error("Timeout fetching data from OpenWeatherMap API")
            return None
        except Exception as e:
            logger.error(f"Error calling OpenWeatherMap API: {e}")
            return None
    
    def _parse_openweather_response(self, data: Dict[str, Any], region: str) -> WeatherReading:
        """Parse OpenWeatherMap API response into WeatherReading"""
        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})
        visibility_m = data.get("visibility", 10000)  # Default 10km in meters
        
        return WeatherReading(
            timestamp=datetime.now(timezone.utc).isoformat(),
            region=region,
            latitude=data["coord"]["lat"],
            longitude=data["coord"]["lon"],
            temperature=main.get("temp", 0.0),
            humidity=main.get("humidity", 0.0),
            pressure=main.get("pressure", 1013.25),
            wind_speed=wind.get("speed", 0.0),
            wind_direction=wind.get("deg", 0.0),
            visibility=visibility_m / 1000.0,  # Convert to km
            weather_condition=weather.get("main", "Unknown"),
            cloud_coverage=clouds.get("all", 0.0),
            precipitation=0.0,  # Not available in current weather API
            uv_index=0.0  # Not available in current weather API
        )
    
    async def fetch_all_regions(self) -> List[WeatherReading]:
        """
        Fetch weather data for all configured regions concurrently
        
        Returns:
            List of WeatherReading objects
        """
        tasks = [
            self.fetch_weather_data(region) 
            for region in self.config.weather.regions.keys()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        weather_readings = []
        for result in results:
            if isinstance(result, WeatherReading):
                weather_readings.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error in concurrent fetch: {result}")
        
        return weather_readings
    
    async def start_continuous_collection(self, callback=None) -> None:
        """
        Start continuous weather data collection
        
        Args:
            callback: Optional callback function to process weather readings
        """
        logger.info("Starting continuous weather data collection...")
        
        while True:
            try:
                weather_readings = await self.fetch_all_regions()
                
                if callback:
                    for reading in weather_readings:
                        await callback(reading)
                else:
                    # Default behavior: log the readings
                    for reading in weather_readings:
                        logger.info(f"Weather data: {reading.region} - "
                                  f"Temp: {reading.temperature}°C, "
                                  f"Humidity: {reading.humidity}%, "
                                  f"Condition: {reading.weather_condition}")
                
                # Wait for the configured interval
                await asyncio.sleep(self.config.weather.collection_interval_minutes * 60)
                
            except asyncio.CancelledError:
                logger.info("Weather collection cancelled")
                break
            except Exception as e:
                logger.error(f"Error in continuous collection: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds before retry


# Example usage
async def main():
    """Example usage of WeatherAPIClient"""
    config = Config()
    
    async with WeatherAPIClient(config) as client:
        # Fetch data for a single region
        weather = await client.fetch_weather_data("north")
        if weather:
            print(f"Weather in north region: {weather.to_json()}")
        
        # Fetch data for all regions
        all_weather = await client.fetch_all_regions()
        print(f"Collected {len(all_weather)} weather readings")


if __name__ == "__main__":
    asyncio.run(main())