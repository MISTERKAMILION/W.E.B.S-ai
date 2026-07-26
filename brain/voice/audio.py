"""Audio playback utilities with high-quality output."""

import os
import sys
import subprocess
import logging

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Plays audio with high quality output."""

    @staticmethod
    def play_file(filepath: str) -> None:
        """Play an audio file with best available quality."""
        if not os.path.exists(filepath):
            logger.error(f"Audio file not found: {filepath}")
            return

        try:
            # Try mpv first (best quality, handles all formats)
            if AudioPlayer._try_mpv(filepath):
                return
            # Try ffplay (good quality)
            if AudioPlayer._try_ffplay(filepath):
                return
            # Try paplay (PulseAudio)
            if AudioPlayer._try_paplay(filepath):
                return
            # Fallback to aplay (ALSA)
            AudioPlayer._try_aplay(filepath)
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")

    @staticmethod
    def _try_mpv(filepath: str) -> bool:
        """Play using mpv with high quality settings."""
        try:
            cmd = [
                "mpv",
                "--no-video",           # No video output
                "--no-terminal",        # Quiet
                f"--audio-file={filepath}",
                "--volume=100",         # Full volume
                "--audio-pitch-correction=yes",
                "--audio-samplerate=48000",
                "--audio-channels=stereo",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def _try_ffplay(filepath: str) -> bool:
        """Play using ffplay."""
        try:
            cmd = [
                "ffplay",
                "-nodisp",              # No video window
                "-autoexit",            # Exit when done
                "-loglevel", "quiet",
                "-ar", "48000",         # Sample rate
                filepath,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def _try_paplay(filepath: str) -> bool:
        """Play using PulseAudio."""
        try:
            result = subprocess.run(
                ["paplay", filepath],
                capture_output=True,
                timeout=120
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def _try_aplay(filepath: str) -> bool:
        """Play using ALSA."""
        try:
            # Convert to WAV for aplay if needed
            if filepath.endswith(".mp3"):
                wav_path = filepath.replace(".mp3", "_play.wav")
                subprocess.run(
                    ["ffmpeg", "-i", filepath, "-acodec", "pcm_s16le",
                     "-ar", "48000", "-ac", "1", wav_path, "-y"],
                    capture_output=True, timeout=10
                )
                result = subprocess.run(
                    ["aplay", wav_path],
                    capture_output=True,
                    timeout=120
                )
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass
                return result.returncode == 0
            else:
                result = subprocess.run(
                    ["aplay", filepath],
                    capture_output=True,
                    timeout=120
                )
                return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
