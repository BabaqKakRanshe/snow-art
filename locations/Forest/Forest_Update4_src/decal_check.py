import bpy, json, bmesh, numpy as np
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree
S = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad'
D = S + '/u3/Assets/Locations/Forest/Data/'
L = json.load(open(D + 'Forest_Layout.json'))
Dr = json.load(open(D + 'Forest_Dressing.json'))
Op = json.load(open(D + 'Forest_Opening.json'))
pl = {p['m']: p for p in L['prefabs']}['BaseMain']
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/forest_main/main.blend')
dg = bpy.context.evaluated_depsgraph_get()
bm = bmesh.new()
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    root = o
    while root.parent: root = root.parent
    if root.name != 'BaseMain': continue
    m = o.evaluated_get(dg).to_mesh()
    t = bmesh.new(); t.from_mesh(m); t.transform(o.matrix_world); 
    tm = bpy.data.meshes.new('t'); t.to_mesh(tm); bm.from_mesh(tm); t.free()
bvh = BVHTree.FromBMesh(bm)
qU = pl['q']; pU = np.array(pl['p'])
def qinv_rot(q, v):
    x, y, z, w = q; qv = np.array([-x, -y, -z]); v = np.array(v, float); t = 2 * np.cross(qv, v); return v + w * t + np.cross(qv, t)
decals = list(Dr['decals']) + [d for s in Op['scares'] if s.get('decals') for d in s['decals']]
gaps = []
for d in decals:
    loc = qinv_rot(qU, np.array(d['p']) - pU)          # Unity prefab-local
    b = Vector((-loc[0], -loc[2], loc[1]))             # Blender frame: x = -X, y = -Z, z = Y
    hit = bvh.ray_cast(b + Vector((0, 0, 0.05)), Vector((0, 0, -1)), 0.5)
    if hit[0] is None:
        gaps.append((d.get('id'), None)); continue
    gaps.append((d.get('id'), round(b.z - hit[0].z, 4)))
bad = [g for g in gaps if g[1] is None or not (0.001 <= g[1] <= 0.02)]
print('DECALS', len(gaps), 'gap min/max', min(g[1] for g in gaps if g[1] is not None), max(g[1] for g in gaps if g[1] is not None), 'bad', bad[:20])
