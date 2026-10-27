"""Inspect B_Skull of the shared Giant_Skeleton.fbx: verts, loose parts, boundary loops before/after merge by distance."""
import bpy, bmesh, sys
FBX = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
ob = bpy.data.objects['B_Skull']
me = ob.data
print('verts', len(me.vertices), 'faces', len(me.polygons), 'scale', tuple(ob.scale), 'dims', tuple(round(d, 2) for d in ob.dimensions))
bm = bmesh.new(); bm.from_mesh(me)
def stats(tag):
    bnd = [e for e in bm.edges if e.is_boundary]
    nonman = [e for e in bm.edges if not e.is_manifold]
    # loose parts
    seen = set(); parts = []
    for v in bm.verts:
        if v.index in seen: continue
        stack = [v]; n = 0; seen.add(v.index)
        while stack:
            x = stack.pop(); n += 1
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen: seen.add(o.index); stack.append(o)
        parts.append(n)
    parts.sort(reverse=True)
    print(tag, 'verts', len(bm.verts), 'boundary edges', len(bnd), 'non-manifold', len(nonman), 'parts', len(parts), parts[:8])
stats('raw')
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005 * max(ob.dimensions))
bm.verts.index_update()
stats('merged')
print('uv layers', [u.name for u in me.uv_layers], 'materials', [m.name for m in me.materials if m])
