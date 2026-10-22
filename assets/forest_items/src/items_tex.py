"""Panel atlas of the Forest items (Update 6): the printed and written surfaces of the 84 small things (papers, labels,
covers, packs, key tags, dials), pixel art in the project's pixel font, point-filtered, as the panels of the generator
shed and the station (gauges, signs, the logbook page): 512 x 512, 220 - 1300 px per metre on the faces (the paper
fine enough to read a heading, the handwriting as lines). German on what was printed here, English only where the
project's rule wants it (equipment). Everything is invented: no real brand, newspaper or product.
Regions (name -> pixel rect) in REG; uv(name) -> (u0, v0, u1, v1) for the KBs.
python3 items_tex.py [out_dir] -> T_Item_Panel_BaseColor.png, T_Item_Panel_Emission.png (the radio set's lit channel),
  item_panel_regions.json"""
import os, sys, json, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pxfont as F
import van2_tex as VT
import kpp_tex as KT                                       # the umlaut glyphs (patched into pxfont on import)
import road_tex as RTX
import main_tex as MT
from noise import fbm

N = 512
PAPER, PAPER_Y, PAPER_G = (232, 228, 212), (222, 210, 180), (214, 214, 206)
INK, BLUE_INK, PENCIL = (30, 28, 26), (44, 56, 122), (112, 112, 108)
RED, GREEN, BLUE, YEL = (188, 40, 30), (46, 110, 58), (40, 70, 140), (226, 186, 40)


def px(m, ppm):
    return max(4, int(round(m * ppm)))


# name, width px, height px (the size on the model / px per metre in the comment)
SIZES = [
    ('note', px(0.148, 420), px(0.21, 420)), ('noteform', px(0.148, 420), px(0.21, 420)),
    ('note_back', 16, 22), ('sticky', 34, 34), ('photo', px(0.136, 420), px(0.136, 420)),
    ('photo_framed', 56, 48), ('envelope', px(0.238, 400), px(0.152, 400)), ('envelope_back', px(0.238, 200), px(0.152, 200)),
    ('news_front', px(0.30, 330), px(0.42, 330)), ('news_back', px(0.30, 330), px(0.42, 330)),
    ('news_spread', px(0.80, 240), px(0.54, 240)), ('mag_cover', px(0.284, 330), px(0.33, 330)),
    ('mag_back', px(0.284, 200), px(0.33, 200)), ('clip_form', px(0.21, 330), px(0.297, 330)),
    ('paperstack', px(0.21, 330), px(0.297, 330)), ('book_pages', px(0.28, 330), px(0.20, 330)),
    ('binder_b', 64, 18), ('binder_r', 64, 18), ('beer_label', 84, 30), ('beer_neck', 30, 10),
    ('schnaps_label', 28, 36), ('water_label', 84, 26), ('can_red', 80, 40), ('can_green', 80, 40),
    ('tin_band', 108, 30), ('tin_lid', 36, 36), ('jar_label', 36, 22), ('cig_front', 24, 38), ('cig_back', 24, 38),
    ('cig_side', 10, 38), ('cig_top', 24, 10), ('med_front', 38, 18), ('med_end', 18, 18), ('oil_label', 66, 52),
    ('paint_label', 168, 34), ('radio_dial', 60, 18), ('radio_set', 132, 48), ('radio_disp', 56, 10), ('card_back', 24, 36),
    ('card_a', 24, 36), ('card_b', 24, 36), ('card_c', 24, 36), ('card_d', 24, 36),
    ('tag_schranke', 40, 14), ('tag_haupt', 40, 14), ('tag_garage', 40, 14), ('tag_generator', 40, 14),
    ('book_spine_a', 12, 40), ('cardboard_print', 60, 46), ('thermos_band', 60, 16),
    ('carton_top', 56, 30), ('carton_parts', 64, 18),
]
REG = MT.pack(SIZES, n=N)


def uv(name, n=N):
    return VT.uv(REG[name], n)


def size_px(name):
    x0, y0, x1, y1 = REG[name]
    return x1 - x0, y1 - y0


# ------------------------------------------------------------------ helpers
def _fill(img, r, col):
    x0, y0, x1, y1 = r
    img[y0:y1, x0:x1] = col


def _noise(img, r, seed, amount=10, scale=9.0):
    x0, y0, x1, y1 = r
    h, w = y1 - y0, x1 - x0
    yy, xx = np.mgrid[0:h, 0:w]
    q = np.stack([xx.ravel() / scale, yy.ravel() / scale, np.full(xx.size, seed * 0.31)], -1).astype(np.float32)
    n = fbm(q, 1.0, 3, seed=seed % 13).reshape(h, w) - 0.5
    sub = img[y0:y1, x0:x1].astype(np.float64) + n[..., None] * amount * 2
    img[y0:y1, x0:x1] = np.clip(sub, 0, 255).astype(np.uint8)


def _lines(img, r, rows, col, seed, x_in=2, w_frac=(0.55, 1.0), gap_rows=(), dash=False):
    """typed / printed text as grey lines (one pixel per row), ragged right edges, a few short words"""
    x0, y0, x1, y1 = r
    rng = np.random.default_rng(seed)
    for yy in rows:
        if yy in gap_rows or yy >= y1 - y0:
            continue
        L = int((x1 - x0 - 2 * x_in) * rng.uniform(*w_frac))
        x = x0 + x_in
        while x < x0 + x_in + L:
            wl = int(rng.integers(2, 7))
            e = min(x + wl, x0 + x_in + L)
            img[y0 + yy, x:e] = col
            x = e + (1 if not dash else 2)


def _scribble(img, r, rows, col, seed, x_in=3, amp=1.0, w_frac=(0.5, 0.95)):
    """handwriting: wavy strokes along the rows, words with gaps, a slant"""
    x0, y0, x1, y1 = r
    rng = np.random.default_rng(seed)
    for yy in rows:
        L = int((x1 - x0 - 2 * x_in) * rng.uniform(*w_frac))
        x = x0 + x_in
        while x < x0 + x_in + L:
            wl = int(rng.integers(4, 12))
            for k in range(wl):
                xx = x + k
                if xx >= x0 + x_in + L or xx >= x1:
                    break
                dy = int(round(amp * math.sin((xx + seed) * 1.7) * rng.uniform(0.4, 1.0)))
                yv = min(max(y0 + yy + dy, y0), y1 - 1)
                img[yv, xx] = col
                if rng.random() < 0.35:
                    img[max(yv - 1, y0), xx] = col
            x += wl + int(rng.integers(2, 4))


def _photo_block(img, r, seed, faded=0.25):
    """a small picture: sky, a dark tree line, a ground band, a grey dish on its mount, two figures"""
    x0, y0, x1, y1 = r
    h, w = y1 - y0, x1 - x0
    sky = np.array([150, 170, 186]) * (1 - faded) + np.array([200, 190, 160]) * faded
    for yy in range(h):
        t = yy / max(h - 1, 1)
        c = sky * (1 - 0.3 * t) + np.array([90, 96, 80]) * 0.3 * t
        img[y0 + yy, x0:x1] = c.astype(np.uint8)
    rng = np.random.default_rng(seed)
    hor = int(h * 0.55)
    for xx in range(w):
        th = int(hor - h * (0.12 + 0.10 * rng.random()) - (2 if xx % 5 == 0 else 0))
        img[y0 + max(th, 0):y0 + hor, x0 + xx] = (44, 60, 46)
    img[y0 + hor:y1, x0:x1] = (96, 92, 70)
    cx, cy, rr = x0 + int(w * 0.62), y0 + int(h * 0.36), max(3, int(h * 0.20))
    F.disc(img, cx, cy, rr, (196, 198, 196))
    F.disc(img, cx + 1, cy + 1, max(1, rr - 2), (168, 170, 168))
    F.rect(img, cx - 1, cy + rr - 1, cx + 1, y0 + hor + 1, (120, 120, 116))
    for fx in (x0 + int(w * 0.22), x0 + int(w * 0.32)):
        F.rect(img, fx, y0 + hor - 6, fx + 2, y0 + hor + 3, (40, 36, 34))
        F.rect(img, fx, y0 + hor - 8, fx + 2, y0 + hor - 7, (190, 160, 130))
    sub = img[y0:y1, x0:x1].astype(np.float64)
    img[y0:y1, x0:x1] = (sub * (1 - faded) + np.array([214, 200, 168]) * faded).astype(np.uint8)


def _frame_wear(img, r, seed, col=(150, 132, 100), n=14):
    KT._age(img, r, seed, n, 0.22, col)


# ------------------------------------------------------------------ papers
def draw_papers(img):
    r = REG['note']                                                  # handwritten note, lined pad paper, a tear at the top
    _fill(img, r, PAPER)
    x0, y0, x1, y1 = r
    for yy in range(10, y1 - y0 - 3, 4):
        img[y0 + yy, x0 + 2:x1 - 2] = (196, 204, 214)
    img[y0 + 5:y1 - 2, x0 + 8] = (214, 150, 150)
    _scribble(img, r, list(range(9, (y1 - y0) - 8, 4)), BLUE_INK, 11, x_in=10, w_frac=(0.45, 0.92))
    for xx in range(x0, x1, 3):
        img[y0, xx] = (180, 176, 160)
    _noise(img, r, 12, 6)
    _frame_wear(img, r, 13)
    r = REG['noteform']                                              # printed form: header bar, boxes, lines, a signature
    _fill(img, r, PAPER_G)
    x0, y0, x1, y1 = r
    F.rect(img, x0 + 3, y0 + 3, x1 - 4, y0 + 10, (60, 60, 58))
    _lines(img, (x0 + 4, y0 + 5, x1 - 4, y0 + 9), [1, 3], (200, 200, 196), 21, x_in=2, w_frac=(0.4, 0.6))
    for i, yy in enumerate(range(16, (y1 - y0) - 14, 6)):
        F.rect(img, x0 + 3, y0 + yy, x0 + 22, y0 + yy, (90, 90, 88))
        img[y0 + yy + 4, x0 + 24:x1 - 4] = (150, 150, 146)
        if i % 2 == 0:
            _scribble(img, (x0 + 24, y0 + yy, x1 - 4, y0 + yy + 5), [2], BLUE_INK, 30 + i, x_in=1, amp=0.8, w_frac=(0.3, 0.8))
    F.frame(img, x0 + 3, y1 - 13, x1 - 4, y1 - 4, (90, 90, 88))
    _scribble(img, (x0 + 30, y1 - 11, x1 - 6, y1 - 5), [3], BLUE_INK, 41, x_in=1, amp=1.2, w_frac=(0.6, 0.8))
    _noise(img, r, 22, 5)
    _frame_wear(img, r, 23)
    _fill(img, REG['note_back'], PAPER)
    _noise(img, REG['note_back'], 24, 5)
    r = REG['sticky']
    _fill(img, r, (236, 214, 92))
    x0, y0, x1, y1 = r
    _scribble(img, r, [8, 13, 18, 23], (36, 40, 90), 31, x_in=4, amp=1.0, w_frac=(0.5, 0.85))
    F.rect(img, x0, y0, x1 - 1, y0 + 4, (226, 200, 80))
    _noise(img, r, 32, 6)
    r = REG['photo']                                                 # a photo: white border, the dish, two people
    _fill(img, r, (226, 222, 210))
    x0, y0, x1, y1 = r
    _photo_block(img, (x0 + 4, y0 + 4, x1 - 4, y1 - 12), 33, faded=0.30)
    _scribble(img, (x0 + 4, y1 - 10, x1 - 4, y1 - 2), [4], (50, 50, 70), 34, x_in=2, amp=0.6, w_frac=(0.4, 0.6))
    _frame_wear(img, r, 35, n=24)
    r = REG['photo_framed']
    _photo_block(img, r, 36, faded=0.18)
    r = REG['envelope']                                              # address lines, a stamp, the postmark, a window band
    _fill(img, r, (220, 210, 182))
    x0, y0, x1, y1 = r
    F.rect(img, x1 - 18, y0 + 4, x1 - 5, y0 + 19, (176, 60, 52))
    F.frame(img, x1 - 18, y0 + 4, x1 - 5, y0 + 19, (236, 230, 214))
    F.ring(img, x1 - 20, y0 + 14, 6, 7, (60, 56, 60))
    for k in range(3):
        img[y0 + 11 + 3 * k, x1 - 34:x1 - 14] = (60, 56, 60)
    _scribble(img, (x0 + 22, y0 + 26, x1 - 10, y1 - 4), [4, 10, 16, 22], BLUE_INK, 37, x_in=2, amp=0.8, w_frac=(0.35, 0.7))
    _noise(img, r, 38, 6)
    _frame_wear(img, r, 39)
    r = REG['envelope_back']
    _fill(img, r, (216, 206, 178))
    x0, y0, x1, y1 = r
    w, h = x1 - x0, y1 - y0
    F.line(img, x0, y0, x0 + w // 2, y0 + int(h * 0.55), (176, 166, 140))
    F.line(img, x1 - 1, y0, x0 + w // 2, y0 + int(h * 0.55), (176, 166, 140))
    _noise(img, r, 40, 5)


def _news_columns(img, r, seed, top, cols=3, photo=None, ad=None):
    x0, y0, x1, y1 = r
    w = (x1 - x0 - 6) // cols
    for c in range(cols):
        cx0 = x0 + 3 + c * w
        _lines(img, (cx0, y0 + top, cx0 + w - 2, y1 - 3), list(range(0, y1 - y0 - top - 3, 2)), (128, 126, 120),
               seed + c, x_in=0, w_frac=(0.8, 1.0))
    if photo:
        _photo_block(img, photo, seed + 7, faded=0.55)
        sub = img[photo[1]:photo[3], photo[0]:photo[2]].astype(np.float64)
        g = sub.mean(-1, keepdims=True)
        img[photo[1]:photo[3], photo[0]:photo[2]] = (g * 0.9 + 14).astype(np.uint8).repeat(3, -1)
    if ad:
        F.rect(img, ad[0], ad[1], ad[2], ad[3], PAPER_Y)
        F.frame(img, ad[0], ad[1], ad[2], ad[3], (60, 58, 54))
        F.text(img, (ad[0] + ad[2]) // 2, (ad[1] + ad[3]) // 2, 'BAUMARKT', F.F35, (60, 58, 54))


def draw_print(img):
    r = REG['news_front']                                            # local paper: masthead, headline, photo, columns
    _fill(img, r, PAPER_Y)
    x0, y0, x1, y1 = r
    F.text(img, (x0 + x1) // 2, y0 + 8, 'HOHENMOOSER BOTE', F.F57, INK, scale=1)
    img[y0 + 14, x0 + 3:x1 - 3] = INK
    img[y0 + 16, x0 + 3:x1 - 3] = (110, 106, 98)
    F.text(img, (x0 + x1) // 2, y0 + 22, 'FUNKSTILLE AM BERG', F.F35, INK, scale=1)
    _news_columns(img, r, 51, 30, cols=3, photo=(x0 + 4, y0 + 30, x0 + 62, y0 + 70))
    _noise(img, r, 52, 7)
    _frame_wear(img, r, 53, n=40)
    r = REG['news_back']
    _fill(img, r, PAPER_Y)
    x0, y0, x1, y1 = r
    _news_columns(img, r, 54, 4, cols=4, ad=(x0 + 52, y1 - 40, x1 - 5, y1 - 6))
    _noise(img, r, 55, 7)
    r = REG['news_spread']                                           # inside pages, a crease down the middle
    _fill(img, r, PAPER_Y)
    x0, y0, x1, y1 = r
    mid = (x0 + x1) // 2
    _news_columns(img, (x0, y0, mid - 2, y1), 56, 12, cols=4, photo=(x0 + 6, y0 + 12, x0 + 60, y0 + 50))
    _news_columns(img, (mid + 2, y0, x1, y1), 57, 12, cols=4, ad=(x1 - 70, y1 - 46, x1 - 8, y1 - 8))
    F.text(img, (x0 + mid) // 2, y0 + 6, 'AUS DER REGION', F.F35, INK)
    F.text(img, (mid + x1) // 2, y0 + 6, 'SPORT', F.F35, INK)
    img[y0:y1, mid - 1:mid + 1] = (176, 166, 140)
    _noise(img, r, 58, 8)
    _frame_wear(img, r, 59, n=60)
    r = REG['mag_cover']                                             # magazine: title band, a big picture, two teasers
    x0, y0, x1, y1 = r
    _photo_block(img, (x0, y0 + 16, x1, y1), 61, faded=0.05)
    F.rect(img, x0, y0, x1 - 1, y0 + 15, (176, 34, 30))
    F.text(img, (x0 + x1) // 2, y0 + 8, 'TECHNIK HEUTE', F.F57, (240, 236, 226))
    F.rect(img, x0 + 4, y1 - 22, x0 + 54, y1 - 6, (240, 210, 40))
    F.text(img, x0 + 29, y1 - 14, 'ANTENNEN', F.F35, INK)
    F.text(img, x1 - 30, y0 + 24, 'NR 9', F.F35, (240, 236, 226))
    _noise(img, r, 62, 6)
    _frame_wear(img, r, 63, n=30)
    r = REG['mag_back']
    x0, y0, x1, y1 = r
    _fill(img, r, (54, 74, 104))
    F.rect(img, x0 + 6, y0 + 10, x1 - 7, y1 - 22, (206, 196, 170))
    F.text(img, (x0 + x1) // 2, y1 - 12, 'ALPENKRONE', F.F35, (236, 230, 210))
    _noise(img, r, 64, 6)
    for name, seed in (('clip_form', 71), ('paperstack', 72)):        # a checklist on the clipboard, a typed page
        r = REG[name]
        _fill(img, r, PAPER_G if name == 'clip_form' else PAPER)
        x0, y0, x1, y1 = r
        if name == 'clip_form':
            F.text(img, (x0 + x1) // 2, y0 + 5, 'KONTROLLE', F.F35, INK)
            for k, yy in enumerate(range(12, y1 - y0 - 4, 5)):
                F.frame(img, x0 + 3, y0 + yy, x0 + 6, y0 + yy + 3, (80, 80, 78))
                _lines(img, (x0 + 9, y0 + yy + 1, x1 - 3, y0 + yy + 3), [1], (120, 120, 116), seed + k, x_in=0, w_frac=(0.4, 0.9))
                if k % 3 != 2:
                    F.line(img, x0 + 3, y0 + yy + 2, x0 + 5, y0 + yy + 4, BLUE_INK)
        else:
            _lines(img, r, list(range(8, y1 - y0 - 6, 3)), (90, 90, 88), seed, x_in=6, w_frac=(0.7, 1.0))
            F.text(img, x0 + 22, y0 + 4, 'PROTOKOLL', F.F35, INK)
        _noise(img, r, seed + 5, 5)
        _frame_wear(img, r, seed + 6)
    r = REG['book_pages']
    _fill(img, r, PAPER_Y)
    x0, y0, x1, y1 = r
    mid = (x0 + x1) // 2
    _lines(img, (x0, y0, mid - 3, y1), list(range(6, y1 - y0 - 5, 3)), (100, 98, 92), 81, x_in=5, w_frac=(0.85, 1.0))
    _lines(img, (mid + 3, y0, x1, y1), list(range(6, y1 - y0 - 5, 3)), (100, 98, 92), 82, x_in=5, w_frac=(0.85, 1.0))
    img[y0:y1, mid - 1:mid + 1] = (170, 160, 136)
    _noise(img, r, 83, 6)
    _frame_wear(img, r, 84, n=20)
    for name, col, txt in (('binder_b', (44, 70, 128), 'WARTUNG'), ('binder_r', (156, 40, 32), 'PROTOKOLLE')):
        r = REG[name]
        _fill(img, r, col)
        x0, y0, x1, y1 = r
        F.rect(img, x0 + 8, y0 + 3, x1 - 20, y1 - 4, PAPER)
        F.text(img, (x0 + 8 + x1 - 20) // 2, (y0 + y1) // 2, txt, F.F35, INK)
        F.disc(img, x1 - 11, (y0 + y1) // 2, 4, (20, 20, 22))
        _noise(img, r, 85, 6)
    r = REG['book_spine_a']
    _fill(img, r, (96, 40, 34))
    x0, y0, x1, y1 = r
    F.rect(img, x0 + 2, y0 + 6, x1 - 3, y0 + 8, (200, 170, 90))
    F.rect(img, x0 + 2, y1 - 9, x1 - 3, y1 - 7, (200, 170, 90))


# ------------------------------------------------------------------ labels, packs
def draw_labels(img):
    r = REG['beer_label']                                            # oval cream label, a crest, the brewery name
    _fill(img, r, (60, 40, 24))
    x0, y0, x1, y1 = r
    F.rect(img, x0 + 26, y0 + 2, x0 + 58, y1 - 3, (226, 208, 160))
    F.frame(img, x0 + 26, y0 + 2, x0 + 58, y1 - 3, (160, 40, 30))
    F.text(img, x0 + 42, y0 + 9, 'BERG', F.F35, (150, 34, 26))
    F.text(img, x0 + 42, y0 + 16, 'PILS', F.F57, INK)
    F.text(img, x0 + 42, y0 + 24, '0,5L', F.F35, (90, 80, 60))
    r = REG['beer_neck']
    _fill(img, r, (196, 170, 90))
    F.rect(img, r[0], r[1] + 4, r[2] - 1, r[1] + 5, (150, 34, 26))
    r = REG['schnaps_label']
    _fill(img, r, (230, 226, 214))
    x0, y0, x1, y1 = r
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, (40, 40, 40))
    F.text(img, (x0 + x1) // 2, y0 + 9, 'KORN', F.F57, INK)
    F.rect(img, x0 + 4, y0 + 16, x1 - 5, y0 + 17, (170, 30, 26))
    F.text(img, (x0 + x1) // 2, y0 + 24, '38%', F.F35, INK)
    _noise(img, r, 91, 5)
    r = REG['water_label']
    _fill(img, r, (40, 92, 56))
    x0, y0, x1, y1 = r
    F.rect(img, x0 + 20, y0 + 3, x0 + 64, y1 - 4, (232, 236, 230))
    F.text(img, x0 + 42, y0 + 10, 'QUELLE', F.F35, (40, 92, 56))
    F.text(img, x0 + 42, y0 + 17, 'HOHENMOOS', F.F35, (70, 70, 70))
    for name, col, txt in (('can_red', (178, 36, 28), 'TOMATEN'), ('can_green', (52, 104, 48), 'ERBSEN')):
        r = REG[name]                                                # paper label round the can: a band, a picture, a name
        _fill(img, r, col)
        x0, y0, x1, y1 = r
        F.rect(img, x0, y0 + 4, x1 - 1, y0 + 6, (232, 220, 190))
        F.rect(img, x0, y1 - 7, x1 - 1, y1 - 5, (232, 220, 190))
        F.text(img, x0 + 24, y0 + 19, txt, F.F35, (240, 236, 220))
        F.disc(img, x0 + 58, y0 + 20, 7, (210, 60, 40) if name == 'can_red' else (120, 180, 80))
        F.disc(img, x0 + 58, y0 + 20, 3, (240, 120, 90) if name == 'can_red' else (170, 220, 120))
        _noise(img, r, 92, 6)
    r = REG['tin_band']
    _fill(img, r, (196, 172, 64))
    x0, y0, x1, y1 = r
    F.text(img, x0 + 30, y0 + 15, 'SARDINEN', F.F35, (40, 50, 110))
    F.rect(img, x0 + 62, y0 + 9, x0 + 90, y0 + 20, (60, 90, 140))
    F.line(img, x0 + 65, y0 + 15, x0 + 86, y0 + 14, (200, 210, 220))
    _noise(img, r, 93, 6)
    r = REG['tin_lid']
    _fill(img, r, (186, 188, 184))
    F.ring(img, (r[0] + r[2]) // 2, (r[1] + r[3]) // 2, 12, 13, (140, 142, 140))
    F.ring(img, (r[0] + r[2]) // 2, (r[1] + r[3]) // 2, 7, 8, (150, 152, 150))
    r = REG['jar_label']
    _fill(img, r, (236, 230, 206))
    x0, y0, x1, y1 = r
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, (60, 110, 60))
    F.text(img, (x0 + x1) // 2, (y0 + y1) // 2, 'GURKEN', F.F35, (40, 80, 40))
    for name in ('cig_front', 'cig_back'):                           # cigarettes: white pack, a red chevron, the brand
        r = REG[name]
        _fill(img, r, (232, 230, 222))
        x0, y0, x1, y1 = r
        for k in range(8):
            F.rect(img, x0 + k, y0 + 18 - k // 2, x0 + k, y0 + 22 - k // 2, (178, 30, 28))
            F.rect(img, x1 - 1 - k, y0 + 18 - k // 2, x1 - 1 - k, y0 + 22 - k // 2, (178, 30, 28))
        F.rect(img, x0 + 8, y0 + 14, x1 - 9, y0 + 22, (178, 30, 28))
        F.text(img, (x0 + x1) // 2, y0 + 8, 'ALPEN', F.F35, (40, 36, 34))
        if name == 'cig_back':
            F.rect(img, x0 + 2, y1 - 12, x1 - 3, y1 - 3, (40, 36, 34))
            _lines(img, (x0 + 3, y1 - 11, x1 - 3, y1 - 4), [1, 3, 5], (230, 228, 220), 94, x_in=0)
    _fill(img, REG['cig_side'], (220, 218, 210))
    F.rect(img, REG['cig_side'][0], REG['cig_side'][1] + 18, REG['cig_side'][2] - 1, REG['cig_side'][1] + 22, (178, 30, 28))
    _fill(img, REG['cig_top'], (232, 230, 222))
    F.rect(img, REG['cig_top'][0] + 2, REG['cig_top'][1] + 3, REG['cig_top'][2] - 3, REG['cig_top'][1] + 6, (210, 190, 120))
    r = REG['med_front']                                             # pain tablets: white box, a green cross, a stripe
    _fill(img, r, (236, 236, 230))
    x0, y0, x1, y1 = r
    F.rect(img, x0 + 4, y0 + 6, x0 + 11, y0 + 8, (40, 130, 70))
    F.rect(img, x0 + 6, y0 + 4, x0 + 9, y0 + 10, (40, 130, 70))
    F.text(img, x0 + 25, y0 + 6, 'TABL.', F.F35, (40, 40, 60))
    F.rect(img, x0, y1 - 5, x1 - 1, y1 - 3, (60, 100, 170))
    _fill(img, REG['med_end'], (236, 236, 230))
    F.rect(img, REG['med_end'][0], REG['med_end'][3] - 5, REG['med_end'][2] - 1, REG['med_end'][3] - 3, (60, 100, 170))
    r = REG['oil_label']                                             # engine oil: yellow band, the grade, English under
    _fill(img, r, (36, 76, 150))
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0 + 12, x1 - 1, y0 + 26, (226, 190, 40))
    F.text(img, (x0 + x1) // 2, y0 + 19, 'MOTOROEL', F.F57, (30, 30, 40))
    F.text(img, (x0 + x1) // 2, y0 + 33, 'ENGINE OIL', F.F35, (230, 230, 236))
    F.text(img, (x0 + x1) // 2, y0 + 42, 'SAE 15W-40  5L', F.F35, (230, 230, 236))
    _noise(img, r, 95, 6)
    r = REG['paint_label']                                           # paint tin: white label, a colour swatch, the name
    _fill(img, r, (230, 228, 220))
    x0, y0, x1, y1 = r
    F.rect(img, x0 + 10, y0 + 6, x0 + 34, y1 - 7, (40, 96, 70))
    F.text(img, x0 + 74, y0 + 12, 'LACKFARBE', F.F35, INK)
    F.text(img, x0 + 74, y0 + 21, 'RESEDAGRUEN', F.F35, (40, 96, 70))
    F.text(img, x0 + 130, y0 + 17, '2,5 L', F.F35, INK)
    _noise(img, r, 96, 6)
    r = REG['radio_dial']                                            # transistor radio: dial scale with the bands
    _fill(img, r, (214, 196, 150))
    x0, y0, x1, y1 = r
    for k in range(4, x1 - x0 - 3, 4):
        img[y0 + 4:y0 + 7 if k % 8 else y0 + 9, x0 + k] = (60, 50, 40)
    F.text(img, x0 + 12, y1 - 5, 'UKW', F.F35, (60, 50, 40))
    F.text(img, x0 + 40, y1 - 5, 'MW', F.F35, (60, 50, 40))
    img[y0 + 2:y1 - 2, x0 + 31] = (190, 40, 30)
    r = REG['radio_set']                                             # the control room's set: grey front, meter, dial, keys
    _fill(img, r, (110, 116, 112))
    x0, y0, x1, y1 = r
    F.rect(img, x0 + 4, y0 + 6, x0 + 30, y0 + 24, (210, 200, 160))
    F.ring(img, x0 + 17, y0 + 24, 12, 13, (60, 56, 48), a0=200, a1=340)
    F.line(img, x0 + 17, y0 + 22, x0 + 24, y0 + 12, (180, 30, 26))
    F.rect(img, x0 + 36, y0 + 8, x0 + 92, y0 + 18, (30, 34, 30))      # the channel window (the display quad sits on it)
    for k in range(6):
        F.rect(img, x0 + 38 + 9 * k, y0 + 26, x0 + 44 + 9 * k, y0 + 31, (40, 40, 40))
    F.text(img, x0 + 112, y0 + 9, 'FUG 8', F.F35, (230, 230, 226))
    F.text(img, x0 + 64, y1 - 6, 'TRANSMIT  RECEIVE  SQUELCH', F.F35, (220, 220, 214))   # equipment labels in English
    _noise(img, r, 97, 4)
    r = REG['thermos_band']
    _fill(img, r, (48, 92, 60))
    F.rect(img, r[0], r[1] + 6, r[2] - 1, r[1] + 9, (210, 196, 150))
    r = REG['cardboard_print']                                       # flattened carton: the maker's print, arrows
    _fill(img, r, (176, 144, 100))
    x0, y0, x1, y1 = r
    F.text(img, (x0 + x1) // 2, y0 + 8, 'KARTON', F.F35, (70, 54, 40))
    for k, xx in enumerate((x0 + 14, x0 + 22)):
        F.rect(img, xx, y0 + 20, xx + 1, y0 + 34, (70, 54, 40))
        F.line(img, xx - 3, y0 + 24, xx, y0 + 20, (70, 54, 40))
        F.line(img, xx + 4, y0 + 24, xx + 1, y0 + 20, (70, 54, 40))
    F.frame(img, x0 + 32, y0 + 18, x1 - 6, y1 - 6, (70, 54, 40))
    F.text(img, x0 + 45, y0 + 28, 'OBEN', F.F35, (70, 54, 40))
    _noise(img, r, 98, 8)


def draw_cartons(img):
    r = REG['carton_top']                                            # printed on the carton: OBEN / TOP with two arrows
    _fill(img, r, (176, 144, 100))
    x0, y0, x1, y1 = r
    ink = (64, 48, 34)
    for xx in (x0 + 7, x1 - 9):
        F.rect(img, xx, y0 + 9, xx + 2, y1 - 4, ink)
        for k in range(4):
            F.rect(img, xx - k, y0 + 6 + k, xx + 2 + k, y0 + 6 + k, ink)
    F.text(img, (x0 + x1) // 2, y0 + 10, 'OBEN', F.F57, ink)
    F.text(img, (x0 + x1) // 2, y0 + 21, 'TOP', F.F57, ink)
    _noise(img, r, 101, 8)
    r = REG['carton_parts']
    _fill(img, r, (176, 144, 100))
    x0, y0, x1, y1 = r
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, (40, 50, 110))
    F.text(img, (x0 + x1) // 2, y0 + 6, 'ERSATZTEILE', F.F35, (40, 50, 110))
    F.text(img, (x0 + x1) // 2, y0 + 12, 'SPARE PARTS', F.F35, (40, 50, 110))
    _noise(img, r, 102, 8)


def draw_cards(img):
    r = REG['card_back']                                             # red backs with a lattice, white border
    _fill(img, r, (236, 232, 222))
    x0, y0, x1, y1 = r
    F.rect(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, (170, 36, 34))
    for yy in range(y0 + 3, y1 - 3):
        for xx in range(x0 + 3, x1 - 3):
            if (xx + yy) % 4 == 0 or (xx - yy) % 4 == 0:
                img[yy, xx] = (210, 120, 110)
    for name, txt, col in (('card_a', '7', RED), ('card_b', 'K', INK), ('card_c', 'A', RED), ('card_d', '9', INK)):
        r = REG[name]
        _fill(img, r, (238, 236, 228))
        x0, y0, x1, y1 = r
        F.text(img, x0 + 4, y0 + 5, txt, F.F35, col)
        F.text(img, x1 - 5, y1 - 6, txt, F.F35, col)
        F.disc(img, (x0 + x1) // 2, (y0 + y1) // 2, 4, col)


def draw_tags(img):
    for name, txt, col in (('tag_schranke', 'SCHRANKE', (178, 40, 30)), ('tag_haupt', 'HAUPTGEB.', (40, 70, 140)),
                           ('tag_garage', 'GARAGE', (46, 110, 58)), ('tag_generator', 'GENERATOR', (210, 170, 40))):
        r = REG[name]
        _fill(img, r, col)
        x0, y0, x1, y1 = r
        F.rect(img, x0 + 2, y0 + 3, x1 - 3, y1 - 4, (236, 230, 210))
        RTX.prop_text(img, (x0 + x1) / 2, (y0 + y1) / 2, txt, F.F35, INK)


def draw_display(img, emi):
    """the radio set's channel display (X08: it lights up by itself): the albedo shows dark glass with the unlit
    segments, the emission map the channel - M_RadioDisplay (off) / M_RadioDisplayOn (on) share the UVs"""
    x0, y0, x1, y1 = REG['radio_disp']
    _fill(img, REG['radio_disp'], (22, 26, 22))
    F.text(img, (x0 + x1) // 2, (y0 + y1) // 2, '88.888', F.F35, (44, 40, 34))
    F.text(emi, (x0 + x1) // 2, (y0 + y1) // 2, '27.135', F.F35, (255, 150, 60))


def build(out_dir):
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (128, 128, 128)
    emi = np.zeros((N, N, 3), np.uint8)
    draw_papers(img)
    draw_print(img)
    draw_labels(img)
    draw_cards(img)
    draw_tags(img)
    draw_cartons(img)
    draw_display(img, emi)
    p = os.path.join(out_dir, 'T_Item_Panel_BaseColor.png')
    Image.fromarray(img, 'RGB').save(p)
    Image.fromarray(emi, 'RGB').save(os.path.join(out_dir, 'T_Item_Panel_Emission.png'))
    json.dump(dict(size=N, regions=REG), open(os.path.join(out_dir, 'item_panel_regions.json'), 'w'), indent=1)
    return p


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'items')
    os.makedirs(out, exist_ok=True)
    print(build(out))
