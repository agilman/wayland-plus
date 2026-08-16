#!/usr/bin/env bash
# Samples total CPU busy% every 30s into a rolling 48h log.
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/wayland-plus"
mkdir -p "$DATA"
LOG="$DATA/cpu-history.log"
read_cpu() { awk '/^cpu /{print $2+$3+$4+$5+$6+$7+$8, $5+$6}' /proc/stat; }

prev=($(read_cpu))
while :; do
  sleep 30
  cur=($(read_cpu))
  dt=$((cur[0]-prev[0])); di=$((cur[1]-prev[1]))
  if (( dt > 0 )); then
    busy=$(awk -v dt="$dt" -v di="$di" 'BEGIN{printf "%.1f", 100*(dt-di)/dt}')
    echo "$(date +%s) $busy" >> "$LOG"
  fi
  prev=("${cur[@]}")
  # trim to last 48h
  cutoff=$(( $(date +%s) - 172800 ))
  if [ -f "$LOG" ] && (( $(wc -l < "$LOG") > 6000 )); then
    tmp=$(mktemp)
    awk -v c="$cutoff" '$1 >= c' "$LOG" > "$tmp" && mv "$tmp" "$LOG"
  fi
done
