"""Panel atlas and own textures of forest_gear (pixel art in the project's font, point filter). Panel (512 x 512): the
D cell's wrapper and the four-pack's sleeve, the 6 V lantern battery's wrapper and cap, the walkie-talkie's front and top
(speaker, the LCD bezel, CH / VOL scales - equipment: English), the hand lamp's plate, the lens tiles (amber, clear; their
glow in the emission map), the doll's painted face, the bulb carton, the worker's brass tag (stamped number), the
Stationsleiter key's tag. Products are printed in German (MONO, GLÜHLAMPE), as forest_items' goods. Own textures (UV 0..1):
the walkie's LCD (lit / off), the postcard's picture side and its back (the message in block capitals, signed "— K"
without the dot), the bulb's frosted glass and the burnt-out glass. Everything is invented: no real brand.
python3 gear_tex.py [out_dir] -> T_Gear_Panel_BaseColor.png / _Emission.png, the own textures, gear_panel_regions.json"""
import os, sys, json, math
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxfont as F
import van2_tex as VT
from noise import fbm

HERE = os.path.dirname(os.path.abspath(__file__))
N = 512
for _f, _src in ((F.F35, {'Ä': '#.#|.#.|#.#|###|#.#', 'Ö': '#.#|...|###|#.#|###', 'Ü': '#.#|...|#.#|#.#|###'}),
                 (F.F57, {'Ä': '.#.#.|.....|.###.|#...#|#####|#...#|#...#', 'Ö': '.#.#.|.....|.###.|#...#|#...#|#...#|.###.',
                          'Ü': '.#.#.|.....|#...#|#...#|#...#|#...#|.###.'})):
    for _k, _s in _src.items():                         # the umlauts (as kpp_tex patches them)
        _f['glyphs'][_k] = F._compile({'x': _s})['x']

INK, WHITE, CREAM = (26, 24, 22), (236, 234, 226), (232, 226, 206)
BLUE_D, BLUE, GOLD = (28, 46, 104), (40, 70, 150), (222, 172, 44)
TAG_NUMBER = '3817'                                     # the dead worker's personnel number, stamped on the brass tag
POSTCARD_MSG = ['A SMALL GIFT', 'FOR THE STATION.', 'KEEP HER WARM.']   # the back, block capitals, then the signature
POSTCARD_SIG = 'K'                                      # "— K" - no full stop (Kessler signs "— K.")

# name, width, height (px) - the size on the model in the comment (px per metre)
SIZES = [('d_band', 112, 56),            # D cell wrapper, 107 x 58 mm unrolled (~1000)
         ('pack_sleeve', 224, 32),       # the four-pack's sleeve, 255 x 36 mm unrolled (~880)
         ('b6_front', 52, 78), ('b6_side', 52, 78), ('b6_top', 40, 40),     # 4R25: 67 x 100 mm faces, the cap 65 mm
         ('walkie_front', 52, 130),      # 48 x 120 mm (~1080)
         ('walkie_top', 60, 34),         # 60 x 34 mm
         ('lamp_plate', 64, 40),         # 50 x 32 mm on both sides of the hand lamp
         ('lens_amber', 32, 32), ('lens_clear', 32, 32),
         ('doll_face', 64, 48),          # the face on the front of the head (planar: 100 x 74 mm)
         ('bulbbox_front', 52, 92), ('bulbbox_side', 52, 92), ('bulbbox_top', 52, 52),   # 64 x 112 mm, 64 x 64 mm
         ('tag_face', 72, 72), ('tag_back', 72, 72),                          # the brass tag, 32 mm (2250)
         ('key_tag', 44, 24),            # the Stationsleiter key's tag insert, 40 x 22 mm
         ('hl_plate', 40, 16),           # the headlamp's battery box lid
         ('solid_black', 8, 8), ('solid_amber', 8, 8)]


def pack(sizes, n=N, gap=2):
    """shelf packing, tallest first: name -> (x0, y0, x1, y1)"""
    out, x, y, row = {}, 0, 0, 0
    for name, w, h in sorted(sizes, key=lambda t: -t[2]):
        if x + w > n:
            x, y, row = 0, y + row + gap, 0
        out[name] = (x, y, x + w, y + h)
        x += w + gap
        row = max(row, h)
    assert y + row <= n, 'panel full'
    return out


REG = pack(SIZES)
WALKIE_FRONT = dict(lcd=(9, 52, 43, 66), speaker=(6, 8, 46, 44), mic=(26, 118))     # px in walkie_front (52 x 130)
WALKIE_TOP = dict(ch=(46, 17), vol=(28, 17), ant=(11, 17), led=(37, 29))          # px in walkie_top (60 x 34)
LCD_PX = (40, 16)
POSTCARD_PX = (512, 364)
GLASS_PX = (32, 64)


def uv(name, n=N):
    return VT.uv(REG[name], n)


def prop_mask(txt, font, scale=1):
    """proportional set (each glyph trimmed to its inked columns, 1 column apart, a space 3 columns)"""
    h = font['h']
    cols, prev = [], ' '
    for ch in txt:
        g = font['glyphs'].get(ch, font['glyphs'].get(ch.upper(), font['glyphs'][' ']))
        if ch == ' ':
            cols.append(np.zeros((h, 3), bool))
            prev = ch
            continue
        used = np.where(g.any(0))[0]
        g = g[:, used.min():used.max() + 1] if len(used) else g
        if cols and prev != ' ':
            cols.append(np.zeros((h, 1), bool))
        cols.append(g)
        prev = ch
    m = np.concatenate(cols, 1) if cols else np.zeros((h, 1), bool)
    return np.kron(m, np.ones((scale, scale), bool))


def ptext(img, cx, cy, txt, font, col, scale=1, align='c'):
    m = prop_mask(txt, font, scale)
    h, w = m.shape
    x = {'c': cx - w / 2.0, 'l': cx, 'r': cx - w}[align]
    F.blit_mask(img, m, int(math.floor(x + 0.5)), int(math.floor(cy - h / 2.0 + 0.5)), col)
    return w, h


def fill(img, r, col):
    x0, y0, x1, y1 = r
    img[y0:y1, x0:x1] = col


def grain(img, r, seed, amount=6.0, scale=7.0):
    """a little print / material unevenness inside a region"""
    x0, y0, x1, y1 = r
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    p = np.stack([xx / 64.0, yy / 64.0, np.full_like(xx, seed * 0.37)], -1).reshape(-1, 3)
    n = fbm(p, scale, 2, seed=seed).reshape(xx.shape) - 0.5
    sub = img[y0:y1, x0:x1].astype(np.float32) + n[..., None] * amount * 2
    img[y0:y1, x0:x1] = np.clip(sub, 0, 255).astype(np.uint8)


def ellipse(img, cx, cy, rx, ry, col):
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    m = ((xx - cx) / max(rx, 0.1)) ** 2 + ((yy - cy) / max(ry, 0.1)) ** 2 <= 1.0
    img[m] = col


# ---------------------------------------------------------------- batteries
def draw_cells(img):
    """D cell wrapper (u around, the print twice so it reads from both sides; top of the region = + end), the four-pack's
    sleeve (front 4 x MONO, sides 1,5 V, back ALKALI-MANGAN), the 4R25 lantern battery (6 V)"""
    x0, y0, x1, y1 = REG['d_band']
    fill(img, REG['d_band'], BLUE_D)
    F.rect(img, x0, y1 - 14, x1 - 1, y1 - 1, GOLD)                       # the gold foot band
    F.rect(img, x0, y1 - 15, x1 - 1, y1 - 15, (240, 220, 150))
    F.rect(img, x0, y0 + 3, x1 - 1, y0 + 3, (120, 140, 196))
    for k in range(2):
        cx = x0 + 28 + 56 * k
        ptext(img, cx, y0 + 15, 'MONO', F.F57, WHITE)
        ptext(img, cx, y0 + 28, '1,5 V', F.F57, GOLD)
        ptext(img, cx, y1 - 7, 'LR20', F.F35, BLUE_D)
        F.text(img, cx - 15, y0 + 8, '+', F.F35, WHITE)
        ptext(img, cx + 8, y0 + 37, 'ALKALI', F.F35, (150, 170, 220))
    grain(img, REG['d_band'], 11, 4)
    # the sleeve: front | chamfer | right | chamfer | back | chamfer | left | chamfer  (the flats 49 mm, the chamfers 15)
    x0, y0, x1, y1 = REG['pack_sleeve']
    fill(img, REG['pack_sleeve'], WHITE)
    W = x1 - x0
    flat, cham = 49.0 / 254.8 * W, 14.7 / 254.8 * W
    edges = [0.0]
    for i in range(4):
        edges += [edges[-1] + flat, edges[-1] + flat + cham]
    for i in range(4):
        a, b = x0 + edges[2 * i], x0 + edges[2 * i + 1]
        c = x0 + edges[2 * i + 2] if 2 * i + 2 < len(edges) else x1
        F.rect(img, int(a), y0, int(b) - 1, y0 + 9, BLUE_D)
        F.rect(img, int(a), y1 - 6, int(b) - 1, y1 - 1, GOLD)
        F.rect(img, int(b), y0, int(c) - 1, y1 - 1, BLUE)                  # the chamfers: blue
        mid = (a + b) / 2
        if i == 0:
            ptext(img, mid, y0 + 5, '4 x MONO', F.F35, WHITE)
            ptext(img, mid, y0 + 17, '1,5 V', F.F57, BLUE_D)
        elif i == 2:
            ptext(img, mid, y0 + 5, 'ALKALI', F.F35, WHITE)
            ptext(img, mid, y0 + 16, 'LR20', F.F35, BLUE_D)
            for j in range(18):                                            # a bar code
                if (j * 7) % 5 < 3:
                    F.rect(img, int(mid - 14 + j * 1.6), y0 + 20, int(mid - 14 + j * 1.6), y0 + 24, INK)
        else:
            ptext(img, mid, y0 + 5, 'MONO', F.F35, WHITE)
            ptext(img, mid, y0 + 17, '1,5 V', F.F35, BLUE_D)
    grain(img, REG['pack_sleeve'], 12, 3)
    # 4R25: front / back, sides, the black cap with + and - by the springs
    RED, RED_D = (196, 62, 30), (130, 36, 20)
    for key in ('b6_front', 'b6_side'):
        x0, y0, x1, y1 = REG[key]
        fill(img, REG[key], RED)
        F.rect(img, x0, y1 - 18, x1 - 1, y1 - 1, (30, 30, 32))
        F.rect(img, x0, y1 - 19, x1 - 1, y1 - 19, GOLD)
        cx = (x0 + x1) / 2
        if key == 'b6_front':
            ptext(img, cx, y0 + 16, '6 V', F.F57, WHITE, scale=2)
            ptext(img, cx, y0 + 33, '4R25', F.F57, GOLD)
            ptext(img, cx, y0 + 44, 'LATERNEN-', F.F35, WHITE)
            ptext(img, cx, y0 + 51, 'BATTERIE', F.F35, WHITE)
            ptext(img, cx, y1 - 9, 'ZINK-KOHLE', F.F35, (200, 200, 196))
        else:
            for j, (yy, t) in enumerate(((14, 'BLOCK'), (24, '6 V'), (34, '4R25'))):
                ptext(img, cx, y0 + yy, t, F.F35 if j != 1 else F.F57, WHITE)
            F.line(img, cx - 6, y0 + 44, cx + 1, y0 + 50, GOLD)             # a flash
            F.line(img, cx + 1, y0 + 50, cx - 2, y0 + 51, GOLD)
            F.line(img, cx - 2, y0 + 51, cx + 6, y0 + 58, GOLD)
            ptext(img, cx, y1 - 9, 'ZINK-KOHLE', F.F35, (200, 200, 196))
        grain(img, REG[key], 13 + len(key), 4)
    x0, y0, x1, y1 = REG['b6_top']
    fill(img, REG['b6_top'], (34, 34, 36))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (54, 54, 56))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    F.disc(img, int(cx - 10), int(cy), 4, (60, 60, 62))
    F.disc(img, int(cx + 10), int(cy), 4, (60, 60, 62))
    F.text(img, cx - 10, cy - 10, '+', F.F57, (200, 200, 196))
    F.text(img, cx + 10, cy - 10, '-', F.F57, (200, 200, 196))
    ptext(img, cx, cy + 12, '6 V', F.F35, (150, 150, 146))


# ---------------------------------------------------------------- walkie-talkie
def draw_walkie(img, emi, lcd_base, lcd_emi):
    x0, y0, x1, y1 = REG['walkie_front']
    BODY, PRINT, DARK = (36, 36, 38), (196, 198, 196), (16, 16, 18)
    fill(img, REG['walkie_front'], BODY)
    sx0, sy0, sx1, sy1 = WALKIE_FRONT['speaker']                             # the speaker grille: slots
    F.rect(img, x0 + sx0, y0 + sy0, x0 + sx1 - 1, y0 + sy1 - 1, (28, 28, 30))
    for yy in range(sy0 + 3, sy1 - 2, 3):
        F.rect(img, x0 + sx0 + 3, y0 + yy, x0 + sx1 - 4, y0 + yy, DARK)
    lx0, ly0, lx1, ly1 = WALKIE_FRONT['lcd']                                 # the LCD bezel (the LCD is its own quad)
    F.rect(img, x0 + lx0 - 2, y0 + ly0 - 2, x0 + lx1 + 1, y0 + ly1 + 1, (58, 58, 60))
    F.rect(img, x0 + lx0, y0 + ly0, x0 + lx1 - 1, y0 + ly1 - 1, (20, 24, 20))
    ptext(img, x0 + 26, y0 + 74, 'SNOW', F.F57, (230, 230, 226))
    ptext(img, x0 + 26, y0 + 83, 'HT-2  UHF', F.F35, (150, 150, 148))
    keys = [('SCAN', 9, 92), ('CALL', 29, 92), ('LAMP', 9, 103), ('LOCK', 29, 103)]
    for t, kx, ky in keys:                                                    # rubber keys
        F.rect(img, x0 + kx, y0 + ky, x0 + kx + 15, y0 + ky + 7, (24, 24, 26))
        F.rect(img, x0 + kx + 1, y0 + ky + 1, x0 + kx + 14, y0 + ky + 6, (58, 58, 62))
        ptext(img, x0 + kx + 8, y0 + ky + 3.5, t, F.F35, PRINT)
    mx, my = WALKIE_FRONT['mic']
    for dx in (-3, 0, 3):
        for dy in (-2, 1):
            img[y0 + my + dy, x0 + mx + dx] = DARK
    ptext(img, x0 + mx, y0 + my + 6, 'MIC', F.F35, (120, 120, 118))
    grain(img, REG['walkie_front'], 21, 3)
    x0, y0, x1, y1 = REG['walkie_top']
    fill(img, REG['walkie_top'], BODY)
    for key, lab, n, a0, a1, rr in (('ch', 'CH', 16, -135.0, 202.5, 8.6), ('vol', 'VOL', 9, -135.0, 135.0, 7.2)):
        cx, cy = WALKIE_TOP[key]
        for i in range(n):                                                    # the scale round the knob (0 at the back)
            a = math.radians(a0 + (a1 - a0) * i / max(n - 1, 1) - 90)
            img[int(round(y0 + cy + rr * math.sin(a))), int(round(x0 + cx + rr * math.cos(a)))] = PRINT
        ptext(img, x0 + cx, y0 + 3, lab, F.F35, PRINT)
    ptext(img, x0 + WALKIE_TOP['ant'][0], y0 + 30, 'ANT', F.F35, (140, 140, 138))
    lx, ly = WALKIE_TOP['led']
    F.rect(img, x0 + lx - 2, y0 + ly - 2, x0 + lx + 2, y0 + ly + 2, (20, 20, 22))
    ptext(img, x0 + lx + 8, y0 + ly, 'TX', F.F35, (140, 140, 138))
    # the LCD (own texture): dark segments "88" off; lit: the backlight with CH 01
    w, h = LCD_PX
    lcd_base[:] = (70, 84, 64)
    F.text(lcd_base, w / 2 + 6, h / 2 - 0.5, '88', F.F57, (60, 72, 56))
    F.text(lcd_base, 9, h / 2 - 0.5, 'CH', F.F35, (60, 72, 56))
    lcd_emi[:] = (96, 150, 70)
    F.text(lcd_emi, w / 2 + 6, h / 2 - 0.5, '01', F.F57, (8, 16, 6))
    F.text(lcd_emi, 9, h / 2 - 0.5, 'CH', F.F35, (8, 16, 6))
    F.rect(lcd_emi, w - 6, 3, w - 3, 4, (8, 16, 6))                           # a battery bar
    for key, col in (('solid_black', (20, 20, 22)), ('solid_amber', (232, 150, 34))):
        fill(img, REG[key], col)


# ---------------------------------------------------------------- lamps
def draw_lamps(img, emi):
    x0, y0, x1, y1 = REG['lamp_plate']                                       # the hand lamp's plate (black, white print)
    fill(img, REG['lamp_plate'], (30, 30, 32))
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, (120, 120, 118))
    ptext(img, (x0 + x1) / 2, y0 + 9, 'HAND LAMP', F.F35, WHITE)
    ptext(img, (x0 + x1) / 2, y0 + 19, '6 V', F.F57, (232, 170, 40))
    ptext(img, (x0 + x1) / 2, y0 + 29, 'BATTERY 4R25', F.F35, (170, 170, 166))
    for key, base, glow in (('lens_amber', (214, 132, 26), (255, 176, 60)), ('lens_clear', (206, 212, 216), (255, 250, 236))):
        x0, y0, x1, y1 = REG[key]
        cx, cy = (x0 + x1) / 2 - 0.5, (y0 + y1) / 2 - 0.5
        yy, xx = np.mgrid[y0:y1, x0:x1]
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / ((x1 - x0) / 2)
        ring = (np.floor(r * 7) % 2 == 0).astype(np.float32)                 # the Fresnel rings
        b = np.array(base, np.float32)
        c = b * (0.82 + 0.16 * ring)[..., None] * (1.0 - 0.18 * np.clip(r - 0.75, 0, 1))[..., None]
        c += (np.exp(-((xx - cx + 5) ** 2 + (yy - cy + 6) ** 2) / 10.0) * 50)[..., None]   # a highlight
        img[y0:y1, x0:x1] = np.clip(c, 0, 255).astype(np.uint8)
        g = np.array(glow, np.float32) * (0.85 + 0.15 * ring)[..., None] * (1.0 - 0.35 * np.clip(r, 0, 1) ** 3)[..., None]
        emi[y0:y1, x0:x1] = np.clip(g, 0, 255).astype(np.uint8)
    x0, y0, x1, y1 = REG['hl_plate']
    fill(img, REG['hl_plate'], (52, 54, 58))
    ptext(img, (x0 + x1) / 2, y0 + 5, 'HEAD LAMP', F.F35, (200, 200, 196))
    ptext(img, (x0 + x1) / 2, y0 + 11, '4,5 V', F.F35, (232, 170, 40))


# ---------------------------------------------------------------- the doll's face
SKIN = (238, 214, 196)


def draw_face(img):
    x0, y0, x1, y1 = REG['doll_face']
    w, h = x1 - x0, y1 - y0
    sub = np.zeros((h, w, 3), np.uint8)
    sub[:] = SKIN
    yy, xx = np.mgrid[0:h, 0:w]
    shade = np.clip(1.0 - 0.16 * (((xx - w / 2 + 0.5) / (w / 2)) ** 2) - 0.06 * np.clip((yy - h * 0.8) / (h * 0.2), 0, 1), 0, 1)
    sub[:] = np.clip(np.array(SKIN, np.float32) * shade[..., None], 0, 255).astype(np.uint8)
    for s in (-1, 1):                                                         # cheeks
        cx, cy = w / 2 + s * 0.25 * w, h * 0.62
        m = np.exp(-(((xx - cx) / 4.6) ** 2 + ((yy - cy) / 3.0) ** 2))
        sub[:] = np.clip(sub.astype(np.float32) * (1 - 0.35 * m[..., None]) + np.array((236, 140, 136)) * 0.35 * m[..., None],
                         0, 255).astype(np.uint8)
    for s in (-1, 1):                                                         # painted eyes: dark ovals, a lid line, a glint
        ex, ey = int(w / 2 + s * 0.18 * w - (1 if s > 0 else 0)), int(h * 0.44)
        ellipse(sub, ex, ey, 2.6, 3.4, (34, 26, 24))
        ellipse(sub, ex, ey + 0.5, 1.6, 2.2, (66, 44, 34))
        sub[ey - 1, ex - 1 if s < 0 else ex] = (236, 236, 230)
        F.line(sub, ex - 3, ey - 5, ex + 3, ey - 5, (110, 74, 56))           # brow
        for dx in (-3, 3):
            sub[ey - 4, ex + dx] = (70, 50, 40)                               # lashes at the corners
    mx, my = w // 2, int(h * 0.74)                                           # a small red mouth, a bow
    F.rect(sub, mx - 2, my, mx + 1, my, (176, 52, 50))
    F.rect(sub, mx - 1, my + 1, mx, my + 1, (150, 40, 40))
    sub[my - 1, mx - 2] = sub[my - 1, mx + 1] = (196, 92, 86)
    sub[int(h * 0.60), mx - 1] = (214, 176, 160)                              # the nose: two dots of shade
    sub[int(h * 0.60), mx] = (214, 176, 160)
    img[y0:y1, x0:x1] = sub


# ---------------------------------------------------------------- the bulb carton
def bulb_icon(img, cx, cy, s, col):
    """a pictogram bulb: the globe (circle), the neck, the cap lines; s = globe radius"""
    F.ring(img, cx, cy, s - 1, s, col)
    F.rect(img, cx - s // 2, cy + s - 1, cx + s // 2, cy + s + 2, col)
    for k in range(3):
        F.rect(img, cx - s // 2 + 1, cy + s + 4 + 2 * k, cx + s // 2 - 1, cy + s + 4 + 2 * k, col)
    F.rect(img, cx - 1, cy + s + 10, cx + 1, cy + s + 11, col)


def draw_bulbbox(img):
    BAND, BAND_D = (226, 186, 40), (180, 140, 30)
    for key in ('bulbbox_front', 'bulbbox_side'):
        x0, y0, x1, y1 = REG[key]
        fill(img, REG[key], (236, 232, 220))
        F.rect(img, x0, y0, x1 - 1, y0 + 7, BAND)                            # the tuck flap's crease at the top
        F.rect(img, x0, y0 + 8, x1 - 1, y0 + 8, BAND_D)
        F.rect(img, x0, y1 - 8, x1 - 1, y1 - 1, BAND)
        F.rect(img, x0, y1 - 9, x1 - 1, y1 - 9, BAND_D)
        cx = (x0 + x1) / 2
        if key == 'bulbbox_front':
            F.rect(img, x0 + 3, y0 + 12, x1 - 4, y0 + 22, (40, 60, 120))
            ptext(img, cx, y0 + 17, 'GLÜHLAMPE', F.F35, WHITE)
            bulb_icon(img, int(cx), y0 + 37, 8, (40, 60, 120))
            ptext(img, cx, y0 + 66, '60 W', F.F57, INK, scale=2)
            ptext(img, cx, y1 - 15, 'E27  230 V', F.F35, INK)
        else:
            for j, t in enumerate(('60 W', 'E27', '230 V', 'MATT', '710 LM')):
                ptext(img, cx, y0 + 17 + 10 * j, t, F.F35 if j else F.F57, INK)
            for j in range(22):                                              # bar code
                if (j * 5 + j // 3) % 4 < 2:
                    F.rect(img, int(cx - 16 + j * 1.5), y1 - 26, int(cx - 16 + j * 1.5), y1 - 16, INK)
        grain(img, REG[key], 31 + len(key), 3)
    x0, y0, x1, y1 = REG['bulbbox_top']
    fill(img, REG['bulbbox_top'], (236, 232, 220))
    F.rect(img, x0, y0, x1 - 1, y0 + 5, BAND)
    F.rect(img, int((x0 + x1) / 2) - 6, y1 - 4, int((x0 + x1) / 2) + 5, y1 - 1, (200, 196, 184))   # the thumb notch
    bulb_icon(img, (x0 + x1) // 2, y0 + 20, 7, (40, 60, 120))
    ptext(img, (x0 + x1) / 2, y0 + 41, '60 W', F.F35, INK)
    grain(img, REG['bulbbox_top'], 39, 3)


# ---------------------------------------------------------------- the brass worker tag and the key tag
def draw_tags(img):
    BRASS, BRASS_D, BRASS_L, STAMP = (184, 146, 70), (126, 96, 44), (222, 192, 118), (96, 70, 34)
    for key in ('tag_face', 'tag_back'):
        x0, y0, x1, y1 = REG[key]
        w = x1 - x0
        cx, cy = (x0 + x1) / 2 - 0.5, (y0 + y1) / 2 - 0.5
        yy, xx = np.mgrid[y0:y1, x0:x1]
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (w / 2)
        p = np.stack([xx / 30.0, yy / 30.0, np.zeros_like(xx, dtype=np.float64)], -1).reshape(-1, 3).astype(np.float32)
        n = fbm(p, 6.0, 2, seed=41 + len(key)).reshape(xx.shape)
        c = np.array(BRASS, np.float32) * (0.86 + 0.28 * n)[..., None]
        c = np.where((r > 0.86)[..., None], np.array(BRASS_D, np.float32) * 1.05, c)      # the rolled rim
        c = np.where(((r > 0.80) & (r <= 0.86))[..., None], np.array(BRASS_L, np.float32), c)
        img[y0:y1, x0:x1] = np.clip(c, 0, 255).astype(np.uint8)
        hx, hy = int(round(cx)), int(round(y0 + 0.155 * w + 0.5))
        F.disc(img, hx, hy, 4, (40, 32, 20))                                  # the hole for the ring
        F.ring(img, hx, hy, 4, 5, BRASS_L)
        if key == 'tag_face':
            ptext(img, cx + 0.5, y0 + 26, 'SNOW', F.F35, STAMP)
            m = prop_mask(TAG_NUMBER, F.F57, 2)
            X, Y = int(round(cx + 0.5 - m.shape[1] / 2)), int(round(y0 + 42 - m.shape[0] / 2))
            F.blit_mask(img, m, X + 1, Y + 1, BRASS_L)                        # stamped: a light lower edge, dark in the cut
            F.blit_mask(img, m, X, Y, STAMP)
            ptext(img, cx + 0.5, y0 + 57, 'NR.', F.F35, STAMP)
        else:
            ptext(img, cx + 0.5, y0 + 30, 'PROJEKT', F.F35, STAMP)
            ptext(img, cx + 0.5, y0 + 40, 'SNOW', F.F57, STAMP)
            ptext(img, cx + 0.5, y0 + 52, 'HOHENMOOS', F.F35, STAMP)
    x0, y0, x1, y1 = REG['key_tag']                                          # black tag, cream insert, ST.-LEITER
    fill(img, REG['key_tag'], (30, 30, 32))
    F.rect(img, x0 + 2, y0 + 4, x1 - 3, y1 - 5, (236, 230, 210))
    ptext(img, (x0 + x1) / 2, (y0 + y1) / 2 - 0.5, 'ST.-LEITER', F.F35, (178, 40, 30))


# ---------------------------------------------------------------- the postcard (own textures)
def postcard_front():
    """a winter picture: pale sky, a blue mountain ridge, a frozen lake, snowy firs either side, a small chapel on the far
    shore; WINTERGRÜSSE in red; a white border - printed, 40 colours"""
    W, H = POSTCARD_PX
    rng = np.random.default_rng(73)
    img = np.zeros((H, W, 3), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    B = 14                                                                   # the white border
    t = yy / H
    sky = np.array((120, 160, 204), np.float32) * (1 - t[..., None]) + np.array((228, 234, 240), np.float32) * t[..., None]
    img[:] = sky
    p = np.stack([xx / 200.0, np.zeros_like(xx), np.zeros_like(xx)], -1).reshape(-1, 3)
    ridge = 150 + 40 * (fbm(p, 2.0, 4, seed=7).reshape(xx.shape) - 0.5) * 2 - 30 * np.exp(-((xx - 330) / 70.0) ** 2)
    mount = yy > ridge
    snowcap = mount & (yy < ridge + 14 + 8 * np.sin(xx / 9.0))
    img[mount] = (92, 112, 150)
    img[snowcap] = (230, 236, 244)
    ridge2 = 196 + 18 * (fbm(p, 4.0, 3, seed=8).reshape(xx.shape) - 0.5) * 2
    near = yy > ridge2
    img[near] = (60, 80, 92)
    lake = (yy > 222) & (yy < 268)
    img[lake] = (176, 196, 212)
    img[lake & (np.abs(np.sin(xx / 13.0 + yy / 3.0)) > 0.97)] = (214, 226, 236)                 # ice streaks
    shore = yy >= 268
    img[shore] = (236, 240, 246)
    img[shore & (yy > 268 + 18 * np.sin(xx / 60.0) + 40)] = (214, 224, 238)                     # blue shadows in the snow
    # the chapel on the far shore (a white box, a dark roof, a small tower)
    cx0 = 300
    img[(xx > cx0) & (xx < cx0 + 26) & (yy > 206) & (yy < 222)] = (226, 222, 214)
    roof = (yy > 196) & (yy <= 206) & (np.abs(xx - cx0 - 13) < 15 - (206 - yy) * 1.2)
    img[roof] = (70, 54, 50)
    img[(xx > cx0 + 2) & (xx < cx0 + 8) & (yy > 186) & (yy < 206)] = (226, 222, 214)
    img[(xx > cx0 + 1) & (xx < cx0 + 9) & (yy > 180) & (yy <= 186)] = (70, 54, 50)
    img[(xx > cx0 + 15) & (xx < cx0 + 19) & (yy > 212) & (yy < 218)] = (210, 170, 90)           # a lit window
    # firs: stacked triangles, dark green, snow on the upper edges
    trees = [(x, b, s) for x, b, s in zip(rng.uniform(-10, 150, 9), rng.uniform(300, 350, 9), rng.uniform(70, 150, 9))]
    trees += [(x, b, s) for x, b, s in zip(rng.uniform(380, 520, 8), rng.uniform(296, 350, 8), rng.uniform(70, 150, 8))]
    trees += [(x, b, s) for x, b, s in zip(rng.uniform(150, 380, 7), rng.uniform(250, 262, 7), rng.uniform(16, 30, 7))]
    for (tx, tb, ts) in sorted(trees, key=lambda q: q[1]):
        for k in range(4):
            top = tb - ts + k * ts * 0.22
            bot = top + ts * 0.42
            half = (yy - top) / (bot - top) * ts * (0.26 + 0.06 * k)
            m = (yy > top) & (yy < bot) & (np.abs(xx - tx) < half)
            img[m] = (36, 62, 46)
            edge = m & (np.abs(xx - tx) > half - 2.5) & (yy < top + (bot - top) * 0.8)
            img[edge] = (236, 240, 246)
        img[(np.abs(xx - tx) < 2.5) & (yy > tb - ts * 0.1) & (yy < tb + 4)] = (70, 52, 40)
    img = np.clip(img + rng.normal(0, 3.0, img.shape), 0, 255)
    img[:B, :] = img[-B:, :] = img[:, :B] = img[:, -B:] = (244, 242, 236)
    out = img.astype(np.uint8)
    m = prop_mask('WINTERGRÜSSE', F.F57, 3)
    X, Y = 28, 26
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            F.blit_mask(out, m, X + dx * 2, Y + dy * 2, (248, 246, 240))
    F.blit_mask(out, m, X, Y, (186, 34, 30))
    from PIL import Image as _I
    q = _I.fromarray(out).quantize(colors=40, method=_I.Quantize.MEDIANCUT, dither=_I.Dither.NONE).convert('RGB')
    return np.asarray(q).copy()


def hand_text(img, x, y, txt, col, rng, scale=2):
    """block capitals by hand: each letter its own little offset, the line drifts"""
    cx = x
    drift = rng.uniform(-0.04, 0.04)
    for ch in txt:
        if ch == ' ':
            cx += 7 * scale
            continue
        m = prop_mask(ch, F.F57, scale)
        dy = int(round(rng.uniform(-1.0, 1.0) + drift * (cx - x)))
        F.blit_mask(img, m, int(cx), int(y + dy), col)
        cx += m.shape[1] + scale + int(rng.integers(0, 2))
    return cx


def postcard_back():
    W, H = POSTCARD_PX
    rng = np.random.default_rng(91)
    img = np.zeros((H, W, 3), np.float32)
    img[:] = CREAM
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    p = np.stack([xx / 300.0, yy / 300.0, np.zeros_like(xx)], -1).reshape(-1, 3)
    img *= (0.95 + 0.06 * fbm(p, 5.0, 3, seed=92).reshape(xx.shape))[..., None]
    out = np.clip(img + rng.normal(0, 2.0, img.shape), 0, 255).astype(np.uint8)
    GREY = (120, 116, 106)
    ptext(out, W / 2, 24, 'POSTKARTE', F.F57, GREY, scale=2)
    F.rect(out, W // 2 + 4, 52, W // 2 + 5, H - 30, GREY)                    # the divider
    sx0, sy0 = W - 88, 40                                                     # the stamp box
    for i in range(sx0, W - 22, 4):
        F.rect(out, i, sy0, i + 1, sy0, GREY)
        F.rect(out, i, sy0 + 80, i + 1, sy0 + 80, GREY)
    for j in range(sy0, sy0 + 81, 4):
        F.rect(out, sx0, j, sx0, j + 1, GREY)
        F.rect(out, W - 23, j, W - 23, j + 1, GREY)
    ptext(out, (sx0 + W - 23) / 2, sy0 + 34, 'BITTE', F.F35, GREY)
    ptext(out, (sx0 + W - 23) / 2, sy0 + 44, 'FREIMACHEN', F.F35, GREY)
    for k in range(4):                                                       # the address lines
        F.rect(out, W // 2 + 26, 178 + 40 * k, W - 26, 178 + 40 * k, GREY)
    INK_B, INK_B2 = (40, 58, 138), (58, 76, 156)
    y = 82
    for i, line in enumerate(POSTCARD_MSG):
        hand_text(out, 30 + rng.integers(0, 6), y, line, INK_B if i % 2 == 0 else INK_B2, rng)
        y += 34
    sx = 120                                                                 # the signature: a long dash and K - no dot
    F.rect(out, sx, y + 30, sx + 22, y + 31, INK_B)
    hand_text(out, sx + 32, y + 22, POSTCARD_SIG, INK_B, rng, scale=3)
    hand_text(out, W // 2 + 30, 160, 'STATION', INK_B2, rng)                 # the address: the station
    hand_text(out, W // 2 + 30, 200, 'HOHENMOOS', INK_B2, rng)
    return out


def glass(burnt=False):
    """the bulb's frosted glass (u round, v from the neck up); burnt: grey-brown smoke at the top, a dark spot"""
    w, h = GLASS_PX
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = 1.0 - yy / (h - 1)
    c = np.array((236, 234, 226), np.float32) * (0.93 + 0.07 * np.sin(np.pi * v))[..., None]
    c[..., 2] -= 4
    if burnt:
        p = np.stack([xx / 16.0, yy / 16.0, np.zeros_like(xx)], -1).reshape(-1, 3)
        n = fbm(p, 3.0, 3, seed=55).reshape(xx.shape)
        smoke = np.clip((v - 0.45) / 0.4, 0, 1) * (0.55 + 0.45 * n)
        c = c * (1 - 0.62 * smoke[..., None]) + np.array((84, 70, 58), np.float32) * 0.62 * smoke[..., None]
        spot = np.exp(-(((xx - w * 0.3) / 3.0) ** 2 + ((yy - h * 0.12) / 3.0) ** 2))
        c = c * (1 - 0.7 * spot[..., None]) + np.array((40, 34, 30), np.float32) * 0.7 * spot[..., None]
    return np.clip(c, 0, 255).astype(np.uint8)


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (24, 24, 24)
    emi = np.zeros_like(img)
    lcd_b = np.zeros((LCD_PX[1], LCD_PX[0], 3), np.uint8)
    lcd_e = np.zeros_like(lcd_b)
    draw_cells(img)
    draw_walkie(img, emi, lcd_b, lcd_e)
    draw_lamps(img, emi)
    draw_face(img)
    draw_bulbbox(img)
    draw_tags(img)
    paths = {}
    for name, a in (('Panel_BaseColor', img), ('Panel_Emission', emi), ('WalkieLCD_BaseColor', lcd_b),
                    ('WalkieLCD_Emission', lcd_e), ('PostcardFront_BaseColor', postcard_front()),
                    ('PostcardBack_BaseColor', postcard_back()), ('BulbGlass_BaseColor', glass(False)),
                    ('BulbBurnt_BaseColor', glass(True))):
        paths[name] = os.path.join(out, f'T_Gear_{name}.png')
        Image.fromarray(a).save(paths[name])
    json.dump(dict(size=N, regions=REG, walkie_front=WALKIE_FRONT, walkie_top=WALKIE_TOP, tag_number=TAG_NUMBER,
                   postcard_message=POSTCARD_MSG + ['— ' + POSTCARD_SIG]),
              open(os.path.join(out, 'gear_panel_regions.json'), 'w'), indent=1, ensure_ascii=False)
    return paths


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'gear')))
