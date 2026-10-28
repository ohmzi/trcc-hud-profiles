#!/usr/bin/env python3
"""Recolour TRCC overlay metrics by threshold.

TRCC stores ONE fixed colour per overlay element, so severity colouring has to
come from outside: this reads the same sensors the panel does and rewrites the
colour only when a metric crosses a band. That keeps the trcc CLI calls to a
handful an hour instead of one per tick.

Element ids change whenever the overlay is rebuilt (loading a theme wipes the
working layer), so they are resolved from `overlay-list` and cached; a failed
update means the cache is stale and the next run re-resolves.

Config: ~/.config/trcc-hud/colorwatch.json (all keys optional)

    {
      "device":   "87ad:70db",              # default: the first attached panel
      "palette":  "~/.config/trcc-hud/palette.json",
      "bands":    {"cpu:temp": [60, 80]},   # [amber_at, red_at] per metric
      "trcc":     "/usr/bin/trcc"
    }
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

CONFIG = Path.home() / ".config/trcc-hud/colorwatch.json"
STATE = Path.home() / ".trcc/colorwatch.json"
HWMON = Path("/sys/class/hwmon")

DEFAULT_BANDS = {
    "cpu:temp": (60, 80),
    "cpu:usage": (50, 85),
    "gpu:primary:temp": (65, 80),
    "gpu:primary:usage": (50, 85),
}
DEFAULT_PALETTE = {"base": "#15803d", "warn": "#b45309", "hot": "#b91c1c"}


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def config() -> dict:
    return load_json(CONFIG)


def device_key(cfg: dict, trcc: str) -> str | None:
    """The panel to drive: configured, else the first `trcc detect` reports."""
    if cfg.get("device"):
        return str(cfg["device"])
    try:
        out = subprocess.run([trcc, "detect"], capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return None
    m = re.search(r"\b([0-9a-f]{4}:[0-9a-f]{4})\b", out)
    return m.group(1) if m else None


def palette(cfg: dict) -> dict:
    path = Path(cfg.get("palette") or Path.home() / ".config/trcc-hud/palette.json").expanduser()
    p = {**DEFAULT_PALETTE, **load_json(path)}
    return {k: str(p[k]) for k in DEFAULT_PALETTE}


def bands(cfg: dict) -> dict[str, tuple[int, int]]:
    out = dict(DEFAULT_BANDS)
    for metric, pair in (cfg.get("bands") or {}).items():
        try:
            out[str(metric)] = (int(pair[0]), int(pair[1]))
        except (TypeError, ValueError, IndexError):
            pass
    return out


def cpu_temp() -> float | None:
    for d in HWMON.glob("hwmon*"):
        try:
            if d.joinpath("name").read_text().strip() != "coretemp":
                continue
        except OSError:
            continue
        for lp in d.glob("temp*_label"):
            try:
                if lp.read_text().strip() == "Package id 0":
                    return float(lp.with_name(lp.name.replace("_label", "_input")).read_text()) / 1000
            except (OSError, ValueError):
                pass
    return None


def cpu_usage(prev: dict) -> float | None:
    """CPU busy % since the previous run; needs the state file to hold a delta."""
    try:
        vals = list(map(int, Path("/proc/stat").read_text().splitlines()[0].split()[1:9]))
    except Exception:
        return None
    idle, total = vals[3] + vals[4], sum(vals)
    out = None
    pt, pi = prev.get("cpu_total"), prev.get("cpu_idle")
    if pt is not None and total > pt:
        out = 100.0 * (1 - (idle - pi) / (total - pt))
    prev["cpu_total"], prev["cpu_idle"] = total, idle
    return out


def gpu() -> tuple[float | None, float | None]:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=6).stdout.strip().splitlines()[0]
        t, u = (float(x) for x in out.split(","))
        return t, u
    except Exception:
        return None, None


def band(value: float | None, lo: int, hi: int, pal: dict) -> str:
    if value is None:
        return pal["base"]
    return pal["base"] if value < lo else pal["warn"] if value < hi else pal["hot"]


def resolve_ids(trcc: str, key: str, wanted: dict) -> dict[str, str]:
    out = subprocess.run([trcc, "display", "overlay-list", key],
                         capture_output=True, text=True, timeout=25).stdout
    ids = {}
    for line in out.splitlines():
        m = re.search(r"(el_\w+)\s+metric\s+\([^)]*\)\s+(\S+)", line)
        if m and m.group(2) in wanted:
            ids[m.group(2)] = m.group(1)
    return ids


def main() -> int:
    cfg = config()
    trcc = str(cfg.get("trcc") or "/usr/bin/trcc")
    key = device_key(cfg, trcc)
    if not key:
        print("no panel found (is trccd running and the cooler attached?)")
        return 0
    pal, bands_ = palette(cfg), bands(cfg)

    prev = load_json(STATE)
    ids = prev.get("ids") or resolve_ids(trcc, key, bands_)
    seen = dict(prev.get("colors") or {})

    gt, gu = gpu()
    values = {"cpu:temp": cpu_temp(), "cpu:usage": cpu_usage(prev),
              "gpu:primary:temp": gt, "gpu:primary:usage": gu}

    changed = 0
    for metric, (lo, hi) in bands_.items():
        if metric not in values:
            continue
        colour = band(values[metric], lo, hi, pal)
        elem = ids.get(metric)
        if not elem or seen.get(metric) == colour:
            continue
        r = subprocess.run([trcc, "display", "overlay-update", key, elem, "--color", colour],
                           capture_output=True, text=True, timeout=25)
        if r.returncode == 0:
            seen[metric] = colour
            changed += 1
        else:
            ids = {}                      # stale cache: re-resolve next run

    prev["ids"], prev["colors"] = ids, seen
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(prev))
    print(f"{values} -> {seen} ({changed} changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
