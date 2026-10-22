"""Painters for the fence kit's atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n]).
The generator shed's wear language (gen_paint / hut_paint / base_paint) on the kit:
  PO-2 panels: grey precast concrete, the outer face a field of 9 x 9 shallow rhombic pyramids in a flat border (the
  relief's light and shade baked in, light from the upper left), water streaks from the top, rust bleeding from the
  outrigger's bolts, lichen and moss creeping up from the ground, a splash of mud; look b darker and greener; the break
  pale and coarse, the rebar rusty; the back plain with its frame; the sockets older, mossy, grout in the slot;
  black steel outriggers going rusty; the wicket's frame and door in the station's grey-green paint, chipped;
  FBS blocks (end grooves, lifting loops of rusty rebar), the concrete barrier (plain or red and white, faded and
  chipped), the cube; the dragon's teeth old (the Westwall's age): dark, mossy tops, lichen;
  galvanised chain-link posts, black steel stakes, the hedgehog's rusty beams, weathered poles and stakes, spruce bark,
  sawn butts and sharpened tips pale, galvanised sign posts and plate backs.
Positions arrive in the bake layout (fence_build: LAYOUT): each texel goes back to its prefab's own frame."""
import numpy as np
from noise import ss, mixc, fbm
from psxbake import lin
from gen_paint import OIL, GRIME, DUST, RUST, RUST_D, _T, _common, run_m
from hut_paint import galv, steel_black, end_grain, bark, weathered, MOSS, LICHEN
from base_paint import concrete, _foot
import fence_kit as FK
import fence_spec as S

LAYOUT = {}
MUD = lin(84, 72, 56)
ALGAE = lin(70, 86, 52)
STATION = lin(96, 112, 96)                  # the station's grey-green (KPP, yard)


def _locals(Pp):
    names = list(LAYOUT)
    if not names:
        return Pp.copy(), np.array([''] * len(Pp), dtype=object)
    offs = np.array([LAYOUT[n] for n in names], np.float32)
    idx = np.zeros(len(Pp), np.int64) if len(names) == 1 else np.abs(Pp[:, 0][:, None] - offs[None, :, 0]).argmin(1)
    return Pp - offs[idx], np.array(names, dtype=object)[idx]


def paint_fence(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    Pl, own = _locals(Pp)
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    zs = set(np.unique(Z).tolist())
    for zones, fn in ((FK.CONCRETE_ZONES, _concrete), (FK.PROPS_ZONES, _props)):
        if zs & set(zones):
            m = np.isin(Z, zones)
            c, g = fn(Pp[m], Pl[m], Nn[m], Z[m], ao[m], aa, own[m])
            col[m] = c
            gr[m] = g
    return col, gr


# ---------------------------------------------------------------- the PO-2 relief
def rhombus_shade(x, z, x0=None, x1=None):
    """the outer face's relief: (shade multiplier, groove 0..1, in_border) at panel coordinates x (along), z (height)"""
    p = S.PO2
    b = p['border']
    x0 = -p['L'] / 2 + p['gap'] / 2 if x0 is None else x0
    x1 = p['L'] / 2 - p['gap'] / 2 if x1 is None else x1
    fx0, fx1 = x0 + b, x1 - b
    fz0, fz1 = p['z0'] + b, p['z1'] - b
    nc, nr = p['cells']
    cw = (p['L'] - p['gap'] - 2 * b) / nc                  # the cell size stays the full panel's (wicket: cut off)
    chh = (fz1 - fz0) / nr
    s = (x - (-p['L'] / 2 + p['gap'] / 2 + b)) / cw
    t = (z - fz0) / chh
    fs = s - np.floor(s) - 0.5
    ft = t - np.floor(t) - 0.5
    d = np.abs(fs) + np.abs(ft)                             # 0 at a pyramid's top, 0.5 on its rim
    inside = d <= 0.5
    sh = np.where(fs < 0, np.where(ft > 0, 1.16, 0.95), np.where(ft > 0, 1.04, 0.80))     # light from the upper left
    sh = np.where(inside, sh, 0.90)
    rim = ss(0.035, 0.0, np.abs(d - 0.5))                   # the dark line where the pyramids meet the flat
    ridge = ss(0.03, 0.0, np.minimum(np.abs(fs), np.abs(ft))) * inside * 0.35   # the pyramids' edges catch light
    sh = sh * (1 - 0.25 * rim) * (1 + 0.10 * ridge)
    in_field = (x > fx0) & (x < fx1) & (z > fz0) & (z < fz1)
    edge_line = in_field & ((np.abs(x - fx0) < 0.012) | (np.abs(x - fx1) < 0.012) | (np.abs(z - fz0) < 0.012) |
                            (np.abs(z - fz1) < 0.012))
    sh = np.where(in_field, sh, 1.0)
    return sh, (rim * in_field + edge_line * 0.6), in_field


def _po2(Pp, Pl, Nn, Z, ao, aa, own, n_lo, n_mid, n_hi, up, cav, edge, T):
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    look_b = np.isin(own, ['ConcreteFence_b', 'ConcreteFence_Plain'])
    base = np.where(look_b[:, None], lin(140, 138, 130)[None, :], lin(166, 163, 154)[None, :])
    c = T(lin(166, 163, 154), 0.12, 0.16) * (base / lin(166, 163, 154)[None, :])
    c = mixc(c, lin(120, 118, 110), ss(0.62, 0.80, fbm(Pp, 30.0, 1, seed=2101)) * 0.30)
    c = mixc(c, lin(190, 188, 180), ss(0.74, 0.88, fbm(Pp, 60.0, 1, seed=2102)) * 0.28)
    streak = ss(0.48, 0.78, fbm(Pp * np.array([7.0, 7.0, 0.35], np.float32), 3.0, 2, seed=2103))     # water from the top
    reach = ss(0.6, 2.6, z) * (0.6 + 0.4 * fbm(Pp * np.array([3, 3, 0.2], np.float32), 4.0, 1, seed=2104))
    c = mixc(c, lin(92, 92, 86), streak * reach * np.where(look_b, 0.75, 0.50))
    bolt_x = S.PO2['L'] / 2 - S.PO2['gap'] / 2                # rust bleeding from the outrigger's bolts (the +x end)
    rx = np.exp(-((x - (bolt_x - 0.05)) / 0.06) ** 2) * ss(2.62, 2.0, z) * ss(1.4, 2.3, z)
    rust_runs = rx * (0.5 + 0.5 * fbm(Pp * np.array([20, 20, 1.5], np.float32), 3.0, 1, seed=2105))
    c = mixc(c, lin(132, 76, 42), rust_runs * 0.7)
    c = mixc(c, LICHEN, ss(0.66, 0.84, fbm(Pp, 5.0, 3, seed=2106)) * np.where(look_b, 0.45, 0.30))
    green = ss(0.9, 0.0, z) * ss(0.45, 0.70, fbm(Pp, 6.0, 2, seed=2107))                 # moss creeping up
    c = mixc(c, np.where(look_b[:, None], ALGAE[None, :], MOSS[None, :]), green * np.where(look_b, 0.85, 0.6))
    c = mixc(c, MUD, ss(0.30, 0.0, z) * (0.3 + 0.4 * fbm(Pp, 9.0, 2, seed=2108)))
    c = mixc(c, lin(70, 70, 66), cav * 0.30)
    return c


def _concrete(Pp, Pl, Nn, Z, ao, aa, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2100)
    T = _T(n_lo, n_hi)
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    M = lambda zz: Z == zz
    col = np.tile(lin(150, 148, 140), (n, 1))
    gr = np.zeros(n, np.float32)
    po2 = _po2(Pp, Pl, Nn, Z, ao, aa, own, n_lo, n_mid, n_hi, up, cav, edge, T)
    # the outer face: the relief
    m = M(FK.Z_FACE)
    if m.any():
        wick = own == 'ConcreteFence_Wicket'
        sh, groove, inf = rhombus_shade(x, z)
        c = po2 * sh[:, None]
        c = mixc(c, lin(60, 60, 56), groove * 0.45)
        col[m] = c[m]
        gr[m] = (groove * 0.3)[m]
    m = M(FK.Z_BACK)                                                    # the back: plain, its frame a shade lighter
    if m.any():
        p = S.PO2
        b = p['border']
        fr = (np.abs(x) > p['L'] / 2 - p['gap'] / 2 - b) | (z < p['z0'] + b) | (z > p['z1'] - b)
        c = po2 * np.where(fr, 1.06, 0.97)[:, None]
        col[m] = c[m]
    m = M(FK.Z_EDGE)
    col[m] = (po2 * 0.92)[m]
    m = M(FK.Z_BREAK)                                                   # fresh break: pale, coarse aggregate
    c = T(lin(184, 178, 164), 0.10, 0.25)
    c = mixc(c, lin(120, 112, 100), ss(0.55, 0.75, fbm(Pp, 80.0, 1, seed=2111)) * 0.6)
    col[m] = c[m]
    m = M(FK.Z_REBAR) | M(FK.Z_LOOP)
    c = mixc(T(RUST, 0.15, 0.2), RUST_D, ss(0.4, 0.7, fbm(Pp, 40.0, 2, seed=2112)) * 0.6)
    col[m] = c[m]
    m = M(FK.Z_SOCK)                                                    # the sockets: older, mud, moss
    c = concrete(Pp, T, cav, up, 2113, base=(132, 130, 122))
    c = mixc(c, MOSS, up * ss(0.45, 0.70, fbm(Pp, 5.0, 2, seed=2114)) * 0.6)
    c = mixc(c, MUD, ss(0.06, -0.10, z) * 0.8 + ss(0.10, 0.0, z) * 0.3)
    col[m] = c[m]
    m = M(FK.Z_SLOT)
    col[m] = mixc(T(lin(54, 52, 48), 0.2, 0.3), lin(96, 92, 84), ss(0.6, 0.8, fbm(Pp, 50.0, 1, seed=2115)) * 0.5)[m]
    m = M(FK.Z_BRACKET)
    c = steel_black(Pp, T, edge, seed=2116)
    c = mixc(c, RUST, ss(0.55, 0.80, fbm(Pp, 12.0, 2, seed=2117)) * 0.55)
    col[m] = c[m]
    m = M(FK.Z_SBACK) | M(FK.Z_SPOST)
    col[m] = galv(Pp, T, seed=2118)[m]
    m = M(FK.Z_SCAP)
    col[m] = T(lin(60, 62, 64), 0.1, 0.1)[m]
    for zz, seed in ((FK.Z_WFRAME, 2119), (FK.Z_WDOOR, 2121)):           # the station's grey-green, chipped
        m = M(zz)
        c = T(STATION, 0.10, 0.12)
        c = mixc(c, RUST, ss(0.70, 0.86, fbm(Pp, 25.0, 2, seed=seed)) * 0.7 + edge * 0.5)
        col[m] = _foot(c, z, Pl, 0.3, seed + 1)[m]
    # blocks
    m = M(FK.Z_FBS) | M(FK.Z_FBSEND)
    c = concrete(Pp, T, cav, up, 2123, base=(150, 148, 138))
    c = mixc(c, lin(96, 94, 88), ss(0.50, 0.78, fbm(Pp * np.array([5, 5, 0.4], np.float32), 4.0, 2, seed=2124)) * 0.45)
    gro = (np.abs(y) < S.FBS['groove'][0] / 2) & M(FK.Z_FBSEND)        # the end groove
    c = np.where(gro[:, None], c * 0.62, c)
    col[m] = _foot(c, z, Pl, 0.25, 2125)[m]
    for zz, seed in ((FK.Z_JERSEY, 2126), (FK.Z_JSTRIPE, 2128), (FK.Z_CUBE, 2130)):
        m = M(zz)
        c = concrete(Pp, T, cav, up, seed, base=(170, 168, 160))
        if zz == FK.Z_JSTRIPE:                                          # red and white, 0.25 m diagonals, faded, chipped
            band = np.floor((x + z) / 0.25) % 2 == 0
            paint = np.where(band[:, None], lin(176, 44, 34)[None, :], lin(222, 218, 206)[None, :])
            chip = ss(0.62, 0.80, fbm(Pp, 22.0, 2, seed=seed + 1)) + edge * 0.6
            c = mixc(paint * T(np.ones(3, np.float32), 0.10, 0.10), c, np.clip(chip, 0, 1) * 0.8)
            c = mixc(c, lin(120, 116, 106), ss(0.75, 0.9, fbm(Pp, 6.0, 2, seed=seed + 2)) * 0.3)
        col[m] = _foot(c, z, Pl, 0.3, seed + 3)[m]
    for zz, seed in ((FK.Z_TOOTH, 2133), (FK.Z_TOOTHTOP, 2136), (FK.Z_TOOTHCHIP, 2139)):    # old, mossy
        m = M(zz)
        c = concrete(Pp, T, cav, up, seed, base=(128, 126, 116))
        c = mixc(c, lin(78, 78, 72), ss(0.45, 0.75, fbm(Pp * np.array([4, 4, 0.5], np.float32), 4.0, 2, seed=seed + 1)) * 0.5)
        c = mixc(c, LICHEN, ss(0.55, 0.78, fbm(Pp, 6.0, 3, seed=seed + 2)) * 0.55)
        moss = ss(0.55, 0.9, up) * ss(0.40, 0.66, fbm(Pp, 5.0, 2, seed=seed + 3)) + ss(0.35, 0.0, z) * 0.5
        c = mixc(c, MOSS, np.clip(moss, 0, 1) * 0.8)
        if zz == FK.Z_TOOTHCHIP:
            c = mixc(c, lin(176, 170, 156), np.full(len(c), 0.55, np.float32))
        col[m] = c[m]
    return col, gr


def _props(Pp, Pl, Nn, Z, ao, aa, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 2200)
    T = _T(n_lo, n_hi)
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    M = lambda zz: Z == zz
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    for zz, seed in ((FK.Z_CPOST, 2201), (FK.Z_CRAIL, 2204), (FK.Z_CCAP, 2207), (FK.Z_HPOST, 2210), (FK.Z_HBACK, 2213)):
        m = M(zz)
        c = galv(Pp, T, seed=seed)
        c = mixc(c, lin(200, 202, 196), ss(0.62, 0.82, fbm(Pp * np.array([2, 2, 0.4], np.float32), 12.0, 2, seed=seed + 1)) * 0.3)
        c = mixc(c, RUST_D, edge * 0.35)
        col[m] = _foot(c, z, Pl, 0.35, seed + 2)[m]
    m = M(FK.Z_STAKE)
    col[m] = _foot(mixc(steel_black(Pp, T, edge, seed=2216), RUST, ss(0.5, 0.75, fbm(Pp, 10.0, 2, seed=2217)) * 0.6),
                   z, Pl, 0.3, 2218)[m]
    m = M(FK.Z_HEDGE)                                                       # the hedgehog: rust, a little old paint
    c = mixc(T(RUST, 0.18, 0.25), RUST_D, ss(0.40, 0.70, fbm(Pp, 14.0, 2, seed=2219)) * 0.7)
    c = mixc(c, lin(64, 70, 58), ss(0.72, 0.86, fbm(Pp, 6.0, 2, seed=2220)) * 0.45)
    col[m] = _foot(c, z, Pl, 0.25, 2221)[m]
    for zz, seed in ((FK.Z_POLE, 2222), (FK.Z_WSTAKE, 2225)):
        m = M(zz)
        col[m] = _foot(weathered(Pp, Nn, T, cav, 0 if zz == FK.Z_POLE else 2, seed), z, Pl, 0.3, seed + 2)[m]
    m = M(FK.Z_BARK) | M(FK.Z_STUB)
    c = bark(Pp, T, up, 2228)
    c = np.where(M(FK.Z_STUB)[:, None], c * 0.9, c)
    col[m] = _foot(c, z, Pl, 0.25, 2231)[m]
    m = M(FK.Z_BUTT)
    col[m] = end_grain(Pp, T, n_hi, 2232)[m]
    m = M(FK.Z_TIP)                                                         # sharpened: pale, axe facets
    c = T(lin(200, 176, 132), 0.12, 0.2)
    c = mixc(c, lin(140, 118, 88), ss(0.5, 0.8, fbm(Pp, 30.0, 2, seed=2234)) * 0.4)
    col[m] = c[m]
    m = M(FK.Z_SCAP)
    col[m] = T(lin(60, 62, 64), 0.1, 0.1)[m]
    return col, gr
