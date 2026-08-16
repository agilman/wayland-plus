#!/usr/bin/env bash
# Live memory% for polybar. Output matches old internal/memory label.
free | awk '/^Mem:/{printf "󰍛 %d%%\n", 100*$3/$2}'
