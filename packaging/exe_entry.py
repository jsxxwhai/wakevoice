# -*- coding: utf-8 -*-
"""Boot entry used by the PyInstaller bundle (OpenVoiceDesktop.exe).

Responsibilities (all idempotent, so every launch is safe and fast):

  1. Locate the writable data dir next to the executable (onedir bundle).
  2. For voice commands, make sure the Chinese Vosk speech model exists
     there; download and extract it on first run otherwise (~42 MB, once).
  3. Point the assistant at that model dir via environment variables and
     then launch the normal CLI (wake-word loop by default).

The model intentionally lives next to the exe (not inside the bundle) so the
download can be retried, updated, or removed by the user without rebuilding.
"""
from __future__ import annotations

import os
import sys
import urllib.request
import zipfile
from pathlib import Path

MODEL_NAME = "vosk-model-small-cn-0.22"
MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip"


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _data_dir() -> Path:
    """Writable folder that travels with the program.

    - PyInstaller onedir bundle -> folder that holds the .exe
    - PyInstaller onefile       -> folder that holds the onefile .exe
    - plain python run          -> repository root (two levels up)
    """
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _model_dir() -> Path:
    return _data_dir() / MODEL_NAME


def _needs_model(argv: list[str]) -> bool:
    """Pure-info commands should work even before the model is downloaded."""
    info = {"--version", "-h", "--help", "--list-skills", "--list-agents"}
    return not (info & set(argv))


def _download_model(target: Path) -> None:
    """Download and extract the model next to the executable."""
    data = target.parent
    data.mkdir(parents=True, exist_ok=True)
    zip_path = data / (MODEL_NAME + ".zip")
    print("==> 首次运行：正在下载中文语音识别模型（约 42MB）...")
    print("    请保持网络畅通，完成后会自动解压并继续启动。")
    try:
        def _report(block_count: int, block_size: int, total: int) -> None:
            if total > 0 and block_count % 20 == 0:
                done = block_count * block_size
                pct = min(100.0, done * 100.0 / total)
                print("\r    已下载：{:.1f}%".format(pct), end="", flush=True)

        urllib.request.urlretrieve(MODEL_URL, zip_path, reporthook=_report)
        print("\r    已下载：100%，正在解压...")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(data)
        print("==> 模型下载完成：{}".format(target))
    except Exception as exc:
        print("\n==> 模型下载失败：{}".format(exc))
        raise
    finally:
        zip_path.unlink(missing_ok=True)

    if not target.is_dir():
        raise RuntimeError(
            "语音模型自动下载失败。请检查网络后重新运行，"
            "或手动下载解压到程序目录:\n  " + MODEL_URL)


def ensure_model() -> Path:
    """Return an existing model dir, downloading it once if necessary."""
    target = _model_dir()
    if target.is_dir():
        return target

    # Developer fallback: reuse a model already present in the repo.
    repo_model = Path(__file__).resolve().parent.parent / MODEL_NAME
    if repo_model.is_dir():
        return repo_model

    _download_model(target)
    return target


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    # Only voice commands require the speech model. Info commands should
    # respond instantly even on a machine that has not downloaded it yet.
    if _needs_model(argv):
        model = ensure_model()
        os.environ.setdefault("STT_MODEL_DIR", str(model))
        os.environ.setdefault("WAKE_WORD", os.environ.get("WAKE_WORD", "你好伙伴"))

    from assistant.cli import main as cli_main
    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())