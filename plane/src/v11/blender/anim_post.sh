#!/bin/bash
# EXR frames -> PNG (URP-like bloom + sRGB, as the stills) -> MP4 (H.264) + GIF
set -e
D=/home/claude/plane/v11/blender/r/anim
P=$D/png; mkdir -p $P
for f in $D/f*.exr; do n=$(basename $f .exr); [ -f $P/$n.png ] || python3 /home/claude/plane/v11/blender/post.py $f $P/$n.png > /dev/null; done
OUT=/home/claude/plane/v11/deliv/previews
ffmpeg -y -loglevel error -framerate 20 -i $P/f%03d.png -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow -movflags +faststart $OUT/lights_v11_blender_light_functions.mp4
ffmpeg -y -loglevel error -framerate 20 -i $P/f%03d.png -vf "split[s0][s1];[s0]palettegen=max_colors=256:stats_mode=full[p];[s1][p]paletteuse=dither=sierra2_4a" -loop 0 $OUT/lights_v11_blender_light_functions.gif
ls -la $OUT/lights_v11_blender_light_functions.*
