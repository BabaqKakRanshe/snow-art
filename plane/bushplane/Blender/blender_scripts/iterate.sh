#!/bin/sh
# Пересборка геометрии и превью одной командой, без запекания карт.
#   sh iterate.sh [ракурсы] [сэмплы]
set -e
B="G:/Programms/Steam/steamapps/common/Blender/blender.exe"
S=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$S/../.." && pwd)
OUT="$ROOT/Blender/out/geo.blend"
VIEWS="${1:-hero,side,front,rear_q,top}"
SAMPLES="${2:-24}"

"$B" --background --factory-startup --python-exit-code 1 --python "$S/build.py" -- "$OUT" 2>&1 \
  | grep -vE "^Read prefs|^Blender quit|^Info: |^\s*$|DeprecationWarning|^  [a-z_]+ =" || true

"$B" --background --factory-startup --python-exit-code 1 --python "$S/render.py" -- \
  "$OUT" "$ROOT/renders/geo" "$VIEWS" "$SAMPLES" 2>&1 \
  | grep -E "^движок|^  [a-z_]+\.png|Error|Traceback|line [0-9]+" || true
