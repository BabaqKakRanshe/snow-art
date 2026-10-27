"""v1.1: the hut door against the porch of forest_hut_yard (HutPorch, read from its yard.blend, never written):
the porch at its scene place (the TowerHut prefab's local (0, 0, 1.2) Unity = (0, -1.2, 0) in the hut frame), the door
IX_HutDoor_1 swept 0..105 deg; for every step the overlap with the porch (BVH) and the clearance to each porch piece
(edges of both sampled every 1 cm); the hut's other meshes against the porch at rest (bench, block, trims...).
python3 -I porch_fit.py [--draft] YARD_BLEND  -> porch_fit{_draft}.json next to this script"""
import bpy, json, math, os, sys
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

SUF = '_draft' if '--draft' in sys.argv else ''
YARD = [a for a in sys.argv if a.endswith('yard.blend')][0]
HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, '..', 'out', f'hut{SUF}.blend'))
C = json.load(open(os.path.join(HERE, '..', 'out', f'hut_contract{SUF}.json')))
PORCH_AT = Matrix.Translation((0.0, -1.2, 0.0))

with bpy.data.libraries.load(YARD, link=False) as (src, dst):
    dst.objects = ['HutPorch']
porch = dst.objects[0]
bpy.context.scene.collection.objects.link(porch)
porch.parent = None
porch.matrix_world = PORCH_AT
bpy.context.view_layer.update()


def mesh_world(o, M=None):
    me = o.data
    me.calc_loop_triangles()
    M = M if M is not None else o.matrix_world
    V = [M @ v.co for v in me.vertices]
    T = [tuple(t.vertices) for t in me.loop_triangles]
    E = [tuple(e.vertices) for e in me.edges]
    return V, T, E


PV, PT, PE = mesh_world(porch)
PB = BVHTree.FromPolygons(PV, PT)
# porch pieces = connected components (for naming the nearest piece)
comp = list(range(len(PV)))


def find(a):
    while comp[a] != a:
        comp[a] = comp[comp[a]]
        a = comp[a]
    return a


for a, b in PE:
    ra, rb = find(a), find(b)
    if ra != rb:
        comp[ra] = rb
groups = {}
for i in range(len(PV)):
    groups.setdefault(find(i), []).append(i)


def piece_name(vids):
    xs = [PV[i].x for i in vids]; ys = [PV[i].y for i in vids]; zs = [PV[i].z for i in vids]
    x0, x1, y0, y1, z0, z1 = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    if z0 > 2.1 and (x1 - x0) < 0.06:
        return f'rafter x {(x0 + x1) / 2:+.2f}'
    if z0 > 2.3 and (y1 - y0) < 0.07:
        return 'wall plate'
    if z0 > 2.1 and (y1 - y0) > 1.0:
        return 'roof sheet'
    if z0 > 2.0 and (x1 - x0) > 2.0:
        return 'beam / fascia'
    if (x1 - x0) < 0.12 and (z1 - z0) > 1.5:
        return f'post x {(x0 + x1) / 2:+.2f}'
    if 1.6 < z0 < 2.0:
        return f'knee brace x {(x0 + x1) / 2:+.2f}'
    if 0.3 < z1 < 0.8 and x0 > 0.5:
        return 'bench'
    if z1 <= 0.33:
        return 'deck / step / piers'
    return f'piece {x0:+.2f}..{x1:+.2f} {y0:+.2f}..{y1:+.2f} {z0:.2f}..{z1:.2f}'


tri_piece = {}
for gi, vids in groups.items():
    nm = piece_name(vids)
    for i in vids:
        tri_piece[i] = nm


def sample_edges(V, E, step=0.01):
    pts = []
    for a, b in E:
        pa, pb = V[a], V[b]
        n = max(1, int((pb - pa).length / step))
        for k in range(n + 1):
            pts.append(pa.lerp(pb, k / n))
    return pts


def clearance(V, T, E):
    """min distance between the two meshes (edges of each sampled against the other) and the nearest porch piece"""
    B = BVHTree.FromPolygons(V, T)
    best = (9.0, None)
    for p in sample_edges(V, E):
        loc, nrm, idx, d = PB.find_nearest(p, 1.0)
        if loc is not None and d < best[0]:
            best = (d, tri_piece[PT[idx][0]])
    for p in sample_edges(PV, PE):
        loc, nrm, idx, d = B.find_nearest(p, 1.0)
        if loc is not None and d < best[0]:
            best = (d, tri_piece[find_vertex(p)])
    return best


PVA = np.array([tuple(v) for v in PV])


def find_vertex(p):
    i = int(np.argmin(((PVA - np.array(tuple(p))) ** 2).sum(1)))
    return i


# the door and everything on it
door = bpy.data.objects['IX_HutDoor_1']
names = [door.name] + [c.name for c in door.children_recursive if c.type == 'MESH' and not c.name.startswith(('COL_', 'LIGHT_'))]
dp = C['parts']['IX_HutDoor_1']
piv, ax = Vector(dp['pivot']), Vector(dp['axis']).normalized()
lo, hi = dp['range']
dm = [(bpy.data.objects[n], mesh_world(bpy.data.objects[n])) for n in names]
# one BVH per porch piece (the clearance to each piece through the whole travel)
PIECES = {}
for gi, vids in groups.items():
    PIECES.setdefault(tri_piece[vids[0]], set()).update(vids)
PB_PIECE = {}
for nm, vids in PIECES.items():
    tris = [t for t in PT if t[0] in vids]
    PB_PIECE[nm] = BVHTree.FromPolygons(PV, tris)
PIECE_SAMPLES = {nm: [p for (a, b) in PE if a in vids for p in sample_edges(PV, [(a, b)])] for nm, vids in PIECES.items()}
piece_min = {nm: (9.0, None) for nm in PIECES}
out = dict(steps=[], worst=None, rest={})
worst = (9.0, None, None)
for a in np.arange(lo, hi + 0.001, 0.5):
    R = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(a), 4, ax) @ Matrix.Translation(-piv)
    V, T, E = [], [], []
    for o, (v, t, e) in dm:
        off = len(V)
        V += [R @ p for p in v]
        T += [(i + off, j + off, k + off) for i, j, k in t]
        E += [(i + off, j + off) for i, j in e]
    B = BVHTree.FromPolygons(V, T)
    hits = B.overlap(PB)
    d, piece = clearance(V, T, E)
    DS = sample_edges(V, E)
    for nm, bv in PB_PIECE.items():
        m = piece_min[nm][0]
        for q in DS:
            loc, nrm, idx, dd = bv.find_nearest(q, 0.5)
            if loc is not None and dd < m:
                m = dd
        for q in PIECE_SAMPLES[nm]:
            loc, nrm, idx, dd = B.find_nearest(q, 0.5)
            if loc is not None and dd < m:
                m = dd
        if m < piece_min[nm][0]:
            piece_min[nm] = (m, float(a))
    out['steps'].append(dict(angle=float(a), overlaps=len(hits), clearance=round(d, 4), nearest=piece))
    if len(hits) or d < worst[0]:
        if len(hits):
            worst = (-1.0, float(a), sorted({tri_piece[PT[j][0]] for i, j in hits}))
        elif worst[0] >= 0:
            worst = (d, float(a), piece)
out['worst'] = worst
# the hut's own meshes at rest against the porch (overlaps only, per object and porch piece); the porch moved 1 mm off
# the facade so that its back resting on the cladding does not count
PB_OFF = BVHTree.FromPolygons([p + Vector((0, -0.001, 0)) for p in PV], PT)
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name.startswith(('COL_', 'LIGHT_')) or o == porch or o.name in names:
        continue
    v, t, e = mesh_world(o)
    if not t:
        continue
    hits = BVHTree.FromPolygons(v, t).overlap(PB_OFF)
    if hits:
        out['rest'][o.name] = sorted({tri_piece[PT[j][0]] for i, j in hits})
print('worst over the swing:', worst)
mins = {}
for s in out['steps']:
    k = s['nearest']
    if k not in mins or s['clearance'] < mins[k][0]:
        mins[k] = (s['clearance'], s['angle'])
for k, (d, a) in sorted(mins.items(), key=lambda kv: kv[1][0]):
    print(f'  nearest {k}: {d * 100:.1f} cm at {a:.1f} deg')
print('overlap steps:', sum(1 for s in out['steps'] if s['overlaps']))
out['piece_min'] = {k: [round(v[0], 4), v[1]] for k, v in piece_min.items()}
for k, (d, a) in sorted(piece_min.items(), key=lambda kv: kv[1][0]):
    if d < 0.5:
        print(f'  clearance to {k}: {d * 100:.1f} cm (at {a:.1f} deg)')
print('at rest, hut meshes touching the porch:', out['rest'])
json.dump(out, open(os.path.join(HERE, f'porch_fit{SUF}.json'), 'w'), indent=1)
