"""v9 texture painter (numpy) from the bake inputs of tex_v9.py.
 - T_Fittings_{BaseColor,MaskMap,Normal} 2048: interior style like the v8 cabin (olive canvas troop seats, aluminium
   tubes, zinc-plated steel, grey lap belts, black clips / holster, orange cargo straps, seat number patches).
 - T_Survival_{BaseColor,MaskMap} 256: PSX like the exterior (painted at 1024 with AO and a soft top light baked into
   the colour, then 4x4 block average, 64-colour palette, ordered 4x4 dither; MaskMap R metal 0/1, G 1, B 1,
   A smoothness in 4 steps; no normal map).
 - T_FogPrint_Hand / T_FogPrint_Finger (128, R8 in an RGB PNG): brushes for UtilityPlaneRig.StampFogPrint.
python3 paint_v9.py [fittings,survival,brush]"""
import os, sys, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex', 'v9')
OUT = os.path.join(TEX, 'out')
os.makedirs(OUT, exist_ok=True)
E = json.load(open(os.path.join(HERE, 'out', 'ext_v9.json')))
Z = E['zones']
S = E['seat']
A9 = json.load(open(os.path.join(TEX, 'atlas9.json')))
WHAT = (sys.argv[1] if len(sys.argv) > 1 else 'fittings,survival,brush').split(',')
FONT_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_C = '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
rng = np.random.default_rng(9)


def s2l(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def l2s(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def srgb(r, g, b):
    return s2l(np.array([r, g, b], np.float32) / 255.0)


# ------------------------------------------------------------------ value noise on a wrapped 3D lattice
LAT = rng.random((64, 64, 64)).astype(np.float32)


def noise3(p, scale):
    q = p * scale
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


def fbm(p, scale, octaves=4, gain=0.5):
    tot, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        tot = tot + amp * noise3(p + o * 17.31, scale * (2 ** o))
        norm += amp
        amp *= gain
    return tot / norm


def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def height_to_normal(h, px_m):
    """h (m) in UV space (row 0 = v 1) -> OpenGL tangent-space normal (x = +u, y = +v)"""
    dhdu = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * px_m)
    dhdv = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) / (2 * px_m)          # row - 1 is higher v
    n = np.dstack([-dhdu, -dhdv, np.ones_like(h)])
    return n / np.linalg.norm(n, axis=2, keepdims=True)


def dilate(arr, cover):
    """fill texels outside the islands with the nearest island value (keeps mips clean)"""
    ii = ndimage.distance_transform_edt(~cover, return_distances=False, return_indices=True)
    return arr[ii[0], ii[1]]


def text_mask(size, text, font, fill_frac=0.8, stencil=False):
    """white text on black, centred, as float mask (size = (w, h) px)"""
    w, h = size
    im = Image.new('L', (w * 4, h * 4), 0)
    d = ImageDraw.Draw(im)
    fs = int(h * 4 * fill_frac)
    while True:
        f = ImageFont.truetype(font, fs)
        bb = d.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= w * 4 * 0.92 or fs < 8:
            break
        fs -= 2
    d.text(((w * 4 - (bb[2] - bb[0])) / 2 - bb[0], (h * 4 - (bb[3] - bb[1])) / 2 - bb[1]), text, font=f, fill=255)
    if stencil:                                    # stencil bridges: two thin horizontal gaps
        for yy in (0.40, 0.62):
            d.rectangle([0, int(h * 4 * yy), w * 4, int(h * 4 * yy) + max(2, h // 6)], fill=0)
    im = im.resize((w, h), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255.0


def island_rect(zmask):
    """bounding box (rows, cols) of the largest connected component of a zone mask"""
    lab, n = ndimage.label(zmask)
    if n == 0:
        return None
    sizes = ndimage.sum(zmask, lab, range(1, n + 1))
    k = int(np.argmax(sizes)) + 1
    sl = ndimage.find_objects(lab == k)[0]
    return sl


# ================================================================== fittings
def fittings():
    res = 2048
    px_m = 1.0 / A9['Fittings']['pxPerMetre']
    zid = np.rint(np.load(os.path.join(TEX, 'F9_id.npy'))[..., 0].astype(np.float32)).astype(np.int32)
    pos = np.load(os.path.join(TEX, 'F9_pos.npy')).astype(np.float32)
    nrm = np.load(os.path.join(TEX, 'F9_nrm.npy')).astype(np.float32)
    ao = np.load(os.path.join(TEX, 'F9_ao.npy'))[..., 0].astype(np.float32)
    aol = np.load(os.path.join(TEX, 'F9_aol.npy'))[..., 0].astype(np.float32) \
        if os.path.exists(os.path.join(TEX, 'F9_aol.npy')) else np.ones_like(ao)
    if aol.shape != ao.shape:                       # baked at half resolution: smooth upscale
        aol = np.asarray(Image.fromarray(aol).resize(ao.shape[::-1], Image.BILINEAR), np.float32)
    cover = zid > 0
    H = W = res
    rows, cols = np.mgrid[0:H, 0:W].astype(np.float32)
    u = cols * px_m                                  # metres in UV space (islands unrotated: u, v = surface metres)
    v = (H - rows) * px_m
    lab, nlab = ndimage.label(cover)
    seed = rng.random(nlab + 1).astype(np.float32) * 50.0
    iseed = seed[lab]
    edge = ndimage.distance_transform_edt(cover) * px_m * 1000.0          # mm from the island border
    uvp = np.dstack([u * 1.0, v * 1.0, iseed])                            # 2D pattern space per island
    # seat-local coordinates (shared islands carry the last baked seat): |x| from the centre, y from the seat centre
    ycs = np.array(sorted({s['yc'] for s in E['seats'].values()}), np.float32)
    yl = pos[..., 1] - ycs[np.argmin(np.abs(pos[..., 1][..., None] - ycs[None, None, :]), axis=2)]
    ax = np.abs(pos[..., 0])
    zz = pos[..., 2]
    big = fbm(pos, 6.0, 4)
    mid = fbm(pos, 40.0, 3)
    fine = fbm(pos, 300.0, 2)
    col = np.zeros((H, W, 3), np.float32)
    metal = np.zeros((H, W), np.float32)
    smooth = np.zeros((H, W), np.float32)
    h = np.zeros((H, W), np.float32)
    zm = lambda *names: np.isin(zid, [Z[n] for n in names])

    # --- canvas (seat pans, backs) and patches: olive drab duck
    can = zm('CANVAS')
    weave = np.sin(2 * np.pi * u / 0.0024) * np.sin(2 * np.pi * v / 0.0024)
    base = srgb(80, 85, 48)
    tone = 0.90 + 0.16 * (big - 0.5) + 0.08 * (mid - 0.5) + 0.04 * weave
    c = base[None, None, :] * tone[..., None]
    pan_top = can & (nrm[..., 2] > 0.8) & (np.abs(zz - S['ZH']) < 0.03)
    seat_wear = pan_top * np.exp(-(((ax - (S['XF'] + 0.55 * S['DEPTH'])) / 0.10) ** 2 + (yl / 0.11) ** 2))
    back_face = can & (np.abs(nrm[..., 0]) > 0.8) & (zz > S['ZLB'])
    back_wear = back_face * np.exp(-(((zz - 1.63) / 0.07) ** 2 + (yl / 0.12) ** 2))
    fade = np.clip(0.55 * seat_wear + 0.35 * back_wear, 0, 1)
    c = c * (1 - fade[..., None]) + srgb(128, 128, 98)[None, None, :] * fade[..., None] * tone[..., None]
    grime = np.clip(0.55 * (1 - ao) + 0.25 * ss(0.55, 0.85, mid) * (1 - ss(0.0, 0.2, fade)), 0, 1)
    c = c * (1 - 0.45 * grime[..., None])
    stitch = can & (edge > 2.0) & (edge < 3.6)
    dash = (np.sin(2 * np.pi * (u + v) / 0.004) > -0.2)
    c = np.where((stitch & dash)[..., None], srgb(60, 64, 36)[None, None, :] * tone[..., None], c)
    col[can] = c[can]
    smooth[can] = (0.16 + 0.10 * fade + 0.03 * mid)[can]
    h[can] = (0.00012 * weave + 0.00045 * (mid - 0.5) - 0.00025 * (stitch & dash) - 0.0002 * ss(4.0, 0.5, edge))[can]
    # --- seat number patches: darker olive patch, worn stencilled digit, stitched border
    for d in (1, 2, 3, 4):
        pm = zm(f'PATCH{d}')
        m = np.zeros((H, W), np.float32)
        lab_p, n_p = ndimage.label(pm)
        for sl in ndimage.find_objects(lab_p):     # both faces of the patch plate (each upright in its own view)
            if sl is None:
                continue
            hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
            if hh < 24 or ww < 24:
                continue
            m[sl] = text_mask((ww, hh), str(d), FONT_B, 0.72, stencil=True)
        pc = srgb(66, 70, 40)[None, None, :] * (0.92 + 0.12 * (mid[..., None] - 0.5) + 0.04 * weave[..., None])
        worn = ss(0.35, 0.75, fine + 0.35 * mid)
        paint = (m > 0.5) & (worn > 0.25)
        pc = np.where(paint[..., None], srgb(214, 206, 170)[None, None, :] * (0.85 + 0.15 * worn[..., None]), pc)
        st_ = pm & (edge > 2.0) & (edge < 3.4) & dash
        pc = np.where(st_[..., None], srgb(52, 55, 32)[None, None, :], pc)
        col[pm] = pc[pm]
        smooth[pm] = np.where(paint, 0.30, 0.18)[pm]
        h[pm] = (0.00012 * weave - 0.0003 * st_ + 0.00004 * paint)[pm]
    # --- lacing cords and webbing (ribs along the strap = across u)
    for zn, rgb, sm, rib in (('LACE', (62, 66, 37), 0.20, 0.0016), ('WEB_GREY', (152, 154, 151), 0.26, 0.0020),
                             ('CARGO_STRAP', (214, 98, 22), 0.30, 0.0018), ('HOLSTER', (16, 16, 17), 0.24, 0.0012),
                             ('BUNGEE', (14, 14, 14), 0.30, 0.0015)):
        mk = zm(zn)
        ribs = np.sin(2 * np.pi * u / rib)
        tone = 0.90 + 0.10 * (mid - 0.5) + 0.05 * ribs
        c = srgb(*rgb)[None, None, :] * tone[..., None]
        if zn == 'BUNGEE':
            fleck = ss(0.62, 0.66, fbm(uvp, 900.0, 1))
            c = np.where((fleck > 0.5)[..., None], srgb(150, 20, 18)[None, None, :], c)
        if zn in ('CARGO_STRAP', 'WEB_GREY'):
            dirt = np.clip(0.5 * (1 - ao) + 0.3 * ss(0.5, 0.8, big), 0, 1)
            c = c * (1 - 0.35 * dirt[..., None])
        if zn == 'HOLSTER':
            scuff = ss(0.6, 0.8, mid) * ss(4.0, 0.5, edge)
            c = c + srgb(60, 60, 62)[None, None, :] * scuff[..., None] * 0.6
            stitch_h = mk & (edge > 1.8) & (edge < 3.0) & dash
            c = np.where(stitch_h[..., None], srgb(45, 45, 46)[None, None, :], c)
        col[mk] = c[mk]
        smooth[mk] = sm + 0.04 * (mid[mk] - 0.5)
        h[mk] = (0.00010 * ribs + 0.0002 * (fine - 0.5))[mk]
    # --- aluminium tubes and sheet: brushed along v (tubes), scuffs, dull oxide spots, hand grime on front tubes
    for zn, rgb, sm in (('TUBE', (205, 207, 210), 0.56), ('ALU_SHEET', (196, 198, 200), 0.50)):
        mk = zm(zn)
        brush = fbm(np.dstack([u * 8.0, v * 0.3, iseed]), 60.0, 3)
        oxide = ss(0.62, 0.78, fbm(pos, 25.0, 3))
        front = mk & (ax < S['XF'] + 0.03) & (np.abs(zz - S['ZH']) < 0.03)
        hand = front * ss(0.4, 0.7, mid)
        c = srgb(*rgb)[None, None, :] * (0.92 + 0.10 * (brush[..., None] - 0.5))
        c = c * (1 - 0.18 * oxide[..., None]) + srgb(170, 172, 168)[None, None, :] * 0.18 * oxide[..., None]
        c = c * (1 - (0.45 * (1 - ao) + 0.3 * hand)[..., None])
        scratch = ss(0.80, 0.86, fbm(np.dstack([u * 4.0, v * 0.25, iseed]), 300.0, 1))
        c = np.where((scratch > 0.5)[..., None], c * 1.08, c)
        col[mk] = c[mk]
        metal[mk] = 1.0
        smooth[mk] = (sm + 0.12 * (brush - 0.5) - 0.20 * oxide - 0.18 * hand + 0.08 * scratch)[mk]
        h[mk] = (0.00002 * (brush - 0.5) - 0.00002 * scratch)[mk]
    # --- zinc-plated steel, D-rings, latch plate, chrome buckle
    for zn, rgb, sm in (('STEEL', (150, 153, 156), 0.42), ('DRING', (150, 152, 154), 0.40), ('LATCH', (186, 188, 190), 0.58),
                        ('BUCKLE', (228, 229, 230), 0.86)):
        mk = zm(zn)
        tint = fbm(pos, 18.0, 2)
        c = srgb(*rgb)[None, None, :] * (0.94 + 0.10 * (mid[..., None] - 0.5))
        if zn in ('STEEL', 'DRING'):
            c = c * (1 + 0.06 * np.dstack([tint - 0.5, (0.5 - tint) * 0.3, 0.5 - tint]))      # chromate sheen
            rust = ss(0.74, 0.82, fbm(pos, 70.0, 3)) * (1 - ao * 0.5)
            c = c * (1 - rust[..., None]) + srgb(110, 62, 30)[None, None, :] * rust[..., None]
            metal[mk] = (1 - ss(0.3, 0.6, rust))[mk]
        else:
            metal[mk] = 1.0
            rust = np.zeros_like(ao)
        c = c * (1 - 0.40 * (1 - ao)[..., None])
        col[mk] = c[mk]
        smooth[mk] = (sm - 0.25 * rust + 0.05 * (fine - 0.5))[mk]
        h[mk] = (0.00002 * (fine - 0.5))[mk]
    # --- black powder-coated clips (chipped to bare steel at the edges) and rubber feet
    mk = zm('BLACK')
    chip = mk & (edge < 1.6) & (ss(0.55, 0.62, fine) > 0.5)
    c = srgb(12, 12, 13)[None, None, :] * (0.9 + 0.2 * (mid[..., None] - 0.5))
    c = np.where(chip[..., None], srgb(140, 142, 145)[None, None, :], c)
    col[mk] = c[mk]
    metal[mk] = np.where(chip, 1.0, 0.0)[mk]
    smooth[mk] = np.where(chip, 0.45, 0.42)[mk]
    h[mk] = (0.00003 * (fine - 0.5))[mk]
    mk = zm('RUBBER')
    c = srgb(9, 9, 9)[None, None, :] * (0.9 + 0.3 * (fine[..., None] - 0.5))
    scuff = (zz < S['FLOOR'] + 0.006) * 0.6
    c = c + srgb(70, 68, 64)[None, None, :] * scuff[..., None] * 0.4
    col[mk] = c[mk]
    smooth[mk] = 0.22
    h[mk] = (0.00004 * (fine - 0.5))[mk]
    # --- assemble
    col = dilate(col, cover)
    metal = dilate(metal, cover)
    smooth = dilate(np.clip(smooth, 0.02, 0.95), cover)
    ao_out = dilate(np.clip(0.30 + 0.70 * ao, 0, 1) * np.clip(0.55 + 0.45 * aol, 0, 1), cover)
    h = dilate(h, cover)
    n = height_to_normal(h, px_m)
    Image.fromarray((l2s(col) * 255 + 0.5).astype(np.uint8), 'RGB').save(os.path.join(OUT, 'T_Fittings_BaseColor.png'))
    mask = np.dstack([metal, ao_out, np.ones_like(ao), smooth])
    Image.fromarray((np.clip(mask, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(
        os.path.join(OUT, 'T_Fittings_MaskMap.png'))
    Image.fromarray(((n * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8), 'RGB').save(os.path.join(OUT, 'T_Fittings_Normal.png'))
    cov = cover.mean()
    print('fittings painted: coverage %.1f %%, AO median %.2f' % (cov * 100, float(np.median(ao[cover]))), flush=True)


# ================================================================== survival kit (PSX)
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0


def kmeans(x, k, iters=18, seed=0):
    r = np.random.default_rng(seed)
    c = x[r.choice(len(x), k, replace=False)].copy()
    for _ in range(iters):
        d = ((x[:, None, :] - c[None, :, :]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            m = lab == j
            c[j] = x[m].mean(0) if m.any() else x[r.integers(len(x))]
    return c


def survival():
    res, out_res, ncol = 1024, 256, 64
    px_m = 1.0 / A9['Survival']['pxPerMetre']
    zid = np.rint(np.load(os.path.join(TEX, 'S9_id.npy'))[..., 0].astype(np.float32)).astype(np.int32)
    pos = np.load(os.path.join(TEX, 'S9_pos.npy')).astype(np.float32)          # object space of each item
    nrm = np.load(os.path.join(TEX, 'S9_nrm.npy')).astype(np.float32)
    ao = np.load(os.path.join(TEX, 'S9_ao.npy'))[..., 0].astype(np.float32)
    cover = zid > 0
    H = W = res
    rows, cols = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = cols * px_m, (H - rows) * px_m
    lab, nlab = ndimage.label(cover)
    iseed = (rng.random(nlab + 1).astype(np.float32) * 50.0)[lab]
    edge = ndimage.distance_transform_edt(cover) * px_m * 1000.0
    mid = fbm(pos, 30.0, 3)
    fine = fbm(pos, 160.0, 2)
    col = np.zeros((H, W, 3), np.float32)
    metal = np.zeros((H, W), np.float32)
    smooth = np.full((H, W), 0.3, np.float32)
    zm = lambda *names: np.isin(zid, [Z[n] for n in names])
    flat = {'BAG': ((226, 88, 24), 0.28, 0), 'BAG_REFLECT': ((196, 197, 192), 0.55, 0), 'BAG_ZIP': ((22, 22, 22), 0.4, 0),
            'BAG_WEB': ((24, 24, 25), 0.25, 0), 'SHOVEL_BLADE': ((168, 30, 26), 0.45, 0),
            'SHOVEL_SHAFT': ((72, 74, 78), 0.55, 1), 'SHOVEL_GRIP': ((22, 22, 23), 0.30, 0),
            'GUN_BODY': ((238, 112, 22), 0.40, 0), 'GUN_DARK': ((28, 28, 29), 0.35, 0), 'GUN_BORE': ((12, 10, 9), 0.1, 0),
            'FLARE_TUBE': ((186, 26, 22), 0.30, 0), 'FLARE_CAP': ((26, 26, 27), 0.30, 0),
            'FLASH_BODY': ((62, 72, 46), 0.45, 0), 'FLASH_KNURL': ((56, 65, 42), 0.35, 0),
            'FLASH_LENS': ((242, 236, 200), 0.85, 0), 'FLASH_RUBBER': ((20, 20, 20), 0.2, 0),
            'SHELL_CASE': ((196, 32, 26), 0.40, 0), 'SHELL_BASE': ((192, 150, 72), 0.55, 1),
            'STRAP_ORANGE': ((220, 108, 20), 0.30, 0), 'ITEM_STEEL': ((165, 167, 170), 0.50, 1),
            'BAG_LABEL': ((230, 228, 218), 0.20, 0), 'FLARE_LABEL': ((228, 222, 206), 0.25, 0)}
    for zn, (rgb, sm, mt) in flat.items():
        mk = zm(zn)
        c = srgb(*rgb)[None, None, :] * (0.92 + 0.14 * (mid[..., None] - 0.5) + 0.05 * (fine[..., None] - 0.5))
        col[mk] = c[mk]
        smooth[mk] = sm
        metal[mk] = mt
    # bag: weave, dirt towards the bottom, creases; reflective tape grid
    mk = zm('BAG')
    weave = np.sin(2 * np.pi * u / 0.005) * np.sin(2 * np.pi * v / 0.005)
    dirt = ss(-0.20, -0.29, pos[..., 2]) * (0.6 + 0.4 * mid)
    c = col * (1 + 0.04 * weave[..., None])
    c = c * (1 - 0.40 * dirt[..., None]) + srgb(70, 58, 44)[None, None, :] * 0.40 * dirt[..., None]
    col[mk] = c[mk]
    mk = zm('BAG_REFLECT')
    grid = (np.abs(np.sin(2 * np.pi * u / 0.012)) < 0.12) | (np.abs(np.sin(2 * np.pi * v / 0.012)) < 0.12)
    col[mk & grid] *= 0.82
    # labels with text
    for zn, lines in (('BAG_LABEL', ('SURVIVAL', 'KIT')), ('FLARE_LABEL', ('RED', 'HAND FLARE'))):
        mk = zm(zn)
        for sl in ndimage.find_objects(ndimage.label(mk)[0]):
            if sl is None:
                continue
            hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
            if hh < 12 or ww < 12:
                continue
            if zn == 'FLARE_LABEL':                    # band round the tube: u = around, v = along -> text along v
                tm = np.rot90(text_mask((hh, ww), ' '.join(lines), FONT_C, 0.62), 1)
            else:
                t1 = text_mask((ww, hh // 2), lines[0], FONT_C, 0.66)
                t2 = text_mask((ww, hh - hh // 2), lines[1], FONT_C, 0.66)
                tm = np.vstack([t1, t2])
            reg = col[sl]
            reg = np.where((tm > 0.45)[..., None], srgb(18, 18, 18)[None, None, :], reg)
            col[sl] = np.where(mk[sl][..., None], reg, col[sl])
    # shovel: worn blade edges show bare aluminium, depth marks on the shaft
    mk = zm('SHOVEL_BLADE')
    tipz = np.abs(pos[..., 1]) > 0.86                              # blade tip region (object space, -y forward)
    wear = mk & (((edge < 1.6) & (ss(0.45, 0.6, fine) > 0.5)) | (tipz & (ss(0.55, 0.7, mid + 0.4 * fine) > 0.5)) |
                 (ss(0.86, 0.92, mid + 0.25 * fine) > 0.5))
    col[wear] = srgb(190, 192, 194)
    metal[wear] = 1.0
    smooth[wear] = 0.5
    mk = zm('SHOVEL_SHAFT')
    marks = mk & (np.abs(((v - iseed * 0.0) % 0.05) - 0.025) < 0.0012) & (((u % 0.06) < 0.012))
    col[marks] = srgb(220, 220, 215)
    # flashlight knurl: diamond hatch
    mk = zm('FLASH_KNURL')
    kn = (np.sin(2 * np.pi * (u + v) / 0.004) * np.sin(2 * np.pi * (u - v) / 0.004)) > 0.3
    col[mk & kn] *= 0.70
    # light from above + AO baked into the colour (PSX carried its own shading)
    shade = (0.80 + 0.20 * np.clip(nrm[..., 2] * 0.5 + 0.5, 0, 1)) * (0.30 + 0.70 * ao)
    lens = zm('FLASH_LENS')
    shade[lens] = 1.0
    col = col * shade[..., None]
    col = dilate(col, cover)
    metal = dilate(metal, cover)
    smooth = dilate(smooth, cover)
    # PSX reduction: 4x4 block mean, 64-colour palette, ordered dither (same as the exterior variant B)
    f = res // out_res
    blk = lambda a: a.reshape(out_res, f, out_res, f, *a.shape[2:]).swapaxes(1, 2).reshape(out_res, out_res, f * f,
                                                                                       *a.shape[2:])
    cs = blk(col).mean(2)
    met = (blk(metal).mean(2) > 0.5).astype(np.float32)
    smo = np.round(blk(smooth).mean(2) * 0.55 * 3) / 3
    covered = blk(cover).mean(2) > 0.25
    s = l2s(cs).reshape(-1, 3)
    samp = s[covered.reshape(-1)]
    samp = samp[np.random.default_rng(1).choice(len(samp), min(len(samp), 40000), replace=False)]
    pal = kmeans(samp, ncol)
    bay = np.tile(BAYER4, (out_res // 4, out_res // 4)).reshape(-1, 1)
    s_d = np.clip(s + (bay - 0.5) * (1.0 / 24.0), 0, 1)
    idx = ((s_d[:, None, :] - pal[None]) ** 2).sum(-1).argmin(1)
    q = pal[idx].reshape(out_res, out_res, 3)
    ii = ndimage.distance_transform_edt(~covered, return_distances=False, return_indices=True)
    q, met, smo = q[ii[0], ii[1]], met[ii[0], ii[1]], smo[ii[0], ii[1]]
    Image.fromarray((q * 255 + 0.5).astype(np.uint8), 'RGB').save(os.path.join(OUT, 'T_Survival_BaseColor.png'))
    mask = np.dstack([met, np.ones_like(met), np.ones_like(met), smo])
    Image.fromarray((mask * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'T_Survival_MaskMap.png'))
    # 1024 preview of the unreduced colour (for checking only)
    Image.fromarray((l2s(col) * 255 + 0.5).astype(np.uint8), 'RGB').save(os.path.join(TEX, 'survival_1k_preview.png'))
    print('survival painted: %d colours, coverage %.1f %%' % (len(np.unique(idx)), cover.mean() * 100), flush=True)


# ================================================================== fog print brushes
def brushes():
    n = 128
    yy, xx = (np.mgrid[0:n, 0:n].astype(np.float32) + 0.5) / n
    x, y = xx * 2 - 1, (1 - yy) * 2 - 1                          # -1..1, y up
    def ell(cx, cy, rx, ry, ang=0.0):
        ca, sa = math.cos(ang), math.sin(ang)
        dx, dy = x - cx, y - cy
        px, py = dx * ca + dy * sa, -dx * sa + dy * ca
        return (px / rx) ** 2 + (py / ry) ** 2
    # palm + four fingers + thumb (left hand seen from the glass side), soft edges
    d = ell(0.0, -0.38, 0.42, 0.40)
    fingers = [(-0.33, 0.30, 0.10, 0.36, 0.20), (-0.11, 0.42, 0.10, 0.42, 0.06), (0.12, 0.40, 0.10, 0.40, -0.05),
               (0.33, 0.24, 0.09, 0.32, -0.18)]
    for cx, cy, rx, ry, a in fingers:
        d = np.minimum(d, ell(cx, cy, rx, ry, a))
    d = np.minimum(d, ell(0.50, -0.42, 0.10, 0.28, 0.85))
    rough = 1.0 + 0.10 * (fbm(np.dstack([x, y, np.zeros_like(x)]), 6.0, 3) - 0.5)
    hand = np.clip((1.0 - d * rough) / 0.18, 0, 1)
    # skin: the print is not uniform (pressure falls off between the pads; a few palm creases)
    skin = 0.86 + 0.14 * fbm(np.dstack([x * 3.0, y * 3.0, np.ones_like(x)]), 9.0, 3)
    crease = np.exp(-((y + 0.30 + 0.25 * x) / 0.025) ** 2) * (np.abs(x) < 0.32) + \
        np.exp(-((y + 0.52 - 0.15 * x) / 0.02) ** 2) * (np.abs(x + 0.05) < 0.30)
    hand = hand * np.clip(skin - 0.35 * crease, 0, 1)
    finger = np.clip((1.0 - ell(0.0, 0.0, 0.85, 0.85)) / 0.35, 0, 1)
    for name, m in (('T_FogPrint_Hand', hand), ('T_FogPrint_Finger', finger)):
        g = (np.clip(m, 0, 1) * 255 + 0.5).astype(np.uint8)
        Image.fromarray(np.dstack([g, g, g]), 'RGB').save(os.path.join(OUT, name + '.png'))
    print('brushes written', flush=True)


if 'fittings' in WHAT:
    fittings()
if 'survival' in WHAT:
    survival()
if 'brush' in WHAT:
    brushes()
