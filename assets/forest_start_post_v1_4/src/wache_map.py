"""The site plan's texture T_Start_WacheMap.png (the card Wache_Map in the frame on the house's road wall): the Forest map seen
from above (tools/snow_qa/topview.py over the whole land: X -600..1200, Z -1200..600, +X right, +Z up) shrunk onto the plan,
the post marked red, on aged paper under the title LAGEPLAN. The panels' PSX step (snow_style panel_signs_lenses, 160 px/m):
the picture to 32 colours with the Bayer 4x4 dither 1/24, the paper flat, the letters after the palette step (no dither).
python3.11 -I wache_map.py <top.png> <out.png> [x0 z1 size]   (the picture's world square: its left X, top Z and side, metres)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: F401  (psxlib needs Blender's modules)
import numpy as np
from PIL import Image
import psxlib as P
import pxfont as F

PPM = 160.0                                   # px per metre of the panels
CARD = (0.704, 0.788)                         # the card (m): wache_kit.MAPF inside the frame, 4 mm under it on each side
MAP_M = 0.62                                  # the picture's side on the card (m)
POST = (-515.5, 546.0)                        # the house in the scene, world X, Z (forest_start_post apply log 30.10)
PAPER, INK, RED = (236, 232, 220), (26, 26, 28), (196, 30, 24)


def main():
    a = sys.argv[1:]
    src, out = a[0], a[1]
    x0, z1, size = (float(v) for v in a[2:5]) if len(a) >= 5 else (-600.0, 600.0, 1800.0)
    W, H = int(round(CARD[0] * PPM)), int(round(CARD[1] * PPM))
    ms = int(round(MAP_M * PPM))
    mx, my = (W - ms) // 2, H - ms - (W - ms) // 2
    # the picture: area mean down to the plan, 32 colours with the ordered dither
    top = Image.open(src).convert('RGB').resize((ms, ms), Image.BOX)
    s = np.asarray(top, np.float32) / 255.0
    s = np.clip((s - 0.5) * 1.15 + 0.5, 0, 1)                            # a printed plan: a little more contrast
    pal = P.kmeans(s.reshape(-1, 3), 32)
    bay = np.tile(P.BAYER4, (ms // 4 + 1, ms // 4 + 1))[:ms, :ms][..., None]
    sd = np.clip(s + (bay - 0.5) / 24.0, 0, 1).reshape(-1, 3)
    idx = np.argmin(((sd[:, None, :] - pal[None, :, :]) ** 2).sum(2), 1)
    pic = (pal[idx].reshape(ms, ms, 3) * 255 + 0.5).astype(np.uint8)
    # the card: flat paper, a few aged pixels, the picture in a 1 px ink line, the post as a red dot, the title
    img = np.zeros((H, W, 3), np.uint8)
    img[:] = PAPER
    rng = np.random.default_rng(1991)
    for (yy, xx) in zip(rng.integers(0, H, 46), rng.integers(0, W, 46)):
        img[yy, xx] = (222, 216, 200) if rng.random() < 0.7 else (206, 198, 176)
    img[my - 1:my + ms + 1, mx - 1:mx + ms + 1] = INK
    img[my:my + ms, mx:mx + ms] = pic
    px = mx + int((POST[0] - x0) / size * ms)
    py = my + int((z1 - POST[1]) / size * ms)
    img[max(my, py - 1):py + 2, max(mx, px - 1):px + 2] = RED
    t = F.text_mask('LAGEPLAN', F.F57, 2)
    ty, tx = (my - 1 - t.shape[0]) // 2, (W - t.shape[1]) // 2
    img[ty:ty + t.shape[0], tx:tx + t.shape[1]][t] = INK
    Image.fromarray(img, 'RGB').save(out)
    print(out, (W, H), 'map', ms, 'px at', round(ms / MAP_M, 1), 'px/m; post at', (px, py))


main()
