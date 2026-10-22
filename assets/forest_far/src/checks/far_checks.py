"""Checks of the far points (out/far.blend + far_contract.json), each prefab moved to the origin (its own frame):
  u3        every Update 3 model present (Dish_1..5 + IX_CabinetDoor_2..6, Radome, RelayMast, MeteoStation, LookoutTower,
            PumpHouse + IX_PumpDoor_7, Chapel + IX_ChapelDoor_8, Cabin + IX_CabinDoor_9, Campsite), the doors' parents and
            pivots as Update 3, the boxes against Update 3's FBX boxes; the hinges (axis, range) as Update 3's
            interactables (Blender axis = -(Unity axis as a position): +angle opens)
  copies    Dish_2 / Dish_5 have Dish_1's UVs and materials loop by loop, Dish_4 Dish_3's (their atlases are shared)
  backfaces rays from rings of eyes round each prefab: the first hit faces the eye (the relay's chain-link and barbed
            wire are two-sided cut-outs)
  floating  connected face islands grouped by touching boxes: every group reaches Update 3's terrain under the prefab
  lights    Update 3's lights and halos at the lens faces (beacons, yard lights, the torch, the candles)
  doors     each door swung 0..max about its hinge (+angle about the contract's axis) against its building: the faces
            that cross (the knuckles round the axis left out); the doorway's clear width and height against the
            player's capsule (r 0.34, h 1.80)
  lookout   the capsule on every tread and landing of Update 3's stairs, on the ship ladder's treads and in the cab:
            nothing above the step height (0.35) inside it - the head room of the climb
  coplanar  overlapping coplanar faces left in one mesh;  uv  the atlas UVs inside 0..1;  the textures
python3 -I far_checks.py [--draft|--test] -> far_checks.json, prints a summary"""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

sys.path.insert(0, '/home/claude/uaz')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import far_spec as S
import far_kit as FK
import chk_common as CC

SFX = '_draft' if '--draft' in sys.argv else '_test' if '--test' in sys.argv else ''
OUTD = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=f'/home/claude/uaz/out/far{SFX}.blend')
C = json.load(open(f'/home/claude/uaz/out/far_contract{SFX}.json'))
RES = {}
ROOTS = [n for n, p in C['parts'].items() if not p.get('parent')]
MAPM = {n: bpy.data.objects[n].matrix_world.copy() for n in ROOTS}
CUTOUT = ('M_Base_ChainLink', 'M_Base_Barbed')
ATLAS = tuple(m.name for m in bpy.data.materials if m.name.startswith('M_Far_'))
U3 = S.U3
ZN = {getattr(FK, k): k for k in dir(FK) if k.startswith('Z_') and isinstance(getattr(FK, k), int)}
CAP_R, CAP_H, STEP = 0.34, 1.80, 0.35


def u2b(p):
    return (-p[0], -p[2], p[1])


def gfn(name):
    return lambda x, y: S.ground(name, x, y) if name in S.GROUND['prefabs'] else 0.0


# ---------------------------------------------------------------- u3
u3 = dict(missing=[], extra=[], parents={}, pivots={}, boxes={}, hinge={})
want = set()
for m, d in U3['u3_models'].items():
    for ob in d['objects']:
        want.add(ob['name'])
        o = bpy.data.objects.get(ob['name'])
        if o is None:
            u3['missing'].append(ob['name'])
            continue
        par = o.parent.name if o.parent else None
        if par != ob['parent']:
            u3['parents'][ob['name']] = dict(ours=par, u3=ob['parent'])
        if ob['parent']:
            loc = [round(v, 4) for v in CC.rel_matrix(o).translation]
            u3['pivots'][ob['name']] = dict(ours=loc, u3=ob['loc'], ok=bool(np.allclose(loc, ob['loc'], atol=1e-3)))
u3['extra'] = [o.name for o in bpy.data.objects if o.type == 'MESH' and o.name not in want]
for n in ROOTS:
    o = bpy.data.objects[n]
    pts = [CC.mesh_world(ob, np.array(CC.rel_matrix(ob)) if ob is not o else None)[0]
           for ob in [o] + [c for c in o.children_recursive if c.type == 'MESH']]
    co = np.vstack(pts)
    lo, hi = co.min(0), co.max(0)
    bb = U3['u3_models'][n]['bb']
    u3['boxes'][n] = dict(ours=[[round(float(a), 3) for a in lo], [round(float(a), 3) for a in hi]], u3=bb,
                          d_lo=[round(float(a - b), 3) for a, b in zip(lo, bb[0])],
                          d_hi=[round(float(a - b), 3) for a, b in zip(hi, bb[1])])
for it in U3['interactables']:
    cp = C['parts'].get(it['child'], {})
    ax = [-v + 0.0 for v in u2b(it['axis'])]
    u3['hinge'][it['child']] = dict(ours=dict(axis=cp.get('axis'), range=cp.get('range')), u3_axis_unity=it['axis'],
                                    expect_axis=ax, ok=bool(cp.get('axis') and np.allclose(cp['axis'], ax, atol=1e-3)
                                                            and list(cp['range']) == [it['min'], it['max']]))
RES['u3'] = u3

# ---------------------------------------------------------------- the dish copies
cop_ = {}
for cp, ref in (('Dish_2', 'Dish_1'), ('Dish_5', 'Dish_1'), ('Dish_4', 'Dish_3')):
    a, b = bpy.data.objects[ref].data, bpy.data.objects[cp].data
    ua, ub = np.empty(2 * len(a.loops)), np.empty(2 * len(b.loops))
    same_topo = len(a.loops) == len(b.loops)
    if same_topo:
        a.uv_layers['PSX'].data.foreach_get('uv', ua)
        b.uv_layers['PSX'].data.foreach_get('uv', ub)
        ma = [a.materials[p.material_index].name for p in a.polygons]
        mb = [b.materials[p.material_index].name for p in b.polygons]
        cop_[cp] = dict(ref=ref, uv_max_diff=float(np.abs(ua - ub).max()), materials_same=ma == mb)
    else:
        cop_[cp] = dict(ref=ref, topology='differs')
RES['copies'] = cop_

# ---------------------------------------------------------------- backfaces
bf = {}
for n in ROOTS:
    tree, info, V, Pl = CC.bvh_of(n)
    bf[n] = CC.backfaces(n, tree, info, V, CUTOUT, ground=gfn(n), rmax=40.0)
RES['backfaces'] = bf

# ---------------------------------------------------------------- floating
flo = {}
for n in ROOTS:
    o = bpy.data.objects[n]
    objs = [(o, None)] + [(c, CC.rel_matrix(c)) for c in o.children_recursive if c.type == 'MESH']
    isl = CC.islands(objs)
    LO = np.array([i['lo'] for i in isl]) - 0.012
    HI = np.array([i['hi'] for i in isl]) + 0.012
    nI = len(isl)
    comp = [-1] * nI
    nc = 0
    for a in range(nI):
        if comp[a] >= 0:
            continue
        st = [a]
        comp[a] = nc
        while st:
            u = st.pop()
            t = np.nonzero(np.all((LO <= HI[u]) & (HI >= LO[u]), axis=1))[0]
            for v in t:
                if comp[v] < 0:
                    comp[v] = nc
                    st.append(int(v))
        nc += 1
    g = gfn(n)
    bad = []
    for c in range(nc):
        mem = [i for i in range(nI) if comp[i] == c]
        gaps = [float(isl[i]['low'][2]) - g(float(isl[i]['low'][0]), float(isl[i]['low'][1])) for i in mem]
        if min(gaps) > 0.03:
            k = mem[int(np.argmin(gaps))]
            bad.append(dict(islands=len(mem), zones=sorted({ZN.get(isl[i]['zone'], isl[i]['zone']) for i in mem}),
                            gap_m=round(min(gaps), 3), at=[round(float(v), 2) for v in isl[k]['low']]))
    flo[n] = dict(groups=nc, islands=nI, floating=bad)
RES['floating'] = flo

# ---------------------------------------------------------------- lights and halos
LENS_M = ('M_Light_Red', 'M_Lamp_SodiumOff', 'M_Headlight', 'M_Candle', 'M_LEDOff')
lights = {}
for n in ROOTS:
    pts = []
    for pl in U3['prefabLights']:
        if pl['model'] == n:
            pts += [('light:' + L.get('tag', ''), L['p']) for L in pl['lights']]
    for pg in U3['prefabGlows']:
        if pg['model'] == n:
            pts += [('halo:' + g_['m'], g_['p']) for g_ in pg['glows']]
    if not pts:
        continue
    tree, info, V, Pl = CC.bvh_of(n)
    res = CC.lens_points(tree, info, V, Pl, [u2b(p) for _, p in pts], LENS_M)
    for (kind, _), r in zip(pts, res):
        r['kind'] = kind
    lights[n] = res
RES['lights'] = lights

# ---------------------------------------------------------------- doors: the swing, the doorway
doors = {}
for n, p in C['parts'].items():
    if not n.startswith('IX_') or p.get('kind') != 'hinge':
        continue
    root = p['parent']
    tree, info, V, Pl = CC.bvh_of(root, children=False)
    d = bpy.data.objects[n]
    M0 = CC.rel_matrix(d)
    piv = np.array(M0.translation)
    co, pls = CC.mesh_world(d)
    za = d.data.attributes['zone'].data
    ax = Vector(p['axis'])
    sw = {}
    for ang in list(range(0, int(p['range'][1]) + 1, 2)):
        M = np.array(M0 @ Matrix.Rotation(math.radians(ang), 4, ax))
        c2 = (M[:3, :3] @ co.T).T + M[:3, 3]
        t = BVHTree.FromPolygons([Vector(q) for q in c2], pls)
        hit = set()
        for a, b in t.overlap(tree):
            ca = np.mean([c2[i] for i in pls[a]], axis=0)
            cb = np.mean([tuple(V[i]) for i in Pl[b]], axis=0)
            if np.hypot(*(ca - piv)[:2]) < 0.035 or np.hypot(*(cb - piv)[:2]) < 0.035:
                continue                                                # the knuckles round the (vertical) axis
            hit.add((ZN.get(int(round(za[a].value)), -1), ZN.get(info[b][1], info[b][1])))
        if hit:
            sw[ang] = sorted(hit)
    # the free edge's way: where it is at the full swing (outside = away from the building's centre)
    far_pt = c2[np.argmax(np.linalg.norm(c2[:, :2] - piv[:2], axis=1))]
    doors[n] = dict(root=root, axis=p['axis'], range=p['range'], crossings={str(k): v for k, v in sw.items()},
                    free_edge_open=[round(float(v), 2) for v in far_pt])
for n, rec in doors.items():
    root = rec['root']
    if root.startswith('Dish'):
        continue
    tree, info, V, Pl = CC.bvh_of(root, children=False)            # the doorway without the leaf: clear width, height
    p = C['parts'][n]
    hx, hy, hz = p['pivot']
    leaf = bpy.data.objects[n]
    co, _ = CC.mesh_world(leaf, np.array(CC.rel_matrix(leaf)))
    cx = float((co[:, 0].min() + co[:, 0].max()) / 2)
    widths, heights = [], []
    for z in np.arange(hz + 0.3, hz + 1.9, 0.2):
        l_ = tree.ray_cast(Vector((cx, hy, z)), Vector((-1, 0, 0)), 3.0)
        r_ = tree.ray_cast(Vector((cx, hy, z)), Vector((1, 0, 0)), 3.0)
        if l_[0] is not None and r_[0] is not None:
            widths.append(r_[0].x - l_[0].x)
    for x in np.linspace(cx - 0.25, cx + 0.25, 5):
        up = tree.ray_cast(Vector((x, hy, hz + 0.5)), Vector((0, 0, 1)), 4.0)
        dn = tree.ray_cast(Vector((x, hy, hz + 0.5)), Vector((0, 0, -1)), 2.0)
        if up[0] is not None:
            heights.append(up[0].z - (dn[0].z if dn[0] is not None else hz))
    rec['doorway'] = dict(clear_width_m=round(min(widths), 3) if widths else None,
                          clear_height_m=round(min(heights), 3) if heights else None,
                          capsule_fits=bool(widths and heights and min(widths) > 2 * CAP_R + 0.02 and min(heights) > CAP_H))
RES['doors'] = doors

# ---------------------------------------------------------------- the lookout: the climb's head room
tree, info, V, Pl = CC.bvh_of('LookoutTower')


def capsule_clear(x, y, zf):
    """the capsule standing at (x, y) on zf: the nearest geometry to its head and shoulders (spheres from 1.10 up to the
    top: above the treads of a steep flight ahead of it) - the head room over the climb"""
    worst = 9.0
    for zc in np.arange(zf + 1.10, zf + CAP_H - CAP_R + 1e-6, 0.04):
        loc, nrm, idx, dist = tree.find_nearest(Vector((x, y, zc)))
        if loc is not None:
            worst = min(worst, dist)
    return worst


L = S.LOOKOUT
tr = sorted(S.STAIRS['treads'], key=lambda r: r[0][2])
lands = sorted(S.STAIRS['landings'], key=lambda r: r[0][2])
path = []
for lo, hi in tr:
    path.append(('tread', (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, hi[2]))
for lo, hi in lands:
    path.append(('landing', (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, hi[2]))
top = lands[-1]
zl = top[1][2]
lx = (L['ladder_x'][0] + L['ladder_x'][1]) / 2
path.append(('top landing, under the well', lx, -0.55, zl))
for i, yc in enumerate(L['ladder_y']):
    path.append((f'ladder tread {i + 1}', lx, yc, zl + 0.25 * (i + 1)))
f1 = L['floor'][1]
for nm, (x, y) in (('cab: off the ladder', (lx, L['well'][3] + 0.40)), ('cab: north', (0.50, 1.25)),
                   ('cab: west', (-1.30, -0.40)), ('cab: south-west', (-1.00, -1.25)), ('cab: south-east', (1.30, -1.35)),
                   ('cab: north-east', (1.30, 1.30))):
    path.append((nm, x, y, f1))
climb = []
for nm, x, y, zf in sorted(path, key=lambda r: r[3]):
    c_ = capsule_clear(x, y, zf)
    climb.append(dict(where=nm, at=[round(x, 3), round(y, 3), round(zf, 3)], clearance_m=round(c_ - CAP_R, 3)))
steps = [round(b['at'][2] - a['at'][2], 3) for a, b in zip(climb[:-1], climb[1:])]
u3c = [c for c in climb if c['where'] in ('tread', 'landing')]
top = [c for c in climb if c['where'] not in ('tread', 'landing')]
flights = []
for fi in range(7):                                                      # Update 3's flights: rise and run of each
    f = sorted([r for r in tr if 3 * fi - 0.05 <= r[0][2] < 3 * fi + 2.95], key=lambda r: r[0][2])
    xs = [(lo[0] + hi[0]) / 2 for lo, hi in f]
    zs = [hi[2] for lo, hi in f]
    flights.append(dict(treads=len(f), rise=round(float(np.mean(np.diff(zs))), 3), run=round(float(np.mean(np.abs(np.diff(xs)))), 3),
                        y=[round(float(min(lo[1] for lo, hi in f)), 2), round(float(max(hi[1] for lo, hi in f)), 2)]))
RES['lookout'] = dict(u3_stairs=dict(flights=flights, angle_deg=[round(math.degrees(math.atan2(f['rise'], f['run'])), 1)
                                                                   for f in flights],
                                     treads_without_headroom=sum(1 for c in u3c if c['clearance_m'] < -0.005),
                                     treads=len(u3c), min_clearance_m=min(c['clearance_m'] for c in u3c)),
                      top=dict(blocked=[c for c in top if c['clearance_m'] < -0.005],
                               min_clearance_m=min(c['clearance_m'] for c in top), path=top),
                      max_rise_m=max(steps), path=climb)

# ---------------------------------------------------------------- coplanar, uv, textures, tris
cop, uvr = {}, {}
for n in ROOTS:
    o = bpy.data.objects[n]
    for ob in [o] + [c for c in o.children_recursive if c.type == 'MESH']:
        c, wh = CC.coplanar(ob.data)
        if c:
            cop[ob.name] = dict(pairs=c, at=wh)
        uvr[ob.name] = CC.uv_range(ob.data, ATLAS)
RES['coplanar_pairs'] = cop
RES['uv_bad'] = {k: {m: r for m, r in v.items() if not r['ok']} for k, v in uvr.items() if any(not r['ok'] for r in v.values())}
RES['images'] = CC.images()
RES['tris'] = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects
               if o.type == 'MESH' and not o.name.startswith(('Terrain', 'Forest_Road', 'Forest_BasePaved'))}

json.dump(RES, open(os.path.join(OUTD, f'far_checks{SFX}.json'), 'w'), indent=1, default=str)
print('u3 missing', u3['missing'], 'extra', u3['extra'], 'parents', u3['parents'])
print('u3 pivots', {k: v['ok'] for k, v in u3['pivots'].items()})
print('u3 hinge', {k: (v['ok'], v['ours']['axis'], v['expect_axis']) for k, v in u3['hinge'].items()})
for n, r in u3['boxes'].items():
    print('box', n, r['d_lo'], r['d_hi'])
print('copies', cop_)
print('backfaces', {n: (r['rays'], {k: v[0] for k, v in sorted(r['bad'].items(), key=lambda kv: -kv[1][0])[:6]})
                    for n, r in bf.items()})
print('floating', {n: r['floating'][:4] for n, r in flo.items() if r['floating']})
print('lights', json.dumps(lights))
for n, r in doors.items():
    print('door', n, 'crossings', {k: v for k, v in list(r['crossings'].items())[:8]}, 'free edge open', r['free_edge_open'],
          r.get('doorway'))
print('lookout top', RES['lookout']['top']['blocked'], RES['lookout']['top']['min_clearance_m'], 'u3 stairs',
      {k: v for k, v in RES['lookout']['u3_stairs'].items() if k != 'flights'}, RES['lookout']['u3_stairs']['flights'][:2])
print('coplanar', {k: v['pairs'] for k, v in cop.items()})
print('uv bad', RES['uv_bad'])
print('images', RES['images'])
print('tris', RES['tris'])
