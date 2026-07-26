"""Evolution - template self-improvement from failures.

Inspired by JARVIS evolution.py - analyzes failed tasks, detects
patterns, and improves prompts/templates to prevent repeat failures.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "evolution"


@dataclass
class FailureRecord:
    task_type: str
    description: str
    error: str
    timestamp: float = field(default_factory=time.time)
    pattern: str = ""


class FailurePattern:
    """Known failure patterns and their fixes."""

    PATTERNS = [
        (r"ModuleNotFoundError", "missing_import", "Add the module to requirements.txt or install it"),
        (r"FileNotFoundError", "missing_file", "Check file paths exist before operations"),
        (r"SyntaxError", "syntax", "Validate syntax before execution"),
        (r"ImportError", "import_error", "Check module compatibility and imports"),
        (r"PermissionError", "permission", "Check file/directory permissions"),
        (r"ConnectionError|TimeoutError", "network", "Check network connectivity"),
        (r"TypeError.*argument", "type_mismatch", "Validate input types before passing"),
        (r"KeyError|IndexError", "key_error", "Check key/index existence before access"),
    ]

    @classmethod
    def detect(cls, error: str) -> Optional[str]:
        """Detect which pattern matches an error message."""
        for regex, pattern_id, _ in cls.PATTERNS:
            if re.search(regex, error, re.IGNORECASE):
                return pattern_id
        return None

    @classmethod
    def get_fix(cls, pattern_id: str) -> str:
        """Get the fix suggestion for a pattern."""
        for _, pid, fix in cls.PATTERNS:
            if pid == pattern_id:
                return fix
        return "Unknown pattern"


class TemplateEvolver:
    """Analyzes failures and improves templates to prevent repeats."""

    MIN_FAILURES = 3  # Minimum failures before evolving

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._failures_file = DATA_DIR / "failures.json"
        self._templates_file = DATA_DIR / "templates.json"
        self._failures: List[Dict] = self._load(self._failures_file)
        self._templates: Dict[str, str] = self._load_dict(self._templates_file)

    def _load(self, path: Path) -> List[Dict]:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                return []
        return []

    def _load_dict(self, path: Path) -> Dict[str, str]:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                return {}
        return {}

    def _save(self, path: Path, data) -> None:
        path.write_text(json.dumps(data, indent=2))

    def log_failure(
        self, task_type: str, description: str, error: str
    ) -> None:
        """Record a task failure."""
        pattern_id = FailurePattern.detect(error) or "unknown"
        record = {
            "type": task_type,
            "desc": description[:200],
            "error": error[:500],
            "pattern": pattern_id,
            "time": time.time(),
        }
        self._failures.append(record)
        self._save(self._failures_file, self._failures[-200:])

    def analyze_failures(self) -> Dict[str, int]:
        """Count failures by pattern."""
        counts: Dict[str, int] = {}
        for f in self._failures:
            pattern = f.get("pattern", "unknown")
            counts[pattern] = counts.get(pattern, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def should_evolve(self) -> bool:
        """Check if we have enough failures to warrant evolution."""
        return len(self._failures) >= self.MIN_FAILURES

    def get_prevention_rules(self) -> str:
        """Generate prevention rules from known failure patterns."""
        analysis = self.analyze_failures()
        if not analysis:
            return ""

        rules = []
        for pattern_id, count in analysis.items():
            if count >= 2:
                fix = FailurePattern.get_fix(pattern_id)
                rules.append(f"Prevent {pattern_id} ({count} occurrences): {fix}")

        return "\n".join(rules) if rules else ""

    def get_context_string(self) -> str:
        """Get evolution context for LLM prompt injection."""
        rules = self.get_prevention_rules()
        if rules:
            return f"LESSONS LEARNED (from past failures):\n{rules}"
        return ""
