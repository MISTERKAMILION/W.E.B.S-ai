# automation/state.py
"""State management for automation system."""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import threading


class AutomationState(str, Enum):
    """Possible states for the automation system."""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    PAUSED = "paused"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class SystemState:
    """Current system state with metadata."""
    
    state: AutomationState = AutomationState.IDLE
    current_action: Optional[str] = None
    current_module: Optional[str] = None
    progress: float = 0.0  # 0-100
    message: str = ""
    started_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update(self, state: AutomationState, message: str = "", progress: float = None):
        """Update system state."""
        self.state = state
        if message:
            self.message = message
        if progress is not None:
            self.progress = max(0, min(100, progress))
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "state": self.state.value,
            "current_action": self.current_action,
            "current_module": self.current_module,
            "progress": self.progress,
            "message": self.message,
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class StateManager:
    """Thread-safe state manager for automation."""
    
    def __init__(self):
        self._state = SystemState()
        self._lock = threading.Lock()
        self._listeners = []
    
    @property
    def state(self) -> SystemState:
        with self._lock:
            return self._state
    
    def update(self, state: AutomationState, **kwargs):
        """Update system state."""
        with self._lock:
            self._state.update(state, **kwargs)
            self._notify_listeners()
    
    def begin_action(self, module: str, action: str):
        """Mark the beginning of an action."""
        with self._lock:
            self._state.state = AutomationState.RUNNING
            self._state.current_module = module
            self._state.current_action = action
            self._state.started_at = datetime.now()
            self._state.updated_at = datetime.now()
            self._state.message = f"Executing {module}.{action}"
    
    def complete_action(self, message: str = "Action completed"):
        """Mark the completion of an action."""
        with self._lock:
            self._state.state = AutomationState.IDLE
            self._state.current_module = None
            self._state.current_action = None
            self._state.message = message
            self._state.updated_at = datetime.now()
            self._state.progress = 100.0
    
    def add_listener(self, callback):
        """Add a listener for state changes."""
        with self._lock:
            self._listeners.append(callback)
    
    def _notify_listeners(self):
        """Notify all listeners of state change."""
        state_data = self._state.to_dict()
        for listener in self._listeners:
            try:
                listener(state_data)
            except Exception:
                pass  # Don't let listener errors break state management