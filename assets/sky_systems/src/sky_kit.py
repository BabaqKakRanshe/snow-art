"""sky_systems geometry: the Sky Island's height systems (VISION 9, RESEARCH_HORROR 4.2: the island stays up on bone dust in
deep cold; the cold loop is failing, the island is sinking) and the walkways under it, in the generator shed's style with the
island's palette (olive paint, rust-brown steel, concrete, yellow). Each root in its own frame (Blender: z up, metres, origin
on the ground / the deck; Unity (x, y, z) -> (-x, z, -y), the front -y -> +Z):
  SkyChiller     the refrigeration unit (Kältemaschine) on its pad: motor and compressor with the V-belts under a hinged guard
                 (SkyChiller_Belt: the belts that break; IX_SkyChillerGuard), the condenser with its fan (SkyChiller_Fan), the
                 receiver, the insulated suction pipes going down into the island (frosted), the refrigerant valve
                 (IX_SkyChillerValve), the control cabinet (panel) with the START lever (IX_SkyChillerStart), RUN / FAULT lamps
                 and an amber beacon; Slot_Refrigerant - where a refrigerant cylinder is connected
  SkySprayer     the bone-dust sprayer: a hopper on a frame with its lid (IX_SkySprayerLid; Slot_DustPour - sacks are emptied
                 here), the rotary feeder with its crank (IX_SkySprayerFeed), the blower, the mast with the swivelling nozzle
                 (SkySprayer_Nozzle), a ladder and a platform at the hopper's rim, the control box (panel); dust everywhere
  SkyBallast     ballast release at the island's edge: a steel tilting deck on a concrete foundation over the drop
                 (IX_SkyBallastDeck), two hydraulic rams (SkyBallast_Ram_L / _R: aim + stretch), three concrete ballast blocks
                 (SkyBallast_Block_1..3, loose: they slide off), the lever station (IX_SkyBallastLever: hold to tilt), the
                 hydraulic unit, a beacon, the BALLASTABWURF sign, railings at the edge
  SkyAltimeter   the island's altitude board by the tower (the chapter's timer, not UI): two lattice legs, the board (panel:
                 HÖHE ÜBER GRUND, 0 .. 2000 m), the marker (SkyAltimeter_Marker: slides with the altitude), the lamp column
                 (SkyAltimeter_Lamps), two floodlights, the obstruction light, a ladder
  SkyWalk_*      walkway modules under the island (steel grating, rust): Straight (4 m), Stair (3 m down), Landing
                 (2.4 x 2.4 m), Turn (corner), Ladder (4 m cage ladder), Cable (1 m hanger, stretched), Anchor (rock plate),
                 Lamp (railing lamp); Hang_* sockets where the cables go up to the rock
Atlases: SkyMachines (the chiller and the sprayer), SkyStructures (the ballast release and the altitude board), SkyWalk (the
walkway modules). Explicit-UV faces (panel, grating) join their bodies at build time (MERGE) unless they are their own objects."""
import math
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, box6, face, KBS, CONTRACT
from van2_kit import ZERO
import sky_tex as ST

uv = ST.uv
TAU = 2 * math.pi
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
V3 = lambda x, y, z: Vector((x, y, z))
WALKS = ['SkyWalk_Straight', 'SkyWalk_Stair', 'SkyWalk_Landing', 'SkyWalk_Turn', 'SkyWalk_Ladder', 'SkyWalk_Cable',
         'SkyWalk_Anchor', 'SkyWalk_Lamp']
ROOTS = ['SkyChiller', 'SkySprayer', 'SkyBallast', 'SkyAltimeter'] + WALKS
DISPLAY = {'SkyChiller': V3(-13, 0, 0), 'SkySprayer': V3(-4, 0, 0), 'SkyBallast': V3(6, -2, 0), 'SkyAltimeter': V3(17, 0, 0),
           'SkyWalk_Straight': V3(-13, 16, 0), 'SkyWalk_Stair': V3(-8, 16, 0), 'SkyWalk_Landing': V3(-2, 16, 0),
           'SkyWalk_Turn': V3(3, 16, 0), 'SkyWalk_Ladder': V3(7, 16, 0), 'SkyWalk_Cable': V3(10, 16, 0),
           'SkyWalk_Anchor': V3(12, 16, 0), 'SkyWalk_Lamp': V3(14, 16, 0)}
ROOT_OF, MERGE, BOXES, MASS = {}, {}, [], {}
LIGHTS = []                       # (name, parent, pos, dir, kind, colour, range, behaviour)
WARM, AMBER, REDL = (1.0, 0.72, 0.42), (1.0, 0.55, 0.12), (1.0, 0.08, 0.03)

# SkyMachines / SkyStructures atlases (1024 each; the zones are shared)
(Z_PAD, Z_SKID, Z_MOTOR, Z_COMP, Z_PULLEY, Z_BELT, Z_GUARD, Z_COND, Z_FIN, Z_FAN, Z_TANK, Z_PIPE, Z_INSUL, Z_VALVE, Z_CAB,
 Z_BEACON, Z_HOPPER, Z_HOPIN, Z_BLOWER, Z_MAST, Z_NOZZLE, Z_LADDER, Z_RAILY, Z_CONC, Z_DECK, Z_DECKUND, Z_HINGE, Z_RAM,
 Z_BLOCK, Z_LEVER, Z_HPU, Z_POST, Z_BOARD, Z_TRUSS, Z_LAMPB, Z_DUST, Z_FROST, Z_PLATE, Z_DUSTIN) = range(1000, 1039)
Z_BHID, Z_PIT = 1039, 1040                                      # the board's face under the panel (hidden), the rams' pit
# SkyWalk atlas (1024)
(Z_WSTR, Z_WRAIL, Z_WTOE, Z_WHANG, Z_WPLATE, Z_WLAMP, Z_WRUNG, Z_WCAGE, Z_WROCK) = range(1060, 1069)


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


def frame_R(t, up=Z):
    t = Vector(t).normalized()
    up = Vector(up)
    if abs(t.dot(up.normalized())) > 0.95:
        up = X if abs(t.x) < 0.9 else Y
    s = up.cross(t).normalized()
    u = t.cross(s)
    return Matrix((t, s, u)).transposed()


def railing(k, pts, zone, h=1.1, r=0.022, posts=None, mid=True, toe=None, toe_zone=None):
    pts = [Vector(p) for p in pts]
    for i in (range(len(pts)) if posts is None else posts):
        k.box_m(pts[i] + Z * (h / 2), (0.05, 0.05, h), zone)
    k.tube([p + Z * h for p in pts], r, zone, 6)
    if mid:
        k.tube([p + Z * (h * 0.5) for p in pts], r * 0.85, zone, 6)
    if toe:
        for a, b in zip(pts[:-1], pts[1:]):
            bar(k, a + Z * 0.05, b + Z * 0.05, toe, 0.10, toe_zone or zone, up=Z)


def bulkhead(kb_body, kb_glow, c, n, zone_body, zone_cage, up=Z, r=0.11):
    c, n = Vector(c), Vector(n).normalized()
    s = r / 0.11
    kb_body.lathe(c, n, [(0.0, 0.11 * s), (0.035 * s, 0.11 * s), (0.05 * s, 0.095 * s)], zone_body, 12)
    kb_glow.lathe(c + n * 0.05 * s, n, [(0.0, 0.085 * s), (0.04 * s, 0.078 * s), (0.075 * s, 0.05 * s), (0.095 * s, 0.0)],
                  ZERO, 10, cap0=False, cap1=False)
    u = up - n * up.dot(n)
    if u.length < 1e-3:
        u = X - n * X.dot(n)
    u.normalize()
    w = n.cross(u)
    for a in (0.0, TAU / 3, 2 * TAU / 3):
        d = u * math.cos(a) + w * math.sin(a)
        kb_body.tube([c + n * 0.05 * s + d * 0.095 * s, c + n * 0.10 * s + d * 0.085 * s, c + n * 0.145 * s + d * 0.03 * s,
                      c + n * 0.152 * s], 0.007 * s, zone_cage, 5, caps=False)


def sign_plate(k_body, k_face, c, n, w, h, region, zone_plate, up=Z, t=0.012):
    c, n = Vector(c), Vector(n).normalized()
    u = Vector(up).cross(n).normalized()
    v = n.cross(u)
    R = Matrix((u, v, n)).transposed()
    k_body.box_m(c + n * (t / 2), (w + 0.02, h + 0.02, t), zone_plate, R)
    k_face.quad_uv(c + n * (t + 0.0015), n, w, h, uv(region), up=v)


def icicle(k, top, L, r, zone, seg=5):
    top = Vector(top)
    k.cyl(top, top - Z * L, r, zone, seg, r2=0.002)


def beacon(k_body, k_glow, c, r=0.09, h=0.16, zone=Z_BEACON):
    """rotating-beacon housing (base) and its dome (glow object)"""
    c = Vector(c)
    k_body.lathe(c, Z, [(0.0, r * 1.15), (0.04, r * 1.15), (0.05, r)], zone, 12)
    k_glow.lathe(c + Z * 0.05, Z, [(0.0, r), (h * 0.7, r * 0.95), (h, r * 0.6), (h + 0.02, 0.0)], ZERO, 12, cap0=False, cap1=False)


# ================================================================ SkyChiller
def build_chiller():
    root = 'SkyChiller'
    k = reg(root, 'SkyMachines', root)
    kf = reg('SkyChiller_Signs', 'panel', root, merge=root)
    gl_run = reg('SkyChiller_LampRun', 'green', root)
    gl_flt = reg('SkyChiller_LampFault', 'red', root)
    gl_bc = reg('SkyChiller_Beacon', 'amber', root)
    # pad and skid
    k.box(-3.2, 3.2, -1.9, 1.9, 0.0, 0.18, Z_PAD)
    zs = 0.38
    for ya, yb in ((-1.45, -1.25), (1.25, 1.45)):
        k.box(-2.9, 2.9, ya, yb, 0.18, zs, Z_SKID)
    for xc in (-2.8, -1.2, 0.3, 1.9, 2.8):
        k.box(xc - 0.1, xc + 0.1, -1.25, 1.25, 0.18, zs - 0.04, Z_SKID)
    yb_ = -0.62                                                 # the belt drive's plane (both shafts along y, pulleys at the front)
    # the compressor: crankcase, two cylinders in V across the shaft with finned heads, the flywheel at the front
    cc = V3(0.10, 0.0, zs + 0.40)
    k.box(cc.x - 0.55, cc.x + 0.55, -0.40, 0.40, zs, zs + 0.64, Z_COMP)
    k.box(cc.x - 0.6, cc.x + 0.6, -0.45, 0.45, zs, zs + 0.08, Z_COMP)
    heads = []
    for sgn in (-1, 1):
        a = math.radians(32) * sgn
        d = Vector((math.sin(a), 0.0, math.cos(a)))
        base = V3(cc.x + sgn * 0.22, 0.0, zs + 0.60)
        k.lathe(base, d, [(0.0, 0.17), (0.40, 0.17)] + [(0.42 + 0.05 * i + dd, rr) for i in range(4)
                                                        for dd, rr in ((0.0, 0.17), (0.015, 0.22), (0.03, 0.22))] +
                [(0.64, 0.17), (0.70, 0.12)], Z_COMP, 12)
        top = base + d * 0.70
        rod(k, top, top + Vector((0, 0, 0.18)), 0.045, Z_PIPE, 8)
        heads.append(top + Vector((0, 0, 0.18)))
    rod(k, V3(cc.x, -0.40, cc.z), V3(cc.x, yb_ + 0.06, cc.z), 0.05, Z_PULLEY, 8)                 # the crankshaft's end
    fw = V3(cc.x, yb_, cc.z)
    k.lathe(fw - Y * 0.06, Y, [(0.0, 0.40), (0.12, 0.40)], Z_PULLEY, 20)                         # the flywheel / big pulley
    # the motor beside it (axis along y, its pulley at the front), feet, junction box
    mc = V3(-1.20, 0.10, zs + 0.38)
    k.lathe(mc + Y * 0.55, -Y, [(0.0, 0.18), (0.06, 0.30), (0.10, 0.31)] + [(0.14 + 0.08 * i + d, rr) for i in range(10)
                                                                           for d, rr in ((0.0, 0.31), (0.03, 0.34), (0.05, 0.34))] +
            [(0.98, 0.31), (1.04, 0.28), (1.10, 0.16)], Z_MOTOR, 16)
    for yy in (mc.y - 0.35, mc.y + 0.35):
        k.box(mc.x - 0.27, mc.x + 0.27, yy - 0.08, yy + 0.08, zs, zs + 0.12, Z_MOTOR)
    k.box(mc.x - 0.15, mc.x + 0.15, mc.y - 0.05, mc.y + 0.25, mc.z + 0.30, mc.z + 0.48, Z_MOTOR)
    rod(k, V3(mc.x, mc.y - 0.55, mc.z), V3(mc.x, yb_ + 0.06, mc.z), 0.04, Z_PULLEY, 8)
    mp = V3(mc.x, yb_, mc.z)
    k.lathe(mp - Y * 0.06, Y, [(0.0, 0.13), (0.12, 0.13)], Z_PULLEY, 14)                         # the motor pulley
    # the belts (SkyChiller_Belt: they break) round both pulleys, in the x-z plane
    bt = reg('SkyChiller_Belt', 'SkyMachines', root)
    dv = mp - fw
    ang0 = math.atan2(dv.z, dv.x)
    for i in range(3):
        yy = yb_ - 0.035 + 0.035 * i
        p1, r1 = Vector((fw.x, yy, fw.z)), 0.405
        p2, r2 = Vector((mp.x, yy, mp.z)), 0.135
        pts = []
        for j in range(13):
            a = ang0 + math.pi / 2 + math.pi * j / 12
            pts.append(p1 + Vector((math.cos(a), 0, math.sin(a))) * r1)
        for j in range(9):
            a = ang0 - math.pi / 2 + math.pi * j / 8
            pts.append(p2 + Vector((math.cos(a), 0, math.sin(a))) * r2)
        pts.append(pts[0])
        bt.strip(pts, Y, 0.024, 0.018, Z_BELT, caps=False)
    part('SkyChiller_Belt', 'static', ((fw.x + mp.x) / 2, yb_, (fw.z + mp.z) / 2), parent=root,
         states=['fitted', 'torn', 'missing'],
         note='the three V-belts motor -> compressor: the usual fault (RESEARCH_HORROR 4.2 "replace the belt"); fitted = shown; '
              'torn / missing = hidden (a spare belt is fitted through the open guard)')
    # the belt guard: a yellow box over the drive, its front plate hinged at the top (IX_SkyChillerGuard)
    gx0, gx1 = mp.x - 0.25, fw.x + 0.52
    gy0, gy1, gz0, gz1 = yb_ - 0.16, yb_ + 0.14, zs, fw.z + 0.52
    k.box(gx0, gx1, gy0 + 0.03, gy1, gz1 - 0.03, gz1, Z_GUARD)                                   # top
    k.box(gx0, gx0 + 0.03, gy0 + 0.03, gy1, gz0, gz1, Z_GUARD)                                   # ends
    k.box(gx1 - 0.03, gx1, gy0 + 0.03, gy1, gz0, gz1, Z_GUARD)
    k.box(gx0, gx1, gy1 - 0.02, gy1, gz0, gz1, Z_GUARD)                                          # back plate
    G = reg('IX_SkyChillerGuard', 'SkyMachines', root)
    G.box(gx0, gx1, gy0, gy0 + 0.03, gz0, gz1, Z_GUARD)
    for zz in (gz0 + 0.2, gz1 - 0.2):
        rod(G, (gx0 + 0.25, gy0 - 0.02, zz), (gx1 - 0.25, gy0 - 0.02, zz), 0.012, Z_PULLEY, 6)
    G.box((gx0 + gx1) / 2 - 0.08, (gx0 + gx1) / 2 + 0.08, gy0 - 0.05, gy0, gz0 + 0.08, gz0 + 0.16, Z_PULLEY)    # the latch
    part('IX_SkyChillerGuard', 'hinge', ((gx0 + gx1) / 2, gy0, gz1), axis=(-1, 0, 0), rng=(0, 110), parent=root,
         states=['closed', 'open'], note='the belt guard\'s front plate: hinged along its top edge, swings up and out (-y)')
    # the condenser (right): casing on legs, fin sides, the fan ring and its fan (SkyChiller_Fan)
    cx0, cx1, cy0, cy1, cz0, cz1 = 1.15, 2.85, -0.70, 0.70, zs + 0.25, zs + 1.75
    for xx in (cx0 + 0.05, cx1 - 0.05):
        for yy in (cy0 + 0.05, cy1 - 0.05):
            k.box(xx - 0.05, xx + 0.05, yy - 0.05, yy + 0.05, zs, cz0, Z_SKID)
    box6(k, (cx0, cy0, cz0), (cx1, cy1, cz1), {'*': Z_COND, '-y': Z_FIN, '+y': Z_FIN, '-x': Z_FIN})
    for xx in (cx0, cx1):
        k.box(xx - 0.03, xx + 0.03, cy0 - 0.03, cy1 + 0.03, cz0, cz1 + 0.02, Z_COND)
    fc = V3((cx0 + cx1) / 2, 0.0, cz1)
    k.lathe(fc, Z, [(0.0, 0.62), (0.18, 0.62), (0.20, 0.58)], Z_COND, 20, cap0=False, cap1=False)
    k.lathe(fc + Z * 0.20, Z, [(0.0, 0.58), (-0.17, 0.58)], Z_COND, 20, cap0=False, cap1=False)
    for i in range(6):
        a = TAU * i / 6
        bar(k, fc + Z * 0.21, fc + Z * 0.21 + Vector((math.cos(a), math.sin(a), 0)) * 0.6, 0.02, 0.02, Z_PULLEY)
    Fn = reg('SkyChiller_Fan', 'SkyMachines', root)
    Fn.lathe(fc + Z * 0.06, Z, [(0.0, 0.10), (0.08, 0.10), (0.10, 0.0)], Z_PULLEY, 10)
    for i in range(5):
        a = TAU * i / 5
        d = Vector((math.cos(a), math.sin(a), 0))
        s_ = Vector((-d.y, d.x, 0))
        p0, p1 = fc + Z * 0.09 + d * 0.10, fc + Z * 0.09 + d * 0.55
        quad(Fn, [p0 - s_ * 0.06 - Z * 0.02, p1 - s_ * 0.13 - Z * 0.03, p1 + s_ * 0.13 + Z * 0.03, p0 + s_ * 0.06 + Z * 0.02],
             Z_FAN, Z)
        quad(Fn, [p0 - s_ * 0.06 - Z * 0.025, p1 - s_ * 0.13 - Z * 0.035, p1 + s_ * 0.13 + Z * 0.025, p0 + s_ * 0.06 + Z * 0.015],
             Z_FAN, -Z)
    part('SkyChiller_Fan', 'spin', fc, axis=(0, 0, 1), parent=root, states=['stopped', 'running'],
         note='the condenser fan: turns while the unit runs (~6 rev/s)')
    # the discharge header from both heads into the condenser's side; the receiver behind the condenser, the liquid line
    hz = max(h.z for h in heads) + 0.12
    k.tube([heads[0], V3(heads[0].x, 0.0, hz), V3(cx0 - 0.02, 0.0, hz)], 0.045, Z_PIPE, 8)
    k.tube([heads[1], V3(heads[1].x, 0.0, hz)], 0.045, Z_PIPE, 8, caps=False)
    rc = V3(2.0, 1.25, zs + 0.32)
    k.lathe(rc - X * 0.7, X, [(0.0, 0.0), (0.06, 0.20), (0.12, 0.25), (1.28, 0.25), (1.34, 0.20), (1.40, 0.0)], Z_TANK, 14,
            cap0=False, cap1=False)
    for xx in (rc.x - 0.45, rc.x + 0.45):
        k.box(xx - 0.06, xx + 0.06, rc.y - 0.22, rc.y + 0.22, zs, rc.z - 0.18, Z_SKID)
    k.tube([V3(2.55, 0.60, cz0 - 0.02), V3(2.55, 0.85, cz0 - 0.02), V3(2.55, 0.85, rc.z + 0.42), V3(2.55, rc.y, rc.z + 0.42),
            V3(2.55, rc.y, rc.z + 0.22)], 0.03, Z_PIPE, 6)
    k.lathe(V3(rc.x - 0.55, rc.y, rc.z + 0.23), Z, [(0.0, 0.035), (0.08, 0.035), (0.09, 0.05), (0.12, 0.05)], Z_VALVE, 8)
    socket('Slot_Refrigerant', (rc.x - 0.55, rc.y, rc.z + 0.36), 'connect', parent=root, dir=(0, 0, 1),
           note='the receiver\'s fill port: a refrigerant cylinder is connected here (RESEARCH_HORROR 4.2 "pump refrigerant")')
    # the cold loop: the insulated suction pair from the compressor's back down into the island (frosted), its valve
    for i, xx in enumerate((cc.x - 0.30, cc.x + 0.15)):
        path = [V3(xx, 0.38, zs + 0.40), V3(xx, 1.30, zs + 0.40), V3(xx, 1.62, zs + 0.10), V3(xx, 1.62, -0.30)]
        k.tube(path, 0.10, Z_INSUL, 10)
        for j in range(4):
            y = 0.50 + j * 0.20 + 0.07 * hsh(j, 5 + i)
            icicle(k, (xx + 0.04 * (hsh(j, 7) - 0.5), y, zs + 0.30), 0.06 + 0.10 * hsh(j, 9 + i), 0.018, Z_FROST)
    vc = V3(cc.x + 0.15, 1.12, zs + 0.40)
    k.box(vc.x - 0.14, vc.x + 0.14, vc.y - 0.12, vc.y + 0.12, vc.z - 0.14, vc.z + 0.14, Z_PIPE)            # the valve body
    rod(k, vc + Z * 0.14, vc + Z * 0.36, 0.02, Z_PIPE, 6)
    Vl = reg('IX_SkyChillerValve', 'SkyMachines', root)
    wc = vc + Z * 0.38
    ring = [wc + Vector((math.cos(TAU * i / 14), math.sin(TAU * i / 14), 0)) * 0.16 for i in range(14)]
    Vl.tube(ring + [ring[0]], 0.016, Z_VALVE, 6, caps=False)
    for i in range(3):
        a = TAU * i / 3
        rod(Vl, wc, wc + Vector((math.cos(a), math.sin(a), 0)) * 0.15, 0.011, Z_VALVE, 6)
    Vl.lathe(wc - Z * 0.02, Z, [(0.0, 0.03), (0.04, 0.03)], Z_VALVE, 8)
    part('IX_SkyChillerValve', 'twist', wc, axis=(0, 0, 1), rng=(0, 1080), parent=root, states=['shut', 'open'],
         note='the suction valve on the cold loop (handwheel, three turns): open it to pump the refrigerant round')
    # the control cabinet (front left, its panel faces -y), the START lever on its side, the lamps, the beacon, the plate
    kx0, kx1, ky0, ky1 = -3.05, -2.15, -1.85, -1.45
    k.box(kx0, kx1, ky0, ky1, 0.18, 2.0, Z_CAB)
    k.box(kx0 - 0.03, kx1 + 0.03, ky0 - 0.03, ky1 + 0.03, 2.0, 2.06, Z_CAB)
    kf.quad_uv(V3((kx0 + kx1) / 2, ky0 - 0.002, 1.35), -Y, 0.80, 1.00, uv('chiller'))
    k.tube([V3(-2.6, ky1, 0.42), V3(-2.6, 0.15, 0.42), V3(-1.75, 0.15, 0.42), V3(-1.75, 0.15, mc.z + 0.40),
            V3(mc.x - 0.15, 0.15, mc.z + 0.40)], 0.03, Z_PIPE, 6)                                       # power to the motor
    St = reg('IX_SkyChillerStart', 'SkyMachines', root)
    lp = V3(kx1 + 0.03, (ky0 + ky1) / 2, 1.20)
    St.box(lp.x, lp.x + 0.05, lp.y - 0.05, lp.y + 0.05, lp.z - 0.05, lp.z + 0.05, Z_LEVER)
    bar(St, lp + X * 0.05, lp + X * 0.05 + Z * 0.38, 0.03, 0.03, Z_LEVER, up=X)
    St.lathe(lp + X * 0.05 + Z * 0.38, Z, [(0.0, 0.035), (0.10, 0.035), (0.12, 0.0)], Z_LEVER, 8)
    part('IX_SkyChillerStart', 'hinge', lp, axis=(1, 0, 0), rng=(0, 75), parent=root, states=['off', 'start'],
         note='the START lever on the cabinet\'s side: pull it down to start the compressor (with the belts fitted and the '
              'valve open the RUN lamp lights; otherwise FAULT)')
    gl_run.lathe(V3(-2.85, ky0 - 0.01, 1.98), -Y, [(0.0, 0.04), (0.03, 0.035), (0.05, 0.0)], ZERO, 10, cap0=False, cap1=False)
    gl_flt.lathe(V3(-2.35, ky0 - 0.01, 1.98), -Y, [(0.0, 0.04), (0.03, 0.035), (0.05, 0.0)], ZERO, 10, cap0=False, cap1=False)
    beacon(k, gl_bc, V3((kx0 + kx1) / 2, (ky0 + ky1) / 2, 2.06))
    kf.quad_uv(V3(cc.x + 0.552, 0.0, zs + 0.40), X, 0.20, 0.10, uv('chiller_tag'))
    for nm, note in (('SkyChiller_LampRun', 'green RUN lamp on the cabinet: M_Sky_Green_Off / M_Sky_Green'),
                     ('SkyChiller_LampFault', 'red FAULT lamp: M_Sky_Red_Off / M_Sky_Red (blinks while the unit is down)'),
                     ('SkyChiller_Beacon', 'amber beacon on the cabinet: turns and glows while the unit is down (M_Sky_Amber)')):
        part(nm, 'static', (0, 0, 0), parent=root, states=['off', 'on'], note=note)
    LIGHTS.append(('Light_SkyChiller_Beacon', root, ((kx0 + kx1) / 2, (ky0 + ky1) / 2, 2.20), None, 'point', AMBER, 8.0, 'rotate'))
    part(root, 'static', (0, 0, 0), note='the refrigeration unit (Kältemaschine) on its 6.4 x 3.8 m pad (root): origin on the '
                                          'ground under the pad\'s middle; the cabinet and the belt guard at the front (-y)')
    B = BOXES.append
    B(('SkyChiller_Pad', root, (-3.2, 3.2, -1.9, 1.9, 0.0, 0.18), None))
    B(('SkyChiller_Machine', root, (mc.x - 0.36, cc.x + 0.60, gy0, 0.70, 0.18, 1.45), None))
    B(('SkyChiller_Condenser', root, (cx0, cx1, cy0, cy1, 0.18, cz1 + 0.2), None))
    B(('SkyChiller_Cabinet', root, (kx0, kx1, ky0, ky1, 0.18, 2.06), None))
    B(('SkyChiller_Receiver', root, (rc.x - 0.7, rc.x + 0.7, rc.y - 0.26, rc.y + 0.26, 0.18, rc.z + 0.26), None))
    B(('SkyChiller_Pipes', root, (cc.x - 0.42, cc.x + 0.42, 0.40, 1.74, 0.18, zs + 0.52), None))


# ================================================================ SkySprayer
def build_sprayer():
    root = 'SkySprayer'
    k = reg(root, 'SkyMachines', root)
    kf = reg('SkySprayer_Signs', 'panel', root, merge=root)
    k.box(-1.6, 1.6, -1.6, 1.6, 0.0, 0.20, Z_PAD)
    zt, zo = 3.2, 1.9                                           # hopper rim, outlet
    a_, b_ = 0.95, 0.22                                         # half widths top / bottom
    # legs (angles) and braces
    for sx in (-1, 1):
        for sy in (-1, 1):
            p0 = V3(sx * 1.05, sy * 1.05, 0.20)
            p1 = V3(sx * 0.98, sy * 0.98, zt)
            bar(k, p0, p1, 0.09, 0.09, Z_SKID, up=X)
    for z in (0.9, 2.2):
        for sx in (-1, 1):
            bar(k, V3(sx * 1.03, -1.03, z), V3(sx * 1.03, 1.03, z), 0.05, 0.05, Z_SKID, up=Z)
            bar(k, V3(-1.03, sx * 1.03, z), V3(1.03, sx * 1.03, z), 0.05, 0.05, Z_SKID, up=Z)
    # the hopper: sloped sides out and in, the rim, the outlet
    T = [V3(-a_, -a_, zt), V3(a_, -a_, zt), V3(a_, a_, zt), V3(-a_, a_, zt)]
    Bt = [V3(-b_, -b_, zo), V3(b_, -b_, zo), V3(b_, b_, zo), V3(-b_, b_, zo)]
    for i in range(4):
        j = (i + 1) % 4
        m = (T[i] + T[j]) / 2
        out = Vector((m.x, m.y, 0.3))
        quad(k, [Bt[i], Bt[j], T[j], T[i]], Z_HOPPER, out)
        quad(k, [Bt[i] + Z * 0.01, Bt[j] + Z * 0.01, T[j] - Z * 0.02, T[i] - Z * 0.02], Z_HOPIN, -out)
    for i in range(4):
        j = (i + 1) % 4
        d = T[j] - T[i]
        bar(k, T[i] - d.normalized() * 0.05, T[j] + d.normalized() * 0.05, 0.08, 0.08, Z_HOPPER, up=Z)
    hz = zo + 0.70                                              # the dust inside: a low heap (nearly empty)
    quad(k, [V3(-0.58, -0.58, hz), V3(0.58, -0.58, hz), V3(0.58, 0.58, hz), V3(-0.58, 0.58, hz)], Z_DUSTIN, Z)
    # the rotary feeder under the outlet, its motor, the crank (IX_SkySprayerFeed)
    k.box(-0.30, 0.30, -0.30, 0.30, zo - 0.55, zo, Z_BLOWER)
    k.lathe(V3(0.30, 0.0, zo - 0.28), X, [(0.0, 0.17), (0.25, 0.17), (0.28, 0.10)], Z_MOTOR, 12)
    Fd = reg('IX_SkySprayerFeed', 'SkyMachines', root)
    fcn = V3(-0.31, 0.0, zo - 0.28)
    Fd.lathe(fcn, -X, [(0.0, 0.05), (0.05, 0.05)], Z_PULLEY, 8)
    bar(Fd, fcn - X * 0.05, fcn - X * 0.05 + Z * 0.25, 0.04, 0.025, Z_LEVER, up=X)
    rod(Fd, fcn - X * 0.05 + Z * 0.25, fcn - X * 0.18 + Z * 0.25, 0.02, Z_LEVER, 6)
    part('IX_SkySprayerFeed', 'twist', fcn, axis=(-1, 0, 0), rng=(0, 3600), parent=root, states=['jammed', 'free'],
         note='the rotary feeder\'s hand crank: turn it to free the jammed feeder (dust caked in the cold), then the motor '
              'takes over')
    # the blower beside it, the duct to the mast, the mast and its swivel nozzle (SkySprayer_Nozzle)
    bc = V3(0.0, -1.15, 0.85)
    k.lathe(bc - Y * 0.25, Y, [(0.0, 0.0), (0.0, 0.52), (0.50, 0.52), (0.50, 0.0)], Z_BLOWER, 18, cap0=False, cap1=False)
    k.box(0.30, 0.75, -1.38, -0.92, 0.85, 1.25, Z_BLOWER)                                     # the scroll's outlet
    k.lathe(bc + Y * 0.25, Y, [(0.0, 0.20), (0.32, 0.20), (0.36, 0.12)], Z_MOTOR, 12)
    rod(k, V3(0.0, -0.30, zo - 0.40), V3(0.0, -0.90, 1.10), 0.10, Z_MAST, 8)                    # the feed into the blower
    mast_x = 0.55
    k.tube([V3(mast_x, -1.15, 1.25), V3(mast_x, -1.15, 6.4)], 0.11, Z_MAST, 10)
    for z in (2.2, 3.05):
        bar(k, V3(mast_x, -1.15, z), V3(0.97, -0.99, z), 0.05, 0.05, Z_SKID, up=Z)
    Nz = reg('SkySprayer_Nozzle', 'SkyMachines', root)
    ncn = V3(mast_x, -1.15, 6.4)
    Nz.lathe(ncn, Z, [(0.0, 0.14), (0.12, 0.14), (0.16, 0.12)], Z_NOZZLE, 10)
    Nz.tube([ncn + Z * 0.12, ncn + Z * 0.40, ncn + Z * 0.55 + Y * -0.15, ncn + Z * 0.58 - Y * 0.45], 0.09, Z_NOZZLE, 10)
    Nz.lathe(ncn + Z * 0.58 - Y * 0.45, -Y, [(0.0, 0.09), (0.25, 0.20)], Z_NOZZLE, 10, cap0=False, cap1=False)
    part('SkySprayer_Nozzle', 'spin', ncn, axis=(0, 0, 1), parent=root, states=['stopped', 'spraying'],
         note='the swivel nozzle on the mast (6.4 m): sweeps round while it sprays (a slow 360 deg, ~20 s); the dust plume is '
              'an effect (Fx_DustPlume from its mouth along -y local)')
    socket('Fx_DustPlume', ncn + Z * 0.58 - Y * 0.70, 'effect', parent='SkySprayer_Nozzle', dir=(0, -1, 0.15),
           note='the plume\'s origin and direction (child of the nozzle)')
    # the lid (IX_SkySprayerLid): a grid hatch over the rim, hinged at the back
    Ld = reg('IX_SkySprayerLid', 'SkyMachines', root)
    Ld.box(-a_ - 0.04, a_ + 0.04, -a_ - 0.04, a_ + 0.04, zt + 0.04, zt + 0.08, Z_HOPPER)
    for xx in np.linspace(-a_ + 0.15, a_ - 0.15, 7):
        Ld.box(xx - 0.02, xx + 0.02, -a_, a_, zt + 0.08, zt + 0.12, Z_HOPPER)
    Ld.box(-0.15, 0.15, -a_ - 0.10, -a_ - 0.04, zt + 0.06, zt + 0.10, Z_LEVER)
    part('IX_SkySprayerLid', 'hinge', (0.0, a_ + 0.04, zt + 0.06), axis=(1, 0, 0), rng=(0, 110), parent=root,
         states=['closed', 'open'], note='the hopper\'s grid lid, hinged at the back: open it to empty dust sacks in')
    socket('Slot_DustPour', (0.0, 0.0, zt + 0.15), 'pour', parent=root, dir=(0, 0, -1),
           note='where a dust sack is emptied (the hopper takes 12 sacks; the heap SkySprayer\'s inside rises with the level)')
    # the platform at the rim (+x side): a grating on a frame, a railing open at the ladder, the ladder up to it
    g = reg('SkySprayer_Grating', 'grating', root)
    deck(g, 1.05, 1.85, -1.0, 1.0, zt)
    for (xa, xb, ya, yb) in ((1.05, 1.85, -1.0, -0.95), (1.05, 1.85, 0.95, 1.0), (1.80, 1.85, -0.95, 0.95), (1.05, 1.10, -0.95, 0.95)):
        k.box(xa, xb, ya, yb, zt - 0.12, zt - 0.005, Z_SKID)
    for yy in (-0.95, 0.95):
        bar(k, V3(1.80, yy, 0.20), V3(1.80, yy, zt - 0.12), 0.06, 0.06, Z_SKID, up=X)
    railing(k, [(1.10, -1.0, zt), (1.82, -1.0, zt), (1.82, -0.28, zt)], Z_RAILY, h=1.0, r=0.02)
    railing(k, [(1.82, 0.28, zt), (1.82, 1.0, zt), (1.10, 1.0, zt)], Z_RAILY, h=1.0, r=0.02)
    for yy in (-0.20, 0.20):
        bar(k, V3(2.05, yy, 0.0), V3(2.05, yy, zt + 0.9), 0.05, 0.015, Z_LADDER, up=X)
        bar(k, V3(1.85, yy, zt - 0.10), V3(2.05, yy, zt - 0.10), 0.04, 0.012, Z_LADDER, up=Z)
    for z in np.arange(0.28, zt, 0.28):
        rod(k, V3(2.05, -0.20, z), V3(2.05, 0.20, z), 0.014, Z_LADDER, 6, caps=False)
    # the control box on the -x leg (panel faces -x), the sight glass, dust heaps round the foot
    k.box(-1.30, -1.12, -0.45, 0.05, 1.05, 1.65, Z_CAB)
    kf.quad_uv(V3(-1.302, -0.20, 1.35), -X, 0.50, 0.60, uv('sprayer'))
    k.box(-0.62, -0.58, -0.25, 0.25, 2.35, 2.75, Z_PULLEY)
    for i in range(7):
        a = TAU * hsh(i, 51)
        r_ = 1.2 + 0.4 * hsh(i, 52)
        c_ = V3(math.cos(a) * r_, math.sin(a) * r_, 0.20)
        k.lathe(c_, Z, [(0.0, 0.35 + 0.25 * hsh(i, 53)), (0.06, 0.25), (0.10, 0.0)], Z_DUST, 8, cap0=False)
    part('SkySprayer_Grating', 'static', (0, 0, 0), parent=root, note='the platform\'s grating (M_Sky_Grating)')
    part(root, 'static', (0, 0, 0), note='the bone-dust sprayer (root): origin on the ground under its plinth\'s middle; the '
                                          'mast and blower at the front (-y), the platform and ladder at +x')
    B = BOXES.append
    B(('SkySprayer_Plinth', root, (-1.6, 1.6, -1.6, 1.6, 0.0, 0.2), None))
    B(('SkySprayer_Hopper', root, (-1.05, 1.05, -1.05, 1.05, 0.2, zt + 0.12), None))
    B(('SkySprayer_Blower', root, (-0.55, 0.80, -1.45, -0.85, 0.2, 1.4), None))
    B(('SkySprayer_Mast', root, (mast_x - 0.12, mast_x + 0.12, -1.27, -1.03, 1.2, 6.5), None))
    B(('SkySprayer_Platform', root, (1.05, 1.85, -1.0, 1.0, zt - 0.12, zt), None))
    B(('SkySprayer_PlatRail', root, (1.80, 1.86, -1.0, 1.0, zt, zt + 1.0), None))


# ================================================================ SkyBallast
def build_ballast():
    root = 'SkyBallast'
    k = reg(root, 'SkyStructures', root)
    PX0, PX1, PY0, PY1, PZ = -2.5, 2.5, 0.6, 4.3, -1.0          # the rams' pit under the deck
    kf = reg('SkyBallast_Signs', 'panel', root, merge=root)
    gl_bc = reg('SkyBallast_Beacon', 'amber', root)
    # the foundation: a slab flush with the ground (its sides and back in the ground), a pit under the deck for the rams,
    # its face 2.6 m down the cliff edge
    for (xa, ya), (xb, yb) in (((-3.4, 0.0), (3.4, PY0)), ((-3.4, PY1), (3.4, 6.0)), ((-3.4, PY0), (PX0, PY1)),
                               ((PX1, PY0), (3.4, PY1))):
        quad(k, [(xa, ya, 0.0), (xb, ya, 0.0), (xb, yb, 0.0), (xa, yb, 0.0)], Z_CONC, Z)
    quad(k, [(-3.4, 0.0, -2.6), (3.4, 0.0, -2.6), (3.4, 0.0, 0.0), (-3.4, 0.0, 0.0)], Z_CONC, -Y)
    for sx in (-1, 1):
        quad(k, [(sx * 3.4, 0.0, -2.6), (sx * 3.4, 0.6, -2.6), (sx * 3.4, 0.6, 0.0), (sx * 3.4, 0.0, 0.0)], Z_CONC, X * sx)
    quad(k, [(-3.4, 0.0, -2.6), (3.4, 0.0, -2.6), (3.4, 0.6, -2.6), (-3.4, 0.6, -2.6)], Z_CONC, -Z)
    quad(k, [(PX0, PY0, PZ), (PX1, PY0, PZ), (PX1, PY1, PZ), (PX0, PY1, PZ)], Z_PIT, Z)               # the pit
    quad(k, [(PX0, PY0, PZ), (PX1, PY0, PZ), (PX1, PY0, 0.0), (PX0, PY0, 0.0)], Z_PIT, Y)
    quad(k, [(PX0, PY1, PZ), (PX1, PY1, PZ), (PX1, PY1, 0.0), (PX0, PY1, 0.0)], Z_PIT, -Y)
    quad(k, [(PX0, PY0, PZ), (PX0, PY1, PZ), (PX0, PY1, 0.0), (PX0, PY0, 0.0)], Z_PIT, X)
    quad(k, [(PX1, PY0, PZ), (PX1, PY1, PZ), (PX1, PY1, 0.0), (PX1, PY0, 0.0)], Z_PIT, -X)
    k.box(-2.6, 2.6, 0.1, 0.35, 0.0, 0.08, Z_HINGE)                                          # the hinge plinth's plate
    # the deck (IX_SkyBallastDeck): a steel plate with ribs under it, side kerbs, a back stop; hinge at the front edge
    D = reg('IX_SkyBallastDeck', 'SkyStructures', root)
    dz = 0.30                                                   # deck top above the slab
    box6(D, (-2.5, 0.25, dz - 0.05), (2.5, 4.4, dz), {'*': Z_DECK, '-z': Z_DECKUND})
    for xx in (-2.0, -0.7, 0.7, 2.0):
        D.box(xx - 0.07, xx + 0.07, 0.30, 4.35, dz - 0.28, dz - 0.05, Z_DECKUND)
    for yy in (1.4, 2.9):
        D.box(-2.45, 2.45, yy - 0.06, yy + 0.06, dz - 0.22, dz - 0.05, Z_DECKUND)
    for sx in (-1, 1):
        D.box(sx * 2.5 - (0.10 if sx > 0 else 0.0), sx * 2.5 + (0.0 if sx > 0 else 0.10), 0.25, 4.4, dz, dz + 0.35, Z_DECK)
    D.box(-2.5, 2.5, 4.25, 4.4, dz, dz + 0.45, Z_DECK)
    for xx in (-1.9, 0.0, 1.9):
        rod(D, (xx - 0.25, 0.22, 0.12), (xx + 0.25, 0.22, 0.12), 0.09, Z_HINGE, 10)
        D.box(xx - 0.22, xx + 0.22, 0.20, 0.55, 0.08, dz - 0.05, Z_HINGE)
    for xx in (-1.2, 1.2):
        D.box(xx - 0.15, xx + 0.15, 3.35, 3.65, dz - 0.40, dz - 0.28, Z_HINGE)                 # the rams' upper lugs
    part('IX_SkyBallastDeck', 'hinge', (0.0, 0.22, 0.12), axis=(1, 0, 0), rng=(0, 38), parent=root, states=['level', 'tipped'],
         note='the tilting deck over the edge: the rams lift its back, it tips forward (-y) about the hinge line at the edge '
              'and the ballast slides off into the fog; only while IX_SkyBallastLever is held (falls back slowly when let go)')
    # the rams: barrel on a lug in the pit, aimed at the deck's lug (aim + stretch in Unity)
    for side, xx in (('L', -1.2), ('R', 1.2)):
        k.box(xx - 0.18, xx + 0.18, 3.32, 3.68, PZ, PZ + 0.15, Z_HINGE)
        R_ = reg(f'SkyBallast_Ram_{side}', 'SkyStructures', root)
        p0, p1 = V3(xx, 3.5, PZ + 0.18), V3(xx, 3.5, dz - 0.44)
        rod(R_, p0, p0 + Z * 0.40, 0.11, Z_RAM, 10)
        rod(R_, p0 + Z * 0.40, p1, 0.05, Z_RAM, 8)
        part(f'SkyBallast_Ram_{side}', 'aim', p0, axis=(0, 0, 1), parent=root, target='IX_SkyBallastDeck',
             target_pos=list(p1), note='hydraulic ram: pivots at its base in the pit and points at its lug under the deck '
                                        '(target_pos, in the deck\'s rest pose); stretch its rod to the distance')
    # the ballast: three concrete blocks on the deck (loose: they slide off when it tips)
    for i, xx in enumerate((-1.6, 0.0, 1.6)):
        nm = f'SkyBallast_Block_{i + 1}'
        Bk = reg(nm, 'SkyStructures', root)
        box6(Bk, (xx - 0.6, 1.6 + 0.15 * hsh(i, 61), dz), (xx + 0.6, 2.8 + 0.15 * hsh(i, 61), dz + 1.0), Z_BLOCK)
        Bk.box(xx - 0.25, xx + 0.25, 2.18, 2.24, dz + 1.0, dz + 1.25, Z_HINGE)                 # a lifting eye
        part(nm, 'item', (xx, 2.2, dz), parent='IX_SkyBallastDeck', states=['on_deck', 'dropped'], mass_hint=3500,
             note=f'ballast block {i + 1} (1.2 x 1.2 x 1.0 m concrete, 3.5 t): a rigid body resting on the deck; when it '
                  f'leaves over the edge - despawn after the fall (it drops through the fog)')
    # the lever station, the hydraulic unit, the beacon, the sign
    lx, ly = 3.9, 6.8
    k.box(lx - 0.6, lx + 0.6, ly - 0.6, ly + 0.6, 0.0, 0.15, Z_PAD)
    k.box(lx - 0.12, lx + 0.12, ly - 0.12, ly + 0.12, 0.15, 1.05, Z_POST)
    Lv = reg('IX_SkyBallastLever', 'SkyStructures', root)
    lp = V3(lx, ly - 0.13, 0.95)
    Lv.box(lp.x - 0.06, lp.x + 0.06, lp.y - 0.03, lp.y + 0.03, lp.z - 0.06, lp.z + 0.06, Z_LEVER)
    bar(Lv, lp, lp + V3(0, -0.15, 0.80), 0.05, 0.04, Z_LEVER, up=X)
    Lv.lathe(lp + V3(0, -0.15, 0.80), V3(0, -0.18, 1.0).normalized(), [(0.0, 0.045), (0.14, 0.045), (0.16, 0.0)], Z_LEVER, 8)
    part('IX_SkyBallastLever', 'hinge', lp, axis=(1, 0, 0), rng=(0, 40), parent=root, states=['rest', 'held'],
         note='the release lever: pull and HOLD (springs back when let go) - the deck tips while it is held '
              '(RESEARCH_HORROR 4.2: "drop the ballast off the edge, holding the lever")')
    k.box(lx - 0.5, lx + 0.5, ly + 0.25, ly + 0.95, 0.15, 1.0, Z_HPU)                            # the hydraulic unit
    k.lathe(V3(lx + 0.15, ly + 0.6, 1.0), Z, [(0.0, 0.18), (0.40, 0.18), (0.45, 0.10)], Z_MOTOR, 12)
    kf.quad_uv(V3(lx, ly + 0.248, 0.62), -Y, 0.60, 0.35, uv('ballast_box'))
    for xr, yh, dx in ((1.2, 4.47, -0.3), (-1.2, 4.55, -0.2)):                                # the hoses into the pit
        k.tube([V3(lx + dx, ly + 0.25, 0.25), V3(lx + dx, yh, 0.025), V3(xr, yh, 0.025), V3(xr, PY1 - 0.035, 0.025),
                V3(xr, PY1 - 0.035, PZ + 0.45), V3(xr, 3.62, PZ + 0.45)], 0.025, Z_RAM, 6)
    k.box(lx - 0.04, lx + 0.04, ly - 0.75, ly - 0.69, 0.0, 2.6, Z_POST)                          # the beacon pole and sign
    beacon(k, gl_bc, V3(lx, ly - 0.72, 2.6), r=0.11)
    sign_plate(k, kf, V3(lx, ly - 0.765, 1.75), -Y, 0.70, 0.50, 'ballast', Z_PLATE)
    LIGHTS.append(('Light_SkyBallast_Beacon', root, (lx, ly - 0.72, 2.8), None, 'point', AMBER, 10.0, 'rotate'))
    part('SkyBallast_Beacon', 'static', (0, 0, 0), parent=root, states=['off', 'on'],
         note='amber beacon by the lever: turns while the deck moves (M_Sky_Amber_Off / M_Sky_Amber)')
    # railings along the edge beside the deck, stops at the deck's sides
    for sx in (-1, 1):
        railing(k, [(sx * 2.7, 0.15, 0.0), (sx * 3.35, 0.15, 0.0), (sx * 3.35, 5.9, 0.0)], Z_RAILY, h=1.1, r=0.022,
                posts=[0, 1, 2])
        k.box(sx * 2.62 - 0.08, sx * 2.62 + 0.08, 0.4, 4.3, 0.0, 0.45, Z_HINGE)
    part(root, 'static', (0, 0, 0), note='ballast release at the island\'s edge (root): origin on the ground in the middle of '
                                          'the edge line - the drop is at -y (Unity +Z), the foundation\'s face goes 2.6 m '
                                          'down the cliff; the lever station 4 m to the side, behind')
    B = BOXES.append
    B(('SkyBallast_SlabFront', root, (-3.4, 3.4, 0.0, PY0, -0.6, 0.0), None))
    B(('SkyBallast_SlabBack', root, (-3.4, 3.4, PY1, 6.0, -0.6, 0.0), None))
    B(('SkyBallast_SlabL', root, (-3.4, PX0, PY0, PY1, -0.6, 0.0), None))
    B(('SkyBallast_SlabR', root, (PX1, 3.4, PY0, PY1, -0.6, 0.0), None))
    B(('SkyBallast_PitFloor', root, (PX0, PX1, PY0, PY1, PZ - 0.2, PZ), None))
    B(('SkyBallast_EdgeL', root, (-3.4, -2.62, 0.0, 6.0, 0.0, 1.1), None))
    B(('SkyBallast_EdgeR', root, (2.62, 3.4, 0.0, 6.0, 0.0, 1.1), None))
    B(('SkyBallast_Deck', 'IX_SkyBallastDeck', (-2.5, 2.5, 0.25, 4.4, dz - 0.3, dz), None))
    B(('SkyBallast_LeverPost', root, (lx - 0.6, lx + 0.6, ly - 0.6, ly + 0.95, 0.0, 1.05), None))
    for i, xx in enumerate((-1.6, 0.0, 1.6)):
        B((f'SkyBallast_Block_{i + 1}', f'SkyBallast_Block_{i + 1}', (xx - 0.6, xx + 0.6, 1.6, 2.8, dz, dz + 1.0), None))
    MASS['IX_SkyBallastDeck'] = 6000.0


# ================================================================ SkyAltimeter
def build_altimeter():
    root = 'SkyAltimeter'
    k = reg(root, 'SkyStructures', root)
    kf = reg('SkyAltimeter_Face', 'panel', root, merge=root)
    gl = reg('SkyAltimeter_Lamps', 'amber', root)
    gfl = reg('SkyAltimeter_Glow', 'lamp', root)
    gr = reg('SkyAltimeter_Obstruction', 'red', root)
    z0, z1 = 4.4, 10.0                                          # the board
    bw = 1.75
    for sx in (-1, 1):
        cx = sx * 1.25
        k.box(cx - 0.55, cx + 0.55, -0.55, 0.55, -0.4, 0.15, Z_PAD)
        corners = [(cx - 0.28, -0.18), (cx + 0.28, -0.18), (cx + 0.28, 0.18), (cx - 0.28, 0.18)]
        for (x, y) in corners:
            bar(k, V3(x, y, 0.15), V3(x, y, z1 + 0.3), 0.06, 0.06, Z_TRUSS, up=X)
        zz = 0.3
        i = 0
        while zz < z1:                                          # zig-zag bracing on the front and back faces
            for y in (-0.18, 0.18):
                xa, xb = (cx - 0.28, cx + 0.28) if i % 2 == 0 else (cx + 0.28, cx - 0.28)
                bar(k, V3(xa, y, zz), V3(xb, y, zz + 0.6), 0.035, 0.035, Z_TRUSS, up=Y)
            for x in (cx - 0.28, cx + 0.28):
                bar(k, V3(x, -0.18, zz), V3(x, 0.18, zz), 0.035, 0.035, Z_TRUSS, up=Z)
            zz += 0.6
            i += 1
    # the board: steel back, frame, the face (panel) toward -y
    box6(k, (-bw, -0.26, z0), (bw, -0.20, z1), {'*': Z_BOARD, '-y': Z_BHID})
    for (xa, xb, za, zb) in ((-bw - 0.06, bw + 0.06, z0 - 0.06, z0), (-bw - 0.06, bw + 0.06, z1, z1 + 0.06),
                             (-bw - 0.06, -bw, z0, z1), (bw, bw + 0.06, z0, z1)):
        k.box(xa, xb, -0.30, -0.18, za, zb, Z_BOARD)
    fc = V3(0.0, -0.262, (z0 + z1) / 2)
    kf.quad_uv(fc, -Y, 3.40, 5.60, uv('altimeter'))
    # the lamp column (amber lamps in the face's sockets) and the marker (SkyAltimeter_Marker)
    W, Hh = 3.40, 5.60
    px_x = (52 + 0.5) / 192 * W - W / 2
    yt_px, yb_px = 44, 316 - 34
    zpx = lambda py: (z1 + z0) / 2 + Hh / 2 - (py + 0.5) / 316 * Hh
    zb_, zt_ = zpx(yb_px), zpx(yt_px)
    for kk in range(20):
        zl = zb_ + (zt_ - zb_) * (50 + kk * 100) / 2000.0
        gl.lathe(V3(px_x, -0.265, zl), -Y, [(0.0, 0.05), (0.02, 0.04), (0.035, 0.0)], ZERO, 8, cap0=False, cap1=False)
    Mk = reg('SkyAltimeter_Marker', 'amber', root)
    sxm = (78 + 0.5) / 192 * W - W / 2
    mz = zb_                                                    # rest: 0 m (the contract gives the range)
    tip = V3(sxm - 0.04, -0.30, mz)
    Mk.poly([tip + V3(-0.42, 0, -0.14), tip, tip + V3(-0.42, 0, 0.14)], ZERO, [(0, 0), (1, 0.5), (0, 1)])
    Mk.poly([tip + V3(-0.42, 0.01, 0.14), tip + V3(0, 0.01, 0), tip + V3(-0.42, 0.01, -0.14)], ZERO, [(0, 1), (1, 0.5), (0, 0)])
    k.box(sxm - 0.60, sxm - 0.52, -0.31, -0.27, zb_ - 0.1, zt_ + 0.1, Z_BOARD)                  # the marker's rail
    part('SkyAltimeter_Marker', 'slide', tip, axis=(0, 0, 1), rng=(0, round(zt_ - zb_, 4)), unit='m', parent=root,
         states=['0 m', '2000 m'], note=f'the lit pointer on the scale: z offset = altitude / 2000 m x {zt_ - zb_:.3f} m (0 m at '
                                        f'rest); it is the chapter\'s timer - the island sinks, the pointer creeps down')
    part('SkyAltimeter_Lamps', 'static', (0, 0, 0), parent=root, states=['off', 'on'],
         note='20 amber lamps beside the scale (one per 100 m band): lit up to the current altitude at night; one object, '
              'M_Sky_Amber_Off / M_Sky_Amber (per-lamp lighting needs a split - the lamp k is at 50 + 100 k m)')
    # floodlights on arms over the board, the obstruction light, the ladder up the left leg
    for i, sx in enumerate((-1, 1)):
        a0 = V3(sx * 1.0, -0.24, z1 + 0.06)
        bar(k, a0, a0 + V3(0, -0.9, 0.35), 0.06, 0.06, Z_TRUSS, up=X)
        lc = a0 + V3(0, -0.95, 0.30)
        k.box(lc.x - 0.18, lc.x + 0.18, lc.y - 0.12, lc.y + 0.12, lc.z - 0.10, lc.z + 0.10, Z_LAMPB)
        gfl.quad_uv(lc + V3(0, 0.0, -0.101), -Z, 0.30, 0.18, (0, 0, 1, 1))
        LIGHTS.append((f'Light_SkyAltimeter_{i + 1}', root, tuple(lc + V3(0, 0, -0.12)), (0, 0.55, -0.83), 'spot', WARM, 9.0,
                       'steady'))
    k.box(-0.06, 0.06, -0.25, -0.20, z1 + 0.06, z1 + 0.5, Z_TRUSS)
    beacon(k, gr, V3(0.0, -0.225, z1 + 0.5), r=0.07, h=0.10)
    LIGHTS.append(('Light_SkyAltimeter_Obstruction', root, (0.0, -0.225, z1 + 0.65), None, 'point', REDL, 6.0, 'blink'))
    for xx in (-1.25 - 0.20, -1.25 + 0.20):
        bar(k, V3(xx, -0.45, 0.15), V3(xx, -0.45, z0 - 0.1), 0.05, 0.015, Z_LADDER, up=Y)
    for z in np.arange(0.45, z0 - 0.2, 0.28):
        rod(k, V3(-1.45, -0.45, z), V3(-1.05, -0.45, z), 0.014, Z_LADDER, 6, caps=False)
    for z in (0.3, 2.0, 3.6):
        bar(k, V3(-1.45, -0.45, z), V3(-1.45, -0.18, z), 0.04, 0.012, Z_LADDER, up=Z)
        bar(k, V3(-1.05, -0.45, z), V3(-1.05, -0.18, z), 0.04, 0.012, Z_LADDER, up=Z)
    part('SkyAltimeter_Glow', 'static', (0, 0, 0), parent=root, states=['off', 'on'],
         note='the two floodlights\' lenses (M_Sky_Lamp_Off / M_Sky_Lamp)')
    part('SkyAltimeter_Obstruction', 'static', (0, 0, 0), parent=root, states=['off', 'on'],
         note='red obstruction light on top (M_Sky_Red): blinks like the island\'s other beacons (SkyIslandBeacons)')
    part(root, 'static', (0, 0, 0), note='the altitude board (root): origin on the ground between its two footings; the face '
                                          '(3.4 x 5.6 m, 4.4 .. 10 m up) looks along -y (Unity +Z): set it by the tower facing '
                                          'the field, so the players outside and the one at the tower\'s console see it')
    B = BOXES.append
    for sx, nm in ((-1, 'L'), (1, 'R')):
        B((f'SkyAltimeter_Leg{nm}', root, (sx * 1.25 - 0.32, sx * 1.25 + 0.32, -0.22, 0.22, 0.0, z1 + 0.3), None))
    B(('SkyAltimeter_Board', root, (-bw - 0.06, bw + 0.06, -0.30, -0.18, z0 - 0.06, z1 + 0.06), None))


# ================================================================ SkyWalk modules
WW, HR = 1.2, 1.1                                               # walkway width, railing height


def deck(kg, x0, x1, y0, y1, z):
    """grating deck face (own material: box-mapped, UV 1 = 0.5 m) seen from above and below"""
    kg.poly([V3(x0, y0, z), V3(x1, y0, z), V3(x1, y1, z), V3(x0, y1, z)], 1)
    kg.poly([V3(x0, y1, z - 0.005), V3(x1, y1, z - 0.005), V3(x1, y0, z - 0.005), V3(x0, y0, z - 0.005)], 1)


def channel(k, a, b, depth=0.20, flange=0.06, t=0.012, side=1, zone=Z_WSTR):
    """C-channel stringer from a to b (top edge at a / b), its back on the walkway's outside (side +-1 along x)"""
    a, b = Vector(a), Vector(b)
    t_ = (b - a).normalized()
    up = Z - t_ * Z.dot(t_)
    up.normalize()
    s = X * side
    L = (b - a).length
    mid = (a + b) / 2 - up * (depth / 2)
    R = Matrix((t_, s, up)).transposed()
    if R.determinant() < 0:
        R = Matrix((t_, -s, up)).transposed()
    k.box_m(mid, (L, t, depth), zone, R)
    for zz in (-depth / 2 + t / 2, depth / 2 - t / 2):
        k.box_m(mid + up * zz - s * (flange / 2), (L, flange, t), zone, R)


def hanger(k, p, zone=Z_WHANG):
    """turnbuckle and clevis on a hanger point (the cable goes up from its top)"""
    p = Vector(p)
    k.box(p.x - 0.03, p.x + 0.03, p.y - 0.015, p.y + 0.015, p.z, p.z + 0.08, zone)
    k.lathe(p + Z * 0.08, Z, [(0.0, 0.018), (0.20, 0.018)], zone, 6)
    k.lathe(p + Z * 0.28, Z, [(0.0, 0.010), (0.05, 0.010)], zone, 6)


def walk_root(name, note):
    part(name, 'static', (0, 0, 0), note=note)


def build_walks():
    # ---- Straight: 4 m
    nm = 'SkyWalk_Straight'
    k = reg(nm, 'SkyWalk', nm)
    g = reg(nm + '_Grating', 'grating', nm)
    L = 4.0
    deck(g, -WW / 2, WW / 2, 0.0, L, 0.0)
    for sx in (-1, 1):
        channel(k, (sx * WW / 2, 0, 0.0), (sx * WW / 2, L, 0.0), side=sx)
        railing(k, [(sx * (WW / 2 - 0.03), 0.05, 0.0), (sx * (WW / 2 - 0.03), L / 2, 0.0), (sx * (WW / 2 - 0.03), L - 0.05, 0.0)],
                Z_WRAIL, h=HR, toe=0.008, toe_zone=Z_WTOE)
    for yy in (0.4, L - 0.4):
        k.box(-WW / 2 - 0.10, WW / 2 + 0.10, yy - 0.04, yy + 0.04, -0.24, -0.20, Z_WSTR)          # the hanger beams
        for sx in (-1, 1):
            hanger(k, (sx * (WW / 2 + 0.07), yy, -0.20))
            socket(f'{nm}_Hang_{"AB"[int(yy > 1)]}{"LR"[int(sx > 0)]}', (sx * (WW / 2 + 0.07), yy, 0.10), 'hang', parent=nm,
                   dir=(0, 0, 1), note='a cable (SkyWalk_Cable) goes up from here to a rock anchor')
    socket(f'{nm}_End', (0, L, 0), 'link', parent=nm, note='the next module\'s origin goes here')
    walk_root(nm, 'walkway 4 m (root): origin on the deck at its start, middle; runs along +y (Unity -Z); grating deck, '
                  'C-channel stringers, railings 1.1 m with toe boards, two hanger beams with turnbuckles')
    BOXES.append((nm + '_Deck', nm, (-WW / 2, WW / 2, 0, L, -0.2, 0.0), None))
    for sx in (-1, 1):
        BOXES.append((f'{nm}_Rail{"LR"[int(sx > 0)]}', nm, (sx * WW / 2 - 0.03, sx * WW / 2 + 0.03, 0, L, 0, HR), None))
    # ---- Stair: 3 m down over 4.2 m
    nm = 'SkyWalk_Stair'
    k = reg(nm, 'SkyWalk', nm)
    g = reg(nm + '_Grating', 'grating', nm)
    n, rise, run = 14, 3.0 / 14, 0.30
    Ls = n * run
    for i in range(n):
        y0, y1 = i * run, (i + 1) * run
        zt = -(i + 1) * rise if i < n - 1 else -3.0
        deck(g, -WW / 2 + 0.04, WW / 2 - 0.04, y0 + 0.02, y1, zt + rise * 0.0 if i < n - 1 else -3.0)
        k.box(-WW / 2 + 0.04, WW / 2 - 0.04, y0 + 0.02, y0 + 0.05, zt - 0.03, zt, Z_WSTR)             # the nosing
    for sx in (-1, 1):
        channel(k, (sx * WW / 2, 0, 0.05), (sx * WW / 2, Ls, -3.0 + 0.05), depth=0.28, side=sx)
        railing(k, [(sx * (WW / 2 - 0.03), 0.05, 0.0), (sx * (WW / 2 - 0.03), Ls / 2, -1.5), (sx * (WW / 2 - 0.03), Ls - 0.05, -3.0)],
                Z_WRAIL, h=HR * 0.95)
    for yy, zz in ((0.4, -0.35), (Ls - 0.4, -3.0 + 0.05 - 0.35)):
        k.box(-WW / 2 - 0.10, WW / 2 + 0.10, yy - 0.04, yy + 0.04, zz - 0.04, zz, Z_WSTR)
        for sx in (-1, 1):
            hanger(k, (sx * (WW / 2 + 0.07), yy, zz))
            socket(f'{nm}_Hang_{"AB"[int(yy > 1)]}{"LR"[int(sx > 0)]}', (sx * (WW / 2 + 0.07), yy, zz + 0.30), 'hang', parent=nm,
                   dir=(0, 0, 1), note='a cable goes up from here to a rock anchor')
    socket(f'{nm}_End', (0, Ls, -3.0), 'link', parent=nm, note='the next module\'s origin (3 m lower)')
    walk_root(nm, 'stair flight (root): from the deck at its top (origin, middle) 14 grating treads down 3 m over 4.2 m along +y')
    ang = math.degrees(math.atan2(3.0, Ls))
    BOXES.append((nm + '_Ramp', nm, (-WW / 2, WW / 2, Ls / 2 - math.hypot(3.0, Ls) / 2, Ls / 2 + math.hypot(3.0, Ls) / 2,
                                      -1.5 - 0.15, -1.5), (-ang, 0, 0)))
    for sx in (-1, 1):
        BOXES.append((f'{nm}_Rail{"LR"[int(sx > 0)]}', nm, (sx * WW / 2 - 0.03, sx * WW / 2 + 0.03, 0, Ls, -3.0, HR), None))
    # ---- Landing: 2.4 x 2.4 m, openings in the middle of -y and +y
    nm = 'SkyWalk_Landing'
    k = reg(nm, 'SkyWalk', nm)
    g = reg(nm + '_Grating', 'grating', nm)
    S2 = 1.2
    deck(g, -S2, S2, 0.0, 2 * S2, 0.0)
    for sx in (-1, 1):
        channel(k, (sx * S2, 0, 0), (sx * S2, 2 * S2, 0), side=sx)
    for yy, sy in ((0.0, -1), (2 * S2, 1)):
        k.box(-S2, S2, yy - (0.012 if sy < 0 else 0), yy + (0.012 if sy > 0 else 0), -0.20, 0.0, Z_WSTR)
    o = WW / 2
    for yy in (0.03, 2 * S2 - 0.03):
        for sx in (-1, 1):
            railing(k, [(sx * o, yy, 0), (sx * (S2 - 0.03), yy, 0)], Z_WRAIL, h=HR)
    for sx in (-1, 1):
        railing(k, [(sx * (S2 - 0.03), 0.03, 0), (sx * (S2 - 0.03), S2, 0), (sx * (S2 - 0.03), 2 * S2 - 0.03, 0)], Z_WRAIL, h=HR,
                toe=0.008, toe_zone=Z_WTOE)
    for i, (xx, yy) in enumerate(((-S2 - 0.07, 0.1), (S2 + 0.07, 0.1), (-S2 - 0.07, 2 * S2 - 0.1), (S2 + 0.07, 2 * S2 - 0.1))):
        hanger(k, (xx, yy, -0.20))
        socket(f'{nm}_Hang_{i + 1}', (xx, yy, 0.10), 'hang', parent=nm, dir=(0, 0, 1), note='a cable up to a rock anchor')
    socket(f'{nm}_End', (0, 2 * S2, 0), 'link', parent=nm, note='the straight-through exit (+y)')
    walk_root(nm, 'landing 2.4 x 2.4 m (root): origin on the deck in the middle of its -y edge; openings 1.2 m in the middle of '
                  '-y and +y, railings elsewhere, four hangers')
    BOXES.append((nm + '_Deck', nm, (-S2, S2, 0, 2 * S2, -0.2, 0), None))
    # ---- Turn: corner 1.2 x 1.2, in from -y, out to +x; railings on -x and +y
    nm = 'SkyWalk_Turn'
    k = reg(nm, 'SkyWalk', nm)
    g = reg(nm + '_Grating', 'grating', nm)
    deck(g, -WW / 2, WW / 2, 0.0, WW, 0.0)
    channel(k, (-WW / 2, 0, 0), (-WW / 2, WW, 0), side=-1)
    channel(k, (-WW / 2, WW, 0), (WW / 2, WW, 0), side=1)
    k.box(WW / 2 - 0.012, WW / 2, 0.0, 0.10, -0.20, 0.0, Z_WSTR)
    railing(k, [(-WW / 2 + 0.03, 0.05, 0), (-WW / 2 + 0.03, WW - 0.03, 0), (WW / 2 - 0.05, WW - 0.03, 0)], Z_WRAIL, h=HR,
            toe=0.008, toe_zone=Z_WTOE)
    hanger(k, (-WW / 2 - 0.07, WW - 0.1, -0.20))
    socket(f'{nm}_Hang_1', (-WW / 2 - 0.07, WW - 0.1, 0.10), 'hang', parent=nm, dir=(0, 0, 1), note='a cable up to an anchor')
    socket(f'{nm}_End', (WW / 2, WW / 2, 0), 'link', parent=nm, rot_deg=-90,
           note='the next module\'s origin, turned -90 deg about z (Unity: +90 about Y) - a right turn; walked the other way it is '
                'a left turn')
    walk_root(nm, 'corner (root): origin on the deck at its -y edge, middle; enter from -y, leave to +x')
    BOXES.append((nm + '_Deck', nm, (-WW / 2, WW / 2, 0, WW, -0.2, 0), None))
    # ---- Ladder: 4 m cage ladder
    nm = 'SkyWalk_Ladder'
    k = reg(nm, 'SkyWalk', nm)
    Hl = 4.0
    for sx in (-0.22, 0.22):
        bar(k, V3(sx, 0.0, -Hl), V3(sx, 0.0, 1.1), 0.06, 0.016, Z_WRUNG, up=Y)
    for z in np.arange(-Hl + 0.25, 0.0, 0.28):
        rod(k, V3(-0.22, 0.0, z), V3(0.22, 0.0, z), 0.014, Z_WRUNG, 6, caps=False)
    for z in np.arange(-Hl + 2.2, 1.11, 0.75):
        pts = [V3(-0.35 * math.cos(a), -0.35 - 0.35 * math.sin(a) + 0.35, z) for a in np.linspace(0, math.pi, 9)]
        pts = [V3(p.x, -(p.y), p.z) for p in pts]
        k.strip(pts, Z, 0.012, 0.05, Z_WCAGE, caps=True)
    for a in np.linspace(0.3, math.pi - 0.3, 5):
        p = V3(-0.35 * math.cos(a), -0.35 * math.sin(a), 0.0)
        bar(k, p + Z * (-Hl + 2.2), p + Z * 1.1, 0.04, 0.012, Z_WCAGE, up=Z)
    socket(f'{nm}_Top', (0, 0.4, 0.0), 'link', parent=nm, note='where it meets the upper deck (its edge at y 0..0.1)')
    socket(f'{nm}_Bottom', (0, 0.4, -Hl), 'link', parent=nm, note='the lower deck')
    walk_root(nm, 'cage ladder 4 m (root): origin at the top in the rungs\' plane; goes down 4 m, the cage on -y, the climber '
                  'faces +y; the stiles reach 1.1 m over the top as grab rails')
    BOXES.append((nm + '_Cage', nm, (-0.36, 0.36, -0.4, 0.05, -Hl + 2.2, 1.1), None))
    # ---- Cable: a 1 m hanger rod (stretched to length)
    nm = 'SkyWalk_Cable'
    k = reg(nm, 'SkyWalk', nm)
    rod(k, V3(0, 0, 0), V3(0, 0, 1.0), 0.012, Z_WHANG, 6)
    walk_root(nm, 'hanger cable (root): 1 m along +z from its origin - scale z to the length (Hang_* socket up to SkyWalk_Anchor)')
    # ---- Anchor: a rock plate with bolts and an eye
    nm = 'SkyWalk_Anchor'
    k = reg(nm, 'SkyWalk', nm)
    k.box(-0.20, 0.20, -0.20, 0.20, -0.03, 0.0, Z_WPLATE)
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.lathe(V3(sx * 0.14, sy * 0.14, -0.03), -Z, [(0.0, 0.025), (0.02, 0.025), (0.03, 0.0)], Z_WPLATE, 6)
    k.lathe(V3(0, 0, -0.03), -Z, [(0.0, 0.05), (0.06, 0.05), (0.07, 0.03)], Z_WPLATE, 8)
    pts = [V3(0.05 * math.cos(a), 0.0, -0.12 - 0.05 * math.sin(a)) for a in np.linspace(0, TAU, 9)]
    k.tube(pts, 0.012, Z_WPLATE, 6, caps=False)
    socket(f'{nm}_Eye', (0, 0, -0.12), 'hang', parent=nm, note='the cable\'s top goes here')
    walk_root(nm, 'rock anchor (root): the plate\'s back on the rock underside at its origin (normal -z); the eye 0.12 m below')
    # ---- Lamp: a caged lamp on a railing post
    nm = 'SkyWalk_Lamp'
    k = reg(nm, 'SkyWalk', nm)
    gl = reg(nm + '_Glow', 'lamp', nm)
    k.box(-0.03, 0.03, -0.03, 0.03, 0.0, 0.6, Z_WRAIL)
    k.box(-0.05, 0.05, -0.05, 0.05, 0.0, 0.08, Z_WRAIL)
    bar(k, V3(0, 0, 0.6), V3(0, 0.25, 0.75), 0.03, 0.03, Z_WRAIL, up=X)
    bulkhead(k, gl, V3(0, 0.27, 0.75), -Z, Z_WLAMP, Z_WCAGE, up=Y, r=0.10)
    part(nm + '_Glow', 'static', (0, 0, 0), parent=nm, states=['off', 'on'], note='its glass: M_Sky_Lamp_Off / M_Sky_Lamp')
    LIGHTS.append(('Light_SkyWalk_Lamp', nm, (0, 0.27, 0.62), (0, 0, -1), 'spot', WARM, 7.0, 'steady'))
    walk_root(nm, 'walkway lamp (root): clamps to a railing post at its origin (the post\'s top, 1.1 m up), the caged lamp over '
                  'the deck on +y; sodium-warm, sparse (one per ~12 m)')
    for w in ('SkyWalk_Straight', 'SkyWalk_Stair', 'SkyWalk_Landing', 'SkyWalk_Turn'):
        part(w + '_Grating', 'static', (0, 0, 0), parent=w, note='the grating deck (M_Sky_Grating, cut-out, box-mapped 0.5 m)')


def build_sky():
    build_chiller()
    build_sprayer()
    build_ballast()
    build_altimeter()
    build_walks()
