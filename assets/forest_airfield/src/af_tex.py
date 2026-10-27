"""Panel atlas of the forest airfield (256 x 256, pixel art, point-filtered) on the explicit-UV objects:
  sign       the pointer at the turn-off from the east road (0.92 x 0.19 m): the station's stained arrow board, routed cream
             letters FLUGPLATZ, AIRFIELD under it (German first), weathered
  plate      the enamel plate on the hangar's bricked-up back opening (0.42 x 0.30 m): white with a red border,
             KEIN ZUTRITT over NO ENTRY
  l_edge     the edge light's amber dome: ribbed glass, the lamp's glow in the middle
  l_thr      the threshold light's green dome, same pattern
  glow_warm  halo tile for the amber glow cards (emission only)
  glow_green halo tile for the green glow cards (emission only)
python3 af_tex.py [out_dir] -> T_AF_Panel_BaseColor.png, T_AF_Panel_Emission.png, af_panel_regions.json"""
import os, sys, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxfont as F
import van2_tex as VT

HERE = os.path.dirname(os.path.abspath(__file__))
N = 256
REG = {'sign': (0, 0, 192, 40), 'plate': (0, 48, 84, 108), 'l_edge': (192, 0, 224, 32), 'l_thr': (224, 0, 256, 32),
       'glow_warm': (192, 64, 256, 128), 'glow_green': (192, 128, 256, 192)}
BOARD, BOARD_D, CREAM = (70, 48, 30), (46, 32, 22), (226, 210, 160)
ENAMEL, RED, INK = (226, 224, 214), (176, 34, 30), (40, 36, 34)


def uv(name, n=N):
    return VT.uv(REG[name], n)


def _weather(img, reg, seed, n=140):
    x0, y0, x1, y1 = reg
    rng = np.random.default_rng(seed)
    for _ in range(n):
        xx_, yy_ = rng.integers(x0 + 1, x1 - 1), rng.integers(y0 + 1, y1 - 1)
        img[yy_, xx_] = (img[yy_, xx_] * 0.65 + np.array((120, 116, 104)) * 0.35).astype(np.uint8)


def draw_sign(img):
    """the station's pointer board (as the hut yard's RouteSign): FLUGPLATZ over AIRFIELD"""
    x0, y0, x1, y1 = REG['sign']
    yy, xx = np.mgrid[y0:y1, x0:x1]
    grain = 0.88 + 0.12 * np.sin(yy * 1.7 + np.sin(xx * 0.09) * 2.0) + 0.05 * ((xx * 7 + yy * 13) % 5 == 0)
    img[y0:y1, x0:x1] = np.clip(np.array(BOARD)[None, None] * grain[..., None], 0, 255).astype(np.uint8)
    F.frame(img, x0, y0, x1 - 1, y1 - 1, BOARD_D, 2)
    F.text(img, x0 + 92, y0 + 13, 'FLUGPLATZ', F.F57, CREAM, scale=2)
    F.text(img, x0 + 92, y0 + 31, 'AIRFIELD', F.F35, (190, 176, 132))
    _weather(img, REG['sign'], 41)


def draw_plate(img):
    """white enamel, red border: KEIN ZUTRITT / NO ENTRY; chipped to black at the corners and the screw holes"""
    x0, y0, x1, y1 = REG['plate']
    img[y0:y1, x0:x1] = ENAMEL
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, RED, 3)
    F.text(img, (x0 + x1) // 2, y0 + 24, 'KEIN ZUTRITT', F.F57, INK)
    F.text(img, (x0 + x1) // 2, y0 + 38, 'NO ENTRY', F.F35, RED)
    for cx, cy in ((x0 + 6, y0 + 6), (x1 - 7, y0 + 6), (x0 + 6, y1 - 7), (x1 - 7, y1 - 7)):
        F.disc(img, cx, cy, 1, (30, 30, 30))
    rng = np.random.default_rng(43)
    for _ in range(22):                                          # chips to the black steel
        cx, cy = rng.integers(x0 + 1, x1 - 2), rng.integers(y0 + 1, y1 - 2)
        img[cy:cy + rng.integers(1, 3), cx:cx + rng.integers(1, 3)] = (34, 32, 30)
    _weather(img, REG['plate'], 44, 80)


def draw_lens(img, emi, name, glass, glow):
    x0, y0, x1, y1 = REG[name]                                   # ribbed dome glass, the lamp's glow in the middle
    yy, xx = np.mgrid[y0:y1, x0:x1]
    v = (yy + 0.5 - y0) / (y1 - y0)
    rib = 0.78 + 0.22 * (np.mod(xx - x0, 3) < 1)
    bulb = np.exp(-((v - 0.45) / 0.24) ** 2)
    t = VT.BAYER[np.mod(yy, 4), np.mod(xx, 4)]
    base = np.floor((0.42 + 0.25 * bulb) * rib * 8 + t) / 8
    img[y0:y1, x0:x1] = (base[..., None] * np.array(glass)[None, None]).astype(np.uint8)
    e = np.clip(0.30 + 0.70 * bulb * rib, 0, 1)
    e = np.floor(e * 9 + t) / 9
    emi[y0:y1, x0:x1] = (e[..., None] * np.array(glow)[None, None]).astype(np.uint8)


def draw_glow(img, emi, name, col):
    x0, y0, x1, y1 = REG[name]
    yy, xx = np.mgrid[y0:y1, x0:x1]
    rr = np.hypot(xx + 0.5 - (x0 + x1) / 2, yy + 0.5 - (y0 + y1) / 2) / ((x1 - x0) / 2)
    g = np.clip(1 - rr, 0, 1) ** 1.6
    t = VT.BAYER[np.mod(yy, 4), np.mod(xx, 4)]
    g = np.floor(g * 10 + t) / 10
    g[rr > 0.97] = 0
    emi[y0:y1, x0:x1] = (g[..., None] * np.array(col)[None, None]).astype(np.uint8)
    img[y0:y1, x0:x1] = 0


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (16, 16, 16)
    emi = np.zeros_like(img)
    draw_sign(img)
    draw_plate(img)
    draw_lens(img, emi, 'l_edge', (220, 160, 40), (255, 196, 80))
    draw_lens(img, emi, 'l_thr', (40, 170, 70), (110, 255, 140))
    draw_glow(img, emi, 'glow_warm', (255, 190, 100))
    draw_glow(img, emi, 'glow_green', (120, 255, 150))
    pb, pe = os.path.join(out, 'T_AF_Panel_BaseColor.png'), os.path.join(out, 'T_AF_Panel_Emission.png')
    Image.fromarray(img).save(pb)
    Image.fromarray(emi).save(pe)
    json.dump(dict(size=N, regions=REG, sign_m=[0.92, 0.19], plate_m=[0.42, 0.30]),
              open(os.path.join(out, 'af_panel_regions.json'), 'w'), indent=1)
    return pb, pe


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'af')))
