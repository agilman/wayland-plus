#!/usr/bin/env bash
# Live CPU% for polybar (1s delta from /proc/stat). Output matches old internal/cpu label.
read -r _ u1 n1 s1 i1 w1 q1 sq1 st1 _ < /proc/stat
sleep 1
read -r _ u2 n2 s2 i2 w2 q2 sq2 st2 _ < /proc/stat
idle=$(( (i2 + w2) - (i1 + w1) ))
total=$(( (u2+n2+s2+i2+w2+q2+sq2+st2) - (u1+n1+s1+i1+w1+q1+sq1+st1) ))
if (( total > 0 )); then
  pct=$(( 100 * (total - idle) / total ))
else
  pct=0
fi
echo "󰻠 ${pct}%"
