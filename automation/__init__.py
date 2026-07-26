"""Automation package for the WEBS application.

Design Principle: Capability-based, not library-based.

This package provides high-level automation capabilities without exposing
implementation details. The Brain receives and sends standardized action/result
objects, and the Automation dispatcher routes them to appropriate modules.

Features:
- Central dispatcher with priority queuing
- Security validation for terminal commands
- Structured logging and metrics
- Action tracking with IDs and timestamps
- Capability detection
- Abstract backend interfaces for browser automation

Usage:
    from automation import Automation, AutomationAction, ActionPriority
    
    # Initialize the dispatcher
    automation = Automation()
    
    # Execute a single action
    action = AutomationAction(
        module="browser",
        action="click",
        params={"selector": ".submit-button"},
        priority=ActionPriority.HIGH
    )
    result = automation.execute(action)
    
    # Or execute multiple actions as a workflow
    workflow = [
        {"module": "applications", "action": "open", "params": {"target": "firefox"}},
        {"module": "browser", "action": "goto", "params": {"url": "https://example.com"}},
    ]
    results = automation.execute_workflow(workflow)
    
    # Or queue actions asynchronously
    action_ids = automation.execute_workflow_async(workflow)
    
    # Get capabilities
    caps = automation.get_capabilities()
    
    # Get statistics
    stats = automation.get_statistics()
"""

from .actions import ActionPriority, ActionStatus, AutomationAction, AutomationResult
from .applications import ApplicationAutomation
from .automation import Automation
from .browser import BrowserAutomation
from .browser_backends import BrowserBackend, PlaywrightBackend, SeleniumBackend
from .desktop import DesktopAutomation
from .exceptions import (
    ApplicationAutomationError,
    AutomationError,
    BrowserAutomationError,
    DesktopAutomationError,
    FileSystemAutomationError,
    NetworkAutomationError,
    SecurityError,
    TerminalAutomationError,
)
from .filesystem import FilesystemAutomation
from .logger import AutomationLogger
from .network import NetworkAutomation
from .queue import AutomationQueue
from .terminal import TerminalAutomation
from .validator import CommandValidator as TerminalCommandValidator

__all__ = [
    # Main dispatcher
    "Automation",
    # Action/Result types
    "AutomationAction",
    "AutomationResult",
    "ActionStatus",
    "ActionPriority",
    # Capability modules
    "DesktopAutomation",
    "BrowserAutomation",
    "TerminalAutomation",
    "FilesystemAutomation",
    "ApplicationAutomation",
    "NetworkAutomation",
    # Support systems
    "AutomationQueue",
    "AutomationLogger",
    "TerminalCommandValidator",
    # Browser backends
    "BrowserBackend",
    "PlaywrightBackend",
    "SeleniumBackend",
    # Exceptions
    "AutomationError",
    "DesktopAutomationError",
    "BrowserAutomationError",
    "TerminalAutomationError",
    "FileSystemAutomationError",
    "ApplicationAutomationError",
    "NetworkAutomationError",
    "SecurityError",
]

# Create a default automation instance for convenient access
automation = Automation()

