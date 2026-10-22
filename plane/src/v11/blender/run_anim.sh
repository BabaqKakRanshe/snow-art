#!/bin/bash
cd /home/claude/plane/v11/blender
timeout 7200 python3 anim_cycles_v11.py -- '{"out_dir": "/home/claude/plane/v11/blender/r/anim", "frames": 60, "fps": 20, "samples": 24, "w": 640, "h": 360, "beacon_top": -150, "beacon_bottom": 20, "flicker_on": 1.5, "flicker_full": 1.8, "flicker": 0.75}' 2>&1 | grep -E "FRAME|ANIMDONE|rror"
