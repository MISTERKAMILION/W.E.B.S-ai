#!/usr/bin/env python3
"""Quick start script for W.E.B.S.

Modes:
  python3 run_webs.py                 Text chat loop
  python3 run_webs.py --voice         Continuous voice loop
  python3 run_webs.py --hotkey        W+V to talk, or type anytime
  python3 run_webs.py --face          Orange Jarvis HUD (fullscreen)
  python3 run_webs.py --face --voice  Jarvis HUD + mic (W+V)
  python3 run_webs.py --face --windowed
  python3 webs_face.py --voice
"""

import sys
import os
import logging
import argparse
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load .env
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

from brain import Brain


def run_text(brain: Brain) -> None:
    """Interactive text chat loop."""
    print("\n" + "-" * 60)
    print("Type your message (or 'exit' to quit)")
    print("-" * 60 + "\n")

    try:
        while True:
            user_input = input("You: ").strip()

            if user_input.lower() in ["exit", "quit", "bye"]:
                print("\nGoodbye, sir.")
                break

            if not user_input:
                continue

            print("Thinking...")
            response = brain.process(user_input)
            print(f"\nW.E.B.S: {response}\n")

    except KeyboardInterrupt:
        print("\n\nGoodbye, sir.")


def run_voice(brain: Brain) -> None:
    """Voice butler loop: listen → process → speak."""
    brain.init_voice()
    if not brain._stt or not brain._stt.available:
        print("Voice STT unavailable. Falling back to text mode.")
        print("Install: pip install faster-whisper sounddevice")
        run_text(brain)
        return

    if brain._voice_engine:
        brain._voice_engine.speak("W.E.B.S online. How may I assist you, sir?")
    else:
        print("W.E.B.S online. How may I assist you, sir?")

    print("\n" + "-" * 60)
    print("Voice mode active. Say 'exit' to quit. (Ctrl+C also works)")
    print("-" * 60 + "\n")

    try:
        while True:
            print("Listening...")
            user_input = brain._stt.listen_once(timeout=6)
            if not user_input:
                continue

            print(f"You: {user_input}")
            if "exit" in user_input.lower() or "goodbye" in user_input.lower():
                if brain._voice_engine:
                    brain._voice_engine.speak("Goodbye, sir.")
                else:
                    print("Goodbye, sir.")
                break

            print("Thinking...")
            response = brain.process(user_input)
            print(f"W.E.B.S: {response}\n")

    except KeyboardInterrupt:
        print("\n\nGoodbye, sir.")


def main():
    parser = argparse.ArgumentParser(description="W.E.B.S AI Assistant")
    parser.add_argument(
        "--face", "-f", action="store_true",
        help="Launch orange Jarvis HUD face (fullscreen)",
    )
    parser.add_argument(
        "--voice", "-v", action="store_true",
        help="Enable continuous microphone voice loop",
    )
    parser.add_argument(
        "--hotkey", "-k", action="store_true",
        help="Activate with W+V shortcut (also allows typing)",
    )
    parser.add_argument(
        "--windowed", action="store_true",
        help="With --face: run windowed instead of fullscreen",
    )
    args = parser.parse_args()

    # Jarvis face mode — full orange HUD
    if args.face:
        face_args = [sys.executable, str(project_root / "webs_face.py")]
        if args.voice or args.hotkey:
            face_args.append("--voice")
        if args.windowed:
            face_args.append("--windowed")
        os.execv(sys.executable, face_args)

    print("=" * 60)
    print("  W.E.B.S AI Assistant")
    print("  Created by Mister Nossair Zaidi")
    print("=" * 60)
    print("\nInitializing W.E.B.S...")

    brain = Brain(enable_face=False)

    state = brain.get_state()
    mode = "hotkey (W+V)" if args.hotkey else ("voice" if args.voice else "text")
    print("\nW.E.B.S is ready!")
    print(f"  State: {state['state']}")
    print(f"  Memory: {state['memory_size']} items")
    print(f"  Models: {state['available_models']}")
    print(f"  Mode: {mode}")

    try:
        if args.hotkey:
            from scripts.webs_hotkey import run_hotkey_session
            run_hotkey_session(brain, enable_voice=True)
        elif args.voice:
            run_voice(brain)
        else:
            run_text(brain)
    finally:
        brain.shutdown()


if __name__ == "__main__":
    main()
