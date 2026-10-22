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


def radio_cell(kind):
    im = Image.new('RGB', (S, S), (6, 6, 6))
    d = ImageDraw.Draw(im)
    h = {'GPSCOM': 0.625, 'AUDIO': 0.2125, 'XPDR': 0.30}[kind]
    H = int(S * h)
    d.rectangle((0, 0, S, H), fill=(34, 34, 36))
    d.rectangle((4, 4, S - 5, H - 5), outline=(70, 70, 72), width=4)
    if kind == 'GPSCOM':
        d.rectangle((S * 0.22, H * 0.10, S * 0.78, H * 0.78), fill=(8, 16, 30))
        d.line([(S * 0.30, H * 0.65), (S * 0.50, H * 0.40), (S * 0.72, H * 0.22)], fill=(220, 40, 200), width=10)
        d.polygon([(S * 0.50, H * 0.40), (S * 0.47, H * 0.48), (S * 0.53, H * 0.48)], fill=WHITE)
        fm = font(FM, S * 0.055)
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
        d.rectangle((S * 0.20, H * 0.18, S * 0.62, H * 0.82), fill=(20, 5, 5))
        text_c(d, (S * 0.41, H * 0.5), '1200 ALT', font(FM, S * 0.075), (255, 70, 40))
        fs = font(FC, S * 0.045)
        for i, t in enumerate(('IDT', 'VFR', 'ON', 'STBY')):
            text_c(d, (S * (0.70 + (i % 2) * 0.13), H * (0.33 + (i // 2) * 0.36)), t, fs)
    return im


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


def build():
    atlas = Image.new('RGB', (W_ATLAS, H_ATLAS), (10, 10, 10))
    cells = {
        0: cell_asi(), 1: cell_att_bezel(), 2: cell_att_card(), 3: cell_alt(), 4: cell_tc(), 5: cell_hdg(),
        6: cell_vsi(),
        7: cell_engine('TORQUE', 'FT-LB x100', 0, 2400, 200, 100, (0, 1865), red=1865, lab_step=400),
        8: cell_engine('ITT', '°C x100', 100, 1100, 100, 100, (400, 765), red=805, lab_step=200),
        9: cell_engine('NG', '% RPM', 0, 110, 10, 1, (52, 101.6), red=101.6, lab_step=20),
        10: cell_engine('PROP', 'RPM x100', 0, 2400, 200, 100, (1600, 1900), red=1900, lab_step=400),
        11: cell_engine('FUEL FLOW', 'PPH x100', 0, 400, 50, 100, (60, 350), lab_step=100),
        12: cell_oil(), 13: cell_fuel('L'), 14: cell_fuel('R'), 15: cell_clock(), 16: cell_amp(),
        17: radio_cell('GPSCOM'), 18: radio_cell('AUDIO'), 19: radio_cell('XPDR'),
        21: cell_annunciator(), 22: cell_autopilot(), 23: cell_oat(),
    }
    for i, im in cells.items():
        col, row = i % 8, i // 8
        atlas.paste(im.resize((CELL, CELL), Image.LANCZOS), (col * CELL, row * CELL))
    sys.path.insert(0, HERE)
    import layout as LY
    strip = labels_strip([x for _, x in LY.SWITCHES],
                         ['BATT', 'AVIONICS', 'FUEL PUMP', 'IGNITION', 'START', 'BEACON', 'STROBE', 'NAV', 'LAND'])
    atlas.paste(strip, (0, 3 * CELL))
    placard_region(atlas)
    p = os.path.join(OUT, 'T_Gauges_BC.png')
    atlas.save(p)
    print('saved', p)


if __name__ == '__main__':
    build()
