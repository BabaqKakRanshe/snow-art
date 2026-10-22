"""Whole-forest planning data (Unity frame): terrain vertices (decimated), road triangles (dirt/asphalt), water, bones.
python3 -I map_big.py -- Forest.blend out.json"""
import bpy, sys, json
from mathutils import Matrix, Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
Cinv = Matrix(((-1, 0, 0), (0, 0, 1), (0, -1, 0)))
out = {'terrain': [], 'road': [], 'water': [], 'bones': [], 'roadmats': {}}
for ob in bpy.data.objects:
    if ob.type != 'MESH':
        continue
    M = ob.matrix_world
    if ob.name.startswith('Terrain_'):
        vs = ob.data.vertices
        step = max(1, len(vs) // 4000)
        for k in range(0, len(vs), step):
            v = vs[k]
            u = Cinv @ (M @ v.co); out['terrain'].append([round(u.x, 1), round(u.y, 2), round(u.z, 1)])
    elif ob.name == 'Forest_Road':
        me = ob.data
        mats = [s.material.name if s.material else '' for s in ob.material_slots]
        for p in me.polygons:
            c = Cinv @ (M @ p.center)
            mn = mats[p.material_index] if p.material_index < len(mats) else ''
            out['roadmats'][mn] = out['roadmats'].get(mn, 0) + 1
            out['road'].append([round(c.x, 2), round(c.y, 2), round(c.z, 2), mn])
    elif ob.name.startswith('Forest_Water'):
        for k in range(0, len(ob.data.vertices), 4):
            v = ob.data.vertices[k]
            u = Cinv @ (M @ v.co); out['water'].append([round(u.x, 1), round(u.y, 2), round(u.z, 1)])
    elif ob.name.startswith('Giant'):
        corners = [Cinv @ (M @ Vector(c)) for c in ob.bound_box]
        lo = [min(p[i] for p in corners) for i in range(3)]; hi = [max(p[i] for p in corners) for i in range(3)]
        out['bones'].append({'n': ob.name, 'lo': [round(x, 1) for x in lo], 'hi': [round(x, 1) for x in hi]})
json.dump(out, open(a[1], 'w'))
print('terrain', len(out['terrain']), 'road polys', len(out['road']), out['roadmats'], 'water', len(out['water']), 'bones', len(out['bones']))
