"""Dispatcher - tracks in-flight automation tasks.

Inspired by JARVIS dispatch_registry.py - a state machine for
tracking what the system is currently working on.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "dispatcher"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class Dispatch:
    id: str
    prompt: str
    project: str = ""
    working_dir: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""
    summary: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    @property
    def elapsed(self) -> float:
        if not self.started_at:
            return 0
        end = self.completed_at or time.time()
        return end - self.started_at

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "prompt": self.prompt[:200],
            "project": self.project,
            "status": self.status.value,
            "elapsed": round(self.elapsed, 1),
            "summary": self.summary[:200],
        }


class Dispatcher:
    """Tracks all dispatched tasks with status management."""

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._dispatches: Dict[str, Dispatch] = {}
        self._history_file = DATA_DIR / "history.json"
        self._load_history()

    def _load_history(self) -> None:
        if self._history_file.exists():
            try:
                data = json.loads(self._history_file.read_text())
                for d in data[-100:]:
                    self._dispatches[d["id"]] = Dispatch(
                        id=d["id"],
                        prompt=d.get("prompt", ""),
                        project=d.get("project", ""),
                        status=TaskStatus(d.get("status", "completed")),
                        result=d.get("result", ""),
                        summary=d.get("summary", ""),
                    )
            except Exception:
                pass

    def _save_history(self) -> None:
        completed = [
            d.to_dict()
            for d in self._dispatches.values()
            if d.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        ]
        self._history_file.write_text(json.dumps(completed[-100:], indent=2))

    def register(self, prompt: str, project: str = "", working_dir: str = "") -> str:
        """Register a new dispatch. Returns task ID."""
        task_id = str(uuid.uuid4())[:8]
        dispatch = Dispatch(
            id=task_id,
            prompt=prompt,
            project=project,
            working_dir=working_dir,
        )
        self._dispatches[task_id] = dispatch
        logger.info(f"Dispatch registered: {task_id} - {prompt[:60]}")
        return task_id

    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: str = "",
        summary: str = "",
    ) -> None:
        """Update a dispatch's status."""
        d = self._dispatches.get(task_id)
        if not d:
            return

        d.status = status
        if status == TaskStatus.RUNNING and not d.started_at:
            d.started_at = time.time()
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT):
            d.completed_at = time.time()
            d.result = result
            d.summary = summary
            self._save_history()

        logger.info(f"Dispatch {task_id}: {status.value}")

    def get_active(self) -> List[Dispatch]:
        """Get all active (pending/running) dispatches."""
        return [
            d for d in self._dispatches.values()
            if d.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
        ]

    def get_recent(self, limit: int = 5) -> List[Dispatch]:
        """Get most recent completed dispatches."""
        completed = [
            d for d in self._dispatches.values()
            if d.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        ]
        completed.sort(key=lambda d: d.completed_at or 0, reverse=True)
        return completed[:limit]

    def get_most_recent(self, project: str = "") -> Optional[Dispatch]:
        """Get the most recent dispatch, optionally filtered by project."""
        items = list(self._dispatches.values())
        if project:
            items = [d for d in items if project.lower() in d.project.lower()]
        if not items:
            return None
        return max(items, key=lambda d: d.created_at)

    def format_for_prompt(self) -> str:
        """Format active and recent dispatches for LLM context injection."""
        lines = []

        active = self.get_active()
        if active:
            lines.append("ACTIVE TASKS:")
            for d in active:
                elapsed = f"{d.elapsed:.0f}s" if d.started_at else "queued"
                lines.append(f"- [{d.id}] RUNNING ({elapsed}): {d.prompt[:80]}")

        recent = self.get_recent(3)
        if recent:
            lines.append("RECENT COMPLETED:")
            for d in recent:
                status = d.status.value.upper()
                lines.append(f"- [{d.id}] {status}: {d.summary[:80]}")

        return "\n".join(lines) if lines else "No active tasks."
