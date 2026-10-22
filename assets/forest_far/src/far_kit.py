"""The Forest map's far points in the generator shed's style (Update 3's names, pivots, sizes, places, lights):
  Dish_1..5   - the satellite dishes: a concrete plinth, the pedestal with its ladder, the azimuth head with its drives, the
                yoke and the elevation axle, the reflector (a paraboloid of panels on a rib truss, Update 3's size and
                elevation), the feed on four struts, Update 3's beacon on the feed (M_Light_Red), the equipment cabinet
                (IX_CabinetDoor_2..6, its modules and LEDs: M_LEDOff), the conduit to the plinth, the sign, the yard light
                (Update 3's M_Lamp_SodiumOff lens under its light and halo);
  Radome      - the 16 m lattice tower with a caged ladder, the deck, the radome (white panels), Update 3's beacon on top,
                the equipment shelter with its door and air conditioner, the cable bridge;
  RelayMast   - the 42 m lattice mast (Update 3's taper), beacons at 21 / 42 m, the microwave drum, three panel antennas, the
                feeder ladder, the shelter, the fenced compound with its gate and sign;
  MeteoStation - the weather station: the white picket enclosure with its gate, the louvred screen, the wind mast with
                the anemometer and the vane (guyed), the rain gauge, the logger with its solar panel, the snow stake;
  LookoutTower - the 22 m fire lookout: four legs, X-bracing, Update 3's stairs (the same treads and landings; decorative,
                as in Update 3: steep flights stacked one over another), stringers and handrails, a stairwell in the cab floor over the last flight, a ship ladder up to the floor, the cab (boarded
                walls, windows: M_GlassDirty, pyramid roof, the fire finder), the lightning rod;
  PumpHouse   - brick, a flat felt roof, the steel door (IX_PumpDoor_7), the pump and its motor, the pipe out to the lake,
                the switch box, the sign;
  Chapel      - a plastered chapel on a fieldstone plinth, a shingled roof, the bell turret with its spire and cross, plank
                door (IX_ChapelDoor_8), windows (M_GlassDirty), pews, the altar with its cloth, four candles (M_Candle
                flames where Update 3's halos are), the cross on the east wall, the graves with iron crosses, the sign;
  Cabin       - the forest cabin: notched logs, the plank door (IX_CabinDoor_9), the window (M_GlassDirty), a board and
                felt roof, the porch, the stove and its pipe, the bunk, the table, the woodpile;
  Campsite    - the abandoned camp: the collapsed orange tent, the fire ring with charred logs and the pot, the tipped
                chair, the rucksack and bedroll, a bottle, the torch on the ground (Update 3's M_Headlight lens and light).
Frames: each prefab its own (Update 3's FBX after import): x / y / z, z up, metres; Unity prefab-local (-x, z, -y)."""
import math
import numpy as np
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, socket, face, box6, KBS, CONTRACT
import van3_mech as VM
from road_kit import bar, bars, rod, log_seg, bolt, rrect_xz, _orient
from base_kit import sq, chamfer_box, superring, sign_plate
import far_spec as S
import far_tex as FT

TAU = 2 * math.pi
uv = FT.uv


def V(*a):
    return Vector(a[0]) if len(a) == 1 else Vector(a)


# ---------------------------------------------------------------- zones (1100+)
# the dishes (two atlases, the same zones)
(Z_DPLINTH, Z_DPED, Z_DHEAD, Z_DARM, Z_DAXLE, Z_DREFL, Z_DBACK, Z_DTRUSS, Z_DSTRUT, Z_DFEED, Z_DHORN, Z_DBEACB, Z_DLADDER,
 Z_DCAB, Z_DCABIN, Z_DMOD, Z_DPAD, Z_DDUCT, Z_DSPOST, Z_DSBACK, Z_DLPOLE, Z_DLHEAD, Z_DLFOOT, Z_DBOLT, Z_DMOTOR, Z_DHUB,
 Z_DRIM) = range(1100, 1127)
TILT = (Z_DREFL, Z_DBACK, Z_DTRUSS, Z_DSTRUT, Z_DFEED, Z_DHORN, Z_DBEACB, Z_DHUB, Z_DRIM)
# the radome and the relay mast (the Towers atlas)
(Z_TLEG, Z_TBRACE, Z_TFOOT, Z_TPLATE, Z_TLADDER, Z_TDECK, Z_TGIRDER, Z_TDOME, Z_TDOMERING, Z_TBEACB, Z_THUT, Z_THUTROOF,
 Z_THUTDOOR, Z_TAC, Z_TCABLE, Z_TBRIDGE, Z_TDRUM, Z_TPANEL, Z_TFPOST, Z_TSBACK, Z_TCONC, Z_TSTEEL, Z_TRLEG,
 Z_TRBRACE) = range(1130, 1154)
# the weather station
(Z_MPICKET, Z_MRAIL, Z_MPOST, Z_MSCREEN, Z_MLOUVRE, Z_MLEG, Z_MMAST, Z_MINSTR, Z_MVANE, Z_MGAUGE, Z_MLOGGER, Z_MSOLAR,
 Z_MSTAKE, Z_MGUY, Z_MCONC, Z_MSBACK) = range(1155, 1171)
# the lookout tower
(Z_LLEG, Z_LBRACE, Z_LFOOT, Z_LTREAD, Z_LSTRING, Z_LRAIL, Z_LFLOOR, Z_LBOARD, Z_LPOST, Z_LROOF, Z_LROOFIN, Z_LROD,
 Z_LTABLE, Z_LPLATE, Z_LSBACK) = range(1172, 1187)
# the chapel
(Z_CWALL, Z_CWALLIN, Z_CPLINTH, Z_CROOF, Z_CROOFIN, Z_CBARGE, Z_CTURRET, Z_CSPIRE, Z_CCROSS, Z_CDOOR, Z_CFRAME, Z_CFLOOR,
 Z_CCEIL, Z_CPEW, Z_CALTAR, Z_CCLOTH, Z_CCANDLE, Z_CSTICK, Z_CICON, Z_CGRAVE, Z_CIRON, Z_CSIGN, Z_CBELL) = range(1188, 1211)
# the small ones: the pump house, the cabin, the campsite
(Z_PBRICK, Z_PPLASTER, Z_PBASE, Z_PROOF, Z_PFLASH, Z_PDOOR, Z_PPUMP, Z_PMOTOR, Z_PPIPE, Z_PBOX, Z_PFLOOR, Z_PSBACK,
 Z_KLOG, Z_KLOGEND, Z_KROOF, Z_KBOARD, Z_KDOOR, Z_KFLOOR, Z_KSTOVE, Z_KPIPE, Z_KFURN, Z_KMATT, Z_KDECK, Z_KWOOD, Z_KWOODEND,
 Z_KFRAME, Z_XTENT, Z_XPOLE, Z_XSTONE, Z_XASH, Z_XCHAR, Z_XPOT, Z_XCHAIR, Z_XCFRAME, Z_XPACK, Z_XROLL, Z_XBOTTLE,
 Z_XTORCH, Z_XMUG, Z_KCHINK) = range(1212, 1252)

DISH_ZONES = list(range(1100, 1127))
TOWER_ZONES = list(range(1130, 1154))
METEO_ZONES = list(range(1155, 1171))
LOOK_ZONES = list(range(1172, 1187))
CHAPEL_ZONES = list(range(1188, 1211))
SMALL_ZONES = list(range(1212, 1251))

DRAFT_COL = {}
for _z, _c in {
        Z_DPLINTH: (148, 146, 138), Z_DPED: (214, 214, 206), Z_DHEAD: (206, 206, 198), Z_DARM: (210, 210, 202),
        Z_DAXLE: (150, 154, 150), Z_DREFL: (228, 228, 222), Z_DBACK: (200, 200, 194), Z_DTRUSS: (156, 160, 158),
        Z_DSTRUT: (200, 200, 196), Z_DFEED: (214, 214, 206), Z_DHORN: (170, 172, 168), Z_DBEACB: (40, 40, 40),
        Z_DLADDER: (150, 154, 150), Z_DCAB: (150, 156, 150), Z_DCABIN: (30, 30, 30), Z_DMOD: (120, 124, 126),
        Z_DPAD: (140, 138, 130), Z_DDUCT: (70, 70, 68), Z_DSPOST: (160, 164, 160), Z_DSBACK: (128, 130, 126),
        Z_DLPOLE: (156, 160, 158), Z_DLHEAD: (120, 124, 126), Z_DLFOOT: (140, 138, 130), Z_DBOLT: (90, 92, 92),
        Z_DMOTOR: (90, 96, 100), Z_DHUB: (200, 200, 194), Z_DRIM: (210, 210, 204),
        Z_TLEG: (156, 160, 158), Z_TBRACE: (156, 160, 158), Z_TFOOT: (140, 138, 130), Z_TPLATE: (150, 154, 150),
        Z_TLADDER: (150, 154, 150), Z_TDECK: (130, 132, 128), Z_TGIRDER: (110, 116, 112), Z_TDOME: (230, 230, 224),
        Z_TDOMERING: (150, 154, 150), Z_TBEACB: (40, 40, 40), Z_THUT: (120, 128, 112), Z_THUTROOF: (130, 132, 128),
        Z_THUTDOOR: (100, 110, 84), Z_TAC: (214, 214, 206), Z_TCABLE: (30, 30, 30), Z_TBRIDGE: (150, 154, 150),
        Z_TDRUM: (214, 214, 206), Z_TPANEL: (226, 226, 220), Z_TFPOST: (156, 160, 158), Z_TSBACK: (128, 130, 126),
        Z_TCONC: (140, 138, 130), Z_TSTEEL: (90, 92, 92), Z_TRLEG: (156, 160, 158), Z_TRBRACE: (156, 160, 158),
        Z_MPICKET: (226, 226, 218), Z_MRAIL: (220, 220, 212), Z_MPOST: (220, 220, 212), Z_MSCREEN: (232, 232, 226),
        Z_MLOUVRE: (226, 226, 220), Z_MLEG: (214, 214, 206), Z_MMAST: (160, 164, 160), Z_MINSTR: (150, 154, 150),
        Z_MVANE: (186, 50, 36), Z_MGAUGE: (176, 180, 180), Z_MLOGGER: (210, 210, 204), Z_MSOLAR: (40, 50, 80),
        Z_MSTAKE: (196, 60, 44), Z_MGUY: (120, 124, 124), Z_MCONC: (140, 138, 130), Z_MSBACK: (128, 130, 126),
        Z_LLEG: (150, 154, 150), Z_LBRACE: (150, 154, 150), Z_LFOOT: (140, 138, 130), Z_LTREAD: (120, 124, 120),
        Z_LSTRING: (140, 144, 140), Z_LRAIL: (150, 154, 150), Z_LFLOOR: (130, 112, 86), Z_LBOARD: (70, 56, 42),
        Z_LPOST: (80, 64, 48), Z_LROOF: (150, 154, 150), Z_LROOFIN: (120, 100, 76), Z_LROD: (150, 110, 70),
        Z_LTABLE: (110, 80, 52), Z_LPLATE: (150, 154, 150), Z_LSBACK: (128, 130, 126),
        Z_CWALL: (226, 222, 210), Z_CWALLIN: (222, 218, 204), Z_CPLINTH: (120, 118, 110), Z_CROOF: (90, 80, 70),
        Z_CROOFIN: (70, 56, 42), Z_CBARGE: (64, 50, 38), Z_CTURRET: (70, 56, 42), Z_CSPIRE: (90, 80, 70),
        Z_CCROSS: (40, 38, 36), Z_CDOOR: (70, 52, 36), Z_CFRAME: (60, 48, 36), Z_CFLOOR: (140, 138, 130), Z_CCEIL: (90, 70, 50),
        Z_CPEW: (96, 70, 46), Z_CALTAR: (150, 146, 136), Z_CCLOTH: (220, 210, 180), Z_CCANDLE: (232, 226, 204),
        Z_CSTICK: (180, 150, 80), Z_CICON: (70, 52, 36), Z_CGRAVE: (70, 60, 44), Z_CIRON: (40, 38, 36), Z_CSIGN: (64, 50, 38),
        Z_CBELL: (150, 120, 60),
        Z_PBRICK: (150, 70, 52), Z_PPLASTER: (200, 196, 180), Z_PBASE: (140, 138, 130), Z_PROOF: (40, 40, 42),
        Z_PFLASH: (150, 154, 150), Z_PDOOR: (120, 124, 120), Z_PPUMP: (40, 70, 130), Z_PMOTOR: (110, 116, 112),
        Z_PPIPE: (110, 60, 34), Z_PBOX: (150, 154, 150), Z_PFLOOR: (130, 128, 120), Z_PSBACK: (128, 130, 126),
        Z_KLOG: (110, 92, 72), Z_KLOGEND: (180, 150, 110), Z_KROOF: (40, 40, 42), Z_KBOARD: (70, 56, 42),
        Z_KDOOR: (70, 52, 36), Z_KFLOOR: (130, 108, 80), Z_KSTOVE: (40, 38, 36), Z_KPIPE: (100, 60, 36),
        Z_KFURN: (130, 100, 66), Z_KMATT: (110, 106, 96), Z_KDECK: (120, 110, 94), Z_KWOOD: (96, 80, 62),
        Z_KWOODEND: (176, 150, 112), Z_KFRAME: (210, 206, 194), Z_KCHINK: (150, 140, 118),
        Z_XTENT: (220, 110, 40), Z_XPOLE: (150, 154, 150), Z_XSTONE: (118, 116, 108), Z_XASH: (60, 58, 54),
        Z_XCHAR: (36, 30, 26), Z_XPOT: (120, 122, 120), Z_XCHAIR: (40, 70, 130), Z_XCFRAME: (150, 154, 150),
        Z_XPACK: (200, 90, 34), Z_XROLL: (110, 110, 104), Z_XBOTTLE: (40, 60, 34), Z_XTORCH: (36, 36, 36),
        Z_XMUG: (200, 196, 186)}.items():
    DRAFT_COL[_z] = _c


def obox(k, c, size, zone, R):
    """an oriented box (R columns = its axes); left-handed frames are fixed"""
    VM.obox(k, c, size, zone, R)


def frame_of(t, up=(0, 0, 1)):
    t = Vector(t).normalized()
    up = Vector(up)
    if abs(t.dot(up.normalized())) > 0.98:
        up = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
    s = t.cross(up).normalized()
    u = s.cross(t).normalized()
    return t, s, u


def sign_posts2(k, kf, xs, y, cz, w, h, region, zp, zb, bot=-0.40, r=0.030):
    """a sign plate (face at y, to -y) on two galvanised posts behind it, two hat rails, clamps"""
    for x in xs:
        rod(k, (x, y + 0.045, bot), (x, y + 0.045, cz + h / 2 + 0.02), r, zp, seg=8, caps=False)
        k.lathe(V(x, y + 0.045, cz + h / 2 + 0.02), (0, 0, 1), [(0.0, r + 0.003), (0.018, r + 0.003), (0.026, r * 0.7),
                                                               (0.032, 0.0)], zp, 8, cap0=True, cap1=False)
    sign_plate(k, kf, ((xs[0] + xs[1]) / 2, y, cz), w, h, region, zone=zb)
    for zr in (cz - h * 0.25, cz + h * 0.25):
        k.box(xs[0] - 0.06, xs[1] + 0.06, y + 0.014, y + 0.018, zr - 0.014, zr + 0.014, zb)
        for x in xs:
            rod(k, (x, y + 0.045, zr - 0.012), (x, y + 0.045, zr + 0.012), r + 0.004, zp, seg=8)


def lamp_pole(k, kl, at, yaw_deg, zp, zh, zf, zb):
    """the yard light (base_kit.lightpole's), standing at `at`, its arm turned by yaw (deg, from +x)"""
    import base_spec as BS
    p = BS.LPOLE
    R = Matrix.Rotation(math.radians(yaw_deg), 3, 'Z')
    O = V(at[0], at[1], 0.0)
    T = lambda q: O + R @ V(q)
    f = p['foot']
    ring = lambda r_, z: [T((-r_, -r_, z)), T((r_, -r_, z)), T((r_, r_, z)), T((-r_, r_, z))]
    k.loft([ring(f, p['foot_bottom']), ring(f, p['foot_top'] - 0.02), ring(f - 0.02, p['foot_top'])], [zf, zf], cap1=zf)
    zt = p['foot_top']
    obox(k, T((0, 0, zt + 0.0075)), (0.30, 0.30, 0.015), zb, R)
    for xs in (-1, 1):
        for ys in (-1, 1):
            bolt(k, T((xs * 0.11, ys * 0.11, zt + 0.015)), (0, 0, 1), 0.016, 0.014, zb, washer=0.022)
    z0 = zt + 0.015
    prof = [(0.0, 0.098), (0.20, 0.098), (0.24, p['r0']), (1.0, p['r0'] - 0.003), (3.0, (p['r0'] + p['r1']) / 2 + 0.002),
            (p['top'] - z0 - 0.25, p['r1'] + 0.002), (p['top'] - z0, p['r1'])]
    k.lathe(T((0, 0, z0)), (0, 0, 1), prof, zp, 12, cap0=False, cap1=False)
    k.lathe(T((0, 0, p['top'])), (0, 0, 1), [(0.0, p['r1']), (0.02, p['r1'] + 0.006), (0.05, 0.04), (0.07, 0.0)], zp, 10,
            cap0=False)
    arm = [T((0.0, 0.0, 5.62)), T((0.02, 0.0, 5.86)), T((0.12, 0.0, 6.00)), T((0.36, 0.0, 6.05)), T((0.82, 0.0, 6.05))]
    k.tube(arm, 0.034, zp, 8)
    x0, x1, y0, y1, zb_, ztp = p['head']
    hk = []
    for fz, ins in ((0.0, 0.0), (0.55, 0.0), (0.85, 0.015), (1.0, 0.045)):
        z = zb_ + (ztp - zb_) * fz
        hk.append([T((x0 + ins, y0 + ins, z)), T((x1 - ins - 0.02, y0 + ins, z)), T((x1 - ins, y0 + ins + 0.03, z)),
                   T((x1 - ins, y1 - ins - 0.03, z)), T((x1 - ins - 0.02, y1 - ins, z)), T((x0 + ins, y1 - ins, z))])
    k.loft(hk, [zh] * 3, cap0=zh, cap1=zh)
    lx0, lx1, ly0, ly1, lz = p['lens']
    ring8 = [T((lx0 + 0.02, ly0, lz)), T((lx1 - 0.02, ly0, lz)), T((lx1, ly0 + 0.02, lz)), T((lx1, ly1 - 0.02, lz)),
             T((lx1 - 0.02, ly1, lz)), T((lx0 + 0.02, ly1, lz)), T((lx0, ly1 - 0.02, lz)), T((lx0, ly0 + 0.02, lz))]
    face(kl, ring8, 0.0, (0, 0, -1))
    return T((1.05, 0.0, 5.85))


def ladder(k, x0, x1, pts_rail, zone, rung=0.30, w=0.05, h=0.012, rr=0.013, out=(0, -1, 0)):
    """a fixed ladder: two flat-bar stiles along the polylines pts_rail(x) -> [points], round rungs every `rung`"""
    for x in (x0, x1):
        k.strip(pts_rail(x), V(1, 0, 0), w, h, zone, caps=True)
    pa, pb = pts_rail(x0), pts_rail(x1)
    za, zb_ = pa[0].z, pa[-1].z
    for z in np.arange(za + 0.25, zb_ - 0.1, rung):
        def at(pts, z_):
            for a, b in zip(pts[:-1], pts[1:]):
                if a.z <= z_ <= b.z:
                    t = (z_ - a.z) / max(b.z - a.z, 1e-9)
                    return a.lerp(b, t)
            return pts[-1]
        rod(k, at(pa, z), at(pb, z), rr, zone, seg=6, caps=False)


def lattice(k, corner, zs, zleg, zbar, leg_r, bar_r, diag=True, xbrace=False, legs=(0, 1, 2, 3), seg_leg=8):
    """a square lattice: corner(z, i) -> the i-th leg's point (counter-clockwise from +x+y), levels zs; legs as rods,
    horizontals and a zig-zag (or X) of diagonals on each face"""
    for i in legs:
        pts = [corner(z, i) for z in zs]
        for a, b in zip(pts[:-1], pts[1:]):
            rod(k, a, b, leg_r(a.z), zleg, seg=seg_leg, caps=False)
    for f in range(4):
        i, j = f, (f + 1) % 4
        for n, z in enumerate(zs[1:], 1):
            rod(k, corner(z, i), corner(z, j), bar_r, zbar, seg=6, caps=False)
            za = zs[n - 1]
            if xbrace:
                rod(k, corner(za, i), corner(z, j), bar_r * 0.85, zbar, seg=6, caps=False)
                rod(k, corner(za, j), corner(z, i), bar_r * 0.85, zbar, seg=6, caps=False)
            elif diag:
                p0, p1 = (corner(za, i), corner(z, j)) if n % 2 else (corner(za, j), corner(z, i))
                rod(k, p0, p1, bar_r * 0.9, zbar, seg=6, caps=False)


# ================================================================ the dishes
def dish(name):
    """a dish at its Update 3 elevation: the reflector, the feed and the beacon where Update 3 has them (the vertex 0.20
    behind Update 3's axle on the dish's axis); the elevation shaft behind the reflector (A), the yoke up to it. Every
    dish of a size is built by the same sequence of calls (the same faces in the same order): far_build bakes the
    reference (Dish_1, Dish_3) and copies its UVs onto the others loop by loop"""
    g = S.dish_geom(name)
    s = S.DSIZE[g['size']]
    D = S.DISH
    atlas = 'Dish' + ('16' if g['size'] == 'L' else '12')
    k = kb(name, atlas)
    A = V(*s['shaft'])                                                   # the elevation shaft (along x)
    # the plinth, the pedestal (flange, bolts, the access door, the ladder), the turntable, the azimuth head with its two
    # drives, the yoke arms up to the shaft's bearings
    pl = D['plinth']
    chamfer_box(k, (-pl, -pl, D['plinth_bottom']), (pl, pl, D['plinth_top']), 0.05, Z_DPLINTH)
    zt = D['plinth_top']
    pr = D['ped_r']
    k.lathe(V(0, 0, zt), (0, 0, 1), [(0.0, pr + 0.20), (0.06, pr + 0.20), (0.06, pr + 0.04), (0.14, pr), (s['ped_top'] - zt - 0.12, pr),
                                     (s['ped_top'] - zt - 0.12, pr + 0.06), (s['ped_top'] - zt, pr + 0.06)], Z_DPED, 20,
            cap0=False, cap1=True)
    for a in range(12):
        q = TAU * (a + 0.5) / 12
        bolt(k, (math.cos(q) * (pr + 0.12), math.sin(q) * (pr + 0.12), zt + 0.06), (0, 0, 1), 0.022, 0.02, Z_DBOLT, washer=0.03)
    k.box(pr - 0.02, pr + 0.012, -0.30, 0.30, zt + 0.5, zt + 2.1, Z_DPED)                  # the access door (+x)
    k.box(pr + 0.012, pr + 0.03, 0.18, 0.24, zt + 1.25, zt + 1.35, Z_DBOLT)
    for zz in (zt + 0.75, zt + 1.85):
        k.box(pr + 0.012, pr + 0.024, -0.31, -0.25, zz - 0.06, zz + 0.06, Z_DBOLT)
    ly = D['ladder_y']
    h0, h1 = s['head']
    for xr in (-D['ladder_x'], D['ladder_x']):
        bar(k, (xr, ly, zt + 0.10), (xr, ly, h0 - 0.05), 0.05, 0.012, Z_DLADDER, up=(1, 0, 0))
        for zz in np.arange(zt + 1.0, h0 - 0.3, 1.5):
            bar(k, (xr, ly + 0.025, zz), (xr * 0.8, -pr * 0.94, zz), 0.03, 0.008, Z_DLADDER)
    for zz in np.arange(zt + 0.2, h0 - 0.2, 0.35):
        rod(k, (-D['ladder_x'], ly, zz), (D['ladder_x'], ly, zz), 0.014, Z_DLADDER, seg=6, caps=False)
    hx, hy = D['head']
    k.lathe(V(0, 0, s['ped_top']), (0, 0, 1), [(0.0, pr + 0.10), (h0 - s['ped_top'] + 0.06, pr + 0.10)], Z_DAXLE, 20,
            cap0=True, cap1=False)
    rb = [V(-hx, -hy, h0), V(hx, -hy, h0), V(hx, hy, h0), V(-hx, hy, h0)]
    rm = [V(-hx, -hy, h1 - 0.08), V(hx, -hy, h1 - 0.08), V(hx, hy, h1 - 0.08), V(-hx, hy, h1 - 0.08)]
    rt = [V(-hx + 0.08, -hy + 0.08, h1), V(hx - 0.08, -hy + 0.08, h1), V(hx - 0.08, hy - 0.08, h1), V(-hx + 0.08, hy - 0.08, h1)]
    k.loft([rb, rm, rt], [Z_DHEAD, Z_DHEAD], cap0=Z_DHEAD, cap1=Z_DHEAD)
    for sx in (-1, 1):                                                   # the azimuth drives on the head's back
        c = V(sx * 0.65, -hy - 0.16, h0 + 0.20)
        box6(k, c - V(0.16, 0.16, 0.18), c + V(0.16, 0.16, 0.18), Z_DMOTOR)
        k.cyl(c + V(0, -0.16, 0.0), c + V(0, -0.46, 0.0), 0.12, Z_DMOTOR, 10)
        k.cyl(c + V(0, -0.46, 0.0), c + V(0, -0.49, 0.0), 0.10, Z_DMOTOR, 10)
    a0, a1 = D['arm_x']
    for sx in (-1, 1):                                                   # the yoke arms: plates from the head to the bearings
        xi, xo = sx * a0, sx * a1
        prof = [(-0.85, h1 - 0.01), (0.85, h1 - 0.01), (A.y + 0.42, A.z + 0.10), (A.y + 0.20, A.z + 0.42),
                (A.y - 0.30, A.z + 0.30), (A.y - 0.42, A.z - 0.10)]
        ring_i = [V(xi, py, pz) for py, pz in prof]
        ring_o = [V(xo, py, pz) for py, pz in prof]
        if sx < 0:
            ring_i, ring_o = ring_o, ring_i
        k.loft([ring_i, ring_o], [Z_DARM], cap0=Z_DARM, cap1=Z_DARM)
        k.cyl(V(xi - sx * 0.03, A.y, A.z), V(xo + sx * 0.06, A.y, A.z), 0.30, Z_DARM, 16)          # the bearing housing
        k.cyl(V(xo + sx * 0.06, A.y, A.z), V(xo + sx * 0.12, A.y, A.z), 0.20, Z_DAXLE, 12)
        for a in range(6):
            q = TAU * a / 6
            bolt(k, (xo + sx * 0.06, A.y + 0.25 * math.cos(q), A.z + 0.25 * math.sin(q)), (sx, 0, 0), 0.02, 0.018, Z_DBOLT)
    k.cyl(V(-a0 + 0.02, A.y, A.z), V(a0 - 0.02, A.y, A.z), 0.15, Z_DAXLE, 12, caps=False)
    # ---- the tilting part (its geometry follows the elevation, its faces do not): the reflector (front panels, back
    # skin, rim, the hub's opening and cap), the hub box and its lugs on the shaft, the rib truss, two hoops, the feed on
    # four struts, the beacon
    ax = Vector(tuple(g['axis']))
    u = V(1, 0, 0)
    v = ax.cross(u).normalized()
    vtx = Vector(tuple(g['vertex']))
    f = g['focal']
    R_ = g['R']
    sh = D['shell']
    P = lambda r, ph, off=0.0: vtx + ax * (r * r / (4 * f) + off) + (u * math.cos(ph) + v * math.sin(ph)) * r
    NS = 32
    rs = [0.55] + [R_ * t for t in (0.18, 0.30, 0.42, 0.54, 0.66, 0.78, 0.90, 1.0)]
    phs = [TAU * i / NS for i in range(NS)]
    front = [[P(r, ph) for ph in phs] for r in rs]
    back = [[P(r, ph, -sh) for ph in phs] for r in rs]
    k.loft([list(reversed(rg)) for rg in front], [Z_DREFL] * (len(rs) - 1))          # the concave face to the feed
    k.loft(back, [Z_DBACK] * (len(rs) - 1))
    k.loft([back[-1], front[-1]], [Z_DRIM])                                          # the rim
    rh = rs[0]
    k.loft([front[0], [P(rh, ph, -sh) for ph in phs]], [Z_DHUB])                     # the hub's opening
    face(k, [P(rh * 0.98, ph, 0.002) for ph in phs], Z_DHUB, ax)                     # its cap
    Rm = Matrix((u, v, ax)).transposed()
    hub_c = vtx - ax * (sh + 0.26)
    obox(k, hub_c, (1.40, 1.00, 0.52), Z_DHUB, Rm)                                   # the hub box behind the reflector
    for sx in (-1, 1):                                                   # its lugs round the shaft
        a_ = hub_c + u * (sx * 0.55) - ax * 0.26
        b_ = V(sx * 0.55, A.y, A.z)
        t_, s_, w_ = frame_of(b_ - a_, u)
        bar(k, a_ - (b_ - a_).normalized() * 0.05, b_, 0.36, 0.05, Z_DHUB, up=u)
        k.cyl(V(sx * 0.55 - 0.03, A.y, A.z), V(sx * 0.55 + 0.03, A.y, A.z), 0.20, Z_DHUB, 12)
    nrib = 16
    for i in range(nrib):                                                # tapered ribs: deep at the hub, thin at the rim
        ph = TAU * i / nrib
        pts = [P(r, ph, -sh - 0.005) for r in np.linspace(rh, R_ * 0.98, 7)]
        dep = [0.32 * (1 - 0.8 * (j / 6)) for j in range(7)]
        mid = [p_ - ax * (d_ / 2) for p_, d_ in zip(pts, dep)]
        rings = []
        t0_ = (mid[-1] - mid[0]).normalized()
        for j in range(7):                                               # one loft: the rings shared by the segments
            tj = (mid[min(j + 1, 6)] - mid[max(j - 1, 0)]).normalized()
            _, s_, w_ = frame_of(tj, ax)
            hj = dep[j] / 2
            c_ = mid[j]
            rings.append(_orient([c_ + s_ * 0.025 + w_ * hj, c_ - s_ * 0.025 + w_ * hj, c_ - s_ * 0.025 - w_ * hj,
                                  c_ + s_ * 0.025 - w_ * hj], t0_))
        k.loft(rings, [Z_DTRUSS] * 6, cap1=Z_DTRUSS)
    for hr in (0.50, 0.85):
        ring_ = [P(R_ * hr, ph, -sh - 0.14) for ph in phs]
        k.tube(ring_ + [ring_[0]], 0.035, Z_DTRUSS, 6, caps=False)
    fc = Vector(tuple(g['focus']))
    for i in range(4):
        ph = TAU * (i + 0.5) / 4
        a_ = P(R_ * 0.62, ph, 0.02)
        b_ = fc + ax * 0.25 + (u * math.cos(ph) + v * math.sin(ph)) * 0.26
        rod(k, a_, b_, 0.05, Z_DSTRUT, seg=6)
        k.cyl(a_ - ax * 0.02, a_ + ax * 0.06, 0.09, Z_DSTRUT, 8)
    k.lathe(fc - ax * 0.45, ax, [(0.0, 0.34), (0.02, 0.35), (0.45, 0.14), (0.55, 0.14)], Z_DHORN, 16, cap0=False, cap1=False)
    face(k, k.ring_pts(fc - ax * 0.30, ax, 0.24, 16)[0], Z_DHORN, -ax)               # the horn's throat (dark)
    k.lathe(fc + ax * 0.05, ax, [(0.0, 0.26), (0.02, 0.30), (0.58, 0.30), (0.62, 0.24)], Z_DFEED, 16, cap0=True, cap1=True)
    bc = Vector(S.u2b(next(l['p'] for pl_ in S.U3['prefabLights'] if pl_['model'] == name for l in pl_['lights']
                          if l.get('tag') == 'beacon')))
    t0 = (bc - fc).dot(ax)                                               # Update 3's beacon (0.73 beyond the focus)
    k.lathe(fc + ax * 0.67, ax, [(0.0, 0.11), (t0 - 0.67 - 0.06, 0.11), (t0 - 0.67 - 0.05, 0.095)], Z_DBEACB, 12, cap0=True,
            cap1=False)
    kb_ = kb(name + '_Beacon', 'lens:red')
    kb_.lathe(fc + ax * (t0 - 0.05), ax, [(0.0, 0.095), (0.06, 0.09), (0.12, 0.06), (0.17, 0.0)], 0.0, 12, cap0=False,
              cap1=False)
    # ---- the equipment cabinet on its pad: the body open behind the door, the modules, the LEDs, the roof cap
    x0, x1, y0, y1, z0, z1 = D['cab']
    px0, px1, py0, py1, pz = D['pad']
    chamfer_box(k, (px0, py0, -0.25), (px1, py1, pz), 0.02, Z_DPAD)
    tw = 0.03
    box6(k, (x0, y0, z0), (x1, y1 - 0.08, z1), Z_DCAB)                                # the body behind the bay
    for (a, b) in ((x0, x0 + tw), (x1 - tw, x1)):
        box6(k, (a, y1 - 0.08, z0), (b, y1, z1), Z_DCAB)
    box6(k, (x0 + tw, y1 - 0.08, z0), (x1 - tw, y1, z0 + 0.03), Z_DCAB)
    box6(k, (x0 + tw, y1 - 0.08, z1 - 0.03), (x1 - tw, y1, z1), Z_DCAB)
    face(k, [V(x0 + tw, y1 - 0.077, z0 + 0.03), V(x1 - tw, y1 - 0.077, z0 + 0.03), V(x1 - tw, y1 - 0.077, z1 - 0.03),
             V(x0 + tw, y1 - 0.077, z1 - 0.03)], Z_DCABIN, (0, 1, 0))
    for zm0, zm1 in ((0.36, 0.64), (0.76, 1.04), (1.16, 1.44), (1.52, 1.80)):
        box6(k, (x0 + 0.12, y1 - 0.079, zm0), (x1 - 0.12, y1 - 0.04, zm1), Z_DMOD)
    kl_ = kb(name + '_LED', 'lens:led')
    for i in range(4):
        xx = x0 + 0.18 + i * 0.08
        kl_.quad_uv(V(xx, y1 - 0.039, 1.74), V(0, 1, 0), 0.03, 0.02, (0, 0, 1, 1))
    rx0, rx1, ry0, ry1, rz0, rz1 = D['roof']
    box6(k, (rx0, ry0, rz0), (rx1, ry1, rz1), Z_DCAB)
    for xx in (x0 + 0.15, x1 - 0.15):                                    # the gland plate, the earth bar
        k.box(xx - 0.06, xx + 0.06, y0 - 0.012, y0, z0 + 0.10, z0 + 0.22, Z_DBOLT)
    # the conduit: from the cabinet along the ground, up the plinth's side, along its top into the pedestal
    k.strip([V(x0 + 0.3, y0 + 0.30, 0.04), V(pl + 0.08, -2.2, 0.04), V(pl + 0.08, -2.2, zt + 0.04),
             V(pl - 0.3, -2.0, zt + 0.04), V(pr + 0.02, -0.6, zt + 0.04)], V(0, 0, 1), 0.16, 0.06, Z_DDUCT, caps=True)
    # the sign on its posts
    sg = D['sign']
    kf = kb(name + '_Sign', 'panel')
    sign_posts2(k, kf, sg['posts'], sg['y'], sg['c'][1], sg['w'], sg['h'], uv('dish'), Z_DSPOST, Z_DSBACK, bot=-0.30)
    # the yard light by the cabinet (Update 3's: the light 1.05 out on the arm, toward (5.01, -3.96))
    lp = D['lamp']
    kll = kb(name + '_Lamp', 'lens:sodium')
    yaw = math.degrees(math.atan2(lp['light'][1] - lp['pole'][1], lp['light'][0] - lp['pole'][0]))
    lamp_pole(k, kll, lp['pole'], yaw, Z_DLPOLE, Z_DLHEAD, Z_DLFOOT, Z_DBOLT)
    part(name, 'static', (0, 0, 0), note=f'satellite dish {2 * R_:.0f} m at {g["el"]:.0f} deg: plinth, pedestal, head, yoke, '
                                          'reflector, feed, beacon, cabinet, conduit, sign, yard light')
    for n_, nt in ((name + '_Beacon', 'the beacon\'s dome (Update 3\'s M_Light_Red, always lit)'),
                   (name + '_Lamp', 'the yard light\'s lens (M_Lamp_SodiumOff: the power grid swaps it)'),
                   (name + '_LED', 'the cabinet\'s LEDs (M_LEDOff: the power grid swaps them to M_LEDOn)'),
                   (name + '_Sign', 'the sign face (panel atlas)')):
        part(n_, 'static', (0, 0, 0), parent=name, note=nt)
    # the cabinet door (IX_CabinetDoor_n): Update 3's hinge, a panel with louvres, a handle, a lock, hinges
    dr = D['door']
    kd = kb(g_door(name), atlas)
    hx_, x1_, yd = dr['hinge_x'], dr['x1'], dr['y']
    zd0, zd1 = dr['z']
    yf_ = yd + 0.017                                                     # the leaf's outer face (2 mm off the cabinet)
    box6(kd, (hx_, yd - 0.013, zd0), (x1_, yf_, zd1), Z_DCAB)
    for zz in np.arange(zd0 + 0.25, zd0 + 0.60, 0.05):
        kd.box(hx_ + 0.20, x1_ - 0.20, yf_, yf_ + 0.009, zz, zz + 0.022, Z_DCAB)
    kd.box(x1_ - 0.10, x1_ - 0.06, yf_, yf_ + 0.03, 1.00, 1.16, Z_DBOLT)
    kd.cyl(V(x1_ - 0.08, yf_ - 0.001, 1.25), V(x1_ - 0.08, yf_ + 0.012, 1.25), 0.018, Z_DBOLT, 8)
    for zz in (zd0 + 0.18, zd1 - 0.18):
        kd.cyl(V(hx_ - 0.012, yd + 0.02, zz - 0.06), V(hx_ - 0.012, yd + 0.02, zz + 0.06), 0.012, Z_DBOLT, 6)
    part(g_door(name), 'hinge', (hx_, yd, zd0), axis=(0, 0, 1), rng=(0, 110), parent=name,
         note='the cabinet door: Update 3\'s hinge (vertical at x 3.65), opens out (+y, towards the pedestal) up to 110 deg')


def g_door(name):
    return S.DISHES[name]['door']


# ================================================================ shared: the equipment shelter, the chain-link compound
def shelter(k, kf, box, roof, door, ac, zw, zr, zd, zac, zconc, zb, sign_region=None, sign_name=None, door_axis='+x'):
    """a prefabricated equipment shelter: corrugated walls (painted), a roof plate with an overhang, two footing strips,
    the door on the +x end with its frame, handle and hinges, a step, the air conditioner on the roof, a cable gland box
    on the -x end"""
    x0, x1, y0, y1, h = box
    for yy in (y0 + 0.3, y1 - 0.3):                                      # footing strips
        chamfer_box(k, (x0 - 0.1, yy - 0.2, -0.3), (x1 + 0.1, yy + 0.2, 0.05), 0.02, zconc)
    box6(k, (x0, y0, 0.05), (x1, y1, h), zw, skip=('-z',))
    rx0, rx1, ry0, ry1, rz0, rz1 = roof
    box6(k, (rx0, ry0, rz0), (rx1, ry1, rz1), zr)
    dx, dy0, dy1, dz0, dz1 = door                                        # the door: proud of the +x end
    box6(k, (x1, dy0 - 0.05, dz0 - 0.03), (x1 + 0.02, dy1 + 0.05, dz1 + 0.05), zb)        # the frame
    box6(k, (x1 + 0.02, dy0, dz0), (x1 + 0.05, dy1, dz1), zd)
    k.box(x1 + 0.05, x1 + 0.08, dy1 - 0.12, dy1 - 0.08, 1.00, 1.18, zb)                      # the handle
    k.cyl(V(x1 + 0.05, dy1 - 0.10, 1.26), V(x1 + 0.07, dy1 - 0.10, 1.26), 0.02, zb, 8)        # the lock
    for zz in (dz0 + 0.25, dz1 - 0.25):
        k.cyl(V(x1 + 0.05, dy0 - 0.012, zz - 0.07), V(x1 + 0.05, dy0 - 0.012, zz + 0.07), 0.014, zb, 6)
    box6(k, (x1 + 0.05, dy0 - 0.05, 0.0), (x1 + 0.45, dy1 + 0.05, 0.18), zb)                 # the step (grating)
    if kf is not None and sign_region is not None:                       # the sign on the door (faces +x)
        sz, sw, sh_ = 1.62, 0.60, 0.36
        cy = (dy0 + dy1) / 2
        ol = rrect_xz(-sw / 2, sw / 2, sz - sh_ / 2, sz + sh_ / 2, 0.015, 2)
        u0, v0, u1, v1 = sign_region
        pts = [V(x1 + 0.056, cy - xx, zz) for xx, zz in ol]
        uvs = [(u0 + (xx + sw / 2) / sw * (u1 - u0), v0 + (zz - (sz - sh_ / 2)) / sh_ * (v1 - v0)) for xx, zz in ol]
        face(kf, pts, 0.0, (1, 0, 0), uvs)
    ax0, ax1, ay0, ay1, az0, az1 = ac                                    # the air conditioner, its fan grille
    box6(k, (ax0, ay0, rz1), (ax1, ay1, az0), zb)
    box6(k, (ax0, ay0, az0), (ax1, ay1, az1), zac)
    k.cyl(V((ax0 + ax1) / 2, (ay0 + ay1) / 2, az1), V((ax0 + ax1) / 2, (ay0 + ay1) / 2, az1 + 0.02), 0.36, zb, 16)
    box6(k, (x0 - 0.12, -0.25, 1.9), (x0, 0.25, 2.35), zb)                                    # the cable gland box


def chainlink_run(k, km, kbw, pts, outward, zp, zr, post_every=3.2, h=2.2, top=2.3, gates=()):
    """a chain-link fence along a polyline: posts at the corners and every ~post_every, a top rail, the chain-link
    (km, two-sided, 0.5 m per tile), three barbed strands on outriggers leaning outward (kbw, the base's 0.52 m band);
    gates: (index of the segment, (s0, s1) along it) left open in the mesh"""
    for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
        a, b = V(a[0], a[1], 0.0), V(b[0], b[1], 0.0)
        L = (b - a).length
        d = (b - a).normalized()
        n = max(1, round(L / post_every))
        o = V(outward[i])
        holes = [g[1] for g in gates if g[0] == i]
        for j in range(n + 1):
            p = a.lerp(b, j / n)
            if j == n and i < len(pts) - 2:
                continue                                                 # the next segment's first post
            rod(k, (p.x, p.y, -0.4), (p.x, p.y, top - 0.012), 0.035, zp, seg=6, caps=False)
            k.cyl(V(p.x, p.y, top - 0.012), V(p.x, p.y, top + 0.008), 0.041, zp, 6)
            arm_top = p + o * 0.36 + V(0, 0, top + 0.36)
            bar(k, V(p.x, p.y, top - 0.03), arm_top, 0.030, 0.006, zp, up=V(d.x, d.y, 0), caps=False)
        spans = [(0.0, L)]
        for s0, s1 in holes:
            new = []
            for c0, c1 in spans:
                if s1 <= c0 or s0 >= c1:
                    new.append((c0, c1))
                else:
                    if s0 > c0:
                        new.append((c0, s0))
                    if s1 < c1:
                        new.append((s1, c1))
            spans = new
        for c0, c1 in spans:
            p0, p1 = a + d * c0, a + d * c1
            rod(k, (p0.x, p0.y, h), (p1.x, p1.y, h), 0.021, zr, seg=6, caps=False)
            q = [V(p0.x, p0.y, 0.03), V(p1.x, p1.y, 0.03), V(p1.x, p1.y, h), V(p0.x, p0.y, h)]
            us = [(c0 / 0.5, 0.06), (c1 / 0.5, 0.06), (c1 / 0.5, h / 0.5), (c0 / 0.5, h / 0.5)]
            km.poly(q, 0.0, us)
            km.poly(list(reversed(q)), 0.0, list(reversed(us)))
            e = (o * 0.36 + V(0, 0, 0.36)).normalized()
            b0, b1 = V(0, 0, top) - e * 0.01, V(0, 0, top) + e * 0.51
            q = [V(p0.x, p0.y, 0) + b0, V(p1.x, p1.y, 0) + b0, V(p1.x, p1.y, 0) + b1, V(p0.x, p0.y, 0) + b1]
            us = [(c0 / 0.5, 0.0), (c1 / 0.5, 0.0), (c1 / 0.5, 1.0), (c0 / 0.5, 1.0)]
            kbw.poly(q, 0.0, us)
            kbw.poly(list(reversed(q)), 0.0, list(reversed(us)))


def caged_ladder(k, x, face_y, z0, z1, zone, cage_from=2.5, w=0.20):
    """a fixed ladder on a tower face (face_y(z) -> the face's y, the ladder 0.15 out in -y), its safety cage"""
    yl = lambda z: face_y(z) - 0.15
    zs = list(np.arange(z0, z1 + 1e-6, 3.0)) + ([z1] if (z1 - z0) % 3.0 > 1e-6 else [])
    for xr in (x - w, x + w):
        for za, zb in zip(zs[:-1], zs[1:]):
            k.strip([V(xr, yl(za), za), V(xr, yl(zb), zb)], V(1, 0, 0), 0.05, 0.012, zone, caps=True)
    for z in np.arange(z0 + 0.25, z1 - 0.1, 0.30):
        rod(k, (x - w, yl(z), z), (x + w, yl(z), z), 0.013, zone, seg=6, caps=False)
    for z in np.arange(z0 + 1.5, z1, 3.0):
        for xr in (x - w, x + w):
            bar(k, (xr, yl(z) + 0.02, z), (xr, face_y(z), z), 0.04, 0.008, zone)
    hoops = list(np.arange(cage_from, z1 - 0.3, 0.9))
    for z in hoops:
        c = V(x, yl(z), z)
        ring = [c + V(-w - 0.02, 0.05, 0)] + [c + V(math.cos(t) * 0.36, -0.36 * math.sin(t) - 0.0, 0) * 1.0 + V(0, -0.05, 0)
                                               for t in np.linspace(math.pi, 0, 7)] + [c + V(w + 0.02, 0.05, 0)]
        k.strip(ring, V(0, 0, 1), 0.04, 0.008, zone, caps=True)
    for t in np.linspace(math.pi * 0.85, math.pi * 0.15, 5):
        pts = [V(x + math.cos(t) * 0.36, yl(z) - 0.36 * math.sin(t) - 0.05, z) for z in (hoops[0], hoops[-1])]
        for za, zb in zip(np.arange(0, 1, 0.25), np.arange(0.25, 1.01, 0.25)):
            k.strip([pts[0].lerp(pts[1], za), pts[0].lerp(pts[1], zb)], V(math.cos(t), -math.sin(t), 0), 0.04, 0.008, zone,
                    caps=True)


# ================================================================ the radome
def radome():
    r = S.RADOME
    k = kb('Radome', 'Towers')
    corners = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
    corner = lambda z, i: V(corners[i][0] * S.radome_c(z), corners[i][1] * S.radome_c(z), z)
    for i, (xs, ys) in enumerate(corners):                               # footings, base plates, bolts
        cx, cy = xs * r['foot'], ys * r['foot']
        fh = r['footing'] / 2
        chamfer_box(k, (cx - fh, cy - fh, -1.0), (cx + fh, cy + fh, 0.10), 0.04, Z_TFOOT)
        k.box(cx - 0.20, cx + 0.20, cy - 0.20, cy + 0.20, 0.10, 0.125, Z_TPLATE)
        for dx in (-0.14, 0.14):
            for dy in (-0.14, 0.14):
                bolt(k, (cx + dx, cy + dy, 0.125), (0, 0, 1), 0.018, 0.016, Z_TSTEEL, washer=0.026)
    zs = [0.125, 4.0, 8.0, 12.0, r['h']]
    lattice(k, corner, zs, Z_TLEG, Z_TBRACE, lambda z: 0.085, 0.035, xbrace=True)
    for z in zs[1:-1]:                                                   # gusset plates at the nodes
        for i in range(4):
            c = corner(z, i)
            k.box_m(c, (0.22, 0.22, 0.10), Z_TPLATE)
    caged_ladder(k, r['ladder_x'], lambda z: -S.radome_c(z), 0.2, r['deck'][0], Z_TLADDER)
    # the deck: perimeter and cross girders, the slab; the hatch over the ladder; the radome's ring
    d0, d1 = r['deck']
    hw = r['deck_half']
    for a_, b_ in ((hw - 0.25, hw), (-hw, -hw + 0.25)):                # the perimeter girders
        box6(k, (a_, -hw, d0), (b_, hw, d0 + 0.55), Z_TGIRDER)
        box6(k, (-hw + 0.25, a_, d0), (hw - 0.25, b_, d0 + 0.55), Z_TGIRDER)
    for xx in (-1.3, 1.3):
        box6(k, (xx - 0.12, -hw + 0.25, d0 + 0.05), (xx + 0.12, hw - 0.25, d0 + 0.55), Z_TGIRDER)
    box6(k, (-hw, -hw, d0 + 0.55), (hw, hw, d1), Z_TDECK)
    lx = r['ladder_x']
    k.box(lx - 0.35, lx + 0.35, -S.radome_c(d0) - 0.55, -S.radome_c(d0) + 0.15, d0 + 0.53, d0 + 0.56, Z_TPLATE)  # the hatch
    k.lathe(V(0, 0, d1), (0, 0, 1), [(0.0, 3.76), (0.15, 3.76), (0.15, 3.70)], Z_TDOMERING, 32, cap0=False, cap1=False)
    for a in range(24):
        q = TAU * (a + 0.5) / 24
        bolt(k, (3.73 * math.cos(q), 3.73 * math.sin(q), d1 + 0.15), (0, 0, 1), 0.02, 0.016, Z_TSTEEL)
    # the radome: a sphere of panels from the ring up to the beacon's plate
    c = V(0, 0, r['dome_c'])
    R = r['dome_r']
    th0 = math.acos((d1 + 0.15 - c.z) / R)                              # the polar angle at the ring
    th1 = math.asin(0.39 / R)
    rings = []
    for th in np.linspace(th0, th1, 9):
        rings.append([c + V(R * math.sin(th) * math.cos(TAU * j / 24), R * math.sin(th) * math.sin(TAU * j / 24),
                            R * math.cos(th)) for j in range(24)])
    k.loft(rings, [Z_TDOME] * 8)
    face(k, rings[-1], Z_TDOME, (0, 0, 1))
    k.lathe(V(0, 0, r['beacon_base']), (0, 0, 1), [(0.0, 0.39), (0.14, 0.39), (0.14, 0.33)], Z_TBEACB, 16, cap0=False,
            cap1=True)
    kl = kb('Radome_Beacon', 'lens:red')
    kl.lathe(V(0, 0, r['beacon_base'] + 0.14), (0, 0, 1), [(0.0, 0.33), (0.18, 0.30), (0.33, 0.18), (0.408, 0.0)], 0.0, 16,
             cap0=False, cap1=False)
    # the shelter, the cable bridge to the tower and up its +x face to the deck
    kf = kb('Radome_Sign', 'panel')
    shelter(k, kf, r['hut'], r['hut_roof'], r['hut_door'], r['ac'], Z_THUT, Z_THUTROOF, Z_THUTDOOR, Z_TAC, Z_TCONC, Z_TSTEEL,
            sign_region=uv('radome'))
    bx0, bx1 = S.radome_c(2.4) + 0.10, r['hut'][0] - 0.12
    k.strip([V(bx0, 0.0, 2.40), V(bx1, 0.0, 2.40)], V(0, 0, 1), 0.30, 0.04, Z_TBRIDGE, caps=True)
    for xx in np.arange(bx0 + 1.2, bx1 - 0.5, 2.4):
        rod(k, (xx, 0.0, -0.3), (xx, 0.0, 2.38), 0.04, Z_TBRIDGE, seg=6, caps=False)
    for dy in (-0.08, 0.0, 0.08):
        k.tube([V(bx1 - 0.05, dy, 2.45), V(bx0 + 0.1, dy, 2.45)], 0.016, Z_TCABLE, 5, caps=False)
    zz_ = list(np.arange(2.4, d0 + 1e-6, 3.0)) + [d0]
    for za, zb in zip(zz_[:-1], zz_[1:]):
        k.strip([V(S.radome_c(za) + 0.10, 0.0, za), V(S.radome_c(zb) + 0.10, 0.0, zb)], V(1, 0, 0), 0.30, 0.03, Z_TBRIDGE,
                caps=False)
        for dy in (-0.08, 0.0, 0.08):
            k.tube([V(S.radome_c(za) + 0.13, dy, za), V(S.radome_c(zb) + 0.13, dy, zb)], 0.016, Z_TCABLE, 5, caps=False)
    part('Radome', 'static', (0, 0, 0), note='16 m lattice tower with a caged ladder, the deck, the radome, the beacon, the '
                                             'equipment shelter, the cable bridge')
    part('Radome_Beacon', 'static', (0, 0, r['beacon_base'] + 0.3), parent='Radome',
         note='the beacon\'s dome (Update 3\'s M_Light_Red; the light and halo at Update 3\'s 26.22)')
    part('Radome_Sign', 'static', (r['hut'][1] + 0.06, 1.4, 1.62), parent='Radome', note='the shelter door\'s sign (panel)')


# ================================================================ the relay mast
def relaymast():
    m = S.RELAY
    k = kb('RelayMast', 'Towers')
    corners = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
    corner = lambda z, i: V(corners[i][0] * S.relay_c(z), corners[i][1] * S.relay_c(z), z)
    for i, (xs, ys) in enumerate(corners):
        cx, cy = xs * m['footings'], ys * m['footings']
        fh = m['footing'] / 2
        chamfer_box(k, (cx - fh, cy - fh, -1.0), (cx + fh, cy + fh, 0.10), 0.04, Z_TFOOT)
        b = corner(0.10, i)
        k.box(b.x - 0.18, b.x + 0.18, b.y - 0.18, b.y + 0.18, 0.10, 0.125, Z_TPLATE)
        for dx in (-0.12, 0.12):
            for dy in (-0.12, 0.12):
                bolt(k, (b.x + dx, b.y + dy, 0.125), (0, 0, 1), 0.016, 0.014, Z_TSTEEL, washer=0.024)
    zs = [0.125] + list(np.arange(m['bay'], m['h'] + 1e-6, m['bay']))
    lattice(k, corner, zs, Z_TRLEG, Z_TRBRACE, lambda z: 0.075 - 0.025 * z / m['h'], 0.026)
    c = S.relay_c(m['h'])
    box6(k, (-c - 0.08, -c - 0.08, m['h']), (c + 0.08, c + 0.08, m['h'] + 0.02), Z_TPLATE)
    bt0, bt1 = m['beacon_top']
    k.lathe(V(0, 0, bt0), (0, 0, 1), [(0.0, 0.345), (0.14, 0.345), (0.14, 0.30)], Z_TBEACB, 16, cap0=True, cap1=True)
    kl = kb('RelayMast_Beacon', 'lens:red')
    kl.lathe(V(0, 0, bt0 + 0.14), (0, 0, 1), [(0.0, 0.30), (0.14, 0.28), (0.28, 0.16), (bt1 - bt0 - 0.14, 0.0)], 0.0, 16,
             cap0=False, cap1=False)
    zb = m['beacons_mid']
    for xs, ys in ((1, -1), (-1, 1)):                                    # the mid beacons on brackets (Update 3's places)
        base = V(xs * S.relay_c(zb), ys * S.relay_c(zb), zb)
        tip = V(xs * m['beacon_mid_xy'], ys * m['beacon_mid_xy'], zb)
        bar(k, base - V(0, 0, 0.04), tip - V(0, 0, 0.04), 0.06, 0.05, Z_TPLATE)
        bar(k, base - V(0, 0, 0.45), tip - V(0, 0, 0.07), 0.03, 0.03, Z_TPLATE)
        k.lathe(V(tip.x, tip.y, zb - 0.02), (0, 0, 1), [(0.0, 0.25), (0.16, 0.25), (0.16, 0.21)], Z_TBEACB, 12, cap0=True,
                cap1=True)
        kl.lathe(V(tip.x, tip.y, zb + 0.14), (0, 0, 1), [(0.0, 0.21), (0.10, 0.19), (0.20, 0.11), (0.26, 0.0)], 0.0, 12,
                 cap0=False, cap1=False)
    # the microwave drum on the +x face (Update 3's: 31.5 m), its mount pipe and struts
    dr = m['drum']
    cz = S.relay_c(dr['z'])
    px = cz + 0.15
    rod(k, (px, 0.0, dr['z'] - 0.9), (px, 0.0, dr['z'] + 0.9), 0.045, Z_TPLATE, seg=8)
    for zz in (dr['z'] - 0.7, dr['z'] + 0.7):
        bar(k, V(cz, 0.0, zz), V(px, 0.0, zz), 0.10, 0.02, Z_TPLATE, up=(0, 0, 1))
    k.lathe(V(dr['x'], 0.0, dr['z']), (1, 0, 0), [(0.0, 0.0), (0.0, dr['r'] - 0.05), (0.06, dr['r']), (0.45, dr['r'])],
            Z_TDRUM, 20, cap0=False, cap1=False)
    k.lathe(V(dr['x'] + 0.45, 0.0, dr['z']), (1, 0, 0), [(0.0, dr['r'] + 0.012), (0.03, dr['r'] + 0.012), (0.06, dr['r'] - 0.02),
                                                         (0.11, 0.0)], Z_TDRUM, 20, cap0=False, cap1=False)
    for sy in (-1, 1):
        rod(k, V(dr['x'] + 0.05, sy * 0.45, dr['z'] - 0.3), V(cz, sy * 0.35, dr['z'] - 1.2), 0.025, Z_TPLATE, seg=6)
    # three panel antennas on pipes near the top, their jumpers
    pa = m['panels']
    for i in range(3):
        a = TAU * i / 3
        dirn = V(math.cos(a), math.sin(a), 0)
        side = V(-dirn.y, dirn.x, 0)
        pc = dirn * pa['r']
        rod(k, pc - dirn * 0.10 + V(0, 0, pa['z'][0] - 0.25), pc - dirn * 0.10 + V(0, 0, pa['z'][1] + 0.15), 0.035, Z_TPLATE, seg=8)
        Rp = Matrix((side, dirn, V(0, 0, 1))).transposed()
        obox(k, pc + dirn * (pa['d'] / 2) + V(0, 0, (pa['z'][0] + pa['z'][1]) / 2), (pa['w'], pa['d'], pa['z'][1] - pa['z'][0]),
             Z_TPANEL, Rp)
        for zz in (pa['z'][0] + 0.3, pa['z'][1] - 0.3):
            bar(k, pc - dirn * 0.10 + V(0, 0, zz), dirn * S.relay_c(zz) * 0.95 + V(0, 0, zz), 0.05, 0.02, Z_TPLATE, up=(0, 0, 1))
        k.tube([pc + dirn * 0.04 + V(0, 0, pa['z'][0]), pc + dirn * 0.0 + V(0, 0, pa['z'][0] - 0.35),
                dirn * 0.25 + V(0, 0, pa['z'][0] - 1.2)], 0.012, Z_TCABLE, 5, caps=False)
    # the feeders down the mast's centre on a cable ladder, out to the shelter on the bridge
    zz_ = list(np.arange(1.0, pa['z'][0] - 1.2 + 1e-6, 3.0))
    for za, zb_ in zip(zz_[:-1], zz_[1:]):
        k.strip([V(0.25, 0.0, za), V(0.25, 0.0, zb_)], V(1, 0, 0), 0.30, 0.03, Z_TBRIDGE, caps=False)
        for dy in (-0.09, -0.03, 0.03, 0.09):
            k.tube([V(0.28, dy, za), V(0.28, dy, zb_)], 0.014, Z_TCABLE, 5, caps=False)
    for zz in np.arange(2.5, pa['z'][0] - 1.5, 3.5):                     # its brackets to the horizontals
        c_ = S.relay_c(zz)
        bar(k, V(0.25, 0.0, zz), V(c_, 0.0, zz), 0.05, 0.02, Z_TPLATE, up=(0, 0, 1))
    bx0, bx1 = 0.25, m['hut'][0] - 0.12
    k.strip([V(bx0, 0.0, 2.4), V(bx1, 0.0, 2.4)], V(0, 0, 1), 0.30, 0.04, Z_TBRIDGE, caps=True)
    for xx in (2.6, 4.2):
        rod(k, (xx, 0.0, -0.3), (xx, 0.0, 2.38), 0.04, Z_TBRIDGE, seg=6, caps=False)
    for dy in (-0.09, -0.03, 0.03, 0.09):
        k.tube([V(0.28, dy, 1.0), V(0.30, dy, 2.2), V(0.6, dy, 2.46), V(bx1 - 0.05, dy, 2.46)], 0.014, Z_TCABLE, 5, caps=False)
    caged_ladder(k, -0.7, lambda z: -S.relay_c(z), 0.2, m['h'] - 0.5, Z_TLADDER)
    # the shelter, the compound's fence with its double gate and the sign
    kf = kb('RelayMast_Sign', 'panel')
    shelter(k, None, m['hut'], m['hut_roof'], m['hut_door'], m['ac'], Z_THUT, Z_THUTROOF, Z_THUTDOOR, Z_TAC, Z_TCONC, Z_TSTEEL)
    fx0, fx1 = m['fence']['x']
    fy0, fy1 = m['fence']['y']
    km = kb('RelayMast_Mesh', 'chainlink')
    kbw = kb('RelayMast_Barbed', 'barbed')
    g0, g1 = -1.5, 1.5                                                    # the double gate in the -x side
    chainlink_run(k, km, kbw, [(fx0, g0), (fx0, fy0), (fx1, fy0), (fx1, fy1), (fx0, fy1), (fx0, g1)],
                  [(-1, 0, 0), (0, -1, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0)], Z_TFPOST, Z_TFPOST)
    for gy in (g0, g1):                                                  # the gate posts (heavier)
        rod(k, (fx0, gy, -0.5), (fx0, gy, 2.35), 0.05, Z_TFPOST, seg=8, caps=False)
        k.cyl(V(fx0, gy, 2.35), V(fx0, gy, 2.37), 0.056, Z_TFPOST, 8)
    for sg, gy in ((1, g0), (-1, g1)):                                   # the leaves: tube frames with chain-link
        y_a, y_b = gy + sg * 0.06, -sg * 0.025
        for zz in (0.12, 2.05):
            rod(k, (fx0, y_a, zz), (fx0, y_b, zz), 0.024, Z_TFPOST, seg=6, caps=True)
        for yy in (y_a, y_b):
            rod(k, (fx0, yy, 0.12), (fx0, yy, 2.05), 0.024, Z_TFPOST, seg=6, caps=True)
        rod(k, (fx0, y_a, 0.15), (fx0, y_b, 2.02), 0.018, Z_TFPOST, seg=6, caps=True)
        q = [V(fx0, y_a, 0.12), V(fx0, y_b, 0.12), V(fx0, y_b, 2.05), V(fx0, y_a, 2.05)]
        us = [(y_a / 0.5, 0.24), (y_b / 0.5, 0.24), (y_b / 0.5, 4.1), (y_a / 0.5, 4.1)]
        km.poly(q, 0.0, us)
        km.poly(list(reversed(q)), 0.0, list(reversed(us)))
        for zz in (0.4, 1.7):
            k.cyl(V(fx0, gy + sg * 0.05, zz - 0.06), V(fx0, gy + sg * 0.05, zz + 0.06), 0.03, Z_TSTEEL, 8)
    k.tube([V(fx0 - 0.03, -0.06, 1.15), V(fx0 - 0.05, 0.0, 1.05), V(fx0 - 0.03, 0.06, 1.15)], 0.007, Z_TSTEEL, 5)   # the chain
    VM.rbox(k, V(fx0 - 0.06, 0.0, 1.0), (0.025, 0.06, 0.05), Z_TSTEEL, r=0.006, ch=0.003)                          # the padlock
    sg_ = m['sign']
    cy_ = -0.75
    ol = rrect_xz(-sg_['w'] / 2, sg_['w'] / 2, sg_['z'] - sg_['h'] / 2, sg_['z'] + sg_['h'] / 2, 0.012, 2)
    u0, v0, u1, v1 = uv('relay')
    pts = [V(fx0 - 0.035, cy_ - xx, zz) for xx, zz in ol]
    face(kf, pts, 0.0, (-1, 0, 0), [(u0 + (xx + sg_['w'] / 2) / sg_['w'] * (u1 - u0),
                                     v0 + (zz - (sg_['z'] - sg_['h'] / 2)) / sg_['h'] * (v1 - v0)) for xx, zz in ol])
    bk = [V(fx0 - 0.025, cy_ - xx, zz) for xx, zz in ol]
    face(k, bk, Z_TSBACK, (1, 0, 0))
    for i in range(len(ol)):
        j = (i + 1) % len(ol)
        face(k, [pts[i], pts[j], bk[j], bk[i]], Z_TSBACK, V(0, -(ol[i][0] + ol[j][0]) / 2, ((ol[i][1] + ol[j][1]) / 2) - sg_['z']))
    part('RelayMast', 'static', (0, 0, 0), note='42 m lattice mast, beacons, microwave drum, panel antennas, feeders, the '
                                                'shelter, the fenced compound with its gate')
    part('RelayMast_Beacon', 'static', (0, 0, 42.3), parent='RelayMast',
         note='the beacons\' domes (Update 3\'s M_Light_Red; the lights and halos at Update 3\'s 21.29 / 42.37)')
    part('RelayMast_Sign', 'static', (fx0 - 0.035, cy_, sg_['z']), parent='RelayMast', note='the gate\'s sign (panel)')
    part('RelayMast_Mesh', 'static', (0, 0, 1.1), parent='RelayMast', note='chain-link (M_Base_ChainLink, cut-out)')
    part('RelayMast_Barbed', 'static', (0, 0, 2.5), parent='RelayMast', note='barbed strands (M_Base_Barbed, cut-out)')


# ================================================================ the weather station
def meteostation():
    mt = S.METEO
    k = kb('MeteoStation', 'Meteo')
    F_ = mt['fence']
    hgt = mt['fence_h']
    # the picket fence: posts every 2 m, two rails, pointed pickets every 0.16 m; the gate in the -y side
    sides = [((-F_, -F_), (F_, -F_), (0, -1)), ((F_, -F_), (F_, F_), (1, 0)), ((F_, F_), (-F_, F_), (0, 1)),
             ((-F_, F_), (-F_, -F_), (-1, 0))]
    g0, g1 = mt['gate']
    for si, (a, b, o) in enumerate(sides):
        a, b, o = V(a[0], a[1], 0), V(b[0], b[1], 0), V(o[0], o[1], 0)
        d = (b - a).normalized()
        L = (b - a).length
        for j in range(7):                                               # posts
            p = a + d * (L * j / 6)
            if j == 6:
                continue
            Rp = Matrix((d, o, V(0, 0, 1))).transposed()
            obox(k, p + V(0, 0, (hgt + 0.10 - 0.40) / 2), (0.08, 0.08, hgt + 0.10 + 0.40), Z_MPOST, Rp)
            for e_, f_ in ((o, d), (-o, d), (d, o), (-d, o)):                # the pyramid cap: four faces, each outward
                q_ = [p + e_ * 0.04 + f_ * 0.04 + V(0, 0, hgt + 0.10), p + e_ * 0.04 - f_ * 0.04 + V(0, 0, hgt + 0.10),
                      p + V(0, 0, hgt + 0.16)]
                face(k, q_, Z_MPOST, e_ + V(0, 0, 0.5))
        spans = [(0.04, L - 0.04)]
        if si == 0:                                                      # the gate opening
            spans = [(0.04, (g0 + F_) - 0.06), ((g1 + F_) + 0.06, L - 0.04)]
        for c0, c1 in spans:
            for zr in (0.20, 0.70):                                      # the rails (on the inside)
                Rp = Matrix((d, o, V(0, 0, 1))).transposed()
                obox(k, a + d * ((c0 + c1) / 2) - o * 0.065 + V(0, 0, zr), (c1 - c0, 0.05, 0.08), Z_MRAIL, Rp)
            for sp in np.arange(c0 + 0.06, c1 - 0.03, mt['pitch']):     # the pickets (on the outside of the rails)
                p = a + d * sp - o * 0.03
                w2 = mt['picket'] / 2
                q0 = [p - d * w2 - o * 0.01 + V(0, 0, 0.03), p + d * w2 - o * 0.01 + V(0, 0, 0.03),
                      p + d * w2 + o * 0.01 + V(0, 0, 0.03), p - d * w2 + o * 0.01 + V(0, 0, 0.03)]
                q1 = [x + V(0, 0, hgt - 0.08) for x in q0]
                k.loft([_orient(q0, V(0, 0, 1)), _orient(q1, V(0, 0, 1))], [Z_MPICKET])
                tp = p + V(0, 0, hgt)
                tq = _orient(q1, V(0, 0, 1))
                for i_ in range(4):
                    face(k, [tq[i_], tq[(i_ + 1) % 4], tp], Z_MPICKET, ((tq[i_] + tq[(i_ + 1) % 4]) / 2 - p).to_2d().to_3d())
    # the gate: a picket leaf on two strap hinges, the latch
    ga, gb = V(g0 + 0.05, -F_, 0), V(g1 - 0.05, -F_, 0)
    d = V(1, 0, 0)
    o = V(0, -1, 0)
    Rp = Matrix((d, o, V(0, 0, 1))).transposed()
    for zr in (0.20, 0.70):
        obox(k, (ga + gb) / 2 - o * 0.065 + V(0, 0, zr), ((gb - ga).length, 0.05, 0.08), Z_MRAIL, Rp)
    obox(k, (ga + gb) / 2 - o * 0.065 + V(0, 0, 0.45), (((gb - ga).length ** 2 + 0.5 ** 2) ** 0.5, 0.04, 0.07), Z_MRAIL,
         Rp @ Matrix.Rotation(math.atan2(0.5, (gb - ga).length), 3, 'Y'))
    for sp in np.arange(0.06, (gb - ga).length - 0.03, mt['pitch']):
        p = ga + d * sp - o * 0.03
        q0 = [p - d * 0.04 - o * 0.01 + V(0, 0, 0.06), p + d * 0.04 - o * 0.01 + V(0, 0, 0.06), p + d * 0.04 + o * 0.01 + V(0, 0, 0.06),
              p - d * 0.04 + o * 0.01 + V(0, 0, 0.06)]
        q1 = [x + V(0, 0, hgt - 0.11) for x in q0]
        k.loft([_orient(q0, V(0, 0, 1)), _orient(q1, V(0, 0, 1))], [Z_MPICKET])
        tq = _orient(q1, V(0, 0, 1))
        tp = p + V(0, 0, hgt - 0.03)
        for i_ in range(4):
            face(k, [tq[i_], tq[(i_ + 1) % 4], tp], Z_MPICKET, ((tq[i_] + tq[(i_ + 1) % 4]) / 2 - p).to_2d().to_3d())
    for zr in (0.20, 0.70):
        k.box(ga.x - 0.04, ga.x + 0.20, -F_ + 0.05, -F_ + 0.09, zr - 0.02, zr + 0.02, Z_MINSTR)
    k.box(gb.x - 0.06, gb.x + 0.06, -F_ + 0.03, -F_ + 0.05, 0.62, 0.68, Z_MINSTR)
    # the sign on the gate (faces -y)
    kf = kb('MeteoStation_Sign', 'panel')
    sign_plate(k, kf, (0.0, -F_ - 0.03, 0.55), 0.72, 0.26, uv('meteo'), zone=Z_MSBACK)
    # the screen: four legs braced, the louvred box, the double roof, the door to the north, a step
    sc_ = mt['screen']
    lx, ly = sc_['legs']
    for xs in (-1, 1):
        for ys in (-1, 1):
            k.box(xs * lx - 0.03, xs * lx + 0.03, ys * ly - 0.03, ys * ly + 0.03, -0.3, sc_['leg_top'], Z_MLEG)
        k.box(xs * lx - 0.02, xs * lx + 0.02, -ly, ly, 0.45, 0.50, Z_MLEG)
    bw, bd, bz0, bz1 = sc_['box']
    box6(k, (-bw / 2 + 0.03, -bd / 2 + 0.03, bz0), (bw / 2 - 0.03, bd / 2 - 0.03, bz1), Z_MSCREEN)
    for xs in (-1, 1):                                                   # the corner posts
        for ys in (-1, 1):
            xa, xb = (bw / 2 - 0.03, bw / 2) if xs > 0 else (-bw / 2, -bw / 2 + 0.03)
            ya, yb = (bd / 2 - 0.03, bd / 2) if ys > 0 else (-bd / 2, -bd / 2 + 0.03)
            k.box(xa, xb, ya, yb, bz0, bz1, Z_MSCREEN)
    for side, (n_, t_, L_) in enumerate((((0, -1, 0), (1, 0, 0), bw), ((0, 1, 0), (1, 0, 0), bw), ((1, 0, 0), (0, 1, 0), bd),
                                         ((-1, 0, 0), (0, 1, 0), bd))):
        n_, t_ = V(n_), V(t_)
        base = n_ * ((bd if abs(n_.y) > 0 else bw) / 2 - 0.035)
        for zz in np.arange(bz0 + 0.06, bz1 - 0.04, 0.075):              # the louvres: slats at 45 deg
            c = base + V(0, 0, zz)
            Rl = Matrix((t_, n_, V(0, 0, 1))).transposed() @ Matrix.Rotation(math.radians(45), 3, 'X')
            obox(k, c, (L_ - 0.07, 0.06, 0.008), Z_MLOUVRE, Rl)
    rw, rd, rz0, rz1 = sc_['roof']
    box6(k, (-rw / 2, -rd / 2, rz0), (rw / 2, rd / 2, rz1), Z_MSCREEN)
    for xs in (-1, 1):
        for ys in (-1, 1):
            k.box(xs * 0.30 - 0.015, xs * 0.30 + 0.015, ys * 0.24 - 0.015, ys * 0.24 + 0.015, bz1, rz0, Z_MSCREEN)
    rz2 = rz1 + 0.05
    box6(k, (-rw / 2 - 0.03, -rd / 2 - 0.03, rz2), (rw / 2 + 0.03, rd / 2 + 0.03, rz2 + 0.03), Z_MSCREEN)
    for xs in (-1, 1):
        for ys in (-1, 1):
            k.box(xs * 0.36 - 0.015, xs * 0.36 + 0.015, ys * 0.28 - 0.015, ys * 0.28 + 0.015, rz1, rz2, Z_MSCREEN)
    for zz in (bz0 + 0.12, bz1 - 0.12):                                  # the door's hinges and the turn button (+y)
        k.box(-bw / 2 + 0.06, -bw / 2 + 0.14, bd / 2 - 0.035, bd / 2 - 0.02, zz - 0.02, zz + 0.02, Z_MINSTR)
    k.box(bw / 2 - 0.10, bw / 2 - 0.06, bd / 2 - 0.035, bd / 2 - 0.015, (bz0 + bz1) / 2 - 0.02, (bz0 + bz1) / 2 + 0.02, Z_MINSTR)
    box6(k, (-0.25, bd / 2 + 0.25, 0.0), (0.25, bd / 2 + 0.55, 0.30), Z_MLEG)                     # the step (+y side)
    # the wind mast (guyed), the cross arm, the cup anemometer, the vane
    mx, my, mh = mt['mast']
    chamfer_box(k, (mx - 0.25, my - 0.25, -0.5), (mx + 0.25, my + 0.25, 0.08), 0.02, Z_MCONC)
    k.box(mx - 0.10, mx + 0.10, my - 0.10, my + 0.10, 0.08, 0.10, Z_MINSTR)
    zz_ = list(np.arange(0.10, mh - 0.5, 2.0)) + [mh]                   # in ~2 m lengths, up to the top
    for za, zb in zip(zz_[:-1], zz_[1:]):
        rod(k, (mx, my, za), (mx, my, zb), 0.045 - 0.012 * za / mh, Z_MMAST, seg=8, caps=False)
    k.lathe(V(mx, my, mh), (0, 0, 1), [(0.0, 0.034), (0.03, 0.034), (0.04, 0.0)], Z_MMAST, 8, cap0=False)
    va, vb, vz = mt['vane']
    rod(k, (va, my, vz), (vb, my, vz), 0.02, Z_MINSTR, seg=6)
    k.box(mx - 0.05, mx + 0.05, my - 0.05, my + 0.05, vz - 0.06, vz + 0.04, Z_MINSTR)
    cx_ = vb - 0.08                                                      # the cups
    rod(k, (cx_, my, vz), (cx_, my, vz + 0.22), 0.012, Z_MINSTR, seg=6)
    k.cyl(V(cx_, my, vz + 0.08), V(cx_, my, vz + 0.20), 0.03, Z_MINSTR, 8)
    for i in range(3):
        a = TAU * i / 3
        tip = V(cx_ + 0.14 * math.cos(a), my + 0.14 * math.sin(a), vz + 0.20)
        rod(k, (cx_, my, vz + 0.20), tip, 0.005, Z_MINSTR, seg=4)
        d_ = V(-math.sin(a), math.cos(a), 0)
        k.lathe(tip - d_ * 0.03, d_, [(0.0, 0.0), (0.0, 0.035), (0.035, 0.035), (0.045, 0.0)], Z_MINSTR, 8, cap0=False,
                cap1=False)
    vx_ = va + 0.08                                                      # the vane: spindle, arm, the red tail fin
    rod(k, (vx_, my, vz), (vx_, my, vz + 0.20), 0.012, Z_MINSTR, seg=6)
    rod(k, (vx_ + 0.12, my, vz + 0.18), (vx_ - 0.22, my, vz + 0.18), 0.008, Z_MINSTR, seg=4)
    k.poly([V(vx_ - 0.16, my, vz + 0.12), V(vx_ - 0.36, my, vz + 0.10), V(vx_ - 0.36, my, vz + 0.28), V(vx_ - 0.16, my, vz + 0.24)],
           Z_MVANE)
    k.poly([V(vx_ - 0.16, my, vz + 0.24), V(vx_ - 0.36, my, vz + 0.28), V(vx_ - 0.36, my, vz + 0.10), V(vx_ - 0.16, my, vz + 0.12)],
           Z_MVANE)
    k.lathe(V(vx_ + 0.12, my, vz + 0.18), (1, 0, 0), [(0.0, 0.02), (0.05, 0.0)], Z_MINSTR, 6, cap0=True)
    for i in range(3):                                                   # three guys to pegs, turnbuckles
        a = TAU * i / 3 + 0.5
        gp = V(mx + 3.2 * math.cos(a), my + 3.2 * math.sin(a), 0.0)
        top = V(mx, my, mh * 0.62)
        rod(k, gp + V(0, 0, 0.05), top, 0.006, Z_MGUY, seg=4, caps=False)
        rod(k, gp + V(0, 0, -0.3), gp + V(0, 0, 0.12), 0.02, Z_MINSTR, seg=6)
    k.box(mx - 0.06, mx + 0.06, my - 0.06, my + 0.06, mh * 0.62 - 0.05, mh * 0.62 + 0.05, Z_MINSTR)
    # the rain gauge on its post
    gx, gy, gz0, gz1, gr_ = mt['gauge']
    k.box(gx - 0.035, gx + 0.035, gy - 0.035, gy + 0.035, -0.3, gz0, Z_MLEG)
    k.lathe(V(gx, gy, gz0), (0, 0, 1), [(0.0, 0.06), (0.04, gr_), (gz1 - gz0 - 0.03, gr_), (gz1 - gz0 - 0.02, gr_ + 0.006),
                                         (gz1 - gz0, gr_ + 0.006), (gz1 - gz0, gr_ - 0.008), (gz1 - gz0 - 0.10, 0.03)], Z_MGAUGE,
            14, cap0=True, cap1=False)
    # the logger box and its solar panel on a post, the cable to the screen, the snow stake
    lgx, lgy = -3.2, -2.6
    rod(k, (lgx, lgy, -0.4), (lgx, lgy, 2.4), 0.04, Z_MMAST, seg=8, caps=False)
    box6(k, (lgx - 0.22, lgy - 0.18, 0.9), (lgx + 0.22, lgy - 0.04, 1.4), Z_MLOGGER)
    k.box(lgx - 0.20, lgx + 0.20, lgy - 0.19, lgy - 0.18, 1.32, 1.38, Z_MINSTR)
    Rs = Matrix.Rotation(math.radians(-50), 3, 'X')
    obox(k, V(lgx, lgy - 0.2, 2.25), (0.66, 0.50, 0.035), Z_MSOLAR, Rs)
    k.tube([V(lgx, lgy - 0.10, 0.9), V(lgx, lgy - 0.05, 0.05), V(-0.35, -0.30, 0.03), V(-0.30, -0.25, 1.2)], 0.01, Z_MGUY, 4,
           caps=False)
    sx_, sy_ = 2.6, -2.8
    k.box(sx_ - 0.025, sx_ + 0.025, sy_ - 0.025, sy_ + 0.025, -0.3, 2.0, Z_MSTAKE)
    part('MeteoStation', 'static', (0, 0, 0), note='weather station: picket enclosure and gate, screen, wind mast, rain '
                                                   'gauge, logger and solar panel, snow stake')
    part('MeteoStation_Sign', 'static', (0.0, -F_ - 0.03, 0.55), parent='MeteoStation', note='the gate\'s sign (panel)')


# ================================================================ the lookout tower
def lookout():
    L = S.LOOKOUT
    k = kb('LookoutTower', 'Lookout')
    corners = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
    corner = lambda z, i: V(corners[i][0] * S.lookout_c(z), corners[i][1] * S.lookout_c(z), z)
    for i, (xs, ys) in enumerate(corners):                               # footings, shoes, anchor bolts
        cx, cy = xs * L['foot'], ys * L['foot']
        fh = L['footing'] / 2
        chamfer_box(k, (cx - fh, cy - fh, -1.0), (cx + fh, cy + fh, 0.10), 0.04, Z_LFOOT)
        k.box(cx - 0.18, cx + 0.18, cy - 0.18, cy + 0.18, 0.10, 0.125, Z_LPLATE)
        for dx in (-0.12, 0.12):
            for dy in (-0.12, 0.12):
                bolt(k, (cx + dx, cy + dy, 0.125), (0, 0, 1), 0.016, 0.014, Z_LPLATE, washer=0.024)
    bay = L['h'] / L['bays']
    zs = [0.125] + [bay * j for j in range(1, L['bays'] + 1)]
    for i in range(4):                                                   # the legs: square tubes bay by bay
        for za, zb in zip(zs[:-1], zs[1:]):
            bar(k, corner(za, i), corner(zb, i), 0.14, 0.14, Z_LLEG, up=(0, 0, 1), caps=False)
    for f in range(4):                                                   # horizontals (angles) and X-bracing (flats)
        i, j = f, (f + 1) % 4
        n_ = (corner(1.0, i) + corner(1.0, j)).to_2d().normalized().to_3d()
        for zi, z in enumerate(zs[1:], 1):
            a, b = corner(z, i), corner(z, j)
            bar(k, a, b, 0.08, 0.08, Z_LBRACE, up=(0, 0, 1), caps=False)
            za = zs[zi - 1]
            for p0, p1 in ((corner(za, i), corner(z, j)), (corner(za, j), corner(z, i))):
                bar(k, p0 + n_ * 0.02, p1 + n_ * 0.02, 0.07, 0.012, Z_LBRACE, up=n_, caps=False)
    # Update 3's stairs: the same treads and landings (kept where they were; decorative, as in Update 3: the flights are
    # 47..66 deg and stacked one over another), the stringers along
    # each flight, handrails, the landings' beams to the tower's horizontals
    tr = sorted(S.STAIRS['treads'], key=lambda r: r[0][2])
    lands = sorted(S.STAIRS['landings'], key=lambda r: r[0][2])
    for lo, hi in tr:
        box6(k, lo, hi, Z_LTREAD)
    for lo, hi in lands:
        box6(k, lo, hi, Z_LTREAD)
    flights = []
    for fi in range(7):
        f = [r for r in tr if 3 * fi - 0.05 <= r[0][2] < 3 * fi + 2.95]
        flights.append(sorted(f, key=lambda r: r[0][2]))
    for fi, f in enumerate(flights):
        first, last = f[0], f[-1]
        dirx = 1.0 if (last[0][0] > first[0][0]) else -1.0
        for side in (0, 1):                                              # the stringers (both sides of the treads)
            yv = (first[0][1] - 0.014) if side == 0 else (first[1][1] + 0.014)
            yv2 = (last[0][1] - 0.014) if side == 0 else (last[1][1] + 0.014)
            x_a = (first[0][0] if dirx > 0 else first[1][0]) - dirx * 0.10
            x_b = (last[1][0] if dirx > 0 else last[0][0]) + dirx * 0.05
            z_a, z_b = first[0][2] - 0.10, last[1][2] + 0.0
            a, b = V(x_a, yv, z_a), V(x_b, yv2, z_b)
            t_ = (b - a).normalized()
            bar(k, a - V(0, 0, 0.08), b - V(0, 0, 0.08), 0.012, 0.22, Z_LSTRING, up=(0, 0, 1))
            # the handrail on posts at both ends of the flight, 0.9 above the nosings
            pa = V(x_a + dirx * 0.12, yv + (-0.03 if side == 0 else 0.03), z_a + 0.10)
            pb = V(x_b - dirx * 0.08, yv2 + (-0.03 if side == 0 else 0.03), z_b)
            for p in (pa, pb):
                rod(k, p, p + V(0, 0, 1.0), 0.020, Z_LRAIL, seg=6, caps=True)
            rod(k, pa + V(0, 0, 0.95), pb + V(0, 0, 0.95), 0.022, Z_LRAIL, seg=6, caps=True)
            rod(k, pa + V(0, 0, 0.50), pb + V(0, 0, 0.50), 0.016, Z_LRAIL, seg=6, caps=True)
    for li, (lo, hi) in enumerate(lands):                                # beams under the landings to the tower's frame
        zt = lo[2]
        c_ = S.lookout_c(zt)
        xs_ = 1.0 if hi[0] > 0 else -1.0
        for yy in (lo[1] + 0.1, hi[1] - 0.1):
            a = V(lo[0] if xs_ > 0 else hi[0], yy, zt - 0.06)
            b = V(xs_ * c_, yy, zt - 0.06)
            bar(k, a - V(xs_ * 0.4, 0, 0), b, 0.06, 0.12, Z_LSTRING, up=(0, 0, 1))
        ox = hi[0] if xs_ > 0 else lo[0]                                 # the guard rail on the landing's outer edge
        for yy in (lo[1] + 0.03, hi[1] - 0.03):
            rod(k, (ox - xs_ * 0.03, yy, hi[2]), (ox - xs_ * 0.03, yy, hi[2] + 1.0), 0.020, Z_LRAIL, seg=6, caps=True)
        rod(k, (ox - xs_ * 0.03, lo[1] + 0.03, hi[2] + 0.95), (ox - xs_ * 0.03, hi[1] - 0.03, hi[2] + 0.95), 0.022, Z_LRAIL, seg=6)
        rod(k, (ox - xs_ * 0.03, lo[1] + 0.03, hi[2] + 0.50), (ox - xs_ * 0.03, hi[1] - 0.03, hi[2] + 0.50), 0.016, Z_LRAIL, seg=6)
    # the ship ladder from the top landing (+y) up to the cab floor at the stairwell's +y edge: three treads, the
    # stringers on the nosings' line, handrails outside the treads (the player's capsule fits between them)
    wx0, wx1, wy0, wy1 = L['well']
    lx0, lx1 = L['ladder_x']
    dpt = L['ladder_d']
    yc0 = L['ladder_y'][0]
    top_land = lands[-1]
    zl = top_land[1][2]
    f0, f1 = L['floor']
    for i, yc in enumerate(L['ladder_y']):
        zz = zl + 0.25 * (i + 1)
        box6(k, (lx0, yc - dpt / 2, zz - 0.04), (lx1, yc + dpt / 2, zz), Z_LTREAD)
    run = L['ladder_y'][1] - yc0
    ya = yc0 + run * (0.56 - 1.0)                                       # the stringers' foot on the landing
    yb = yc0 + run * ((f1 - zl) / 0.25 - 1.0)                           # their head under the floor's edge
    for xs in (lx0 - 0.014, lx1 + 0.014):
        bar(k, V(xs, ya, zl + 0.07), V(xs, yb, f1 - 0.07), 0.012, 0.16, Z_LSTRING, up=(0, 0, 1))
    for xs in (lx0 - 0.045, lx1 + 0.045):
        rod(k, (xs, ya + 0.04, zl + 0.03), (xs, ya + 0.04, zl + 0.95), 0.020, Z_LRAIL, seg=6, caps=True)
        rod(k, (xs, ya + 0.04, zl + 0.95), (xs, wy1 + 0.04, f1 + 0.95), 0.022, Z_LRAIL, seg=6, caps=True)
        rod(k, (xs, wy1 + 0.04, f1), (xs, wy1 + 0.04, f1 + 0.95), 0.020, Z_LRAIL, seg=6, caps=True)
    # the cab: its floor round the stairwell on joists (cut at the well, trimmers round it), the rails and toe boards
    # round the well (open where the ladder arrives), the boarded walls, the windows (M_GlassDirty), the sills, the
    # pyramid roof (corrugated) on rafters, the fire finder, the lightning rod
    cb = L['cab']
    for (a0, a1, b0, b1) in ((-cb, wx0, -cb, cb), (wx1, cb, -cb, cb), (wx0, wx1, -cb, wy0), (wx0, wx1, wy1, cb)):
        box6(k, (a0, b0, f0), (a1, b1, f1), Z_LFLOOR)
    for yy in (-1.5, -0.5, 0.5, 1.5):
        if wy0 - 0.05 < yy < wy1 + 0.05:
            k.box(-cb + 0.1, wx0 - 0.05, yy - 0.05, yy + 0.05, f0 - 0.18, f0, Z_LBRACE)
        else:
            k.box(-cb + 0.1, cb - 0.1, yy - 0.05, yy + 0.05, f0 - 0.18, f0, Z_LBRACE)
    k.box(wx0 - 0.05, wx0, wy0 - 0.05, wy1 + 0.05, f0 - 0.18, f0, Z_LBRACE)                    # the trimmer at x0
    for y0_ in (wy0 - 0.05, wy1):
        k.box(wx0, cb - 0.1, y0_, y0_ + 0.05, f0 - 0.18, f0, Z_LBRACE)                         # the headers at y0, y1
    ex = wx1 + 0.0                                                       # the -y side runs to the wall
    runs = [((wx0 - 0.03, wy0 - 0.03), (ex, wy0 - 0.03)), ((wx0 - 0.03, wy0 - 0.03), (wx0 - 0.03, wy1 + 0.03)),
            ((wx0 - 0.03, wy1 + 0.03), (lx0 - 0.09, wy1 + 0.03)), ((lx1 + 0.09, wy1 + 0.03), (ex, wy1 + 0.03))]
    for (ax, ay), (bx, by) in runs:
        n_post = max(1, int(round(math.hypot(bx - ax, by - ay) / 0.9)))
        for t in np.linspace(0.0, 1.0, n_post + 1):
            px_, py_ = ax + (bx - ax) * t, ay + (by - ay) * t
            if px_ > wx1 - 0.04:
                continue                                                 # (the wall is there)
            rod(k, (px_, py_, f1), (px_, py_, f1 + 1.0), 0.020, Z_LRAIL, seg=6, caps=True)
        bx_ = min(bx, wx1 - 0.03)
        rod(k, (ax, ay, f1 + 0.95), (bx_, by, f1 + 0.95), 0.022, Z_LRAIL, seg=6, caps=True)
        rod(k, (ax, ay, f1 + 0.50), (bx_, by, f1 + 0.50), 0.016, Z_LRAIL, seg=6, caps=True)
        horiz = abs(by - ay) < 1e-6
        if horiz:
            k.box(min(ax, bx_), max(ax, bx_), ay - 0.01, ay + 0.01, f1, f1 + 0.10, Z_LFLOOR)
        else:
            k.box(ax - 0.01, ax + 0.01, min(ay, by), max(ay, by), f1, f1 + 0.10, Z_LFLOOR)
    w = L['wall']
    g0, g1 = L['glass']
    kg = kb('LookoutTower_Glass', 'glass')
    for side in range(4):
        a = math.pi / 2 * side
        n_ = V(math.cos(a), math.sin(a), 0)
        t_ = V(-n_.y, n_.x, 0)
        Rw = Matrix((t_, n_, V(0, 0, 1))).transposed()
        obox(k, n_ * w + V(0, 0, (f1 + L['wall_top']) / 2), (2 * w + 0.06, 0.06, L['wall_top'] - f1), Z_LBOARD, Rw)
        obox(k, n_ * (w + 0.06) + V(0, 0, L['wall_top'] + 0.02), (2 * w + 0.20, 0.14, 0.04), Z_LPOST, Rw)        # the sill
        for xx in (-w, -0.6, 0.6, w):                                    # the posts between the windows
            obox(k, n_ * w + t_ * xx + V(0, 0, (L['wall_top'] + L['eaves']) / 2), (0.08, 0.08, L['eaves'] - L['wall_top']),
                 Z_LPOST, Rw)
        obox(k, n_ * w + V(0, 0, L['eaves'] - 0.03), (2 * w + 0.08, 0.10, 0.06), Z_LPOST, Rw)                     # the head
        for xc in (-1.2, 0.0, 1.2):                                      # three panes a side, a glazing bar in each
            c = n_ * w + t_ * xc + V(0, 0, (g0 + g1) / 2)
            kg.quad_uv(c, n_, 1.12, g1 - g0, (0, 0, 1, 1))
            obox(k, n_ * (w + 0.005) + t_ * xc + V(0, 0, (g0 + g1) / 2), (0.03, 0.03, g1 - g0), Z_LPOST, Rw)
    eh, apex = L['roof']
    ez = L['eaves']
    base = [V(-eh, -eh, ez), V(eh, -eh, ez), V(eh, eh, ez), V(-eh, eh, ez)]
    top = V(0, 0, apex)
    for i in range(4):
        j = (i + 1) % 4
        face(k, [base[i], base[j], top], Z_LROOF, ((base[i] + base[j]) / 2 - V(0, 0, ez)).normalized() + V(0, 0, 1))
        face(k, [base[j], base[i], top - V(0, 0, 0.05)], Z_LROOFIN, -((base[i] + base[j]) / 2 - V(0, 0, ez)).normalized() - V(0, 0, 1))
        face(k, [base[i], base[j], base[j] - V(0, 0, 0.05), base[i] - V(0, 0, 0.05)], Z_LROOF,
             ((base[i] + base[j]) / 2 - V(0, 0, ez)).normalized())
    for i in range(4):                                                   # the hip rafters
        bar(k, base[i] * 0.95 + V(0, 0, ez * 0.05 - 0.10), top - V(0, 0, 0.14), 0.06, 0.10, Z_LPOST)
    fx, fy = L['finder']                                                 # the fire finder: pedestal, round table, sight ring
    rod(k, (fx, fy, 22.0), (fx, fy, 22.95), 0.05, Z_LTABLE, seg=8)
    k.cyl(V(fx, fy, 22.95), V(fx, fy, 23.0), 0.42, Z_LTABLE, 16)
    k.tube([V(fx + 0.38 * math.cos(t), fy + 0.38 * math.sin(t), 23.04) for t in np.linspace(0, TAU, 17)], 0.01, Z_LROD, 5,
           caps=False)
    k.box(fx - 0.30, fx + 0.30, fy - 0.02, fy + 0.02, 23.0, 23.02, Z_LROD)
    for xs in (-0.30, 0.30):
        k.box(fx + xs - 0.01, fx + xs + 0.01, fy - 0.02, fy + 0.02, 23.02, 23.16, Z_LROD)
    k.cyl(V(1.2, 1.2, 22.0), V(1.2, 1.2, 22.55), 0.025, Z_LTABLE, 6, caps=False)            # a stool
    k.cyl(V(1.2, 1.2, 22.55), V(1.2, 1.2, 22.6), 0.17, Z_LTABLE, 12)
    rod(k, (0, 0, apex - 0.05), (0, 0, L['rod_top']), 0.025, Z_LROD, seg=6)
    k.lathe(V(0, 0, L['rod_top']), (0, 0, 1), [(0.0, 0.025), (0.12, 0.0)], Z_LROD, 6, cap0=False)
    dc = [corner(z, 0) + V(0.08, 0.08, 0) for z in (21.9, 15.0, 8.0, 0.2)]                 # the down conductor
    for a, b in zip(dc[:-1], dc[1:]):
        k.strip([a, b], V(1, 1, 0).normalized(), 0.025, 0.004, Z_LROD, caps=False)
    # the sign by the stairs' foot (faces -x)
    kf = kb('LookoutTower_Sign', 'panel')
    sx_, sy_ = -3.75, -0.63
    for yy in (sy_ - 0.30, sy_ + 0.30):
        rod(k, (sx_ + 0.045, yy, -0.4), (sx_ + 0.045, yy, 1.72), 0.03, Z_LPLATE, seg=8, caps=True)
    ol = rrect_xz(-0.37, 0.37, 1.34, 1.70, 0.015, 2)
    u0, v0, u1, v1 = uv('lookout')
    pts = [V(sx_, sy_ - xx, zz) for xx, zz in ol]
    face(kf, pts, 0.0, (-1, 0, 0), [(u0 + (xx + 0.37) / 0.74 * (u1 - u0), v0 + (zz - 1.34) / 0.36 * (v1 - v0)) for xx, zz in ol])
    bk = [V(sx_ + 0.014, sy_ - xx, zz) for xx, zz in ol]
    face(k, bk, Z_LSBACK, (1, 0, 0))
    for i in range(len(ol)):
        j = (i + 1) % len(ol)
        face(k, [pts[i], pts[j], bk[j], bk[i]], Z_LSBACK, V(0, -(ol[i][0] + ol[j][0]) / 2, ((ol[i][1] + ol[j][1]) / 2) - 1.52))
    part('LookoutTower', 'static', (0, 0, 0), note='22 m fire lookout: legs, bracing, Update 3\'s stairs (the same treads and '
                                                   'landings), stringers, handrails, a stairwell in the cab floor, a ship ladder up to it, '
                                                   'the cab with its windows and roof, the fire finder, the lightning rod')
    part('LookoutTower_Glass', 'static', (0, 0, 23.55), parent='LookoutTower', note='the cab\'s panes (M_GlassDirty)')
    part('LookoutTower_Sign', 'static', (sx_, sy_, 1.52), parent='LookoutTower', note='the sign by the stairs (panel)')


# ================================================================ shared: walls with openings
def wall_x(k, x_out, x_in, y0, y1, z0, z1, holes, zo, zi, zr):
    """a wall between the planes x_out (outer) and x_in (inner) from y0..y1, z0..z1, with rectangular holes
    [(ya, yb, za, zb)]: built from boxes round the holes; outer face zone zo, inner zi, the reveals zr"""
    _wall(k, 'x', x_out, x_in, y0, y1, z0, z1, holes, zo, zi, zr)


def wall_y(k, y_out, y_in, x0, x1, z0, z1, holes, zo, zi, zr):
    _wall(k, 'y', y_out, y_in, x0, x1, z0, z1, holes, zo, zi, zr)


def _wall(k, ax, o, i, a0, a1, z0, z1, holes, zo, zi, zr):
    holes = sorted(holes)
    pieces = []
    prev = a0
    for (ha, hb, hz0, hz1) in holes:
        pieces.append((prev, ha, z0, z1))
        if hz0 > z0:
            pieces.append((ha, hb, z0, hz0))
        if hz1 < z1:
            pieces.append((ha, hb, hz1, z1))
        prev = hb
    pieces.append((prev, a1, z0, z1))
    lo_n, hi_n = min(o, i), max(o, i)
    out_key = ('-' if o < i else '+') + ax
    in_key = ('+' if o < i else '-') + ax
    for (pa, pb, pz0, pz1) in pieces:
        if pb - pa < 1e-4 or pz1 - pz0 < 1e-4:
            continue
        zones = {out_key: zo, in_key: zi, '*': zr}
        if ax == 'x':
            box6(k, (lo_n, pa, pz0), (hi_n, pb, pz1), zones, skip=('-z',) if pz0 <= z0 + 1e-6 else ())
        else:
            box6(k, (pa, lo_n, pz0), (pb, hi_n, pz1), zones, skip=('-z',) if pz0 <= z0 + 1e-6 else ())


# ================================================================ the pump house
def pumphouse():
    p = S.PUMP
    k = kb('PumpHouse', 'Small')
    bx, by, bz = p['base']
    chamfer_box(k, (-bx, -by, -0.30), (bx, by, bz), 0.02, Z_PBASE)
    wx, wy, t = p['wall']
    top = p['top']
    d0, d1, dz = -0.60, 0.30, p['door'][2]                               # the opening, round Update 3's door leaf
    wall_y(k, -wy, -wy + t, -wx, wx, bz, top, [(d0, d1, bz, dz)], Z_PBRICK, Z_PPLASTER, Z_PBRICK)
    wall_y(k, wy, wy - t, -wx, wx, bz, top, [(0.48, 0.72, 0.48, 0.72)], Z_PBRICK, Z_PPLASTER, Z_PBRICK)   # the pipe's hole
    wall_x(k, wx, wx - t, -wy + t, wy - t, bz, top, [(-0.30, 0.30, 1.95, 2.30)], Z_PBRICK, Z_PPLASTER, Z_PBRICK)
    wall_x(k, -wx, -wx + t, -wy + t, wy - t, bz, top, [], Z_PBRICK, Z_PPLASTER, Z_PBRICK)
    face(k, [V(-wx + t, -wy + t, bz + 0.005), V(wx - t, -wy + t, bz + 0.005), V(wx - t, wy - t, bz + 0.005),
             V(-wx + t, wy - t, bz + 0.005)], Z_PFLOOR, (0, 0, 1))
    for zz in np.arange(1.98, 2.29, 0.06):                               # the vent's louvres (+x wall)
        obox(k, V(wx - t / 2, 0.0, zz), (0.04, 0.60, 0.012), Z_PFLASH, Matrix.Rotation(math.radians(-35), 3, 'Y'))
    rx, ry, rz0, rz1 = p['roof']
    box6(k, (-rx, -ry, rz0), (rx, ry, rz1), {'-z': Z_PPLASTER, '*': Z_PROOF})
    for (a0, a1, b0, b1) in ((-rx - 0.02, rx + 0.02, -ry - 0.02, -ry), (-rx - 0.02, rx + 0.02, ry, ry + 0.02),
                             (-rx - 0.02, -rx, -ry, ry), (rx, rx + 0.02, -ry, ry)):
        k.box(a0, a1, b0, b1, rz0 - 0.06, rz1 + 0.03, Z_PFLASH)
    k.cyl(V(1.4, 0.9, rz1), V(1.4, 0.9, rz1 + 0.45), 0.05, Z_PFLASH, 8)  # the vent pipe and its cap
    k.lathe(V(1.4, 0.9, rz1 + 0.45), (0, 0, 1), [(0.0, 0.09), (0.04, 0.09), (0.08, 0.0)], Z_PFLASH, 8, cap0=True)
    for a0, a1, z_a, z_b in ((d0 - 0.06, d0, bz, dz + 0.06), (d1, d1 + 0.06, bz, dz + 0.06), (d0 - 0.06, d1 + 0.06, dz, dz + 0.06)):
        k.box(a0, a1, -wy - 0.012, -wy, z_a, z_b, Z_PDOOR)               # the steel frame round the opening
    # the pump on its frame, the motor, the coupling guard, the valve and the pipe out through the back wall to the lake
    k.box(0.20, 1.40, 0.02, 0.62, bz, bz + 0.10, Z_PMOTOR)
    k.cyl(V(0.60, 0.10, 0.62), V(0.60, 0.52, 0.62), 0.26, Z_PPUMP, 14)
    k.cyl(V(0.60, 0.31, 0.32), V(0.60, 0.31, 0.40), 0.16, Z_PPUMP, 12)
    k.cyl(V(0.86, 0.31, 0.62), V(1.02, 0.31, 0.62), 0.12, Z_PMOTOR, 10)
    k.cyl(V(1.02, 0.31, 0.62), V(1.50, 0.31, 0.62), 0.20, Z_PMOTOR, 14)
    for a in range(12):                                                  # the motor's fins
        q = TAU * a / 12
        k.box_m(V(1.26, 0.31 + 0.205 * math.cos(q), 0.62 + 0.205 * math.sin(q)), (0.40, 0.02, 0.02), Z_PMOTOR,
                Matrix.Rotation(q, 3, 'X'))
    box6(k, (1.10, 0.10, 0.85), (1.34, 0.52, 0.95), Z_PMOTOR)            # its terminal box
    px_, py0, py1, pz_ = p['pipe']
    k.tube([V(0.60, 0.52, pz_), V(0.60, 0.70, pz_), V(0.60, 1.20, pz_), V(0.60, 1.60, pz_), V(0.60, py1 - 0.35, pz_),
            V(0.60, py1 - 0.05, pz_ - 0.25), V(0.60, py1, -0.30)], 0.10, Z_PPIPE, 10)
    for yy in (0.70, 1.62, 3.0):                                         # flanges
        k.cyl(V(0.60, yy - 0.02, pz_), V(0.60, yy + 0.02, pz_), 0.15, Z_PPIPE, 10)
    k.cyl(V(0.60, 0.95, pz_), V(0.60, 1.07, pz_), 0.14, Z_PPIPE, 10)     # the valve, its stem and handwheel
    k.cyl(V(0.60, 1.01, pz_ + 0.12), V(0.60, 1.01, pz_ + 0.40), 0.02, Z_PMOTOR, 6)
    k.tube([V(0.60 + 0.16 * math.cos(q), 1.01 + 0.16 * math.sin(q), pz_ + 0.40) for q in np.linspace(0, TAU, 13)], 0.012,
           Z_PPUMP, 5, caps=False)
    for yy in (2.2, 3.6):                                                # pipe saddles outside
        k.box(0.45, 0.75, yy - 0.06, yy + 0.06, -0.2, pz_ - 0.10, Z_PBASE)
    k.cyl(V(0.60, 0.45, 0.88), V(0.60, 0.45, 1.05), 0.012, Z_PMOTOR, 6)  # the gauge
    k.cyl(V(0.60, 0.42, 1.05), V(0.60, 0.48, 1.05), 0.05, Z_PFLASH, 10)
    bx0, bx1, by0, by1, bz0, bz1 = p['box']
    box6(k, (bx0, wy - t - 0.20, bz0), (bx1, wy - t, bz1), Z_PBOX)       # the switch box, its conduit and cable
    k.cyl(V((bx0 + bx1) / 2, wy - t - 0.06, bz1), V((bx0 + bx1) / 2, wy - t - 0.06, top), 0.02, Z_PBOX, 6, caps=False)
    k.tube([V(bx1 - 0.05, wy - t - 0.10, bz0), V(bx1 - 0.05, wy - t - 0.10, bz + 0.02), V(1.30, 0.70, bz + 0.02),
            V(1.22, 0.45, 0.90)], 0.015, Z_PMOTOR, 5, caps=False)
    k.box(bx0 + 0.10, bx0 + 0.16, wy - t - 0.22, wy - t - 0.20, bz1 - 0.30, bz1 - 0.10, Z_PMOTOR)   # the main switch
    kf = kb('PumpHouse_Sign', 'panel')                                   # the enamel sign right of the door
    sx_, sy_, sz_, sw_, sh_ = p['sign']
    sign_plate(k, kf, (sx_, -wy - 0.008, sz_), sw_, sh_, uv('pump'), back=0.006, zone=Z_PSBACK)
    part('PumpHouse', 'static', (0, 0, 0), note='brick pump house: flat roof, the pump and motor, the pipe to the lake, the '
                                                'switch box, the sign')
    part('PumpHouse_Sign', 'static', (sx_, -wy - 0.008, sz_), parent='PumpHouse', note='PUMPSTATION / PUMP STATION (panel)')
    # the door (IX_PumpDoor_7): a steel leaf on Update 3's hinge, its handle, lock, vent
    lf = p['leaf']
    kd = kb('IX_PumpDoor_7', 'Small')
    hx_, x1_, yd = lf['hinge_x'], lf['x1'], lf['y']
    zd0, zd1 = lf['z']
    yf_ = -wy + 0.002                                                    # the leaf's outer face: in the opening, just
    box6(kd, (hx_ + 0.012, yf_, zd0), (x1_, yf_ + 0.040, zd1), Z_PDOOR)   # behind the hinge's line on the wall's face
    kd.box(x1_ - 0.09, x1_ - 0.055, yf_ - 0.035, yf_, 1.12, 1.16, Z_PPIPE)                              # the lever handle
    kd.box(x1_ - 0.16, x1_ - 0.055, yf_ - 0.05, yf_ - 0.035, 1.12, 1.16, Z_PPIPE)
    kd.box(x1_ - 0.10, x1_ - 0.045, yf_ - 0.010, yf_, 1.04, 1.24, Z_PPIPE)
    kd.cyl(V(x1_ - 0.075, yf_ + 0.001, 1.30), V(x1_ - 0.075, yf_ - 0.012, 1.30), 0.018, Z_PPIPE, 8)
    for zz in np.arange(0.40, 0.70, 0.06):
        kd.box(hx_ + 0.20, x1_ - 0.20, yf_ - 0.010, yf_, zz, zz + 0.025, Z_PDOOR)
    for zz in (zd0 + 0.20, zd1 - 0.20):                                  # the knuckles on the axis
        kd.cyl(V(hx_, -wy, zz - 0.07), V(hx_, -wy, zz + 0.07), 0.014, Z_PDOOR, 6)
        kd.box(hx_ + 0.005, hx_ + 0.10, yf_ - 0.004, yf_, zz - 0.03, zz + 0.03, Z_PDOOR)                  # their leaves
    part('IX_PumpDoor_7', 'hinge', (hx_, -wy, zd0), axis=(0, 0, -1), rng=(0, 100), parent='PumpHouse',
         note='the steel door: Update 3\'s hinge (vertical at x -0.59), opens out (-y) up to 100 deg')


# ================================================================ the forest cabin
def cabin():
    c = S.CABIN
    k = kb('Cabin', 'Small')
    X, Y, r, crs = c['x'], c['y'], c['log_r'], c['course']
    d0, d1, dz = c['door']
    wy0, wy1, wz0, wz1 = c['window']
    ext = 0.35                                                           # the notched corners: log ends 0.35 past
    for i in range(c['courses']):
        z = 0.15 + crs * i
        zf = z + crs / 2                                                 # the front / back logs sit half a course up
        for sx in (-1, 1):                                               # the side walls: along y
            pieces = [(-Y - ext, Y + ext)]
            if sx > 0 and wz0 - r < z < wz1 + r:
                pieces = [(-Y - ext, wy0), (wy1, Y + ext)]
            for a, b in pieces:
                log_seg(k, (sx * X, a, z), (sx * X, b, z), r, r * 0.95, Z_KLOG, Z_KLOGEND, seg=8, n=2, wob=0.04,
                        seed=100 + i * 7 + sx)
        if zf > 3.62:
            continue
        for sy in (-1, 1):                                               # the front / back walls: along x
            pieces = [(-X - ext, X + ext)]
            if sy < 0 and zf < dz + r:
                pieces = [(-X - ext, d0 - 0.06), (d1, X + ext)]
            for a, b in pieces:
                log_seg(k, (a, sy * Y, zf), (b, sy * Y, zf), r, r * 0.95, Z_KLOG, Z_KLOGEND, seg=8, n=2, wob=0.04,
                        seed=300 + i * 7 + sy)
    # the chinking: a clay-and-moss core in each wall's middle plane, seen in the seams between the round logs (no light
    # through the walls), cut at the door and the window (its edges inside their frames)
    t_, zt_ = 0.025, 0.15 + crs * (c['courses'] - 1) + r * 0.6
    k.box(-X - t_, -X + t_, -Y, Y, 0.04, zt_, Z_KCHINK)
    for (a, b, z0_, z1_) in ((-Y, wy0 - 0.035, 0.04, zt_), (wy1 + 0.035, Y, 0.04, zt_),
                             (wy0 - 0.035, wy1 + 0.035, 0.04, wz0 - 0.035), (wy0 - 0.035, wy1 + 0.035, wz1 + 0.035, zt_)):
        k.box(X - t_, X + t_, a, b, z0_, z1_, Z_KCHINK)
    k.box(-X, X, Y - t_, Y + t_, 0.16, zt_, Z_KCHINK)
    for (a, b, z0_, z1_) in ((-X, d0 - 0.065, 0.16, zt_), (d1 + 0.035, X, 0.16, zt_), (d0 - 0.035, d1 + 0.035, dz + 0.05, zt_)):
        k.box(a, b, -Y - t_, -Y + t_, z0_, z1_, Z_KCHINK)
    for (a0, a1, b0, b1, z0, z1) in ((d0 - 0.07, d0, -Y, -Y + 0.14, 0.18, dz),                     # the door's frame:
                                     (d0 - 0.07, d0 - 0.055, -Y - 0.14, -Y, 0.18, dz),           # hinge side, rebated
                                     (d1, d1 + 0.07, -Y - 0.14, -Y + 0.14, 0.18, dz + 0.07),       # outside
                                     (d0 - 0.07, d1 + 0.07, -Y - 0.14, -Y + 0.14, dz, dz + 0.10)):
        box6(k, (a0, b0, z0), (a1, b1, z1), Z_KBOARD)
    for (a0, a1, z0, z1) in ((wy0 - 0.07, wy0, wz0 - 0.07, wz1 + 0.07), (wy1, wy1 + 0.07, wz0 - 0.07, wz1 + 0.07),
                             (wy0 - 0.07, wy1 + 0.07, wz0 - 0.07, wz0), (wy0 - 0.07, wy1 + 0.07, wz1, wz1 + 0.07)):
        box6(k, (X - 0.14, a0, z0), (X + 0.14, a1, z1), Z_KFRAME)        # the window's frame (white, as the hut's)
    box6(k, (X + 0.14, wy0 - 0.10, wz0 - 0.10), (X + 0.22, wy1 + 0.10, wz0 - 0.06), Z_KFRAME)       # the sill
    k.box(X - 0.01, X + 0.01, (wy0 + wy1) / 2 - 0.02, (wy0 + wy1) / 2 + 0.02, wz0, wz1, Z_KFRAME)    # the glazing bars
    k.box(X - 0.01, X + 0.01, wy0, wy1, (wz0 + wz1) / 2 - 0.02, (wz0 + wz1) / 2 + 0.02, Z_KFRAME)
    kg = kb('Cabin_Glass', 'glass')
    kg.quad_uv(V(X, (wy0 + wy1) / 2, (wz0 + wz1) / 2), V(1, 0, 0), wy1 - wy0, wz1 - wz0, (0, 0, 1, 1))
    # the floor, the gables (board and batten), the roof (boards under tar paper), bargeboards, the ridge cap
    f0, f1 = c['floor']
    box6(k, (-X + 0.12, -Y + 0.12, f0), (X - 0.12, Y - 0.12, f1), Z_KFLOOR)
    ey, ez = c['eaves']
    rz, rx = c['ridge'], c['roof_x']
    zg0 = 0.15 + crs * (c['courses'] - 1) + r
    for sx in (-1, 1):
        g = [V(sx * X, -Y - ext * 0.3, zg0), V(sx * X, Y + ext * 0.3, zg0), V(sx * X, 0.0, rz - 0.12)]
        face(k, g, Z_KBOARD, (sx, 0, 0))
        face(k, [p_ - V(sx * 0.03, 0, 0) for p_ in g], Z_KBOARD, (-sx, 0, 0))
        for yy in np.arange(-1.6, 1.61, 0.4):                            # battens
            zt_ = zg0 + (rz - 0.12 - zg0) * (1 - abs(yy) / (Y + ext * 0.3))
            k.box(sx * X + (0.0 if sx > 0 else -0.025), sx * X + (0.025 if sx > 0 else 0.0), yy - 0.025, yy + 0.025, zg0, zt_,
                  Z_KBOARD)
    th = 0.12
    for sy in (-1, 1):
        a = [V(-rx, sy * ey, ez), V(rx, sy * ey, ez), V(rx, 0.0, rz), V(-rx, 0.0, rz)]
        up_ = V(0, sy * (rz - ez), ey).normalized()
        face(k, a, Z_KROOF, up_)
        b = [p_ - V(0, 0, th) for p_ in a]
        face(k, b, Z_KBOARD, -up_)
        face(k, [a[0], a[1], b[1], b[0]], Z_KBOARD, (0, sy, 0))
        for sx in (-1, 1):
            i0, i1 = (0, 3) if sx < 0 else (1, 2)
            face(k, [a[i0], a[i1], b[i1], b[i0]], Z_KBOARD, (sx, 0, 0))
            bar(k, V(sx * (rx + 0.02), sy * ey, ez - 0.10), V(sx * (rx + 0.02), 0.0, rz - 0.06), 0.03, 0.22, Z_KBOARD,
                up=(0, 0, 1))                                            # the bargeboards
    k.strip([V(-rx - 0.02, 0.0, rz + 0.01), V(rx + 0.02, 0.0, rz + 0.01)], V(0, 0, 1), 0.30, 0.02, Z_KROOF, caps=True)
    # the porch: the deck on log joists, two posts, a lean-to roof under the main eave
    px0, px1, py0, py1, pz = c['porch']
    box6(k, (px0, py0, pz - 0.04), (px1, py1, pz), Z_KDECK)
    for xx in (px0 + 0.15, 0.0, px1 - 0.15):
        log_seg(k, (xx, py0 + 0.05, pz - 0.10), (xx, py1, pz - 0.10), 0.07, 0.065, Z_KWOOD, Z_KWOODEND, seg=6, n=2, wob=0.05,
                seed=500 + int(xx * 10))
    ppx0, ppx1, ppy = c['porch_posts']
    zr0, zr1 = 3.15, 2.62
    for xx in (ppx0, ppx1):
        log_seg(k, (xx, ppy, pz), (xx, ppy, zr1 - 0.02), 0.07, 0.065, Z_KWOOD, Z_KWOODEND, seg=7, n=2, wob=0.04,
                seed=520 + int(xx * 10))
    log_seg(k, (ppx0 - 0.3, ppy, zr1 - 0.04), (ppx1 + 0.3, ppy, zr1 - 0.04), 0.07, 0.065, Z_KWOOD, Z_KWOODEND, seg=7, n=2,
            wob=0.03, seed=530)
    a = [V(-1.45, -Y - 0.15, zr0), V(1.45, -Y - 0.15, zr0), V(1.45, ppy - 0.25, zr1), V(-1.45, ppy - 0.25, zr1)]
    face(k, a, Z_KROOF, (0, -0.35, 1))
    b = [p_ - V(0, 0, 0.08) for p_ in a]
    face(k, b, Z_KBOARD, (0, 0.35, -1))
    for i0, i1, n_ in ((0, 3, (-1, 0, 0)), (1, 2, (1, 0, 0)), (2, 3, (0, -1, 0))):
        face(k, [a[i0], a[i1], b[i1], b[i0]], Z_KBOARD, n_)
    # the stove and its pipe through the roof, the bunk and mattress, the table and a stool, a shelf
    sx_, sy_ = c['stove']
    box6(k, (sx_ - 0.24, sy_ - 0.25, f1 + 0.10), (sx_ + 0.24, sy_ + 0.25, 0.90), Z_KSTOVE)
    for xs in (-1, 1):                                                   # its legs
        for ys in (-1, 1):
            k.box(sx_ + xs * 0.20 - 0.02, sx_ + xs * 0.20 + 0.02, sy_ + ys * 0.21 - 0.02, sy_ + ys * 0.21 + 0.02, f1, f1 + 0.10,
                  Z_KSTOVE)
    k.box(sx_ - 0.16, sx_ + 0.16, sy_ - 0.255, sy_ - 0.25, 0.40, 0.70, Z_KSTOVE)
    k.tube([V(sx_, sy_ + 0.05, 0.90), V(sx_, sy_ + 0.05, c['chimney_top'] - 0.12)], 0.07, Z_KPIPE, 10, caps=False)
    k.lathe(V(sx_, sy_ + 0.05, c['chimney_top'] - 0.12), (0, 0, 1), [(0.0, 0.07), (0.04, 0.16), (0.08, 0.16), (0.12, 0.0)],
            Z_KPIPE, 10, cap0=False)
    bx0, bx1, by0, by1, bz = c['bunk']
    box6(k, (bx0, by0, bz - 0.10), (bx1, by1, bz), Z_KFURN)
    for xx in (bx0 + 0.05, bx1 - 0.05):
        k.box(xx - 0.04, xx + 0.04, by0 + 0.02, by0 + 0.10, f1, bz - 0.10, Z_KFURN)
    VM.rbox(k, V((bx0 + bx1) / 2, (by0 + by1) / 2, bz + 0.06), (bx1 - bx0 - 0.08, by1 - by0 - 0.08, 0.12), Z_KMATT, r=0.04,
            ch=0.02)
    tx, ty, tz = c['table']
    box6(k, (tx - 0.5, ty - 0.35, tz - 0.05), (tx + 0.5, ty + 0.35, tz), Z_KFURN)
    for xs in (-1, 1):
        for ys in (-1, 1):
            k.box(tx + xs * 0.42 - 0.03, tx + xs * 0.42 + 0.03, ty + ys * 0.28 - 0.03, ty + ys * 0.28 + 0.03, f1, tz - 0.05, Z_KFURN)
    box6(k, (0.55, -0.85, 0.42), (0.85, -0.55, 0.46), Z_KFURN)
    for xs in (-1, 1):
        for ys in (-1, 1):
            k.box(0.70 + xs * 0.12 - 0.02, 0.70 + xs * 0.12 + 0.02, -0.70 + ys * 0.12 - 0.02, -0.70 + ys * 0.12 + 0.02, f1, 0.42,
                  Z_KFURN)
    box6(k, (-X + 0.12, -1.6, 1.55), (-X + 0.42, -0.4, 1.58), Z_KFURN)
    # the woodpile against the -x wall (Update 3's: nine logs along y)
    for i, (xx, zz, rr) in enumerate(((-2.84, 0.20, 0.21), (-3.28, 0.20, 0.19), (-3.72, 0.20, 0.20), (-4.16, 0.20, 0.21),
                                      (-3.06, 0.56, 0.20), (-3.50, 0.56, 0.18), (-3.94, 0.56, 0.21),
                                      (-3.28, 0.92, 0.19), (-3.72, 0.92, 0.19))):
        a, b = V(xx, -2.0 + 0.05 * (i % 3), zz), V(xx, 3.0 - 0.06 * (i % 2), zz)
        if i % 2:
            a, b = b, a
        log_seg(k, a, b, rr, rr * 0.9, Z_KWOOD, Z_KWOODEND, seg=9, n=4, wob=0.05, seed=600 + i)
    part('Cabin', 'static', (0, 0, 0), note='log cabin: notched logs, the window, a board and felt roof, the porch, the stove, '
                                            'the bunk, the table, the woodpile')
    part('Cabin_Glass', 'static', (X, (wy0 + wy1) / 2, (wz0 + wz1) / 2), parent='Cabin', note='the window\'s pane (M_GlassDirty)')
    # the door (IX_CabinDoor_9): planks, a Z-brace, the latch, strap hinges
    lf = c['leaf']
    kd = kb('IX_CabinDoor_9', 'Small')
    hx_, x1_, yd = lf['hinge_x'], lf['x1'], lf['y']
    zd0, zd1 = lf['z']
    box6(kd, (hx_ + 0.01, yd - 0.025, zd0 + 0.02), (x1_ - 0.01, yd + 0.025, zd1), Z_KDOOR)
    for zz in (zd0 + 0.25, zd1 - 0.25):                                  # the ledges and the strap hinges inside (+y)
        kd.box(hx_ + 0.04, x1_ - 0.05, yd + 0.025, yd + 0.05, zz - 0.06, zz + 0.06, Z_KDOOR)
        kd.box(hx_ + 0.012, hx_ + 0.35, yd + 0.05, yd + 0.056, zz - 0.025, zz + 0.025, Z_KPIPE)
    dz_ = (zd1 - zd0 - 0.5)
    obox(kd, V((hx_ + x1_) / 2, yd + 0.0375, (zd0 + zd1) / 2), ((dz_ ** 2 + (x1_ - hx_ - 0.12) ** 2) ** 0.5, 0.025, 0.11), Z_KDOOR,
         Matrix.Rotation(-math.atan2(dz_, x1_ - hx_ - 0.12), 3, 'Y'))   # the Z's diagonal
    kd.box(x1_ - 0.12, x1_ - 0.08, yd - 0.07, yd - 0.025, 1.08, 1.17, Z_KPIPE)                          # the latch outside
    kd.box(x1_ - 0.12, x1_ - 0.08, yd + 0.025, yd + 0.06, 1.08, 1.17, Z_KPIPE)                          # and its grip inside
    part('IX_CabinDoor_9', 'hinge', (hx_, yd, zd0), axis=(0, 0, -1), rng=(0, 100), parent='Cabin',
         note='the plank door: Update 3\'s hinge (vertical at x -1.47), opens out (-y) up to 100 deg')


# ================================================================ the chapel
def chapel():
    c = S.CHAPEL
    k = kb('Chapel', 'Chapel')
    ox, oy = c['out']
    ix, iy = c['inner']
    wt = c['wall_top']
    fl = 0.10                                                            # the floor above the terrain (Update 3's was 0)
    d0, d1, dz = c['door']
    wz0, wz1 = c['win_z']
    # the fieldstone plinth round the walls, the walls (plaster) with the door and four windows, the gables
    for (a0, a1, b0, b1) in ((-ox - 0.04, ox + 0.04, -oy - 0.04, -oy), (-ox - 0.04, ox + 0.04, oy, oy + 0.04),
                             (-ox - 0.04, -ox, -oy, oy), (ox, ox + 0.04, -oy, oy)):
        pieces = [(a0, a1)]
        if b1 <= -oy + 1e-6:
            pieces = [(a0, d0 - 0.10), (d1 + 0.10, a1)]
        for pa, pb in pieces:
            box6(k, (pa, b0, -0.40), (pb, b1, 0.50), Z_CPLINTH, skip=('-z',))
    wall_y(k, -oy, -iy, -ox, ox, -0.20, wt, [(d0, d1, fl, dz)], Z_CWALL, Z_CWALLIN, Z_CWALL)
    wall_y(k, oy, iy, -ox, ox, -0.20, wt, [], Z_CWALL, Z_CWALLIN, Z_CWALL)
    holes = [(ya, yb, wz0, wz1) for ya, yb in c['windows']]
    wall_x(k, -ox, -ix, -iy, iy, -0.20, wt, holes, Z_CWALL, Z_CWALLIN, Z_CWALL)
    wall_x(k, ox, ix, -iy, iy, -0.20, wt, holes, Z_CWALL, Z_CWALLIN, Z_CWALL)
    rz = c['ridge']
    for sy in (-1, 1):                                                   # the gables (plaster), their tops under the roof
        g = [V(-ox, sy * oy, wt), V(ox, sy * oy, wt), V(0.0, sy * oy, rz - 0.15)]
        face(k, g, Z_CWALL, (0, sy, 0))
    face(k, [V(-ix, -iy, fl), V(ix, -iy, fl), V(ix, iy, fl), V(-ix, iy, fl)], Z_CFLOOR, (0, 0, 1))
    box6(k, (d0, -oy - 0.25, -0.20), (d1, -iy, fl), {'+z': Z_CPLINTH, '*': Z_CPLINTH}, skip=('-z',))   # the threshold stone
    face(k, [V(-ix, -iy, wt - 0.02), V(ix, -iy, wt - 0.02), V(ix, iy, wt - 0.02), V(-ix, iy, wt - 0.02)], Z_CCEIL, (0, 0, -1))
    for yy in np.arange(-iy + 0.5, iy, 1.0):                             # ceiling beams
        k.box(-ix, ix, yy - 0.06, yy + 0.06, wt - 0.16, wt - 0.02, Z_CBARGE)
    # the roof: shingles over boards on two planes, bargeboards, the eaves' fascia
    ex, ez = c['eaves']
    ry = c['roof_y']
    for sx in (-1, 1):
        a = [V(sx * ex, -ry, ez + 0.12), V(sx * ex, ry, ez + 0.12), V(0.0, ry, rz), V(0.0, -ry, rz)]
        up_ = V(sx * (rz - ez), 0, ex).normalized()
        face(k, a, Z_CROOF, up_)
        b = [p_ - V(0, 0, 0.12) for p_ in a]
        face(k, b, Z_CROOFIN, -up_)
        face(k, [a[0], a[1], b[1], b[0]], Z_CBARGE, (sx, 0, 0))
        for sy, (i0, i1) in ((-1, (0, 3)), (1, (1, 2))):
            face(k, [a[i0], a[i1], b[i1], b[i0]], Z_CBARGE, (0, sy, 0))
            bar(k, V(sx * (ex + 0.02), sy * (ry + 0.03), ez - 0.06), V(0.0, sy * (ry + 0.03), rz + 0.02), 0.04, 0.24, Z_CBARGE,
                up=(0, 0, 1))
    k.strip([V(0, -ry - 0.05, rz + 0.02), V(0, ry + 0.05, rz + 0.02)], V(0, 0, 1), 0.24, 0.03, Z_CBARGE, caps=True)
    # the bell turret: a boarded box with louvred openings and a small bell, the spire, the iron cross
    th, ty, tz0, tz1 = c['turret']
    box6(k, (-th, ty - th, tz0), (th, ty + th, tz1), Z_CTURRET)
    for sy in (-1, 1):                                                   # the sound openings (dark recesses, louvres)
        for zz in np.arange(tz1 - 0.65, tz1 - 0.18, 0.09):
            obox(k, V(0.0, ty + sy * (th + 0.012), zz + 0.02), (0.50, 0.05, 0.012), Z_CBARGE,
                 Matrix.Rotation(math.radians(sy * 35), 3, 'X'))
    for sx in (-1, 1):
        for zz in np.arange(tz1 - 0.65, tz1 - 0.18, 0.09):
            obox(k, V(sx * (th + 0.012), ty, zz + 0.02), (0.05, 0.50, 0.012), Z_CBARGE,
                 Matrix.Rotation(math.radians(-sx * 35), 3, 'Y'))
    for sx in (-1, 1):                                                   # corner boards
        for sy in (-1, 1):
            box6(k, (sx * th - 0.03, ty + sy * th - 0.03, tz0), (sx * th + 0.03, ty + sy * th + 0.03, tz1), Z_CBARGE)
    s0, s1 = c['spire']
    sb = th + 0.10
    base = [V(-sb, ty - sb, s0), V(sb, ty - sb, s0), V(sb, ty + sb, s0), V(-sb, ty + sb, s0)]
    apex = V(0.0, ty, s1)
    for i in range(4):
        j = (i + 1) % 4
        face(k, [base[i], base[j], apex], Z_CSPIRE, ((base[i] + base[j]) / 2 - V(0, ty, s0)).normalized() + V(0, 0, 0.6))
    face(k, list(reversed(base)), Z_CBARGE, (0, 0, -1))
    c0, c1 = c['cross']
    k.box(-0.025, 0.025, ty - 0.02, ty + 0.02, s1 - 0.05, c1, Z_CCROSS)
    k.box(-0.18, 0.18, ty - 0.02, ty + 0.02, 9.78, 9.82, Z_CCROSS)
    k.lathe(V(0, ty, c0 + 0.08), (0, 0, 1), [(0.0, 0.0), (0.0, 0.06), (0.06, 0.08), (0.12, 0.0)], Z_CCROSS, 10, cap0=False,
            cap1=False)
    # the windows: frames, glazing bars, the panes (M_GlassDirty)
    kg = kb('Chapel_Glass', 'glass')
    for sx in (-1, 1):
        xg = sx * (ox - 0.16)
        for ya, yb in c['windows']:
            for (a0, a1, z0, z1) in ((ya, ya + 0.05, wz0, wz1), (yb - 0.05, yb, wz0, wz1), (ya, yb, wz0, wz0 + 0.05),
                                     (ya, yb, wz1 - 0.05, wz1), ((ya + yb) / 2 - 0.02, (ya + yb) / 2 + 0.02, wz0, wz1),
                                     (ya, yb, (wz0 + wz1) / 2 - 0.02, (wz0 + wz1) / 2 + 0.02),
                                     (ya, yb, wz0 + (wz1 - wz0) * 0.75 - 0.015, wz0 + (wz1 - wz0) * 0.75 + 0.015)):
                box6(k, (xg - 0.03, a0, z0), (xg + 0.03, a1, z1), Z_CFRAME)
            kg.quad_uv(V(xg, (ya + yb) / 2, (wz0 + wz1) / 2), V(sx, 0, 0), yb - ya - 0.04, wz1 - wz0 - 0.04, (0, 0, 1, 1))
            box6(k, (sx * ox - (0.0 if sx > 0 else 0.06), ya - 0.05, wz0 - 0.07), (sx * ox + (0.06 if sx > 0 else 0.0), yb + 0.05, wz0 - 0.02),
                 Z_CPLINTH)                                              # the stone sills
    # the pews (two rows of four), the altar of stone with its cloth, the candles, the cross on the east wall
    for (xa, xb) in c['pews_x']:
        for yc in c['pews_y']:
            box6(k, (xa, yc - 0.175, 0.425), (xb, yc + 0.175, 0.475), Z_CPEW)
            box6(k, (xa, yc + 0.20, 0.60), (xb, yc + 0.24, 1.00), Z_CPEW)
            for xx in (xa + 0.04, xb - 0.04):
                box6(k, (xx - 0.025, yc - 0.17, fl), (xx + 0.025, yc + 0.24, 0.425), Z_CPEW)
                box6(k, (xx - 0.025, yc + 0.20, 0.475), (xx + 0.025, yc + 0.24, 1.00), Z_CPEW)
            box6(k, (xa + 0.06, yc - 0.40, fl + 0.05), (xb - 0.06, yc - 0.30, fl + 0.12), Z_CPEW)      # the kneeler
    ax0, ax1, ay0, ay1, az = c['altar']
    box6(k, (ax0, ay0, fl), (ax1, ay1, az), Z_CALTAR)
    cx0, cx1, cy0, cy1, cz = c['cloth']
    box6(k, (cx0, cy0, az), (cx1, cy1, cz), Z_CCLOTH)
    box6(k, (cx0 + 0.15, cy0 - 0.01, az - 0.45), (cx1 - 0.15, cy0, az), Z_CCLOTH)                     # its front drop
    kc = kb('Chapel_Flame', 'lens:candle')
    cyc = c['candle_y']
    for (xx, zt_, zt2) in c['candles']:
        k.lathe(V(xx, cyc, cz), (0, 0, 1), [(0.0, 0.045), (0.015, 0.045), (0.03, 0.016), (0.12, 0.014), (0.13, 0.03),
                                            (0.145, 0.03), (0.15, 0.012)], Z_CSTICK, 10, cap0=True, cap1=True)
        k.cyl(V(xx, cyc, cz + 0.15), V(xx, cyc, 1.28), 0.012, Z_CCANDLE, 8)
        for a in (0.0, math.pi / 2):                                     # the flame: two crossed quads (M_Candle)
            d_ = V(math.cos(a), math.sin(a), 0) * 0.008
            pts = [V(xx, cyc, 1.282) - d_, V(xx, cyc, 1.282) + d_, V(xx, cyc, 1.322) + d_ * 0.2, V(xx, cyc, 1.322) - d_ * 0.2]
            kc.poly(pts, 0.0, [(0, 0), (1, 0), (1, 1), (0, 1)])
            kc.poly(list(reversed(pts)), 0.0, [(0, 1), (1, 1), (1, 0), (0, 0)])
    ix0, ix1, iz0, iz1, iy_ = c['icon']
    box6(k, (-0.05, iy_ - 0.06, iz0), (0.05, iy_, iz1), Z_CICON)                                       # the cross
    box6(k, (-0.40, iy_ - 0.06, iz1 - 0.42), (0.40, iy_, iz1 - 0.32), Z_CICON)
    # the door (IX_ChapelDoor_8): planks with iron straps, a ring handle
    lf = c['leaf']
    kd = kb('IX_ChapelDoor_8', 'Chapel')
    hx_, x1_, yd = lf['hinge_x'], lf['x1'], lf['y']
    zd0, zd1 = lf['z']
    yf_ = yd - 0.025                                                     # the leaf's outer face
    box6(kd, (hx_ + 0.01, yf_, fl + 0.01), (x1_ - 0.01, yd + 0.045, zd1), Z_CDOOR)
    for zz in (fl + 0.35, 1.2, zd1 - 0.35):
        kd.box(hx_ + 0.06, x1_ - 0.20, yf_ - 0.008, yf_, zz - 0.03, zz + 0.03, Z_CIRON)
        for xx in np.arange(hx_ + 0.10, x1_ - 0.25, 0.22):
            kd.cyl(V(xx, yf_ - 0.008, zz), V(xx, yf_ - 0.015, zz), 0.012, Z_CIRON, 6)
    kd.tube([V(x1_ - 0.14 + 0.06 * math.cos(q), yf_ - 0.025, 1.05 + 0.06 * math.sin(q)) for q in np.linspace(0, TAU, 11)],
            0.008, Z_CIRON, 5, caps=False)
    kd.cyl(V(x1_ - 0.14, yf_ + 0.001, 1.11), V(x1_ - 0.14, yf_ - 0.025, 1.11), 0.02, Z_CIRON, 8)
    part('IX_ChapelDoor_8', 'hinge', (hx_, yd, lf['z'][0]), axis=(0, 0, -1), rng=(0, 100), parent='Chapel',
         note='the plank door: Update 3\'s hinge (vertical at x -0.56), opens out (-y) up to 100 deg')
    # the graves (Update 3's six): mounds, iron crosses leaning a little, their name plates
    rng = np.random.default_rng(31)
    for i, (gx, gy) in enumerate(c['graves']):
        mound = [superring(gx, gy + 0.70, 0.42 * s_, 0.75 * s_, z_, 4.0, 14) for s_, z_ in ((1.0, -0.05), (0.92, 0.10), (0.6, 0.18))]
        k.loft(mound, [Z_CGRAVE, Z_CGRAVE], cap1=Z_CGRAVE)
        tilt = Matrix.Rotation(rng.uniform(-0.08, 0.08), 3, 'X') @ Matrix.Rotation(rng.uniform(-0.06, 0.06), 3, 'Y')
        base = V(gx, gy - 0.02, 0.0)
        T = lambda q: base + tilt @ V(q)
        obox(k, T((0, 0, 0.605)), (0.05, 0.035, 1.41), Z_CIRON, tilt)
        obox(k, T((0, 0, 1.0)), (0.55, 0.035, 0.05), Z_CIRON, tilt)
        obox(k, T((0, -0.005, 1.0)), (0.16, 0.03, 0.12), Z_CCANDLE, tilt)                                     # the plate
        for sg in (-1, 1):                                               # the little roof over the cross
            obox(k, T((sg * 0.08, 0, 1.27)), (0.18, 0.08, 0.012), Z_CIRON, tilt @ Matrix.Rotation(math.radians(-sg * 25), 3, 'Y'))
    # the carved sign by the path on two posts (faces -y)
    kf = kb('Chapel_Sign', 'panel')
    sx_, sy_, sz_, sw_, sh_ = c['sign']
    for xx in (sx_ - sw_ / 2 + 0.06, sx_ + sw_ / 2 - 0.06):
        log_seg(k, (xx, sy_ + 0.06, -0.4), (xx, sy_ + 0.06, sz_ + sh_ / 2 + 0.06), 0.05, 0.045, Z_CSIGN, Z_CBARGE, seg=6, n=2,
                wob=0.04, seed=700 + int(xx * 10))
    sign_plate(k, kf, (sx_, sy_, sz_), sw_, sh_, uv('chapel'), back=0.04, zone=Z_CSIGN)
    part('Chapel', 'static', (0, 0, 0), note='forest chapel: plinth, plastered walls, shingled roof, bell turret, spire and '
                                             'cross, windows, pews, altar, candles, the cross on the east wall, the graves, '
                                             'the sign')
    part('Chapel_Glass', 'static', (0, 0, 2.05), parent='Chapel', note='the windows\' panes (M_GlassDirty)')
    part('Chapel_Flame', 'static', (0, cyc, 1.30), parent='Chapel',
         note='the candles\' flames (Update 3\'s M_Candle: they flicker with Light_candle; the halos at Update 3\'s places)')
    part('Chapel_Sign', 'static', (sx_, sy_, sz_), parent='Chapel', note='WALDKAPELLE / FOREST CHAPEL (panel)')


# ================================================================ the abandoned campsite
def rock(k, c, r, zone, seed, flat=0.6):
    """a field stone: a squashed, lumpy octahedral sphere half in the ground"""
    rng = np.random.default_rng(seed)
    rings = []
    for th in (0.0, 0.55, 1.05, 1.57):
        z = r * math.cos(th) * flat
        rr = r * math.sin(th)
        rings.append([V(c[0] + rr * (0.85 + 0.3 * rng.random()) * math.cos(TAU * j / 7 + seed),
                        c[1] + rr * (0.85 + 0.3 * rng.random()) * math.sin(TAU * j / 7 + seed), c[2] + z) for j in range(7)])
    rings = rings[::-1]                                                  # from the ground ring up
    k.loft(rings[:-1], [zone] * 2)
    top = V(c[0], c[1], c[2] + r * flat)
    for j in range(7):
        face(k, [rings[-2][j], rings[-2][(j + 1) % 7], top], zone, (rings[-2][j] + rings[-2][(j + 1) % 7]) / 2 - V(c[0], c[1], c[2]))


def campsite():
    cp = S.CAMP
    k = kb('Campsite', 'Small')
    # the collapsed tent: a draped two-sided sheet, a pole snapped across it, guy lines, pegs
    tx0, tx1, ty0, ty1 = cp['tent']
    nx, ny = 8, 6
    def h(x, y):
        u_, v_ = (x - tx0) / (tx1 - tx0), (y - ty0) / (ty1 - ty0)
        return 0.09 + 0.42 * math.exp(-((u_ - 0.30) / 0.22) ** 2 - ((v_ - 0.52) / 0.35) ** 2) + \
            0.18 * math.exp(-((u_ - 0.62) / 0.15) ** 2 - ((v_ - 0.3) / 0.2) ** 2) + 0.03 * math.sin(u_ * 17 + v_ * 9)
    grid = [[V(tx0 + (tx1 - tx0) * i / nx, ty0 + (ty1 - ty0) * j / ny, 0.0) for i in range(nx + 1)] for j in range(ny + 1)]
    for row in grid:
        for p in row:
            p.z = h(p.x, p.y)
    for j in range(ny):
        for i in range(nx):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            face(k, q, Z_XTENT, (0, 0, 1))
    # the hem: the sheet's edge folds down into the ground all round (nothing to see under it: one-sided is enough)
    ring_ = [grid[0][i] for i in range(nx + 1)] + [grid[j][nx] for j in range(1, ny + 1)] + \
            [grid[ny][i] for i in range(nx - 1, -1, -1)] + [grid[j][0] for j in range(ny - 1, 0, -1)]
    cx_, cy_ = (tx0 + tx1) / 2, (ty0 + ty1) / 2
    for a_, b_ in zip(ring_, ring_[1:] + ring_[:1]):
        out_ = V((a_.x + b_.x) / 2 - cx_, (a_.y + b_.y) / 2 - cy_, 0.0)
        face(k, [a_, b_, V(b_.x, b_.y, -0.03), V(a_.x, a_.y, -0.03)], Z_XTENT, out_)
    k.tube([V(-0.40, -0.95, 0.02), V(-0.40, -0.55, 0.40), V(-0.42, -0.10, 0.56), V(-0.36, 0.30, 0.50)], 0.008, Z_XPOLE, 5)
    k.tube([V(-0.30, 0.34, 0.48), V(-0.10, 0.62, 0.30), V(0.05, 0.92, 0.02)], 0.008, Z_XPOLE, 5)
    for (a, b) in (((tx0, ty0, 0.06), (tx0 - 0.45, ty0 - 0.35, 0.0)), ((tx1, ty1, 0.05), (tx1 + 0.40, ty1 + 0.30, 0.0))):
        k.tube([V(a), V(b)], 0.004, Z_XPOLE, 3, caps=False)
        rod(k, V(b) + V(0, 0, -0.08), V(b) + V(0, 0, 0.06), 0.008, Z_XPOLE, seg=4)
    # the fire ring: stones, ash, charred logs, the pot on a stone
    fx, fy, fr = cp['fire']
    face(k, [V(fx + 0.36 * math.cos(TAU * j / 12), fy + 0.36 * math.sin(TAU * j / 12), 0.045) for j in range(12)], Z_XASH,
         (0, 0, 1))
    for j in range(9):
        a = TAU * j / 9 + 0.2
        rock(k, (fx + fr * math.cos(a), fy + fr * math.sin(a), 0.0), 0.10 + 0.03 * ((j * 7) % 3) / 2, Z_XSTONE, 40 + j)
    for j, a in enumerate((0.3, 1.9, 3.4, 4.9)):
        r0, r1 = 0.05, 0.30
        log_seg(k, (fx + r0 * math.cos(a), fy + r0 * math.sin(a), 0.09), (fx + r1 * math.cos(a), fy + r1 * math.sin(a), 0.07),
                0.04, 0.035, Z_XCHAR, Z_XASH, seg=6, n=1, wob=0.08, seed=60 + j)
    a_p = TAU * 1 / 9 + 0.2                                              # the pot on the ring's second stone
    px, py, pz_ = fx + fr * math.cos(a_p), fy + fr * math.sin(a_p), 0.06
    k.lathe(V(px, py, pz_), (0, 0, 1), [(0.0, 0.0), (0.0, 0.085), (0.01, 0.10), (0.15, 0.10), (0.16, 0.105), (0.16, 0.095),
                                        (0.02, 0.085)], Z_XPOT, 12, cap0=False, cap1=False)
    k.tube([V(px - 0.10, py, pz_ + 0.14), V(px, py + 0.02, pz_ + 0.24), V(px + 0.10, py, pz_ + 0.14)], 0.004, Z_XPOT, 4)
    # the camp chair, tipped over on its back: an X frame, the blue seat and back
    chx, chy = cp['chair']
    R = Matrix.Rotation(math.radians(-100), 3, 'X')
    O = V(chx, chy, 0.38)
    T = lambda q: O + R @ V(q)
    for sx in (-1, 1):
        rod(k, T((sx * 0.26, -0.25, -0.25)), T((sx * 0.26, 0.25, 0.20)), 0.012, Z_XCFRAME, seg=5)
        rod(k, T((sx * 0.26, 0.25, -0.25)), T((sx * 0.26, -0.25, 0.20)), 0.012, Z_XCFRAME, seg=5)
        rod(k, T((sx * 0.26, 0.20, 0.20)), T((sx * 0.26, 0.28, 0.70)), 0.012, Z_XCFRAME, seg=5)
    seat = [T((-0.26, -0.22, 0.18)), T((0.26, -0.22, 0.18)), T((0.26, 0.22, 0.12)), T((-0.26, 0.22, 0.12))]
    back_ = [T((-0.26, 0.22, 0.20)), T((0.26, 0.22, 0.20)), T((0.26, 0.29, 0.68)), T((-0.26, 0.29, 0.68))]
    for q in (seat, back_):                                              # two-sided fabric: the back face 2 mm off
        n_ = K.newell(q).normalized()
        face(k, q, Z_XCHAIR, None)
        face(k, [p_ - n_ * 0.002 for p_ in reversed(q)], Z_XCHAIR, None)
    # the rucksack lying on its side, the bedroll, a mug, the bottle, the torch on the ground
    kx, ky = cp['pack']
    VM.rbox(k, V(kx + 0.05, ky, 0.20), (0.40, 0.30, 0.34), Z_XPACK, r=0.08, ch=0.03, axis='x')
    VM.rbox(k, V(kx + 0.18, ky - 0.17, 0.15), (0.18, 0.06, 0.16), Z_XPACK, r=0.03, ch=0.015, axis='x')
    k.cyl(V(kx - 0.10, ky + 0.12, 0.13), V(kx - 0.10, ky + 0.34, 0.13), 0.10, Z_XROLL, 10)          # the bedroll
    k.lathe(V(2.70, 0.55, 0.03), (0, 0, 1), [(0.0, 0.0), (0.0, 0.04), (0.09, 0.042), (0.09, 0.036), (0.01, 0.034)], Z_XMUG, 10,
            cap0=False, cap1=False)
    bx, by = cp['bottle']
    k.lathe(V(bx - 0.10, by, 0.07), (1, 0, 0), [(0.0, 0.0), (0.0, 0.038), (0.14, 0.04), (0.17, 0.02), (0.22, 0.014), (0.22, 0.0)],
            Z_XBOTTLE, 10, cap0=False, cap1=False)
    d_ = V(0.86083, -0.50637, 0.05064).normalized()                     # the torch points where Update 3's light shines
    lc = V(0.598, -1.716, 0.058)
    k.cyl(lc - d_ * 0.25, lc - d_ * 0.085, 0.030, Z_XTORCH, 10)
    k.lathe(lc - d_ * 0.085, d_, [(0.0, 0.031), (0.03, 0.043), (0.08, 0.044), (0.085, 0.039)], Z_XTORCH, 12, cap0=False,
            cap1=False)
    k.box_m(lc - d_ * 0.16 + V(0, 0, 0.030), (0.03, 0.02, 0.01), Z_XCFRAME, Matrix.Rotation(math.atan2(d_.y, d_.x), 3, 'Z'))
    kl = kb('Campsite_Lens', 'lens:headlight')
    ring, _ = kl.ring_pts(lc, d_, 0.039, 12)
    face(kl, ring, 0.0, d_)
    part('Campsite', 'static', (0, 0, 0), note='the abandoned camp: the collapsed tent, the fire ring and the pot, the tipped '
                                               'chair, the rucksack and bedroll, a mug, a bottle, the torch')
    part('Campsite_Lens', 'static', tuple(lc), parent='Campsite',
         note='the torch\'s glass (Update 3\'s M_Headlight; its light and halo at Update 3\'s places)')


def build_far():
    for n in ('Dish_1', 'Dish_2', 'Dish_3', 'Dish_4', 'Dish_5'):
        dish(n)
    radome()
    relaymast()
    meteostation()
    lookout()
    pumphouse()
    chapel()
    cabin()
    campsite()
