#!/bin/bash
# usage: emul_list.sh "view:mode" ...   mode = night | flat
cd /home/claude/plane/v11/prev
for vm in "$@"; do
  v=${vm%%:*}; m=${vm##*:}
  if [ "$m" = night ]; then J='{"downsample":1}'; else J='{"downsample":1,"ambient":0.5,"moon":0.0,"atmosphere":0.0,"fog_density":0.0,"levels":{"nav":0,"beacon":0,"landing":0,"cabin":0,"cargo":0,"flood":0,"strobe":0}}'; fi
  python3 urp_emulate.py /home/claude/plane/v12/prev/r/$v v11 /home/claude/plane/v12/prev/r/${v}_$m.png "$J" 2>&1 | tail -1
done
echo LISTDONE
