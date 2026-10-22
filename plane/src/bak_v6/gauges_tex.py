"""Draw the instrument atlas T_Gauges (4096x2048). 8x4 grid of 512 px cells (rows 0-2 = dials/radios),
row 3 top strip = switch labels. Angles are degrees clockwise from 12 o'clock as the pilot sees the dial."""
import math, os, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as LY

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'tex', 'v2')
os.makedirs(OUT, exist_ok=True)
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FC = '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
FM = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
S = 1024                     # supersampled cell size
W_ATLAS, H_ATLAS, CELL = 4096, 2048, 512
WHITE, BLACK, FACE = (236, 236, 230), (0, 0, 0), (14, 14, 14)
GREEN, YELLOW, RED, BLUE_W = (40, 190, 70), (235, 200, 30), (220, 40, 30), (230, 230, 230)
ORANGE = (240, 130, 20)


def font(path, size):
    return ImageFont.truetype(path, int(size))


def pol(c, r, a):
    return (c[0] + r * math.sin(math.radians(a)), c[1] - r * math.cos(math.radians(a)))


def new_cell(bg=FACE, circle=True):
    im = Image.new('RGB', (S, S), (6, 6, 6))
    d = ImageDraw.Draw(im)
    if circle:
        d.ellipse((0, 0, S - 1, S - 1), fill=bg)
    else:
        d.rectangle((0, 0, S, S), fill=bg)
    return im, d


def text_c(d, xy, s, f, fill=WHITE, angle=None):
    bb = d.textbbox((0, 0), s, font=f)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text((xy[0] - w / 2 - bb[0], xy[1] - h / 2 - bb[1]), s, font=f, fill=fill)


def arc(d, c, r, a0, a1, width, fill):
    # PIL arc angles: 0 = 3 o'clock, clockwise. ours: 0 = 12 o'clock, clockwise -> subtract 90
    d.arc((c[0] - r, c[1] - r, c[0] + r, c[1] + r), a0 - 90, a1 - 90, fill=fill, width=int(width))


def tick(d, c, r0, r1, a, w, fill=WHITE):
    d.line([pol(c, r0, a), pol(c, r1, a)], fill=fill, width=int(w))


def dial(vmin, vmax, a0, a1, majors, minors, labels, arcs=(), redlines=(), title='', sub='', lab_r=0.62,
         lab_size=0.11, title_y=0.30, sub_y=0.72, fmt=None):
    im, d = new_cell()
    c = (S / 2, S / 2)
    R = S / 2 * 0.96
    ang = lambda v: a0 + (v - vmin) / (vmax - vmin) * (a1 - a0)
    for a in arcs:
        v0, v1, col = a[:3]
        rr = a[3] if len(a) > 3 else 0.90
        arc(d, c, R * rr, ang(v0), ang(v1), S * 0.035, col)
    for v in minors:
        tick(d, c, R * 0.86, R * 0.94, ang(v), S * 0.008)
    for v in majors:
        tick(d, c, R * 0.78, R * 0.94, ang(v), S * 0.014)
    for v in redlines:
        tick(d, c, R * 0.74, R * 0.96, ang(v), S * 0.02, RED)
    f = font(FB, S * lab_size)
    for v, s in labels:
        text_c(d, pol(c, R * lab_r, ang(v)), s, f)
    if title:
        text_c(d, (S / 2, S * title_y), title, font(FC, S * 0.075))
    if sub:
        text_c(d, (S / 2, S * sub_y), sub, font(FC, S * 0.06), (200, 200, 190))
    return im


def rng(a, b, st):
    out, v = [], a
    while v <= b + 1e-9:
        out.append(round(v, 6))
        v += st
    return out


def cell_asi():
    return dial(0, 200, 10, 330, rng(20, 200, 20), rng(40, 200, 5),
                [(v, str(v)) for v in range(40, 201, 20)],
                arcs=[(45, 110, BLUE_W, 0.83), (60, 150, GREEN), (150, 175, YELLOW)], redlines=[175],
                title='AIRSPEED', sub='KNOTS', lab_r=0.64, lab_size=0.095, title_y=0.42, sub_y=0.58)


def cell_alt():
    im = dial(0, 10, 0, 360, rng(0, 9, 1), rng(0, 9.8, 0.2), [(v, str(v)) for v in range(10)],
              title='ALT', sub='100 FEET', title_y=0.33, sub_y=0.68)
    d = ImageDraw.Draw(im)
    x0, y0 = S * 0.60, S * 0.46
    d.rectangle((x0, y0, x0 + S * 0.2, y0 + S * 0.08), fill=(30, 30, 30), outline=WHITE, width=3)
    text_c(d, (x0 + S * 0.1, y0 + S * 0.04), '29.92', font(FM, S * 0.055))
    return im


def cell_vsi():
    ang = lambda v: -90 + v / 2000 * 165
    im, d = new_cell()
    c, R = (S / 2, S / 2), S / 2 * 0.96
    for v in range(-2000, 2001, 100):
        tick(d, c, R * (0.78 if v % 500 == 0 else 0.87), R * 0.94, ang(v), S * (0.014 if v % 500 == 0 else 0.008))
    f = font(FB, S * 0.10)
    text_c(d, pol(c, R * 0.64, ang(0)), '0', f)
    for v in (500, 1000, 1500):
        text_c(d, pol(c, R * 0.64, ang(v)), str(v // 100), f)
        text_c(d, pol(c, R * 0.64, ang(-v)), str(v // 100), f)
    text_c(d, pol(c, R * 0.64, 90), '20', f)
    text_c(d, (S * 0.30, S * 0.36), 'UP', font(FC, S * 0.065))
    text_c(d, (S * 0.30, S * 0.64), 'DN', font(FC, S * 0.065))
    text_c(d, (S * 0.54, S * 0.40), 'VERTICAL SPEED', font(FC, S * 0.042))
    text_c(d, (S * 0.54, S * 0.60), '100 FT/MIN', font(FC, S * 0.042))
    return im


def cell_tc():
    im, d = new_cell()
    c, R = (S / 2, S / 2), S / 2 * 0.96
    for a in (-90, 90, -110, 110):     # wings-level and standard-rate marks
        tick(d, c, R * 0.72, R * 0.93, a, S * 0.02)
    text_c(d, pol(c, R * 0.62, -125), 'L', font(FB, S * 0.1))
    text_c(d, pol(c, R * 0.62, 125), 'R', font(FB, S * 0.1))
    text_c(d, (S / 2, S * 0.22), 'TURN COORDINATOR', font(FC, S * 0.05))
    text_c(d, (S / 2, S * 0.30), '2 MIN', font(FC, S * 0.055))
    text_c(d, (S / 2, S * 0.88), 'NO PITCH INFORMATION', font(FC, S * 0.035), (190, 190, 180))
    # inclinometer tube (ball is a separate part)
    cc, rr = (S / 2, S * 0.12), S * 0.62
    d.arc((cc[0] - rr, cc[1] - rr, cc[0] + rr, cc[1] + rr), 70, 110, fill=(60, 60, 60), width=int(S * 0.09))
    for dx in (-0.055, 0.055):
        d.line([(S / 2 + dx * S, S * 0.69), (S / 2 + dx * S, S * 0.80)], fill=BLACK, width=int(S * 0.012))
    return im


def cell_att_bezel():
    im, d = new_cell()
    c, R = (S / 2, S / 2), S / 2 * 0.96
    for a, L in ((0, 0.20), (-10, 0.10), (10, 0.10), (-20, 0.10), (20, 0.10), (-30, 0.16), (30, 0.16),
                 (-60, 0.16), (60, 0.16), (-90, 0.12), (90, 0.12), (-45, 0.08), (45, 0.08)):
        tick(d, c, R * (0.98 - L), R * 0.97, a, S * 0.018)
    d.polygon([pol(c, R * 0.97, -5), pol(c, R * 0.97, 5), pol(c, R * 0.80, 0)], fill=WHITE)
    return im


def cell_att_card():
    im = Image.new('RGB', (S, S), (60, 110, 175))
    d = ImageDraw.Draw(im)
    d.rectangle((0, S / 2, S, S), fill=(110, 70, 35))
    d.line([(0, S / 2), (S, S / 2)], fill=WHITE, width=int(S * 0.012))
    px10 = S / 2 * (0.006 / 0.042)            # 10 deg of pitch = 6 mm on a 42 mm card
    f = font(FB, S * 0.05)
    for p in (-20, -15, -10, -5, 5, 10, 15, 20):
        y = S / 2 - p / 10 * px10
        L = S * (0.16 if p % 10 == 0 else 0.08)
        d.line([(S / 2 - L, y), (S / 2 + L, y)], fill=WHITE, width=int(S * 0.008))
        if p % 10 == 0:
            text_c(d, (S / 2 - L - S * 0.06, y), str(abs(p)), f)
            text_c(d, (S / 2 + L + S * 0.06, y), str(abs(p)), f)
    c = (S / 2, S / 2)
    d.polygon([pol(c, S * 0.40, 0), pol(c, S * 0.44, -5), pol(c, S * 0.44, 5)], fill=WHITE)   # sky pointer
    return im


def cell_hdg():
    im, d = new_cell()
    c, R = (S / 2, S / 2), S / 2 * 0.96
    for a in range(0, 360, 5):
        tick(d, c, R * (0.80 if a % 10 == 0 else 0.87), R * 0.95, a, S * (0.012 if a % 10 == 0 else 0.007))
    f = font(FB, S * 0.1)
    for a in range(0, 360, 30):
        s = {0: 'N', 90: 'E', 180: 'S', 270: 'W'}.get(a, str(a // 10))
        # upright relative to the rim (rotate text)
        t = Image.new('RGBA', (int(S * 0.2), int(S * 0.14)), (0, 0, 0, 0))
        td = ImageDraw.Draw(t)
        text_c(td, (t.width / 2, t.height / 2), s, f, ORANGE if a % 90 == 0 else WHITE)
        t = t.rotate(-a, resample=Image.BICUBIC, expand=True)
        p = pol(c, R * 0.63, a)
        im.paste(t, (int(p[0] - t.width / 2), int(p[1] - t.height / 2)), t)
    return im


def cell_engine(title, sub, vmin, vmax, step, lab_div, green, red=None, yellow=None, lab_step=None):
    arcs = [(green[0], green[1], GREEN)]
    if yellow:
        arcs.append((yellow[0], yellow[1], YELLOW))
    lab_step = lab_step or step
    return dial(vmin, vmax, -135, 135, rng(vmin, vmax, step), rng(vmin, vmax, step / 2),
                [(v, str(int(round(v / lab_div)))) for v in rng(vmin, vmax, lab_step)], arcs=arcs,
                redlines=[red] if red is not None else [], title=title, sub=sub, lab_r=0.60, lab_size=0.105,
                title_y=0.40, sub_y=0.62)


def cell_oil():
    im, d = new_cell()
    c, R = (S / 2, S / 2), S / 2 * 0.96
    ap = lambda v: -150 + v / 200 * 120      # pressure: 7 -> 11 o'clock
    at = lambda v: 150 - v / 150 * 120       # temperature: 5 -> 1 o'clock
    arc(d, c, R * 0.9, ap(85), ap(105), S * 0.035, GREEN)
    arc(d, c, R * 0.9, at(120), at(10), S * 0.035, GREEN)
    for v in rng(0, 200, 20):
        tick(d, c, R * (0.78 if v % 40 == 0 else 0.86), R * 0.94, ap(v), S * 0.012)
    for v in rng(0, 150, 15):
        tick(d, c, R * (0.78 if v % 30 == 0 else 0.86), R * 0.94, at(v), S * 0.012)
    tick(d, c, R * 0.74, R * 0.96, ap(105), S * 0.02, RED)
    tick(d, c, R * 0.74, R * 0.96, at(99), S * 0.02, RED)
    f = font(FB, S * 0.09)
    for v in (0, 100, 200):
        text_c(d, pol(c, R * 0.60, ap(v)), str(v // 10) if v else '0', f)
    for v in (0, 150):
        text_c(d, pol(c, R * 0.60, at(v)), str(v // 10) if v else '0', f)
    text_c(d, (S * 0.36, S * 0.64), 'PSI', font(FC, S * 0.055))
    text_c(d, (S * 0.64, S * 0.64), '°C', font(FC, S * 0.055))
    text_c(d, (S / 2, S * 0.36), 'OIL', font(FC, S * 0.075))
    return im


def cell_fuel(side):
    im = dial(0, 60, -60, 60, rng(0, 60, 15), rng(0, 60, 5),
              [(0, 'E'), (15, '¼'), (30, '½'), (45, '¾'), (60, 'F')], arcs=[(0, 5, RED)],
              title=f'FUEL {side}', sub='GAL', lab_r=0.62, title_y=0.68, sub_y=0.80)
    return im


def cell_clock():
    im, d = new_cell()
    c, R = (S / 2, S / 2), S / 2 * 0.96
    for m in range(60):
        tick(d, c, R * (0.80 if m % 5 == 0 else 0.88), R * 0.95, m * 6, S * (0.016 if m % 5 == 0 else 0.007))
    f = font(FB, S * 0.12)
    for h in range(1, 13):
        text_c(d, pol(c, R * 0.64, h * 30), str(h), f)
    return im


def cell_amp():
    return dial(-60, 60, -90, 90, rng(-60, 60, 30), rng(-60, 60, 10),
                [(-60, '-60'), (-30, '-30'), (0, '0'), (30, '30'), (60, '60')], title='AMPS', sub='',
                lab_r=0.62, lab_size=0.09, title_y=0.72)


RADIO_WINDOWS = {   # LCD / LED windows of each unit, fractions of (S, H): powered content only shows in them
    'GPSCOM': [(0.22, 0.10, 0.78, 0.78), (0.02, 0.09, 0.205, 0.50), (0.79, 0.09, 0.975, 0.37)],
    'XPDR': [(0.20, 0.18, 0.62, 0.82)],
    'AUDIO': [],
}


def radio_cell(kind, lit=False):
    """radio unit face. lit=False: avionics off (dark windows, silk-screen labels only) for the base atlas;
    lit=True: the powered look, used for the display emission map (v5, audit N3)."""
    im = Image.new('RGB', (S, S), (6, 6, 6))
    d = ImageDraw.Draw(im)
    h = {'GPSCOM': 0.625, 'AUDIO': 0.2125, 'XPDR': 0.30}[kind]
    H = int(S * h)
    d.rectangle((0, 0, S, H), fill=(34, 34, 36))
    d.rectangle((4, 4, S - 5, H - 5), outline=(70, 70, 72), width=4)
    off_lcd = (11, 13, 12)
    if kind == 'GPSCOM':
        win = RADIO_WINDOWS[kind]
        d.rectangle((S * win[0][0], H * win[0][1], S * win[0][2], H * win[0][3]), fill=(8, 16, 30) if lit else off_lcd)
        for w in win[1:]:
            d.rectangle((S * w[0], H * w[1], S * w[2], H * w[3]), fill=(6, 12, 6) if lit else off_lcd)
        if lit:
            d.line([(S * 0.30, H * 0.65), (S * 0.50, H * 0.40), (S * 0.72, H * 0.22)], fill=(220, 40, 200), width=10)
            d.polygon([(S * 0.50, H * 0.40), (S * 0.47, H * 0.48), (S * 0.53, H * 0.48)], fill=WHITE)
            fm = font(FM, S * 0.045)
            d.text((S * 0.03, H * 0.12), 'COM', font=fm, fill=(120, 220, 120))
            d.text((S * 0.03, H * 0.25), '118.30', font=fm, fill=(120, 220, 120))
            d.text((S * 0.03, H * 0.38), '121.50', font=fm, fill=(80, 150, 80))
            d.text((S * 0.80, H * 0.12), 'NAV', font=fm, fill=(120, 220, 120))
            d.text((S * 0.80, H * 0.25), '113.9', font=fm, fill=(120, 220, 120))
        fs = font(FC, S * 0.04)
        for i, t in enumerate(('CDI', 'OBS', 'MSG', 'FPL', 'PROC')):
            text_c(d, (S * (0.30 + i * 0.105), H * 0.89), t, fs)
    elif kind == 'AUDIO':
        fs = font(FC, S * 0.05)
        for i, t in enumerate(('COM1', 'COM2', 'NAV1', 'MKR', 'SPKR', 'ICS')):
            x = S * (0.08 + i * 0.15)
            d.rectangle((x, H * 0.18, x + S * 0.11, H * 0.82), fill=(55, 55, 58), outline=(90, 90, 90), width=3)
            text_c(d, (x + S * 0.055, H * 0.5), t, fs)
    else:
        w = RADIO_WINDOWS[kind][0]
        d.rectangle((S * w[0], H * w[1], S * w[2], H * w[3]), fill=(20, 5, 5) if lit else (13, 10, 10))
        if lit:
            text_c(d, (S * 0.41, H * 0.5), '1200 ALT', font(FM, S * 0.075), (255, 70, 40))
        fs = font(FC, S * 0.045)
        for i, t in enumerate(('IDT', 'VFR', 'ON', 'STBY')):
            text_c(d, (S * (0.70 + (i % 2) * 0.13), H * (0.33 + (i // 2) * 0.36)), t, fs)
    return im


RADIO_CELLS = {17: 'GPSCOM', 19: 'XPDR'}     # split into the Display_Radio renderer at export (avionics-powered)


def display_emission():
    """T_Displays_Emission: powered radio windows at full strength, key labels at half (unit backlight);
    black elsewhere. Same UV space as T_Gauges_BC."""
    import numpy as np
    em = np.zeros((H_ATLAS, W_ATLAS, 3), np.float32)
    for i, kind in RADIO_CELLS.items():
        on = np.asarray(radio_cell(kind, True).resize((CELL, CELL), Image.LANCZOS)).astype(np.float32) / 255.0
        lum = on.max(axis=2)
        k = np.clip((lum - 0.45) / 0.35, 0.0, 1.0) * 0.5                  # labels
        H = {'GPSCOM': 0.625, 'XPDR': 0.30}[kind]
        for w in RADIO_WINDOWS[kind]:
            x0, x1 = int(CELL * w[0]), int(CELL * w[2])
            y0, y1 = int(CELL * H * w[1]), int(CELL * H * w[3])
            k[y0:y1, x0:x1] = 1.0
        col, row = i % 8, i // 8
        em[row * CELL:(row + 1) * CELL, col * CELL:(col + 1) * CELL] = on * k[..., None]
    return Image.fromarray((np.clip(em, 0, 1) * 255).astype(np.uint8), 'RGB')


def labels_strip(xs, names):
    """4096 x 160 strip; u maps pilot-left (x=0.64) -> right (x=0.17)."""
    Wd, Hd = 4096 * 2, 160 * 2
    im = Image.new('RGB', (Wd, Hd), (22, 22, 24))
    d = ImageDraw.Draw(im)
    f = font(FC, Hd * 0.42)
    for x, n in zip(xs, names):
        u = (0.64 - x) / 0.47
        text_c(d, (u * Wd, Hd * 0.5), n, f)
    return im.resize((4096, 160), Image.LANCZOS)


def cell_annunciator():
    """v4: 12 lamps, 3 rows x 4, dark lens + coloured legend; lit state is emissive in the game material"""
    im = Image.new('RGB', (S, S), (6, 6, 6))
    d = ImageDraw.Draw(im)
    RED, AMB, GRN = (210, 40, 30), (225, 165, 20), (50, 185, 70)
    colors = {'OIL PRESS': RED, 'ENG HOT': RED, 'STARTER ON': GRN, 'IGNITION': GRN}
    H = int(S * 0.44)              # 3 rows x 4 in a 0.150 x 0.066 panel -> aspect 2.27
    d.rectangle((0, 0, S, H), fill=(20, 20, 22))
    f = font(FC, S * 0.030)
    cw, ch = S / 4, H / 3
    for i, t in enumerate(LY.ANNUN_LAMPS):
        col = colors.get(t, AMB)
        x0, y0 = (i % 4) * cw, (i // 4) * ch
        d.rectangle((x0 + 7, y0 + 7, x0 + cw - 7, y0 + ch - 7), fill=tuple(int(c * 0.22) for c in col),
                    outline=(60, 60, 60), width=4)
        text_c(d, (x0 + cw / 2, y0 + ch / 2), t, f, tuple(int(c * 0.85) for c in col))
    return im


def cell_autopilot():
    im = Image.new('RGB', (S, S), (6, 6, 6))
    d = ImageDraw.Draw(im)
    H = int(S * 0.2125)
    d.rectangle((0, 0, S, H), fill=(34, 34, 36))
    d.rectangle((S * 0.05, H * 0.2, S * 0.45, H * 0.8), fill=(10, 16, 10))
    text_c(d, (S * 0.25, H * 0.5), 'ROL  ALT', font(FM, S * 0.05), (120, 220, 120))
    fs = font(FC, S * 0.024)
    for i, t in enumerate(('AP', 'HDG', 'NAV', 'APR', 'ALT', 'UP', 'DN')):
        x = S * (0.50 + i * 0.07)
        d.rectangle((x, H * 0.25, x + S * 0.055, H * 0.75), fill=(55, 55, 58), outline=(90, 90, 90), width=3)
        text_c(d, (x + S * 0.0275, H * 0.5), t, fs)
    return im


def cell_oat():
    return dial(-40, 50, -135, 135, rng(-40, 50, 10), rng(-40, 50, 5),
                [(v, str(v)) for v in (-40, -20, 0, 20, 40)], title='OAT', sub='°C', lab_r=0.62, lab_size=0.1,
                title_y=0.40, sub_y=0.62)


PLACARDS = ['CABIN HEAT', 'DEFROST', 'PARK BRAKE', 'FUEL SHUTOFF', 'PANEL LT', 'FLOOD LT', 'EMER PWR', 'FRICTION',
            'AVIONICS', 'FLAPS', 'STARTER', 'IGNITION', 'CARGO DOOR L', 'CARGO DOOR R', 'CABIN LT', 'CARGO LT']


def placard_region(atlas):
    d = ImageDraw.Draw(atlas)
    f = font(FC, 40)
    for i, t in enumerate(PLACARDS):
        col, row = i % 8, i // 8
        x0, y0 = col * 512, 1700 + row * 90
        d.rectangle((x0 + 6, y0, x0 + 506, y0 + 80), fill=(22, 22, 24))
        text_c(d, (x0 + 256, y0 + 40), t, f, (225, 225, 220))
    # compass correction card
    x0, y0 = 0, 1885
    d.rectangle((x0 + 6, y0, x0 + 506, y0 + 156), fill=(235, 235, 225))
    fs = font(FM, 24)
    rows = [('FOR', 'N', '30', '60', 'E', '120', '150'), ('STR', '359', '28', '61', '92', '118', '151'),
            ('FOR', 'S', '210', '240', 'W', '300', '330'), ('STR', '182', '209', '242', '271', '299', '331')]
    for r, vals in enumerate(rows):
        for c, v in enumerate(vals):
            d.text((x0 + 16 + c * 70, y0 + 10 + r * 36), v, font=fs, fill=(20, 20, 20))
    # fuel selector overhead placard
    x0 = 512
    d.rectangle((x0 + 6, y0, x0 + 506, y0 + 156), fill=(22, 22, 24))
    text_c(d, (x0 + 128, y0 + 40), 'LEFT', font(FC, 34), (230, 230, 225))
    text_c(d, (x0 + 384, y0 + 40), 'RIGHT', font(FC, 34), (230, 230, 225))
    text_c(d, (x0 + 256, y0 + 100), 'FUEL  ON / OFF', font(FC, 30), (230, 70, 50))
    # CB labels strip
    x0 = 1024
    d.rectangle((x0 + 6, y0, x0 + 2042, y0 + 156), fill=(22, 22, 24))
    cbs = ['BUS 1', 'BUS 2', 'AVN', 'GPS', 'COM', 'XPDR', 'AP', 'INST', 'PITOT', 'LTS', 'STROBE', 'NAV',
           'LAND', 'FUEL P', 'START', 'IGN', 'GEN', 'ANN', 'FLAP', 'TRIM', 'HEAT', 'FAN', 'ELT', 'SPARE']
    for i, t in enumerate(cbs):
        c, r = i % 8, i // 8
        text_c(d, (x0 + 60 + c * 125, y0 + 26 + r * 50), t, font(FC, 26), (225, 225, 220))


# v5 placards in the free cell 20 (atlas px x 2048..2560, y 1024..1536); regions in cell pixels (x0, y0, x1, y1)
P20 = {'QUAD': (0, 0, 512, 48), 'FLAP': (0, 52, 384, 308), 'TRIM': (388, 52, 508, 92), 'FUEL': (0, 312, 256, 376),
       'DOOR': (256, 312, 512, 376), 'EXT': (0, 380, 256, 428), 'CDOOR': (256, 380, 512, 428),
       'FLOOR': (0, 432, 512, 508)}


def cell_placards_v5():
    k = 2
    im = Image.new('RGB', (512 * k, 512 * k), (10, 10, 10))
    d = ImageDraw.Draw(im)
    R = lambda key: tuple(v * k for v in P20[key])
    BG = (22, 22, 24)
    x0, y0, x1, y1 = R('QUAD')
    d.rectangle((x0, y0, x1, y1), fill=BG)
    f = font(FC, 26 * k)
    for i, t in enumerate(('POWER', 'PROP', 'FUEL COND')):
        cx = x0 + (i + 0.5) * (x1 - x0) / 3
        text_c(d, (cx, (y0 + y1) / 2), t, f)
        if i:
            d.line([(x0 + i * (x1 - x0) / 3, y0 + 8 * k), (x0 + i * (x1 - x0) / 3, y1 - 8 * k)], fill=(120, 120, 120),
                   width=2 * k)
    x0, y0, x1, y1 = R('FLAP')
    d.rectangle((x0, y0, x1, y1), fill=BG)
    text_c(d, ((x0 + x1) / 2, y0 + 40 * k), 'FLAPS', font(FB, 44 * k))
    labs = ['FULL', '20°', '10°', 'UP']
    for i, t in enumerate(labs):
        cx = x0 + (0.14 + 0.24 * i) * (x1 - x0)
        d.line([(cx, y0 + 80 * k), (cx, y0 + 150 * k)], fill=WHITE, width=5 * k)
        text_c(d, (cx, y0 + 190 * k), t, font(FC, 34 * k))
    d.line([(x0 + 0.14 * (x1 - x0), y0 + 115 * k), (x0 + 0.86 * (x1 - x0), y0 + 115 * k)], fill=(150, 150, 150),
           width=3 * k)
    x0, y0, x1, y1 = R('TRIM')
    d.rectangle((x0, y0, x1, y1), fill=BG)
    fs = font(FC, 12 * k)
    for i, (t, col) in enumerate((('DN', WHITE), ('T.O.', (60, 200, 80)), ('UP', WHITE))):
        cx = x0 + (0.15 + 0.35 * i) * (x1 - x0)
        d.line([(cx, y0 + 3 * k), (cx, y0 + 15 * k)], fill=col, width=2 * k)
        text_c(d, (cx, y0 + 28 * k), t, fs, col)
    x0, y0, x1, y1 = R('FUEL')
    d.rectangle((x0, y0, x1, y1), fill=BG)
    text_c(d, ((x0 + x1) / 2, y0 + 20 * k), 'FUEL SHUTOFF', font(FB, 26 * k), (230, 60, 45))
    text_c(d, ((x0 + x1) / 2, y0 + 47 * k), 'PULL OFF', font(FC, 22 * k), WHITE)
    x0, y0, x1, y1 = R('DOOR')
    d.rectangle((x0, y0, x1, y1), fill=(40, 40, 42))
    text_c(d, ((x0 + x1) / 2, y0 + 20 * k), 'DOOR', font(FB, 24 * k))
    text_c(d, ((x0 + x1) / 2, y0 + 46 * k), 'PULL TO OPEN', font(FC, 22 * k))
    x0, y0, x1, y1 = R('EXT')
    d.rectangle((x0, y0, x1, y1), fill=(190, 30, 25))
    text_c(d, ((x0 + x1) / 2, (y0 + y1) / 2), 'FIRE EXTINGUISHER', font(FB, 17 * k), (245, 245, 240))
    x0, y0, x1, y1 = R('CDOOR')
    d.rectangle((x0, y0, x1, y1), fill=(40, 40, 42))
    text_c(d, ((x0 + x1) / 2, (y0 + y1) / 2), 'CARGO DOOR - PULL TO OPEN', font(FC, 16 * k))
    x0, y0, x1, y1 = R('FLOOR')
    d.rectangle((x0, y0, x1, y1), fill=(16, 16, 16))
    for t in range(0, x1 - x0, 28 * k):                           # hazard stripes at both ends
        for xa in (x0, x1 - 56 * k):
            d.polygon([(xa + t % (56 * k), y0), (xa + t % (56 * k) + 14 * k, y0), (xa + t % (56 * k) - 10 * k, y1),
                       (xa + t % (56 * k) - 24 * k, y1)], fill=(230, 190, 20))
    d.rectangle((x0 + 56 * k, y0, x1 - 56 * k, y1), fill=(16, 16, 16))
    text_c(d, ((x0 + x1) / 2, y0 + 24 * k), 'MAX FLOOR LOADING 200 LB/SQ FT', font(FB, 17 * k), (235, 195, 30))
    text_c(d, ((x0 + x1) / 2, y0 + 54 * k), 'SECURE ALL CARGO BEFORE FLIGHT', font(FC, 16 * k), (235, 235, 230))
    return im.resize((512, 512), Image.LANCZOS)


def emission_map(atlas):
    """backlit markings only: dials, radio faces, switch / panel placard lightplates, CB labels.
    Not lit: compass card, overhead fuel placard (dome-lit), v5 placards (cell 20)."""
    import numpy as np
    a = np.asarray(atlas).astype(np.float32) / 255.0
    lum = a.max(axis=2)
    k = np.clip((lum - 0.30) / 0.55, 0.0, 1.0)[..., None]
    e = a * k
    e[1024:1536, 2048:2560] = 0.0                       # cell 20
    e[1885:2048, 0:1024] = 0.0                          # compass card + overhead fuel placard
    return Image.fromarray((e * 255).astype(np.uint8), 'RGB')


# ================================================================== v6: 4096 x 4096 atlas (panel v6)
# top half = v5 cells (17/18/19 repainted: VOLT, VAC, HOBBS); bottom half = regions from panel6 (atlas6.json)
import numpy as np
import panel6 as P6

FN = '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf'
LEG = (234, 234, 228)                      # lightplate legend white
PLATE_BG = (33, 33, 35)
AMBER6, RED6, GREEN6 = (245, 168, 28), (236, 48, 32), (62, 212, 84)
ANN_RGB = {'red': RED6, 'green': GREEN6, 'amber': AMBER6}


def cell_volt():
    return dial(0, 35, -135, 135, rng(0, 35, 5), rng(0, 35, 1), [(v, str(v)) for v in (0, 10, 20, 30)],
                arcs=[(24, 29, GREEN), (29, 31, YELLOW)], redlines=[32], title='VOLTS', sub='DC', lab_r=0.60,
                lab_size=0.105, title_y=0.40, sub_y=0.62)


def cell_vac():
    return dial(0, 10, -135, 135, rng(0, 10, 1), rng(0, 10, 0.5), [(v, str(v)) for v in (0, 2, 4, 6, 8, 10)],
                arcs=[(4.5, 5.5, GREEN)], title='SUCTION', sub='IN HG', lab_r=0.60, lab_size=0.10,
                title_y=0.40, sub_y=0.62)


def cell_hobbs():
    """LCD hour meter: black face, legends, dark window where Display_Hobbs sits (P6.HOBBS_WIN, dial r 26.5 mm)"""
    im, d = new_cell()
    r_mm = P6.DS / 2 - P6.BEZEL_W[P6.DS]
    k = S / (2 * r_mm * 1000)                                   # px per mm in the cell
    w = P6.HOBBS_WIN
    cx, cy = S / 2 + w['dx'] * 1000 * k, S / 2 - w['dz'] * 1000 * k
    hw, hh = w['w'] * 500 * k, w['h'] * 500 * k
    d.rounded_rectangle((cx - hw - 6, cy - hh - 6, cx + hw + 6, cy + hh + 6), radius=10, fill=(40, 40, 42))
    d.rectangle((cx - hw, cy - hh, cx + hw, cy + hh), fill=(9, 12, 10))
    text_c(d, (S / 2, cy - hh - 0.11 * S), 'HOURS', font(FC, S * 0.085))
    text_c(d, (S / 2, cy + hh + 0.12 * S), 'HOBBS', font(FC, S * 0.06), (190, 190, 182))
    text_c(d, (S / 2, cy + hh + 0.21 * S), 'QUARTZ', font(FC, S * 0.04), (150, 150, 145))
    return im


class Plate:
    """supersampled painter for one atlas region; coordinates in plate-local mm (s right, t down)"""

    def __init__(self, reg, bg=PLATE_BG, ss=3):
        self.rect = reg['rect']
        x, y, w, h = self.rect
        self.wm, self.hm = reg['size_mm']
        self.W, self.H = w * ss, h * ss
        self.kx, self.ky = self.W / self.wm, self.H / self.hm
        self.im = Image.new('RGB', (self.W, self.H), bg)
        self.d = ImageDraw.Draw(self.im)

    def p(self, s, t):
        return (s * self.kx, t * self.ky)

    def text(self, s, t, size, txt, fill=LEG, fnt=FC, align='c'):
        """size = em height in mm; text vertically centred on t by its cap height"""
        f = ImageFont.truetype(fnt, max(4, int(round(size * self.ky))))
        cap = f.getbbox('H')
        x, y = self.p(s, t)
        y_base = y + (cap[3] - cap[1]) / 2
        anchor = {'c': 'ms', 'l': 'ls', 'r': 'rs'}[align]
        self.d.text((x, y_base), txt, font=f, fill=fill, anchor=anchor)

    def text_w(self, size, txt, fnt=FC):
        f = ImageFont.truetype(fnt, max(4, int(round(size * self.ky))))
        return f.getlength(txt) / self.kx

    def rect_(self, s0, t0, s1, t1, fill=None, outline=None, width=0.0, radius=0.0):
        box = (*self.p(s0, t0), *self.p(s1, t1))
        if radius > 0:
            self.d.rounded_rectangle(box, radius=radius * self.kx, fill=fill, outline=outline,
                                     width=max(1, int(width * self.kx)) if outline else 0)
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=max(1, int(width * self.kx)) if outline else 0)

    def circle(self, s, t, r, fill=None, outline=None, width=0.0):
        x, y = self.p(s, t)
        rr = r * self.kx
        self.d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=fill, outline=outline,
                       width=max(1, int(width * self.kx)) if outline else 0)

    def line(self, pts, fill=LEG, width=0.5):
        self.d.line([self.p(*q) for q in pts], fill=fill, width=max(1, int(width * self.kx)))

    def arc_scale(self, s, t, r, a0, a1, ticks, fill=LEG, width=0.45, tick_len=1.6):
        """clockwise from 12 o'clock (pilot view), degrees"""
        x, y = self.p(s, t)
        rr = r * self.kx
        self.d.arc((x - rr, y - rr, x + rr, y + rr), a0 - 90, a1 - 90, fill=fill, width=max(1, int(width * self.kx)))
        for a in ticks:
            p0 = (s + r * math.sin(math.radians(a)), t - r * math.cos(math.radians(a)))
            p1 = (s + (r + tick_len) * math.sin(math.radians(a)), t - (r + tick_len) * math.cos(math.radians(a)))
            self.line([p0, p1], fill, width)

    def bevel_edge(self, light=(62, 62, 64), dark=(12, 12, 13), w=0.6):
        self.rect_(0, 0, self.wm, self.hm, outline=dark, width=w * 1.6)
        self.line([(w, self.hm - w), (w, w), (self.wm - w, w)], light, w)

    def out(self):
        return self.im.resize(self.rect[2:], Image.LANCZOS)


def _fit(pl, txt, size, max_w, fnt=FC):
    while size > 1.2 and pl.text_w(size, txt, fnt) > max_w:
        size *= 0.94
    return size


# ------------------------------------------------------------------ radio faces (off look in the base atlas, lit legends in T_Displays_Emission)
def radio_face(kind, reg, lit=False):
    spec = P6.RADIO_FACE[kind]
    pl = Plate(reg, bg=(0, 0, 0) if lit else (31, 31, 33))
    L = (lambda v: tuple(int(c * v) for c in (255, 252, 240))) if lit else (lambda v: LEG)
    if not lit:
        pl.bevel_edge(light=(70, 70, 72), dark=(10, 10, 11), w=0.7)
        for nm, (s0, t0, s1, t1) in spec['windows'].items():
            pl.rect_(s0 - 1.2, t0 - 1.2, s1 + 1.2, t1 + 1.2, fill=(16, 16, 17), radius=1.0)
            pl.rect_(s0, t0, s1, t1, fill=(7, 9, 9))
        for s, t, od, idd, kd in spec['knobs']:
            pl.circle(s, t, od / 2 + 1.0, fill=(14, 14, 15))
        for s, t, dd, col in spec.get('lamps', []):
            pl.circle(s, t, dd / 2 + 0.6, fill=(12, 12, 12))
            pl.circle(s, t, dd / 2, fill=tuple(int(c * 0.42) for c in col))
            pl.circle(s - dd * 0.15, t - dd * 0.15, dd * 0.13, fill=tuple(min(255, int(c * 0.7) + 40) for c in col))
    for s, t, sz, txt in spec['texts'] + spec.get('lamp_labels', []):
        pl.text(s, t, sz, txt, fill=L(0.5) if lit else (200, 200, 194))
    for s0, t0, s1, t1, txt in spec['caps']:
        if not lit:
            pl.rect_(s0, t0, s1, t1, fill=(50, 50, 54), outline=(18, 18, 20), width=0.35)
            pl.line([(s0 + 0.4, t1 - 0.5), (s0 + 0.4, t0 + 0.4), (s1 - 0.4, t0 + 0.4)], (84, 84, 88), 0.3)
        txt2 = {'<>': '⇆', 'D->': 'D→'}.get(txt, txt)
        sz = _fit(pl, txt2, min(2.6, (t1 - t0) * 0.42), (s1 - s0) * 0.86)
        pl.text((s0 + s1) / 2, (t0 + t1) / 2, sz, txt2, fill=L(0.75) if lit else (226, 226, 220),
                fnt=FB if txt2 in ('⇆', 'D→') else FC)
    return pl.out()


# ------------------------------------------------------------------ annunciator
def annunciator(reg, lit=False):
    pl = Plate(reg, bg=(0, 0, 0) if lit else (13, 13, 14))
    for i, name in enumerate(P6.ANN_LAMPS):
        col = ANN_RGB[P6.ANN_COLOR.get(name, 'amber')]
        s0, t0, s1, t1 = P6.ann_lens(i)
        if lit:
            pl.rect_(s0, t0, s1, t1, fill=tuple(int(c * 0.30) for c in col))
            sz = _fit(pl, name, 4.8, (s1 - s0) * 0.86)
            pl.text((s0 + s1) / 2, (t0 + t1) / 2, sz, name, fill=tuple(min(255, int(c * 1.0 + 25)) for c in col))
        else:
            pl.rect_(s0 - 0.6, t0 - 0.6, s1 + 0.6, t1 + 0.6, fill=(6, 6, 6))
            pl.rect_(s0, t0, s1, t1, fill=tuple(int(c * 0.10) + 9 for c in col))
            pl.line([(s0 + 0.5, t0 + 0.6), (s1 - 0.5, t0 + 0.6)], tuple(int(c * 0.16) + 22 for c in col), 0.5)
            sz = _fit(pl, name, 4.8, (s1 - s0) * 0.86)
            pl.text((s0 + s1) / 2, (t0 + t1) / 2, sz, name, fill=tuple(int(c * 0.50) for c in col))
    return pl.out()


# ------------------------------------------------------------------ switch lightplate
def _sw_local(x, z):
    xl, xr, zb, zt = P6.SW_PLATE
    return ((xl - x) * 1000, (zt - z) * 1000)


def switch_plate(reg):
    pl = Plate(reg)
    pl.bevel_edge()
    W = pl.wm
    for s, t in ((5, 5), (W - 5, 5), (5, pl.hm - 5), (W - 5, pl.hm - 5)):
        pl.circle(s, t, 2.6, fill=(14, 14, 15))
    for bone, (x, z, lab) in P6.RHEOSTATS.items():
        s, t = _sw_local(x, z)
        pl.text(s, t - 21.0, 4.0, lab)
        pl.arc_scale(s, t, 15.0, -135, 135, [-135, -90, -45, 0, 45, 90, 135], width=0.45)
        for a, txt in ((-135, 'OFF'), (135, 'BRT')):
            pl.text(s + 19.8 * math.sin(math.radians(a)), t - 19.8 * math.cos(math.radians(a)), 2.8, txt)
    for z in P6.SW_DIVIDERS:
        t = _sw_local(0, z)[1]
        pl.line([(7, t), (W - 7, t)], (150, 150, 148), 0.5)
    t_div = _sw_local(0, P6.SW_DIVIDERS[-1])[1]
    pl.line([(W / 2, t_div + 4), (W / 2, pl.hm - 8)], (110, 110, 108), 0.4)
    for x, z, txt in P6.SW_HEADERS:
        s, t = _sw_local(x, z)
        pl.text(s, t, 4.4, txt, fill=(250, 250, 244))
        tw = pl.text_w(4.4, txt) / 2 + 2.5
        if txt == 'CARGO DOOR':
            pl.line([(10, t), (s - tw, t)], (150, 150, 148), 0.45)
            pl.line([(s + tw, t), (W - 10, t)], (150, 150, 148), 0.45)
    for bone, (x, z, lab, on, off) in P6.SWITCHES.items():
        s, t = _sw_local(x, z)
        if bone == 'SW_Starter':          # the flip guard hides the plate below it (pilot view): legends on its right
            pl.text(s + 27.0, t - 11.0, 4.0, lab)
            pl.text(s + 27.0, t - 2.0, 2.9, on, align='c')
            pl.text(s + 27.0, t + 7.5, 2.9, off, align='c')
        else:
            pl.text(s, t - 18.5, 4.3, lab)
            pl.text(s + 17.5, t - 5.0, 2.9, on, align='c')
            pl.text(s + 17.5, t + 6.0, 2.9, off, align='c')
        pl.circle(s, t, 6.2, fill=(16, 16, 17))                   # nut footprint
    return pl.out()


# ------------------------------------------------------------------ circuit breaker lightplate
def cb_plate(reg):
    pl = Plate(reg)
    pl.bevel_edge()
    xl, xr, zb, zt = P6.CB_PLATE
    pl.text(pl.wm / 2, 8.5, 3.8, 'CIRCUIT BREAKERS', fill=(250, 250, 244))
    tw = pl.text_w(3.8, 'CIRCUIT BREAKERS') / 2 + 3
    pl.line([(8, 8.5), (pl.wm / 2 - tw, 8.5)], (150, 150, 148), 0.45)
    pl.line([(pl.wm / 2 + tw, 8.5), (pl.wm - 8, 8.5)], (150, 150, 148), 0.45)
    for s, t in ((4.5, 4.5), (pl.wm - 4.5, 4.5), (4.5, pl.hm - 4.5), (pl.wm - 4.5, pl.hm - 4.5)):
        pl.circle(s, t, 2.4, fill=(14, 14, 15))
    for r, z in enumerate(P6.CB_ROWS):
        for c, x in enumerate(P6.CB_COLS):
            name, amps = P6.CB[r][c]
            s, t = (xl - x) * 1000, (zt - z) * 1000
            sz = _fit(pl, name, 3.2, 32.0)
            pl.text(s, t - 12.8, sz, name)
            pl.circle(s, t, P6.CB_COLLAR_R * 1000 + 0.4, fill=(12, 12, 12))
            pl.circle(s, t, P6.CB_CAP_R * 1000, fill=(20, 20, 21))
            pl.text(s, t, 3.9 if amps < 10 else 3.5, str(amps), fill=(246, 246, 240), fnt=FB)
    return pl.out()


def label_plate(reg, txt, size=4.4):
    pl = Plate(reg)
    pl.bevel_edge(w=0.35)
    pl.text(pl.wm / 2, pl.hm / 2, _fit(pl, txt, size, pl.wm - 4), txt)
    return pl.out()


def jacks_plate(reg):
    pl = Plate(reg)
    pl.bevel_edge(w=0.4)
    for s, t, txt in P6.JACK_POS:
        pl.text(s, 7.0, 3.0, txt)
        pl.circle(s, t, 5.4, fill=(12, 12, 12))
    for s, t in ((3.5, 3.5), (pl.wm - 3.5, 3.5), (3.5, pl.hm - 3.5), (pl.wm - 3.5, pl.hm - 3.5)):
        pl.circle(s, t, 1.6, fill=(14, 14, 15))
    return pl.out()


# ------------------------------------------------------------------ placards (not backlit)
def placard_limits(reg):
    pl = Plate(reg, bg=(17, 17, 18))
    pl.rect_(2.0, 2.0, pl.wm - 2.0, pl.hm - 2.0, outline=(205, 205, 198), width=0.5)
    pl.text(pl.wm / 2, 9.0, 5.2, 'OPERATING LIMITATIONS', fill=(240, 240, 234), fnt=FB)
    W = pl.wm
    lines = ['THIS AIRPLANE MUST BE OPERATED IN THE NORMAL CATEGORY IN',
             'COMPLIANCE WITH THE LIMITATIONS IN THE FLIGHT MANUAL.']
    for i, s in enumerate(lines):
        pl.text(W / 2, 17.5 + i * 5.2, _fit(pl, s, 3.4, W - 12), s, fill=(225, 225, 218))
    rows = [('MAX TAKEOFF WEIGHT', '8000 LB'), ('MANEUVERING SPEED  VA', '148 KIAS'),
            ('MAX FLAP EXTENDED  VFE  10°', '175 KIAS'), ('20° / FULL', '150 / 125 KIAS'),
            ('DEMONSTRATED CROSSWIND', '20 KNOTS'), ('MAX OPERATING ALTITUDE', '25 000 FT')]
    for i, (a, b) in enumerate(rows):
        t = 31.5 + i * 6.6
        pl.text(8, t, 3.5, a, fill=(225, 225, 218), align='l')
        pl.text(W - 8, t, 3.5, b, fill=(235, 235, 228), align='r')
        wa, wb = pl.text_w(3.5, a), pl.text_w(3.5, b)
        s0, s1 = 8 + wa + 2, W - 8 - wb - 2
        k = s0
        while k < s1 - 0.6:
            pl.circle(k, t + 1.0, 0.28, fill=(170, 170, 164))
            k += 1.6
    for i, s in enumerate(('NO ACROBATIC MANEUVERS, INCLUDING SPINS, APPROVED',
                           'DAY  •  NIGHT  •  VFR  •  IFR  •  NO KNOWN ICING')):
        pl.text(W / 2, 75.5 + i * 6.0, _fit(pl, s, 3.5, W - 12), s, fill=(235, 235, 228))
    return pl.out()


def placard_nosmoke(reg):
    pl = Plate(reg, bg=(236, 235, 228))
    pl.rect_(1.6, 1.6, pl.wm - 1.6, pl.hm - 1.6, outline=(30, 30, 30), width=0.6)
    cs, ct, r = 21.0, pl.hm / 2, 16.0
    pl.circle(cs, ct, r, fill=(236, 235, 228), outline=(205, 30, 25), width=2.6)
    pl.rect_(cs - 11, ct - 2.0, cs + 7, ct + 2.0, fill=(40, 40, 40))           # cigarette
    pl.rect_(cs + 7, ct - 2.0, cs + 10.5, ct + 2.0, fill=(225, 120, 40))
    for k in range(3):
        pl.line([(cs + 9 + k * 1.5, ct - 4.5), (cs + 10 + k * 1.5, ct - 9.0)], (120, 120, 120), 0.5)
    a = math.radians(45)
    pl.line([(cs - r * 0.70, ct - r * 0.70), (cs + r * 0.70, ct + r * 0.70)], (205, 30, 25), 2.6)
    pl.text(87, 20.0, 8.6, 'NO SMOKING', fill=(20, 20, 20), fnt=FB)
    pl.text(87, 37.0, 5.4, 'FASTEN SEAT BELTS', fill=(20, 20, 20), fnt=FB)
    return pl.out()


def placard_engine(reg):
    pl = Plate(reg, bg=(17, 17, 18))
    pl.rect_(1.2, 1.2, pl.wm - 1.2, pl.hm - 1.2, outline=(200, 200, 194), width=0.4)
    for i, s in enumerate(('ENGINE LIMITS   TRQ 1865 FT-LB   ITT 805 °C',
                           'NG 101.6 %   PROP 1900 RPM   OIL 85-105 PSI')):
        pl.text(pl.wm / 2, 6.3 + i * 7.4, _fit(pl, s, 3.8, pl.wm - 8), s, fill=(232, 232, 226))
    return pl.out()


def mapcase_plate(reg):
    pl = Plate(reg, bg=(20, 20, 21))
    pl.text(pl.wm / 2, pl.hm / 2, 4.2, 'MAP CASE', fill=(214, 214, 208))
    return pl.out()


def map_art(reg):
    """folded VFR chart (fictional): terrain tints, lakes, a river, airways, airports, grid, title block"""
    pl = Plate(reg, bg=(214, 222, 196), ss=2)
    W, H = pl.wm, pl.hm
    rnd = np.random.default_rng(42)
    for k in range(70):                                         # terrain tint blobs
        s, t, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(6, 22)
        tone = rnd.choice([0, 1, 2])
        col = [(205, 214, 182), (222, 210, 176), (196, 205, 170)][tone]
        pl.circle(s, t, r, fill=col)
    for k in range(5):                                          # lakes
        s, t = rnd.uniform(15, W - 15), rnd.uniform(15, H - 15)
        pts = [(s + rnd.uniform(4, 11) * math.cos(a), t + rnd.uniform(3, 8) * math.sin(a))
               for a in np.linspace(0, 2 * math.pi, 14)]
        pl.d.polygon([pl.p(*q) for q in pts], fill=(150, 196, 222), outline=(70, 120, 170))
    river = [(0, 30)]
    for k in range(1, 12):
        river.append((k * W / 11, river[-1][1] + rnd.uniform(-9, 11)))
    pl.line(river, (70, 130, 190), 1.0)
    for s in np.arange(0, W, 30):
        pl.line([(s, 0), (s, H)], (120, 120, 120), 0.25)
    for t in np.arange(0, H, 30):
        pl.line([(0, t), (W, t)], (120, 120, 120), 0.25)
    apts = [(40, 50), (120, 32), (170, 95), (78, 112), (196, 40)]
    for a, b in zip(apts, apts[1:]):
        pl.line([a, b], (170, 60, 150), 0.7)
    for i, (s, t) in enumerate(apts):
        pl.circle(s, t, 3.2, outline=(170, 60, 150), width=0.8)
        pl.line([(s - 2, t - 1.6), (s + 2, t + 1.6)], (170, 60, 150), 0.8)
        pl.text(s + 5, t - 4, 2.6, ['NORTH FORK', 'ELK LAKE', 'RIDGE STRIP', 'BEAR CREEK', 'PINE BAY'][i],
                fill=(150, 40, 130), align='l')
    pl.rect_(W - 70, H - 22, W - 4, H - 4, fill=(245, 245, 238), outline=(40, 40, 40), width=0.4)
    pl.text(W - 37, H - 16, 3.6, 'VFR CHART', fill=(20, 20, 20), fnt=FB)
    pl.text(W - 37, H - 9, 2.6, 'NORTH RANGE  1:500 000', fill=(30, 30, 30))
    for s in (W / 3, 2 * W / 3):                                # fold creases
        pl.line([(s, 0), (s, H)], (236, 240, 226), 0.8)
        pl.line([(s + 0.8, 0), (s + 0.8, H)], (168, 172, 150), 0.5)
    pl.line([(0, H / 2), (W, H / 2)], (236, 240, 226), 0.8)
    pl.line([(0, H / 2 + 0.8), (W, H / 2 + 0.8)], (168, 172, 150), 0.5)
    return pl.out()


def poh_cover(reg):
    pl = Plate(reg, bg=(22, 26, 34), ss=2)
    pl.rect_(6, 6, pl.wm - 6, pl.hm - 6, outline=(170, 150, 90), width=0.8)
    pl.text(pl.wm / 2, 60, 9.0, "PILOT'S", fill=(220, 200, 130), fnt=FB)
    pl.text(pl.wm / 2, 76, 9.0, 'OPERATING', fill=(220, 200, 130), fnt=FB)
    pl.text(pl.wm / 2, 92, 9.0, 'HANDBOOK', fill=(220, 200, 130), fnt=FB)
    pl.line([(30, 108), (pl.wm - 30, 108)], (170, 150, 90), 0.8)
    pl.text(pl.wm / 2, 122, 6.0, 'UTILITY TURBOPROP', fill=(205, 205, 200))
    pl.text(pl.wm / 2, 190, 4.0, 'KEEP IN AIRCRAFT', fill=(160, 160, 155))
    return pl.out()


# ------------------------------------------------------------------ assembly
LIT_REGIONS = ('SW', 'CB', 'L_CabinHeat', 'L_Defrost', 'L_ParkBrake', 'L_AnnTest', 'JACKS')   # backlit lightplates


def paste_region(atlas, reg, im, pad=8):
    """paste with an edge-extended gutter (mip-safe)"""
    x, y, w, h = reg['rect']
    a = np.asarray(im)
    big = np.pad(a, ((pad, pad), (pad, pad), (0, 0)), mode='edge')
    atlas.paste(Image.fromarray(big), (x - pad, y - pad))


def build():
    R = P6.write_atlas_json()['regions']
    atlas = Image.new('RGB', (W_ATLAS, 4096), (10, 10, 10))
    cells = {
        0: cell_asi(), 1: cell_att_bezel(), 2: cell_att_card(), 3: cell_alt(), 4: cell_tc(), 5: cell_hdg(),
        6: cell_vsi(),
        7: cell_engine('TORQUE', 'FT-LB x100', 0, 2400, 200, 100, (0, 1865), red=1865, lab_step=400),
        8: cell_engine('ITT', '°C x100', 100, 1100, 100, 100, (400, 765), red=805, lab_step=200),
        9: cell_engine('NG', '% RPM', 0, 110, 10, 1, (52, 101.6), red=101.6, lab_step=20),
        10: cell_engine('PROP', 'RPM x100', 0, 2400, 200, 100, (1600, 1900), red=1900, lab_step=400),
        11: cell_engine('FUEL FLOW', 'PPH x100', 0, 400, 50, 100, (60, 350), lab_step=100),
        12: cell_oil(), 13: cell_fuel('L'), 14: cell_fuel('R'), 15: cell_clock(), 16: cell_amp(),
        17: cell_volt(), 18: cell_vac(), 19: cell_hobbs(),
        20: cell_placards_v5(), 23: cell_oat(),
    }
    for i, im in cells.items():
        col, row = i % 8, i // 8
        atlas.paste(im.resize((CELL, CELL), Image.LANCZOS), (col * CELL, row * CELL))
    placard_region(atlas)                                   # compass card + overhead fuel placard are still used
    dr = ImageDraw.Draw(atlas)
    dr.rectangle((0, 1536, 4095, 1880), fill=(10, 10, 10))  # v5 switch strip + panel placard slots: unused in v6
    dr.rectangle((1024, 1880, 4095, 2047), fill=(10, 10, 10))   # v5 CB label strip: unused
    ems = Image.new('RGB', (W_ATLAS, 4096), (0, 0, 0))      # T_Displays_Emission
    for u in P6.RADIOS:
        reg = R['R_' + u]
        paste_region(atlas, reg, radio_face(u, reg))
        paste_region(ems, reg, radio_face(u, reg, lit=True))
    paste_region(atlas, R['ANN'], annunciator(R['ANN']))
    paste_region(ems, R['ANN'], annunciator(R['ANN'], lit=True))
    paste_region(atlas, R['SW'], switch_plate(R['SW']))
    paste_region(atlas, R['CB'], cb_plate(R['CB']))
    for k, v in P6.LABELS.items():
        paste_region(atlas, R[k], label_plate(R[k], v[4], 4.6 if k != 'L_AnnTest' else 3.6))
    paste_region(atlas, R['JACKS'], jacks_plate(R['JACKS']))
    paste_region(atlas, R['P_Limits'], placard_limits(R['P_Limits']))
    paste_region(atlas, R['P_NoSmoke'], placard_nosmoke(R['P_NoSmoke']))
    paste_region(atlas, R['P_Engine'], placard_engine(R['P_Engine']))
    paste_region(atlas, R['MAPCASE'], mapcase_plate(R['MAPCASE']))
    paste_region(atlas, R['MAP'], map_art(R['MAP']))
    paste_region(atlas, R['POH'], poh_cover(R['POH']))
    p = os.path.join(OUT, 'T_Gauges_BC.png')
    atlas.save(p)
    # backlight emission: v5 rule for the dial cells (top half), lightplates only in the bottom half
    a = np.asarray(atlas).astype(np.float32) / 255.0
    k = np.clip((a.max(axis=2) - 0.30) / 0.55, 0.0, 1.0)[..., None]
    e = a * k
    e[1024:1536, 2048:2560] = 0.0                           # cell 20 placards
    e[1536:2048, :] = 0.0                                   # compass card, overhead placard, unused strips
    e[1024:1536, 2560:3584] = 0.0                           # cells 21/22 (unused)
    lit = np.zeros(e.shape[:2], bool)
    lit[:2048] = True
    for n in LIT_REGIONS:
        x, y, w, h = R[n]['rect']
        lit[y:y + h, x:x + w] = True
    e[~lit] = 0.0
    Image.fromarray((e * 255).astype(np.uint8), 'RGB').save(os.path.join(OUT, 'T_Gauges_Emission.png'))
    ems.save(os.path.join(OUT, 'T_Displays_Emission.png'))
    print('saved', p, atlas.size)


if __name__ == '__main__':
    build()
