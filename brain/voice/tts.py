"""Text-to-Speech engine using Piper TTS with British voices.

Fast, offline, low-resource TTS using pre-trained Piper voice models.
"""

import logging
import os
import tempfile
import wave
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

VOICES_DIR = Path(__file__).resolve().parent.parent.parent / "voices" / "piper"

DEFAULT_VOICE = "en_GB-alan-medium"

VOICE_PRESETS = {
    "default": DEFAULT_VOICE,
    "alfred": DEFAULT_VOICE,
    "jarvis": DEFAULT_VOICE,
    "british": DEFAULT_VOICE,
}


class TTSEngine:
    """TTS engine using Piper for fast, offline British speech.

    Voice is tuned to sound energetic and upbeat rather than monotone.
    """

    def __init__(self, voice: str = "default"):
        self._voice_name = VOICE_PRESETS.get(voice, DEFAULT_VOICE)
        self._voice = None
        self._available = False

        model_path = VOICES_DIR / f"{self._voice_name}.onnx"
        if not model_path.exists():
            logger.error(f"Piper voice not found: {model_path}")
            return

        try:
            from piper import PiperVoice
            from piper.config import SynthesisConfig
            self._voice = PiperVoice.load(str(model_path))
            self._syn_config = SynthesisConfig(
                length_scale=0.82,
                noise_scale=0.7,
                noise_w_scale=0.9,
            )
            self._available = True
            logger.info(f"Piper TTS: {self._voice_name} ({self._voice.config.sample_rate}Hz)")
        except Exception as e:
            logger.error(f"Piper init failed: {e}")

    @property
    def available(self) -> bool:
        return self._available

    def set_voice(self, voice: str) -> None:
        """Change voice preset."""
        new_name = VOICE_PRESETS.get(voice, voice)
        model_path = VOICES_DIR / f"{new_name}.onnx"
        if model_path.exists():
            try:
                from piper import PiperVoice
                self._voice = PiperVoice.load(str(model_path))
                self._voice_name = new_name
                logger.info(f"Piper voice changed to: {new_name}")
            except Exception as e:
                logger.error(f"Failed to load voice {new_name}: {e}")
        else:
            logger.error(f"Voice not found: {model_path}")

    def generate(self, text: str, voice: Optional[str] = None) -> Optional[str]:
        """Generate speech audio and return temp WAV file path."""
        if not text or not text.strip():
            return None
        if not self._available or not self._voice:
            return None

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name

            with wave.open(tmp_path, "wb") as wf:
                self._voice.synthesize_wav(text, wf, syn_config=self._syn_config)

            return tmp_path
        except Exception as e:
            logger.error(f"Piper TTS generation failed: {e}")
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            return None

    def generate_wav(self, text: str, voice: Optional[str] = None) -> Optional[bytes]:
        """Generate speech and return WAV bytes."""
        audio_path = self.generate(text, voice)
        if not audio_path:
            return None

        try:
            with open(audio_path, "rb") as f:
                audio = f.read()
            os.unlink(audio_path)
            return audio
        except Exception:
            return None
