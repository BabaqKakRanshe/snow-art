"""islands with a negative signed volume (faces pointing inwards) in out/hut.blend (or the .blend given last)"""
import bpy, bmesh, sys
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=sys.argv[-1] if sys.argv[-1].endswith('.blend') else '/home/claude/uaz/out/hut.blend')
bad = []
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name.startswith('COL_'):
        continue
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    # islands by shared vertices (KB faces of one primitive share verts only when built by box_m / loft / lathe)
    parent = list(range(len(bm.verts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for f in bm.faces:
        vs = [v.index for v in f.verts]
        for v in vs[1:]:
            a, b = find(vs[0]), find(v)
            if a != b:
                parent[a] = b
    isl = {}
    for f in bm.faces:
        r = find(f.verts[0].index)
        p0 = f.verts[0].co
        vol = 0.0
        for i in range(1, len(f.verts) - 1):
            vol += p0.dot(f.verts[i].co.cross(f.verts[i + 1].co)) / 6.0
        a = isl.setdefault(r, [0.0, 0, Vector()])
        a[0] += vol
        a[1] += 1
        a[2] += f.calc_center_median()
    for r, (vol, n, c) in isl.items():
        if n >= 6 and vol < -1e-8:
            bad.append((o.name, n, vol, tuple(round(v, 3) for v in (o.matrix_world @ (c / n)))))
    bm.free()
print('inverted islands', len(bad))
for b in bad[:60]:
    print('  ', b)
