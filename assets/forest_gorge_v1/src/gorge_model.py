"""NW river gorge: the rock walls (stacked blocky slabs, 3 tiers to the rim), scree, the stones under Bridge30's bents.
Blender in the project's convention: Blender (x, y, z) = Unity (-x, -z, y). One object per 50 m segment of the line and
per material (GORGE_S07_RockB ...), so Unity assigns materials by name and puts a MeshCollider on each.

python3.11 -I gorge_model.py <out.blend> <out.fbx>
Writes data/gorge_model.json (ledge spruces for the Terrain, counts) next to the .blend."""
import bpy, bmesh, math, os, sys, json
import numpy as np
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import full_params as FP

D = os.path.dirname(os.path.abspath(__file__))
SEG = 50.0
MATS = ['RockA', 'RockB', 'RockC', 'Snow']
UNDER = np.load(os.path.join(D, '..', 'gorge', 'data', 'bridge_under.npz'))
BINFO = json.load(open(os.path.join(D, '..', 'gorge', 'data', 'bridge_info.json')))
STATS = dict(slabs=0, clamped=0, dropped=0, scree=0, tris=0)
H_NEW = np.load(os.path.join(D, 'data', 'H_new.npy')).astype(np.float64)
CAM_KEEP = []                                   # Unity x, z spots kept free of boulders (the preview's river camera)


def B(ux, uz, uy=0.0):
    """Unity -> Blender (project convention)"""
    return np.array([-ux, -uz, uy])


def par(side, key, t):
    return float(np.interp(t, FP.TP, (FP.PL if side > 0 else FP.PR)[key]))


def frame(t, side):
    """Blender xy of the line at t, ex (along the wall), ey (into the wall, away from the river)"""
    x, z = FP.at(t, 0.0)
    x2, z2 = FP.at(t, side * 1.0)
    o = B(x, z)[:2]
    ey = B(x2, z2)[:2] - o
    ey /= np.linalg.norm(ey)
    ez = np.array([0.0, 0.0, 1.0])
    ex = np.cross(np.r_[ey, 0.0], ez)[:2]                        # ex = ey x ez: right-handed
    return o, ex, ey


def unity_xz(p):
    return -p[0], -p[1]


def on_map(p, margin=1.0):
    ux, uz = unity_xz(p)
    return (FP.X0 + margin <= ux <= FP.X0 + (FP.N - 1) * FP.ST - margin) and (FP.Z0 + margin <= uz <= FP.Z0 + (FP.N - 1) * FP.ST - margin)


# ---------------------------------------------------------------- clearance: Bridge30 and the road approaches
def allowed_top(pts):
    """pts: Blender xy (n, 2). Highest top for a solid over them: 0.25 under the deck / abutments, 0.12 into a post,
    0.12 under the old road surface at the approaches."""
    x0, y0, c = float(UNDER['x0']), float(UNDER['y0']), float(UNDER['cell'])     # concept scene frame
    ux, uz = -pts[:, 0], -pts[:, 1]
    sx, sy = ux - FP.OX, uz - FP.OZ
    j = np.floor((sx - x0) / c).astype(int); i = np.floor((sy - y0) / c).astype(int)
    ok = (i >= 0) & (i < UNDER['under'].shape[0]) & (j >= 0) & (j < UNDER['under'].shape[1])
    lim = np.inf
    if ok.any():
        lim = float(np.minimum(UNDER['under'][i[ok], j[ok]] - 0.25, UNDER['post'][i[ok], j[ok]] + 0.12).min())
    t, s = FP.to_ts(ux, uz)
    r = FP.road_at(ux, uz)
    m = (r > 0.05) & (np.abs(s) > 11.0)
    if m.any():
        lim = min(lim, float(FP.sample(FP.O, ux[m], uz[m]).min()) - 0.12)
    return lim


def footprint(cxy, ex, ey, a, b, margin=0.3):
    u = np.arange(-a - margin, a + margin + 1e-6, 0.25)
    v = np.arange(-b - margin, b + margin + 1e-6, 0.25)
    U, V = np.meshgrid(u, v)
    return cxy + U.reshape(-1, 1) * ex + V.reshape(-1, 1) * ey


def near_bridge(p):
    ux, uz = unity_xz(p)
    return math.hypot(ux - FP.BRIDGE[0], uz - FP.BRIDGE[1]) < 32.0


# ---------------------------------------------------------------- one rock chunk (as in the concept)
def _cut(bm, co, no):
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5, plane_co=co, plane_no=no, clear_outer=True)
    bnd = [e for e in bm.edges if e.is_boundary]
    if bnd:
        bmesh.ops.holes_fill(bm, edges=bnd, sides=0)


def chunk(a, b, c, rng, top_cuts=True, lean=True, jitter=True):
    bm = bmesh.new()
    lx = rng.uniform(-0.12, 0.12) * min(c, 1.5) if lean else 0.0
    ly = rng.uniform(0.04, 0.22) * min(c, 2.0) if lean else 0.0
    tx, ty = (rng.uniform(-0.09, 0.09), rng.uniform(-0.07, 0.05)) if lean else (0.0, 0.0)
    ch = {}
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        ch[(sx, sy)] = (rng.uniform(0.08, 0.5) * a, rng.uniform(0.08, 0.5) * b) if rng.random() < 0.85 else (0.0, 0.0)
    for sz in (-1, 1):
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            cx, cy = ch[(sx, sy)]
            pts = [(sx * (a - cx), sy * b), (sx * a, sy * (b - cy))] if cx > 0 else [(sx * a, sy * b)]
            for x, y in pts:
                if sz > 0:
                    bm.verts.new((x + lx, y + ly, c + tx * x + ty * y))
                else:
                    bm.verts.new((x, y, -c))
    if lean and c > 0.6:
        zc = rng.uniform(-0.35, 0.25) * c
        out = rng.uniform(0.0, 0.3) * min(b, 1.0)
        for x in (-a * rng.uniform(0.3, 0.8), a * rng.uniform(0.3, 0.8)):
            bm.verts.new((x + lx * (zc + c) / (2 * c), -b - out + ly * (zc + c) / (2 * c), zc))
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    if top_cuts:
        if rng.random() < 0.75:
            i, d = rng.uniform(0.15, 0.55) * min(1.2, b), rng.uniform(0.15, 0.7) * min(1.2, c)
            yaw = rng.uniform(-0.35, 0.35)
            _cut(bm, Vector((lx, -b + ly + i, c)), Vector((math.sin(yaw) * d, -math.cos(yaw) * d, i)).normalized())
        for sx in (-1, 1):
            if rng.random() < 0.45:
                i, d = rng.uniform(0.1, 0.45), rng.uniform(0.15, 0.6)
                _cut(bm, Vector((sx * (a - i) + lx, 0, c + tx * sx * a)), Vector((sx * d, 0, i)).normalized())
        for sx in (-1, 1):
            if rng.random() < 0.55:
                p, q, r = rng.uniform(0.3, 1.1), rng.uniform(0.25, 0.9), rng.uniform(0.4, 1.5)
                p1 = Vector((sx * (a - p) + lx, -b + ly, c)); p2 = Vector((sx * a + lx, -b + ly + q, c)); p3 = Vector((sx * a + lx * 0.5, -b + ly * 0.5, c - r))
                no = (p2 - p1).cross(p3 - p1).normalized()
                if no.dot(Vector((sx, -1, 1))) < 0:
                    no = -no
                _cut(bm, p1, no)
    if jitter:
        js = 0.045 * min(a, b, max(c, 0.5))
        for v in bm.verts:
            if v.co.z > -c + 1e-3:
                v.co += Vector(rng.uniform(-js, js, 3))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    V = np.array([v.co[:] for v in bm.verts])
    idx = {v: k for k, v in enumerate(bm.verts)}
    F = [[idx[v] for v in f.verts] for f in bm.faces]
    bm.free()
    return V, F


class Sink:
    """faces in Blender coords, per (segment, material): positions per corner (flat), uv per corner"""
    def __init__(self):
        self.parts = {}

    def add(self, Vw, F, seg, rockmat, rng):
        for f in F:
            P = Vw[f]
            n = np.cross(P[1] - P[0], P[2] - P[0])
            ln = np.linalg.norm(n)
            if ln < 1e-9:
                continue
            n /= ln
            snow = n[2] > 0.85 or (n[2] > 0.66 and rng.random() < (n[2] - 0.66) / 0.19)
            mat = 3 if snow else rockmat
            ux, uz, uy = -P[:, 0], -P[:, 1], P[:, 2]
            if mat == 3:
                uv = np.stack([ux / 2.0, uz / 2.0], 1)                    # the terrain's snow: Unity x, z over 2 m
            else:
                ax = np.argmax(np.abs(n))
                if ax == 2:
                    uv = np.stack([ux, uz], 1) / 2.4
                elif ax == 0:
                    uv = np.stack([uz, uy], 1) / 2.4
                else:
                    uv = np.stack([ux, uy], 1) / 2.4
            key = (seg, mat)
            lst = self.parts.setdefault(key, ([], []))
            lst[0].append(P)
            lst[1].append(uv)

    def build(self, mats):
        objs = []
        for (seg, mat), (Ps, UVs) in sorted(self.parts.items()):
            P = np.concatenate(Ps); UV = np.concatenate(UVs)
            # merge identical corners (same position and uv) to keep the vertex count sane
            key = np.round(np.c_[P, UV], 5)
            uniq, inv = np.unique(key, axis=0, return_inverse=True)
            inv = inv.ravel()
            verts = uniq[:, :3]
            faces = inv.reshape(-1, 3)
            name = f'GORGE_S{seg:02d}_{MATS[mat]}'
            me = bpy.data.meshes.new(name)
            me.from_pydata(verts.tolist(), [], faces.tolist())
            uvl = me.uv_layers.new(name='UVMap')
            loop_uv = uniq[inv][:, 3:5]
            uvl.data.foreach_set('uv', loop_uv.astype(np.float32).ravel())
            me.validate()
            for p in me.polygons:
                p.use_smooth = False
            me.materials.append(mats[mat])
            ob = bpy.data.objects.new(name, me)
            bpy.context.scene.collection.objects.link(ob)
            objs.append(ob)
            STATS['tris'] += len(faces)
        return objs


def place(sink, V, F, cxy, ex, ey, zc, yaw, seg, rockmat, rng):
    c, s_ = math.cos(yaw), math.sin(yaw)
    exr = ex * c + ey * s_; eyr = -ex * s_ + ey * c
    R = np.array([[exr[0], eyr[0], 0.0], [exr[1], eyr[1], 0.0], [0.0, 0.0, 1.0]])
    Vw = V @ R.T + np.array([cxy[0], cxy[1], zc])
    sink.add(Vw, F, seg, rockmat, rng)


def seg_of(t):
    return int(np.clip((t - FP.T_START) // SEG, 0, 99))


# ---------------------------------------------------------------- walls
TIER = {0: ('f0', 'd0', 'z1', None), 1: ('f1', 'd1', 'z2', 'z1'), 2: ('f2', 'd2', 'zr', 'z2')}
T0_WALL = 3.0                                    # rock walls from here (the gorge is faded in above the line start)


def column(sink, rng, side, tier, tc, w, ledge_spots):
    kf, kd, kt, kb = TIER[tier]
    W = par(side, 'W', tc)
    f, d = par(side, kf, tc), par(side, kd, tc) * rng.uniform(0.85, 1.2)
    ztop = par(side, kt, tc) + (rng.uniform(-0.45, 0.3) if tier == 2 else rng.uniform(-0.2, 0.45))
    if tier < 2 and rng.random() < 0.1 and abs(tc - FP.TB) > 12:
        ztop = par(side, TIER[tier + 1][2], tc) + rng.uniform(-0.6, 0.2)
    elif tier > 0 and rng.random() < 0.07:
        ztop -= (ztop - par(side, kb, tc)) * rng.uniform(0.35, 0.6)
    zbot = W - 1.5 if tier == 0 else par(side, kb, tc) - 1.1
    ufront = f + rng.uniform(-0.45, 0.35)
    o, ex, ey = frame(tc, side)
    if not (on_map(o + ey * ufront) and on_map(o + ey * (ufront + d)) and on_map(o + ex * w / 2 + ey * ufront) and on_map(o - ex * w / 2 + ey * ufront)):
        return
    vis0 = W if tier == 0 else zbot + 1.1
    n = int(np.clip(round((ztop - vis0) / rng.uniform(1.5, 2.9)), 1, 4))
    cuts = np.sort(rng.uniform(0.25, 0.85, n - 1)) if n > 1 else np.array([])
    zs = [zbot] + [vis0 + (ztop - vis0) * q for q in cuts] + [ztop]
    yaw = rng.uniform(-0.07, 0.07)
    shift_x, setback = rng.uniform(-0.1, 0.1), 0.0
    rockmat = int(rng.integers(0, 3))
    seg = seg_of(tc)
    for k in range(n):
        z0, z1 = zs[k] - (0.06 if k else 0.0), zs[k + 1]
        a = w / 2 * rng.uniform(0.9, 1.05)
        b = d / 2
        uf = ufront + setback
        cxy = o + ey * (uf + b) + ex * (shift_x + rng.uniform(-0.12, 0.12))
        if near_bridge(cxy) or FP.road_at(*unity_xz(cxy)) > 0.05:
            lim = allowed_top(footprint(cxy, ex, ey, a, b))
            if z1 > lim:
                STATS['clamped'] += 1
                z1 = lim
            if z1 - z0 < 0.45:
                STATS['dropped'] += 1
                break
        c = (z1 - z0) / 2
        V, F = chunk(a, b, c, rng, top_cuts=(k == n - 1 or rng.random() < 0.6))
        place(sink, V, F, cxy, ex, ey, (z0 + z1) / 2, yaw + rng.uniform(-0.05, 0.05), seg, rockmat if rng.random() < 0.8 else int(rng.integers(0, 3)), rng)
        STATS['slabs'] += 1
        setback += rng.uniform(0.0, 0.32)
    if tier < 2:
        ledge_spots.append((side, tier, tc, ufront + d))


def walls(sink, rng):
    spots = []
    for side in (1, -1):
        for tier in (0, 1, 2):
            t = T0_WALL
            while t < FP.T_END:
                w = rng.uniform(1.7, 5.2)
                column(sink, rng, side, tier, t + w / 2, w, spots)
                t += w * rng.uniform(0.72, 0.88)
    return spots


def footings(sink, rng):
    posts = BINFO['posts']
    for grp in ([p for p in posts if p['xyz'][2] < 10], [p for p in posts if p['xyz'][2] > 10]):
        U = np.array([[p['xyz'][0] + FP.OX, p['xyz'][1] + FP.OZ] for p in grp])        # Unity x, z
        t, s = FP.to_ts(U[:, 0], U[:, 1])
        zb = [p['xyz'][2] for p in grp]
        tc, sc = float((t.min() + t.max()) / 2), float(np.mean(s))
        side = 1 if sc > 0 else -1
        top = max(zb) + 0.1
        if side < 0:
            u_in, u_out = abs(sc) - 1.0, par(side, 'f0', tc) + 0.6
            bottom = FP.WL.min() - 1.6
        else:
            u_in, u_out = abs(sc) - 0.95, abs(sc) + 0.95
            bottom = top - 1.0
        a = float(t.max() - t.min()) / 2 + 0.7
        b = (u_out - u_in) / 2
        o, ex, ey = frame(tc, side)
        cxy = o + ey * ((u_in + u_out) / 2)
        V, F = chunk(a, b, (top - bottom) / 2, rng, top_cuts=False, lean=False, jitter=False)
        place(sink, V, F, cxy, ex, ey, (top + bottom) / 2, 0.0, seg_of(tc), 1, rng)
        print(f'footing side {side} t {tc:.2f} s {sc:.2f} u {u_in:.2f}..{u_out:.2f} top {top:.2f}', flush=True)


def boulder(sink, rng, cxy, zc, size, yaw, tseg):
    a, b, c = size * rng.uniform(0.7, 1.2), size * rng.uniform(0.6, 1.0), size * rng.uniform(0.45, 0.8)
    ex = np.array([math.cos(yaw), math.sin(yaw)]); ey = np.array([-ex[1], ex[0]])
    if near_bridge(cxy):
        lim = allowed_top(footprint(cxy, ex, ey, a, b, 0.2))
        if zc + c > lim:
            return
    ux, uz = unity_xz(cxy)
    if any(math.hypot(ux - k[0], uz - k[1]) < 4.0 for k in CAM_KEEP):
        return
    if not on_map(cxy, 2.0):
        return
    V, F = chunk(a, b, c, rng, top_cuts=True)
    place(sink, V, F, cxy, ex, ey, zc, 0.0, seg_of(tseg), int(rng.integers(0, 3)), rng)
    STATS['scree'] += 1


def scree(sink, rng):
    for side in (1, -1):
        t = T0_WALL
        while t < FP.T_END:
            t += rng.uniform(2.0, 5.5)
            o, ex, ey = frame(t, side)
            f0, W = par(side, 'f0', t), par(side, 'W', t)
            for _ in range(rng.integers(1, 3)):
                u = f0 - rng.uniform(0.2, 1.6)
                boulder(sink, rng, o + ey * u + ex * rng.uniform(-1, 1), W - rng.uniform(-0.15, 0.25), rng.uniform(0.3, 0.85), rng.uniform(0, 6.3), t)
            for kf, kz in (('f1', 'z1'), ('f2', 'z2')):
                if rng.random() < 0.55:
                    u = par(side, kf, t) - rng.uniform(0.1, 0.8)
                    boulder(sink, rng, o + ey * u + ex * rng.uniform(-1, 1), par(side, kz, t) + rng.uniform(0.0, 0.2), rng.uniform(0.25, 0.6), rng.uniform(0, 6.3), t)
    t = T0_WALL
    while t < FP.T_END:
        t += rng.uniform(14, 30)
        o, ex, ey = frame(t, 1)
        if abs(t - FP.TB) > 9:
            boulder(sink, rng, o + ey * rng.uniform(-2.5, 2.5), par(1, 'W', t) - rng.uniform(0.0, 0.3), rng.uniform(0.45, 1.1), rng.uniform(0, 6.3), t)


# ---------------------------------------------------------------- spruces on the wide ledges (Terrain trees in Unity)
def ledge_trees(spots, rng):
    names = ['Fir_4', 'Fir_7', 'Spruce_13']
    out, used = [], []
    rng.shuffle(spots)
    for side, tier, t, uback in spots:
        u_next = par(side, 'f1' if tier == 0 else 'f2', t) - 0.4
        gap = u_next - uback
        if gap < 1.3 or rng.random() > 0.22:
            continue
        ux, uz = FP.at(t, side * (uback + gap / 2))
        if any(math.hypot(ux - a, uz - b) < 7.0 for a, b in used) or math.hypot(ux - FP.BRIDGE[0], uz - FP.BRIDGE[1]) < 12:
            continue
        if not (FP.X0 + 2 < ux < -2 and 2 < uz < 598):
            continue
        nm = names[int(rng.integers(0, 3))]
        sc = {'Fir_4': rng.uniform(0.75, 1.1), 'Fir_7': rng.uniform(0.5, 0.75), 'Spruce_13': rng.uniform(0.28, 0.42)}[nm]
        out.append({'prefab': nm, 'x': round(float(ux), 2), 'z': round(float(uz), 2), 'scale': round(float(sc), 3), 'yaw': round(float(rng.uniform(0, 6.283)), 3)})
        used.append((ux, uz))
    return out


# ---------------------------------------------------------------- materials (preview look = what Unity gets)
def materials():
    T = '/mnt/user-data/uploads/snow/Snow/Assets/Locations/Forest/Terrain/Ground/'
    out = []
    for nm, tex, tint in (('M_GorgeRock_A', 'T_GR_Rock_A.png', (1.0, 1.0, 1.0)), ('M_GorgeRock_B', 'T_GR_Rock_A.png', (0.87, 0.88, 0.9)),
                          ('M_GorgeRock_C', 'T_GR_Rock_A.png', (0.74, 0.75, 0.78)), ('M_GorgeSnow', 'T_GR_Floor_A.png', (1.0, 1.0, 1.0))):
        m = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
        m.use_nodes = True
        N, L = m.node_tree.nodes, m.node_tree.links
        pb = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
        pb.inputs['Roughness'].default_value = 0.95
        tx = N.new('ShaderNodeTexImage')
        tx.image = bpy.data.images.get(tex) or bpy.data.images.load(T + tex)
        tx.interpolation = 'Closest'
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
        L.new(tx.outputs['Color'], mx.inputs['A']); mx.inputs['B'].default_value = (*tint, 1)
        L.new(mx.outputs['Result'], pb.inputs['Base Color'])
        out.append(m)
    return out


def build(rng_seed=20261028):
    rng = np.random.default_rng(rng_seed)
    sink = Sink()
    spots = walls(sink, rng)
    footings(sink, rng)
    scree(sink, rng)
    objs = sink.build(materials())
    trees = ledge_trees(spots, rng)
    return objs, trees


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    out_blend, out_fbx = argv[0], argv[1]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs, trees = build()
    root = bpy.data.objects.new('Forest_Gorge', None)
    bpy.context.scene.collection.objects.link(root)
    for o in objs:
        o.parent = root
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=out_fbx, use_selection=True, object_types={'MESH'}, global_scale=1.0,
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                             bake_space_transform=True, mesh_smooth_type='FACE', use_tspace=False, use_triangles=True,
                             colors_type='NONE', add_leaf_bones=False, bake_anim=False, path_mode='STRIP', embed_textures=False)
    json.dump({'ledgeTrees': trees, 'stats': STATS, 'objects': [o.name for o in objs]},
              open(os.path.join(D, 'data', 'gorge_model.json'), 'w'), indent=1)
    print('gorge model', STATS, 'objects', len(objs), 'ledge trees', len(trees), flush=True)


if __name__ == '__main__':
    main()
