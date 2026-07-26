"""
planner.py
----------

The Planner analyzes a user request and determines what
the Brain should do next.

IMPORTANT
---------
The Planner NEVER:
- Talks to the AI model
- Executes automation
- Reads or writes memory
- Collects data

Its ONLY responsibility is to analyze the request and
produce a structured execution plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# ==========================================================
# PLAN OBJECT
# ==========================================================

@dataclass
class Plan:
    """Represents the execution plan produced by the Planner."""

    # conversation / information / automation / memory / unknown
    intent: str = "conversation"

    # Required modules
    need_model: bool = True
    need_collection: bool = False
    need_automation: bool = False
    need_memory: bool = False

    # Tools required
    tools: List[str] = field(default_factory=list)

    # Extra information
    priority: str = "normal"
    requires_confirmation: bool = False

    # Future use
    confidence: float = 1.0
    notes: str = ""


# ==========================================================
# PLANNER
# ==========================================================

class Planner:
    """
    Analyze user requests.

    This class NEVER executes actions.
    It only decides what modules are required.
    """

    def __init__(self):

        self.automation_keywords = {
            "open",
            "launch",
            "start",
            "run",
            "close",
            "click",
            "press",
            "type",
            "move",
            "drag",
            "scroll",
            "create",
            "delete",
            "remove",
            "copy",
            "rename",
            "download",
            "upload",
            "install",
            "uninstall",
            "shutdown",
            "restart",
            "play",
            "pause",
            "stop"
        }

        self.information_keywords = {
            "latest",
            "today",
            "current",
            "news",
            "search",
            "find",
            "look up",
            "lookup",
            "version",
            "weather",
            "price"
        }

        self.memory_keywords = {
            "remember",
            "forget",
            "save",
            "recall"
        }

    # ------------------------------------------------------

    def analyze(self, user_input: str) -> Plan:
        """
        Analyze the user's request.

        Parameters
        ----------
        user_input : str

        Returns
        -------
        Plan
        """

        message = user_input.lower().strip()

        plan = Plan()

        # --------------------------------------------------
        # MEMORY
        # --------------------------------------------------

        if any(word in message for word in self.memory_keywords):

            plan.intent = "memory"
            plan.need_memory = True

        # --------------------------------------------------
        # INFORMATION
        # --------------------------------------------------

        if any(word in message for word in self.information_keywords):

            plan.intent = "information"
            plan.need_collection = True
            plan.need_model = True

        # --------------------------------------------------
        # AUTOMATION
        # --------------------------------------------------

        if any(word in message for word in self.automation_keywords):

            plan.intent = "automation"
            plan.need_automation = True

        # --------------------------------------------------
        # TOOL SELECTION
        # --------------------------------------------------

        browser_words = {
            "browser",
            "chrome",
            "firefox",
            "edge",
            "website",
            "youtube",
            "google"
        }

        filesystem_words = {
            "file",
            "folder",
            "directory"
        }

        media_words = {
            "music",
            "song",
            "video",
            "spotify",
            "vlc"
        }

        system_words = {
            "shutdown",
            "restart",
            "computer",
            "pc"
        }

        web_words = {
            "search",
            "latest",
            "news",
            "weather",
            "internet",
            "online"
        }

        if any(word in message for word in browser_words):
            plan.tools.append("browser")

        if any(word in message for word in filesystem_words):
            plan.tools.append("filesystem")

        if any(word in message for word in media_words):
            plan.tools.append("media")

        if any(word in message for word in system_words):
            plan.tools.append("system")

        if any(word in message for word in web_words):
            plan.tools.append("web")

        # Remove duplicate tools
        plan.tools = list(dict.fromkeys(plan.tools))

        # --------------------------------------------------
        # HIGH RISK ACTIONS
        # --------------------------------------------------

        dangerous_words = {
            "shutdown",
            "restart",
            "delete",
            "remove",
            "format",
            "erase"
        }

        if any(word in message for word in dangerous_words):

            plan.priority = "high"
            plan.requires_confirmation = True

        # --------------------------------------------------
        # NOTES
        # --------------------------------------------------

        plan.notes = (
            f"Intent '{plan.intent}' detected. "
            f"Required tools: {', '.join(plan.tools) if plan.tools else 'None'}."
        )

        return plan

    # ------------------------------------------------------

    def explain(self, plan: Plan) -> str:
        """
        Return a human-readable explanation of a plan.
        Useful for debugging.
        """

        return (
            f"Intent: {plan.intent}\n"
            f"Need Model: {plan.need_model}\n"
            f"Need Collection: {plan.need_collection}\n"
            f"Need Automation: {plan.need_automation}\n"
            f"Need Memory: {plan.need_memory}\n"
            f"Tools: {', '.join(plan.tools) if plan.tools else 'None'}\n"
            f"Priority: {plan.priority}\n"
            f"Confirmation Required: {plan.requires_confirmation}\n"
            f"Confidence: {plan.confidence:.2f}"
        )


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    planner = Planner()

    while True:

        user = input("You: ")

        if user.lower() == "exit":
            break

        plan = planner.analyze(user)

        print()
        print(planner.explain(plan))
        print("-" * 50)