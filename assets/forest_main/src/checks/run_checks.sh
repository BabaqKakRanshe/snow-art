#!/bin/bash
# all checks of the main building on out/main.blend (+ out/main_contract.json), one log each next to this script;
# then checks_summary.json (the short Russian summary for docs/MAIN_CONTRACT.md)
D=$(cd "$(dirname "$0")" && pwd)
cd "$D"
timeout 1800 python3 -I probe_main.py > probe_main.log 2>&1; echo "probe exit $?" >> probe_main.log
timeout 3000 python3 -I backfaces.py > backfaces.log 2>&1; echo "backfaces exit $?" >> backfaces.log
timeout 1800 python3 -I coplanar2.py > coplanar2.log 2>&1; echo "coplanar exit $?" >> coplanar2.log
timeout 2400 python3 -I props_check.py > props_check.log 2>&1; echo "props exit $?" >> props_check.log
timeout 3600 python3 -I walk.py > walk.log 2>&1; echo "walk exit $?" >> walk.log
timeout 5400 python3 -I sweep2.py > sweep2.log 2>&1; echo "sweep2 exit $?" >> sweep2.log
python3 summary.py "$D"
echo ALLDONE > done.flag
