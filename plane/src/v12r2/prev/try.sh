#!/bin/bash
# try.sh <variant> <params.json or -> <atlas spec> <views...>: textures -> preview folder -> passes -> flat emulation
V=$1; PJ=$2; SPEC=$3; shift 3
W=/home/claude/plane/v12r2/work
cd /home/claude/plane/v12r2/tex
if [ "$PJ" = "-" ]; then python3 psx_interior2.py $W/psx$V $SPEC | tail -6; else python3 psx_interior2.py $W/psx$V $SPEC $PJ | tail -6; fi
rm -rf $W/tex_prev$V; cp -r /home/claude/plane/v12/work/tex_preview_v12 $W/tex_prev$V; cp $W/psx$V/T_*.png $W/tex_prev$V/
J='{"downsample":1,"ambient":0.5,"moon":0.0,"atmosphere":0.0,"fog_density":0.0,"levels":{"nav":0,"beacon":0,"landing":0,"cabin":0,"cargo":0,"flood":0,"strobe":0}}'
for v in "$@"; do
  python3 - "$v" "$V" <<'PY'
import json, sys
v, V = sys.argv[1], sys.argv[2]
base = '/home/claude/plane/v12/prev/r/cfg_%s_v12.json' % v
c = json.load(open(base))
c['out'] = '/home/claude/plane/v12r2/prev/r/%s_%s' % (v, V)
c['tex'] = '/home/claude/plane/v12r2/work/tex_prev%s' % V
json.dump(c, open('/home/claude/plane/v12r2/prev/r/cfg_%s_%s.json' % (v, V), 'w'), indent=1)
PY
  (cd /home/claude/plane/v12/prev && python3 cy12.py /home/claude/plane/v12r2/prev/r/cfg_${v}_$V.json > /home/claude/plane/v12r2/prev/r/log_${v}_$V.txt 2>&1)
  (cd /home/claude/plane/v11/prev && python3 urp_emulate.py /home/claude/plane/v12r2/prev/r/${v}_$V v11 /home/claude/plane/v12r2/prev/r/${v}_${V}_flat.png "$J" 2>&1 | tail -1)
done
echo TRYDONE
