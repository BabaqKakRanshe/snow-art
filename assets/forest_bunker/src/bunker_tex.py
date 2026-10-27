"""Panel atlas and own textures of forest_bunker (pixel art in the project's font, point filter). Wall signs German first,
English under; the door console's labels English (equipment).
Panel (256 x 256):
  notaus    NOTAUSGANG / EMERGENCY EXIT over the hangar's side door (green, the running man, an arrow)
  rauchen   RAUCHEN VERBOTEN / NO SMOKING by the hangar gate (the crossed cigarette in a red ring)
  zutritt   ZUTRITT VERBOTEN / NO ENTRY in the entrance portal
  drucktuer DRUCKTÜR 3 / BLAST DOOR 3 over the round door (yellow enamel)
  genehm    ZUTRITT NUR MIT GENEHMIGUNG / AUTHORISED PERSONNEL ONLY beside it
  console   the round door's control panel (DOOR 3 CONTROL: pressure, hydraulics, the LOCKED / OPEN lamps, the key switch,
            the guarded OPEN button; equipment - English)
Own textures: the wet boot prints (T_Bunker_Prints, RGBA cut-out: the X11 prints' sole pattern - the same boots, see
FOREST_OPENING X11 - in water-dark instead of mud), the ice tile (the forest_world tile: 64 x 64, UV 1 = 1 m).
Everything is invented.
python3 bunker_tex.py [out_dir] -> T_Bunker_*.png, bunker_panel_regions.json"""
import os, sys, json, math
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxfont as F
import van2_tex as VT
import gear_tex as GT
import world_tex as WT
from noise import fbm

HERE = os.path.dirname(os.path.abspath(__file__))
N = 256
ptext, fill, grain = GT.ptext, GT.fill, GT.grain
INK, WHITE = (26, 24, 22), (236, 232, 220)
RED, RED_D, YELLOW, GREEN = (196, 36, 26), (130, 24, 18), (232, 184, 28), (24, 128, 70)
SIZES = [('notaus', 112, 48),            # 0.70 x 0.30 m (160 px/m)
         ('rauchen', 64, 88),            # 0.40 x 0.55 m
         ('zutritt', 96, 64),            # 0.60 x 0.40 m
         ('drucktuer', 192, 44),         # 1.20 x 0.275 m
         ('genehm', 96, 64),             # 0.60 x 0.40 m
         ('console', 128, 92)]           # 0.80 x 0.575 m: the console's sloping face
REG = GT.pack(SIZES, n=N)
# the X11 prints cell of the Forest decals (T_BVDecal_Cut_px, uv 0.754 0.004 0.996 0.496): a stride, left and right
X11_DECAL = '/mnt/user-data/uploads/snow/Snow/Assets/Locations/Forest/Textures/T_BVDecal_Cut_px.png'
X11_CELL = (193, 64, 254, 127)
PRINTS_N = 64


def uv(name, n=N):
    return VT.uv(REG[name], n)


def _plate(img, r, col, rim=None, t=1):
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, col)
    if rim is not None:
        F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, rim, t)


def _age(img, r, seed, spots=40, amount=0.3, col=(110, 80, 50)):
    """rust spots and frost-dulled enamel"""
    x0, y0, x1, y1 = r
    rng = np.random.default_rng(seed)
    for _ in range(spots):
        fx, fy = rng.integers(x0 + 1, x1 - 1), rng.integers(y0 + 1, y1 - 1)
        img[fy, fx] = (img[fy, fx] * (1 - amount) + np.array(col) * amount).astype(np.uint8)
    sub = img[y0:y1, x0:x1].astype(np.float32)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    p = np.stack([xx / 40.0, yy / 40.0, np.full_like(xx, seed * 0.1)], -1).reshape(-1, 3)
    dull = np.clip((fbm(p, 3.0, 2, seed=seed).reshape(xx.shape) - 0.50) * 1.2, 0, 0.22)
    sub = sub * (1 - dull[..., None]) + np.array((200, 204, 206), np.float32) * dull[..., None]
    img[y0:y1, x0:x1] = np.clip(sub, 0, 255).astype(np.uint8)


def _screws(img, r, col=(150, 146, 138), inset=5):
    x0, y0, x1, y1 = r
    for sx in (x0 + inset, x1 - inset - 1):
        for sy in (y0 + inset, y1 - inset - 1):
            F.disc(img, sx + 0.5, sy + 0.5, 1.4, col)


def draw_signs(img):
    # NOTAUSGANG / EMERGENCY EXIT: green, white border, the running man left, arrow to the door
    r = REG['notaus']
    x0, y0, x1, y1 = r
    _plate(img, r, GREEN, (226, 246, 232))
    W_ = (232, 250, 238)
    F.rect(img, x0 + 5, y0 + 5, x0 + 33, y1 - 6, W_)
    m = GREEN
    F.disc(img, x0 + 22, y0 + 11, 3, m)
    F.line(img, x0 + 21, y0 + 15, x0 + 17, y0 + 27, m, 3)
    F.line(img, x0 + 17, y0 + 27, x0 + 25, y0 + 38, m, 3)
    F.line(img, x0 + 17, y0 + 27, x0 + 10, y0 + 38, m, 3)
    F.line(img, x0 + 20, y0 + 18, x0 + 28, y0 + 23, m, 2)
    F.line(img, x0 + 19, y0 + 18, x0 + 11, y0 + 22, m, 2)
    cx = x0 + 36 + (x1 - x0 - 40) / 2
    ptext(img, cx, y0 + 14, 'NOTAUSGANG', F.F57, W_)
    ptext(img, cx, y0 + 26, 'EMERGENCY EXIT', F.F35, W_)
    F.rect(img, cx - 24, y0 + 37, cx + 14, y0 + 39, W_)                       # the arrow
    for k in range(7):
        F.rect(img, cx + 14 + k, y0 + 32 + k, cx + 15 + k, y0 + 44 - k, W_)
    _age(img, r, 61, 30, 0.25)
    # RAUCHEN VERBOTEN / NO SMOKING: white, the red ring with the bar over a cigarette
    r = REG['rauchen']
    x0, y0, x1, y1 = r
    _plate(img, r, WHITE, INK)
    cx, cy = (x0 + x1) / 2, y0 + 30
    F.ring(img, cx, cy, 18, 23, RED)
    F.rect(img, cx - 13, cy - 2, cx + 9, cy + 2, (60, 56, 50))                 # the cigarette, its filter, the smoke
    F.rect(img, cx + 10, cy - 2, cx + 14, cy + 2, (200, 140, 60))
    for k in range(4):
        F.rect(img, cx - 16 - (k % 2), cy - 6 - 3 * k, cx - 15 - (k % 2), cy - 5 - 3 * k, (120, 120, 120))
    F.line(img, cx - 15, cy - 15, cx + 15, cy + 15, RED, 4)
    ptext(img, cx, y0 + 62, 'RAUCHEN', F.F57, INK)
    ptext(img, cx, y0 + 71, 'VERBOTEN', F.F57, INK)
    ptext(img, cx, y0 + 81, 'NO SMOKING', F.F35, (90, 86, 80))
    _screws(img, r)
    _age(img, r, 62, 40, 0.3)
    # ZUTRITT VERBOTEN / NO ENTRY: white, red border, red title
    r = REG['zutritt']
    x0, y0, x1, y1 = r
    _plate(img, r, WHITE, RED, 2)
    cx = (x0 + x1) / 2
    ptext(img, cx, y0 + 15, 'ZUTRITT', F.F57, RED, scale=2)
    ptext(img, cx, y0 + 31, 'VERBOTEN', F.F57, RED)
    F.rect(img, x0 + 12, y0 + 39, x1 - 13, y0 + 39, (150, 146, 138))
    ptext(img, cx, y0 + 48, 'NO ENTRY', F.F57, INK)
    _screws(img, r)
    _age(img, r, 63, 60, 0.35)
    # DRUCKTÜR 3 / BLAST DOOR 3: yellow enamel, black letters, hazard ends
    r = REG['drucktuer']
    x0, y0, x1, y1 = r
    _plate(img, r, YELLOW, INK)
    for x in range(x0 + 2, x0 + 16):
        for y in range(y0 + 2, y1 - 2):
            if ((x - x0) + (y - y0)) // 5 % 2 == 0:
                img[y, x] = INK
                img[y, x1 - 1 - (x - x0)] = INK
    cx = (x0 + x1) / 2
    ptext(img, cx, y0 + 14, 'DRUCKTÜR 3', F.F57, INK, scale=2)
    ptext(img, cx, y0 + 33, 'BLAST DOOR 3', F.F57, INK)
    _age(img, r, 64, 50, 0.3)
    # ZUTRITT NUR MIT GENEHMIGUNG / AUTHORISED PERSONNEL ONLY
    r = REG['genehm']
    x0, y0, x1, y1 = r
    _plate(img, r, WHITE, INK)
    F.rect(img, x0 + 2, y0 + 2, x1 - 3, y0 + 13, RED)
    cx = (x0 + x1) / 2
    ptext(img, cx, y0 + 8, 'ACHTUNG', F.F57, WHITE)
    ptext(img, cx, y0 + 21, 'ZUTRITT NUR', F.F57, INK)
    ptext(img, cx, y0 + 30, 'MIT GENEHMIGUNG', F.F57, INK)
    F.rect(img, x0 + 10, y0 + 37, x1 - 11, y0 + 37, (150, 146, 138))
    ptext(img, cx, y0 + 45, 'AUTHORISED', F.F35, (90, 86, 80))
    ptext(img, cx, y0 + 53, 'PERSONNEL ONLY', F.F35, (90, 86, 80))
    _screws(img, r, inset=4)
    _age(img, r, 65, 50, 0.3)


def draw_console(img):
    """the round door's control panel, sloping face 0.80 x 0.60 m: grey-green steel, two gauges, the lamps (off), the
    key switch, the guarded OPEN button, a hand-written card taped on"""
    r = REG['console']
    x0, y0, x1, y1 = r
    BODY, DARK, LBL = (96, 108, 100), (40, 44, 42), (226, 228, 214)
    fill(img, r, BODY)
    grain(img, r, 71, amount=6.0)
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (70, 78, 72))
    F.rect(img, x0 + 4, y0 + 4, x1 - 5, y0 + 14, DARK)                         # the title strip
    ptext(img, (x0 + x1) / 2, y0 + 9, 'DOOR 3 CONTROL', F.F35, LBL)
    for i, (gx, lab) in enumerate(((x0 + 20, 'PRESSURE'), (x0 + 54, 'HYDR.'))):
        gy = y0 + 34
        F.disc(img, gx, gy, 13, (30, 30, 30))
        F.disc(img, gx, gy, 11, (218, 214, 196))
        for a in range(0, 271, 30):
            F.tick(img, gx, gy, 8, 10, math.radians(225 - a), (30, 30, 30))
        F.tick(img, gx, gy, 0, 9, math.radians(225 - (8 if i == 0 else 4)), (170, 30, 20), 1)    # needles on zero
        ptext(img, gx, gy + 18, lab, F.F35, LBL)
    for j, (lab, col) in enumerate((('LOCKED', (110, 30, 26)), ('OPEN', (30, 80, 40)), ('POWER', (120, 96, 30)))):
        lx, ly = x0 + 82, y0 + 24 + j * 12
        F.disc(img, lx, ly, 4, (24, 24, 24))
        F.disc(img, lx, ly, 3, col)                                           # unlit lenses
        ptext(img, lx + 7, ly, lab, F.F35, LBL, align='l')
    kx, ky = x0 + 22, y0 + 73                                                 # the key switch
    F.disc(img, kx, ky, 7, (170, 168, 160))
    F.disc(img, kx, ky, 5, (120, 118, 112))
    F.rect(img, kx - 1, ky - 4, kx, ky + 4, (40, 40, 40))
    ptext(img, kx + 11, ky - 4, 'KEY', F.F35, LBL, align='l')
    bx, by = x0 + 70, y0 + 73                                                 # the guarded OPEN button
    F.rect(img, bx - 13, by - 10, bx + 13, by + 10, (200, 170, 30))
    for k in range(-13, 14, 4):
        F.rect(img, bx + k, by - 10, bx + k + 1, by - 9, INK)
        F.rect(img, bx + k, by + 9, bx + k + 1, by + 10, INK)
    F.disc(img, bx, by, 7, (150, 30, 24))
    F.disc(img, bx - 1, by - 1, 5, (196, 50, 36))
    ptext(img, bx, by + 14, 'OPEN', F.F35, LBL)
    cx_, cy_ = x0 + 108, y0 + 73                                             # a card taped on: hand-written
    F.rect(img, cx_ - 12, cy_ - 9, cx_ + 12, cy_ + 9, (222, 214, 188))
    F.rect(img, cx_ - 4, cy_ - 11, cx_ + 4, cy_ - 8, (200, 196, 170))
    for k, w in enumerate((18, 14, 16)):
        F.rect(img, cx_ - 9, cy_ - 4 + k * 4, cx_ - 9 + w, cy_ - 4 + k * 4, (60, 60, 120))
    _age(img, r, 72, 80, 0.3)


def prints_tex():
    """the X11 prints cell (left and right sole in a stride, 0.9 m) recoloured wet: water-dark grey with a glint;
    RGBA, alpha 0 / 255 (cut-out); 64 x 64 (the cell padded)"""
    out = np.zeros((PRINTS_N, PRINTS_N, 4), np.uint8)
    out[..., :3] = (34, 38, 42)
    try:
        a = np.array(Image.open(X11_DECAL).convert('RGBA'))
        x0, y0, x1, y1 = X11_CELL
        c = a[y0:y1, x0:x1]
        m = c[..., 3] > 127
        lum = c[..., :3].mean(-1)
    except FileNotFoundError:                                  # (the package keeps the result; only a rebuild needs the decal)
        m = np.zeros((63, 61), bool)
        lum = np.zeros((63, 61))
    h, w = m.shape
    oy, ox = (PRINTS_N - h) // 2, (PRINTS_N - w) // 2
    rgb = np.where((lum < 30)[..., None], np.array((22, 26, 30)), np.array((40, 46, 52)))      # the mud's dark core -> deeper water
    sub = out[oy:oy + h, ox:ox + w]
    sub[..., :3] = np.where(m[..., None], rgb, sub[..., :3])
    sub[..., 3] = np.where(m, 255, 0)
    glint = m & (np.roll(m, 1, 0) == False)                    # a lighter texel on each print's top edge: the wet sheen
    sub[..., :3][glint] = (86, 96, 104)
    return out


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (24, 24, 24)
    draw_signs(img)
    draw_console(img)
    paths = {}
    for name, a, mode in (('Panel_BaseColor', img, 'RGB'), ('Prints_BaseColor', prints_tex(), 'RGBA'),
                          ('Ice_BaseColor', WT.ice_tile(), 'RGB')):
        paths[name] = os.path.join(out, f'T_Bunker_{name}.png')
        Image.fromarray(a, mode).save(paths[name])
    json.dump(dict(size=N, regions=REG, prints=dict(px=PRINTS_N, metres=0.9, source='T_BVDecal_Cut_px (X11 prints cell)',
                                                    layout='one stride (left and right sole) per quad, toes to +v'),
                   ice=dict(tile_px=WT.ICE_N, px_per_m=64)),
              open(os.path.join(out, 'bunker_panel_regions.json'), 'w'), indent=1, ensure_ascii=False)
    return paths


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'bunker')))
