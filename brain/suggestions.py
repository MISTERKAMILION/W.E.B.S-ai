"""Suggestions - post-task proactive follow-up suggestions.

Inspired by JARVIS suggestions.py - after a task completes,
suggests exactly 1 next logical step using file heuristics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Suggestion:
    text: str
    action_type: str  # "build", "browse", "fix", "test", "document"
    action_details: dict


def suggest_followup(
    task_type: str,
    task_description: str,
    working_dir: str = "",
    result: str = "",
) -> Optional[Suggestion]:
    """Generate one proactive suggestion after a task completes.

    Uses file-system heuristics, no LLM calls.
    """
    if not working_dir:
        return None

    project = Path(working_dir)

    if not project.exists():
        return None

    # Check for missing tests
    has_tests = any(project.rglob("test_*.py")) or any(project.rglob("*_test.py"))
    if not has_tests and task_type in ("build", "fix"):
        return Suggestion(
            text="I noticed there are no tests yet. Want me to add some?",
            action_type="test",
            action_details={"directory": working_dir},
        )

    # Check for missing README
    has_readme = (project / "README.md").exists() or (project / "readme.md").exists()
    if not has_readme and task_type == "build":
        return Suggestion(
            text="There's no README yet. Shall I create one?",
            action_type="document",
            action_details={"directory": working_dir, "file": "README.md"},
        )

    # Check for missing requirements.txt
    has_requirements = (project / "requirements.txt").exists()
    has_setup = (project / "setup.py").exists() or (project / "pyproject.toml").exists()
    if not has_requirements and not has_setup and task_type == "build":
        return Suggestion(
            text="No requirements file found. Want me to generate one?",
            action_type="document",
            action_details={"directory": working_dir, "file": "requirements.txt"},
        )

    # Check for linting issues (placeholder - would need actual linting)
    has_linter_config = (
        (project / ".flake8").exists()
        or (project / "pyproject.toml").exists()
        or (project / ".eslintrc.json").exists()
    )
    if not has_linter_config and task_type == "build":
        return Suggestion(
            text="No linter config found. Want me to set one up?",
            action_type="fix",
            action_details={"directory": working_dir},
        )

    return None
