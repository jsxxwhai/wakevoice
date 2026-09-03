"""Built-in skill: control the computer (keyboard, mouse)."""
from __future__ import annotations

import re
import sys
import time

from .base import Skill


def _pag():
    """Lazily import pyautogui so it does not occupy memory until first use."""
    try:
        import pyautogui
        return pyautogui
    except Exception:
        return None


def _is_ascii(text) -> bool:
    """True when every char is ASCII, so plain key events can type it."""
    try:
        text.encode("ascii")
        return True
    except (UnicodeEncodeError, AttributeError):
        return False


def _paste_modifier() -> str:
    """Return the keyboard modifier used for paste on this platform."""
    if sys.platform == "darwin":
        return "command"
    return "ctrl"


def _paste_via_clipboard(text):
    """Paste `text` by copying it to the clipboard and pressing Ctrl/Cmd+V.

    pyautogui.write() can only send single key codes and silently drops any
    non-ASCII character (Chinese, emoji, ...). Copying to the clipboard and
    pasting is the reliable cross-language input path.
    """
    import pyperclip
    pag = _pag()
    if pag is None:
        return False, "控制模块未安装"

    # Remember the user's clipboard so we can restore it afterwards.
    previous = None
    try:
        previous = pyperclip.paste()
    except Exception:
        previous = None

    try:
        pyperclip.copy(text)
    except Exception as e:
        return False, "写入剪贴板失败：" + str(e)

    # Give the clipboard a moment to settle before pasting (Windows clipboard
    # can briefly reject an immediate Ctrl+V while the copy is still open).
    time.sleep(0.05)

    try:
        pag.hotkey(_paste_modifier(), "v")
    except Exception as e:
        return False, "粘贴失败：" + str(e)
    finally:
        if previous is not None:
            try:
                time.sleep(0.05)
                pyperclip.copy(previous)
            except Exception:
                pass
    return True, None


def _type_text(text):
    if not text:
        return "请告诉我要输入什么文字，例如：输入 你好"
    if _is_ascii(text):
        pag = _pag()
        if pag is None:
            return "控制模块未安装（pip install pyautogui）"
        try:
            pag.write(text, interval=0.03)
        except Exception as e:
            # e.g. pyautogui.FailSafeException (mouse moved to a screen corner)
            return "输入失败（可能是鼠标在屏幕角落触发了安全保护）：" + str(e)
        return "已输入 " + str(len(text)) + " 个字符"
    # 非 ASCII（中文/日文/emoji…）：pyautogui.write 会静默丢弃，改走剪贴板粘贴
    ok, err = _paste_via_clipboard(text)
    if not ok:
        return "输入失败：" + (err or "未知错误")
    return "已输入 " + str(len(text)) + " 个字符"


def _press_keys(keys):
    if not keys or not str(keys).strip():
        return "请告诉我要按哪个键，例如：按下 ctrl+c"
    pag = _pag()
    if pag is None:
        return "控制模块未安装"
    # split on 、 , ， ; or whitespace, but KEEP + so hotkeys like ctrl+c work
    parts = [k.strip() for k in re.split(r"[、,，;\s]+", keys) if k.strip()]
    if not parts:
        return "请告诉我要按哪个键，例如：按下 ctrl+c"
    pressed = []
    try:
        for k in parts:
            if "+" in k:
                pag.hotkey(*[p.strip() for p in k.split("+") if p.strip()])
            else:
                pag.press(k)
            pressed.append(k)
    except Exception as e:
        return "按键失败（可能是鼠标在屏幕角落触发了安全保护）：" + str(e)
    return "已按下 " + " ".join(pressed)


def _click(x, y):
    """Click at (x, y); validate coordinates to avoid accidental (0,0) clicks."""
    try:
        xi = int(x)
        yi = int(y)
    except (TypeError, ValueError):
        return "请提供有效的点击坐标，例如：点击 100 200"
    if xi < 0 or yi < 0:
        return "坐标不能为负数"
    pag = _pag()
    if pag is None:
        return "控制模块未安装"
    try:
        pag.click(xi, yi)
    except Exception as e:
        return "点击失败（可能是鼠标在屏幕角落触发了安全保护）：" + str(e)
    return "已点击 (" + str(xi) + ", " + str(yi) + ")"


def register_control_skills(registry):
    registry.register(Skill(
        name="type_text", description="模拟键盘输入文字（支持中文/任意字符）",
        patterns=[re.compile(r"(?:输入|打字)\s*(?P<text>.+)")],
        keywords=["输入", "打字"],
        handler=lambda p, c: _type_text(p.get("text", "")),
    ))
    registry.register(Skill(
        name="press_keys", description="按下按键或组合键，如 ctrl+c",
        patterns=[re.compile(r"(?:按下|按键|按)\s*(?P<keys>.+)")],
        keywords=["按下", "按键"],
        handler=lambda p, c: _press_keys(p.get("keys", "")),
    ))
    registry.register(Skill(
        name="click", description="点击屏幕坐标（例如：点击 100 200）",
        patterns=[re.compile(r"(?:点击|单击)\s*(?P<x>\d+)\s*[,，\s]\s*(?P<y>\d+)")],
        keywords=[],
        handler=lambda p, c: _click(p.get("x", 0), p.get("y", 0)),
    ))
