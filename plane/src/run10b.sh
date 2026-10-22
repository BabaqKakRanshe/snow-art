#!/bin/bash
# Utility Plane v10 (revision b) - full pipeline, in order. Scripts: v10b/ (working copies in the session scratchpad).
# 0. textures (unchanged since the first v10 pass): python3 tex_v10.py -> export/unity_v10/.../Textures
# 1. geometry: error-bounded reduction per connected piece + per-triangle check + locks
#      python3 opt_v10b.py view_locks_1.json        -> out/plane_v9_final_v10_meshopt.blend, opt_v10b_report.json
# 2. hidden faces (Embree; glass never occludes) -> normals repair -> sharp edges -> scene dumps -> view comparison
#      bash run10b_geo.sh                           -> out/plane_v9_final_v10.blend, vis_v10b_report.json, vis2/cmp_b
#    (view_locks_1.json was made from the first vis2/cmp_b report: points of the 2 components on reduced parts)
# 3. Unity export (colliders / sockets / zones from the v9 meshes; LOD budgets of v9: out/lod_budget_v9.json)
#      python3 export_unity_v10.py v10 > logs10/exp10.log
#      python3 fbxverify_v10.py v10 > logs10/ver10.log
#      python3 audit_fbx.py export/unity_v10/Assets/UtilityPlane/Models/UtilityPlane.fbx audit_fbx_v10.json
#      python3 colcmp.py <v9 fbx> <v10 fbx>          (all 60 colliders within 0.1 mm)
#      dump_scene.py on both FBX + viscmp3.py        (regressions vs v9 model AND v9 FBX: z-fight pixels only)
#      lodcheck.py                                   -> vis2/lodcheck3.log (LOD switch pops, v9 vs v10)
# 4. docs: docs_v10/build_contract10.py, build_readme10.py, build_components10.py,
#      make_docs.py logs10/exp10.log logs10/ver10.log, fill_prompt10.py logs10/exp10.log logs10/ver10.log
#      kit task 1.2.1: docs_kit/fill_kit_prompt121.py
# 5. renders v9/v10 (rcmp.sh v9|v10), make_sheets10.py -> previews; make_blend10_all.py <pkg root> -> Blender file
