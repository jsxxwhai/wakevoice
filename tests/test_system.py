"""Tests for system skills and hotkey fix (no external side effects)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from assistant.skills import control as control_skill
from assistant.skills import system as system_skill
from assistant.skills.base import SkillRegistry


def _reg():
    reg = SkillRegistry()
    control_skill.register_control_skills(reg)
    system_skill.register_system_skills(reg)
    return reg


def test_press_keys_keeps_plus():
    # The hotkey bug: '+' must survive splitting so ctrl+c reaches hotkey.
    import re
    assert "+" not in re.split(r"[、,，;\s]+", "ctrl+c")
    reg = _reg()
    skill, params = reg.route("按下 ctrl+c")
    assert skill.name == "press_keys"
    assert params.get("keys") == "ctrl+c"


def test_set_volume_pattern():
    reg = _reg()
    skill, params = reg.route("音量调到 80")
    assert skill.name == "set_volume"
    assert params.get("level") == "80"


def test_clipboard_write_pattern():
    reg = _reg()
    skill, params = reg.route("复制 你好世界")
    assert skill.name == "clipboard_write"
    assert params.get("text") == "你好世界"


def test_screenshot_pattern():
    reg = _reg()
    skill, _params = reg.route("帮我截个图")
    assert skill.name == "screenshot"


def test_llm_json_code_fence():
    import json
    raw = "```json\n{\"reply\": \"你好\", \"emotion\": \"happy\"}\n```"
    cleaned = raw.strip().strip("`").replace("json", "", 1).strip()
    data = json.loads(cleaned)
    assert data["emotion"] == "happy"

def test_llm_client_tool_loop_multi_turn():
    """LLMClient.respond_with_tools chains a tool call then a final answer."""
    from assistant.core.llm import LLMClient

    class SeqClient(LLMClient):
        def __init__(self):
            super().__init__()
            self._seq = [
                '{"action": "call_tool", "tool": "open_app", "args": "notepad"}',
                '{"reply": "已打开记事本", "emotion": "happy"}',
            ]

        def chat(self, messages, json_mode=False):
            return self._seq.pop(0)

    seen = []
    client = SeqClient()
    reply, emotion = client.respond_with_tools(
        "打开记事本",
        tools=[{"name": "open_app", "description": "打开软件"}],
        execute_tool=lambda name, args: seen.append((name, args)) or "done",
    )
    assert reply == "已打开记事本"
    assert emotion == "happy"
    assert seen == [("open_app", "notepad")]

def test_new_system_skills_route():
    reg = _reg()
    cases = [
        ("系统信息", "system_info"),
        ("查看系统信息", "system_info"),
        ("锁定屏幕", "lock_screen"),
        ("锁屏", "lock_screen"),
        ("打开任务管理器", "task_manager"),
        ("显示桌面", "minimize_windows"),
        ("最小化所有窗口", "minimize_windows"),
    ]
    for text, expected in cases:
        skill, _params = reg.route(text)
        assert skill is not None, f"no skill matched: {text}"
        assert skill.name == expected, f"{text} -> {skill.name} != {expected}"


def test_respond_with_tools_no_executor_default():
    """Calling respond_with_tools without execute_tool must not crash."""
    from assistant.core.llm import LLMClient

    class OneShot(LLMClient):
        def chat(self, messages, json_mode=False):
            return '{"reply": "你好", "emotion": "neutral"}'

    reply, emotion = OneShot().respond_with_tools("你好", tools=[])
    assert reply == "你好"
    assert emotion == "neutral"


def test_routing_open_app_not_hijacked_by_read_file():
    """'打开百度' must route to open_app, not read_file."""
    from assistant.skills import apps as apps_skill
    reg = _reg()
    reg.register(apps_skill.open_app_skill())
    skill, _params = reg.route("打开百度")
    assert skill.name == "open_app"


def test_write_file_missing_text_does_not_crash(tmp_path):
    """'写入 hello' (no content) must not raise; empty text defaults to ''."""
    reg = _reg()
    skill, _params = reg.route("写入 hello")
    assert skill.name == "write_file"
    # handler must accept a missing/None text without crashing
    target = tmp_path / "hello"
    assert skill.handler({"path": str(target), "text": None}, None) == "已写入文件 " + str(target)
    assert target.read_text(encoding="utf-8") == ""


def test_read_file_pattern_extracts_path():
    """'读文件 a.txt' must extract the path, not the literal '文件'."""
    reg = _reg()
    skill, params = reg.route("读文件 a.txt")
    assert skill.name == "read_file"
    assert params.get("path") == "a.txt"


def test_routing_clipboard_read_not_hijacked():
    """'读取剪贴板' must route to clipboard_read, not read_file."""
    reg = _reg()
    skill, _params = reg.route("读取剪贴板")
    assert skill.name == "clipboard_read"
    skill2, _ = reg.route("剪贴板")
    assert skill2.name == "clipboard_read"


def test_copy_to_clipboard_not_hijacked_by_read():
    """'复制到剪贴板' must route to clipboard_write, not clipboard_read."""
    reg = _reg()
    skill, params = reg.route("复制到剪贴板")
    assert skill is not None
    assert skill.name == "clipboard_write"
    assert params.get("text") == "到剪贴板"


def test_type_text_handles_pyautogui_failsafe(monkeypatch):
    """_type_text must catch pyautogui failures and return a friendly message."""
    from assistant.skills import control as C

    class FakePag:
        def write(self, text, interval=0.0):
            raise RuntimeError("PyAutoGUI fail-safe triggered")

    monkeypatch.setattr(C, "_pag", lambda: FakePag())
    out = C._type_text("你好")
    assert "输入失败" in out


def test_type_text_empty_returns_guidance():
    from assistant.skills import control as C
    assert "请告诉我" in C._type_text("")


def test_press_keys_empty_returns_guidance():
    """Empty press_keys input must return guidance, not a misleading message."""
    from assistant.skills import control as C
    assert "请告诉我" in C._press_keys("")
    assert "请告诉我" in C._press_keys("   ")


def test_volume_clamps_range(monkeypatch):
    """Volume outside 0-100 is clamped; non-numeric input returns guidance."""
    from assistant.skills import system as S
    # non-numeric input returns guidance without touching the system
    assert "请提供" in S._set_volume("abc")
    # clamp + fake the OS backend to avoid a real volume change
    monkeypatch.setattr(S, "os", _FakeOS("nt"))
    captured = {}
    def fake_posix(level):
        captured["level"] = level
        return "ok"
    monkeypatch.setattr(S, "_set_volume_posix", fake_posix)
    # force posix path by pretending non-nt, then restore nt check via fake os
    monkeypatch.setattr(S, "os", _FakeOS("posix"))
    S._set_volume("999")
    assert captured["level"] == "100"


class _FakeOS:
    def __init__(self, name):
        self.name = name


def test_screenshot_default_path_not_cwd(monkeypatch, tmp_path):
    """_screenshot with no path writes to Pictures, not the current dir."""
    import types

    from assistant.skills import system as S

    pics = tmp_path / "Pictures"
    # redirect expanduser("~") to a temp base so no real Pictures is touched
    monkeypatch.setattr(S.os.path, "expanduser", lambda p: str(tmp_path) if p == "~" else p)

    class FakeMSS:
        def __init__(self):
            pass
        def shot(self, output):
            FakeMSS.output = output
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    mss_mod = types.ModuleType("mss")
    mss_mod.mss = FakeMSS
    monkeypatch.setitem(sys.modules, "mss", mss_mod)

    result = S._screenshot(None)
    assert "已截图保存到" in result
    assert str(pics) in result
    assert not (Path.cwd() / "screenshot.png").exists()


# ---- safety railing tests: screen-affecting ops must be opt-in ----

class _FakeCfg:
    def __init__(self, allow=False):
        self._allow = allow
    def get(self, key, default=None):
        if key == "safety.allow_screen_control":
            return self._allow
        return default


class _FakeCtx:
    def __init__(self, allow=False):
        self.config = _FakeCfg(allow)


def test_lock_screen_disabled_by_default(monkeypatch):
    """Without safety.allow_screen_control, lock/screen-control must refuse."""
    from assistant.skills import system as S
    called = []
    monkeypatch.setattr(S, "_lock_screen", lambda: called.append(1) or "locked")
    out = S._lock_screen_handler({}, _FakeCtx(False))
    assert "默认禁用" in out
    assert called == []


def test_lock_screen_runs_when_enabled(monkeypatch):
    from assistant.skills import system as S
    called = []
    monkeypatch.setattr(S, "_lock_screen", lambda: called.append(1) or "locked")
    out = S._lock_screen_handler({}, _FakeCtx(True))
    assert out == "locked"
    assert called == [1]


def test_minimize_disabled_by_default(monkeypatch):
    from assistant.skills import system as S
    called = []
    monkeypatch.setattr(S, "_minimize_all_windows", lambda: called.append(1) or "minimized")
    out = S._minimize_handler({}, _FakeCtx(False))
    assert "默认禁用" in out
    assert called == []


def test_task_manager_still_allowed_without_flag(monkeypatch):
    """Task manager is not a screen-control op and must remain available."""
    from assistant.skills import system as S
    called = []
    monkeypatch.setattr(S, "_open_task_manager", lambda: called.append(1) or "taskmgr")
    out = S._task_manager_handler({}, _FakeCtx(False))
    assert out == "taskmgr"
    assert called == [1]
