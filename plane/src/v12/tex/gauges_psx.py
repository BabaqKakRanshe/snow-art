"""v12: the instrument / placard atlas redrawn as PS1-style pixel art, 1024 x 1024, same UV layout as v7-v11
(T_Gauges_BC, T_Gauges_Emission, T_Displays_Emission). Every legend uses the pixel fonts of pxfont.py on the texel
grid, so text stays sharp under Point filtering; nothing is anti-aliased.

Texel density per region (1024 atlas; screen density at 1920 x 1080, vertical FOV 60, from the seat that reads it):
the drawing grid is chosen so one texel covers about one screen pixel or more from the seat:
  dials 64 px per dial (2 x 2 texel pixels in the 128 px cell), annunciator, label plates and the engine placard
  2 x 2 texel pixels, switch / CB lightplates, radio faces, compass card and the placards at 1 x 1.
Scales are simplified where 64 px cannot hold the original marks (fewer labels, minor ticks every 10 kt etc.).
python3 gauges_psx.py <out_dir>"""
import os, sys, math, json
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, '/home/claude/plane')
import pxfont as F
import panel7 as P6

N = 1024
SC = N / 4096.0
REG = json.load(open('/home/claude/plane/tex/v7/atlas7.json'))['regions']

# ------------------------------------------------------------------ palette (PS1-like: few flat colours)
BG = (10, 10, 10)
FACE = (14, 14, 14)
OUT = (6, 6, 6)
WHITE = (236, 236, 230)
GREY = (150, 150, 146)
DGREY = (90, 90, 88)
GREEN = (40, 190, 70)
YELLOW = (235, 200, 30)
RED = (220, 40, 30)
ORANGE = (240, 130, 20)
BLUEW = (210, 214, 222)
SKY = (60, 110, 175)
GROUND = (110, 70, 35)
PLATE = (33, 33, 35)
PLATE_HI = (66, 66, 68)
PLATE_LO = (12, 12, 13)
LEG = (234, 234, 228)
LEG_DIM = (200, 200, 194)
NUT = (16, 16, 17)
CREAM = (236, 235, 228)
INK = (20, 20, 20)
AMBER6, RED6, GREEN6 = (245, 168, 28), (236, 48, 32), (62, 212, 84)
ANN_RGB = {'red': RED6, 'green': GREEN6, 'amber': AMBER6}


class Reg:
    """drawing grid for one atlas region. rect in 4096-atlas pixels; size in mm (plate-local s right, t down);
    f = texels per drawing pixel (1 or 2, aligned to the absolute atlas grid)"""

    def __init__(self, rect, size_mm=None, f=1, bg=BG):
        x, y, w, h = rect
        self.X0, self.Y0, self.W, self.H = x * SC, y * SC, w * SC, h * SC
        self.f = f
        self.gx0, self.gy0 = int(math.floor(self.X0 / f)), int(math.floor(self.Y0 / f))
        self.gx1, self.gy1 = int(math.ceil((self.X0 + self.W) / f)), int(math.ceil((self.Y0 + self.H) / f))
        self.img = np.zeros((self.gy1 - self.gy0, self.gx1 - self.gx0, 3), np.uint8)
        self.img[:] = bg
        self.wm, self.hm = size_mm if size_mm else (self.W, self.H)
        self.kx = self.W / self.wm / f                       # drawing px per mm
        self.ky = self.H / self.hm / f

    def p(self, s, t):
        """plate mm -> drawing px (float; pixel i covers [i, i + 1))"""
        return ((self.X0 + s * self.W / self.wm) / self.f - self.gx0, (self.Y0 + t * self.H / self.hm) / self.f - self.gy0)

    def mm(self, d):
        return d * self.kx

    def paste(self, atlas, used):
        up = np.repeat(np.repeat(self.img, self.f, 0), self.f, 1)
        X, Y = self.gx0 * self.f, self.gy0 * self.f
        h, w = up.shape[:2]
        atlas[Y:Y + h, X:X + w] = up
        used[Y:Y + h, X:X + w] = True


# ------------------------------------------------------------------ text helpers in plate mm
def T(r, s, t, txt, font=F.F35, col=LEG, scale=1, align='c'):
    x, y = r.p(s, t)
    return F.text(r.img, x, y, txt, font, col, scale, align)


def fit_scale(txt, font, max_w_px, scales=(2, 1)):
    for sc in scales:
        if F.text_size(txt, font, sc)[0] <= max_w_px:
            return sc
    return 1


# ================================================================== dials (64 px drawing grid in a 128 px cell)
DS = 64
C0 = DS / 2.0
RD = DS / 2.0 * 0.96


def cell_reg(i, f=2):
    col, row = i % 8, i // 8
    return Reg((col * 512, row * 512, 512, 512), None, f, OUT)


def new_dial(i, face=FACE):
    r = cell_reg(i)
    F.disc(r.img, C0, C0, C0, face)
    return r


LAYOUT_WARN = []
R_ARC, R_MIN0, R_MAJ0, R_TICK1, R_LAB = 0.90, 0.88, 0.76, 0.95, 0.70


def label_pos(s, font, a, r_out=R_LAB):
    """centre of a dial numeral whose box just stays inside radius r_out (x RD) along its own direction"""
    w, h = F.text_size(s, font)
    e = abs(math.sin(math.radians(a))) * w / 2 + abs(math.cos(math.radians(a))) * h / 2
    return F.pol(C0, C0, RD * r_out - e, a)


def check_layout(name, ink, boxes, pad=1, gap=2):
    """text boxes must not touch each other or the ticks / arcs drawn before them"""
    for i, (x0, y0, x1, y1, t) in enumerate(boxes):
        sub = ink[max(0, y0 - pad):y1 + pad + 1, max(0, x0 - pad):x1 + pad + 1]
        if sub.any():
            LAYOUT_WARN.append(f'{name}: "{t}" touches a tick / arc ({int(sub.sum())} px)')
        for (a0, b0, a1, b1, u) in boxes[:i]:
            if not (x1 + gap < a0 or a1 + gap < x0 or y1 + gap < b0 or b1 + gap < y0):
                LAYOUT_WARN.append(f'{name}: "{t}" touches "{u}"')


class Boxes:
    def __enter__(self):
        F.BOXES = []
        return F.BOXES

    def __exit__(self, *a):
        F.BOXES = None


def ink_of(r, face=FACE):
    im = r.img
    m = np.any(im != np.array(face, np.uint8), axis=2)
    yy, xx = np.mgrid[0:im.shape[0], 0:im.shape[1]] + 0.5
    return m & (((xx - C0) ** 2 + (yy - C0) ** 2) <= (C0 - 0.5) ** 2)


def dial(i, vmin, vmax, a0, a1, majors, minors, labels, arcs=(), redlines=(), title='', sub='', lab_r=R_LAB,
         title_y=0.38, sub_y=0.60, lab_font=F.F35, title_font=F.F35, sub_font=F.F35, skip_major=(), extra=None,
         name='', title_dx=0.0, sub_dx=0.0, text_gap=2):
    r = new_dial(i)
    im = r.img
    ang = lambda v: a0 + (v - vmin) / (vmax - vmin) * (a1 - a0)
    for a in arcs:
        v0, v1, col = a[:3]
        rr = a[3] if len(a) > 3 else R_ARC
        w = a[4] if len(a) > 4 else 2.0
        F.ring(im, C0, C0, RD * rr - w / 2, RD * rr + w / 2, col, ang(v0), ang(v1))
    for v in minors:
        F.tick(im, C0, C0, RD * R_MIN0, RD * R_TICK1, ang(v), WHITE)
    for v in majors:
        if v not in skip_major:
            F.tick(im, C0, C0, RD * R_MAJ0, RD * R_TICK1, ang(v), WHITE)
    for v in redlines:
        F.tick(im, C0, C0, RD * R_MAJ0, RD * 0.98, ang(v), RED, 2)
    ink = ink_of(r)
    with Boxes() as boxes:
        for v, s in labels:
            rr = lab_r
            if isinstance(s, tuple):
                s, rr = s
            x, y = label_pos(s, lab_font, ang(v), rr)
            F.text(im, x, y, s, lab_font, WHITE)
        if extra:
            extra(r, ang)
        fixed = list(boxes)
        # title and sub: nearest free spot to the asked one (no touching numerals, ticks, each other or the needle hub)
        for txt, fnt, y0, dx0, col in ((title, title_font, title_y, title_dx, WHITE), (sub, sub_font, sub_y, sub_dx, LEG_DIM)):
            if not txt:
                continue
            w, h = F.text_size(txt, fnt)
            best = None
            for dy in sorted(range(-6, 7), key=abs):
                for dx in sorted(range(-5, 6), key=abs):
                    cx, cy = C0 + dx0 + dx, DS * y0 + dy
                    X, Y = int(math.floor(cx - w / 2 + 0.5)), int(math.floor(cy - h / 2 + 0.5))
                    box = (X, Y, X + w - 1, Y + h - 1)
                    if box_free(box, ink, fixed, text_gap=text_gap):
                        best = (abs(dy) + abs(dx), cx, cy)
                        break
                if best:
                    break
            if best is None:
                LAYOUT_WARN.append(f'{name or i}: no free place for "{txt}"')
                best = (0, C0 + dx0, DS * y0)
            F.text(im, best[1], best[2], txt, fnt, col)
            fixed = list(boxes)
        check_layout(name or f'cell{i}', ink, list(boxes), gap=text_gap)
    return r


HUB = (29, 29, 34, 34)                                          # needle hub (cap ~2.6 px radius) in the 64 px dial


def box_free(box, ink, others, pad=1, text_gap=2):
    x0, y0, x1, y1 = box
    if x0 < 2 or y0 < 2 or x1 > DS - 3 or y1 > DS - 3:
        return False
    if (x0 - C0) ** 2 + (y0 - C0) ** 2 > (C0 - 2) ** 2 or (x1 - C0) ** 2 + (y1 - C0) ** 2 > (C0 - 2) ** 2 or \
            (x0 - C0) ** 2 + (y1 - C0) ** 2 > (C0 - 2) ** 2 or (x1 - C0) ** 2 + (y0 - C0) ** 2 > (C0 - 2) ** 2:
        return False
    if ink[max(0, y0 - pad):y1 + pad + 1, max(0, x0 - pad):x1 + pad + 1].any():
        return False
    for k, (a0, b0, a1, b1) in enumerate([HUB] + [o[:4] for o in others]):
        p = pad if k == 0 else text_gap                        # 2 px between two texts: words must not run together
        if not (x1 + p < a0 or a1 + p < x0 or y1 + p < b0 or b1 + p < y0):
            return False
    return True


def rng(a, b, st):
    out, v = [], a
    while v <= b + 1e-9:
        out.append(round(v, 6))
        v += st
    return out


def cell_asi():
    return dial(0, 0, 200, 10, 330, rng(20, 200, 20), rng(30, 190, 20),
                [(v, str(v)) for v in (40, 80, 120, 160, 200)],
                arcs=[(45, 110, BLUEW, 0.80, 1.4), (60, 150, GREEN), (150, 175, YELLOW)], redlines=[175],
                title='KNOTS', title_y=0.62, title_dx=-3.0, name='ASI')


def cell_alt():
    """v7 Kollsman window (cut out of the dial mesh; the pressure disc ALT_Baro turns behind it) on the right: the
    numeral 3 moves outside the window, in place of its major tick"""
    w = P6.BARO_WIN
    X = lambda u: C0 + u * DS / 2
    Z = lambda v: C0 - v * DS / 2
    x0, x1, y0, y1 = X(w['x0']), X(w['x1']), Z(w['z1']), Z(w['z0'])
    r = dial(3, 0, 10, 0, 360, rng(0, 9, 1), rng(0.5, 9.5, 1),
             [(v, str(v)) for v in range(10) if v != 3] + [(3, ('3', 0.93))],
             title='ALT', sub='100FT', title_y=0.36, sub_y=0.605, lab_font=F.F57, skip_major=(3,), name='ALT',
             text_gap=1)
    F.rect(r.img, math.floor(x0) - 1, math.floor(y0) - 1, math.ceil(x1), math.ceil(y1), (60, 60, 62))
    F.rect(r.img, math.floor(x0), math.floor(y0), math.ceil(x1) - 1, math.ceil(y1) - 1, (8, 8, 8))
    return r


def cell_baro():
    """pressure disc behind the Kollsman window (seen only through the small window): 128 grid so the radial labels
    (every 0.1 inHg: 29.9, 30.0 ...) do not overlap; ticks every 0.05. The label of value v sits at clock angle
    90 - (v - 29.92) * 120 and reads upright at 3 o'clock"""
    r = cell_reg(21, f=1)
    im = r.img
    n = im.shape[0]
    c = n / 2.0
    im[:] = (8, 8, 8)
    F.disc(im, c, c, c, (10, 10, 10))
    k = (n / 2) / P6.BARO_DISC_R
    ang = lambda v: 90.0 - (v - 29.92) * P6.BARO_DEG_PER_INHG
    lo, hi = P6.BARO_RANGE
    for i in range(int(round((hi - lo) / 0.05)) + 1):
        v = lo + i * 0.05
        major = abs(v * 10 - round(v * 10)) < 1e-6
        F.tick(im, c, c, 0.22 * k, (0.33 if major else 0.29) * k, ang(v), WHITE)
    for i in range(int(round((hi - lo) / 0.1)) + 1):
        v = lo + i * 0.1
        a = ang(v)
        x, y = F.pol(c, c, P6.BARO_LABEL_R * k, a)
        F.rot_text(im, x, y, f'{v:.1f}', F.F35, WHITE, a - 90.0, thr=0.5)
    return r


def cell_vsi():
    ang_ = lambda v: -90 + v / 2000 * 165

    def extra(r, ang):
        im = r.img
        F.text(im, *label_pos('0', F.F57, ang_(0)), '0', F.F57, WHITE)
        for v in (500, 1000, 1500):
            F.text(im, *label_pos(str(v // 100), F.F35, ang_(v)), str(v // 100), F.F35, WHITE)
            F.text(im, *label_pos(str(v // 100), F.F35, ang_(-v)), str(v // 100), F.F35, WHITE)
        F.text(im, *label_pos('20', F.F35, 90), '20', F.F35, WHITE)
        F.text(im, 24.5, 25.5, 'UP', F.F35, WHITE)
        F.text(im, 24.5, 39.5, 'DN', F.F35, WHITE)
        F.text(im, 41.5, 25.5, 'FPM', F.F35, LEG_DIM)
        F.text(im, 41.5, 39.5, 'x100', F.F35, LEG_DIM)
    majors = [v for v in range(-2000, 2001, 100) if v % 500 == 0]
    minors = [v for v in range(-2000, 2001, 100) if v % 500]
    return dial(6, -2000, 2000, ang_(-2000), ang_(2000), majors, minors, [], extra=extra, name='VSI')


def cell_tc():
    def extra(r, ang):
        im = r.img
        F.text(im, *F.pol(C0, C0, RD * 0.66, -128), 'L', F.F57, WHITE)
        F.text(im, *F.pol(C0, C0, RD * 0.66, 128), 'R', F.F57, WHITE)
        F.text(im, C0, DS * 0.20, 'TURN COORD', F.F35, WHITE)
        F.text(im, C0, DS * 0.30, '2 MIN', F.F35, WHITE)
        F.text(im, C0, DS * 0.885, 'NO PITCH', F.F35, LEG_DIM)
    r = dial(4, 0, 1, 0, 1, [], [], [], extra=extra, name='TC')
    im = r.img
    for a in (-90, 90, -110, 110):
        F.tick(im, C0, C0, RD * 0.70, RD * 0.95, a, WHITE, 2)
    F.ring(im, C0, DS * 0.12, DS * 0.62 - 2.9, DS * 0.62 + 2.9, (60, 60, 60), 160, 200)
    for dx in (-3.5, 3.0):
        F.rect(im, C0 + dx, DS * 0.69, C0 + dx, DS * 0.80, (0, 0, 0))
    return r


def cell_att_bezel():
    r = new_dial(1)
    im = r.img
    for a, L in ((0, 0.20), (-10, 0.10), (10, 0.10), (-20, 0.10), (20, 0.10), (-30, 0.16), (30, 0.16),
                 (-60, 0.16), (60, 0.16), (-90, 0.12), (90, 0.12), (-45, 0.08), (45, 0.08)):
        F.tick(im, C0, C0, RD * (0.98 - L), RD * 0.97, a, WHITE, 2 if L >= 0.16 else 1)
    p = [F.pol(C0, C0, RD * 0.97, -6), F.pol(C0, C0, RD * 0.97, 6), F.pol(C0, C0, RD * 0.78, 0)]
    yy, xx = np.mgrid[0:DS, 0:DS] + 0.5
    def side(a, b):
        return (b[0] - a[0]) * (yy - a[1]) - (b[1] - a[1]) * (xx - a[0])
    s0, s1, s2 = side(p[0], p[1]), side(p[1], p[2]), side(p[2], p[0])
    m = ((s0 >= 0) & (s1 >= 0) & (s2 >= 0)) | ((s0 <= 0) & (s1 <= 0) & (s2 <= 0))
    im[m] = WHITE
    return r


def cell_att_card():
    r = cell_reg(2)
    im = r.img
    im[:] = SKY
    im[DS // 2:, :] = GROUND
    F.rect(im, 0, DS // 2, DS - 1, DS // 2, WHITE)
    px10 = DS / 2 * (0.006 / 0.042)
    for p in (-20, -10, -5, 5, 10, 20):
        y = DS / 2 - p / 10 * px10
        L = DS * (0.16 if p % 10 == 0 else 0.07)
        F.rect(im, C0 - L, math.floor(y), C0 + L - 1, math.floor(y), WHITE)
        if abs(p) == 10:
            F.text(im, C0 - L - 5, math.floor(y) + 0.5, '10', F.F35, WHITE)
        if abs(p) == 20:
            F.text(im, C0 + L + 4, math.floor(y) + 0.5, '20', F.F35, WHITE)
    yy, xx = np.mgrid[0:DS, 0:DS] + 0.5                      # sky pointer
    tri = [F.pol(C0, C0, DS * 0.40, 0), F.pol(C0, C0, DS * 0.45, -6), F.pol(C0, C0, DS * 0.45, 6)]
    def side(a, b):
        return (b[0] - a[0]) * (yy - a[1]) - (b[1] - a[1]) * (xx - a[0])
    s0, s1, s2 = side(tri[0], tri[1]), side(tri[1], tri[2]), side(tri[2], tri[0])
    im[((s0 >= 0) & (s1 >= 0) & (s2 >= 0)) | ((s0 <= 0) & (s1 <= 0) & (s2 <= 0))] = WHITE
    return r


def rot90_text(img, cx, cy, txt, font, col, quarter):
    """text turned by quarter x 90 deg clockwise (whole-pixel rotation: no resampling)"""
    m = np.rot90(F.text_mask(txt, font), -quarter % 4)
    h, w = m.shape
    F.blit_mask(img, m, int(math.floor(cx - w / 2 + 0.5)), int(math.floor(cy - h / 2 + 0.5)), col)
    if F.BOXES is not None:
        X, Y = int(math.floor(cx - w / 2 + 0.5)), int(math.floor(cy - h / 2 + 0.5))
        F.BOXES.append((X, Y, X + w - 1, Y + h - 1, txt))


def cell_hdg():
    """heading card (turns with the heading): numerals every 30 deg printed in the nearest quarter turn of their
    radial orientation, so they stay clean pixels (at most 45 deg tilt when they reach the lubber line)"""
    def extra(r, ang):
        for a in range(0, 360, 30):
            s = {0: 'N', 90: 'E', 180: 'S', 270: 'W'}.get(a, str(a // 10))
            q = int(round(a / 90.0)) % 4
            x, y = F.pol(C0, C0, RD * (0.60 if len(s) == 1 else 0.58), a)
            rot90_text(r.img, x, y, s, F.F57 if a % 90 == 0 else F.F35, ORANGE if a % 90 == 0 else WHITE, q)
    r = dial(5, 0, 360, 0, 360, [a for a in range(0, 360, 30)], [a for a in range(0, 360, 10) if a % 30],
             [], extra=extra, name='HDG')
    LAYOUT_WARN[:] = [w for w in LAYOUT_WARN if not w.startswith('HDG:') or 'tick' in w]
    return r


def cell_engine(i, title, sub, vmin, vmax, step, lab_div, green, red=None, yellow=None, lab_step=None, labels=None):
    """2-1/4 in. engine dials: 5 x 7 numerals (the 64 px dial is a bit denser than the screen from the seat at 1080p;
    5 x 7 glyphs survive that, 3 x 5 do not), so only a few numbers"""
    arcs = [(green[0], green[1], GREEN)]
    if yellow:
        arcs.append((yellow[0], yellow[1], YELLOW))
    lab_step = lab_step or step
    labs = labels if labels is not None else [(v, str(int(round(v / lab_div)))) for v in rng(vmin, vmax, lab_step)]
    return dial(i, vmin, vmax, -135, 135, rng(vmin, vmax, step), [v + step / 2 for v in rng(vmin, vmax - step, step)],
                labs, arcs=arcs, redlines=[red] if red is not None else [], title=title, sub=sub, lab_font=F.F57,
                name=title, sub_y=0.62)


def cell_oil():
    ap = lambda v: -150 + v / 200 * 120
    at = lambda v: 150 - v / 150 * 120

    def extra(r, ang):
        im = r.img
        for v in (0, 100, 200):
            s = str(v // 10) if v else '0'
            F.text(im, *label_pos(s, F.F35, ap(v)), s, F.F35, WHITE)
        for v in (0, 150):
            s = str(v // 10) if v else '0'
            F.text(im, *label_pos(s, F.F35, at(v)), s, F.F35, WHITE)
        F.text(im, DS * 0.37, DS * 0.64, 'PSI', F.F35, LEG_DIM)
        F.text(im, DS * 0.64, DS * 0.64, '°C', F.F35, LEG_DIM)
        F.text(im, C0, DS * 0.37, 'OIL', F.F35, WHITE)
    r = new_dial(12)
    im = r.img
    F.ring(im, C0, C0, RD * R_ARC - 1, RD * R_ARC + 1, GREEN, ap(85), ap(105))
    F.ring(im, C0, C0, RD * R_ARC - 1, RD * R_ARC + 1, GREEN, at(120), at(10))
    for v in rng(0, 200, 20):
        F.tick(im, C0, C0, RD * (R_MAJ0 if v % 40 == 0 else R_MIN0), RD * R_TICK1, ap(v), WHITE)
    for v in rng(0, 150, 15):
        F.tick(im, C0, C0, RD * (R_MAJ0 if v % 30 == 0 else R_MIN0), RD * R_TICK1, at(v), WHITE)
    F.tick(im, C0, C0, RD * R_MAJ0, RD * 0.98, ap(105), RED, 2)
    F.tick(im, C0, C0, RD * R_MAJ0, RD * 0.98, at(99), RED, 2)
    ink = ink_of(r)
    with Boxes() as boxes:
        extra(r, None)
        check_layout('OIL', ink, list(boxes))
    return r


def cell_fuel(i, side):
    return dial(i, 0, 60, -60, 60, rng(0, 60, 15), rng(5, 55, 10),
                [(0, 'E'), (60, 'F')], arcs=[(0, 5, RED)], lab_font=F.F57,
                title=f'FUEL {side}', sub='GAL', title_y=0.68, sub_y=0.82, name=f'FUEL {side}',
                extra=lambda r, ang: F.text(r.img, *label_pos('1/2', F.F35, ang(30)), '1/2', F.F35, WHITE))


def cell_clock():
    def extra(r, ang):
        for h in (3, 6, 9, 12):                                   # quarter hours as numerals, the rest ticks
            F.text(r.img, *label_pos(str(h), F.F57, h * 30, 0.70), str(h), F.F57, WHITE)
    r = dial(15, 0, 60, 0, 360, rng(0, 55, 5), [], [], extra=extra, name='CLOCK')
    for m in range(60):
        if m % 5:
            x, y = F.pol(C0, C0, RD * 0.93, m * 6)
            F.rect(r.img, math.floor(x), math.floor(y), math.floor(x), math.floor(y), DGREY)
    return r


def cell_amp():
    return dial(16, -60, 60, -90, 90, rng(-60, 60, 30), rng(-50, 50, 10),
                [(-60, '-60'), (0, '0'), (60, '60')], title='AMPS', title_y=0.70, lab_font=F.F57, name='AMPS')


def cell_volt():
    return dial(17, 0, 35, -135, 135, rng(0, 35, 5), [v for v in range(0, 36) if v % 5],
                [(v, str(v)) for v in (0, 10, 20, 30)], arcs=[(24, 29, GREEN), (29, 31, YELLOW)], redlines=[32],
                title='VOLTS', sub='DC', title_y=0.62, sub_y=0.38, lab_font=F.F57, name='VOLTS')


def cell_vac():
    return dial(18, 0, 10, -135, 135, rng(0, 10, 1), rng(0.5, 9.5, 1), [(v, str(v)) for v in (0, 5, 10)],
                arcs=[(4.5, 5.5, GREEN)], title='SUCTION', lab_font=F.F57, name='SUCTION')


def cell_oat():
    return dial(23, -40, 50, -135, 135, rng(-40, 50, 10), rng(-35, 45, 10),
                [(v, str(v)) for v in (-40, 0, 40)], title='OAT °C', lab_font=F.F57, name='OAT')


def cell_hobbs():
    r = new_dial(19)
    im = r.img
    r_mm = P6.DS / 2 - P6.BEZEL_W[P6.DS]
    k = DS / (2 * r_mm * 1000)
    w = P6.HOBBS_WIN
    cx, cy = DS / 2 + w['dx'] * 1000 * k, DS / 2 - w['dz'] * 1000 * k
    hw, hh = w['w'] * 500 * k, w['h'] * 500 * k
    F.rect(im, cx - hw - 2, cy - hh - 2, cx + hw + 1, cy + hh + 1, (40, 40, 42))
    F.rect(im, cx - hw, cy - hh, cx + hw - 1, cy + hh - 1, (9, 12, 10))
    F.text(im, C0, cy - hh - 7, 'HOURS', F.F35, WHITE)
    F.text(im, C0, cy + hh + 7, 'HOBBS', F.F35, LEG_DIM)
    F.text(im, C0, cy + hh + 14, 'QUARTZ', F.F35, (150, 150, 145))
    return r


# ================================================================== cell 20: v5 placards (1 texel per pixel)
P20 = {'QUAD': (0, 0, 512, 48), 'FLAP': (0, 52, 384, 308), 'TRIM': (388, 52, 508, 92), 'FUEL': (0, 312, 256, 376),
       'DOOR': (256, 312, 512, 376), 'EXT': (0, 380, 256, 428), 'CDOOR': (256, 380, 512, 428),
       'FLOOR': (0, 432, 512, 508)}


def sub20(key, bg):
    x0, y0, x1, y1 = P20[key]
    return Reg((2048 + x0, 1024 + y0, x1 - x0, y1 - y0), None, 1, bg)


def cell20(regs):
    r = Reg((2048, 1024, 512, 512), None, 1, (10, 10, 10))
    regs.append(r)
    q = sub20('QUAD', (22, 22, 24))
    w = q.img.shape[1]
    for i, t in enumerate(('POWER', 'PROP', 'FUEL COND')):
        F.text(q.img, (i + 0.5) * w / 3, q.img.shape[0] / 2, t, F.F35, LEG)
        if i:
            F.rect(q.img, round(i * w / 3), 2, round(i * w / 3), q.img.shape[0] - 3, GREY)
    regs.append(q)
    fl = sub20('FLAP', (22, 22, 24))
    W, H = fl.img.shape[1], fl.img.shape[0]
    F.text(fl.img, W / 2, H * 0.17, 'FLAPS', F.F57, WHITE)
    F.rect(fl.img, W * 0.14, H * 0.46, W * 0.86, H * 0.46, GREY)
    for i, t in enumerate(('FULL', '20°', '10°', 'UP')):
        cx = W * (0.14 + 0.24 * i)
        F.rect(fl.img, cx, H * 0.33, cx, H * 0.60, WHITE)
        F.text(fl.img, cx, H * 0.76, t, F.F35, WHITE)
    regs.append(fl)
    tr = sub20('TRIM', (22, 22, 24))
    W, H = tr.img.shape[1], tr.img.shape[0]
    for i, (t, col) in enumerate((('DN', WHITE), ('TO', (60, 200, 80)), ('UP', WHITE))):
        cx = W * (0.15 + 0.35 * i)
        F.rect(tr.img, cx, 0, cx, 2, col)
        F.text(tr.img, cx, 6.5, t, F.F35, col)
    regs.append(tr)
    fu = sub20('FUEL', (22, 22, 24))
    W, H = fu.img.shape[1], fu.img.shape[0]
    F.text(fu.img, W / 2, H * 0.30, 'FUEL SHUTOFF', F.F35, (230, 60, 45))
    F.text(fu.img, W / 2, H * 0.74, 'PULL OFF', F.F35, WHITE)
    regs.append(fu)
    do = sub20('DOOR', (40, 40, 42))
    W, H = do.img.shape[1], do.img.shape[0]
    F.text(do.img, W / 2, H * 0.30, 'DOOR', F.F35, WHITE)
    F.text(do.img, W / 2, H * 0.74, 'PULL TO OPEN', F.F35, WHITE)
    regs.append(do)
    ex = sub20('EXT', (190, 30, 25))
    W, H = ex.img.shape[1], ex.img.shape[0]
    F.text(ex.img, W / 2, H * 0.27, 'FIRE', F.F35, (245, 245, 240))
    F.text(ex.img, W / 2, H * 0.73, 'EXTINGUISHER', F.F35, (245, 245, 240))
    regs.append(ex)
    cd = sub20('CDOOR', (40, 40, 42))
    W, H = cd.img.shape[1], cd.img.shape[0]
    F.text(cd.img, W / 2, H * 0.27, 'CARGO DOOR', F.F35, WHITE)
    F.text(cd.img, W / 2, H * 0.73, 'PULL TO OPEN', F.F35, WHITE)
    regs.append(cd)
    fo = sub20('FLOOR', (16, 16, 16))
    W, H = fo.img.shape[1], fo.img.shape[0]
    for xa in (0, W - 6):                                     # hazard stripes at both ends
        for y in range(H):
            for x in range(6):
                if ((x + y) // 3) % 2 == 0:
                    fo.img[y, xa + x] = (230, 190, 20)
    F.text(fo.img, W / 2, H * 0.20, 'MAX FLOOR LOADING', F.F35, (235, 195, 30))
    F.text(fo.img, W / 2, H * 0.50, '200 LB/SQ FT', F.F35, (235, 195, 30))
    F.text(fo.img, W / 2, H * 0.80, 'SECURE ALL CARGO', F.F35, (235, 235, 230))
    regs.append(fo)


# ================================================================== old v5 strip rows still in use
def cmp_card():
    """compass correction card (top half row 3, x 0..512, y 1885..2041 in 4096 px)"""
    r = Reg((0, 1885, 512, 156), None, 1, CREAM)
    rows = [('FOR', 'N', '30', '60', 'E', '120', '150'), ('STR', '359', '28', '61', '92', '118', '151'),
            ('FOR', 'S', '210', '240', 'W', '300', '330'), ('STR', '182', '209', '242', '271', '299', '331')]
    W, H = r.img.shape[1], r.img.shape[0]
    F.frame(r.img, 0, 0, W - 1, H - 1, (40, 40, 40))
    for i, vals in enumerate(rows):
        for c, v in enumerate(vals):
            F.text(r.img, 9 + c * 18.3, 5.5 + i * 9, v, F.F35, INK if c else (120, 30, 25))
    return r


def ovh_fuel():
    r = Reg((512, 1885, 512, 156), None, 1, (22, 22, 24))
    W, H = r.img.shape[1], r.img.shape[0]
    F.text(r.img, W * 0.25, H * 0.28, 'LEFT', F.F57, (230, 230, 225))
    F.text(r.img, W * 0.75, H * 0.28, 'RIGHT', F.F57, (230, 230, 225))
    F.text(r.img, W * 0.5, H * 0.70, 'FUEL ON/OFF', F.F57, (230, 70, 50))
    return r


def compass_strip():
    reg = REG['COMPASS']
    r = Reg(reg['rect'], reg['size_mm'], 1, (12, 12, 12))
    W = r.wm
    NAMES = {0: 'N', 90: 'E', 180: 'S', 270: 'W'}
    for L in range(0, 360, 5):
        beta = (L - 180) % 360
        u = ((360 - beta) % 360) / 360.0
        for wrap in (-1, 0, 1):
            s_ = (u + wrap) * W
            if -8 <= s_ <= W + 8:
                x, y0 = r.p(s_, 1.5)
                _, y1 = r.p(s_, 6.5 if L % 10 == 0 else 4.5)
                F.rect(r.img, math.floor(x), math.floor(y0), math.floor(x), math.floor(y1), (236, 236, 230))
                if L % 30 == 0:
                    xx, yy = r.p(s_, 14.5)
                    F.text(r.img, xx, yy, NAMES.get(L, str(L // 10)), F.F57, (240, 240, 232))
    x0, y0 = r.p(0, 0.6)
    F.rect(r.img, 0, math.floor(y0), r.img.shape[1] - 1, math.floor(y0), (90, 90, 88))
    return r


# ================================================================== bottom half: lightplates, radios, placards
def bevel(r, light=PLATE_HI, dark=PLATE_LO):
    h, w = r.img.shape[:2]
    F.frame(r.img, 0, 0, w - 1, h - 1, dark)
    F.rect(r.img, 1, 1, w - 2, 1, light)
    F.rect(r.img, 1, 1, 1, h - 2, light)


def circle_mm(r, s, t, rad, col):
    x, y = r.p(s, t)
    F.disc(r.img, x, y, rad * r.kx, col)


def radio_face(kind, lit=False):
    reg = REG['R_' + kind]
    spec = P6.RADIO_FACE[kind]
    r = Reg(reg['rect'], reg['size_mm'], 1, (0, 0, 0) if lit else (31, 31, 33))
    L = (lambda v: tuple(int(c * v) for c in (255, 252, 240))) if lit else (lambda v: None)
    if not lit:
        bevel(r, (70, 70, 72), (10, 10, 11))
        for nm, (s0, t0, s1, t1) in spec['windows'].items():
            x0, y0 = r.p(s0 - 1.2, t0 - 1.2); x1, y1 = r.p(s1 + 1.2, t1 + 1.2)
            F.rect(r.img, x0, y0, x1 - 1, y1 - 1, (16, 16, 17))
            x0, y0 = r.p(s0, t0); x1, y1 = r.p(s1, t1)
            F.rect(r.img, x0, y0, x1 - 1, y1 - 1, (7, 9, 9))
        for s, t, od, idd, kd in spec['knobs']:
            circle_mm(r, s, t, od / 2 + 1.0, (14, 14, 15))
        for s, t, dd, col in spec.get('lamps', []):
            circle_mm(r, s, t, dd / 2 + 0.6, (12, 12, 12))
            circle_mm(r, s, t, dd / 2, tuple(int(c * 0.42) for c in col))
    for s, t, sz, txt in spec['texts'] + spec.get('lamp_labels', []):
        big = txt in ('GPS', 'XPDR', 'ADF', 'COM', 'NAV') and sz >= 2.6
        x, y = r.p(s, t)
        F.text(r.img, x, y, txt, F.F35, L(0.5) if lit else LEG_DIM, 2 if big else 1)
    for s0, t0, s1, t1, txt in spec['caps']:
        x0, y0 = r.p(s0, t0); x1, y1 = r.p(s1, t1)
        if not lit:
            F.rect(r.img, x0, y0, x1 - 1, y1 - 1, (50, 50, 54))
            F.frame(r.img, x0, y0, x1 - 1, y1 - 1, (18, 18, 20))
            F.rect(r.img, x0 + 1, y0 + 1, x1 - 2, y0 + 1, (84, 84, 88))
        txt2 = {'<>': '⇆', 'D->': 'D→', 'FLT/ET': 'FLT', 'SET/RST': 'RST'}.get(txt, txt)
        F.text(r.img, (x0 + x1) / 2, (y0 + y1) / 2, txt2, F.F35, L(0.75) if lit else (226, 226, 220))
    return r


def ann_lines(name, max_w):
    """one line if it fits 86 % of the lens, else two lines split at the space nearest the middle"""
    if F.text_size(name, F.F35)[0] <= max_w or ' ' not in name:
        return [name]
    sp = [i for i, c in enumerate(name) if c == ' ']
    i = min(sp, key=lambda k: abs(k - len(name) / 2))
    return [name[:i], name[i + 1:]]


def annunciator(lit=False):
    reg = REG['ANN']
    r = Reg(reg['rect'], reg['size_mm'], 2, (0, 0, 0) if lit else (13, 13, 14))
    for i, name in enumerate(P6.ANN_LAMPS):
        col = ANN_RGB[P6.ANN_COLOR.get(name, 'amber')]
        s0, t0, s1, t1 = P6.ann_lens(i)
        x0, y0 = r.p(s0, t0); x1, y1 = r.p(s1, t1)
        x0, y0, x1, y1 = math.floor(x0 + 0.5), math.floor(y0 + 0.5), math.floor(x1 + 0.5) - 1, math.floor(y1 + 0.5) - 1
        lines = ann_lines(name, 0.86 * (x1 - x0 + 1))
        cx, cy = (x0 + x1 + 1) / 2, (y0 + y1 + 1) / 2
        if lit:
            F.rect(r.img, x0, y0, x1, y1, tuple(int(c * 0.30) for c in col))
            tc = tuple(min(255, int(c * 1.0 + 25)) for c in col)
        else:
            F.rect(r.img, x0 - 1, y0 - 1, x1 + 1, y1 + 1, (6, 6, 6))
            F.rect(r.img, x0, y0, x1, y1, tuple(int(c * 0.10) + 9 for c in col))
            F.rect(r.img, x0 + 1, y0 + 1, x1 - 1, y0 + 1, tuple(int(c * 0.16) + 22 for c in col))
            tc = tuple(int(c * 0.50) for c in col)
        for k, ln in enumerate(lines):
            F.text(r.img, cx, cy + (k - (len(lines) - 1) / 2) * 6, ln, F.F35, tc)
    return r


def _sw_local(x, z):
    xl, xr, zb, zt = P6.SW_PLATE
    return ((xl - x) * 1000, (zt - z) * 1000)


def switch_plate():
    reg = REG['SW']
    r = Reg(reg['rect'], reg['size_mm'], 1, PLATE)
    bevel(r)
    W, H = r.wm, r.hm
    for s, t in ((5, 5), (W - 5, 5), (5, H - 5), (W - 5, H - 5)):
        circle_mm(r, s, t, 2.6, NUT)
    for bone, (x, z, lab) in P6.RHEOSTATS.items():
        s, t = _sw_local(x, z)
        T(r, s, t - 22.0, lab)
        cx, cy = r.p(s, t)
        rad = r.mm(15.0)
        F.ring(r.img, cx, cy, rad - 0.5, rad + 0.5, LEG, -135, 135)
        for a in (-135, -90, -45, 0, 45, 90, 135):
            F.tick(r.img, cx, cy, rad, rad + 2, a, LEG)
        for a, txt in ((-135, 'OFF'), (135, 'BRT')):
            T(r, s + 21.5 * math.sin(math.radians(a)), t - 21.5 * math.cos(math.radians(a)), txt, col=LEG_DIM)
    for z in P6.SW_DIVIDERS:
        t = _sw_local(0, z)[1]
        x0, y = r.p(7, t); x1, _ = r.p(W - 7, t)
        F.rect(r.img, x0, y, x1, y, GREY)
    t_div = _sw_local(0, P6.SW_DIVIDERS[-1])[1]
    x, y0 = r.p(W / 2, t_div + 4); _, y1 = r.p(W / 2, H - 8)
    F.rect(r.img, x, y0, x, y1, (110, 110, 108))
    for x, z, txt in P6.SW_HEADERS:
        s, t = _sw_local(x, z)
        w, _ = T(r, s, t, txt, col=(250, 250, 244))
        if txt in ('CARGO DOOR', 'DOORS'):
            xc, yc = r.p(s, t)
            x0, _ = r.p(10, t); x1, _ = r.p(W - 10, t)
            F.rect(r.img, x0, yc, xc - w / 2 - 3, yc, GREY)
            F.rect(r.img, xc + w / 2 + 2, yc, x1, yc, GREY)
    for bone, (x, z, lab, on, off) in P6.SWITCHES.items():
        s, t = _sw_local(x, z)
        if bone == 'SW_Starter':
            T(r, s + 26.0, t - 12.0, lab)
            T(r, s + 26.0, t - 2.0, on, col=LEG_DIM)
            T(r, s + 26.0, t + 8.0, off, col=LEG_DIM)
        else:
            T(r, s, t - 18.5, lab)
            T(r, s + 18.5, t - 6.0, on, col=LEG_DIM)
            T(r, s + 18.5, t + 6.5, off, col=LEG_DIM)
        circle_mm(r, s, t, 6.2, NUT)
    return r


def cb_plate():
    reg = REG['CB']
    r = Reg(reg['rect'], reg['size_mm'], 1, PLATE)
    bevel(r)
    xl, xr, zb, zt = P6.CB_PLATE
    w, _ = T(r, r.wm / 2, 8.5, 'CIRCUIT BREAKERS', col=(250, 250, 244))
    xc, yc = r.p(r.wm / 2, 8.5)
    x0, _ = r.p(8, 8.5); x1, _ = r.p(r.wm - 8, 8.5)
    F.rect(r.img, x0, yc, xc - w / 2 - 3, yc, GREY)
    F.rect(r.img, xc + w / 2 + 2, yc, x1, yc, GREY)
    for s, t in ((4.5, 4.5), (r.wm - 4.5, 4.5), (4.5, r.hm - 4.5), (r.wm - 4.5, r.hm - 4.5)):
        circle_mm(r, s, t, 2.4, NUT)
    for ri, z in enumerate(P6.CB_ROWS):
        for ci, x in enumerate(P6.CB_COLS):
            name, amps = P6.CB[ri][ci]
            s, t = (xl - x) * 1000, (zt - z) * 1000
            T(r, s, t - 12.5, name)
            circle_mm(r, s, t, P6.CB_COLLAR_R * 1000 + 0.4, (12, 12, 12))
            circle_mm(r, s, t, P6.CB_CAP_R * 1000, (20, 20, 21))
            T(r, s, t, str(amps), col=(246, 246, 240))
    return r


def label_plate(key, txt):
    reg = REG[key]
    r = Reg(reg['rect'], reg['size_mm'], 1, PLATE)
    bevel(r)
    h, w = r.img.shape[:2]
    sc = fit_scale(txt, F.F35, w - 4)
    F.text(r.img, w / 2, h / 2, txt, F.F35, LEG, sc)
    return r


def jacks_plate():
    reg = REG['JACKS']
    r = Reg(reg['rect'], reg['size_mm'], 1, PLATE)
    bevel(r)
    for s, t, txt in P6.JACK_POS:
        T(r, s, 6.5, txt)
        circle_mm(r, s, t, 5.4, (12, 12, 12))
    for s, t in ((3.5, 3.5), (r.wm - 3.5, 3.5), (3.5, r.hm - 3.5), (r.wm - 3.5, r.hm - 3.5)):
        circle_mm(r, s, t, 1.6, NUT)
    return r


def leader(r, x0, x1, y, col):
    for x in range(int(math.ceil(x0)), int(math.floor(x1)) + 1, 2):
        r.img[int(y), x] = col


def placard_limits():
    reg = REG['P_Limits']
    r = Reg(reg['rect'], reg['size_mm'], 1, (17, 17, 18))
    h, w = r.img.shape[:2]
    F.frame(r.img, 2, 2, w - 3, h - 3, (205, 205, 198))
    F.text(r.img, w / 2, 10, 'OPERATING LIMITATIONS', F.F57, (240, 240, 234))
    rows = [('MAX TAKEOFF WT', '8000 LB'), ('VA', '148 KIAS'), ('VFE 10°', '175 KIAS'), ('VFE 20°/FULL', '150/125'),
            ('DEMO X-WIND', '20 KT'), ('MAX ALTITUDE', '25000 FT')]
    y = 22
    for a, b in rows:
        wa, _ = F.text(r.img, 8, y, a, F.F35, (225, 225, 218), 2, 'l', 't')
        wb, _ = F.text(r.img, w - 8, y, b, F.F35, (235, 235, 228), 2, 'r', 't')
        leader(r, 8 + wa + 2, w - 8 - wb - 3, y + 8, (170, 170, 164))
        y += 13
    F.text(r.img, w / 2, y + 4, 'NO ACROBATICS', F.F35, (235, 235, 228), 2)
    F.text(r.img, w / 2, y + 17, 'DAY NIGHT VFR IFR NO ICING', F.F35, (235, 235, 228), 1)
    return r


def placard_nosmoke():
    reg = REG['P_NoSmoke']
    r = Reg(reg['rect'], reg['size_mm'], 1, CREAM)
    h, w = r.img.shape[:2]
    F.frame(r.img, 1, 1, w - 2, h - 2, (30, 30, 30))
    cx, cy = r.p(21.0, r.hm / 2)
    rad = r.mm(16.0)
    F.ring(r.img, cx, cy, rad - 3, rad, (205, 30, 25))
    x0, y0 = r.p(10, r.hm / 2 - 2); x1, y1 = r.p(28, r.hm / 2 + 2)
    F.rect(r.img, x0, y0, x1, y1, (40, 40, 40))
    x2, _ = r.p(31.5, 0)
    F.rect(r.img, x1 + 1, y0, x2, y1, (225, 120, 40))
    for k in range(3):
        F.line(r.img, x2 - 2 + 2 * k, y0 - 2, x2 - 1 + 2 * k, y0 - 6, (120, 120, 120))
    d = rad * 0.70
    F.line(r.img, cx - d, cy - d, cx + d, cy + d, (205, 30, 25), 2)
    F.line(r.img, cx - d + 1, cy - d, cx + d + 1, cy + d, (205, 30, 25), 1)
    tx, _ = r.p(87, 0)
    F.text(r.img, tx, h * 0.36, 'NO SMOKING', F.F35, INK, 2)
    F.text(r.img, tx, h * 0.70, 'FASTEN SEAT BELTS', F.F57, INK)
    return r


def placard_engine():
    reg = REG['P_Engine']
    r = Reg(reg['rect'], reg['size_mm'], 1, (17, 17, 18))
    h, w = r.img.shape[:2]
    F.frame(r.img, 1, 1, w - 2, h - 2, (200, 200, 194))
    F.text(r.img, w / 2, 6, 'ENGINE LIMITS', F.F35, (232, 232, 226))
    F.text(r.img, w / 2, 16, 'TRQ 1865  ITT 805°C', F.F35, (232, 232, 226), 2)
    F.text(r.img, w / 2, 28, 'NG 101.6%  NP 1900', F.F35, (232, 232, 226), 2)
    return r


def mapcase_plate():
    reg = REG['MAPCASE']
    r = Reg(reg['rect'], reg['size_mm'], 1, (20, 20, 21))
    h, w = r.img.shape[:2]
    F.text(r.img, w / 2, h / 2, 'MAP CASE', F.F35, (214, 214, 208), 2)
    return r


def poh_cover():
    reg = REG['POH']
    r = Reg(reg['rect'], reg['size_mm'], 1, (22, 26, 34))
    h, w = r.img.shape[:2]
    gold, pale = (220, 200, 130), (170, 150, 90)
    F.frame(r.img, 4, 4, w - 5, h - 5, pale)
    for i, s in enumerate(("PILOT'S", 'OPERATING', 'HANDBOOK')):
        F.text(r.img, w / 2, 40 + i * 17, s, F.F57, gold, 2 if F.text_size('OPERATING', F.F57, 2)[0] <= w - 10 else 1)
    F.rect(r.img, 22, 86, w - 23, 86, pale)
    F.text(r.img, w / 2, 96, 'UTILITY TURBOPROP', F.F35, (205, 205, 200))
    F.text(r.img, w / 2, 150, 'KEEP IN AIRCRAFT', F.F35, (160, 160, 155))
    return r


def map_art():
    reg = REG['MAP']
    r = Reg(reg['rect'], reg['size_mm'], 1, (214, 222, 196))
    im = r.img
    h, w = im.shape[:2]
    rnd = np.random.default_rng(42)
    for k in range(70):
        s, t, rr = rnd.uniform(0, r.wm), rnd.uniform(0, r.hm), rnd.uniform(6, 22)
        col = [(205, 214, 182), (222, 210, 176), (196, 205, 170)][rnd.choice([0, 1, 2])]
        x, y = r.p(s, t)
        F.disc(im, x, y, r.mm(rr), col)
    yy, xx = np.mgrid[0:h, 0:w] + 0.5
    for k in range(5):
        s, t = rnd.uniform(15, r.wm - 15), rnd.uniform(15, r.hm - 15)
        x, y = r.p(s, t)
        a, b = r.mm(rnd.uniform(5, 10)), r.mm(rnd.uniform(3, 7))
        m = ((xx - x) / a) ** 2 + ((yy - y) / b) ** 2 <= 1
        im[m] = (150, 196, 222)
        edge = m & ~ndimage.binary_erosion(m)
        im[edge] = (70, 120, 170)
    river = [(0, 30)]
    for k in range(1, 12):
        river.append((k * r.wm / 11, river[-1][1] + rnd.uniform(-9, 11)))
    for a, b in zip(river, river[1:]):
        F.line(im, *r.p(*a), *r.p(*b), (70, 130, 190))
    for s in np.arange(0, r.wm, 30):
        x, _ = r.p(s, 0)
        F.rect(im, x, 0, x, h - 1, (150, 150, 140))
    for t in np.arange(0, r.hm, 30):
        _, y = r.p(0, t)
        F.rect(im, 0, y, w - 1, y, (150, 150, 140))
    apts = [(40, 50), (120, 32), (170, 95), (78, 112), (196, 40)]
    for a, b in zip(apts, apts[1:]):
        F.line(im, *r.p(*a), *r.p(*b), (170, 60, 150))
    for i, (s, t) in enumerate(apts):
        x, y = r.p(s, t)
        F.ring(im, x, y, 1.5, 2.6, (170, 60, 150))
        F.text(im, x + 4, y - 5, ['NORTH FORK', 'ELK LAKE', 'RIDGE', 'BEAR CREEK', 'PINE BAY'][i], F.F35,
               (150, 40, 130), 1, 'l', 't')
    x0, y0 = r.p(r.wm - 70, r.hm - 22)
    F.rect(im, x0, y0, w - 4, h - 4, (245, 245, 238))
    F.frame(im, x0, y0, w - 4, h - 4, (40, 40, 40))
    F.text(im, (x0 + w - 4) / 2, y0 + 5, 'VFR CHART', F.F35, INK)
    F.text(im, (x0 + w - 4) / 2, y0 + 11, '1:500 000', F.F35, (30, 30, 30))
    for s in (r.wm / 3, 2 * r.wm / 3):
        x, _ = r.p(s, 0)
        F.rect(im, x, 0, x, h - 1, (236, 240, 226))
        F.rect(im, x + 1, 0, x + 1, h - 1, (168, 172, 150))
    _, y = r.p(0, r.hm / 2)
    F.rect(im, 0, y, w - 1, y, (236, 240, 226))
    F.rect(im, 0, y + 1, w - 1, y + 1, (168, 172, 150))
    return r


# ================================================================== assembly
LIT_REGIONS = ('SW', 'CB', 'L_CabinHeat', 'L_Defrost', 'L_ParkBrake', 'L_AnnTest', 'JACKS')


def region_box(rect, pad=0):
    x, y, w, h = rect
    return (int(math.floor(x * SC)) - pad, int(math.floor(y * SC)) - pad, int(math.ceil((x + w) * SC)) + pad,
            int(math.ceil((y + h) * SC)) + pad)


def build(out):
    atlas = np.zeros((N, N, 3), np.uint8)
    atlas[:] = BG
    used = np.zeros((N, N), bool)
    regs = []
    dials = [cell_asi(), cell_att_bezel(), cell_att_card(), cell_alt(), cell_tc(), cell_hdg(), cell_vsi(),
             cell_engine(7, 'TRQ x100', '', 0, 2400, 200, 100, (0, 1865), red=1865, lab_step=1200),
             cell_engine(8, 'ITT', '°C x100', 100, 1100, 100, 100, (400, 765), red=805, labels=[(100, '1'), (500, '5'), (900, '9')]),
             cell_engine(9, 'NG %', '', 0, 110, 10, 1, (52, 101.6), red=101.6, labels=[(0, '0'), (50, '50'), (100, '100')]),
             cell_engine(10, 'NP x100', '', 0, 2400, 200, 100, (1600, 1900), red=1900, lab_step=1200),
             cell_engine(11, 'FUEL x100', '', 0, 400, 50, 100, (60, 350), lab_step=200),
             cell_oil(), cell_fuel(13, 'L'), cell_fuel(14, 'R'), cell_clock(), cell_amp(), cell_volt(), cell_vac(),
             cell_hobbs(), cell_baro(), cell_oat()]
    regs += dials
    cell20(regs)
    regs += [cmp_card(), ovh_fuel(), compass_strip()]
    for u in P6.RADIOS:
        regs.append(radio_face(u))
    regs.append(annunciator())
    regs.append(switch_plate())
    regs.append(cb_plate())
    for k, v in P6.LABELS.items():
        regs.append(label_plate(k, {'PARKING BRAKE': 'PARK BRAKE'}.get(v[4], v[4])))
    regs += [jacks_plate(), placard_limits(), placard_nosmoke(), placard_engine(), mapcase_plate(), map_art(),
             poh_cover()]
    for r in regs:
        r.paste(atlas, used)
    # T_Displays_Emission: lit radio faces + lit annunciator, same UV space
    ems = np.zeros((N, N, 3), np.uint8)
    used_e = np.zeros((N, N), bool)
    for u in P6.RADIOS:
        radio_face(u, lit=True).paste(ems, used_e)
    annunciator(lit=True).paste(ems, used_e)
    # gutters: every texel outside the drawn regions takes its nearest drawn texel (mip-safe edges), 4 texels wide
    dist, ii = ndimage.distance_transform_edt(~used, return_indices=True)
    near = dist <= 4
    atlas[near] = atlas[ii[0], ii[1]][near]
    ems_f = ems.copy()
    ems_f[near] = ems[ii[0], ii[1]][near]
    # backlight emission (v7 rule): dial cells (top half, not cell 20 / 22), lightplates, compass card
    a = atlas.astype(np.float32) / 255.0
    k = np.clip((a.max(axis=2) - 0.30) / 0.55, 0.0, 1.0)[..., None]
    lit = np.zeros((N, N), bool)
    lit[:384, :] = True                                      # dial rows 0-2
    x0, y0, x1, y1 = region_box((2048, 1024, 512, 512))
    lit[y0:y1, x0:x1] = False                               # cell 20 placards
    x0, y0, x1, y1 = region_box((3072, 1024, 512, 512))
    lit[y0:y1, x0:x1] = False                               # cell 22 (unused)
    for n in LIT_REGIONS + ('COMPASS',):
        x0, y0, x1, y1 = region_box(REG[n]['rect'], 4)
        lit[y0:y1, x0:x1] = True
    eg = (a * k * 255 + 0.5).astype(np.uint8)
    eg[~lit] = 0
    os.makedirs(out, exist_ok=True)
    Image.fromarray(atlas, 'RGB').save(os.path.join(out, 'T_Gauges_BC.png'), optimize=True)
    Image.fromarray(eg, 'RGB').save(os.path.join(out, 'T_Gauges_Emission.png'), optimize=True)
    Image.fromarray(ems_f, 'RGB').save(os.path.join(out, 'T_Displays_Emission.png'), optimize=True)
    cols = np.unique(atlas.reshape(-1, 3), axis=0)
    print('saved', out, 'atlas colours', len(cols), 'regions', len(regs))
    for w in LAYOUT_WARN:
        print('LAYOUT', w)


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else '/home/claude/plane/v12/work/gauges')
