"""Checks of the base prefabs (out/base.blend + base_contract.json), each prefab moved to the origin (its own frame):
  u3        every Update 3 model present (Hatch + IX_HatchLid_94, Helipad, RadioMast, Crates, LogPile, LightPole,
            PowerPole, FenceChain, OldFence a/b/c, Forest_Wires), the child's parent and pivot as Update 3, the root pivots
            at the origin; the boxes against Update 3's FBX boxes; the hinge (axis, range, locked) as Update 3
  backfaces rays from rings of eyes round each prefab (and from above): the first hit faces the eye (Unity culls back
            faces); the chain-link, barbed and rusty strands are two-sided cut-outs by design
  floating  connected face islands grouped by touching boxes: every group reaches the ground (Update 3's terrain under
            each placement; the fences on their own ground plane) - nothing hangs in the air
  lights    Update 3's lights and halos (the mast's beacons, the yard light) at the lens faces of the rebuilt lamps
  hatch     the lid swung 0..100 deg about its hinge against the frame, collar, staple and padlock
  wires     the line's conductors: their ends on the insulators, their clearance over the terrain and the base prefabs
  layout    Update 3's fence placements on the terrain (informational: the layout is Update 3's, kept)
  coplanar  overlapping coplanar faces left in one mesh (z-fighting)
  uv        the atlas materials' UVs inside 0..1; the textures the materials use
python3 -I base_checks.py [--draft] -> base_checks.json, prints a summary"""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

sys.path.insert(0, '/home/claude/uaz')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base_spec as S
import base_kit as BK
import chk_common as CC

SFX = '_draft' if '--draft' in sys.argv else ''
OUTD = os.path.dirname(os.path.abspath(__file__))
TERRAIN = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/trail2/terrain.blend'
bpy.ops.wm.open_mainfile(filepath=f'/home/claude/uaz/out/base{SFX}.blend')
C = json.load(open(f'/home/claude/uaz/out/base_contract{SFX}.json'))
RES = {}
ROOTS = [n for n, p in C['parts'].items() if not p.get('parent')]
MAPM = {n: bpy.data.objects[n].matrix_world.copy() for n in ROOTS}
PREFABS = [n for n in ROOTS if n != 'Forest_Wires']
CUTOUT = ('M_Base_ChainLink', 'M_Base_Barbed', 'M_Base_Rust')
ATLAS = ('M_Base_Props', 'M_Base_Helipad', 'M_Base_Mast', 'M_Base_Poles', 'M_Base_Fence', 'M_Base_Panel')
U3 = S.U3


def u2b(p):
    return (-p[0], -p[2], p[1])


# ---------------------------------------------------------------- the ground under each placement
def _grid_sample(g, x, y):
    z = np.array([[np.nan if v is None else v for v in r] for r in g['z']], np.float64)
    z = np.nan_to_num(z, nan=float(np.nanmin(z)))
    fi = min(max((x - g['x0']) / g['step'], 0.0), z.shape[1] - 1.0001)
    fj = min(max((y - g['y0']) / g['step'], 0.0), z.shape[0] - 1.0001)
    i_, j_ = int(fi), int(fj)
    a, b = fi - i_, fj - j_
    q = z[j_:j_ + 2, i_:i_ + 2]
    return float((q[0, 0] * (1 - a) + q[0, 1] * a) * (1 - b) + (q[1, 0] * (1 - a) + q[1, 1] * a) * b)


def ground_fns(name):
    if name in S.GROUND['prefabs']:
        fns = []
        for i, e in enumerate(S.GROUND['prefabs'][name]):
            anchors = e.get('anchors', {})

            def f(x, y, i=i, anchors=anchors):
                for key, g in anchors.items():
                    ax, ay = map(float, key.split(','))
                    if abs(x - ax) < 1.5 and abs(y - ay) < 1.5:
                        return _grid_sample(g, x, y)
                return S.ground(name, x, y, i)
            fns.append(f)
        return fns
    return [lambda x, y: 0.0]


# ---------------------------------------------------------------- u3: presence, hierarchy, pivots, boxes, the hinge
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
    CC.solo(ROOTS, MAPM, n) if n != 'Forest_Wires' else None
    o = bpy.data.objects[n]
    pts = []
    for ob in [o] + [c for c in o.children_recursive if c.type == 'MESH']:
        co, _ = CC.mesh_world(ob, np.array(CC.rel_matrix(ob)) if ob is not o else None)
        pts.append(co)
    co = np.vstack(pts)
    if n == 'Forest_Wires':                                            # world model: compare in Update 3's FBX frame
        co = co.copy()
    lo, hi = co.min(0), co.max(0)
    bb = U3['u3_models'][n]['bb'] if n in U3['u3_models'] else None
    rec = dict(ours=[[round(float(a), 3) for a in lo], [round(float(a), 3) for a in hi]], u3=bb)
    if bb:
        rec['d_lo'] = [round(float(a - b), 3) for a, b in zip(lo, bb[0])]
        rec['d_hi'] = [round(float(a - b), 3) for a, b in zip(hi, bb[1])]
    u3['boxes'][n] = rec
for it in U3['interactables']:
    cp = C['parts'].get(it['child'], {})
    ax_u3 = [-round(v, 4) + 0.0 for v in u2b(it['axis'])]          # Blender axis = -(Unity axis as a position)
    u3['hinge'][it['child']] = dict(ours=dict(axis=cp.get('axis'), range=cp.get('range'), locked=cp.get('locked'),
                                              pivot=cp.get('pivot')),
                                    u3=dict(axis_expected=ax_u3, axis_unity=it['axis'], range=[it['min'], it['max']], locked=it.get('locked')),
                                    ok=bool(cp.get('axis') and np.allclose(cp['axis'], ax_u3, atol=1e-3)
                                            and list(cp.get('range')) == [it['min'], it['max']]
                                            and bool(cp.get('locked')) == bool(it.get('locked'))))
RES['u3'] = u3

# ---------------------------------------------------------------- backfaces
bf = {}
for n in PREFABS:
    CC.solo(ROOTS, MAPM, n)
    tree, info, V, Pl = CC.bvh_of(n)
    g0 = ground_fns(n)[0]
    r = CC.backfaces(n, tree, info, V, CUTOUT, ground=g0, rmax=40.0)
    bf[n] = r
RES['backfaces'] = {n: dict(rays=r['rays'], bad=r['bad']) for n, r in bf.items()}

# ---------------------------------------------------------------- floating: groups of touching islands reach the ground
flo = {}
for n in PREFABS:
    o = bpy.data.objects[n]
    objs = [(o, None)] + [(c, CC.rel_matrix(c)) for c in o.children_recursive if c.type == 'MESH']
    isl = CC.islands(objs)
    LO = np.array([i['lo'] for i in isl]) - 0.012
    HI = np.array([i['hi'] for i in isl]) + 0.012
    nI = len(isl)
    adj = [[] for _ in range(nI)]
    for a in range(nI):
        t = np.all((LO <= HI[a]) & (HI >= LO[a]), axis=1)
        for b in np.nonzero(t)[0]:
            if b != a:
                adj[a].append(int(b))
    comp = [-1] * nI
    nc = 0
    for a in range(nI):
        if comp[a] >= 0:
            continue
        st = [a]
        comp[a] = nc
        while st:
            u = st.pop()
            for v in adj[u]:
                if comp[v] < 0:
                    comp[v] = nc
                    st.append(v)
        nc += 1
    fns = ground_fns(n)
    bad = []
    for c in range(nc):
        mem = [i for i in range(nI) if comp[i] == c]
        gaps = []
        for i in mem:
            low = isl[i]['low']
            gaps.append(max(float(low[2]) - g(float(low[0]), float(low[1])) for g in fns))
        if min(gaps) > 0.03:
            k = mem[int(np.argmin(gaps))]
            bad.append(dict(islands=len(mem), zones=sorted({isl[i]['zone'] for i in mem}), gap_m=round(min(gaps), 3),
                            at=[round(float(v), 2) for v in isl[k]['low']]))
    flo[n] = dict(groups=nc, islands=nI, floating=bad)
RES['floating'] = flo

# ---------------------------------------------------------------- lights and halos at the lenses
lights = {}
LENS = {'RadioMast': ('M_Light_Red',), 'LightPole': ('M_Lamp_SodiumOff',)}
for n, lm in LENS.items():
    CC.solo(ROOTS, MAPM, n)
    tree, info, V, Pl = CC.bvh_of(n)
    pts = []
    for pl in U3['prefabLights']:
        if pl['model'] == n:
            pts += [('light', L['p']) for L in pl['lights']]
    for pg in U3['prefabGlows']:
        if pg['model'] == n:
            pts += [('halo', g['p']) for g in pg['glows']]
    res = CC.lens_points(tree, info, V, Pl, [u2b(p) for _, p in pts], lm)
    for (kind, _), r in zip(pts, res):
        r['kind'] = kind
    lights[n] = res
RES['lights'] = lights

# ---------------------------------------------------------------- the hatch: the lid's swing
CC.solo(ROOTS, MAPM, 'Hatch')
tree, info, V, Pl = CC.bvh_of('Hatch', children=False)
lid = bpy.data.objects['IX_HatchLid_94']
M0 = CC.rel_matrix(lid)
piv = Vector(M0.translation)
co, pls = CC.mesh_world(lid)
za = lid.data.attributes['zone'].data
sw = {}
for ang in list(range(0, 21, 1)) + list(range(22, 101, 2)):
    R = Matrix.Rotation(math.radians(ang), 4, Vector((0, -1, 0)))
    M = np.array(M0 @ R)
    c2 = (M[:3, :3] @ co.T).T + M[:3, 3]
    t = BVHTree.FromPolygons([Vector(p) for p in c2], pls)
    hit = set()
    for a, b in t.overlap(tree):
        ca = np.mean([c2[i] for i in pls[a]], axis=0)
        cb = np.mean([tuple(V[i]) for i in Pl[b]], axis=0)
        if math.hypot(ca[0] - piv.x, ca[2] - piv.z) < 0.025 or math.hypot(cb[0] - piv.x, cb[2] - piv.z) < 0.025:
            continue                                                    # the knuckles round the axis (they turn in place)
        hit.add((int(round(za[a].value)), info[b][1]))
    if hit:
        sw[ang] = sorted(hit)
ZN = {getattr(BK, k): k for k in dir(BK) if k.startswith('Z_') and isinstance(getattr(BK, k), int)}
RES['hatch_swing'] = {str(a): [(ZN.get(p, p), ZN.get(q, q)) for p, q in v] for a, v in sw.items()}
# the lid at rest: its underside on the frame (gap), its edge to the frame's leg (gap)
h = S.HATCH
RES['hatch_rest'] = dict(lid_bottom=h['lid_skirt'], frame_top=h['top'] + 0.012, lid_half=h['lid'], frame_in=h['frame_in'],
                         side_gap=round(h['frame_in'] - h['lid'], 3))

# ---------------------------------------------------------------- the line's conductors
for n in ROOTS:
    bpy.data.objects[n].matrix_world = MAPM[n]
bpy.context.view_layer.update()
with bpy.data.libraries.load(TERRAIN) as (src, dst):
    dst.objects = [n for n in src.objects if n != 'Forest_Marker']
TV, TP = [], []
for o in dst.objects:
    if o is not None and o.name not in bpy.context.scene.objects:
        bpy.context.scene.collection.objects.link(o)
bpy.context.view_layer.update()
for o in dst.objects:
    if o is None or o.type != 'MESH':
        continue
    co, pls = CC.mesh_world(o, np.array(o.matrix_world))
    b0 = len(TV)
    TV += [Vector(p) for p in co]
    TP += [[b0 + i for i in p] for p in pls]
TT = BVHTree.FromPolygons(TV, TP)
W = bpy.data.objects['Forest_Wires']
wco, _ = CC.mesh_world(W, np.array(W.matrix_world))
wz = W.data.attributes['zone'].data
vz = np.zeros(len(W.data.vertices))
for pg in W.data.polygons:
    for vi in pg.vertices:
        vz[vi] = wz[pg.index].value
cond = wco[np.round(vz) == 0]
risers = [np.array(S.local_to_map('PowerPole', (0, 0, 0), i - 1))[:2] for i in S.LINE_ENDS]
span_v = cond[np.min([np.linalg.norm(cond[:, :2] - r, axis=1) for r in risers], axis=0) > 1.2]
clear = []
for p in span_v[::2]:
    loc, nrm, idx, d = TT.ray_cast(Vector((p[0], p[1], p[2])), Vector((0, 0, -1)), 200.0)
    if loc is not None:
        clear.append(float(p[2] - loc.z))
# the base prefabs at their places (and the five more yard lights, the three more poles) round the conductors
OV, OP = [], []
for n in PREFABS:
    if n in ('PowerPole',):
        continue
    plist = [MAPM[n]]
    if n == 'LightPole':
        plist = [Matrix([list(r) for r in S.frame_matrix(e['p'], e['q'])]) for e in U3['prefabs']['LightPole']]
    for Mw in plist:
        co, pls = CC.mesh_world(bpy.data.objects[n], np.array(Mw))
        b0 = len(OV)
        OV += [Vector(p) for p in co]
        OP += [[b0 + i for i in p] for p in pls]
OT = BVHTree.FromPolygons(OV, OP)
near = min(OT.find_nearest(Vector(p))[3] for p in cond[::4])
ends = {}
for a_, b_ in S.SPANS:
    for who in (a_, b_):
        for q in S.insulators(who):
            d = np.linalg.norm(cond - (np.array(q) + [0, 0, 0.012]), axis=1).min()
            ends[f'{who}:{q[0]:.2f},{q[1]:.2f}'] = round(float(d), 4)
SPAN_L = {f'{a}-{b}': round(float(np.linalg.norm(np.array(S.insulators(a)[1]) - np.array(S.insulators(b)[1]))), 2) for a, b in S.SPANS}
RES['wires'] = dict(conductor_vertices=len(cond), spans_m=SPAN_L, mid_sag_m={k: round(S.WIRE_SAG * v * v, 2) for k, v in SPAN_L.items()}, min_clearance_terrain_m=round(min(clear), 2) if clear else None,
                    min_dist_other_base_prefabs_m=round(float(near), 2), end_to_insulator_max_m=max(ends.values()),
                    sag_per_m2=S.WIRE_SAG)

# ---------------------------------------------------------------- layout (Update 3's): the fences on the terrain
G = S.GROUND['fences']
lay = {}
for nm in ('OldFence', 'OldFence_b', 'OldFence_c'):
    gp = np.array([g['ground']['2.0'] for g in G[nm]])
    lay[nm] = dict(n=len(gp), post_floating=int((gp < -0.40 + 0.0).sum()), post_mostly_buried=int((gp > 1.0).sum()))
posts, starts = [], []
for nm in ('OldFence', 'OldFence_b', 'OldFence_c'):
    for e in U3['scatter'][nm]:
        M = np.array(S.frame_matrix(e['p'], e['q']))
        posts.append((M @ np.array([2.0, 0, 0, 1]))[:3])
        starts.append((M @ np.array([-2.0, 0, 0, 1]))[:3])
posts, starts = np.array(posts), np.array(starts)
dv = []
for s in starts:
    d = np.linalg.norm(posts[:, :2] - s[:2], axis=1)
    j = int(d.argmin())
    if d[j] < 0.05:
        dv.append(abs(posts[j, 2] - s[2]))
dv = np.array(dv)
lay['old_strand_joints'] = dict(joined=len(dv), step_over_0_3m=int((dv > 0.3).sum()), step_over_1m=int((dv > 1.0).sum()),
                                max_step_m=round(float(dv.max()), 2))
gc = np.array([g['ground']['1.5'] for g in G['FenceChain']])
lay['FenceChain'] = dict(n=len(gc), post_floating=int((gc < -0.40).sum()),
                         max_fall_along_section_m=round(max(max(g['ground'].values()) - min(g['ground'].values())
                                                            for g in G['FenceChain']), 3))
RES['layout'] = lay

# ---------------------------------------------------------------- coplanar, uv, textures
cop, uvr = {}, {}
for n in ROOTS:
    o = bpy.data.objects[n]
    for ob in [o] + [c for c in o.children_recursive if c.type == 'MESH']:
        c, wh = CC.coplanar(ob.data)
        if c:
            cop[ob.name] = dict(pairs=c, at=wh)
        uvr[ob.name] = CC.uv_range(ob.data, ATLAS)
RES['coplanar_pairs'] = cop
RES['uv'] = {k: v for k, v in uvr.items() if v}
RES['uv_bad'] = {k: {m: r for m, r in v.items() if not r['ok']} for k, v in uvr.items() if any(not r['ok'] for r in v.values())}
RES['images'] = CC.images()
RES['tris'] = {n: sum(len(p.vertices) - 2 for p in bpy.data.objects[n].data.polygons) for n in
               [o.name for o in bpy.data.objects if o.type == 'MESH']}

json.dump(RES, open(os.path.join(OUTD, f'base_checks{SFX}.json'), 'w'), indent=1, default=str)
print('u3 missing', u3['missing'], 'extra', u3['extra'], 'parents', u3['parents'])
print('u3 pivots', u3['pivots'])
print('u3 hinge', u3['hinge'])
for n, r in u3['boxes'].items():
    print('box', n, r.get('d_lo'), r.get('d_hi'))
print('backfaces', {n: (r['rays'], {k: v[0] for k, v in sorted(r['bad'].items(), key=lambda kv: -kv[1][0])[:6]})
                    for n, r in RES['backfaces'].items()})
print('floating', {n: r['floating'][:4] for n, r in flo.items() if r['floating']})
print('lights', json.dumps(lights))
print('hatch swing', {a: v for a, v in list(RES['hatch_swing'].items())[:30]})
print('wires', RES['wires'])
print('layout', lay)
print('coplanar', {k: v['pairs'] for k, v in cop.items()})
print('uv bad', RES['uv_bad'])
print('images', RES['images'])
print('tris', RES['tris'])
