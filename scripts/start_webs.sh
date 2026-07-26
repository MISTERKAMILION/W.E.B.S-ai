#!/usr/bin/env bash
# Start full W.E.B.S (face + voice + live brain) — no terminal needed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LOCK="/tmp/webs_face.lock"
PIDFILE="/tmp/webs_face.pid"

# If already running, bring window forward if possible and exit
if [[ -f "$PIDFILE" ]]; then
  oldpid="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [[ -n "${oldpid:-}" ]] && kill -0 "$oldpid" 2>/dev/null; then
    # Already up — nothing to do
    exit 0
  fi
  rm -f "$PIDFILE" "$LOCK"
fi

PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi

# Load .env into environment
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

# Launch Jarvis face + voice (fullscreen HUD)
nohup "$PYTHON" "$ROOT/webs_face.py" --voice \
  > /tmp/webs_face.log 2>&1 &
echo $! > "$PIDFILE"
exit 0
