"""Main VoiceEngine orchestrator."""

import logging
import os
import threading
import time
from queue import Queue
from typing import List, Optional

from .audio import AudioPlayer
from .tts import TTSEngine
from .voices import VoiceManager, VoiceProfile

logger = logging.getLogger(__name__)


class VoiceEngine:
    """
    High-level voice engine for W.E.B.S.

    Handles TTS generation, voice profiles, and audio playback.
    Supports async speaking via a background queue.
    """

    def __init__(
        self,
        voices_dir: Optional[str] = None,
    ):
        self.voice_manager = VoiceManager(voices_dir)
        self.tts = TTSEngine("alfred")  # Default to Alfred voice
        self.audio = AudioPlayer()
        self._connected = self.tts.available

        # Async speak queue
        self._speak_queue: Queue = Queue()
        self._is_speaking = False
        self._speaker_thread: Optional[threading.Thread] = None

        if self._connected:
            self._start_speaker_thread()

        if not self._connected:
            logger.warning("No TTS engine available. Install edge-tts: pip install edge-tts")

    def _start_speaker_thread(self) -> None:
        """Start background speaker thread."""
        def _speaker_loop():
            while True:
                try:
                    if not self._speak_queue.empty():
                        text, voice = self._speak_queue.get()
                        self._is_speaking = True
                        try:
                            audio_path = self.tts.generate(text, voice)
                            if audio_path:
                                self.audio.play_file(audio_path)
                                # Clean up temp file
                                try:
                                    os.unlink(audio_path)
                                except OSError:
                                    pass
                        except Exception as e:
                            logger.error(f"Speaking error: {e}")
                        finally:
                            self._is_speaking = False
                    else:
                        time.sleep(0.05)
                except Exception:
                    time.sleep(0.1)

        self._speaker_thread = threading.Thread(target=_speaker_loop, daemon=True)
        self._speaker_thread.start()

    def speak(
        self,
        text: str,
        voice: str = "default",
    ) -> bool:
        """Speak text aloud (blocking). Returns True on success."""
        if not text or not text.strip():
            return False

        if not self._connected:
            logger.error("TTS engine not connected")
            return False

        audio_path = self.tts.generate(text, voice)
        if audio_path:
            self.audio.play_file(audio_path)
            try:
                os.unlink(audio_path)
            except OSError:
                pass
            return True
        return False

    def speak_async(
        self,
        text: str,
        voice: str = "default",
    ) -> bool:
        """Queue speech for background playback (non-blocking)."""
        if not self._connected or not text:
            return False
        self._speak_queue.put((text, voice))
        return True

    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._is_speaking

    def wait_until_done(self, timeout: float = 30.0) -> bool:
        """Block until speaking finishes or timeout."""
        start = time.time()
        while self._is_speaking and (time.time() - start) < timeout:
            time.sleep(0.1)
        return not self._is_speaking

    def add_voice(
        self, name: str, sample_path: str, description: str = ""
    ) -> bool:
        """Add a voice profile from a WAV file."""
        if not os.path.exists(sample_path):
            logger.error(f"Sample file not found: {sample_path}")
            return False
        profile = VoiceProfile(
            name=name,
            sample_path=sample_path,
            description=description,
        )
        self.voice_manager.add_profile(profile)
        logger.info(f"Voice added: {name}")
        return True

    def list_voices(self) -> List[str]:
        """List available voice profiles."""
        return self.voice_manager.list_profiles()

    def is_available(self) -> bool:
        """Check if TTS is available."""
        return self._connected

    def close(self) -> None:
        """Clean up resources."""
        pass
