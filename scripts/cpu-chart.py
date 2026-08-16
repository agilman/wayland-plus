#!/usr/bin/env python3
"""CPU usage chart (last hour from local sampler log) + top consumers
-> dunst image notification. Falls back to sar if the log is too fresh.

Note: image must stay <= ~300px tall — dunst on this setup crops taller
icons (probed 2026-08-16: 300px ok, 340px cropped top+bottom).
"""
import datetime
import os
import re
import subprocess

_DATA = os.path.join(os.environ.get("XDG_DATA_HOME",
                                     os.path.expanduser("~/.local/share")),
                     "wayland-plus")
OUT = f"/tmp/wayland-plus-cpu-chart-{os.environ.get('USER', 'user')}.png"
LOG = os.path.join(_DATA, "cpu-history.log")

def read_log():
    pts = []
    if os.path.exists(LOG):
        for line in open(LOG):
            parts = line.split()
            if len(parts) == 2:
                try:
                    pts.append((datetime.datetime.fromtimestamp(int(parts[0])),
                                float(parts[1])))
                except ValueError:
                    pass
    return sorted(pts)

def read_sar_backfill():
    """Old sar data, if sysstat was ever enabled."""
    pts = []
    rx = re.compile(r"^(\d{2}:\d{2}:\d{2})\s+(?:AM|PM)?\s*all\s+[\d.]+\s+[\d.]+\s+"
                    r"[\d.]+\s+[\d.]+\s+[\d.]+\s+([\d.]+)")
    for f in sorted(os.listdir("/var/log/sysstat")) if os.path.isdir("/var/log/sysstat") else []:
        try:
            out = subprocess.run(["sar", "-u", "-f", f"/var/log/sysstat/{f}"],
                                 capture_output=True, text=True,
                                 env={**os.environ, "LC_ALL": "C"}, timeout=10).stdout
        except Exception:
            continue
        hdr = [l for l in out.splitlines() if l.startswith("Linux")]
        if not hdr:
            continue
        m = re.search(r"(\d{2})/(\d{2})/(\d{2})", hdr[0])
        if not m:
            continue
        mo, day, yr = int(m.group(1)), int(m.group(2)), 2000 + int(m.group(3))
        for line in out.splitlines():
            mm = rx.match(line)
            if mm:
                t = datetime.datetime.strptime(mm.group(1), "%H:%M:%S")
                try:
                    pts.append((t.replace(year=yr, month=mo, day=day),
                                100.0 - float(mm.group(2))))
                except ValueError:
                    pass
    return sorted(pts)

def top_consumers(n=5):
    try:
        out = subprocess.run(["ps", "-eo", "pcpu,comm", "--sort=-pcpu"],
                             capture_output=True, text=True, timeout=5).stdout
        rows = []
        for line in out.splitlines()[1:]:
            parts = line.split(None, 1)
            if len(parts) == 2:
                try:
                    rows.append((float(parts[0]), parts[1].strip()))
                except ValueError:
                    pass
            if len(rows) == n:
                break
        return rows
    except Exception:
        return []

def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(hours=1)
    pts = [p for p in read_log() if p[0] >= cutoff]
    note = ""
    if len(pts) < 10:
        sar = [p for p in read_sar_backfill() if p[0] >= cutoff]
        if len(sar) > len(pts):
            pts = sar
        if pts:
            note = f"  (logging since {pts[0].strftime('%H:%M')})"

    if len(pts) < 2:
        subprocess.run(["notify-send", "-t", "10000", "CPU usage",
                        "History logging just started — check back in a bit."])
        return

    times = [p[0] for p in pts]
    busy = [p[1] for p in pts]
    hours = [(t - times[0]).total_seconds() / 3600 for t in times]

    top = top_consumers()

    fig = plt.figure(figsize=(3.6, 2.9), dpi=100)   # 360x290, under dunst's ~300px cap
    fig.patch.set_facecolor("#1e1e2e")
    ax = fig.add_axes([0.13, 0.44, 0.83, 0.44])
    ax.set_facecolor("#181825")

    ax.fill_between(hours, busy, color="#94e2d5", alpha=0.22)
    ax.plot(hours, busy, color="#94e2d5", lw=1.6)
    ax.axhline(85, color="#f38ba8", lw=0.7, ls="--", alpha=0.6)

    # 10-minute ticks aligned to the wall clock
    t0 = times[0].replace(second=0, microsecond=0)
    t0 += datetime.timedelta(minutes=10 - t0.minute % 10)
    ticks = []
    t = t0
    while t <= times[-1]:
        ticks.append((t - times[0]).total_seconds() / 3600)
        t += datetime.timedelta(minutes=10)
    ax.set_xticks(ticks)
    ax.set_xticklabels([(times[0] + datetime.timedelta(hours=h)).strftime("%H:%M")
                        for h in ticks], color="#a6adc8", fontsize=7)
    ax.tick_params(colors="#a6adc8", labelsize=7)
    for s in ax.spines.values():
        s.set_color("#313244")
    ax.grid(axis="y", color="#313244", lw=0.4)
    ax.set_ylim(0, max(100, max(busy) * 1.15))
    ax.set_xlim(0, max(hours[-1], 0.01))

    avg = sum(busy) / len(busy)
    peak_i = busy.index(max(busy))
    ax.set_title(f"CPU — last hour{note}  ·  avg {avg:.0f}%  now {busy[-1]:.0f}%",
                 color="#cdd6f4", fontsize=9, loc="left")
    ax.annotate(f"peak {busy[peak_i]:.0f}%",
                xy=(hours[peak_i], busy[peak_i]), xytext=(4, 6),
                textcoords="offset points", color="#f9e2af", fontsize=7)

    fig.text(0.05, 0.345, "Top consumers", color="#cdd6f4",
             fontsize=8, weight="bold")
    y = 0.275
    for pct, name in top:
        fig.text(0.05, y, f"{pct:5.1f}%  {name}", color="#a6adc8",
                 fontsize=8, family="monospace")
        y -= 0.055

    fig.savefig(OUT, facecolor=fig.get_facecolor())

    subprocess.run(["notify-send", "-a", "cpu-chart", "-t", "20000", "-i", OUT,
                    " ", " "])

if __name__ == "__main__":
    main()
