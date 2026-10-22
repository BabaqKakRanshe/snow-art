"""Panel atlas of the main building (1024 x 1024, pixel art, point-filtered): every sign, label, plan, dial and paper of
Update 3 at its Update 3 place (main_signs.py puts the quads), redrawn in the project's pixel font; German first, English
under it on the wall signs, the controller's labels in both (the boiler note names the STÖRUNG lamp); the lens tiles of the
fixtures (M_FX_*) and the fault lamp (M_HeatFault).
  signs   obs_plate (RADIOOBSERVATORIUM HOHENMOOS), garage, befugt, kontroll, server, wohn, brand, hoch, technik, tueren,
          heizoel, klingel, notstrom, feuertuer, heiznot, floor_UG / _EG / _1OG / _DACH, uv_og, hv_ug, main_lbl, hv_labels
  safety  pic_ext (F001), pic_call (F005), pic_aid (E003), pic_nosmoke (P002), evac_EG / _OG / _UG (the plans of the
          building from main_spec), exit (the running man; emission)
  devices clock (stopped at 2:40, as the checkpoint's), mano (0-4 bar), therm (0-120 C), thermostat (5-30 C), timer,
          ctl_front (the heating controller), boiler_panel, mimic (the Schaltraum's wiring board), wb_leit (the control
          room's whiteboard), display (the antenna field mimic), map (the map table's map), crt (dark screen)
  papers  paper_a..d, calendar (October 2026, 1-16 crossed as at the hut and the checkpoint), procedure (the boiler's
          board), poster (kitchen), roster (barracks)
  lenses  l_tube, l_globe, l_diff, l_bulb, l_emlens, l_halogen, l_red, l_led, l_fault
python3 main_tex.py [out_dir] -> T_Main_Panel_BaseColor.png / _Emission.png, main_panel_regions.json"""
import os, sys, json, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pxfont as F
import van2_tex as VT
import kpp_tex as KT                                                  # the umlaut glyphs (patched into pxfont on import)
import main_spec as S

N = 1024
INK, WHITE, PAPER = (26, 24, 22), (236, 232, 220), (224, 218, 196)
RED, RED_D, GREEN_S, BLUE_S, YEL = (190, 34, 26), (130, 24, 18), (0, 128, 70), (34, 60, 108), (226, 182, 30)
PENCIL, BLUE_PEN, GREY_T = (84, 80, 92), (40, 52, 120), (96, 92, 86)
SIZES = [('obs_plate', 400, 56), ('tueren', 304, 40), ('befugt', 240, 44), ('garage', 180, 72), ('wohn', 162, 50),
         ('notstrom', 166, 26), ('heiznot', 168, 28), ('kontroll', 142, 40), ('server', 140, 46), ('brand', 142, 44),
         ('hoch', 144, 40), ('technik', 120, 52), ('feuertuer', 116, 24), ('klingel', 104, 24), ('heizoel', 96, 44),
         ('hv_labels', 300, 16), ('main_lbl', 96, 20), ('hv_ug', 72, 24), ('uv_og', 48, 16),
         ('floor_UG', 64, 64), ('floor_EG', 64, 64), ('floor_1OG', 64, 64), ('floor_DACH', 64, 64),
         ('pic_ext', 64, 64), ('pic_call', 64, 64), ('pic_aid', 64, 64), ('pic_nosmoke', 64, 64),
         ('evac_EG', 240, 168), ('evac_OG', 240, 168), ('evac_UG', 240, 168), ('exit', 160, 72),
         ('mimic', 296, 196), ('wb_leit', 336, 216), ('display', 260, 140), ('map', 220, 150),
         ('ctl_front', 120, 360), ('boiler_panel', 176, 70), ('clock', 96, 96), ('mano', 64, 64), ('therm', 64, 64),
         ('thermostat', 48, 48), ('timer', 48, 48), ('crt', 48, 36),
         ('paper_a', 48, 66), ('paper_b', 48, 66), ('paper_c', 48, 66), ('paper_d', 48, 66), ('calendar', 84, 100),
         ('procedure', 60, 76), ('poster', 72, 96), ('roster', 60, 84),
         ('l_tube', 16, 16), ('l_globe', 16, 16), ('l_diff', 16, 16), ('l_bulb', 16, 16), ('l_emlens', 16, 16),
         ('l_halogen', 16, 16), ('l_red', 16, 16), ('l_led', 16, 16), ('l_fault', 16, 16)]


def pack(sizes, n=N, gap=2):
    """shelf packing, tallest first: name -> (x0, y0, x1, y1)"""
    out, x, y, row = {}, 0, 0, 0
    for name, w, h in sorted(sizes, key=lambda t: -t[2]):
        if x + w > n:
            x, y, row = 0, y + row + gap, 0
        out[name] = (x, y, x + w, y + h)
        x += w + gap
        row = max(row, h)
    assert y + row <= n, 'panel full'
    return out


REG = pack(SIZES)


def uv(name, n=N):
    return VT.uv(REG[name], n)


def _plate(img, r, col, rim=None, t=1):
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, col)
    if rim is not None:
        F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, rim, t)


def _age(img, r, seed, spots=18, amount=0.18, col=(120, 100, 70)):
    x0, y0, x1, y1 = r
    rng = np.random.default_rng(seed)
    for _ in range(spots):
        fx, fy = rng.integers(x0 + 1, x1 - 1), rng.integers(y0 + 1, y1 - 1)
        img[fy, fx] = (img[fy, fx] * (1 - amount) + np.array(col) * amount).astype(np.uint8)


def _two(img, r, de, en, fg, sub, big=1, f_de=None, f_en=None):
    """a two-line sign: German (larger) over English"""
    x0, y0, x1, y1 = r
    cx, h = (x0 + x1) / 2, y1 - y0
    f_de = f_de or F.F57
    f_en = f_en or F.F35
    hd = f_de['h'] * big
    he = f_en['h']
    gap = max(2, (h - hd - he) // 3)
    F.text(img, cx, y0 + gap + hd / 2, de, f_de, fg, scale=big)
    F.text(img, cx, y0 + 2 * gap + hd + he / 2, en, f_en, sub)


def _screws(img, r, col=(150, 146, 138)):
    x0, y0, x1, y1 = r
    for sx in (x0 + 4, x1 - 5):
        for sy in (y0 + 4, y1 - 5):
            F.disc(img, sx + 0.5, sy + 0.5, 1.2, col)


# ---------------------------------------------------------------- signs
def draw_signs(img):
    r = REG['obs_plate']                                      # the station's name plate: blue enamel, white letters
    _plate(img, r, BLUE_S, WHITE, 2)
    _two(img, r, 'RADIOOBSERVATORIUM HOHENMOOS', 'RADIO OBSERVATORY', WHITE, (196, 206, 226), big=2, f_en=F.F57)
    _screws(img, r, (180, 188, 200))
    _age(img, r, 101, 60, 0.25, (110, 120, 120))
    r = REG['garage']
    _plate(img, r, BLUE_S, WHITE, 2)
    F.text(img, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, 'GARAGE', F.F57, WHITE, scale=4)
    _screws(img, r, (180, 188, 200))
    _age(img, r, 102, 50, 0.25, (110, 120, 120))
    for name, de, en, bg, rim, fg, sub in (
            ('befugt', 'ZUTRITT NUR FÜR BEFUGTE', 'AUTHORIZED PERSONNEL ONLY', (228, 226, 218), INK, INK, GREY_T),
            ('kontroll', 'KONTROLLRAUM', 'CONTROL ROOM', (228, 226, 218), INK, INK, GREY_T),
            ('server', 'SERVERRAUM', 'SERVER ROOM', (228, 226, 218), INK, INK, GREY_T),
            ('wohn', 'WOHNBEREICH', 'LIVING QUARTERS', (228, 226, 218), INK, INK, GREY_T),
            ('technik', 'TECHNIK', 'UTILITY ROOM', (228, 226, 218), INK, INK, GREY_T),
            ('brand', 'BRANDGEFAHR', 'FLAMMABLE', YEL, INK, INK, (70, 60, 30)),
            ('hoch', 'HOCHSPANNUNG', 'HIGH VOLTAGE', YEL, INK, INK, (70, 60, 30)),
            ('tueren', 'TÜREN NACHTS GESCHLOSSEN HALTEN', 'KEEP DOORS CLOSED AT NIGHT', (232, 230, 222), RED, RED_D, RED),
            ('heizoel', 'HEIZÖL', 'FUEL OIL', YEL, INK, INK, (70, 60, 30)),
            ('klingel', 'BITTE KLINGELN', 'PLEASE RING', WHITE, INK, INK, GREY_T),
            ('notstrom', 'NOTSTROM-EINSPEISUNG', 'GENERATOR FEED', (232, 150, 30), INK, INK, (60, 40, 20)),
            ('feuertuer', 'FEUERSCHUTZTÜR', 'GESCHLOSSEN HALTEN', WHITE, INK, INK, GREY_T),
            ('heiznot', 'HEIZUNG NOTSCHALTER', 'HEATING EMERGENCY STOP', RED, WHITE, WHITE, (246, 214, 208))):
        r = REG[name]
        _plate(img, r, bg, rim)
        h = r[3] - r[1]
        big = 2 if (h >= 50 and name in ('wohn', 'technik')) else 1
        if name == 'feuertuer':                                   # two German lines: the door sticker
            _two(img, r, de, en, fg, fg, f_en=F.F35, f_de=F.F35)
        else:
            _two(img, r, de, en, fg, sub, big=big)
        _age(img, r, hash(name) % 997, 10 + (r[2] - r[0]) // 10, 0.2)
    for name, txt in (('floor_UG', 'UG'), ('floor_EG', 'EG'), ('floor_1OG', '1. OG'), ('floor_DACH', 'DACH')):
        r = REG[name]
        _plate(img, r, (20, 20, 20), (200, 200, 196))
        F.text(img, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, txt, F.F57, (236, 236, 232), scale=4 if len(txt) <= 2 else 2)
    for name, txt in (('uv_og', 'UV-OG'), ('hv_ug', 'HV-UG')):
        r = REG[name]
        _plate(img, r, WHITE, INK)
        F.text(img, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, txt, F.F57 if r[3] - r[1] >= 20 else F.F35, INK,
               scale=2 if r[3] - r[1] >= 24 else 1)
    r = REG['main_lbl']
    _plate(img, r, RED, WHITE)
    F.text(img, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, 'MAIN SWITCH', F.F57, WHITE)
    r = REG['hv_labels']                                      # the six lever switches of HV-UG (English, equipment)
    x0, y0, x1, y1 = r
    labels = ['EG LIGHT', 'EG POWER', 'OG LIGHT', 'OG POWER', 'UG HEAT', 'SERVER']
    w = (x1 - x0) / 6
    for i, t in enumerate(labels):
        a = x0 + i * w
        F.rect(img, a + 1, y0, a + w - 2, y1 - 1, (232, 228, 214))
        F.frame(img, a + 1, y0, a + w - 2, y1 - 1, (120, 112, 96))
        F.text(img, a + w / 2, (y0 + y1) / 2, t, F.F35, INK)


def draw_pictos(img):
    r = REG['pic_ext']                                        # F001: red square, white extinguisher and flame
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, RED)
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, WHITE)
    F.rect(img, x0 + 34, y0 + 22, x0 + 44, y0 + 54, WHITE)
    F.rect(img, x0 + 37, y0 + 16, x0 + 41, y0 + 22, WHITE)
    F.line(img, x0 + 41, y0 + 18, x0 + 50, y0 + 26, WHITE, 2)
    for k, (dx, h) in enumerate(((10, 18), (16, 26), (22, 14))):
        F.rect(img, x0 + dx, y0 + 54 - h, x0 + dx + 4, y0 + 54, WHITE)
    F.rect(img, x0 + 8, y0 + 54, x0 + 30, y0 + 55, WHITE)
    r = REG['pic_call']                                       # F005: red square, the call point with a pressing hand
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, RED)
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, WHITE)
    F.frame(img, x0 + 14, y0 + 12, x0 + 44, y0 + 42, WHITE, 2)
    F.disc(img, x0 + 29, y0 + 27, 6, WHITE)
    F.rect(img, x0 + 34, y0 + 36, x0 + 52, y0 + 44, WHITE)
    F.rect(img, x0 + 30, y0 + 30, x0 + 36, y0 + 38, WHITE)
    for k in range(4):
        F.line(img, x0 + 10 + k * 4, y0 + 50, x0 + 6 + k * 4, y0 + 56, WHITE, 1)
    r = REG['pic_aid']                                        # E003: green square, the white cross
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, GREEN_S)
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, WHITE)
    F.rect(img, x0 + 26, y0 + 12, x0 + 37, y0 + 51, WHITE)
    F.rect(img, x0 + 12, y0 + 26, x0 + 51, y0 + 37, WHITE)
    r = REG['pic_nosmoke']                                    # P002: white disc, red ring and bar, the cigarette
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, WHITE)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    F.rect(img, x0 + 12, cy - 3, x0 + 44, cy + 3, INK)
    F.rect(img, x0 + 45, cy - 3, x0 + 50, cy + 3, (200, 120, 60))
    for k in range(3):
        F.line(img, x0 + 52 + k, cy - 8 - k * 3, x0 + 49 + k, cy - 14 - k * 3, (140, 140, 140))
    F.ring(img, cx, cy, 25, 30, RED)
    F.line(img, cx - 19, cy - 19, cx + 19, cy + 19, RED, 5)
    r = REG['exit']                                           # the exit sign's face (green, the running man, arrow)
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (20, 190, 90))
    F.frame(img, x0 + 2, y0 + 2, x1 - 3, y1 - 3, (230, 255, 236))
    F.rect(img, x0 + 8, y0 + 8, x0 + 56, y0 + 63, (230, 255, 236))
    m = (20, 190, 90)
    F.disc(img, x0 + 36, y0 + 16, 5, m)
    F.line(img, x0 + 34, y0 + 22, x0 + 28, y0 + 40, m, 5)
    F.line(img, x0 + 28, y0 + 40, x0 + 40, y0 + 56, m, 4)
    F.line(img, x0 + 28, y0 + 40, x0 + 18, y0 + 56, m, 4)
    F.line(img, x0 + 33, y0 + 26, x0 + 44, y0 + 34, m, 3)
    F.line(img, x0 + 31, y0 + 26, x0 + 20, y0 + 32, m, 3)
    F.rect(img, x0 + 70, y0 + 31, x0 + 122, y0 + 40, (230, 255, 236))
    for k in range(14):
        F.rect(img, x0 + 122 + k, y0 + 22 + k, x0 + 123 + k, y0 + 49 - k, (230, 255, 236))
    F.text(img, x0 + 104, y0 + 60, 'NOTAUSGANG', F.F35, (230, 255, 236))


def draw_evac(img):
    """FLUCHT- UND RETTUNGSPLAN per floor: the floor's rooms from main_spec, escape routes in green, extinguishers and
    call points in red, 'you are here' at the plan's place (Update 3: corridor north wall, x -1.3)"""
    for lvl, name, title in (('EG', 'evac_EG', 'ERDGESCHOSS'), ('OG', 'evac_OG', '1. OBERGESCHOSS'),
                             ('UG', 'evac_UG', 'UNTERGESCHOSS')):
        r = REG[name]
        x0, y0, x1, y1 = r
        F.rect(img, x0, y0, x1 - 1, y1 - 1, (240, 240, 234))
        F.rect(img, x0, y0, x1 - 1, y0 + 10, GREEN_S)
        F.text(img, x0 + 3, y0 + 3, 'FLUCHT- UND RETTUNGSPLAN', F.F35, WHITE, align='l', valign='t')
        F.text(img, x1 - 3, y0 + 3, title, F.F35, WHITE, align='r', valign='t')
        # plan area: x -18.2..8.2 (garage on EG), y -6.2..7.2
        px0, py0, px1, py1 = x0 + 6, y0 + 14, x1 - 6, y1 - 34
        X0, X1, Y0, Y1 = (-18.2, 8.2, -6.4, 7.2) if lvl == 'EG' else (-8.4, 8.2, -6.4, 7.2)
        sc = min((px1 - px0) / (X1 - X0), (py1 - py0) / (Y1 - Y0))
        ox = px0 + ((px1 - px0) - sc * (X1 - X0)) / 2

        def P(x, y):
            return ox + (x - X0) * sc, py1 - (y - Y0) * sc
        for rn, R in S.ROOMS.items():
            if R['level'] != lvl and not (rn == 'Treppenhaus'):
                continue
            a, b = P(R['x0'], R['y1']), P(R['x1'], R['y0'])
            col = (226, 238, 226) if rn.startswith('Flur') or rn in ('Treppenhaus', 'Windfang') else (250, 250, 246)
            F.rect(img, a[0], a[1], b[0], b[1], col)
            F.frame(img, a[0], a[1], b[0], b[1], INK)
        # escape arrows along the corridor to the exits
        cy_ = P(0, 0)[1]
        for xa, xb in ((-1.0, -6.5), (1.0, 7.0)):
            pa, pb = P(xa, 0), P(xb, 0)
            F.line(img, pa[0], cy_, pb[0], cy_, (0, 150, 80), 2)
            d = 1 if xb > xa else -1
            for k in range(4):
                F.rect(img, pb[0] - d * k, cy_ - (3 - k), pb[0] - d * k, cy_ + (3 - k), (0, 150, 80))
        yh = P(-1.3, 0.95)
        F.disc(img, yh[0], yh[1], 2.5, (0, 120, 60))                    # you are here
        F.ring(img, yh[0], yh[1], 3.5, 4.5, (0, 120, 60))
        for (ex, ey) in {'EG': [(7.28, -0.9), (-5.25, -2.12)], 'OG': [(-0.91, -0.9)], 'UG': [(3.40, -1.2)]}[lvl]:
            q = P(ex, ey)
            F.rect(img, q[0] - 1.5, q[1] - 1.5, q[0] + 1.5, q[1] + 1.5, RED)
        # the legend
        ly = y1 - 30
        for i, (c, de, en) in enumerate(((GREEN_S, 'FLUCHTWEG', 'ESCAPE ROUTE'), (RED, 'BRANDSCHUTZ', 'FIRE EQUIPMENT'),
                                         ((0, 120, 60), 'STANDORT', 'YOU ARE HERE'))):
            F.rect(img, x0 + 4, ly + i * 9, x0 + 9, ly + i * 9 + 5, c)
            F.text(img, x0 + 12, ly + i * 9, de + ' / ' + en, F.F35, INK, align='l', valign='t')
        F.rect(img, x0 + 130, ly - 2, x1 - 5, y1 - 4, (250, 236, 232))
        F.frame(img, x0 + 130, ly - 2, x1 - 5, y1 - 4, RED)
        F.text(img, x0 + 134, ly + 1, 'IM BRANDFALL:', F.F35, RED, align='l', valign='t')
        F.text(img, x0 + 134, ly + 9, 'RUHE BEWAHREN', F.F35, INK, align='l', valign='t')
        F.text(img, x0 + 134, ly + 17, 'BRAND MELDEN 112', F.F35, INK, align='l', valign='t')
        _age(img, r, 120 + len(lvl), 30, 0.12)


# ---------------------------------------------------------------- devices
def _dial(img, r, lo, hi, step, label, red_from=None, face=(236, 234, 226), rim=(30, 30, 30)):
    """a round dial in a black square: 270 deg scale from lo to hi (the needle part turns 0..270 over it)"""
    x0, y0, x1, y1 = r
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    R = (x1 - x0) / 2
    F.rect(img, x0, y0, x1 - 1, y1 - 1, rim)
    F.disc(img, cx, cy, R - 1.5, face)
    a0 = 225.0                                                # the 0 at 7:30, clockwise to 4:30 (270 deg)
    n = int(round((hi - lo) / step))
    for i in range(n + 1):
        ang = a0 - 270.0 * i / n
        F.tick(img, cx, cy, R - 7, R - 3, 90 - ang, INK, 1)
        if R > 20:
            v = lo + i * step
            p = (cx + math.cos(math.radians(ang)) * (R - 13), cy - math.sin(math.radians(ang)) * (R - 13))
            F.text(img, p[0], p[1], ('%g' % v), F.F35, INK)
    if red_from is not None:
        for k in range(30):
            v = red_from + (hi - red_from) * k / 29
            ang = a0 - 270.0 * (v - lo) / (hi - lo)
            F.tick(img, cx, cy, R - 4, R - 2, 90 - ang, RED, 1)
    F.text(img, cx, cy + R * 0.45, label, F.F35, GREY_T)


def draw_devices(img, emi):
    r = REG['clock']                                          # the station's clocks stopped at 2:40 (the checkpoint's)
    x0, y0, x1, y1 = r
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    R = (x1 - x0) / 2
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (20, 20, 20))
    F.disc(img, cx, cy, R - 0.5, (232, 230, 222))
    for h in range(12):
        F.tick(img, cx, cy, R - 9 if h % 3 == 0 else R - 7, R - 3, h * 30, INK, 2 if h % 3 == 0 else 1)
    F.tick(img, cx, cy, 0, R * 0.52, 2 * 30 + 40 * 0.5, INK, 3)
    F.tick(img, cx, cy, 0, R * 0.78, 40 * 6, INK, 2)
    F.disc(img, cx, cy, 2, INK)
    F.text(img, cx, cy + R * 0.42, 'SIEMENS', F.F35, GREY_T)
    _dial(img, REG['mano'], 0, 4, 1, 'BAR', red_from=3.0)
    _dial(img, REG['therm'], 0, 120, 20, 'C')
    _dial(img, REG['thermostat'], 5, 30, 5, '', face=(214, 212, 204))
    r = REG['timer']                                          # the controller's time switch: a 24 h dial with pins
    x0, y0, x1, y1 = r
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (60, 62, 60))
    F.disc(img, cx, cy, 21, (226, 222, 210))
    for h in range(24):
        F.tick(img, cx, cy, 15, 20, h * 15, (60, 60, 60) if h % 6 else RED, 1)
    for h in (6, 7, 8, 17, 18, 19, 20, 21):
        F.tick(img, cx, cy, 20, 23, h * 15, (40, 90, 160), 2)
    F.text(img, cx, cy, '24H', F.F35, INK)
    r = REG['ctl_front']                                      # the heating controller's front (0.48 x 1.48 m, ~243 px /
    x0, y0, x1, y1 = r                                        # m): Update 3's PUMPE / BRENNER / STÖRUNG labels, German
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (196, 190, 170))      # over English, at the controls (x 0.76 / 0.86 / 0.96 / 1.06)
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, (120, 116, 100))
    F.rect(img, x0 + 8, y0 + 8, x1 - 9, y0 + 30, (60, 62, 60))
    F.text(img, (x0 + x1) / 2, y0 + 14, 'HEIZUNG', F.F57, (230, 226, 210))
    F.text(img, (x0 + x1) / 2, y0 + 24, 'HEATING CONTROL', F.F35, (200, 196, 180))
    F.rect(img, x0 + 8, y0 + 150, x1 - 9, y0 + 252, (40, 44, 46))                      # the window (relays behind)
    for k in range(4):
        F.rect(img, x0 + 14 + k * 24, y0 + 166, x0 + 30 + k * 24, y0 + 214, (90, 92, 88))
        F.rect(img, x0 + 16 + k * 24, y0 + 170, x0 + 28 + k * 24, y0 + 178, (200, 150, 40))
    tx = lambda xm: x0 + (xm - 0.66) / 0.48 * (x1 - x0)
    F.disc(img, tx(0.90), y1 - 75, 19, (60, 62, 60))                                     # the time switch's bezel
    for (xm, de, en, row) in ((0.76, 'PUMPE', 'PUMP', 0), (0.86, 'BRENNER', 'BURNER', 1), (0.96, 'STÖRUNG', 'FAULT', 0),
                              (1.06, 'THERMOST.', '5-30 C', 1)):
        yy = y1 - 50 + row * 13
        F.text(img, tx(xm), yy, de, F.F35, RED_D if de == 'STÖRUNG' else INK)
        F.text(img, tx(xm), yy + 6, en, F.F35, GREY_T)
        F.line(img, tx(xm), yy + 9 + (1 - row) * 0, tx(xm), y1 - 20, (120, 116, 100), 1)
    for xm in (0.76, 0.86):
        F.rect(img, tx(xm) - 5, y1 - 19, tx(xm) + 4, y1 - 8, (30, 30, 30))               # the rockers' bezels
    F.disc(img, tx(0.96), y1 - 13, 5, (60, 20, 18))                                        # the lamp's bezel
    F.disc(img, tx(1.06), y1 - 13, 8, (214, 212, 204))
    for k in range(6):
        F.tick(img, tx(1.06), y1 - 13, 6, 8, 225 - 54 * k, INK, 1)
    F.text(img, (x0 + x1) / 2, y0 + 44, 'FÜLLEN AM KESSEL', F.F35, INK)
    F.text(img, (x0 + x1) / 2, y0 + 52, 'FILL TAP AT THE BOILER', F.F35, GREY_T)
    _age(img, r, 140, 60, 0.15)
    r = REG['boiler_panel']
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (70, 72, 70))
    F.text(img, (x0 + x1) / 2, y0 + 8, 'VIESSMANN  VITOLA', F.F35, (220, 216, 200))
    F.text(img, x0 + 28, y1 - 10, 'KESSEL C', F.F35, (220, 216, 200))
    F.text(img, x0 + 28, y1 - 4, 'BOILER C', F.F35, (170, 166, 150))
    F.rect(img, x0 + 120, y0 + 28, x0 + 160, y0 + 40, (30, 30, 30))
    F.text(img, x0 + 140, y0 + 48, 'NETZ / MAINS', F.F35, (220, 216, 200))
    r = REG['crt']
    F.rect(img, r[0], r[1], r[2] - 1, r[3] - 1, (18, 24, 22))
    F.rect(img, r[0] + 4, r[1] + 4, r[0] + 14, r[1] + 8, (34, 44, 40))


def draw_boards(img):
    r = REG['mimic']                                          # the Schaltraum's wiring board (single-line, English)
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (234, 234, 228))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (150, 150, 146))
    F.text(img, (x0 + x1) / 2, y0 + 8, 'POWER SUPPLY - MAIN BUILDING', F.F57, INK)
    F.rect(img, x0 + 12, y0 + 24, x0 + 76, y0 + 50, (250, 250, 246))
    F.frame(img, x0 + 12, y0 + 24, x0 + 76, y0 + 50, INK)
    F.text(img, x0 + 44, y0 + 32, 'GENERATOR', F.F35, INK)
    F.text(img, x0 + 44, y0 + 41, '400 V 3~', F.F35, INK)
    F.rect(img, x0 + 12, y0 + 60, x0 + 76, y0 + 86, (250, 250, 246))
    F.frame(img, x0 + 12, y0 + 60, x0 + 76, y0 + 86, INK)
    F.text(img, x0 + 44, y0 + 68, 'GRID', F.F35, INK)
    F.text(img, x0 + 44, y0 + 77, '(OFF)', F.F35, RED)
    F.line(img, x0 + 76, y0 + 37, x0 + 110, y0 + 37, INK, 2)
    F.line(img, x0 + 76, y0 + 73, x0 + 96, y0 + 73, (160, 160, 156), 1)
    F.rect(img, x0 + 110, y0 + 26, x0 + 150, y0 + 48, (250, 236, 232))
    F.frame(img, x0 + 110, y0 + 26, x0 + 150, y0 + 48, RED)
    F.text(img, x0 + 130, y0 + 33, 'MAIN', F.F35, RED_D)
    F.text(img, x0 + 130, y0 + 41, 'SWITCH', F.F35, RED_D)
    F.line(img, x0 + 150, y0 + 37, x0 + 172, y0 + 37, INK, 2)
    F.rect(img, x0 + 172, y0 + 24, x0 + 176, y1 - 20, INK)                              # the busbar
    feeds = ['EG LIGHT', 'EG POWER', 'OG LIGHT', 'OG POWER', 'UG HEAT', 'SERVER', 'UV-OG', 'PUMPS']
    for i, t in enumerate(feeds):
        y = y0 + 30 + i * 19
        F.line(img, x0 + 176, y, x0 + 206, y, INK, 1)
        F.frame(img, x0 + 206, y - 5, x0 + 214, y + 5, INK)
        F.line(img, x0 + 214, y, x0 + 226, y, INK, 1)
        F.text(img, x0 + 230, y, t, F.F35, INK, align='l')
    _age(img, r, 150, 80, 0.10)
    r = REG['wb_leit']                                        # the control room's whiteboard: the last shift's notes
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (238, 240, 238))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (170, 172, 172))
    hand = [(10, 'SCHICHT 14.10.  KESSLER / ALBERS', BLUE_PEN), (24, 'ANT. 3 AZIMUT HAENGT - NOVAK FRAGEN', BLUE_PEN),
            (38, 'BAENDER 14-22 NACH BONN', INK), (52, 'GENERATOR: DIESEL BESTELLEN!', RED_D),
            (70, 'NACHTS NIEMANDEN REINLASSEN', RED_D), (84, 'AUCH WENN ER RUFT', RED_D)]
    for y, t, c in hand:
        F.text(img, x0 + 10, y0 + y, t, F.F35, c, align='l', valign='t')
    for k in range(17):                                       # tally marks, in fives
        bx = x0 + 10 + (k // 5) * 26 + (k % 5) * 4
        if k % 5 == 4:
            F.line(img, bx - 16, y0 + 112, bx + 1, y0 + 104, INK, 1)
        else:
            F.line(img, bx, y0 + 102, bx, y0 + 114, INK, 1)
    F.text(img, x0 + 120, y0 + 104, 'TAGE OHNE KONTAKT', F.F35, INK, align='l', valign='t')
    for k in range(30):                                        # a half-wiped sketch of the antenna field
        a = k / 29 * math.pi
        F.rect(img, x0 + 250 + math.cos(a) * 30, y0 + 150 - math.sin(a) * 24, x0 + 250 + math.cos(a) * 30,
               y0 + 150 - math.sin(a) * 24, (120, 130, 150))
    _age(img, r, 151, 120, 0.08, (180, 184, 190))
    r = REG['display']                                        # the antenna-field mimic on the partition
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (34, 40, 44))
    F.text(img, (x0 + x1) / 2, y0 + 8, 'ANTENNENFELD / ANTENNA FIELD', F.F35, (200, 204, 196))
    for i in range(5):
        cx = x0 + 30 + i * 50
        cy = y0 + 70
        F.ring(img, cx, cy, 10, 13, (190, 196, 200), 200, 340)
        F.line(img, cx, cy, cx, cy + 20, (190, 196, 200))
        F.line(img, cx, cy + 22, cx, y1 - 22, (90, 160, 90))
        F.disc(img, cx + 16, cy - 12, 3, (60, 70, 60))
        F.text(img, cx, cy + 34, 'ANT %d' % (i + 1), F.F35, (200, 204, 196))
    F.line(img, x0 + 30, y1 - 22, x0 + 230, y1 - 22, (90, 160, 90), 2)
    F.text(img, (x0 + x1) / 2, y1 - 12, 'LEITSTAND', F.F35, (200, 204, 196))
    r = REG['map']                                            # the topographic map on the map table
    x0, y0, x1, y1 = r
    yy, xx = np.mgrid[y0:y1, x0:x1]
    from noise import fbm
    pts = np.stack([xx.ravel() / 60.0, yy.ravel() / 60.0, np.zeros(xx.size)], -1).astype(np.float32)
    h = fbm(pts, 1.0, 4, seed=77).reshape(xx.shape)
    base = np.where(h[..., None] > 0.55, np.array((150, 170, 120)), np.array((176, 196, 140)))
    contour = (np.abs(((h * 14) % 1.0) - 0.5) < 0.06)
    img[y0:y1, x0:x1] = np.where(contour[..., None], np.array((150, 110, 70)), base).astype(np.uint8)
    F.line(img, x0 + 10, y0 + 120, x0 + 200, y0 + 30, (200, 60, 40), 1)                  # the road
    F.rect(img, x0 + 150, y0 + 40, x0 + 160, y0 + 50, INK)                               # the station
    F.text(img, x0 + 155, y0 + 58, 'STATION', F.F35, INK)
    F.ring(img, x0 + 155, y0 + 45, 22, 23, (200, 40, 30))
    F.text(img, x0 + 50, y0 + 12, 'HOHENMOOS 1:25000', F.F35, INK)
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (120, 110, 90))


def draw_papers(img):
    rng = np.random.default_rng(160)
    for name in ('paper_a', 'paper_b', 'paper_c', 'paper_d'):
        r = REG[name]
        x0, y0, x1, y1 = r
        F.rect(img, x0, y0, x1 - 1, y1 - 1, PAPER if name != 'paper_d' else (236, 228, 190))
        F.rect(img, x0 + 4, y0 + 4, x0 + 30, y0 + 6, INK)
        for k in range(y0 + 12, y1 - 6, 4):
            w = int(rng.integers(16, 40))
            F.rect(img, x0 + 4, k, x0 + 4 + w, k, (110, 106, 100))
        _age(img, r, int(rng.integers(0, 999)), 12, 0.15)
    r = REG['calendar']                                       # October 2026 (the 1st a Thursday), 1-16 crossed out
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (232, 228, 214))
    F.rect(img, x0 + 2, y0 + 2, x1 - 3, y0 + 30, (120, 140, 160))
    F.rect(img, x0 + 2, y0 + 22, x1 - 3, y0 + 30, (60, 80, 60))
    F.text(img, (x0 + x1) / 2, y0 + 36, 'OKTOBER', F.F35, (150, 30, 24))
    cw = (x1 - x0 - 2) / 7.0
    for day in range(1, 32):
        cell = 3 + day - 1
        row, colm = cell // 7, cell % 7
        cx = x0 + 1 + cw * (colm + 0.5)
        cy = y0 + 48 + row * 10
        F.text(img, cx, cy, str(day), F.F35, (150, 30, 24) if colm == 6 else INK)
        if day <= 16:
            F.line(img, cx - 3, cy + 2, cx + 3, cy - 2, PENCIL)
    r = REG['procedure']                                      # the boiler's board: Novak's procedure (as the note)
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (236, 232, 214))
    F.text(img, (x0 + x1) / 2, y0 + 5, 'HEIZUNG', F.F35, INK)
    for i, t in enumerate(('1 NOT-AUS EIN', '2 DRUCK 1,5 BAR', '3 PUMPE EIN', '4 BRENNER EIN', '  STOERUNG?', '  RESET DRUECKEN',
                           '5 THERMOSTAT 20')):
        F.text(img, x0 + 3, y0 + 13 + i * 8, t, F.F35, BLUE_PEN if i in (4, 5) else INK, align='l', valign='t')
    r = REG['poster']                                         # the kitchen poster: a 70s safety poster
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (230, 196, 60))
    F.rect(img, x0 + 4, y0 + 18, x1 - 5, y1 - 22, (240, 236, 220))
    F.disc(img, (x0 + x1) / 2, y0 + 48, 16, (200, 60, 40))
    F.rect(img, (x0 + x1) / 2 - 2, y0 + 36, (x0 + x1) / 2 + 1, y0 + 52, WHITE)
    F.rect(img, (x0 + x1) / 2 - 2, y0 + 55, (x0 + x1) / 2 + 1, y0 + 58, WHITE)
    F.text(img, (x0 + x1) / 2, y0 + 9, 'VORSICHT', F.F57, INK)
    F.text(img, (x0 + x1) / 2, y1 - 15, 'HEISSE PLATTE', F.F35, INK)
    F.text(img, (x0 + x1) / 2, y1 - 7, 'HOT PLATE', F.F35, GREY_T)
    r = REG['roster']                                         # the barracks' duty roster
    x0, y0, x1, y1 = r
    F.rect(img, x0, y0, x1 - 1, y1 - 1, PAPER)
    F.text(img, (x0 + x1) / 2, y0 + 5, 'DIENSTPLAN', F.F35, INK)
    for k in range(y0 + 12, y1 - 3, 8):
        F.rect(img, x0 + 2, k, x1 - 3, k, (176, 186, 196))
    for i, (d, who) in enumerate((('12.10', 'KESSLER'), ('13.10', 'ALBERS'), ('14.10', 'NOVAK'), ('15.10', 'KESSLER'),
                                  ('16.10', 'ALBERS'), ('17.10', ''), ('18.10', ''))):
        y = y0 + 14 + i * 8
        F.text(img, x0 + 3, y, d, F.F35, INK, align='l', valign='t')
        F.text(img, x0 + 25, y, who, F.F35, BLUE_PEN, align='l', valign='t')
    _age(img, r, 161, 20)


def draw_lenses(img, emi):
    for name, base, glow in (('l_tube', (238, 240, 236), (255, 255, 250)), ('l_globe', (226, 214, 190), (255, 214, 150)),
                             ('l_diff', (232, 232, 226), (250, 250, 244)), ('l_bulb', (240, 226, 190), (255, 210, 140)),
                             ('l_emlens', (236, 236, 228), (255, 252, 236)), ('l_halogen', (220, 220, 214), (255, 224, 170)),
                             ('l_red', (150, 20, 16), (255, 40, 24)), ('l_led', (40, 120, 50), (60, 255, 90)),
                             ('l_fault', (120, 18, 14), (255, 36, 20))):
        r = REG[name]
        F.rect(img, r[0], r[1], r[2] - 1, r[3] - 1, base)
        F.rect(emi, r[0], r[1], r[2] - 1, r[3] - 1, glow)
    r = REG['exit']
    sub = img[r[1]:r[3], r[0]:r[2]]
    emi[r[1]:r[3], r[0]:r[2]] = sub                             # the exit sign glows as it is printed


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (128, 128, 128)
    emi = np.zeros((N, N, 3), np.uint8)
    draw_signs(img)
    draw_pictos(img)
    draw_evac(img)
    draw_devices(img, emi)
    draw_boards(img)
    draw_papers(img)
    draw_lenses(img, emi)
    pb = os.path.join(out, 'T_Main_Panel_BaseColor.png')
    pe = os.path.join(out, 'T_Main_Panel_Emission.png')
    Image.fromarray(img, 'RGB').save(pb)
    Image.fromarray(emi, 'RGB').save(pe)
    json.dump({k: list(v) for k, v in REG.items()}, open(os.path.join(out, 'main_panel_regions.json'), 'w'), indent=0)
    return pb, pe


if __name__ == '__main__':
    o = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'main')
    print(build(o))
