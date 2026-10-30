"""forest_smoke 2.0 printed textures (pixel art in the project's font, point filter; the pager's panel way),
drawn after the Codex concepts the user picked 27.10 (docs/gdd/concept/09_smoking/packs_1.png, lighter_1.png). Brands are
invented (1991, Harz):
  Harzgold  - West, cream flip-top box, gold bands, a crest, the Brocken with its tower, 'FILTER CIGARETTEN';
  Brocken   - East (VEB), soft grey-blue paper pack, the miners' hammer-and-pick in a gear ring, red name block, no filter;
  Nordlicht - menthol, deep green flip-top box, an aurora over spruces, stars.
The 1991 warning (EG): 'DIE EG-GESUNDHEITSMINISTER: RAUCHEN GEFAEHRDET DIE GESUNDHEIT' on the back (no umlauts in the font).
Panels per brand 512 x 256 at 2000 px / m (front, back, left, right, top, bottom of 54 x 88 x 22 mm, the cigarette ends seen inside);
the lighter's panel 64 x 32 (the BLITZ label, the flame); the filters 16 x 32 per brand (u round, v from the joint to
the mouth end, the end cap in the last rows); the ember 8 x 8; the smoke puff 16 x 16 RGBA (4 alpha steps).
python smoke2_tex.py [out_dir]"""
import os, sys, json, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'lib'))
import pxfont as F
from noise import fbm

BRANDS = ('Harzgold', 'Brocken', 'Nordlicht')
S = 2                                     # the packs' print at 2000 px / m: held at the eye, the small print must read
PW, PH = 512, 256
PACK = dict(front=(0, 0, 108, 176), back=(110, 0, 218, 176), left=(220, 0, 264, 176), right=(266, 0, 310, 176),
            top=(312, 0, 420, 44), bottom=(312, 46, 420, 90), inner=(312, 92, 412, 128))
LW, LH = 64, 32
LIGHTER = dict(label=(0, 0, 30, 9), flame=(32, 0, 40, 24), flame_core=(42, 0, 50, 24))


def uv(rect, w, h, inset=0.5):
    """pixel rect (y down) -> (u0, v0, u1, v1) with a half-texel inset"""
    x0, y0, x1, y1 = rect
    return ((x0 + inset) / w, 1 - (y1 - inset) / h, (x1 - inset) / w, 1 - (y0 + inset) / h)


def pack_uv(name):
    return uv(PACK[name], PW, PH)


def lighter_uv(name):
    return uv(LIGHTER[name], LW, LH)


# ------------------------------------------------------------------ drawing helpers
def fill(img, r, col):
    x0, y0, x1, y1 = r
    img[y0:y1, x0:x1] = col


def noise_rect(r, seed, scale=7.0):
    x0, y0, x1, y1 = r
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    p = np.stack([xx / 64.0, yy / 64.0, np.full_like(xx, seed * 0.37)], -1).reshape(-1, 3)
    return fbm(p, scale, 2, seed=seed).reshape(xx.shape) - 0.5


def grain(img, r, seed, amount=5.0, scale=7.0):
    x0, y0, x1, y1 = r
    sub = img[y0:y1, x0:x1].astype(np.float32) + noise_rect(r, seed, scale)[..., None] * amount * 2
    img[y0:y1, x0:x1] = np.clip(sub, 0, 255).astype(np.uint8)


def wear(img, r, seed, light=(236, 228, 210), width=2, amount=0.55):
    """rubbed card at a face's edges: the print worn to the board along the border, more at the corners"""
    x0, y0, x1, y1 = r
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = np.minimum(np.minimum(xx - x0, x1 - 1 - xx), np.minimum(yy - y0, y1 - 1 - yy))
    corner = np.minimum(np.minimum(xx - x0, x1 - 1 - xx), 3) + np.minimum(np.minimum(yy - y0, y1 - 1 - yy), 3)
    n = noise_rect(r, seed, 23.0) + 0.5
    m = ((d < width) & (n > 1 - amount)) | ((corner < 3) & (n > 0.3))
    sub = img[y0:y1, x0:x1]
    sub[m] = (sub[m].astype(np.float32) * 0.35 + np.array(light, np.float32) * 0.65).astype(np.uint8)


def dirt(img, r, seed, col=(70, 60, 48), amount=0.25):
    x0, y0, x1, y1 = r
    n = noise_rect(r, seed, 5.0) + 0.5
    k = np.clip((n - 0.55) * 3.0, 0, 1)[..., None] * amount
    sub = img[y0:y1, x0:x1].astype(np.float32)
    img[y0:y1, x0:x1] = np.clip(sub * (1 - k) + np.array(col, np.float32) * k, 0, 255).astype(np.uint8)


def prop_mask(txt, font, scale=1):
    """proportional set: each glyph trimmed to its inked columns and scaled, 1 px apart (big names stay tight), a space 3
    columns of the scale"""
    h = font['h'] * scale
    one = np.ones((scale, scale), bool)
    cols = []
    for ch in txt:
        g = font['glyphs'].get(ch, font['glyphs'].get(ch.upper(), font['glyphs'][' ']))
        if ch == ' ':
            cols.append(np.zeros((h, 3 * scale), bool))
            continue
        used = np.where(g.any(0))[0]
        if len(used):
            g = g[:, used[0]:used[-1] + 1]
        cols.append(np.kron(g, one))
        cols.append(np.zeros((h, 1), bool))
    return np.concatenate(cols[:-1] if len(cols) > 1 else cols, 1) if cols else np.zeros((h, 1), bool)


def ptext(img, r, cx, cy, txt, font, col, scale=1, bold=False, shadow=None):
    """proportional text centred at (cx, cy) of region r (px from its top left)"""
    m = prop_mask(txt, font, scale)
    if bold:
        m = m | np.pad(m, ((0, 0), (1, 0)))[:, :-1]
    h, w = m.shape
    x, y = int(math.floor(r[0] + cx - w / 2.0 + 0.5)), int(math.floor(r[1] + cy - h / 2.0 + 0.5))
    if shadow is not None:
        F.blit_mask(img, m, x + 1, y + 1, shadow)
    F.blit_mask(img, m, x, y, col)
    return w, h


def hline(img, r, y, col, x0=0, x1=None):
    x1 = r[2] - r[0] if x1 is None else x1
    F.rect(img, r[0] + x0, r[1] + y, r[0] + x1 - 1, r[1] + y, col)


def cig_ends(img, r, filt, paper=(232, 228, 216), gap=(40, 34, 28)):
    """the cigarettes seen from the top inside the pack: 2 rows of round ends (filter or tobacco)"""
    fill(img, r, gap)
    x0, y0, x1, y1 = r
    n_x, n_y = 7, 2
    sx, sy = (x1 - x0) / n_x, (y1 - y0) / n_y
    for j in range(n_y):
        for i in range(n_x):
            cx, cy = x0 + sx * (i + 0.5) + (sx / 2 if j else 0) * 0.0, y0 + sy * (j + 0.5)
            F.disc(img, cx, cy, sx * 0.48, paper)
            F.disc(img, cx, cy, sx * 0.36, filt)


# ------------------------------------------------------------------ the packs (coordinates in mm of the face = px / S)
def R(r, x0, y0, x1, y1):
    """a rect in mm of face r -> px"""
    return (r[0] + int(x0 * S), r[1] + int(y0 * S), r[0] + int(x1 * S), r[1] + int(y1 * S))


def T(img, r, cx, cy, txt, font, col, scale=1, **kw):
    """text centred at (cx, cy) mm of face r"""
    return ptext(img, r, cx * S, cy * S, txt, font, col, scale, **kw)


def band(img, r, y0, y1, col):
    fill(img, R(r, 0, y0, (r[2] - r[0]) / S, y1), col)


def warning(img, r, y0, ink, paper):
    """the 1991 EG warning in a black frame, 3 lines of the small font"""
    w = (r[2] - r[0]) / S
    fill(img, R(r, 3, y0, w - 3, y0 + 21), ink)
    fill(img, R(r, 3.5, y0 + 0.5, w - 3.5, y0 + 20.5), paper)
    for i, ln in enumerate(('DIE EG-GESUNDHEITS-', 'MINISTER: RAUCHEN', 'GEFAEHRDET DIE', 'GESUNDHEIT')):
        T(img, r, w / 2, y0 + 3.5 + i * 4.5, ln, F.F35, ink)


def mountain(img, r, cx, base, half, height, dark, light):
    """the Brocken: a broad hill with a shoulder, the lit flank lighter, the transmitter tower on the top"""
    for i in range(int(-half * S), int(half * S) + 1):
        x = i / S
        h = height * max(0.0, 1 - (abs(x) / half) ** 1.4) + 1.6 * math.exp(-((x + half * 0.45) / 3.0) ** 2)
        col = dark if x < 1 else light
        F.rect(img, r[0] + int((cx + x) * S), r[1] + int((base - h) * S), r[0] + int((cx + x) * S), r[1] + int(base * S), col)
    F.rect(img, r[0] + int(cx * S), r[1] + int((base - height - 6) * S), r[0] + int(cx * S) + 1, r[1] + int((base - height) * S), dark)
    F.rect(img, r[0] + int(cx * S) - 2, r[1] + int((base - height - 4) * S), r[0] + int(cx * S) + 3, r[1] + int((base - height - 4) * S), dark)


def stack(img, r, y0, word, col, step=5.5):
    """a name stacked down a narrow side"""
    for i, ch in enumerate(word):
        T(img, r, (r[2] - r[0]) / S / 2, y0 + i * step, ch, F.F57, col)


def pack_harzgold():
    img = np.zeros((PH, PW, 3), np.uint8)
    CREAM, GOLD, GOLDD, BROWN, BROWNL, INK, RED = ((228, 216, 186), (178, 140, 64), (128, 96, 40), (110, 90, 66), (150, 128, 98),
                                                    (54, 38, 24), (156, 36, 28))
    for k in ('front', 'back'):
        r = PACK[k]
        fill(img, r, CREAM)
        grain(img, r, 11 + len(k), 5)
        band(img, r, 0, 6, GOLD)                                                  # the gold top of the lid
        band(img, r, 7, 7.5, GOLDD)
        band(img, r, 21.5, 22, GOLDD)                                             # the lid's cut, a printed rule
        cx = 27                                                                   # the crest: a red shield, a gold mantle
        fill(img, R(r, cx - 3.5, 11, cx + 3.5, 17), GOLD)
        fill(img, R(r, cx - 2, 10, cx + 2, 18), RED)
        fill(img, R(r, cx - 1, 9, cx + 1, 10), GOLD)
        if k == 'front':
            mountain(img, r, 27, 46, 15, 9, BROWN, BROWNL)
            T(img, r, 27, 54, 'HARZGOLD', F.F57, INK, scale=2)
            T(img, r, 27, 62, 'FILTER', F.F57, GOLDD)
            T(img, r, 27, 67, 'CIGARETTEN', F.F57, GOLDD)
        else:
            T(img, r, 27, 30, 'HARZGOLD', F.F57, INK, scale=2)
            warning(img, r, 40, INK, (242, 238, 226))
            T(img, r, 27, 68, '20 FILTER-CIGARETTEN', F.F35, GOLDD)
        band(img, r, 76, 78, GOLD)
        band(img, r, 79.5, 80, GOLDD)
        wear(img, r, 21 + len(k), width=3)
        dirt(img, r, 31 + len(k), amount=0.15)
    for k in ('left', 'right'):
        r = PACK[k]
        fill(img, r, CREAM)
        grain(img, r, 41 + len(k), 5)
        band(img, r, 0, 6, GOLD)
        band(img, r, 21.5, 22, GOLDD)
        stack(img, r, 30, 'HARZGOLD', INK)
        band(img, r, 76, 78, GOLD)
        wear(img, r, 51 + len(k), width=3)
    for k, seed in (('top', 61), ('bottom', 62)):
        r = PACK[k]
        fill(img, r, GOLD if k == 'top' else CREAM)
        grain(img, r, seed, 5)
        if k == 'bottom':
            fill(img, R(r, 6, 9, 26, 12), INK)                                    # the batch stamp
            T(img, r, 36, 10.5, '0391 HZ', F.F35, INK)
        wear(img, r, seed + 10, width=3)
    cig_ends(img, PACK['inner'], (196, 140, 80))
    return img


def pack_brocken():
    img = np.zeros((PH, PW, 3), np.uint8)
    PAPER, RED, PALE, INK, BLUE = (166, 178, 188), (166, 38, 32), (228, 224, 212), (36, 46, 62), (52, 68, 96)
    for k in ('front', 'back'):
        r = PACK[k]
        fill(img, r, PAPER)
        grain(img, r, 71 + len(k), 10, 9.0)
        # Schlaegel und Eisen (the miners' hammer and pick) in a gear ring
        cx, cy = 27 * S, 18 * S
        for a in range(0, 360, 3):
            t = math.radians(a)
            tooth = (a // 15) % 2 == 0
            for q in np.arange(7.0 * S, (10.0 if tooth else 9.0) * S, 0.5):
                img[r[1] + int(round(cy + q * math.sin(t))), r[0] + int(round(cx + q * math.cos(t)))] = BLUE
        for dx in (-1, 1):                                                        # the two crossed hafts and their heads
            F.line(img, r[0] + cx - 9 * dx, r[1] + cy + 9, r[0] + cx + 7 * dx, r[1] + cy - 7, BLUE, w=2)
            fill(img, (r[0] + cx + 4 * dx - 3, r[1] + cy - 11, r[0] + cx + 4 * dx + 5, r[1] + cy - 7), BLUE)
        fill(img, R(r, 4, 32, 50, 46), RED)                                       # the red name block
        T(img, r, 27, 39, 'BROCKEN', F.F57, PALE, scale=2)
        T(img, r, 27, 52, 'OHNE FILTER', F.F57, INK)
        fill(img, R(r, 8, 56.5, 46, 57), INK)
        T(img, r, 27, 61, 'VEB TABAK HARZ', F.F57, INK)
        T(img, r, 27, 68, 'M 1,60', F.F57, INK)
        if k == 'back':
            fill(img, R(r, 4, 74, 50, 84), PALE)
            T(img, r, 27, 77, 'RAUCHEN GEFAEHRDET', F.F35, INK)
            T(img, r, 27, 81, 'DIE GESUNDHEIT', F.F35, INK)
        dirt(img, r, 81 + len(k), col=(96, 92, 80), amount=0.3)
        rng = np.random.default_rng(91 + len(k))                                  # creases of a soft pack
        for _ in range(6):
            x0_, y0_ = int(rng.integers(4, 100)), int(rng.integers(6, 170))
            F.line(img, r[0] + x0_, r[1] + y0_, r[0] + min(107, x0_ + int(rng.integers(8, 24))),
                   r[1] + min(175, max(0, y0_ + int(rng.integers(-12, 13)))), (132, 142, 152))
        wear(img, r, 101 + len(k), light=(208, 212, 214), amount=0.7, width=3)
    for k in ('left', 'right'):
        r = PACK[k]
        fill(img, r, PAPER)
        grain(img, r, 111 + len(k), 10, 9.0)
        fill(img, R(r, 3, 24, 19, 66), RED)
        stack(img, r, 28, 'BROCKEN', PALE)
        dirt(img, r, 121 + len(k), col=(96, 92, 80), amount=0.3)
        wear(img, r, 131 + len(k), light=(208, 212, 214), amount=0.7, width=3)
    for k, seed in (('top', 141), ('bottom', 142)):
        r = PACK[k]
        fill(img, r, PAPER)
        grain(img, r, seed, 10, 9.0)
        wear(img, r, seed + 10, light=(208, 212, 214), amount=0.7, width=3)
    cig_ends(img, PACK['inner'], (120, 84, 52), paper=(226, 222, 210))           # tobacco, no filter
    return img


def pack_nordlicht():
    img = np.zeros((PH, PW, 3), np.uint8)
    GREEN, DEEP, AUR0, AUR1, AUR2, CREAM, TEAL, STAR = ((28, 80, 62), (16, 50, 40), (36, 104, 80), (62, 164, 118), (150, 226, 182),
                                                         (228, 224, 202), (92, 186, 152), (236, 216, 150))
    for k in ('front', 'back'):
        r = PACK[k]
        fill(img, r, GREEN)
        grain(img, r, 151 + len(k), 4)
        band(img, r, 21.5, 22, DEEP)                                              # the lid's cut
        if k == 'front':
            # the aurora: slanted curtains, brightest at their lower hem, over a row of spruces
            for xp in range(108):
                x = xp / S
                hem = 42 - 9 * (x / 54.0) + 2.0 * math.sin(x / 4.5)
                for yp in range(int((hem - 20) * S), int(hem * S)):
                    t = (yp / S - (hem - 20)) / 20.0
                    if ((xp // 3) % 3 == 0) and t < 0.55:
                        continue
                    img[r[1] + yp, r[0] + xp] = AUR2 if t > 0.86 else AUR1 if t > 0.5 else AUR0
            for i, sx in enumerate((3, 8, 13, 18, 37, 42, 47, 51)):                # spruces on the ridge
                hh = 7 + (i * 5) % 4
                for q in range(int(hh * S)):
                    half = q / S / 3.0
                    F.rect(img, r[0] + int((sx - half) * S), r[1] + int((46 - hh) * S) + q, r[0] + int((sx + half) * S),
                           r[1] + int((46 - hh) * S) + q, DEEP)
            fill(img, R(r, 0, 45.5, 54, 47), DEEP)
            for sx, sy in ((40, 6), (47, 13), (10, 9)):                           # stars: little crosses
                fill(img, R(r, sx - 1.5, sy - 0.5, sx + 1.5, sy + 0.5), STAR)
                fill(img, R(r, sx - 0.5, sy - 1.5, sx + 0.5, sy + 1.5), STAR)
            T(img, r, 27, 55, 'NORDLICHT', F.F57, CREAM, scale=2, shadow=DEEP)
            fill(img, R(r, 6, 61, 48, 61.5), CREAM)
            T(img, r, 27, 70, 'MENTHOL', F.F57, TEAL)
            T(img, r, 27, 78, 'FILTER', F.F57, CREAM)
        else:
            T(img, r, 27, 30, 'NORDLICHT', F.F57, CREAM, scale=2, shadow=DEEP)
            warning(img, r, 40, (22, 28, 24), (228, 230, 220))
            T(img, r, 27, 70, 'MENTHOL', F.F57, TEAL)
        band(img, r, 84, 88, DEEP)
        wear(img, r, 161 + len(k), light=(164, 198, 178), width=3)
    for k in ('left', 'right'):
        r = PACK[k]
        fill(img, r, GREEN)
        grain(img, r, 171 + len(k), 4)
        band(img, r, 21.5, 22, DEEP)
        stack(img, r, 27, 'NORDLICHT', CREAM)
        band(img, r, 84, 88, DEEP)
        wear(img, r, 181 + len(k), light=(164, 198, 178), width=3)
    for k, seed in (('top', 191), ('bottom', 192)):
        r = PACK[k]
        fill(img, r, GREEN if k == 'top' else DEEP)
        grain(img, r, seed, 4)
        if k == 'top':
            for sx, sy in ((10, 6), (40, 14)):
                fill(img, R(r, sx - 0.5, sy - 0.5, sx + 0.5, sy + 0.5), STAR)
        wear(img, r, seed + 10, light=(164, 198, 178), width=3)
    cig_ends(img, PACK['inner'], (236, 236, 228))                                # white menthol filters
    return img


# ------------------------------------------------------------------ cigarette, lighter, smoke
def cig_filter(brand):
    """16 x 32: u round the filter, v from the paper joint (row 0) to the mouth end; rows 28-31 = the mouth end's cap"""
    img = np.zeros((32, 16, 3), np.uint8)
    if brand == 'Harzgold':
        img[:] = (194, 128, 64)                                                   # cork paper with darker specks
        rng = np.random.default_rng(3)
        for _ in range(36):
            img[rng.integers(0, 28), rng.integers(0, 16)] = (156, 96, 46)
        img[2:4] = (214, 180, 86)                                                 # the gold ring near the joint
        img[28:32] = (232, 224, 204)                                              # the white acetate end
    elif brand == 'Nordlicht':
        img[:] = (232, 234, 226)
        img[2:4] = (64, 150, 112)                                                 # the green ring
        img[28:32] = (240, 240, 234)
    else:                                                                         # Brocken: paper to the end, tobacco
        img[:] = (228, 224, 212)
        F.text(img, 8, 13, 'B', F.F35, (164, 36, 32))
        img[28:32] = (120, 84, 52)
    return img


def lighter_panel():
    img = np.zeros((LH, LW, 3), np.uint8)
    emi = np.zeros_like(img)
    r = LIGHTER['label']
    fill(img, r, (230, 226, 214))
    F.rect(img, r[0], r[1], r[2] - 1, r[1], (180, 176, 166))
    ptext(img, r, 15, 4.5, 'BLITZ', F.F57, (52, 30, 26))
    # the flame: a blue root, a yellow-orange body, a pale core (emission = colour)
    for key, core in (('flame', False), ('flame_core', True)):
        x0, y0, x1, y1 = LIGHTER[key]
        for y in range(y0, y1):
            t = 1 - (y - y0) / (y1 - y0 - 1)                                      # 0 at the bottom row .. 1 at the top
            c = (70, 110, 255) if t < 0.18 else (255, 236, 150) if (core and t < 0.6) else (255, 196, 70) if t < 0.55 else (255, 130, 40)
            img[y, x0:x1] = c
            emi[y, x0:x1] = c
    return img, emi


def ember():
    img = np.zeros((8, 8, 3), np.uint8)
    img[:] = (230, 70, 20)
    img[2:6, 2:6] = (255, 170, 60)
    img[0, :] = img[:, 0] = (120, 40, 20)
    return img


def smoke_puff():
    n = 16
    img = np.zeros((n, n, 4), np.uint8)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) + 0.5
    d = np.hypot(xx - n / 2, yy - n / 2) / (n / 2)
    p = np.stack([xx / 16.0, yy / 16.0, np.full_like(xx, 0.7)], -1).reshape(-1, 3)
    wob = (fbm(p, 3.0, 2, seed=5).reshape(xx.shape) - 0.5) * 0.35
    a = np.floor(np.clip(1.0 - (d + wob), 0, 1) * 4) / 4
    img[..., :3] = 255
    img[..., 3] = (a * 255).astype(np.uint8)
    return img


def build(out):
    os.makedirs(out, exist_ok=True)
    paths = {}

    def save(name, a):
        paths[name] = os.path.join(out, name + '.png')
        Image.fromarray(a).save(paths[name])

    save('T_CigPack_Harzgold', pack_harzgold())
    save('T_CigPack_Brocken', pack_brocken())
    save('T_CigPack_Nordlicht', pack_nordlicht())
    for b in BRANDS:
        save(f'T_Cig_Filter_{b}', cig_filter(b))
    lp, le = lighter_panel()
    save('T_Lighter_Panel_BaseColor', lp)
    save('T_Lighter_Panel_Emission', le)
    save('T_Cig_Ember', ember())
    save('T_Smoke_Puff', smoke_puff())
    json.dump(dict(pack=dict(size=[PW, PH], regions=PACK), lighter=dict(size=[LW, LH], regions=LIGHTER), brands=BRANDS),
              open(os.path.join(out, 'smoke_regions.json'), 'w'), indent=1)
    return paths


if __name__ == '__main__':
    print(json.dumps(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex2')), indent=1))
