"""Speech-to-text with faster-whisper (local) and SpeechRecognition fallback.

Provides continuous listening with optional wake word detection.
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)


def _ensure_capture_enabled() -> None:
    """Unmute ALSA Capture and set reasonable mic gain."""
    try:
        result = subprocess.run(
            ["amixer", "-c", "0", "sget", "Capture"],
            capture_output=True, text=True, timeout=5,
        )
        if "[off]" in result.stdout:
            subprocess.run(
                ["amixer", "-c", "0", "set", "Capture", "toggle"],
                capture_output=True, timeout=5,
            )
            logger.info("Unmuted ALSA Capture control")
        subprocess.run(
            ["amixer", "-c", "0", "set", "Internal Mic Boost", "0%"],
            capture_output=True, timeout=5,
        )
        subprocess.run(
            ["amixer", "-c", "0", "set", "Capture", "50%"],
            capture_output=True, timeout=5,
        )
    except Exception:
        pass


def _find_working_mic() -> Optional[int]:
    """Find a microphone device that actually captures audio.

    Tries PulseAudio first, then device 0.
    Returns the device index or None for default.
    """
    if not HAS_SR:
        return None

    names = sr.Microphone.list_microphone_names()

    for idx, name in enumerate(names):
        if "pulse" in name.lower():
            try:
                mic = sr.Microphone(device_index=idx)
                with mic as source:
                    sr.Recognizer().adjust_for_ambient_noise(source, duration=0.5)
                logger.info(f"Found working mic: {name} (index {idx})")
                return idx
            except Exception:
                continue

    return None

# --- Optional backends ---
try:
    from faster_whisper import WhisperModel

    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False
    WhisperModel = None  # type: ignore

try:
    import sounddevice as sd

    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
    sd = None  # type: ignore

try:
    import speech_recognition as sr

    HAS_SR = True
except ImportError:
    HAS_SR = False
    sr = None  # type: ignore


class SpeechToText:
    """Continuous speech-to-text with optional wake word.

    Prefers local faster-whisper; falls back to Google STT via SpeechRecognition.
    """

    def __init__(
        self,
        wake_word: Optional[str] = None,
        language: str = "en-US",
        energy_threshold: int = 300,
        pause_threshold: float = 0.8,
        whisper_model: str = "base",
        sample_rate: int = 16000,
        listen_seconds: float = 6.0,
    ):
        self.wake_word = wake_word
        self.language = language
        self.is_listening = False
        self._callback: Optional[Callable[[str], None]] = None
        self._thread: Optional[threading.Thread] = None
        self.sample_rate = sample_rate
        self.listen_seconds = listen_seconds

        self._whisper = None
        self.recognizer = None
        self.microphone = None
        self._backend = "none"

        _ensure_capture_enabled()

        # Prefer local faster-whisper
        if HAS_WHISPER and HAS_SOUNDDEVICE:
            try:
                self._whisper = WhisperModel(
                    whisper_model, device="cpu", compute_type="int8"
                )
                self._backend = "faster-whisper"
                logger.info(f"STT: faster-whisper ({whisper_model})")
            except Exception as e:
                logger.warning(f"faster-whisper init failed: {e}")

        # Fallback: Google via SpeechRecognition
        if self._backend == "none" and HAS_SR:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = energy_threshold
            self.recognizer.pause_threshold = pause_threshold
            try:
                mic_index = _find_working_mic()
                self.microphone = sr.Microphone(device_index=mic_index)
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=2)
                if self.recognizer.energy_threshold < 300:
                    self.recognizer.energy_threshold = 300
                self._backend = "google"
                logger.info(f"STT: SpeechRecognition (Google) device={mic_index}")
            except Exception as e:
                logger.warning(f"No microphone available: {e}")
                self.microphone = None

        if self._backend == "none":
            logger.error(
                "STT unavailable. Install: pip install faster-whisper sounddevice"
            )

    @property
    def available(self) -> bool:
        return self._backend != "none"

    def start_listening(self, callback: Callable[[str], None]) -> None:
        """Start listening for voice input in background."""
        if not self.available:
            logger.error("Cannot start listening: STT not available")
            return

        self._callback = callback
        self.is_listening = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info(
            f"Started listening via {self._backend} "
            f"(wake word: {self.wake_word or 'none'})"
        )

    def stop_listening(self) -> None:
        """Stop listening."""
        self.is_listening = False
        logger.info("Stopped listening")

    def _dispatch(self, text: str) -> None:
        text = (text or "").strip()
        if not text or not self._callback:
            return

        if self.wake_word:
            if self.wake_word.lower() not in text.lower():
                return
            text = text.lower().replace(self.wake_word.lower(), "").strip()
            if not text:
                return

        logger.info(f"Heard: {text}")
        self._callback(text)

    def _listen_loop(self) -> None:
        """Main listening loop."""
        while self.is_listening:
            try:
                text = self.listen_once(timeout=int(self.listen_seconds))
                if text:
                    self._dispatch(text)
            except Exception as e:
                logger.error(f"Listening error: {e}")
                time.sleep(1)

    def _listen_whisper(self, seconds: float) -> Optional[str]:
        """Record and transcribe with faster-whisper."""
        audio = sd.rec(
            int(seconds * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        samples = np.squeeze(audio)
        if samples.size == 0 or float(np.abs(samples).mean()) < 1e-4:
            return None

        segments, _ = self._whisper.transcribe(samples, language="en")
        text = " ".join(s.text.strip() for s in segments).strip()
        return text or None

    def _listen_google(self, timeout: int) -> Optional[str]:
        """Listen once via SpeechRecognition + Google."""
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=10
                )
            return self.recognizer.recognize_google(
                audio, language=self.language
            )
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            logger.error(f"Google STT error: {e}")
            return None

    def listen_once(self, timeout: int = 5) -> Optional[str]:
        """Listen for a single utterance and return text."""
        if self._backend == "faster-whisper":
            return self._listen_whisper(float(timeout))
        if self._backend == "google":
            return self._listen_google(timeout)
        return None
