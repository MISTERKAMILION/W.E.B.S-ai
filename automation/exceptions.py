"""Custom exceptions for the automation module."""


class AutomationError(Exception):
    """Base exception for automation errors."""
    pass


class DesktopAutomationError(AutomationError):
    """Raised when desktop automation fails."""
    pass


class BrowserAutomationError(AutomationError):
    """Raised when browser automation fails."""
    pass


class TerminalAutomationError(AutomationError):
    """Raised when terminal automation fails."""
    pass


class FileSystemAutomationError(AutomationError):
    """Raised when file system automation fails."""
    pass


class ApplicationAutomationError(AutomationError):
    """Raised when application automation fails."""
    pass


class NetworkAutomationError(AutomationError):
    """Raised when network automation fails."""
    pass


class SecurityError(AutomationError):
    """Raised when security validation fails."""
    pass
