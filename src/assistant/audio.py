"""Lightweight WAV playback with interrupt support.

The project intentionally keeps dependencies minimal, so playback is done
through `sounddevice` (already required by STT/wake) instead of adding a
media library. edge-tts/pyttsx3 hand us raw audio; we write a temp WAV and
stream it out. An interrupt Event lets the voice loop stop speech instantly.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import wave
from pathlib import Path

log = logging.getLogger(__name__)

def _sd():
    """Lazily import sounddevice so non-audio paths never need PortAudio."""
    import sounddevice as sd
    return sd


class StopRequested(Exception):
    """Raised inside a worker when an interrupt (stop key) is pressed."""


_DEFAULT_RUNTIME_DIR = Path("runtime_tmp")
_MAX_TEMP_BYTES = 50 * 1024 * 1024  # hard ceiling shared by all audio scratch


def set_runtime_dir(path) -> None:
    """Point audio scratch files at a project-local directory."""
    globals()["_DEFAULT_RUNTIME_DIR"] = Path(path)


def _temp_dir() -> Path:
    d = _DEFAULT_RUNTIME_DIR
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return d


def _cleanup_runtime(max_age_seconds: float = 3600.0) -> None:
    """Delete stale scratch and enforce a hard total-size cap (oldest first)."""
    d = _temp_dir()
    try:
        now = time.time()
        files = []
        for path in d.glob("openvoice_tts_*.wav"):
            try:
                files.append((path, path.stat().st_mtime, path.stat().st_size))
            except OSError:
                continue
        total = sum(sz for _, _, sz in files)
        # oldest first
        for path, mtime, size in sorted(files, key=lambda x: x[1]):
            if now - mtime >= max_age_seconds or total > _MAX_TEMP_BYTES:
                try:
                    path.unlink(missing_ok=True)
                    total -= size
                except OSError:
                    continue
    except Exception:
        pass


def _clean_stale_temp_wavs(max_age_seconds: float = 3600.0) -> None:
    """Backwards-compatible cleanup wrapper (kept for imports/tests)."""
    _cleanup_runtime(max_age_seconds=max_age_seconds)


def _project_runtime_dir() -> Path:
    """Resolve runtime scratch dir.

    Absolute configured paths are used as-is; relative paths are anchored to
    the repository root so scratch never lands on the system drive or CWD.
    """
    configured = _DEFAULT_RUNTIME_DIR
    if configured.is_absolute():
        return configured
    root = Path(__file__).resolve().parent.parent.parent
    return root / configured


def _play_wav_sync(path: str | Path, stop_event: threading.Event | None = None) -> None:
    """Blocking WAV playback through sounddevice.

    Polls `stop_event` every ~30 ms so a stop key can cut speech short.
    """
    import soundfile as sf

    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    if data.size == 0:
        return
    # stereo -> mono downmix for the OutputStream (device-agnostic)
    if data.shape[1] > 1:
        data = data.mean(axis=1, keepdims=True)
    frames = int(sr * 0.03)
    with _sd().OutputStream(samplerate=sr, channels=1, dtype="float32") as out:
        idx = 0
        while idx < data.shape[0]:
            if stop_event is not None and stop_event.is_set():
                raise StopRequested()
            chunk = data[idx:idx + frames]
            out.write(chunk)
            idx += frames


def _write_wav(path: str | Path, pcm: bytes, sample_rate: int = 24000,
               sample_width: int = 2) -> None:
    """Write raw 16-bit little-endian PCM bytes to a mono WAV file."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(sample_width)
        w.setframerate(sample_rate)
        w.writeframes(pcm)


def play_pcm(pcm: bytes, sample_rate: int, stop_event: threading.Event | None = None) -> bool:
    """Play raw 16-bit mono PCM; returns True when fully played.

    Falls back gracefully if no audio output device is available. Temp WAVs are
    written to the project-local `runtime_tmp/` directory (never the OS temp on
    the system drive) and removed as soon as playback ends.
    """
    if not pcm:
        return False
    _cleanup_runtime(max_age_seconds=0.0)  # opportunistic tidy on entry
    tmp = _project_runtime_dir() / f"openvoice_tts_{os.getpid()}_{threading.get_ident()}.wav"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_wav(tmp, pcm, sample_rate=sample_rate)
        _play_wav_sync(tmp, stop_event)
        return True
    except StopRequested:
        return False
    except Exception as e:
        log.warning("audio playback failed: %s", e)
        return False
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        # Opportunistically clear old leftovers from any earlier crashed runs.
        _clean_stale_temp_wavs()
