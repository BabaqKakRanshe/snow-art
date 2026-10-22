"""v8 exterior edits on top of v7 (out/plane_v7.blend -> out/plane_v8.blend). Only airframe-atlas meshes change (v8
re-UVs and re-paints the whole airframe); cockpit and Details meshes keep their v7 UVs and textures.
 - src_Struts: streamlined lift struts (symmetric teardrop section, chord 0.14 m, t/c 0.30, leading edge forward) on
   the v7 strut line; the lower pin moves 6.5 cm out along that line so it sits outside the skin: fork fitting, bolt
   and a lug bracket on the fuselage; at the wing the strut flares into a fairing cuff (no exposed upper fitting).
 - src_WingDetails: rebuilt as in v2 (vortex generators, stall strips, flap-track fairings and tie-down rings are
   identical) with a streamlined jury strut (clamp collar on the strut, fitting plate under the wing) and a grab
   handle on two stand-offs ahead of the strut leading edge.
 - src_Dorsal: smooth dorsal fin: concave top line from the cabin roof (y 1.75) into the fin leading edge (z 2.98),
   rounded top edge, circular fillet into the tail cone, aft end buried in the fin.
 - src_Antennas: the top comm blade and the whip move from the tail cone (now the dorsal fin) to the flat cabin roof
   (v7 vertices translated, so their Details UVs and textures stay valid).
Every rebuilt mesh carries a face attribute 'v8zone' (painting zones for the v8 livery) - see ZONES.
Writes out/plane_v8.blend and out/ext_v8.json."""
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import *
import layout as LY

bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v7.blend'))
O, MAT = bpy.data.objects, bpy.data.materials
ROOT = O['UtilityPlane']
INFO = {}
ZONES = {'strut': 0, 'strut_fitting': 1, 'strut_cuff': 2, 'jury': 3, 'jury_fitting': 4, 'handle': 5, 'tiedown': 6,
         'vg': 7, 'stall_strip': 8, 'canoe': 9, 'dorsal': 10}

# ------------------------------------------------------------------ wing helpers (as build_v2)
W_LE, W_CH = -2.55, 2.10
W_Z0, DIH = 2.648, math.radians(2.0)
W_M, W_P, W_T = 0.02, 0.4, 0.13
CUFF_X = 3.9


def wz(x):
    return W_Z0 + max(0.0, abs(x) - 0.76) * math.tan(DIH)


def cuffed(xc, yc, k=1.0):
    if xc >= 0.22:
        return xc, yc
    f = (1 - xc / 0.22) ** 2
    return xc - 0.028 * f * k, yc - 0.020 * f * k


def wing_surface_z(x, xc, upper=True):
    u, l = naca(W_M, W_P, W_T, xc)
    return wz(x) + (u[1] if upper else l[1]) * W_CH


def bvh_of(names):
    verts, polys = [], []
    for n in names:
        ob = O[n]
        mw = ob.matrix_world
        b = len(verts)
        verts += [mw @ v.co for v in ob.data.vertices]
        polys += [[b + i for i in p.vertices] for p in ob.data.polygons]
    return BVHTree.FromPolygons(verts, polys, all_triangles=False)


WING = bvh_of(['src_Wing'])
FUSE = bvh_of(['src_Fuselage'])
FIN = bvh_of(['src_Fin'])


def wing_lower(x, y):
    h = WING.ray_cast(Vector((x, y, 1.6)), Vector((0, 0, 1)), 3.0)
    assert h[0] is not None, ('no wing above', x, y)
    return h[0].z


for n in ('src_Struts', 'src_WingDetails', 'src_Dorsal', 'src_Antennas'):
    assert O[n].matrix_world == Matrix.Identity(4), (n, 'expected identity transform')


class Tagger:
    """bmesh + float face layer 'v8zone'; tag(zone) marks the faces created since the last call"""
    def __init__(self):
        self.bm = bmesh.new()
        self.zl = self.bm.faces.layers.float.new('v8zone')
        self.seen = set()

    def tag(self, zone):
        z = float(ZONES[zone])
        for f in self.bm.faces:
            if f not in self.seen:
                f[self.zl] = z
                self.seen.add(f)


def replace_mesh(name, bm, angle=40.0):
    ob = O[name]
    old = ob.data
    me = bpy.data.meshes.new(name + '_v8')
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for m in old.materials:
        me.materials.append(m)
    ob.data = me
    bpy.data.meshes.remove(old)
    me.name = name
    shade(ob, angle)
    return ob


def naca_t(xc, t):
    xc = max(xc, 0.0)
    return 5 * t * (0.2969 * math.sqrt(xc) - 0.1260 * xc - 0.3516 * xc ** 2 + 0.2843 * xc ** 3 - 0.1036 * xc ** 4)


def section2d(n_half, t, x0):
    """closed symmetric teardrop ring (chord units, axis at x0): TE -> upper -> LE -> lower, 2 * n_half points"""
    xs = [0.5 * (1 - math.cos(math.pi * i / n_half)) for i in range(n_half + 1)]
    up = [(x - x0, naca_t(x, t)) for x in xs]
    lo = [(x - x0, -naca_t(x, t)) for x in xs]
    return list(reversed(up)) + lo[1:-1]


def frame(d):
    """chord direction = flight direction (+Y = aft) made perpendicular to the strut axis; thickness = d x chord"""
    Y = Vector((0, 1, 0))
    ec = (Y - d * Y.dot(d)).normalized()
    et = d.cross(ec).normalized()
    return ec, et


# ================================================================== 1. STRUTS
S_C, S_TC, S_X0 = 0.14, 0.30, 0.35          # chord (m), thickness ratio, strut tube axis at 35 % chord
SEC = section2d(14, S_TC, S_X0)
STRUT = {}
T = Tagger()
bm = T.bm
for sgn in (1, -1):
    p0_v7 = Vector((0.70 * sgn, -1.55, 1.10))
    xw, yw = 3.4 * sgn, -1.75
    p1 = Vector((xw, yw, wing_surface_z(xw, (yw - W_LE) / W_CH, upper=False) + 0.01))   # v7 wing pin
    d = (p1 - p0_v7).normalized()
    p0 = p0_v7 + d * 0.065                                   # v8 lower pin: 6.5 cm out along the same line
    L = (p1 - p0).length
    ec, et = frame(d)
    sk = FUSE.ray_cast(p0, Vector((-sgn, 0, 0)), 0.5)       # fuselage skin under the pin
    assert sk[0] is not None
    skin = sk[0]

    def ring(dist, sc_c=1.0, sc_t=1.0, chord=S_C, sec=SEC, base=p0, dd=d, ec_=ec, et_=et):
        P = base + dd * dist
        return [P + ec_ * (cx * chord * sc_c) + et_ * (ty * chord * sc_t) for cx, ty in sec]

    # main strut: rounded lower end cap -> constant section -> flared cuff sunk into the wing
    rings = []
    d_tip, d_full = 0.085, 0.150
    for phi in (0.30, 0.55, 0.80, 1.05, 1.30, math.pi / 2):
        rings.append(ring(d_full - (d_full - d_tip) * math.cos(phi), math.sin(phi), math.sin(phi)))
    for dist in (0.6, 1.2, 1.8, L - 0.30):
        rings.append(ring(dist))
    loft(bm, rings, True, True, False)
    T.tag('strut')
    cuff = []
    for k in range(1, 9):
        f = k / 8
        dist = L - 0.30 + 0.40 * f
        s = 3 * min(f / 0.8, 1) ** 2 - 2 * min(f / 0.8, 1) ** 3
        cuff.append(ring(dist, 1.0 + 0.45 * s, 1.0 + 0.70 * s))
    vr = loft(bm, [rings[-1]] + cuff, True, False, True)
    T.tag('strut_cuff')
    # lower fitting: fuselage lug (plate normal to Y) + doubler, fork plates on the strut end, bolt along Y
    up_xz = Vector((0, 1, 0)).cross(d).normalized()          # in the XZ plane, perpendicular to the strut
    if up_xz.z < 0:
        up_xz = -up_xz
    out = Vector((sgn, 0, 0))
    lug_pts = []
    for a in range(0, 181, 15):                              # rounded tab around the pin, base on the skin
        aa = math.radians(a - 90)
        lug_pts.append(p0 + (out * math.cos(aa) + Vector((0, 0, 1)) * math.sin(aa)) * 0.024)
    lug_pts = [Vector((skin.x - sgn * 0.004, p0.y, p0.z - 0.05))] + lug_pts + \
              [Vector((skin.x - sgn * 0.004, p0.y, p0.z + 0.05))]
    loft(bm, [[p + Vector((0, -0.005, 0)) for p in lug_pts], [p + Vector((0, 0.005, 0)) for p in lug_pts]],
         True, True, True)
    box(bm, (skin.x + sgn * 0.002, p0.y, p0.z), (0.008, 0.11, 0.13), bevel=0.003, bevel_segs=1)    # doubler
    T.tag('strut_fitting')
    for sy in (-1, 1):                                       # fork plates straddling the lug
        yy = Vector((0, sy * 0.0095, 0))
        corners = []
        for a in range(90, 271, 20):                         # rounded end round the pin
            aa = math.radians(a)
            corners.append(p0 + yy + (d * math.cos(aa) + up_xz * math.sin(aa)) * 0.020)
        corners += [p0 + yy + d * 0.11 - up_xz * 0.018, p0 + yy + d * 0.11 + up_xz * 0.018]
        loft(bm, [[c - Vector((0, 0.003, 0)) for c in corners], [c + Vector((0, 0.003, 0)) for c in corners]],
             True, True, True)
    cylinder(bm, p0 + Vector((0, -0.024, 0)), p0 + Vector((0, 0.024, 0)), 0.0065, 0.0065, 10)       # bolt
    for sy in (-1, 1):                                       # hex head / nut
        cylinder(bm, p0 + Vector((0, sy * 0.0125, 0)), p0 + Vector((0, sy * 0.019, 0)), 0.0115, 0.0115, 6)
    T.tag('strut_fitting')
    STRUT[sgn] = dict(p0=p0, p1=p1, d=d, ec=ec, et=et, L=L, p0_v7=p0_v7, skin=skin)
fix_normals(bm)
struts = replace_mesh('src_Struts', bm)
INFO['struts'] = {('L' if s > 0 else 'R'): dict(pin_fuselage=list(v['p0']), pin_wing=list(v['p1']),
                                                  length=round(v['L'], 4)) for s, v in STRUT.items()}
INFO['strut_section'] = dict(chord=S_C, thickness=round(S_C * S_TC, 4), axis_at_chord=S_X0)

# ================================================================== 2. WING DETAILS (v2 parts + v8 jury strut / handle)
T = Tagger()
bm = T.bm
k = 0
J_C, J_TC, J_X0 = 0.055, 0.32, 0.40
JSEC = section2d(8, J_TC, J_X0)
for sgn in (1, -1):
    x = 0.95
    while x < 6.75:                                          # vortex generators (unchanged)
        xx = sgn * x
        xc = 0.11
        xc2 = cuffed(xc, 0)[0] if abs(xx) >= CUFF_X else xc
        y = W_LE + xc2 * W_CH
        z = wing_surface_z(xx, xc, True) - 0.002
        ang = math.radians(16 if k % 2 == 0 else -16)
        dv = Vector((math.sin(ang), math.cos(ang), 0))
        n = Vector((math.cos(ang), -math.sin(ang), 0)) * 0.001
        base = Vector((xx, y, z))
        pts = [base, base + dv * 0.035, base + dv * 0.035 + Vector((0, 0, 0.018))]
        vs = [bm.verts.new(p + n) for p in pts] + [bm.verts.new(p - n) for p in pts]
        for f in ((0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)):
            bm.faces.new([vs[i] for i in f])
        k += 1
        x += 0.105
    T.tag('vg')
    sweep(bm, [Vector((sgn * x0, W_LE - 0.004, wz(x0) - 0.008)) for x0 in (1.05, 1.25, 1.45)], 0.007, 0.007, 3)
    T.tag('stall_strip')
    for xt in (1.25, 2.45, 3.65, 4.85, 6.05):                 # flap-track / hinge fairings (unchanged)
        xs_ = sgn * xt
        zl = wing_surface_z(xs_, 0.55, False)
        prof = []
        for i in range(9):
            u = i / 8
            prof.append((W_LE + W_CH * (0.62 + 0.42 * u), 0.045 * math.sin(math.pi * u) ** 0.6))
        revolve(bm, prof, 'Y', (xs_, 0, zl - 0.01), segs=10)
    T.tag('canoe')
    tr_c = Vector((sgn * 3.2, -1.62, wing_surface_z(sgn * 3.2, (-1.62 - W_LE) / W_CH, False) - 0.03))
    sweep(bm, [tr_c + Vector((0, 0.025 * math.cos(a), 0.025 * math.sin(a))) for a in
               [2 * math.pi * i / 12 for i in range(13)]], 0.005, 0.005, 6, cap0=False, cap1=False)
    T.tag('tiedown')
    # jury strut: v7 line (55 % of the v7 strut line up to the wing), streamlined, clamp collar + wing plate
    S = STRUT[sgn]
    j0 = S['p0_v7'].lerp(S['p1'], 0.55)
    j1 = Vector((j0.x, j0.y + 0.05, wing_lower(j0.x, j0.y + 0.05) + 0.012))
    dj = (j1 - j0).normalized()
    ecj, etj = frame(dj)
    Lj = (j1 - j0).length
    rj = lambda dist, s=1.0: [j0 + dj * dist + ecj * (cx * J_C * s) + etj * (ty * J_C * s) for cx, ty in JSEC]
    loft(bm, [rj(0.0), rj(0.5 * Lj), rj(Lj)], True, True, True)
    T.tag('jury')
    # clamp collar round the main strut (a slightly larger strut section, 4 cm long) + lug
    d, ec, et = S['d'], S['ec'], S['et']
    tj = (j0 - S['p0']).dot(d)
    collar = [[S['p0'] + d * (tj + dd) + ec * (cx * S_C * 1.10) + et * (ty * S_C * 1.32) for cx, ty in SEC]
              for dd in (-0.022, -0.016, 0.016, 0.022)]
    collar[0] = [S['p0'] + d * (tj - 0.022) + ec * (cx * S_C * 1.02) + et * (ty * S_C * 1.08) for cx, ty in SEC]
    collar[3] = [S['p0'] + d * (tj + 0.022) + ec * (cx * S_C * 1.02) + et * (ty * S_C * 1.08) for cx, ty in SEC]
    loft(bm, collar, True, True, True)
    box(bm, tuple(j0 + dj * 0.045), (0.020, 0.030, 0.020), bevel=0.004, bevel_segs=1)
    plate_c = Vector((j1.x, j1.y, wing_lower(j1.x, j1.y) - 0.002))
    box(bm, tuple(plate_c), (0.06, 0.09, 0.010), bevel=0.003, bevel_segs=1)
    T.tag('jury_fitting')
    # grab handle: two stand-offs from the strut leading edge, grip bar parallel to the strut (v7: 18..30 % of the line)
    le_off = S_C * S_X0
    g = []
    for t_ in (0.18, 0.30):
        pv7 = S['p0_v7'].lerp(S['p1'], t_)
        g.append(S['p0'] + d * (pv7 - S['p0']).dot(d))
    reach = le_off + 0.060
    path = [g[0] - ec * 0.02, g[0] - ec * (reach - 0.018), g[0] - ec * reach + d * 0.018,
            g[1] - ec * reach - d * 0.018, g[1] - ec * (reach - 0.018), g[1] - ec * 0.02]
    pts_ = []
    for a, b in zip(path[:-1], path[1:]):
        for i in range(4):
            pts_.append(a.lerp(b, i / 4))
    pts_.append(path[-1])
    sweep(bm, pts_, 0.0095, 0.0095, 10)
    T.tag('handle')
    INFO.setdefault('jury', {})['L' if sgn > 0 else 'R'] = dict(base=list(j0), top=list(j1))
    INFO.setdefault('grab_handle', {})['L' if sgn > 0 else 'R'] = dict(a=list(g[0] - ec * reach),
                                                                       b=list(g[1] - ec * reach))
fix_normals(bm)
wdet = replace_mesh('src_WingDetails', bm, 45)

# ================================================================== 3a. FIN: same planform and NACA 0011 section as v2, finer
# tessellation (24 points per side, a ring every ~5 cm) so the dorsal fin can blend into its leading edge cleanly
HINGE_Y, FIN_T = 4.60, 0.11


def fin_ring(z, le, te, n, tscale=1.0):
    ch = te - le
    h = (HINGE_Y - 0.012 - le) / ch
    return [Vector((yc * ch, le + xc * ch, z)) for xc, yc in airfoil_ring(0, h, n, 0, 0, FIN_T * tscale, True)]


def fin_le_te(z):
    R = [(2.36, 3.22, 5.08), (2.60, 3.47, 5.07), (3.82, 4.12, 4.98)]
    a, b = (R[0], R[1]) if z <= R[1][0] else (R[1], R[2])
    t = (z - a[0]) / (b[0] - a[0])
    return a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t


fz_list = [2.36, 2.42, 2.48, 2.54, 2.60] + [2.60 + (3.82 - 2.60) * i / 24 for i in range(1, 25)]
rings = [fin_ring(z, *fin_le_te(z), 24) for z in fz_list]
rings.append(fin_ring(3.86, 4.19, 4.98, 24, 0.8))
rings.append(fin_ring(3.90, 4.26, 4.98, 24, 0.6))
T = Tagger()
loft(T.bm, rings, True, True, True)
T.tag('dorsal')
for f in T.bm.faces:
    f[T.zl] = 0.0
fix_normals(T.bm)
fin_ob = replace_mesh('src_Fin', T.bm, 35)
FIN = bvh_of(['src_Fin'])

# ================================================================== 3b. DORSAL FIN
FIN_LE = [(2.36, 3.22), (2.60, 3.47), (3.82, 4.12)]


def fin_le_y(z):
    if z <= FIN_LE[1][0]:
        (z0, y0), (z1, y1) = FIN_LE[0], FIN_LE[1]
    else:
        (z0, y0), (z1, y1) = FIN_LE[1], FIN_LE[2]
    return y0 + (z - z0) * (y1 - y0) / (z1 - z0)


def zt(y):                                       # tail-cone top line (linear loft between the tail stations)
    a, b = LY.ST_TAIL_A, LY.ST_TAIL_B
    return a[2] + (b[2] - a[2]) * (y - a[0]) / (b[0] - a[0])


Z_M = 2.98
Y_M = fin_le_y(Z_M)
le_dir = Vector((0, FIN_LE[2][1] - FIN_LE[1][1], FIN_LE[2][0] - FIN_LE[1][0])).normalized()
Y0 = 1.75
P0 = Vector((0, Y0, zt(Y0)))
P1 = Vector((0, 2.60, zt(Y0)))
P3 = Vector((0, Y_M, Z_M))
P2 = P3 - le_dir * 0.42
bez = []
for i in range(400):
    t = i / 399
    p = (1 - t) ** 3 * P0 + 3 * (1 - t) ** 2 * t * P1 + 3 * (1 - t) * t ** 2 * P2 + t ** 3 * P3
    bez.append((p.y, p.z))
assert all(b[0] < c[0] for b, c in zip(bez[:-1], bez[1:])), 'dorsal top line not monotonic in y'


def z_top(y):
    if y >= Y_M:
        return Z_M + (y - Y_M) * 1.2                 # inside the fin: behind its leading edge
    for (ya, za), (yb, zb) in zip(bez[:-1], bez[1:]):
        if ya <= y <= yb:
            return za + (zb - za) * (y - ya) / (yb - ya)
    return bez[0][1]


def smooth01(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


EMBED = 0.035
FQ = (0.0, 0.10, 0.25, 0.45, 0.70, 1.0)                     # fillet zone samples (fractions of the fillet height)
CQ = (0.06, 0.14, 0.24, 0.35, 0.47, 0.59, 0.70, 0.80, 0.88, 0.95, 1.0)   # core samples above the fillet
BL_A, BL_D = 0.020, 0.004                       # fin blend: width d + h(f - d), C1, 4 mm inside the fin where f wins
BL_B = BL_A + 2 * BL_D
FIN_RINGS = [(2.36, 3.22, 5.08), (2.60, 3.47, 5.07), (3.82, 4.12, 4.98)]   # build_v2 fin: (z, le, te), NACA 0011


def fin_half(y, z):
    """analytic half-thickness of the fin at (y, z) (smooth; the mesh lies 0-1.5 mm inside it behind the LE)"""
    if z <= FIN_RINGS[1][0]:
        a, b = FIN_RINGS[0], FIN_RINGS[1]
    else:
        a, b = FIN_RINGS[1], FIN_RINGS[2]
    t = (z - a[0]) / (b[0] - a[0])
    le, te = a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t
    xc = (y - le) / (te - le)
    if xc <= 0.0:
        return 0.0
    return naca_t(min(xc, 1.0), 0.11) * (te - le)


def blend(d, f):
    x = f - d
    if x <= -BL_A:
        return d
    if x >= BL_B:
        return d + x - BL_D
    return d + (x + BL_A) ** 2 / (2 * (BL_A + BL_B))


def dorsal_ring(y):
    base_top = zt(y)
    h = max(z_top(y) - base_top, 0.0005)
    rt = min(0.010 + 0.006 * smooth01((y - Y0) / 1.6), 0.45 * h)
    hc = h - rt
    w_core = 0.012 + 0.022 * smooth01((y - Y0) / 1.0)
    R_f = min(0.035, 0.7 * hc) * smooth01((y - Y0) / 0.35 + 0.15) * (1 - smooth01((y - 3.60) / 0.40))

    def width(zp):
        zc = max(zp, 0.0)
        core = rt + (w_core - rt) * max(0.0, 1 - zc / hc) ** 1.3 if hc > 1e-6 else rt
        if zp <= 0:
            fil = R_f
        elif zp < R_f:
            fil = R_f - math.sqrt(max(0.0, R_f * R_f - (R_f - zp) ** 2))
        else:
            fil = 0.0
        return core + fil

    fz = max(min(0.035, 0.7 * hc), 1e-5)               # fillet zone height (constant sample count per ring)
    zs = [-EMBED] + [fz * q for q in FQ] + [fz + (hc - fz) * q for q in CQ]
    pts = [(width(zp), base_top + zp) for zp in zs]
    for a in (30, 60):
        aa = math.radians(a)
        pts.append((rt * math.cos(aa), base_top + hc + rt * math.sin(aa)))
    left = [Vector((blend(w, fin_half(y, z)), y, z)) for w, z in pts]
    top = [Vector((0.0, y, base_top + h))]
    right = [Vector((-p.x, p.y, p.z)) for p in reversed(left)]
    return left + top + right


ys = [Y0 + (3.30 - Y0) * (i / 26) for i in range(26)] + [3.30 + (3.95 - 3.30) * (i / 32) for i in range(33)]
T = Tagger()
loft(T.bm, [dorsal_ring(y) for y in ys], True, True, True)
T.tag('dorsal')
fix_normals(T.bm)
dors = replace_mesh('src_Dorsal', T.bm, 50)
INFO['dorsal'] = dict(start_y=Y0, merge=[Y_M, Z_M], end_y=ys[-1], embed=EMBED)

# ================================================================== 4. ANTENNAS: top comm blade + whip -> cabin roof
ant = O['src_Antennas']
bm = bmesh.new()
bm.from_mesh(ant.data)
bm.verts.ensure_lookup_table()
seen, comps = set(), []
for v in bm.verts:
    if v.index in seen:
        continue
    stack, comp = [v], []
    seen.add(v.index)
    while stack:
        a = stack.pop()
        comp.append(a)
        for e in a.link_edges:
            b = e.other_vert(a)
            if b.index not in seen:
                seen.add(b.index)
                stack.append(b)
    comps.append(comp)
moved = {'blade': 0, 'whip': 0}
for comp in comps:
    c = sum((v.co for v in comp), Vector()) / len(comp)
    if abs(c.x) < 0.05 and 2.2 < c.y < 2.5 and c.z > 2.55:
        dv = Vector((0, 0.85 - 2.35, 2.662 - 2.585))           # roof is flat (z 2.66) between y 0.6 and 1.1
        key = 'blade'
    elif abs(c.x) < 0.05 and 3.0 < c.y < 3.3 and 2.48 < c.z < 3.2:
        roof = 2.66 + (2.645 - 2.66) * (1.30 - 1.10) / (1.50 - 1.10)
        dv = Vector((0, 1.30 - 3.05, (roof - 0.01) - 2.51))
        key = 'whip'
    else:
        continue
    for v in comp:
        v.co += dv
    moved[key] += 1
assert moved['blade'] >= 3 and moved['whip'] == 3, moved
bm.to_mesh(ant.data)
bm.free()
INFO['antennas_moved'] = dict(comm_blade_to_y=0.85, whip_to_y=1.30, components=moved)

# ================================================================== checks
def verts_w(ob):
    return [ob.matrix_world @ v.co for v in ob.data.vertices]


def zone_verts(ob, zone):
    me = ob.data
    za = me.attributes['v8zone'].data
    idx = {vi for p in me.polygons if round(za[p.index].value) == ZONES[zone] for vi in p.vertices}
    return [ob.matrix_world @ me.vertices[i].co for i in idx]


rep = {}
SBVH = bvh_of(['src_Struts'])
for sgn in (1, -1):
    S = STRUT[sgn]
    main = [p for p in zone_verts(struts, 'strut') if p.x * sgn > 0]
    far = [p for p in main if (p - S['p0']).dot(S['d']) > 0.2]
    dmin_f = min(FUSE.find_nearest(p)[3] for p in far)
    above = [p for p in main if (p - S['p0']).dot(S['d']) < S['L'] - 0.31 and p.z > wing_lower(p.x, p.y) - 0.002]
    ring_pts = [p for p in verts_w(wdet) if abs(p.x - sgn * 3.2) < 0.01 and abs(p.y + 1.62) < 0.04]
    d_ring = min(SBVH.find_nearest(p)[3] for p in ring_pts)
    kit = Vector((3.36 * sgn, -1.75, 2.585))
    d_kit = SBVH.find_nearest(kit)[3]
    rep['L' if sgn > 0 else 'R'] = dict(min_dist_main_to_fuselage=round(dmin_f, 4), main_verts_in_wing=len(above),
                                       tiedown_ring_to_strut=round(d_ring, 4), kit_attach_to_strut=round(d_kit, 4))
    assert dmin_f > 0.02 and not above and d_ring > 0.004, rep
# dorsal: visible part ahead of the fin; aft rings buried in the fin
dv = verts_w(dors)
far = [p for p in dv if p.y > Y_M + 0.06]
out_fin = 0
for p in far:                                     # is the point between the fin's two side faces?
    hl = FIN.ray_cast(Vector((0.5, p.y, p.z)), Vector((-1, 0, 0)), 1.0)
    hr = FIN.ray_cast(Vector((-0.5, p.y, p.z)), Vector((1, 0, 0)), 1.0)
    if hl[0] is None or hr[0] is None or not (hr[0].x - 1e-4 <= p.x <= hl[0].x + 1e-4):
        if p.z > zt(p.y) + 0.002:
            out_fin += 1
rep['dorsal'] = dict(verts=len(dv), aft_verts=len(far), aft_verts_outside_fin_above_skin=out_fin,
                     merge=[round(Y_M, 4), Z_M])
ant_pts = verts_w(ant)
rep['antenna_to_dorsal'] = round(min(bvh_of(['src_Dorsal']).find_nearest(p)[3] for p in ant_pts
                                     if p.y > 0.5 and abs(p.x) < 0.1 and p.z > 2.5), 4)
print('CHECKS', json.dumps(rep, indent=1))
INFO['checks'] = rep

tris = 0
dg = bpy.context.evaluated_depsgraph_get()
for ob in bpy.data.objects:
    if ob.type == 'MESH':
        me = ob.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        n = len(me.loop_triangles)
        tris += n
        if ob.name in ('src_Struts', 'src_WingDetails', 'src_Dorsal', 'src_Antennas'):
            print(f'  {ob.name:18s} {n}')
        ob.evaluated_get(dg).to_mesh_clear()
print('TOTAL TRIS', tris)


def _jsonable(o):
    if isinstance(o, Vector):
        return [round(c, 5) for c in o]
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, float):
        return round(o, 5)
    return o


json.dump(_jsonable(INFO), open(os.path.join(HERE, 'out', 'ext_v8.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v8.blend'))
print('saved plane_v8.blend')
