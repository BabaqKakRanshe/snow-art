"""Panel atlas of the first-evening plates (512 x 256, pixel art, point-filtered; docs/gdd/QUESTIONS_7.md §4, user 27.10):
  map       the overlook's board (1.00 x 1.10 m): SIE SIND HIER / YOU ARE HERE over a north-up map of the area - the start
            post, the road, the lake with the hangar on its south-west bank, the checkpoint, the station; the red dot is the
            overlook itself (QUESTIONS_7 16)
  genstart  the generator's start form on the container wall by its door (0.63 x 0.58 m): STARTVORGANG, three steps
            1 KRAFTSTOFF / FUEL, 2 START, 3 HAUPTSCHALTER / MAIN SWITCH (QUESTIONS_7 6)
  hangar    the plate on the lake hangar's gate (0.70 x 0.31 m): GESPERRT / LOCKED, SCHLÜSSEL: STATIONSLEITER / KEY: STATION
            CHIEF - the key that is missing from the checkpoint's board (QUESTIONS_7 17)
  notstrom  the tag on the checkpoint's power cabinet (0.36 x 0.13 m): NOTSTROM / 12V EMERGENCY (QUESTIONS_7 15)
Wall signs German first, English under it (snow_style.json lettering); enamel white, red border, screws, aged pixels.
python3 pl_tex.py [out_dir] -> T_PL_Panel_BaseColor.png, pl_panel_regions.json"""
import os, sys, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxfont as F
import van2_tex as VT

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 512, 256
PPM = 160.0                                                   # the panel class (snow_style.json classes.panel_signs_lenses)
REG = {'map': (0, 0, 160, 176), 'genstart': (168, 0, 278, 92), 'hangar': (286, 0, 398, 50), 'notstrom': (286, 58, 350, 79)}
ENAMEL, RED, INK, GREY = (226, 224, 214), (176, 34, 30), (40, 36, 34), (112, 106, 96)
PAPER, PAPER_D, FOREST, WATER, WATER_D, ROAD = (222, 212, 180), (150, 138, 110), (122, 140, 96), (150, 176, 190), (84, 110, 128), (70, 56, 44)

# umlauts: the dots replace the top row of the glyph (as kpp_tex / hut_tex / cont_tex)
for _f, _src in ((F.F35, {'Ä': '#.#|.#.|#.#|###|#.#', 'Ö': '#.#|...|###|#.#|###', 'Ü': '#.#|...|#.#|#.#|###'}),
                 (F.F57, {'Ä': '.#.#.|.....|.###.|#...#|#####|#...#|#...#', 'Ö': '.#.#.|.....|.###.|#...#|#...#|#...#|.###.',
                          'Ü': '.#.#.|.....|#...#|#...#|#...#|#...#|.###.'})):
    for _k, _s in _src.items():
        _f['glyphs'][_k] = F._compile({'x': _s})['x']


def uv(name):
    """pixel rect -> (u0, v0, u1, v1) on the 512 x 256 atlas with a half-texel inset"""
    x0, y0, x1, y1 = REG[name]
    return ((x0 + 0.5) / W, 1 - (y1 - 0.5) / H, (x1 - 0.5) / W, 1 - (y0 + 0.5) / H)


def size_m(name):
    x0, y0, x1, y1 = REG[name]
    return (x1 - x0) / PPM, (y1 - y0) / PPM


def _age(img, reg, seed, n, chips=True):
    """18-70 random pixels per plate darker, a few chips to the black steel (snow_style lettering: ageing)"""
    x0, y0, x1, y1 = reg
    rng = np.random.default_rng(seed)
    for _ in range(n):
        xx_, yy_ = rng.integers(x0 + 1, x1 - 1), rng.integers(y0 + 1, y1 - 1)
        img[yy_, xx_] = (img[yy_, xx_] * 0.68 + np.array((120, 116, 104)) * 0.32).astype(np.uint8)
    for _ in range(max(4, n // 6) if chips else 0):
        cx, cy = rng.integers(x0 + 1, x1 - 2), rng.integers(y0 + 1, y1 - 2)
        if rng.random() < 0.5:                                    # chips mostly at the rim
            cx = x0 + 1 if rng.random() < 0.5 else x1 - 2
        img[cy:cy + rng.integers(1, 3), cx:cx + rng.integers(1, 3)] = (34, 32, 30)


def _enamel(img, name, border=3):
    """white enamel, a red border inset 2 px, four rusty screws"""
    x0, y0, x1, y1 = REG[name]
    img[y0:y1, x0:x1] = ENAMEL
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, RED, border)
    for cx, cy in ((x0 + 6, y0 + 6), (x1 - 7, y0 + 6), (x0 + 6, y1 - 7), (x1 - 7, y1 - 7)):
        F.disc(img, cx, cy, 1, (30, 30, 30))
        img[cy, cx] = (120, 70, 40)                               # rust in the screw slot


def draw_genstart(img):
    x0, y0, x1, y1 = REG['genstart']
    _enamel(img, 'genstart')
    cx = (x0 + x1) // 2
    F.text(img, cx, y0 + 12, 'STARTVORGANG', F.F57, INK)
    F.text(img, cx, y0 + 21, 'START PROCEDURE', F.F35, RED)
    F.rect(img, x0 + 9, y0 + 26, x1 - 10, y0 + 26, GREY)
    for i, (de, en) in enumerate((('1 KRAFTSTOFF', 'FUEL'), ('2 START', 'START'), ('3 HAUPTSCHALTER', 'MAIN SWITCH'))):
        ty = y0 + 35 + i * 19
        F.text(img, x0 + 10, ty, de, F.F57, INK, align='l')
        F.text(img, x0 + 16, ty + 9, en, F.F35, GREY, align='l')
    _age(img, REG['genstart'], 61, 60)


def draw_hangar(img):
    x0, y0, x1, y1 = REG['hangar']
    _enamel(img, 'hangar')
    cx = (x0 + x1) // 2
    F.text(img, cx, y0 + 11, 'GESPERRT', F.F57, INK)
    F.text(img, cx, y0 + 19, 'LOCKED', F.F35, RED)
    F.text(img, cx, y0 + 29, 'SCHLÜSSEL: STATIONSLEITER', F.F35, INK)
    F.text(img, cx, y0 + 37, 'KEY: STATION CHIEF', F.F35, RED)
    _age(img, REG['hangar'], 62, 40)


def draw_notstrom(img):
    """a small equipment plate: fill + 1 px light frame + 1 px dark bottom / right (no room for the red border)"""
    x0, y0, x1, y1 = REG['notstrom']
    img[y0:y1, x0:x1] = (214, 180, 40)                             # yellow warning plate
    F.rect(img, x0, y0, x1 - 1, y0, (236, 214, 120))
    F.rect(img, x0, y0, x0, y1 - 1, (236, 214, 120))
    F.rect(img, x0, y1 - 1, x1 - 1, y1 - 1, (120, 96, 20))
    F.rect(img, x1 - 1, y0, x1 - 1, y1 - 1, (120, 96, 20))
    cx = (x0 + x1) // 2
    F.text(img, cx, y0 + 7, 'NOTSTROM', F.F57, INK)
    F.text(img, cx, y0 + 15, '12V EMERGENCY', F.F35, INK)
    _age(img, REG['notstrom'], 63, 18)


# ---------------------------------------------------------------- the overlook's map (north up, world x / z in metres)
MAP_X0, MAP_Z1, MAP_S = -560.0, 600.0, 7.58                   # the world's top-left corner and metres per pixel
ROAD_PTS = [(-511, 554), (-422, 436), (-331, 332), (-250, 258), (-145, 155), (18, 66), (144, -65), (320, -310), (340, -350)]
POST, OVERLOOK, KPP, STATION, HANGAR = (-511, 554), (-185, 148), (144, -65), (340, -355), (-150, -34)
LAKE_C, LAKE_R = (-90, 35), (105, 85)                         # Forest lake ice: x -214..23, z -75..130 (Editor.log 27.10)


def _px(p, x0, y0):
    return x0 + 12.5 + (p[0] - MAP_X0) / MAP_S, y0 + 32 + (MAP_Z1 - p[1]) / MAP_S


def draw_map(img):
    x0, y0, x1, y1 = REG['map']
    img[y0:y1, x0:x1] = (92, 70, 48)                               # the board's wood shows round the paper
    mx0, my0, mx1, my1 = x0 + 4, y0 + 24, x1 - 5, y1 - 5
    yy, xx = np.mgrid[my0:my1 + 1, mx0:mx1 + 1]
    t = VT.BAYER[np.mod(yy, 4), np.mod(xx, 4)]
    paper = np.where((t > 0.82)[..., None], np.array(FOREST)[None, None], np.array(PAPER)[None, None])
    img[my0:my1 + 1, mx0:mx1 + 1] = paper.astype(np.uint8)            # the forest as a light green screen
    F.frame(img, mx0, my0, mx1, my1, PAPER_D, 1)
    # header on the enamel strip
    F.rect(img, x0 + 4, y0 + 3, x1 - 5, y0 + 20, ENAMEL)
    F.disc(img, x0 + 12, y0 + 9.5, 2.6, RED)
    F.text(img, x0 + 18, y0 + 9, 'SIE SIND HIER', F.F57, INK, align='l')
    F.text(img, x0 + 18, y0 + 17, 'YOU ARE HERE', F.F35, RED, align='l')
    # the lake (an ellipse over the ice's extent) and its outline
    lc = _px(LAKE_C, x0, y0)
    rx, rz = LAKE_R[0] / MAP_S, LAKE_R[1] / MAP_S
    d = ((xx + 0.5 - lc[0]) / rx) ** 2 + ((yy + 0.5 - lc[1]) / rz) ** 2
    img[my0:my1 + 1, mx0:mx1 + 1][d <= 1.0] = WATER
    img[my0:my1 + 1, mx0:mx1 + 1][(d > 0.82) & (d <= 1.0)] = WATER_D
    F.text(img, lc[0], lc[1] - 1, 'SEE', F.F35, WATER_D)
    F.text(img, lc[0], lc[1] + 6, 'LAKE', F.F35, WATER_D)
    # the road, 2 px
    pts = [_px(p, x0, y0) for p in ROAD_PTS]
    for a, b in zip(pts[:-1], pts[1:]):
        F.line(img, a[0], a[1], b[0], b[1], ROAD, 2)
    # places
    p = _px(POST, x0, y0)
    F.rect(img, int(p[0]) - 1, int(p[1]) - 1, int(p[0]) + 2, int(p[1]) + 2, INK)
    F.text(img, p[0] + 5, p[1] - 3, 'POSTEN', F.F35, INK, align='l')
    p = _px(KPP, x0, y0)
    F.rect(img, int(p[0]) - 3, int(p[1]), int(p[0]) + 3, int(p[1]) + 1, RED)            # the barrier across the road
    F.text(img, p[0] + 6, p[1] - 4, 'KPP', F.F35, INK, align='l')
    p = _px(STATION, x0, y0)
    F.rect(img, int(p[0]) - 3, int(p[1]) - 2, int(p[0]) + 3, int(p[1]) + 2, INK)
    F.text(img, p[0] - 5, p[1] - 8, 'STATION', F.F35, INK, align='r')
    p = _px(HANGAR, x0, y0)
    F.rect(img, int(p[0]) - 2, int(p[1]) - 1, int(p[0]) + 1, int(p[1]) + 1, INK)
    F.text(img, p[0] - 4, p[1] + 1, 'HANGAR', F.F35, INK, align='r')
    p = _px(OVERLOOK, x0, y0)                                       # you are here: a red dot, a wedge to the lake
    F.disc(img, p[0], p[1], 2.6, RED)
    F.line(img, p[0] + 2, p[1] + 2, p[0] + 6, p[1] + 6, RED, 1)
    # north arrow
    nx, ny = mx1 - 9, my0 + 6
    F.line(img, nx, ny + 9, nx, ny + 1, INK, 1)
    F.line(img, nx - 2, ny + 3, nx, ny + 1, INK, 1)
    F.line(img, nx + 2, ny + 3, nx, ny + 1, INK, 1)
    F.text(img, nx, ny + 13, 'N', F.F35, INK)
    _age(img, (mx0, my0, mx1, my1), 64, 70, chips=False)


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((H, W, 3), np.uint8)
    img[:] = (16, 16, 16)
    draw_map(img)
    draw_genstart(img)
    draw_hangar(img)
    draw_notstrom(img)
    pb, pe = os.path.join(out, 'T_PL_Panel_BaseColor.png'), os.path.join(out, 'T_PL_Panel_Emission.png')
    Image.fromarray(img).save(pb)
    Image.fromarray(np.zeros_like(img)).save(pe)                  # no glow: the plates are read by torchlight
    json.dump(dict(size=[W, H], ppm=PPM, regions=REG, metres={k: size_m(k) for k in REG}),
              open(os.path.join(out, 'pl_panel_regions.json'), 'w'), indent=1)
    return pb, pe


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'pl')))
