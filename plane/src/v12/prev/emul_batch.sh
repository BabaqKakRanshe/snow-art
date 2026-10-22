#!/bin/bash
# usage: emul_batch.sh view1 view2 ...  (night + flat for each, full 1080p)
cd /home/claude/plane/v11/prev
for v in "$@"; do
  python3 urp_emulate.py /home/claude/plane/v12/prev/r/$v v11 /home/claude/plane/v12/prev/r/${v}_night.png '{"downsample":1}' 2>&1 | tail -1
  python3 urp_emulate.py /home/claude/plane/v12/prev/r/$v v11 /home/claude/plane/v12/prev/r/${v}_flat.png '{"downsample":1,"ambient":0.5,"moon":0.0,"atmosphere":0.0,"fog_density":0.0,"levels":{"nav":0,"beacon":0,"landing":0,"cabin":0,"cargo":0,"flood":0,"strobe":0}}' 2>&1 | tail -1
done
echo BATCHDONE
