"""PSX tile textures for the van concept (plane recipe: palette per texture, Bayer 4x4, shading and wear painted
into the colour, point filtering in the material).  python3 tex_van.py -> tex/*.png"""
import os, math
import numpy as np
from PIL import Image
from scipy import ndimage

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tex')
os.makedirs(OUT, exist_ok=True)
RNG = np.random.default_rng(11)
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0


def noise(n, scale, seed, m=None):
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
            msk = lab == j
            if msk.any():
                c[j] = x[msk].mean(0)
    return c


def psx(img, ncol=32, amp=1 / 24, name=None):
    H, W, _ = img.shape
    img = np.clip(img, 0, 1)
    pal = kmeans(img.reshape(-1, 3)[::max(1, H * W // 6000)], ncol)
    th = np.tile(BAYER4, (H // 4 + 1, W // 4 + 1))[:H, :W, None]
    d = np.clip(img + (th - 0.5) * amp * 2, 0, 1)
    lab = ((d.reshape(-1, 1, 3) - pal[None]) ** 2).sum(-1).argmin(1)
    out = pal[lab].reshape(H, W, 3)
    if name:
        Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, name + '.png'))
    return out


def col(rgb):
    return np.array(rgb, np.float32) / 255.0


def base(n, rgb, var=0.06, fine=0.03, seed=1, scale=16):
    b = col(rgb)[None, None, :] * np.ones((n, n, 1), np.float32)
    lo = noise(n, scale, seed)[..., None]
    hi = RNG.random((n, n, 1)).astype(np.float32)
    return b * (1 + (lo - 0.5) * var * 2 + (hi - 0.5) * fine * 2)


def streaks(n, seed, density=0.05, length=24):
    """vertical dirt runs (tileable)"""
    r = np.random.default_rng(seed)
    m = np.zeros((n, n), np.float32)
    for _ in range(int(n * density)):
        x = r.integers(0, n)
        y0 = r.integers(0, n)
        L = r.integers(length // 2, length)
        a = r.uniform(0.3, 1.0)
        for k in range(L):
            m[(y0 + k) % n, x] = max(m[(y0 + k) % n, x], a * (1 - k / L))
    return ndimage.gaussian_filter(m, (1.5, 0.5), mode='wrap')


def scratches(n, seed, count=40):
    r = np.random.default_rng(seed)
    m = np.zeros((n, n), np.float32)
    for _ in range(count):
        x, y = r.integers(0, n, 2)
        a = r.uniform(0, math.pi)
        L = r.integers(3, 12)
        for k in range(L):
            m[int(y + k * math.sin(a)) % n, int(x + k * math.cos(a)) % n] = 1
    return m


N = 128
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
# body paint (fallback for small painted parts; the body itself gets a baked atlas)
p = base(N, (140, 32, 25), 0.10, 0.04, 21, 32)
p *= (1 - 0.25 * streaks(N, 22)[..., None])
p = np.where((scratches(N, 23, 25) > 0)[..., None], p * 0.7 + col((90, 80, 70)) * 0.3, p)
psx(p, 24, name='paint_red')
w = base(N, (205, 203, 194), 0.06, 0.03, 24, 32) * (1 - 0.18 * streaks(N, 25)[..., None])
psx(w, 20, name='paint_white')

n = 64
yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
psx(base(n, (36, 36, 38), 0.10, 0.08, 31, 8), 12, name='rubber')
pl = base(n, (30, 31, 33), 0.08, 0.10, 32, 4)
psx(pl, 12, name='plastic_black')
c = base(n, (44, 45, 46), 0.12, 0.06, 33, 16)
c = np.where((scratches(n, 34, 30) > 0)[..., None], c * 1.6, c)
rust = (noise(n, 8, 35) > 0.78)[..., None]
c = np.where(rust, c * 0.6 + col((92, 52, 30)) * 0.4, c)
psx(c, 16, name='chassis_dark')
st = base(n, (120, 122, 124), 0.10, 0.08, 36, 8)
st = np.where((scratches(n, 37, 40) > 0)[..., None], st * 1.25, st)
psx(st, 14, name='steel_worn')
psx(base(n, (58, 60, 62), 0.08, 0.05, 38, 8), 12, name='rim_grey')
wd = base(n, (138, 104, 66), 0.05, 0.04, 39)
wd = np.where(((yy % 16) < 1)[..., None], wd * 0.55, wd)
wd *= (0.92 + 0.08 * np.sin(xx / 2.2 + noise(n, 8, 40) * 5))[..., None]
psx(wd, 14, name='wood_crate')
psx(base(n, (86, 90, 66), 0.08, 0.06, 41, 8), 12, name='canvas')

# interior: beige leatherette with fine grain, small diamond tufting (10 cm at 160 px/m), pine boards
lv = base(n, (176, 150, 112), 0.05, 0.05, 51, 8)
psx(lv, 14, name='vinyl_beige')
u = ((xx + yy) % 16) / 16.0
v = ((xx - yy) % 16) / 16.0
tri = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
puff = np.clip(tri / 0.25, 0, 1) ** 0.5
q = col((112, 74, 44))[None, None] * (0.68 + 0.38 * puff[..., None])
q = np.where((tri < 0.04)[..., None], q * 0.6, q)
q *= (1 + (RNG.random((n, n, 1)) - 0.5) * 0.06)
psx(q, 16, name='vinyl_tufted')
n2 = 128
yy2, xx2 = np.mgrid[0:n2, 0:n2].astype(np.float32)
bw = 12                                                  # board width in texels (9 cm at 130 px/m)
board = (xx2 // bw).astype(int)
tone = np.random.default_rng(52).uniform(0.86, 1.10, 64)[board % 64]
pine = col((170, 136, 98))[None, None] * tone[..., None]
grain = np.sin((xx2 % bw) * 0.9 + noise(n2, 16, 53) * 9 + board * 1.7)
pine *= (0.93 + 0.06 * grain)[..., None]
pine = np.where(((xx2 % bw) < 1)[..., None], pine * 0.45, pine)
knots = (noise(n2, 8, 54) > 0.93)[..., None]
pine = np.where(knots, pine * 0.62, pine)
psx(pine, 20, name='pine_boards')
# floor: worn linoleum with a faded pattern
fl = base(n, (96, 84, 70), 0.10, 0.06, 55, 16)
fl = np.where((((xx // 8) + (yy // 8)) % 2 == 0)[..., None], fl * 0.92, fl)
psx(fl, 12, name='linoleum')
# fabrics: wool blanket (red-green check), curtain (faded floral stripes), seat cloth
bl = base(n, (126, 40, 34), 0.04, 0.06, 56, 8)
cx = ((xx // 8) % 2 == 0)[..., None]
cy = ((yy // 8) % 2 == 0)[..., None]
bl = np.where(cx & cy, bl * 0.5 + col((34, 62, 40)) * 0.5, bl)
bl = np.where(cx ^ cy, bl * 0.82, bl)
psx(bl, 14, name='blanket')
cu = base(n, (170, 150, 104), 0.04, 0.05, 57, 8)
stripe = ((xx % 16) < 3)[..., None]
cu = np.where(stripe, cu * 0.7 + col((120, 50, 40)) * 0.3, cu)
cu *= (0.82 + 0.18 * np.sin(xx / 2.8))[..., None]
psx(cu, 14, name='curtain')
sc = base(n, (70, 74, 82), 0.05, 0.08, 58, 4)
sc = np.where((((xx // 4) + (yy // 4)) % 2 == 0)[..., None], sc * 0.9, sc)
psx(sc, 12, name='seat_cloth')
psx(base(n, (40, 38, 36), 0.10, 0.07, 59, 8), 10, name='iron')
psx(base(n, (200, 200, 196), 0.04, 0.04, 60, 8), 10, name='headliner')
cp = base(n, (150, 146, 134), 0.06, 0.05, 61, 16)
cp = np.where((scratches(n, 62, 14) > 0)[..., None], cp * 0.8, cp)
psx(cp, 14, name='cab_paint')
print('textures', sorted(os.listdir(OUT)))
