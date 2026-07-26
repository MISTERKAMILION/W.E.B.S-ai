"""
memory.py
---------

Memory system for W.E.B.S.

Responsibilities
----------------
- Store conversation history
- Store user preferences
- Save memory to disk
- Load memory from disk

This module NEVER:
- Talks to the AI model
- Makes decisions
- Executes automation
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


class Memory:
    """
    W.E.B.S Memory Manager
    """

    def __init__(self):

        # Create memory folder if it doesn't exist
        self.memory_dir = Path("memory")
        self.memory_dir.mkdir(exist_ok=True)

        self.history_file = self.memory_dir / "history.json"
        self.preferences_file = self.memory_dir / "preferences.json"

        self.history: List[Dict[str, str]] = []
        self.preferences: Dict[str, str] = {}

        self.load()

    # --------------------------------------------------
    # Conversation History
    # --------------------------------------------------

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation history.
        """

        self.history.append({
            "role": role,
            "content": content
        })

    def get_history(self) -> List[Dict[str, str]]:
        """
        Return the full conversation history.
        """

        return self.history

    def clear_history(self) -> None:
        """
        Clear conversation history.
        """

        self.history.clear()
        self.save()

    # --------------------------------------------------
    # Preferences
    # --------------------------------------------------

    def remember(self, key: str, value: str) -> None:
        """
        Save a user preference.
        """

        self.preferences[key] = value
        self.save()

    def recall(self, key: str, default=None):
        """
        Recall a stored preference.
        """

        return self.preferences.get(key, default)

    def forget(self, key: str) -> None:
        """
        Remove a stored preference.
        """

        self.preferences.pop(key, None)
        self.save()

    def get_preferences(self) -> Dict[str, str]:
        """
        Return all stored preferences.
        """

        return self.preferences

    # --------------------------------------------------
    # Save / Load
    # --------------------------------------------------

    def save(self) -> None:
        """
        Save memory to disk.
        """

        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(
                self.history,
                f,
                indent=4,
                ensure_ascii=False
            )

        with open(self.preferences_file, "w", encoding="utf-8") as f:
            json.dump(
                self.preferences,
                f,
                indent=4,
                ensure_ascii=False
            )

    def load(self) -> None:
        """
        Load memory from disk.
        """

        if self.history_file.exists():
            with open(self.history_file, "r", encoding="utf-8") as f:
                self.history = json.load(f)

        if self.preferences_file.exists():
            with open(self.preferences_file, "r", encoding="utf-8") as f:
                self.preferences = json.load(f)