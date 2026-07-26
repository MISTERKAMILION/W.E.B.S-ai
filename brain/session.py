"""
session.py
----------

Session management for W.E.B.S.

Responsibilities:
- Track user sessions
- Maintain session state
- Store session-specific data
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionStatus(str, Enum):
    """Status of a session."""
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


@dataclass(slots=True)
class Session:
    """Represents a user session."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default"
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    messages: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    current_plan_id: Optional[str] = None

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the session."""
        self.messages.append({"role": role, "content": content})
        self.last_activity = time.time()

    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Get session messages."""
        if limit:
            return self.messages[-limit:]
        return self.messages

    def clear_messages(self) -> None:
        """Clear session messages."""
        self.messages.clear()

    def is_active(self) -> bool:
        """Check if session is active."""
        return self.status == SessionStatus.ACTIVE

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "message_count": len(self.messages),
        }


class SessionManager:
    """Manages user sessions."""

    def __init__(self, max_sessions: int = 100):
        self.max_sessions = max_sessions
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.RLock()

    def create_session(self, user_id: str = "default") -> Session:
        """Create a new session."""
        with self._lock:
            session = Session(user_id=user_id)
            self._sessions[session.id] = session

            # Enforce max sessions
            if len(self._sessions) > self.max_sessions:
                self._cleanup_old_sessions()

            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def get_or_create_session(
        self, session_id: Optional[str] = None
    ) -> Session:
        """Get existing session or create new one."""
        with self._lock:
            if session_id:
                session = self._sessions.get(session_id)
                if session and session.is_active():
                    session.touch()
                    return session

            return self.create_session()

    def end_session(self, session_id: str) -> bool:
        """End a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.status = SessionStatus.ENDED
                return True
            return False

    def list_sessions(self, active_only: bool = True) -> List[Session]:
        """List all sessions."""
        with self._lock:
            sessions = list(self._sessions.values())
            if active_only:
                sessions = [s for s in sessions if s.is_active()]
            return sessions

    def _cleanup_old_sessions(self) -> None:
        """Remove oldest inactive sessions."""
        inactive = [
            s for s in self._sessions.values()
            if not s.is_active()
        ]
        inactive.sort(key=lambda s: s.last_activity)

        # Remove oldest inactive sessions
        for session in inactive[:len(inactive) // 2]:
            del self._sessions[session.id]

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        with self._lock:
            active = sum(1 for s in self._sessions.values() if s.is_active())
            return {
                "total_sessions": len(self._sessions),
                "active_sessions": active,
                "max_sessions": self.max_sessions,
            }
