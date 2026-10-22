"""Main building — the upper floor, the basement and the outside details (main_rooms carries the ground floor). Every piece
stands at its Update 3 place and size: the dressing props and notes of Update 3 (Forest_Dressing.json) spawn on these
surfaces, so table, desk and counter tops, bunks, shelves and cabinet tops keep their heights. The boiler room's controls
and the entrance door's bar form the second prefab, BaseMain_Opening, as in Update 3."""
import math
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, Z_GALV, Z_STEELBLK
import van3_mech as VM
import main_spec as S
import main_shell as MS
import main_ix_u3 as X
from main_furn import *                                              # noqa: F401,F403
import main_furn as F
import main_rooms as M1

NX, PX, NY, PY = (-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0)
OG = S.OG_F
UG = S.UG_F


def R(name):
    return MS.rkb(name)


def opening():
    return kb('BaseMain_Opening', 'MainOpening')


# ================================================================ upper floor
def kaserne():
    k = R('Kaserne')
    for (y0, y1) in ((-5.39, -4.51), (-3.44, -2.56)):
        bunk(k, -7.65, -5.65, y0, y1, OG)
    M1.boots(k, Vector((-5.58, -4.75, OG)))
    M1.boots(k, Vector((-5.53, -2.75, OG)))
    # the trestle table (plates set out, a thermos jug) and its two benches
    trestle_table(k, -4.50, -3.70, -4.70, -2.70, OG, 0.78)
    for y in (-4.60, -4.15, -3.70, -3.25, -2.80):
        plate(k, Vector((-4.25, y, OG + 0.78)))
    k.cyl(Vector((-3.90, -3.00, OG + 0.78)), Vector((-3.90, -3.00, OG + 0.90)), 0.048, F.Z_CHROME, 12)
    k.cyl(Vector((-3.90, -3.00, OG + 0.90)), Vector((-3.90, -3.00, OG + 0.92)), 0.03, Z_STEELBLK, 10)
    for x0, x1 in ((-4.89, -4.61), (-3.59, -3.31)):
        bench(k, x0, x1, -4.70, -2.70, OG, 0.47)
    # bedside units between the bunks (Update 3 doors); four lockers and the double cabinet along the corridor wall
    for y0, y1, nm in ((-4.46, -4.00, 'IX_TumbaDoor_52'), (-2.51, -2.05, 'IX_TumbaDoor_53')):
        carcass(k, (-7.65, y0, OG), (-7.25, y1, OG + 0.60), '+x', zone=F.Z_OLIVE, t=0.015, plinth=0.04, inset=0.010)
        hinged_door(nm, Vector(PX), F.Z_OLIVE, th=0.016, handle='knob', note='bedside unit door')
    locker_unit(k, ('IX_LockerDoor_54', 'IX_LockerDoor_55', 'IX_LockerDoor_56', 'IX_LockerDoor_57'),
                (-7.45, -1.65, OG), (-5.39, -1.15, OG + 1.80), NY, single=True)
    double_cabinet(k, -5.31, -4.36, -1.74, -1.15, OG, 1.80)                     # (clear of locker 57's door at 110)
    # the notice board (duty roster), radiators, detector, sockets, the switch
    B(k, (-2.15, -1.18, OG + 1.33), (-1.69, -1.15, OG + 1.73), F.Z_WOODF)         # the notice board (papers: panel)
    radiator(k, -6.45, -5.24, -5.65, 1, axis='y', zf=OG)
    radiator(k, -3.85, -2.64, -5.65, 1, axis='y', zf=OG)
    smoke_detector(k, (-4.30, -3.40, S.OG_C))
    socket_outlet(k, (-7.65, -3.95, OG + 0.30), PX)
    socket_outlet(k, (-2.40, -5.65, OG + 0.30), PY)
    rocker_switch('IX_LightSwitch_Kaserne_94', NY, 'light switch (Kaserne)', k_room=k)


def bunk(k, x0, x1, y0, y1, zf):
    """a two-tier steel bunk as in Update 3: 4 cm corner posts to 1.72, angle frames at 0.38 / 1.28 with sprung bases,
    12 cm mattresses (tops 0.54 / 1.44: the sleep zones lie on them), pillows at the head (west), a folded blanket at the
    foot; end bars between the posts"""
    p = 0.04
    for x in (x0, x1 - p):
        for y in (y0, y1 - p):
            B(k, (x, y, zf), (x + p, y + p, zf + 1.72), F.Z_OLIVE)
    for zb in (0.38, 1.28):
        z0, z1 = zf + zb, zf + zb + 0.04
        for (a, b) in (((x0 + p, y0 + 0.01), (x1 - p, y0 + 0.04)), ((x0 + p, y1 - 0.04), (x1 - p, y1 - 0.01))):
            B(k, (a[0], a[1], z0), (b[0], b[1], z1), F.Z_OLIVE)
        for (a, b) in (((x0 + 0.01, y0 + p), (x0 + 0.04, y1 - p)), ((x1 - 0.04, y0 + p), (x1 - 0.01, y1 - p))):
            B(k, (a[0], a[1], z0), (b[0], b[1], z1), F.Z_OLIVE)
        B(k, (x0 + 0.04, y0 + 0.04, z0 + 0.012), (x1 - 0.04, y1 - 0.04, z0 + 0.02), F.Z_STEELF)        # the sprung base
        VM.rbox(k, Vector(((x0 + x1) / 2, (y0 + y1) / 2, z1 + 0.06)), (x1 - x0 - 0.10, y1 - y0 - 0.10, 0.12),
                F.Z_MATTRESS, r=0.03, ch=0.015)
        VM.rbox(k, Vector((x0 + 0.28, (y0 + y1) / 2 + 0.01, z1 + 0.17)), (0.33, 0.51, 0.10), F.Z_PILLOW, r=0.04, ch=0.02)
        VM.rbox(k, Vector((x1 - 0.59, (y0 + y1) / 2, z1 + 0.14)), (0.96, y1 - y0 - 0.06, 0.04), F.Z_BLANKET, r=0.015,
                ch=0.006)
    for x in (x0 + 0.02, x1 - 0.02):                                 # end bars
        for zz in (0.15, 0.95, 1.62):
            k.cyl(Vector((x, y0 + p, zf + zz)), Vector((x, y1 - p, zf + zz)), 0.013, F.Z_OLIVE, 6)


def trestle_table(k, x0, x1, y0, y1, zf, h):
    """the barracks table: a board top on two green steel trestles"""
    rb(k, (x0, y0, zf + h - 0.04), (x1, y1, zf + h), F.Z_WOODF, r=0.006, ch=0.003)
    for yc in (y0 + 0.15, y1 - 0.15):
        for xa, xb in ((x0 + 0.05, x0 + 0.20), (x1 - 0.05, x1 - 0.20)):
            k.cyl(Vector((xa, yc, zf)), Vector((xb, yc, zf + h - 0.06)), 0.016, F.Z_OLIVE, 6)
        B(k, (x0 + 0.05, yc - 0.03, zf + h - 0.07), (x1 - 0.05, yc + 0.03, zf + h - 0.04), F.Z_OLIVE)
        k.cyl(Vector((x0 + 0.12, yc, zf + 0.25)), Vector((x1 - 0.12, yc, zf + 0.25)), 0.012, F.Z_OLIVE, 6)
    k.cyl(Vector(((x0 + x1) / 2, y0 + 0.15, zf + 0.25)), Vector(((x0 + x1) / 2, y1 - 0.15, zf + 0.25)), 0.014, F.Z_OLIVE, 6)


def bench(k, x0, x1, y0, y1, zf, h):
    rb(k, (x0, y0, zf + h - 0.04), (x1, y1, zf + h), F.Z_WOODF, r=0.006, ch=0.003)
    for y in (y0 + 0.12, y1 - 0.12):
        B(k, ((x0 + x1) / 2 - 0.10, y - 0.015, zf), ((x0 + x1) / 2 + 0.10, y + 0.015, zf + 0.03), F.Z_OLIVE)
        B(k, ((x0 + x1) / 2 - 0.015, y - 0.015, zf + 0.03), ((x0 + x1) / 2 + 0.015, y + 0.015, zf + h - 0.04), F.Z_OLIVE)
        B(k, (x0 + 0.02, y - 0.015, zf + h - 0.07), (x1 - 0.02, y + 0.015, zf + h - 0.04), F.Z_OLIVE)


def double_cabinet(k, x0, x1, y0, y1, zf, h):
    """a two-door olive steel cabinet (static: its doors are shut and not in Update 3's parts)"""
    carcass(k, (x0, y0 + 0.02, zf), (x1, y1, zf + h), '-y', zone=F.Z_OLIVE, t=0.015, plinth=0.06)
    xm = (x0 + x1) / 2
    for a, b in ((x0 + 0.004, xm - 0.002), (xm + 0.002, x1 - 0.004)):
        B(k, (a, y0, zf + 0.065), (b, y0 + 0.02, zf + h - 0.005), F.Z_OLIVE)
        for i in range(4):
            zz = zf + h - 0.16 - i * 0.03
            B(k, (a + 0.08, y0 - 0.004, zz), (b - 0.08, y0, zz + 0.012), F.Z_STEELF)
    for x in (xm - 0.04, xm + 0.04):
        F.bar_handle(k, (x, y0, zf + 1.0), 0.14, (0, 0, 1), (0, -1, 0))


def plate(k, c, r=0.105, h=0.02):
    k.lathe(c, Vector((0, 0, 1)), [(0.0, r * 0.6), (h * 0.3, r * 0.62), (h * 0.8, r), (h, r)], F.Z_PLATE, 16)


def kueche():
    k = R('Kueche')
    kitchen_block(k, OG)
    fridge(k)
    table(k, 3.90, 5.30, -4.10, -3.30, OG, 0.755, top_zone=F.Z_LAMINATE, leg_zone=F.Z_CHROME)
    for i in range(5):                                               # the plate stack (a mug of Update 3 on it), mugs
        plate(k, Vector((4.30, -3.55, OG + 0.755 + i * 0.0118)), r=0.12, h=0.0108)
    for (x, y, z) in ((4.30, -3.85, F.Z_DRUM_R), (4.70, -3.95, F.Z_MUG), (4.80, -3.60, F.Z_MUG), (4.85, -3.45, F.Z_MUG)):
        M1.mug(k, Vector((x, y, OG + 0.755)))
    B(k, (4.475, -3.66, OG + 0.755), (4.725, -3.34, OG + 0.765), F.Z_PAPER)
    for c, yaw in (((4.25, -4.32), 180), ((4.95, -4.24), 180), ((4.25, -3.24), 0), ((4.945, -3.32), 0)):
        tube_chair(k, Vector((c[0], c[1], OG)), yaw)
    sofa(k, OG)
    tv_set(k, OG)
    table(k, -0.15, 0.45, -4.20, -3.20, OG, 0.49, top_zone=F.Z_WOODF, leg_zone=F.Z_WOODF)
    armchair(k, Vector((-0.145, -4.91, OG)), yaw=215)
    radiator(k, -4.65, -3.44, 7.65, -1, axis='x', zf=OG)
    M1.clock(k, (3.60, -1.15, OG + 2.00), NY, r=0.13)
    speaker(k, (0.50, -1.15, OG + 2.60), NY)
    first_aid(k, (7.65, -1.95, OG + 1.43), NX)
    smoke_detector(k, (1.50, -3.40, S.OG_C))
    for x in (4.62, 5.62):
        socket_outlet(k, (x, -1.15, OG + 1.12), NY)
    socket_outlet(k, (-1.45, -3.40, OG + 0.30), PX)
    rocker_switch('IX_LightSwitch_Kueche_96', NY, 'light switch (Kueche)', k_room=k, pair='IX_ShutterSwitch_Kueche_129')
    rocker_switch('IX_ShutterSwitch_Kueche_129', NY, 'roller shutters, electric (Kueche): all four curtains; needs mains')


def kitchen_block(k, zf):
    """Update 3's kitchen run: four base cabinets (x 4.09..6.49), the worktop at 0.90 (pots and plates of Update 3 stand
    on it), the flush hob with four plates (x 4.26..4.82), the sink (x 5.79..6.29) and its tap, the coffee maker and the
    kettle, the microwave, the tiled splashback, four wall cabinets"""
    y0, y1 = -1.77, -1.15
    B(k, (4.09, y0 + 0.08, zf), (6.49, y1, zf + 0.08), F.Z_RUBBERB)
    B(k, (4.09, y0 + 0.03, zf + 0.08), (6.49, y1, zf + 0.87), F.Z_LAMINATE, skip=('-y',))
    for i in range(4):
        xa = 4.11 + i * 0.60
        B(k, (xa, y0 + 0.02, zf + 0.08), (xa + 0.56, y0 + 0.03, zf + 0.84), F.Z_LAMINATE)
        F.bar_handle(k, (xa + 0.28, y0 + 0.02, zf + 0.78), 0.12, (1, 0, 0), (0, -1, 0), stand=0.015)
    for xa, xb in ((4.09, 4.11), (4.67, 4.71), (5.27, 5.31), (5.87, 5.91), (6.47, 6.49)):
        B(k, (xa, y0 + 0.02, zf + 0.08), (xb, y0 + 0.03, zf + 0.87), F.Z_LAMINATE)
    B(k, (4.09, y0 + 0.02, zf + 0.84), (6.49, y0 + 0.03, zf + 0.87), F.Z_LAMINATE)
    # the worktop (the sink cut out) with the hob set flush
    top = zf + 0.90
    for (xa, xb, ya, yb) in ((4.08, 5.79, y0, y1), (6.29, 6.50, y0, y1), (5.79, 6.29, y0, -1.65), (5.79, 6.29, -1.25, y1)):
        B(k, (xa, ya, top - 0.03), (xb, yb, top), F.Z_DESKTOP)
    B(k, (4.26, -1.70, top), (4.82, -1.20, top + 0.007), F.Z_STOVE)
    for (cx, cy, r) in ((4.41, -1.56, 0.09), (4.41, -1.34, 0.07), (4.67, -1.34, 0.09), (4.67, -1.56, 0.07)):
        k.cyl(Vector((cx, cy, top + 0.007)), Vector((cx, cy, top + 0.009)), r, Z_STEELBLK, 16)
    B(k, (4.30, -1.72, top - 0.02), (4.80, -1.70, top), F.Z_STOVE)                 # the knobs' strip
    for i in range(4):
        k.cyl(Vector((4.36 + i * 0.12, -1.72, top - 0.01)), Vector((4.36 + i * 0.12, -1.74, top - 0.01)), 0.009,
              Z_STEELBLK, 8)
    # the stainless sink, its rim, the tap with its spout over the basin
    B(k, (5.79, -1.65, top - 0.17), (6.29, -1.25, top - 0.15), F.Z_SINK)
    for (a, b) in (((5.79, -1.65), (5.80, -1.25)), ((6.28, -1.65), (6.29, -1.25)), ((5.80, -1.65), (6.28, -1.60)),
                   ((5.80, -1.26), (6.28, -1.25))):
        B(k, (a[0], a[1], top - 0.15), (b[0], b[1], top + 0.002), F.Z_SINK)
    k.cyl(Vector((5.92, -1.45, top - 0.151)), Vector((5.92, -1.45, top - 0.149)), 0.025, Z_STEELBLK, 10)
    k.tube([Vector((6.04, -1.21, top)), Vector((6.04, -1.21, top + 0.24)), Vector((6.04, -1.33, top + 0.24)),
            Vector((6.04, -1.35, top + 0.21))], 0.012, F.Z_CHROME, 8)
    B(k, (6.01, -1.24, top + 0.10), (6.07, -1.18, top + 0.13), F.Z_CHROME)
    # the coffee maker (black, a glass jug) and the chrome kettle stand on the hob's back plates, as in Update 3
    VM.rbox(k, Vector((4.44, -1.35, top + 0.16)), (0.22, 0.25, 0.32), Z_STEELBLK, r=0.02, ch=0.008)
    k.cyl(Vector((4.44, -1.45, top + 0.007)), Vector((4.44, -1.45, top + 0.14)), 0.062, F.Z_SCREEN, 12)
    k.lathe(Vector((4.74, -1.45, top + 0.009)), Vector((0, 0, 1)), [(0.0, 0.065), (0.12, 0.06), (0.17, 0.035), (0.20, 0.0)],
            F.Z_CHROME, 12)
    k.tube([Vector((4.74, -1.39, top + 0.20)), Vector((4.74, -1.39, top + 0.215)), Vector((4.74, -1.51, top + 0.215)),
            Vector((4.74, -1.51, top + 0.17))], 0.007, Z_STEELBLK, 6)
    # the microwave, its door window and controls
    B(k, (5.00, -1.58, top + 0.01), (5.48, -1.22, top + 0.31), F.Z_ENAMELW)
    B(k, (5.15, -1.584, top + 0.06), (5.45, -1.58, top + 0.26), F.Z_SCREEN)
    B(k, (5.01, -1.584, top + 0.06), (5.09, -1.58, top + 0.26), Z_STEELBLK)
    # the splashback, the wall cabinets
    B(k, (4.08, y1 - 0.008, top), (6.50, y1, zf + 1.50), F.Z_TILESPL)
    for i in range(4):
        xa = 4.10 + i * 0.60
        B(k, (xa, -1.50, zf + 1.50), (xa + 0.58, -1.16, zf + 2.20), F.Z_LAMINATE)
        F.bar_handle(k, (xa + 0.29, -1.50, zf + 1.56), 0.10, (1, 0, 0), (0, -1, 0), stand=0.015)


def fridge(k):
    """the tall fridge-freezer at the run's end (body x 6.50..7.10, top 1.84: a plate of Update 3 lies on it), white
    inside with wire shelves and the freezer box; its door is the Update 3 part"""
    nm = 'IX_FridgeDoor_58'
    x0, x1, y0, y1, z0, z1 = 6.50, 7.10, -1.777, -1.16, OG, OG + 1.84
    carcass(k, (x0, y0, z0), (x1, y1, z1), '-y', zone=F.Z_ENAMELW, t=0.04, plinth=0.05)
    for z in (0.45, 0.80, 1.10):
        for i in range(9):
            x = x0 + 0.07 + i * 0.058
            k.cyl(Vector((x, y0 + 0.03, z0 + z)), Vector((x, y1 - 0.06, z0 + z)), 0.003, F.Z_CHROME, 4)
    B(k, (x0 + 0.04, y0 + 0.03, z0 + 1.36), (x1 - 0.04, y1 - 0.04, z0 + 1.40), F.Z_ENAMELW)    # the freezer's floor
    B(k, (x0 + 0.05, y0 + 0.03, z0 + 1.42), (x1 - 0.05, y0 + 0.045, z0 + 1.76), F.Z_CABGREY)   # its flap
    d = hinged_door(nm, Vector(NY), F.Z_ENAMELW, th=0.05, handle=None, note='fridge door')
    lo, hi = lohi(nm)
    p = Vector(X.IX[nm]['pivot'])
    far, sg = (lo.x, 1) if abs(p.x - hi.x) < abs(p.x - lo.x) else (hi.x, -1)
    F.bar_handle(d, (far + sg * 0.045, p.y - 0.042, (lo.z + hi.z) / 2 + 0.20), 0.40, (0, 0, 1), (0, -1, 0), zone=F.Z_CHROME)


def table(k, x0, x1, y0, y1, zf, h, top_zone=None, leg_zone=None):
    rb(k, (x0, y0, zf + h - 0.035), (x1, y1, zf + h), top_zone or F.Z_WOODF, r=0.008, ch=0.004)
    for x in (x0 + 0.05, x1 - 0.05):
        for y in (y0 + 0.08, y1 - 0.08):
            B(k, (x - 0.02, y - 0.02, zf), (x + 0.02, y + 0.02, zf + h - 0.035), leg_zone or F.Z_STEELF)
    B(k, (x0 + 0.05, y0 + 0.08, zf + h - 0.10), (x0 + 0.07, y1 - 0.08, zf + h - 0.035), leg_zone or F.Z_STEELF)
    B(k, (x1 - 0.07, y0 + 0.08, zf + h - 0.10), (x1 - 0.05, y1 - 0.08, zf + h - 0.035), leg_zone or F.Z_STEELF)


def tube_chair(k, base, yaw):
    """a chrome-legged kitchen chair, grey padded seat and back (back toward +y at yaw 0)"""
    R_ = Matrix.Rotation(math.radians(yaw), 3, 'Z')
    for dx, dy in ((-0.18, -0.18), (0.18, -0.18), (-0.18, 0.18), (0.18, 0.18)):
        p = base + R_ @ Vector((dx, dy, 0))
        k.cyl(p, p + Vector((0, 0, 0.44)), 0.011, F.Z_CHROME, 6)
    VM.obox(k, base + Vector((0, 0, 0.465)), (0.42, 0.42, 0.05), F.Z_CHAIRSEAT, R_)
    for dx in (-0.18, 0.18):
        p = base + R_ @ Vector((dx, 0.19, 0.44))
        k.cyl(p, p + Vector((0, 0, 0.38)), 0.011, F.Z_CHROME, 6)
    VM.obox(k, base + R_ @ Vector((0, 0.20, 0.70)), (0.40, 0.03, 0.30), F.Z_CHAIRSEAT, R_)


def sofa(k, zf):
    """the 70s sofa (brown fabric, wooden feet) facing the TV (-x): its arms (top 0.75), seat (0.50) and back (0.90)
    carry Update 3's mugs, jars and the kettle"""
    x0, x1, y0, y1 = 0.77, 1.63, -4.40, -2.40
    for x in (x0 + 0.06, x1 - 0.06):
        for y in (y0 + 0.06, y1 - 0.06):
            k.cyl(Vector((x, y, zf)), Vector((x, y, zf + 0.07)), 0.022, F.Z_WOODF, 8)
    VM.rbox(k, Vector(((x0 + 0.02 + x1 - 0.20) / 2, (y0 + y1) / 2, zf + 0.185)), (x1 - 0.20 - x0 - 0.02, y1 - y0 - 0.40, 0.23),
            F.Z_FABRIC_B, r=0.03, ch=0.015)
    VM.rbox(k, Vector(((x0 + 0.02 + x1 - 0.20) / 2, (y0 + y1) / 2, zf + 0.40)), (x1 - 0.20 - x0 - 0.02, y1 - y0 - 0.42, 0.20),
            F.Z_FABRIC_B, r=0.05, ch=0.02)
    VM.rbox(k, Vector((x1 - 0.10, (y0 + y1) / 2, zf + 0.485)), (0.20, y1 - y0 - 0.40, 0.83), F.Z_FABRIC_B, r=0.05, ch=0.02)
    for ya, yb in ((y0, y0 + 0.20), (y1 - 0.20, y1)):
        VM.rbox(k, Vector(((x0 + x1) / 2, (ya + yb) / 2, zf + 0.41)), (x1 - x0, yb - ya, 0.68), F.Z_FABRIC_B, r=0.05, ch=0.02)


def tv_set(k, zf):
    """the TV on its low cabinet (dark laminate), screen toward the sofa (+x); its top at 1.066 holds two plates"""
    x0, x1, y0, y1 = -1.45, -0.96, -3.90, -2.90
    B(k, (x0, y0, zf + 0.04), (x1, y1, zf + 0.55), F.Z_TV)
    B(k, (x0 + 0.03, y0 + 0.03, zf), (x1 - 0.03, y1 - 0.03, zf + 0.04), F.Z_RUBBERB)
    B(k, (x1 - 0.004, y0 + 0.05, zf + 0.10), (x1, y1 - 0.05, zf + 0.50), F.Z_TV)
    VM.rbox(k, Vector((-1.21, -3.40, zf + 0.808)), (0.42, 0.62, 0.516), Z_STEELBLK, r=0.03, ch=0.01)
    B(k, (-0.997, -3.62, zf + 0.62), (-0.993, -3.18, zf + 0.98), F.Z_SCREENP)
    for i in range(3):
        k.cyl(Vector((-0.995, -3.10, zf + 0.92 - i * 0.07)), Vector((-0.985, -3.10, zf + 0.92 - i * 0.07)), 0.012,
              F.Z_CHROME, 8)


def armchair(k, base, yaw=0):
    """the green armchair by the window, its back toward the window corner"""
    R_ = Matrix.Rotation(math.radians(yaw), 3, 'Z')
    for dx, dy in ((-0.30, -0.30), (0.30, -0.30), (-0.30, 0.30), (0.30, 0.30)):
        p = base + R_ @ Vector((dx, dy, 0))
        leg(k, p.x, p.y, base.z, base.z + 0.24, r=0.018, zone=F.Z_WOODF, seg=6)
    VM.obox(k, base + Vector((0, 0, 0.36)), (0.70, 0.70, 0.24), F.Z_FABRIC_G, R_)
    VM.obox(k, base + R_ @ Vector((0, 0.28, 0.66)), (0.70, 0.14, 0.40), F.Z_FABRIC_G, R_)
    for dx in (-0.30, 0.30):
        VM.obox(k, base + R_ @ Vector((dx, -0.02, 0.56)), (0.10, 0.62, 0.20), F.Z_FABRIC_G, R_)


def flur_og():
    k = R('Flur_OG')
    extinguisher(k, (-0.91, -1.00, OG + 0.55), PY)
    dist_sub(k, -3.00, 1.00, OG)
    alarm_bell(k, (0.60, -1.00, OG + 2.50), PY)
    call_point(k, (1.25, 1.00, OG + 1.45), NY)
    speaker(k, (-4.60, -1.00, OG + 2.64), PY)
    for x in (0.0, 5.60):
        smoke_detector(k, (x, 0.0, S.OG_C))
    rocker_switch('IX_LightSwitch_Flur_OG_95', NY, 'light switch (corridor, upper floor)', k_room=k)
    socket_outlet(k, (5.00, -1.00, OG + 0.30), PY)


def dist_sub(k, x, y_wall, zf):
    """the sub-distribution board UV-OG: a grey steel cabinet with a window strip, its conduits up to the ceiling"""
    B(k, (x - 0.23, y_wall - 0.14, zf + 1.00), (x + 0.23, y_wall, zf + 1.80), F.Z_BOARDC)
    B(k, (x - 0.20, y_wall - 0.142, zf + 1.30), (x + 0.20, y_wall - 0.14, zf + 1.45), F.Z_SCREEN)
    F.bar_handle(k, (x + 0.18, y_wall - 0.14, zf + 1.40), 0.10, (0, 0, 1), (0, -1, 0), stand=0.02)
    for dx in (-0.15, -0.05, 0.05, 0.15):
        F.conduit_run(k, [Vector((x + dx, y_wall - 0.03, zf + 1.80)), Vector((x + dx, y_wall - 0.03, S.OG_C - 0.02))])


def waschraum():
    k = R('Waschraum')
    for (y0, y1) in ((3.75, 4.65), (4.70, 5.60)):
        shower(k, -7.65, -6.75, y0, y1, OG)
    wc_cubicles(k)
    trough(k, -7.65, -7.15, 1.55, 3.55, OG)
    B(k, (-2.46, 1.50, OG), (-1.96, 2.00, OG + 0.86), F.Z_WASHM)                # washing machine (a towel on it)
    k.cyl(Vector((-2.46, 1.75, OG + 0.50)), Vector((-2.475, 1.75, OG + 0.50)), 0.17, F.Z_SCREEN, 16)
    k.cyl(Vector((-2.46, 1.75, OG + 0.50)), Vector((-2.47, 1.75, OG + 0.50)), 0.20, F.Z_CHROME, 16)
    B(k, (-2.462, 1.55, OG + 0.76), (-2.46, 1.95, OG + 0.84), Z_STEELBLK)
    towel_rack(k)
    for y in (2.90, 3.20, 3.50):                                     # rubber boots under the rack
        M1.boots(k, Vector((-2.17, y, OG)))
    socket_outlet(k, (-1.95, 1.75, OG + 1.20), NX, kind='surface')
    rocker_switch('IX_LightSwitch_Waschraum_97', PY, 'light switch (Waschraum)', k_room=k)


def towel_rack(k):
    """the wall rack: a laminate shelf at 0.92 with folded towels, the top shelf at 1.72 (a soap of Update 3 on it), chrome
    brackets"""
    x0, x1, y0, y1 = -2.15, -1.95, 2.75, 3.58
    for z in (0.90, 1.70):
        B(k, (x0, y0, OG + z), (x1, y1, OG + z + 0.02), F.Z_LAMINATE)
        for y in (y0 + 0.05, y1 - 0.05):
            B(k, (x0 + 0.04, y - 0.006, OG + z - 0.10), (x1, y + 0.006, OG + z), F.Z_CHROME)
    for i, y in enumerate((2.90, 3.17, 3.44)):
        VM.rbox(k, Vector((-2.055, y, OG + 0.98)), (0.17, 0.22, 0.12), F.Z_TOWEL if i != 1 else F.Z_PILLOW, r=0.03, ch=0.01)
    k.cyl(Vector((-2.13, y0 + 0.08, OG + 1.40)), Vector((-2.13, y1 - 0.08, OG + 1.40)), 0.010, F.Z_CHROME, 8)
    VM.rbox(k, Vector((-2.12, 3.17, OG + 1.20)), (0.04, 0.50, 0.40), F.Z_TOWEL, r=0.01, ch=0.005)


def shower(k, x0, x1, y0, y1, zf):
    """a shower cubicle: enamel tray, a glass wall on its north side on aluminium profiles, a curtain rail on the open
    side, the chrome riser and head on the west wall (y0 + 0.15)"""
    B(k, (x0, y0, zf), (x1, y1, zf + 0.08), F.Z_SHOWER)
    kg = kb('R_Waschraum_Glass', 'glass')
    if y1 < 5.6:
        for side in (1, -1):
            yy = y1 - 0.01 + side * 0.004
            face(kg, [(x0 + 0.02, yy, zf + 0.10), (x1 - 0.02, yy, zf + 0.10), (x1 - 0.02, yy, zf + 2.0),
                      (x0 + 0.02, yy, zf + 2.0)], 0, (0, side, 0))
        B(k, (x1 - 0.02, y1 - 0.02, zf + 0.08), (x1, y1, zf + 2.0), F.Z_CHROME)
        B(k, (x0 + 0.02, y1 - 0.02, zf + 1.98), (x1 - 0.02, y1, zf + 2.0), F.Z_CHROME)
    k.cyl(Vector((x1 - 0.01, y0 + 0.03, zf + 2.0)), Vector((x1 - 0.01, y1 - 0.03, zf + 2.0)), 0.010, F.Z_CHROME, 6)
    B(k, (x1 - 0.02, y0 + 0.04, zf + 0.30), (x1, y0 + 0.30, zf + 1.98), F.Z_CURTAIN)
    yc = y0 + 0.15
    k.cyl(Vector((x0 + 0.03, yc, zf + 1.00)), Vector((x0 + 0.03, yc, zf + 2.06)), 0.012, F.Z_CHROME, 8)
    B(k, (x0, yc - 0.08, zf + 1.00), (x0 + 0.06, yc + 0.08, zf + 1.10), F.Z_CHROME)
    k.tube([Vector((x0 + 0.03, yc, zf + 2.04)), Vector((x0 + 0.22, yc, zf + 2.04)), Vector((x0 + 0.26, yc, zf + 2.0))], 0.010,
           F.Z_CHROME, 6)
    k.cyl(Vector((x0 + 0.28, yc, zf + 2.00)), Vector((x0 + 0.28, yc, zf + 1.97)), 0.04, F.Z_CHROME, 12)


def wc_cubicles(k):
    """two WC cubicles in the NE corner: laminate partitions on legs, doors ajar, white bowls (seat top 0.41: a towel of
    Update 3 lies on one) and cisterns"""
    x0, x1, y0, y1 = -3.97, -1.95, 4.23, 5.65
    for xa in (x0, -2.96):
        B(k, (xa, y0, OG + 0.15), (xa + 0.03, y1, OG + 2.00), F.Z_CUBICLE)
        for y in (y0 + 0.05, y1 - 0.05):
            k.cyl(Vector((xa + 0.015, y, OG)), Vector((xa + 0.015, y, OG + 0.15)), 0.012, F.Z_CHROME, 6)
    B(k, (x0 + 0.03, y0, OG + 0.15), (x0 + 0.30, y0 + 0.03, OG + 2.00), F.Z_CUBICLE)
    B(k, (-2.93, y0, OG + 0.15), (-2.70, y0 + 0.03, OG + 2.00), F.Z_CUBICLE)
    for xa, xb in ((x0 + 0.30, -2.98), (-2.70, x1 - 0.02)):          # the doors, ajar (hinged at their west edge)
        R_ = Matrix.Rotation(math.radians(-25), 3, 'Z')
        w = xb - xa
        c = Vector((xa, y0 + 0.015, OG + 1.075)) + R_ @ Vector((w / 2, 0, 0))
        VM.obox(k, c, (w, 0.025, 1.85), F.Z_CUBICLE, R_)
    for xm in (-3.45, -2.45):
        k.lathe(Vector((xm, 5.21, OG)), Vector((0, 0, 1)), [(0.0, 0.11), (0.25, 0.14), (0.36, 0.19), (0.38, 0.19)],
                F.Z_ENAMELW, 14)
        rb(k, (xm - 0.21, 5.00, OG + 0.38), (xm + 0.21, 5.42, OG + 0.41), F.Z_WOODF, r=0.05, ch=0.01)   # the closed lid
        B(k, (xm - 0.21, 5.46, OG + 0.54), (xm + 0.21, 5.64, OG + 0.96), F.Z_ENAMELW)
        k.cyl(Vector((xm + 0.12, 5.46, OG + 0.92)), Vector((xm + 0.12, 5.44, OG + 0.92)), 0.015, F.Z_CHROME, 8)
        k.cyl(Vector((xm, 5.55, OG + 0.54)), Vector((xm, 5.55, OG + 0.40)), 0.02, F.Z_CHROME, 8)


def trough(k, x0, x1, y0, y1, zf):
    """the galvanised wash stand on legs: a flat top at 0.835 (Update 3's cups, soap and a note stand on it) with four
    basins along its front edge, long-spout taps on a rail, a mirror over each"""
    top = zf + 0.835
    B(k, (x0, y0, top - 0.15), (x1, y1, top - 0.005), Z_GALV)
    ys = [y0 + 0.25 + i * 0.5 for i in range(4)]
    bx0, bx1 = x1 - 0.20, x1 - 0.04
    cuts = [(y - 0.13, y + 0.13) for y in ys]
    edges = [y0] + [v for c in cuts for v in c] + [y1]
    B(k, (x0, y0, top - 0.005), (bx0, y1, top), F.Z_CHROME, skip=('-z',))
    B(k, (bx1, y0, top - 0.005), (x1, y1, top), F.Z_CHROME, skip=('-z',))
    for ya, yb in zip(edges[0::2], edges[1::2]):
        B(k, (bx0, ya, top - 0.005), (bx1, yb, top), F.Z_CHROME, skip=('-z',))
    for y in ys:
        B(k, (bx0, y - 0.13, top - 0.10), (bx1, y + 0.13, top - 0.005), F.Z_SINK, skip=('+z',))
        k.cyl(Vector(((bx0 + bx1) / 2, y, top - 0.099)), Vector(((bx0 + bx1) / 2, y, top - 0.097)), 0.02, Z_STEELBLK, 8)
    for y in (y0 + 0.08, y1 - 0.08):
        for x in (x0 + 0.06, x1 - 0.06):
            leg(k, x, y, zf, top - 0.15, r=0.02, zone=Z_GALV)
    k.cyl(Vector((x0 + 0.03, y0, zf + 1.05)), Vector((x0 + 0.03, y1, zf + 1.05)), 0.014, F.Z_CHROME, 8)
    for i in range(4):
        y = y0 + 0.25 + i * 0.5
        k.tube([Vector((x0 + 0.03, y, zf + 1.05)), Vector((x0 + 0.30, y, zf + 1.05)), Vector((x0 + 0.38, y, zf + 0.98))],
               0.010, F.Z_CHROME, 6)
        k.cyl(Vector((x0 + 0.03, y, zf + 1.05)), Vector((x0 + 0.03, y, zf + 1.10)), 0.016, F.Z_CHROME, 8)
        B(k, (x0, y - 0.20, zf + 1.20), (x0 + 0.008, y + 0.20, zf + 1.70), F.Z_MIRROR)


def stationsleiter():
    k = R('Stationsleiter')
    bookshelf(k, 6.30, 7.10, 1.15, 1.47, OG)
    desk(k, 4.20, 5.80, 3.51, 4.35, top_z=OG + 0.75, front='+y', pedestal_x=5.55, zf=OG)
    pedestal(k, ('IX_Drawer_59', 'IX_Drawer_60', 'IX_Drawer_61'), PY, (5.35, 3.65, OG), (5.75, 4.28, OG + 0.72))
    office_chair(k, (4.97, 4.65, OG), yaw=0)
    wood_chair(k, (4.54, 2.965, OG), yaw=180, seat_zone=F.Z_FABRIC_B)
    pedestal(k, ('IX_Drawer_62', 'IX_Drawer_63', 'IX_Drawer_64', 'IX_Drawer_65'), PX, (1.95, 4.71, OG), (2.57, 5.18, OG + 1.32))
    pedestal(k, ('IX_Drawer_66', 'IX_Drawer_67', 'IX_Drawer_68'), PX, (1.95, 4.21, OG), (2.57, 4.68, OG + 1.32))
    B(k, (2.57, 4.237, OG + 0.99), (2.588, 4.663, OG + 1.30), F.Z_DRAWER)           # the fixed top front of cabinet B
    safe(k, 7.10, 7.65, 1.70, 2.30, OG)
    radiator(k, 4.24, 5.45, 5.65, -1, axis='y', zf=OG)
    M1.clock(k, (4.30, 1.15, OG + 2.00), PY, r=0.13)
    red_phone(k, OG + 0.75)
    B(k, (4.518, 3.776, OG + 0.75), (4.842, 4.044, OG + 0.752), F.Z_PAPER)
    M1.mug(k, Vector((4.392, 4.046, OG + 0.75)))
    M1.mug(k, Vector((5.55, 4.10, OG + 0.75)))
    smoke_detector(k, (3.40, 4.60, S.OG_C))
    socket_outlet(k, (5.20, 5.65, OG + 0.30), NY)
    socket_outlet(k, (1.95, 3.40, OG + 0.30), PX)
    rocker_switch('IX_LightSwitch_Stationsleiter_98', PY, 'light switch (Stationsleiter)', k_room=k,
                  pair='IX_ShutterSwitch_Stationsleiter_130')
    rocker_switch('IX_ShutterSwitch_Stationsleiter_130', PY,
                  'roller shutters, electric (Stationsleiter): three curtains; needs mains')


def bookshelf(k, x0, x1, y0, y1, zf):
    B(k, (x0, y0, zf), (x0 + 0.02, y1, zf + 1.90), F.Z_WOODF)
    B(k, (x1 - 0.02, y0, zf), (x1, y1, zf + 1.90), F.Z_WOODF)
    B(k, (x0 + 0.02, y0, zf), (x1 - 0.02, y0 + 0.01, zf + 1.90), F.Z_WOODF)
    for i in range(6):
        z = zf + 0.05 + i * 0.36
        B(k, (x0 + 0.02, y0, z), (x1 - 0.02, y1, z + 0.02), F.Z_WOODF)
        if i < 5:
            n = 14
            xa = x0 + 0.03
            for j in range(n):
                w = 0.035 + ((i + j * 5) % 4) * 0.012
                h = 0.22 + ((i * 3 + j * 7) % 5) * 0.025
                if xa + w > x1 - 0.04:
                    break
                B(k, (xa, y0 + 0.03, z + 0.02), (xa + w - 0.003, y1 - 0.02, z + 0.02 + h), F.Z_BOOKS)
                xa += w


def safe(k, x0, x1, y0, y1, zf):
    """the chief's safe (Update 3: a green steel box by the window; the note chief_safe gives its combination): body,
    the door toward the room with its dial and the bolt handle (static: no part in Update 3); a binder lies on it"""
    h = 1.00
    B(k, (x0 + 0.03, y0, zf), (x1, y1, zf + h), F.Z_SAFE)
    B(k, (x0, y0 + 0.03, zf + 0.06), (x0 + 0.03, y1 - 0.03, zf + h - 0.06), F.Z_SAFE)
    for (a, b) in (((x0, y0), (x0 + 0.03, y0 + 0.03)), ((x0, y1 - 0.03), (x0 + 0.03, y1))):
        B(k, (a[0], a[1], zf), (b[0], b[1], zf + h), F.Z_SAFE)
    B(k, (x0, y0 + 0.03, zf), (x0 + 0.03, y1 - 0.03, zf + 0.06), F.Z_SAFE)
    B(k, (x0, y0 + 0.03, zf + h - 0.06), (x0 + 0.03, y1 - 0.03, zf + h), F.Z_SAFE)
    c = Vector((x0, (y0 + y1) / 2 + 0.06, zf + 0.62))
    k.cyl(c, c - Vector((0.025, 0, 0)), 0.045, F.Z_CHROME, 16)
    k.cyl(c - Vector((0.025, 0, 0)), c - Vector((0.04, 0, 0)), 0.012, F.Z_CHROME, 8)
    hc = Vector((x0, (y0 + y1) / 2 - 0.12, zf + 0.62))
    k.cyl(hc, hc - Vector((0.05, 0, 0)), 0.012, F.Z_CHROME, 8)
    k.cyl(hc - Vector((0.05, 0, 0.08)), hc - Vector((0.05, 0, -0.08)), 0.010, F.Z_CHROME, 8)
    for z in (0.15, h - 0.15):
        k.cyl(Vector((x0 - 0.005, y1 - 0.03, zf + z - 0.05)), Vector((x0 - 0.005, y1 - 0.03, zf + z + 0.05)), 0.012,
              F.Z_STEELF, 8)


def red_phone(k, z):
    """the chief's red telephone (Update 3: body 5.37..5.61 / 3.51..3.77, top 0.10 over the desk; a medicine box of
    Update 3 lies on it): body, the dial on its sloped front, the handset in the cradle"""
    VM.rbox(k, Vector((5.491, 3.637, z + 0.05)), (0.244, 0.256, 0.10), F.Z_DRUM_R, r=0.025, ch=0.01)
    c = Vector((5.525, 3.52, z + 0.235 - 0.15))
    k.cyl(Vector((5.525, 3.512, z + 0.085)), Vector((5.525, 3.505, z + 0.085)), 0.045, F.Z_ENAMELW, 14)
    VM.rbox(k, Vector((5.491, 3.6375, z + 0.12)), (0.215, 0.06, 0.04), F.Z_DRUM_R, r=0.015, ch=0.006, axis='x')
    for x in (5.40, 5.58):
        VM.rbox(k, Vector((x, 3.6375, z + 0.115)), (0.05, 0.11, 0.05), F.Z_DRUM_R, r=0.015, ch=0.006)


# ================================================================ basement
def heizung():
    k = R('Heizung')
    oil_store(k)
    boiler(k)
    # hot-water cylinder, the pump group on its insulated manifold, the mains up to the ceiling and into the corridor
    k.cyl(Vector((3.95, -1.55, UG + 0.06)), Vector((3.95, -1.55, UG + 1.80)), 0.30, F.Z_CYL, 18)
    k.lathe(Vector((3.95, -1.55, UG + 1.80)), Vector((0, 0, 1)), [(0.0, 0.30), (0.05, 0.27), (0.08, 0.15), (0.09, 0.0)],
            F.Z_CYL, 18, cap0=False)
    for a in (0.0, 2.094, 4.189):
        p = Vector((3.95 + 0.24 * math.cos(a), -1.55 + 0.24 * math.sin(a), UG))
        k.cyl(p, p + Vector((0, 0, 0.06)), 0.03, F.Z_STEELF, 8)
    k.tube([Vector((3.95, -1.55, UG + 1.89)), Vector((3.95, -1.55, UG + 2.45)), Vector((3.54, -1.55, UG + 2.45)),
            Vector((3.54, -1.20, UG + 2.45))], 0.011, F.Z_COPPER, 6)
    k.tube([Vector((3.67, -1.55, UG + 0.25)), Vector((3.54, -1.55, UG + 0.25)), Vector((3.54, -1.55, UG + 2.40))], 0.011,
           F.Z_COPPER, 6)
    B(k, (4.20, -1.40, UG + 0.75), (5.40, -1.25, UG + 0.88), F.Z_INSUL)
    for x in (4.32, 4.60, 5.05):
        k.cyl(Vector((x, -1.33, UG + 0.88)), Vector((x, -1.33, UG + 2.30)), 0.016, F.Z_COPPER, 8)
        VM.rbox(k, Vector((x, -1.39, UG + 1.08)), (0.10, 0.20, 0.16), F.Z_PUMPG, r=0.02, ch=0.008)
        k.cyl(Vector((x, -1.33, UG + 1.32)), Vector((x, -1.42, UG + 1.32)), 0.022, F.Z_BRASS, 8)
        k.cyl(Vector((x - 0.05, -1.42, UG + 1.32)), Vector((x + 0.05, -1.42, UG + 1.32)), 0.008,
              F.Z_DRUM_R if x < 4.8 else F.Z_DRUM_B, 6)
    for i, y in enumerate((-1.30, -1.24)):                           # flow / return headers -> the corridor's mains
        z = UG + 2.30 + i * 0.08
        k.cyl(Vector((3.70, y, z)), Vector((6.30, y, z)), 0.045, F.Z_INSUL, 10)
        k.cyl(Vector((3.70 + i * 0.18, y, z)), Vector((3.70 + i * 0.18, -1.15, z)), 0.045, F.Z_INSUL, 10)
    for x in (4.20, 5.20, 6.20):
        B(k, (x - 0.01, -1.33, UG + 2.36), (x + 0.01, -1.21, UG + 2.38), F.Z_STEELF)
        B(k, (x - 0.01, -1.33, UG + 2.38), (x + 0.01, -1.31, S.UG_C), F.Z_STEELF)
    for x in (6.10, 6.30):                                           # the boiler's flow / return up to the headers
        k.cyl(Vector((x, -1.30, UG + 1.55)), Vector((x, -1.30, UG + 2.30)), 0.03, F.Z_INSUL, 8)
    # the electrics: the controller cabinet by the door (its front with the switches is BaseMain_Opening), the switch's
    # surface box, a socket, conduits with their junction boxes at 2.52
    B(k, (0.65, -1.34, UG + 1.20), (1.15, -1.156, UG + 2.70), F.Z_BOARDC)
    for (x, top) in ((0.80, S.UG_C - 0.02), (1.00, S.UG_C - 0.02)):
        F.conduit_run(k, [Vector((x, -1.18, UG + 2.70)), Vector((x, -1.18, top))])
    rocker_switch('IX_LightSwitch_Heizung_99', NY, 'light switch (Heizung), surface box')
    F.junction_box(k, (3.17, -1.15, UG + 1.05), NY)
    socket_outlet(k, (1.50, -1.15, UG + 1.10), NY, kind='surface')
    for x in (1.50, 3.17):
        F.conduit_run(k, [Vector((x, -1.17, UG + 1.15)), Vector((x, -1.17, UG + 2.48))])
        F.junction_box(k, (x, -1.15, UG + 2.52), NY)
        F.conduit_run(k, [Vector((x, -1.17, UG + 2.56)), Vector((x, -1.17, S.UG_C - 0.02))])
    F.conduit_run(k, [Vector((1.00, -1.18, S.UG_C - 0.05)), Vector((5.62, -1.18, S.UG_C - 0.05))])
    F.conduit_run(k, [Vector((4.46, -1.18, S.UG_C - 0.05)), Vector((4.46, -1.18, UG + 1.20)), Vector((4.46, -1.29, UG + 1.20))])
    # the shelf on the west wall, the extinguisher and its sign, the boiler's procedure board, the detector
    M1.shelving(k, -1.95, -1.43, -4.22, -2.58, 2.08, facing=PX, levels=4, zf=UG)
    extinguisher(k, (3.40, -1.15, UG + 0.55), NY)
    B(k, (5.53, -1.16, UG + 1.44), (5.71, -1.15, UG + 1.66), F.Z_WOODF)            # the procedure's board
    smoke_detector(k, (4.10, -3.20, S.UG_C))
    opening_heating()


def oil_store(k):
    """the heating-oil store: the ribbed green tank on three saddles in its galvanised bund, the level glass, the manhole
    with the suction line's fitting, fill and vent pipes up and out through the south wall, the plate"""
    for (lo_, hi_) in (((-0.72, -4.19), (2.72, -4.17)), ((-0.72, -5.65), (2.72, -5.63)),     # the bund: 2 cm walls
                       ((-0.72, -5.63), (-0.70, -4.19)), ((2.70, -5.63), (2.72, -4.19))):
        B(k, (lo_[0], lo_[1], UG), (hi_[0], hi_[1], UG + 0.32), Z_GALV, skip=('-z',))
    B(k, (-0.70, -5.63, UG), (2.70, -4.19, UG + 0.02), Z_GALV, skip=('-z',))
    for (xa, xb) in ((-0.38, -0.23), (0.93, 1.07), (2.23, 2.38)):
        B(k, (xa, -5.60, UG + 0.02), (xb, -4.30, UG + 0.10), F.Z_STEELF)
    VM.rbox(k, Vector((1.00, -4.95, UG + 0.85)), (3.20, 1.30, 1.50), F.Z_TANKG, r=0.06, ch=0.03, axis='x')
    for x in (-0.07, 0.65, 1.35, 2.05):
        VM.rbox(k, Vector((x, -4.95, UG + 0.85)), (0.06, 1.34, 1.54), F.Z_TANKG, r=0.07, ch=0.03, axis='x')
    k.cyl(Vector((0.15, -4.95, UG + 1.60)), Vector((0.15, -4.95, UG + 1.65)), 0.27, F.Z_TANKG, 18)
    for i in range(10):
        a = i * math.tau / 10
        p = Vector((0.15 + 0.24 * math.cos(a), -4.95 + 0.24 * math.sin(a), UG + 1.65))
        k.cyl(p, p + Vector((0, 0, 0.012)), 0.011, F.Z_STEELF, 6)
    B(k, (-0.38, -4.30, UG + 0.45), (-0.32, -4.29, UG + 1.45), F.Z_SCREEN)
    B(k, (-0.40, -4.30, UG + 0.43), (-0.30, -4.285, UG + 0.45), F.Z_STEELF)
    B(k, (-0.40, -4.30, UG + 1.45), (-0.30, -4.285, UG + 1.47), F.Z_STEELF)
    for xx, r, top in ((1.90, 0.035, -0.40), (2.15, 0.03, -0.40)):
        k.tube([Vector((xx, -5.40, UG + 1.60)), Vector((xx, -5.40, top)), Vector((xx, -5.65, top))], r, F.Z_STEELF, 10)
    k.cyl(Vector((2.30, -4.95, UG + 1.60)), Vector((2.30, -4.95, UG + 1.70)), 0.04, F.Z_STEELF, 10)
    k.tube([Vector((2.30, -4.95, UG + 1.70)), Vector((2.30, -4.95, UG + 2.45)), Vector((5.62, -4.95, UG + 2.45)),
            Vector((5.62, -1.22, UG + 2.45)), Vector((5.62, -1.22, UG + 1.12))], 0.008, F.Z_COPPER, 6)


def boiler(k):
    """the oil boiler (U3: x 5.75..6.75, y -2.10..-1.20, top 1.55) on its plinth: casing, the door plate with the burner
    (its reset button on top is a part of BaseMain_Opening), the control panel with the thermometer, the flue to the brick
    chimney with its draught limiter, the safety group with the manometer, the expansion vessel, the drain funnel over
    the floor gully, the blue bucket"""
    bx0, bx1, by0, by1 = 5.75, 6.75, -2.10, -1.20
    B(k, (bx0 - 0.05, by0 - 0.05, UG), (bx1 + 0.05, by1, UG + 0.10), MS.Z_FL_CONC, skip=('-z',))
    rb(k, (bx0, by0, UG + 0.10), (bx1, by1, UG + 1.55), F.Z_BOILER, r=0.02, ch=0.008)
    B(k, (5.90, by0 - 0.03, UG + 0.35), (6.60, by0, UG + 1.05), F.Z_BOILER)
    for z in (UG + 0.45, UG + 0.95):
        k.cyl(Vector((5.93, by0 - 0.03, z - 0.04)), Vector((5.93, by0 - 0.03, z + 0.04)), 0.015, F.Z_STEELF, 8)
    B(k, (5.81, by0 - 0.055, UG + 1.15), (6.69, by0, UG + 1.50), F.Z_STEELF)
    # the burner: housing with its motor and the oil pump, the blast tube into the door plate
    VM.rbox(k, Vector((6.17, -2.32, UG + 0.78)), (0.30, 0.36, 0.27), F.Z_BURNER, r=0.03, ch=0.01)
    k.cyl(Vector((6.17, -2.14, UG + 0.78)), Vector((6.17, -2.10 - 0.03, UG + 0.78)), 0.07, F.Z_STEELF, 12)
    k.cyl(Vector((6.32, -2.38, UG + 0.74)), Vector((6.44, -2.38, UG + 0.74)), 0.075, F.Z_BURNER, 12)
    VM.rbox(k, Vector((6.17, -2.47, UG + 0.70)), (0.20, 0.06, 0.10), Z_STEELBLK, r=0.01, ch=0.004)
    B(k, (6.10, -2.45, UG + 0.913), (6.24, -2.39, UG + 0.917), F.Z_STEELF)
    # the flue up and across to the chimney, the draught limiter
    k.cyl(Vector((6.30, by1 - 0.20, UG + 1.55)), Vector((6.30, by1 - 0.20, UG + 2.15)), 0.09, Z_GALV, 12)
    k.cyl(Vector((6.30, by1 - 0.20, UG + 2.15)), Vector((7.15, by1 - 0.20, UG + 2.15)), 0.09, Z_GALV, 12)
    k.lathe(Vector((6.30, by1 - 0.20, UG + 2.15)), Vector((0, 0, 1)), [(-0.09, 0.0), (-0.09, 0.093), (0.09, 0.093),
                                                                      (0.09, 0.0)], Z_GALV, 12)
    k.cyl(Vector((6.75, by1 - 0.29, UG + 2.15)), Vector((6.75, by1 - 0.40, UG + 2.15)), 0.06, Z_GALV, 10)
    k.cyl(Vector((6.75, by1 - 0.40, UG + 2.10)), Vector((6.75, by1 - 0.40, UG + 2.22)), 0.07, Z_STEELBLK, 10)
    # the safety group on the boiler: riser, valve, the manometer's case (its dial and needle are BaseMain_Opening)
    k.cyl(Vector((6.60, -1.33, UG + 1.55)), Vector((6.60, -1.33, UG + 1.70)), 0.015, F.Z_BRASS, 8)
    k.cyl(Vector((6.55, -1.33, UG + 1.70)), Vector((6.72, -1.33, UG + 1.70)), 0.018, F.Z_BRASS, 8)
    k.cyl(Vector((6.60, -1.33, UG + 1.70)), Vector((6.60, -1.33, UG + 1.78)), 0.012, F.Z_BRASS, 8)
    k.cyl(Vector((6.60, -1.33, UG + 1.78)), Vector((6.60, -1.37, UG + 1.78)), 0.012, F.Z_BRASS, 8)
    k.lathe(Vector((6.72, -1.33, UG + 1.70)), Vector((0, 0, 1)), [(0.0, 0.025), (0.08, 0.025), (0.08, 0.035), (0.10, 0.0)],
            F.Z_DRUM_R, 10)
    k.tube([Vector((6.72, -1.33, UG + 1.70)), Vector((6.90, -1.33, UG + 1.70)), Vector((6.90, -1.645, UG + 0.55))], 0.012,
           F.Z_COPPER, 6)
    # expansion vessel on its pipe, the drain funnel over the gully (Update 3: x 6.76..6.96), the bucket
    k.lathe(Vector((7.30, -1.95, UG + 0.02)), Vector((0, 0, 1)), [(0.0, 0.08), (0.06, 0.20), (0.45, 0.20), (0.55, 0.10),
                                                                  (0.58, 0.03)], F.Z_DRUM_R, 16)
    for a in (0.0, 2.094, 4.189):
        p = Vector((7.30 + 0.12 * math.cos(a), -1.95 + 0.12 * math.sin(a), UG))
        k.cyl(p, p + Vector((0, 0, 0.06)), 0.012, F.Z_STEELF, 6)
    k.tube([Vector((7.30, -1.95, UG + 0.60)), Vector((7.30, -1.95, UG + 0.95)), Vector((6.75, -1.95, UG + 0.95))], 0.012,
           F.Z_COPPER, 6)
    k.lathe(Vector((6.86, -1.645, UG + 0.30)), Vector((0, 0, 1)), [(0.0, 0.025), (0.10, 0.08), (0.17, 0.10)], Z_STEELBLK,
            12, cap0=False, cap1=False)
    k.lathe(Vector((6.86, -1.645, UG + 0.30)), Vector((0, 0, 1)), [(0.17, 0.10), (0.17, 0.097), (0.10, 0.077),
                                                                   (0.003, 0.022)], Z_STEELBLK, 12, cap0=False,
            cap1=False)                                              # its rim and the inside (facing in)
    k.cyl(Vector((6.86, -1.645, UG + 0.30)), Vector((6.86, -1.645, UG + 0.0)), 0.025, Z_STEELBLK, 8)
    B(k, (6.76, -1.70, UG + 0.15), (6.78, -1.59, UG + 0.30), Z_GALV)
    B(k, (6.88, -1.82, UG - 0.001), (7.02, -1.68, UG + 0.004), Z_GALV)
    k.lathe(Vector((7.00, -2.25, UG)), Vector((0, 0, 1)), [(0.0, 0.12), (0.26, 0.14)], F.Z_DRUM_B, 14, cap1=False)
    k.lathe(Vector((7.00, -2.25, UG + 0.01)), Vector((0, 0, 1)), [(0.25, 0.135), (0.0, 0.115)], F.Z_DRUM_B, 14,
            cap0=False, cap1=False)                                      # the inside (facing in)
    k.disc_uv(Vector((7.00, -2.25, UG + 0.011)), Vector((0, 0, 1)), 0.115, (0, 0, 0, 0), seg=14, zone=F.Z_DRUM_B)
    k.lathe(Vector((7.00, -2.25, UG + 0.26)), Vector((0, 0, 1)), [(0.0, 0.142), (0.0, 0.135)], F.Z_DRUM_B, 14,
            cap0=False, cap1=False)                                      # the rim (facing up)


def opening_heating():
    """BaseMain_Opening (the second prefab, Update 3's names, pivots, axes and ranges): the controller's front plate with
    the pump and burner rockers, the STÖRUNG lamp and the thermostat knob; the gauges' dials (the needles are parts); the
    fill tap's body with its hose by the boiler; the brackets of the entrance door's bar and the bar itself"""
    o = opening()
    part('BaseMain_Opening', 'static', (0.0, 0.0, 0.0), parent=None,
         note='second prefab (Update 3): the heating controls and the entrance door bar; light layers 5 + 7 (mask 160)')
    # the controller's front plate (the cabinet behind it is R_Heizung)
    B(o, (0.66, -1.342, UG + 1.21), (1.14, -1.338, UG + 2.69), F.Z_BOARDC)
    zt_, zb_ = UG + 2.69 - 150 / 243, UG + 2.69 - 252 / 243           # the window over the relays (drawn on the panel)
    for (xa_, xb_, za_, zc_) in ((0.686, 1.110, zb_ - 0.006, zb_), (0.686, 1.110, zt_, zt_ + 0.006),
                                 (0.686, 0.692, zb_, zt_), (1.104, 1.110, zb_, zt_)):
        B(o, (xa_, -1.346, za_), (xb_, -1.342, zc_), F.Z_STEELF)
    B(o, (0.70, -1.344, UG + 1.215), (1.10, -1.342, UG + 1.31), F.Z_STEELF)
    lamp = kb('BaseMain_Opening__fault', 'lens:heatfault')         # STÖRUNG: the game lights it (M_HeatFault -> On)
    part('BaseMain_Opening__fault', 'static', (0.96, -1.342, UG + 1.264), parent='BaseMain_Opening',
         note='the burner fault lamp (material M_HeatFault, the game swaps it to M_HeatFaultOn); joined at export')
    B(o, (0.944, -1.346, UG + 1.248), (0.976, -1.342, UG + 1.280), Z_STEELBLK)
    lamp.lathe(Vector((0.96, -1.346, UG + 1.264)), Vector((0, -1, 0)), [(0.0, 0.012), (0.006, 0.011), (0.010, 0.006),
                                                                   (0.011, 0.0)], 0, 10, cap0=False)
    for nm in ('IX_HeatPump_304', 'IX_HeatBurner_305'):
        kk = ix_part(nm, parent='BaseMain_Opening', atlas='MainOpening', note='heating: rocker switch (pump / burner), -25..25 deg')
        lo_, hi_ = lohi(nm)
        p = Vector(X.IX[nm]['pivot'])
        # the rocker on the bezel (its back two planes falling off by 26 deg: it rocks 25 deg clear of the bezel)
        F.rocker(kk, p, Vector((0, -1, 0)), Vector((1, 0, 0)), (hi_.x - lo_.x, hi_.z - lo_.z, (p.y - lo_.y) - 0.0068),
                 F.Z_ROCKER, 26.0, back=-0.0068)
        B(o, (p.x - 0.02, -1.344, p.z - 0.025), (p.x + 0.02, -1.342, p.z + 0.025), Z_STEELBLK)
    kk = ix_part('IX_HeatThermostat_306', parent='BaseMain_Opening', atlas='MainOpening', note='heating thermostat knob, 0..270 deg')
    p = Vector(X.IX['IX_HeatThermostat_306']['pivot'])
    kk.cyl(p, p - Vector((0, 0.021, 0)), 0.016, F.Z_HANDLEB, 14)
    B(kk, (p.x - 0.002, p.y - 0.022, p.z + 0.004), (p.x + 0.002, p.y - 0.021, p.z + 0.014), F.Z_DRUM_R)
    # the gauges: the manometer on the safety group, the boiler thermometer on its panel
    for nm, r, back in (('IX_HeatGauge_309', 0.050, 0.03), ('IX_HeatTempGauge_310', 0.040, 0.008)):
        kk = ix_part(nm, parent='BaseMain_Opening', atlas='MainOpening', note='gauge needle (the game sets 0..270 deg)')
        p = Vector(X.IX[nm]['pivot'])
        lo_, hi_ = lohi(nm)
        tip = Vector((lo_.x, p.y, lo_.z))
        d = (tip - p)
        ln = min(d.length, 0.86 * r)                                 # inside the bezel's lip (0.94 r) all the way round
        d = d.normalized() * ln
        Rn = Matrix((d.normalized(), Vector((0, 1, 0)), d.normalized().cross(Vector((0, 1, 0))))).transposed()
        VM.obox(kk, p + d * 0.5 + Vector((0, -0.0025, 0)), (ln, 0.002, 0.003), F.Z_DRUM_R, Rn)
        kk.cyl(p + Vector((0, -0.001, 0)), p + Vector((0, -0.004, 0)), 0.005, Z_STEELBLK, 8)
        o.lathe(p + Vector((0, 0.001, 0)), Vector((0, 1, 0)), [(-0.004, r * 0.94), (-0.004, r), (back, r), (back, 0.0)],
                F.Z_CHROME, 18, cap0=False)                          # the bezel; the dial face: main_signs (panel)
    c2 = Vector((6.15, -2.1612, UG + 1.38))                            # the boiler panel's second dial (Update 3)
    o.lathe(c2 - Vector((0, 0.0002, 0)), Vector((0, 1, 0)), [(-0.004, 0.0376), (-0.004, 0.040), (0.006, 0.040), (0.006, 0.0)],
            F.Z_CHROME, 18, cap0=False)
    # the fill tap: the valve body under its lever (the lever turns about z), the hose tail and the coiled hose
    kk = ix_part('IX_HeatFill_307', parent='BaseMain_Opening', atlas='MainOpening', note='heating fill tap lever, 0..90 deg')
    p = Vector(X.IX['IX_HeatFill_307']['pivot'])
    lo_, hi_ = lohi('IX_HeatFill_307')
    B(kk, (lo_.x, lo_.y - 0.002, lo_.z - 0.003), (hi_.x, hi_.y + 0.002, hi_.z + 0.003), F.Z_DRUM_B)
    kk.cyl(p, p - Vector((0, 0, 0.008)), 0.008, F.Z_DRUM_B, 8)
    o.cyl(p - Vector((0, 0, 0.008)), p - Vector((0, 0, 0.05)), 0.016, F.Z_BRASS, 10)
    o.cyl(p - Vector((0, -0.002, 0.03)), p - Vector((0, -0.17, 0.03)), 0.011, F.Z_BRASS, 8)
    o.tube([p - Vector((0, -0.17, 0.03)), p + Vector((0, 0.19, -0.03)), Vector((5.60, -1.17, UG + 0.80)),
            Vector((5.60, -1.17, UG + 1.12))], 0.011, F.Z_COPPER, 6)
    o.cyl(p - Vector((0, 0.002, 0.03)), p - Vector((0, 0.04, 0.03)), 0.010, F.Z_BRASS, 8)
    hose = [p - Vector((0, 0.04, 0.03))]
    for i in range(1, 9):
        t = i / 8
        hose.append(Vector((5.56 - 0.10 * math.sin(t * 4.0), -1.43 - 0.22 * t, UG + 0.50 - 0.48 * min(1.0, t * 1.6))))
    for i in range(10):
        a = i * math.tau / 10
        hose.append(Vector((5.40 + 0.16 * math.cos(a), -1.75 + 0.16 * math.sin(a), UG + 0.012 + 0.016 * (i % 2))))
    o.tube(hose, 0.010, F.Z_RUBBERB, 6, caps=True)
    # the burner's reset button on its housing (Update 3: a slide part, pressed 6 mm down); its cap is the fault light
    nm = 'IX_BurnerReset_308'
    kk = ix_part(nm, parent='BaseMain_Opening', atlas='MainOpening',
                 note='burner reset button: pressed 0..6 mm (down); its red cap lights on a burner fault (M_HeatFault)')
    p = Vector(X.IX[nm]['pivot'])
    o.lathe(p, Vector((0, 0, -1)), [(0.004, 0.0125), (-0.003, 0.0125), (-0.003, 0.016), (0.0, 0.016)], Z_STEELBLK, 12,
            cap0=False, cap1=False)                                  # the bezel ring on the housing (the button sinks in)
    kk.cyl(p + Vector((0, 0, 0.003)), p + Vector((0, 0, 0.006)), 0.0115, Z_STEELBLK, 12)
    cap = kb(nm + '__lit', 'lens:heatfault')
    part(nm + '__lit', 'static', p, parent=nm, note="the reset button's cap (material M_HeatFault); joined at export")
    cap.lathe(p + Vector((0, 0, 0.006)), Vector((0, 0, 1)), [(0.0, 0.011), (0.003, 0.0105), (0.005, 0.007), (0.006, 0.0)],
              0, 12, cap0=False)
    # the entrance door's bar in the door niche: the pivot bracket with its pin, the cradle at the east end, the bar
    nm = 'IX_MainDoorBar_311'
    kk = ix_part(nm, parent='BaseMain_Opening', atlas='MainOpening',
                 note='entrance door bar: 0 = across the door (in the cradle), 85 = raised; turns in the door niche')
    lo_, hi_ = lohi(nm)
    p = Vector(X.IX[nm]['pivot'])
    VM.rbox(kk, (lo_ + hi_) / 2, tuple(hi_ - lo_), F.Z_BAR, r=0.008, ch=0.004, axis='x')
    for x in (lo_.x + 0.30, hi_.x - 0.30):
        B(kk, (x - 0.02, lo_.y - 0.002, lo_.z - 0.002), (x + 0.02, hi_.y + 0.002, hi_.z + 0.002), F.Z_STEELF)
    yb = S.DOORS['IX_MainDoor_1']['wall'][2] - MS.niche_depth('IX_MainDoor_1')        # the niche's back face (-5.76)
    B(o, (-7.235, yb, p.z - 0.075), (-7.125, yb + 0.012, p.z + 0.075), F.Z_STEELF)       # pivot plate
    for y0_, y1_ in ((yb + 0.012, lo_.y - 0.002), (hi_.y + 0.002, hi_.y + 0.012)):
        B(o, (-7.235, y0_, p.z - 0.05), (-7.205, y1_, p.z + 0.05), F.Z_STEELF)
    o.cyl(Vector((p.x, yb + 0.012, p.z)), Vector((p.x, hi_.y + 0.016, p.z)), 0.010, F.Z_CHROME, 8)
    xe0, xe1 = hi_.x - 0.035, -5.665
    B(o, (xe0, yb, p.z - 0.11), (xe1, yb + 0.012, p.z + 0.06), F.Z_STEELF)                # cradle plate
    B(o, (xe0, yb + 0.012, lo_.z - 0.012), (xe1, hi_.y + 0.012, lo_.z - 0.002), F.Z_STEELF)  # its bottom
    B(o, (xe0, hi_.y + 0.002, lo_.z - 0.012), (xe1, hi_.y + 0.012, lo_.z + 0.045), F.Z_STEELF)  # front lip


def flur_ug():
    k = R('Flur_UG')
    # the heating mains under the ceiling along the south wall (insulated, on hangers), the cable tray beside them
    for y, z in ((-0.80, S.UG_C - 0.40), (-0.62, S.UG_C - 0.42)):
        k.cyl(Vector((-1.90, y, z)), Vector((7.60, y, z)), 0.05, F.Z_INSUL, 10)
    for i, x in enumerate((3.70, 3.88)):                             # the headers from the boiler room drop to the mains
        z0 = UG + 2.30 + i * 0.08
        ym = (-0.80, -0.62)[i]
        k.cyl(Vector((x, -1.00, z0)), Vector((x, ym, z0)), 0.045, F.Z_INSUL, 10)
        k.cyl(Vector((x, ym, z0)), Vector((x, ym, (S.UG_C - 0.40, S.UG_C - 0.42)[i])), 0.045, F.Z_INSUL, 10)
    for x in (-1.0, 1.0, 3.0, 5.0, 7.0):
        B(k, (x - 0.01, -0.90, S.UG_C - 0.48), (x + 0.01, -0.52, S.UG_C - 0.46), F.Z_STEELF)
        for y in (-0.89, -0.53):
            B(k, (x - 0.01, y - 0.01, S.UG_C - 0.46), (x + 0.01, y + 0.01, S.UG_C), F.Z_STEELF)
    B(k, (-1.74, -1.00, S.UG_C - 0.38), (4.64, -0.86, S.UG_C - 0.36), F.Z_TRAY)
    for y in (-0.97, -0.92):
        k.cyl(Vector((-1.74, y, S.UG_C - 0.345)), Vector((4.64, y, S.UG_C - 0.345)), 0.012, F.Z_CABLE, 6)
    stepladder(k, Vector((6.80, 0.60, UG)))
    alarm_bell(k, (0.60, -1.00, UG + 1.95), PY)
    call_point(k, (1.25, 1.00, UG + 1.45), NY)
    speaker(k, (5.00, 1.00, UG + 2.19), NY)
    hs = ix_part('IX_HeatingStop_131', note='emergency heating switch (Heizung NOT-AUS) by the boiler room, -10..10 deg')
    p = Vector(X.IX['IX_HeatingStop_131']['pivot'])
    B(k, (1.50, -1.00, p.z - 0.05), (1.60, -0.936, p.z + 0.05), F.Z_CALLPT)
    B(k, (1.515, -0.936, p.z - 0.035), (1.585, -0.934, p.z + 0.035), F.Z_SOCKET)
    F.rocker(hs, p, Vector((0, 1, 0)), Vector((1, 0, 0)), (0.040, 0.055, 0.018), F.Z_DRUM_R, 11.0, back=-0.0005)
    smoke_detector(k, (3.00, 0.0, S.UG_C))
    rocker_switch('IX_LightSwitch_Flur_UG_100', NY, 'light switch (corridor, basement), surface box')
    F.junction_box(k, (0.82, 1.00, UG + 1.05), NY)
    socket_outlet(k, (2.60, 1.00, UG + 1.10), NY, kind='surface')
    for x in (0.82, 2.60):
        F.conduit_run(k, [Vector((x, 0.98, UG + 1.15)), Vector((x, 0.98, UG + 2.48))])
        F.junction_box(k, (x, 1.00, UG + 2.52), NY)
        F.conduit_run(k, [Vector((x, 0.98, UG + 2.56)), Vector((x, 0.98, S.UG_C - 0.02))])


def stepladder(k, base):
    """an aluminium stepladder folded against the north wall (Update 3: x 6.56..7.04, y 0.24..0.96, 2.15 tall)"""
    for dx in (-0.22, 0.22):
        k.cyl(base + Vector((dx, -0.30, 0.0)), base + Vector((dx, 0.28, 2.15)), 0.016, F.Z_CHROME, 6)
        k.cyl(base + Vector((dx, -0.36, 0.0)), base + Vector((dx, 0.22, 2.10)), 0.014, F.Z_CHROME, 6)
    for i in range(6):
        t = (i + 1) / 7
        p = base + Vector((0, -0.30 + 0.58 * t, 2.15 * t))
        B(k, (p.x - 0.22, p.y - 0.05, p.z - 0.01), (p.x + 0.22, p.y + 0.05, p.z + 0.01), F.Z_CHROME)


def schaltraum():
    k = R('Schaltraum')
    # the main switchboard HV-UG: cream steel panels, six lever switches and the main switch (Update 3 parts); the
    # levers' pivots stand at y 5.25 .. 5.28 and they swing up to 80 / 90 deg: the panels' front at BF behind them, each
    # lever in a gate open upwards, the main switch's axle in bearings in a U-plate
    BF = 5.30
    B(k, (3.80, BF, UG + 0.40), (5.40, 5.65, UG + 2.00), F.Z_BOARDC)
    B(k, (3.78, BF - 0.02, UG + 0.38), (5.42, BF + 0.01, UG + 0.42), F.Z_STEELF)
    for xs in (4.335, 4.865):
        B(k, (xs - 0.003, BF - 0.003, UG + 0.42), (xs + 0.003, BF, UG + 2.00), Z_STEELBLK)
    for i in range(69, 75):
        nm = 'IX_Breaker_%d' % i
        kk = ix_part(nm, note='outgoing lever switch, 0..80 deg')
        lo_, hi_ = lohi(nm)
        p = Vector(X.IX[nm]['pivot'])
        kk.cyl(Vector((p.x, p.y + 0.002, p.z)), Vector((p.x, lo_.y + 0.035, p.z)), 0.010, F.Z_CHROME, 8)
        VM.rbox(kk, Vector((p.x, lo_.y + 0.02, p.z)), (hi_.x - lo_.x, 0.04, hi_.z - lo_.z), F.Z_BREAKER, r=0.01, ch=0.004,
                axis='y')
        g = 0.013                                                    # the gate: 2.6 cm wide, open above the pivot
        B(k, (p.x - 0.045, p.y, p.z - 0.07), (p.x - g, BF, p.z + 0.07), F.Z_RUBBERB)
        B(k, (p.x + g, p.y, p.z - 0.07), (p.x + 0.045, BF, p.z + 0.07), F.Z_RUBBERB)
        B(k, (p.x - g, p.y, p.z - 0.07), (p.x + g, BF, p.z - g), F.Z_RUBBERB)
    nm = 'IX_MainSwitch_75'
    kk = ix_part(nm, note='MAIN SWITCH of the building (the mains on / off), lever 0..90 deg')
    lo_, hi_ = lohi(nm)
    p = Vector(X.IX[nm]['pivot'])
    for x in (lo_.x + 0.02, hi_.x - 0.02):
        kk.cyl(Vector((x, p.y, p.z)), Vector((x, lo_.y + 0.03, p.z)), 0.012, F.Z_MAINSW, 8)
    VM.rbox(kk, Vector(((lo_.x + hi_.x) / 2, lo_.y + 0.02, p.z)), (hi_.x - lo_.x, 0.04, hi_.z - lo_.z), F.Z_MAINSW, r=0.012,
            ch=0.005, axis='x')
    kk.cyl(Vector((p.x - 0.088, p.y, p.z)), Vector((p.x + 0.088, p.y, p.z)), 0.02, Z_STEELBLK, 10)     # the axle
    yb0 = BF - 0.03
    B(k, (p.x - 0.15, yb0, p.z - 0.14), (p.x + 0.15, BF, p.z - 0.035), Z_STEELBLK)                  # the U-plate
    for sx in (-1, 1):
        B(k, (p.x + sx * 0.106, yb0, p.z - 0.035), (p.x + sx * 0.15, BF, p.z + 0.14), Z_STEELBLK)
        B(k, (p.x + sx * 0.0885, p.y - 0.022, p.z - 0.026), (p.x + sx * 0.106, BF, p.z + 0.026), Z_STEELBLK)  # bearing
    # the wall board on the east wall and the cabinet with its door (Update 3 parts)
    M1.dist_board(k, 'x', 7.65, -1, 2.80, 3.60, UG + 0.75, UG + 1.85, ['IX_Breaker_%d' % i for i in range(76, 82)],
                  'IX_Isolator_82')
    B(k, (7.42, 4.20, UG + 0.90), (7.65, 5.00, UG + 1.90), F.Z_BOARDC, skip=('-x',))
    B(k, (7.42, 4.20, UG + 0.90), (7.44, 5.00, UG + 0.92), F.Z_BOARDC)
    B(k, (7.42, 4.20, UG + 1.88), (7.44, 5.00, UG + 1.90), F.Z_BOARDC)
    B(k, (7.42, 4.20, UG + 0.92), (7.44, 4.22, UG + 1.88), F.Z_BOARDC)
    B(k, (7.42, 4.98, UG + 0.92), (7.44, 5.00, UG + 1.88), F.Z_BOARDC)
    B(k, (7.62, 4.25, UG + 1.00), (7.63, 4.95, UG + 1.80), F.Z_STEELF)               # the mounting plate inside
    for z in (UG + 1.20, UG + 1.45, UG + 1.70):
        B(k, (7.60, 4.30, z), (7.62, 4.90, z + 0.035), F.Z_RUBBERB)
        for i in range(10):
            B(k, (7.585, 4.33 + i * 0.056, z - 0.035), (7.60, 4.375 + i * 0.056, z + 0.07), F.Z_BREAKER)
    hinged_door('IX_PanelDoor_83', Vector(NX), F.Z_ENAMELW, th=0.02, handle='bar', note='distribution cabinet door')
    # the mimic board on the west wall (frame, the diagram, six indicator lamps), the cable trays, the extinguisher
    B(k, (1.95, 2.66, UG + 0.96), (1.98, 4.14, UG + 1.94), F.Z_STEELF)             # the board (its drawing: panel)
    for (y, z) in ((3.03, 1.215), (3.15, 1.395), (3.27, 1.575), (3.39, 1.215), (3.51, 1.395), (3.63, 1.575)):
        k.cyl(Vector((1.985, y, UG + z)), Vector((1.995, y, UG + z)), 0.015, Z_STEELBLK, 10)
    for (y0, y1) in ((2.05, 2.35), (4.75, 5.05)):
        B(k, (1.95, y0, UG + 2.35), (7.65, y1, UG + 2.37), F.Z_TRAY)
        for yy in (y0, y1 - 0.01):
            B(k, (1.95, yy, UG + 2.37), (7.65, yy + 0.01, UG + 2.42), F.Z_TRAY)
        for y in (y0 + 0.06, y0 + 0.13, y0 + 0.21):
            k.cyl(Vector((1.95, y, UG + 2.385)), Vector((7.65, y, UG + 2.385)), 0.014, F.Z_CABLE, 6)
    extinguisher(k, (1.95, 5.215, UG + 0.55), PX)
    rocker_switch('IX_LightSwitch_Schaltraum_101', PY, 'light switch (Schaltraum), surface box')
    F.junction_box(k, (4.77, 1.15, UG + 1.05), PY)
    socket_outlet(k, (1.95, 2.00, UG + 1.10), PX, kind='surface')
    for (c, n, up) in (((4.77, 1.15), PY, (4.77, 1.17)), ((1.95, 2.00), PX, (1.97, 2.00))):
        F.conduit_run(k, [Vector((up[0], up[1], UG + 1.15)), Vector((up[0], up[1], UG + 2.48))])
        F.junction_box(k, (c[0], c[1], UG + 2.52), n)
        F.conduit_run(k, [Vector((up[0], up[1], UG + 2.56)), Vector((up[0], up[1], S.UG_C - 0.02))])
    smoke_detector(k, (3.30, 3.40, S.UG_C))


# ================================================================ outside
def outside():
    """the entrance landing, its steps and the ramp with its railing, the canopy, bell panel and name plate; the exit
    landing with its steps at the east end; the garage apron and the side door's step; six downpipes with their scuppers;
    the heating-oil fill and vent points; the generator feed-in box; louvred air bricks; roof plant (ventilation unit,
    lattice mast, dish, vent cowls) — all at Update 3's places"""
    k = MS.ext()
    gd = S.GROUND                                                    # -0.45
    zb = S.PLINTH_BOT                                                # -0.75
    # entrance: landing (top 0.00), two steps down to the yard, the 1:13 ramp east along the facade with its railing
    B(k, (-8.00, -7.70, zb), (-4.60, -6.00, 0.0), MS.Z_PLINTH, skip=('+y',))
    for i, (y0, y1, top) in enumerate(((-7.98, -7.70, -0.15), (-8.26, -7.98, -0.30))):
        B(k, (-7.30, y0, zb), (-5.60, y1, top), MS.Z_PLINTH, skip=('+y',))
    ramp(k, -4.60, 1.40, -7.50, -6.00, 0.0, gd, zb)
    ramp_rail(k)
    canopy(k)
    B(k, (-5.79, -6.014, 1.65), (-4.51, -6.0, 1.85), F.Z_STEELF)                     # the name plate (its text: panel)
    wall_box(k, (-7.35, -6.00, 1.35), NY, 0.13, 0.22, 0.036, F.Z_STEELF)            # bell and intercom
    k.cyl(Vector((-7.35, -6.036, 1.30)), Vector((-7.35, -6.046, 1.30)), 0.016, F.Z_CHROME, 10)
    # exit landing (top 0.00) with two steps east
    B(k, (8.00, -1.20, zb), (9.80, 1.20, 0.0), MS.Z_PLINTH, skip=('-x',))
    B(k, (9.80, -1.20, zb), (10.08, 1.20, -0.15), MS.Z_PLINTH, skip=('-x',))
    B(k, (10.08, -1.20, zb), (10.36, 1.20, -0.30), MS.Z_PLINTH, skip=('-x',))
    # garage: the apron falling from the gate to the yard, the side door's step
    apron(k, -17.00, -12.70, -6.50, -5.00, S.G_F, gd, zb)
    B(k, (-11.50, -5.28, zb), (-10.15, -5.00, -0.30), MS.Z_PLINTH, skip=('+y',))
    # downpipes: main roof (scuppers through the parapet at 6.63..6.77), garage roof (3.78..3.92)
    for (x, y, out, top, scup) in ((-8.12, -5.55, NX, 6.38, 6.63), (-8.12, 5.55, NX, 6.38, 6.63),
                                   (7.82, -6.12, NY, 6.38, 6.63), (7.55, 6.12, PY, 6.38, 6.63),
                                   (-17.45, -5.12, NY, 3.53, 3.78), (-17.45, 5.12, PY, 3.53, 3.78)):
        downpipe(k, Vector((x, y, gd)), Vector(out), top, scup)
    # heating oil: the fill pipe (brass coupling, yellow cap) and the vent pipe with its cowl, out of the wall at -0.40
    for xx, r, top in ((1.90, 0.026, -0.05), (2.15, 0.022, 0.55)):
        k.tube([Vector((xx, -6.00, -0.40)), Vector((xx, -6.13, -0.40)), Vector((xx, -6.13, top))], r, Z_GALV, 10)
        for z in (-0.25, 0.20):
            if z < top - 0.05:
                B(k, (xx - 0.015, -6.12, z - 0.0125), (xx + 0.015, -6.0, z + 0.0125), Z_GALV)
    k.cyl(Vector((1.90, -6.13, -0.05)), Vector((1.90, -6.13, 0.01)), 0.042, F.Z_BRASS, 12)
    k.cyl(Vector((1.90, -6.13, 0.01)), Vector((1.90, -6.13, 0.05)), 0.046, F.Z_BAR, 12)
    k.lathe(Vector((2.15, -6.13, 0.55)), Vector((0, 0, 1)), [(0.0, 0.052), (0.05, 0.052), (0.05, 0.06), (0.08, 0.0)], Z_GALV, 12)
    # the generator feed-in by the garage door (NOTSTROM-EINSPEISUNG): steel box, the red CEE inlet with its cap, the sign
    B(k, (-8.75, -5.15, 0.82), (-8.45, -5.00, 1.18), F.Z_STEELF, skip=('+y',))
    k.cyl(Vector((-8.60, -5.15, 0.965)), Vector((-8.60, -5.231, 0.965)), 0.046, F.Z_DRUM_R, 12)
    k.cyl(Vector((-8.60, -5.207, 0.981)), Vector((-8.60, -5.238, 0.981)), 0.034, Z_STEELBLK, 10)
    # the wall lamp's bracket over the garage door (its lamp: main_fx)
    B(k, (-9.225, -5.12, 3.175), (-9.175, -5.00, 3.225), Z_GALV)
    # air bricks of the barracks and the washroom on the west facade
    for y in (-4.85, 4.85):
        B(k, (-8.006, y - 0.19, 3.75), (-8.0, y + 0.19, 4.24), Z_GALV)
        for i in range(8):
            z = 3.79 + i * 0.055
            B(k, (-8.02, y - 0.17, z), (-8.006, y + 0.17, z + 0.012), Z_GALV)
    roof_kit(k)


def ramp(k, x0, x1, y0, y1, z_hi, z_lo, zb):
    """a ramp falling from x0 (z_hi) to x1 (z_lo) on its concrete body down to zb"""
    face(k, [(x0, y0, z_hi), (x1, y0, z_lo), (x1, y1, z_lo), (x0, y1, z_hi)], MS.Z_PLINTH, (0, 0, 1))
    face(k, [(x0, y0, z_hi), (x1, y0, z_lo), (x1, y0, zb), (x0, y0, zb)], MS.Z_PLINTH, (0, -1, 0))
    face(k, [(x1, y0, z_lo), (x1, y1, z_lo), (x1, y1, zb), (x1, y0, zb)], MS.Z_PLINTH, (1, 0, 0))


def apron(k, x0, x1, y0, y1, z_hi, z_lo, zb):
    """the garage apron: top falling from z_hi at the gate (y1) to z_lo at the yard (y0)"""
    face(k, [(x0, y0, z_lo), (x1, y0, z_lo), (x1, y1, z_hi), (x0, y1, z_hi)], MS.Z_PLINTH, (0, 0, 1))
    face(k, [(x0, y0, z_lo), (x1, y0, z_lo), (x1, y0, zb), (x0, y0, zb)], MS.Z_PLINTH, (0, -1, 0))
    for x, s in ((x0, -1), (x1, 1)):
        face(k, [(x, y0, z_lo), (x, y1, z_hi), (x, y1, zb), (x, y0, zb)], MS.Z_PLINTH, (s, 0, 0))


def ramp_rail(k):
    """the ramp's railing (Update 3): square posts every 1.5 m, the black handrail 0.93 above the ramp, a mid rail"""
    y = -7.4685

    def zr(x):                                                       # the ramp surface
        return 0.0 + (x + 4.60) / 6.0 * (S.GROUND - 0.0)
    for x in (-4.60, -3.10, -1.60, -0.10, 1.40):
        B(k, (x - 0.014, y - 0.0135, zr(x)), (x + 0.014, y + 0.0135, zr(x) + 0.93), F.Z_STEELF)
    k.cyl(Vector((-4.62, y, zr(-4.60) + 0.945)), Vector((1.42, y, zr(1.40) + 0.945)), 0.024, Z_STEELBLK, 10)
    k.cyl(Vector((-4.60, y, zr(-4.60) + 0.47)), Vector((1.40, y, zr(1.40) + 0.47)), 0.011, F.Z_STEELF, 6)


def canopy(k):
    """the entrance canopy: a concrete slab with a steel fascia in the station's colour, a drip edge"""
    B(k, (-8.40, -7.90, 2.75), (-4.60, -6.00, 3.00), MS.Z_BAND, skip=('+y',))
    B(k, (-8.42, -7.92, 2.72), (-4.58, -7.90, 3.02), F.Z_FASCIA)
    B(k, (-8.42, -7.90, 2.72), (-8.40, -6.00, 3.02), F.Z_FASCIA, skip=('+y',))
    B(k, (-4.60, -7.90, 2.72), (-4.58, -6.00, 3.02), F.Z_FASCIA, skip=('+y',))


def downpipe(k, base, out, top, scup):
    """a galvanised downpipe 12 cm off the wall: the shoe turned away from the wall, brackets every 1.8 m, the hopper and
    the scupper through the parapet"""
    wall = -out
    p0 = Vector((base.x, base.y, -0.27))
    k.cyl(p0, Vector((base.x, base.y, top)), 0.05, Z_GALV, 10)
    k.tube([p0 + Vector((0, 0, 0.02)), Vector((base.x, base.y, -0.38)), Vector((base.x, base.y, -0.38)) + out * 0.10,
            Vector((base.x, base.y, -0.40)) + out * 0.19], 0.05, Z_GALV, 10)
    for z in (0.60, 2.40, 4.20, 6.00):
        if z < top - 0.1:
            c = Vector((base.x, base.y, z))
            k.cyl(c - Vector((0, 0, 0.015)), c + Vector((0, 0, 0.015)), 0.056, Z_GALV, 10)
            a = c + wall * 0.05
            b = c + wall * 0.12
            B(k, (min(a.x, b.x) - (0.02 if abs(out.y) > 0.5 else 0), min(a.y, b.y) - (0.02 if abs(out.x) > 0.5 else 0),
                  z - 0.015), (max(a.x, b.x) + (0.02 if abs(out.y) > 0.5 else 0),
                               max(a.y, b.y) + (0.02 if abs(out.x) > 0.5 else 0), z + 0.015), Z_GALV)
    k.lathe(Vector((base.x, base.y, top)), Vector((0, 0, 1)), [(0.0, 0.05), (0.14, 0.10), (0.24, 0.10)], Z_GALV, 10,
            cap1=False)
    c = Vector((base.x, base.y, scup))
    a = c + out * 0.04
    b = c + wall * 0.12
    hw = 0.10
    lo = Vector((min(a.x, b.x), min(a.y, b.y), scup))
    hi = Vector((max(a.x, b.x), max(a.y, b.y), scup + 0.14))
    if abs(out.x) > 0.5:
        lo.y, hi.y = base.y - hw, base.y + hw
    else:
        lo.x, hi.x = base.x - hw, base.x + hw
    B(k, lo, hi, Z_GALV)


def roof_kit(k):
    """roof plant at Update 3's places: the ventilation unit on its concrete base with louvres and the fan, its duct to the
    tower; the 12 m lattice mast with platform grating; the satellite dish on its post; vent cowls (main roof, garage)"""
    zr = S.ROOF
    B(k, (-6.50, -3.50, zr), (-4.00, -2.00, zr + 0.12), MS.Z_BAND, skip=('-z',))
    B(k, (-6.40, -3.40, zr + 0.12), (-4.10, -2.10, zr + 1.30), F.Z_CABGREY, skip=('-z',))
    for i in range(8):
        x = -6.25 + i * 0.28
        B(k, (x, -3.43, zr + 0.30), (x + 0.18, -3.40, zr + 1.15), Z_STEELBLK)
        for j in range(8):
            B(k, (x + 0.01, -3.432, zr + 0.34 + j * 0.10), (x + 0.17, -3.43, zr + 0.36 + j * 0.10), F.Z_STEELF)
    k.cyl(Vector((-5.25, -2.75, zr + 1.30)), Vector((-5.25, -2.75, zr + 1.36)), 0.42, Z_STEELBLK, 20)
    k.cyl(Vector((-5.25, -2.75, zr + 1.36)), Vector((-5.25, -2.75, zr + 1.37)), 0.38, F.Z_STEELF, 20)
    B(k, (-4.10, -2.95, zr + 0.40), (-0.60, -2.55, zr + 0.80), Z_GALV)
    B(k, (-0.60, -2.95, zr), (-0.20, -2.55, zr + 0.80), Z_GALV, skip=('-z',))
    # the lattice mast (three legs, cross bracing) on its concrete base by the tower, a platform with grating at 6 m
    mc = Vector((5.45, 2.95, zr))
    B(k, mc - Vector((0.60, 0.60, 0.0)), mc + Vector((0.60, 0.60, 0.12)), MS.Z_BAND, skip=('-z',))
    top = 18.50
    legs = [mc + Vector((0.45 * math.cos(a), 0.45 * math.sin(a), 0.12)) for a in (0.5236, 2.618, 4.712)]
    shrink = 0.35

    def at(i, z):
        f = 1.0 - (1.0 - shrink) * (z - zr) / (top - zr)
        p = legs[i]
        return Vector((mc.x + (p.x - mc.x) * f, mc.y + (p.y - mc.y) * f, z))
    for i in range(3):
        k.cyl(at(i, zr + 0.12), at(i, top), 0.03, Z_GALV, 6)
    nseg = 14
    for s in range(nseg):
        z0 = zr + 0.12 + s * (top - zr - 0.12) / nseg
        z1 = z0 + (top - zr - 0.12) / nseg
        for i in range(3):
            j = (i + 1) % 3
            k.cyl(at(i, z0), at(j, z1), 0.008, Z_GALV, 4)
            k.cyl(at(i, z0), at(j, z0), 0.008, Z_GALV, 4)
    zp = zr + 6.0
    c = Vector((mc.x, mc.y, zp))
    k.cyl(c, c + Vector((0, 0, 0.03)), 0.55, F.Z_GRATING, 12)
    k.cyl(c + Vector((0, 0, 0.03)), c + Vector((0, 0, 0.05)), 0.56, Z_GALV, 12, caps=False)
    for i in range(10):
        a = i * math.tau / 10
        p = c + Vector((0.55 * math.cos(a), 0.55 * math.sin(a), 0.0))
        k.cyl(p, p + Vector((0, 0, 1.0)), 0.012, Z_GALV, 4)
    k.lathe(c + Vector((0, 0, 1.0)), Vector((0, 0, 1)), [(0.0, 0.55), (0.03, 0.55)], Z_GALV, 12, cap0=False, cap1=False)
    k.cyl(Vector((mc.x + 0.10, mc.y - 0.30, zr + 0.12)), Vector((mc.x + 0.10, mc.y - 0.30, top - 0.5)), 0.012, Z_STEELBLK, 6)
    # the dish on its post (Update 3: base 2.60..3.60 / -4.60..-3.60, post to 7.70, reflector 2.56..3.55 at 7.36..8.26)
    B(k, (2.60, -4.60, zr), (3.60, -3.60, zr + 0.12), Z_GALV, skip=('-z',))
    k.cyl(Vector((3.10, -4.10, zr + 0.12)), Vector((3.10, -4.10, zr + 1.10)), 0.04, Z_GALV, 10)
    axis = Vector((-0.55, -0.40, 0.73)).normalized()
    dc = Vector((3.05, -4.18, 7.80))
    k.lathe(dc, axis, [(0.0, 0.02), (0.04, 0.20), (0.11, 0.38), (0.15, 0.49)], F.Z_DISH, 20, cap0=True, cap1=False)
    k.lathe(dc + axis * 0.003, axis, [(0.0, 0.0), (0.0, 0.47)], F.Z_DISH, 20, cap0=False, cap1=False)
    k.cyl(dc, dc + axis * 0.10, 0.03, Z_GALV, 8)
    k.cyl(dc + axis * 0.10, Vector((2.90, -4.44, 8.00)), 0.008, Z_GALV, 4)
    k.cyl(Vector((2.90, -4.44, 8.00)) - axis * 0.03, Vector((2.90, -4.44, 8.00)) + axis * 0.03, 0.03, Z_STEELBLK, 8)
    # vent cowls
    for (x, y, z) in ((-5.0, 3.20, zr), (-3.0, 4.60, zr), (4.5, -3.0, zr), (-13.5, 2.50, S.G_ROOF), (-11.0, -2.0, S.G_ROOF)):
        k.cyl(Vector((x, y, z)), Vector((x, y, z + 0.55)), 0.08, Z_GALV, 10)
        k.lathe(Vector((x, y, z + 0.55)), Vector((0, 0, 1)), [(0.0, 0.08), (0.0, 0.16), (0.05, 0.12), (0.07, 0.0)], Z_GALV, 12)
    # the cable tray from the mast and the dish to the tower
    B(k, (1.95, 2.85, zr + 0.10), (4.85, 3.05, zr + 0.14), F.Z_TRAY)
    B(k, (3.10, -3.60, zr + 0.10), (3.30, 1.0, zr + 0.14), F.Z_TRAY)


def build():
    kaserne()
    kueche()
    flur_og()
    waschraum()
    stationsleiter()
    heizung()
    flur_ug()
    schaltraum()
    outside()
