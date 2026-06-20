#!/usr/bin/env bash
# Generate the hicolor application-icon set from a single square master PNG.
#
# Save the image produced with ChatGPT as data/icon-master.png (square, >=1024px),
# then run this script. It writes data/icons/hicolor/<size>/apps/<app-id>.png for
# every size GNOME looks up. Re-run whenever the master changes.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ID="io.github.AndreaBonn.Sysbar"
MASTER="${ROOT_DIR}/data/icon-master.png"
ICONS_DIR="${ROOT_DIR}/data/icons/hicolor"
SIZES=(512 256 128 64 48)

if ! command -v convert >/dev/null 2>&1; then
    echo "ImageMagick 'convert' not found; install imagemagick" >&2
    exit 1
fi

if [ ! -f "${MASTER}" ]; then
    echo "Master image not found: ${MASTER}" >&2
    echo "Export the ChatGPT image (square, >=1024px) to that path first." >&2
    exit 1
fi

for size in "${SIZES[@]}"; do
    dest_dir="${ICONS_DIR}/${size}x${size}/apps"
    mkdir -p "${dest_dir}"
    convert "${MASTER}" -resize "${size}x${size}" "${dest_dir}/${APP_ID}.png"
    echo "Wrote ${dest_dir}/${APP_ID}.png"
done
