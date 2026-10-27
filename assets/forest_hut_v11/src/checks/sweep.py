"""Sweep every moving part through its range and report new interpenetrations (BVH triangle overlap) vs rest.
python3 -I sweep.py [--draft] [-- Part_A Part_B ...]  -> sweep{_draft}.json next to this script"""
import bpy, json, math, os, sys
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ARGS = sys.argv[:sys.argv.index('--')] if '--' in sys.argv else sys.argv
SUF = '_draft' if '--draft' in ARGS else ''
bpy.ops.wm.open_mainfile(filepath=f'/home/claude/hut11/out/hut{SUF}.blend')
C = json.load(open(f'/home/claude/hut11/out/hut_contract{SUF}.json'))
P = C['parts']
SKIP_OBJ = lambda n: n.startswith(('COL_', 'LIGHT_'))
objs = {o.name: o for o in bpy.data.objects if o.type == 'MESH' and not SKIP_OBJ(o.name)}


def world_mesh(o):
    me = o.data
    me.calc_loop_triangles()
    M = o.matrix_world
    V = [M @ v.co for v in me.vertices]
    T = [tuple(t.vertices) for t in me.loop_triangles]
    zone_attr = me.attributes.get('zone')
    zones = [zone_attr.data[t.polygon_index].value if zone_attr else -1 for t in me.loop_triangles]
    return V, T, zones


WM = {n: world_mesh(o) for n, o in objs.items()}
BV = {n: BVHTree.FromPolygons(v, t) for n, (v, t, z) in WM.items()}


def descendants(o):
    return [c.name for c in o.children_recursive if c.name in objs]


def xform(kind, piv, ax, val):
    piv, ax = Vector(piv), Vector(ax).normalized()
    if kind in ('hinge', 'twist', 'spin'):
        return Matrix.Translation(piv) @ Matrix.Rotation(math.radians(val), 4, ax) @ Matrix.Translation(-piv)
    if kind == 'slide':
        return Matrix.Translation(ax * val)
    raise ValueError(kind)


def group_bvh(names, M):
    V, T, owner = [], [], []
    for n in names:
        v, t, z = WM[n]
        off = len(V)
        V += [M @ p for p in v]
        T += [(a + off, b + off, c + off) for a, b, c in t]
        owner += [(n, i) for i in range(len(t))]
    return BVHTree.FromPolygons(V, T), V, T, owner


def centroid(n, i):
    v, t, z = WM[n]
    a, b, c = t[i]
    return (v[a] + v[b] + v[c]) / 3, z[i]


ONLY = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None
report = {}
for name, p in P.items():
    if p['kind'] not in ('hinge', 'twist', 'slide', 'spin') or name not in objs:
        continue
    if ONLY and name not in ONLY:
        continue
    rng = p['range']
    if p['kind'] == 'spin':
        rng = [0, 360]
    if rng is None:          # needles: sweep the scale range
        sc = p['scale']
        rng = [sc['angle_min'] - p['rest'], sc['angle_max'] - p['rest']]
    lo, hi = rng
    if p['kind'] in ('twist', 'spin') and hi - lo > 360:
        hi = lo + 360
    vals = list(np.linspace(lo, hi, 25)) if p['kind'] != 'slide' else list(np.linspace(lo, hi, 9))
    grp = [name] + descendants(objs[name])
    others = [n for n in objs if n not in grp and not n.startswith(('Snow_', 'Glow_'))]
    rest_hits = {}
    res = {}
    for k, val in enumerate([0.0] + vals):
        M = xform(p['kind'], p['pivot'], p['axis'], val)
        bvh, V, T, owner = group_bvh(grp, M)
        for o in others:
            pairs = BV[o].overlap(bvh)
            if not pairs:
                continue
            hit_o = {i for i, j in pairs}
            if k == 0:
                rest_hits[o] = hit_o
                continue
            new = hit_o - rest_hits.get(o, set())
            if new:
                mov = {owner[j] for i, j in pairs if i in new}
                r = res.setdefault(o, dict(vals=[], ex_other=None, ex_mov=None, n=0))
                r['vals'].append(round(float(val), 2))
                if len(new) > r['n']:
                    r['n'] = len(new)
                    cs = [centroid(o, i) for i in list(new)[:4]]
                    r['ex_other'] = [(tuple(round(x, 3) for x in c), int(z)) for c, z in cs]
                    mv = list(mov)[:3]
                    r['ex_mov'] = [(mn, tuple(round(x, 3) for x in (M @ centroid(mn, mi)[0]))) for mn, mi in mv]
    rest_list = {o: len(h) for o, h in rest_hits.items()}
    report[name] = dict(kind=p['kind'], range=rng, group=grp, rest_overlaps=rest_list, new=res)
    print('==', name, p['kind'], rng, 'group', grp)
    print('   rest overlaps:', rest_list)
    for o, r in res.items():
        print('   NEW vs', o, 'at', r['vals'][:6], ('... %d vals' % len(r['vals'])) if len(r['vals']) > 6 else '',
              'other tris', r['ex_other'], 'moving', r['ex_mov'])
json.dump(report, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'sweep{SUF}.json'), 'w'),
          indent=1, default=str)
