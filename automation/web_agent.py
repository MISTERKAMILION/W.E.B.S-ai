"""Browser agent using browser-use for autonomous web tasks.

Falls back to opening a Google search in the default browser if
browser-use / playwright are not installed.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

_HAS_BROWSER_USE = False
try:
    from browser_use import Agent  # type: ignore

    _HAS_BROWSER_USE = True
except ImportError:
    Agent = None  # type: ignore
    logger.info("browser-use not installed; web agent will use browser fallback")


def _get_llm():
    """Build a LangChain Groq LLM for browser-use, if available."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None
    try:
        from langchain_groq import ChatGroq

        return ChatGroq(
            groq_api_key=api_key,
            model_name=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        )
    except ImportError:
        logger.warning("langchain-groq not installed")
        return None


async def _run_browser_agent(task: str) -> str:
    """Run browser-use Agent asynchronously."""
    llm = _get_llm()
    if llm is None:
        raise RuntimeError("Groq LLM unavailable for browser agent")

    agent = Agent(task=task, llm=llm)
    result = await agent.run()
    return str(result)


def do_web_task(task: str, timeout: int = 180) -> str:
    """Execute an autonomous browser task.

    Uses browser-use when installed; otherwise opens a Google search.
    """
    task = (task or "").strip()
    if not task:
        return "No web task specified."

    if _HAS_BROWSER_USE:
        try:
            return asyncio.run(asyncio.wait_for(_run_browser_agent(task), timeout=timeout))
        except Exception as e:
            logger.error(f"browser-use failed: {e}")
            # Fall through to simple open

    # Fallback: open search in default browser
    url = f"https://www.google.com/search?q={quote(task)}"
    try:
        subprocess.Popen(
            ["xdg-open", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"Opened browser search for: {task}"
    except Exception as e:
        return f"Web task failed: {e}"


def is_browser_agent_available() -> bool:
    """Return True if full browser-use agent can run."""
    return _HAS_BROWSER_USE and bool(os.environ.get("GROQ_API_KEY"))
