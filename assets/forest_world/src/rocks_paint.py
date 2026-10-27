"""Painter of the forest_rocks atlases (psxbake): Harz-like granite - warm grey with cool blotches, mica and quartz specks,
dark water streaks down the steep faces, a crack or two; pale grey-green lichen with rare orange spots, moss on the tops,
at the foot and in the joints, spruce needles on the ledges, soil at the foot. Painted light: tops lighter, undersides
darker. The model is told by its zone (rocks_kit: Z0 + 2 i, the buried underside Z0 + 2 i + 1); z is the height above
its ground line (the models stand on z = 0)."""
import numpy as np
from noise import ss, mixc, fbm
from psxbake import lin
import rocks_kit as RK

GRANITE, GRANITE_C, GRANITE_W = lin(126, 122, 114), lin(104, 107, 106), lin(136, 125, 106)
MICA, QUARTZ = lin(56, 55, 53), lin(182, 180, 172)
STREAK = lin(64, 66, 60)
LICHEN, LICHEN_D, LICHEN_O = lin(160, 166, 140), lin(124, 132, 108), lin(178, 128, 60)
MOSS, MOSS_D, MOSS_L = lin(70, 86, 40), lin(46, 58, 30), lin(98, 112, 54)
NEEDLE_A, NEEDLE_B, NEEDLE_C = lin(132, 92, 46), lin(96, 70, 40), lin(66, 50, 32)
SOIL, SOIL_D = lin(76, 62, 46), lin(50, 41, 31)
KIND = {'stone': dict(moss=0.55, lichen=0.45, needles=0.6), 'boulder': dict(moss=0.6, lichen=0.6, needles=0.6),
        'cliff': dict(moss=0.65, lichen=0.65, needles=0.75)}
OVERRIDE = {'ForestStone_6': dict(moss=1.0, lichen=0.4, needles=0.8)}
DRAFT_COL = (110, 108, 102)


def make_painter(models, heights):
    """models: rocks_kit.MODELS; heights: {name: the top z above the ground}"""
    n = len(models)
    H = np.ones(n, np.float32)
    PM = np.zeros((n, 3), np.float32)
    for m in models:
        p = dict(KIND[m['kind']], **OVERRIDE.get(m['name'], {}))
        H[m['idx']] = max(heights[m['name']], 0.1)
        PM[m['idx']] = (p['moss'], p['lichen'], p['needles'])

    def painter(Pp, Nn, Z, ao, aa):
        k = np.clip((Z - RK.Z0) // 2, 0, n - 1)
        hid = ((Z - RK.Z0) % 2) == 1
        z = Pp[:, 2]
        up, down = np.clip(Nn[:, 2], 0, 1), np.clip(-Nn[:, 2], 0, 1)
        steep = 1.0 - np.abs(Nn[:, 2])
        moss_k, lich_k, ndl_k = PM[k, 0], PM[k, 1], PM[k, 2]
        n_lo = fbm(Pp, 0.55, 3, seed=1)
        n_mid = fbm(Pp, 2.8, 3, seed=2)
        n_hi = fbm(Pp, 22.0, 2, seed=3)
        # granite: blotches, a warm cast, specks
        c = mixc(np.tile(GRANITE, (len(z), 1)), GRANITE_C, ss(0.38, 0.66, n_lo) * 0.8)
        c = mixc(c, GRANITE_W, ss(0.56, 0.80, n_mid) * 0.45)
        c = c * (0.90 + 0.16 * (n_mid - 0.5) * 2 + 0.10 * (n_hi - 0.5))[:, None]
        sp = fbm(Pp, 68.0, 1, seed=4)
        c = mixc(c, MICA, ss(0.30, 0.22, sp) * 0.65)
        c = mixc(c, QUARTZ, ss(0.72, 0.80, sp) * 0.45)
        # dark water streaks down the steep faces
        st = fbm(Pp, 4.5, 2, seed=5, stretch=(1.0, 1.0, 0.13))
        c = mixc(c, STREAK, ss(0.60, 0.74, st) * ss(0.35, 0.75, steep) * (1 - up) * 0.45)
        # lichen: pale patches, darker hearts, rare orange spots on the sunny tops
        lc = fbm(Pp, 4.2, 3, seed=7)
        patch = ss(0.60, 0.72, lc) * lich_k * (0.35 + 0.65 * (1 - down))
        c = mixc(c, LICHEN, patch * 0.42)
        c = mixc(c, LICHEN_D, patch * ss(0.58, 0.72, fbm(Pp, 14.0, 2, seed=8)) * 0.45)
        c = mixc(c, LICHEN_O, ss(0.80, 0.86, fbm(Pp, 8.0, 2, seed=9)) * ss(0.2, 0.6, up) * lich_k * 0.8)
        # moss: on the tops, at the foot, in the joints
        m_top = ss(0.45, 0.80, up) * ss(0.44, 0.62, fbm(Pp, 2.0, 3, seed=10))
        m_foot = ss(0.40, 0.02, z) * ss(0.38, 0.60, fbm(Pp, 3.6, 2, seed=11))
        m_joint = ss(0.58, 0.32, ao) * ss(0.40, 0.65, fbm(Pp, 5.0, 2, seed=12)) * 0.7
        moss = np.clip((m_top + m_foot + m_joint) * moss_k, 0, 1)
        mv = fbm(Pp, 14.0, 2, seed=13)
        mcol = np.where((mv > 0.62)[:, None], MOSS_L, np.where((mv < 0.40)[:, None], MOSS_D, MOSS))
        c = mixc(c, mcol, ss(0.25, 0.60, moss))
        # spruce needles on the ledges and tops
        ndl = ss(0.74, 0.94, up) * ss(0.48, 0.68, fbm(Pp, 6.0, 2, seed=14)) * ndl_k
        pick = fbm(Pp, 40.0, 1, seed=15)
        ncol = np.where((pick > 0.58)[:, None], NEEDLE_A, np.where((pick > 0.36)[:, None], NEEDLE_B, NEEDLE_C))
        c = mixc(c, ncol, ss(0.30, 0.65, ndl))
        # soil at the foot
        c = mixc(c, SOIL, ss(0.20, 0.0, z) * (0.55 + 0.35 * fbm(Pp, 7.0, 2, seed=16)))
        c = mixc(c, SOIL_D, ss(0.0, -0.10, z))
        # painted light: tops lighter, undersides darker
        c = c * (0.93 + 0.12 * up - 0.12 * down)[:, None]
        c[hid] = SOIL_D
        # a crack or two on the faces: one-texel grooves along a noise isoline
        cr = np.abs(fbm(Pp, 1.1, 2, seed=17) - 0.5)
        groove = ss(0.006, 0.0, cr) * ss(0.3, 0.7, steep) * (1 - ss(0.3, 0.7, moss)) * 0.6
        groove[hid] = 0
        return np.clip(c, 0, 1).astype(np.float32), groove.astype(np.float32)

    return painter
