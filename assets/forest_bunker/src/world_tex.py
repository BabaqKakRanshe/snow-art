"""Panel atlas and own textures of forest_world (pixel art in the project's font, point filter).
Panel (256 x 256): the station's marking on the shift car's doors (RADIOOBSERVATORIUM / HOHENMOOS, white stencil on the
station's grey-green) and the cave's newspaper (ALPENBOTE of 12 November 1991 - one of the Forester's 1991 things; German,
as print is). Own textures: the fire barrel's flame flipbook (8 frames of 32 x 64 in a row, alpha cut-out; base = emission),
the ice overlay's tile (64 x 64, box-mapped at 64 px/m), the wreck's cracked windscreen (128 x 128, alpha).
Everything is invented: no real paper, brand or make.
python3 world_tex.py [out_dir] -> T_World_*.png, world_panel_regions.json"""
import os, sys, json, math
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxfont as F
import van2_tex as VT
import gear_tex as GT                                   # the umlauts, ptext / fill / grain / pack
from noise import fbm

HERE = os.path.dirname(os.path.abspath(__file__))
N = 256
ptext, fill, grain = GT.ptext, GT.fill, GT.grain
STATION_GREEN = (88, 104, 92)
PAPER_DATE = '12. NOVEMBER 1991'
SIZES = [('shift_door', 112, 40),        # 0.70 x 0.25 m on the door (160 px/m)
         ('paper', 96, 128)]             # 0.30 x 0.40 m folded newspaper (320 px/m)
REG = GT.pack(SIZES, n=N)
FIRE_FRAMES, FIRE_FW, FIRE_FH = 8, 32, 64
ICE_N = 64


def uv(name, n=N):
    return VT.uv(REG[name], n)


def draw_door(img):
    r = REG['shift_door']
    x0, y0, x1, y1 = r
    fill(img, r, STATION_GREEN)
    grain(img, r, 11, amount=5.0)
    cx = (x0 + x1) / 2
    ptext(img, cx, y0 + 13, 'RADIOOBSERVATORIUM', F.F35, (226, 228, 220), scale=1)
    ptext(img, cx, y0 + 25, 'HOHENMOOS', F.F57, (226, 228, 220), scale=1)
    F.rect(img, x0 + 8, y0 + 33, x1 - 9, y0 + 33, (206, 208, 200))
    sub = img[y0:y1, x0:x1].astype(np.float32)               # the stencil worn: chalky, chipped at the edges
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    p = np.stack([xx / 32.0, yy / 32.0, np.full_like(xx, 3.1)], -1).reshape(-1, 3)
    wear = fbm(p, 9.0, 2, seed=12).reshape(xx.shape)
    white = sub.mean(-1) > 160
    chip = white & (wear > 0.66)
    sub[chip] = sub[chip] * 0.35 + np.array(STATION_GREEN, np.float32) * 0.65
    img[y0:y1, x0:x1] = np.clip(sub, 0, 255).astype(np.uint8)


def draw_paper(img):
    r = REG['paper']
    x0, y0, x1, y1 = r
    fill(img, r, (214, 206, 182))
    grain(img, r, 21, amount=7.0)
    INK = (40, 38, 36)
    ptext(img, (x0 + x1) / 2, y0 + 8, 'ALPENBOTE', F.F57, INK, scale=1)
    F.rect(img, x0 + 4, y0 + 14, x1 - 5, y0 + 14, INK)
    ptext(img, (x0 + x1) / 2, y0 + 19, PAPER_DATE, F.F35, INK)
    F.rect(img, x0 + 4, y0 + 24, x1 - 5, y0 + 24, INK)
    ptext(img, (x0 + x1) / 2, y0 + 32, 'ERSTER SCHNEE', F.F57, INK)
    ptext(img, (x0 + x1) / 2, y0 + 42, 'AUF DEM HOHENMOOS', F.F35, INK)
    F.rect(img, x0 + 6, y0 + 50, x0 + 44, y0 + 78, (120, 116, 104))         # the photo: grey, a dark ridge
    for i in range(38):
        h = int(8 + 6 * math.sin(i * 0.31) + 3 * math.sin(i * 1.7))
        F.rect(img, x0 + 6 + i, y0 + 78 - h, x0 + 6 + i, y0 + 78, (70, 68, 62))
    rng = np.random.default_rng(4)
    for col0, col1, ya, yb in ((x0 + 48, x1 - 6, y0 + 50, y0 + 80), (x0 + 6, x0 + 44, y0 + 84, y1 - 6),
                               (x0 + 48, x1 - 6, y0 + 84, y1 - 6)):           # the columns: lines of grey 'text'
        for yy in range(ya, yb, 3):
            L = int((col1 - col0) * rng.uniform(0.7, 1.0))
            F.rect(img, col0, yy, col0 + L, yy, (96, 92, 84))
    sub = img[y0:y1, x0:x1].astype(np.float32)               # damp: a brown tide mark at the bottom right, yellowed edges
    yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0].astype(np.float32)
    d = np.hypot((xx - (x1 - x0)) / 60.0, (yy - (y1 - y0)) / 70.0)
    stain = np.clip(1.2 - d, 0, 1) * 0.45
    sub = sub * (1 - stain[..., None]) + np.array((150, 118, 74), np.float32) * stain[..., None]
    edge = np.minimum.reduce([xx, yy, (x1 - x0) - 1 - xx, (y1 - y0) - 1 - yy])
    yel = np.clip(1 - edge / 6.0, 0, 1) * 0.35
    sub = sub * (1 - yel[..., None]) + np.array((190, 160, 100), np.float32) * yel[..., None]
    img[y0:y1, x0:x1] = np.clip(sub, 0, 255).astype(np.uint8)


def fire_flipbook():
    """8 frames of a pixel-art flame tongue cluster, rising and flickering; RGBA, alpha cut-out (0 / 255)"""
    W, H = FIRE_FW * FIRE_FRAMES, FIRE_FH
    out = np.zeros((H, W, 4), np.uint8)
    ramp = np.array([(70, 10, 4), (150, 28, 6), (214, 70, 10), (246, 130, 24), (255, 190, 60), (255, 236, 150)], np.float32)
    yy, xx = np.mgrid[0:H, 0:FIRE_FW].astype(np.float32)
    v = 1.0 - (yy + 0.5) / H                                    # 0 at the bottom, 1 at the top
    u = (xx + 0.5) / FIRE_FW - 0.5
    for f in range(FIRE_FRAMES):
        t = f / FIRE_FRAMES
        p = np.stack([xx / 9.0, (yy / 9.0) + t * 7.1, np.full_like(xx, 1.7 + math.sin(t * 2 * math.pi) * 0.6)], -1).reshape(-1, 3)
        n1 = fbm(p, 1.0, 3, seed=31).reshape(xx.shape)
        p2 = np.stack([xx / 4.0, (yy / 4.0) + t * 13.0, np.full_like(xx, 0.3 + t)], -1).reshape(-1, 3)
        n2 = fbm(p2, 1.0, 2, seed=32).reshape(xx.shape)
        sway = 0.06 * math.sin(2 * math.pi * t + 0.7) * v
        width = 0.40 * (1.0 - v) ** 0.8 + 0.03                  # a tapering body, wide at the base
        body = width - np.abs(u - sway) * (1.0 + 0.9 * (n1 - 0.5)) - 0.05 * (n2 - 0.5)
        heat = body * 2.2 + (n1 - 0.5) * 0.55 + (n2 - 0.5) * 0.35 - v * 0.35
        tongues = (n2 > 0.58) & (v > 0.40) & (np.abs(u - sway) < 0.20) & (v < 0.86)   # loose tongues above the body
        heat = np.where(tongues, np.maximum(heat, 0.10 + (n2 - 0.58) * 1.5), heat)
        a = heat > 0.04
        lvl = np.clip((heat - 0.04) / 0.62, 0, 0.999) * (len(ramp) - 1)
        bay = np.tile(VT.BAYER, (H // 4 + 1, FIRE_FW // 4 + 1))[:H, :FIRE_FW]
        idx = np.clip(np.floor(lvl + bay - 0.5), 0, len(ramp) - 1).astype(np.int32)
        col = ramp[idx]
        fr = np.zeros((H, FIRE_FW, 4), np.uint8)
        fr[..., :3] = col.astype(np.uint8)
        fr[..., 3] = np.where(a, 255, 0)
        fr[..., :3][~a] = (70, 10, 4)                          # the cut-out texels keep a dark ember colour (no halo at mips)
        out[:, f * FIRE_FW:(f + 1) * FIRE_FW] = fr
    return out


def ice_tile():
    """64 x 64 tileable: clear blue-white glaze with milky rime streaks, trapped bubbles; 24 colours, Bayer"""
    n = ICE_N
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    ang = 2 * np.pi * np.stack([xx / n, yy / n], -1)
    p = np.stack([np.cos(ang[..., 0]) * 1.6, np.sin(ang[..., 0]) * 1.6, np.cos(ang[..., 1]) * 1.6 + np.sin(ang[..., 1]) * 0.9],
                 -1).reshape(-1, 3)
    n1 = fbm(p, 1.0, 3, seed=41).reshape(n, n)
    p2 = np.stack([np.cos(ang[..., 0]) * 4.0, np.sin(ang[..., 0]) * 4.0, np.sin(ang[..., 1]) * 0.6], -1).reshape(-1, 3)
    streak = fbm(p2, 1.0, 2, seed=42).reshape(n, n)
    base = np.array((168, 196, 214), np.float32)
    milky = np.array((228, 236, 240), np.float32)
    deep = np.array((112, 146, 170), np.float32)
    t = np.clip((n1 - 0.35) * 1.8, 0, 1)
    c = base[None, None] * (1 - t[..., None]) + milky[None, None] * t[..., None]
    s = np.clip((streak - 0.55) * 4.0, 0, 1)
    c = c * (1 - 0.5 * s[..., None]) + milky * 0.5 * s[..., None]
    d = np.clip((0.40 - n1) * 3.0, 0, 1)
    c = c * (1 - d[..., None]) + deep * d[..., None]
    rng = np.random.default_rng(43)
    for _ in range(22):                                         # bubbles: a light texel with a dark one under it
        bx, by = rng.integers(0, n), rng.integers(0, n)
        c[by, bx] = (240, 246, 248)
        c[(by + 1) % n, bx] = c[(by + 1) % n, bx] * 0.8
    q = np.floor(c / 255.0 * 23 + VT.BAYER[np.arange(n)[:, None] % 4, np.arange(n)[None] % 4][..., None] - 0.5) / 23
    return (np.clip(q, 0, 1) * 255 + 0.5).astype(np.uint8)


def cracked_glass():
    """128 x 128 RGBA, UV 0..1 over the windscreen: grime, a bullseye impact low on the passenger side with radial and
    ring cracks (opaque white), the glass between them at alpha 0.35"""
    n = 128
    img = np.zeros((n, n, 4), np.float32)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    p = np.stack([xx / 40.0, yy / 40.0, np.full_like(xx, 0.5)], -1).reshape(-1, 3)
    g = fbm(p, 1.0, 3, seed=51).reshape(n, n)
    img[..., :3] = np.array((120, 128, 122), np.float32)[None, None] * (0.85 + 0.3 * g[..., None])
    img[..., 3] = 0.30 + 0.25 * np.clip((g - 0.45) * 2, 0, 1) + 0.25 * np.clip((yy / n - 0.75) * 3, 0, 1)   # grime low
    cx, cy = 34.0, 92.0                                         # the impact (image y down: low on the screen)
    crack = np.zeros((n, n), bool)
    rng = np.random.default_rng(52)
    for k in range(14):                                         # radial cracks, jagged
        a = k / 14 * 2 * np.pi + rng.uniform(-0.15, 0.15)
        x, y, L = cx, cy, rng.uniform(25, 95)
        s = 0.0
        while s < L:
            a += rng.uniform(-0.25, 0.25)
            x += math.cos(a)
            y += math.sin(a)
            s += 1
            if 0 <= int(x) < n and 0 <= int(y) < n:
                crack[int(y), int(x)] = True
    for r in (5.0, 9.0, 15.0, 24.0):                            # ring cracks round the impact
        d = np.abs(np.hypot(xx - cx, yy - cy) - r - 1.5 * np.sin(np.arctan2(yy - cy, xx - cx) * 5 + r))
        crack |= (d < 0.55) & (rng.random((n, n)) > 0.25)
    core = np.hypot(xx - cx, yy - cy) < 3.0
    img[crack | core, :3] = (226, 232, 230)
    img[crack | core, 3] = 0.92
    out = np.zeros((n, n, 4), np.uint8)
    out[..., :3] = np.clip(img[..., :3], 0, 255).astype(np.uint8)
    out[..., 3] = (np.clip(img[..., 3], 0, 1) * 255 + 0.5).astype(np.uint8)
    return out


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (24, 24, 24)
    draw_door(img)
    draw_paper(img)
    paths = {}
    for name, a, mode in (('Panel_BaseColor', img, 'RGB'), ('Fire_BaseColor', fire_flipbook(), 'RGBA'),
                          ('Ice_BaseColor', ice_tile(), 'RGB'), ('GlassCracked_BaseColor', cracked_glass(), 'RGBA')):
        paths[name] = os.path.join(out, f'T_World_{name}.png')
        Image.fromarray(a, mode).save(paths[name])
    json.dump(dict(size=N, regions=REG, paper_date=PAPER_DATE, fire=dict(frames=FIRE_FRAMES, frame_px=[FIRE_FW, FIRE_FH],
                                                                         layout='frames left to right, u = frame / 8'),
                   ice=dict(tile_px=ICE_N, px_per_m=64)),
              open(os.path.join(out, 'world_panel_regions.json'), 'w'), indent=1, ensure_ascii=False)
    return paths


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'world')))
