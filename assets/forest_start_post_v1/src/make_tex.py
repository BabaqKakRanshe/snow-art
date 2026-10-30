"""textures of the start post concept (pixel art like the project's *_px textures, 32 px per metre):
T_SP_Plaster_px.png - grey rendered brick (Wachhaus walls, 4 x 4 m tile, damp band at the bottom, brick where the render fell off)
T_SP_Plate_px.png   - the SPERRGEBIET plate cut from T_Fence_Panel_A_px.png (zone fence plates)
python3 -I make_tex.py"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage

D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, 'tex')
rng = np.random.default_rng(2910)
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def noise(n, s):
    return ndimage.gaussian_filter(rng.standard_normal((n, n)), s, mode='wrap')


def norm(a):
    return (a - a.min()) / (a.max() - a.min() + 1e-9)


def quant(val, pal):
    """val 0..1 -> palette index with 4x4 Bayer dithering"""
    n = len(pal)
    t = np.tile(BAYER, (val.shape[0] // 4, val.shape[1] // 4))
    k = np.clip((val * (n - 1) + t - 0.5).round(), 0, n - 1).astype(int)
    return np.array(pal, np.uint8)[k]


def plaster():
    N = 128                                   # 4 m
    v = norm(noise(N, 10)) * 0.55 + norm(noise(N, 3)) * 0.3 + norm(noise(N, 1)) * 0.15
    yy = np.arange(N)[:, None] * np.ones((1, N))          # row 0 = top of the picture = 4 m up; bottom rows = ground
    h = (N - 1 - yy) / 32.0                                # metres over the ground
    damp = np.clip(1 - (h - 0.2) / 0.45, 0, 1) * (0.75 + 0.25 * norm(noise(N, 2)))
    streak = np.clip(norm(ndimage.gaussian_filter(rng.standard_normal((N, N)), (12, 1.2), mode='wrap')) - 0.62, 0, 1) * 2.2
    val = np.clip(0.62 * v + 0.3 - 0.42 * damp - 0.25 * streak * (h > 1.0), 0, 1)
    pal = [(78, 77, 74), (98, 97, 93), (118, 117, 112), (136, 135, 129), (152, 151, 145), (166, 165, 158)]
    img = quant(val, pal)
    # brick where the render fell off: two patches
    for (cx, cy, rw, rh) in ((100, 96, 11, 6),):
        Y_, X_ = np.ogrid[:N, :N]
        m = (((X_ - cx) / rw) ** 2 + ((Y_ - cy) / rh) ** 2 + 1.1 * norm(noise(N, 2.5)) - 0.55) < 1.0
        for y in range(N):
            for x in range(N):
                if not m[y, x]:
                    continue
                row = y // 3
                off = 4 if row % 2 else 0
                mortar = (y % 3 == 2) or ((x + off) % 8 == 7)
                if mortar:
                    img[y, x] = (120, 116, 108)
                else:
                    t = ((x + off) // 8 * 7 + row * 3) % 5
                    img[y, x] = [(110, 52, 38), (124, 60, 42), (98, 46, 34), (132, 70, 50), (116, 56, 40)][t]
        # broken render edge: a darker ring
        ring = ndimage.binary_dilation(m, iterations=1) & ~m
        img[ring] = (70, 69, 66)
    # cracks
    for _ in range(5):
        x, y = rng.integers(0, N, 2)
        for k in range(rng.integers(10, 28)):
            img[y % N, x % N] = (64, 63, 60)
            x += rng.integers(-1, 2); y += 1
    Image.fromarray(img, 'RGB').save(os.path.join(OUT, 'T_SP_Plaster_px.png'))


def plate():
    src = Image.open('/mnt/user-data/uploads/snow/source/world_sync/forest/map/textures/T_Fence_Panel_A_px.png').convert('RGB')
    a = np.asarray(src)
    # the SPERRGEBIET plate: the red-bordered panel at the bottom left
    x0, y0, x1, y1 = 2, 130, 157, 223
    src.crop((x0, y0, x1 + 1, y1 + 1)).save(os.path.join(OUT, 'T_SP_Plate_px.png'))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    plaster(); plate()
    print('ok')
