"""Panel atlas of forest_devices (512 x 512, pixel art, point filter) on the explicit-UV faces: the fax's control panel
(keypad, START / STOP, the LCD frame), the PC keyboard and the laptop keyboard (key legends in the 3 x 5 font), the PC's
front bezel (floppy, drive blank, POWER / TURBO / RESET, a 486DX2 sticker), the telemetry cassette's label (window, reels),
the tape box's labels, the drop box's plate (KASSETTEN / TAPES - German first, English under); emission tiles: the fax LCD,
the green and red LEDs. Equipment labels in English. Also the fax paper (its own 256 x 362 texture, blank thermal paper:
the game prints on it).  python3 devices_tex.py [out_dir]"""
import os, sys, json, math
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxfont as F
import van2_tex as VT

HERE = os.path.dirname(os.path.abspath(__file__))
N = 512
REG = {'fax_panel': (0, 0, 200, 100), 'kbd': (0, 104, 280, 216), 'lap_kbd': (284, 104, 444, 176),
       'cass_label': (204, 0, 284, 52), 'cbox_front': (288, 0, 416, 44), 'cbox_top': (288, 48, 416, 100),
       'drop_plate': (420, 0, 512, 46), 'pc_front': (0, 220, 168, 276), 'fax_lcd': (172, 220, 236, 236),
       'led_green': (240, 220, 256, 236), 'led_red': (260, 220, 276, 236), 'screen_off': (284, 180, 348, 228),
       'btn_green': (124, 55, 138, 61), 'btn_red': (164, 55, 178, 61),    # solid tiles inside the START / STOP wells
       'deck_front': (0, 280, 240, 350), 'key_grey': (250, 280, 262, 290), 'key_red': (266, 280, 278, 290),
       'therm_dry': (300, 280, 316, 440), 'therm_wet': (320, 280, 336, 440), 'therm_max': (340, 280, 356, 440),
       'therm_min': (360, 280, 376, 440), 'chart': (380, 280, 476, 312), 'enamel': (250, 296, 262, 306)}
DECK_PX = (240, 70)                       # the tape deck's faceplate: 0.94 x 0.27 m
DECK_HOLE = (16, 20, 45, 40)              # the cassette opening (px, left top right bottom) - cut out of the faceplate
DECK_KEYS = [(56 + 15 * i, 30, 68 + 15 * i, 38) for i in range(5)]   # REC, PLAY, REW, FF, STOP / EJECT
THERM = dict(lo=-40.0, hi=50.0, y_hi=14, y_lo=148, read={'therm_dry': -12.0, 'therm_wet': -13.0, 'therm_max': -6.0,
                                                          'therm_min': -19.0})
INK, WHITE = (24, 24, 22), (232, 228, 216)
BEIGE, BEIGE_D, BEIGE_L = (196, 186, 160), (150, 142, 120), (214, 206, 182)
DARK, DARK2 = (44, 44, 46), (66, 66, 68)


def uv(name, n=N):
    return VT.uv(REG[name], n)


def _keys(img, x0, y0, rows, kw, kh, gap, face, edge, legend, legends=None, font=F.F35):
    """a grid of keys: rows = [(x offset in key units, [width in key units, ...]), ...]"""
    legends = legends or []
    for r, (xo, widths) in enumerate(rows):
        x = x0 + xo * kw
        y = y0 + r * kh
        for i, w in enumerate(widths):
            ww = int(round(w * kw)) - gap
            F.rect(img, x, y, x + ww - 1, y + kh - gap - 1, edge)
            F.rect(img, x + 1, y + 1, x + ww - 2, y + kh - gap - 3, face)
            if r < len(legends) and i < len(legends[r]) and legends[r][i]:
                F.text(img, x + ww / 2 - 0.5, y + (kh - gap) / 2 - 1, legends[r][i], font, legend)
            x += int(round(w * kw))


def draw_fax(img, emi):
    x0, y0, x1, y1 = REG['fax_panel']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (186, 182, 170))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (150, 146, 136))
    # the LCD bezel (the LCD itself is its own object)
    F.rect(img, x0 + 8, y0 + 8, x0 + 92, y0 + 30, (60, 62, 60))
    F.text(img, x0 + 50, y0 + 37, 'TELEFAX', F.F35, (90, 90, 86))
    # keypad 3 x 4 (* and # drawn by hand)
    legends = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'], ['', '0', '']]
    _keys(img, x0 + 8, y0 + 44, [(0, [1, 1, 1])] * 4, 16, 13, 2, (214, 210, 198), (120, 118, 110), INK, legends)
    for (kx, ch) in ((x0 + 8, '*'), (x0 + 40, '#')):
        cx, cy = kx + 7, y0 + 44 + 3 * 13 + 5
        if ch == '*':
            for dx, dy in ((0, 0), (-1, -1), (1, 1), (-1, 1), (1, -1)):
                img[cy + dy, cx + dx] = INK
        else:
            for d in (-1, 1):
                img[cy - 2:cy + 3, cx + d] = INK
                img[cy + d, cx - 2:cx + 3] = INK
    # function keys and their labels (English)
    for i, lab in enumerate(['COPY', 'TEL', 'AUTO', 'MEMO']):
        kx, ky = x0 + 62, y0 + 44 + i * 13
        F.rect(img, kx, ky, kx + 28, ky + 10, (120, 118, 110))
        F.rect(img, kx + 1, ky + 1, kx + 27, ky + 8, (200, 196, 184))
        F.text(img, kx + 14, ky + 4.5, lab, F.F35, INK)
    # START (green) and STOP (red) - the keys are separate parts; here the wells and the labels
    for (kx, lab, col) in ((x0 + 120, 'START', (60, 120, 70)), (x0 + 160, 'STOP', (150, 50, 40))):
        F.rect(img, kx - 2, y0 + 50, kx + 24, y0 + 66, (110, 108, 100))
        F.rect(img, kx, y0 + 52, kx + 22, y0 + 64, col)
        F.text(img, kx + 11, y0 + 72, lab, F.F35, INK)
    F.text(img, x0 + 150, y0 + 14, 'READY', F.F35, INK)
    F.disc(img, x0 + 130, y0 + 14, 2, (40, 60, 40))
    F.text(img, x0 + 150, y0 + 26, 'ERROR', F.F35, INK)
    F.disc(img, x0 + 130, y0 + 26, 2, (60, 40, 40))
    F.text(img, x0 + 140, y0 + 88, 'DOCUMENT FACE DOWN', F.F35, (90, 90, 86))
    # the LCD tile: dim segments, greenish
    lx0, ly0, lx1, ly1 = REG['fax_lcd']
    F.rect(img, lx0, ly0, lx1 - 1, ly1 - 1, (70, 86, 64))
    F.rect(emi, lx0, ly0, lx1 - 1, ly1 - 1, (34, 52, 30))
    F.text(img, (lx0 + lx1) / 2, (ly0 + ly1) / 2 - 0.5, 'READY 07:30', F.F35, (40, 52, 38))
    F.text(emi, (lx0 + lx1) / 2, (ly0 + ly1) / 2 - 0.5, 'READY 07:30', F.F35, (150, 230, 140))
    for key, col in (('led_green', (90, 255, 110)), ('led_red', (255, 70, 50))):
        a0, b0, a1, b1 = REG[key]
        F.rect(img, a0, b0, a1 - 1, b1 - 1, tuple(int(c * 0.35) for c in col))
        F.disc(emi, (a0 + a1) // 2, (b0 + b1) // 2, 6, col)


def draw_keyboard(img):
    x0, y0, x1, y1 = REG['kbd']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, BEIGE_D)
    kw, kh = 14, 15
    main = [(0.0, [1] + [1] * 12 + [2]), (0.0, [1.5] + [1] * 12 + [1.5]), (0.0, [1.8] + [1] * 11 + [2.2]),
            (0.0, [2.3] + [1] * 10 + [2.7]), (0.0, [1.5, 1.2, 7.0, 1.2, 1.5])]
    legends = [['ESC', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '<-'],
               ['TAB', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '(', ')', ''],
               ['CAP', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', "'", 'ENT'],
               ['SHIFT', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/', 'SHIFT'],
               ['CTL', 'ALT', '', 'ALT', 'CTL']]
    _keys(img, x0 + 4, y0 + 22, main, kw, kh, 2, BEIGE_L, (120, 112, 92), INK, legends)
    fkeys = [(0.0, [1] * 12)]
    _keys(img, x0 + 4, y0 + 3, fkeys, kw * 1.08, 14, 3, BEIGE_L, (120, 112, 92), INK,
          [['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12']])
    _keys(img, x0 + 214, y0 + 22, [(0, [1, 1, 1, 1]), (0, [1, 1, 1, 1]), (0, [1, 1, 1, 1]), (0, [1, 1, 1, 1]), (0, [2, 1, 1])],
          kw, kh, 2, BEIGE_L, (120, 112, 92), INK,
          [['NUM', '/', 'x', '-'], ['7', '8', '9', '+'], ['4', '5', '6', ''], ['1', '2', '3', 'E'], ['0', '.', '']])
    for i, lab in enumerate(['NUM', 'CAPS', 'SCROLL']):
        F.disc(img, x0 + 222 + i * 18, y0 + 9, 1, (60, 90, 60))


def draw_laptop(img):
    x0, y0, x1, y1 = REG['lap_kbd']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (34, 34, 36))
    main = [(0.0, [1] * 13 + [1.6]), (0.0, [1.4] + [1] * 12 + [1.2]), (0.0, [1.7] + [1] * 11 + [1.9]),
            (0.0, [2.2] + [1] * 10 + [2.4]), (0.0, [1.3, 1.3, 6.5, 1.3, 1.3, 1.0])]
    legends = [['', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '<'],
               ['', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '(', ')'],
               ['', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', "'", ''],
               ['', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/', ''],
               ['', '', '', '', '', '']]
    _keys(img, x0 + 3, y0 + 14, main, 10.4, 11, 1, (58, 58, 60), (20, 20, 22), (200, 200, 196), legends)
    _keys(img, x0 + 3, y0 + 3, [(0.0, [1] * 15)], 10.0, 10, 2, (52, 52, 54), (20, 20, 22), (170, 170, 166),
          [['', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', '', '', '', '', '']])


def draw_pc_front(img):
    x0, y0, x1, y1 = REG['pc_front']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, BEIGE)
    F.frame(img, x0, y0, x1 - 1, y1 - 1, BEIGE_D)
    # the 5.25" bay blank and the 3.5" floppy drive (right half), the vent slots (left)
    F.rect(img, x0 + 92, y0 + 8, x1 - 8, y0 + 22, BEIGE_D)
    F.rect(img, x0 + 93, y0 + 9, x1 - 9, y0 + 21, BEIGE_L)
    F.rect(img, x0 + 92, y0 + 28, x1 - 8, y0 + 42, BEIGE_D)
    F.rect(img, x0 + 93, y0 + 29, x1 - 9, y0 + 41, (186, 176, 150))
    F.rect(img, x0 + 100, y0 + 33, x0 + 140, y0 + 35, DARK)              # the floppy slot
    F.rect(img, x0 + 148, y0 + 36, x0 + 154, y0 + 39, (120, 112, 92))    # eject button
    F.disc(img, x0 + 100, y0 + 38, 1, (70, 100, 70))
    for yy in range(y0 + 8, y0 + 44, 4):
        F.rect(img, x0 + 8, yy, x0 + 50, yy + 1, BEIGE_D)
    F.text(img, x0 + 70, y0 + 48, 'POWER', F.F35, INK)
    F.text(img, x0 + 30, y0 + 48, 'TURBO  RESET', F.F35, INK)
    F.rect(img, x0 + 56, y0 + 10, x0 + 84, y0 + 18, (60, 60, 140))     # the sticker
    F.text(img, x0 + 70, y0 + 14, '486DX2', F.F35, (230, 230, 230))
    # the screen-off tile (the laptop's dark glass)
    a0, b0, a1, b1 = REG['screen_off']
    yy, xx = np.mgrid[b0:b1, a0:a1]
    g = 18 + 10 * np.exp(-(((xx - a0) / (a1 - a0) - 0.3) ** 2 + ((yy - b0) / (b1 - b0) - 0.25) ** 2) / 0.05)
    img[b0:b1, a0:a1] = np.stack([g * 0.9, g, g * 1.05], -1).astype(np.uint8)


def draw_cassette(img):
    x0, y0, x1, y1 = REG['cass_label']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (30, 30, 32))                 # the black shell around the label
    F.rect(img, x0 + 4, y0 + 3, x1 - 5, y0 + 34, WHITE)
    F.rect(img, x0 + 4, y0 + 3, x1 - 5, y0 + 8, (176, 40, 36))
    F.text(img, (x0 + x1) / 2, y0 + 5.5, 'SNOW TELEMETRY', F.F35, WHITE)
    F.text(img, x0 + 8, y0 + 12, 'ANT.', F.F35, INK, align='l')
    F.rect(img, x0 + 26, y0 + 15, x1 - 10, y0 + 15, (150, 150, 150))
    F.text(img, x0 + 8, y0 + 20, 'DATE', F.F35, INK, align='l')
    F.rect(img, x0 + 26, y0 + 23, x1 - 10, y0 + 23, (150, 150, 150))
    F.rect(img, x0 + 22, y0 + 27, x1 - 23, y0 + 38, (20, 20, 22))     # the window, the reels
    for cx in (x0 + 30, x1 - 31):
        F.ring(img, cx, y0 + 32, 3, 5, (210, 210, 206))
        F.disc(img, cx, y0 + 32, 2, (40, 40, 40))
    F.text(img, (x0 + x1) / 2, y0 + 44, 'C-60', F.F35, (150, 150, 150))
    for xx in (x0 + 10, x1 - 11):                                       # screw holes
        F.disc(img, xx, y0 + 46, 1, (12, 12, 12))


def draw_box_labels(img):
    for key, lines in (('cbox_front', [('TELEMETRY TAPES', F.F57, (176, 40, 36)), ('C-60  x10', F.F35, INK),
                                       ('PROJEKT SNOW', F.F35, INK)]),
                       ('cbox_top', [('SNOW', F.F57, INK), ('HANDLE WITH CARE', F.F35, INK), ('KEEP DRY - KEEP COLD', F.F35, INK)])):
        x0, y0, x1, y1 = REG[key]
        F.rect(img, x0, y0, x1 - 1, y1 - 1, (166, 128, 86))
        F.rect(img, x0 + 6, y0 + 4, x1 - 7, y1 - 5, (222, 214, 190))
        n = len(lines)
        for i, (t, f, c) in enumerate(lines):
            F.text(img, (x0 + x1) / 2, y0 + 4 + (y1 - y0 - 8) * (i + 0.5) / n, t, f, c)
    x0, y0, x1, y1 = REG['drop_plate']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (232, 228, 214))
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, (40, 70, 52), 2)
    F.text(img, (x0 + x1) / 2, y0 + 12, 'KASSETTEN', F.F57, INK)
    F.text(img, (x0 + x1) / 2, y0 + 23, 'TAPES', F.F57, (90, 90, 86))
    F.text(img, (x0 + x1) / 2, y0 + 35, 'PROJEKT SNOW', F.F35, (40, 70, 52))


def _sym(img, cx, cy, kind, col):
    """5 x 5 transport symbols: rec (dot), play, rew, ff, stop (square with the eject triangle over it)"""
    pts = {'rec': ['.###.', '#####', '#####', '#####', '.###.'],
           'play': ['#....', '###..', '#####', '###..', '#....'],
           'ff': ['#.#..', '##.#.', '#####', '##.#.', '#.#..'],
           'rew': ['..#.#', '.#.##', '#####', '.#.##', '..#.#'],
           'stop': ['..#..', '.###.', '.....', '#####', '#####']}[kind]
    for j, row in enumerate(pts):
        for i, ch in enumerate(row):
            if ch == '#':
                img[cy - 2 + j, cx - 2 + i] = col


def draw_deck(img, emi):
    """the telemetry recorder's faceplate (rack module in the dish cabinets): dark grey like the cabinet's modules"""
    x0, y0, x1, y1 = REG['deck_front']
    BODY, EAR, LEG = (66, 70, 74), (48, 50, 54), (200, 202, 198)
    F.rect(img, x0, y0, x1 - 1, y1 - 1, BODY)
    F.rect(img, x0, y0, x0 + 7, y1 - 1, EAR)
    F.rect(img, x1 - 8, y0, x1 - 1, y1 - 1, EAR)
    for xx in (x0 + 3, x1 - 5):                                         # the rack screws
        for yy in (y0 + 7, y1 - 9):
            F.rect(img, xx, yy, xx + 1, yy + 2, (24, 24, 26))
    F.rect(img, x0 + 8, y0, x1 - 9, y0 + 11, (52, 54, 58))              # the title strip
    F.text(img, x0 + 12, y0 + 6, 'TELEMETRY RECORDER  TR-4', F.F35, LEG, align='l')
    F.text(img, x1 - 12, y0 + 6, 'PROJEKT SNOW', F.F35, (150, 152, 150), align='r')
    hx0, hy0, hx1, hy1 = DECK_HOLE                                      # the bezel round the cassette opening
    F.rect(img, x0 + hx0 - 2, y0 + hy0 - 2, x0 + hx1 + 1, y0 + hy1 + 1, (104, 108, 112))
    F.rect(img, x0 + hx0, y0 + hy0, x0 + hx1 - 1, y0 + hy1 - 1, (14, 14, 14))
    F.text(img, x0 + (hx0 + hx1) / 2, y0 + hy0 - 6, 'TAPE', F.F35, LEG)
    for i, (a, b, c, d) in enumerate(DECK_KEYS):                        # the key wells and their symbols
        F.rect(img, x0 + a - 1, y0 + b - 1, x0 + c, y0 + d, (30, 30, 32))
        _sym(img, x0 + (a + c) // 2, y0 + d + 5, ['rec', 'play', 'rew', 'ff', 'stop'][i], (220, 60, 50) if i == 0 else LEG)
    F.text(img, x0 + 62, y0 + 51, 'REC', F.F35, (220, 60, 50))
    F.text(img, x0 + 122, y0 + 51, 'EJECT', F.F35, LEG)
    F.rect(img, x0 + 56, y0 + 57, x0 + 128, y0 + 65, (226, 224, 214))   # a strip to write the antenna on
    F.text(img, x0 + 59, y0 + 61, 'ANT.', F.F35, (40, 40, 40), align='l')
    F.text(img, x0 + 153, y0 + 17, 'COUNTER', F.F35, LEG)                # the tape counter
    F.rect(img, x0 + 142, y0 + 22, x0 + 164, y0 + 33, (10, 10, 10))
    F.text(img, x0 + 153, y0 + 27.5, '000', F.F57, (230, 230, 226))
    F.text(img, x0 + 190, y0 + 17, 'LEVEL', F.F35, LEG)                  # the level meters (L, R), unlit
    for r, yy in enumerate((y0 + 23, y0 + 29)):
        F.text(img, x0 + 167, yy + 2, 'LR'[r], F.F35, LEG)
        for s in range(10):
            col = (50, 90, 50) if s < 7 else ((110, 100, 40) if s < 9 else (110, 40, 36))
            F.rect(img, x0 + 171 + 4 * s, yy, x0 + 173 + 4 * s, yy + 4, col)
    F.text(img, x0 + 222, y0 + 17, 'POWER', F.F35, LEG)                  # the rocker switch
    F.rect(img, x0 + 218, y0 + 22, x0 + 226, y0 + 34, (20, 20, 22))
    F.rect(img, x0 + 219, y0 + 23, x0 + 225, y0 + 28, (44, 44, 46))
    F.text(img, x0 + 222, y0 + 25.5, 'I', F.F35, LEG)
    for key, col in (('key_grey', (150, 152, 154)), ('key_red', (176, 44, 36)), ('enamel', (232, 232, 226))):
        a, b, c, d = REG[key]
        F.rect(img, a, b, c - 1, d - 1, col)


def _therm_y(t):
    return THERM['y_hi'] + (THERM['hi'] - t) / (THERM['hi'] - THERM['lo']) * (THERM['y_lo'] - THERM['y_hi'])


def draw_thermometers(img):
    """four thermometer scales (16 x 160 px, the bulb at the bottom): dry and wet bulb (mercury; the wet bulb in a muslin
    sleeve), maximum (mercury), minimum (red spirit with its dark index); white enamel, a tick every 2 deg, numbers every 10"""
    for key in ('therm_dry', 'therm_wet', 'therm_max', 'therm_min'):
        x0, y0, x1, y1 = REG[key]
        F.rect(img, x0, y0, x1 - 1, y1 - 1, (236, 236, 230))
        F.frame(img, x0, y0, x1 - 1, y1 - 1, (150, 150, 144))
        for t in range(-40, 51, 2):
            yy = y0 + int(round(_therm_y(t)))
            ln = 5 if t % 10 == 0 else 2
            F.rect(img, x1 - 4 - ln, yy, x1 - 5, yy, (40, 40, 40))
            if t % 10 == 0:
                F.text(img, x0 + 5, yy, str(abs(t)), F.F35, (30, 30, 30) if t >= 0 else (40, 60, 150))
        cx = x1 - 4
        top = y0 + int(round(_therm_y(THERM['hi']))) - 2
        bulb = y0 + int(round(_therm_y(THERM['lo']))) + 3
        F.rect(img, cx, top, cx, bulb, (196, 204, 212))                  # the empty capillary
        level = y0 + int(round(_therm_y(THERM['read'][key])))
        liquid = (200, 40, 30) if key == 'therm_min' else (150, 152, 158)
        F.rect(img, cx, level, cx, bulb, liquid)
        F.rect(img, cx - 1, bulb, cx + 1, bulb + 4, liquid)
        if key == 'therm_min':
            F.rect(img, cx, level - 4, cx, level - 2, (30, 40, 110))     # the index
        if key == 'therm_wet':
            F.rect(img, cx - 2, bulb - 2, cx + 2, bulb + 6, (214, 214, 206))   # the muslin
        F.text(img, x0 + 5, y0 + 6, 'C', F.F35, (60, 60, 60))


def draw_chart(img):
    """the thermohygrograph's weekly chart round its drum: a pale grid, temperature (violet) above, humidity (blue) below"""
    x0, y0, x1, y1 = REG['chart']
    F.rect(img, x0, y0, x1 - 1, y1 - 1, (230, 226, 210))
    for xx in range(x0, x1, 4):
        F.rect(img, xx, y0, xx, y1 - 1, (200, 190, 200) if (xx - x0) % 12 else (170, 150, 180))
    for yy in range(y0 + 2, y1, 4):
        F.rect(img, x0, yy, x1 - 1, yy, (205, 196, 206))
    for i in range(x1 - x0 - 8):                                        # the traces end where the pens stand today
        t = i / 13.7
        yt = y0 + 9 + int(round(3.0 * math.sin(t * 2 * math.pi) + 1.5 * math.sin(t * 0.7)))
        yh = y0 + 23 + int(round(-2.5 * math.sin(t * 2 * math.pi + 0.4) + 1.0 * math.cos(t * 0.5)))
        img[yt, x0 + i] = (120, 40, 140)
        img[yh, x0 + i] = (40, 60, 150)
    F.rect(img, x0, y0, x0, y1 - 1, (120, 110, 100))                    # the chart's seam


def paper(out):
    w, h = 256, 362
    rng = np.random.default_rng(5)
    base = np.array((238, 236, 226), np.float32)
    g = rng.normal(0, 3.0, (h, w))[..., None]
    img = np.clip(base[None, None] + g, 0, 255).astype(np.uint8)
    img[:, :, 2] = np.clip(img[:, :, 2].astype(int) - 4, 0, 255)
    p = os.path.join(out, 'T_Dev_FaxPaper_BaseColor.png')
    Image.fromarray(img).save(p)
    return p


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (16, 16, 16)
    emi = np.zeros_like(img)
    draw_fax(img, emi)
    draw_keyboard(img)
    draw_laptop(img)
    draw_pc_front(img)
    draw_cassette(img)
    draw_box_labels(img)
    draw_deck(img, emi)
    draw_thermometers(img)
    draw_chart(img)
    pb, pe = os.path.join(out, 'T_Dev_Panel_BaseColor.png'), os.path.join(out, 'T_Dev_Panel_Emission.png')
    Image.fromarray(img).save(pb)
    Image.fromarray(emi).save(pe)
    pp = paper(out)
    tiles = {}                                    # the LCD and the laptop screen: own textures (full 0..1 UVs, the game swaps them)
    for name, key, src in (('FaxLCD_BaseColor', 'fax_lcd', img), ('FaxLCD_Emission', 'fax_lcd', emi),
                           ('ScreenOff_BaseColor', 'screen_off', img)):
        x0, y0, x1, y1 = REG[key]
        tiles[name] = os.path.join(out, f'T_Dev_{name}.png')
        Image.fromarray(src[y0:y1, x0:x1].copy()).save(tiles[name])
    json.dump(dict(size=N, regions=REG), open(os.path.join(out, 'devices_panel_regions.json'), 'w'), indent=1)
    return pb, pe, pp, tiles


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'devices')))
