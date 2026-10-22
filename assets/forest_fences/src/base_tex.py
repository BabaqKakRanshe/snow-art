"""Panel atlas of the base prefabs (256 x 256, pixel art, point-filtered, 160 px/m on the faces as the road's signs), in
the project's pixel font; German first, English under it (the project's rule for wall signs):
  hatch    SCHACHT - ABSTURZGEFAHR / SHAFT - DANGER OF FALLING: white plate, red rule, on two posts by the hatch
  heli     HUBSCHRAUBERLANDEPLATZ / HELIPAD - UNBEFUGTEN BETRETEN VERBOTEN / AUTHORISED PERSONS ONLY: the station's
           blue, on two posts by the pad
  ice      VORSICHT EISFALL / BEWARE OF FALLING ICE: the warning triangle on white, strapped to the radio mast's leg
The faces glow faintly at night as the road's signs (the material's emission = the albedo at 0.06).
Cut-outs (RGBA, alpha 0 between the wires): T_Base_ChainLink (64 x 64, 0.5 m per tile, the checkpoint's galvanised
mesh), T_Base_Barbed (64 x 67, three strands over the fence's 45-degree outrigger: 0.141 / 0.311 / 0.481 m along a
0.52 m band, 0.5 m per tile along), T_Base_Rust (64 x 12: one rusty two-strand barbed wire with its barbs in a 0.08 m
band, 0.5 m per tile) for the old boundary fence.
python3 base_tex.py [out_dir] -> T_Base_Panel_BaseColor.png, T_Base_ChainLink.png, T_Base_Barbed.png, T_Base_Rust.png"""
import os, sys, json, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pxfont as F
import van2_tex as VT
import kpp_tex as KT                                       # the umlaut glyphs (patched into pxfont on import)
import yard_tex as YT
import road_tex as RTX                                     # proportional setting, wear, the barbed-wire band
from noise import fbm

N = 256
PPM = 160.0
INK, WHITE = (26, 24, 22), (236, 232, 220)
RED = (196, 36, 26)
BLUE = (34, 60, 108)
YELLOW = (236, 190, 30)


def _px(m):
    return int(round(m * PPM))


SIZES = [('hatch', _px(0.93), _px(0.28)), ('heli', _px(1.20), _px(0.42)), ('ice', _px(0.42), _px(0.34))]
import main_tex as MT
REG = MT.pack(SIZES, n=N)


def uv(name, n=N):
    return VT.uv(REG[name], n)


def draw_hatch(img):
    x0, y0, x1, y1 = REG['hatch']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, WHITE)
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, RED, 2)
    cx = (x0 + x1) / 2
    RTX.prop_text(img, cx, y0 + 13, 'SCHACHT', F.F57, RED, scale=2)
    RTX.prop_text(img, cx, y0 + 25, 'ABSTURZGEFAHR', F.F57, INK, scale=1)
    F.rect(img, x0 + 20, y0 + 30, x1 - 21, y0 + 30, (150, 146, 138))
    RTX.prop_text(img, cx, y0 + 36, 'SHAFT - DANGER OF FALLING', F.F35, (70, 66, 60), scale=1)
    RTX._wear(img, (x0, y0, x1, y1), 81, fade=0.05, grime=(118, 104, 84))
    KT._age(img, (x0, y0, x1, y1), 82, 40, 0.30, (120, 74, 44))


def draw_heli(img):
    x0, y0, x1, y1 = REG['heli']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, BLUE)
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, (232, 234, 236), 2)
    bx0, by0 = x0 + 7, y0 + 7                                  # the H in a white square at the left
    s = (y1 - y0) - 14
    F.rect(img, bx0, by0, bx0 + s - 1, by0 + s - 1, (236, 238, 240))
    hw = max(3, s // 6)
    F.rect(img, bx0 + s // 5, by0 + s // 6, bx0 + s // 5 + hw - 1, by0 + s - s // 6 - 1, BLUE)
    F.rect(img, bx0 + s - s // 5 - hw, by0 + s // 6, bx0 + s - s // 5 - 1, by0 + s - s // 6 - 1, BLUE)
    F.rect(img, bx0 + s // 5, by0 + s // 2 - hw // 2, bx0 + s - s // 5 - 1, by0 + s // 2 + hw // 2, BLUE)
    tx = (bx0 + s + 4 + x1 - 6) / 2
    RTX.prop_text(img, tx, y0 + 14, 'HUBSCHRAUBER-', F.F57, (236, 238, 240), scale=1)
    RTX.prop_text(img, tx, y0 + 23, 'LANDEPLATZ', F.F57, (236, 238, 240), scale=1)
    RTX.prop_text(img, tx, y0 + 35, 'HELIPAD', F.F57, (196, 206, 226), scale=2)
    RTX.prop_text(img, tx, y0 + 47, 'UNBEFUGTEN ZUTRITT VERBOTEN', F.F35, (236, 238, 240), scale=1)
    RTX.prop_text(img, tx, y0 + 55, 'AUTHORISED PERSONS ONLY', F.F35, (196, 206, 226), scale=1)
    RTX._wear(img, (x0, y0, x1, y1), 83, fade=0.12, grime=(80, 84, 72))


def draw_ice(img):
    x0, y0, x1, y1 = REG['ice']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, WHITE)
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, (60, 58, 54), 1)
    cx, top = (x0 + x1) / 2, y0 + 4                           # the warning triangle (yellow, black border, a falling block)
    h = 20
    for k in range(h):
        half = (k + 1) * 0.62
        F.rect(img, int(cx - half), top + k, int(cx + half), top + k, INK)
    for k in range(3, h - 2):
        half = (k - 2) * 0.62 - 0.5
        if half > 0:
            F.rect(img, int(cx - half), top + k, int(cx + half), top + k, YELLOW)
    F.rect(img, int(cx) - 2, top + 8, int(cx) + 1, top + 11, INK)
    F.rect(img, int(cx) - 1, top + 13, int(cx), top + 16, INK)
    RTX.prop_text(img, cx, y0 + 31, 'VORSICHT EISFALL', F.F35, INK, scale=1)
    RTX.prop_text(img, cx, y0 + 40, 'BEWARE OF', F.F35, (70, 66, 60), scale=1)
    RTX.prop_text(img, cx, y0 + 47, 'FALLING ICE', F.F35, (70, 66, 60), scale=1)
    RTX._wear(img, (x0, y0, x1, y1), 84, fade=0.05, grime=(118, 104, 84))
    KT._age(img, (x0, y0, x1, y1), 85, 25, 0.35, (120, 74, 44))


def rusty(path, w=64, h=12):
    """one old two-strand barbed wire, rusty, its barbs every 0.125 m, in a 0.08 m band (0.5 m per tile)"""
    rgba = np.zeros((h, w, 4), np.uint8)
    yc = h // 2
    xx = np.arange(w)
    q3 = np.stack([xx / 7.0, np.zeros(w), np.zeros(w)], -1).astype(np.float32)
    nz = fbm(q3, 1.0, 2, seed=93)
    for x in range(w):
        c = np.array((112, 60, 34)) * (0.75 + 0.5 * nz[x])
        d = np.array((70, 40, 26)) * (0.8 + 0.4 * nz[x])
        up = (x // 2) % 2 == 0
        rgba[yc - (1 if up else 0), x, :3], rgba[yc - (1 if up else 0), x, 3] = np.clip(c, 0, 255), 255
        rgba[yc - (0 if up else 1), x, :3], rgba[yc - (0 if up else 1), x, 3] = np.clip(d, 0, 255), 255
    for bx in range(3, w, 16):
        for dx, dy in ((-2, -3), (-1, -2), (1, 2), (2, 3), (-2, 3), (-1, 2), (1, -2), (2, -3)):
            xx_, yy_ = (bx + dx) % w, yc + dy
            if 0 <= yy_ < h:
                rgba[yy_, xx_, :3] = (98, 54, 32) if dy < 0 else (66, 38, 24)
                rgba[yy_, xx_, 3] = 255
    Image.fromarray(rgba, 'RGBA').save(path)
    return path


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (128, 128, 124)
    draw_hatch(img)
    draw_heli(img)
    draw_ice(img)
    p = os.path.join(out, 'T_Base_Panel_BaseColor.png')
    Image.fromarray(img, 'RGB').save(p)
    pc = YT.chainlink(os.path.join(out, 'T_Base_ChainLink.png'))
    pb = RTX.barbed(os.path.join(out, 'T_Base_Barbed.png'), w=64, h=67, rel=(0.141, 0.311, 0.481), height=0.52)
    pr = rusty(os.path.join(out, 'T_Base_Rust.png'))
    json.dump(dict(size=N, ppm=PPM, regions={k: list(v) for k, v in REG.items()},
                   chainlink=dict(size=64, metres_per_tile=0.5),
                   barbed=dict(size=[64, 67], metres_per_tile=[0.5, 0.52], strands_along_band=[0.141, 0.311, 0.481]),
                   rust=dict(size=[64, 12], metres_per_tile=[0.5, 0.08])),
              open(os.path.join(out, 'base_panel_regions.json'), 'w'), indent=1)
    return p, pc, pb, pr


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'base')
    print(build(o))
