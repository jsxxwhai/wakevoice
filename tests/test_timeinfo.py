"""Tests for offline time/date skills (deterministic via injected `now`)."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from assistant.skills import system as system_skill
from assistant.skills import timeinfo as time_skill
from assistant.skills.base import SkillRegistry


def _reg(now=None):
    reg = SkillRegistry()
    system_skill.register_system_skills(reg)
    time_skill.register_time_skills(reg, now=now)
    return reg


def test_tell_time_routes_and_answers():
    now = datetime(2026, 9, 3, 15, 24)
    reg = _reg(now)
    skill, params = reg.route("现在几点")
    assert skill is not None and skill.name == "tell_time"
    assert skill.handler(params, None) == "现在是下午3点24分"


def test_tell_time_variants():
    reg = _reg(datetime(2026, 9, 3, 9, 5))
    for text in ["几点了", "现在几点钟", "请问现在几点", "几点了呀"]:
        skill, _ = reg.route(text)
        assert skill is not None, f"no match: {text}"
        assert skill.name == "tell_time", f"{text} -> {skill.name}"
    skill, _ = reg.route("现在几点")
    assert skill.handler({}, None) == "现在是上午9点5分"


def test_tell_time_whole_hour():
    reg = _reg(datetime(2026, 9, 3, 8, 0))
    skill, _ = reg.route("现在几点")
    assert skill.handler({}, None) == "现在是早上8点整"


def test_tell_time_midnight_and_noon():
    reg = _reg(datetime(2026, 9, 3, 0, 5))
    skill, _ = reg.route("现在几点")
    assert skill.handler({}, None) == "现在是凌晨12点5分"
    reg2 = _reg(datetime(2026, 9, 3, 12, 30))
    skill2, _ = reg2.route("现在几点")
    assert skill2.handler({}, None) == "现在是中午12点30分"


def test_tell_date_routes_and_answers():
    now = datetime(2026, 9, 3, 10, 0)  # 2026-09-03 is a Thursday
    reg = _reg(now)
    for text in ["今天星期几", "星期几", "今天几号", "请问今天日期"]:
        skill, _ = reg.route(text)
        assert skill is not None, f"no match: {text}"
        assert skill.name == "tell_date", f"{text} -> {skill.name}"
    skill, params = reg.route("今天星期几")
    assert skill.handler(params, None) == "今天是2026年9月3日，星期四"


def test_time_skills_do_not_hijack_commands():
    """输入/打开 commands must never route to time/date skills."""
    reg = _reg(datetime(2026, 9, 3, 10, 0))
    for text in ["输入时间", "打开记事本", "写入时间计划"]:
        hit = reg.route(text)
        assert hit is None or hit[0].name not in ("tell_time", "tell_date"), text
