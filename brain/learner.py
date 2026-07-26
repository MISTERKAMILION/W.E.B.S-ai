"""Usage learner - tracks task patterns and project usage.

Inspired by JARVIS learning.py - tracks what the user does most,
suggests context based on fuzzy matching, and provides session stats.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "learner"


@dataclass
class TaskRecord:
    task_type: str
    description: str
    project: str = ""
    success: bool = True
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0


class UsageLearner:
    """Tracks usage patterns and suggests context based on past behavior."""

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._tasks_file = DATA_DIR / "tasks.json"
        self._projects_file = DATA_DIR / "projects.json"
        self._tasks: List[Dict] = self._load(self._tasks_file)
        self._projects: List[Dict] = self._load(self._projects_file)
        self._session_start = time.time()

    def _load(self, path: Path) -> List[Dict]:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                return []
        return []

    def _save(self, path: Path, data: List[Dict]) -> None:
        path.write_text(json.dumps(data[-500:], indent=2))

    def log_task(
        self,
        task_type: str,
        description: str,
        success: bool,
        project: str = "",
        duration: float = 0.0,
    ) -> None:
        """Record a completed task."""
        record = {
            "type": task_type,
            "desc": description[:200],
            "project": project,
            "success": success,
            "time": time.time(),
            "duration": duration,
        }
        self._tasks.append(record)
        self._save(self._tasks_file, self._tasks)

        if project:
            self._touch_project(project)

    def _touch_project(self, name: str) -> None:
        for p in self._projects:
            if p["name"].lower() == name.lower():
                p["last_used"] = time.time()
                p["uses"] = p.get("uses", 0) + 1
                self._save(self._projects_file, self._projects)
                return
        self._projects.append({
            "name": name,
            "uses": 1,
            "last_used": time.time(),
        })
        self._save(self._projects_file, self._projects)

    def suggest_project(self, text: str) -> Optional[str]:
        """Fuzzy-match user text against known projects."""
        if not self._projects:
            return None

        text_lower = text.lower()
        best_name = None
        best_score = 0.0

        for p in self._projects:
            name = p["name"]
            name_lower = name.lower()

            # Exact substring match
            if name_lower in text_lower:
                return name

            # Fuzzy match
            score = SequenceMatcher(None, text_lower, name_lower).ratio()

            # Recency boost
            age = time.time() - p.get("last_used", 0)
            if age < 3600:
                score *= 1.3
            elif age < 86400:
                score *= 1.1

            # Frequency boost
            uses = p.get("uses", 1)
            score *= min(1.0 + uses * 0.05, 1.5)

            if score > best_score:
                best_score = score
                best_name = name

        if best_score > 0.4:
            return best_name
        return None

    def get_frequent_types(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get most common task types."""
        counts: Dict[str, int] = {}
        for t in self._tasks:
            tt = t.get("type", "unknown")
            counts[tt] = counts.get(tt, 0) + 1
        return sorted(counts.items(), key=lambda x: -x[1])[:limit]

    def get_recent_projects(self, limit: int = 5) -> List[str]:
        """Get most recently used projects."""
        sorted_p = sorted(self._projects, key=lambda p: -p.get("last_used", 0))
        return [p["name"] for p in sorted_p[:limit]]

    def get_success_rate(self, task_type: Optional[str] = None) -> float:
        """Get success rate for a task type or overall."""
        relevant = self._tasks
        if task_type:
            relevant = [t for t in self._tasks if t.get("type") == task_type]
        if not relevant:
            return 1.0
        successes = sum(1 for t in relevant if t.get("success", True))
        return successes / len(relevant)

    def get_session_stats(self) -> Dict:
        """Get stats for the current session."""
        elapsed = time.time() - self._session_start
        recent = [t for t in self._tasks if t.get("time", 0) > self._session_start]
        return {
            "session_tasks": len(recent),
            "session_success_rate": (
                sum(1 for t in recent if t.get("success", True)) / len(recent)
                if recent else 1.0
            ),
            "total_tasks": len(self._tasks),
            "total_projects": len(self._projects),
            "session_elapsed": round(elapsed),
        }

    def get_context_string(self) -> str:
        """Build a context string for injection into LLM prompts."""
        lines = []

        freq = self.get_frequent_types(3)
        if freq:
            lines.append("Frequent tasks: " + ", ".join(f"{t}({c})" for t, c in freq))

        recent = self.get_recent_projects(3)
        if recent:
            lines.append("Recent projects: " + ", ".join(recent))

        stats = self.get_session_stats()
        if stats["total_tasks"] > 0:
            lines.append(
                f"History: {stats['total_tasks']} tasks, "
                f"{stats['session_success_rate']:.0%} success"
            )

        return "\n".join(lines) if lines else ""
