"""Panel atlas of the station yard (512 x 512, pixel art, point-filtered) on the explicit-UV objects, and the alpha tiles:
  board_fuel   the signboard in front of the bund: GHS flame + DIESELKRAFTSTOFF / DIESEL FUEL, the no-smoking sign +
               RAUCHEN UND OFFENES FEUER VERBOTEN / NO SMOKING, NO NAKED FLAMES
  sign_hv      the yellow lightning triangle + HOCHSPANNUNG — LEBENSGEFAHR / HIGH VOLTAGE — DANGER OF DEATH (transformer gate,
               the pole)
  sign_noentry UNBEFUGTEN IST DER ZUTRITT VERBOTEN / NO ADMITTANCE TO UNAUTHORISED PERSONS (transformer fence)
  plate_trafo  the transformer's rating plate;  plate_tank  the tanks' name plate;  plate_pump  HAND PUMP / DIESEL
  plate_fill1/2  FILL T1 / FILL T2 over the fill couplings;  plate_ext  FEUERLÖSCHER / FIRE EXTINGUISHER
  plate_cab    LV DISTRIBUTION + the lightning arrow (the low-voltage cabinet);  plate_bolt  the pole's enamel arrow plate;
  plate_pole   POLE 14;  gauge_t1 / gauge_t2  the tanks' level dials at the fill point (35 % / 10 %);  gauge_oil  the
               conservator's oil level dial;  ghs  the small flame diamond at the fill point
German first, English under it on the signs (the project's rule); equipment labels in English.
T_Yard_ChainLink (64 x 64 RGBA): galvanised chain-link, 0.5 m per tile; T_Yard_Barbed (64 x 46 RGBA): three strands of barbed
wire, 0.5 m x 0.36 m per tile — both alpha cut-out (the checkpoint's tiles).
python3 yard_tex.py [out_dir]  ->  T_Yard_Panel_BaseColor.png / _Emission.png, T_Yard_ChainLink.png, T_Yard_Barbed.png,
yard_panel_regions.json"""
import os, sys, json, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pxfont as F
import van2_tex as VT
from noise import fbm

for _f, _src in ((F.F35, {'Ä': '#.#|.#.|#.#|###|#.#', 'Ö': '#.#|...|###|#.#|###', 'Ü': '#.#|...|#.#|#.#|###'}),
                 (F.F57, {'Ä': '.#.#.|.....|.###.|#...#|#####|#...#|#...#', 'Ö': '.#.#.|.....|.###.|#...#|#...#|#...#|.###.',
                          'Ü': '.#.#.|.....|#...#|#...#|#...#|#...#|.###.'})):
    for _k, _s in _src.items():
        _f['glyphs'][_k] = F._compile({'x': _s})['x']

N = 512
REG = {'board_fuel': (0, 0, 240, 120), 'sign_hv': (240, 0, 360, 92), 'sign_noentry': (360, 0, 512, 76),
       'plate_trafo': (0, 120, 64, 164), 'plate_tank': (64, 120, 128, 160), 'plate_pump': (128, 120, 192, 140),
       'plate_fill1': (128, 140, 176, 156), 'plate_fill2': (176, 140, 224, 156), 'plate_ext': (224, 120, 280, 176),
       'plate_cab': (280, 120, 344, 152), 'plate_bolt': (344, 120, 368, 160), 'plate_pole': (368, 120, 400, 136),
       'gauge_t1': (400, 120, 424, 144), 'gauge_t2': (424, 120, 448, 144), 'gauge_oil': (448, 120, 468, 140),
       'ghs': (468, 120, 492, 144)}
INK, WHITE = (26, 24, 22), (236, 232, 220)
RED, RED_D, YELLOW = (196, 36, 26), (130, 24, 18), (238, 190, 30)
ALU, ALU_D = (176, 178, 172), (110, 112, 108)
CHAIN_N = 64
BARB_W, BARB_H = 64, 46


def uv(name, n=N):
    return VT.uv(REG[name], n)


def _plate(img, r, col, rim=None, t=1):
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, col)
    if rim is not None:
        F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, rim, t)


def _age(img, r, seed, spots=18, amount=0.18, col=(120, 100, 70)):
    x0, y0, x1, y1 = r
    rng = np.random.default_rng(seed)
    for _ in range(spots):
        fx, fy = rng.integers(x0 + 1, x1 - 1), rng.integers(y0 + 1, y1 - 1)
        img[fy, fx] = (img[fy, fx] * (1 - amount) + np.array(col) * amount).astype(np.uint8)


def _poly_mask(H, W, pts, ox=0.0, oy=0.0):
    """pixels whose centres lie inside the polygon pts [(x, y)] (pixel units, relative to ox, oy)"""
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = xx + 0.5 + ox, yy + 0.5 + oy
    inside = np.zeros((H, W), bool)
    n = len(pts)
    for i in range(n):
        (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
        cond = (ya > py) != (yb > py)
        xint = xa + (py - ya) * (xb - xa) / np.where(yb - ya == 0, 1e-9, yb - ya)
        inside ^= cond & (px < xint)
    return inside


def fill_poly(img, pts, col):
    H, W = img.shape[:2]
    img[_poly_mask(H, W, pts)] = col


# ---------------------------------------------------------------- pictograms
def flame(img, cx, cy, s, col=INK):
    """a pixel flame (GHS02 style) of height ~s centred at cx, cy"""
    pts = [(cx - 0.30 * s, cy + 0.40 * s), (cx - 0.36 * s, cy + 0.05 * s), (cx - 0.18 * s, cy - 0.18 * s),
           (cx - 0.10 * s, cy - 0.02 * s), (cx - 0.02 * s, cy - 0.48 * s), (cx + 0.18 * s, cy - 0.12 * s),
           (cx + 0.24 * s, cy - 0.26 * s), (cx + 0.36 * s, cy + 0.06 * s), (cx + 0.30 * s, cy + 0.40 * s)]
    fill_poly(img, pts, col)
    F.rect(img, cx - 0.44 * s, cy + 0.44 * s, cx + 0.44 * s, cy + 0.50 * s, col)          # the base line


def ghs_flame(img, cx, cy, r):
    """GHS diamond: red border, white field, the black flame"""
    fill_poly(img, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], RED)
    q = r - max(2.0, r * 0.16)
    fill_poly(img, [(cx, cy - q), (cx + q, cy), (cx, cy + q), (cx - q, cy)], WHITE)
    flame(img, cx, cy + r * 0.02, q * 0.95)


def no_smoking(img, cx, cy, r):
    """prohibition sign P002: red ring and bar over a black cigarette with smoke"""
    F.disc(img, cx, cy, r, RED)
    F.disc(img, cx, cy, r * 0.76, WHITE)
    F.rect(img, cx - r * 0.55, cy + r * 0.02, cx + r * 0.42, cy + r * 0.16, INK)           # the cigarette
    F.rect(img, cx + r * 0.30, cy + r * 0.02, cx + r * 0.42, cy + r * 0.16, (210, 120, 60))
    for k in range(3):
        F.disc(img, cx + r * (0.30 + 0.06 * k), cy - r * (0.12 + 0.16 * k), max(0.8, r * 0.06), INK)
    for t in np.linspace(-0.70, 0.70, int(r * 4)):                                          # the bar, 45 deg
        F.disc(img, cx + t * r, cy + t * r, max(1.0, r * 0.11), RED)


def bolt_triangle(img, cx, cy, s):
    """W012 warning triangle: yellow, black border, the black lightning arrow (height s)"""
    h = s
    w = s * 1.12
    fill_poly(img, [(cx, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)], INK)
    k = max(2.0, s * 0.12)
    fill_poly(img, [(cx, cy - h / 2 + k * 1.6), (cx + w / 2 - k * 1.25, cy + h / 2 - k * 0.7),
                    (cx - w / 2 + k * 1.25, cy + h / 2 - k * 0.7)], YELLOW)
    bolt(img, cx, cy + h * 0.10, h * 0.50, INK)


def bolt(img, cx, cy, h, col):
    """zigzag lightning arrow pointing down, height h centred at cx, cy"""
    pts = [(cx + 0.10 * h, cy - 0.50 * h), (cx - 0.16 * h, cy + 0.04 * h), (cx + 0.02 * h, cy + 0.02 * h),
           (cx - 0.12 * h, cy + 0.38 * h), (cx - 0.20 * h, cy + 0.30 * h), (cx - 0.12 * h, cy + 0.52 * h),
           (cx + 0.10 * h, cy + 0.28 * h), (cx + 0.02 * h, cy + 0.30 * h), (cx + 0.18 * h, cy - 0.08 * h),
           (cx + 0.00 * h, cy - 0.06 * h), (cx + 0.22 * h, cy - 0.50 * h)]
    fill_poly(img, pts, col)


def extinguisher_icon(img, cx, cy, s, col=WHITE):
    """F001 fire extinguisher (white on red): the bottle with round shoulders, the valve and its lever, the hose"""
    k = s / 24.0
    F.rect(img, cx - 3 * k, cy - 3 * k, cx + 4 * k, cy + 10 * k, col)                     # the bottle
    F.rect(img, cx - 2 * k, cy - 4 * k, cx + 3 * k, cy - 3 * k, col)                      # the shoulder
    F.rect(img, cx - 1 * k, cy - 7 * k, cx + 2 * k, cy - 5 * k, col)                      # the neck
    F.rect(img, cx - 2 * k, cy - 9 * k, cx + 3 * k, cy - 8 * k, col)                      # the valve head
    F.line(img, cx + 2 * k, cy - 9.5 * k, cx + 7 * k, cy - 11 * k, col, 2)                  # the lever
    F.line(img, cx - 2 * k, cy - 8.5 * k, cx - 7 * k, cy - 6 * k, col, 2)                   # the hose ...
    F.line(img, cx - 7 * k, cy - 6 * k, cx - 7 * k, cy + 6 * k, col, 2)
    F.rect(img, cx - 8 * k, cy + 6 * k, cx - 6 * k, cy + 9 * k, col)                      # ... and its nozzle


# ---------------------------------------------------------------- signs and plates
def draw_signs(img):
    r = REG['board_fuel']                                     # white enamel board, black rule between the two halves
    _plate(img, r, WHITE, INK)
    x0, y0, x1, y1 = r
    ym = (y0 + y1) // 2
    F.rect(img, x0 + 4, ym, x1 - 5, ym, (150, 146, 138))
    ghs_flame(img, x0 + 30, y0 + 30, 22)
    tx = x0 + 60 + (x1 - x0 - 64) / 2
    F.text(img, tx, y0 + 21, 'DIESELKRAFTSTOFF', F.F57, INK)
    F.text(img, tx, y0 + 34, 'DIESEL FUEL', F.F57, (90, 86, 80))
    F.text(img, tx, y0 + 47, 'WASSERGEFÄHRDEND • WATER POLLUTANT', F.F35, (110, 104, 96))
    no_smoking(img, x0 + 30, ym + 30, 22)
    F.text(img, tx, ym + 14, 'RAUCHEN UND OFFENES', F.F57, RED)
    F.text(img, tx, ym + 25, 'FEUER VERBOTEN', F.F57, RED)
    F.text(img, tx, ym + 38, 'NO SMOKING,', F.F57, (90, 86, 80))
    F.text(img, tx, ym + 48, 'NO NAKED FLAMES', F.F57, (90, 86, 80))
    for sx in (x0 + 5, x1 - 6):
        for sy in (y0 + 5, y1 - 6):
            F.disc(img, sx + 0.5, sy + 0.5, 1.6, (150, 146, 138))
    _age(img, r, 41, 70, 0.28)
    r = REG['sign_hv']                                        # white plate: the yellow triangle, the warning in red / black
    _plate(img, r, WHITE, INK)
    x0, y0, x1, y1 = r
    cx = (x0 + x1) / 2
    bolt_triangle(img, cx, y0 + 22, 32)
    F.text(img, cx, y0 + 47, 'HOCHSPANNUNG', F.F57, INK)
    F.text(img, cx, y0 + 57, 'LEBENSGEFAHR', F.F57, RED)
    F.text(img, cx, y0 + 69, 'HIGH VOLTAGE', F.F35, (90, 86, 80))
    F.text(img, cx, y0 + 77, 'DANGER OF DEATH', F.F35, RED_D)
    _age(img, r, 42, 40, 0.25)
    r = REG['sign_noentry']
    _plate(img, r, WHITE, RED, 2)
    x0, y0, x1, y1 = r
    cx = (x0 + x1) / 2
    F.text(img, cx, y0 + 13, 'UNBEFUGTEN IST DER', F.F57, INK)
    F.text(img, cx, y0 + 24, 'ZUTRITT VERBOTEN', F.F57, INK)
    F.rect(img, x0 + 14, y0 + 33, x1 - 15, y0 + 33, (150, 146, 138))
    F.text(img, cx, y0 + 43, 'NO ADMITTANCE TO', F.F57, (90, 86, 80))
    F.text(img, cx, y0 + 54, 'UNAUTHORISED', F.F57, (90, 86, 80))
    F.text(img, cx, y0 + 64, 'PERSONS', F.F57, (90, 86, 80))
    _age(img, r, 43, 40, 0.25)


def draw_plates(img, emi):
    r = REG['plate_trafo']                                    # aluminium rating plate, engraved
    _plate(img, r, ALU, ALU_D)
    x0, y0, x1, y1 = r
    cx = (x0 + x1) / 2
    for i, (t, f) in enumerate((('TRANSFORMER', F.F35), ('250 KVA 50 HZ', F.F35), ('20000 / 400 V', F.F35),
                                ('DYN5  UK 4%', F.F35), ('OIL 380 KG', F.F35), ('NO 41187  1987', F.F35))):
        F.text(img, cx, y0 + 6 + i * 6.4, t, f, (40, 40, 38))
    _age(img, r, 44, 20, 0.3, (80, 70, 60))
    r = REG['plate_tank']
    _plate(img, r, ALU, ALU_D)
    x0, y0, x1, y1 = r
    cx = (x0 + x1) / 2
    for i, t in enumerate(('STORAGE TANK', '18 000 L', 'DIN 6616', 'DIESEL • 1979')):
        F.text(img, cx, y0 + 7 + i * 8, t, F.F35, (40, 40, 38))
    _age(img, r, 45, 26, 0.35, (110, 70, 40))
    r = REG['plate_pump']
    _plate(img, r, (232, 226, 206), INK)
    x0, y0, x1, y1 = r
    F.text(img, (x0 + x1) / 2, y0 + 7, 'HAND PUMP', F.F35, INK)
    F.text(img, (x0 + x1) / 2, y0 + 14, 'DIESEL', F.F35, RED_D)
    for key, t in (('plate_fill1', 'FILL T1'), ('plate_fill2', 'FILL T2')):
        r = REG[key]
        _plate(img, r, (232, 226, 206), INK)
        x0, y0, x1, y1 = r
        F.text(img, (x0 + x1) / 2, (y0 + y1) / 2, t, F.F35, INK)
        _age(img, r, 46 + len(key), 8, 0.3)
    r = REG['plate_ext']                                      # red square with the white extinguisher, the words under it
    _plate(img, r, WHITE, INK)
    x0, y0, x1, y1 = r
    cx = (x0 + x1) / 2
    F.rect(img, cx - 14, y0 + 3, cx + 13, y0 + 30, RED)
    extinguisher_icon(img, cx + 2, y0 + 17, 24)
    F.text(img, cx, y0 + 38, 'FEUERLÖSCHER', F.F35, INK)
    F.text(img, cx, y0 + 46, 'EXTINGUISHER', F.F35, (90, 86, 80))
    r = REG['plate_cab']                                      # grey sticker: the black arrow, LV DISTRIBUTION
    _plate(img, r, (214, 214, 206), INK)
    x0, y0, x1, y1 = r
    bolt_triangle(img, x0 + 13, (y0 + y1) / 2, 18)
    F.text(img, x0 + 40, y0 + 10, 'LV', F.F57, INK)
    F.text(img, x0 + 40, y0 + 21, 'DISTRIB.', F.F35, INK)
    r = REG['plate_bolt']                                     # white enamel plate with the red zigzag arrow
    _plate(img, r, WHITE, (150, 146, 138))
    x0, y0, x1, y1 = r
    bolt(img, (x0 + x1) / 2, (y0 + y1) / 2, 30, RED)
    _age(img, r, 47, 10, 0.3)
    r = REG['plate_pole']
    _plate(img, r, (232, 226, 206), INK)
    x0, y0, x1, y1 = r
    F.text(img, (x0 + x1) / 2, (y0 + y1) / 2, 'POLE 14', F.F35, INK)
    for key, frac, lab in (('gauge_t1', 0.35, 'T1'), ('gauge_t2', 0.10, 'T2')):
        x0, y0, x1, y1 = REG[key]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        F.rect(img, x0, y0, x1 - 1, y1 - 1, (30, 30, 30))
        F.disc(img, cx, cy, 11.0, (232, 230, 220))
        for k in range(5):
            F.tick(img, cx, cy, 8.0, 10.5, -120 + k * 60, INK)
        F.ring(img, cx, cy, 8.6, 10.4, RED, -120, -90)                                      # the reserve band
        F.text(img, cx, cy + 6, lab, F.F35, INK)
        hx, hy = F.pol(cx, cy, 8.5, -120 + 240 * frac)
        F.line(img, cx, cy, hx, hy, RED_D, 1)
        F.disc(img, cx, cy, 1.4, INK)
    x0, y0, x1, y1 = REG['gauge_oil']
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (40, 40, 40))
    F.disc(img, cx, cy, 9.0, (226, 224, 214))
    F.text(img, cx - 4, cy + 4, '-', F.F35, INK)
    F.text(img, cx + 4, cy + 4, '+', F.F35, INK)
    hx, hy = F.pol(cx, cy, 7.0, 20)
    F.line(img, cx, cy, hx, hy, INK, 1)
    x0, y0, x1, y1 = REG['ghs']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (150, 154, 150))
    ghs_flame(img, (x0 + x1) / 2, (y0 + y1) / 2, 11.5)


def chainlink(path):
    """galvanised chain-link (the checkpoint's): diamonds 8 px across, alpha 0 between the wires"""
    n = CHAIN_N
    yy, xx = np.mgrid[0:n, 0:n]
    a = np.mod(xx + yy, 8) == 0
    b = np.mod(xx - yy, 8) == 0
    wire = a | b
    knot = a & b
    knot = knot | np.roll(knot, 1, 1)
    q3 = np.stack([xx.ravel() / 9.0, yy.ravel() / 9.0, np.zeros(xx.size)], -1).astype(np.float32)
    nz = fbm(q3, 1.0, 2, seed=51).reshape(n, n)
    col = np.array((150, 156, 152), np.float64)[None, None] * (0.80 + 0.35 * nz[..., None])
    col = np.where(knot[..., None], col * 0.75, col)
    rust = (nz > 0.70)[..., None]
    col = np.where(rust & wire[..., None], col * 0.5 + np.array((120, 66, 34)) * 0.5, col)
    rgba = np.zeros((n, n, 4), np.uint8)
    rgba[..., :3] = np.clip(col, 0, 255).astype(np.uint8)
    rgba[..., 3] = np.where(wire | knot, 255, 0)
    Image.fromarray(rgba, 'RGBA').save(path)
    return path


def barbed(path):
    """barbed wire band (the checkpoint's): three twisted strands with barbs, 0.5 m x 0.36 m per tile"""
    w, h = BARB_W, BARB_H
    rgba = np.zeros((h, w, 4), np.uint8)
    col = np.array((128, 130, 126), np.uint8)
    dark = np.array((86, 84, 80), np.uint8)
    for k, rel in enumerate((0.06, 0.18, 0.30)):
        r = int(round((0.36 - rel) / 0.36 * h))
        for x in range(w):
            up = (x // 2 + k) % 2 == 0
            rgba[r - (1 if up else 0), x, :3] = col
            rgba[r - (1 if up else 0), x, 3] = 255
            rgba[r - (0 if up else 1), x, :3] = dark
            rgba[r - (0 if up else 1), x, 3] = 255
        for bx in range(4 + k * 5, w, 16):
            for dx, dy in ((-2, -2), (-1, -1), (1, 1), (2, 2), (-2, 2), (-1, 1), (1, -1), (2, -2)):
                xx, yy = (bx + dx) % w, r + dy
                if 0 <= yy < h:
                    rgba[yy, xx, :3] = col if dy < 0 else dark
                    rgba[yy, xx, 3] = 255
    rust = (np.arange(w)[None, :] * 7 + np.arange(h)[:, None] * 13) % 11 == 0
    rgba[..., :3] = np.where((rust & (rgba[..., 3] > 0))[..., None], np.array((120, 70, 40), np.uint8), rgba[..., :3])
    Image.fromarray(rgba, 'RGBA').save(path)
    return path


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (16, 16, 16)
    emi = np.zeros_like(img)
    draw_signs(img)
    draw_plates(img, emi)
    pb, pe = os.path.join(out, 'T_Yard_Panel_BaseColor.png'), os.path.join(out, 'T_Yard_Panel_Emission.png')
    Image.fromarray(img).save(pb)
    Image.fromarray(emi).save(pe)
    pc = chainlink(os.path.join(out, 'T_Yard_ChainLink.png'))
    pw = barbed(os.path.join(out, 'T_Yard_Barbed.png'))
    json.dump(dict(size=N, regions=REG, chainlink=dict(size=CHAIN_N, metres_per_tile=0.5),
                   barbed=dict(size=[BARB_W, BARB_H], metres_per_tile=[0.5, 0.36], strands_above_foot=[0.06, 0.18, 0.30])),
              open(os.path.join(out, 'yard_panel_regions.json'), 'w'), indent=1)
    return pb, pe, pc, pw


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'yard')
    print(build(out))
