"""Station yard, Forest map prologue (Forest_Opening.json S7 power): the Update 3 fuel tanks and the transformer rebuilt in
the generator shed's construction and finishes.
  fuel tanks (root FuelTanks): a concrete bund (Auffangwanne) on the Update 3 footprint with a sump and its grating, two
  horizontal steel tanks (DIN 6616 style, 18 000 L each) on welded steel saddles over concrete plinths, painted in the
  station's grey-green with the stencils painted on (DIESEL, TANK 1 / TANK 2 · 18 000 L); on top the manhole, the vent with
  its hood, the fill stub; the fill lines run over the left end and the front wall down to the fill couplings (FILL T1 /
  T2, the level dials, the GHS flame); the suction line from the bottom of tank 1 runs along the bund floor, up the inside of
  the front wall and over it to the wing pump on its post (IX_PumpLever_301, +-60 deg, Update 3's lever) with the hose, the
  brass nozzle in its holder and the drip tray with a grating where the yard's jerrycan stands; a galvanised step-over stile
  with handrails, a cat ladder on tank 1's head, pipe stands, the drain valve with its padlock, the signboard
  (DIESELKRAFTSTOFF / DIESEL FUEL, RAUCHEN UND OFFENES FEUER VERBOTEN / NO SMOKING, NO NAKED FLAMES), the extinguisher post.
  transformer (root Trafo): a concrete pad with an oil sump (gravel) and steel rails, an oil-filled 250 kVA transformer
  (fin radiators, three porcelain HV bushings, four LV bushings, the conservator with its oil dial and the silica-gel
  breather, rating plate), the LV cable down to the trench covers and the grey GRP distribution cabinet, a chain-link fence
  with barbed wire and the gate (IX_TrafoGate_91, opens out 0..100, Update 3's), HOCHSPANNUNG — LEBENSGEFAHR / HIGH VOLTAGE —
  DANGER OF DEATH and UNBEFUGTEN IST DER ZUTRITT VERBOTEN / NO ADMITTANCE TO UNAUTHORISED PERSONS; behind the fence the
  creosoted pole: the crossarm with three pin insulators where the map's wires end, the fuse cutouts and surge arresters,
  the jumpers down to the bushings, the arrow plate and POLE 14.
Frames (each root is its own prefab; parts and sockets are given in their root's frame): FuelTanks — x along the tanks, y
toward the back (-y = the yard side with the pump), z up, origin = the middle of the bund on the ground (bund floor 0.15);
Trafo — x along the gate side, y toward the back (the pole), z up, origin = the middle of the pad on the ground (pad top
0.20).  Unity: (x, y, z) -> (-x, z, -y), angle -> -angle."""
import math
from mathutils import Vector, Matrix
import van3_mech as VM
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, prism_x, prism_y, quad, transform_kb, KBS, CONTRACT
from gen_kit import Z_STEELBLK, Z_GALV
from van2_kit import ZERO
import yard_tex as YT

uv = YT.uv
TAU = 2 * math.pi

# ---------------------------------------------------------------- zones
(Z_BUNDW, Z_BUNDF, Z_TANK, Z_SADDLE, Z_PLINTH, Z_PIPE, Z_GRATING, Z_RUBBERY, Z_FOOTC, Z_TRAYG, Z_SHELL) = range(200, 211)  # Tanks
(Z_PAD, Z_GRAVEL, Z_TRAFO, Z_FINS, Z_PORC, Z_POLE, Z_CABGRP, Z_COPPER, Z_CABLE, Z_PORCG, Z_TRENCH) = range(220, 231)  # Trafo
(Z_PUMPB, Z_LEVER, Z_GRIP, Z_HOSE, Z_BRASS, Z_EXT, Z_WHEEL, Z_GAUGEH, Z_LOCK, Z_BREATH, Z_EARTH, Z_COLUMN, Z_CAP,
 Z_SENSOR) = range(240, 254)                                                                                      # YardProps

# ---------------------------------------------------------------- the fuel tanks (FuelTanks frame)
BX, BY, WT = 4.30, 3.60, 0.20                      # bund outer half sizes (Update 3), wall thickness
IX, IY = BX - WT, BY - WT                          # inner faces 4.10, 3.40
FL, WTOP, WBOT, CH = 0.15, 0.86, -0.06, 0.02       # floor, wall top, slab underside, chamfer
SUMP = (-3.85, -3.45, -3.20, -2.80)                # the sump in the front-left corner
SUMP_Z = 0.03
TANK_Y = {'T1': -1.75, 'T2': 1.75}                 # tank 1 in front (the pump side)
TZ, TR, TL, THD = 1.75, 1.06, 2.50, 0.32           # axis height, shell vertex radius (24-gon), half length, head depth
NSEG = 24
PHI = [math.radians(7.5 + 15.0 * i) for i in range(NSEG)]       # from the bottom, toward +y, over the top, back by -y
TIN = TR * math.cos(math.radians(7.5))             # the facets lie 1.051 from the axis
TTOP = TZ + TIN
HEAD = [(0.0, TR), (0.05, 1.045), (0.11, 1.00), (0.17, 0.92), (0.22, 0.80), (0.265, 0.62), (0.295, 0.42), (0.313, 0.21),
        (THD, 0.0)]
SAD_X = (-1.60, 1.60)
PL_Z = 0.45                                        # plinth top
SAD_A = math.radians(37.5)                         # the saddle hugs the tank +-37.5 deg off the bottom
FILL_X, VENT_X, MAN_X, OUT_X = -2.10, -1.00, 0.60, -1.05
FILL_RUN = {'T1': -3.25, 'T2': -3.50}              # the fill lines' x over the left end and down to the couplings
FILL_Z = 1.20                                      # their run along y, over the front wall
COUPLING_Y, COUPLING_Z = -3.96, 0.95
PUMP_C = Vector((-1.50, -4.15, 1.02))              # wing pump body centre, shaft along y (Update 3)
LEVER_PIV = Vector((-1.50, -4.222, 1.02))          # IX_PumpLever_301 (Update 3's origin)
NOZZLE = Vector((-1.40, -4.25, 0.74))              # Pump_FuelTanks.nozzle (Forest_Opening.json)
OPERATOR = Vector((-1.50, -4.95, 0.0))             # Pump_FuelTanks.operatorPos
CAN = Vector((-1.10, -4.45, 0.03))                 # Jerrycan_Yard (Forest_Opening.json), turned -20 deg
CAN_YAW = -20.0
TRAY = (-1.34, -0.70, -4.70, -4.20)
FOOT = (-1.66, -1.36, -4.30, -4.00)
STILE_X = (3.04, 3.88)                             # the step-over stile lands beyond tank 1's head; 0.87 m between the
                                                   # handrails: the Snow player's capsule (d 0.68) passes with room
LADDER_X, LADDER_Y = 2.98, (-1.98, -1.52)
BOARD = dict(x0=0.30, x1=1.50, z0=1.18, z1=1.78, y=-3.89, posts=(0.35, 1.45))
EXT_POST = Vector((1.72, -4.10, 0.0))
DRAIN_X = -3.85

# ---------------------------------------------------------------- the transformer (Trafo frame)
TRAFO_PLACE = (Vector((8.0, -10.0, -0.044)), -90.0)            # Trafo root in the FuelTanks frame (Update 3 layout)
PAD = (-2.60, 2.60, -2.10, 2.10)
PAD_TOP, PAD_BOT = 0.20, -0.15
FX = (-2.50, 2.50)
FY0, FY1 = -2.00, 1.78                              # front (the gate) and back fence lines
FZ0, FZ1 = 0.22, 2.20
GATE = dict(x0=-1.50, x1=0.04, z0=0.23, z1=2.12)
HINGE_X, LATCH_X = -1.56, 0.105
GATE_PIV = Vector((-1.50, -2.00, 0.0))              # IX_TrafoGate_91 (Update 3's origin)
SUMP_T = (-0.95, 0.95, -0.45, 1.05)
TK = dict(x0=-0.62, x1=0.62, y0=0.02, y1=0.58, z0=0.40, z1=1.50)  # transformer tank
HV_X, HV_Y, LV_X, LV_Y = (-0.30, 0.0, 0.30), 0.36, (-0.36, -0.12, 0.12, 0.36), 0.10
HV_TOP = 2.02
CONS = dict(x0=-0.40, x1=0.40, y=0.66, z=1.78, r=0.12)
CAB = dict(x0=-2.30, x1=-1.55, y0=1.30, y1=1.66, z0=PAD_TOP, z1=1.30)
POLE = Vector((0.0, 2.00, 0.0))
POLE_TOP, POLE_R0, POLE_R1 = 8.60, 0.135, 0.105
XARM_Z = (8.15, 8.25)
INSUL_X = (-1.05, 0.45, 1.05)                       # the map's wires end over these (Forest_Wires)
INSUL_TOP = 8.40
CUT_Z, CUT_X, CUT_Y = 5.60, (-0.60, 0.0, 0.60), 1.70
ARR_Z = 4.90


def pole_r(z):
    return POLE_R0 + (POLE_R1 - POLE_R0) * max(0.0, min(1.0, z / POLE_TOP))


# ================================================================ helpers
def pipe(k, pts, r, zone, seg=8, bend=0.07):
    """tube along a polyline with rounded corners (three points on a short arc at every corner)"""
    pts = [Vector(p) for p in pts]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        d0, d1 = (b - a).normalized(), (c - b).normalized()
        if d0.dot(d1) > 0.999:
            out.append(b)
            continue
        rr = min(bend, (b - a).length * 0.45, (c - b).length * 0.45)
        p0, p1 = b - d0 * rr, b + d1 * rr
        for t in (0.0, 0.5, 1.0):
            q = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * b + t ** 2 * p1
            out.append(q)
    out.append(pts[-1])
    k.tube(out, r, zone, seg)


def tank_pt(x, yc, phi, r=TR):
    return Vector((x, yc + r * math.sin(phi), TZ - r * math.cos(phi)))


def slab_yz(k, x0, x1, zb, top, zone, sides=True):
    """plate between x0 and x1: bottom edge at zb, top edge along the polyline top [(y, z)] (y ascending)"""
    for i in range(len(top) - 1):
        (ya, za), (yb, zb_) = top[i], top[i + 1]
        for xx, s in ((x0, -1), (x1, 1)):
            face(k, [(xx, ya, zb), (xx, yb, zb), (xx, yb, zb_), (xx, ya, za)], zone, (s, 0, 0))
        n = Vector((0, -(zb_ - za), yb - ya))
        face(k, [(x0, ya, za), (x1, ya, za), (x1, yb, zb_), (x0, yb, zb_)], zone, n)
    if sides:
        (ya, za), (yb, zb_) = top[0], top[-1]
        face(k, [(x0, ya, zb), (x1, ya, zb), (x1, ya, za), (x0, ya, za)], zone, (0, -1, 0))
        face(k, [(x0, yb, zb), (x1, yb, zb), (x1, yb, zb_), (x0, yb, zb_)], zone, (0, 1, 0))


def chain_quad(k, axis, a, u0, u1, z0, z1, tile=0.5):
    """two-sided chain-link quad in the plane axis = a (y: u = x), UVs in tiles of `tile` metres"""
    for d, s in ((-0.0006, -1), (0.0006, 1)):
        if axis == 'y':
            pts = [(u0, a + d, z0), (u1, a + d, z0), (u1, a + d, z1), (u0, a + d, z1)]
            n = (0, s, 0)
        else:
            pts = [(a + d, u0, z0), (a + d, u1, z0), (a + d, u1, z1), (a + d, u0, z1)]
            n = (s, 0, 0)
        uvs = [(u0 / tile, z0 / tile), (u1 / tile, z0 / tile), (u1 / tile, z1 / tile), (u0 / tile, z1 / tile)]
        face(k, pts, ZERO, n, uvs)


def barbed_band(k, axis, a, u0, u1, zb):
    """two-sided barbed-wire band (alpha texture) in the plane axis = a from u0 to u1, foot at zb, 0.36 high"""
    for d, s in ((-0.0006, -1), (0.0006, 1)):
        if axis == 'y':
            pts = [(u0, a + d, zb), (u1, a + d, zb), (u1, a + d, zb + 0.36), (u0, a + d, zb + 0.36)]
            n = (0, s, 0)
        else:
            pts = [(a + d, u0, zb), (a + d, u1, zb), (a + d, u1, zb + 0.36), (a + d, u0, zb + 0.36)]
            n = (s, 0, 0)
        face(k, pts, ZERO, n, [(u0 / 0.5, 0.0), (u1 / 0.5, 0.0), (u1 / 0.5, 1.0), (u0 / 0.5, 1.0)])


# ================================================================ the bund
def bund():
    B = kb('FuelTanks', 'Tanks')
    # the wall ring: outer faces (down into the ground), the chamfers, the top, the inner faces down to the floor
    O = [(-BX, -BY), (BX, -BY), (BX, BY), (-BX, BY)]
    I = [(-IX, -IY), (IX, -IY), (IX, IY), (-IX, IY)]
    Oc = [(x + (CH if x < 0 else -CH), y + (CH if y < 0 else -CH)) for x, y in O]
    Ic = [(x - (CH if x < 0 else -CH), y - (CH if y < 0 else -CH)) for x, y in I]
    for i in range(4):
        j = (i + 1) % 4
        (ax, ay), (bx, by) = O[i], O[j]
        n_out = Vector((by - ay, -(bx - ax), 0)).normalized()          # the ring runs counter-clockwise from above
        face(B, [(ax, ay, WBOT), (bx, by, WBOT), (bx, by, WTOP - CH), (ax, ay, WTOP - CH)], Z_BUNDW, n_out)
        face(B, [(ax, ay, WTOP - CH), (bx, by, WTOP - CH), (Oc[j][0], Oc[j][1], WTOP), (Oc[i][0], Oc[i][1], WTOP)], Z_BUNDW,
             n_out + Vector((0, 0, 1)))
        face(B, [(Oc[i][0], Oc[i][1], WTOP), (Oc[j][0], Oc[j][1], WTOP), (Ic[j][0], Ic[j][1], WTOP), (Ic[i][0], Ic[i][1], WTOP)],
             Z_BUNDW, (0, 0, 1))
        face(B, [(Ic[i][0], Ic[i][1], WTOP), (Ic[j][0], Ic[j][1], WTOP), (I[j][0], I[j][1], WTOP - CH), (I[i][0], I[i][1], WTOP - CH)],
             Z_BUNDW, -n_out + Vector((0, 0, 1)))
        face(B, [(I[i][0], I[i][1], WTOP - CH), (I[j][0], I[j][1], WTOP - CH), (I[j][0], I[j][1], FL), (I[i][0], I[i][1], FL)],
             Z_BUNDW, -n_out)
    # the floor round the sump (four quads), the sump's sides and floor
    sx0, sx1, sy0, sy1 = SUMP
    for x0, x1, y0, y1 in ((-IX, IX, sy1, IY), (-IX, IX, -IY, sy0), (-IX, sx0, sy0, sy1), (sx1, IX, sy0, sy1)):
        face(B, [(x0, y0, FL), (x1, y0, FL), (x1, y1, FL), (x0, y1, FL)], Z_BUNDF, (0, 0, 1))
    box6(B, (sx0, sy0, SUMP_Z), (sx1, sy1, FL), {'*': Z_BUNDF}, skip=('+z', '-z'))
    for f in list(B.bm.faces)[-4:]:                                       # the sump's sides face inward
        f.normal_flip()
    face(B, [(sx0, sy0, SUMP_Z), (sx1, sy0, SUMP_Z), (sx1, sy1, SUMP_Z), (sx0, sy1, SUMP_Z)], Z_BUNDF, (0, 0, 1))
    # the sump grating (galvanised, on a ledge 2 cm down)
    gz = FL - 0.02
    for i in range(6):
        xx = sx0 + 0.02 + i * (sx1 - sx0 - 0.04) / 5
        B.box(xx - 0.004, xx + 0.004, sy0 + 0.01, sy1 - 0.01, gz - 0.02, gz, Z_GALV)
    for yy in (sy0 + 0.01, sy1 - 0.01):
        B.box(sx0 + 0.01, sx1 - 0.01, yy - 0.005, yy + 0.005, gz - 0.025, gz, Z_GALV)
    # the drain stub through the front wall (the valve and its padlock are props)
    pipe(B, [(DRAIN_X, -IY + 0.05, 0.26), (DRAIN_X, -BY - 0.13, 0.26)], 0.024, Z_PIPE, 8)
    B.cyl(Vector((DRAIN_X, -BY - 0.002, 0.26)), Vector((DRAIN_X, -BY - 0.012, 0.26)), 0.055, Z_PIPE, 10)    # the wall flange


# ================================================================ the tanks
def tank(name, yc):
    B = kb('FuelTanks', 'Tanks')
    xs = [-TL, -TL / 2, 0.0, TL / 2, TL]
    for xa, xb in zip(xs[:-1], xs[1:]):
        for i in range(NSEG):
            pa, pb = PHI[i], PHI[(i + 1) % NSEG]
            pm = (pa + pb) / 2 if i < NSEG - 1 else pa + math.radians(7.5)
            out = Vector((0, math.sin(pm), -math.cos(pm)))
            face(B, [tank_pt(xa, yc, pa), tank_pt(xb, yc, pa), tank_pt(xb, yc, pb), tank_pt(xa, yc, pb)], Z_SHELL, out)
    for sgn in (-1, 1):                                                  # dished heads
        x0 = sgn * TL
        ctr = Vector((x0 - sgn * 1.2, yc, TZ))
        rings = []
        for d, r in HEAD:
            rings.append([tank_pt(x0 + sgn * d, yc, p, r) for p in PHI] if r > 1e-6 else None)
        apex = Vector((x0 + sgn * THD, yc, TZ))
        for j in range(len(HEAD) - 1):
            ra, rb = rings[j], rings[j + 1]
            for i in range(NSEG):
                i2 = (i + 1) % NSEG
                pts = [ra[i], ra[i2], rb[i2], rb[i]] if rb is not None else [ra[i], ra[i2], apex]
                c = sum(pts, Vector()) / len(pts)
                face(B, pts, Z_SHELL, c - ctr)
    # the saddles: concrete plinth, base plate, web plate hugging the tank, wear plate, two ribs, anchor bolts
    for sx in SAD_X:
        box6(B, (sx - 0.30, yc - 0.85, FL), (sx + 0.30, yc + 0.85, PL_Z), Z_PLINTH, skip=('-z',))
        B.box(sx - 0.16, sx + 0.16, yc - 0.80, yc + 0.80, PL_Z, PL_Z + 0.02, Z_SADDLE)
        arc = [p for p in PHI if p <= SAD_A + 1e-6] + [p - TAU for p in PHI if p >= TAU - SAD_A - 1e-6]
        arc = sorted(arc, key=lambda p: math.sin(p))
        top = [(yc + (TR + 0.012) * math.sin(p), TZ - (TR + 0.012) * math.cos(p)) for p in arc]
        slab_yz(B, sx - 0.006, sx + 0.006, PL_Z + 0.02, top, Z_SADDLE)
        for i in range(len(arc) - 1):                                    # wear plate: outer face and the two ends
            pa, pb = arc[i], arc[i + 1]
            pm = (pa + pb) / 2
            out = Vector((0, math.sin(pm), -math.cos(pm)))
            qa, qb = tank_pt(0, yc, pa, TR + 0.012), tank_pt(0, yc, pb, TR + 0.012)
            face(B, [(sx - 0.11, qa.y, qa.z), (sx + 0.11, qa.y, qa.z), (sx + 0.11, qb.y, qb.z), (sx - 0.11, qb.y, qb.z)], Z_SADDLE, out)
            ia, ib = tank_pt(0, yc, pa, TR + 0.002), tank_pt(0, yc, pb, TR + 0.002)
            for xx, s in ((sx - 0.11, -1), (sx + 0.11, 1)):
                face(B, [(xx, ia.y, ia.z), (xx, qa.y, qa.z), (xx, qb.y, qb.z), (xx, ib.y, ib.z)], Z_SADDLE, (s, 0, 0))
        for p in (arc[0], arc[-1]):
            qa, ia = tank_pt(0, yc, p, TR + 0.012), tank_pt(0, yc, p, TR + 0.002)
            out = Vector((0, math.cos(p), math.sin(p))) * (1 if math.sin(p) > 0 else -1)
            face(B, [(sx - 0.11, ia.y, ia.z), (sx + 0.11, ia.y, ia.z), (sx + 0.11, qa.y, qa.z), (sx - 0.11, qa.y, qa.z)], Z_SADDLE, out)
        for dy in (-0.35, 0.35):
            box6(B, (sx - 0.10, yc + dy - 0.005, PL_Z + 0.02), (sx + 0.10, yc + dy + 0.005, 0.740), Z_SADDLE, skip=('-z',))
        for ax in (sx - 0.12, sx + 0.12):
            for ay in (yc - 0.70, yc + 0.70):
                B.lathe(Vector((ax, ay, PL_Z + 0.035)), (0, 0, 1), [(0.0, 0.010), (0.02, 0.010)], Z_STEELBLK, 6, cap0=False)
                box6(B, (ax - 0.016, ay - 0.016, PL_Z + 0.02), (ax + 0.016, ay + 0.016, PL_Z + 0.035), Z_STEELBLK, skip=('-z',))
    # on top: the manhole (collar, bolted lid), the vent with its hood, the fill stub (its line: fill_lines)
    B.cyl(Vector((MAN_X, yc, TTOP - 0.04)), Vector((MAN_X, yc, TTOP + 0.12)), 0.30, Z_TANK, 16, caps=False)
    B.cyl(Vector((MAN_X, yc, TTOP + 0.12)), Vector((MAN_X, yc, TTOP + 0.15)), 0.335, Z_TANK, 16)
    for i in range(12):
        a = TAU * i / 12
        bx_, by_ = MAN_X + 0.31 * math.cos(a), yc + 0.31 * math.sin(a)
        B.box(bx_ - 0.012, bx_ + 0.012, by_ - 0.012, by_ + 0.012, TTOP + 0.15, TTOP + 0.165, Z_STEELBLK)
    B.box(MAN_X - 0.03, MAN_X + 0.03, yc - 0.22, yc + 0.22, TTOP + 0.15, TTOP + 0.17, Z_TANK)          # lid handle bar
    pipe(B, [(VENT_X, yc, TTOP - 0.03), (VENT_X, yc, 3.42)], 0.026, Z_PIPE, 8)
    B.cyl(Vector((VENT_X, yc, TTOP)), Vector((VENT_X, yc, TTOP + 0.025)), 0.06, Z_PIPE, 10)          # flange
    B.cyl(Vector((VENT_X, yc, 3.30)), Vector((VENT_X, yc, 3.40)), 0.045, Z_PIPE, 10)                 # flame arrester body
    B.lathe(Vector((VENT_X, yc, 3.42)), (0, 0, 1), [(0.0, 0.03), (0.0, 0.085), (0.05, 0.085), (0.075, 0.06), (0.09, 0.0)],
            Z_PIPE, 12, cap0=True, cap1=False)                                                    # the hood
    B.cyl(Vector((FILL_X, yc, TTOP)), Vector((FILL_X, yc, TTOP + 0.025)), 0.07, Z_PIPE, 10)
    # the tank's lifting lugs (two on top)
    for lx in (-1.90, 1.90):
        B.box(lx - 0.06, lx + 0.06, yc - 0.006, yc + 0.006, TTOP - 0.01, TTOP + 0.07, Z_TANK)


def _head_arc():
    """[(r, s)]: the arc length s along the head's profile from the apex, against the radius r (ascending)"""
    prof = list(reversed(HEAD))
    out, s = [(prof[0][1], 0.0)], 0.0
    for (d0, r0), (d1, r1) in zip(prof[:-1], prof[1:]):
        s += math.hypot(d1 - d0, r1 - r0)
        out.append((r1, s))
    return out


def tank_uvs(objs, uv_name):
    """custom unwrap of the tank shells and heads (psxbake hook, after the smart projection, before the packing): each shell
    unrolled into one island with its seam along the bottom, each head an azimuthal-equidistant disc about its apex — no
    island borders across the smooth surfaces; the smart projection's metric scale is kept"""
    o = next((o for o in objs if o.name == 'FuelTanks'), None)
    if o is None:
        return
    me = o.data
    za = me.attributes['zone'].data
    uvl = me.uv_layers[uv_name].data
    M = o.matrix_world
    a3 = a2 = 0.0
    for p in me.polygons:
        if round(za[p.index].value) in (Z_SHELL, Z_BUNDF, Z_PLINTH):
            continue
        vs = [M @ me.vertices[i].co for i in p.vertices]
        us = [uvl[li].uv.copy() for li in p.loop_indices]
        for i in range(1, len(vs) - 1):
            a3 += (vs[i] - vs[0]).cross(vs[i + 1] - vs[0]).length / 2
            e1, e2 = us[i] - us[0], us[i + 1] - us[0]
            a2 += abs(e1.x * e2.y - e1.y * e2.x) / 2
    k = math.sqrt(a2 / a3)                       # (the zones scaled before this hook, Z_BUNDF and Z_PLINTH, are left out)
    tab = _head_arc()

    def s_of_r(rho):
        for (r0, s0), (r1, s1) in zip(tab[:-1], tab[1:]):
            if r0 <= rho <= r1 + 1e-9:
                return s0 + (s1 - s0) * (rho - r0) / max(r1 - r0, 1e-9)
        return tab[-1][1] + (rho - tab[-1][0])

    for p in me.polygons:
        if round(za[p.index].value) != Z_SHELL:
            continue
        vs = [M @ me.vertices[i].co for i in p.vertices]
        yc = TANK_Y['T1'] if sum(v.y for v in vs) < 0 else TANK_Y['T2']
        ox = 0.0 if yc < 0 else 9.0
        if all(abs(v.x) <= TL + 1e-4 for v in vs):
            ph = [math.atan2(v.y - yc, -(v.z - TZ)) % TAU for v in vs]
            if max(ph) - min(ph) > math.pi:
                ph = [a + TAU if a < math.pi else a for a in ph]
            uvs = [(a * TR + ox, v.x) for a, v in zip(ph, vs)]
        else:
            sx_ = 1 if sum(v.x for v in vs) > 0 else -1
            cx = ox + (20.0 if sx_ > 0 else 24.0)
            uvs = []
            for v in vs:
                rho = math.hypot(v.y - yc, v.z - TZ)
                th = math.atan2(v.z - TZ, v.y - yc)
                s_ = s_of_r(rho)
                uvs.append((cx + s_ * math.cos(th), s_ * math.sin(th)))
        for li, (u, v_) in zip(p.loop_indices, uvs):
            uvl[li].uv = (k * u, k * v_)


def fill_lines():
    B = kb('FuelTanks', 'Tanks')
    for name, yc in TANK_Y.items():
        xr = FILL_RUN[name]
        pipe(B, [(FILL_X, yc, TTOP + 0.02), (FILL_X, yc, 2.98), (xr, yc, 2.98), (xr, yc, FILL_Z), (xr, -3.80, FILL_Z),
                 (xr, -3.80, COUPLING_Z), (xr, COUPLING_Y + 0.04, COUPLING_Z)], 0.03, Z_PIPE, 8, bend=0.10)
    # the pipe stands carrying both runs (galvanised post, crossbar, U clamps)
    xm = (FILL_RUN['T1'] + FILL_RUN['T2']) / 2
    for yy in (0.0, -2.95):
        B.cyl(Vector((xm, yy, FL + 0.01)), Vector((xm, yy, FILL_Z - 0.07)), 0.024, Z_GALV, 8)
        B.box(xm - 0.20, xm + 0.20, yy - 0.025, yy + 0.025, FILL_Z - 0.07, FILL_Z - 0.03, Z_GALV)
        B.box(xm - 0.08, xm + 0.08, yy - 0.06, yy + 0.06, FL, FL + 0.01, Z_GALV)
        for xr in FILL_RUN.values():
            B.box(xr - 0.04, xr + 0.04, yy - 0.012, yy + 0.012, FILL_Z + 0.03, FILL_Z + 0.04, Z_GALV)
    # the couplings' wall plate with the two level dials (their faces: panel)
    B.box(-3.62, -3.13, -BY - 0.010, -BY, 0.38, 0.62, Z_GALV)
    for xr in FILL_RUN.values():                                             # brackets holding the drops to the wall
        B.box(xr - 0.025, xr + 0.025, -3.80, -BY, FILL_Z - 0.32, FILL_Z - 0.28, Z_GALV)


def suction_line():
    """tank 1's bottom outlet (the valve is a prop), along the floor, up the inside of the front wall, over it to the pump"""
    B = kb('FuelTanks', 'Tanks')
    yc = TANK_Y['T1']
    zb = TZ - TIN
    pipe(B, [(OUT_X, yc, zb + 0.02), (OUT_X, yc, 0.30), (OUT_X, -3.22, 0.30), (OUT_X, -3.22, PUMP_C.z), (OUT_X, -3.85, PUMP_C.z),
             (PUMP_C.x, -3.85, PUMP_C.z), (PUMP_C.x, -4.07, PUMP_C.z)], 0.024, Z_PIPE, 8, bend=0.09)
    B.cyl(Vector((OUT_X, yc, zb - 0.02)), Vector((OUT_X, yc, zb + 0.01)), 0.06, Z_PIPE, 10)            # outlet flange
    for yy in (-2.40, -3.05):                                                 # floor saddles under the run
        B.box(OUT_X - 0.05, OUT_X + 0.05, yy - 0.03, yy + 0.03, FL, 0.276, Z_GALV)
    B.box(OUT_X - 0.04, OUT_X + 0.04, -3.40, -3.246, 0.74, 0.78, Z_GALV)      # wall bracket on the riser
    B.box(OUT_X - 0.04, OUT_X + 0.04, -3.62, -3.40, WTOP, WTOP + 0.03, Z_GALV) # saddle on the wall top
    B.box(OUT_X - 0.012, OUT_X + 0.012, -3.52, -3.48, WTOP + 0.03, PUMP_C.z - 0.024, Z_GALV)


def pump_and_tray():
    B = kb('FuelTanks', 'Tanks')
    fx0, fx1, fy0, fy1 = FOOT
    box6(B, (fx0, fy0, -0.15), (fx1, fy1, 0.02), Z_FOOTC, skip=('-z',))
    tx0, tx1, ty0, ty1 = TRAY                                                 # drip tray: rim, bottom, the grating on top
    box6(B, (tx0, ty0, 0.0), (tx1, ty1, 0.004), Z_TRAYG, skip=('-z',))
    for (a0, a1, b0, b1) in ((tx0, tx1, ty0, ty0 + 0.012), (tx0, tx1, ty1 - 0.012, ty1), (tx0, tx0 + 0.012, ty0 + 0.012, ty1 - 0.012),
                             (tx1 - 0.012, tx1, ty0 + 0.012, ty1 - 0.012)):
        box6(B, (a0, b0, 0.004), (a1, b1, 0.045), Z_TRAYG, skip=('-z',))
    for i in range(1, 12):
        xx = tx0 + i * (tx1 - tx0) / 12
        B.box(xx - 0.003, xx + 0.003, ty0 + 0.012, ty1 - 0.012, 0.012, CAN.z, Z_GRATING)
    for yy in (ty0 + 0.17, ty1 - 0.17):
        B.box(tx0 + 0.012, tx1 - 0.012, yy - 0.003, yy + 0.003, 0.012, CAN.z, Z_GRATING)
    P = kb('Pump', 'YardProps')                                                # wing pump on its post
    box6(P, (PUMP_C.x - 0.03, -4.18, 0.03), (PUMP_C.x + 0.03, -4.12, 0.90), Z_COLUMN, skip=('-z', '+z'))
    P.box(PUMP_C.x - 0.07, PUMP_C.x + 0.07, -4.22, -4.08, 0.02, 0.03, Z_COLUMN)          # foot plate
    P.box(PUMP_C.x - 0.05, PUMP_C.x + 0.05, -4.17, -4.10, 0.90, 0.935, Z_COLUMN)         # head bracket
    P.cyl(Vector((PUMP_C.x, -4.09, PUMP_C.z)), Vector((PUMP_C.x, -4.205, PUMP_C.z)), 0.09, Z_PUMPB, 14)
    P.cyl(Vector((PUMP_C.x, -4.20, PUMP_C.z)), Vector((PUMP_C.x, -4.212, PUMP_C.z)), 0.10, Z_PUMPB, 14)  # cover flange
    for i in range(6):
        a = TAU * i / 6 + 0.26
        P.cyl(Vector((PUMP_C.x + 0.085 * math.cos(a), -4.212, PUMP_C.z + 0.085 * math.sin(a))),
              Vector((PUMP_C.x + 0.085 * math.cos(a), -4.220, PUMP_C.z + 0.085 * math.sin(a))), 0.008, Z_COLUMN, 6)
    P.cyl(Vector((PUMP_C.x, -4.09, PUMP_C.z)), Vector((PUMP_C.x, -4.06, PUMP_C.z)), 0.04, Z_PUMPB, 10)    # inlet boss
    P.cyl(Vector((PUMP_C.x + 0.085, -4.15, PUMP_C.z - 0.03)), Vector((PUMP_C.x + 0.125, -4.15, PUMP_C.z - 0.03)), 0.022, Z_PUMPB, 8)
    # the short hose from the outlet down into the nozzle, which hangs below it in a ring holder on the post
    hose = [(PUMP_C.x + 0.125, -4.15, PUMP_C.z - 0.03), (-1.355, -4.165, 0.975), (-1.37, -4.20, 0.95), (-1.392, -4.24, 0.93),
            (NOZZLE.x, NOZZLE.y, 0.905)]
    P.tube([Vector(p) for p in hose], 0.016, Z_HOSE, 8)
    P.cyl(Vector((NOZZLE.x, NOZZLE.y, 0.92)), Vector((NOZZLE.x, NOZZLE.y, 0.86)), 0.022, Z_BRASS, 8)          # ferrule
    VM.rbox(P, (NOZZLE.x, NOZZLE.y, 0.84), (0.05, 0.035, 0.06), Z_BRASS, r=0.008, ch=0.004)                   # the valve body
    P.cyl(Vector((NOZZLE.x, NOZZLE.y, 0.81)), Vector((NOZZLE.x, NOZZLE.y, NOZZLE.z)), 0.011, Z_BRASS, 8)       # the spout
    P.box(PUMP_C.x + 0.045, NOZZLE.x - 0.02, NOZZLE.y - 0.007, NOZZLE.y + 0.007, 0.86, 0.875, Z_COLUMN)  # the ring holder
    P.box(PUMP_C.x + 0.03, PUMP_C.x + 0.045, NOZZLE.y - 0.008, -4.18, 0.85, 0.885, Z_COLUMN)
    P.box(PUMP_C.x - 0.105, PUMP_C.x + 0.105, -4.188, -4.180, 0.585, 0.655, Z_COLUMN)                   # plate on the post
    # the lever (IX_PumpLever_301): a flat bar from the boss, the round grip across the top toward the operator
    L = kb('IX_PumpLever_301', 'YardProps')
    L.cyl(Vector((LEVER_PIV.x, -4.212, LEVER_PIV.z)), Vector((LEVER_PIV.x, -4.232, LEVER_PIV.z)), 0.026, Z_LEVER, 10)
    L.box(LEVER_PIV.x - 0.015, LEVER_PIV.x + 0.015, -4.236, -4.224, LEVER_PIV.z - 0.05, 1.40, Z_LEVER)
    L.cyl(Vector((LEVER_PIV.x, -4.230, 1.38)), Vector((LEVER_PIV.x, -4.30, 1.38)), 0.016, Z_GRIP, 10)
    part('IX_PumpLever_301', 'hinge', LEVER_PIV, (0, 1, 0), (-60, 60), parent='FuelTanks', states=['left', 'right'],
         note='the wing pump\'s lever: held (use) it swings -60..+60 and back, +0.5 L/s into a jerrycan under the nozzle '
              '(Pump_FuelTanks, Forest_Opening.json; Update 3: same name, pivot and travel)')
    part('Pump', 'static', (PUMP_C.x, -4.15, 0.0), parent='FuelTanks',
         note='the wing pump on its post: body, hose, the brass nozzle in its holder (Pump_FuelTanks.nozzle at its tip)')


def stile_and_ladder():
    B = kb('FuelTanks', 'Tanks')
    x0, x1 = STILE_X
    treads = [(-4.20, -3.96, 0.29), (-3.96, -3.72, 0.58), (-3.72, -3.28, 0.88), (-3.28, -3.04, 0.62), (-3.04, -2.80, 0.38)]
    for ya, yb, zt in treads:                                                # grating treads with a nosing bar
        box6(B, (x0, ya, zt - 0.03), (x1, yb, zt), {'+z': Z_GRATING, '*': Z_GALV})
    # stringers: flat bars down both sides, outside (to the ground) and inside (to the floor)
    for xx in (x0 - 0.012, x1 + 0.002):
        for pts in ([(-4.32, 0.0), (-4.20, 0.0), (-3.72, 0.60), (-3.72, 0.90), (-3.98, 0.90), (-4.32, 0.40)],
                    [(-3.28, 0.60), (-2.68, FL), (-2.56, FL), (-2.56, 0.30), (-3.10, 0.90), (-3.28, 0.90)]):
            poly = [(y, z) for y, z in pts]
            prism_x(B, poly[::-1] if _cw(poly) else poly, xx, xx + 0.010, Z_GALV, Z_GALV)
        box6(B, (xx, -3.72, 0.78), (xx + 0.010, -3.28, 0.90), Z_GALV)           # over the wall
    # handrails: posts, a sloped rail up, level over the wall, down inside, mid rails
    for xx in (x0 - 0.035, x1 + 0.035):
        posts = [(-4.26, 0.0, 1.15), (-3.70, 0.88, 1.85), (-3.30, 0.88, 1.85), (-2.70, FL, 1.12)]
        for yy, z0, z1 in posts:
            B.cyl(Vector((xx, yy, z0)), Vector((xx, yy, z1)), 0.021, Z_GALV, 8)
        pipe(B, [(xx, -4.26, 1.15), (xx, -3.70, 1.85), (xx, -3.30, 1.85), (xx, -2.70, 1.12)], 0.021, Z_GALV, 8, bend=0.05)
        pipe(B, [(xx, -4.26, 0.62), (xx, -3.70, 1.33), (xx, -3.30, 1.33), (xx, -2.70, 0.62)], 0.014, Z_GALV, 6, bend=0.05)
    # the cat ladder on tank 1's right head: rails, rungs, wall brackets to the head, the rails bent over the top
    ly0, ly1 = LADDER_Y
    for yy in (ly0, ly1):
        pipe(B, [(LADDER_X, yy, FL), (LADDER_X, yy, 3.12), (LADDER_X - 0.12, yy, 3.24), (2.40, yy, 3.24), (2.40, yy, TTOP - 0.01)],
             0.019, Z_GALV, 8, bend=0.10)
        for zb in (1.05, 2.45):
            hx = head_x(math.hypot(yy - TANK_Y['T1'], zb - TZ))
            B.box(hx - 0.01, LADDER_X - 0.012, yy - 0.012, yy + 0.012, zb - 0.02, zb + 0.02, Z_GALV)
    for i in range(10):
        zr = 0.43 + i * 0.28
        B.cyl(Vector((LADDER_X, ly0 + 0.012, zr)), Vector((LADDER_X, ly1 - 0.012, zr)), 0.013, Z_GALV, 6)


def head_x(rho):
    """x of the right head's surface at the distance rho from the tank's axis"""
    if rho >= TR:
        return TL
    for (d0, r0), (d1, r1) in zip(HEAD[:-1], HEAD[1:]):
        if r1 <= rho <= r0:
            return TL + d0 + (d1 - d0) * (r0 - rho) / max(r0 - r1, 1e-9)
    return TL + THD


def _cw(poly):
    a = 0.0
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
        a += x0 * y1 - x1 * y0
    return a < 0


def board_and_extinguisher():
    B = kb('FuelTanks', 'Tanks')
    S = kb('FuelTanks_Signs', 'panel')
    bd = BOARD
    for px in bd['posts']:
        B.cyl(Vector((px, bd['y'] + 0.034, -0.30)), Vector((px, bd['y'] + 0.034, bd['z1'] + 0.04)), 0.026, Z_GALV, 8)
        B.cyl(Vector((px, bd['y'] + 0.034, bd['z1'] + 0.04)), Vector((px, bd['y'] + 0.034, bd['z1'] + 0.048)), 0.03, Z_GALV, 8)
    box6(B, (bd['x0'], bd['y'] + 0.002, bd['z0']), (bd['x1'], bd['y'] + 0.008, bd['z1']), Z_GALV)
    quad(S, ((bd['x0'] + bd['x1']) / 2, bd['y'], (bd['z0'] + bd['z1']) / 2), (0, -1, 0), bd['x1'] - bd['x0'] - 0.02,
         bd['z1'] - bd['z0'] - 0.02, uv('board_fuel'))
    e = EXT_POST
    B.cyl(Vector((e.x, e.y, -0.30)), Vector((e.x, e.y, 1.72)), 0.026, Z_GALV, 8)
    box6(B, (e.x - 0.17, e.y - 0.20, 1.30), (e.x + 0.17, e.y + 0.03, 1.32), Z_GALV)                 # the little roof
    box6(B, (e.x - 0.17, e.y - 0.20, 1.04), (e.x - 0.165, e.y + 0.03, 1.30), Z_GALV)
    box6(B, (e.x + 0.165, e.y - 0.20, 1.04), (e.x + 0.17, e.y + 0.03, 1.30), Z_GALV)
    box6(B, (e.x - 0.11, e.y - 0.034, 1.43), (e.x + 0.11, e.y - 0.026, 1.67), Z_GALV)                # sign plate
    quad(S, (e.x, e.y - 0.036, 1.55), (0, -1, 0), 0.20, 0.20, uv('plate_ext'))
    Pr = kb('FuelTanks_Props', 'YardProps')
    Pr.box(e.x - 0.03, e.x + 0.03, e.y - 0.07, e.y - 0.02, 1.08, 1.12, Z_COLUMN)                    # the bracket
    Pr.cyl(Vector((e.x, e.y - 0.11, 0.62)), Vector((e.x, e.y - 0.11, 1.10)), 0.085, Z_EXT, 12)
    Pr.lathe(Vector((e.x, e.y - 0.11, 1.10)), (0, 0, 1), [(0.0, 0.085), (0.03, 0.06), (0.05, 0.03), (0.07, 0.0)], Z_EXT, 12, cap0=False)
    Pr.box(e.x - 0.015, e.x + 0.015, e.y - 0.13, e.y - 0.09, 1.17, 1.22, Z_LEVER)                   # head
    Pr.box(e.x - 0.01, e.x + 0.06, e.y - 0.12, e.y - 0.10, 1.215, 1.225, Z_LEVER)
    Pr.tube([Vector((e.x - 0.015, e.y - 0.12, 1.19)), Vector((e.x - 0.09, e.y - 0.14, 1.10)),
             Vector((e.x - 0.10, e.y - 0.15, 0.80)), Vector((e.x - 0.09, e.y - 0.14, 0.70))], 0.011, Z_HOSE, 6)


def fittings_props():
    """valves, the fill couplings with their caps, the overfill sensor box, the dials, the drain valve and its padlock,
    the earthing leads"""
    Pr = kb('FuelTanks_Props', 'YardProps')
    S = kb('FuelTanks_Signs', 'panel')
    yc = TANK_Y['T1']
    zv = 0.52                                                                 # tank 1's outlet valve (gate valve)
    VM.rbox(Pr, (OUT_X, yc, zv), (0.10, 0.08, 0.11), Z_CAP, r=0.015, ch=0.008)
    Pr.cyl(Vector((OUT_X, yc - 0.04, zv)), Vector((OUT_X, yc - 0.13, zv)), 0.008, Z_LEVER, 6)
    Pr.lathe(Vector((OUT_X, yc - 0.13, zv)), (0, -1, 0), [(0.0, 0.07), (0.0, 0.085), (0.012, 0.085), (0.012, 0.07)], Z_WHEEL, 14,
             cap0=False, cap1=False)
    for a in (0, 90):
        r_ = math.radians(a)
        Pr.box(OUT_X - 0.075 * abs(math.cos(r_)) - 0.006, OUT_X + 0.075 * abs(math.cos(r_)) + 0.006, yc - 0.137, yc - 0.125,
               zv - 0.075 * abs(math.sin(r_)) - 0.006, zv + 0.075 * abs(math.sin(r_)) + 0.006, Z_WHEEL)
    for name, xr in FILL_RUN.items():                                         # couplings and their chained caps
        c = Vector((xr, COUPLING_Y, COUPLING_Z))
        Pr.cyl(c + Vector((0, 0.04, 0)), c - Vector((0, 0.02, 0)), 0.042, Z_CAP, 12)
        Pr.cyl(c - Vector((0, 0.02, 0)), c - Vector((0, 0.06, 0)), 0.050, Z_CAP, 12)
        for s in (-1, 1):
            Pr.box(xr + s * 0.05 - 0.008, xr + s * 0.05 + 0.008, c.y - 0.05, c.y - 0.03, c.z - 0.008, c.z + 0.008, Z_CAP)
        Pr.tube([c + Vector((0.03, -0.02, -0.04)), c + Vector((0.05, 0.0, -0.10)), c + Vector((0.04, 0.02, -0.06))], 0.003, Z_LEVER, 4)
        quad(S, (xr, -BY - 0.0115, 0.58), (0, -1, 0), 0.16, 0.053, uv('plate_fill1' if name == 'T1' else 'plate_fill2'))
        Pr.cyl(Vector((xr, -BY - 0.010, 0.46)), Vector((xr, -BY - 0.040, 0.46)), 0.046, Z_GAUGEH, 12)   # its level dial
        quad(S, (xr, -BY - 0.044, 0.46), (0, -1, 0), 0.078, 0.078, uv('gauge_t1' if name == 'T1' else 'gauge_t2'))
    VM.rbox(Pr, (-3.03, -BY - 0.03, 0.50), (0.08, 0.06, 0.12), Z_SENSOR, r=0.01, ch=0.005)       # overfill sensor socket
    quad(S, (-2.86, -BY - 0.0015, 0.55), (0, -1, 0), 0.12, 0.12, uv('ghs'))
    VM.rbox(Pr, (DRAIN_X, -BY - 0.09, 0.26), (0.07, 0.06, 0.07), Z_CAP, r=0.012, ch=0.006)       # the drain ball valve
    Pr.box(DRAIN_X - 0.008, DRAIN_X + 0.008, -BY - 0.10, -BY - 0.08, 0.29, 0.31, Z_LEVER)
    Pr.box(DRAIN_X - 0.012, DRAIN_X + 0.15, -BY - 0.10, -BY - 0.08, 0.305, 0.320, Z_WHEEL)       # its lever (closed: along x)
    Pr.box(DRAIN_X + 0.13, DRAIN_X + 0.15, -BY - 0.10, -BY - 0.08, 0.17, 0.305, Z_LEVER)        # the hasp down to the wall eye
    VM.rbox(Pr, (DRAIN_X + 0.14, -BY - 0.09, 0.14), (0.04, 0.02, 0.045), Z_LOCK, r=0.006, ch=0.003)  # padlock
    Pr.lathe(Vector((DRAIN_X + 0.14, -BY - 0.09, 0.162)), (0, 0, 1), [(0.0, 0.012), (0.02, 0.012)], Z_CAP, 6, cap0=False)
    for yc_ in TANK_Y.values():                                               # earthing leads from the saddles to the wall
        Pr.tube([Vector((SAD_X[0] - 0.16, yc_ - 0.78, PL_Z + 0.03)), Vector((SAD_X[0] - 0.30, yc_ - 0.80, FL + 0.02)),
                 Vector((-IX + 0.02, yc_ - 0.80, FL + 0.02)), Vector((-IX + 0.002, yc_ - 0.80, 0.40))], 0.006, Z_EARTH, 5)
    # the pump's plate and the tanks' name plate on tank 1's left head
    S2 = S
    quad(S2, (PUMP_C.x, -4.191, 0.62), (0, -1, 0), 0.20, 0.065, uv('plate_pump'))
    quad(S2, (-TL - THD - 0.003, TANK_Y['T1'], TZ - 0.30), (-1, 0, 0), 0.20, 0.125, uv('plate_tank'))


def fuel_points():
    socket('Spot_Jerrycan', CAN, 'item_slot', parent='FuelTanks', yaw=CAN_YAW,
           note='Jerrycan_Yard stands here at the start: empty, on the drip-tray grating under the nozzle, turned -20 deg '
                '(Forest_Opening.json, same place as Update 3)')
    socket('Stand_PumpOperator', OPERATOR, 'stand', parent='FuelTanks',
           note='where the one who pumps stands (Pump_FuelTanks.operatorPos)')
    socket('Hand_PumpLever', (LEVER_PIV.x, -4.27, 1.38), 'hand', parent='IX_PumpLever_301',
           note='hold use: the lever swings left and right (+-60); 0.5 L/s while held')
    socket('Pump_Nozzle', NOZZLE, 'vfx', parent='Pump', dir=(0, 0, -1),
           note='the nozzle\'s tip (Pump_FuelTanks.nozzle): diesel runs out here while pumping into a can within 0.45 m '
                '(horizontal) and at most 0.7 m below')
    socket('VFX_FuelDrip', NOZZLE - Vector((0, 0, 0.01)), 'vfx', parent='Pump', dir=(0, 0, -1),
           note='a drop of diesel now and then; the tray smells')
    socket('Audio_Pump', PUMP_C, 'audio', parent='Pump', note='the wing pump: suck-clack each stroke, the can gurgling')
    for name, yc in TANK_Y.items():
        socket(f'Audio_Tank_{name}', (0.0, yc, TZ), 'audio', parent='FuelTanks',
               note=f'tank {name[1]} booms when knocked (tank 2 nearly empty: a hollow ring); diesel sloshing')
    socket('Audio_Stile', ((STILE_X[0] + STILE_X[1]) / 2, -3.50, 0.90), 'audio', parent='FuelTanks',
           note='steps on the galvanised grating')
    socket('Hide_TankGap', (0.0, 0.0, FL), 'hide', parent='FuelTanks',
           note='crouch between the two tanks inside the bund: out of sight from the yard and the pump')


def fuel_colliders():
    B = [('Bund_Slab', 'FuelTanks', (-BX, BX, -BY, BY, WBOT, FL), None),
         ('Bund_Wall_F', 'FuelTanks', (-BX, BX, -BY, -IY, FL, WTOP), None),
         ('Bund_Wall_B', 'FuelTanks', (-BX, BX, IY, BY, FL, WTOP), None),
         ('Bund_Wall_L', 'FuelTanks', (-BX, -IX, -IY, IY, FL, WTOP), None),
         ('Bund_Wall_R', 'FuelTanks', (IX, BX, -IY, IY, FL, WTOP), None)]
    for name, yc in TANK_Y.items():
        B.append((f'Tank_{name}_A', 'FuelTanks', (-TL - THD, TL + THD, yc - 0.75, yc + 0.75, TZ - TIN, TTOP), None))
        B.append((f'Tank_{name}_B', 'FuelTanks', (-TL - THD, TL + THD, yc - TIN, yc + TIN, TZ - 0.55, TZ + 0.55), None))
        for sx in SAD_X:
            B.append((f'Saddle_{name}_{"L" if sx < 0 else "R"}', 'FuelTanks', (sx - 0.30, sx + 0.30, yc - 0.85, yc + 0.85, FL, 0.93),
                      None))
    B += [('Pump', 'Pump', (PUMP_C.x - 0.10, PUMP_C.x + 0.13, -4.23, -4.05, 0.0, PUMP_C.z + 0.10), None),
          ('Stile_1', 'FuelTanks', (*STILE_X, -4.20, -3.96, 0.0, 0.29), None),
          ('Stile_2', 'FuelTanks', (*STILE_X, -3.96, -3.72, 0.0, 0.58), None),
          ('Stile_Top', 'FuelTanks', (*STILE_X, -3.72, -3.28, 0.0, 0.88), None),
          ('Stile_3', 'FuelTanks', (*STILE_X, -3.28, -3.04, FL, 0.62), None),
          ('Stile_4', 'FuelTanks', (*STILE_X, -3.04, -2.80, FL, 0.38), None),
          ('Stile_Rail_L', 'FuelTanks', (STILE_X[0] - 0.06, STILE_X[0] - 0.01, -4.28, -2.68, 0.0, 1.87), None),
          ('Stile_Rail_R', 'FuelTanks', (STILE_X[1] + 0.01, STILE_X[1] + 0.06, -4.28, -2.68, 0.0, 1.87), None),
          ('Ladder', 'FuelTanks', (LADDER_X - 0.04, LADDER_X + 0.04, LADDER_Y[0] - 0.03, LADDER_Y[1] + 0.03, FL, 3.26), None),
          ('Fill_Drops', 'FuelTanks', (FILL_RUN['T2'] - 0.06, FILL_RUN['T1'] + 0.06, -4.02, -3.60, 0.85, FILL_Z + 0.04), None),
          ('Board', 'FuelTanks', (BOARD['x0'], BOARD['x1'], -3.90, -3.85, BOARD['z0'], BOARD['z1']), None),
          ('Board_Post_L', 'FuelTanks', (BOARD['posts'][0] - 0.03, BOARD['posts'][0] + 0.03, -3.89, -3.83, 0.0, BOARD['z0']), None),
          ('Board_Post_R', 'FuelTanks', (BOARD['posts'][1] - 0.03, BOARD['posts'][1] + 0.03, -3.89, -3.83, 0.0, BOARD['z0']), None),
          ('Extinguisher', 'FuelTanks', (EXT_POST.x - 0.17, EXT_POST.x + 0.17, EXT_POST.y - 0.20, EXT_POST.y + 0.03, 0.0, 1.70),
           None)]
    return B


def fuel_knock_rays():
    rays = []
    for name, yc in TANK_Y.items():
        s = -1 if yc < 0 else 1
        for i, x in enumerate((-1.8, -0.4, 1.0, 2.0)):
            rays.append((f'Knock_{name}_Side{i}', (x, yc + s * 2.2, TZ + 0.25), (0, -s, 0)))
        for i, x in enumerate((-1.2, 1.4)):
            rays.append((f'Knock_{name}_Top{i}', (x, yc + 0.3, 3.8), (0, 0, -1)))
        for sg, lab in ((-1, 'L'), (1, 'R')):
            rays.append((f'Knock_{name}_Head{lab}', (sg * 3.9, yc + 0.35, TZ + 0.3), (-sg, 0, 0)))
    return rays


# ================================================================ the transformer
def trafo_pad():
    T = kb('Trafo', 'Trafo')
    x0, x1, y0, y1 = PAD
    sx0, sx1, sy0, sy1 = SUMP_T
    for (a0, a1, b0, b1) in ((x0, x1, sy1, y1), (x0, x1, y0, sy0), (x0, sx0, sy0, sy1), (sx1, x1, sy0, sy1)):
        face(T, [(a0, b0, PAD_TOP), (a1, b0, PAD_TOP), (a1, b1, PAD_TOP), (a0, b1, PAD_TOP)], Z_PAD, (0, 0, 1))
    for (ax, ay), (bx, by), n in (((x0, y0), (x1, y0), (0, -1, 0)), ((x1, y0), (x1, y1), (1, 0, 0)), ((x1, y1), (x0, y1), (0, 1, 0)),
                                  ((x0, y1), (x0, y0), (-1, 0, 0))):
        face(T, [(ax, ay, PAD_BOT), (bx, by, PAD_BOT), (bx, by, PAD_TOP), (ax, ay, PAD_TOP)], Z_PAD, n)
    gz = PAD_TOP - 0.08                                                     # the oil sump: sides, gravel
    box6(T, (sx0, sy0, gz), (sx1, sy1, PAD_TOP), Z_PAD, skip=('+z', '-z'))
    for f in list(T.bm.faces)[-4:]:
        f.normal_flip()
    face(T, [(sx0, sy0, gz), (sx1, sy0, gz), (sx1, sy1, gz), (sx0, sy1, gz)], Z_GRAVEL, (0, 0, 1))
    for xr in (-0.45, 0.45):                                                # rails across the sump (steel I)
        T.box(xr - 0.05, xr + 0.05, sy0 - 0.06, sy1 + 0.06, PAD_TOP, PAD_TOP + 0.012, Z_STEELBLK)
        T.box(xr - 0.006, xr + 0.006, sy0 - 0.06, sy1 + 0.06, PAD_TOP + 0.012, PAD_TOP + 0.088, Z_STEELBLK)
        T.box(xr - 0.05, xr + 0.05, sy0 - 0.06, sy1 + 0.06, PAD_TOP + 0.088, PAD_TOP + 0.10, Z_STEELBLK)
    # cable trench covers: transformer -> cabinet
    for (a0, a1, b0, b1) in ((-1.95, -0.92, 0.12, 0.42), (-2.10, -1.80, 0.42, CAB['y0'])):
        box6(T, (a0, b0, PAD_TOP), (a1, b1, PAD_TOP + 0.03), Z_TRENCH, skip=('-z',))


def transformer():
    T = kb('Trafo', 'Trafo')
    t = TK
    for yb in (0.06, 0.54):                                                 # base frame (channels along x)
        box6(T, (-0.68, yb - 0.04, PAD_TOP + 0.10), (0.68, yb + 0.04, t['z0']), Z_TRAFO)
    box6(T, (t['x0'], t['y0'], t['z0']), (t['x1'], t['y1'], t['z1']), Z_TRAFO)
    box6(T, (t['x0'] - 0.04, t['y0'] - 0.04, t['z1']), (t['x1'] + 0.04, t['y1'] + 0.04, t['z1'] + 0.04), Z_TRAFO)   # the lid
    for i in range(14):                                                     # bolts round the lid
        a = i / 13.0
        for yy in (t['y0'] - 0.02, t['y1'] + 0.02):
            xx = t['x0'] + a * (t['x1'] - t['x0'])
            T.box(xx - 0.01, xx + 0.01, yy - 0.01, yy + 0.01, t['z1'] + 0.04, t['z1'] + 0.055, Z_STEELBLK)
    for (fy0, fy1) in ((t['y0'] - 0.20, t['y0']), (t['y1'], t['y1'] + 0.20)):           # the fin radiators, front and back
        for i in range(13):
            xx = -0.48 + i * 0.08
            box6(T, (xx - 0.006, fy0, t['z0'] + 0.12), (xx + 0.006, fy1, t['z1'] - 0.10), Z_FINS)
        for zz in (t['z0'] + 0.10, t['z1'] - 0.10):
            T.cyl(Vector((-0.52, (fy0 + fy1) / 2, zz)), Vector((0.52, (fy0 + fy1) / 2, zz)), 0.022, Z_FINS, 8)
    for lx in (t['x0'] + 0.04, t['x1'] - 0.04):                              # lifting lugs
        for ly in (t['y0'] - 0.02, t['y1'] + 0.02):
            box6(T, (lx - 0.03, ly - 0.006, t['z1'] + 0.04), (lx + 0.03, ly + 0.006, t['z1'] + 0.12), Z_TRAFO, skip=('-z',))
    zl = t['z1'] + 0.04
    for x in HV_X:                                                          # HV bushings: brown porcelain, five sheds
        prof = [(0.0, 0.06), (0.03, 0.06), (0.03, 0.045)]
        for s in range(4):
            h = 0.07 + s * 0.08
            prof += [(h, 0.045), (h + 0.005, 0.078 - s * 0.003), (h + 0.022, 0.078 - s * 0.003), (h + 0.03, 0.045)]
        prof += [(0.40, 0.04), (0.40, 0.0)]
        T.lathe(Vector((x, HV_Y, zl)), (0, 0, 1), prof, Z_PORC, 10, cap0=False)
        T.cyl(Vector((x, HV_Y, zl + 0.40)), Vector((x, HV_Y, HV_TOP)), 0.014, Z_COPPER, 8)
        T.box(x - 0.025, x + 0.025, HV_Y - 0.008, HV_Y + 0.008, HV_TOP - 0.03, HV_TOP + 0.02, Z_COPPER)
    for x in LV_X:                                                          # LV bushings: short, one shed, copper flags
        T.lathe(Vector((x, LV_Y, zl)), (0, 0, 1), [(0.0, 0.05), (0.02, 0.05), (0.02, 0.035), (0.07, 0.035), (0.075, 0.055),
                                                   (0.09, 0.055), (0.10, 0.03), (0.14, 0.03), (0.14, 0.0)], Z_PORC, 8, cap0=False)
        T.box(x - 0.02, x + 0.02, LV_Y - 0.005, LV_Y + 0.005, zl + 0.14, zl + 0.22, Z_COPPER)
    c = CONS                                                                # the conservator on two brackets, its pipe
    T.cyl(Vector((c['x0'], c['y'], c['z'])), Vector((c['x1'], c['y'], c['z'])), c['r'], Z_TRAFO, 14, caps=False)
    for sg, xe in ((-1, c['x0']), (1, c['x1'])):
        T.lathe(Vector((xe, c['y'], c['z'])), (sg, 0, 0), [(0.0, c['r']), (0.025, c['r'] * 0.85), (0.04, c['r'] * 0.5), (0.045, 0.0)],
                Z_TRAFO, 14, cap0=False)
    for bx in (-0.28, 0.28):
        box6(T, (bx - 0.006, 0.54, zl + 0.012), (bx + 0.006, 0.62, c['z'] - c['r'] * 0.85), Z_TRAFO, skip=('-z',))
        box6(T, (bx - 0.03, 0.53, zl), (bx + 0.03, 0.62, zl + 0.012), Z_TRAFO)
    pipe(T, [(0.12, c['y'], c['z'] - c['r'] + 0.01), (0.12, c['y'], zl + 0.08), (0.12, 0.48, zl + 0.08),
             (0.12, 0.48, zl)], 0.018, Z_TRAFO, 8, bend=0.03)
    box6(T, (0.07, 0.43, zl + 0.03), (0.17, 0.53, zl + 0.11), Z_TRAFO)                                # the relay box
    pipe(T, [(c['x1'] + 0.04, c['y'], c['z']), (c['x1'] + 0.32, c['y'], c['z']), (c['x1'] + 0.32, c['y'], 1.36)], 0.012, Z_TRAFO, 6,
         bend=0.04)
    # the LV cable bundle along over the flags, to the left, down the left end into the trench; a lead up from each flag
    pipe(T, [(LV_X[-1] + 0.05, LV_Y, zl + 0.30), (-0.74, LV_Y, zl + 0.30), (-0.74, LV_Y, PAD_TOP + 0.10),
             (-0.92, LV_Y + 0.15, PAD_TOP + 0.03)], 0.034, Z_CABLE, 8, bend=0.10)
    for x in LV_X:
        T.cyl(Vector((x, LV_Y, zl + 0.21)), Vector((x, LV_Y, zl + 0.29)), 0.014, Z_CABLE, 6)
    for zz in (0.55, 0.95, 1.30):
        T.box(-0.78, -0.62, LV_Y - 0.045, LV_Y + 0.045, zz - 0.012, zz + 0.012, Z_STEELBLK)


def cabinet():
    T = kb('Trafo', 'Trafo')
    c = CAB
    box6(T, (c['x0'], c['y0'], c['z0']), (c['x1'], c['y1'], c['z0'] + 0.10), Z_TRENCH, skip=('-z',))     # plinth
    box6(T, (c['x0'] + 0.01, c['y0'] + 0.01, c['z0'] + 0.10), (c['x1'] - 0.01, c['y1'] - 0.01, c['z1']), Z_CABGRP, skip=('-z',))
    box6(T, (c['x0'] - 0.02, c['y0'] - 0.03, c['z1']), (c['x1'] + 0.02, c['y1'] + 0.02, c['z1'] + 0.05), Z_CABGRP)
    xm = (c['x0'] + c['x1']) / 2
    T.box(xm - 0.002, xm + 0.002, c['y0'] + 0.002, c['y0'] + 0.012, c['z0'] + 0.14, c['z1'] - 0.04, Z_CABLE)   # door gap


def fence():
    T = kb('Trafo', 'Trafo')
    M_ = kb('Trafo_Fence_Mesh', 'chainlink')
    Bb = kb('Trafo_Fence_Barbed', 'barbed')
    x0, x1 = FX
    posts = [(x0, FY0), (HINGE_X, FY0), (LATCH_X, FY0), (1.30, FY0), (x1, FY0), (x1, -0.10), (x1, FY1), (1.25, FY1), (-1.25, FY1),
             (x0, FY1), (x0, -0.10)]
    for (px, py) in posts:
        T.cyl(Vector((px, py, PAD_BOT + 0.05)), Vector((px, py, FZ1 + 0.02)), 0.030, Z_GALV, 6)
        T.cyl(Vector((px, py, FZ1 + 0.02)), Vector((px, py, FZ1 + 0.035)), 0.034, Z_GALV, 6)
        T.cyl(Vector((px, py, FZ1 + 0.035)), Vector((px, py, FZ1 + 0.40)), 0.012, Z_GALV, 4)              # barbed-wire arm
    runs = [('y', FY0, x0, HINGE_X), ('y', FY0, LATCH_X, x1), ('x', x1, FY0, FY1), ('y', FY1, x0, x1), ('x', x0, FY0, FY1)]
    for ax, a, u0, u1 in runs:
        if ax == 'y':
            T.cyl(Vector((u0 + 0.03, a, FZ1)), Vector((u1 - 0.03, a, FZ1)), 0.021, Z_GALV, 6)
            T.cyl(Vector((u0 + 0.03, a, FZ0 + 0.03)), Vector((u1 - 0.03, a, FZ0 + 0.03)), 0.004, Z_GALV, 4)
        else:
            T.cyl(Vector((a, u0 + 0.03, FZ1)), Vector((a, u1 - 0.03, FZ1)), 0.021, Z_GALV, 6)
            T.cyl(Vector((a, u0 + 0.03, FZ0 + 0.03)), Vector((a, u1 - 0.03, FZ0 + 0.03)), 0.004, Z_GALV, 4)
        chain_quad(M_, ax, a, u0 + 0.03, u1 - 0.03, FZ0, FZ1 - 0.02)
        barbed_band(Bb, ax, a, u0, u1, FZ1 + 0.03)
    part('Trafo_Fence_Mesh', 'static', (0, 0, 1.0), parent='Trafo', note='chain-link of the fence (M_Yard_ChainLink, 0.5 m tile)')
    part('Trafo_Fence_Barbed', 'static', (0, 0, 2.4), parent='Trafo', note='barbed wire over the fence (M_Yard_Barbed)')
    # the gate leaf: tube frame, a brace, chain-link, barbed wire, the drop latch; hinges on the hinge post
    G = kb('IX_TrafoGate_91', 'Trafo')
    g = GATE
    gy = FY0
    for xx in (g['x0'], g['x1']):
        G.cyl(Vector((xx, gy, g['z0'])), Vector((xx, gy, g['z1'] + 0.37)), 0.017, Z_GALV, 8)
    for zz in (g['z0'] + 0.02, 1.15, g['z1']):
        G.cyl(Vector((g['x0'] + 0.017, gy, zz)), Vector((g['x1'] - 0.017, gy, zz)), 0.015, Z_GALV, 8)
    G.cyl(Vector((g['x0'] + 0.03, gy, g['z0'] + 0.04)), Vector((g['x1'] - 0.03, gy, 1.13)), 0.012, Z_GALV, 6)
    for zz in (0.45, 1.85):                                                 # hinges: post straps, collars round the leaf tube
        T.box(HINGE_X + 0.02, g['x0'] - 0.026, gy - 0.008, gy + 0.008, zz - 0.025, zz + 0.025, Z_GALV)
        T.cyl(Vector((g['x0'], gy, zz - 0.03)), Vector((g['x0'], gy, zz + 0.03)), 0.026, Z_GALV, 8, caps=False)
    G.box(g['x1'] - 0.01, g['x1'] + 0.03, gy - 0.040, gy - 0.025, 1.00, 1.10, Z_GALV)             # the drop latch
    G.cyl(Vector((g['x1'] + 0.02, gy - 0.047, 1.12)), Vector((g['x1'] + 0.02, gy - 0.047, 0.98)), 0.008, Z_GALV, 6)
    T.box(LATCH_X - 0.027, LATCH_X + 0.005, gy - 0.065, gy - 0.030, 0.98, 1.12, Z_GALV)          # keeper on the post
    Gm = kb('IX_TrafoGate_91_Mesh', 'chainlink')
    chain_quad(Gm, 'y', gy, g['x0'] + 0.035, g['x1'] - 0.02, g['z0'] + 0.03, g['z1'] - 0.02)        # clear of the hinge collars
    Gb = kb('IX_TrafoGate_91_Barbed', 'barbed')
    barbed_band(Gb, 'y', gy, g['x0'], g['x1'], g['z1'] + 0.03)
    Gs = kb('IX_TrafoGate_91_Sign', 'panel')
    sx = (g['x0'] + g['x1']) / 2
    G.box(sx - 0.21, sx + 0.21, gy - 0.026, gy - 0.018, 1.30, 1.62, Z_GALV)
    quad(Gs, (sx, gy - 0.028, 1.46), (0, -1, 0), 0.40, 0.307, uv('sign_hv'))
    part('IX_TrafoGate_91', 'hinge', GATE_PIV, (0, 0, -1), (0, 100), parent='Trafo', states=['shut', 'open'],
         note='the transformer gate: opens outward 0..100 (Update 3: same name, pivot and travel; not locked)')
    for n_ in ('IX_TrafoGate_91_Mesh', 'IX_TrafoGate_91_Barbed', 'IX_TrafoGate_91_Sign'):
        part(n_, 'static', GATE_PIV + Vector((0.77, 0, 1.2)), parent='IX_TrafoGate_91', note={
            'IX_TrafoGate_91_Mesh': 'chain-link of the gate (M_Yard_ChainLink)',
            'IX_TrafoGate_91_Barbed': 'barbed wire over the gate (M_Yard_Barbed)',
            'IX_TrafoGate_91_Sign': 'HOCHSPANNUNG — LEBENSGEFAHR / HIGH VOLTAGE — DANGER OF DEATH on the gate'}[n_])


def pole():
    T = kb('Trafo', 'Trafo')
    p = POLE
    prof = [(z, pole_r(z)) for z in (-0.30, 0.0, 2.0, 4.5, 7.0, POLE_TOP)]
    T.lathe(Vector((p.x, p.y, 0.0)), (0, 0, 1), [(z, r) for z, r in prof], Z_POLE, 10, cap0=False)
    T.lathe(Vector((p.x, p.y, POLE_TOP)), (0, 0, 1), [(0.0, pole_r(POLE_TOP) + 0.01), (0.03, pole_r(POLE_TOP) + 0.01),
                                                       (0.06, 0.0)], Z_GALV, 12, cap0=False)        # the cap
    za, zb = XARM_Z                                                          # the top crossarm (wood) and its braces
    box6(T, (-1.25, p.y - 0.05, za), (1.25, p.y + 0.05, zb), Z_POLE)
    for sg in (-1, 1):
        T.strip([Vector((sg * 0.72, p.y - 0.056, za)), Vector((sg * 0.06, p.y - 0.056, 7.62))], Vector((0, -1, 0)), 0.04,
                0.008, Z_GALV)
    for x in INSUL_X:                                                        # pin insulators: steel pin, brown porcelain
        T.cyl(Vector((x, p.y, zb)), Vector((x, p.y, zb + 0.05)), 0.014, Z_GALV, 6)
        T.lathe(Vector((x, p.y, zb + 0.04)), (0, 0, 1), [(0.0, 0.03), (0.0, 0.07), (0.015, 0.07), (0.03, 0.045), (0.07, 0.045),
                                                         (0.08, 0.062), (0.095, 0.062), (0.11, 0.035), (0.115, 0.035),
                                                         (0.115, 0.0)], Z_PORC, 10, cap0=True)
    # the lower crossarm (galvanised angle) with the three fuse cutouts, the arresters' bracket below
    fy = p.y - pole_r(CUT_Z) - 0.025
    box6(T, (-0.78, fy - 0.025, CUT_Z - 0.06), (0.78, fy + 0.025, CUT_Z), Z_GALV)
    box6(T, (-0.68, fy - 0.025, ARR_Z - 0.05), (0.68, fy + 0.025, ARR_Z), Z_GALV)
    for x in CUT_X:
        T.box(x - 0.02, x + 0.02, CUT_Y + 0.02, fy - 0.025, CUT_Z - 0.10, CUT_Z - 0.06, Z_GALV)
        T.lathe(Vector((x, CUT_Y + 0.04, CUT_Z - 0.10)), (0, 0, -1), [(0.0, 0.03), (0.02, 0.045), (0.04, 0.03), (0.07, 0.045),
                                                                      (0.09, 0.03), (0.12, 0.045), (0.14, 0.03), (0.16, 0.0)],
                Z_PORCG, 10, cap0=True)
        a, b = Vector((x, CUT_Y - 0.02, CUT_Z - 0.06)), Vector((x, CUT_Y - 0.10, CUT_Z - 0.38))
        T.cyl(a, b, 0.022, Z_CABLE, 8)                                       # the fuse tube, swung out a little
        T.box(x - 0.02, x + 0.02, CUT_Y - 0.03, CUT_Y + 0.05, CUT_Z - 0.06, CUT_Z - 0.04, Z_COPPER)
        T.box(x - 0.02, x + 0.02, CUT_Y - 0.12, CUT_Y + 0.05, CUT_Z - 0.40, CUT_Z - 0.38, Z_COPPER)
        T.box(x - 0.02, x + 0.02, CUT_Y + 0.02, fy - 0.025, ARR_Z - 0.04, ARR_Z, Z_GALV)
        T.lathe(Vector((x, CUT_Y + 0.04, ARR_Z)), (0, 0, 1), [(0.0, 0.035), (0.02, 0.05), (0.05, 0.035), (0.08, 0.05),
                                                              (0.11, 0.035), (0.14, 0.05), (0.17, 0.035), (0.20, 0.03),
                                                              (0.20, 0.0)], Z_PORCG, 10, cap0=True)
    # jumpers: the line insulators down to the cutouts, the cutouts to the arresters and on down to the bushings
    for xi, xc, xb in zip(INSUL_X, CUT_X, HV_X):
        T.tube([Vector((xi, p.y, INSUL_TOP + 0.005)), Vector((xi, p.y - 0.09, INSUL_TOP - 0.045)),
                Vector((xi * 0.8 + xc * 0.2, p.y - 0.14, 7.4)), Vector((xc, CUT_Y - 0.02, CUT_Z - 0.03))], 0.006, Z_COPPER, 5)
        T.tube([Vector((xc, CUT_Y - 0.11, CUT_Z - 0.39)), Vector((xc, CUT_Y + 0.0, ARR_Z + 0.28)),
                Vector((xc, CUT_Y + 0.04, ARR_Z + 0.205))], 0.005, Z_COPPER, 5)
        mid = Vector(((xc + xb) / 2, (CUT_Y + HV_Y) / 2, (CUT_Z - 0.40 + HV_TOP) / 2 - 0.35))
        T.tube([Vector((xc, CUT_Y - 0.12, CUT_Z - 0.40)), mid, Vector((xb, HV_Y, HV_TOP + 0.02))], 0.006, Z_COPPER, 5)
    T.tube([Vector((CUT_X[0], CUT_Y + 0.04, ARR_Z - 0.05)), Vector((-0.04, p.y - pole_r(4.0) - 0.01, 4.0)),
            Vector((-0.04, p.y - pole_r(0.5) - 0.01, 0.5)), Vector((-0.04, p.y - pole_r(0.0) - 0.01, -0.05))], 0.005, Z_COPPER, 5)
    for zz in (0.4, 1.2, 2.0, 2.8, 3.6):                                     # staples on the earth wire
        T.box(-0.055, -0.025, p.y - pole_r(zz) - 0.02, p.y - pole_r(zz) + 0.005, zz - 0.006, zz + 0.006, Z_GALV)


def trafo_signs_props():
    S = kb('Trafo_Signs', 'panel')
    Pr = kb('Trafo_Props', 'YardProps')
    # the fence sign (front right), the pole's arrow plate and number, the rating plate, the oil dial, the cabinet sticker
    box6(kb('Trafo', 'Trafo'), (0.58, FY0 - 0.026, 1.36), (1.10, FY0 - 0.018, 1.62), Z_GALV)
    quad(S, (0.84, FY0 - 0.028, 1.49), (0, -1, 0), 0.50, 0.25, uv('sign_noentry'))
    Tk = kb('Trafo', 'Trafo')
    for zc, w, h, key in ((2.60, 0.12, 0.20, 'plate_bolt'), (2.32, 0.10, 0.05, 'plate_pole')):
        py = POLE.y - pole_r(zc) - 0.016                                       # nailed on with spacers, 1.6 cm off the pole
        box6(Tk, (-w / 2 - 0.004, py + 0.002, zc - h / 2 - 0.004), (w / 2 + 0.004, py + 0.010, zc + h / 2 + 0.004), K.Z_GALV)
        quad(S, (0.0, py, zc), (0, -1, 0), w, h, uv(key))
    quad(S, (TK['x1'] + 0.003, 0.30, 0.95), (1, 0, 0), 0.20, 0.14, uv('plate_trafo'))
    quad(S, (CONS['x0'] - 0.048, CONS['y'], CONS['z']), (-1, 0, 0), 0.07, 0.07, uv('gauge_oil'))
    quad(S, ((CAB['x0'] + CAB['x1']) / 2 - 0.17, CAB['y0'] + 0.008, 1.06), (0, -1, 0), 0.25, 0.125, uv('plate_cab'))
    part('Trafo_Signs', 'static', (0, 0, 1.5), parent='Trafo',
         note='panel decals: the fence sign, the pole\'s arrow plate and number, the rating plate, the oil dial, the cabinet sticker')
    # the silica-gel breather (glass, orange crystals) under the conservator's pipe, the cabinet's lock, an open padlock
    bx, by = CONS['x1'] + 0.32, CONS['y']
    Pr.cyl(Vector((bx, by, 1.36)), Vector((bx, by, 1.33)), 0.045, Z_CAP, 10)
    Pr.cyl(Vector((bx, by, 1.33)), Vector((bx, by, 1.20)), 0.038, Z_BREATH, 10)
    Pr.cyl(Vector((bx, by, 1.20)), Vector((bx, by, 1.17)), 0.045, Z_CAP, 10)
    Pr.cyl(Vector((bx, by, 1.17)), Vector((bx, by, 1.12)), 0.03, Z_BREATH, 8)
    VM.rbox(Pr, ((CAB['x0'] + CAB['x1']) / 2 + 0.06, CAB['y0'] + 0.006, 0.86), (0.03, 0.012, 0.05), Z_LOCK, r=0.004, ch=0.002)
    lk = Vector((LATCH_X - 0.01, FY0 - 0.085, 0.93))                           # the open padlock hung on the keeper
    VM.rbox(Pr, lk, (0.045, 0.022, 0.05), Z_LOCK, r=0.006, ch=0.003)
    Pr.tube([lk + Vector((-0.012, 0, 0.025)), lk + Vector((-0.012, 0, 0.06)), lk + Vector((0.004, 0, 0.075)),
             lk + Vector((0.016, 0, 0.065))], 0.004, Z_CAP, 5)
    VM.rbox(Pr, (TK['x1'] + 0.04, 0.15, TK['z0'] + 0.06), (0.06, 0.05, 0.05), Z_CAP, r=0.008, ch=0.004)   # drain valve
    Pr.tube([Vector((TK['x0'], 0.50, TK['z0'] + 0.02)), Vector((-0.80, 0.52, PAD_TOP + 0.01)), Vector((-1.10, 0.52, PAD_TOP + 0.01))],
            0.007, Z_EARTH, 5)
    part('Trafo_Props', 'static', (0, 0, 1.0), parent='Trafo',
         note='small things: the silica-gel breather, the cabinet lock, the open padlock on the gate keeper, the drain valve, '
              'the earth lead')


def trafo_points():
    socket('Hand_TrafoGate', (GATE['x1'] - 0.01, FY0 - 0.06, 1.06), 'hand', parent='IX_TrafoGate_91',
           note='lift the drop latch and swing the gate out (not locked; the open padlock hangs on the keeper)')
    socket('Audio_TrafoHum', (0.0, 0.30, 1.0), 'audio', parent='Trafo',
           note='the transformer hums when the line is live (silent in the prologue: the station runs on the generator)')
    socket('Audio_TrafoGate', (GATE['x0'], FY0, 1.2), 'audio', parent='IX_TrafoGate_91', note='the gate\'s hinges squeal')
    socket('VFX_Arc_Cutouts', (0.0, CUT_Y - 0.05, CUT_Z - 0.22), 'vfx', parent='Trafo', dir=(0, -1, 0),
           note='flash and bang at the fuse cutouts on the pole (a storm, the line coming back)')
    socket('Audio_Wires', (0.0, POLE.y, INSUL_TOP), 'audio', parent='Trafo', note='the wires sing in the wind; insulators crackle in rain')
    socket('Hide_Trafo', (0.0, 1.28, PAD_TOP), 'hide', parent='Trafo',
           note='behind the transformer inside the fence, under the conservator')


def trafo_colliders():
    return [('Trafo_Pad', 'Trafo', (*PAD, PAD_BOT, PAD_TOP), None),
            ('Fence_Front_L', 'Trafo', (FX[0] - 0.03, HINGE_X + 0.03, FY0 - 0.03, FY0 + 0.03, PAD_TOP, FZ1 + 0.40), None),
            ('Fence_Front_R', 'Trafo', (LATCH_X - 0.03, FX[1] + 0.03, FY0 - 0.03, FY0 + 0.03, PAD_TOP, FZ1 + 0.40), None),
            ('Fence_Right', 'Trafo', (FX[1] - 0.03, FX[1] + 0.03, FY0, FY1, PAD_TOP, FZ1 + 0.40), None),
            ('Fence_Back', 'Trafo', (FX[0] - 0.03, FX[1] + 0.03, FY1 - 0.03, FY1 + 0.03, PAD_TOP, FZ1 + 0.40), None),
            ('Fence_Left', 'Trafo', (FX[0] - 0.03, FX[0] + 0.03, FY0, FY1, PAD_TOP, FZ1 + 0.40), None),
            ('Gate_Leaf', 'IX_TrafoGate_91', (GATE['x0'], GATE['x1'] + 0.02, FY0 - 0.025, FY0 + 0.02, GATE['z0'], GATE['z1'] + 0.37),
             None),
            ('Transformer', 'Trafo', (-0.70, 0.70, TK['y0'] - 0.21, TK['y1'] + 0.21, PAD_TOP, CONS['z'] + CONS['r']), None),
            ('Cabinet', 'Trafo', (CAB['x0'] - 0.02, CAB['x1'] + 0.02, CAB['y0'] - 0.03, CAB['y1'] + 0.02, PAD_TOP, CAB['z1'] + 0.05),
             None),
            ('Pole', 'Trafo', (POLE.x - POLE_R0, POLE.x + POLE_R0, POLE.y - POLE_R0, POLE.y + POLE_R0, -0.30, POLE_TOP), None)]


def trafo_knock_rays():
    return [('Knock_Trafo_L', (-1.6, 0.30, 0.95), (1, 0, 0)), ('Knock_Trafo_R', (1.6, 0.25, 0.80), (-1, 0, 0)),
            ('Knock_Trafo_Lid', (0.20, 0.20, 2.4), (0, 0, -1)), ('Knock_Cabinet', ((CAB['x0'] + CAB['x1']) / 2, 0.6, 0.80), (0, 1, 0)),
            ('Knock_Cabinet_Top', ((CAB['x0'] + CAB['x1']) / 2, (CAB['y0'] + CAB['y1']) / 2, 2.0), (0, 0, -1))]


# ================================================================ assembly
ROOTS = ('FuelTanks', 'Trafo')


def root_of(name):
    p = CONTRACT['parts'][name]
    while p.get('parent'):
        name = p['parent']
        p = CONTRACT['parts'][name]
    return name


def static_boxes():
    """(name, parent, (x0, x1, y0, y1, z0, z1) in the parent's root frame, rotation or None, root)"""
    return [(n, par, b, r, 'FuelTanks') for n, par, b, r in fuel_colliders()] + \
           [(n, par, b, r, 'Trafo') for n, par, b, r in trafo_colliders()]


def knock_rays():
    return [(n, o, d, 'FuelTanks') for n, o, d in fuel_knock_rays()] + [(n, o, d, 'Trafo') for n, o, d in trafo_knock_rays()]


def build_yard():
    for d in (KBS, K.ATLAS, CONTRACT['parts'], CONTRACT['sockets']):
        d.clear()
    K.LAMPS.clear()
    bund()
    for name, yc in TANK_Y.items():
        tank(name, yc)
    fill_lines()
    suction_line()
    pump_and_tray()
    stile_and_ladder()
    board_and_extinguisher()
    fittings_props()
    part('FuelTanks', 'static', (0, 0, 0), parent=None,
         note='the fuel tanks: the bund, two tanks on their saddles, the lines, the stile and the ladder, the signboard '
              '(Update 3: the map\'s FuelTanks prefab, same place)')
    part('FuelTanks_Props', 'static', (0, 0, 0.5), parent='FuelTanks',
         note='small things: the outlet valve, the fill couplings and caps, the level dials, the overfill socket, the drain '
              'valve with its padlock, the extinguisher, the earth leads')
    part('FuelTanks_Signs', 'static', (0, -3.6, 1.0), parent='FuelTanks',
         note='panel decals: the signboard, FILL T1 / T2, the dials, the GHS flame, the pump\'s plate, the tanks\' name plate, '
              'the extinguisher sign')
    fuel_points()
    trafo_pad()
    transformer()
    cabinet()
    fence()
    pole()
    trafo_signs_props()
    part('Trafo', 'static', (0, 0, 0), parent=None,
         note='the transformer station: pad, transformer, cabinet, fence, the pole (Update 3: the map\'s Trafo prefab, same place)')
    trafo_points()
    for n in CONTRACT['parts']:
        CONTRACT['parts'][n]['root'] = root_of(n)
    for s in CONTRACT['sockets'].values():
        s['root'] = root_of(s['parent'])
