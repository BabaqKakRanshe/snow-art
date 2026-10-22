Forest Update 4 — how the package was made (all paths relative to the generator's workspace)

1. u4_export.py   — Blender 5.0 (bpy as a Python module): one FBX per prefab from the six batch blends
                    (source/assets/forest_hut|kpp|yard|main|garage|road/*.blend) in Update 3's FBX convention:
                    FBX 7400, Y up, front +Z, UnitScaleFactor 100, root at the origin, children translated only,
                    normals and smoothing by face written (Normals: Import).
                    Box colliders COL_*, halo cards Glow_* and LIGHT_* sockets stay out; nested children are joined
                    into their top-level object; game-known material names get Update 3's names.
2. u4_verify_fbx.py — every FBX back through Blender's importer: bounds and pivots of every object within 1 mm,
                    triangles and materials as in the blend, no node rotation or scale.
3. u4_build.py    — the unitypackage: models under Update 3's GUIDs, textures renamed to *_A_px / *_E_px,
                    Forest_Materials.json (47 new + 3 updated), Forest_Layout.json (13 changes, block "u4"),
                    README section (u4_readme_section.md).
4. u4_check_pkg.py — independent check of the package against Update 3's files.
5. u4_preview.py  — quick renders of the package FBX with the package's material definitions (reports/u4_preview_sheet.png).
Helpers: lampspots.py (lamp, lens and halo positions), u3tris.py (Update 3 triangle counts), decal_check.py (decals of
Forest_Dressing / Forest_Opening above the new floors: 56 of 56, 4–12 mm), nodes_cmp.py (FBX nodes vs Update 3 and the
layout references), pivot_cmp.py (pivots of the IX parts against Update 3: 146 of 155 within 2 cm, 9 moved -
 FOREST_U4_UNITY.md, Appendix А), list_blend.py.
reports/: export report (objects, bounds, pivots, materials, triangles), verify result (0 problems), lamp positions,
package manifest (paths, GUIDs, md5), preview sheet.
