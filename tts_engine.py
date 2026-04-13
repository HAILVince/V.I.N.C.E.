"""
VINCE tts_engine.py
Text-to-Speech engine wrapper.
Uses pyttsx3 (offline SAPI5 on Windows / espeak on Linux).
Falls back gracefully if not installed.
"""

import threading
from typing import Optional

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

import data as D


class TTSEngine:
    """
    Thread-safe TTS wrapper.
    Call speak(text) to queue a reading. Call stop() to interrupt.
    """

    def __init__(self):
        self._engine: Optional["pyttsx3.Engine"] = None
        self._lock = threading.Lock()
        self._speaking = False
        self._init()

    def _init(self):
        if not TTS_AVAILABLE:
            return
        try:
            self._engine = pyttsx3.init()
            self._apply_settings()
        except Exception as e:
            print(f"[TTS] Failed to init pyttsx3: {e}")
            self._engine = None

    def _apply_settings(self):
        if not self._engine:
            return
        cfg = D.get_tts()
        try:
            self._engine.setProperty("rate",   cfg.get("rate",   175))
            self._engine.setProperty("volume", cfg.get("volume", 1.0))
            vid = cfg.get("voice_id", "")
            if vid:
                self._engine.setProperty("voice", vid)
        except Exception as e:
            print(f"[TTS] Settings error: {e}")

    def speak(self, text: str) -> None:
        """Speak text in a background thread (non-blocking)."""
        if not TTS_AVAILABLE or not self._engine:
            return
        cfg = D.get_tts()
        if not cfg.get("enabled", False):
            return

        def _run():
            with self._lock:
                self._speaking = True
                try:
                    self._apply_settings()
                    # Clean text: strip markdown-ish symbols
                    clean = self._clean(text)
                    self._engine.say(clean)
                    self._engine.runAndWait()
                except Exception as e:
                    print(f"[TTS] speak error: {e}")
                finally:
                    self._speaking = False

        threading.Thread(target=_run, daemon=True).start()

    def stop(self) -> None:
        """Interrupt current speech."""
        if self._engine and self._speaking:
            try:
                self._engine.stop()
            except Exception:
                pass

    def get_voices(self) -> list[dict]:
        """Return list of available voices as dicts with id and name."""
        if not self._engine:
            return []
        try:
            voices = self._engine.getProperty("voices")
            return [{"id": v.id, "name": v.name} for v in voices]
        except Exception:
            return []

    def set_voice(self, voice_id: str) -> None:
        D.set_tts({"voice_id": voice_id})
        if self._engine:
            try:
                self._engine.setProperty("voice", voice_id)
            except Exception as e:
                print(f"[TTS] set_voice error: {e}")

    def set_rate(self, rate: int) -> None:
        D.set_tts({"rate": rate})

    def set_volume(self, volume: float) -> None:
        D.set_tts({"volume": volume})

    def set_enabled(self, state: bool) -> None:
        D.set_tts({"enabled": state})

    @property
    def available(self) -> bool:
        return TTS_AVAILABLE and self._engine is not None

    @property
    def speaking(self) -> bool:
        return self._speaking

    @staticmethod
    def _clean(text: str) -> str:
        """Remove markdown and special characters before speaking."""
        import re
        text = re.sub(r"\*+([^*]+)\*+", r"\1", text)
        text = re.sub(r"`{1,3}[^`]*`{1,3}", " code block ", text)
        text = re.sub(r"#{1,6}\s*", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        text = re.sub(r"[◈●○▶⚙⚠◉►▷◆◇]", "", text)
        text = re.sub(r"─+", "", text)
        return text.strip()


# Singleton instance
_engine: Optional[TTSEngine] = None


def get_engine() -> TTSEngine:
    global _engine
    if _engine is None:
        _engine = TTSEngine()
    return _engine
