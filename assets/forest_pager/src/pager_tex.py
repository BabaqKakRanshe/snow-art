"""Panel atlas and the LCD texture of forest_pager (pixel art in the project's font, point filter; adapted from forest_gear's
gear_tex). Panel (128 x 128): the pager's front (the bezel round the LCD, the three key labels, the maker's line - equipment:
English, as the walkie), the right side's inventory sticker (the station's asset tag: German first, then English), the top
(the LED window, BEEP / VIB). Own texture (UV 0..1): the LCD - 20 x 4 characters of 5 x 7 dots, as a 1994 alphanumeric pager:
off (blank, the dots faintly visible) and lit (green backlight, a message list the game replaces with its own text).
Everything is invented: no real brand.
python3 pager_tex.py [out_dir] -> T_Pager_Panel_BaseColor.png / _Emission.png, T_Pager_LCD_BaseColor.png / _Emission.png,
pager_panel_regions.json"""
import os, sys, json, math
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxfont as F
import van2_tex as VT
from noise import fbm

HERE = os.path.dirname(os.path.abspath(__file__))
N = 128
ASSET_TAG = '4471'                                      # the station's inventory number on the side sticker

# name, width, height (px) - the size on the model in the comment
SIZES = [('pager_front', 78, 56),       # 78 x 56 mm (1000 px / m, as the walkie's front)
         ('pager_side', 22, 56),        # the right side, 22 x 56 mm: the asset sticker
         ('pager_top', 78, 22),         # the top, 78 x 22 mm
         ('key_up', 14, 10), ('key_read', 14, 10), ('key_down', 14, 10),   # the keys' faces, 14 x 10 mm
         ('solid_black', 8, 8)]


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
# px in pager_front (78 x 56, y down): the LCD window, the three keys (centre, half size), the LED, the maker's line
# 1.2 (27.10, reference «brick refined»): wider keys with their signs on them, the LED beside the maker line
FRONT = dict(lcd=(10, 6, 68, 25), keys=[(22, 43), (39, 43), (56, 43)], key_half=(7, 5), led=(66, 31), maker=(36, 31))
LCD_COLS, LCD_ROWS = 20, 4
LCD_PX = (LCD_COLS * 6 + 4, LCD_ROWS * 9 + 4)          # 124 x 40: 5 x 7 dots, 1 px apart, rows 2 px apart, 2 px margin
LCD_LIST = ['3 MSG  •1', '>17:30 K. STATION', ' 16:02 K. SHIFT 3', ' 14:47 TEST 4471']


def uv(name, n=N):
    return VT.uv(REG[name], n)


def prop_mask(txt, font, scale=1):
    """proportional set (each glyph trimmed to its inked columns, 1 column apart, a space 3 columns)"""
    h = font['h']
    cols = []
    for ch in txt:
        g = font['glyphs'].get(ch, font['glyphs'].get(ch.upper(), font['glyphs'][' ']))
        if ch == ' ':
            cols.append(np.zeros((h, 3), bool))
            continue
        used = np.where(g.any(0))[0]
        if len(used):
            g = g[:, used[0]:used[-1] + 1]
        cols.append(g)
        cols.append(np.zeros((h, 1), bool))
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


def mono(img, x, y, txt, col):
    """fixed 6-px cells of the 5 x 7 font (the LCD's character grid), x / y = the cell's top left"""
    for i, ch in enumerate(txt):
        if ch == ' ':
            continue
        if ch == '|':                                    # a signal bar: rising heights
            continue
        g = F.F57['glyphs'].get(ch, F.F57['glyphs'].get(ch.upper(), F.F57['glyphs'][' ']))
        F.blit_mask(img, g, x + i * 6, y, col)


def draw_front(img):
    x0, y0, x1, y1 = REG['pager_front']
    BODY, PRINT, DARK = (46, 46, 50), (206, 208, 204), (14, 14, 16)
    fill(img, REG['pager_front'], BODY)
    lx0, ly0, lx1, ly1 = FRONT['lcd']                                          # the bezel (the LCD is its own quad)
    F.rect(img, x0 + lx0 - 3, y0 + ly0 - 3, x0 + lx1 + 2, y0 + ly1 + 2, (24, 24, 26))
    F.rect(img, x0 + lx0 - 1, y0 + ly0 - 1, x0 + lx1, y0 + ly1, DARK)
    ptext(img, x0 + FRONT['maker'][0], y0 + FRONT['maker'][1], 'SNOW  PG-4', F.F35, PRINT)
    hx, hy = FRONT['key_half']
    for i, (kx, ky) in enumerate(FRONT['keys']):                               # the key wells and their signs under them
        ax, ay, bx, by = x0 + kx - hx - 2, y0 + ky - hy - 1, x0 + kx + hx + 1, y0 + ky + hy   # 1.2: oval wells as the reference
        for r in range(3):                                                     # the rows narrow by 3, 2, 1 px at the ends
            cut = (3, 1, 0)[r]
            F.rect(img, ax + cut, ay + r, bx - cut, ay + r, DARK)
            F.rect(img, ax + cut, by - r, bx - cut, by - r, DARK)
        F.rect(img, ax, ay + 3, bx, by - 3, DARK)
    # the signs are on the keys themselves now (draw_keys)
    lx, ly = FRONT['led']
    F.rect(img, x0 + lx - 2, y0 + ly - 2, x0 + lx + 1, y0 + ly + 1, DARK)
    grain(img, REG['pager_front'], 31, 3)


def draw_side(img):
    """the station's inventory sticker on the right side: a cream label, worn at the corners"""
    x0, y0, x1, y1 = REG['pager_side']
    fill(img, REG['pager_side'], (46, 46, 50))
    sx0, sy0, sx1, sy1 = x0 + 3, y0 + 12, x1 - 3, y0 + 44
    F.rect(img, sx0, sy0, sx1 - 1, sy1 - 1, (214, 206, 182))
    F.rect(img, sx0, sy0, sx1 - 1, sy0 + 5, (150, 40, 32))
    ptext(img, (sx0 + sx1) / 2, sy0 + 3, 'HM', F.F35, (236, 226, 210))
    ptext(img, (sx0 + sx1) / 2, sy0 + 10, 'INV', F.F35, (60, 56, 50))
    ptext(img, (sx0 + sx1) / 2, sy0 + 17, ASSET_TAG, F.F35, (40, 36, 32))
    for i in range(3):                                                          # a little barcode
        F.rect(img, sx0 + 3 + i * 4, sy0 + 23, sx0 + 4 + i * 4, sy0 + 28, (40, 36, 32))
    img[sy0, sx0] = img[sy1 - 1, sx1 - 1] = (46, 46, 50)                       # torn corners
    grain(img, (sx0, sy0, sx1, sy1), 33, 5)


def draw_top(img):
    x0, y0, x1, y1 = REG['pager_top']
    fill(img, REG['pager_top'], (46, 46, 50))
    ptext(img, x0 + 20, y0 + 11, 'BEEP', F.F35, (200, 200, 196))
    ptext(img, x0 + 44, y0 + 11, 'VIB', F.F35, (200, 200, 196))
    F.rect(img, x0 + 29, y0 + 9, x0 + 36, y0 + 13, (14, 14, 16))               # the mode switch's slot
    grain(img, REG['pager_top'], 35, 3)
    fill(img, REG['solid_black'], (20, 20, 22))


def draw_keys(img):
    """the keys' faces: dark rubber, the sign in white (up and down: a 7-px triangle, read: a 4-px square)"""
    SIGN, RUB = (236, 236, 230), (60, 60, 64)
    for i, name in enumerate(('key_up', 'key_read', 'key_down')):
        x0, y0, x1, y1 = REG[name]
        fill(img, REG[name], RUB)
        cx, cy = x0 + 7, y0 + 5
        for r in range(4):
            if i == 0:
                F.rect(img, cx - r, cy - 2 + r, cx + r, cy - 2 + r, SIGN)
            elif i == 2:
                F.rect(img, cx - r, cy + 1 - r, cx + r, cy + 1 - r, SIGN)
        if i == 1:
            F.rect(img, cx - 2, cy - 2, cx + 1, cy + 1, SIGN)
        grain(img, REG[name], 37 + i, 3)


def draw_lcd():
    """off: the glass grey-green, the dot cells faintly; lit: green backlight and the message list (dark dots)"""
    w, h = LCD_PX
    base = np.zeros((h, w, 3), np.uint8)
    emi = np.zeros_like(base)
    base[:] = (70, 82, 64)
    for r in range(LCD_ROWS):
        for c in range(LCD_COLS):
            F.rect(base, 2 + c * 6, 2 + r * 9, 2 + c * 6 + 4, 2 + r * 9 + 6, (66, 78, 60))
    emi[:] = (100, 150, 74)
    for r, line in enumerate(LCD_LIST):
        mono(emi, 2, 2 + r * 9, line, (10, 18, 8))
    for i, hh in enumerate((2, 4, 6)):                                          # the signal bars, top right
        F.rect(emi, w - 14 + i * 4, 2 + 7 - hh, w - 12 + i * 4, 2 + 6, (10, 18, 8))
    return base, emi


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (24, 24, 24)
    emi = np.zeros_like(img)
    draw_front(img)
    draw_side(img)
    draw_top(img)
    draw_keys(img)
    lcd_b, lcd_e = draw_lcd()
    paths = {}
    for name, a in (('Panel_BaseColor', img), ('Panel_Emission', emi), ('LCD_BaseColor', lcd_b), ('LCD_Emission', lcd_e)):
        paths[name] = os.path.join(out, f'T_Pager_{name}.png')
        Image.fromarray(a).save(paths[name])
    json.dump(dict(size=N, regions=REG, front=FRONT, lcd_px=LCD_PX, lcd_cols=LCD_COLS, lcd_rows=LCD_ROWS,
                   lcd_cell='6 x 9 px from (2, 2): 5 x 7 dots, 1 px apart, rows 2 px apart', asset_tag=ASSET_TAG),
              open(os.path.join(out, 'pager_panel_regions.json'), 'w'), indent=1, ensure_ascii=False)
    return paths


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'pager')))
