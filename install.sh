#!/usr/bin/env bash
# wayland-plus installer
# Copies configs into place, enables systemd user units.
# Anything it replaces is backed up as <name>.bak-<timestamp>.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
STAMP=$(date +%Y%m%d-%H%M%S)

backup() {
  if [ -e "$1" ]; then
    mv -v "$1" "$1.bak-$STAMP"
    echo "  (existing $1 backed up as $1.bak-$STAMP)"
  fi
}

echo "== wayland-plus install =="

# 1. Config directory + personal config.env
CFG="$HOME/.config/wayland-plus"
mkdir -p "$CFG/scripts" "$HOME/.local/share/wayland-plus" "$HOME/.local/state"
if [ ! -f "$CFG/config.env" ]; then
  cp "$SRC/config.env.example" "$CFG/config.env"
  echo ">> Created $CFG/config.env"
  echo ">> EDIT IT: set LAT/LON/TZ/CITY before the AQI modules will work."
else
  echo ">> Keeping existing $CFG/config.env"
fi

# 2. Scripts
cp -v "$SRC"/scripts/*.sh "$SRC"/scripts/*.py "$CFG/scripts/"
chmod +x "$CFG"/scripts/*.sh "$CFG"/scripts/*.py

# 3. Bar / compositor / notification configs (back up whatever we replace)
backup "$HOME/.config/waybar"
cp -rv "$SRC/waybar" "$HOME/.config/waybar"
chmod +x "$HOME/.config/waybar/launch.sh"

backup "$HOME/.config/sway"
cp -rv "$SRC/sway" "$HOME/.config/sway"
chmod +x "$HOME/.config/sway/scratch-toggle.sh"

backup "$HOME/.config/dunst"
cp -rv "$SRC/dunst" "$HOME/.config/dunst"

# 4. Systemd user units: CPU history sampler + hourly AQI chart pre-render
mkdir -p "$HOME/.config/systemd/user"
cp -v "$SRC"/systemd/*.service "$SRC"/systemd/*.timer "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now cpu-history.service
systemctl --user enable --now aqi-chart.timer

cat <<EOF

== Done ==
Dependencies (Debian/Ubuntu):
  sudo apt install waybar sway swaybg swayidle swaylock dunst kitty tmux \\
    fuzzel rofi grim slurp wl-clipboard dex pavucontrol \\
    network-manager-gnome jq curl python3-matplotlib \\
    swayosd cliphist poweralertd \\
    fonts-jetbrains-mono-nerd-font   # or install JetBrainsMono Nerd Font manually
Optional: sysstat (adds historical CPU data via sar backfill)

Next steps:
  1. Edit $CFG/config.env (coordinates, timezone, city)
  2. Log out and back into a sway session (or: systemctl --user restart for live tweaks)
  3. Enjoy. Click the AQI/CPU/MEM modules for charts and popups.

Note: dunst crops notification icons taller than ~300px on some setups;
all bundled chart scripts render at 290px or less to stay safe.
EOF
