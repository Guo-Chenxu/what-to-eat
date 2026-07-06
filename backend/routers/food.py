from __future__ import annotations

import math

import aiosqlite
from fastapi import APIRouter, HTTPException, Query, status

from backend.database import get_db
from backend.models import FoodOptionCreate, FoodOptionResponse, FoodOptionUpdate, FoodPageResponse

router = APIRouter(prefix="/api/food", tags=["food"])


def _clamp_page(page: int) -> int:
    return max(page, 1)


def _clamp_page_size(page_size: int, max_size: int = 100) -> int:
    return min(max(page_size, 1), max_size)


def _food_from_row(row: aiosqlite.Row) -> FoodOptionResponse:
    return FoodOptionResponse(
        id=row["id"],
        name=row["name"],
        type=row["type"],
        characteristics=row["characteristics"],
        service_type=row["service_type"],
        avg_price=row["avg_price"],
        create_time=row["create_time"],
        update_time=row["update_time"],
    )


async def _fetch_food(food_id: int) -> FoodOptionResponse | None:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM food_options WHERE id = ? AND deleted = 0", (food_id,))
        row = await cursor.fetchone()
    return _food_from_row(row) if row else None


@router.get("", response_model=FoodPageResponse)
async def list_foods(
    page: int = Query(default=1),
    page_size: int = Query(default=15),
) -> FoodPageResponse:
    page = _clamp_page(page)
    page_size = _clamp_page_size(page_size)
    offset = (page - 1) * page_size
    async with get_db() as db:
        total_cursor = await db.execute("SELECT COUNT(*) FROM food_options WHERE deleted = 0")
        total = (await total_cursor.fetchone())[0]
        cursor = await db.execute(
            """
            SELECT * FROM food_options
            WHERE deleted = 0
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        )
        rows = await cursor.fetchall()
    total_pages = math.ceil(total / page_size) if total else 0
    return FoodPageResponse(
        items=[_food_from_row(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=FoodOptionResponse, status_code=status.HTTP_201_CREATED)
async def create_food(payload: FoodOptionCreate) -> FoodOptionResponse:
    try:
        async with get_db() as db:
            cursor = await db.execute(
                """
                INSERT INTO food_options (name, type, characteristics, service_type, avg_price)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload.name.strip(),
                    payload.type.strip(),
                    payload.characteristics.strip(),
                    payload.service_type,
                    payload.avg_price,
                ),
            )
            await db.commit()
            food_id = cursor.lastrowid
    except aiosqlite.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="食物名称已存在") from exc

    food = await _fetch_food(food_id)
    if not food:
        raise HTTPException(status_code=500, detail="创建后读取食物失败")
    return food


@router.put("/{food_id}", response_model=FoodOptionResponse)
async def update_food(food_id: int, payload: FoodOptionUpdate) -> FoodOptionResponse:
    existing = await _fetch_food(food_id)
    if not existing:
        raise HTTPException(status_code=404, detail="食物不存在")

    data = payload.model_dump(exclude_unset=True)
    updated = {
        "name": data.get("name", existing.name),
        "type": data.get("type", existing.type),
        "characteristics": data.get("characteristics", existing.characteristics),
        "service_type": data.get("service_type", existing.service_type),
        "avg_price": data.get("avg_price", existing.avg_price),
    }
    for key in ("name", "type", "characteristics"):
        if isinstance(updated[key], str):
            updated[key] = updated[key].strip()

    try:
        async with get_db() as db:
            await db.execute(
                """
                UPDATE food_options
                SET name = ?, type = ?, characteristics = ?, service_type = ?, avg_price = ?,
                    update_time = CURRENT_TIMESTAMP
                WHERE id = ? AND deleted = 0
                """,
                (
                    updated["name"],
                    updated["type"],
                    updated["characteristics"],
                    updated["service_type"],
                    updated["avg_price"],
                    food_id,
                ),
            )
            await db.commit()
    except aiosqlite.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="食物名称已存在") from exc

    refreshed = await _fetch_food(food_id)
    if not refreshed:
        raise HTTPException(status_code=404, detail="食物不存在")
    return refreshed


@router.delete("/{food_id}")
async def delete_food(food_id: int) -> dict[str, str]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            UPDATE food_options
            SET deleted = 1, update_time = CURRENT_TIMESTAMP
            WHERE id = ? AND deleted = 0
            """,
            (food_id,),
        )
        await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="食物不存在")
    return {"message": "删除成功"}
