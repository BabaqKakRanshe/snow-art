#!/bin/bash
# v10b geometry chain after opt_v10b.py (which writes out/plane_v9_final_v10_meshopt.blend):
#   hidden faces (glass never hides) -> normals repair -> sharp edges -> scene dumps -> view comparison
set -e
cd /tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/opt
O=/home/claude/plane/out
python3 vis_remove2.py $O/plane_v9_final_v10_meshopt.blend $O/plane_v9_final_v10.blend > vis_v10b.log 2>&1
cp $O/plane_v9_final_v10.blend $O/plane_v9_final_v10_vis_raw.blend
VISREP=vis_v10b_report.json python3 fix_normals.py > fix_v10b.log 2>&1
python3 mark_sharp_v10.py > sharp_v10b.log 2>&1
python3 vis2/dump_scene.py $O/plane_v9_final_v10.blend $PWD/vis2/scene_v10.npz > vis2/dump_v10.log 2>&1
python3 vis2/viscmp.py vis2/scene_v9.npz vis2/scene_v10.npz vis2/cmp_b > vis2/cmp_b.log 2>&1
echo GEO_DONE >> vis2/cmp_b.log
