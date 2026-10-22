"""How a chain-link texture looks along a fence at the game's pixel size: a numpy renderer of one fence plane
(y = 0, x 0..80 m, z 0.03..2.2 m) seen obliquely from eye height, point sampling with mip maps chosen by the screen
footprint (as the GPU with Point filter: the nearest mip, no blend), alpha test 0.5.
Variants: the old texture (Updates 4-5: 1 px wires, 8 px lattice, black under the holes) with ordinary box mips;
the new texture with box mips; the new one with coverage-preserving mips (Unity's Mip Maps Preserve Coverage)."""
import sys, math
import numpy as np
from PIL import Image

W, H = int(sys.argv[3]) if len(sys.argv) > 3 else 640, int(sys.argv[4]) if len(sys.argv) > 4 else 360


def mips(rgba, preserve=False, ref=0.5):
    lv = [rgba.astype(np.float64) / 255.0]
    cov0 = (lv[0][..., 3] >= ref).mean()
    while lv[-1].shape[0] > 1:
        a = lv[-1]
        b = (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]) / 4.0
        if preserve:
            al = b[..., 3]
            lo, hi = 0.0, 1.0                                 # find the threshold whose coverage matches mip 0's
            for _ in range(30):
                mid = (lo + hi) / 2
                if (al >= mid).mean() > cov0:
                    lo = mid
                else:
                    hi = mid
            thr = max((lo + hi) / 2, 1e-4)
            b[..., 3] = np.clip(al * (ref / thr), 0, 1)
        lv.append(b)
    return lv


def render(levels, tile_m=0.5, cam=(-3.0, -4.0, 1.7), look=(20.0, 0.0, 1.2), fov=60.0, bg=None, lod_bias=0.0):
    C = np.array(cam)
    f = np.array(look) - C
    f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    th = math.tan(math.radians(fov) / 2)
    ys, xs = np.mgrid[0:H, 0:W]
    px = (2 * (xs + 0.5) / W - 1) * th * W / H
    py = (1 - 2 * (ys + 0.5) / H) * th
    d = f[None, None] + px[..., None] * r[None, None] + py[..., None] * u[None, None]
    t = -C[1] / d[..., 1]
    P = C[None, None] + d * t[..., None]
    X, Z = P[..., 0], P[..., 2]
    hit = (t > 0) & (X >= 0) & (X <= 80) & (Z >= 0.03) & (Z <= 2.2)
    n0 = levels[0].shape[0]
    U, V = X / tile_m * n0, Z / tile_m * n0
    dUx, dUy = np.gradient(U, axis=1), np.gradient(U, axis=0)
    dVx, dVy = np.gradient(V, axis=1), np.gradient(V, axis=0)
    rho = np.maximum(np.hypot(dUx, dVx), np.hypot(dUy, dVy))
    lam = np.log2(np.maximum(rho, 1e-6)) + lod_bias
    L = np.clip(np.floor(lam + 0.5), 0, len(levels) - 1).astype(int)
    out = bg.copy() if bg is not None else np.zeros((H, W, 3))
    for l in range(len(levels)):
        m = hit & (L == l)
        if not m.any():
            continue
        tex = levels[l]
        s = tex.shape[0]
        ui = np.floor(U[m] / n0 * s).astype(int) % s
        vi = (s - 1 - (np.floor(V[m] / n0 * s).astype(int) % s))
        c = tex[vi, ui]
        keep = c[:, 3] >= 0.5
        idx = np.argwhere(m)[keep]
        out[idx[:, 0], idx[:, 1]] = c[keep, :3]
    return out


def background():
    ys, xs = np.mgrid[0:H, 0:W]
    g = np.zeros((H, W, 3))
    g[...] = (0.16, 0.20, 0.14)
    g[ys > H * 0.62] = (0.30, 0.27, 0.22)
    rng = np.random.default_rng(3)
    g += rng.normal(0, 0.015, g.shape)
    return np.clip(g, 0, 1)


if __name__ == '__main__':
    old = np.array(Image.open(sys.argv[1]).convert('RGBA'))
    new = np.array(Image.open(sys.argv[2]).convert('RGBA'))
    bg = background()
    rows = [('было: тонкая сетка, обычные mip', render(mips(old), bg=bg)),
            ('стало: новая сетка, обычные mip', render(mips(new), bg=bg)),
            ('стало: новая сетка + Preserve Coverage', render(mips(new, preserve=True), bg=bg))]
    tiles = []
    for name, img in rows:
        im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
        tiles.append((name, im))
    out = sys.argv[5] if len(sys.argv) > 5 else 'moire.png'
    Wd = W * 2
    sheet = Image.new('RGB', (Wd, (H * 2 + 24) * len(tiles)), (20, 20, 20))
    from PIL import ImageDraw
    dr = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(tiles):
        y0 = i * (H * 2 + 24)
        sheet.paste(im.resize((W * 2, H * 2), Image.NEAREST), (0, y0 + 24))
        dr.text((6, y0 + 6), name, fill=(255, 220, 120))
    sheet.save(out)
    print('saved', out)
