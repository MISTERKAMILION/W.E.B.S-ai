#!/usr/bin/env python3
"""One-time setup for Alfred voice."""

import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
VOICES_DIR = PROJECT_ROOT / "voices"


def main():
    print("W.E.B.S — Alfred Voice Setup")
    print("=" * 60)

    VOICES_DIR.mkdir(parents=True, exist_ok=True)

    alfred_path = VOICES_DIR / "alfred.wav"
    if alfred_path.exists():
        print(f"Alfred voice already exists at {alfred_path}")
        return

    print()
    print("  Place a 6-second audio sample of Alfred speaking")
    print(f"  in: {VOICES_DIR}")
    print("  Name it: alfred.wav")
    print()

    choice = input("  Copy from another location? (y/n): ").strip().lower()
    if choice == "y":
        src = input("  Full path to audio file: ").strip()
        if src and Path(src).exists():
            shutil.copy(src, alfred_path)
            print("  Alfred voice copied!")
        else:
            print("  File not found.")
            return

    # Create profiles.json
    profiles_file = VOICES_DIR / "profiles.json"
    if not profiles_file.exists():
        data = {
            "alfred": {
                "name": "alfred",
                "sample_path": str(alfred_path),
                "language": "en",
                "speed": 1.0,
                "description": "Alfred voice",
            }
        }
        with open(profiles_file, "w") as f:
            json.dump(data, f, indent=2)
        print("  Voice profile saved.")

    print()
    print("  Setup complete!")
    print("  Run: python3 webs_face.py --voice")
    print("  Or:  python3 run_webs.py --face --voice")


if __name__ == "__main__":
    main()
