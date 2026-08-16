#!/usr/bin/env python3
"""AQI forecast chart -> dunst image notification.
Fetches 24h hourly US AQI + PM2.5 from Open-Meteo, renders Catppuccin-styled PNG.
Config: ~/.config/wayland-plus/config.env (LAT/LON/TZ/CITY).

Modes:
  --render   fetch + render cache PNG, no notification (used by systemd timer)
  (default)  show cached PNG if fresh (<75 min); else render first, then show.
"""
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.request

CONFIG = os.path.join(os.environ.get("XDG_CONFIG_HOME",
                                      os.path.expanduser("~/.config")),
                      "wayland-plus", "config.env")

def load_config():
    cfg = {}
    try:
        for line in open(CONFIG):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    except OSError:
        pass
    return cfg

_cfg = load_config()
LAT, LON = _cfg.get("LAT"), _cfg.get("LON")
TZ = _cfg.get("TZ", "UTC")
CITY = _cfg.get("CITY", "")
if not LAT or not LON or LAT == "0.0":
    raise SystemExit(f"wayland-plus: set LAT/LON in {CONFIG}")

URL = ("https://air-quality-api.open-meteo.com/v1/air-quality"
       f"?latitude={LAT}&longitude={LON}"
       f"&hourly=us_aqi,pm2_5&forecast_hours=24&timezone={TZ}")
OUT = f"/tmp/wayland-plus-aqi-chart-{os.environ.get('USER', 'user')}.png"
MAX_AGE = 75 * 60  # seconds before the cache is considered stale

# (lo, hi, catppuccin color, label)
CATS = [(0, 50, "#a6e3a1", "Good"),
        (50, 100, "#f9e2af", "Moderate"),
        (100, 150, "#fab387", "Unhealthy (sensitive)"),
        (150, 200, "#f38ba8", "Unhealthy"),
        (200, 301, "#cba6f7", "Very Unhealthy"),
        (300, 501, "#f38ba8", "Hazardous")]

def label_for(aqi):
    for lo, hi, _, lab in CATS:
        if lo <= aqi < hi or (aqi >= hi and hi == 501):
            return lab
    return "?"

def airnow_now():
    """Official monitor observation, if available (contrasts model values)."""
    try:
        with urllib.request.urlopen(
                "https://airnowgovapi.com/reportingarea/get"
                f"?latitude={LAT}&longitude={LON}", timeout=10) as r:
            obs = [o for o in json.load(r)
                   if o.get("dataType") == "O" and isinstance(o.get("aqi"), int)]
        if obs:
            o = max(obs, key=lambda o: o["issueDate"] + " " + o["time"])
            return o["aqi"], o["category"]
    except Exception:
        pass
    return None, None

def cache_fresh():
    try:
        return (time.time() - os.path.getmtime(OUT)) < MAX_AGE
    except OSError:
        return False

def render():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with urllib.request.urlopen(URL, timeout=15) as r:
        d = json.load(r)
    h = d["hourly"]
    rows = [(datetime.datetime.fromisoformat(t), a, p)
            for t, a, p in zip(h["time"], h["us_aqi"], h["pm2_5"])
            if a is not None]
    if not rows:
        raise SystemExit("no data")
    times = [r[0] for r in rows]
    aqi = [r[1] for r in rows]
    pm = [r[2] for r in rows if r[2] is not None]

    fig, ax = plt.subplots(figsize=(3.6, 2.4), dpi=100)
    fig.patch.set_facecolor("#1e1e2e")
    ax.set_facecolor("#181825")

    for lo, hi, c, _ in CATS:
        ax.axhspan(lo, min(hi, 500), color=c, alpha=0.07)

    x = list(range(len(aqi)))
    ax.fill_between(x, aqi, color="#89b4fa", alpha=0.22)
    ax.plot(x, aqi, color="#89b4fa", lw=2)
    ax.scatter([0], [aqi[0]], color="#cdd6f4", s=16, zorder=5)

    step = max(1, len(times) // 6)
    ax.set_xticks(range(0, len(times), step))
    ax.set_xticklabels([times[i].strftime("%H:%M") for i in range(0, len(times), step)],
                       color="#a6adc8", fontsize=7)
    ax.tick_params(colors="#a6adc8", labelsize=7)
    for s in ax.spines.values():
        s.set_color("#313244")
    ax.grid(axis="y", color="#313244", lw=0.4)
    ax.set_ylim(0, max(60, max(aqi) * 1.25))
    ax.set_xlim(0, len(times) - 1)

    peak_i = aqi.index(max(aqi))
    ax.set_title(f"AQI forecast — next {len(aqi)} h  ·  model   (now {aqi[0]})",
                 color="#cdd6f4", fontsize=9, loc="left")
    ax.annotate(f"peak {aqi[peak_i]} @ {times[peak_i].strftime('%H:%M')}",
                xy=(peak_i, aqi[peak_i]), xytext=(4, 6),
                textcoords="offset points", color="#f9e2af", fontsize=7)

    mon_aqi, mon_cat = airnow_now()
    if mon_aqi is not None:
        fig.text(0.04, 0.015, f"AirNow monitor now: {mon_aqi} ({mon_cat})",
                 color="#a6e3a1" if mon_aqi <= 50 else "#f9e2af", fontsize=7)

    fig.tight_layout(pad=0.6, rect=(0, 0.05, 1, 1))
    fig.savefig(OUT, facecolor=fig.get_facecolor())

    body = (f"Now {aqi[0]} ({label_for(aqi[0])}) · "
            f"peak {max(aqi)} at {times[peak_i].strftime('%H:%M')}\n"
            f"PM2.5 now: {pm[0] if pm else '?'} µg/m³ · model forecast")
    if mon_aqi is not None:
        body += f"\nAirNow monitor now: {mon_aqi} ({mon_cat})"
    return body

def show():
    subprocess.run(["notify-send", "-a", "aqi-chart", "-t", "20000", "-i", OUT,
                    " ", " "])

def main():
    if "--render" in sys.argv:
        render()
        return
    if not cache_fresh():
        render()
    show()

if __name__ == "__main__":
    main()
