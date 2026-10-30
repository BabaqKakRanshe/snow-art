"""Panel atlas of the forest network props (256 x 256, pixel art, point-filtered) on the explicit-UV objects:
  n05 .. n12   the compartment stones' whole -y faces (0.24 x 1.05 m, ~150 px/m) with the fork's number (5-12 of
               docs/gdd/locations/roads/network_proposal.png) cut in at 0.46 m: grey granite speckle, the groove dark, a light
               lower-right lip, damp and dirt towards the foot. The whole face, so no plate edge shows on the stone
python3 net_tex.py [out_dir] -> T_NET_Panel_BaseColor.png, T_NET_Panel_Emission.png, net_panel_regions.json"""
import os, sys, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxfont as F
import van2_tex as VT

HERE = os.path.dirname(os.path.abspath(__file__))
N = 256
NUMBERS = list(range(5, 13))
TILE_W, TILE_H = 32, 168
FACE_M = (0.24, 1.05)                  # the face the tile covers: width, height (0.30 m of it in the ground)
NUMBER_DOWN = 0.29                     # m from the face's top to the number's middle (the number at 0.46 m over the ground)
REG = {}
for i, n in enumerate(NUMBERS):
    REG[f'n{n:02d}'] = (i * TILE_W, 0, (i + 1) * TILE_W, TILE_H)
GRANITE = (128, 126, 120)
# the pointers' arrow boards (as the airfield's AF_Sign / the hut yard's RouteSign: 0.92 x 0.19 m), German over English
SIGNS = {'sign_lager': ('LAGER', 'CAMP'), 'sign_kapelle': ('KAPELLE', 'CHAPEL')}
REG['sign_lager'] = (0, 176, 192, 216)
REG['sign_kapelle'] = (0, 216, 192, 256)
BOARD, BOARD_D, CREAM = (70, 48, 30), (46, 32, 22), (226, 210, 160)
# the forest track barrier's board (1.10 x 0.24 m): WALDWEG only, small (the free corner of the atlas, 64 x 16 px)
REG['sign_waldweg'] = (192, 176, 256, 192)
REG['sign_druck'] = (192, 192, 256, 208)                 # the bunker portal's door plate


def uv(name, n=N):
    return VT.uv(REG[name], n, inset=1.5)        # the quad's edge must never fetch the black between the tiles


def draw_number(img, name, number, seed):
    """granite with feldspar speckle; the number cut 2 px deep: the groove dark, its lower-right lip catching the light"""
    x0, y0, x1, y1 = REG[name]
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    t = VT.BAYER[np.mod(yy, 4), np.mod(xx, 4)]
    base = np.array(GRANITE, np.float32)[None, None] * (0.90 + 0.10 * np.floor((rng.random(yy.shape) * 0.6 + t * 0.4) * 4) / 4)[..., None]
    spk = rng.random(yy.shape)
    base = np.where((spk > 0.93)[..., None], np.array((176, 170, 160), np.float32)[None, None], base)
    base = np.where((spk < 0.06)[..., None], np.array((70, 68, 64), np.float32)[None, None], base)
    img[y0:y1, x0:x1] = np.clip(base, 0, 255).astype(np.uint8)
    txt = str(number).replace('0', 'O')                       # the font's zero is slashed; a stone mason cuts a round one
    mask = np.asarray(F.text_mask(txt, F.F57, 3 if len(txt) == 1 else 2), bool)     # 15 x 21 px for one digit, 22 x 14 for two
    h, w = mask.shape
    ox, oy = x0 + (TILE_W - w) // 2, y0 + int(NUMBER_DOWN / FACE_M[1] * TILE_H) - h // 2
    # damp and dirt rising from the foot (the lowest 0.30 m is in the ground)
    foot = int((1.0 - 0.42 / FACE_M[1]) * TILE_H)
    for yy_ in range(foot, y1):
        k = min(1.0, (yy_ - foot) / max(1, (y1 - foot) * 0.6))
        img[yy_, x0:x1] = (img[yy_, x0:x1] * (1.0 - 0.45 * k) + np.array((92, 78, 60)) * 0.45 * k).astype(np.uint8)
    lip = np.zeros_like(mask)
    lip[1:, 1:] = mask[:-1, :-1]
    lip &= ~mask
    for yy_ in range(h):
        for xx_ in range(w):
            if mask[yy_, xx_]:
                img[oy + yy_, ox + xx_] = (44, 42, 40)
            elif lip[yy_, xx_]:
                img[oy + yy_, ox + xx_] = (170, 166, 156)
    for _ in range(90):                                          # weathering: lichen dots and chips over the face
        cx, cy = rng.integers(x0 + 1, x1 - 1), rng.integers(y0 + 1, y1 - 1)
        img[cy, cx] = (img[cy, cx] * 0.6 + np.array((112, 120, 84)) * 0.4).astype(np.uint8)


def draw_sign(img, name):
    x0, y0, x1, y1 = REG[name]
    de, en = SIGNS[name]
    yy, xx = np.mgrid[y0:y1, x0:x1]
    grain = 0.88 + 0.12 * np.sin(yy * 1.7 + np.sin(xx * 0.09) * 2.0) + 0.05 * ((xx * 7 + yy * 13) % 5 == 0)
    img[y0:y1, x0:x1] = np.clip(np.array(BOARD)[None, None] * grain[..., None], 0, 255).astype(np.uint8)
    F.frame(img, x0, y0, x1 - 1, y1 - 1, BOARD_D, 2)
    F.text(img, x0 + 92, y0 + 13, de, F.F57, CREAM, scale=2)
    F.text(img, x0 + 92, y0 + 31, en, F.F35, (190, 176, 132))
    rng = np.random.default_rng(sum(map(ord, name)))
    for _ in range(140):
        xx_, yy_ = rng.integers(x0 + 1, x1 - 1), rng.integers(y0 + 1, y1 - 1)
        img[yy_, xx_] = (img[yy_, xx_] * 0.65 + np.array((120, 116, 104)) * 0.35).astype(np.uint8)


def draw_waldweg(img):
    x0, y0, x1, y1 = REG['sign_waldweg']
    yy, xx = np.mgrid[y0:y1, x0:x1]
    grain = 0.9 + 0.1 * np.sin(yy * 2.1 + np.sin(xx * 0.2) * 1.5)
    img[y0:y1, x0:x1] = np.clip(np.array((214, 206, 186))[None, None] * grain[..., None], 0, 255).astype(np.uint8)   # whitewashed
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (40, 34, 28), 1)
    F.text(img, x0 + 32, y0 + 5, 'WALDWEG', F.F57, (34, 30, 26))       # x is the text's middle
    rng = np.random.default_rng(7)
    for _ in range(40):
        xx_, yy_ = rng.integers(x0 + 1, x1 - 1), rng.integers(y0 + 1, y1 - 1)
        img[yy_, xx_] = (img[yy_, xx_] * 0.7 + np.array((120, 110, 90)) * 0.3).astype(np.uint8)


def draw_druck(img):
    x0, y0, x1, y1 = REG['sign_druck']
    img[y0:y1, x0:x1] = (196, 168, 40)                                   # yellow plate
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (30, 28, 24), 1)
    F.text(img, x0 + 32, y0 + 8, 'DRUCKTUER', F.F35, (24, 22, 20))


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (16, 16, 16)
    emi = np.zeros_like(img)
    for i, n in enumerate(NUMBERS):
        draw_number(img, f'n{n:02d}', n, 500 + n)
    for name in SIGNS:
        draw_sign(img, name)
    draw_waldweg(img)
    draw_druck(img)
    pb, pe = os.path.join(out, 'T_NET_Panel_BaseColor.png'), os.path.join(out, 'T_NET_Panel_Emission.png')
    Image.fromarray(img).save(pb)
    Image.fromarray(emi).save(pe)
    json.dump(dict(size=N, regions=REG, face_m=list(FACE_M)), open(os.path.join(out, 'net_panel_regions.json'), 'w'), indent=1)
    return pb, pe


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'net')))
