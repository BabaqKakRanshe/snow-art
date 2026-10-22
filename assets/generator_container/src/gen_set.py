"""Generator shed kit, part 2: the old diesel generating set on its skid and its control panel.
Inline four-cylinder diesel (radiator end east, towards the outlet louvre) driving a 40 kVA alternator (west, towards
the door); fuel system on the south side (lift pump with hand primer, water separator with a drain tap, fuel filter
with a bleed screw, inline injection pump with the stop and governor levers, injector pipes, leak-off), oil on the
north side (dipstick, filler cap, filter), radiator with a pressure cap and a drain cock, fan in a shroud, fan belt with
a charging dynamo, exhaust manifold, silencer and the pipe to the wall, air filter with a wing-nut lid, starter,
12 V battery (the van's size: interchangeable) with clamps, alternator terminal box with the main breaker, canvas duct
from the radiator to the louvre; control panel on a frame over the alternator end: six gauges with needles, hour
meter, five warning lamps, key switch, glow and stop buttons, emergency stop, voltage trim.
Shed frame (gen_kit): x east, y north, z up."""
import math
import numpy as np
from mathutils import Vector, Matrix
import van3_mech as VM
import gen_kit as K
from gen_kit import (kb, part, socket, box6, face, quad, uv, GY, FLOOR, IX1, EXH_Y, EXH_Z, LOUV,
                     Z_GPAINT, Z_GIRON, Z_SKID, Z_EXH, Z_ALU2, Z_RAD, Z_RADT, Z_FANB, Z_HOSE2, Z_BELT, Z_STEEL3,
                     Z_COPPER, Z_BRASS2, Z_GLASSB, Z_BATTC, Z_LEAD2, Z_WIRER, Z_WIRERB, Z_YEL2, Z_RED2, Z_PANELBOX,
                     Z_RUBBERM, Z_CANVAS2, Z_ALT, Z_FILTERC, Z_AIRF, Z_BLACK2, Z_CHROME2)
import gen_tex as GT
from van2_kit import up_axes, rrect, ZERO

ZS, ZC, ZF = 0.30, 0.64, 0.84                     # skid top, crank axis, fan axis
SK_X0, SK_X1 = -0.70, 1.80
GP_X, GP_Z0 = -0.663, 1.04                         # panel face plane (normal -x, 3 mm off the box) and its bottom edge
GP_N = Vector((-1, 0, 0))
CYL_X = [0.455 + 0.15 * i for i in range(4)]
PUMP_X = [0.52, 0.60, 0.68, 0.76]
BATT_C = Vector((0.47, GY - 0.2525, 0.22))          # battery base centre, inboard between the south rail and the sump
                                                    # (same box and posts as the van's)
BELT = [(GY, ZC, 0.090), (GY, ZF, 0.075), (GY - 0.25, 0.92, 0.040)]
BELT_X = 1.135
NEEDLE_SPECS = {}                                   # name -> (centre, normal, length, rest_deg, scale)


def gp(u, v, off=0.0):
    """genset panel point: u across (right seen from the front = -y), v up from the bottom edge"""
    return Vector((GP_X - off, GY - u, GP_Z0 + v))


def needle(name, c, n, length, ang, parent, scale):
    k = kb(name, 'needle')
    u, v = up_axes(n)
    a = math.radians(ang)
    d = v * math.cos(a) + u * math.sin(a)
    s = d.cross(n).normalized()
    c = Vector(c)
    tip, tail = c + d * length, c - d * length * 0.2
    w = max(0.0016, length * 0.06)
    face(k, [tail - s * w, tail + s * w, c + s * w * 1.3, tip, c - s * w * 1.3], ZERO, n)
    k.lathe(c - n * 0.001, n, [(0, w * 2.4), (0.002, w * 2.4), (0.003, 0.0)], ZERO, 8, cap0=False)
    v0, v1, a0, a1, unit = scale
    part(name, 'hinge', c, -n, None, rest=float(ang), parent=parent, scale=dict(min=v0, max=v1, angle_min=a0, angle_max=a1, unit=unit),
         note='gauge needle: the axis points into the panel, + = clockwise for the viewer; rest = the modelled angle '
              'from 12 o\'clock; angle(value) from scale (linear), turn by angle - rest')
    NEEDLE_SPECS[name] = (c, n, length, ang, scale)


def bezel(k, c, n, r, zone=Z_CHROME2, h=0.008, seg=14):
    k.lathe(Vector(c), n, [(0.0, r + 0.004), (h * 0.75, r + 0.004), (h, r + 0.001), (h * 0.75, r)], zone, seg,
            cap0=False, cap1=False)


# ================================================================ skid, engine, radiator
def skid(G):
    for sy in (-1, 1):
        ya, yb = sorted((GY + sy * 0.34, GY + sy * 0.42))
        box6(G, (SK_X0, ya, 0.14), (SK_X1, yb, ZS), Z_SKID)
        for x in (-0.62, 0.55, 1.70):
            box6(G, (x - 0.06, ya, FLOOR), (x + 0.06, yb, 0.14), Z_RUBBERM, skip=('-z', '+z'))
        for xe, dx in ((SK_X0, -1), (SK_X1, 1)):                        # lifting eyes
            c = Vector((xe + dx * 0.03, GY + sy * 0.38, 0.22))
            ring = [c + Vector((0.03 * math.cos(t), 0, 0.03 * math.sin(t))) for t in np.linspace(0, 2 * math.pi, 9)]
            G.tube(ring, 0.006, Z_YEL2, 5, caps=False)
    for x in (-0.62, 0.15, 0.95, 1.70):
        box6(G, (x - 0.03, GY - 0.34, 0.16), (x + 0.03, GY + 0.34, 0.28), Z_SKID, skip=('-y', '+y'))


def engine(G, kbs_):
    VM.rbox(G, (0.68, GY, 0.725), (0.72, 0.38, 0.51), Z_GPAINT, r=0.02, ch=0.008)        # block
    for x in np.arange(0.40, 0.97, 0.14):
        for sy in (-1, 1):
            ya, yb = sorted((GY + sy * 0.19, GY + sy * 0.20))
            G.box(x - 0.008, x + 0.008, ya, yb, 0.50, 0.92, Z_GPAINT)
    VM.rbox(G, (0.68, GY, 0.405), (0.64, 0.32, 0.13), Z_GPAINT, r=0.015, ch=0.006)       # sump
    G.cyl((0.90, GY, 0.34), (0.90, GY, 0.325), 0.012, Z_STEEL3, 6)
    VM.rbox(G, (0.68, GY, 1.04), (0.70, 0.36, 0.12), Z_GPAINT, r=0.012, ch=0.005)        # head
    VM.rbox(G, (0.68, GY, 1.15), (0.62, 0.26, 0.10), Z_ALU2, r=0.04, ch=0.015, axis='x')  # rocker cover
    for x in (0.42, 0.94):
        for sy in (-1, 1):
            G.cyl((x, GY + sy * 0.10, 1.19), (x, GY + sy * 0.10, 1.205), 0.007, Z_STEEL3, 6)
    VM.rbox(G, (1.07, GY, 0.74), (0.06, 0.34, 0.48), Z_GPAINT, r=0.03, ch=0.008)          # timing cover
    G.lathe(Vector((0.20, GY, ZC)), (1, 0, 0), [(0.0, 0.29), (0.09, 0.31), (0.12, 0.31)], Z_GPAINT, 18, cap0=True, cap1=False)
    # alternator: end cover (grille), body with bands, adapter ring; feet on the rails
    G.lathe(Vector((-0.55, GY, ZC)), (1, 0, 0), [(-0.03, 0.21), (-0.01, 0.235), (0.0, 0.26), (0.73, 0.26), (0.73, 0.28),
                                                 (0.75, 0.28)], Z_ALT, 18, cap0=True, cap1=True)
    for a in (-0.40, -0.15, 0.08):
        G.lathe(Vector((a, GY, ZC)), (1, 0, 0), [(0.0, 0.26), (0.003, 0.267), (0.017, 0.267), (0.02, 0.26)], Z_ALT, 18,
                cap0=False, cap1=False)
    for x in (-0.45, 0.10):
        for sy in (-1, 1):
            ya, yb = sorted((GY + sy * 0.17, GY + sy * 0.42))
            box6(G, (x - 0.04, ya, ZS), (x + 0.04, yb, 0.46), Z_GPAINT, skip=('-z',))
    for sy in (-1, 1):                                                   # front engine mounts
        ya, yb = sorted((GY + sy * 0.19, GY + sy * 0.40))
        box6(G, (0.92, ya, 0.34), (0.98, yb, 0.50), Z_GPAINT)
        ya, yb = sorted((GY + sy * 0.34, GY + sy * 0.42))
        box6(G, (0.90, ya, ZS), (1.00, yb, 0.34), Z_RUBBERM, skip=('-z',))
    # front: crank pulley, water pump, fan pulley and spacer, dynamo, belt
    G.lathe(Vector((BELT_X - 0.02, GY, ZC)), (1, 0, 0), [(0.0, 0.09), (0.012, 0.09), (0.02, 0.078), (0.028, 0.09),
                                                        (0.04, 0.09)], Z_STEEL3, 16, cap0=True, cap1=True)
    G.cyl((BELT_X - 0.07, GY, ZC), (BELT_X - 0.02, GY, ZC), 0.04, Z_STEEL3, 10, caps=False)     # snout from the timing cover
    G.cyl((BELT_X + 0.02, GY, ZC), (BELT_X + 0.04, GY, ZC), 0.035, Z_STEEL3, 10)
    G.cyl((1.06, GY, ZF), (1.12, GY, ZF), 0.055, Z_GPAINT, 12)
    G.lathe(Vector((1.12, GY, ZF)), (1, 0, 0), [(0.0, 0.075), (0.008, 0.075), (0.015, 0.064), (0.022, 0.075), (0.03, 0.075)],
            Z_STEEL3, 14, cap0=True, cap1=True)
    G.cyl((1.15, GY, ZF), (1.335, GY, ZF), 0.025, Z_STEEL3, 8)
    dc = Vector((0.0, GY - 0.25, 0.92))
    G.cyl((0.92, dc.y, dc.z), (1.11, dc.y, dc.z), 0.06, Z_BLACK2, 12)
    G.lathe(Vector((1.12, dc.y, dc.z)), (1, 0, 0), [(0.0, 0.04), (0.008, 0.04), (0.015, 0.032), (0.022, 0.04), (0.03, 0.04)],
            Z_STEEL3, 10, cap0=True, cap1=True)
    G.box(0.96, 1.04, GY - 0.205, GY - 0.19, 0.86, 0.98, Z_STEEL3)
    G.strip([Vector((1.08, GY - 0.20, 0.78)), Vector((1.08, GY - 0.25, 0.86))], (1, 0, 0), 0.006, 0.02, Z_STEEL3)
    B = kb('Engine_Belt', 'Genset')
    path = VM._belt_path(BELT_X, BELT, n=6)
    B.strip(path + [path[0]], (1, 0, 0), 0.006, 0.014, Z_BELT, caps=False)
    part('Engine_Belt', 'static', (BELT_X, GY, ZF), parent='Genset', states=['ok', 'loose', 'broken'],
         note='fan belt (crank, fan, dynamo): broken = hide it (CHG lamp on, the fan stops: overheating), '
              'loose = squeal and a weak charge')
    F = kb('Engine_Fan', 'Genset')
    fc = Vector((1.36, GY, ZF))
    F.cyl(fc - Vector((0.025, 0, 0)), fc + Vector((0.012, 0, 0)), 0.05, Z_FANB, 10)
    for i in range(4):
        a = math.radians(45 + 90 * i)
        dirv = Vector((0, math.cos(a), math.sin(a)))
        tang = Vector((0, -math.sin(a), math.cos(a)))
        R = Matrix((Vector((1, 0, 0)), dirv, tang)).transposed() @ Matrix.Rotation(math.radians(25), 3, 'Y')
        F.box_m(fc + dirv * 0.135, (0.004, 0.18, 0.07), Z_FANB, R)          # root inside the hub
    part('Engine_Fan', 'spin', fc, (1, 0, 0), parent='Genset', spin_sign=-1,
         note='cooling fan: turns with the engine (1500 rpm x 1.2), negative about +x - it blows through the radiator '
              'towards the louvre')
    socket('Audio_Fan', fc + Vector((0.05, 0, 0)), 'audio', parent='Genset', note='fan roar and the belt (squeal when loose)')
    # radiator: core, tanks, side channels beside the core, uprights and stays, shroud sleeve and ring
    G.box(1.50, 1.58, GY - 0.33, GY + 0.33, 0.40, 1.16, Z_RAD)
    VM.rbox(G, (1.54, GY, 1.21), (0.12, 0.70, 0.10), Z_RADT, r=0.015, ch=0.006)
    VM.rbox(G, (1.54, GY, 0.36), (0.12, 0.70, 0.08), Z_RADT, r=0.015, ch=0.006)
    for sy in (-1, 1):
        ya, yb = sorted((GY + sy * 0.33, GY + sy * 0.37))
        box6(G, (1.49, ya, 0.40), (1.59, yb, 1.16), Z_GPAINT, skip=('-z', '+z'))
        ya, yb = sorted((GY + sy * 0.37, GY + sy * 0.41))
        box6(G, (1.52, ya, ZS), (1.56, yb, 1.26), Z_SKID, skip=('-z',))
        G.tube([(1.53, GY + sy * 0.30, 1.255), (1.00, GY + sy * 0.12, 1.10)], 0.007, Z_STEEL3, 5)
    for lo, hi in (((1.40, GY - 0.35, 1.148), (1.495, GY + 0.35, 1.158)), ((1.40, GY - 0.35, 0.402), (1.495, GY + 0.35, 0.412)),
                   ((1.40, GY - 0.35, 0.412), (1.495, GY - 0.34, 1.148)), ((1.40, GY + 0.34, 0.412), (1.495, GY + 0.35, 1.148))):
        box6(G, lo, hi, Z_GPAINT, skip=('+x',))                           # sleeve inside the tanks' outline
    G.lathe(fc - Vector((0.03, 0, 0)), (1, 0, 0), [(0.0, 0.265), (0.07, 0.265), (0.07, 0.255), (0.0, 0.255)], Z_GPAINT, 20,
            cap0=False, cap1=False)                                     # outer face out, inner face towards the fan
    pc = Vector((1.398, GY, ZF))                                        # back plate: sleeve rectangle -> fan ring
    rect = rrect(Vector((1.398, GY, 0.78)), Vector((0, 1, 0)), Vector((0, 0, 1)), 0.70, 0.736, 0.012, k=4)
    ring = []
    for p_ in rect:
        d_ = Vector((0, p_.y - pc.y, p_.z - pc.z)).normalized()
        ring.append(pc + d_ * 0.265)
    for j in range(len(rect)):
        j2 = (j + 1) % len(rect)
        q = [rect[j], rect[j2], ring[j2], ring[j]]
        face(G, q, Z_GPAINT, (-1, 0, 0))
        face(G, [v + Vector((0.004, 0, 0)) for v in q], Z_GPAINT, (1, 0, 0))
    neck = Vector((1.54, GY + 0.15, 1.26))
    G.cyl(neck, neck + Vector((0, 0, 0.05)), 0.025, Z_BRASS2, 10)
    G.tube([neck + Vector((0.02, 0.02, 0.035)), neck + Vector((0.03, 0.06, 0.03)), Vector((1.585, GY + 0.38, 1.20)),
            Vector((1.585, GY + 0.38, 0.32))], 0.004, Z_HOSE2, 4)
    Rc = kb('Radiator_Cap', 'Genset')
    cp = neck + Vector((0, 0, 0.05))
    Rc.lathe(cp, (0, 0, 1), [(0.0, 0.032), (0.012, 0.035), (0.02, 0.03), (0.024, 0.0)], Z_BRASS2, 12, cap0=True)
    Rc.box_m(cp + Vector((0, 0, 0.014)), (0.085, 0.012, 0.008), Z_BRASS2)
    part('Radiator_Cap', 'twist', cp, (0, 0, 1), (0, 180), parent='Genset', states=['shut', 'safety stop', 'off'],
         note='pressure cap: 90 = first stop (hot: steam hisses out), push down and turn on to 180, then it lifts off')
    socket('Hand_Radiator_Cap', cp + Vector((0, 0, 0.02)), 'hand', parent='Radiator_Cap')
    socket('Pour_Coolant', neck + Vector((0, 0, 0.06)), 'pour', parent='Genset', note='coolant goes in here (cap off)')
    socket('VFX_RadSteam', cp + Vector((0, 0, 0.03)), 'vfx', parent='Genset', dir=(0, 0, 1),
           note='steam out of the neck when the hot cap is opened / the engine boils over')
    dr = Vector((1.582, GY - 0.35, 0.36))                               # tank end, east of the upright
    G.cyl(dr, dr - Vector((0, 0.07, 0)), 0.010, Z_BRASS2, 8)
    D = kb('Radiator_Drain', 'Genset')
    D.cyl(dr - Vector((0, 0.07, 0)), dr - Vector((0, 0.085, 0)), 0.005, Z_BRASS2, 6)
    D.box_m(dr - Vector((0, 0.087, 0)), (0.05, 0.006, 0.01), Z_BRASS2)
    part('Radiator_Drain', 'twist', dr - Vector((0, 0.07, 0)), (0, -1, 0), (0, 180), parent='Genset', removable=False,
         states=['shut', 'open'],
         note='radiator drain cock (south side, low, beside the upright): unscrew (+) to open, coolant runs out (VFX_RadDrain)')
    socket('Hand_Radiator_Drain', dr - Vector((0, 0.09, 0)), 'hand', parent='Radiator_Drain')
    socket('VFX_RadDrain', dr - Vector((0, 0.07, 0.015)), 'vfx', parent='Genset', dir=(0, 0, -1), note='coolant runs out here')
    # hoses, thermostat housing
    G.box(1.035, 1.085, GY + 0.05, GY + 0.11, 1.04, 1.09, Z_GPAINT)
    G.tube([(1.08, GY + 0.08, 1.07), (1.25, GY + 0.10, 1.16), (1.40, GY + 0.12, 1.212), (1.49, GY + 0.12, 1.212)], 0.022, Z_HOSE2, 8)
    G.tube([(1.10, GY + 0.10, 0.76), (1.25, GY + 0.16, 0.50), (1.40, GY + 0.18, 0.36), (1.49, GY + 0.18, 0.36)], 0.022, Z_HOSE2, 8)
    # exhaust: manifold (north), riser, silencer on two straps, bellows, pipe to the wall thimble
    VM.rbox(G, (0.69, GY + 0.215, 1.03), (0.58, 0.07, 0.08), Z_EXH, r=0.015, ch=0.005)
    for x in CYL_X:
        G.cyl((x, GY + 0.175, 1.03), (x, GY + 0.20, 1.03), 0.022, Z_EXH, 8)
    G.tube([(0.69, GY + 0.215, 1.065), (0.69, GY + 0.20, 1.22), (0.78, GY + 0.15, 1.34)], 0.03, Z_EXH, 8)
    G.lathe(Vector((0.40, GY + 0.14, 1.42)), (1, 0, 0), [(0.0, 0.06), (0.03, 0.09), (0.57, 0.09), (0.60, 0.06)], Z_EXH, 14,
            cap0=True, cap1=True)
    for x in (0.50, 0.90):
        G.box(x - 0.012, x + 0.012, GY + 0.125, GY + 0.155, 1.10, 1.34, Z_STEEL3)
    for i in range(5):
        x = 1.0 + 0.024 * i
        G.cyl((x, GY + 0.14, 1.42), (x + 0.012, GY + 0.14, 1.42), 0.043, Z_STEEL3, 10)
        G.cyl((x + 0.012, GY + 0.14, 1.42), (x + 0.024, GY + 0.14, 1.42), 0.037, Z_STEEL3, 10)
    G.tube([(1.12, GY + 0.14, 1.42), (1.17, GY + 0.135, 1.46), (1.20, EXH_Y, 1.55), (1.20, EXH_Y, 1.88), (1.24, EXH_Y, 1.935),
            (1.30, EXH_Y, EXH_Z), (IX1 - 0.03, EXH_Y, EXH_Z)], 0.035, Z_EXH, 10, caps=False)
    socket('Heat_Silencer', (0.70, GY + 0.14, 1.53), 'heat', parent='Genset', note='hot silencer: burns, warms hands, melts snow')
    # intake: manifold (south), short elbow, air filter canister with a wing-nut lid
    VM.rbox(G, (0.69, GY - 0.215, 1.04), (0.58, 0.07, 0.08), Z_ALU2, r=0.015, ch=0.005)
    af = Vector((0.66, GY - 0.38, 1.00))
    G.cyl((0.66, GY - 0.25, 1.05), (0.66, GY - 0.30, 1.10), 0.025, Z_HOSE2, 8)
    G.lathe(af, (0, 0, 1), [(0.0, 0.088), (0.28, 0.088)], Z_AIRF, 14, cap0=True, cap1=False)
    G.box(0.62, 0.70, GY - 0.30, GY - 0.18, 0.975, 1.00, Z_STEEL3)
    Lf = kb('Engine_AirFilterLid', 'Genset')
    lc = af + Vector((0, 0, 0.28))
    Lf.lathe(lc, (0, 0, 1), [(0.0, 0.094), (0.015, 0.094), (0.03, 0.06), (0.035, 0.0)], Z_AIRF, 14, cap0=True)
    Lf.cyl(lc + Vector((0, 0, 0.03)), lc + Vector((0, 0, 0.05)), 0.008, Z_STEEL3, 6)
    Lf.box_m(lc + Vector((0, 0, 0.048)), (0.05, 0.008, 0.014), Z_STEEL3)
    part('Engine_AirFilterLid', 'twist', lc + Vector((0, 0, 0.045)), (0, 0, 1), (0, 120), parent='Genset',
         states=['on', 'off'], note='air filter lid: undo the wing nut (+), then lift off')
    socket('Hand_AirFilterLid', lc + Vector((0, 0, 0.05)), 'hand', parent='Engine_AirFilterLid')
    # fuel system (south side)
    VM.rbox(G, (0.64, GY - 0.255, 0.74), (0.32, 0.11, 0.16), Z_ALU2, r=0.012, ch=0.004)
    VM.rbox(G, (0.44, GY - 0.26, 0.74), (0.08, 0.12, 0.20), Z_ALU2, r=0.012, ch=0.004)
    for x in PUMP_X:
        G.cyl((x, GY - 0.255, 0.82), (x, GY - 0.255, 0.85), 0.009, Z_STEEL3, 6)
    for x, xc in zip(PUMP_X, CYL_X):
        G.tube([(x, GY - 0.255, 0.85), (x, GY - 0.275, 0.95), (xc, GY - 0.26, 1.12), (xc, GY - 0.20, 1.145),
                (xc, GY - 0.168, 1.145)], 0.0035, Z_STEEL3, 4)
        G.cyl((xc, GY - 0.155, 1.10), (xc, GY - 0.155, 1.17), 0.011, Z_STEEL3, 6)
    G.tube([Vector((xc, GY - 0.155, 1.178)) for xc in CYL_X], 0.003, Z_STEEL3, 4)
    G.tube([(CYL_X[0], GY - 0.155, 1.178), (0.36, GY - 0.16, 1.17), (0.34, GY - 0.30, 0.90), (0.34, GY - 0.45, 0.50),
            (0.34, GY - 0.46, 0.33), (1.28, GY - 0.46, 0.33), (1.32, GY - 0.52, 0.30), (1.32, GY - 0.52, 0.115)],
           0.004, Z_COPPER, 4)
    St = kb('Engine_StopLever', 'Genset')
    sp = Vector((0.43, GY - 0.325, 0.80))
    St.box_m(sp + Vector((0, -0.004, 0.05)), (0.012, 0.006, 0.10), Z_STEEL3)
    St.lathe(sp + Vector((0, -0.004, 0.10)), (0, 0, 1), [(0.0, 0.010), (0.006, 0.014), (0.016, 0.014), (0.022, 0.0)], Z_RED2, 8)
    G.cyl(sp, sp + Vector((0, 0.01, 0)), 0.012, Z_STEEL3, 8)
    part('Engine_StopLever', 'hinge', sp, (0, -1, 0), (0, 40), parent='Genset', states=['run', 'stop'],
         note='manual stop on the injection pump: pull the red knob back (+40) and hold until the engine dies; springs back')
    socket('Hand_Engine_StopLever', sp + Vector((0, -0.006, 0.11)), 'hand', parent='Engine_StopLever')
    Gv = kb('Engine_GovernorLever', 'Genset')
    gpv = Vector((0.60, GY - 0.316, 0.70))
    gd = Vector((0.6, 0, -0.8))
    Gv.box_m(gpv + gd * 0.04, (0.01, 0.006, 0.08), Z_STEEL3, VM.frame_R(Vector((0, 1, 0)), gd))
    G.cyl(gpv, gpv + Vector((0, 0.01, 0)), 0.01, Z_STEEL3, 8)
    G.cyl((0.62, GY - 0.315, 0.68), (0.70, GY - 0.315, 0.68), 0.004, Z_STEEL3, 5)
    part('Engine_GovernorLever', 'hinge', gpv, (0, -1, 0), (-15, 15), parent='Genset', states=['set (1500 rpm, 50 Hz)'],
         note='governor speed lever, locked at 1500 rpm: frequency = 50 + angle / 6 Hz (needs a spanner to move)')
    G.box(0.88, 0.96, GY - 0.38, GY - 0.30, 0.78, 0.82, Z_ALU2)                       # fuel filter head
    Ff = kb('Engine_FuelFilter', 'Genset')                                            # spin-on canister under it
    Ff.lathe(Vector((0.92, GY - 0.34, 0.62)), (0, 0, 1), [(0.0, 0.035), (0.01, 0.042), (0.15, 0.042), (0.158, 0.04)],
             Z_FILTERC, 12, cap0=True, cap1=True)
    fp = Vector((0.92, GY - 0.34, 0.778))
    part('Engine_FuelFilter', 'twist', fp, (0, 0, -1), (0, 720), parent='Genset', removable='end',
         states=['clean', 'clogged (waxed diesel)'],
         note='spin-on fuel filter: unscrew (+, two turns, from below), then it comes off; FuelFilter_Spare goes on in its place '
              '(Slot_FuelFilter); clogged = the engine starves and dies')
    socket('Hand_Engine_FuelFilter', Vector((0.92, GY - 0.385, 0.68)), 'hand', parent='Engine_FuelFilter')
    socket('Slot_FuelFilter', fp, 'item_slot', parent='Genset', note='filter head: a spin-on filter screws on here')
    G.box(0.90, 0.94, GY - 0.30, GY - 0.19, 0.79, 0.81, Z_STEEL3)
    Bs = kb('Engine_BleedScrew', 'Genset')
    bs = Vector((0.92, GY - 0.34, 0.82))
    Bs.cyl(bs, bs + Vector((0, 0, 0.012)), 0.0055, Z_STEEL3, 6)
    Bs.cyl(bs + Vector((0, 0, 0.008)), bs + Vector((0, 0, 0.018)), 0.0085, Z_STEEL3, 6)
    part('Engine_BleedScrew', 'twist', bs, (0, 0, 1), (0, 720), parent='Genset', removable=False, states=['shut', 'open'],
         note='bleed screw on the filter head: open a turn or two (+), pump Engine_PrimerLever until fuel comes out '
              'without bubbles (VFX_FuelBleed), close it; needed after the tank ran dry')
    socket('Hand_Engine_BleedScrew', bs + Vector((0, 0, 0.02)), 'hand', parent='Engine_BleedScrew')
    socket('VFX_FuelBleed', bs + Vector((0, -0.01, 0.006)), 'vfx', parent='Genset', dir=(0, -1, 0.3),
           note='froth, then clear diesel dribbles out while bleeding')
    G.cyl((0.66, GY - 0.19, 0.54), (0.66, GY - 0.25, 0.54), 0.035, Z_ALU2, 10)        # lift pump + primer
    Pr = kb('Engine_PrimerLever', 'Genset')
    pp = Vector((0.66, GY - 0.25, 0.52))
    Pr.box_m(pp + Vector((0, -0.004, -0.03)), (0.01, 0.006, 0.06), Z_STEEL3)
    Pr.cyl(pp + Vector((0, -0.004, -0.06)), pp + Vector((0, -0.02, -0.06)), 0.007, Z_BLACK2, 6)
    part('Engine_PrimerLever', 'hinge', pp, (0, -1, 0), (0, 35), parent='Genset', states=['rest'],
         note='hand primer on the lift pump: pump it (0..35 and back) to push fuel through for bleeding')
    socket('Hand_Engine_PrimerLever', pp + Vector((0, -0.02, -0.06)), 'hand', parent='Engine_PrimerLever')
    G.box(1.17, 1.23, GY - 0.44, GY - 0.42, 0.20, 0.56, Z_STEEL3)                      # water separator
    G.box(1.16, 1.24, GY - 0.52, GY - 0.44, 0.52, 0.56, Z_ALU2)
    sep = Vector((1.20, GY - 0.48, 0.36))
    G.lathe(sep, (0, 0, 1), [(0.0, 0.03), (0.02, 0.04), (0.14, 0.04), (0.16, 0.035)], Z_GLASSB, 12, cap0=True, cap1=False)
    Wd = kb('Engine_WaterDrain', 'Genset')
    Wd.cyl(sep, sep - Vector((0, 0, 0.018)), 0.0065, Z_BRASS2, 6)
    Wd.box_m(sep - Vector((0, 0, 0.02)), (0.03, 0.005, 0.008), Z_BRASS2)
    part('Engine_WaterDrain', 'twist', sep, (0, 0, -1), (0, 180), parent='Genset', removable=False, states=['shut', 'open'],
         note='drain tap under the water separator bowl: open (+) until the water layer has run out, then diesel')
    socket('Hand_Engine_WaterDrain', sep - Vector((0, 0, 0.02)), 'hand', parent='Engine_WaterDrain')
    socket('VFX_WaterDrain', sep - Vector((0, 0, 0.03)), 'vfx', parent='Genset', dir=(0, 0, -1), note='water, then diesel drips')
    for pts in ([(1.25, GY - 0.50, 0.115), (1.25, GY - 0.50, 0.30), (1.235, GY - 0.49, 0.50), (1.225, GY - 0.485, 0.54)],
                [(1.18, GY - 0.49, 0.555), (1.10, GY - 0.47, 0.565), (0.90, GY - 0.40, 0.565), (0.72, GY - 0.28, 0.555),
                 (0.67, GY - 0.255, 0.555)],
                [(0.66, GY - 0.255, 0.575), (0.70, GY - 0.30, 0.66), (0.82, GY - 0.36, 0.76), (0.88, GY - 0.36, 0.80)],
                [(0.96, GY - 0.32, 0.80), (0.985, GY - 0.29, 0.79), (0.84, GY - 0.27, 0.78), (0.80, GY - 0.26, 0.77)]):
        G.tube([Vector(p) for p in pts], 0.004, Z_COPPER, 4)
    # oil (north side): dipstick tube + stick, filler cap, filter; starter
    t0, t1 = Vector((0.88, GY + 0.20, 0.52)), Vector((0.90, GY + 0.34, 1.00))
    G.tube([t0, t1], 0.006, Z_STEEL3, 6)
    ax = (t1 - t0).normalized()
    Dk = kb('Engine_Dipstick', 'Genset')
    rc = t1 + ax * 0.028
    side = ax.cross(Vector((0, 0, 1))).normalized()
    Dk.tube([rc + side * 0.018 * math.cos(a) + ax * 0.018 * math.sin(a) for a in np.linspace(0, 2 * math.pi, 13)], 0.004, Z_YEL2, 6,
            caps=False)
    Dk.tube([t1 + ax * 0.012, t1 - ax * 0.40], 0.0022, Z_STEEL3, 4)
    part('Engine_Dipstick', 'slide', t1, ax, (0, 0.42), unit='m', parent='Genset', states=['in', 'out'],
         note='pull out by the yellow ring (+0.42): oil level marks on the stick (texture), wipe, push back')
    socket('Hand_Engine_Dipstick', rc, 'hand', parent='Engine_Dipstick')
    oc = Vector((0.92, GY + 0.05, 1.20))
    Oc = kb('Engine_OilCap', 'Genset')
    Oc.lathe(oc, (0, 0, 1), [(0.0, 0.028), (0.014, 0.028), (0.018, 0.022)], Z_BLACK2, 12)
    Oc.box_m(oc + Vector((0, 0, 0.022)), (0.045, 0.008, 0.012), Z_BLACK2)
    part('Engine_OilCap', 'twist', oc, (0, 0, 1), (0, 90), parent='Genset', removable='end', states=['on', 'off'],
         note='oil filler on the rocker cover: quarter turn (+), lift off; Pour_Oil')
    socket('Hand_Engine_OilCap', oc + Vector((0, 0, 0.025)), 'hand', parent='Engine_OilCap')
    socket('Pour_Oil', oc + Vector((0, 0, 0.04)), 'pour', parent='Genset', note='engine oil goes in here (cap off)')
    G.cyl((0.62, GY + 0.19, 0.60), (0.62, GY + 0.31, 0.60), 0.05, Z_FILTERC, 12)
    G.cyl((0.30, GY + 0.25, 0.53), (0.56, GY + 0.25, 0.53), 0.055, Z_BLACK2, 12)
    G.cyl((0.40, GY + 0.25, 0.612), (0.52, GY + 0.25, 0.612), 0.03, Z_BLACK2, 10)
    socket('Audio_Engine', (0.68, GY, 0.80), 'audio', parent='Genset', note='diesel: glow tick, cranking, knock, idle 1500 rpm, '
           'labouring under load, dying')
    socket('Audio_Alternator', (-0.20, GY, ZC), 'audio', parent='Genset', note='alternator whine, rises with the load')


def duct(G):
    """canvas sleeve from the radiator frame to the louvre opening (double-sided), steel flanges at both ends"""
    rings = []
    spec = [(1.605, 0.36, 0.33, 1.25, 0.0), (1.92, 0.45, 0.40, 1.335, 0.02), (IX1 - 0.045, 0.53, 0.47, 1.43, 0.0)]
    for x, hy, z0, z1, bulge in spec:
        c = Vector((x, GY, (z0 + z1) / 2))
        rings.append((c, rrect(c, Vector((0, 1, 0)), Vector((0, 0, 1)), 2 * hy, (z1 - z0) + 2 * bulge, 0.05)))
    for (ca, ra), (cb, rb) in zip(rings[:-1], rings[1:]):
        n = len(ra)
        ia = [p - Vector((0, p.y - ca.y, p.z - ca.z)).normalized() * 0.004 for p in ra]
        ib = [p - Vector((0, p.y - cb.y, p.z - cb.z)).normalized() * 0.004 for p in rb]
        mid = ca.lerp(cb, 0.5)
        for j in range(n):
            j2 = (j + 1) % n
            q = [ra[j], ra[j2], rb[j2], rb[j]]
            cen = sum(q, Vector()) / 4
            out = Vector((0, cen.y - mid.y, cen.z - mid.z))
            face(G, q, Z_CANVAS2, out)
            face(G, [ia[j], ia[j2], ib[j2], ib[j]], Z_CANVAS2, -out)
    for x, hy, z0, z1 in ((1.60, 0.37, 0.32, 1.26),):                 # the wall end is clamped to the louvre frame
        for lo, hi in (((x, GY - hy, z1 - 0.03), (x + 0.03, GY + hy, z1)), ((x, GY - hy, z0), (x + 0.03, GY + hy, z0 + 0.03)),
                       ((x, GY - hy, z0 + 0.03), (x + 0.03, GY - hy + 0.03, z1 - 0.03)),
                       ((x, GY + hy - 0.03, z0 + 0.03), (x + 0.03, GY + hy, z1 - 0.03))):
            box6(G, lo, hi, Z_SKID)


def battery():
    G = K.KBS['Genset']
    tz = BATT_C.z                                                       # tray hung from the south rail, inside the skid
    box6(G, (BATT_C.x - 0.15, GY - 0.34, tz - 0.02), (BATT_C.x + 0.15, GY - 0.16, tz), Z_SKID)
    for lo, hi in (((BATT_C.x - 0.15, GY - 0.165, tz), (BATT_C.x + 0.15, GY - 0.16, tz + 0.03)),
                   ((BATT_C.x - 0.15, GY - 0.34, tz), (BATT_C.x - 0.145, GY - 0.165, tz + 0.03)),
                   ((BATT_C.x + 0.145, GY - 0.34, tz), (BATT_C.x + 0.15, GY - 0.165, tz + 0.03))):
        box6(G, lo, hi, Z_SKID)
    for dx in (-0.11, 0.11):                                            # gussets under the tray, welded to the rail
        box6(G, (BATT_C.x + dx - 0.004, GY - 0.34, tz - 0.06), (BATT_C.x + dx + 0.004, GY - 0.30, tz - 0.02), Z_SKID,
             skip=('-y', '+z'))
    B = kb('Battery', 'Genset')
    bc = BATT_C
    VM.rbox(B, bc + Vector((0, 0, 0.0925)), (0.278, 0.175, 0.185), Z_BATTC, r=0.008, ch=0.004)
    B.box(bc.x - 0.135, bc.x + 0.135, bc.y - 0.083, bc.y + 0.083, bc.z + 0.185, bc.z + 0.195, Z_BATTC)
    for i in range(6):
        x = bc.x - 0.10 + 0.04 * i
        B.cyl((x, bc.y + 0.035, bc.z + 0.195), (x, bc.y + 0.035, bc.z + 0.203), 0.011, Z_BATTC, 8)
    posts = {}
    for name, dx in (('Pos', -0.105), ('Neg', 0.105)):
        p0 = Vector((bc.x + dx, bc.y - 0.04, bc.z + 0.195))
        B.cyl(p0, p0 + Vector((0, 0, 0.022)), 0.0095, Z_LEAD2, 8, r2=0.0085)
        posts[name] = p0 + Vector((0, 0, 0.022))
    B.tube([(bc.x - 0.13, bc.y, bc.z + 0.12), (bc.x - 0.12, bc.y, bc.z + 0.26), (bc.x + 0.12, bc.y, bc.z + 0.26),
            (bc.x + 0.13, bc.y, bc.z + 0.12)], 0.006, Z_BLACK2, 6)
    part('Battery', 'item', bc, (0, 0, 1), parent='Genset', states=['charge 0..1'],
         note='12 V 60 Ah starting battery, the same size and post layout as the van\'s Battery (they swap); lift by the strap '
              'with both clamps off')
    socket('Hand_Battery', bc + Vector((0, 0, 0.26)), 'hand', parent='Battery')
    socket('Slot_Battery', bc, 'item_slot', parent='Genset', note='battery tray inside the skid under the fuel side (reach over the '
           'south rail): a battery stands here, posts towards the aisle')
    for name, dx in (('Pos', -0.105), ('Neg', 0.105)):
        socket(f'Jump_{name}', Vector((bc.x + dx, bc.y - 0.04, bc.z + 0.217)), 'item_slot', parent='Battery',
               note=f'{"plus" if name == "Pos" else "minus"} post: a jumper-cable clamp bites here (the van\'s Battery has its posts '
                    f'at the same place relative to its pivot)')
    for name, zone in (('Pos', Z_WIRER), ('Neg', Z_WIRERB)):
        Cl = kb(f'Battery_Clamp{name}', 'Genset')
        p = posts[name]
        Cl.cyl(p - Vector((0, 0, 0.018)), p + Vector((0, 0, 0.004)), 0.016, Z_LEAD2, 8)
        Cl.box_m(p + Vector((0, -0.028, -0.007)), (0.02, 0.04, 0.012), Z_LEAD2)
        Cl.cyl(p + Vector((0, -0.012, -0.007)), p + Vector((0.03, -0.012, -0.007)), 0.0045, Z_STEEL3, 6)
        end = p + Vector((0, -0.05, -0.007))
        Cl.tube([end, end + Vector((0, -0.03, -0.01)), Vector((end.x, GY - 0.40, ZS + 0.03)), Vector((end.x, GY - 0.43, ZS - 0.02)),
                 Vector((end.x, GY - 0.43, 0.16))], 0.007, zone, 6)              # over the rail, down its outer face
        if name == 'Pos':
            Cl.box_m(p + Vector((0, 0, 0.010)), (0.036, 0.036, 0.014), Z_RED2)
        part(f'Battery_Clamp{name}', 'slide', p, (0, 0, 1), (0, 0.04), unit='m', parent='Genset', states=['on', 'off'],
             note='loosen the bolt, lift off the post (minus first); the cable runs under the skid to the starter')
        socket(f'Hand_Clamp{name}', p + Vector((0, 0, 0.01)), 'hand', parent=f'Battery_Clamp{name}')


def alternator_box(G):
    VM.rbox(G, (-0.15, GY - 0.29, 0.72), (0.30, 0.14, 0.24), Z_GPAINT, r=0.01, ch=0.004)
    G.cyl((-0.15, GY - 0.32, 0.60), (-0.15, GY - 0.32, 0.565), 0.025, Z_BLACK2, 10)
    G.tube([(-0.15, GY - 0.32, 0.565), (-0.15, GY - 0.40, 0.42), (-0.15, GY - 0.45, 0.24), (-0.15, GY - 0.45, 0.13),
            (-0.15, -0.66, 0.095)], 0.018, Z_WIRERB, 8)
    box6(G, (-0.19, GY - 0.40, 0.66), (-0.11, GY - 0.36, 0.78), Z_BLACK2, skip=('+y',))
    Br = kb('Gen_Breaker', 'Genset')
    bp = Vector((-0.15, GY - 0.40, 0.72))
    d = Vector((0, -0.6, -0.8))
    Br.cyl(bp, bp + d * 0.035, 0.006, Z_BLACK2, 6)
    Br.box_m(bp + d * 0.038, (0.03, 0.012, 0.012), Z_BLACK2, VM.frame_R(Vector((1, 0, 0)), d))
    part('Gen_Breaker', 'hinge', bp, (-1, 0, 0), (0, 60), parent='Genset', states=['off (down)', 'on (up)', 'tripped (middle)'],
         note='alternator main breaker on the terminal box (63 A): up = output to the board; trips to the middle on overload')
    socket('Hand_Gen_Breaker', bp + d * 0.04, 'hand', parent='Gen_Breaker')


# ================================================================ control panel
def control_panel(G):
    # frame posts from the rails, cross bar, rubber mounts, the box
    for sy in (-1, 1):
        ya, yb = sorted((GY + sy * 0.36, GY + sy * 0.40))
        box6(G, (-0.59, ya, ZS), (-0.55, yb, 0.98), Z_SKID, skip=('-z', '+z'))
        G.cyl((-0.57, GY + sy * 0.20, 1.02), (-0.57, GY + sy * 0.20, 1.04), 0.02, Z_RUBBERM, 8)
    box6(G, (-0.59, GY - 0.40, 0.98), (-0.55, GY + 0.40, 1.02), Z_SKID)
    VM.rbox(G, (-0.57, GY, GP_Z0 + 0.25), (0.18, 0.60, 0.50), Z_PANELBOX, r=0.01, ch=0.004, axis='x')
    G.tube([(-0.57, GY - 0.10, GP_Z0), (-0.57, GY - 0.15, 0.95), (-0.40, GY - 0.26, 0.88), (-0.22, GY - 0.30, 0.84)], 0.012, Z_WIRERB, 6)
    G.box(-0.60, -0.592, GY - 0.13, GY + 0.13, 0.88, 0.98, Z_SKID)                    # bracket of the start plate
    Fc = kb('GPanel_Face', 'panel')
    n = GP_N
    quad(Fc, gp(0, GT.GP_H / 2, 0.0), n, GT.GP_W, GT.GP_H, uv('gpanel'))
    pl = kb('Genset_Plates', 'panel')
    quad(pl, (-0.603, GY, 0.93), n, 0.24, 0.08, uv('sign_start'))
    quad(pl, (-0.47, GY - 0.259, ZC), (0, -1, 0), 0.10, 0.05, uv('nameplate'))
    part('Genset_Plates', 'static', (-0.603, GY, 0.93), parent='Genset', note='start instructions under the panel, alternator nameplate')
    part('GPanel_Face', 'static', gp(0, 0.25), parent='Genset', note='control panel face (panel atlas): gauges and labels')
    gs = GT.GPANEL
    scales = {'oil': (0, 8, -60, 60, 'bar'), 'temp': (40, 120, -60, 60, 'deg C'), 'batt': (8, 16, -60, 60, 'V'),
              'acv': (0, 500, -120, 120, 'V'), 'aca': (0, 100, -120, 120, 'A'), 'hz': (45, 55, -120, 120, 'Hz')}
    nn = {'oil': 'Needle_Oil', 'temp': 'Needle_Temp', 'batt': 'Needle_Batt', 'acv': 'Needle_GenV', 'aca': 'Needle_GenA',
          'hz': 'Needle_GenHz'}
    for key in ('oil', 'temp', 'batt', 'acv', 'aca', 'hz'):
        u_, v_, d_ = gs[key]
        r = d_ / 2
        c = gp(u_, v_)
        Fc.disc_uv(c + n * 0.003, n, r, uv(key), 16)
        bezel(G, c, n, r, h=0.008)
        sc = scales[key]
        needle(nn[key], c + n * 0.005, n, r * 0.80, sc[2], 'Genset', sc)
    u_, v_, w_, h_ = gs['hours']
    c = gp(u_, v_)
    quad(Fc, c + n * 0.002, n, w_, h_, uv('hours'))
    for lo, hi in (((c.x - 0.008, c.y - w_ / 2 - 0.006, c.z + h_ / 2), (c.x, c.y + w_ / 2 + 0.006, c.z + h_ / 2 + 0.006)),
                   ((c.x - 0.008, c.y - w_ / 2 - 0.006, c.z - h_ / 2 - 0.006), (c.x, c.y + w_ / 2 + 0.006, c.z - h_ / 2)),
                   ((c.x - 0.008, c.y - w_ / 2 - 0.006, c.z - h_ / 2), (c.x, c.y - w_ / 2, c.z + h_ / 2)),
                   ((c.x - 0.008, c.y + w_ / 2, c.z - h_ / 2), (c.x, c.y + w_ / 2 + 0.006, c.z + h_ / 2))):
        box6(G, lo, hi, Z_BLACK2, skip=('+x',))
    for t, colr, u_ in gs['lamps']:
        c = gp(u_, gs['lamp_v'])
        r = gs['lamp_d'] / 2
        bezel(G, c, n, r + 0.001, h=0.006, seg=10)
        Lk = kb('GLamp_' + t, 'lens:' + colr)
        Lk.disc_uv(c + n * 0.002, n, r, uv('l_' + colr), 10, dome=0.005)
        part('GLamp_' + t, 'static', c + n * 0.004, parent='Genset',
             note={'GLOW': 'amber: glow plugs heating (GLOW button held / key at START)',
                   'CHG': 'red: no charge from the dynamo (key ON, engine stopped, or the belt broken)',
                   'OIL': 'red: low oil pressure (key ON, engine stopped, or out of oil: stop it!)',
                   'TEMP': 'red: coolant too hot (louvre shut, belt broken, no coolant)',
                   'RUN': 'green: running and the voltage is up'}[t])
    u_, v_, d_ = gs['vadj']
    c = gp(u_, v_)
    Va = kb('Gen_VAdj', 'Genset')
    Va.cyl(c, c + n * 0.018, d_ / 2, Z_BLACK2, 12)
    Va.box_m(c + n * 0.019 + Vector((0, 0, d_ * 0.25)), (0.002, 0.003, d_ * 0.45), Z_CHROME2)
    part('Gen_VAdj', 'hinge', c, -n, (-135, 135), parent='Genset', states=['nominal 400 V at 0'],
         note='voltage trim: + (clockwise) raises the output voltage, 400 V + angle x 0.3 V')
    socket('Hand_Gen_VAdj', c + n * 0.02, 'hand', parent='Gen_VAdj')
    u_, v_, d_ = gs['key']
    c = gp(u_, v_)
    Fc.disc_uv(c + n * 0.002, n, d_ / 2, uv('keyplate'), 14)
    bezel(G, c, n, d_ / 2, h=0.006)
    Ky = kb('Gen_Key', 'Genset')
    Ky.cyl(c + n * 0.004, c + n * 0.022, 0.0035, Z_BRASS2, 6)
    u_ax, v_ax = up_axes(n)
    Ky.box_m(c + n * 0.034, (0.004, 0.024, 0.026), Z_BRASS2, Matrix((u_ax, v_ax, n)).transposed())
    part('Gen_Key', 'twist', c, -n, (0, 95), parent='Genset', removable='start', states=['OFF 0', 'ON 52', 'START 95'],
         note='key switch: ON (52) powers the panel; START (95, springs back to ON) cranks; pulled out at OFF')
    socket('Hand_Gen_Key', c + n * 0.035, 'hand', parent='Gen_Key')
    for key, name, zone, note in (('glow', 'Gen_GlowButton', Z_YEL2, 'GLOW: hold 20 s before starting in the cold (GLamp_GLOW on)'),
                                  ('stop', 'Gen_StopButton', Z_RED2, 'STOP: electric fuel cut-off while held')):
        u_, v_, d_ = gs[key]
        c = gp(u_, v_)
        bezel(G, c, n, d_ / 2, h=0.006, seg=10)
        Bt = kb(name, 'Genset')
        Bt.cyl(c, c + n * 0.012, d_ / 2 - 0.002, zone, 10)
        part(name, 'slide', c + n * 0.012, -n, (0, 0.006), unit='m', parent='Genset', states=['out', 'pressed'],
             note=note + '; springs back')
        socket('Hand_' + name, c + n * 0.014, 'hand', parent=name)
    u_, v_, d_ = gs['estop']
    c = gp(u_, v_)
    G.cyl(c, c + n * 0.012, 0.016, Z_BLACK2, 10)
    Es = kb('Gen_EStop', 'Genset')
    Es.lathe(c, n, [(0.012, 0.012), (0.018, 0.024), (0.030, 0.024), (0.035, 0.016), (0.037, 0.0)], Z_RED2, 12, cap0=True)
    part('Gen_EStop', 'slide', c + n * 0.037, -n, (0, 0.010), unit='m', parent='Genset', states=['released', 'latched in'],
         note='emergency stop: push in (latches, the engine stops at once); twist clockwise to release (back to 0)')
    socket('Hand_Gen_EStop', c + n * 0.038, 'hand', parent='Gen_EStop')


def build_genset():
    G = kb('Genset', 'Genset')
    skid(G)
    engine(G, None)
    duct(G)
    battery()
    alternator_box(G)
    control_panel(G)
    part('Genset', 'static', ((SK_X0 + SK_X1) / 2, GY, FLOOR), parent='Shed', states=['stopped', 'cranking', 'running', 'dying'],
         note='diesel generating set on its skid: engine, alternator, radiator, panel (one mesh); moving parts are children')
    return G
