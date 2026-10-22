"""v7 instrument panel specification (v6 + cabin door switches, movable radio / instrument knobs,
Kollsman window, compass card). No bpy: positions, sizes and atlas regions shared by
gauges_tex.py (atlas painter), cp_panel6.py (geometry + UVs) and export_unity_v6.py.

Build frame: nose -Y, pilot-left +X, up +Z, metres. The panel face (sub-panel fronts) is at PY and faces +Y.
Plates are given as (x_left, x_right, z_bottom, z_top) with x_left > x_right (pilot-left edge first).
Plate-local coordinates (s, t) are millimetres from the plate's top-left corner as the pilot sees it:
s grows to the pilot's right (-X), t grows downwards.

Gauge atlas T_Gauges_BC is 4096 x 4096 in v6. The top half (y < 2048) holds the v5 cells unchanged
(cells 17/18/19 repainted with VOLT/VAC/HOBBS); everything new lives in the bottom half.
Builders write OLD-SPACE UVs  u = px / 4096, v = 1 - py / 2048  (negative v for the bottom half); the
cockpit tail remaps every gauge-atlas UV once: v' = 0.5 + 0.5 v  ( = 1 - py / 4096 )."""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
PY = -2.985
AW = AH = 4096
ATLAS_JSON = os.path.join(HERE, 'tex', 'v7', 'atlas7.json')


def auv(px, py):
    """atlas pixel -> old-space UV (see module doc)"""
    return (px / AW, 1.0 - py / 2048.0)


# ------------------------------------------------------------------ sub-panels and frame
SUBPANELS = {'SP_P': (0.645, 0.040, 1.455, 2.028), 'SP_C': (0.036, -0.196, 1.455, 2.028),
             'SP_R': (-0.200, -0.645, 1.455, 2.028)}
SP_T = 0.003                       # sub-panel thickness (front face at PY)

# ------------------------------------------------------------------ instruments (recessed behind the sub-panel holes)
D6, DS = 0.082, 0.058              # hole diameters: 3-1/8" and 2-1/4" instruments
BEZEL_W = {D6: 0.0035, DS: 0.0025}  # visible bezel ring inside the hole
FACE_DY = -0.012                   # dial face plane = PY + FACE_DY
GLASS_DY = -0.004
CAN_DY = -0.032                    # instrument can rear
# name -> (x, z, hole_d, cell, needles)   needles: (bone, length fraction, kind)
GAUGES = {
    'ASI':   (0.426, 1.935, D6, 0, [('Needle_ASI', 0.88, 'needle')]),
    'ATT':   (0.330, 1.935, D6, 1, [('ATT_Roll', 1.0, 'rollcard')]),
    'ALT':   (0.234, 1.935, D6, 3, [('Needle_ALT100', 0.88, 'needle'), ('Needle_ALT1000', 0.55, 'needle_short')]),
    'TC':    (0.426, 1.835, D6, 4, [('TC_Plane', 0.8, 'plane'), ('TC_Ball', 1.0, 'ball')]),
    'HDG':   (0.330, 1.835, D6, 5, [('HDG_Card', 1.0, 'card')]),
    'VSI':   (0.234, 1.835, D6, 6, [('Needle_VSI', 0.88, 'needle')]),
    # engine block 2 x 4 between the six-pack and the centre stack
    'TRQ':   (0.150, 1.978, DS, 7, [('Needle_TRQ', 0.85, 'needle')]),
    'ITT':   (0.084, 1.978, DS, 8, [('Needle_ITT', 0.85, 'needle')]),
    'PROP':  (0.150, 1.910, DS, 10, [('Needle_PROP', 0.85, 'needle')]),
    'NG':    (0.084, 1.910, DS, 9, [('Needle_NG', 0.85, 'needle')]),
    'OIL':   (0.150, 1.842, DS, 12, [('Needle_OILP', 0.8, 'needle'), ('Needle_OILT', 0.8, 'needle')]),
    'FF':    (0.084, 1.842, DS, 11, [('Needle_FF', 0.85, 'needle')]),
    'FUELL': (0.150, 1.774, DS, 13, [('Needle_FUELL', 0.85, 'needle')]),
    'FUELR': (0.084, 1.774, DS, 14, [('Needle_FUELR', 0.85, 'needle')]),
    # copilot side: systems
    'CLOCK': (-0.255, 1.935, DS, 15, [('Clock_Hour', 0.55, 'needle_short'), ('Clock_Min', 0.85, 'needle')]),
    'AMP':   (-0.325, 1.935, DS, 16, [('Needle_AMP', 0.85, 'needle')]),
    'VOLT':  (-0.395, 1.935, DS, 17, [('Needle_VOLT', 0.85, 'needle')]),
    'VAC':   (-0.255, 1.835, DS, 18, [('Needle_VAC', 0.85, 'needle')]),
    'OAT':   (-0.325, 1.835, DS, 23, [('Needle_OAT', 0.85, 'needle')]),
    'HOBBS': (-0.395, 1.835, DS, 19, []),
}
ATT_CARD_CELL = 2
# knobs on instruments: gauge -> list of clock angles (deg, pilot view); they sit on the sub-panel just outside the hole
GAUGE_KNOBS = {'ALT': [225], 'HDG': [225, 135], 'ATT': [180], 'CLOCK': [45]}
# v7 (M3): instrument knobs that are separate rig parts (rotate about the gauge axis); the others stay static
GAUGE_KNOB_RIG = {('ALT', 225): 'Knob_ALT_Baro', ('HDG', 225): 'Knob_DG_Set', ('HDG', 135): 'Knob_HDG_Bug'}
# Kollsman window on the altimeter dial (dial-normalised: x to the pilot's right, z up, in units of the dial radius)
BARO_WIN = dict(x0=0.20, x1=0.60, z0=-0.08, z1=0.08)
BARO_CELL = 21                    # rotating pressure scale disc (cell 21 of the atlas, behind the dial)
BARO_DISC_R = 0.75                # disc radius / dial radius
BARO_LABEL_R = 0.47               # label centre radius / dial radius (window 0.20..0.60; ticks 0.22..0.32)
BARO_DEG_PER_INHG = 120.0         # scale: 0.1 inHg = 12 deg; 29.92 under the index at rest
BARO_RANGE = (28.6, 31.0)
# compass (v7): drum card behind a window in the housing front (build frame), wet-compass printing
COMPASS = dict(cx=0.0, cy=-2.667, cz=2.52, r=0.026, h=0.026, win_w=0.030, win_h=0.016, bezel_y=(-2.640, -2.636),
               box=(0.072, 0.056, 0.052))
COMPASS_RECT = (16, 1552)          # top-left of the card strip in the atlas (top half, free v5 strip rows); 6 px/mm
NEEDLE_REST = {
    'Needle_ASI': 10.0, 'Needle_ALT100': 0.0, 'Needle_ALT1000': 0.0, 'Needle_VSI': -90.0,
    'Needle_TRQ': -135.0, 'Needle_ITT': -135.0, 'Needle_NG': -135.0, 'Needle_PROP': -135.0,
    'Needle_FF': -135.0, 'Needle_OILP': -150.0, 'Needle_OILT': 150.0,
    'Needle_FUELL': -60.0, 'Needle_FUELR': -60.0, 'Clock_Hour': 0.0, 'Clock_Min': 0.0, 'Needle_AMP': 0.0,
    'Needle_OAT': -75.0, 'Needle_VOLT': -135.0, 'Needle_VAC': -135.0,
}
# Hobbs LCD window on its dial (dial-local mm, centre offset and size)
HOBBS_WIN = dict(dx=0.0, dz=0.0035, w=0.030, h=0.0095)

# ------------------------------------------------------------------ annunciator (4 x 3 lamps) + test button
ANN = dict(xl=0.026, xr=-0.186, zb=1.940, zt=2.008, border=3.0, gap=3.0)          # mm for border/gap
ANN_LAMPS = ['OIL PRESS', 'ENG HOT', 'FUEL LOW L', 'FUEL LOW R', 'GEN OFF', 'BATT LOW', 'STARTER ON', 'IGNITION',
             'DOOR', 'CARGO DOOR', 'CARGO LOOSE', 'SEAT BELT']
ANN_COLOR = {'OIL PRESS': 'red', 'ENG HOT': 'red', 'STARTER ON': 'green', 'IGNITION': 'green'}   # others amber
ANN_TEST_BTN = (0.018, 1.919)
ANN_TEST_PLATE = (0.027, 0.009, 1.900, 1.907)


def ann_lens(i):
    """lamp lens rectangle in annunciator-local mm (s0, t0, s1, t1)"""
    W, H = (ANN['xl'] - ANN['xr']) * 1000, (ANN['zt'] - ANN['zb']) * 1000
    b, g = ANN['border'], ANN['gap']
    lw, lh = (W - 2 * b - 3 * g) / 4, (H - 2 * b - 2 * g) / 3
    c, r = i % 4, i // 4
    s0, t0 = b + c * (lw + g), b + r * (lh + g)
    return (s0, t0, s0 + lw, t0 + lh)


# ------------------------------------------------------------------ radio stack (faces 6 mm proud of the panel)
RADIO_X = (0.000, -0.160)
RADIO_FACE_DY = 0.006
RADIO_BODY_DY = -0.030
# unit -> (z_top, z_bottom)
RADIOS = {'AUDIO': (1.932, 1.898), 'NAVCOM': (1.895, 1.851), 'GPS': (1.848, 1.780), 'XPDR': (1.777, 1.735),
          'AP': (1.732, 1.698), 'ADF': (1.695, 1.655)}
# face elements in face-local mm (s right, t down from the face's top-left), 160 mm wide
# caps: (s0, t0, s1, t1, legend)   knobs: (s, t, outer_d, inner_d or 0, kind)   windows: name -> (s0, t0, s1, t1)
# texts: (s, t, size_mm, text)     lamps: (s, t, d, colour)
RADIO_FACE = {
    'AUDIO': dict(
        caps=[(6 + i * 13.5, 13, 17 + i * 13.5, 21, t) for i, t in
              enumerate(('COM1', 'COM2', 'BOTH', 'NAV1', 'NAV2', 'ADF', 'MKR', 'SPKR'))],
        knobs=[(151, 18, 10, 0, 'plain')], windows={},
        texts=[(151, 5.5, 2.4, 'VOL'), (61, 6.5, 2.4, 'AUDIO SELECT'), (130, 28.5, 2.2, 'MARKER')],
        lamps=[(122, 16, 4.5, (40, 90, 220)), (130, 16, 4.5, (230, 160, 30)), (138, 16, 4.5, (230, 230, 225))],
        lamp_labels=[(122, 23, 2.4, 'O'), (130, 23, 2.4, 'M'), (138, 23, 2.4, 'I')]),
    'NAVCOM': dict(
        caps=[(33, 32, 45, 38, '<>'), (104, 32, 116, 38, '<>')],
        knobs=[(72, 24, 16, 10, 'conc'), (146, 24, 16, 10, 'conc'), (7, 22, 8, 0, 'plain')],
        windows={'Display_COM1': (15, 8, 63, 25), 'Display_NAV1': (86, 8, 134, 25)},
        texts=[(39, 4.6, 2.6, 'COM'), (110, 4.6, 2.6, 'NAV'), (27, 28.5, 2.0, 'USE'), (51, 28.5, 2.0, 'STBY'),
               (98, 28.5, 2.0, 'USE'), (122, 28.5, 2.0, 'STBY'), (7, 12, 2.0, 'PWR'), (7, 32, 2.0, 'VOL'),
               (72, 38.5, 2.0, 'PULL 25K'), (146, 38.5, 2.0, 'PULL ID')]),
    'GPS': dict(
        caps=[(6, 24, 24, 31, 'NRST'), (6, 35, 24, 42, 'OBS'), (6, 46, 24, 53, 'MSG'),
              (128, 7, 152, 14, 'D->'), (128, 17, 152, 24, 'MENU'), (128, 27, 152, 34, 'CLR'),
              (128, 37, 152, 44, 'ENT')] +
             [(30 + i * 19.25, 59, 45 + i * 19.25, 65, t) for i, t in enumerate(('NAV', 'WPT', 'FPL', 'MAP', 'PROC'))],
        knobs=[(14, 13, 10, 0, 'plain'), (145, 56.5, 16, 10, 'conc')],
        windows={'Display_GPS': (30, 6, 122, 56)},
        texts=[(14, 3.6, 2.0, 'PUSH PWR'), (15, 62, 3.0, 'GPS')]),
    'XPDR': dict(
        caps=[(44 + i * 7.5, 28, 50.5 + i * 7.5, 34, str(i)) for i in range(8)] +
             [(112, 8, 128, 15, 'IDT'), (112, 18, 128, 25, 'VFR'), (112, 28, 128, 35, 'CLR')],
        knobs=[(20, 22, 14, 0, 'pointer')],
        windows={'Display_XPDR': (44, 6, 104, 24)},
        texts=[(9.5, 15.5, 2.0, 'OFF'), (14.5, 9.5, 2.0, 'SBY'), (25.5, 9.5, 2.0, 'ON'), (30.5, 15.5, 2.0, 'ALT'),
               (31.5, 22.5, 2.0, 'TST'), (142, 19, 2.0, 'REPLY'), (142, 33, 2.6, 'XPDR')],
        lamps=[(142, 12, 4.0, (230, 150, 30))]),
    'AP': dict(
        caps=[(6, 6, 24, 16, 'AP'), (30, 22, 44, 29, 'HDG'), (48, 22, 62, 29, 'NAV'), (66, 22, 80, 29, 'APR'),
              (84, 22, 98, 29, 'REV'), (102, 22, 116, 29, 'ALT'), (120, 6, 134, 13, 'UP'), (120, 16, 134, 23, 'DN')],
        knobs=[(150, 15, 12, 0, 'plain')],
        windows={'Display_AP': (30, 5, 110, 18)},
        texts=[(15, 24.5, 2.2, 'AUTOPILOT'), (150, 27.5, 2.0, 'BARO')]),
    'ADF': dict(
        caps=[(28, 27, 40, 33, 'ADF'), (43, 27, 55, 33, 'BFO'), (58, 27, 70, 33, 'FRQ'), (73, 27, 86, 33, 'FLT/ET'),
              (89, 27, 101, 33, 'SET/RST')],
        knobs=[(12, 22, 10, 0, 'plain'), (145, 21, 16, 10, 'conc')],
        windows={'Display_ADF': (28, 6, 100, 23)},
        texts=[(12, 9, 2.0, 'OFF/VOL'), (118, 8, 2.6, 'ADF')]),
}
CAP_H = 0.0025                      # cap height over the face
# v7 (M7): every radio knob is its own rig part (rotate about its axis); concentric = outer + inner
RADIO_KNOB_NAMES = {
    'AUDIO': [('Knob_Audio_Vol',)],
    'NAVCOM': [('Knob_Com_Outer', 'Knob_Com_Inner'), ('Knob_Nav_Outer', 'Knob_Nav_Inner'), ('Knob_NavCom_Vol',)],
    'GPS': [('Knob_GPS_Pwr',), ('Knob_GPS_Outer', 'Knob_GPS_Inner')],
    'XPDR': [('Knob_XPDR_Mode',)],
    'AP': [('Knob_AP_Baro',)],
    'ADF': [('Knob_ADF_Vol',), ('Knob_ADF_Outer', 'Knob_ADF_Inner')],
}
XPDR_MODES = [('OFF', -58.0), ('SBY', -24.0), ('ON', 24.0), ('ALT', 58.0), ('TST', 92.0)]   # pointer clock angles

# ------------------------------------------------------------------ circuit breakers (lightplate, 4 x 6)
CB_PLATE = (0.030, -0.190, 1.468, 1.645)
CB_ROWS = [1.612, 1.571, 1.530, 1.489]
CB_COLS = [0.030 - (0.022 + i * 0.0352) for i in range(6)]
CB = [[('START', 5), ('IGN', 5), ('FUEL PUMP', 10), ('FUEL QTY', 2), ('ENG INST', 5), ('ANN', 5)],
      [('NAV LT', 5), ('STROBE', 10), ('BEACON', 5), ('LAND LT', 15), ('CABIN LT', 5), ('CARGO LT', 5)],
      [('CARGO DR', 10), ('FLAP', 10), ('PITOT HT', 10), ('STALL WARN', 2), ('INST LT', 5), ('GEN', 5)],
      [('AUDIO', 5), ('NAV/COM', 10), ('GPS', 5), ('XPDR', 3), ('AUTOPILOT', 5), ('ADF', 3)]]
CB_CAP_R = 0.0045
CB_COLLAR_R = 0.0065

# ------------------------------------------------------------------ switch lightplate (pilot side, outboard)
SW_PLATE = (0.640, 0.488, 1.470, 1.945)
SW_COL = (0.606, 0.522)
# bone -> (x, z, label, on_legend, off_legend)
# v7: DOORS block (cabin + cargo, NEW-04 / M1) on top, the electrical and lights columns 46 mm apart below it
SWITCHES = {
    'SW_CabinDoor_L': (0.606, 1.852, 'CABIN LEFT', 'OPEN', 'CLOSE'),
    'SW_CabinDoor_R': (0.522, 1.852, 'CABIN RIGHT', 'OPEN', 'CLOSE'),
    'SW_CargoDoor_L': (0.606, 1.800, 'CARGO LEFT', 'OPEN', 'CLOSE'),
    'SW_CargoDoor_R': (0.522, 1.800, 'CARGO RIGHT', 'OPEN', 'CLOSE'),
    'SW_Battery':     (0.606, 1.722, 'BATTERY', 'ON', 'OFF'),
    'SW_Avionics':    (0.606, 1.676, 'AVIONICS', 'ON', 'OFF'),
    'SW_FuelPump':    (0.606, 1.630, 'FUEL PUMP', 'ON', 'OFF'),
    'SW_Ignition':    (0.606, 1.584, 'IGNITION', 'ON', 'NORM'),
    'SW_Starter':     (0.606, 1.505, 'STARTER', 'START', 'OFF'),
    'SW_Beacon':      (0.522, 1.722, 'BEACON', 'ON', 'OFF'),
    'SW_Strobe':      (0.522, 1.676, 'STROBE', 'ON', 'OFF'),
    'SW_NavLights':   (0.522, 1.630, 'NAV', 'ON', 'OFF'),
    'SW_Landing':     (0.522, 1.584, 'LANDING', 'ON', 'OFF'),
    'SW_CabinLight':  (0.522, 1.538, 'CABIN LT', 'ON', 'OFF'),
    'SW_CargoLight':  (0.522, 1.492, 'CARGO LT', 'ON', 'OFF'),
}
DOOR_SWITCHES = ('SW_CabinDoor_L', 'SW_CabinDoor_R', 'SW_CargoDoor_L', 'SW_CargoDoor_R')
STARTER_GUARD = dict(w=0.021, h=0.036, d=0.030, hinge_dz=0.021)   # hinge above the switch, guard hangs down
RHEOSTATS = {'Rheo_Flood': (0.606, 1.912, 'FLOOD'), 'Rheo_Panel': (0.522, 1.912, 'PANEL')}
SW_HEADERS = [(0.564, 1.882, 'DOORS'), (0.606, 1.757, 'ELECTRICAL'), (0.522, 1.757, 'LIGHTS')]
SW_DIVIDERS = [1.893, 1.772]

# ------------------------------------------------------------------ pulls, jacks, placards
PULLS = {'Pull_CabinHeat': (0.140, 1.640, 'knob'), 'Pull_Defrost': (0.075, 1.640, 'knob'),
         'Pull_ParkBrake': (0.435, 1.505, 'tee')}
# label plates: name -> (x_left, x_right, z_bottom, z_top, text)
LABELS = {
    'L_CabinHeat': (0.165, 0.115, 1.6635, 1.6725, 'CABIN HEAT'),
    'L_Defrost':   (0.100, 0.050, 1.6635, 1.6725, 'DEFROST'),
    'L_ParkBrake': (0.463, 0.407, 1.5235, 1.5325, 'PARKING BRAKE'),
    'L_AnnTest':   ANN_TEST_PLATE + ('TEST',),
}
JACKS = {'P': (0.430, 0.380, 1.600, 1.630), 'C': (-0.380, -0.430, 1.700, 1.730)}   # MIC / PHONE plates
JACK_POS = [(15.0, 19.0, 'MIC'), (35.0, 19.0, 'PHONE')]                            # plate-local mm
PLACARDS = {
    'P_Limits':  (-0.440, -0.625, 1.872, 1.967),
    'P_NoSmoke': (-0.465, -0.600, 1.785, 1.840),
    'P_Engine':  (0.180, 0.054, 1.716, 1.736),
}

# ------------------------------------------------------------------ glovebox (map case), copilot side
GLOVE = dict(xl=-0.235, xr=-0.605, zb=1.478, zt=1.650, depth=0.200, lid_gap=0.0025, lid_t=0.012)
GLOVE_LATCH = (-0.420, 1.633)
GLOVE_PLACARD = (-0.390, -0.450, 1.6105, 1.6185)        # 'MAP CASE' on the lid (closed position)

# ------------------------------------------------------------------ atlas regions (bottom half), px per mm
REGION_PXMM = {'radio': 6.4, 'ann': 7.0, 'cb': 5.0, 'sw': 3.5, 'label': 7.0, 'jack': 6.0, 'limits': 5.5,
               'nosmoke': 5.0, 'engine': 7.0, 'map': 3.0, 'mapcase': 7.0, 'poh': 3.0, 'compass': 6.0}


def _mm(p):
    return ((p[0] - p[1]) * 1000.0, (p[3] - p[2]) * 1000.0)


def region_sizes():
    """name -> (w_px, h_px, px_per_mm, (w_mm, h_mm))"""
    R = {}
    for u, (zt, zb) in RADIOS.items():
        R['R_' + u] = (160.0, (zt - zb) * 1000.0, REGION_PXMM['radio'])
    W, H = (ANN['xl'] - ANN['xr']) * 1000, (ANN['zt'] - ANN['zb']) * 1000
    R['ANN'] = (W, H, REGION_PXMM['ann'])
    R['CB'] = _mm(CB_PLATE) + (REGION_PXMM['cb'],)
    R['SW'] = _mm(SW_PLATE) + (REGION_PXMM['sw'],)
    for k, v in LABELS.items():
        R[k] = _mm(v[:4]) + (REGION_PXMM['label'],)
    R['JACKS'] = _mm(JACKS['P']) + (REGION_PXMM['jack'],)
    R['P_Limits'] = _mm(PLACARDS['P_Limits']) + (REGION_PXMM['limits'],)
    R['P_NoSmoke'] = _mm(PLACARDS['P_NoSmoke']) + (REGION_PXMM['nosmoke'],)
    R['P_Engine'] = _mm(PLACARDS['P_Engine']) + (REGION_PXMM['engine'],)
    R['MAPCASE'] = _mm(GLOVE_PLACARD) + (REGION_PXMM['mapcase'],)
    R['MAP'] = (220.0, 140.0, REGION_PXMM['map'])
    R['POH'] = (150.0, 210.0, REGION_PXMM['poh'])
    return {k: (int(math.ceil(w * k_)), int(math.ceil(h * k_)), k_, (w, h)) for k, (w, h, k_) in R.items()}


def pack(gutter=16, y0=2048 + 16, x0=16):
    """deterministic column layout of the bottom half: each column stacks its entries top-down; a tuple entry is a
    row of regions side by side. Columns start right of the widest region of the previous column."""
    S = region_sizes()
    cols = [['R_GPS', 'R_NAVCOM', 'R_XPDR', 'R_ADF', 'R_AUDIO', 'R_AP', 'P_Engine',
             ('L_CabinHeat', 'L_Defrost', 'L_AnnTest')],
            ['SW', 'L_ParkBrake', 'MAPCASE'],
            ['ANN', ('CB', 'JACKS'), 'P_Limits'],
            ['POH', 'MAP', 'P_NoSmoke']]
    out = {}
    x = x0
    for col in cols:
        y, wmax = y0, 0
        for ent in col:
            row = ent if isinstance(ent, tuple) else (ent,)
            xx, hmax = x, 0
            for n in row:
                w, h = S[n][:2]
                out[n] = (xx, y, w, h)
                xx += w + gutter
                hmax = max(hmax, h)
            wmax = max(wmax, xx - gutter - x)
            y += hmax + gutter
        x += wmax + gutter
    assert set(out) == set(S), set(S) ^ set(out)
    circ = 2 * math.pi * COMPASS['r'] * 1000.0                     # v7 compass card strip: fixed rect, top half
    k = REGION_PXMM['compass']
    S['COMPASS'] = (int(math.ceil(circ * k)), int(math.ceil(COMPASS['h'] * 1000.0 * k)), k, (circ, COMPASS['h'] * 1000.0))
    items = list(out.items())
    for i, (a, ra) in enumerate(items):
        assert ra[1] >= 2048 and ra[1] + ra[3] <= AH - 8 and ra[0] + ra[2] <= AW - 8, ('outside', a, ra)
        for b, rb in items[:i]:
            assert (ra[0] + ra[2] <= rb[0] or rb[0] + rb[2] <= ra[0] or ra[1] + ra[3] <= rb[1] or
                    rb[1] + rb[3] <= ra[1]), ('overlap', a, b)
    out['COMPASS'] = (COMPASS_RECT[0], COMPASS_RECT[1], S['COMPASS'][0], S['COMPASS'][1])
    assert out['COMPASS'][1] + out['COMPASS'][3] <= 1880 and out['COMPASS'][0] + out['COMPASS'][2] <= AW
    return out, S


def write_atlas_json():
    rects, S = pack()
    data = {'size': [AW, AH], 'note': 'pixel rects [x, y, w, h] in T_Gauges_BC (v7); px_per_mm per region',
            'regions': {k: dict(rect=list(v), px_per_mm=S[k][2], size_mm=[round(S[k][3][0], 3), round(S[k][3][1], 3)])
                        for k, v in rects.items()}}
    os.makedirs(os.path.dirname(ATLAS_JSON), exist_ok=True)
    json.dump(data, open(ATLAS_JSON, 'w'), indent=1)
    return data


def load_regions():
    return json.load(open(ATLAS_JSON))['regions']


def region_uv(reg, s_mm, t_mm):
    """plate-local mm -> old-space UV inside an atlas region dict (from load_regions)"""
    x, y, w, h = reg['rect']
    wm, hm = reg['size_mm']
    return auv(x + s_mm / wm * w, y + t_mm / hm * h)


if __name__ == '__main__':
    d = write_atlas_json()
    for k, v in sorted(d['regions'].items(), key=lambda kv: (kv[1]['rect'][1], kv[1]['rect'][0])):
        print(f"{k:12s} {v['rect']}  {v['px_per_mm']} px/mm  {v['size_mm']}")
    used = sum(v['rect'][2] * v['rect'][3] for v in d['regions'].values())
    print('bottom half used', round(used / (4096 * 2048) * 100, 1), '%')
