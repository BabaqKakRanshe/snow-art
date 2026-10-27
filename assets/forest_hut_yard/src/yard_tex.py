"""Panel atlas of the hut yard (256 x 256, pixel art, point-filtered) on the explicit-UV objects:
  sign       the arrow board at the trail head (0.92 x 0.19 m): dark stained board, routed cream letters FORSTHÜTTE / 100 m,
             FORESTER'S HUT under it (German first), weathered
  l_lant     the battery lantern's yellow glass: ribbed, the bulb's glow in the middle (warm yellow when lit)
  glow_warm  halo tile for the glow cards (emission only)
  map        the forester's folded map (0.42 x 0.30 m): roads, the stream, woods, the hut, antenna No. 1 circled red, a place in
             the woods crossed out, FORSTKARTE HOHENMOOS
python3 yard_tex.py [out_dir] -> T_Yard_Panel_BaseColor.png, T_Yard_Panel_Emission.png, yard_panel_regions.json"""
import os, sys, json, math
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxfont as F
import van2_tex as VT

# umlauts: the dots replace the top row of the glyph (as hut_tex / cont_tex); a lower-case m for '100 m'
for _f, _src in ((F.F35, {'Ä': '#.#|.#.|#.#|###|#.#', 'Ö': '#.#|...|###|#.#|###', 'Ü': '#.#|...|#.#|#.#|###'}),
                 (F.F57, {'Ä': '.#.#.|.....|.###.|#...#|#####|#...#|#...#', 'Ö': '.#.#.|.....|.###.|#...#|#...#|#...#|.###.',
                          'Ü': '.#.#.|.....|#...#|#...#|#...#|#...#|.###.',
                          'm': '.....|.....|##.#.|#.#.#|#.#.#|#.#.#|#.#.#'})):
    for _k, _s in _src.items():
        _f['glyphs'][_k] = F._compile({'x': _s})['x']

HERE = os.path.dirname(os.path.abspath(__file__))
N = 256
REG = {'sign': (0, 0, 192, 40), 'l_lant': (192, 0, 224, 32), 'glow_warm': (192, 64, 256, 128), 'map': (0, 64, 128, 156),
       'route': (0, 160, 192, 200)}
BOARD, BOARD_D, CREAM = (70, 48, 30), (46, 32, 22), (226, 210, 160)
PAPER, PAPER_D, INK, RED, BLUE, GREEN = (214, 204, 172), (176, 164, 132), (52, 46, 40), (184, 36, 28), (70, 96, 140), (120, 140, 96)


def uv(name, n=N):
    return VT.uv(REG[name], n)


def draw_sign(img):
    x0, y0, x1, y1 = REG['sign']
    yy, xx = np.mgrid[y0:y1, x0:x1]
    grain = 0.88 + 0.12 * np.sin(yy * 1.7 + np.sin(xx * 0.09) * 2.0) + 0.05 * ((xx * 7 + yy * 13) % 5 == 0)
    img[y0:y1, x0:x1] = np.clip(np.array(BOARD)[None, None] * grain[..., None], 0, 255).astype(np.uint8)
    F.frame(img, x0, y0, x1 - 1, y1 - 1, BOARD_D, 2)
    F.text(img, x0 + 70, y0 + 13, 'FORSTHÜTTE', F.F57, CREAM, scale=2)
    F.text(img, x0 + 165, y0 + 13, '100 m', F.F57, CREAM)
    F.text(img, x0 + 165, y0 + 23, '→', F.F57, CREAM)
    F.text(img, x0 + 70, y0 + 31, "FORESTER'S HUT", F.F35, (190, 176, 132))
    rng = np.random.default_rng(31)
    for _ in range(140):                                         # weathering: letters worn, the board's grey bloom
        xx_, yy_ = rng.integers(x0 + 1, x1 - 1), rng.integers(y0 + 1, y1 - 1)
        img[yy_, xx_] = (img[yy_, xx_] * 0.65 + np.array((120, 116, 104)) * 0.35).astype(np.uint8)


def draw_route(img):
    """the station pointer: OBSERVATORIUM (cream, routed) over OBSERVATORY, same board and weathering as the hut's"""
    x0, y0, x1, y1 = REG['route']
    yy, xx = np.mgrid[y0:y1, x0:x1]
    grain = 0.88 + 0.12 * np.sin(yy * 1.7 + np.sin(xx * 0.09) * 2.0) + 0.05 * ((xx * 7 + yy * 13) % 5 == 0)
    img[y0:y1, x0:x1] = np.clip(np.array(BOARD)[None, None] * grain[..., None], 0, 255).astype(np.uint8)
    F.frame(img, x0, y0, x1 - 1, y1 - 1, BOARD_D, 2)
    F.text(img, x0 + 92, y0 + 13, 'OBSERVATORIUM', F.F57, CREAM, scale=2)
    F.text(img, x0 + 92, y0 + 31, 'OBSERVATORY', F.F35, (190, 176, 132))
    rng = np.random.default_rng(37)
    for _ in range(140):
        xx_, yy_ = rng.integers(x0 + 1, x1 - 1), rng.integers(y0 + 1, y1 - 1)
        img[yy_, xx_] = (img[yy_, xx_] * 0.65 + np.array((120, 116, 104)) * 0.35).astype(np.uint8)


def draw_lens(img, emi):
    x0, y0, x1, y1 = REG['l_lant']                               # ribbed yellow glass, the bulb's glow in the middle
    yy, xx = np.mgrid[y0:y1, x0:x1]
    v = (yy + 0.5 - y0) / (y1 - y0)
    rib = 0.80 + 0.20 * (np.mod(xx - x0, 3) < 1)
    bulb = np.exp(-((v - 0.5) / 0.22) ** 2)
    t = VT.BAYER[np.mod(yy, 4), np.mod(xx, 4)]
    base = np.floor((0.40 + 0.25 * bulb) * rib * 8 + t) / 8
    img[y0:y1, x0:x1] = (base[..., None] * np.array((210, 170, 60))[None, None]).astype(np.uint8)
    e = np.clip(0.30 + 0.70 * bulb * rib, 0, 1)
    e = np.floor(e * 9 + t) / 9
    emi[y0:y1, x0:x1] = (e[..., None] * np.array((255, 200, 90))[None, None]).astype(np.uint8)
    x0, y0, x1, y1 = REG['glow_warm']
    yy, xx = np.mgrid[y0:y1, x0:x1]
    rr = np.hypot(xx + 0.5 - (x0 + x1) / 2, yy + 0.5 - (y0 + y1) / 2) / ((x1 - x0) / 2)
    g = np.clip(1 - rr, 0, 1) ** 1.6
    t = VT.BAYER[np.mod(yy, 4), np.mod(xx, 4)]
    g = np.floor(g * 10 + t) / 10
    g[rr > 0.97] = 0
    emi[y0:y1, x0:x1] = (g[..., None] * np.array((255, 190, 100))[None, None]).astype(np.uint8)
    img[y0:y1, x0:x1] = 0


def draw_map(img):
    x0, y0, x1, y1 = REG['map']
    yy, xx = np.mgrid[y0:y1, x0:x1]
    paper = 0.92 + 0.08 * (((xx * 31 + yy * 17) % 7) == 0)
    img[y0:y1, x0:x1] = np.clip(np.array(PAPER)[None, None] * paper[..., None], 0, 255).astype(np.uint8)
    w, h = x1 - x0, y1 - y0
    for fx in (w // 3, 2 * w // 3):                              # the folds
        img[y0:y1, x0 + fx] = PAPER_D
    rng = np.random.default_rng(5)
    for _ in range(260):                                         # woods: green dots
        px, py = x0 + rng.integers(3, w - 3), y0 + rng.integers(14, h - 3)
        img[py, px] = GREEN
    for i in range(w):                                           # the stream
        py = y0 + int(h * 0.62 + 6 * math.sin(i / 9.0))
        img[py, x0 + i] = BLUE
    road = [(4, 20), (40, 40), (70, 52), (100, 70), (124, 86)]   # the road (double line)
    for (ax, ay), (bx, by) in zip(road[:-1], road[1:]):
        F.line(img, x0 + ax, y0 + ay, x0 + bx, y0 + by, INK)
        F.line(img, x0 + ax, y0 + ay + 2, x0 + bx, y0 + by + 2, INK)
    F.line(img, x0 + 70, y0 + 54, x0 + 62, y0 + 74, INK)         # the trail to the hut
    F.rect(img, x0 + 60, y0 + 74, x0 + 63, y0 + 77, INK)          # the hut
    cx, cy = x0 + 84, y0 + 34                                     # antenna No. 1: a mast symbol, circled red
    F.line(img, cx, cy - 4, cx, cy + 3, INK)
    F.line(img, cx - 3, cy + 3, cx + 3, cy + 3, INK)
    for a in range(0, 360, 8):
        px, py = int(round(cx + 7 * math.cos(math.radians(a)))), int(round(cy + 7 * math.sin(math.radians(a))))
        img[py, px] = RED
    F.text(img, cx + 14, cy - 4, '1', F.F35, RED)
    qx, qy = x0 + 26, y0 + 70                                     # a place in the woods crossed out (the cave hook)
    F.line(img, qx - 4, qy - 4, qx + 4, qy + 4, RED)
    F.line(img, qx - 4, qy + 4, qx + 4, qy - 4, RED)
    F.text(img, x0 + w // 2, y0 + 6, 'FORSTKARTE HOHENMOOS', F.F35, INK)
    F.frame(img, x0, y0, x1 - 1, y1 - 1, PAPER_D, 1)


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (16, 16, 16)
    emi = np.zeros_like(img)
    draw_sign(img)
    draw_route(img)
    draw_lens(img, emi)
    draw_map(img)
    pb, pe = os.path.join(out, 'T_Yard_Panel_BaseColor.png'), os.path.join(out, 'T_Yard_Panel_Emission.png')
    Image.fromarray(img).save(pb)
    Image.fromarray(emi).save(pe)
    json.dump(dict(size=N, regions=REG, sign_m=[0.92, 0.19], map_m=[0.42, 0.30]),
              open(os.path.join(out, 'yard_panel_regions.json'), 'w'), indent=1)
    return pb, pe


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'yard')))
