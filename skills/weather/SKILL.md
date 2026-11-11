---
name: weather
version: 1.0.0
description: Real-time weather forecasts, current conditions, humidity, and wind speed using the free Open-Meteo API.
author: jarvis-ecosystem
license: MIT
allowed_tools: [web_search, execute_command]
tags: [weather, forecast, open-meteo, environment]
---

# Weather Forecasting & Conditions Skill

This skill allows JARVIS to retrieve live weather data, temperature, humidity, wind conditions, and weather forecasts for any city worldwide using the free, keyless **Open-Meteo** API.

## API Endpoint Reference

- **Geocoding API** (resolve city to latitude/longitude):
  `https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json`
- **Forecast & Current Conditions**:
  `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,is_day,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto`

## UI Event Emission

When the user asks for weather or current meteorological conditions, fetch the data and emit a `show-weather` window event for the JARVIS Weather Widget:

```json
{
  "city": "London",
  "country": "United Kingdom",
  "temperature": 18.5,
  "humidity": 65,
  "windSpeed": 14.2,
  "isDay": true,
  "condition": "Clear"
}
```

### Weather Codes Mapping
- `0`: Clear
- `1, 2, 3`: Cloudy
- `45, 48`: Haze / Fog
- `51, 53, 55, 61, 63, 65, 80, 81, 82`: Rain
- `71, 73, 75, 77, 85, 86`: Snow
- `95, 96, 99`: Thunderstorm
