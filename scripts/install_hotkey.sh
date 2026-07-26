#!/usr/bin/env bash
# Install W+V global activator for W.E.B.S (no terminal needed after this).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"

echo "==> Installing W.E.B.S W+V activator"

chmod +x "$ROOT/scripts/start_webs.sh" "$ROOT/scripts/webs_daemon.py" "$ROOT/scripts/install_hotkey.sh"

# Python deps
"$PYTHON" -m pip install -q pynput evdev 2>/dev/null || true

# Autostart daemon on login
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/webs-hotkey.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=W.E.B.S Hotkey (W+V)
Comment=Press W+V to start W.E.B.S
Exec=$PYTHON $ROOT/scripts/webs_daemon.py
Path=$ROOT
Terminal=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF

# App launcher
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/webs.desktop" <<EOF
[Desktop Entry]
Name=W.E.B.S
Comment=Orange Jarvis AI — face + voice + live brain
Exec=bash $ROOT/scripts/start_webs.sh
Path=$ROOT
Terminal=false
Type=Application
Categories=Utility;
StartupNotify=true
EOF

# GNOME backup shortcut: Super+Shift+W (works even without input group)
if command -v gsettings >/dev/null 2>&1; then
  SCHEMA="org.gnome.settings-daemon.plugins.media-keys"
  PATH_BASE="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"
  KEY="$PATH_BASE/webs/"
  existing="$(gsettings get $SCHEMA custom-keybindings 2>/dev/null || echo "@as []")"
  if [[ "$existing" != *"$KEY"* ]]; then
    if [[ "$existing" == "@as []" || "$existing" == "[]" ]]; then
      gsettings set $SCHEMA custom-keybindings "['$KEY']"
    else
      # append
      trimmed="${existing%]*}"
      gsettings set $SCHEMA custom-keybindings "${trimmed}, '$KEY']"
    fi
  fi
  gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEY name "W.E.B.S"
  gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEY command "bash $ROOT/scripts/start_webs.sh"
  gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEY binding "<Super><Shift>w"
  echo "==> GNOME backup shortcut set: Super+Shift+W"
fi

# Allow global keyboard read (needed for true W+V on Wayland)
if ! groups | grep -q '\binput\b'; then
  echo ""
  echo "==> One-time setup for true W+V everywhere (Wayland):"
  echo "    sudo usermod -aG input \$USER"
  echo "    then log out and back in"
  echo ""
  echo "    Until then use: Super+Shift+W"
else
  echo "==> User already in 'input' group — W+V will work globally"
fi

# Restart daemon now
pkill -f "webs_daemon.py" 2>/dev/null || true
rm -f /tmp/webs_daemon.pid
nohup "$PYTHON" "$ROOT/scripts/webs_daemon.py" >/tmp/webs_hotkey_daemon.log 2>&1 &
sleep 0.5
echo "==> Daemon started (pid $(cat /tmp/webs_daemon.pid 2>/dev/null || echo '?'))"
echo ""
echo "Done. Press W+V (or Super+Shift+W) to start W.E.B.S — no code needed."
