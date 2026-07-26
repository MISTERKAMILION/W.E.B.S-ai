# automation/validator.py
"""Security validator for terminal commands using pattern-based approach."""

import re
from typing import List, Pattern, Tuple
from pathlib import Path


class TerminalSecurityError(Exception):
    """Raised when a command violates security policies."""
    pass


class CommandValidator:
    """Pattern-based terminal command validator.
    
    Instead of maintaining a whitelist of specific commands, this validator
    checks for dangerous patterns that should never be allowed.
    """
    
    # Patterns that are ALWAYS dangerous, regardless of context
    DANGEROUS_PATTERNS: List[Tuple[str, str]] = [
        # System destruction
        (r"rm\s+-rf\s+/", "Recursive removal of root directory"),
        (r"rm\s+-rf\s+/\*", "Recursive removal of root contents"),
        (r"mkfs\s+", "Formatting filesystem"),
        (r"dd\s+if=.*of=/dev/", "Direct disk write"),
        
        # Fork bombs
        (r":\(\)\{\s*:\|:&\s*\};:", "Fork bomb"),
        (r"\{\s*: \| : &\s*\};\s*:", "Fork bomb variant"),
        
        # Dangerous redirects
        (r">\s*/dev/sd", "Writing directly to disk device"),
        (r">\s*/dev/mem", "Writing to memory device"),
        
        # Dangerous eval patterns
        (r"eval\s+.*\$", "Eval with variable expansion"),
        (r"\|\s*sh", "Pipe to shell execution"),
        (r"\|\s*bash", "Pipe to bash execution"),
        (r"curl.*\|\s*(sh|bash)", "Curl to shell pipe"),
        (r"wget.*\|\s*(sh|bash)", "Wget to shell pipe"),
        
        # Insecure permissions
        (r"chmod\s+777\s+/", "World-writable root permissions"),
        (r"chmod\s+-R\s+777\s+/", "Recursive world-writable root"),
        
        # System compromise
        (r"passwd\s+root", "Changing root password"),
        (r"useradd\s+-o\s+-u\s+0", "Creating privileged user"),
        (r"echo\s+.*>\s*/etc/passwd", "Modifying passwd file"),
        (r"echo\s+.*>\s*/etc/shadow", "Modifying shadow file"),
        
        # Network pivoting
        (r"iptables\s+-F", "Flushing firewall rules"),
        (r"ufw\s+disable", "Disabling firewall"),
    ]
    
    # Suspicious patterns that need additional context
    SUSPICIOUS_PATTERNS: List[Tuple[str, str]] = [
        (r"sudo\s+", "Elevated privileges (requires confirmation)"),
        (r"rm\s+-rf", "Force recursive removal"),
        (r"chmod\s+777", "World-writable permissions"),
        (r"chown\s+.*:.*\s+/", "Changing root ownership"),
        (r"wget\s+http[s]?://", "Download from internet"),
        (r"curl\s+http[s]?://", "Download from internet"),
        (r"nmap\s+", "Network scanning"),
        (r"ssh\s+.*@", "Remote SSH connection"),
        (r"scp\s+.*@", "Remote file copy"),
    ]
    
    # Allowed command prefixes for common operations
    # These are evaluated AFTER dangerous patterns are checked
    ALLOWED_PREFIXES: List[str] = [
        "git", "python", "python3", "pip", "pip3",
        "npm", "node", "yarn",
        "cargo", "rustc", "go", "golang",
        "apt", "apt-get", "yum", "dnf", "pacman", "brew",
        "docker", "podman",
        "kubectl", "helm",
        "systemctl", "service",
        "journalctl", "log",
        "ping", "traceroute", "dig", "nslookup",
        "ssh", "scp", "rsync",
        "ls", "pwd", "cat", "head", "tail", "less", "more",
        "find", "grep", "awk", "sed", "sort", "uniq", "wc",
        "mkdir", "touch", "cp", "mv", "ln",
        "tar", "gzip", "zip", "unzip", "xz", "bzip2",
        "make", "cmake", "ninja",
        "vim", "nano", "emacs",
        "python -m pip", "python3 -m pip",
    ]
    
    @classmethod
    def validate(cls, command: str) -> bool:
        """Validate a command for safety.
        
        Returns True if safe, raises TerminalSecurityError if dangerous.
        """
        command = command.strip()
        
        if not command:
            raise TerminalSecurityError("Empty command")
        
        # First check for dangerous patterns
        for pattern, description in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                raise TerminalSecurityError(
                    f"Dangerous pattern detected: {description}\n"
                    f"Command: {command}"
                )
        
        # Check for suspicious patterns (log but allow with warning)
        warnings = []
        for pattern, description in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                warnings.append(description)
        
        if warnings:
            # Store warnings for logging (they don't block execution)
            cls._last_warnings = warnings
        
        # Finally, check against allowed prefixes
        # This prevents commands like "rm -rf *" even if not caught above
        first_word = command.split()[0] if command.split() else ""
        
        # Check if command is in allowed prefixes
        allowed = False
        for prefix in cls.ALLOWED_PREFIXES:
            if command.startswith(prefix + " ") or command == prefix:
                allowed = True
                break
        
        if not allowed:
            # For commands not in prefix list, only allow if they're simple executables
            # with no dangerous flags
            if cls._is_simple_command(command):
                return True
            
            raise TerminalSecurityError(
                f"Command not allowed (use allowed prefix list): {first_word}\n"
                f"Command: {command}"
            )
        
        return True
    
    @classmethod
    def _is_simple_command(cls, command: str) -> bool:
        """Check if command is a simple executable with no flags."""
        parts = command.split()
        if len(parts) == 1:
            # Single word command (just executable name)
            # Trust that it's probably safe if not caught by dangerous patterns
            return True
        return False
    
    @classmethod
    def get_last_warnings(cls) -> List[str]:
        """Get warnings from the last validation."""
        return getattr(cls, '_last_warnings', [])