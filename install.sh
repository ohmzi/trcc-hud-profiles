#!/bin/bash
# Install the TRCC HUD profiles: scripts, profile list, theme skeletons and the
# colour-watcher timer.
#
# Nothing is overwritten that already exists — an existing profile's theme
# directory (and the background video you put in it) is left alone. Pass
# --force to rewrite the shipped files.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

TRCC="${TRCC_BIN:-/usr/bin/trcc}"
command -v "$TRCC" >/dev/null || { echo "trcc not found at $TRCC — install TRCC Linux first"; exit 1; }

BIN="$HOME/.local/bin"
CONF="$HOME/.config/trcc-hud"
SHARE="$HOME/.local/share/trcc-hud"
UNITS="$HOME/.config/systemd/user"
ROOT="${TRCC_THEME_ROOT:-$(ls -d "$HOME"/.trcc-user/data/theme* 2>/dev/null | head -1)}"
[ -n "$ROOT" ] || { echo "no theme root under ~/.trcc-user/data — run TRCC once with the panel attached"; exit 1; }

echo "==> scripts -> $BIN"
mkdir -p "$BIN"
install -m 755 "$HERE/bin/trcc-colorwatch.py" "$BIN/trcc-colorwatch.py"
install -m 755 "$HERE/bin/trcc-profile" "$BIN/trcc-profile"

echo "==> masks -> $SHARE/masks"
mkdir -p "$SHARE/masks"
for m in ghibli-scrim.png black.png; do
    [ -f "$SHARE/masks/$m" ] && [ "$FORCE" -eq 0 ] || cp "$HERE/masks/$m" "$SHARE/masks/$m"
done

echo "==> profile list -> $CONF/profiles.conf"
mkdir -p "$CONF"
if [ ! -f "$CONF/profiles.conf" ] || [ "$FORCE" -eq 1 ]; then
    sed "s#\.\./masks/#$SHARE/masks/#g" "$HERE/profiles/profiles.conf" > "$CONF/profiles.conf"
fi

echo "==> theme skeletons -> $ROOT"
make_theme() {                       # name  config.json  mask-file-or-empty  bg-file-or-empty
    local dir="$ROOT/$1"
    mkdir -p "$dir"
    if [ ! -f "$dir/trcc.json" ] || [ "$FORCE" -eq 1 ]; then
        cp "$HERE/profiles/$2" "$dir/trcc.json"
    fi
    [ -n "$3" ] && { [ -f "$dir/01.png" ] || cp "$SHARE/masks/$3" "$dir/01.png"; }
    [ -n "$4" ] && { [ -f "$dir/00.png" ] || cp "$SHARE/masks/$4" "$dir/00.png"; }
    echo "    $dir"
}
make_theme "Studio Gib" studio-gib.json ghibli-scrim.png ""
make_theme "Black HUD"  black-hud.json  ""               black.png

echo "==> timer -> $UNITS"
mkdir -p "$UNITS"
for u in trcc-colorwatch.service trcc-colorwatch.timer; do
    [ -f "$UNITS/$u" ] && [ "$FORCE" -eq 0 ] || cp "$HERE/systemd/$u" "$UNITS/$u"
done
systemctl --user daemon-reload
systemctl --user enable --now trcc-colorwatch.timer

cat <<EOF

Installed. Next:

  1. Put a background in each profile — the artwork is Thermalright's, so it
     is not shipped here. In TRCC's gallery pick a theme, which stages the
     file under ~/.trcc/data/web/<res>/, then copy it into the profile:
       cp ~/.trcc/data/web/<res>/<id>.mp4 "$ROOT/Studio Gib/Theme.mp4"
     (Black HUD already has 00.png, a plain black canvas.)

  2. Switch profiles:
       ~/.local/bin/trcc-profile --list
       ~/.local/bin/trcc-profile "Black HUD"

  3. Colours escalate at: CPU 60/80 C, GPU 65/80 C, usage 50/85 %.
     Adjust in ~/.config/trcc-hud/colorwatch.json.
EOF
