"""The Forest map's road prefabs in the generator shed's style (Update 3's names, pivots, sizes and places; the map's
prologue road from the SPERRGEBIET gate to the observatory, and the station's other signs):
  Sign_Observatory, Sign_Viewpoint, Sign_Lookout, Sign_Pump, Sign_Radar, Sign_Relay, Sign_Weather and the distance signs
    Dist_11 / 09 / 07 / 23 / 03 - German road signs: an aluminium plate with a folded edge (the face = the sign, the back
    dust grey RAL 7037) on two galvanised tube posts 60.3 with caps, two hat rails on the back, tube clamps;
  EuroPost - the road's delineator posts (Update 3's scatter, 48 along the road): white post, black band, amber
    reflectors both ways;
  ZoneGate - the zone gate behind the players' car: two concrete pillars with caps on footings, two gate leaves of
    galvanised tube (frame, mid stile, brace) with chain-link, barbed wire on uprights, the SPERRGEBIET plate on a
    mounting frame on each leaf (one to each side, as Update 3), hinges on the pillars, a drop bolt, a chain with a
    padlock round the two latch stiles;
  Bridge30 - the timber bridge over the ravine (32 m): transverse deck planks, two running strips of three boards,
    curbs on spacer blocks, six log stringers in three spans with strapped joints over the piers, two pile bents with
    caps, X-bracing and walings, log cribs with stone fill at the banks under sill beams, the railing (posts bolted to
    the outer stringers on packing blocks, handrail, mid rail), weight-limit signs 7,5 t at both ends;
  OverlookDeck - the viewing platform on the bank: round posts on concrete footings, double beams, joists, a board
    deck, railings on three sides, steps with stringers, a bench facing the view, fixed binoculars;
  FallenTree, LogCut - the windfall: a dead spruce torn out with its root plate, fallen downhill across the road, sawn
    straight at both road edges (fresh pale cuts, sawdust), the cut piece dragged onto the far verge.
Frames: each prefab its own (Update 3's FBX after import): x / y / z, z up, metres; Unity prefab-local (-x, z, -y).
Faces carry a float 'zone' (atlases: Signs, Gate, Bridge, Deck, Windfall) or explicit 'PSX' UVs (panel: the sign faces;
chainlink / barbed: tiled cut-outs; lens:reflector)."""
import math
import bmesh
import numpy as np
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, socket, face, box6, KBS, CONTRACT
import road_spec as S
import road_tex as RT

TAU = 2 * math.pi
uv = RT.uv

# ---------------------------------------------------------------- zones (800+)
(Z_SPOST, Z_SCAP, Z_SBACK, Z_SRAIL, Z_SCLAMP, Z_EPBODY, Z_EPBAND) = range(800, 807)
(Z_CONC, Z_CONCCAP, Z_GTUBE, Z_GHINGE, Z_GPLATE, Z_GBAR, Z_CHAIN, Z_GBOLT, Z_GFOOT) = range(810, 819)
(Z_PLANK, Z_STRIP, Z_STRINGER, Z_CAPB, Z_PILE, Z_BRACE, Z_CRIB, Z_STONE, Z_RPOST, Z_RAIL, Z_CURB, Z_STEEL, Z_LOGEND,
 Z_SILL, Z_BSPOST, Z_BSBACK) = range(820, 836)
(Z_DBOARD, Z_DJOIST, Z_DLEG, Z_DRPOST, Z_DRAIL, Z_DSTEP, Z_BENCH, Z_SCOPE, Z_SCOPEPOST, Z_DFOOT, Z_DEND,
 Z_DSTEEL) = range(840, 852)
(Z_TBARK, Z_TWOOD, Z_TCUT, Z_TROOT, Z_TBRANCH, Z_SAWDUST, Z_SOIL, Z_TSTONE, Z_DRAG, Z_TBREAK) = range(860, 870)

DRAFT_COL = {
    Z_SPOST: (160, 164, 160), Z_SCAP: (60, 62, 64), Z_SBACK: (128, 130, 126), Z_SRAIL: (170, 172, 170),
    Z_SCLAMP: (150, 152, 150), Z_EPBODY: (226, 226, 220), Z_EPBAND: (30, 30, 30),
    Z_CONC: (150, 148, 140), Z_CONCCAP: (160, 158, 150), Z_GTUBE: (156, 160, 158), Z_GHINGE: (60, 58, 56),
    Z_GPLATE: (226, 224, 216), Z_GBAR: (110, 112, 112), Z_CHAIN: (120, 70, 40), Z_GBOLT: (90, 92, 92),
    Z_GFOOT: (120, 118, 110),
    Z_PLANK: (122, 112, 96), Z_STRIP: (96, 86, 72), Z_STRINGER: (104, 92, 76), Z_CAPB: (98, 86, 70), Z_PILE: (96, 84, 68),
    Z_BRACE: (118, 106, 90), Z_CRIB: (92, 80, 64), Z_STONE: (120, 118, 110), Z_RPOST: (112, 102, 86),
    Z_RAIL: (120, 110, 94), Z_CURB: (100, 90, 76), Z_STEEL: (50, 48, 46), Z_LOGEND: (150, 132, 104), Z_SILL: (100, 88, 72),
    Z_BSPOST: (160, 164, 160), Z_BSBACK: (128, 130, 126),
    Z_DBOARD: (132, 124, 104), Z_DJOIST: (112, 106, 90), Z_DLEG: (110, 104, 88), Z_DRPOST: (120, 112, 96),
    Z_DRAIL: (126, 118, 100), Z_DSTEP: (120, 112, 94), Z_BENCH: (130, 104, 72), Z_SCOPE: (36, 40, 38),
    Z_SCOPEPOST: (96, 60, 36), Z_DFOOT: (140, 138, 130), Z_DEND: (150, 134, 106), Z_DSTEEL: (60, 58, 56),
    Z_TBARK: (92, 84, 76), Z_TWOOD: (138, 130, 116), Z_TCUT: (214, 186, 136), Z_TROOT: (70, 58, 44),
    Z_TBRANCH: (110, 100, 88), Z_SAWDUST: (206, 172, 116), Z_SOIL: (58, 48, 38), Z_TSTONE: (118, 116, 108),
    Z_DRAG: (74, 62, 48), Z_TBREAK: (150, 140, 120)}
SIGN_ZONES = list(range(800, 807))
GATE_ZONES = list(range(810, 819))
BRIDGE_ZONES = list(range(820, 836))
DECK_ZONES = list(range(840, 852))
WIND_ZONES = list(range(860, 870))


# ---------------------------------------------------------------- helpers
def V(*a):
    return Vector(a[0]) if len(a) == 1 else Vector(a)


def _orient(ring, t):
    """a ring counter-clockwise round t (outward lofts)"""
    return ring if K.newell(ring).dot(t) > 0 else list(reversed(ring))


def _frame(t, up):
    t = Vector(t).normalized()
    up = Vector(up)
    if abs(t.dot(up.normalized())) > 0.98:
        up = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
    s = t.cross(up).normalized()
    u = s.cross(t).normalized()
    return t, s, u


def _section(w, h, ch):
    hw, hh = w / 2, h / 2
    if ch <= 1e-6:
        return [(hw, hh), (hw, -hh), (-hw, -hh), (-hw, hh)]
    return [(hw - ch, hh), (hw, hh - ch), (hw, -hh + ch), (hw - ch, -hh), (-hw + ch, -hh), (-hw, -hh + ch), (-hw, hh - ch),
            (-hw + ch, hh)]


def bar(k, a, b, w, h, zone, ch=0.0, up=(0, 0, 1), zcap=None, caps=True):
    """a bar a -> b of section w (across) x h (along `up`), its long edges chamfered by ch; end faces zone zcap"""
    a, b = Vector(a), Vector(b)
    t, s, u = _frame(b - a, up)
    sec = _section(w, h, ch)
    ra = _orient([a + s * x + u * y for x, y in sec], t)
    rb = _orient([b + s * x + u * y for x, y in sec], t)
    zc = zone if zcap is None else zcap
    k.loft([ra, rb], [zone], cap0=zc if caps else None, cap1=zc if caps else None)


def bars(k, pts, w, h, zone, ch=0.0, up=(0, 0, 1), zcap=None):
    """a bar along a polyline (mitred at the bends)"""
    pts = [Vector(p) for p in pts]
    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        t, s, u = _frame(t, up)
        rings.append(_orient([p + s * x + u * y for x, y in _section(w, h, ch)], (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])))
    zc = zone if zcap is None else zcap
    k.loft(rings, [zone] * (len(rings) - 1), cap0=zc, cap1=zc)


def rod(k, a, b, r, zone, seg=8, r2=None, caps=True, zcap=None):
    """round bar / tube / log a -> b (end faces zone zcap)"""
    a, b = Vector(a), Vector(b)
    t = (b - a).normalized()
    ra, _ = k.ring_pts(a, t, r, seg)
    rb, _ = k.ring_pts(b, t, r if r2 is None else r2, seg)
    zc = zone if zcap is None else zcap
    k.loft([ra, rb], [zone], cap0=zc if caps else None, cap1=zc if caps else None)


def log_seg(k, a, b, r0, r1, zone, zend, seg=8, n=1, wob=0.0, seed=0, caps=(True, True), twist=0.0):
    """a round log a -> b tapering r0 -> r1 in n lengths, its radius wobbling by wob (knots, bulges); end grain zend"""
    a, b = Vector(a), Vector(b)
    t = (b - a).normalized()
    rng = np.random.default_rng(seed)
    rings, ref = [], None
    for i in range(n + 1):
        f = i / n
        c = a.lerp(b, f)
        r = r0 + (r1 - r0) * f
        ring, e1 = k.ring_pts(c, t, r, seg, ref)
        ref = e1
        if wob > 0:
            j = 1 + wob * (rng.random(seg) * 2 - 1) * (0.4 if i in (0, n) else 1.0)
            ring = [c + (q - c) * float(jj) for q, jj in zip(ring, j)]
        rings.append(ring)
    k.loft(rings, [zone] * n, cap0=zend if caps[0] else None, cap1=zend if caps[1] else None)
    return rings


def disc_face(k, c, n, r, zone, seg=10):
    ring, _ = k.ring_pts(Vector(c), Vector(n), r, seg)
    face(k, ring, zone, n)


def bolt(k, c, n, r=0.012, h=0.010, zone=Z_STEEL, seg=6, washer=0.0):
    """a bolt head (hex) / nut, optionally on a washer, on a face with outward normal n (no hidden bottom faces)"""
    c, n = Vector(c), Vector(n).normalized()
    if washer > 0:
        ra, _ = k.ring_pts(c - n * 0.001, n, washer, 6)
        rb, _ = k.ring_pts(c + n * 0.003, n, washer, 6)
        k.loft([ra, rb], [zone], cap1=zone)
        c = c + n * 0.003
    ra, _ = k.ring_pts(c - n * 0.001, n, r, seg)
    rb, _ = k.ring_pts(c + n * h, n, r, seg)
    k.loft([ra, rb], [zone], cap1=zone)


def rrect_xz(x0, x1, z0, z1, r, k=3):
    """rounded rectangle in the x-z plane, counter-clockwise seen from -y (x right, z up)"""
    pts = []
    for cx, cz, a0 in ((x1 - r, z0 + r, -90), (x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180)):
        for i in range(k + 1):
            a = math.radians(a0 + 90 * i / k)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def ground_patch(name, x0, x1, y0, y1, step=0.5):
    """the ground under a prefab as a mesh (for the AO bake: the shading where things meet the ground)"""
    xs = np.arange(x0, x1 + 1e-6, step)
    ys = np.arange(y0, y1 + 1e-6, step)
    verts = [(float(x), float(y), S.ground(name, float(x), float(y))) for y in ys for x in xs]
    nx = len(xs)
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(len(ys) - 1)
             for i in range(nx - 1)]
    return verts, faces


# ================================================================ the road signs
def _plate(k, kf, name, W, Z0, Z1, region, y_face=S.FACE_Y, y_back=S.PLATE_BACK, zone=Z_SBACK, xc=0.0):
    """the sign plate: the face (panel UVs, its own KB), the folded edge and the back (zone), rounded corners"""
    ol = rrect_xz(xc - W / 2, xc + W / 2, Z0, Z1, S.CORNER_R, 3)
    u0, v0, u1, v1 = region
    pts = [Vector((x, y_face, z)) for x, z in ol]
    uvs = [(u0 + (x - (xc - W / 2)) / W * (u1 - u0), v0 + (z - Z0) / (Z1 - Z0) * (v1 - v0)) for x, z in ol]
    face(kf, pts, 0.0, (0, -1, 0), uvs)
    back = [Vector((x, y_back, z)) for x, z in ol]
    n = len(ol)
    for i in range(n):
        j = (i + 1) % n
        face(k, [pts[i], pts[j], back[j], back[i]], zone,
             Vector((((ol[i][0] + ol[j][0]) / 2) - xc, 0, ((ol[i][1] + ol[j][1]) / 2) - (Z0 + Z1) / 2)))
    face(k, back, zone, (0, 1, 0))


def _post(k, name, x, top, y=S.POST_Y, r=S.POST_R, zone=Z_SPOST, cap=Z_SCAP, bot=None):
    """a galvanised tube post from below the ground (Update 3's -0.40, deeper under a bank) to `top`, a domed cap"""
    if bot is None:
        bot = min(S.POST_BOT, S.ground(name, x, y) - 0.35)
    rod(k, (x, y, bot), (x, y, top), r, zone, seg=8, caps=False)
    face(k, k.ring_pts(Vector((x, y, bot)), (0, 0, -1), r, 8)[0], zone, (0, 0, -1))
    k.lathe(Vector((x, y, top - 0.012)), (0, 0, 1), [(0.0, r + 0.003), (0.018, r + 0.003), (0.026, r * 0.70), (0.032, 0.0)],
            cap, 8, cap0=True, cap1=False)


def _clamp(k, x, z, y=S.POST_Y, r=S.POST_R):
    """tube clamp round the post gripping the rail: a band and its bolt behind the post"""
    rod(k, (x, y, z - 0.014), (x, y, z + 0.014), r + 0.004, Z_SCLAMP, seg=8)
    rod(k, (x - 0.026, y + r + 0.006, z), (x + 0.026, y + r + 0.006, z), 0.006, Z_SCLAMP, seg=6)


def road_sign(name):
    s = S.SIGNS[name]
    w, z0, z1 = s['face']
    B = S.BORDER
    W, Z0, Z1 = w + 2 * B, z0 - B, z1 + B
    k = kb(name, 'Signs')
    kf = kb(name + '_Face', 'panel')
    _plate(k, kf, name, W, Z0, Z1, uv(name))
    px = s['post']
    for sx in (-1, 1):
        _post(k, name, sx * px, Z1 + 0.030)
    H = Z1 - Z0
    rails = (Z0 + 0.30 * H, Z1 - 0.30 * H) if H > 0.30 else (Z0 + 0.28 * H, Z1 - 0.28 * H)
    rx = px + 0.10
    for zr in rails:                                                   # hat rails riveted to the back
        k.box(-rx, rx, S.PLATE_BACK, S.PLATE_BACK + 0.004, zr - 0.016, zr + 0.016, Z_SRAIL)
        k.box(-rx, rx, S.PLATE_BACK + 0.004, -0.0005, zr - 0.010, zr + 0.010, Z_SRAIL)
        for sx in (-1, 1):
            _clamp(k, sx * px, zr)
    part(name, 'static', (0, 0, 0), note=s['note'] + ': ' + s['de'] + (' / ' + s['en'] if s['en'] else ''))
    part(name + '_Face', 'static', (0, S.FACE_Y, (Z0 + Z1) / 2), parent=name, note='the sign face (panel atlas)')


# ================================================================ the delineator post (EuroPost)
def europost():
    """German Leitpfosten: a white plastic post, chamfered section 0.12 (across the road, x) x 0.10 (along it, y), 1.00
    above the ground, a black band at the top with an amber reflector both ways (along the road), a hipped top"""
    p = S.POST
    k = kb('EuroPost', 'Signs')
    kl = kb('EuroPost_Refl', 'lens:reflector')
    w, d, h = p['w'], p['d'], p['h']
    sec = [(w / 2 - 0.015, d / 2), (w / 2, d / 2 - 0.012), (w / 2, -d / 2 + 0.012), (w / 2 - 0.015, -d / 2),
           (-w / 2 + 0.015, -d / 2), (-w / 2, -d / 2 + 0.012), (-w / 2, d / 2 - 0.012), (-w / 2 + 0.015, d / 2)]
    zb = h - p['band']
    rings = [_orient([Vector((x, y, z)) for x, y in sec], Vector((0, 0, 1))) for z in (-p['below'], zb, h - 0.03)]
    k.loft(rings[:2], [Z_EPBODY], cap0=Z_EPBODY)
    k.loft(rings[1:], [Z_EPBAND])
    top = Vector((0, 0, h))
    r3 = rings[2]
    for i in range(len(r3)):                                          # hipped top
        face(k, [r3[i], r3[(i + 1) % len(r3)], top], Z_EPBAND, (r3[i] + r3[(i + 1) % len(r3)]) / 2 - Vector((0, 0, h - 0.06)))
    rw, rh = p['refl']
    zc = zb + p['band'] / 2 - 0.01
    for sy in (-1, 1):                                                 # the reflectors in a black bezel
        ya, yb_ = sorted((sy * d / 2, sy * (d / 2 + 0.004)))
        box6(k, (-rw / 2 - 0.006, ya, zc - rh / 2 - 0.006), (rw / 2 + 0.006, yb_, zc + rh / 2 + 0.006), Z_EPBAND,
             skip=('-y',) if sy > 0 else ('+y',))
        yl = sy * (d / 2 + 0.0055)
        face(kl, [Vector((-rw / 2, yl, zc - rh / 2)), Vector((rw / 2, yl, zc - rh / 2)), Vector((rw / 2, yl, zc + rh / 2)),
                  Vector((-rw / 2, yl, zc + rh / 2))], 0.0, (0, sy, 0), [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)])
    part('EuroPost', 'static', (0, 0, 0), note='delineator post (Update 3\'s scatter model: 48 along the road, list rocks)')
    part('EuroPost_Refl', 'static', (0, 0, zc), parent='EuroPost', note='the reflectors (M_Reflector, amber, emissive)')


# ================================================================ the zone gate (SPERRGEBIET)
def zone_gate():
    g = S.GATE
    k = kb('ZoneGate', 'Gate')
    km = kb('ZoneGate_Mesh', 'chainlink')
    kw = kb('ZoneGate_Barbed', 'barbed')
    kf = kb('ZoneGate_Face', 'panel')
    P, half = g['pillar_x'], g['pillar'] / 2
    ch = 0.015
    for sx in (-1, 1):                                                  # pillars: chamfered shafts on footings, caps
        cx = sx * P
        gz = min(S.ground('ZoneGate', cx + dx, dy) for dx in (-half, half) for dy in (-half, half))
        bot = gz - 0.45
        sec = _section(g['pillar'], g['pillar'], ch)
        r0 = _orient([Vector((cx + x, y, bot)) for x, y in sec], Vector((0, 0, 1)))
        r1 = _orient([Vector((cx + x, y, g['pillar_top'])) for x, y in sec], Vector((0, 0, 1)))
        k.loft([r0, r1], [Z_CONC], cap0=Z_CONC)
        face(k, r1, Z_CONC, (0, 0, 1))
        cw, chh = g['cap']
        box6(k, (cx - cw / 2, -cw / 2, g['pillar_top']), (cx + cw / 2, cw / 2, g['pillar_top'] + chh), Z_CONCCAP,
             skip=('+z',))
        top = g['pillar_top'] + chh                                    # the cap's top falls to its edges (weathering)
        cs = [Vector((cx + a * cw / 2, b * cw / 2, top)) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        apex = Vector((cx, 0, top + 0.03))
        for i in range(4):
            face(k, [cs[i], cs[(i + 1) % 4], apex], Z_CONCCAP, (cs[i] + cs[(i + 1) % 4]) / 2 - Vector((cx, 0, top - 0.2)))
        fz = gz - 0.02                                                 # footing collar just proud of the ground
        box6(k, (cx - half - 0.07, -half - 0.07, gz - 0.40), (cx + half + 0.07, half + 0.07, fz + 0.06), Z_GFOOT)
    x_in, x_out = g['leaf_x']
    r = g['tube_r']
    zb, zt = g['rail_z']
    for sx in (-1, 1):                                                 # the two leaves (left -x, right +x)
        xh, xl = sx * x_out, sx * x_in                                  # hinge stile, latch stile
        xm = sx * g['plate_x']
        for xx in (xh, xl):
            rod(k, (xx, 0, zb - 0.06), (xx, 0, zt + 0.02), r, Z_GTUBE, seg=8)
            k.lathe(Vector((xx, 0, zt + 0.02)), (0, 0, 1), [(0.0, r), (0.012, r * 0.6), (0.016, 0.0)], Z_GTUBE, 8,
                    cap0=False)
            face(k, k.ring_pts(Vector((xx, 0, zb - 0.06)), (0, 0, -1), r, 8)[0], Z_GTUBE, (0, 0, -1))
        a, b = min(xh, xl) + r * 0.9, max(xh, xl) - r * 0.9
        for zz in (zb, zt):
            rod(k, (a, 0, zz), (b, 0, zz), r, Z_GTUBE, seg=8, caps=False)
        rod(k, (xm, 0, zb + r * 0.9), (xm, 0, zt - r * 0.9), g['mid_r'], Z_GTUBE, seg=6, caps=False)     # mid stile
        p0 = Vector((xh - sx * r * 0.8, 0, zb + r * 0.8))               # brace: hinge foot -> latch head (compression)
        p1 = Vector((xl + sx * r * 0.8, 0, zt - r * 0.8))
        rod(k, p0, p1, g['brace_r'], Z_GTUBE, seg=6, caps=False)
        mz0, mz1 = g['mesh_z']
        u0, u1 = sorted((xh - sx * (r + 0.004), xl + sx * (r + 0.004)))
        for dd, sg in ((-0.0006, -1), (0.0006, 1)):                    # chain-link in the frame's plane, both sides
            face(km, [Vector((u0, dd, mz0)), Vector((u1, dd, mz0)), Vector((u1, dd, mz1)), Vector((u0, dd, mz1))], 0.0,
                 (0, sg, 0), [(u0 / 0.5, mz0 / 0.5), (u1 / 0.5, mz0 / 0.5), (u1 / 0.5, mz1 / 0.5), (u0 / 0.5, mz1 / 0.5)])
        for xx in (xh, xm, xl):                                        # barbed-wire uprights (flat bar 40 x 6) on the
            ya = (r if xx != xm else g['mid_r']) - 0.004               # back of the stiles
            k.box(xx - 0.020, xx + 0.020, ya, r + 0.0065, zt - 0.10, g['barb_top'], Z_GTUBE)
        yb = r + 0.0075
        bu0, bu1 = sorted((xh, xl))
        for dd, sg in ((-0.0006, -1), (0.0006, 1)):
            fz0, fz1 = g['barb_foot'], g['barb_foot'] + g['barb_h']
            face(kw, [Vector((bu0, yb + dd, fz0)), Vector((bu1, yb + dd, fz0)), Vector((bu1, yb + dd, fz1)),
                      Vector((bu0, yb + dd, fz1))], 0.0, (0, sg, 0),
                 [(bu0 / 0.5, 0.0), (bu1 / 0.5, 0.0), (bu1 / 0.5, 1.0), (bu0 / 0.5, 1.0)])
        for zz in g['hinge_z']:                                         # hinges: anchor plate + pin on the pillar, collars
            xp = sx * (P - half)
            k.box(min(xp, xp - sx * 0.012), max(xp, xp - sx * 0.012), -0.07, 0.07, zz - 0.09, zz + 0.09, Z_GHINGE)
            for dy in (-0.045, 0.045):
                for dz in (-0.055, 0.055):
                    bolt(k, (xp - sx * 0.012, dy, zz + dz), (-sx, 0, 0), r=0.010, h=0.008, zone=Z_GHINGE)
            bar(k, (xp - sx * 0.012, 0, zz - 0.030), (xh + sx * 0.0, 0, zz - 0.030), 0.040, 0.016, Z_GHINGE)
            rod(k, (xh, 0, zz - 0.022), (xh, 0, zz + 0.050), r + 0.008, Z_GHINGE, seg=8)
            rod(k, (xh, 0, zz - 0.040), (xh, 0, zz - 0.022), 0.010, Z_GHINGE, seg=6)
        # the SPERRGEBIET plate on its frame: left leaf to -y, right leaf to +y (Update 3's)
        sy = -1 if sx < 0 else 1
        pw, ph = g['plate']
        yf = sy * (r + 0.0125 + 0.016)                                  # the face 16 mm in front of the plate's back
        for zz in g['bars_z']:                                          # two grey flat bars on the mid stile
            ax0, ax1 = sorted((sx * g['bars_x'][0], sx * g['bars_x'][1]))
            k.box(ax0, ax1, min(sy * (r + 0.002), sy * (r + 0.012)), max(sy * (r + 0.002), sy * (r + 0.012)),
                  zz - 0.020, zz + 0.020, Z_GBAR)
            for xx in (ax0 + 0.03, ax1 - 0.03):                          # hook bolts through the chain-link
                rod(k, (xx, sy * 0.004, zz), (xx, sy * (r + 0.016), zz), 0.005, Z_GBAR, seg=5)
            rod(k, (xm - 0.035, sy * (g['mid_r'] + 0.012), zz), (xm + 0.035, sy * (g['mid_r'] + 0.012), zz), 0.006,
                Z_GBAR, seg=5)
        yback = sy * (r + 0.0125)
        _plate_gate(k, kf, xm, g['plate_cz'], pw, ph, yf, yback, sy)
    # the latch: a chain round both latch stiles and a padlock; the drop bolt on the right leaf into a ground socket
    zl = g['lock_z']
    for i, dz in enumerate((-0.03, 0.0, 0.03)):
        pts = []
        for a in range(0, 360, 30):
            ang = math.radians(a)
            pts.append(Vector((0.085 * math.cos(ang), 0.045 * math.sin(ang), zl + dz + 0.012 * math.sin(2 * ang + i))))
        pts.append(pts[0])
        k.tube(pts, 0.007, Z_CHAIN, seg=5, caps=False)
    pl = Vector((0.0, 0.070, zl - 0.10))
    k.box(pl.x - 0.032, pl.x + 0.032, pl.y - 0.014, pl.y + 0.014, pl.z - 0.040, pl.z + 0.010, Z_CHAIN)       # padlock body
    k.tube([pl + Vector((-0.020, 0, 0.010)), pl + Vector((-0.020, 0, 0.045)), pl + Vector((0, 0, 0.060)),
            pl + Vector((0.020, 0, 0.045)), pl + Vector((0.020, 0, 0.010))], 0.005, Z_CHAIN, seg=5, caps=True)
    k.tube([Vector((0.02, 0.05, zl - 0.02)), pl + Vector((0.0, 0, 0.058))], 0.006, Z_CHAIN, seg=5, caps=True)
    xb = x_in + 0.050
    rod(k, (xb, -0.050, 0.020), (xb, -0.050, 0.62), 0.008, Z_GBOLT, seg=6)                  # drop bolt
    for zz in (0.22, 0.52):
        k.box(xb - 0.014, xb + 0.014, -0.058, -0.030, zz - 0.020, zz + 0.020, Z_GBOLT)
    bar(k, (xb, -0.050, 0.60), (xb + 0.06, -0.050, 0.60), 0.012, 0.012, Z_GBOLT)
    gz = S.ground('ZoneGate', xb, -0.05)
    box6(k, (xb - 0.10, -0.15, gz - 0.25), (xb + 0.10, 0.05, gz + 0.012), Z_GFOOT)      # socket block in the road
    rod(k, (xb, -0.050, gz + 0.012), (xb, -0.050, gz + 0.020), 0.020, Z_GBOLT, seg=8)
    part('ZoneGate', 'static', (0, 0, 0), note='the zone gate (SPERRGEBIET) behind the car at the start, shut; '
                                               'static as Update 3 (no moving parts)')
    for n_, nt in (('ZoneGate_Mesh', 'chain-link of the leaves (M_Road_ChainLink, alpha cut-out, 0.5 m tile)'),
                   ('ZoneGate_Barbed', 'barbed wire over the leaves (M_Road_Barbed, alpha cut-out)'),
                   ('ZoneGate_Face', 'the SPERRGEBIET plates\' faces (panel atlas)')):
        part(n_, 'static', (0, 0, 1.2), parent='ZoneGate', note=nt)


def _plate_gate(k, kf, xc, zc, pw, ph, yf, yback, sy):
    """the gate's sign plate facing sy (-1: -y, +1: +y): face (panel), folded edge, back"""
    ol = rrect_xz(xc - pw / 2, xc + pw / 2, zc - ph / 2, zc + ph / 2, 0.018, 2)
    u0, v0, u1, v1 = uv('gate')
    pts, uvs = [], []
    for x, z in ol:
        pts.append(Vector((x, yf, z)))
        fx = (x - (xc - pw / 2)) / pw
        if sy > 0:                                                        # seen from +y the text runs to -x
            fx = 1 - fx
        uvs.append((u0 + fx * (u1 - u0), v0 + (z - (zc - ph / 2)) / ph * (v1 - v0)))
    face(kf, pts, 0.0, (0, sy, 0), uvs)
    back = [Vector((x, yback, z)) for x, z in ol]
    n = len(ol)
    for i in range(n):
        j = (i + 1) % n
        face(k, [pts[i], pts[j], back[j], back[i]], Z_GPLATE,
             Vector(((ol[i][0] + ol[j][0]) / 2 - xc, 0, (ol[i][1] + ol[j][1]) / 2 - zc)))
    face(k, back, Z_GPLATE, (0, -sy, 0))


# ================================================================ the timber bridge (Bridge30)
def _z262(k, kf, base, face_dir, gname, yaw_deg):
    """the weight-limit sign on its post, built facing -y at the origin, turned and placed (base: post foot x, y)"""
    t = K.KB()
    tf = K.KB()
    R = 0.21
    g = S.ground(gname, base[0], base[1])
    zc = g + 1.75
    _post(t, gname, 0.0, zc + R + 0.03, bot=g - 0.50)
    ring = [(R * math.cos(TAU * i / 16), zc + R * math.sin(TAU * i / 16)) for i in range(16)]
    u0, v0, u1, v1 = uv('z262')
    pts = [Vector((x, S.FACE_Y, z)) for x, z in ring]
    face(tf, pts, 0.0, (0, -1, 0), [(u0 + (x + R) / (2 * R) * (u1 - u0), v0 + (z - zc + R) / (2 * R) * (v1 - v0)) for x, z in ring])
    back = [Vector((x, S.PLATE_BACK, z)) for x, z in ring]
    for i in range(16):
        j = (i + 1) % 16
        face(t, [pts[i], pts[j], back[j], back[i]], Z_BSBACK, Vector((ring[i][0], 0, ring[i][1] - zc)))
    face(t, back, Z_BSBACK, (0, 1, 0))
    for zr in (zc - 0.09, zc + 0.09):
        t.box(-0.13, 0.13, S.PLATE_BACK, -0.0005, zr - 0.014, zr + 0.014, Z_BSPOST)
        _clamp(t, 0.0, zr)
    for kk in (t, tf):
        for f in kk.bm.faces:                                          # the post's zone in the bridge's atlas
            if round(f[kk.zl]) == Z_SPOST:
                f[kk.zl] = Z_BSPOST
            elif round(f[kk.zl]) in (Z_SCAP, Z_SCLAMP):
                f[kk.zl] = Z_BSPOST
    # the bottom of the post: the ground was sampled at the origin of the temporary frame -> resample here
    M = Matrix.Translation(Vector((base[0], base[1], 0.0))) @ Matrix.Rotation(math.radians(yaw_deg), 4, 'Z')
    K.merge_kb(k, t, M)
    K.merge_kb(kf, tf, M)


def bridge():
    b = S.BRIDGE
    k = kb('Bridge30', 'Bridge')
    kf = kb('Bridge30_Face', 'panel')
    rng = np.random.default_rng(30)
    x0, x1 = b['deck_x']
    hw, pt = b['half_w'], b['plank_top']
    n = int(round((x1 - x0) / b['plank_pitch'])) + 1
    for i in range(n):                                                 # deck planks (transverse), each a little different
        xc = x0 + i * b['plank_pitch']
        w = b['plank_w'] + rng.uniform(-0.014, 0.012)
        dz = rng.uniform(-0.006, 0.0)
        ya, yb = -hw + rng.uniform(-0.01, 0.02), hw + rng.uniform(-0.02, 0.01)
        R = Matrix.Rotation(math.radians(rng.uniform(-0.7, 0.7)), 3, 'Z')
        k.box_m(Vector((xc, (ya + yb) / 2, pt - b['plank_t'] / 2 + dz)), (w, yb - ya, b['plank_t']), Z_PLANK, R)
    sb = pt + 0.0                                                      # running strips: three boards each, staggered joints
    for yc in b['strips_y']:
        bw = (b['strip_w'] - 0.02 * (b['strip_boards'] - 1)) / b['strip_boards']
        for j in range(b['strip_boards']):
            yy = yc + (j - (b['strip_boards'] - 1) / 2) * (bw + 0.02)
            xs = [x0 - 0.12 + 0.40]
            while xs[-1] < x1 + 0.12 - 0.40 - 4.6:
                xs.append(xs[-1] + rng.uniform(3.6, 5.4))
            xs.append(x1 + 0.12 - 0.40)
            for a, c in zip(xs[:-1], xs[1:]):
                a2, c2 = a + 0.004, c - 0.004
                bar(k, (a2, yy, sb + 0.035), (c2, yy, sb + 0.035), bw, 0.070, Z_STRIP, ch=0.008, zcap=Z_STRIP)
            for xe, sg in ((x0 - 0.12, -1), (x1 + 0.12, 1)):           # wedge ramps at the ends (the car's wheels)
                xa, xb_ = (xe, xe - sg * 0.40)
                lo, hi = sorted((xa, xb_))
                y0_, y1_ = yy - bw / 2, yy + bw / 2
                top_hi, top_lo = sb + 0.070, sb + 0.004
                za = top_lo if sg < 0 else top_hi
                zb_ = top_hi if sg < 0 else top_lo
                if sg < 0:
                    poly = [(lo, sb), (hi, sb), (hi, top_hi), (lo, top_lo)]
                else:
                    poly = [(lo, sb), (hi, sb), (hi, top_lo), (lo, top_hi)]
                for q in range(4):
                    pa, pb = poly[q], poly[(q + 1) % 4]
                    face(k, [Vector((pa[0], y0_, pa[1])), Vector((pb[0], y0_, pb[1])), Vector((pb[0], y1_, pb[1])),
                             Vector((pa[0], y1_, pa[1]))], Z_STRIP,
                         Vector(((pa[0] + pb[0]) / 2 - (lo + hi) / 2, 0, (pa[1] + pb[1]) / 2 - (sb + 0.03))))
                face(k, [Vector((p_[0], y0_, p_[1])) for p_ in poly], Z_STRIP, (0, -1, 0))
                face(k, [Vector((p_[0], y1_, p_[1])) for p_ in poly], Z_STRIP, (0, 1, 0))
    for sx in (-1, 1):                                                 # approach boards: the wheel tracks run on from the
        xa_ = sx * (x1 + 0.145)                                        # road onto the deck over the dip at its ends
        xr_ = sx * 16.60
        for yc in b['strips_y']:
            gz = min(S.ground('Bridge30', xr_, yc + dy) for dy in (-0.35, 0.0, 0.35))
            ta, tb_ = sb + 0.004, gz + 0.010
            y0_, y1_ = yc - b['strip_w'] / 2, yc + b['strip_w'] / 2
            poly = [(xa_, ta - 0.06), (xr_, tb_ - 0.06), (xr_, tb_), (xa_, ta)]
            cx_ = (xa_ + xr_) / 2
            for q in range(4):
                pa, pb = poly[q], poly[(q + 1) % 4]
                face(k, [Vector((pa[0], y0_, pa[1])), Vector((pb[0], y0_, pb[1])), Vector((pb[0], y1_, pb[1])),
                         Vector((pa[0], y1_, pa[1]))], Z_STRIP, Vector(((pa[0] + pb[0]) / 2 - cx_, 0, (pa[1] + pb[1]) / 2 - (ta + tb_) / 2 + 0.03)))
            face(k, [Vector((p_[0], y0_, p_[1])) for p_ in poly], Z_STRIP, (0, -1, 0))
            face(k, [Vector((p_[0], y1_, p_[1])) for p_ in poly], Z_STRIP, (0, 1, 0))
            for bx in (0.40, 0.95):                                    # bolts into the sleepers
                xb_ = xa_ + sx * bx
                zt_ = ta + (tb_ - ta) * bx / abs(xr_ - xa_)
                for dy in (-0.22, 0.0, 0.22):
                    bolt(k, (xb_, yc + dy, zt_), (0, 0, 1), r=0.016, h=0.006)
        for bx in (0.40, 0.95):                                        # two sleepers under them, bedded in the road
            xs_ = xa_ + sx * bx
            zt_ = sb + 0.004 - 0.06 + (min(S.ground('Bridge30', xr_, y) for y in (-0.95, 0.95)) + 0.010 - sb - 0.004) * bx / abs(xr_ - xa_)
            bar(k, (xs_, -1.55, zt_ - 0.07), (xs_, 1.55, zt_ - 0.07), 0.16, 0.14, Z_CURB, ch=0.012, zcap=Z_LOGEND)
    cw, chh = b['curb']                                                # curbs on spacer blocks
    for sy in (-1, 1):
        yc = sy * b['curb_y']
        for xa, xc_ in ((x0 - 0.05, -0.004), (0.004, x1 + 0.05)):
            bar(k, (xa, yc, pt + 0.045 + chh / 2), (xc_, yc, pt + 0.045 + chh / 2), cw, chh, Z_CURB, ch=0.012)
        for xs_ in np.arange(x0 + 0.4, x1, 1.5):
            k.box(xs_ - 0.10, xs_ + 0.10, yc - cw / 2 + 0.005, yc + cw / 2 - 0.005, pt, pt + 0.045, Z_CURB)
        for xs_ in np.arange(x0 + 0.4, x1, 3.0):
            bolt(k, (xs_, yc, pt + 0.045 + chh), (0, 0, 1), r=0.016, h=0.006)
    rs = b['stringer_r']                                                # log stringers: three spans, butt joints on the caps
    s_top = pt - b['plank_t'] - 0.002
    ends = [b['stringer_x'][0], b['joints_x'][0], b['joints_x'][1], b['stringer_x'][1]]
    for li, yc in enumerate(b['stringers_y']):
        for si, (a, c) in enumerate(zip(ends[:-1], ends[1:])):
            a2 = a + (0.003 if si > 0 else 0.0)
            c2 = c - (0.003 if si < 2 else 0.0)
            zc = s_top - rs
            log_seg(k, (a2, yc, zc), (c2, yc, zc), rs, rs, Z_STRINGER, Z_LOGEND, seg=10, n=5, wob=0.035,
                    seed=100 + li * 3 + si)
        for xj in b['joints_x']:                                       # joint straps both sides, bolted
            for sy in (-1, 1):
                yy = yc + sy * (rs + 0.012)
                bar(k, (xj - 0.40, yy, s_top - rs), (xj + 0.40, yy, s_top - rs), 0.008, 0.07, Z_STEEL, up=(0, 0, 1))
                for dx in (-0.22, 0.22):
                    bolt(k, (xj + dx, yy + sy * 0.004, s_top - rs), (0, sy, 0), r=0.013, h=0.010)
    cap = b['cap']
    cz1 = s_top - 2 * rs
    cz0 = cz1 - cap[1]
    piles = {}
    for xp in b['piers_x']:                                            # pile bents: cap, piles, walings, X-bracing
        bar(k, (xp, -cap[2] / 2, (cz0 + cz1) / 2), (xp, cap[2] / 2, (cz0 + cz1) / 2), cap[0], cap[1], Z_CAPB, ch=0.02,
            up=(0, 0, 1), zcap=Z_LOGEND)
        for yc in b['stringers_y']:                                    # drift pins stringer -> cap (heads on the cap's side)
            bolt(k, (xp + cap[0] / 2, yc, cz0 + 0.08), (1, 0, 0), r=0.014, h=0.010)
        gmax = -1e9
        for j, yp in enumerate(b['piles_y']):
            gz = S.ground('Bridge30', xp, yp)
            gmax = max(gmax, gz)
            lean = Vector((rng.uniform(-0.015, 0.015), rng.uniform(-0.015, 0.015), 0.0))
            top = Vector((xp, yp, cz0 + 0.03))
            bot = Vector((xp, yp, gz - 0.60)) + lean * (cz0 - gz + 0.6)
            nn = max(2, int((top - bot).length / 2.5))
            log_seg(k, bot, top, b['pile_r'] + 0.012, b['pile_r'] - 0.008, Z_PILE, Z_LOGEND, seg=8, n=nn, wob=0.03,
                    seed=200 + j + int(xp))
            piles[(xp, yp)] = (bot, top)
        zw = [cz0 - 0.38]                                              # walings: under the cap, (middle), near the ground
        lowest = gmax + 0.75
        if zw[0] - lowest > 5.0:
            zw.append((zw[0] + lowest) / 2)
        zw.append(lowest)
        bt = b['pile_r'] + 0.03
        for sx in (-1, 1):
            xf = xp + sx * bt
            for zz in zw:
                bar(k, (xf, -2.55, zz), (xf, 2.55, zz), 0.06, 0.22, Z_BRACE, ch=0.006, up=(0, 0, 1))
                for yp in b['piles_y']:
                    bolt(k, (xf + sx * 0.03, yp, zz), (sx, 0, 0), r=0.014, h=0.010)
            for za, zb_ in zip(zw[:-1], zw[1:]):
                xf2 = xp + sx * (bt + 0.055)
                if sx > 0:
                    pa, pb = Vector((xf2, -2.40, zb_ + 0.08)), Vector((xf2, 2.40, za - 0.08))
                else:
                    pa, pb = Vector((xf2, -2.40, za - 0.08)), Vector((xf2, 2.40, zb_ + 0.08))
                bar(k, pa, pb, 0.20, 0.05, Z_BRACE, ch=0.005, up=(sx, 0, 0))
    # the banks: a sill beam bedded under the stringers, two retaining logs below it, stones between
    for sx in (-1, 1):
        xs_ = sx * 14.25
        bar(k, (xs_, -2.60, cz1 - b['sill'][1] / 2), (xs_, 2.60, cz1 - b['sill'][1] / 2), b['sill'][0], b['sill'][1], Z_SILL,
            ch=0.015, zcap=Z_LOGEND)
        for q, xr in enumerate((sx * 13.62, sx * 13.18)):              # a stepped log revetment down the bank under it
            gz = min(S.ground('Bridge30', xr, yy) for yy in np.linspace(-2.6, 2.6, 9))
            zz = gz + 0.05
            log_seg(k, (xr, -2.75, zz), (xr, 2.75, zz), b['crib_r'], b['crib_r'] - 0.012, Z_CRIB, Z_LOGEND, seg=8, n=3,
                    wob=0.04, seed=300 + q + (sx > 0) * 5)
            for yy in (-2.1, 0.0, 2.1):                                # stakes in front of it
                xk = xr - sx * (b['crib_r'] + 0.07)
                g2 = S.ground('Bridge30', xk, yy)
                rod(k, (xk, yy, g2 - 0.7), (xk, yy, zz + 0.12), 0.06, Z_CRIB, seg=6, zcap=Z_LOGEND)
            for q2 in range(6):                                        # stones behind it
                yy = -2.2 + q2 * 0.88 + rng.uniform(-0.15, 0.15)
                xq = xr + sx * 0.26
                _stone(k, (xq, yy, S.ground('Bridge30', xq, yy) + 0.03), (0.30, 0.26, 0.18), Z_STONE,
                       500 + q * 10 + q2 + (sx > 0) * 40)
    # the railing: posts on packing blocks bolted to the outer stringers, handrail on the posts, mid rail inside
    pw = b['post']
    for sy in (-1, 1):
        yo = sy * b['post_y']
        y_in = yo - sy * pw / 2
        y_str = sy * (abs(b['stringers_y'][-1]) + rs)
        for xp in b['posts_x']:
            bar(k, (xp, yo, s_top - 2 * rs - 0.04), (xp, yo, b['rail_top'] - b['hand'][1]), pw, pw, Z_RPOST, ch=0.012,
                up=(1, 0, 0), zcap=Z_LOGEND)
            ya, yb_ = sorted((y_in, y_str - sy * 0.03))
            k.box(xp - 0.07, xp + 0.07, ya, yb_, s_top - rs - 0.16, s_top - rs + 0.14, Z_RPOST)
            for zz in (s_top - rs - 0.09, s_top - rs + 0.07):
                bolt(k, (xp, yo + sy * pw / 2, zz), (0, sy, 0), r=0.016, h=0.012, washer=0.030)
        hw_, hh_ = b['hand']
        zh = b['rail_top'] - hh_ / 2
        for xa, xc_ in zip(b['posts_x'][0::3][:-1], b['posts_x'][3::3]):
            bar(k, (xa - (0.07 if xa == b['posts_x'][0] else -0.002), yo, zh), (xc_ + (0.07 if xc_ == b['posts_x'][-1] else -0.002), yo, zh),
                hw_, hh_, Z_RAIL, ch=0.025, up=(0, 0, 1), zcap=Z_LOGEND)
        mw, mh = b['mid']
        ym = y_in - sy * mw / 2
        for xa, xc_ in ((b['posts_x'][0] - 0.07, -0.002), (0.002, b['posts_x'][-1] + 0.07)):
            bar(k, (xa, ym, b['mid_z']), (xc_, ym, b['mid_z']), mw, mh, Z_RAIL, ch=0.012, up=(0, 0, 1), zcap=Z_LOGEND)
    # the weight limit at both ends, on the right of the way in (the car comes from -x, the gate's side)
    _z262(k, kf, (-16.35, -3.35), (-1, 0, 0), 'Bridge30', -90.0)
    _z262(k, kf, (16.35, 3.15), (1, 0, 0), 'Bridge30', 90.0)
    part('Bridge30', 'static', (0, 0, 0), note='the timber bridge over the ravine (deck 30 m, Update 3\'s levels: the planks\' top '
                                               '-0.01, the running strips +0.06 - the car crosses here, S5)')
    part('Bridge30_Face', 'static', (0, 0, 1.5), parent='Bridge30', note='the weight-limit signs\' faces (panel atlas)')


def _stone(k, c, size, zone, seed, n=18):
    """low-poly field stone (hut_kit.rock)"""
    rng = np.random.default_rng(seed)
    pts = []
    for _ in range(n):
        v = rng.normal(size=3)
        v /= np.linalg.norm(v) + 1e-9
        v *= 0.80 + 0.20 * rng.random()
        v[2] = max(v[2], -0.85) if v[2] < 0 else min(v[2], 0.78)
        pts.append(Vector(c) + Vector((v[0] * size[0] / 2, v[1] * size[1] / 2, v[2] * size[2] / 2)))
    tmp = bmesh.new()
    vs = [tmp.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(tmp, input=vs)
    for f in list(tmp.faces):
        face(k, [Vector(v.co) for v in f.verts], zone, f.normal)
    tmp.free()


# ================================================================ the overlook deck (OverlookDeck)
def overlook():
    d = S.DECK
    k = kb('OverlookDeck', 'Deck')
    rng = np.random.default_rng(40)
    xa, xb = d['x']
    ya, yb = d['y']
    top = d['top']
    bw, bt = d['board']
    jz1 = top - bt                                                   # joists' top
    jz0 = jz1 - 0.14
    bz1 = jz0                                                        # double beams' top
    bz0 = bz1 - 0.20
    # footings and round posts
    for xx in d['legs_x']:
        for yy in d['legs_y']:
            g = min(S.ground('OverlookDeck', xx + dx, yy + dy) for dx in (-0.15, 0.15) for dy in (-0.15, 0.15))
            gmax = max(S.ground('OverlookDeck', xx + dx, yy + dy) for dx in (-0.15, 0.15) for dy in (-0.15, 0.15))
            ft = min(gmax + 0.10, bz0 - 0.03)
            rod(k, (xx, yy, g - 0.35), (xx, yy, ft), 0.15, Z_DFOOT, seg=10)
            log_seg(k, (xx, yy, ft), (xx, yy, bz1), d['leg_r'] + 0.005, d['leg_r'], Z_DLEG, Z_DEND, seg=8,
                    n=max(1, int((bz1 - ft) / 0.8)), wob=0.02, seed=int(xx * 10 + yy * 3 + 50))
            k.box(xx - 0.07, xx + 0.07, yy - 0.07, yy + 0.07, ft, ft + 0.006, Z_DSTEEL)                # post base plate
    for yy in d['legs_y']:                                             # double beams (clamps) both sides of the posts
        for sy in (-1, 1):
            yc = yy + sy * (d['leg_r'] + 0.025)
            bar(k, (xa - 0.05, yc, (bz0 + bz1) / 2), (xb + 0.05, yc, (bz0 + bz1) / 2), 0.05, 0.20, Z_DJOIST, ch=0.006,
                zcap=Z_DEND)
        for xx in d['legs_x']:
            for dz in (-0.05, 0.05):
                bolt(k, (xx, yy - (d['leg_r'] + 0.05), (bz0 + bz1) / 2 + dz), (0, -1, 0), r=0.014, h=0.010, washer=0.024)
    # the back legs stand tall on the slope: a diagonal between them, notched into the legs
    yy = d['legs_y'][1]
    for xa_, xb_ in ((d['legs_x'][1], d['legs_x'][2]), (d['legs_x'][0], d['legs_x'][1])):
        ga = S.ground('OverlookDeck', xa_, yy)
        gb = S.ground('OverlookDeck', xb_, yy)
        if bz0 - max(ga, gb) > 0.9:
            bar(k, (xa_ + 0.03, yy, bz0 - 0.06), (xb_ - 0.03, yy, max(gb, ga) + 0.40), 0.10, 0.04, Z_DJOIST, ch=0.005,
                up=(0, 1, 0), zcap=Z_DEND)
            for xx_, zz_ in ((xa_, bz0 - 0.08), (xb_, max(gb, ga) + 0.42)):
                bolt(k, (xx_, yy - 0.086, zz_), (0, -1, 0), r=0.012, h=0.008)
    # joists along y, rim boards round the edge
    for xx in (-2.40, -1.60, -0.80, 0.0, 0.80, 1.60, 2.40):
        bar(k, (xx, ya + 0.03, (jz0 + jz1) / 2), (xx, yb - 0.03, (jz0 + jz1) / 2), 0.08, 0.14, Z_DJOIST, ch=0.006,
            zcap=Z_DEND)
    rim = 0.03
    for (p0, p1, up) in (((xa - rim / 2, ya, 0), (xa - rim / 2, yb, 0), (1, 0, 0)),
                         ((xb + rim / 2, ya, 0), (xb + rim / 2, yb, 0), (1, 0, 0)),
                         ((xa - rim, yb + rim / 2, 0), (xb + rim, yb + rim / 2, 0), (0, 1, 0)),
                         ((xa - rim, ya - rim / 2, 0), (xb + rim, ya - rim / 2, 0), (0, 1, 0))):
        zc = top - 0.10
        bar(k, (p0[0], p0[1], zc), (p1[0], p1[1], zc), rim, 0.20, Z_DJOIST, ch=0.004, up=(0, 0, 1), zcap=Z_DEND)
    # deck boards along x
    nb = int((yb - ya) / (bw + 0.008))
    pitch = (yb - ya) / nb
    for i in range(nb):
        yc = ya + (i + 0.5) * pitch
        dz = rng.uniform(-0.003, 0.0)
        ww = pitch - 0.008 + rng.uniform(-0.004, 0.0)
        k.box(xa - 0.002 + rng.uniform(-0.01, 0.0), xb + 0.002 + rng.uniform(0.0, 0.01), yc - ww / 2, yc + ww / 2,
              top - bt + dz, top + dz, Z_DBOARD)
    # railing on three sides: squared posts bolted to the rim, round handrail and mid rail
    rp = d['rail_post']
    xl, xr = xa - rim - rp / 2, xb + rim + rp / 2
    yr = yb + rim + rp / 2
    posts = [(min(max(x, xl), xr) if abs(x) < 2.49 else (xl if x < 0 else xr), yr, 'b') for x in d['rail_back_x']]
    posts += [(xl, y, 's') for y in d['rail_side_y'][:-1]] + [(xr, y, 's') for y in d['rail_side_y'][:-1]]
    for x, y, kind in posts:
        bar(k, (x, y, top - 0.30), (x, y, d['hand_z'] - 0.02), rp, rp, Z_DRPOST, ch=0.010, up=(1, 0, 0), zcap=Z_DEND)
        n = (0, 1, 0) if kind == 'b' else ((-1, 0, 0) if x < 0 else (1, 0, 0))
        for zz in (top - 0.20, top - 0.04):
            bolt(k, (x + n[0] * rp / 2, y + n[1] * rp / 2, zz), n, r=0.012, h=0.008, washer=0.022)
    y0r = d['rail_side_y'][0] - 0.03
    for zz, rr in ((d['hand_z'], d['hand_r']), (d['mid_z'], d['mid_r'])):
        k.tube([Vector((xl, y0r, zz)), Vector((xl, yr, zz)), Vector((xr, yr, zz)), Vector((xr, y0r, zz))], rr,
               Z_DRAIL, seg=8, caps=True)
    for x, sx in ((xl, 1), (xr, -1)):                                  # kick boards inside the posts: sides, back
        xk = x + sx * (rp / 2 + 0.0125)
        bar(k, (xk, ya + 0.06, top + 0.06), (xk, yr - rp / 2 - 0.025, top + 0.06), 0.025, 0.12, Z_DRPOST, ch=0.003,
            zcap=Z_DEND)
    yk = yr - rp / 2 - 0.0125
    bar(k, (xl + rp / 2 + 0.025, yk, top + 0.06), (xr - rp / 2 - 0.025, yk, top + 0.06), 0.025, 0.12, Z_DRPOST, ch=0.003,
        up=(0, 0, 1), zcap=Z_DEND)
    # the steps (open front): two stringers, two treads (Update 3: three; the ground here is higher)
    sxa, sxb = d['steps_x']
    yf = ya - 0.92
    gf = sum(S.ground('OverlookDeck', x, yf + 0.15) for x in (sxa, 0.0, sxb)) / 3
    rise = (top - gf) / 3
    for xx in (sxa - 0.025, sxb + 0.025):
        g = S.ground('OverlookDeck', xx, yf)
        bar(k, (xx, yf, g + 0.06), (xx, ya - 0.02, top - 0.14), 0.05, 0.24, Z_DSTEP, ch=0.004, zcap=Z_DEND)
        k.box(xx - 0.06, xx + 0.06, yf - 0.06, yf + 0.10, g - 0.10, g + 0.02, Z_DFOOT)                # a slab under each
    for i in range(2):
        zt = gf + rise * (i + 1)
        y1_ = ya - 0.02 - (1 - i) * 0.30
        k.box(sxa, sxb, y1_ - 0.30, y1_, zt - 0.05, zt, Z_DSTEP)
    # the bench (facing the view, +y): two leg frames, a two-board seat, a backrest
    bc = d['bench']
    cx, cy = bc['c']
    g = top
    for dx in (-0.70, 0.70):
        for dy in (-0.15, 0.15):
            bar(k, (cx + dx, cy + dy, g), (cx + dx, cy + dy, bc['seat'] - 0.045), 0.07, 0.07, Z_BENCH, ch=0.008,
                up=(1, 0, 0))
        bar(k, (cx + dx, cy - 0.20, bc['seat'] - 0.075), (cx + dx, cy + 0.20, bc['seat'] - 0.075), 0.06, 0.06, Z_BENCH,
            ch=0.006)
        bar(k, (cx + dx, cy - 0.17, bc['seat'] - 0.04), (cx + dx, cy - 0.24, bc['seat'] + 0.40), 0.06, 0.05, Z_BENCH,
            ch=0.006, up=(0, 1, 0))
    for dy in (-0.095, 0.095):
        bar(k, (cx - bc['len'] / 2, cy + dy, bc['seat'] - 0.0225), (cx + bc['len'] / 2, cy + dy, bc['seat'] - 0.0225), 0.18,
            0.045, Z_BENCH, ch=0.008, zcap=Z_DEND)
    bar(k, (cx - bc['len'] / 2, cy - 0.235, bc['seat'] + 0.30), (cx + bc['len'] / 2, cy - 0.235, bc['seat'] + 0.30), 0.04,
        0.14, Z_BENCH, ch=0.008, zcap=Z_DEND)
    # the fixed binoculars on a pipe post
    sc_ = d['scope']
    px_, py_ = sc_['c']
    k.lathe(Vector((px_, py_, top)), (0, 0, 1), [(0.0, 0.11), (0.012, 0.11), (0.012, 0.05), (0.03, 0.04)], Z_SCOPEPOST, 10,
            cap0=False)
    rod(k, (px_, py_, top + 0.02), (px_, py_, sc_['z'] - 0.10), 0.035, Z_SCOPEPOST, seg=8)
    for q in range(4):
        a = q * math.pi / 2 + math.pi / 4
        bolt(k, (px_ + 0.08 * math.cos(a), py_ + 0.08 * math.sin(a), top + 0.012), (0, 0, 1), r=0.010, h=0.008)
    k.box(px_ - 0.045, px_ + 0.045, py_ - 0.03, py_ + 0.03, sc_['z'] - 0.10, sc_['z'] - 0.05, Z_SCOPEPOST)        # yoke
    for sx in (-1, 1):
        k.box(px_ + sx * 0.040 - 0.008, px_ + sx * 0.040 + 0.008, py_ - 0.025, py_ + 0.025, sc_['z'] - 0.06,
              sc_['z'] + 0.01, Z_SCOPEPOST)
    for sx in (-1, 1):                                                 # the two barrels (eyepieces to -y, objectives +y)
        bx = px_ + sx * 0.07
        k.lathe(Vector((bx, py_ - 0.13, sc_['z'])), (0, 1, 0), [(0.0, 0.020), (0.03, 0.022), (0.035, 0.033), (0.20, 0.038),
                                                                 (0.215, 0.045), (0.26, 0.045)], Z_SCOPE, 10,
                cap0=True, cap1=True)
    k.box(px_ - 0.07, px_ + 0.07, py_ - 0.05, py_ + 0.06, sc_['z'] - 0.022, sc_['z'] + 0.022, Z_SCOPE)              # bridge
    part('OverlookDeck', 'static', (0, 0, 0), note='the viewing platform on the bank (AUSSICHTSPUNKT): the view to +y over '
                                                   'the lake to the giant\'s hand')


# ================================================================ the windfall (FallenTree, LogCut)
def taper_tube(k, pts, radii, zone, seg=8, zcap0=None, zcap1=None, wob=0.0, seed=0, ref=None):
    """a tube along a polyline with a radius per point (parallel-transport frames), its rings wobbling by wob; returns
    the rings"""
    pts = [Vector(p) for p in pts]
    rng = np.random.default_rng(seed)
    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        ring, e1 = k.ring_pts(p, t, radii[i], seg, ref)
        ref = e1
        if wob > 0:
            j = 1 + wob * (rng.random(seg) * 2 - 1)
            ring = [p + (q - p) * float(jj) for q, jj in zip(ring, j)]
        rings.append(ring)
    k.loft(rings, [zone] * (len(rings) - 1), cap0=zcap0, cap1=zcap1)
    return rings


def _tree_r(x):
    """the spruce's radius along the trunk (x from the root plate): root flare, the bole, the top"""
    t = S.TREE
    if x <= t['cut0']:
        base = t['r_base'] + (t['r_cut0'] - t['r_base']) * (x - 2.0) / (t['cut0'] - 2.0) if x > 2.0 else t['r_base']
        return base + 0.13 * math.exp(-(x - 0.80) / 0.45)
    if x <= t['cut1']:
        return t['r_cut0'] + (t['r_cut1'] - t['r_cut0']) * (x - t['cut0']) / (t['cut1'] - t['cut0'])
    return 0.012 + (t['r_cut1'] - 0.012) * ((t['tip'] - x) / (t['tip'] - t['cut1'])) ** 0.9


def _branch(k, base, d, L, r0, zone, zend, rng, ground=None, seg=4, twigs=True, xlim=None):
    """a dead spruce branch from base along d (drooping), tapering to a point; if it would dig into the ground it ends
    there (bent against it) or is broken off short (a pale break); xlim (lo, hi): it stays within these x (the road
    between the cuts is clear: whatever reached over it was sawn off with the trunk)"""
    d = Vector(d).normalized()
    if xlim is not None and abs(d.x) > 1e-6:
        lim = xlim[0] if d.x < 0 else xlim[1]
        L = max(0.0, min(L, (lim - base.x) / d.x))
        if L < 0.12:
            return
    end = base + d * L + Vector((0, 0, -0.18 * L))
    if ground is not None:
        ge = ground(end.x, end.y)
        if end.z < ge + 0.03:
            lo, hi = 0.0, 1.0                                          # where it meets the ground
            for _ in range(14):
                m = (lo + hi) / 2
                e = base + d * L * m + Vector((0, 0, -0.18 * L * m * m))
                if e.z < ground(e.x, e.y) + 0.03:
                    hi = m
                else:
                    lo = m
            L = L * lo
            end = base + d * L + Vector((0, 0, -0.18 * L * lo))
            if L < 0.18:                                               # a stub, broken off
                L = 0.05 + 0.12 * rng.random()
                end = base + d * L
                taper_tube(k, [base, end], [r0, r0 * 0.75], zone, seg=seg, zcap1=zend)
                return
    mid = base + d * (L * 0.5) + Vector((0, 0, -0.06 * L))
    taper_tube(k, [base, mid, end], [r0, r0 * 0.55, 0.003], zone, seg=seg)
    if twigs and L > 0.5:
        for q in range(2 + int(L > 1.0) + int(L > 1.6) * 2):
            f = 0.25 + 0.65 * rng.random()
            p0 = base.lerp(mid, f * 2) if f < 0.5 else mid.lerp(end, (f - 0.5) * 2)
            side = d.cross(Vector((0, 0, 1)))
            if side.length < 1e-3:
                side = Vector((1, 0, 0))
            dd = (d * 0.6 + side.normalized() * (1 if q % 2 else -1) * 0.8 + Vector((0, 0, rng.uniform(-0.3, 0.4)))).normalized()
            ll = 0.22 + 0.30 * rng.random()
            if xlim is not None and not (xlim[0] <= (p0 + dd * ll).x <= xlim[1]):
                continue
            taper_tube(k, [p0, p0 + dd * ll], [0.006, 0.0015], zone, seg=3)


def _pile(k, c, r, h, zone, seed, gfun, n=10):
    """a low heap (sawdust, soil) following the ground: an irregular rim on the ground, a middle ring, the top"""
    rng = np.random.default_rng(seed)
    c = Vector(c)
    rim, mid = [], []
    for i in range(n):
        a = TAU * i / n
        rr = r * (0.8 + 0.4 * rng.random())
        p = Vector((c.x + rr * math.cos(a), c.y + rr * math.sin(a), 0))
        p.z = gfun(p.x, p.y) + 0.004
        rim.append(p)
        q = Vector((c.x + 0.55 * rr * math.cos(a), c.y + 0.55 * rr * math.sin(a), 0))
        q.z = gfun(q.x, q.y) + 0.70 * h
        mid.append(q)
    top = Vector((c.x, c.y, gfun(c.x, c.y) + h))
    for i in range(n):
        j = (i + 1) % n
        face(k, [rim[i], rim[j], mid[j], mid[i]], zone, (0, 0, 1))
        face(k, [mid[i], mid[j], top], zone, (0, 0, 1))


def _strip(k, pts, widths, zone, gfun, dz=0.010):
    """a flat strip along a polyline on the ground (decals: a drag trail, a pit)"""
    pts = [Vector((p[0], p[1], 0)) for p in pts]
    L, R = [], []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        s = Vector((-t.y, t.x, 0))
        a, b = p + s * widths[i] / 2, p - s * widths[i] / 2
        a.z, b.z = gfun(a.x, a.y) + dz, gfun(b.x, b.y) + dz
        L.append(a)
        R.append(b)
    for i in range(len(pts) - 1):
        face(k, [L[i], R[i], R[i + 1], L[i + 1]], zone, (0, 0, 1))


def fallen_tree():
    t = S.TREE
    k = kb('FallenTree', 'Windfall')
    rng = np.random.default_rng(31)
    gfun = lambda x, y: S.ground('FallenTree', x, y)
    # ---- the root plate: torn out and stood up at the trunk's foot, leaning back (its top to -x): a spruce's plate is
    # wide and flat (shallow roots), its rim ragged with torn roots, earth and stones caught in its underside
    pc = Vector((0.72, 0.0, 1.05))
    tilt = math.radians(10)
    nrm = Vector((math.cos(tilt), 0.0, math.sin(tilt)))
    e1 = Vector((0, 1, 0))
    e2 = nrm.cross(e1)
    e2 = -e2 if e2.z < 0 else e2
    n = 24
    rad = [1.45 * (1 + 0.10 * math.sin(3 * TAU * i / n + 0.7) + 0.07 * math.sin(7 * TAU * i / n + 2.1)
                   + 0.10 * (rng.random() - 0.5)) for i in range(n)]
    dirs = [e1 * math.cos(TAU * i / n) + e2 * math.sin(TAU * i / n) for i in range(n)]
    ring = [pc + dirs[i] * rad[i] for i in range(n)]
    front = [p + nrm * (0.06 + 0.04 * rng.random()) for p in ring]
    back = [p - nrm * (0.16 + 0.08 * rng.random()) for p in ring]
    back2 = [pc + dirs[i] * rad[i] * 0.62 - nrm * (0.30 + 0.06 * rng.random()) for i in range(n)]
    fc = pc + nrm * 0.12
    bc = pc - nrm * 0.38
    for i in range(n):
        j = (i + 1) % n
        face(k, [front[i], front[j], fc], Z_SOIL, nrm)                           # the old forest floor (moss, needles)
        face(k, [front[i], back[i], back[j], front[j]], Z_TROOT, (dirs[i] + dirs[j]) / 2)   # the torn rim
        face(k, [back[i], back2[i], back2[j], back[j]], Z_TROOT, -nrm + ((dirs[i] + dirs[j]) / 2) * 0.5)
        face(k, [back2[i], bc, back2[j]], Z_TROOT, -nrm)
    for q in range(34):                                                         # torn roots round the rim and behind
        a = TAU * rng.random()
        dr = e1 * math.cos(a) + e2 * math.sin(a)
        i = int(round(a / TAU * n)) % n
        on_rim = q < 24
        p0 = pc + dr * rad[i] * (0.97 if on_rim else 0.35 + 0.45 * rng.random()) - nrm * (0.05 + 0.15 * rng.random()
                                                                                       if on_rim else 0.30)
        if p0.z < gfun(p0.x, p0.y) + 0.06:
            continue
        dd = (dr * (0.9 if on_rim else 0.4) - nrm * (0.25 + 0.5 * rng.random())).normalized()
        L = (0.30 + 0.80 * rng.random()) if on_rim else 0.20 + 0.35 * rng.random()
        r0 = 0.018 + 0.040 * rng.random() ** 1.5
        p1 = p0 + dd * L * 0.5 + Vector((0, 0, -0.10 * L))
        p2 = p0 + dd * L + Vector((0, 0, -0.32 * L))
        if p2.z < gfun(p2.x, p2.y) + 0.02:
            p2.z = gfun(p2.x, p2.y) + 0.02
        taper_tube(k, [p0, p1, p2], [r0, r0 * 0.55, r0 * 0.22], Z_TROOT, seg=4 if r0 < 0.035 else 5, zcap1=Z_TBREAK)
    for q in range(7):                                                          # stones caught in the roots
        a = TAU * rng.random()
        rr = 0.2 + 0.8 * rng.random()
        c = pc + (e1 * math.cos(a) + e2 * math.sin(a)) * rr - nrm * (0.30 + 0.05 * rng.random())
        if c.z > gfun(c.x, c.y) + 0.15:
            _stone(k, c, (0.20 + 0.12 * rng.random(), 0.16 + 0.1 * rng.random(), 0.14), Z_TSTONE, 600 + q)
    # ---- the pit it left (dark loose soil) and the soil heaped round its back
    pit = [(-0.55 + 1.10 * math.cos(a), 1.15 * math.sin(a)) for a in np.linspace(0, TAU, 13)[:-1]]
    pctr = Vector((-0.55, 0.0, gfun(-0.55, 0.0) + 0.008))
    pr = [Vector((x, y, gfun(x, y) + 0.016)) for x, y in pit]
    for i in range(len(pr)):
        face(k, [pr[i], pr[(i + 1) % len(pr)], pctr], Z_SOIL, (0, 0, 1))
    mound_in = [(-0.55 + 1.15 * math.cos(a), 1.20 * math.sin(a)) for a in np.linspace(math.radians(70), math.radians(290), 9)]
    mound_cr = [(-0.55 + 1.40 * math.cos(a), 1.45 * math.sin(a)) for a in np.linspace(math.radians(70), math.radians(290), 9)]
    mound_out = [(-0.55 + 1.75 * math.cos(a), 1.80 * math.sin(a)) for a in np.linspace(math.radians(70), math.radians(290), 9)]
    for i in range(8):
        hh = [0.0, 0.16 + 0.06 * math.sin(i * 1.7), 0.0]
        ri = [Vector((x, y, gfun(x, y) + 0.016)) for x, y in (mound_in[i], mound_in[i + 1])]
        rc = [Vector((x, y, gfun(x, y) + 0.16 + 0.05 * math.sin((i + d_) * 1.7))) for d_, (x, y) in
              enumerate((mound_cr[i], mound_cr[i + 1]))]
        ro = [Vector((x, y, gfun(x, y) + 0.010)) for x, y in (mound_out[i], mound_out[i + 1])]
        face(k, [ri[0], ri[1], rc[1], rc[0]], Z_SOIL, (0.3, 0, 1))
        face(k, [rc[0], rc[1], ro[1], ro[0]], Z_SOIL, (-0.3, 0, 1))
    for q in range(3):
        x_, y_ = -0.55 + rng.uniform(-0.6, 0.5), rng.uniform(-0.7, 0.7)
        _stone(k, (x_, y_, gfun(x_, y_) + 0.04), (0.20, 0.17, 0.12), Z_TSTONE, 620 + q)
    # ---- the root part: from the plate down to the cut at the road's near edge
    zb = pc.z
    zc0 = gfun(t['cut0'], 0.0) + _tree_r(t['cut0']) - 0.02
    xs = [0.80, 1.10, 1.6, 2.4, 3.5, 5.0, 6.5, 8.0, 9.5, 11.0, t['cut0']]
    line = lambda x: Vector((x, 0.0, zb + (zc0 - zb) * (x - 0.80) / (t['cut0'] - 0.80)))
    pts = [line(x) for x in xs]
    rings = taper_tube(k, pts, [_tree_r(x) for x in xs], Z_TBARK, seg=10, zcap1=Z_TCUT, wob=0.035, seed=41)
    for x in np.arange(6.6, t['cut0'] - 0.25, 0.42):                             # dead branch stubs up the bole
        for q in range(int(rng.integers(1, 3))):
            th = rng.uniform(-0.2 * math.pi, 1.2 * math.pi)                       # not into the ground
            radial = Vector((0, math.cos(th), math.sin(th)))
            c = line(x)
            base = c + radial * _tree_r(x) * 0.92
            L = 0.06 + 0.24 * rng.random() if x < 11.0 else 0.10 + 0.9 * rng.random() ** 2
            dd = (radial + Vector((0.45, 0, 0))).normalized()
            L = min(L, (t['cut0'] - 0.05 - base.x) / dd.x) if dd.x > 0 else L
            if L < 0.04:
                continue
            if L < 0.35:
                taper_tube(k, [base, base + dd * L], [0.028, 0.020], Z_TBRANCH, seg=4, zcap1=Z_TBREAK)
            else:
                _branch(k, base, dd, L, 0.026, Z_TBRANCH, Z_TBREAK, rng, gfun, xlim=(-1e9, t['cut0'] - 0.05))
    # ---- the crown part: from the cut at the far edge to the top, lying on the ground and its branches
    xs2 = list(np.arange(t['cut1'], t['tip'] - 0.01, 0.9)) + [t['tip']]
    def yof(x):
        return 0.30 * ((x - t['cut1']) / (t['tip'] - t['cut1'])) ** 2
    zs = []
    for x in xs2:
        best = -1e9
        for xx in np.arange(x - 1.2, x + 1.21, 0.2):
            if t['cut1'] - 0.05 <= xx <= t['tip']:
                best = max(best, gfun(xx, yof(xx)) + _tree_r(xx))
        lift = 0.03 + 0.20 * ((x - t['cut1']) / (t['tip'] - t['cut1'])) ** 1.5
        zs.append(best - 0.02 + lift)
    pts2 = [Vector((x, yof(x), z)) for x, z in zip(xs2, zs)]
    taper_tube(k, pts2, [_tree_r(x) for x in xs2], Z_TBARK, seg=8, zcap0=Z_TCUT, zcap1=Z_TBREAK, wob=0.03, seed=42)

    def crown_c(x):
        for i in range(len(xs2) - 1):
            if xs2[i] <= x <= xs2[i + 1]:
                f = (x - xs2[i]) / (xs2[i + 1] - xs2[i])
                return pts2[i].lerp(pts2[i + 1], f)
        return pts2[-1]
    for x in np.arange(t['cut1'] + 0.30, t['tip'] - 0.3, 0.45):                 # whorls of dead branches
        nb = int(rng.integers(5, 7))
        th0 = rng.uniform(0, TAU)
        c = crown_c(x)
        f = (x - t['cut1']) / (t['tip'] - t['cut1'])
        for j in range(nb):
            th = th0 + TAU * j / nb + rng.uniform(-0.3, 0.3)
            radial = Vector((0, math.cos(th), math.sin(th)))
            base = c + radial * _tree_r(x) * 0.9
            dd = (radial * 0.85 + Vector((-0.40 + 0.85 * f, 0, 0))).normalized()   # drooping (to the root) low, up the top
            L = (0.30 + 1.9 * (1 - f) ** 0.7) * rng.uniform(0.7, 1.1)
            if rng.random() < 0.18:                                             # broken in the fall
                L *= 0.3
            _branch(k, base, dd, L, 0.010 + 0.016 * min(L / 2.0, 1.0), Z_TBRANCH, Z_TBREAK, rng, gfun,
                    xlim=(t['cut1'] + 0.05, 1e9))
    # ---- sawdust under both cuts (the chainsaw throws it to one side)
    for (x, y, r, h, sd) in ((t['cut0'] + 0.16, -0.36, 0.30, 0.045, 1), (t['cut0'] - 0.02, 0.44, 0.22, 0.03, 2),
                             (t['cut0'] + 0.45, 0.05, 0.36, 0.012, 3), (t['cut1'] - 0.14, 0.38, 0.30, 0.045, 4),
                             (t['cut1'] + 0.06, -0.40, 0.20, 0.025, 5), (t['cut1'] - 0.45, 0.02, 0.34, 0.012, 6)):
        _pile(k, (x, y, 0), r, h, Z_SAWDUST, 700 + sd, gfun)
    part('FallenTree', 'static', (0, 0, 0), note='the windfall (S4): a dead spruce torn out with its root plate (the pit at the '
                                                 'pivot), fallen downhill across the road and sawn straight at both edges (x '
                                                 f'{t["cut0"]} and {t["cut1"]}); the road between is clear')


def _ft_to_lc():
    F = np.array(S.GROUND['prefabs']['FallenTree']['world'])
    L = np.array(S.GROUND['prefabs']['LogCut']['world'])
    return np.linalg.inv(L) @ F


def log_cut():
    t = S.TREE
    k = kb('LogCut', 'Windfall')
    rng = np.random.default_rng(32)
    gfun = lambda x, y: S.ground('LogCut', x, y)
    L = t['cut1'] - t['cut0'] - 2 * t['kerf']
    xa, xb = -L / 2, L / 2
    ra, rb = _tree_r(t['cut0'] + t['kerf']), _tree_r(t['cut1'] - t['kerf'])
    za, zb = gfun(xa, 0) + ra - 0.03, gfun(xb, 0) + rb - 0.03
    lift = 0.0
    for x in np.linspace(xa, xb, 33):                                           # lies on its high points
        f = (x - xa) / (xb - xa)
        z = za + (zb - za) * f + lift
        r = ra + (rb - ra) * f
        lift = max(lift, gfun(x, 0) - 0.03 - (z - r))
    za, zb = za + lift, zb + lift
    xs = list(np.linspace(xa, xb, 9))
    pts = [Vector((x, 0.0, za + (zb - za) * (x - xa) / (xb - xa))) for x in xs]
    taper_tube(k, pts, [ra + (rb - ra) * (x - xa) / (xb - xa) for x in xs], Z_TBARK, seg=10, zcap0=Z_TCUT, zcap1=Z_TCUT,
               wob=0.03, seed=43)
    for q in range(8):                                                         # its branch stubs (it was rolled over)
        x = rng.uniform(xa + 0.6, xb - 0.4)
        th = rng.uniform(-0.15 * math.pi, 1.15 * math.pi)
        radial = Vector((0, math.cos(th), math.sin(th)))
        f = (x - xa) / (xb - xa)
        c = Vector((x, 0.0, za + (zb - za) * f))
        base = c + radial * (ra + (rb - ra) * f) * 0.92
        ll = 0.05 + 0.20 * rng.random()
        taper_tube(k, [base, base + (radial + Vector((0.3, 0, 0))).normalized() * ll], [0.026, 0.019], Z_TBRANCH, seg=4,
                   zcap1=Z_TBREAK)
    M = _ft_to_lc()                                                             # the drag trail from the road gap to here
    gap = [(15.0, -0.10), (16.6, 0.25), (18.2, 0.85), (19.4, 1.55), (20.25, 2.15)]
    tr = []
    for x, y in gap:
        p = M @ np.array([x, y, 0.0, 1.0])
        tr.append((float(p[0]), float(p[1])))
    tr.append((xa * 0.15, 0.30))
    _strip(k, tr, [0.62, 0.66, 0.60, 0.56, 0.50, 0.46], Z_DRAG, gfun, dz=0.012)
    part('LogCut', 'static', (0, 0, 0), note='the piece sawn out of the road (6.4 m, the gap in FallenTree), dragged onto the '
                                             'far verge: the drag trail runs from the gap to it')


# ================================================================ all of it
def build_road():
    for name in S.SIGN_ORDER:
        road_sign(name)
    europost()
    zone_gate()
    bridge()
    overlook()
    fallen_tree()
    log_cut()
