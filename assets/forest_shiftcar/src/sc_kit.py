"""The previous shift's car (forest_shiftcar 2.3, built locally with tools/snow_style 28.10; docs/gdd/QUESTIONS_7.md §4 13):
a long 5-door 80s off-roader wagon in the station's faded green with a beige lower band, broken down before the checkpoint
with its hood up - the battery on its tray in the engine bay is the one the players carry to the booth's power cabinet
(Slot_ShiftCar_Battery). After the user's pick of the GPT references B (long wagon, roof basket with a ladder, black flares)
and C (rectangular lamps in a black grille, wide black side trim, two-tone) - refs/B_long_wagon.png, refs/C_soft_80s_suv.png.
No interior (user 28.10): dark glass over a black shell.
2.1 after the user's review of 2.0 («слишком узкий корпус, слишком высокая крыша, мультяшно; внутренняя часть колёс
просвечивается; слишком квадратная, острая»): 1.84 m wide (was 1.76), the roof at 1.60 m (was 1.78) with a raked windscreen,
the glass almost flush with the sides and leaning in, the sides bowed (tucked at the sill and the shoulder), round arches,
rounded corners, shoulders and roof edges; the tyres closed inside and every wheel face turned outward.
One root in its own frame (Blender: z up, the front -y, metres; origin on the ground between the axles; Unity (x, y, z) ->
(-x, z, -y), the front -> +Z)."""
import math
import bmesh
from mathutils import Vector, Matrix
import van3_mech as VM
import gen_kit as K
from gen_kit import kb, part, socket, face, KBS, Z_STEELBLK
from van2_kit import ZERO
import start_kit as SK
from start_kit import (Z_PAINT, Z_CBLACK, Z_UNDER, Z_TYRE, Z_RIM, Z_CHROME, Z_HEAD, Z_TAIL, Z_GRILLE, Z_PLATE, Z_RUBBER)
import sc_tex as ST

ROOTS = ['ShiftCar']
DISPLAY = {'ShiftCar': Vector((0.0, 0.0, 0.0))}
ROOT_OF = {}
BOXES = []
TAU = 2 * math.pi

CW, CH, CC = 0.92, 0.05, 0.16                         # half width, the shoulder's radius, the corners' radius (plan)
FRONT, REAR = -2.28, 2.22
YFA, YRA, TRK, RW, RWID, RA = -1.40, 1.24, 0.78, 0.40, 0.29, 0.50  # axles, half track, wheel r / width, arch radius
Z_SILL, Z_BAND, Z_MID, ZH0, ZH1, Z_BELT = 0.42, 0.62, 0.80, 1.00, 1.07, 1.10    # 2.3: belt +8 cm (windows -17%)
Y_WS, Y_RF, Y_RR, ZR, Z_ROOF = -0.74, -0.30, 2.08, 1.56, 1.60                    # 2.3: windscreen 16-18 cm back
WB, WR = 0.86, 0.75                                   # the glasshouse: half width at the belt / at the roof edge
PILLARS = {'B': (0.08, 0.18), 'C': (1.06, 1.16), 'D': (1.92, 2.08)}
HOOD_Y1 = Y_WS - 0.03
HOOD_UP = 55.0
FENDER_IN = 0.80
BAY_Z = 0.55
BATT_TRAY = (0.48, 0.76, -2.04, -1.74)
BATT_Z = 0.64
LEVELS = (Z_SILL, 0.60, Z_BAND, 0.68, Z_MID, 0.88)    # rows shared by the sides, corners, front and rear (no cracks)


def reg(name, atlas, root='ShiftCar'):
    ROOT_OF[name] = root
    return kb(name, atlas)


def z_top(y):
    """the hood line / belt line (the top of the body sides)"""
    if y <= Y_WS:
        return ZH0 + (ZH1 - ZH0) * (y - FRONT) / (Y_WS - FRONT)
    return ZH1 + (Z_BELT - ZH1) * min(1.0, (y - Y_WS) / (REAR - Y_WS))


def xs(z, top):
    """the bowed side: tucked under at the sill, full at the band and the middle, a little in at the shoulder"""
    if z <= Z_BAND:
        return CW - 0.04 + 0.04 * (z - Z_SILL) / (Z_BAND - Z_SILL)
    if z <= Z_MID:
        return CW
    return CW - 0.02 * (z - Z_MID) / max(top - Z_MID, 1e-3)


def rows(bottom, top):
    return [bottom] + [l for l in LEVELS if bottom + 1e-4 < l < top - 1e-4] + [top]


def arch(yc, grow=0.0):
    """the arch edge (y, z) from its front foot over the top to its rear foot, where it meets the sill"""
    r = RA * (1 + grow)
    s = math.degrees(math.asin(max(-1.0, min(1.0, (Z_SILL - RW) / r))))
    pts = []
    for i in range(13):
        a = math.radians(180.0 - s + (2 * s - 180.0) * i / 12)
        pts.append((yc + r * math.cos(a), RW + r * math.sin(a)))
    return pts


def column(k, s, ya, za, yb, zb, ta, tb, zone=Z_PAINT):
    """one vertical strip of the side between y = ya and yb: from the bottom edge up to the top, cut at the shared rows"""
    la, lb = rows(za, ta), rows(zb, tb)
    lv = sorted(set([l for l in LEVELS] + [za, zb, ta, tb]))
    for z0, z1 in zip(lv[:-1], lv[1:]):
        qa0, qa1 = min(max(z0, za), ta), min(max(z1, za), ta)
        qb0, qb1 = min(max(z0, zb), tb), min(max(z1, zb), tb)
        pts = [(ya, qa0), (yb, qb0), (yb, qb1), (ya, qa1)]
        q = []
        for y, z in pts:
            p = (s * xs(z, ta if y == ya else tb), y, z)
            if not q or (Vector(p) - Vector(q[-1])).length > 1e-5:
                q.append(p)
        if len(q) > 2 and (Vector(q[0]) - Vector(q[-1])).length < 1e-5:
            q.pop()
        if len(q) >= 3:
            face(k, q, zone, (s, 0, 0))


def corner(k, s, end):
    """the rounded vertical corner from the side (at y = end + CC*d) to the face (y = end): three segments over the rows"""
    d = 1 if end == FRONT else -1
    yc = end + d * CC
    top = z_top(yc) - CH
    lv = rows(Z_SILL, top)
    n = 3
    for z0, z1 in zip(lv[:-1], lv[1:]):
        for i in range(n):
            ring = []
            for j in (i, i + 1):
                th = math.radians(90.0 * j / n)
                for z in (z0, z1):
                    X = xs(z, top)
                    ring.append((s * (X - CC + CC * math.cos(th)), yc - d * CC * math.sin(th), z))
            a0, a1, b0, b1 = ring
            mid = Vector(a0) + Vector(b1)
            out = Vector((mid.x / 2 - s * (CW - CC), mid.y / 2 - yc, 0)).normalized()
            face(k, [a0, b0, b1, a1], Z_PAINT, out)
    # the cap over the corner up to the shoulder / hood line
    arc = []
    for j in range(n + 1):
        th = math.radians(90.0 * j / n)
        X = xs(top, top)
        arc.append((s * (X - CC + CC * math.cos(th)), yc - d * CC * math.sin(th), top))
    tip = (s * (CW - 0.02 - CH), yc, z_top(yc))
    for p, q in zip(arc[:-1], arc[1:]):
        face(k, [p, q, tip], Z_PAINT, (0, -d * 0.3, 1))
    return [a for a in arc]


def flip_to(k, faces, want):
    """turn every face of a lathe piece so that it faces `want(face_centre)`"""
    for f in faces:
        f.normal_update()
        if f.normal.dot(want(f.calc_center_median())) < 0:
            f.normal_flip()


def wheel(k, c, side, r=RW, w=RWID, seg=16):
    """an all-terrain tyre (its tread zig-zags in silhouette), closed inside, on a dished steel wheel; every face outward"""
    bm = k.bm
    ax = Vector((side, 0, 0))
    hw = w / 2
    bm.faces.ensure_lookup_table()
    f0 = len(bm.faces)
    prof = [(-hw, r * 0.58), (-hw * 1.08, r * 0.74), (-hw * 1.04, r * 0.90), (-hw * 0.78, r), (hw * 0.78, r), (hw * 1.04, r * 0.90),
            (hw * 1.08, r * 0.74), (hw, r * 0.58)]
    n0 = len(bm.verts)
    k.lathe(c, ax, prof, Z_TYRE, seg, cap0=False, cap1=False)
    bm.verts.ensure_lookup_table()
    for ring in (3, 4):
        for i in range(1, seg, 2):
            v = bm.verts[n0 + ring * seg + i]
            dv = v.co - c
            along = dv.dot(ax)
            v.co = c + ax * along + (dv - ax * along) * 0.955
    bm.faces.ensure_lookup_table()
    flip_to(k, bm.faces[f0:], lambda p: p - c)                                       # the tyre: away from the wheel's centre
    f1 = len(bm.faces)
    k.lathe(c, ax, [(-hw, r * 0.58), (hw, r * 0.58)], Z_TYRE, seg, cap0=False, cap1=False)
    bm.faces.ensure_lookup_table()
    flip_to(k, bm.faces[f1:], lambda p: -((p - c) - ax * (p - c).dot(ax)))         # its bead: toward the axle
    f2 = len(bm.faces)
    o = c + ax * (hw * 0.70)
    k.lathe(o, ax, [(0.0, r * 0.58), (-0.02, r * 0.52), (-0.05, r * 0.40), (-0.05, r * 0.24), (-0.02, r * 0.20), (0.0, r * 0.12),
                    (0.0, 0.0)], Z_RIM, seg // 2, cap0=False, cap1=False)
    bm.faces.ensure_lookup_table()
    flip_to(k, bm.faces[f2:], lambda p: ax)                                           # the wheel's face: outward
    f3 = len(bm.faces)
    k.lathe(c - ax * (hw * 0.70), -ax, [(0.0, r * 0.58), (0.03, r * 0.30), (0.04, 0.0)], Z_UNDER, seg // 2, cap0=False, cap1=False)
    bm.faces.ensure_lookup_table()
    flip_to(k, bm.faces[f3:], lambda p: -ax)                                          # the back: inward (to the car)


def body():
    k = reg('ShiftCar', 'ShiftCar')
    bottom = [(FRONT + CC, Z_SILL)] + arch(YFA) + arch(YRA) + [(REAR - CC, Z_SILL)]
    for s in (-1, 1):
        for (ya, za), (yb, zb) in zip(bottom[:-1], bottom[1:]):
            if yb - ya > 1e-6:
                column(k, s, ya, za, yb, zb, z_top(ya) - CH, z_top(yb) - CH)
        # the rounded shoulder (two segments) along the whole side, then the fender tops and the belt behind the windscreen
        ys = [FRONT + CC, (FRONT + CC + HOOD_Y1) / 2, HOOD_Y1, Y_WS, 0.0, 1.2, REAR - CC]
        for ya, yb in zip(ys[:-1], ys[1:]):
            pa = [Vector((s * (CW - 0.02 - CH + CH * math.cos(math.radians(t))), ya, z_top(ya) - CH + CH * math.sin(math.radians(t))))
                  for t in (0, 45, 90)]
            pb = [Vector((s * (CW - 0.02 - CH + CH * math.cos(math.radians(t))), yb, z_top(yb) - CH + CH * math.sin(math.radians(t))))
                  for t in (0, 45, 90)]
            for i in range(2):
                face(k, [pa[i], pb[i], pb[i + 1], pa[i + 1]], Z_PAINT, (s, 0, 1))
        X = CW - 0.02 - CH
        face(k, [(s * X, FRONT + CC, z_top(FRONT + CC)), (s * X, HOOD_Y1, z_top(HOOD_Y1)),
                 (s * FENDER_IN, HOOD_Y1, z_top(HOOD_Y1)), (s * FENDER_IN, FRONT + CC, z_top(FRONT + CC))], Z_PAINT, (0, 0, 1))
        face(k, [(s * X, Y_WS, z_top(Y_WS)), (s * X, REAR - CC, z_top(REAR - CC)),
                 (s * (WB - 0.02), REAR - CC, z_top(REAR - CC)), (s * (WB - 0.02), Y_WS, z_top(Y_WS))], Z_PAINT, (0, 0, 1))
        face(k, [(s * X, HOOD_Y1, z_top(HOOD_Y1)), (s * X, Y_WS, z_top(Y_WS)), (s * FENDER_IN, Y_WS, z_top(Y_WS)),
                 (s * FENDER_IN, HOOD_Y1, z_top(HOOD_Y1))], Z_PAINT, (0, 0, 1))
        # the bay's side walls, the wheel wells and their inner walls
        face(k, [(s * FENDER_IN, FRONT + CC, z_top(FRONT + CC)), (s * FENDER_IN, HOOD_Y1, z_top(HOOD_Y1)),
                 (s * FENDER_IN, HOOD_Y1, BAY_Z), (s * FENDER_IN, FRONT + CC, BAY_Z)], Z_UNDER, (-s, 0, 0))
        for yc in (YFA, YRA):
            pts = arch(yc)
            for (ya, za), (yb, zb) in zip(pts[:-1], pts[1:]):
                n = Vector((0, yc - (ya + yb) / 2, RW - (za + zb) / 2)).normalized()
                xa, xb = s * xs(za, 1.0), s * xs(zb, 1.0)
                face(k, [(xa, ya, za), (xb, yb, zb), (s * 0.56, yb, zb), (s * 0.56, ya, za)], Z_UNDER, n)
            face(k, [(s * 0.56, y, z) for y, z in pts], Z_UNDER, (s, 0, 0))
            fl = arch(yc, 0.07)                                       # the black flare round the arch
            k.strip([Vector((s * (CW + 0.025), y, max(z, Z_SILL - 0.03))) for y, z in fl], Vector((s, 0, 0)), 0.10, 0.05, Z_CBLACK)
        # the wide black body-side trim at the band's top, between the arches
        for ya, yb in ((FRONT + CC, YFA - RA - 0.06), (YFA + RA + 0.06, YRA - RA - 0.06), (YRA + RA + 0.06, REAR - CC)):
            k.box(*sorted((s * (CW - 0.005), s * (CW + 0.022))), ya, yb, Z_BAND - 0.03, Z_BAND + 0.05, Z_CBLACK)
        corner(k, s, FRONT)
        corner(k, s, REAR)
    # front: the face (its outer edge follows the bowed side), lamps, grille, indicators; the rounded nose up to the hood line
    zs = rows(Z_SILL, ZH0 - CH)
    for j in range(len(zs) - 1):
        za, zb = zs[j], zs[j + 1]
        zm = (za + zb) / 2
        for s in (-1, 1):
            xo_a, xo_b = xs(za, ZH0 - CH) - CC, xs(zb, ZH0 - CH) - CC
            cells = [(0.0, 0.40), (0.40, 0.44), (0.44, 0.70), (0.70, None)]
            for x0, x1 in cells:
                xa0, xa1 = x0, (x1 if x1 is not None else xo_a)
                xb0, xb1 = x0, (x1 if x1 is not None else xo_b)
                xm = (x0 + (x1 if x1 is not None else xo_a)) / 2
                zone = Z_PAINT
                if 0.44 <= xm <= 0.70 and 0.68 <= zm <= 0.88:
                    zone = Z_HEAD
                elif 0.44 <= xm <= 0.70 and 0.60 <= zm <= 0.68:
                    zone = Z_TAIL
                elif xm < 0.40 and 0.60 <= zm <= 0.88:
                    zone = Z_GRILLE
                face(k, [(s * xa0, FRONT, za), (s * xa1, FRONT, za), (s * xb1, FRONT, zb), (s * xb0, FRONT, zb)], zone, (0, -1, 0))
    # the nose's rounded top edge: front face top -> hood line (two segments)
    xo = xs(ZH0 - CH, ZH0 - CH) - CC
    for t0, t1 in ((0, 45), (45, 90)):
        def nose(t, x):
            a = math.radians(t)
            return (x, FRONT + CC * (1 - math.cos(a)) * 0.5, ZH0 - CH + (z_top(FRONT + CC * 0.5) - (ZH0 - CH)) * math.sin(a))
        face(k, [nose(t0, -xo), nose(t0, xo), nose(t1, xo), nose(t1, -xo)], Z_PAINT, (0, -1, 1))
    zn = z_top(FRONT + CC * 0.5)
    face(k, [(-xo, FRONT + CC * 0.5, zn), (xo, FRONT + CC * 0.5, zn), (FENDER_IN, FRONT + CC, z_top(FRONT + CC)),
             (-FENDER_IN, FRONT + CC, z_top(FRONT + CC))], Z_PAINT, (0, 0, 1))
    for s in (-1, 1):                                                  # fill between the nose and the corner caps
        face(k, [(s * xo, FRONT + CC * 0.5, zn), (s * FENDER_IN, FRONT + CC, z_top(FRONT + CC)),
                 (s * (CW - 0.02 - CH), FRONT + CC, z_top(FRONT + CC)), (s * xo, FRONT, ZH0 - CH)], Z_PAINT, (0, -0.3, 1))
    for s in (-1, 1):                                                  # the lamps' chrome bezels
        k.strip([Vector((s * 0.43, FRONT - 0.006, 0.67)), Vector((s * 0.71, FRONT - 0.006, 0.67)), Vector((s * 0.71, FRONT - 0.006, 0.89)),
                 Vector((s * 0.43, FRONT - 0.006, 0.89)), Vector((s * 0.43, FRONT - 0.006, 0.67))], Vector((0, -1, 0)), 0.014, 0.012,
                Z_CHROME, caps=False)
    # bumpers: a chamfered black beam wrapping round the corners
    for yy, d in ((FRONT, -1), (REAR, 1)):
        VM.rbox(k, (0.0, yy + d * 0.04, 0.50), (1.70, 0.13, 0.17), Z_CBLACK, r=0.03, ch=0.015, axis='x')
        for s in (-1, 1):
            VM.obox(k, Vector((s * 0.89, yy - d * 0.06, 0.50)), (0.10, 0.26, 0.15), Z_CBLACK,
                    Matrix.Rotation(math.radians(s * d * 30), 3, 'Z'))
    for xb in (-0.30, 0.30):                                          # tow hooks
        k.box(xb - 0.03, xb + 0.03, FRONT - 0.15, FRONT - 0.10, 0.42, 0.48, Z_STEELBLK)
    # the engine bay
    face(k, [(-FENDER_IN, FRONT + CC, BAY_Z), (FENDER_IN, FRONT + CC, BAY_Z), (FENDER_IN, HOOD_Y1, BAY_Z), (-FENDER_IN, HOOD_Y1, BAY_Z)],
         Z_UNDER, (0, 0, 1))
    face(k, [(-FENDER_IN, HOOD_Y1, BAY_Z), (FENDER_IN, HOOD_Y1, BAY_Z), (FENDER_IN, HOOD_Y1, ZH1), (-FENDER_IN, HOOD_Y1, ZH1)], Z_UNDER,
         (0, -1, 0))
    face(k, [(-FENDER_IN, HOOD_Y1, ZH1), (FENDER_IN, HOOD_Y1, ZH1), (FENDER_IN, Y_WS, ZH1 + 0.01), (-FENDER_IN, Y_WS, ZH1 + 0.01)], Z_CBLACK,
         (0, 0, 1))
    face(k, [(-FENDER_IN, FRONT + CC, BAY_Z), (FENDER_IN, FRONT + CC, BAY_Z), (FENDER_IN, FRONT + CC, z_top(FRONT + CC)),
             (-FENDER_IN, FRONT + CC, z_top(FRONT + CC))], Z_UNDER, (0, 1, 0))
    k.box(-0.54, 0.54, FRONT + CC, FRONT + CC + 0.07, 0.62, 0.90, Z_GRILLE)
    VM.rbox(k, (-0.06, -1.42, 0.76), (0.56, 0.72, 0.40), Z_STEELBLK, r=0.03, ch=0.015, axis='y')
    VM.rbox(k, (-0.06, -1.42, 0.98), (0.30, 0.64, 0.06), Z_CBLACK, r=0.02, ch=0.01, axis='y')
    k.cyl(Vector((-0.42, -1.26, 0.92)), Vector((-0.42, -1.26, 0.98)), 0.15, Z_CBLACK, 10)
    k.cyl(Vector((-0.42, -1.26, 0.86)), Vector((-0.42, -1.26, 0.92)), 0.05, Z_CBLACK, 6)
    k.box(0.50, 0.68, -1.28, -1.10, BAY_Z, 0.84, Z_RUBBER)
    x0, x1, y0, y1 = BATT_TRAY
    k.box(x0, x1, y0, y1, BAY_Z, BATT_Z, Z_CBLACK)
    k.tube([Vector((x0 + 0.04, y1 - 0.02, BATT_Z + 0.20)), Vector((0.38, -1.58, 0.90)), Vector((0.24, -1.42, 0.98))], 0.012, Z_CBLACK, 5,
           caps=False)
    k.tube([Vector((x1 - 0.05, y1 - 0.02, BATT_Z + 0.20)), Vector((0.66, -1.55, 0.72)), Vector((0.52, -1.45, 0.62))], 0.012, Z_TAIL, 5,
           caps=False)
    # rear: the tailgate's lower face (its edge follows the bowed side), tail lamps, plate; the rounded top edge; the ladder
    zs = rows(Z_SILL, Z_BELT - CH)
    for j in range(len(zs) - 1):
        za, zb = zs[j], zs[j + 1]
        zm = (za + zb) / 2
        for s in (-1, 1):
            xo_a, xo_b = xs(za, Z_BELT - CH) - CC, xs(zb, Z_BELT - CH) - CC
            for x0, x1 in ((0.0, 0.26), (0.26, 0.62), (0.62, None)):
                xa1, xb1 = (x1 if x1 is not None else xo_a), (x1 if x1 is not None else xo_b)
                zone = Z_PAINT
                if x1 is None and 0.68 <= zm <= 0.98:
                    zone = Z_TAIL
                elif x1 == 0.26 and 0.62 <= zm <= 0.80:
                    zone = Z_PLATE
                face(k, [(s * x0, REAR, za), (s * xa1, REAR, za), (s * xb1, REAR, zb), (s * x0, REAR, zb)], zone, (0, 1, 0))
    xo = xs(Z_BELT - CH, Z_BELT - CH) - CC
    face(k, [(-xo, REAR, Z_BELT - CH), (xo, REAR, Z_BELT - CH), (FENDER_IN, REAR - CC, z_top(REAR - CC)),
             (-FENDER_IN, REAR - CC, z_top(REAR - CC))], Z_PAINT, (0, 1, 1))
    for s in (-1, 1):
        face(k, [(s * xo, REAR, Z_BELT - CH), (s * FENDER_IN, REAR - CC, z_top(REAR - CC)),
                 (s * (CW - 0.02 - CH), REAR - CC, z_top(REAR - CC))], Z_PAINT, (0, 0.3, 1))
    lx0, lx1, ly = 0.38, 0.60, REAR + 0.06
    for lx in (lx0, lx1):
        k.cyl(Vector((lx, ly, 0.66)), Vector((lx, ly, Z_ROOF + 0.04)), 0.014, Z_CBLACK, 6)
        k.cyl(Vector((lx, ly, Z_ROOF + 0.04)), Vector((lx, Y_RR - 0.08, Z_ROOF + 0.10)), 0.014, Z_CBLACK, 6)
        k.box(lx - 0.025, lx + 0.025, REAR, ly, 0.74, 0.77, Z_CBLACK)
        k.box(lx - 0.025, lx + 0.025, REAR, ly, 1.36, 1.39, Z_CBLACK)
    zz = 0.76
    while zz < Z_ROOF - 0.05:
        k.cyl(Vector((lx0, ly, zz)), Vector((lx1, ly, zz)), 0.011, Z_CBLACK, 5)
        zz += 0.22
    # the floor pan, the axles and differentials, the wheels
    face(k, [(-(CW - 0.04), FRONT + CC, Z_SILL), (CW - 0.04, FRONT + CC, Z_SILL), (CW - 0.04, REAR - CC, Z_SILL),
             (-(CW - 0.04), REAR - CC, Z_SILL)], Z_UNDER, (0, 0, -1))
    for yc in (YFA, YRA):
        k.cyl(Vector((-TRK + 0.12, yc, RW)), Vector((TRK - 0.12, yc, RW)), 0.07, Z_UNDER, 6)
        k.box(-0.20, 0.20, yc - 0.12, yc + 0.12, RW - 0.10, RW + 0.10, Z_UNDER)
    SK.triangulate_ngons(k)
    for yc in (YFA, YRA):
        for s in (-1, 1):
            wheel(k, Vector((s * TRK, yc, RW)), s)
    return k


def glasshouse():
    k = KBS['ShiftCar']
    g = reg('SC_Glass', 'glass')
    # the roof with rounded side edges and drip rails; front and rear edges chamfered
    rr = 0.05
    for s in (-1, 1):
        prev = None
        for t in (0, 45, 90):
            a = math.radians(t)
            x, z = s * (WR - rr + rr * math.cos(a)), ZR + (Z_ROOF - ZR) * math.sin(a)
            cur = (x, z)
            if prev:
                face(k, [(prev[0], Y_RF, prev[1]), (prev[0], Y_RR, prev[1]), (cur[0], Y_RR, cur[1]), (cur[0], Y_RF, cur[1])], Z_PAINT,
                     (s, 0, 1))
            prev = cur
        k.strip([Vector((s * (WR + 0.008), Y_RF + 0.04, ZR - 0.01)), Vector((s * (WR + 0.008), Y_RR - 0.02, ZR - 0.01))],
                Vector((0, 0, 1)), 0.016, 0.016, Z_CBLACK)
    xr = WR - rr
    face(k, [(-xr, Y_RF + 0.03, Z_ROOF), (xr, Y_RF + 0.03, Z_ROOF), (xr, Y_RR - 0.02, Z_ROOF), (-xr, Y_RR - 0.02, Z_ROOF)], Z_PAINT,
         (0, 0, 1))
    for yy, ye, d in ((Y_RF, Y_RF + 0.03, -1), (Y_RR, Y_RR - 0.02, 1)):
        face(k, [(-WR, yy, ZR), (WR, yy, ZR), (xr, ye, Z_ROOF), (-xr, ye, Z_ROOF)], Z_PAINT, (0, d, 1))
        for s in (-1, 1):
            face(k, [(s * WR, yy, ZR), (s * xr, ye, Z_ROOF), (s * WR, ye, ZR + (Z_ROOF - ZR) * 0.7)], Z_PAINT, (s, d, 1))
    xi, y0, y1, z0, z1 = WR - 0.08, Y_WS + 0.12, REAR - CC - 0.05, 0.52, ZR - 0.05
    shell = [([(-xi, y0, z0), (-xi, y1, z0), (-xi, y1, z1), (-xi, y0, z1)], (1, 0, 0)),
             ([(xi, y0, z0), (xi, y1, z0), (xi, y1, z1), (xi, y0, z1)], (-1, 0, 0)),
             ([(-xi, y0, z1), (xi, y0, z1), (xi, y1, z1), (-xi, y1, z1)], (0, 0, -1)),
             ([(-xi, y0, z0), (xi, y0, z0), (xi, y0, z1), (-xi, y0, z1)], (0, 1, 0)),
             ([(-xi, y1, z0), (xi, y1, z0), (xi, y1, z1), (-xi, y1, z1)], (0, -1, 0)),
             ([(-xi, y0, z0), (xi, y0, z0), (xi, y1, z0), (-xi, y1, z0)], (0, 0, 1))]
    for q, n in shell:
        face(k, q, Z_UNDER, n)
    # the roof basket (reference B), low on the roof
    bx, by0, by1, bz = 0.66, Y_RF + 0.18, Y_RR - 0.08, Z_ROOF + 0.10
    rim = [Vector((-bx, by0, bz)), Vector((bx, by0, bz)), Vector((bx, by1, bz)), Vector((-bx, by1, bz)), Vector((-bx, by0, bz))]
    k.tube(rim, 0.015, Z_CBLACK, 6, caps=False)
    n = 6
    for i in range(n + 1):
        yy = by0 + (by1 - by0) * i / n
        for s in (-1, 1):
            k.cyl(Vector((s * bx, yy, Z_ROOF)), Vector((s * bx, yy, bz)), 0.011, Z_CBLACK, 5)
        if 0 < i < n:
            k.cyl(Vector((-bx, yy, bz - 0.05)), Vector((bx, yy, bz - 0.05)), 0.010, Z_CBLACK, 5)
    for s in (-1, 1):
        k.cyl(Vector((s * bx, by0, bz - 0.05)), Vector((s * bx, by1, bz - 0.05)), 0.010, Z_CBLACK, 5)
    k.cyl(Vector((-bx, by0 - 0.02, bz + 0.06)), Vector((bx, by0 - 0.02, bz + 0.06)), 0.013, Z_CBLACK, 6)
    for xx in (-bx, -0.22, 0.22, bx):
        k.cyl(Vector((xx, by0, bz)), Vector((xx, by0 - 0.02, bz + 0.06)), 0.010, Z_CBLACK, 5)

    def P(s, y, t, inset=0.0):
        x, z = s * (WB + (WR - WB) * t), Z_BELT + (ZR - Z_BELT) * t
        return Vector((x - s * inset, y, z))

    for s in (-1, 1):
        a0, a1 = P(s, Y_WS, 0.0), P(s, Y_RF, 1.0)
        k.strip([a0 + Vector((0, 0.03, 0)), a1 + Vector((0, 0.03, -0.01))], Vector((s, 0, 0.35)), 0.08, 0.05, Z_PAINT)
        for name, (ya, yb) in PILLARS.items():
            q = [P(s, ya, 0.0), P(s, yb, 0.0), P(s, yb, 1.0), P(s, ya, 1.0)]
            face(k, q, Z_PAINT if name == 'D' else Z_CBLACK, (s, 0, 0.4))
        k.box(*sorted((s * (WB - 0.01), s * (WB + 0.012))), Y_WS, PILLARS['D'][1], Z_BELT - 0.012, Z_BELT + 0.012, Z_RUBBER)
        spans = [(Y_WS + 0.10, PILLARS['B'][0]), (PILLARS['B'][1], PILLARS['C'][0]), (PILLARS['C'][1], PILLARS['D'][0])]
        for i, (ya, yb) in enumerate(spans):
            if i == 0:
                pts = [P(s, ya, 0.02, 0.012), P(s, yb, 0.02, 0.012), P(s, yb, 0.98, 0.012), P(s, Y_RF + 0.06, 0.98, 0.012)]
            else:
                pts = [P(s, ya, 0.02, 0.012), P(s, yb, 0.02, 0.012), P(s, yb, 0.98, 0.012), P(s, ya, 0.98, 0.012)]
            face(g, pts, ZERO, (s, 0, 0.4))
            k.strip(pts + [pts[0]], Vector((s, 0, 0.4)), 0.022, 0.012, Z_RUBBER, caps=False)
        k.box(*sorted((s * (CW - 0.02), s * (CW + 0.05))), Y_WS + 0.10, Y_WS + 0.16, Z_BELT - 0.06, Z_BELT - 0.02, Z_CBLACK)
        VM.rbox(k, (s * (CW + 0.11), Y_WS + 0.13, Z_BELT + 0.05), (0.16, 0.05, 0.18), Z_CBLACK, r=0.03, ch=0.01, axis='y')
        for yh in (PILLARS['B'][0] - 0.10, PILLARS['C'][0] - 0.10):
            k.box(*sorted((s * (CW - 0.02), s * (CW + 0.012))), yh - 0.08, yh + 0.08, Z_BELT - 0.12, Z_BELT - 0.09, Z_CBLACK)
    ws = [Vector((-WB + 0.06, Y_WS + 0.05, Z_BELT + 0.01)), Vector((WB - 0.06, Y_WS + 0.05, Z_BELT + 0.01)),
          Vector((WR - 0.06, Y_RF + 0.02, ZR - 0.01)), Vector((-WR + 0.06, Y_RF + 0.02, ZR - 0.01))]
    face(g, ws, ZERO, (0, -0.6, 0.8))
    k.strip(ws + [ws[0]], Vector((0, -0.6, 0.8)), 0.035, 0.015, Z_RUBBER, caps=False)
    for xw in (-0.48, 0.04):
        k.strip([Vector((xw, Y_WS + 0.07, Z_BELT + 0.03)), Vector((xw + 0.44, Y_WS + 0.14, Z_BELT + 0.12))], Vector((0, -0.6, 0.8)),
                0.02, 0.012, Z_CBLACK)
    rw = [Vector((WR - 0.06, Y_RR + 0.015, ZR - 0.04)), Vector((-WR + 0.06, Y_RR + 0.015, ZR - 0.04)),
          Vector((-WB + 0.10, REAR - CC, z_top(REAR - CC) + 0.02)), Vector((WB - 0.10, REAR - CC, z_top(REAR - CC) + 0.02))]
    face(g, rw, ZERO, (0, 1, 0.2))
    k.strip(rw + [rw[0]], Vector((0, 1, 0.2)), 0.03, 0.015, Z_RUBBER, caps=False)
    for s in (-1, 1):
        face(k, [P(s, PILLARS['D'][1], 0.0), Vector((s * (WB - 0.10), REAR - CC, z_top(REAR - CC) + 0.02)),
                 Vector((s * (WR - 0.06), Y_RR + 0.015, ZR - 0.04)), P(s, PILLARS['D'][1], 1.0)], Z_PAINT, (s, 1, 0.2))
    # the station's lettering on both front doors (cut-out letters, panel atlas)
    p = reg('SC_Letters', 'panel')
    w, h = ST.size_m('door')
    w, h = w * 0.9, h * 0.9
    u0, v0, u1, v1 = ST.uv('door')
    yc, zc = -0.32, 0.82
    z0, z1 = zc - h / 2, zc + h / 2

    def door_x(z):                                                   # the door's surface with the crease (refine), 1.5 mm out
        top = z_top(yc) - CH
        bump = 0.014 * max(0.0, 1 - abs(z - Z_MID) / (0.12 if z < Z_MID else 0.08))
        return xs(z, top) + bump + 0.0015

    for s in (-1, 1):
        ya, yb = (yc - w / 2, yc + w / 2) if s > 0 else (yc + w / 2, yc - w / 2)     # u runs to the reader's right
        for za, zb in ((z0, Z_MID), (Z_MID, z1)):
            va, vb = v0 + (v1 - v0) * (za - z0) / h, v0 + (v1 - v0) * (zb - z0) / h
            pts = [(s * door_x(za), ya, za), (s * door_x(za), yb, za), (s * door_x(zb), yb, zb), (s * door_x(zb), ya, zb)]
            face(p, pts, ZERO, (s, 0, 0), [(u0, va), (u1, va), (u1, vb), (u0, vb)])
    part('SC_Glass', 'static', (0, 0.6, 1.30), parent='ShiftCar', note='all windows (dark dirty glass, a black shell behind, no interior)')
    part('SC_Letters', 'static', (0, -0.32, 0.82), parent='ShiftCar', note='RADIOOBSERVATORIUM / HOHENMOOS on both front doors')


def hood():
    """the hood, open: a full-width panel with its front edge turned down, hinged at the windscreen end, on its stay"""
    h = reg('SC_Hood', 'ShiftCar')
    y0, y1, x = FRONT + CC * 0.5, HOOD_Y1, FENDER_IN + 0.02
    zt0, zt1 = z_top(y0) + 0.01, z_top(y1) + 0.01
    face(h, [(-x, y0, zt0), (x, y0, zt0), (x, y1, zt1), (-x, y1, zt1)], Z_PAINT, (0, 0, 1))
    face(h, [(-x, y0, zt0 - 0.03), (x, y0, zt0 - 0.03), (x, y1, zt1 - 0.03), (-x, y1, zt1 - 0.03)], Z_UNDER, (0, 0, -1))
    face(h, [(-x, y0, zt0 - 0.05), (x, y0, zt0 - 0.05), (x, y0, zt0), (-x, y0, zt0)], Z_PAINT, (0, -1, 0))
    for s in (-1, 1):
        face(h, [(s * x, y0, zt0 - 0.05), (s * x, y1, zt1 - 0.03), (s * x, y1, zt1), (s * x, y0, zt0)], Z_PAINT, (s, 0, 0))
    for xr in (-0.30, 0.30):
        h.box(xr - 0.03, xr + 0.03, y0 + 0.05, y1 - 0.05, zt0 - 0.05, zt0 - 0.03, Z_UNDER)
    piv = Vector((0.0, y1, zt1))
    R = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(-HOOD_UP), 4, 'X') @ Matrix.Translation(-piv)
    K.transform_kb(h, R)
    tip = R @ Vector((-0.64, y0 + 0.20, zt0 - 0.03))
    KBS['ShiftCar'].cyl(Vector((-0.64, y0 + 0.20, BAY_Z + 0.30)), tip, 0.008, Z_CHROME, 4)
    part('SC_Hood', 'static', tuple(piv), parent='ShiftCar', note=f'the hood, open {HOOD_UP:.0f} deg (the car broke down; static)')


def refine():
    """shaped in the live Blender (28.10, user «делай» to working there): the roof crowned 3.5 cm, a crease along the sides at
    the middle row (1.4 cm out), the headlamps, grille and tail lamps set into the body (their inset walls black)"""
    k = KBS['ShiftCar']
    bm = k.bm
    zl = k.zl
    bm.faces.ensure_lookup_table()
    bm.normal_update()

    def roof():
        return [f for f in bm.faces if f.normal.z > 0.99 and all(abs(v.co.z - Z_ROOF) < 0.002 and abs(v.co.x) < WR - 0.04
                                                                    for v in f.verts)]
    print('refine: roof faces', len(roof()))
    for xx in (0.0, -0.36, 0.36):
        g = set()
        for f in roof():
            g |= set(f.verts) | set(f.edges) | {f}
        bmesh.ops.bisect_plane(bm, geom=list(g), plane_co=(xx, 0, 0), plane_no=(1, 0, 0))
    for v in {v for f in roof() for v in f.verts}:
        t = min(1.0, abs(v.co.x) / (WR - 0.05))
        v.co.z += 0.035 * (1 - t * t)
    for v in bm.verts:
        if abs(v.co.z - Z_MID) < 1e-4 and abs(v.co.x) > CW - 0.02:
            v.co.x += math.copysign(0.014, v.co.x)
    bm.faces.ensure_lookup_table()

    def on(y0, test):
        return [f for f in bm.faces if all(abs(v.co.y - y0) < 1e-4 for v in f.verts) and test(f.calc_center_median())]
    groups = [(on(FRONT, lambda c: 0.44 < c.x < 0.70 and 0.68 < c.z < 0.88), 0.025),
              (on(FRONT, lambda c: -0.70 < c.x < -0.44 and 0.68 < c.z < 0.88), 0.025),
              (on(FRONT, lambda c: abs(c.x) < 0.40 and 0.60 < c.z < 0.88), 0.035),
              (on(REAR, lambda c: c.x > 0.62 and 0.68 < c.z < 0.98), -0.015),
              (on(REAR, lambda c: c.x < -0.62 and 0.68 < c.z < 0.98), -0.015)]
    print('refine: lamp / grille faces', [len(g[0]) for g in groups])
    for faces, depth in groups:
        if not faces:
            continue
        r = bmesh.ops.inset_region(bm, faces=faces, thickness=0.012, depth=0.0, use_even_offset=True)
        for f in r['faces']:
            f[zl] = Z_CBLACK
        for v in {v for f in faces for v in f.verts}:
            v.co.y += depth
    bm.normal_update()


def build_car():
    body()
    glasshouse()
    hood()
    refine()
    x0, x1, y0, y1 = BATT_TRAY
    socket('Slot_ShiftCar_Battery', ((x0 + x1) / 2, (y0 + y1) / 2, BATT_Z), 'stow', parent='ShiftCar',
           note='the battery\'s place on its tray in the engine bay (the item\'s origin, upright, its front -y): the battery the '
                'players carry to the checkpoint\'s power cabinet (QUESTIONS_7 §4 13)')
    part('ShiftCar', 'static', (0, 0, 0), note='the previous shift\'s car (root): origin = the ground between the axles; the front -y')
    # the bay stays open from above (the players reach in for the battery): the cabin, a low nose under the bay's floor, the
    # fenders' walls and the front wall round it
    zt = z_top(FRONT + CC)
    BOXES.extend([('Car_Cabin', 'ShiftCar', (-0.96, 0.96, HOOD_Y1, REAR + 0.10, 0.30, Z_ROOF + 0.12), None),
                  ('Car_Nose', 'ShiftCar', (-0.96, 0.96, FRONT - 0.10, HOOD_Y1, 0.30, BAY_Z), None),
                  ('Car_FenderL', 'ShiftCar', (FENDER_IN, CW, FRONT, HOOD_Y1, BAY_Z, zt), None),
                  ('Car_FenderR', 'ShiftCar', (-CW, -FENDER_IN, FRONT, HOOD_Y1, BAY_Z, zt), None),
                  ('Car_Front', 'ShiftCar', (-FENDER_IN, FENDER_IN, FRONT - 0.10, FRONT + CC, BAY_Z, zt), None)])
