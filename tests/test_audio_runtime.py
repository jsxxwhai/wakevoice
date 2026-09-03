"""Tests for project-local audio scratch dir and cleanup guards.

These must never touch real audio devices; they only exercise the helper that
decides where temp WAVs go and how stale files are cleaned up.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def test_play_pcm_writes_to_project_runtime_dir_not_os_temp(monkeypatch, tmp_path):
    """The temp WAV path must live under the project runtime dir, never OS temp."""
    from assistant import audio as A

    # Never open a real stream during this unit test.
    calls = []
    monkeypatch.setattr(A, "_play_wav_sync", lambda path, stop_event=None: calls.append(path))

    root = Path(__file__).resolve().parent.parent
    target = root / "runtime_tmp"
    monkeypatch.setattr(A, "_DEFAULT_RUNTIME_DIR", Path("runtime_tmp"))
    monkeypatch.setattr(A, "_project_runtime_dir", lambda: target)

    ok = A.play_pcm(b"\x00" * 100, sample_rate=16000)
    assert ok is True
    assert len(calls) == 1
    wav_path = Path(calls[0])
    # the scratch file was created inside the project runtime dir
    assert wav_path.parent == target
    assert wav_path.suffix == ".wav"
    # and was removed again after playback finished
    assert not wav_path.exists()


def test_cleanup_removes_stale_wavs(tmp_path):
    from assistant import audio as A

    # Create one fresh + one stale scratch file in a temp runtime dir.
    old = tmp_path / "openvoice_tts_old.wav"
    new = tmp_path / "openvoice_tts_new.wav"
    old.write_bytes(b"x" * 10)
    new.write_bytes(b"x" * 10)
    # force old mtime far in the past
    import os
    import time
    old_time = time.time() - 7200
    os.utime(old, (old_time, old_time))

    # redirect helper so cleanup scans tmp_path
    A._temp_dir = lambda: tmp_path

    A._cleanup_runtime(max_age_seconds=3600.0)
    assert not old.exists()
    assert new.exists()


def test_cleanup_enforces_total_size_cap(tmp_path):
    from assistant import audio as A

    # Create 3 files that together exceed the (patched) cap.
    old_cap = A._MAX_TEMP_BYTES
    A._MAX_TEMP_BYTES = 20
    try:
        f1 = tmp_path / "openvoice_tts_1.wav"
        f2 = tmp_path / "openvoice_tts_2.wav"
        f3 = tmp_path / "openvoice_tts_3.wav"
        f1.write_bytes(b"a" * 10)
        f2.write_bytes(b"b" * 10)
        f3.write_bytes(b"c" * 10)
        # stagger mtimes so deletion order is deterministic (oldest first)
        import os
        import time
        now = time.time()
        for i, f in enumerate((f1, f2, f3)):
            os.utime(f, (now - 100 + i, now - 100 + i))
        A._temp_dir = lambda: tmp_path
        A._cleanup_runtime(max_age_seconds=0.0)
        # total after cleanup must fit under the cap
        remaining = [f for f in tmp_path.glob("openvoice_tts_*.wav")]
        total = sum(f.stat().st_size for f in remaining)
        assert total <= 20
    finally:
        A._MAX_TEMP_BYTES = old_cap
