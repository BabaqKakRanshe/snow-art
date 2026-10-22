"""for every printed face (panel material) of every item: is it visible, or does the body poke through it?
python3 -I label_check.py <blend> [mat_name]"""
import bpy, sys, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
blend = sys.argv[1]
MAT = sys.argv[2] if len(sys.argv) > 2 else 'M_Item_Panel'
bpy.ops.wm.open_mainfile(filepath=blend)
bad = {}
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.type != 'MESH':
        continue
    mi = [i for i, m in enumerate(o.data.materials) if m and m.name == MAT]
    if not mi:
        continue
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    tot, hidden, ds = 0, 0, []
    for f in bm.faces:
        if f.material_index not in mi:
            continue
        c = f.calc_center_median()
        n = f.normal
        pts = [c] + [c.lerp(v.co, 0.7) for v in f.verts]
        for p in pts:
            tot += 1
            hit = tree.ray_cast(p + n * 0.004, -n, 0.006)
            if hit[0] is None:
                continue
            hf = bm.faces[hit[2]]
            d = (hit[0] - p).dot(n)
            if hf.material_index not in mi and d > -1e-5:
                hidden += 1
                ds.append(round(d * 1000, 2))
    bm.free()
    if hidden:
        bad[o.name] = (hidden, tot, sorted(ds)[:6], sorted(ds)[-3:])
print('LABELS', bad)
