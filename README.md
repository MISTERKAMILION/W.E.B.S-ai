# W.E.B.S. — Web Enhanced Butler System

W.E.B.S. is a modular personal AI assistant built in Python. It brings conversational AI, memory, voice interaction, web research, and desktop automation together behind a command-line interface and an optional animated HUD.

**Created by Nossair Zaidi · [@MISTERKAMILION](https://github.com/MISTERKAMILION)**

## Features

- **Modular assistant core** that coordinates prompts, tools, memory, and tasks.
- **Multiple AI providers:** Groq, local Ollama, Puter, and a demo provider (availability depends on configuration).
- **Voice input and output** with local and online speech options.
- **Web research** and an optional AI-assisted browser agent.
- **Desktop and file automation**, including app management, filesystem operations, and keyboard/mouse actions.
- **Persistent context** through conversation memory, preferences, tasks, and SQLite-backed search.
- **Animated interface** with text, voice, hotkey, and face modes.

## Project structure

| Directory / file | Purpose |
| --- | --- |
| `brain/` | Orchestration, providers, memory, tools, planning, and events |
| `automation/` | Desktop, browser, filesystem, search, and image-generation tools |
| `data/` | Application data and supporting modules |
| `memory/` | Conversation history and preferences |
| `scripts/` | Helper scripts and launch support |
| `voices/` | Voice assets and related resources |
| `run_webs.py` | Main launcher with selectable modes |
| `webs.py` | CLI launcher |
| `webs_face.py` | Animated HUD interface |
| `requirements.txt` | Python package dependencies |

## Requirements

- Python 3
- Packages listed in `requirements.txt`
- Optional provider credentials or local services (for example, Groq API access or Ollama) for the corresponding AI backend
- Audio devices and system libraries for voice features; a compatible desktop environment for automation and the HUD

## Setup

1. Clone this repository and enter its directory.
2. Install the Python dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Configure the provider and optional service you want to use. Keep credentials out of source control.
4. Start in text mode:

   ```bash
   python run_webs.py
   ```

## Run modes

```bash
python run_webs.py                 # Text mode
python run_webs.py --voice         # Voice mode
python run_webs.py --hotkey        # Hotkey mode
python run_webs.py --face          # Animated HUD
python run_webs.py --face --voice  # HUD with voice
python run_webs.py --face --windowed
python webs.py -m "your message"   # Single message
```

Some features require additional setup, such as a browser engine, audio support, a configured model provider, or a supported desktop environment.

## Safety and privacy

W.E.B.S. can interact with the filesystem, applications, browser, and operating system. Review actions before allowing them, and run the assistant with only the permissions it needs. Conversation history, preferences, logs, and generated files may be stored locally. Do not commit API keys, personal data, or other secrets.

## License

Released under the [MIT License](LICENSE).

---

Built by **Nossair Zaidi** · [GitHub: @MISTERKAMILION](https://github.com/MISTERKAMILION)
