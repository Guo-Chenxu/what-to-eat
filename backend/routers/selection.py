from __future__ import annotations

import json
import math
from datetime import date, timedelta
from typing import Any, AsyncIterator

import aiosqlite
from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.database import get_db, get_time_slot
from backend.models import ChoiceUpdate, HistoryPageResponse, SelectRequest, SelectionResponse, SLOT_NAMES
from backend.services.llm import parse_recommendation, stream_food_recommendation
from backend.services.weather import get_weather

router = APIRouter(tags=["selection"])


def _row_dict(row: aiosqlite.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _selection_from_row(row: aiosqlite.Row) -> SelectionResponse:
    return SelectionResponse(
        id=row["id"],
        date=row["date"],
        time_slot=row["time_slot"],
        slot_name=SLOT_NAMES.get(row["time_slot"], "未知"),
        food_1=row["food_1"],
        food_2=row["food_2"],
        reasoning=row["reasoning"],
        weather=row["weather"],
        location=row["location"],
        final_choice=row["final_choice"],
        today_preference=row["today_preference"],
        create_time=row["create_time"],
    )


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _load_recent_history(current_date: str, time_slot: int) -> list[dict[str, Any]]:
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT * FROM selections
            WHERE deleted = 0
              AND date >= ?
              AND final_choice IS NOT NULL
              AND final_choice != ''
              AND NOT (date = ? AND time_slot = ?)
            ORDER BY create_time DESC
            """,
            (cutoff, current_date, time_slot),
        )
        rows = await cursor.fetchall()
    history: list[dict[str, Any]] = []
    for row in rows:
        item = _row_dict(row)
        item["slot_name"] = SLOT_NAMES.get(row["time_slot"], "未知")
        history.append(item)
    return history


async def _load_food_options() -> list[dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, name, type, characteristics, service_type, avg_price
            FROM food_options
            WHERE deleted = 0
            ORDER BY id ASC
            """
        )
        rows = await cursor.fetchall()
    return [_row_dict(row) for row in rows]


async def _save_selection(
    current_date: str,
    time_slot: int,
    food_1: str,
    food_2: str,
    reasoning: str,
    weather: str,
    location: str,
    today_preference: str | None,
) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT OR REPLACE INTO selections
                (date, time_slot, food_1, food_2, reasoning, weather, location,
                 final_choice, today_preference, deleted, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, 0, CURRENT_TIMESTAMP)
            """,
            (
                current_date,
                time_slot,
                food_1,
                food_2,
                reasoning,
                weather,
                location,
                today_preference,
            ),
        )
        await db.commit()
        return int(cursor.lastrowid)


@router.post("/api/select")
async def select_food(
    lat: float | None = Query(default=None),
    lon: float | None = Query(default=None),
    payload: SelectRequest | None = Body(default=None),
) -> StreamingResponse:
    preference = (payload.today_preference if payload else None) or None
    if preference is not None:
        preference = preference.strip() or None

    async def event_generator() -> AsyncIterator[str]:
        current_date = date.today().isoformat()
        time_slot, slot_name = get_time_slot()
        weather_data = await get_weather(lat=lat, lon=lon)
        weather_text = f"{weather_data.description}，{weather_data.temp}"
        location_text = weather_data.location
        history = await _load_recent_history(current_date, time_slot)
        food_options = await _load_food_options()

        full_text = ""
        try:
            async for chunk in stream_food_recommendation(
                weather=weather_text,
                history=history,
                food_options=food_options,
                current_date=current_date,
                slot_name=slot_name,
                today_preference=preference,
            ):
                full_text += chunk
                yield _sse({"content": chunk})
        except Exception as exc:
            yield _sse({"type": "error", "message": f"推荐生成失败：{exc}"})
            return

        food_1, food_2 = parse_recommendation(full_text)
        record_id = await _save_selection(
            current_date=current_date,
            time_slot=time_slot,
            food_1=food_1,
            food_2=food_2,
            reasoning=full_text,
            weather=weather_text,
            location=location_text,
            today_preference=preference,
        )
        yield _sse({"type": "done", "id": record_id, "food_1": food_1, "food_2": food_2})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/api/history", response_model=HistoryPageResponse)
async def list_history(
    page: int = Query(default=1),
    page_size: int = Query(default=10),
) -> HistoryPageResponse:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)
    offset = (page - 1) * page_size
    async with get_db() as db:
        total_cursor = await db.execute("SELECT COUNT(*) FROM selections WHERE deleted = 0")
        total = (await total_cursor.fetchone())[0]
        cursor = await db.execute(
            """
            SELECT * FROM selections
            WHERE deleted = 0
            ORDER BY create_time DESC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        )
        rows = await cursor.fetchall()
    total_pages = math.ceil(total / page_size) if total else 0
    return HistoryPageResponse(
        items=[_selection_from_row(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


async def _fetch_selection(selection_id: int) -> SelectionResponse | None:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM selections WHERE id = ? AND deleted = 0", (selection_id,))
        row = await cursor.fetchone()
    return _selection_from_row(row) if row else None


@router.patch("/api/history/{selection_id}/choice", response_model=SelectionResponse)
async def set_final_choice(selection_id: int, payload: ChoiceUpdate) -> SelectionResponse:
    choice = payload.final_choice.strip()
    async with get_db() as db:
        cursor = await db.execute(
            """
            UPDATE selections
            SET final_choice = ?, update_time = CURRENT_TIMESTAMP
            WHERE id = ? AND deleted = 0
            """,
            (choice, selection_id),
        )
        await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    selection = await _fetch_selection(selection_id)
    if not selection:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return selection


@router.delete("/api/history/{selection_id}")
async def delete_history(selection_id: int) -> dict[str, str]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            UPDATE selections
            SET deleted = 1, update_time = CURRENT_TIMESTAMP
            WHERE id = ? AND deleted = 0
            """,
            (selection_id,),
        )
        await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return {"message": "删除成功"}
