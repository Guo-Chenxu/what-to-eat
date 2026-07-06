from datetime import datetime

from backend.database import get_time_slot
from backend.routers.stats import bucket_price, build_price_stats
from backend.services.llm import parse_recommendation


def test_parse_recommendation_uses_last_matching_line():
    text = "推荐：旧菜、旧饭\n分析内容\n推荐：兰州拉面、黄焖鸡"
    assert parse_recommendation(text) == ("兰州拉面", "黄焖鸡")


def test_parse_recommendation_returns_question_marks_when_missing():
    assert parse_recommendation("今天随便吃点吧") == ("?", "?")


def test_get_time_slot_boundaries():
    assert get_time_slot(datetime(2026, 7, 6, 13, 59)) == (1, "午餐")
    assert get_time_slot(datetime(2026, 7, 6, 14, 0)) == (2, "晚餐")
    assert get_time_slot(datetime(2026, 7, 6, 19, 0)) == (3, "夜宵")


def test_bucket_price_boundaries():
    assert bucket_price(24) == "<25"
    assert bucket_price(25) == "25-34"
    assert bucket_price(34) == "25-34"
    assert bucket_price(35) == "35-44"
    assert bucket_price(44) == "35-44"
    assert bucket_price(45) == "45-54"
    assert bucket_price(54) == "45-54"
    assert bucket_price(55) == "≥55"


def test_build_price_stats_uses_floor_average_and_fixed_buckets():
    stats = build_price_stats([24, 25, 35, 45, 55, 56])
    assert stats.avg_price == 40
    assert [item.range for item in stats.distribution] == ["<25", "25-34", "35-44", "45-54", "≥55"]
    assert [item.count for item in stats.distribution] == [1, 1, 1, 1, 2]
