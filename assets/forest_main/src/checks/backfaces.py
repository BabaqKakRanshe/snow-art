"""Faces the camera would see from behind (Unity culls them: the surface vanishes): rays from inside every room (a grid of
eye points at 0.9 / 1.6 m) and from outside round the building (rings at 1.7 / 4 / 9 m) in many directions; the first
hit must face the eye. Glass and the joined lens / panel faces count too (one-sided in Unity).
python3 -I backfaces.py [--test] -> backfaces.json (object, zone, material, count, an example point)"""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector
sys.path.insert(0, '/home/claude/uaz')
import main_spec as S

SFX = '_test' if '--test' in sys.argv else ''
bpy.ops.wm.open_mainfile(filepath=f'/home/claude/uaz/out/main{SFX}.blend')
for _lib in list(bpy.data.libraries):                 # 1.2: the snow_kit instances (linked) are not the building's
    bpy.data.libraries.remove(_lib)                  # geometry: checked as in 1.1, the station has main_leit_check.py
C = json.load(open(f'/home/claude/uaz/out/main_contract{SFX}.json'))
for n, p in C['parts'].items():
    o = bpy.data.objects.get(n)
    if o is not None and p['kind'] == 'scale':
        o.scale.z = p['range'][1] if p.get('open', True) else p['range'][0]
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene
rng = np.random.default_rng(3)
dirs = rng.normal(size=(160, 3))
dirs /= np.linalg.norm(dirs, axis=1)[:, None]
bad = {}
nray = 0


SKIPPED = []


def shoot(eye, outside=False):
    """an eye inside a solid (a wall, a cabinet, a slab) sees mostly backs: such eyes are dropped (> 25 % of its rays);
    from outside, what lies under the yard is not seen (the terrain is not in this scene)"""
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
        if mat.startswith('M_Glass'):                  # glass is two faces back to back
            continue
        if nrm.dot(Vector(d)) > 0.05:                  # seen from behind
            pz = me.attributes['zone'].data[idx].value if 'zone' in me.attributes else -1
            found.append(((ob.name, int(round(pz)), mat), [round(v, 3) for v in loc]))
    if len(found) > 0.25 * len(dirs):
        SKIPPED.append([round(v, 2) for v in eye])
        return
    for k, loc in found:
        e = bad.setdefault(k, [0, loc, [round(v, 2) for v in eye]])
        e[0] += 1


for rn, R in S.ROOMS.items():
    xs = np.linspace(R['x0'] + 0.63, R['x1'] - 0.63, max(2, int((R['x1'] - R['x0']) / 2.5)))
    ys = np.linspace(R['y0'] + 0.63, R['y1'] - 0.63, max(2, int((R['y1'] - R['y0']) / 2.5)))
    zs = [R['f'] + 0.9, R['f'] + 1.6] if rn != 'Treppenhaus' else [S.UG_F + 1.6, 1.6, S.OG_F + 1.6, S.ROOF + 1.6]
    for x in xs:
        for y in ys:
            for z in zs:
                shoot((x, y, z))
for r_, h in ((22.0, 1.7), (22.0, 4.0), (26.0, 9.0), (14.0, 1.7)):          # (below ground nothing is seen)
    for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
        shoot((-4.0 + r_ * math.cos(a), r_ * math.sin(a), h), outside=True)
rows = sorted(([k[0], k[1], k[2], v[0], v[1], v[2]] for k, v in bad.items()), key=lambda r: -r[3])
print('rays', nray, 'eyes dropped (inside solids)', len(SKIPPED), 'back-facing first hits', sum(r[3] for r in rows), 'in',
      len(rows), 'object/zone/material groups')
for r in rows[:60]:
    print('  ', r)
json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backfaces.json'), 'w'), indent=0)
