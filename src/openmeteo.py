# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Open-Meteo tools.

Open-Meteo is a public API, so these tools call the upstream endpoints directly
instead of modeling a fake credentialed connection.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations
import httpx
from pydantic.dataclasses import dataclass


FORECAST_API_BASE_URL = "https://api.open-meteo.com/v1"
GEOCODING_API_BASE_URL = "https://geocoding-api.open-meteo.com/v1"
DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class OpenMeteoResult:
    """Standardized Open-Meteo response."""

    success: bool
    data: Any = None
    error: str | None = None


def _csv(values: Sequence[str] | None) -> str | None:
    """Join non-empty values into a stable comma-separated list."""
    if not values:
        return None
    cleaned = [value.strip() for value in values if value.strip()]
    if not cleaned:
        return None
    return ",".join(dict.fromkeys(cleaned))


async def _get_json(base_url: str, path: str, params: dict[str, Any]) -> OpenMeteoResult:
    """Execute a GET request and normalize Open-Meteo error payloads."""
    query = {key: value for key, value in params.items() if value is not None}

    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.get(path, params=query)
    except httpx.HTTPError as exc:
        return OpenMeteoResult(success=False, error=str(exc))

    try:
        payload = response.json()
    except ValueError:
        if response.status_code < 400:
            return OpenMeteoResult(success=False, error="Upstream returned a non-JSON response")
        payload = response.text

    if isinstance(payload, dict) and payload.get("error") is True:
        reason = payload.get("reason")
        return OpenMeteoResult(success=False, error=str(reason or "Request failed"))

    if response.status_code >= 400:
        if isinstance(payload, dict):
            reason = payload.get("reason") or payload.get("error")
            return OpenMeteoResult(success=False, error=str(reason or f"HTTP {response.status_code}"))
        return OpenMeteoResult(success=False, error=f"HTTP {response.status_code}: {payload}")

    return OpenMeteoResult(success=True, data=payload)


@tool(
    description="Search locations with the Open-Meteo geocoding API",
    tags=["locations", "read"],
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def openmeteo_search_locations(
    name: str, count: int = 5, language: str = "en", country_code: str | None = None
) -> OpenMeteoResult:
    """Search places by name or postal code."""
    result = await _get_json(
        GEOCODING_API_BASE_URL,
        "/search",
        {
            "name": name,
            "count": count,
            "language": language,
            "countryCode": country_code.upper() if country_code else None,
        },
    )
    if not result.success:
        return result

    payload = result.data if isinstance(result.data, dict) else {}
    rows = payload.get("results") or []
    return OpenMeteoResult(
        success=True,
        data=[
            {
                "name": row.get("name"),
                "country": row.get("country"),
                "admin1": row.get("admin1"),
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
                "timezone": row.get("timezone"),
                "elevation": row.get("elevation"),
                "population": row.get("population"),
            }
            for row in rows
        ],
    )


@tool(
    description="Get forecast data from Open-Meteo for specific coordinates",
    tags=["forecast", "read"],
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def openmeteo_get_forecast(
    latitude: float,
    longitude: float,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    current: list[str] | None = None,
    timezone: str | None = None,
    forecast_days: int | None = None,
    past_days: int | None = None,
    models: list[str] | None = None,
    temperature_unit: str | None = None,
    wind_speed_unit: str | None = None,
    precipitation_unit: str | None = None,
) -> OpenMeteoResult:
    """Get weather forecast data for coordinates."""
    resolved_timezone = timezone or "auto"
    return await _get_json(
        FORECAST_API_BASE_URL,
        "/forecast",
        {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": _csv(hourly),
            "daily": _csv(daily),
            "current": _csv(current),
            "timezone": resolved_timezone,
            "forecast_days": forecast_days,
            "past_days": past_days,
            "models": _csv(models),
            "temperature_unit": temperature_unit,
            "wind_speed_unit": wind_speed_unit,
            "precipitation_unit": precipitation_unit,
        },
    )


@tool(
    description="Search a location by name, then fetch its Open-Meteo forecast",
    tags=["forecast", "locations", "read"],
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def openmeteo_get_forecast_for_location(
    location: str,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    current: list[str] | None = None,
    timezone: str | None = None,
    forecast_days: int | None = None,
    past_days: int | None = None,
    models: list[str] | None = None,
    temperature_unit: str | None = None,
    wind_speed_unit: str | None = None,
    precipitation_unit: str | None = None,
    language: str = "en",
    country_code: str | None = None,
    allow_ambiguous: bool = False,
) -> OpenMeteoResult:
    """Resolve a place name to coordinates, then fetch its forecast."""
    location_result = await openmeteo_search_locations(
        name=location, count=5, language=language, country_code=country_code
    )
    if not location_result.success:
        return location_result

    matches = location_result.data if isinstance(location_result.data, list) else []
    if not matches:
        return OpenMeteoResult(success=False, error=f"No matching location found for '{location}'")
    if len(matches) > 1 and not allow_ambiguous:
        return OpenMeteoResult(
            success=False,
            data=matches,
            error=(
                f"Multiple matching locations found for '{location}'. "
                "Refine the query or pass country_code, or set allow_ambiguous=True."
            ),
        )

    match = matches[0]
    forecast_result = await openmeteo_get_forecast(
        latitude=float(match["latitude"]),
        longitude=float(match["longitude"]),
        hourly=hourly,
        daily=daily,
        current=current,
        timezone=timezone or match.get("timezone"),
        forecast_days=forecast_days,
        past_days=past_days,
        models=models,
        temperature_unit=temperature_unit,
        wind_speed_unit=wind_speed_unit,
        precipitation_unit=precipitation_unit,
    )
    if not forecast_result.success:
        return forecast_result

    return OpenMeteoResult(success=True, data={"location": match, "forecast": forecast_result.data})


openmeteo_tools = [openmeteo_search_locations, openmeteo_get_forecast, openmeteo_get_forecast_for_location]
