from __future__ import annotations

from fastapi import APIRouter, Query

from backend.models import WeatherResponse
from backend.services.weather import get_weather

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("", response_model=WeatherResponse)
async def weather(
    lat: float | None = Query(default=None),
    lon: float | None = Query(default=None),
) -> WeatherResponse:
    return await get_weather(lat=lat, lon=lon)
