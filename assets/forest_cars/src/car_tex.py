"""Panel atlas of the forest's abandoned cars (256 x 128 RGBA, pixel art, point-filtered, alpha cut-out): the cracks on the
wreck's windscreen - a star from an impact low on the passenger side, radial cracks and a few rings, white with grey edges.
python3 car_tex.py [out_dir] -> T_CAR_Panel_BaseColor.png (RGBA), T_CAR_Panel_Emission.png"""
import os, sys, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 256, 128
REG = {'crack': (0, 0, 192, 128)}


def uv(name):
    x0, y0, x1, y1 = REG[name]
    return ((x0 + 0.5) / W, 1 - (y1 - 0.5) / H, (x1 - 0.5) / W, 1 - (y0 + 0.5) / H)


def _line(a, x0, y0, x1, y1, v):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n + 1):
        x = int(round(x0 + (x1 - x0) * i / n))
        y = int(round(y0 + (y1 - y0) * i / n))
        if 0 <= x < a.shape[1] and 0 <= y < a.shape[0]:
            a[y, x] = max(a[y, x], v)


def build(out):
    os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(83)
    x0, y0, x1, y1 = REG['crack']
    a = np.zeros((H, W), np.float32)
    cx, cy = x0 + 132, y0 + 84                                   # the impact (image space: y down; the quad's low passenger side)
    for k in range(13):                                          # radial cracks, each a jagged walk
        ang = 2 * math.pi * k / 13 + rng.uniform(-0.2, 0.2)
        x, y = cx, cy
        L = rng.uniform(35, 95)
        step = 0
        while step < L:
            ang += rng.uniform(-0.35, 0.35)
            nx, ny = x + math.cos(ang) * 4, y + math.sin(ang) * 4
            _line(a, x, y, nx, ny, 1.0)
            x, y = nx, ny
            step += 4
            if rng.random() < 0.08:                              # a branch
                b = ang + rng.choice([-0.8, 0.8])
                _line(a, x, y, x + math.cos(b) * 12, y + math.sin(b) * 12, 0.8)
    for r in (7, 15, 26):                                        # rings round the impact, broken
        seg = 18
        for i in range(seg):
            if rng.random() < 0.3:
                continue
            t0, t1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
            rr = r + rng.uniform(-2, 2)
            _line(a, cx + rr * math.cos(t0), cy + rr * math.sin(t0) * 0.8, cx + rr * math.cos(t1), cy + rr * math.sin(t1) * 0.8, 0.9)
    for dx in range(-3, 4):                                      # the crushed spot
        for dy in range(-3, 4):
            if dx * dx + dy * dy <= 9:
                a[cy + dy, cx + dx] = 1.0
    img = np.zeros((H, W, 4), np.uint8)
    shade = (200 + rng.integers(0, 40, (H, W))).astype(np.uint8)
    img[..., 0] = shade
    img[..., 1] = shade
    img[..., 2] = np.minimum(255, shade.astype(int) + 8).astype(np.uint8)
    img[..., 3] = np.where(a > 0.5, 255, 0).astype(np.uint8)
    pb, pe = os.path.join(out, 'T_CAR_Panel_BaseColor.png'), os.path.join(out, 'T_CAR_Panel_Emission.png')
    Image.fromarray(img, 'RGBA').save(pb)
    Image.fromarray(np.zeros((H, W, 3), np.uint8)).save(pe)
    return pb, pe


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'cars')))
