"""Built-in offline skills: tell the current time and date (no LLM/network).

These make the assistant's most-tested first commands ("现在几点", "今天星期几")
work out of the box with zero configuration, matching the README/quickstart.
Patterns are anchored so a phrase like "输入时间" is never hijacked by the
time skill (the type_text skill owns that utterance). The helpers accept an
optional ``now`` so tests can be deterministic.
"""
from __future__ import annotations

import re
from datetime import datetime

from .base import Skill

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

# Optional question lead-ins + optional 现在/当前/今天 + the actual query word.
# Both are anchored at the start of the utterance (with optional trailing
# particles) so command verbs such as 输入/打开/复制 never route here.
_TIME_PAT = re.compile(
    r"^(?:请问|告诉我|帮我看看|帮我查一下|看一下|看下|那)?\s*"
    r"(?:现在|当前)?\s*(?:几点了|几点钟|几点啦|几点|什么时间|时间)[呀啊呢]?$"
)
_DATE_PAT = re.compile(
    r"^(?:请问|告诉我|帮我看看|帮我查一下|看一下|看下|那)?\s*"
    r"(?:今天|现在|当前)?\s*(?:星期几|周几|礼拜几|几号|什么日子|日期)[呀啊呢]?$"
)


def _period_hour(h: int) -> tuple[str, int]:
    """Map 24h hour to a natural Chinese (period, 12h hour) pair."""
    if 0 <= h < 5:
        return "凌晨", h if h != 0 else 12
    if 5 <= h < 9:
        return "早上", h
    if 9 <= h < 12:
        return "上午", h
    if h == 12:
        return "中午", 12
    if 13 <= h < 18:
        return "下午", h - 12
    if 18 <= h < 24:
        return "晚上", h - 12
    return "中午", 12


def _now_text(now: datetime | None = None) -> str:
    dt = now or datetime.now()
    period, h12 = _period_hour(dt.hour)
    if dt.minute == 0:
        return f"现在是{period}{h12}点整"
    return f"现在是{period}{h12}点{dt.minute}分"


def _date_text(now: datetime | None = None) -> str:
    dt = now or datetime.now()
    weekday = WEEKDAYS[dt.weekday()]
    return f"今天是{dt.year}年{dt.month}月{dt.day}日，{weekday}"


def register_time_skills(registry, now: datetime | None = None):
    def _time(params, ctx):
        return _now_text(now)

    def _date(params, ctx):
        return _date_text(now)

    registry.register(Skill(
        name="tell_time",
        description="现在几点/几点了（当前时间）",
        patterns=[_TIME_PAT],
        keywords=[],
        handler=_time,
    ))
    registry.register(Skill(
        name="tell_date",
        description="今天星期几/日期（今天几号）",
        patterns=[_DATE_PAT],
        keywords=[],
        handler=_date,
    ))
