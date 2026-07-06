from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SLOT_NAMES = {1: "午餐", 2: "晚餐", 3: "夜宵"}
ServiceType = Literal["外卖", "到店<100m", "到店<500m", "到店<1km", "到店<2km"]


class FoodOptionCreate(BaseModel):
    name: str
    type: str
    characteristics: str
    service_type: ServiceType
    avg_price: int = Field(gt=0)


class FoodOptionUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    characteristics: str | None = None
    service_type: ServiceType | None = None
    avg_price: int | None = Field(default=None, gt=0)


class FoodOptionResponse(BaseModel):
    id: int
    name: str
    type: str
    characteristics: str
    service_type: str
    avg_price: int
    create_time: str
    update_time: str


class SelectionResponse(BaseModel):
    id: int
    date: str
    time_slot: int
    slot_name: str
    food_1: str
    food_2: str
    reasoning: str | None
    weather: str | None
    location: str | None
    final_choice: str | None
    today_preference: str | None
    create_time: str


class SelectRequest(BaseModel):
    today_preference: str | None = None


class ChoiceUpdate(BaseModel):
    final_choice: str


class HistoryPageResponse(BaseModel):
    items: list[SelectionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class FoodPageResponse(BaseModel):
    items: list[FoodOptionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ChoiceStatItem(BaseModel):
    name: str
    count: int


class PriceDistItem(BaseModel):
    range: str
    count: int


class PriceStatsResponse(BaseModel):
    avg_price: int
    distribution: list[PriceDistItem]


class WeatherResponse(BaseModel):
    temp: str
    description: str
    city: str
    location: str
