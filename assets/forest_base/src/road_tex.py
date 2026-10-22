"""Panel atlas of the road prefabs (512 x 512, pixel art, point-filtered): the sign faces at a reading density (160 px/m;
the plates are a face + 15 mm all round, Update 3's), drawn in the project's pixel font as the station's other signs.
  Sign_Observatory  RADIOOBSERVATORIUM HOHENMOOS / RADIO OBSERVATORY - the station's blue (the main building's name plate)
  Sign_Viewpoint    AUSSICHTSPUNKT / VIEWPOINT, tourist brown;  Sign_Lookout  FEUERWACHTURM / FIRE LOOKOUT, forestry green
  Sign_Pump, Sign_Radar, Sign_Relay, Sign_Weather   PUMPWERK / PUMP STATION, RADAR, RELAISSTATION / RELAY STATION,
                    WETTERSTATION / WEATHER STATION, the station's blue
  Dist_11 .. Dist_03  OBSERVATORIUM x,x km, black on white (1,1 -> 0,9 -> 0,7 -> 2,3 -> 0,3: the fourth lies, as Update 3)
  gate              SPERRGEBIET / RESTRICTED AREA - ZUTRITT VERBOTEN / NO ENTRY: the checkpoint's sign (white plate, red
                    border, red title) on the zone gate's leaves
  z262              the weight limit 7,5 t (red ring, white field) at the bridge's ends
German first, English under it (the project's rule).  Retroreflective sheeting: the game lets these faces glow faintly at
night (the material's emission = this texture, Update 3's M_ObsSigns: 0.06).
T_Road_ChainLink (64 x 64 RGBA): the checkpoint's galvanised chain-link, 0.5 m per tile; T_Road_Barbed (64 x 54 RGBA):
three strands of barbed wire at 0.06 / 0.21 / 0.36 m over the foot of a 0.42 m band (Update 3's gate wires 2.50 / 2.65 /
2.80), 0.5 m per tile along.
python3 road_tex.py [out_dir] -> T_Road_Panel_BaseColor.png, T_Road_ChainLink.png, T_Road_Barbed.png, road_panel_regions.json"""
import os, sys, json, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pxfont as F
import van2_tex as VT
import kpp_tex as KT                                     # the umlaut glyphs (patched into pxfont on import)
import yard_tex as YT
import road_spec as S
from noise import fbm

# lower-case k, m, t for "km" and "7,5 t" (the font has capitals only; patched in as kpp_tex patches the umlauts)
for _k, _s in {'k': '#....|#....|#..#.|#.#..|##...|#.#..|#..#.', 'm': '.....|.....|##.#.|#.#.#|#.#.#|#.#.#|#.#.#',
               't': '.#...|.#...|####.|.#...|.#...|.#..#|..##.'}.items():
    F.F57['glyphs'][_k] = F._compile({'x': _s})['x']


def prop_mask(txt, font, scale=1):
    """proportional set: each glyph trimmed to its inked columns, 1 column apart, a space 3 columns (signs are set
    proportionally, as DIN 1451)"""
    h = font['h']
    cols, prev = [], ' '
    for ch in txt:
        g = font['glyphs'].get(ch, font['glyphs'].get(ch.upper(), font['glyphs'][' ']))
        if ch == ' ':
            cols.append(np.zeros((h, 3), bool))
            prev = ch
            continue
        used = np.where(g.any(0))[0]
        g = g[:, used.min():used.max() + 1] if len(used) else g
        if cols and prev != ' ':
            cols.append(np.zeros((h, 1), bool))
        cols.append(g)
        prev = ch
    m = np.concatenate(cols, 1) if cols else np.zeros((h, 1), bool)
    return np.kron(m, np.ones((scale, scale), bool))


def prop_size(txt, font, scale=1):
    m = prop_mask(txt, font, scale)
    return m.shape[1], m.shape[0]


def prop_text(img, cx, cy, txt, font, col, scale=1):
    m = prop_mask(txt, font, scale)
    h, w = m.shape
    X, Y = int(math.floor(cx - w / 2.0 + 0.5)), int(math.floor(cy - h / 2.0 + 0.5))
    F.blit_mask(img, m, X, Y, col)
    return w, h

N = 512
PPM = 160.0                                              # px per metre on the faces
INK, WHITE = (26, 24, 22), (236, 232, 220)
RED, RED_D = (196, 36, 26), (130, 24, 18)
SCHEMES = {S.BLUE: dict(field=(34, 60, 108), rim=(232, 234, 236), fg=(236, 238, 240), sub=(196, 206, 226)),
           S.GREEN: dict(field=(28, 102, 58), rim=(232, 236, 230), fg=(238, 240, 234), sub=(200, 222, 204)),
           S.BROWN: dict(field=(120, 70, 42), rim=(236, 230, 220), fg=(240, 236, 228), sub=(226, 208, 188)),
           S.WHITE_F: dict(field=(234, 232, 224), rim=(40, 38, 36), fg=(30, 28, 26), sub=(70, 68, 64))}


def _px(m):
    return int(round(m * PPM))


SIZES = []
for _n, _s in S.SIGNS.items():
    w, z0, z1 = _s['face']
    SIZES.append((_n, _px(w + 2 * S.BORDER), _px(z1 - z0 + 2 * S.BORDER)))
SIZES += [('gate', _px(S.GATE['plate'][0]), _px(S.GATE['plate'][1])), ('z262', _px(0.42), _px(0.42))]
REG = None


def _pack():
    global REG
    import main_tex as MT
    REG = MT.pack(SIZES, n=N)


_pack()


def uv(name, n=N):
    return VT.uv(REG[name], n)


def _fit(txt, w, h, fonts):
    """the largest (font, scale) of `fonts` whose text fits w x h pixels"""
    for font, sc in fonts:
        tw, th = prop_size(txt, font, sc)
        if tw <= w and th <= h:
            return font, sc, tw, th
    font, sc = fonts[-1]
    tw, th = prop_size(txt, font, sc)
    return font, sc, tw, th


def _wear(img, r, seed, fade=0.10, grime=(96, 92, 80)):
    """sun-faded top, grime and algae along the bottom edge, a few scratches and spots (sparse, readable)"""
    x0, y0, x1, y1 = r
    sub = img[y0:y1, x0:x1].astype(np.float64)
    h, w = sub.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    q3 = np.stack([xx.ravel() / 23.0, yy.ravel() / 23.0, np.full(xx.size, seed * 0.37)], -1).astype(np.float32)
    n1 = fbm(q3, 1.0, 3, seed=seed % 11).reshape(h, w)
    top = np.clip(1 - yy / max(h - 1, 1), 0, 1)
    sub = sub + (255 - sub) * (fade * top * (0.6 + 0.8 * n1))[..., None]                     # faded where the sun hits
    bot = np.clip((yy - h * 0.70) / (h * 0.30), 0, 1) * (n1 > 0.48)
    sub = sub * (1 - 0.28 * bot[..., None]) + np.array(grime) * 0.28 * bot[..., None]
    q3b = np.stack([xx.ravel() / 4.0, yy.ravel() / 4.0, np.full(xx.size, seed * 0.91)], -1).astype(np.float32)
    spots = (fbm(q3b, 1.0, 2, seed=(seed + 3) % 11).reshape(h, w) > 0.80)
    sub = np.where(spots[..., None], sub * 0.80 + np.array((110, 112, 96)) * 0.20, sub)
    rng = np.random.default_rng(seed)
    for _ in range(max(1, w // 140)):                                                    # a scratch or two
        sx, sy = rng.integers(4, max(5, w - 20)), rng.integers(h // 2, max(h // 2 + 1, h - 4))
        ln = rng.integers(5, 12)
        for k in range(ln):
            xx_, yy_ = sx + k, sy + k // 5
            if 0 <= xx_ < w and 0 <= yy_ < h:
                sub[yy_, xx_] = sub[yy_, xx_] * 0.75 + np.array((200, 200, 194)) * 0.25
    img[y0:y1, x0:x1] = np.clip(sub, 0, 255).astype(np.uint8)


def draw_sign(img, name):
    s = S.SIGNS[name]
    c = SCHEMES[s['scheme']]
    x0, y0, x1, y1 = REG[name]
    w, h = x1 - x0, y1 - y0
    F.rect(img, x0, y0, x1 - 1, y1 - 1, c['field'])
    b = max(2, _px(S.BORDER))                                       # the inset rim (the retroreflective border)
    F.frame(img, x0 + b, y0 + b, x1 - 1 - b, y1 - 1 - b, c['rim'], 2)
    iw, ih = w - 2 * b - 10, h - 2 * b - 6
    cx = (x0 + x1) / 2
    big = [(F.F57, 4), (F.F57, 3), (F.F57, 2), (F.F57, 1)]
    if s['en']:
        fd, sd, tw, th = _fit(s['de'], iw, int(ih * 0.48), big)
        fe, se, tw2, th2 = _fit(s['en'], iw, int(ih * 0.32) + 1, [(F.F57, 2), (F.F35, 2), (F.F57, 1), (F.F35, 1)])
        gap = max(2, (h - th - th2) // 3)
        prop_text(img, cx, y0 + gap + th / 2, s['de'], fd, c['fg'], scale=sd)
        prop_text(img, cx, y0 + 2 * gap + th + th2 / 2, s['en'], fe, c['sub'], scale=se)
    else:
        fd, sd, tw, th = _fit(s['de'], iw, int(ih * 0.70), big)
        prop_text(img, cx, (y0 + y1) / 2, s['de'], fd, c['fg'], scale=sd)
    seed = sum(map(ord, name))
    _wear(img, (x0, y0, x1, y1), seed, fade=0.06 if s['scheme'] == S.WHITE_F else 0.12,
          grime=(120, 118, 100) if s['scheme'] == S.WHITE_F else (80, 84, 72))


def draw_gate(img):
    """the checkpoint's SPERRGEBIET sign (kpp_tex.sign_sperr) at the zone gate's plate size"""
    x0, y0, x1, y1 = REG['gate']
    w, h = x1 - x0, y1 - y0
    F.rect(img, x0, y0, x1 - 1, y1 - 1, WHITE)
    F.frame(img, x0 + 3, y0 + 3, x1 - 4, y1 - 4, RED, 3)
    cx = (x0 + x1) / 2
    prop_text(img, cx, y0 + 19, 'SPERRGEBIET', F.F57, RED, scale=3)
    prop_text(img, cx, y0 + 38, 'RESTRICTED AREA', F.F57, INK, scale=2)
    F.rect(img, x0 + 26, y0 + 48, x1 - 27, y0 + 48, (150, 146, 138))
    prop_text(img, cx, y0 + 58, 'ZUTRITT VERBOTEN', F.F57, INK, scale=2)
    prop_text(img, cx, y0 + 74, 'NO ENTRY', F.F57, (60, 58, 54), scale=2)
    _wear(img, (x0, y0, x1, y1), 61, fade=0.05, grime=(118, 104, 84))
    KT._age(img, (x0, y0, x1, y1), 62, 70, 0.30, (120, 74, 44))


def draw_z262(img):
    """Zeichen 262 (actual mass 7,5 t): red ring, white field, black numbers; the corners are off the disc"""
    x0, y0, x1, y1 = REG['z262']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (150, 150, 146))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = (x1 - x0) / 2
    F.disc(img, cx, cy, r - 0.5, (232, 230, 224))
    F.ring(img, cx, cy, r * 0.78, r - 0.6, (200, 30, 24))
    prop_text(img, cx, cy, '7,5 t', F.F57, INK, scale=2)
    _wear(img, (x0, y0, x1, y1), 71, fade=0.05)


def barbed(path, w=64, h=54, rel=(0.06, 0.21, 0.36), height=0.42):
    """yard_tex.barbed with Update 3's spacing: three twisted strands with barbs, 0.5 m x `height` per tile"""
    rgba = np.zeros((h, w, 4), np.uint8)
    col = np.array((128, 130, 126), np.uint8)
    dark = np.array((86, 84, 80), np.uint8)
    for k, rr in enumerate(rel):
        r = int(round((height - rr) / height * (h - 1)))
        for x in range(w):
            up = (x // 2 + k) % 2 == 0
            rgba[r - (1 if up else 0), x, :3] = col
            rgba[r - (1 if up else 0), x, 3] = 255
            rgba[r - (0 if up else 1), x, :3] = dark
            rgba[r - (0 if up else 1), x, 3] = 255
        for bx in range(4 + k * 5, w, 16):
            for dx, dy in ((-2, -2), (-1, -1), (1, 1), (2, 2), (-2, 2), (-1, 1), (1, -1), (2, -2)):
                xx, yy = (bx + dx) % w, r + dy
                if 0 <= yy < h:
                    rgba[yy, xx, :3] = col if dy < 0 else dark
                    rgba[yy, xx, 3] = 255
    rust = (np.arange(w)[None, :] * 7 + np.arange(h)[:, None] * 13) % 11 == 0
    rgba[..., :3] = np.where((rust & (rgba[..., 3] > 0))[..., None], np.array((120, 70, 40), np.uint8), rgba[..., :3])
    Image.fromarray(rgba, 'RGBA').save(path)
    return path


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (128, 128, 124)
    for name in S.SIGNS:
        draw_sign(img, name)
    draw_gate(img)
    draw_z262(img)
    p = os.path.join(out, 'T_Road_Panel_BaseColor.png')
    Image.fromarray(img, 'RGB').save(p)
    pc = YT.chainlink(os.path.join(out, 'T_Road_ChainLink.png'))
    pw = barbed(os.path.join(out, 'T_Road_Barbed.png'))
    json.dump(dict(size=N, ppm=PPM, regions={k: list(v) for k, v in REG.items()},
                   chainlink=dict(size=64, metres_per_tile=0.5),
                   barbed=dict(size=[64, 54], metres_per_tile=[0.5, 0.42], strands_above_foot=[0.06, 0.21, 0.36])),
              open(os.path.join(out, 'road_panel_regions.json'), 'w'), indent=1)
    return p, pc, pw


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'road')
    print(build(o))
