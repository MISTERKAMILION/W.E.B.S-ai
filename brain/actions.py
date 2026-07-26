"""Action tag system - detects and parses action commands from user input.

Inspired by JARVIS action tags - allows the Brain to detect
intentions like building, browsing, researching, remembering.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ActionType(str, Enum):
    BUILD = "build"
    BROWSE = "browse"
    RESEARCH = "research"
    REMEMBER = "remember"
    REMIND = "remind"
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    OPEN_FILE = "open_file"
    OPEN_NEWS = "open_news"
    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    RUN_COMMAND = "run_command"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"
    COPY_FILE = "copy_file"
    MOVE_FILE = "move_file"
    RENAME_FILE = "rename_file"
    CREATE_DIR = "create_dir"
    DELETE_DIR = "delete_dir"
    GET_FILE_INFO = "get_file_info"
    COMPRESS = "compress"
    EXTRACT = "extract"
    GENERATE_IMAGE = "generate_image"
    LIST_DIR = "list_dir"
    SEARCH = "search"
    CREATE_NOTE = "create_note"
    ADD_TASK = "add_task"
    COMPLETE_TASK = "complete_task"
    SCREEN = "screen"
    WEB_TASK = "web_task"
    CHAT = "chat"


@dataclass
class DetectedAction:
    """An action detected from user input."""
    type: ActionType
    target: str = ""
    params: Dict = field(default_factory=dict)
    confidence: float = 1.0


# Known desktop apps (used for open/close matching)
_KNOWN_APPS = (
    "firefox|chrome|brave|code|vim|nano|terminal|spotify|"
    "discord|slack|vlc|gedit|nautilus|files|calculator|thunderbird"
)

# Action detection patterns (order matters - first match wins)
# More specific patterns FIRST. Duplicates removed.
ACTION_PATTERNS: List[Tuple[str, ActionType]] = [
    # Directory listing BEFORE read/show (fixes "show me files in Downloads")
    (r"(?:list|show|display)\s+(?:me\s+)?(?:the\s+)?(?:files|folders|contents|dirs|directories)\s+(?:on\s+(?:my\s+)?(?:pc|computer|desktop)|in\s+(?:my\s+)?(.+)|here)?", ActionType.LIST_DIR),
    (r"(?:list|ls|dir)\s+(?:the\s+)?(?:files\s+)?(?:in\s+|of\s+)?(.+)", ActionType.LIST_DIR),
    (r"(?:what|which)\s+files\s+(?:are\s+)?(?:on\s+(?:my\s+)?(?:pc|computer)|in\s+(?:my\s+)?(.+)|here)?", ActionType.LIST_DIR),
    (r"(?:show|list)\s+(?:me\s+)?(?:my\s+)?(?:pc|computer)\s+files", ActionType.LIST_DIR),

    # Directory create/delete
    (r"(?:mkdir|create\s+(?:a\s+)?(?:directory|folder|dir))\s+(.+)", ActionType.CREATE_DIR),
    (r"(?:rmdir|delete\s+(?:the\s+)?(?:directory|folder|dir))\s+(.+)", ActionType.DELETE_DIR),

    # News (before general read/show)
    (r"(?:open|show|get|fetch|read)\s+(?:me\s+)?(?:the\s+)?(?:latest\s+)?news\s+(?:from|on|about)\s+(.+)", ActionType.OPEN_NEWS),
    (r"(?:open|show|get|fetch|read)\s+(?:me\s+)?(?:the\s+)?(?:latest\s+)?news\b", ActionType.OPEN_NEWS),
    (r"(?:what(?:'s| is)\s+(?:happening|going on|in the news|new))", ActionType.OPEN_NEWS),

    # Spotify / music apps BEFORE generic browse
    (r"(?:open|launch|start|play)\s+(?:a\s+)?(?:song|music|track|playlist)?\s*(?:on\s+)?(spotify)\b", ActionType.OPEN_APP),
    (r"(?:play|open)\s+(.+?)\s+on\s+(spotify)\b", ActionType.OPEN_APP),
    (r"(?:open|launch|start)\s+(" + _KNOWN_APPS + r")\b", ActionType.OPEN_APP),
    (r"(?:close|kill|quit|stop)\s+(" + _KNOWN_APPS + r")\b", ActionType.CLOSE_APP),

    # Mouse
    (r"(?:move|go)\s+(?:the\s+)?(?:cursor|mouse)\s+(?:to\s+)?(\d+)\s*[,x]\s*(\d+)", ActionType.MOUSE),
    (r"(?:click|left click)\s+(?:at\s+)?(\d+)\s*[,x]\s*(\d+)", ActionType.MOUSE),
    (r"(?:double\s*click)\s+(?:at\s+)?(\d+)\s*[,x]\s*(\d+)", ActionType.MOUSE),
    (r"(?:right\s*click)\s+(?:at\s+)?(\d+)\s*[,x]\s*(\d+)", ActionType.MOUSE),
    (r"(?:scroll|wheel)\s+(up|down)", ActionType.MOUSE),
    (r"(?:where|position)\s+(?:is\s+)?(?:the\s+)?(?:cursor|mouse)", ActionType.MOUSE),

    # Keyboard
    (r"(?:press|hit)\s+(ctrl|alt|shift|super)\s*\+?\s*(\w+)", ActionType.KEYBOARD),
    (r"(?:press|hit)\s+(enter|tab|escape|space|backspace|delete|home|end|pageup|pagedown|up|down|left|right|f\d+)\b", ActionType.KEYBOARD),
    (r"(?:type|write)\s+(?:on\s+(?:the\s+)?(?:keyboard|screen)\s+)?(.+)", ActionType.KEYBOARD),

    # File create / save research into file
    (r"(?:put|save|write|store)\s+(?:it|that|this|the\s+(?:report|research|results?|info|content))?\s*(?:in|into|to)\s+(?:a\s+)?(?:file\s+)?(?:called\s+|named\s+)?(\S+)", ActionType.CREATE_FILE),
    (r"(?:create|make|write|save)\s+(?:a\s+)?(?:file|txt|report)\s+(?:called\s+|named\s+)?(\S+?)(?:\s+with\s+(?:content\s+)?(.+))?$", ActionType.CREATE_FILE),
    (r"(?:delete|remove|rm)\s+(?:the\s+)?(?:file\s+)?(\S+)", ActionType.DELETE_FILE),

    # LIST_DIR already above; READ_FILE after list so "show files" wins
    (r"(?:read|show|display|cat)\s+(?:the\s+)?(?:file\s+|contents?\s+of\s+)?(\S+\.\w{1,5})\b", ActionType.READ_FILE),
    (r"(?:read|cat)\s+(?:the\s+)?(?:file\s+)?(\S+)", ActionType.READ_FILE),

    # Copy / move / rename
    (r"(?:copy|cp)\s+(.+?)\s+(?:to|into|onto)\s+(.+)", ActionType.COPY_FILE),
    (r"(?:move|mv)\s+(.+?)\s+(?:to|into|onto)\s+(.+)", ActionType.MOVE_FILE),
    (r"(?:rename)\s+(.+?)\s+(?:to|as)\s+(.+)", ActionType.RENAME_FILE),

    # File info (avoid bare "info" matching mid-sentence topics like "snakes info")
    (r"(?:file\s+info|details)\s+(?:of\s+|for\s+)?(.+)", ActionType.GET_FILE_INFO),
    (r"(?:^|\b)info\s+(?:of|for|about)\s+(.+)", ActionType.GET_FILE_INFO),
    (r"^info\s+(\S.+)$", ActionType.GET_FILE_INFO),

    # Extract / compress
    (r"(?:unzip|extract)\s+(.+?)(?:\s+(?:to|into)\s+(.+))?$", ActionType.EXTRACT),
    (r"(?:zip|compress|archive)\s+(.+?)\s+(?:to|into)\s+(.+)", ActionType.COMPRESS),
    (r"(?:zip|compress|archive)\s+(.+)", ActionType.COMPRESS),

    # Open file by extension (after open app)
    (r"(?:open|launch)\s+(?:the\s+)?(?:file\s+)?(.+\.\w{1,5})\b", ActionType.OPEN_FILE),
    (r"(?:open)\s+(?:it|that|the\s+file)\b", ActionType.OPEN_FILE),

    # Research BEFORE browse/search (compound research commands)
    (r"(?:do\s+(?:a\s+)?(?:full\s+)?)?(?:research|investigate|look into|find out about)\s+(?:on\s+)?(.+)", ActionType.RESEARCH),

    # Browser agent web tasks
    (r"(?:browse|use\s+(?:the\s+)?browser|web\s+task|automate)\s+(?:and\s+)?(.+)", ActionType.WEB_TASK),

    # Browse / search
    (r"(?:open|go to|browse|navigate to|visit)\s+(https?://\S+)", ActionType.BROWSE),
    (r"(?:open|go to|browse|play)\s+(.+?)\s+(?:on|in|using)\s+(youtube|brave|chrome|firefox|browser|google|bing|duckduckgo)\b", ActionType.BROWSE),
    (r"(?:search|google|look up|find)\s+(?:for\s+|about\s+|on\s+)?(.+)", ActionType.SEARCH),
    (r"(?:open|go to|play)\s+(.+)", ActionType.BROWSE),

    # Remember / remind
    (r"(?:remember|save|note|store)\s+(?:that\s+)?(.+)", ActionType.REMEMBER),
    (r"(?:i\s+(?:prefer|like|want|need|hate|love))\s+(.+)", ActionType.REMEMBER),
    (r"(?:remind me to|remind me that)\s+(.+)", ActionType.REMIND),

    # Run command
    (r"(?:run|execute)\s+(?:the\s+)?(?:command\s+)?(.+)", ActionType.RUN_COMMAND),

    # Notes / tasks
    (r"(?:take a note|note down|add note|create note)\s*:?\s*(.+)", ActionType.CREATE_NOTE),
    (r"(?:add task|create task|todo|to-do)\s*:?\s*(.+)", ActionType.ADD_TASK),
    (r"(?:complete|done|finish|mark done)\s+(.+)", ActionType.COMPLETE_TASK),

    # Screen
    (r"(?:what(?:'s| is) on (?:my )?screen|look at (?:my )?screen|what do you see)", ActionType.SCREEN),

    # Image generation
    (r"(?:generate|create|make|draw|design|produce|sketch|paint)\s+(?:an?\s+)?(?:image|picture|photo|drawing|art|illustration|logo)\s+(?:of\s+|of\s+a\s+|of\s+an?\s+)?(.+)", ActionType.GENERATE_IMAGE),
    (r"(?:generate|create|make|draw|design|produce|sketch|paint)\s+(.+?)\s+(?:image|picture|photo|drawing|art|illustration|logo)", ActionType.GENERATE_IMAGE),
    (r"(?:draw|sketch|paint)\s+(.+)", ActionType.GENERATE_IMAGE),

    # Build (generic - last resort)
    (r"(?:build|develop)\s+(.+)", ActionType.BUILD),
]


_COMPOUND_SPLIT = re.compile(
    r"\s+(?:and then|then|and also|and)\s+",
    re.IGNORECASE,
)


def _build_action(match: re.Match, action_type: ActionType, raw: str) -> DetectedAction:
    """Build a DetectedAction from a regex match."""
    target = match.group(1).strip() if match.lastindex and match.group(1) else ""

    # Spotify "play X on spotify" — group 2 is the app name
    if action_type == ActionType.OPEN_APP and match.lastindex and match.lastindex >= 2 and match.group(2):
        app = match.group(2).strip()
        query = match.group(1).strip()
        # If group1 is the app itself (e.g. just "spotify"), use that
        if query.lower() in ("spotify", "song", "music", "track", "playlist", ""):
            target = app
        elif app.lower() == "spotify":
            target = f"spotify:{query}"
        else:
            target = app

    if action_type == ActionType.CREATE_FILE and match.lastindex and match.lastindex >= 2 and match.group(2):
        content = match.group(2).strip()
        if content:
            target = f"{target} with content {content}"

    if action_type in (
        ActionType.COPY_FILE,
        ActionType.MOVE_FILE,
        ActionType.RENAME_FILE,
        ActionType.COMPRESS,
        ActionType.EXTRACT,
    ):
        if match.lastindex and match.lastindex >= 2 and match.group(2):
            dest = match.group(2).strip()
            target = f"{target} to {dest}"

    # LIST_DIR with no/common path → expand shortcuts
    if action_type == ActionType.LIST_DIR:
        raw_l = raw.lower()
        t = target.lower().strip() if target else ""
        shortcuts = {
            "downloads": "~/Downloads",
            "download": "~/Downloads",
            "desktop": "~/Desktop",
            "documents": "~/Documents",
            "docs": "~/Documents",
            "home": "~",
            "pc": "~",
            "computer": "~",
            ".": ".",
        }
        if not t:
            if "desktop" in raw_l:
                target = "~/Desktop"
            elif "download" in raw_l:
                target = "~/Downloads"
            elif "document" in raw_l:
                target = "~/Documents"
            elif "pc" in raw_l or "computer" in raw_l or "home" in raw_l:
                target = "~"
            else:
                target = "."
        elif t in shortcuts:
            target = shortcuts[t]
        elif t.startswith("my "):
            key = t[3:].strip()
            target = shortcuts.get(key, target)

    # OPEN_FILE "open it" — empty target means "last file"
    if action_type == ActionType.OPEN_FILE and not target:
        target = "__LAST_FILE__"

    target = target.strip("\"'")
    return DetectedAction(
        type=action_type,
        target=target,
        params={"raw": raw},
    )


def _detect_single(text: str) -> Optional[DetectedAction]:
    """Detect a single action from a text segment."""
    text = text.strip()
    if not text:
        return None

    for pattern, action_type in ACTION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _build_action(match, action_type, text)
    return None


def detect_actions(text: str) -> List[DetectedAction]:
    """Detect actions from user input text.

    Supports compound commands split on 'and' / 'then', e.g.:
    'research snakes and put it in a file called report.txt and open it'
    """
    text_lower = text.lower().strip()
    if not text_lower:
        return []

    # Try compound segments first
    segments = _COMPOUND_SPLIT.split(text_lower)
    if len(segments) > 1:
        actions: List[DetectedAction] = []
        for segment in segments:
            action = _detect_single(segment.strip())
            if action:
                # Keep original full text in params for context
                action.params["raw"] = text
                action.params["segment"] = segment.strip()
                actions.append(action)
        if actions:
            return actions

    action = _detect_single(text_lower)
    if action:
        action.params["raw"] = text
        return [action]
    return []


def format_action_tag(action: DetectedAction) -> str:
    """Format an action as a tag string for LLM context."""
    return f"[ACTION:{action.type.value.upper()}] {action.target}"


def is_action_request(text: str) -> bool:
    """Quick check if text contains an action request."""
    return len(detect_actions(text)) > 0
