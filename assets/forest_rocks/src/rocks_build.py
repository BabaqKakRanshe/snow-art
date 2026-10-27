"""forest_rocks: build the 12 rocks (rocks_kit), bake the PSX atlases (rocks_paint), write the contract.
python3 -I rocks_build.py [--draft] -> out/rocks.blend, rocks.json, rocks_contract.json, tex/rocks/
(--draft: no bake, plain grey; out/rocks_draft.blend). In the .blend the models stand apart in rows (display_offset)."""
import sys, os, math, json, time
sys.path.insert(0, '/home/claude/uaz')
import bpy
import numpy as np
from mathutils import Vector, Matrix
import psxlib as P
import psxbake as PB
import rocks_kit as RK

DRAFT = '--draft' in sys.argv
HERE = P.HERE
TEX = os.path.join(HERE, 'tex', 'rocks')
OUT = os.path.join(HERE, 'out')
os.makedirs(TEX, exist_ok=True)
T0 = time.time()
PB.POS_SCALE = 80.0                                   # bake range +-40 m: the rows span x -2..33, y -22..0
SHED_PPM = 51.3                                       # the project's pixel (the generator shed's building atlas)
INFO = {'atlases': {}}


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


def to_unity(v):
    return [round(-float(v[0]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(-float(v[1]), 4) + 0.0]


bpy.ops.wm.read_factory_settings(use_empty=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
models = RK.build_rocks()
colls = {}
for kind, title in (('stone', 'Stones'), ('boulder', 'Boulders'), ('cliff', 'Cliffs')):
    colls[kind] = bpy.data.collections.new(title)
    bpy.context.scene.collection.children.link(colls[kind])
objs, DISPLAY = {}, {}
row_x = {'stone': 0.0, 'boulder': 0.0, 'cliff': 0.0}
ROW_Y = {'stone': 0.0, 'boulder': -5.0, 'cliff': -16.0}
for m in models:
    o = RK.to_object(m, colls[m['kind']])
    me = o.data
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    me.set_sharp_from_angle(angle=math.radians(38.0))
    xs = [v.co.x for v in me.vertices]
    w = max(xs) - min(xs)
    gap = {'stone': 0.5, 'boulder': 1.2, 'cliff': 3.0}[m['kind']]
    off = Vector((row_x[m['kind']] - min(xs), ROW_Y[m['kind']], 0.0))
    row_x[m['kind']] += w + gap
    o.location = off
    DISPLAY[m['name']] = [round(off.x, 3), round(off.y, 3), 0.0]
    objs[m['name']] = o
bpy.context.view_layer.update()
for o in objs.values():                                # bake the display offset into nothing: keep the origin at the ground
    pass
stats = {}
for m in models:
    o = objs[m['name']]
    co = np.array([v.co[:] for v in o.data.vertices])
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    zone = np.array([a.value for a in o.data.attributes['zone'].data])
    area_vis = sum(p.area for p, z in zip(o.data.polygons, zone) if int(round(z)) % 2 == 0)
    stats[m['name']] = dict(kind=m['kind'], tris=tris, min=co.min(0).round(3).tolist(), max=co.max(0).round(3).tolist(),
                            area=round(area_vis, 2), bury=m['bury'], note=m['note'])
    log(m['name'], tris, 'tris', 'size', (co.max(0) - co.min(0)).round(2).tolist(), 'top', round(co[:, 2].max(), 2),
        'area', round(area_vis, 1))
groups = {'Rocks': [objs[m['name']] for m in models if m['kind'] != 'cliff'],
          'Cliffs': [objs[m['name']] for m in models if m['kind'] == 'cliff']}
for g, ol in groups.items():
    log('group', g, 'area', round(sum(stats[o.name]['area'] for o in ol), 1))

if DRAFT:
    mat = bpy.data.materials.new('draft_rock')
    mat.diffuse_color = (0.42, 0.41, 0.39, 1)
    for o in objs.values():
        o.data.materials.append(mat)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'rocks_draft.blend'))
    json.dump(dict(stats=stats, display=DISPLAY), open(os.path.join(OUT, 'rocks_draft.json'), 'w'), indent=1)
    log('draft saved')
    sys.exit(0)

# ------------------------------------------------------------------ atlases
import rocks_paint as RP
heights = {n: s['max'][2] for n, s in stats.items()}
painter = RP.make_painter(models, heights)
hidden_small = {RK.Z0 + 2 * m['idx'] + 1: 0.1 for m in models}
ATLASES = [('Rocks', [objs[m['name']] for m in models if m['kind'] != 'cliff'], 64.0, 0.30)]
for i, m in enumerate([m for m in models if m['kind'] == 'cliff']):
    ATLASES.append((f'Cliff{i + 1}', [objs[m['name']]], SHED_PPM, 0.55))
ATLAS_OF = {}
for name, ol, cap, aod in ATLASES:
    PB.make_atlas(name, ol, painter, TEX, prefix='T_Rocks_', mat_prefix='M_Rocks_', size=1024, ao_min=0.30, ao_dist=aod,
                  rough=0.9, log=log, info=INFO['atlases'], ppm_cap=cap, zone_scale=hidden_small)
    for o in ol:
        ATLAS_OF[o.name] = name

# ------------------------------------------------------------------ contract, stats, save
C = {'models': {}, 'meta': {}}
for m in models:
    s = stats[m['name']]
    lo, hi = s['min'], s['max']
    C['models'][m['name']] = dict(
        kind=m['kind'], atlas=ATLAS_OF[m['name']], material='M_Rocks_' + ATLAS_OF[m['name']], tris=s['tris'],
        heightAboveGround=round(hi[2], 3), bury=m['bury'],
        size=[round(hi[i] - lo[i], 3) for i in range(3)],
        sizeUnity=[round(hi[0] - lo[0], 3), round(hi[2] - lo[2], 3), round(hi[1] - lo[1], 3)],
        boundsUnity=dict(min=[round(-hi[0], 3) + 0.0, round(lo[2], 3), round(-hi[1], 3) + 0.0],
                         max=[round(-lo[0], 3) + 0.0, round(hi[2], 3), round(-lo[1], 3) + 0.0]),
        collider=dict(type='MeshCollider', convex=m['kind'] != 'cliff', mesh='render'),
        display_offset=DISPLAY[m['name']], note=m['note'])
C['meta'] = dict(
    version='1.0', units='metres',
    frame='each model in its own frame: z up, front -y; origin on the ground line (z = 0); below it the foot goes into the '
          'ground down to -bury (flat underside, not seen). In rocks.blend the models stand apart in rows (display_offset)',
    unity='(x, y, z) -> Unity (-x, z, -y); the front (-y) is the prefab\'s +Z',
    colliders='MeshCollider on the render mesh: convex for the stones and boulders (Unity cooks the hull), not convex for the '
              'cliffs (static)',
    materials='M_Rocks_Rocks (6 stones + 3 boulders), M_Rocks_Cliff1..3 (one per cliff): baked PSX atlases, point filter',
    textures='tex', model='rocks.blend')
json.dump(C, open(os.path.join(OUT, 'rocks_contract.json'), 'w'), indent=1, ensure_ascii=False)
tris = {n: s['tris'] for n, s in stats.items()}
json.dump(dict(atlases=INFO['atlases'], tris=tris, tris_total=sum(tris.values()), display_offset=DISPLAY),
          open(os.path.join(OUT, 'rocks.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'rocks.blend'))
log('saved rocks.blend; tris', sum(tris.values()))
