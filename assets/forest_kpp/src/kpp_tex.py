"""Panel atlas of the checkpoint (512 x 512, pixel art, point-filtered) on the explicit-UV objects, and the chain-link tile:
  sign_kpp    KONTROLLPUNKT / CHECKPOINT, the board on the front fascia
  sign_halt   HALT! AUSWEIS VORZEIGEN / STOP! SHOW YOUR ID, red plate under the pass window
  sign_sperr  SPERRGEBIET / RESTRICTED AREA, ZUTRITT VERBOTEN / NO ENTRY on the gate leaf
  sign_staff  NUR FÜR PERSONAL / STAFF ONLY on the booth door;  sign_keys  SCHLÜSSEL / KEYS on the key cabinet door
  keytags     the hook labels in the key cabinet (German over English): SCHRANKE, HAUPTGEB., GARAGE, GENERATOR, LEITER
  roster      DIENSTPLAN (the guards' duty roster, German, 16./17.10. by hand), phonelist  TELEFON (internal numbers)
  calendar    October (2026: the 1st is a Thursday), days 1-16 crossed out (the same days as the forester's)
  clock       the wall clock's face, stopped at 2:40 (the guard book's last line)
  radio       the radio's front: frequency window, CHANNEL / VOLUME (equipment labels in English)
  phone_dial  the rotary dial;  crt  the CCTV picture of the barrier (emission, with the power), dark glass (base)
  sign_sperr2 (v2) the solid gate leaf's plate (0.90 x 0.70 m): SPERRGEBIET / RESTRICTED AREA, ZUTRITT VERBOTEN / NO ENTRY,
              the CCTV camera pictogram with VIDEOÜBERWACHT / CCTV
  sign_volt   (v2) the yellow warning triangle with the black lightning (0.10 x 0.0875 m): the barrier cabinet, the gate drive
  keytags     (v2) the SCHRANKE tag is gone (its hook was removed): a bare slot with a pencil outline, the other four as before
  l_fluor     the fluorescent tube (cylinder UVs: v along the tube), l_bulk the bulkhead dome (the shed's)
  glow_cold / glow_warm  halo tiles for the glow cards (emission only);  firstaid  ERSTE HILFE / FIRST AID box front
German first, English under it on the wall signs (the project's rule); the guards' own papers in German.
T_Kpp_ChainLink (64 x 64 RGBA): galvanised chain-link, 0.5 m per tile, alpha cut-out; T_Kpp_Barbed (64 x 46 RGBA): three
strands of barbed wire, 0.5 m per tile along, 0.36 m high, alpha cut-out.
python3 kpp_tex.py [out_dir]  ->  T_Kpp_Panel_BaseColor.png / _Emission.png, T_Kpp_ChainLink.png, kpp_panel_regions.json"""
import os, sys, json, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pxfont as F
import van2_tex as VT
from noise import fbm

# umlauts: the dots replace the top row of the glyph (as hut_tex / cont_tex)
for _f, _src in ((F.F35, {'Ä': '#.#|.#.|#.#|###|#.#', 'Ö': '#.#|...|###|#.#|###', 'Ü': '#.#|...|#.#|#.#|###'}),
                 (F.F57, {'Ä': '.#.#.|.....|.###.|#...#|#####|#...#|#...#', 'Ö': '.#.#.|.....|.###.|#...#|#...#|#...#|.###.',
                          'Ü': '.#.#.|.....|#...#|#...#|#...#|#...#|.###.'})):
    for _k, _s in _src.items():
        _f['glyphs'][_k] = F._compile({'x': _s})['x']

N = 512
REG = {'sign_kpp': (0, 0, 288, 48), 'sign_halt': (288, 0, 480, 52), 'sign_sperr': (0, 48, 144, 144),
       'sign_staff': (144, 48, 240, 80), 'sign_keys': (240, 52, 336, 78), 'keytags': (144, 80, 364, 100),
       'roster': (0, 144, 64, 234), 'phonelist': (64, 144, 128, 229), 'calendar': (128, 144, 200, 244),
       'clock': (200, 144, 264, 208), 'radio': (264, 144, 360, 176), 'phone_dial': (360, 144, 392, 176),
       'crt': (392, 144, 456, 192), 'l_fluor': (456, 144, 488, 160), 'l_bulk': (456, 160, 488, 192),
       'glow_cold': (0, 256, 64, 320), 'glow_warm': (64, 256, 128, 320), 'firstaid': (200, 208, 248, 246),
       'sign_sperr2': (0, 320, 144, 432), 'sign_volt': (144, 320, 192, 362)}                 # v2
REG_SIZE_M = {'sign_sperr2': (0.90, 0.70), 'sign_volt': (0.10, 0.0875)}                    # v2: the quads' sizes
INK, WHITE, PAPER = (26, 24, 22), (236, 232, 220), (224, 218, 196)
RED, RED_D, YELLOW = (196, 36, 26), (130, 24, 18), (238, 190, 30)
PENCIL, BLUE_PEN = (84, 80, 92), (40, 52, 120)
CHAIN_N = 64
BARB_W, BARB_H = 64, 46                                  # barbed wire band: 0.5 m x 0.36 m


def uv(name, n=N):
    return VT.uv(REG[name], n)


def _plate(img, r, col, rim=None, t=1):
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, col)
    if rim is not None:
        F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, rim, t)


def _age(img, r, seed, spots=18, amount=0.18, col=(120, 100, 70)):
    """foxing / rust spots and a slight unevenness on a plate or paper"""
    x0, y0, x1, y1 = r
    rng = np.random.default_rng(seed)
    for _ in range(spots):
        fx, fy = rng.integers(x0 + 1, x1 - 1), rng.integers(y0 + 1, y1 - 1)
        img[fy, fx] = (img[fy, fx] * (1 - amount) + np.array(col) * amount).astype(np.uint8)


def _poly_mask(H, W, pts):
    """pixels whose centres lie inside the polygon pts [(x, y)] (pixel units)"""
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = xx + 0.5, yy + 0.5
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


def bolt(img, cx, cy, h, col):
    """zigzag lightning arrow pointing down, height h centred at cx, cy (as yard_tex)"""
    pts = [(cx + 0.10 * h, cy - 0.50 * h), (cx - 0.16 * h, cy + 0.04 * h), (cx + 0.02 * h, cy + 0.02 * h),
           (cx - 0.12 * h, cy + 0.38 * h), (cx - 0.20 * h, cy + 0.30 * h), (cx - 0.12 * h, cy + 0.52 * h),
           (cx + 0.10 * h, cy + 0.28 * h), (cx + 0.02 * h, cy + 0.30 * h), (cx + 0.18 * h, cy - 0.08 * h),
           (cx + 0.00 * h, cy - 0.06 * h), (cx + 0.22 * h, cy - 0.50 * h)]
    fill_poly(img, pts, col)


def bolt_triangle(img, cx, cy, s):
    """W012 warning triangle: yellow, black border, the black lightning arrow (height s, width 1.12 s)"""
    h, w = s, s * 1.12
    fill_poly(img, [(cx, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)], INK)
    k = max(2.0, s * 0.12)
    fill_poly(img, [(cx, cy - h / 2 + k * 1.6), (cx + w / 2 - k * 1.25, cy + h / 2 - k * 0.7),
                    (cx - w / 2 + k * 1.25, cy + h / 2 - k * 0.7)], YELLOW)
    bolt(img, cx, cy + h * 0.10, h * 0.56, INK)


def cctv_icon(img, cx, cy, s, col=INK):
    """CCTV pictogram: the camera body tilted down to the left, its hood and lens, the arm to a wall plate (size ~s)"""
    k = s / 32.0
    a = math.radians(-18)                                       # the body's axis: down toward the front (left)
    ca, sa = math.cos(a), math.sin(a)

    def P(u, v):                                                # body frame: u along the camera (front = -u), v down
        return (cx + (u * ca - v * sa) * k, cy + (u * sa + v * ca) * k)
    fill_poly(img, [P(-12, -5), P(10, -5), P(10, 5), P(-12, 5)], col)                     # the body
    fill_poly(img, [P(-16, -7), P(-11, -7), P(-11, 5), P(-16, 5)], col)                   # the hood
    fill_poly(img, [P(-14, -1), P(-12, -1), P(-12, 2), P(-14, 2)], WHITE)                 # the lens' glint
    fill_poly(img, [P(-11, -8), P(9, -8), P(9, -6), P(-11, -6)], col)                     # the sunshield
    x0, y0 = P(6, 5)
    F.line(img, x0, y0, x0 + 3 * k, y0 + 7 * k, col, 2)                                   # the arm down
    F.line(img, x0 + 3 * k, y0 + 7 * k, x0 + 12 * k, y0 + 7 * k, col, 2)                 # ... and to the wall
    F.rect(img, x0 + 12 * k, y0 + 2 * k, x0 + 14 * k, y0 + 12 * k, col)                  # the wall plate


# ---------------------------------------------------------------- signs
def draw_signs(img):
    r = REG['sign_kpp']                                       # white enamel board, black border, red rule
    _plate(img, r, WHITE, INK)
    x0, y0, x1, y1 = r
    cx = (x0 + x1) / 2
    F.text(img, cx, y0 + 15, 'KONTROLLPUNKT', F.F57, INK, scale=2)
    F.rect(img, x0 + 40, y0 + 26, x1 - 41, y0 + 27, RED)
    F.text(img, cx, y0 + 36, 'CHECKPOINT', F.F57, (70, 66, 60))
    for sx in (x0 + 6, x1 - 7):
        for sy in (y0 + 6, y1 - 7):
            F.disc(img, sx + 0.5, sy + 0.5, 1.6, (150, 146, 138))
    _age(img, r, 31, 40, 0.25)
    r = REG['sign_halt']                                      # red plate, white letters and border
    _plate(img, r, RED, WHITE)
    x0, y0, x1, y1 = r
    cx = (x0 + x1) / 2
    F.text(img, cx, y0 + 11, 'HALT!', F.F57, WHITE, scale=2)
    F.text(img, cx, y0 + 25, 'AUSWEIS VORZEIGEN', F.F57, WHITE)
    F.rect(img, x0 + 30, y0 + 32, x1 - 31, y0 + 32, (236, 170, 160))
    F.text(img, cx, y0 + 39, 'STOP! SHOW YOUR ID', F.F57, (246, 220, 214))
    _age(img, r, 32, 30, 0.3, (90, 40, 30))
    r = REG['sign_sperr']                                     # white plate, red border; red title
    _plate(img, r, WHITE, RED, 2)
    x0, y0, x1, y1 = r
    cx = (x0 + x1) / 2
    F.text(img, cx, y0 + 15, 'SPERRGEBIET', F.F57, RED, scale=2)
    F.text(img, cx, y0 + 28, 'RESTRICTED AREA', F.F57, INK)
    F.rect(img, x0 + 12, y0 + 37, x1 - 13, y0 + 37, (150, 146, 138))
    F.text(img, cx, y0 + 49, 'ZUTRITT VERBOTEN', F.F57, INK)
    F.text(img, cx, y0 + 59, 'NO ENTRY', F.F57, INK)
    F.rect(img, x0 + 12, y0 + 68, x1 - 13, y0 + 68, (150, 146, 138))
    F.text(img, cx, y0 + 77, 'VIDEOÜBERWACHT', F.F35, RED_D)
    F.text(img, cx, y0 + 85, 'CCTV IN OPERATION', F.F35, (90, 86, 80))
    _age(img, r, 34, 60, 0.3, (110, 70, 40))
    r = REG['sign_staff']
    _plate(img, r, WHITE, INK)
    x0, y0, x1, y1 = r
    F.text(img, (x0 + x1) / 2, y0 + 11, 'NUR FÜR PERSONAL', F.F35, INK)
    F.text(img, (x0 + x1) / 2, y0 + 21, 'STAFF ONLY', F.F35, (90, 86, 80))
    r = REG['sign_keys']                                      # a printed label stuck on the cream door
    _plate(img, r, (232, 226, 206), INK)
    x0, y0, x1, y1 = r
    F.text(img, (x0 + x1) / 2, y0 + 9, 'SCHLÜSSEL', F.F57, INK)
    F.text(img, (x0 + x1) / 2, y0 + 19, 'KEYS', F.F35, (90, 86, 80))
    draw_signs_v2(img)


def draw_signs_v2(img):
    r = REG['sign_sperr2']                                    # the solid gate leaf: white enamel, red border
    _plate(img, r, WHITE, RED, 2)
    x0, y0, x1, y1 = r
    cx = (x0 + x1) / 2
    F.text(img, cx, y0 + 15, 'SPERRGEBIET', F.F57, RED, scale=2)
    F.text(img, cx, y0 + 29, 'RESTRICTED AREA', F.F57, INK)
    F.rect(img, x0 + 12, y0 + 37, x1 - 13, y0 + 37, (150, 146, 138))
    F.text(img, cx, y0 + 46, 'ZUTRITT VERBOTEN', F.F57, INK)
    F.text(img, cx, y0 + 56, 'NO ENTRY', F.F57, (90, 86, 80))
    F.rect(img, x0 + 12, y0 + 65, x1 - 13, y0 + 65, (150, 146, 138))
    F.rect(img, x0 + 8, y0 + 71, x0 + 44, y0 + 104, (236, 232, 220))
    F.frame(img, x0 + 8, y0 + 71, x0 + 44, y0 + 104, INK)
    cctv_icon(img, x0 + 25, y0 + 85, 30)
    tx = x0 + 52 + (x1 - x0 - 58) / 2
    F.text(img, tx, y0 + 80, 'VIDEOÜBERWACHT', F.F57, RED_D)
    F.text(img, tx, y0 + 92, 'CCTV', F.F57, INK)
    F.text(img, tx, y0 + 101, 'IN OPERATION', F.F35, (90, 86, 80))
    for sx in (x0 + 6, x1 - 7):
        for sy in (y0 + 6, y1 - 7):
            F.disc(img, sx + 0.5, sy + 0.5, 1.6, (150, 146, 138))
    _age(img, r, 35, 70, 0.3, (110, 70, 40))
    r = REG['sign_volt']                                      # the triangle on a white label (the sticker's backing)
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (232, 228, 214))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (176, 172, 160))
    bolt_triangle(img, (x0 + x1) / 2, (y0 + y1) / 2 + 0.5, 36)
    _age(img, r, 36, 12, 0.25)


def draw_keytags(img):
    r = REG['keytags']
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (196, 188, 158))
    cells = [(None, None), ('HAUPTGEB.', 'MAIN BLDG'), ('GARAGE', 'GARAGE'), ('GENERATOR', 'GENERATOR'),
             ('LEITER', 'DIRECTOR')]                         # v2: the SCHRANKE hook and its tag are gone
    w = (x1 - x0) / len(cells)
    for i, (de, en) in enumerate(cells):
        a = x0 + i * w
        if de is None:                                        # a bare slot: the pencil outline the tag left, two pin holes
            F.frame(img, a + 2, y0 + 2, a + w - 3, y1 - 3, (172, 164, 136))
            for px_ in (a + 4, a + w - 5):
                F.rect(img, px_, y0 + 4, px_, y0 + 4, (120, 112, 92))
            continue
        F.rect(img, a + 1, y0 + 1, a + w - 2, y1 - 2, (238, 234, 220))
        F.frame(img, a + 1, y0 + 1, a + w - 2, y1 - 2, (120, 112, 96))
        F.text(img, a + w / 2, y0 + 6, de, F.F35, INK)
        F.text(img, a + w / 2, y0 + 13, en, F.F35, (100, 96, 90))


def draw_firstaid(img):
    r = REG['firstaid']                                       # white box, the green square with the white cross
    x0, y0, x1, y1 = r
    _plate(img, r, (232, 232, 226), (150, 150, 146))
    cx = (x0 + x1) / 2
    F.rect(img, cx - 9, y0 + 3, cx + 8, y0 + 20, (0, 132, 72))
    F.rect(img, cx - 2, y0 + 6, cx + 1, y0 + 17, (240, 240, 236))
    F.rect(img, cx - 6, y0 + 10, cx + 5, y0 + 13, (240, 240, 236))
    F.text(img, cx, y0 + 26, 'ERSTE HILFE', F.F35, INK)
    F.text(img, cx, y0 + 33, 'FIRST AID', F.F35, (90, 86, 80))
    _age(img, r, 43, 10)


# ---------------------------------------------------------------- the guards' papers
def _hand(img, x, y, txt, col=BLUE_PEN):
    F.text(img, x, y, txt, F.F35, col, align='l', valign='t')


def draw_papers(img):
    r = REG['roster']
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, PAPER)
    F.text(img, (x0 + x1) / 2, y0 + 5, 'DIENSTPLAN', F.F35, INK)
    F.text(img, (x0 + x1) / 2, y0 + 11, 'WACHE KPP', F.F35, (110, 104, 92))
    for k in range(y0 + 16, y1 - 3, 8):
        F.rect(img, x0 + 2, k, x1 - 3, k, (176, 186, 196))
    F.rect(img, x0 + 24, y0 + 16, x0 + 24, y1 - 4, (200, 120, 110))
    rows = [('12.10', 'BECKER'), ('13.10', 'WOLF'), ('14.10', 'BECKER'), ('15.10', 'KRAUSE'), ('16.10', 'WOLF'),
            ('17.10', 'WOLF'), ('18.10', 'KRAUSE'), ('19.10', 'BECKER'), ('20.10', '')]
    for i, (dte, who) in enumerate(rows):
        y = y0 + 18 + i * 8
        F.text(img, x0 + 3, y, dte, F.F35, INK, align='l', valign='t')
        _hand(img, x0 + 27, y, who)
    for i in (6, 7):                                          # the shifts after the 17th: struck out in red
        F.line(img, x0 + 26, y0 + 18 + i * 8 + 2, x1 - 4, y0 + 18 + i * 8 + 2, RED, 1)
    _age(img, r, 41, 20)
    r = REG['phonelist']
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (230, 226, 210))
    F.text(img, (x0 + x1) / 2, y0 + 5, 'TELEFON', F.F57, INK)
    F.rect(img, x0 + 4, y0 + 10, x1 - 5, y0 + 10, INK)
    for i, (who, num) in enumerate((('LEITUNG', '101'), ('LEITSTAND', '110'), ('MESSRAUM', '114'), ('FUNK', '120'),
                                    ('GARAGE', '140'), ('FEUERWEHR', '112'), ('ARZT', '0-2231'))):
        y = y0 + 15 + i * 8
        F.text(img, x0 + 3, y, who, F.F35, INK, align='l', valign='t')
        F.text(img, x1 - 3, y, num, F.F35, INK, align='r', valign='t')
    _hand(img, x0 + 3, y0 + 15 + 7 * 8 + 1, 'KOMMT NICHT', RED_D)                      # under ARZT, in pen
    _age(img, r, 42, 16)
    # calendar: October 2026, a picture of the station's dish at dusk
    r = REG['calendar']
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (232, 228, 214))
    py1 = y0 + 40
    yy, xx = np.mgrid[y0 + 2:py1, x0 + 2:x1 - 2]
    tt = (yy - y0) / 40.0
    sky = np.array((214, 160, 110))[None, None] * (1 - tt[..., None]) + np.array((84, 80, 112))[None, None] * tt[..., None]
    t = VT.BAYER[np.mod(yy, 4), np.mod(xx, 4)]
    img[y0 + 2:py1, x0 + 2:x1 - 2] = np.clip(np.floor(sky / 24 + t[..., None]) * 24, 0, 255).astype(np.uint8)
    F.rect(img, x0 + 2, py1 - 6, x1 - 3, py1 - 1, (36, 46, 38))
    rng = np.random.default_rng(12)
    for k in range(x0 + 2, x1 - 2, 3):
        h = int(6 + rng.integers(0, 10))
        for j in range(h):
            F.rect(img, k - j * 0.22, py1 - 6 - h + j, k + j * 0.22, py1 - 6 - h + j, (30, 40, 34))
    dx, dy = x0 + 46, py1 - 12                                # the dish
    F.ring(img, dx, dy - 6, 7, 9, (200, 200, 196), 200, 340)
    F.line(img, dx, dy - 6, dx, dy + 6, (200, 200, 196))
    F.rect(img, dx - 3, dy + 5, dx + 3, dy + 6, (200, 200, 196))
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, py1, (150, 140, 120))
    F.text(img, (x0 + x1) / 2, py1 + 6, 'OKTOBER', F.F57, (150, 30, 24))
    cw = (x1 - x0 - 2) / 7.0
    gy0 = py1 + 13
    for i, d in enumerate(['MO', 'DI', 'MI', 'DO', 'FR', 'SA', 'SO']):
        F.text(img, x0 + 1 + cw * (i + 0.5), gy0, d, F.F35, (150, 30, 24) if i == 6 else INK)
    first = 3                                                 # 1 October 2026 is a Thursday
    for day in range(1, 32):
        cell = first + day - 1
        row, colm = cell // 7, cell % 7
        cx = x0 + 1 + cw * (colm + 0.5)
        cy = gy0 + 8 + row * 8
        F.text(img, cx, cy, str(day), F.F35, (150, 30, 24) if colm == 6 else INK)
        if day <= 16:
            F.line(img, cx - 4, cy - 3, cx + 4, cy + 3, PENCIL)
            F.line(img, cx + 4, cy - 3, cx - 4, cy + 3, PENCIL)
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (170, 160, 140))


# ---------------------------------------------------------------- clock, radio, dial, CCTV
def draw_devices(img, emi):
    r = REG['clock']
    x0, y0, x1, y1 = r
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    R = (x1 - x0) / 2
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (20, 20, 20))
    F.disc(img, cx, cy, R - 0.5, (230, 228, 220))
    for h in range(12):
        F.tick(img, cx, cy, R - 7 if h % 3 else R - 9, R - 3, h * 30, INK, 2 if h % 3 == 0 else 1)
    for m in range(60):
        if m % 5:
            F.tick(img, cx, cy, R - 4, R - 3, m * 6, (90, 88, 84))
    F.text(img, cx, cy + 9, 'BAHN', F.F35, (120, 116, 108))
    hx, hy = F.pol(cx, cy, R * 0.50, (2 + 40 / 60) * 30)     # 2:40
    F.line(img, cx, cy, hx, hy, INK, 2)
    mx, my = F.pol(cx, cy, R * 0.80, 40 * 6)
    F.line(img, cx, cy, mx, my, INK, 2)
    sx, sy = F.pol(cx, cy, R * 0.84, 37 * 6)
    F.line(img, cx, cy, sx, sy, (196, 30, 24), 1)
    F.disc(img, cx, cy, 2.0, INK)
    r = REG['radio']                                          # olive front: the frequency window, labels by the knobs
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (84, 92, 66))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (54, 60, 42))
    wx0, wx1 = x0 + 26, x1 - 26
    F.rect(img, wx0, y0 + 4, wx1, y0 + 13, (24, 26, 20))
    for i, k in enumerate(range(wx0 + 2, wx1 - 1, 3)):
        F.rect(img, k, y0 + 11 - (2 if i % 5 == 0 else 1), k, y0 + 12, (200, 190, 140))
    F.rect(img, wx0 + 17, y0 + 5, wx0 + 17, y0 + 12, (220, 60, 40))
    F.text(img, x0 + 3, y0 + 3, 'FUG 7', F.F35, (220, 214, 180), align='l', valign='t')
    F.text(img, x0 + 18, y0 + 21, 'CHANNEL', F.F35, (220, 214, 180), align='l')
    F.text(img, x1 - 18, y0 + 21, 'VOLUME', F.F35, (220, 214, 180), align='r')
    F.disc(img, x1 - 8, y0 + 7, 1.5, (60, 20, 16))
    F.disc(emi, x1 - 8, y0 + 7, 1.5, (255, 60, 40))
    r = REG['phone_dial']                                     # rotary dial: cream face, ten finger holes, the stop
    x0, y0, x1, y1 = r
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (176, 84, 38))
    F.disc(img, cx, cy, 15.5, (206, 100, 46))
    for i in range(10):
        hx, hy = F.pol(cx, cy, 11.0, 30 + i * 28)
        F.disc(img, hx, hy, 2.6, (238, 232, 214))
        F.disc(img, hx, hy, 1.0, (40, 36, 30))
    F.disc(img, cx, cy, 5.5, (238, 232, 214))
    F.text(img, cx, cy, '110', F.F35, INK)
    sx, sy = F.pol(cx, cy, 14.5, 320)
    F.line(img, sx, sy, cx + (sx - cx) * 0.7, cy + (sy - cy) * 0.7, (200, 200, 196), 1)
    r = REG['crt']                                            # base: dark glass; emission: the gate camera
    x0, y0, x1, y1 = r
    W, H = x1 - x0, y1 - y0
    yy, xx = np.mgrid[0:H, 0:W]
    vig = 1 - 0.55 * (((xx + 0.5) / W - 0.5) ** 2 * 2.4 + ((yy + 0.5) / H - 0.5) ** 2 * 2.4)
    base = np.stack([24 + 10 * vig, 30 + 12 * vig, 28 + 10 * vig], -1)
    base[(xx > W * 0.62) & (xx < W * 0.80) & (yy < H * 0.4) & (yy > 2)] += 26          # a window's reflection
    img[y0:y1, x0:x1] = np.clip(base, 0, 255).astype(np.uint8)
    pic = np.zeros((H, W), np.float64)
    hor = int(H * 0.46)
    pic[:hor] = 0.20 + 0.05 * (yy[:hor] / hor)                 # sky
    pic[hor:] = 0.34
    road = np.abs((xx + 0.5) - (W * 0.55 + (yy - hor) * 0.55)) < (4 + (yy - hor) * 0.9)
    pic[(yy >= hor) & road] = 0.52
    rng = np.random.default_rng(13)
    for k in range(0, W, 3):                                  # forest edge
        h = int(6 + rng.integers(0, 8))
        pic[max(0, hor - h):hor, k:k + 2] = 0.10
    by = hor + 11                                             # the barrier: striped boom, post, rest post
    for k in range(int(W * 0.22), int(W * 0.78)):
        pic[by:by + 2, k] = 0.85 if ((k // 4) % 2) else 0.38
    pic[by - 6:by + 9, int(W * 0.20):int(W * 0.24)] = 0.70
    pic[by:by + 9, int(W * 0.78):int(W * 0.79)] = 0.62
    noise = rng.random((H, W)) * 0.10
    scan = np.where(yy % 2 == 0, 1.0, 0.72)
    pic = np.clip((pic + noise) * scan * vig, 0, 1)
    e = np.stack([pic * 170, pic * 220, pic * 190], -1)
    F.text(e, 3, 3, 'CAM 1', F.F35, (220, 240, 220), align='l', valign='t')
    F.text(e, W - 3, H - 8, '02:40', F.F35, (220, 240, 220), align='r', valign='t')
    emi[y0:y1, x0:x1] = np.clip(e, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- lenses and glows
def draw_lenses(img, emi):
    x0, y0, x1, y1 = REG['l_fluor']                           # v along the tube: dark electrode ends, a cool even middle
    w = x1 - x0
    for i in range(y1 - y0):
        v = 1.0 - (i + 0.5) / (y1 - y0)
        endd = min(v, 1 - v)
        dark = 1.0 - 0.75 * math.exp(-(endd / 0.035) ** 2)
        e = np.array((214, 236, 244)) * dark
        b = np.array((200, 204, 200)) * (0.72 + 0.28 * dark)
        emi[y0 + i, x0:x1] = np.clip(e, 0, 255).astype(np.uint8)
        img[y0 + i, x0:x1] = np.clip(b, 0, 255).astype(np.uint8)
    x0, y0, x1, y1 = REG['l_bulk']                            # the shed's bulkhead dome (warm), the cage in front
    yy, xx = np.mgrid[y0:y1, x0:x1]
    rr = np.hypot(xx + 0.5 - (x0 + x1) / 2, yy + 0.5 - (y0 + y1) / 2) / ((x1 - x0) / 2)
    b = np.clip(1.0 - 0.55 * rr, 0, 1)
    t = VT.BAYER[np.mod(yy, 4), np.mod(xx, 4)]
    q = np.floor(b * 7 + t) / 7
    tile = (q[..., None] * np.array((230, 224, 200))[None, None]).astype(np.uint8)
    img[y0:y1, x0:x1] = (tile * 0.55).astype(np.uint8)
    emi[y0:y1, x0:x1] = tile
    for k in range(x0 + 7, x1, 8):
        img[y0:y1, k] = (40, 40, 40)
        emi[y0:y1, k] = (60, 58, 50)
    for key, col in (('glow_cold', (200, 230, 255)), ('glow_warm', (255, 190, 110))):
        x0, y0, x1, y1 = REG[key]
        yy, xx = np.mgrid[y0:y1, x0:x1]
        rr = np.hypot(xx + 0.5 - (x0 + x1) / 2, yy + 0.5 - (y0 + y1) / 2) / ((x1 - x0) / 2)
        g = np.clip(1 - rr, 0, 1) ** 1.6
        t = VT.BAYER[np.mod(yy, 4), np.mod(xx, 4)]
        g = np.floor(g * 10 + t) / 10
        g[rr > 0.97] = 0
        emi[y0:y1, x0:x1] = (g[..., None] * np.array(col)[None, None]).astype(np.uint8)
        img[y0:y1, x0:x1] = 0


def chainlink(path):
    """galvanised chain-link: diamonds 8 px across (6 cm at 0.5 m per 64 px), 1 px wires with a 2 px knuckle where they
    cross, a little rust; alpha 0 between the wires"""
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
    """barbed wire band: three twisted strands with barbs every 0.125 m, 0.5 m x 0.36 m per tile (64 x 46 px), alpha
    cut-out; strands 0.06, 0.18, 0.30 m above the band's foot"""
    w, h = BARB_W, BARB_H
    rgba = np.zeros((h, w, 4), np.uint8)
    col = np.array((128, 130, 126), np.uint8)
    dark = np.array((86, 84, 80), np.uint8)
    for k, rel in enumerate((0.06, 0.18, 0.30)):
        r = int(round((0.36 - rel) / 0.36 * h))
        for x in range(w):
            up = (x // 2 + k) % 2 == 0                         # the twist: the two wires swap every 2 px
            rgba[r - (1 if up else 0), x, :3] = col
            rgba[r - (1 if up else 0), x, 3] = 255
            rgba[r - (0 if up else 1), x, :3] = dark
            rgba[r - (0 if up else 1), x, 3] = 255
        for bx in range(4 + k * 5, w, 16):                     # barbs: a small X across the strand
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
    draw_keytags(img)
    draw_firstaid(img)
    draw_papers(img)
    draw_devices(img, emi)
    draw_lenses(img, emi)
    pb, pe = os.path.join(out, 'T_Kpp_Panel_BaseColor.png'), os.path.join(out, 'T_Kpp_Panel_Emission.png')
    Image.fromarray(img).save(pb)
    Image.fromarray(emi).save(pe)
    pc = chainlink(os.path.join(out, 'T_Kpp_ChainLink.png'))
    pw = barbed(os.path.join(out, 'T_Kpp_Barbed.png'))
    json.dump(dict(size=N, regions=REG, sizes_m=REG_SIZE_M, chainlink=dict(size=CHAIN_N, metres_per_tile=0.5),
                   barbed=dict(size=[BARB_W, BARB_H], metres_per_tile=[0.5, 0.36], strands_above_foot=[0.06, 0.18, 0.30])),
              open(os.path.join(out, 'kpp_panel_regions.json'), 'w'), indent=1)
    return pb, pe, pc, pw


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'kpp')
    print(build(out))
