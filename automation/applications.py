"""Application automation for launching and managing applications.

Capabilities:
- Launch/close applications
- Check running status
- Focus windows
- List running processes
"""

import subprocess
from typing import List

from .exceptions import ApplicationAutomationError
from .terminal import TerminalAutomation


class ApplicationAutomation:
    """Application launch and management automation."""

    def __init__(self):
        """Initialize application automation."""
        self._terminal = TerminalAutomation()

    def open(self, target: str, *args: str) -> None:
        """Open an application.
        
        Args:
            target: Application name or path (e.g., "firefox", "/usr/bin/gedit").
            *args: Additional command-line arguments.
            
        Raises:
            ApplicationAutomationError: If application fails to open.
        """
        try:
            cmd = f"{target} {' '.join(args)}".strip()
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            raise ApplicationAutomationError(f"Failed to open {target}: {e}")

    def close(self, target: str) -> None:
        """Close an application by name.
        
        Args:
            target: Application name to close (e.g., "firefox").
            
        Raises:
            ApplicationAutomationError: If application fails to close.
        """
        try:
            self._terminal.run(f"killall {target}")
        except Exception as e:
            raise ApplicationAutomationError(f"Failed to close {target}: {e}")

    def is_running(self, target: str) -> bool:
        """Check if an application is running.
        
        Args:
            target: Application name to check.
            
        Returns:
            True if application is running, False otherwise.
        """
        try:
            output = self._terminal.run(f"pgrep -x {target}")
            return bool(output and output.strip())
        except Exception:
            return False

    def focus(self, target: str) -> None:
        """Focus on an application window.
        
        Args:
            target: Application name or window title.
            
        Raises:
            ApplicationAutomationError: If focus fails.
        """
        try:
            # This is a placeholder - actual implementation depends on desktop environment
            # For X11: wmctrl -a "window_title"
            # For Wayland: varies by compositor
            self._terminal.run(f"wmctrl -a '{target}'")
        except Exception as e:
            raise ApplicationAutomationError(f"Failed to focus on {target}: {e}")

    def list_running(self) -> List[str]:
        """List all running applications.
        
        Returns:
            List of running application names.
        """
        try:
            output = self._terminal.run("ps aux | awk '{print $11}' | grep -v '^\\[' | sort -u")
            apps = [line.strip().split("/")[-1] for line in output.split("\n") if line.strip()]
            return [app for app in apps if app and not app.startswith("-")]
        except Exception:
            return []
