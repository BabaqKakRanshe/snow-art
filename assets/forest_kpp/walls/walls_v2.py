"""KPP v2 walls: the PO-2 walls of Forest Update 7 at the base gate and at the checkpoint barrier as one straight line at
one height, with the gate's end posts, and the Terrain levelling strips Unity applies under them.

  gate:    the gate's v2 end posts (0.30 x 0.30) stand in the wall line at Blender x -7.45..-7.15 (east) and +0.15..+0.45
           (west). The west run (the leaf's parking side) now starts at the west post (+0.45): its start socket moves there
           from +2.925 and one panel more fills the place of v1's chain-link fixed panel; its next five panels are re-spaced
           (2.448 m) to meet U7's joint at +15.138. The east run ends at the east post (-7.45): its seven panels nearest the
           gate are re-spaced (2.536 m) to meet U7's joint at -25.202. Every other piece keeps its place.
  barrier: the wings keep their places (the v2 pad, cabinet, rest post and conduit clear them - see clearances).
  levelling: one strip along each wall line, flat at the gate's / the relocated checkpoint's height, half width 2.0 m,
           a 3.0 m smoothstep across, linear ramps along the line at both ends (as long as needed for steps <= 0.10 m
           between neighbouring panels); every U7 piece whose ground changes gets its height again by U7's own rules on
           the levelled ground (panels: the ground at the centre; sockets: at the socket; FBS: on the ground, the upper
           one 0.58 higher; cubes, coils, signs: at the centre; teeth: min(centre, corners + 0.22)).
python3 -I walls_v2.py  ->  u7_layout_v2.json, diff.json, levelling.json, walls_v2_data.json (for plans_v2.py)"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
U7 = '/home/claude/uaz/out/forest_update7/u7_layout.json'
LAYOUT = '/home/claude/uaz/out/forest_update6/stage/Assets/Locations/Forest/Data/Forest_Layout.json'
TERR = '/home/claude/fence/game_terrain_1_1.npy'
FIRST = 5649                                 # u7.records.first: record i is rocks[5649 + i] in Forest_Layout.json
U = json.load(open(U7))
L = json.load(open(LAYOUT))
H0 = np.load(TERR)                           # [z, x] metres, tile 1_1 (x 0..600, z -600..0)
X0, Z0, T_ = 0.0, -600.0, 600.0
STEP = T_ / (H0.shape[0] - 1)


# ---------------------------------------------------------------- frames
def yaw_of(q):
    return math.degrees(2 * math.atan2(q[1], q[3]))


def ux_of(yaw):
    t = math.radians(yaw)
    return np.array([math.cos(t), -math.sin(t)])


def uz_of(yaw):
    t = math.radians(yaw)
    return np.array([math.sin(t), math.cos(t)])


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


G_P = np.array([313.23465, -309.11115])
G_H = 16.018454
G_YAW = yaw_of([0.0, 0.069757, 0.0, 0.997564])          # 8.0
G_X, G_Y = -ux_of(G_YAW), -uz_of(G_YAW)                   # the Gate root's Blender +x (west), +y (inside) in the world
B_P = np.array(U['barrier']['post'])
B_ARM = unit(np.array(U['barrier']['rest']) - B_P)       # the barrier's Blender +x: post -> rest
B_IN = unit(U['barrier']['road_in'])                     # its Blender +y: to the booth / base
B_H = 9.27351                                            # the relocation's flat height (ForestRelocationStep)
# checks against the U7 data
assert abs((np.array(U['gate']['west_end']) - G_P) @ G_X - 2.925) < 1e-6
assert abs((np.array(U['gate']['east_end']) - G_P) @ G_X + 7.90) < 1e-6
assert abs(B_ARM @ B_IN) < 1e-6 and (np.array(U['barrier']['booth']) - B_P) @ B_IN > 0


def gw(bx, by=0.0):
    return G_P + G_X * bx + G_Y * by


def bw(bx, by=0.0):
    return B_P + B_ARM * bx + B_IN * by


def gl(p):
    d = np.asarray(p, float) - G_P
    return np.array([d @ G_X, d @ G_Y])


def bl(p):
    d = np.asarray(p, float) - B_P
    return np.array([d @ B_ARM, d @ B_IN])


# ---------------------------------------------------------------- the ground, before and after the levelling
def sample(H, x, z):
    u, v = (x - X0) / STEP, (z - Z0) / STEP
    i0, j0 = int(np.floor(u)), int(np.floor(v))
    fu, fv = u - i0, v - j0
    return float((H[j0, i0] * (1 - fu) + H[j0, i0 + 1] * fu) * (1 - fv) + (H[j0 + 1, i0] * (1 - fu) + H[j0 + 1, i0 + 1] * fu) * fv)


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


HW, FP = 2.0, 3.0                                        # half width, falloff across


def strip_w(st, x, z):
    """weight of a strip at world points x, z (arrays): 1 on the flat, smoothstep across, linear along beyond the ends"""
    A, Bp = np.array(st['A']), np.array(st['B'])
    d = Bp - A
    Ln = float(np.linalg.norm(d))
    u = d / Ln
    v = np.array([-u[1], u[0]])
    px, pz = x - A[0], z - A[1]
    s = px * u[0] + pz * u[1]
    t = np.abs(px * v[0] + pz * v[1])
    w_perp = np.where(t <= HW, 1.0, smooth((HW + FP - t) / FP))
    w_al = np.where(s < 0, np.clip(1.0 + s / st['ramp_start'], 0, 1), np.where(s > Ln, np.clip(1.0 - (s - Ln) / st['ramp_end'], 0, 1), 1.0))
    return w_perp * w_al


def level(strips):
    H = H0.copy()
    for st in strips:
        A, Bp = np.array(st['A']), np.array(st['B'])
        pad = HW + FP + max(st['ramp_start'], st['ramp_end']) + 1.0
        lo, hi = np.minimum(A, Bp) - pad, np.maximum(A, Bp) + pad
        j0, j1 = int((lo[0] - X0) / STEP), int((hi[0] - X0) / STEP) + 2
        i0, i1 = int((lo[1] - Z0) / STEP), int((hi[1] - Z0) / STEP) + 2
        xs = X0 + np.arange(j0, j1) * STEP
        zs = Z0 + np.arange(i0, i1) * STEP
        XX, ZZ = np.meshgrid(xs, zs)
        w = strip_w(st, XX, ZZ)
        H[i0:i1, j0:j1] = H[i0:i1, j0:j1] + w * (st['height'] - H[i0:i1, j0:j1])
    return H


# ---------------------------------------------------------------- the records
recs = [dict(r) for r in U['records']]
for r in recs:
    r['p'] = list(r['p'])
orig = [json.loads(json.dumps(r)) for r in U['records']]
IDX = {FIRST + i: i for i in range(len(recs))}


def rec(idx):
    return recs[IDX[idx]]


changed_why = {}                                          # record index -> reasons
added = []                                                # new records (appended)


def note(i, why):
    changed_why.setdefault(i, [])
    if why not in changed_why[i]:
        changed_why[i].append(why)


# ---- the gate: the runs end at the v2 posts
POST_E, POST_W = (-7.45, -7.15), (0.15, 0.45)
RUN_W0, RUN_E0 = POST_W[1], POST_E[0]                     # the runs' ends at the posts
runW, runE = U['runs']['N_west'], U['runs']['N_east']
sW, sE = runW['spacing'], runE['spacing']
outer = np.array(runW['outer'])
assert np.allclose(outer, runE['outer']) and np.allclose(outer, -G_Y, atol=1e-6)
# west: U7's start socket 5649 at +2.925, panels 5650..5654 (centres +4.146 .. +13.917), joint +15.138 kept
w_joint = float(gl([rec(5655)['p'][0], rec(5655)['p'][2]])[0]) - sW / 2   # +15.1386: 5655's joint
west_ids = [5650, 5651, 5652, 5653, 5654]
for k, idx in enumerate(west_ids):
    assert abs(gl([rec(idx)['p'][0], rec(idx)['p'][2]])[0] - (2.925 + (k + 0.5) * sW)) < 0.02, idx
assert rec(5649)['m'] == 'ConcreteFence_Socket' and abs(gl([rec(5649)['p'][0], rec(5649)['p'][2]])[0] - 2.925) < 1e-3
nW = 6
sW2 = (w_joint - RUN_W0) / nW
cW = [RUN_W0 + (i + 0.5) * sW2 for i in range(nW)]
# east: panels 5703..5697 (centres -9.136 .. -23.966), joint -25.202 kept
e_joint = float(gl([rec(5696)['p'][0], rec(5696)['p'][2]])[0]) + sE / 2   # -25.202: 5696's joint
east_ids = [5703, 5702, 5701, 5700, 5699, 5698, 5697]
for k, idx in enumerate(east_ids):
    assert abs(gl([rec(idx)['p'][0], rec(idx)['p'][2]])[0] - (-7.90 - (k + 0.5) * sE)) < 0.02, idx
nE = 7
sE2 = (RUN_E0 - e_joint) / nE
cE = [RUN_E0 - (i + 0.5) * sE2 for i in range(nE)]
q_run = rec(5650)['q']
assert all(np.allclose(rec(i)['q'], q_run, atol=2e-6) for i in west_ids + east_ids + [5649])   # the runs' own q kept


def offset(i, n_, s, kept_out):
    """U7: panels closer than 2.48 m overlap at the joints, every other one 12 mm out (to the outside, -y here); the new
    ones alternate so that the last of them differs from the kept panel next to it"""
    if s >= 2.48:
        return 0.0
    p_ = (n_ - 1 - i) % 2
    out_ = (p_ == 1) if kept_out else (p_ == 0)
    return -0.012 if out_ else 0.0


def kept_offset(idx):
    p = rec(idx)['p']
    return round(float(gl([p[0], p[2]])[1]), 3)


# west: the new socket and panels (ids: 5649 the socket, a new panel next to the post, then 5650..5654)
off_next_W = kept_offset(5655)
p = gw(RUN_W0, 0.0)
rec(5649)['p'] = [round(float(p[0]), 4) + 0.0, None, round(float(p[1]), 4) + 0.0]
note(IDX[5649], 'gate v2: the west run starts at the west post (+0.45 instead of +2.925)')
west_slots = []
for i, c in enumerate(cW):
    by = offset(i, nW, sW2, off_next_W < -0.006)
    p = gw(c, by)
    west_slots.append((c, by, p))
new_W = dict(m='ConcreteFence', p=[round(float(west_slots[0][2][0]), 4) + 0.0, None, round(float(west_slots[0][2][1]), 4) + 0.0],
             q=list(q_run), group='perimeter')
added.append((new_W, 'gate v2: the panel between the west post and the old run start (v1 had the gate\'s chain-link fixed panel '
                      'there)', 0.0))
for (c, by, p), idx in zip(west_slots[1:], west_ids):
    r = rec(idx)
    r['p'] = [round(float(p[0]), 4) + 0.0, None, round(float(p[1]), 4) + 0.0]
    note(IDX[idx], 're-spaced %.4f -> %.4f m to meet the west post' % (sW, sW2))
# east
off_next_E = kept_offset(5696)
for i, (c, idx) in enumerate(zip(cE, east_ids)):
    by = offset(i, nE, sE2, off_next_E < -0.006)
    p = gw(c, by)
    r = rec(idx)
    r['p'] = [round(float(p[0]), 4) + 0.0, None, round(float(p[1]), 4) + 0.0]
    note(IDX[idx], 're-spaced %.4f -> %.4f m to end at the east post' % (sE, sE2))

# ---- the strips: flat parts from the posts / the wing roots out to the joint nearest 15 m; ramps chosen below
g_flat0 = RUN_E0 - 6 * sE2                                # the east joint 15.2 m from the post
g_flat1 = w_joint                                         # +15.138: 14.7 m from the west post
b_flat0, b_flat1 = -0.90 - 15.0, 6.25 + 15.0              # the wings' joints 15 m from their roots
STRIPS = [dict(name='gate', A=gw(g_flat0).tolist(), B=gw(g_flat1).tolist(), height=G_H, local=(g_flat0, g_flat1),
               frame='gate'),
          dict(name='barrier', A=bw(b_flat0).tolist(), B=bw(b_flat1).tolist(), height=B_H, local=(b_flat0, b_flat1),
               frame='barrier')]


# ---------------------------------------------------------------- heights by U7's rules on a ground H
FOOT = {'ConcreteFence': (1.25, 0.12), 'ConcreteFence_b': (1.25, 0.12), 'ConcreteFence_Broken': (1.25, 0.12),
        'ConcreteFence_Sign': (1.25, 0.12), 'ConcreteFence_Plain': (1.25, 0.12), 'ConcreteFence_Wicket': (1.25, 0.12),
        'ConcreteFence_Socket': (0.48, 0.38), 'TankTooth': (0.5, 0.5), 'TankTooth_b': (0.5, 0.5),
        'RoadBlock_FBS': (1.19, 0.20), 'RoadBlock_Jersey': (1.0, 0.31), 'RoadBlock_Jersey_Striped': (1.0, 0.31),
        'RoadBlock_Cube': (0.5, 0.5), 'WireCoil': (2.5, 0.48), 'WireBarricade': (1.5, 0.75), 'Hedgehog': (0.8, 0.8),
        'Abatis': (4.3, 1.35), 'Abatis_b': (3.8, 1.3), 'Sign_Halt': (0.62, 0.10), 'Sign_NoEntry': (0.30, 0.08)}
FOOT_OFF = {'Abatis': -0.55, 'Abatis_b': -0.75}
PANELS = ('ConcreteFence', 'ConcreteFence_b', 'ConcreteFence_Broken', 'ConcreteFence_Sign', 'ConcreteFence_Plain',
          'ConcreteFence_Wicket')


def y_rule(r, H, i):
    m = r['m']
    c = np.array([r['p'][0], r['p'][2]], float)
    if m in PANELS:
        # U7 took the ground at the panel's centre on the run line (the 12 mm offset is applied after); the offset moves
        # the sample by 12 mm, far under the heightmap's 0.59 m: sampled where the panel stands
        return sample(H, *c)
    if m == 'RoadBlock_FBS':
        lower = [j for j, o in enumerate(recs) if o['m'] == 'RoadBlock_FBS' and j != i and
                 abs(o['p'][0] - r['p'][0]) < 1e-3 and abs(o['p'][2] - r['p'][2]) < 1e-3]
        base = sample(H, *c)
        if lower and orig[i]['p'][1] > orig[lower[0]]['p'][1]:
            return base + 0.58
        return base
    if m in ('TankTooth', 'TankTooth_b'):
        yaw = yaw_of(r['q'])
        ux, uz = ux_of(yaw), uz_of(yaw)
        gs = [sample(H, *(c + ux * sx * 0.5 + uz * sz * 0.5)) for sx in (-1, 1) for sz in (-1, 1)]
        return min(sample(H, *c), min(gs) + 0.22)
    return sample(H, *c)


def influence(st, c, rad):
    """does the strip's modified area reach a piece of radius rad at c"""
    A, Bp = np.array(st['A']), np.array(st['B'])
    d = Bp - A
    Ln = float(np.linalg.norm(d))
    u = d / Ln
    v = np.array([-u[1], u[0]])
    s, t = (c - A) @ u, abs((c - A) @ v)
    return (t - rad < HW + FP) and (-st['ramp_start'] - rad < s < Ln + st['ramp_end'] + rad)


def flat_at(st, c):
    A, Bp = np.array(st['A']), np.array(st['B'])
    d = Bp - A
    Ln = float(np.linalg.norm(d))
    u = d / Ln
    v = np.array([-u[1], u[0]])
    s, t = (c - A) @ u, abs((c - A) @ v)
    return t <= HW and 0 <= s <= Ln


def heights(strips):
    """the records' heights on the levelled ground: (H levelled, list of new y per record, new y of the added)"""
    H = level(strips)
    ys = []
    for i, r in enumerate(recs):
        c = np.array([r['p'][0], r['p'][2]])
        rad = math.hypot(*FOOT[r['m']]) + 0.6
        moved = r['p'][1] is None
        hit = [st for st in strips if influence(st, c, rad)]
        if not hit and not moved:
            ys.append(orig[i]['p'][1])
            continue
        flat = [st for st in hit if flat_at(st, c)]
        if flat and r['m'] in PANELS + ('ConcreteFence_Socket',):
            y = flat[0]['height']
        else:
            y = y_rule(r, H, i)
        ys.append(y)
    ya = []
    for r, why, _ in added:
        c = np.array([r['p'][0], r['p'][2]])
        flat = [st for st in strips if flat_at(st, c)]
        ya.append(flat[0]['height'] if flat else sample(H, *c))
    return H, ys, ya


def run_panels(frame, lo, hi):
    """(local x, record index) of the PO-2 panels of a wall line between lo and hi, sorted"""
    out = []
    for i, r in enumerate(recs):
        if r['m'] not in PANELS:
            continue
        c = np.array([r['p'][0], r['p'][2]])
        lx, ly = (gl(c) if frame == 'gate' else bl(c))
        if abs(ly) < 0.05 and lo <= lx <= hi:
            out.append((float(lx), i))
    return sorted(out)


# ---- the ramps: the shortest (whole panels, 2.5 m) with every step between neighbouring panels <= 0.10 m
def steps_along(frame, lo, hi, ys, ya):
    pts = []
    for lx, i in run_panels(frame, lo, hi):
        pts.append((lx, ys[i]))
    for (r, why, _), y in zip(added, ya):
        c = np.array([r['p'][0], r['p'][2]])
        lx, ly = (gl(c) if frame == 'gate' else bl(c))
        if frame == ('gate' if r['group'] == 'perimeter' else 'barrier') and lo <= lx <= hi and abs(ly) < 0.05:
            pts.append((float(lx), y))
    pts.sort()
    return pts


CAP = 12.5
choice = {}


def u7_y(lx, frame):
    """U7's height of the panel nearest local x on the same line (before any change)"""
    best = None
    for i, o in enumerate(orig):
        if o['m'] not in PANELS:
            continue
        c = np.array([o['p'][0], o['p'][2]])
        x_, y_ = (gl(c) if frame == 'gate' else bl(c))
        if abs(y_) < 0.05 and (best is None or abs(x_ - lx) < best[0]):
            best = (abs(x_ - lx), o['p'][1])
    return best[1]


for st in STRIPS:
    st['ramp_start'] = st['ramp_end'] = 2.5
for st in STRIPS:
    a, b = st['local']
    for end, key in ((a, 'ramp_start'), (b, 'ramp_end')):
        best = None
        for fe in (2.5, 5.0, 7.5, 10.0, CAP):
            st[key] = fe
            Hh, ys, ya = heights(STRIPS)
            # from the last flat panel to the first panel past the ramp: every step <= 0.10 m, or no worse than U7's own
            # step at that joint (the ground beyond the ramp is the U7 ground)
            lo, hi = (end - fe - 2.6, end + 1.3) if key == 'ramp_start' else (end - 1.3, end + fe + 2.6)
            pts = steps_along(st['frame'], lo, hi, ys, ya)
            worst = 0.0
            for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
                old_step = abs(u7_y(x2, st['frame']) - u7_y(x1, st['frame']))
                worst = max(worst, abs(y2 - y1) - max(0.10, old_step + 0.005))
            mx = max(abs(y2 - y1) for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]))
            if best is None or worst < best[1] - 1e-4:
                best = (fe, worst, mx)
            if worst <= 0.0:
                break
        st[key] = best[0]
        choice[(st['name'], key)] = (st[key], round(best[2], 3), 'ok' if best[1] <= 0 else 'over by %.3f' % best[1])
print('ramps', choice)

Hh, ys, ya = heights(STRIPS)

# ---------------------------------------------------------------- write the heights, the changes
TOL = 0.001
for i, (r, y) in enumerate(zip(recs, ys)):
    old = orig[i]['p'][1]
    if r['p'][1] is None:
        r['p'][1] = round(float(y), 4) + 0.0
        note(i, 'height %.4f -> %.4f' % (old, r['p'][1]))
    elif abs(y - old) >= TOL:
        r['p'][1] = round(float(y), 4) + 0.0
        note(i, 'levelled ground: height %.4f -> %.4f' % (old, r['p'][1]))
for (r, why, _), y in zip(added, ya):
    r['p'][1] = round(float(y), 4) + 0.0
new_idx0 = FIRST + len(recs)
for k, (r, why, _) in enumerate(added):
    recs.append(r)

# ---- trees under new or moved footprints (removed from the data as U7 did), trees and objects in the strips
TRUNK = {'SpruceHC': 0.30, 'Spruce': 0.30, 'Fir': 0.30, 'Pine': 0.30, 'Larch': 0.28, 'Birch': 0.20, 'Dead': 0.20, 'Snag': 0.22}
removed_before = {t['index'] for t in U['removed_trees']}
TREES = [(k, t) for k, t in enumerate(L['trees']) if k not in removed_before]


def in_box(p, c, yaw, hx, hz, pad=0.0):
    rr = np.asarray(p) - c
    return abs(rr @ ux_of(yaw)) <= hx + pad and abs(rr @ uz_of(yaw)) <= hz + pad


new_removed = []
moved = [i for i in changed_why if any(w.startswith(('gate v2', 're-spaced')) for w in changed_why[i])] + \
        list(range(len(orig), len(recs)))
for i in moved:
    r = recs[i]
    yaw = yaw_of(r['q'])
    hx, hz = FOOT[r['m']]
    c = np.array([r['p'][0], r['p'][2]])
    for k, t in TREES:
        if abs(t['p'][0] - c[0]) > 4 or abs(t['p'][2] - c[1]) > 4:
            continue
        rad = TRUNK.get(t['m'].split('_')[0], 0.0) * t.get('s', 1.0)
        if in_box([t['p'][0], t['p'][2]], c, yaw, hx + 0.15, hz + 0.15, pad=rad + (0.10 if rad > 0 else 0.0)):
            if k not in [n['index'] for n in new_removed]:
                new_removed.append(dict(list='trees', m=t['m'], p=t['p'], index=int(k), why='gate v2 ' + r['m']))
print('trees under the new / moved pieces:', len(new_removed), [n['m'] for n in new_removed])

dz = Hh - H0
in_strips = {}
for st in STRIPS:
    rows = dict(trees=[], rocks=[], prefabs=[])
    for k, t in TREES:
        c = np.array([t['p'][0], t['p'][2]])
        if influence(st, c, 0.0):
            d_ = sample(Hh, *c) - sample(H0, *c)
            if abs(d_) > 0.005:
                rows['trees'].append((t['m'], round(d_, 3)))
    u7_lo = FIRST
    for k, rr in enumerate(L['rocks']):
        c = np.array([rr['p'][0], rr['p'][2]])
        if influence(st, c, 0.0):
            d_ = sample(Hh, *c) - sample(H0, *c)
            if abs(d_) > 0.005:
                rows['rocks'].append((rr['m'], round(d_, 3)))
    in_strips[st['name']] = dict(trees=len(rows['trees']),
                                 trees_max_dz=max([abs(d) for _, d in rows['trees']], default=0.0),
                                 tree_models=sorted({m.split('_')[0] for m, _ in rows['trees']}),
                                 rocks=len(rows['rocks']), rock_models=sorted({m for m, _ in rows['rocks']}),
                                 rocks_max_dz=max([abs(d) for _, d in rows['rocks']], default=0.0))
print('objects on ground that moves:', in_strips)

# ---------------------------------------------------------------- keepClear for the changed / added pieces
KEEP_MARGIN = 1.0


def keep(r):
    yw = yaw_of(r['q'])
    hx, hz = FOOT[r['m']]
    c = np.array([r['p'][0], r['p'][2]]) - uz_of(yw) * FOOT_OFF.get(r['m'], 0.0)
    ax = ux_of(yw)
    a_, b_ = c - ax * max(hx - hz, 0.0), c + ax * max(hx - hz, 0.0)
    return dict(a=[round(float(a_[0]), 2), round(float(a_[1]), 2)], b=[round(float(b_[0]), 2), round(float(b_[1]), 2)],
                r=round(float(min(hx, hz) + KEEP_MARGIN), 2))


keep_clear = list(U['keep_clear'])
assert len(keep_clear) == len(orig)
for i in changed_why:
    keep_clear[i] = keep(recs[i])
for r in recs[len(orig):]:
    keep_clear.append(keep(r))

# ---------------------------------------------------------------- the clearances at the barrier (v2 pad, cabinet, rest, conduit)
def rect_gap(a, b):
    """gap between axis-aligned rectangles (x0, x1, y0, y1) in a local frame (negative = overlap)"""
    gx = max(a[0] - b[1], b[0] - a[1])
    gy = max(a[2] - b[3], b[2] - a[3])
    return max(gx, gy) if (gx > 0 or gy > 0) else max(gx, gy)


V2_BAR = {'pad': (-0.40, 0.40, -0.40, 0.50), 'cabinet': (-0.18, 0.18, 0.06, 0.38), 'rest pad': (5.40, 5.75, -0.20, 0.20),
          'conduit to the booth (out of the pad, +y)': (-0.22, -0.18, 0.50, 1.12),
          'conduit to the booth (across, y 1.10)': (-1.12, -0.18, 1.08, 1.12),
          'conduit to the booth (to its pad, x -1.10)': (-1.12, -1.08, 1.08, 4.45),
          'conduit to the wall box (out of the pad, -y)': (-0.32, -0.28, -0.64, -0.40),
          'conduit to the wall box (on the ground, y -0.62)': (-1.57, -0.28, -0.64, -0.60),
          'conduit to the wall box (to the panel, x -1.55)': (-1.57, -1.53, -0.64, -0.119),
          'wall box (on the panel face)': (-1.636, -1.464, -0.186, -0.095),
          'camera mast footing (v2.1)': (-1.85, -1.35, 1.25, 1.75),
          'camera cable to the booth (v2.1, x -1.60)': (-1.616, -1.584, 1.75, 4.45)}
bar_pieces = []
for i, r in enumerate(recs[:len(orig)]):
    if r['group'] != 'kpp':
        continue
    c = np.array([r['p'][0], r['p'][2]])
    lx, ly = bl(c)
    if abs(lx) > 12 or abs(ly) > 4:
        continue
    yaw = yaw_of(r['q'])
    hx, hz = FOOT[r['m']]
    # the footprint's extent in the barrier frame (all pieces here are square to it)
    ex = abs(-ux_of(yaw) @ B_ARM) * hx + abs(-uz_of(yaw) @ B_ARM) * hz
    ey = abs(-ux_of(yaw) @ B_IN) * hx + abs(-uz_of(yaw) @ B_IN) * hz
    if r['m'] in PANELS:                                   # a panel's own socket is at its +x end (0.475 x 0.375)
        bx_ = float(-ux_of(yaw) @ B_ARM)
        sx = lx + np.sign(bx_) * 1.25
        bar_pieces.append(('%d %s socket' % (FIRST + i, r['m']), (sx - 0.475, sx + 0.475, ly - 0.375, ly + 0.375)))
        bar_pieces.append(('%d %s' % (FIRST + i, r['m']), (lx - 1.24, lx + 1.24, ly - 0.075, ly + 0.075)))
    elif r['m'] == 'ConcreteFence_Socket':
        bar_pieces.append(('%d %s' % (FIRST + i, r['m']), (lx - 0.475, lx + 0.475, ly - 0.375, ly + 0.375)))
    else:
        bar_pieces.append(('%d %s' % (FIRST + i, r['m']), (lx - ex, lx + ex, ly - ey, ly + ey)))
clear = []
for nm, rr in V2_BAR.items():
    best = min(((rect_gap(rr, b), pn) for pn, b in bar_pieces), key=lambda t: t[0])
    clear.append(dict(what=nm, nearest=best[1], gap=round(best[0], 3)))
print('barrier clearances:', clear)

# the gate: the runs' ends against the posts, the sockets against the rail strip, the cabinet, the pole
V2_GATE = {'east post': (-7.45, -7.15, -0.15, 0.15), 'west post': (0.15, 0.45, -0.15, 0.15),
           'rail strip': (-7.10, 6.80, 0.40, 0.60), 'leaf (parked)': (-0.40, 6.60, 0.46, 0.54),
           'leaf (shut)': (-7.00, 0.00, 0.46, 0.54), 'drive cabinet': (-0.32, -0.02, 0.64, 0.90), 'guide rollers, outer stand': (-0.14, -0.06, 0.33, 0.41), 'guide rollers, inner stand': (0.00, 0.08, 0.59, 0.67),
           'pole (0.5 m round it)': (1.10, 2.10, 1.70, 2.70),
           'camera mast footing (v2.1)': (0.70, 1.20, 1.20, 1.70),
           'camera cable (v2.1, down to y 0.80)': (0.934, 0.966, 0.784, 1.20),
           'camera cable (v2.1, y 0.80 to the drive)': (0.02, 0.966, 0.784, 0.816)}
gate_pieces = []
for i, r in enumerate(recs):
    if r['group'] != 'perimeter':
        continue
    c = np.array([r['p'][0], r['p'][2]])
    lx, ly = gl(c)
    if not (-30 < lx < 24 and abs(ly) < 4):
        continue
    nm = '%d %s' % (FIRST + i, r['m'])
    if r['m'] in PANELS:
        sx = lx + 1.0 * (sW2 if lx > 0 else sE2) / 2 * np.sign(float(-ux_of(yaw_of(r['q'])) @ G_X))
        gate_pieces.append((nm + ' socket', (sx - 0.475, sx + 0.475, ly - 0.375, ly + 0.375)))
        gate_pieces.append((nm, (lx - 1.24, lx + 1.24, ly - 0.075, ly + 0.075)))
    elif r['m'] == 'ConcreteFence_Socket':
        gate_pieces.append((nm, (lx - 0.475, lx + 0.475, ly - 0.375, ly + 0.375)))
gclear = []
for nm, rr in V2_GATE.items():
    cand = [(rect_gap(rr, b), pn) for pn, b in gate_pieces]
    if 'post' in nm:                                      # the post stands on its run's end socket by design
        cand = [(g, pn) for g, pn in cand if 'socket' not in pn.lower()]
    best = min(cand, key=lambda t: t[0])
    gclear.append(dict(what=nm, nearest=best[1], gap=round(best[0], 3)))
print('gate clearances:', gclear)
ends = dict(west=min(b[0] for pn, b in gate_pieces if 'socket' not in pn.lower() and b[0] > 0),
            east=max(b[1] for pn, b in gate_pieces if 'socket' not in pn.lower() and b[1] < -7))
print('panel ends next to the posts (local x):', ends)

# ---------------------------------------------------------------- outputs
out = json.loads(json.dumps(U))
out['records'] = recs
out['keep_clear'] = keep_clear
out['removed_trees'] = U['removed_trees'] + new_removed
west_end, east_end = gw(RUN_W0), gw(RUN_E0)
out['gate']['west_end'] = west_end.tolist()
out['gate']['east_end'] = east_end.tolist()
out['gate']['v2'] = dict(posts=dict(east=gw(-7.30).tolist(), west=gw(0.30).tolist(), size=[0.30, 0.30], height=2.70),
                         note='KPP v2 gate: end posts in the wall line (Blender x -7.45..-7.15 and +0.15..+0.45), the solid leaf '
                              'shut x -7.00..0.00 on a rail 0.50 m inside (strip y 0.40..0.60), parked x -0.40..6.60; the runs '
                              'end at the posts; local frame = the Gate root (x west along the wall, y inside)')
for nm, A_, B_ in (('N_west', None, west_end), ('N_east', east_end, None)):
    rr = out['runs'][nm]
    if A_ is not None:
        rr['A'] = A_.tolist()
    if B_ is not None:
        rr['B'] = B_.tolist()
rw, re_ = out['runs']['N_west'], out['runs']['N_east']
rw['panels'] += 1
rw['length'] = round(float(np.linalg.norm(np.array(rw['B']) - np.array(rw['A']))), 2)
re_['length'] = round(float(np.linalg.norm(np.array(re_['B']) - np.array(re_['A']))), 2)
rw['v2'] = dict(near_gate=dict(panels=nW, spacing=round(sW2, 4), from_local=RUN_W0, to_local=round(w_joint, 3)),
                note='the panels from the west post to the joint at +15.138 re-spaced; the rest as U7')
re_['v2'] = dict(near_gate=dict(panels=nE, spacing=round(sE2, 4), from_local=RUN_E0, to_local=round(e_joint, 3)),
                 note='the panels from the east post to the joint at -25.202 re-spaced; the rest as U7')
lev = []
for st in STRIPS:
    lev.append(dict(name=st['name'], line=[[round(v, 4) for v in st['A']], [round(v, 4) for v in st['B']]],
                    height=st['height'], half_width=HW, falloff=FP, ramp_start=st['ramp_start'], ramp_end=st['ramp_end'],
                    local=[round(st['local'][0], 3), round(st['local'][1], 3)], local_frame=st['frame']))
out['levelling'] = lev
out['frame'] = U['frame'] + '; v2 (KPP v2 walls): the runs at the gate end at its posts, levelled strips (levelling)'
json.dump(out, open(os.path.join(HERE, 'u7_layout_v2.json'), 'w'), indent=1)

diff = dict(note='Forest Update 7 layout -> v2 (KPP v2 walls). id = index in Forest_Layout.json rocks (u7.records.first 5649 + '
                 'the record\'s place in u7_layout.json); added: appended after the last U7 record',
            changed=[], added=[], removed=[], removed_trees=new_removed)
for i in sorted(changed_why):
    o, r = orig[i], recs[i]
    if o['p'] == r['p'] and o['q'] == r['q']:
        continue
    diff['changed'].append(dict(id=FIRST + i, m=r['m'], group=r['group'], old=dict(p=o['p'], q=o['q']),
                                new=dict(p=r['p'], q=r['q']), why='; '.join(changed_why[i])))
for k, (r, why, _) in enumerate(added):
    diff['added'].append(dict(id=new_idx0 + k, m=r['m'], group=r['group'], p=r['p'], q=r['q'], why=why))
json.dump(diff, open(os.path.join(HERE, 'diff.json'), 'w'), indent=1, ensure_ascii=False)
json.dump(dict(note='Terrain levelling strips for Unity (game frame = Forest world, tile 1_1). For every heightmap sample at '
                    'world (x, z): A, B = the line\'s ends, s = the distance along A->B from A, t = the distance across; '
                    'w_across = 1 for t <= half_width, smoothstep((half_width + falloff - t) / falloff) beyond (0 past '
                    'half_width + falloff); w_along = 1 for 0 <= s <= |AB|, 1 + s / ramp_start for s < 0, 1 - (s - |AB|) / '
                    'ramp_end beyond B (linear, clamped 0..1); w = w_across * w_along; h = h + w * (height - h). Then the '
                    'U7 pieces stand on it (u7_layout_v2.json); trees and rocks in the strips follow the ground '
                    '(objects.in_strips)',
               strips=lev, objects=dict(in_strips=in_strips)),
          open(os.path.join(HERE, 'levelling.json'), 'w'), indent=1)
np.save(os.path.join(HERE, 'terrain_levelled_1_1.npy'), Hh.astype(np.float32))
data = dict(gate=dict(P=G_P.tolist(), X=G_X.tolist(), Y=G_Y.tolist(), H=G_H, runW0=RUN_W0, runE0=RUN_E0, sW2=sW2, sE2=sE2,
                      w_joint=w_joint, e_joint=e_joint, clear=gclear, ends=ends),
            barrier=dict(P=B_P.tolist(), X=B_ARM.tolist(), Y=B_IN.tolist(), H=B_H, clear=clear),
            ramps={'%s %s' % k: v for k, v in choice.items()}, strips=lev, in_strips=in_strips)
json.dump(data, open(os.path.join(HERE, 'walls_v2_data.json'), 'w'), indent=1)
print('changed', len(diff['changed']), 'added', len(diff['added']), 'removed', len(diff['removed']), 'trees', len(new_removed))
