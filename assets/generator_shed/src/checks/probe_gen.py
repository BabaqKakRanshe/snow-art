"""sanity probe of out/gen.blend + out/gen_contract.json: pivots, axes, sockets, sweeps of the moving parts, colliders"""
import bpy, json, math, sys
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/home/claude/uaz/out/gen.blend')
C = json.load(open('/home/claude/uaz/out/gen_contract.json'))
L = json.load(open('/home/claude/uaz/out/gen_lights.json'))['lights']
O = bpy.data.objects
P, S = C['parts'], C['sockets']
bad, warn = [], []


def wverts(o, M=None):
    M = M or o.matrix_world
    return np.array([tuple(M @ v.co) for v in o.data.vertices])


def bbox(o, M=None):
    w = wverts(o, M)
    return w.min(0), w.max(0)


def dist_box(p, lo, hi):
    d = np.maximum(np.maximum(lo - p, p - hi), 0)
    return float(np.linalg.norm(d))


# 1. pivots near their objects, unit axes, parents exist
for k, p in P.items():
    o = O.get(k)
    if o is None:
        bad.append(f'{k}: no object')
        continue
    if p['parent'] and p['parent'] not in O:
        bad.append(f'{k}: parent {p["parent"]} missing')
    if o.type == 'MESH' and len(o.data.vertices):
        lo, hi = bbox(o)
        d = dist_box(np.array(p['pivot']), lo, hi)
        if d > 0.06 and p['kind'] != 'static':
            warn.append(f'{k}: pivot {d:.3f} m away from its mesh')
        if (Vector(o.matrix_world.translation) - Vector(p['pivot'])).length > 1e-3:
            bad.append(f'{k}: object origin != pivot')
    if p.get('axis') is not None and abs(Vector(p['axis']).length - 1) > 1e-3:
        bad.append(f'{k}: axis not unit')
# 2. sockets: parents exist, hand sockets near their part
for k, s in S.items():
    if s['parent'] and s['parent'] not in O:
        bad.append(f'socket {k}: parent {s["parent"]} missing')
    if s['kind'] == 'hand' and s['parent'] in O and O[s['parent']].type == 'MESH':
        lo, hi = bbox(O[s['parent']])
        d = dist_box(np.array(s['pos']), lo, hi)
        if d > 0.05:
            warn.append(f'{k}: {d:.3f} m from {s["parent"]}')
# 3. lights inside / at their lens
for l in L:
    lo, hi = bbox(O[l['lens']])
    d = dist_box(np.array(l['position']), lo - 0.002, hi + 0.002)
    print('light', l['socket'], 'to lens', round(d, 3))
    if d > 0.03:
        bad.append(f'{l["socket"]} {d:.3f} m from its lens')
# 4. sweeps
statics = [o for o in O if o.type == 'MESH' and not o.name.startswith(('COL_', 'Snow_'))]


def bvh_of(o, M=None):
    M = M or o.matrix_world
    return BVHTree.FromPolygons([tuple(M @ v.co) for v in o.data.vertices], [tuple(pp.vertices) for pp in o.data.polygons])


def sweep(name, angles, ignore=()):
    p = P[name]
    o = O[name]
    piv, ax = Vector(p['pivot']), Vector(p['axis'])
    kids = [o] + [c for c in o.children_recursive if c.type == 'MESH' and not c.name.startswith('COL_')]
    others = [s for s in statics if s not in kids and s.name not in ignore and s.name != (o.parent.name if o.parent else '')]
    tree_o = {s.name: bvh_of(s) for s in others}
    hits = set()
    for a in angles:
        R = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(a), 4, ax) @ Matrix.Translation(-piv)
        for kid in kids:
            t = bvh_of(kid, R @ kid.matrix_world)
            for nm, tr in tree_o.items():
                if t.overlap(tr):
                    hits.add((nm, a))
    first = {}
    for nm, a in sorted(hits, key=lambda t: t[1]):
        first.setdefault(nm, a)
    return first


for name, angles, ign in (('Door_R', range(5, 171, 5), ()), ('Door_L', range(5, 171, 5), ()),
                          ('Board_Door', range(5, 101, 5), ()), ('Window_Shutter', range(5, 181, 5), ()),
                          ('Door_Hasp', range(5, 171, 5), ()), ('Louvre_Lever', range(5, 76, 5), ()),
                          ('Louvre_Blade_3', range(5, 76, 10), ()), ('Window_Latch', range(5, 91, 5), ()),
                          ('Board_Changeover', (-60, -30, 30, 60), ()), ('DayTank_Valve', range(10, 91, 10), ()),
                          ('Gen_Breaker', (20, 40, 60), ()), ('Board_Brk_Gen', (20, 40, 60), ()),
                          ('Board_MCB_1', (20, 40, 60), ()), ('Light_Switch', (25, 50), ()),
                          ('Engine_StopLever', (20, 40), ()), ('Exhaust_Flap', (35, 70), ()),
                          ('Radiator_Cap', (90, 180), ()), ('DrumPump_Crank', range(0, 360, 30), ())):
    f = sweep(name, angles, ign)
    print('sweep', name, f or 'clear')
    if f:
        warn.append(f'{name} touches {f}')
# 5. hide points: the eye free of colliders, the hip above the floor
cols = {c['name']: c for c in C['colliders']}


def in_col(p):
    out = []
    for n, c in cols.items():
        if c.get('rotation'):
            continue
        cb, sz = np.array(c['center_body']), np.array(c['size'])
        if np.all(np.abs(np.array(p) - cb) <= sz / 2):
            out.append(n)
    return out


for k, s in S.items():
    if s['kind'] == 'hide':
        print('hide', k, 'eye in', in_col(s['eye']) or 'free', 'hip in', in_col(s['pos']) or 'free')
        if in_col(s['eye']):
            bad.append(f'{k}: eye inside a collider')
# 6. moving parts' rest boxes vs static colliders (a part buried in a collider can't be grabbed)
for k, p in P.items():
    if p['kind'] in ('static',) or k not in O or O[k].type != 'MESH' or k.startswith(('Needle_', 'GLamp', 'BLamp', 'Lens')):
        continue
    lo, hi = bbox(O[k])
    c = (lo + hi) / 2
    inside = [n for n in in_col(c) if not n.startswith(('COL_Door', 'COL_Shutter', 'COL_Board_Door'))]
    if inside:
        warn.append(f'{k} centre inside {inside}')
print('PARTS', len(P), 'SOCKETS', len(S), 'COLLIDERS', len(cols))
print('WARN', len(warn))
for w in warn:
    print('  ', w)
print('PROBLEMS', bad or 'none')
