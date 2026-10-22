"""The fence and road-block kit of the Forest (Update 7), in the generator shed's style:
  ConcreteFence, ConcreteFence_b - a 2.5 m PO-2 panel (the Soviet rhombus relief on the outer face, -y), its FO-2
        socket at the joint (+x end), the Y outrigger with two barbed bands on the joint (b: other weathering);
  ConcreteFence_Broken - the same, the upper corner knocked off, rebar sticking out;
  ConcreteFence_Sign - the same with the SPERRGEBIET / RESTRICTED AREA plate;
  ConcreteFence_Plain - panel and socket, no outrigger;
  ConcreteFence_Socket - the socket that starts a run (with its outrigger);
  ConcreteFence_Wicket - a 1.2 m panel and a steel door frame with the door standing open (people through, not cars);
  ChainFence, ChainFence_Torn - a 3 m chain-link section that does not flicker (the mesh one face per side, 2.4 mm
        apart, one-sided material; the new woven netting), outrigger and barbed band (Torn: a hole cut, the flap bent out);
  WireCoil - 5 m of concertina razor wire on three stakes;
  RoadBlock_FBS - an FBS 24.4.6 foundation block with two lifting loops; RoadBlock_Jersey, RoadBlock_Jersey_Striped -
        the concrete barrier (Striped: red and white); RoadBlock_Cube - a 1 m concrete cube with a loop;
  TankTooth, TankTooth_b - dragon's teeth (b: chipped, leaning);
  Hedgehog - three steel I-beams crossed;
  WireBarricade - a cheval de frise: a pole on X-shaped stakes wound with barbed wire;
  Abatis, Abatis_b - felled spruces, the butts cut, the branches cut back and sharpened to the outside;
  Sign_Halt - HALT! KONTROLLPUNKT / STOP! CHECKPOINT on two posts; Sign_NoEntry - the round no-entry sign.
Frames: x along, y across (-y the outside), z up, pivot on the ground in the middle; Unity prefab-local (-x, z, -y).
Faces carry a float 'zone' (atlases Concrete, Props) or explicit 'PSX' UVs (panel: the sign faces; chainlink, barbed,
chainbarbed, razor: tiled cut-outs)."""
import math
import numpy as np
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, socket, face, box6, KBS, CONTRACT
from road_kit import bar, rod, log_seg, bolt
from base_kit import chamfer_box, sign_plate, sign_post
import fence_spec as S
import fence_tex as FT

TAU = 2 * math.pi
uv = FT.uv

# ---------------------------------------------------------------- zones (2000+)
(Z_FACE, Z_BACK, Z_EDGE, Z_BREAK, Z_REBAR, Z_SOCK, Z_SLOT, Z_BRACKET, Z_SBACK, Z_SPOST, Z_SCAP,
 Z_WFRAME, Z_WDOOR) = range(2000, 2013)
(Z_FBS, Z_FBSEND, Z_LOOP, Z_JERSEY, Z_JSTRIPE, Z_CUBE, Z_TOOTH, Z_TOOTHTOP, Z_TOOTHCHIP) = range(2015, 2024)
(Z_CPOST, Z_CRAIL, Z_CCAP, Z_STAKE, Z_HEDGE, Z_POLE, Z_WSTAKE, Z_BARK, Z_BUTT, Z_TIP, Z_STUB, Z_HPOST,
 Z_HBACK) = range(2030, 2043)
CONCRETE_ZONES = list(range(2000, 2024))
PROPS_ZONES = list(range(2030, 2043))
DRAFT_COL = {
    Z_FACE: (162, 160, 152), Z_BACK: (150, 148, 140), Z_EDGE: (140, 138, 130), Z_BREAK: (176, 172, 160),
    Z_REBAR: (110, 62, 36), Z_SOCK: (130, 128, 120), Z_SLOT: (50, 48, 44), Z_BRACKET: (52, 50, 48),
    Z_SBACK: (140, 142, 138), Z_SPOST: (150, 154, 150), Z_SCAP: (60, 62, 64), Z_WFRAME: (70, 86, 70),
    Z_WDOOR: (70, 86, 70),
    Z_FBS: (150, 148, 140), Z_FBSEND: (130, 128, 120), Z_LOOP: (110, 62, 36), Z_JERSEY: (166, 164, 156),
    Z_JSTRIPE: (196, 40, 30), Z_CUBE: (156, 154, 146), Z_TOOTH: (148, 146, 136), Z_TOOTHTOP: (140, 138, 128),
    Z_TOOTHCHIP: (178, 174, 162),
    Z_CPOST: (156, 160, 158), Z_CRAIL: (156, 160, 158), Z_CCAP: (140, 144, 140), Z_STAKE: (80, 70, 60),
    Z_HEDGE: (96, 60, 40), Z_POLE: (120, 104, 84), Z_WSTAKE: (110, 96, 78), Z_BARK: (88, 72, 58), Z_BUTT: (196, 168, 120),
    Z_TIP: (206, 180, 136), Z_STUB: (92, 78, 62), Z_HPOST: (150, 154, 150), Z_HBACK: (140, 142, 138)}


def V(*a):
    return Vector(a[0]) if len(a) == 1 else Vector(a)


def quad2(k, pts, uvs, off):
    """a cut-out quad as two faces 2*off apart, each facing out (one-sided material: no fight between the two)"""
    pts = [V(p) for p in pts]
    n = K.newell(pts).normalized()
    k.poly([p + n * off for p in pts], 0.0, uvs)
    k.poly([p - n * off for p in reversed(pts)], 0.0, list(reversed(uvs)))


def band(k, x0, x1, a0, a1, tile_u=0.5, tile_v=None, off=0.0012):
    """a cut-out band along x from x0 to x1 between the points a0 -> a1 (y, z) of its cross line; u = x / tile_u,
    v 0..1 over a0 -> a1 (or (a1 - a0) / tile_v when tile_v: tiled across)"""
    a0, a1 = V(0, *a0), V(0, *a1)
    L = (a1 - a0).length
    v1 = 1.0 if tile_v is None else L / tile_v
    pts = [V(x0, a0.y, a0.z), V(x1, a0.y, a0.z), V(x1, a1.y, a1.z), V(x0, a1.y, a1.z)]
    uvs = [(x0 / tile_u, 0.0), (x1 / tile_u, 0.0), (x1 / tile_u, v1), (x0 / tile_u, v1)]
    quad2(k, pts, uvs, off)


# ================================================================ PO-2
def po2_slab(k, outline, y0, y1, zf, zb, ze):
    """a slab between the planes y0 (outer face, zone zf) and y1 (back, zb) over a polygon outline [(x, z)]
    (counter-clockwise seen from -y); the faces are fanned from the first point (the outline must be star-shaped from it)"""
    fo = [V(x, y0, z) for x, z in outline]
    bo = [V(x, y1, z) for x, z in outline]
    n = len(outline)
    for i in range(1, n - 1):
        face(k, [fo[0], fo[i], fo[i + 1]], zf, (0, -1, 0))
        face(k, [bo[0], bo[i + 1], bo[i]], zb, (0, 1, 0))
    cx = sum(x for x, z in outline) / n
    cz = sum(z for x, z in outline) / n
    for i in range(n):
        j = (i + 1) % n
        mid = V((outline[i][0] + outline[j][0]) / 2 - cx, 0, (outline[i][1] + outline[j][1]) / 2 - cz)
        face(k, [fo[i], fo[j], bo[j], bo[i]], ze, mid)


def po2_panel(k, x0=None, x1=None, broken=False):
    p = S.PO2
    t = p['t']
    x0 = -p['L'] / 2 + p['gap'] / 2 if x0 is None else x0
    x1 = p['L'] / 2 - p['gap'] / 2 if x1 is None else x1
    z0, z1 = p['z0'], p['z1']
    if not broken:
        po2_slab(k, [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], -t / 2, t / 2, Z_FACE, Z_BACK, Z_EDGE)
        return
    b = S.BROKEN
    zc = b['cut'][-1][1]
    po2_slab(k, [(x0, z0), (x1, z0), (x1, zc), (x0, zc)], -t / 2, t / 2, Z_FACE, Z_BACK, Z_EDGE)
    # the upper part, its broken edge from (x0, zc) up to (cut[0]) - fanned from (x1, zc); the break's faces Z_BREAK
    top = [(x1, zc), (x1, z1)] + [c for c in b['cut']]
    fo = [V(x, -t / 2, z) for x, z in top]
    bo = [V(x, t / 2, z) for x, z in top]
    for i in range(1, len(top) - 1):
        face(k, [fo[0], fo[i], fo[i + 1]], Z_FACE, (0, -1, 0))
        face(k, [bo[0], bo[i + 1], bo[i]], Z_BACK, (0, 1, 0))
    face(k, [fo[0], fo[1], bo[1], bo[0]], Z_EDGE, (1, 0, 0))                           # the end
    face(k, [fo[1], fo[2], bo[2], bo[1]], Z_EDGE, (0, 0, 1))                           # the top
    rng = np.random.default_rng(31)
    cut = b['cut']
    for i in range(len(cut) - 1):                                                      # the break (rough: a ridge)
        a, c = V(cut[i][0], 0, cut[i][1]), V(cut[i + 1][0], 0, cut[i + 1][1])
        nrm = V(-(c - a).z, 0, (c - a).x)
        if nrm.x > 0:
            nrm = -nrm
        mid = (a + c) / 2 + nrm.normalized() * float(rng.uniform(0.01, 0.03)) + V(0, float(rng.uniform(-0.02, 0.02)), 0)
        fa, fc = V(a.x, -t / 2, a.z), V(c.x, -t / 2, c.z)
        ba, bc = V(a.x, t / 2, a.z), V(c.x, t / 2, c.z)
        face(k, [fa, fc, mid], Z_BREAK, V(0, -1, 0) + nrm)
        face(k, [mid, bc, ba], Z_BREAK, V(0, 1, 0) + nrm)
        face(k, [fa, mid, ba], Z_BREAK, nrm)
        face(k, [fc, bc, mid], Z_BREAK, nrm)
    # rebar out of the break: bent 8 mm bars
    kr = k
    for j in range(b['rebar']):
        f = (j + 0.5) / b['rebar']
        i = min(int(f * (len(cut) - 1)), len(cut) - 2)
        ff = f * (len(cut) - 1) - i
        a = V(cut[i][0], 0, cut[i][1]).lerp(V(cut[i + 1][0], 0, cut[i + 1][1]), ff)
        y = float(rng.uniform(-0.04, 0.04))
        d = V(-0.6 + float(rng.uniform(-0.3, 0.3)), float(rng.uniform(-0.2, 0.2)), 0.8).normalized()
        L = float(rng.uniform(0.08, 0.22))
        p0 = V(a.x, y, a.z) - d * 0.03
        p1 = p0 + d * L
        p2 = p1 + (d + V(float(rng.uniform(-0.6, 0.6)), 0, -0.5)).normalized() * L * 0.5
        kr.tube([p0, p1, p2], 0.005, Z_REBAR, seg=4, caps=False)


def po2_socket(k, xc=None, lx=None):
    s = S.PO2['socket']
    xc = S.PO2['L'] / 2 if xc is None else xc
    lx = s['lx'] if lx is None else lx
    chamfer_box(k, (xc - lx / 2, -s['ly'] / 2, s['bot']), (xc + lx / 2, s['ly'] / 2, s['top']), 0.015, Z_SOCK)
    sx, sy = s['slot']                                         # the slot the legs stand in (dark, grout around them)
    sx = min(sx, lx - 0.1)
    k.poly([V(xc - sx / 2, -sy / 2, s['top'] + 0.002), V(xc + sx / 2, -sy / 2, s['top'] + 0.002),
            V(xc + sx / 2, sy / 2, s['top'] + 0.002), V(xc - sx / 2, sy / 2, s['top'] + 0.002)], Z_SLOT)


def po2_outrigger(k, kb_, x=None, x0=None, x1=None):
    """the Y outrigger on the joint x: an angle bar up the panel ends, two arms; the barbed bands from x0 to x1"""
    b = S.BRACKET
    p = S.PO2
    x = p['L'] / 2 if x is None else x
    x0 = -p['L'] / 2 if x0 is None else x0
    x1 = p['L'] / 2 if x1 is None else x1
    w, t = b['w'], b['t']
    bar(k, (x, 0.0, b['z_base']), (x, 0.0, b['z_fork']), w, t, Z_BRACKET, up=(1, 0, 0))
    bar(k, (x + w / 2 - t / 2, 0.0, b['z_base']), (x + w / 2 - t / 2, 0.0, b['z_fork']), w, t, Z_BRACKET, up=(0, 1, 0))
    for zz in (b['z_base'] + 0.08, p['z1'] - 0.12):                                    # bolted to the panels' ends
        bolt(k, (x, -w / 2 - 0.001, zz), (0, -1, 0), 0.010, 0.008, Z_BRACKET)
    a = math.radians(b['angle'])
    fork = V(x, 0.0, b['z_fork'])
    for sg in (-1, 1):                                       # -1: the outer arm, +1: the inner
        d = V(0, sg * math.sin(a), math.cos(a))
        end = fork + d * b['arm']
        bar(k, fork - d * 0.01, end, w * 0.8, t, Z_BRACKET, up=(1, 0, 0))
        band(kb_, x0, x1, (fork.y + d.y * 0.01, fork.z + d.z * 0.01), (fork.y + d.y * b['band'], fork.z + d.z * b['band']))


def concrete_fence(name, look='a', broken=False, sign=False, outrigger=True):
    k = kb(name, 'Concrete')
    po2_panel(k, broken=broken)
    po2_socket(k)
    if outrigger:
        kbw = kb(name + '_Barbed', 'barbed')
        po2_outrigger(k, kbw)
        part(name + '_Barbed', 'static', (0, 0, 2.9), parent=name, note='barbed strands on both arms (M_Fence_Barbed, cut-out)')
    if sign:
        g = S.SIGN
        kf = kb(name + '_Sign', 'panel')
        sign_plate(k, kf, (g['c'][0], -S.PO2['t'] / 2 - 0.018, g['c'][1]), g['w'], g['h'], uv('sperr'), back=0.012,
                   zone=Z_SBACK)
        for sx in (-1, 1):
            for sz in (-1, 1):
                bolt(k, (g['c'][0] + sx * (g['w'] / 2 - 0.04), -S.PO2['t'] / 2 - 0.019, g['c'][1] + sz * (g['h'] / 2 - 0.04)),
                     (0, -1, 0), 0.008, 0.006, Z_BRACKET)
        part(name + '_Sign', 'static', (0, -0.09, g['c'][1]), parent=name, note='SPERRGEBIET plate (M_Fence_Panel)')
    what = {'a': 'weathered grey', 'b': 'darker, moss and water streaks'}[look]
    part(name, 'static', (0, 0, 0), note=f'a 2.5 m PO-2 panel ({what}{", the corner knocked off" if broken else ""}'
                                         f'{", the restricted-area plate" if sign else ""}), its FO-2 socket at x +1.25'
                                         f'{", the Y outrigger on the joint" if outrigger else ""}; relief on -y (outside)')


def concrete_socket():
    name = 'ConcreteFence_Socket'
    k = kb(name, 'Concrete')
    po2_socket(k, xc=0.0)
    b = S.BRACKET
    w, t = b['w'], b['t']
    bar(k, (0.0, 0.0, S.PO2['socket']['top']), (0.0, 0.0, b['z_fork']), w, t, Z_BRACKET, up=(1, 0, 0))   # a post of its own
    bar(k, (w / 2 - t / 2, 0.0, S.PO2['socket']['top']), (w / 2 - t / 2, 0.0, b['z_fork']), w, t, Z_BRACKET, up=(0, 1, 0))
    a = math.radians(b['angle'])
    fork = V(0.0, 0.0, b['z_fork'])
    for sg in (-1, 1):
        d = V(0, sg * math.sin(a), math.cos(a))
        bar(k, fork - d * 0.01, fork + d * b['arm'], w * 0.8, t, Z_BRACKET, up=(1, 0, 0))
    part(name, 'static', (0, 0, 0), note='the socket that starts a run, with its outrigger post (the run\'s first panel '
                                        'stands with its -x end in it; the bands belong to the panels)')


def concrete_wicket():
    name = 'ConcreteFence_Wicket'
    w_ = S.WICKET
    k = kb(name, 'Concrete')
    po2_panel(k, x0=w_['panel'][0], x1=w_['panel'][1])
    po2_socket(k)                                                       # at the joint, +x
    po2_socket(k, xc=w_['panel'][1] - 0.15, lx=0.60)                    # under the short panel's free end
    kbw = kb(name + '_Barbed', 'barbed')
    po2_outrigger(k, kbw)
    xa, xb = w_['opening'][0] + 0.05, w_['opening'][1] - 0.03          # the door frame: two posts and a lintel
    r = w_['post_r']
    for xx in (xa, xb):
        rod(k, (xx, 0.0, -0.30), (xx, 0.0, w_['lintel_z'] + 0.05), r, Z_WFRAME, seg=6, caps=True)
    bar(k, (xa, 0.0, w_['lintel_z']), (xb, 0.0, w_['lintel_z']), 0.06, 0.06, Z_WFRAME, up=(0, 0, 1))
    # the door: hinged on the right post, standing open to the outside (a tube frame, chain-link in it)
    km = kb(name + '_Mesh', 'chainlink')
    ang = math.radians(w_['door_open'])
    hinge = V(xb, 0.0, 0.05)
    d = V(-math.cos(ang), -math.sin(ang), 0)
    W, H = w_['door_w'], w_['door_h']
    c = [hinge, hinge + d * W, hinge + d * W + V(0, 0, H), hinge + V(0, 0, H)]
    for a_, b_ in zip(c, c[1:] + c[:1]):
        rod(k, a_, b_, 0.016, Z_WDOOR, seg=5, caps=False)
    rod(k, c[0] + V(0, 0, H * 0.5), c[1] + V(0, 0, H * 0.5), 0.012, Z_WDOOR, seg=5, caps=False)
    us = [(0.0, 0.0), (W / 0.5, 0.0), (W / 0.5, H / 0.5), (0.0, H / 0.5)]
    quad2(km, [c[0] + V(0, 0, 0.02), c[1] + V(0, 0, 0.02), c[2] - V(0, 0, 0.02), c[3] - V(0, 0, 0.02)], us, 0.0012)
    for zz in (0.35, H - 0.35):
        k.box(xb - 0.02, xb + 0.05, -0.03, 0.03, zz - 0.04, zz + 0.04, Z_WFRAME)          # the hinges
    part(name, 'static', (0, 0, 0), note='a 1.2 m panel and a walk-through: steel door frame, the door standing open '
                                        '(people pass, cars do not); socket at +1.25, outrigger on the joint')
    part(name + '_Barbed', 'static', (0, 0, 2.9), parent=name, note='barbed strands (M_Fence_Barbed, cut-out)')
    part(name + '_Mesh', 'static', (0.6, -0.5, 1.0), parent=name, note='the door\'s chain-link (M_Fence_ChainLink)')


# ================================================================ chain-link
def chain_fence(name, torn=False):
    c = S.CHAIN
    k = kb(name, 'Props')
    x, r = c['post_x'], c['post_r']
    rod(k, (x, 0.0, c['post_bottom']), (x, 0.0, c['post_top'] - 0.012), r, Z_CPOST, seg=6, caps=False)
    k.cyl(V(x, 0, c['post_top'] - 0.012), V(x, 0, c['post_top'] + 0.008), r + 0.006, Z_CCAP, 6)
    (ay0, az0), (ay1, az1) = c['arm']
    bar(k, (x, ay0 - 0.010, az0 - 0.030), (x, ay1, az1), 0.030, 0.006, Z_CPOST, up=(1, 0, 0), caps=False)
    rod(k, (-c['L'] / 2, 0.0, c['rail_z']), (x - r, 0.0, c['rail_z']), c['rail_r'], Z_CRAIL, seg=6, caps=False)
    rod(k, (-c['L'] / 2, 0.0, 0.10), (x - r, 0.0, 0.10), 0.004, Z_CRAIL, seg=4, caps=False)       # the tension wire
    km = kb(name + '_Mesh', 'chainlink')
    z0, z1 = c['mesh_z']
    x0, x1 = -c['L'] / 2, x - r
    off = c['off']

    def mesh(xa, xb, za, zb):
        quad2(km, [V(xa, 0, za), V(xb, 0, za), V(xb, 0, zb), V(xa, 0, zb)],
              [(xa / 0.5, za / 0.5), (xb / 0.5, za / 0.5), (xb / 0.5, zb / 0.5), (xa / 0.5, zb / 0.5)], off)

    if not torn:
        mesh(x0, x1, z0, z1)
    else:
        t = c['torn']
        hx0, hx1 = t['x']
        hz0, hz1 = t['z']
        mesh(x0, hx0, z0, z1)
        mesh(hx1, x1, z0, z1)
        mesh(hx0, hx1, hz1, z1)
        # the flap: the cut piece hangs from the hole's top edge, bent out (-y) by 55 degrees, curled at the end
        f = t['flap']
        a = math.radians(55.0)
        p0, p1 = V(hx0 + 0.04, 0, hz1), V(hx1 - 0.06, 0, hz1)
        d1 = V(0, -math.sin(a), -math.cos(a))
        q = [p0, p1, p1 + d1 * f, p0 + d1 * f * 0.9]
        quad2(km, q, [(p0.x / 0.5, hz1 / 0.5), (p1.x / 0.5, hz1 / 0.5), (p1.x / 0.5, (hz1 - f) / 0.5),
                      (p0.x / 0.5, (hz1 - f * 0.9) / 0.5)], off)
    kbw = kb(name + '_Barbed', 'chainbarbed')
    d = V(0, ay1 - ay0, az1 - az0).normalized()
    a0, a1 = V(0, ay0, az0) - d * 0.01, V(0, ay0, az0) + d * (c['band'] - 0.01)
    band(kbw, -c['L'] / 2, c['L'] / 2, (a0.y, a0.z), (a1.y, a1.z))
    part(name, 'static', (0, 0, 0), note='a 3 m chain-link section (post at x +1.5, as FenceChain)'
                                        + ('; a hole cut at the bottom, the flap bent out' if torn else ''))
    part(name + '_Mesh', 'static', (0, 0, 1.1), parent=name, note='chain-link (M_Fence_ChainLink, cut-out, one-sided faces)')
    part(name + '_Barbed', 'static', (0, -0.18, 2.48), parent=name, note='barbed strands (M_Fence_ChainBarbed, cut-out)')


# ================================================================ concertina
def wire_coil():
    c = S.COIL
    name = 'WireCoil'
    k = kb(name, 'Props')
    kr = kb(name + '_Razor', 'razor')
    L, R, loops, seg, w = c['L'], c['r'], c['loops'], c['seg'], c['ribbon']
    n = loops * seg
    zc = R + 0.03
    pts = []
    for i in range(n + 1):
        t = i / n
        a = TAU * loops * t
        x = -L / 2 + L * t
        pts.append((V(x, R * math.sin(a), zc - R * math.cos(a)), V(0, math.sin(a), -math.cos(a))))
    s = 0.0
    for (p0, r0), (p1, r1) in zip(pts[:-1], pts[1:]):
        seg_len = (p1 - p0).length
        ax = V(1, 0, 0)
        q = [p0 - ax * w / 2, p1 - ax * w / 2, p1 + ax * w / 2, p0 + ax * w / 2]
        uvs = [(s / 0.5, 0.0), ((s + seg_len) / 0.5, 0.0), ((s + seg_len) / 0.5, 1.0), (s / 0.5, 1.0)]
        quad2(kr, q, uvs, 0.0012)
        s += seg_len
    for x in c['stakes']:                                                # Y-section steel stakes, the coil hooked on
        bar(k, (x, 0.0, -0.30), (x, 0.0, c['stake_h']), 0.040, 0.005, Z_STAKE, up=(1, 0, 0))
        bar(k, (x + 0.018, 0.0, -0.30), (x + 0.018, 0.0, c['stake_h']), 0.040, 0.005, Z_STAKE, up=(0, 1, 0))
    part(name, 'static', (0, 0, 0), note='5 m of concertina razor wire on three stakes (the tape: M_Fence_Razor, cut-out)')
    part(name + '_Razor', 'static', (0, 0, 0.48), parent=name, note='razor tape (M_Fence_Razor, cut-out)')


# ================================================================ road blocks
def loop(k, c, axis_x, r, rod_r, zone, seg=7):
    """a lifting loop: half a ring standing on a block's top, in the plane of x (axis_x True) or y"""
    pts = []
    for i in range(seg + 1):
        a = math.pi * i / seg
        dx, dz = r * math.cos(a), r * math.sin(a)
        pts.append(V(c[0] + (dx if axis_x else 0), c[1] + (0 if axis_x else dx), c[2] + dz - 0.02))
    k.tube(pts, rod_r, zone, seg=4, caps=False)


def roadblock_fbs():
    f = S.FBS
    name = 'RoadBlock_FBS'
    k = kb(name, 'Concrete')
    L, w, h = f['L'], f['w'], f['h']
    box6(k, (-L / 2, -w / 2, 0.0), (L / 2, w / 2, h), {'*': Z_FBS, '-x': Z_FBSEND, '+x': Z_FBSEND}, skip=('-z',))
    for x in (-f['loop_x'], f['loop_x']):
        loop(k, (x, 0.0, h), False, f['loop_r'], f['loop_rod'], Z_LOOP)
    part(name, 'static', (0, 0, 0), note='FBS 24.4.6 foundation block 2.38 x 0.40 x 0.58 m, two lifting loops, end grooves')


def roadblock_jersey(name, striped=False):
    j = S.JERSEY
    k = kb(name, 'Concrete')
    L = j['L']
    prof = j['prof']
    zone = Z_JSTRIPE if striped else Z_JERSEY
    ra = [V(-L / 2, y, z) for y, z in prof]
    rb = [V(L / 2, y, z) for y, z in prof]
    for i in range(len(prof) - 1):                                            # the long faces, outward
        a, b_ = ra[i], ra[i + 1]
        mid = V(0, (prof[i][0] + prof[i + 1][0]) / 2, (prof[i][1] + prof[i + 1][1]) / 2 - 0.4)
        face(k, [a, b_, rb[i + 1], rb[i]], zone, mid)
    face(k, ra, Z_JERSEY, (-1, 0, 0))
    face(k, rb, Z_JERSEY, (1, 0, 0))
    part(name, 'static', (0, 0, 0), note='New Jersey concrete barrier 2.0 x 0.61 x 0.81 m'
                                        + (' painted red and white' if striped else ''))


def roadblock_cube():
    c = S.CUBE
    name = 'RoadBlock_Cube'
    k = kb(name, 'Concrete')
    s = c['s']
    chamfer_box(k, (-s / 2, -s / 2, -0.05), (s / 2, s / 2, s), c['ch'], Z_CUBE)
    loop(k, (0.0, 0.0, s), True, c['loop_r'], c['loop_rod'], Z_LOOP)
    part(name, 'static', (0, 0, 0), note='a 1 m concrete cube with a lifting loop')


def tank_tooth(name, chipped=False):
    t = S.TOOTH
    k = kb(name, 'Concrete')
    b, tp, h = t['base'] / 2, t['top'] / 2, t['h']
    bury = t['bury']
    slope = (b - tp) / h
    bb = b + slope * bury
    rb = [V(-bb, -bb, -bury), V(bb, -bb, -bury), V(bb, bb, -bury), V(-bb, bb, -bury)]
    rt = [V(-tp, -tp, h), V(tp, -tp, h), V(tp, tp, h), V(-tp, tp, h)]
    apex = V(0, 0, h + t['cap'])
    chip = 1 if chipped else None
    if chipped:                                           # one top corner knocked off: lower and pulled in
        rt[1] = V(tp * 0.55, -tp * 0.55, h - 0.17)
    for i in range(4):
        j = (i + 1) % 4
        mid = (rb[i] + rb[j] + rt[i] + rt[j]) / 4
        face(k, [rb[i], rb[j], rt[j], rt[i]], Z_TOOTH, V(mid.x, mid.y, 0.2))
    for i in range(4):
        j = (i + 1) % 4
        zz = Z_TOOTHCHIP if chip in (i, j) else Z_TOOTHTOP
        face(k, [rt[i], rt[j], apex], zz, (rt[i] + rt[j]) / 2 - V(0, 0, h - 0.5))
    part(name, 'static', (0, 0, 0), note='dragon\'s tooth: a concrete truncated pyramid 1.0 m square, 1.1 m tall'
                                        + (' (a corner knocked off)' if chipped else ''))


def hedgehog():
    hd = S.HEDGE
    name = 'Hedgehog'
    k = kb(name, 'Props')
    L, w, t = hd['L'], hd['w'], hd['t']
    # an orthonormal triad with (1, 1, 1) up: each beam's lower end 35.3 degrees below the horizon, on the ground
    up = V(1, 1, 1).normalized()
    e = [V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)]
    R = up.rotation_difference(V(0, 0, 1)).to_matrix()
    Rz = Matrix.Rotation(math.radians(15.0), 3, 'Z')
    e = [Rz @ (R @ ei) for ei in e]
    c = V(0, 0, (L / 2) / math.sqrt(3) + 0.02)
    for ei in e:
        a, b_ = c - ei * L / 2, c + ei * L / 2
        side = ei.cross(V(0, 0, 1))
        side = side.normalized() if side.length > 1e-4 else V(1, 0, 0)
        nrm = ei.cross(side).normalized()
        bar(k, a, b_, w, t, Z_HEDGE, up=tuple(side))                         # the web
        for sg in (-1, 1):                                                     # the flanges, at the web's edges
            bar(k, a + nrm * sg * (w / 2 - t / 2), b_ + nrm * sg * (w / 2 - t / 2), w * 0.75, t, Z_HEDGE, up=tuple(nrm))
    part(name, 'static', (0, 0, 0), note='Czech hedgehog: three steel I-beams 1.6 m crossed, standing on three ends')


def wire_barricade():
    b = S.BARRICADE
    name = 'WireBarricade'
    k = kb(name, 'Props')
    kw = kb(name + '_Barbed', 'barbed')
    L = b['L']
    zc = b['beam_z']
    log_seg(k, V(-L / 2, 0, zc), V(L / 2, 0, zc), b['beam_r'], b['beam_r'] * 0.9, Z_POLE, Z_BUTT, seg=6, n=2, wob=0.06,
            seed=11)
    a = math.radians(90.0 - b['stake_ang'])
    half = b['stake_L'] / 2
    for i, x in enumerate(b['stake_x']):
        for sg in (-1, 1):
            d = V(0, sg * math.sin(a), math.cos(a))
            p0, p1 = V(x + sg * 0.03, 0, zc) - d * half, V(x + sg * 0.03, 0, zc) + d * half
            log_seg(k, p0, p1 - d * 0.10, b['stake_r'], b['stake_r'] * 0.9, Z_WSTAKE, Z_BUTT, seg=5, n=1, wob=0.05,
                    seed=20 + i * 2 + (sg > 0))
            k.cyl(p1 - d * 0.10, p1, b['stake_r'] * 0.9, Z_TIP, 5, r2=0.004, caps=False)        # sharpened
    for sg in (-1, 1):                                                         # the wire wound over each half of the X
        d = V(0, sg * math.sin(a), math.cos(a))
        lo, hi = V(0, 0, zc) - d * (half - 0.15), V(0, 0, zc) + d * (half - 0.15)
        band(kw, -L / 2 + 0.05, L / 2 - 0.05, (lo.y + sg * 0.02, lo.z), (hi.y + sg * 0.02, hi.z), tile_v=b['wire_band'])
    part(name, 'static', (0, 0, 0), note='cheval de frise: a 3 m pole on three X-shaped sharpened stakes, barbed wire wound '
                                        'over the X')
    part(name + '_Barbed', 'static', (0, 0, zc), parent=name, note='barbed wire (M_Fence_Barbed, cut-out)')


def _felled(k, rng, butt, top, r0, r1, seed, crown=0.32, whorl=0.38, per=5, Lmax=1.7):
    """one felled spruce lying on the ground: the butt sawn, the lower trunk's branches cut back to stubs, the crown's
    whorls of branches kept and sharpened (they turn up at the ends, as a spruce's do); those that pointed into the ground
    are sawn off, those that pointed in (+y) cut back. Returns the sharpened tips (for the wire)"""
    log_seg(k, butt, top, r0, r1, Z_BARK, Z_BUTT, seg=7, n=5, wob=0.07, seed=seed, caps=(True, True))
    ax = (top - butt).normalized()
    s1 = ax.cross(V(0, 0, 1)).normalized()
    if s1.y > 0:
        s1 = -s1                                                   # s1: across the trunk, to the outside (-y)
    u1 = s1.cross(ax).normalized()
    if u1.z < 0:
        u1 = -u1
    Ltr = (top - butt).length
    tips = []

    def at(f):
        return butt.lerp(top, f), r0 + (r1 - r0) * f

    for i in range(int(Ltr * crown / 0.30)):                      # the lower trunk: stubs
        c, r = at((i + rng.uniform(0.2, 0.8)) * 0.30 / Ltr)
        ang = rng.uniform(0, TAU)
        d = (s1 * math.cos(ang) + u1 * math.sin(ang) + ax * 0.35).normalized()
        if d.z < -0.2:
            continue
        k.cyl(c + d * r * 0.8, c + d * (r + rng.uniform(0.08, 0.26)), rng.uniform(0.022, 0.034), Z_STUB, 4, r2=0.014,
              caps=True)
    n_wh = max(3, int(Ltr * (1 - crown) / whorl))
    for w in range(n_wh):
        f = crown + (1 - crown) * (w + rng.uniform(0.25, 0.75)) / n_wh
        c, r = at(f)
        g = (f - crown) / (1 - crown)                              # 0 at the crown's foot, 1 at the top
        Lw = Lmax * (1.0 - 0.72 * g) * rng.uniform(0.85, 1.1)
        a0 = rng.uniform(0, TAU)
        for j in range(per):
            ang = a0 + TAU * j / per + rng.uniform(-0.3, 0.3)
            d = (s1 * math.cos(ang) + u1 * math.sin(ang) + ax * 0.32).normalized()
            if d.z < -0.35:                                        # into the ground: sawn off at the trunk
                continue
            if d.dot(s1) < -0.55:                                  # to the inside: cut back
                k.cyl(c + d * r * 0.8, c + d * (r + rng.uniform(0.12, 0.30)), 0.032, Z_STUB, 4, r2=0.022, caps=True)
                continue
            rr = 0.026 + 0.030 * (1.0 - g)
            p0 = c + d * r * 0.7
            mid = p0 + d * Lw * 0.55
            d2 = (d + V(0, 0, 0.30) + s1 * 0.10).normalized()
            p1 = mid + d2 * max(0.10, Lw * 0.45 - 0.14)
            if p1.z < 0.12:
                p1.z = 0.12
            k.cyl(p0, mid, rr, Z_STUB, 4, r2=rr * 0.75, caps=False)
            k.cyl(mid, p1, rr * 0.75, Z_STUB, 4, r2=rr * 0.55, caps=False)
            k.cyl(p1, p1 + (p1 - mid).normalized() * 0.14, rr * 0.55, Z_TIP, 4, r2=0.002, caps=False)
            tips.append(p1)
            if Lw > 0.8 and rng.random() < 0.5:                     # a side twig, sharpened too
                q0 = p0.lerp(mid, rng.uniform(0.45, 0.8))
                dd = (d + ax * rng.uniform(0.2, 0.6) + V(0, 0, rng.uniform(0.1, 0.5))).normalized()
                q1 = q0 + dd * Lw * 0.32
                k.cyl(q0, q1, rr * 0.5, Z_STUB, 3, r2=rr * 0.35, caps=False)
                k.cyl(q1, q1 + dd * 0.09, rr * 0.35, Z_TIP, 3, r2=0.002, caps=False)
    k.cyl(top, top + ax * 0.30, r1, Z_STUB, 4, r2=r1 * 0.6, caps=False)         # the leader, sharpened
    k.cyl(top + ax * 0.30, top + ax * 0.46, r1 * 0.6, Z_TIP, 4, r2=0.002, caps=False)
    return tips


def _wire_through(kw, rng, tips, x0, x1, zs=(0.35, 0.80), band_h=0.46):
    """barbed wire strung through the crowns: a strip from tip to tip along x (the outer ones), at two heights"""
    for zt in zs:
        pts = sorted([p for p in tips if abs(p.z - zt) < 0.35 and p.y < 0.2], key=lambda p: p.x)
        chain, last = [], None
        for p in pts:
            if last is None or p.x - last.x > 0.9:
                chain.append(p)
                last = p
        if len(chain) < 2:
            continue
        for a_, b_ in zip(chain, chain[1:]):
            if (b_ - a_).length > 2.6:
                continue
            h = V(0, 0, band_h / 2)
            u0, u1 = a_.x / 0.5, b_.x / 0.5
            quad2(kw, [a_ - h, b_ - h, b_ + h, a_ + h], [(u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)], 0.0012)


def abatis(name, single=False, seed=None):
    a_ = S.ABATIS
    seed = a_['seed'] if seed is None else seed
    rng = np.random.default_rng(seed)
    k = kb(name, 'Props')
    kw = kb(name + '_Barbed', 'barbed')
    lift = a_['lift']
    if single:                                                    # one big spruce, its crown to the outside
        L, r0 = 6.6, 0.25
        tips = _felled(k, rng, V(-L / 2, 0.25, r0 + lift), V(L / 2, -0.25, 0.08 + lift), r0, 0.06, seed, crown=0.28,
                       Lmax=1.9)
        note = f'abatis: one felled spruce {L:.1f} m, the butt sawn, the crown\'s branches sharpened, those to the inside ' \
               'cut back; barbed wire strung through the crown'
    else:                                                         # two laid head to tail, the crowns overlapping
        L1, L2 = a_['L'], 6.0
        tips = _felled(k, rng, V(-L1 / 2 - 0.3, 0.30, 0.22 + lift), V(L1 / 2 - 0.3, -0.10, 0.07 + lift), 0.22, 0.06, seed,
                       Lmax=1.7)
        tips += _felled(k, rng, V(L2 / 2 + 0.6, -0.45, 0.19 + lift), V(-L2 / 2 + 0.6, -0.75, 0.07 + lift), 0.19, 0.05,
                        seed + 1, Lmax=1.5)
        note = f'abatis: two felled spruces ({L1:.1f} and {L2:.1f} m) laid head to tail, the crowns overlapping, butts sawn, ' \
               'the crowns\' branches sharpened, those to the inside cut back; barbed wire strung through'
    _wire_through(kw, rng, tips, -4.0, 4.0)
    part(name, 'static', (0, 0, 0), note=note)
    part(name + '_Barbed', 'static', (0, 0, 0.6), parent=name, note='barbed wire through the crowns (M_Fence_Barbed, cut-out)')


# ================================================================ signs
def sign_halt():
    h = S.HALT
    name = 'Sign_Halt'
    k = kb(name, 'Props')
    kf = kb(name + '_Sign', 'panel')
    top = h['z'] + h['h'] / 2 + 0.06
    for x in h['posts']:
        sign_post(k, x, 0.02, top, r=h['post_r'], zone=Z_HPOST, cap=Z_SCAP)
    sign_plate(k, kf, (0.0, -h['post_r'] - 0.005, h['z']), h['w'], h['h'], uv('halt'), back=0.014, zone=Z_HBACK)
    for x in h['posts']:
        for zz in (h['z'] - h['h'] / 2 + 0.10, h['z'] + h['h'] / 2 - 0.10):              # clamps
            k.box(x - 0.05, x + 0.05, -0.002, 0.065, zz - 0.02, zz + 0.02, Z_HPOST)
    part(name, 'static', (0, 0, 0), note='HALT! KONTROLLPUNKT / STOP! CHECKPOINT board 1.2 x 0.8 m on two posts')
    part(name + '_Sign', 'static', (0, -0.04, h['z']), parent=name, note='the board\'s face (M_Fence_Panel)')


def sign_noentry():
    n = S.NOENTRY
    name = 'Sign_NoEntry'
    k = kb(name, 'Props')
    kf = kb(name + '_Sign', 'panel')
    sign_post(k, 0.0, 0.02, n['z'] + n['r'] + 0.02, r=n['post_r'], zone=Z_HPOST, cap=Z_SCAP)
    c = V(0.0, -n['post_r'] - 0.008, n['z'])
    kf.disc_uv(c, (0, -1, 0), n['r'], uv('noentry'), seg=16)
    ring = [c + V(n['r'] * math.cos(TAU * i / 16), 0, n['r'] * math.sin(TAU * i / 16)) for i in range(16)]
    back = [p + V(0, 0.010, 0) for p in ring]
    for i in range(16):
        j = (i + 1) % 16
        face(k, [ring[i], ring[j], back[j], back[i]], Z_HBACK, (ring[i] + ring[j]) / 2 - c)
    face(k, list(reversed(back)), Z_HBACK, (0, 1, 0))
    for zz in (n['z'] - 0.12, n['z'] + 0.12):
        k.box(-0.05, 0.05, -0.002, 0.06, zz - 0.02, zz + 0.02, Z_HPOST)
    part(name, 'static', (0, 0, 0), note='the round no-entry sign (Zeichen 267) on a post')
    part(name + '_Sign', 'static', (0, -0.04, n['z']), parent=name, note='the sign\'s face (M_Fence_Panel)')


MODELS = ['ConcreteFence', 'ConcreteFence_b', 'ConcreteFence_Broken', 'ConcreteFence_Sign', 'ConcreteFence_Plain',
          'ConcreteFence_Socket', 'ConcreteFence_Wicket', 'ChainFence', 'ChainFence_Torn', 'WireCoil', 'RoadBlock_FBS',
          'RoadBlock_Jersey', 'RoadBlock_Jersey_Striped', 'RoadBlock_Cube', 'TankTooth', 'TankTooth_b', 'Hedgehog',
          'WireBarricade', 'Abatis', 'Abatis_b', 'Sign_Halt', 'Sign_NoEntry']


def build_all():
    concrete_fence('ConcreteFence', 'a')
    concrete_fence('ConcreteFence_b', 'b')
    concrete_fence('ConcreteFence_Broken', 'a', broken=True)
    concrete_fence('ConcreteFence_Sign', 'a', sign=True)
    concrete_fence('ConcreteFence_Plain', 'b', outrigger=False)
    concrete_socket()
    concrete_wicket()
    chain_fence('ChainFence')
    chain_fence('ChainFence_Torn', torn=True)
    wire_coil()
    roadblock_fbs()
    roadblock_jersey('RoadBlock_Jersey')
    roadblock_jersey('RoadBlock_Jersey_Striped', striped=True)
    roadblock_cube()
    tank_tooth('TankTooth')
    tank_tooth('TankTooth_b', chipped=True)
    hedgehog()
    wire_barricade()
    abatis('Abatis')
    abatis('Abatis_b', single=True, seed=19)
    sign_halt()
    sign_noentry()
