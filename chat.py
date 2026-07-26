#!/usr/bin/env python3
"""Command-line chat interface for W.E.B.S AI."""

import sys
import os
import readline
from pathlib import Path
from typing import Optional
import argparse

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from brain import Brain


CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


class Chat:
    """Interactive chat interface for W.E.B.S."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        offline_model: str = "llama3.2:3b",
        enable_face: bool = False,
    ):
        self.api_key = api_key
        self.offline_model = offline_model
        self.running = True
        self.history_file = os.path.expanduser("~/.webs_chat_history")
        self._setup_history()

        # Create brain with offline model first
        self.brain = Brain(
            api_key=api_key,
            offline_model=offline_model,
            enable_face=enable_face,
        )

    def _setup_history(self):
        try:
            readline.read_history_file(self.history_file)
        except FileNotFoundError:
            pass
        readline.set_history_length(1000)

    def _save_history(self):
        try:
            readline.write_history_file(self.history_file)
        except Exception:
            pass

    def _setup_groq_key(self) -> str:
        """Prompt for Groq API key if not set. Returns key or empty."""
        key = self.api_key or os.environ.get("GROQ_API_KEY", "")
        if key:
            return key

        print(f"\n  {BOLD}Online mode needs a Groq API key.{RESET}")
        print(f"  Get one free at: {CYAN}https://console.groq.com/keys{RESET}\n")
        try:
            key = input(f"  {CYAN}Enter Groq API key (or press Enter to skip): {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            return ""

        if key:
            # Save to env file for next time
            env_file = Path(__file__).parent / ".env"
            with open(env_file, "w") as f:
                f.write(f"GROQ_API_KEY={key}\n")
            os.environ["GROQ_API_KEY"] = key
            print(f"  {GREEN}Key saved to .env{RESET}")
        return key

    def _choose_mode(self) -> bool:
        """Ask user to pick online or offline. Returns False if user quits."""
        print(f"\n{BOLD}{CYAN}{'=' * 60}{RESET}")
        print(f"{BOLD}{CYAN}       W.E.B.S AI Assistant{RESET}")
        print(f"{BOLD}{CYAN}       Created by Mister Nossair Zaidi{RESET}")
        print(f"{BOLD}{CYAN}{'=' * 60}{RESET}")

        providers = self.brain.model_manager.list_providers()
        has_ollama = "ollama" in providers

        print(f"\n{BOLD}Choose your mode:{RESET}\n")
        print(f"  {GREEN}[1]{RESET} Online  (Groq API - fast, requires internet)")
        print(f"  {GREEN}[2]{RESET} Offline (Ollama - local, no internet needed)")
        print(f"  {YELLOW}[3]{RESET} Demo    (dummy responses for testing)")
        print()

        while True:
            try:
                choice = input(f"{BOLD}{CYAN}Pick [1/2/3]: {RESET}").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{YELLOW}Goodbye!{RESET}")
                return False

            if choice == "1":
                key = self._setup_groq_key()
                if not key:
                    print(f"  {RED}No key provided. Try offline or demo mode.{RESET}\n")
                    continue
                # Rebuild brain with the key
                self.brain = Brain(api_key=key, offline_model=self.offline_model)
                self.brain.set_model_preference("online")
                current = self.brain.model_manager.get_current_provider()
                print(f"\n  {GREEN}Online mode activated ({current}){RESET}\n")
                return True
            elif choice == "2" and has_ollama:
                self.brain.set_model_preference("offline")
                current = self.brain.model_manager.get_current_provider()
                print(f"\n  {GREEN}Offline mode activated ({current}){RESET}\n")
                return True
            elif choice == "3":
                self.brain.model_manager.switch_to("dummy")
                print(f"\n  {YELLOW}Demo mode activated (dummy responses){RESET}\n")
                return True
            else:
                print(f"  {RED}Invalid choice. Try again.{RESET}")

    def _print_welcome(self):
        mode = self.brain.model_manager.get_current_provider()
        print(f"{BOLD}{CYAN}╔══════════════════════════════════════╗{RESET}")
        print(f"{BOLD}{CYAN}║        W.E.B.S AI Assistant         ║{RESET}")
        print(f"{BOLD}{CYAN}╚══════════════════════════════════════╝{RESET}")
        print(f"\n  Mode: {GREEN}{mode}{RESET}")
        print(f"\n  Commands:")
        print(f"    /online   - Switch to online model")
        print(f"    /offline  - Switch to offline model")
        print(f"    /models   - Show available models")
        print(f"    /help     - Show help")
        print(f"    /exit     - Exit")
        print(f"\n  {'-' * 40}\n")

    def _print_help(self):
        print(f"\n  Commands:")
        print(f"    /online   - Switch to online model")
        print(f"    /offline  - Switch to offline model")
        print(f"    /models   - Show available models")
        print(f"    /clear    - Clear screen")
        print(f"    /exit     - Exit")
        print()

    def _show_models(self):
        models = self.brain.get_available_models()
        current = self.brain.model_manager.get_current_provider()
        print(f"\n  Available providers:")
        for m in models:
            marker = f"{GREEN}>>>{RESET} " if m == current else "    "
            print(f"  {marker}{m}")
        print()

    def _switch_model(self, preference: str):
        pref_map = {
            "online": "online",
            "offline": "offline",
        }
        if preference not in pref_map:
            print(f"  {RED}Unknown: {preference}{RESET}")
            return
        self.brain.set_model_preference(pref_map[preference])
        current = self.brain.model_manager.get_current_provider()
        print(f"  {GREEN}Switched to: {current}{RESET}\n")

    def _clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        self._print_welcome()

    def _handle_command(self, command: str) -> bool:
        if command == "/exit":
            print(f"\n{YELLOW}Goodbye!{RESET}")
            self._save_history()
            return False
        elif command == "/help":
            self._print_help()
        elif command == "/models":
            self._show_models()
        elif command == "/online":
            self._switch_model("online")
        elif command == "/offline":
            self._switch_model("offline")
        elif command == "/clear":
            self._clear_screen()
        else:
            print(f"  {RED}Unknown command: {command}{RESET}")
            print(f"  Type /help for available commands")
        return True

    def _process_input(self, user_input: str):
        if not user_input.strip():
            return

        if user_input.startswith("/"):
            self._handle_command(user_input)
            return

        print(f"\n  {YELLOW}Thinking...{RESET}", end="", flush=True)

        try:
            response = self.brain.process(user_input)
            print("\r" + " " * 20 + "\r", end="", flush=True)
            print(f"\n  {BOLD}W.E.B.S:{RESET} {response}\n")
        except Exception as e:
            print("\r" + " " * 20 + "\r", end="", flush=True)
            print(f"\n  {RED}Error: {e}{RESET}\n")

    def run(self):
        """Run the chat with mode selection first."""
        # Step 1: Choose mode
        if not self._choose_mode():
            return

        # Step 2: Show welcome and start chatting
        self._print_welcome()

        while self.running:
            try:
                user_input = input(f"{BOLD}{CYAN}You: {RESET}").strip()
                self._process_input(user_input)
            except KeyboardInterrupt:
                print(f"\n\n{YELLOW}Goodbye!{RESET}")
                self._save_history()
                break
            except EOFError:
                print(f"\n\n{YELLOW}Goodbye!{RESET}")
                self._save_history()
                break
            except Exception as e:
                print(f"\n  {RED}Unexpected error: {e}{RESET}\n")

    def run_once(self, message: str):
        if not message.strip():
            return
        print(f"\n  You: {message}")
        print(f"  {YELLOW}Thinking...{RESET}", end="", flush=True)
        try:
            response = self.brain.process(message)
            print("\r" + " " * 20 + "\r", end="", flush=True)
            print(f"\n  {BOLD}W.E.B.S:{RESET} {response}\n")
        except Exception as e:
            print("\r" + " " * 20 + "\r", end="", flush=True)
            print(f"\n  {RED}Error: {e}{RESET}\n")


def main():
    parser = argparse.ArgumentParser(description="W.E.B.S AI Chat Interface")
    parser.add_argument("--message", "-m", type=str, help="Send a single message and exit")
    parser.add_argument("--api-key", "-k", type=str, help="Groq API key for online model")
    parser.add_argument(
        "--offline-model", "-o", type=str, default="llama3.2:3b",
        help="Offline model name (default: llama3.2:3b)"
    )
    parser.add_argument(
        "--face", "-f", action="store_true",
        help="Enable animated face window with lip sync"
    )

    args = parser.parse_args()

    # Load .env file if it exists
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

    api_key = args.api_key or os.getenv("GROQ_API_KEY")

    chat = Chat(
        api_key=api_key,
        offline_model=args.offline_model,
        enable_face=args.face,
    )

    if args.message:
        chat.run_once(args.message)
    else:
        chat.run()


if __name__ == "__main__":
    main()
