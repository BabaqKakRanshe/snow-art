"""Winter preflight kit + fuel can for the Utility Plane (kit v1).
python3 kit_geo.py  ->  out/kit_geo_v1.blend  (plane final blend + collection 'Kit'), out/kit_v1.json

Installed forms are built in the plane build frame (nose -Y, pilot-left +X, up +Z) where they sit on the parked plane;
anything that rests on the ground is built in the PARKED frame (flat ground, z = MAIN_CONTACT_Z) and mapped back with
the inverse park rotation, so it is level when the plane stands tail-down. Hanging parts (streamers) follow parked
gravity. Carry forms (bags, can, funnel, stowed heater) are built at the origin, pivot at the bottom centre.

Refs: aircraftcovers.com/208 (Caravan inlet plugs set of 2 with streamers, exhaust plugs, pitot covers with PVC
install handle, insulated engine cover with velcro under the spinner and belly strap, wing covers with straps under the
wing, wrap-around canopy cover with belly straps); Aerotech Herman Nelson BT400 (duct hose, treated canvas) - here a
compact forced-air heater instead of the 325 kg trailer; NATO 20 l jerry can 470 x 340 x 165 mm."""
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import *
import layout as LY

bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v7_final_v7.blend'))
O, MAT = bpy.data.objects, bpy.data.materials
KC = bpy.data.collections.new('Kit')
bpy.context.scene.collection.children.link(KC)

# ------------------------------------------------------------------ park frame
TH = math.radians(LY.PARK_PITCH_DEG)
PIV = Vector((0.0, LY.MAIN_WHEEL_C[1], LY.MAIN_CONTACT_Z))
R = Matrix.Translation(PIV) @ Matrix.Rotation(-TH, 4, 'X') @ Matrix.Translation(-PIV)     # build -> parked
RI = R.inverted()                                                                       # parked -> build
GZ = LY.MAIN_CONTACT_Z                                                                  # parked ground z
G_BUILD = (RI.to_3x3() @ Vector((0, 0, -1))).normalized()                               # parked gravity in build


def to_parked(p):
    return R @ Vector(p)


def to_build(p):
    return RI @ Vector(p)


# ------------------------------------------------------------------ materials (preview colours; nodes in kit_nodes.py)
KMAT = {
    'kit_RedVinyl': (0.50, 0.03, 0.02), 'kit_Streamer': (0.55, 0.02, 0.02), 'kit_CoverFabric': (0.05, 0.06, 0.07),
    'kit_CoverRed': (0.40, 0.04, 0.03), 'kit_Webbing': (0.02, 0.02, 0.02), 'kit_Buckle': (0.05, 0.05, 0.05),
    'kit_ChockYellow': (0.75, 0.52, 0.03), 'kit_Rope': (0.70, 0.55, 0.05), 'kit_Steel': (0.55, 0.55, 0.55),
    'kit_HeaterBody': (0.75, 0.38, 0.03), 'kit_Duct': (0.03, 0.03, 0.03), 'kit_CanOlive': (0.12, 0.13, 0.06),
    'kit_PlasticBlack': (0.02, 0.02, 0.02), 'kit_Rubber': (0.02, 0.02, 0.02), 'kit_CoverInner': (0.12, 0.12, 0.12),
    'kit_DuctRib': (0.03, 0.03, 0.03), 'kit_SteelHidden': (0.45, 0.45, 0.45),
}
M = {}
for k, c in KMAT.items():
    m = MAT.get(k) or MAT.new(k)
    m.diffuse_color = (*c, 1)
    M[k] = m
MATS = list(KMAT)


def mi(name):
    return MATS.index(name)


OPEN = 'kit_open'                     # face tag: open thin parts (streamers, straps) keep their built winding


UVDONE = 'kit_uvdone'                 # face tag: UVMap already set (tubes: one rectangle each), skip smart project


def tube(bm, path, r, segs=8, mat=0, cap0=True, cap1=True, up_hint=Vector((0, 0, 1))):
    """tube along a polyline with parallel-transport frames (no twist) and its own UVs: u = length, v = around (m);
    the tube unwraps as ONE rectangle (a smart projection of a bent tube gives hollow U / ring islands)"""
    path = [Vector(p) for p in path]
    uvl = bm.loops.layers.uv.get('UVMap') or bm.loops.layers.uv.new('UVMap')
    lay = bm.faces.layers.int.get(UVDONE) or bm.faces.layers.int.new(UVDONE)
    n = len(path)
    tng = []
    for k in range(n):
        t = (path[min(k + 1, n - 1)] - path[max(k - 1, 0)])
        tng.append(t.normalized())
    side, up = ring_frame(path[0], tng[0], up_hint)
    frames = [(side, up)]
    for k in range(1, n):
        rot = tng[k - 1].rotation_difference(tng[k])
        side = (rot @ side).normalized()
        side = (side - tng[k] * side.dot(tng[k])).normalized()
        up = tng[k].cross(side).normalized()
        frames.append((side, up))
    rings, sacc = [], [0.0]
    for k in range(n):
        sd, upv = frames[k]
        rings.append([bm.verts.new(path[k] + (sd * math.cos(2 * math.pi * i / segs) + upv * math.sin(2 * math.pi * i / segs)) * r)
                      for i in range(segs)])
        if k:
            sacc.append(sacc[-1] + (path[k] - path[k - 1]).length)
    circ = 2 * math.pi * r
    for k in range(n - 1):
        for i in range(segs):
            j = (i + 1) % segs
            f = bm.faces.new([rings[k][i], rings[k + 1][i], rings[k + 1][j], rings[k][j]])
            f.material_index = mat
            f[lay] = 1
            for lp in f.loops:
                kk = k if lp.vert in rings[k] else k + 1
                ii = rings[kk].index(lp.vert)
                if ii == 0 and (lp.vert is rings[kk][j] and j == 0):
                    ii = segs
                lp[uvl].uv = (sacc[kk], ii / segs * circ)
    for k_, flag in ((0, cap0), (n - 1, cap1)):
        if flag:
            f = bm.faces.new(rings[k_] if k_ else list(reversed(rings[k_])))
            f.material_index = mat
    return rings


def open_layer(bm):
    """get/create the tag layer BEFORE making faces (a new layer invalidates existing BMFace references)"""
    return bm.faces.layers.int.get(OPEN) or bm.faces.layers.int.new(OPEN)


def tag_open(bm, faces):
    lay = bm.faces.layers.int[OPEN]
    for f in faces:
        f[lay] = 1


def new_obj(name, bm, used=None):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    lay = bm.faces.layers.int.get(OPEN)
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if not (lay and f[lay])])
    ob = obj_from_bm(name, bm, KC, [M[k] for k in MATS])
    if OPEN in ob.data.attributes:
        ob.data.attributes.remove(ob.data.attributes[OPEN])
    shade(ob, 40)
    return ob


# ------------------------------------------------------------------ helpers
dg = bpy.context.evaluated_depsgraph_get()


def bvh_of(names):
    vs, fs = [], []
    for n in names:
        ob = O[n]
        me = ob.evaluated_get(dg).to_mesh()
        off = len(vs)
        vs += [ob.matrix_world @ v.co for v in me.vertices]
        fs += [tuple(off + i for i in p.vertices) for p in me.polygons]
        ob.evaluated_get(dg).to_mesh_clear()
    return BVHTree.FromPolygons(vs, fs)


def hull2d(pts):
    """monotone chain convex hull of (a, b) tuples, CCW"""
    P = sorted(set(pts))
    if len(P) < 3:
        return P
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def resample(poly, n, weights=None):
    """resample a 2D/3D polyline (list of Vector) to n points by arc length (optional density function of s)"""
    d = [0.0]
    for a, b in zip(poly[:-1], poly[1:]):
        d.append(d[-1] + (b - a).length)
    L = d[-1]
    out = []
    for i in range(n):
        t = i / (n - 1)
        if weights:
            t = weights(t)
        s = t * L
        k = max(0, min(len(d) - 2, next((j for j in range(len(d) - 1) if d[j + 1] >= s), len(d) - 2)))
        f = (s - d[k]) / max(d[k + 1] - d[k], 1e-9)
        out.append(poly[k].lerp(poly[k + 1], f))
    return out


def shell(bm, grid, thick, mat, normals=None, close_u=False, mat_inner=None):
    """thick surface from a grid of points [rows][cols] (outer surface); inner offset along -normal by thick;
    mat_inner: material of the inner face and the rim walls (cover lining, UV-packed small)"""
    mat_in = mat if mat_inner is None else mat_inner
    nr, nc = len(grid), len(grid[0])
    if normals is None:
        normals = []
        for i in range(nr):
            row = []
            for j in range(nc):
                du = grid[min(i + 1, nr - 1)][j] - grid[max(i - 1, 0)][j]
                dv = grid[i][min(j + 1, nc - 1)] - grid[i][max(j - 1, 0)]
                n = du.cross(dv)
                row.append(n.normalized() if n.length > 1e-12 else Vector((0, 0, 1)))
            normals.append(row)
    outer = [[bm.verts.new(grid[i][j]) for j in range(nc)] for i in range(nr)]
    inner = [[bm.verts.new(grid[i][j] - normals[i][j] * thick) for j in range(nc)] for i in range(nr)]

    def quad(vs, m):
        try:
            f = bm.faces.new(vs)
            f.material_index = m
        except ValueError:
            pass
    for i in range(nr - 1):
        for j in range(nc - 1):
            quad([outer[i][j], outer[i + 1][j], outer[i + 1][j + 1], outer[i][j + 1]], mat)
            quad([inner[i][j], inner[i][j + 1], inner[i + 1][j + 1], inner[i + 1][j]], mat_in)
    for i in range(nr - 1):                       # side walls along the boundary
        quad([outer[i][0], inner[i][0], inner[i + 1][0], outer[i + 1][0]], mat_in)
        quad([outer[i][nc - 1], outer[i + 1][nc - 1], inner[i + 1][nc - 1], inner[i][nc - 1]], mat_in)
    for j in range(nc - 1):
        quad([outer[0][j], outer[0][j + 1], inner[0][j + 1], inner[0][j]], mat_in)
        quad([outer[nr - 1][j], inner[nr - 1][j], inner[nr - 1][j + 1], outer[nr - 1][j + 1]], mat_in)
    return outer, normals


TEXT_LAYER = 'TextUV'


def streamer(bm, top, length, width, side_dir, mat, curl=0.04, segs=10):
    """REMOVE BEFORE FLIGHT streamer: thin strip hanging along parked gravity from `top`; TextUV u along the strip.
    Two layers 1.5 mm apart, each facing away from the other; the text reads (unmirrored) from both sides."""
    open_layer(bm)
    uvl = bm.loops.layers.uv.get(TEXT_LAYER) or bm.loops.layers.uv.new(TEXT_LAYER)
    g = G_BUILD
    s = side_dir - g * side_dir.dot(g)
    s = s.normalized() if s.length > 1e-6 else Vector((1, 0, 0))
    fwd = g.cross(s).normalized()
    rows = []
    for k in range(segs + 1):
        t = k / segs
        c = top + g * (length * t) + fwd * (curl * math.sin(t * math.pi * 1.5)) + s * (0.01 * math.sin(t * 6.0))
        rows.append([c - s * (width / 2), c + s * (width / 2)])
    th = 0.0015
    A = [[bm.verts.new(p) for p in r] for r in rows]                     # front layer, faces +fwd
    B = [[bm.verts.new(p - fwd * th) for p in r] for r in rows]          # back layer, faces -fwd
    new = []
    for k in range(segs):
        for L, order, back in ((A, (0, 2, 3, 1), False), (B, (0, 1, 3, 2), True)):
            q = [L[k][0], L[k][1], L[k + 1][0], L[k + 1][1]]             # 0 = (k, left) 1 = (k, right) 2 = (k+1, left) 3 = (k+1, right)
            f = bm.faces.new([q[i] for i in order])
            f.material_index = mat
            new.append(f)
            for lp in f.loops:
                kk = k if lp.vert in (L[k][0], L[k][1]) else k + 1
                jj = 0 if lp.vert is L[kk][0] else 1
                lp[uvl].uv = (kk / segs, 1 - jj if back else jj)
    tag_open(bm, new)


def ring_band(bm, pts, normals, width, thick, mat, closed=False):
    """flat strap along a polyline of surface points (pts) lying on a surface with normals; width across.
    Single-sided (faces +normal): side walls would unwrap as hollow rings and waste the atlas."""
    open_layer(bm)
    n = len(pts)
    V = []
    for k in range(n):
        tng = (pts[min(k + 1, n - 1)] - pts[max(k - 1, 0)]).normalized()
        side = tng.cross(normals[k]).normalized()
        V.append([bm.verts.new(pts[k] - side * (width / 2)), bm.verts.new(pts[k] + side * (width / 2))])
    new = []
    for k in range(n - 1):
        try:
            f = bm.faces.new([V[k][0], V[k][1], V[k + 1][1], V[k + 1][0]])
        except ValueError:
            continue
        f.material_index = mat
        new.append(f)
    tag_open(bm, new)


def fabric_sag(p, amp, freq, phase=0.0):
    return amp * math.sin(p * freq + phase)


def conform(verts, bvh, margin, maxd=0.25):
    """push vertices that are inside / closer than margin to the target surface out to margin (nearest-face normal)"""
    n_moved = 0
    for v in verts:
        q, nrm, i, d = bvh.find_nearest(v.co, maxd)
        if q is None:
            continue
        if (v.co - q).dot(nrm) < margin:
            v.co = q + nrm * margin
            n_moved += 1
    return n_moved


def smooth_grid(grid, iters=2, fac=0.5):
    """Laplacian smoothing of the interior of a point grid [rows][cols] (borders kept)"""
    nr, nc = len(grid), len(grid[0])
    for _ in range(iters):
        g2 = [row[:] for row in grid]
        for i in range(1, nr - 1):
            for j in range(1, nc - 1):
                avg = (grid[i - 1][j] + grid[i + 1][j] + grid[i][j - 1] + grid[i][j + 1]) / 4
                g2[i][j] = grid[i][j].lerp(avg, fac)
        grid[:] = g2
    return grid


def streamer_wrap(bm, center, axis, radius_fn, width, mat, segs=24):
    """stowed streamer wound around a body: single-sided band around `axis` through `center`, radius_fn(angle)"""
    s_, u_ = ring_frame(center, axis)
    ax = axis.normalized()
    open_layer(bm)
    uvl = bm.loops.layers.uv.get(TEXT_LAYER) or bm.loops.layers.uv.new(TEXT_LAYER)
    V = []
    for k in range(segs + 1):
        a = 2 * math.pi * k / segs
        p = center + (s_ * math.cos(a) + u_ * math.sin(a)) * radius_fn(a)
        V.append([bm.verts.new(p - ax * (width / 2)), bm.verts.new(p + ax * (width / 2))])
    new = []
    for k in range(segs):
        f = bm.faces.new([V[k][0], V[k][1], V[k + 1][1], V[k + 1][0]])
        f.material_index = mat
        new.append(f)
        for lp in f.loops:
            kk = k if lp.vert in V[k] else k + 1
            lp[uvl].uv = (kk / segs * 0.5, 0 if lp.vert is V[kk][0] else 1)
    tag_open(bm, new)


INFO = {'installed': {}, 'carry': {}}

# ================================================================== targets on the plane
WING = bvh_of(['src_Wing', 'src_WingTE_Center', 'src_WingTE_TipL', 'src_WingTE_TipR', 'Aileron_L', 'Aileron_R',
               'Flap_L', 'Flap_R', 'src_WingDetails', 'FuelCap_L', 'FuelCap_R'])
FUSE = bvh_of(['src_Fuselage', 'src_GlassFixed', 'src_FuseDetails', 'CP_WindshieldFrame'])
FUSEW = bvh_of(['src_Fuselage', 'src_GlassFixed', 'src_FuseDetails', 'CP_WindshieldFrame', 'src_Wing'])
COWL = bvh_of(['src_Fuselage'])
EXH = bvh_of(['src_CowlDetails', 'src_Fuselage'])
INTK = bvh_of(['src_CowlDetails', 'src_Fuselage'])
STOWED = {}                                    # carry versions of the streamer items (streamer wound around the body)

# ================================================================== 1. intake plug (red vinyl over foam) + streamer
IZ = 1.335
face_y0, face_y1 = -4.665, -4.632
ring = lambda hw, hh, y, z=IZ: [Vector((x, y, z + zz)) for x, zz in superellipse(hw, hh, 3.0, 24)]


def intake_plug(stowed):
    bm = bmesh.new()
    vr = loft(bm, [ring(0.142, 0.036, -4.530), ring(0.146, 0.038, face_y1), ring(0.205, 0.088, face_y1),
                   ring(0.212, 0.092, face_y1 - 0.012), ring(0.205, 0.088, face_y0),
                   ring(0.150, 0.050, face_y0 - 0.006)], True, True, True, mat=mi('kit_RedVinyl'))
    conform([v for r in vr[:2] for v in r], INTK, 0.003)
    loop = [Vector((0.06 * math.cos(a), face_y0 - 0.006 - 0.025 * math.sin(a), IZ + 0.02)) for a in
            (math.pi * i / 10 for i in range(11))]
    sweep(bm, loop, 0.012, 0.002, 6, mat=mi('kit_Webbing'))                       # grab loop
    if stowed:                                            # streamer wound round the rim, 3 mm off the vinyl
        bm.normal_update()
        bv = BVHTree.FromBMesh(bm)
        cen = Vector((0.0, face_y1 - 0.012, IZ))

        def rimf(a):
            d = Vector((math.cos(a), 0.0, math.sin(a)))
            h = bv.ray_cast(cen + d * 0.5, -d, 0.5)
            return (0.5 - h[3] + 0.003) if h[0] is not None else 0.22
        streamer_wrap(bm, cen, Vector((0, 1, 0)), rimf, 0.03, mi('kit_Streamer'), 48)
    else:
        streamer(bm, Vector((0.0, face_y0 - 0.004, IZ - 0.086)), 0.55, 0.05, Vector((1, 0, 0)), mi('kit_Streamer'))
    return bm


plug = new_obj('Kit_IntakePlug', intake_plug(False))
set_pivot(plug, (0.0, face_y0, IZ))
INFO['installed']['Kit_IntakePlug'] = dict(socket='Socket_Kit_IntakePlug', pos=tuple(plug.matrix_world.translation))
STOWED['SM_Kit_IntakePlug'] = (intake_plug(True), 0.9, 'intake plug, streamer wound round the rim')

# ================================================================== 2. exhaust plugs (foam plug in the stack + vinyl cap)
EX_C = Vector((0.735, -3.802, 1.563))
EX_A = Vector((0.138, 0.988, -0.059)).normalized()


def exhaust_plug(c, a, stowed):
    side_v, up_v = ring_frame(c, a)
    N = 24
    dirs = [side_v * math.cos(2 * math.pi * k / N) + up_v * math.sin(2 * math.pi * k / N) for k in range(N)]
    r_in = []
    for d in dirs:
        h = EXH.ray_cast(c - a * 0.01, d, 0.3)
        r_in.append(h[3] if h[0] is not None else 0.075)
    u_lip = 0.0                                          # where the stack ends (outboard ray stops hitting)
    k_out = max(range(N), key=lambda k: dirs[k].x * math.copysign(1.0, c.x))
    for k in range(16):
        u = 0.002 * k
        if EXH.ray_cast(c + a * u, dirs[k_out], 0.3)[0] is None:
            break
        u_lip = u
    ring_ = lambda u, rf: [c + a * u + dirs[k] * rf(k) for k in range(N)]
    bm = bmesh.new()
    loft(bm, [ring_(u_lip - 0.080, lambda k: r_in[k] - 0.016), ring_(u_lip - 0.070, lambda k: r_in[k] - 0.004),
              ring_(u_lip - 0.004, lambda k: r_in[k] - 0.004)], True, True, True, mat=mi('kit_RedVinyl'))
    ro = lambda k: r_in[k] + 0.015
    vr = loft(bm, [ring_(u_lip + 0.003, lambda k: r_in[k] + 0.0075), ring_(u_lip - 0.020, lambda k: r_in[k] + 0.0075),
                   ring_(u_lip - 0.020, lambda k: r_in[k] + 0.0135), ring_(u_lip + 0.008, ro),
                   ring_(u_lip + 0.022, lambda k: ro(k) * 0.84), ring_(u_lip + 0.032, lambda k: ro(k) * 0.48),
                   ring_(u_lip + 0.036, lambda k: ro(k) * 0.05)], True, True, True, mat=mi('kit_RedVinyl'))
    conform([v for r in vr for v in r], EXH, 0.003)
    if stowed:
        streamer_wrap(bm, c + a * (u_lip - 0.006), a, lambda ang: max(r_in) + 0.020, 0.05, mi('kit_Streamer'))
    else:
        k_dn = min(range(N), key=lambda k: dirs[k].dot(G_BUILD) * -1)    # cap point facing the ground
        streamer(bm, c + a * (u_lip + 0.004) + dirs[k_dn] * (r_in[k_dn] + 0.012), 0.50, 0.05, side_v,
                 mi('kit_Streamer'))
    return bm, u_lip


for side, sg in (('L', 1), ('R', -1)):
    c = Vector((sg * EX_C.x, EX_C.y, EX_C.z))
    a = Vector((sg * EX_A.x, EX_A.y, EX_A.z)).normalized()
    bm, u_lip = exhaust_plug(c, a, False)
    ob = new_obj(f'Kit_ExhaustCover_{side}', bm)
    set_pivot(ob, tuple(c + a * u_lip))
    INFO['installed'][ob.name] = dict(socket=f'Socket_Kit_ExhaustCover_{side}', pos=tuple(c + a * u_lip))
    if side == 'L':
        STOWED['SM_Kit_ExhaustCover'] = (exhaust_plug(c, a, True)[0], 0.3, 'exhaust plug, streamer wound round the cap')

# ================================================================== 3. pitot cover (sleeve, velcro strap, streamer)
PT_TIP = Vector((4.600, -2.472, 2.573))


def pitot_cover(stowed):
    bm = bmesh.new()
    revolve(bm, [(-2.490, 0.0), (-2.488, 0.012), (-2.482, 0.020), (-2.470, 0.023), (-2.300, 0.023),
                 (-2.290, 0.020)], 'Y', (PT_TIP.x, 0.0, PT_TIP.z), segs=16, mat=mi('kit_RedVinyl'))
    revolve(bm, [(-2.330, 0.026), (-2.300, 0.026)], 'Y', (PT_TIP.x, 0.0, PT_TIP.z), segs=16, mat=mi('kit_Webbing'))
    if stowed:
        streamer_wrap(bm, Vector((PT_TIP.x, -2.40, PT_TIP.z)), Vector((0, 1, 0)), lambda ang: 0.0255, 0.05,
                      mi('kit_Streamer'), 16)
    else:
        streamer(bm, Vector((PT_TIP.x, -2.486, PT_TIP.z - 0.02)), 0.45, 0.05, Vector((1, 0, 0)), mi('kit_Streamer'))
    return bm


ob = new_obj('Kit_PitotCover', pitot_cover(False))
set_pivot(ob, tuple(PT_TIP))
INFO['installed']['Kit_PitotCover'] = dict(socket='Socket_Kit_PitotCover', pos=tuple(PT_TIP))
STOWED['SM_Kit_PitotCover'] = (pitot_cover(True), 0.15, 'pitot cover, streamer wound round the sleeve')


# ================================================================== 4. wing covers (convex envelope of each section)
def wing_section(x, n=34):
    """outer envelope of the wing section at span x: from the lower LE wrap over the top to the TE"""
    zc = 2.72 + max(0.0, abs(x) - 0.76) * math.tan(math.radians(2.0))
    yc = -1.45
    pts = []
    for k in range(240):
        th = 2 * math.pi * k / 240
        d = Vector((0.0, math.cos(th), math.sin(th) * 0.35)).normalized()
        o = Vector((x, yc, zc)) + Vector((0.0, math.cos(th) * 1.8, math.sin(th) * 0.6))
        h = WING.ray_cast(o, (Vector((x, yc, zc)) - o).normalized(), 3.0)
        if h[0] is not None:
            pts.append((h[0].y, h[0].z))
    hull = hull2d(pts)
    # keep the part from the TE over the top to ~0.11 m behind the LE on the lower side
    y_le = min(p[0] for p in hull)
    y_te = max(p[0] for p in hull)
    hv = [Vector((0.0, p[0], p[1])) for p in hull]          # CCW in (y, z): from rightmost going up = TE -> top -> LE
    i_te = max(range(len(hv)), key=lambda i: (hv[i].y, hv[i].z))
    seq = hv[i_te:] + hv[:i_te]
    # walk CCW from TE: upper surface first (increasing angle) until LE, then lower until y > y_le + 0.11
    out = [seq[0]]
    passed_le = False
    for p in seq[1:]:
        if abs(p.y - y_le) < 1e-6:
            passed_le = True
        if passed_le and p.y > y_le + 0.11:
            break
        out.append(p)
    prof = resample(out, n, weights=lambda t: 0.85 * (0.5 - 0.5 * math.cos(math.pi * t)) + 0.15 * t)   # 0->0, 1->1, denser at the hems
    res = []
    for k, p in enumerate(prof):
        q = prof[min(k + 1, n - 1)] - prof[max(k - 1, 0)]
        nrm = Vector((0.0, q.z, -q.y)).normalized()          # outward for a CCW contour in (y, z)
        res.append((Vector((x, p.y, p.z)), nrm))
    return res, y_le, y_te


WSAG = lambda x, k: 0.004 * math.sin(abs(x) * 7.0 + k * 0.6)          # slack fabric ripple
for side, sg in (('L', 1), ('R', -1)):
    xs = [sg * (0.82 + (6.95 - 0.82) * i / 46) for i in range(47)]
    grid, nrms = [], []
    for x in xs:
        sec, y_le, y_te = wing_section(x)
        row, nrow = [], []
        for k, (p, nrm) in enumerate(sec):
            q = p + nrm * (0.012 + WSAG(x, k))
            if k == 0:                                           # TE hem: overhang and droop
                q = q + Vector((0, 0.03, -0.015))
            row.append(q)
            nrow.append(nrm)
        grid.append(row)
        nrms.append(nrow)
    bm = bmesh.new()
    outer, _ = shell(bm, grid, 0.004, mi('kit_CoverFabric'), nrms, mat_inner=mi('kit_CoverInner'))
    conform(bm.verts, WING, 0.003)
    # straps under the wing at 4 stations, around the chord, with a buckle on the lower side
    for xs_ in (1.65, 2.65, 4.15, 5.65):
        x = sg * xs_
        sec, y_le, y_te = wing_section(x)
        lower = []
        for k in range(16):
            y = (y_le + 0.11) + (y_te - 0.02 - (y_le + 0.11)) * k / 15
            h = WING.ray_cast(Vector((x, y, 1.5)), Vector((0, 0, 1)), 3.0)
            if h[0] is not None:
                lower.append((h[0] - Vector((0, 0, 0.008)), Vector((0, 0, -1))))
        loop_pts = [p + n * (0.012 + WSAG(x, k) + 0.0055) for k, (p, n) in enumerate(sec)] + [p for p, n in lower]
        loop_nrm = [n for p, n in sec] + [n for p, n in lower]
        ring_band(bm, loop_pts, loop_nrm, 0.045, 0.003, mi('kit_Webbing'))
        if lower:
            bpt = lower[len(lower) // 2][0]
            box(bm, bpt + Vector((0, 0, -0.008)), (0.055, 0.04, 0.012), mat=mi('kit_Buckle'), bevel=0.003, bevel_segs=1)
    ob = new_obj(f'Kit_WingCover_{side}', bm)
    set_pivot(ob, (sg * 3.9, -1.5, 2.95))
    INFO['installed'][ob.name] = dict(socket=f'Socket_Kit_WingCover_{side}', pos=tuple(ob.matrix_world.translation))


# ================================================================== 5. windshield cover (over the windshield, belly strap)
def hood_point(bvh, y, ang, zc=1.62, rad=2.0):
    d = Vector((math.sin(ang), 0.0, math.cos(ang)))
    o = Vector((0.0, y, zc)) + d * rad
    h = bvh.ray_cast(o, -d, rad * 2)
    if h[0] is None:
        return None, None
    return h[0], (h[1] if h[1].dot(d) > 0 else -h[1])            # normal facing the ray origin (outside)


def strap_loop(y, bvhs, off=0.004):
    """belly strap path at station y: outermost surface of several BVHs (fuselage + the cover itself), off above it"""
    pts, nn = [], []
    for k in range(49):
        a = math.radians(-180 + 7.5 * k)
        org = Vector((0.0, y, 1.62)) + Vector((math.sin(a), 0.0, math.cos(a))) * 2.0
        best = None
        for bv in bvhs:
            p, n = hood_point(bv, y, a)
            if p is not None and (best is None or (p - org).length < best[0]):
                best = ((p - org).length, p, n)
        if best:
            pts.append(best[1] + best[2] * off)
            nn.append(best[2])
    return pts, nn


def hood_lim(bvh, y, xlim):
    """angle (from the top) where the hood hit point reaches |x| = xlim: coarse 1 deg search + bisection"""
    prev, hi = 0.0, None
    for k in range(1, 121):
        a = math.radians(k)
        p, n = hood_point(bvh, y, a)
        if p is None or abs(p.x) > xlim:
            hi = a
            break
        prev = a
    if hi is None:
        return prev
    lo = prev
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        p, n = hood_point(bvh, y, mid)
        if p is None or abs(p.x) > xlim:
            hi = mid
        else:
            lo = mid
    return lo


WS_Y0, WS_Y1, WS_XLIM = -3.33, -2.62, 0.70          # behind the engine cover's rear hem (-3.345) .. roof/wing joint; side edge on the A-pillar
WS_ZLIM = lambda y: 1.95 + 0.20 * (y - WS_Y0) / (WS_Y1 - WS_Y0)  # side hem: hangs ~0.3 m down the door windows


def taut_section(bvh, y, xlim, zlim, n=25):
    """fabric pulled taut over the cabin at station y: upper chain of the convex hull of the cross-section,
    clipped at |x| = xlim (bridges window recesses and frame steps); returns n points + outward normals"""
    pts = []
    for k in range(201):
        p, _ = hood_point(bvh, y, math.radians(-100 + k))
        if p is not None:
            pts.append((p.x, p.z))
    hull = hull2d(pts)                                # CCW in (x, z)
    i_r = max(range(len(hull)), key=lambda i: hull[i])
    i_l = min(range(len(hull)), key=lambda i: hull[i])
    up, i = [hull[i_r]], i_r
    while i != i_l:                                   # upper chain: rightmost -> over the top -> leftmost
        i = (i + 1) % len(hull)
        up.append(hull[i])
    def clip_keep(chain, f):
        """keep the part of a polyline where f(x, z) >= 0, with exact (linear) cut points"""
        out = []
        for a, b in zip(chain[:-1], chain[1:]):
            fa, fb = f(*a), f(*b)
            if fa >= 0:
                out.append(a)
            if (fa >= 0) != (fb >= 0):
                t = fa / (fa - fb)
                out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        if f(*chain[-1]) >= 0:
            out.append(chain[-1])
        return out
    clip = clip_keep(up, lambda x, z: z - zlim)
    clip = clip_keep(clip, lambda x, z: xlim - abs(x))
    poly = [Vector((0.0, x, z)) for x, z in clip]     # (0, x, z) so resample works on 3D vectors
    prof = resample(poly, n)
    res = []
    for k, q in enumerate(prof):
        t = prof[min(k + 1, n - 1)] - prof[max(k - 1, 0)]
        nx, nz = t.z, -t.y                            # outward normal of the CCW upper chain
        L = math.hypot(nx, nz) or 1.0
        res.append((Vector((q.y, y, q.z)), Vector((nx / L, 0.0, nz / L))))
    return res


ys = [WS_Y0 + (WS_Y1 - WS_Y0) * i / 30 for i in range(31)]
grid, nrms = [], []
for y in ys:
    sec = taut_section(FUSE, y, WS_XLIM, WS_ZLIM(y))
    grid.append([p + n * (0.014 + 0.003 * math.sin(j * 0.9 + y * 30)) for j, (p, n) in enumerate(sec)])
    nrms.append([n for p, n in sec])
smooth_grid(grid, 3, 0.5)
nrms = smooth_grid([[n.copy() for n in r] for r in nrms], 3, 0.5)
nrms = [[n.normalized() for n in r] for r in nrms]
bm = bmesh.new()
shell(bm, grid, 0.004, mi('kit_CoverFabric'), nrms, mat_inner=mi('kit_CoverInner'))
conform(bm.verts, FUSEW, 0.003)
# belly strap around the fuselage at the front edge of the cover
bm.normal_update()
pts, nn = strap_loop(-3.31, [FUSE, BVHTree.FromBMesh(bm)])     # strap clear of the engine cover (ends at y -3.345)
ring_band(bm, pts, nn, 0.045, 0.003, mi('kit_Webbing'))
bot = min(pts, key=lambda p: p.z)
box(bm, bot + Vector((0, 0, -0.008)), (0.06, 0.045, 0.014), mat=mi('kit_Buckle'), bevel=0.003, bevel_segs=1)
ob = new_obj('Kit_WindshieldCover', bm)
set_pivot(ob, (0.0, -2.95, 2.35))
INFO['installed']['Kit_WindshieldCover'] = dict(socket='Socket_Kit_WindshieldCover', pos=(0.0, -2.95, 2.35))

# ================================================================== 6. insulated engine cover (red, quilted, open bottom)
ys = [-4.585 + (-3.345 + 4.585) * i / 40 for i in range(41)]
grid, nrms = [], []
for y in ys:
    row, nrow = [], []
    lim = 0.0
    for k in range(1, 120):
        a = math.radians(k)
        p, n = hood_point(COWL, y, a)
        if p is None or p.z < 1.70:
            break
        lim = a
    for j in range(29):
        a = -lim + 2 * lim * j / 28
        p, n = hood_point(COWL, y, a)
        puff = 0.022 + 0.004 * math.cos(j * 1.3) * math.cos(y * 25)
        row.append(p + n * puff)
        nrow.append(n)
    grid.append(row)
    nrms.append(nrow)
bm = bmesh.new()
shell(bm, grid, 0.018, mi('kit_CoverRed'), nrms, mat_inner=mi('kit_CoverInner'))
conform(bm.verts, COWL, 0.003)
bm.normal_update()
pts, nn = strap_loop(-3.40, [FUSE, BVHTree.FromBMesh(bm)])
ring_band(bm, pts, nn, 0.045, 0.003, mi('kit_Webbing'))
ob = new_obj('Kit_EngineCover', bm)
set_pivot(ob, (0.0, -3.95, 1.95))
INFO['installed']['Kit_EngineCover'] = dict(socket='Socket_Kit_EngineCover', pos=(0.0, -3.95, 1.95))


# ================================================================== 7. wheel chocks (yellow urethane pairs + rope), parked frame
def chock(bm, cx, cy, dirn, w, toe, face_top, h, back, mat):
    """wedge in the parked frame; dirn = +1 chock aft of the contact, -1 ahead; toe/face_top/back = distances"""
    prof = [(toe, 0.0), (face_top, h), (back - 0.02, h), (back, h - 0.02), (back, 0.0)]
    rings_ = []
    for xo in (-w / 2, w / 2):
        rings_.append([Vector((cx + xo, cy + dirn * d, GZ + z)) for d, z in prof])
    vr = loft(bm, rings_, True, True, True, mat=mat)
    return vr


def rope(bm, pts, r, mat, segs=6):
    tube(bm, pts, r, segs, mat=mat)


def chock_pair(name, wheel_c_build, r, width, h, sock):
    cpk = to_parked((wheel_c_build[0], wheel_c_build[1], wheel_c_build[2] - r))
    cy, cx = cpk.y, cpk.x
    d_top = math.sqrt(max(r * r - (r - h) ** 2, 0.0)) + 0.03
    toe = d_top - 0.12 * (h / 0.14)
    back = d_top + 0.18 * (h / 0.14)
    bm = bmesh.new()
    chock(bm, cx, cy, 1, width, toe, d_top, h, back, mi('kit_ChockYellow'))
    chock(bm, cx, cy, -1, width, toe, d_top, h, back, mi('kit_ChockYellow'))
    xo = cx + math.copysign(width / 2 + 0.015, cx if abs(cx) > 1e-3 else 1.0)
    ends = [Vector((xo, cy - back + 0.05, GZ + h * 0.55)), Vector((xo, cy + back - 0.05, GZ + h * 0.55))]
    pts = [ends[0].lerp(ends[1], t) + Vector((0, 0, -h * 0.45 * math.sin(math.pi * t))) for t in
           (i / 14 for i in range(15))]
    rope(bm, pts, 0.006, mi('kit_Rope'))
    for e in ends:
        rope(bm, [e + Vector((0, -0.015, 0)), e + Vector((0, 0.015, 0))], 0.011, mi('kit_Rope'))
    bm.transform(RI)
    ob = new_obj(name, bm)
    set_pivot(ob, tuple(to_build((cx, cy, GZ))))
    INFO['installed'][name] = dict(socket=sock, pos=tuple(ob.matrix_world.translation))
    return ob


def tyre_width(name):
    xs_ = [(O[name].matrix_world @ v.co).x for v in O[name].data.vertices]
    return max(xs_) - min(xs_)


W_MAIN, W_TAIL = tyre_width('Wheel_L') + 0.06, tyre_width('TailWheel') + 0.06       # 0.46 / 0.23 m
chock_pair('Kit_Chocks_L', LY.MAIN_WHEEL_C, LY.MAIN_WHEEL_R, W_MAIN, 0.14, 'Socket_Kit_Chocks_L')
chock_pair('Kit_Chocks_R', (-LY.MAIN_WHEEL_C[0], *LY.MAIN_WHEEL_C[1:]), LY.MAIN_WHEEL_R, W_MAIN, 0.14, 'Socket_Kit_Chocks_R')
chock_pair('Kit_Chocks_Tail', LY.TAIL_WHEEL_C, LY.TAIL_WHEEL_R, W_TAIL, 0.08, 'Socket_Kit_Chocks_Tail')


# ================================================================== 8. tie-downs (screw anchor + rope to the fitting)
def screw_anchor(bm, base):
    """galvanised screw anchor: eye ring above ground, shaft + helix below (only the top 0.12 m shows)"""
    sweep(bm, [base + Vector((0, 0, -0.35)), base + Vector((0, 0, -0.005))], 0.009, 0.009, 8, mat=mi('kit_SteelHidden'),
          cap1=False)                                                                 # buried shaft
    sweep(bm, [base + Vector((0, 0, -0.005)), base + Vector((0, 0, 0.04))], 0.009, 0.009, 8, mat=mi('kit_Steel'),
          cap0=False)
    eye = [base + Vector((0.032 * math.cos(a), 0.0, 0.075 + 0.032 * math.sin(a))) for a in
           (2 * math.pi * i / 16 for i in range(17))]
    sweep(bm, eye, 0.006, 0.006, 6, mat=mi('kit_Steel'), cap0=False, cap1=False)
    helix = [base + Vector((0.05 * math.cos(t), 0.05 * math.sin(t), -0.10 - 0.035 * t / math.pi)) for t in
             (i * 0.35 for i in range(28))]
    sweep(bm, helix, 0.012, 0.003, 6, mat=mi('kit_SteelHidden'))


def tie_down(name, attach_build, off_parked, sock):
    a = to_parked(attach_build)
    g = Vector((a.x + off_parked[0], a.y + off_parked[1], GZ))
    bm = bmesh.new()
    screw_anchor(bm, g)
    top = g + Vector((0, 0, 0.075 + 0.032))
    pts = []
    L = (a - top).length
    for i in range(21):
        t = i / 20
        pts.append(top.lerp(a, t) + Vector((0, 0, -0.02 * L * math.sin(math.pi * t))))
    rope(bm, pts, 0.007, mi('kit_Rope'))
    for p in (top, a):                                      # knots
        sweep(bm, [p + Vector((0, 0, -0.02)), p + Vector((0, 0, 0.02))], 0.014, 0.014, 8, mat=mi('kit_Rope'))
    bm.transform(RI)
    ob = new_obj(name, bm)
    set_pivot(ob, tuple(to_build(g)))
    INFO['installed'][name] = dict(socket=sock, pos=tuple(ob.matrix_world.translation),
                                   attach=tuple(attach_build), ropeLength=round(L, 3))
    return ob


tie_down('Kit_TieDown_L', (3.36, -1.75, 2.585), (0.85, 0.35), 'Socket_Kit_TieDown_L')
tie_down('Kit_TieDown_R', (-3.36, -1.75, 2.585), (-0.85, 0.35), 'Socket_Kit_TieDown_R')
tie_down('Kit_TieDown_Tail', (0.0, 3.95, 1.715), (0.32, -0.18), 'Socket_Kit_TieDown_Tail')   # down-forward-left, clear of the tail wheel


# ================================================================== 9. engine preheater (compact forced-air heater + duct)
def heater_body(bm, base, yaw):
    """base = ground point under the heater centre (parked frame); outlet points along local +Y rotated by yaw"""
    Rz = Matrix.Rotation(yaw, 4, 'Z')
    T = Matrix.Translation(base) @ Rz
    b2 = bmesh.new()
    box(b2, (0, 0, 0.13), (0.36, 0.72, 0.18), mat=mi('kit_HeaterBody'), bevel=0.02, bevel_segs=2)       # tank
    box(b2, (0, -0.30, 0.235), (0.07, 0.05, 0.03), mat=mi('kit_PlasticBlack'), bevel=0.006, bevel_segs=1)
    revolve(b2, [(-0.30, 0.0), (-0.30, 0.13), (-0.26, 0.15), (0.24, 0.15), (0.28, 0.12), (0.36, 0.09),
                 (0.40, 0.085)], 'Y', (0, 0, 0.38), segs=24, mat=mi('kit_HeaterBody'))                   # burner can
    for yy in (-0.27, -0.22, -0.17):                                                                      # rear grille rings
        revolve(b2, [(yy, 0.151), (yy + 0.012, 0.151)], 'Y', (0, 0, 0.38), segs=24, mat=mi('kit_Steel'))
    for sx in (-1, 1):                                                                                    # handle frame
        frame = [Vector((sx * 0.17, -0.32, 0.22)), Vector((sx * 0.17, -0.32, 0.58)),
                 Vector((sx * 0.17, -0.31, 0.61)), Vector((sx * 0.17, -0.28, 0.62)),
                 Vector((sx * 0.17, 0.16, 0.62)), Vector((sx * 0.17, 0.19, 0.61)),
                 Vector((sx * 0.17, 0.20, 0.58)), Vector((sx * 0.17, 0.20, 0.22))]   # bent tube, rounded corners
        tube(b2, frame, 0.012, 8, mat=mi('kit_Steel'))
        revolve(b2, [(-0.035, 0.0), (-0.035, 0.08), (0.035, 0.08), (0.035, 0.0)], 'X',
                (sx * 0.21, -0.25, 0.08), segs=16, mat=mi('kit_Rubber'))                                   # wheels
    sweep(b2, [Vector((-0.17, -0.32, 0.62)), Vector((0.17, -0.32, 0.62))], 0.014, 0.014, 8, mat=mi('kit_Rubber'))
    box(b2, (0, 0.28, 0.02), (0.30, 0.05, 0.04), mat=mi('kit_Rubber'), bevel=0.005, bevel_segs=1)          # front foot
    b2.transform(T)
    me = bpy.data.meshes.new('_tmp')
    b2.to_mesh(me)
    b2.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return T @ Vector((0, 0.40, 0.38)), (Rz.to_3x3() @ Vector((0, 1, 0)))


def duct(bm, pts, r, mat, ribs=True):
    """flexible duct: tube along a path with helical rib rings"""
    path = resample(pts, 60)
    tube(bm, path, r, 16, mat=mat, cap0=False, cap1=False)
    if ribs:
        for k in range(1, 59, 2):
            p = path[k]
            tng = (path[k + 1] - path[k - 1]).normalized()
            s, u = ring_frame(p, tng)
            ring_ = [p + (s * math.cos(a) + u * math.sin(a)) * (r + 0.004) for a in
                     (2 * math.pi * i / 16 for i in range(17))]
            sweep(bm, ring_, 0.004, 0.004, 4, mat=mi('kit_DuctRib'), cap0=False, cap1=False)


INTAKE_FACE_B = Vector((0.0, -4.66, IZ))
ip = to_parked(INTAKE_FACE_B)                       # intake face in the parked frame (~1.75 m above ground)
HB = Vector((0.85, ip.y - 1.05, GZ))                # heater ahead-left of the nose, under the stopped prop's free sector
bm = bmesh.new()
outlet, odir = heater_body(bm, HB, math.radians(-145))
end = Vector((0.0, ip.y - 0.06, ip.z))               # adapter mouth just ahead of the intake face
c1 = outlet + odir * 0.35
c2 = end + Vector((0.0, -0.45, -0.55))
pts = [outlet] + [p for p in bezier(outlet + odir * 0.05, c1, c2, 12)] + bezier(c2, end + Vector((0, -0.30, -0.25)), end, 10)
duct(bm, pts, 0.075, mi('kit_Duct'))
# fishtail adapter into the intake (0.28 x 0.07 mouth)
ad = [Vector((0.0, end.y - 0.10, end.z)), Vector((0.0, end.y - 0.05, end.z)), Vector((0.0, end.y + 0.035, end.z))]
loft(bm, [[Vector((p.x + 0.075 * math.cos(a) * (1 + 0.85 * k), p.y, p.z + 0.075 * math.sin(a) * (1 - 0.55 * k)))
           for a in (2 * math.pi * i / 16 for i in range(16))] for k, p in zip((0.0, 0.5, 1.0), ad)],
     True, False, False, mat=mi('kit_Steel'))
bm.transform(RI)
ob = new_obj('Kit_Heater', bm)
set_pivot(ob, tuple(to_build(HB)))
INFO['installed']['Kit_Heater'] = dict(socket='Socket_Kit_Heater', pos=tuple(ob.matrix_world.translation),
                                       ductEnd=tuple(to_build(end)))

# ================================================================== CARRY FORMS (origin, pivot at the bottom centre)
CARRY = []


def carry_obj(name, bm, mass, note):
    ob = new_obj(name, bm)
    vs = [v.co for v in ob.data.vertices]
    zmin = min(v.z for v in vs)
    cx = (min(v.x for v in vs) + max(v.x for v in vs)) / 2
    cy = (min(v.y for v in vs) + max(v.y for v in vs)) / 2
    ob.data.transform(Matrix.Translation((-cx, -cy, -zmin)))
    ob.location = (0, 0, 0)
    INFO['carry'][name] = dict(mass=mass, note=note,
                               size=[round(max(v[i] for v in ob.data.vertices for _ in [0]) if False else 0, 3) for i in range(3)])
    dims = [round(max(v.co[i] for v in ob.data.vertices) - min(v.co[i] for v in ob.data.vertices), 3) for i in range(3)]
    INFO['carry'][name]['size'] = dims
    CARRY.append(ob)
    return ob


def bag_cylinder(bm, length, rad, mat, handle=True):
    prof = [(-length / 2, 0.0), (-length / 2, rad * 0.75), (-length / 2 + 0.03, rad), (length / 2 - 0.03, rad),
            (length / 2, rad * 0.75), (length / 2, 0.0)]
    revolve(bm, prof, 'X', (0, 0, rad), segs=20, mat=mat,
            radial_fn=lambda i, j, r: r * (1.0 + 0.04 * math.sin(i * 1.7 + j)))
    if handle:
        for xo in (-length * 0.22, length * 0.22):
            sweep(bm, [Vector((xo, -0.03, 2 * rad - 0.01)), Vector((xo, -0.02, 2 * rad + 0.05)),
                       Vector((xo, 0.02, 2 * rad + 0.05)), Vector((xo, 0.03, 2 * rad - 0.01))], 0.012, 0.002, 6,
                  mat=mi('kit_Webbing'))
    for xo in (-length / 2 + 0.06, length / 2 - 0.06):     # compression straps: closed flat loops round the bag
        rr = rad * 1.045 + 0.004
        streamer_wrap(bm, Vector((xo, 0.0, rad)), Vector((1, 0, 0)), lambda a: rr, 0.04, mi('kit_Webbing'), 32)


bm = bmesh.new()
bag_cylinder(bm, 0.72, 0.16, mi('kit_CoverFabric'))
carry_obj('SM_Kit_WingCoverBag', bm, 4.5, 'one wing cover, rolled')
bm = bmesh.new()
bag_cylinder(bm, 0.48, 0.13, mi('kit_CoverFabric'))
carry_obj('SM_Kit_WindshieldCoverBag', bm, 2.2, 'windshield cover, rolled')
bm = bmesh.new()
box(bm, (0, 0, 0.13), (0.52, 0.34, 0.26), mat=mi('kit_CoverRed'), bevel=0.06, bevel_segs=3)
for xo in (-0.15, 0.15):
    sweep(bm, [Vector((xo, -0.03, 0.25)), Vector((xo, -0.02, 0.31)), Vector((xo, 0.02, 0.31)), Vector((xo, 0.03, 0.25))],
          0.012, 0.002, 6, mat=mi('kit_Webbing'))
carry_obj('SM_Kit_EngineCoverBag', bm, 3.8, 'insulated engine cover, folded')
bm = bmesh.new()
bag_cylinder(bm, 0.46, 0.11, mi('kit_CoverFabric'))
carry_obj('SM_Kit_TieDownBag', bm, 6.0, '3 screw anchors + 3 ropes')

# jerry can 470 x 340 x 165 (NATO 20 l), olive drab, three handles, cap at the front corner
bm = bmesh.new()
H, Wd, D = 0.47, 0.34, 0.165
box(bm, (0, 0, (H - 0.035) / 2), (Wd, D, H - 0.035), mat=mi('kit_CanOlive'), bevel=0.018, bevel_segs=2)
for sx in (-1, 1):                                       # X embossing (raised ribs on both big faces)
    for sy in (-1, 1):
        a = Vector((sx * 0.13, sy * (D / 2 + 0.002), 0.06))
        b = Vector((-sx * 0.13, sy * (D / 2 + 0.002), 0.40))
        sweep(bm, [a, b], 0.010, 0.004, 6, mat=mi('kit_CanOlive'))
for xo in (-0.085, 0.0, 0.085):                           # three handles
    sweep(bm, [Vector((xo, -0.03, H - 0.035)), Vector((xo, -0.03, H)), Vector((xo, 0.03, H)), Vector((xo, 0.03, H - 0.035))],
          0.008, 0.008, 6, mat=mi('kit_CanOlive'))
sweep(bm, [Vector((-0.11, 0.0, H - 0.005)), Vector((0.11, 0.0, H - 0.005))], 0.009, 0.009, 8, mat=mi('kit_CanOlive'))
revolve(bm, [(0.0, 0.028), (0.025, 0.028), (0.03, 0.022), (0.03, 0.0)], 'Z', (0.13, 0.0, H - 0.04), segs=16,
        mat=mi('kit_Steel'))
box(bm, (0.13, 0.0, H - 0.005), (0.06, 0.016, 0.012), mat=mi('kit_Steel'), bevel=0.003, bevel_segs=1)
jc = carry_obj('SM_Kit_JerryCan', bm, 4.2, '20 l, empty 4.2 kg, full (Jet A-1, 0.8 kg/l) 20.2 kg')
INFO['carry']['SM_Kit_JerryCan']['pourPoint'] = (0.13, 0.0, H - 0.01)
INFO['carry']['SM_Kit_JerryCan']['capacityL'] = 20

# funnel with filter screen
bm = bmesh.new()
revolve(bm, [(0.0, 0.016), (0.10, 0.016), (0.12, 0.03), (0.28, 0.12), (0.30, 0.125), (0.30, 0.118), (0.285, 0.112),
             (0.13, 0.025)], 'Z', (0, 0, 0), segs=24, mat=mi('kit_PlasticBlack'))
revolve(bm, [(0.25, 0.0), (0.25, 0.10)], 'Z', (0, 0, 0), segs=24, mat=mi('kit_Steel'))
tube(bm, [Vector((0.12, 0.0, 0.29)), Vector((0.17, 0.0, 0.27)), Vector((0.17, 0.0, 0.20)), Vector((0.10, 0.0, 0.16))],
     0.006, 6, mat=mi('kit_PlasticBlack'))
carry_obj('SM_Kit_Funnel', bm, 0.4, 'fuel funnel with water filter screen')

# stowed heater: same body, duct coiled on top
bm = bmesh.new()
heater_body(bm, Vector((0, 0, 0)), 0.0)
coil = []
for i in range(120):
    t = i / 119 * 2.6 * 2 * math.pi
    coil.append(Vector((0.13 * math.cos(t), 0.05 + 0.20 * math.sin(t) * 0.6, 0.70 + 0.03 * t / (2 * math.pi))))
duct(bm, coil, 0.075, mi('kit_Duct'), ribs=False)
carry_obj('SM_Kit_HeaterStowed', bm, 26.0, 'forced-air heater, duct coiled on top')

# rigid items: carry copies of the installed meshes (same shape), pivot at the bottom centre
for name, (bm_, mass, note) in STOWED.items():          # streamer items: own carry meshes (streamer wound up)
    carry_obj(name, bm_, mass, note)
for src, name, mass in (('Kit_Chocks_L', 'SM_Kit_Chocks', 5.0), ('Kit_Chocks_Tail', 'SM_Kit_ChocksTail', 2.0)):
    s = O[src]
    me = s.data.copy()
    ob = bpy.data.objects.new(name, me)
    KC.objects.link(ob)
    if src.startswith('Kit_Chocks'):                     # chocks: undo the park tilt so they sit flat
        ob.data.transform(s.matrix_world)
        ob.data.transform(R)
    else:
        ob.data.transform(Matrix.Translation(Vector((0, 0, 0))))
    vs = [v.co for v in ob.data.vertices]
    zmin = min(v.z for v in vs)
    cx = (min(v.x for v in vs) + max(v.x for v in vs)) / 2
    cy = (min(v.y for v in vs) + max(v.y for v in vs)) / 2
    ob.data.transform(Matrix.Translation((-cx, -cy, -zmin)))
    INFO['carry'][name] = dict(mass=mass, note='same mesh as ' + src,
                               size=[round(max(v.co[i] for v in ob.data.vertices) - min(v.co[i] for v in ob.data.vertices), 3)
                                     for i in range(3)])
    CARRY.append(ob)

# lay the carry items out in a row beside the plane (preview only; the export moves each to the origin)
for k, ob in enumerate(CARRY):
    ob.location = to_build((3.0 + 0.9 * (k % 6), -6.5 - 1.0 * (k // 6), GZ))
    ob.rotation_euler = (TH, 0, 0)                       # build frame: tilted so the park rotation levels it

tris = 0
for ob in KC.objects:
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    tris += n
    print(f'  {ob.name:28s} {n}')
    ob.evaluated_get(dg).to_mesh_clear()
print('KIT TRIS', tris)
INFO['park'] = dict(pitchDeg=LY.PARK_PITCH_DEG, pivot=tuple(PIV), groundZ=GZ)
json.dump(INFO, open(os.path.join(HERE, 'out', 'kit_v1.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'kit_geo_v1.blend'))
print('saved kit_geo_v1.blend')
