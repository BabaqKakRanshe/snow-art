"""Panel atlas and own textures of sky_systems (Sky Island, act 2; pixel art in the project's font, point filter). Wall signs
German first, English under; equipment labels English.
Panel (512 x 512):
  altimeter   the altitude board's face (3.4 x 5.6 m): HÖHE ÜBER GRUND / HEIGHT ABOVE GROUND, a scale 0 .. 2000 m (ticks every
              100 m, numbers every 500), the red KRITISCH / CRITICAL band (0 .. 400 m), the yellow WARNUNG / WARNING band
              (400 .. 800 m), the lamp column's sockets; the marker is its own part
  chiller     the refrigeration unit's control panel: REFRIGERATION UNIT 2, suction / discharge / oil gauges, the motor's ammeter,
              RUN / FAULT lamps, START / STOP, a hand-written card
  chiller_tag the unit's maker plate (invented)
  sprayer     the dust sprayer's control box: DUST SPRAYER, FEED RATE, BLOWER, HOPPER LEVEL, the switch positions
  ballast     BALLASTABWURF / BALLAST RELEASE, LEBENSGEFAHR / DANGER plate by the lever
  ballast_box the hydraulic unit's label: HYDRAULIC UNIT, HOLD LEVER TO TILT, PRESSURE
Own textures: T_Sky_Grating (64 x 64 RGBA cut-out, tiles: UV 1 = 0.5 m - the walkways' and platforms' grating).
Everything is invented.
python3 sky_tex.py [out_dir] -> T_Sky_*.png, sky_panel_regions.json"""
import os, sys, json, math
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxfont as F
import van2_tex as VT
import gear_tex as GT
from noise import fbm

HERE = os.path.dirname(os.path.abspath(__file__))
N = 512
ptext, fill, grain = GT.ptext, GT.fill, GT.grain
INK, WHITE = (26, 24, 22), (232, 228, 214)
RED, YELLOW, GREEN = (178, 46, 34), (214, 172, 44), (40, 120, 64)
OLIVE = (71, 72, 56)
SIZES = [('altimeter', 192, 316),        # 3.4 x 5.6 m (56 px/m)
         ('chiller', 128, 160),          # 0.80 x 1.00 m (160 px/m)
         ('chiller_tag', 64, 32),        # 0.20 x 0.10 m (320 px/m)
         ('sprayer', 80, 96),            # 0.50 x 0.60 m
         ('ballast', 112, 80),           # 0.70 x 0.50 m
         ('ballast_box', 96, 56)]        # 0.60 x 0.35 m
REG = GT.pack(SIZES, n=N)
GRATING_N = 64


def uv(name, n=N):
    return VT.uv(REG[name], n)


def _age(img, r, seed, spots=40, amount=0.3, col=(110, 80, 50), dull=0.10):
    x0, y0, x1, y1 = r
    rng = np.random.default_rng(seed)
    for _ in range(spots):
        fx, fy = rng.integers(x0 + 1, x1 - 1), rng.integers(y0 + 1, y1 - 1)
        img[fy, fx] = (img[fy, fx] * (1 - amount) + np.array(col) * amount).astype(np.uint8)
    sub = img[y0:y1, x0:x1].astype(np.float32)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    p = np.stack([xx / 40.0, yy / 40.0, np.full_like(xx, seed * 0.1)], -1).reshape(-1, 3)
    d = np.clip((fbm(p, 7.0, 2, seed=seed).reshape(xx.shape) - 0.56) * 0.7, 0, dull)
    sub = sub * (1 - d[..., None]) + np.array((196, 192, 150), np.float32) * d[..., None]      # the island's yellow dust
    img[y0:y1, x0:x1] = np.clip(sub, 0, 255).astype(np.uint8)


def _gauge(img, gx, gy, r, lab, needle_a, LBL):
    F.disc(img, gx, gy, r + 2, (30, 30, 30))
    F.disc(img, gx, gy, r, (218, 212, 190))
    for a in range(0, 271, 30):
        F.tick(img, gx, gy, r - 3, r - 1, math.radians(225 - a), (30, 30, 30))
    F.tick(img, gx, gy, r * 0.65, r - 1, math.radians(225 - 230), (180, 40, 30))                 # the red end of the scale
    F.tick(img, gx, gy, 0, r - 2, math.radians(225 - needle_a), (170, 30, 20), 1)
    ptext(img, gx, gy + r + 7, lab, F.F35, LBL)


def draw_altimeter(img):
    r = REG['altimeter']
    x0, y0, x1, y1 = r
    BG, LINE = (40, 42, 38), (226, 222, 204)
    fill(img, r, BG)
    grain(img, r, 81, amount=4.0)
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (120, 116, 100), 2)
    cx = (x0 + x1) / 2
    ptext(img, cx, y0 + 12, 'HÖHE ÜBER GRUND', F.F57, LINE)
    ptext(img, cx, y0 + 23, 'HEIGHT ABOVE GROUND', F.F35, (180, 176, 160))
    F.rect(img, x0 + 8, y0 + 30, x1 - 9, y0 + 30, (120, 116, 100))
    # the scale: 0 m at the bottom (y_b), 2000 m at the top (y_t); the lamp column on its left, numbers on its right
    yt, yb = y0 + 44, y1 - 34
    sx = x0 + 78                                           # the scale's spine
    lx = x0 + 52                                           # the lamp column
    H = yb - yt
    ypx = lambda m: yb - H * m / 2000.0
    F.rect(img, sx - 1, yt, sx, yb, LINE)
    for lo, hi, col in ((0, 400, RED), (400, 800, YELLOW)):
        F.rect(img, sx + 3, int(ypx(hi)), sx + 10, int(ypx(lo)), col)
    for m in range(0, 2001, 100):
        y = int(round(ypx(m)))
        big = m % 500 == 0
        F.rect(img, sx - (12 if big else 6), y, sx, y, LINE)
        if big:
            ptext(img, sx + 32, y, f'{m}', F.F57, LINE, scale=2 if m in (0, 1000, 2000) else 1)
    ptext(img, sx + 46, int(ypx(1000)) + 14, 'M', F.F57, (180, 176, 160))
    for k in range(20):                                    # the lamp column's sockets (dark rings; the lamps are a glow part)
        y = int(round(ypx(50 + k * 100)))
        F.disc(img, lx, y, 4, (20, 20, 20))
        F.disc(img, lx, y, 2, (70, 64, 50))
    F.rect(img, x0 + 8, yb + 6, x1 - 9, yb + 6, (120, 116, 100))
    ptext(img, cx - 40, yb + 15, 'KRITISCH', F.F57, RED)
    ptext(img, cx - 40, yb + 25, 'CRITICAL', F.F35, (200, 120, 100))
    ptext(img, cx + 40, yb + 15, 'WARNUNG', F.F57, YELLOW)
    ptext(img, cx + 40, yb + 25, 'WARNING', F.F35, (210, 190, 120))
    _age(img, r, 82, 160, 0.25, dull=0.08)


def draw_chiller(img):
    r = REG['chiller']
    x0, y0, x1, y1 = r
    BODY, DARK, LBL = (72, 74, 60), (34, 36, 32), (226, 224, 206)
    fill(img, r, BODY)
    grain(img, r, 83, amount=5.0)
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (50, 52, 44))
    F.rect(img, x0 + 4, y0 + 4, x1 - 5, y0 + 15, DARK)
    ptext(img, (x0 + x1) / 2, y0 + 10, 'REFRIGERATION UNIT 2', F.F35, LBL)
    for (gx, lab, a) in ((x0 + 22, 'SUCTION', 40), (x0 + 64, 'DISCHARGE', 20), (x0 + 106, 'OIL', 10)):
        _gauge(img, gx, y0 + 38, 13, lab, a, LBL)
    _gauge(img, x0 + 32, y0 + 86, 15, 'MOTOR A', 5, LBL)
    for j, (lab, col) in enumerate((('RUN', (30, 80, 40)), ('FAULT', (110, 30, 26)))):
        ly = y0 + 74 + j * 16
        F.disc(img, x0 + 80, ly, 5, (24, 24, 24))
        F.disc(img, x0 + 80, ly, 4, col)
        ptext(img, x0 + 90, ly, lab, F.F35, LBL, align='l')
    for j, (lab, col) in enumerate((('START', (40, 110, 50)), ('STOP', (170, 40, 30)))):
        bx, by = x0 + 30 + j * 44, y0 + 126
        F.disc(img, bx, by, 9, (30, 30, 30))
        F.disc(img, bx, by, 7, col)
        ptext(img, bx, by + 15, lab, F.F35, LBL)
    cx_, cy_ = x0 + 108, y0 + 132                          # a card: hand-written dates of the last service
    F.rect(img, cx_ - 14, cy_ - 12, cx_ + 14, cy_ + 12, (220, 212, 184))
    for k, w in enumerate((20, 16, 22, 12)):
        F.rect(img, cx_ - 10, cy_ - 8 + k * 5, cx_ - 10 + w, cy_ - 8 + k * 5, (60, 60, 120))
    _age(img, r, 84, 90, 0.3)
    r = REG['chiller_tag']
    x0, y0, x1, y1 = r
    fill(img, r, (172, 160, 120))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (110, 100, 70))
    ptext(img, (x0 + x1) / 2, y0 + 8, 'TYPE KV 40-2', F.F35, INK)
    ptext(img, (x0 + x1) / 2, y0 + 16, 'NO 1974-0217', F.F35, INK)
    ptext(img, (x0 + x1) / 2, y0 + 24, '40 KW  380 V', F.F35, INK)
    _age(img, r, 85, 20, 0.3)


def draw_sprayer(img):
    r = REG['sprayer']
    x0, y0, x1, y1 = r
    BODY, DARK, LBL = (78, 80, 66), (34, 36, 32), (226, 224, 206)
    fill(img, r, BODY)
    grain(img, r, 86, amount=5.0)
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (50, 52, 44))
    F.rect(img, x0 + 3, y0 + 3, x1 - 4, y0 + 13, DARK)
    ptext(img, (x0 + x1) / 2, y0 + 8, 'DUST SPRAYER', F.F35, LBL)
    _gauge(img, x0 + 22, y0 + 32, 11, 'FEED', 0, LBL)
    _gauge(img, x0 + 58, y0 + 32, 11, 'BLOWER', 0, LBL)
    ptext(img, x0 + 6, y0 + 60, 'HOPPER LEVEL', F.F35, LBL, align='l')
    F.rect(img, x0 + 6, y0 + 66, x1 - 7, y0 + 72, (24, 24, 24))
    F.rect(img, x0 + 7, y0 + 67, x0 + 14, y0 + 71, (170, 50, 30))              # nearly empty
    for k, lab in enumerate(('OFF', 'LOW', 'HIGH')):
        ptext(img, x0 + 16 + k * 24, y0 + 84, lab, F.F35, LBL)
    F.disc(img, x0 + 16, y0 + 90 - 12, 3, (200, 200, 190))
    _age(img, r, 87, 50, 0.3, dull=0.18)


def draw_ballast(img):
    r = REG['ballast']
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, WHITE)
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, RED, 2)
    cx = (x0 + x1) / 2
    ptext(img, cx, y0 + 12, 'BALLASTABWURF', F.F57, INK)
    ptext(img, cx, y0 + 22, 'BALLAST RELEASE', F.F35, (90, 86, 80))
    F.rect(img, x0 + 10, y0 + 29, x1 - 11, y0 + 29, (150, 146, 138))
    for yy in range(y0 + 38, y0 + 61):
        t = (yy - (y0 + 38)) / 22.0
        F.rect(img, int(x0 + 34 - 12 * t), yy, int(x0 + 34 + 12 * t), yy, YELLOW)
    F.rect(img, x0 + 33, y0 + 44, x0 + 35, y0 + 53, INK)
    F.rect(img, x0 + 33, y0 + 56, x0 + 35, y0 + 57, INK)
    ptext(img, x0 + 80, y0 + 44, 'LEBENS-', F.F57, RED)
    ptext(img, x0 + 80, y0 + 53, 'GEFAHR', F.F57, RED)
    ptext(img, x0 + 80, y0 + 64, 'DANGER', F.F35, INK)
    _age(img, r, 88, 60, 0.3)
    r = REG['ballast_box']
    x0, y0, x1, y1 = r
    fill(img, r, (190, 186, 170))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, INK)
    cx = (x0 + x1) / 2
    ptext(img, cx, y0 + 9, 'HYDRAULIC UNIT', F.F35, INK)
    F.rect(img, x0 + 6, y0 + 15, x1 - 7, y0 + 15, INK)
    ptext(img, cx, y0 + 24, 'HOLD LEVER TO TILT', F.F35, RED)
    ptext(img, cx, y0 + 34, 'RELEASE TO STOP', F.F35, INK)
    ptext(img, cx, y0 + 46, 'MAX 160 BAR', F.F35, INK)
    _age(img, r, 89, 40, 0.3)


def grating():
    """64 x 64 RGBA: welded bar grating (bearing bars along v every 8 px, cross bars every 16 px), rusty steel; holes alpha 0"""
    n = GRATING_N
    yy, xx = np.mgrid[0:n, 0:n]
    bar = (xx % 8) < 2
    cross = (yy % 16) < 2
    m = bar | cross
    p = np.stack([xx / 16.0, yy / 16.0, np.full(xx.shape, 0.7)], -1).reshape(-1, 3).astype(np.float32)
    nz = fbm(p, 1.0, 3, seed=91).reshape(n, n)
    base = np.array((92, 78, 66), np.float32)
    rust = np.array((120, 62, 34), np.float32)
    c = base[None, None] * (1 - nz[..., None] * 0.6) + rust[None, None] * (nz[..., None] * 0.6)
    c = np.where(cross[..., None], c * 0.85, c)
    out = np.zeros((n, n, 4), np.uint8)
    out[..., :3] = np.clip(c, 0, 255).astype(np.uint8)
    out[..., 3] = np.where(m, 255, 0)
    out[..., :3][~m] = (40, 34, 30)
    return out


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (24, 24, 24)
    draw_altimeter(img)
    draw_chiller(img)
    draw_sprayer(img)
    draw_ballast(img)
    paths = {}
    for name, a, mode in (('Panel_BaseColor', img, 'RGB'), ('Grating_BaseColor', grating(), 'RGBA')):
        paths[name] = os.path.join(out, f'T_Sky_{name}.png')
        Image.fromarray(a, mode).save(paths[name])
    json.dump(dict(size=N, regions=REG, grating=dict(px=GRATING_N, metres_per_tile=0.5)),
              open(os.path.join(out, 'sky_panel_regions.json'), 'w'), indent=1, ensure_ascii=False)
    return paths


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'sky')))
