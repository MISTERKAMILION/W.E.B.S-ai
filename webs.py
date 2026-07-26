#!/usr/bin/env python3
"""
W.E.B.S — Launcher

Usage:
    W.E.B.S --start          Full-screen animated face
    W.E.B.S --start --voice  Full-screen face with voice
    W.E.B.S --chat           Chat mode (no face)
    W.E.B.S --chat --face    Chat with face
    W.E.B.S --help           Show help
"""

import sys
import os
import argparse

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Load .env
env_file = os.path.join(project_root, ".env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()


def start_face_mode(voice=False):
    """Launch the full-screen animated Jarvis face."""
    import importlib.util

    face_path = os.path.join(project_root, "webs_face.py")
    spec = importlib.util.spec_from_file_location("webs_face", face_path)
    core = importlib.util.module_from_spec(spec)
    sys.argv = ["webs_face.py"]
    if voice:
        sys.argv.append("--voice")
    spec.loader.exec_module(core)
    core.main()


def start_chat(face_enabled=False):
    """Launch the chat interface."""
    from chat import Chat

    api_key = os.environ.get("GROQ_API_KEY")
    chat = Chat(api_key=api_key, enable_face=face_enabled)
    chat.run()


def main():
    parser = argparse.ArgumentParser(
        prog="W.E.B.S",
        description="W.E.B.S — AI Operating System",
    )
    parser.add_argument(
        "--start",
        action="store_true",
        help="Launch the full-screen animated face",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Launch the chat interface",
    )
    parser.add_argument(
        "--face",
        action="store_true",
        help="Enable animated face with chat mode",
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Enable voice output",
    )
    parser.add_argument(
        "--message",
        "-m",
        type=str,
        help="Send a single message and exit",
    )

    args = parser.parse_args()

    if not any([args.start, args.chat, args.face, args.message]):
        print()
        print("  W.E.B.S — AI Operating System")
        print("  Created by Mister Nossair Zaidi")
        print()
        print("  Usage:")
        print("    W.E.B.S --start          Full-screen face")
        print("    W.E.B.S --start --voice  Full-screen face + voice")
        print("    W.E.B.S --chat           Chat mode")
        print("    W.E.B.S --chat --face    Chat with face")
        print("    W.E.B.S --help           Help")
        print()
        return

    if args.start:
        start_face_mode(voice=args.voice)
    elif args.message:
        from chat import Chat

        api_key = os.environ.get("GROQ_API_KEY")
        chat = Chat(api_key=api_key, enable_face=args.face)
        chat.run_once(args.message)
    elif args.chat or args.face:
        start_chat(face_enabled=args.face)
    else:
        start_chat(face_enabled=False)


if __name__ == "__main__":
    main()
