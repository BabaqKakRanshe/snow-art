#!/bin/sh
# the road prefabs' checks (after road_build.py): -> road_checks.json, road_checks.log
cd "$(dirname "$0")"
python3 -I road_checks.py > road_checks.log 2>&1
grep -E "^(coplanar|u3|backfaces|floating|bridge|overlook|windfall|europost)" road_checks.log
