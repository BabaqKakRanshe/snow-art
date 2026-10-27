"""Painter of the forest_trash atlas (psxbake): weathered rubbish lying in a spruce forest - newspaper gone grey and wavy,
wet cardboard, cups, PET bottles with blue caps, black and blue bags, tins with faded labels and rust, rusty sheet and pipe,
grey planks with nails, bark, green / brown / clear glass with bright glints; the mound under each pile is soil with
specks of that rubbish; the bale of each clump is the same rubbish pressed into layers. Needles and soil on the piles,
painted light (tops lighter, undersides darker). Zones: trash_kit."""
import numpy as np
from noise import ss, mixc, fbm
from psxbake import lin, hash1
import trash_kit as TK

SOIL, SOIL_D = lin(70, 57, 42), lin(48, 39, 30)
NEEDLE_A, NEEDLE_B, NEEDLE_C = lin(132, 92, 46), lin(96, 70, 40), lin(66, 50, 32)
RUST, RUST_D, RUST_L = lin(124, 64, 32), lin(72, 38, 22), lin(150, 92, 52)
C = {
    TK.Z_NEWS: lin(196, 192, 178), TK.Z_CARD: lin(148, 112, 74), TK.Z_CUP: lin(218, 214, 204), TK.Z_CUP_IN: lin(74, 52, 36),
    TK.Z_PET: lin(150, 178, 186), TK.Z_PET_CAP: lin(40, 78, 168), TK.Z_BAG_K: lin(30, 30, 33), TK.Z_BAG_B: lin(44, 72, 132),
    TK.Z_TRAY: lin(208, 208, 198), TK.Z_YOG: lin(222, 204, 172), TK.Z_CANISTER: lin(150, 44, 34), TK.Z_CAN: lin(152, 152, 146),
    TK.Z_CAN_TOP: lin(150, 150, 144), TK.Z_CRUSH: lin(130, 120, 106), TK.Z_SHEET: lin(118, 74, 44), TK.Z_PIPE: lin(96, 60, 40),
    TK.Z_WIRE: lin(82, 52, 34), TK.Z_PLANK: lin(124, 116, 100), TK.Z_NAIL: lin(90, 54, 34), TK.Z_BARK: lin(82, 66, 52),
    TK.Z_WOOD_END: lin(172, 142, 98), TK.Z_GL_G: lin(42, 92, 52), TK.Z_GL_B: lin(84, 48, 22), TK.Z_GL_C: lin(168, 184, 178),
    TK.Z_GL_LABEL: lin(212, 202, 162), TK.Z_SHARD: lin(150, 176, 160), TK.Z_JAR_LID: lin(168, 138, 72), TK.Z_BOX: lin(204, 170, 64),
}
LABELS = [lin(178, 46, 38), lin(48, 112, 62), lin(214, 176, 52), lin(46, 82, 150), lin(220, 220, 214)]
SPECKS = {'Paper': [lin(196, 192, 178), lin(148, 112, 74), lin(218, 214, 204)],
          'Plastic': [lin(150, 178, 186), lin(44, 72, 132), lin(208, 208, 198), lin(40, 78, 168)],
          'Metal': [RUST, lin(152, 152, 146), RUST_D, lin(178, 46, 38)],
          'Wood': [lin(124, 116, 100), lin(172, 142, 98), lin(82, 66, 52)],
          'Glass': [lin(42, 92, 52), lin(84, 48, 22), lin(168, 184, 178), lin(220, 232, 226)],
          'Mixed': [lin(196, 192, 178), lin(30, 30, 33), lin(152, 152, 146), lin(42, 92, 52), lin(148, 112, 74), lin(178, 46, 38)]}
BALE_COLS = {'Paper': [lin(196, 192, 178), lin(148, 112, 74), lin(160, 156, 146), lin(120, 90, 60)],
             'Plastic': [lin(150, 178, 186), lin(208, 208, 198), lin(44, 72, 132), lin(40, 40, 44), lin(170, 176, 176)],
             'Metal': [RUST, lin(140, 140, 134), RUST_D, lin(88, 88, 86), RUST_L, lin(150, 50, 40)],
             'Wood': [lin(124, 116, 100), lin(172, 142, 98), lin(82, 66, 52), lin(100, 90, 74)],
             'Glass': [lin(42, 92, 52), lin(84, 48, 22), lin(150, 166, 160), lin(30, 60, 36), lin(110, 118, 114)],
             'Mixed': [lin(196, 192, 178), lin(40, 40, 44), lin(140, 140, 134), lin(148, 112, 74), lin(42, 92, 52), lin(90, 76, 60)]}
BALE_DIRT = lin(96, 86, 70)
DRAFT_COL = {z: tuple(int(255 * (c ** (1 / 2.2))) for c in v) for z, v in C.items()}
for k in TK.KINDS:
    DRAFT_COL[TK.Z_MOUND[k]] = (90, 76, 60)
    DRAFT_COL[TK.Z_BALE[k]] = (140, 130, 110)


def _pick(cols, t):
    """one of the colours by a 0..1 value per texel"""
    cols = np.asarray(cols, np.float32)
    i = np.clip((t * len(cols)).astype(np.int32), 0, len(cols) - 1)
    return cols[i]


def painter(Pp, Nn, Z0, ao, aa):
    n = len(Z0)
    clump = Z0 >= 400
    Z = np.where(clump, Z0 - TK.CLUMP_DZ, Z0)
    up, down = np.clip(Nn[:, 2], 0, 1), np.clip(-Nn[:, 2], 0, 1)
    z = Pp[:, 2]
    c = np.zeros((n, 3), np.float32)
    n_mid = fbm(Pp, 9.0, 3, seed=31)
    n_hi = fbm(Pp, 40.0, 2, seed=32)
    for zone, col in C.items():
        m = Z == zone
        if m.any():
            c[m] = col
    # newspaper: text blocks and a headline, yellowed, wavy wet stains
    m = Z == TK.Z_NEWS
    if m.any():
        q = Pp[m]
        blk = hash1(np.floor(q[:, 0] * 36) + 57.0 * np.floor(q[:, 1] * 9)) > 0.45
        c[m] = mixc(c[m], lin(120, 118, 112), blk * 0.45)
        c[m] = mixc(c[m], lin(40, 40, 40), (hash1(np.floor(q[:, 0] * 6) + 13 * np.floor(q[:, 1] * 3)) > 0.9) * 0.6)
        c[m] = mixc(c[m], lin(170, 150, 104), ss(0.55, 0.75, fbm(q, 5.0, 2, seed=33)) * 0.55)
    # cardboard: corrugation stripes, wet dark patches, tape
    m = Z == TK.Z_CARD
    if m.any():
        q = Pp[m]
        c[m] = c[m] * (0.92 + 0.10 * (np.sin((q[:, 0] + q[:, 1]) * 260) > 0.6))[:, None]
        c[m] = mixc(c[m], lin(96, 70, 46), ss(0.55, 0.72, fbm(q, 4.0, 2, seed=34)) * 0.7)
    # cups and the yoghurt pot: a coloured print
    for zz, cols in ((TK.Z_CUP, [lin(176, 40, 36), lin(46, 82, 150)]), (TK.Z_YOG, [lin(206, 94, 60), lin(214, 176, 52)])):
        m = Z == zz
        if m.any():
            q = Pp[m]
            c[m] = mixc(c[m], _pick(cols, hash1(np.floor(q[:, 0] * 3) + 7 * np.floor(q[:, 1] * 3))),
                        ss(0.52, 0.60, fbm(q, 14.0, 2, seed=35)) * 0.85)
    # PET: glints along the tops, a little green; caps red or blue
    m = Z == TK.Z_PET
    if m.any():
        c[m] = mixc(c[m], lin(226, 236, 236), ss(0.55, 0.95, up[m]) * ss(0.5, 0.7, n_hi[m]) * 0.8)
    m = Z == TK.Z_PET_CAP
    if m.any():
        q = Pp[m]
        c[m] = _pick([lin(40, 78, 168), lin(176, 40, 36), lin(220, 220, 214)], hash1(np.floor(q[:, 0] * 12) + 31 * np.floor(q[:, 1] * 12)))
    # bags: wrinkle highlights
    for zz in (TK.Z_BAG_K, TK.Z_BAG_B):
        m = Z == zz
        if m.any():
            w = fbm(Pp[m], 22.0, 2, seed=36)
            c[m] = c[m] * (0.75 + 0.9 * ss(0.55, 0.80, w) * (0.4 + 0.6 * up[m]))[:, None]
    # tins: a faded label of one colour per tin, scratches, rust; crushed ones rustier
    for zz, r in ((TK.Z_CAN, 0.25), (TK.Z_CRUSH, 0.6), (TK.Z_CAN_TOP, 0.35)):
        m = Z == zz
        if m.any():
            q = Pp[m]
            if zz != TK.Z_CAN_TOP:
                lab = _pick(LABELS, hash1(np.floor(q[:, 0] * 5) + 17 * np.floor(q[:, 1] * 5)))
                c[m] = mixc(c[m], lab * 0.85, ss(0.30, 0.42, fbm(q, 18.0, 2, seed=37)) * 0.9)
            c[m] = mixc(c[m], RUST, ss(1.0 - r, 1.0 - r + 0.18, fbm(q, 12.0, 3, seed=38)) * 0.85)
    # sheet, pipe, wire, nails, the jar lid: rust in three shades, old paint on the sheet
    for zz in (TK.Z_SHEET, TK.Z_PIPE, TK.Z_WIRE, TK.Z_NAIL, TK.Z_JAR_LID):
        m = Z == zz
        if m.any():
            q = Pp[m]
            r = fbm(q, 10.0, 3, seed=39)
            c[m] = mixc(c[m], RUST_D, ss(0.55, 0.75, r) * 0.7)
            c[m] = mixc(c[m], RUST_L, ss(0.40, 0.25, r) * 0.5)
            if zz == TK.Z_SHEET:
                c[m] = mixc(c[m], lin(104, 112, 102), ss(0.62, 0.70, fbm(q, 3.5, 2, seed=40)) * 0.9)
    # wood: grey weathered planks, grain, dark wet patches, a little moss; bark with lichen; fresh ends
    m = Z == TK.Z_PLANK
    if m.any():
        q = Pp[m]
        g = np.sin((q[:, 0] * 0.9 + q[:, 1] * 0.4) * 140 + 6 * fbm(q, 6.0, 2, seed=41))
        c[m] = c[m] * (0.90 + 0.10 * g)[:, None]
        c[m] = mixc(c[m], lin(78, 72, 60), ss(0.58, 0.76, fbm(q, 4.0, 2, seed=42)) * 0.6)
        c[m] = mixc(c[m], lin(70, 86, 40), ss(0.72, 0.84, fbm(q, 8.0, 2, seed=43)) * up[m] * 0.6)
    m = Z == TK.Z_BARK
    if m.any():
        c[m] = mixc(c[m], lin(150, 156, 132), ss(0.66, 0.78, fbm(Pp[m], 16.0, 2, seed=44)) * 0.6)
    # glass: glints on the tops and edges, darker in the depth
    for zz in (TK.Z_GL_G, TK.Z_GL_B, TK.Z_GL_C, TK.Z_SHARD):
        m = Z == zz
        if m.any():
            gl = ss(0.62, 0.92, up[m]) * ss(0.55, 0.72, n_hi[m])
            c[m] = mixc(c[m] * (0.7 + 0.3 * ao[m])[:, None], lin(232, 240, 236), gl * 0.85)
    m = Z == TK.Z_GL_LABEL
    if m.any():
        c[m] = mixc(c[m], lin(170, 44, 38), ss(0.45, 0.55, fbm(Pp[m], 20.0, 1, seed=45)) * 0.8)
    m = Z == TK.Z_BOX
    if m.any():
        c[m] = mixc(c[m], lin(176, 40, 36), ss(0.5, 0.6, fbm(Pp[m], 16.0, 2, seed=46)) * 0.8)
    # mounds: soil with specks of the kind's rubbish
    for k in TK.KINDS:
        m = Z == TK.Z_MOUND[k]
        if m.any():
            q = Pp[m]
            c[m] = mixc(np.tile(SOIL, (int(m.sum()), 1)), SOIL_D, ss(0.4, 0.7, fbm(q, 6.0, 2, seed=47)) * 0.6)
            sp = fbm(q, 40.0, 1, seed=48)
            col = _pick(SPECKS[k], hash1(np.floor(q[:, 0] * 40) + 71 * np.floor(q[:, 1] * 40))) * 0.85
            c[m] = mixc(c[m], col, ss(0.63, 0.69, sp) * 0.8)
    # bales: the rubbish pressed into layers (wood: fibres along the bundle)
    for k in TK.KINDS:
        m = Z == TK.Z_BALE[k]
        if m.any():
            q = Pp[m]
            if k == 'Wood':
                layer = np.floor(q[:, 1] * 30 + q[:, 2] * 30 + 3 * fbm(q, 4.0, 2, seed=49))
            else:
                layer = np.floor(q[:, 2] * 28 + 2.5 * fbm(q, 5.0, 2, seed=49))
            cell = layer + 13.0 * np.floor(q[:, 0] * 9 + q[:, 1] * 7 + 2 * fbm(q, 3.0, 2, seed=50))
            col = mixc(_pick(BALE_COLS[k], hash1(cell)), BALE_DIRT, np.full(int(m.sum()), 0.32, np.float32))
            c[m] = col * (0.86 + 0.18 * hash1(cell + 0.5))[:, None]
            seam = np.abs(np.modf(q[:, 2] * 28 + 2.5 * fbm(q, 5.0, 2, seed=49))[0] - 0.5) > 0.42
            c[m] = c[m] * np.where(seam, 0.7, 1.0)[:, None]
    # weathering: dirt low on the piles, needles on what faces up, painted light
    on_ground = ~clump
    c = mixc(c, SOIL, on_ground * ss(0.06, 0.0, z) * 0.6)
    ndl = on_ground * ss(0.70, 0.92, up) * ss(0.58, 0.74, fbm(Pp, 7.0, 2, seed=51))
    pick = fbm(Pp, 40.0, 1, seed=52)
    ncol = np.where((pick > 0.58)[:, None], NEEDLE_A, np.where((pick > 0.36)[:, None], NEEDLE_B, NEEDLE_C))
    c = mixc(c, ncol, ss(0.25, 0.6, ndl))
    c = c * (0.90 + 0.12 * up - 0.12 * down + 0.10 * (n_mid - 0.5))[:, None]
    return np.clip(c, 0, 1).astype(np.float32), None
