#!/bin/sh
# Полный прогон: геометрия -> развёртка и запекание -> превью.
#   sh pipeline.sh [размер карт] [сэмплы AO] [ракурсы]
#
# Пути выводятся из расположения самого скрипта, а не задаются абсолютно:
# пакет переносной, и после переезда каталога жёсткие пути молча указывали бы
# на старое место.
set -e
B="G:/Programms/Steam/steamapps/common/Blender/blender.exe"
S=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$S/../.." && pwd)
O="$ROOT/Blender/out"
TEX="$ROOT/tex"
SIZE="${1:-4096}"
AO="${2:-64}"
VIEWS="${3:-hero,side,front,rear_q,detail_nose}"

QUIET='^Read prefs|^Read blend|^Blender quit|^Info: |^Fra:|DeprecationWarning|^  [a-z_]+ =|HIPEW'

echo "--- геометрия ---"
"$B" --background --factory-startup --python-exit-code 1 --python "$S/build.py" -- "$O/geo.blend" 2>&1 \
  | grep -vE "$QUIET" || true

echo "--- развёртка и запекание (${SIZE}px, AO ${AO} спп) ---"
"$B" --background --factory-startup --python-exit-code 1 --python "$S/shade.py" -- \
  "$O/geo.blend" "$TEX" "$O/shaded.blend" "$SIZE" "$AO" 2>&1 \
  | grep -vE "$QUIET" || true

echo "--- превью ---"
"$B" --background --factory-startup --python-exit-code 1 --python "$S/render.py" -- \
  "$O/shaded.blend" "$ROOT/renders/final" "$VIEWS" 64 2>&1 \
  | grep -E "^движок|^  [a-z_]+\.png|Error|Traceback" || true
