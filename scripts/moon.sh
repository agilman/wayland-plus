#!/usr/bin/env bash
# Moon phase module — phase computed offline (synodic month from known new moon).
# Sunrise/sunset from Open-Meteo (cached 6h) when config.env has LAT/LON.
# Modes: waybar (JSON) | notify (dunst popup)

SYNODIC=29.53058867
EPOCH=947182440  # 2000-01-06 18:14 UTC, a known new moon

CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/wayland-plus/config.env"
[ -f "$CONFIG" ] && . "$CONFIG"

now=$(date +%s)
age=$(awk -v n="$now" -v e="$EPOCH" -v s="$SYNODIC" 'BEGIN{a=(n-e)/86400; printf "%.4f", a - int(a/s)*s}')
idx=$(awk -v a="$age" -v s="$SYNODIC" 'BEGIN{print int((a/s)*8 + 0.5) % 8}')
illum=$(awk -v a="$age" -v s="$SYNODIC" 'BEGIN{pi=3.14159265; printf "%.0f", (1-cos(2*pi*a/s))/2*100}')
next_full=$(awk -v a="$age" -v s="$SYNODIC" 'BEGIN{d=s/2-a; if(d<0)d+=s; printf "%.1f", d}')
next_new=$(awk -v a="$age" -v s="$SYNODIC" 'BEGIN{printf "%.1f", s-a}')

icons=(󰽡 󰽢 󰽣 󰽤 󰽥 󰽦 󰽧 󰽨)
names=("New Moon" "Waxing Crescent" "First Quarter" "Waxing Gibbous" "Full Moon" "Waning Gibbous" "Last Quarter" "Waning Crescent")

# --- sunrise / sunset (optional, cached 6h, needs LAT/LON) ---
sunline=""
if [ -n "${LAT:-}" ] && [ -n "${LON:-}" ] && [ "$LAT" != "0.0" ]; then
  SUN_CACHE=/tmp/wayland-plus-sun-${USER}.json
  smtime=$(stat -c %Y "$SUN_CACHE" 2>/dev/null || echo 0)
  if (( now - smtime >= 21600 )); then
    curl -fsS --max-time 5 "https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}&daily=sunrise,sunset&forecast_days=1&timezone=auto" \
      | jq '{sunrise: .daily.sunrise[0], sunset: .daily.sunset[0]}' > "$SUN_CACHE" 2>/dev/null
  fi
  sunrise=$(jq -r '.sunrise | split("T")[1] // empty' "$SUN_CACHE" 2>/dev/null)
  sunset=$(jq -r '.sunset | split("T")[1] // empty' "$SUN_CACHE" 2>/dev/null)
  [ -n "$sunrise" ] && [ -n "$sunset" ] && sunline="Sunrise ${sunrise} · Sunset ${sunset}"
fi

case "$1" in
  notify)
    notify-send -a moon -t 15000 "${names[$idx]} — ${illum}% illuminated" "Moon age: ${age} days of ${SYNODIC%.*}
Next full moon: in ${next_full} days
Next new moon: in ${next_new} days${sunline:+
$sunline}" 2>/dev/null
    ;;
  *)
    printf '{"text": "%s", "tooltip": "%s — %s%% illuminated%s"}\n' \
      "${icons[$idx]}" "${names[$idx]}" "$illum" "${sunline:+ · $sunline}"
    ;;
esac
