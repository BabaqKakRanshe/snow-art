"""T_Lens_BaseColor.png / T_Lens_Emission.png (64 px, 32 px per region: PS1 / PSX texel size close to the airframe's
at arm's length; few grey levels, ordered dither, point-sampled).
Grey patterns multiplied by the lens tint (_BaseColor) in Unity; the emission map shapes the glow the Rig drives.
Regions (UV, origin bottom-left): ribbed side of a round lens u 0-0.5 v 0.5-1; dome cap u 0.5-1 v 0.5-1;
nav lens (nose of the wingtip housing) u 0-0.5 v 0-0.5; flat cover with a reflector (landing light) u 0.5-1 v 0-0.5.
python3 lens_tex_v13.py <out_dir>"""
import sys, os
import numpy as np
from PIL import Image

out = sys.argv[1] if len(sys.argv) > 1 else '.'
os.makedirs(out, exist_ok=True)
N, H = 64, 32
BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0


def quant(img, levels=8):
    """ordered dither to 'levels' grey steps (PSX look)"""
    h, w = img.shape
    t = np.tile(BAYER, (h // 4 + 1, w // 4 + 1))[:h, :w]
    q = np.floor(np.clip(img, 0, 1) * (levels - 1) + t) / (levels - 1)
    return np.clip(q, 0, 1)


yy, xx = np.mgrid[0:H, 0:H].astype(np.float32)
u, v = (xx + 0.5) / H, 1.0 - (yy + 0.5) / H         # region-local UV (v up)


def ribbed_side():
    """around (u) x along the axis (v): Fresnel rings as horizontal bands, a darker reflector shell behind the bulb,
    the bulb as a bright spot (lens base at v = 0, dome starts at v = 0.6)"""
    band = 0.5 + 0.5 * np.cos(2 * np.pi * v * 5.0)
    base = 0.62 + 0.20 * band
    shell = np.exp(-((u - 0.5) / 0.16) ** 2) * (v < 0.55)
    base -= 0.16 * shell
    bulb = np.exp(-(((u - 0.5) / 0.07) ** 2 + ((v - 0.30) / 0.10) ** 2))
    glint = np.exp(-(((u - 0.18) / 0.05) ** 2)) * 0.18
    col = np.clip(base + 0.30 * bulb + glint, 0, 1)
    emi = np.clip(0.55 + 0.25 * band - 0.20 * shell + 0.55 * bulb, 0, 1)
    return col, emi


def dome_cap():
    r = np.hypot(u - 0.5, v - 0.5) * 2
    rings = 0.5 + 0.5 * np.cos(2 * np.pi * r * 3.0)
    col = 0.66 + 0.18 * rings + 0.25 * np.exp(-(r / 0.30) ** 2)       # corners keep the rim value (no black at mips)
    emi = 0.60 + 0.20 * rings + 0.40 * np.exp(-(r / 0.35) ** 2)
    return np.clip(col, 0, 1), np.clip(emi, 0, 1)


def nav_lens():
    """u along the housing (0 = nose, 1 = gasket), v across: vertical prism ribs, the bulb near the gasket"""
    ribs = 0.5 + 0.5 * np.cos(2 * np.pi * u * 4.0)
    col = 0.64 + 0.16 * ribs
    bulb = np.exp(-(((u - 0.78) / 0.12) ** 2 + ((v - 0.5) / 0.18) ** 2))
    col += 0.30 * bulb + 0.14 * np.exp(-((v - 0.80) / 0.06) ** 2)          # bulb + top glint
    emi = 0.50 + 0.20 * ribs + 0.60 * bulb
    return np.clip(col, 0, 1), np.clip(emi, 0, 1)


def flat_reflector():
    """landing light behind a clear cover: parabolic reflector rings, bulb with its small shield"""
    r = np.hypot((u - 0.5) * 1.55, v - 0.5) * 2                # cover is wider than tall
    refl = 0.5 + 0.5 * np.cos(2 * np.pi * r * 2.5)
    col = np.where(r < 0.95, 0.48 + 0.30 * refl, 4 / 7)               # outside the reflector: one exact grey step (no dots)
    bulb = np.exp(-(r / 0.16) ** 2)
    shield = (np.abs(u - 0.5) < 0.04) & (np.abs(v - 0.5) < 0.04)
    col = col + 0.40 * bulb - 0.35 * shield
    col += 0.18 * np.exp(-(((u - 0.25) / 0.05) ** 2 + ((v - 0.72) / 0.09) ** 2))   # glint on the cover
    emi = np.where(r < 0.95, 0.35 + 0.35 * refl, 0.2) + 0.70 * bulb
    return np.clip(col, 0, 1), np.clip(emi, 0, 1)


C = np.zeros((N, N), np.float32)
E = np.zeros((N, N), np.float32)
for (fx, fy), fn in (((0, 0), ribbed_side), ((1, 0), dome_cap), ((0, 1), nav_lens), ((1, 1), flat_reflector)):
    c, e = fn()
    C[fy * H:(fy + 1) * H, fx * H:(fx + 1) * H] = c
    E[fy * H:(fy + 1) * H, fx * H:(fx + 1) * H] = e
Cq, Eq = quant(C, 8), quant(E, 6)
Image.fromarray((np.stack([Cq] * 3, -1) * 255).round().astype(np.uint8), 'RGB').save(os.path.join(out, 'T_Lens_BaseColor.png'))
Image.fromarray((np.stack([Eq] * 3, -1) * 255).round().astype(np.uint8), 'RGB').save(os.path.join(out, 'T_Lens_Emission.png'))
print('T_Lens written to', out, 'base mean', round(float(Cq.mean()), 3), 'emission mean', round(float(Eq.mean()), 3))
