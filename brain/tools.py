"""
tools.py
--------

Tool registry for W.E.B.S.

Allows dynamic registration and execution of tools.
"""

from __future__ import annotations

import inspect
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==========================================================
# Data Models
# ==========================================================

class ToolCategory(str, Enum):
    """Categories of tools."""
    SEARCH = "search"
    WEB = "web"
    AUTOMATION = "automation"
    FILE = "file"
    SYSTEM = "system"
    UTILITY = "utility"
    AI = "ai"


@dataclass(slots=True)
class Tool:
    """A tool that can be called by the Brain."""

    name: str
    description: str
    func: Callable
    category: ToolCategory = ToolCategory.UTILITY
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    is_async: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters,
            "requires_confirmation": self.requires_confirmation,
        }

    def execute(self, *args, **kwargs) -> Any:
        """Execute the tool."""
        try:
            if self.is_async:
                import asyncio
                return asyncio.run(self.func(*args, **kwargs))
            return self.func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Tool {self.name} failed: {str(e)}")
            raise


# ==========================================================
# Tool Registry
# ==========================================================

class ToolRegistry:
    """
    Registry for all available tools.

    Usage:
        registry = ToolRegistry()

        @registry.register("search", "Search the web")
        def search(query: str) -> str:
            return results

        tools = registry.list_tools()
        result = registry.execute("search", query="Python")
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._lock = threading.RLock()
        logger.info("ToolRegistry initialized")

    def register(
        self,
        name: str,
        description: str,
        category: ToolCategory = ToolCategory.UTILITY,
        requires_confirmation: bool = False,
    ) -> Callable:
        """
        Decorator to register a tool.

        Usage:
            @registry.register("search", "Search the web")
            def search(query: str):
                return "Results"
        """

        def decorator(func: Callable) -> Callable:
            # Extract parameter info
            sig = inspect.signature(func)
            parameters = {}
            for param_name, param in sig.parameters.items():
                param_type = param.annotation
                if param_type is inspect.Parameter.empty:
                    param_type = str
                parameters[param_name] = {
                    "type": (
                        param_type.__name__
                        if hasattr(param_type, "__name__")
                        else str(param_type)
                    ),
                    "required": param.default is inspect.Parameter.empty,
                    "default": (
                        param.default
                        if param.default is not inspect.Parameter.empty
                        else None
                    ),
                }

            tool = Tool(
                name=name,
                description=description,
                func=func,
                category=category,
                parameters=parameters,
                requires_confirmation=requires_confirmation,
                is_async=inspect.iscoroutinefunction(func),
            )

            with self._lock:
                self._tools[name] = tool

            logger.info(f"Registered tool: {name}")
            return func

        return decorator

    def register_tool(self, tool: Tool) -> None:
        """Register a tool instance."""
        with self._lock:
            self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        with self._lock:
            if name in self._tools:
                del self._tools[name]
                return True
        return False

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        with self._lock:
            return self._tools.get(name)

    def list_tools(
        self, category: Optional[ToolCategory] = None
    ) -> List[Tool]:
        """List all tools or tools in a category."""
        with self._lock:
            tools = list(self._tools.values())
            if category:
                tools = [t for t in tools if t.category == category]
            return tools

    def list_tool_names(self) -> List[str]:
        """List all tool names."""
        with self._lock:
            return list(self._tools.keys())

    def execute(self, name: str, **kwargs) -> Any:
        """Execute a tool by name."""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        return tool.execute(**kwargs)

    def get_tools_for_prompt(self) -> str:
        """Get a formatted list of tools for the prompt."""
        tools = self.list_tools()
        result = "Available Tools:\n"
        for tool in tools:
            params = ", ".join(
                [f"{k}: {v['type']}" for k, v in tool.parameters.items()]
            )
            result += f"  - {tool.name}({params}): {tool.description}\n"
        return result
