#!/bin/bash
# final renders of the four concepts (48 spp, interior 96)
cd /home/claude/truck
for c in c1_kung c2_vahta c3_balloon c4_tracked; do
  python3 run.py $c all 48 2>&1 | grep -E 'built|done|Error|rror|Traceback' 
done
