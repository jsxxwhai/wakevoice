"""Text-to-speech with emotional style support.

Engines:
- `edge`: Microsoft Edge neural TTS (online), supports SSML emotion/style tags.
- `pyttsx3`: offline SAPI fallback (Windows), no emotion, minimal memory.

Emotion map translates high-level emotions into edge-tts `mstts:express-as` styles.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Any

from ..audio import StopRequested, play_pcm

log = logging.getLogger(__name__)

# edge-tts emotion -> (style, styledegree) for the Xiaoxiao/standard voices.
EMOTION_MAP = {
    "neutral": ("general", "1.0"),
    "happy": ("cheerful", "1.0"),
    "sad": ("sad", "1.0"),
    "angry": ("angry", "1.0"),
    "fear": ("fearful", "1.0"),
    "excited": ("excited", "1.0"),
    "gentle": ("gentle", "1.0"),
    "calm": ("calm", "1.0"),
    "surprised": ("surprised", "1.0"),
}


class EdgeUnavailable(RuntimeError):
    """Raised when the online edge TTS cannot produce audio.

    Callers may catch this to fall back to an offline engine (pyttsx3)
    instead of failing silently.
    """



@dataclass
class TTSResult:
    """Result of a synthesis call."""
    engine: str
    duration_ms: int
    emotion: str | None


class BaseTTS:
    name = "base"

    def say(self, text: str, emotion: str | None = None, **kwargs) -> TTSResult:
        raise NotImplementedError

    def stop(self) -> None:
        """Interrupt any in-progress utterance."""

    def close(self) -> None:
        pass


def _run_async(coro) -> Any:
    """Run an async coroutine in a fresh loop (works from any thread)."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            try:
                loop.close()
            except Exception:
                pass


class EdgeTTS(BaseTTS):
    """Neural TTS via the `edge-tts` package. Emotional and natural."""

    name = "edge"

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "+0%",
                 pitch: str = "+0Hz", volume: str = "+0%", emotion_enabled: bool = True,
                 style: str = "general"):
        import edge_tts  # lazy import to keep startup memory low
        self._edge = edge_tts
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.volume = volume
        self.emotion_enabled = emotion_enabled
        self.style = style
        self._ready = True

    def _build_ssml(self, text: str, emotion: str | None) -> str:
        if not self.emotion_enabled:
            emotion = None
        style, degree = EMOTION_MAP.get(emotion or self.style or "neutral",
                                        EMOTION_MAP["neutral"])
        esc = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        prosody = f"rate='{self.rate}' pitch='{self.pitch}' volume='{self.volume}'"
        return (
            f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='zh-CN'>"
            f"<voice name='{self.voice}'>"
            f"<mstts:express-as style='{style}' styledegree='{degree}' xmlns:mstts='https://www.w3.org/2001/mstts'>"
            f"<prosody {prosody}>{esc}</prosody>"
            f"</mstts:express-as></voice></speak>"
        )

    async def _synthesize_pcm(self, ssml: str) -> bytes:
        """Synthesize SSML to raw 16-bit mono PCM (no playback)."""
        tts = self._edge.Communicate(ssml, voice=self.voice)
        chunks: list[bytes] = []
        async for chunk in tts.stream():
            if isinstance(chunk, dict) and chunk.get("type") == "audio":
                data = chunk.get("data")
                if data:
                    chunks.append(data)
        return b"".join(chunks)

    def synthesize(self, text: str, emotion: str | None = None) -> bytes:
        """Return raw 16-bit mono PCM (24000 Hz for edge voices)."""
        ssml = self._build_ssml(text, emotion)
        try:
            pcm = _run_async(self._synthesize_pcm(ssml))
            if not pcm:
                log.warning("edge-tts returned empty audio for: %.40s", text)
                raise EdgeUnavailable("edge-tts produced no audio")
            return pcm
        except EdgeUnavailable:
            raise
        except Exception as e:
            log.warning("edge-tts synthesis failed: %s", e)
            raise EdgeUnavailable(str(e)) from e

    def say(self, text: str, emotion: str | None = None, **kwargs) -> TTSResult:
        """Synthesize then play; honors a stop_event passed via kwargs."""
        stop_event: threading.Event | None = kwargs.get("stop_event")
        pcm = self.synthesize(text, emotion)
        # edge voices are 24 kHz mono 16-bit
        played = play_pcm(pcm, sample_rate=24000, stop_event=stop_event)
        if not played and stop_event is not None and stop_event.is_set():
            raise StopRequested()
        return TTSResult(self.name, 0, emotion)


class Pyttsx3TTS(BaseTTS):
    """Offline fallback using Windows SAPI. No emotion, tiny memory."""

    name = "pyttsx3"

    def __init__(self, rate: int = 175, volume: float = 0.9):
        import pyttsx3  # lazy import
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", rate)
        self._engine.setProperty("volume", volume)
        for voice in self._engine.getProperty("voices"):
            if "zh" in str(voice.id).lower() or "chinese" in str(voice.name).lower():
                try:
                    self._engine.setProperty("voice", voice.id)
                    break
                except Exception:
                    pass

    def say(self, text: str, emotion: str | None = None, **kwargs) -> TTSResult:
        stop_event: threading.Event | None = kwargs.get("stop_event")

        def _stop_if_needed():
            if stop_event is not None and stop_event.is_set():
                try:
                    self._engine.stop()
                except Exception:
                    pass

        self._engine.say(text)
        # runAndWait is blocking; poll the stop event in a timer so a stop key
        # cuts the utterance short.
        timer = None
        if stop_event is not None:
            timer = threading.Timer(0.05, _stop_if_needed)
            timer.daemon = True
            timer.start()
        try:
            self._engine.runAndWait()
        finally:
            if timer is not None:
                timer.cancel()
        return TTSResult(self.name, 0, emotion)

    def close(self) -> None:
        try:
            self._engine.stop()
        except Exception:
            pass


def get_tts_engine(config) -> BaseTTS:
    """Factory: instantiate the configured TTS engine (lazy, small footprint)."""
    engine_name = config.get("tts.engine", "edge")
    if engine_name == "edge":
        try:
            return EdgeTTS(
                voice=config.get("tts.voice", "zh-CN-XiaoxiaoNeural"),
                rate=config.get("tts.rate", "+0%"),
                pitch=config.get("tts.pitch", "+0Hz"),
                volume=config.get("tts.volume", "+0%"),
                emotion_enabled=config.get("tts.emotion_enabled", True),
                style=config.get("tts.style", "general"),
            )
        except Exception as e:
            log.warning("edge TTS unavailable (%s); falling back to pyttsx3", e)
            return Pyttsx3TTS()
    # pyttsx3 uses numeric values (int wpm rate, float 0.0-1.0 volume),
    # whereas edge-tts uses strings like "+0%". Only reuse a numeric rate if
    # the user set one; otherwise fall back to safe defaults.
    def _as_int_rate(v, default=175):
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    def _as_float_volume(v, default=0.9):
        try:
            f = float(v)
            return max(0.0, min(1.0, f))
        except (TypeError, ValueError):
            return default

    return Pyttsx3TTS(
        rate=_as_int_rate(config.get("tts.pyttsx3_rate", 175), 175),
        volume=_as_float_volume(config.get("tts.pyttsx3_volume", 0.9), 0.9),
    )
