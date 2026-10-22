"""PSX textures for the ground-vehicle concepts (same recipe as the plane: shading in the colour,
small palette per texture, ordered 4x4 Bayer dither, point filtering in the material).
python3 tex_gen.py -> tex/*.png"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tex')
os.makedirs(OUT, exist_ok=True)
RNG = np.random.default_rng(7)
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0


def noise(n, scale, seed):
    """tileable value noise in 0..1"""
    r = np.random.default_rng(seed)
    k = max(1, n // scale)
    g = r.random((k, k))
    z = ndimage.zoom(np.tile(g, (3, 3)), scale, order=3)[k * scale:2 * k * scale, k * scale:2 * k * scale]
    z = (z - z.min()) / (np.ptp(z) + 1e-6)
    return z[:n, :n]


def kmeans(x, k, iters=14, seed=0):
    r = np.random.default_rng(seed)
    c = x[r.choice(len(x), k, replace=False)].copy()
    for _ in range(iters):
        lab = ((x[:, None, :] - c[None]) ** 2).sum(-1).argmin(1)
        for j in range(k):
            m = lab == j
            if m.any():
                c[j] = x[m].mean(0)
    return c


def psx(img, ncol=24, amp=1 / 24, name=None):
    """img float sRGB (H, W, 3) 0..1 -> palette + Bayer, saved as PNG"""
    H, W, _ = img.shape
    img = np.clip(img, 0, 1)
    pal = kmeans(img.reshape(-1, 3)[::max(1, H * W // 4000)], ncol)
    th = np.tile(BAYER4, (H // 4 + 1, W // 4 + 1))[:H, :W, None]
    d = np.clip(img + (th - 0.5) * amp * 2, 0, 1)
    lab = ((d.reshape(-1, 1, 3) - pal[None]) ** 2).sum(-1).argmin(1)
    out = pal[lab].reshape(H, W, 3)
    if name:
        Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, name + '.png'))
    return out


def col(rgb):
    return np.array(rgb, np.float32) / 255.0


def flat(n, rgb, var=0.06, fine=0.03, seed=1, scale=16):
    base = col(rgb)[None, None, :] * np.ones((n, n, 1), np.float32)
    lo = noise(n, scale, seed)[..., None]
    hi = RNG.random((n, n, 1)).astype(np.float32)
    return base * (1 + (lo - 0.5) * var * 2 + (hi - 0.5) * fine * 2)


N = 64
# exterior paint (plane red / white band), chassis, metal, rubber
psx(flat(N, (150, 30, 24), 0.07, 0.035, 11), 16, name='paint_red')
psx(flat(N, (204, 204, 196), 0.05, 0.03, 12), 12, name='paint_white')
psx(flat(N, (52, 54, 56), 0.08, 0.04, 13), 12, name='paint_dark')
psx(flat(N, (128, 130, 132), 0.06, 0.05, 14), 12, name='metal')
psx(flat(N, (34, 34, 36), 0.10, 0.06, 15), 10, name='rubber')
psx(flat(N, (88, 92, 70), 0.08, 0.05, 16), 12, name='canvas')

# snow (ground) and packed snow / ruts
n = 128
s = flat(n, (222, 228, 238), 0.05, 0.035, 21, 32)
sp = (RNG.random((n, n)) > 0.985)[..., None]
s = np.where(sp, s * 1.06, s)
psx(s, 12, name='snow')
r = flat(n, (176, 178, 186), 0.10, 0.06, 22, 16)
psx(r, 14, name='snow_packed')

# spruce needles / bark
g = flat(N, (34, 58, 42), 0.18, 0.12, 31, 8)
streak = noise(N, 4, 32)[..., None]
psx(g * (0.8 + 0.4 * streak), 12, name='spruce')
psx(flat(N, (70, 52, 40), 0.12, 0.08, 33, 8), 10, name='bark')

# ---------------------------------------------------------------- interior
# quilted leatherette (дерматин на ватине): diamond tufting with buttons
y, x = np.mgrid[0:N, 0:N].astype(np.float32)
u = ((x + y) % 32) / 32.0
v = ((x - y) % 32) / 32.0
tri = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))      # 0 at seams, 0.25 in the middle of a cell
puff = np.clip(tri / 0.25, 0, 1) ** 0.6
q = col((128, 88, 50))[None, None] * (0.62 + 0.45 * puff[..., None])
seam = tri < 0.03
q = np.where(seam[..., None], q * 0.55, q)
btn = ((np.abs((x % 32) - 16) < 1.6) & (np.abs((y % 32) - 0) < 1.6)) | \
      ((np.abs((x % 32) - 0) < 1.6) & (np.abs((y % 32) - 16) < 1.6))
q = np.where(btn[..., None], col((60, 40, 24))[None, None], q)
q = q * (1 + (RNG.random((N, N, 1)) - 0.5) * 0.06)
psx(q, 16, name='quilt')

# pale interior paint (kung walls above the quilting), wood, floor mat, blanket, curtain, iron
psx(flat(N, (170, 182, 160), 0.06, 0.03, 41), 12, name='paint_interior')
w = flat(N, (156, 112, 70), 0.05, 0.03, 42)
grain = np.sin(y / 3.0 + noise(N, 8, 43) * 6)[..., None]
psx(w * (0.9 + 0.08 * grain), 14, name='wood')
m = flat(N, (46, 46, 44), 0.06, 0.05, 44)
rib = ((y % 8) < 2)[..., None]
psx(np.where(rib, m * 1.35, m), 8, name='floormat')
pl = flat(N, (120, 38, 32), 0.04, 0.05, 45)
cx = ((x // 8) % 2 == 0)[..., None]
cy = ((y // 8) % 2 == 0)[..., None]
pl = np.where(cx & cy, pl * 0.55 + col((30, 70, 40)) * 0.45, pl)
pl = np.where(cx ^ cy, pl * 0.8, pl)
pl = np.where(((x % 16) == 3)[..., None] | ((y % 16) == 3)[..., None], pl * 0.9 + 0.08, pl)
psx(pl, 14, name='blanket')
c = flat(N, (92, 112, 74), 0.04, 0.04, 46)
fold = (0.75 + 0.25 * np.sin(x / 2.6))[..., None]
psx(c * fold, 12, name='curtain')
psx(flat(N, (40, 38, 36), 0.10, 0.07, 47), 10, name='iron')

# paper map pinned on the wall
n = 128
mp = flat(n, (214, 204, 170), 0.05, 0.03, 51)
yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
h = noise(n, 32, 52)
for lv in np.linspace(0.15, 0.9, 9):
    mp = np.where((np.abs(h - lv) < 0.008)[..., None], mp * 0.7 + col((150, 90, 40)) * 0.3, mp)
mp = np.where(((xx % 32) < 1) [..., None] | ((yy % 32) < 1)[..., None], mp * 0.75 + col((60, 80, 140)) * 0.25, mp)
river = np.abs(yy - (60 + 18 * np.sin(xx / 17))) < 1.5
mp = np.where(river[..., None], col((70, 110, 170)), mp)
route = (np.abs(xx - (40 + yy * 0.5)) < 1.0) & (yy > 20) & (yy < 110)
mp = np.where(route[..., None], col((180, 30, 20)), mp)
psx(mp, 16, name='map')
print('textures:', sorted(os.listdir(OUT)))
