#!/bin/bash
# all checks of the garage on out/garage.blend (+ out/garage_contract.json), one log each next to this script; then
# checks_summary.json (the short Russian summary for docs/GARAGE_CONTRACT.md)
D=$(cd "$(dirname "$0")" && pwd)
cd "$D"
timeout 1200 python3 -I probe_gar.py > probe_gar.log 2>&1; echo "probe exit $?" >> probe_gar.log
timeout 1800 python3 -I backfaces.py > backfaces.log 2>&1; echo "backfaces exit $?" >> backfaces.log
timeout 1200 python3 -I coplanar2.py /home/claude/uaz/out/garage.blend > coplanar2.log 2>&1; echo "coplanar exit $?" >> coplanar2.log
timeout 3000 python3 -I walk.py > walk.log 2>&1; echo "walk exit $?" >> walk.log
timeout 3000 python3 -I sweep2.py > sweep2.log 2>&1; echo "sweep2 exit $?" >> sweep2.log
python3 summary.py "$D"
echo ALLDONE > done.flag
