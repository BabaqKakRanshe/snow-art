"""The Forest base's remaining prefabs in the generator shed's style (Update 3's names, pivots, sizes, places, lights):
  Hatch     - the shaft hatch: a concrete collar with a galvanised angle frame, a chequer-plate lid on two hinges
              (IX_HatchLid_94, locked: hasp, staple and padlock), the dark shaft with the top of its ladder, a mushroom
              vent, the SCHACHT sign on two posts;
  Helipad   - the pad (the painted H and the dashed ring are in the concrete's atlas), eight edge lights (Update 3's
              M_Lamp_WarmOff domes), the windsock on its mast with the tilting hinge, the swivel and the hoop, the sign,
              a fire-extinguisher box on a post, a tarped pallet;
  RadioMast - the 60 m guyed lattice mast in seven red and white bands: legs on base plates and footings, horizontals
              and diagonals, the ladder up the -y face, the cable tray with three feeders, VHF dipoles at 55 / 58 m,
              beacons on brackets at 20 / 40 m and on top (Update 3's M_Light_Red), the lightning rod, guys at
              21 / 42 / 57 m to three anchor blocks with turnbuckles, the VORSICHT EISFALL plate;
  Crates    - an olive transport chest with a case on top and a small case beside it, two pine crates (one open, straw);
  LogPile   - nine spruce logs (Update 3's) on two skids between four stakes;
  LightPole - galvanised yard light on a concrete footing: base plate and bolts, door, outreach arm, the luminaire
              (Update 3's M_Lamp_SodiumOff lens under the light and the halo);
  PowerPole - the yard's trafo pole type: creosoted pole, wooden crossarm, braces, three pin insulators (their tops at
              Update 3's 8.72: the wires end there), earth wire, plates;
  FenceChain - a 3 m section of the base fence (213 on the map: lean): post and cap, top rail, chain-link and the
              barbed strands over the outrigger (cut-outs);
  OldFence, OldFence_b, OldFence_c - the old boundary fence (294 on the map: lean): a weathered post (Update 3's lean)
              and four slack rusty strands from the previous post (c: one snapped, both ends curled down);
  Forest_Wires - the overhead line (a world model, the map frame): twelve conductors on catenaries trafo -> poles
              1 -> 2 and trafo -> 3 -> 4 between Update 3's insulator tops, cable risers down poles 2 and 4.
Frames: each prefab its own (Update 3's FBX after import): x / y / z, z up, metres; Unity prefab-local (-x, z, -y).
Faces carry a float 'zone' (atlases Props, Helipad, Mast, Poles, Fence) or explicit 'PSX' UVs (panel: the sign faces;
chainlink / barbed / rust: tiled cut-outs; lens:sodium / warm / red: Update 3's lamp materials); Forest_Wires' zone is
its material: 0 M_Cable, 1 M_Galvanized, 2 M_Enamel."""
import math
import numpy as np
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, socket, face, box6, KBS, CONTRACT
import van3_mech as VM
from road_kit import bar, rod, log_seg, bolt, rrect_xz
import base_spec as S
import base_tex as BT

TAU = 2 * math.pi
uv = BT.uv

# ---------------------------------------------------------------- zones (1000+)
# Props atlas: the hatch, the crates, the log pile
(Z_HCONC, Z_HFRAME, Z_HLID, Z_HHINGE, Z_HLOCK, Z_HVENT, Z_HSHAFT, Z_HRUNG, Z_SPOST, Z_SCAP, Z_SBACK, Z_SRAIL,
 Z_SCLAMP) = range(1000, 1013)
(Z_COLIVE, Z_CSTEEL, Z_CROPE, Z_CPINE, Z_CSTRAW, Z_CCASE, Z_CINNER) = range(1015, 1022)
(Z_LBARK, Z_LEND, Z_LSKID, Z_LSTAKE) = range(1023, 1027)
# Helipad atlas
(Z_PAD, Z_PADSIDE, Z_PFOOT, Z_LSTALK, Z_LBODY, Z_SMAST, Z_SFRAME, Z_SOCKR, Z_SOCKW, Z_PALLET, Z_TARP, Z_ROPE,
 Z_EXTBOX, Z_EXTLBL, Z_HPOST, Z_HBACK) = range(1030, 1046)
# Mast atlas
(Z_MLEG, Z_MBAR, Z_MFOOT, Z_MPLATE, Z_MLADDER, Z_MBRK, Z_MBODY, Z_MGUY, Z_MANCH, Z_MTURN, Z_MTRAY, Z_MCOAX, Z_MANT,
 Z_MROD, Z_MBACK) = range(1050, 1065)
# Poles atlas
(Z_LPOLE, Z_LDOOR, Z_LFOOT, Z_LBOLT, Z_LHEAD, Z_PPOLE, Z_PXARM, Z_PGALV, Z_PPORC, Z_PEARTH, Z_PPLATE) = range(1070, 1081)
# Fence atlas
(Z_FPOST, Z_FRAIL, Z_FCLAMP, Z_OPOST, Z_OTOP) = range(1085, 1090)

DRAFT_COL = {
    Z_HCONC: (148, 146, 138), Z_HFRAME: (150, 154, 150), Z_HLID: (92, 96, 96), Z_HHINGE: (50, 48, 46), Z_HLOCK: (168, 140, 70),
    Z_HVENT: (150, 154, 150), Z_HSHAFT: (40, 38, 36), Z_HRUNG: (90, 70, 50), Z_SPOST: (160, 164, 160), Z_SCAP: (60, 62, 64),
    Z_SBACK: (128, 130, 126), Z_SRAIL: (170, 172, 170), Z_SCLAMP: (150, 152, 150),
    Z_COLIVE: (96, 96, 64), Z_CSTEEL: (70, 72, 64), Z_CROPE: (150, 132, 96), Z_CPINE: (176, 150, 108), Z_CSTRAW: (196, 170, 104),
    Z_CCASE: (84, 90, 64), Z_CINNER: (120, 100, 70),
    Z_LBARK: (92, 84, 76), Z_LEND: (200, 172, 128), Z_LSKID: (110, 100, 86), Z_LSTAKE: (104, 94, 80),
    Z_PAD: (150, 148, 140), Z_PADSIDE: (130, 128, 120), Z_PFOOT: (140, 138, 130), Z_LSTALK: (150, 154, 150),
    Z_LBODY: (40, 40, 40), Z_SMAST: (200, 200, 196), Z_SFRAME: (150, 154, 150), Z_SOCKR: (190, 44, 34),
    Z_SOCKW: (220, 220, 214), Z_PALLET: (160, 136, 100), Z_TARP: (70, 86, 64), Z_ROPE: (170, 150, 110), Z_EXTBOX: (180, 36, 30),
    Z_EXTLBL: (220, 216, 206), Z_HPOST: (160, 164, 160), Z_HBACK: (128, 130, 126),
    Z_MLEG: (190, 60, 44), Z_MBAR: (190, 60, 44), Z_MFOOT: (140, 138, 130), Z_MPLATE: (150, 154, 150), Z_MLADDER: (150, 154, 150),
    Z_MBRK: (150, 154, 150), Z_MBODY: (40, 40, 40), Z_MGUY: (120, 124, 124), Z_MANCH: (140, 138, 130), Z_MTURN: (130, 132, 128),
    Z_MTRAY: (150, 154, 150), Z_MCOAX: (30, 30, 30), Z_MANT: (180, 182, 180), Z_MROD: (150, 110, 70), Z_MBACK: (128, 130, 126),
    Z_LPOLE: (156, 160, 158), Z_LDOOR: (150, 154, 150), Z_LFOOT: (140, 138, 130), Z_LBOLT: (90, 92, 92), Z_LHEAD: (120, 124, 126),
    Z_PPOLE: (92, 70, 50), Z_PXARM: (100, 82, 60), Z_PGALV: (150, 154, 150), Z_PPORC: (120, 60, 34), Z_PEARTH: (160, 100, 60),
    Z_PPLATE: (200, 200, 196),
    Z_FPOST: (156, 160, 158), Z_FRAIL: (156, 160, 158), Z_FCLAMP: (140, 144, 140), Z_OPOST: (110, 104, 92), Z_OTOP: (140, 130, 112)}
PROPS_ZONES = list(range(1000, 1027))
HELI_ZONES = list(range(1030, 1046))
MAST_ZONES = list(range(1050, 1065))
POLES_ZONES = list(range(1070, 1081))
FENCE_ZONES = list(range(1085, 1090))

# the crates (Update 3's boxes: A an olive chest 1.0 x 0.6 turned 14 deg, B a case on it, D and E pine crates; C new)
CRATES = dict(A=dict(c=(0.80, 0.24), size=(1.00, 0.60, 0.75), yaw=14.0),
              B=dict(c=(0.80, 0.24), size=(0.52, 0.40, 0.34), yaw=6.0, z=0.75),
              C=dict(c=(0.86, -0.52), size=(0.48, 0.30, 0.30), yaw=-18.0),
              D=dict(c=(-0.87, 0.12), size=(1.00, 0.75, 0.74), yaw=-8.0),
              E=dict(c=(-0.18, -0.53), size=(0.90, 0.60, 0.70), yaw=25.0))
LOG_RISE = 0.10                                          # the pile lies on two skids


def V(*a):
    return Vector(a[0]) if len(a) == 1 else Vector(a)


def sq(r, z, cx=0.0, cy=0.0):
    """a square ring (half size r) counter-clockwise from +z"""
    return [V(cx - r, cy - r, z), V(cx + r, cy - r, z), V(cx + r, cy + r, z), V(cx - r, cy + r, z)]


def chamfer_box(k, lo, hi, ch, zone, bottom=False):
    """box lo..hi with its four top edges chamfered by ch (concrete blocks, footings); no bottom face (in the ground)"""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    rb = [V(x0, y0, z0), V(x1, y0, z0), V(x1, y1, z0), V(x0, y1, z0)]
    rm = [V(x0, y0, z1 - ch), V(x1, y0, z1 - ch), V(x1, y1, z1 - ch), V(x0, y1, z1 - ch)]
    rt = [V(x0 + ch, y0 + ch, z1), V(x1 - ch, y0 + ch, z1), V(x1 - ch, y1 - ch, z1), V(x0 + ch, y1 - ch, z1)]
    k.loft([rb, rm, rt], [zone, zone], cap0=zone if bottom else None, cap1=zone)


def superring(cx, cy, hx, hy, z, p=4.0, n=16):
    """a superellipse ring (half sizes hx, hy) counter-clockwise from +z"""
    out = []
    for i in range(n):
        a = TAU * i / n
        c, s = math.cos(a), math.sin(a)
        out.append(V(cx + hx * math.copysign(abs(c) ** (2 / p), c), cy + hy * math.copysign(abs(s) ** (2 / p), s), z))
    return out


def sign_plate(kp, kf, c, w, h, region, back=0.014, zone=Z_SBACK):
    """an aluminium sign plate: the face (panel UVs, its own KB) at y = c.y facing -y, the folded edge and the back"""
    cx, cy, cz = c
    ol = rrect_xz(cx - w / 2, cx + w / 2, cz - h / 2, cz + h / 2, 0.018, 3)
    u0, v0, u1, v1 = region
    pts = [V(x, cy, z) for x, z in ol]
    uvs = [(u0 + (x - (cx - w / 2)) / w * (u1 - u0), v0 + (z - (cz - h / 2)) / h * (v1 - v0)) for x, z in ol]
    face(kf, pts, 0.0, (0, -1, 0), uvs)
    bk = [V(x, cy + back, z) for x, z in ol]
    n = len(ol)
    for i in range(n):
        j = (i + 1) % n
        face(kp, [pts[i], pts[j], bk[j], bk[i]], zone, V(((ol[i][0] + ol[j][0]) / 2) - cx, 0, ((ol[i][1] + ol[j][1]) / 2) - cz))
    face(kp, bk, zone, (0, 1, 0))


def sign_post(k, x, y, top, bot=-0.40, r=0.030, zone=Z_SPOST, cap=Z_SCAP):
    rod(k, (x, y, bot), (x, y, top - 0.012), r, zone, seg=8, caps=False)
    k.lathe(V(x, y, top - 0.012), (0, 0, 1), [(0.0, r + 0.003), (0.018, r + 0.003), (0.026, r * 0.70), (0.032, 0.0)],
            cap, 8, cap0=True, cap1=False)


def sign_on_posts(k, kf, xs, y, cz, w, h, region, bot=-0.40, zp=Z_SPOST, zb=Z_SBACK, zc=Z_SCAP):
    """a sign plate (face at y, to -y) on two galvanised posts behind it, two hat rails, tube clamps"""
    for x in xs:
        sign_post(k, x, y + 0.045, cz + h / 2 + 0.03, bot, zone=zp, cap=zc)
    sign_plate(k, kf, ((xs[0] + xs[1]) / 2, y, cz), w, h, region, zone=zb)
    for zr in (cz - h * 0.25, cz + h * 0.25):
        k.box(xs[0] - 0.08, xs[1] + 0.08, y + 0.014, y + 0.018, zr - 0.014, zr + 0.014, zb)
        for x in xs:
            rod(k, (x, y + 0.045, zr - 0.012), (x, y + 0.045, zr + 0.012), 0.034, zp, seg=8)


# ================================================================ the shaft hatch
def hatch():
    h = S.HATCH
    k = kb('Hatch', 'Props')
    c, top, ch = h['collar'], h['top'], h['chamfer']
    fo, fi = h['frame_out'], h['frame_in']
    # the collar: walls and the chamfered top edge, the top up to the frame (the walls go on into the ground)
    rt = sq(c - ch, top)
    k.loft([sq(c, h['bottom']), sq(c, top - ch), rt], [Z_HCONC, Z_HCONC])
    rf = sq(fo, top)
    for i in range(4):
        j = (i + 1) % 4
        face(k, [rt[i], rt[j], rf[j], rf[i]], Z_HCONC, (0, 0, 1))
    # the galvanised angle frame: the flange on the concrete, its leg down into the shaft
    zf = top + 0.012
    rfo, rfi, leg = sq(fo, zf), sq(fi, zf), sq(fi, top - 0.10)
    for i in range(4):
        j = (i + 1) % 4
        m = (rf[i] + rf[j]) / 2
        out = V(m.x, m.y, 0)
        face(k, [rfo[i], rfo[j], rfi[j], rfi[i]], Z_HFRAME, (0, 0, 1))
        face(k, [rf[i], rf[j], rfo[j], rfo[i]], Z_HFRAME, out)
        face(k, [rfi[i], rfi[j], leg[j], leg[i]], Z_HFRAME, -out)
    # the shaft: dark concrete walls down to a black floor just above the terrain (the terrain has no hole: the shaft's
    # depth is painted, darker downward), the top of the ladder on the +y wall
    zb = h['shaft_floor']
    low = sq(fi, zb)
    for i in range(4):
        j = (i + 1) % 4
        m = (leg[i] + leg[j]) / 2
        face(k, [leg[i], leg[j], low[j], low[i]], Z_HSHAFT, -V(m.x, m.y, 0))
    face(k, low, Z_HSHAFT, (0, 0, 1))
    ly = fi - 0.10
    for xr in (-0.22, 0.22):
        bar(k, (xr, ly, zb), (xr, ly, top - 0.06), 0.05, 0.012, Z_HRUNG, up=(1, 0, 0), caps=False)
        bar(k, (xr, ly + 0.025, top - 0.13), (xr, fi, top - 0.13), 0.04, 0.008, Z_HRUNG, up=(0, 0, 1))
    for z in np.arange(zb + 0.12, top - 0.10, 0.28):
        rod(k, (-0.22, ly, z), (0.22, ly, z), 0.012, Z_HRUNG, seg=6, caps=False)
    # the hinges: their knuckles on the lid's axis (the lid's knuckles between them), the leaves down the frame's leg
    # inside the opening - below the axis, out of the lid's swing (the lid opens 100 deg about its bottom edge)
    px, _, pz = h['pivot']
    for y0, y1 in ((-0.66, -0.50), (0.50, 0.66)):
        k.box(px - 0.012, px - 0.004, y0, y1, pz - 0.13, pz - 0.016, Z_HHINGE)
        rod(k, (px, y0, pz), (px, y1, pz), 0.018, Z_HHINGE, seg=8)
        for yy in (y0 + 0.04, y1 - 0.04):
            bolt(k, (px - 0.004, yy, pz - 0.085), (1, 0, 0), 0.009, 0.005, Z_HHINGE)
    # the staple on the collar by the lid's free edge, the padlock through it (locked, as Update 3)
    sx = h['staple_x']
    k.box(sx - 0.03, sx + 0.03, -0.045, 0.045, top, top + 0.008, Z_HHINGE)
    for yy in (-0.02, 0.02):
        rod(k, (sx, yy, top + 0.006), (sx, yy, h['staple_top']), 0.008, Z_HHINGE, seg=6, caps=False)
    rod(k, (sx, -0.028, h['staple_top']), (sx, 0.028, h['staple_top']), 0.008, Z_HHINGE, seg=6)
    lz = h['staple_top'] - 0.088                                       # the padlock's body centre
    VM.rbox(k, V(sx, 0.0, lz), (0.060, 0.026, 0.050), Z_HLOCK, r=0.006, ch=0.003)
    k.tube([V(sx - 0.018, 0.0, lz + 0.022), V(sx - 0.018, 0.0, lz + 0.060), V(sx, 0.0, lz + 0.074),
            V(sx + 0.018, 0.0, lz + 0.060), V(sx + 0.018, 0.0, lz + 0.022)], 0.0055, Z_HHINGE, 6, caps=False)
    # the mushroom vent
    vx, vy = h['vent']
    vt = h['vent_top'] - top
    k.lathe(V(vx, vy, top), (0, 0, 1), [(0.0, 0.10), (0.012, 0.10), (0.012, 0.058), (vt - 0.06, 0.055), (vt - 0.06, 0.13),
                                        (vt - 0.03, 0.13), (vt, 0.06), (vt + 0.012, 0.0)], Z_HVENT, 10, cap0=False)
    for a in range(4):
        q = a * TAU / 4 + 0.4
        bolt(k, (vx + 0.08 * math.cos(q), vy + 0.08 * math.sin(q), top + 0.012), (0, 0, 1), 0.010, 0.008, Z_HHINGE)
    # the SCHACHT sign on two posts by the hatch (Update 3's place)
    kf = kb('Hatch_Sign', 'panel')
    cx, cz, w_, h_ = h['sign']
    sign_on_posts(k, kf, h['sign_posts'], h['sign_y'], cz, w_, h_, uv('hatch'))
    part('Hatch', 'static', (0, 0, 0), note='the shaft hatch: concrete collar, frame, shaft, vent, hinges, staple and padlock '
                                             '(locked), the SCHACHT sign')
    part('Hatch_Sign', 'static', (cx, h['sign_y'], cz), parent='Hatch', note='the sign face (panel atlas)')
    # the lid (IX_HatchLid_94): a chequer-plate slab, strap hinges with their knuckles on the axis, a fold-flat ring
    # handle, the hasp over the staple
    L = kb('IX_HatchLid_94', 'Props')
    l, lt, ls = h['lid'], h['lid_top'], h['lid_skirt']
    g_ = h['lid_gap']                                                   # the slab's hinge edge clear of the axis: open
    box6(L, (-l + g_, -l, ls), (l, l, lt), Z_HLID)                      # at 100 deg it stays above the frame
    for y0, y1 in ((-0.50, -0.34), (0.34, 0.50)):
        L.box(px + g_ + 0.03, px + 0.30, y0, y1, lt, lt + 0.006, Z_HHINGE)
        bar(L, (px + 0.012, (y0 + y1) / 2, pz + 0.012), (px + g_ + 0.03, (y0 + y1) / 2, lt + 0.003), 0.006, y1 - y0,
            Z_HHINGE, up=(0, 1, 0))                                     # cranked from the knuckle to the lid's top
        rod(L, (px, y0, pz), (px, y1, pz), 0.018, Z_HHINGE, seg=8)
        for xx in (px + 0.12, px + 0.24):
            bolt(L, (xx, (y0 + y1) / 2, lt + 0.006), (0, 0, 1), 0.009, 0.005, Z_HHINGE)
    hx = h['handle_x']
    L.tube([V(hx - 0.06, -0.10, lt + 0.008), V(hx + 0.06, -0.10, lt + 0.008), V(hx + 0.10, 0.0, lt + 0.008),
            V(hx + 0.06, 0.10, lt + 0.008), V(hx - 0.06, 0.10, lt + 0.008)], 0.009, Z_HHINGE, 6)
    for yy in (-0.10, 0.10):
        L.box(hx - 0.09, hx - 0.05, yy - 0.015, yy + 0.015, lt, lt + 0.012, Z_HHINGE)
    L.box(l - 0.12, l + 0.006, -0.035, 0.035, lt, lt + 0.006, Z_HHINGE)              # the hasp: over the edge, down
    L.box(l, l + 0.006, -0.035, 0.035, ls + 0.005, lt, Z_HHINGE)                     # the side, out over the staple
    L.box(l + 0.006, sx + 0.065, -0.035, 0.035, zf + 0.001, zf + 0.008, Z_HHINGE)
    part('IX_HatchLid_94', 'hinge', h['pivot'], axis=(0, -1, 0), rng=(0, 100), parent='Hatch', locked=True,
         note='the shaft lid: the hinge along y at x -0.90, z 0.51 (Update 3\'s), opens up to 100 deg; locked (the padlock '
              'on the staple)')


# ================================================================ the crates
def _box_lid(k, T, R, sx, sy, sz, zone, lip=True, ch=0.014):
    """a chest: chamfered top edges, a proud lid lip band 0.10 under the top"""
    rings = []
    for z, d in ((0.0, 0.0), (sz - ch, 0.0), (sz, ch)):
        rings.append([T((-sx / 2 + d, -sy / 2 + d, z)), T((sx / 2 - d, -sy / 2 + d, z)), T((sx / 2 - d, sy / 2 - d, z)),
                      T((-sx / 2 + d, sy / 2 - d, z))])
    k.loft(rings, [zone, zone], cap1=zone)
    if lip:
        e = 0.008
        z0, z1 = sz - 0.13, sz - 0.10
        ring = lambda z, d: [T((-sx / 2 - d, -sy / 2 - d, z)), T((sx / 2 + d, -sy / 2 - d, z)), T((sx / 2 + d, sy / 2 + d, z)),
                             T((-sx / 2 - d, sy / 2 + d, z))]
        inner0, inner1, outer0, outer1 = ring(z0, 0.0), ring(z1, 0.0), ring(z0, e), ring(z1, e)
        k.loft([outer0, outer1], [zone])
        for i in range(4):
            j = (i + 1) % 4
            face(k, [inner1[i], inner1[j], outer1[j], outer1[i]], zone, (0, 0, 1))
            face(k, [inner0[i], inner0[j], outer0[j], outer0[i]], zone, (0, 0, -1))


def _chest(k, d, zone, handles=True, corners=True, hasps=True, carry=False):
    cx, cy = d['c']
    sx, sy, sz = d['size']
    z0 = d.get('z', 0.0)
    R = Matrix.Rotation(math.radians(d['yaw']), 3, 'Z')
    T = lambda p: V(cx, cy, z0) + R @ V(p)
    _box_lid(k, T, R, sx, sy, sz, zone)
    if corners:                                                          # pressed steel corner caps
        for xs in (-1, 1):
            for ys in (-1, 1):
                for zz in (0.032, sz - 0.032):
                    k.box_m(T((xs * (sx / 2 - 0.028), ys * (sy / 2 - 0.028), zz)), (0.064, 0.064, 0.068), Z_CSTEEL, R)
    if handles:                                                          # rope handles in two cleats at the ends
        for xs in (-1, 1):
            zh = sz * 0.60
            for yy in (-0.11, 0.11):
                k.box_m(T((xs * (sx / 2 + 0.006), yy, zh)), (0.012, 0.035, 0.05), Z_CSTEEL, R)
            k.tube([T((xs * (sx / 2 + 0.012), -0.11, zh)), T((xs * (sx / 2 + 0.034), 0.0, zh - 0.07)),
                    T((xs * (sx / 2 + 0.012), 0.11, zh))], 0.011, Z_CROPE, 6)
    if hasps:                                                            # two hasps on the front
        for xx in (-sx * 0.28, sx * 0.28):
            k.box_m(T((xx, -sy / 2 - 0.006, sz - 0.11)), (0.05, 0.012, 0.10), Z_CSTEEL, R)
    if carry:                                                            # a folding carry handle on the lid
        c = T((0, 0, sz))
        k.tube([c + R @ V(-0.10, 0, 0.004), c + R @ V(-0.08, 0, 0.040), c + R @ V(0.08, 0, 0.040), c + R @ V(0.10, 0, 0.004)],
               0.010, Z_CSTEEL, 6)
        for xx in (-0.11, 0.11):
            k.box_m(c + R @ V(xx, 0, 0.006), (0.04, 0.03, 0.012), Z_CSTEEL, R)


def _pine(k, d, open_=False):
    """a pine crate: board sides, battens round the edges; open: the lid leans on its back, straw inside"""
    cx, cy = d['c']
    sx, sy, sz = d['size']
    R = Matrix.Rotation(math.radians(d['yaw']), 3, 'Z')
    T = lambda p: V(cx, cy, 0.0) + R @ V(p)
    ring = lambda z, e=0.0: [T((-sx / 2 - e, -sy / 2 - e, z)), T((sx / 2 + e, -sy / 2 - e, z)), T((sx / 2 + e, sy / 2 + e, z)),
                             T((-sx / 2 - e, sy / 2 + e, z))]
    k.loft([ring(0.0), ring(sz)], [Z_CPINE], cap1=None if open_ else Z_CPINE)
    for xs in (-1, 1):                                                   # the battens: vertical at the corners, rails
        for ys in (-1, 1):
            k.box_m(T((xs * (sx / 2 - 0.035), ys * (sy / 2 + 0.010), sz / 2)), (0.07, 0.02, sz), Z_CPINE, R)
            k.box_m(T((xs * (sx / 2 + 0.010), ys * (sy / 2 - 0.035), sz / 2)), (0.02, 0.07, sz), Z_CPINE, R)
        k.box_m(T((xs * (sx / 2 + 0.010), 0, sz - 0.04)), (0.02, sy - 0.14, 0.07), Z_CPINE, R)
        k.box_m(T((xs * (sx / 2 + 0.010), 0, 0.05)), (0.02, sy - 0.14, 0.07), Z_CPINE, R)
    for ys in (-1, 1):
        k.box_m(T((0, ys * (sy / 2 + 0.010), sz - 0.04)), (sx - 0.14, 0.02, 0.07), Z_CPINE, R)
        k.box_m(T((0, ys * (sy / 2 + 0.010), 0.05)), (sx - 0.14, 0.02, 0.07), Z_CPINE, R)
    if not open_:
        for xx in (-sx / 2 + 0.07, 0.0, sx / 2 - 0.07):                  # the lid's cleats
            k.box_m(T((xx, 0, sz + 0.010)), (0.07, sy - 0.04, 0.02), Z_CPINE, R)
        return
    w = 0.018                                                            # the walls' thickness at the open top
    inner = [T((-sx / 2 + w, -sy / 2 + w, sz)), T((sx / 2 - w, -sy / 2 + w, sz)), T((sx / 2 - w, sy / 2 - w, sz)),
             T((-sx / 2 + w, sy / 2 - w, sz))]
    outer = ring(sz)
    for i in range(4):
        j = (i + 1) % 4
        face(k, [outer[i], outer[j], inner[j], inner[i]], Z_CPINE, (0, 0, 1))
    deep = [p - V(0, 0, 0.16) for p in inner]
    cen = T((0, 0, sz))
    for i in range(4):
        j = (i + 1) % 4
        m = (inner[i] + inner[j]) / 2
        face(k, [inner[i], inner[j], deep[j], deep[i]], Z_CINNER, cen - m)
    rng = np.random.default_rng(7)                                       # the straw: a lumpy mat under the rim
    gx, gy = 5, 4
    grid = [[T((-sx / 2 + w + (sx - 2 * w) * i / gx, -sy / 2 + w + (sy - 2 * w) * j / gy,
                sz - 0.16 + 0.02 + (0.05 * rng.random() if 0 < i < gx and 0 < j < gy else 0.0))) for i in range(gx + 1)]
            for j in range(gy + 1)]
    for j in range(gy):
        for i in range(gx):
            face(k, [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]], Z_CSTRAW, (0, 0, 1))
    for t in range(6):                                                   # tufts over the front rim (two-sided)
        a = T((-sx / 2 + 0.12 + (sx - 0.24) * t / 5, -sy / 2 + 0.02, sz - 0.02))
        k.poly([a, a + R @ V(0.04, -0.06, 0.06), a + R @ V(0.09, 0.0, 0.0)], Z_CSTRAW)
        k.poly([a + R @ V(0.09, 0.0, 0.0), a + R @ V(0.04, -0.06, 0.06), a], Z_CSTRAW)
    # the lid: stood on end against the crate's left side (-x'), resting on the rim, its cleats outward
    L_, W_, t_ = sx + 0.02, sy + 0.02, 0.024
    th = math.radians(16.0)
    xb = -sx / 2 - 0.012 - sz * math.tan(th)
    a_ = R @ V(math.sin(th), 0, math.cos(th))                            # up the lid, toward the crate
    b_ = R @ V(0, 1, 0)
    c_ = a_.cross(b_)                                                    # the lid's outer face (away from the crate)
    Rlid = Matrix((a_, b_, c_)).transposed()
    c0 = T((xb, 0.0, 0.0)) + a_ * (L_ / 2) + c_ * (t_ / 2)
    k.box_m(c0, (L_, W_, t_), Z_CPINE, Rlid)
    for yy in (-W_ / 2 + 0.07, W_ / 2 - 0.07):
        k.box_m(c0 + c_ * (t_ / 2 + 0.010) + b_ * yy, (L_ - 0.04, 0.07, 0.02), Z_CPINE, Rlid)


def crates():
    k = kb('Crates', 'Props')
    _chest(k, CRATES['A'], Z_COLIVE)
    _chest(k, CRATES['B'], Z_CCASE, handles=False, corners=False, carry=True)
    _chest(k, CRATES['C'], Z_CCASE, handles=False, corners=True, hasps=False, carry=True)
    _pine(k, CRATES['D'])
    _pine(k, CRATES['E'], open_=True)
    part('Crates', 'static', (0, 0, 0), note='an olive transport chest with a case on top and a small case beside it, two pine '
                                             'crates (one open, straw); stencils in English')


# ================================================================ the log pile
def logpile():
    k = kb('LogPile', 'Props')
    for xs in (-1.55, 1.55):
        log_seg(k, (xs, -1.00, 0.055), (xs, 1.00, 0.055), 0.065, 0.060, Z_LSKID, Z_LEND, seg=7, n=2, wob=0.06,
                seed=int(xs * 10) + 40, caps=(True, True))
    for i, (x0, x1, y, z, r) in enumerate(S.LOGS):
        a, b = V(x0, y, z + LOG_RISE), V(x1, y, z + LOG_RISE)
        if i % 2:
            a, b = b, a                                                  # butts at both ends of the pile
        log_seg(k, a, b, r, r * 0.88, Z_LBARK, Z_LEND, seg=10, n=4, wob=0.05, seed=60 + i)
    for xs in (-1.75, 1.75):                                             # stakes against rolling
        for ys in (-1, 1):
            y = ys * 0.93
            log_seg(k, (xs, y, -0.30), (xs + 0.02 * ys, y + 0.03 * ys, 1.00), 0.050, 0.045, Z_LSTAKE, Z_LEND, seg=6, n=2,
                    wob=0.08, seed=80 + int(xs * 4 + ys), caps=(False, True))
    part('LogPile', 'static', (0, 0, 0), note='nine spruce logs (Update 3\'s) on two skids between four stakes')


# ================================================================ the yard light pole
def lightpole():
    p = S.LPOLE
    k = kb('LightPole', 'Poles')
    f = p['foot']
    chamfer_box(k, (-f, -f, p['foot_bottom']), (f, f, p['foot_top']), 0.02, Z_LFOOT)
    zt = p['foot_top']
    k.box(-0.15, 0.15, -0.15, 0.15, zt, zt + 0.015, Z_LBOLT)
    for xs in (-1, 1):
        for ys in (-1, 1):
            bolt(k, (xs * 0.11, ys * 0.11, zt + 0.015), (0, 0, 1), 0.016, 0.014, Z_LBOLT, washer=0.022)
    z0 = zt + 0.015
    prof = [(0.0, 0.098), (0.20, 0.098), (0.24, p['r0']), (1.0, p['r0'] - 0.003), (3.0, (p['r0'] + p['r1']) / 2 + 0.002),
            (p['top'] - z0 - 0.25, p['r1'] + 0.002), (p['top'] - z0, p['r1'])]
    k.lathe(V(0, 0, z0), (0, 0, 1), prof, Z_LPOLE, 12, cap0=False, cap1=False)
    k.lathe(V(0, 0, p['top']), (0, 0, 1), [(0.0, p['r1']), (0.02, p['r1'] + 0.006), (0.05, 0.04), (0.07, 0.0)], Z_LPOLE, 10,
            cap0=False)
    yd = -(p['r0'] - 0.002)                                              # the inspection door
    k.box(-0.040, 0.040, yd - 0.006, yd + 0.012, 0.62, 0.98, Z_LDOOR)
    for zz in (0.66, 0.94):
        bolt(k, (0.0, yd - 0.006, zz), (0, -1, 0), 0.007, 0.004, Z_LBOLT)
    arm = [V(0.0, 0.0, 5.62), V(0.02, 0.0, 5.86), V(0.12, 0.0, 6.00), V(0.36, 0.0, 6.05), V(0.82, 0.0, 6.05)]
    k.tube(arm, 0.034, Z_LPOLE, 8)
    x0, x1, y0, y1, zb, ztp = p['head']
    hk = []
    for fz, ins in ((0.0, 0.0), (0.55, 0.0), (0.85, 0.015), (1.0, 0.045)):
        z = zb + (ztp - zb) * fz
        hk.append([V(x0 + ins, y0 + ins, z), V(x1 - ins - 0.02, y0 + ins, z), V(x1 - ins, y0 + ins + 0.03, z),
                   V(x1 - ins, y1 - ins - 0.03, z), V(x1 - ins - 0.02, y1 - ins, z), V(x0 + ins, y1 - ins, z)])
    k.loft(hk, [Z_LHEAD] * 3, cap0=Z_LHEAD, cap1=Z_LHEAD)
    for yy in (y0 - 0.004, y1):                                           # the shell's clips
        k.box(x1 - 0.06, x1 - 0.03, yy, yy + 0.004, zb + 0.02, zb + 0.06, Z_LBOLT)
    lx0, lx1, ly0, ly1, lz = p['lens']
    kl = kb('LightPole_Lens', 'lens:sodium')
    ring = [V(lx0 + 0.02, ly0, lz), V(lx1 - 0.02, ly0, lz), V(lx1, ly0 + 0.02, lz), V(lx1, ly1 - 0.02, lz),
            V(lx1 - 0.02, ly1, lz), V(lx0 + 0.02, ly1, lz), V(lx0, ly1 - 0.02, lz), V(lx0, ly0 + 0.02, lz)]
    face(kl, ring, 0.0, (0, 0, -1))
    part('LightPole', 'static', (0, 0, 0), note='galvanised yard light: footing, base plate, door, arm, luminaire')
    part('LightPole_Lens', 'static', ((lx0 + lx1) / 2, 0.0, lz), parent='LightPole',
         note='the lamp\'s lens (Update 3\'s M_Lamp_SodiumOff: the power grid swaps it to M_Light_Sodium)')


# ================================================================ the power pole (the yard's trafo pole type)
def pp_r(z):
    p = S.PPOLE
    return p['r0'] + (p['r1'] - p['r0']) * max(0.0, min(1.0, (z - p['bottom']) / (p['top'] - p['bottom'])))


def powerpole():
    p = S.PPOLE
    k = kb('PowerPole', 'Poles')
    prof = [(z - p['bottom'], pp_r(z)) for z in (p['bottom'], 0.0, 2.0, 4.5, 7.0, p['top'])]
    k.lathe(V(0, 0, p['bottom']), (0, 0, 1), prof, Z_PPOLE, 10, cap0=False, cap1=False)
    k.lathe(V(0, 0, p['top']), (0, 0, 1), [(0.0, pp_r(p['top']) + 0.010), (0.03, pp_r(p['top']) + 0.010), (0.06, 0.0)],
            Z_PGALV, 12, cap0=True)
    za, zb = p['xarm']
    box6(k, (-1.25, -0.05, za), (1.25, 0.05, zb), Z_PXARM)
    k.box(-0.06, 0.06, -0.075, -0.05, za - 0.06, zb + 0.02, Z_PGALV)                       # the crossarm's bolt plate
    bolt(k, (0.0, -0.075, (za + zb) / 2), (0, -1, 0), 0.014, 0.012, Z_PGALV, washer=0.025)
    for sg in (-1, 1):                                                                   # the braces
        k.strip([V(sg * 0.72, -0.056, za), V(sg * 0.06, -0.056, za - 0.53)], V(0, -1, 0), 0.04, 0.008, Z_PGALV)
        k.strip([V(sg * 0.72, 0.056, za), V(sg * 0.06, 0.056, za - 0.53)], V(0, 1, 0), 0.04, 0.008, Z_PGALV)
    bolt(k, (0.0, -pp_r(za - 0.53) - 0.012, za - 0.53), (0, -1, 0), 0.012, 0.010, Z_PGALV, washer=0.02)
    for x in p['insul_x']:                                             # pin insulators: steel pin, brown porcelain
        k.cyl(V(x, 0, zb), V(x, 0, zb + 0.05), 0.014, Z_PGALV, 6, caps=False)
        k.lathe(V(x, 0, zb + 0.04), (0, 0, 1), [(0.0, 0.03), (0.0, 0.07), (0.015, 0.07), (0.03, 0.045), (0.07, 0.045),
                                                 (0.08, 0.062), (0.095, 0.062), (0.11, 0.035), (0.115, 0.035), (0.115, 0.0)],
                Z_PPORC, 10, cap0=True)
    # the earth wire down the pole with its staples, the number plate and the danger plate
    k.tube([V(-0.03, -pp_r(za - 0.4) - 0.006, za - 0.4), V(-0.03, -pp_r(4.0) - 0.006, 4.0), V(-0.03, -pp_r(0.5) - 0.006, 0.5),
            V(-0.03, -pp_r(0.0) - 0.006, -0.05)], 0.005, Z_PEARTH, 5, caps=False)
    for zz in (0.4, 1.4, 2.4, 3.4, 4.4, 5.4, 6.4, 7.4):
        k.box(-0.055, -0.005, -pp_r(zz) - 0.016, -pp_r(zz) + 0.004, zz - 0.006, zz + 0.006, Z_PGALV)
    for zc, w, h in ((2.40, 0.10, 0.14), (3.10, 0.18, 0.16)):
        py = -pp_r(zc) - 0.012
        box6(k, (-w / 2 + 0.04, py, zc - h / 2), (w / 2 + 0.04, py + 0.010, zc + h / 2), Z_PPLATE)
    part('PowerPole', 'static', (0, 0, 0),
         note='creosoted pole, wooden crossarm and braces, three pin insulators (tops at Update 3\'s 8.72: the wires end there)')


# ================================================================ the base fence (chain-link, 3 m; 213 on the map: lean)
def fencechain():
    f = S.FENCE
    k = kb('FenceChain', 'Fence')
    x, r = f['post_x'], f['post_r']
    rod(k, (x, 0.0, f['post_bottom']), (x, 0.0, f['post_top'] - 0.012), r, Z_FPOST, seg=6, caps=False)
    k.cyl(V(x, 0, f['post_top'] - 0.012), V(x, 0, f['post_top'] + 0.008), r + 0.006, Z_FCLAMP, 6)          # the cap
    (ay0, az0), (ay1, az1) = f['arm']                                  # the outrigger (welded on, 45 deg out to -y)
    bar(k, (x, ay0 - 0.010, az0 - 0.030), (x, ay1, az1), 0.030, 0.006, Z_FPOST, up=(1, 0, 0), caps=False)
    rod(k, (f['x0'], 0.0, f['rail_z']), (x - r, 0.0, f['rail_z']), f['rail_r'], Z_FRAIL, seg=6, caps=False)
    km = kb('FenceChain_Mesh', 'chainlink')                            # the chain-link: two-sided, 0.5 m per tile
    z0, z1 = f['mesh_z']
    x0, x1 = f['x0'], x - r
    q = [V(x0, 0, z0), V(x1, 0, z0), V(x1, 0, z1), V(x0, 0, z1)]
    us = [(x0 / 0.5, z0 / 0.5), (x1 / 0.5, z0 / 0.5), (x1 / 0.5, z1 / 0.5), (x0 / 0.5, z1 / 0.5)]
    km.poly(q, 0.0, us)
    km.poly(list(reversed(q)), 0.0, list(reversed(us)))
    kbw = kb('FenceChain_Barbed', 'barbed')                            # the three strands in a 0.52 m band on the arm
    d = V(0, ay1 - ay0, az1 - az0).normalized()
    a0, a1 = V(0, ay0, az0) - d * 0.01, V(0, ay0, az0) + d * 0.51
    q = [V(f['x0'], a0.y, a0.z), V(f['x1'], a0.y, a0.z), V(f['x1'], a1.y, a1.z), V(f['x0'], a1.y, a1.z)]
    us = [(f['x0'] / 0.5, 0.0), (f['x1'] / 0.5, 0.0), (f['x1'] / 0.5, 1.0), (f['x0'] / 0.5, 1.0)]
    kbw.poly(q, 0.0, us)
    kbw.poly(list(reversed(q)), 0.0, list(reversed(us)))
    part('FenceChain', 'static', (0, 0, 0), note='a 3 m section of the base fence (post at x 1.5, as Update 3)')
    part('FenceChain_Mesh', 'static', (0, 0, 1.1), parent='FenceChain', note='chain-link (M_Base_ChainLink, cut-out)')
    part('FenceChain_Barbed', 'static', (0, -0.18, 2.48), parent='FenceChain', note='barbed strands (M_Base_Barbed, cut-out)')


# ================================================================ the old boundary fence (294 on the map: lean)
def old_post_at(name, z):
    o = S.OLD[name]
    bot, top = V(2.0, 0.0, -0.40), V(o['top'])
    return bot.lerp(top, (z - bot.z) / (top.z - bot.z))


def oldfence(name):
    o = S.OLD[name]
    k = kb(name, 'Fence')
    top = V(o['top'])
    bot = V(2.0, 0.0, -0.40)
    log_seg(k, bot, top, S.OLD_POST_R * 1.04, S.OLD_POST_R * 0.92, Z_OPOST, Z_OTOP, seg=6, n=2, wob=0.07,
            seed=sum(map(ord, name)) % 997, caps=(False, True))
    kr = kb(name + '_Wire', 'rust')

    def band(pts, hh=0.04):
        """a two-sided vertical band 0.08 m along a polyline, the strand along its middle; u along the wire (0.5 m)"""
        s = 0.0
        for a, b in zip(pts[:-1], pts[1:]):
            L = (b - a).length
            q = [a - V(0, 0, hh), b - V(0, 0, hh), b + V(0, 0, hh), a + V(0, 0, hh)]
            us = [(s / 0.5, 0.0), ((s + L) / 0.5, 0.0), ((s + L) / 0.5, 1.0), (s / 0.5, 1.0)]
            kr.poly(q, 0.0, us)
            kr.poly(list(reversed(q)), 0.0, list(reversed(us)))
            s += L

    for i, (h, sag) in enumerate(o['strands']):
        pe = old_post_at(name, h) + V(-S.OLD_POST_R, -0.01, 0)
        a = V(-2.0, 0.0, h)
        P_ = lambda t: a.lerp(pe, t) - V(0, 0, sag * 4 * t * (1 - t))
        if o.get('broken') == i:                                         # snapped: both ends curl down
            left = [P_(0.0), P_(0.22), P_(0.36) + V(0.02, 0.03, -0.10), P_(0.36) + V(0.10, 0.06, -0.42)]
            right = [P_(1.0), P_(0.76), P_(0.60) + V(-0.03, 0.04, -0.12), P_(0.60) + V(-0.12, 0.08, -0.50)]
            band(left)
            band(right)
        else:
            band([P_(0.0), P_(0.3), P_(0.7), P_(1.0)])
    part(name, 'static', (0, 0, 0), note='old boundary fence: a weathered post (Update 3\'s lean) and four slack strands')
    part(name + '_Wire', 'static', (0, 0, 1.0), parent=name, note='rusty barbed strands (M_Base_Rust, cut-out)')


# ================================================================ the helipad
def helipad():
    h = S.HELI
    k = kb('Helipad', 'Helipad')
    seg = 72
    R, ch = h['r'], h['chamfer']
    circ = lambda r, z: [V(r * math.cos(TAU * i / seg), r * math.sin(TAU * i / seg), z) for i in range(seg)]
    rings = [circ(R, h['bottom']), circ(R, h['top'] - ch), circ(R - ch, h['top'])]
    k.loft(rings, [Z_PADSIDE, Z_PADSIDE])
    inner = circ(R - 3.0, h['top'])
    for i in range(seg):
        j = (i + 1) % seg
        face(k, [rings[2][i], rings[2][j], inner[j], inner[i]], Z_PAD, (0, 0, 1))
    face(k, inner, Z_PAD, (0, 0, 1))
    # the eight edge lights (Update 3's places): a base plate, a stalk, a black body, the dome
    kl = kb('Helipad_Lens', 'lens:warm')
    for i in range(8):
        a = TAU * i / 8
        cx, cy = h['lights_r'] * math.cos(a), h['lights_r'] * math.sin(a)
        k.box(cx - 0.07, cx + 0.07, cy - 0.07, cy + 0.07, h['top'], h['top'] + 0.012, Z_LSTALK)
        rod(k, (cx, cy, h['top'] + 0.012), (cx, cy, 0.335), 0.026, Z_LSTALK, seg=8, caps=False)
        k.lathe(V(cx, cy, 0.335), (0, 0, 1), [(0.0, 0.045), (0.005, 0.066), (0.035, 0.066), (0.040, 0.058)], Z_LBODY, 12,
                cap0=True, cap1=True)
        kl.lathe(V(cx, cy, 0.374), (0, 0, 1), [(0.0, 0.056), (0.025, 0.052), (0.045, 0.034), (0.056, 0.0)], 0.0, 12,
                 cap0=False, cap1=False)
    # the windsock: a concrete footing, the white mast with its tilting hinge, the swivel, the hoop, the red and white
    # sock drooping in a light wind
    sx, sy = h['sock']
    chamfer_box(k, (sx - 0.53, sy - 0.53, -0.40), (sx + 0.53, sy + 0.53, 0.10), 0.03, Z_PFOOT)
    k.box(sx - 0.17, sx + 0.17, sy - 0.17, sy + 0.17, 0.10, 0.115, Z_SFRAME)
    for xs in (-1, 1):
        for ys in (-1, 1):
            bolt(k, (sx + xs * 0.12, sy + ys * 0.12, 0.115), (0, 0, 1), 0.012, 0.012, Z_SFRAME, washer=0.018)
    rod(k, (sx, sy, 0.115), (sx, sy, h['sock_top']), 0.060, Z_SMAST, seg=10, caps=False)
    k.box(sx - 0.085, sx + 0.085, sy - 0.03, sy + 0.03, 1.00, 1.18, Z_SFRAME)
    rod(k, (sx - 0.09, sy, 1.09), (sx + 0.09, sy, 1.09), 0.015, Z_SFRAME, seg=6)
    st = h['sock_top']
    k.cyl(V(sx, sy, st), V(sx, sy, st + 0.12), 0.045, Z_SFRAME, 10)
    hoop_c = V(sx + 0.42, sy + 0.04, st + 0.06)
    nrm = V(1.0, 0.10, -0.12).normalized()
    k.tube([V(sx, sy, st + 0.06), V(sx + 0.20, sy + 0.02, st + 0.08), hoop_c - nrm * 0.02 + V(0, 0, 0.24)], 0.012,
           Z_SFRAME, 6)
    hr, _ = k.ring_pts(hoop_c, nrm, 0.25, 14)
    k.tube(hr + [hr[0]], 0.010, Z_SFRAME, 6, caps=False)
    rings, zones = [], []
    L = 2.9
    for i in range(11):
        t = i / 10
        c = hoop_c + nrm * (L * t) + V(0, 0.10 * t, -1.5 * t * t)
        d = (nrm + V(0, 0.012, -3.0 * t / L)).normalized()
        r = 0.25 + (0.11 - 0.25) * t
        rr, _ = k.ring_pts(c, d, r, 12)
        wob = 1.0 + 0.06 * np.sin(np.arange(12) * 2.3 + i * 1.7)
        rings.append([c + (q - c) * float(w) for q, w in zip(rr, wob)])
        if i < 10:
            zones.append(Z_SOCKR if (i // 2) % 2 == 0 else Z_SOCKW)
    k.loft(rings, zones)
    k.loft([list(reversed(r)) for r in rings], zones)                    # the inside of the sock
    # the sign (Update 3's place, between its two posts)
    kf = kb('Helipad_Sign', 'panel')
    cx, cy, cz, w_, h_ = h['sign']
    sign_on_posts(k, kf, h['sign_posts'], cy, cz, w_, h_, uv('heli'), bot=-0.30, zp=Z_HPOST, zb=Z_HBACK, zc=Z_LBODY)
    # the fire-extinguisher box on its post
    ex, ey = h['extinguisher']
    rod(k, (ex, ey + 0.04, -0.40), (ex, ey + 0.04, 1.30), 0.035, Z_SFRAME, seg=8, caps=False)
    k.cyl(V(ex, ey + 0.04, 1.30), V(ex, ey + 0.04, 1.31), 0.04, Z_SFRAME, 8)
    box6(k, (ex - 0.19, ey - 0.20, 0.55), (ex + 0.19, ey - 0.005, 1.25), Z_EXTBOX)
    box6(k, (ex - 0.13, ey - 0.208, 0.95), (ex + 0.13, ey - 0.20, 1.12), Z_EXTLBL)
    k.box(ex + 0.10, ex + 0.16, ey - 0.215, ey - 0.20, 0.80, 0.86, Z_LBODY)
    # the pallet with its tarped load and the ropes over it
    px, py = h['pallet']
    for xx in (-0.52, 0.0, 0.52):
        for yy in (-0.42, 0.0, 0.42):
            box6(k, (px + xx - 0.07, py + yy - 0.07, 0.022), (px + xx + 0.07, py + yy + 0.07, 0.11), Z_PALLET)
    for yy in (-0.42, 0.0, 0.42):
        box6(k, (px - 0.60, py + yy - 0.07, 0.0), (px + 0.60, py + yy + 0.07, 0.022), Z_PALLET)
    for i in range(7):
        yy = -0.45 + i * 0.15
        box6(k, (px - 0.60, py + yy - 0.05, 0.11), (px + 0.60, py + yy + 0.05, 0.132), Z_PALLET)
    tr = [superring(px, py, 0.56, 0.47, 0.132, 6.0), superring(px, py, 0.57, 0.48, 0.20, 6.0),
          superring(px, py, 0.55, 0.45, 0.70, 5.0), superring(px, py, 0.47, 0.38, 0.88, 4.0),
          superring(px, py, 0.30, 0.24, 0.94, 3.0)]
    k.loft(tr, [Z_TARP] * 4, cap1=Z_TARP)
    for yy in (-0.22, 0.22):
        k.tube([V(px - 0.585, py + yy, 0.12), V(px - 0.575, py + yy, 0.62), V(px - 0.47, py + yy, 0.86),
                V(px + 0.47, py + yy, 0.86), V(px + 0.575, py + yy, 0.62), V(px + 0.585, py + yy, 0.12)], 0.008, Z_ROPE, 5)
    part('Helipad', 'static', (0, 0, 0), note='the pad, edge lights, windsock, sign, extinguisher box, tarped pallet')
    part('Helipad_Lens', 'static', (0, 0, 0.40), parent='Helipad',
         note='the edge lights\' domes (Update 3\'s M_Lamp_WarmOff: the power grid swaps it to M_Light_WarmWhite)')
    part('Helipad_Sign', 'static', (cx, cy, cz), parent='Helipad', note='the sign face (panel atlas)')


# ================================================================ the radio mast
def _corner(z, xs, ys):
    c = S.mast_c(z)
    return V(xs * c, ys * c, z)


def radiomast():
    m = S.MAST
    k = kb('RadioMast', 'Mast')
    H = m['h']
    corners = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
    zs = list(np.arange(0.0, H + 1e-6, m['bay']))
    zb0 = 0.125
    for xs, ys in corners:                                               # footings and base plates under the legs
        cx, cy = xs * m['footings'], ys * m['footings']
        fh = m['footing'] / 2
        chamfer_box(k, (cx - fh, cy - fh, -1.0), (cx + fh, cy + fh, 0.10), 0.04, Z_MFOOT)
        b = _corner(0.10, xs, ys)
        k.box(b.x - 0.16, b.x + 0.16, b.y - 0.16, b.y + 0.16, 0.10, zb0, Z_MPLATE)
        for dx in (-0.11, 0.11):
            for dy in (-0.11, 0.11):
                bolt(k, (b.x + dx, b.y + dy, zb0), (0, 0, 1), 0.016, 0.014, Z_MPLATE, washer=0.024)
    for xs, ys in corners:                                               # legs (tapering with the mast)
        pts = [_corner(z, xs, ys) for z in [zb0] + zs[1:]]
        r0, r1 = m['leg_r']
        for a, b in zip(pts[:-1], pts[1:]):
            rod(k, a, b, r0 + (r1 - r0) * a.z / H, Z_MLEG, seg=8, caps=False)
    for fi in range(4):                                                  # horizontals, a zig-zag of diagonals on each face
        c0, c1 = corners[fi], corners[(fi + 1) % 4]
        for i, z in enumerate(zs[1:], 1):
            rod(k, _corner(z, *c0), _corner(z, *c1), m['bar_r'], Z_MBAR, seg=6, caps=False)
            za = zs[i - 1] if i > 1 else zb0
            p0, p1 = (_corner(za, *c0), _corner(z, *c1)) if i % 2 else (_corner(za, *c1), _corner(z, *c0))
            rod(k, p0, p1, m['diag_r'], Z_MBAR, seg=6, caps=False)
    # the beacons on brackets at 20 / 40 m (two opposite corners, Update 3's places), the top plate and beacon, the rod
    kl = kb('RadioMast_Lens', 'lens:red')
    for zb in m['beacons']:
        for xs, ys in ((1, -1), (-1, 1)):
            base = _corner(zb, xs, ys)
            tip = base + V(xs * m['bracket'], ys * m['bracket'], 0.0)
            bar(k, base - V(0, 0, 0.04), tip - V(0, 0, 0.04), 0.05, 0.05, Z_MBRK)
            bar(k, base - V(0, 0, 0.40), tip - V(0, 0, 0.065), 0.03, 0.03, Z_MBRK)          # the strut under it
            k.lathe(V(tip.x, tip.y, zb - 0.015), (0, 0, 1), [(0.0, 0.09), (0.03, 0.10), (0.175, 0.10), (0.185, 0.085)],
                    Z_MBODY, 12, cap0=True, cap1=False)
            kl.lathe(V(tip.x, tip.y, zb + 0.17), (0, 0, 1), [(0.0, 0.085), (0.06, 0.08), (0.12, 0.055), (0.17, 0.0)], 0.0, 12,
                     cap0=False, cap1=False)
    zt = H
    c = S.mast_c(zt)
    box6(k, (-c - 0.08, -c - 0.08, zt), (c + 0.08, c + 0.08, zt + 0.02), Z_MBRK)
    k.lathe(V(0, 0, zt + 0.02), (0, 0, 1), [(0.0, 0.16), (0.06, 0.17), (0.14, 0.17), (0.15, 0.15)], Z_MBODY, 14,
            cap0=False, cap1=True)
    kl.lathe(V(0, 0, m['beacon_top'] + 0.01), (0, 0, 1), [(0.0, 0.15), (0.12, 0.14), (0.26, 0.09), (0.37, 0.0)], 0.0, 14,
             cap0=False, cap1=False)
    rod(k, (c - 0.05, c - 0.05, zt + 0.02), (c - 0.05, c - 0.05, m['rod_top'] - 0.10), 0.016, Z_MROD, seg=6, caps=False)
    k.lathe(V(c - 0.05, c - 0.05, m['rod_top'] - 0.10), (0, 0, 1), [(0.0, 0.016), (0.10, 0.0)], Z_MROD, 6, cap0=False)
    # VHF dipoles on stand-off arms on the +x / -x faces at 55 and 58 m
    for zd in (55.0, 58.0):
        for xs in (1, -1):
            cz = S.mast_c(zd)
            a = V(xs * cz, 0.0, zd)
            b = a + V(xs * 0.75, 0, 0)
            bar(k, a, b, 0.04, 0.04, Z_MANT)
            for dx in (0.0, xs * 0.06):
                rod(k, b + V(dx, 0, -0.75), b + V(dx, 0, 0.75), 0.012, Z_MANT, seg=6)
            box6(k, b + V(min(0, xs * 0.10) - 0.02, -0.04, -0.06), b + V(max(0, xs * 0.10) + 0.02, 0.04, 0.06), Z_MANT)
    # the cable tray up the +x face with three feeders; they go into the ground by the footing
    zz_ = list(np.arange(0.6, 57.5 + 1e-6, 3.0))                         # in 3 m lengths: short UV islands
    for za, zb in zip(zz_[:-1], zz_[1:]):
        pts = [V(S.mast_c(z) + 0.07, 0.0, z) for z in (za, zb)]
        k.strip(pts, V(1, 0, 0), 0.20, 0.010, Z_MTRAY, caps=False)
        for dy in (-0.05, 0.0, 0.05):
            k.tube([p + V(0.018, dy, 0.0) for p in pts], 0.011, Z_MCOAX, 5, caps=False)
    for dy in (-0.05, 0.0, 0.05):
        k.tube([V(S.mast_c(0.6) + 0.088, dy, 0.6), V(S.mast_c(0.3) + 0.12, dy, 0.30), V(S.mast_c(0.0) + 0.35, dy, -0.10)],
               0.011, Z_MCOAX, 5, caps=False)
    for zz in np.arange(3.0, 57.0, 6.0):                                 # the tray's brackets to the horizontals
        cz = S.mast_c(zz)
        bar(k, V(cz, 0.0, zz), V(cz + 0.065, 0.0, zz), 0.24, 0.03, Z_MTRAY, up=(0, 0, 1))
    # the ladder up the -y face (flat-bar stiles, round rungs, brackets every 3 m)
    lyo = 0.13
    for xr in (-0.20, 0.20):
        zz_ = list(np.linspace(0.3, H, 21))                              # 3 m lengths
        for za, zb in zip(zz_[:-1], zz_[1:]):
            k.strip([V(xr, -S.mast_c(z) - lyo, z) for z in (za, zb)], V(1, 0, 0), 0.05, 0.012, Z_MLADDER, caps=True)
    for z in np.arange(0.6, H - 0.2, 0.30):
        y = -S.mast_c(z) - lyo
        rod(k, (-0.20, y, z), (0.20, y, z), 0.013, Z_MLADDER, seg=6, caps=False)
    for z in np.arange(1.5, H, 3.0):
        for xr in (-0.20, 0.20):
            bar(k, (xr, -S.mast_c(z) - lyo + 0.02, z), (xr * 0.6, -S.mast_c(z), z), 0.03, 0.008, Z_MLADDER)
    # guys at 21 / 42 / 57 m to three anchor blocks: turnbuckles and links at the anchor plates
    for ai, (ax, ay) in enumerate(m['anchors']):
        d = V(ax, ay, 0).normalized()
        ab = m['anchor_block'] / 2
        chamfer_box(k, (ax - ab, ay - ab, -0.50), (ax + ab, ay + ab, m['anchor_top']), 0.04, Z_MANCH)
        pb = V(ax, ay, m['anchor_top'])
        side = V(-d.y, d.x, 0)
        bar(k, pb - d * 0.05 + V(0, 0, -0.02), pb + d * 0.02 + V(0, 0, 0.14), 0.40, 0.03, Z_MTURN, up=(0, 0, 1))
        for gi, gz in enumerate(m['guy_z']):
            c = S.mast_c(gz)
            if abs(d.x) >= abs(d.y):
                top = V(math.copysign(c, d.x), d.y / abs(d.x) * c, gz)
            else:
                top = V(d.x / abs(d.y) * c, math.copysign(c, d.y), gz)
            off = side * ((gi - 1) * 0.12)
            low = pb + off + V(0, 0, 0.24)
            dirn = (top - low).normalized()
            tb = low + dirn * 0.55
            rod(k, pb + off + V(0, 0, 0.10), low, 0.012, Z_MTURN, seg=6)
            rod(k, low, tb, 0.022, Z_MTURN, seg=6)
            nseg = max(1, int((top - tb).length / 4.0) + 1)              # 4 m lengths: short UV islands
            for j in range(nseg):
                rod(k, tb.lerp(top, j / nseg), tb.lerp(top, (j + 1) / nseg), 0.011, Z_MGUY, seg=6, caps=False)
            k.box_m(top, (0.10, 0.10, 0.06), Z_MPLATE)
    # the warning plate on two flat bars between the ladder's stile and the leg, by the ladder's foot
    kf = kb('RadioMast_Sign', 'panel')
    zc = 1.75
    c = S.mast_c(zc)
    sxc = (0.20 + c) / 2
    sign_plate(k, kf, (sxc, -c - 0.085, zc), 0.42, 0.34, uv('ice'), zone=Z_MBACK)
    for zz in (zc - 0.11, zc + 0.11):
        bar(k, V(0.21, -c - lyo, zz), V(c, -c, zz), 0.03, 0.006, Z_MPLATE, up=(0, 0, 1))
    part('RadioMast', 'static', (0, 0, 0), note='60 m guyed lattice mast, bands, ladder, tray, dipoles, beacons, guys, anchors')
    part('RadioMast_Lens', 'static', (0, 0, 40.0), parent='RadioMast',
         note='the beacons\' domes (Update 3\'s M_Light_Red: always lit; the lights and halos stay at Update 3\'s places)')
    part('RadioMast_Sign', 'static', (sxc, -c - 0.085, zc), parent='RadioMast', note='VORSICHT EISFALL (panel)')


# ================================================================ the overhead line (world model)
def catenary(a, b, sag, n=16):
    a, b = Vector(a), Vector(b)
    return [a.lerp(b, float(t)) - Vector((0, 0, sag * 4 * t * (1 - t))) for t in np.linspace(0, 1, n + 1)]


def wires():
    """Forest_Wires in the Blender map frame: the conductors (zone 0: M_Cable) on catenaries between the insulator
    tops; at poles 2 and 4 the line turns down the pole into the ground: jumpers to three potheads (zone 2: M_Enamel) on a
    bracket, cables down to a galvanised guard tube (zone 1: M_Galvanized)"""
    kw = kb('Forest_Wires', 'cable')
    for a_, b_ in S.SPANS:
        A, B = S.insulators(a_), S.insulators(b_)
        for pa, pb in zip(A, B):
            span = float(np.linalg.norm(np.array(pb) - np.array(pa)))
            kw.tube(catenary(np.array(pa) + [0, 0, 0.012], np.array(pb) + [0, 0, 0.012], S.WIRE_SAG * span * span, 18),
                    0.010, 0.0, 4, caps=False)
    for pi_ in S.LINE_ENDS:
        prev = pi_ - 1
        M = np.array(S.map_matrix('PowerPole', pi_ - 1))
        Mi = np.linalg.inv(M)
        src = (Mi @ np.array([*S.local_to_map('PowerPole', (0, 0, 0), prev - 1), 1.0]))[:3]
        side = -1.0 if src[1] > 0 else 1.0                              # the riser hangs on the far side from the line
        L = lambda v: Vector((M @ np.array([v[0], v[1], v[2], 1.0]))[:3])
        r = pp_r
        yb = side * (r(7.6) + 0.30)
        for xi, xp in zip(S.PPOLE['insul_x'], (-0.24, 0.0, 0.24)):
            kw.tube([L((xi, 0.0, S.PPOLE['insul_top'] + 0.012)), L((xi, side * 0.14, S.PPOLE['insul_top'] - 0.02)),
                     L((xi * 0.5 + xp * 0.5, side * 0.26, 8.15)), L((xp, yb, 7.88))], 0.008, 0.0, 6, caps=False)
            kw.tube([L((xp, yb, 7.88)), L((xp, yb, 7.84)), L((xp, yb, 7.62))], 0.034, 2.0, 8)        # the potheads
            kw.tube([L((xp, yb, 7.62)), L((xp, yb - side * 0.10, 7.45)), L((xp * 0.3, side * (r(7.1) + 0.03), 7.10))], 0.016,
                    0.0, 6, caps=False)
        kw.tube([L((-0.32, yb, 7.58)), L((0.32, yb, 7.58))], 0.02, 1.0, 6)                           # their bracket
        for sg in (-1, 1):
            kw.tube([L((sg * 0.30, yb, 7.58)), L((sg * 0.06, side * r(7.58), 7.58))], 0.015, 1.0, 6)
        kw.tube([L((0.0, side * (r(z) + 0.03), z)) for z in (7.10, 5.0, 3.0, 2.45)], 0.026, 0.0, 6, caps=False)
        kw.tube([L((0.0, side * (r(2.5) + 0.045), 2.5)), L((0.0, side * (r(0.0) + 0.045), -0.25))], 0.045, 1.0, 8)
        for zz in (0.6, 1.6, 2.35, 3.4, 4.6, 5.8, 6.8):
            rr = r(zz) + (0.045 if zz < 2.5 else 0.03)
            kw.tube([L((-0.07, side * (r(zz) - 0.01), zz)), L((-0.05, side * rr, zz)), L((0.05, side * rr, zz)),
                     L((0.07, side * (r(zz) - 0.01), zz))], 0.006, 1.0, 4, caps=False)
    part('Forest_Wires', 'static', (0, 0, 0), note='world model: the overhead line\'s conductors and the two cable risers '
                                                  '(zone 0 -> M_Cable, 1 -> M_Galvanized, 2 -> M_Enamel)')


def build_base():
    hatch()
    crates()
    logpile()
    lightpole()
    powerpole()
    fencechain()
    for n in ('OldFence', 'OldFence_b', 'OldFence_c'):
        oldfence(n)
    helipad()
    radiomast()
    wires()
