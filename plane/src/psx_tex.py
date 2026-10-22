"""PS1 / PSX lo-fi versions of the exterior atlases (Airframe, Wing, Details) from the v8 4K maps.
usage: python3 psx_tex.py <variant> [atlases=Airframe,Wing,Details]   (winter kit: KitCovers,KitProps)
variants (size, colours, dither):  a = 512 / 32 / none,  b = 512 / 64 / ordered 4x4,  c = 1024 / 64 / none
out tex/psx_<variant>/T_<atlas>_BaseColor.png (sRGB, palette-limited, AO + panel lines + seams baked in),
    T_<atlas>_MaskMap.png (R metal 0/1, G 1 = occlusion baked into the colour, B 1, A smoothness in 4 steps).
No normal map: PS1 had none; grooves and rivet rows read as 1-texel dark lines in the colour."""
import os, sys, json
import numpy as np
from PIL import Image
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'export', 'unity_v8', 'Assets', 'UtilityPlane', 'Textures')
VAR = sys.argv[1] if len(sys.argv) > 1 else 'b'
ATL = (sys.argv[2] if len(sys.argv) > 2 else 'Airframe,Wing,Details').split(',')
SPEC = {'a': (512, 32, 0.0), 'b': (512, 64, 1.0), 'c': (1024, 64, 0.0)}
SIZE, NCOL, DITHER = SPEC[VAR]
OUT = os.path.join(HERE, 'tex', f'psx_{VAR}')
os.makedirs(OUT, exist_ok=True)
COVER = {'Airframe': 'T8_A_id.npy', 'Wing': 'T8_W_id.npy'}       # coverage (channel 3) of the v8 livery atlases
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0


def s2l(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def l2s(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def blocks(a, f):
    """(H, W[, C]) -> (H/f, W/f, f*f[, C]) block view"""
    H, W = a.shape[:2]
    rest = a.shape[2:]
    b = a.reshape(H // f, f, W // f, f, *rest).swapaxes(1, 2)
    return b.reshape(H // f, W // f, f * f, *rest)


def kmeans(x, k, iters=18, seed=0):
    rng = np.random.default_rng(seed)
    c = x[rng.choice(len(x), k, replace=False)].copy()
    for _ in range(iters):
        d = ((x[:, None, :] - c[None, :, :]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            m = lab == j
            c[j] = x[m].mean(0) if m.any() else x[rng.integers(len(x))]
    return c


KIT_SRC = os.path.join(HERE, 'export', 'unity_kit', 'Assets', 'UtilityPlane', 'Textures')


def run(name):
    src = KIT_SRC if name.startswith('Kit') else SRC
    bc = np.asarray(Image.open(os.path.join(src, f'T_{name}_BaseColor.png')).convert('RGB'), np.float32) / 255
    mk = np.asarray(Image.open(os.path.join(src, f'T_{name}_MaskMap.png')).convert('RGBA'), np.float32) / 255
    H = bc.shape[0]
    f = H // SIZE
    cov = None
    if name in COVER:
        idm = np.load(os.path.join(HERE, 'tex', 'v8', COVER[name]), mmap_mode='r')
        cov = np.asarray(idm[..., 3]) > 0.5
    lin = s2l(bc)
    ao = mk[..., 1]
    # colour with the occlusion baked in (PS1 textures carried their own shading)
    shaded = lin * (0.25 + 0.75 * ao)[..., None]
    col = blocks(shaded, f).mean(2)
    # panel lines / seams: a groove a few 4K texels wide survives as a 1-texel dark line (low percentile per block)
    gb = blocks(ao, f)
    line = np.clip((gb.mean(2) - np.percentile(gb, 12, axis=2)) * 2.6, 0, 0.55)
    col = col * (1 - line)[..., None]
    metal = (blocks(mk[..., 0], f).mean(2) > 0.5).astype(np.float32)
    smooth = np.round(blocks(mk[..., 3], f).mean(2) * 0.55 * 3) / 3          # 4 steps, duller than v8
    covered = np.ones(col.shape[:2], bool) if cov is None else blocks(cov, f).mean(2) > 0.25
    # palette: k-means in sRGB on covered texels, ordered dither before the nearest-colour pick
    s = l2s(col).reshape(-1, 3)
    samp = s[covered.reshape(-1)]
    samp = samp[np.random.default_rng(1).choice(len(samp), min(len(samp), 60000), replace=False)]
    pal = kmeans(samp, NCOL)
    if DITHER:
        n = col.shape[0]
        bay = np.tile(BAYER4, (n // 4, n // 4)).reshape(-1, 1)
        step = 1.0 / 24.0                                              # ~ one 5-bit level of the PS1 frame buffer
        s_d = np.clip(s + (bay - 0.5) * step * DITHER, 0, 1)
    else:
        s_d = s
    idx = np.empty(len(s_d), np.int32)
    for i in range(0, len(s_d), 65536):
        idx[i:i + 65536] = ((s_d[i:i + 65536, None, :] - pal[None]) ** 2).sum(-1).argmin(1)
    q = pal[idx].reshape(col.shape)
    # padding: uncovered texels take the nearest covered colour (no bleeding of random colours into mips)
    if not covered.all():
        ii = ndimage.distance_transform_edt(~covered, return_distances=False, return_indices=True)
        q = q[ii[0], ii[1]]
        metal = metal[ii[0], ii[1]]
        smooth = smooth[ii[0], ii[1]]
    Image.fromarray((q * 255 + 0.5).astype(np.uint8), 'RGB').save(os.path.join(OUT, f'T_{name}_BaseColor.png'))
    mask = np.dstack([metal, np.ones_like(metal), np.ones_like(metal), smooth])
    Image.fromarray((mask * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(OUT, f'T_{name}_MaskMap.png'))
    print(name, 'size', SIZE, 'colours', len(np.unique(idx)), 'dither', DITHER, flush=True)


for a in ATL:
    run(a)
json.dump(dict(variant=VAR, size=SIZE, colours=NCOL, dither=DITHER), open(os.path.join(OUT, 'psx.json'), 'w'))
