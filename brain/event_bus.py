"""
event_bus.py
------------

Event bus for W.E.B.S.

Decoupled communication between modules.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==========================================================
# Data Models
# ==========================================================

class EventType(str, Enum):
    """Types of events."""

    # System
    SYSTEM_START = "system:start"
    SYSTEM_STOP = "system:stop"

    # Brain
    BRAIN_THINKING = "brain:thinking"
    BRAIN_RESPONDING = "brain:responding"
    BRAIN_DONE = "brain:done"
    BRAIN_ERROR = "brain:error"

    # Planner
    PLANNER_PLANNING = "planner:planning"
    PLANNER_PLAN_CREATED = "planner:plan_created"
    PLANNER_TASK_START = "planner:task_start"
    PLANNER_TASK_COMPLETE = "planner:task_complete"
    PLANNER_TASK_FAILED = "planner:task_failed"

    # Collector
    COLLECTOR_SEARCHING = "collector:searching"
    COLLECTOR_FETCHING = "collector:fetching"
    COLLECTOR_RESULT = "collector:result"

    # Automation
    AUTOMATION_START = "automation:start"
    AUTOMATION_COMPLETE = "automation:complete"
    AUTOMATION_ERROR = "automation:error"

    # Voice
    VOICE_SPEAKING = "voice:speaking"
    VOICE_DONE = "voice:done"
    VOICE_IDLE = "voice:idle"
    VOICE_LISTENING = "voice:listening"

    # Memory
    MEMORY_STORE = "memory:store"
    MEMORY_RECALL = "memory:recall"


@dataclass(slots=True)
class Event:
    """An event in the system."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.SYSTEM_START
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: int = 0  # 0 = highest

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
        }


# ==========================================================
# Event Bus
# ==========================================================

class EventBus:
    """
    Central event bus for decoupled communication.

    Usage:
        bus = EventBus()

        # Subscribe
        bus.subscribe(EventType.BRAIN_RESPONDING, on_response)

        # Publish
        bus.publish(Event(
            type=EventType.BRAIN_RESPONDING,
            source="brain",
            data={"response": "Hello"}
        ))
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._wildcard_subscribers: List[Callable] = []
        self._event_queue: List[Event] = []
        self._lock = threading.RLock()
        self._running = True
        self._processing_thread = None

        # Start processing thread
        self._start_processor()

        logger.info("EventBus initialized")

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """Subscribe to an event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type.value}")

    def subscribe_all(self, callback: Callable) -> None:
        """Subscribe to all events."""
        with self._lock:
            self._wildcard_subscribers.append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """Unsubscribe from an event type."""
        with self._lock:
            if event_type in self._subscribers:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)

    def publish(self, event: Event) -> None:
        """Publish an event (async)."""
        with self._lock:
            self._event_queue.append(event)
        logger.debug(f"Event published: {event.type.value}")

    def publish_sync(self, event: Event) -> None:
        """Publish an event and process immediately."""
        self._process_event(event)

    def _start_processor(self) -> None:
        """Start the event processing thread."""

        def processor():
            while self._running:
                event = None
                try:
                    with self._lock:
                        if self._event_queue:
                            event = self._event_queue.pop(0)
                    if event is not None:
                        self._process_event(event)
                    else:
                        time.sleep(0.01)
                except Exception as e:
                    logger.error(f"Event processor error: {e}")

        self._processing_thread = threading.Thread(
            target=processor, name="EventProcessor", daemon=True
        )
        self._processing_thread.start()

    def _process_event(self, event: Event) -> None:
        """Process a single event."""
        # Copy callbacks outside lock to avoid deadlock
        wildcard = list(self._wildcard_subscribers)
        specific = []
        with self._lock:
            if event.type in self._subscribers:
                specific = self._subscribers[event.type].copy()

        for callback in wildcard:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Wildcard subscriber error: {e}")

        for callback in specific:
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    f"Event handler error for {event.type.value}: {e}"
                )

    def stop(self) -> None:
        """Stop the event bus."""
        self._running = False
        if self._processing_thread:
            self._processing_thread.join(timeout=2)
        logger.info("EventBus stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        with self._lock:
            return {
                "queue_size": len(self._event_queue),
                "subscribers": len(self._subscribers),
                "wildcard_subscribers": len(self._wildcard_subscribers),
                "event_types": list(self._subscribers.keys()),
            }
