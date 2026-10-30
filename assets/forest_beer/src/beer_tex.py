"""forest_beer label textures (user 29.10: «приступай» on concept_v1/cans_1.png, docs/gdd/items/beer). Five invented 1991
Harz beers in steel cans, the stay-on tab on all of them (QUESTIONS.md 3):
  Pils      - «HARZER PILS», 0.5 l, green and silver, mountain and firs;
  Export    - «ILSETALER EXPORT», 0.33 l, cream and brown, the town; cheap East;
  Schwarz   - «HEXENBRÄU SCHWARZBIER», 0.5 l, black and purple, the witch over the Brocken;
  Bock      - «BERGMANN BOCK», 0.5 l, red and gold, the miner with his lamp;
  Leicht    - «SCHNEEKÖNIG LEICHT», 0.33 l, white and blue, the snow crown;
  Kalo      - «KALOSCHNIZZER STARKBIER», 0.5 l, red and gold, the user's friend as a grinning miner (user 30.10: «1 делаем»
              on concept_v2/kalo_front_1.png, the left can).
The FRONT of each label is unwrapped from the picked concept itself (the top row is the cans seen face on, so a column x of
the picture is the angle asin((x - cx) / R) on the can): +-62 degrees, the cylinder's shading divided out. The BACK is
grown row by row from the colours at the edges of that strip and gets the brewery's small print (pixel font). The label
then gets grain and the PSX quantization (64 colours), point filter.
Label u: 0..1 once round the can, u = 0.5 the front (-y), u grows to +x; v: 0 the label's foot, 1 its top.
python beer_tex.py [out_dir]"""
import os, sys, json, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'lib'))
import pxfont as F
from noise import fbm

ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
CONCEPTS = os.path.join(ROOT, 'docs', 'gdd', 'items', 'beer')
CONCEPT = {'Kalo': 'concept_v2/kalo_front_1.png'}                       # the rest: concept_v1/cans_1.png
BRANDS = ('Pils', 'Export', 'Schwarz', 'Bock', 'Leicht', 'Kalo')
NAME = {'Pils': 'Harzer Pils', 'Export': 'Ilsetaler Export', 'Schwarz': 'Hexenbräu Schwarzbier', 'Bock': 'Bergmann Bock',
        'Leicht': 'Schneekönig Leicht', 'Kalo': 'Kaloschnizzer Starkbier'}
LITRES = {'Pils': 0.5, 'Export': 0.33, 'Schwarz': 0.5, 'Bock': 0.5, 'Leicht': 0.33, 'Kalo': 0.5}
ABV = {'Pils': 4.9, 'Export': 5.2, 'Schwarz': 4.9, 'Bock': 7.2, 'Leicht': 2.8, 'Kalo': 7.2}
# the top row of cans_1.png (1536 x 1024): x0, x1 of the body, y of the label's top and foot (under the neck, over the rim);
# Kalo: the left can of kalo_front_1.png (1536 x 1024), its straight side
SRC = {'Pils': (168, 366, 60, 468), 'Export': (421, 614, 200, 470), 'Schwarz': (669, 873, 58, 470),
       'Bock': (934, 1120, 58, 470), 'Leicht': (1205, 1406, 210, 470), 'Kalo': (287, 645, 120, 922)}
# the small print on the back: lines, ink, the ground colour
BACK = {'Pils': (('HARZER BRAUHAUS', 'SEIT 1869'), ('ZUTATEN: WASSER,', 'GERSTENMALZ, HOPFEN'), ('KUEHL LAGERN',), (226, 220, 196), (30, 86, 50)),
        'Export': (('VEB BRAUEREI', 'ILSETAL'), ('EXPORTBIER', 'HELL'), ('TGL 7764',), (96, 58, 30), (214, 206, 184)),
        'Schwarz': (('HEXENBRAEU', 'BROCKENBRAUEREI'), ('ZUTATEN: WASSER,', 'GERSTENMALZ, HOPFEN'), ('DUNKEL GEBRAUT',), (196, 176, 226), (26, 24, 28)),
        'Bock': (('BERGMANN', 'BRAUEREI'), ('STARKBIER', 'NACH ALTER ART'), ('GLUECK AUF!',), (226, 192, 108), (140, 30, 26)),
        'Leicht': (('SCHNEEKOENIG', 'LEICHTBIER'), ('NUR 2,8% VOL', 'WENIGER ALKOHOL'), ('KUEHL LAGERN',), (40, 92, 160), (222, 224, 226)),
        'Kalo': (('KALOSCHNIZZER', 'STARKBIER'), ('ZUTATEN: WASSER,', 'GERSTENMALZ, HOPFEN'), ('PROST, KUMPEL!',), (226, 192, 108), (158, 20, 18))}
W = 512                                   # once round (207 mm) -> 2470 px / m: the can is held at the eye
H = {0.5: 384, 0.33: 256}
FRONT_DEG, BLEND_DEG = 100.0, 26.0
# Kalo's print is drawn flat and its name runs to 0.95 R: spread linearly (no stretch at the ends) over +-68 degrees, to
# 0.975 R, and blend into the back only past that
MAP = {'Kalo': dict(front=68.0, blend=5.0, span=0.975, lin=True, outside=True)}


def unwrap(src, brand):
    x0, x1, yt, yf = SRC[brand]
    cx, R = (x0 + x1) / 2.0, (x1 - x0) / 2.0
    h = H[LITRES[brand]]
    mp = MAP.get(brand, dict(front=FRONT_DEG, blend=BLEND_DEG, span=0.90, lin=False, outside=False))
    fd = math.radians(mp['front'])
    out = np.zeros((h, W, 3), np.float32)
    u = (np.arange(W) + 0.5) / W
    th = (u - 0.5) * 2 * math.pi
    ys = yf - (np.arange(h) + 0.5) / h * (yf - yt)                          # row 0 of the image = the label's top
    ys = ys[::-1]
    # the concept paints the label as a print seen face on: its visible width (to 0.90 R, the dark rim left out) is
    # spread over +-FRONT_DEG of the can, so the whole name sits on the front half and wraps a little round the sides
    front = np.abs(th) <= fd
    tc = np.clip(th, -fd, fd)
    s = tc / fd if mp['lin'] else np.sin(tc * (90.0 / mp['front']))
    xs = cx + mp['span'] * R * s
    xi = np.clip(np.round(xs).astype(int), 0, src.shape[1] - 1)
    yi = np.clip(np.round(ys).astype(int), 0, src.shape[0] - 1)
    out[:] = src[yi][:, xi]
    # the cylinder's shading: each column's median brightness against the middle columns, smoothed, divided out
    lum = out.mean(2)
    med = np.median(lum, 0)
    mid = np.median(med[np.abs(th) < math.radians(12)])
    k = np.clip(med / max(mid, 1.0), 0.45, 1.3)
    k = np.convolve(np.pad(k, 9, mode='edge'), np.ones(19) / 19, mode='valid')
    gain = np.where(front, 1.0 / k, 1.0)
    out = out * gain[None, :, None]
    # the back: the trim bands (top and foot 14 % of rows) carry on round from the strip's edges, row by row; the rest is
    # the brand's ground colour (BACK) for the small print
    edge = (np.abs(th) > fd - math.radians(16)) & front
    row_col = np.median(out[:, edge], 1)                                                    # (h, 3)
    rc = np.stack([np.convolve(np.pad(row_col[:, c], 2, mode='edge'), np.ones(5) / 5, mode='valid') for c in range(3)], 1)
    rows = np.arange(h) / h
    trim = (rows < 0.14) | (rows > 0.86)
    ground = np.array(BACK[brand][4], np.float32)
    rc[~trim] = ground
    bd = math.radians(mp['blend'])
    a = np.clip((np.abs(th) - (fd if mp['outside'] else fd - bd)) / bd, 0, 1)
    out = out * (1 - a)[None, :, None] + rc[:, None, :] * a[None, :, None]
    return np.clip(out, 0, 255), rc


def back_print(img, brand, rc):
    h = img.shape[0]
    head, mid, foot, ink, _ = BACK[brand]
    lines = list(head) + [''] + list(mid) + [''] + list(foot) + ['', f'{LITRES[brand]:.2f}'.replace('0.50', '0,5').replace('0.33', '0,33') + ' L   ' + f'{ABV[brand]:.1f}'.replace('.', ',') + '% VOL']
    step = 9
    y0 = h // 2 - len(lines) * step // 2
    mask = np.zeros((h, W), bool)
    for i, ln in enumerate(lines):
        if not ln:
            continue
        m = F.text_mask(ln, F.F57 if i < 2 else F.F35)
        mh, mw = m.shape
        x = W // 2 - mw // 2
        y = y0 + i * step
        mask[y:y + mh, x:x + mw] |= m
    mask = np.roll(mask, W // 2, axis=1)                                     # centred on the back (u = 0)
    img[mask] = ink
    return img


def grain(img, seed, amount=6.0):
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    p = np.stack([xx / 64.0, yy / 64.0, np.full_like(xx, seed * 0.37)], -1).reshape(-1, 3)
    n = fbm(p, 7.0, 2, seed=seed).reshape(h, w) - 0.5
    return np.clip(img + n[..., None] * amount * 2, 0, 255)


def quantize(img, n=64):
    im = Image.fromarray(img.astype(np.uint8)).quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    return np.asarray(im.convert('RGB'))


def build(out):
    os.makedirs(out, exist_ok=True)
    srcs, paths = {}, {}
    for i, b in enumerate(BRANDS):
        c = CONCEPT.get(b, 'concept_v1/cans_1.png')
        if c not in srcs:
            srcs[c] = np.asarray(Image.open(os.path.join(CONCEPTS, c)).convert('RGB')).astype(np.float32)
        img, rc = unwrap(srcs[c], b)
        img = grain(img, 40 + i)
        img = back_print(img.astype(np.uint8), b, rc)
        img = quantize(img)
        p = os.path.join(out, f'T_Beer_{b}.png')
        Image.fromarray(img).save(p)
        paths[f'T_Beer_{b}'] = p
    json.dump(dict(brands=BRANDS, names=NAME, litres=LITRES, abv=ABV, size={b: [W, H[LITRES[b]]] for b in BRANDS},
                   concept={b: 'docs/gdd/items/beer/' + CONCEPT.get(b, 'concept_v1/cans_1.png') for b in BRANDS}, src=SRC),
              open(os.path.join(out, 'beer_labels.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    return paths


if __name__ == '__main__':
    print(json.dumps(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex')), indent=1))
