"""Faces the camera would see from behind (Unity culls them: the surface vanishes): rays from inside the hall (a grid of
eye points at 0.9 / 1.6 m, the doors shut and open) and from outside round the garage (rings at 1.7 / 4 / 9 m) in many
directions; the first hit must face the eye. Glass two-faced by design; the lens / panel faces count (one-sided).
python3 -I backfaces.py [--draft|--test] -> backfaces.json (object, zone, material, count, an example point)"""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, '/home/claude/uaz')
import gar_spec as S

SFX = '_draft' if '--draft' in sys.argv else '_test' if '--test' in sys.argv else ''
bpy.ops.wm.open_mainfile(filepath=f'/home/claude/uaz/out/garage{SFX}.blend')
C = json.load(open(f'/home/claude/uaz/out/garage_contract{SFX}.json'))
sc = bpy.context.scene
REST = {o.name: o.matrix_world.copy() for o in bpy.data.objects}
rng = np.random.default_rng(3)
dirs = rng.normal(size=(160, 3))
dirs /= np.linalg.norm(dirs, axis=1)[:, None]
bad = {}
nray = 0
SKIPPED = []


def pose(open_):
    for n, p in C['parts'].items():
        o = bpy.data.objects.get(n)
        if o is None or p['kind'] != 'hinge':
            continue
        piv, ax = Vector(p['pivot']), Vector(p['axis']).normalized()
        a = p['range'][1] if open_ else 0.0
        o.matrix_world = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(a), 4, ax) @ Matrix.Translation(-piv) @ REST[n]
    bpy.context.view_layer.update()


def shoot(dg, eye, outside=False):
    global nray
    found = []
    for d in dirs:
        hit, loc, nrm, idx, ob, mw = sc.ray_cast(dg, Vector(eye), Vector(d), distance=30.0)
        nray += 1
        if not hit:
            continue
        if outside and loc.z < S.GROUND - 0.02:
            continue
        me = ob.data
        mat = me.materials[me.polygons[idx].material_index].name if me.materials else '-'
        if mat.startswith('M_Glass'):
            continue
        if nrm.dot(Vector(d)) > 0.05:
            pz = me.attributes['zone'].data[idx].value if 'zone' in me.attributes else -1
            found.append(((ob.name, int(round(pz)), mat), [round(v, 3) for v in loc]))
    if len(found) > 0.25 * len(dirs):
        SKIPPED.append([round(v, 2) for v in eye])
        return
    for k, loc in found:
        e = bad.setdefault(k, [0, loc, [round(v, 2) for v in eye]])
        e[0] += 1


for op in (False, True):
    pose(op)
    dg = bpy.context.evaluated_depsgraph_get()
    for x in np.linspace(-S.XI + 0.5, S.XI - 0.5, 6):
        for y in np.linspace(-S.YI + 0.5, S.YI - 0.5, 5):
            for z in (0.9, 1.6):
                shoot(dg, (x, y, z))
    for r_, h in ((12.0, 1.7), (12.0, 4.0), (16.0, 9.0), (8.5, 1.7)):
        for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
            shoot(dg, (r_ * math.cos(a), r_ * math.sin(a), h), outside=True)
rows = sorted(([k[0], k[1], k[2], v[0], v[1], v[2]] for k, v in bad.items()), key=lambda r: -r[3])
print('rays', nray, 'eyes dropped (inside solids)', len(SKIPPED), 'back-facing first hits', sum(r[3] for r in rows), 'in',
      len(rows), 'object/zone/material groups')
for r in rows[:60]:
    print('  ', r)
json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backfaces.json'), 'w'), indent=0)
