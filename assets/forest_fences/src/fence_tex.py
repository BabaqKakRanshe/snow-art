"""Textures of the fence kit (Forest Update 7) that are drawn, not baked.

Sign panel T_Fence_Panel (256 x 256, pixel art, 160 px/m on the faces as the road's and the base's signs; German first,
English under it - the project's rule for wall signs):
  halt     HALT! KONTROLLPUNKT / STOP! CHECKPOINT: white board, red border, on two posts at the checkpoint
  sperr    SPERRGEBIET - BETRETEN VERBOTEN! / RESTRICTED AREA - NO ENTRY!: a plate on the concrete fence
  noentry  the round no-entry sign (Zeichen 267: red disc, white bar) at the chicane
Cut-outs (RGBA; alpha 0 between the wires, the RGB under the holes = the wire's mean colour so that mip levels do not
darken; wires 2 px wide; drawn so that they tile):
  netting  chain-link, diamonds 16 px across (12.5 cm at 0.5 m per 64 px), woven: each wire shifted by its own +-1 px
           and lit on one edge, knots alternating over / under - half the frequency of Updates 4-5's 1-px 8-px
           lattice (the moire), and not a perfect lattice (what is left of the moire turns into noise)
  barbed   twisted two-wire strands 2 px, barbs every 0.125 m (X, 5 px), at given heights in a band
  razor    the concertina's razor tape: a 2 px core with blades every 0.0625 m, 0.06 m band
The replacements (the same file names, sizes, tilings and strand heights as Updates 4-5, the new drawing):
  T_Base/Kpp/Yard/Road_ChainLink, T_Base/Kpp/Yard/Road_Barbed, T_Base_Rust.
python3 fence_tex.py [out_dir] [repl_dir]"""
import os, sys, json, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pxfont as F
import van2_tex as VT
import kpp_tex as KT                                       # the umlaut glyphs (patched into pxfont on import)
import road_tex as RTX                                     # proportional setting, wear
from noise import fbm
import fence_spec as S

N = 256
PPM = 160.0
INK, WHITE = (26, 24, 22), (236, 232, 220)
RED, RED_D = (196, 36, 26), (150, 30, 22)
GREY_T = (92, 88, 82)


def _px(m):
    return int(round(m * PPM))


SIZES = [('halt', _px(S.HALT['w']), _px(S.HALT['h'])), ('sperr', _px(S.SIGN['w']), _px(S.SIGN['h'])),
         ('noentry', _px(2 * S.NOENTRY['r']), _px(2 * S.NOENTRY['r']))]
import main_tex as MT
REG = MT.pack(SIZES, n=N)


def uv(name, n=N):
    return VT.uv(REG[name], n)


def draw_halt(img):
    x0, y0, x1, y1 = REG['halt']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, WHITE)
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, RED, 5)
    cx = (x0 + x1) / 2
    RTX.prop_text(img, cx, y0 + 27, 'HALT!', F.F57, RED, scale=3)
    RTX.prop_text(img, cx, y0 + 52, 'KONTROLLPUNKT', F.F57, INK, scale=2)
    F.rect(img, x0 + 24, y0 + 66, x1 - 25, y0 + 66, (170, 164, 156))
    RTX.prop_text(img, cx, y0 + 82, 'STOP!', F.F57, RED_D, scale=2)
    RTX.prop_text(img, cx, y0 + 101, 'CHECKPOINT', F.F57, GREY_T, scale=2)
    RTX._wear(img, (x0, y0, x1, y1), 701, fade=0.06, grime=(118, 104, 84))
    KT._age(img, (x0, y0, x1, y1), 702, 60, 0.30, (120, 74, 44))


def draw_sperr(img):
    x0, y0, x1, y1 = REG['sperr']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, WHITE)
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, RED, 4)
    cx = (x0 + x1) / 2
    RTX.prop_text(img, cx, y0 + 20, 'SPERRGEBIET', F.F57, RED, scale=2)
    RTX.prop_text(img, cx, y0 + 38, 'BETRETEN VERBOTEN!', F.F57, INK, scale=1)
    F.rect(img, x0 + 18, y0 + 50, x1 - 19, y0 + 50, (170, 164, 156))
    RTX.prop_text(img, cx, y0 + 63, 'RESTRICTED AREA', F.F57, RED_D, scale=1)
    RTX.prop_text(img, cx, y0 + 76, 'NO ENTRY!', F.F57, GREY_T, scale=1)
    RTX._wear(img, (x0, y0, x1, y1), 703, fade=0.10, grime=(110, 98, 80))
    KT._age(img, (x0, y0, x1, y1), 704, 80, 0.40, (130, 70, 40))


def draw_noentry(img):
    x0, y0, x1, y1 = REG['noentry']
    img[y0:y1, x0:x1] = (150, 152, 148)                        # the galvanised rim shows past the disc's corners
    cx, cy = (x0 + x1 - 1) / 2, (y0 + y1 - 1) / 2
    r = (x1 - x0) / 2
    F.disc(img, cx, cy, r - 0.5, (232, 230, 224))
    F.disc(img, cx, cy, r - 3.0, (190, 30, 24))
    bw, bh = int(r * 1.25), max(4, int(r * 0.30))
    F.rect(img, int(cx - bw / 2), int(cy - bh / 2), int(cx + bw / 2), int(cy + bh / 2), (240, 238, 232))
    RTX._wear(img, (x0, y0, x1, y1), 705, fade=0.08, grime=(110, 98, 80))


# ---------------------------------------------------------------- cut-outs
GALV = np.array((150, 156, 152), np.float64)
RUST = np.array((120, 66, 34), np.float64)


def _fill_rgb(rgba):
    """the RGB under the holes = the wires' mean colour: the mip levels average to the wire's colour, not to black"""
    a = rgba[..., 3] > 0
    if a.any():
        mean = rgba[..., :3][a].mean(0)
        rgba[..., :3] = np.where(a[..., None], rgba[..., :3], mean.astype(np.uint8))
    return rgba


def netting(n=64, period=16, seed=51, rust=0.22, base=GALV):
    """woven chain-link that tiles: two families of 2-px diagonal wires (x + y and x - y), each wire shifted by its own
    -1 / 0 / +1 px, the lit edge up-left, knots over / under in turn"""
    assert n % period == 0
    rng = np.random.default_rng(seed)
    k_n = n // period
    jA, jB = rng.integers(-1, 2, k_n), rng.integers(-1, 2, k_n)
    yy, xx = np.mgrid[0:n, 0:n]
    sA, sB = xx + yy, xx - yy + n
    kA, kB = (sA // period) % k_n, (sB // period) % k_n
    dA = (sA + jA[kA]) % period
    dB = (sB + jB[kB]) % period
    wA, wB = dA < 2, dB < 2
    wire = wA | wB
    q3 = np.stack([xx.ravel() / 11.0, yy.ravel() / 11.0, np.zeros(xx.size)], -1).astype(np.float32)
    nz = fbm(q3, 1.0, 2, seed=seed).reshape(n, n)
    lift = np.where(wA, 0.92 + 0.16 * ((kA * 7) % 3) / 2.0, 0.92 + 0.16 * ((kB * 5) % 3) / 2.0)   # wire to wire
    shade = np.where((wA & (dA == 0)) | (wB & (dB == 0)), 1.12, 0.86)                            # lit edge, shadow edge
    col = base[None, None] * (0.86 + 0.26 * nz[..., None]) * lift[..., None] * shade[..., None]
    knot = wA & wB
    over_a = ((kA + kB) % 2 == 0)
    col = np.where((knot & ~over_a)[..., None] & wB[..., None] & (dA > 0)[..., None], col * 0.80, col)
    col = np.where((knot & over_a)[..., None] & wA[..., None] & (dB > 0)[..., None], col * 0.80, col)
    rmask = (nz > 1.0 - rust)[..., None] & wire[..., None]
    col = np.where(rmask, col * 0.45 + RUST * 0.55, col)
    rgba = np.zeros((n, n, 4), np.uint8)
    rgba[..., :3] = np.clip(col, 0, 255).astype(np.uint8)
    rgba[..., 3] = np.where(wire, 255, 0)
    return _fill_rgb(rgba)


def barbed(w, h, rel, height, seed=61, rusty=False):
    """strands of two twisted wires (2 px), barbs (X of 5 px) every 16 px, at rel (metres from the band's foot)"""
    rgba = np.zeros((h, w, 4), np.uint8)
    lite = np.array((136, 138, 132), np.float64) if not rusty else np.array((124, 70, 40), np.float64)
    dark = np.array((84, 82, 78), np.float64) if not rusty else np.array((74, 42, 26), np.float64)
    q3 = np.stack([np.arange(w) / 9.0, np.zeros(w), np.zeros(w)], -1).astype(np.float32)
    nz = fbm(q3, 1.0, 2, seed=seed)
    for k, rr in enumerate(rel):
        r = int(round((height - rr) / height * (h - 1)))
        r = min(max(r, 3), h - 4)
        for x in range(w):
            up = (x // 3 + k) % 2 == 0
            f = 0.85 + 0.3 * nz[x]
            for yy_, c in ((r - 1, lite if up else dark), (r, dark if up else lite)):
                rgba[yy_, x, :3] = np.clip(c * f, 0, 255)
                rgba[yy_, x, 3] = 255
        for bx in range(5 + k * 5, w + 5, 16):
            for dx, dy in ((-2, -3), (-1, -2), (1, 1), (2, 2), (-2, 2), (-1, 1), (1, -2), (2, -3)):
                xx_, yy_ = (bx + dx) % w, r + dy
                if 0 <= yy_ < h:
                    rgba[yy_, xx_, :3] = np.clip((lite if dy < 0 else dark), 0, 255)
                    rgba[yy_, xx_, 3] = 255
    return _fill_rgb(rgba)


def razor(w=64, h=12, seed=71):
    """razor tape: a 2 px core and diamond blades every 8 px, galvanised, a little rust"""
    rgba = np.zeros((h, w, 4), np.uint8)
    yc = h // 2
    lite, dark = np.array((176, 180, 176)), np.array((104, 108, 106))
    for x in range(w):
        rgba[yc - 1, x, :3], rgba[yc, x, :3] = lite, dark
        rgba[yc - 1:yc + 1, x, 3] = 255
    for bx in range(2, w, 8):
        for dx in range(-3, 4):
            hh = 4 - abs(dx)
            for dy in range(1, hh + 1):
                for yy_, c in ((yc - 1 - dy, lite), (yc + dy, dark)):
                    if 0 <= yy_ < h:
                        rgba[yy_, (bx + dx) % w, :3] = c
                        rgba[yy_, (bx + dx) % w, 3] = 255
    rr = (np.arange(w)[None, :] * 7 + np.arange(h)[:, None] * 13) % 17 == 0
    rgba[..., :3] = np.where((rr & (rgba[..., 3] > 0))[..., None], np.array((122, 76, 46), np.uint8), rgba[..., :3])
    return _fill_rgb(rgba)


def save(arr, path):
    Image.fromarray(arr, 'RGBA' if arr.shape[-1] == 4 else 'RGB').save(path)
    return path


# the replacements of Updates 4-5's cut-outs: name -> (kind, size, args)
REPL = {
    'T_Base_ChainLink': ('net', (64, 64), dict(seed=51)),
    'T_Kpp_ChainLink': ('net', (64, 64), dict(seed=52)),
    'T_Yard_ChainLink': ('net', (64, 64), dict(seed=52)),
    'T_Road_ChainLink': ('net', (64, 64), dict(seed=53, rust=0.30)),
    'T_Base_Barbed': ('barb', (64, 67), dict(rel=(0.141, 0.311, 0.481), height=0.52)),
    'T_Kpp_Barbed': ('barb', (64, 46), dict(rel=(0.06, 0.18, 0.30), height=0.36)),
    'T_Yard_Barbed': ('barb', (64, 46), dict(rel=(0.06, 0.18, 0.30), height=0.36)),
    'T_Road_Barbed': ('barb', (64, 54), dict(rel=(0.06, 0.21, 0.36), height=0.42)),
    'T_Base_Rust': ('barb', (64, 12), dict(rel=(0.04,), height=0.08, rusty=True)),
}


def replacements(out):
    os.makedirs(out, exist_ok=True)
    done = {}
    for name, (kind, (w, h), kw) in REPL.items():
        if kind == 'net':
            arr = netting(w, **kw)
        else:
            arr = barbed(w, h, **kw)
        done[name] = save(arr, os.path.join(out, name + '_A_px.png'))
    return done


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (128, 128, 124)
    draw_halt(img)
    draw_sperr(img)
    draw_noentry(img)
    p = save(img, os.path.join(out, 'T_Fence_Panel_BaseColor.png'))
    pn = save(netting(64, seed=57), os.path.join(out, 'T_Fence_ChainLink.png'))
    b = S.BRACKET
    pb = save(barbed(64, 66, rel=b['strands'], height=b['band'], seed=62), os.path.join(out, 'T_Fence_Barbed.png'))
    c = S.CHAIN
    pc = save(barbed(64, 67, rel=c['strands'], height=c['band'], seed=63), os.path.join(out, 'T_Fence_ChainBarbed.png'))
    pr = save(razor(), os.path.join(out, 'T_Fence_Razor.png'))
    json.dump(dict(size=N, ppm=PPM, regions={k: list(v) for k, v in REG.items()},
                   netting=dict(size=64, metres_per_tile=0.5, diamond_px=16, wire_px=2),
                   barbed=dict(size=[64, 66], metres_per_tile=[0.5, b['band']], strands=list(b['strands'])),
                   chain_barbed=dict(size=[64, 67], metres_per_tile=[0.5, c['band']], strands=list(c['strands'])),
                   razor=dict(size=[64, 12], metres_per_tile=[0.5, 0.06])),
              open(os.path.join(out, 'fence_panel_regions.json'), 'w'), indent=1)
    return p, pn, pb, pc, pr


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'fence')
    print(build(o))
    r = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'tex', 'fence', 'replacements')
    print(replacements(r))
