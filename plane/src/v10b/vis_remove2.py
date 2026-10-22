"""v10b hidden-face removal (Embree; replaces vis_remove.py). Reads the reduced blend, deletes the faces of interior
static parts that no eye position can see, writes the result:  python3 vis_remove2.py <in.blend> <out.blend>
Same rules as the first pass, with one fix: glass (any material with 'Glass' in its name - window glass, gauge glass,
compass glass) never hides anything; the first pass let gauge glass hide the dials behind it.
 eyes: inside the cabin a 15 cm grid from 15 cm above the floor to the ceiling, wall to wall, nose to tail; outside a
       50 cm grid around the cabin (x +-4 m, 2.5 m beyond nose and tail, z -0.1..5 m); eyes inside solid geometry dropped
 1. forward pass: from every eye 16 000 (inside) / 8 000 (outside) directions; the first front-facing triangle each
    ray meets is seen (back faces are culled, as in Unity: rays pass through them)
 2. every polygon of an interior static part that no ray met: exact line of sight from its centre and 5 points near
    its corners to every eye in front of it; deleted only if all are blocked by front faces
Occluders: Cockpit static parts, Cabin_Fittings and the body source parts; doors, controls, seats, belts and other
moving parts never occlude (they can be opened / moved)."""
import bpy, bmesh, json, time, sys
import numpy as np
from embreex import rtcore_scene as rtcs
from embreex.mesh_construction import TriangleMesh

SRC, OUT = sys.argv[-2], sys.argv[-1]
REPORT = '/tmp/claude-0/-home-claude/51fa62a7-1078-590a-959e-7ab38193aafa/scratchpad/opt/vis_v10b_report.json'
bpy.ops.wm.open_mainfile(filepath=SRC)
CPR = json.load(open('/home/claude/plane/out/cockpit_rig_v7.json'))
rig = set(CPR['rig'].keys())
O = bpy.data.objects
static = [o for o in bpy.data.collections['Cockpit'].objects if o.type == 'MESH' and o.name not in rig and
          not o.name.startswith(('Lamp_', 'Lens_', 'Display_', 'Belt_')) and o.name not in ('CP_RadioFaces', 'CP_Annunciator')]
static += [O['Cabin_Fittings']]
body = [o for o in bpy.data.collections['Aircraft'].objects if o.type == 'MESH' and o.name.startswith('src_') and
        o.name not in ('src_GlassFixed', 'src_StepLadder') and not o.name.startswith('src_Case')]
objs = static + body
P_all, own_obj, own_poly, glass = [], [], [], []
for oi, o in enumerate(objs):
    me = o.data
    me.calc_loop_triangles()
    T = len(me.loop_triangles)
    vi = np.empty(T * 3, np.int32); me.loop_triangles.foreach_get('vertices', vi)
    pi = np.empty(T, np.int32); me.loop_triangles.foreach_get('polygon_index', pi)
    mi = np.empty(T, np.int32); me.loop_triangles.foreach_get('material_index', mi)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    M = np.array(o.matrix_world)
    w = co @ M[:3, :3].T + M[:3, 3]
    P_all.append(w[vi].reshape(T, 3, 3))
    own_obj.append(np.full(T, oi, np.int32)); own_poly.append(pi)
    mn = [(m.name if m else '') for m in me.materials] or ['']
    glass.append(np.array(['Glass' in mn[min(k, len(mn) - 1)] for k in mi], bool))
P_all = np.concatenate(P_all); own_obj = np.concatenate(own_obj); own_poly = np.concatenate(own_poly)
glass = np.concatenate(glass)
occ = np.where(~glass)[0]                                   # occluder triangles (no glass)
P = P_all[occ]
NG = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
NG /= np.maximum(np.linalg.norm(NG, axis=1), 1e-20)[:, None]
scene = rtcs.EmbreeScene()
TriangleMesh(scene, P.astype(np.float32))
print('occluder tris', len(P), 'glass tris left out', int(glass.sum()), flush=True)


def cast(o, d, tfar=None, stop='front'):
    """first triangle that faces the viewer (stop='front': NG.d < 0) or faces the ray's end (stop='back': NG.d > 0)
    along each ray, passing through the others; -1 = none within tfar"""
    n = len(o)
    res = np.full(n, -1, np.int64)
    org = o.astype(np.float32).copy()
    dd = d.astype(np.float32)
    left = np.full(n, np.inf, np.float64) if tfar is None else tfar.astype(np.float64).copy()
    todo = np.arange(n)
    for _ in range(48):
        if len(todo) == 0:
            break
        dist = np.minimum(left[todo], 1e30).astype(np.float32)
        r = scene.run(org[todo], dd[todo], dists=dist, output=1)
        pid = r['primID'].astype(np.int64)
        tf = r['tfar'].astype(np.float64)
        hit = (pid >= 0) & (tf < left[todo])
        s = np.zeros(len(todo), bool)
        if hit.any():
            dots = (NG[pid[hit]] * dd[todo[hit]]).sum(1)
            s[hit] = (dots < 0) if stop == 'front' else (dots > 0)
        res[todo[s]] = pid[s]
        go = hit & ~s
        adv = tf[go] + 1e-5
        left[todo[go]] -= adv
        org[todo[go]] += dd[todo[go]] * adv[:, None].astype(np.float32)
        todo = todo[go]
    return res


# ---------------------------------------------------------------- eyes (same grids as the first pass)
pts = np.array([v for o in static for v in [tuple(o.matrix_world @ c_) for c_ in [__import__('mathutils').Vector(c) for c in o.bound_box]]])
lo, hi = pts.min(0), pts.max(0)
FLOOR = 1.07


def inside_solid(E):
    E = np.asarray(E, np.float64)
    back = np.zeros(len(E), int)
    for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        D = np.repeat(np.array([d], np.float32), len(E), 0)
        r = scene.run(E.astype(np.float32), D, output=1)
        pid = r['primID'].astype(np.int64)
        ok = (pid >= 0) & (r['tfar'] < 0.6)
        b = np.zeros(len(E), bool)
        b[ok] = (NG[pid[ok]] * D[ok]).sum(1) > 0
        back += b
    return back >= 4


eyes_in = np.array([(x, y, z) for x in np.arange(lo[0] + 0.04, hi[0] - 0.02, 0.15) for y in np.arange(lo[1] + 0.04, hi[1], 0.15)
                    for z in np.arange(FLOOR + 0.15, hi[2] - 0.03, 0.15)])
eyes_in = eyes_in[~inside_solid(eyes_in)]
eo = []
for x in np.arange(-4.0, 4.01, 0.5):
    for y in np.arange(lo[1] - 2.5, hi[1] + 2.5, 0.5):
        for z in np.arange(-0.1, 5.0, 0.4):
            if lo[0] - 0.05 < x < hi[0] + 0.05 and lo[1] - 0.05 < y < hi[1] + 0.05 and lo[2] - 0.05 < z < hi[2] + 0.05:
                continue
            eo.append((x, y, z))
eyes_out = np.array(eo)
eyes_out = eyes_out[~inside_solid(eyes_out)]
print('eyes inside', len(eyes_in), 'outside', len(eyes_out), flush=True)


def fib(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)


# ---------------------------------------------------------------- 1. forward pass
t0 = time.time()
hit = np.zeros(len(P), bool)
for eyes, nd in ((eyes_in, 16000), (eyes_out, 8000)):
    D = fib(nd)
    B = max(1, 1000000 // nd)
    for s in range(0, len(eyes), B):
        E = eyes[s:s + B]
        o = np.repeat(E, nd, 0)
        d = np.tile(D, (len(E), 1))
        r = cast(o, d)
        hit[r[r >= 0]] = True
    print('  forward pass', len(eyes), 'eyes', round(time.time() - t0), 's', flush=True)
seen = set(zip(own_obj[occ][hit].tolist(), own_poly[occ][hit].tolist()))
print('forward pass done', round(time.time() - t0), 's; triangles hit', int(hit.sum()), '/', len(P), flush=True)

# ---------------------------------------------------------------- 2. exact line of sight for polygons nobody hit
EYES = np.concatenate([eyes_in, eyes_out])
removable = []
t1 = time.time()
ntest = 0
for oi, o in enumerate(objs[:len(static)]):
    me = o.data
    M = np.array(o.matrix_world)
    R = M[:3, :3]
    Rn = np.linalg.inv(R).T
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3) @ R.T + M[:3, 3]
    for p in me.polygons:
        if (oi, p.index) in seen:
            continue
        ntest += 1
        c = np.array(p.center) @ R.T + M[:3, 3]
        n = np.array(p.normal) @ Rn.T
        n /= max(np.linalg.norm(n), 1e-20)
        sp = [c] + [co[vi] * 0.85 + c * 0.15 for vi in p.vertices[:5]]
        vis = False
        for s_ in sp:
            S = s_ + n * 0.0005
            rel = EYES - S
            dist = np.linalg.norm(rel, axis=1)
            front = (rel @ n) > 0.01 * dist
            if not front.any():
                continue
            Dv = rel[front] / dist[front][:, None]
            r = cast(np.repeat(S[None, :], front.sum(), 0), Dv, tfar=dist[front], stop='back')
            if (r < 0).any():
                vis = True
                break
        if not vis:
            removable.append((oi, p.index))
        if ntest % 2000 == 0:
            print('  LOS tested', ntest, 'removable', len(removable), round(time.time() - t1), 's', flush=True)
print('LOS done', round(time.time() - t1), 's; tested', ntest, 'removable polygons', len(removable), flush=True)
kill_by = {}
for oi, pi in removable:
    kill_by.setdefault(oi, []).append(pi)

# ---------------------------------------------------------------- 3. delete
removed = {}
for oi, o in enumerate(objs):
    kill = kill_by.get(oi, [])
    if not kill:
        continue
    me = o.data
    before = sum(len(p.vertices) - 2 for p in me.polygons)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in kill], context='FACES_ONLY')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.update()
    after = sum(len(p.vertices) - 2 for p in me.polygons)
    removed[o.name] = (before, after)
tot_b = sum(b for b, a in removed.values())
tot_a = sum(a for b, a in removed.values())
for k, (b, a) in sorted(removed.items(), key=lambda kv: kv[1][1] - kv[1][0]):
    print(f'  {k:22s} {b:6d} -> {a:6d}  (-{b - a})')
print('removed tris', tot_b - tot_a, flush=True)
json.dump(dict(removed=removed, eyes_in=len(eyes_in), eyes_out=len(eyes_out), glass_occludes=False),
          open(REPORT, 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print('saved', OUT)
