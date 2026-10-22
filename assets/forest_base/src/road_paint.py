"""Painters for the road prefabs' atlases (psxbake): painter(Pp, Nn, Z, ao, aa) -> (rgb_linear[n, 3], groove[n] or None).
The generator shed's wear language (gen_paint / hut_paint: the same rules, noise and finishes - galvanised steel with
its spangle and white rust, black steel going rusty, weathered grey spruce, bark, end grain, field stone) on the road's
materials: the signs' galvanised posts and dust-grey backs (with the maker's sticker), the white delineators greened on
their shady side; the gate's concrete pillars streaked from the caps and rust-stained under the hinges, its galvanised
tubes; the bridge's planks (one tone each, nails over the stringers, moss along the edges), the running strips worn dark
by tyres, debarked log stringers green underneath, piles wet at their foot; the overlook's pressure-treated pine
(green fading to grey), a worn path from the steps; the dead spruce: grey flaking bark, bare silver wood with bark-beetle
galleries where the bark fell, lichen on the dead branches, the fresh pale saw cuts with their rings and the blue stain
of the dead sapwood, sawdust, the torn root plate, the pit, the drag trail.
Positions arrive in the bake layout (road_build.bake_layout -> LAYOUT): each texel goes back to its prefab's own frame
for the ground under it (road_spec.ground_v)."""
import numpy as np
from noise import ss, mixc, fbm, dist_periodic, groove as gline
from psxbake import lin, boards, hash1
from gen_paint import OIL, GRIME, DUST, RUST, RUST_D, _T, _common, run_m
from hut_paint import galv, steel_black, stone, end_grain, bark, weathered, MOSS, LICHEN
import road_spec as S
import road_kit as RK

LAYOUT = {}
SOIL, SOIL_D, MUD = lin(70, 58, 44), lin(44, 36, 28), lin(84, 72, 56)
GREY_WOOD, GREY_WOOD_D = lin(128, 122, 110), lin(66, 62, 56)
ALGAE = lin(70, 86, 52)


def _locals(Pp, Z):
    """texels back to their prefab's frame: (local positions, owner name per texel)"""
    names = list(LAYOUT)
    if not names:
        return Pp.copy(), np.array([''] * len(Pp), dtype=object)
    offs = np.array([LAYOUT[n] for n in names], np.float32)
    if len(names) == 1:
        idx = np.zeros(len(Pp), np.int64)
    elif 'LogCut' in LAYOUT:
        idx = np.where(Pp[:, 1] < -4.5, names.index('LogCut'), names.index('FallenTree'))
    else:
        idx = np.abs(Pp[:, 0][:, None] - offs[None, :, 0]).argmin(1)
    Pl = Pp - offs[idx]
    return Pl, np.array(names, dtype=object)[idx]


def _ground(Pl, own):
    """the ground (local z) under each texel"""
    g = np.zeros(len(Pl), np.float32)
    for n in set(own):
        m = own == n
        if n in S.GROUND['prefabs']:
            g[m] = S.ground_v(n, Pl[m, 0], Pl[m, 1])
    return g


def paint_road(Pp, Nn, Z, ao, aa):
    n = len(Pp)
    Pl, own = _locals(Pp, Z)
    hz = Pl[:, 2] - _ground(Pl, own)                                    # height above the ground
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    zs = set(np.unique(Z).tolist())
    for zones, fn in ((RK.SIGN_ZONES, _signs), (RK.GATE_ZONES, _gate), (RK.BRIDGE_ZONES, _bridge), (RK.DECK_ZONES, _deck),
                      (RK.WIND_ZONES, _windfall)):
        if zs & set(zones):
            m = np.isin(Z, zones)
            c, g = fn(Pp[m], Pl[m], Nn[m], Z[m], ao[m], aa, hz[m], own[m])
            col[m] = c
            gr[m] = g
    return col, gr


def _foot(c, hz, Pl, h=0.30, seed=900):
    """splash, soil and moss where a thing meets the ground"""
    c = mixc(c, MUD, ss(h, 0.0, hz) * (0.35 + 0.4 * fbm(Pl, 9.0, 2, seed=seed)))
    return mixc(c, MOSS, ss(h * 0.6, 0.0, hz) * ss(0.55, 0.75, fbm(Pl, 6.0, 2, seed=seed + 1)) * 0.6)


# ================================================================ signs and delineators
def _signs(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 801)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    # galvanised posts: the shed's galvanising, mud splash and lichen at the foot, grime under the clamps
    m = M(RK.Z_SPOST)
    c = galv(Pp, T, seed=802)
    c = mixc(c, lin(196, 198, 190), ss(0.62, 0.80, fbm(Pp * np.array([2, 2, 0.4], np.float32), 14.0, 2, seed=803)) * 0.35)
    c = _foot(c, hz, Pl, 0.35, 804)
    col[m] = c[m]
    m = M(RK.Z_SCAP)
    col[m] = mixc(T(lin(58, 60, 62), 0.08, 0.12), lin(96, 98, 98), up * 0.4)[m]
    # the plate's back: dust grey RAL 7037, chalky, dirt run down from the top fold, the maker's sticker
    m = M(RK.Z_SBACK)
    c = T(lin(124, 127, 122), 0.10, 0.14)
    c = mixc(c, lin(150, 152, 146), ss(0.55, 0.85, fbm(Pp, 5.0, 2, seed=805)) * 0.35)
    runs = ss(0.60, 0.82, fbm(Pp * np.array([1.6, 1.6, 0.18], np.float32), 8.0, 3, seed=806))
    c = mixc(c, lin(84, 84, 78), runs * 0.35 + cav * 0.3)
    c = mixc(c, lin(96, 90, 72), up * 0.55)                              # needles and dirt on the top fold
    back = Nn[:, 1] > 0.9
    for name in set(own):
        if name not in S.SIGNS:
            continue
        w, z0, z1 = S.SIGNS[name]['face']
        sx, sz = w / 2 - 0.14, z0 + 0.06
        st = back & (own == name) & (np.abs(x - sx) < 0.045) & (np.abs(z - sz) < 0.028)
        c = np.where(st[:, None], lin(214, 210, 196), c)
        txt = st & (dist_periodic(z - sz, 0.012) < 0.0028) & (np.abs(x - sx) < 0.035)
        c = np.where(txt[:, None], lin(70, 70, 70), c)
    col[m] = c[m]
    m = M(RK.Z_SRAIL)
    col[m] = mixc(T(lin(176, 178, 174), 0.08, 0.12), lin(110, 110, 104), cav * 0.4 + runs * 0.2)[m]
    m = M(RK.Z_SCLAMP)
    col[m] = mixc(galv(Pp, T, seed=807) * 0.9, RUST, ss(0.72, 0.88, fbm(Pp, 40.0, 2, seed=808)) * 0.5)[m]
    # the delineator: white plastic, yellowed a little, green on the shady side (-x), splashed at the foot
    m = M(RK.Z_EPBODY)
    c = T(lin(232, 232, 222), 0.05, 0.08)
    c = mixc(c, lin(214, 208, 180), ss(0.4, 0.9, fbm(Pp, 3.0, 2, seed=809)) * 0.3)
    shade = ss(0.0, -0.8, Nn[:, 0]) * 0.5 + 0.2
    c = mixc(c, ALGAE, ss(0.45, 0.75, fbm(Pp, 7.0, 3, seed=810)) * shade * 0.6)
    c = mixc(c, lin(120, 112, 96), ss(0.30, 0.0, z) * (0.5 + 0.4 * fbm(Pp, 12.0, 2, seed=811)))
    c = mixc(c, lin(150, 146, 134), cav * 0.4)
    col[m] = c[m]
    m = M(RK.Z_EPBAND)
    col[m] = mixc(T(lin(34, 34, 34), 0.06, 0.12), lin(70, 70, 68), up * 0.45 + ss(0.7, 0.9, fbm(Pp, 20.0, 2, seed=812)) * 0.25)[m]
    return col, gr


# ================================================================ the zone gate
def _gate(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 811)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    g = S.GATE
    # concrete pillars: precast, fine aggregate, black streaks from the cap, rust under the hinges, moss at the foot
    m = M(RK.Z_CONC)
    c = T(lin(150, 148, 140), 0.14, 0.20)
    c = mixc(c, lin(112, 110, 104), ss(0.62, 0.80, fbm(Pp, 30.0, 1, seed=812)) * 0.35)
    c = mixc(c, lin(176, 174, 166), ss(0.74, 0.88, fbm(Pp, 60.0, 1, seed=813)) * 0.30)
    streak = ss(0.55, 0.80, fbm(Pp * np.array([1.5, 1.5, 0.10], np.float32), 6.0, 3, seed=814)) * ss(1.2, 2.7, z)
    c = mixc(c, lin(70, 70, 66), streak * 0.55)
    hinge = np.zeros(n, np.float32)
    for hzz in g['hinge_z']:
        for sx in (-1, 1):
            xp = sx * (g['pillar_x'] - g['pillar'] / 2)
            hinge = np.maximum(hinge, np.exp(-((x - xp) / 0.10) ** 2 - (y / 0.10) ** 2) * ss(hzz + 0.05, hzz - 0.5, z)
                               * ss(hzz - 1.3, hzz - 0.2, z))
    c = mixc(c, RUST, np.clip(hinge, 0, 1) * 0.7 * (0.6 + 0.4 * fbm(Pp * np.array([3, 3, 0.3], np.float32), 10.0, 2, seed=815)))
    c = mixc(c, LICHEN, ss(0.66, 0.84, fbm(Pp, 5.0, 3, seed=816)) * 0.45)
    c = _foot(c, hz, Pl, 0.45, 817)
    col[m] = c[m]
    m = M(RK.Z_CONCCAP)
    c = T(lin(160, 158, 150), 0.12, 0.18)
    c = mixc(c, MOSS, up * ss(0.48, 0.70, fbm(Pp, 4.0, 3, seed=818)) * 0.7)
    c = mixc(c, lin(80, 80, 76), (1 - up) * 0.3 + cav * 0.3)
    col[m] = c[m]
    m = M(RK.Z_GFOOT)
    c = mixc(T(lin(128, 126, 118), 0.14, 0.2), SOIL, ss(0.12, -0.05, hz) * 0.5)
    col[m] = mixc(c, MOSS, ss(0.5, 0.7, fbm(Pp, 6.0, 2, seed=819)) * 0.45)[m]
    # galvanised tubes: spangle, white rust, rust at the welds, grime low, the latch worn bright by hands
    m = M(RK.Z_GTUBE)
    c = galv(Pp, T, seed=820)
    c = mixc(c, lin(204, 206, 200), ss(0.66, 0.84, fbm(Pp * np.array([2, 2, 0.5], np.float32), 12.0, 2, seed=821)) * 0.3)
    c = mixc(c, RUST_D, edge * 0.4)
    c = _foot(c, hz, Pl, 0.4, 822)
    c = mixc(c, lin(196, 198, 194), np.exp(-((np.abs(x) - 0.05) / 0.06) ** 2 - ((z - 1.15) / 0.25) ** 2) * 0.4)
    col[m] = c[m]
    m = M(RK.Z_GHINGE)
    col[m] = steel_black(Pp, T, edge, seed=823)[m]
    m = M(RK.Z_GBAR)
    c = T(lin(108, 112, 112), 0.10, 0.14)
    col[m] = mixc(c, RUST, np.clip(edge * 0.8 + ss(0.75, 0.9, fbm(Pp, 30.0, 2, seed=824)) * 0.5, 0, 0.8))[m]
    m = M(RK.Z_GPLATE)
    c = T(lin(222, 220, 212), 0.06, 0.10)
    c = mixc(c, lin(140, 132, 116), ss(0.6, 0.82, fbm(Pp * np.array([1.5, 1.5, 0.2], np.float32), 8.0, 3, seed=825)) * 0.35 + cav * 0.3)
    col[m] = c[m]
    m = M(RK.Z_CHAIN)
    c = T(lin(112, 62, 34), 0.18, 0.25)
    c = mixc(c, lin(66, 40, 26), ss(0.5, 0.8, fbm(Pp, 60.0, 1, seed=826)) * 0.6)
    col[m] = mixc(c, lin(140, 90, 52), edge * 0.5)[m]
    m = M(RK.Z_GBOLT)
    col[m] = mixc(galv(Pp, T, seed=827) * 0.85, RUST, 0.25 + 0.3 * fbm(Pp, 30.0, 2, seed=828))[m]
    return col, gr


# ================================================================ the bridge
def _plank_wood(Pp, Pl, Nn, T, cav, along, pitch, aa, seed, base=(124, 116, 100), crack=0.6):
    """weathered spruce boards: one tone per board, silver-grey on top, browner on the sides and underneath, cracks
    along the grain, dark seams"""
    sc = np.ones(3, np.float32) * 6.0
    sc[along] = 0.30
    c = T(lin(*base), 0.14, 0.18)
    c = mixc(c, lin(156, 150, 136), np.clip(Nn[:, 2], 0, 1) * 0.30)
    c = mixc(c, lin(92, 74, 56), np.clip(-Nn[:, 2], 0, 1) * 0.40)
    c = mixc(c, GREY_WOOD_D, ss(0.66, 0.80, fbm(Pp * sc, 6.0, 2, seed=seed)) * crack)
    c = mixc(c, LICHEN, ss(0.78, 0.90, fbm(Pp, 9.0, 2, seed=seed + 1)) * 0.35)
    return mixc(c, lin(58, 54, 48), cav * 0.5)


def _bridge(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 831)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    b = S.BRIDGE
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    # deck planks: one tone per plank, nails over the stringers, green toward the edges, wet dark where water runs off
    m = M(RK.Z_PLANK)
    pi_ = np.round((x - b['deck_x'][0]) / b['plank_pitch'])
    c = _plank_wood(Pp, Pl, Nn, T, cav, 1, b['plank_pitch'], aa, 832) * (0.84 + 0.30 * hash1(pi_, 33))[:, None]
    edge_y = ss(1.4, 2.3, np.abs(y))
    c = mixc(c, ALGAE, edge_y * ss(0.42, 0.70, fbm(Pp, 4.0, 3, seed=833)) * 0.55)
    c = mixc(c, lin(64, 58, 50), ss(0.62, 0.86, fbm(Pp * np.array([0.2, 1, 1], np.float32), 3.0, 2, seed=834)) * 0.30)
    sy_ = np.min(np.abs(y[:, None] - np.array(b['stringers_y'])[None]), 1)
    nail = (sy_ < 0.012) & (np.abs(dist_periodic(x - b['deck_x'][0], b['plank_pitch']) - 0.06) < 0.014) & (Nn[:, 2] > 0.8)
    c = np.where(nail[:, None], lin(40, 34, 30), c)
    under_strip = np.zeros(n, bool)
    for yc in b['strips_y']:
        under_strip |= np.abs(y - yc) < b['strip_w'] / 2 + 0.03
    c = mixc(c, lin(70, 62, 52), (under_strip & (Nn[:, 2] > 0.5)) * 0.45)
    col[m] = c[m]
    # running strips: tyre-worn dark centre lines, mud carried on from the road, carriage bolts
    m = M(RK.Z_STRIP)
    c = _plank_wood(Pp, Pl, Nn, T, cav, 0, 4.0, aa, 835, base=(108, 98, 84), crack=0.5)
    tyre = np.zeros(n, np.float32)
    for yc in b['strips_y']:
        tyre = np.maximum(tyre, np.exp(-((y - yc) / 0.16) ** 2))
    c = mixc(c, lin(62, 56, 48), tyre * np.clip(Nn[:, 2], 0, 1) * 0.55)
    c = mixc(c, MUD, ss(11.0, 15.5, np.abs(x)) * (0.4 + 0.5 * fbm(Pp, 5.0, 2, seed=836)) * np.clip(Nn[:, 2], 0, 1))
    bolt_ = (dist_periodic(x + 0.3 * np.sign(y), 1.2) < 0.012) & (dist_periodic(y - np.sign(y) * 0.95, 0.24, 0.12) < 0.012) & (Nn[:, 2] > 0.8)
    c = np.where(bolt_[:, None], lin(46, 42, 40), c)
    col[m] = c[m]
    m = M(RK.Z_CURB)
    c = _plank_wood(Pp, Pl, Nn, T, cav, 0, 4.0, aa, 837, base=(98, 90, 78))
    col[m] = mixc(c, MOSS, up * ss(0.45, 0.70, fbm(Pp, 5.0, 3, seed=838)) * 0.6)[m]
    # log stringers: debarked, grey-brown, green and dark underneath, cracks along x, bark left in strips
    m = M(RK.Z_STRINGER)
    c = T(lin(118, 104, 86), 0.14, 0.18)
    c = mixc(c, GREY_WOOD_D, ss(0.66, 0.80, fbm(Pp * np.array([0.25, 6, 6], np.float32), 6.0, 2, seed=839)) * 0.6)
    c = mixc(c, lin(70, 56, 42), ss(0.70, 0.86, fbm(Pp * np.array([0.5, 3, 3], np.float32), 5.0, 2, seed=840)) * 0.7)   # bark
    c = mixc(c, ALGAE, np.clip(-Nn[:, 2], 0, 1) * ss(0.40, 0.65, fbm(Pp, 3.0, 3, seed=841)) * 0.6)
    c = mixc(c, SOIL_D, ss(13.0, 15.0, np.abs(x)) * 0.5)
    col[m] = mixc(c, lin(50, 46, 40), cav * 0.5)[m]
    # pier caps, sills: squared timber, wet and dark, moss on top, black stain under the stringers
    for zz, base in ((RK.Z_CAPB, (96, 86, 72)), (RK.Z_SILL, (88, 78, 64))):
        m = M(zz)
        c = _plank_wood(Pp, Pl, Nn, T, cav, 1, 5.2, aa, 842 + zz, base=base, crack=0.7)
        c = mixc(c, MOSS, up * ss(0.50, 0.72, fbm(Pp, 5.0, 3, seed=844)) * 0.6)
        col[m] = c[m]
    # piles: grey above, algae and wet soil toward the foot
    m = M(RK.Z_PILE)
    c = T(lin(112, 100, 84), 0.14, 0.18)
    c = mixc(c, GREY_WOOD_D, ss(0.66, 0.80, fbm(Pp * np.array([6, 6, 0.25], np.float32), 6.0, 2, seed=845)) * 0.6)
    c = mixc(c, ALGAE, ss(2.5, 0.3, hz) * (0.4 + 0.4 * fbm(Pp, 4.0, 2, seed=846)))
    c = mixc(c, SOIL_D, ss(0.6, 0.0, hz) * 0.7)
    col[m] = c[m]
    m = M(RK.Z_BRACE)
    c = _plank_wood(Pp, Pl, Nn, T, cav, 2, 1.0, aa, 847, base=(116, 108, 94))
    c = mixc(c, ALGAE, ss(1.8, 0.2, hz) * 0.4)
    col[m] = c[m]
    m = M(RK.Z_CRIB)
    c = bark(Pp, T, up, 848)
    col[m] = _foot(c, hz, Pl, 0.25, 849)[m]
    m = M(RK.Z_STONE)
    col[m] = stone(Pp, Nn, T, cav, up, hz, 850)[m]
    # the railing: grey posts, the handrail polished by hands on top, lichen on the outer faces
    m = M(RK.Z_RPOST)
    c = _plank_wood(Pp, Pl, Nn, T, cav, 2, 1.0, aa, 851, base=(116, 110, 96))
    c = mixc(c, lin(66, 60, 50), ss(-0.1, -0.5, z) * 0.5)
    col[m] = c[m]
    m = M(RK.Z_RAIL)
    c = _plank_wood(Pp, Pl, Nn, T, cav, 0, 6.0, aa, 852, base=(122, 114, 100))
    c = mixc(c, lin(150, 136, 112), np.clip(Nn[:, 2], 0, 1) * (z > 0.9) * 0.45)
    out_ = np.sign(y) * Nn[:, 1] > 0.6
    c = mixc(c, LICHEN, out_ * ss(0.6, 0.8, fbm(Pp, 6.0, 2, seed=853)) * 0.5)
    col[m] = c[m]
    m = M(RK.Z_STEEL)
    col[m] = steel_black(Pp, T, edge, seed=854)[m]
    m = M(RK.Z_LOGEND)
    c = end_grain(Pp, T, n_hi, 855) * 0.82 + lin(96, 90, 80) * 0.18
    col[m] = mixc(c, lin(60, 54, 46), cav * 0.5)[m]
    m = M(RK.Z_BSPOST)
    col[m] = _foot(galv(Pp, T, seed=856), hz, Pl, 0.35, 857)[m]
    m = M(RK.Z_BSBACK)
    col[m] = mixc(T(lin(124, 127, 122), 0.10, 0.14), lin(84, 84, 78), cav * 0.3 + up * 0.3)[m]
    # seams between planks / boards: the 1-texel groove
    seam = M(RK.Z_PLANK) & (Nn[:, 2] > 0.8) & (np.abs(dist_periodic(x - b['deck_x'][0], b['plank_pitch']) - b['plank_pitch'] / 2) < 0.004)
    gr = np.where(seam, 0.6, gr)
    return col, gr


# ================================================================ the overlook deck (pressure-treated pine)
def _kdi(Pp, Nn, T, cav, along, seed, base=(132, 128, 104)):
    """pressure-treated pine: the salts' green in the shade and on the sides, grey where the sun and rain bleach it"""
    sc = np.ones(3, np.float32) * 6.0
    sc[along] = 0.30
    c = T(lin(*base), 0.12, 0.16)
    c = mixc(c, lin(108, 122, 92), (1 - np.clip(Nn[:, 2], 0, 1)) * 0.45)
    c = mixc(c, lin(146, 142, 130), np.clip(Nn[:, 2], 0, 1) * 0.35)
    c = mixc(c, lin(70, 68, 58), ss(0.66, 0.80, fbm(Pp * sc, 6.0, 2, seed=seed)) * 0.55)
    return mixc(c, lin(62, 60, 50), cav * 0.5)


def _deck(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 861)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    d = S.DECK
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    m = M(RK.Z_DBOARD)                                                   # boards: worn path steps -> railing, needles, nails
    bi = np.floor((y - d['y'][0]) / ((d['y'][1] - d['y'][0]) / 23))
    c = _kdi(Pp, Nn, T, cav, 0, 862) * (0.88 + 0.22 * hash1(bi, 34))[:, None]
    path = np.exp(-((x - 0.25 * (y - 0.0)) / 0.55) ** 2) * ss(-0.2, 1.0, y) * ss(3.7, 2.6, y)
    path = np.maximum(path, np.exp(-((y - 3.2) / 0.40) ** 2) * ss(-2.6, -1.0, x) * ss(2.6, 1.2, x))
    c = mixc(c, lin(156, 146, 124), np.clip(path, 0, 1) * 0.35 * np.clip(Nn[:, 2], 0, 1))
    c = mixc(c, lin(104, 74, 46), ss(0.72, 0.90, fbm(Pp, 22.0, 1, seed=863)) * 0.35 * np.clip(Nn[:, 2], 0, 1))     # needles
    c = mixc(c, ALGAE, ss(2.0, 2.5, np.abs(x)) * ss(0.5, 0.75, fbm(Pp, 4.0, 2, seed=864)) * 0.4)
    nail = (np.min(np.abs(x[:, None] - np.array([-2.4, -1.6, -0.8, 0.0, 0.8, 1.6, 2.4])[None]), 1) < 0.012) & \
           (np.abs(dist_periodic(y - d['y'][0], (d['y'][1] - d['y'][0]) / 23) - 0.05) < 0.011) & (Nn[:, 2] > 0.8)
    c = np.where(nail[:, None], lin(48, 44, 40), c)
    col[m] = c[m]
    m = M(RK.Z_DJOIST)
    col[m] = _kdi(Pp, Nn, T, cav, 0, 865, base=(118, 124, 98))[m]
    m = M(RK.Z_DLEG)
    c = _kdi(Pp, Nn, T, cav, 2, 866, base=(122, 120, 98))
    col[m] = _foot(c, hz, Pl, 0.5, 867)[m]
    m = M(RK.Z_DRPOST)
    col[m] = _kdi(Pp, Nn, T, cav, 2, 868, base=(128, 126, 106))[m]
    m = M(RK.Z_DRAIL)
    c = _kdi(Pp, Nn, T, cav, 0, 869, base=(134, 130, 110))
    col[m] = mixc(c, lin(160, 146, 118), np.clip(Nn[:, 2], 0, 1) * (z > 1.6) * 0.4)[m]
    m = M(RK.Z_DSTEP)
    c = _kdi(Pp, Nn, T, cav, 0, 870)
    c = mixc(c, MUD, np.clip(Nn[:, 2], 0, 1) * np.exp(-(x / 0.35) ** 2) * 0.45)
    col[m] = _foot(c, hz, Pl, 0.3, 871)[m]
    m = M(RK.Z_BENCH)                                                    # stained brown, the stain worn off the seat
    c = T(lin(112, 80, 52), 0.12, 0.16)
    c = mixc(c, lin(150, 130, 100), np.clip(Nn[:, 2], 0, 1) * ss(0.4, 0.8, fbm(Pp, 4.0, 2, seed=872)) * 0.5)
    c = mixc(c, lin(70, 64, 54), ss(0.66, 0.80, fbm(Pp * np.array([0.3, 6, 6], np.float32), 6.0, 2, seed=873)) * 0.4)
    sx_, sy_ = d['bench']['c']
    carve = (np.abs(x - sx_ - 0.45) < 0.09) & (np.abs(y - sy_ - 0.06) < 0.03) & (Nn[:, 2] > 0.8) & \
            (dist_periodic(x - sx_, 0.022) < 0.004)                     # someone's initials cut into the seat
    c = np.where(carve[:, None], lin(70, 50, 34), c)
    col[m] = mixc(c, lin(60, 48, 36), cav * 0.4)[m]
    m = M(RK.Z_SCOPE)                                                    # dark green enamel, worn to metal at the edges
    c = T(lin(36, 52, 42), 0.08, 0.12)
    c = mixc(c, lin(120, 122, 118), edge * 0.6)
    col[m] = mixc(c, lin(20, 22, 22), cav * 0.4)[m]
    m = M(RK.Z_SCOPEPOST)
    c = T(lin(40, 62, 48), 0.12, 0.2)
    col[m] = mixc(c, RUST, np.clip(0.35 + 0.5 * fbm(Pp, 12.0, 2, seed=874) + edge * 0.4, 0, 0.9))[m]
    m = M(RK.Z_DFOOT)
    c = T(lin(140, 138, 130), 0.14, 0.2)
    col[m] = _foot(c, hz, Pl, 0.2, 875)[m]
    m = M(RK.Z_DEND)
    col[m] = (end_grain(Pp, T, n_hi, 876) * 0.7 + lin(110, 112, 90) * 0.3)[m]
    m = M(RK.Z_DSTEEL)
    col[m] = galv(Pp, T, seed=877)[m]
    seam = M(RK.Z_DBOARD) & (Nn[:, 2] > 0.8) & (dist_periodic(y - d['y'][0], (d['y'][1] - d['y'][0]) / 23) < 0.004)
    gr = np.where(seam, 0.6, gr)
    return col, gr


# ================================================================ the windfall
def _windfall(Pp, Pl, Nn, Z, ao, aa, hz, own):
    n = len(Pp)
    n_lo, n_mid, n_hi, up, cav, edge = _common(Pp, Nn, ao, 881)
    T = _T(n_lo, n_hi)
    M = lambda zz: Z == zz
    x, y, z = Pl[:, 0], Pl[:, 1], Pl[:, 2]
    t = S.TREE
    col = np.tile(lin(128, 128, 128), (n, 1))
    gr = np.zeros(n, np.float32)
    is_log = own == 'LogCut'
    # dead spruce bark: grey-brown scales; patches where it fell off (silver wood, bark-beetle galleries); lichen;
    # damp, dark and mossy where it lies on the ground; the log's bark scraped on one side where it was dragged
    m = M(RK.Z_TBARK)
    c = T(lin(92, 84, 76), 0.14, 0.20)
    scales = fbm(Pp * np.array([3, 1, 1], np.float32), 26.0, 2, seed=882)
    c = c * (0.82 + 0.30 * scales)[:, None]
    c = mixc(c, lin(52, 44, 38), ss(0.62, 0.78, fbm(Pp * np.array([0.5, 2, 2], np.float32), 14.0, 2, seed=883)) * 0.5)
    bare = ss(0.58, 0.66, fbm(Pp * np.array([0.35, 1, 1], np.float32), 1.6, 3, seed=884))
    wood = T(lin(150, 142, 126), 0.10, 0.14)
    gal = fbm(Pp * np.array([0.6, 1, 1], np.float32), 18.0, 2, seed=885)
    galleries = ss(0.03, 0.0, np.abs(gal - 0.5)) * ss(0.4, 0.7, fbm(Pp, 4.0, 2, seed=886))
    wood = mixc(wood, lin(80, 70, 58), galleries * 0.8)
    c = mixc(c, wood, bare * 0.95)
    c = mixc(c, LICHEN, ss(0.70, 0.86, fbm(Pp, 7.0, 2, seed=887)) * np.clip(Nn[:, 2] + 0.3, 0, 1) * 0.5)
    low = ss(0.25, 0.0, hz) * np.clip(-Nn[:, 2] + 0.2, 0, 1)
    c = mixc(c, lin(46, 42, 34), low * 0.7)
    c = mixc(c, MOSS, ss(0.35, 0.05, hz) * ss(0.45, 0.70, fbm(Pp, 5.0, 2, seed=888)) * 0.55)
    scrape = is_log & (Nn[:, 1] > 0.35) & (ss(0.55, 0.65, fbm(Pp * np.array([0.08, 1, 1], np.float32), 10.0, 2, seed=889)) > 0.5)
    c = np.where(scrape[:, None], mixc(lin(176, 156, 120) * np.ones((n, 1), np.float32), lin(110, 96, 74),
                                       fbm(Pp * np.array([0.05, 2, 2], np.float32), 30.0, 1, seed=890)), c)
    col[m] = c[m]
    # the fresh saw cuts: pale cream, rings, the chain's arcs, blue stain in the dead sapwood, a dark bark rim
    m = M(RK.Z_TCUT)
    c = T(lin(220, 192, 146), 0.06, 0.10)
    rings = 0.5 + 0.5 * np.cos(2 * np.pi * fbm(Pp, 2.2, 2, seed=891) * 18.0)
    c = c * (0.92 + 0.10 * rings)[:, None]
    arcs = 0.5 + 0.5 * np.cos(2 * np.pi * (Pp[:, 1] * 0.8 + Pp[:, 2]) / 0.018)
    c = c * (0.95 + 0.06 * arcs)[:, None]
    # radial position on the face: the distance from the cut's centre (the trunk's axis there)
    cen = np.zeros((n, 3), np.float32)
    rr = np.ones(n, np.float32) * 0.2
    for cx_, rad, who in ((t['cut0'], 0.215, 'FallenTree'), (t['cut1'], 0.185, 'FallenTree'),
                          (-(t['cut1'] - t['cut0']) / 2 + t['kerf'], 0.215, 'LogCut'),
                          ((t['cut1'] - t['cut0']) / 2 - t['kerf'], 0.185, 'LogCut')):
        sel = (own == who) & (np.abs(x - cx_) < 0.06)
        if sel.any():
            cy, cz = np.median(y[sel & M(RK.Z_TCUT)]) if (sel & M(RK.Z_TCUT)).any() else 0.0, \
                np.median(z[sel & M(RK.Z_TCUT)]) if (sel & M(RK.Z_TCUT)).any() else 0.0
            cen[sel] = (cx_, cy, cz)
            rr[sel] = rad
    rad_f = np.hypot(y - cen[:, 1], z - cen[:, 2]) / rr
    c = mixc(c, lin(132, 140, 146), ss(0.62, 0.82, rad_f) * ss(0.35, 0.65, fbm(Pp, 9.0, 2, seed=892)) * 0.55)   # blue stain
    c = mixc(c, lin(196, 166, 118), ss(0.25, 0.0, rad_f) * 0.35)                                               # the pith
    c = mixc(c, lin(70, 56, 42), ss(0.90, 0.99, rad_f) * 0.8)                                                  # bark rim
    col[m] = c[m]
    # dead branches: grey, beard lichen in tufts; broken ends pale
    m = M(RK.Z_TBRANCH)
    c = T(lin(108, 100, 90), 0.12, 0.18)
    c = mixc(c, lin(168, 176, 150), ss(0.66, 0.82, fbm(Pp, 10.0, 2, seed=893)) * 0.55)
    col[m] = mixc(c, lin(60, 56, 50), cav * 0.4)[m]
    m = M(RK.Z_TBREAK)
    col[m] = mixc(T(lin(158, 146, 122), 0.10, 0.14), lin(104, 96, 82), ss(0.5, 0.8, fbm(Pp, 20.0, 1, seed=894)) * 0.4)[m]
    # the root plate: earth and roots; its front is the old forest floor (moss, needles), the pit and the heaped soil
    m = M(RK.Z_TROOT)
    c = T(lin(68, 54, 40), 0.16, 0.22)
    fib = ss(0.04, 0.0, np.abs(fbm(Pp, 6.0, 2, seed=895) - 0.5))
    c = mixc(c, lin(120, 98, 72), fib * 0.7)
    c = mixc(c, lin(112, 108, 100), ss(0.80, 0.90, fbm(Pp, 30.0, 1, seed=896)) * 0.5)                         # grit, pebbles
    col[m] = mixc(c, lin(36, 30, 24), cav * 0.5)[m]
    m = M(RK.Z_SOIL)
    plate = np.abs(Nn[:, 2]) < 0.75
    floor_ = mixc(T(lin(74, 82, 48), 0.18, 0.22), lin(98, 72, 46), ss(0.45, 0.70, fbm(Pp, 6.0, 2, seed=897)) * 0.6)
    soil = T(lin(58, 46, 34), 0.18, 0.25)
    soil = mixc(soil, lin(96, 80, 60), ss(0.6, 0.85, fbm(Pp, 12.0, 2, seed=898)) * 0.4)
    soil = mixc(soil, lin(104, 76, 46), ss(0.80, 0.92, fbm(Pp, 25.0, 1, seed=899)) * 0.4)                     # needles
    col[m] = np.where(plate[:, None], floor_, soil)[m]
    m = M(RK.Z_TSTONE)
    col[m] = stone(Pp, Nn, T, cav, up, hz, 900)[m]
    # sawdust: fresh orange-cream, darker specks of bark, fading into the ground at its rim
    m = M(RK.Z_SAWDUST)
    c = T(lin(202, 172, 124), 0.10, 0.18)
    c = mixc(c, lin(96, 80, 64), ss(0.78, 0.92, fbm(Pp, 50.0, 1, seed=901)) * 0.6)
    c = mixc(c, SOIL, ss(0.60, 0.80, fbm(Pp, 9.0, 2, seed=904)) * 0.45)                 # trodden into the earth in patches
    c = mixc(c, SOIL, ss(0.016, 0.004, hz) * 0.65)
    col[m] = c[m]
    # the drag trail: compressed dark earth, scrape lines along it, bark flakes and sawdust carried along
    m = M(RK.Z_DRAG)
    c = T(lin(64, 54, 42), 0.16, 0.2)
    c = mixc(c, lin(46, 38, 30), ss(0.45, 0.75, fbm(Pp * np.array([1, 0.2, 1], np.float32), 8.0, 2, seed=902)) * 0.5)
    c = mixc(c, lin(150, 126, 90), ss(0.84, 0.94, fbm(Pp, 30.0, 1, seed=903)) * 0.5)
    col[m] = c[m]
    return col, gr
