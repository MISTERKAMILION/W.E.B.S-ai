#!/usr/bin/env python3
"""
W.E.B.S global activator — press W+V to start the full AI.

No terminal. No code. W+V → face + voice + live brain.

Uses:
  1) evdev (best on Wayland — needs 'input' group)
  2) pynput fallback
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOG = Path("/tmp/webs_hotkey_daemon.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [W.E.B.S] %(message)s",
    handlers=[logging.FileHandler(LOG), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("webs_daemon")

START_SCRIPT = ROOT / "scripts" / "start_webs.sh"
PIDFILE = Path("/tmp/webs_face.pid")
DAEMON_PID = Path("/tmp/webs_daemon.pid")

# Linux keycodes
KEY_W = 17
KEY_V = 47


def _is_webs_running() -> bool:
    if not PIDFILE.exists():
        return False
    try:
        pid = int(PIDFILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def launch_webs() -> None:
    if _is_webs_running():
        logger.info("Already running — ignore")
        return
    logger.info("Launching full W.E.B.S (face + voice + brain)")
    START_SCRIPT.chmod(0o755)
    subprocess.Popen(
        ["bash", str(START_SCRIPT)],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


class ChordState:
    def __init__(self, cooldown: float = 2.0):
        self.w = False
        self.v = False
        self.cooldown = cooldown
        self._last = 0.0
        self._lock = threading.Lock()

    def set_key(self, is_w: bool, is_v: bool, pressed: bool) -> None:
        with self._lock:
            if is_w:
                self.w = pressed
            if is_v:
                self.v = pressed
            if self.w and self.v:
                now = time.time()
                if now - self._last >= self.cooldown:
                    self._last = now
                    threading.Thread(target=launch_webs, daemon=True).start()


def listen_evdev(chord: ChordState) -> bool:
    """Global W+V via evdev (works on Wayland if user in 'input' group)."""
    try:
        from evdev import InputDevice, ecodes, list_devices
    except ImportError:
        logger.warning("evdev not installed")
        return False

    devices = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
            caps = dev.capabilities().get(ecodes.EV_KEY, [])
            if KEY_W in caps and KEY_V in caps:
                devices.append(dev)
        except (PermissionError, OSError):
            continue

    if not devices:
        logger.warning(
            "No readable keyboards via evdev. "
            "Run: sudo usermod -aG input $USER   then log out/in"
        )
        return False

    logger.info(f"evdev listening on {len(devices)} keyboard(s) for W+V")

    def _watch(dev: InputDevice) -> None:
        try:
            for event in dev.read_loop():
                if event.type != ecodes.EV_KEY:
                    continue
                if event.code == KEY_W:
                    chord.set_key(True, False, event.value != 0)
                elif event.code == KEY_V:
                    chord.set_key(False, True, event.value != 0)
        except Exception as e:
            logger.error(f"evdev device error: {e}")

    for d in devices:
        threading.Thread(target=_watch, args=(d,), daemon=True).start()
    return True


def listen_pynput(chord: ChordState) -> bool:
    """Fallback listener (limited on Wayland)."""
    try:
        from pynput import keyboard
    except ImportError:
        return False

    def on_press(key):
        try:
            c = key.char.lower() if hasattr(key, "char") and key.char else ""
        except Exception:
            c = ""
        if c == "w":
            chord.set_key(True, False, True)
        elif c == "v":
            chord.set_key(False, True, True)

    def on_release(key):
        try:
            c = key.char.lower() if hasattr(key, "char") and key.char else ""
        except Exception:
            c = ""
        if c == "w":
            chord.set_key(True, False, False)
        elif c == "v":
            chord.set_key(False, True, False)

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()
    logger.info("pynput listener started (may be limited on Wayland)")
    return True


def main() -> None:
    if DAEMON_PID.exists():
        try:
            old = int(DAEMON_PID.read_text().strip())
            os.kill(old, 0)
            logger.info(f"Daemon already running (pid {old})")
            return
        except Exception:
            DAEMON_PID.unlink(missing_ok=True)

    def cleanup(*_a):
        try:
            if DAEMON_PID.exists() and DAEMON_PID.read_text().strip() == str(os.getpid()):
                DAEMON_PID.unlink(missing_ok=True)
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    DAEMON_PID.write_text(str(os.getpid()))

    chord = ChordState()
    ok = listen_evdev(chord)
    if not ok:
        ok = listen_pynput(chord)
    if not ok:
        logger.error("No hotkey backend available. Install: pip install evdev pynput")
        cleanup()
        return

    logger.info("Ready. Press W + V together to start W.E.B.S.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
