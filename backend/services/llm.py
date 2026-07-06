from __future__ import annotations

import os
import re
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from backend.config import settings

_api_key = settings.llm.api_key
if isinstance(_api_key, str) and _api_key.startswith("${") and _api_key.endswith("}"):
    _api_key = os.getenv(_api_key[2:-1], "")

client = AsyncOpenAI(base_url=settings.llm.base_url, api_key=_api_key or "EMPTY")


def build_prompt(
    weather: str,
    history: list[dict[str, Any]],
    food_options: list[dict[str, Any]],
    current_date: str,
    slot_name: str,
    today_preference: str | None = None,
) -> str:
    history_text = "\n".join(
        f"- {item.get('date', '')} {item.get('slot_name', '')}: {item.get('final_choice', '')}"
        for item in history
        if item.get("final_choice")
    ) or "近7天暂无已确认饮食记录。"

    food_text = "\n".join(
        "- {name}（{type}，{characteristics}，{service_type}，人均¥{avg_price}）".format(
            name=item.get("name", ""),
            type=item.get("type", ""),
            characteristics=item.get("characteristics", ""),
            service_type=item.get("service_type", ""),
            avg_price=item.get("avg_price", ""),
        )
        for item in food_options
    ) or "暂无可选食物。"

    preference_text = ""
    if today_preference:
        preference_text = f"\n今日偏好：{today_preference}（可参考，不必强求，综合考虑即可）"

    return f"""你是一位懂天气、习惯和预算的美食推荐助手。请根据以下信息，为用户推荐今天适合吃的东西。

当前天气：{weather}
日期时段：{current_date} {slot_name}{preference_text}

近7天已确认饮食历史：
{history_text}

可选食物列表：
{food_text}

要求：
1. 综合天气、时段、近期是否重复、今日偏好、获取方式和人均价格，先给出自然、简洁、有帮助的推荐理由。
2. 最终只从可选食物列表中选出 2 个候选食物，尽量避免刚吃过的重复选择。
3. 如果食物库为空，请说明需要先添加食物，并在最后仍按格式输出问号占位。
4. 最后一行必须严格使用格式：推荐：{{食物名称1}}、{{食物名称2}}
"""


def parse_recommendation(full_text: str) -> tuple[str, str]:
    pattern = re.compile(r"推荐[：:]\s*(.+?)\s*[、,，]\s*(.+?)\s*$", re.MULTILINE)
    matches = pattern.findall(full_text)
    if not matches:
        return "?", "?"
    first, second = matches[-1]
    return first.strip(), second.strip()


async def stream_food_recommendation(
    weather: str,
    history: list[dict[str, Any]],
    food_options: list[dict[str, Any]],
    current_date: str,
    slot_name: str,
    today_preference: str | None = None,
) -> AsyncIterator[str]:
    prompt = build_prompt(
        weather=weather,
        history=history,
        food_options=food_options,
        current_date=current_date,
        slot_name=slot_name,
        today_preference=today_preference,
    )
    stream = await client.chat.completions.create(
        model=settings.llm.model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        stream=True,
    )
    async for chunk in stream:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        content = getattr(delta, "content", None)
        if content:
            yield content
