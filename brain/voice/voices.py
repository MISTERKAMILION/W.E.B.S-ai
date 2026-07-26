"""Voice profile management."""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VoiceProfile:
    """A voice profile with reference audio."""

    name: str
    sample_path: str
    language: str = "en"
    speed: float = 1.0
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "sample_path": self.sample_path,
            "language": self.language,
            "speed": self.speed,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceProfile":
        return cls(
            name=data["name"],
            sample_path=data["sample_path"],
            language=data.get("language", "en"),
            speed=data.get("speed", 1.0),
            description=data.get("description", ""),
        )


class VoiceManager:
    """Manages voice profiles and reference audio samples."""

    def __init__(self, voices_dir: Optional[str] = None):
        self.voices_dir = Path(
            voices_dir
            or os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(__file__))
                ),
                "voices",
            )
        )
        self.voices_dir.mkdir(parents=True, exist_ok=True)
        self.profiles: Dict[str, VoiceProfile] = {}
        self._load_profiles()
        logger.info(
            f"VoiceManager initialized with {len(self.profiles)} voices"
        )

    def _load_profiles(self) -> None:
        """Load voice profiles from disk."""
        profiles_file = self.voices_dir / "profiles.json"
        if profiles_file.exists():
            try:
                with open(profiles_file) as f:
                    data = json.load(f)
                    for name, config in data.items():
                        self.profiles[name] = VoiceProfile.from_dict(config)
            except Exception as e:
                logger.error(f"Failed to load voice profiles: {e}")

        # Auto-load .wav files that don't have profiles
        for wav_file in self.voices_dir.glob("*.wav"):
            name = wav_file.stem
            if name not in self.profiles:
                self.profiles[name] = VoiceProfile(
                    name=name,
                    sample_path=str(wav_file),
                    description="Auto-loaded voice",
                )

    def add_profile(self, profile: VoiceProfile) -> None:
        """Add or update a voice profile."""
        self.profiles[profile.name] = profile
        self._save_profiles()

    def get_profile(self, name: str) -> Optional[VoiceProfile]:
        """Get a voice profile by name."""
        return self.profiles.get(name)

    def list_profiles(self) -> List[str]:
        """List all profile names."""
        return list(self.profiles.keys())

    def get_voice_sample(self, name: str) -> Optional[str]:
        """Get the path to a voice sample file."""
        profile = self.get_profile(name)
        if profile and os.path.exists(profile.sample_path):
            return profile.sample_path
        return None

    def _save_profiles(self) -> None:
        """Save all profiles to disk."""
        profiles_file = self.voices_dir / "profiles.json"
        data = {name: p.to_dict() for name, p in self.profiles.items()}
        try:
            with open(profiles_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save voice profiles: {e}")
