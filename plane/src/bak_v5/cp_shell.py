
# ================================================================== v5 INTERIOR SHELL (Caravan-style lined cabin)
# Lining profile in arc-length coordinates; chamfered liner panels that follow the fuselage section and the
# wing-box headliner; window/door trims and seals; floor, seat tracks, cargo tracks, tie-downs; headliner with
# the ventilation plenum; bulkhead liners; windshield frame trims; cargo barrier with webbing nets.
# Interior atlas materials (src_IN_*), webbing on its own tiled material.
import bisect
from mathutils import geometry as mgeo

LIN = LY.SKIN_T + 0.025            # liner face inset from the outer skin (25 mm insulation gap)
FZ = LY.FLOOR_Z
BARRIER_Y = -1.72
REAR_Y = LY.REAR_BULKHEAD_Y - 0.02
Z_KICK = 1.28                      # top of the dark kick strip
PD = LY.PILOT_DOOR[0]
CD = LY.CARGO_DOOR[0]
PD_FWD = PD[0][0] - 0.035          # -3.155 footwell kick panel ends at the pilot door
PD_AFT = PD[1][0] + 0.035          # -1.945 wall liner starts aft of the pilot door
CD_FWD = CD[0][0] - 0.035          # -0.885
CD_AFT = CD[1][0] + 0.035          # 0.485
WS_AFT_Y = LY.WS_L[0][2][1]        # -2.65 windshield aft edge
WS_X = LY.WS_L[0][1][0]            # 0.655 windshield outer edge
TRACK_X = (0.42, 0.0, -0.42)
TIE_Y = (-1.45, -0.80, -0.15, 0.50, 1.10)
HX0 = 0.105                        # plenum half width (headliner panels start here)
DY = 0.005
_SEC = {}


# ------------------------------------------------------------------ lining profile (right half, inset LIN)
def _section(y):
    zb, zt, hw, ne = station_at(y)
    return (round(zb, 5), round(zt, 5), round(hw, 5), round(ne, 4))


def _curve(sec):
    """(X, Z, S) from the floor up to the roof centre, S = arc length"""
    if sec in _SEC:
        return _SEC[sec]
    zb, zt, hw, ne = sec
    zc, b, a = (zb + zt) / 2, (zt - zb) / 2 - LIN, hw - LIN
    tf = min(1.0, (zc - FZ) / b)
    X, Z = [a * (1 - tf ** ne) ** (1 / ne)], [FZ]
    N = 3000
    for k in range(N + 1):
        th = -math.pi / 2 + math.pi * k / N
        c, s_ = math.cos(th), math.sin(th)
        z = zc + b * math.copysign(abs(s_) ** (2 / ne), s_)
        if z <= Z[-1] + 1e-9:
            continue
        X.append(a * abs(c) ** (2 / ne))
        Z.append(z)
    S = [0.0]
    for k in range(1, len(X)):
        S.append(S[-1] + math.hypot(X[k] - X[k - 1], Z[k] - Z[k - 1]))
    _SEC[sec] = (X, Z, S)
    return _SEC[sec]


def _pair(y):
    f = y / DY
    i0 = math.floor(f)
    return _curve(_section(i0 * DY)), _curve(_section((i0 + 1) * DY)), f - i0


def _s_at_z(C, z):
    X, Z, S = C
    if z <= Z[0]:
        return 0.0
    if z >= Z[-1]:
        return S[-1]
    k = bisect.bisect_left(Z, z)
    dz = Z[k] - Z[k - 1]
    t = (z - Z[k - 1]) / dz if dz > 0 else 0.0
    return S[k - 1] + (S[k] - S[k - 1]) * t


def _at_s(C, s):
    X, Z, S = C
    s = min(max(s, 0.0), S[-1])
    k = min(max(1, bisect.bisect_left(S, s)), len(S) - 1)
    ds = S[k] - S[k - 1]
    t = (s - S[k - 1]) / ds if ds > 0 else 0.0
    L = ds if ds > 0 else 1.0
    return (X[k - 1] + (X[k] - X[k - 1]) * t, Z[k - 1] + (Z[k] - Z[k - 1]) * t,
            (X[k] - X[k - 1]) / L, (Z[k] - Z[k - 1]) / L)


def s_of_z(y, z):
    A, B, t = _pair(y)
    return _s_at_z(A, z) * (1 - t) + _s_at_z(B, z) * t


def wall_frame(y, s):
    """(x, z, tx, tz): lining point at arc length s and the unit tangent (pointing up the profile)"""
    A, B, t = _pair(y)
    a, b = _at_s(A, s), _at_s(B, s)
    x, z, tx, tz = [a[i] + (b[i] - a[i]) * t for i in range(4)]
    L = math.hypot(tx, tz) or 1.0
    return x, z, tx / L, tz / L


def wall_pt(side, y, s, d=0.0):
    """point on the lining surface (side +1 = left / +X), d = offset along the inward normal"""
    x, z, tx, tz = wall_frame(y, s)
    return Vector((side * (x - tz * d), y, z + tx * d))


def wall_in(side, p):
    x, z, tx, tz = wall_frame(p.y, s_of_z(p.y, p.z))
    return Vector((-side * tz, 0.0, tx))


def surf_x_any(y, z, inset):
    zb, zt, hw, ne = station_at(y)
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    a, b = hw - inset, hh - inset
    t = min(0.999999, abs(z - zc) / b)
    return a * (1 - t ** ne) ** (1 / ne)


def surf_z_top(y, x, inset):
    zb, zt, hw, ne = station_at(y)
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    a, b = hw - inset, hh - inset
    return zc + b * max(0.0, 1 - (abs(x) / a) ** ne) ** (1 / ne)


def x_floor(y):
    return surf_x_any(y, FZ, LIN)


def s_junction(y):
    """the wall liner ends 12 mm under the headliner"""
    return s_of_z(y, head_z(y) - 0.012)


# ------------------------------------------------------------------ 2D polygon helpers + chamfered panel builder
def dedupe(P, eps=1e-6):
    out = []
    for p in P:
        if not out or math.dist(p, out[-1]) > eps:
            out.append(tuple(p))
    while len(out) > 2 and math.dist(out[0], out[-1]) <= eps:
        out.pop()
    return out


def offs(P, d):
    """offset a convex(ish) polygon by d (+ = outward), either winding; collinear neighbours handled"""
    n = len(P)
    area = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))
    sg = 1 if area > 0 else -1
    lines = []
    for i in range(n):
        p, q = P[i], P[(i + 1) % n]
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        nx, ny = uy * sg, -ux * sg
        lines.append(((p[0] + nx * d, p[1] + ny * d), (ux, uy), (nx, ny)))
    out = []
    for i in range(n):
        (p1, d1, n1), (p2, d2, n2) = lines[i - 1], lines[i]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-6:
            out.append((P[i][0] + (n1[0] + n2[0]) / 2 * d, P[i][1] + (n1[1] + n2[1]) / 2 * d))
        else:
            t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
            out.append((p1[0] + d1[0] * t, p1[1] + d1[1] * t))
    return out


def densify(polys, step):
    """subdivide matching polygons edge by edge with equal counts (keeps the point correspondence)"""
    n = len(polys[0])
    out = [[] for _ in polys]
    for i in range(n):
        j = (i + 1) % n
        L = max(math.dist(P[i], P[j]) for P in polys)
        k = max(1, int(math.ceil(L / step)))
        for t in range(k):
            f = t / k
            for P, O in zip(polys, out):
                O.append((P[i][0] + (P[j][0] - P[i][0]) * f, P[i][1] + (P[j][1] - P[i][1]) * f))
    return out


def orient(f, inward, bm=None):
    """face normal towards `inward`; marks the face as pre-oriented (plate 2) so mk() keeps it"""
    f.normal_update()
    if f.normal.dot(inward) < 0:
        f.normal_flip()
    if bm is not None:
        f[plate_layer(bm)] = 2


def panel2d(bm, O, holes, mapf, inward_fn, depth=0.005, cham=0.005, mat=0, grid=0.07, back=False, step=0.035,
            back_mat=None):
    """chamfered panel from an outline O (u, v) with holes; mapf(u, v, d) -> world point, inward_fn(p) -> direction
    into the cabin. Face at depth `depth`, chamfer from the outline (depth 0). Edges are densified so the
    boundary follows curved mappings. Chamfers share the face boundary vertices (one UV island per panel);
    panels with a hole are cut in two through the hole (no hollow islands in the atlas)."""
    plate_layer(bm)                      # create the layer before holding face references
    O = dedupe(O)
    O, I = densify([O, offs(O, -cham)], step)
    HH = []
    for H in holes:
        H = dedupe(H)
        HH.append(densify([H, offs(H, cham)], step))
    Hs = [h[1] for h in HH]
    loops = [I] + Hs
    pts = [p for L in loops for p in L]
    us, vs = [p[0] for p in I], [p[1] for p in I]
    u = min(us) + grid / 2
    while u < max(us):
        v = min(vs) + grid / 2
        while v < max(vs):
            q = (u, v)
            if LY.point_in_poly(q, I) and not any(LY.point_in_poly(q, H) for H in Hs):
                if min(math.dist(q, p) for p in pts) > grid * 0.45:
                    pts.append(q)
            v += grid
        u += grid
    edges = []
    k = 0
    for L in loops:
        n = len(L)
        edges += [(k + i, k + (i + 1) % n) for i in range(n)]
        k += n
    res = mgeo.delaunay_2d_cdt([Vector(p) for p in pts], edges, [list(range(len(I)))], 1, 1e-7)
    vco, faces, orig = res[0], res[2], res[3]
    inmap = {}
    for oi, srcs in enumerate(orig):
        for s_ in srcs:
            inmap[s_] = oi
    bv = [bm.verts.new(mapf(p.x, p.y, depth)) for p in vco]
    made = []
    for fi in faces:
        c = (sum(vco[i].x for i in fi) / len(fi), sum(vco[i].y for i in fi) / len(fi))
        if any(LY.point_in_poly(c, H) for H in Hs):
            continue
        try:
            f = bm.faces.new([bv[i] for i in fi])
        except ValueError:
            continue
        f.material_index = mat
        orient(f, inward_fn(f.calc_center_median()), bm)
        made.append((f, c[0]))

    def strip(A, k0, dA):
        n = len(A)
        va = [bm.verts.new(mapf(p[0], p[1], dA)) for p in A]
        vb = [bv[inmap[k0 + i]] for i in range(n)]
        for i in range(n):
            j = (i + 1) % n
            try:
                f = bm.faces.new((va[i], va[j], vb[j], vb[i]))
            except ValueError:
                continue
            f.material_index = mat
            orient(f, inward_fn(f.calc_center_median()), bm)
            made.append((f, (A[i][0] + A[j][0]) / 2))
    strip(O, 0, 0.0)
    k = len(I)
    for H, H2 in HH:
        strip(H, k, 0.0)
        k += len(H2)
    if holes:
        uc = sum(p[0] for p in holes[0]) / len(holes[0])
        side_of = {f: (cu < uc) for f, cu in made}
        cut = set()
        for f, cu in made:
            for e in f.edges:
                lf = [g for g in e.link_faces if g in side_of]
                if len(lf) == 2 and side_of[lf[0]] != side_of[lf[1]]:
                    cut.add(e)
        if cut:
            bmesh.ops.split_edges(bm, edges=list(cut))
    if back:            # flat back for free-standing panels
        bb = [bm.verts.new(mapf(p[0], p[1], 0.0)) for p in O]
        f = bm.faces.new(bb)
        f.material_index = mat if back_mat is None else back_mat
        orient(f, -inward_fn(f.calc_center_median()), bm)


def rrect(u0, u1, v0, v1, r):
    return LY.rounded_poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], r, seg=3)


class Band:
    """wall strip between s = lo(y) and s = hi(y); panel coords (y, w) with w in metre-like units [0, H]"""

    def __init__(self, lo, hi, y0, y1):
        self.lo, self.hi = lo, hi
        self.H = sum(hi(y) - lo(y) for y in (y0, (y0 + y1) / 2, y1)) / 3

    def s(self, y, w):
        a, b = self.lo(y), self.hi(y)
        return a + (b - a) * w / self.H

    def w(self, y, s):
        a, b = self.lo(y), self.hi(y)
        return (s - a) * self.H / (b - a)


def wall_panel(bm, side, y0, y1, lo, hi, depth, cham, mat, r=0.012, wins=(), grow=0.014, grid=0.07, base_d=0.0):
    B = Band(lo, hi, y0, y1)
    if B.H < 0.008:
        return None
    holes = []
    for outline, wr in wins:
        pts = LY.rounded_poly(LY.offset_poly(outline, grow), wr + grow, seg=4)
        pts = densify([dedupe(pts)], 0.025)[0]
        holes.append([(y, B.w(y, s_of_z(y, z))) for y, z in pts])
    rr = max(cham + 0.001, min(r, B.H / 2 - 0.0005))
    panel2d(bm, rrect(y0, y1, 0.0, B.H, rr), holes,
            lambda u, v, d: wall_pt(side, u, B.s(u, v), d + base_d),
            lambda p: wall_in(side, p), depth=depth, cham=cham, mat=mat, grid=grid)
    return B


def prof_sweep(bm, path, prof, mat, up_hint=Vector((0, 0, 1)), caps=True):
    """sweep a closed 2D profile (a along tangent x up, b along up) along a polyline"""
    rings = []
    N = len(path)
    for k in range(N):
        p = Vector(path[k])
        tng = (Vector(path[min(k + 1, N - 1)]) - Vector(path[max(k - 1, 0)])).normalized()
        sv = tng.cross(up_hint).normalized()
        uv_ = sv.cross(tng).normalized()
        rings.append([p + sv * a + uv_ * b for a, b in prof])
    loft(bm, rings, True, caps, caps, mat)


def rr_prof(a0, a1, b0, b1, r, seg=2):
    """rounded rectangle profile for prof_sweep"""
    return LY.rounded_poly([(a0, b0), (a1, b0), (a1, b1), (a0, b1)], r, seg=seg)


# ------------------------------------------------------------------ wall liners (Kydex-like sidewall panels)
LINER = bmesh.new()
kick_hi = lambda y: s_of_z(y, Z_KICK)
zero = lambda y: 0.0
for side in (1, -1):
    for y0, y1, wins in ((PD_AFT, -1.20, [LY.W2]), (-1.20, CD_FWD, []), (CD_AFT, REAR_Y, [LY.W4])):
        wall_panel(LINER, side, y0, y1, kick_hi, s_junction, 0.006, 0.006, MI['src_IN_Liner'], wins=wins)
        wall_panel(LINER, side, y0, y1, zero, kick_hi, 0.014, 0.007, MI['src_IN_Kick'], r=0.010, grid=0.06)
    # strip above the cargo door (door surround .. headliner)
    wall_panel(LINER, side, CD_FWD, CD_AFT, lambda y: s_of_z(y, CD[2][1] + 0.033), s_junction, 0.006, 0.004,
               MI['src_IN_Liner'], r=0.006, grid=0.05)
    # footwell side kick panel forward of the pilot door (floor .. behind the instrument panel)
    y0, y1 = LY.FIREWALL_Y + 0.01, PD_FWD
    wall_panel(LINER, side, y0, y1, zero, lambda y: s_of_z(y, 1.62), 0.010, 0.006, MI['src_IN_Kick'], r=0.010,
               grid=0.05)
    # fresh-air outlet in the kick panel
    yc = (y0 + y1) / 2
    p = wall_pt(side, yc, s_of_z(yc, 1.32), 0.010)
    revolve(LINER, [(0.0, 0.0), (0.0, 0.028), (-side * 0.006, 0.026), (-side * 0.010, 0.016), (-side * 0.012, 0.0)],
            'X', (p.x, p.y, p.z), segs=16, mat=MI['src_IN_Trim'])
    for k in range(3):                                         # louvre vanes
        box(LINER, (p.x - side * 0.010, p.y, p.z - 0.012 + k * 0.012), (0.004, 0.036, 0.003), mat=MI['src_IN_Trim'])
    # strut-fitting cover plate on the kick strip (strut attaches outside at y ~ -1.55)
    yc = -1.55
    wall_panel(LINER, side, yc - 0.07, yc + 0.07, lambda y: s_of_z(y, 1.12), lambda y: s_of_z(y, 1.26), 0.004,
               0.002, MI['src_IN_Steel'], r=0.010, grid=0.04, base_d=0.014)
    for uu in (yc - 0.052, yc + 0.052):
        for zz in (1.14, 1.24):
            p = wall_pt(side, uu, s_of_z(uu, zz), 0.018)
            n_ = wall_in(side, p)
            cylinder(LINER, p, p + n_ * 0.003, 0.0055, 0.0042, 8, mat=MI['src_IN_Steel'])
mk('CP_Liner', LINER)


# ------------------------------------------------------------------ window and door trims (closeouts) + seals
def surround(bm, side, outline, r, grow_in, mat, lip=0.006, shallow=None, step=0.025):
    """trim ring: jamb from the inner skin at the opening to the trim face, bezel onto the liner, hidden flange.
    shallow(y, z) -> 0..1 blends to a thin frame on the inner skin where no liner borders the opening."""
    plate_layer(bm)
    base = LY.rounded_poly(outline, r, seg=4)
    gin = LY.rounded_poly(LY.offset_poly(outline, grow_in), r + grow_in, seg=4)
    glp = LY.rounded_poly(LY.offset_poly(outline, grow_in + lip), r + grow_in + lip, seg=4)
    base, gin, glp = densify([base, gin, glp], step)
    cy = sum(p[0] for p in outline) / len(outline)
    cz = sum(p[1] for p in outline) / len(outline)
    rings = []
    for (ys, zs), (yi, zi), (yl, zl) in zip(base, gin, glp):
        h = shallow(ys, zs) if shallow else 0.0
        fi = (grow_in * (1 - h) + 0.004 * h) / grow_in
        fl = ((grow_in + lip) * (1 - h) + 0.008 * h) / (grow_in + lip)
        yi, zi = ys + (yi - ys) * fi, zs + (zi - zs) * fi
        yl, zl = ys + (yl - ys) * fl, zs + (zl - zs) * fl
        di = (LIN + 0.010) * (1 - h) + (LY.SKIN_T + 0.008) * h
        dl = (LIN + 0.002) * (1 - h) + (LY.SKIN_T + 0.004) * h
        if h > 0.0:
            cap = head_z(yi) - 0.004
            zi, zl = min(zi, cap), min(zl, cap + 0.001)
        rings.append([Vector((side * surf_x_any(ys, zs, LY.SKIN_T + 0.002), ys, zs)),
                      Vector((side * surf_x_any(yi, zi, di), yi, zi)),
                      Vector((side * surf_x_any(yl, zl, dl), yl, zl)),
                      Vector((side * surf_x_any(yl, zl, dl - 0.006), yl, zl))])
    n = len(rings)
    vr = [[bm.verts.new(p) for p in r_] for r_ in rings]
    cuts = {0, n // 4, n // 2, 3 * n // 4}                 # quarter rings: no hollow islands in the atlas
    vdup = {c: [bm.verts.new(p) for p in rings[c]] for c in cuts}
    for i in range(n):
        j = (i + 1) % n
        ri = vdup[i] if i in cuts else vr[i]
        for k in range(3):
            try:
                f = bm.faces.new((ri[k], vr[j][k], vr[j][k + 1], ri[k + 1]))
            except ValueError:
                continue
            f.material_index = mat
            fc = f.calc_center_median()
            radial = Vector((0, fc.y - cy, fc.z - cz)).normalized()
            # k0: jamb, faces the opening centre; k1: bezel, faces the cabin; k2: hidden flange, faces outward
            ref = (-radial + Vector((-side * 0.3, 0, 0))) if k == 0 else (
                Vector((-side, 0, 0)) if k == 1 else radial)
            orient(f, ref, bm)


def pd_shallow(y, z):
    """pilot door: no wall liner along the top and the windshield-side slope"""
    zl = 1.95 + (2.50 - 1.95) * (y - PD[0][0]) / (PD[1][0] - PD[0][0])
    return smooth01(zl - 0.03, zl + 0.03, z)


TRIM = bmesh.new()
SEAL = bmesh.new()
for side in (1, -1):
    for w in LY.SIDE_FIXED['L']:
        surround(TRIM, side, w[0], w[1], 0.014, MI['src_IN_Trim'])
    surround(TRIM, side, PD, LY.PILOT_DOOR[1], 0.030, MI['src_IN_Trim'], lip=0.008, shallow=pd_shallow)
    surround(TRIM, side, CD, LY.CARGO_DOOR[1], 0.030, MI['src_IN_Trim'], lip=0.008)
    for outline, r in (LY.PILOT_DOOR, LY.CARGO_DOOR):
        pts = densify([LY.rounded_poly(LY.offset_poly(outline, -0.003), max(r - 0.003, 0.01), seg=4)], 0.06)[0]
        path = [Vector((side * (surf_x_any(y, z, LY.SKIN_T) - 0.009), y, z)) for y, z in pts]
        n_ = len(path)
        for q in range(4):                     # four open pieces (closed loops unwrap into hollow islands)
            i0, i1 = q * n_ // 4, (q + 1) * n_ // 4
            seg = [path[i % n_] for i in range(i0, i1 + 1)]
            sweep(SEAL, seg, 0.009, 0.007, 6, cap0=False, cap1=False, mat=MI['src_IN_Seal'])
mk('CP_Trims', TRIM)
mk('CP_DoorSeals', SEAL, smooth=60)

# ------------------------------------------------------------------ floor: cockpit plate, mats, seat tracks; cargo tread plate, tracks, tie-downs
FL = bmesh.new()
up = lambda p: Vector((0, 0, 1))
mapfl = lambda u, v, d: Vector((u, v, FZ + d))


def floor_poly(y0, y1, m=0.002, step=0.05):
    n = max(2, int(math.ceil((y1 - y0) / step)))
    ys = [y0 + (y1 - y0) * i / n for i in range(n + 1)]
    return [(x_floor(y) - m, y) for y in ys] + [(-(x_floor(y) - m), y) for y in reversed(ys)]


panel2d(FL, floor_poly(LY.FIREWALL_Y + 0.005, BARRIER_Y - 0.003), [], mapfl, up, depth=0.003, cham=0.003,
        mat=MI['src_IN_FloorPaint'], grid=0.12)
for v0, v1 in ((BARRIER_Y + 0.003, -0.203), (-0.197, REAR_Y - 0.003)):
    panel2d(FL, floor_poly(v0, v1), [], mapfl, up, depth=0.004, cham=0.003, mat=MI['src_IN_Tread'], grid=0.12)
# sub-floor (dark, closes the panel seams) and seam cover strips
panel2d(FL, floor_poly(LY.FIREWALL_Y + 0.004, REAR_Y - 0.001, m=0.001), [], mapfl, up, depth=0.0005, cham=0.001,
        mat=MI['src_IN_Hidden'], grid=0.3)
for ys_ in (BARRIER_Y, -0.20):
    hw_ = x_floor(ys_) - 0.03
    box(FL, (0.0, ys_, FZ + 0.0055), (2 * hw_, 0.028, 0.003), mat=MI['src_IN_Steel'], bevel=0.001, bevel_segs=1)
# floor edge strips along the kick panels (hide the floor/liner junction)
edge_prof = rr_prof(-0.030, 0.004, -0.002, 0.007, 0.003)
for side in (1, -1):
    for v0, v1 in ((PD_AFT, CD_FWD - 0.03), (CD_AFT + 0.03, REAR_Y - 0.004)):
        n = max(2, int((v1 - v0) / 0.05))
        ys = [v0 + (v1 - v0) * i / n for i in range(n + 1)]
        if side < 0:
            ys = ys[::-1]
        path = [Vector((side * (x_floor(y) - 0.002), y, FZ + 0.003)) for y in ys]
        prof_sweep(FL, path, edge_prof, MI['src_IN_Steel'])
# footwell mats (ribbed rubber) and heel plates
for sx in LY.SEATS_X:
    box(FL, (sx, -2.86, FZ + 0.006), (0.40, 0.46, 0.006), mat=MI['src_IN_Seal'], bevel=0.004, bevel_segs=1)
    for k in range(13):
        box(FL, (sx, -3.07 + k * 0.034, FZ + 0.0105), (0.36, 0.012, 0.003), mat=MI['src_IN_Seal'])
    box(FL, (sx, -2.98, FZ + 0.0115), (0.30, 0.10, 0.003), mat=MI['src_IN_Tread'], bevel=0.002, bevel_segs=1)
# seat tracks: I-section, 2 per seat, with end stops
for sx in LY.SEATS_X:
    for dx in (-0.15, 0.15):
        x = sx + dx
        y0, y1 = -2.66, -1.86
        box(FL, (x, (y0 + y1) / 2, FZ + 0.0045), (0.032, y1 - y0, 0.003), mat=MI['src_IN_Track'], bevel=0.001,
            bevel_segs=1)
        box(FL, (x, (y0 + y1) / 2, FZ + 0.012), (0.008, y1 - y0, 0.014), mat=MI['src_IN_Track'])
        box(FL, (x, (y0 + y1) / 2, FZ + 0.0205), (0.022, y1 - y0, 0.004), mat=MI['src_IN_Track'], bevel=0.0012,
            bevel_segs=1)
        for yy in (y0 + 0.01, y1 - 0.01):
            box(FL, (x, yy, FZ + 0.017), (0.026, 0.012, 0.012), mat=MI['src_IN_Steel'], bevel=0.002, bevel_segs=1)
# cargo L-tracks (slightly proud) + double-stud tie-down fittings with D-rings
TRACK_Y = {}
TIEDOWNS = []                                          # D-ring centres (Unity sockets Socket_TieDown_NN)
for tx in TRACK_X:
    y0, y1 = BARRIER_Y + 0.04, REAR_Y - 0.04
    while abs(tx) > 0 and x_floor(y1) - 0.06 < abs(tx):
        y1 -= 0.01
    TRACK_Y[tx] = (y0, y1)
    box(FL, (tx, (y0 + y1) / 2, FZ + 0.006), (0.034, y1 - y0, 0.004), mat=MI['src_IN_Track'], bevel=0.0015,
        bevel_segs=1)
    for ty in TIE_Y:
        if not (y0 + 0.04 < ty < y1 - 0.04):
            continue
        c = Vector((tx, ty, FZ + 0.008))
        TIEDOWNS.append((tx, ty, FZ + 0.008 + 0.026))
        box(FL, c + Vector((0, 0, 0.006)), (0.026, 0.056, 0.012), mat=MI['src_IN_Steel'], bevel=0.003, bevel_segs=1)
        ring = [c + Vector((0, 0.022 * math.cos(a_), 0.014 + 0.024 * math.sin(a_))) for a_ in
                [math.pi * i / 10 for i in range(11)]]
        sweep(FL, ring, 0.0045, 0.0045, 8, mat=MI['src_IN_Steel'], up_hint=Vector((1, 0, 0)))
        cylinder(FL, c + Vector((0.017, 0, 0.012)), c + Vector((-0.017, 0, 0.012)), 0.005, 0.005, 8,
                 mat=MI['src_IN_Steel'])
# door sills: tread-plate steps from the floor up to the sill, following the fuselage wall
for side in (1, -1):
    for outline, zs in ((PD, PD[0][1]), (CD, CD[0][1])):
        y0, y1 = outline[0][0] + 0.03, outline[1][0] - 0.03
        n = max(2, int((y1 - y0) / 0.05))
        ys = [y0 + (y1 - y0) * i / n for i in range(n + 1)]
        if side < 0:
            ys = ys[::-1]
        path = [Vector((side * (surf_x_any(y, zs, LY.SKIN_T) + 0.004), y, FZ)) for y in ys]
        prof_sweep(FL, path, rr_prof(-0.135, 0.0, -0.004, zs - FZ + 0.008, 0.004), MI['src_IN_Tread'])
mk('CP_Floor', FL)

# ------------------------------------------------------------------ headliner: panels on the wing box, plenum, vents, lights, grab handles
HL = bmesh.new()
down = lambda p: Vector((0, 0, -1))
XREF = 0.60


def head_X(v):
    """headliner half width: to the wall-liner junction (+6 mm overlap); over the pilot door (no wall liner)
    out to the inner skin"""
    xj = wall_frame(v, s_junction(v))[0] + 0.006
    xs = surf_x_any(v, head_z(v), LY.SKIN_T + 0.004)
    h = smooth01(PD_AFT + 0.02, PD_AFT - 0.02, v)
    return xj * (1 - h) + xs * h


def head_map(sg):
    def f(u, v, d):
        X = head_X(v)
        x = HX0 + (u - HX0) * (X - HX0) / (XREF - HX0)
        t = min(1.0, x / X)
        return Vector((sg * x, v, head_z(v) + 0.008 * (1 - t * t) - d))
    return f


seams = [WS_AFT_Y + 0.005, BARRIER_Y, CD_FWD, CD_AFT, REAR_Y]
for v0, v1 in zip(seams[:-1], seams[1:]):
    for sg in (1, -1):
        panel2d(HL, rrect(HX0, XREF, v0 + 0.002, v1 - 0.002, 0.010), [], head_map(sg), down, depth=0.006,
                cham=0.005, mat=MI['src_IN_Headliner'], grid=0.08)
# centre plenum (ventilation duct fed from the wing-root inlets); the overhead console sits on it in front
v0, v1 = LY.OVERHEAD['y1'], REAR_Y - 0.004
n = max(4, int((v1 - v0) / 0.05))
rings = []
for k in range(n + 1):
    y = v0 + (v1 - v0) * k / n
    zt = head_z(y) + 0.010
    zb_ = head_z(y) - 0.032
    rings.append([Vector(p) for p in ((HX0, y, zt), (HX0, y, zb_ + 0.012), (HX0 - 0.004, y, zb_ + 0.004),
                                      (HX0 - 0.012, y, zb_), (-HX0 + 0.012, y, zb_), (-HX0 + 0.004, y, zb_ + 0.004),
                                      (-HX0, y, zb_ + 0.012), (-HX0, y, zt))])
loft(HL, rings, False, False, False, mat=MI['src_IN_Headliner'])
# eyeball outlets over each cargo zone
for yv in (-1.05, 0.30):
    zc_ = head_z(yv) - 0.032
    revolve(HL, [(0.0, 0.0), (0.0, 0.030), (-0.004, 0.030), (-0.008, 0.024), (-0.008, 0.0)], 'Z', (0.0, yv, zc_),
            segs=16, mat=MI['src_IN_Trim'])
    revolve(HL, [(-0.008, 0.0), (-0.008, 0.019), (-0.016, 0.017), (-0.022, 0.010), (-0.024, 0.0)], 'Z',
            (0.0, yv, zc_), segs=14, mat=MI['src_IN_Steel'])
# grab handles: over the cargo doors (strip above the door) and on the headliner over the pilot doors
for side in (1, -1):
    yc_, L = -0.20, 0.30
    a0 = wall_pt(side, yc_ - L / 2, s_junction(yc_ - L / 2) - 0.05, 0.006)
    a1 = wall_pt(side, yc_ + L / 2, s_junction(yc_ + L / 2) - 0.05, 0.006)
    n0, n1 = wall_in(side, a0), wall_in(side, a1)
    path = [a0, a0 + n0 * 0.040 + Vector((0, 0.02, 0)), a1 + n1 * 0.040 - Vector((0, 0.02, 0)), a1]
    sweep(HL, spline(path, 4), 0.011, 0.011, 10, mat=MI['src_IN_Trim'], up_hint=Vector((0, 0, 1)))
    for p, n_ in ((a0, n0), (a1, n1)):
        cylinder(HL, p - n_ * 0.006, p + n_ * 0.012, 0.016, 0.014, 12, mat=MI['src_IN_Trim'])
    xh = side * 0.50
    ya, yb = -2.36, -2.10
    za, zb2 = head_z(ya) - 0.004, head_z(yb) - 0.004
    path = [Vector((xh, ya, za)), Vector((xh, ya + 0.02, za - 0.040)), Vector((xh, yb - 0.02, zb2 - 0.040)),
            Vector((xh, yb, zb2))]
    sweep(HL, spline(path, 4), 0.011, 0.011, 10, mat=MI['src_IN_Trim'], up_hint=Vector((1, 0, 0)))
    for p in path[0], path[-1]:
        cylinder(HL, p + Vector((0, 0, 0.008)), p - Vector((0, 0, 0.012)), 0.016, 0.014, 12, mat=MI['src_IN_Trim'])
# headliner-to-wall cove strips (wherever a wall liner meets the headliner)
for side in (1, -1):
    n = int((REAR_Y - PD_AFT) / 0.05)
    path = [wall_pt(side, y, s_junction(y) - 0.004, 0.010) for y in
            [PD_AFT + (REAR_Y - PD_AFT) * i / n for i in range(n + 1)]]
    sweep(HL, path, 0.012, 0.009, 8, mat=MI['src_IN_Trim'], up_hint=Vector((0, 0, 1)))
mk('CP_Headliner', HL, smooth=40)

# cargo courtesy lights in the plenum (lens split to Lens_CargoLight by material in the Unity export)
bm = bmesh.new()
for yl in (-0.55, 0.75):
    zc_ = head_z(yl) - 0.032
    rbox(bm, (0.0, yl, zc_ - 0.004), (0.15, 0.07, 0.008), MI['src_IN_Trim'], bevel=0.004, segs=1)
    rbox(bm, (0.0, yl, zc_ - 0.010), (0.12, 0.05, 0.006), MI['M_Light_Cabin'], bevel=0.003, segs=1)
mk('CP_CargoLight', bm)

# ------------------------------------------------------------------ windshield frame: aft header (either side of the compass), centre post cover
WF = bmesh.new()
for sg in (1, -1):
    xs_ = [sg * (0.05 + (WS_X - 0.035 - 0.05) * i / 14) for i in range(15)]
    path = [Vector((x, WS_AFT_Y + 0.004, surf_z_top(WS_AFT_Y, x, LY.SKIN_T) + 0.002)) for x in xs_]
    prof_sweep(WF, path, rr_prof(-0.017, 0.017, -0.036, 0.0, 0.007), MI['src_IN_Trim'])
ys_ = [-2.705 - 0.535 * i / 14 for i in range(15)]
path = [Vector((0.0, y, surf_z_top(y, 0.0, LY.SKIN_T) + 0.002)) for y in ys_]
prof_sweep(WF, path, rr_prof(-0.036, 0.036, -0.016, 0.0, 0.006), MI['src_IN_Trim'])
mk('CP_WindshieldFrame', WF)

# ------------------------------------------------------------------ bulkheads: firewall blanket (footwell), rear bulkhead liner
BK = bmesh.new()
yfw = LY.FIREWALL_Y + 0.012
for j in range(4):
    z0, z1 = FZ + 0.01 + j * 0.10, FZ + 0.01 + (j + 1) * 0.10
    xw = surf_x_any(yfw, z0, LIN + 0.012)
    w = 2 * xw / 10
    for i in range(10):
        rbox(BK, (-xw + (i + 0.5) * w, yfw, (z0 + z1) / 2), (w - 0.002, 0.016, 0.098), MI['src_IN_Insul'],
             bevel=0.006, segs=1)
# firewall closeout behind the blanket / panel: full lining section, dark
yfp = LY.FIREWALL_Y + 0.004
X_, Z_, S_ = _curve(_section(yfp))
half = [(x, z) for x, z in zip(X_, Z_)][::12] + [(0.0, Z_[-1])]
O = dedupe([(x, z) for x, z in half] + [(-x, z) for x, z in reversed(half)])
O = [O[i] for i in mgeo.convex_hull_2d(O)]
panel2d(BK, O, [], lambda u, v, d: Vector((u, yfp + d, v)), lambda p: Vector((0, 1, 0)), depth=0.002, cham=0.002,
        mat=MI['src_IN_Kick'], grid=0.15)
# rear bulkhead liner: lining section at REAR_Y up into the headliner, chamfered, with an access panel
X_, Z_, S_ = _curve(_section(REAR_Y))
ztop = head_z(REAR_Y) + 0.004
half = [(x, z) for x, z in zip(X_, Z_) if z <= ztop]
half = half[::max(1, len(half) // 40)] + [(max(0.0, surf_x_any(REAR_Y, ztop, LIN)), ztop)]
O = [(x, z) for x, z in half] + [(-x, z) for x, z in reversed(half)]
O = dedupe(O)
O = [O[i] for i in mgeo.convex_hull_2d(O)]
mapr = lambda u, v, d: Vector((u, REAR_Y - d, v))
panel2d(BK, O, [], mapr, lambda p: Vector((0, -1, 0)), depth=0.008, cham=0.006, mat=MI['src_IN_Liner'], grid=0.12)
panel2d(BK, rrect(-0.30, 0.30, 1.40, 2.05, 0.02), [], lambda u, v, d: Vector((u, REAR_Y - 0.008 - d, v)),
        lambda p: Vector((0, -1, 0)), depth=0.004, cham=0.003, mat=MI['src_IN_Liner'], grid=0.1)
for u in (-0.28, 0.28):
    for v in (1.42, 1.725, 2.03):
        cylinder(BK, Vector((u, REAR_Y - 0.011, v)), Vector((u, REAR_Y - 0.015, v)), 0.0065, 0.005, 10,
                 mat=MI['src_IN_Steel'])
mk('CP_Bulkheads', BK)

# ------------------------------------------------------------------ cargo barrier: two composite posts + three webbing nets
BR = bmesh.new()
NETS = bmesh.new()
uvn = NETS.loops.layers.uv.new('UVMap')
POST_X = (0.25, -0.25)
zt_ = head_z(BARRIER_Y) + 0.004
for px in POST_X:
    rbox(BR, (px, BARRIER_Y, (FZ + zt_) / 2), (0.055, 0.045, zt_ - FZ), MI['src_IN_Composite'], bevel=0.008, segs=2)
    rbox(BR, (px, BARRIER_Y, FZ + 0.03), (0.09, 0.08, 0.06), MI['src_IN_Steel'], bevel=0.006, segs=1)       # floor fitting
    rbox(BR, (px, BARRIER_Y, zt_ - 0.030), (0.08, 0.07, 0.05), MI['src_IN_Steel'], bevel=0.006, segs=1)    # roof fitting
mk('CP_Barrier', BR)


def strap(bm, a, b, w, t, normal, mat, u0=0.0):
    """flat webbing strap from a to b, width w across, thickness t along `normal`; UV u in metres"""
    d = (b - a)
    dn = d.normalized()
    side = dn.cross(normal).normalized() * (w / 2)
    nn = normal.normalized() * (t / 2)
    cs = [a - side - nn, a + side - nn, a + side + nn, a - side + nn]
    ce = [b - side - nn, b + side - nn, b + side + nn, b - side + nn]
    va = [bm.verts.new(p) for p in cs]
    vb = [bm.verts.new(p) for p in ce]
    uvl = bm.loops.layers.uv.active
    mid = (a + b) / 2
    su, nu = side.normalized(), nn.normalized()
    for i in range(4):
        j = (i + 1) % 4
        f = bm.faces.new((va[i], va[j], vb[j], vb[i]))
        f.material_index = mat
        off = f.calc_center_median() - mid
        off -= dn * off.dot(dn)
        f.normal_update()
        if f.normal.dot(off) < 0:
            f.normal_flip()
        wide = i % 2 == 0                      # faces at -nn / +nn span the strap width
        for lp in f.loops:
            q = lp.vert.co - a
            lp[uvl].uv = (u0 + q.dot(dn), (0.5 + q.dot(su) / w) if wide else (0.075 + 0.075 * q.dot(nu) / (t / 2)))


def net(bm, xa, xb, z0, z1, y, cell=0.13):
    """webbing net between the edge curves x = xa(z) .. xb(z), z0..z1, in the plane y"""
    nrm = Vector((0, 1, 0))
    W = MI['src_IN_Webbing']
    nz = max(2, round((z1 - z0) / cell))
    zs = [z0 + (z1 - z0) * k / nz for k in range(nz + 1)]
    nx = max(2, round(max(abs(xb(z) - xa(z)) for z in zs) / cell))
    P = lambda f, z, dy=0.0: Vector((xa(z) + (xb(z) - xa(z)) * f, y + dy, z))
    strap(bm, P(0, z0), P(1, z0), 0.038, 0.005, nrm, W)
    strap(bm, P(0, z1), P(1, z1), 0.038, 0.005, nrm, W)
    for f in (0.0, 1.0):
        for k in range(nz):
            strap(bm, P(f, zs[k]), P(f, zs[k + 1]), 0.038, 0.005, nrm, W, u0=zs[k] - z0)
    for i in range(1, nx):
        for k in range(nz):
            strap(bm, P(i / nx, zs[k], 0.004), P(i / nx, zs[k + 1], 0.004), 0.025, 0.003, nrm, W, u0=zs[k] - z0)
    for k in range(1, nz):
        strap(bm, P(0, zs[k], -0.004), P(1, zs[k], -0.004), 0.025, 0.003, nrm, W)


zn0, zn1 = FZ + 0.06, head_z(BARRIER_Y) - 0.05
yn = BARRIER_Y + 0.03
net(NETS, lambda z: POST_X[0] - 0.035, lambda z: POST_X[1] + 0.035, zn0, zn1, yn)
wall_x = lambda z: surf_x_any(BARRIER_Y, z, LIN) - 0.02
for side in (1, -1):
    net(NETS, lambda z, side=side: side * (abs(POST_X[0]) + 0.035), lambda z, side=side: side * wall_x(z),
        zn0, zn1, yn)
NETS.normal_update()
ob_nets = obj_from_bm('CP_BarrierNets', NETS, CP, MATS)
shade(ob_nets, 30)
STATIC.append(ob_nets.name)
# quick-release fittings where the nets attach (posts and sidewalls)
bm = bmesh.new()
for x in (POST_X[0] - 0.035, POST_X[1] + 0.035):
    for z in (zn0, 1.55, zn1):
        cylinder(bm, Vector((x, BARRIER_Y + 0.02, z)), Vector((x, BARRIER_Y + 0.05, z)), 0.012, 0.010, 10,
                 mat=MI['src_IN_Steel'])
for side in (1, -1):
    for z in (zn0, 1.55, zn1):
        xw = wall_x(z)
        cylinder(bm, Vector((side * xw, yn, z)), Vector((side * (xw + 0.026), yn, z)), 0.012, 0.012, 10,
                 mat=MI['src_IN_Steel'])
mk('CP_BarrierFittings', bm)
