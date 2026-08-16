#!/bin/bash
# Waybar launcher (mirrors polybar/launch.sh). Logs to ~/.local/state/waybar.log
killall -q waybar
while pgrep -u $UID -x waybar >/dev/null; do sleep 0.2; done
# Wait for the sway IPC socket (guards against session-start race)
for i in $(seq 1 50); do
  [ -S "${SWAYSOCK:-}" ] && break
  sleep 0.2
done
mkdir -p ~/.local/state
waybar >> ~/.local/state/waybar.log 2>&1 &
