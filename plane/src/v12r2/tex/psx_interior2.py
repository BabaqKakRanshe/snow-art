"""v12 r2: stronger PS1 / PSX interior atlases (user: "сильнее PSX везде": bigger texels, fewer colours, more contrast,
so the interior reads as PSX at a glance like the exterior; the text atlas is not touched).
Sources as in v12 (v9 4096 maps, Fittings 2048; AO bakes of v8 / v9). Differences from v12 (tex/v12 psx_interior.py):
  - 512² (Fittings 256²): texels twice as large (cockpit 133, cabin 85, floor 76, seats 154, fittings 111 px per m);
  - 32 colours per atlas (v12: 64), k-means sampled with extra weight on saturated texels so small coloured parts
    (knobs, guards, labels on parts) keep their colour;
  - stronger baked shading: small-scale AO from 0.12 (v12 0.25), cabin AO 0.65..1 (v12 0.85..1);
  - painted PS1 shading from the geometry (per-texel world position and normal, work/geomaps_<N>.npz):
      top light (faces up lighter, faces down darker), creases (inside corners darker, outside edges lighter = wear),
      grime on the lower walls near the floor and in patches on the floor, world-space mottling (no seams);
  - local contrast (log luminance against its island-local blur) so every variation shows in the palette.
Then as v12: 4 x 4 Bayer dither between the two nearest palette colours, mask R metal 4 steps, G 1, B 1, A smoothness
4 steps x 0.55, padding by distance transform.
python3 psx_interior2.py <out_dir> <Atlas=size,...> [params.json]"""
import os, sys, json, zlib
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
SRC = '/home/claude/plane/export/unity_v9/Assets/UtilityPlane/Textures'
TEX8 = '/home/claude/plane/tex/v8'
TEX9 = '/home/claude/plane/tex/v9'
UVT = '/home/claude/plane/v12/work/uvtris_v11.npz'
GEO = '/home/claude/plane/v12r2/work/geomaps_%d.npz'
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0
AO_SRC = {'Cockpit': ('T8_C_aos', 'T8_C_aol'), 'Interior': ('T8_I_aos', 'T8_I_aol'), 'Floor': ('T8_F_aos', 'T8_F_aol'),
          'Seats': ('T8_S_aos', 'T8_S_aol'), 'Fittings': ('F9_ao', 'F9_aol')}
PX_PER_M_1024 = {'Cockpit': 265.6, 'Interior': 170.7, 'Floor': 152.6, 'Seats': 308.3, 'Fittings': 445.2}
FLOOR_Z = 1.074                                      # cabin floor, Blender world z (m)

P = dict(ncol=32, ncol_atlas={}, ao_floor=0.12, aol_floor=0.65, top=0.10, mottle1=0.18, mottle2=0.12,
         mottle_scale1=2.5, mottle_scale2=9.0, grime=0.30, grime_h=0.40, floor_patch=0.22, crease_dark=0.35,
         crease_light=0.20, crease_k0=20.0, crease_k1=170.0, contrast=0.6, contrast_sigma=1.2, sat_weight=6.0,
         grain=0.09, metal_sigma=0.4, contrast_dark=0.9, groove_max=0.55)


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


def kmeans(x, k, iters=20, seed=0):
    rng = np.random.default_rng(seed)
    c = x[rng.choice(len(x), k, replace=False)].copy()
    for _ in range(iters):
        d = ((x[:, None, :] - c[None, :, :]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            m = lab == j
            c[j] = x[m].mean(0) if m.any() else x[rng.integers(len(x))]
    return c


def ordered_dither(x, pal, bay):
    """4 x 4 Bayer dither between the two nearest palette colours (a colour on a palette entry stays flat)"""
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
    d = TEX8 if name != 'Fittings' else TEX9
    aos = np.load(os.path.join(d, a_s + '.npy')).astype(np.float32)[..., 0]
    aol = np.load(os.path.join(d, a_l + '.npy')).astype(np.float32)[..., 0]
    up = lambda a: np.asarray(Image.fromarray(a, 'F').resize((S, S), Image.BILINEAR), np.float32)
    return up(aos), up(aol)


def dominant(lab_b):
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


# ------------------------------------------------------------------ world-space value noise (seamless across UV islands)
LAT = np.random.default_rng(12).random((64, 64, 64)).astype(np.float32)


def noise3(p, scale):
    q = p * scale + 17.0
    i0 = np.floor(q).astype(np.int64)
    f = q - i0
    f = f * f * (3 - 2 * f)
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1]) * \
                    (f[..., 2] if dz else 1 - f[..., 2])
                out = out + w * LAT[(i0[..., 0] + dx) % 64, (i0[..., 1] + dy) % 64, (i0[..., 2] + dz) % 64]
    return out


def geo_maps(name, N, covered):
    """world position / normal / object id per output texel; covered texels without a rasterised centre take the
    nearest rasterised texel"""
    g = np.load(GEO % N)
    tri, p, n, o = g[name + '_tri'], g[name + '_p'], g[name + '_n'], g[name + '_o']
    have = tri >= 0
    ii = ndimage.distance_transform_edt(~have, return_distances=False, return_indices=True)
    p, n, o = p[ii[0], ii[1]], n[ii[0], ii[1]], o[ii[0], ii[1]]
    return p, n, o, have


def curvature(p, n, o, valid, texel_m):
    """signed curvature (1/m) from the 4 neighbours on the same object and surface (convex > 0, concave < 0)"""
    c = np.zeros(p.shape[:2], np.float32)
    k = np.zeros(p.shape[:2], np.float32)
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        pj = np.roll(p, (-dy, -dx), (0, 1)); nj = np.roll(n, (-dy, -dx), (0, 1))
        oj = np.roll(o, (-dy, -dx), (0, 1)); vj = np.roll(valid, (-dy, -dx), (0, 1))
        dp = pj - p
        d2 = (dp * dp).sum(-1)
        ok = valid & vj & (oj == o) & (d2 < (2.5 * texel_m) ** 2) & (d2 > (0.05 * texel_m) ** 2)
        kk = ((nj - n) * dp).sum(-1) / np.maximum(d2, 1e-12)
        c += np.where(ok, kk, 0)
        k += ok
    return np.where(k > 0, c / np.maximum(k, 1), 0)


def island_blur(a, cov, sig):
    w = cov.astype(np.float32)
    return ndimage.gaussian_filter(a * w, sig) / np.maximum(ndimage.gaussian_filter(w, sig), 1e-4)


def despeckle(st, cov):
    """4-step mask map: a texel whose step at most one covered neighbour shares, inside a 3 x 3 window where one step
    holds 5 or more covered texels, takes that step (the tread plate's diamonds alias into lone full-metal texels at
    512, black specks at night)"""
    lv = np.round(st * 3).astype(np.int32)
    cnt = np.stack([ndimage.uniform_filter(((lv == k) & cov).astype(np.float32), 3, mode='constant') * 9 for k in range(4)], -1)
    own = np.take_along_axis(cnt, lv[..., None], -1)[..., 0]
    maj = cnt.argmax(-1)
    fix = cov & (own <= 2.5) & (cnt.max(-1) >= 4.5)
    return np.where(fix, maj, lv) / 3.0


def seat_numbers(q, pal, N, S):
    """troop seat number patches (PATCH1..4 of the v9 Fittings id map, 64 px at 2048 = 8 texels at 256): redrawn as
    5 x 7 pixel-font digits (tex/v12 pxfont.py, the font of the instrument atlas), upright as painted in v9, light
    digit on the olive patch, both colours from the atlas palette (block means turn the stencilled digit into a blur)"""
    sys.path.insert(0, '/home/claude/plane/v12/tex')
    import pxfont as F
    E = json.load(open('/home/claude/plane/out/ext_v9.json'))
    zid = np.load(os.path.join(TEX9, 'F9_id.npy'))[..., 0]
    k = N / zid.shape[0]
    near = lambda rgb: pal[((pal - np.asarray(rgb, np.float32) / 255.0) ** 2).sum(1).argmin()]
    patch_c, digit_c = near((66, 70, 40)), near((214, 206, 170))
    for d in (1, 2, 3, 4):
        lab, _ = ndimage.label(zid == E['zones'][f'PATCH{d}'])
        for sl in ndimage.find_objects(lab):
            if sl is None or sl[0].stop - sl[0].start < 24 or sl[1].stop - sl[1].start < 24:
                continue
            y0, y1 = int(round(sl[0].start * k)), int(round(sl[0].stop * k))
            x0, x1 = int(round(sl[1].start * k)), int(round(sl[1].stop * k))
            q[y0:y1, x0:x1] = patch_c
            g = F.F57['glyphs'][str(d)]
            gh, gw = g.shape
            oy, ox = y0 + (y1 - y0 - gh) // 2, x0 + (x1 - x0 - gw + 1) // 2
            q[oy:oy + gh, ox:ox + gw][g] = digit_c
    return q


def run(name, N, out, prm):
    mat = 'M_' + name
    bc = np.asarray(Image.open(os.path.join(SRC, f'T_{name}_BaseColor.png')).convert('RGB'), np.float32) / 255
    mk = np.asarray(Image.open(os.path.join(SRC, f'T_{name}_MaskMap.png')).convert('RGBA'), np.float32) / 255
    S = bc.shape[0]
    f = S // N
    cov = coverage(mat, S)
    cov = ndimage.binary_dilation(cov, iterations=1)
    lab, nlab = ndimage.label(cov)
    aos, aol = load_ao(name, S)
    sig = 0.5 * S / N
    cf = cov.astype(np.float32)
    aos = ndimage.gaussian_filter(aos * cf, sig) / np.maximum(ndimage.gaussian_filter(cf, sig), 1e-4)
    s = prm['ao_floor'] + (1 - prm['ao_floor']) * np.clip(aos, 0, 1)
    s = np.clip(s / np.percentile(s[cov], 80), 0, 1)
    ref = np.percentile(aol[cov & (aol > 0.0005)], 92)
    t = prm['aol_floor'] + (1 - prm['aol_floor']) * np.clip(aol / max(ref, 1e-3), 0, 1) ** 0.6
    t = np.clip(t / np.percentile(t[cov], 80), 0, 1)
    shade = s * t
    lin = s2l(bc) * shade[..., None]
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
    gb = blocks(mk[..., 1], f).reshape(N * N, f * f)
    full = (cnt == f * f)
    line = np.zeros(N * N, np.float32)
    line[full] = np.clip((gb[full].mean(1) - np.percentile(gb[full], 12, axis=1)) * 2.6, 0, prm['groove_max'])
    col = col * (1 - line.reshape(N, N))[..., None]

    # painted PS1 shading from the geometry
    texel_m = 1.0 / (PX_PER_M_1024[name] * N / 1024.0)
    p, n, o, have = geo_maps(name, N, covered)
    nz = n[..., 2]
    fac = 1 + prm['top'] * nz
    m1 = noise3(p, prm['mottle_scale1']); m2 = noise3(p, prm['mottle_scale2'])
    fac *= 1 + prm['mottle1'] * (m1 - 0.5) + prm['mottle2'] * (m2 - 0.5)
    z = p[..., 2]
    gh = np.clip((FLOOR_Z + prm['grime_h'] - z) / prm['grime_h'], 0, 1) ** 1.6 * np.clip(1 - nz, 0, 1)
    patch = (nz > 0.7) & (z < FLOOR_Z + 0.05)
    gp = np.where(patch, np.clip((noise3(p, 3.0) - 0.45) * 3, 0, 1), 0) * (prm['floor_patch'] / max(prm['grime'], 1e-6))
    g = np.clip(gh + gp, 0, 1)
    fac *= 1 - prm['grime'] * g
    tint = np.power(np.array([1.0, 0.93, 0.80], np.float32)[None, None, :], g[..., None])
    kap = curvature(p, n, o, covered, texel_m)
    conv = np.clip((kap - prm['crease_k0']) / (prm['crease_k1'] - prm['crease_k0']), 0, 1)
    conc = np.clip((-kap - prm['crease_k0']) / (prm['crease_k1'] - prm['crease_k0']), 0, 1)
    fac *= (1 + prm['crease_light'] * conv) * (1 - prm['crease_dark'] * conc)
    col = col * fac[..., None] * tint
    # local contrast on log luminance inside the islands
    L = np.maximum((col * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1), 1e-5)
    lL = np.log(L)
    lb_ = island_blur(lL, covered, prm['contrast_sigma'])
    gain = np.exp(np.clip(prm['contrast'] * (lL - lb_), -prm['contrast_dark'], 0.9))   # darkening capped: no black specks
    col = col * gain[..., None]
    # per-texel grain (the low-res photo texture of a PS1 game: every texel its own value, so the texels read as
    # blocks even on plain dark paint); seeded per atlas, clipped
    jit = np.clip(np.random.default_rng(zlib.crc32(name.encode())).normal(0, 1, (N, N)), -2.2, 2.2)
    col = col * np.exp(prm['grain'] * jit)[..., None]

    # metal in 4 steps on a lightly smoothed map (v12: sigma 0.8 texel at 1024 = 0.4 at 512), normalised to the
    # covered texels so thin parts (yoke tubes, rails) keep their own value instead of mixing with the gutter
    metal = np.round(np.clip(island_blur(bmean(mk[..., 0]), covered, prm['metal_sigma']), 0, 1) * 3) / 3
    smooth = np.round(bmean(mk[..., 3]) * 0.55 * 3) / 3
    metal, smooth = despeckle(metal, covered), despeckle(smooth, covered)
    srgb = l2s(col).reshape(-1, 3)
    cv = covered.reshape(-1)
    samp = srgb[cv]
    sat = samp.max(1) - samp.min(1)
    wgt = 1 + prm['sat_weight'] * sat
    rng = np.random.default_rng(1)
    pick = rng.choice(len(samp), min(len(samp), 60000), replace=False, p=wgt / wgt.sum())
    ncol = prm['ncol_atlas'].get(name, prm['ncol'])
    pal = kmeans(samp[pick], ncol)
    bay = np.tile(BAYER4, (N // 4, N // 4)).reshape(-1)
    idx = ordered_dither(srgb, pal, bay)
    q = pal[idx].reshape(N, N, 3)
    if name == 'Fittings':
        q = seat_numbers(q, pal, N, S)
    ii = ndimage.distance_transform_edt(~covered, return_distances=False, return_indices=True)
    q, metal, smooth = q[ii[0], ii[1]], metal[ii[0], ii[1]], smooth[ii[0], ii[1]]
    os.makedirs(out, exist_ok=True)
    Image.fromarray((q * 255 + 0.5).astype(np.uint8), 'RGB').save(os.path.join(out, f'T_{name}_BaseColor.png'), optimize=True)
    mask = np.dstack([metal, np.ones_like(metal), np.ones_like(metal), smooth])
    Image.fromarray((mask * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(out, f'T_{name}_MaskMap.png'), optimize=True)
    info = dict(atlas=name, size=N, source=S, block=f, colours=int(len(np.unique(idx[cv]))), islands=int(nlab),
                covered=round(float(covered.mean()), 4), px_per_m=round(1 / texel_m, 1),
                convex=round(float((conv > 0.3)[covered].mean()), 3), concave=round(float((conc > 0.3)[covered].mean()), 3),
                grime=round(float((g > 0.3)[covered].mean()), 3))
    print(json.dumps(info), flush=True)
    return info


def run_webbing(out, w_out=32, ncol=8):
    """tiled strap texture: v11 512 x 128 (u along the strap, 10 repeats per metre... the material tiles 10 x 1) ->
    block mean to w_out x w_out/4, the weave relief of the normal map baked as light from above-left, ncol colours,
    Bayer dither between the two nearest; no normal map"""
    T = '/home/claude/plane/export/unity_v11/Assets/UtilityPlane/Textures/'
    bc = np.asarray(Image.open(T + 'T_Webbing_BaseColor.png').convert('RGB'), np.float32) / 255
    nm = np.asarray(Image.open(T + 'T_Webbing_Normal.png').convert('RGB'), np.float32) / 255 * 2 - 1
    L = np.array([-0.35, 0.45, 0.82]); L /= np.linalg.norm(L)
    shade = np.clip(0.55 + 0.45 * (nm @ L) / max(L[2], 1e-3), 0.6, 1.15)
    lin = s2l(bc) * shade[..., None]
    H, W = lin.shape[:2]
    f = W // w_out
    col = lin.reshape(H // f, f, W // f, f, 3).mean((1, 3))
    # strap edges darker (stitched hem), centre lighter: across v
    h = col.shape[0]
    v = (np.arange(h) + 0.5) / h
    edge = np.clip(1 - np.abs(v - 0.5) * 2, 0, 1)
    col = col * (0.72 + 0.36 * np.minimum(edge * 2.2, 1.0))[:, None, None]
    srgb = l2s(col).reshape(-1, 3)
    pal = kmeans(srgb, ncol)
    bay = np.tile(BAYER4, (max(1, col.shape[0] // 4), max(1, col.shape[1] // 4)))[:col.shape[0], :col.shape[1]].reshape(-1)
    idx = ordered_dither(srgb, pal, bay)
    q = pal[idx].reshape(col.shape)
    Image.fromarray((q * 255 + 0.5).astype(np.uint8), 'RGB').save(os.path.join(out, 'T_Webbing_BaseColor.png'), optimize=True)
    print('webbing', q.shape, ncol, 'colours', flush=True)


if __name__ == '__main__':
    out = sys.argv[1]
    spec = dict(kv.split('=') for kv in sys.argv[2].split(','))
    prm = dict(P)
    if len(sys.argv) > 3:
        prm.update(json.load(open(sys.argv[3])))
    res = []
    for k, v in spec.items():
        if k == 'Webbing':
            run_webbing(out, int(v))
        else:
            res.append(run(k, int(v), out, prm))
    json.dump(dict(params=prm, atlases=res), open(os.path.join(out, 'psx_interior2.json'), 'w'), indent=1)
