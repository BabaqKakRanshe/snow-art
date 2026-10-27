"""forest_devices geometry: the paperwork and data devices of the Forest tasks, in the generator shed's style. Nine roots,
each in its own frame (Blender: z up, the front -y, metres; origin on the surface it stands on, z = 0; Unity (x, y, z) ->
(-x, z, -y), the front -> +Z):
  Fax          a 90s thermal desktop fax: the sloped control panel (keypad, COPY / TEL / AUTO / MEMO, START and STOP as their
               own push parts, READY / ERROR LEDs, the LCD its own object), the handset in its cradle (Fax_Handset, lifted
               by the game) on a coiled cord, the document feeder at the back (Slot_DocIn) and the exit slot with its tray
               at the front (Slot_PaperOut); English labels
  FaxPaper     a received fax: an A4 sheet of thermal paper curling at the far end; its own material and full 0..1 UVs on the
               face (the game prints the text), the back on a blank corner
  Cassette     the telemetry tape: a compact cassette with the SNOW TELEMETRY label (ANT. / DATE lines to write on)
  CassetteBox  the day-2 delivery: a taped carton of ten tapes, TELEMETRY TAPES C-60 x10, PROJEKT SNOW
  DropBox      the tape drop box on the helipad: a steel box in the station's grey-green on a galvanised post in a concrete
               footing, the slot with its flap (DropBox_Flap swings in), the courier's locked door, the plate KASSETTEN /
               TAPES (German first, English under); Slot_Cassette
  ObjectPC     the object computer (relay, radar shelters): a beige 486 desktop case (POWER pushes in, the power LED), the
               keyboard and the mouse as their own objects; the monitor is snow_kit's Kit_Monitor_CRT (an instance on the case)
  Laptop       a 90s notebook for the weather station and the camp: the lid IX_LaptopLid (hinge at the back, opens 0..115),
               the screen its own object (Laptop_Screen, full 0..1 UVs for the game's picture), keyboard, trackball, LED
  TapeDeck     the telemetry recorder TR-4 for the dish cabinets: a rack faceplate (dark grey like the cabinet's modules) with
               the cassette compartment (Slot_Tape) behind a tilting door with a smoked window (IX_TapeDoor), five keys
               (REC, PLAY, REW, FF, STOP / EJECT), the counter, level meters, REC and POWER LEDs; fixed on the third module
               of every dish cabinet (PLACEMENTS)
  MeteoScreen  the weather station's Stevenson screen: legs, a slatted floor, louvred walls, a double roof, the louvred door
               (IX_ScreenDoor) on the north side, a step; inside the thermometer frame with the dry and wet bulb, maximum and
               minimum thermometers (panel tiles), the wet bulb's water bottle, a thermohygrograph with its chart drum;
               replaces the screen of forest_far's MeteoStation (1.1: Mount_MeteoScreen)
Labels, key fields, plates and scales (panel atlas) are merged into their body at build time (MERGE); parts / sockets in each
root's frame (the contract); in the .blend the roots stand apart (DISPLAY)."""
import math
import numpy as np
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, prism_x, quad, KBS, CONTRACT
import devices_tex as DT

uv = DT.uv
ROOTS = ['Fax', 'FaxPaper', 'Cassette', 'CassetteBox', 'DropBox', 'ObjectPC', 'Laptop', 'TapeDeck', 'MeteoScreen']
DISPLAY = {'Fax': Vector((0.0, 0.0, 0.0)), 'FaxPaper': Vector((0.45, 0.0, 0.0)), 'Cassette': Vector((0.85, -0.05, 0.0)),
           'CassetteBox': Vector((0.85, 0.15, 0.0)), 'DropBox': Vector((2.2, 0.0, 0.0)), 'ObjectPC': Vector((-1.0, 0.0, 0.0)),
           'Laptop': Vector((-2.0, 0.0, 0.0)), 'TapeDeck': Vector((0.0, 1.0, 0.3)), 'MeteoScreen': Vector((2.2, 1.6, 0.0))}
PLACEMENTS = {}                  # where the forest_far prefabs take these models: root -> [dict(parent, package, pos, yaw, note)]
ROOT_OF = {}
MERGE = {}                       # panel-atlas KB -> the body it is joined into (a second material on that mesh)
BOXES = []                       # colliders: (name, parent, (x0, x1, y0, y1, z0, z1), rot or None) in the root frame
KIT_INST = {}                    # snow_kit instances: name -> dict(item, parent, pos, note)
(Z_BEIGE, Z_BEIGE_D, Z_RUBBER, Z_SLOT, Z_CORD, Z_TRAY, Z_CASS, Z_CARDB, Z_TAPE, Z_GREEN, Z_GALV, Z_CONC, Z_STEEL,
 Z_METAL, Z_LAP, Z_LAP_D, Z_BTN_G, Z_BTN_R, Z_COIL, Z_LOCK, Z_MOUSE, Z_DECK, Z_SCRWHITE, Z_SCRLEG, Z_SCRWOOD, Z_SCRSTEEL,
 Z_SCRMETAL, Z_SCRBLACK, Z_CLOTH, Z_BOTTLE) = range(400, 430)
DEV_ZONES = list(range(400, 430))


def reg(name, atlas, root, merge=None):
    ROOT_OF[name] = root
    if merge:
        MERGE[name] = merge
    return kb(name, atlas)


def obox(k, c, size, zone, R=None):
    """oriented box: centre c, size (sx, sy, sz) along the columns of R"""
    k.box_m(Vector(c), size, zone, R if R is not None else Matrix.Identity(3))


def box_uv(k, c, size, R, uvrect):
    """oriented box with every face mapped to uvrect (a solid-colour tile of the panel atlas)"""
    u0, v0, u1, v1 = uvrect
    for f in k.box_m(Vector(c), size, 0.0, R):
        for l, t in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
            l[k.uvl].uv = t


def frame_of(t, side=Vector((1, 0, 0))):
    """3x3 with columns (side, t, n): a plate lying along t, its normal n = side x t"""
    t = Vector(t).normalized()
    n = side.cross(t).normalized()
    return Matrix((side, t, n)).transposed()


def path_len(pts):
    return sum((b - a).length for a, b in zip(pts[:-1], pts[1:]))


def path_at(pts, s):
    for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
        L = (b - a).length
        if s <= L or i == len(pts) - 2:
            f = min(max(s / max(L, 1e-9), 0.0), 1.0)
            return a.lerp(b, f), (b - a).normalized()
        s -= L


def coil(k, pts, r_coil, r_wire, pitch, zone, per_turn=4):
    """a coiled cord: a helix of radius r_coil wound along the polyline pts (one turn per `pitch`), drawn as a thin tube"""
    pts = [Vector(p) for p in pts]
    L = path_len(pts)
    n = max(8, int(L / pitch * per_turn))
    out, e1 = [], None
    for i in range(n + 1):
        s = L * i / n
        p, t = path_at(pts, s)
        ref = e1 if e1 is not None else (Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0)))
        e1 = (ref - t * ref.dot(t)).normalized()
        e2 = t.cross(e1)
        ph = 2 * math.pi * s / pitch
        out.append(p + (e1 * math.cos(ph) + e2 * math.sin(ph)) * r_coil)
    k.tube(out, r_wire, zone, 3)


# ================================================================ Fax
FAX_SLOPE_A, FAX_SLOPE_B = Vector((0.0, -0.115, 0.060)), Vector((0.0, 0.025, 0.090))
FAX_UP = (FAX_SLOPE_B - FAX_SLOPE_A).normalized()
FAX_N = Vector((0.0, -FAX_UP.z, FAX_UP.y))                   # the panel's outward normal (up and to the front)
FAX_PC = Vector((0.045, 0.0, 0.0)) + (FAX_SLOPE_A + FAX_SLOPE_B) / 2 + FAX_N * 0.001   # the panel's centre
FAX_PW, FAX_PH = 0.20, 0.10
BAY_Z = 0.068                                                # the handset bay's top


def fax_panel_point(px, py, lift=0.0):
    """a pixel of the fax panel region (200 x 100) -> a point on the panel"""
    u = (px / 200.0 - 0.5) * FAX_PW
    v = (0.5 - py / 100.0) * FAX_PH
    return FAX_PC + Vector((u, 0, 0)) + FAX_UP * v + FAX_N * lift


def build_fax():
    k = reg('Fax', 'Devices', 'Fax')
    poly = [(-0.12, 0.0), (0.12, 0.0), (0.12, 0.105), (0.035, 0.105), (0.025, 0.090), (-0.115, 0.060), (-0.12, 0.055)]
    prism_x(k, poly, -0.09, 0.17, Z_BEIGE, Z_BEIGE, [Z_BEIGE_D, Z_BEIGE, Z_BEIGE, Z_BEIGE, Z_BEIGE, Z_BEIGE, Z_BEIGE])
    polyl = [(-0.12, 0.0), (0.12, 0.0), (0.12, BAY_Z), (-0.12, BAY_Z)]                 # the handset bay (left)
    prism_x(k, polyl, -0.17, -0.09, Z_BEIGE, None, [Z_BEIGE_D, Z_BEIGE, Z_BEIGE, Z_BEIGE])
    k.box(-0.170, -0.163, -0.12, 0.12, BAY_Z, BAY_Z + 0.008, Z_BEIGE)                  # the cradle's outer lip
    k.box(-0.138, -0.122, -0.012, 0.012, BAY_Z, BAY_Z + 0.009, Z_BEIGE_D)              # the hook switch
    # the panel (explicit UVs, merged into the body), the LCD, START / STOP, the LEDs
    pn = reg('Fax_Panel', 'panel', 'Fax', merge='Fax')
    quad(pn, FAX_PC, FAX_N, FAX_PW, FAX_PH, uv('fax_panel'), up=FAX_UP)
    lcd = reg('Fax_LCD', 'lcd', 'Fax')
    c_lcd = fax_panel_point(50, 19, 0.0012)
    quad(lcd, c_lcd, FAX_N, 0.072, 0.019, (0.0, 0.0, 1.0, 1.0), up=FAX_UP)
    part('Fax_LCD', 'static', c_lcd, parent='Fax',
         note='the LCD: M_Dev_FaxLCD (lit: READY 07:30) / M_Dev_FaxLCD_Off; its own texture, full 0..1 UVs (u right, v up '
              'the panel) - the game may draw its own text')
    R = Matrix((Vector((1, 0, 0)), FAX_UP, FAX_N)).transposed()
    for nm, px, tile, note in (('Fax_Btn_Start', 131, 'btn_green', 'START (green): pushes in 3 mm - send / receive / copy'),
                               ('Fax_Btn_Stop', 171, 'btn_red', 'STOP (red): pushes in 3 mm')):
        b = reg(nm, 'panel', 'Fax')
        c = fax_panel_point(px, 58, 0.0035)
        box_uv(b, c, (0.020, 0.011, 0.006), R, uv(tile))
        part(nm, 'slide', c, axis=-FAX_N, rng=(0.0, 0.003), unit='m', parent='Fax', note=note)
    for nm, py, kind, txt in (('Fax_LED_Ready', 14, 'led_g', 'READY (green)'), ('Fax_LED_Error', 26, 'led_r', 'ERROR (red)')):
        l = reg(nm, 'lens:' + kind, 'Fax')
        c = fax_panel_point(130, py, 0.0012)
        quad(l, c, FAX_N, 0.006, 0.006, uv('led_green' if kind == 'led_g' else 'led_red'), up=FAX_UP)
        mat = 'M_Dev_LED' + ('G' if kind == 'led_g' else 'R')
        part(nm, 'static', c, parent='Fax', note=f'{txt} LED: {mat} (lit) / {mat}_Off')
    # the document feeder at the back: an inclined guide plate with side guides, the dark slit in the top
    a, b_ = Vector((0.0, 0.040, 0.106)), Vector((0.0, 0.128, 0.170))
    Rg = frame_of(b_ - a)
    mid = (a + b_) / 2
    obox(k, (0.045, mid.y, mid.z), (0.20, (b_ - a).length, 0.003), Z_TRAY, Rg)
    nrm = Rg.col[2]
    for xg in (-0.052, 0.142):
        obox(k, Vector((xg, mid.y, mid.z)) + nrm * 0.011, (0.004, (b_ - a).length, 0.022), Z_TRAY, Rg)
    face(k, [(-0.06, 0.036, 0.1053), (0.15, 0.036, 0.1053), (0.15, 0.046, 0.1053), (-0.06, 0.046, 0.1053)], Z_SLOT, (0, 0, 1))
    # the exit slot and its tray at the front
    face(k, [(-0.06, -0.1205, 0.036), (0.15, -0.1205, 0.036), (0.15, -0.1205, 0.044), (-0.06, -0.1205, 0.044)], Z_SLOT,
         (0, -1, 0))
    for (y0, z0, y1, z1) in ((-0.120, 0.031, -0.150, 0.029), (-0.150, 0.029, -0.172, 0.036)):
        tt = Vector((0, y1 - y0, z1 - z0))
        obox(k, (0.045, (y0 + y1) / 2, (z0 + z1) / 2), (0.21, tt.length + 0.002, 0.003), Z_TRAY, frame_of(tt))
    for xf in (-0.15, 0.15):                                                           # rubber feet
        for yf in (-0.10, 0.10):
            k.box(xf - 0.012, xf + 0.012, yf - 0.012, yf + 0.012, -0.004, 0.0, Z_RUBBER)
    # the handset: the ear and mouth cups on the bay, the handle bent down into them (lifted by the game)
    h = reg('Fax_Handset', 'Devices', 'Fax')
    hc = Vector((-0.130, 0.0, BAY_Z + 0.019))
    for ys in (-1, 1):
        cc = Vector((hc.x, ys * 0.084, BAY_Z + 0.002))
        h.lathe(cc, (0, 0, 1), [(0.0, 0.021), (0.004, 0.025), (0.015, 0.025), (0.020, 0.019)], Z_BEIGE, seg=10)
        h.cyl(cc, cc - Vector((0, 0, 0.001)), 0.016, Z_BEIGE_D, 10)
    h.strip([(hc.x, -0.098, BAY_Z + 0.017), (hc.x, -0.072, BAY_Z + 0.030), (hc.x, 0.072, BAY_Z + 0.030),
             (hc.x, 0.098, BAY_Z + 0.017)], (0, 0, 1), 0.034, 0.016, Z_BEIGE)
    part('Fax_Handset', 'item', hc, parent='Fax', note='the handset: lifted / put back by the game (Hand_Handset); its coiled '
                                                       'cord stays on the body - hide or stretch it while lifted')
    socket('Hand_Handset', hc + Vector((0, 0, 0.019)), 'hand', parent='Fax_Handset', note='grip the handset (the bar)')
    coil(k, [(-0.150, -0.110, BAY_Z + 0.004), (-0.168, -0.132, 0.040), (-0.180, -0.104, 0.008), (-0.180, -0.020, 0.0065),
             (-0.174, 0.020, 0.026)], 0.0045, 0.0016, 0.016, Z_COIL)
    k.tube([(0.12, 0.121, 0.020), (0.125, 0.16, 0.006), (0.13, 0.24, 0.003)], 0.0035, Z_CORD, 5)
    k.tube([(0.08, 0.121, 0.020), (0.075, 0.16, 0.006), (0.05, 0.24, 0.003)], 0.003, Z_CORD, 5)
    part('Fax', 'static', (0, 0, 0), note='the fax (root): origin on the desk under its middle; the handset bay on the left, '
                                          'the panel sloping to the front, the feeder at the back')
    socket('Slot_DocIn', (0.045, 0.041, 0.108), 'slot', parent='Fax', dir=(b_ - a).normalized() * -1,
           note='the document feeder: a form laid face down on the guide slides down into the slit')
    socket('Slot_PaperOut', (0.045, -0.125, 0.040), 'slot', parent='Fax', dir=(0.0, -1.0, 0.0),
           note='the exit slot: a received fax (FaxPaper) comes out here onto the tray')
    BOXES.extend([('Fax_Body', 'Fax', (-0.17, 0.17, -0.12, 0.12, 0.0, 0.105), None),
                  ('Fax_Handset', 'Fax_Handset', (-0.155, -0.105, -0.11, 0.11, BAY_Z + 0.002, BAY_Z + 0.038), None)])


# ================================================================ FaxPaper
def build_paper():
    k = reg('FaxPaper', 'paper', 'FaxPaper')
    W, L = 0.210, 0.297
    ys = np.linspace(-L / 2, L / 2, 9)

    def zc(y):
        s = (y + L / 2) / L
        return 0.0006 + 0.030 * max(0.0, (s - 0.62) / 0.38) ** 2.2

    BU = (0.006, 0.006, 0.030, 0.030)                       # the back: a blank corner of the sheet (keep it unprinted)
    for i in range(len(ys) - 1):
        ya, yb = ys[i], ys[i + 1]
        va, vb = (ya + L / 2) / L, (yb + L / 2) / L
        pts = [Vector((-W / 2, ya, zc(ya))), Vector((W / 2, ya, zc(ya))), Vector((W / 2, yb, zc(yb))), Vector((-W / 2, yb, zc(yb)))]
        k.poly(pts, 0.0, [(0.0, va), (1.0, va), (1.0, vb), (0.0, vb)])
        back = [p - Vector((0, 0, 0.0002)) for p in reversed(pts)]
        k.poly(back, 0.0, [(BU[0], BU[3]), (BU[2], BU[3]), (BU[2], BU[1]), (BU[0], BU[1])])
    part('FaxPaper', 'item', (0, 0, 0), note='a received fax: A4 thermal paper, the far end curls up; M_Dev_FaxPaper (its own '
                                               'texture): the face has full 0..1 UVs (u across, v from the leading edge = the '
                                               'top of the page) - the game prints the text; the back maps to the corner u, v '
                                               '0.006..0.03 (keep it blank)')
    BOXES.append(('FaxPaper', 'FaxPaper', (-0.105, 0.105, -0.1485, 0.1485, 0.0, 0.01), None))


# ================================================================ Cassette, CassetteBox
CASS = (0.1003, 0.0638, 0.0120)


def build_cassette():
    k = reg('Cassette', 'Devices', 'Cassette')
    W, D, H = CASS
    box6(k, (-W / 2, -D / 2, 0.0), (W / 2, D / 2, H), Z_CASS, skip=('+z', '-z'))
    lb = reg('Cassette_Label', 'panel', 'Cassette', merge='Cassette')
    quad(lb, (0, 0, H), (0, 0, 1), W, D, uv('cass_label'), up=(0, 1, 0))
    quad(lb, (0, 0, 0), (0, 0, -1), W, D, uv('cass_label'), up=(0, 1, 0))
    part('Cassette', 'item', (0, 0, H / 2), note='the telemetry tape (compact cassette, C-60), label on both faces; pivot at '
                                                 'its middle, the tape edge (head openings) to -y')
    BOXES.append(('Cassette', 'Cassette', (-W / 2, W / 2, -D / 2, D / 2, 0.0, H), None))


def build_box():
    k = reg('CassetteBox', 'Devices', 'CassetteBox')
    W, D, H = 0.180, 0.115, 0.075
    box6(k, (-W / 2, -D / 2, 0.0), (W / 2, D / 2, H), Z_CARDB)
    t = 0.0006
    k.strip([(-W / 2 - t, 0, H - 0.030), (-W / 2 - t, 0, H + t), (W / 2 + t, 0, H + t), (W / 2 + t, 0, H - 0.030)], (0, 1, 0),
            0.0012, 0.044, Z_TAPE)                                                     # the tape over the lid
    lb = reg('CassetteBox_Label', 'panel', 'CassetteBox', merge='CassetteBox')
    quad(lb, (0, -D / 2 - 0.0005, H * 0.48), (0, -1, 0), 0.16, 0.055, uv('cbox_front'))
    quad(lb, (0, 0.040, H + 0.0004), (0, 0, 1), 0.085, 0.0345, uv('cbox_top'), up=(0, 1, 0))
    part('CassetteBox', 'item', (0, 0, 0), note='the day-2 delivery: a taped carton of ten telemetry tapes; origin under its '
                                                'middle (it does not open - the game hands out Cassette items)')
    BOXES.append(('CassetteBox', 'CassetteBox', (-W / 2, W / 2, -D / 2, D / 2, 0.0, H), None))


# ================================================================ DropBox
DB = dict(x=0.20, y=0.15, z0=1.00, z1=1.42)


def build_dropbox():
    k = reg('DropBox', 'Outdoor', 'DropBox')
    box6(k, (-0.18, -0.18, -0.30), (0.18, 0.18, 0.05), Z_CONC)
    box6(k, (-0.03, -0.03, 0.058), (0.03, 0.03, DB['z0'] + 0.10), Z_GALV, skip=('-z',))
    k.box(-0.06, 0.06, -0.06, 0.06, 0.05, 0.058, Z_GALV)                               # the base plate, four bolts
    for xs in (-1, 1):
        for ys in (-1, 1):
            k.cyl((xs * 0.045, ys * 0.045, 0.058), (xs * 0.045, ys * 0.045, 0.068), 0.008, Z_GALV, 6)
    x, y, z0, z1 = DB['x'], DB['y'], DB['z0'], DB['z1']
    box6(k, (-x, -y, z0), (x, y, z1), Z_GREEN)
    # the roof: a cap sloping to the back, the overhang shelters the slot
    poly = [(-y - 0.035, z1), (y + 0.025, z1), (y + 0.025, z1 + 0.025), (-y - 0.035, z1 + 0.060)]
    prism_x(k, poly, -x - 0.025, x + 0.025, Z_GREEN, Z_GREEN, [Z_GREEN, Z_GREEN, Z_GREEN, Z_GREEN])
    # the slot (dark) under a drip lip; its flap
    face(k, [(-0.085, -y - 0.0008, 1.300), (0.085, -y - 0.0008, 1.300), (0.085, -y - 0.0008, 1.332), (-0.085, -y - 0.0008, 1.332)],
         Z_SLOT, (0, -1, 0))
    k.box(-0.10, 0.10, -y - 0.006, -y, 1.338, 1.350, Z_GREEN)
    f = reg('DropBox_Flap', 'Outdoor', 'DropBox')
    f.box(-0.088, 0.088, -y - 0.004, -y - 0.001, 1.298, 1.334, Z_STEEL)
    part('DropBox_Flap', 'hinge', (0.0, -y - 0.0025, 1.334), axis=(1, 0, 0), rng=(0, 70), parent='DropBox',
         note='the slot\'s flap: hinge along its top edge, swings in (into the box) up to 70 deg when a tape goes in')
    # the courier's door: a raised panel, hinges on the left, the lock
    k.box(-0.16, 0.16, -y - 0.006, -y, 1.04, 1.27, Z_GREEN)
    for zz in (1.07, 1.24):
        k.cyl((-0.166, -y - 0.008, zz - 0.02), (-0.166, -y - 0.008, zz + 0.02), 0.006, Z_STEEL, 6)
    k.cyl((0.12, -y - 0.006, 1.155), (0.12, -y - 0.016, 1.155), 0.010, Z_LOCK, 8)
    pl = reg('DropBox_Plate', 'panel', 'DropBox', merge='DropBox')
    quad(pl, (-0.015, -y - 0.0068, 1.155), (0, -1, 0), 0.22, 0.11, uv('drop_plate'))
    part('DropBox', 'static', (0, 0, 0), note='the tape drop box (root): origin on the ground at the post (the footing goes 0.30 '
                                              'in); the slot faces the front (-y)')
    socket('Slot_Cassette', (0.0, -y - 0.004, 1.316), 'slot', parent='DropBox', dir=(0, 1, 0),
           note='push a tape in here (the flap swings); the courier empties the box overnight')
    BOXES.extend([('DropBox_Box', 'DropBox', (-x - 0.025, x + 0.025, -y - 0.035, y + 0.025, z0, z1 + 0.06), None),
                  ('DropBox_Post', 'DropBox', (-0.03, 0.03, -0.03, 0.03, 0.0, z0), None),
                  ('DropBox_Footing', 'DropBox', (-0.18, 0.18, -0.18, 0.18, -0.30, 0.05), None)])


# ================================================================ ObjectPC
PC = dict(w=0.42, d=0.40, h=0.14)
MOUSE = Vector((0.33, -0.40, 0.0))


def pc_front_point(px, py, lift=0.0):
    """a pixel of the pc_front region (168 x 56) -> a point on the bezel"""
    w, d, h = PC['w'], PC['d'], PC['h']
    zc, hh, ww = (0.012 + h - 0.004) / 2, h - 0.016, w - 0.01
    return Vector(((px / 168.0 - 0.5) * ww, -d / 2 - 0.0005 - lift, zc + (0.5 - py / 56.0) * hh))


def build_pc():
    k = reg('ObjectPC', 'Devices', 'ObjectPC')
    w, d, h = PC['w'], PC['d'], PC['h']
    box6(k, (-w / 2, -d / 2 + 0.012, 0.012), (w / 2, d / 2, h), {'*': Z_BEIGE, '+y': Z_METAL, '-y': Z_BEIGE_D, '-z': Z_BEIGE_D})
    box6(k, (-w / 2 + 0.005, -d / 2, 0.012), (w / 2 - 0.005, -d / 2 + 0.012, h - 0.004), Z_BEIGE_D, skip=('-y', '+y'))
    fr = reg('ObjectPC_Front', 'panel', 'ObjectPC', merge='ObjectPC')
    quad(fr, ((0.0, -d / 2 - 0.0005, (0.012 + h - 0.004) / 2)), (0, -1, 0), w - 0.01, h - 0.016, uv('pc_front'))
    for xs in (-1, 1):
        for ys in (-1, 1):
            k.box(xs * (w / 2 - 0.04) - 0.015, xs * (w / 2 - 0.04) + 0.015, ys * (d / 2 - 0.04) - 0.015,
                  ys * (d / 2 - 0.04) + 0.015, 0.0, 0.012, Z_RUBBER)
    pw = reg('ObjectPC_Power', 'Devices', 'ObjectPC')
    pc_ = pc_front_point(70, 40, 0.004)
    obox(pw, pc_, (0.020, 0.008, 0.012), Z_BEIGE_D)
    part('ObjectPC_Power', 'slide', pc_, axis=(0, 1, 0), rng=(0.0, 0.004), unit='m', parent='ObjectPC',
         note='POWER: pushes in 4 mm (on / off)')
    led = reg('ObjectPC_LED', 'lens:led_g', 'ObjectPC')
    lc = pc_front_point(56, 41, 0.0003)
    quad(led, lc, (0, -1, 0), 0.006, 0.004, uv('led_green'))
    part('ObjectPC_LED', 'static', lc, parent='ObjectPC', note='the power LED: M_Dev_LEDG (lit) / M_Dev_LEDG_Off')
    # the keyboard: a wedge, the key field on its slope (panel), its cable round the left of the case to the back
    kb_ = reg('PC_Keyboard', 'Devices', 'ObjectPC')
    kc = Vector((0.0, -0.40, 0.0))
    polyk = [(-0.095, 0.0), (0.095, 0.0), (0.095, 0.040), (-0.095, 0.024)]
    prism_x(kb_, [(yy + kc.y, zz) for yy, zz in polyk], -0.23, 0.23, Z_BEIGE, Z_BEIGE, [Z_BEIGE_D, Z_BEIGE, Z_BEIGE, Z_BEIGE])
    up = Vector((0, 0.19, 0.016)).normalized()
    nk = Vector((0, -up.z, up.y))
    kk = reg('PC_Keyboard_Keys', 'panel', 'ObjectPC', merge='PC_Keyboard')
    quad(kk, kc + Vector((0, 0.0, 0.032)) + nk * 0.0008, nk, 0.44, 0.17, uv('kbd'), up=up)
    kb_.tube([kc + Vector((0.0, 0.095, 0.030)), kc + Vector((0.0, 0.135, 0.004)), (-0.15, -0.245, 0.004), (-0.222, -0.18, 0.004),
              (-0.222, 0.19, 0.004), (-0.18, 0.212, 0.040), (-0.18, 0.200, 0.050)], 0.003, Z_CORD, 5)
    part('PC_Keyboard', 'static', kc, parent='ObjectPC', note='the keyboard: its own object (move it with the desk); the cable '
                                                              'runs round the left of the case into the back')
    ms = reg('PC_Mouse', 'Devices', 'ObjectPC')
    ms.superdome(MOUSE, (0, 0, 1), Vector((0, 1, 0)), 0.031, 0.056, 0.032, (0.0, 0.0, 1.0, 1.0), nu=8, nv=8, p=4.0, prof='dome',
                 zone=Z_MOUSE)
    ms.tube([MOUSE + Vector((0, 0.054, 0.010)), MOUSE + Vector((0, 0.090, 0.003)), (0.30, -0.25, 0.003), (0.226, -0.15, 0.003),
             (0.226, 0.19, 0.003), (0.18, 0.212, 0.040), (0.18, 0.200, 0.046)], 0.0022, Z_CORD, 4)
    part('PC_Mouse', 'static', MOUSE, parent='ObjectPC', note='the mouse (two buttons): its own object; the cable runs round the '
                                                              'right of the case into the back')
    part('ObjectPC', 'static', (0, 0, 0), note='the object computer (root): the case, origin on the desk under its middle; '
                                               'the monitor: a snow_kit Kit_Monitor_CRT at Kit_Monitor_CRT (kit_instances)')
    socket('Kit_Monitor_CRT', (0.0, 0.0, h), 'kit', parent='ObjectPC', dir=(0, -1, 0),
           note='an instance of snow_kit Kit_Monitor_CRT: its origin (the middle of its bottom) here, facing the front (-y); '
                'the game shows the picture on its screen object (Kit_Monitor_Screen)')
    socket('Slot_Floppy', pc_front_point(120, 34, 0.0015), 'slot', parent='ObjectPC', dir=(0, 1, 0),
           note='the 3.5" floppy drive slot')
    KIT_INST['Monitor_PC'] = dict(item='Kit_Monitor_CRT', parent='ObjectPC', pos=Vector((0.0, 0.0, h)),
                                  note='the object computer\'s monitor (snow_kit K2) on the case')
    BOXES.extend([('ObjectPC_Case', 'ObjectPC', (-w / 2, w / 2, -d / 2, d / 2, 0.0, h), None),
                  ('PC_Keyboard', 'PC_Keyboard', (-0.23, 0.23, -0.495, -0.305, 0.0, 0.04), None),
                  ('PC_Mouse', 'PC_Mouse', (MOUSE.x - 0.031, MOUSE.x + 0.031, MOUSE.y - 0.056, MOUSE.y + 0.056, 0.0, 0.032), None)])


# ================================================================ Laptop
LAP = dict(w=0.300, d=0.230, h=0.034, lid=0.011)


def build_laptop():
    k = reg('Laptop', 'Devices', 'Laptop')
    w, d, h, lt = LAP['w'], LAP['d'], LAP['h'], LAP['lid']
    box6(k, (-w / 2, -d / 2, 0.004), (w / 2, d / 2, h), {'*': Z_LAP, '-z': Z_LAP_D})
    for xs in (-1, 1):
        for ys in (-1, 1):
            k.box(xs * (w / 2 - 0.02) - 0.01, xs * (w / 2 - 0.02) + 0.01, ys * (d / 2 - 0.02) - 0.008,
                  ys * (d / 2 - 0.02) + 0.008, 0.0, 0.004, Z_RUBBER)
    kk = reg('Laptop_Keys', 'panel', 'Laptop', merge='Laptop')
    quad(kk, (0.0, 0.040, h + 0.0006), (0, 0, 1), 0.270, 0.122, uv('lap_kbd'), up=(0, 1, 0))
    k.lathe((0.0, -0.068, h - 0.002), (0, 0, 1), [(0.0, 0.0125), (0.0035, 0.0115), (0.0065, 0.008), (0.008, 0.003), (0.0085, 0.0)],
            Z_LAP_D, seg=10)                                                           # the trackball
    for xs in (-1, 1):
        k.box(xs * 0.030 - 0.018, xs * 0.030 + 0.018, -0.100, -0.088, h, h + 0.002, Z_LAP_D)
    led = reg('Laptop_LED', 'lens:led_g', 'Laptop')
    lc = Vector((0.10, -d / 2 - 0.0006, 0.022))
    quad(led, lc, (0, -1, 0), 0.010, 0.003, uv('led_green'))
    part('Laptop_LED', 'static', lc, parent='Laptop', note='the power LED: M_Dev_LEDG (lit) / M_Dev_LEDG_Off')
    # the lid (closed on the base): two hinge knuckles at the back, opens to the back
    piv = Vector((0.0, d / 2 - 0.007, h + 0.0075))
    lid = reg('IX_LaptopLid', 'Devices', 'Laptop')
    box6(lid, (-w / 2, -d / 2 + 0.004, h + 0.002), (w / 2, d / 2 - 0.012, h + 0.002 + lt), {'*': Z_LAP, '-z': Z_LAP_D})
    for xs in (-1, 1):
        lid.cyl((xs * 0.11 - 0.03, piv.y, piv.z), (xs * 0.11 + 0.03, piv.y, piv.z), 0.0055, Z_LAP_D, 8)
    scr = reg('Laptop_Screen', 'screen', 'Laptop')
    sc_c = Vector((0.0, -0.004, h + 0.0015))
    quad(scr, sc_c, (0, 0, -1), 0.244, 0.183, (0.0, 0.0, 1.0, 1.0), up=(0, -1, 0))
    part('IX_LaptopLid', 'hinge', piv, axis=(-1, 0, 0), rng=(0, 115), parent='Laptop', states=['closed', 'open'],
         note='the lid, closed in the model: hinge along the back edge, opens up to 115 deg (on a desk ~105)')
    part('Laptop_Screen', 'static', sc_c, parent='IX_LaptopLid',
         note='the screen: M_Dev_ScreenOff (its own texture); full 0..1 UVs (u left-right, v bottom-top as seen with the lid '
              'open) - the game\'s picture')
    part('Laptop', 'static', (0, 0, 0), note='the notebook (root): origin on the desk under its middle')
    BOXES.extend([('Laptop_Base', 'Laptop', (-w / 2, w / 2, -d / 2, d / 2, 0.0, h), None),
                  ('Laptop_Lid', 'IX_LaptopLid', (-w / 2, w / 2, -d / 2 + 0.004, d / 2 - 0.001, h + 0.002, h + 0.002 + lt), None)])


# ================================================================ TapeDeck (the telemetry recorder in the dish cabinets)
DECK = dict(w=0.94, h=0.27, t=0.024)
DECK_MOUNT = Vector((4.20, -2.94, 1.30))        # forest_far dish frame: the front of the cabinet's third module (z 1.16..1.44)


def deck_point(px, py, lift=0.0):
    """a pixel of the deck_front region -> a point on the faceplate (the front plane y = -t; lift: further out)"""
    W, H = DT.DECK_PX
    return Vector(((px / W - 0.5) * DECK['w'], -DECK['t'] - lift, (0.5 - py / H) * DECK['h']))


def panel_with_hole(k, w, h, y, uvr, hole):
    """a panel facing -y in the plane y (x across, z up, centred on 0), uvr over all of it, the rectangle hole
    (x0, z0, x1, z1) left open: up to four quads"""
    U0, V0, U1, V1 = uvr
    hx0, hz0, hx1, hz1 = hole

    def q(x0, x1, z0, z1):
        if x1 - x0 < 1e-6 or z1 - z0 < 1e-6:
            return
        uu = [U0 + (x + w / 2) / w * (U1 - U0) for x in (x0, x1)]
        vv = [V0 + (z + h / 2) / h * (V1 - V0) for z in (z0, z1)]
        k.poly([Vector((x0, y, z0)), Vector((x1, y, z0)), Vector((x1, y, z1)), Vector((x0, y, z1))], 0.0,
               [(uu[0], vv[0]), (uu[1], vv[0]), (uu[1], vv[1]), (uu[0], vv[1])])
    q(-w / 2, w / 2, -h / 2, hz0)
    q(-w / 2, w / 2, hz1, h / 2)
    q(-w / 2, hx0, hz0, hz1)
    q(hx1, w / 2, hz0, hz1)


def build_deck():
    k = reg('TapeDeck', 'Devices', 'TapeDeck')
    w, h, t = DECK['w'], DECK['h'], DECK['t']
    box6(k, (-w / 2, -t, -h / 2), (w / 2, 0.0, h / 2), Z_DECK, skip=('-y',))
    hx0, hy0, hx1, hy1 = DT.DECK_HOLE
    a, b = deck_point(hx0, hy1), deck_point(hx1, hy0)                                 # the opening: left-bottom, right-top
    xa, xb, za, zb, yb_ = a.x, b.x, a.z, b.z, -0.002
    face(k, [(xa, -t, za), (xa, yb_, za), (xa, yb_, zb), (xa, -t, zb)], Z_SLOT, (1, 0, 0))   # the cassette compartment
    face(k, [(xb, -t, za), (xb, yb_, za), (xb, yb_, zb), (xb, -t, zb)], Z_SLOT, (-1, 0, 0))
    face(k, [(xa, -t, za), (xb, -t, za), (xb, yb_, za), (xa, yb_, za)], Z_SLOT, (0, 0, 1))
    face(k, [(xa, -t, zb), (xb, -t, zb), (xb, yb_, zb), (xa, yb_, zb)], Z_SLOT, (0, 0, -1))
    face(k, [(xa, yb_, za), (xb, yb_, za), (xb, yb_, zb), (xa, yb_, zb)], Z_SLOT, (0, -1, 0))
    for zz in (za + 0.004, zb - 0.004):                                                # the cassette's guides
        k.box(xa + 0.010, xa + 0.016, -0.004, yb_, zz - 0.002, zz + 0.002, Z_LAP_D)
        k.box(xb - 0.016, xb - 0.010, -0.004, yb_, zz - 0.002, zz + 0.002, Z_LAP_D)
    pn = reg('TapeDeck_Panel', 'panel', 'TapeDeck', merge='TapeDeck')
    panel_with_hole(pn, w, h, -t - 0.0004, uv('deck_front'), (xa, za, xb, zb))
    # the keys: REC (red), PLAY, REW, FF, STOP / EJECT - each pushes in 4 mm
    names = ['Rec', 'Play', 'Rew', 'FF', 'Stop']
    notes = ['REC (red): record - with PLAY held in, as on any deck', 'PLAY', 'REW: rewind', 'FF: fast forward',
             'STOP / EJECT: stops; pressed again it opens the door (IX_TapeDoor)']
    for i, (px0, py0, px1, py1) in enumerate(DT.DECK_KEYS):
        c0, c1 = deck_point(px0, py1), deck_point(px1, py0)
        c = Vector(((c0.x + c1.x) / 2, -t - 0.003, (c0.z + c1.z) / 2))
        nm = 'TapeDeck_Key_' + names[i]
        kk = reg(nm, 'panel', 'TapeDeck')
        box_uv(kk, c, (c1.x - c0.x - 0.002, 0.006, c1.z - c0.z - 0.002), None, uv('key_red' if i == 0 else 'key_grey'))
        part(nm, 'slide', c, axis=(0, 1, 0), rng=(0.0, 0.004), unit='m', parent='TapeDeck', note=notes[i])
    for nm, px, py, kind, txt in (('TapeDeck_LED_Rec', 62, 25, 'led_r', 'REC (red): lit while recording'),
                                  ('TapeDeck_LED_Power', 222, 40, 'led_g', 'POWER (green)')):
        l = reg(nm, 'lens:' + kind, 'TapeDeck')
        c = deck_point(px, py, 0.0008)
        quad(l, c, (0, -1, 0), 0.012, 0.009, uv('led_green' if kind == 'led_g' else 'led_red'))
        mat = 'M_Dev_LED' + ('G' if kind == 'led_g' else 'R')
        part(nm, 'static', c, parent='TapeDeck', note=f'{txt} LED: {mat} (lit) / {mat}_Off')
    # the cassette door: a dark frame with a smoked window, hinged along its bottom edge, tilts out
    g, fw = 0.0006, 0.006
    x0d, x1d, z0d, z1d = xa + g, xb - g, za + g, zb - g
    yd0, yd1 = -t, -t + 0.005
    d = reg('IX_TapeDoor', 'Devices', 'TapeDeck')
    d.box(x0d, x1d, yd0, yd1, z0d, z0d + fw, Z_LAP_D)
    d.box(x0d, x1d, yd0, yd1, z1d - fw, z1d, Z_LAP_D)
    d.box(x0d, x0d + fw, yd0, yd1, z0d + fw, z1d - fw, Z_LAP_D)
    d.box(x1d - fw, x1d, yd0, yd1, z0d + fw, z1d - fw, Z_LAP_D)
    d.box((x0d + x1d) / 2 - 0.012, (x0d + x1d) / 2 + 0.012, yd0 - 0.003, yd0, z1d - fw, z1d - 0.001, Z_LAP_D)   # finger grip
    win = reg('TapeDeck_Window', 'glass', 'TapeDeck')
    wc = Vector(((x0d + x1d) / 2, (yd0 + yd1) / 2, (z0d + z1d) / 2))
    quad(win, wc, (0, -1, 0), x1d - x0d - 2 * fw + 0.002, z1d - z0d - 2 * fw + 0.002, (0.0, 0.0, 1.0, 1.0))
    piv = Vector(((x0d + x1d) / 2, (yd0 + yd1) / 2, z0d))
    part('IX_TapeDoor', 'hinge', piv, axis=(1, 0, 0), rng=(0, 30), parent='TapeDeck', states=['closed', 'open'],
         note='the cassette door: hinge along its bottom edge, tilts out (to the front) up to 30 deg - STOP / EJECT opens it')
    part('TapeDeck_Window', 'static', wc, parent='IX_TapeDoor', note='the door\'s smoked window (M_Dev_Glass)')
    part('TapeDeck', 'static', (0, 0, 0), note='the telemetry recorder (root): a rack faceplate for the dish cabinets; origin '
                                               'in the middle of its back face (on the module it is fixed to), the front -y')
    cc = Vector(((xa + xb) / 2, -0.0125, (za + zb) / 2))
    socket('Slot_Tape', cc, 'slot', parent='TapeDeck', up=(0, -1, 0), forward=(0, 0, -1),
           note='a Cassette goes here: its origin (its middle) on this point, its +z (the label) to the front (-y), its tape '
                'edge (its -y) down (-z); seen through the window when the door is shut')
    BOXES.extend([('TapeDeck', 'TapeDeck', (-w / 2, w / 2, -t, 0.0, -h / 2, h / 2), None),
                  ('TapeDoor', 'IX_TapeDoor', (x0d, x1d, yd0 - 0.003, yd1, z0d, z1d), None)])
    PLACEMENTS['TapeDeck'] = [dict(parent=dn, package='forest_far', pos=DECK_MOUNT, yaw=180.0,
                                   note=f'in {dn}\'s equipment cabinet (behind {door}), on the third module from the bottom; '
                                        'faces the cabinet door (+y of the dish)')
                              for dn, door in (('Dish_1', 'IX_CabinetDoor_2'), ('Dish_2', 'IX_CabinetDoor_3'),
                                               ('Dish_3', 'IX_CabinetDoor_4'), ('Dish_4', 'IX_CabinetDoor_5'),
                                               ('Dish_5', 'IX_CabinetDoor_6'))]


# ================================================================ MeteoScreen (the Stevenson screen of the weather station)
SCR = dict(legs=(0.30, 0.25), box=(0.75, 0.60, 1.20, 1.90), roof=(0.85, 0.70, 1.905, 1.955), roof2=(0.91, 0.76, 2.005, 2.035))


def louvres(k, n_out, side, L, plane, z0, z1, pitch=0.07, width=0.05, zone=None):
    """a louvred wall: slats along `side` (length L) at 45 deg, the outer edge low (rain runs off), in the wall plane `plane`
    (a point on it; n_out its outward normal), their centres spread evenly from z0 to z1 about `pitch` apart"""
    n_out, side = Vector(n_out), Vector(side)
    t = (n_out - Vector((0, 0, 1))).normalized()
    R = frame_of(t, side)
    for zz in np.linspace(z0, z1, int(round((z1 - z0) / pitch)) + 1):
        obox(k, Vector(plane) + Vector((0, 0, float(zz))), (L, width, 0.008), zone, R)


def board(k, c, w, h, n, up, tile, side_tile, depth=0.004):
    """a thin board (w across, h along up) facing n: the face shows tile, the edges and the back side_tile"""
    n, up = Vector(n).normalized(), Vector(up).normalized()
    u = up.cross(n).normalized()
    R = Matrix((u, up, -n)).transposed()
    U0, V0, U1, V1 = side_tile
    for f in k.box_m(Vector(c) - n * depth / 2, (w, h, depth), 0.0, R):
        for l, t in zip(f.loops, ((U0, V0), (U1, V0), (U1, V1), (U0, V1))):
            l[k.uvl].uv = t
    k.quad_uv(Vector(c) + n * 0.0003, n, w, h, tile, up=up)


def drum(k, c, r, h, tile, top_tile, seg=12):
    """an upright drum with the tile wrapped once round its side (v up), the top capped"""
    c = Vector(c)
    U0, V0, U1, V1 = tile
    ring = [(c + Vector((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), 0.0))) for i in range(seg + 1)]
    for i in range(seg):
        a, b = ring[i], ring[i + 1]
        ua, ub = U0 + (U1 - U0) * i / seg, U0 + (U1 - U0) * (i + 1) / seg
        k.poly([a, b, b + Vector((0, 0, h)), a + Vector((0, 0, h))], 0.0, [(ua, V0), (ub, V0), (ub, V1), (ua, V1)])
    T0, W0, T1, W1 = top_tile
    k.poly([p + Vector((0, 0, h)) for p in ring[:seg]], 0.0, [((T0 + T1) / 2, (W0 + W1) / 2)] * seg)


def build_screen():
    k = reg('MeteoScreen', 'Outdoor', 'MeteoScreen')
    lx, ly = SCR['legs']
    bw, bd, bz0, bz1 = SCR['box']
    for xs in (-1, 1):                                                 # four legs braced, rails under the box
        for ys in (-1, 1):
            k.box(xs * lx - 0.03, xs * lx + 0.03, ys * ly - 0.03, ys * ly + 0.03, -0.30, bz0, Z_SCRLEG)
        k.box(xs * lx - 0.02, xs * lx + 0.02, -ly + 0.03, ly - 0.03, 0.45, 0.50, Z_SCRLEG)
        k.box(xs * lx - 0.02, xs * lx + 0.02, -ly + 0.03, ly - 0.03, 1.10, 1.15, Z_SCRLEG)
    for ys in (-1, 1):
        k.box(-lx + 0.03, lx - 0.03, ys * ly - 0.02, ys * ly + 0.02, 1.10, 1.15, Z_SCRLEG)
    # the box: slatted floor, bottom frame, corner posts, the lid; louvred back and sides
    for yy in (-0.22, -0.11, 0.0, 0.11, 0.22):
        k.box(-bw / 2 + 0.03, bw / 2 - 0.03, yy - 0.045, yy + 0.045, bz0, bz0 + 0.02, Z_SCRWHITE)
    for ys in (-1, 1):
        k.box(-bw / 2, bw / 2, ys * (bd / 2 - 0.015) - 0.015, ys * (bd / 2 - 0.015) + 0.015, bz0, bz0 + 0.04, Z_SCRWHITE)
    for xs in (-1, 1):
        k.box(xs * (bw / 2 - 0.015) - 0.015, xs * (bw / 2 - 0.015) + 0.015, -bd / 2 + 0.03, bd / 2 - 0.03, bz0, bz0 + 0.04,
              Z_SCRWHITE)
        for ys in (-1, 1):
            k.box(xs * (bw / 2 - 0.015) - 0.015, xs * (bw / 2 - 0.015) + 0.015, ys * (bd / 2 - 0.015) - 0.015,
                  ys * (bd / 2 - 0.015) + 0.015, bz0 + 0.04, bz1 - 0.04, Z_SCRWHITE)
    box6(k, (-bw / 2, -bd / 2, bz1 - 0.04), (bw / 2, bd / 2, bz1), Z_SCRWHITE)
    louvres(k, (0, 1, 0), (1, 0, 0), bw - 0.06, (0, bd / 2 - 0.015, 0), bz0 + 0.058, bz1 - 0.058, zone=Z_SCRWHITE)
    louvres(k, (-1, 0, 0), (0, 1, 0), bd - 0.06, (-bw / 2 + 0.015, 0, 0), bz0 + 0.058, bz1 - 0.058, zone=Z_SCRWHITE)
    louvres(k, (1, 0, 0), (0, -1, 0), bd - 0.06, (bw / 2 - 0.015, 0, 0), bz0 + 0.058, bz1 - 0.058, zone=Z_SCRWHITE)
    # the double roof on spacers
    rw, rd, rz0, rz1 = SCR['roof']
    box6(k, (-rw / 2, -rd / 2, rz0), (rw / 2, rd / 2, rz1), Z_SCRWHITE)
    for xs in (-1, 1):
        for ys in (-1, 1):
            k.box(xs * 0.30 - 0.015, xs * 0.30 + 0.015, ys * 0.24 - 0.015, ys * 0.24 + 0.015, bz1, rz0, Z_SCRWHITE)
            k.box(xs * 0.36 - 0.015, xs * 0.36 + 0.015, ys * 0.28 - 0.015, ys * 0.28 + 0.015, rz1, SCR['roof2'][2], Z_SCRWHITE)
    r2w, r2d, r2z0, r2z1 = SCR['roof2']
    box6(k, (-r2w / 2, -r2d / 2, r2z0), (r2w / 2, r2d / 2, r2z1), Z_SCRWHITE)
    # the door's hinge leaves on the left post, the turn button on the right post; the step in front
    for zz in (bz0 + 0.12, bz1 - 0.12):
        k.box(-bw / 2, -bw / 2 + 0.03, -bd / 2 - 0.004, -bd / 2, zz - 0.02, zz + 0.02, Z_SCRSTEEL)
    k.box(bw / 2 - 0.035, bw / 2 + 0.005, -bd / 2 - 0.008, -bd / 2 - 0.002, (bz0 + bz1) / 2 - 0.02, (bz0 + bz1) / 2 + 0.02,
          Z_SCRWOOD)
    k.cyl((bw / 2 - 0.015, -bd / 2 - 0.002, (bz0 + bz1) / 2), (bw / 2 - 0.015, -bd / 2, (bz0 + bz1) / 2), 0.004, Z_SCRSTEEL, 6)
    box6(k, (-0.25, -bd / 2 - 0.55, 0.0), (0.25, -bd / 2 - 0.25, 0.30), Z_SCRWOOD)
    # the door (IX_ScreenDoor): a frame of stiles and rails, louvres, a knob; hinged on the left, opens out
    dz0, dz1, dx = bz0 + 0.04, bz1 - 0.04, bw / 2 - 0.03
    d = reg('IX_ScreenDoor', 'Outdoor', 'MeteoScreen')
    yo, yi = -bd / 2, -bd / 2 + 0.025
    d.box(-dx, -dx + 0.035, yo, yi, dz0, dz1, Z_SCRWHITE)
    d.box(dx - 0.035, dx, yo, yi, dz0, dz1, Z_SCRWHITE)
    d.box(-dx + 0.035, dx - 0.035, yo, yi, dz0, dz0 + 0.04, Z_SCRWHITE)
    d.box(-dx + 0.035, dx - 0.035, yo, yi, dz1 - 0.04, dz1, Z_SCRWHITE)
    louvres(d, (0, -1, 0), (-1, 0, 0), 2 * dx - 0.07, (0, (yo + yi) / 2, 0), dz0 + 0.058, dz1 - 0.058, zone=Z_SCRWHITE)
    for zz in (bz0 + 0.12, bz1 - 0.12):
        d.box(-dx, -dx + 0.08, yo - 0.004, yo, zz - 0.02, zz + 0.02, Z_SCRSTEEL)
    d.lathe((dx - 0.0175, yo, (bz0 + bz1) / 2), (0, -1, 0), [(0.0, 0.008), (0.015, 0.008), (0.02, 0.013), (0.03, 0.013),
                                                            (0.032, 0.0)], Z_SCRWOOD, seg=8)
    part('IX_ScreenDoor', 'hinge', (-dx, yo, dz0), axis=(0, 0, -1), rng=(0, 110), parent='MeteoScreen', states=['closed', 'open'],
         note='the screen\'s door: hinge on the left (vertical), opens out to the front up to 110 deg; held shut by the turn '
              'button on the right post')
    # inside: the thermometer frame, the four thermometers (panel tiles), the wet bulb's water bottle and wick, the
    # thermohygrograph on the floor
    yf = 0.10
    for xs in (-1, 1):
        k.box(xs * 0.15 - 0.01, xs * 0.15 + 0.01, yf - 0.01, yf + 0.01, bz0 + 0.02, 1.76, Z_SCRWOOD)
    for zz in (1.34, 1.64):
        k.box(-0.17, 0.17, yf - 0.01, yf + 0.01, zz - 0.01, zz + 0.01, Z_SCRWOOD)
    k.box(-0.17, 0.17, yf - 0.01, yf + 0.01, 1.75, 1.77, Z_SCRWOOD)
    th = reg('MeteoScreen_Thermometers', 'panel', 'MeteoScreen', merge='MeteoScreen')
    yb = yf - 0.011
    board(th, (-0.05, yb, 1.475), 0.025, 0.25, (0, -1, 0), (0, 0, 1), uv('therm_dry'), uv('enamel'))
    board(th, (0.05, yb, 1.475), 0.025, 0.25, (0, -1, 0), (0, 0, 1), uv('therm_wet'), uv('enamel'))
    board(th, (0.0, yb, 1.685), 0.025, 0.28, (0, -1, 0), (1, 0, 0), uv('therm_max'), uv('enamel'))
    board(th, (0.0, yb, 1.718), 0.025, 0.28, (0, -1, 0), (1, 0, 0), uv('therm_min'), uv('enamel'))
    k.lathe((0.055, yb - 0.01, bz0 + 0.02), (0, 0, 1), [(0.0, 0.016), (0.045, 0.016), (0.055, 0.008), (0.07, 0.008)], Z_BOTTLE,
            seg=8, cap0=True, cap1=True)
    k.tube([(0.055, yb - 0.006, 1.345), (0.055, yb - 0.010, 1.31), (0.055, yb - 0.010, bz0 + 0.08)], 0.0025, Z_CLOTH, 4)
    gx, gy = -0.20, -0.15                                            # the thermohygrograph (drum recorder)
    k.box(gx - 0.12, gx + 0.12, gy - 0.065, gy + 0.065, bz0 + 0.02, bz0 + 0.05, Z_SCRBLACK)
    k.box(gx + 0.03, gx + 0.11, gy - 0.05, gy + 0.03, bz0 + 0.05, bz0 + 0.11, Z_SCRBLACK)
    k.box(gx + 0.035, gx + 0.105, gy - 0.054, gy - 0.05, bz0 + 0.06, bz0 + 0.10, Z_CLOTH)
    ch = reg('MeteoScreen_Chart', 'panel', 'MeteoScreen', merge='MeteoScreen')
    drum(ch, (gx - 0.055, gy, bz0 + 0.05), 0.045, 0.09, uv('chart'), uv('key_grey'), seg=12)
    for zz in (bz0 + 0.115, bz0 + 0.085):
        k.box(gx - 0.012, gx + 0.04, gy - 0.001, gy + 0.001, zz - 0.0015, zz + 0.0015, Z_SCRMETAL)
    part('MeteoScreen', 'static', (0, 0, 0), note='the Stevenson screen (root): origin on the ground under its middle; the door '
                                                  'to the front (-y) - on the station it faces north')
    socket('View_Instruments', (0.0, -bd / 2 - 0.35, 1.55), 'view', parent='MeteoScreen', dir=(0, 1, 0),
           note='where the player stands to read the instruments (eye height), the door open')
    for nm, pos, note in (('Read_Dry', (-0.05, yb, 1.475), 'the dry bulb thermometer (the air temperature)'),
                          ('Read_Wet', (0.05, yb, 1.475), 'the wet bulb thermometer (with the dry one: the humidity)'),
                          ('Read_Max', (0.0, yb, 1.685), 'the maximum thermometer (since the last reading)'),
                          ('Read_Min', (0.0, yb, 1.718), 'the minimum thermometer (since the last reading)'),
                          ('Read_Chart', (gx - 0.055, gy - 0.046, bz0 + 0.095), 'the thermohygrograph\'s weekly chart')):
        socket(nm, pos, 'read', parent='MeteoScreen', dir=(0, -1, 0), note=note)
    BOXES.extend([('Screen_Legs', 'MeteoScreen', (-lx - 0.03, lx + 0.03, -ly - 0.03, ly + 0.03, 0.0, bz0), None),
                  ('Screen_Floor', 'MeteoScreen', (-bw / 2, bw / 2, -bd / 2, bd / 2, bz0, bz0 + 0.04), None),
                  ('Screen_Back', 'MeteoScreen', (-bw / 2, bw / 2, bd / 2 - 0.03, bd / 2, bz0, bz1), None),
                  ('Screen_Left', 'MeteoScreen', (-bw / 2, -bw / 2 + 0.03, -bd / 2, bd / 2, bz0, bz1), None),
                  ('Screen_Right', 'MeteoScreen', (bw / 2 - 0.03, bw / 2, -bd / 2, bd / 2, bz0, bz1), None),
                  ('Screen_Roof', 'MeteoScreen', (-r2w / 2, r2w / 2, -r2d / 2, r2d / 2, bz1 - 0.04, r2z1), None),
                  ('Screen_Step', 'MeteoScreen', (-0.25, 0.25, -bd / 2 - 0.55, -bd / 2 - 0.25, 0.0, 0.30), None),
                  ('ScreenDoor', 'IX_ScreenDoor', (-dx, dx, yo, yi, dz0, dz1), None)])
    PLACEMENTS['MeteoScreen'] = [dict(parent='MeteoStation', package='forest_far', pos=Vector((0.0, 0.0, 0.0)), yaw=180.0,
                                      note='on the weather station\'s Mount_MeteoScreen (forest_far 1.1: the station without '
                                           'its old screen): the door to the north (+y of the station)')]


def build_devices():
    build_fax()
    build_paper()
    build_cassette()
    build_box()
    build_dropbox()
    build_pc()
    build_laptop()
    build_deck()
    build_screen()
