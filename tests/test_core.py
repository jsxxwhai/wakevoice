"""Tests for core skills and config routing (no audio/mic required)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from assistant.skills.base import SkillRegistry
from assistant.skills import apps as apps_skill
from assistant.skills import control as control_skill
from assistant.core.config import Config


def _registry() -> SkillRegistry:
    reg = SkillRegistry()
    reg.register(apps_skill.open_app_skill())
    control_skill.register_control_skills(reg)
    return reg


def test_open_app_target():
    reg = _registry()
    skill, params = reg.route("打开百度")
    assert skill.name == "open_app"
    assert params.get("target") == "百度"


def test_type_text():
    reg = _registry()
    skill, params = reg.route("输入你好世界")
    assert skill.name == "type_text"
    assert params.get("text") == "你好世界"


def test_press_keys():
    reg = _registry()
    skill, params = reg.route("按下ctrl+c")
    assert skill.name == "press_keys"
    assert params.get("keys") == "ctrl+c"


def test_click_coords():
    reg = _registry()
    skill, params = reg.route("点击 100 200")
    assert skill.name == "click"
    assert params.get("x") == "100"
    assert params.get("y") == "200"


def test_config_defaults():
    cfg = Config()
    assert cfg.get("app.name") == "OpenVoice"
    assert cfg.get("wake.word") == "你好伙伴"
    assert cfg.get("tts.engine") == "edge"


def test_config_set_get():
    cfg = Config()
    cfg.set("wake.word", "土豆")
    assert cfg.get("wake.word") == "土豆"


def test_tts_emotion_enabled_disables_ssml_style():
    """When emotion_enabled is False, EdgeTTS builds neutral SSML."""
    from assistant.tts.engine import EdgeTTS
    e = EdgeTTS.__new__(EdgeTTS)
    e.voice = "zh-CN-XiaoxiaoNeural"
    e.rate = "+0%"
    e.pitch = "+0Hz"
    e.volume = "+0%"
    e.emotion_enabled = False
    e.style = "general"
    ssml = e._build_ssml("hi", "happy")
    assert "style='general'" in ssml
    e.emotion_enabled = True
    ssml2 = e._build_ssml("hi", "happy")
    assert "style='cheerful'" in ssml2


def test_tts_style_config_used_when_no_emotion():
    """tts.style is used as the fallback SSML style when emotion is None."""
    from assistant.tts.engine import EdgeTTS
    e = EdgeTTS.__new__(EdgeTTS)
    e.voice = "zh-CN-XiaoxiaoNeural"
    e.rate = "+0%"
    e.pitch = "+0Hz"
    e.volume = "+0%"
    e.emotion_enabled = True
    e.style = "calm"
    ssml = e._build_ssml("hi", None)
    assert "style='calm'" in ssml


def test_click_requires_coordinates():
    """A bare '点击' without coordinates must NOT route to a (0,0) click."""
    reg = _registry()
    # '点击' alone has no coordinates -> must not match the click skill
    assert reg.route("点击") is None or reg.route("点击")[0].name != "click"
    # negative coordinates are rejected by the handler
    from assistant.skills import control as C
    assert "坐标不能为负数" in C._click(-5, 10)
    # invalid coordinates are rejected
    assert "请提供有效" in C._click("abc", "def")


def test_config_env_var_override(monkeypatch):
    """Env vars override config values (e.g. WAKE_WORD wins over wake.word)."""
    cfg = Config()
    cfg.set("wake.word", "你好伙伴")
    monkeypatch.setenv("WAKE_WORD", "土豆")
    assert cfg.get("wake.word") == "土豆"
    monkeypatch.delenv("WAKE_WORD")
    assert cfg.get("wake.word") == "你好伙伴"


def test_config_get_missing_returns_default():
    cfg = Config()
    assert cfg.get("does.not.exist", "fallback") == "fallback"
    assert cfg.get("does.not.exist") is None


def test_config_nested_get():
    cfg = Config()
    cfg.set("mcp.servers", [{"name": "x"}])
    assert cfg.get("mcp.servers") == [{"name": "x"}]

def test_wake_backends_listed_and_default_valid():
    """wake.backends enumerates valid engines; default engine is one of them."""
    cfg = Config()
    backends = cfg.get("wake.backends")
    assert isinstance(backends, list) and backends
    assert cfg.get("wake.engine") in backends


def test_app_autostart_field_removed():
    """app.autostart was a dead config field and must not be present."""
    cfg = Config()
    assert "autostart" not in cfg.get("app")

def test_pyttsx3_fallback_uses_numeric_defaults(monkeypatch):
    """pyttsx3 fallback must not receive edge-tts string values (rate="+0%")."""
    import assistant.tts.engine as E
    from assistant.core.config import Config

    created = {}

    class FakePyttsx3(E.BaseTTS):
        name = "pyttsx3"
        def __init__(self, rate=175, volume=0.9):
            created["rate"] = rate
            created["volume"] = volume
        def say(self, text, emotion=None, **kwargs):
            return E.TTSResult("pyttsx3", 0, emotion)

    # force engine name to pyttsx3 and stub the class to avoid real SAPI init
    cfg = Config()
    cfg.set("tts.engine", "pyttsx3")
    cfg.set("tts.rate", "+0%")  # edge-tts style string must NOT leak through
    cfg.set("tts.volume", "+0%")
    monkeypatch.setattr(E, "Pyttsx3TTS", FakePyttsx3)
    engine = E.get_tts_engine(cfg)
    assert isinstance(engine, FakePyttsx3)
    assert created["rate"] == 175
    assert 0.0 <= created["volume"] <= 1.0

def test_env_var_coerces_numeric_types(monkeypatch):
    """Numeric env vars are coerced to int/float so typed config consumers work."""
    cfg = Config()
    monkeypatch.setenv("AGENTS_MAX_WORKERS", "7")
    assert cfg.get("agents.max_workers") == 7
    assert isinstance(cfg.get("agents.max_workers"), int)
    monkeypatch.setenv("WAKE_SENSITIVITY", "0.85")
    assert cfg.get("wake.sensitivity") == 0.85
    assert isinstance(cfg.get("wake.sensitivity"), float)
    monkeypatch.setenv("TTS_EMOTION_ENABLED", "false")
    assert cfg.get("tts.emotion_enabled") is False


def test_env_var_bool_true_strings(monkeypatch):
    cfg = Config()
    monkeypatch.setenv("SKILLS_ENABLED", "true")
    assert cfg.get("skills.enabled") is True
    monkeypatch.setenv("SKILLS_ENABLED", "1")
    assert cfg.get("skills.enabled") is True
    monkeypatch.setenv("SKILLS_ENABLED", "no")
    assert cfg.get("skills.enabled") is False


def test_launch_app_website_mapping(monkeypatch):
    """Expanded website mapping routes to the right URL (no real browser)."""
    from assistant.skills import apps as A
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))
    A._launch_app("百度", None)
    assert opened == ["https://www.baidu.com"]
    opened.clear()
    A._launch_app("打开 b站", None)
    assert opened == ["https://www.bilibili.com"]
    opened.clear()
    A._launch_app("豆瓣", None)
    assert opened == ["https://www.douban.com"]


def test_launch_app_exe_mapping(monkeypatch):
    """Expanded executable mapping launches the right binary (no real launch)."""
    from assistant.skills import apps as A
    launched = []
    monkeypatch.setattr(A.subprocess, "Popen", lambda c, shell=False: launched.append(c))
    monkeypatch.setattr(A, "os", type("OS", (), {"name": "nt"})())
    assert "记事本" in A._launch_app("记事本", None)
    assert launched == ["notepad.exe"]

def test_launch_app_prefers_longer_key_match(monkeypatch):
    """“百度地图” must open map.baidu.com, not baidu.com."""
    from assistant.skills import apps as A
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))
    A._launch_app("打开百度地图", None)
    assert opened == ["https://map.baidu.com"]


def test_launch_app_prefers_longer_exe_match(monkeypatch):
    """“文件资源管理器” must hit the longer key, not the bare “资源管理器”."""
    from assistant.skills import apps as A
    launched = []
    monkeypatch.setattr(A.subprocess, "Popen", lambda c, shell=False: launched.append(c))
    monkeypatch.setattr(A, "os", type("OS", (), {"name": "nt"})())
    out = A._launch_app("文件资源管理器", None)
    assert "已启动" in out
    assert launched == ["explorer.exe"]


def test_type_text_ascii_uses_pyautogui_write(monkeypatch):
    """ASCII text should still go through pyautogui.write (fast path)."""
    from assistant.skills import control as C
    calls = {}
    class FakePag:
        def write(self, text, interval=0.03):
            calls['text'] = text
            calls['interval'] = interval
    monkeypatch.setattr(C, '_pag', lambda: FakePag())
    assert '已输入' in C._type_text('hello')
    assert calls == {'text': 'hello', 'interval': 0.03}


def test_type_text_non_ascii_uses_clipboard_paste(monkeypatch):
    """Chinese text must paste via clipboard+hotkey, never pyautogui.write."""
    from assistant.skills import control as C
    calls = {}
    class FakePag:
        def hotkey(self, *keys):
            calls['hotkey'] = keys
    monkeypatch.setattr(C, '_pag', lambda: FakePag())
    monkeypatch.setattr(C, '_paste_modifier', lambda: 'ctrl')
    monkeypatch.setattr('pyperclip.copy', lambda s: calls.setdefault('copies', []).append(s))
    monkeypatch.setattr('pyperclip.paste', lambda: 'old-clip')
    monkeypatch.setattr('time.sleep', lambda s: None)
    assert '已输入' in C._type_text('你好世界')
    assert calls['hotkey'] == ('ctrl', 'v')
    assert calls['copies'][0] == '你好世界'
    # clipboard restored afterwards
    assert calls['copies'][-1] == 'old-clip'
