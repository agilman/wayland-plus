#!/usr/bin/env bash
# Weather module: Open-Meteo current conditions + rain outlook (no API key).
# Modes: waybar (JSON) | notify (dunst popup)
# Config: ~/.config/wayland-plus/config.env (LAT/LON/CITY)

CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/wayland-plus/config.env"
[ -f "$CONFIG" ] && . "$CONFIG"
if [ -z "${LAT:-}" ] || [ -z "${LON:-}" ] || [ "$LAT" = "0.0" ]; then
  [ "$1" = waybar ] && echo '{"text": "󰖍 cfg", "class": "nodata"}' || echo "set LAT/LON in $CONFIG" >&2
  exit 1
fi

CACHE=/tmp/wayland-plus-weather-${USER}.json
MAX_AGE=900

UNITS="${UNITS:-metric}"   # metric | imperial (config.env)
if [ "$UNITS" = imperial ]; then
  UNIT_PARAMS="&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch"
  TU="°F"; WU="mph"; RU="in"
else
  UNIT_PARAMS=""
  TU="°C"; WU="km/h"; RU="mm"
fi

fetch() {
  local raw
  raw=$(curl -fsS --max-time 10 "https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m&hourly=precipitation_probability,precipitation&daily=precipitation_probability_max,precipitation_sum,temperature_2m_max,temperature_2m_min&forecast_days=1&timezone=auto${UNIT_PARAMS}") || return
  jq '{
    temp: .current.temperature_2m,
    feels: .current.apparent_temperature,
    code: .current.weather_code,
    wind: .current.wind_speed_10m,
    prob_max: .daily.precipitation_probability_max[0],
    rain_sum: .daily.precipitation_sum[0],
    tmax: .daily.temperature_2m_max[0],
    tmin: .daily.temperature_2m_min[0],
    rain_3h: ([.hourly.precipitation[:3] | .[]] | add),
    asof: (.current.time)
  }' <<<"$raw" > "$CACHE"
}

now=$(date +%s)
mtime=$(stat -c %Y "$CACHE" 2>/dev/null || echo 0)
if (( now - mtime >= MAX_AGE )); then fetch; fi

temp=$(jq -r '.temp // empty' "$CACHE" 2>/dev/null)
if [ -z "$temp" ]; then
  [ "$1" = waybar ] && echo '{"text": "󰖍 --", "class": "nodata"}' || echo "no weather data"
  exit 0
fi

code=$(jq -r '.code' "$CACHE")
case "$code" in
  0)            icon=󰖑; class=clear;  desc="Clear sky" ;;
  1|2)          icon=󰖉; class=clear;  desc="Partly cloudy" ;;
  3)            icon=󰖍; class=cloudy; desc="Overcast" ;;
  45|48)        icon=󰖍; class=cloudy; desc="Fog" ;;
  51|53|55|56|57) icon=󰖐; class=rain; desc="Drizzle" ;;
  61|63|65|66|67) icon=󰖐; class=rain; desc="Rain" ;;
  71|73|75|77)  icon=󰬶; class=snow;  desc="Snow" ;;
  80|81|82)     icon=󰖐; class=rain;  desc="Rain showers" ;;
  85|86)        icon=󰬶; class=snow;  desc="Snow showers" ;;
  95|96|99)     icon=󰽜; class=storm; desc="Thunderstorm" ;;
  *)            icon=󰖍; class=cloudy; desc="Code $code" ;;
esac

wind=$(jq -r '.wind' "$CACHE")
prob=$(jq -r '.prob_max // 0' "$CACHE")
rainsum=$(jq -r '.rain_sum // 0' "$CACHE")
feels=$(jq -r '.feels' "$CACHE")
tmax=$(jq -r '.tmax' "$CACHE"); tmin=$(jq -r '.tmin' "$CACHE")
rain3h=$(jq -r '.rain_3h // 0' "$CACHE")

case "$1" in
  notify)
    notify-send -a weather -t 15000 "Weather${CITY:+ — $CITY}: ${desc}, ${temp}${TU}" "Feels like ${feels}${TU} · Wind ${wind} ${WU}
Next 3h rain: ${rain3h} ${RU}
Today: ${rainsum} ${RU} expected, ${prob}% chance
High ${tmax}${TU} / Low ${tmin}${TU}" 2>/dev/null
    ;;
  *)
    printf '{"text": "%s %s%s", "class": "%s", "tooltip": "%s · wind %s %s · rain today %s %s (%s%%)"}\n' \
      "$icon" "$temp" "$TU" "$class" "$desc" "$wind" "$WU" "$rainsum" "$RU" "$prob"
    ;;
esac
