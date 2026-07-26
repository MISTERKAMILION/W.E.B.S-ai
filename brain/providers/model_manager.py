"""Model manager - selects and switches between providers."""

from __future__ import annotations

from typing import Dict, List, Optional

from brain.providers.dummy import DummyProvider
from brain.providers.online import OnlineProvider
from brain.providers.offline import OfflineProvider
from brain.providers.puter import PuterProvider


class ModelManager:
    """Manages available model providers and selects the best one."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        offline_model: str = "llama3.2:3b",
    ) -> None:
        self.providers: Dict[str, object] = {}

        # Always register dummy as fallback
        self.providers["dummy"] = DummyProvider()

        # Register online provider if API key is available
        online = OnlineProvider(api_key=api_key)
        if online.available:
            self.providers["groq"] = online

        # Register offline provider if Ollama is running
        offline = OfflineProvider(model_name=offline_model)
        if offline.available:
            self.providers["ollama"] = offline

        # Register Puter provider if auth token is set
        import os
        if os.environ.get("PUTER_AUTH_TOKEN"):
            self.providers["puter"] = PuterProvider()

        # Select best available provider
        self._current = self._select_best()

    def _select_best(self) -> str:
        """Pick the best provider: groq > ollama > puter > dummy."""
        if "groq" in self.providers:
            return "groq"
        if "ollama" in self.providers:
            return "ollama"
        if "puter" in self.providers:
            return "puter"
        return "dummy"

    def get_current_provider(self) -> Optional[str]:
        """Return the name of the current provider."""
        return self._current

    def get_provider(self):
        """Return the current provider object."""
        return self.providers.get(self._current)

    def switch_to(self, name: str) -> bool:
        """Switch to a named provider. Returns True on success."""
        if name in self.providers:
            self._current = name
            return True
        return False

    def list_providers(self) -> List[str]:
        """Return names of all registered providers."""
        return list(self.providers.keys())

    def generate(self, messages: List[Dict[str, str]]) -> str:
        """Generate a response using the current provider."""
        provider = self.get_provider()
        if provider is None:
            return "No model provider available."
        return provider.generate(messages)
