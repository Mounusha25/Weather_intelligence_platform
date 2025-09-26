# API Documentation

## Real-Time Weather Intelligence Platform API

This document describes the REST API endpoints, data models, and integration patterns for the Weather Intelligence Platform.

## Base URLs

```
Development: https://weather-api-dev.azurewebsites.net/api/v1
Production:  https://weather-api-prod.azurewebsites.net/api/v1
```

## Authentication

### Azure AD Authentication
```http
Authorization: Bearer {azure-ad-token}
```

### API Key Authentication
```http
X-API-Key: {your-api-key}
```

### Service Principal
```bash
# Get access token
az account get-access-token --resource https://weather-api-prod.azurewebsites.net
```

## Core Endpoints

### Weather Data

#### Get Current Weather Data
```http
GET /weather/current
```

**Parameters:**
- `region` (string, optional): Filter by region
- `limit` (integer, optional): Limit results (default: 100, max: 1000)
- `include_forecast` (boolean, optional): Include ML predictions

**Response:**
```json
{
  "data": [
    {
      "timestamp": "2024-01-15T14:30:00Z",
      "region": "northeast",
      "temperature": 22.5,
      "humidity": 65,
      "pressure": 1013.2,
      "wind_speed": 12.3,
      "wind_direction": 180,
      "visibility": 10.0,
      "weather_condition": "partly_cloudy",
      "severity_score": 0.2,
      "alert_level": "normal",
      "forecast": {
        "next_hour": {
          "temperature": 23.1,
          "precipitation_probability": 0.15
        }
      }
    }
  ],
  "metadata": {
    "total_records": 1,
    "freshness_seconds": 45,
    "data_quality": 0.98
  }
}
```

#### Get Historical Weather Data
```http
GET /weather/history
```

**Parameters:**
- `start_date` (string, required): ISO 8601 date (YYYY-MM-DD)
- `end_date` (string, required): ISO 8601 date (YYYY-MM-DD)
- `region` (string, optional): Filter by region
- `aggregation` (string, optional): `hourly`, `daily`, `raw` (default: hourly)

**Example:**
```http
GET /weather/history?start_date=2024-01-01&end_date=2024-01-07&region=southwest&aggregation=daily
```

**Response:**
```json
{
  "data": [
    {
      "date": "2024-01-01",
      "region": "southwest",
      "avg_temperature": 18.5,
      "min_temperature": 12.1,
      "max_temperature": 24.8,
      "total_precipitation": 0.0,
      "max_wind_speed": 15.2,
      "severe_weather_events": 0
    }
  ],
  "aggregation": "daily",
  "period": {
    "start": "2024-01-01",
    "end": "2024-01-07",
    "days": 7
  }
}
```

### Weather Alerts

#### Get Active Alerts
```http
GET /alerts/active
```

**Parameters:**
- `region` (string, optional): Filter by region
- `severity` (string, optional): `low`, `medium`, `high`, `critical`
- `alert_type` (string, optional): `temperature`, `wind`, `precipitation`, `visibility`

**Response:**
```json
{
  "alerts": [
    {
      "alert_id": "alert_20240115_001",
      "timestamp": "2024-01-15T14:25:00Z",
      "region": "central",
      "alert_type": "wind",
      "severity": "high", 
      "title": "High Wind Warning",
      "description": "Sustained winds of 25+ mph expected",
      "expected_conditions": {
        "wind_speed": 28.5,
        "duration_hours": 6,
        "affected_areas": ["urban", "rural"]
      },
      "lead_time_minutes": 18,
      "confidence_score": 0.87,
      "expires_at": "2024-01-15T22:00:00Z"
    }
  ],
  "metadata": {
    "active_count": 1,
    "total_regions_affected": 1,
    "highest_severity": "high"
  }
}
```

#### Create Weather Alert
```http
POST /alerts
```

**Request Body:**
```json
{
  "region": "northeast",
  "alert_type": "temperature",
  "severity": "medium",
  "title": "Temperature Advisory", 
  "description": "Temperatures expected to drop below freezing",
  "expected_conditions": {
    "min_temperature": -5.0,
    "duration_hours": 12
  },
  "lead_time_minutes": 30,
  "expires_at": "2024-01-16T08:00:00Z"
}
```

### Machine Learning Predictions

#### Get Weather Forecast
```http
GET /ml/forecast
```

**Parameters:**
- `region` (string, optional): Target region
- `hours_ahead` (integer, optional): Forecast horizon (default: 24, max: 168)
- `model` (string, optional): `arima`, `xgboost`, `ensemble` (default: ensemble)

**Response:**
```json
{
  "forecast": [
    {
      "timestamp": "2024-01-15T15:00:00Z",
      "region": "northeast",
      "predicted_temperature": 21.8,
      "temperature_confidence": 0.92,
      "predicted_precipitation": 0.0,
      "precipitation_probability": 0.05,
      "severe_weather_risk": 0.12,
      "model_used": "ensemble"
    }
  ],
  "model_performance": {
    "mae_temperature": 1.2,
    "accuracy_precipitation": 0.89,
    "last_trained": "2024-01-15T00:00:00Z"
  }
}
```

#### Get Model Performance Metrics
```http
GET /ml/performance
```

**Response:**
```json
{
  "models": {
    "arima": {
      "mae_temperature": 1.45,
      "mae_improvement": -22.3,
      "last_evaluation": "2024-01-15T06:00:00Z",
      "training_samples": 50000,
      "status": "active"
    },
    "xgboost": {
      "accuracy_severe_weather": 0.94,
      "precision": 0.89,
      "recall": 0.91,
      "f1_score": 0.90,
      "false_alarm_reduction": -31.2,
      "last_evaluation": "2024-01-15T06:00:00Z",
      "status": "active"
    }
  },
  "ensemble_performance": {
    "overall_accuracy": 0.93,
    "lead_time_minutes": 18.5,
    "false_alarm_rate": 0.28
  }
}
```

### Data Quality

#### Get Data Quality Metrics
```http
GET /data-quality
```

**Parameters:**
- `time_window` (string, optional): `1h`, `24h`, `7d` (default: 24h)
- `region` (string, optional): Filter by region

**Response:**
```json
{
  "overall_quality": 0.96,
  "metrics": {
    "completeness": 0.98,
    "accuracy": 0.95,
    "timeliness": 0.94,
    "consistency": 0.97
  },
  "issues": [
    {
      "type": "missing_data",
      "region": "southwest", 
      "duration_minutes": 5,
      "impact": "low"
    }
  ],
  "data_freshness": {
    "avg_seconds": 42,
    "p95_seconds": 58,
    "target_seconds": 60
  }
}
```

### System Health

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T14:30:00Z",
  "components": {
    "event_hub": {
      "status": "healthy",
      "latency_ms": 15,
      "throughput_per_sec": 1250
    },
    "kusto": {
      "status": "healthy",
      "query_latency_p95_ms": 650,
      "data_freshness_seconds": 45
    },
    "ml_models": {
      "status": "healthy",
      "arima_status": "active",
      "xgboost_status": "active",
      "prediction_latency_ms": 85
    },
    "power_bi": {
      "status": "healthy",
      "dashboard_response_ms": 450,
      "last_refresh": "2024-01-15T14:29:00Z"
    }
  },
  "performance": {
    "query_latency_p95_ms": 650,
    "data_freshness_seconds": 45,
    "false_alarm_rate": 0.28,
    "prediction_accuracy": 0.93
  }
}
```

#### Detailed System Status
```http
GET /status
```

**Response:**
```json
{
  "platform": {
    "version": "1.2.0",
    "uptime_hours": 168.5,
    "environment": "production"
  },
  "data_pipeline": {
    "events_processed_last_hour": 45000,
    "processing_lag_seconds": 12,
    "error_rate": 0.001
  },
  "storage": {
    "kusto_size_gb": 256.7,
    "kusto_utilization": 0.34,
    "blob_storage_gb": 150.2
  },
  "alerts": {
    "active_alerts": 2,
    "alerts_last_24h": 15,
    "avg_lead_time_minutes": 18.5
  }
}
```

## Data Ingestion APIs

### Batch Data Upload
```http
POST /data/batch
```

**Content-Type:** `application/json` or `multipart/form-data`

**JSON Request:**
```json
{
  "data": [
    {
      "timestamp": "2024-01-15T14:30:00Z",
      "region": "northeast",
      "temperature": 22.5,
      "humidity": 65,
      "pressure": 1013.2
    }
  ],
  "source": "weather_station_001",
  "metadata": {
    "batch_id": "batch_20240115_001",
    "quality_checked": true
  }
}
```

### Streaming Data Endpoint
```http
POST /data/stream
```

**WebSocket URL:** `wss://weather-api-prod.azurewebsites.net/ws/stream`

**Message Format:**
```json
{
  "type": "weather_data",
  "timestamp": "2024-01-15T14:30:00Z",
  "region": "central",
  "data": {
    "temperature": 18.5,
    "humidity": 72,
    "wind_speed": 8.2
  }
}
```

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "INVALID_REGION",
    "message": "The specified region 'invalid' is not supported",
    "details": {
      "supported_regions": ["northeast", "southeast", "central", "southwest", "northwest"],
      "request_id": "req_20240115_001234"
    }
  },
  "timestamp": "2024-01-15T14:30:00Z"
}
```

### HTTP Status Codes
| Code | Description | Common Causes |
|------|-------------|---------------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid parameters, malformed JSON |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 422 | Validation Error | Data validation failed |
| 429 | Rate Limited | Too many requests |
| 500 | Server Error | Internal platform error |
| 503 | Service Unavailable | Platform maintenance or overload |

### Error Codes Reference
| Code | Description | Resolution |
|------|-------------|------------|
| `INVALID_REGION` | Unknown region specified | Use supported region names |
| `DATA_TOO_OLD` | Historical data request too old | Reduce date range |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Implement request throttling |
| `MODEL_UNAVAILABLE` | ML model temporarily down | Try again or use different model |
| `DATA_QUALITY_LOW` | Data quality below threshold | Check data source |

## Rate Limiting

### Default Limits
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642248000
```

| Endpoint Category | Requests per Hour | Burst Limit |
|-------------------|-------------------|-------------|
| Weather Data | 10,000 | 100/minute |
| Alerts | 5,000 | 50/minute |
| ML Predictions | 2,000 | 20/minute |
| Data Quality | 1,000 | 10/minute |
| Health Checks | 500 | 5/minute |

### Rate Limit Headers
- `X-RateLimit-Limit`: Maximum requests per hour
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Data Models

### Weather Data Schema
```typescript
interface WeatherData {
  timestamp: string;           // ISO 8601 datetime
  region: string;             // Geographic region identifier
  temperature: number;        // Celsius
  humidity: number;          // Percentage (0-100)
  pressure: number;          // hPa (hectopascals)
  wind_speed: number;        // m/s (meters per second)
  wind_direction: number;    // Degrees (0-360)
  visibility: number;        // Kilometers
  weather_condition: string; // Enumerated condition
  severity_score: number;    // 0.0-1.0 risk score
  alert_level: string;       // normal|advisory|warning|critical
}
```

### Alert Schema
```typescript
interface WeatherAlert {
  alert_id: string;
  timestamp: string;
  region: string;
  alert_type: 'temperature' | 'wind' | 'precipitation' | 'visibility';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  expected_conditions: Record<string, any>;
  lead_time_minutes: number;
  confidence_score: number;
  expires_at: string;
}
```

### Prediction Schema
```typescript
interface WeatherPrediction {
  timestamp: string;
  region: string;
  predicted_temperature: number;
  temperature_confidence: number;
  predicted_precipitation: number;
  precipitation_probability: number;
  severe_weather_risk: number;
  model_used: string;
}
```

## Integration Examples

### Python Client
```python
import requests
from datetime import datetime, timedelta

class WeatherClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {'X-API-Key': api_key}
    
    def get_current_weather(self, region: str = None):
        params = {'region': region} if region else {}
        response = requests.get(
            f"{self.base_url}/weather/current",
            headers=self.headers,
            params=params
        )
        return response.json()
    
    def get_forecast(self, region: str, hours_ahead: int = 24):
        response = requests.get(
            f"{self.base_url}/ml/forecast",
            headers=self.headers,
            params={'region': region, 'hours_ahead': hours_ahead}
        )
        return response.json()

# Usage
client = WeatherClient(
    base_url="https://weather-api-prod.azurewebsites.net/api/v1",
    api_key="your-api-key"
)

current = client.get_current_weather(region="northeast")
forecast = client.get_forecast(region="northeast", hours_ahead=48)
```

### JavaScript/Node.js Client
```javascript
class WeatherAPIClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.headers = {
            'X-API-Key': apiKey,
            'Content-Type': 'application/json'
        };
    }
    
    async getCurrentWeather(region = null) {
        const params = new URLSearchParams();
        if (region) params.append('region', region);
        
        const response = await fetch(
            `${this.baseUrl}/weather/current?${params}`,
            { headers: this.headers }
        );
        return await response.json();
    }
    
    async getActiveAlerts(severity = null) {
        const params = new URLSearchParams();
        if (severity) params.append('severity', severity);
        
        const response = await fetch(
            `${this.baseUrl}/alerts/active?${params}`,
            { headers: this.headers }
        );
        return await response.json();
    }
}

// Usage
const client = new WeatherAPIClient(
    'https://weather-api-prod.azurewebsites.net/api/v1',
    'your-api-key'
);

const weather = await client.getCurrentWeather('central');
const alerts = await client.getActiveAlerts('high');
```

### PowerShell Integration
```powershell
# Weather Intelligence Platform PowerShell Module
function Get-WeatherData {
    param(
        [string]$BaseUrl,
        [string]$ApiKey,
        [string]$Region,
        [string]$Endpoint = "weather/current"
    )
    
    $headers = @{
        'X-API-Key' = $ApiKey
        'Content-Type' = 'application/json'
    }
    
    $uri = "$BaseUrl/$Endpoint"
    if ($Region) {
        $uri += "?region=$Region"
    }
    
    try {
        $response = Invoke-RestMethod -Uri $uri -Headers $headers -Method Get
        return $response
    }
    catch {
        Write-Error "API request failed: $_"
    }
}

# Usage
$weather = Get-WeatherData -BaseUrl "https://weather-api-prod.azurewebsites.net/api/v1" -ApiKey "your-key" -Region "northeast"
```

## Webhooks

### Alert Notifications
```http
POST https://your-webhook-endpoint.com/weather-alerts
```

**Webhook Payload:**
```json
{
  "webhook_id": "webhook_20240115_001",
  "timestamp": "2024-01-15T14:30:00Z",
  "event_type": "alert_created",
  "alert": {
    "alert_id": "alert_20240115_001",
    "region": "central",
    "severity": "high",
    "alert_type": "wind",
    "title": "High Wind Warning"
  }
}
```

### Data Quality Notifications
```json
{
  "webhook_id": "webhook_20240115_002",
  "timestamp": "2024-01-15T14:30:00Z", 
  "event_type": "data_quality_degraded",
  "quality_metrics": {
    "overall_quality": 0.85,
    "affected_regions": ["southwest"],
    "duration_minutes": 15
  }
}
```

## SDK and Libraries

### Official SDKs
- **Python**: `pip install weather-intelligence-sdk`
- **Node.js**: `npm install @weather-intelligence/sdk`
- **C#**: `Install-Package WeatherIntelligence.SDK`

### Community Libraries
- **R**: `weather.intelligence` package
- **Java**: `weather-intelligence-java`
- **Go**: `github.com/weather-intelligence/go-sdk`

For additional information, see [Integration Guide](integration.md) and [SDK Documentation](sdk.md).