"""v12: PS1 / PSX versions of the interior atlases (Cockpit, Interior, Floor, Seats, Fittings) from the v9 sources
(4096 / Fittings 2048), the same recipe as the exterior (v9) with three interior-specific changes:
  - shading: small-scale AO (aos, 0.22 m; Fittings 0.12 m) at full strength, the cabin-scale AO (aol, sky through the
    windows) only gently, both normalised to the open surfaces (p80 = 1), so flat panels keep their colour and only
    crevices, contact areas and corners darken (the cabin lamps still light the room in Unity);
  - block means only over the dominant UV island of each block (no colour bleeding between neighbouring islands, no
    black gutter at island edges);
  - every block a UV island touches is "covered" (thin parts keep their own colour at 512).
AO is smoothed inside the islands (no bake noise); metal in 4 steps on a lightly smoothed map.
Then: grooves -> 1-texel dark lines (AO percentile), 64-colour k-means palette in sRGB, Bayer 4x4 dither between the
two nearest palette colours (flat areas stay flat),
mask R metal 4 steps (exterior: 0/1), G 1, B 1, A smoothness 4 steps x 0.55, padding by distance transform.
python3 psx_interior.py <out_dir> <Atlas=size,...>   e.g.  out Cockpit=1024,Interior=1024"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
SRC = '/home/claude/plane/export/unity_v9/Assets/UtilityPlane/Textures'
TEX8 = '/home/claude/plane/tex/v8'
TEX9 = '/home/claude/plane/tex/v9'
UVT = '/home/claude/plane/v12/work/uvtris_v11.npz'
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0
AO_SRC = {'Cockpit': ('T8_C_aos', 'T8_C_aol'), 'Interior': ('T8_I_aos', 'T8_I_aol'), 'Floor': ('T8_F_aos', 'T8_F_aol'),
          'Seats': ('T8_S_aos', 'T8_S_aol'), 'Fittings': ('F9_ao', 'F9_aol')}
NCOL, DITHER = 64, 1.0
AOL_FLOOR = 0.85                                   # cabin-scale AO range kept in the colour: 0.85 .. 1


def s2l(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def l2s(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def blocks(a, f):
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


def nearest(x, pal):
    idx = np.empty(len(x), np.int32)
    for i in range(0, len(x), 65536):
        idx[i:i + 65536] = ((x[i:i + 65536, None, :] - pal[None]) ** 2).sum(-1).argmin(1)
    return idx


def ordered_dither(x, pal, bay):
    """Bayer 4 x 4 dither between the two nearest palette colours: a colour that sits on a palette entry stays flat,
    one between two entries becomes their 4 x 4 mix in proportion (the naive "add noise, take nearest" dither of the
    exterior puts a checkerboard on every flat panel, which up close in the cabin reads as noise)"""
    out = np.empty(len(x), np.int32)
    for i in range(0, len(x), 65536):
        c = x[i:i + 65536]
        d = ((c[:, None, :] - pal[None]) ** 2).sum(-1)
        o = np.argsort(d, axis=1)[:, :2]
        p1, p2 = pal[o[:, 0]], pal[o[:, 1]]
        seg = p2 - p1
        t = np.clip(((c - p1) * seg).sum(1) / np.maximum((seg * seg).sum(1), 1e-9), 0, 1)
        out[i:i + 65536] = np.where(t > bay[i:i + 65536], o[:, 1], o[:, 0])
    return out


def coverage(mat, S):
    tris = np.load(UVT)[mat]
    im = Image.new('L', (S, S), 0)
    dr = ImageDraw.Draw(im)
    for t in tris:
        dr.polygon([(u * S, (1 - v) * S) for u, v in t], fill=255, outline=255)
    return np.asarray(im) > 0


def load_ao(name, S):
    a_s, a_l = AO_SRC[name]
    aos = np.load(os.path.join(TEX8 if name != 'Fittings' else TEX9, a_s + '.npy')).astype(np.float32)[..., 0]
    aol = np.load(os.path.join(TEX8 if name != 'Fittings' else TEX9, a_l + '.npy')).astype(np.float32)[..., 0]
    up = lambda a: np.asarray(Image.fromarray(a, 'F').resize((S, S), Image.BILINEAR), np.float32)
    return up(aos), up(aol)


def dominant(lab_b):
    """lab_b (n, ff) island labels per block (0 = gutter) -> label covering most of each block (0 if none)"""
    s = np.sort(np.where(lab_b > 0, lab_b, -1), axis=1)
    run = np.ones(len(s), np.int32)
    best = np.where(s[:, 0] > 0, 1, 0).astype(np.int32)
    bl = np.where(s[:, 0] > 0, s[:, 0], 0)
    for i in range(1, s.shape[1]):
        same = (s[:, i] == s[:, i - 1]) & (s[:, i] > 0)
        run = np.where(same, run + 1, 1)
        upd = (s[:, i] > 0) & (run > best)
        best = np.where(upd, run, best)
        bl = np.where(upd, s[:, i], bl)
    return bl


def run(name, N, out):
    mat = 'M_' + name
    bc = np.asarray(Image.open(os.path.join(SRC, f'T_{name}_BaseColor.png')).convert('RGB'), np.float32) / 255
    mk = np.asarray(Image.open(os.path.join(SRC, f'T_{name}_MaskMap.png')).convert('RGBA'), np.float32) / 255
    S = bc.shape[0]
    f = S // N
    cov = coverage(mat, S)
    cov = ndimage.binary_dilation(cov, iterations=1)
    lab, nlab = ndimage.label(cov)
    aos, aol = load_ao(name, S)
    # the AO bakes are noisy (64 samples): smooth inside the islands (normalised Gaussian, ~1 output texel) so the
    # baked shading has no salt-and-pepper grain; the Bayer dither is the only pattern
    sig = 0.5 * S / N
    cf = cov.astype(np.float32)
    aos = ndimage.gaussian_filter(aos * cf, sig) / np.maximum(ndimage.gaussian_filter(cf, sig), 1e-4)
    # shading baked into the colour, normalised to the open surfaces
    s = 0.25 + 0.75 * np.clip(aos, 0, 1)
    s = np.clip(s / np.percentile(s[cov], 80), 0, 1)
    ref = np.percentile(aol[cov & (aol > 0.0005)], 92)
    t = AOL_FLOOR + (1 - AOL_FLOOR) * np.clip(aol / max(ref, 1e-3), 0, 1) ** 0.6
    t = np.clip(t / np.percentile(t[cov], 80), 0, 1)
    shade = s * t
    lin = s2l(bc) * shade[..., None]
    # dominant island per block
    lb = blocks(lab, f).reshape(N * N, f * f)
    dom = dominant(lb)
    m = (lb == dom[:, None]) & (dom[:, None] > 0)
    cnt = m.sum(1)
    covered = (cnt > 0).reshape(N, N)
    w = m.astype(np.float32)
    def bmean(a):
        ab = blocks(a, f).reshape(N * N, f * f, *a.shape[2:])
        if ab.ndim == 3:
            return ((ab * w[..., None]).sum(1) / np.maximum(cnt, 1)[:, None]).reshape(N, N, -1)
        return ((ab * w).sum(1) / np.maximum(cnt, 1)).reshape(N, N)
    col = bmean(lin)
    # grooves: AO percentile inside fully covered blocks (G of the v9 mask = aos x cabin AO)
    if f >= 4:
        gb = blocks(mk[..., 1], f).reshape(N * N, f * f)
        full = (cnt == f * f)
        line = np.zeros(N * N, np.float32)
        line[full] = np.clip((gb[full].mean(1) - np.percentile(gb[full], 12, axis=1)) * 2.6, 0, 0.55)
        col = col * (1 - line.reshape(N, N))[..., None]
    # metal in 4 steps (0, 1/3, 2/3, 1) on a lightly smoothed map: the interior has half-metal surfaces (the cargo
    # floor tread plate is ~0.7) that 0/1 would turn into black mirrors at night; smoothing keeps worn areas from
    # becoming a checkerboard of metal / paint texels
    metal = np.round(np.clip(ndimage.gaussian_filter(bmean(mk[..., 0]), 0.8), 0, 1) * 3) / 3
    smooth = np.round(bmean(mk[..., 3]) * 0.55 * 3) / 3
    # palette + dither
    srgb = l2s(col).reshape(-1, 3)
    samp = srgb[covered.reshape(-1)]
    samp = samp[np.random.default_rng(1).choice(len(samp), min(len(samp), 60000), replace=False)]
    pal = kmeans(samp, NCOL)
    bay = np.tile(BAYER4, (N // 4, N // 4)).reshape(-1)
    idx = ordered_dither(srgb, pal, bay) if DITHER else nearest(srgb, pal)
    q = pal[idx].reshape(N, N, 3)
    ii = ndimage.distance_transform_edt(~covered, return_distances=False, return_indices=True)
    q, metal, smooth = q[ii[0], ii[1]], metal[ii[0], ii[1]], smooth[ii[0], ii[1]]
    os.makedirs(out, exist_ok=True)
    Image.fromarray((q * 255 + 0.5).astype(np.uint8), 'RGB').save(os.path.join(out, f'T_{name}_BaseColor.png'), optimize=True)
    mask = np.dstack([metal, np.ones_like(metal), np.ones_like(metal), smooth])
    Image.fromarray((mask * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(out, f'T_{name}_MaskMap.png'), optimize=True)
    info = dict(atlas=name, size=N, source=S, block=f, colours=int(len(np.unique(idx[covered.reshape(-1)]))),
                islands=int(nlab), covered=round(float(covered.mean()), 4),
                shade_median=round(float(np.median(shade[cov])), 3))
    print(json.dumps(info), flush=True)
    return info


if __name__ == '__main__':
    out = sys.argv[1]
    spec = dict(kv.split('=') for kv in sys.argv[2].split(','))
    res = [run(k, int(v), out) for k, v in spec.items()]
    json.dump(res, open(os.path.join(out, 'psx_interior.json'), 'w'), indent=1)


def run_webbing(out, f=2, ncol=8):
    """tiled strap texture (512 x 128, twill): block mean / 2 -> 256 x 64 (keeps the twill), the weave relief of the normal map baked as
    light from above-left, 8 colours, Bayer dither; no normal map"""
    T = '/home/claude/plane/export/unity_v11/Assets/UtilityPlane/Textures/'
    bc = np.asarray(Image.open(T + 'T_Webbing_BaseColor.png').convert('RGB'), np.float32) / 255
    nm = np.asarray(Image.open(T + 'T_Webbing_Normal.png').convert('RGB'), np.float32) / 255 * 2 - 1
    L = np.array([-0.35, 0.45, 0.82]); L /= np.linalg.norm(L)
    shade = np.clip(0.55 + 0.45 * (nm @ L) / max(L[2], 1e-3), 0.6, 1.15)
    lin = s2l(bc) * shade[..., None]
    H, W = lin.shape[:2]
    col = lin.reshape(H // f, f, W // f, f, 3).mean((1, 3))
    srgb = l2s(col).reshape(-1, 3)
    pal = kmeans(srgb, ncol)
    h, w = col.shape[:2]
    bay = np.tile(BAYER4, (h // 4, w // 4)).reshape(-1)
    idx = ordered_dither(srgb, pal, bay)
    q = pal[idx].reshape(h, w, 3)
    Image.fromarray((q * 255 + 0.5).astype(np.uint8), 'RGB').save(os.path.join(out, 'T_Webbing_BaseColor.png'), optimize=True)
    print(json.dumps(dict(atlas='Webbing', size=[w, h], colours=int(len(np.unique(idx))))), flush=True)
