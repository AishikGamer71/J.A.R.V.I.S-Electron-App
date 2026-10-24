---
name: maps
version: 1.0.0
description: Geographic search, interactive map centering, and waypoint routing using OpenStreetMap Nominatim and Leaflet.
author: jarvis-ecosystem
license: MIT
allowed_tools: [web_search, execute_command]
tags: [maps, openstreetmap, nominatim, location, routing, leaflet]
---

# Maps & Geographical Navigation Skill

This skill allows JARVIS to geocode addresses, locate landmarks, calculate point-to-point routes, and project interactive maps inside the JARVIS HUD.

## Data Providers

- **OpenStreetMap Nominatim Geocoding API**:
  `https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1`
- **OSRM Public Routing Engine**:
  `https://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson`

## UI Event Emission

### Single Location (`map-update`):
```json
{
  "lat": 51.5074,
  "lng": -0.1278,
  "name": "London, UK"
}
```

### Route Mode (`map-route`):
```json
{
  "start": [51.5074, -0.1278],
  "end": [51.7520, -1.2577],
  "startName": "London",
  "endName": "Oxford",
  "distance": "89.4 km",
  "duration": "1h 18m",
  "coordinates": [
    [51.5074, -0.1278],
    [51.6000, -0.5000],
    [51.7520, -1.2577]
  ]
}
```
