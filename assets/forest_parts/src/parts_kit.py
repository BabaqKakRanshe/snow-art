"""forest_parts geometry: the replacement parts and portable kit of the Forest repair tasks, in the generator shed's style.
Seven roots, each in its own frame (Blender: z up, the front -y, metres; origin on the surface it stands on, z = 0, under
its middle; Unity (x, y, z) -> (-x, z, -y), the front -> +Z):
  Item_DosingPump        C08: the dosing pump for the pump house - a steel skid with lifting handles at both ends (two
                         carry it), a 30 l tank, the motor with its gearbox and diaphragm head, the stroke knob, the motor
                         switch, the valves V1 (suction), V2 (bleed back to the tank), V3 (discharge) as hinge parts, the
                         pressure gauge's needle, the plate with the valve diagram and the priming steps, the waybill taped on
                         the tank (DosingPump_Waybill, an item: dated 1991); the discharge hose to the pump house's pipe
                         (DosingPump_Hose, shown once it is installed - PLACEMENTS)
  Item_SodiumLamp        C09: a 400 W high-pressure sodium lamp, E40, tubular, clear: the arc tube its own object (lit /
                         off), the glass its own material
  Item_SodiumLampBox     its carton (NATRIUMDAMPF-HOCHDRUCKLAMPE 400 W E40)
  Item_RadarCRT          C10: the radar's round display tube (40 cm), standing on its face: the face its own object (UV
                         0..1 - the game draws the sweep), the implosion band with four mounting lugs (two carry it), the
                         black-coated funnel, the anode cap, the neck and its base
  Item_RelayUnit         C07: the relay transceiver RT-7, a 19" 3U unit: handles, the RF LEVEL meter's needle, four LEDs,
                         the fuse holder (unscrews, the fuse inside: good / burnt), the power toggle, the rear connectors
  Item_BackupGenerator   P3: a portable petrol generator in a tube frame (two carry it, strapped in the van): the tank with
                         its cap, the recoil grip, the choke, ON / OFF, two Schuko outlets
  LakeSensor             P4: the lake sensor on its post: the box with a hinged lid (inside the logger and the 6 V battery -
                         Slot_Battery takes forest_gear's Item_Battery6V), the status LED, the whip antenna, the sign
                         MESSSTELLE / GAUGE STATION, the cable down the post and over the ground to the probe in the water
Printed faces (panel atlas) are merged into their bodies at build time (MERGE); parts / sockets in each root's frame (the
contract); in the .blend the roots stand apart (DISPLAY)."""
import math
import numpy as np
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, box6, face, quad, KBS, CONTRACT
from van2_kit import rrect
import van3_mech as VM
from gear_kit import band_uv, lathe_uv, planar, ring_tube, frame_of, ell_rings
import parts_tex as PT

uv = PT.uv
TAU = 2 * math.pi
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
ROOTS = ['Item_DosingPump', 'Item_SodiumLamp', 'Item_SodiumLampBox', 'Item_RadarCRT', 'Item_RelayUnit', 'Item_BackupGenerator',
         'LakeSensor']
DISPLAY = {'Item_DosingPump': Vector((0.0, 0.0, 0.0)), 'Item_BackupGenerator': Vector((0.3, -1.1, 0.0)),
           'Item_RelayUnit': Vector((-1.2, 0.0, 0.0)), 'Item_RadarCRT': Vector((-1.2, -1.0, 0.0)),
           'Item_SodiumLamp': Vector((1.2, -1.1, 0.0)), 'Item_SodiumLampBox': Vector((1.35, -1.1, 0.0)),
           'LakeSensor': Vector((2.6, 0.9, 0.0))}
ROOT_OF, MERGE, BOXES, MASS = {}, {}, [], {}
PLACEMENTS = {}                  # root -> [dict(parent, package, pos, yaw, note)] in the parent's frame
(Z_SKID, Z_HANDLE, Z_TANK, Z_TANKCAP, Z_GEARBOX, Z_MOTOR, Z_HEAD, Z_PVC, Z_VALVE, Z_LEVER, Z_GAUGE, Z_HOSE, Z_TAPE,
 Z_LAMPCAP, Z_INSUL, Z_SOLDER, Z_WIRE, Z_BAND, Z_FUNNEL, Z_CRTGLASS, Z_NECK, Z_TUBEBASE, Z_PIN, Z_RACK, Z_RACKBODY,
 Z_RHANDLE, Z_KNURL, Z_CONN, Z_GFRAME, Z_GOLIVE, Z_ENGINE, Z_GBLACK, Z_MUFFLER, Z_RUBBER, Z_PANEL_D, Z_CHROME) = range(600, 636)
PARTS_ZONES = list(range(600, 636))
(Z_POST, Z_BOX, Z_BOXIN, Z_LATCH, Z_ANT, Z_SCABLE, Z_PROBE, Z_SIGNBACK, Z_CLIP) = range(640, 649)
SENSOR_ZONES = list(range(640, 649))


def part(name, *a, **kw):
    assert name not in CONTRACT['parts'], f'part {name} twice'
    K.part(name, *a, **kw)


def socket(name, *a, **kw):
    assert name not in CONTRACT['sockets'], f'socket {name} twice'
    K.socket(name, *a, **kw)


def reg(name, atlas, root, merge=None):
    ROOT_OF[name] = root
    if merge:
        MERGE[name] = merge
    return kb(name, atlas)


def arc_label(k, c, r, z0, z1, a_mid, a_w, uvrect, seg=6):
    """a label on a vertical cylinder (axis z through c, radius r): centred at angle a_mid (deg, 0 = +x, counter-clockwise),
    a_w wide; reads from outside"""
    c = Vector(c)
    u0, v0, u1, v1 = uvrect
    for i in range(seg):                                    # u runs to the viewer's right (counter-clockwise from above)
        a = math.radians(a_mid - a_w / 2 + a_w * i / seg)
        b = math.radians(a_mid - a_w / 2 + a_w * (i + 1) / seg)
        pa, pb = c + Vector((r * math.cos(a), r * math.sin(a), 0)), c + Vector((r * math.cos(b), r * math.sin(b), 0))
        ua, ub = u0 + (u1 - u0) * i / seg, u0 + (u1 - u0) * (i + 1) / seg
        face(k, [pa + Z * z0, pb + Z * z0, pb + Z * z1, pa + Z * z1], 0.0, (pa + pb) / 2 - c,
             uvs=[(ua, v0), (ub, v0), (ub, v1), (ua, v1)])


def valve(k, lk, c, axis, lever_dir, zone=Z_VALVE):
    """a ball valve on a pipe along axis through c: the body, the stem and the lever (lk, the hinge part's KB) - the lever
    lies across the pipe (closed) along lever_dir"""
    c, ax, ld = Vector(c), Vector(axis).normalized(), Vector(lever_dir).normalized()
    k.cyl(c - ax * 0.026, c + ax * 0.026, 0.0165, zone, 8)
    for s in (-1, 1):
        k.cyl(c + ax * s * 0.026, c + ax * s * 0.034, 0.0125, zone, 6)                   # the nuts
    k.cyl(c, c + Z * 0.030, 0.0055, zone, 6)                                             # the stem
    top = c + Z * 0.031
    R = frame_of(ld, ld.cross(Z))                                                        # the lever along ld, its grip
    lk.box_m(top + ld * 0.036, (0.010, 0.072, 0.005), Z_LEVER, R)
    lk.box_m(top + ld * 0.068, (0.016, 0.016, 0.009), Z_LEVER, R)
    return top


# ================================================================ Item_DosingPump
PUMP = dict(lx=0.80, ly=0.46, deck=0.060, tank=(-0.20, 0.0, 0.16, 0.48))
PUMP_HOUSE_POS = Vector((-0.85, -0.30, 0.205))       # forest_far PumpHouse frame: on the floor, left of the house pump
PUMP_INJECT = Vector((0.50, 0.85, 0.60))             # the same frame: the house pipe's side, behind its valve (x 0.6, z 0.6)


def build_pump():
    k = reg('Item_DosingPump', 'Parts', 'Item_DosingPump')
    pk = reg('DosingPump_Print', 'panel', 'Item_DosingPump', merge='Item_DosingPump')
    lx, ly, dk = PUMP['lx'], PUMP['ly'], PUMP['deck']
    for s in (-1, 1):                                                                    # the skid: two channels, the deck
        k.box(-lx / 2, lx / 2, s * (ly / 2 - 0.05) - 0.025, s * (ly / 2 - 0.05) + 0.025, 0.0, dk - 0.006, Z_SKID)
    box6(k, (-lx / 2, -ly / 2, dk - 0.006), (lx / 2, ly / 2, dk), Z_SKID)
    for s in (-1, 1):                                                                    # the lifting handles at both ends
        x0 = s * (lx / 2 - 0.02)
        k.tube([Vector((x0, -0.18, dk - 0.012)), Vector((s * (lx / 2 + 0.05), -0.18, dk + 0.035)),
                Vector((s * (lx / 2 + 0.06), -0.12, dk + 0.045)), Vector((s * (lx / 2 + 0.06), 0.12, dk + 0.045)),
                Vector((s * (lx / 2 + 0.05), 0.18, dk + 0.035)), Vector((x0, 0.18, dk - 0.012))], 0.0135, Z_HANDLE, 8)
    tx, ty, tr, th = PUMP['tank']                                                        # the tank, its cap, the level lines
    k.lathe(Vector((tx, ty, dk)), Z, [(0.0, tr - 0.01), (0.008, tr), (th - 0.03, tr), (th, tr - 0.04), (th, 0.05)], Z_TANK, 16,
            cap0=True, cap1=True)
    k.lathe(Vector((tx, ty, dk + th)), Z, [(0.0, 0.045), (0.028, 0.045), (0.032, 0.040)], Z_TANKCAP, 12, cap0=False, cap1=True)
    for i in range(6):                                                                   # the tape over the waybill's top
        a0, a1 = math.radians(-90.0 - 30.0 + 10.0 * i), math.radians(-90.0 - 30.0 + 10.0 * (i + 1))
        q0 = Vector((tx + (tr + 0.0025) * math.cos(a0), ty + (tr + 0.0025) * math.sin(a0), 0))
        q1 = Vector((tx + (tr + 0.0025) * math.cos(a1), ty + (tr + 0.0025) * math.sin(a1), 0))
        k.poly([q0 + Z * (dk + 0.402), q1 + Z * (dk + 0.402), q1 + Z * (dk + 0.422), q0 + Z * (dk + 0.422)], Z_TAPE)
    wb = reg('DosingPump_Waybill', 'waybill', 'Item_DosingPump')                        # A5 bent round the tank's front
    zc0, zc1, n_ = dk + 0.20, dk + 0.41, 5
    for i in range(n_):
        a0, a1 = -90.0 - 26.5 + 53.0 * i / n_, -90.0 - 26.5 + 53.0 * (i + 1) / n_
        p0 = Vector((tx + (tr + 0.0015) * math.cos(math.radians(a0)), ty + (tr + 0.0015) * math.sin(math.radians(a0)), 0))
        p1 = Vector((tx + (tr + 0.0015) * math.cos(math.radians(a1)), ty + (tr + 0.0015) * math.sin(math.radians(a1)), 0))
        wb.poly([p0 + Z * zc0, p1 + Z * zc0, p1 + Z * zc1, p0 + Z * zc1], 0.0,
                [(i / n_, 0.0), ((i + 1) / n_, 0.0), ((i + 1) / n_, 1.0), (i / n_, 1.0)])
    part('DosingPump_Waybill', 'item', Vector((tx, ty - tr, (zc0 + zc1) / 2)), parent='Item_DosingPump',
         note='the waybill (LIEFERSCHEIN, dated 03.11.1991 - signed back-dated): taped on the tank, the player takes it off and '
              'reads it; M_Parts_Waybill, UV 0..1 (u across, v up the page)')
    # the drive: the gearbox, the motor with its fan cover and terminal box, the diaphragm head on the gearbox' front
    k.box(0.10, 0.22, -0.05, 0.09, dk, dk + 0.165, Z_GEARBOX)
    k.cyl((0.22, 0.02, dk + 0.085), (0.37, 0.02, dk + 0.085), 0.064, Z_MOTOR, 14)
    k.cyl((0.37, 0.02, dk + 0.085), (0.395, 0.02, dk + 0.085), 0.066, Z_MOTOR, 14, r2=0.058)
    for s in (-1, 1):
        k.box(0.24, 0.35, 0.02 + s * 0.04 - 0.012, 0.02 + s * 0.04 + 0.012, dk, dk + 0.03, Z_MOTOR)
    k.box(0.26, 0.34, -0.022, 0.058, dk + 0.146, dk + 0.188, Z_MOTOR)                     # the terminal box
    quad(pk, (0.315, 0.02 - 0.0645, dk + 0.085), (0, -1, 0), 0.048, 0.024, uv('pump_motor'))
    hc = Vector((0.16, -0.05, dk + 0.090))
    k.lathe(hc, -Y, [(0.0, 0.058), (0.012, 0.064), (0.034, 0.064), (0.040, 0.050)], Z_HEAD, 14, cap0=False, cap1=True)
    for i in range(6):                                                                   # the head's bolts
        a = TAU * i / 6
        p = hc - Y * 0.040 + Vector((0.050 * math.cos(a), 0, 0.050 * math.sin(a)))
        k.cyl(p, p - Y * 0.006, 0.0055, Z_VALVE, 6)
    for dz, nm in ((-0.072, 'in'), (0.072, 'out')):                                     # its valve housings
        k.cyl(hc - Y * 0.02 + Z * (dz * 0.80), hc - Y * 0.02 + Z * dz, 0.017, Z_HEAD, 8)
    # the stroke knob on the gearbox (its scale on the top), the motor's rotary switch on the terminal box
    sk = Vector((0.16, 0.02, dk + 0.165))
    planar(pk, [sk + Vector((0.028 * math.cos(TAU * i / 12), 0.028 * math.sin(TAU * i / 12), 0.0006)) for i in range(12)],
           uv('pump_stroke'), (sk.x - 0.028, sk.y - 0.028), (sk.x + 0.028, sk.y + 0.028))
    kn = reg('DosingPump_Stroke', 'Parts', 'Item_DosingPump')
    kn.lathe(sk, Z, [(0.0, 0.020), (0.024, 0.020), (0.028, 0.016)], Z_KNURL, 12, cap0=False, cap1=True)
    kn.box_m(sk + Vector((0, -0.010, 0.0285)), (0.004, 0.018, 0.002), Z_LEVER)
    part('DosingPump_Stroke', 'twist', sk, axis=(0, 0, -1), rng=(0.0, 270.0), parent='Item_DosingPump', removable=False,
         note='the stroke knob: 0..270 deg clockwise seen from above = 0..100 % (the dose)')
    sw_c = Vector((0.30, -0.022, dk + 0.167))
    sw = reg('DosingPump_Switch', 'Parts', 'Item_DosingPump')
    sw.cyl(sw_c, sw_c - Y * 0.014, 0.012, Z_GBLACK, 10)
    sw.box_m(sw_c - Y * 0.017, (0.030, 0.006, 0.008), Z_LEVER)
    part('DosingPump_Switch', 'twist', sw_c, axis=(0, 1, 0), rng=(0.0, 90.0), parent='Item_DosingPump', removable=False,
         note='the motor switch on the terminal box: 0 = OFF (the lever across), 90 deg clockwise seen from the front = ON')
    # the plate on its stand behind the drive: the valve diagram and the priming steps
    k.box(-0.02, 0.33, 0.185, 0.195, dk, dk + 0.58, Z_SKID)
    for xx in (-0.02, 0.32):
        k.box(xx, xx + 0.01, 0.13, 0.195, dk, dk + 0.012, Z_SKID)
    quad(pk, (0.155, 0.1845, dk + 0.460), (0, -1, 0), 0.28, 0.21, uv('pump_plate'))
    # the pipework: suction tank -> V1 -> head; head -> tee -> V2 (bleed back into the tank) and -> V3 -> the outlet
    r_p = 0.0085
    suc = [Vector((tx + tr - 0.004, -0.06, dk + 0.045)), Vector((0.000, -0.06, dk + 0.045)), Vector((0.075, -0.06, dk + 0.045)),
           Vector((0.110, -0.075, dk + 0.020)), Vector((0.16, -0.070, dk + 0.020)), Vector((0.16, -0.070, dk + 0.032))]
    k.tube(suc, r_p, Z_PVC, 6)
    dis = [Vector((0.16, -0.070, dk + 0.148)), Vector((0.16, -0.070, dk + 0.230)), Vector((0.16, -0.095, dk + 0.250))]
    k.tube(dis, r_p, Z_PVC, 6)
    k.tube([Vector((0.16, -0.095, dk + 0.250)), Vector((0.39, -0.095, dk + 0.250))], r_p, Z_PVC, 6)
    k.tube([Vector((0.16, -0.095, dk + 0.250)), Vector((-0.015, -0.095, dk + 0.250)), Vector((-0.040, -0.085, dk + 0.330)),
            Vector((tx + tr * 0.80, -0.075, dk + 0.390))], r_p, Z_PVC, 6)
    k.cyl((0.39, -0.095, dk + 0.250), (0.415, -0.095, dk + 0.250), 0.014, Z_VALVE, 8)       # the outlet's quick coupling
    vals = {}
    for nm, c, ax in (('V1', (0.035, -0.06, dk + 0.045), X), ('V2', (0.060, -0.095, dk + 0.250), X),
                      ('V3', (0.300, -0.095, dk + 0.250), X)):
        lk = reg('DosingPump_' + nm, 'Parts', 'Item_DosingPump')
        top = valve(k, lk, c, ax, -Y)
        vals[nm] = top
    notes = {'V1': 'V1, suction (tank -> pump): the lever across the pipe = closed; 90 deg = open (along the pipe)',
             'V2': 'V2, bleed (back into the tank): open to prime - run the motor until no air comes, then close',
             'V3': 'V3, discharge (pump -> outlet / hose): open last'}
    for nm, top in vals.items():
        part('DosingPump_' + nm, 'hinge', top, axis=(0, 0, 1), rng=(0, 90), parent='Item_DosingPump', states=['closed', 'open'],
             note=notes[nm] + ' (turns counter-clockwise seen from above)')
    # the pressure gauge on the discharge line, its needle
    k.cyl((0.215, -0.095, dk + 0.250), (0.215, -0.095, dk + 0.305), 0.005, Z_VALVE, 6)
    gc = Vector((0.215, -0.095, dk + 0.335))
    k.lathe(gc + Y * 0.012, -Y, [(0.0, 0.033), (0.024, 0.033), (0.026, 0.030)], Z_GAUGE, 14, cap0=True, cap1=False)
    pk.disc_uv(gc - Y * 0.0145, -Y, 0.029, uv('pump_gauge'), seg=14)
    nd = reg('DosingPump_Needle', 'Parts', 'Item_DosingPump')
    R = Matrix.Rotation(math.radians(PT.PUMP_GAUGE['lo']), 3, Vector((0, 1, 0)))
    nd.box_m(gc - Y * 0.0158 + R @ Vector((0, 0, 0.009)), (0.0016, 0.0008, 0.024), Z_LEVER, R)
    nd.cyl(gc - Y * 0.0152, gc - Y * 0.0168, 0.0025, Z_GBLACK, 6)
    part('DosingPump_Needle', 'hinge', gc - Y * 0.0158, axis=(0, 1, 0), rng=(0.0, PT.PUMP_GAUGE['hi'] - PT.PUMP_GAUGE['lo']),
         parent='Item_DosingPump', unit='deg',
         note='the gauge needle: 0 at 0 bar, +270 deg (clockwise seen from the front) at 10 bar; 27 deg per bar')
    # the discharge hose for the installed pump (lies over the pump house floor to the injection point on its pipe)
    hs = reg('DosingPump_Hose', 'Parts', 'Item_DosingPump')
    M = Matrix.Translation(-PUMP_HOUSE_POS)
    pts_house = [Vector((-0.435, -0.395, 0.515)), Vector((-0.400, -0.395, 0.515)), Vector((-0.34, -0.37, 0.36)),
                 Vector((-0.28, -0.30, 0.215)), Vector((-0.10, 0.20, 0.215)), Vector((0.06, 0.70, 0.215)),
                 Vector((0.26, 0.80, 0.215)), Vector((0.38, 0.84, 0.30)), Vector((0.44, 0.85, 0.52)), Vector((0.47, 0.85, 0.60))]
    pts = [M @ p for p in pts_house]
    hs.tube(pts, 0.011, Z_HOSE, 6)
    ij = M @ PUMP_INJECT
    hs.cyl(ij - X * 0.035, ij + X * 0.005, 0.016, Z_VALVE, 8)                            # the injection fitting on the pipe
    hs.box_m(ij + X * 0.012, (0.03, 0.09, 0.03), Z_VALVE)
    part('DosingPump_Hose', 'static', M @ Vector(pts_house[0]), parent='Item_DosingPump',
         note='the discharge hose from the outlet to the injection fitting on the pump house pipe - it fits the placement in '
              'forest_far PumpHouse only: hide it until the pump is installed (C08), show it then')
    part('Item_DosingPump', 'item', (0, 0, 0), note='the dosing pump (root): a skid 0.80 x 0.46 m, origin on the floor under '
                                                    'its middle; the valves and the gauge to the front (-y); two carry it')
    for s, nm in ((-1, 'A'), (1, 'B')):
        socket('Hand_Pump_' + nm, (s * (lx / 2 + 0.06), 0.0, dk + 0.045), 'hand', parent='Item_DosingPump',
               note='a lifting handle (one player each end)')
    socket('Port_Discharge', (0.415, -0.095, dk + 0.250), 'port', parent='Item_DosingPump', dir=(1, 0, 0),
           note='the outlet\'s quick coupling (the hose starts here)')
    socket('Fill_Tank', (tx, ty, dk + th + 0.032), 'fill', parent='Item_DosingPump', dir=(0, 0, -1),
           note='the tank\'s filler under the cap')
    socket('Cable_Power', (0.34, 0.058, dk + 0.167), 'cable', parent='Item_DosingPump', dir=(0, 1, 0),
           note='the motor\'s cable out of the terminal box (to the pump house switch box)')
    socket('Audio_Pump', (0.30, 0.02, dk + 0.085), 'audio', parent='Item_DosingPump', note='the motor and the diaphragm\'s tick')
    MASS['Item_DosingPump'] = 45.0
    BOXES.extend([('Pump_Skid', 'Item_DosingPump', (-lx / 2 - 0.07, lx / 2 + 0.07, -ly / 2, ly / 2, 0.0, dk + 0.06), None),
                  ('Pump_Tank', 'Item_DosingPump', (tx - tr, tx + tr, ty - tr, ty + tr, dk, dk + th + 0.03), None),
                  ('Pump_Drive', 'Item_DosingPump', (0.10, 0.40, -0.11, 0.09, dk, dk + 0.19), None),
                  ('Pump_Pipes', 'Item_DosingPump', (-0.04, 0.42, -0.135, -0.04, dk + 0.20, dk + 0.37), None),
                  ('Pump_Plate', 'Item_DosingPump', (-0.02, 0.33, 0.18, 0.20, dk, dk + 0.58), None)])
    PLACEMENTS['Item_DosingPump'] = [dict(parent='PumpHouse', package='forest_far', pos=PUMP_HOUSE_POS, yaw=0.0,
                                          note='installed (C08): on the pump house floor left of the house pump, the valves '
                                               'to the door; DosingPump_Hose then runs to the fitting on the house pipe')]


# ================================================================ Item_SodiumLamp, Item_SodiumLampBox
def build_sodium():
    k = reg('Item_SodiumLamp', 'Parts', 'Item_SodiumLamp')
    k.lathe(Vector((0, 0, 0)), Z, [(0.0, 0.0), (0.0008, 0.0060), (0.0040, 0.0080)], Z_SOLDER, 10, cap0=False, cap1=False)
    k.lathe(Vector((0, 0, 0)), Z, [(0.0040, 0.0080), (0.0042, 0.0160), (0.0095, 0.0170), (0.0100, 0.0186)], Z_INSUL, 14,
            cap0=False, cap1=False)
    th = [(0.0100, 0.0186)]
    z = 0.0100
    while z < 0.0440:
        th += [(z + 0.0020, 0.0199), (z + 0.0052, 0.0186)]
        z += 0.00635
    th += [(0.0470, 0.0200), (0.0485, 0.0210), (0.0500, 0.0210)]
    k.lathe(Vector((0, 0, 0)), Z, th, Z_LAMPCAP, 12, cap0=False, cap1=False)
    g = reg('SodiumLamp_Glass', 'glass', 'Item_SodiumLamp', merge='Item_SodiumLamp')      # the clear outer tube
    g.lathe(Vector((0, 0, 0)), Z, [(0.0500, 0.0205), (0.0560, 0.0225), (0.0640, 0.0240), (0.2660, 0.0240), (0.2780, 0.0215),
                                   (0.2860, 0.0140), (0.2900, 0.0)], 0.0, 12, cap0=False, cap1=False)
    for zz in (0.068, 0.074):                                                            # getter rings
        k.lathe(Vector((0, 0, zz)), Z, [(0.0, 0.010), (0.002, 0.010)], Z_WIRE, 8, cap0=False, cap1=False)
    k.tube([Vector((0.0, 0.0, 0.052)), Vector((0.0, 0.0, 0.110))], 0.0015, Z_WIRE, 4)     # the stem, the frame rod
    k.tube([Vector((0.0, 0.0, 0.088)), Vector((0.013, 0.0, 0.098)), Vector((0.014, 0.0, 0.250)), Vector((0.004, 0.0, 0.262)),
            Vector((0.0, 0.0, 0.248))], 0.0012, Z_WIRE, 4)
    for zz in (0.112, 0.240):
        k.cyl((0.0, 0.0, zz - 0.004), (0.0, 0.0, zz + 0.004), 0.0062, Z_WIRE, 8)        # the arc tube's end caps
    a = reg('SodiumLamp_ArcTube', 'arc', 'Item_SodiumLamp')
    a.lathe(Vector((0, 0, 0.116)), Z, [(0.0, 0.0048), (0.120, 0.0048)], 0.0, 10, cap0=True, cap1=True)
    part('SodiumLamp_ArcTube', 'static', (0.0, 0.0, 0.176), parent='Item_SodiumLamp',
         note='the ceramic arc tube: M_Parts_ArcTube_Off (in the file) / M_Parts_ArcTube (lit: orange, it warms up from a '
              'dim red in about a minute) - the searchlight\'s light comes from here')
    part('Item_SodiumLamp', 'item', (0, 0, 0), note='a 400 W high-pressure sodium lamp, E40, tubular clear (root): standing '
                                                    'on its cap, origin under the contact; the glass M_Parts_LampGlass')
    socket('Screw_E40', (0.0, 0.0, 0.025), 'screw', parent='Item_SodiumLamp', dir=(0, 0, -1),
           note='screws into the searchlight\'s E40 holder cap first (-z), clockwise seen from the glass')
    MASS['Item_SodiumLamp'] = 0.18
    BOXES.append(('SodiumLamp', 'Item_SodiumLamp', (-0.024, 0.024, -0.024, 0.024, 0.0, 0.290), None))
    bx = reg('Item_SodiumLampBox', 'panel', 'Item_SodiumLampBox')
    w, h = 0.072, 0.300
    for n, up, key in (((0, -1, 0), (0, 0, 1), 'lampbox_front'), ((0, 1, 0), (0, 0, 1), 'lampbox_front'),
                       ((1, 0, 0), (0, 0, 1), 'lampbox_side'), ((-1, 0, 0), (0, 0, 1), 'lampbox_side'),
                       ((0, 0, 1), (0, 1, 0), 'lampbox_top'), ((0, 0, -1), (0, 1, 0), 'lampbox_top')):
        n = Vector(n)
        c = Vector((0, 0, h / 2)) + Vector((n.x * w / 2, n.y * w / 2, n.z * h / 2))
        quad(bx, c, n, w, h if abs(n.z) < 0.5 else w, uv(key), up=up)
    part('Item_SodiumLampBox', 'item', (0, 0, 0), note='the sodium lamp\'s carton (root): standing, origin under its middle; '
                                                       'it does not open (the game hands out Item_SodiumLamp)')
    MASS['Item_SodiumLampBox'] = 0.30
    BOXES.append(('SodiumLampBox', 'Item_SodiumLampBox', (-w / 2, w / 2, -w / 2, w / 2, 0.0, h), None))


# ================================================================ Item_RadarCRT (standing on its face)
CRT = dict(r=0.205, band=0.212, h_band=0.062, neck=0.026, z_neck=0.385, z_base=0.535, top=0.565)


def build_crt():
    k = reg('Item_RadarCRT', 'Parts', 'Item_RadarCRT')
    pk = reg('RadarCRT_Label', 'panel', 'Item_RadarCRT', merge='Item_RadarCRT')
    r, rb = CRT['r'], CRT['band']
    fc = reg('RadarCRT_Face', 'crtface', 'Item_RadarCRT')
    fc.disc_uv(Vector((0, 0, 0.008)), Vector((0, 0, -1)), r, (0.0, 0.0, 1.0, 1.0), seg=24, dome=0.008)
    part('RadarCRT_Face', 'static', (0.0, 0.0, 0.004), parent='Item_RadarCRT',
         note='the face (down while it stands on it): M_Parts_CRTFace dark (in the file); UV 0..1 - the game draws the sweep '
              '(u right, v up seen from in front of the face, the lugs A / B left / right)')
    k.lathe(Vector((0, 0, 0)), Z, [(0.008, r), (0.012, rb), (CRT['h_band'] - 0.004, rb), (CRT['h_band'], r - 0.004)], Z_BAND, 24,
            cap0=False, cap1=False)
    for i, ang in enumerate((45.0, 135.0, 225.0, 315.0)):                                 # the mounting lugs
        a = math.radians(ang)
        d = Vector((math.cos(a), math.sin(a), 0))
        k.box_m(d * (rb + 0.016) + Z * 0.036, (0.036, 0.034, 0.004), Z_BAND, frame_of(Vector((0, 0, 1)).cross(d), d))
        k.box_m(d * (rb + 0.003) + Z * 0.036, (0.008, 0.034, 0.040), Z_BAND, frame_of(Vector((0, 0, 1)).cross(d), d))
    # the glass: the shoulder (grey-green), the black-coated funnel, the neck, the base with its pins
    k.lathe(Vector((0, 0, 0)), Z, [(CRT['h_band'], r - 0.004), (0.090, 0.192), (0.115, 0.170)], Z_CRTGLASS, 24, cap0=False,
            cap1=False)
    k.lathe(Vector((0, 0, 0)), Z, [(0.115, 0.170), (0.200, 0.120), (0.300, 0.068), (0.360, 0.036), (CRT['z_neck'], CRT['neck'])],
            Z_FUNNEL, 20, cap0=False, cap1=False)
    k.lathe(Vector((0, 0, 0)), Z, [(CRT['z_neck'], CRT['neck']), (CRT['z_base'], CRT['neck'])], Z_NECK, 12, cap0=False, cap1=False)
    k.lathe(Vector((0, 0, 0)), Z, [(CRT['z_base'], 0.029), (CRT['top'] - 0.004, 0.029), (CRT['top'], 0.024)], Z_TUBEBASE, 12,
            cap0=True, cap1=True)
    for i in range(12):
        a = TAU * i / 13
        p = Vector((0.016 * math.cos(a), 0.016 * math.sin(a), CRT['top']))
        k.cyl(p, p + Z * 0.008, 0.0012, Z_PIN, 4)
    k.box(-0.003, 0.003, 0.0, 0.010, CRT['top'], CRT['top'] + 0.010, Z_TUBEBASE)            # the key
    ac = Vector((0.0, 0.135, 0.205))                                                       # the anode cap on the funnel
    k.cyl(ac, ac + Vector((0, 0.010, 0.006)), 0.014, Z_TUBEBASE, 10)
    k.cyl(ac + Vector((0, 0.010, 0.006)), ac + Vector((0, 0.012, 0.007)), 0.006, Z_PIN, 8)
    arc_label(pk, (0, 0, 0), rb + 0.0006, 0.017, 0.045, -90.0, 19.5, uv('crt_label'), seg=5)
    part('Item_RadarCRT', 'item', (0, 0, 0), note='the radar display tube (root): standing on its face, origin at the face\'s '
                                                  'middle (the lowest point); the neck up; two carry it by the lugs')
    socket('Mount_Face', (0, 0, 0), 'mount', parent='Item_RadarCRT', dir=(0, 0, -1),
           note='installed: this point on the console\'s screen opening, dir towards the operator; lug A to the operator\'s '
                'left')
    for nm, ang in (('A', 135.0), ('B', 315.0)):
        a = math.radians(ang)
        socket('Hand_CRT_' + nm, Vector((math.cos(a), math.sin(a), 0)) * (rb + 0.026) + Z * 0.036, 'hand',
               parent='Item_RadarCRT', note='a mounting lug: one player each side')
    socket('Socket_Neck', (0.0, 0.0, CRT['top'] + 0.008), 'plug', parent='Item_RadarCRT', dir=(0, 0, 1),
           note='the base\'s pins: the console\'s tube socket goes on here')
    socket('Anode_Cap', ac + Vector((0, 0.012, 0.007)), 'plug', parent='Item_RadarCRT', note='the high-voltage lead clips on')
    MASS['Item_RadarCRT'] = 14.0
    BOXES.extend([('CRT_Face', 'Item_RadarCRT', (-rb, rb, -rb, rb, 0.0, CRT['h_band']), None),
                  ('CRT_Funnel', 'Item_RadarCRT', (-0.18, 0.18, -0.18, 0.18, CRT['h_band'], 0.20), None),
                  ('CRT_Cone', 'Item_RadarCRT', (-0.10, 0.10, -0.10, 0.10, 0.20, CRT['z_neck']), None),
                  ('CRT_Neck', 'Item_RadarCRT', (-0.03, 0.03, -0.03, 0.03, CRT['z_neck'], CRT['top'] + 0.008), None)])


# ================================================================ Item_RelayUnit (19" 3U)
RU = dict(pw=0.483, ph=0.1334, bw=0.431, y_f=-0.160, t=0.003, y_b=0.160)


def relay_point(px, py, lift=0.0):
    """a pixel of relay_front (240 x 66) -> a point on the front (the panel's face y = y_f; lift: further out)"""
    W, H = PT.RELAY_PX
    return Vector(((px / W - 0.5) * RU['pw'], RU['y_f'] - lift, (1 - py / H) * RU['ph']))


def build_relay():
    k = reg('Item_RelayUnit', 'Parts', 'Item_RelayUnit')
    pk = reg('RelayUnit_Print', 'panel', 'Item_RelayUnit', merge='Item_RelayUnit')
    pw, ph, bw, yf, t, yb = RU['pw'], RU['ph'], RU['bw'], RU['y_f'], RU['t'], RU['y_b']
    box6(k, (-pw / 2, yf, 0.0), (pw / 2, yf + t, ph), Z_RACK, skip=('-y',))
    quad(pk, (0.0, yf - 0.0003, ph / 2), (0, -1, 0), pw, ph, uv('relay_front'))
    box6(k, (-bw / 2, yf + t, 0.002), (bw / 2, yb, ph - 0.002), {'*': Z_RACKBODY, '+y': Z_RACKBODY}, skip=('-y',))
    quad(pk, (0.0, yb + 0.0003, ph / 2), (0, 1, 0), bw, 0.12, uv('relay_rear'))
    for xs in (-1, 1):                                                                    # the handles
        x = (PT.RELAY['handles'][0 if xs < 0 else 1] / PT.RELAY_PX[0] - 0.5) * pw
        k.tube([Vector((x, yf, 0.024)), Vector((x, yf - 0.030, 0.034)), Vector((x, yf - 0.032, 0.100)),
                Vector((x, yf, 0.110))], 0.0048, Z_RHANDLE, 6)
    for px in (96, 128):                                                                  # the rear N connectors
        x = (px / 216 - 0.5) * bw
        k.cyl((x, yb, 0.072), (x, yb + 0.018, 0.072), 0.0095, Z_CONN, 8)
        k.cyl((x, yb + 0.018, 0.072), (x, yb + 0.020, 0.072), 0.0065, Z_CONN, 8)
    jc = relay_point(*PT.RELAY['jack'])
    k.cyl(jc, jc - Y * 0.010, 0.0055, Z_CONN, 8)                                         # the BNC test jack
    # the RF LEVEL meter's needle (at rest on the left: no signal)
    mx0, my0, mx1, my1 = PT.RELAY['meter']
    piv = relay_point((mx0 + mx1) / 2, my1 - 4, 0.0012)
    nd = reg('RelayUnit_Needle', 'Parts', 'Item_RelayUnit')
    R = Matrix.Rotation(math.radians(-50.0), 3, Vector((0, 1, 0)))                     # at rest: 50 deg left of up
    nd.box_m(piv + R @ Vector((0, 0, 0.020)), (0.0012, 0.0006, 0.040), Z_GBLACK, R)
    part('RelayUnit_Needle', 'hinge', piv, axis=(0, 1, 0), rng=(0.0, 100.0), parent='Item_RelayUnit',
         note='the RF LEVEL needle: 0 = left (no signal), +100 deg clockwise seen from the front = full scale; the red '
              'zone from 80')
    for (lx_, ly_), nm, kind in zip(PT.RELAY['leds'], ('PWR', 'TX', 'RX', 'ALM'), ('g', 'a', 'g', 'r')):
        l = reg('RelayUnit_LED_' + nm, 'led', 'Item_RelayUnit')
        c = relay_point(lx_, ly_, 0.0008)
        quad(l, c, (0, -1, 0), 0.006, 0.006, (0.0, 0.0, 1.0, 1.0))
        mat = {'g': 'M_Parts_LEDG', 'a': 'M_Parts_LEDA', 'r': 'M_Parts_LEDR'}[kind]
        part('RelayUnit_LED_' + nm, 'static', c, parent='Item_RelayUnit', lamp_kind=kind,
             note=f'{nm} LED: {mat} (lit) / M_Parts_LED_Off (in the file)')
    # the fuse holder: the cap unscrews and comes off with the fuse in it
    fc_ = relay_point(*PT.RELAY['fuse'])
    k.cyl(fc_, fc_ - Y * 0.004, 0.0105, Z_GBLACK, 12)
    cp = reg('RelayUnit_FuseCap', 'Parts', 'Item_RelayUnit')
    cp.lathe(fc_ - Y * 0.004, -Y, [(0.0, 0.0075), (0.012, 0.0075), (0.014, 0.0060)], Z_KNURL, 10, cap0=False, cap1=True)
    fu = reg('RelayUnit_Fuse', 'fuse', 'Item_RelayUnit')
    fu.cyl(fc_ + Y * 0.000, fc_ + Y * 0.016, 0.0026, 0.0, 6)
    part('RelayUnit_FuseCap', 'twist', fc_ - Y * 0.004, axis=(0, -1, 0), rng=(0.0, 300.0), parent='Item_RelayUnit',
         removable='end', note='the fuse holder\'s cap: unscrews counter-clockwise (seen from the front) and comes off with the '
                               'fuse')
    part('RelayUnit_Fuse', 'static', fc_ + Y * 0.008, parent='RelayUnit_FuseCap',
         note='the glass fuse 5 x 20 mm, 2 A slow (in the cap): M_Parts_FuseOK (in the file) / M_Parts_FuseBurnt (C07: a '
              'burnt fuse is one of the causes)')
    sc_ = relay_point(*PT.RELAY['switch'])
    sw = reg('RelayUnit_Power', 'Parts', 'Item_RelayUnit')
    Rd = Matrix.Rotation(math.radians(20.0), 3, Vector((1, 0, 0)))                       # tipped down (O)
    sw.cyl(sc_, sc_ + Rd @ Vector((0, -0.016, 0)), 0.0025, Z_CHROME, 6)
    sw.cyl(sc_ + Rd @ Vector((0, -0.016, 0)), sc_ + Rd @ Vector((0, -0.020, 0)), 0.0034, Z_CHROME, 6)
    part('RelayUnit_Power', 'hinge', sc_, axis=(-1, 0, 0), rng=(0, 40), parent='Item_RelayUnit', states=['off', 'on'],
         note='the power toggle: down = O (in the model), 40 deg up = I')
    part('Item_RelayUnit', 'item', (0, 0, 0), note='the relay transceiver RT-7 (root): a 19" 3U unit, origin under its middle on '
                                                   'the shelf; the front panel to -y (its face at y -0.16)')
    socket('Mount_Rack', (0.0, yf + t, ph / 2), 'mount', parent='Item_RelayUnit', dir=(0, 1, 0),
           note='the panel\'s back face middle: on the rack rails (the ears\' holes 465 mm apart)')
    for nm, x in (('L', -1), ('R', 1)):
        xx = (PT.RELAY['handles'][0 if x < 0 else 1] / PT.RELAY_PX[0] - 0.5) * pw
        socket('Hand_Relay_' + nm, (xx, yf - 0.032, 0.067), 'hand', parent='Item_RelayUnit', note='a front handle')
    for nm, px in (('Plug_AntA', 96), ('Plug_AntB', 128)):
        socket(nm, ((px / 216 - 0.5) * bw, yb + 0.020, 0.072), 'plug', parent='Item_RelayUnit', dir=(0, 1, 0),
               note='an N connector at the back: the antenna feeder')
    socket('Plug_Mains', ((171 / 216 - 0.5) * bw, yb + 0.002, (1 - 28 / 60) * 0.12 + 0.007), 'plug', parent='Item_RelayUnit',
           dir=(0, 1, 0), note='the mains inlet at the back')
    MASS['Item_RelayUnit'] = 9.0
    BOXES.extend([('Relay_Body', 'Item_RelayUnit', (-bw / 2, bw / 2, yf, yb + 0.02, 0.0, ph), None),
                  ('Relay_Panel', 'Item_RelayUnit', (-pw / 2, pw / 2, yf - 0.034, yf + t, 0.0, ph), None)])


# ================================================================ Item_BackupGenerator
GEN = dict(lx=0.62, ly=0.46, h=0.47, r=0.014)


def gen_panel_point(px, py, lift=0.0):
    """a pixel of gen_panel (96 x 64) -> a point on the control panel (x 0.04..0.28, z 0.26..0.10, the face y -0.19)"""
    return Vector((0.04 + px / 96.0 * 0.24, -0.1905 - lift, 0.26 - py / 64.0 * 0.16))


def build_generator():
    k = reg('Item_BackupGenerator', 'Parts', 'Item_BackupGenerator')
    pk = reg('Generator_Print', 'panel', 'Item_BackupGenerator', merge='Item_BackupGenerator')
    lx, ly, h, r = GEN['lx'], GEN['ly'], GEN['h'], GEN['r']
    zb, zt = 0.030, h - r
    for s in (-1, 1):                                                                    # the side loops of the frame
        y = s * ly / 2
        loop = [Vector((-lx / 2 + 0.06, y, zb)), Vector((lx / 2 - 0.06, y, zb)), Vector((lx / 2 - 0.01, y, zb + 0.03)),
                Vector((lx / 2, y, zb + 0.08)), Vector((lx / 2, y, zt - 0.07)), Vector((lx / 2 - 0.02, y, zt - 0.015)),
                Vector((lx / 2 - 0.07, y, zt)), Vector((-lx / 2 + 0.07, y, zt)), Vector((-lx / 2 + 0.02, y, zt - 0.015)),
                Vector((-lx / 2, y, zt - 0.07)), Vector((-lx / 2, y, zb + 0.08)), Vector((-lx / 2 + 0.01, y, zb + 0.03)),
                Vector((-lx / 2 + 0.06, y, zb))]
        k.tube(loop, r, Z_GFRAME, 8, caps=False)
    for xx in (-lx / 2, lx / 2):                                                         # the cross bars (the top ones: handles)
        k.cyl((xx, -ly / 2, zb + 0.10), (xx, ly / 2, zb + 0.10), r, Z_GFRAME, 8, caps=False)
        k.cyl((xx * 0.84, -ly / 2, zt), (xx * 0.84, ly / 2, zt), r, Z_GFRAME, 8, caps=False)
        k.cyl((xx * 0.84, -0.10, zt), (xx * 0.84, 0.10, zt), r + 0.005, Z_RUBBER, 8)     # the rubber grips
    for xs in (-1, 1):
        k.cyl((xs * (lx / 2 - 0.08), -ly / 2, zb), (xs * (lx / 2 - 0.08), ly / 2, zb), r * 0.8, Z_GFRAME, 6, caps=False)
        for ys in (-1, 1):
            k.cyl((xs * (lx / 2 - 0.10), ys * ly / 2, 0.0), (xs * (lx / 2 - 0.10), ys * ly / 2, zb - r * 0.6), 0.022, Z_RUBBER, 8)
    # the engine block, the cylinder with fins, the air filter, the recoil starter's housing, the alternator
    k.box(-0.15, 0.05, -0.13, 0.11, 0.065, 0.235, Z_ENGINE)
    k.box(-0.10, 0.12, -0.09, 0.09, 0.04, 0.065, Z_GFRAME)                                 # the engine mounts
    R = Matrix.Rotation(math.radians(-18.0), 3, Vector((0, 1, 0)))
    cyl_c = Vector((-0.02, 0.0, 0.285))
    k.box_m(cyl_c, (0.10, 0.12, 0.11), Z_ENGINE, R)
    for i in range(5):
        k.box_m(cyl_c + R @ Vector((0, 0, -0.04 + 0.02 * i)), (0.13, 0.14, 0.006), Z_ENGINE, R)
    k.box(-0.13, -0.05, -0.17, -0.13, 0.205, 0.300, Z_GBLACK)                               # the air filter cover
    rs_c = Vector((-0.15, -0.01, 0.165))
    k.lathe(rs_c, -X, [(0.0, 0.095), (0.020, 0.095), (0.030, 0.085), (0.034, 0.040)], Z_GBLACK, 16, cap0=False, cap1=True)
    k.cyl((0.05, -0.02, 0.150), (0.245, -0.02, 0.150), 0.090, Z_GOLIVE, 16)
    k.cyl((0.245, -0.02, 0.150), (0.265, -0.02, 0.150), 0.090, Z_GOLIVE, 16, r2=0.070)
    # the muffler and its shield at the back, the exhaust pipe
    k.cyl((-0.08, 0.15, 0.290), (0.14, 0.15, 0.290), 0.048, Z_MUFFLER, 12)
    k.box(-0.09, 0.15, 0.170, 0.205, 0.235, 0.345, Z_MUFFLER)
    k.tube([Vector((0.14, 0.15, 0.290)), Vector((0.19, 0.15, 0.290)), Vector((0.21, 0.19, 0.275))], 0.012, Z_MUFFLER, 6)
    # the tank on top, its sticker, the cap (twist); the control panel at the front with the outlets
    rings = [rrect(Vector((0.0, 0.0, z_)), X, Y, w_, d_, rr, 3) for z_, w_, d_, rr in
             ((0.335, 0.40, 0.30, 0.05), (0.350, 0.44, 0.34, 0.06), (0.425, 0.44, 0.34, 0.06), (0.445, 0.40, 0.30, 0.05))]
    k.loft(rings, [Z_GOLIVE] * 3, cap0=Z_GOLIVE, cap1=Z_GOLIVE)
    quad(pk, (-0.04, -0.1705, 0.3875), (0, -1, 0), 0.14, 0.07, uv('gen_tank'))
    fn = Vector((0.11, 0.05, 0.445))
    k.cyl(fn, fn + Z * 0.012, 0.030, Z_GBLACK, 12)
    cp = reg('Gen_FuelCap', 'Parts', 'Item_BackupGenerator')
    cp.lathe(fn + Z * 0.012, Z, [(0.0, 0.036), (0.020, 0.036), (0.026, 0.028)], Z_GBLACK, 12, cap0=True, cap1=True)
    cp.box_m(fn + Z * 0.040, (0.050, 0.008, 0.008), Z_GBLACK)
    part('Gen_FuelCap', 'twist', fn + Z * 0.012, axis=(0, 0, 1), rng=(0.0, 540.0), parent='Item_BackupGenerator',
         removable='end', note='the tank cap: one and a half turns counter-clockwise (seen from above), then it comes off')
    k.box(0.035, 0.285, -0.190, -0.170, 0.095, 0.265, Z_PANEL_D)
    quad(pk, (0.16, -0.1905, 0.18), (0, -1, 0), 0.24, 0.16, uv('gen_panel'))
    for (ox, oy) in PT.GEN['outlets']:
        c = gen_panel_point(ox, oy)
        k.cyl(c + Y * 0.001, c - Y * 0.008, 0.029, Z_GBLACK, 12, caps=False)
        k.lathe(c - Y * 0.008, -Y, [(0.0, 0.029), (0.0, 0.024)], Z_GBLACK, 12, cap0=False, cap1=False)
    rc = gen_panel_point(*PT.GEN['reset'])
    k.cyl(rc, rc - Y * 0.008, 0.0045, Z_RUBBER, 6)
    swc = gen_panel_point(*PT.GEN['switch'])
    sw = reg('Gen_Switch', 'Parts', 'Item_BackupGenerator')
    sw.box_m(swc - Y * 0.007 + Z * 0.002, (0.012, 0.012, 0.016), Z_LEVER, Matrix.Rotation(math.radians(-15), 3, 'X'))
    part('Gen_Switch', 'hinge', swc, axis=(-1, 0, 0), rng=(0, 30), parent='Item_BackupGenerator', states=['off', 'on'],
         note='ON / OFF: the rocker tips 30 deg (top in = ON); the engine stops when it goes off')
    ch_c = Vector((-0.06, -0.150, 0.170))
    chk = reg('Gen_Choke', 'Parts', 'Item_BackupGenerator')
    chk.box_m(ch_c, (0.012, 0.030, 0.010), Z_LEVER)
    chk.box_m(ch_c - Y * 0.018, (0.020, 0.008, 0.018), Z_LEVER)
    part('Gen_Choke', 'slide', ch_c, axis=(1, 0, 0), rng=(0.0, 0.025), unit='m', parent='Item_BackupGenerator',
         note='the choke lever on the carburettor: 25 mm to +x = choke closed (a cold start), back once it runs')
    gp = Vector((-0.170, -0.088, 0.205))
    gr = reg('Gen_StartGrip', 'Parts', 'Item_BackupGenerator')
    gr.cyl(gp - Z * 0.035, gp + Z * 0.035, 0.010, Z_GBLACK, 8)
    gr.cyl(gp, gp + Y * 0.014, 0.0025, Z_GBLACK, 4)
    part('Gen_StartGrip', 'slide', gp, axis=(0, -1, 0), rng=(0.0, 0.60), unit='m', parent='Item_BackupGenerator',
         note='the recoil starter\'s grip: pulled out up to 0.6 m to the front and back (the game draws the cord from the '
              'housing to the grip); a few pulls start a warm engine, the choke for a cold one')
    part('Item_BackupGenerator', 'item', (0, 0, 0), note='a portable petrol generator 2.8 kVA (root): a tube frame 0.62 x 0.46 m, '
                                                         'origin on the ground under its middle; the panel and the starter to '
                                                         'the front (-y); two carry it by the end bars')
    for s, nm in ((-1, 'A'), (1, 'B')):
        socket('Hand_Gen_' + nm, (s * lx / 2 * 0.84, 0.0, zt), 'hand', parent='Item_BackupGenerator',
               note='a carrying bar with its grip (one player each end)')
    socket('Fill_Fuel', fn + Z * 0.012, 'fill', parent='Item_BackupGenerator', dir=(0, 0, -1),
           note='the tank\'s filler under the cap (the canister\'s spout)')
    socket('Exhaust', (0.215, 0.20, 0.272), 'fx', parent='Item_BackupGenerator', dir=(0.3, 1, -0.3),
           note='the exhaust\'s end: smoke while it runs')
    for i, (ox, oy) in enumerate(PT.GEN['outlets']):
        socket(f'Outlet_{i + 1}', gen_panel_point(ox, oy, 0.008), 'plug', parent='Item_BackupGenerator', dir=(0, -1, 0),
               note=f'Schuko outlet {i + 1}: a plug goes in along +y (the cable to the relay station)')
    for i, (xs, ys) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        socket(f'Tie_{i + 1}', (xs * (lx / 2 - 0.02), ys * ly / 2, zb + 0.10), 'tie', parent='Item_BackupGenerator',
               note='a strap point on the frame (lashed in the van)')
    socket('Audio_Engine', (0.0, 0.0, 0.22), 'audio', parent='Item_BackupGenerator', note='the engine')
    MASS['Item_BackupGenerator'] = 46.0
    BOXES.append(('Generator', 'Item_BackupGenerator', (-lx / 2 - r, lx / 2 + r, -ly / 2 - r, ly / 2 + r, 0.0, h + 0.02), None))


# ================================================================ LakeSensor (on its post at the lake shore)
LS = dict(post=0.030, top=1.45, bx=0.12, by0=-0.145, by1=-0.035, bz0=0.95, bz1=1.25, wall=0.008)


def build_sensor():
    k = reg('LakeSensor', 'Sensor', 'LakeSensor')
    pk = reg('LakeSensor_Print', 'panel', 'LakeSensor', merge='LakeSensor')
    pr, top = LS['post'], LS['top']
    k.cyl((0, 0, -0.40), (0, 0, top), pr, Z_POST, 10, caps=False)
    k.lathe(Vector((0, 0, top)), Z, [(0.0, pr + 0.003), (0.012, pr + 0.003), (0.016, 0.0)], Z_POST, 10, cap0=True, cap1=False)
    bx, by0, by1, bz0, bz1, w = LS['bx'], LS['by0'], LS['by1'], LS['bz0'], LS['bz1'], LS['wall']
    for zz in (bz0 + 0.04, bz1 - 0.04):                                                  # the bracket's two clamps
        k.box(-0.05, 0.05, by1, -pr + 0.004, zz - 0.02, zz + 0.02, Z_CLIP)
        ring_tube(k, (0, 0, zz), (0, 0, 1), pr + 0.004, 0.004, Z_CLIP, seg=12)
    # the box: its walls (open front), the inside, the logger board on the back wall, the battery's clips
    box6(k, (-bx, by0 + 0.012, bz0), (bx, by1, bz1), Z_BOX, skip=('-y',))
    for (a, b) in ((-bx, -bx + w), (bx - w, bx)):                                        # the walls' front edges and inner faces
        face(k, [(a, by0 + 0.012, bz0), (b, by0 + 0.012, bz0), (b, by0 + 0.012, bz1), (a, by0 + 0.012, bz1)], Z_BOX, (0, -1, 0))
    for (a, b) in ((bz0, bz0 + w), (bz1 - w, bz1)):
        face(k, [(-bx + w, by0 + 0.012, a), (bx - w, by0 + 0.012, a), (bx - w, by0 + 0.012, b), (-bx + w, by0 + 0.012, b)], Z_BOX,
             (0, -1, 0))
    yi0, yi1 = by0 + 0.012, by1 - w
    face(k, [(-bx + w, yi1, bz0 + w), (bx - w, yi1, bz0 + w), (bx - w, yi1, bz1 - w), (-bx + w, yi1, bz1 - w)], Z_BOXIN, (0, -1, 0))
    face(k, [(-bx + w, yi0, bz0 + w), (bx - w, yi0, bz0 + w), (bx - w, yi1, bz0 + w), (-bx + w, yi1, bz0 + w)], Z_BOXIN, (0, 0, 1))
    face(k, [(-bx + w, yi0, bz1 - w), (bx - w, yi0, bz1 - w), (bx - w, yi1, bz1 - w), (-bx + w, yi1, bz1 - w)], Z_BOXIN, (0, 0, -1))
    face(k, [(-bx + w, yi0, bz0 + w), (-bx + w, yi1, bz0 + w), (-bx + w, yi1, bz1 - w), (-bx + w, yi0, bz1 - w)], Z_BOXIN, (1, 0, 0))
    face(k, [(bx - w, yi0, bz0 + w), (bx - w, yi1, bz0 + w), (bx - w, yi1, bz1 - w), (bx - w, yi0, bz1 - w)], Z_BOXIN, (-1, 0, 0))
    quad(pk, (-0.035, yi1 - 0.0004, bz1 - 0.085), (0, -1, 0), 0.13, 0.09, uv('sensor_pcb'))
    slot = Vector((0.060, (yi0 + yi1) / 2, bz0 + w))
    for xs in (-1, 1):                                                                    # the battery leads with their clips
        tip = slot + Vector((xs * 0.0164, 0.0, 0.1165 + 0.004))
        k.tube([Vector((-0.035 + xs * 0.01, yi1 - 0.002, bz1 - 0.14)), Vector((0.02 + xs * 0.01, yi1 - 0.012, bz1 - 0.07)),
                tip + Vector((0, 0.012, 0.030)), tip + Vector((0, 0.004, 0.006))], 0.0022, Z_SCABLE, 4)
        k.box_m(tip + Vector((0, 0.002, 0.004)), (0.008, 0.006, 0.010), Z_LATCH)
    # the lid (hinged on the left, opens out to the front), its label, the status LED, the latches
    lid = reg('LakeSensor_Lid', 'Sensor', 'LakeSensor')
    lid.box(-bx, bx, by0, by0 + 0.012, bz0, bz1, Z_BOX)
    for zz in (bz0 + 0.06, bz1 - 0.06):
        lid.box(bx - 0.006, bx + 0.008, by0 - 0.004, by0 + 0.010, zz - 0.015, zz + 0.015, Z_LATCH)
        k.box(-bx - 0.010, -bx + 0.002, by0 + 0.004, by0 + 0.016, zz - 0.02, zz + 0.02, Z_LATCH)
    lb = reg('LakeSensor_LidPrint', 'panel', 'LakeSensor', merge='LakeSensor_Lid')
    quad(lb, (0.0, by0 - 0.0004, bz1 - 0.075), (0, -1, 0), 0.144, 0.072, uv('sensor_label'))
    led = reg('LakeSensor_LED', 'led', 'LakeSensor')
    lc = Vector((0.085, by0 - 0.0006, bz0 + 0.05))
    quad(led, lc, (0, -1, 0), 0.008, 0.008, (0.0, 0.0, 1.0, 1.0))
    part('LakeSensor_Lid', 'hinge', (-bx, by0, bz0), axis=(0, 0, -1), rng=(0, 120), parent='LakeSensor',
         states=['closed', 'open'], note='the box\'s lid: hinged on the left (vertical), opens out to the front up to 120 deg; '
                                         'two latches on the right')
    part('LakeSensor_LED', 'static', lc, parent='LakeSensor_Lid', lamp_kind='status',
         note='the status LED on the lid: M_Parts_LEDG blinking = OK, M_Parts_LEDR = the battery is low, M_Parts_LED_Off = '
              'dead (in the file)')
    # the antenna on the top, the sign under the box, the cable down the post and over the ground to the probe
    k.cyl((0.08, (by0 + by1) / 2, bz1), (0.08, (by0 + by1) / 2, bz1 + 0.025), 0.010, Z_ANT, 8)
    k.cyl((0.08, (by0 + by1) / 2, bz1 + 0.025), (0.08, (by0 + by1) / 2, bz1 + 0.47), 0.0045, Z_ANT, 6, r2=0.0022)
    sy_ = -pr - 0.012
    k.box(-0.13, 0.13, sy_, sy_ + 0.006, 0.62, 0.78, Z_SIGNBACK)
    for zz in (0.66, 0.74):
        k.box(-0.02, 0.02, sy_ + 0.006, -pr + 0.002, zz - 0.012, zz + 0.012, Z_CLIP)
    quad(pk, (0.0, sy_ - 0.0004, 0.70), (0, -1, 0), 0.24, 0.14, uv('sensor_sign'))
    cab = [Vector((-0.06, (by0 + by1) / 2, bz0)), Vector((-0.06, -0.075, bz0 - 0.05)), Vector((-0.020, -pr - 0.008, bz0 - 0.10)),
           Vector((-0.012, -pr - 0.006, 0.60)), Vector((-0.012, -pr - 0.006, 0.40)), Vector((-0.012, -pr - 0.006, 0.08)),
           Vector((-0.020, -0.10, 0.012)), Vector((0.030, -0.45, 0.008)), Vector((-0.040, -0.90, 0.008)),
           Vector((0.020, -1.30, 0.008)), Vector((0.0, -1.58, 0.020))]
    k.tube(cab, 0.0055, Z_SCABLE, 5)
    for zz in (0.85, 0.50, 0.20):                                                        # cable clips on the post
        k.box(-0.022, -0.002, -pr - 0.013, -pr + 0.002, zz - 0.008, zz + 0.008, Z_CLIP)
    k.cyl((0.0, -1.58, 0.020), (0.0, -1.84, 0.020), 0.020, Z_PROBE, 8)
    k.lathe(Vector((0.0, -1.84, 0.020)), -Y, [(0.0, 0.020), (0.012, 0.010), (0.016, 0.0)], Z_PROBE, 8, cap0=False, cap1=False)
    part('LakeSensor', 'static', (0, 0, 0), note='the lake sensor (root): the post on the shore, origin on the ground at the post '
                                                 '(it goes 0.4 m in); the box to the front (-y) - the cable runs on to the probe '
                                                 'in the water 1.8 m in front: put the prefab with -y to the lake')
    socket('Slot_Battery', slot, 'slot', parent='LakeSensor', up=(0, 0, 1), forward=(0, -1, 0),
           note='forest_gear\'s Item_Battery6V: its origin here, upright, + to the left (-x); the leads\' clips sit over its '
                'springs; the lid open')
    socket('View_Sensor', (0.0, -0.75, 1.55), 'view', parent='LakeSensor', dir=(0, 1, 0),
           note='where the player stands to change the battery (eye height), the lid open')
    socket('Probe', (0.0, -1.856, 0.020), 'point', parent='LakeSensor', dir=(0, -1, 0), note='the probe\'s tip: in the water')
    BOXES.extend([('Sensor_Post', 'LakeSensor', (-pr, pr, -pr, pr, -0.40, top + 0.012), None),
                  ('Sensor_Box', 'LakeSensor', (-bx - 0.01, bx, by0 + 0.012, by1, bz0, bz1), None),
                  ('Sensor_Sign', 'LakeSensor', (-0.13, 0.13, sy_, -pr, 0.62, 0.78), None),
                  ('Sensor_Probe', 'LakeSensor', (-0.02, 0.02, -1.856, -1.58, 0.0, 0.04), None),
                  ('Sensor_Lid', 'LakeSensor_Lid', (-bx, bx + 0.008, by0 - 0.004, by0 + 0.012, bz0, bz1), None)])


def build_parts():
    build_pump()
    build_sodium()
    build_crt()
    build_relay()
    build_generator()
    build_sensor()
