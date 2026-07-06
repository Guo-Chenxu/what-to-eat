from __future__ import annotations

import uvicorn

from backend.config import settings


def main() -> None:
    uvicorn.run(
        "backend.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
