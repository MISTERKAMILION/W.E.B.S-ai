"""Linux terminal automation for executing commands.

Capabilities:
- Command execution (run, run_background, stop)
- Output capture
- Privilege escalation (sudo)

This module is Linux-focused and handles terminal operations.
Later extensions: git(), python(), docker()
"""

import subprocess
import time
from typing import Dict, List, Optional, Tuple

from .exceptions import TerminalAutomationError


class TerminalAutomation:
    """Terminal automation for Linux systems."""

    def __init__(self, validator: Optional["TerminalCommandValidator"] = None):
        """Initialize terminal automation.
        
        Args:
            validator: Optional TerminalCommandValidator for security.
                      If None, no validation is performed.
        """
        self._processes: Dict[str, subprocess.Popen] = {}
        self._process_counter = 0
        self._validator = validator

    # ============= COMMAND EXECUTION =============

    def run(self, command: str, timeout: int = 30) -> str:
        """Execute a command and wait for completion.
        
        Args:
            command: The shell command to execute.
            timeout: Maximum time to wait in seconds.
            
        Returns:
            Standard output of the command.
            
        Raises:
            TerminalAutomationError: If command fails or times out.
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

            if result.returncode != 0:
                raise TerminalAutomationError(
                    f"Command failed (exit code {result.returncode}): {result.stderr}"
                )

            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise TerminalAutomationError(f"Command timed out after {timeout}s: {command}")
        except Exception as e:
            raise TerminalAutomationError(f"Failed to execute command: {e}")

    def run_background(self, command: str) -> str:
        """Execute a command in the background and return a process ID.
        
        Args:
            command: The shell command to execute.
            
        Returns:
            Process ID (string identifier for later reference).
            
        Raises:
            TerminalAutomationError: If command fails to start.
        """
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            pid = f"bg_{self._process_counter}"
            self._process_counter += 1
            self._processes[pid] = process

            return pid
        except Exception as e:
            raise TerminalAutomationError(f"Failed to start background command: {e}")

    def stop(self, process_id: str) -> None:
        """Stop a background process.
        
        Args:
            process_id: Process ID returned from run_background().
            
        Raises:
            TerminalAutomationError: If process not found or termination fails.
        """
        try:
            process = self._processes.get(process_id)
            if not process:
                raise TerminalAutomationError(f"Process not found: {process_id}")

            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            del self._processes[process_id]
        except Exception as e:
            raise TerminalAutomationError(f"Failed to stop process: {e}")

    def output(self, process_id: str) -> Tuple[str, str]:
        """Get output from a background process.
        
        Args:
            process_id: Process ID returned from run_background().
            
        Returns:
            Tuple of (stdout, stderr).
            
        Raises:
            TerminalAutomationError: If getting output fails.
        """
        try:
            process = self._processes.get(process_id)
            if not process:
                raise TerminalAutomationError(f"Process not found: {process_id}")

            stdout, stderr = process.communicate(timeout=1)
            return (stdout.strip() if stdout else "", stderr.strip() if stderr else "")
        except subprocess.TimeoutExpired:
            return ("", "")
        except Exception as e:
            raise TerminalAutomationError(f"Failed to get output: {e}")

    # ============= PRIVILEGED EXECUTION =============

    def sudo(self, command: str, password: Optional[str] = None, timeout: int = 30) -> str:
        """Execute a command with sudo (requires password or no-password sudo).
        
        Args:
            command: The command to execute with sudo.
            password: Optional password for sudo. If None, assumes passwordless sudo.
            timeout: Maximum time to wait in seconds.
            
        Returns:
            Standard output of the command.
            
        Raises:
            TerminalAutomationError: If command fails or authentication fails.
        """
        try:
            full_command = f"sudo {command}"

            if password:
                # Use echo to pipe password
                full_command = f"echo {password} | sudo -S {command}"

            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

            if result.returncode != 0:
                raise TerminalAutomationError(
                    f"Sudo command failed: {result.stderr}"
                )

            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise TerminalAutomationError(f"Sudo command timed out: {command}")
        except Exception as e:
            raise TerminalAutomationError(f"Failed to execute sudo command: {e}")
