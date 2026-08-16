#!/usr/bin/env python3
"""24h rain + temperature forecast chart -> dunst image notification.

Architecture (fast clicks):
  --render   fetch forecast -> JSON cache + base PNG (used by systemd timer)
  (default)  overlay a "now" line on the cached base PNG via PIL (~0.2s),
             then show. Only falls back to a full fetch+render if the
             cache is stale (>3h) or missing.

Base PNG has fixed geometry (360x290, ax rect [0.12, 0.16, 0.76, 0.66]),
so the time->pixel mapping for the "now" line is exact.
Config: ~/.config/wayland-plus/config.env (LAT/LON/TZ/CITY/UNITS).
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
USER = os.environ.get("USER", "user")
JSON_CACHE = f"/tmp/wayland-plus-weather-forecast-{USER}.json"
BASE_PNG = f"/tmp/wayland-plus-weather-chart-base-{USER}.png"
OUT = f"/tmp/wayland-plus-weather-chart-{USER}.png"
MAX_AGE = 3 * 3600  # base cache considered stale after 3 hours

# plot area geometry (must match fig.add_axes below): figsize 3.6x2.9 @100dpi
AX_X0, AX_W = 0.12 * 360, 0.76 * 360
AX_Y0, AX_Y1 = (1 - (0.16 + 0.66)) * 290, (1 - 0.16) * 290

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

def fetch():
    with urllib.request.urlopen(URL, timeout=15) as r:
        d = json.load(r)
    json.dump(d, open(JSON_CACHE, "w"))
    return d

def load_cached():
    if os.path.exists(JSON_CACHE) and os.path.exists(BASE_PNG):
        if time.time() - os.path.getmtime(BASE_PNG) < MAX_AGE:
            try:
                return json.load(open(JSON_CACHE))
            except (OSError, ValueError):
                pass
    return None

def render_base(d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

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
    ax.bar(x, [r or 0 for r in rain], color="#89b4fa", alpha=0.85, width=0.8)
    ax.set_ylabel(RU, color="#89b4fa", fontsize=7)
    ax.set_ylim(0, max(1.5 if UNITS != "imperial" else 0.1,
                       max((r or 0) for r in rain) * 1.3))
    ax.tick_params(axis="y", colors="#89b4fa", labelsize=6)

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

    fig.savefig(BASE_PNG, facecolor=fig.get_facecolor())

def overlay_now(d):
    """Copy base PNG and draw a vertical 'now' line at the current time."""
    from PIL import Image, ImageDraw
    times = [datetime.datetime.fromisoformat(t) for t in d["hourly"]["time"]]
    now = datetime.datetime.now()
    n = len(times)
    # fractional index of 'now' (hourly slots, times[0] = forecast start)
    fi = (now - times[0]).total_seconds() / 3600
    frac = (fi + 0.5) / n                     # xlim is (-0.5, n-0.5)
    frac = max(0.0, min(1.0, frac))
    x = AX_X0 + frac * AX_W

    img = Image.open(BASE_PNG).convert("RGB")
    dr = ImageDraw.Draw(img)
    dr.line([(x, AX_Y0), (x, AX_Y1)], fill="#f38ba8", width=2)
    img.save(OUT)

def show(d):
    h, dy = d["hourly"], d["daily"]
    rain = h["precipitation"]
    times = [datetime.datetime.fromisoformat(t) for t in h["time"]]
    total = sum(r or 0 for r in rain)
    peak_i = max(range(len(rain)), key=lambda i: rain[i] or 0)
    body = (f"Next 24h: {total:.2f} {RU} rain · "
            f"peak {rain[peak_i] or 0:.2f} {RU} at {times[peak_i].strftime('%H:%M')}\n"
            f"Prob max {dy['precipitation_probability_max'][0]}% · "
            f"{dy['temperature_2m_min'][0]:.0f}–{dy['temperature_2m_max'][0]:.0f} {TU}")
    subprocess.run(["notify-send", "-a", "weather-chart", "-t", "20000",
                    "-i", OUT, "Weather — next 24 h", body])

def main():
    if "--render" in sys.argv:
        render_base(fetch())
        return
    d = load_cached()
    if d is None:
        d = fetch()
        render_base(d)
    overlay_now(d)
    show(d)

if __name__ == "__main__":
    main()
