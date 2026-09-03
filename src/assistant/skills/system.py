"""Built-in skills: system utilities (volume, clipboard, screenshot, file ops)."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from .base import Skill

try:
    import pyperclip
    _CLIP = True
except Exception:
    _CLIP = False


def _set_volume_posix(level):
    """Set volume on Linux/macOS via amixer or pactl (best effort)."""
    try:
        if subprocess.run(["amixer", "--version"], capture_output=True).returncode == 0:
            subprocess.run(["amixer", "-q", "sset", "Master", f"{int(level)}%"],
                           capture_output=True, timeout=10)
            return "volume set to " + str(int(level)) + "%"
    except Exception:
        pass
    try:
        if subprocess.run(["pactl", "--version"], capture_output=True).returncode == 0:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{int(level)}%"],
                           capture_output=True, timeout=10)
            return "volume set to " + str(int(level)) + "%"
    except Exception:
        pass
    return "cannot set volume on this platform (need amixer or pactl)"

def _set_volume(level):
    """Set Windows master volume 0-100 using the PowerShell COM API."""
    try:
        level_i = int(level)
    except (TypeError, ValueError):
        return "请提供 0-100 的音量值，例如：音量调到 80"
    if level_i < 0:
        level_i = 0
    elif level_i > 100:
        level_i = 100
    level = str(level_i)
    if os.name != "nt":
        return _set_volume_posix(level)
    try:
        # single-line PowerShell that uses the CoreAudio COM object
        ps = (
            "Add-Type -TypeDefinition 'using System.Runtime.InteropServices;"
            "[Guid(\"5CDF2C82-841E-4546-9722-0CF74078229A\"), "
            "InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]"
            "interface IAudioEndpointVolume {"
            "int _; int _2; int _3; int _4; int _5; int _6; int _7; int _8; int _9; "
            "int SetMasterVolumeLevelScalar(float fLevel, System.Guid g);};"
            "[Guid(\"D666063F-1587-4E43-81F1-B948E807363F\"), "
            "InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]"
            "interface IMMDevice {int Activate(ref System.Guid id, int clsCtx, int params, out IAudioEndpointVolume vol);};"
            "[Guid(\"A95664D2-9614-4F35-A746-DE8DB63617E6\"), "
            "InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]"
            "interface IMMDeviceEnumerator {int EnumAudioEndpoints(int dataFlow, int mask, out IMMDevice dev);};"
            "[ComImport, Guid(\"BCDE0395-E52F-467C-8E3D-C4579291692E\")] class MMDeviceEnumeratorComObject {};"
            "$e = New-Object MMDeviceEnumeratorComObject -as IMMDeviceEnumerator;"
            "$m = $null; [void]$e.EnumAudioEndpoints(0, 1, [ref]$m);"
            "$v = $null; [void]$m.Activate([ref][Guid]\"5CDF2C82-841E-4546-9722-0CF74078229A\", 0, 0, [ref]$v);"
            "[void]$v.SetMasterVolumeLevelScalar(%f, [Guid]::Empty)'"
        )
        level_f = float(level) / 100.0
        subprocess.run(["powershell", "-NoProfile", "-Command", ps % level_f],
                       capture_output=True, timeout=10)
        return "音量已设为 " + str(int(level)) + "%"
    except Exception as e:
        return "设置音量失败：" + str(e)




def _system_info():
    """Return a compact summary of OS, CPU, and memory (best effort)."""
    try:
        import platform
        import shutil
        total, used, free = shutil.disk_usage(os.path.expanduser("~"))
        gb = 1024 ** 3
        parts = [
            "系统: " + platform.system() + " " + platform.release(),
            "机器: " + platform.machine(),
            "Python: " + platform.python_version(),
            f"磁盘: 已用 {used / gb:.1f} GB / 共 {total / gb:.1f} GB（剩余 {free / gb:.1f} GB）",
        ]
        return "；".join(parts)
    except Exception as e:
        return "读取系统信息失败：" + str(e)


def _lock_screen():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "屏幕已锁定"
        except Exception as e:
            return "锁屏失败：" + str(e)
    try:
        subprocess.run(["xdg-screensaver", "lock"], capture_output=True, timeout=10)
        return "屏幕已锁定"
    except Exception as e:
        return "锁屏失败：" + str(e)


def _open_task_manager():
    if os.name == "nt":
        try:
            subprocess.Popen(["taskmgr.exe"])
            return "已打开任务管理器"
        except Exception as e:
            return "打开任务管理器失败：" + str(e)
    try:
        subprocess.Popen(["gnome-system-monitor"])
        return "已打开系统监视器"
    except Exception as e:
        return "打开系统监视器失败：" + str(e)


def _minimize_all_windows():
    if os.name != "nt":
        return "最小化窗口目前仅支持 Windows"
    try:
        import ctypes
        ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)  # Win key down
        ctypes.windll.user32.keybd_event(0x44, 0, 0, 0)  # D key down
        ctypes.windll.user32.keybd_event(0x44, 0, 2, 0)  # D key up
        ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)  # Win key up
        return "已最小化所有窗口"
    except Exception as e:
        return "最小化窗口失败：" + str(e)



def _system_info_handler(p, c):
    return _system_info()


def _ctx_config(c):
    """Return the config object from a skill context (or None)."""
    return getattr(c, "config", None) if c is not None else None


def _screen_control_enabled(c) -> bool:
    """Screen-affecting ops require explicit user opt-in via safety config."""
    cfg = _ctx_config(c)
    if cfg is None:
        return False
    try:
        return bool(cfg.get("safety.allow_screen_control", False))
    except Exception:
        return False


def _lock_screen_handler(p, c):
    if not _screen_control_enabled(c):
        return "锁屏/黑屏操作已默认禁用。如需开启，请在配置里设置 safety.allow_screen_control: true"
    return _lock_screen()


def _task_manager_handler(p, c):
    return _open_task_manager()


def _minimize_handler(p, c):
    if not _screen_control_enabled(c):
        return "最小化/显示桌面操作已默认禁用。如需开启，请在配置里设置 safety.allow_screen_control: true"
    return _minimize_all_windows()


def _clipboard_read():
    if not _CLIP:
        return "剪贴板模块未安装（pip install pyperclip）"
    return pyperclip.paste()


def _clipboard_write(text):
    if not _CLIP:
        return "剪贴板模块未安装（pip install pyperclip）"
    pyperclip.copy(text)
    return "已复制到剪贴板"


def _screenshot(path=None):
    """Capture the screen to PNG.

    If `path` is empty/None, a timestamped file is written into the user's
    Pictures directory (falling back to home) so the current working
    directory is never polluted with stray screenshot files.
    """
    try:
        import mss
        if not path:
            from datetime import datetime
            pics = Path(os.path.expanduser("~")) / "Pictures"
            try:
                pics.mkdir(parents=True, exist_ok=True)
            except Exception:
                pics = Path(os.path.expanduser("~"))
            path = str(pics / ("截图_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"))
        with mss.mss() as sct:
            sct.shot(output=path)
        return "已截图保存到 " + path
    except Exception as e:
        return "截图失败：" + str(e)


def _write_file(path, text):
    try:
        path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return "已写入文件 " + path
    except Exception as e:
        return "写文件失败：" + str(e)


def _read_file(path):
    try:
        path = os.path.expanduser(path)
        with open(path, encoding="utf-8") as f:
            return f.read(2001)[:2000]
    except Exception as e:
        return "读文件失败：" + str(e)


def register_system_skills(registry):
    registry.register(Skill(
        name="set_volume",
        description="调节系统音量（0-100）",
        patterns=[re.compile(r"(?:音量|声音)\s*(?:调到|设为|调整到|设成)?\s*(?P<level>\d{1,3})")],
        keywords=["音量", "声音"],
        handler=lambda p, c: _set_volume(p.get("level", "50")),
    ))
    registry.register(Skill(
        name="clipboard_write",
        description="复制文字到剪贴板",
        patterns=[re.compile(r"(?:复制|拷贝)\s*(?P<text>.+)")],
        keywords=["复制", "拷贝"],
        handler=lambda p, c: _clipboard_write(p.get("text", "")),
    ))
    registry.register(Skill(
        name="screenshot",
        description="屏幕截图",
        patterns=[re.compile(r"(?:屏幕截图|截屏|截个图|截一张图|截图)")],
        keywords=["截图", "截屏"],
        handler=lambda p, c: _screenshot(""),
    ))
    registry.register(Skill(
        name="write_file",
        description="写入文本到文件",
        patterns=[re.compile(r"(?:写入|保存到)\s*(?P<path>\S+)\s*(?P<text>.+)?")],
        keywords=["写入文件", "保存"],
        handler=lambda p, c: _write_file(p.get("path", ""), p.get("text") or ""),
    ))
    registry.register(Skill(
        name="read_file",
        description="读取文件内容",
        patterns=[re.compile(r"(?:读取文件|查看文件|读取|读文件|查看|读)\s*(?P<path>\S+)")],
        keywords=["读文件"],
        handler=lambda p, c: _read_file(p.get("path", "")),
    ))

    registry.register(Skill(
        name="clipboard_read",
        description="读取剪贴板内容",
        # Anchored so "复制到剪贴板" does NOT match the read skill.
        patterns=[re.compile(r"^(?:读取|查看|看|读)\s*剪贴板(?:内容|里的内容)?$|^剪贴板(?:内容)?$")],
        keywords=[],
        handler=lambda p, c: _clipboard_read(),
    ))


    registry.register(Skill(
        name="system_info",
        description="查看系统信息（系统版本、内存、磁盘）",
        patterns=[re.compile(r"(?:系统信息|系统状态|电脑信息|磁盘空间|内存)")],
        keywords=["系统信息", "磁盘"],
        handler=_system_info_handler,
    ))
    registry.register(Skill(
        name="lock_screen",
        description="锁定屏幕",
        patterns=[re.compile(r"(?:锁定屏幕|锁屏|锁住电脑)")],
        keywords=["锁屏"],
        handler=_lock_screen_handler,
    ))
    registry.register(Skill(
        name="task_manager",
        description="打开任务管理器",
        patterns=[re.compile(r"(?:任务管理器|打开任务管理器)")],
        keywords=["任务管理器"],
        handler=_task_manager_handler,
    ))
    registry.register(Skill(
        name="minimize_windows",
        description="最小化所有窗口（显示桌面）",
        patterns=[re.compile(r"(?:最小化|显示桌面|收起所有窗口)")],
        keywords=["最小化", "显示桌面"],
        handler=_minimize_handler,
    ))
