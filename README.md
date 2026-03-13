# OpenMeteo MCP Server

A Dedalus MCP server for the public Open-Meteo weather APIs.

## Features

- Search places with Open-Meteo geocoding
- Fetch forecasts by coordinates
- Fetch forecasts directly by place name
- No upstream API key required for the public API

## Usage

### Run the server

```bash
uv run python src/main.py
```

### Test locally

```bash
uv run python src/client.py
```

## Available Tools

| Tool | Description |
|------|-------------|
| `openmeteo_search_locations` | Search locations by name |
| `openmeteo_get_forecast` | Get forecast data for coordinates |
| `openmeteo_get_forecast_for_location` | Search a location, then fetch its forecast |

## API Reference

- Forecast API: [open-meteo.com/en/docs](https://open-meteo.com/en/docs)
- Geocoding API: [open-meteo.com/en/docs/geocoding-api](https://open-meteo.com/en/docs/geocoding-api)

## License

MIT
