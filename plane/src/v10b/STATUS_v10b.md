# v10b status (14.10, after the first v10 package was found to have visible defects)

Found by comparing v9/v10 renders + a new ray-cast view comparison (vis2/viscmp.py, Unity-like back-face culling):
- vis_remove.py let gauge glass (M_GaugeGlass inside CP_Gauges) occlude: 12 gauge dials deleted -> holes. FIXED: vis_remove2.py
  (Embree), glass never occludes.
- meshoptimizer joined touching pieces (coincident vertices = wedges): wrong normals/UVs on door chamfers, liner fillets,
  rivets; sampled p99 metrics missed it. FIXED: opt_v10b.py = per-connected-piece simplification + per-triangle check
  (opt_lib2.tri_check, exact float64 closest point; Blender BVH fails on 2000:1 slivers) + vertex locks until clean.
- Cycles drew custom normals wrongly on fans without sharp edges (Wheel lugs black). FIXED: sharp_lib.set_normals
  (sharp edges where normals jump; encoded twice; verify; free normals fallback). FBX/Unity were not affected by this one.
- zero-area triangles at collapsed-ring rivet tips broke normal decoding -> dropped in build_mesh2.

Pipeline (geometry): opt_v10b.py [view_locks_1.json] -> run10b_geo.sh (vis_remove2 -> fix_normals (VISREP) -> mark_sharp_v10
-> dump_scene -> viscmp). Cache: cache_v10b/*.npz (VERSION b8).
Result: reduced set 184 483 -> 129 201 tris, hidden 4 455; viscmp 130 views / 50 M px: 18 px left = z-fight of coincident
faces in CP_BarrierNets (unchanged part, v9 has the same twin faces).
Backups: out/plane_v9_final_v10_firstpass(.blend|_meshopt.blend) = the first (defective) v10.
meshopt_lod.py: per-piece jitter (LOD wedge mixing) + exact normals; backup meshopt_lod.v10a.py.
docs_v10/v10_numbers.py -> b reports (backup v10_numbers.v10a.py). TODO: contract 17.1 text, export, verify, audit,
docs, renders, previews, blender file, zip, deliver.
