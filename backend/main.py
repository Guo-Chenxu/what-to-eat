from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import logging

from backend.database import init_db
from backend.routers import food, selection, stats, weather
from backend.config import settings

logger = logging.getLogger("uvicorn")

app = FastAPI(title="今天吃什么", version="1.0.0")


@app.on_event("startup")
async def startup() -> None:
    await init_db()
    logger.info("数据库初始化完成")
    logger.info("服务已启动，监听 %s:%s", settings.app.host, settings.app.port)


app.include_router(food.router)
app.include_router(weather.router)
app.include_router(selection.router)
app.include_router(stats.router)

STATIC_DIR = Path(__file__).parent / "static"
ASSETS_DIR = STATIC_DIR / "assets"
INDEX_FILE = STATIC_DIR / "index.html"

if STATIC_DIR.exists() and any(STATIC_DIR.iterdir()):
    if ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        return FileResponse(INDEX_FILE)

else:

    @app.get("/{full_path:path}", include_in_schema=False)
    async def frontend_not_built(full_path: str) -> JSONResponse:
        return JSONResponse(
            {
                "message": "前端尚未构建。请运行 `make build`，或开发时运行 `cd frontend && npm run dev`。"
            }
        )
