#!/usr/bin/env bash
# Memory detail popup: top consumers via dunst.
body=$(ps -eo pmem,comm --sort=-pmem | awk 'NR==1{next} NR>6{exit} {printf "%5.1f%%  %s\n", $1, $2}')
used=$(free -h | awk '/^Mem:/{print $3 " / " $2}')
notify-send -a mem-info -t 15000 -u normal "Memory — $(hostname)" "Used: ${used}

Top consumers:
${body}"
