# wayland-plus

A Catppuccin-Mocha Wayland desktop setup for **sway + waybar + dunst**, built
around clickable status modules with real charts — not just numbers.

Evolved from an i3/polybar rice; now fully Wayland-native.

## The modules

| Module | Shows | Left click | Right click | Middle click |
|---|---|---|---|---|
| **AQI** | US Air Quality Index, EPA-colored | 24h forecast chart (dunst image) | Detail popup (source, PM2.5, as-of) | AirNow fire/smoke map |
| **CPU** | Live busy % | Last-hour chart + top-5 consumers | Top consumers popup | — |
| **Memory** | Used % | Top consumers popup | — | — |

### AQI: real monitors first, model second

`aqi.sh` prefers the **official AirNow monitor observation** for your location
(no API key needed) and falls back to the **Open-Meteo CAMS model** when no
monitor data exists. The forecast chart renders the 24h model curve with EPA
category bands and annotates the current official reading for comparison.

A systemd timer pre-renders the chart hourly so clicks feel instant.

### CPU chart with history

`cpu-history.service` samples total busy% every 30 s into a rolling 48 h log
(`~/.local/share/wayland-plus/cpu-history.log`). Clicking the CPU module renders
the last hour with wall-clock-aligned 10-minute ticks, avg/peak annotations, and
the current top-5 consumers drawn into the image. If `sysstat` is installed,
older `sar` data backfills the window before the local log has enough history.

### Dunst quirks handled

Some dunst/Wayland builds crop notification icons taller than ~300 px. All
charts render at ≤ 290 px height to stay safe; the CPU chart packs the
consumer list into the image itself (image-only notification, no body text).

## Install

```bash
git clone https://github.com/agilman/wayland-plus.git
cd wayland-plus
./install.sh
```

The installer backs up any configs it replaces (`*.bak-<timestamp>`), copies
everything, and enables the systemd user units. Then edit
`~/.config/wayland-plus/config.env` and set your coordinates/timezone/city —
the AQI modules refuse to run until you do (no hardcoded locations).

Dependencies (Debian/Ubuntu) — the installer prints the full list:
waybar, sway, swaybg, swayidle, swaylock, dunst, kitty, tmux, fuzzel, rofi,
grim, slurp, wl-clipboard, dex, pavucontrol, network-manager-gnome, jq, curl,
python3-matplotlib, and a Nerd Font (JetBrainsMono recommended).
Optional: sysstat (historical CPU data).

## Layout

```
config.env.example      LAT/LON/TZ/CITY template (real config.env is gitignored)
scripts/                aqi.sh, aqi-chart.py, aqi-open.sh, cpu-*, mem-*
waybar/                 config (JSONC), style.css (Catppuccin Mocha), launch.sh
sway/                   config (Alt-mod, gaps, scratchpad via kitty+tmux)
dunst/                  dunstrc
systemd/                cpu-history.service, aqi-chart.service + .timer
install.sh              idempotent-ish installer with backups
```

## Notes & assumptions

- Battery module assumes `BAT1`; edit waybar config if yours differs (some laptops expose `BAT0`).
- Random wallpaper expects images in `~/Pictures/wallpaper/`.
- The sway config is an opinionated i3 port: Alt as $mod, vim-ish focus keys,
  gaps 14, smart borders, Catppuccin window colors. Trim to taste.
- Window switcher is `rofi -show window` (XWayland); app launcher is `fuzzel`.

## Screenshots

_(coming soon)_

## License

MIT — see [LICENSE](LICENSE).
