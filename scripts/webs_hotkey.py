#!/usr/bin/env python3
"""Global W+V hotkey listener for W.E.B.S.

Press W and V together to wake the butler (listen once → reply → speak).
You can also type in the terminal at any time.

Usage:
    python3 run_webs.py --hotkey
    python3 scripts/webs_hotkey.py          # same, thin wrapper
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Set

logger = logging.getLogger(__name__)

# Key names pynput may report for W / V
_W_KEYS = {"w", "Key.w"}
_V_KEYS = {"v", "Key.v"}


def _key_name(key) -> str:
    """Normalize a pynput key to a comparable string."""
    try:
        if hasattr(key, "char") and key.char:
            return key.char.lower()
    except Exception:
        pass
    name = str(key)
    if name.startswith("'") and name.endswith("'") and len(name) == 3:
        return name[1].lower()
    return name


class WVHotkey:
    """Detect simultaneous W + V press (chord)."""

    def __init__(self, on_activate: Callable[[], None], cooldown: float = 1.5):
        self.on_activate = on_activate
        self.cooldown = cooldown
        self._pressed: Set[str] = set()
        self._last_fire = 0.0
        self._listener = None
        self._busy = False
        self._lock = threading.Lock()

    def _maybe_fire(self) -> None:
        now = time.time()
        if now - self._last_fire < self.cooldown:
            return
        w_down = bool(self._pressed & _W_KEYS) or "w" in self._pressed
        v_down = bool(self._pressed & _V_KEYS) or "v" in self._pressed
        if not (w_down and v_down):
            return
        if self._busy:
            return
        self._last_fire = now
        self._busy = True

        def _run():
            try:
                self.on_activate()
            finally:
                self._busy = False

        threading.Thread(target=_run, daemon=True).start()

    def _on_press(self, key) -> None:
        name = _key_name(key)
        self._pressed.add(name)
        if name in ("w", "v") or name in _W_KEYS or name in _V_KEYS:
            self._maybe_fire()

    def _on_release(self, key) -> None:
        name = _key_name(key)
        self._pressed.discard(name)

    def start(self) -> bool:
        """Start global listener. Returns False if pynput unavailable."""
        try:
            from pynput import keyboard
        except ImportError:
            logger.error("pynput not installed. Run: pip install pynput")
            return False

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()
        logger.info("Hotkey armed: press W+V together to activate W.E.B.S")
        return True

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None


def run_hotkey_session(brain, enable_voice: bool = True) -> None:
    """Hybrid session: W+V = talk, keyboard = type."""
    if enable_voice:
        brain.init_voice()

    stt_ok = bool(brain._stt and getattr(brain._stt, "available", False))
    tts = brain._voice_engine

    def speak(text: str) -> None:
        print(f"W.E.B.S: {text}")
        if tts:
            tts.speak_async(text)

    def handle(text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        print(f"You: {text}")
        if text.lower() in ("exit", "quit", "bye") or "goodbye" in text.lower():
            speak("Goodbye, sir.")
            # Signal main loop via flag
            session["running"] = False
            return
        print("Thinking...")
        reply = brain.process(text)
        # process() already speaks if voice engine active; still print
        if not tts:
            print(f"\nW.E.B.S: {reply}\n")
        else:
            print(f"\nW.E.B.S: {reply}\n")

    def on_wv() -> None:
        if not stt_ok:
            speak("Voice is unavailable, sir. Please type instead.")
            return
        print("\n[W+V] Listening...")
        if tts:
            # Avoid talking over the mic
            tts.wait_until_done(timeout=2.0)
        heard = brain._stt.listen_once(timeout=6)
        if not heard:
            print("[W+V] Nothing heard.")
            return
        handle(heard)

    session = {"running": True}
    hotkey = WVHotkey(on_activate=on_wv)
    hotkey_ok = hotkey.start()

    speak("W.E.B.S online. Press W+V to talk, or type below, sir.")
    print()
    print("-" * 60)
    if hotkey_ok:
        print("  Shortcut : W + V  (press both together)")
    else:
        print("  Hotkey unavailable — typing only (pip install pynput)")
    print("  Type     : enter a message below")
    print("  Exit     : type exit  |  Ctrl+C")
    print("-" * 60)
    print()

    try:
        while session["running"]:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break
            if not session["running"]:
                break
            if not user_input:
                continue
            handle(user_input)
            if not session["running"]:
                break
    except KeyboardInterrupt:
        print("\n\nGoodbye, sir.")
    finally:
        hotkey.stop()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    env_file = project_root / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

    from brain import Brain

    print("=" * 60)
    print("  W.E.B.S — Hotkey mode (W+V)")
    print("=" * 60)

    brain = Brain()
    try:
        run_hotkey_session(brain, enable_voice=True)
    finally:
        brain.shutdown()


if __name__ == "__main__":
    main()
