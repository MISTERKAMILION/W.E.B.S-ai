"""Automation integration for Brain.

Registers automation capabilities as Brain tools so the AI can
execute tasks on the system.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from brain.brain import Brain

logger = logging.getLogger(__name__)


def register_automation_tools(brain: Brain) -> None:
    """Register all automation capabilities as Brain tools."""

    try:
        from automation.terminal import TerminalAutomation
        from automation.applications import ApplicationAutomation
        from automation.filesystem import FilesystemAutomation
        from automation.network import NetworkAutomation
    except ImportError as e:
        logger.warning(f"Automation modules not available: {e}")
        return

    terminal = TerminalAutomation()
    apps = ApplicationAutomation()
    filesystem = FilesystemAutomation()
    network = NetworkAutomation()

    # --- Terminal ---

    @brain.tools.register("terminal_run", "Execute a shell command and return output")
    def terminal_run(command: str) -> str:
        try:
            return terminal.run(command, timeout=30)
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("terminal_background", "Run a command in the background")
    def terminal_background(command: str) -> str:
        try:
            pid = terminal.run_background(command)
            return f"Started background process: {pid}"
        except Exception as e:
            return f"Error: {e}"

    # --- Applications ---

    @brain.tools.register("open_app", "Open an application by name")
    def open_app(target: str) -> str:
        try:
            apps.open(target)
            return f"Opened {target}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("close_app", "Close an application by name")
    def close_app(target: str) -> str:
        try:
            apps.close(target)
            return f"Closed {target}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("is_app_running", "Check if an application is running")
    def is_app_running(target: str) -> str:
        running = apps.is_running(target)
        return f"{target} is {'running' if running else 'not running'}"

    # --- Filesystem ---

    @brain.tools.register("read_file", "Read a file's contents")
    def read_file(path: str) -> str:
        try:
            return filesystem.read(path)
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("write_file", "Write content to a file (overwrites)")
    def write_file(path: str, content: str) -> str:
        try:
            filesystem.write(path, content)
            return f"Written to {path}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("append_file", "Append content to a file")
    def append_file(path: str, content: str) -> str:
        try:
            filesystem.write(path, content, append=True)
            return f"Appended to {path}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("list_dir", "List files and folders in a directory")
    def list_dir(path: str = ".") -> str:
        try:
            items = filesystem.list_files(path)
            return "\n".join(items) if items else "Empty directory"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("file_exists", "Check if a file or directory exists")
    def file_exists(path: str) -> str:
        exists = filesystem.exists(path)
        return f"{path} {'exists' if exists else 'does not exist'}"

    @brain.tools.register("get_file_info", "Get file/directory details (type, size)")
    def get_file_info(path: str) -> str:
        try:
            import os
            if not os.path.exists(path):
                return f"{path} does not exist"
            st = os.stat(path)
            is_dir = os.path.isdir(path)
            size = st.st_size
            kind = "directory" if is_dir else "file"
            # Human readable size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    break
                size /= 1024
            return f"{path}: {kind}, {size:.1f}{unit}, modified {st.st_mtime:.0f}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("create_file", "Create a new file with optional content")
    def create_file(path: str, content: str = "") -> str:
        try:
            filesystem.create_file(path, content)
            return f"Created {path}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("delete_file", "Delete a file")
    def delete_file(path: str) -> str:
        try:
            filesystem.delete_file(path)
            return f"Deleted {path}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("copy_file", "Copy a file or directory to a new location")
    def copy_file(source: str, destination: str) -> str:
        try:
            filesystem.copy(source, destination)
            return f"Copied {source} to {destination}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("move_file", "Move or rename a file or directory")
    def move_file(source: str, destination: str) -> str:
        try:
            filesystem.move(source, destination)
            return f"Moved {source} to {destination}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("rename_file", "Rename a file or directory (same folder)")
    def rename_file(path: str, new_name: str) -> str:
        try:
            filesystem.rename(path, new_name)
            return f"Renamed to {new_name}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("create_dir", "Create a directory (and parent dirs)")
    def create_dir(path: str) -> str:
        try:
            filesystem.create_directory(path)
            return f"Created directory {path}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("delete_dir", "Delete a directory and all its contents")
    def delete_dir(path: str) -> str:
        try:
            filesystem.delete_directory(path, recursive=True)
            return f"Deleted directory {path}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("search_files", "Search for files matching a pattern")
    def search_files(directory: str, pattern: str) -> str:
        try:
            matches = filesystem.search(directory, pattern)
            return "\n".join(matches) if matches else "No matches found"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("compress", "Compress a file or directory into a zip/tar archive")
    def compress(source: str, destination: str) -> str:
        try:
            fmt = "tar" if destination.endswith((".tar.gz", ".tgz")) else "zip"
            filesystem.compress(source, destination, format=fmt)
            return f"Compressed {source} to {destination}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("extract", "Extract an archive (zip/tar.gz)")
    def extract(archive: str, destination: str) -> str:
        try:
            filesystem.extract(archive, destination)
            return f"Extracted {archive} to {destination}"
        except Exception as e:
            return f"Error: {e}"

    # --- Network ---

    @brain.tools.register("http_get", "Fetch a URL and return its content")
    def http_get(url: str) -> str:
        try:
            return network.get(url)
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("download_file", "Download a file from a URL")
    def download_file(url: str, destination: str) -> str:
        try:
            network.download(url, destination)
            return f"Downloaded to {destination}"
        except Exception as e:
            return f"Error: {e}"

    @brain.tools.register("check_internet", "Check if internet connection is available")
    def check_internet() -> str:
        online = network.check_connection()
        return f"Internet is {'connected' if online else 'disconnected'}"

    # --- Image Generation ---

    try:
        from automation.image_gen import ImageGenerator
        image_gen = ImageGenerator()

        @brain.tools.register("generate_image", "Generate an image from a text description")
        def generate_image(prompt: str, size: str = "square") -> str:
            try:
                if size == "landscape":
                    path = image_gen.generate_landscape(prompt)
                elif size == "portrait":
                    path = image_gen.generate_portrait(prompt)
                else:
                    path = image_gen.generate_square(prompt)
                if path:
                    return f"Generated image: {path}"
                return "Image generation failed"
            except Exception as e:
                return f"Error: {e}"

        @brain.tools.register("list_images", "List all generated images")
        def list_images() -> str:
            images = image_gen.list_generated()
            return "\n".join(images) if images else "No images generated yet"

        @brain.tools.register("delete_image", "Delete a generated image by filename")
        def delete_image(filename: str) -> str:
            if image_gen.delete_image(filename):
                return f"Deleted {filename}"
            return f"Image {filename} not found"

    except ImportError as e:
        logger.warning(f"Image generation not available: {e}")

    # --- Input Control (Mouse/Keyboard) ---

    try:
        from automation.input_control import InputControl
        input_ctrl = InputControl()

        @brain.tools.register("move_mouse", "Move cursor to screen position (x, y)")
        def move_mouse(x: int, y: int) -> str:
            return input_ctrl.move_mouse(x, y)

        @brain.tools.register("click_at", "Click at screen position (x, y). Button: left/right")
        def click_at(x: int, y: int, button: str = "left") -> str:
            return input_ctrl.click(x, y, button=button)

        @brain.tools.register("double_click", "Double click at screen position")
        def double_click(x: int, y: int) -> str:
            return input_ctrl.double_click(x, y)

        @brain.tools.register("right_click", "Right click at screen position")
        def right_click_at(x: int, y: int) -> str:
            return input_ctrl.right_click(x, y)

        @brain.tools.register("scroll_mouse", "Scroll up (positive) or down (negative)")
        def scroll_mouse(amount: int) -> str:
            return input_ctrl.scroll(amount)

        @brain.tools.register("type_text", "Type text on keyboard")
        def type_text(text: str) -> str:
            return input_ctrl.type_text(text)

        @brain.tools.register("press_key", "Press a key (enter, tab, escape, space, backspace, delete, etc)")
        def press_key(key: str) -> str:
            return input_ctrl.press_key(key)

        @brain.tools.register("hotkey", "Press key combo like 'ctrl+c', 'alt+tab', 'ctrl+v'")
        def hotkey(keys: str) -> str:
            key_list = [k.strip() for k in keys.split("+")]
            return input_ctrl.hotkey(*key_list)

        @brain.tools.register("get_cursor_pos", "Get current cursor position")
        def get_cursor_pos() -> str:
            return input_ctrl.get_mouse_position()

        @brain.tools.register("get_screen_size", "Get screen resolution")
        def get_screen_size() -> str:
            return input_ctrl.get_screen_size()

        @brain.tools.register("take_screenshot", "Take a screenshot of the screen")
        def take_screenshot() -> str:
            return input_ctrl.screenshot()

    except ImportError as e:
        logger.warning(f"Input control not available: {e}")

    # --- Open File ---

    @brain.tools.register("open_file", "Open a file with its default application")
    def open_file(path: str) -> str:
        import subprocess
        try:
            subprocess.Popen(
                ["xdg-open", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return f"Opened: {path}"
        except Exception as e:
            return f"Error: {e}"

    # --- News ---

    try:
        from automation.news import NewsAutomation
        news = NewsAutomation()

        @brain.tools.register("open_news", "Open a news website (bbc, cnn, reuters, google news, etc)")
        def open_news(site: str = "google news") -> str:
            return news.open_news(site)

        @brain.tools.register("search_news", "Search for news on a topic")
        def search_news(query: str) -> str:
            return news.search_news(query)

        @brain.tools.register("get_headlines", "Get top headlines from a news source")
        def get_headlines(source: str = "bbc") -> str:
            headlines = news.get_headlines(source)
            if headlines:
                return "\n".join(f"  {i+1}. {h['title']}" for i, h in enumerate(headlines))
            return f"No headlines from {source}"

        @brain.tools.register("list_news_sources", "List available news sources")
        def list_news_sources() -> str:
            return news.list_sources()

    except ImportError as e:
        logger.warning(f"News automation not available: {e}")

    # --- Live search (always-current news/web) ---

    try:
        from automation.live_search import get_live_search, build_live_context

        live = get_live_search()

        @brain.tools.register(
            "live_search",
            "Fetch live news and web results for a topic (always current)",
        )
        def live_search(query: str) -> str:
            try:
                return live.briefing(query, include_top=True)
            except Exception as e:
                return f"Error: {e}"

        @brain.tools.register(
            "top_headlines",
            "Get today's top world headlines",
        )
        def top_headlines() -> str:
            items = live.top_headlines(limit=12)
            if not items:
                return "No headlines available right now."
            return "\n".join(f"  {i+1}. {h['title']}" for i, h in enumerate(items))

        @brain.tools.register(
            "live_briefing",
            "Build a full live context briefing for the brain",
        )
        def live_briefing(query: str) -> str:
            return build_live_context(query, force=True)

    except ImportError as e:
        logger.warning(f"Live search not available: {e}")

    # --- Browser Agent (browser-use) ---

    try:
        from automation.web_agent import do_web_task

        @brain.tools.register(
            "do_web_task",
            "Use the browser agent to search, click, and complete web tasks",
        )
        def web_task(task: str) -> str:
            try:
                return do_web_task(task)
            except Exception as e:
                return f"Error: {e}"

    except ImportError as e:
        logger.warning(f"Web agent not available: {e}")

    logger.info(f"Registered {len(brain.tools.list_tool_names())} automation tools")
