"""Panel atlas of the forester's hut (512 x 512, pixel art, point-filtered), on the explicit-UV objects:
  map       the forester's district map on the back wall: REVIERKARTE, the real road from the Sperrgebiet gate past the
            hut, over the bridge and the overlook to the checkpoint and the station (Forest_Layout positions), forest,
            clearings, contours (5 m, from the site heights), the river, symbols; the OBSERVATORIUM circled in red
            pencil, a red pencil cross in the woods north of the chapel; north arrow, scale bar
  calendar  October (2026 layout: the 1st is a Thursday), German weekdays, days 1-16 crossed out (the note: 16.10.)
  sign      FORSTHÜTTE / FORESTER'S HUT, white letters on a dark board (the sign at the path)
  l_lantern storm-lantern globe: sooty glass (base), flame-lit glass (emission); horizontally uniform (cylinder UVs)
  l_oillamp the oil lamp's chimney, the same way
  glow      soft halo for the lantern's glow cards (emission only)
German on the map and the calendar (the forester's own), the sign bilingual.  Umlaut glyphs added to both fonts.
python3 hut_tex.py [out_dir]  ->  T_Hut_Panel_BaseColor.png / _Emission.png, hut_panel_regions.json"""
import os, sys, json, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pxfont as F
import van2_tex as VT
from noise import fbm

# umlauts: the dots replace the top row of the glyph (as cont_tex)
for _f, _src in ((F.F35, {'Ä': '#.#|.#.|#.#|###|#.#', 'Ö': '#.#|...|###|#.#|###', 'Ü': '#.#|...|#.#|#.#|###'}),
                 (F.F57, {'Ä': '.#.#.|.....|.###.|#...#|#####|#...#|#...#', 'Ö': '.#.#.|.....|.###.|#...#|#...#|#...#|.###.',
                          'Ü': '.#.#.|.....|#...#|#...#|#...#|#...#|.###.'})):
    for _k, _s in _src.items():
        _f['glyphs'][_k] = F._compile({'x': _s})['x']

N = 512
REG = {'map': (0, 0, 288, 186), 'calendar': (288, 0, 360, 100), 'sign': (0, 192, 256, 264),
       'l_lantern': (368, 0, 400, 32), 'l_oillamp': (400, 0, 432, 32), 'glow': (432, 0, 496, 64)}
INK, PAPER, RED = (34, 30, 26), (224, 216, 190), (186, 40, 30)


def uv(name, n=N):
    return VT.uv(REG[name], n)


# ---------------------------------------------------------------- the district map
SITES = {   # Unity x, z, height (Forest_Layout.json prefabs / anchors)
    'gate': (-511.5, 554.2, 29.3), 'start': (-463.2, 495.6, 22.9), 'hut': (-474.0, 404.0, 28.4), 'stand': (-482.0, 412.0, 28.9),
    'd11': (-422.2, 435.6, 24.6), 'bridge': (-331.3, 331.6, 19.5), 'd09': (-293.3, 282.7, 15.6), 'fallen': (-249.6, 258.5, 13.8),
    'd07': (-145.1, 154.5, 10.4), 'overlook': (-185.3, 148.0, 10.3), 'd23': (18.4, 65.8, 6.8), 'd03': (149.1, -76.3, 9.3),
    'ribs': (180.0, -141.0, 8.9), 'kpp': (313.0, -289.6, 16.4), 'base': (340.0, -360.0, 16.7), 'gen': (394.0, -335.3, 16.3),
    'garage': (379.7, -400.9, 16.4), 'mast': (293.4, -403.9, 16.3), 'dish1': (-470.0, 380.0, 28.1), 'dish2': (-380.0, -200.0, 33.9),
    'dish3': (480.0, 330.0, 19.9), 'dish4': (-150.0, 430.0, 21.5), 'dish5': (60.0, -380.0, 23.5), 'radome': (110.0, -430.0, 30.3),
    'relay': (-320.0, -330.0, 48.5), 'lookout': (-260.0, -80.0, 35.4), 'meteo': (215.0, -300.0, 13.3), 'camp': (-120.0, -300.0, 11.0),
    'chapel': (470.0, -120.0, 4.6), 'cabin': (-420.0, 60.0, 14.0), 'pump': (520.0, -230.0, 1.4), 'woods': (505.0, 160.0, 7.0),
    'hand': (13.0, -39.0, 6.0)}
ROAD = ['gate', 'start', 'd11', 'bridge', 'd09', 'fallen', 'd07', 'd23', 'd03', 'ribs', 'kpp', 'base']


def _frame():
    """map frame: the hut -> station road runs left to right (the map is turned; the north arrow says so)"""
    h, b = np.array(SITES['hut'][:2]), np.array(SITES['base'][:2])
    e1 = (b - h) / np.linalg.norm(b - h)
    e2 = np.array([-e1[1], e1[0]])
    return h, e1, e2


def _to_px(r, xz):
    h, e1, e2 = _frame()
    x0, y0, x1, y1 = r
    mx0, mx1, my0, my1 = -190.0, 1310.0, -380.0, 590.0                  # metres along / across the road
    s = (x1 - x0) / (mx1 - mx0)
    d = np.asarray(xz, np.float64) - h
    mx, my = d @ e1, d @ e2
    return x0 + (mx - mx0) * s, y0 + (my1 - my) * s, s


def _from_px(r, px, py):
    h, e1, e2 = _frame()
    x0, y0, x1, y1 = r
    mx0, mx1, my0, my1 = -190.0, 1310.0, -380.0, 590.0
    s = (x1 - x0) / (mx1 - mx0)
    mx = (px - x0) / s + mx0
    my = my1 - (py - y0) / s
    return h[0] + mx * e1[0] + my * e2[0], h[1] + mx * e1[1] + my * e2[1]


def _poly(img, pts, col, w=1):
    for a, b in zip(pts[:-1], pts[1:]):
        F.line(img, a[0], a[1], b[0], b[1], col, w)


def _chaikin(pts, n=3):
    pts = [np.asarray(p, np.float64) for p in pts]
    for _ in range(n):
        q = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            q += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        q.append(pts[-1])
        pts = q
    return pts


def draw_map(img_full):
    X0, Y0, X1, Y1 = REG['map']
    W, H = X1 - X0, Y1 - Y0
    r = (0, 0, W, H)                                                    # drawn on its own canvas (clipped), pasted at the end
    x0, y0, x1, y1 = r
    img = np.zeros((H, W, 3), np.uint8)
    P = lambda key: _to_px(r, SITES[key][:2])[:2]
    # height field from the site heights (gaussian RBF + a plane) and a little noise -> contours
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64) + 0.5
    wx, wz = _from_px(r, xx, yy)
    pts = np.array([v for v in SITES.values()], np.float64)
    A = np.c_[np.ones(len(pts)), pts[:, 0], pts[:, 1]]
    coef = np.linalg.lstsq(A, pts[:, 2], rcond=None)[0]
    res = pts[:, 2] - A @ coef
    sig = 230.0
    K_ = np.exp(-((pts[:, None, 0] - pts[None, :, 0]) ** 2 + (pts[:, None, 1] - pts[None, :, 1]) ** 2) / (2 * sig ** 2))
    wgt = np.linalg.solve(K_ + 0.25 * np.eye(len(pts)), res)
    Hf = coef[0] + coef[1] * wx + coef[2] * wz
    for (px_, pz_, _), w_ in zip(pts, wgt):
        Hf += w_ * np.exp(-((wx - px_) ** 2 + (wz - pz_) ** 2) / (2 * sig ** 2))
    q3 = np.stack([wx.ravel() / 100.0, wz.ravel() / 100.0, np.zeros(wx.size)], -1).astype(np.float32)
    Hf += (fbm(q3, 0.9, 3, seed=7).reshape(Hf.shape) - 0.5) * 6.0
    # forest everywhere, stippled; clearings round the sites and along the road
    paper = np.array(PAPER, np.float64)
    forest = np.array((150, 178, 120), np.float64)
    t = VT.BAYER[np.mod(yy.astype(int), 4), np.mod(xx.astype(int), 4)]
    dens = fbm(q3, 2.4, 2, seed=8).reshape(Hf.shape)
    clear = np.zeros_like(Hf)
    for key, rad in (('base', 95.0), ('kpp', 30.0), ('overlook', 26.0), ('camp', 30.0), ('meteo', 22.0), ('chapel', 30.0),
                     ('pump', 20.0), ('hut', 14.0), ('cabin', 16.0), ('relay', 18.0), ('radome', 24.0)):
        cx, cz = SITES[key][:2]
        clear = np.maximum(clear, (np.hypot(wx - cx, wz - cz) < rad * (0.85 + 0.3 * dens)).astype(np.float64))
    tile = np.where(clear[..., None] > 0.5, paper, forest)
    tree = (t < 0.18 + 0.25 * dens) & (clear < 0.5)
    tile = np.where(tree[..., None], np.array((112, 146, 92), np.float64), tile)
    # contours every 5 m, every 4th (20 m) darker
    band = np.floor(Hf / 5.0)
    edge = np.zeros_like(band, bool)
    edge[:-1, :] |= band[:-1, :] != band[1:, :]
    edge[:, :-1] |= band[:, :-1] != band[:, 1:]
    idx = np.maximum(band, np.roll(band, -1, 0))
    major = edge & (np.mod(idx, 4) == 0)
    tile = np.where((edge & ~major)[..., None], tile * 0.55 + np.array((150, 104, 60)) * 0.45, tile)
    tile = np.where(major[..., None], tile * 0.25 + np.array((128, 80, 40)) * 0.75, tile)
    img[y0:y1, x0:x1] = np.clip(tile, 0, 255).astype(np.uint8)
    # the river through the bridge, a pond by the pump house
    bx, by = P('bridge')
    river = _chaikin([(bx - 34, y0 - 2), (bx - 22, by - 42), (bx - 6, by - 14), (bx, by), (bx + 10, by + 20), (bx + 30, by + 46),
                      (bx + 60, by + 60), (bx + 96, y1 + 2)], 3)
    _poly(img, river, (70, 110, 168), 2)
    px_, py_ = P('pump')
    F.disc(img, px_ + 3, py_ + 2, 3.2, (70, 110, 168))
    # the road (black edges, white middle) and the path to the hut
    rp = _chaikin([P(k) for k in ROAD], 2)
    _poly(img, rp, INK, 3)
    _poly(img, rp, (236, 232, 214), 1)
    hx, hy = P('hut')
    _poly(img, [P('start'), ((hx + P('start')[0]) / 2 + 2, (hy + P('start')[1]) / 2), (hx, hy)], INK, 1)
    gx, gy = P('gate')
    # Sperrgebiet boundary: red dashed fence line across the road at the gate, hatched on the inside (the hut's side)
    h, e1, e2 = _frame()
    sx_, sy_ = P('start')
    dv = np.array([sx_ - gx, sy_ - gy])
    dv /= np.linalg.norm(dv)
    pv = np.array([-dv[1], dv[0]])
    for k in range(-40, 41):
        p = np.array([gx, gy]) + pv * k
        if k % 6 < 4:
            F.rect(img, p[0], p[1], p[0], p[1], RED)
        if k % 6 == 1:
            q = p + dv * 3 + pv * 1.5
            F.line(img, p[0], p[1], q[0], q[1], RED)
    F.text(img, gx + 5, gy - 30, 'SPERRGEBIET', F.F35, RED, align='l')
    # symbols
    def house(key, col=INK):
        x, y = P(key)
        F.rect(img, x - 2, y - 1, x + 2, y + 2, col)
        F.rect(img, x - 1, y - 2, x + 1, y - 2, col)
        F.rect(img, x, y - 3, x, y - 3, col)
    def dish(key):
        x, y = P(key)
        F.ring(img, x, y, 1.5, 3.0, INK, 200, 340)
        F.rect(img, x, y - 1, x, y + 2, INK)
    def stand(key):
        x, y = P(key)
        F.line(img, x - 2, y + 2, x, y - 2, INK)
        F.line(img, x + 2, y + 2, x, y - 2, INK)
        F.rect(img, x - 1, y, x + 1, y, INK)
    house('hut')
    stand('stand')
    house('cabin')
    for k in ('dish1', 'dish2', 'dish3', 'dish4', 'dish5'):
        dish(k)
    x, y = P('radome')
    F.disc(img, x, y, 2.2, INK)
    for k in ('relay', 'lookout'):
        x, y = P(k)
        F.line(img, x - 2, y + 3, x, y - 4, INK)
        F.line(img, x + 2, y + 3, x, y - 4, INK)
        F.rect(img, x - 1, y, x + 1, y, INK)
    x, y = P('chapel')
    F.rect(img, x, y - 3, x, y + 3, INK)
    F.rect(img, x - 2, y - 1, x + 2, y - 1, INK)
    for k, sz in (('base', (6, 3)), ('gen', (2, 1)), ('garage', (2, 2)), ('kpp', (1, 1)), ('meteo', (1, 1)), ('pump', (1, 1))):
        x, y = P(k)
        F.rect(img, x - sz[0], y - sz[1], x + sz[0], y + sz[1], INK)
    x, y = P('mast')
    F.rect(img, x, y - 4, x, y + 1, INK)
    x, y = P('bridge')
    for s_ in (-1, 1):
        F.line(img, x - 3 + s_ * 1, y - 3 + s_ * -1 + 1, x + 3 + s_ * 1, y + 3 + s_ * -1 - 1, INK)
    for k in ('overlook', 'camp'):
        x, y = P(k)
        F.ring(img, x, y, 1.5, 2.6, INK)
    # labels
    lab = lambda key, txt, dx, dy, al='l': F.text(img, P(key)[0] + dx, P(key)[1] + dy, txt, F.F35, INK, align=al)
    lab('hut', 'FORSTHÜTTE', 4, 1)
    lab('cabin', 'HÜTTE', 4, 0)
    lab('overlook', 'AUSSICHT', 0, 7, 'c')
    lab('chapel', 'KAPELLE', 0, 7, 'c')
    lab('relay', 'FUNKMAST', 0, 7, 'c')
    lab('lookout', 'TURM', 4, 0)
    lab('camp', 'LAGERPLATZ', 0, 6, 'c')
    lab('base', 'OBSERVATORIUM', 0, 11, 'c')
    lab('kpp', 'WACHE', -3, -5, 'r')
    x, y = P('bridge')
    F.text(img, x + 6, y - 5, 'BRÜCKE', F.F35, INK, align='l')
    # the forester's red pencil: a wobbly ring round the station, a cross in the woods
    bx, by = P('base')
    for a in range(0, 400, 4):
        rr = 15.5 + 1.6 * math.sin(math.radians(a * 2.3)) + (a / 400.0) * 1.5
        F.rect(img, bx + rr * math.cos(math.radians(a)) * 1.35, by + 2 + rr * math.sin(math.radians(a)),
                bx + rr * math.cos(math.radians(a)) * 1.35, by + 2 + rr * math.sin(math.radians(a)), RED)
    wx_, wy_ = P('woods')
    F.line(img, wx_ - 3, wy_ - 3, wx_ + 3, wy_ + 3, RED, 2)
    F.line(img, wx_ + 3, wy_ - 3, wx_ - 3, wy_ + 3, RED, 2)
    # title block, scale bar, north arrow, frame
    F.rect(img, x0 + 3, y0 + 3, x0 + 84, y0 + 22, (232, 226, 204))
    F.frame(img, x0 + 3, y0 + 3, x0 + 84, y0 + 22, INK)
    F.text(img, x0 + 44, y0 + 10, 'REVIERKARTE', F.F57, INK)
    F.text(img, x0 + 44, y0 + 18, 'FORSTREVIER 7', F.F35, (70, 64, 56))
    s = _to_px(r, SITES['hut'][:2])[2]
    L = 250.0 * s
    sx, sy = x1 - 10 - 2 * L, y1 - 9
    for i in range(2):
        F.rect(img, sx + i * L, sy, sx + (i + 1) * L - 1, sy + 1, INK if i == 0 else (240, 236, 222))
    F.frame(img, sx, sy - 1, sx + 2 * L - 1, sy + 2, INK)
    F.text(img, sx, sy - 5, '0', F.F35, INK)
    F.text(img, sx + 2 * L - 1, sy - 5, '500 M', F.F35, INK, align='r')
    nx_, nz_ = -e1[1], e1[0]                                            # map direction of north
    nvec = np.array([(np.array([0.0, 1.0]) @ e1), (np.array([0.0, 1.0]) @ e2)])
    ax, ay = x1 - 16, y0 + 20
    tip = (ax + nvec[0] * 11, ay - nvec[1] * 11)
    tail = (ax - nvec[0] * 9, ay + nvec[1] * 9)
    F.line(img, tail[0], tail[1], tip[0], tip[1], INK, 1)
    side = np.array([nvec[1], nvec[0]])
    for sgn in (-1, 1):
        F.line(img, tip[0], tip[1], tip[0] - nvec[0] * 5 + sgn * side[0] * 3, tip[1] + nvec[1] * 5 + sgn * side[1] * 3, INK, 1)
    F.text(img, tip[0] + nvec[0] * 5, tip[1] - nvec[1] * 5, 'N', F.F35, INK)
    F.frame(img, x0, y0, x1 - 1, y1 - 1, INK)
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, (200, 192, 166))
    # age: a fold across the middle, foxing
    fold = x0 + W // 2
    img[y0 + 2:y1 - 2, fold] = (img[y0 + 2:y1 - 2, fold] * 0.86).astype(np.uint8)
    rng = np.random.default_rng(3)
    for _ in range(26):
        fx, fy = rng.integers(x0 + 3, x1 - 3), rng.integers(y0 + 3, y1 - 3)
        img[fy, fx] = (img[fy, fx] * 0.80 + np.array((150, 110, 60)) * 0.20).astype(np.uint8)
    img_full[Y0:Y1, X0:X1] = img


# ---------------------------------------------------------------- calendar
def draw_calendar(img):
    x0, y0, x1, y1 = REG['calendar']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (232, 228, 214))
    # picture: a stag at the forest edge at dusk
    py1 = y0 + 40
    yy, xx = np.mgrid[y0 + 2:py1, x0 + 2:x1 - 2]
    tt = (yy - y0) / 40.0
    sky = (np.array((206, 150, 96))[None, None] * (1 - tt[..., None]) + np.array((96, 84, 110))[None, None] * tt[..., None])
    t = VT.BAYER[np.mod(yy, 4), np.mod(xx, 4)]
    sky = np.floor(sky / 24 + t[..., None]) * 24
    img[y0 + 2:py1, x0 + 2:x1 - 2] = np.clip(sky, 0, 255).astype(np.uint8)
    rng = np.random.default_rng(11)
    for k in range(x0 + 2, x1 - 2, 3):                                 # spruce silhouettes
        h = int(10 + rng.integers(0, 14))
        for j in range(h):
            w = max(0, (j * 0.45))
            F.rect(img, k - w / 2, py1 - h + j, k + w / 2, py1 - h + j, (30, 40, 34))
    F.rect(img, x0 + 2, py1 - 4, x1 - 3, py1 - 1, (34, 44, 36))
    sx, sy = x0 + 24, py1 - 6                                           # the stag
    F.rect(img, sx, sy - 6, sx + 9, sy - 3, (20, 18, 16))
    for lx in (sx, sx + 2, sx + 7, sx + 9):
        F.rect(img, lx, sy - 3, lx, sy, (20, 18, 16))
    F.rect(img, sx + 9, sy - 9, sx + 10, sy - 6, (20, 18, 16))
    F.rect(img, sx + 10, sy - 10, sx + 12, sy - 9, (20, 18, 16))
    for d in (-1, 1):
        F.line(img, sx + 11, sy - 10, sx + 11 + d * 3, sy - 15, (20, 18, 16))
        F.line(img, sx + 11 + d * 2, sy - 13, sx + 11 + d * 4, sy - 13, (20, 18, 16))
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, py1, (150, 140, 120))
    F.text(img, (x0 + x1) / 2, py1 + 6, 'OKTOBER', F.F57, (150, 30, 24))
    days = ['MO', 'DI', 'MI', 'DO', 'FR', 'SA', 'SO']
    cw = (x1 - x0 - 2) / 7.0
    gy0 = py1 + 13
    for i, d in enumerate(days):
        F.text(img, x0 + 1 + cw * (i + 0.5), gy0, d, F.F35, (150, 30, 24) if i == 6 else INK)
    first = 3                                                           # 1 October 2026 is a Thursday
    for day in range(1, 32):
        cell = first + day - 1
        row, colm = cell // 7, cell % 7
        cx = x0 + 1 + cw * (colm + 0.5)
        cy = gy0 + 8 + row * 8
        F.text(img, cx, cy, str(day), F.F35, (150, 30, 24) if colm == 6 else INK)
        if day <= 16:                                                   # crossed out in pencil
            F.line(img, cx - 4, cy - 3, cx + 4, cy + 3, (90, 84, 96))
            F.line(img, cx + 4, cy - 3, cx - 4, cy + 3, (90, 84, 96))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (170, 160, 140))
    F.rect(img, (x0 + x1) / 2 - 1, y0, (x0 + x1) / 2, y0 + 1, (40, 40, 40))   # the nail hole


# ---------------------------------------------------------------- the sign
def draw_sign(img):
    x0, y0, x1, y1 = REG['sign']
    yy, xx = np.mgrid[y0:y1, x0:x1]
    q3 = np.stack([xx.ravel() / 40.0, (yy.ravel() % 18) * 6.0, (yy.ravel() // 18) * 1.0], -1).astype(np.float32)
    grain = fbm(q3 * np.array([0.25, 1.0, 1.0], np.float32), 3.0, 3, seed=21).reshape(xx.shape)
    base = np.array((58, 44, 32), np.float64)[None, None] * (0.80 + 0.40 * grain[..., None])
    img[y0:y1, x0:x1] = np.clip(base, 0, 255).astype(np.uint8)
    W = (232, 228, 214)
    F.frame(img, x0 + 4, y0 + 4, x1 - 5, y1 - 5, W)
    F.text(img, (x0 + x1) / 2, y0 + 25, 'FORSTHÜTTE', F.F57, W, scale=3)
    F.rect(img, x0 + 52, y0 + 44, x1 - 53, y0 + 44, (150, 140, 120))
    F.text(img, (x0 + x1) / 2, y0 + 55, "FORESTER'S HUT", F.F57, (200, 194, 176))
    q3b = np.stack([xx.ravel() / 9.0, yy.ravel() / 9.0, np.zeros(xx.size)], -1).astype(np.float32)
    flake = (fbm(q3b, 1.0, 3, seed=22).reshape(xx.shape) > 0.66) & (img[y0:y1, x0:x1].mean(-1) > 150)
    sub = img[y0:y1, x0:x1]
    sub[flake] = (sub[flake] * 0.45 + base[flake] * 0.55).astype(np.uint8)
    for sx in (x0 + 10, x1 - 11):                                       # screw heads
        F.disc(img, sx, (y0 + y1) / 2, 2.2, (120, 116, 108))


# ---------------------------------------------------------------- lenses and the glow
def draw_lenses(img, emi):
    for key, tint, flame_v in (('l_lantern', (255, 196, 110), 0.42), ('l_oillamp', (255, 206, 130), 0.30)):
        x0, y0, x1, y1 = REG[key]
        h = y1 - y0
        v = 1.0 - (np.arange(h) + 0.5) / h                               # v (bottom 0 .. top 1) per pixel row
        glow = np.exp(-0.5 * ((v - flame_v) / 0.16) ** 2)
        core = np.exp(-0.5 * ((v - flame_v) / 0.05) ** 2)
        soot = np.clip((v - 0.70) / 0.30, 0, 1)
        e = (np.array(tint)[None] * (0.25 + 0.75 * glow)[:, None] + np.array((255, 250, 220))[None] * 0.6 * core[:, None])
        e = e * (1 - 0.65 * soot)[:, None]
        t = VT.BAYER[np.mod(np.arange(h), 4), 0][:, None]
        e = np.floor(e / 16 + t) * 16
        b = np.array((120, 104, 80))[None] * (0.55 + 0.30 * glow)[:, None] * (1 - 0.6 * soot)[:, None]
        emi[y0:y1, x0:x1] = np.clip(e, 0, 255).astype(np.uint8)[:, None, :]
        img[y0:y1, x0:x1] = np.clip(b, 0, 255).astype(np.uint8)[:, None, :]
    x0, y0, x1, y1 = REG['glow']
    yy, xx = np.mgrid[y0:y1, x0:x1]
    rr = np.hypot(xx + 0.5 - (x0 + x1) / 2, yy + 0.5 - (y0 + y1) / 2) / ((x1 - x0) / 2)
    g = np.clip(1 - rr, 0, 1) ** 1.6
    t = VT.BAYER[np.mod(yy, 4), np.mod(xx, 4)]
    g = np.floor(g * 10 + t) / 10
    g[rr > 0.97] = 0
    emi[y0:y1, x0:x1] = (g[..., None] * np.array((255, 190, 110))[None, None]).astype(np.uint8)
    img[y0:y1, x0:x1] = 0


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (16, 16, 16)
    emi = np.zeros_like(img)
    draw_map(img)
    draw_calendar(img)
    draw_sign(img)
    draw_lenses(img, emi)
    pb, pe = os.path.join(out, 'T_Hut_Panel_BaseColor.png'), os.path.join(out, 'T_Hut_Panel_Emission.png')
    Image.fromarray(img).save(pb)
    Image.fromarray(emi).save(pe)
    json.dump(dict(size=N, regions=REG), open(os.path.join(out, 'hut_panel_regions.json'), 'w'), indent=1)
    return pb, pe


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'hut')
    print(build(out))
