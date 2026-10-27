"""forest_bunker geometry (TASKS C12, day 8: the bunker under the lake; concept 07_lakebunker), in the generator shed's
style. Four roots, each in its own frame (Blender: z up, metres; Unity (x, y, z) -> (-x, z, -y); sizes in bunker_spec):
  BunkerHangar    the hangar in the shore: a concrete hall 18 x 15 x 6.5 m behind a 34 m facade with splayed wing walls
                  and an apron to the ice; two steel gate leaves sliding in front of the facade on a floor rail under a
                  top guide (IX_HangarGate_L / _R, open onto the ice: the ice is the runway); inside pilasters, steel
                  beams, six pendant lamps, the side door up on a landing with steps (IX_HangarSideDoor, NOTAUSGANG: to
                  the underground part and the entrance), the back opening to the round door's vestibule (Link_BlastDoor),
                  the parking place of forest's UtilityPlane (Slot_Plane: the plane as it is, under PlaneTarp);
                  BunkerHangar_Glow - the lamps' bulbs (M_Bunker_Lamp / _Off)
  BlastDoor       "die Tür nach unten": the vestibule behind the hangar (consoles side, drain channel with a railing,
                  pipes, icicles) ending in a round blast door - hazard ring, six hydraulic bolts (IX_BlastDoor_Bolt_*),
                  hub and handwheel (IX_BlastDoor_Wheel), the hinge; the leaf IX_BlastDoor stays locked until act 3;
                  behind it a short tunnel and the first steps down (Link_Down); BlastDoor_Prints - wet boot prints to it
                  (the X11 sole); the door console (panel)
  BunkerEntrance  the way in by the hand on the lake: a concrete stair trench with railings down under a portal canopy;
                  in the landing floor the steel hatch (IX_BunkerHatch, its handwheel IX_BunkerHatch_Wheel) under a
                  sheet of ice (BunkerEntrance_Ice; over the hatch three chunks to knock off: Ice_Hatch_1..3); the shaft
                  with its ladder below (Link_Shaft at its foot)
  PlaneTarp       an olive canvas thrown over the plane's wing middle and cabin (bunker_tarp_sim.py), in the plane's own
                  frame: a child of the UtilityPlane root
Explicit-UV faces (signs, the console face) join their bodies at build time (MERGE); parts / sockets in each root's
frame (the contract); in the .blend the roots stand apart (DISPLAY) - the vestibule at its link behind the hangar."""
import math
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, box6, face, KBS, CONTRACT, transform_kb
from van2_kit import ZERO
import bunker_spec as S
import bunker_tex as BT

uv = BT.uv
TAU = 2 * math.pi
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
V3 = lambda x, y, z: Vector((x, y, z))
ROOTS = ['BunkerHangar', 'BlastDoor', 'BunkerEntrance', 'PlaneTarp']
DISPLAY = {'BunkerHangar': V3(0, 0, 0), 'BlastDoor': V3(0, S.HY_BACK, 0), 'BunkerEntrance': V3(-32, -6, 0),
           'PlaneTarp': V3(26, 6, 0)}
ROOT_OF, MERGE, BOXES, MASS = {}, {}, [], {}
LIGHTS = []                       # (name, parent, pos, dir, kind, colour, range, behaviour)
REMOVABLE, HITS = [], []
TARP_NPZ = '/home/claude/uaz/out/bunker_work/tarp.npz'
WARM = (1.0, 0.78, 0.52)

# Hangar atlas (2048): the shell
(Z_HWALL, Z_HFLOOR, Z_HCEIL, Z_HFAC, Z_HWING, Z_HAPRON, Z_HHIDE, Z_HPIL, Z_HLAND, Z_HSNOW, Z_HICE, Z_HREVEAL,
 Z_HSTUB) = range(800, 813)
# HangarParts atlas (1024): gates, steel, lamps, door, railings
(Z_GLEAF, Z_GLEAFIN, Z_GFRAME, Z_GHAZ, Z_GROLL, Z_BEAM, Z_SHADE, Z_SHADEIN, Z_ROD, Z_RAIL, Z_TRACK, Z_GUIDE, Z_DOOR,
 Z_DOORFR, Z_HANDLE, Z_CAGE, Z_LAMPB, Z_PLATE, Z_VENT) = range(830, 849)
# BlastDoor atlas (1024)
(Z_VWALL, Z_VFLOOR, Z_VCEIL, Z_VEND, Z_VHIDE, Z_RING, Z_LEAF, Z_LEAFRIM, Z_HUB, Z_CYL, Z_RODC, Z_DOG, Z_WHEEL, Z_HINGE,
 Z_TUN, Z_VOID, Z_PIPE, Z_BRACK, Z_TRAY, Z_CAB, Z_CHAN, Z_CHICE, Z_VRAIL, Z_VICE, Z_VLAMP, Z_SILL, Z_STEPD) = range(860, 887)
# Entrance atlas (1024)
(Z_EWALL, Z_ESTEP, Z_ETOP, Z_ECEIL, Z_EFLOOR, Z_ESHAFT, Z_ELADDER, Z_ERAIL, Z_EFRAME, Z_ELID, Z_EWHEEL, Z_EHINGE,
 Z_ESNOW, Z_EHIDE, Z_ELAMP, Z_EOUT) = range(900, 916)
# Tarp atlas (512)
Z_TARP, Z_TARPHEM = 930, 931


def part(name, *a, **kw):
    assert name not in CONTRACT['parts'], f'part {name} twice'
    K.part(name, *a, **kw)


def socket(name, *a, **kw):
    assert name not in CONTRACT['sockets'], f'socket {name} twice'
    K.socket(name, *a, **kw)


def reg(name, atlas, root, merge=None):
    ROOT_OF[name] = root
    if merge:
        MERGE[name] = merge
    return kb(name, atlas)


def hsh(i, s=0):
    x = math.sin(i * 12.9898 + s * 78.233) * 43758.5453
    return x - math.floor(x)


def rod(k, a, b, r, zone, seg=8, caps=True):
    k.cyl(Vector(a), Vector(b), r, zone, seg, caps=caps)


def bar(k, a, b, w, h, zone, up=(0, 0, 1)):
    k.strip([Vector(a), Vector(b)], Vector(up), w, h, zone)


def quad(k, pts, zone, out):
    face(k, [Vector(p) for p in pts], zone, out)


def railing(k, pts, zone, h=1.0, r=0.024, posts=None, mid=True):
    """pipe railing along a polyline of walking-surface points: posts (at the given indices, default every point), a top
    rail h above, a mid rail h / 2 above"""
    pts = [Vector(p) for p in pts]
    for i in (range(len(pts)) if posts is None else posts):
        rod(k, pts[i] - Z * 0.02, pts[i] + Z * (h + 0.01), r * 1.1, zone, 8)
    k.tube([p + Z * h for p in pts], r, zone, 8)
    if mid:
        k.tube([p + Z * (h * 0.5) for p in pts], r * 0.85, zone, 6)


def ibeam(k, a, b, depth, fw, web, ft, zone, up=Z):
    """I-section between the top-flange centre points a -> b (the section hangs below, `up` = the web's direction)"""
    a, b = Vector(a), Vector(b)
    t = (b - a).normalized()
    up = Vector(up).normalized()
    s = up.cross(t).normalized()                              # (t, s, up) right-handed: box_m keeps its normals out
    R = Matrix((t, s, up)).transposed()
    L = (b - a).length
    mid = (a + b) / 2
    k.box_m(mid - up * (ft / 2), (L, fw, ft), zone, R)
    k.box_m(mid - up * (depth - ft / 2), (L, fw, ft), zone, R)
    k.box_m(mid - up * (depth / 2), (L, web, depth - 2 * ft), zone, R)


def icicle(k, top, L, r, zone, seg=5):
    top = Vector(top)
    k.cyl(top, top - Z * L, r, zone, seg, r2=0.002)


def bulkhead(kb_body, kb_glow, c, n, zone_body, zone_cage, up=Z):
    """wall / ceiling bulkhead lamp: a round cast base, the glass dome (glow), a three-bar cage"""
    c, n = Vector(c), Vector(n).normalized()
    kb_body.lathe(c, n, [(0.0, 0.11), (0.035, 0.11), (0.05, 0.095)], zone_body, 12, cap0=True, cap1=True)
    kb_glow.lathe(c + n * 0.05, n, [(0.0, 0.085), (0.04, 0.078), (0.075, 0.05), (0.095, 0.0)], ZERO, 10, cap0=False,
                  cap1=False)
    u = up - n * up.dot(n)
    if u.length < 1e-3:
        u = X - n * X.dot(n)
    u.normalize()
    w = n.cross(u)
    for a in (0.0, TAU / 3, 2 * TAU / 3):
        d = u * math.cos(a) + w * math.sin(a)
        kb_body.tube([c + n * 0.05 + d * 0.095, c + n * 0.10 + d * 0.085, c + n * 0.145 + d * 0.03, c + n * 0.152],
                     0.007, zone_cage, 5, caps=False)
    kb_body.lathe(c + n * 0.05, n, [(0.0, 0.098), (0.012, 0.098)], zone_cage, 12, cap0=False, cap1=False)


def sign_plate(k_body, k_face, c, n, w, h, region, zone_plate, up=Z, t=0.012):
    """a screwed sign: a thin plate on the wall, its face (panel atlas) 1.5 mm proud"""
    c, n = Vector(c), Vector(n).normalized()
    u = Vector(up).cross(n).normalized()
    v = n.cross(u)
    R = Matrix((u, v, n)).transposed()
    k_body.box_m(c + n * (t / 2), (w + 0.02, h + 0.02, t), zone_plate, R)
    k_face.quad_uv(c + n * (t + 0.0015), n, w, h, uv(region), up=v)


def circle_rect_ring(k, c, r, rect, zone, out, seg=40, inner='circle'):
    """flat ring between a circle (centre c in the x-z plane, radius r) and an axis-aligned rectangle (x0, x1, z0, z1):
    inner='circle' -> the circle is the hole in the rectangle; 'rect' -> the rectangle is the hole in the disc; the
    rectangle's corners are on the rays so the edges stay straight; faces point along `out` (+-y)"""
    cx, y, cz = c
    x0, x1, z0, z1 = rect
    angs = [TAU * i / seg for i in range(seg)]
    angs += [math.atan2(zz - cz, xx - cx) % TAU for xx, zz in ((x0, z0), (x1, z0), (x1, z1), (x0, z1))]
    angs = sorted(set(round(a, 9) for a in angs))

    def on_rect(a):
        dx, dz = math.cos(a), math.sin(a)
        ts = []
        for xx in (x0, x1):
            if abs(dx) > 1e-9:
                t = (xx - cx) / dx
                if t > 0 and z0 - 1e-6 <= cz + dz * t <= z1 + 1e-6:
                    ts.append(t)
        for zz in (z0, z1):
            if abs(dz) > 1e-9:
                t = (zz - cz) / dz
                if t > 0 and x0 - 1e-6 <= cx + dx * t <= x1 + 1e-6:
                    ts.append(t)
        t = min(ts)
        return Vector((cx + dx * t, y, cz + dz * t))

    for i in range(len(angs)):
        a0, a1 = angs[i], angs[(i + 1) % len(angs)]
        c0 = Vector((cx + r * math.cos(a0), y, cz + r * math.sin(a0)))
        c1 = Vector((cx + r * math.cos(a1), y, cz + r * math.sin(a1)))
        quad(k, [c0, c1, on_rect(a1), on_rect(a0)], zone, out)


# ================================================================ BunkerHangar
def build_hangar():
    H = S.H
    xi, y0, y1, zc, zr, zp, zf = H['xi'], H['y_in0'], H['y_in1'], H['zc'], H['z_roof'], H['z_par'], H['z_foot']
    gx, gz, fx = H['gate_x'], H['gate_z'], H['fac_x']
    xo, yb = xi + H['t_side'], S.HY_BACK
    k = reg('BunkerHangar', 'Hangar', 'BunkerHangar')
    p = reg('BunkerHangar_Parts', 'HangarParts', 'BunkerHangar')
    pf = reg('BunkerHangar_Signs', 'panel', 'BunkerHangar', merge='BunkerHangar_Parts')
    gl = reg('BunkerHangar_Glow', 'lamp', 'BunkerHangar')
    # ---- floor, ceiling, roof
    quad(k, [(-gx, 0, 0), (gx, 0, 0), (gx, y0, 0), (-gx, y0, 0)], Z_HFLOOR, Z)
    quad(k, [(-xi, y0, 0), (xi, y0, 0), (xi, y1, 0), (-xi, y1, 0)], Z_HFLOOR, Z)
    bo, bh = H['back_open']
    quad(k, [(-bo, y1, 0), (bo, y1, 0), (bo, yb, 0), (-bo, yb, 0)], Z_HFLOOR, Z)
    quad(k, [(-xi, y0, zc), (xi, y0, zc), (xi, y1, zc), (-xi, y1, zc)], Z_HCEIL, -Z)
    quad(k, [(-xo, y0, zr), (xo, y0, zr), (xo, yb, zr), (-xo, yb, zr)], Z_HHIDE, Z)
    # ---- the front wall: facade face, the gate's reveals, the inner face, the parapet
    for xa, xb in ((-fx, -gx), (gx, fx)):
        quad(k, [(xa, 0, zf), (xb, 0, zf), (xb, 0, zp), (xa, 0, zp)], Z_HFAC, -Y)
    quad(k, [(-gx, 0, gz), (gx, 0, gz), (gx, 0, zp), (-gx, 0, zp)], Z_HFAC, -Y)
    for sx in (-1, 1):
        quad(k, [(sx * gx, 0, 0), (sx * gx, y0, 0), (sx * gx, y0, gz), (sx * gx, 0, gz)], Z_HREVEAL, -X * sx)
        quad(k, [(sx * gx, y0, 0), (sx * xi, y0, 0), (sx * xi, y0, zc), (sx * gx, y0, zc)], Z_HWALL, Y)
        quad(k, [(sx * xo, y0, zf), (sx * fx, y0, zf), (sx * fx, y0, zp), (sx * xo, y0, zp)], Z_HHIDE, Y)
    quad(k, [(-gx, 0, gz), (gx, 0, gz), (gx, y0, gz), (-gx, y0, gz)], Z_HREVEAL, -Z)
    quad(k, [(-gx, y0, gz), (gx, y0, gz), (gx, y0, zc), (-gx, y0, zc)], Z_HWALL, Y)
    quad(k, [(-fx, 0, zp), (fx, 0, zp), (fx, y0, zp), (-fx, y0, zp)], Z_HFAC, Z)
    quad(k, [(-xo, y0, zr), (xo, y0, zr), (xo, y0, zp), (-xo, y0, zp)], Z_HHIDE, Y)
    # ---- side walls (the side door's opening in the -x wall), outer faces
    dy0, dy1 = H['door_y'] - H['door_w'] / 2, H['door_y'] + H['door_w'] / 2
    dz0, dz1 = H['door_sill'], H['door_sill'] + H['door_h']
    for sx in (-1, 1):
        n = -X * sx
        if sx < 0:
            for ya, yb_, za, zb in ((y0, dy0, 0, zc), (dy0, dy1, 0, dz0), (dy0, dy1, dz1, zc), (dy1, y1, 0, zc)):
                quad(k, [(-xi, ya, za), (-xi, yb_, za), (-xi, yb_, zb), (-xi, ya, zb)], Z_HWALL, n)
        else:
            quad(k, [(xi, y0, 0), (xi, y1, 0), (xi, y1, zc), (xi, y0, zc)], Z_HWALL, n)
        quad(k, [(sx * xo, y0, zf), (sx * xo, yb, zf), (sx * xo, yb, zr), (sx * xo, y0, zr)], Z_HHIDE, X * sx)
    # the corridor stub behind the side door (dark; the underground part joins at Link_SideDoor)
    xs = -xo - 1.5
    quad(k, [(xs, dy0, dz0), (-xi, dy0, dz0), (-xi, dy1, dz0), (xs, dy1, dz0)], Z_HSTUB, Z)
    quad(k, [(xs, dy0, dz1), (-xi, dy0, dz1), (-xi, dy1, dz1), (xs, dy1, dz1)], Z_HSTUB, -Z)
    quad(k, [(xs, dy0, dz0), (-xi, dy0, dz0), (-xi, dy0, dz1), (xs, dy0, dz1)], Z_HSTUB, Y)
    quad(k, [(xs, dy1, dz0), (-xi, dy1, dz0), (-xi, dy1, dz1), (xs, dy1, dz1)], Z_HSTUB, -Y)
    quad(k, [(xs, dy0, dz0), (xs, dy1, dz0), (xs, dy1, dz1), (xs, dy0, dz1)], Z_HSTUB, X)
    # ---- back wall with the opening to the vestibule
    for xa, xb, za, zb in ((-xi, -bo, 0, zc), (bo, xi, 0, zc), (-bo, bo, bh, zc)):
        quad(k, [(xa, y1, za), (xb, y1, za), (xb, y1, zb), (xa, y1, zb)], Z_HWALL, -Y)
    for sx in (-1, 1):
        quad(k, [(sx * bo, y1, 0), (sx * bo, yb, 0), (sx * bo, yb, bh), (sx * bo, y1, bh)], Z_HREVEAL, -X * sx)
    quad(k, [(-bo, y1, bh), (bo, y1, bh), (bo, yb, bh), (-bo, yb, bh)], Z_HREVEAL, -Z)
    for xa, xb, za, zb in ((-xo, -bo, zf, zr), (bo, xo, zf, zr), (-bo, bo, bh, zr)):
        quad(k, [(xa, yb, za), (xb, yb, za), (xb, yb, zb), (xa, yb, zb)], Z_HHIDE, Y)
    # ---- pilasters under the beams
    for yp in H['pil_y']:
        w2, d = H['pil_w'] / 2, H['pil_d']
        for sx in (-1, 1):
            xa, xb = sx * xi, sx * (xi - d)
            quad(k, [(xb, yp - w2, 0), (xb, yp + w2, 0), (xb, yp + w2, zc), (xb, yp - w2, zc)], Z_HPIL, -X * sx)
            quad(k, [(xa, yp - w2, 0), (xb, yp - w2, 0), (xb, yp - w2, zc), (xa, yp - w2, zc)], Z_HPIL, -Y)
            quad(k, [(xa, yp + w2, 0), (xb, yp + w2, 0), (xb, yp + w2, zc), (xa, yp + w2, zc)], Z_HPIL, Y)
    # ---- wing walls: splayed toward the lake, the tops falling to 1 m; their snow
    a = math.radians(H['wing_ang'])
    for sx in (-1, 1):
        d = Vector((sx * math.sin(a), -math.cos(a), 0.0))
        n_in = Vector((-sx * math.cos(a), -math.sin(a), 0.0))
        A = Vector((sx * fx, 0.0, 0.0)) - d * 0.3
        B = Vector((sx * fx, 0.0, 0.0)) + d * H['wing_len']
        t = -n_in * H['wing_t']
        za, zb = zp, H['wing_z_end']
        quad(k, [A + Z * zf, B + Z * zf, B + Z * zb, A + Z * za], Z_HWING, n_in)
        quad(k, [A + Z * za, B + Z * zb, B + t + Z * zb, A + t + Z * za], Z_HWING, Z)
        quad(k, [B + Z * zf, B + t + Z * zf, B + t + Z * zb, B + Z * zb], Z_HWING, d)
        quad(k, [A + t + Z * zf, B + t + Z * zf, B + t + Z * zb, A + t + Z * za], Z_HHIDE, -n_in)
        sn = []
        for i in range(9):
            q = i / 8
            P0 = A.lerp(B, q) + Z * (za + (zb - za) * q)
            sn.append(P0 - n_in * (H['wing_t'] / 2))
        k.strip([s_ + Z * 0.05 for s_ in sn], Z, H['wing_t'] + 0.10, 0.12, Z_HSNOW)
    # ---- apron: falls 0.2 m to the ice; its front edge
    ax, ay, ad = H['apron_x'] + 3.2, H['apron_y'], H['apron_drop']
    quad(k, [(-ax, ay, -ad), (ax, ay, -ad), (ax, 0, 0), (-ax, 0, 0)], Z_HAPRON, Z)
    quad(k, [(-ax, ay, -ad - 0.4), (ax, ay, -ad - 0.4), (ax, ay, -ad), (-ax, ay, -ad)], Z_HAPRON, -Y)
    # ---- snow: on the parapet, on the top guide; icicles at the parapet, the guide, inside the lintel
    prof = [(-0.07, zp), (y0 + 0.05, zp), (y0 + 0.05, zp + 0.13), (y0 - 0.25, zp + 0.21), (0.10, zp + 0.20), (-0.07, zp + 0.10)]
    K.prism_x(k, prof, -fx - 0.05, fx + 0.05, Z_HSNOW, Z_HSNOW)
    g0, g1 = H['guide_z']
    k.box(-fx + 0.05, fx - 0.05, -0.70, -0.20, g1, g1 + 0.07, Z_HSNOW)
    for i in range(48):
        x = -fx + 0.4 + i * (2 * fx - 0.8) / 47 + (hsh(i, 1) - 0.5) * 0.3
        L = 0.15 + 0.55 * hsh(i, 2) ** 1.5
        icicle(k, (x, -0.05, zp + 0.04), L, 0.03 + 0.03 * hsh(i, 3), Z_HICE)
    for i in range(30):
        x = -fx + 0.6 + i * (2 * fx - 1.2) / 29 + (hsh(i, 4) - 0.5) * 0.3
        if hsh(i, 5) > 0.55:
            icicle(k, (x, -0.69, g0 + 0.01), 0.08 + 0.18 * hsh(i, 6), 0.022, Z_HICE)
    for i in range(22):
        x = -gx + 0.4 + i * (2 * gx - 0.8) / 21 + (hsh(i, 7) - 0.5) * 0.25
        icicle(k, (x, y0 - 0.06, gz + 0.01), 0.10 + 0.32 * hsh(i, 8) ** 1.3, 0.022 + 0.02 * hsh(i, 9), Z_HICE)
    # ---- landing and steps up to the side door
    lx = -xi + H['land_x']
    la, lb = H['land_y']
    k.box(-xi, lx, la, lb, 0.0, dz0, Z_HLAND)
    sa, sb = H['step_w']
    for i in range(H['steps'] - 1):
        xa_, xb_ = lx + H['run'] * i, lx + H['run'] * (i + 1)
        k.box(xa_ - 0.01, xb_, sa, sb, 0.0, dz0 - H['rise'] * (i + 1), Z_HLAND)
    x_end = lx + H['run'] * (H['steps'] - 1)
    for yy in (la + 0.03, lb - 0.03):
        railing(p, [(-xi + 0.05, yy, dz0), (lx - 0.02, yy, dz0), (x_end - 0.10, yy, H['rise']), (x_end + 0.18, yy, 0.0)],
                Z_RAIL, posts=[0, 1, 3])
    # ---- the side door: octagonal steel frame on the wall, the leaf (IX_HangarSideDoor), the lamp and sign over it
    ch = 0.20
    def octo(y_a, y_b, z_a, z_b, c):
        return [(y_a + c, z_a), (y_b - c, z_a), (y_b, z_a + c), (y_b, z_b - c), (y_b - c, z_b), (y_a + c, z_b), (y_a, z_b - c),
                (y_a, z_a + c)]
    inner = octo(dy0, dy1, dz0, dz1, ch)
    outer = octo(dy0 - 0.13, dy1 + 0.13, dz0 - 0.05, dz1 + 0.13, ch + 0.06)
    xf = -xi + 0.06
    for i in range(8):
        j = (i + 1) % 8
        (ya, za), (yb2, zb2) = inner[i], inner[j]
        (Ya, Za), (Yb, Zb) = outer[i], outer[j]
        quad(p, [(xf, ya, za), (xf, yb2, zb2), (xf, Yb, Zb), (xf, Ya, Za)], Z_DOORFR, X)
        e = Vector((0, zb2 - za, -(yb2 - ya)))                       # in-plane outward normal of the inner edge
        quad(p, [(xf, ya, za), (xf, yb2, zb2), (-xo, yb2, zb2), (-xo, ya, za)], Z_DOORFR, -e)
        E = Vector((0, Zb - Za, -(Yb - Ya)))
        quad(p, [(xf, Ya, Za), (xf, Yb, Zb), (-xi, Yb, Zb), (-xi, Ya, Za)], Z_DOORFR, E)
    dl = reg('IX_HangarSideDoor', 'HangarParts', 'BunkerHangar')
    lin_ = octo(dy0 + 0.012, dy1 - 0.012, dz0 + 0.012, dz1 - 0.012, ch)
    K.prism_x(dl, [(yy, zz) for yy, zz in lin_], -xi - 0.02, -xi + 0.04, Z_DOOR, Z_DOOR)
    for zz in (dz0 + 0.55, dz0 + 1.55):
        dl.box(-xi + 0.04, -xi + 0.075, dy0 + 0.10, dy1 - 0.10, zz - 0.05, zz + 0.05, Z_DOOR)
    hz = dz0 + 1.05
    dl.box(-xi + 0.04, -xi + 0.08, dy1 - 0.20, dy1 - 0.12, hz - 0.06, hz + 0.06, Z_HANDLE)     # the dog lever
    bar(dl, (-xi + 0.10, dy1 - 0.16, hz), (-xi + 0.10, dy1 - 0.52, hz - 0.12), 0.03, 0.03, Z_HANDLE, up=X)
    rod(dl, (-xi + 0.04, dy1 - 0.16, hz), (-xi + 0.11, dy1 - 0.16, hz), 0.02, Z_HANDLE, 8)
    for zz in (dz0 + 0.35, dz1 - 0.35):                                   # hinge knuckles on the front edge
        rod(dl, (-xi + 0.06, dy0 + 0.01, zz - 0.10), (-xi + 0.06, dy0 + 0.01, zz + 0.10), 0.03, Z_HANDLE, 8)
    part('IX_HangarSideDoor', 'hinge', (-xi + 0.06, dy0 + 0.01, dz0), axis=(0, 0, -1), rng=(0, 95), parent='BunkerHangar',
         states=['closed', 'open'], note='the side door up on the landing (NOTAUSGANG): to the underground part and the '
                                         'entrance shaft (Link_SideDoor); opens into the hall, hinge on its front edge')
    bulkhead(p, gl, (-xi + 0.01, H['door_y'], dz1 + 0.32), X, Z_LAMPB, Z_CAGE)
    sign_plate(p, pf, (-xi + 0.005, H['door_y'], dz1 + 0.70), X, 0.70, 0.30, 'notaus', Z_PLATE)
    LIGHTS.append(('Light_HangarDoor', 'BunkerHangar', (-xi + 0.20, H['door_y'], dz1 + 0.30), None, 'point', WARM, 6.0,
                   'steady'))
    sign_plate(p, pf, (xi - 0.005, 2.2, 1.95), -X, 0.40, 0.55, 'rauchen', Z_PLATE)
    # ---- the gate: the floor rail, the top guide on brackets, two leaves (IX_HangarGate_L / _R)
    # (the long members in short lengths: one 33 m strip would cap the whole atlas' pixel density)
    xs_ = np.linspace(-fx + 0.1, fx - 0.1, 9)
    for xa_, xb_ in zip(xs_[:-1], xs_[1:]):
        p.box(xa_, xb_, H['rail_y'] - 0.04, H['rail_y'] + 0.04, -0.03, 0.03, Z_TRACK)
    xs_ = [-fx + 0.05] + [-fx + 0.4 + i * (2 * fx - 0.8) / 14 for i in range(1, 14)] + [fx - 0.05]
    for xa_, xb_ in zip(xs_[:-1], xs_[1:]):
        p.box(xa_, xb_, -0.68, -0.22, g0, g1, Z_GUIDE)
    for i in range(15):
        x = -fx + 0.4 + i * (2 * fx - 0.8) / 14
        p.box(x - 0.07, x + 0.07, -0.22, 0.0, g0 + 0.04, g1 - 0.04, Z_GUIDE)
    lw, lz0, lz1, ly0, ly1 = H['leaf_w'], H['leaf_z0'], H['leaf_z1'], H['leaf_y0'], H['leaf_y1']
    for side, sx in (('L', -1), ('R', 1)):
        name = f'IX_HangarGate_{side}'
        L = reg(name, 'HangarParts', 'BunkerHangar')
        xa_, xb_ = (-lw, 0.0) if sx < 0 else (0.0, lw)
        xm = 0.0                                                          # the meeting edge
        st = 0.20
        outer_x = xa_ if sx < 0 else xb_
        o0, o1 = (outer_x, outer_x + st) if sx < 0 else (outer_x - st, outer_x)
        m0, m1 = (xm - st, xm) if sx < 0 else (xm, xm + st)
        box6(L, (o0, ly0, lz0), (o1, ly1, lz1), Z_GFRAME)
        box6(L, (m0, ly0, lz0), (m1, ly1, lz1), {'*': Z_GFRAME, '-y': Z_GHAZ, '+y': Z_GHAZ})
        ia, ib = (o1, m0) if sx < 0 else (m1, o0)
        box6(L, (ia, ly0, lz0), (ib, ly1, lz0 + 0.20), Z_GFRAME)
        box6(L, (ia, ly0, lz1 - 0.20), (ib, ly1, lz1), Z_GFRAME)
        quad(L, [(ia, ly0 + 0.02, lz0 + 0.2), (ib, ly0 + 0.02, lz0 + 0.2), (ib, ly0 + 0.02, lz1 - 0.2), (ia, ly0 + 0.02, lz1 - 0.2)],
             Z_GLEAF, -Y)
        quad(L, [(ia, ly1 - 0.02, lz0 + 0.2), (ib, ly1 - 0.02, lz0 + 0.2), (ib, ly1 - 0.02, lz1 - 0.2), (ia, ly1 - 0.02, lz1 - 0.2)],
             Z_GLEAFIN, Y)
        for zz in (1.55, 2.75, 3.95):
            L.box(ia, ib, ly0 - 0.02, ly0 + 0.02, zz - 0.06, zz + 0.06, Z_GFRAME)
            L.box(ia, ib, ly1 - 0.02, ly1 + 0.02, zz - 0.05, zz + 0.05, Z_GFRAME)
        for xr in (min(xa_, xb_) + 0.65, max(xa_, xb_) - 0.65):
            L.box(xr - 0.24, xr + 0.24, ly0 - 0.03, ly1 + 0.03, 0.0, lz0 + 0.22, Z_GROLL)
            rod(L, (xr, ly0 - 0.035, 0.11), (xr, ly1 + 0.035, 0.11), 0.10, Z_GROLL, 10)
            L.box(xr - 0.10, xr + 0.10, -0.52, -0.38, lz1, g0 + 0.10, Z_GROLL)
        hx = xm + sx * 0.10
        for yy, oy in ((ly0 - 0.13, -1), (ly1 + 0.13, 1)):                # pull handles, out and in
            rod(L, (hx, yy, 1.0), (hx, yy, 1.8), 0.022, Z_HANDLE, 8)
            for zz in (1.05, 1.75):
                rod(L, (hx, yy, zz), (hx, (ly0 if oy < 0 else ly1), zz), 0.016, Z_HANDLE, 6)
        piv = ((xa_ + xb_) / 2, H['rail_y'], lz0)
        part(name, 'slide', piv, axis=(sx, 0, 0), rng=(0, lw), unit='m', parent='BunkerHangar', states=['closed', 'open'],
             note=f'gate leaf {side}: rolls on the floor rail under the top guide, out in front of the facade; open = slid '
                  f'{lw} m aside (the opening 16 m: the plane taxis out onto the ice)')
    # ---- beams: transverse I-beams over the pilasters, three lighter ones lengthwise
    for yp in H['pil_y']:
        for xa_, xb_ in ((-xi, -4.5), (-4.5, 0.0), (0.0, 4.5), (4.5, xi)):
            ibeam(p, (xa_, yp, zc), (xb_, yp, zc), H['beam_d'], H['beam_f'], 0.04, 0.03, Z_BEAM)
    for xb2 in (-4.5, 0.0, 4.5):
        ys_ = np.linspace(y0, y1, 6)
        for ya_, yb_ in zip(ys_[:-1], ys_[1:]):
            ibeam(p, (xb2, ya_, zc - 0.002), (xb2, yb_, zc - 0.002), 0.35, 0.20, 0.03, 0.025, Z_BEAM)
    # ---- six pendant lamps under the lengthwise beams
    lz = H['lamp_z']
    for i, (x, y) in enumerate(H['lamps']):
        rod(p, (x, y, zc - 0.35), (x, y, lz + 0.30), 0.012, Z_ROD, 6, caps=False)
        p.lathe(V3(x, y, lz), Z, [(0.0, 0.30), (0.02, 0.29), (0.16, 0.16), (0.25, 0.085), (0.30, 0.06)], Z_SHADE, 14,
                cap0=False, cap1=True)
        p.lathe(V3(x, y, lz), Z, [(0.25, 0.08), (0.16, 0.155), (0.02, 0.285)], Z_SHADEIN, 14, cap0=False, cap1=False)
        p.lathe(V3(x, y, lz + 0.30), Z, [(0.0, 0.05), (0.05, 0.03), (0.07, 0.0)], Z_ROD, 8, cap0=True, cap1=False)
        gl.lathe(V3(x, y, lz + 0.05), Z, [(0.0, 0.0), (0.02, 0.05), (0.08, 0.065), (0.14, 0.04), (0.17, 0.0)], ZERO, 8,
                 cap0=False, cap1=False)
        LIGHTS.append((f'Light_Hangar_{i + 1}', 'BunkerHangar', (x, y, lz + 0.08), (0, 0, -1), 'spot', WARM, 16.0, 'steady'))
    bulkhead(p, gl, (0.0, y1 - 0.01, bh + 0.35), -Y, Z_LAMPB, Z_CAGE)
    LIGHTS.append(('Light_HangarBack', 'BunkerHangar', (0.0, y1 - 0.20, bh + 0.32), None, 'point', WARM, 7.0, 'steady'))
    # ---- vents high in the back wall
    for xv in (-6.0, 6.0):
        p.box(xv - 0.55, xv + 0.55, y1 - 0.06, y1, 5.0, 5.8, Z_VENT)
        for j in range(5):
            zz = 5.08 + j * 0.15
            bar(p, (xv - 0.50, y1 - 0.09, zz), (xv + 0.50, y1 - 0.09, zz), 0.10, 0.02, Z_VENT, up=V3(0, -0.5, 1).normalized())
    part('BunkerHangar', 'static', (0, 0, 0),
         note='the hangar (root): origin on the floor in the middle of the gate line (the facade\'s front face); the gate '
              'faces -y (Unity +Z): set it into the shore so the apron meets the lake ice; the hall runs 16.4 m into the '
              'bank, its roof 7.3 m up (the terrain over it), the wing walls hold the bank')
    part('BunkerHangar_Parts', 'static', (0, 0, 0), parent='BunkerHangar',
         note='steel and fittings: beams, lamp bodies, railings, the side door frame, the gate rail and top guide, vents, '
              'signs (panel)')
    part('BunkerHangar_Glow', 'static', (0, 0, 0), parent='BunkerHangar', states=['off', 'on'],
         note='the lamps\' bulbs and glasses: M_Bunker_Lamp_Off / M_Bunker_Lamp (with the lights in bunker_lights.json)')
    # ---- sockets
    M = S.plane_park_matrix()
    socket('Slot_Plane', M.translation, 'plane', parent='BunkerHangar', euler=(-S.PLANE['pitch'], 0.0, 0.0),
           note='forest UtilityPlane (v13, the WinterKit installed) parked: its root here, rotated (Euler XYZ, deg) nose-up '
                'so the tail wheel rests on the floor; the nose to the gate; PlaneTarp goes on it (its child)')
    for i, (x, y, yaw) in enumerate(((7.6, 4.6, 90), (7.6, 6.2, 90), (7.4, 13.8, 90), (-7.4, 13.8, -90), (-7.6, 5.4, -90))):
        socket(f'Slot_Dressing_{i + 1}', (x, y, 0.0), 'dressing', parent='BunkerHangar', yaw=yaw,
               note='a place on the floor for the plane package\'s cargo cases / stepladder / kit bags, or crates')
    socket('Link_BlastDoor', (0.0, yb, 0.0), 'link', parent='BunkerHangar',
           note='the back opening (5.0 x 4.6 m): BlastDoor\'s origin goes here, no rotation')
    socket('Link_SideDoor', (xs, H['door_y'], dz0), 'link', parent='BunkerHangar',
           note='the end of the corridor stub behind the side door (1.2 x 2.1 m, floor 1.2 m up): the underground part to '
                'the entrance shaft continues here, along -x')
    # ---- colliders (root frame)
    B = BOXES.append
    B(('Hangar_Floor', 'BunkerHangar', (-xo, xo, 0.0, yb, -0.4, 0.0), None))
    B(('Hangar_Apron', 'BunkerHangar', (-ax, ax, ay, 0.0, -0.6, -0.1), (math.degrees(math.atan2(ad, -ay)), 0, 0)))
    B(('Hangar_FrontL', 'BunkerHangar', (-fx, -gx, 0.0, y0, zf, zp), None))
    B(('Hangar_FrontR', 'BunkerHangar', (gx, fx, 0.0, y0, zf, zp), None))
    B(('Hangar_Lintel', 'BunkerHangar', (-gx, gx, 0.0, y0, gz, zp), None))
    B(('Hangar_WallR', 'BunkerHangar', (xi, xo, y0, yb, 0.0, zr), None))
    B(('Hangar_WallL_Front', 'BunkerHangar', (-xo, -xi, y0, dy0, 0.0, zr), None))
    B(('Hangar_WallL_Back', 'BunkerHangar', (-xo, -xi, dy1, yb, 0.0, zr), None))
    B(('Hangar_WallL_Sill', 'BunkerHangar', (-xo, -xi, dy0, dy1, 0.0, dz0), None))
    B(('Hangar_WallL_Head', 'BunkerHangar', (-xo, -xi, dy0, dy1, dz1, zr), None))
    B(('Hangar_BackL', 'BunkerHangar', (-xo, -bo, y1, yb, 0.0, zr), None))
    B(('Hangar_BackR', 'BunkerHangar', (bo, xo, y1, yb, 0.0, zr), None))
    B(('Hangar_BackLintel', 'BunkerHangar', (-bo, bo, y1, yb, bh, zr), None))
    B(('Hangar_Roof', 'BunkerHangar', (-xo, xo, y0, yb, zc, zr), None))
    for i, yp in enumerate(H['pil_y']):
        for sx in (-1, 1):
            xa, xb = sorted((sx * xi, sx * (xi - H['pil_d'])))
            B((f'Hangar_Pilaster_{i + 1}{"L" if sx < 0 else "R"}', 'BunkerHangar', (xa, xb, yp - 0.25, yp + 0.25, 0, zc), None))
    for sx, nm in ((-1, 'L'), (1, 'R')):
        ang = math.radians(H['wing_ang'])
        d = Vector((sx * math.sin(ang), -math.cos(ang), 0.0))
        n_out = Vector((sx * math.cos(ang), math.sin(ang), 0.0))
        c = Vector((sx * fx, 0, 0)) + d * (H['wing_len'] / 2 - 0.15) + n_out * (H['wing_t'] / 2)
        Lw = H['wing_len'] + 0.3
        B((f'Hangar_Wing{nm}', 'BunkerHangar', (c.x - H['wing_t'] / 2, c.x + H['wing_t'] / 2, c.y - Lw / 2, c.y + Lw / 2, zf, zp),
           (0, 0, sx * H['wing_ang'])))
    B(('Hangar_Landing', 'BunkerHangar', (-xi, lx, la, lb, 0.0, dz0), None))
    run = H['run'] * (H['steps'] - 1)
    slope = math.atan2(dz0, run + 0.28)
    cxs = lx + (run + 0.28) / 2
    hyp = math.hypot(run + 0.28, dz0)
    B(('Hangar_Steps', 'BunkerHangar', (cxs - hyp / 2, cxs + hyp / 2, sa, sb, dz0 / 2 - 0.15, dz0 / 2 + 0.0),
       (0, math.degrees(slope), 0)))
    for yy in (la + 0.03, lb - 0.03):
        B((f'Hangar_StairRail_{"A" if yy < 2 else "B"}', 'BunkerHangar', (-xi, x_end + 0.2, yy - 0.03, yy + 0.03, 0.0, dz0 + 1.0), None))
    for side in ('L', 'R'):
        nm = f'IX_HangarGate_{side}'
        xa_, xb_ = (-lw, 0.0) if side == 'L' else (0.0, lw)
        B((f'HangarGate_{side}', nm, (xa_, xb_, ly0 - 0.03, ly1 + 0.03, 0.0, lz1), None))
    B(('HangarSideDoor', 'IX_HangarSideDoor', (-xi - 0.02, -xi + 0.08, dy0, dy1, dz0, dz1), None))
    MASS['IX_HangarGate_L'] = MASS['IX_HangarGate_R'] = 2400.0
    MASS['IX_HangarSideDoor'] = 160.0


# ================================================================ BlastDoor
def build_blastdoor():
    Vv = S.V
    xi, zc, L, t = Vv['xi'], Vv['zc'], Vv['L'], Vv['t']
    xo = xi + t
    cz, lr, lt = Vv['door_c'], Vv['leaf_r'], Vv['leaf_t']
    r0, r1 = Vv['ring_r']
    yr = L - Vv['ring_t']                                     # the ring's face
    yf = L - Vv['leaf_front']                                 # the leaf's face
    yback = yf + lt
    cw = Vv['chan_w']
    xc = xi - cw
    k = reg('BlastDoor', 'BlastDoor', 'BlastDoor')
    kf = reg('BlastDoor_Signs', 'panel', 'BlastDoor', merge='BlastDoor')
    gl = reg('BlastDoor_Glow', 'lamp', 'BlastDoor')
    # ---- shell: floor with the channel, walls, ceiling, hidden outside
    quad(k, [(-xi, 0, 0), (xc, 0, 0), (xc, L, 0), (-xi, L, 0)], Z_VFLOOR, Z)
    cd = Vv['chan_d']
    quad(k, [(xc, 0.05, -cd), (xi, 0.05, -cd), (xi, L, -cd), (xc, L, -cd)], Z_CHAN, Z)
    quad(k, [(xc, 0.05, -cd), (xc, L, -cd), (xc, L, 0), (xc, 0.05, 0)], Z_CHAN, X)
    quad(k, [(xc, 0.05, -cd), (xi, 0.05, -cd), (xi, 0.05, 0), (xc, 0.05, 0)], Z_CHAN, Y)
    quad(k, [(xc, 0.05, -cd + 0.13), (xi, 0.05, -cd + 0.13), (xi, L, -cd + 0.13), (xc, L, -cd + 0.13)], Z_CHICE, Z)
    quad(k, [(-xi, 0, 0), (-xi, L, 0), (-xi, L, zc), (-xi, 0, zc)], Z_VWALL, X)
    quad(k, [(xi, 0, -cd), (xi, L, -cd), (xi, L, zc), (xi, 0, zc)], Z_VWALL, -X)
    quad(k, [(-xi, 0, zc), (xi, 0, zc), (xi, L, zc), (-xi, L, zc)], Z_VCEIL, -Z)
    for sx in (-1, 1):
        quad(k, [(sx * xo, 0, -0.3), (sx * xo, L + t, -0.3), (sx * xo, L + t, zc + t), (sx * xo, 0, zc + t)], Z_VHIDE, X * sx)
    quad(k, [(-xo, 0, zc + t), (xo, 0, zc + t), (xo, L + t, zc + t), (-xo, L + t, zc + t)], Z_VHIDE, Z)
    # ---- the end wall round the ring, the ring (hazard face), its seat
    circle_rect_ring(k, (0.0, L, cz), r1, (-xi, xi, 0.0, zc), Z_VEND, -Y, seg=40)
    k.lathe(V3(0, yr, cz), Y, [(0.0, r0), (0.0, r1)], Z_RING, 40, cap0=False, cap1=False)      # (flat annulus)
    k.lathe(V3(0, yr, cz), Y, [(0.0, r1), (L - yr, r1)], Z_RING, 40, cap0=False, cap1=False)               # outer band
    k.lathe(V3(0, yr, cz), Y, [(yback + 0.05 - yr, r0), (0.0, r0)], Z_RING, 40, cap0=False, cap1=False)    # the seat (in)
    # ---- behind the door: the short round tunnel, its back plate, the passage and the first steps down
    y_t1 = yback + 0.65
    k.lathe(V3(0, yback + 0.05, cz), Y, [(y_t1 - yback - 0.05, r0), (0.0, r0)], Z_TUN, 32, cap0=False, cap1=False)
    zt = 0.55                                                 # the tunnel's floor
    hw = math.sqrt(r0 ** 2 - (cz - zt) ** 2)
    quad(k, [(-hw, yback + 0.05, zt), (hw, yback + 0.05, zt), (hw, y_t1, zt), (-hw, y_t1, zt)], Z_TUN, Z)
    pw, ph = 0.70, 2.95
    circle_rect_ring(k, (0.0, y_t1, cz), r0, (-pw, pw, zt, ph), Z_TUN, -Y, seg=32)
    yy = y_t1
    zz = zt
    prof = [(yy, zz)]
    yy += 0.30
    prof.append((yy, zz))
    for i in range(Vv['steps'] + 1):
        zz -= 0.20
        prof.append((yy, zz))
        yy += 0.30
        prof.append((yy, zz))
    y_end = yy + 0.40
    prof.append((y_end, zz))
    for (ya, za), (yb2, zb2) in zip(prof[:-1], prof[1:]):
        if abs(za - zb2) < 1e-6:
            quad(k, [(-pw, ya, za), (pw, ya, za), (pw, yb2, za), (-pw, yb2, za)], Z_STEPD, Z)
        else:
            quad(k, [(-pw, ya, za), (pw, ya, za), (pw, ya, zb2), (-pw, ya, zb2)], Z_STEPD, -Y)
    for sx in (-1, 1):
        quad(k, [(sx * pw, y_t1, zz), (sx * pw, y_end, zz), (sx * pw, y_end, ph), (sx * pw, y_t1, ph)], Z_TUN, -X * sx)
    quad(k, [(-pw, y_t1, ph), (pw, y_t1, ph), (pw, y_end, ph), (-pw, y_end, ph)], Z_TUN, -Z)
    quad(k, [(-pw, y_end, zz), (pw, y_end, zz), (pw, y_end, ph), (-pw, y_end, ph)], Z_VOID, -Y)
    z_down = zz
    # the step block in front of the sill
    k.box(-0.65, 0.65, yf - 0.62, yf - 0.06, 0.0, 0.27, Z_SILL)
    # ---- the hinge (static half): pin, knuckles and brackets on the wall
    hx, hy = Vv['hinge_x'], L + Vv['hinge_dy']
    rod(k, (hx, hy, cz - 1.45), (hx, hy, cz + 1.45), 0.055, Z_HINGE, 10)
    for za, zb in ((cz + 1.12, cz + 1.40), (cz - 1.40, cz - 1.12), (cz - 0.12, cz + 0.12)):
        rod(k, (hx, hy, za), (hx, hy, zb), 0.11, Z_HINGE, 12)
        k.box(hx - 0.12, hx + 0.12, hy, L, za + 0.02, zb - 0.02, Z_HINGE)
    # ---- the leaf (IX_BlastDoor): front disc with a chamfer, the rim, the back; hub, cylinders, hinge arms
    D = reg('IX_BlastDoor', 'BlastDoor', 'BlastDoor')
    c = V3(0, yf, cz)
    D.lathe(c, Y, [(0.0, 0.0), (0.0, lr - 0.08), (0.06, lr)], Z_LEAF, 40, cap0=False, cap1=False)
    D.lathe(c, Y, [(0.06, lr), (lt, lr)], Z_LEAFRIM, 40, cap0=False, cap1=False)
    D.lathe(V3(0, yback, cz), Y, [(0.0, lr), (0.0, 0.0)], Z_LEAF, 40, cap0=False, cap1=False)
    D.lathe(c, -Y, [(0.0, 0.46), (0.07, 0.46), (0.10, 0.40), (0.17, 0.40), (0.19, 0.24), (0.25, 0.22), (0.27, 0.0)], Z_HUB, 20,
            cap0=False, cap1=False)
    for i in range(Vv['arms']):
        a = math.pi / 2 + i * TAU / Vv['arms']
        u = V3(math.cos(a), 0, math.sin(a))
        dep = -Y * 0.09
        rod(D, c + u * 0.48 + dep, c + u * 1.02 + dep, 0.075, Z_CYL, 10)
        rod(D, c + u * 1.00 + dep, c + u * 1.26 + dep, 0.036, Z_RODC, 8)
        w = Y.cross(u)
        R = Matrix((u, w, Y)).transposed()
        D.box_m(c + u * 0.52 + dep, (0.10, 0.22, 0.16), Z_CYL, R)                    # the cylinder's clevis at the hub
        bn = f'IX_BlastDoor_Bolt_{i + 1}'
        Bk = reg(bn, 'BlastDoor', 'BlastDoor')
        Bk.box_m(c + u * 1.47 - Y * 0.08, (0.46, 0.24, 0.12), Z_DOG, R)
        Bk.box_m(c + u * 1.30 - Y * 0.09, (0.12, 0.12, 0.14), Z_DOG, R)
        part(bn, 'slide', c + u * 1.47 - Y * 0.08, axis=tuple(-u), rng=(0, 0.16), unit='m', parent='IX_BlastDoor',
             states=['locked', 'unlocked'], locked=True,
             note=f'locking bolt {i + 1}: out over the ring = locked; slides 0.16 m in (to the hub) before the leaf can '
                  f'swing (act 3)')
    for zz in (cz + 0.95, cz - 0.95):                       # the hinge arms and the leaf's knuckles
        D.box(hx, -1.05, hy - 0.08, hy + 0.08, zz - 0.13, zz + 0.13, Z_HINGE)
        D.box(-1.25, -0.95, hy - 0.08, yf, zz - 0.13, zz + 0.13, Z_HINGE)
        rod(D, (hx, hy, zz - 0.15), (hx, hy, zz + 0.15), 0.11, Z_HINGE, 12)
    part('IX_BlastDoor', 'hinge', (hx, hy, cz), axis=(0, 0, -1), rng=(0, 90), parent='BlastDoor',
         states=['locked', 'open'], locked=True,
         note='the round blast door ("die Tür nach unten"): seen on day 8, opened only in act 3; first the wheel turns and '
              'the six bolts slide in, then the leaf swings out into the vestibule about the hinge on its left')
    W = reg('IX_BlastDoor_Wheel', 'BlastDoor', 'BlastDoor')
    wc = c - Y * 0.30
    wr = Vv['wheel_r']
    ring_pts = [wc + V3(math.cos(TAU * i / 18), 0, math.sin(TAU * i / 18)) * wr for i in range(18)]
    W.tube(ring_pts + [ring_pts[0]], 0.026, Z_WHEEL, 6, caps=False)
    for i in range(6):
        a = i * TAU / 6 + 0.26
        u = V3(math.cos(a), 0, math.sin(a))
        rod(W, wc + u * 0.06, wc + u * (wr - 0.01), 0.018, Z_WHEEL, 6)
    W.lathe(wc + Y * 0.04, -Y, [(0.0, 0.09), (0.08, 0.09), (0.10, 0.0)], Z_WHEEL, 12, cap0=True, cap1=False)
    part('IX_BlastDoor_Wheel', 'twist', wc, axis=(0, -1, 0), rng=(0, 720), parent='IX_BlastDoor', locked=True,
         states=['locked', 'unlocked'], note='the handwheel: two turns draw the bolts in (with power and the console\'s key '
                                            'in act 3; until then it does not move)')
    # ---- the vestibule's fittings: pipes and brackets, the cable tray, the console, the railing, lamps, signs
    for (px, pz, pr) in ((2.20, 4.30, 0.10), (1.92, 4.33, 0.07), (2.32, 3.98, 0.05)):
        rod(k, (px, 0.0, pz), (px, L, pz), pr, Z_PIPE, 10, caps=False)
    for yb2 in (1.0, 3.0, 5.0, 7.0):
        k.box(1.70, xi, yb2 - 0.04, yb2 + 0.04, 4.14, 4.19, Z_BRACK)
        k.box(xi - 0.05, xi, yb2 - 0.04, yb2 + 0.04, 3.85, 4.45, Z_BRACK)
    k.box(-xi, -xi + 0.30, 0.0, L, 3.98, 4.06, Z_TRAY)
    for (cx_, cz_) in ((-xi + 0.08, 4.09), (-xi + 0.15, 4.10), (-xi + 0.22, 4.09)):
        rod(k, (cx_, 0.0, cz_), (cx_, L, cz_), 0.018, Z_TRAY, 6, caps=False)
    cy0, cy1 = 2.30, 3.30                                   # (clear of the leaf's swing: it opens over y 3.9 .. 7.6)
    prof_c = [(-xi, 0.0), (-1.95, 0.0), (-1.95, 1.05), (-2.22, 1.558), (-2.22, 1.85), (-xi, 1.85)]
    K.prism_y(k, prof_c, cy0, cy1, Z_CAB, Z_CAB, edges=[None, Z_CAB, Z_CAB, Z_CAB, Z_CAB, None])
    sl = Vector((-0.27, 0.0, 0.508)).normalized()
    nrm = Vector((0.508, 0.0, 0.27)).normalized()
    cc = Vector(((-1.95 - 2.22) / 2, (cy0 + cy1) / 2, (1.05 + 1.558) / 2))
    kf.quad_uv(cc + nrm * 0.003, nrm, 0.80, 0.575, uv('console'), up=sl)
    rod(k, (-2.36, (cy0 + cy1) / 2, 1.85), (-2.36, (cy0 + cy1) / 2, 3.98), 0.025, Z_TRAY, 6)
    railing(k, [(xc - 0.05, 0.35, 0.0), (xc - 0.05, 2.3, 0.0), (xc - 0.05, 4.2, 0.0), (xc - 0.05, 6.1, 0.0), (xc - 0.05, L - 0.30, 0.0)],
            Z_VRAIL, h=1.0, r=0.022)
    bulkhead(k, gl, (xi - 0.01, 4.8, 3.3), -X, Z_VLAMP, Z_VLAMP)
    bulkhead(k, gl, (-xi + 0.01, 1.6, 3.3), X, Z_VLAMP, Z_VLAMP)
    LIGHTS.append(('Light_Vestibule_1', 'BlastDoor', (xi - 0.25, 4.8, 3.3), None, 'point', WARM, 8.0, 'steady'))
    LIGHTS.append(('Light_Vestibule_2', 'BlastDoor', (-xi + 0.25, 1.6, 3.3), None, 'point', WARM, 8.0, 'steady'))
    sign_plate(k, kf, (0.0, L - 0.005, cz + r1 + 0.36), -Y, 1.20, 0.275, 'drucktuer', Z_BRACK)
    sign_plate(k, kf, (xi - 0.005, L - 0.80, 1.75), -X, 0.60, 0.40, 'genehm', Z_BRACK)
    # ---- icicles: off the ceiling by the end wall, off the pipes
    for i in range(16):
        x = -xi + 0.25 + i * (2 * xi - 0.5) / 15 + (hsh(i, 21) - 0.5) * 0.2
        y = L - 0.10 - 0.55 * hsh(i, 22)
        icicle(k, (x, y, zc + 0.01), 0.12 + 0.55 * hsh(i, 23) ** 1.4, 0.025 + 0.025 * hsh(i, 24), Z_VICE)
    for i in range(10):
        y = 0.6 + i * 0.72 + hsh(i, 25) * 0.3
        px, pz, pr = ((2.20, 4.30, 0.10), (1.92, 4.33, 0.07), (2.32, 3.98, 0.05))[i % 3]
        icicle(k, (px, y, pz - pr + 0.01), 0.08 + 0.30 * hsh(i, 26), 0.02, Z_VICE)
    # ---- the wet prints to the door (the X11 sole: the same boots)
    pr_ = reg('BlastDoor_Prints', 'prints', 'BlastDoor')
    pts = [Vector((0.30 * math.sin(i * 0.9 + 0.4) - 0.10 + 0.05 * i, 0.75 + i * 0.86, 0.004)) for i in range(8)]
    pts.append(Vector((0.0, yf - 0.62 - 0.45, 0.004)))
    for i in range(8):
        hd = (pts[i + 1] - pts[i])
        hd.z = 0
        hd.normalize()
        pr_.quad_uv(pts[i], Z, 0.9, 0.9, (0.0, 0.0, 1.0, 1.0), up=hd)
    part('BlastDoor', 'static', (0, 0, 0),
         note='the vestibule with the round door (root): origin on the floor in the middle of its open end; goes on the '
              'hangar\'s Link_BlastDoor (no rotation); 5.0 x 4.6 m inside, the door at the far end (8 m)')
    part('BlastDoor_Glow', 'static', (0, 0, 0), parent='BlastDoor', states=['off', 'on'],
         note='the two wall lamps\' glasses: M_Bunker_Lamp_Off / M_Bunker_Lamp')
    part('BlastDoor_Prints', 'static', (0, 0, 0), parent='BlastDoor', states=['shown', 'hidden'],
         note='wet boot prints from the hangar to the door (M_Bunker_Prints, cut-out): the sole of X11 / the old shift\'s '
              'boots - someone went to this door; 8 strides of 0.9 m')
    socket('Link_Down', (0.0, y_end, z_down), 'link', parent='BlastDoor',
           note='behind the door: the end of the first steps down (1.4 m wide) - act 3 (the metro, the megastructures) '
                'continues here, along +y')
    socket('View_BlastDoor', (0.0, 1.5, 1.65), 'view', parent='BlastDoor', dir=(0, 1, 0.05),
           note='the day-8 look at the door from the vestibule\'s mouth')
    # colliders
    B = BOXES.append
    B(('Vest_Floor', 'BlastDoor', (-xi, xc, 0.0, L, -0.3, 0.0), None))
    B(('Vest_Channel', 'BlastDoor', (xc, xi, 0.0, L, -cd - 0.3, -cd), None))
    B(('Vest_WallL', 'BlastDoor', (-xo, -xi, 0.0, L, -0.3, zc), None))
    B(('Vest_WallR', 'BlastDoor', (xi, xo, 0.0, L, -cd - 0.3, zc), None))
    B(('Vest_Ceiling', 'BlastDoor', (-xo, xo, 0.0, L + t, zc, zc + t), None))
    B(('Vest_EndL', 'BlastDoor', (-xi, -r1, L - 0.16, L + t, 0.0, zc), None))
    B(('Vest_EndR', 'BlastDoor', (r1, xi, L - 0.16, L + t, 0.0, zc), None))
    B(('Vest_EndTop', 'BlastDoor', (-r1, r1, L - 0.16, L + t, cz + r1 - 0.05, zc), None))
    B(('Vest_Sill', 'BlastDoor', (-r1, r1, L - 0.16, L + t, 0.0, cz - lr), None))
    B(('Vest_Step', 'BlastDoor', (-0.65, 0.65, yf - 0.62, yf - 0.06, 0.0, 0.27), None))
    B(('Vest_Rail', 'BlastDoor', (xc - 0.08, xc - 0.02, 0.3, L - 0.25, 0.0, 1.02), None))
    B(('Vest_Console', 'BlastDoor', (-xi, -1.95, cy0, cy1, 0.0, 1.85), None))
    B(('Tunnel_Floor', 'BlastDoor', (-hw, hw, yback, y_t1 + 0.3, zt - 0.3, zt), None))
    B(('Passage_WallL', 'BlastDoor', (-pw - 0.3, -pw, y_t1, y_end, z_down, ph), None))
    B(('Passage_WallR', 'BlastDoor', (pw, pw + 0.3, y_t1, y_end, z_down, ph), None))
    B(('Passage_End', 'BlastDoor', (-pw, pw, y_end, y_end + 0.3, z_down, ph), None))
    ang = math.degrees(math.atan2(zt - z_down, y_end - 0.4 - y_t1 - 0.3))
    ln = math.hypot(zt - z_down, y_end - 0.4 - y_t1 - 0.3)
    ym = (y_t1 + 0.3 + y_end - 0.4) / 2
    B(('Passage_Steps', 'BlastDoor', (-pw, pw, ym - ln / 2, ym + ln / 2, (zt + z_down) / 2 - 0.2, (zt + z_down) / 2), (-ang, 0, 0)))
    B(('BlastDoor_Leaf', 'IX_BlastDoor', (-lr, lr, yf - 0.28, yback, cz - lr, cz + lr), None))
    MASS['IX_BlastDoor'] = 9000.0


# ================================================================ BunkerEntrance
def build_entrance():
    E = S.E
    xi, t, wt = E['xi'], E['t'], E['wall_top']
    xo = xi + t
    rise, run, n = E['rise'], E['run'], E['risers']
    zl = -S.E_DROP                                             # the landing
    yl0 = (n - 1) * run                                        # the last riser
    yp, yl1 = E['portal_y'], E['land_y1']
    zcl = zl + E['clear']                                      # the canopy's underside
    yb = yl1 + 0.30
    hc, hi, hl, fw = E['hatch_c'], E['hatch_in'], E['hatch_lid'], E['frame_w']
    ho = hi + fw
    zs = zl - E['shaft_d']
    k = reg('BunkerEntrance', 'Entrance', 'BunkerEntrance')
    kf = reg('BunkerEntrance_Signs', 'panel', 'BunkerEntrance', merge='BunkerEntrance')
    gl = reg('BunkerEntrance_Glow', 'lamp', 'BunkerEntrance')
    # ---- the steps (risers, treads), the landing round the hatch
    for i in range(n):
        y = i * run
        za, zb = -i * rise, -(i + 1) * rise
        quad(k, [(-xi, y, zb), (xi, y, zb), (xi, y, za), (-xi, y, za)], Z_ESTEP, -Y)
        if i < n - 1:
            quad(k, [(-xi, y, zb), (xi, y, zb), (xi, y + run, zb), (-xi, y + run, zb)], Z_ESTEP, Z)
    for xa, xb, ya, yb2 in ((-xi, xi, yl0, hc - ho), (-xi, xi, hc + ho, yl1), (-xi, -ho, hc - ho, hc + ho), (ho, xi, hc - ho, hc + ho)):
        quad(k, [(xa, ya, zl), (xb, ya, zl), (xb, yb2, zl), (xa, yb2, zl)], Z_EFLOOR, Z)
    # ---- the trench walls: inner faces following the steps, tops, the outer lip, the front ends
    for sx in (-1, 1):
        x = sx * xi
        nin = -X * sx
        for i in range(n):
            y = i * run
            zb = -(i + 1) * rise
            ye = min(y + run, yp) if i < n - 1 else yp
            quad(k, [(x, y, zb), (x, ye, zb), (x, ye, wt), (x, y, wt)], Z_EWALL, nin)
        quad(k, [(x, -0.30, 0.0), (x, 0.0, 0.0), (x, 0.0, wt), (x, -0.30, wt)], Z_EWALL, nin)
        quad(k, [(x, yp, zl), (x, yl1, zl), (x, yl1, zcl), (x, yp, zcl)], Z_EWALL, nin)
        quad(k, [(x, -0.30, wt), (sx * xo, -0.30, wt), (sx * xo, yp, wt), (x, yp, wt)], Z_ETOP, Z)
        quad(k, [(sx * xo, -0.30, -0.35), (sx * xo, yb, -0.35), (sx * xo, yb, wt), (sx * xo, -0.30, wt)], Z_EOUT, X * sx)
        quad(k, [(x, -0.30, -0.35), (sx * xo, -0.30, -0.35), (sx * xo, -0.30, wt), (x, -0.30, wt)], Z_EOUT, -Y)
    quad(k, [(-xi, -0.30, -0.35), (xi, -0.30, -0.35), (xi, -0.30, 0.0), (-xi, -0.30, 0.0)], Z_EHIDE, -Y)
    quad(k, [(-xi, -0.30, 0.0), (xi, -0.30, 0.0), (xi, 0.0, 0.0), (-xi, 0.0, 0.0)], Z_ESTEP, Z)
    # ---- the portal canopy: lintel face, underside, top, back wall, outer lip
    quad(k, [(-xo, yp, zcl), (xo, yp, zcl), (xo, yp, wt), (-xo, yp, wt)], Z_EWALL, -Y)
    quad(k, [(-xi, yp, zcl), (xi, yp, zcl), (xi, yl1, zcl), (-xi, yl1, zcl)], Z_ECEIL, -Z)
    quad(k, [(-xo, yp, wt), (xo, yp, wt), (xo, yb, wt), (-xo, yb, wt)], Z_ETOP, Z)
    quad(k, [(-xi, yl1, zl), (xi, yl1, zl), (xi, yl1, zcl), (-xi, yl1, zcl)], Z_EWALL, -Y)
    quad(k, [(-xo, yb, -0.35), (xo, yb, -0.35), (xo, yb, wt), (-xo, yb, wt)], Z_EOUT, Y)
    # ---- the shaft: walls, its floor, the passage at its foot (Link_Shaft), the ladder on the -y wall
    sy0, sy1 = hc - hi, hc + hi
    zp_top = zs + 2.0
    for (a, b, nn) in (((-hi, sy0), (hi, sy0), Y), ((hi, sy1), (-hi, sy1), -Y), ((-hi, sy1), (-hi, sy0), X), ((hi, sy0), (hi, sy1), -X)):
        if nn.y < 0:                                           # the +y wall: the passage opening at the foot
            quad(k, [(a[0], a[1], zp_top), (b[0], b[1], zp_top), (b[0], b[1], zl), (a[0], a[1], zl)], Z_ESHAFT, nn)
            quad(k, [(hi, sy1, zs), (0.45, sy1, zs), (0.45, sy1, zp_top), (hi, sy1, zp_top)], Z_ESHAFT, nn)
            quad(k, [(-0.45, sy1, zs), (-hi, sy1, zs), (-hi, sy1, zp_top), (-0.45, sy1, zp_top)], Z_ESHAFT, nn)
        else:
            quad(k, [(a[0], a[1], zs), (b[0], b[1], zs), (b[0], b[1], zl), (a[0], a[1], zl)], Z_ESHAFT, nn)
    quad(k, [(-hi, sy0, zs), (hi, sy0, zs), (hi, sy1, zs), (-hi, sy1, zs)], Z_ESHAFT, Z)
    ye = sy1 + 1.0
    quad(k, [(-0.45, sy1, zs), (0.45, sy1, zs), (0.45, ye, zs), (-0.45, ye, zs)], Z_ESHAFT, Z)
    quad(k, [(-0.45, sy1, zp_top), (0.45, sy1, zp_top), (0.45, ye, zp_top), (-0.45, ye, zp_top)], Z_ESHAFT, -Z)
    for sx in (-1, 1):
        quad(k, [(sx * 0.45, sy1, zs), (sx * 0.45, ye, zs), (sx * 0.45, ye, zp_top), (sx * 0.45, sy1, zp_top)], Z_ESHAFT, -X * sx)
    ly = sy0 + 0.16
    for sx in (-0.22, 0.22):
        bar(k, (sx, ly, zs), (sx, ly, zl + 0.75), 0.05, 0.012, Z_ELADDER, up=X)
        for zz in (zs + 0.6, zl - 0.6, zl - 0.06):
            bar(k, (sx, sy0, zz), (sx, ly + 0.01, zz), 0.04, 0.010, Z_ELADDER, up=Z)
        k.tube([V3(sx, ly, zl - 0.02), V3(sx, ly, zl + 0.70), V3(sx, ly - 0.10, zl + 0.80)], 0.016, Z_ELADDER, 6)
    zz = zs + 0.28
    while zz < zl - 0.10:
        rod(k, (-0.22, ly, zz), (0.22, ly, zz), 0.013, Z_ELADDER, 6, caps=False)
        zz += 0.28
    # ---- the hatch frame (galvanised angle) in the landing
    zf = zl + 0.012
    sq = lambda r, z, yc=hc: [V3(-r, yc - r, z), V3(r, yc - r, z), V3(r, yc + r, z), V3(-r, yc + r, z)]
    rfo, rfi, rlow = sq(ho, zf), sq(hi, zf), sq(hi, zl - 0.10)
    rfl = sq(ho, zl)
    for i in range(4):
        j = (i + 1) % 4
        m = (rfo[i] + rfo[j]) / 2
        out = Vector((m.x, m.y - hc, 0.0))
        face(k, [rfo[i], rfo[j], rfi[j], rfi[i]], Z_EFRAME, Z)
        face(k, [rfl[i], rfl[j], rfo[j], rfo[i]], Z_EFRAME, out)
        face(k, [rfi[i], rfi[j], rlow[j], rlow[i]], Z_EFRAME, -out)
    for xx in (-0.30, 0.30):                                   # the fixed hinge knuckles on the +y edge
        rod(k, (xx - 0.17, hc + hl + 0.03, zl + 0.035), (xx - 0.09, hc + hl + 0.03, zl + 0.035), 0.022, Z_EHINGE, 8)
        rod(k, (xx + 0.09, hc + hl + 0.03, zl + 0.035), (xx + 0.17, hc + hl + 0.03, zl + 0.035), 0.022, Z_EHINGE, 8)
        k.box(xx - 0.17, xx + 0.17, hc + hl + 0.03, hc + ho + 0.08, zl, zl + 0.015, Z_EHINGE)
    # ---- the lid (IX_BunkerHatch) and its wheel
    Ld = reg('IX_BunkerHatch', 'Entrance', 'BunkerEntrance')
    lz0, lz1 = zl + 0.014, zl + 0.070
    box6(Ld, (-hl, hc - hl, lz0), (hl, hc + hl, lz1), Z_ELID)
    for yy in (hc - 0.25, hc + 0.25):
        Ld.box(-hl + 0.06, hl - 0.06, yy - 0.025, yy + 0.025, lz1, lz1 + 0.025, Z_ELID)
    for xx in (-0.30, 0.30):
        Ld.box(xx - 0.075, xx + 0.075, hc + hl - 0.30, hc + hl + 0.02, lz1, lz1 + 0.010, Z_EHINGE)
        rod(Ld, (xx - 0.085, hc + hl + 0.03, zl + 0.035), (xx + 0.085, hc + hl + 0.03, zl + 0.035), 0.022, Z_EHINGE, 8)
    Ld.lathe(V3(0, hc, lz1), Z, [(0.0, 0.08), (0.03, 0.06), (0.035, 0.0)], Z_EWHEEL, 10, cap0=False, cap1=True)
    part('IX_BunkerHatch', 'hinge', (0.0, hc + hl + 0.03, zl + 0.035), axis=(-1, 0, 0), rng=(0, 110), parent='BunkerEntrance',
         states=['closed', 'open'], note='the steel hatch in the landing floor: under the ice until Ice_Hatch_1..3 are '
                                        'knocked off; then the wheel, then it lifts toward the back wall (hinge on its +y '
                                        'edge); the ladder goes down the shaft\'s -y wall')
    Wh = reg('IX_BunkerHatch_Wheel', 'Entrance', 'BunkerEntrance')
    wc = V3(0, hc, lz1 + 0.040)
    pts = [wc + V3(math.cos(TAU * i / 14), math.sin(TAU * i / 14), 0) * 0.17 for i in range(14)]
    Wh.tube(pts + [pts[0]], 0.014, Z_EWHEEL, 6, caps=False)
    for i in range(4):
        a = i * TAU / 4 + 0.4
        rod(Wh, wc + V3(math.cos(a), math.sin(a), 0) * 0.03, wc + V3(math.cos(a), math.sin(a), 0) * 0.165, 0.011, Z_EWHEEL, 6)
    part('IX_BunkerHatch_Wheel', 'twist', wc, axis=(0, 0, 1), rng=(0, 540), parent='IX_BunkerHatch',
         states=['dogged', 'free'], note='the hatch\'s handwheel: one and a half turns free the dogs; frozen while iced')
    # ---- the ice: a sheet over the landing (frozen melt water), three chunks over the hatch
    ice = reg('BunkerEntrance_Ice', 'iceclear', 'BunkerEntrance')
    it = E['ice_t']
    zi = zl + it + 0.016
    ix, iy0, iy1 = 0.74, hc - 0.74, hc + 0.74                  # the chunks' square
    for xa, xb, ya, yb2 in ((-xi, xi, yl0 - 0.05, iy0), (-xi, xi, iy1, yl1), (-xi, -ix, iy0, iy1), (ix, xi, iy0, iy1)):
        box6(ice, (xa + 0.005, ya, zl + 0.003), (xb - 0.005, yb2, zi), 1, skip=('-z',))   # (no underside: one layer seen from above)
    cuts = [-ix, -0.21 + 0.04, 0.27, ix]
    for c_ in range(3):
        nm = f'Ice_Hatch_{c_ + 1}'
        ck = reg(nm, 'iceclear', 'BunkerEntrance')
        xa, xb = cuts[c_], cuts[c_ + 1]
        ys = np.linspace(iy0, iy1, 7)
        ja = [xa + (0.0 if c_ == 0 else 0.06 * (hsh(j, 31 + c_) - 0.5)) for j in range(7)]
        jb = [xb + (0.0 if c_ == 2 else 0.06 * (hsh(j, 32 + c_) - 0.5)) for j in range(7)]
        top = zi + 0.01 * (hsh(c_, 33) - 0.5)
        bot = zl + 0.075
        for j in range(6):                                     # a slab with jagged sides: strips along y
            a0, a1, b0, b1 = ja[j], ja[j + 1], jb[j], jb[j + 1]
            quad(ck, [(a0, ys[j], top), (b0, ys[j], top), (b1, ys[j + 1], top), (a1, ys[j + 1], top)], 1, Z)
            quad(ck, [(a0, ys[j], bot), (a1, ys[j + 1], bot), (a1, ys[j + 1], top), (a0, ys[j], top)], 1, -X)
            quad(ck, [(b0, ys[j], bot), (b1, ys[j + 1], bot), (b1, ys[j + 1], top), (b0, ys[j], top)], 1, X)
        quad(ck, [(ja[0], iy0, bot), (jb[0], iy0, bot), (jb[0], iy0, top), (ja[0], iy0, top)], 1, -Y)
        quad(ck, [(ja[-1], iy1, bot), (jb[-1], iy1, bot), (jb[-1], iy1, top), (ja[-1], iy1, top)], 1, Y)
        part(nm, 'static', ((xa + xb) / 2, hc, (top + bot) / 2), parent='BunkerEntrance', states=['iced', 'clear'],
             note=f'ice chunk {c_ + 1} of 3 over the hatch: knocked off (forest_gear Item_IceAxe, a crowbar) - hide it, drop '
                  f'a few chunks; the hatch opens when all three are gone; hit box in the contract')
        REMOVABLE.append(nm)
        HITS.append((nm, (min(ja + [xa]) - 0.02, max(jb + [xb]) + 0.02, iy0 - 0.02, iy1 + 0.02, bot - 0.02, top + 0.03)))
    part('BunkerEntrance_Ice', 'static', (0, (yl0 + yl1) / 2, zl), parent='BunkerEntrance', states=['iced', 'thawed'],
         note='the frozen melt water on the landing (clear ice, M_Bunker_IceClear: the hatch shows through)')
    # ---- railings on the wall tops, a handrail down the +x wall, snow, the lamp and the sign in the portal
    for sx in (-1, 1):
        xr = sx * (xi + t / 2)
        railing(k, [(xr, -0.15, wt), (xr, 1.30, wt), (xr, 2.75, wt), (xr, 4.20, wt), (xr, yp - 0.12, wt)], Z_ERAIL, h=1.0, r=0.024)
        k.tube([V3(xr, -0.15, wt + 1.0), V3(xr, -0.45, wt + 0.75), V3(xr, -0.52, wt + 0.02)], 0.024, Z_ERAIL, 8)
    hx = xi - 0.07
    hz = 0.90
    k.tube([V3(hx, 0.10, -0.19 + hz), V3(hx, yl0 + 0.10, zl + hz)], 0.022, Z_ERAIL, 8)
    for yy in (0.4, 2.2, 4.0):
        zz = -0.19 + (yy - 0.10) / yl0 * (zl + 0.19) + hz
        bar(k, (xi, yy, zz - 0.04), (hx, yy, zz - 0.04), 0.03, 0.03, Z_ERAIL, up=Z)
    for i in range(7):                                         # snow on the upper treads, thinning down
        y = i * run
        zb = -(i + 1) * rise
        th = 0.10 - 0.012 * i
        xa = -xi + 0.05 * hsh(i, 41)
        xb = xi - 0.05 * hsh(i, 42)
        k.box(xa, xb, y + 0.02, y + run, zb, zb + th, Z_ESNOW)
    k.box(-xi + 0.01, xi - 0.01, -0.30, 0.0, 0.0, 0.10, Z_ESNOW)
    k.box(-xo - 0.03, -xi + 0.02, -0.33, yp, wt, wt + 0.08, Z_ESNOW)
    k.box(xi - 0.02, xo + 0.03, -0.33, yp, wt, wt + 0.08, Z_ESNOW)
    k.box(-xo - 0.03, xo + 0.03, yp - 0.03, yb + 0.03, wt, wt + 0.12, Z_ESNOW)
    bulkhead(k, gl, (0.0, yl1 - 0.01, zcl - 0.30), -Y, Z_ELAMP, Z_ELAMP)
    LIGHTS.append(('Light_Entrance', 'BunkerEntrance', (0.0, yl1 - 0.25, zcl - 0.32), None, 'point', WARM, 6.0, 'steady'))
    sign_plate(k, kf, (0.0, yl1 - 0.005, zl + 1.45), -Y, 0.60, 0.40, 'zutritt', Z_ELAMP)
    part('BunkerEntrance', 'static', (0, 0, 0),
         note='the way in by the hand (root): origin on the ground at the top step\'s edge; the trench goes down to +y '
              '(16 risers, 3.04 m) under the portal canopy; set the ground (terrain) to z 0 round the wall tops')
    part('BunkerEntrance_Glow', 'static', (0, 0, 0), parent='BunkerEntrance', states=['off', 'on'],
         note='the portal lamp\'s glass: M_Bunker_Lamp_Off / M_Bunker_Lamp')
    socket('Link_Shaft', (0.0, ye, zs), 'link', parent='BunkerEntrance',
           note='the end of the passage at the shaft\'s foot (0.9 x 2.0 m): the underground part to the hangar\'s side '
                'door (Link_SideDoor) continues here, along +y')
    # colliders
    B = BOXES.append
    ang = math.degrees(math.atan2(S.E_DROP, yl0))
    ln = math.hypot(S.E_DROP, yl0)
    B(('Entr_Steps', 'BunkerEntrance', (-xi, xi, yl0 / 2 - ln / 2, yl0 / 2 + ln / 2, zl / 2 - 0.25, zl / 2), (-ang, 0, 0)))
    B(('Entr_WallL', 'BunkerEntrance', (-xo, -xi, -0.30, yb, zl - 0.3, wt), None))
    B(('Entr_WallR', 'BunkerEntrance', (xi, xo, -0.30, yb, zl - 0.3, wt), None))
    B(('Entr_Canopy', 'BunkerEntrance', (-xo, xo, yp, yb, zcl, wt), None))
    B(('Entr_Back', 'BunkerEntrance', (-xi, xi, yl1, yb, zl, zcl), None))
    B(('Entr_LandFront', 'BunkerEntrance', (-xi, xi, yl0, hc - ho, zl - 0.3, zl), None))
    B(('Entr_LandBack', 'BunkerEntrance', (-xi, xi, hc + ho, yl1, zl - 0.3, zl), None))
    B(('Entr_LandL', 'BunkerEntrance', (-xi, -ho, hc - ho, hc + ho, zl - 0.3, zl), None))
    B(('Entr_LandR', 'BunkerEntrance', (ho, xi, hc - ho, hc + ho, zl - 0.3, zl), None))
    B(('Entr_RailL', 'BunkerEntrance', (-xo, -xi, -0.3, yp, wt, wt + 1.02), None))
    B(('Entr_RailR', 'BunkerEntrance', (xi, xo, -0.3, yp, wt, wt + 1.02), None))
    for nm, (xa, xb, ya, yb2) in (('Shaft_S', (-hi - 0.3, hi + 0.3, sy0 - 0.3, sy0)), ('Shaft_W', (-hi - 0.3, -hi, sy0, sy1)),
                                  ('Shaft_E', (hi, hi + 0.3, sy0, sy1))):
        B((f'Entr_{nm}', 'BunkerEntrance', (xa, xb, ya, yb2, zs, zl), None))
    B(('Entr_Shaft_N', 'BunkerEntrance', (-hi - 0.3, hi + 0.3, sy1, sy1 + 0.3, zp_top, zl), None))
    B(('Entr_ShaftFloor', 'BunkerEntrance', (-hi, hi, sy0, ye, zs - 0.3, zs), None))
    B(('Entr_PassL', 'BunkerEntrance', (-0.75, -0.45, sy1, ye, zs, zp_top), None))
    B(('Entr_PassR', 'BunkerEntrance', (0.45, 0.75, sy1, ye, zs, zp_top), None))
    B(('Entr_Ice', 'BunkerEntrance_Ice', (-xi, xi, yl0, yl1, zl, zi), None))
    B(('BunkerHatch', 'IX_BunkerHatch', (-hl, hl, hc - hl, hc + hl, lz0, lz1 + 0.05), None))
    MASS['IX_BunkerHatch'] = 140.0


# ================================================================ PlaneTarp
def build_tarp():
    d = np.load(TARP_NPZ)
    P = d['plane']
    ny, nx = P.shape[:2]
    step = 2
    js = list(range(0, ny, step))
    is_ = list(range(0, nx, step))
    if js[-1] != ny - 1:
        js.append(ny - 1)
    if is_[-1] != nx - 1:
        is_.append(nx - 1)
    k = reg('PlaneTarp', 'Tarp', 'PlaneTarp')
    vs = [[k.bm.verts.new(Vector(P[j, i])) for i in is_] for j in js]
    nj, ni = len(js), len(is_)
    for a in range(nj - 1):
        for b in range(ni - 1):
            hem = a == 0 or b == 0 or a == nj - 2 or b == ni - 2
            f = k._f([vs[a][b], vs[a][b + 1], vs[a + 1][b + 1], vs[a + 1][b]], Z_TARPHEM if hem else Z_TARP)
            f.smooth = True
    part('PlaneTarp', 'static', (0, 0, 0), states=['on', 'off'],
         note='the canvas over the parked plane (root): in forest UtilityPlane\'s own frame - parent it to the plane root '
              'at (0, 0, 0), no rotation (draped with the plane at Slot_Plane: nose-up, the WinterKit covers on); one sheet, '
              'seen from both sides: material Render Face Both; pulled off first (then the kit covers)')
    low = np.unravel_index(np.argmin(P[..., 2]), P.shape[:2])
    socket('Grab_Tarp', tuple(P[low]), 'grab', parent='PlaneTarp',
           note='where it is pulled off: the lowest hanging corner of the canvas (by a cabin door)')


def build_bunker():
    build_hangar()
    build_blastdoor()
    build_entrance()
    build_tarp()
