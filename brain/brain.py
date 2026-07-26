"""
brain.py
--------

Main AI controller for the WEBS application.

Orchestrates planning, memory, model, tools, events, state, and face.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from brain.memory import Memory
from brain.memory_sqlite import SQLiteMemory
from brain.providers.model_manager import ModelManager
from brain.prompt_manager import PromptManager
from brain.session import SessionManager
from brain.cache import Cache
from brain.tools import ToolRegistry, ToolCategory
from brain.event_bus import EventBus, Event, EventType
from brain.state import StateManager, SystemState
from brain.learner import UsageLearner
from brain.suggestions import suggest_followup
from brain.dispatcher import Dispatcher, TaskStatus
from brain.evolution import TemplateEvolver
from brain.routing import classify_message, is_casual, MessageType
from brain.actions import detect_actions, ActionType

logger = logging.getLogger(__name__)


class Brain:
    """Main Brain orchestrator for W.E.B.S."""

    def __init__(
        self,
        prompt_dir: Optional[str] = None,
        api_key: Optional[str] = None,
        offline_model: str = "llama3.2:3b",
        config: Optional[Dict[str, Any]] = None,
        enable_face: bool = False,
    ) -> None:
        """Initialize the Brain with all components."""
        self.config = config or {}
        self.prompt_dir = Path(
            prompt_dir or Path(__file__).resolve().parent / "prompts"
        )
        self.name = "WEBS Brain"

        # Initialize event bus first
        self.event_bus = EventBus()

        # Initialize state
        self.state = StateManager(self.event_bus)
        self.state.set_state(SystemState.INITIALIZING, "Brain starting")

        # Initialize components
        self.memory = Memory()
        self.memory_db = SQLiteMemory()
        self.cache = Cache(
            max_size=self.config.get("cache_size", 500),
            ttl_seconds=self.config.get("cache_ttl", 3600),
        )
        self.model_manager = ModelManager(
            api_key=api_key, offline_model=offline_model
        )
        self.model = self.model_manager
        self.prompt_manager = PromptManager(str(self.prompt_dir))
        self.session_manager = SessionManager()
        self.tools = ToolRegistry()

        # JARVIS-inspired modules
        self.learner = UsageLearner()
        self.dispatcher = Dispatcher()
        self.evolver = TemplateEvolver()

        # Initialize face (optional)
        self.face = None
        self._face_enabled = enable_face
        if enable_face:
            self._init_face()

        # Initialize planner (lazy import to avoid circular issues)
        from brain.planner import Planner
        self.planner = Planner()

        # Voice components (lazy init)
        self._voice_engine = None
        self._stt = None

        # Context for compound commands (research → save → open)
        self._last_research: str = ""
        self._last_file: str = ""

        # Register built-in tools
        self._register_tools()

        # Register automation tools
        try:
            from brain.automation_integration import register_automation_tools
            register_automation_tools(self)
        except Exception as e:
            logger.warning(f"Automation tools not registered: {e}")

        # Register event handlers
        self._register_event_handlers()

        # State
        self.state.set_state(SystemState.IDLE, "Brain ready")

        logger.info("Brain fully initialized")

    def _init_face(self) -> None:
        """Initialize the face system."""
        try:
            from face import FaceWindow
            self.face = FaceWindow()
            self.face.show()
            logger.info("Face system initialized")
        except Exception as e:
            logger.warning(f"Face system unavailable: {e}")
            self.face = None
            self._face_enabled = False

    def init_voice(self, wake_word: Optional[str] = None) -> None:
        """Initialize voice engine and STT. Call explicitly to enable voice."""
        try:
            from brain.voice import VoiceEngine, SpeechToText
            self._voice_engine = VoiceEngine()
            self._stt = SpeechToText(wake_word=wake_word)
            logger.info("Voice system initialized")
        except Exception as e:
            logger.warning(f"Voice system unavailable: {e}")

    def start_listening(self) -> None:
        """Start listening for voice commands."""
        if self._stt:
            self._stt.start_listening(self._handle_voice_command)

    def stop_listening(self) -> None:
        """Stop listening for voice commands."""
        if self._stt:
            self._stt.stop_listening()

    def _handle_voice_command(self, text: str) -> None:
        """Handle voice command from STT."""
        logger.info(f"Voice command: {text}")
        self.event_bus.publish(Event(
            type=EventType.VOICE_LISTENING,
            source="brain",
            data={"command": text}
        ))
        response = self.process(text)
        if response and self._voice_engine:
            self._voice_engine.speak_async(response)

    # ==========================================================
    # Tool Registration
    # ==========================================================

    def _register_tools(self) -> None:
        """Register all built-in tools."""

        @self.tools.register(
            "search", "Search the live web / news for current information", ToolCategory.SEARCH
        )
        def search(query: str) -> str:
            try:
                from automation.live_search import get_live_search
                return get_live_search().briefing(query, include_top=False)
            except Exception as e:
                result = self.collector.collect(query) if hasattr(self, 'collector') else None
                return result.content if result else f"Search failed: {e}"

        @self.tools.register(
            "fetch_url", "Fetch and read a webpage", ToolCategory.WEB
        )
        def fetch_url(url: str) -> str:
            result = self.collector.collect(url) if hasattr(self, 'collector') else None
            return result.content if result else "Could not fetch URL."

        @self.tools.register(
            "remember", "Store information in memory", ToolCategory.AI
        )
        def remember(content: str) -> str:
            self.memory.remember("user_note", content)
            return "I'll remember that."

        @self.tools.register(
            "recall", "Retrieve information from memory", ToolCategory.AI
        )
        def recall(query: str) -> str:
            result = self.memory.recall(query)
            if result:
                return str(result)
            return "I don't have that in my memory."

    # ==========================================================
    # Event Handlers
    # ==========================================================

    def _register_event_handlers(self) -> None:
        """Register event handlers."""
        self.event_bus.subscribe(
            EventType.PLANNER_TASK_START, self._on_task_start
        )
        self.event_bus.subscribe(
            EventType.PLANNER_TASK_COMPLETE, self._on_task_complete
        )
        self.event_bus.subscribe(
            EventType.COLLECTOR_SEARCHING, self._on_searching
        )

    def _on_task_start(self, event: Event) -> None:
        self.state.set_state(
            SystemState.THINKING,
            f"Task: {event.data.get('task', 'unknown')}",
        )

    def _on_task_complete(self, event: Event) -> None:
        self.state.set_state(SystemState.IDLE, "Task complete")

    def _on_searching(self, event: Event) -> None:
        self.state.set_state(SystemState.SEARCHING, event.data.get("query", ""))

    # ==========================================================
    # Core Processing
    # ==========================================================

    def process(self, user_input: str, session_id: Optional[str] = None) -> str:
        """
        Process user input and return response.
        """
        if not user_input or not user_input.strip():
            return "Please say something."

        start_time = time.time()

        # Get or create session
        session = self.session_manager.get_or_create_session(session_id)
        self.state.set_state(SystemState.THINKING, "Processing input")

        # Face: show listening/thinking expression
        if self.face:
            self.face.set_emotion(user_input, "user")

        # Store user message
        self.memory.add_message(role="user", content=user_input)
        session.add_message("user", user_input)

        # Detect actions
        actions = detect_actions(user_input)

        # Publish event
        self.event_bus.publish(
            Event(
                type=EventType.BRAIN_THINKING,
                source="brain",
                data={"user_input": user_input},
            )
        )

        try:
            # Face: thinking expression
            if self.face:
                self.face.set_thinking()

            # Execute detected actions (supports compound chains)
            action_results = []
            for action in actions:
                result = self._execute_action(action)
                if result:
                    action_results.append(result)

            # Build messages with context injection
            history = self.memory.get_history()[-3:]
            system_prompt = self.load_prompts()

            # Always inject live clock + current news/web when needed
            # so the online brain is never stuck on a 2023 cutoff
            try:
                from automation.live_search import build_live_context, needs_live_context

                force_live = needs_live_context(user_input) or any(
                    getattr(a, "type", None)
                    and a.type.value in ("research", "search", "open_news", "web_task")
                    for a in actions
                )
                live_ctx = build_live_context(user_input, force=force_live)
                if live_ctx:
                    system_prompt += f"\n\n{live_ctx}"
            except Exception as e:
                logger.warning(f"Live context unavailable: {e}")

            # Inject dispatcher context if there are active tasks
            dispatch_ctx = self.dispatcher.format_for_prompt()
            if dispatch_ctx and "No active tasks" not in dispatch_ctx:
                system_prompt += f"\n\n{dispatch_ctx}"

            # Inject SQLite memory context
            memory_ctx = self.memory_db.build_context()
            if memory_ctx:
                system_prompt += f"\n\n{memory_ctx}"

            # Inject action results
            if action_results:
                system_prompt += f"\n\nAction results: {'; '.join(action_results)}\nIMPORTANT: The action has already been executed. Use the exact URL shown in the action result in your response."

            messages = [{"role": "system", "content": system_prompt}]
            for item in history:
                messages.append({"role": item["role"], "content": item["content"]})
            messages.append({"role": "user", "content": user_input})

            # Generate response
            reply = self.model_manager.generate(messages)

            # Store in memory
            self.memory.add_message(role="assistant", content=reply)
            session.add_message("assistant", reply)

            # Log task for learner
            msg_type = classify_message(user_input)
            self.learner.log_task(
                task_type=msg_type.value,
                description=user_input[:200],
                success=True,
            )

            # Auto-speak response if voice is active
            if self._voice_engine:
                self._voice_engine.speak_async(reply)

            # Face: speak the response with emotion
            if self.face:
                self.face.speak(reply, emotion=True)

            # Publish event
            self.event_bus.publish(
                Event(
                    type=EventType.BRAIN_RESPONDING,
                    source="brain",
                    data={
                        "response": reply,
                        "time": time.time() - start_time,
                    },
                )
            )

            self.state.set_state(SystemState.IDLE, "Response ready")

            return reply

        except Exception as e:
            error_msg = f"I encountered an error: {str(e)}"
            logger.error(error_msg)

            # Log failure for evolution
            self.evolver.log_failure("chat", user_input[:200], str(e))

            # Face: show error expression
            if self.face:
                self.face.set_emotion("I'm sorry, something went wrong", "assistant")

            self.event_bus.publish(
                Event(
                    type=EventType.BRAIN_ERROR,
                    source="brain",
                    data={"error": str(e)},
                )
            )

            self.state.set_state(SystemState.ERROR, str(e))
            return error_msg

    def _execute_action(self, action) -> str:
        """Execute a detected action. Returns result string."""
        try:
            if action.type == ActionType.REMEMBER:
                self.memory_db.remember(action.target, importance=3)
                return f"Remembered: {action.target}"

            elif action.type == ActionType.ADD_TASK:
                self.memory_db.create_task(title=action.target)
                return f"Task created: {action.target}"

            elif action.type == ActionType.CREATE_NOTE:
                self.memory_db.create_note("user_note", action.target)
                return f"Note saved: {action.target}"

            elif action.type == ActionType.OPEN_APP:
                target = action.target
                # spotify:query → open Spotify (optionally with search URI)
                if target.lower().startswith("spotify:"):
                    query = target.split(":", 1)[1].strip()
                    if self.tools.get_tool("open_app"):
                        self.tools.execute("open_app", target="spotify")
                    if query and query.lower() not in ("song", "music", "track"):
                        import subprocess
                        import urllib.parse
                        uri = f"spotify:search:{urllib.parse.quote(query)}"
                        try:
                            subprocess.Popen(
                                ["xdg-open", uri],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            return f"Opened Spotify and searched for: {query}"
                        except Exception:
                            pass
                    return "Opened Spotify"
                if self.tools.get_tool("open_app"):
                    return self.tools.execute("open_app", target=target)
                return f"Would open: {target}"

            elif action.type == ActionType.CLOSE_APP:
                if self.tools.get_tool("close_app"):
                    return self.tools.execute("close_app", target=action.target)
                return f"Would close: {action.target}"

            elif action.type == ActionType.RUN_COMMAND:
                if self.tools.get_tool("terminal_run"):
                    return self.tools.execute("terminal_run", command=action.target)
                return f"Would run: {action.target}"

            elif action.type == ActionType.READ_FILE:
                if self.tools.get_tool("read_file"):
                    return self.tools.execute("read_file", path=action.target)
                return f"Would read: {action.target}"

            elif action.type == ActionType.CREATE_FILE:
                # Parse "test.txt with content hello world"
                target = action.target
                content = ""
                if " with content " in target:
                    parts = target.split(" with content ", 1)
                    target = parts[0].strip()
                    content = parts[1].strip()
                elif " with " in target:
                    parts = target.split(" with ", 1)
                    target = parts[0].strip()
                    content = parts[1].strip()
                # Compound: "put it in a file" after research → reuse research text
                if not content and self._last_research:
                    content = self._last_research
                if self.tools.get_tool("create_file"):
                    result = self.tools.execute("create_file", path=target, content=content)
                    self._last_file = target
                    return result
                self._last_file = target
                return f"Would create file: {target}"

            elif action.type == ActionType.DELETE_FILE:
                if self.tools.get_tool("delete_file"):
                    return self.tools.execute("delete_file", path=action.target)
                return f"Would delete: {action.target}"

            elif action.type == ActionType.COPY_FILE:
                target = action.target
                source, dest = "", ""
                if " to " in target:
                    parts = target.split(" to ", 1)
                elif " into " in target:
                    parts = target.split(" into ", 1)
                elif " onto " in target:
                    parts = target.split(" onto ", 1)
                else:
                    return f"Copy needs a destination. Usage: copy <source> to <destination>"
                source = parts[0].strip()
                dest = parts[1].strip()
                if self.tools.get_tool("copy_file"):
                    return self.tools.execute("copy_file", source=source, destination=dest)
                return f"Would copy {source} to {dest}"

            elif action.type == ActionType.MOVE_FILE:
                target = action.target
                source, dest = "", ""
                if " to " in target:
                    parts = target.split(" to ", 1)
                elif " into " in target:
                    parts = target.split(" into ", 1)
                elif " onto " in target:
                    parts = target.split(" onto ", 1)
                else:
                    return f"Move needs a destination. Usage: move <source> to <destination>"
                source = parts[0].strip()
                dest = parts[1].strip()
                if self.tools.get_tool("move_file"):
                    return self.tools.execute("move_file", source=source, destination=dest)
                return f"Would move {source} to {dest}"

            elif action.type == ActionType.RENAME_FILE:
                target = action.target
                source, new_name = "", ""
                if " to " in target:
                    parts = target.split(" to ", 1)
                elif " as " in target:
                    parts = target.split(" as ", 1)
                else:
                    return f"Rename needs a new name. Usage: rename <file> to <new_name>"
                source = parts[0].strip()
                new_name = parts[1].strip()
                # If dest has a path, just use the filename
                if "/" in new_name:
                    new_name = new_name.rsplit("/", 1)[-1]
                if self.tools.get_tool("rename_file"):
                    return self.tools.execute("rename_file", path=source, new_name=new_name)
                return f"Would rename {source} to {new_name}"

            elif action.type == ActionType.CREATE_DIR:
                if self.tools.get_tool("create_dir"):
                    return self.tools.execute("create_dir", path=action.target)
                return f"Would create directory: {action.target}"

            elif action.type == ActionType.DELETE_DIR:
                if self.tools.get_tool("delete_dir"):
                    return self.tools.execute("delete_dir", path=action.target)
                return f"Would delete directory: {action.target}"

            elif action.type == ActionType.GET_FILE_INFO:
                if self.tools.get_tool("get_file_info"):
                    return self.tools.execute("get_file_info", path=action.target)
                return f"Would get info for: {action.target}"

            elif action.type == ActionType.COMPRESS:
                target = action.target
                source = target
                dest = ""
                if " to " in target:
                    parts = target.split(" to ", 1)
                    source = parts[0].strip()
                    dest = parts[1].strip()
                elif " into " in target:
                    parts = target.split(" into ", 1)
                    source = parts[0].strip()
                    dest = parts[1].strip()
                else:
                    dest = source + ".zip"
                if self.tools.get_tool("compress"):
                    return self.tools.execute("compress", source=source, destination=dest)
                return f"Would compress {source} to {dest}"

            elif action.type == ActionType.EXTRACT:
                target = action.target
                source = target
                dest = ""
                if " to " in target:
                    parts = target.split(" to ", 1)
                    source = parts[0].strip()
                    dest = parts[1].strip()
                elif " into " in target:
                    parts = target.split(" into ", 1)
                    source = parts[0].strip()
                    dest = parts[1].strip()
                else:
                    dest = source.rsplit(".", 1)[0] if "." in source else source + "_extracted"
                if self.tools.get_tool("extract"):
                    return self.tools.execute("extract", archive=source, destination=dest)
                return f"Would extract {source} to {dest}"

            elif action.type == ActionType.GENERATE_IMAGE:
                # Determine size from prompt
                raw = action.params.get("raw", "").lower()
                size = "square"
                if any(w in raw for w in ["landscape", "wide", "banner", "horizontal"]):
                    size = "landscape"
                elif any(w in raw for w in ["portrait", "tall", "vertical"]):
                    size = "portrait"
                if self.tools.get_tool("generate_image"):
                    return self.tools.execute("generate_image", prompt=action.target, size=size)
                return f"Would generate image: {action.target}"

            elif action.type == ActionType.OPEN_FILE:
                path = action.target
                if path in ("", "__LAST_FILE__"):
                    path = self._last_file
                if not path:
                    return "No file to open, sir. Please specify a path."
                if self.tools.get_tool("open_file"):
                    return self.tools.execute("open_file", path=path)
                return f"Would open file: {path}"

            elif action.type == ActionType.LIST_DIR:
                path = action.target or "."
                if path.startswith("~"):
                    from pathlib import Path as _P
                    path = str(_P(path).expanduser())
                if self.tools.get_tool("list_dir"):
                    listing = self.tools.execute("list_dir", path=path)
                    return f"Files in {path}:\n{listing}"
                return f"Would list directory: {path}"

            elif action.type == ActionType.RESEARCH:
                topic = action.target
                # Prefer live search briefing (always current), then browser agent
                report = ""
                try:
                    from automation.live_search import get_live_search

                    report = get_live_search().briefing(topic, include_top=True)
                except Exception as e:
                    logger.warning(f"Live research failed: {e}")

                if not report and self.tools.get_tool("do_web_task"):
                    report = self.tools.execute(
                        "do_web_task",
                        task=f"Research and summarize the latest information about: {topic}. Include key facts and sources.",
                    )
                if not report:
                    report = self.model_manager.generate([
                        {"role": "system", "content": "You are a research assistant. Produce a clear, structured report. Prefer current facts."},
                        {"role": "user", "content": f"Research and summarize: {topic}"},
                    ])
                self._last_research = str(report)
                return f"Research complete on '{topic}'.\n{report}"

            elif action.type == ActionType.WEB_TASK:
                if self.tools.get_tool("do_web_task"):
                    return self.tools.execute("do_web_task", task=action.target)
                return f"Browser agent unavailable. Would run web task: {action.target}"

            elif action.type == ActionType.OPEN_NEWS:
                raw = action.params.get("raw", "").lower()
                # Extract site from user input
                site = "google news"
                for name in ["bbc", "cnn", "reuters", "guardian", "al jazeera",
                             "nytimes", "techcrunch", "verge", "hacker news",
                             "ars technica", "fox news", "sky news"]:
                    if name in raw:
                        site = name
                        break
                # Check if it's a topic search
                if "about" in raw or "on " in raw:
                    topic = action.target
                    if self.tools.get_tool("search_news"):
                        return self.tools.execute("search_news", query=topic)
                if self.tools.get_tool("open_news"):
                    return self.tools.execute("open_news", site=site)
                return f"Would open news: {site}"

            elif action.type == ActionType.MOUSE:
                raw = action.params.get("raw", "").lower()
                # Parse mouse actions
                if "scroll" in raw or "wheel" in raw:
                    direction = "up" if "up" in raw else "down"
                    amount = 3 if direction == "up" else -3
                    if self.tools.get_tool("scroll_mouse"):
                        return self.tools.execute("scroll_mouse", amount=amount)
                elif "position" in raw or "where" in raw:
                    if self.tools.get_tool("get_cursor_pos"):
                        return self.tools.execute("get_cursor_pos")
                elif "right click" in raw:
                    x, y = int(action.target.split(",")[0]), int(action.target.split(",")[1])
                    if self.tools.get_tool("right_click"):
                        return self.tools.execute("right_click", x=x, y=y)
                elif "double" in raw:
                    x, y = int(action.target.split(",")[0]), int(action.target.split(",")[1])
                    if self.tools.get_tool("double_click"):
                        return self.tools.execute("double_click", x=x, y=y)
                elif "click" in raw:
                    x, y = int(action.target.split(",")[0]), int(action.target.split(",")[1])
                    if self.tools.get_tool("click_at"):
                        return self.tools.execute("click_at", x=x, y=y)
                else:
                    # Move cursor
                    parts = action.target.replace("x", ",").split(",")
                    x, y = int(parts[0]), int(parts[1])
                    if self.tools.get_tool("move_mouse"):
                        return self.tools.execute("move_mouse", x=x, y=y)

            elif action.type == ActionType.KEYBOARD:
                raw = action.params.get("raw", "").lower()
                # Check for hotkey (ctrl+c, alt+tab, etc)
                if "+" in raw or "ctrl" in raw or "alt" in raw or "shift" in raw:
                    import re
                    key_match = re.search(r'(ctrl|alt|shift|super)\s*\+?\s*(\w+)', raw)
                    if key_match:
                        combo = f"{key_match.group(1)}+{key_match.group(2)}"
                        if self.tools.get_tool("hotkey"):
                            return self.tools.execute("hotkey", keys=combo)
                # Check for single key press
                single_keys = ["enter", "tab", "escape", "space", "backspace", "delete",
                               "home", "end", "pageup", "pagedown", "up", "down", "left", "right"]
                for key in single_keys:
                    if key in raw:
                        if self.tools.get_tool("press_key"):
                            return self.tools.execute("press_key", key=key)
                # Otherwise type the text
                text = action.target
                if self.tools.get_tool("type_text"):
                    return self.tools.execute("type_text", text=text)
                return f"Would type: {text}"

            elif action.type == ActionType.BROWSE:
                import subprocess
                from urllib.parse import quote
                target = action.target
                # If it's already a URL, open it directly
                if target.startswith("http"):
                    url = target
                else:
                    raw = action.params.get("raw", "").lower()
                    # YouTube: use yt-dlp to find actual video URL
                    if "youtube" in raw:
                        try:
                            logger.info(f"yt-dlp searching: {target}")
                            result = subprocess.run(
                                ["yt-dlp", "--js-runtimes", "nodejs",
                                 f"ytsearch1:{target}", "--get-id", "--no-warnings"],
                                capture_output=True, text=True, timeout=20
                            )
                            logger.info(f"yt-dlp rc={result.returncode} stdout_len={len(result.stdout)}")
                            video_id = result.stdout.strip().split("\n")[0] if result.stdout.strip() else ""
                            if video_id:
                                url = f"https://www.youtube.com/watch?v={video_id}"
                                logger.info(f"yt-dlp found video: {video_id}")
                            else:
                                logger.info(f"yt-dlp no ID, stderr: {result.stderr[:200]}")
                                url = f"https://www.youtube.com/results?search_query={quote(target)}"
                        except Exception as e:
                            logger.error(f"yt-dlp failed: {e}")
                            url = f"https://www.youtube.com/results?search_query={quote(target)}"
                    elif any(s in raw for s in ["google", "bing", "duckduckgo"]):
                        url = f"https://www.google.com/search?q={quote(target)}"
                    elif "brave" in raw:
                        url = f"https://search.brave.com/search?q={quote(target)}"
                    else:
                        url = f"https://www.google.com/search?q={quote(target)}"
                # Open in default browser
                try:
                    subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return f"Opened: {url}"
                except Exception:
                    return f"Would open: {url}"

            elif action.type == ActionType.SEARCH:
                query = action.target
                try:
                    from automation.live_search import get_live_search

                    briefing = get_live_search().briefing(query, include_top=False)
                    self._last_research = briefing
                    return briefing
                except Exception:
                    pass
                if self.tools.get_tool("do_web_task"):
                    return self.tools.execute(
                        "do_web_task",
                        task=f"Search the web for: {query} and summarize the top results",
                    )
                import subprocess
                from urllib.parse import quote
                url = f"https://www.google.com/search?q={quote(query)}"
                try:
                    subprocess.Popen(
                        ["xdg-open", url],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return f"Opened search: {url}"
                except Exception:
                    return f"Would search: {query}"

            elif action.type == ActionType.REMEMBER:
                content = action.target
                self.memory_db.remember(content, mem_type="fact", importance=2)
                return f"Remembered: {content}"

            else:
                return ""

        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return f"Action failed: {e}"

    def process_full(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input and return full structured result.

        Returns the full structured result dict (used by tests).
        """
        plan = self.planner.analyze(user_input)
        self.memory.add_message(role="user", content=user_input)

        context = self.build_context(user_input, plan)
        messages = self.build_messages(context)

        reply = self.model_manager.generate(messages)

        self.memory.add_message(role="assistant", content=reply)

        return {
            "reply": reply,
            "plan": plan,
            "success": True,
            "emotion": "thinking",
            "actions": [],
            "remember": [],
        }

    # ==========================================================
    # Context Building
    # ==========================================================

    def build_context(
        self, user_input: str, plan
    ) -> Dict[str, Any]:
        """Create a structured context object for downstream processing."""
        history = self.memory.get_history()[-5:]
        return {
            "system_prompt": self.load_prompts(),
            "history": history,
            "user_input": user_input,
            "plan": plan,
            "collected_data": {},
            "memory": self.memory,
        }

    def build_messages(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build OpenAI/Ollama-style message list from the context."""
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": context["system_prompt"]},
        ]

        for item in context["history"]:
            messages.append({"role": item["role"], "content": item["content"]})

        messages.append({"role": "user", "content": context["user_input"]})
        return messages

    def load_prompts(self) -> str:
        """Load all .txt prompt files automatically from the prompt directory."""
        prompts: List[str] = []

        for file in sorted(self.prompt_dir.glob("*.txt")):
            text = file.read_text(encoding="utf-8").strip()
            if text:
                prompts.append(text)

        base = "\n\n".join(prompts).strip()

        # Append available tool list so model knows its capabilities
        tool_names = self.tools.list_tool_names()
        if tool_names:
            tool_list = ", ".join(tool_names)
            base += f"\n\nAvailable tools: {tool_list}. Use them when needed."

        # Inject learner context (frequent tasks, recent projects)
        learner_ctx = self.learner.get_context_string()
        if learner_ctx:
            base += f"\n\n{learner_ctx}"

        # Inject evolution rules (lessons from past failures)
        evo_ctx = self.evolver.get_context_string()
        if evo_ctx:
            base += f"\n\n{evo_ctx}"

        return base

    # ==========================================================
    # Utility Methods
    # ==========================================================

    def get_available_models(self) -> List[str]:
        """Return names of all registered providers."""
        return self.model_manager.list_providers()

    def set_model_preference(self, preference: str) -> None:
        """Switch provider based on preference string."""
        pref_map = {
            "online": "groq",
            "offline": "ollama",
        }
        provider_name = pref_map.get(preference.lower())
        if provider_name:
            self.model_manager.switch_to(provider_name)

    def get_state(self) -> Dict[str, Any]:
        """Get current system state."""
        return {
            "state": self.state.get_state().value,
            "session_count": len(self.session_manager.list_sessions()),
            "memory_size": len(self.memory.get_history()),
            "cache_size": self.cache.get_stats().size,
            "available_models": self.model_manager.list_providers(),
            "face_enabled": self._face_enabled,
        }

    def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("Shutting down Brain...")
        if self.face:
            self.face.hide()
        self.event_bus.stop()
        self.cache.clear()
        logger.info("Brain shutdown complete")

    def reset(self) -> None:
        """Reset all state."""
        self.memory.clear_history()
        self.cache.clear()
        self.session_manager = SessionManager()
        self.state.reset()
        logger.info("Brain reset complete")
