from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

import aiosqlite

from backend.config import settings

ROOT_DIR = Path(__file__).parent.parent
DB_PATH = ROOT_DIR / settings.database.path

FOOD_SCHEMA = """
CREATE TABLE IF NOT EXISTS food_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    characteristics TEXT NOT NULL,
    service_type TEXT NOT NULL DEFAULT '到店<500m',
    avg_price INTEGER NOT NULL DEFAULT 30,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted INTEGER NOT NULL DEFAULT 0
)
"""

SELECTION_SCHEMA = """
CREATE TABLE IF NOT EXISTS selections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time_slot INTEGER NOT NULL,
    food_1 TEXT NOT NULL,
    food_2 TEXT NOT NULL,
    reasoning TEXT,
    weather TEXT,
    location TEXT,
    final_choice TEXT,
    today_preference TEXT,
    create_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted INTEGER NOT NULL DEFAULT 0,
    UNIQUE(date, time_slot)
)
"""

FOOD_ALTERS = [
    "ALTER TABLE food_options ADD COLUMN service_type TEXT NOT NULL DEFAULT '到店<500m'",
    "ALTER TABLE food_options ADD COLUMN avg_price INTEGER NOT NULL DEFAULT 30",
    "ALTER TABLE food_options ADD COLUMN update_time TEXT",
    "ALTER TABLE food_options ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0",
]

SELECTION_ALTERS = [
    "ALTER TABLE selections ADD COLUMN today_preference TEXT",
    "ALTER TABLE selections ADD COLUMN update_time TEXT",
    "ALTER TABLE selections ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0",
]


def get_time_slot(now: datetime | None = None) -> tuple[int, str]:
    current = now or datetime.now()
    if current.hour < 14:
        return 1, "午餐"
    if current.hour < 19:
        return 2, "晚餐"
    return 3, "夜宵"


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(FOOD_SCHEMA)
        await db.execute(SELECTION_SCHEMA)
        await _run_alters(db, FOOD_ALTERS)
        await _run_alters(db, SELECTION_ALTERS)
        if not await _has_good_update_time(db, "food_options"):
            await _rebuild_food_options(db)
        if not await _has_good_update_time(db, "selections"):
            await _rebuild_selections(db)
        await db.commit()


async def _run_alters(db: aiosqlite.Connection, statements: list[str]) -> None:
    for statement in statements:
        try:
            await db.execute(statement)
        except aiosqlite.OperationalError:
            pass


async def _table_columns(db: aiosqlite.Connection, table: str) -> dict[str, dict[str, object]]:
    cursor = await db.execute(f"PRAGMA table_info({table})")
    rows = await cursor.fetchall()
    return {row[1]: {"notnull": row[3], "default": row[4]} for row in rows}


async def _has_good_update_time(db: aiosqlite.Connection, table: str) -> bool:
    columns = await _table_columns(db, table)
    update_time = columns.get("update_time")
    if not update_time:
        return False
    default = str(update_time.get("default") or "").upper()
    return bool(update_time.get("notnull")) and default == "CURRENT_TIMESTAMP"


def _expr(columns: dict[str, dict[str, object]], column: str, default: str) -> str:
    return column if column in columns else default


async def _rebuild_food_options(db: aiosqlite.Connection) -> None:
    columns = await _table_columns(db, "food_options")
    await db.execute("DROP TABLE IF EXISTS food_options_new")
    await db.execute(FOOD_SCHEMA.replace("food_options", "food_options_new", 1))
    select_sql = f"""
        INSERT OR IGNORE INTO food_options_new
            (id, name, type, characteristics, service_type, avg_price, create_time, update_time, deleted)
        SELECT
            {_expr(columns, 'id', 'NULL')},
            {_expr(columns, 'name', "''")},
            {_expr(columns, 'type', "''")},
            {_expr(columns, 'characteristics', "''")},
            COALESCE({_expr(columns, 'service_type', "'到店<500m'")}, '到店<500m'),
            COALESCE({_expr(columns, 'avg_price', '30')}, 30),
            COALESCE({_expr(columns, 'create_time', 'CURRENT_TIMESTAMP')}, CURRENT_TIMESTAMP),
            COALESCE({_expr(columns, 'update_time', 'CURRENT_TIMESTAMP')}, CURRENT_TIMESTAMP),
            COALESCE({_expr(columns, 'deleted', '0')}, 0)
        FROM food_options
    """
    await db.execute(select_sql)
    await db.execute("DROP TABLE food_options")
    await db.execute("ALTER TABLE food_options_new RENAME TO food_options")


async def _rebuild_selections(db: aiosqlite.Connection) -> None:
    columns = await _table_columns(db, "selections")
    await db.execute("DROP TABLE IF EXISTS selections_new")
    await db.execute(SELECTION_SCHEMA.replace("selections", "selections_new", 1))
    select_sql = f"""
        INSERT OR IGNORE INTO selections_new
            (id, date, time_slot, food_1, food_2, reasoning, weather, location,
             final_choice, today_preference, create_time, update_time, deleted)
        SELECT
            {_expr(columns, 'id', 'NULL')},
            {_expr(columns, 'date', "date('now')")},
            {_expr(columns, 'time_slot', '1')},
            {_expr(columns, 'food_1', "''")},
            {_expr(columns, 'food_2', "''")},
            {_expr(columns, 'reasoning', 'NULL')},
            {_expr(columns, 'weather', 'NULL')},
            {_expr(columns, 'location', 'NULL')},
            {_expr(columns, 'final_choice', 'NULL')},
            {_expr(columns, 'today_preference', 'NULL')},
            COALESCE({_expr(columns, 'create_time', 'CURRENT_TIMESTAMP')}, CURRENT_TIMESTAMP),
            COALESCE({_expr(columns, 'update_time', 'CURRENT_TIMESTAMP')}, CURRENT_TIMESTAMP),
            COALESCE({_expr(columns, 'deleted', '0')}, 0)
        FROM selections
    """
    await db.execute(select_sql)
    await db.execute("DROP TABLE selections")
    await db.execute("ALTER TABLE selections_new RENAME TO selections")
