from __future__ import annotations

from fastapi import APIRouter

from backend.database import get_db
from backend.models import ChoiceStatItem, PriceDistItem, PriceStatsResponse

router = APIRouter(prefix="/api/stats", tags=["stats"])

PRICE_BUCKETS: list[tuple[str, int | None, int | None]] = [
    ("<25", None, 24),
    ("25-34", 25, 34),
    ("35-44", 35, 44),
    ("45-54", 45, 54),
    ("≥55", 55, None),
]


def bucket_price(price: int) -> str:
    for label, lower, upper in PRICE_BUCKETS:
        if lower is None and price <= upper:
            return label
        if upper is None and price >= lower:
            return label
        if lower is not None and upper is not None and lower <= price <= upper:
            return label
    return "≥55"


def build_price_stats(prices: list[int]) -> PriceStatsResponse:
    distribution = {label: 0 for label, _, _ in PRICE_BUCKETS}
    if not prices:
        return PriceStatsResponse(
            avg_price=0,
            distribution=[PriceDistItem(range=label, count=0) for label in distribution],
        )

    for price in prices:
        distribution[bucket_price(price)] += 1
    avg_price = sum(prices) // len(prices)
    return PriceStatsResponse(
        avg_price=avg_price,
        distribution=[PriceDistItem(range=label, count=distribution[label]) for label in distribution],
    )


@router.get("/choices", response_model=list[ChoiceStatItem])
async def choice_stats() -> list[ChoiceStatItem]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT final_choice AS name, COUNT(*) AS count
            FROM selections
            WHERE deleted = 0 AND final_choice IS NOT NULL AND final_choice != ''
            GROUP BY final_choice
            ORDER BY count DESC
            """
        )
        rows = await cursor.fetchall()
    return [ChoiceStatItem(name=row["name"], count=row["count"]) for row in rows]


@router.get("/price", response_model=PriceStatsResponse)
async def price_stats() -> PriceStatsResponse:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT fo.avg_price AS avg_price
            FROM selections s
            JOIN food_options fo ON fo.name = s.final_choice
            WHERE s.deleted = 0
              AND fo.deleted = 0
              AND s.final_choice IS NOT NULL
              AND s.final_choice != ''
            """
        )
        rows = await cursor.fetchall()
    return build_price_stats([row["avg_price"] for row in rows])
