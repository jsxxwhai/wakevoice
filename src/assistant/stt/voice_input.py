"""Hands-free voice input for the assistant.

Captures microphone audio and returns the recognized text once the user stops
speaking for a configurable silence gap. A push-to-talk (hold Space) mode is
also provided as a fallback, and an optional global "stop" key can interrupt
both listening and TTS playback.

For testability the capture stream is obtained from a factory (`stream_factory`)
and the keyboard module from an optional argument, so unit tests can inject
fake audio frames without a real microphone.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable

import numpy as np

log = logging.getLogger(__name__)

def _sd():
    """Lazily import sounddevice so non-audio paths never need PortAudio."""
    import sounddevice as sd
    return sd

# 16-bit PCM silence threshold: RMS below this counts as "no speech".
_SILENCE_RMS = 250.0
# blocksize for capture (~100 ms at 16 kHz).
_CAPTURE_BLOCK = 1600
# Safety cap: if no speech is ever heard, stop after ~30 s of silence.
_TIMEOUT_SILENT_BLOCKS = 300
# Safety cap: hands-free listening never runs longer than ~120 s total even if
# background noise keeps the RMS gate open (prevents infinite busy loops that
# could exhaust memory/CPU when the mic hears the assistant's own TTS output).
_MAX_LISTEN_BLOCKS = 1200
# Push-to-talk recording cap (~120 s) so a stuck/held key cannot record
# forever and accumulate unbounded audio in RAM.
_MAX_PTT_BLOCKS = 1200


class VoiceInput:
    """Hands-free single-utterance recognizer.

    Uses a KaldiRecognizer fed incrementally with audio so that recognition
    keeps producing partial results; the utterance is finalized after a
    sustained silence (or when stop_keys is pressed).
    """

    def __init__(self, recognizer, sample_rate: int = 16000,
                 silence_blocks: int = 8, stop_keys: list[str] | None = None,
                 stream_factory=None):
        self._rec = recognizer
        self.sample_rate = sample_rate
        self.silence_blocks = max(1, int(silence_blocks))
        self.stop_keys = list(stop_keys or [])
        self._stop_event = threading.Event()
        self._stream_factory = stream_factory

    def _open_stream(self):
        if self._stream_factory is not None:
            return self._stream_factory()
        return _sd().RawInputStream(samplerate=self.sample_rate, blocksize=_CAPTURE_BLOCK,
                                 dtype="int16", channels=1)

    # ---- push-to-talk helper (uses its own stream) ----
    def listen_push_to_talk(self, hold_key: str = "space",
                            stop_keys: list[str] | None = None,
                            on_start: Callable | None = None,
                            on_stop: Callable | None = None) -> str:
        """Record while `hold_key` is held; return recognized text.

        This mirrors the previous VoskSTT.push_to_talk behaviour but uses the
        incremental recognizer so it stays consistent with hands-free input.
        The optional global stop key aborts recording at any time.
        """
        import keyboard
        self._rec.Reset()
        self._stop_event.clear()
        while not keyboard.is_pressed(hold_key):
            if self._is_stop_pressed(keyboard):
                log.info("stop key pressed; aborting push-to-talk")
                return ""
            time.sleep(0.02)
        if on_start:
            on_start()
        chunks: list[bytes] = []
        stream = self._open_stream()
        stream.start()
        try:
            blocks = 0
            while keyboard.is_pressed(hold_key):
                if self._is_stop_pressed(keyboard):
                    log.info("stop key pressed; aborting push-to-talk")
                    return ""
                data, _ = stream.read(_CAPTURE_BLOCK)
                chunks.append(bytes(data))
                blocks += 1
                if blocks >= _MAX_PTT_BLOCKS:
                    log.warning("push-to-talk hit max duration; forcing end")
                    break
        finally:
            stream.stop()
            stream.close()
        if on_stop:
            on_stop()
        if not chunks:
            return ""
        self._rec.Reset()
        for c in chunks:
            self._rec.AcceptWaveform(c)
        result = json.loads(self._rec.FinalResult())
        return result.get("text", "").strip()

    # ---- hands-free ----
    def _is_stop_pressed(self, keyboard) -> bool:
        """True if a local stop event fired or any stop key is held."""
        if self._stop_event.is_set():
            return True
        if not self.stop_keys:
            return False
        for k in self.stop_keys:
            try:
                if keyboard.is_pressed(k):
                    return True
            except Exception:
                continue
        return False

    def stop(self) -> None:
        """Programmatically stop listening/speaking from another thread."""
        self._stop_event.set()

    @staticmethod
    def _is_speech(data: bytes) -> bool:
        audio = np.frombuffer(data, dtype=np.int16).astype(np.float64)
        rms = float(np.sqrt(np.mean(audio * audio))) if audio.size else 0.0
        return rms >= _SILENCE_RMS

    def listen_hands_free(self, on_partial: Callable[[str], None] | None = None,
                          on_timeout: Callable[[], None] | None = None,
                          stop_key=None, keyboard=None) -> str:
        """Listen until a silence gap (or stop key) ends the utterance."""
        if keyboard is None:
            import keyboard  # type: ignore
        self._rec.Reset()
        # A stop requested before listen() begins (pre-set) must still abort.
        if not self._stop_event.is_set():
            self._stop_event.clear()
        # also honor an explicitly passed single stop key (e.g. from app config)
        self.stop_keys = list(self.stop_keys) + ([str(stop_key).lower()] if stop_key else [])
        if hasattr(self._rec, "SetWords"):
            try:
                self._rec.SetWords(True)
            except Exception:
                pass
        silence = 0
        saw_speech = False
        total_blocks = 0
        last_partial = ""
        stream = self._open_stream()
        stream.start()
        try:
            while True:
                if self._is_stop_pressed(keyboard):
                    log.info("stop key pressed; aborting listening")
                    return ""
                data, _ = stream.read(_CAPTURE_BLOCK)
                total_blocks += 1
                is_speech = self._is_speech(data)

                if is_speech:
                    silence = 0
                    saw_speech = True
                else:
                    silence += 1

                # Hard safety budget: never listen forever. Even with constant
                # background audio this ends the turn so the loop can recover
                # instead of spinning (protects against self-trigger feedback).
                if total_blocks >= _MAX_LISTEN_BLOCKS:
                    log.warning("hands-free listen hit max duration; forcing end")
                    break

                self._rec.AcceptWaveform(data)

                if is_speech or silence <= 2:
                    partial = ""
                    try:
                        partial = json.loads(self._rec.PartialResult()).get("partial", "")
                    except Exception:
                        partial = ""
                    if partial and partial != last_partial:
                        last_partial = partial
                        if on_partial:
                            on_partial(partial)

                # ended: saw speech then enough sustained silence
                if saw_speech and silence >= self.silence_blocks:
                    break
                # aborted before any speech
                if not saw_speech and silence >= max(_TIMEOUT_SILENT_BLOCKS,
                                                     self.silence_blocks * 5):
                    if on_timeout:
                        on_timeout()
                    return ""
        finally:
            stream.stop()
            stream.close()

        try:
            final_text = json.loads(self._rec.FinalResult()).get("text", "").strip()
        except Exception:
            final_text = ""
        return final_text
