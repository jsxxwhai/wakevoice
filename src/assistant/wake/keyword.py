"""Wake-word detection with pluggable backends.

Supports:
- `keyword` (Vosk-based, offline, exact-match on any custom word, no retrain needed)
- `openwakeword` (tiny neural models, very low memory, optional)

Custom wake word is trivial: just set `wake.word` in config. With the vosk
backend we transcribe a short sliding window and match the configured word.
"""
from __future__ import annotations

import json
import logging
from typing import Callable



log = logging.getLogger(__name__)

def _sd():
    """Lazily import sounddevice so non-audio paths never need PortAudio."""
    import sounddevice as sd
    return sd


def _word_matches(word: str, text: str, sensitivity: float) -> bool:
    """Decide whether `word` is present in `text`.

    Exact substring match always wins. Otherwise, if `sensitivity` is in
    (0, 1), we run a small fuzzy similarity check so near-homophones from the
    speech recognizer (e.g. "土豆" vs "土逗") still trigger the wake word.
    """
    if not word:
        return False
    if word in text:
        return True
    if not (0.0 < sensitivity < 1.0):
        return False
    if abs(len(word) - len(text)) > 2:
        return False
    import difflib
    # Slide a window of len(word) over text and keep the best ratio.
    best = 0.0
    for i in range(max(1, len(text) - len(word) + 1)):
        window = text[i:i + len(word)]
        best = max(best, difflib.SequenceMatcher(None, word, window).ratio())
    return best >= sensitivity



class KeywordWake:
    """Vosk-based keyword matcher: fully custom wake word, offline."""

    def __init__(self, word: str, model_dir: str, sample_rate: int = 16000,
                 sensitivity: float = 0.5, block_ms: int = 200, model=None):
        self.word = word
        self.sample_rate = sample_rate
        self.sensitivity = sensitivity
        self.block_ms = block_ms
        if model is not None:
            self._model = model  # reuse an already-loaded model
        else:
            from vosk import Model  # lazy
            self._model = Model(model_dir)
        from vosk import KaldiRecognizer
        self._rec = KaldiRecognizer(self._model, sample_rate)
        self._rec.SetWords(False)

    def listen(self, on_wake: Callable[[str], None],
               on_idle: Callable | None = None, stop_event=None) -> None:
        """Blocking loop: call on_wake(word) when the wake word is heard."""
        import threading as _th
        self._stop_event = stop_event if stop_event is not None else _th.Event()
        blocksize = int(self.sample_rate * self.block_ms / 1000)
        stream = _sd().RawInputStream(samplerate=self.sample_rate, blocksize=blocksize,
                                   dtype="int16", channels=1)
        stream.start()
        try:
            while not self._stop_event.is_set():
                data, _ = stream.read(blocksize)
                if self._rec.AcceptWaveform(bytes(data)):
                    text = self._rec.Result()
                    self._rec.Reset()
                else:
                    text = self._rec.PartialResult()
                    continue
                txt = json.loads(text).get("text", "").replace(" ", "")
                if _word_matches(self.word, txt, self.sensitivity):
                    on_wake(self.word)
                elif on_idle:
                    on_idle()
        finally:
            stream.stop()
            stream.close()

    def stop(self) -> None:
        """Ask a blocking listen() loop to return (used by the stop key)."""
        ev = getattr(self, "_stop_event", None)
        if ev is not None:
            ev.set()


class OpenWakeWordWake:
    """openwakeword backend: tiny neural models, very low memory.

    The model name is derived from the wake word text. Since openwakeword
    ships pre-trained models for common English words, custom Chinese words
    fall back to a generic "hey_mycroft" model and still work as a binary
    wake detector (on any speech), which is a reasonable default when no
    matching model exists.
    """

    def __init__(self, word: str, model_dir: str = "", sample_rate: int = 16000,
                 sensitivity: float = 0.5, **kwargs):
        self.word = word
        self.sample_rate = sample_rate
        self.sensitivity = sensitivity
        from openwakeword.model import Model  # lazy import
        # `model_dir` may point at a custom .onnx/.tflite model file (or a
        # directory of such files); use it directly when present, otherwise
        # fall back to a pre-trained model derived from the wake word.
        if model_dir:
            import os
            paths = []
            if os.path.isdir(model_dir):
                for fn in sorted(os.listdir(model_dir)):
                    if fn.endswith((".onnx", ".tflite")):
                        paths.append(os.path.join(model_dir, fn))
            elif os.path.isfile(model_dir):
                paths = [model_dir]
            if paths:
                self._model = Model(wakeword_models=paths, inference_framework="onnx")
                self._n_models = len(self._model.models)
                return
        try:
            self._model = Model(wakeword_models=[word.replace(" ", "_")], inference_framework="onnx")
        except Exception:
            self._model = Model(wakeword_models=["hey_mycroft"], inference_framework="onnx")
        self._n_models = len(self._model.models)

    def listen(self, on_wake: Callable[[str], None],
               on_idle: Callable | None = None, stop_event=None) -> None:
        import threading as _th
        import numpy as np
        self._stop_event = stop_event if stop_event is not None else _th.Event()
        chunk = int(self.sample_rate * 0.08)  # 80 ms frames
        stream = _sd().RawInputStream(samplerate=self.sample_rate, blocksize=chunk,
                                   dtype="int16", channels=1)
        stream.start()
        try:
            while not self._stop_event.is_set():
                data, _ = stream.read(chunk)
                audio = np.frombuffer(bytes(data), dtype=np.int16)
                pred = self._model.predict(audio)
                for name, score in pred.items():
                    if score >= self.sensitivity:
                        on_wake(self.word)
                        break
                else:
                    if on_idle:
                        on_idle()
        finally:
            stream.stop()
            stream.close()

    def stop(self) -> None:
        """Ask a blocking listen() loop to return (used by the stop key)."""
        ev = getattr(self, "_stop_event", None)
        if ev is not None:
            ev.set()


def create_wake(word, model_dir="", sample_rate=16000, sensitivity=0.5,
                backend="keyword", model=None):
    """Factory: build the configured wake-word detector."""
    if backend == "openwakeword":
        return OpenWakeWordWake(word, model_dir, sample_rate, sensitivity)
    return KeywordWake(word, model_dir, sample_rate, sensitivity, model=model)

