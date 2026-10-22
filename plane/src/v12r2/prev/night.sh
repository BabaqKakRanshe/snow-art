#!/bin/bash
# night.sh <variant> <views...>: 720p passes + URP twin night (panel light, red flood, domes) for the variant textures
V=$1; shift
for v in "$@"; do
  python3 - "$v" "$V" <<'PY'
import json, sys
v, V = sys.argv[1], sys.argv[2]
c = json.load(open('/home/claude/plane/v12/prev/r/cfg_%s_v12_720.json' % v))
c['out'] = '/home/claude/plane/v12r2/prev/r/%s_%s_720' % (v, V)
c['tex'] = '/home/claude/plane/v12r2/work/tex_prev%s' % V
json.dump(c, open('/home/claude/plane/v12r2/prev/r/cfg_%s_%s_720.json' % (v, V), 'w'), indent=1)
PY
  (cd /home/claude/plane/v12/prev && python3 cy12.py /home/claude/plane/v12r2/prev/r/cfg_${v}_${V}_720.json > /home/claude/plane/v12r2/prev/r/log_${v}_${V}_720.txt 2>&1)
  (cd /home/claude/plane/v11/prev && python3 urp_emulate.py /home/claude/plane/v12r2/prev/r/${v}_${V}_720 v11 /home/claude/plane/v12r2/prev/r/${v}_${V}_720_night.png '{"downsample":1}' 2>&1 | tail -1)
done
echo NIGHTDONE
