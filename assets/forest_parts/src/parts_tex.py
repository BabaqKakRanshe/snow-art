"""Panel atlas and own textures of forest_parts (pixel art in the project's font, point filter). Panel (512 x 512): the
relay transceiver's front and rear panels (RT-7, RF LEVEL meter, LEDs, FUSE, POWER), the backup generator's control panel
(two Schuko outlets, 230 V ~ 50 Hz, ON / OFF, RESET, hour meter) and its tank sticker, the dosing pump's plate (the valve
diagram and the priming steps), its motor plate, the pressure gauge's and the stroke knob's dials, the radar tube's
sticker, the sodium lamp's carton, the lake sensor's box label, its post sign (MESSSTELLE / GAUGE STATION - German first,
English under) and its logger board. Equipment in English, the carton in German. Own textures (UV 0..1): the dosing pump's
waybill (LIEFERSCHEIN, dated 1991 - signed back-dated, EVENTS day 4) and the radar tube's dark face (the game draws the
sweep). Everything is invented: no real brand or type number.
python3 parts_tex.py [out_dir] -> T_Parts_Panel_BaseColor.png / _Emission.png, the own textures, parts_panel_regions.json"""
import os, sys, json, math
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxfont as F
import van2_tex as VT
import gear_tex as GT                                   # the umlauts, ptext / fill / grain / pack
from noise import fbm

HERE = os.path.dirname(os.path.abspath(__file__))
N = 512
INK, WHITE, CREAM = (26, 24, 22), (236, 234, 226), (232, 226, 206)
DARK, LEG = (66, 70, 74), (200, 202, 198)
ptext, fill, grain = GT.ptext, GT.fill, GT.grain
WAYBILL_DATE = '03.11.1991'
SIZES = [('relay_front', 240, 66),       # 0.483 x 0.133 m (497 px/m)
         ('relay_rear', 216, 60),        # 0.432 x 0.12 m
         ('gen_panel', 96, 64),          # 0.24 x 0.16 m
         ('gen_tank', 80, 40),           # 0.20 x 0.10 m
         ('pump_plate', 112, 84),        # 0.28 x 0.21 m
         ('pump_motor', 48, 24), ('pump_gauge', 40, 40), ('pump_stroke', 40, 40),
         ('crt_label', 72, 28),
         ('lampbox_front', 56, 120), ('lampbox_side', 56, 120), ('lampbox_top', 56, 56),
         ('sensor_label', 72, 36), ('sensor_sign', 96, 56), ('sensor_pcb', 64, 44)]
REG = GT.pack(SIZES, n=N)
RELAY_PX = (240, 66)
RELAY = dict(meter=(40, 16, 84, 50), leds=[(104, 30), (118, 30), (132, 30), (146, 30)], fuse=(172, 33), switch=(204, 33),
             jack=(158, 52), handles=(20, 220))                  # px in relay_front
GEN_PX = (96, 64)
GEN = dict(outlets=[(24, 34), (60, 34)], switch=(84, 14), reset=(84, 46), meter=(16, 10))
PUMP_GAUGE = dict(lo=-135.0, hi=135.0, bar=10.0)
LCD_DUMMY = None


def uv(name, n=N):
    return VT.uv(REG[name], n)


def screw(img, x, y, col=(30, 30, 32)):
    F.rect(img, x, y, x + 1, y + 1, col)


# ---------------------------------------------------------------- the relay transceiver
def draw_relay(img):
    x0, y0, x1, y1 = REG['relay_front']
    EAR = (48, 50, 54)
    fill(img, REG['relay_front'], DARK)
    F.rect(img, x0, y0, x0 + 9, y1 - 1, EAR)
    F.rect(img, x1 - 10, y0, x1 - 1, y1 - 1, EAR)
    for xx in (x0 + 3, x1 - 6):
        for yy in (y0 + 8, y1 - 11):
            F.rect(img, xx, yy, xx + 2, yy + 3, (20, 20, 22))
    F.rect(img, x0 + 10, y0, x1 - 11, y0 + 10, (52, 54, 58))
    ptext(img, x0 + 32, y0 + 5, 'RELAY TRANSCEIVER  RT-7', F.F35, LEG, align='l')
    ptext(img, x1 - 32, y0 + 5, 'PROJEKT SNOW', F.F35, (150, 152, 150), align='r')
    mx0, my0, mx1, my1 = RELAY['meter']                                     # the RF LEVEL meter's dial (the needle is a part)
    F.rect(img, x0 + mx0 - 2, y0 + my0 - 2, x0 + mx1 + 1, y0 + my1 + 1, (30, 30, 32))
    F.rect(img, x0 + mx0, y0 + my0, x0 + mx1 - 1, y0 + my1 - 1, (224, 220, 200))
    cx, cy = x0 + (mx0 + mx1) / 2, y0 + my1 - 4
    for i in range(11):
        a = math.radians(-50 + 100 * i / 10 - 90)
        r0, r1 = (19, 23) if i % 5 == 0 else (21, 23)
        for r in np.arange(r0, r1 + 0.5, 0.5):
            img[int(round(cy + r * math.sin(a))), int(round(cx + r * math.cos(a)))] = (40, 40, 40) if i < 8 else (176, 40, 30)
    ptext(img, cx, y0 + my0 + 18, 'RF', F.F35, (60, 60, 60))
    ptext(img, x0 + (mx0 + mx1) / 2, y0 + my1 + 6, 'RF LEVEL', F.F35, LEG)
    for (lx, ly), lab in zip(RELAY['leds'], ('PWR', 'TX', 'RX', 'ALM')):     # the LED holes and their labels
        F.disc(img, x0 + lx, y0 + ly, 3, (24, 24, 26))
        ptext(img, x0 + lx, y0 + ly + 8, lab, F.F35, LEG)
    fx, fy = RELAY['fuse']
    F.disc(img, x0 + fx, y0 + fy, 6, (36, 36, 38))
    ptext(img, x0 + fx, y0 + fy - 12, 'FUSE', F.F35, LEG)
    ptext(img, x0 + fx, y0 + fy + 12, '2A T', F.F35, LEG)
    sx, sy = RELAY['switch']
    F.rect(img, x0 + sx - 5, y0 + sy - 7, x0 + sx + 5, y0 + sy + 7, (36, 36, 38))
    ptext(img, x0 + sx, y0 + sy - 12, 'POWER', F.F35, LEG)
    ptext(img, x0 + sx, y0 + sy + 12, 'I  O', F.F35, LEG)
    jx, jy = RELAY['jack']
    F.ring(img, x0 + jx, y0 + jy, 3, 4, (170, 170, 168))
    ptext(img, x0 + jx + 14, y0 + jy, 'TEST', F.F35, LEG)
    grain(img, REG['relay_front'], 51, 3)
    x0, y0, x1, y1 = REG['relay_rear']
    fill(img, REG['relay_rear'], (150, 152, 150))                            # the zinc-plated rear panel
    F.disc(img, x0 + 34, y0 + 30, 21, (120, 122, 120))                        # the fan grille
    for i in range(7):
        F.ring(img, x0 + 34, y0 + 30, 3 * i + 1, 3 * i + 1.9, (50, 52, 52))
    for xx, lab in ((96, 'ANT A'), (128, 'ANT B')):
        F.disc(img, x0 + xx, y0 + 28, 7, (120, 122, 120))
        ptext(img, x0 + xx, y0 + 43, lab, F.F35, INK)
    F.rect(img, x0 + 160, y0 + 20, x0 + 182, y0 + 36, (30, 30, 32))           # the mains inlet
    ptext(img, x0 + 171, y0 + 43, '~230 V', F.F35, INK)
    F.rect(img, x0 + 150, y0 + 6, x0 + 206, y0 + 14, (236, 234, 226))
    ptext(img, x0 + 178, y0 + 10, 'SERIAL 0447', F.F35, INK)
    for xx in (x0 + 4, x1 - 6):
        for yy in (y0 + 4, y1 - 6):
            screw(img, xx, yy)
    grain(img, REG['relay_rear'], 52, 5)


# ---------------------------------------------------------------- the backup generator
def schuko(img, cx, cy):
    """a Schuko outlet seen from the front: a round recess, two holes, the earth clips top and bottom, a flap hinge"""
    F.disc(img, cx, cy, 11, (40, 40, 42))
    F.disc(img, cx, cy, 9, (70, 70, 72))
    for dx in (-4, 4):
        F.disc(img, cx + dx, cy, 1, (14, 14, 14))
    for dy in (-8, 8):
        F.rect(img, cx - 2, cy + dy, cx + 2, cy + dy, (176, 178, 176))


def draw_generator(img):
    x0, y0, x1, y1 = REG['gen_panel']
    fill(img, REG['gen_panel'], (54, 56, 58))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (30, 30, 32))
    for (ox, oy) in GEN['outlets']:
        schuko(img, x0 + ox, y0 + oy)
    ptext(img, x0 + 42, y0 + 54, '230 V ~ 50 Hz  16 A', F.F35, LEG)
    sx, sy = GEN['switch']
    F.rect(img, x0 + sx - 5, y0 + sy - 6, x0 + sx + 5, y0 + sy + 6, (24, 24, 26))
    ptext(img, x0 + sx, y0 + sy + 11, 'ON/OFF', F.F35, LEG)
    rx, ry = GEN['reset']
    F.disc(img, x0 + rx, y0 + ry, 4, (24, 24, 26))
    ptext(img, x0 + rx, y0 + ry + 9, 'RESET', F.F35, LEG)
    mx, my = GEN['meter']
    F.rect(img, x0 + mx - 10, y0 + my - 5, x0 + mx + 10, y0 + my + 5, (16, 16, 16))
    F.text(img, x0 + mx, y0 + my, '0412', F.F35, (220, 220, 214))
    ptext(img, x0 + mx + 24, y0 + my, 'HOURS', F.F35, (150, 152, 150))
    grain(img, REG['gen_panel'], 61, 3)
    x0, y0, x1, y1 = REG['gen_tank']
    OLIVE = (82, 98, 64)
    fill(img, REG['gen_tank'], OLIVE)
    F.rect(img, x0 + 2, y0 + 3, x1 - 3, y1 - 4, (232, 228, 214))
    ptext(img, (x0 + x1) / 2, y0 + 10, 'GENERATOR', F.F57, INK)
    ptext(img, (x0 + x1) / 2, y0 + 20, '2.8 kVA  230 V', F.F35, INK)
    F.rect(img, x0 + 6, y0 + 25, x1 - 7, y0 + 32, (200, 160, 30))
    ptext(img, (x0 + x1) / 2, y0 + 28.5, 'UNLEADED ONLY', F.F35, INK)
    grain(img, REG['gen_tank'], 62, 3)


# ---------------------------------------------------------------- the dosing pump
def valve_sym(img, cx, cy, col):
    """a valve in a pipe diagram: two triangles tip to tip"""
    for d in range(5):
        F.rect(img, cx - 5 + d, cy - d, cx - 5 + d, cy + d, col)
        F.rect(img, cx + 5 - d, cy - d, cx + 5 - d, cy + d, col)


def num(img, cx, cy, n, col):
    F.ring(img, cx, cy, 4, 5, col)
    F.text(img, cx + 0.5, cy, str(n), F.F35, col)


def draw_pump(img):
    x0, y0, x1, y1 = REG['pump_plate']
    fill(img, REG['pump_plate'], (230, 228, 216))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (40, 70, 52), 2)
    ptext(img, (x0 + x1) / 2, y0 + 6, 'DOSING PUMP DP-40', F.F35, INK)
    BL, RD = (40, 60, 130), (176, 40, 30)
    # the diagram: TANK -> V1 -> PUMP -> V3 -> OUT, the bleed through V2 back into the tank
    F.frame(img, x0 + 6, y0 + 18, x0 + 24, y0 + 42, INK)
    ptext(img, x0 + 15.5, y0 + 30, 'TANK', F.F35, INK)
    F.rect(img, x0 + 25, y0 + 36, x0 + 50, y0 + 36, BL)                      # suction
    valve_sym(img, x0 + 36, y0 + 36, BL)
    ptext(img, x0 + 36, y0 + 46, 'V1', F.F35, RD)
    F.ring(img, x0 + 56, y0 + 36, 5, 6, INK)                                  # the pump
    ptext(img, x0 + 56.5, y0 + 36, 'P', F.F35, INK)
    F.rect(img, x0 + 62, y0 + 36, x0 + 92, y0 + 36, BL)                      # discharge
    valve_sym(img, x0 + 76, y0 + 36, BL)
    ptext(img, x0 + 76, y0 + 46, 'V3', F.F35, RD)
    ptext(img, x0 + 100, y0 + 36, 'OUT', F.F35, INK)
    F.rect(img, x0 + 56, y0 + 22, x0 + 56, y0 + 30, BL)                      # the bleed up and back into the tank
    F.rect(img, x0 + 25, y0 + 22, x0 + 56, y0 + 22, BL)
    valve_sym(img, x0 + 40, y0 + 22, BL)
    ptext(img, x0 + 40, y0 + 14, 'V2', F.F35, RD)
    steps = ['1  OPEN V1', '2  OPEN V2 - MOTOR ON', '    BLEED UNTIL NO AIR', '3  CLOSE V2 - OPEN V3']
    for i, s in enumerate(steps):
        ptext(img, x0 + 6, y0 + 54 + 7 * i, s, F.F35, INK, align='l')
    grain(img, REG['pump_plate'], 71, 3)
    x0, y0, x1, y1 = REG['pump_motor']
    fill(img, REG['pump_motor'], (200, 202, 198))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (120, 122, 120))
    ptext(img, (x0 + x1) / 2, y0 + 5, '3~ MOTOR', F.F35, INK)
    ptext(img, (x0 + x1) / 2, y0 + 12, '0.25 kW', F.F35, INK)
    ptext(img, (x0 + x1) / 2, y0 + 19, '400 V 50 Hz', F.F35, INK)
    for key, lab, n_, hi in (('pump_gauge', 'BAR', 11, 10), ('pump_stroke', 'STROKE', 11, 100)):
        x0, y0, x1, y1 = REG[key]
        cx, cy = (x0 + x1) / 2 - 0.5, (y0 + y1) / 2 - 0.5
        F.disc(img, int(cx + 0.5), int(cy + 0.5), 19, (236, 234, 226) if key == 'pump_gauge' else (52, 54, 56))
        F.ring(img, int(cx + 0.5), int(cy + 0.5), 18, 19, (40, 40, 40) if key == 'pump_gauge' else (120, 122, 120))
        tick = INK if key == 'pump_gauge' else LEG
        for i in range(n_):
            a = math.radians(PUMP_GAUGE['lo'] + (PUMP_GAUGE['hi'] - PUMP_GAUGE['lo']) * i / (n_ - 1) - 90)
            r0 = 12 if i % 5 == 0 else 14
            for r in np.arange(r0, 16.5, 0.5):
                img[int(round(cy + r * math.sin(a))), int(round(cx + r * math.cos(a)))] = tick
            if i % 5 == 0:
                t = str(int(hi * i / (n_ - 1)))
                F.text(img, cx + 8.5 * math.cos(a), cy + 8.5 * math.sin(a), t, F.F35, tick)
        ptext(img, cx + 0.5, cy + 10, lab, F.F35, tick)


# ---------------------------------------------------------------- the radar tube, the sodium lamp's carton, the lake sensor
def draw_misc(img):
    x0, y0, x1, y1 = REG['crt_label']
    fill(img, REG['crt_label'], (236, 232, 214))
    F.rect(img, x0, y0, x1 - 1, y0 + 8, (200, 160, 30))
    ptext(img, (x0 + x1) / 2, y0 + 4.5, 'HIGH VOLTAGE', F.F35, INK)
    ptext(img, (x0 + x1) / 2, y0 + 14, 'PPI TUBE 40-P7', F.F35, INK)
    ptext(img, (x0 + x1) / 2, y0 + 22, 'HANDLE WITH CARE', F.F35, (176, 40, 30))
    grain(img, REG['crt_label'], 81, 3)
    ORANGE, ORANGE_D = (222, 120, 30), (170, 86, 20)
    for key in ('lampbox_front', 'lampbox_side'):
        x0, y0, x1, y1 = REG[key]
        fill(img, REG[key], (236, 232, 220))
        F.rect(img, x0, y0, x1 - 1, y0 + 9, ORANGE)
        F.rect(img, x0, y1 - 10, x1 - 1, y1 - 1, ORANGE)
        F.rect(img, x0, y0 + 10, x1 - 1, y0 + 10, ORANGE_D)
        cx = (x0 + x1) / 2
        if key == 'lampbox_front':
            for i, t in enumerate(('NATRIUM-', 'DAMPF-', 'HOCHDRUCK-', 'LAMPE')):
                ptext(img, cx, y0 + 18 + 8 * i, t, F.F35, INK)
            F.rect(img, int(cx) - 5, y0 + 52, int(cx) + 4, y0 + 82, (190, 190, 186))      # the tube pictogram
            F.rect(img, int(cx) - 3, y0 + 56, int(cx) + 2, y0 + 78, (236, 232, 220))
            F.rect(img, int(cx) - 1, y0 + 60, int(cx), y0 + 74, ORANGE)
            F.rect(img, int(cx) - 4, y0 + 83, int(cx) + 3, y0 + 90, (120, 120, 116))
            ptext(img, cx, y0 + 98, '400 W', F.F57, INK)
            ptext(img, cx, y0 + 108, 'E40', F.F35, INK)
        else:
            for i, t in enumerate(('400 W', 'E40', 'ROHRFORM', 'KLAR', '2000 K', 'NUR MIT', 'VORSCHALT-', 'GERÄT')):
                ptext(img, cx, y0 + 18 + 9 * i, t, F.F35 if i else F.F57, INK)
            for j in range(20):
                if (j * 3 + j // 4) % 4 < 2:
                    F.rect(img, int(cx - 14 + j * 1.5), y1 - 30, int(cx - 14 + j * 1.5), y1 - 20, INK)
        grain(img, REG[key], 82 + len(key), 3)
    x0, y0, x1, y1 = REG['lampbox_top']
    fill(img, REG['lampbox_top'], (236, 232, 220))
    F.rect(img, x0, y0, x1 - 1, y0 + 6, ORANGE)
    ptext(img, (x0 + x1) / 2, y0 + 24, '400 W', F.F57, INK)
    ptext(img, (x0 + x1) / 2, y0 + 36, 'E40', F.F35, INK)
    x0, y0, x1, y1 = REG['sensor_label']
    fill(img, REG['sensor_label'], (236, 234, 226))
    F.frame(img, x0, y0, x1 - 1, y1 - 1, (40, 60, 130), 1)
    ptext(img, (x0 + x1) / 2, y0 + 7, 'LAKE SENSOR LS-3', F.F35, INK)
    ptext(img, (x0 + x1) / 2, y0 + 15, 'PROJEKT SNOW', F.F35, (40, 60, 130))
    F.rect(img, x0 + 4, y0 + 21, x1 - 5, y0 + 30, (200, 160, 30))
    ptext(img, (x0 + x1) / 2, y0 + 25.5, 'BATTERY 6V 4R25', F.F35, INK)
    x0, y0, x1, y1 = REG['sensor_sign']                                     # a wall sign: German first, English under
    fill(img, REG['sensor_sign'], (236, 236, 230))
    F.frame(img, x0 + 1, y0 + 1, x1 - 2, y1 - 2, (40, 70, 140), 2)
    ptext(img, (x0 + x1) / 2, y0 + 13, 'MESSSTELLE', F.F57, INK)
    ptext(img, (x0 + x1) / 2, y0 + 25, 'GAUGE STATION', F.F35, (90, 90, 86))
    ptext(img, (x0 + x1) / 2, y0 + 37, 'NICHT BERÜHREN', F.F35, (176, 40, 30))
    ptext(img, (x0 + x1) / 2, y0 + 45, 'DO NOT TOUCH', F.F35, (120, 60, 50))
    grain(img, REG['sensor_sign'], 91, 3)
    x0, y0, x1, y1 = REG['sensor_pcb']                                      # the logger board inside the box
    fill(img, REG['sensor_pcb'], (36, 92, 52))
    for (a, b, c, d) in ((6, 6, 22, 14), (28, 6, 44, 12), (6, 20, 18, 30), (24, 22, 40, 30), (46, 18, 58, 38)):
        F.rect(img, x0 + a, y0 + b, x0 + c, y0 + d, (24, 24, 26))
    for i in range(10):
        F.rect(img, x0 + 4 + 6 * i, y0 + 36, x0 + 5 + 6 * i, y0 + 40, (200, 180, 110))
    for yy in (16, 33):
        F.rect(img, x0 + 2, y0 + yy, x1 - 3, y0 + yy, (70, 130, 80))
    F.rect(img, x0 + 48, y0 + 4, x0 + 58, y0 + 12, (220, 220, 214))
    ptext(img, x0 + 53, y0 + 8, 'LS3', F.F35, INK)


# ---------------------------------------------------------------- own textures
def waybill():
    """the dosing pump's waybill: LIEFERSCHEIN, the date in 1991, the signature (the delivery came on day 4 - EVENTS:
    the note is signed back-dated, 1991)"""
    w, h = 256, 362
    rng = np.random.default_rng(17)
    img = np.clip(np.array((238, 236, 228), np.float32)[None, None] + rng.normal(0, 2.5, (h, w, 1)), 0, 255).astype(np.uint8)
    ptext(img, 20, 24, 'LIEFERSCHEIN', F.F57, INK, scale=2, align='l')
    ptext(img, w - 20, 24, 'NR. 4471', F.F57, INK, align='r')
    F.rect(img, 18, 40, w - 19, 40, INK)
    rows = [('DATUM', WAYBILL_DATE), ('EMPFÄNGER', 'STATION HOHENMOOS'), ('PROJEKT', 'SNOW'), ('VERSAND', 'HUBSCHRAUBER')]
    for i, (k, v) in enumerate(rows):
        ptext(img, 20, 56 + 14 * i, k, F.F35, (90, 90, 86), align='l')
        ptext(img, 100, 56 + 14 * i, v, F.F57, INK, align='l')
    F.rect(img, 18, 118, w - 19, 118, INK)
    ptext(img, 20, 130, 'POS  MENGE  BEZEICHNUNG', F.F35, (90, 90, 86), align='l')
    items = [('1', '1', 'DOSIERPUMPE DP-40'), ('', '', 'KOMPLETT MIT TANK 30 L'), ('2', '1', 'DICHTUNGSSATZ'),
             ('3', '1', 'BETRIEBSANLEITUNG')]
    for i, (a, b, c) in enumerate(items):
        ptext(img, 22, 146 + 14 * i, a, F.F57, INK, align='l')
        ptext(img, 52, 146 + 14 * i, b, F.F57, INK, align='l')
        ptext(img, 84, 146 + 14 * i, c, F.F57, INK, align='l')
    F.rect(img, 18, 214, w - 19, 214, INK)
    ptext(img, 20, 290, 'UNTERSCHRIFT', F.F35, (90, 90, 86), align='l')
    F.rect(img, 20, 312, 140, 312, (120, 120, 116))
    pts = [(28, 304), (40, 292), (48, 306), (60, 290), (70, 302), (84, 296), (96, 304), (112, 294), (126, 300)]
    for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):                         # the signature, blue ink
        F.line(img, xa, ya, xb, yb, (44, 58, 136))
    ptext(img, 160, 300, WAYBILL_DATE, F.F57, (44, 58, 136), align='l')     # dated by hand, the same day
    F.disc(img, 214, 270, 22, (176, 70, 60))                                  # a faded stamp
    F.disc(img, 214, 270, 19, (238, 236, 228))
    ptext(img, 214, 266, 'GEPRÜFT', F.F35, (176, 70, 60))
    ptext(img, 214, 274, 'VERSAND', F.F35, (176, 70, 60))
    return img


def crt_face():
    """the radar tube's face, switched off: dark green-grey glass, a faint reflection (the game puts the sweep on it)"""
    w = 128
    yy, xx = np.mgrid[0:w, 0:w].astype(np.float32)
    r = np.hypot(xx - w / 2 + 0.5, yy - w / 2 + 0.5) / (w / 2)
    g = 50 + 10 * (1 - np.clip(r, 0, 1)) + 34 * np.exp(-(((xx - w * 0.33) / 14) ** 2 + ((yy - w * 0.28) / 10) ** 2))
    g = g - 12 * np.clip((r - 0.9) / 0.1, 0, 1)                             # darker at the rim, under the band
    img = np.stack([g * 0.88, g * 1.0, g * 0.92], -1)
    img[r > 1.0] = (16, 18, 16)
    return np.clip(img, 0, 255).astype(np.uint8)


def build(out):
    os.makedirs(out, exist_ok=True)
    img = np.zeros((N, N, 3), np.uint8)
    img[:] = (24, 24, 24)
    emi = np.zeros_like(img)
    draw_relay(img)
    draw_generator(img)
    draw_pump(img)
    draw_misc(img)
    paths = {}
    for name, a in (('Panel_BaseColor', img), ('Panel_Emission', emi), ('Waybill_BaseColor', waybill()),
                    ('CRTFace_BaseColor', crt_face())):
        paths[name] = os.path.join(out, f'T_Parts_{name}.png')
        Image.fromarray(a).save(paths[name])
    json.dump(dict(size=N, regions=REG, relay_front=RELAY, gen_panel=GEN, waybill_date=WAYBILL_DATE),
              open(os.path.join(out, 'parts_panel_regions.json'), 'w'), indent=1, ensure_ascii=False)
    return paths


if __name__ == '__main__':
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'tex', 'parts')))
