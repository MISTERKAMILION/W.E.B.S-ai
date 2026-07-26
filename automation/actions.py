"""Action definitions and types for automation.

Provides structured representations of automation actions and results,
with support for tracking, priority, and execution metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class ActionStatus(str, Enum):
    """Status of an automation action."""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    TIMEOUT = "timeout"


class ActionPriority(str, Enum):
    """Priority level for action execution."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AutomationAction:
    """Structured automation action sent by the Brain.
    
    Includes tracking, priority, and timing information for better
    workflow management and debugging.
    
    Example:
        action = AutomationAction(
            module="browser",
            action="click",
            params={"selector": ".submit-button"},
            priority=ActionPriority.HIGH
        )
    """
    module: str  # desktop, browser, terminal, filesystem, applications, network
    action: str  # click, type, run, etc.
    params: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)
    priority: ActionPriority = ActionPriority.NORMAL

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "module": self.module,
            "action": self.action,
            "params": self.params,
            "created_at": self.created_at.isoformat(),
            "priority": self.priority.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutomationAction":
        """Create from dictionary."""
        return cls(
            module=data.get("module", ""),
            action=data.get("action", ""),
            params=data.get("params", {}),
            id=data.get("id", str(uuid.uuid4())[:8]),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data and isinstance(data["created_at"], str)
            else datetime.now(),
            priority=ActionPriority(data.get("priority", "normal")),
        )


@dataclass
class AutomationResult:
    """Standardized result from automation execution.
    
    Includes execution metrics for performance tracking and analysis.
    
    Example success:
        result = AutomationResult(
            status=ActionStatus.SUCCESS,
            module="browser",
            action="click",
            output=None,
            execution_time=0.42
        )
    """
    status: ActionStatus
    module: str
    action: str
    output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0  # seconds
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "module": self.module,
            "action": self.action,
            "output": self.output,
            "error": self.error,
            "execution_time": round(self.execution_time, 3),
            "started_at": self.started_at.isoformat()
            if self.started_at
            else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }

    @property
    def is_success(self) -> bool:
        """Check if action succeeded."""
        return self.status == ActionStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        """Check if action failed."""
        return self.status == ActionStatus.FAILURE
