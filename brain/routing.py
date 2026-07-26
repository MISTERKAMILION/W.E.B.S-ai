"""Message routing - classifies user messages as casual or work.

Inspired by JARVIS work_mode.py - routes messages to the right
model and processing pipeline based on intent.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional


class MessageType(str, Enum):
    CASUAL = "casual"
    WORK = "work"
    COMMAND = "command"
    QUESTION = "question"


# Patterns for different message types
CASUAL_PATTERNS = [
    r"^(hi|hello|hey|yo|sup|howdy|greetings)\b",
    r"^(good\s+(morning|afternoon|evening|night))\b",
    r"^(thanks|thank you|cheers|thx)\b",
    r"^(bye|goodbye|see ya|later|cya)\b",
    r"^(how are you|how's it going|what's up)\b",
    r"^(ok|okay|sure|yep|yeah|yup|nah|nope)\b",
    r"^(lol|haha|hehe|lmao|rofl)\b",
    r"^(nice|cool|awesome|great|sweet|perfect)\b",
    r"^(yes|no|maybe|sure|fine)\b",
]

WORK_PATTERNS = [
    r"\b(build|create|make|develop|code|program|implement|write)\b",
    r"\b(fix|debug|repair|solve|troubleshoot|patch)\b",
    r"\b(deploy|ship|release|push|commit|merge)\b",
    r"\b(test|verify|validate|check|review)\b",
    r"\b(refactor|optimize|improve|upgrade|migrate)\b",
    r"\b(install|setup|configure|install|uninstall)\b",
    r"\b(run|execute|start|stop|restart|kill)\b",
    r"\b(read|write|edit|modify|update|delete|create)\s+(file|code|script)",
    r"\b(search|find|grep|look up|research)\b",
    r"\b(python|javascript|typescript|rust|go|java|c\+\+)\b",
    r"\b(git|docker|npm|pip|cargo|brew)\b",
    r"\b(server|database|api|endpoint|route|function|class)\b",
]

COMMAND_PATTERNS = [
    r"^(open|launch|start|run)\s+\w+",
    r"^(close|kill|stop|quit)\s+\w+",
    r"^(list|show|display|print)\s+",
    r"^(set|change|modify|update)\s+",
    r"^(send|email|message)\s+",
]


def classify_message(text: str) -> MessageType:
    """Classify a user message into a type."""
    text = text.strip()
    if not text:
        return MessageType.CASUAL

    text_lower = text.lower()

    # Check casual patterns first
    for pattern in CASUAL_PATTERNS:
        if re.match(pattern, text_lower):
            return MessageType.CASUAL

    # Check command patterns
    for pattern in COMMAND_PATTERNS:
        if re.match(pattern, text_lower):
            return MessageType.COMMAND

    # Check work patterns
    for pattern in WORK_PATTERNS:
        if re.search(pattern, text_lower):
            return MessageType.WORK

    # Default to question for anything with a question mark
    if "?" in text:
        return MessageType.QUESTION

    return MessageType.WORK


def is_casual(text: str) -> bool:
    """Quick check if message is casual (for model routing)."""
    return classify_message(text) == MessageType.CASUAL


def is_work(text: str) -> bool:
    """Quick check if message requires work execution."""
    return classify_message(text) in (MessageType.WORK, MessageType.COMMAND)


def should_use_fast_model(text: str) -> bool:
    """Determine if we can use the faster/cheaper model."""
    msg_type = classify_message(text)
    return msg_type in (MessageType.CASUAL, MessageType.QUESTION)
