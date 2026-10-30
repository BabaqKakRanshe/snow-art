"""StartWache (forest_start_post 1.3, built with tools/snow_style 29.10): the guard house of the start post that replaces the
booth (concept_v3 arrive_wache + night_wache, QUESTIONS_3 #4 #9 accepted; user 29.10: no box, more detail, no Z door). One
root in its own frame (Blender: z up, metres; origin on the ground in the middle of the footprint; the front (the big window, to
the barrier and the road coming in) = -y, the road wall with the door = +x; Unity (x, y, z) -> (-x, z, -y), the front -> +Z).
The frame and the footprint (3.8 x 4.0) are those of the house in forest_start_post_v1 (ForestStartDress.json: u -8.5, v -3.4,
yaw 180).
  StartWache   rendered brick walls 0.25 on a concrete plinth (board formwork, 0.35 = the floor, a sloped capping), plaster
               bands round the windows; a mono-pitch roof falling 5 deg to the back: rafters with their tails out at the front
               (0.45) and the back (0.35), boards and felt, white barge boards, a white fascia with a half-round gutter and a
               downpipe at the back corner, a drip edge at the front; the stove pipe with its cap, a roof-mounted whip antenna
               for the radio (the coax down the front corner); the big front window in three lights with top lights and a
               steel counter outside under the right one (the pass-through); a small barred window in the road wall and one in
               the left wall over the bunk; the steel door frame (IX_Door: a painted steel door, a louvred vent, a kick plate,
               lever handles, three hinges; opens outward, hinge at its back edge) under a canopy on two steel brackets, the
               booth's bulkhead lamp under it (Lamp_Booth / Lens_Booth / Glow_Booth / LIGHT_Booth move here), two concrete
               steps with a pipe handrail, a field telephone box, a snow shovel; the booth's plate ZUFAHRT SPERRGEBIET
               (Booth_Sign) right of the big window; split firewood stacked under the back eaves.
               Inside: whitewash over a dark green oil-paint dado, board floor, a sloped ply ceiling; the desk under the big
               window (Slot_Table_1..3) with the log book, a mug and the radio (Audio_Radio), a chair; a bunk with a blanket
               (Spot_Bunk); a cast-iron stove on a steel plate with a kettle, the fire seen through the door slot (Glow_Stove),
               a log basket; a shelf (Slot_Shelf), a key board, a clock, the calendar, a first-aid box, a coat on a hook; the
               jerrycan's place along the road wall (Slot_Booth_Jerrycan); a caged ceiling bulkhead (Lens_Wache, lit).
Atlas Wache (1024, the shed's 51.3 px/m); the lens, the halo card and the plate: the start panel (start_tex)."""
import math
import random
import numpy as np
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, prism_x, prism_y, quad, KBS, CONTRACT
from gen_kit import Z_SLAB, Z_FLOOR, Z_TRIMW, Z_LINING, Z_TIMBER, Z_STEELBLK, Z_GALV, Z_RUSTPIPE
import start_tex as ST
import start_kit as SK

uv = ST.uv
TAU = 2 * math.pi
ROOT = 'StartWache'
BOXES = []                       # colliders: (name, parent, (x0, x1, y0, y1, z0, z1)) in the root frame

# ---------------------------------------------------------------- zones (atlas Wache)
(Z_RENDER, Z_RENDER_IN, Z_REVEAL, Z_FELT, Z_DESK, Z_BLANKET, Z_PILLOW, Z_COAT, Z_PAPER, Z_IRON, Z_RADIO, Z_BOOK, Z_CAL,
 Z_FLOORPLATE, Z_SOFFIT, Z_STEELPAINT, Z_RTRIM, Z_LOGS, Z_KETTLE, Z_CLOCK, Z_AID, Z_MUG, Z_CORR, Z_DOORSTEEL, Z_RAFTER) = range(200, 225)
WACHE_ZONES = [Z_SLAB, Z_FLOOR, Z_TRIMW, Z_LINING, Z_TIMBER, Z_STEELBLK, Z_GALV, Z_RUSTPIPE] + list(range(200, 225))
Z_WOOD_END, Z_WOOD_SPLIT, Z_WOOD_BARK = 300, 400, 500   # firewood: + the piece's index in FIREWOOD (the painter finds its pith)
FIREWOOD = []        # dict(o = the pith at the piece's back end, A = along the piece, U / V = its section's axes, R = the log's
                     # radius, sp = 0 spruce 1 pine 2 beech 3 birch, fresh = 0 weathered .. 1 fresh, kind)
PILE_TOP = None      # (xs, z): the stack's top, for the snow on it

# ---------------------------------------------------------------- the house
HX, HY, T = 1.90, 2.00, 0.25                         # outer half sizes, wall thickness
IX0, IX1, IY0, IY1 = -HX + T, HX - T, -HY + T, HY - T  # room 3.30 x 3.50
FL = 0.35                                            # floor = the plinth's top; the plinth goes 0.30 into the ground
PL0, PLO = -0.30, 0.03                               # plinth bottom, how far it stands proud of the render
PITCH = math.radians(5.0)                            # mono-pitch, high at the front
TP, CP = math.tan(PITCH), math.cos(PITCH)
ZF = 3.00                                            # rafter bottom over the front wall's outer face
RW, RD, BOARD = 0.07, 0.16, 0.024                    # rafter width / depth, roof boards
OVF, OVB, OVS = 0.45, 0.35, 0.30                     # overhangs: front, back, sides
YF, YB, XV = -HY - OVF, HY + OVB, HX + OVS           # the roof's edges
RAFTERS = [-1.80, -1.20, -0.60, 0.0, 0.60, 1.20, 1.80]
WIN_F = dict(u0=-0.95, u1=0.85, z0=1.25, z1=2.35)    # the big window in the front wall (u = x): three lights, top lights
WIN_S = dict(u0=-1.50, u1=-0.70, z0=1.35, z1=2.20)   # the small window in the road wall (u = y), barred
WIN_L = dict(u0=-0.30, u1=0.30, z0=1.80, z1=2.30)    # the small window in the left wall over the bunk (u = y), barred
FRAME_OUT, FRAME_D, FW = 0.06, 0.07, 0.06            # window frame: from the outer face in, its depth, its width
DOOR = dict(u0=0.55, u1=1.45, z0=FL, z1=FL + 2.00)   # the door's opening in the road wall (0.90 x 2.00)
DOOR_PIV = Vector((HX - 0.01, DOOR['u1'] - 0.005, FL + 1.0))   # the hinge line (outside the leaf's outer face, its back edge)
LAMP = Vector((HX, (DOOR['u0'] + DOOR['u1']) / 2, 2.52))      # the booth's bulkhead under the canopy
D_LAMP = LAMP - SK.BULK
SIGN_C = Vector((1.42, -HY - 0.014, 1.65))
D_SIGN = SIGN_C - SK.SIGN['c']
CANOPY = dict(x1=HX + 0.85, y0=0.25, y1=1.75, z_wall=2.82, z_edge=2.72)
STEPS = dict(y0=DOOR['u0'] - 0.15, y1=DOOR['u1'] + 0.15)
STOVE = dict(x0=-1.55, x1=-1.05, y0=1.15, y1=1.65, h=0.74)
PIPE = Vector((-1.30, 1.40, 0.0))                    # the stove pipe's axis (x, y): through the ceiling and the roof
PIPE_TOP = 3.95
DESK = dict(x0=-1.00, x1=0.80, y0=IY0, y1=IY0 + 0.60, z=FL + 0.74)
BUNK = dict(x0=IX0, x1=IX0 + 0.80, y0=-1.05, y1=0.95, z=FL + 0.42)
SHELF = dict(x0=-0.70, x1=0.30, y0=IY1 - 0.24, y1=IY1, z=1.55)
PILE = dict(x0=-1.60, x1=0.40, y0=HY + 0.03, y1=HY + 0.36, z0=0.10, z1=1.28)    # firewood under the back eaves
ANT = Vector((-1.62, -1.72, 0.0))                    # the antenna's foot on the roof (front left)


def z_rb(y):
    """rafter bottom line (vertical measure)"""
    return ZF - (y + HY) * TP


def z_rt(y):
    return z_rb(y) + RD / CP


def z_bt(y):                                          # the boards' top = the felt
    return z_rt(y) + BOARD / CP


def z_ci(y):                                          # the ceiling inside (ply under the rafters)
    return z_rb(y) - 0.02


def P3(axis, a, u, z):
    """wall coordinates -> the root frame: axis 'y' = a wall across y (u = x), 'x' = across x (u = y)"""
    return Vector((u, a, z)) if axis == 'y' else Vector((a, u, z))


def nrm(axis, s):
    return Vector((0, s, 0)) if axis == 'y' else Vector((s, 0, 0))


def plane(k, axis, a, n, u0, u1, zb, top, holes, zone):
    """the faces of a wall plane from zb up to top(u) (a line in u), around the rectangular holes [(u0, u1, z0, z1)]"""
    us = sorted({u0, u1} | {h[0] for h in holes if u0 < h[0] < u1} | {h[1] for h in holes if u0 < h[1] < u1})
    for ua, ub in zip(us[:-1], us[1:]):
        cu = (ua + ub) / 2
        hz = sorted({h[2] for h in holes if h[0] < cu < h[1]} | {h[3] for h in holes if h[0] < cu < h[1]})
        zs = [zb] + [z for z in hz if zb < z < min(top(ua), top(ub))] + [None]
        for j in range(len(zs) - 1):
            za, zb_ = zs[j], zs[j + 1]
            mid = (za + (zb_ if zb_ is not None else min(top(ua), top(ub)))) / 2
            if any(h[0] < cu < h[1] and h[2] < mid < h[3] for h in holes):
                continue
            if zb_ is None:
                pts = [P3(axis, a, ua, za), P3(axis, a, ub, za), P3(axis, a, ub, top(ub)), P3(axis, a, ua, top(ua))]
            else:
                pts = [P3(axis, a, ua, za), P3(axis, a, ub, za), P3(axis, a, ub, zb_), P3(axis, a, ua, zb_)]
            face(k, pts, zone, n)


def reveal(k, axis, a_out, a_in, h, sill=True, head=True, sides=True, zone=Z_REVEAL, a_from=None):
    """the opening's reveal faces through the wall (normals into the opening); a_from: start of the reveal from the outer
    face (the part between the outer face and a_from is covered by something else)"""
    u0, u1, z0, z1 = h
    a0, a1 = sorted((a_out if a_from is None else a_from, a_in))
    nu = Vector((1, 0, 0)) if axis == 'y' else Vector((0, 1, 0))
    if sides:
        face(k, [P3(axis, a0, u0, z0), P3(axis, a1, u0, z0), P3(axis, a1, u0, z1), P3(axis, a0, u0, z1)], zone, nu)
        face(k, [P3(axis, a0, u1, z0), P3(axis, a1, u1, z0), P3(axis, a1, u1, z1), P3(axis, a0, u1, z1)], zone, -nu)
    if head:
        face(k, [P3(axis, a0, u0, z1), P3(axis, a1, u0, z1), P3(axis, a1, u1, z1), P3(axis, a0, u1, z1)], zone, Vector((0, 0, -1)))
    if sill:
        face(k, [P3(axis, a0, u0, z0), P3(axis, a1, u0, z0), P3(axis, a1, u1, z0), P3(axis, a0, u1, z0)], zone, Vector((0, 0, 1)))


def wbox(k, axis, ua, ub, aa, ab, za, zb, zone, skip=()):
    """box in wall coordinates (u along the wall, a across it); skip in wall terms: '-u', '+u', '-a', '+a', '-z', '+z'"""
    m = {'u': 'x' if axis == 'y' else 'y', 'a': 'y' if axis == 'y' else 'x', 'z': 'z'}
    lo, hi = P3(axis, min(aa, ab), min(ua, ub), min(za, zb)), P3(axis, max(aa, ab), max(ua, ub), max(za, zb))
    box6(k, tuple(lo), tuple(hi), zone, skip=tuple(s[0] + m[s[1]] for s in skip))


def window(k, g, axis, out_sign, h, mullions, transom=None, bars=False, counter=None):
    """a white frame 7 cm deep 6 cm in from the outer face, mullions at `mullions` (u), a transom at z `transom`, the panes to g
    (two faces back to back), a galvanised sill outside (or the steel counter under the lights of `counter` (u0, u1)), a spruce
    sill inside, the render reveals, a plaster band round it on the facade; bars in the reveal outside the frame"""
    u0, u1, z0, z1 = h
    a_out = HY * out_sign if axis == 'y' else HX * out_sign
    a_in = a_out - out_sign * T
    f_out, f_in = a_out - out_sign * FRAME_OUT, a_out - out_sign * (FRAME_OUT + FRAME_D)
    fa, fb = sorted((f_out, f_in))
    reveal(k, axis, a_out, a_in, h, sill=False)
    wbox(k, axis, u0, u1, fa, fb, z0, z0 + FW, Z_TRIMW, skip=('-z', '-u', '+u'))
    wbox(k, axis, u0, u1, fa, fb, z1 - FW, z1, Z_TRIMW, skip=('+z', '-u', '+u'))
    wbox(k, axis, u0, u0 + FW, fa, fb, z0 + FW, z1 - FW, Z_TRIMW, skip=('-u', '-z', '+z'))
    wbox(k, axis, u1 - FW, u1, fa, fb, z0 + FW, z1 - FW, Z_TRIMW, skip=('+u', '-z', '+z'))
    bm = 0.024
    am0, am1 = sorted((f_out - out_sign * 0.01, f_in + out_sign * 0.01))
    cols = [u0 + FW] + [x for m in mullions for x in (m - 0.03, m + 0.03)] + [u1 - FW]
    for m in mullions:
        wbox(k, axis, m - 0.03, m + 0.03, am0, am1, z0 + FW, z1 - FW, Z_TRIMW, skip=('-z', '+z'))
    rows = [(z0 + FW, z1 - FW)]
    if transom is not None:
        for ca, cb in zip(cols[0::2], cols[1::2]):
            wbox(k, axis, ca, cb, am0, am1, transom - bm, transom + bm, Z_TRIMW, skip=('-u', '+u'))
        rows = [(z0 + FW, transom - bm), (transom + bm, z1 - FW)]
    ag = (f_out + f_in) / 2
    n = nrm(axis, 1)
    for ca, cb in zip(cols[0::2], cols[1::2]):
        for qa, qb in rows:
            for d, s in ((-0.0005, -1), (0.0005, 1)):
                face(g, [P3(axis, ag + d, ca, qa), P3(axis, ag + d, cb, qa), P3(axis, ag + d, cb, qb), P3(axis, ag + d, ca, qb)], 0.0, n * s)
    # sills: galvanised outside (4 cm proud, into the side reveals), spruce inside; the steel counter of the pass-through
    so0, so1 = sorted((a_out + out_sign * 0.045, f_out))
    if counter is None:
        wbox(k, axis, u0 - 0.025, u1 + 0.025, so0, so1, z0 - 0.022, z0, Z_GALV)
        wbox(k, axis, u0 - 0.025, u1 + 0.025, a_out + out_sign * 0.035, a_out + out_sign * 0.045, z0 - 0.06, z0 - 0.022, Z_GALV)
    else:
        ca, cb = counter
        wbox(k, axis, u0 - 0.025, ca, so0, so1, z0 - 0.022, z0, Z_GALV)
        wbox(k, axis, u0 - 0.025, ca, a_out + out_sign * 0.035, a_out + out_sign * 0.045, z0 - 0.06, z0 - 0.022, Z_GALV)
        c0, c1 = sorted((a_out + out_sign * 0.34, f_out))
        wbox(k, axis, ca, u1 + 0.025, c0, c1, z0 - 0.012, z0, Z_GALV)                                  # the counter plate
        wbox(k, axis, ca, u1 + 0.025, a_out + out_sign * 0.33, a_out + out_sign * 0.34, z0 - 0.045, z0 - 0.012, Z_GALV)
        for ub in (ca + 0.07, u1 - 0.05):                                                              # its brackets
            pa = P3(axis, a_out, ub, z0 - 0.33)
            pb = P3(axis, a_out + out_sign * 0.30, ub, z0 - 0.015)
            k.strip([pa, pb], Vector((0, 0, 1)) if axis == 'x' else Vector((0, 0, 1)), 0.012, 0.03, Z_STEELPAINT)
            wbox(k, axis, ub - 0.02, ub + 0.02, a_out, a_out + out_sign * 0.006, z0 - 0.36, z0 - 0.30, Z_STEELPAINT, skip=('-a' if out_sign > 0 else '+a',))
    si0, si1 = sorted((f_in, a_in - out_sign * 0.035))
    wbox(k, axis, u0 - 0.03, u1 + 0.03, si0, si1, z0 - 0.028, z0, Z_TIMBER)
    # the plaster band round the window on the facade (2 cm proud, 10 cm wide): sides and head
    b0, b1 = sorted((a_out, a_out + out_sign * 0.02))
    into = '-a' if out_sign > 0 else '+a'
    wbox(k, axis, u0 - 0.10, u0, b0, b1, z0 - 0.06, z1 + 0.10, Z_RTRIM, skip=(into,))
    wbox(k, axis, u1, u1 + 0.10, b0, b1, z0 - 0.06, z1 + 0.10, Z_RTRIM, skip=(into,))
    wbox(k, axis, u0, u1, b0, b1, z1, z1 + 0.10, Z_RTRIM, skip=(into, '-u', '+u'))
    if bars:
        ab = a_out - out_sign * 0.03
        nb = max(2, int(round((u1 - u0) / 0.12)))
        for i in range(1, nb):
            ub = u0 + (u1 - u0) * i / nb
            k.cyl(P3(axis, ab, ub, z0 - 0.01), P3(axis, ab, ub, z1 + 0.01), 0.008, Z_STEELBLK, 6)
        for zb_ in (z0 + 0.12, z1 - 0.12):
            wbox(k, axis, u0 - 0.01, u1 + 0.01, ab - 0.004, ab + 0.004, zb_ - 0.02, zb_ + 0.02, Z_STEELBLK)


# ================================================================ the shell
def house():
    k = kb(ROOT, 'Wache')
    g = kb('Booth_Glass', 'glass')
    # ---- plinth: board-formwork concrete, 3 cm proud of the render, 0.30 in the ground, a sloped capping to the render
    box6(k, (-HX - PLO, -HY - PLO, PL0), (HX + PLO, HY + PLO, FL - 0.02), Z_SLAB, skip=('-z', '+z'))
    O = [Vector((-HX - PLO, -HY - PLO, FL - 0.02)), Vector((HX + PLO, -HY - PLO, FL - 0.02)), Vector((HX + PLO, HY + PLO, FL - 0.02)),
         Vector((-HX - PLO, HY + PLO, FL - 0.02))]
    I = [Vector((-HX, -HY, FL + 0.03)), Vector((HX, -HY, FL + 0.03)), Vector((HX, HY, FL + 0.03)), Vector((-HX, HY, FL + 0.03))]
    for i, n in enumerate(((0, -1, 1.5), (1, 0, 1.5), (0, 1, 1.5), (-1, 0, 1.5))):
        face(k, [O[i], O[(i + 1) % 4], I[(i + 1) % 4], I[i]], Z_SLAB, n)
    # ---- floor boards, the threshold
    for xa, xb in ((IX0, 0.0), (0.0, IX1)):
        for ya, yb in ((IY0, 0.0), (0.0, IY1)):
            face(k, [(xa, ya, FL), (xb, ya, FL), (xb, yb, FL), (xa, yb, FL)], Z_FLOOR, (0, 0, 1))
    face(k, [(IX1, DOOR['u0'], FL), (HX - 0.08, DOOR['u0'], FL), (HX - 0.08, DOOR['u1'], FL), (IX1, DOOR['u1'], FL)], Z_TIMBER, (0, 0, 1))
    face(k, [(HX - 0.08, DOOR['u0'], FL), (HX, DOOR['u0'], FL), (HX, DOOR['u1'], FL), (HX - 0.08, DOOR['u1'], FL)], Z_STEELPAINT, (0, 0, 1))
    # ---- walls: the render outside up to the roof boards (the rafter tails pass through), whitewash inside up to the ceiling
    hf = (WIN_F['u0'], WIN_F['u1'], WIN_F['z0'], WIN_F['z1'])
    hs = (WIN_S['u0'], WIN_S['u1'], WIN_S['z0'], WIN_S['z1'])
    hl = (WIN_L['u0'], WIN_L['u1'], WIN_L['z0'], WIN_L['z1'])
    hd = (DOOR['u0'], DOOR['u1'], DOOR['z0'], DOOR['z1'])
    zfo, zbo = z_rt(-HY), z_rt(HY)
    plane(k, 'y', -HY, Vector((0, -1, 0)), -HX, HX, FL + 0.03, lambda u: zfo, [hf], Z_RENDER)
    plane(k, 'y', HY, Vector((0, 1, 0)), -HX, HX, FL + 0.03, lambda u: zbo, [], Z_RENDER)
    plane(k, 'x', -HX, Vector((-1, 0, 0)), -HY, HY, FL + 0.03, z_rt, [hl], Z_RENDER)
    plane(k, 'x', HX, Vector((1, 0, 0)), -HY, HY, FL + 0.03, z_rt, [hs, hd], Z_RENDER)
    plane(k, 'y', IY0, Vector((0, 1, 0)), IX0, IX1, FL, lambda u: z_ci(IY0), [hf], Z_RENDER_IN)
    plane(k, 'y', IY1, Vector((0, -1, 0)), IX0, IX1, FL, lambda u: z_ci(IY1), [], Z_RENDER_IN)
    plane(k, 'x', IX0, Vector((1, 0, 0)), IY0, IY1, FL, z_ci, [hl], Z_RENDER_IN)
    plane(k, 'x', IX1, Vector((-1, 0, 0)), IY0, IY1, FL, z_ci, [hs, hd], Z_RENDER_IN)
    window(k, g, 'y', -1, hf, [-0.35, 0.25], transom=2.03, counter=(0.25, 0.85))
    window(k, g, 'x', 1, hs, [(WIN_S['u0'] + WIN_S['u1']) / 2], transom=(WIN_S['z0'] + WIN_S['z1']) / 2 + 0.06, bars=True)
    window(k, g, 'x', -1, hl, [], transom=None, bars=True)
    door_frame(k)
    # ---- the booth's plate on a galvanised backing (Booth_Sign moves onto it)
    s = SK.SIGN
    k.box(SIGN_C.x - s['w'] / 2 - 0.012, SIGN_C.x + s['w'] / 2 + 0.012, -HY - 0.012, -HY, SIGN_C.z - s['h'] / 2 - 0.012,
          SIGN_C.z + s['h'] / 2 + 0.012, Z_GALV)
    roof(k)
    canopy(k)
    outside(k)
    woodpile(k)
    interior(k)
    part('Booth_Glass', 'static', ((WIN_F['u0'] + WIN_F['u1']) / 2, -HY + FRAME_OUT + FRAME_D / 2, (WIN_F['z0'] + WIN_F['z1']) / 2),
         parent=ROOT, note='the panes of the three windows (the booth\'s glass object takes this mesh; M_Start_Glass)')
    part(ROOT, 'static', (0, 0, 0), note='the guard house (root): origin = the middle of the footprint on the ground; floor 0.35 '
                                         '(the plinth\'s top), the plinth 0.30 into the ground')
    BOXES.extend([
        ('Wache_Plinth', ROOT, (-HX - PLO, HX + PLO, -HY - PLO, HY + PLO, PL0, FL)),
        ('Wache_Front', ROOT, (-HX, HX, -HY, IY0, FL, zfo)),
        ('Wache_Back', ROOT, (-HX, HX, IY1, HY, FL, zbo)),
        ('Wache_Left', ROOT, (-HX, IX0, IY0, IY1, FL, zfo)),
        ('Wache_Road_F', ROOT, (IX1, HX, IY0, DOOR['u0'], FL, zfo)),
        ('Wache_Road_B', ROOT, (IX1, HX, DOOR['u1'], IY1, FL, zfo)),
        ('Wache_Road_Top', ROOT, (IX1, HX, DOOR['u0'], DOOR['u1'], DOOR['z1'], zfo)),
        ('Wache_Roof', ROOT, (-XV - 0.03, XV + 0.03, YF, YB, z_rb(YB), z_bt(YF) + 0.02))])


def door_frame(k):
    """the steel frame (Zarge) of the door: a flange round the opening on the facade, the lining of the reveal's outer 8 cm,
    the stop the leaf closes against; render reveal behind it; the spruce casing inside"""
    u0, u1, z0, z1 = DOOR['u0'], DOOR['u1'], DOOR['z0'], DOOR['z1']
    lin = 0.08
    reveal(k, 'x', HX, IX1, (u0, u1, z0, z1), sill=False, a_from=HX - lin)
    for (ua, ub) in ((u0 - 0.05, u0), (u1, u1 + 0.05)):                                               # flanges on the facade
        box6(k, (HX, ua, z0), (HX + 0.008, ub, z1 + 0.05), Z_STEELPAINT, skip=('-x', '-z'))
    box6(k, (HX, u0, z1), (HX + 0.008, u1, z1 + 0.05), Z_STEELPAINT, skip=('-x', '-y', '+y'))
    face(k, [(HX, u0, z0), (HX - lin, u0, z0), (HX - lin, u0, z1), (HX, u0, z1)], Z_STEELPAINT, (0, 1, 0))      # the lining
    face(k, [(HX, u1, z0), (HX - lin, u1, z0), (HX - lin, u1, z1), (HX, u1, z1)], Z_STEELPAINT, (0, -1, 0))
    face(k, [(HX, u0, z1), (HX - lin, u0, z1), (HX - lin, u1, z1), (HX, u1, z1)], Z_STEELPAINT, (0, 0, -1))
    st = 0.018                                                                                        # the stop strip
    box6(k, (HX - 0.085, u0, z0), (HX - 0.07, u0 + st, z1), Z_STEELPAINT, skip=('-y', '-z', '+z'))
    box6(k, (HX - 0.085, u1 - st, z0), (HX - 0.07, u1, z1), Z_STEELPAINT, skip=('+y', '-z', '+z'))
    box6(k, (HX - 0.085, u0 + st, z1 - st), (HX - 0.07, u1 - st, z1), Z_STEELPAINT, skip=('+z', '-y', '+y'))
    for (ua, ub, za, zb) in ((u0 - 0.07, u0, FL, z1 + 0.07), (u1, u1 + 0.07, FL, z1 + 0.07), (u0, u1, z1, z1 + 0.07)):
        wbox(k, 'x', ua, ub, IX1 - 0.02, IX1, za, zb, Z_TIMBER, skip=('+a', '-z'))
    for zh in (FL + 0.25, FL + 1.0, FL + 1.75):                                                       # the hinges' frame halves
        k.cyl(Vector((DOOR_PIV.x, DOOR_PIV.y, zh - 0.06)), Vector((DOOR_PIV.x, DOOR_PIV.y, zh)), 0.011, Z_STEELPAINT, 8)
        k.box(HX + 0.008, HX + 0.013, DOOR_PIV.y + 0.005, DOOR_PIV.y + 0.045, zh - 0.06, zh, Z_STEELPAINT)


def door():
    """IX_Door: a painted steel door 0.89 x 1.99, 5 cm, in the frame 2 cm in from the facade; opens outward (+) about its back
    (+y) edge; a louvred vent low down, a kick plate, lever handles both sides, the lock's cylinder, three hinge knuckles"""
    D = kb('IX_Door', 'Wache')
    u0, u1, z0, z1 = DOOR['u0'] + 0.006, DOOR['u1'] - 0.006, DOOR['z0'] + 0.008, DOOR['z1'] - 0.006
    x0, x1 = HX - 0.07, HX - 0.02
    box6(D, (x0, u0, z0), (x1, u1, z1), Z_DOORSTEEL)
    # the leaf's outer panel: a raised border (pressed steel), the vent, the kick plate
    box6(D, (x1, u0 + 0.05, z0 + 0.05), (x1 + 0.004, u1 - 0.05, z1 - 0.05), Z_DOORSTEEL, skip=('-x',))
    vz0, vz1, vy0, vy1 = z0 + 0.18, z0 + 0.46, u0 + 0.20, u1 - 0.20
    box6(D, (x1 + 0.004, vy0, vz0), (x1 + 0.016, vy1, vz0 + 0.02), Z_DOORSTEEL, skip=('-x',))
    box6(D, (x1 + 0.004, vy0, vz1 - 0.02), (x1 + 0.016, vy1, vz1), Z_DOORSTEEL, skip=('-x',))
    box6(D, (x1 + 0.004, vy0, vz0 + 0.02), (x1 + 0.016, vy0 + 0.02, vz1 - 0.02), Z_DOORSTEEL, skip=('-x', '-z', '+z'))
    box6(D, (x1 + 0.004, vy1 - 0.02, vz0 + 0.02), (x1 + 0.016, vy1, vz1 - 0.02), Z_DOORSTEEL, skip=('-x', '-z', '+z'))
    face(D, [(x1 + 0.006, vy0 + 0.02, vz0 + 0.02), (x1 + 0.006, vy1 - 0.02, vz0 + 0.02), (x1 + 0.006, vy1 - 0.02, vz1 - 0.02),
             (x1 + 0.006, vy0 + 0.02, vz1 - 0.02)], Z_STEELBLK, (1, 0, 0))
    for i in range(6):                                                                                 # the louvre slats
        zc = vz0 + 0.04 + i * 0.04
        R = Matrix.Rotation(math.radians(-35), 3, 'Y')
        D.box_m(Vector((x1 + 0.010, (vy0 + vy1) / 2, zc)), (0.004, vy1 - vy0 - 0.04, 0.035), Z_DOORSTEEL, R)
    box6(D, (x1, u0 + 0.056, z0 + 0.01), (x1 + 0.007, u1 - 0.056, z0 + 0.16), Z_GALV, skip=('-x',))    # kick plate
    hz = FL + 1.05
    hy = u0 + 0.07
    for xx, s in ((x1 + 0.004, 1), (x0, -1)):                                                          # escutcheons, levers
        D.box(*sorted((xx, xx + s * 0.008)), hy - 0.022, hy + 0.022, hz - 0.15, hz + 0.05, Z_STEELBLK)
        D.cyl(Vector((xx + s * 0.008, hy, hz)), Vector((xx + s * 0.055, hy, hz)), 0.010, Z_STEELBLK, 8)
        D.cyl(Vector((xx + s * 0.055, hy - 0.005, hz)), Vector((xx + s * 0.055, hy + 0.12, hz)), 0.011, Z_STEELBLK, 8)
        D.cyl(Vector((xx + s * 0.008, hy, hz - 0.10)), Vector((xx + s * 0.016, hy, hz - 0.10)), 0.014, Z_GALV, 8)      # the cylinder
    for zh in (FL + 0.25, FL + 1.0, FL + 1.75):                                                         # knuckles on the leaf
        D.cyl(Vector((DOOR_PIV.x, DOOR_PIV.y, zh)), Vector((DOOR_PIV.x, DOOR_PIV.y, zh + 0.07)), 0.011, Z_STEELPAINT, 8)
        D.box(x1 - 0.004, x1 + 0.004, DOOR_PIV.y - 0.05, DOOR_PIV.y - 0.008, zh, zh + 0.07, Z_STEELPAINT)
    part('IX_Door', 'hinge', DOOR_PIV, (0, 0, 1), (0, 100), parent=ROOT, states=['shut', 'open'],
         note='the guard house\'s steel door in the road wall, hinged at its back (+y) edge, opens outward (+) to 100 deg; lever '
              'handles both sides (the booth\'s IX_Door object takes this mesh and stands open 80 deg as the booth\'s did)')
    socket('Hand_Door_Out', (x1 + 0.07, hy + 0.08, hz), 'hand', parent='IX_Door', note='lever outside')
    socket('Hand_Door_In', (x0 - 0.07, hy + 0.08, hz), 'hand', parent='IX_Door', note='lever inside')


def roof(k):
    """rafter tails out at the front and the back, the verge rafters, boards with felt, white barge boards and the back fascia,
    the drip edge at the front, the gutter on hooks and the downpipe, the stove pipe, the radio antenna"""
    for xr in RAFTERS:
        for (ya, yb) in ((YF, -HY + 0.01), (HY - 0.01, YB)):
            poly = [(ya, z_rb(ya)), (yb, z_rb(yb)), (yb, z_rt(yb)), (ya, z_rt(ya))]
            ends = [Z_RAFTER, None, None, Z_RAFTER if ya == YF else None]
            prism_x(k, poly, xr - RW / 2, xr + RW / 2, Z_RAFTER, Z_RAFTER, ends)
    for sx in (-1, 1):                                                                                # the verge rafters
        xr = sx * (XV - RW / 2)
        poly = [(YF, z_rb(YF)), (YB, z_rb(YB)), (YB, z_rt(YB)), (YF, z_rt(YF))]
        prism_x(k, poly, xr - RW / 2, xr + RW / 2, Z_RAFTER if sx > 0 else None, None if sx > 0 else Z_RAFTER,
                [Z_RAFTER, Z_RAFTER, None, Z_RAFTER])
    # the boards' underside where it shows (the overhangs), the boards' front edge, the felt
    for (xa, xb, ya, yb) in ((-XV, XV, YF, -HY), (-XV, XV, HY, YB), (-XV, -HX, -HY, HY), (HX, XV, -HY, HY)):
        face(k, [(xa, ya, z_rt(ya)), (xb, ya, z_rt(ya)), (xb, yb, z_rt(yb)), (xa, yb, z_rt(yb))], Z_SOFFIT, (0, -TP, -1))
    face(k, [(-XV, YF, z_bt(YF) + 0.004), (XV, YF, z_bt(YF) + 0.004), (XV, YB, z_bt(YB) + 0.004), (-XV, YB, z_bt(YB) + 0.004)], Z_FELT,
         (0, TP, 1))
    # the drip edge at the front: a flange on the felt and a nose over the boards' edge
    box6(k, (-XV - 0.02, YF - 0.012, z_rt(YF) - 0.035), (XV + 0.02, YF, z_bt(YF) + 0.012), Z_GALV, skip=('+y',))
    # white barge boards on the verges, the white fascia at the back (the gutter on it)
    for sx in (-1, 1):
        xa, xb = sorted((sx * XV, sx * (XV + 0.022)))
        poly = [(YF - 0.014, z_rb(YF - 0.014) - 0.01), (YB + 0.022, z_rb(YB + 0.022) - 0.01), (YB + 0.022, z_bt(YB + 0.022) + 0.03),
                (YF - 0.014, z_bt(YF - 0.014) + 0.03)]
        prism_x(k, poly, xa, xb, Z_TRIMW, Z_TRIMW)
    poly = [(YB, z_rb(YB) - 0.02), (YB + 0.022, z_rb(YB + 0.022) - 0.02), (YB + 0.022, z_bt(YB + 0.022) + 0.01), (YB, z_bt(YB) + 0.01)]
    prism_x(k, poly, -XV, XV, None, None, [Z_TRIMW, Z_TRIMW, Z_TRIMW, None])
    # the gutter: half round 0.12 on five hooks, end caps, the outlet over the downpipe
    gr = 0.06
    gy, gz = YB + 0.022 + gr + 0.005, z_bt(YB) - 0.04
    seg = 8
    arc = [(gy + gr * math.cos(math.pi + math.pi * i / seg), gz + gr * math.sin(math.pi + math.pi * i / seg)) for i in range(seg + 1)]
    for i in range(seg):
        (ya, za), (yb, zb) = arc[i], arc[i + 1]
        face(k, [(-XV, ya, za), (XV, ya, za), (XV, yb, zb), (-XV, yb, zb)], Z_GALV, (0, ((ya + yb) / 2 - gy), ((za + zb) / 2 - gz)))
        face(k, [(-XV, ya, za + 0.003), (XV, ya, za + 0.003), (XV, yb, zb + 0.003), (-XV, yb, zb + 0.003)], Z_GALV,
             (0, -((ya + yb) / 2 - gy), -((za + zb) / 2 - gz)))
    k.cyl(Vector((-XV + 0.002, gy + gr, gz)), Vector((XV - 0.002, gy + gr, gz)), 0.008, Z_GALV, 6, caps=False)   # the rolled bead
    for sx in (-1, 1):
        pts = [Vector((sx * XV, y, z)) for (y, z) in arc]
        face(k, pts, Z_GALV, (sx, 0, 0))
    for xh in (-1.9, -0.95, 0.0, 0.95, 1.9):
        k.strip([Vector((xh, YB + 0.022, gz + 0.03)), Vector((xh, gy, gz - gr - 0.006)), Vector((xh, gy + gr + 0.006, gz + 0.01))],
                Vector((1, 0, 0)), 0.025, 0.004, Z_GALV)
    # the downpipe at the back right corner: outlet, swan neck to the wall, down to a shoe over the ground
    dx = 1.72
    dp = [Vector((dx, gy, gz - gr)), Vector((dx, gy, gz - gr - 0.10)), Vector((dx, HY + 0.12, gz - gr - 0.30)),
          Vector((dx, HY + 0.07, gz - gr - 0.42)), Vector((dx, HY + 0.07, 0.30)), Vector((dx, HY + 0.12, 0.16)), Vector((dx, HY + 0.30, 0.10))]
    k.tube(dp, 0.040, Z_GALV, 10, caps=True)
    for zc in (0.8, 1.6, 2.3):
        k.box(dx - 0.05, dx + 0.05, HY, HY + 0.035, zc - 0.015, zc + 0.015, Z_GALV)
        k.cyl(Vector((dx, HY + 0.07, zc - 0.02)), Vector((dx, HY + 0.07, zc + 0.02)), 0.046, Z_GALV, 10)
    # the stove pipe: collar on the felt, the pipe, the rain cap on three legs
    p = PIPE
    zr = z_bt(p.y) + 0.004
    k.cyl(Vector((p.x, p.y, zr)), Vector((p.x, p.y, zr + 0.10)), 0.13, Z_GALV, 12, r2=0.075)
    k.cyl(Vector((p.x, p.y, zr + 0.10)), Vector((p.x, p.y, PIPE_TOP)), 0.065, Z_RUSTPIPE, 10, caps=False)
    k.lathe(Vector((p.x, p.y, PIPE_TOP + 0.10)), (0, 0, 1), [(0.0, 0.17), (0.07, 0.02)], Z_RUSTPIPE, 10, cap0=True, cap1=False)
    for a in (0, 120, 240):
        dv = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        k.box_m(Vector((p.x, p.y, PIPE_TOP + 0.05)) + dv * 0.068, (0.012, 0.012, 0.10), Z_RUSTPIPE)
    for a in (45, 225):                                                                              # two stay wires
        dv = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        top = Vector((p.x, p.y, PIPE_TOP - 0.25)) + dv * 0.065
        foot = Vector((p.x, p.y, 0)) + dv * 0.75
        foot.z = z_bt(foot.y) + 0.01
        k.cyl(top, foot, 0.004, Z_STEELBLK, 4)
        k.box(foot.x - 0.03, foot.x + 0.03, foot.y - 0.03, foot.y + 0.03, foot.z - 0.005, foot.z + 0.01, Z_GALV)
    # the radio antenna on the roof (front left): base plate, mast, the loading coil, the whip; the coax down the front corner
    a0 = Vector((ANT.x, ANT.y, z_bt(ANT.y) + 0.004))
    k.box(a0.x - 0.10, a0.x + 0.10, a0.y - 0.10, a0.y + 0.10, a0.z, a0.z + 0.008, Z_GALV)
    k.cyl(a0 + Vector((0, 0, 0.008)), a0 + Vector((0, 0, 0.75)), 0.022, Z_GALV, 8)
    k.cyl(a0 + Vector((0, 0, 0.75)), a0 + Vector((0, 0, 0.85)), 0.030, Z_STEELBLK, 8)
    k.cyl(a0 + Vector((0, 0, 0.85)), a0 + Vector((0, 0, 2.30)), 0.005, Z_STEELBLK, 4, r2=0.003)
    for a in (0, 120, 240):                                                                          # stays to the plate's corners
        dv = Vector((math.cos(math.radians(a + 30)), math.sin(math.radians(a + 30)), 0))
        k.cyl(a0 + Vector((0, 0, 0.45)), a0 + dv * 0.13 + Vector((0, 0, 0.01)), 0.003, Z_GALV, 4)
    k.tube([a0 + Vector((0.03, 0, 0.10)), Vector((ANT.x, YF + 0.10, z_bt(YF + 0.10) + 0.03)), Vector((ANT.x, YF - 0.035, z_bt(YF) - 0.02)),
            Vector((ANT.x, YF - 0.035, 2.70)), Vector((ANT.x, -HY - 0.025, 2.70)), Vector((ANT.x, -HY - 0.025, 1.75)),
            Vector((-1.20, -HY - 0.025, 1.75)), Vector((-1.20, -HY + 0.02, 1.75))], 0.0045, Z_STEELBLK, 5)


def canopy(k):
    """the canopy over the door: two steel brackets (arm and strut), a timber frame, a corrugated sheet sloping out, a white
    fascia, the flashing to the wall; the booth's bulkhead hangs under it"""
    c = CANOPY
    x0, x1, y0, y1 = HX, c['x1'], c['y0'], c['y1']
    zt = lambda x: c['z_wall'] + (c['z_edge'] - c['z_wall']) * (x - x0) / (x1 - x0)
    for ys in (y0 + 0.02, y1 - 0.06):                                                                # the side bearers
        poly = [(x0, zt(x0) - 0.13), (x1 - 0.02, zt(x1 - 0.02) - 0.13), (x1 - 0.02, zt(x1 - 0.02) - 0.02), (x0, zt(x0) - 0.02)]
        prism_y(k, [(a, b) for a, b in poly], ys, ys + 0.04, Z_TIMBER, Z_TIMBER, [Z_TIMBER, Z_TIMBER, None, None])
    face(k, [(x0, y0, zt(x0) - 0.02), (x1, y0, zt(x1) - 0.02), (x1, y1, zt(x1) - 0.02), (x0, y1, zt(x0) - 0.02)], Z_SOFFIT,
         (-0.1, 0, -1))
    face(k, [(x0, y0, zt(x0) + 0.004), (x1, y0, zt(x1) + 0.004), (x1, y1, zt(x1) + 0.004), (x0, y1, zt(x0) + 0.004)], Z_CORR,
         (0.1, 0, 1))
    for ys, sg in ((y0, -1), (y1, 1)):                                                               # the sheet's side edges
        face(k, [(x0, ys, zt(x0) - 0.02), (x1, ys, zt(x1) - 0.02), (x1, ys, zt(x1) + 0.004), (x0, ys, zt(x0) + 0.004)], Z_TIMBER, (0, sg, 0))
    box6(k, (x1, y0 - 0.01, zt(x1) - 0.14), (x1 + 0.022, y1 + 0.01, zt(x1) + 0.02), Z_TRIMW)         # fascia
    box6(k, (x0, y0 - 0.02, zt(x0) - 0.01), (x0 + 0.08, y1 + 0.02, zt(x0) + 0.012), Z_GALV, skip=('-x',))   # the flashing
    box6(k, (x0, y0 - 0.02, zt(x0) + 0.012), (x0 + 0.008, y1 + 0.02, zt(x0) + 0.09), Z_GALV, skip=('-x',))
    for ys in (y0 + 0.04, y1 - 0.04):                                                                # steel brackets
        arm_a, arm_b = Vector((x0 + 0.004, ys, zt(x0) - 0.145)), Vector((x1 - 0.10, ys, zt(x1 - 0.10) - 0.145))
        k.strip([arm_a, arm_b], Vector((0, 0, 1)), 0.01, 0.04, Z_STEELPAINT)
        st_a, st_b = Vector((x0 + 0.004, ys, zt(x0) - 0.60)), Vector((x0 + 0.48, ys, zt(x0 + 0.48) - 0.15))
        k.strip([st_a, st_b], Vector((0, 0, 1)), 0.008, 0.035, Z_STEELPAINT)
        k.box(x0, x0 + 0.008, ys - 0.04, ys + 0.04, zt(x0) - 0.66, zt(x0) - 0.12, Z_STEELPAINT)
    # the lamp's conduit: up from the bulkhead's plate into the wall under the canopy
    K.conduit(k, [LAMP + Vector((0.012, 0.0, 0.075)), LAMP + Vector((0.012, 0.0, 0.16)), LAMP + Vector((0.012, 0.22, 0.16))], r=0.009)
    k.box(HX, HX + 0.045, LAMP.y + 0.20, LAMP.y + 0.29, LAMP.z + 0.11, LAMP.z + 0.20, Z_GALV)


def outside(k):
    """the steps with a pipe handrail, the field telephone box by the door, a snow shovel against the wall"""
    yc0, yc1 = STEPS['y0'], STEPS['y1']
    box6(k, (HX + PLO, yc0, PL0), (HX + 0.32, yc1, FL - 0.02), Z_SLAB, skip=('-x', '-z'))
    box6(k, (HX + 0.32, yc0, PL0), (HX + 0.62, yc1, 0.17), Z_SLAB, skip=('-x', '-z'))
    BOXES.append(('Wache_Step_Hi', ROOT, (HX, HX + 0.32, yc0, yc1, -0.10, FL - 0.02)))
    BOXES.append(('Wache_Step_Lo', ROOT, (HX + 0.32, HX + 0.62, yc0, yc1, -0.10, 0.17)))
    yr = yc0 - 0.06
    for xp, zt in ((HX + 0.30, 1.22), (HX + 0.66, 0.98)):
        k.cyl(Vector((xp, yr, -0.15)), Vector((xp, yr, zt)), 0.021, Z_STEELPAINT, 8)
    k.tube([Vector((HX + 0.004, yr, 1.30)), Vector((HX + 0.30, yr, 1.24)), Vector((HX + 0.66, yr, 1.00)), Vector((HX + 0.70, yr, 0.92))],
           0.021, Z_STEELPAINT, 8)
    k.box(HX, HX + 0.008, yr - 0.04, yr + 0.04, 1.24, 1.36, Z_STEELPAINT)
    # the field telephone box left of the door, its cable up into the canopy
    ty0, ty1 = -0.22, 0.04
    box6(k, (HX, ty0, 1.20), (HX + 0.10, ty1, 1.52), Z_STEELPAINT, skip=('-x',))
    box6(k, (HX + 0.10, ty0 - 0.005, 1.47), (HX + 0.112, ty1 + 0.005, 1.535), Z_STEELPAINT, skip=('-x',))
    k.cyl(Vector((HX + 0.11, (ty0 + ty1) / 2, 1.30)), Vector((HX + 0.13, (ty0 + ty1) / 2, 1.30)), 0.012, Z_STEELBLK, 8)
    K.conduit(k, [Vector((HX + 0.012, (ty0 + ty1) / 2, 1.52)), Vector((HX + 0.012, (ty0 + ty1) / 2, 2.60)),
                  Vector((HX + 0.012, CANOPY['y0'] + 0.05, 2.60))], r=0.009)
    # the snow shovel against the wall right of the door
    hb, ht = Vector((HX + 0.26, DOOR['u1'] + 0.33, 0.14)), Vector((HX + 0.03, DOOR['u1'] + 0.31, 1.28))
    k.cyl(hb, ht, 0.016, Z_TIMBER, 6)
    k.box(ht.x - 0.02, ht.x + 0.02, ht.y - 0.07, ht.y + 0.07, ht.z - 0.01, ht.z + 0.02, Z_TIMBER)
    Rb = Matrix.Rotation(math.atan2(hb.x - ht.x, ht.z - hb.z), 3, 'Y')
    k.box_m(hb + Vector((0.05, 0, -0.06)), (0.012, 0.36, 0.40), Z_GALV, Rb)


# ---------------------------------------------------------------- firewood: split pieces, each with its own zones
KINDS_P = (('wedge', 0.42), ('sector', 0.26), ('segment', 0.27), ('round', 0.05))
SIZES = {'wedge': (0.20, 0.30), 'sector': (0.12, 0.18), 'segment': (0.10, 0.19), 'round': (0.045, 0.07)}   # the logs' radii
SPECIES_P = ((0, 0.45), (1, 0.20), (2, 0.25), (3, 0.10))      # spruce, pine, beech, birch
WOOD_SCALE = 1.1                                     # the pieces' size (the stack: ~70 pieces, user 30.10: three times fewer)


def _pick(table, rng):
    t = rng.random() * sum(p_ for _, p_ in table)
    for k_, p_ in table:
        t -= p_
        if t <= 0:
            return k_
    return table[-1][0]


def wood_section(kind, R, rng):
    """the section of a piece of firewood: polygon (counter-clockwise, u right v up, the log's pith at the origin, the piece's
    middle towards +u) and per edge True = bark (the log's surface) / False = a split face"""
    def arc(r, a0, a1, nseg, jr):
        return [(r * (1 + rng.uniform(-jr, jr)) * math.cos(a0 + (a1 - a0) * i / nseg),
                 r * (1 + rng.uniform(-jr, jr)) * math.sin(a0 + (a1 - a0) * i / nseg)) for i in range(nseg + 1)]
    if kind == 'round':                              # a whole thin round
        n, ph = 7, rng.uniform(0, TAU)
        return arc(R, ph, ph + TAU * (n - 1) / n, n - 1, 0.05), [True] * n
    if kind == 'segment':                            # a round cut by one split, c = the split's distance from the pith
        c = R * rng.uniform(-0.12, 0.60)
        a = math.acos(c / R)
        nseg = 4 if a > 1.25 else 3
        return arc(R, -a, a, nseg, 0.04), [True] * nseg + [False]
    if kind == 'sector':                             # a quarter or a third of a round, the pith at its corner
        d = math.radians(rng.uniform(80, 125))
        nseg = 3 if d < math.radians(100) else 4
        return ([(rng.uniform(0.0, 0.015), rng.uniform(-0.01, 0.01))] + arc(R, -d / 2, d / 2, nseg, 0.04),
                [False] + [True] * nseg + [False])
    d = math.radians(rng.uniform(38, 58))            # 'wedge': split from a big round, the heart broken off near the pith
    r0 = R * rng.uniform(0.05, 0.22)
    nseg = 2 if R * d < 0.15 else 3
    i0 = (r0 * (1 + rng.uniform(-0.1, 0.1)) * math.cos(-d / 2), r0 * math.sin(-d / 2))
    i1 = (r0 * math.cos(d / 2), r0 * math.sin(d / 2))
    return [i0] + arc(R, -d / 2, d / 2, nseg, 0.03) + [i1], [False] + [True] * nseg + [False, False]


def _rot(poly, phi):
    c, s = math.cos(phi), math.sin(phi)
    return [(u * c - v * s, u * s + v * c) for (u, v) in poly]


def _lie(poly, bark, kind, mode, rng):
    """turn a section the way it lies: 'flat' on one of its split faces, 'up' / 'down' = the bark up / down (wedges and
    sectors by turns, so they nest), segments mostly on their split face"""
    j = math.radians(rng.uniform(-8, 8))
    if kind == 'round':
        return _rot(poly, rng.uniform(0, TAU))
    if kind == 'segment':
        mode = 'flat' if rng.random() < 0.7 else 'down'
    if mode == 'flat' or (kind != 'segment' and rng.random() < 0.15):
        m = len(poly)
        e = rng.choice([i for i in range(m) if not bark[i]])
        (ua, va), (ub, vb) = poly[e], poly[(e + 1) % m]
        return _rot(poly, -math.atan2(vb - va, ub - ua) + j * 0.5)
    if kind == 'segment':
        return _rot(poly, -math.pi / 2 + j)
    return _rot(poly, (math.pi / 2 if mode == 'up' else -math.pi / 2) + j)


def _profile(poly, us):
    """the section's lowest and highest v over each u (NaN where it isn't)"""
    lo = np.full(len(us), np.nan)
    hi = np.full(len(us), np.nan)
    m = len(poly)
    for e in range(m):
        (ua, va), (ub, vb) = poly[e], poly[(e + 1) % m]
        if abs(ub - ua) < 1e-9:
            continue
        sel = (us >= min(ua, ub)) & (us <= max(ua, ub))
        v = va + (us[sel] - ua) * (vb - va) / (ub - ua)
        lo[sel] = np.fmin(lo[sel], v)
        hi[sel] = np.fmax(hi[sel], v)
    return lo, hi


def _mirror(poly, bark):
    m = len(poly)
    return [(-u, v) for (u, v) in reversed(poly)], [bark[(m - 2 - i) % m] for i in range(m)]


def stack_firewood(c0, c1, zb, zt, rng, scale, nmax=999, sink=0.006, tries=12):
    """split firewood laid piece by piece, course by course from c0 to c1 onto the pieces below (from zb up to about zt):
    at each place the best of `tries` random pieces (kind, size, how it lies) = the one leaving the least gap under it, so
    the pieces nest; the first course lies on split faces. -> [(section round its pith, bark flags, (c, v) of the pith,
    kind, R)], (cs, skyline)"""
    step = 0.005
    cs = np.arange(c0 + step / 2, c1, step)
    S = np.full(len(cs), float(zb))
    out = []
    for course in range(80):
        rev = course % 2 == 1                        # every other course from the other end
        if rev:
            S = S[::-1].copy()
        cur = c0 + rng.uniform(0.0, 0.012)
        n0 = len(out)
        while cur < c1 - 0.04 and len(out) < nmax:
            best = None
            for attempt in range(tries):
                kind = _pick(KINDS_P, rng) if c1 - cur > 0.16 else rng.choice(('segment', 'segment', 'sector', 'round'))
                lo_, hi_ = SIZES[kind]
                R = scale * rng.uniform(lo_, hi_ if c1 - cur > 0.16 else (lo_ + hi_) / 2)
                poly, bark = wood_section(kind, R, rng)
                mode = 'flat' if course == 0 else rng.choice(('up', 'down', 'up', 'down', 'flat'))
                poly = _lie(poly, bark, kind, mode, rng)
                if rng.random() < 0.5:
                    poly, bark = _mirror(poly, bark)
                umin = min(p_[0] for p_ in poly)
                w = max(p_[0] for p_ in poly) - umin
                xl = cur + rng.uniform(0.003, 0.012)
                if xl + w > c1:
                    continue
                sel = np.nonzero((cs >= xl) & (cs <= xl + w))[0]
                lo, hi = _profile(poly, cs[sel] - xl + umin)
                ok = ~np.isnan(lo)
                if ok.sum() < 3:
                    continue
                rest = float(np.max(S[sel[ok]] - lo[ok])) - sink
                if rest + float(np.nanmax(hi)) > zt + 0.03:
                    continue
                hole = float(np.sum(np.clip(rest + lo[ok] - S[sel[ok]], 0, None))) * step
                score = hole / w + 0.012 * rng.random() + (0.03 if kind == 'round' else 0.0)
                if best is None or score < best[0]:
                    best = (score, poly, bark, kind, R, xl, w, umin, sel[ok], rest, hi[ok])
            if best is None:
                cur += 0.04
                continue
            _, poly, bark, kind, R, xl, w, umin, idx, rest, hi_ = best
            S[idx] = np.maximum(S[idx], rest + hi_)
            if rev:
                poly, bark = _mirror(poly, bark)
                out.append((poly, bark, (c0 + c1 - (xl - umin), rest), kind, R))
            else:
                out.append((poly, bark, (xl - umin, rest), kind, R))
            cur = xl + w
        if rev:
            S = S[::-1].copy()
        if len(out) == n0 or len(out) >= nmax:
            break
    return out, (cs, S)


def wood_piece(k, poly, bark, O, A, U, V, L, kind, R, rng, fresh, caps=(True, True)):
    """a piece of firewood: the section `poly` (round the pith) in the plane through O spanned by U, V, L long along A; its
    faces get the zones of its index in FIREWOOD; caps = (the end at O, the end at O + L A)"""
    i = len(FIREWOOD)
    FIREWOOD.append(dict(o=Vector(O), A=Vector(A), U=Vector(U), V=Vector(V), R=R, sp=_pick(SPECIES_P, rng), fresh=fresh,
                         kind=kind))
    P0 = [O + U * u + V * v for (u, v) in poly]
    P1 = [p_ + A * L for p_ in P0]
    if caps[0]:
        face(k, P0, Z_WOOD_END + i, -A)
    if caps[1]:
        face(k, P1, Z_WOOD_END + i, A)
    m = len(poly)
    for e in range(m):
        (ua, va), (ub, vb) = poly[e], poly[(e + 1) % m]
        face(k, [P0[e], P0[(e + 1) % m], P1[(e + 1) % m], P1[e]], (Z_WOOD_BARK if bark[e] else Z_WOOD_SPLIT) + i,
             U * (vb - va) - V * (ub - ua))


def woodpile(k):
    """split firewood stacked against the back wall under the eaves, the ends to the yard: about 70 pieces 0.30-0.33 long
    (wedges of big rounds, quarters, halves and slabs, a few thin rounds; spruce, pine, beech, birch), each with its own
    end grain; two rails under it, a stake at each front corner, two pieces fallen at its foot"""
    global PILE_TOP
    p = PILE
    rng = random.Random(1979)
    pieces, PILE_TOP = stack_firewood(p['x0'], p['x1'], p['z0'], p['z1'], rng, WOOD_SCALE)
    A, U, V = Vector((0, 1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1))
    for (poly, bark, (pc, pv), kind, R) in pieces:
        yb = p['y0'] + rng.uniform(0.0, 0.02)
        yf = p['y1'] - rng.uniform(0.0, 0.035)
        wood_piece(k, poly, bark, Vector((pc, yb, pv)), A, U, V, yf - yb, kind, R, rng, rng.uniform(0.2, 0.7), caps=(False, True))
    for ys in (p['y0'] + 0.07, p['y1'] - 0.07):                        # two rails along the stack
        box6(k, (p['x0'] - 0.04, ys - 0.045, -0.02), (p['x1'] + 0.04, ys + 0.045, p['z0']), Z_TIMBER, skip=('-z',))
    for xs in (p['x0'] - 0.06, p['x1']):                                # a stake at each front corner
        box6(k, (xs, p['y1'] - 0.04, -0.15), (xs + 0.06, p['y1'] + 0.02, p['z1'] + 0.10), Z_TIMBER)
    for (x, ang, kind, R) in ((-0.30, 70.0, 'sector', 0.15), (0.62, 20.0, 'segment', 0.13)):   # two fallen at its foot
        poly, bark = wood_section(kind, R * WOOD_SCALE, rng)
        poly = _lie(poly, bark, kind, 'flat', rng)
        uc = (min(p_[0] for p_ in poly) + max(p_[0] for p_ in poly)) / 2
        vmin = min(p_[1] for p_ in poly)
        a = math.radians(ang)
        A_ = Vector((math.cos(a), math.sin(a), 0))
        U_ = Vector((-math.sin(a), math.cos(a), 0))
        L = rng.uniform(0.30, 0.33)
        O = Vector((x, p['y1'] + 0.22, 0)) - U_ * uc + V * (-vmin - 0.006) - A_ * (L / 2)
        wood_piece(k, poly, bark, O, A_, U_, V, L, kind, R * WOOD_SCALE, rng, rng.uniform(0.3, 0.6))
    BOXES.append(('Wache_Woodpile', ROOT, (p['x0'] - 0.06, p['x1'] + 0.06, p['y0'], p['y1'] + 0.02, 0.0, p['z1'])))


def interior(k):
    # ---- the desk under the big window: top, apron, four legs; the log book, a mug, the radio and its lead to the antenna
    d = DESK
    box6(k, (d['x0'], d['y0'], d['z'] - 0.035), (d['x1'], d['y1'], d['z']), Z_DESK, skip=('-y',))
    box6(k, (d['x0'] + 0.04, d['y1'] - 0.065, d['z'] - 0.14), (d['x1'] - 0.04, d['y1'] - 0.045, d['z'] - 0.035), Z_TIMBER, skip=('+z',))
    for lx in (d['x0'] + 0.03, d['x1'] - 0.08):
        for ly in (d['y0'] + 0.03, d['y1'] - 0.08):
            box6(k, (lx, ly, FL), (lx + 0.05, ly + 0.05, d['z'] - 0.035), Z_TIMBER, skip=('-z', '+z'))
    box6(k, (0.48, -1.52, d['z']), (0.78, -1.31, d['z'] + 0.032), Z_BOOK, skip=('-z',))                  # the post's log book
    k.lathe(Vector((0.14, -1.30, d['z'])), (0, 0, 1), [(0.0, 0.038), (0.095, 0.042)], Z_MUG, 10, cap0=False, cap1=True)   # a mug
    k.tube([Vector((0.182, -1.30, d['z'] + 0.075)), Vector((0.215, -1.30, d['z'] + 0.065)), Vector((0.215, -1.30, d['z'] + 0.030)),
            Vector((0.18, -1.30, d['z'] + 0.022))], 0.006, Z_MUG, 5, caps=False)
    box6(k, (-0.95, -1.70, d['z']), (-0.66, -1.56, d['z'] + 0.17), Z_RADIO, skip=('-z',))              # the radio
    k.cyl(Vector((-0.92, -1.62, d['z'] + 0.17)), Vector((-0.86, -1.66, d['z'] + 0.52)), 0.004, Z_STEELBLK, 5)   # its aerial
    for kx in (-0.72, -0.89):
        k.cyl(Vector((kx, -1.56, d['z'] + 0.05)), Vector((kx, -1.545, d['z'] + 0.05)), 0.012, Z_STEELBLK, 8)
    k.tube([Vector((-0.80, -1.70, d['z'] + 0.10)), Vector((-0.80, IY0 + 0.01, d['z'] + 0.12)), Vector((-1.20, IY0 + 0.01, 1.60)),
            Vector((-1.20, IY0 + 0.01, 1.75)), Vector((-1.20, IY0 - 0.02, 1.75))], 0.0045, Z_STEELBLK, 5)
    socket('Audio_Radio', (-0.80, -1.55, d['z'] + 0.09), 'audio', parent=ROOT,
           note='the radio on the desk: the weather report in German, quietly (QUESTIONS_3 #6); X01 at the post silences it (#10)')
    for i, x in enumerate((-0.45, -0.05, 0.30)):
        socket(f'Slot_Table_{i + 1}', (x, -1.42, d['z']), 'slot', parent=ROOT, note='a place on the desk top (z = the top)')
    # the chair, turned a little to the window
    c = Vector((-0.15, -0.95, FL))
    box6(k, (c.x - 0.21, c.y - 0.21, c.z + 0.42), (c.x + 0.21, c.y + 0.21, c.z + 0.455), Z_TIMBER)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box6(k, (c.x + sx * 0.18 - 0.02, c.y + sy * 0.18 - 0.02, c.z), (c.x + sx * 0.18 + 0.02, c.y + sy * 0.18 + 0.02, c.z + 0.42),
                 Z_TIMBER, skip=('+z',))
        box6(k, (c.x + sx * 0.18 - 0.02, c.y + 0.16, c.z + 0.455), (c.x + sx * 0.18 + 0.02, c.y + 0.20, c.z + 0.90), Z_TIMBER, skip=('-z',))
    box6(k, (c.x - 0.185, c.y + 0.168, c.z + 0.70), (c.x + 0.185, c.y + 0.192, c.z + 0.86), Z_TIMBER)
    # ---- the bunk on the left wall: frame, boards, a straw mattress under a grey blanket, the pillow
    b = BUNK
    box6(k, (b['x0'], b['y0'], b['z'] - 0.12), (b['x1'], b['y1'], b['z'] - 0.04), Z_TIMBER, skip=('-x',))
    for ly in (b['y0'], b['y1'] - 0.06):
        box6(k, (b['x1'] - 0.06, ly, FL), (b['x1'], ly + 0.06, b['z'] - 0.12), Z_TIMBER, skip=('-z', '+z'))
    box6(k, (b['x0'], b['y0'] + 0.02, b['z'] - 0.04), (b['x1'] - 0.02, b['y1'] - 0.02, b['z'] + 0.06), Z_BLANKET, skip=('-x', '-z'))
    box6(k, (b['x0'] + 0.08, b['y1'] - 0.42, b['z'] + 0.06), (b['x1'] - 0.12, b['y1'] - 0.08, b['z'] + 0.14), Z_PILLOW, skip=('-z',))
    socket('Spot_Bunk', ((b['x0'] + b['x1']) / 2, (b['y0'] + b['y1']) / 2, b['z'] + 0.06), 'spot', parent=ROOT,
           note='the bunk: here the frozen player wakes (decision 7a.11); head at +y')
    BOXES.append(('Wache_Bunk', ROOT, (b['x0'], b['x1'], b['y0'], b['y1'], FL, b['z'] + 0.06)))
    BOXES.append(('Wache_Desk', ROOT, (d['x0'], d['x1'], d['y0'], d['y1'], FL, d['z'])))
    # ---- the stove: cast iron on legs, a steel plate under it, the fire door with its slot (Glow_Stove), a kettle, the pipe
    s = STOVE
    zb = FL + 0.10
    box6(k, (IX0, s['y0'] - 0.15, FL), (s['x1'] + 0.40, IY1, FL + 0.004), Z_FLOORPLATE, skip=('-z', '-x', '+y'))
    for lx in (s['x0'] + 0.03, s['x1'] - 0.07):
        for ly in (s['y0'] + 0.03, s['y1'] - 0.07):
            box6(k, (lx, ly, FL + 0.004), (lx + 0.04, ly + 0.04, zb), Z_IRON, skip=('-z', '+z'))
    box6(k, (s['x0'], s['y0'], zb), (s['x1'], s['y1'], FL + s['h']), Z_IRON)
    ztop = FL + s['h'] + 0.025
    box6(k, (s['x0'] - 0.02, s['y0'] - 0.02, FL + s['h']), (s['x1'] + 0.02, s['y1'] + 0.02, ztop), Z_IRON, skip=('-z',))
    k.cyl(Vector((s['x0'] + 0.13, s['y0'] + 0.12, ztop)), Vector((s['x0'] + 0.13, s['y0'] + 0.12, ztop + 0.006)), 0.09, Z_IRON, 12)   # hob ring
    xd = s['x1']
    fz0, fz1, fy0, fy1 = zb + 0.12, zb + 0.44, s['y0'] + 0.10, s['y1'] - 0.10
    box6(k, (xd, fy0, fz0), (xd + 0.012, fy1, fz1), Z_IRON, skip=('-x',))                              # the fire door
    sz0, sz1, sy0, sy1 = fz0 + 0.20, fz0 + 0.245, fy0 + 0.06, fy1 - 0.06                               # its draught slot
    k.box(xd + 0.012, xd + 0.024, fy0 + 0.02, fy0 + 0.05, fz0 + 0.12, fz0 + 0.20, Z_STEELBLK)          # the latch
    face(k, [(xd + 0.0135, sy0, sz0), (xd + 0.0135, sy1, sz0), (xd + 0.0135, sy1, sz1), (xd + 0.0135, sy0, sz1)], Z_STEELBLK, (1, 0, 0))
    G = kb('Glow_Stove', 'glow')
    quad(G, (xd + 0.016, (sy0 + sy1) / 2, (sz0 + sz1) / 2), (1, 0, 0), sy1 - sy0, (sz1 - sz0), uv('glow_warm'))
    part('Glow_Stove', 'static', (xd + 0.014, (sy0 + sy1) / 2, (sz0 + sz1) / 2), parent=ROOT,
         note='the fire in the stove door\'s slot: additive card (M_Start_Glow), always on; Light_Wache_Stove beside it')
    socket('LIGHT_Wache_Stove', (xd + 0.20, (sy0 + sy1) / 2, sz0), 'light', parent=ROOT, note='the stove\'s glow on the floor (point)')
    kc = Vector((s['x0'] + 0.13, s['y0'] + 0.12, ztop + 0.006))                                         # the kettle on the hob
    k.lathe(kc, (0, 0, 1), [(0.0, 0.085), (0.11, 0.09), (0.15, 0.06), (0.17, 0.03)], Z_KETTLE, 10, cap0=True, cap1=True)
    k.cyl(kc + Vector((0.07, 0, 0.05)), kc + Vector((0.16, 0, 0.13)), 0.014, Z_KETTLE, 6, r2=0.008)
    k.tube([kc + Vector((-0.06, 0, 0.15)), kc + Vector((-0.04, 0, 0.23)), kc + Vector((0.04, 0, 0.23)), kc + Vector((0.06, 0, 0.15))],
           0.006, Z_STEELBLK, 5, caps=False)
    p = PIPE
    k.cyl(Vector((p.x, p.y, ztop)), Vector((p.x, p.y, z_ci(p.y) + 0.02)), 0.06, Z_STEELBLK, 10, caps=False)
    k.cyl(Vector((p.x, p.y, z_ci(p.y) - 0.004)), Vector((p.x, p.y, z_ci(p.y) - 0.012)), 0.12, Z_GALV, 12)   # the ceiling collar
    socket('VFX_Smoke', (p.x, p.y, PIPE_TOP + 0.18), 'vfx', parent=ROOT, note='the stove\'s smoke over the pipe\'s cap')
    BOXES.append(('Wache_Stove', ROOT, (s['x0'], s['x1'], s['y0'], s['y1'], FL, ztop)))
    # the log basket by the stove with three split pieces from the stack (along x)
    bc = Vector((-0.80, 1.45, FL))
    box6(k, (bc.x - 0.20, bc.y - 0.16, bc.z), (bc.x + 0.20, bc.y + 0.16, bc.z + 0.28), Z_TIMBER, skip=('-z',))
    rng = random.Random(1980)
    pieces, _ = stack_firewood(bc.y - 0.15, bc.y + 0.15, bc.z + 0.28, bc.z + 0.52, rng, 0.62 * WOOD_SCALE, nmax=3)
    for (poly, bark, (pc, pv), kind, R) in pieces:
        x0_ = bc.x - 0.17 + rng.uniform(-0.02, 0.02)
        wood_piece(k, poly, bark, Vector((x0_, pc, pv)), Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)),
                   rng.uniform(0.31, 0.34), kind, R, rng, rng.uniform(0.5, 0.8))
    # ---- the shelf on the back wall (the funnel), its brackets; the clock over it; the key board by the door
    sh = SHELF
    box6(k, (sh['x0'], sh['y0'], sh['z']), (sh['x1'], sh['y1'], sh['z'] + 0.025), Z_TIMBER, skip=('+y',))
    for bx_ in (sh['x0'] + 0.12, sh['x1'] - 0.12):
        k.box(bx_ - 0.012, bx_ + 0.012, sh['y1'] - 0.20, sh['y1'], sh['z'] - 0.14, sh['z'], Z_STEELBLK)
    socket('Slot_Shelf', ((sh['x0'] + sh['x1']) / 2, (sh['y0'] + sh['y1']) / 2, sh['z'] + 0.03), 'slot', parent=ROOT,
           note='the shelf board on the back wall (the funnel, rim down)')
    cc = Vector((-0.20, IY1, 2.12))
    k.lathe(cc, (0, -1, 0), [(0.0, 0.13), (0.035, 0.13)], Z_CLOCK, 16, cap0=False, cap1=True)
    kb_ = (1.12, 1.42, 1.52, 1.68)
    box6(k, (kb_[0], IY1 - 0.018, kb_[2]), (kb_[1], IY1, kb_[3]), Z_TIMBER, skip=('+y',))
    for i in range(4):
        hx_ = kb_[0] + 0.05 + i * 0.067
        k.cyl(Vector((hx_, IY1 - 0.018, 1.58)), Vector((hx_, IY1 - 0.06, 1.595)), 0.004, Z_GALV, 5)
    k.box(kb_[0] + 0.045, kb_[0] + 0.06, IY1 - 0.055, IY1 - 0.05, 1.52, 1.575, Z_GALV)                 # a key on its hook
    # the first-aid box on the left wall by the window
    box6(k, (IX0, -1.52, 1.45), (IX0 + 0.11, -1.22, 1.70), Z_AID, skip=('-x',))
    # ---- the jerrycan's place: on the floor along the road wall under the small window, by the desk
    socket('Slot_Booth_Jerrycan', (IX1 - 0.12, -1.25, FL + 0.01), 'slot', parent=ROOT,
           note='the jerrycan on the floor along the road wall (ForestItemPointsStep: yaw 90 = along the wall, as in the booth)')
    # ---- the coat on its hook by the door, the calendar 1991, the light switch and the conduit to the ceiling lamp
    hk = Vector((IX1, 0.10, 1.80))
    k.cyl(hk, hk + Vector((-0.06, 0, 0.02)), 0.006, Z_STEELBLK, 6)
    xb = IX1 - 0.03
    box6(k, (xb - 0.20, hk.y - 0.20, 1.46), (xb, hk.y + 0.20, 1.72), Z_COAT)                           # shoulders
    box6(k, (xb - 0.25, hk.y - 0.26, 0.96), (xb, hk.y + 0.26, 1.46), Z_COAT, skip=('+z',))           # the body, open below
    for sg in (-1, 1):                                                                                # the sleeves
        ya, yb = sorted((hk.y + sg * 0.26, hk.y + sg * 0.32))
        box6(k, (xb - 0.17, ya, 1.06), (xb - 0.02, yb, 1.64), Z_COAT)
    box6(k, (xb - 0.17, hk.y - 0.12, 1.72), (xb - 0.01, hk.y + 0.12, 1.88), Z_COAT, skip=('-z',))     # the hood on the hook
    face(k, [(0.45, IY1 - 0.003, 1.42), (0.75, IY1 - 0.003, 1.42), (0.75, IY1 - 0.003, 1.86), (0.45, IY1 - 0.003, 1.86)], Z_CAL, (0, -1, 0))
    sw = Vector((IX1, DOOR['u1'] + 0.17, 1.40))
    box6(k, (IX1 - 0.04, sw.y - 0.04, sw.z - 0.045), (IX1, sw.y + 0.04, sw.z + 0.045), Z_GALV, skip=('+x',))
    cl = Vector((0.0, -0.20, z_ci(-0.20)))
    K.conduit(k, [Vector((IX1 - 0.02, sw.y, sw.z + 0.045)), Vector((IX1 - 0.02, sw.y, z_ci(sw.y) - 0.02)),
                  Vector((cl.x + 0.06, sw.y, z_ci(sw.y) - 0.02)), Vector((cl.x + 0.06, cl.y + 0.05, z_ci(cl.y + 0.05) - 0.02))], r=0.010)
    # ---- the caged ceiling bulkhead (the shed's): plate, housing, the dome (Lens_Wache, lit), the cage
    c = cl
    k.box(c.x - 0.045, c.x + 0.045, c.y - 0.045, c.y + 0.045, c.z - 0.012, c.z + 0.004, Z_STEELBLK)
    k.lathe(c - Vector((0, 0, 0.012)), (0, 0, -1), [(0.0, 0.07), (0.01, 0.085), (0.045, 0.085), (0.05, 0.072)], Z_STEELBLK, 12,
            cap0=True, cap1=False)
    L = kb('Lens_Wache', 'lens:booth')
    dome_c = c - Vector((0, 0, 0.060))
    L.disc_uv(dome_c, Vector((0, 0, -1)), 0.068, uv('l_bulk'), 12, dome=0.04)
    for a in (0, 60, 120):
        dv = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        k.tube([dome_c + dv * 0.078 * math.cos(math.radians(t)) - Vector((0, 0, 0.052 * math.sin(math.radians(t)))) for t in range(0, 181, 30)],
               0.003, Z_STEELBLK, 4, caps=False)
    part('Lens_Wache', 'static', dome_c - Vector((0, 0, 0.02)), parent=ROOT,
         note='the ceiling bulkhead\'s dome: M_Start_Lamp_Booth (lit); the light LIGHT_Wache_Inside under it')
    socket('LIGHT_Wache_Inside', dome_c - Vector((0, 0, 0.10)), 'light', parent=ROOT, note='the warm light inside (point, 2700 K)')
    # the ceiling: ply under the rafters, sloping with the roof
    face(k, [(IX0, IY0, z_ci(IY0)), (IX1, IY0, z_ci(IY0)), (IX1, IY1, z_ci(IY1)), (IX0, IY1, z_ci(IY1))], Z_LINING, (0, -TP, -1))


def build_wache():
    house()
    door()


# ---------------------------------------------------------------- the booth's parts that move into the house (Unity deltas)
def unity_vec(v):
    return [round(-float(v[0]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(-float(v[1]), 4) + 0.0]


MOVES = {   # template child -> delta in the prefab (Unity, metres)
    'Lamp_Booth': D_LAMP, 'Lens_Booth': D_LAMP, 'Glow_Booth': D_LAMP, 'LIGHT_Booth': D_LAMP,
    'Booth_Sign': D_SIGN}
