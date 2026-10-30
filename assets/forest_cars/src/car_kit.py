"""The forest's two abandoned passenger cars (forest_cars 1.2, built locally with tools/snow_style 28.10), the way the previous
shift's car was rebuilt (forest_shiftcar 2.3: user «в такое же состояние нужно привести остальные не юзабельные машины»):
  StartCar  by the start post: a mid-80s estate, oxblood gone chalky, the rear right tyre flat (the body leans to it), the driver's
            door open 70 deg (IX_CarDoor), roof rails, needles and leaves; a simple interior (seen through the open door)
  WreckCar  before the checkpoint: a late-70s three-box saloon, faded blue and rusted through, chrome grille and bumpers, the front
            right wheel gone (it lies on the brake drum), the rear right tyre flat, the boot lid ajar (IX_WreckCarBoot), the
            windscreen cracked (panel decal), a crust of snow on top
The user's picks of the GPT references (28.10): start_B (mid-80s estate) and wreck_A (late-70s saloon) in
tools/snow_style/work/forest_cars_refs. The shape language of ShiftCar 2.3: bowed sides with a crease, round arches, rounded
corners, shoulders and roof edges, a crowned roof, lamps set into the body, closed wheels with every face outward, modest glass.
One car per build (configure(name)); each root in its own frame (Blender: z up, the front -y, metres; origin on the ground
between the axles; Unity (x, y, z) -> (-x, z, -y), the front -> +Z). The car's left (the driver's side) is +x."""
import math
import bmesh
from mathutils import Vector, Matrix
import van3_mech as VM
import gen_kit as K
from gen_kit import kb, part, socket, face, KBS, Z_STEELBLK
from van2_kit import ZERO
import start_kit as SK
from start_kit import (Z_PAINT, Z_CBLACK, Z_UNDER, Z_TYRE, Z_RIM, Z_CHROME, Z_HEAD, Z_TAIL, Z_SEAT, Z_DASH, Z_CARPET, Z_LINER,
                       Z_CARD, Z_GRILLE, Z_PLATE, Z_GAUGE, Z_RUBBER)
import car_tex as CT

SPECS = {
    'StartCar': dict(
        kind='estate', CW=0.86, CH=0.04, CC=0.13, FRONT=-2.30, REAR=2.24, YFA=-1.34, YRA=1.28, TRK=0.72, RW=0.30, RWID=0.19,
        RA=0.36, Z_SILL=0.24, Z_LOW=0.40, Z_MID=0.56, ZH0=0.74, ZH1=0.96, Z_BELT=0.96,          # 1.1: belt +8 cm
        Y_WS=-0.46, Y_RF=0.14, Y_RR=2.02, ZR=1.34, Z_ROOF=1.38, WB=0.80, WR=0.68,             # 1.1: windscreen 16 cm back
        PILLARS={'B': (0.44, 0.52), 'C': (1.32, 1.40), 'D': (1.88, 2.02)},
        LEVELS=(0.24, 0.40, 0.46, 0.52, 0.56, 0.64, 0.78),
        front_cells=((0.0, 0.34), (0.34, 0.38), (0.38, 0.66), (0.66, None)),
        front_zone=lambda xm, zm: (Z_HEAD if 0.38 <= xm <= 0.66 and 0.52 <= zm <= 0.64 else
                                   Z_TAIL if xm > 0.66 and 0.52 <= zm <= 0.64 else
                                   Z_GRILLE if xm < 0.34 and 0.52 <= zm <= 0.64 else Z_PAINT),
        rear_cells=((0.0, 0.24), (0.24, 0.52), (0.52, None)),
        rear_zone=lambda xm, zm, last: (Z_TAIL if last and 0.56 <= zm <= 0.78 else
                                        Z_PLATE if xm < 0.24 and 0.56 <= zm <= 0.64 else Z_PAINT),
        bumper='black', side_trim='black', rails=True, door_open=70.0, boot_open=None, crack=False,
        wheels={'RR': 'flat'}, drops={'RR': 0.08}, flat_drop=0.06, glass=((0.17, 0.16, 0.13), 0.62)),
    'WreckCar': dict(
        kind='saloon', CW=0.86, CH=0.04, CC=0.10, FRONT=-2.32, REAR=2.30, YFA=-1.36, YRA=1.30, TRK=0.72, RW=0.30, RWID=0.18,
        RA=0.36, Z_SILL=0.24, Z_LOW=0.40, Z_MID=0.60, ZH0=0.80, ZH1=0.94, Z_BELT=0.94,          # 1.1: belt +8 cm
        Y_WS=-0.39, Y_RF=0.11, Y_RR=1.06, ZR=1.32, Z_ROOF=1.36, WB=0.80, WR=0.70, Y_RW=1.50,  # 1.1: windscreen 17 cm back
        PILLARS={'B': (0.52, 0.60), 'C': (1.04, None)},
        LEVELS=(0.24, 0.40, 0.48, 0.54, 0.60, 0.70),
        front_cells=((0.0, 0.40), (0.40, 0.44), (0.44, 0.70), (0.70, None)),
        front_zone=lambda xm, zm: (Z_HEAD if 0.44 <= xm <= 0.70 and 0.54 <= zm <= 0.70 else
                                   Z_TAIL if xm > 0.70 and 0.54 <= zm <= 0.70 else
                                   Z_GRILLE if xm < 0.40 and 0.48 <= zm <= 0.70 else Z_PAINT),
        rear_cells=((0.0, 0.22), (0.22, 0.48), (0.48, None)),
        rear_zone=lambda xm, zm, last: (Z_TAIL if last and 0.54 <= zm <= 0.70 else
                                        Z_PLATE if xm < 0.22 and 0.54 <= zm <= 0.70 else Z_PAINT),
        bumper='chrome', side_trim='chrome', rails=False, door_open=None, boot_open=12.0, crack=True,
        wheels={'FR': 'missing', 'RR': 'flat'}, drops={'FR': 0.15, 'RR': 0.06}, flat_drop=0.05, glass=((0.20, 0.21, 0.22), 0.55)),
}

S = None                                             # the spec of the car being built (an object with the SPECS keys)
NAME = None
ROOTS = []
DISPLAY = {}
ROOT_OF = {}
BOXES = []
M_LEAN = Matrix.Identity(4)


class _Spec:
    def __init__(self, d):
        self.__dict__.update(d)


def configure(name):
    global S, NAME, ROOTS, DISPLAY
    S = _Spec(SPECS[name])
    NAME = name
    ROOTS[:] = [name]
    DISPLAY.clear()
    DISPLAY[name] = Vector((0.0, 0.0, 0.0))


def reg(name, atlas):
    ROOT_OF[name] = NAME
    return kb(name, atlas)


def z_top(y):
    if y <= S.Y_WS:
        return S.ZH0 + (S.ZH1 - S.ZH0) * (y - S.FRONT) / (S.Y_WS - S.FRONT)
    return S.ZH1 + (S.Z_BELT - S.ZH1) * min(1.0, (y - S.Y_WS) / max(S.REAR - S.Y_WS, 1e-3))


def xs(z, top):
    """the bowed side: tucked under at the sill, full from Z_LOW to the crease (its row 1.2 cm out: ShiftCar 2.2's crease),
    a little in at the shoulder"""
    if abs(z - S.Z_MID) < 1e-6:
        return S.CW + 0.012
    if z <= S.Z_LOW:
        return S.CW - 0.04 + 0.04 * (z - S.Z_SILL) / (S.Z_LOW - S.Z_SILL)
    if z <= S.Z_MID:
        return S.CW
    return S.CW - 0.02 * (z - S.Z_MID) / max(top - S.Z_MID, 1e-3)


def rows(bottom, top):
    return [bottom] + [l for l in S.LEVELS if bottom + 1e-4 < l < top - 1e-4] + [top]


def arch(yc):
    s = math.degrees(math.asin(max(-1.0, min(1.0, (S.Z_SILL - S.RW) / S.RA))))
    return [(yc + S.RA * math.cos(math.radians(180.0 - s + (2 * s - 180.0) * i / 12)),
             S.RW + S.RA * math.sin(math.radians(180.0 - s + (2 * s - 180.0) * i / 12))) for i in range(13)]


def door_span():
    """the open driver's door (front left, +x): from the windscreen's foot to the B pillar"""
    return S.Y_WS + 0.04, S.PILLARS['B'][0] + 0.04


def column(k, s, ya, za, yb, zb, ta, tb, zone=Z_PAINT):
    lv = sorted(set(list(S.LEVELS) + [za, zb, ta, tb]))
    for z0, z1 in zip(lv[:-1], lv[1:]):
        qa0, qa1 = min(max(z0, za), ta), min(max(z1, za), ta)
        qb0, qb1 = min(max(z0, zb), tb), min(max(z1, zb), tb)
        q = []
        for y, z in [(ya, qa0), (yb, qb0), (yb, qb1), (ya, qa1)]:
            p = (s * xs(z, ta if y == ya else tb), y, z)
            if not q or (Vector(p) - Vector(q[-1])).length > 1e-5:
                q.append(p)
        if len(q) > 2 and (Vector(q[0]) - Vector(q[-1])).length < 1e-5:
            q.pop()
        if len(q) >= 3:
            face(k, q, zone, (s, 0, 0))


def shoulder(k, s, ya, yb):
    X = S.CW - 0.02 - S.CH
    pa = [Vector((s * (X + S.CH * math.cos(math.radians(t))), ya, z_top(ya) - S.CH + S.CH * math.sin(math.radians(t)))) for t in (0, 45, 90)]
    pb = [Vector((s * (X + S.CH * math.cos(math.radians(t))), yb, z_top(yb) - S.CH + S.CH * math.sin(math.radians(t)))) for t in (0, 45, 90)]
    for i in range(2):
        face(k, [pa[i], pb[i], pb[i + 1], pa[i + 1]], Z_PAINT, (s, 0, 1))


def corner(k, s, end):
    d = 1 if end == S.FRONT else -1
    yc = end + d * S.CC
    top = z_top(yc) - S.CH
    n = 3
    for z0, z1 in zip(rows(S.Z_SILL, top)[:-1], rows(S.Z_SILL, top)[1:]):
        for i in range(n):
            ring = []
            for j in (i, i + 1):
                th = math.radians(90.0 * j / n)
                for z in (z0, z1):
                    X = xs(z, top)
                    ring.append((s * (X - S.CC + S.CC * math.cos(th)), yc - d * S.CC * math.sin(th), z))
            a0, a1, b0, b1 = ring
            mid = Vector(a0) + Vector(b1)
            out = Vector((mid.x / 2 - s * (S.CW - S.CC), mid.y / 2 - yc, 0)).normalized()
            face(k, [a0, b0, b1, a1], Z_PAINT, out)


def end_cap(k, end):
    """the top of a car's end as one closed fan (1.2: the nose rounding, fills and corner caps of 1.1 left slivers that a
    back-face-culling engine showed as holes): the end face's top edge, both rounded corners, the shoulders' profiles and the
    hood / deck edge at the corners' station - every edge shared with its neighbour"""
    d = 1 if end == S.FRONT else -1
    yc = end + d * S.CC
    top = z_top(yc) - S.CH
    zt = z_top(yc)
    X = S.CW - 0.02 - S.CH
    n = 3

    def arc(s, js):
        return [(s * (xs(top, top) - S.CC + S.CC * math.cos(math.radians(90.0 * j / n))),
                 yc - d * S.CC * math.sin(math.radians(90.0 * j / n)), top) for j in js]

    def sh(s, ts):
        return [(s * (X + S.CH * math.cos(math.radians(t))), yc, top + S.CH * math.sin(math.radians(t))) for t in ts]
    loop = arc(1, range(n, -1, -1)) + sh(1, (45, 90)) + sh(-1, (90, 45)) + arc(-1, range(0, n + 1))
    c = Vector((0.0, end + d * S.CC * 0.45, top + (zt - top) * 0.75))
    pts = [Vector(q) for q in loop]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        face(k, [a, b, c], Z_PAINT, (0, -d * 0.4, 1))


def flip_to(faces, want):
    for f in faces:
        f.normal_update()
        if f.normal.dot(want(f.calc_center_median())) < 0:
            f.normal_flip()


def wheel(k, c, side, kind='ok', r=None, w=None, seg=16):
    """a road tyre on a steel wheel with a hub cap, closed inside, every face outward; 'flat': the bottom squashed onto the
    ground; 'missing': only the brake drum on its hub (the car lies on it)"""
    r = r or S.RW
    w = w or S.RWID
    bm = k.bm
    ax = Vector((side, 0, 0))
    hw = w / 2
    if kind == 'missing':
        f0 = len(bm.faces)
        k.lathe(c, ax, [(-0.06, 0.0), (-0.06, 0.13), (0.03, 0.13), (0.04, 0.10), (0.06, 0.05), (0.07, 0.0)], Z_RIM, 12, cap0=False,
                cap1=False)
        bm.faces.ensure_lookup_table()
        flip_to(bm.faces[f0:], lambda p: p - c)
        return
    prof = [(-hw, r * 0.62), (-hw * 1.06, r * 0.78), (-hw * 1.02, r * 0.93), (-hw * 0.7, r), (hw * 0.7, r), (hw * 1.02, r * 0.93),
            (hw * 1.06, r * 0.78), (hw, r * 0.62)]
    n0 = len(bm.verts)
    f0 = len(bm.faces)
    k.lathe(c, ax, prof, Z_TYRE, seg, cap0=False, cap1=False)
    if kind == 'flat':
        bm.verts.ensure_lookup_table()
        zmin = c.z - r
        for v in bm.verts[n0:]:
            if v.co.z < 0.10:
                v.co.z = 0.10 * (v.co.z - zmin) / (0.10 - zmin)          # [lowest, 0.10] -> [0, 0.10]: squashed, not folded
                dd = (v.co - c).dot(ax)
                bul = 0.04 * (1 - v.co.z / 0.10)
                v.co += ax * (math.copysign(bul, dd) if abs(dd) > 0.01 else 0.0)
    bm.faces.ensure_lookup_table()
    flip_to(bm.faces[f0:], lambda p: p - c)
    f1 = len(bm.faces)
    k.lathe(c, ax, [(-hw, r * 0.62), (hw, r * 0.62)], Z_TYRE, seg, cap0=False, cap1=False)
    bm.faces.ensure_lookup_table()
    flip_to(bm.faces[f1:], lambda p: -((p - c) - ax * (p - c).dot(ax)))
    f2 = len(bm.faces)
    o = c + ax * (hw * 0.70)
    k.lathe(o, ax, [(0.0, r * 0.62), (-0.015, r * 0.56), (-0.035, r * 0.42), (-0.035, r * 0.26), (-0.01, r * 0.22), (0.0, r * 0.14),
                    (0.0, 0.0)], Z_RIM, seg // 2, cap0=False, cap1=False)
    bm.faces.ensure_lookup_table()
    flip_to(bm.faces[f2:], lambda p: ax)
    f3 = len(bm.faces)
    k.lathe(c - ax * (hw * 0.70), -ax, [(0.0, r * 0.62), (0.03, r * 0.30), (0.04, 0.0)], Z_UNDER, seg // 2, cap0=False, cap1=False)
    bm.faces.ensure_lookup_table()
    flip_to(bm.faces[f3:], lambda p: -ax)


# ---------------------------------------------------------------------------------------------------------------- body
def body():
    k = reg(NAME, NAME)
    yd0, yd1 = door_span() if S.door_open else (None, None)
    bottom = [(S.FRONT + S.CC, S.Z_SILL)]
    for yc in (S.YFA, S.YRA):
        bottom += arch(yc)
    bottom.append((S.REAR - S.CC, S.Z_SILL))
    if yd0 is not None:                                          # the door's cut lines as stations of the outline
        for yy in (yd0, yd1):
            for i in range(len(bottom) - 1):
                (ya, za), (yb, zb) = bottom[i], bottom[i + 1]
                if ya < yy < yb:
                    bottom.insert(i + 1, (yy, za + (zb - za) * (yy - ya) / (yb - ya)))
                    break
    in_door = lambda s, ya, yb: S.door_open and s > 0 and ya >= yd0 - 1e-6 and yb <= yd1 + 1e-6
    for s in (-1, 1):
        for (ya, za), (yb, zb) in zip(bottom[:-1], bottom[1:]):
            if yb - ya > 1e-6 and not in_door(s, ya, yb):
                column(k, s, ya, za, yb, zb, z_top(ya) - S.CH, z_top(yb) - S.CH)
        ys = sorted(set([S.FRONT + S.CC, (S.FRONT + S.Y_WS) / 2, S.Y_WS, 0.0, 1.0, S.REAR - S.CC] + ([yd0, yd1] if yd0 else [])))
        for ya, yb in zip(ys[:-1], ys[1:]):
            if not in_door(s, ya, yb):
                shoulder(k, s, ya, yb)
        X = S.CW - 0.02 - S.CH
        # the belt top behind the windscreen (the glasshouse stands on it)
        face(k, [(s * X, S.Y_WS, z_top(S.Y_WS)), (s * X, S.REAR - S.CC, z_top(S.REAR - S.CC)),
                 (s * (S.WB - 0.02), S.REAR - S.CC, z_top(S.REAR - S.CC)), (s * (S.WB - 0.02), S.Y_WS, z_top(S.Y_WS))], Z_PAINT, (0, 0, 1))
        for yc in (S.YFA, S.YRA):                                   # wheel wells, a lip round the arch
            pts = arch(yc)
            for (ya, za), (yb, zb) in zip(pts[:-1], pts[1:]):
                n = Vector((0, yc - (ya + yb) / 2, S.RW - (za + zb) / 2)).normalized()
                q = [(s * xs(za, 1.0), ya, za), (s * xs(zb, 1.0), yb, zb), (s * 0.54, yb, zb), (s * 0.54, ya, za)]
                face(k, q, Z_UNDER, n)
                face(k, q, Z_UNDER, -n)                                  # its back: seen from inside the car
            face(k, [(s * 0.54, y, z) for y, z in pts], Z_UNDER, (s, 0, 0))
            face(k, [(s * 0.54, y, z) for y, z in pts], Z_UNDER, (-s, 0, 0))
            k.strip([Vector((s * (S.CW + 0.006), y, z)) for y, z in pts], Vector((s, 0, 0)), 0.035, 0.016, Z_PAINT)
        trim = Z_CBLACK if S.side_trim == 'black' else Z_CHROME
        th = 0.06 if S.side_trim == 'black' else 0.016
        for ya, yb in ((S.FRONT + S.CC, S.YFA - S.RA - 0.04), (S.YFA + S.RA + 0.04, S.YRA - S.RA - 0.04),
                       (S.YRA + S.RA + 0.04, S.REAR - S.CC)):
            if S.door_open and s > 0 and ya < yd1 and yb > yd0:       # the open door carries its own piece
                for a, b in ((ya, yd0), (yd1, yb)):
                    if b - a > 0.02:
                        k.box(*sorted((s * (S.CW - 0.005), s * (S.CW + 0.018))), a, b, S.Z_MID - th / 2, S.Z_MID + th / 2, trim)
                continue
            k.box(*sorted((s * (S.CW - 0.005), s * (S.CW + 0.018))), ya, yb, S.Z_MID - th / 2, S.Z_MID + th / 2, trim)
        corner(k, s, S.FRONT)
        corner(k, s, S.REAR)
    front(k)
    rear(k)
    top(k)
    # bumpers, the floor pan, the axles
    for yy, d in ((S.FRONT, -1), (S.REAR, 1)):
        zone = Z_CBLACK if S.bumper == 'black' else Z_CHROME
        hgt = 0.16 if S.bumper == 'black' else 0.11
        zc = 0.38 if S.bumper == 'black' else 0.37
        VM.rbox(k, (0.0, yy + d * 0.04, zc), (1.66, 0.12, hgt), zone, r=0.03 if S.bumper == 'black' else 0.02, ch=0.012, axis='x')
        for s in (-1, 1):
            VM.obox(k, Vector((s * 0.84, yy - d * 0.05, zc)), (0.09, 0.22, hgt - 0.02), zone, Matrix.Rotation(math.radians(s * d * 30), 3, 'Z'))
            if S.bumper == 'chrome':                                # rubber overriders
                k.box(s * 0.30 - 0.04, s * 0.30 + 0.04, yy + d * 0.08 - 0.04, yy + d * 0.08 + 0.04, zc - 0.07, zc + 0.08, Z_RUBBER)
    face(k, [(-(S.CW - 0.04), S.FRONT + S.CC, S.Z_SILL), (S.CW - 0.04, S.FRONT + S.CC, S.Z_SILL), (S.CW - 0.04, S.REAR - S.CC, S.Z_SILL),
             (-(S.CW - 0.04), S.REAR - S.CC, S.Z_SILL)], Z_UNDER, (0, 0, -1))
    for yc in (S.YFA, S.YRA):
        k.cyl(Vector((-S.TRK + 0.12, yc, S.RW)), Vector((S.TRK - 0.12, yc, S.RW)), 0.05, Z_UNDER, 6)
    k.cyl(Vector((0.30, S.REAR - 0.10, 0.26)), Vector((0.30, S.REAR + 0.06, 0.25)), 0.025, Z_STEELBLK, 6)          # the exhaust
    SK.triangulate_ngons(k)
    return k


def front(k):
    top_f = z_top(S.FRONT + S.CC) - S.CH
    zs = rows(S.Z_SILL, top_f)
    for za, zb in zip(zs[:-1], zs[1:]):
        zm = (za + zb) / 2
        for s in (-1, 1):
            xo_a, xo_b = xs(za, top_f) - S.CC, xs(zb, top_f) - S.CC
            for x0, x1 in S.front_cells:
                xa1, xb1 = (x1 if x1 is not None else xo_a), (x1 if x1 is not None else xo_b)
                if xa1 - x0 < 1e-4 and xb1 - x0 < 1e-4:
                    continue
                xm = (x0 + xa1) / 2
                face(k, [(s * x0, S.FRONT, za), (s * xa1, S.FRONT, za), (s * xb1, S.FRONT, zb), (s * x0, S.FRONT, zb)],
                     S.front_zone(xm, zm), (0, -1, 0))
    end_cap(k, S.FRONT)
    # the lamps' bezels and the grille's frame
    hx = [c for c in S.front_cells if c[1] is not None]
    lamp = hx[2]
    zl = [z for z in S.LEVELS]
    z0 = min(z for z in zl if z >= (0.52 if S.kind == 'estate' else 0.54) - 1e-6)
    z1 = 0.64 if S.kind == 'estate' else 0.70
    zone = Z_CBLACK if S.bumper == 'black' else Z_CHROME
    for s in (-1, 1):
        a, b = lamp
        k.strip([Vector((s * (a - 0.006), S.FRONT - 0.006, z0 - 0.006)), Vector((s * (b + 0.006), S.FRONT - 0.006, z0 - 0.006)),
                 Vector((s * (b + 0.006), S.FRONT - 0.006, z1 + 0.006)), Vector((s * (a - 0.006), S.FRONT - 0.006, z1 + 0.006)),
                 Vector((s * (a - 0.006), S.FRONT - 0.006, z0 - 0.006))], Vector((0, -1, 0)), 0.014, 0.012, zone, caps=False)
    if S.bumper == 'chrome':
        g = hx[0][1]
        k.strip([Vector((-g, S.FRONT - 0.008, 0.48)), Vector((g, S.FRONT - 0.008, 0.48)), Vector((g, S.FRONT - 0.008, 0.71)),
                 Vector((-g, S.FRONT - 0.008, 0.71)), Vector((-g, S.FRONT - 0.008, 0.48))], Vector((0, -1, 0)), 0.024, 0.016, Z_CHROME,
                caps=False)


def rear(k):
    top_r = z_top(S.REAR - S.CC) - S.CH
    zs = rows(S.Z_SILL, top_r)
    for za, zb in zip(zs[:-1], zs[1:]):
        zm = (za + zb) / 2
        for s in (-1, 1):
            xo_a, xo_b = xs(za, top_r) - S.CC, xs(zb, top_r) - S.CC
            for x0, x1 in S.rear_cells:
                xa1, xb1 = (x1 if x1 is not None else xo_a), (x1 if x1 is not None else xo_b)
                face(k, [(s * x0, S.REAR, za), (s * xa1, S.REAR, za), (s * xb1, S.REAR, zb), (s * x0, S.REAR, zb)],
                     S.rear_zone((x0 + xa1) / 2, zm, x1 is None), (0, 1, 0))
    end_cap(k, S.REAR)


def top(k):
    """the hood (closed, with its seam painted) and, on the saloon, the boot deck round the lid"""
    X = S.CW - 0.02 - S.CH
    y0 = S.FRONT + S.CC
    ys = [y0 + (S.Y_WS - y0) * i / 4 for i in range(5)]
    for ya, yb in zip(ys[:-1], ys[1:]):
        face(k, [(-X, ya, z_top(ya)), (X, ya, z_top(ya)), (X, yb, z_top(yb)), (-X, yb, z_top(yb))], Z_PAINT, (0, 0, 1))
    face(k, [(-X, S.Y_WS, z_top(S.Y_WS)), (X, S.Y_WS, z_top(S.Y_WS)), (X, S.Y_WS + 0.03, z_top(S.Y_WS) + 0.005),
             (-X, S.Y_WS + 0.03, z_top(S.Y_WS) + 0.005)], Z_CBLACK, (0, 0, 1))
    if S.kind == 'saloon':
        yl0, yl1, xl = S.Y_RW + 0.03, S.REAR - S.CC, S.WB - 0.04       # the lid's opening: a dark boot under it
        face(k, [(-X, S.Y_RW, z_top(S.Y_RW)), (X, S.Y_RW, z_top(S.Y_RW)), (X, yl0, z_top(yl0)), (-X, yl0, z_top(yl0))], Z_PAINT, (0, 0, 1))
        for s in (-1, 1):
            face(k, [(s * X, yl0, z_top(yl0)), (s * X, yl1, z_top(yl1)), (s * xl, yl1, z_top(yl1)), (s * xl, yl0, z_top(yl0))], Z_PAINT,
                 (0, 0, 1))
        k.box(-xl, xl, yl0, yl1, 0.40, 0.42, Z_CARPET)                  # the boot floor
        for s in (-1, 1):
            face(k, [(s * xl, yl0, 0.42), (s * xl, yl1, 0.42), (s * xl, yl1, z_top(yl1)), (s * xl, yl0, z_top(yl0))], Z_UNDER, (-s, 0, 0))
        face(k, [(-xl, yl0, 0.42), (xl, yl0, 0.42), (xl, yl0, z_top(yl0)), (-xl, yl0, z_top(yl0))], Z_UNDER, (0, 1, 0))
        face(k, [(-xl, yl1, 0.42), (xl, yl1, 0.42), (xl, yl1, z_top(yl1)), (-xl, yl1, z_top(yl1))], Z_UNDER, (0, -1, 0))


# ---------------------------------------------------------------------------------------------------------------- glass
def P(s, y, t, inset=0.0):
    x, z = s * (S.WB + (S.WR - S.WB) * t), S.Z_BELT + (S.ZR - S.Z_BELT) * t
    return Vector((x - s * inset, y, z))


def rear_line(t):
    """y of the glasshouse's rear edge at height fraction t (the tailgate glass on the estate, the rear window on the saloon)"""
    if S.kind == 'estate':
        return (S.REAR - S.CC) + (S.Y_RR - (S.REAR - S.CC)) * t
    return S.Y_RW + (S.Y_RR - S.Y_RW) * t


def glasshouse():
    k = KBS[NAME]
    g = reg(NAME + '_Glass', 'glass')
    rr = 0.04
    for s in (-1, 1):                                                  # the roof's rounded side edges, drip rails
        prev = None
        for t in (0, 45, 90):
            a = math.radians(t)
            cur = (s * (S.WR - rr + rr * math.cos(a)), S.ZR + (S.Z_ROOF - S.ZR) * math.sin(a))
            if prev:
                face(k, [(prev[0], S.Y_RF, prev[1]), (prev[0], S.Y_RR, prev[1]), (cur[0], S.Y_RR, cur[1]), (cur[0], S.Y_RF, cur[1])],
                     Z_PAINT, (s, 0, 1))
            prev = cur
        k.strip([Vector((s * (S.WR + 0.006), S.Y_RF + 0.04, S.ZR - 0.008)), Vector((s * (S.WR + 0.006), S.Y_RR - 0.02, S.ZR - 0.008))],
                Vector((0, 0, 1)), 0.012, 0.012, Z_CHROME if S.bumper == 'chrome' else Z_CBLACK)
    xr = S.WR - rr
    face(k, [(-xr, S.Y_RF + 0.03, S.Z_ROOF), (xr, S.Y_RF + 0.03, S.Z_ROOF), (xr, S.Y_RR - 0.02, S.Z_ROOF), (-xr, S.Y_RR - 0.02, S.Z_ROOF)],
         Z_PAINT, (0, 0, 1))
    for yy, ye, d in ((S.Y_RF, S.Y_RF + 0.03, -1), (S.Y_RR, S.Y_RR - 0.02, 1)):
        face(k, [(-S.WR, yy, S.ZR), (S.WR, yy, S.ZR), (xr, ye, S.Z_ROOF), (-xr, ye, S.Z_ROOF)], Z_PAINT, (0, d, 1))
        for s in (-1, 1):
            face(k, [(s * S.WR, yy, S.ZR), (s * xr, ye, S.Z_ROOF), (s * S.WR, ye, S.ZR + (S.Z_ROOF - S.ZR) * 0.7)], Z_PAINT, (s, d, 1))
    face(k, [(-S.WR + 0.03, S.Y_RF + 0.03, S.ZR - 0.03), (S.WR - 0.03, S.Y_RF + 0.03, S.ZR - 0.03), (S.WR - 0.03, S.Y_RR - 0.03, S.ZR - 0.03),
             (-S.WR + 0.03, S.Y_RR - 0.03, S.ZR - 0.03)], Z_LINER, (0, 0, -1))   # the headliner
    yd0, yd1 = door_span() if S.door_open else (None, None)
    for s in (-1, 1):
        a0, a1 = P(s, S.Y_WS, 0.0), P(s, S.Y_RF, 1.0)
        k.strip([a0 + Vector((0, 0.03, 0)), a1 + Vector((0, 0.03, -0.01))], Vector((s, 0, 0.35)), 0.07, 0.045, Z_PAINT)
        b0, b1 = S.PILLARS['B']
        q = [P(s, b0, 0.0), P(s, b1, 0.0), P(s, b1, 1.0), P(s, b0, 1.0)]
        face(k, q, Z_CBLACK, (s, 0, 0.4))
        face(k, q, Z_LINER, (-s, 0, -0.4))                                # every pillar has an inside (seen through the far windows)
        if S.kind == 'estate':
            for name in ('C', 'D'):
                ya, yb = S.PILLARS[name]
                face(k, [P(s, ya, 0.0), P(s, yb, 0.0), P(s, yb, 1.0), P(s, ya, 1.0)], Z_CBLACK if name == 'C' else Z_PAINT, (s, 0, 0.4))
                face(k, [P(s, ya, 0.0), P(s, yb, 0.0), P(s, yb, 1.0), P(s, ya, 1.0)], Z_LINER, (-s, 0, -0.4))
            yb_ = S.PILLARS['D'][1]
            dq = [P(s, yb_, 0.0), Vector((s * (S.WB - 0.04), rear_line(0.0), S.Z_BELT)), Vector((s * (S.WR - 0.02), rear_line(1.0), S.ZR)),
                  P(s, yb_, 1.0)]
            face(k, dq, Z_PAINT, (s, 1, 0.3))
            face(k, dq, Z_LINER, (-s, -1, -0.3))
            spans = [(b1, S.PILLARS['C'][0]), (S.PILLARS['C'][1], S.PILLARS['D'][0])]
        else:
            c0 = S.PILLARS['C'][0]
            cq = [P(s, c0, 0.0), Vector((s * S.WB, S.Y_RW, S.Z_BELT)), Vector((s * S.WR, S.Y_RR, S.ZR)), P(s, c0, 1.0)]
            face(k, cq, Z_PAINT, (s, 0, 0.4))
            face(k, cq, Z_LINER, (-s, 0, -0.4))
            spans = [(b1, c0)]
        k.box(*sorted((s * (S.WB - 0.01), s * (S.WB + 0.01))), S.Y_WS, rear_line(0.0), S.Z_BELT - 0.01, S.Z_BELT + 0.01, Z_RUBBER)
        windows = [] if (S.door_open and s > 0) else [(S.Y_WS + 0.08, b0, True)]
        windows += [(ya, yb, False) for ya, yb in spans]
        for ya, yb, first in windows:
            if first:
                pts = [P(s, ya, 0.03, 0.01), P(s, yb, 0.03, 0.01), P(s, yb, 0.97, 0.01), P(s, S.Y_RF + 0.06, 0.97, 0.01)]
            else:
                pts = [P(s, ya, 0.03, 0.01), P(s, yb, 0.03, 0.01), P(s, yb, 0.97, 0.01), P(s, ya, 0.97, 0.01)]
            face(g, pts, ZERO, (s, 0, 0.4))
            k.strip(pts + [pts[0]], Vector((s, 0, 0.4)), 0.018, 0.010, Z_RUBBER, caps=False)
        if not (S.door_open and s > 0):                                  # mirror and handle on a closed front door
            mirror(k, s, S.Y_WS + 0.12)
            k.box(*sorted((s * (S.CW - 0.02), s * (S.CW + 0.012))), b0 - 0.16, b0 - 0.04, S.Z_BELT - 0.10, S.Z_BELT - 0.075, Z_CBLACK)
        k.box(*sorted((s * (S.CW - 0.02), s * (S.CW + 0.012))), S.PILLARS['C'][0] - 0.16, S.PILLARS['C'][0] - 0.04, S.Z_BELT - 0.10,
              S.Z_BELT - 0.075, Z_CBLACK)
    ws = [Vector((-S.WB + 0.05, S.Y_WS + 0.05, S.Z_BELT + 0.01)), Vector((S.WB - 0.05, S.Y_WS + 0.05, S.Z_BELT + 0.01)),
          Vector((S.WR - 0.05, S.Y_RF + 0.02, S.ZR - 0.01)), Vector((-S.WR + 0.05, S.Y_RF + 0.02, S.ZR - 0.01))]
    face(g, ws, ZERO, (0, -0.6, 0.8))
    k.strip(ws + [ws[0]], Vector((0, -0.6, 0.8)), 0.03, 0.012, Z_CHROME if S.bumper == 'chrome' else Z_RUBBER, caps=False)
    for xw in (-0.46, 0.02):
        k.strip([Vector((xw, S.Y_WS + 0.07, S.Z_BELT + 0.03)), Vector((xw + 0.40, S.Y_WS + 0.13, S.Z_BELT + 0.10))], Vector((0, -0.6, 0.8)),
                0.018, 0.010, Z_CBLACK)
    rw = [Vector((S.WR - 0.05, rear_line(1.0) - 0.01, S.ZR - 0.03)), Vector((-S.WR + 0.05, rear_line(1.0) - 0.01, S.ZR - 0.03)),
          Vector((-S.WB + 0.08, rear_line(0.0), S.Z_BELT + 0.03)), Vector((S.WB - 0.08, rear_line(0.0), S.Z_BELT + 0.03))]
    face(g, rw, ZERO, (0, 1, 0.5))
    k.strip(rw + [rw[0]], Vector((0, 1, 0.5)), 0.03, 0.012, Z_CHROME if S.bumper == 'chrome' else Z_RUBBER, caps=False)
    if S.rails:                                                         # roof rails on three feet
        for s in (-1, 1):
            xx = s * (S.WR - 0.12)
            k.tube([Vector((xx, S.Y_RF + 0.30, S.Z_ROOF + 0.05)), Vector((xx, S.Y_RR - 0.12, S.Z_ROOF + 0.05))], 0.016, Z_CBLACK, 6)
            for yy in (S.Y_RF + 0.30, (S.Y_RF + S.Y_RR) / 2, S.Y_RR - 0.12):
                k.box(xx - 0.02, xx + 0.02, yy - 0.04, yy + 0.04, S.Z_ROOF - 0.01, S.Z_ROOF + 0.05, Z_CBLACK)
    if S.crack:                                                         # the cracked windscreen (decal over the glass)
        p = reg(NAME + '_Crack', 'panel')
        c = (ws[0] + ws[1] + ws[2] + ws[3]) / 4
        c = c + (ws[0] - ws[1]).normalized() * 0.18 + (ws[0] - ws[3]).normalized() * 0.10
        n = (ws[1] - ws[0]).cross(ws[3] - ws[0]).normalized()
        if n.dot(Vector((0, -0.6, 0.8))) < 0:
            n = -n
        K.quad(p, c + n * 0.004, tuple(n), 0.62, 0.42, CT.uv('crack'), up=tuple((ws[3] - ws[0]).normalized()))
        part(NAME + '_Crack', 'static', tuple(c), parent=NAME, note='the cracks on the windscreen (cut-out decal, panel atlas)')
    part(NAME + '_Glass', 'static', (0, 0.4, 1.10), parent=NAME, note='all fixed windows (dirty glass)')


def mirror(k, s, y):
    k.box(*sorted((s * (S.CW - 0.02), s * (S.CW + 0.04))), y - 0.03, y + 0.03, S.Z_BELT - 0.05, S.Z_BELT - 0.01, Z_CBLACK)
    VM.rbox(k, (s * (S.CW + 0.09), y, S.Z_BELT + 0.04), (0.13, 0.04, 0.10), Z_CBLACK if S.bumper == 'black' else Z_CHROME, r=0.02,
            ch=0.008, axis='y')


# ---------------------------------------------------------------------------------------------------------------- interior
def interior():
    """seen through the glass and the open door: floor, door cards, dash, wheel, two front seats, the rear bench"""
    k = KBS[NAME]
    xi = S.CW - 0.06
    yi0, yi1 = S.Y_WS + 0.02, (S.REAR - S.CC - 0.05) if S.kind == 'estate' else S.Y_RW - 0.02
    def over_arch(y, m=0.0):
        return any(abs(y - yc) < S.RA + m for yc in (S.YFA, S.YRA))

    def card_bottom(y):
        zb = 0.30
        for yc in (S.YFA, S.YRA):
            if abs(y - yc) < S.RA:
                zb = max(zb, S.RW + math.sqrt(S.RA ** 2 - (y - yc) ** 2) + 0.06)
        return zb

    def stations(ya, yb, edge=0.0):
        ys = [ya, yb] + [yc + sg * (S.RA + edge) for yc in (S.YFA, S.YRA) for sg in (-1, 1)]
        ys += [yc - S.RA + 2 * S.RA * i / 16 for yc in (S.YFA, S.YRA) for i in range(17)]
        return sorted(set(round(y, 5) for y in ys if ya - 1e-6 <= y <= yb + 1e-6))
    fs = stations(yi0, yi1, 0.02)
    for ya, yb in zip(fs[:-1], fs[1:]):                                   # the floor: 0.52 wide over the wells
        w = 0.52 if over_arch((ya + yb) / 2, 0.02) else xi
        face(k, [(-w, ya, 0.30), (w, ya, 0.30), (w, yb, 0.30), (-w, yb, 0.30)], Z_CARPET, (0, 0, 1))
    yd0, yd1 = door_span() if S.door_open else (None, None)
    for s in (-1, 1):
        if S.door_open and s > 0:
            segs = [(yd1, yi1)]
            face(k, [(s * xi, yd0, 0.30), (s * S.CW, yd0, 0.30), (s * S.CW, yd1, 0.30), (s * xi, yd1, 0.30)], Z_CARPET, (0, 0, 1))   # the sill
        else:
            segs = [(yi0, yi1)]
        for ya, yb in segs:
            st = stations(ya, yb)
            for y0, y1 in zip(st[:-1], st[1:]):
                face(k, [(s * xi, y0, card_bottom(y0)), (s * xi, y1, card_bottom(y1)), (s * xi, y1, S.Z_BELT), (s * xi, y0, S.Z_BELT)],
                     Z_CARD, (-s, 0, 0))
    face(k, [(-xi, yi1, 0.30), (xi, yi1, 0.30), (xi, yi1, S.Z_BELT), (-xi, yi1, S.Z_BELT)], Z_CARD, (0, -1, 0))
    face(k, [(-xi, yi0, 0.30), (xi, yi0, 0.30), (xi, yi0, S.Z_BELT), (-xi, yi0, S.Z_BELT)], Z_CARPET, (0, 1, 0))
    VM.rbox(k, (0.0, S.Y_WS + 0.20, S.Z_BELT - 0.08), (2 * xi, 0.34, 0.20), Z_DASH, r=0.04, ch=0.02, axis='x')
    k.box(0.20, 0.56, S.Y_WS + 0.36, S.Y_WS + 0.38, S.Z_BELT - 0.14, S.Z_BELT - 0.04, Z_GAUGE)
    sc = Vector((0.38, S.Y_WS + 0.50, S.Z_BELT - 0.04))
    ax = Vector((0, 0.80, 0.60)).normalized()
    k.cyl(sc - ax * 0.30, sc - ax * 0.02, 0.022, Z_CBLACK, 8)
    e1 = Vector((1, 0, 0))
    e2 = ax.cross(e1).normalized()
    k.tube([sc + (e1 * math.cos(2 * math.pi * i / 12) + e2 * math.sin(2 * math.pi * i / 12)) * 0.18 for i in range(13)], 0.014, Z_CBLACK, 5,
           caps=False)
    yf = S.Y_WS + 0.95
    for xc in (-0.38, 0.38):
        VM.rbox(k, (xc, yf, 0.42), (0.46, 0.48, 0.12), Z_SEAT, r=0.03, ch=0.015, axis='z')
        VM.obox(k, Vector((xc, yf + 0.27, 0.72)), (0.45, 0.10, 0.56), Z_SEAT, Matrix.Rotation(math.radians(-14), 3, 'X'))
        VM.rbox(k, (xc, yf + 0.31, 1.04), (0.24, 0.10, 0.14), Z_SEAT, r=0.03, ch=0.01, axis='z')
    yr = yf + (0.85 if S.kind == 'estate' else 0.78)
    VM.rbox(k, (0.0, yr, 0.42), (2 * xi - 0.06, 0.46, 0.12), Z_SEAT, r=0.03, ch=0.015, axis='z')
    VM.obox(k, Vector((0.0, yr + 0.26, 0.70)), (2 * xi - 0.06, 0.10, 0.52), Z_SEAT, Matrix.Rotation(math.radians(-10), 3, 'X'))
    if S.kind == 'saloon' and yi1 - (yr + 0.28) > 0.02:                 # the parcel shelf under the rear window
        face(k, [(-xi, yr + 0.28, S.Z_BELT), (xi, yr + 0.28, S.Z_BELT), (xi, yi1, S.Z_BELT), (-xi, yi1, S.Z_BELT)], Z_DASH, (0, 0, 1))


# ---------------------------------------------------------------------------------------------------------------- moving parts
def door():
    """the driver's door (front left, +x), open: the side between its cut lines, its window frame and glass, the inner card"""
    name = 'IX_CarDoor'
    d = reg(name, NAME)
    dg = reg(name + '_Glass', 'glass')
    yd0, yd1 = door_span()
    s = 1
    bottom = []
    for yy in (yd0, yd1):
        z = S.Z_SILL
        for yc in (S.YFA, S.YRA):
            if abs(yy - yc) < S.RA:
                z = max(z, S.RW + math.sqrt(S.RA * S.RA - (yy - yc) ** 2))
        bottom.append((yy, z + 0.01))
    (ya, za), (yb, zb) = bottom
    column(d, s, ya, za, yb, zb, z_top(ya) - S.CH, z_top(yb) - S.CH)
    shoulder(d, s, ya, yb)
    xi = S.CW - 0.07
    X = S.CW - 0.02 - S.CH
    face(d, [(xi, ya, za), (xi, yb, zb), (xi, yb, z_top(yb)), (xi, ya, z_top(ya))], Z_CARD, (-1, 0, 0))
    face(d, [(X, ya, z_top(ya)), (X, yb, z_top(yb)), (xi, yb, z_top(yb)), (xi, ya, z_top(ya))], Z_PAINT, (0, 0, 1))
    for yy, n in ((ya, -1), (yb, 1)):
        zz = za if yy == ya else zb
        face(d, [(xs(zz, 1.0), yy, zz), (xs(z_top(yy) - S.CH, z_top(yy) - S.CH), yy, z_top(yy) - S.CH), (xi, yy, z_top(yy)), (xi, yy, zz)],
             Z_PAINT, (0, n, 0))
    face(d, [(xs(za, 1.0), ya, za), (xs(zb, 1.0), yb, zb), (xi, yb, zb), (xi, ya, za)], Z_PAINT, (0, 0, -1))
    fr = [P(s, S.Y_WS + 0.06, 0.0), P(s, yb - 0.02, 0.0), P(s, yb - 0.02, 1.0), P(s, S.Y_RF + 0.04, 1.0)]
    d.strip(fr + [fr[0]], Vector((1, 0, 0.4)), 0.035, 0.022, Z_CBLACK, caps=False)
    gl = [P(s, S.Y_WS + 0.09, 0.04, 0.01), P(s, yb - 0.05, 0.04, 0.01), P(s, yb - 0.05, 0.95, 0.01), P(s, S.Y_RF + 0.07, 0.95, 0.01)]
    face(dg, gl, ZERO, (1, 0, 0.4))
    face(dg, list(reversed(gl)), ZERO, (-1, 0, -0.4))
    d.box(S.CW - 0.01, S.CW + 0.015, yb - 0.17, yb - 0.05, S.Z_BELT - 0.10, S.Z_BELT - 0.075, Z_CBLACK)       # the handle
    d.box(xi - 0.03, xi, ya + 0.20, ya + 0.50, 0.55, 0.60, Z_CARD)                                           # the armrest
    trim = Z_CBLACK if S.side_trim == 'black' else Z_CHROME
    th = 0.06 if S.side_trim == 'black' else 0.016
    d.box(S.CW + 0.007, S.CW + 0.030, ya + 0.005, yb - 0.005, S.Z_MID - th / 2, S.Z_MID + th / 2, trim)
    mirror(d, s, S.Y_WS + 0.12)
    piv = Vector((S.CW, ya, 0.0))
    R = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(-S.door_open), 4, 'Z') @ Matrix.Translation(-piv)
    K.transform_kb(d, R)
    K.transform_kb(dg, R)
    part(name, 'hinge', tuple(piv), axis=(0, 0, 1), rng=(0, 72), rest=S.door_open, parent=NAME,
         note=f'the driver\'s door (front left, +x): hinge at its front edge, stands open {S.door_open:.0f} deg (static)')
    part(name + '_Glass', 'static', tuple(piv), parent=name, note='the door\'s window')


def boot():
    """the saloon's boot lid, ajar: hinged at its front edge (axis x), its rear edge up S.boot_open degrees"""
    name = 'IX_WreckCarBoot'
    b = reg(name, NAME)
    y0, y1, x = S.Y_RW + 0.03, S.REAR - S.CC + 0.02, S.WB - 0.03
    z0, z1 = z_top(y0) + 0.005, z_top(y1) + 0.005
    face(b, [(-x, y0, z0), (x, y0, z0), (x, y1, z1), (-x, y1, z1)], Z_PAINT, (0, 0, 1))
    face(b, [(-x, y0, z0 - 0.03), (x, y0, z0 - 0.03), (x, y1, z1 - 0.03), (-x, y1, z1 - 0.03)], Z_UNDER, (0, 0, -1))
    face(b, [(-x, y1, z1 - 0.05), (x, y1, z1 - 0.05), (x, y1, z1), (-x, y1, z1)], Z_PAINT, (0, 1, 0))
    for s in (-1, 1):
        face(b, [(s * x, y0, z0 - 0.03), (s * x, y1, z1 - 0.05), (s * x, y1, z1), (s * x, y0, z0)], Z_PAINT, (s, 0, 0))
    piv = Vector((0.0, y0, z0))
    R = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(S.boot_open), 4, 'X') @ Matrix.Translation(-piv)
    K.transform_kb(b, R)
    part(name, 'hinge', tuple(piv), axis=(1, 0, 0), rng=(0, 75), rest=S.boot_open, parent=NAME,
         note=f'the boot lid: hinged at its front edge, stands ajar {S.boot_open:.0f} deg (static)')


def refine():
    """ShiftCar 2.2's live-Blender touches: the roof crowned, lamps and grille set in (the crease: xs)"""
    k = KBS[NAME]
    bm = k.bm
    bm.normal_update()

    def roof():
        return [f for f in bm.faces if f.normal.z > 0.99 and all(abs(v.co.z - S.Z_ROOF) < 0.002 and abs(v.co.x) < S.WR - 0.03 for v in f.verts)]
    for xx in (0.0, -0.32, 0.32):
        g = set()
        for f in roof():
            g |= set(f.verts) | set(f.edges) | {f}
        bmesh.ops.bisect_plane(bm, geom=list(g), plane_co=(xx, 0, 0), plane_no=(1, 0, 0))
    for v in {v for f in roof() for v in f.verts}:
        t = min(1.0, abs(v.co.x) / (S.WR - 0.04))
        v.co.z += 0.03 * (1 - t * t)
    bm.faces.ensure_lookup_table()
    bm.normal_update()

    def on(y0, test):
        return [f for f in bm.faces if all(abs(v.co.y - y0) < 1e-4 for v in f.verts) and test(f.calc_center_median(), f[k.zl])]
    groups = []
    for sgn in (1, -1):
        groups.append((on(S.FRONT, lambda c, z, sg=sgn: round(z) == Z_HEAD and c.x * sg > 0), 0.02))
        groups.append((on(S.REAR, lambda c, z, sg=sgn: round(z) == Z_TAIL and c.x * sg > 0), -0.012))
    groups.append((on(S.FRONT, lambda c, z: round(z) == Z_GRILLE), 0.03))
    for faces, depth in groups:
        if not faces:
            continue
        r = bmesh.ops.inset_region(bm, faces=faces, thickness=0.01, depth=0.0, use_even_offset=True)
        for f in r['faces']:
            f[k.zl] = Z_CBLACK
        for v in {v for f in faces for v in f.verts}:
            v.co.y += depth
    bm.normal_update()


def lean_matrix():
    """the body settles onto the flat / missing corners: a plane through the four corner drops (least squares)"""
    pos = {'FL': (S.TRK, S.YFA), 'FR': (-S.TRK, S.YFA), 'RL': (S.TRK, S.YRA), 'RR': (-S.TRK, S.YRA)}
    import numpy as np
    A = np.array([[1.0, x, y] for x, y in pos.values()])
    b = np.array([S.drops.get(n, 0.0) for n in pos])
    c, ax, ay = np.linalg.lstsq(A, b, rcond=None)[0]
    return Matrix.Translation((0, 0, -float(c))) @ Matrix.Rotation(float(-ay), 4, 'X') @ Matrix.Rotation(float(ax), 4, 'Y')


def build_car(name):
    global M_LEAN
    configure(name)
    body()
    glasshouse()
    interior()
    if S.door_open:
        door()
    if S.boot_open:
        boot()
    refine()
    M_LEAN = lean_matrix()
    for n, k in list(KBS.items()):
        K.transform_kb(k, M_LEAN)
    for p in K.CONTRACT['parts'].values():
        if p['parent'] is not None:
            p['pivot'] = list(M_LEAN @ Vector(p['pivot']))
    k = KBS[NAME]
    pos = {'FL': (S.TRK, S.YFA, 1), 'FR': (-S.TRK, S.YFA, -1), 'RL': (S.TRK, S.YRA, 1), 'RR': (-S.TRK, S.YRA, -1)}
    for n, (x, y, s) in pos.items():
        kind = S.wheels.get(n, 'ok')
        if kind == 'missing':
            hub = M_LEAN @ Vector((x, y, S.RW))
            wheel(k, Vector((x, y, hub.z)), s, 'missing')
        elif kind == 'flat':
            wheel(k, Vector((x, y, S.RW - S.flat_drop)), s, 'flat')
        else:
            wheel(k, Vector((x, y, S.RW)), s)
    part(NAME, 'static', (0, 0, 0), note=f'{NAME} (root): origin = the ground between the axles; the front -y; the driver\'s side +x')
    BOXES.append(('Car_Body', NAME, (-0.92, 0.92, S.FRONT - 0.10, S.REAR + 0.10, 0.22, S.Z_ROOF + (0.08 if S.rails else 0.0)), None))
