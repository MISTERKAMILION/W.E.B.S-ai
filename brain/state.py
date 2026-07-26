"""
state.py
--------

State machine for W.E.B.S.

Tracks system state for UI and internal coordination.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==========================================================
# States
# ==========================================================

class SystemState(str, Enum):
    """Possible states for W.E.B.S."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    LISTENING = "listening"
    THINKING = "thinking"
    SEARCHING = "searching"
    FETCHING = "fetching"
    EXECUTING = "executing"
    SPEAKING = "speaking"
    WAITING = "waiting"
    ERROR = "error"
    SLEEPING = "sleeping"


@dataclass(slots=True)
class StateChange:
    """Record of a state change."""

    from_state: SystemState
    to_state: SystemState
    timestamp: float = field(default_factory=time.time)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_state.value,
            "to": self.to_state.value,
            "timestamp": self.timestamp,
            "reason": self.reason,
        }


# ==========================================================
# State Manager
# ==========================================================

class StateManager:
    """
    Manages W.E.B.S. state.

    Publishes state changes to the event bus.
    """

    def __init__(self, event_bus=None):
        self.current_state = SystemState.IDLE
        self.previous_state = SystemState.IDLE
        self.history: List[StateChange] = []
        self.max_history = 100
        self._event_bus = event_bus
        self._lock = threading.RLock()

        logger.info(f"StateManager initialized: {self.current_state.value}")

    def set_state(self, new_state: SystemState, reason: str = "") -> None:
        """Change the current state."""
        should_publish = False
        change_data = None

        with self._lock:
            if new_state == self.current_state:
                return

            change = StateChange(
                from_state=self.current_state,
                to_state=new_state,
                reason=reason,
            )

            self.previous_state = self.current_state
            self.current_state = new_state

            # Add to history
            self.history.append(change)
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]

            logger.info(
                f"State change: {change.from_state.value} -> "
                f"{change.to_state.value} ({reason})"
            )

            # Prepare event data outside lock
            if self._event_bus:
                should_publish = True
                change_data = {
                    "from_state": change.from_state.value,
                    "to_state": change.to_state.value,
                    "reason": reason,
                }

        # Publish event outside lock
        if should_publish and self._event_bus:
            from brain.event_bus import Event, EventType

            self._event_bus.publish(
                Event(
                    type=EventType.SYSTEM_START,
                    source="state",
                    data=change_data,
                )
            )

    def get_state(self) -> SystemState:
        """Get current state."""
        with self._lock:
            return self.current_state

    def is_idle(self) -> bool:
        return self.current_state == SystemState.IDLE

    def is_processing(self) -> bool:
        return self.current_state in [
            SystemState.THINKING,
            SystemState.SEARCHING,
            SystemState.FETCHING,
            SystemState.EXECUTING,
        ]

    def is_speaking(self) -> bool:
        return self.current_state == SystemState.SPEAKING

    def is_listening(self) -> bool:
        return self.current_state == SystemState.LISTENING

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get state history."""
        with self._lock:
            return [c.to_dict() for c in self.history[-limit:]]

    def get_duration(self, state: SystemState) -> float:
        """Get duration of current state."""
        # Find when we entered this state
        for change in reversed(self.history):
            if change.to_state == state:
                return time.time() - change.timestamp
        return 0.0

    def reset(self) -> None:
        """Reset state manager."""
        with self._lock:
            self.current_state = SystemState.IDLE
            self.previous_state = SystemState.IDLE
            self.history = []
