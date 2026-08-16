#!/usr/bin/env bash
# AQI module: AirNow official monitor (preferred) -> Open-Meteo model (fallback).
# Modes: waybar (JSON) | notify (dunst popup) | <none> (polybar-format string)
# Config: ~/.config/wayland-plus/config.env (LAT/LON/CITY)
# Cache: 15 min. Colors: Catppuccin Mocha.

CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/wayland-plus/config.env"
[ -f "$CONFIG" ] && . "$CONFIG"
if [ -z "${LAT:-}" ] || [ -z "${LON:-}" ] || [ "$LAT" = "0.0" ]; then
  echo "wayland-plus: set LAT/LON in $CONFIG" >&2
  [ "$1" = waybar ] && echo '{"text": "󰢬 cfg", "class": "nodata"}' || echo "%{F#f38ba8}󰢬 cfg%{F-}"
  exit 1
fi
CITY="${CITY:-}"

CACHE=/tmp/wayland-plus-aqi-${USER}.json
MAX_AGE=900

color_for() {
  local aqi=$1
  if   (( aqi <= 50 ));  then echo "#a6e3a1"
  elif (( aqi <= 100 )); then echo "#f9e2af"
  elif (( aqi <= 150 )); then echo "#fab387"
  elif (( aqi <= 200 )); then echo "#f38ba8"
  elif (( aqi <= 300 )); then echo "#cba6f7"
  else                        echo "#f38ba8"; fi
}

fetch() {
  local raw obs aqi pm
  # 1) AirNow official monitor (hourly observation, dataType=O; no API key)
  if raw=$(curl -fsS --max-time 10 "https://airnowgovapi.com/reportingarea/get?latitude=${LAT}&longitude=${LON}"); then
    obs=$(jq -c '[.[] | select(.dataType=="O" and (.aqi|type=="number"))] | sort_by(.issueDate + " " + .time) | last' <<<"$raw" 2>/dev/null)
    if [ -n "$obs" ] && [ "$obs" != "null" ]; then
      jq -n --argjson obs "$obs" '{
        source: "AirNow monitor",
        aqi: $obs.aqi,
        category: $obs.category,
        parameter: $obs.parameter,
        asof: ($obs.time + " " + $obs.timezone)
      }' > "$CACHE" && return
    fi
  fi
  # 2) Open-Meteo CAMS model fallback (no API key)
  if raw=$(curl -fsS --max-time 10 "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${LAT}&longitude=${LON}&current=us_aqi,pm2_5"); then
    aqi=$(jq -r '.current.us_aqi // empty' <<<"$raw")
    if [ -n "$aqi" ]; then
      pm=$(jq -r '.current.pm2_5 // empty' <<<"$raw")
      jq -n --argjson aqi "$aqi" --arg pm "$pm" '{
        source: "Open-Meteo model (AirNow unavailable)",
        aqi: $aqi,
        category: (if $aqi<=50 then "Good" elif $aqi<=100 then "Moderate" elif $aqi<=150 then "Unhealthy for Sensitive Groups" elif $aqi<=200 then "Unhealthy" elif $aqi<=300 then "Very Unhealthy" else "Hazardous" end),
        pm2_5: ($pm|tonumber? // null)
      }' > "$CACHE"
    fi
  fi
}

now=$(date +%s)
mtime=$(stat -c %Y "$CACHE" 2>/dev/null || echo 0)
if (( now - mtime >= MAX_AGE )); then fetch; fi

aqi=$(jq -r '.aqi // empty' "$CACHE" 2>/dev/null)
if [ -z "$aqi" ]; then
  if [ "$1" = notify ]; then
    notify-send "Air Quality" "No data from AirNow or Open-Meteo right now." 2>/dev/null
  elif [ "$1" = waybar ]; then
    echo '{"text": "󰢬 --", "class": "nodata"}'
  else
    echo "%{F#585b70}󰢬 --%{F-}"
  fi
  exit 0
fi

color=$(color_for "$aqi")
class_for() {
  local aqi=$1
  if   (( aqi <= 50 ));  then echo good
  elif (( aqi <= 100 )); then echo moderate
  elif (( aqi <= 150 )); then echo usg
  elif (( aqi <= 200 )); then echo unhealthy
  elif (( aqi <= 300 )); then echo veryunhealthy
  else                        echo hazardous; fi
}
case "$1" in
  notify)
    notify-send "Air Quality${CITY:+ — $CITY}" "AQI: ${aqi} — $(jq -r '.category' "$CACHE")
Parameter: $(jq -r '.parameter // "PM2.5 (modeled)"' "$CACHE")
PM2.5: $(jq -r '(.pm2_5 // "n/a") | tostring' "$CACHE") µg/m³
As of: $(jq -r '.asof // "now"' "$CACHE")
Source: $(jq -r '.source' "$CACHE")" 2>/dev/null
    ;;
  waybar)
    printf '{"text": "󰢬 %s", "class": "%s", "tooltip": "%s — %s | PM2.5: %s | As of: %s"}\n' \
      "$aqi" "$(class_for "$aqi")" "$(jq -r '.category' "$CACHE")" "$(jq -r '.source' "$CACHE")" \
      "$(jq -r '(.pm2_5 // "n/a") | tostring' "$CACHE")" "$(jq -r '.asof // "now"' "$CACHE")"
    ;;
  *)
    echo "%{F${color}}󰢬 ${aqi}%{F-}"
    ;;
esac
