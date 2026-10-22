"""Painters for the Forest base prefabs' atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n]).
The generator shed's wear language (gen_paint / hut_paint / road_paint: the same rules, noise and finishes - galvanised
steel with its spangle and white rust, black steel going rusty, weathered grey wood, bark, end grain, concrete with
streaks and moss) on the base's things: the hatch's precast collar (rust bleeding from the hinges and the staple, needles
on the top, the dark shaft), its chequer-plate lid worn bright where it is walked on; olive transport chests with
chipped paint and English stencils, pine crates; the log pile (bark, pale ends with the forester's spray marks); the
helipad's concrete (saw-cut joints, the white H and the yellow dashed ring faded and chipped, a dark wet edge, oil where
helicopters stand), the red and white windsock, the tarped pallet; the radio mast's seven aviation bands (red and white,
chalky, rust at the nodes), galvanised ladder, concrete anchors; the galvanised yard light, the creosoted power pole and
its plates; the chain-link fence's galvanised posts, the old boundary fence's grey post.
Positions arrive in the bake layout (base_build: LAYOUT): each texel goes back to its prefab's own frame."""
import math
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, boards, hash1
from gen_paint import OIL, GRIME, DUST, RUST, RUST_D, _T, _common, run_m
from hut_paint import galv, steel_black, stone, end_grain, bark, weathered, MOSS, LICHEN
import pxfont as F
import road_tex as RTX
import base_spec as S
import base_kit as BK

LAYOUT = {}
SOIL, SOIL_D, MUD = lin(70, 58, 44), lin(44, 36, 28), lin(84, 72, 56)
ALGAE = lin(70, 86, 52)
NEEDLES = lin(104, 76, 46)


def _locals(Pp):
    """texels back to their prefab's frame: (local positions, owner name per texel)"""
    names = list(LAYOUT)
    if not names:
        return Pp.copy(), np.array([''] * len(Pp), dtype=object)
    offs = np.array([LAYOUT[n] for n in names], np.float32)
    idx = np.zeros(len(Pp), np.int64) if len(names) == 1 else np.abs(Pp[:, 0][:, None] - offs[None, :, 0]).argmin(1)
    return Pp - offs[idx], np.array(names, dtype=object)[idx]


def _ground(Pl, own):
    g = np.zeros(len(Pl), np.float32)
    for n in set(own):
        m = own == n
        if n in S.GROUND['prefabs']:
            g[m] = S.ground_v(n, Pl[m, 0], Pl[m, 1])
    return g


def paint_base(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    Pl, own = _locals(Pp)
    hz = Pl[:, 2] - _ground(Pl, own)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    zs = set(np.unique(Z).tolist())
    for zones, fn in ((BK.PROPS_ZONES, _props), (BK.HELI_ZONES, _heli), (BK.MAST_ZONES, _mast), (BK.POLES_ZONES, _poles),
                      (BK.FENCE_ZONES, _fence)):
        if zs & set(zones):
            m = np.isin(Z, zones)
            c, g = fn(Pp[m], Pl[m], Nn[m], Z[m], ao[m], aa, hz[m], own[m])
            col[m] = c
            gr[m] = g
    return col, gr


def _foot(c, hz, Pl, h=0.30, seed=1900):
    """splash, soil and moss where a thing meets the ground"""
    c = mixc(c, MUD, ss(h, 0.0, hz) * (0.35 + 0.4 * fbm(Pl, 9.0, 2, seed=seed)))
    return mixc(c, MOSS, ss(h * 0.6, 0.0, hz) * ss(0.55, 0.75, fbm(Pl, 6.0, 2, seed=seed + 1)) * 0.6)


def concrete(Pp, T, cav, up, seed, base=(150, 148, 140)):
    """precast concrete: fine aggregate, darker and paler specks, lichen in patches, dirt in the hollows"""
    c = T(lin(*base), 0.14, 0.20)
    c = mixc(c, lin(112, 110, 104), ss(0.62, 0.80, fbm(Pp, 30.0, 1, seed=seed)) * 0.35)
    c = mixc(c, lin(176, 174, 166), ss(0.74, 0.88, fbm(Pp, 60.0, 1, seed=seed + 1)) * 0.30)
    c = mixc(c, LICHEN, ss(0.68, 0.86, fbm(Pp, 5.0, 3, seed=seed + 2)) * 0.40)
    return mixc(c, lin(80, 80, 76), cav * 0.35)


def stencil(u, v, txt, cu, cv, px, font=F.F35):
    """texels whose face coordinates (u right, v up, metres) fall on the text centred at (cu, cv); px = one font pixel"""
    m = RTX.prop_mask(txt, font, 1)
    h, w = m.shape
    ci = np.floor((u - cu) / px + w / 2.0).astype(np.int64)
    ri = np.floor((cv - v) / px + h / 2.0).astype(np.int64)
    ok = (ci >= 0) & (ci < w) & (ri >= 0) & (ri < h)
    out = np.zeros(len(u), bool)
    out[ok] = m[ri[ok], ci[ok]]
    return out


def _box_local(Pl, Nn, d):
    """a crate's frame: (x', y', z' local; normal in it)"""
    a = math.radians(d['yaw'])
    ca, sa = math.cos(a), math.sin(a)
    cx, cy = d['c']
    dx, dy = Pl[:, 0] - cx, Pl[:, 1] - cy
    xl, yl = ca * dx + sa * dy, -sa * dx + ca * dy
    nx, ny = ca * Nn[:, 0] + sa * Nn[:, 1], -sa * Nn[:, 0] + ca * Nn[:, 1]
    return xl, yl, Pl[:, 2] - d.get('z', 0.0), nx, ny


def _crate_label(xl, yl, zl, ny, d, lines, px, near=0.03):
    """stencil lines on the crate's front (-y') face; lines: [(text, v centre)]"""
    sx, sy, sz = d['size']
    on = (np.abs(yl + sy / 2) < near) & (ny < -0.7) & (np.abs(xl) < sx / 2)
    m = np.zeros(len(xl), bool)
    for txt, vc in lines:
        m |= stencil(xl, zl, txt, 0.0, vc, px)
    return on & m


# ================================================================ Props: the hatch, the crates, the log pile
def _props(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 1001)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    h = S.HATCH
    # ---- the hatch collar: precast, streaks from the top edge, rust bleeding from the hinges and the staple onto the top,
    # needles and dirt in the corners of the top, moss at the foot
    m = M(BK.Z_HCONC)
    c = concrete(Pp, T, cav, up, 1002)
    side = up < 0.5
    streak = ss(0.55, 0.80, fbm(Pp * np.array([1.5, 1.5, 0.10], np.float32), 6.0, 3, seed=1003)) * side
    c = mixc(c, lin(78, 78, 72), streak * 0.45)
    px_, _, pz = h['pivot']
    rust = np.zeros(n, np.float32)
    for (rx, ry, rr) in ((px_ - 0.07, -0.58, 0.16), (px_ - 0.07, 0.58, 0.16), (h['staple_x'], 0.0, 0.12),
                         (h['vent'][0], h['vent'][1], 0.20)):
        rust = np.maximum(rust, np.exp(-(((x - rx) / rr) ** 2 + ((y - ry) / rr) ** 2)))
    c = mixc(c, RUST, np.clip(rust * (0.5 + 0.5 * fbm(Pp, 12.0, 2, seed=1004)), 0, 1) * 0.65 * up)
    r_ = np.maximum(np.abs(x), np.abs(y))
    c = mixc(c, NEEDLES, up * ss(1.10, 1.40, r_) * ss(0.45, 0.70, fbm(Pp, 9.0, 2, seed=1005)) * 0.55)
    c = mixc(c, MOSS, up * ss(0.58, 0.78, fbm(Pp, 4.0, 3, seed=1006)) * 0.45)
    c = _foot(c, hz, Pl, 0.25, 1007)
    col[m] = c[m]
    m = M(BK.Z_HFRAME)
    c = galv(Pp, T, seed=1008)
    c = mixc(c, lin(198, 200, 194), ss(0.62, 0.82, fbm(Pp, 14.0, 2, seed=1009)) * 0.35)
    c = mixc(c, lin(70, 70, 66), (z < h['top']) * 0.45)                          # the leg in the shaft, darker
    col[m] = mixc(c, RUST_D, edge * 0.4)[m]
    # ---- the shaft: concrete fading into black with depth, wet algae on the walls
    m = M(BK.Z_HSHAFT)
    depth = ss(h['top'] - 0.02, h['shaft_floor'] + 0.05, z)
    c = concrete(Pp, T, cav, up, 1010, base=(96, 94, 88))
    c = mixc(c, ALGAE * 0.5, ss(0.5, 0.75, fbm(Pp, 8.0, 2, seed=1011)) * 0.4)
    c = c * (1.0 - 0.94 * depth)[:, None]
    c = np.where((up > 0.9)[:, None], lin(6, 6, 6) * np.ones((n, 1), np.float32), c)
    col[m] = c[m]
    m = M(BK.Z_HRUNG)
    c = galv(Pp, T, seed=1012) * 0.8
    c = mixc(c, RUST, np.clip(0.35 + 0.5 * fbm(Pp, 20.0, 2, seed=1013), 0, 1) * 0.7)
    col[m] = (c * (1.0 - 0.85 * ss(h['top'] - 0.05, h['shaft_floor'] + 0.08, z))[:, None])[m]
    # ---- the lid: chequer plate in black paint, worn to bare steel where it is walked on and at the edges, rust
    # where water stands, needles; the diamond lugs as a pale / dark dither
    m = M(BK.Z_HLID)
    c = T(lin(58, 60, 60), 0.10, 0.14)
    lug = (dist_periodic(x + y, 0.085) < 0.016) & (dist_periodic(x - y, 0.17, 0.085) > 0.04) & (up > 0.9)
    lug2 = (dist_periodic(x - y, 0.085) < 0.016) & (dist_periodic(x + y, 0.17) > 0.04) & (up > 0.9)
    c = mixc(c, lin(104, 106, 104), (lug | lug2) * 0.55)
    walk = np.exp(-((x - 0.1) / 0.55) ** 2 - (y / 0.7) ** 2) * up
    c = mixc(c, lin(128, 128, 124), np.clip(walk * ss(0.35, 0.70, fbm(Pp, 10.0, 2, seed=1014)) * 0.7 + edge * 0.6, 0, 1))
    c = mixc(c, RUST, ss(0.62, 0.82, fbm(Pp, 6.0, 3, seed=1015)) * (0.35 + 0.4 * up) * 0.7)
    c = mixc(c, NEEDLES, up * ss(0.70, 0.86, fbm(Pp, 16.0, 2, seed=1016)) * 0.45)
    col[m] = c[m]
    m = M(BK.Z_HHINGE)
    col[m] = steel_black(Pp, T, edge, seed=1017)[m]
    m = M(BK.Z_HLOCK)                                                            # a brass padlock, tarnished
    c = T(lin(168, 136, 64), 0.08, 0.14)
    c = mixc(c, lin(86, 78, 52), ss(0.45, 0.75, fbm(Pp, 40.0, 2, seed=1018)) * 0.55)
    col[m] = mixc(c, lin(200, 172, 96), edge * 0.6)[m]
    m = M(BK.Z_HVENT)
    c = galv(Pp, T, seed=1019)
    c = mixc(c, RUST, ss(0.6, 0.8, fbm(Pp, 10.0, 2, seed=1020)) * 0.5 + (1 - up) * 0.15)
    col[m] = mixc(c, lin(60, 60, 58), ((Nn[:, 2] < -0.5) & (z > h['vent_top'] - 0.07)) * 0.6)[m]
    # ---- the sign's posts and back (the road signs' rules)
    m = M(BK.Z_SPOST)
    c = galv(Pp, T, seed=1021)
    col[m] = _foot(c, hz, Pl, 0.35, 1022)[m]
    m = M(BK.Z_SCAP)
    col[m] = mixc(T(lin(58, 60, 62), 0.08, 0.12), lin(96, 98, 98), up * 0.4)[m]
    m = M(BK.Z_SBACK)
    c = T(lin(124, 127, 122), 0.10, 0.14)
    c = mixc(c, lin(84, 84, 78), ss(0.60, 0.82, fbm(Pp * np.array([1.6, 1.6, 0.18], np.float32), 8.0, 3, seed=1023)) * 0.35)
    col[m] = mixc(c, lin(96, 90, 72), up * 0.55)[m]
    m = M(BK.Z_SRAIL)
    col[m] = mixc(T(lin(176, 178, 174), 0.08, 0.12), lin(110, 110, 104), cav * 0.4)[m]
    m = M(BK.Z_SCLAMP)
    col[m] = mixc(galv(Pp, T, seed=1024) * 0.9, RUST, ss(0.72, 0.88, fbm(Pp, 40.0, 2, seed=1025)) * 0.5)[m]
    # ---- the crates: olive paint chipped at the edges to grey primer and wood, rain streaks, mud low down, stencils
    for zz, base, seed in ((BK.Z_COLIVE, (92, 94, 62), 1030), (BK.Z_CCASE, (78, 86, 60), 1040)):
        m = M(zz)
        if not m.any():
            continue
        c = T(lin(*base), 0.10, 0.14)
        c = mixc(c, lin(120, 120, 88), ss(0.55, 0.85, fbm(Pp, 4.0, 2, seed=seed)) * 0.25)              # sun-faded
        c = mixc(c, lin(112, 108, 96), np.clip(edge * 0.9 + ss(0.78, 0.90, fbm(Pp, 30.0, 2, seed=seed + 1)) * 0.5, 0, 1))
        runs = ss(0.58, 0.82, fbm(Pp * np.array([1.6, 1.6, 0.15], np.float32), 8.0, 3, seed=seed + 2)) * (up < 0.5)
        c = mixc(c, lin(58, 58, 44), runs * 0.30 + cav * 0.3)
        c = mixc(c, NEEDLES, up * ss(0.62, 0.82, fbm(Pp, 12.0, 2, seed=seed + 3)) * 0.45)
        c = _foot(c, hz, Pl, 0.18, seed + 4)
        col[m] = c[m]
    m = M(BK.Z_CSTEEL)
    c = T(lin(64, 68, 58), 0.08, 0.12)
    col[m] = mixc(c, RUST, np.clip(edge * 0.6 + ss(0.72, 0.86, fbm(Pp, 30.0, 2, seed=1050)) * 0.5, 0, 0.8))[m]
    m = M(BK.Z_CROPE)
    c = T(lin(150, 130, 94), 0.10, 0.16) * (0.85 + 0.25 * (dist_periodic(Pp[:, 0] + Pp[:, 1] + Pp[:, 2], 0.03) / 0.015))[:, None]
    col[m] = mixc(c, lin(80, 70, 52), cav * 0.4 + ss(0.6, 0.8, fbm(Pp, 10.0, 2, seed=1051)) * 0.3)[m]
    for zz, base, seed in ((BK.Z_CPINE, (172, 146, 104), 1052), (BK.Z_CINNER, (128, 104, 72), 1056)):
        m = M(zz)
        if not m.any():
            continue
        vert = np.abs(Nn[:, 2]) < 0.6
        bi = np.floor(Pl[:, 2] / 0.125)
        c = T(lin(*base), 0.12, 0.16) * (0.90 + 0.18 * hash1(bi + np.round(Pl[:, 0] * 3), 41))[:, None]
        c = mixc(c, lin(132, 126, 114), up * 0.45 + ss(0.55, 0.85, fbm(Pp, 3.0, 2, seed=seed)) * 0.25)       # greyed
        c = mixc(c, lin(70, 60, 46), ss(0.66, 0.80, fbm(Pp * np.array([0.3, 0.3, 6], np.float32), 6.0, 2, seed=seed + 1)) * 0.4)
        c = mixc(c, lin(66, 56, 42), cav * 0.5)
        c = _foot(c, hz, Pl, 0.15, seed + 2)
        col[m] = c[m]
        seam = vert & (dist_periodic(Pl[:, 2], 0.125) < 0.004)
        gr = np.where(m & seam, 0.5, gr)
    m = M(BK.Z_CSTRAW)
    c = T(lin(196, 170, 104), 0.12, 0.18)
    c = mixc(c, lin(140, 112, 60), ss(0.45, 0.75, fbm(Pp * np.array([3, 0.4, 1], np.float32), 30.0, 2, seed=1060)) * 0.6)
    col[m] = mixc(c, lin(90, 72, 40), cav * 0.5)[m]
    # the stencils: English, in faded paint
    crates_m = own == 'Crates'
    for key, lines, px, ink in (('A', (('SURVEY', 0.47), ('EQUIPMENT', 0.33)), 0.02, (206, 198, 160)),
                                ('B', (('SPARES', 0.17),), 0.02, (206, 198, 160)),
                                ('C', (('TOOLS', 0.15),), 0.02, (206, 198, 160)),
                                ('D', (('KEEP DRY', 0.42),), 0.022, (40, 36, 30)),
                                ('E', (('FRAGILE', 0.40),), 0.022, (150, 40, 30))):
        d = BK.CRATES[key]
        xl, yl, zl, nx, ny = _box_local(Pl, Nn, d)
        zone_ok = np.isin(Z, (BK.Z_COLIVE, BK.Z_CCASE, BK.Z_CPINE))
        lab = crates_m & zone_ok & _crate_label(xl, yl, zl, ny, d, lines, px)
        wear = ss(0.35, 0.65, fbm(Pp, 25.0, 2, seed=1070 + ord(key)))
        col = np.where(lab[:, None], mixc(col, lin(*ink), 0.85 * wear + 0.1), col)
    # ---- the log pile: spruce bark, pale cut ends greying, the forester's spray marks on the +x ends
    m = M(BK.Z_LBARK)
    c = bark(Pp, T, up, 1080)
    c = c * (0.9 + 0.2 * fbm(Pp * np.array([0.2, 3, 3], np.float32), 8.0, 2, seed=1081))[:, None]
    c = mixc(c, lin(124, 84, 56), ss(0.66, 0.84, fbm(Pp, 18.0, 2, seed=1082)) * 0.35)                       # red-brown scales
    col[m] = _foot(c, hz, Pl, 0.25, 1083)[m]
    m = M(BK.Z_LEND)
    c = end_grain(Pp, T, n_hi, 1084)
    c = mixc(c, lin(120, 110, 96), ss(0.5, 0.8, fbm(Pp, 4.0, 2, seed=1085)) * 0.3)
    spray = np.zeros(n, np.float32)
    is_pile = own == 'LogPile'
    for i, (x0, x1, yc, zc, r) in enumerate(S.LOGS):
        zc = zc + BK.LOG_RISE
        xe = x1 if i % 2 == 0 else x0                                     # the thin end of each log faces the other way
        if xe < 0:
            continue
        dd = np.hypot(y - yc, z - zc)
        on = is_pile & (np.abs(x - xe) < 0.05) & (dd < r * 1.02)
        if i % 3 == 0:
            spray = np.maximum(spray, on * np.exp(-(dd / (r * 0.45)) ** 2))                          # a dot
        elif i % 3 == 1:
            spray = np.maximum(spray, on * (np.abs((y - yc) - 0.6 * (z - zc)) < 0.035))               # a stroke
    blue = lin(40, 70, 150)
    c = mixc(c, blue, np.clip(spray * (0.6 + 0.4 * fbm(Pp, 30.0, 1, seed=1086)), 0, 1))
    col[m] = c[m]
    for zz, seed in ((BK.Z_LSKID, 1087), (BK.Z_LSTAKE, 1090)):
        m = M(zz)
        c = weathered(Pp, Nn, T, cav, 2 if zz == BK.Z_LSTAKE else 1, seed)
        c = mixc(c, lin(78, 66, 52), ss(0.6, 0.8, fbm(Pp, 10.0, 2, seed=seed + 1)) * 0.4)                  # bark left on
        col[m] = _foot(c, hz, Pl, 0.3, seed + 2)[m]
    return col, gr


# ================================================================ the helipad
def _heli(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 1101)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    h = S.HELI
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    r = np.hypot(x, y)
    # ---- the pad: broom-finished concrete, saw-cut joints every 4 m, the white H and the yellow dashed ring faded and
    # chipped, oil and exhaust soot where helicopters stood, the wet dark rim, needles and moss along the joints
    m = M(BK.Z_PAD)
    c = concrete(Pp, T, cav, up, 1102, base=(146, 144, 136))
    c = c * (0.94 + 0.08 * (dist_periodic(y + 0.3 * np.sin(x * 0.7), 0.05) / 0.025))[:, None]          # broom lines
    jx, jy = dist_periodic(x, 4.0), dist_periodic(y, 4.0)
    joint = (np.minimum(jx, jy) < 0.008) & (r < h['r'] - 0.15)
    c = mixc(c, MOSS, np.clip(ss(0.10, 0.0, np.minimum(jx, jy)) * ss(0.5, 0.75, fbm(Pp, 6.0, 2, seed=1103)), 0, 1) * 0.55)
    c = mixc(c, lin(70, 66, 58), np.exp(-(r / 3.2) ** 2) * ss(0.35, 0.75, fbm(Pp, 3.0, 3, seed=1104)) * 0.45)   # oil
    c = mixc(c, lin(108, 108, 102), ss(h['r'] - 1.2, h['r'], r) * 0.5)                                   # the wet rim
    c = mixc(c, NEEDLES, ss(h['r'] - 2.5, h['r'], r) * ss(0.62, 0.84, fbm(Pp, 10.0, 2, seed=1105)) * 0.5)
    hb0, hb1, hl = h['h_bar']
    H_ = ((np.abs(x) > hb0) & (np.abs(x) < hb1) & (np.abs(y) < hl)) | ((np.abs(x) <= hb0) & (np.abs(y) < h['h_cross']))
    ang = np.mod(np.arctan2(y, x), 2 * np.pi)
    dash = (r > h['ring'][0]) & (r < h['ring'][1]) & (np.mod(ang / (2 * np.pi) * h['ring_dashes'], 1.0) < 0.62)
    chip = ss(0.70, 0.84, fbm(Pp, 22.0, 2, seed=1106))
    fade = 0.80 - 0.25 * fbm(Pp, 2.0, 2, seed=1107)
    c = mixc(c, lin(226, 224, 214), H_ * (1 - chip) * fade)
    c = mixc(c, lin(214, 172, 40), dash * (1 - chip) * fade)
    col[m] = c[m]
    gr = np.where(m & joint, 0.7, gr)
    m = M(BK.Z_PADSIDE)
    c = concrete(Pp, T, cav, up, 1108, base=(132, 130, 122))
    c = mixc(c, lin(70, 68, 62), ss(0.0, 0.12, h['top'] - z) * 0.3)
    col[m] = _foot(c, hz, Pl, 0.35, 1109)[m]
    m = M(BK.Z_PFOOT)
    col[m] = _foot(concrete(Pp, T, cav, up, 1110), hz, Pl, 0.25, 1111)[m]
    for zz, seed in ((BK.Z_LSTALK, 1112), (BK.Z_SFRAME, 1114), (BK.Z_HPOST, 1116)):
        m = M(zz)
        c = galv(Pp, T, seed=seed)
        col[m] = _foot(mixc(c, RUST_D, edge * 0.4), hz, Pl, 0.3, seed + 1)[m]
    m = M(BK.Z_LBODY)
    c = T(lin(36, 36, 36), 0.06, 0.12)
    col[m] = mixc(c, lin(90, 88, 82), up * 0.4 + edge * 0.3)[m]
    # ---- the windsock mast: white paint, rust from the joints and the hinge, the sock red and white faded, dirty in
    # its folds
    m = M(BK.Z_SMAST)
    c = T(lin(214, 214, 206), 0.06, 0.10)
    c = mixc(c, RUST, run_m(Pp) * 0.35 + np.exp(-((z - 1.09) / 0.25) ** 2) * 0.35 * ss(0.4, 0.7, fbm(Pp, 10.0, 2, seed=1118)))
    c = _foot(mixc(c, lin(150, 146, 134), cav * 0.4), hz, Pl, 0.3, 1119)
    col[m] = c[m]
    for zz, base, seed in ((BK.Z_SOCKR, (186, 50, 36), 1120), (BK.Z_SOCKW, (218, 216, 206), 1122)):
        m = M(zz)
        c = T(lin(*base), 0.08, 0.12)
        c = mixc(c, lin(150, 140, 120) if zz == BK.Z_SOCKW else lin(150, 70, 60), ss(0.45, 0.8, fbm(Pp, 3.0, 2, seed=seed)) * 0.4)
        col[m] = mixc(c, lin(70, 60, 50), cav * 0.5 + ss(-0.3, -0.9, Nn[:, 2]) * 0.2)[m]
    m = M(BK.Z_PALLET)
    c = weathered(Pp, Nn, T, cav, 0, 1124)
    c = mixc(c, lin(160, 136, 100), np.full(n, 0.35, np.float32))
    col[m] = _foot(c, hz, Pl, 0.12, 1125)[m]
    m = M(BK.Z_TARP)                                                                  # olive tarp, folds, needles, damp
    c = T(lin(70, 84, 62), 0.10, 0.16)
    c = mixc(c, lin(108, 118, 92), up * ss(0.4, 0.8, fbm(Pp, 2.5, 2, seed=1126)) * 0.35)
    c = mixc(c, lin(40, 46, 36), cav * 0.6 + ss(0.62, 0.80, fbm(Pp * np.array([1, 1, 3], np.float32), 6.0, 2, seed=1127)) * 0.3)
    c = mixc(c, NEEDLES, up * ss(0.68, 0.86, fbm(Pp, 14.0, 2, seed=1128)) * 0.5)
    col[m] = c[m]
    m = M(BK.Z_ROPE)
    col[m] = mixc(T(lin(170, 150, 110), 0.1, 0.16), lin(90, 80, 60), cav * 0.4)[m]
    m = M(BK.Z_EXTBOX)                                                                # RAL 3000 box, sun-faded on top
    c = T(lin(172, 34, 28), 0.06, 0.10)
    c = mixc(c, lin(200, 120, 110), up * 0.35)
    col[m] = mixc(c, lin(90, 30, 24), cav * 0.4 + edge * 0.2)[m]
    m = M(BK.Z_EXTLBL)                                                                # the label: a red pictogram on white
    c = T(lin(226, 222, 212), 0.04, 0.08)
    ex, ey = h['extinguisher']
    pict = (np.abs(x - (ex - 0.06)) < 0.025) & (np.abs(z - 1.03) < 0.06)
    c = np.where(pict[:, None], lin(170, 34, 28) * np.ones((n, 1), np.float32), c)
    col[m] = c[m]
    m = M(BK.Z_HBACK)
    c = T(lin(124, 127, 122), 0.10, 0.14)
    col[m] = mixc(c, lin(96, 90, 72), up * 0.55 + cav * 0.3)[m]
    return col, gr


# ================================================================ the radio mast
def _mast(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 1201)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    m_ = S.MAST
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    # ---- the lattice: seven aviation bands (red at the top and the foot), chalky, rust at the nodes and bolts, streaks
    band = np.clip(np.floor(z / (m_['h'] / m_['bands'])), 0, m_['bands'] - 1)
    red = (band % 2) == 0
    for zz in (BK.Z_MLEG, BK.Z_MBAR):
        m = M(zz)
        c = np.where(red[:, None], T(lin(178, 54, 40), 0.08, 0.12), T(lin(222, 222, 214), 0.05, 0.10))
        c = mixc(c, np.where(red[:, None], lin(196, 120, 110) * np.ones((n, 1), np.float32),
                             lin(236, 236, 230) * np.ones((n, 1), np.float32)), ss(0.5, 0.85, fbm(Pp, 2.0, 2, seed=1202)) * 0.30)
        node = dist_periodic(z, m_['bay']) < 0.06
        c = mixc(c, RUST, np.clip(node * ss(0.45, 0.75, fbm(Pp, 20.0, 2, seed=1203)) * 0.7 + edge * 0.3, 0, 0.85))
        c = mixc(c, RUST_D, run_m(Pp) * 0.30)
        c = _foot(c, hz, Pl, 0.4, 1204)
        col[m] = c[m]
    m = M(BK.Z_MFOOT)
    col[m] = _foot(concrete(Pp, T, cav, up, 1205), hz, Pl, 0.3, 1206)[m]
    m = M(BK.Z_MANCH)
    c = concrete(Pp, T, cav, up, 1207, base=(138, 136, 128))
    c = mixc(c, MOSS, up * ss(0.45, 0.70, fbm(Pp, 4.0, 3, seed=1208)) * 0.7)
    col[m] = _foot(c, hz, Pl, 0.3, 1209)[m]
    for zz, seed in ((BK.Z_MPLATE, 1210), (BK.Z_MLADDER, 1212), (BK.Z_MBRK, 1214), (BK.Z_MTRAY, 1216), (BK.Z_MTURN, 1218)):
        m = M(zz)
        c = galv(Pp, T, seed=seed)
        c = mixc(c, RUST, np.clip(edge * 0.5 + ss(0.74, 0.88, fbm(Pp, 25.0, 2, seed=seed + 1)) * 0.45, 0, 0.8))
        if zz == BK.Z_MLADDER:                                                         # rungs worn bright on top
            c = mixc(c, lin(200, 202, 198), up * ss(0.3, 0.7, fbm(Pp, 30.0, 1, seed=seed + 2)) * 0.5)
        col[m] = _foot(c, hz, Pl, 0.3, seed + 2)[m]
    m = M(BK.Z_MBODY)
    c = T(lin(44, 44, 42), 0.06, 0.12)
    col[m] = mixc(c, lin(110, 108, 100), up * 0.35 + edge * 0.3)[m]
    m = M(BK.Z_MGUY)                                                                   # the strand's lay, a dull grey
    c = T(lin(118, 122, 122), 0.06, 0.10) * (0.86 + 0.24 * (dist_periodic(z + Pp[:, 0] * 0.3, 0.05) / 0.025))[:, None]
    col[m] = mixc(c, RUST_D, ss(0.7, 0.9, fbm(Pp, 6.0, 2, seed=1220)) * 0.35)[m]
    m = M(BK.Z_MCOAX)
    c = T(lin(30, 30, 30), 0.06, 0.12)
    col[m] = mixc(c, lin(80, 80, 78), up * 0.3 + ss(0.6, 0.9, fbm(Pp, 5.0, 2, seed=1221)) * 0.2)[m]
    m = M(BK.Z_MANT)
    c = T(lin(184, 186, 184), 0.06, 0.10)
    col[m] = mixc(c, lin(120, 122, 118), cav * 0.4 + ss(0.6, 0.85, fbm(Pp, 12.0, 2, seed=1222)) * 0.25)[m]
    m = M(BK.Z_MROD)                                                                   # copper gone brown and green
    c = T(lin(132, 92, 60), 0.08, 0.14)
    col[m] = mixc(c, lin(96, 140, 116), ss(0.5, 0.8, fbm(Pp, 8.0, 2, seed=1223)) * 0.6)[m]
    m = M(BK.Z_MBACK)
    c = T(lin(124, 127, 122), 0.10, 0.14)
    col[m] = mixc(c, lin(96, 90, 72), up * 0.55 + cav * 0.3)[m]
    return col, gr


# ================================================================ the yard light and the power pole
def _poles(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 1301)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    m = M(BK.Z_LPOLE)
    c = galv(Pp, T, seed=1302)
    c = mixc(c, lin(200, 202, 196), ss(0.62, 0.82, fbm(Pp * np.array([2, 2, 0.4], np.float32), 12.0, 2, seed=1303)) * 0.35)
    c = mixc(c, lin(96, 96, 90), ss(0.9, 0.1, z) * 0.35)
    col[m] = _foot(c, hz, Pl, 0.35, 1304)[m]
    m = M(BK.Z_LDOOR)
    c = galv(Pp, T, seed=1305)
    sticker = (np.abs(z - 0.86) < 0.035) & (np.abs(x) < 0.03) & (y < 0)                # the lamp's number sticker
    c = np.where(sticker[:, None], lin(220, 206, 60) * np.ones((n, 1), np.float32), c)
    col[m] = c[m]
    m = M(BK.Z_LFOOT)
    col[m] = _foot(concrete(Pp, T, cav, up, 1306), hz, Pl, 0.2, 1307)[m]
    m = M(BK.Z_LBOLT)
    col[m] = mixc(galv(Pp, T, seed=1308) * 0.85, RUST, 0.25 + 0.3 * fbm(Pp, 30.0, 2, seed=1309))[m]
    m = M(BK.Z_LHEAD)                                                                  # grey powder coat, dirty on top
    c = T(lin(132, 136, 136), 0.06, 0.10)
    c = mixc(c, lin(80, 82, 78), up * 0.45 + ss(0.6, 0.85, fbm(Pp, 10.0, 2, seed=1310)) * 0.2)
    col[m] = mixc(c, NEEDLES, up * ss(0.66, 0.86, fbm(Pp, 16.0, 2, seed=1311)) * 0.4)[m]
    # ---- the power pole: creosote brown, long cracks, greyed toward the top, a dark ground line (the yard pole's rule)
    m = M(BK.Z_PPOLE)
    ang = np.arctan2(y, x)
    crack = np.maximum(gline(dist_periodic(ang * 0.13, 0.11, 0.03), 0.004, aa), gline(dist_periodic(ang * 0.13, 0.11, 0.08), 0.003, aa))
    crack = crack * ss(0.45, 0.70, fbm(Pp * np.array([1, 1, 0.08], np.float32), 4.0, 2, seed=1312))
    c = T(lin(66, 50, 36), 0.14, 0.18) * (0.86 + 0.24 * fbm(Pp * np.array([4, 4, 0.2], np.float32), 12.0, 2, seed=1313))[:, None]
    c = mixc(c, lin(112, 106, 96), ss(4.0, 9.0, z) * 0.45)
    c = mixc(c, lin(30, 24, 20), np.exp(-((hz - 0.08) / 0.18) ** 2) * 0.6)
    c = mixc(c, lin(26, 22, 18), crack * 0.8)
    col[m] = c[m]
    gr = np.where(m, crack * 0.6, gr)
    m = M(BK.Z_PXARM)
    c = weathered(Pp, Nn, T, cav, 0, 1314)
    col[m] = mixc(c, lin(86, 70, 52), np.full(n, 0.3, np.float32))[m]
    m = M(BK.Z_PGALV)
    col[m] = mixc(galv(Pp, T, seed=1315), RUST, np.clip(edge * 0.4 + run_m(Pp) * 0.3, 0, 0.7))[m]
    m = M(BK.Z_PPORC)
    c = T(lin(120, 62, 38), 0.06, 0.10) * (0.85 + 0.30 * n_hi)[:, None]
    c = mixc(c, lin(200, 150, 120), ss(0.55, 0.95, np.clip(Nn[:, 2] * 0.5 + 0.5, 0, 1)) * 0.25)
    col[m] = mixc(c, lin(60, 40, 30), ss(-0.2, -0.8, Nn[:, 2]) * 0.4)[m]
    m = M(BK.Z_PEARTH)
    c = T(lin(128, 90, 60), 0.08, 0.14)
    col[m] = mixc(c, lin(90, 128, 104), ss(0.5, 0.8, fbm(Pp, 8.0, 2, seed=1316)) * 0.5)[m]
    m = M(BK.Z_PPLATE)                                                                 # the number plate and the danger sign
    c = T(lin(226, 224, 214), 0.04, 0.08)
    num = (np.abs(z - 2.40) < 0.08) & (dist_periodic(x * 1.0, 0.03) < 0.007) & (np.abs(z - 2.40) < 0.03)
    c = np.where(num[:, None], lin(30, 30, 30) * np.ones((n, 1), np.float32), c)
    dz = z - 3.10
    yel = (np.abs(z - 3.10) < 0.085)
    tri = yel & (dz > -0.05) & (dz < 0.06 - 0.0) & (np.abs(x - 0.04) < (0.06 - dz) * 0.6)
    c = np.where(yel[:, None], lin(236, 196, 30) * np.ones((n, 1), np.float32), c)
    c = np.where(tri[:, None] & ~((np.abs(x - 0.04) < (0.035 - dz) * 0.45) & (dz > -0.03))[:, None],
                 lin(30, 30, 30) * np.ones((n, 1), np.float32), c)
    bolt_ = yel & (np.abs((x - 0.04) + 0.6 * dz) < 0.006) & (np.abs(dz) < 0.035)
    c = np.where(bolt_[:, None], lin(30, 30, 30) * np.ones((n, 1), np.float32), c)
    col[m] = mixc(c, lin(120, 90, 60), edge * 0.5)[m]
    return col, gr


# ================================================================ the fences
def _fence(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 1401)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    for zz, seed in ((BK.Z_FPOST, 1402), (BK.Z_FRAIL, 1405), (BK.Z_FCLAMP, 1408)):
        m = M(zz)
        c = galv(Pp, T, seed=seed)
        c = mixc(c, lin(200, 202, 196), ss(0.62, 0.82, fbm(Pp * np.array([2, 2, 0.4], np.float32), 12.0, 2, seed=seed + 1)) * 0.35)
        c = mixc(c, RUST_D, edge * 0.35)
        col[m] = _foot(c, hz, Pl, 0.35, seed + 2)[m]
    m = M(BK.Z_OPOST)                                                                  # a grey split post, cracked, lichen
    c = weathered(Pp, Nn, T, cav, 2, 1411)
    c = mixc(c, LICHEN, ss(0.62, 0.80, fbm(Pp, 6.0, 3, seed=1412)) * 0.5)
    c = mixc(c, lin(52, 46, 38), ss(0.5, 0.0, hz) * 0.55)
    col[m] = _foot(c, hz, Pl, 0.4, 1413)[m]
    m = M(BK.Z_OTOP)
    c = end_grain(Pp, T, n_hi, 1414) * 0.6 + lin(110, 106, 96) * 0.4
    col[m] = mixc(c, MOSS, ss(0.4, 0.7, fbm(Pp, 10.0, 2, seed=1415)) * 0.5)[m]
    return col, gr
