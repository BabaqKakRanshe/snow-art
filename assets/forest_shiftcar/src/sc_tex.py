"""Panel atlas of the previous shift's car (256 x 64 RGBA, pixel art, point-filtered, alpha cut-out): the station's lettering on
both front doors - RADIOOBSERVATORIUM over HOHENMOOS, off-white, chipped; only the letters are opaque (the door's own paint shows
round them; 1.0 had a green plate behind the letters).
python3 sc_tex.py [out_dir] -> T_SC_Panel_BaseColor.png (RGBA), T_SC_Panel_Emission.png"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxfont as F

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, PPM = 256, 64, 160.0
REG = {'door': (0, 0, 128, 36)}
WHITE = (212, 210, 196)


def uv(name):
    x0, y0, x1, y1 = REG[name]
    return ((x0 + 0.5) / W, 1 - (y1 - 0.5) / H, (x1 - 0.5) / W, 1 - (y0 + 0.5) / H)


def size_m(name):
    x0, y0, x1, y1 = REG[name]
    return (x1 - x0) / PPM, (y1 - y0) / PPM


def build(out):
    os.makedirs(out, exist_ok=True)
    ink = np.zeros((H, W, 3), np.uint8)
    x0, y0, x1, y1 = REG['door']
    cx = (x0 + x1) // 2
    F.text(ink, cx, y0 + 11, 'RADIOOBSERVATORIUM', F.F57, (255, 255, 255))
    F.text(ink, cx, y0 + 23, 'HOHENMOOS', F.F57, (255, 255, 255))
    a = (ink.max(axis=2) > 0)
    rng = np.random.default_rng(71)
    for _ in range(70):                                           # chipped letters: the paint shows through
        a[rng.integers(y0, y1), rng.integers(x0, x1)] = False
    img = np.zeros((H, W, 4), np.uint8)
    img[..., :3] = WHITE
    img[..., 3] = np.where(a, 255, 0)
    shade = rng.integers(0, 18, (H, W))
    img[..., :3] = np.clip(img[..., :3].astype(int) - shade[..., None], 0, 255)
    pb, pe = os.path.join(out, 'T_SC_Panel_BaseColor.png'), os.path.join(out, 'T_SC_Panel_Emission.png')
    Image.fromarray(img, 'RGBA').save(pb)
    Image.fromarray(np.zeros((H, W, 3), np.uint8)).save(pe)
    return pb, pe


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'sc')))
