#!/usr/bin/env bash
# Opens the AirNow fire/smoke map centered on your configured coordinates.
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/wayland-plus/config.env"
[ -f "$CONFIG" ] && . "$CONFIG"
if [ -z "${LAT:-}" ] || [ -z "${LON:-}" ] || [ "$LAT" = "0.0" ]; then
  notify-send "wayland-plus" "Set LAT/LON in $CONFIG first." 2>/dev/null
  exit 1
fi
xdg-open "https://fire.airnow.gov/?lat=${LAT}&lon=${LON}&zoom=9"
