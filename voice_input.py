"""
VINCE voice_input.py
Push-to-Talk speech recognition.
Hold a button → microphone records → release → text appears in input field.
Uses SpeechRecognition + PyAudio. Falls back gracefully if not installed.
"""

import threading
from typing import Callable, Optional

try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False

import data as D


class VoiceInput:
    """
    PTT voice input controller.

    Usage:
        vi = VoiceInput(on_result=fn, on_error=fn, on_listening=fn)
        vi.start_recording()   # call on button press
        vi.stop_recording()    # call on button release → fires on_result
    """

    def __init__(
        self,
        on_result:    Optional[Callable[[str], None]] = None,
        on_error:     Optional[Callable[[str], None]] = None,
        on_listening: Optional[Callable[[bool], None]] = None,
    ):
        self.on_result    = on_result
        self.on_error     = on_error
        self.on_listening = on_listening  # True = started, False = stopped

        self._recognizer  = sr.Recognizer() if STT_AVAILABLE else None
        self._is_recording = False
        self._audio_data: Optional["sr.AudioData"] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def available(self) -> bool:
        return STT_AVAILABLE and self._recognizer is not None

    def start_recording(self) -> None:
        """Begin capturing from the microphone (non-blocking)."""
        if not self.available or self._is_recording:
            return
        self._is_recording = True
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop_recording(self) -> None:
        """Stop capturing and transcribe. Fires on_result when done."""
        self._is_recording = False
        # Thread will detect this flag and exit

    def _record_loop(self) -> None:
        cfg = D.get_stt()
        self._recognizer.energy_threshold = cfg.get("energy_threshold", 300)
        self._recognizer.dynamic_energy_threshold = True

        if self.on_listening:
            self.on_listening(True)

        try:
            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self._recognizer.listen(
                    source,
                    timeout=None,        # no timeout — user controls via button
                    phrase_time_limit=30,
                )
        except Exception as e:
            if self.on_error:
                self.on_error(f"Microphone error: {e}")
            if self.on_listening:
                self.on_listening(False)
            return
        finally:
            self._is_recording = False

        if self.on_listening:
            self.on_listening(False)

        # Transcribe
        try:
            text = self._recognizer.recognize_google(audio)
            if self.on_result:
                self.on_result(text)
        except sr.UnknownValueError:
            if self.on_error:
                self.on_error("Could not understand audio.")
        except sr.RequestError as e:
            if self.on_error:
                self.on_error(f"Speech recognition service error: {e}")
        except Exception as e:
            if self.on_error:
                self.on_error(f"STT error: {e}")
