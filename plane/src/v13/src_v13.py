"""Utility Plane v13 source: out/plane_v9_final_v11.blend +
  (1) exterior light fixtures that are part of the airframe: fin-cap fairing + flange for the top beacon, belly doubler
      + flange for the bottom beacon (moved up to the belly: in v5-v12 it hung 9 cm under the skin), wingtip nav /
      strobe housings (lens = nose of the housing, strobe window aft), tail-cone boss for the tail light, a cover that
      follows the wing leading edge for the landing light;
  (2) new lens meshes (src_Lights) with UVs into T_Lens (ribbed lens / dome / flat reflector), same material slots;
  (3) sliding cargo doors: rails swept along the roller paths of the door motion (DOOR below = the same formula as
      UtilityPlaneRig.SlidingDoorPose), roller arms added to CargoDoor_L / _R.
Build frame: x left, y aft, z up, metres.  Output: out/plane_v9_final_v13.blend, out/light_pos_v13.json,
out/doors_v13.json.   python3 src_v13.py"""
import bpy, bmesh, math, json, os
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

HERE = '/home/claude/plane'
SRC = HERE + '/out/plane_v9_final_v11.blend'
OUT = HERE + '/out/plane_v9_final_v13.blend'
bpy.ops.wm.open_mainfile(filepath=SRC)
O = bpy.data.objects
MAT = bpy.data.materials
COLL = bpy.data.collections['Aircraft']
ROOT = O['UtilityPlane']
DG = bpy.context.evaluated_depsgraph_get()
PI = math.pi

# ---------------------------------------------------------------- atlas patches (PSX v12 textures, 512 px, top-left)
def rect(x0, y0, x1, y1, size=512):
    return (x0 / size, 1 - y1 / size, x1 / size, 1 - y0 / size)          # u0, v0, u1, v1 (UV origin bottom-left)
DET_DARK = rect(205, 188, 219, 212)        # T_Details: dark grey metal (flanges, bezels, bosses)
DET_BLACK = rect(346, 54, 368, 66)         # T_Details: near black (gaskets)
DET_RAIL = rect(200, 384, 228, 406)        # T_Details: weathered dark metal (door rails)
FLOOR_METAL = rect(216, 204, 232, 232)     # T_Floor: light grey metal (door roller arms)
FLOOR_DARK = rect(319, 385, 325, 391)      # T_Floor: dark grey (rubber pull grip on the door's front edge)
# T_Lens (128 px, written by lens_tex_v13.py): UV regions
L_CYL = (0.0, 0.5, 0.5, 1.0)               # ribbed side of a round lens (u around, v along the axis)
L_CAP = (0.5, 0.5, 1.0, 1.0)               # dome cap (polar)
L_NAV = (0.0, 0.0, 0.5, 0.5)               # nav lens = nose of the wingtip housing
L_FLAT = (0.5, 0.0, 1.0, 0.5)              # flat cover with a reflector (landing light)


def in_rect(r, u, v):
    return (r[0] + (r[2] - r[0]) * min(max(u, 0.0), 1.0), r[1] + (r[3] - r[1]) * min(max(v, 0.0), 1.0))


# ---------------------------------------------------------------- surfaces: BVH + UV lookup (world space)
class Surf:
    def __init__(self, names):
        self.bm = bmesh.new()
        for n in names:
            ob = O[n]
            me = ob.evaluated_get(DG).to_mesh()
            t = bmesh.new()
            t.from_mesh(me)
            t.transform(ob.matrix_world)
            m = bpy.data.meshes.new('_tmp')
            t.to_mesh(m)
            t.free()
            self.bm.from_mesh(m)
            bpy.data.meshes.remove(m)
        bmesh.ops.triangulate(self.bm, faces=self.bm.faces[:])
        self.bm.faces.ensure_lookup_table()
        self.uv = self.bm.loops.layers.uv.active
        self.tree = BVHTree.FromBMesh(self.bm)

    def ray(self, o, d, dist=3.0):
        return self.tree.ray_cast(Vector(o), Vector(d).normalized(), dist)

    def uv_at(self, p):
        loc, n, i, d = self.tree.find_nearest(Vector(p))
        f = self.bm.faces[i]
        a, b, c = (l.vert.co for l in f.loops)
        ua, ub, uc = (Vector((l[self.uv].uv.x, l[self.uv].uv.y, 0.0)) for l in f.loops)
        w = barycentric_transform(loc, a, b, c, ua, ub, uc)
        return (w.x, w.y)




# ---------------------------------------------------------------- uniform paint patches matched to the surface colour
import numpy as _np
from PIL import Image as _Image
TEXDIR = '/home/claude/plane/export/unity_v12r2/Assets/UtilityPlane/Textures/'
_ATL = {}


def _atlas(name):
    if name not in _ATL:
        _ATL[name] = _np.asarray(_Image.open(TEXDIR + name + '_BaseColor.png').convert('RGB')).astype(float)
    return _ATL[name]


def paint_patch(atlas, surf, points, win=8):
    """rect of a low-variance patch of 'atlas' whose colour is closest to the paint of 'surf' at 'points'"""
    a = _atlas(atlas)
    H, W, _ = a.shape
    cols = []
    for p in points:
        u, v = surf.uv_at(Vector(p))
        x, y = int(min(max(u, 0), 0.999) * W), int((1 - min(max(v, 0), 0.999)) * H)
        cols.append(a[max(0, y - 1):y + 2, max(0, x - 1):x + 2].reshape(-1, 3).mean(0))
    target = _np.mean(cols, 0)
    best = None
    lum = a.mean(2)
    for y in range(0, H - win, 2):
        for x in range(0, W - win, 2):
            blk = a[y:y + win, x:x + win]
            sd = lum[y:y + win, x:x + win].std()
            if sd > 14:
                continue
            d = _np.linalg.norm(blk.reshape(-1, 3).mean(0) - target) + 0.6 * sd
            if best is None or d < best[0]:
                best = (d, x, y)
    d, x, y = best
    print(f'  paint patch {atlas}: target {target.round(0)} -> px ({x},{y}) score {d:.1f}')
    return rect(x + 1, y + 1, x + win - 1, y + win - 1, W)

FUSE = Surf(['src_Fuselage'])
FIN = Surf(['src_Fin'])
WING = Surf(['src_Wing', 'src_WingTE_TipL', 'src_WingTE_TipR', 'src_WingTE_Center'])

# ---------------------------------------------------------------- mesh builder
class Builder:
    """faces with a material slot and per-loop UVs; uv='transfer:<Surf>' or a function (vertex, face) -> (u, v)"""

    def __init__(self, name, mats):
        self.name, self.mats = name, mats
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new('UVMap')
        self.tag = self.bm.faces.layers.int.new('ref')
        self.refs = []

    def v(self, p):
        return self.bm.verts.new(Vector(p))

    ref = None                                         # current "inside" point (or ('dir', vector))

    def face(self, verts, mat, uvs):
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            return None
        f.material_index = self.mats.index(mat)
        for l, uv in zip(f.loops, uvs):
            l[self.uv].uv = uv
        f[self.tag] = len(self.refs)
        self.refs.append(self.ref)
        return f

    def orient(self):
        """every face points away from its part's inside point (or along its outward direction)"""
        self.bm.normal_update()
        flip = []
        for f in self.bm.faces:
            r = self.refs[f[self.tag]]
            if r is None:
                continue
            if isinstance(r, tuple) and r[0] == 'axis':          # away from a line (point r[1], direction r[2])
                d = f.calc_center_median() - r[1]
                want = d - r[2] * d.dot(r[2])
            else:
                want = r[1] if isinstance(r, tuple) else f.calc_center_median() - r
            if f.normal.dot(want) < 0:
                flip.append(f)
        if flip:
            bmesh.ops.reverse_faces(self.bm, faces=flip, flip_multires=False)
        return len(flip)

    def obj(self, parent=ROOT, smooth_deg=40):
        n = self.orient()
        print(self.name, 'faces flipped to the outside:', n, 'of', len(self.bm.faces))
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts[:], dist=1e-6)
        me = bpy.data.meshes.new(self.name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        for m in self.mats:
            me.materials.append(MAT[m])
        for p in me.polygons:
            p.use_smooth = True
        ob = bpy.data.objects.new(self.name, me)
        COLL.objects.link(ob)
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()
        bpy.context.view_layer.update()
        try:                                              # Blender 4.1+: smooth by angle
            me.set_sharp_from_angle(angle=math.radians(smooth_deg))
        except Exception:
            pass
        return ob


def quad_strip(B, rows, mat, uvfun, close=False):
    """rows: list of lists of points (same length); faces between consecutive rows; uvfun(point, i, j) -> uv"""
    vs = [[B.v(p) for p in row] for row in rows]
    n = len(rows[0])
    for i in range(len(rows) - 1):
        for j in range(n - (0 if close else 1)):
            j2 = (j + 1) % n
            q = [vs[i][j], vs[i][j2], vs[i + 1][j2], vs[i + 1][j]]
            pts = [rows[i][j], rows[i][j2], rows[i + 1][j2], rows[i + 1][j]]
            idx = [(i, j), (i, j2), (i + 1, j2), (i + 1, j)]
            B.face(q, mat, [uvfun(p, a, b) for p, (a, b) in zip(pts, idx)])
    return vs


def fan(B, ring_pts, centre, mat, uvfun, flip=False):
    c = B.v(centre)
    n = len(ring_pts)
    rv = [B.v(p) for p in ring_pts]
    for j in range(n):
        j2 = (j + 1) % n
        tri = [c, rv[j], rv[j2]] if not flip else [c, rv[j2], rv[j]]
        pts = [centre, ring_pts[j], ring_pts[j2]] if not flip else [centre, ring_pts[j2], ring_pts[j]]
        B.face(tri, mat, [uvfun(p, k) for k, p in enumerate(pts)])


def frame(axis):
    a = Vector(axis).normalized()
    t = Vector((1, 0, 0)) if abs(a.x) < 0.9 else Vector((0, 1, 0))
    u = a.cross(t).normalized()
    w = a.cross(u).normalized()
    return a, u, w


def circle(c, axis, r, segs, phase=0.0):
    a, u, w = frame(axis)
    c = Vector(c)
    return [c + r * (math.cos(phase + 2 * PI * k / segs) * u + math.sin(phase + 2 * PI * k / segs) * w)
            for k in range(segs)]


def round_lens(Lb, base_c, axis, r, h_cyl, h_dome, mat, segs=14):
    """cylindrical lens with a domed end, base at base_c, pointing along axis (ribbed side -> L_CYL, cap -> L_CAP)"""
    a = Vector(axis).normalized()
    Lb.ref = Vector(base_c) - a * 0.01
    rows, vv = [], []
    for k in range(3):
        rows.append(circle(Vector(base_c) + a * (h_cyl * k / 2), a, r, segs))
        vv.append(k / 2 * 0.6)
    for k, th in enumerate((0.45, 0.9)):                 # dome rings
        rows.append(circle(Vector(base_c) + a * (h_cyl + h_dome * math.sin(th)), a, r * math.cos(th), segs))
        vv.append(0.6 + 0.2 * (k + 1))
    tip = Vector(base_c) + a * (h_cyl + h_dome)

    def uv_side(p, i, j):
        return in_rect(L_CYL, j / segs, vv[i])
    quad_strip(Lb, rows, mat, uv_side, close=True)
    _, u, w = frame(a)

    def uv_cap(p, k):
        d = Vector(p) - tip
        rr = max(r, 1e-6)
        return in_rect(L_CAP, 0.5 + 0.5 * d.dot(u) / rr, 0.5 + 0.5 * d.dot(w) / rr)
    fan(Lb, rows[-1], tip, mat, uv_cap)
    return tip


def flange(Mb, base_ring, top_c, axis, r_out, r_in, mat_rect, segs=14):
    """metal ring: side from base_ring (points, conformed to a surface) up to a flat top, top annulus to r_in"""
    a = Vector(axis).normalized()
    Mb.ref = Vector(top_c) - a * 0.05
    top = circle(top_c, a, r_out, segs)
    inner = circle(top_c, a, r_in, segs)
    quad_strip(Mb, [base_ring, top], 'M_Details', lambda p, i, j: in_rect(mat_rect, j / segs, i), close=True)
    quad_strip(Mb, [top, inner], 'M_Details', lambda p, i, j: in_rect(mat_rect, j / segs, 0.5 + 0.5 * i), close=True)


LIGHTS = json.load(open(HERE + '/out/light_pos.json'))
NEWPOS = dict(LIGHTS)
MOUNT_MATS = ['M_Airframe', 'M_Wing', 'M_Details']
LENS_MATS = ['M_Light_Red', 'M_Light_Green', 'M_Light_White', 'M_Light_Beacon', 'M_Light_Landing']
MB = Builder('src_LightMounts', MOUNT_MATS)
LB = Builder('src_Lights_v13', LENS_MATS)
SEG = 14

# ================================================================ (1a) top beacon on a fin-cap fairing
Z0, YB = 3.900, 4.425
ya, yb = 4.290, 4.560
secs, nphi = 16, 9
rows = []
for i in range(secs + 1):
    s = i / secs
    y = ya + (yb - ya) * s
    w = 0.036 * max(math.sin(PI * s), 0.0) ** 0.55 + 0.003
    h = 0.024 * max(math.sin(PI * s), 0.0) ** 0.7 + 0.001
    hh = FIN.ray((0.3, y, Z0 - 0.006), (-1, 0, 0), 0.6)
    fh = abs(hh[0].x) - 0.001 if hh[0] is not None else 0.02
    row = [Vector((fh, y, Z0 - 0.006))]
    for k in range(nphi):
        ph = PI * k / (nphi - 1)
        row.append(Vector((w * math.cos(ph), y, Z0 + h * math.sin(ph))))
    row.append(Vector((-fh, y, Z0 - 0.006)))
    rows.append(row)
MB.ref = None
MB.ref = Vector((0, YB, Z0 - 0.03))
FIN_P = paint_patch('T_Airframe', FIN, [(0.0, y, Z0 - 0.002) for y in (4.33, 4.40, 4.47, 4.53)] +
                    [(0.027, y, Z0 - 0.03) for y in (4.35, 4.45)])
fin_uv = lambda p, *a: in_rect(FIN_P, (p.y - ya) / (yb - ya), 0.5 + p.x / 0.08)
quad_strip(MB, rows, 'M_Airframe', lambda p, i, j: fin_uv(p))
fan(MB, rows[0], Vector((0, ya - 0.004, Z0 + 0.0005)), 'M_Airframe', lambda p, k: fin_uv(p), flip=True)
fan(MB, rows[-1], Vector((0, yb + 0.004, Z0 + 0.0005)), 'M_Airframe', lambda p, k: fin_uv(p))
top_z = Z0 + 0.025


def fairing_z(x, y):
    s = (y - ya) / (yb - ya)
    w = 0.036 * max(math.sin(PI * s), 0.0) ** 0.55 + 0.003
    h = 0.024 * max(math.sin(PI * s), 0.0) ** 0.7 + 0.001
    return Z0 + h * math.sqrt(max(0.0, 1 - (x / w) ** 2))


base = [Vector((p.x, p.y, fairing_z(p.x, p.y) - 0.003)) for p in circle((0, YB, top_z), (0, 0, 1), 0.032, SEG)]
flange(MB, base, Vector((0, YB, top_z + 0.009)), (0, 0, 1), 0.032, 0.027, DET_DARK)
tip = round_lens(LB, Vector((0, YB, top_z + 0.009)), (0, 0, 1), 0.028, 0.030, 0.015, 'M_Light_Beacon')
NEWPOS['Beacon_Top'] = [0.0, YB, round(top_z + 0.009 + 0.019, 4)]

# ================================================================ (1b) bottom beacon on a belly doubler
YC = 1.650
hit = FUSE.ray((0, YC, 0.3), (0, 0, 1))
C0, NB = hit[0], -hit[1].normalized()               # NB: into the fuselage (up); outward = -NB
OUTN = -NB
PLATE = 0.006


def belly(x, y):
    h = FUSE.ray((x, y, 0.3), (0, 0, 1))
    return h[0]


rim_in, rim_out, plate_c = [], [], C0 + OUTN * PLATE
for k in range(SEG + 2):
    ang = 2 * PI * k / (SEG + 2)
    x, y = 0.066 * math.cos(ang), YC + 0.080 * math.sin(ang)
    s = belly(x, y)
    rim_in.append(s - Vector((0, 0, 0.002)))
    rim_out.append(s + OUTN * PLATE)
BELLY_P = paint_patch('T_Airframe', FUSE, [(x, y, 1.12) for x in (-0.06, 0.0, 0.06) for y in (1.58, 1.65, 1.72)])
uvt = lambda p, *a: in_rect(BELLY_P, 0.5 + p.x / 0.14, 0.5 + (p.y - YC) / 0.18)
MB.ref = C0 + NB * 0.05
quad_strip(MB, [rim_in, rim_out], 'M_Airframe', lambda p, i, j: uvt(p), close=True)
fan(MB, rim_out, plate_c, 'M_Airframe', lambda p, k: uvt(p), flip=True)
# flange: vertical axis (lamp axis = plane down), top conformed to the doubler plane
plane_pt, plane_n = plate_c, OUTN
fl_bot = plate_c.z - 0.012
ring_top = []
for p in circle((0, YC, plate_c.z), (0, 0, -1), 0.034, SEG):
    # point on the doubler plane straight above / below p, 2 mm inside the plate
    t = (plane_pt - p).dot(plane_n) / plane_n.z
    ring_top.append(Vector((p.x, p.y, p.z + t / 1.0)) + Vector((0, 0, 0.002)))
flange(MB, ring_top, Vector((0, YC, fl_bot)), (0, 0, -1), 0.034, 0.028, DET_DARK)
round_lens(LB, Vector((0, YC, fl_bot)), (0, 0, -1), 0.029, 0.028, 0.014, 'M_Light_Beacon')
NEWPOS['Beacon_Bottom'] = [0.0, YC, round(fl_bot - 0.019, 4)]

# ================================================================ (1c) wingtip nav / strobe housings
YN, YT, ZC = -2.420, -2.110, 2.868                 # ~0.31 m housing (Caravan unit 188 mm, Whelen Orion 600 144 mm)
BANDS = [(-2.420, -2.330, 'nav'), (-2.330, -2.318, 'gasket'), (-2.318, -2.262, 'body'), (-2.262, -2.190, 'strobe'),
         (-2.190, -2.110, 'body')]
YS = sorted({YN, YT} | {b[0] for b in BANDS} | {b[1] for b in BANDS} |
            {YN + (YT - YN) * k / 24 for k in range(25)})
NPH = 11
TIP_P = {s_: paint_patch('T_Wing', WING, [(g_ * 7.095, y, z) for y in (-2.28, -2.20, -2.12) for z in (2.85, 2.88)])
         for g_, s_ in ((1, 'L'), (-1, 'R'))}
for sg, side in ((1, 'L'), (-1, 'R')):
    rows = []
    for y in YS:
        s = (y - YN) / (YT - YN)
        fa = min(1.0, s / 0.26) ** 0.5
        fb = min(1.0, (1 - s) / 0.36) ** 0.7
        hz = 0.029 * fa * fb + 0.0015
        bx = 0.032 * fa * fb + 0.0015
        row = []
        for k in range(NPH):
            ph = -PI / 2 + PI * k / (NPH - 1)
            z = ZC + hz * math.sin(ph)
            h = WING.ray((sg * 7.6, y, z), (-sg, 0, 0), 1.0)
            xs = h[0].x if h[0] is not None else sg * 7.1
            row.append(Vector((xs - sg * 0.003 + sg * bx * math.cos(ph), y, z)))
        rows.append(row)
    nav_mat = 'M_Light_Red' if sg > 0 else 'M_Light_Green'
    for i in range(len(rows) - 1):
        ym = 0.5 * (YS[i] + YS[i + 1])
        kind = next(b[2] for b in BANDS if b[0] - 1e-9 <= ym <= b[1] + 1e-9)
        for j in range(NPH - 1):
            pts = [rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]]
            ref = Vector((sg * 7.0, 0.5 * (YS[i] + YS[i + 1]), ZC))
            MB.ref = LB.ref = ref
            if kind == 'body':
                B, mat, uvs = MB, 'M_Wing', [in_rect(TIP_P[side], (p.y - YN) / (YT - YN), (p.z - ZC) / 0.06 + 0.5) for p in pts]
            elif kind == 'gasket':
                B, mat, uvs = MB, 'M_Details', [in_rect(DET_BLACK, 0.5, (p.z - ZC) / 0.06 + 0.5) for p in pts]
            else:
                B = LB
                mat = nav_mat if kind == 'nav' else 'M_Light_White'
                y0, y1 = (-2.420, -2.330) if kind == 'nav' else (-2.262, -2.190)
                reg = L_NAV if kind == 'nav' else L_CYL
                uvs = [in_rect(reg, (p.y - y0) / (y1 - y0), (p.z - ZC) / 0.06 + 0.5) for p in pts]
            B.face([B.v(p) for p in pts], mat, uvs)
    NEWPOS[f'Nav_{side}'] = [sg * 7.118, -2.372, ZC]
    NEWPOS[f'Strobe_{side}'] = [sg * 7.124, -2.226, ZC]

# ================================================================ (1d) tail light on a boss
YE, ZT = 5.050, 2.260
base = [Vector((p.x, YE - 0.006, p.z)) for p in circle((0, YE, ZT), (0, 1, 0), 0.028, SEG)]
flange(MB, base, Vector((0, YE + 0.022, ZT)), (0, 1, 0), 0.028, 0.022, DET_DARK)
round_lens(LB, Vector((0, YE + 0.022, ZT)), (0, 1, 0), 0.0235, 0.016, 0.020, 'M_Light_White')
NEWPOS['Nav_Tail'] = [0.0, round(YE + 0.022 + 0.018, 4), ZT]

# ================================================================ (1e) landing light: cover that follows the leading edge
# v13.1: sampled by rays fanned out from a line inside the nose (x = const per column): rows ~6 deg apart, so the
# chords never cut through the facet edges of the low-poly leading edge (v13.0: rows at fixed z showed the skin
# through the cover and a ragged bezel). Cover 3.5 mm proud, a raised bezel frame around it, back onto the skin.
XL, CW = 2.300, 0.062                 # centre x, half width of the cover
TH_C, TH_R, TH_B = 38.0, 42.0, 47.0   # half angle around the nose: cover edge / bezel ridge / bezel foot (deg)
XR, XB = 0.004, 0.010                 # bezel ridge / foot beyond the cover edge in x


def nose_centre(x):
    best = None
    for k in range(61):
        z = 2.64 + 0.002 * k
        h = WING.ray((x, -3.6, z), (0, 1, 0), 2.0)
        if h[0] is not None and (best is None or h[0].y < best.y):
            best = h[0]
    return Vector((x, best.y + 0.060, best.z))


def nose_pt(x, th, off):
    c = nose_centre(x) if x not in _NC else _NC[x]
    _NC[x] = c
    d = Vector((0.0, -math.cos(math.radians(th)), math.sin(math.radians(th))))
    h = WING.ray(c, d, 0.5)
    return h[0] + d * off


_NC = {}
NXC, NTH = 5, 13
xs_c = [XL - CW + 2 * CW * k / (NXC - 1) for k in range(NXC)]
th_c = [-TH_C + 2 * TH_C * k / (NTH - 1) for k in range(NTH)]
C_MID = nose_centre(XL)
LB.ref = MB.ref = ('axis', C_MID, Vector((1, 0, 0)))
grid = [[nose_pt(x, th, 0.0035) for x in xs_c] for th in th_c]
quad_strip(LB, grid, 'M_Light_Landing',
           lambda p, i, j: in_rect(L_FLAT, j / (NXC - 1), i / (NTH - 1)))


def ring(xa, xb, th, off):
    """closed loop in (x, theta) around the cover: bottom edge, right side, top edge, left side"""
    xs = [xa + (xb - xa) * k / (NXC - 1) for k in range(NXC)]
    ts = [-th + 2 * th * k / (NTH - 1) for k in range(NTH)]
    loop = [(x, ts[0]) for x in xs] + [(xs[-1], t) for t in ts[1:]] + \
           [(x, ts[-1]) for x in reversed(xs[:-1])] + [(xs[0], t) for t in reversed(ts[1:-1])]
    return [nose_pt(x, t, off) for x, t in loop]


inner = ring(XL - CW, XL + CW, TH_C, 0.0035)
ridge = ring(XL - CW - XR, XL + CW + XR, TH_R, 0.0055)
foot = ring(XL - CW - XB, XL + CW + XB, TH_B, -0.0010)      # sunk 1 mm into the skin: a clean contact line
n_ring = len(inner)
quad_strip(MB, [inner, ridge, foot], 'M_Details', lambda p, i, j: in_rect(DET_DARK, j / n_ring, i / 2), close=True)
c0 = nose_pt(XL, 0.0, 0.0)
NEWPOS['Landing'] = [XL, round(c0.y - 0.015, 4), round(c0.z, 4)]
print('landing cover: nose', tuple(round(v, 4) for v in c0), 'cover z', round(grid[0][2].z, 3), '..', round(grid[-1][2].z, 3))

# old lenses out, new lenses in (same object name, same material order, so the export splits them per light)
old = O['src_Lights']
old.name = 'src_Lights_v12_removed'
mounts = MB.obj()
lens = LB.obj(smooth_deg=60)
lens.name = lens.data.name = 'src_Lights'
bpy.data.objects.remove(old)

# ================================================================ (2) sliding cargo doors
D_OUT, D_BACK, T_POP, T_SLIDE0 = 0.140, 1.300, 0.25, 0.22
# v13.1: the fuselage side is straight to y 1.02 and then tapers (half width at the centre rail 0.740 -> 0.672 at the
# pivot's full-open y 1.75, close to s^2): the rear roller follows it, so the open door hugs the side (5 cm off) instead
# of standing 12-22 cm off the tapered skin. tuck = D_TUCK * s^2, s = (back - B_TUCK0) / (D_BACK - B_TUCK0).
D_TUCK, B_TUCK0 = 0.068, 0.570


def S3(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def S5(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (10 - 15 * x + 6 * x * x)


def door_offsets(t, L):
    p = t / T_POP
    out_f = D_OUT * S3(p / 0.75)
    out_r = D_OUT * S3((p - 0.25) / 0.75)
    back = D_BACK * S5((t - T_SLIDE0) / (1 - T_SLIDE0))
    s = min(max((back - B_TUCK0) / (D_BACK - B_TUCK0), 0.0), 1.0)
    out_r -= D_TUCK * s * s                               # v13.1: rear tucks in along the tapering side
    return out_r, back, math.atan2(out_f - out_r, L)


DOORS = {}
for sg, side in ((1, 'L'), (-1, 'R')):
    door = O[f'CargoDoor_{side}']
    P = door.matrix_world.translation.copy()
    vs = [door.matrix_world @ v.co for v in door.data.vertices]
    y_front = min(p.y for p in vs)
    L = P.y - y_front
    DOORS[side] = dict(pivot=P, L=L, y_front=y_front, z0=min(p.z for p in vs), z1=max(p.z for p in vs),
                       inner=min(abs(p.x) for p in vs))


def door_point(q, t, side, sg):
    d = DOORS[side]
    out_r, back, yaw = door_offsets(t, d['L'])
    rel = Vector(q) - d['pivot']
    rot = Matrix.Rotation(sg * yaw, 4, 'Z')
    return d['pivot'] + (rot @ rel) + Vector((sg * out_r, back, 0.0))


def skin_x(sg, y, z):
    h = FUSE.ray((sg * 1.5, y, z), (-sg, 0, 0), 1.5)
    return abs(h[0].x) if h[0] is not None else 0.6


TS = sorted({k / 160 for k in range(161)} | {k / 400 for k in range(101)})
RB = Builder('src_DoorRails', ['M_Details'])
ARMS = {}
RAILS_JSON = {}
for sg, side in ((1, 'L'), (-1, 'R')):
    d = DOORS[side]
    yf, yr = d['y_front'], d['pivot'].y
    rollers = {
        'upper': (yf + 0.065, 2.470, d['z1'] - 0.022),
        'lower': (yf + 0.065, 1.078, d['z0'] + 0.022),
        'centre': (yr + 0.025, 1.770, 1.770),
    }
    ARMS[side] = []
    RAILS_JSON[side] = {}
    for key, (ry, rz, z_door) in rollers.items():
        # rail just outside the skin where the roller runs at full travel; closed tip = open tip - D_OUT
        y_open = ry + D_BACK
        x_skin = max(skin_x(sg, yy, rz) for yy in (ry + 0.2, 0.5 * (ry + y_open), min(y_open, 1.0)))
        x_open = x_skin + 0.022 if key != 'centre' else skin_x(sg, min(ry + 0.3, 0.9), rz) + 0.022
        tip0 = Vector((sg * (x_open - D_OUT), ry, rz))
        path = [door_point(tip0, t, side, sg) for t in TS]
        path.append(path[-1] + Vector((0, 0.035, 0)))
        ARMS[side].append((key, tip0, z_door))
        # rail = rectangle from the skin to 13 mm outside the roller path, 26 mm high; only where it is outside
        rows = []
        for i, p in enumerate(path):
            xs = skin_x(sg, p.y, rz)
            xo = abs(p.x) + 0.013
            if xo < xs + 0.008:
                continue
            xi = xs - 0.004
            rows.append([Vector((sg * xi, p.y, rz - 0.013)), Vector((sg * xo, p.y, rz - 0.013)),
                         Vector((sg * xo, p.y, rz + 0.013)), Vector((sg * xi, p.y, rz + 0.013))])
        # thin the rows (every 2nd in the straight part) for a low-poly rail
        keep = [rows[0]]
        for r_ in rows[1:-1]:
            if (r_[1] - keep[-1][1]).length > 0.045 or abs(abs(r_[1].x) - abs(keep[-1][1].x)) > 0.004:
                keep.append(r_)
        keep.append(rows[-1])
        L_rail = sum((keep[i + 1][1] - keep[i][1]).length for i in range(len(keep) - 1))
        acc = [0.0]
        for i in range(len(keep) - 1):
            acc.append(acc[-1] + (keep[i + 1][1] - keep[i][1]).length)
        def uvr(p, i, j, acc=acc, L_rail=L_rail):
            return in_rect(DET_RAIL, acc[i] / L_rail, j / 4)
        rr = keep
        for i in range(len(rr) - 1):
            RB.ref = (sum(rr[i], Vector()) + sum(rr[i + 1], Vector())) / 8
            quad_strip(RB, rr[i:i + 2], 'M_Details', lambda p, a, j, i=i: uvr(p, a + i, j), close=True)
        RB.ref = sum(rr[-2], Vector()) / 4
        fan(RB, rr[-1], sum(rr[-1], Vector()) / 4, 'M_Details', lambda p, k: in_rect(DET_RAIL, 0.9, 0.5))
        RAILS_JSON[side][key] = dict(z=rz, y_from=round(keep[0][1].y, 4), y_to=round(keep[-1][1].y, 4),
                                     x_outer=round(abs(keep[-1][1].x), 4), tip_closed=[round(v, 4) for v in tip0])
rails = RB.obj()

# roller arms: added to the door meshes (box beam from the door's inner face to the roller + the roller)
for sg, side in ((1, 'L'), (-1, 'R')):
    d = DOORS[side]
    door = O[f'CargoDoor_{side}']
    AB = Builder(f'_arms_{side}', ['M_Floor'])
    for key, tip, z_door in ARMS[side]:
        root = Vector((sg * (d['inner'] + 0.012), tip.y, z_door))
        if key == 'centre':
            root = Vector((sg * (d['inner'] + 0.012), d['pivot'].y - 0.03, z_door))
        axis = tip - root
        a, u, w = frame(axis)
        sq = [u * 0.009 + w * 0.009, -u * 0.009 + w * 0.009, -u * 0.009 - w * 0.009, u * 0.009 - w * 0.009]
        r0 = [root + q for q in sq]
        r1 = [tip + q for q in sq]
        rows_ = [r0, r1]
        AB.ref = (root + tip) / 2
        quad_strip(AB, rows_, 'M_Floor', lambda p, i, j: in_rect(FLOOR_METAL, j / 4, i), close=True)
        fan(AB, rows_[0], root, 'M_Floor', lambda p, k: in_rect(FLOOR_METAL, 0.5, 0.0), flip=True)
        # roller: vertical cylinder at the tip
        AB.ref = tip
        rb = circle(tip - Vector((0, 0, 0.008)), (0, 0, 1), 0.012, 10)
        rt = circle(tip + Vector((0, 0, 0.008)), (0, 0, 1), 0.012, 10)
        quad_strip(AB, [rb, rt], 'M_Floor', lambda p, i, j: in_rect(FLOOR_METAL, j / 10, i), close=True)
        fan(AB, rt, tip + Vector((0, 0, 0.008)), 'M_Floor', lambda p, k: in_rect(FLOOR_METAL, 0.5, 0.5))
        fan(AB, rb, tip - Vector((0, 0, 0.008)), 'M_Floor', lambda p, k: in_rect(FLOOR_METAL, 0.5, 0.5), flip=True)
    # v13.1: pull grip on the door's front edge face (dark rubber strip, 3 mm proud, 6 mm gap to the jamb): with the
    # door slid fully aft the front edge stands at the rear jamb, where a player inside the bay can reach it
    # (Socket_Handle_CargoDoor_<side>_Edge + zone in the export); the inner handle is then behind the jamb
    gx0, gx1 = 0.715, 0.737
    gy0, gy1 = d['y_front'] - 0.003, d['y_front'] + 0.004
    gz0, gz1 = 1.58, 1.82
    gc = Vector((sg * 0.726, 0.5 * (gy0 + gy1), 0.5 * (gz0 + gz1)))
    AB.ref = gc
    ring_b = [Vector((sg * gx0, gy0, gz0)), Vector((sg * gx1, gy0, gz0)), Vector((sg * gx1, gy1, gz0)), Vector((sg * gx0, gy1, gz0))]
    ring_t = [Vector((q.x, q.y, gz1)) for q in ring_b]
    quad_strip(AB, [ring_b, ring_t], 'M_Floor', lambda p, i, j: in_rect(FLOOR_DARK, j / 4, i), close=True)
    fan(AB, ring_t, Vector((gc.x, gc.y, gz1)), 'M_Floor', lambda p, k: in_rect(FLOOR_DARK, 0.5, 0.5))
    fan(AB, ring_b, Vector((gc.x, gc.y, gz0)), 'M_Floor', lambda p, k: in_rect(FLOOR_DARK, 0.5, 0.5), flip=True)
    arms = AB.obj(parent=ROOT)
    # join the arms into the door (door active: keeps the door's name, pivot, custom normals, material order)
    bpy.ops.object.select_all(action='DESELECT')
    arms.select_set(True)
    door.select_set(True)
    bpy.context.view_layer.objects.active = door
    bpy.ops.object.join()
    print('door', side, 'faces now', len(door.data.polygons), 'mats', [m.name for m in door.data.materials])

json.dump(NEWPOS, open(HERE + '/out/light_pos_v13.json', 'w'), indent=1)
DOOR_JSON = dict(
    note='v13 sliding cargo doors, build frame (x left, y aft, z up, m). Pose at t (0 closed .. 1 open): rotate the door '
         'about the vertical axis through its pivot by sign * yaw (front outward), then translate by (sign * out_r, back, 0). '
         'out_f = D_OUT * S3(p / 0.75), out_r = D_OUT * S3((p - 0.25) / 0.75), p = t / T_POP; back = D_BACK * S5((t - T_SLIDE0) / '
         '(1 - T_SLIDE0)); out_r -= D_TUCK * s^2, s = clamp01((back - B_TUCK0) / (D_BACK - B_TUCK0)) (the rear follows the '
         'tapering side); yaw = atan2(out_f - out_r, length). S3 = smoothstep, S5 = smootherstep.',
    D_OUT=D_OUT, D_BACK=D_BACK, T_POP=T_POP, T_SLIDE0=T_SLIDE0, D_TUCK=D_TUCK, B_TUCK0=B_TUCK0,
    doors={s: dict(pivot=[round(v, 4) for v in d['pivot']], length=round(d['L'], 4), y_front=round(d['y_front'], 4),
                   rails=RAILS_JSON[s]) for s, d in DOORS.items()})
json.dump(DOOR_JSON, open(HERE + '/out/doors_v13.json', 'w'), indent=1)
print('mounts faces', len(mounts.data.polygons), '| lenses faces', len(lens.data.polygons), '| rails faces',
      len(rails.data.polygons))
print('new light positions', json.dumps(NEWPOS))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('saved', OUT)
