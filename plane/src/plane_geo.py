"""Geometry builder for the expedition utility aircraft.
Blender convention: nose points to -Y, up is +Z, pilot's LEFT side is +X.
Units: metres. Ground plane z = 0 (all three tyres touch it).
Every face carries a float attribute 'mid' (material/region id) used for baking.
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix

ID = dict(FUS=1, WING=3, STAB=4, FIN=5, STRUT=6, EXHAUST=7, INTAKE=8, GLASS=9, LIGHT=10,
          INTERIOR=11, TIRE=12, HUB=13, SPINNER=14, BLADE=15, CASE_Y=16, CASE_G=17,
          CASE_T=18, CASE_D=19, CASE_M=20, JAMB=22)
SET_OF = {1: 'Fuselage', 4: 'Surfaces', 5: 'Surfaces', 6: 'Fuselage', 7: 'Fuselage', 8: 'Fuselage',
          22: 'Fuselage', 3: 'Surfaces', 9: 'Glass', 10: 'Lights',
          11: 'Details', 12: 'Details', 13: 'Details', 14: 'Details', 15: 'Details', 16: 'Details',
          17: 'Details', 18: 'Details', 19: 'Details', 20: 'Details'}

# ---------------------------------------------------------------- key dimensions
FUS_ST = [  # y, half-width, z bottom, z top, superellipse exponent
    (-2.80, 0.50, 1.50, 2.42, 3.2),
    (-2.74, 0.55, 1.45, 2.45, 3.8),
    (-2.35, 0.59, 1.40, 2.47, 4.5),
    (-1.60, 0.63, 1.32, 2.45, 5.2),
    (-1.10, 0.66, 1.25, 2.43, 6.0),
    (-1.00, 0.68, 1.23, 2.43, 6.5),
    (-0.54, 0.68, 1.23, 2.76, 6.5),
    (0.35, 0.68, 1.23, 2.76, 6.5),
    (1.20, 0.68, 1.23, 2.76, 6.5),
    (2.90, 0.68, 1.23, 2.76, 6.5),
    (3.80, 0.67, 1.25, 2.74, 6.3),
    (4.60, 0.53, 1.44, 2.63, 5.0),
    (5.40, 0.37, 1.62, 2.52, 4.2),
    (6.15, 0.23, 1.78, 2.42, 3.6),
    (6.70, 0.12, 1.90, 2.34, 3.0),
    (6.80, 0.06, 1.97, 2.28, 3.0),
]
RING_N = 40
WING_LE, WING_CHORD, WING_ZC, WING_SEMI, DIHEDRAL = -0.54, 1.95, 2.82, 6.6, math.radians(1.0)
WING_AF = dict(m=0.03, p=0.4, t=0.13)
CS_SPLIT = 0.70           # main wing box ends here (chord fraction)
CS_START = 0.712          # control surfaces start here
FLAP_X = (0.80, 3.31)
AIL_X = (3.49, 6.06)
STAB = dict(le=5.35, te=6.75, hinge=6.26, z=2.0, semi=2.6, t=0.09, elev_x0=0.23)
FIN_TE, FIN_HINGE = 6.88, 6.30
FIN_ST = [(2.30, 3.90, 0.05), (2.72, 4.70, 0.07), (3.25, 5.40, 0.10), (3.85, 5.95, 0.10)]  # z, LE y, t
RUDDER_Z0 = 2.42
PROP_C = Vector((0.0, -2.98, 2.12))
PROP_R = 1.45
MAIN_WHEEL = dict(x=1.50, y=-0.96, r=0.475, w=0.40)
TAIL_WHEEL = dict(y=6.40, r=0.165, w=0.09)
DOOR = dict(y0=1.25, y1=2.85, z0=1.32, z1=2.55)
WIN_Z = (1.95, 2.55)
WIN_L = [(-0.45, 0.30), (0.40, 1.05), (3.00, 3.60)]
WIN_R = [(-0.45, 0.30), (0.40, 1.05), (1.25, 1.95), (2.10, 2.75), (3.00, 3.60)]
SKY = dict(y0=1.60, y1=2.40, x0=0.12, x1=0.50)
BAY = dict(x=0.57, y0=1.00, y1=3.75, z0=1.30, z1=2.66)


def fus_section(y):
    """Interpolated (a, zb, zt, p) of the fuselage at station y."""
    st = FUS_ST
    if y <= st[0][0]:
        return st[0][1:]
    for s0, s1 in zip(st, st[1:]):
        if s0[0] <= y <= s1[0]:
            t = (y - s0[0]) / (s1[0] - s0[0])
            return tuple(a + (b - a) * t for a, b in zip(s0[1:], s1[1:]))
    return st[-1][1:]


def fus_half_width(y, z):
    a, zb, zt, p = fus_section(y)
    zm, b = (zb + zt) / 2, (zt - zb) / 2
    u = min(abs(z - zm) / b, 1.0)
    return a * (1 - u ** p) ** (1 / p)


def naca(c, m, p, t):
    c = min(max(c, 0.0), 1.0)
    yt = 5 * t * (0.2969 * math.sqrt(c) - 0.1260 * c - 0.3516 * c * c + 0.2843 * c ** 3 - 0.1036 * c ** 4)
    if m == 0:
        yc = 0.0
    elif c < p:
        yc = m / p ** 2 * (2 * p * c - c * c)
    else:
        yc = m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * c - c * c)
    return yc, yt


def airfoil_pts(c0, c1, n, m=0.0, p=0.4, t=0.12):
    """Closed section ring: upper surface c1->c0 then lower c0->c1. Returns [(c, z)]."""
    s = [0.5 * (1 - math.cos(math.pi * i / (n - 1))) for i in range(n)]
    cs = [c0 + (c1 - c0) * si for si in s]
    up = []
    for c in reversed(cs):
        yc, yt = naca(c, m, p, t)
        up.append((c, yc + yt))
    lo = []
    for c in cs:
        yc, yt = naca(c, m, p, t)
        lo.append((c, yc - yt))
    if c0 == 0:
        lo = lo[1:]
    if c1 >= 1.0:
        lo = lo[:-1]
    return up + lo


def wing_z(x, c, upper=False):
    yc, yt = naca(c, **WING_AF)
    return WING_ZC + (yc + (yt if upper else -yt)) * WING_CHORD + abs(x) * math.tan(DIHEDRAL)


# ---------------------------------------------------------------- bmesh helpers
class Part:
    """A bmesh with the 'mid' face layer; becomes one Blender object."""

    def __init__(self, name, group, pivot=None):
        self.name, self.group = name, group
        self.pivot = pivot
        self.bm = bmesh.new()
        self.mid = self.bm.faces.layers.float.new('mid')

    def face(self, verts, mid):
        f = self.bm.faces.new(verts)
        f[self.mid] = mid
        f.smooth = True
        return f

    def set_mid(self, faces, mid):
        for f in faces:
            f[self.mid] = mid

    def recalc(self, faces):
        bmesh.ops.recalc_face_normals(self.bm, faces=list(faces))

    def to_object(self, coll):
        me = bpy.data.meshes.new(self.name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        ob = bpy.data.objects.new(self.name, me)
        coll.objects.link(ob)
        ob['group'] = self.group
        if self.pivot is not None:
            ob['pivot'] = list(self.pivot)
        return ob


def loft(P, rings, mid, cap0=True, cap1=True, closed=True):
    """rings: list of lists of Vector (equal length). Returns (vert grid, side faces, caps)."""
    bm = P.bm
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    faces = []
    for j in range(len(vs) - 1):
        for i in range(n if closed else n - 1):
            i2 = (i + 1) % n
            faces.append(P.face((vs[j][i], vs[j][i2], vs[j + 1][i2], vs[j + 1][i]), mid))
    caps = []
    if cap0:
        caps.append(P.face(vs[0], mid))
    if cap1:
        caps.append(P.face(list(reversed(vs[-1])), mid))
    P.recalc(faces + caps)
    return vs, faces, caps


def lathe(P, prof, o, ax, e1, e2, n, mid, closed_profile=False, offset=None, mids=None):
    """Revolve profile [(w, r)] around axis (o, ax). offset(k, j, w, r) -> extra radius."""
    bm = P.bm
    grid = []
    poles = {}
    for k in range(n):
        th = 2 * math.pi * k / n
        d = e1 * math.cos(th) + e2 * math.sin(th)
        row = []
        for j, (w, r) in enumerate(prof):
            if r < 1e-6:
                if j not in poles:
                    poles[j] = bm.verts.new(o + ax * w)
                row.append(poles[j])
            else:
                rr = r + (offset(k, j, w, r) if offset else 0.0)
                row.append(bm.verts.new(o + ax * w + d * rr))
        grid.append(row)
    faces = []
    m = len(prof)
    jr = range(m if closed_profile else m - 1)
    for k in range(n):
        k2 = (k + 1) % n
        for j in jr:
            j2 = (j + 1) % m
            q = [grid[k][j], grid[k2][j], grid[k2][j2], grid[k][j2]]
            uq = []
            for v in q:
                if v not in uq:
                    uq.append(v)
            if len(uq) < 3:
                continue
            mm = mids[j] if mids else mid
            faces.append(P.face(uq, mm))
    P.recalc(faces)
    return faces


def superellipse(a, zb, zt, p, n=RING_N):
    zm, b = (zb + zt) / 2, (zt - zb) / 2
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        out.append((a * math.copysign(abs(c) ** (2 / p), c), zm + b * math.copysign(abs(s) ** (2 / p), s)))
    return out


def frame_from(direction):
    d = direction.normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    e1 = d.cross(up).normalized()
    e2 = d.cross(e1).normalized()
    return d, e1, e2


def tube(P, a, b, r, mid, n=8, r2=None, cap=True, ellipse=None, ref=None):
    """Straight tube from a to b. ellipse=(ra, rb) with ra along 'ref' direction."""
    a, b = Vector(a), Vector(b)
    d, e1, e2 = frame_from(b - a)
    if ref is not None:
        ref = Vector(ref)
        e1 = (ref - d * ref.dot(d)).normalized()
        e2 = d.cross(e1).normalized()
    rings = []
    for pt, rad in ((a, r), (b, r2 if r2 is not None else r)):
        ring = []
        for i in range(n):
            th = 2 * math.pi * i / n
            if ellipse:
                ring.append(pt + e1 * math.cos(th) * ellipse[0] * rad / r + e2 * math.sin(th) * ellipse[1] * rad / r)
            else:
                ring.append(pt + (e1 * math.cos(th) + e2 * math.sin(th)) * rad)
        rings.append(ring)
    return loft(P, rings, mid, cap, cap)


def box(P, center, size, mid, bevel=0.0, segs=1, rot=None):
    M = Matrix.Translation(Vector(center))
    if rot is not None:
        M = M @ rot.to_4x4()
    M = M @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
    res = bmesh.ops.create_cube(P.bm, size=1.0, matrix=M)
    verts = res['verts']
    faces = list({f for v in verts for f in v.link_faces})
    P.set_mid(faces, mid)
    for f in faces:
        f.smooth = True
    if bevel > 0:
        edges = list({e for f in faces for e in f.edges})
        r = bmesh.ops.bevel(P.bm, geom=edges, offset=bevel, offset_type='OFFSET', segments=segs,
                            profile=0.5, affect='EDGES', clamp_overlap=True)
        for f in r['faces']:
            f[P.mid] = mid
            f.smooth = True
        faces = list({f for v in r['verts'] for f in v.link_faces} | set(faces))
        faces = [f for f in faces if f.is_valid]
    return faces


def extract(P, faces, name, group, pivot=None):
    """Copy faces to a new Part and delete them from P."""
    N = Part(name, group, pivot)
    vmap = {}
    for f in faces:
        vs = []
        for v in f.verts:
            if v not in vmap:
                vmap[v] = N.bm.verts.new(v.co)
            vs.append(vmap[v])
        nf = N.face(vs, f[P.mid])
        nf.smooth = f.smooth
    bmesh.ops.delete(P.bm, geom=list(faces), context='FACES')
    return N


# ---------------------------------------------------------------- parts
def build_fuselage():
    P = Part('Fuselage', 'Body')
    rings = []
    for (y, a, zb, zt, p) in FUS_ST:
        rings.append([Vector((x, y, z)) for (x, z) in superellipse(a, zb, zt, p)])
    vs, faces, caps = loft(P, rings, ID['FUS'])
    bm = P.bm
    # ---- cowl front: lip + deep dark intake recess (spinner sits in front of it)
    front = caps[0]
    bmesh.ops.inset_region(bm, faces=[front], thickness=0.045, depth=0.0, use_even_offset=True)
    r = bmesh.ops.inset_region(bm, faces=[front], thickness=0.012, depth=-0.30, use_even_offset=True)
    P.set_mid(r['faces'] + [front], ID['INTAKE'])
    # ---- cuts for windows / door / skylights, limited to the cabin
    def cabin_geom():
        fs = [f for f in bm.faces if -1.05 < f.calc_center_median().y < 3.85]
        es = list({e for f in fs for e in f.edges})
        vv = list({v for f in fs for v in f.verts})
        return fs + es + vv
    ycuts = sorted({-0.45, 0.30, 0.40, 1.05, 1.25, 1.60, 1.95, 2.10, 2.40, 2.75, 2.85, 3.00, 3.60})
    for y in ycuts:
        bmesh.ops.bisect_plane(bm, geom=cabin_geom(), dist=1e-5, plane_co=(0, y, 0), plane_no=(0, 1, 0))
    for z in (DOOR['z0'], WIN_Z[0], 2.20, WIN_Z[1]):
        bmesh.ops.bisect_plane(bm, geom=cabin_geom(), dist=1e-5, plane_co=(0, 0, z), plane_no=(0, 0, 1))
    for x in (-SKY['x1'], -SKY['x0'], SKY['x0'], SKY['x1']):
        bmesh.ops.bisect_plane(bm, geom=cabin_geom(), dist=1e-5, plane_co=(x, 0, 0), plane_no=(1, 0, 0))
    bm.faces.ensure_lookup_table()

    def inside(c, y0, y1, z0, z1):
        return y0 < c.y < y1 and z0 < c.z < z1

    door_f, glass_regions = [], []
    wins = [[] for _ in range(len(WIN_L) + len(WIN_R))]
    wshield, sky = [], [[], []]
    for f in bm.faces:
        c = f.calc_center_median()
        if c.x > 0.3 and inside(c, DOOR['y0'], DOOR['y1'], DOOR['z0'], DOOR['z1']):
            door_f.append(f)
            continue
        for i, (y0, y1) in enumerate(WIN_L):
            if c.x > 0.3 and inside(c, y0, y1, *WIN_Z):
                wins[i].append(f)
        for i, (y0, y1) in enumerate(WIN_R):
            if c.x < -0.3 and inside(c, y0, y1, *WIN_Z):
                wins[len(WIN_L) + i].append(f)
        if -1.0 < c.y < -0.54 and c.z > 2.20:
            wshield.append(f)
        if c.z > 2.70 and SKY['y0'] < c.y < SKY['y1'] and SKY['x0'] < abs(c.x) < SKY['x1']:
            sky[0 if c.x > 0 else 1].append(f)
    # ---- cargo door: copy skin patch into its own part, open a hole
    hinge = Vector((fus_half_width(2.05, DOOR['z1']), (DOOR['y0'] + DOOR['y1']) / 2, DOOR['z1']))
    door = extract(P, door_f, 'CargoDoor', 'CargoDoor', pivot=hinge)
    # jamb: extrude the hole boundary inward to the bay wall plane
    bnd = [e for e in bm.edges if e.is_boundary]
    ex = bmesh.ops.extrude_edge_only(bm, edges=bnd)
    newv = [g for g in ex['geom'] if isinstance(g, bmesh.types.BMVert)]
    for v in newv:
        v.co.x = BAY['x'] - 0.005
    jf = [g for g in ex['geom'] if isinstance(g, bmesh.types.BMFace)]
    ctr = Vector((0.6, (DOOR['y0'] + DOOR['y1']) / 2, (DOOR['z0'] + DOOR['z1']) / 2))
    for f in jf:
        f[P.mid] = ID['JAMB']
        f.smooth = False
        f.normal_update()
        cc = f.calc_center_median()
        to_c = ctr - cc
        to_c.x = 0
        if f.normal.dot(to_c) < 0:
            f.normal_flip()
    # ---- windows: recessed glass with a rubber/frame lip
    regions = [w for w in wins if w] + [wshield] + [s for s in sky if s]
    for reg in regions:
        reg = [f for f in reg if f.is_valid]
        r = bmesh.ops.inset_region(bm, faces=reg, thickness=0.022, depth=-0.012, use_even_offset=True)
        P.set_mid(r['faces'], ID['FUS'])
        P.set_mid(reg, ID['GLASS'])
    glass = extract(P, [f for f in bm.faces if f[P.mid] == ID['GLASS']], 'Glass_Fuselage', 'Body')
    return P, door, glass


def solidify_part(P, thickness, rim_mid):
    """Give an open surface part thickness (inward along vertex normals)."""
    bm = P.bm
    bm.normal_update()
    faces = list(bm.faces)
    bnd = [e for e in bm.edges if e.is_boundary]
    inner = {v: bm.verts.new(v.co - v.normal * thickness) for v in list(bm.verts)}
    for f in faces:
        nf = P.face([inner[v] for v in reversed(f.verts)], f[P.mid])
    for e in bnd:
        v0, v1 = e.verts
        # orient using the owning face's winding
        f = e.link_faces[0]
        loop = [l for l in f.loops if l.edge == e][0]
        a, b = loop.vert, loop.link_loop_next.vert
        P.face([b, a, inner[a], inner[b]], rim_mid)


def build_door(door):
    solidify_part(door, 0.03, ID['FUS'])
    # handle
    y, z = 2.05, 1.52
    x = fus_half_width(y, z)
    box(door, (x + 0.02, y, z), (0.03, 0.20, 0.035), ID['STRUT'], bevel=0.006)
    for dy in (-0.08, 0.08):
        box(door, (x + 0.01, y + dy, z), (0.03, 0.03, 0.03), ID['STRUT'])
    # hinge knuckles along the top edge
    for yy in (1.45, 2.05, 2.65):
        tube(door, (x - 0.02, yy - 0.08, DOOR['z1'] - 0.005), (x - 0.02, yy + 0.08, DOOR['z1'] - 0.005), 0.018,
             ID['STRUT'], n=8)
    return door


def build_cowl_details(P):
    # chin intake scoop
    rings = []
    for (y, a, zb, zt) in ((-2.76, 0.24, 1.35, 1.56), (-2.30, 0.26, 1.33, 1.55), (-1.70, 0.20, 1.34, 1.46)):
        rings.append([Vector((x, y, z)) for (x, z) in superellipse(a, zb, zt, 4.0, n=16)])
    vs, faces, caps = loft(P, rings, ID['FUS'])
    bmesh.ops.inset_region(P.bm, faces=[caps[0]], thickness=0.02, depth=0.0, use_even_offset=True)
    r = bmesh.ops.inset_region(P.bm, faces=[caps[0]], thickness=0.005, depth=-0.18, use_even_offset=True)
    P.set_mid(r['faces'] + [caps[0]], ID['INTAKE'])
    # turboprop exhaust stacks
    for s in (1, -1):
        a = Vector((s * 0.55, -1.80, 2.02))
        b = Vector((s * 0.80, -1.52, 1.97))
        vs, faces, caps = tube(P, a, b, 0.085, ID['EXHAUST'], n=12)
        end = caps[1]
        bmesh.ops.inset_region(P.bm, faces=[end], thickness=0.012, depth=0.0)
        r = bmesh.ops.inset_region(P.bm, faces=[end], thickness=0.001, depth=-0.12)
        P.set_mid(r['faces'] + [end], ID['INTAKE'])
        # flange ring
        tube(P, a + (b - a) * 0.55, a + (b - a) * 0.62, 0.097, ID['EXHAUST'], n=12)


def build_wing():
    P = Part('Wing', 'Body')
    af_main = airfoil_pts(0.0, CS_SPLIT, 14, **WING_AF)
    af_rear = airfoil_pts(CS_SPLIT, 1.0, 7, **WING_AF)

    def ring(pts, x):
        dz = abs(x) * math.tan(DIHEDRAL)
        return [Vector((x, WING_LE + c * WING_CHORD, WING_ZC + zz * WING_CHORD + dz)) for c, zz in pts]

    xs = [-6.6, -6.06, -4.7, -3.4, -2.1, -0.80, 0.0, 0.80, 2.1, 3.4, 4.7, 6.06, 6.6]
    loft(P, [ring(af_main, x) for x in xs], ID['WING'])
    # fixed trailing-edge fills (root, between flap & aileron, tip)
    for xr in ((-0.80, 0.0, 0.80), (3.31, 3.49), (-3.49, -3.31), (6.06, 6.6), (-6.6, -6.06)):
        loft(P, [ring(af_rear, x) for x in xr], ID['WING'])
    return P


def build_control_surface(name, group, x0, x1, le, te, zc, af, hinge_c, ring_fn, mid):
    P = Part(name, group)
    pts = airfoil_pts(hinge_c, 1.0, 7, **af)
    loft(P, [ring_fn(pts, x0), ring_fn(pts, x1)], mid)
    return P


def build_flaps_ailerons():
    parts = []
    af = airfoil_pts(CS_START, 1.0, 7, **WING_AF)

    def ring(x):
        dz = abs(x) * math.tan(DIHEDRAL)
        return [Vector((x, WING_LE + c * WING_CHORD, WING_ZC + zz * WING_CHORD + dz)) for c, zz in af]

    yc_h, _ = naca(CS_START, **WING_AF)
    for name, (x0, x1) in (('Flap', FLAP_X), ('Aileron', AIL_X)):
        for side, s in (('L', 1), ('R', -1)):
            xa, xb = sorted((s * x0, s * x1))
            xm = (xa + xb) / 2
            piv = Vector((xm, WING_LE + CS_START * WING_CHORD,
                          WING_ZC + yc_h * WING_CHORD + abs(xm) * math.tan(DIHEDRAL)))
            P = Part(f'{name}_{side}', f'{name}_{side}', pivot=piv)
            loft(P, [ring(xa), ring(xb)], ID['WING'])
            parts.append(P)
    return parts


def build_struts(P):
    for s in (1, -1):
        A = Vector((s * 0.60, 0.20, 1.33))
        B = Vector((s * 3.60, -0.05, wing_z(3.6, 0.255) + 0.01))
        tube(P, A, B, 0.045, ID['STRUT'], n=12, ellipse=(0.05, 0.02), ref=(0, 1, 0))
        # end fittings
        box(P, A + Vector((s * 0.03, 0, 0)), (0.08, 0.10, 0.08), ID['STRUT'], bevel=0.01)
        box(P, B - Vector((0, 0, 0.03)), (0.06, 0.12, 0.08), ID['STRUT'], bevel=0.01)
        # jury strut
        J = A + (B - A) * 0.45
        W = Vector((J.x, 0.02, wing_z(J.x, 0.28) + 0.01))
        tube(P, J, W, 0.016, ID['STRUT'], n=8)


def build_main_gear(P):
    wx, wy, wr = MAIN_WHEEL['x'], MAIN_WHEEL['y'], MAIN_WHEEL['r']
    for s in (1, -1):
        top = Vector((s * 0.40, -0.78, 1.30))
        bot = Vector((s * 1.22, wy, wr + 0.03))
        # flat spring-steel leg: rectangle section, wide along Y
        tube(P, top, bot, 0.07, ID['STRUT'], n=8, ellipse=(0.075, 0.03), ref=(0, 1, 0), r2=0.055)
        box(P, top + Vector((0, 0, 0.02)), (0.22, 0.20, 0.08), ID['STRUT'], bevel=0.01)
        # axle + brake disc + caliper
        tube(P, Vector((s * 1.18, wy, wr)), Vector((s * (wx - 0.10), wy, wr)), 0.035, ID['STRUT'], n=10)
        tube(P, Vector((s * 1.27, wy, wr)), Vector((s * 1.29, wy, wr)), 0.13, ID['EXHAUST'], n=18)
        box(P, (s * 1.26, wy - 0.10, wr + 0.08), (0.06, 0.07, 0.10), ID['STRUT'], bevel=0.01)


def build_tail_gear(P):
    ty, tr = TAIL_WHEEL['y'], TAIL_WHEEL['r']
    top = Vector((0, 5.55, 1.72))
    low = Vector((0, 6.30, 0.40))
    tube(P, top, low, 0.035, ID['STRUT'], n=10, r2=0.03)
    box(P, (0, 5.55, 1.66), (0.14, 0.24, 0.06), ID['STRUT'], bevel=0.01)
    box(P, (0, 6.31, 0.38), (0.17, 0.09, 0.05), ID['STRUT'], bevel=0.008)
    for s in (1, -1):
        tube(P, Vector((s * 0.065, 6.31, 0.37)), Vector((s * 0.065, ty, tr)), 0.018, ID['STRUT'], n=6)
    tube(P, Vector((-0.08, ty, tr)), Vector((0.08, ty, tr)), 0.012, ID['STRUT'], n=8)


def build_antennas(P):
    # whip antennas (swept back) + blade antenna
    for base, tip in (((0.25, 1.90, 2.755), (0.25, 2.25, 3.40)),
                      ((-0.20, 3.20, 2.735), (-0.20, 3.40, 3.28)),
                      ((0.00, 0.35, 3.00), (0.00, 0.62, 3.55))):
        tube(P, base, tip, 0.009, ID['STRUT'], n=6, r2=0.005)
        tube(P, Vector(base) - Vector((0, 0, 0.01)), Vector(base) + Vector((0, 0, 0.02)), 0.03, ID['STRUT'], n=10)
    # blade antenna on the belly
    Pb = [Vector((0.0, 1.9, 1.25)), Vector((0.0, 2.15, 1.25)), Vector((0.0, 2.2, 1.05)), Vector((0.0, 2.08, 1.05))]
    rings = [[v + Vector((0.012, 0, 0)) for v in Pb], [v + Vector((-0.012, 0, 0)) for v in Pb]]
    loft(P, rings, ID['STRUT'])


def build_tail():
    P = Part('Tail', 'Body')
    st = STAB
    chord = st['te'] - st['le']
    hc = (st['hinge'] - st['le']) / chord
    af = airfoil_pts(0.0, hc, 10, m=0.0, t=st['t'])

    def sring(pts, x):
        return [Vector((x, st['le'] + c * chord, st['z'] + zz * chord)) for c, zz in pts]

    xs = [-st['semi'], -1.3, -st['elev_x0'], 0.0, st['elev_x0'], 1.3, st['semi']]
    loft(P, [sring(af, x) for x in xs], ID['STAB'])
    # fin (fixed part)
    def fin_ring(z, le, t, c0, c1, n):
        ch = FIN_TE - le
        pts = airfoil_pts(c0, c1, n, m=0.0, t=t)
        return [Vector((zz * ch, le + c * ch, z)) for c, zz in pts]

    rings = []
    for z, le, t in FIN_ST:
        hcf = (FIN_HINGE - le) / (FIN_TE - le)
        rings.append(fin_ring(z, le, t, 0.0, hcf, 10))
    loft(P, rings, ID['FIN'])
    return P


def fin_le(z):
    for (z0, l0, t0), (z1, l1, t1) in zip(FIN_ST, FIN_ST[1:]):
        if z0 <= z <= z1:
            u = (z - z0) / (z1 - z0)
            return l0 + (l1 - l0) * u, t0 + (t1 - t0) * u
    return FIN_ST[-1][1], FIN_ST[-1][2]


def build_rudder():
    piv = Vector((0.0, FIN_HINGE + 0.02, (RUDDER_Z0 + FIN_ST[-1][0]) / 2))
    P = Part('Rudder', 'Rudder', pivot=piv)
    rings = []
    for z in (RUDDER_Z0, 3.25, FIN_ST[-1][0]):
        le, t = fin_le(z)
        ch = FIN_TE - le
        c0 = (FIN_HINGE + 0.02 - le) / ch
        pts = airfoil_pts(c0, 1.0, 7, m=0.0, t=t)
        rings.append([Vector((zz * ch, le + c * ch, z)) for c, zz in pts])
    loft(P, rings, ID['FIN'])
    return P


def build_elevator():
    st = STAB
    chord = st['te'] - st['le']
    c0 = (st['hinge'] + 0.02 - st['le']) / chord
    piv = Vector((0.0, st['hinge'] + 0.02, st['z']))
    P = Part('Elevator', 'Elevator', pivot=piv)
    pts = airfoil_pts(c0, 1.0, 7, m=0.0, t=st['t'])

    def sring(x):
        return [Vector((x, st['le'] + c * chord, st['z'] + zz * chord)) for c, zz in pts]

    for s in (1, -1):
        xa, xb = sorted((s * st['elev_x0'], s * st['semi']))
        loft(P, [sring(xa), sring(xb)], ID['STAB'])
    # torque tube joining the halves behind the tail cone
    tube(P, Vector((-st['elev_x0'] - 0.01, st['hinge'] + 0.05, st['z'])),
         Vector((st['elev_x0'] + 0.01, st['hinge'] + 0.05, st['z'])), 0.02, ID['STAB'], n=8)
    return P


def build_lights():
    P = Part('NavLights', 'Body')
    spots = []
    for s in (1, -1):
        x = s * (WING_SEMI + 0.005)
        spots.append((Vector((x, WING_LE + 0.30 * WING_CHORD, wing_z(x, 0.3) + 0.08)), Vector((s, 0, 0)), 0.045))
        spots.append((Vector((s * (STAB['semi'] + 0.005), STAB['le'] + 0.35, STAB['z'])), Vector((s, 0, 0)), 0.03))
    spots.append((Vector((0.0, 6.10, FIN_ST[-1][0] + 0.005)), Vector((0, 0, 1)), 0.035))
    for c, d, r in spots:
        _, e1, e2 = frame_from(d)
        prof = [(0.0, r * 1.05), (0.02, r), (0.045, r * 0.75), (0.06, r * 0.35), (0.065, 0.0)]
        prof = [(-0.01, 0.0)] + prof
        lathe(P, prof, c, d.normalized(), e1, e2, 12, ID['LIGHT'])
    return P, spots


def build_propeller():
    P = Part('Propeller', 'Propeller', pivot=PROP_C.copy())
    # spinner
    base_y, L, R = -2.82, 0.58, 0.255
    prof = [(0.0, 0.0)]
    for i in range(11):
        u = i / 10
        prof.append((u * L, R * (1 - u ** 1.7) ** 0.62 if u < 1 else 0.0))
    o = Vector((0.0, base_y, PROP_C.z))
    lathe(P, prof, o, Vector((0, -1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)), 24, ID['SPINNER'])
    # blades
    rs = [0.12, 0.26, 0.45, 0.70, 0.95, 1.18, 1.34, 1.43, PROP_R]
    chords = [0.13, 0.20, 0.25, 0.25, 0.23, 0.20, 0.16, 0.12, 0.06]
    betas = [58, 48, 38, 30, 24, 19, 16, 14, 13]
    ts = [0.45, 0.20, 0.12, 0.09, 0.075, 0.065, 0.06, 0.06, 0.06]
    ea = Vector((0, -1, 0))
    for i in range(3):
        phi = math.radians(90 + 120 * i)
        er = Vector((math.cos(phi), 0, math.sin(phi)))
        et = Vector((-math.sin(phi), 0, math.cos(phi)))
        rings = []
        for r, ch, be, t in zip(rs, chords, betas, ts):
            b = math.radians(be)
            dc = et * math.cos(b) + ea * math.sin(b)
            dt = -et * math.sin(b) + ea * math.cos(b)
            pts = airfoil_pts(0.0, 1.0, 9, m=0.03 if t < 0.3 else 0.0, p=0.4, t=t)
            rings.append([PROP_C + er * r + dc * ((c - 0.35) * ch) + dt * (zz * ch) for c, zz in pts])
        loft(P, rings, ID['BLADE'])
    return P


TIRE_PROF = [(-0.15, 0.235), (-0.19, 0.28), (-0.20, 0.36), (-0.195, 0.42), (-0.18, 0.455), (-0.14, 0.472),
             (-0.07, 0.475), (0.0, 0.475), (0.07, 0.475), (0.14, 0.472), (0.18, 0.455), (0.195, 0.42),
             (0.20, 0.36), (0.19, 0.28), (0.15, 0.235), (0.0, 0.228)]
HUB_PROF = [(-0.135, 0.0), (-0.135, 0.055), (-0.115, 0.075), (-0.105, 0.20), (-0.15, 0.232), (0.15, 0.232),
            (0.105, 0.20), (0.115, 0.075), (0.135, 0.055), (0.135, 0.0)]


def build_wheel(name, center, width, radius, outward, lugs=True, n=64):
    sw, sr = width / 0.40, radius / 0.475
    P = Part(name, name, pivot=Vector(center))
    o = Vector(center)
    ax = Vector((outward, 0, 0))
    e1, e2 = Vector((0, 1, 0)), Vector((0, 0, 1))

    def lug(k, j, w, r):
        if not lugs or r < 0.44:
            return 0.0
        blk = (k // 2) % 2
        if abs(w) < 0.01:
            return 0.012 * sr
        on = (blk == 0) if w < 0 else (blk == 1)
        return (0.03 if on else 0.0) * sr * (1.0 if abs(w) < 0.19 else 0.6)

    tp = [(w * sw, r * sr) for w, r in TIRE_PROF]
    lathe(P, tp, o, ax, e1, e2, n, ID['TIRE'], closed_profile=True,
          offset=(lambda k, j, w, r: lug(k, j, w / sw, r / sr)))
    hp = [(w * sw, r * sr) for w, r in HUB_PROF]
    lathe(P, hp, o, ax, e1, e2, 24, ID['HUB'])
    # wheel nuts on the outer face
    for i in range(6):
        th = 2 * math.pi * i / 6
        c = o + ax * (0.137 * sw) + (e1 * math.cos(th) + e2 * math.sin(th)) * (0.12 * sr)
        tube(P, c - ax * 0.01, c + ax * 0.018 * sw, 0.014 * sr, ID['HUB'], n=6)
    return P


def build_cargo_bay():
    P = Part('CargoBay', 'CargoBay')
    x, y0, y1, z0, z1 = BAY['x'], BAY['y0'], BAY['y1'], BAY['z0'], BAY['z1']
    V = lambda a, b, c: P.bm.verts.new((a, b, c))
    def quad(a, b, c, d, mid=ID['INTERIOR']):
        f = P.face([V(*a), V(*b), V(*c), V(*d)], mid)
        f.smooth = False
        return f
    I = ID['INTERIOR']
    quad((-x, y0, z0), (x, y0, z0), (x, y1, z0), (-x, y1, z0))            # floor (up)
    quad((-x, y0, z1), (-x, y1, z1), (x, y1, z1), (x, y0, z1))            # ceiling (down)
    quad((-x, y0, z0), (-x, y1, z0), (-x, y1, z1), (-x, y0, z1))          # far wall (+X)
    quad((-x, y0, z0), (-x, y0, z1), (x, y0, z1), (x, y0, z0))            # front bulkhead (+Y)
    quad((-x, y1, z0), (x, y1, z0), (x, y1, z1), (-x, y1, z1))            # rear bulkhead (-Y)
    for ya, yb in ((y0, DOOR['y0']), (DOOR['y1'], y1)):                  # near wall pieces (-X)
        quad((x, ya, z0), (x, ya, z1), (x, yb, z1), (x, yb, z0))
    quad((x, DOOR['y0'], DOOR['z1']), (x, DOOR['y0'], z1), (x, DOOR['y1'], z1), (x, DOOR['y1'], DOOR['z1']))
    # fix orientation: all normals must face the bay centre
    ctr = Vector((0, (y0 + y1) / 2, (z0 + z1) / 2))
    for f in P.bm.faces:
        f.normal_update()
        if f.normal.dot(ctr - f.calc_center_median()) < 0:
            f.normal_flip()
    # floor tie-down rails and ribs
    for xx in (-0.32, 0.32):
        box(P, (xx, (y0 + y1) / 2, z0 + 0.012), (0.04, y1 - y0 - 0.04, 0.024), ID['CASE_M'])
    for yy in (1.6, 2.3, 3.0):
        box(P, (-x + 0.02, yy, (z0 + z1) / 2), (0.04, 0.05, z1 - z0 - 0.02), ID['INTERIOR'])
    # cases: (center, size, colour id)
    cases = [((0.30, 2.22, z0 + 0.20), (0.50, 0.84, 0.40), ID['CASE_Y']),
             ((0.30, 2.18, z0 + 0.40 + 0.165), (0.44, 0.56, 0.33), ID['CASE_G']),
             ((0.28, 1.52, z0 + 0.28), (0.46, 0.44, 0.56), ID['CASE_T']),
             ((0.28, 1.50, z0 + 0.56 + 0.13), (0.40, 0.40, 0.26), ID['CASE_D']),
             ((0.30, 2.93, z0 + 0.24), (0.46, 0.44, 0.48), ID['CASE_T']),
             ((-0.25, 2.60, z0 + 0.15), (0.40, 0.70, 0.30), ID['CASE_G'])]
    for c, s, mid in cases:
        c = Vector(c)
        box(P, c, s, mid, bevel=0.025, segs=2)
        # rims (lid seam band), latches, handle on the door-facing (+X) side
        box(P, c + Vector((0, 0, s[2] * 0.18)), (s[0] + 0.012, s[1] + 0.012, 0.03), mid, bevel=0.006)
        for dy in (-s[1] * 0.3, s[1] * 0.3):
            box(P, c + Vector((s[0] / 2 + 0.008, dy, s[2] * 0.18)), (0.02, 0.05, 0.07), ID['CASE_M'], bevel=0.004)
        box(P, c + Vector((0, 0, s[2] / 2 + 0.022)), (0.04, min(0.22, s[1] * 0.4), 0.02), ID['CASE_M'], bevel=0.005)
        for dy in (-0.09, 0.09):
            if s[1] * 0.4 > 0.18:
                box(P, c + Vector((0, dy, s[2] / 2 + 0.01)), (0.035, 0.025, 0.025), ID['CASE_M'])
    return P


def build_all(coll):
    parts = []
    fus, door, glass = build_fuselage()
    build_cowl_details(fus)
    build_struts(fus)
    build_main_gear(fus)
    build_tail_gear(fus)
    build_antennas(fus)
    parts += [fus, build_door(door), glass]
    parts.append(build_wing())
    parts += build_flaps_ailerons()
    parts.append(build_tail())
    parts.append(build_rudder())
    parts.append(build_elevator())
    lights, spots = build_lights()
    parts.append(lights)
    parts.append(build_propeller())
    w = MAIN_WHEEL
    parts.append(build_wheel('Wheel_L', (w['x'], w['y'], w['r']), w['w'], w['r'], 1))
    parts.append(build_wheel('Wheel_R', (-w['x'], w['y'], w['r']), w['w'], w['r'], -1))
    t = TAIL_WHEEL
    parts.append(build_wheel('Wheel_Tail', (0.0, t['y'], t['r']), t['w'], t['r'], 1, n=40))
    parts.append(build_cargo_bay())
    objs = [p.to_object(coll) for p in parts]
    return objs, spots
