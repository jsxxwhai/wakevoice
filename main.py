"""Friendly entry point: double-click to run, or `python main.py`.

Auto-installs missing dependencies and then starts the assistant.
"""
from __future__ import annotations

import os
import subprocess
import sys


# Core runtime dependencies. If any is missing (or the package itself is not
# installed yet), run an editable install which pulls in everything from
# pyproject.toml. We check a broad set so a fresh double-click just works
# even if only one transitive package (e.g. `keyboard`) is absent.
_CORE_IMPORTS = (
    "yaml",
    "sounddevice",
    "vosk",
    "pyttsx3",
    "edge_tts",
    "pyautogui",
    "keyboard",
    "pyperclip",
    "pytesseract",
    "mss",
    "PIL",
    "numpy",
    "requests",
    "rich",
)


def _ensure_deps() -> None:
    missing = []
    for mod in _CORE_IMPORTS:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        print("首次运行，正在安装依赖（请稍候）...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
        print("依赖安装完成。")


def _ensure_config() -> None:
    """Auto-create config/config.yaml from the example on first run.

    Never overwrites an existing file, so re-launching is always safe and the
    user always ends up with a real, editable config after the first start.
    """
    try:
        from pathlib import Path
        here = Path(os.path.dirname(os.path.abspath(__file__)))
        dst = here / "config" / "config.yaml"
        if dst.exists():
            return
        src = here / "config" / "config.example.yaml"
        if not src.exists():
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        print("首次运行：已生成 config/config.yaml（可修改唤醒词/按键）。")
    except Exception as e:  # best-effort; built-in defaults still work
        print("提示：自动生成配置文件失败（{}），将使用默认配置。".format(e))


def main() -> int:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    _ensure_deps()
    _ensure_config()
    from assistant.cli import main as cli_main
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
