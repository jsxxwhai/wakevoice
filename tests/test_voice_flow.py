"""Tests for the hands-free voice flow (no real mic / no audio device).

Uses fake recognizers and fake capture streams to exercise VoiceInput's
silence-gap detection, timeout, and stop-key abort, plus Assistant voice-mode
configuration helpers.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

from assistant.stt.voice_input import _CAPTURE_BLOCK, VoiceInput


def _speech_block(amp=20000):
    """A loud 16-bit PCM block (counts as speech)."""
    arr = (np.ones(_CAPTURE_BLOCK, dtype=np.int16) * amp).astype(np.int16)
    return arr.tobytes()


def _silent_block():
    return b"\x00" * (_CAPTURE_BLOCK * 2)


class FakeRec:
    """Minimal recognizer recording what it receives."""

    def __init__(self, final_text="你好世界"):
        self.final_text = final_text
        self.accepted = b""
        self.reset_count = 0
        self.setwords = False

    def Reset(self):
        self.reset_count += 1

    def AcceptWaveform(self, data):
        self.accepted += data

    def PartialResult(self):
        return json.dumps({"partial": "你好"})

    def FinalResult(self):
        return json.dumps({"text": self.final_text})

    def SetWords(self, flag):
        self.setwords = flag


class FakeStream:
    """Serves pre-arranged frames, then raises StopIteration-like exhaustion."""

    def __init__(self, frames):
        self.frames = list(frames)
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self):
        self.started = True

    def read(self, n):
        if not self.frames:
            # keep handing silence so loops with silence_blocks logic terminate
            return _silent_block(), None
        return self.frames.pop(0), None

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


class FakeKeyboard:
    def __init__(self, stop_pressed=False):
        self.stop_pressed = stop_pressed

    def is_pressed(self, key):
        return self.stop_pressed


def _voice(frames, silence_blocks=4, stop_keys=None, final="你好世界"):
    rec = FakeRec(final_text=final)
    vi = VoiceInput(rec, sample_rate=16000, silence_blocks=silence_blocks,
                    stop_keys=stop_keys, stream_factory=lambda: FakeStream(frames))
    return vi, rec


def test_hands_free_returns_after_silence_gap():
    frames = [_speech_block()] * 3 + [_silent_block()] * 6
    vi, rec = _voice(frames, silence_blocks=5)
    out = vi.listen_hands_free()
    assert out == "你好世界"
    assert rec.accepted  # audio was fed


def test_hands_free_timeout_when_no_speech():
    # silence_blocks=4 but FakeStream never runs out; it keeps handing silence,
    # so the no-speech timeout needs ~ max(30, 4*5)=30 silent blocks.
    frames = []
    vi, _rec = _voice(frames, silence_blocks=30)
    fired = []
    out = vi.listen_hands_free(on_timeout=lambda: fired.append(True))
    assert out == ""
    assert fired == [True]


def test_hands_free_stop_key_aborts():
    frames = [_speech_block()] * 2
    vi, _rec = _voice(frames, silence_blocks=4, stop_keys=["esc"])
    class KB:
        def is_pressed(self, key):
            return True
    out = vi.listen_hands_free(keyboard=KB())
    assert out == ""


def test_is_speech_classification():
    assert VoiceInput._is_speech(_speech_block()) is True
    assert VoiceInput._is_speech(_silent_block()) is False


def test_push_to_talk_returns_text(monkeypatch):
    rec = FakeRec(final_text="打开记事本")
    frames = [_speech_block()] * 2
    vi = VoiceInput(rec, silence_blocks=4, stream_factory=lambda: FakeStream(frames))

    # patch the keyboard module used by push_to_talk: first call is_pressed
    # returns False (wait for press) once, then True (hold/record) for a while,
    # then False (release) so the loop ends.
    class KB:
        def __init__(self):
            self.n = 0
        def is_pressed(self, key):
            self.n += 1
            if self.n == 1:
                return False       # not yet pressed -> wait
            if self.n <= 4:
                return True        # held -> record
            return False           # released -> stop
    kb = KB()
    monkeypatch.setitem(sys.modules, "keyboard", kb)
    out = vi.listen_push_to_talk(hold_key="space")
    assert out == "打开记事本"


# ---- Assistant background TTS worker / stop key integration ----

def _bare_assistant(monkeypatch):
    """An Assistant instance that never touches audio/mic/network."""
    import collections
    import threading as _t

    from assistant.core.app import Assistant

    a = Assistant.__new__(Assistant)
    from assistant.core.config import Config
    a.config = Config()
    a._stop_exit = _t.Event()
    a._stopped = _t.Event()
    a._tts_stop = _t.Event()
    a._tts_queue = collections.deque()
    a._speaking = _t.Event()
    a._tts_thread = None
    a._stop_thread = None

    class _FakeTTS:
        def __init__(self):
            self.said = []
        def say(self, text, emotion=None, stop_event=None):
            self.said.append(text)
        def stop(self):
            pass
        def close(self):
            pass

    a._tts = _FakeTTS()
    return a


def test_tts_worker_drains_queue(monkeypatch):
    """The background worker speaks queued lines and clears _speaking."""
    import threading as _t
    import time as _time
    a = _bare_assistant(monkeypatch)

    # hold the queue: speak() must not auto-start the worker here
    monkeypatch.setattr(a, "_start_tts_worker", lambda: None)
    a.speak("第一句")
    a.speak("第二句")
    assert len(a._tts_queue) == 2

    # spawn the real worker thread (what _start_tts_worker does)
    worker = _t.Thread(target=a._tts_worker, daemon=True)
    worker.start()
    end = _time.monotonic() + 3.0
    while _time.monotonic() < end and a._tts_queue:
        _time.sleep(0.02)
    assert a._tts.said == ["第一句", "第二句"]
    assert not a._tts_queue
    assert not a._speaking.is_set()
    a._stop_exit.set()
    worker.join(timeout=1.0)


def test_speak_noop_after_shutdown(monkeypatch):
    """Once _stop_exit is set (shutdown), speak() must not enqueue."""
    a = _bare_assistant(monkeypatch)
    monkeypatch.setattr(a, "_start_tts_worker", lambda: None)
    a._stop_exit.set()
    a.speak("不要说话")
    assert len(a._tts_queue) == 0


def test_await_quiet_waits_while_speaking(monkeypatch):
    """_await_quiet returns only after the assistant stops talking."""
    import threading as _t
    import time as _time
    a = _bare_assistant(monkeypatch)
    a._speaking.set()

    def _release():
        _time.sleep(0.15)
        a._speaking.clear()

    _t.Thread(target=_release, daemon=True).start()
    start = _time.monotonic()
    a._await_quiet(settle=0.0)
    assert _time.monotonic() - start >= 0.1
    assert not a._speaking.is_set()


def test_wait_until_idle_waits_while_speaking(monkeypatch):
    """_wait_until_idle blocks while speech is playing, then returns."""
    import threading as _t
    import time as _time
    a = _bare_assistant(monkeypatch)
    a._speaking.set()

    def _clear():
        _time.sleep(0.15)
        a._speaking.clear()

    _t.Thread(target=_clear, daemon=True).start()
    start = _time.monotonic()
    a._wait_until_idle(timeout=2.0)
    assert _time.monotonic() - start >= 0.1
    assert not a._speaking.is_set()


def test_stop_listener_disabled_starts_nothing(monkeypatch):
    """stop_enabled=false must not start the stop-key watcher thread."""
    from assistant.core.app import Assistant
    a = Assistant()
    a.config.set("voice.stop_enabled", False)
    monkeypatch.setattr(a, "_stop_keys", list)
    a._start_stop_listener()
    assert getattr(a, "_stop_thread", None) is None


def test_stop_listener_absent_keyboard_module(monkeypatch):
    """Missing keyboard module must degrade silently (no thread)."""
    from assistant.core.app import Assistant
    a = Assistant()
    a.config.set("voice.stop_enabled", True)
    a.config.set("voice.stop_key", "esc")
    assert a._stop_keys() == ["esc"]
    import builtins
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "keyboard":
            raise ImportError("no keyboard here")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    a._start_stop_listener()
    assert getattr(a, "_stop_thread", None) is None


# ---- push-to-talk stop key ----
def test_push_to_talk_stop_key_aborts(monkeypatch):
    """The global stop key interrupts push-to-talk recording too."""
    import sys
    rec = FakeRec(final_text="不该识别")
    frames = [_speech_block()] * 2
    vi = VoiceInput(rec, silence_blocks=4, stop_keys=["esc"],
                    stream_factory=lambda: FakeStream(frames))

    class KB:
        def is_pressed(self, key):
            # hold key not pressed yet; stop key is pressed -> abort
            return key != "space"

    monkeypatch.setitem(sys.modules, "keyboard", KB())
    out = vi.listen_push_to_talk(hold_key="space")
    assert out == ""


# ---- Assistant voice config helpers ----

def test_assistant_voice_helpers(monkeypatch):
    from assistant.core.app import Assistant
    a = Assistant()
    a.config.set("voice.mode", "hands_free")
    assert a._voice_mode() == "hands_free"
    a.config.set("voice.mode", "push_to_talk")
    assert a._voice_mode() == "push_to_talk"

    # silence 1.5s at 16kHz -> block=0.1s -> 15 blocks
    a.config.set("stt.sample_rate", 16000)
    a.config.set("voice.silence_seconds", 1.5)
    assert a._silence_seconds_to_blocks() == 15

    # stop enabled default -> ['esc']; disabled -> []
    a.config.set("voice.stop_enabled", True)
    a.config.set("voice.stop_key", "esc")
    assert a._stop_keys() == ["esc"]
    a.config.set("voice.stop_enabled", False)
    assert a._stop_keys() == []


def test_speak_stop_speaking(monkeypatch):
    """speak queues text; stop_speaking clears queue and signals stop."""
    from assistant.core.app import Assistant

    class FakeTTS:
        def __init__(self):
            self.said = []
            self.stopped = False
        def say(self, text, emotion=None, stop_event=None):
            self.said.append(text)
        def stop(self):
            self.stopped = True
        def close(self):
            pass

    a = Assistant.__new__(Assistant)
    import collections
    import threading as _t
    a._tts_stop = _t.Event()
    a._tts_queue = collections.deque()
    a._speaking = _t.Event()
    a._tts_thread = None
    a._tts = FakeTTS()
    # Avoid spawning the real background thread during the unit test.
    monkeypatch.setattr(a, "_start_tts_worker", lambda: None)
    a.speak("你好")
    a.speak("在吗")
    assert len(a._tts_queue) == 2
    a.stop_speaking()
    assert len(a._tts_queue) == 0
    assert a._tts_stop.is_set()


# ---- single-key abort_now / programmatic stop ----


def test_stop_aborts_active_voice_listen(monkeypatch):
    """_on_stop_press must abort the VoiceInput instance currently listening."""
    import threading as _t

    from assistant.core.app import Assistant
    rec = FakeRec(final_text="不该识别")
    frames = [_speech_block()] * 2
    from assistant.stt.voice_input import VoiceInput
    vi = VoiceInput(rec, silence_blocks=4,
                    stream_factory=lambda: FakeStream(frames))

    a = Assistant.__new__(Assistant)
    a.config = None
    a._stopped = _t.Event()
    a._tts_stop = _t.Event()
    a._tts_queue = __import__('collections').deque()
    a._tts = None
    a._active_voice = vi
    a._abort_cbs = []
    a.stop_speaking = lambda: None
    a._on_stop_press()
    assert vi._stop_event.is_set()


def test_abort_now_stops_speech_and_notifies_listeners(monkeypatch):
    """abort_now must stop speech and fire registered abort callbacks."""
    import collections
    import threading as _t

    from assistant.core.app import Assistant
    a = Assistant.__new__(Assistant)
    a.config = None
    a._stopped = _t.Event()
    a._stop_exit = _t.Event()
    a._tts_stop = _t.Event()
    a._tts_queue = collections.deque()
    a._tts = None
    a._active_voice = None
    a._abort_cbs = []
    fired = []
    a._abort_cbs.append(lambda: fired.append(True))
    a.stop_speaking = lambda: a._tts_stop.set()
    a.abort_now()
    assert a._stopped.is_set()
    assert a._tts_stop.is_set()
    assert fired == [True]
