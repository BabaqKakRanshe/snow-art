"""Checks of the road prefabs (out/road[_test].blend + road_contract.json), each prefab moved to the origin (its own
frame) in turn:
  u3        every Update 3 prefab of the batch present, one mesh object each, root pivot at the origin; the box against
            Update 3's FBX box (road_u3_data.json)
  backfaces rays from rings of eye points round each prefab (and from above): the first hit must face the eye (Unity culls
            back faces); the chain-link / barbed-wire quads are two-sided by design
  ground    each island (connected faces) of the parts that stand on / lie on the ground reaches the ground: its lowest
            point at most 3 cm above Update 3's terrain under it (road_ground.json); nothing floats
  bridge    the deck: a capsule (r 0.34, h 1.80, step 0.35) walks from road to road; the car's line: both running strips
            continuous (no step > 3 cm, no gap) from road to road; the railing's openings narrower than the capsule
  overlook  the capsule climbs the steps onto the deck; the railing's openings narrower than the capsule
  windfall  the road between the cuts clear: no part of FallenTree / LogCut more than 6 cm over the road corridor
            (FallenTree's frame x 13.0 .. 19.0) - the car drives through (S5)
  europost  at its 48 places the post's buried foot (0.35 m) covers the ground's fall across its footprint; where they stand
python3 -I road_checks.py [--test] -> road_checks.json, prints a summary"""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0, '/home/claude/uaz')
import road_spec as S

SFX = '_test' if '--test' in sys.argv else '_draft' if '--draft' in sys.argv else ''
OUTD = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=f'/home/claude/uaz/out/road{SFX}.blend')
C = json.load(open(f'/home/claude/uaz/out/road_contract{SFX}.json'))
sc = bpy.context.scene
RES = {}
ROOTS = [n for n, p in C['parts'].items() if not p.get('parent')]
MAPM = {n: bpy.data.objects[n].matrix_world.copy() for n in ROOTS}
CUTOUT = ('M_Road_ChainLink', 'M_Road_Barbed')


def solo(name):
    for n in ROOTS:
        o = bpy.data.objects[n]
        if n == name:
            o.matrix_world = Matrix.Identity(4)
            o.hide_set(False)
            o.hide_viewport = False
        else:
            o.matrix_world = MAPM[n]
            o.hide_viewport = True
    bpy.context.view_layer.update()


def bvh_of(name):
    o = bpy.data.objects[name]
    me = o.data
    V = [v.co.copy() for v in me.vertices]
    Pl = [list(p.vertices) for p in me.polygons]
    return BVHTree.FromPolygons(V, Pl), me


# ---------------------------------------------------------------- u3: presence, pivots, boxes
want = list(S.U3['prefabs']) + ['EuroPost']
u3 = dict(missing=[n for n in want if n not in ROOTS], extra=[n for n in ROOTS if n not in want], boxes={})
for n in ROOTS:
    o = bpy.data.objects[n]
    co = np.array([tuple(v.co) for v in o.data.vertices])
    lo, hi = co.min(0), co.max(0)
    rec = dict(ours=[[round(float(a), 3) for a in lo], [round(float(a), 3) for a in hi]], pivot=C['parts'][n]['pivot'])
    if n in S.U3['u3_models']:
        rec['u3'] = S.U3['u3_models'][n]['bb']
    u3['boxes'][n] = rec
RES['u3'] = u3

# ---------------------------------------------------------------- backfaces
rng = np.random.default_rng(5)
dirs = rng.normal(size=(120, 3))
dirs /= np.linalg.norm(dirs, axis=1)[:, None]
bf = {}
nray = 0
for n in ROOTS:
    solo(n)
    tree, me = bvh_of(n)
    co = np.array([tuple(v.co) for v in me.vertices])
    lo, hi = co.min(0), co.max(0)
    c = (lo + hi) / 2
    R = max(float(np.linalg.norm(hi - lo)) / 2, 0.6)
    eyes = []
    for k, rr in enumerate((R * 1.2 + 1.0, R * 2.0 + 2.0)):
        for zz in (lo[2] + 0.5, c[2], hi[2] + 1.0):
            for a in np.linspace(0, 2 * math.pi, 10, endpoint=False):
                eyes.append(Vector((c[0] + rr * math.cos(a), c[1] + rr * math.sin(a), zz)))
    eyes.append(Vector((c[0], c[1], hi[2] + R + 2.0)))
    for eye in eyes:
        g = S.ground(n, eye.x, eye.y) if n in S.GROUND['prefabs'] else 0.0
        if eye.z < g + 0.3:
            eye.z = g + 0.3
        for d in dirs:
            loc, nrm, idx, dist = tree.ray_cast(eye, Vector(d), 60.0)
            nray += 1
            if loc is None:
                continue
            mat = me.materials[me.polygons[idx].material_index].name if me.materials else '-'
            if mat in CUTOUT:
                continue
            if nrm.dot(Vector(d)) > 0.05:
                pz = int(round(me.attributes['zone'].data[idx].value)) if 'zone' in me.attributes else -1
                e = bf.setdefault(f'{n}|{pz}|{mat}', [0, [round(v, 3) for v in loc], [round(v, 2) for v in eye]])
                e[0] += 1
RES['backfaces'] = dict(rays=nray, bad=bf)

# ---------------------------------------------------------------- ground: the islands that should touch the ground do
import road_kit as RK
CONTACT = {RK.Z_SPOST, RK.Z_BSPOST, RK.Z_EPBODY, RK.Z_CONC, RK.Z_GFOOT, RK.Z_PILE, RK.Z_CRIB, RK.Z_STONE, RK.Z_DFOOT,
           RK.Z_DSTEP, RK.Z_TBARK, RK.Z_TROOT, RK.Z_SAWDUST, RK.Z_SOIL, RK.Z_DRAG, RK.Z_TSTONE}
gres = {}
for n in ROOTS:
    if n not in S.GROUND['prefabs'] and n != 'EuroPost':
        continue
    o = bpy.data.objects[n]
    me = o.data
    za = me.attributes['zone'].data
    # islands over all faces; a contact-zone island is fine if it reaches the ground or touches another island
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    zl = bm.faces.layers.float.get('zone')
    seen = set()
    isl = []
    for f0 in bm.faces:
        if f0.index in seen:
            continue
        comp, st = [], [f0]
        seen.add(f0.index)
        while st:
            f = st.pop()
            comp.append(f)
            for e in f.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        st.append(h)
        vs = {v for f in comp for v in f.verts}
        co = np.array([tuple(v.co) for v in vs])
        isl.append(dict(lo=co.min(0), hi=co.max(0), low=co[co[:, 2].argmin()], zone=int(round(comp[0][zl])) if zl else -1,
                        faces=len(comp)))
    bm.free()
    LO = np.array([i['lo'] for i in isl]) - 0.012
    HI = np.array([i['hi'] for i in isl]) + 0.012
    worst = []
    for k_, i in enumerate(isl):
        if i['zone'] not in CONTACT:
            continue
        low = i['low']
        g = S.ground(n, float(low[0]), float(low[1])) if n in S.GROUND['prefabs'] else 0.0
        gap = float(low[2]) - g
        if gap <= 0.03:
            continue
        touch = np.all((LO <= i['hi'] + 0.012) & (HI >= i['lo'] - 0.012), axis=1)
        touch[k_] = False
        if touch.any():
            continue
        worst.append(dict(zone=i['zone'], gap_m=round(gap, 3), at=[round(float(a), 2) for a in low], faces=i['faces']))
    gres[n] = sorted(worst, key=lambda w: -w['gap_m'])[:8]
RES['ground_floating'] = {k: v for k, v in gres.items() if v}

# ---------------------------------------------------------------- the bridge: capsule walk, the car's strips, the railing
solo('Bridge30')
tree, me = bvh_of('Bridge30')
b = S.BRIDGE


def surf(x, y, top=3.0):
    loc, nrm, idx, d = tree.ray_cast(Vector((x, y, top)), Vector((0, 0, -1)), 20.0)
    gz = S.ground('Bridge30', x, y)
    if loc is None or loc.z < gz:
        return gz, 'ground'
    return loc.z, me.materials[me.polygons[idx].material_index].name


walk = dict(max_step=0.0, holes=[], blocked=[])
for y in np.arange(-1.85, 1.86, 0.25):
    prev = None
    for x in np.arange(-18.0, 18.01, 0.10):
        z, what = surf(x, y)
        if prev is not None and abs(z - prev) > walk['max_step']:
            walk['max_step'] = round(abs(z - prev), 3)
        if prev is not None and abs(z - prev) > 0.35:
            walk['blocked'].append([round(x, 2), round(y, 2), round(z - prev, 3)])
        if what == 'ground' and abs(x) < 14.0:
            walk['holes'].append([round(x, 2), round(y, 2)])
        prev = z
car = {}
for yc in b['strips_y']:
    for dy in (-0.235, 0.0, 0.235):
        zs = []
        prev, worst = None, 0.0
        for x in np.arange(-17.5, 17.51, 0.05):
            z = max(surf(x + dx_, yc + dy)[0] for dx_ in (-0.06, -0.03, 0.0, 0.03, 0.06))
            if prev is not None:
                worst = max(worst, abs(z - prev))
            prev = z
            zs.append(z)
        car[f'{yc + dy:+.3f}'] = dict(max_step_m=round(worst, 4), top_min=round(min(zs[60:-60]), 3), top_max=round(max(zs[60:-60]), 3))
rail = dict(gap_curb_mid=round(b['mid_z'] - b['mid'][1] / 2 - (b['plank_top'] + 0.045 + b['curb'][1]), 3),
            gap_mid_hand=round(b['rail_top'] - b['hand'][1] - (b['mid_z'] + b['mid'][1] / 2), 3),
            gap_deck_mid_outside_curb=round(b['mid_z'] - b['mid'][1] / 2 - b['plank_top'], 3), capsule_d=0.68)
RES['bridge'] = dict(walk=walk, car_strips=car, railing=rail,
                     ok=walk['max_step'] <= 0.35 and not walk['holes'] and all(v['max_step_m'] <= 0.03 for v in car.values()))

# ---------------------------------------------------------------- the overlook: up the steps, onto the deck
solo('OverlookDeck')
tree, me = bvh_of('OverlookDeck')
d = S.DECK
steps = []
prev = None
for y in np.arange(-1.6, 3.0, 0.05):
    z = -1e9
    for dy in (-0.05, -0.025, 0.0, 0.025, 0.05):                     # a foot's length
        loc, nrm, idx, dist = tree.ray_cast(Vector((0.0, y + dy, 4.0)), Vector((0, 0, -1)), 10.0)
        gz = S.ground('OverlookDeck', 0.0, y + dy)
        z = max(z, loc.z if loc is not None and loc.z > gz else gz)
    if prev is not None:
        steps.append(round(z - prev, 3))
    prev = z
prof = [(round(float(y), 2), round(float(z), 3)) for y, z in zip(np.arange(-1.6, 3.0, 0.05), np.cumsum([0] + steps))]
RES['overlook_profile_x0'] = prof
RES['overlook'] = dict(max_rise=max(steps), max_drop=min(steps),
                       rail_gaps=dict(kick_mid=round(d['mid_z'] - d['mid_r'] - (d['top'] + 0.12), 3),
                                      mid_hand=round(d['hand_z'] - d['hand_r'] - (d['mid_z'] + d['mid_r']), 3), capsule_d=0.68),
                       ok=max(steps) <= 0.35)

# ---------------------------------------------------------------- the windfall: the road between the cuts is clear
F = np.array(S.GROUND['prefabs']['FallenTree']['world'])
Lm = np.array(S.GROUND['prefabs']['LogCut']['world'])
worst = []
for n, M in (('FallenTree', np.eye(4)), ('LogCut', np.linalg.inv(F) @ Lm)):
    o = bpy.data.objects[n]
    co = np.array([tuple(v.co) for v in o.data.vertices])
    co = (M[:3, :3] @ co.T).T + M[:3, 3]
    inside = (co[:, 0] > 13.0) & (co[:, 0] < 19.0) & (np.abs(co[:, 1]) < 11.0)
    for p in co[inside]:
        h = p[2] - S.ground('FallenTree', float(p[0]), float(p[1]))
        worst.append((round(float(h), 3), n, [round(float(a), 2) for a in p]))
worst.sort(key=lambda w: -w[0])
RES['windfall'] = dict(max_height_over_road_m=worst[0][0] if worst else None, top=worst[:5],
                       ok=(not worst) or worst[0][0] <= 0.06)

# ---------------------------------------------------------------- the delineators
ep = []
for e in S.GROUND['europosts']:
    g = e['ground']
    fall = max(g.values()) - min(g.values())
    ep.append(fall)
RES['europost'] = dict(count=len(ep), max_fall_across_footprint_m=round(max(ep), 3), buried=S.POST['below'],
                       ok=max(ep) < S.POST['below'] - 0.1)

# ---------------------------------------------------------------- coplanar faces left in one object (z-fighting in the game)
sys.path.insert(0, '/home/claude/uaz')
import bld_common as BC
cop = {}
for n in ROOTS:
    me = bpy.data.objects[n].data
    Fs, buckets = [], {}
    for pg in me.polygons:
        if pg.area < 1e-6:
            continue
        nn = pg.normal.copy()
        pts = [me.vertices[i].co.copy() for i in pg.vertices]
        d_ = nn.dot(pg.center)
        Fs.append((pg.index, nn, d_, pts, pg.material_index))
        buckets.setdefault((round(nn.x * 100), round(nn.y * 100), round(nn.z * 100), round(d_ * 1000)), []).append(len(Fs) - 1)
    cnt = 0
    for key, ids in buckets.items():
        cand = list(ids)
        for dk in (-1, 1):
            cand += buckets.get((key[0], key[1], key[2], key[3] + dk), [])
        for i in ids:
            a_ = Fs[i]
            for j in cand:
                if j <= i:
                    continue
                b_ = Fs[j]
                if a_[1].dot(b_[1]) < 0.999 or abs(a_[2] - b_[2]) > 0.0005:
                    continue
                inter = BC._clip(BC._to2d(a_[3], a_[1]), BC._to2d(b_[3], a_[1]))
                if len(inter) >= 3:
                    ar = abs(sum(inter[q][0] * inter[(q + 1) % len(inter)][1] - inter[(q + 1) % len(inter)][0] * inter[q][1]
                                 for q in range(len(inter)))) / 2
                    if ar > 1e-5:
                        cnt += 1
    if cnt:
        cop[n] = cnt
RES['coplanar_pairs'] = cop
print('coplanar pairs left', cop)
json.dump(RES, open(os.path.join(OUTD, 'road_checks.json'), 'w'), indent=1)
print('u3 missing', u3['missing'], 'extra', u3['extra'])
print('backfaces', nray, 'rays, bad:', {k: v[0] for k, v in sorted(bf.items(), key=lambda kv: -kv[1][0])[:12]})
print('floating', {k: [(w['zone'], w['gap_m']) for w in v[:4]] for k, v in RES['ground_floating'].items()})
print('bridge', RES['bridge']['ok'], walk['max_step'], len(walk['holes']), len(walk['blocked']), car, rail)
print('overlook', RES['overlook'])
print('windfall', RES['windfall']['max_height_over_road_m'], RES['windfall']['top'][:3])
print('europost', RES['europost'])
