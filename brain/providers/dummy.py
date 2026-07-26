"""Dummy provider for offline/testing fallbacks."""

from __future__ import annotations

from typing import Dict, List


class DummyProvider:
    """Simple stub provider that echoes a canned response."""

    name = "dummy"

    def __init__(self, reply: str = "W.E.B.S is ready, sir.") -> None:
        self.reply = reply

    @property
    def available(self) -> bool:
        return True

    def generate(self, messages: List[Dict[str, str]]) -> str:
        return self.reply
