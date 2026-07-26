"""Mouse and keyboard control automation.

Uses PyAutoGUI for cross-platform input control.
Provides cursor movement, clicking, scrolling, typing, and hotkeys.
"""

import logging
import subprocess
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import pyautogui
    # Test if display is available
    pyautogui.size()
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    pyautogui.PAUSE = 0.1
    HAS_PYAUTOGUI = True
except Exception:
    HAS_PYAUTOGUI = False
    logger.warning("PyAutoGUI not available or no display")


class InputControl:
    """Mouse and keyboard input control."""

    def __init__(self):
        self._available = HAS_PYAUTOGUI
        if not self._available:
            logger.warning("Input control unavailable - install pyautogui")

    @property
    def available(self) -> bool:
        return self._available

    # ========== MOUSE ==========

    def move_mouse(self, x: int, y: int, duration: float = 0.3) -> str:
        """Move cursor to absolute screen position."""
        if not self._available:
            return "PyAutoGUI not available"
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return f"Cursor moved to ({x}, {y})"
        except Exception as e:
            return f"Error: {e}"

    def move_mouse_relative(self, dx: int, dy: int, duration: float = 0.3) -> str:
        """Move cursor relative to current position."""
        if not self._available:
            return "PyAutoGUI not available"
        try:
            pyautogui.moveRel(dx, dy, duration=duration)
            pos = pyautogui.position()
            return f"Cursor moved to ({pos.x}, {pos.y})"
        except Exception as e:
            return f"Error: {e}"

    def click(self, x: Optional[int] = None, y: Optional[int] = None,
              button: str = "left", clicks: int = 1) -> str:
        """Click at position (or current position if None)."""
        if not self._available:
            return "PyAutoGUI not available"
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, clicks=clicks, button=button)
                return f"Clicked ({x}, {y})"
            else:
                pyautogui.click(clicks=clicks, button=button)
                pos = pyautogui.position()
                return f"Clicked at ({pos.x}, {pos.y})"
        except Exception as e:
            return f"Error: {e}"

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Double click at position."""
        return self.click(x, y, clicks=2)

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Right click at position."""
        return self.click(x, y, button="right")

    def scroll(self, amount: int, x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Scroll up (positive) or down (negative)."""
        if not self._available:
            return "PyAutoGUI not available"
        try:
            if x is not None and y is not None:
                pyautogui.scroll(amount, x=x, y=y)
            else:
                pyautogui.scroll(amount)
            direction = "up" if amount > 0 else "down"
            return f"Scrolled {direction} {abs(amount)} clicks"
        except Exception as e:
            return f"Error: {e}"

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int,
             duration: float = 0.5, button: str = "left") -> str:
        """Drag from start to end position."""
        if not self._available:
            return "PyAutoGUI not available"
        try:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.drag(end_x - start_x, end_y - start_y,
                          duration=duration, button=button)
            return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"
        except Exception as e:
            return f"Error: {e}"

    def get_mouse_position(self) -> str:
        """Get current cursor position."""
        if not self._available:
            return "PyAutoGUI not available"
        pos = pyautogui.position()
        return f"Cursor at ({pos.x}, {pos.y})"

    def get_screen_size(self) -> str:
        """Get screen resolution."""
        if not self._available:
            return "PyAutoGUI not available"
        size = pyautogui.size()
        return f"Screen: {size.width}x{size.height}"

    # ========== KEYBOARD ==========

    def type_text(self, text: str, interval: float = 0.02) -> str:
        """Type text character by character."""
        if not self._available:
            return "PyAutoGUI not available"
        try:
            pyautogui.typewrite(text, interval=interval)
            return f"Typed: {text[:50]}"
        except Exception as e:
            return f"Error: {e}"

    def press_key(self, key: str) -> str:
        """Press a single key (enter, tab, escape, space, etc.)."""
        if not self._available:
            return "PyAutoGUI not available"
        try:
            pyautogui.press(key)
            return f"Pressed: {key}"
        except Exception as e:
            return f"Error: {e}"

    def hotkey(self, *keys) -> str:
        """Press a key combination (e.g., ctrl+c, alt+tab)."""
        if not self._available:
            return "PyAutoGUI not available"
        try:
            pyautogui.hotkey(*keys)
            return f"Pressed: {'+'.join(keys)}"
        except Exception as e:
            return f"Error: {e}"

    def key_down(self, key: str) -> str:
        """Hold down a key."""
        if not self._available:
            return "PyAutoGUI not available"
        try:
            pyautogui.keyDown(key)
            return f"Key down: {key}"
        except Exception as e:
            return f"Error: {e}"

    def key_up(self, key: str) -> str:
        """Release a key."""
        if not self._available:
            return "PyAutoGUI not available"
        try:
            pyautogui.keyUp(key)
            return f"Key up: {key}"
        except Exception as e:
            return f"Error: {e}"

    # ========== SCREEN ==========

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> str:
        """Take a screenshot. Returns file path."""
        if not self._available:
            return "PyAutoGUI not available"
        try:
            import tempfile
            import os
            img = pyautogui.screenshot(region=region)
            path = os.path.join(tempfile.gettempdir(), "webs_screenshot.png")
            img.save(path)
            return f"Screenshot saved: {path}"
        except Exception as e:
            return f"Error: {e}"

    def locate_on_screen(self, image_path: str, confidence: float = 0.8) -> str:
        """Find an image on screen and return its center coordinates."""
        if not self._available:
            return "PyAutoGUI not available"
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                return f"Found at ({center.x}, {center.y})"
            return "Not found on screen"
        except Exception as e:
            return f"Error: {e}"
