"""forest_gear geometry: the things the players carry, pull and find in the Forest (the tasks' consumables, lamps, the radio,
the haulers for one player, the story items), in the generator shed's style. Fifteen roots, each in its own frame
(Blender: z up, the front -y, metres; origin on the surface it stands on, z = 0, under its middle - the key and the brass
tag: the hanging point on top of the ring, as forest_items' keys; Unity (x, y, z) -> (-x, z, -y), the front -> +Z):
  Item_Battery         a D cell (MONO 1,5 V), standing
  Item_BatteryPack     four D cells in a printed sleeve (the order from the PC)
  Item_Battery6V       a 4R25 lantern battery (6 V block, two spring terminals): the hand lamp's and the lake sensor's
  Item_Walkie          a handheld UHF radio: channel knob (16 clicks) and volume / on-off knob as twist parts, the PTT key
                       (slide), the LCD its own object (lit / off), the TX / RX LED, the antenna, the belt clip; English labels
  Item_Lantern         a 6 V hand lamp with an amber lens - the yellow light (R1: yellow holds the Cold one): the lens its own
                       object (lit / off), the slide switch, the battery door at the back (Slot_Battery takes Item_Battery6V)
  Item_Headlamp        an elastic head band with the lamp (tilts down, the bezel turns it on), a clear lens (white light),
                       the battery box at the back
  Item_Cart            a platform cart for heavy loads: plywood deck on a blue steel frame, push handle, two fixed and two
                       swivel pneumatic wheels (spin parts)
  Item_Sled            a red plastic pulk with lashing ropes, the tow rope with its T-handle (Sled_Tow: hide it while the game
                       draws the rope from Tow_Anchor to the hand)
  Item_Doll            the day-3 doll: a cloth doll in a knitted dress sitting with her legs out, painted face, yarn braids;
                       Doll_Head turns (twist about z) - the demo's last shot
  Item_Postcard        the card with the doll: a winter picture; the back (own texture) - the message signed "— K" without
                       the dot; both faces UV 0..1, the game may swap the back
  Item_Bulb            a frosted E27 60 W bulb; the glass its own material (M_Gear_Bulb / M_Gear_BulbBurnt)
  Item_BulbBox         its carton (GLÜHLAMPE 60 W E27 230 V)
  Item_WorkerTag       a round brass tag with a stamped personnel number (gear_tex.TAG_NUMBER) on a split ring
  Item_Key_Stationsleiter  the station chief's key: forest_items' key (the same ring, key and tag) with a black tag ST.-LEITER
  Item_IceAxe          an ice axe (ash shaft, steel head: pick and adze, the spike) for chipping ice off the antennas; upright,
                       the spike's tip at the origin
Printed faces (panel atlas) are merged into their body at build time (MERGE); parts / sockets in each root's frame (the
contract); in the .blend the roots stand apart (DISPLAY)."""
import math
import numpy as np
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, box6, face, quad, KBS, CONTRACT
from van2_kit import rrect
import van3_mech as VM
import gear_tex as GT

uv = GT.uv
TAU = 2 * math.pi
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
ROOTS = ['Item_Battery', 'Item_BatteryPack', 'Item_Battery6V', 'Item_Walkie', 'Item_Lantern', 'Item_Headlamp', 'Item_Cart',
         'Item_Sled', 'Item_Doll', 'Item_Postcard', 'Item_Bulb', 'Item_BulbBox', 'Item_WorkerTag', 'Item_Key_Stationsleiter',
         'Item_IceAxe']
DISPLAY = {'Item_Battery': Vector((0.0, 0.0, 0.0)), 'Item_BatteryPack': Vector((0.10, 0.0, 0.0)),
           'Item_Battery6V': Vector((0.22, 0.0, 0.0)), 'Item_Walkie': Vector((0.38, 0.0, 0.0)),
           'Item_Lantern': Vector((0.56, 0.0, 0.0)), 'Item_Headlamp': Vector((0.82, 0.0, 0.0)),
           'Item_Bulb': Vector((1.03, 0.0, 0.0)), 'Item_BulbBox': Vector((1.13, 0.0, 0.0)),
           'Item_WorkerTag': Vector((1.24, 0.0, 0.12)), 'Item_Key_Stationsleiter': Vector((1.31, 0.0, 0.12)),
           'Item_Postcard': Vector((1.48, 0.0, 0.0)), 'Item_Doll': Vector((1.75, 0.0, 0.0)), 'Item_IceAxe': Vector((2.05, 0.0, 0.0)),
           'Item_Cart': Vector((-0.75, 0.25, 0.0)), 'Item_Sled': Vector((-1.75, 0.6, 0.0))}
ROOT_OF = {}
MERGE = {}                       # explicit-UV KB -> the body it is joined into (a second material on that mesh)
BOXES = []                       # colliders: (name, parent, (x0, x1, y0, y1, z0, z1), rot or None) in the root frame
MASS = {}                        # root -> kg (a suggestion for the rigidbody)
(Z_CELL, Z_CELLWRAP, Z_B6CHAM, Z_B6CAP, Z_SPRING, Z_WK, Z_WK_RUB, Z_WK_METAL, Z_LAMP, Z_LAMP_BK, Z_LAMP_SW, Z_CAVITY,
 Z_CHROME, Z_BAND, Z_HL, Z_HL_BEZEL, Z_CABLE, Z_SKIN, Z_HAIR, Z_DRESS, Z_COLLAR, Z_SOCK, Z_SHOE, Z_RIBBON, Z_BULBCAP,
 Z_BULBINS, Z_SOLDER, Z_BRASS, Z_STEEL, Z_TAGBK, Z_AXE, Z_AXEWOOD, Z_LEASH) = range(500, 533)
SMALL_ZONES = list(range(500, 533))
(Z_CART, Z_DECK, Z_TYRE, Z_RIM, Z_ZINC, Z_GRIP, Z_SLED, Z_SLED_IN, Z_ROPE, Z_TWOOD) = range(540, 550)
HAUL_ZONES = list(range(540, 550))


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


def frame_of(t, side=Vector((1, 0, 0))):
    """3x3 with columns (side, t, n): a plate lying along t, its normal n = side x t"""
    t = Vector(t).normalized()
    side = (Vector(side) - t * Vector(side).dot(t)).normalized()
    n = side.cross(t).normalized()
    return Matrix((side, t, n)).transposed()


def band_uv(k, c, axis, r, h0, h1, uvrect, seg=16, ref=(1, 0, 0)):
    """an open cylinder band with uvrect wrapped once round it: u counter-clockwise seen from the axis' tip (from ref),
    v along the axis - the print reads from outside"""
    c, ax = Vector(c), Vector(axis).normalized()
    e1 = (Vector(ref) - ax * Vector(ref).dot(ax)).normalized()
    e2 = ax.cross(e1)
    u0, v0, u1, v1 = uvrect
    for i in range(seg):
        a0, a1 = TAU * i / seg, TAU * (i + 1) / seg
        p0 = c + (e1 * math.cos(a0) + e2 * math.sin(a0)) * r
        p1 = c + (e1 * math.cos(a1) + e2 * math.sin(a1)) * r
        ua, ub = u0 + (u1 - u0) * i / seg, u0 + (u1 - u0) * (i + 1) / seg
        k.poly([p0 + ax * h0, p1 + ax * h0, p1 + ax * h1, p0 + ax * h1], 0.0, [(ua, v0), (ub, v0), (ub, v1), (ua, v1)])


def lathe_uv(k, c, axis, prof, uvrect, seg=16, ref=(1, 0, 0)):
    """a lathe with explicit UVs: u round (counter-clockwise from ref), v along the profile (first -> last point)"""
    c, ax = Vector(c), Vector(axis).normalized()
    e1 = (Vector(ref) - ax * Vector(ref).dot(ax)).normalized()
    e2 = ax.cross(e1)
    u0, v0, u1, v1 = uvrect
    L = [0.0]
    for (a, r), (b, s) in zip(prof[:-1], prof[1:]):
        L.append(L[-1] + math.hypot(b - a, s - r))
    for j in range(len(prof) - 1):
        (a, r), (b, s) = prof[j], prof[j + 1]
        va, vb = v0 + (v1 - v0) * L[j] / L[-1], v0 + (v1 - v0) * L[j + 1] / L[-1]
        for i in range(seg):
            t0, t1 = TAU * i / seg, TAU * (i + 1) / seg
            d0, d1 = e1 * math.cos(t0) + e2 * math.sin(t0), e1 * math.cos(t1) + e2 * math.sin(t1)
            ua, ub = u0 + (u1 - u0) * i / seg, u0 + (u1 - u0) * (i + 1) / seg
            q = [c + ax * a + d0 * r, c + ax * a + d1 * r, c + ax * b + d1 * s, c + ax * b + d0 * s]
            if s < 1e-6:
                k.poly(q[:3], 0.0, [(ua, va), (ub, va), ((ua + ub) / 2, vb)])
            elif r < 1e-6:
                k.poly([q[0], q[2], q[3]], 0.0, [((ua + ub) / 2, va), (ub, vb), (ua, vb)])
            else:
                k.poly(q, 0.0, [(ua, va), (ub, va), (ub, vb), (ua, vb)])


def planar(k, pts, uvrect, lo, hi, axes=('x', 'y')):
    """a polygon with UVs projected on two world axes: lo / hi (2-tuples) -> uvrect"""
    u0, v0, u1, v1 = uvrect
    ia, ib = 'xyz'.index(axes[0]), 'xyz'.index(axes[1])
    uvs = [(u0 + (u1 - u0) * (p[ia] - lo[0]) / (hi[0] - lo[0]), v0 + (v1 - v0) * (p[ib] - lo[1]) / (hi[1] - lo[1])) for p in pts]
    return k.poly([Vector(p) for p in pts], 0.0, uvs)


def coil(k, a, b, r_coil, r_wire, turns, zone, per_turn=6):
    """a coil spring from a to b"""
    a, b = Vector(a), Vector(b)
    t = (b - a).normalized()
    e1 = (X - t * X.dot(t)).normalized() if abs(t.x) < 0.9 else (Y - t * Y.dot(t)).normalized()
    e2 = t.cross(e1)
    n = int(turns * per_turn)
    pts = [a.lerp(b, i / n) + (e1 * math.cos(TAU * i / per_turn) + e2 * math.sin(TAU * i / per_turn)) * r_coil for i in range(n + 1)]
    k.tube(pts, r_wire, zone, 3)


def ring_tube(k, c, n, r, r_wire, zone, seg=14, wseg=4):
    """a closed wire ring (torus) round axis n"""
    c, n = Vector(c), Vector(n).normalized()
    e1 = (Z - n * Z.dot(n)).normalized() if abs(n.z) < 0.9 else (X - n * X.dot(n)).normalized()
    e2 = n.cross(e1)
    pts = [c + (e1 * math.cos(TAU * i / seg) + e2 * math.sin(TAU * i / seg)) * r for i in range(seg)]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[(i + 1) % seg] - pts[i - 1]).normalized()
        rd = (p - c).normalized()
        rings.append([p + (rd * math.cos(TAU * j / wseg) + n * math.sin(TAU * j / wseg)) * r_wire for j in range(wseg)])
    for i in range(seg):
        A, B = rings[i], rings[(i + 1) % seg]
        for j in range(wseg):
            face(k, [A[j], A[(j + 1) % wseg], B[(j + 1) % wseg], B[j]], zone,
                 out=(A[j] + B[(j + 1) % wseg]) / 2 - (pts[i] + pts[(i + 1) % seg]) / 2)


def loft_open(k, rings, zone, out_fn):
    """quads between consecutive open polylines of equal length; each quad faces out_fn(its centre)"""
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(len(a) - 1):
            q = [a[i], a[i + 1], b[i + 1], b[i]]
            cc = sum(q, Vector()) / 4
            face(k, q, zone, out_fn(cc))


def ell_rings(c, axis, stations, seg=10, side=X):
    """rings of ellipses along axis: stations [(along, rx, ry)], rx along side"""
    c, ax = Vector(c), Vector(axis).normalized()
    e1 = (Vector(side) - ax * Vector(side).dot(ax)).normalized()
    e2 = ax.cross(e1)
    return [[c + ax * a + e1 * (rx * math.cos(TAU * i / seg)) + e2 * (ry * math.sin(TAU * i / seg)) for i in range(seg)]
            for a, rx, ry in stations]


# ================================================================ batteries
D_R, D_H, D_TOP = 0.0171, 0.0600, 0.0615


def d_cell(k, pk, c, seg=16):
    """a D cell standing on c: the steel bottom, the printed wrapper (pk), the wrapper's rolled top, the steel top, the nub"""
    c = Vector(c)
    k.lathe(c, Z, [(0.0, 0.0150), (0.0012, D_R)], Z_CELL, seg, cap0=True, cap1=False)
    band_uv(pk, c, Z, D_R, 0.0012, 0.0590, uv('d_band'), seg=seg, ref=(1, 0, 0))
    k.lathe(c, Z, [(0.0590, D_R), (D_H, 0.0155)], Z_CELLWRAP, seg, cap0=False, cap1=False)
    k.lathe(c, Z, [(D_H, 0.0155), (D_H, 0.0049)], Z_CELL, seg, cap0=False, cap1=False)
    k.lathe(c, Z, [(D_H, 0.0049), (D_TOP, 0.0047)], Z_CELL, 10, cap0=False, cap1=True)


def build_battery():
    k = reg('Item_Battery', 'Small', 'Item_Battery')
    pk = reg('Battery_Wrap', 'panel', 'Item_Battery', merge='Item_Battery')
    d_cell(k, pk, (0, 0, 0))
    part('Item_Battery', 'item', (0, 0, 0), note='a D cell (MONO 1,5 V, LR20): standing, origin under its middle, + up; the '
                                                 'wrapper printed twice round (reads from the front and the back)')
    MASS['Item_Battery'] = 0.14
    BOXES.append(('Battery', 'Item_Battery', (-D_R, D_R, -D_R, D_R, 0.0, D_TOP), None))


PACK_F, PACK_C = 0.0350, 0.02457                    # the sleeve's flats and where its chamfers start (round 4 cells)


def build_pack():
    k = reg('Item_BatteryPack', 'Small', 'Item_BatteryPack')
    pk = reg('BatteryPack_Print', 'panel', 'Item_BatteryPack', merge='Item_BatteryPack')
    s = 0.0172
    for xs in (-1, 1):
        for ys in (-1, 1):
            d_cell(k, pk, (xs * s, ys * s, 0.0), seg=12)
    f, c = PACK_F, PACK_C
    P = [(-c, -f), (c, -f), (f, -c), (f, c), (c, f), (-c, f), (-f, c), (-f, -c)]
    L = [0.0]
    for i in range(8):
        a, b = Vector(P[i] + (0,)), Vector(P[(i + 1) % 8] + (0,))
        L.append(L[-1] + (b - a).length)
    u0, v0, u1, v1 = uv('pack_sleeve')
    z0, z1 = 0.012, 0.048
    for i in range(8):
        a, b = P[i], P[(i + 1) % 8]
        ua, ub = u0 + (u1 - u0) * L[i] / L[-1], u0 + (u1 - u0) * L[i + 1] / L[-1]
        pk.poly([Vector((a[0], a[1], z0)), Vector((b[0], b[1], z0)), Vector((b[0], b[1], z1)), Vector((a[0], a[1], z1))], 0.0,
                [(ua, v0), (ub, v0), (ub, v1), (ua, v1)])
    part('Item_BatteryPack', 'item', (0, 0, 0), note='four D cells in a printed sleeve (4 x MONO 1,5 V): the order from the PC; '
                                                     'standing, origin under its middle')
    MASS['Item_BatteryPack'] = 0.58
    BOXES.append(('BatteryPack', 'Item_BatteryPack', (-f, f, -f, f, 0.0, D_TOP), None))


B6 = dict(f=0.03335, ch=0.003, h=0.100, cap=0.0045, xs=0.0164, spring=0.012)


def build_b6():
    k = reg('Item_Battery6V', 'Small', 'Item_Battery6V')
    pk = reg('Battery6V_Print', 'panel', 'Item_Battery6V', merge='Item_Battery6V')
    f, ch, h = B6['f'], B6['ch'], B6['h']
    c = f - ch
    P = [(-c, -f), (c, -f), (f, -c), (f, c), (c, f), (-c, f), (-f, c), (-f, -c)]
    tiles = {0: 'b6_front', 2: 'b6_side', 4: 'b6_front', 6: 'b6_side'}
    for i in range(8):
        a, b = P[i], P[(i + 1) % 8]
        q = [Vector((a[0], a[1], 0.0)), Vector((b[0], b[1], 0.0)), Vector((b[0], b[1], h)), Vector((a[0], a[1], h))]
        if i in tiles:
            u0, v0, u1, v1 = uv(tiles[i])
            pk.poly(q, 0.0, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
        else:
            k.poly(q, Z_B6CHAM)
    k.poly([Vector((p[0], p[1], 0.0)) for p in reversed(P)], Z_B6CAP)                     # the bottom
    f2, c2 = f - 0.0008, c - 0.0008
    P2 = [(-c2, -f2), (c2, -f2), (f2, -c2), (f2, c2), (c2, f2), (-c2, f2), (-f2, c2), (-f2, -c2)]
    zt = h + B6['cap']
    for i in range(8):                                                                  # the cap: a ledge, its sides
        a, b, a2, b2 = P[i], P[(i + 1) % 8], P2[i], P2[(i + 1) % 8]
        face(k, [Vector((a[0], a[1], h)), Vector((b[0], b[1], h)), Vector((b2[0], b2[1], h)), Vector((a2[0], a2[1], h))], Z_B6CAP,
             (0, 0, 1))
        face(k, [Vector((a2[0], a2[1], h)), Vector((b2[0], b2[1], h)), Vector((b2[0], b2[1], zt)), Vector((a2[0], a2[1], zt))],
             Z_B6CAP, Vector(((a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2, 0)))
    planar(pk, [Vector((p[0], p[1], zt)) for p in P2], uv('b6_top'), (-f2, -f2), (f2, f2))
    for xs in (-1, 1):                                                                  # the spring terminals
        coil(k, (xs * B6['xs'], 0.0, zt), (xs * B6['xs'], 0.0, zt + B6['spring']), 0.0034, 0.0007, 4, Z_SPRING)
        k.cyl((xs * B6['xs'], 0.0, zt), (xs * B6['xs'], 0.0, zt + 0.0006), 0.0042, Z_SPRING, 8)
    part('Item_Battery6V', 'item', (0, 0, 0), note='a 4R25 lantern battery (6 V block, zinc-carbon): two spring terminals on '
                                                   'top, + on the left (-x); takes the hand lamp (Slot_Battery) and the lake '
                                                   'sensor; standing, origin under its middle')
    socket('Term_Plus', (-B6['xs'], 0.0, zt + B6['spring']), 'contact', parent='Item_Battery6V', note='the + spring')
    socket('Term_Minus', (B6['xs'], 0.0, zt + B6['spring']), 'contact', parent='Item_Battery6V', note='the - spring')
    MASS['Item_Battery6V'] = 0.55
    BOXES.append(('Battery6V', 'Item_Battery6V', (-f, f, -f, f, 0.0, zt + B6['spring']), None))


# ================================================================ Item_Walkie
WK = dict(w=0.060, d=0.034, h=0.128, r=0.006, bevel=0.0015)


def wk_front_point(px, py, lift=0.0):
    """a pixel of walkie_front (52 x 130) -> a point on the front (x -0.024..0.024, z 0.123..0.003)"""
    return Vector((-0.024 + px / 52.0 * 0.048, -WK['d'] / 2 - lift, 0.123 - py / 130.0 * 0.120))


def wk_top_point(px, py, lift=0.0):
    """a pixel of walkie_top (60 x 34) -> a point on the top (x -0.030..0.030, y 0.017..-0.017)"""
    return Vector((-0.030 + px / 60.0 * 0.060, 0.017 - py / 34.0 * 0.034, WK['h'] + lift))


def build_walkie():
    k = reg('Item_Walkie', 'Small', 'Item_Walkie')
    pk = reg('Walkie_Print', 'panel', 'Item_Walkie', merge='Item_Walkie')
    w, d, h, r, bv = WK['w'], WK['d'], WK['h'], WK['r'], WK['bevel']
    R0 = rrect(Vector((0, 0, 0)), X, Y, w, d, r, 3)
    n = len(R0)
    h1 = h - 0.002
    R1 = [p + Z * h1 for p in R0]
    R2 = [p + Z * h for p in rrect(Vector((0, 0, 0)), X, Y, w - 2 * bv, d - 2 * bv, r - bv, 3)]
    fu0, fv0, fu1, fv1 = uv('walkie_front')
    for j in range(n):
        j2 = (j + 1) % n
        if j == n - 1:                                       # the front flat: 0..0.003 body, the print, 0.123..h1 body
            a, b = R0[j], R0[j2]
            for z0, z1, pr in ((0.0, 0.003, False), (0.003, 0.123, True), (0.123, h1, False)):
                q = [a + Z * z0, b + Z * z0, b + Z * z1, a + Z * z1]
                if pr:
                    pk.poly(q, 0.0, [(fu0, fv0), (fu1, fv0), (fu1, fv1), (fu0, fv1)])
                else:
                    k.poly(q, Z_WK)
        else:
            k.poly([R0[j], R0[j2], R1[j2], R1[j]], Z_WK)
        k.poly([R1[j], R1[j2], R2[j2], R2[j]], Z_WK)
    planar(pk, R2, uv('walkie_top'), (-0.030, -0.017), (0.030, 0.017))
    k.poly(list(reversed(R0)), Z_WK)
    # the knobs (twist parts), the antenna, the LED
    for nm, key, rr, hh, rng, note in (
            ('Walkie_Knob_Channel', 'ch', 0.0072, 0.014, (0.0, 337.5), 'the channel knob: 16 clicks of 22.5 deg (0 = channel 1); '
                                                                       'turns clockwise seen from above (+angle about -z)'),
            ('Walkie_Knob_Volume', 'vol', 0.0058, 0.012, (0.0, 270.0), 'on / off and volume: the first 30 deg click it on, '
                                                                       'then louder to 270; clockwise seen from above')):
        c = wk_top_point(*GT.WALKIE_TOP[key])
        kk = reg(nm, 'Small', 'Item_Walkie')
        kk.lathe(c, Z, [(0.0, rr), (hh - 0.002, rr), (hh, rr - 0.0012)], Z_WK_RUB, 12, cap0=False, cap1=True)
        kk.box_m(c + Vector((0, -rr * 0.55, hh + 0.0004)), (0.0012, rr * 0.9, 0.0008), Z_WK_METAL)     # the pointer (to the front)
        part(nm, 'twist', c, axis=(0, 0, -1), rng=rng, parent='Item_Walkie', removable=False, note=note)
    ca = wk_top_point(*GT.WALKIE_TOP['ant'])
    k.lathe(ca, Z, [(0.0, 0.0066), (0.0050, 0.0066), (0.0064, 0.0052)], Z_WK_METAL, 10, cap0=False, cap1=False)
    k.lathe(ca, Z, [(0.0064, 0.0050), (0.020, 0.0046), (0.108, 0.0036), (0.114, 0.0030), (0.1165, 0.0)], Z_WK_RUB, 10,
            cap0=True, cap1=False)
    led = reg('Walkie_LED', 'led', 'Item_Walkie')
    cl = wk_top_point(*GT.WALKIE_TOP['led'], lift=0.0003)
    quad(led, cl, (0, 0, 1), 0.0026, 0.0026, (0.0, 0.0, 1.0, 1.0), up=(0, 1, 0))
    part('Walkie_LED', 'static', cl, parent='Item_Walkie', note='TX / RX LED: M_Gear_LEDR while sending, M_Gear_LEDG while '
                                                                'receiving, M_Gear_LED_Off (in the file)')
    lx0, ly0, lx1, ly1 = GT.WALKIE_FRONT['lcd']
    a, b = wk_front_point(lx0, ly1), wk_front_point(lx1, ly0)
    lc = Vector(((a.x + b.x) / 2, -d / 2 - 0.0004, (a.z + b.z) / 2))
    lcd = reg('Walkie_LCD', 'lcd', 'Item_Walkie')
    quad(lcd, lc, (0, -1, 0), b.x - a.x, b.z - a.z, (0.0, 0.0, 1.0, 1.0))
    part('Walkie_LCD', 'static', lc, parent='Item_Walkie', note='the LCD: M_Gear_WalkieLCD (lit: CH 01, backlight) / '
                                                                'M_Gear_WalkieLCD_Off; its own texture, UV 0..1 (u right, v up) - '
                                                                'the game may draw its own channel')
    # the PTT key on the left side, the belt clip at the back
    p = reg('Walkie_PTT', 'Small', 'Item_Walkie')
    p.box(-w / 2 - 0.0018, -w / 2 + 0.0002, -0.008, 0.008, 0.066, 0.100, Z_WK_RUB)
    part('Walkie_PTT', 'slide', (-w / 2 - 0.0008, 0.0, 0.083), axis=(1, 0, 0), rng=(0.0, 0.0015), unit='m', parent='Item_Walkie',
         note='PTT (push to talk), the long key on the left side: pushes in 1.5 mm while held')
    k.box(-0.014, 0.014, d / 2, d / 2 + 0.004, 0.096, 0.112, Z_WK)
    k.strip([Vector((0.0, d / 2 + 0.0047, 0.108)), Vector((0.0, d / 2 + 0.0052, 0.072)), Vector((0.0, d / 2 + 0.0062, 0.044)),
             Vector((0.0, d / 2 + 0.0038, 0.037))], (1, 0, 0), 0.0015, 0.030, Z_WK_METAL)
    part('Item_Walkie', 'item', (0, 0, 0), note='a handheld UHF radio (root): standing, origin under its middle; the front '
                                                '(speaker, LCD) to -y; the antenna on the top left')
    socket('Hand_Walkie', (0.0, 0.0, 0.060), 'hand', parent='Item_Walkie', note='grip (the body, the PTT under the thumb of the '
                                                                               'right hand... the left side)')
    socket('Speaker', wk_front_point(26, 26, 0.001), 'audio', parent='Item_Walkie', dir=(0, -1, 0), note='the speaker grille')
    socket('Mic', wk_front_point(*GT.WALKIE_FRONT['mic'], 0.001), 'audio', parent='Item_Walkie', dir=(0, -1, 0),
           note='the microphone holes')
    socket('Antenna_Tip', ca + Z * 0.1165, 'point', parent='Item_Walkie', note='the antenna tip (static on the radio, effects)')
    MASS['Item_Walkie'] = 0.38
    BOXES.extend([('Walkie', 'Item_Walkie', (-w / 2 - 0.002, w / 2, -d / 2, d / 2 + 0.007, 0.0, h), None),
                  ('Walkie_Antenna', 'Item_Walkie', (ca.x - 0.0066, ca.x + 0.0066, ca.y - 0.0066, ca.y + 0.0066, h, h + 0.1165), None)])


# ================================================================ Item_Lantern (6 V hand lamp, amber lens)
LT = dict(w=0.090, d=0.090, h=0.135, r=0.008, ox=0.035, oz0=0.008, oz1=0.127, head_z=0.090, head_r=0.045)


def build_lantern():
    k = reg('Item_Lantern', 'Small', 'Item_Lantern')
    w, d, h, r = LT['w'], LT['d'], LT['h'], LT['r']
    ox, oz0, oz1 = LT['ox'], LT['oz0'], LT['oz1']
    R0 = rrect(Vector((0, 0, 0)), X, Y, w, d, r, 3)
    n = len(R0)
    h1 = h - 0.003
    R1 = [p + Z * h1 for p in R0]
    R2 = [p + Z * h for p in rrect(Vector((0, 0, 0)), X, Y, w - 0.004, d - 0.004, r - 0.002, 3)]
    back = 2 * 4 - 1                                          # the back flat: R0[7] (x = w/2 - r) -> R0[8] (x = -w/2 + r)
    for j in range(n):
        j2 = (j + 1) % n
        if j == back:                                         # round the battery opening
            xa, xb = R0[j].x, R0[j2].x
            yb = d / 2
            for (x0, x1, z0, z1) in ((xb, xa, 0.0, oz0), (xb, xa, oz1, h1), (xb, -ox, oz0, oz1), (ox, xa, oz0, oz1)):
                face(k, [Vector((x0, yb, z0)), Vector((x1, yb, z0)), Vector((x1, yb, z1)), Vector((x0, yb, z1))], Z_LAMP, (0, 1, 0))
        else:
            k.poly([R0[j], R0[j2], R1[j2], R1[j]], Z_LAMP)
        k.poly([R1[j], R1[j2], R2[j2], R2[j]], Z_LAMP_BK)
    k.poly(R2, Z_LAMP_BK)
    k.poly(list(reversed(R0)), Z_LAMP)
    # the battery compartment behind the opening (dark, faces inwards)
    ci = dict(x0=-ox, x1=ox, y0=-0.040, y1=d / 2, z0=oz0, z1=oz1)
    face(k, [(-ox, ci['y0'], oz0), (ox, ci['y0'], oz0), (ox, ci['y0'], oz1), (-ox, ci['y0'], oz1)], Z_CAVITY, (0, 1, 0))
    face(k, [(-ox, ci['y0'], oz0), (-ox, ci['y1'], oz0), (-ox, ci['y1'], oz1), (-ox, ci['y0'], oz1)], Z_CAVITY, (1, 0, 0))
    face(k, [(ox, ci['y0'], oz0), (ox, ci['y1'], oz0), (ox, ci['y1'], oz1), (ox, ci['y0'], oz1)], Z_CAVITY, (-1, 0, 0))
    face(k, [(-ox, ci['y0'], oz0), (ox, ci['y0'], oz0), (ox, ci['y1'], oz0), (-ox, ci['y1'], oz0)], Z_CAVITY, (0, 0, 1))
    face(k, [(-ox, ci['y0'], oz1), (ox, ci['y0'], oz1), (ox, ci['y1'], oz1), (-ox, ci['y1'], oz1)], Z_CAVITY, (0, 0, -1))
    for xs in (-1, 1):                                        # the lamp's contacts at the top of the compartment
        k.box(xs * B6['xs'] - 0.003, xs * B6['xs'] + 0.003, -0.002, 0.004, oz1 - 0.003, oz1, Z_SPRING)
    # the head on the front: the barrel, the chrome bezel, the amber lens
    hc = Vector((0.0, -d / 2, LT['head_z']))
    k.lathe(hc, -Y, [(-0.004, 0.036), (0.006, LT['head_r']), (0.028, LT['head_r'])], Z_LAMP, 18, cap0=False, cap1=False)
    k.lathe(hc, -Y, [(0.028, 0.0465), (0.0335, 0.0465), (0.0350, 0.0390), (0.0320, 0.0378)], Z_CHROME, 18, cap0=False, cap1=False)
    ln = reg('Lantern_Lens', 'lens:amber', 'Item_Lantern')
    lc = hc - Y * 0.0322
    ln.disc_uv(lc, -Y, 0.0380, uv('lens_amber'), seg=18, dome=0.003)
    part('Lantern_Lens', 'static', lc, parent='Item_Lantern', note='the amber lens: M_Gear_LensAmber (lit, glows by day too) / '
                                                                   'M_Gear_LensAmber_Off (in the file)')
    # the handle over the top, the slide switch, the plates
    k.strip([Vector((0.0, 0.030, h - 0.002)), Vector((0.0, 0.028, h + 0.028)), Vector((0.0, 0.014, h + 0.041)),
             Vector((0.0, -0.014, h + 0.041)), Vector((0.0, -0.028, h + 0.028)), Vector((0.0, -0.030, h - 0.002))],
            (1, 0, 0), 0.008, 0.020, Z_LAMP_BK)
    k.box(-0.035, -0.021, -0.034, -0.016, h, h + 0.002, Z_LAMP_BK)
    sw = reg('Lantern_Switch', 'Small', 'Item_Lantern')
    swc = Vector((-0.028, -0.019, h + 0.0045))
    sw.box_m(swc, (0.007, 0.007, 0.005), Z_LAMP_SW)
    part('Lantern_Switch', 'slide', swc, axis=(0, -1, 0), rng=(0.0, 0.009), unit='m', parent='Item_Lantern',
         note='the red slide switch on the top: forward (to the lens) 9 mm = on')
    pl = reg('Lantern_Plate', 'panel', 'Item_Lantern', merge='Item_Lantern')
    for xs in (-1, 1):
        quad(pl, (xs * (w / 2 + 0.0004), 0.004, 0.052), (xs, 0, 0), 0.050, 0.031, uv('lamp_plate'))
    # the battery door (hinged along its bottom edge, opens out to the back)
    dr = reg('Lantern_Door', 'Small', 'Item_Lantern')
    dr.box(-ox - 0.0006, ox + 0.0006, d / 2 - 0.0025, d / 2 + 0.0005, oz0 - 0.0006, oz1 + 0.0006, Z_LAMP)
    dr.box(-0.008, 0.008, d / 2 + 0.0005, d / 2 + 0.0025, oz1 - 0.010, oz1 - 0.002, Z_LAMP_BK)      # the latch
    part('Lantern_Door', 'hinge', (0.0, d / 2 + 0.0005, oz0 - 0.0006), axis=(-1, 0, 0), rng=(0, 90), parent='Item_Lantern',
         states=['closed', 'open'], note='the battery door at the back: hinge along its bottom edge, opens out up to 90 deg; '
                                         'behind it the 4R25 (Slot_Battery)')
    part('Item_Lantern', 'item', (0, 0, 0), note='a 6 V hand lamp with an amber lens (root): the yellow light (R1); standing, '
                                                 'origin under its middle, the lens to -y')
    socket('Light_Lantern', lc - Y * 0.003, 'light', parent='Item_Lantern', dir=(0, -1, 0), color=[1.0, 0.62, 0.20],
           spot_angle=60.0, range=14.0, note='a spot light (suggested colour linear RGB, angle, range): on while the lamp is on '
                                             'and has a charged battery')
    socket('Hand_Lantern', (0.0, 0.0, h + 0.040), 'hand', parent='Item_Lantern', note='carried by the handle')
    socket('Slot_Battery', (0.0, 0.0025, oz0), 'slot', parent='Item_Lantern', up=(0, 0, 1), forward=(0, -1, 0),
           note='Item_Battery6V\'s origin here, upright, its + spring to the left (-x); the door open')
    MASS['Item_Lantern'] = 0.45
    BOXES.extend([('Lantern_Body', 'Item_Lantern', (-w / 2, w / 2, -d / 2, d / 2, 0.0, h), None),
                  ('Lantern_Head', 'Item_Lantern', (-0.0465, 0.0465, -d / 2 - 0.036, -d / 2, LT['head_z'] - 0.0465,
                                                    LT['head_z'] + 0.0465), None),
                  ('Lantern_Handle', 'Item_Lantern', (-0.010, 0.010, -0.034, 0.034, h, h + 0.045), None),
                  ('Lantern_Door', 'Lantern_Door', (-ox, ox, d / 2 - 0.0025, d / 2 + 0.0025, oz0, oz1), None)])


# ================================================================ Item_Headlamp
HL = dict(a=0.078, b=0.098, z0=0.0125, z1=0.0375, t=0.002, zc=0.025)


def build_headlamp():
    k = reg('Item_Headlamp', 'Small', 'Item_Headlamp')
    a, b, z0, z1, t, zc = HL['a'], HL['b'], HL['z0'], HL['z1'], HL['t'], HL['zc']
    N = 28
    pts = []
    for i in range(N):
        ph = TAU * i / N
        p = Vector((a * math.cos(ph), b * math.sin(ph), 0.0))
        nn = Vector((math.cos(ph) / a, math.sin(ph) / b, 0.0)).normalized()
        pts.append((p, nn))
    for i in range(N):                                       # the elastic band: outside, inside, the two edges
        (p0, n0), (p1, n1) = pts[i], pts[(i + 1) % N]
        o0, o1, i0, i1 = p0 + n0 * t / 2, p1 + n1 * t / 2, p0 - n0 * t / 2, p1 - n1 * t / 2
        face(k, [o0 + Z * z0, o1 + Z * z0, o1 + Z * z1, o0 + Z * z1], Z_BAND, n0 + n1)
        face(k, [i0 + Z * z0, i1 + Z * z0, i1 + Z * z1, i0 + Z * z1], Z_BAND, -(n0 + n1))
        face(k, [o0 + Z * z1, o1 + Z * z1, i1 + Z * z1, i0 + Z * z1], Z_BAND, (0, 0, 1))
        face(k, [o0 + Z * z0, o1 + Z * z0, i1 + Z * z0, i0 + Z * z0], Z_BAND, (0, 0, -1))
    yb = -b - t / 2
    k.box(-0.029, 0.029, yb - 0.006, yb, zc - 0.017, zc + 0.017, Z_HL)                 # the base plate on the band
    for xs in (-1, 1):                                                                  # the lamp's side brackets
        k.box(xs * 0.0225 - 0.0015, xs * 0.0225 + 0.0015, yb - 0.016, yb - 0.006, zc - 0.008, zc + 0.008, Z_HL)
    piv = Vector((0.0, yb - 0.009, zc))
    lm = reg('Headlamp_Lamp', 'Small', 'Item_Headlamp')
    lm.lathe(piv, -Y, [(0.0, 0.0150), (0.003, 0.0205), (0.024, 0.0205), (0.026, 0.0198)], Z_HL, 16, cap0=True, cap1=False)
    part('Headlamp_Lamp', 'hinge', piv, axis=(1, 0, 0), rng=(0, 45), parent='Item_Headlamp',
         note='the lamp tilts down on its brackets, 0..45 deg')
    bz = reg('Headlamp_Bezel', 'Small', 'Item_Headlamp')
    bz.lathe(piv, -Y, [(0.026, 0.0212), (0.0325, 0.0212), (0.0335, 0.0168), (0.0315, 0.0162)], Z_HL_BEZEL, 16, cap0=False,
             cap1=False)
    part('Headlamp_Bezel', 'twist', piv, axis=(0, 1, 0), rng=(0.0, 90.0), parent='Headlamp_Lamp', removable=False,
         note='the ribbed bezel: a quarter turn clockwise (seen from the front) switches the lamp on')
    ln = reg('Headlamp_Lens', 'lens:clear', 'Item_Headlamp')
    lc = piv - Y * 0.0318
    ln.disc_uv(lc, -Y, 0.0165, uv('lens_clear'), seg=16, dome=0.002)
    part('Headlamp_Lens', 'static', lc, parent='Headlamp_Lamp', note='the clear lens: M_Gear_LensClear (lit) / '
                                                                      'M_Gear_LensClear_Off (in the file)')
    # the battery box at the back, its lid plate, the cable along the band's right side
    k.box(-0.031, 0.031, b + t / 2, b + t / 2 + 0.024, 0.0, 0.046, Z_HL)
    pl = reg('Headlamp_Plate', 'panel', 'Item_Headlamp', merge='Item_Headlamp')
    quad(pl, (0.0, b + t / 2 + 0.0244, 0.026), (0, 1, 0), 0.040, 0.016, uv('hl_plate'))
    cab = [Vector((0.022, b + 0.010, 0.040))]
    for ph in np.linspace(math.radians(72), math.radians(-78), 12):
        p = Vector((a * math.cos(ph), b * math.sin(ph), 0.0))
        nn = Vector((math.cos(ph) / a, math.sin(ph) / b, 0.0)).normalized()
        cab.append(p + nn * 0.004 + Z * 0.0395)
    cab.append(Vector((0.014, yb - 0.004, zc + 0.012)))
    k.tube(cab, 0.0018, Z_CABLE, 4)
    part('Item_Headlamp', 'item', (0, 0, 0), note='a headlamp (root): the band as worn (a loop for a head 0.156 x 0.196 m), the '
                                                  'lamp at the front (-y), the battery box at the back; on a table it rests on '
                                                  'the lamp and the box')
    socket('Light_Headlamp', lc - Y * 0.002, 'light', parent='Headlamp_Lamp', dir=(0, -1, 0), color=[1.0, 0.96, 0.90],
           spot_angle=40.0, range=18.0, note='a spot light (suggested): on while switched on (the bezel) with charge left')
    socket('Wear_Head', (0.0, 0.0, zc), 'wear', parent='Item_Headlamp', forward=(0, -1, 0),
           note='worn: this point on the head\'s centre at the brow line, -y to the front (the band then sits round the head)')
    MASS['Item_Headlamp'] = 0.22
    BOXES.append(('Headlamp', 'Item_Headlamp', (-a - t, a + t, yb - 0.044, b + t / 2 + 0.024, 0.0, 0.046), None))


# ================================================================ Item_Cart
CT = dict(w=0.55, l=0.90, deck=0.340, wr=0.13, ww=0.085, wx=0.2175, wy_f=0.32, wy_b=0.29, trail=0.040)


def wheel(k, c, w, r, seg=14):
    """a pneumatic wheel on an axle along x through c: the tyre, both rims, the hub"""
    c = Vector(c)
    hw = w / 2
    k.lathe(c - X * hw, X, [(0.0025, r * 0.70), (0.0, r * 0.84), (0.007, r * 0.97), (0.022, r), (w - 0.022, r), (w - 0.007, r * 0.97),
                            (w, r * 0.84), (w - 0.0025, r * 0.70)], Z_TYRE, seg, cap0=False, cap1=False)
    for s in (-1, 1):
        cc = c + X * s * (hw - 0.0025)
        k.lathe(cc, X * s, [(0.0, r * 0.70), (-0.006, r * 0.48), (-0.010, r * 0.20), (-0.010, 0.014)], Z_RIM, seg, cap0=False,
                cap1=False)
    k.cyl(c - X * (hw + 0.006), c + X * (hw + 0.006), 0.016, Z_ZINC, 8)


def build_cart():
    k = reg('Item_Cart', 'Haul', 'Item_Cart')
    w, l, dk, wr, ww = CT['w'], CT['l'], CT['deck'], CT['wr'], CT['ww']
    fz0, fz1 = dk - 0.058, dk - 0.018                                                  # the frame's channel under the deck
    box6(k, (-w / 2, -l / 2, dk - 0.018), (w / 2, l / 2, dk), {'*': Z_DECK})
    for xs in (-1, 1):
        k.box(xs * w / 2 - (0.030 if xs > 0 else 0.0), xs * w / 2 + (0.0 if xs > 0 else 0.030), -l / 2, l / 2, fz0, fz1, Z_CART)
    for ys in (-1, 1):
        k.box(-w / 2 + 0.030, w / 2 - 0.030, ys * l / 2 - (0.030 if ys > 0 else 0.0), ys * l / 2 + (0.0 if ys > 0 else 0.030),
              fz0, fz1, Z_CART)
    for yy in (-CT['wy_f'], 0.0, CT['wy_b']):
        k.box(-w / 2 + 0.030, w / 2 - 0.030, yy - 0.020, yy + 0.020, fz0 + 0.008, fz1, Z_CART)
    # the handle at the back (+y): two uprights, the grip bar, a brace; rubber grips
    for xs in (-1, 1):
        k.tube([Vector((xs * 0.245, l / 2 - 0.015, fz0 + 0.01)), Vector((xs * 0.245, l / 2 - 0.005, dk + 0.04)),
                Vector((xs * 0.245, l / 2 + 0.045, 0.90)), Vector((xs * 0.205, l / 2 + 0.050, 0.955))], 0.0125, Z_CART, 8)
    k.tube([Vector((-0.205, l / 2 + 0.050, 0.955)), Vector((0.205, l / 2 + 0.050, 0.955))], 0.0125, Z_CART, 8, caps=False)
    k.tube([Vector((-0.245, l / 2 + 0.017, 0.62)), Vector((0.245, l / 2 + 0.017, 0.62))], 0.010, Z_CART, 6)
    for xs in (-1, 1):
        k.cyl((xs * 0.075, l / 2 + 0.050, 0.955), (xs * 0.195, l / 2 + 0.050, 0.955), 0.0165, Z_GRIP, 8)
    # the fixed wheels at the front (-y): forks, axle
    for xs, nm in ((-1, 'FL'), (1, 'FR')):
        wx = xs * CT['wx']
        wy = -CT['wy_f']
        for s in (-1, 1):
            k.box(wx + s * 0.052 - 0.002, wx + s * 0.052 + 0.002, wy - 0.022, wy + 0.022, wr - 0.015, fz0, Z_ZINC)
        k.cyl((wx - 0.056, wy, wr), (wx + 0.056, wy, wr), 0.007, Z_ZINC, 6)
        wk = reg('Cart_Wheel_' + nm, 'Haul', 'Item_Cart')
        wheel(wk, (wx, wy, wr), ww, wr)
        part('Cart_Wheel_' + nm, 'spin', (wx, wy, wr), axis=(1, 0, 0), parent='Item_Cart',
             note=f'front {"left" if xs < 0 else "right"} wheel (fixed): spins about its axle (x); rolling forward (to -y) '
                  'turns it the positive way about +x')
    # the swivel casters at the back (+y): plate, bearing, fork (part), wheel (part of the fork)
    for xs, nm in ((-1, 'BL'), (1, 'BR')):
        sx, sy = xs * CT['wx'], CT['wy_b']
        k.box(sx - 0.045, sx + 0.045, sy - 0.045, sy + 0.045, fz0 - 0.006, fz0, Z_ZINC)
        cs = reg('Cart_Caster_' + nm, 'Haul', 'Item_Cart')
        cs.cyl((sx, sy, fz0 - 0.006), (sx, sy, fz0 - 0.022), 0.032, Z_ZINC, 10)
        ay = sy + CT['trail']
        tv = Vector((0, ay - sy, wr - (fz0 - 0.022)))
        for s in (-1, 1):                                                               # the fork's two plates
            mid = Vector((sx + s * 0.052, (sy + ay) / 2, (fz0 - 0.022 + wr) / 2))
            cs.box_m(mid, (0.004, tv.length + 0.02, 0.040), Z_ZINC, frame_of(tv, X))
        cs.box(sx - 0.054, sx + 0.054, sy - 0.026, sy + 0.026, fz0 - 0.030, fz0 - 0.022, Z_ZINC)
        cs.cyl((sx - 0.056, ay, wr), (sx + 0.056, ay, wr), 0.007, Z_ZINC, 6)
        part('Cart_Caster_' + nm, 'spin', (sx, sy, fz0 - 0.014), axis=(0, 0, 1), parent='Item_Cart',
             note=f'back {"left" if xs < 0 else "right"} swivel caster: turns freely about z (the wheel trails {CT["trail"]} m '
                  'behind its pivot)')
        wk = reg('Cart_Wheel_' + nm, 'Haul', 'Item_Cart')
        wheel(wk, (sx, ay, wr), ww, wr)
        part('Cart_Wheel_' + nm, 'spin', (sx, ay, wr), axis=(1, 0, 0), parent='Cart_Caster_' + nm,
             note='the caster\'s wheel: spins about its axle')
    part('Item_Cart', 'static', (0, 0, 0), note='a platform cart (root): origin on the ground under the deck\'s middle; the push '
                                                'handle at the back (+y), so it rolls to -y; deck 0.55 x 0.90 m at 0.34 m')
    socket('Cargo_Cart', (0.0, 0.0, dk), 'cargo', parent='Item_Cart', size=[w - 0.02, l - 0.02],
           note='the deck: loads stand on it (top at z = 0.34); the game parents them to the cart while it moves')
    for xs, nm in ((-1, 'L'), (1, 'R')):
        socket('Hand_Cart_' + nm, (xs * 0.135, l / 2 + 0.050, 0.955), 'hand', parent='Item_Cart', note='the grip on the bar')
    MASS['Item_Cart'] = 22.0
    BOXES.extend([('Cart_Deck', 'Item_Cart', (-w / 2, w / 2, -l / 2, l / 2, fz0, dk), None),
                  ('Cart_Handle', 'Item_Cart', (-0.258, 0.258, l / 2 - 0.03, l / 2 + 0.064, dk, 0.968), None)])
    for nm, par in (('FL', 'Cart_Wheel_FL'), ('FR', 'Cart_Wheel_FR'), ('BL', 'Cart_Wheel_BL'), ('BR', 'Cart_Wheel_BR')):
        c = Vector(CONTRACT['parts'][par]['pivot'])
        BOXES.append(('Cart_Wheel_' + nm, par, (c.x - ww / 2, c.x + ww / 2, c.y - wr, c.y + wr, c.z - wr, c.z + wr), None))


# ================================================================ Item_Sled (pulk)
SLED = [(-0.650, 0.150, 0.180, 0.236), (-0.622, 0.205, 0.120, 0.228), (-0.572, 0.240, 0.070, 0.218), (-0.502, 0.262, 0.036, 0.208),
        (-0.402, 0.274, 0.012, 0.202), (-0.282, 0.279, 0.000, 0.200), (0.100, 0.280, 0.000, 0.200), (0.500, 0.279, 0.000, 0.200),
        (0.600, 0.276, 0.006, 0.202), (0.650, 0.272, 0.016, 0.204)]
RUN_X = (0.135, 0.125, 0.095, 0.085)


def sled_sections(inner):
    out = []
    for si, (y, w, zb, zt) in enumerate(SLED):
        zb_e = zb + 0.006
        dep = 0.006 if zb <= 0.012 and 0 < si < len(SLED) - 1 else 0.0
        rx = [x * (w / 0.28) for x in RUN_X]
        if not inner:
            xs = [-w, -w + 0.012, -w + 0.035, -w + 0.060, -rx[0], -rx[1], -rx[2], -rx[3], rx[3], rx[2], rx[1], rx[0], w - 0.060,
                  w - 0.035, w - 0.012, w]
            zs = [zt, zb_e + 0.050, zb_e + 0.008, zb_e, zb_e, zb_e - dep, zb_e - dep, zb_e, zb_e, zb_e - dep, zb_e - dep, zb_e,
                  zb_e, zb_e + 0.008, zb_e + 0.050, zt]
            yy = y
        else:
            xs = [-w + 0.006, -w + 0.018, -w + 0.040, -w + 0.064, -rx[0], -rx[1], -rx[2], -rx[3], rx[3], rx[2], rx[1], rx[0],
                  w - 0.064, w - 0.040, w - 0.018, w - 0.006]
            zf = zb_e + 0.006
            zs = [zt, zf + 0.050, zf + 0.008, zf] + [zf] * 8 + [zf, zf + 0.008, zf + 0.050, zt]
            yy = y + (0.006 if si == 0 else (-0.006 if si == len(SLED) - 1 else 0.0))
        out.append([Vector((x, yy, z)) for x, z in zip(xs, zs)])
    return out


def build_sled():
    k = reg('Item_Sled', 'Haul', 'Item_Sled')
    O, I = sled_sections(False), sled_sections(True)
    ctr = lambda p: Vector((0.0, p.y, 0.16))
    loft_open(k, O, Z_SLED, lambda c: (c - ctr(c)) * Vector((1, 0.0, 1)) + Vector((0, 0, -0.001)))
    loft_open(k, I, Z_SLED_IN, lambda c: -((c - ctr(c)) * Vector((1, 0.0, 1))))
    for s in range(len(SLED) - 1):                                                      # the rims: tops of both walls
        for i in (0, 15):
            face(k, [O[s][i], I[s][i], I[s + 1][i], O[s + 1][i]], Z_SLED, (0, 0, 1))
    face(k, O[0], Z_SLED, (0, -1, 0))                                                   # the bow and the stern walls
    face(k, I[0], Z_SLED_IN, (0, 1, 0))
    face(k, O[-1], Z_SLED, (0, 1, 0))
    face(k, I[-1], Z_SLED_IN, (0, -1, 0))
    for s in (0, -1):
        face(k, [O[s][0], O[s][15], I[s][15], I[s][0]], Z_SLED, (0, 0, 1))
    # the rolled rim (a tube along both walls round the stern), the grab ropes through eyes along the sides, the bow eye
    for sgn in (-1, 1):
        rim = [Vector((sgn * (w + 0.002), y, zt + 0.004)) for (y, w, zb, zt) in SLED]
        k.tube(rim, 0.008, Z_SLED, 6, caps=True)
        rope = []
        for j, y in enumerate(np.linspace(-0.50, 0.58, 7)):
            w_ = float(np.interp(y, [s_[0] for s_ in SLED], [s_[1] for s_ in SLED]))
            zt_ = float(np.interp(y, [s_[0] for s_ in SLED], [s_[3] for s_ in SLED]))
            rope.append(Vector((sgn * (w_ + 0.010), y, zt_ - 0.030)))
            k.box_m((sgn * (w_ + 0.004), y, zt_ - 0.030), (0.012, 0.022, 0.018), Z_SLED)
            if j < 6:
                y2 = y + (0.58 + 0.50) / 12
                w2 = float(np.interp(y2, [s_[0] for s_ in SLED], [s_[1] for s_ in SLED]))
                zt2 = float(np.interp(y2, [s_[0] for s_ in SLED], [s_[3] for s_ in SLED]))
                rope.append(Vector((sgn * (w2 + 0.016), y2, zt2 - 0.062)))
        k.tube(rope, 0.0045, Z_ROPE, 5, caps=True)
    k.tube([Vector((-0.274, 0.646, 0.207)), Vector((0.274, 0.646, 0.207))], 0.008, Z_SLED, 6)            # the stern's rim
    ring_tube(k, (0.0, -0.664, 0.208), (1, 0, 0), 0.014, 0.0032, Z_ZINC, seg=12)
    k.box(-0.020, 0.020, -0.656, -0.640, 0.190, 0.226, Z_SLED)
    # the tow rope lying out in front, its T-handle (Sled_Tow - the game hides it and draws its own rope while pulling)
    tw = reg('Sled_Tow', 'Haul', 'Item_Sled')
    path = [Vector((0.0, -0.664, 0.194)), Vector((0.0, -0.700, 0.120)), Vector((0.010, -0.760, 0.040)),
            Vector((0.040, -0.880, 0.008)), Vector((0.050, -1.050, 0.006)), Vector((0.000, -1.250, 0.006)),
            Vector((-0.050, -1.420, 0.006)), Vector((-0.030, -1.560, 0.010)), Vector((0.0, -1.640, 0.014))]
    tw.tube(path, 0.0055, Z_ROPE, 5)
    tw.cyl((-0.075, -1.655, 0.016), (0.075, -1.655, 0.016), 0.0155, Z_TWOOD, 8)
    part('Sled_Tow', 'static', (0.0, -1.655, 0.016), parent='Item_Sled',
         note='the tow rope and its T-handle lying out in front: hide it while pulling and draw a rope from Tow_Anchor to the '
              'hand (Hand_Sled is where the handle lies)')
    part('Item_Sled', 'static', (0, 0, 0), note='a plastic pulk (root): origin on the ground under its middle; the bow (eye, '
                                                'tow rope) to -y; inside 0.53 x 1.2 m, walls 0.2 m')
    socket('Tow_Anchor', (0.0, -0.664, 0.194), 'rope', parent='Item_Sled', note='the bow eye: the tow rope\'s end')
    socket('Hand_Sled', (0.0, -1.655, 0.016), 'hand', parent='Sled_Tow', note='the T-handle (where it lies)')
    socket('Cargo_Sled', (0.0, 0.05, 0.012), 'cargo', parent='Item_Sled', size=[0.50, 1.05],
           note='the floor inside: loads lie on it (z = 0.012); the game parents them while it is pulled')
    MASS['Item_Sled'] = 5.5
    BOXES.extend([('Sled_Floor', 'Item_Sled', (-0.27, 0.27, -0.45, 0.64, 0.0, 0.012), None),
                  ('Sled_Left', 'Item_Sled', (-0.288, -0.268, -0.55, 0.65, 0.0, 0.208), None),
                  ('Sled_Right', 'Item_Sled', (0.268, 0.288, -0.55, 0.65, 0.0, 0.208), None),
                  ('Sled_Bow', 'Item_Sled', (-0.26, 0.26, -0.672, -0.45, 0.006, 0.236), (-20.0, 0.0, 0.0)),
                  ('Sled_Stern', 'Item_Sled', (-0.27, 0.27, 0.638, 0.654, 0.0, 0.212), None)])


# ================================================================ Item_Doll
DOLL = dict(neck=0.212, hc=0.268, hr=0.054)


def build_doll():
    k = reg('Item_Doll', 'Small', 'Item_Doll')
    # the dress: a bell of ellipse rings from the spread hem to the shoulders (flatter front to back)
    st = [(0.0, 0.090, 0.078), (0.010, 0.093, 0.081), (0.032, 0.088, 0.077), (0.060, 0.075, 0.064), (0.092, 0.058, 0.048),
          (0.115, 0.050, 0.040), (0.148, 0.052, 0.040), (0.172, 0.056, 0.041), (0.188, 0.052, 0.038), (0.198, 0.036, 0.028),
          (0.203, 0.016, 0.014)]
    rings = ell_rings((0, 0.006, 0), Z, st, seg=14)
    k.loft(rings, [Z_DRESS] * (len(rings) - 1), cap0=Z_DRESS)
    k.lathe((0, 0.004, 0.0), Z, [(0.200, 0.016), (0.198, 0.044), (0.192, 0.050)], Z_COLLAR, 14, cap0=False, cap1=False)
    k.cyl((0, 0.004, 0.196), (0, 0.004, DOLL['neck'] + 0.006), 0.0135, Z_SKIN, 8)
    # the arms: sleeves resting forward on the lap, mitten hands
    for xs in (-1, 1):
        arm = [Vector((xs * 0.046, 0.004, 0.186)), Vector((xs * 0.062, -0.004, 0.150)), Vector((xs * 0.064, -0.022, 0.112)),
               Vector((xs * 0.052, -0.058, 0.084))]
        k.tube(arm, 0.0155, Z_DRESS, 8)
        k.cyl(arm[-1], arm[-1] + (arm[-1] - arm[-2]).normalized() * 0.006, 0.0145, Z_COLLAR, 8)          # the cuff
        hd = (arm[-1] - arm[-2]).normalized()
        k.lathe(arm[-1] + hd * 0.006, hd, [(0.0, 0.0110), (0.014, 0.0118), (0.022, 0.0085), (0.026, 0.0)], Z_SKIN, 8, cap0=True,
                cap1=False)
    # the legs out in front: white stockings, black strap shoes (toes up)
    for xs in (-1, 1):
        k.tube([Vector((xs * 0.031, -0.010, 0.024)), Vector((xs * 0.034, -0.090, 0.0175)), Vector((xs * 0.036, -0.150, 0.0168))],
               0.0165, Z_SOCK, 8)
        VM.rbox(k, (xs * 0.036, -0.163, 0.031), (0.032, 0.026, 0.046), Z_SHOE, r=0.010, ch=0.004, axis='y')
    # the head (Doll_Head, turns about z at the neck): a sphere - the face (panel, planar), the hair (top, sides, back),
    # skin under the chin; a fringe over the brow; two braids with red ribbons
    hk = reg('Doll_Head', 'Small', 'Item_Doll')
    fk = reg('Doll_Face', 'panel', 'Item_Doll', merge='Doll_Head')
    c = Vector((0.0, 0.0, DOLL['hc']))
    r = DOLL['hr']
    rz = r * 1.04
    NL, NA = 9, 16
    fx, fz0, fz1 = 0.93 * r, 0.80 * rz, 0.52 * rz                                  # the face tile's extent (64 x 48)
    u0, v0, u1, v1 = uv('doll_face')

    def P(i, j):
        lat = -math.pi / 2 + math.pi * i / NL
        lon = TAU * j / NA - math.pi / 2                                              # j = 0 at the front (-y)
        return c + Vector((r * math.cos(lat) * math.cos(lon), r * math.cos(lat) * math.sin(lon), rz * math.sin(lat)))
    for i in range(NL):
        for j in range(NA):
            q = [P(i, j), P(i, j + 1), P(i + 1, j + 1), P(i + 1, j)]
            if i == 0:
                q = [q[0], q[2], q[3]]
            elif i == NL - 1:
                q = q[:3]
            cc = sum(q, Vector()) / len(q) - c
            lat = math.degrees(math.asin(max(-1.0, min(1.0, cc.z / max(cc.length, 1e-9)))))
            front = -cc.y / max(math.hypot(cc.x, cc.y), 1e-9)                          # cos of the angle from the front
            if front > 0.45 and -52 < lat < 24:
                planar(fk, q, (u0, v0, u1, v1), (-fx, c.z - fz0), (fx, c.z + fz1), axes=('x', 'z'))
            else:
                zone = Z_HAIR if (lat > 24 or (front <= 0.45 and lat > -38) or (front < -0.3 and lat > -62)) else Z_SKIN
                face(hk, q, zone, cc)
    fr = []
    for j in range(-5, 6):                                                              # the fringe: a band proud of the brow
        lon = math.radians(j * 11.0) - math.pi / 2
        row = []
        for lat_d, off in ((20.0, 0.0034), (31.0, 0.0030), (44.0, 0.0012)):
            lat = math.radians(lat_d + (2.5 if j % 2 else 0.0) * (lat_d == 20.0))
            row.append(c + Vector(((r + off) * math.cos(lat) * math.cos(lon), (r + off) * math.cos(lat) * math.sin(lon),
                                   (rz + off) * math.sin(lat))))
        fr.append(row)
    for a_, b_ in zip(fr[:-1], fr[1:]):
        for i in range(2):
            q = [a_[i], b_[i], b_[i + 1], a_[i + 1]]
            face(hk, q, Z_HAIR, sum(q, Vector()) / 4 - c)
    for xs in (-1, 1):
        br = [Vector((xs * 0.046, 0.016, 0.262)), Vector((xs * 0.054, 0.024, 0.232)), Vector((xs * 0.057, 0.026, 0.205)),
              Vector((xs * 0.056, 0.022, 0.178))]
        hk.tube(br, 0.0095, Z_HAIR, 6)
        for t in (0.35, 0.65):                                                         # the plaits' knots
            p = br[1].lerp(br[2], t) if t < 0.5 else br[2].lerp(br[3], t)
            hk.cyl(p - Z * 0.004, p + Z * 0.004, 0.0108, Z_HAIR, 6)
        rb = br[-1] + Vector((0, 0, -0.004))
        hk.box_m(rb, (0.030, 0.008, 0.012), Z_RIBBON)
        hk.tube([br[-1] + Vector((0, 0, -0.008)), br[-1] + Vector((xs * 0.002, -0.002, -0.022))], 0.0068, Z_HAIR, 5)
    part('Doll_Head', 'twist', (0.0, 0.0, DOLL['neck']), axis=(0, 0, 1), rng=(-170.0, 170.0), parent='Item_Doll',
         removable=False, note='the head turns about the neck (z): +angle to her left (counter-clockwise seen from above); the '
                               'demo\'s end - after the postcard\'s menu closes, turn it towards the camera')
    part('Item_Doll', 'item', (0, 0, 0), note='the day-3 doll (root): sitting with her legs out to the front (-y), origin on the '
                                              'surface under her middle; it moves only when nobody looks (the game places it)')
    socket('Doll_Eyes', c + Vector((0.0, -r - 0.002, -0.004)), 'look', parent='Doll_Head', dir=(0, -1, 0),
           note='between the painted eyes: for "is anyone looking at her" and her gaze')
    socket('Hand_Doll', (0.0, 0.004, 0.150), 'hand', parent='Item_Doll', note='picked up round the waist')
    MASS['Item_Doll'] = 0.45
    BOXES.extend([('Doll_Body', 'Item_Doll', (-0.095, 0.095, -0.180, 0.090, 0.0, DOLL['neck']), None),
                  ('Doll_Head', 'Doll_Head', (-0.064, 0.064, -0.058, 0.060, DOLL['neck'], c.z + rz + 0.004), None)])


# ================================================================ Item_Postcard
PC_W, PC_H = 0.148, 0.105


def build_postcard():
    fk = reg('Item_Postcard', 'pc_front', 'Item_Postcard')
    bk = reg('Postcard_Back', 'pc_back', 'Item_Postcard', merge='Item_Postcard')
    nx, ny = 6, 4

    def zc(x, y):
        return 0.0004 + 0.0028 * ((abs(x) / (PC_W / 2)) ** 3) * (0.4 + 0.6 * (abs(y) / (PC_H / 2)) ** 2)
    xs = [-PC_W / 2 + PC_W * i / nx for i in range(nx + 1)]
    ys = [-PC_H / 2 + PC_H * j / ny for j in range(ny + 1)]
    for j in range(ny):                                     # triangles split the same way on both faces (the curled
        for i in range(nx):                                 # corners are not planar: the back must not poke through)
            q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            for tri in ((q[0], q[1], q[2]), (q[0], q[2], q[3])):
                top = [Vector((xs[a], ys[b], zc(xs[a], ys[b]))) for a, b in tri]
                fk.poly(top, 0.0, [(a / nx, b / ny) for a, b in tri])
                bot = [Vector((xs[a], ys[b], zc(xs[a], ys[b]) - 0.0003)) for a, b in reversed(tri)]
                bk.poly(bot, 0.0, [(1.0 - a / nx, b / ny) for a, b in reversed(tri)])
    part('Item_Postcard', 'item', (0, 0, 0), note='the card with the doll (root): lying picture up, origin under its middle; the '
                                                  'picture M_Gear_PostcardFront (UV 0..1: u right, v to the top edge +y), the back '
                                                  'M_Gear_PostcardBack (UV 0..1 as read turned over left to right: u to -x, v to '
                                                  '+y) - the message, signed "— K" without the dot; the demo\'s final menu')
    MASS['Item_Postcard'] = 0.005
    BOXES.append(('Postcard', 'Item_Postcard', (-PC_W / 2, PC_W / 2, -PC_H / 2, PC_H / 2, 0.0, 0.0035), None))


# ================================================================ Item_Bulb, Item_BulbBox
def build_bulb():
    k = reg('Item_Bulb', 'Small', 'Item_Bulb')
    k.lathe(Vector((0, 0, 0)), Z, [(0.0, 0.0), (0.0006, 0.0034), (0.0020, 0.0042)], Z_SOLDER, 10, cap0=False, cap1=False)
    k.lathe(Vector((0, 0, 0)), Z, [(0.0020, 0.0042), (0.0022, 0.0088), (0.0058, 0.0094), (0.0060, 0.0118)], Z_BULBINS, 14,
            cap0=False, cap1=False)
    th = [(0.0060, 0.0118)]
    z = 0.0060
    while z < 0.0245:                                                                   # the E27 thread (crest, root)
        th += [(z + 0.0012, 0.0131), (z + 0.0030, 0.0123)]
        z += 0.0036
    th += [(0.0262, 0.0130), (0.0268, 0.0138), (0.0280, 0.0138)]
    k.lathe(Vector((0, 0, 0)), Z, th, Z_BULBCAP, 12, cap0=False, cap1=False)
    g = reg('Bulb_Glass', 'bulb', 'Item_Bulb', merge='Item_Bulb')
    lathe_uv(g, Vector((0, 0, 0)), Z, [(0.0280, 0.0136), (0.0340, 0.0158), (0.0420, 0.0200), (0.0520, 0.0255), (0.0620, 0.0290),
                                       (0.0720, 0.0300), (0.0820, 0.0292), (0.0900, 0.0265), (0.0970, 0.0215), (0.1020, 0.0142),
                                       (0.1050, 0.0065), (0.1060, 0.0)], (0.0, 0.0, 1.0, 1.0), seg=14)
    part('Item_Bulb', 'item', (0, 0, 0), note='a frosted E27 bulb, 60 W (root): standing on its cap, origin under the contact; '
                                              'the glass: M_Gear_Bulb (new) - M_Gear_BulbBurnt for a dead one (the same UVs)')
    socket('Screw_E27', (0.0, 0.0, 0.016), 'screw', parent='Item_Bulb', dir=(0, 0, -1),
           note='screws into a lamp holder cap first (-z): two turns clockwise seen from the glass')
    MASS['Item_Bulb'] = 0.03
    BOXES.append(('Bulb', 'Item_Bulb', (-0.030, 0.030, -0.030, 0.030, 0.0, 0.106), None))


BB = dict(w=0.064, h=0.112)


def build_bulbbox():
    k = reg('Item_BulbBox', 'panel', 'Item_BulbBox')
    w, h = BB['w'], BB['h']
    for n, up, key in (((0, -1, 0), (0, 0, 1), 'bulbbox_front'), ((0, 1, 0), (0, 0, 1), 'bulbbox_front'),
                       ((1, 0, 0), (0, 0, 1), 'bulbbox_side'), ((-1, 0, 0), (0, 0, 1), 'bulbbox_side'),
                       ((0, 0, 1), (0, 1, 0), 'bulbbox_top'), ((0, 0, -1), (0, 1, 0), 'bulbbox_top')):
        n = Vector(n)
        c = Vector((0, 0, h / 2)) + Vector((n.x * w / 2, n.y * w / 2, n.z * h / 2))
        size = (w, h) if abs(n.z) < 0.5 else (w, w)
        quad(k, c, n, size[0], size[1], uv(key), up=up)
    part('Item_BulbBox', 'item', (0, 0, 0), note='the bulb\'s carton (root): GLÜHLAMPE 60 W E27 230 V; standing, origin under '
                                                 'its middle; it does not open (the game hands out Item_Bulb)')
    MASS['Item_BulbBox'] = 0.06
    BOXES.append(('BulbBox', 'Item_BulbBox', (-w / 2, w / 2, -w / 2, w / 2, 0.0, h), None))


# ================================================================ Item_WorkerTag, Item_Key_Stationsleiter
def build_tag():
    k = reg('Item_WorkerTag', 'Small', 'Item_WorkerTag')
    pk = reg('WorkerTag_Faces', 'panel', 'Item_WorkerTag', merge='Item_WorkerTag')
    ring_tube(k, (0.0, 0.0, -0.010), (1, 0, 0), 0.0091, 0.0009, Z_STEEL, seg=12, wseg=3)  # the split ring through the hole
    ring_tube(k, (0.0006, 0.0, -0.010), (1, 0, 0), 0.0091, 0.0009, Z_STEEL, seg=12, wseg=3)
    c = Vector((0.0, 0.0, -0.031))
    k.lathe(c - Y * 0.00075, Y, [(0.0, 0.016), (0.0015, 0.016)], Z_BRASS, 20, cap0=False, cap1=False)
    pk.disc_uv(c - Y * 0.00075, -Y, 0.016, uv('tag_face'), seg=20)
    pk.disc_uv(c + Y * 0.00075, Y, 0.016, uv('tag_back'), seg=20)
    part('Item_WorkerTag', 'item', (0, 0, 0), note=f'a round brass tag (32 mm) with the stamped personnel number '
                                                   f'{GT.TAG_NUMBER} (SNOW, NR.) on a split ring; the back PROJEKT SNOW '
                                                   f'HOHENMOOS; origin = the hanging point (the top of the ring), the number to -y')
    MASS['Item_WorkerTag'] = 0.012
    BOXES.append(('WorkerTag', 'Item_WorkerTag', (-0.016, 0.016, -0.0025, 0.0025, -0.047, 0.0), None))


def build_key():
    """forest_items' key (items_kit._key: the same ring, key and tag, origin = the hanging point) with a black tag"""
    k = reg('Item_Key_Stationsleiter', 'Small', 'Item_Key_Stationsleiter')
    pk = reg('Key_Tag', 'panel', 'Item_Key_Stationsleiter', merge='Item_Key_Stationsleiter')
    k.lathe(Vector((0.0, 0.0, -0.0115)), Vector((0, 1, 0)), [(-0.0012, 0.0115), (0.0012, 0.0115)], Z_STEEL, 12, cap0=False, cap1=False)
    k.lathe(Vector((0.0, 0.0, -0.0115)), Vector((0, 1, 0)), [(0.0012, 0.0095), (-0.0012, 0.0095)], Z_STEEL, 12, cap0=False, cap1=False)
    for s in (-1, 1):
        k.lathe(Vector((0.0, 0.0, -0.0115)), Vector((0, s, 0)), [(0.0012, 0.0095), (0.0012, 0.0115)], Z_STEEL, 12, cap0=False,
                cap1=False)
    yk = 0.0012
    k.lathe(Vector((0.0, yk, -0.0315)), Vector((0, 1, 0)), [(0.0, 0.0105), (0.0022, 0.0105)], Z_BRASS, 12)
    box6(k, (-0.0045, yk, -0.050), (0.0045, yk + 0.0022, -0.040), Z_BRASS)
    box6(k, (-0.0035, yk, -0.0835), (0.0035, yk + 0.0022, -0.050), Z_BRASS)
    for i, d in enumerate((0.0035, 0.0015, 0.004, 0.002, 0.003)):                       # its own bitting
        z = -0.055 - i * 0.0055
        box6(k, (0.0035, yk, z - 0.0026), (0.0035 + d, yk + 0.0022, z + 0.0026), Z_BRASS)
    VM.rbox(k, Vector((0.0, -0.0021, -0.052)), (0.029, 0.0022, 0.052), Z_TAGBK, r=0.005, ch=0.0008, axis='y')
    quad(pk, (0.0, -0.00325, -0.052), (0, -1, 0), 0.040, 0.022, uv('key_tag'), up=(1, 0, 0))
    k.tube([Vector((0.0, -0.002, -0.0215)), Vector((0.0, -0.002, -0.027))], 0.0012, Z_STEEL, 4)
    part('Item_Key_Stationsleiter', 'item', (0, 0, 0),
         note='the station chief\'s key (root): forest_items\' key - the same ring, brass key and tag (fits the hooks of the KPP '
              'key cabinet), a black tag ST.-LEITER; origin = the hanging point (the top of the ring); opens the cabinet in the '
              'chief\'s office (I5), lies in the Forester\'s cave (I1)')
    MASS['Item_Key_Stationsleiter'] = 0.02
    BOXES.append(('Key', 'Item_Key_Stationsleiter', (-0.0145, 0.0145, -0.0035, 0.0035, -0.0835, 0.0), None))


# ================================================================ Item_IceAxe
def build_iceaxe():
    k = reg('Item_IceAxe', 'Small', 'Item_IceAxe')
    k.lathe(Vector((0, 0, 0)), Z, [(0.0, 0.0), (0.022, 0.0060), (0.030, 0.0085)], Z_AXE, 8, cap0=False, cap1=False)
    k.loft(ell_rings((0, 0, 0), Z, [(0.030, 0.0125, 0.0100), (0.072, 0.0160, 0.0120)], seg=10),
           [Z_AXE], cap0=Z_AXE)                                                           # the spike's collar
    k.loft(ell_rings((0, 0, 0), Z, [(0.072, 0.0150, 0.0110), (0.30, 0.0152, 0.0112), (0.50, 0.0158, 0.0116),
                                    (0.636, 0.0162, 0.0120)], seg=10), [Z_AXEWOOD] * 3, cap0=Z_AXEWOOD)
    k.box(-0.020, 0.020, -0.0135, 0.0135, 0.618, 0.666, Z_AXE)                           # the head's eye round the shaft
    # the pick (+x, drooping, a point) and the adze (-x, a broad thin blade)
    pick = []
    for t in np.linspace(0.0, 1.0, 6):
        x = 0.018 + 0.168 * t
        z = 0.648 - 0.040 * t ** 1.6
        hh, ww = 0.024 * (1 - 0.85 * t), 0.0075 * (1 - 0.6 * t)
        pick.append((Vector((x, 0.0, z)), hh, ww))
    rings = []
    for i, (p, hh, ww) in enumerate(pick):
        tdir = (pick[min(i + 1, 5)][0] - pick[max(i - 1, 0)][0]).normalized()
        nz = Vector((-tdir.z, 0.0, tdir.x))
        rings.append([p + nz * hh / 2, p + Y * ww / 2, p - nz * hh / 2 * 1.2, p - Y * ww / 2])
    rings[-1] = [pick[-1][0] - Vector((0, 0, 0.002))] * 4
    for a_, b_ in zip(rings[:-1], rings[1:]):
        for j in range(4):
            q = [a_[j], b_[j], b_[(j + 1) % 4], a_[(j + 1) % 4]]
            cc = sum(q, Vector()) / 4
            ax = sum(a_, Vector()) / 4
            if (q[1] - q[2]).length < 1e-6:
                q = [q[0], q[1], q[3]]
            face(k, q, Z_AXE, cc - ax)
    face(k, list(reversed(rings[0])), Z_AXE, (-1, 0, 0))
    adze = []
    for t in np.linspace(0.0, 1.0, 5):
        x = -0.018 - 0.080 * t
        z = 0.646 - 0.010 * t ** 2
        adze.append((Vector((x, 0.0, z)), 0.018 * (1 - 0.78 * t) + 0.003, 0.016 + 0.034 * t))
    rings = [[p + Vector((0, -ww / 2, hh / 2)), p + Vector((0, ww / 2, hh / 2)), p + Vector((0, ww / 2, -hh / 2)),
              p + Vector((0, -ww / 2, -hh / 2))] for p, hh, ww in adze]
    for a_, b_ in zip(rings[:-1], rings[1:]):
        for j in range(4):
            q = [a_[j], a_[(j + 1) % 4], b_[(j + 1) % 4], b_[j]]
            face(k, q, Z_AXE, sum(q, Vector()) / 4 - (sum(a_, Vector()) + sum(b_, Vector())) / 8)
    face(k, rings[-1], Z_AXE, (-1, 0, 0))
    face(k, rings[0], Z_AXE, (1, 0, 0))
    # a leather wrist loop on a ring under the head
    k.lathe(Vector((0, 0, 0.596)), Z, [(0.0, 0.0175), (0.006, 0.0175)], Z_STEEL, 10, cap0=False, cap1=False)
    Rl = Matrix.Rotation(math.radians(35.0), 3, 'Z')                                     # the loop hangs back and to the side
    k.strip([Rl @ Vector((0.0, 0.017, 0.600)), Rl @ Vector((0.0, 0.050, 0.540)), Rl @ Vector((0.0, 0.062, 0.470)),
             Rl @ Vector((0.0, 0.052, 0.420)), Rl @ Vector((0.0, 0.026, 0.430)), Rl @ Vector((0.0, 0.018, 0.520)),
             Rl @ Vector((0.0, 0.016, 0.592))], Rl @ Vector((1, 0, 0)), 0.003, 0.016, Z_LEASH)
    part('Item_IceAxe', 'item', (0, 0, 0), note='an ice axe (root): upright, origin = the spike\'s tip; the pick to +x, the adze '
                                                'to -x; for chipping ice off the antennas (P1) - hit with the pick')
    socket('Hand_IceAxe', (0.0, 0.0, 0.17), 'hand', parent='Item_IceAxe', note='swinging grip, low on the shaft')
    socket('Hand_IceAxe_Head', (0.0, 0.0, 0.672), 'hand', parent='Item_IceAxe', note='walking grip on the head')
    socket('Tip_Pick', (0.186, 0.0, 0.606), 'point', parent='Item_IceAxe', dir=Vector((0.25, 0.0, -0.97)).normalized(),
           note='the pick\'s point: the hit point for chipping ice')
    socket('Tip_Adze', (-0.098, 0.0, 0.636), 'point', parent='Item_IceAxe', note='the adze\'s edge')
    MASS['Item_IceAxe'] = 0.75
    BOXES.extend([('IceAxe_Shaft', 'Item_IceAxe', (-0.0165, 0.0165, -0.0125, 0.0125, 0.0, 0.618), None),
                  ('IceAxe_Head', 'Item_IceAxe', (-0.100, 0.188, -0.026, 0.026, 0.600, 0.666), None)])


def build_gear():
    build_battery()
    build_pack()
    build_b6()
    build_walkie()
    build_lantern()
    build_headlamp()
    build_cart()
    build_sled()
    build_doll()
    build_postcard()
    build_bulb()
    build_bulbbox()
    build_tag()
    build_key()
    build_iceaxe()
