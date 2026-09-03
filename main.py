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


def main() -> int:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    _ensure_deps()
    from assistant.cli import main as cli_main
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
