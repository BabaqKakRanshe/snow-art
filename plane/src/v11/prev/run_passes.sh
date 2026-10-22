#!/bin/bash
# renders the Cycles passes for every view (1520x856)
cd /home/claude/plane/v11/prev
for v in ext_front ext_rear ext_far int_cockpit int_bay; do
  python3 -c "
import json; V = json.load(open('views.json'))['$v']
V.update(out='/home/claude/plane/v11/prev/r/$v', W=1520, H=856)
json.dump(V, open('r/cfg_$v.json', 'w'))"
  timeout 1500 python3 cy11.py r/cfg_$v.json > r/log_$v.txt 2>&1
  echo "$v $(grep -c Saved r/log_$v.txt) $(grep dumped r/log_$v.txt)"
done
