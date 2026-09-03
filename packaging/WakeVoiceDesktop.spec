# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for WakeVoice (onedir portable bundle).

Build (from repo root):
    python -m PyInstaller --noconfirm --clean packaging/WakeVoiceDesktop.spec

The speech model is intentionally NOT bundled (~65 MB extracted). The runtime
boot entry (exe_entry.py) downloads it next to the .exe on first launch so a
fresh copy can run offline-capable afterwards and updates never require
rebuilding the binary.

The `assistant` package only needs its own modules plus the light third-party
deps declared in pyproject.toml. Heavy ML libraries installed on this build
machine (torch, tensorflow, scipy, pandas, matplotlib, transformers...) are
explicitly excluded so the bundle stays small and the build stays fast.
"""
import os

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

SPEC_DIR = os.path.abspath(SPECPATH)
ROOT = os.path.dirname(SPEC_DIR)

name = "WakeVoiceDesktop"

# Every assistant submodule that the app actually uses at runtime.
hiddenimports = [
    "assistant",
    "assistant.audio",
    "assistant.cli",
    "assistant.paths",
    "assistant.agents.hub",
    "assistant.agents.llm_agent",
    "assistant.connectors.client",
    "assistant.core.app",
    "assistant.core.config",
    "assistant.core.errors",
    "assistant.core.llm",
    "assistant.core.logging",
    "assistant.core.memory",
    "assistant.core.memory_ctx",
    "assistant.screen.reader",
    "assistant.skills.apps",
    "assistant.skills.base",
    "assistant.skills.control",
    "assistant.skills.mcp_bridge",
    "assistant.skills.plugins",
    "assistant.skills.system",
    "assistant.stt.voice_input",
    "assistant.stt.vosk_stt",
    "assistant.tts.engine",
    "assistant.wake.keyword",
    # vosk cffi backend
    "vosk",
    "vosk.vosk_cffi",
    "_cffi_backend",
]

# Vosk ships its C++ runtime as DLLs inside the vosk package dir; collect
# them into the bundle so the ABI-mode cffi wrapper can load libvosk.dll.
binaries = collect_dynamic_libs("vosk")

# Non-python data shipped inside the vosk package (e.g. transcriber helpers).
datas = collect_data_files("vosk")

# Heavy ML / data libraries that are NOT runtime deps of this app but are
# installed on the build machine and would otherwise bloat the bundle.
EXCLUDES = [
    "tkinter",
    "unittest",
    "pydoc",
    "test",
    "pytest",
    "torch",
    "torchaudio",
    "torchvision",
    "tensorflow",
    "keras",
    "jax",
    "scipy",
    "pandas",
    "matplotlib",
    "transformers",
    "sklearn",
    "numba",
    "llvmlite",
    "cv2",
    # OpenAI SDK and its dependency tree (optional LLM feature only).
    # The assistant falls back to built-in local skills when the SDK is
    # absent, so bundling these would only bloat the download for most users.
    "openai",
    "httpx",
    "httpcore",
    "pydantic",
    "pydantic_core",
    "jiter",
    "distro",
    "tqdm",
    "websockets",
    "anyio",
    "cryptography",
    "bcrypt",
    "h11",
    "sniffio",
]

a = Analysis(
    [os.path.join(SPEC_DIR, "exe_entry.py")],
    pathex=[ROOT, os.path.join(ROOT, "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=name,
)