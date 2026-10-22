import bpy, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
C = json.load(open('/home/claude/uaz/out/gen_contract.json'))
objs = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith(('COL_', 'Snow_'))]
B = {}
for o in objs:
    me = o.data; me.calc_loop_triangles()
    B[o.name] = BVHTree.FromPolygons([o.matrix_world @ v.co for v in me.vertices], [tuple(t.vertices) for t in me.loop_triangles])
def inside(b, p):
    votes = 0
    for d in (Vector((1, 0.0137, 0.0071)), Vector((-0.011, 1, 0.017)), Vector((0.013, -0.009, 1))):
        d.normalize(); o = p.copy(); hits = 0
        for _ in range(200):
            loc, n, i, dist = b.ray_cast(o, d, 10)
            if loc is None: break
            hits += 1; o = loc + d * 1e-5
        votes += hits % 2
    return votes >= 2
for k, s in C['sockets'].items():
    if s['kind'] not in ('hand', 'pour', 'item_slot', 'vfx', 'hide'):
        continue
    p = Vector(s['pos'])
    own = s['parent']
    for n, b in B.items():
        if n == own or (s['kind'] == 'hand' and n == own):
            continue
        if inside(b, p):
            print(f'{k:26s} ({s["kind"]}) at {tuple(s["pos"])} is inside {n}')
# also part pivots of interactive parts inside other objects
for k, p in C['parts'].items():
    if p['kind'] in ('static',):
        continue
    if k not in bpy.data.objects: continue
    o = bpy.data.objects[k]
    c = sum((o.matrix_world @ v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
    for n, b in B.items():
        if n == k or n in [ch.name for ch in o.children_recursive]:
            continue
        if inside(b, c):
            print(f'part {k:24s} centroid {tuple(round(x,3) for x in c)} inside {n}')
