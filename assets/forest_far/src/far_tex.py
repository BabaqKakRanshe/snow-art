"""Panel atlas of the far points (512 x 512, pixel art, point-filtered, 160 px/m on the faces as the road's signs), in the
project's pixel font; German first, English under it (the project's rule for wall signs):
  dish     ANTENNENANLAGE / ANTENNA SITE - VORSICHT HOCHFREQUENZ / CAUTION RF RADIATION: white, the radiation triangle
           (the same plate at all five dishes: they share their atlas)
  radome   RADARSTATION / RADAR STATION - ZUTRITT VERBOTEN / NO ENTRY: on the shelter's door
  relay    FUNKSTATION - ZUTRITT VERBOTEN / RADIO RELAY STATION - NO ENTRY: on the compound's gate
  meteo    WETTERSTATION / WEATHER STATION: the station's green plate on the enclosure's gate
  lookout  AUSSICHTSTURM / LOOKOUT TOWER - BETRETEN AUF EIGENE GEFAHR / CLIMB AT YOUR OWN RISK: on a leg by the stairs
  pump     PUMPSTATION / PUMP STATION: blue enamel over the door
  chapel   WALDKAPELLE / FOREST CHAPEL: carved board by the path (pale letters cut into dark wood)
The faces glow faintly at night as the road's signs (the material's emission = the albedo at 0.06); the chapel's board
too (it is in the same panel; at 0.06 the dark wood barely shows).
python3 far_tex.py [out_dir] -> T_Far_Panel_BaseColor.png, far_panel_regions.json"""
import os, sys, json
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pxfont as F
import van2_tex as VT
import kpp_tex as KT                                       # the umlaut glyphs (patched into pxfont on import)
import road_tex as RTX
import main_tex as MT

N = 512
PPM = 160.0
INK, WHITE = (26, 24, 22), (236, 232, 220)
RED = (196, 36, 26)
BLUE = (34, 60, 108)
YELLOW = (236, 190, 30)
GREEN = (28, 102, 58)


def _px(m):
    return int(round(m * PPM))


SIZES = [('dish', _px(1.03), _px(0.42)), ('radome', _px(0.60), _px(0.36)), ('relay', _px(0.80), _px(0.22)),
         ('meteo', _px(0.72), _px(0.26)), ('lookout', _px(0.74), _px(0.36)), ('pump', _px(1.04), _px(0.244)),
         ('chapel', _px(1.60), _px(0.254))]
REG = MT.pack(SIZES, n=N)


def uv(name, n=N):
    return VT.uv(REG[name], n)


def _tri(img, cx, top, h, k=0.62):
    for j in range(h):
        half = (j + 1) * k
        F.rect(img, int(cx - half), top + j, int(cx + half), top + j, INK)
    for j in range(3, h - 2):
        half = (j - 2) * k - 0.5
        if half > 0:
            F.rect(img, int(cx - half), top + j, int(cx + half), top + j, YELLOW)


def draw_dish(img):
    x0, y0, x1, y1 = REG['dish']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, WHITE)
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, RED, 2)
    _tri(img, x0 + 26, y0 + 12, 30)                              # the radiation warning: a triangle with rays
    cx, cy = x0 + 26, y0 + 32
    F.rect(img, cx - 1, cy - 1, cx, cy, INK)
    for dx, dy in ((-5, -2), (5, -2), (-7, 3), (7, 3), (-4, 6), (4, 6)):
        F.rect(img, cx + dx, cy + dy, cx + dx, cy + dy, INK)
    tx = (x0 + 50 + x1 - 6) / 2
    RTX.prop_text(img, tx, y0 + 13, 'ANTENNENANLAGE', F.F57, INK, scale=1)
    RTX.prop_text(img, tx, y0 + 23, 'ANTENNA SITE', F.F35, (70, 66, 60), scale=1)
    F.rect(img, x0 + 54, y0 + 31, x1 - 10, y0 + 31, (150, 146, 138))
    RTX.prop_text(img, tx, y0 + 41, 'VORSICHT', F.F57, RED, scale=1)
    RTX.prop_text(img, tx, y0 + 50, 'HOCHFREQUENZ', F.F57, RED, scale=1)
    RTX.prop_text(img, tx, y0 + 59, 'CAUTION: RF RADIATION', F.F35, (70, 66, 60), scale=1)
    RTX._wear(img, (x0, y0, x1, y1), 91, fade=0.06, grime=(118, 104, 84))
    KT._age(img, (x0, y0, x1, y1), 92, 30, 0.25, (120, 74, 44))


def draw_radome(img):
    x0, y0, x1, y1 = REG['radome']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, WHITE)
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, RED, 2)
    cx = (x0 + x1) / 2
    RTX.prop_text(img, cx, y0 + 11, 'RADARSTATION', F.F57, INK, scale=1)
    RTX.prop_text(img, cx, y0 + 20, 'RADAR STATION', F.F35, (70, 66, 60), scale=1)
    F.rect(img, x0 + 8, y0 + 26, x1 - 9, y0 + 41, RED)
    RTX.prop_text(img, cx, y0 + 31, 'ZUTRITT VERBOTEN', F.F35, WHITE, scale=1)
    RTX.prop_text(img, cx, y0 + 38, 'NO ENTRY', F.F35, (240, 210, 200), scale=1)
    RTX._wear(img, (x0, y0, x1, y1), 93, fade=0.06, grime=(118, 104, 84))
    KT._age(img, (x0, y0, x1, y1), 94, 20, 0.25, (120, 74, 44))


def draw_relay(img):
    x0, y0, x1, y1 = REG['relay']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, WHITE)
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, RED, 2)
    cx = (x0 + x1) / 2
    RTX.prop_text(img, cx, y0 + 11, 'FUNKSTATION - ZUTRITT VERBOTEN', F.F35, INK, scale=1)
    RTX.prop_text(img, cx, y0 + 22, 'RADIO RELAY STATION - NO ENTRY', F.F35, (70, 66, 60), scale=1)
    RTX._wear(img, (x0, y0, x1, y1), 95, fade=0.06, grime=(118, 104, 84))
    KT._age(img, (x0, y0, x1, y1), 96, 20, 0.30, (120, 74, 44))


def draw_meteo(img):
    x0, y0, x1, y1 = REG['meteo']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, GREEN)
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, (232, 236, 230), 1)
    cx = (x0 + x1) / 2
    RTX.prop_text(img, cx, y0 + 15, 'WETTERSTATION', F.F57, (238, 240, 234), scale=1)
    RTX.prop_text(img, cx, y0 + 27, 'WEATHER STATION', F.F35, (200, 222, 204), scale=1)
    RTX._wear(img, (x0, y0, x1, y1), 97, fade=0.12, grime=(80, 84, 72))


def draw_lookout(img):
    x0, y0, x1, y1 = REG['lookout']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (120, 70, 42))                 # the forestry's brown
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, (236, 230, 220), 1)
    cx = (x0 + x1) / 2
    RTX.prop_text(img, cx, y0 + 11, 'AUSSICHTSTURM', F.F57, (240, 236, 228), scale=1)
    RTX.prop_text(img, cx, y0 + 20, 'LOOKOUT TOWER', F.F35, (226, 208, 188), scale=1)
    F.rect(img, x0 + 8, y0 + 26, x1 - 9, y0 + 26, (226, 208, 188))
    RTX.prop_text(img, cx, y0 + 33, 'BETRETEN AUF EIGENE GEFAHR', F.F35, (240, 236, 228), scale=1)
    RTX.prop_text(img, cx, y0 + 42, 'CLIMB AT YOUR OWN RISK', F.F35, (226, 208, 188), scale=1)
    RTX._wear(img, (x0, y0, x1, y1), 98, fade=0.12, grime=(80, 70, 56))


def draw_pump(img):
    x0, y0, x1, y1 = REG['pump']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, BLUE)
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, (232, 234, 236), 1)
    cx = (x0 + x1) / 2
    RTX.prop_text(img, cx, y0 + 13, 'PUMPSTATION', F.F57, (236, 238, 240), scale=2)
    RTX.prop_text(img, cx, y0 + 29, 'PUMP STATION', F.F57, (196, 206, 226), scale=1)
    for (sx, sy) in ((x0 + 5, y0 + 5), (x1 - 6, y0 + 5), (x0 + 5, y1 - 6), (x1 - 6, y1 - 6)):     # the enamel's screws
        F.rect(img, sx, sy, sx, sy, (150, 156, 170))
    RTX._wear(img, (x0, y0, x1, y1), 99, fade=0.10, grime=(80, 84, 72))
    KT._age(img, (x0, y0, x1, y1), 100, 26, 0.35, (110, 70, 40))


def draw_chapel(img):
    x0, y0, x1, y1 = REG['chapel']
    rng = np.random.default_rng(101)
    for y in range(y0, y1):                                             # dark stained board, grain along x
        for x in range(x0, x1):
            g = 0.86 + 0.14 * np.sin((x - x0) * 0.21 + np.sin(y * 0.7) * 2.0) + 0.06 * rng.random()
            img[y, x] = np.clip(np.array((70, 52, 36)) * g, 0, 255)
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, (46, 34, 24), 1)
    cx = (x0 + x1) / 2
    RTX.prop_text(img, cx - 40, y0 + 14, 'WALDKAPELLE', F.F57, (206, 186, 150), scale=2)
    RTX.prop_text(img, cx + 76, y0 + 14, 'FOREST CHAPEL', F.F57, (176, 156, 120), scale=1)
    for (sx, sy) in ((x0 + 4, y0 + 20), (x1 - 5, y0 + 20)):
        F.rect(img, sx, sy, sx + 1, sy + 1, (40, 38, 36))
    RTX._wear(img, (x0, y0, x1, y1), 102, fade=0.08, grime=(60, 64, 44))


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (128, 128, 124)
    for fn in (draw_dish, draw_radome, draw_relay, draw_meteo, draw_lookout, draw_pump, draw_chapel):
        fn(img)
    p = os.path.join(out, 'T_Far_Panel_BaseColor.png')
    Image.fromarray(img, 'RGB').save(p)
    json.dump(dict(size=N, ppm=PPM, regions={k: list(v) for k, v in REG.items()}),
              open(os.path.join(out, 'far_panel_regions.json'), 'w'), indent=1)
    return p


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'far')
    print(build(o))
