"""Bootstrap: auto-install dependencies and download the Vosk model.

Run:  python scripts/bootstrap.py

Idempotent: skips pip install when every dependency is already importable and
skips the model download when the model directory already exists, so the
second and later launches (e.g. via start.bat) are near-instant.
"""
from __future__ import annotations

import importlib
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip"
MODEL_DIR = ROOT / "vosk-model-small-cn-0.22"

# (pip distribution name, importable module name). The importable name is used
# to decide whether a fresh `pip install` is still required.
REQUIREMENTS = [
    ("pyyaml", "yaml"),
    ("sounddevice", "sounddevice"),
    ("numpy", "numpy"),
    ("vosk", "vosk"),
    ("pyttsx3", "pyttsx3"),
    ("edge-tts", "edge_tts"),
    ("pyautogui", "pyautogui"),
    ("keyboard", "keyboard"),
    ("pyperclip", "pyperclip"),
    ("mss", "mss"),
    ("pillow", "PIL"),
    ("pytesseract", "pytesseract"),
    ("requests", "requests"),
    ("rich", "rich"),
    ("openai", "openai"),
]


def run(cmd: list[str]) -> None:
    print("$ " + " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))


def _deps_missing() -> list[str]:
    missing: list[str] = []
    for dist, mod in REQUIREMENTS:
        try:
            importlib.import_module(mod)
        except Exception:
            missing.append(dist)
    return missing


def install_deps(force: bool = False) -> None:
    missing = _deps_missing()
    if not missing and not force:
        print("==> Python 依赖已就绪，跳过安装。")
        return
    print("==> 安装 Python 依赖 ...")
    targets = [d for d, _ in REQUIREMENTS] if force else missing
    run([sys.executable, "-m", "pip", "install", "-U", *targets])


def download_model() -> None:
    if MODEL_DIR.exists():
        print(f"模型已存在: {MODEL_DIR}")
        return
    zip_path = ROOT / "vosk-model-small-cn-0.22.zip"
    print("==> 下载中文语音识别模型（约 42MB）...")
    urllib.request.urlretrieve(MODEL_URL, zip_path)
    print("==> 解压模型 ...")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(ROOT)
    zip_path.unlink(missing_ok=True)
    print(f"模型就绪: {MODEL_DIR}")


def install_package() -> None:
    """Install this project itself in editable mode.

    Ensures the `assistant` package is importable from the repo even on a
    machine that has never run `pip install -e .` before, so double-click
    launchers (start.bat / start.ps1) work out of the box.
    """
    try:
        import assistant  # noqa: F401
        print("==> OpenVoice package already installed.")
        return
    except Exception:
        pass
    print("==> Installing OpenVoice package (editable)...")
    run([sys.executable, "-m", "pip", "install", "-e", "."])


def verify_setup() -> bool:
    """Return True when the runtime is ready to launch."""
    ok = True
    try:
        import assistant  # noqa: F401
        print("==> package import: OK")
    except Exception as e:
        print(f"==> package import: FAILED ({e})")
        ok = False
    for dist, mod in REQUIREMENTS:
        try:
            importlib.import_module(mod)
        except Exception as e:
            print(f"==> dependency {dist}: MISSING ({e})")
            ok = False
    if not MODEL_DIR.exists():
        print("==> speech model: MISSING")
        ok = False
    if ok:
        print("==> All checks passed. Ready to launch.")
    return ok



def main() -> int:
    install_deps()
    install_package()
    download_model()
    print()
    if not verify_setup():
        print("==> Setup incomplete; please fix the issues above and re-run.")
        return 1
    print("依赖安装完成。可以启动:")
    print("  python main.py --wake    # 持续唤醒监听")
    print("  python main.py --text    # 文字对话（无需麦克风）")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
