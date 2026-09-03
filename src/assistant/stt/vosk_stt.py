"""Speech-to-text using Vosk (offline, small memory).

Supports both push-to-talk (hold Space to record) and hands-free input (the
recognizer finalizes an utterance after a configurable silence gap).
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

from ..core.errors import STTError

log = logging.getLogger(__name__)


class VoskSTT:
    """Offline recognizer backed by Vosk Kaldi models.

    The model is loaded lazily and can be swapped for a different language/model.
    """

    def __init__(self, model_dir: str | Path, sample_rate: int = 16000,
                 language: str = "zh-CN"):
        self.model_dir = Path(model_dir)
        self.sample_rate = sample_rate
        self.language = language
        self._model = None
        self._rec = None

    @property
    def model(self):
        if self._model is None:
            from vosk import KaldiRecognizer, Model  # lazy import
            if not self.model_dir.exists():
                raise STTError(f"Vosk model not found: {self.model_dir}")
            self._model = Model(str(self.model_dir))
            self._rec = KaldiRecognizer(self._model, self.sample_rate)
        return self._model, self._rec

    def recognize_bytes(self, pcm: bytes) -> str:
        """Finalize recognition on a raw 16-bit mono PCM buffer."""
        _, rec = self.model
        rec.AcceptWaveform(pcm)
        result = json.loads(rec.FinalResult())
        return result.get("text", "").strip()

    def _voice(self, silence_blocks: int = 8, stop_keys: list[str] | None = None):
        """Build the shared VoiceInput wrapper around this recognizer."""
        from .voice_input import VoiceInput
        _, rec = self.model
        return VoiceInput(rec, sample_rate=self.sample_rate,
                          silence_blocks=silence_blocks, stop_keys=stop_keys)

    def new_voice(self, silence_blocks: int = 8, stop_keys: list[str] | None = None):
        """Return a fresh VoiceInput bound to this recognizer (public helper)."""
        return self._voice(silence_blocks=silence_blocks, stop_keys=stop_keys)

    def listen_push_to_talk(self, hold_key: str = "space",
                            stop_keys: list[str] | None = None,
                            on_start: Callable | None = None,
                            on_stop: Callable | None = None) -> str:
        """Record while `hold_key` is held, return recognized text.

        An optional global stop key aborts recording at any time.
        """
        return self._voice(stop_keys=stop_keys).listen_push_to_talk(
            hold_key=hold_key, on_start=on_start, on_stop=on_stop)

    def listen_hands_free(self, silence_blocks: int = 8,
                          stop_keys: list[str] | None = None,
                          on_partial: Callable[[str], None] | None = None,
                          on_timeout: Callable[[], None] | None = None,
                          stop_key: str | None = None) -> str:
        """Listen hands-free; finalize after `silence_blocks` silent blocks."""
        return self._voice(silence_blocks=silence_blocks, stop_keys=stop_keys).listen_hands_free(
            on_partial=on_partial, on_timeout=on_timeout, stop_key=stop_key)

    def close(self) -> None:
        self._model = None
        self._rec = None
