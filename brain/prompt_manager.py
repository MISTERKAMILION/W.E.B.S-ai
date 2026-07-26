"""
prompt_manager.py
-----------------

Manages prompt templates for W.E.B.S.

Loads prompt files from the prompts directory and provides
methods to render them with variables.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manages prompt templates.

    Loads all .txt files from the prompts directory and provides
    methods to render them with variables.
    """

    def __init__(self, prompts_dir: Optional[str] = None):
        self.prompts_dir = Path(
            prompts_dir or Path(__file__).resolve().parent / "prompts"
        )
        self._cache: Dict[str, str] = {}
        self._load_prompts()

    def _load_prompts(self) -> None:
        """Load all prompt files from the prompts directory."""
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self.prompts_dir}")
            return

        for file in sorted(self.prompts_dir.glob("*.txt")):
            try:
                text = file.read_text(encoding="utf-8").strip()
                if text:
                    self._cache[file.stem] = text
                    logger.debug(f"Loaded prompt: {file.name}")
            except Exception as e:
                logger.error(f"Failed to load prompt {file.name}: {e}")

        logger.info(f"Loaded {len(self._cache)} prompts from {self.prompts_dir}")

    def get_prompt(self, name: str) -> str:
        """Get a prompt by name (filename without .txt)."""
        return self._cache.get(name, "")

    def render_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Render the system prompt with context."""
        # Combine all prompts in order
        order = ["system", "personality", "rules", "capabilities", "format"]
        parts = []
        for name in order:
            prompt = self.get_prompt(name)
            if prompt:
                parts.append(prompt)

        result = "\n\n".join(parts)

        # Replace variables if context provided
        if context:
            for key, value in context.items():
                placeholder = f"{{{{{key}}}}}"
                if placeholder in result:
                    result = result.replace(placeholder, str(value))

        return result

    def render_chat_prompt(
        self,
        user_input: str,
        memory_context: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """Render a chat prompt with system message and user input."""
        messages = []

        # System message
        system = self.render_system_prompt(additional_context)
        messages.append({"role": "system", "content": system})

        # Memory context if provided
        if memory_context:
            messages.append({
                "role": "system",
                "content": f"Memory context:\n{memory_context}",
            })

        # User message
        messages.append({"role": "user", "content": user_input})

        return messages

    def list_prompts(self) -> List[str]:
        """List all loaded prompt names."""
        return list(self._cache.keys())

    def reload(self) -> None:
        """Reload all prompts from disk."""
        self._cache.clear()
        self._load_prompts()

    def add_prompt(self, name: str, content: str) -> None:
        """Add or update a prompt."""
        self._cache[name] = content

    def remove_prompt(self, name: str) -> bool:
        """Remove a prompt."""
        if name in self._cache:
            del self._cache[name]
            return True
        return False
