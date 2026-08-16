#!/usr/bin/env python3
"""24h rain forecast chart -> dunst image notification.
Fetches hourly precipitation/probability/temperature from Open-Meteo,
renders Catppuccin-styled PNG (<=290px tall, dunst-safe).
Config: ~/.config/wayland-plus/config.env (LAT/LON/TZ/CITY).

Modes:
  --render   fetch + render cache PNG, no notification
  (default)  show cached PNG if fresh (<15 min); else render first, then show.
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
CITY = _cfg.get("CITY", "")
UNITS = _cfg.get("UNITS", "metric")
if not LAT or not LON or LAT == "0.0":
    raise SystemExit(f"wayland-plus: set LAT/LON in {CONFIG}")

if UNITS == "imperial":
    _UP = "&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch"
    TU, RU = "°F", "in"
else:
    _UP = ""
    TU, RU = "°C", "mm"

URL = ("https://api.open-meteo.com/v1/forecast"
       f"?latitude={LAT}&longitude={LON}"
       "&hourly=temperature_2m,precipitation_probability,precipitation"
       "&daily=precipitation_sum,precipitation_probability_max,"
       "temperature_2m_max,temperature_2m_min"
       f"&forecast_hours=24&timezone=auto{_UP}")
OUT = f"/tmp/wayland-plus-weather-chart-{os.environ.get('USER', 'user')}.png"
MAX_AGE = 15 * 60

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
    times = [datetime.datetime.fromisoformat(t) for t in h["time"]]
    temp = h["temperature_2m"]
    prob = h["precipitation_probability"]
    rain = h["precipitation"]
    dy = d["daily"]

    fig = plt.figure(figsize=(3.6, 2.9), dpi=100)   # 360x290, dunst-safe
    fig.patch.set_facecolor("#1e1e2e")
    ax = fig.add_axes([0.12, 0.16, 0.76, 0.66])
    ax.set_facecolor("#181825")

    x = list(range(len(rain)))
    # rain bars
    ax.bar(x, [r or 0 for r in rain], color="#89b4fa", alpha=0.85, width=0.8)
    ax.set_ylabel(RU, color="#89b4fa", fontsize=7)
    ax.set_ylim(0, max(1.5 if UNITS != "imperial" else 0.1,
                       max((r or 0) for r in rain) * 1.3))
    ax.tick_params(axis="y", colors="#89b4fa", labelsize=6)

    # probability + temperature on secondary axis
    ax2 = ax.twinx()
    ax2.plot(x, [p or 0 for p in prob], color="#74c7ec", lw=1.2, ls="--")
    ax2.plot(x, temp, color="#fab387", lw=1.6)
    ax2.set_ylim(0, max(100, max(temp) * 1.2))
    ax2.tick_params(axis="y", colors="#a6adc8", labelsize=6)
    ax2.set_ylabel(f"% / {TU}", color="#a6adc8", fontsize=7)

    step = max(1, len(times) // 6)
    ax.set_xticks(range(0, len(times), step))
    ax.set_xticklabels([times[i].strftime("%H:%M") for i in range(0, len(times), step)],
                       color="#a6adc8", fontsize=7)
    ax.tick_params(axis="x", colors="#a6adc8", labelsize=7)
    for s in list(ax.spines.values()) + list(ax2.spines.values()):
        s.set_color("#313244")
    ax.grid(axis="y", color="#313244", lw=0.4)
    ax.set_xlim(-0.5, len(times) - 0.5)

    total = sum(r or 0 for r in rain)
    peak_i = max(range(len(rain)), key=lambda i: rain[i] or 0)
    city = f" — {CITY}" if CITY else ""
    ax.set_title(f"Rain{city} — next {len(rain)} h  ·  total {total:.2f} {RU}",
                 color="#cdd6f4", fontsize=9, loc="left")
    if (rain[peak_i] or 0) > 0:
        ax.annotate(f"{rain[peak_i]:.2f} {RU}",
                    xy=(peak_i, rain[peak_i]), xytext=(4, 4),
                    textcoords="offset points", color="#89b4fa", fontsize=7)

    fig.text(0.12, 0.045,
             f"prob max {dy['precipitation_probability_max'][0]}%  ·  "
             f"{dy['temperature_2m_min'][0]:.0f}–{dy['temperature_2m_max'][0]:.0f} {TU}  ·  "
             f"bars: rain {RU} · dashed: prob % · orange: temp",
             color="#a6adc8", fontsize=6)

    fig.savefig(OUT, facecolor=fig.get_facecolor())

    return (f"Next 24h: {total:.2f} {RU} rain · "
            f"peak {rain[peak_i] or 0:.2f} {RU} at {times[peak_i].strftime('%H:%M')}\n"
            f"Prob max {dy['precipitation_probability_max'][0]}% · "
            f"{dy['temperature_2m_min'][0]:.0f}–{dy['temperature_2m_max'][0]:.0f} {TU}")

def show():
    subprocess.run(["notify-send", "-a", "weather-chart", "-t", "20000", "-i", OUT,
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
