# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

from __future__ import annotations

import pytest

import openmeteo
from openmeteo import OpenMeteoResult


@pytest.mark.asyncio
async def test_get_forecast_defaults_timezone_to_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_get_json(base_url: str, path: str, params: dict[str, object]) -> OpenMeteoResult:
        captured["base_url"] = base_url
        captured["path"] = path
        captured["params"] = params
        return OpenMeteoResult(success=True, data={"ok": True})

    monkeypatch.setattr(openmeteo, "_get_json", fake_get_json)

    result = await openmeteo.openmeteo_get_forecast(latitude=52.52, longitude=13.41)

    assert result.success is True
    assert captured["base_url"] == openmeteo.FORECAST_API_BASE_URL
    assert captured["path"] == "/forecast"
    assert captured["params"]["timezone"] == "auto"


@pytest.mark.asyncio
async def test_forecast_for_location_rejects_ambiguous_results(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search_locations(**_: object) -> OpenMeteoResult:
        return OpenMeteoResult(
            success=True,
            data=[
                {"name": "Springfield", "latitude": 39.8, "longitude": -89.64, "timezone": "America/Chicago"},
                {"name": "Springfield", "latitude": 44.05, "longitude": -123.02, "timezone": "America/Los_Angeles"},
            ],
        )

    monkeypatch.setattr(openmeteo, "openmeteo_search_locations", fake_search_locations)

    result = await openmeteo.openmeteo_get_forecast_for_location(location="Springfield")

    assert result.success is False
    assert "Multiple matching locations" in (result.error or "")
    assert isinstance(result.data, list)
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_forecast_for_location_uses_first_match_when_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search_locations(**_: object) -> OpenMeteoResult:
        return OpenMeteoResult(
            success=True,
            data=[
                {"name": "Berlin", "latitude": 52.52437, "longitude": 13.41053, "timezone": "Europe/Berlin"},
                {"name": "Berlin", "latitude": 44.47, "longitude": -71.18, "timezone": "America/New_York"},
            ],
        )

    async def fake_get_forecast(**kwargs: object) -> OpenMeteoResult:
        return OpenMeteoResult(success=True, data=kwargs)

    monkeypatch.setattr(openmeteo, "openmeteo_search_locations", fake_search_locations)
    monkeypatch.setattr(openmeteo, "openmeteo_get_forecast", fake_get_forecast)

    result = await openmeteo.openmeteo_get_forecast_for_location(
        location="Berlin", allow_ambiguous=True, current=["temperature_2m"]
    )

    assert result.success is True
    assert result.data["location"]["timezone"] == "Europe/Berlin"
    assert result.data["forecast"]["timezone"] == "Europe/Berlin"


@pytest.mark.asyncio
async def test_get_json_rejects_non_json_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        status_code = 200
        text = "<html>oops</html>"

        def json(self) -> object:
            raise ValueError("not json")

    class FakeClient:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def get(self, path: str, params: dict[str, object]) -> FakeResponse:
            assert path == "/search"
            assert params["name"] == "Berlin"
            return FakeResponse()

    monkeypatch.setattr(openmeteo.httpx, "AsyncClient", FakeClient)

    result = await openmeteo._get_json(openmeteo.GEOCODING_API_BASE_URL, "/search", {"name": "Berlin"})

    assert result.success is False
    assert result.error == "Upstream returned a non-JSON response"
