#!/usr/bin/env bash
# CPU detail popup: top consumers via dunst (mirrors mem-info.sh).
body=$(ps -eo pcpu,comm --sort=-pcpu | awk 'NR==1{next} NR>6{exit} {printf "%5.1f%%  %s\n", $1, $2}')
load=$(cut -d" " -f1-3 /proc/loadavg)
nproc=$(nproc)
notify-send -a cpu-info -t 15000 -u normal "CPU — $(hostname)" "Load: ${load}  (${nproc} cores)

Top consumers:
${body}"
