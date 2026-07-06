from __future__ import annotations

import asyncio
from typing import Any

import httpx

from backend.config import settings
from backend.models import WeatherResponse

WTTR_URL = "https://zh.wttr.in/{query}"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "what-to-eat/1.0 (personal meal recommendation app)"


def _fallback_weather() -> WeatherResponse:
    city = settings.weather.city
    return WeatherResponse(temp="--", description="无法获取天气", city=city, location=city)


def _extract_weather(payload: dict[str, Any], fallback_city: str) -> tuple[str, str, str]:
    current = (payload.get("current_condition") or [{}])[0]
    temp = current.get("temp_C") or current.get("FeelsLikeC") or "--"
    descriptions = current.get("lang_zh-cn") or current.get("weatherDesc") or [{}]
    description = descriptions[0].get("value") if descriptions else None
    nearest = payload.get("nearest_area") or [{}]
    area = nearest[0] if nearest else {}
    names = area.get("areaName") or [{}]
    city = names[0].get("value") if names else None
    return f"{temp}°C", description or "天气未知", city or fallback_city


async def _fetch_weather(client: httpx.AsyncClient, query: str) -> tuple[str, str, str]:
    response = await client.get(
        WTTR_URL.format(query=query),
        params={"format": "j1", "lang": settings.weather.language},
    )
    response.raise_for_status()
    return _extract_weather(response.json(), settings.weather.city)


async def _fetch_location(client: httpx.AsyncClient, lat: float, lon: float) -> tuple[str, str]:
    response = await client.get(
        NOMINATIM_URL,
        params={
            "format": "jsonv2",
            "lat": lat,
            "lon": lon,
            "accept-language": "zh-CN",
        },
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    payload = response.json()
    address = payload.get("address") or {}
    city = (
        address.get("city")
        or address.get("town")
        or address.get("county")
        or address.get("suburb")
        or settings.weather.city
    )
    location = payload.get("display_name") or city
    return city, location


async def get_weather(lat: float | None = None, lon: float | None = None) -> WeatherResponse:
    try:
        timeout = httpx.Timeout(6.0, connect=3.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            if lat is not None and lon is not None:
                weather_task = _fetch_weather(client, f"{lat},{lon}")
                location_task = _fetch_location(client, lat, lon)
                (temp, description, weather_city), (geo_city, location) = await asyncio.gather(
                    weather_task,
                    location_task,
                )
                return WeatherResponse(
                    temp=temp,
                    description=description,
                    city=geo_city or weather_city,
                    location=location or geo_city or weather_city,
                )

            temp, description, city = await _fetch_weather(client, settings.weather.city)
            return WeatherResponse(temp=temp, description=description, city=city, location=city)
    except Exception:
        return _fallback_weather()
