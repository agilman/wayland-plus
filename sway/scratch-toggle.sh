#!/bin/bash
# Lazy scratchpad: create on first use, show/hide after. Marker: window title claw-scratch.
if swaymsg -t get_tree | jq -e "[.. | objects | select(.name? == \"claw-scratch\")] | length > 0" >/dev/null; then
  swaymsg scratchpad show
else
  kitty --title claw-scratch -e tmux new-session -A -s scratch &
fi
