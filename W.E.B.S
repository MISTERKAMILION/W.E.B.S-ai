#!/bin/bash
# W.E.B.S — AI Operating System Launcher
# Usage: W.E.B.S --start | --chat | --face | --help

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/webs.py" "$@"
