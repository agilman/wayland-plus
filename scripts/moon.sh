#!/usr/bin/env bash
# Moon phase module — computed offline (synodic month from a known new moon).
# Modes: waybar (JSON) | notify (dunst popup)

SYNODIC=29.53058867
EPOCH=947182440  # 2000-01-06 18:14 UTC, a known new moon

now=$(date +%s)
age=$(awk -v n="$now" -v e="$EPOCH" -v s="$SYNODIC" 'BEGIN{a=(n-e)/86400; printf "%.4f", a - int(a/s)*s}')
idx=$(awk -v a="$age" -v s="$SYNODIC" 'BEGIN{print int((a/s)*8 + 0.5) % 8}')
illum=$(awk -v a="$age" -v s="$SYNODIC" 'BEGIN{pi=3.14159265; printf "%.0f", (1-cos(2*pi*a/s))/2*100}')
next_full=$(awk -v a="$age" -v s="$SYNODIC" 'BEGIN{d=s/2-a; if(d<0)d+=s; printf "%.1f", d}')
next_new=$(awk -v a="$age" -v s="$SYNODIC" 'BEGIN{printf "%.1f", s-a}')

icons=(󰽡 󰽢 󰽣 󰽤 󰽥 󰽦 󰽧 󰽨)
names=("New Moon" "Waxing Crescent" "First Quarter" "Waxing Gibbous" "Full Moon" "Waning Gibbous" "Last Quarter" "Waning Crescent")

case "$1" in
  notify)
    notify-send -a moon -t 15000 "${names[$idx]} — ${illum}% illuminated" "Moon age: ${age} days of ${SYNODIC%.*}
Next full moon: in ${next_full} days
Next new moon: in ${next_new} days" 2>/dev/null
    ;;
  *)
    printf '{"text": "%s", "tooltip": "%s — %s%% illuminated"}\n' \
      "${icons[$idx]}" "${names[$idx]}" "$illum"
    ;;
esac
