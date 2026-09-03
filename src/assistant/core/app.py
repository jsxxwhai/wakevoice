"""Main application: wires config, skills, agents, extension, TTS, STT, wake word."""
from __future__ import annotations

import logging
import threading
import time
from collections import deque

from ..agents.hub import Agent, AgentContext, AgentHub
from ..agents.llm_agent import LLMAgent
from ..audio import StopRequested
from ..connectors.client import MCPManager
from ..paths import resolve
from ..skills import apps as apps_skill
from ..skills import control as control_skill
from ..skills import mcp_bridge
from ..skills import plugins as plugin_loader
from ..skills import system as system_skill
from ..skills import timeinfo as time_skill
from ..skills.base import SkillRegistry
from .config import Config
from .llm import LLMClient
from .logging import setup_logging
from .memory_ctx import Memory

log = logging.getLogger(__name__)


class _StopWatch:
    """Small reusable polling helper for a physical stop key.

    Keeps one lazy keyboard import and exposes ny_pressed() so the
    assistant and its voice input loops can share the same stop key.
    """

    def __init__(self, stop_keys_callable):
        self._keys_callable = stop_keys_callable
        self._kb = None

    def kb(self):
        if self._kb is None:
            try:
                import keyboard
                self._kb = keyboard
            except Exception:
                self._kb = False
        return self._kb

    def keys(self) -> list[str]:
        try:
            return self._keys_callable() or []
        except Exception:
            return []

    def any_pressed(self) -> bool:
        kb = self.kb()
        if not kb:
            return False
        for k in self.keys():
            try:
                if kb.is_pressed(k):
                    return True
            except Exception:
                continue
        return False

    def reset(self) -> None:
        """Clear transient state between runs.

        Kept simple and idempotent: there is no per-run state cached in
        this helper today, but entry points call reset() so a future
        implementation can drop any held key state here without callers
        having to change.
        """
        self._kb = None


class Assistant:

    """Top-level assistant object. Lazy-loads heavy subsystems."""

    def __init__(self, config_path: str | None = None):
        self.config = Config(config_path)
        setup_logging(self.config.get("app.log_level", "INFO"))
        self._init_runtime_dir()
        self.skills = SkillRegistry()
        self.agents = AgentHub(max_workers=self.config.get("agents.max_workers", 4))
        self.extension = MCPManager()
        self._tts = None
        self._stt = None
        self._wake = None
        self._llm = None
        self._memory = Memory(max_turns=self.config.get("memory.max_turns", 10))
        self._memory_path = self.config.get("memory.file", "")
        self._screen_reader = None
        # --- voice-loop state ---
        self._tts_thread: threading.Thread | None = None
        self._tts_stop = threading.Event()
        self._tts_queue: deque[tuple[str, str | None]] = deque()
        self._speaking = threading.Event()       # True while TTS is producing sound
        self._stopped = threading.Event()        # set when user pressed stop key
        self._stop_exit = threading.Event()       # stop-listener shutdown flag (independent of TTS)
        self._stop_thread: threading.Thread | None = None   # stop-key watcher thread
        self._abort_cbs: list = []               # listeners to notify on stop press
        self._active_voice = None                 # VoiceInput currently listening
        self._stop_watch = _StopWatch(self._stop_keys)   # reusable polling helpers
        if self._memory_path:
            self._memory.load(self._memory_path)
        self._register_builtins()
        self._load_extension_servers()

    def _init_runtime_dir(self) -> None:
        """Anchor audio/runtime scratch files inside the project, then tidy."""
        try:
            from .. import audio as audio_mod
            rd_cfg = self.config.get("safety.runtime_dir", "runtime_tmp") or "runtime_tmp"
            rd = resolve(str(rd_cfg)) or rd_cfg
            audio_mod.set_runtime_dir(str(rd))
            if self.config.get("safety.cleanup_on_start", True):
                audio_mod._cleanup_runtime()
        except Exception as e:
            log.warning("runtime dir init failed: %s", e)

    # ---- subsystems (lazy) ----
    @property
    def tts(self):
        if self._tts is None:
            from ..tts.engine import get_tts_engine
            self._tts = get_tts_engine(self.config)
        return self._tts

    @property
    def stt(self):
        if self._stt is None:
            from ..stt.vosk_stt import VoskSTT
            model = resolve(str(self.config.get("stt.model_dir", "vosk-model-small-cn-0.22") or "vosk-model-small-cn-0.22"))
            self._stt = VoskSTT(
                model,
                self.config.get("stt.sample_rate", 16000),
                self.config.get("stt.language", "zh-CN"),
            )
        return self._stt

    @property
    def wake(self):
        if self._wake is None:
            from ..core.errors import WakeWordError
            from ..wake.keyword import create_wake
            model = resolve(str(self.config.get("stt.model_dir", "vosk-model-small-cn-0.22") or "vosk-model-small-cn-0.22"))
            backend = self.config.get("wake.engine", "keyword")
            valid = self.config.get("wake.backends", ["keyword", "openwakeword"]) or []
            if backend not in valid:
                raise WakeWordError(
                    f"unknown wake engine {backend!r}; choose one of {valid}")
            if backend == "openwakeword":
                self._wake = create_wake(
                    self.config.get("wake.word", "你好伙伴"), model,
                    sensitivity=self.config.get("wake.sensitivity", 0.5),
                    backend="openwakeword")
            else:
                shared = self.stt.model[0]  # reuse STT model to save memory
                self._wake = create_wake(
                    self.config.get("wake.word", "你好伙伴"), model,
                    sensitivity=self.config.get("wake.sensitivity", 0.5),
                    backend="keyword", model=shared)
        return self._wake

    def _llm_available(self) -> bool:
        """LLM is usable only when enabled AND (base_url or an API key) is set.

        This avoids a cold 20s timeout when no key is configured: the assistant
        falls back to the local skills reply immediately instead.
        """
        if not self.config.get("llm.enabled", True):
            return False
        if self.config.get("llm.base_url"):
            return True
        import os
        key_env = self.config.get("llm.api_key_env", "OPENAI_API_KEY")
        return bool(os.environ.get(key_env))

    @property
    def llm(self):
        if not self._llm_available():
            return None
        if self._llm is None:
            self._llm = LLMClient(
                base_url=self.config.get("llm.base_url"),
                api_key_env=self.config.get("llm.api_key_env", "OPENAI_API_KEY"),
                model=self.config.get("llm.model", "gpt-4o-mini"),
                temperature=self.config.get("llm.temperature", 0.7),
                timeout=self.config.get("llm.timeout", 20.0),
            )
        return self._llm

    def _load_extension_servers(self) -> None:
        """Auto-discover and configure extension servers from config."""
        if not self.config.get("extension.auto_discover", True):
            return
        servers = self.config.get("extension.servers", []) or []
        if servers:
            try:
                self.extension.load(servers)
                log.info("loaded %d extension server(s)", len(servers))
            except Exception as e:
                log.warning("failed to load extension servers: %s", e)

    def _register_builtins(self) -> None:
        # honor skills.enabled: when false, skip all built-in skills (the LLM
        # agent fallback still works, but no local capability is registered).
        if not self.config.get("skills.enabled", True):
            log.info("skills disabled via config; no built-in skills registered")
            self._register_default_agent()
            return

        disabled = set(self.config.get("skills.disabled", []) or [])
        self.skills.register(apps_skill.open_app_skill())
        control_skill.register_control_skills(self.skills)
        system_skill.register_system_skills(self.skills)
        self.skills.register(mcp_bridge.make_mcp_skill(self.extension))
        # offline time/date (always available, no LLM key needed)
        time_skill.register_time_skills(self.skills)
        # screen-reading skill
        self.skills.register_func(
            name="read_screen", description="截图并识别屏幕上的文字",
            patterns=["读屏幕", "看屏幕", "屏幕内容"],
            keywords=["读屏幕", "看屏幕", "屏幕"],
        )(self._run_read_screen)
        self._register_default_agent()

        # honor skills.disabled by unregistering those skills after registration
        for name in disabled:
            self.skills.unregister(name)

        # local plugin auto-discovery (drop .py files into the skills dir)
        plugin_dir = str(resolve(str(self.config.get("skills.plugin_dir", "skills") or "skills")))
        try:
            plugin_loader.load_plugin_dir(self.skills, plugin_dir)
        except Exception as e:
            log.warning("plugin loading failed: %s", e)

    def _register_default_agent(self) -> None:
        """Register the default agent (used even when skills are off)."""
        name = self.config.get("agents.default_agent", "general")
        self.agents.register(Agent(
            name=name, role="通用助手",
            description="处理日常对话和内置技能路由"))

    # ================= speech / TTS worker =================
    def _ensure_voice_runtime(self) -> None:
        """Start the TTS worker and the stop-key listener (idempotent)."""
        self._start_tts_worker()
        self._start_stop_listener()

    def _start_tts_worker(self) -> None:
        """Ensure the single background TTS worker is running.

        Speech runs off the main thread so the assistant can keep listening
        and a stop key can interrupt the current utterance instantly.
        """
        if self._tts_thread is not None and self._tts_thread.is_alive():
            return
        self._stop_exit.clear()
        self._tts_stop.clear()
        self._tts_thread = threading.Thread(
            target=self._tts_worker, name="openvoice-tts", daemon=True)
        self._tts_thread.start()

    def _tts_worker(self) -> None:
        """Drain the speech queue, one utterance at a time.

        A stop key only interrupts the current utterance; it must NOT kill
        the thread, otherwise the next speak() would spawn a fresh worker and
        the stop listener would lose its meaning. The worker exits only when
        `_stop_exit` is set during shutdown.
        """
        while not self._stop_exit.is_set():
            try:
                text, emotion = self._tts_queue.popleft()
            except IndexError:
                # idle: brief wait for new speech (also honors shutdown)
                self._stop_exit.wait(0.1)
                continue
            if not text or not str(text).strip():
                continue
            self._speaking.set()
            # a fresh utterance must not be cut by a previous interrupt
            self._tts_stop.clear()
            try:
                self.tts.say(text, emotion, stop_event=self._tts_stop)
            except StopRequested:
                log.info("tts interrupted by stop key")
            except Exception as e:
                log.warning("tts say failed: %s", e)
                # If the online edge TTS cannot produce audio (no network,
                # endpoint issue), fall back to the offline pyttsx3 engine
                # once so the assistant still speaks.
                try:
                    from ..tts.engine import EdgeUnavailable, Pyttsx3TTS
                    if isinstance(e, EdgeUnavailable) or (self._tts is not None and getattr(self._tts, "name", "") == "edge"):
                        try:
                            self._tts.close()
                        except Exception:
                            pass
                        self._tts = Pyttsx3TTS(
                            rate=int(self.config.get("tts.pyttsx3_rate", 175) or 175),
                            volume=float(self.config.get("tts.pyttsx3_volume", 0.9) or 0.9),
                        )
                        log.warning("edge TTS failed; fell back to offline pyttsx3")
                        self.tts.say(text, emotion, stop_event=self._tts_stop)
                except Exception as fb:
                    log.warning("tts fallback also failed: %s", fb)
            finally:
                self._speaking.clear()

    def _wait_until_idle(self, timeout: float = 5.0) -> None:
        """Block until the assistant is no longer speaking and its queue is
        empty (used before returning to wake listening or shutting down).
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self._speaking.is_set() and not self._tts_queue:
                return
            time.sleep(0.05)

    def stop_speaking(self) -> None:
        """Immediately interrupt any in-progress TTS and clear the queue."""
        self._tts_stop.set()
        self._tts_queue.clear()
        if getattr(self, "_tts", None) is not None:
            try:
                self._tts.stop()
            except Exception:
                pass

    def speak(self, text: str, emotion: str | None = None) -> None:
        """Queue text for speech (non-blocking, interruptible)."""
        log.info("reply: %s", text)
        if not text or not str(text).strip():
            return
        stop_exit = getattr(self, "_stop_exit", None)
        if stop_exit is not None and stop_exit.is_set():
            # shutting down / already stopped: never enqueue new speech
            return
        self._tts_queue.append((str(text), emotion))
        self._start_tts_worker()

    # ================= listening / conversation =================
    def _silence_seconds_to_blocks(self) -> int:
        secs = float(self.config.get("voice.silence_seconds", 1.5) or 1.5)
        sr = int(self.config.get("stt.sample_rate", 16000))
        block_secs = 1600.0 / float(sr)  # capture block length in seconds
        return max(2, round(secs / block_secs))

    def _voice_mode(self) -> str:
        return str(self.config.get("voice.mode", "hands_free") or "hands_free").lower()

    def _stop_keys(self) -> list[str]:
        if not self.config.get("voice.stop_enabled", True):
            return []
        key = str(self.config.get("voice.stop_key", "esc") or "").strip().lower()
        return [key] if key else []

    def _listen_one(self) -> str:
        """Capture one utterance using the configured voice mode.

        Hands-free: speak and pause; the recognizer ends the utterance after a
        silence gap. Push-to-talk: hold the configured key while speaking.
        Returns the recognized text (possibly empty if aborted).
        """
        mode = self._voice_mode()
        stop_keys = self._stop_keys()
        if mode == "hands_free":
            # Build one VoiceInput and keep it on self so a stop-key press
            # (abort callback) can abort the exact in-progress listen.
            self._active_voice = self.stt.new_voice(
                silence_blocks=self._silence_seconds_to_blocks(), stop_keys=stop_keys)
            return self._active_voice.listen_hands_free(
                on_partial=None,
                on_timeout=None,
                stop_key=stop_keys[0] if stop_keys else None,
            )
        # push_to_talk (hold a key)
        hold_key = str(self.config.get("voice.hold_key", "space") or "space")
        return self.stt.listen_push_to_talk(hold_key=hold_key, stop_keys=stop_keys)

    def _await_quiet(self, settle: float = 0.35) -> None:
        """Self-trigger guard for hands-free mode.

        Keep the microphone closed while the assistant is still talking so it
        never "hears" and re-processes its own reply. Push-to-talk is
        user-initiated (a held key), so it does not need this wait.
        """
        if self._voice_mode() != "hands_free":
            return
        while (self._speaking.is_set() or self._tts_queue) and not self._stopped.is_set():
            time.sleep(0.05)
        if settle > 0 and not self._stopped.is_set():
            time.sleep(settle)

    def _conversation_loop(self) -> None:
        """Wake -> multi-turn voice dialogue until exit phrase / stop key."""
        exit_words = ["再见", "拜拜", "退出", "关闭", "结束", "不用了", "没事了"]
        while True:
            if self._stopped.is_set():
                self._stopped.clear()
                break
            self._await_quiet()
            if self._stopped.is_set():
                self._stopped.clear()
                break
            text = self._listen_one()
            if self._stopped.is_set():
                self._stopped.clear()
                break
            if not text:
                continue
            log.info("heard: %s", text)
            if any(k in text for k in exit_words):
                self.speak("好的，再见啦。")
                # finish the farewell before returning to wake listening
                self._wait_until_idle()
                break
            result = self.handle_text(text)
            if not result:
                continue
            reply, emotion = result
            # When an answer is spoken the loop returns to listening, so a
            # user can simply speak again without pressing anything.
            self.speak(reply, emotion)
            # keep the mic closed until the reply is fully spoken (feedback)
            self._await_quiet()

    def _start_stop_listener(self) -> None:
        """Start the single global stop-key watcher thread (idempotent)."""
        stop_thread = getattr(self, "_stop_thread", None)
        if stop_thread is not None and stop_thread.is_alive():
            return
        stop_keys = self._stop_keys()
        if not stop_keys:
            return
        if not self._stop_watch.kb():
            log.warning("stop-key listener unavailable")
            return

        def _watch():
            while not self._stop_exit.is_set():
                try:
                    if self._stop_watch.any_pressed():
                        log.info("stop key pressed")
                        self._on_stop_press()
                        # debounce; avoid repeated triggers while held
                        self._stop_exit.wait(0.3)
                except Exception:
                    self._stop_exit.wait(0.05)
                self._stop_exit.wait(0.03)

        self._stop_thread = threading.Thread(
            target=_watch, name="openvoice-stop", daemon=True)
        self._stop_thread.start()

    def _on_stop_press(self) -> None:
        """Central stop-key action: abort speech + all in-flight listening."""
        self._stopped.set()
        self.stop_speaking()
        # abort the VoiceInput instance currently listening (if any)
        vi = getattr(self, "_active_voice", None)
        if vi is not None:
            try:
                vi.stop()
            except Exception:
                pass
        # signal every registered abort callback (wake-listen, ...)
        for cb in list(getattr(self, "_abort_cbs", [])):
            try:
                cb()
            except Exception:
                pass

    def abort_now(self) -> None:
        """Public API: immediately stop speaking and abort current listening."""
        self._on_stop_press()

    def _say_hello(self) -> None:
        name = self.config.get("app.name", "OpenVoice")
        if name == "OpenVoice":
            self.speak("我在。")
        else:
            self.speak("在的。")

    # ================= public entry points =================
    def run_once(self) -> None:
        """Single wake-free exchange: say one command, get one answer."""
        self._stopped.clear()
        self._stop_watch.reset()
        self._abort_cbs = []
        self._ensure_voice_runtime()
        if self._voice_mode() == "hands_free":
            self.speak("我在，请直接对我说话，说完停一下。")
        else:
            self.speak("我在，请按住空格键对我说话，说完松开。")
        self._conversation_loop()

    def run_wake_loop(self) -> None:
        """Continuous wake-word loop.

        Say the wake word -> assistant answers "我在。" -> speak your command
        hands-free (pause to finish) or hold the configured key. Press the
        stop key at any time to interrupt.
        """
        self._stopped.clear()
        self._stop_watch.reset()
        self._abort_cbs = []
        self._ensure_voice_runtime()
        self.speak("唤醒词已就绪，叫我" + self.config.get("wake.word", "你好伙伴") + "吧。")
        # never let our own startup announcement re-trigger the wake word
        self._wait_until_idle()

        def on_wake(word):
            log.info("woke by: %s", word)
            if self._stopped.is_set():
                # a stop press while idle: ignore this wake
                self._stopped.clear()
                return
            self._say_hello()
            self._conversation_loop()
            # settle so goodbye / last answer is not picked up by wake listen
            self._await_quiet()

        def _wake_abort():
            # cancel a blocking wake listen (e.g. via the physical stop key)
            stop = getattr(self.wake, "stop", None)
            if callable(stop):
                try:
                    stop()
                except Exception:
                    pass
        self._abort_cbs.append(_wake_abort)
        try:
            self.wake.listen(on_wake)
        finally:
            if _wake_abort in self._abort_cbs:
                self._abort_cbs.remove(_wake_abort)


    def shutdown(self) -> None:
        if getattr(self, "_memory_path", "") and self._memory:
            try:
                self._memory.save(self._memory_path)
            except Exception as e:
                log.warning("failed to save memory: %s", e)
        self._stop_exit.set()
        self.stop_speaking()
        if self._tts_thread is not None and self._tts_thread.is_alive():
            self._tts_thread.join(timeout=1.0)
        stop_thread = getattr(self, "_stop_thread", None)
        if stop_thread is not None and stop_thread.is_alive():
            stop_thread.join(timeout=1.0)
        self.agents.shutdown()
        self.extension.close_all()
        if self._tts:
            self._tts.close()
        if self._stt:
            self._stt.close()

    # -- keep referenced method used by the screen skill --
    def _run_read_screen(self, params, ctx):
        from ..screen.reader import ScreenReader
        if getattr(self, "_screen_reader", None) is None:
            self._screen_reader = ScreenReader(
                ocr_enabled=self.config.get("screen.ocr_enabled", True),
                ocr_lang=self.config.get("screen.ocr_lang", "chi_sim+eng"),
                backend=self.config.get("screen.backend", "mss"))
        result = self._screen_reader.read_screen()
        txt = result.get("text", "").strip()
        if txt:
            return "屏幕上看到的内容是：" + txt[:200]
        return "我没能识别到屏幕上的文字。"

    def handle_text(self, text: str) -> tuple[str, str] | None:
        """Route one user utterance; returns (reply, emotion)."""
        if not text.strip():
            return None
        ctx = AgentContext(config=self.config, skills=self.skills, speak=self.speak)
        name = self.config.get("agents.default_agent", "general")
        agent = LLMAgent(name=name, llm=self.llm, memory=self._memory)
        try:
            return agent.respond(text, ctx)
        except Exception as e:
            log.exception("handle_text failed")
            return f"抱歉，出了点问题：{e}", "neutral"
