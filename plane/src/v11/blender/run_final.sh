#!/bin/bash
# final Cycles stills (sequential: each render uses both cores)
cd /home/claude/plane/v11/blender
R=/home/claude/plane/v11/blender/r
run() { timeout 3600 python3 render_cycles_v11.py -- "$2" 2>&1 | grep -E "RENDERED|rror" ; python3 post.py $R/cy_$1.exr $R/cy_$1.png; }
run ext_front        '{"view": "ext_front", "out": "'$R'/cy_ext_front.exr", "time": 0.6, "beacon_top": -60, "beacon_bottom": -100, "samples": 128}'
run ext_front_strobe '{"view": "ext_front", "out": "'$R'/cy_ext_front_strobe.exr", "time": 0.002, "beacon_top": -60, "beacon_bottom": -100, "samples": 128}'
run ext_rear         '{"view": "ext_rear", "out": "'$R'/cy_ext_rear.exr", "time": 0.6, "beacon_top": 140, "beacon_bottom": 60, "samples": 128}'
run ext_far          '{"view": "ext_far", "out": "'$R'/cy_ext_far.exr", "time": 0.6, "beacon_top": 30, "beacon_bottom": -150, "samples": 128}'
run int_cockpit      '{"view": "int_cockpit", "out": "'$R'/cy_int_cockpit.exr", "time": 0.6, "atmosphere": 0.05, "samples": 128}'
run int_bay          '{"view": "int_bay", "out": "'$R'/cy_int_bay.exr", "time": 0.6, "atmosphere": 0.05, "samples": 128}'
run ext_front_atm1   '{"view": "ext_front", "out": "'$R'/cy_ext_front_atm1.exr", "time": 0.6, "beacon_top": -60, "beacon_bottom": -100, "atmosphere": 1.0, "samples": 128}'
run ext_front_atm0   '{"view": "ext_front", "out": "'$R'/cy_ext_front_atm0.exr", "time": 0.6, "beacon_top": -60, "beacon_bottom": -100, "atmosphere": 0.0, "samples": 128}'
echo ALLDONE
