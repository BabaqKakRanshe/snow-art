"""Panel atlas of the Snow kit (T_Kit_Panel, 512 x 512, pixel art, point-filtered) and the CRT screen textures.
Regions, their physical sizes and what they show come from snowkit_spec.PANEL (each drawing keeps the physical aspect):
  btn_schranke / btn_tor / btn_licht / btn_blank  engraved push-button labels (white on black): SCHRANKE / BARRIER,
                 TOR / GATE, LICHT / LIGHTS, a blank one
  lbl_console    the strip on the console top: TORSTEUERUNG / GATE CONTROL
  sign_notstrom  the power cabinet's door plate: the yellow lightning triangle, NOTSTROM 12V / EMERGENCY 12V,
                 BATTERIE ANSCHLIESSEN / CONNECT BATTERY
  lbl_switch     the change-over switch plate: NETZ / MAINS at 10:30 (the handle's 0), BATTERIE / BATTERY at 1:30 (90
                 clockwise), the arc between them, the hub hole in the middle
  sign_volt      the yellow warning triangle with the black lightning (a sticker on a white label)
  sign_danger    the pole plate: the red lightning arrow, LEBENS- / GEFAHR over DANGER
  phone_dial     the rotary dial: cream number ring, the clear finger wheel, ten holes (1 at 2 o'clock ... 0 at 5 o'clock),
                 the finger stop at 4 o'clock, a paper centre label
  lbl_monitor    the CRT's lower bezel strip: CCTV / MONITOR at the left, CONTRAST, BRIGHT, POWER over the knobs
                 (knob centres at u 0.410, 0.676, 0.895 of the strip)
  lbl_cabinet_in the circuit card inside the cabinet door: NOTSTROM 12V, battery -> switch -> SCHRANKE / TOR / LICHT,
                 and in pen: KLEMMEN FEST!
  lbl_trafo      the transformer's rating plate (aluminium, engraved);  lbl_pole  the pole's enamel number plate (L4 / 17)
  l_red / l_green / l_amber  indicator domes (disc UVs): base = unlit glass, emission = lit
  l_beacon       the beacon dome, cylindrical UVs (u round, v up): orange fresnel ribs, the mirror at u 0.5 (bright band
                 when lit: turn the lens mesh to sweep it);  l_cam  the camera's front glass with the lens (no emission)
  l_flood        the mast floodlight's glass: prismatic ribs, the faceted reflector, the halogen tube (warm white lit)
  l_street       the mast street lamp's opal bowl from below (bluish white lit: mercury)
  glow_red / glow_green / glow_amber / glow_orange / glow_white  halo tiles (emission only, radial falloff)
Signs: German first, English under it (the project's rule); equipment labels as the spec gives them.
Screens (snowkit_spec.SCREEN, 128 x 96, own UV 0..1 on the screen object): T_Kit_Screen_Off - dark grey-green CRT glass,
a faint window reflection, dark corners; T_Kit_Screen_On - stand-in CCTV picture (night, monochrome green-grey: the road,
the barrier boom, the booth's corner, scanlines, noise, CAM 1, 23.10.26 02:40) for the previews; T_Kit_Screen_On_Gate - the
same for the gate camera (CAM 2: the closed sliding leaf with its barbed wire, the post, the wall, the floodlight's pool; 1.1,
the previews put it on the gate monitors); Unity shows its camera.
python3 snowkit_tex.py [out_dir]  ->  T_Kit_Panel_BaseColor.png, T_Kit_Panel_Emission.png, T_Kit_Screen_Off.png,
T_Kit_Screen_On.png, T_Kit_Screen_On_Gate.png, kit_panel_regions.json   (default out_dir: tex/snow_kit)"""
import os, sys, json, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pxfont as F
import van2_tex as VT
import snowkit_spec as S

# umlauts: the dots replace the top row of the glyph (as kpp_tex / yard_tex)
for _f, _src in ((F.F35, {'Ä': '#.#|.#.|#.#|###|#.#', 'Ö': '#.#|...|###|#.#|###', 'Ü': '#.#|...|#.#|#.#|###'}),
                 (F.F57, {'Ä': '.#.#.|.....|.###.|#...#|#####|#...#|#...#', 'Ö': '.#.#.|.....|.###.|#...#|#...#|#...#|.###.',
                          'Ü': '.#.#.|.....|#...#|#...#|#...#|#...#|.###.'})):
    for _k, _s in _src.items():
        _f['glyphs'][_k] = F._compile({'x': _s})['x']

N = S.PANEL_N
REG = {k: v[0] for k, v in S.PANEL.items()}
INK, WHITE, PAPER = (26, 24, 22), (236, 232, 220), (224, 218, 196)
RED, RED_D, YELLOW = (196, 36, 26), (130, 24, 18), (238, 190, 30)
ALU, ALU_D, ALU_L = (176, 178, 172), (112, 114, 110), (204, 206, 200)
BLUE_PEN, PENCIL = (40, 52, 120), (84, 80, 92)
GREY_T = (90, 86, 80)
BAYER = VT.BAYER


def uv(name, n=N):
    return VT.uv(REG[name], n)


# ---------------------------------------------------------------- helpers
def _plate(img, r, col, rim=None, t=1):
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, col)
    if rim is not None:
        F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, rim, t)


def _bevel(img, r, hi, lo):
    """1 px light top / left edge and dark bottom / right edge"""
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y0, hi)
    F.rect(img, x0, y0, x0, y1 - 1, hi)
    F.rect(img, x0, y1 - 1, x1 - 1, y1 - 1, lo)
    F.rect(img, x1 - 1, y0, x1 - 1, y1 - 1, lo)


def _age(img, r, seed, spots=18, amount=0.18, col=(120, 100, 70)):
    """foxing / rust spots and scratches: a few pixels pulled toward `col`"""
    x0, y0, x1, y1 = r
    rng = np.random.default_rng(seed)
    for _ in range(spots):
        fx, fy = rng.integers(x0 + 1, x1 - 1), rng.integers(y0 + 1, y1 - 1)
        img[fy, fx] = (img[fy, fx] * (1 - amount) + np.array(col) * amount).astype(np.uint8)


def _poly_mask(H, W, pts):
    """pixels whose centres lie inside the polygon pts [(x, y)] (pixel units)"""
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = xx + 0.5, yy + 0.5
    inside = np.zeros((H, W), bool)
    n = len(pts)
    for i in range(n):
        (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
        cond = (ya > py) != (yb > py)
        xint = xa + (py - ya) * (xb - xa) / np.where(yb - ya == 0, 1e-9, yb - ya)
        inside ^= cond & (px < xint)
    return inside


def fill_poly(img, pts, col):
    H, W = img.shape[:2]
    img[_poly_mask(H, W, pts)] = col


def bolt(img, cx, cy, h, col):
    """zigzag lightning arrow pointing down, height h centred at cx, cy (yard_tex's)"""
    pts = [(cx + 0.10 * h, cy - 0.50 * h), (cx - 0.16 * h, cy + 0.04 * h), (cx + 0.02 * h, cy + 0.02 * h),
           (cx - 0.12 * h, cy + 0.38 * h), (cx - 0.20 * h, cy + 0.30 * h), (cx - 0.12 * h, cy + 0.52 * h),
           (cx + 0.10 * h, cy + 0.28 * h), (cx + 0.02 * h, cy + 0.30 * h), (cx + 0.18 * h, cy - 0.08 * h),
           (cx + 0.00 * h, cy - 0.06 * h), (cx + 0.22 * h, cy - 0.50 * h)]
    fill_poly(img, pts, col)


def bolt_triangle(img, cx, cy, s):
    """W012 warning triangle: yellow, black border, the black lightning arrow (height s, width 1.12 s)"""
    h = s
    w = s * 1.12
    fill_poly(img, [(cx, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)], INK)
    k = max(2.0, s * 0.12)
    fill_poly(img, [(cx, cy - h / 2 + k * 1.6), (cx + w / 2 - k * 1.25, cy + h / 2 - k * 0.7),
                    (cx - w / 2 + k * 1.25, cy + h / 2 - k * 0.7)], YELLOW)
    bolt(img, cx, cy + h * 0.10, h * 0.56, INK)


def _radial(r, cx=None, cy=None):
    """pixel grid of region r and the normalised radius from its centre (1 = the half width)"""
    x0, y0, x1, y1 = r
    cx = (x0 + x1) / 2 if cx is None else cx
    cy = (y0 + y1) / 2 if cy is None else cy
    yy, xx = np.mgrid[y0:y1, x0:x1]
    rr = np.hypot(xx + 0.5 - cx, yy + 0.5 - cy) / ((x1 - x0) / 2)
    return yy, xx, rr


def _quant(v, levels, yy, xx):
    """ordered-dither a 0..1 field to `levels` steps (the panels' gradients)"""
    t = BAYER[np.mod(yy, 4), np.mod(xx, 4)]
    return np.clip(np.floor(v * levels + t) / levels, 0, 1)


# ---------------------------------------------------------------- console labels and strip
def _label(img, r, de, en, seed):
    """engraved black label (traffolyte): white letters cut into the black, a worn bevel, a few scratches"""
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (30, 30, 32))
    _bevel(img, r, (74, 74, 76), (12, 12, 13))
    F.rect(img, x0 + 1, y0 + 1, x1 - 2, y0 + 1, (44, 44, 46))
    cx = (x0 + x1) / 2
    if de:
        F.text(img, cx, y0 + 10, de, F.F57, (234, 234, 228))
    if en:
        F.text(img, cx, y0 + 20, en, F.F35, (172, 172, 166))
    _age(img, r, seed, 14, 0.35, (120, 120, 116))


def draw_console(img):
    _label(img, REG['btn_schranke'], 'SCHRANKE', 'BARRIER', 61)
    _label(img, REG['btn_tor'], 'TOR', 'GATE', 62)
    _label(img, REG['btn_licht'], 'LICHT', 'LIGHTS', 63)
    _label(img, REG['btn_blank'], '', '', 64)
    x0, y0, x1, y1 = REG['btn_blank']                       # a ghost of glue where an old label sat
    F.rect(img, x0 + 18, y0 + 8, x1 - 19, y0 + 9, (40, 40, 40))
    r = REG['lbl_console']                                  # anodised dark grey strip, two screws
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (46, 48, 52))
    _bevel(img, r, (86, 88, 92), (20, 20, 22))
    cx = (x0 + x1) / 2
    F.text(img, cx, y0 + 5, 'TORSTEUERUNG', F.F35, (228, 228, 222))
    F.text(img, cx, y0 + 11, 'GATE CONTROL', F.F35, (160, 162, 160))
    for sx in (x0 + 4, x1 - 5):
        F.disc(img, sx + 0.5, (y0 + y1) / 2, 1.6, (150, 152, 150))
        img[int((y0 + y1) / 2), int(sx)] = (60, 60, 62)


# ---------------------------------------------------------------- the power cabinet
def draw_cabinet(img):
    r = REG['sign_notstrom']                                # white enamel plate, black frame
    _plate(img, r, WHITE, INK)
    x0, y0, x1, y1 = r
    cx = (x0 + x1) / 2
    bolt_triangle(img, cx, y0 + 20, 30)
    F.text(img, cx, y0 + 44, 'NOTSTROM 12V', F.F57, INK)
    F.rect(img, x0 + 10, y0 + 51, x1 - 11, y0 + 51, (160, 156, 146))
    F.text(img, cx, y0 + 58, 'EMERGENCY 12V', F.F35, GREY_T)
    F.text(img, cx, y0 + 66, 'BATTERIE ANSCHLIESSEN', F.F35, RED_D)
    F.text(img, cx, y0 + 73, 'CONNECT BATTERY', F.F35, GREY_T)
    for sx in (x0 + 4, x1 - 5):
        for sy in (y0 + 4, y1 - 5):
            F.disc(img, sx + 0.5, sy + 0.5, 1.4, (150, 146, 138))
    _age(img, r, 71, 50, 0.28, (110, 90, 60))
    # the change-over switch plate: aluminium, engraved black
    r = REG['lbl_switch']
    x0, y0, x1, y1 = r
    _plate(img, r, ALU)
    _bevel(img, r, ALU_L, ALU_D)
    cx, cy = (x0 + x1) / 2, y0 + 38
    F.text(img, x0 + 14, y0 + 7, 'NETZ', F.F35, INK)
    F.text(img, x0 + 14, y0 + 14, 'MAINS', F.F35, (70, 70, 68))
    F.text(img, x1 - 19, y0 + 7, 'BATTERIE', F.F35, INK)
    F.text(img, x1 - 19, y0 + 14, 'BATTERY', F.F35, (70, 70, 68))
    F.ring(img, cx, cy, 19.0, 20.2, (40, 40, 40), -45, 45)          # the arc of the handle's travel
    for a in (-45, 45):
        F.tick(img, cx, cy, 14.5, 23.5, a, INK, 2)                  # the two position marks
    for a, s in ((-45, 1), (45, -1)):                               # little arrowheads at the arc's ends
        px_, py_ = F.pol(cx, cy, 19.6, a + s * 4)
        F.disc(img, px_, py_, 1.3, (40, 40, 40))
    F.disc(img, cx, cy, 8.0, (150, 152, 148))                      # the bezel the handle turns on
    F.ring(img, cx, cy, 7.0, 8.2, (90, 92, 88))
    F.disc(img, cx, cy, 3.6, (24, 24, 24))                         # the spindle hole
    F.text(img, cx, y1 - 6, 'S1', F.F35, (70, 70, 68))
    for sx in (x0 + 3, x1 - 4):
        for sy in (y0 + 3, y1 - 4):
            F.disc(img, sx + 0.5, sy + 0.5, 1.1, (120, 122, 118))
    _age(img, r, 72, 16, 0.3, (90, 90, 86))
    # the circuit card inside the door: printed frame and heading, the diagram drawn by hand
    r = REG['lbl_cabinet_in']
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, PAPER)
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, (150, 144, 128))
    F.text(img, x0 + 4, y0 + 3, 'NOTSTROM 12V', F.F35, INK, align='l', valign='t')
    F.rect(img, x0 + 3, y0 + 9, x1 - 4, y0 + 9, (150, 144, 128))
    by = y0 + 22                                                    # battery -> B; mains -> N; the blade feeds the bus
    F.rect(img, x0 + 8, by - 6, x0 + 8, by + 6, BLUE_PEN)           # the battery: long and short plates
    F.rect(img, x0 + 11, by - 3, x0 + 11, by + 3, BLUE_PEN)
    F.text(img, x0 + 6, by - 9, '+', F.F35, BLUE_PEN)
    F.text(img, x0 + 13, by - 9, '-', F.F35, BLUE_PEN)
    F.text(img, x0 + 10, by + 11, 'BATT', F.F35, BLUE_PEN)
    F.line(img, x0 + 12, by, x0 + 30, by, BLUE_PEN)
    F.disc(img, x0 + 31, by + 0.5, 1.1, BLUE_PEN)                  # contact B
    F.disc(img, x0 + 31, by + 8.5, 1.1, BLUE_PEN)                  # contact N
    F.text(img, x0 + 31, by - 5, 'B', F.F35, BLUE_PEN)
    F.line(img, x0 + 30, by + 8, x0 + 27, by + 8, BLUE_PEN)         # the mains lead, down to NETZ
    F.line(img, x0 + 27, by + 8, x0 + 27, by + 10, BLUE_PEN)
    F.text(img, x0 + 28, by + 14, 'NETZ', F.F35, BLUE_PEN)
    F.disc(img, x0 + 40, by + 4.5, 1.1, BLUE_PEN)                  # the blade's pivot, thrown to B
    F.line(img, x0 + 40, by + 4, x0 + 32, by + 0.5, BLUE_PEN)
    F.line(img, x0 + 41, by + 4, x0 + 50, by + 4, BLUE_PEN)
    F.line(img, x0 + 50, y0 + 15, x0 + 50, y0 + 31, BLUE_PEN)       # the bus and three fused outputs
    for i, lab in enumerate(('SCHRANKE', 'TOR', 'LICHT')):
        yy = y0 + 13 + i * 8
        F.line(img, x0 + 50, yy + 2, x0 + 56, yy + 2, BLUE_PEN)
        F.rect(img, x0 + 56, yy + 1, x0 + 58, yy + 3, BLUE_PEN)
        F.text(img, x0 + 61, yy, lab, F.F35, INK, align='l', valign='t')
    F.text(img, x0 + 4, y1 - 8, 'KLEMMEN FEST!', F.F35, RED_D, align='l', valign='t')
    F.line(img, x0 + 4, y1 - 2, x0 + 58, y1 - 2, RED_D)
    _age(img, r, 73, 30, 0.22)


# ---------------------------------------------------------------- warning signs
def draw_signs(img):
    r = REG['sign_volt']                                    # the triangle on a white label (the sticker's backing)
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (232, 228, 214))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (176, 172, 160))
    bolt_triangle(img, (x0 + x1) / 2, (y0 + y1) / 2 + 0.5, 36)
    _age(img, r, 81, 12, 0.25)
    r = REG['sign_danger']                                  # white enamel: the red arrow, LEBENS- / GEFAHR, DANGER
    _plate(img, r, WHITE, INK)
    x0, y0, x1, y1 = r
    cx = (x0 + x1) / 2
    bolt(img, cx, y0 + 25, 34, RED)
    F.text(img, cx, y0 + 52, 'LEBENS-', F.F57, INK)
    F.text(img, cx, y0 + 61, 'GEFAHR', F.F57, INK)
    F.rect(img, x0 + 8, y0 + 67, x1 - 9, y0 + 67, (160, 156, 146))
    F.text(img, cx, y0 + 73, 'DANGER', F.F35, RED_D)
    for sx in (x0 + 4, x1 - 5):
        for sy in (y0 + 4, y1 - 5):
            F.disc(img, sx + 0.5, sy + 0.5, 1.4, (150, 146, 138))
    _age(img, r, 82, 60, 0.3, (110, 80, 50))
    r = REG['lbl_pole']                                     # blue enamel number plate, white rim and figures
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (36, 62, 136))
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, (226, 228, 230))
    cx = (x0 + x1) / 2
    F.text(img, cx, y0 + 7, 'L4', F.F35, (226, 228, 230))
    F.text(img, cx, y0 + 20, '17', F.F57, (236, 238, 240), scale=2)
    for sx, sy in ((x0 + 3, y0 + 3), (x1 - 4, y1 - 4), (x0 + 3, y1 - 4), (x1 - 4, y0 + 3)):
        img[sy, sx] = (20, 30, 60)
    _age(img, r, 83, 14, 0.4, (40, 36, 34))
    r = REG['lbl_trafo']                                    # aluminium rating plate, engraved
    _plate(img, r, ALU, ALU_D)
    x0, y0, x1, y1 = r
    cx = (x0 + x1) / 2
    for i, t in enumerate(('TRANSFORMATOR', '20000 / 400 V', '50 KVA   50 HZ', 'DYN5   UK 4%', 'NR 21877  1974')):
        F.text(img, cx, y0 + 4.5 + i * 6, t, F.F35, (40, 40, 38))
    _age(img, r, 84, 16, 0.3, (80, 70, 60))


# ---------------------------------------------------------------- phone dial, monitor strip
def draw_devices(img):
    r = REG['phone_dial']
    x0, y0, x1, y1 = r
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (176, 84, 36))              # the body round the dial (orange, in shade)
    F.disc(img, cx, cy, 23.6, (58, 54, 50))                          # the wheel's shadowed edge
    F.disc(img, cx, cy, 22.6, (188, 182, 164))                       # the clear finger wheel over the cream ring
    F.ring(img, cx, cy, 21.6, 22.6, (232, 230, 220))                 # its polished rim
    holes = {}
    for d in range(1, 11):
        a = 60 - (d - 1) * 30
        hx, hy = F.pol(cx, cy, 16.6, a)
        holes[d % 10] = (hx, hy)
        F.disc(img, hx, hy, 4.2, (96, 92, 84))                       # the hole's wall
        F.disc(img, hx, hy, 3.5, (236, 232, 216))                    # the number ring seen through it
        F.text(img, hx, hy, str(d % 10), F.F35, INK)
    F.disc(img, cx, cy, 9.6, (150, 146, 134))                        # the centre label's rim
    F.disc(img, cx, cy, 8.6, (240, 238, 228))                        # the paper label
    F.rect(img, cx - 5, cy - 2, cx + 4, cy - 2, (120, 30, 26))
    F.text(img, cx, cy + 2.5, '130', F.F35, (40, 40, 60))
    sx0, sy0 = F.pol(cx, cy, 23.2, 112)                              # the finger stop (chrome hook at 4 o'clock)
    sx1, sy1 = F.pol(cx, cy, 15.0, 108)
    F.line(img, sx0, sy0, sx1, sy1, (214, 214, 210), 2)
    F.line(img, sx0 + 1, sy0, sx1 + 1, sy1, (120, 120, 116))
    r = REG['lbl_monitor']                                  # the lower bezel strip (dark grey, as the bezel)
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (70, 70, 72))
    F.rect(img, x0, y0, x1 - 1, y0, (88, 88, 90))
    F.rect(img, x0, y1 - 1, x1 - 1, y1 - 1, (50, 50, 52))
    F.text(img, x0 + 3, y0 + 2, 'CCTV', F.F35, (210, 210, 204), align='l', valign='t')
    F.text(img, x0 + 3, y0 + 9, 'MONITOR', F.F35, (150, 150, 146), align='l', valign='t')
    for u, lab in MON_KNOBS:
        kx = x0 + u * (x1 - x0)
        F.text(img, kx, y0 + 4.5, lab, F.F35, (196, 196, 190))
        F.rect(img, kx - 1, y0 + 9, kx, y0 + 10, (150, 150, 146))   # a little index under each label


# ---------------------------------------------------------------- lenses and glows
MON_KNOBS = ((0.410, 'CONTRAST'), (0.676, 'BRIGHT'), (0.895, 'POWER'))     # u of the knob centres on the strip
LENS_COL = {'l_red': ((116, 22, 18), (255, 72, 52)), 'l_green': ((22, 88, 40), (96, 255, 124)),
            'l_amber': ((132, 80, 12), (255, 184, 48))}
GLOW_COL = {'glow_red': (255, 64, 44), 'glow_green': (84, 255, 112), 'glow_amber': (255, 172, 52),
            'glow_orange': (255, 130, 30), 'glow_white': (255, 238, 204)}


def draw_lenses(img, emi):
    for key, (cb, ce) in LENS_COL.items():                  # domed indicator lens: the disc fills the tile
        r = REG[key]
        yy, xx, rr = _radial(r)
        x0, y0, x1, y1 = r
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        # unlit: coloured glass, darker toward the rim, a soft window highlight up-left (posterised, no dither)
        hl = np.hypot(xx + 0.5 - (cx - 5), yy + 0.5 - (cy - 5)) / 7.0
        b = 0.62 + 0.38 * (1 - rr ** 2) + 0.55 * np.clip(1 - hl, 0, 1) ** 2
        q = np.floor(np.clip(b / 1.5, 0, 1) * 5) / 5
        base = np.clip(np.array(cb)[None, None] * (0.40 + 1.05 * q[..., None]), 0, 255)
        spec = np.hypot(xx + 0.5 - (cx - 5), yy + 0.5 - (cy - 6)) < 1.6
        base[spec] = (236, 232, 226)
        img[y0:y1, x0:x1] = base.astype(np.uint8)
        # lit: a hot core, the coloured dome round it, the rim a little darker
        e = np.clip(1.0 - 0.55 * rr ** 1.5, 0, 1)
        q = _quant(e, 7, yy, xx)
        ec = np.array(ce, np.float64)[None, None] * q[..., None]
        core = rr < 0.32
        ec[core] = np.minimum(255, np.array(ce) * 0.85 + np.array((60, 60, 40)))
        emi[y0:y1, x0:x1] = np.clip(ec, 0, 255).astype(np.uint8)
    # the beacon dome: u round (x), v up (y: the top row = the dome's top)
    r = REG['l_beacon']
    x0, y0, x1, y1 = r
    W, H = x1 - x0, y1 - y0
    yy, xx = np.mgrid[0:H, 0:W]
    u = (xx + 0.5) / W
    v = 1.0 - (yy + 0.5) / H                                          # 0 at the rim, 1 at the top
    rib = np.where(np.mod(xx, 2) == 0, 1.0, 0.76)                      # fresnel ribs, 2 px
    rib = np.where(v > 0.80, 1.0, rib)                                 # the smooth crown
    mirror = np.clip(1 - np.abs(u - 0.5) / 0.14, 0, 1) * ss_np(0.16, 0.30, v) * ss_np(0.86, 0.70, v)
    bulb = np.exp(-(((u - 0.5) / 0.05) ** 2 + ((v - 0.50) / 0.08) ** 2))
    crown = ss_np(0.72, 1.0, v)
    b = 0.62 * rib + 0.30 * mirror + 0.22 * crown
    q = _quant(np.clip(b, 0, 1), 7, yy + y0, xx + x0)
    base = np.array((176, 84, 22), np.float64)[None, None] * (0.55 + 0.75 * q[..., None])
    base = base + np.array((40, 40, 40))[None, None] * mirror[..., None] * 0.8
    base[v < 0.06] = (58, 30, 12)                                     # the rim on the base
    img[y0:y1, x0:x1] = np.clip(base, 0, 255).astype(np.uint8)
    e = 0.34 * rib + 0.66 * mirror + 0.9 * bulb + 0.10 * crown
    q = _quant(np.clip(e, 0, 1), 8, yy + y0, xx + x0)
    ec = np.array((255, 128, 26), np.float64)[None, None] * q[..., None]
    hot = (mirror > 0.55) | (bulb > 0.45)
    ec[hot] = np.minimum(255, ec[hot] * 0.6 + np.array((120, 110, 70)))
    ec[v < 0.06] = 0
    emi[y0:y1, x0:x1] = np.clip(ec, 0, 255).astype(np.uint8)
    # the camera's front glass: dark glass, the lens barrel, the iris, a reflection arc and a glint
    r = REG['l_cam']
    yy, xx, rr = _radial(r)
    x0, y0, x1, y1 = r
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    g = np.zeros(rr.shape + (3,))
    g[:] = (22, 24, 26)
    g[rr < 0.78] = (46, 48, 52)                                       # the lens barrel's front ring
    g[rr < 0.66] = (14, 14, 16)
    g[rr < 0.36] = (30, 26, 44)                                       # the coated front element
    g[rr < 0.16] = (8, 8, 10)
    ang = np.degrees(np.arctan2(xx + 0.5 - cx, -(yy + 0.5 - cy))) % 360
    arc = (rr > 0.40) & (rr < 0.56) & (ang > 280) & (ang < 340)
    g[arc] = (84, 72, 124)
    g[(np.hypot(xx + 0.5 - (cx - 3), yy + 0.5 - (cy - 4)) < 1.2)] = (226, 226, 236)
    g[(np.abs(xx + 0.5 - (x1 - 6)) < 4) & (np.abs(yy + 0.5 - (y0 + 5)) < 1)] = (60, 64, 70)   # the window seen in the glass
    img[y0:y1, x0:x1] = g.astype(np.uint8)
    emi[y0:y1, x0:x1] = 0
    # the floodlight's glass: prismatic ribs across, the faceted reflector fanning out from the halogen tube in the middle
    r = REG['l_flood']
    x0, y0, x1, y1 = r
    W, H = x1 - x0, y1 - y0
    yy, xx = np.mgrid[y0:y1, x0:x1]
    u, v = (xx - x0 + 0.5) / W, (yy - y0 + 0.5) / H
    du, dv = u - 0.5, (v - 0.5) * H / W
    rr = np.hypot(du, dv * 1.6)
    fan = 0.5 + 0.5 * np.cos(np.arctan2(dv, du) * 8)
    rib = np.where(np.mod(yy - y0, 3) == 0, 0.78, 1.0)
    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    b = (0.50 + 0.30 * fan * (1 - np.clip(rr / 0.6, 0, 1)) + 0.2 * (1 - np.clip(rr / 0.35, 0, 1))) * rib * (0.62 + 0.38 * ss_np(0.0, 0.12, edge))
    tube = (np.abs(v - 0.5) < 1.1 / H) & (np.abs(u - 0.5) < 0.34)
    q = _quant(np.clip(b, 0, 1), 6, yy, xx)
    base = np.array((142, 148, 152), np.float64)[None, None] * (0.45 + 0.75 * q[..., None])
    base[tube] = (224, 220, 196)
    for ex in (0.16, 0.84):                                          # the tube's end caps
        base[(np.abs(v - 0.5) < 2.2 / H) & (np.abs(u - ex) < 1.1 / W)] = (70, 66, 60)
    img[y0:y1, x0:x1] = np.clip(base, 0, 255).astype(np.uint8)
    e = np.exp(-((v - 0.5) / 0.22) ** 2) * (0.55 + 0.45 * (1 - np.clip(np.abs(u - 0.5) * 1.8, 0, 1))) + \
        0.30 * fan * (1 - np.clip(rr / 0.7, 0, 1)) + 0.12
    q = _quant(np.clip(e * rib, 0, 1), 8, yy, xx)
    ec = np.array((255, 236, 196), np.float64)[None, None] * q[..., None]
    ec[tube] = (255, 252, 236)
    emi[y0:y1, x0:x1] = np.clip(ec, 0, 255).astype(np.uint8)
    # the street lamp's opal bowl from below: milky, a darker rim, the lamp a soft blob in the middle (bluish when lit)
    r = REG['l_street']
    x0, y0, x1, y1 = r
    W, H = x1 - x0, y1 - y0
    yy, xx = np.mgrid[y0:y1, x0:x1]
    u, v = (xx - x0 + 0.5) / W, (yy - y0 + 0.5) / H
    edge = np.minimum(np.minimum(u, 1 - u) * W / H, np.minimum(v, 1 - v))
    blob = np.exp(-(((u - 0.5) / 0.16) ** 2 + ((v - 0.5) / 0.30) ** 2))
    b = 0.55 + 0.25 * ss_np(0.0, 0.25, edge) + 0.15 * blob
    q = _quant(np.clip(b, 0, 1), 6, yy, xx)
    base = np.array((196, 198, 192), np.float64)[None, None] * (0.40 + 0.70 * q[..., None])
    base[edge < 1.2 / H] = (90, 92, 92)                              # the frame's lip
    img[y0:y1, x0:x1] = np.clip(base, 0, 255).astype(np.uint8)
    e = 0.30 + 0.45 * ss_np(0.0, 0.30, edge) + 0.55 * blob
    q = _quant(np.clip(e, 0, 1), 8, yy, xx)
    ec = np.array((214, 236, 255), np.float64)[None, None] * q[..., None]
    ec[blob > 0.65] = (246, 252, 255)
    ec[edge < 1.2 / H] = 0
    emi[y0:y1, x0:x1] = np.clip(ec, 0, 255).astype(np.uint8)
    for key, col in GLOW_COL.items():                       # halo tiles: emission only
        r = REG[key]
        yy, xx, rr = _radial(r)
        x0, y0, x1, y1 = r
        gg = np.clip(1 - rr, 0, 1) ** 1.6
        gg = _quant(gg, 10, yy, xx)
        gg[rr > 0.97] = 0
        emi[y0:y1, x0:x1] = (gg[..., None] * np.array(col)[None, None]).astype(np.uint8)
        img[y0:y1, x0:x1] = 0


def ss_np(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- screens (own UV 0..1)
def screen_off(path):
    W, H = S.SCREEN['size']
    yy, xx = np.mgrid[0:H, 0:W]
    u, v = (xx + 0.5) / W, (yy + 0.5) / H
    vig = 1 - 0.80 * (((u - 0.5) * 1.15) ** 2 + ((v - 0.5) * 1.15) ** 2) * 1.6
    vig = np.clip(vig, 0.25, 1)
    refl = ((u > 0.58) & (u < 0.86) & (v > 0.08) & (v < 0.46) & (u - 0.58 > (v - 0.08) * 0.12))
    refl &= ~((np.abs(u - 0.72) < 0.008) | (np.abs(v - 0.27) < 0.012))    # the window's cross bars
    band = np.exp(-((v - 0.07) / 0.035) ** 2) * (1 - np.abs(u - 0.5) * 1.6).clip(0, 1)   # the glass's curve catching light
    b = 0.40 * vig + 0.16 * refl + 0.18 * band
    q = _quant(np.clip(b, 0, 1), 9, yy, xx)
    col = np.stack([16 + 46 * q, 22 + 54 * q, 20 + 50 * q], -1)
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8), 'RGB').save(path)
    return path


def screen_on(path):
    """the stand-in picture: night, the KPP camera under the eave looking at the barrier"""
    W, H = S.SCREEN['size']
    rng = np.random.default_rng(91)
    yy, xx = np.mgrid[0:H, 0:W]
    u, v = (xx + 0.5) / W, (yy + 0.5) / H
    hor = 38
    pic = np.zeros((H, W))
    pic[:hor] = 0.12 + 0.09 * (yy[:hor] / hor)                          # sky, a little lighter at the horizon
    pic[hor:] = 0.20 + 0.08 * ((yy[hor:] - hor) / (H - hor))             # the ground
    vx = 78                                                             # the road's vanishing point
    half = 1.5 + (yy - hor) * 0.95
    centre = vx - (yy - hor) * 0.55
    road = (yy >= hor) & (np.abs(xx + 0.5 - centre) < half)
    pic[road] = 0.30 + 0.10 * ((yy[road] - hor) / (H - hor))
    edge = (yy >= hor) & (np.abs(np.abs(xx + 0.5 - centre) - half) < 0.8)
    pic[edge] = 0.42
    for k in range(0, W, 2):                                            # the forest edge: jagged spruce tops
        h = int(5 + rng.integers(0, 12) + 4 * math.sin(k * 0.21))
        pic[max(0, hor - h):hor + 2, k:k + 2] = 0.05 + 0.03 * rng.random()
    for k in range(0, W, 7):                                            # a few spruce spires above the edge
        h = int(14 + rng.integers(0, 10))
        for j in range(h):
            w = max(0, int((j / h) * 3))
            pic[hor - h + j, max(0, k - w):k + w + 1] = 0.04
    lamp = np.exp(-(((xx - 104) / 26.0) ** 2 + ((yy - 70) / 16.0) ** 2))   # the booth's lamp lights the ground
    pic = pic + 0.30 * lamp * (yy > hor)
    by = 60                                                              # the barrier: cabinet, striped boom, rest post
    pic[by - 12:by + 14, 30:36] = 0.58
    pic[by - 14:by - 11, 29:37] = 0.30
    pic[by - 17:by - 14, 31:35] = 0.75                                   # the beacon on the cabinet
    for k in range(36, 96):
        seg = ((k - 36) // 6) % 2
        pic[by - 1:by + 2, k] = 0.86 if seg == 0 else 0.40
    pic[by + 1:by + 13, 95:97] = 0.55
    pic[by + 12:by + 15, 92:100] = 0.48
    pic[by + 13:by + 16, 26:40] = 0.45                                   # the cabinet's pad
    wall = xx >= 112                                                     # the booth's corner on the right
    pic[wall] = 0.34 + 0.05 * ((yy[wall]) / H)
    pic[(xx >= 112) & (xx < 114)] = 0.52                                 # the white corner board
    win = (xx >= 117) & (yy > 18) & (yy < 44)
    pic[win] = 0.66                                                      # a lit window
    pic[(xx >= 117) & (np.abs(yy - 31) < 1)] = 0.40
    pic[(xx >= 104) & (xx < 128) & (yy < 9)] = 0.18                      # the eave
    pic = pic + rng.normal(0, 0.035, pic.shape)
    roll = np.exp(-((yy - 74) / 3.0) ** 2) * 0.06                        # a slow sync roll band
    scan = np.where(yy % 2 == 0, 1.0, 0.78)
    vig = np.clip(1 - 0.55 * (((u - 0.5) * 1.1) ** 2 + ((v - 0.5) * 1.1) ** 2) * 1.8, 0.3, 1)
    pic = np.clip((pic + roll) * scan * vig, 0, 1)
    q = _quant(pic, 14, yy, xx)
    col = np.stack([q * 176 + 6, q * 226 + 8, q * 194 + 6], -1)
    col = np.clip(col, 0, 255).astype(np.uint8)
    txt = (226, 246, 228)
    F.text(col, 4, 4, 'CAM 1', F.F57, txt, align='l', valign='t')
    F.text(col, W - 4, H - 10, '23.10.26 02:40', F.F35, txt, align='r', valign='t')
    Image.fromarray(col, 'RGB').save(path)
    return path


def cctv(pic, yy, xx, u, v, rng, label, path):
    """the stand-in pictures' camera look: noise, a sync roll band, scanlines, vignette, 14 levels, green-grey, the caption"""
    H, W = pic.shape
    pic = pic + rng.normal(0, 0.035, pic.shape)
    roll = np.exp(-((yy - 74) / 3.0) ** 2) * 0.06
    scan = np.where(yy % 2 == 0, 1.0, 0.78)
    vig = np.clip(1 - 0.55 * (((u - 0.5) * 1.1) ** 2 + ((v - 0.5) * 1.1) ** 2) * 1.8, 0.3, 1)
    pic = np.clip((pic + roll) * scan * vig, 0, 1)
    q = _quant(pic, 14, yy, xx)
    col = np.stack([q * 176 + 6, q * 226 + 8, q * 194 + 6], -1)
    col = np.clip(col, 0, 255).astype(np.uint8)
    txt = (226, 246, 228)
    F.text(col, 4, 4, label, F.F57, txt, align='l', valign='t')
    F.text(col, W - 4, H - 10, '23.10.26 02:40', F.F35, txt, align='r', valign='t')
    Image.fromarray(col, 'RGB').save(path)
    return path


def screen_on_gate(path):
    """the gate camera's stand-in (1.1): night, from the mast west of the opening, looking down along the closed sliding
    leaf: the yard lit by the floodlight on the left, the leaf with its stiffeners and barbed wire across the picture, the
    street side dark beyond it, the wall going on at the top right, the concrete post at the bottom left"""
    W, H = S.SCREEN['size']
    rng = np.random.default_rng(92)
    yy, xx = np.mgrid[0:H, 0:W]
    u, v = (xx + 0.5) / W, (yy + 0.5) / H
    pic = 0.17 + 0.05 * (yy / H)                                         # the yard's ground
    for _ in range(26):                                                  # dry grass tufts
        cx, cy = rng.integers(2, 70), rng.integers(4, 90)
        pic[cy:cy + 3, cx:cx + 4] -= 0.06 + 0.04 * rng.random()
    x0, x1 = 44.0, 124.0                                                 # the leaf: near end (bottom) to far end (top right)
    def lerp(a, b, x):
        return a + (b - a) * np.clip((x - x0) / (x1 - x0), 0, 1)
    bot = lerp(97.0, 30.0, xx + 0.5)                                     # its foot on the rail
    top = lerp(66.0, 15.0, xx + 0.5)                                     # its top rail
    beyond = (xx >= x0) & (yy < top) & (yy < bot)                        # above the leaf: the street side, unlit
    pic[beyond] = 0.10 + 0.03 * (yy[beyond] / H)
    leaf = (xx >= x0) & (xx <= x1) & (yy >= top) & (yy <= bot)
    pic[leaf] = 0.27 + 0.06 * ((xx[leaf] - x0) / (x1 - x0))
    t = 0.0                                                              # stiffeners: closer together toward the far end
    while True:
        xs = x0 + 3 + t
        if xs > x1 - 2:
            break
        st = (np.abs(xx + 0.5 - xs) < 1.0) & leaf
        pic[st] = 0.44
        t += max(3.0, 11.0 - 0.09 * t)
    rail = (xx >= x0) & (xx <= x1) & (np.abs(yy + 0.5 - top) < 1.2)
    pic[rail] = 0.56
    foot = (xx >= x0) & (xx <= x1) & (np.abs(yy + 0.5 - bot) < 1.0)
    pic[foot] = 0.36
    for k, off in enumerate((3.5, 6.5, 9.5)):                            # barbed wire: three strands, dotted
        wire = (xx >= x0) & (xx <= x1) & (np.abs(yy + 0.5 - (top - off * lerp(1.0, 0.55, xx + 0.5))) < 0.6) & ((xx + k) % 3 != 0)
        pic[wire] = 0.66
    t = 0.0
    while True:                                                          # the wire's little posts
        xs = x0 + 2 + t
        if xs > x1 - 1:
            break
        ytop = float(lerp(66.0, 15.0, xs)) - 10.5 * float(lerp(1.0, 0.55, xs))
        ylow = float(lerp(66.0, 15.0, xs))
        pm = (np.abs(xx + 0.5 - xs) < 0.6) & (yy >= ytop) & (yy <= ylow)
        pic[pm] = 0.58
        t += max(4.0, 14.0 - 0.1 * t)
    wall = (xx >= 112) & (yy < lerp(66.0, 15.0, 112.0) - 1)              # the wall going on beyond the leaf's far end
    pic[wall] = 0.40 + 0.04 * ((yy[wall]) / 20.0)
    pic[(xx >= 112) & ((xx - 112) % 7 == 0) & (yy < 14)] = 0.30          # its panel joints
    lamp = np.exp(-(((xx - 30) / 30.0) ** 2 + ((yy - 64) / 22.0) ** 2))  # the floodlight's pool on the yard side
    yard = ~((xx >= x0) & (yy < bot))
    pic = pic + 0.34 * lamp * yard + 0.12 * lamp * leaf
    post = (xx >= 28) & (xx < 44) & (yy >= 58)                           # the concrete post at the near end
    pic[post] = 0.60 + 0.06 * ((xx[post] - 28) / 16.0)
    pic[(xx >= 26) & (xx < 46) & (yy >= 54) & (yy < 59)] = 0.76          # its cap
    pic[(xx >= 36) & (xx < 44) & (yy >= 58)] -= 0.10                     # its shaded side
    box = (xx >= 6) & (xx < 22) & (yy >= 80) & (yy < 92)                 # the drive's housing on its plinth
    pic[box] = 0.48
    pic[(xx >= 4) & (xx < 24) & (yy >= 91) & (yy < 94)] = 0.36
    return cctv(pic, yy, xx, u, v, rng, 'CAM 2', path)


# ---------------------------------------------------------------- build
def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (16, 16, 16)
    emi = np.zeros_like(img)
    draw_console(img)
    draw_cabinet(img)
    draw_signs(img)
    draw_devices(img)
    draw_lenses(img, emi)
    for name, (rect, size, _) in S.PANEL.items():                # every region drawn, aspect kept within half a pixel
        x0, y0, x1, y1 = rect
        assert abs((x1 - x0) / (y1 - y0) - size[0] / size[1]) * (y1 - y0) < 0.6 or name.startswith('glow') or \
            name == 'l_beacon', (name, rect, size)
    pb, pe = os.path.join(out, 'T_Kit_Panel_BaseColor.png'), os.path.join(out, 'T_Kit_Panel_Emission.png')
    Image.fromarray(img).save(pb)
    Image.fromarray(emi).save(pe)
    so = screen_off(os.path.join(out, S.SCREEN['off'] + '.png'))
    sn = screen_on(os.path.join(out, S.SCREEN['on'] + '.png'))
    sg = screen_on_gate(os.path.join(out, S.SCREEN['on_gate'] + '.png'))
    json.dump(dict(size=N, regions={k: dict(rect=list(v[0]), size_m=list(v[1]), note=v[2]) for k, v in S.PANEL.items()},
                   screens=dict(size=list(S.SCREEN['size']), off=S.SCREEN['off'] + '.png', on=S.SCREEN['on'] + '.png',
                                on_gate=S.SCREEN['on_gate'] + '.png', note=S.SCREEN['note']),
                   notes=dict(lbl_switch='NETZ mark at -45 deg (10:30), BATTERIE at +45 deg (1:30) from 12 o\'clock about '
                                         'the plate point (0.5, 38/64 from the top); the handle turns 90 clockwise',
                              lbl_monitor='knob centres at u 0.410 (CONTRAST), 0.676 (BRIGHT), 0.895 (POWER) of the strip, label row v 0.72, '
                                          'index marks v 0.38',
                              phone_dial='holes at radius 16.6 / 24 of the half width, digit d at 60 - (d - 1) * 30 deg '
                                         'clockwise from 12 o\'clock (1 at 2 o\'clock, 0 at 5 o\'clock); the stop at ~110 deg',
                              l_beacon='cylindrical: u round the dome, v up from the rim; the mirror band at u 0.5')),
              open(os.path.join(out, 'kit_panel_regions.json'), 'w'), indent=1)
    return dict(base=pb, emi=pe, screen_off=so, screen_on=sn, screen_on_gate=sg)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'snow_kit')
    print(build(out))
