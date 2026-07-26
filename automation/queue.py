"""Priority queue for automation actions.

Allows the Brain to enqueue actions asynchronously, with support for
priority levels, progress tracking, and workflow management.
"""

from queue import PriorityQueue
from threading import Lock
from typing import Callable, List, Optional

from .actions import ActionPriority, AutomationAction


class AutomationQueue:
    """Priority queue for managing automation actions.
    
    Supports priority-based execution, listener notifications,
    and workflow orchestration.
    """

    def __init__(self):
        """Initialize the automation queue."""
        self.queue = PriorityQueue()
        self.lock = Lock()
        self._count = 0
        self._listeners: List[Callable[[AutomationAction], None]] = []

    def enqueue(self, action: AutomationAction) -> str:
        """Add an action to the queue with priority.

        Args:
            action: The AutomationAction to enqueue.

        Returns:
            The action ID.
        """
        # Priority mapping (lower number = higher priority)
        priority_map = {
            ActionPriority.CRITICAL: 0,
            ActionPriority.HIGH: 1,
            ActionPriority.NORMAL: 2,
            ActionPriority.LOW: 3,
        }

        with self.lock:
            self._count += 1
            priority = (priority_map[action.priority], self._count)
            self.queue.put((priority, action))

            # Notify listeners
            for listener in self._listeners:
                try:
                    listener(action)
                except Exception:
                    pass

        return action.id

    def dequeue(self, timeout: Optional[float] = None) -> Optional[AutomationAction]:
        """Get the next action from the queue.

        Args:
            timeout: Maximum time to wait in seconds.

        Returns:
            Next AutomationAction or None if queue is empty.
        """
        try:
            priority, action = self.queue.get(timeout=timeout)
            return action
        except Exception:
            return None

    def size(self) -> int:
        """Get the current queue size.

        Returns:
            Number of pending actions.
        """
        return self.queue.qsize()

    def is_empty(self) -> bool:
        """Check if queue is empty.

        Returns:
            True if no actions pending.
        """
        return self.queue.empty()

    def clear(self) -> None:
        """Clear all actions from the queue."""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except Exception:
                break

    def add_listener(self, callback: Callable[[AutomationAction], None]) -> None:
        """Add a listener for new enqueued actions.

        Args:
            callback: Function to call when action is enqueued.
                      Receives AutomationAction as argument.
        """
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[AutomationAction], None]) -> None:
        """Remove a listener.

        Args:
            callback: Listener function to remove.
        """
        if callback in self._listeners:
            self._listeners.remove(callback)

    def get_status(self) -> dict:
        """Get queue status.

        Returns:
            Dictionary with queue information.
        """
        return {
            "pending": self.size(),
            "is_empty": self.is_empty(),
            "listeners": len(self._listeners),
        }
