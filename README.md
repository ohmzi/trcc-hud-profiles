# TRCC HUD profiles

Two things TRCC Linux doesn't do on its own, for Thermalright AIO panels
(developed against a GrandVision 360 / Levita Vision, 1600×720, USB `87ad:70db`):

* **Profiles that travel** — a saved theme carries its layout, but not its mask
  and not the colour palette. `trcc-profile` switches all three together.
* **Colour that reacts** — an overlay element has one fixed colour. A small
  timer recolours CPU/GPU readouts as they cross thresholds.

```
CPU 49°C 10%                                    00:25
                                             2026/10/28
                                                WED
GPU 60°C  4%
```

## What's here

| Path | What it does |
|---|---|
| `bin/trcc-profile` | Loads a profile, applies its mask, sets its palette |
| `bin/trcc-colorwatch.py` | Reads sensors, recolours metrics by band (only on change) |
| `profiles/profiles.conf` | The profile list: `name\|base\|warn\|hot\|mask` |
| `profiles/*.json` | Overlay layouts (9 elements: CPU/GPU temp+usage, clock, date, weekday) |
| `masks/ghibli-scrim.png` | A soft scrim so dark text stays readable over art |
| `masks/black.png` | A plain black canvas |
| `systemd/` | User timer that runs the colour watcher every 20 s |
| `install.sh` | Installs the above; never overwrites an existing theme dir |

## Install

```bash
git clone https://github.com/<you>/trcc-hud-profiles
cd trcc-hud-profiles
./install.sh
```

Requires TRCC Linux installed and a panel attached once (so its theme root
exists). `install.sh` never deletes: an existing profile directory — and the
background you put in it — is left alone. `--force` rewrites the shipped files.

## Profiles

```bash
trcc-profile --list
trcc-profile "Studio Gib"
trcc-profile "Black HUD"
```

| Profile | Background | Text | Escalation |
|---|---|---|---|
| Studio Gib | your animated scene | black clock, dark-green metrics | green → amber → red |
| Black HUD | black canvas | white | white → amber → red |

Both use the same layout and the same thresholds:

| Metric | Amber at | Red at |
|---|---|---|
| CPU temperature | 60 °C | 80 °C |
| CPU usage | 50 % | 85 % |
| GPU temperature | 65 °C | 80 °C |
| GPU usage | 50 % | 85 % |

Override in `~/.config/trcc-hud/colorwatch.json`:

```json
{
  "device": "87ad:70db",
  "bands": {"cpu:temp": [65, 85], "gpu:primary:temp": [70, 82]}
}
```

## Backgrounds

The animated scene backgrounds are **Thermalright's artwork**, downloaded by
TRCC from its own catalogue — they are deliberately **not** in this repo. Pick
a theme in TRCC's gallery, then copy the staged file into the profile:

```bash
cp ~/.trcc/data/web/1600720/<theme-id>.mp4 "$HOME/.trcc-user/data/theme1600720/Studio Gib/Theme.mp4"
trcc-profile "Studio Gib"
```

`Black HUD` needs nothing: it ships a black `00.png`.

## Things that bit me (and why the scripts look like this)

1. **`trcc theme save` writes a static PNG and drops the video.** A saved
   animated theme comes back frozen; put `Theme.mp4` back into the directory.
   It also records whatever background/mask reference was active at the time —
   a gallery theme you browsed earlier can end up embedded in your profile.
2. **A theme's in-dir `01.png` is not adopted as the device mask on load.**
   `trcc-profile` applies it explicitly.
3. **Loading any theme wipes the overlay layer.** Element ids are re-minted,
   which is why the watcher resolves ids by metric name rather than caching
   them forever.
4. **The metric id is a sensor id, not a field name.** `cpu:temp` works;
   `cpu_temp` is accepted and then silently never draws.

## Uninstall

```bash
systemctl --user disable --now trcc-colorwatch.timer
rm -f ~/.local/bin/trcc-profile ~/.local/bin/trcc-colorwatch.py
rm -rf ~/.config/trcc-hud ~/.local/share/trcc-hud
```

## Licence

MIT — see `LICENSE`. Not affiliated with Thermalright or the TRCC Linux
project; this is a small add-on that drives an already-installed TRCC.
