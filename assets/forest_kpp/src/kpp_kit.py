"""Checkpoint (KPP) at the station gate, Forest map prologue (Forest_Opening.json S6, X05): the Update 3 guard booth, barrier
and sliding gate rebuilt in the generator shed's construction and finishes, the booth in grey-green paint (the station colour).
  booth (root Checkpoint): concrete pad with yellow-black bollards; board-and-batten walls with white trims and corner boards;
  a mono-pitch corrugated roof falling to the back on open spruce rafters, white fascia and barge boards, the KONTROLLPUNKT /
  CHECKPOINT board on the front fascia; a ribbon window of three lights in the front, the road-side window with the pass sash
  (IX_BoothWindow_302) between two fixed panes and a counter board outside, one window on the left (it watches the walkway
  past the booth); the door in the back (IX_BoothDoor_74) hung outside on strap hinges like the shed's, boarded, a white Z
  frame, glazed above; the phone bell, the CCTV camera and the caged bulkhead outside; inside the shed's birch-ply lining,
  open rafters, a concrete floor; the L desk (front and road side) with the drawer unit (IX_Drawer_75..77), the grey filing
  cabinet (IX_Drawer_78..80), the key cabinet (IX_KeyBoxDoor_303) with five labelled hooks (the game's four keys hang there,
  the Stationsleiter hook is empty), the corkboard, the radio, the CCTV monitor, the rotary phone, the swivel chair, hi-vis
  vests, the extinguisher, a convector heater, the wall clock (stopped at 2:40), the flickering fluorescent batten;
  barrier (root Barrier, 7 m out on the road): concrete foot, a post beside the boom, the striped boom with its counterweight
  (IX_BarrierArm_82, lifts 0..80), the rest post with the fork and the two eyes the game's padlock locks together;
  gate (root Gate, beside the booth): a ground-rail sliding leaf (IX_Gate_81, 6.6 m) running 0.22 m inside the fence line on
  two V wheels, guided at the top by two roller posts, chain-link infill (tiled alpha material), barbed wire, the SPERRGEBIET
  sign; the receiving post with its catch, the end stop, a fixed fence panel that closes the line to the map's fence.
Frame (the Update 3 Checkpoint prefab's): x toward the road, y toward the back (the door, the station side), z up, metres;
origin = the middle of the pad on the ground; floor z = 0.15.  Unity: (x, y, z) -> (-x, z, -y), angle -> -angle."""
import math
from math import ceil as math_ceil
from mathutils import Vector, Matrix
import van3_mech as VM
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, prism_x, prism_y, wall_grid, quad, transform_kb, KBS, CONTRACT, LAMPS
from gen_kit import (Z_SLAB, Z_FLOOR, Z_CLAD, Z_TRIMW, Z_LINING, Z_TIMBER, Z_ROOF, Z_ROOFUNDER, Z_DOOR, Z_DOORIN, Z_STEELBLK,
                     Z_GALV, Z_ENAMEL_IN)
from van2_kit import ZERO
import kpp_tex as KT

uv = KT.uv
TAU = 2 * math.pi

# ---------------------------------------------------------------- dimensions (booth frame)
FLOOR = 0.15
PAD = (-3.05, 3.05, -2.55, 2.55)                       # concrete pad, top = floor
PAD_Z0 = -0.25                                         # its sides go a little into the ground (the ground is ~-0.15 round it)
X0, X1, Y0, Y1 = -2.10, 2.10, -1.60, 1.60              # booth outer faces
T = 0.12
IX0, IX1, IY0, IY1 = X0 + T, X1 - T, Y0 + T, Y1 - T    # room 3.96 x 2.96
PITCH = math.radians(5.0)                              # mono-pitch: high at the front (-y), falls to the back
TP, CP, SP = math.tan(PITCH), math.cos(PITCH), math.sin(PITCH)
ZF = 2.85                                              # rafter bottom over the front outer face
OV_F, OV_B, OV_S = 0.45, 0.35, 0.40
YF, YB, XS = Y0 - OV_F, Y1 + OV_B, X1 + OV_S
RAFT_D, RAFT_W, PURL, SHEET = 0.14, 0.05, 0.04, 0.025
RAFTERS = [-1.95, -1.30, -0.65, 0.0, 0.65, 1.30, 1.95]
PURLINS = [-1.95, -1.40, -0.85, -0.30, 0.25, 0.80, 1.35, 1.85]
WZ0, WZ1 = 1.20, 2.35                                  # window band (sill / head)
WIN_F = (-1.82, 1.82)                                  # front ribbon window, three lights
WIN_R = (-1.45, 0.35)                                  # road side: fixed | pass | fixed
PASS = (-0.86, -0.32)                                  # the pass opening in the outer plane
SASH = (-0.88, -0.30)                                  # the sash behind it (slides 0.54 toward the front)
WIN_L = (-0.60, 0.60)                                  # left side
DOOR = dict(x0=0.46, x1=1.35, z0=FLOOR, z1=2.20)       # opening in the back wall
LEAF = dict(x0=0.44, x1=1.37, y0=Y1 + 0.004, y1=Y1 + 0.054, z0=FLOOR + 0.012, z1=2.222)   # hung on the outside face
DOOR_PIV = Vector((1.375, Y1 + 0.060, 1.20))
DESK_TOP = 0.90
DESK_F = (IX0, 1.38, IY0, -0.88)                       # front desk x0, x1, y0, y1 (the road desk owns the corner)
DESK_R = (1.38, IX1, IY0, 0.96)
DRAW = dict(x0=1.40, x1=IX1, y0=0.53, y1=0.96)         # drawer unit under the road desk (fronts face -x)
CAB = dict(x0=IX0, x1=-1.38, y0=0.97, y1=1.44, z1=1.20)   # filing cabinet in the back-left corner (fronts face +x)
KEYBOX = dict(x0=-0.77, x1=-0.25, y0=1.43, y1=IY1, z0=1.53, z1=2.07)   # Update 3's place; door hinge at x0
HOOKS = [('Schranke', -0.70), ('Hauptgebaeude', -0.60), ('Garage', -0.50), ('Generator', -0.40), ('Stationsleiter', -0.30)]
HOOK_Y, HOOK_Z = 1.473, 1.95                           # the keys' hanging points (Forest_Opening.json)
HEATER = dict(y0=-0.80, y1=-0.10, z0=0.26, z1=0.68)
PHONE = Vector((1.67, -0.55, DESK_TOP))                # zone Phone_KPP (Update 3)
NOTE = Vector((1.62, 0.15, 0.902))                     # Note_KPPLog spawns here
BELL = Vector((2.19, 1.00, 2.60))                      # X05 bell (Update 3)
FLUOR = Vector((-0.30, 0.10, 2.65))                    # the batten's middle (under the rafters)
LIGHT_FLUOR = Vector((-0.30, 0.10, 2.56))
BULK = Vector((0.905, Y1, 2.44))                       # bulkhead plate over the door
CLOCK = Vector((0.10, IY1, 2.02))
CHAIR = Vector((0.68, -0.45, FLOOR))
MONITOR = Vector((-1.05, -1.25, DESK_TOP))
RADIO = Vector((0.80, -1.34, DESK_TOP))
BARRIER_PLACE = (Vector((3.10, -7.00, -0.3867)), 0.0)  # Update 3 layout, in this frame (yaw 0: the roots share the axes)
GATE_PLACE = (Vector((11.00, 0.00, -0.3772)), 0.0)
BOOM_PIV = Vector((0.0, 0.0, 1.17))                    # barrier frame
BOOM_LEN = 6.0
PADLOCK = Vector((5.85, 0.0, 1.015))                   # barrier frame: the padlock's hanging point (Update 3 data)
EYE = Vector((5.85, 0.0, 1.026))                       # the two eyes' common axis (along y)
REST_X = 5.60                                          # the boom's rest post, 0.25 m in from the eyes: the lock hangs free
LEAF_Y = 0.22                                          # gate frame: the leaf runs 0.22 m inside the fence line
GATE_LEAF = (-7.00, 0.00)                              # closed
GATE_Z = (0.16, 2.00)                                  # leaf frame bottom / top
GATE_TRAVEL = 6.6
FENCE_X = (0.20, 2.40)                                 # gate frame: the fixed panel's posts

# ---------------------------------------------------------------- zones.  Kpp atlas: the shed's where the finish is the
# shed's, then the KPP's own; KppProps atlas: the small things
(Z_BOLLARD, Z_DESK, Z_CABGREY, Z_KEYBOX, Z_CORK, Z_BOOM, Z_BARPOST, Z_HEATER, Z_RUBBER_K, Z_GATEROLL, Z_CONC,
 Z_BARBED) = range(140, 152)                           # Kpp (the booth) and KppYard (the barrier and the gate) share them
KPP_ZONES = [Z_SLAB, Z_FLOOR, Z_CLAD, Z_TRIMW, Z_LINING, Z_TIMBER, Z_ROOF, Z_ROOFUNDER, Z_DOOR, Z_DOORIN, Z_STEELBLK, Z_GALV,
             Z_ENAMEL_IN] + list(range(140, 152))
(Z_PHONE, Z_VEST, Z_EXTP, Z_CRT, Z_CHAIR, Z_BLACKP, Z_BELLP, Z_PAPERP, Z_MUGP, Z_FLASK, Z_BINDER, Z_RADIO, Z_CAMP,
 Z_CHROMEP, Z_FAID) = range(170, 185)
PROP_ZONES = list(range(170, 185))
FAID = dict(x0=-0.05, x1=0.25, y0=IY1 - 0.10, z0=1.38, z1=1.62)     # first-aid box under the clock


def z_rb(y):
    """rafter bottom line at y (falls toward +y)"""
    return ZF - (y - Y0) * TP


def z_rt(y):
    return z_rb(y) + RAFT_D / CP


def z_sb(y):
    return z_rb(y) + (RAFT_D + PURL) / CP


def z_st(y):
    return z_sb(y) + SHEET / CP


ZS = z_rb(IY1)                                          # side walls: full grid cells up to here, a wedge above
ZTOP_F = ZF                                             # front wall top (= rafter bottom at its outer face)
ZTOP_B = z_rb(IY1)                                      # back wall top (= rafter bottom at its inner face)


# ================================================================ helpers
def uv_cyl(k, c, h0, h1, rect, axis=(0, 0, 1)):
    """cylindrical UVs for every face of k (lens lathes): u round the axis, v along it from h0 to h1"""
    c, ax = Vector(c), Vector(axis).normalized()
    e1 = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))
    e1 = (e1 - ax * e1.dot(ax)).normalized()
    e2 = ax.cross(e1)
    u0, v0, u1, v1 = rect
    for f in k.bm.faces:
        for l in f.loops:
            d = l.vert.co - c
            a = (math.atan2(d.dot(e2), d.dot(e1)) / TAU) % 1.0
            t = min(max((d.dot(ax) - h0) / (h1 - h0), 0.0), 1.0)
            l[k.uvl].uv = (u0 + (u1 - u0) * (0.05 + 0.9 * a), v0 + (v1 - v0) * t)


def ring(k, c, axis, R, r, zone, seg=10, tseg=5):
    """closed wire ring (torus) of radius R, wire radius r, about `axis` through c"""
    c, ax = Vector(c), Vector(axis).normalized()
    e1 = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 0, 1))
    e1 = (e1 - ax * e1.dot(ax)).normalized()
    e2 = ax.cross(e1)
    pts = [c + (e1 * math.cos(TAU * i / seg) + e2 * math.sin(TAU * i / seg)) * R for i in range(seg + 1)]
    k.tube(pts, r, zone, tseg, caps=False)


def lights_of(u0, u1, n, fw=0.045, mw=0.09):
    """clear spans of n lights in an opening u0..u1 (stiles fw at the ends, mullions mw between)"""
    w = (u1 - u0 - 2 * fw - (n - 1) * mw) / n
    a, out = u0 + fw, []
    for _ in range(n):
        out.append((a, a + w))
        a += w + mw
    return out


class WallBox:
    """boxes in wall coordinates: a across the wall, u along it, z up (axis = the wall's normal axis)"""

    def __init__(self, k, axis):
        self.k, self.axis = k, axis
        self.A, self.U = ('y', 'x') if axis == 'y' else ('x', 'y')

    def S(self, *names):                              # '+a', '-u', '+z' -> box6 face keys
        return tuple(n[0] + {'a': self.A, 'u': self.U, 'z': 'z'}[n[1]] for n in names)

    def P(self, a, u, z):
        return Vector((u, a, z)) if self.axis == 'y' else Vector((a, u, z))

    def box(self, ua, ub, za, zb, aa, ab, zone=Z_TRIMW, skip=(), k=None):
        lo = self.P(min(aa, ab), min(ua, ub), za)
        hi = self.P(max(aa, ab), max(ua, ub), zb)
        box6(k or self.k, tuple(lo), tuple(hi), zone, skip=self.S(*skip))

    def glass(self, g, a, ua, ub, za, zb):
        n = Vector((0, 1, 0)) if self.axis == 'y' else Vector((1, 0, 0))
        for d, s in ((-0.0005, -1), (0.0005, 1)):
            face(g, [self.P(a + d, ua, za), self.P(a + d, ub, za), self.P(a + d, ub, zb), self.P(a + d, ua, zb)], ZERO, n * s)


def window(k, g, axis, a_out, a_in, u0, u1, z0, z1, out_sign, n=1, cross=True):
    """the shed's window: a white frame in the opening (mullions between n lights, a glazing cross in each), panes to the
    glass KB g, white outside trims and sill, a spruce sill inside"""
    W = WallBox(k, axis)
    fw = 0.045
    lo_a, hi_a = sorted((a_out, a_in))
    f0, f1 = lo_a + 0.02, hi_a - 0.02
    am = (f0 + f1) / 2
    W.box(u0, u1, z0, z0 + fw, f0, f1, skip=('-z',))
    W.box(u0, u1, z1 - fw, z1, f0, f1, skip=('+z',))
    W.box(u0, u0 + fw, z0 + fw, z1 - fw, f0, f1, skip=('-u', '-z', '+z'))
    W.box(u1 - fw, u1, z0 + fw, z1 - fw, f0, f1, skip=('+u', '-z', '+z'))
    L = lights_of(u0, u1, n, fw)
    for (_, ma), (mb, _) in zip(L[:-1], L[1:]):
        W.box(ma, mb, z0 + fw, z1 - fw, f0, f1, skip=('-z', '+z'))
    zc = (z0 + z1) / 2
    for la, lb in L:
        if cross:
            uc = (la + lb) / 2
            W.box(uc - 0.015, uc + 0.015, z0 + fw, z1 - fw, am - 0.015, am + 0.015, skip=('-z', '+z'))
            W.box(la, lb, zc - 0.015, zc + 0.015, am - 0.012, am + 0.012, skip=('-u', '+u'))
        W.glass(g, am, la, lb, z0 + fw, z1 - fw)
    t0, t1 = sorted((a_out, a_out + out_sign * 0.022))
    into = '+a' if out_sign < 0 else '-a'                 # the trims' face against the cladding
    W.box(u0 - 0.07, u1 + 0.07, z1, z1 + 0.07, t0, t1, skip=(into,))
    W.box(u0 - 0.07, u0, z0, z1, t0, t1, skip=(into, '-z', '+z'))
    W.box(u1, u1 + 0.07, z0, z1, t0, t1, skip=(into, '-z', '+z'))
    s0, s1 = sorted((a_out, a_out + out_sign * 0.06))
    W.box(u0 - 0.09, u1 + 0.09, z0 - 0.035, z0, s0, s1, skip=(into,))
    i0, i1 = sorted((a_in, a_in - out_sign * 0.05))
    W.box(u0 - 0.03, u1 + 0.03, z0 - 0.03, z0, i0, i1, zone=Z_TIMBER, skip=('-a' if out_sign < 0 else '+a',))


# ================================================================ the booth shell
def shell():
    k = kb('Checkpoint', 'Kpp')
    g = kb('Window_Glass', 'glass')
    wz = dict(out=Z_CLAD, reveal=Z_TIMBER, end=Z_CLAD, top=Z_TIMBER, **{'in': Z_LINING})
    # concrete pad: sides (into the ground), the top round the booth, the floor inside, the threshold
    x0, x1, y0, y1 = PAD
    box6(k, (x0, y0, PAD_Z0), (x1, y1, FLOOR), Z_SLAB, skip=('-z', '+z'))
    for lo, hi in (((x0, y0), (x1, Y0)), ((x0, Y1), (x1, y1)), ((x0, Y0), (X0, Y1)), ((X1, Y0), (x1, Y1))):
        face(k, [(lo[0], lo[1], FLOOR), (hi[0], lo[1], FLOOR), (hi[0], hi[1], FLOOR), (lo[0], hi[1], FLOOR)], Z_SLAB, (0, 0, 1))
    xs, ys = [IX0, -0.66, 0.66, IX1], [IY0, 0.0, IY1]
    for i in range(3):
        for j in range(2):
            face(k, [(xs[i], ys[j], FLOOR), (xs[i + 1], ys[j], FLOOR), (xs[i + 1], ys[j + 1], FLOOR), (xs[i], ys[j + 1], FLOOR)],
                 Z_FLOOR, (0, 0, 1))
    face(k, [(DOOR['x0'], IY1, FLOOR), (DOOR['x1'], IY1, FLOOR), (DOOR['x1'], Y1, FLOOR), (DOOR['x0'], Y1, FLOOR)], Z_FLOOR, (0, 0, 1))
    # walls: front (the ribbon window), back (the door), the road side, the left side
    wall_grid(k, 'y', Y0, IY0, [X0, WIN_F[0], WIN_F[1], X1], [FLOOR, WZ0, WZ1, ZTOP_F], {(1, 1)}, -1, wz, ends=True, top=True)
    wall_grid(k, 'y', IY1, Y1, [X0, DOOR['x0'], DOOR['x1'], X1], [FLOOR, DOOR['z1'], ZTOP_B], {(1, 0)}, 1, wz, ends=True, top=True)
    wall_grid(k, 'x', IX1, X1, [IY0, WIN_R[0], WIN_R[1], IY1], [FLOOR, WZ0, WZ1, ZS], {(1, 1)}, 1, wz, ends=False, top=False)
    wall_grid(k, 'x', X0, IX0, [IY0, WIN_L[0], WIN_L[1], IY1], [FLOOR, WZ0, WZ1, ZS], {(1, 1)}, -1, wz, ends=False, top=False)
    # the side walls above the grid, up to the sheet (the purlins pass through them)
    poly = [(IY0, ZS), (IY1, ZS), (IY1, z_sb(IY1) - 0.002), (IY0, z_sb(IY0) - 0.002)]
    prism_x(k, poly, IX1, X1, Z_LINING, Z_CLAD, [None, None, None, None])
    prism_x(k, poly, X0, IX0, Z_CLAD, Z_LINING, [None, None, None, None])
    # front and back walls above their tops: blocking between the rafters and a strip over them, up to the sheet
    bays = [(X0, RAFTERS[0] - RAFT_W / 2)] + [(a + RAFT_W / 2, b - RAFT_W / 2) for a, b in zip(RAFTERS[:-1], RAFTERS[1:])] + \
           [(RAFTERS[-1] + RAFT_W / 2, X1)]
    for (ya, yb), zt, e_ya, e_yb in (((Y0, IY0), ZTOP_F, Z_CLAD, Z_LINING), ((IY1, Y1), ZTOP_B, Z_LINING, Z_CLAD)):
        poly = [(ya, zt), (yb, zt), (yb, z_rt(yb)), (ya, z_rt(ya))]
        for xa, xb in bays:
            prism_x(k, poly, xa, xb, Z_CLAD if xa == X0 else None, Z_CLAD if xb == X1 else None, [None, e_yb, None, e_ya])
        poly = [(ya, z_rt(ya)), (yb, z_rt(yb)), (yb, z_sb(yb) - 0.002), (ya, z_sb(ya) - 0.002)]
        prism_x(k, poly, X0, X1, Z_CLAD, Z_CLAD, [None, e_yb, None, e_ya])
    # windows
    window(k, g, 'y', Y0, IY0, WIN_F[0], WIN_F[1], WZ0, WZ1, -1, n=3)
    window(k, g, 'x', X0, IX0, WIN_L[0], WIN_L[1], WZ0, WZ1, -1, n=1)
    road_window(k, g)
    # corner boards (white), up to the sheet
    cb, ct = 0.14, 0.025
    for sx in (-1, 1):
        for sy in (-1, 1):
            xo, yo = (X1 if sx > 0 else X0), (Y1 if sy > 0 else Y0)
            ztop = z_sb(yo) - 0.002
            xa, xb = sorted((xo, xo - sx * cb))
            ya, yb = sorted((yo, yo + sy * ct))
            box6(k, (xa, ya, FLOOR), (xb, yb, ztop), Z_TRIMW, skip=('-z', '+z', '+y' if sy < 0 else '-y'))
            xa, xb = sorted((xo, xo + sx * ct))
            ya, yb = sorted((yo + sy * ct, yo - sy * (cb - ct)))
            box6(k, (xa, ya, FLOOR), (xb, yb, ztop), Z_TRIMW, skip=('-z', '+z', '+x' if sx < 0 else '-x'))
    # door trims (white) beside and over the hung leaf; the pintles of the strap hinges
    for xa, xb in ((0.295, 0.425), (1.39, 1.52)):
        box6(k, (xa, Y1, FLOOR), (xb, Y1 + 0.025, 2.24), Z_TRIMW, skip=('-y', '-z', '+z'))
    box6(k, (0.295, Y1, 2.24), (1.52, Y1 + 0.025, 2.37), Z_TRIMW, skip=('-y',))
    for zh in (0.30, 2.10):
        k.box(1.39, 1.43, Y1 + 0.025, Y1 + 0.058, zh - 0.03, zh + 0.03, Z_STEELBLK)
    roof(k)
    return k


def road_window(k, g):
    """the road-side window: an outer frame plane with two fixed panes and the pass opening between them, an inner plane
    with the sash on two tracks (it slides 0.54 m toward the front behind the left pane); white trims outside (the front
    corner board is the left trim), a counter board on brackets under the pass opening"""
    W = WallBox(k, 'x')
    u0, u1 = WIN_R
    p0, p1 = PASS
    fw = 0.045
    o0, o1 = X1 - 0.065, X1 - 0.02                      # outer plane
    W.box(u0, u1, WZ0, WZ0 + fw, o0, o1, skip=('-z',))
    W.box(u0, u1, WZ1 - fw, WZ1, o0, o1, skip=('+z',))
    W.box(u0, u0 + fw, WZ0 + fw, WZ1 - fw, o0, o1, skip=('-u', '-z', '+z'))
    W.box(u1 - fw, u1, WZ0 + fw, WZ1 - fw, o0, o1, skip=('+u', '-z', '+z'))
    W.box(p0 - fw, p0, WZ0 + fw, WZ1 - fw, o0, o1, skip=('-z', '+z'))
    W.box(p1, p1 + fw, WZ0 + fw, WZ1 - fw, o0, o1, skip=('-z', '+z'))
    am = (o0 + o1) / 2
    zc = (WZ0 + WZ1) / 2
    for la, lb in ((u0 + fw, p0 - fw), (p1 + fw, u1 - fw)):
        W.box(la, lb, zc - 0.015, zc + 0.015, am - 0.012, am + 0.012, skip=('-u', '+u'))
        W.glass(g, am, la, lb, WZ0 + fw, WZ1 - fw)
    # inner plane: the two tracks the sash runs in
    W.box(u0, u1, WZ0, WZ0 + 0.02, IX1 + 0.008, IX1 + 0.050, zone=Z_TIMBER, skip=('-z',))
    W.box(u0, u1, WZ1 - 0.02, WZ1, IX1 + 0.008, IX1 + 0.050, zone=Z_TIMBER, skip=('+z',))
    # trims, sills
    t0, t1 = X1, X1 + 0.022
    W.box(-1.485, u1 + 0.07, WZ1, WZ1 + 0.07, t0, t1, skip=('-a', '-u'))
    W.box(-1.485, u0, WZ0, WZ1, t0, t1, skip=('-a', '-z', '+z', '-u'))   # left: from the corner board to the opening
    W.box(u1, u1 + 0.07, WZ0, WZ1, t0, t1, skip=('-a', '-z', '+z'))
    W.box(-1.485, u1 + 0.09, WZ0 - 0.035, WZ0, X1, X1 + 0.06, skip=('-a',))
    W.box(u0 - 0.03, u1 + 0.03, WZ0 - 0.03, WZ0, IX1 - 0.05, IX1, zone=Z_TIMBER, skip=('+a',))
    # counter board outside under the pass opening, on two brackets
    W.box(p0 - 0.10, p1 + 0.10, WZ0 - 0.065, WZ0 - 0.035, X1, X1 + 0.32, zone=Z_TIMBER, skip=('-a',))
    for yb in (p0 - 0.06, p1 + 0.06):
        k.strip([Vector((X1 + 0.004, yb, WZ0 - 0.30)), Vector((X1 + 0.27, yb, WZ0 - 0.072))], Vector((0, 1, 0)), 0.03, 0.008, Z_STEELBLK)
        k.box(X1, X1 + 0.006, yb - 0.02, yb + 0.02, WZ0 - 0.33, WZ0 - 0.07, Z_STEELBLK)
    # the sash (IX_BoothWindow_302): white frame, a glazing bar, a finger pull on the room side
    S = kb('IX_BoothWindow_302', 'Kpp')
    s0, s1 = IX1 + 0.016, IX1 + 0.042
    sz0, sz1 = WZ0 + 0.025, WZ1 - 0.025
    a0, a1 = SASH
    sw = 0.05
    Ws = WallBox(S, 'x')
    Ws.box(a0, a1, sz0, sz0 + sw, s0, s1)
    Ws.box(a0, a1, sz1 - sw, sz1, s0, s1)
    Ws.box(a0, a0 + sw, sz0 + sw, sz1 - sw, s0, s1, skip=('-z', '+z'))
    Ws.box(a1 - sw, a1, sz0 + sw, sz1 - sw, s0, s1, skip=('-z', '+z'))
    zm = (sz0 + sz1) / 2
    Ws.box(a0 + sw, a1 - sw, zm - 0.015, zm + 0.015, s0 + 0.004, s1 - 0.004, skip=('-u', '+u'))
    S.box(s0 - 0.014, s0, a1 - 0.13, a1 - 0.07, zm - 0.12, zm - 0.06, Z_STEELBLK)
    Sg = kb('IX_BoothWindow_302_Glass', 'glass')
    Ws.glass(Sg, (s0 + s1) / 2, a0 + sw, a1 - sw, sz0 + sw, sz1 - sw)
    part('IX_BoothWindow_302', 'slide', ((s0 + s1) / 2, a0, sz0), (0, -1, 0), (0, 0.54), unit='m', parent='Checkpoint',
         states=['shut', 'open'], note='pass window (Schalterfenster): the sash slides toward the front behind the fixed pane, 0.54 m '
                                       'open (Update 3: same name, axis and travel)')
    part('IX_BoothWindow_302_Glass', 'static', ((s0 + s1) / 2, (a0 + a1) / 2, zm), parent='IX_BoothWindow_302',
         note='the sash pane (glass material)')
    socket('Hand_BoothWindow', (s0 - 0.03, a1 - 0.10, zm - 0.09), 'hand', parent='IX_BoothWindow_302', note='finger pull')


def roof(k):
    """rafters front to back, purlins across, the corrugated sheet (top / underside / edges), white fascia boards front
    and back between white barge boards"""
    for xr in RAFTERS + [-(XS - 0.025), XS - 0.025]:
        poly = [(YF, z_rb(YF)), (YB, z_rb(YB)), (YB, z_rt(YB)), (YF, z_rt(YF))]
        prism_x(k, poly, xr - RAFT_W / 2, xr + RAFT_W / 2, Z_TIMBER, Z_TIMBER, [Z_TIMBER, None, None, None])
    for yp in PURLINS:
        w = 0.025
        poly = [(yp - w, z_rt(yp - w)), (yp + w, z_rt(yp + w)), (yp + w, z_sb(yp + w) - 0.001), (yp - w, z_sb(yp - w) - 0.001)]
        prism_x(k, poly, -XS, XS, None, None, [None, Z_TIMBER, None, Z_TIMBER])
    top = [Vector((-XS, YF, z_st(YF))), Vector((XS, YF, z_st(YF))), Vector((XS, YB, z_st(YB))), Vector((-XS, YB, z_st(YB)))]
    bot = [Vector((-XS, YF, z_sb(YF))), Vector((XS, YF, z_sb(YF))), Vector((XS, YB, z_sb(YB))), Vector((-XS, YB, z_sb(YB)))]
    nrm = Vector((0, SP, CP))
    face(k, top, Z_ROOF, nrm)
    face(k, bot, Z_ROOFUNDER, -nrm)
    # fascia (between the barge boards): the front one carries the sign plate; barge boards over the verges
    box6(k, (-XS, YF - 0.025, z_rb(YF) - 0.03), (XS, YF, z_st(YF) + 0.02), Z_TRIMW, skip=('+y', '-x', '+x'))
    box6(k, (-XS, YB, z_rb(YB) - 0.03), (XS, YB + 0.025, z_st(YB) + 0.02), Z_TRIMW, skip=('-y', '-x', '+x'))
    for sx in (-1, 1):
        xa, xb = sorted((sx * XS, sx * (XS + 0.025)))
        ya, yb = YF - 0.025, YB + 0.025
        poly = [(ya, z_st(ya) + 0.02 - 0.22), (yb, z_st(yb) + 0.02 - 0.22), (yb, z_st(yb) + 0.02), (ya, z_st(ya) + 0.02)]
        prism_x(k, poly, xa, xb, Z_TRIMW, Z_TRIMW)


# ================================================================ the door: hung outside like the shed's, glazed above
def door():
    D = kb('IX_BoothDoor_74', 'Kpp')
    L = LEAF
    x0, x1, ya, yb, zl, zh = L['x0'], L['x1'], L['y0'], L['y1'], L['z0'], L['z1']
    gx0, gx1, gz0, gz1 = x0 + 0.13, x1 - 0.13, 1.40, 2.02             # the glazing
    zones = {'+y': Z_DOOR, '-y': Z_DOORIN, '*': Z_DOOR}
    box6(D, (x0, ya, zl), (x1, yb, gz0), zones)
    box6(D, (x0, ya, gz1), (x1, yb, zh), zones)
    box6(D, (x0, ya, gz0), (gx0, yb, gz1), zones, skip=('-z', '+z'))
    box6(D, (gx1, ya, gz0), (x1, yb, gz1), zones, skip=('-z', '+z'))
    gw = 0.035                                                        # white glazing frame on both faces, a cross
    for y0_, y1_, sk in ((yb, yb + 0.012, '-y'), (ya - 0.012, ya, '+y')):
        box6(D, (gx0 - gw, y0_, gz0 - gw), (gx1 + gw, y1_, gz0), Z_TRIMW, skip=(sk,))
        box6(D, (gx0 - gw, y0_, gz1), (gx1 + gw, y1_, gz1 + gw), Z_TRIMW, skip=(sk,))
        box6(D, (gx0 - gw, y0_, gz0), (gx0, y1_, gz1), Z_TRIMW, skip=(sk, '-z', '+z'))
        box6(D, (gx1, y0_, gz0), (gx1 + gw, y1_, gz1), Z_TRIMW, skip=(sk, '-z', '+z'))
    xm, zm = (gx0 + gx1) / 2, (gz0 + gz1) / 2
    ym = (ya + yb) / 2
    box6(D, (xm - 0.012, ym - 0.012, gz0), (xm + 0.012, ym + 0.012, gz1), Z_TRIMW, skip=('-z', '+z'))
    box6(D, (gx0, ym - 0.010, zm - 0.012), (gx1, ym + 0.010, zm + 0.012), Z_TRIMW, skip=('-x', '+x'))
    G = kb('IX_BoothDoor_74_Glass', 'glass')
    for d, n in ((-0.0005, (0, -1, 0)), (0.0005, (0, 1, 0))):
        face(G, [(gx0, ym + d, gz0), (gx1, ym + d, gz0), (gx1, ym + d, gz1), (gx0, ym + d, gz1)], ZERO, n)
    # white Z frame outside: two ledges and the brace (hinge side low -> latch side high, clear of the handle)
    for z0_ in (0.25, 1.12):
        box6(D, (x0 + 0.03, yb, z0_), (x1 - 0.03, yb + 0.02, z0_ + 0.10), Z_TRIMW, skip=('-y',))
    D.strip([Vector((x1 - 0.10, yb + 0.009, 0.36)), Vector((x0 + 0.34, yb + 0.009, 1.11))], Vector((0, 1, 0)), 0.09, 0.016, Z_TRIMW)
    # strap hinges (black): the lower one over the lower ledge, the upper one on the boards; knuckles on the pivot line
    for zh_, yf in ((0.30, yb + 0.02), (2.10, yb)):
        D.box(x1 - 0.44, DOOR_PIV.x - 0.006, yf + 0.001, yf + 0.007, zh_ - 0.022, zh_ + 0.022, Z_STEELBLK)
        if yf > yb:                                                   # down from the ledge to the knuckle
            D.box(DOOR_PIV.x - 0.012, DOOR_PIV.x - 0.006, DOOR_PIV.y + 0.005, yf + 0.001, zh_ - 0.022, zh_ + 0.022, Z_STEELBLK)
        D.cyl(Vector((DOOR_PIV.x, DOOR_PIV.y, zh_ - 0.03)), Vector((DOOR_PIV.x, DOOR_PIV.y, zh_ + 0.03)), 0.011, Z_STEELBLK, 8)
    hz = 1.00
    for yy, s in ((yb, 1), (ya, -1)):
        D.box(x0 + 0.05, x0 + 0.09, *sorted((yy, yy + s * 0.008)), hz - 0.10, hz + 0.05, Z_STEELBLK)
        D.cyl(Vector((x0 + 0.07, yy + s * 0.008, hz)), Vector((x0 + 0.07, yy + s * 0.045, hz)), 0.008, Z_STEELBLK, 6)
        D.cyl(Vector((x0 + 0.07, yy + s * 0.045, hz)), Vector((x0 + 0.19, yy + s * 0.045, hz)), 0.009, Z_STEELBLK, 6)
    D.box(x0 + 0.03, x0 + 0.14, ya - 0.028, ya - 0.008, hz - 0.12, hz + 0.06, Z_STEELBLK)
    Sg = kb('IX_BoothDoor_74_Sign', 'panel')
    quad(Sg, (0.79, yb + 0.0025, 1.285), (0, 1, 0), 0.30, 0.10, uv('sign_staff'))
    part('IX_BoothDoor_74', 'hinge', DOOR_PIV, (0, 0, -1), (0, 100), parent='Checkpoint', states=['shut', 'open'],
         note='booth door in the back wall, hung outside on strap hinges at its +x edge; opens outward (+) to 100; lever handles both '
              'sides; not locked (Update 3: same name, hinge side and travel)')
    part('IX_BoothDoor_74_Glass', 'static', (xm, ym, zm), parent='IX_BoothDoor_74', note='the door pane (glass material)')
    part('IX_BoothDoor_74_Sign', 'static', (0.79, yb, 1.285), parent='IX_BoothDoor_74',
         note='NUR FÜR PERSONAL / STAFF ONLY plate on the door (panel atlas)')
    socket('Hand_BoothDoor_Out', (x0 + 0.15, yb + 0.07, hz), 'hand', parent='IX_BoothDoor_74', note='lever outside')
    socket('Hand_BoothDoor_In', (x0 + 0.15, ya - 0.07, hz), 'hand', parent='IX_BoothDoor_74', note='lever inside')


# ================================================================ furniture
def furniture():
    k = KBS['Checkpoint']
    t0 = DESK_TOP - 0.03
    # L desk: 30 mm ply tops, an apron along the free edges, legs; the road desk owns the corner
    xa, xb, ya, yb = DESK_F
    box6(k, (xa, ya, t0), (xb, yb, DESK_TOP), Z_DESK, skip=('-x', '+x', '-y'))
    xa2, xb2, ya2, yb2 = DESK_R
    box6(k, (xa2, ya2, t0), (xb2, yb2, DESK_TOP), Z_DESK, skip=('+x', '-y'))
    box6(k, (xa + 0.02, yb - 0.022, t0 - 0.09), (xa2, yb - 0.004, t0), Z_DESK, skip=('+z', '-x', '+x'))
    box6(k, (xa2 + 0.004, yb, t0 - 0.09), (xa2 + 0.022, DRAW['y0'], t0), Z_DESK, skip=('+z', '-y', '+y'))
    for lx, ly in ((xa + 0.04, yb - 0.05), (-0.85, yb - 0.05), (0.30, yb - 0.05), (xa2 + 0.05, -0.84)):
        box6(k, (lx - 0.025, ly - 0.025, FLOOR), (lx + 0.025, ly + 0.025, t0), Z_DESK, skip=('-z', '+z'))
    k.box(xa, xb, IY0, IY0 + 0.03, t0 - 0.06, t0, Z_TIMBER)                       # cleat on the front wall
    # drawer unit (IX_Drawer_75..77 pull toward the room, -x)
    d = DRAW
    for y0_, y1_ in ((d['y0'], d['y0'] + 0.015), (d['y1'] - 0.015, d['y1'])):
        box6(k, (d['x0'], y0_, FLOOR), (d['x1'], y1_, t0), Z_DESK, skip=('-z', '+z', '+x'))
    box6(k, (d['x0'] + 0.02, d['y0'] + 0.015, FLOOR), (d['x1'], d['y1'] - 0.015, 0.185), Z_DESK, skip=('-z', '-y', '+y', '+x'))
    box6(k, (d['x0'], d['y0'] + 0.015, 0.825), (d['x1'], d['y1'] - 0.015, t0), Z_DESK, skip=('+z', '-y', '+y', '+x'))
    ym = (d['y0'] + d['y1']) / 2
    for name, z0, z1 in (('IX_Drawer_75', 0.625, 0.815), ('IX_Drawer_76', 0.415, 0.605), ('IX_Drawer_77', 0.195, 0.405)):
        Dr = kb(name, 'Kpp')
        fx0, fx1 = d['x0'], d['x0'] + 0.02
        box6(Dr, (fx0, d['y0'] + 0.017, z0), (fx1, d['y1'] - 0.017, z1), Z_DESK)
        bx1 = d['x1'] - 0.03
        for y0_, y1_ in ((d['y0'] + 0.03, d['y0'] + 0.042), (d['y1'] - 0.042, d['y1'] - 0.03)):
            box6(Dr, (fx1, y0_, z0 + 0.012), (bx1, y1_, z1 - 0.04), Z_DESK, skip=('-x',))
        box6(Dr, (bx1 - 0.012, d['y0'] + 0.042, z0 + 0.012), (bx1, d['y1'] - 0.042, z1 - 0.04), Z_DESK, skip=('-y', '+y'))
        box6(Dr, (fx1, d['y0'] + 0.042, z0 + 0.012), (bx1 - 0.012, d['y1'] - 0.042, z0 + 0.024), Z_DESK, skip=('-x', '+x', '-y', '+y'))
        Dr.tube([Vector((fx0, ym - 0.05, (z0 + z1) / 2)), Vector((fx0 - 0.03, ym - 0.05, (z0 + z1) / 2)),
                 Vector((fx0 - 0.03, ym + 0.05, (z0 + z1) / 2)), Vector((fx0, ym + 0.05, (z0 + z1) / 2))], 0.006, Z_STEELBLK, 5, caps=False)
        part(name, 'slide', (fx0, ym, z0), (-1, 0, 0), (0, 0.38), unit='m', parent='Checkpoint', states=['shut', 'out'],
             note='desk drawer under the road-side desk: pulls into the room, 0.38 m (Update 3: same name, axis and travel)')
        socket('Hand_' + name[3:], (fx0 - 0.045, ym, (z0 + z1) / 2), 'hand', parent=name)
    # filing cabinet in the back-left corner (IX_Drawer_78..80 pull toward +x); deep enough for the 0.45 m travel
    c = CAB
    for y0_, y1_ in ((c['y0'], c['y0'] + 0.015), (c['y1'] - 0.015, c['y1'])):
        box6(k, (c['x0'], y0_, FLOOR), (c['x1'] - 0.02, y1_, c['z1'] - 0.015), Z_CABGREY, skip=('-z', '+z', '-x'))
    box6(k, (c['x0'], c['y0'], c['z1'] - 0.015), (c['x1'], c['y1'], c['z1']), Z_CABGREY, skip=('-x',))
    box6(k, (c['x0'] + 0.01, c['y0'] + 0.015, FLOOR), (c['x1'] - 0.02, c['y1'] - 0.015, 0.185), Z_CABGREY,
         skip=('-z', '-x', '-y', '+y'))
    cym = (c['y0'] + c['y1']) / 2
    for name, z0, z1 in (('IX_Drawer_78', 0.875, 1.175), ('IX_Drawer_79', 0.535, 0.865), ('IX_Drawer_80', 0.195, 0.525)):
        Dr = kb(name, 'Kpp')
        fx0, fx1 = c['x1'] - 0.02, c['x1']
        box6(Dr, (fx0, c['y0'] + 0.017, z0), (fx1, c['y1'] - 0.017, z1), Z_CABGREY)
        bx0 = c['x0'] + 0.03
        for y0_, y1_ in ((c['y0'] + 0.025, c['y0'] + 0.035), (c['y1'] - 0.035, c['y1'] - 0.025)):
            box6(Dr, (bx0, y0_, z0 + 0.012), (fx0, y1_, z1 - 0.05), Z_CABGREY, skip=('+x',))
        box6(Dr, (bx0, c['y0'] + 0.035, z0 + 0.012), (bx0 + 0.01, c['y1'] - 0.035, z1 - 0.05), Z_CABGREY, skip=('-y', '+y'))
        box6(Dr, (bx0 + 0.01, c['y0'] + 0.035, z0 + 0.012), (fx0, c['y1'] - 0.035, z0 + 0.022), Z_CABGREY, skip=('-x', '+x', '-y', '+y'))
        Dr.box(fx1, fx1 + 0.014, cym - 0.07, cym + 0.07, z1 - 0.075, z1 - 0.055, Z_STEELBLK)
        part(name, 'slide', (fx1, cym, z0), (1, 0, 0), (0, 0.45), unit='m', parent='Checkpoint', states=['shut', 'out'],
             note='filing cabinet drawer: pulls into the room (+x), 0.45 m (Update 3: same name, axis and travel)')
        socket('Hand_' + name[3:], (fx1 + 0.035, cym, z1 - 0.065), 'hand', parent=name)
    # key cabinet on the back wall (Update 3's place): the box, a back panel, five hooks; the door with its label
    b = KEYBOX
    box6(k, (b['x0'], b['y0'], b['z0']), (b['x1'], b['y1'], b['z0'] + 0.012), Z_KEYBOX, skip=('+y',))
    box6(k, (b['x0'], b['y0'], b['z1'] - 0.012), (b['x1'], b['y1'], b['z1']), Z_KEYBOX, skip=('+y',))
    box6(k, (b['x0'], b['y0'], b['z0'] + 0.012), (b['x0'] + 0.012, b['y1'], b['z1'] - 0.012), Z_KEYBOX, skip=('+y', '-z', '+z'))
    box6(k, (b['x1'] - 0.012, b['y0'], b['z0'] + 0.012), (b['x1'], b['y1'], b['z1'] - 0.012), Z_KEYBOX, skip=('+y', '-z', '+z'))
    face(k, [(b['x0'] + 0.012, 1.478, b['z0'] + 0.012), (b['x1'] - 0.012, 1.478, b['z0'] + 0.012),
             (b['x1'] - 0.012, 1.478, b['z1'] - 0.012), (b['x0'] + 0.012, 1.478, b['z1'] - 0.012)], Z_KEYBOX, (0, -1, 0))
    for name, xh in HOOKS:
        k.tube([Vector((xh, 1.478, HOOK_Z + 0.006)), Vector((xh, 1.458, HOOK_Z + 0.006)), Vector((xh, 1.455, HOOK_Z + 0.018))],
               0.0022, Z_STEELBLK, 5)
        socket('Key_Hook_' + name, (xh, HOOK_Y, HOOK_Z), 'item_slot', parent='Checkpoint',
               note=(f'Key_{name} hangs here (its origin is the hanging point; Forest_Opening.json, same place as Update 3)'
                     if name != 'Stationsleiter' else 'the Stationsleiter hook: empty (its key is not here)'))
    Kd = kb('IX_KeyBoxDoor_303', 'Kpp')
    dy0, dy1 = b['y0'] - 0.012, b['y0']
    box6(Kd, (b['x0'], dy0, b['z0']), (b['x1'], dy1, b['z1']), Z_KEYBOX)
    Kd.box(b['x1'] - 0.055, b['x1'] - 0.035, dy0 - 0.014, dy0, (b['z0'] + b['z1']) / 2 - 0.035, (b['z0'] + b['z1']) / 2 + 0.035, Z_STEELBLK)
    Kl = kb('IX_KeyBoxDoor_303_Label', 'panel')
    quad(Kl, ((b['x0'] + b['x1']) / 2, dy0 - 0.0025, b['z1'] - 0.09), (0, -1, 0), 0.30, 0.08, uv('sign_keys'))
    piv = Vector((b['x0'], 1.429, 1.80))
    part('IX_KeyBoxDoor_303', 'hinge', piv, (0, 0, -1), (0, 120), parent='Checkpoint', states=['shut', 'open'],
         note='key cabinet door: hinged at its left edge, opens into the room (+) to 120; inside the hooks Schranke, Hauptgebäude, '
              'Garage, Generator with their keys and the empty Stationsleiter hook (Update 3: same name, pivot and travel)')
    part('IX_KeyBoxDoor_303_Label', 'static', ((b['x0'] + b['x1']) / 2, dy0, b['z1'] - 0.09), parent='IX_KeyBoxDoor_303',
         note='SCHLÜSSEL / KEYS label on the cabinet door (panel atlas)')
    socket('Hand_KeyBoxDoor', (b['x1'] - 0.045, dy0 - 0.035, (b['z0'] + b['z1']) / 2), 'hand', parent='IX_KeyBoxDoor_303')
    # corkboard, vest hooks on the left wall, the extinguisher bracket, the convector heater on the left wall
    box6(k, (-1.86, IY1 - 0.022, 1.42), (-1.04, IY1, 1.98), {'-y': Z_CORK, '*': Z_TIMBER}, skip=('+y',))
    for yv in (0.85, 1.20):
        k.box(IX0, IX0 + 0.012, yv - 0.03, yv + 0.03, 1.83, 1.89, Z_TIMBER)
        k.tube([Vector((IX0 + 0.012, yv, 1.86)), Vector((IX0 + 0.06, yv, 1.86)), Vector((IX0 + 0.075, yv, 1.89))], 0.005, Z_STEELBLK, 5)
    k.box(1.56, 1.68, IY1 - 0.012, IY1, 0.98, 1.12, Z_STEELBLK)
    h = HEATER
    VM.rbox(k, (IX0 + 0.05, (h['y0'] + h['y1']) / 2, (h['z0'] + h['z1']) / 2), (0.08, h['y1'] - h['y0'], h['z1'] - h['z0']), Z_HEATER,
            r=0.02, ch=0.01, axis='y')
    for yy in (h['y0'] + 0.10, h['y1'] - 0.10):
        k.box(IX0, IX0 + 0.01, yy - 0.02, yy + 0.02, h['z0'] + 0.10, h['z1'] - 0.10, Z_STEELBLK)


# ================================================================ small things (KppProps)
def props():
    P = kb('Kpp_Props', 'KppProps')
    # hi-vis vests on the left-wall hooks (thin, width along y)
    for yv in (0.85, 1.20):
        rings = []
        for zz, w, dpt in ((1.27, 0.15, 0.022), (1.66, 0.15, 0.022), (1.80, 0.08, 0.016), (1.875, 0.025, 0.010)):
            xc = IX0 + 0.045
            rings.append([Vector((xc + a * dpt, yv + b_ * w, zz)) for a, b_ in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
        P.loft(rings, [Z_VEST] * 3, cap0=Z_VEST, cap1=Z_VEST)
    # extinguisher on its bracket right of the door
    ec = Vector((1.62, IY1 - 0.095, 0.66))
    P.lathe(ec, (0, 0, 1), [(0.0, 0.0), (0.0, 0.07), (0.40, 0.075), (0.45, 0.05), (0.48, 0.02), (0.48, 0.0)], Z_EXTP, 12)
    P.box(ec.x - 0.02, ec.x + 0.02, ec.y - 0.02, ec.y + 0.02, ec.z + 0.48, ec.z + 0.55, Z_BLACKP)
    P.box(ec.x - 0.07, ec.x + 0.015, ec.y - 0.012, ec.y + 0.012, ec.z + 0.54, ec.z + 0.56, Z_BLACKP)
    P.tube([ec + Vector((0.02, 0, 0.53)), ec + Vector((0.09, 0, 0.50)), ec + Vector((0.10, 0, 0.30)), ec + Vector((0.08, 0, 0.20))],
           0.009, Z_BLACKP, 6)
    # CCTV monitor (beige CRT) on the front desk, its screen faces the room
    mc = MONITOR
    VM.rbox(P, mc + Vector((0, 0.03, 0.165)), (0.36, 0.24, 0.33), Z_CRT, r=0.02, ch=0.012, axis='y')
    VM.rbox(P, mc + Vector((0, -0.12, 0.15)), (0.26, 0.10, 0.24), Z_CRT, r=0.03, ch=0.01, axis='y')
    P.tube([mc + Vector((0.10, -0.16, 0.05)), mc + Vector((0.12, -0.21, 0.02)), mc + Vector((0.20, -0.20, 0.004))], 0.005, Z_BLACKP, 5)
    # binders standing against the left wall at the end of the front desk
    for yb_ in (-1.37, -1.30, -1.23):
        P.box(IX0 + 0.01, IX0 + 0.29, yb_ - 0.03, yb_ + 0.03, DESK_TOP, DESK_TOP + 0.31, Z_BINDER)
    # thermos and a mug, papers
    P.lathe(Vector((0.30, -1.23, DESK_TOP)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.045), (0.25, 0.045), (0.27, 0.035), (0.31, 0.035),
                                                       (0.31, 0.0)], Z_FLASK, 10)
    mug = Vector((0.42, -1.30, DESK_TOP))
    P.lathe(mug, (0, 0, 1), [(0.0, 0.0), (0.0, 0.040), (0.09, 0.042), (0.09, 0.0)], Z_MUGP, 10)
    P.tube([mug + Vector((0.040, 0, 0.070)), mug + Vector((0.075, 0, 0.060)), mug + Vector((0.075, 0, 0.030)),
            mug + Vector((0.040, 0, 0.020))], 0.006, Z_MUGP, 5, caps=False)
    P.box(-0.38, -0.08, -1.36, -1.15, DESK_TOP, DESK_TOP + 0.010, Z_PAPERP)
    # the radio on the front desk (the guard book: it switched itself on), two knobs, the carry handle, the hand mic
    rc = RADIO
    VM.rbox(P, rc + Vector((0, 0, 0.07)), (0.36, 0.24, 0.14), Z_RADIO, r=0.012, ch=0.008)
    for xk in (-0.13, 0.13):
        P.cyl(Vector((rc.x + xk, rc.y + 0.12, rc.z + 0.07)), Vector((rc.x + xk, rc.y + 0.14, rc.z + 0.07)), 0.016, Z_BLACKP, 8)
    P.strip([rc + Vector((-0.12, 0, 0.14)), rc + Vector((-0.10, 0, 0.18)), rc + Vector((0.10, 0, 0.18)), rc + Vector((0.12, 0, 0.14))],
            Vector((0, 1, 0)), 0.02, 0.016, Z_BLACKP)
    P.lathe(rc + Vector((0.235, 0.02, 0.0)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.022), (0.09, 0.026), (0.10, 0.018), (0.10, 0.0)], Z_BLACKP, 8)
    P.tube([rc + Vector((0.235, 0.02, 0.012)), rc + Vector((0.26, -0.05, 0.004)), rc + Vector((0.21, -0.10, 0.004)),
            rc + Vector((0.18, -0.06, 0.02)), rc + Vector((0.18, -0.01, 0.05))], 0.004, Z_BLACKP, 5)
    # the first-aid box under the clock
    f = FAID
    VM.rbox(P, ((f['x0'] + f['x1']) / 2, (f['y0'] + IY1) / 2, (f['z0'] + f['z1']) / 2), (f['x1'] - f['x0'], IY1 - f['y0'], f['z1'] - f['z0']),
            Z_FAID, r=0.012, ch=0.006, axis='y')
    # wall clock over the gap between the key cabinet and the door
    P.lathe(CLOCK, (0, -1, 0), [(0.0, 0.15), (0.035, 0.15), (0.04, 0.135)], Z_BLACKP, 18, cap0=False, cap1=False)
    # the CCTV camera on its bracket under the front eave at the road corner, looking at the barrier
    cw = Vector((X1 - 0.20, Y0, 2.70))
    P.box(cw.x - 0.04, cw.x + 0.04, Y0 - 0.010, Y0, cw.z - 0.06, cw.z + 0.06, Z_BLACKP)
    cam = cw + Vector((0.10, -0.30, -0.06))
    P.strip([cw + Vector((0, -0.010, 0)), cw + Vector((0.04, -0.20, -0.02)), cam + Vector((0, 0.03, 0.06))], Vector((0, 0, 1)),
            0.025, 0.025, Z_BLACKP)
    d_cam = (Vector((BARRIER_PLACE[0].x + 3.0, BARRIER_PLACE[0].y, 1.0)) - cam).normalized()
    R = VM.frame_R(d_cam, Vector((0, 0, 1)))
    P.box_m(cam, (0.30, 0.10, 0.10), Z_CAMP, R)
    P.box_m(cam + d_cam * 0.03 + R @ Vector((0, 0.065, 0)), (0.36, 0.012, 0.14), Z_CAMP, R)
    part('Kpp_Props', 'static', (0, 0, 0), parent='Checkpoint',
         note='small things: vests, extinguisher, CCTV monitor, binders, thermos, mug, papers, the radio and its mic, the wall '
              'clock, the first-aid box, the CCTV camera under the front eave')
    # the swivel chair (the guard faces the road desk: +x); clear of the pulled drawers
    C = kb('Kpp_Chair', 'KppProps')
    cc = CHAIR
    for a in range(18, 378, 72):
        dv = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        C.strip([cc + Vector((0, 0, 0.075)), cc + dv * 0.29 + Vector((0, 0, 0.055))], Vector((0, 0, 1)), 0.035, 0.022, Z_BLACKP)
        C.lathe(cc + dv * 0.29, (0, 0, 1), [(0.0, 0.0), (0.0, 0.025), (0.045, 0.025), (0.045, 0.0)], Z_BLACKP, 6)
    C.cyl(cc + Vector((0, 0, 0.075)), cc + Vector((0, 0, 0.40)), 0.025, Z_CHROMEP, 8)
    VM.rbox(C, cc + Vector((0, 0, 0.44)), (0.46, 0.46, 0.07), Z_CHAIR, r=0.05, ch=0.02)
    C.strip([cc + Vector((-0.16, 0, 0.44)), cc + Vector((-0.25, 0, 0.58))], Vector((0, 1, 0)), 0.05, 0.014, Z_BLACKP)
    VM.rbox(C, cc + Vector((-0.27, 0, 0.78)), (0.06, 0.42, 0.36), Z_CHAIR, r=0.05, ch=0.02, axis='x')
    part('Kpp_Chair', 'static', cc, parent='Checkpoint', note='the guard\'s swivel chair at the road-side desk')
    socket('Seat_Chair', cc + Vector((0, 0, 0.48)), 'seat', parent='Kpp_Chair', note='sit at the desk: the pass window and the phone in '
                                                                                     'reach', eye=K.r4(cc + Vector((0.02, 0, 1.20))),
           facing=[1.0, 0.0, 0.0])
    # the rotary phone (70s): a sloped body, the dial (panel), the receiver on the cradle (its own object), the cord
    Ph = kb('Phone', 'KppProps')
    p = PHONE
    poly = [(p.x - 0.10, p.z), (p.x + 0.10, p.z), (p.x + 0.10, p.z + 0.095), (p.x - 0.10, p.z + 0.055)]
    prism_y(Ph, poly, p.y - 0.115, p.y + 0.115, Z_PHONE, Z_PHONE)
    for yy in (-0.05, 0.05):
        Ph.box(p.x + 0.035, p.x + 0.065, p.y + yy - 0.012, p.y + yy + 0.012, p.z + 0.082, p.z + 0.118, Z_PHONE)
    sl = Vector((-0.04, 0.0, 0.20)).normalized()                     # the slope's normal: up and toward the guard (-x)
    s0 = Vector((p.x - 0.045, p.y, p.z + 0.066))
    Ph.lathe(s0, sl, [(0.0, 0.046), (0.006, 0.046)], Z_BLACKP, 14, cap0=False, cap1=False)
    Dl = kb('Phone_Dial', 'panel')
    Dl.disc_uv(s0 + sl * 0.003, sl, 0.045, uv('phone_dial'), 16)
    Ph.tube([p + Vector((0.10, 0.06, 0.02)), p + Vector((0.16, 0.10, 0.004)), p + Vector((0.12, 0.17, 0.004)),
             p + Vector((0.05, 0.16, 0.004)), p + Vector((0.05, 0.13, 0.11))], 0.004, Z_BLACKP, 5)
    Pr = kb('Phone_Receiver', 'KppProps')
    rc_ = p + Vector((0.05, 0.0, 0.125))
    Pr.strip([rc_ + Vector((0, -0.10, 0)), rc_ + Vector((0, 0.10, 0))], Vector((0, 0, 1)), 0.042, 0.024, Z_PHONE)
    for yy in (-0.10, 0.10):
        Pr.lathe(rc_ + Vector((0, yy, -0.012)), (0, 0, -1), [(0.0, 0.0), (0.0, 0.026), (0.02, 0.032), (0.03, 0.030), (0.03, 0.0)],
                 Z_PHONE, 10)
    part('Phone', 'static', p, parent='Checkpoint',
         note='rotary desk phone (70s, orange) by the pass window: X05 rings it twice; zone Phone_KPP (Update 3) is round the receiver')
    part('Phone_Receiver', 'static', rc_, parent='Phone', note='the receiver on its cradle: hide / animate it while it is picked up '
                                                               '(X05: silence, then breathing)')
    part('Phone_Dial', 'static', s0, parent='Phone', note='dial face (panel atlas)')
    socket('Hand_Phone_Receiver', rc_ + Vector((0, 0, 0.03)), 'hand', parent='Phone_Receiver')
    # the bell outside on the road-side wall under the eave (rings with the phone)
    Bl = kb('Phone_Bell', 'KppProps')
    Bl.box(X1, X1 + 0.012, BELL.y - 0.07, BELL.y + 0.07, BELL.z - 0.09, BELL.z + 0.09, Z_BLACKP)
    Bl.lathe(Vector((X1 + 0.012, BELL.y, BELL.z)), (1, 0, 0), [(0.0, 0.0), (0.0, 0.085), (0.03, 0.082), (0.065, 0.05), (0.08, 0.0)],
             Z_BELLP, 14)
    Bl.cyl(Vector((X1 + 0.012, BELL.y, BELL.z - 0.075)), Vector((X1 + 0.05, BELL.y, BELL.z - 0.075)), 0.008, Z_BLACKP, 6)
    part('Phone_Bell', 'static', BELL, parent='Checkpoint', note='the phone\'s bell outside on the road-side wall: rings with the phone (X05)')


# ================================================================ lamps: the fluorescent batten (flickers), the door bulkhead,
# the CCTV screen
def lamps():
    k = KBS['Checkpoint']
    c = FLUOR
    zr = z_rb(c.y)
    for xr in (-0.65, 0.0):                              # short hangers to the two rafters it crosses
        k.cyl(Vector((xr, c.y, c.z + 0.025)), Vector((xr, c.y, zr)), 0.004, Z_STEELBLK, 4)
    L = kb('Lamp_Fluor', 'Kpp')
    VM.rbox(L, c, (1.26, 0.10, 0.05), Z_ENAMEL_IN, r=0.01, ch=0.006, axis='x')
    for sx in (-1, 1):
        L.box(c.x + sx * 0.60 - 0.015, c.x + sx * 0.60 + 0.015, c.y - 0.03, c.y + 0.03, c.z - 0.045, c.z - 0.02, Z_ENAMEL_IN)
    part('Lamp_Fluor', 'static', c, parent='Checkpoint',
         note='fluorescent batten under the rafters: flickers from the start although there is no power (Update 3: Light_booth, '
              'M_Lamp_FluorFlicker)')
    tc = c + Vector((-0.58, 0, -0.038))
    G = kb('Lens_Fluor', 'lens:fluor')
    G.lathe(tc, (1, 0, 0), [(0.0, 0.0135), (1.16, 0.0135)], ZERO, 8, cap0=True, cap1=True)
    uv_cyl(G, tc, 0.0, 1.16, uv('l_fluor'), axis=(1, 0, 0))
    part('Lens_Fluor', 'static', c + Vector((0, 0, -0.038)), parent='Lamp_Fluor',
         note='the tube: M_Kpp_Lamp_Fluor (lit, flickering) / M_Kpp_Lamp_Fluor_Off')
    Gw = kb('Glow_Fluor', 'glow')
    gc = c + Vector((0, 0, -0.04))
    quad(Gw, gc, (0, 0, -1), 1.56, 0.42, uv('glow_cold'), up=(0, 1, 0))
    for n in ((0, 1, 0), (0, -1, 0)):
        quad(Gw, gc + Vector((0, 0, -0.03)), n, 1.56, 0.16, uv('glow_cold'))
    part('Glow_Fluor', 'static', gc, parent='Lamp_Fluor', note='halo cards along the tube: additive, unlit; flicker with the light')
    LAMPS.append(('Fluor', LIGHT_FLUOR, (0, 0, -1), 'fluor', (0, 1, 0)))
    # the caged bulkhead over the door outside (the shed's), on the station power
    b = BULK
    k.box(b.x - 0.05, b.x + 0.05, Y1, Y1 + 0.01, b.z - 0.06, b.z + 0.06, Z_STEELBLK)
    k.lathe(b + Vector((0, 0.01, 0)), (0, 1, 0), [(0.0, 0.07), (0.01, 0.085), (0.045, 0.085), (0.05, 0.072)], Z_STEELBLK, 12,
            cap0=True, cap1=False)
    dc = b + Vector((0, 0.058, 0))
    Lb = kb('Lens_Bulk_Door', 'lens:bulk')
    Lb.disc_uv(dc, Vector((0, 1, 0)), 0.068, uv('l_bulk'), 12, dome=0.04)
    for a in (0, 60, 120):
        d = Vector((math.cos(math.radians(a)), 0, math.sin(math.radians(a))))
        k.tube([dc + d * 0.078 * math.cos(math.radians(t)) + Vector((0, 0.052 * math.sin(math.radians(t)), 0)) for t in range(0, 181, 30)],
               0.003, Z_STEELBLK, 4, caps=False)
    part('Lens_Bulk_Door', 'static', dc + Vector((0, 0.02, 0)), parent='Checkpoint',
         note='frosted dome of the bulkhead over the door: lit with the station power (M_Kpp_Lamp_Bulk / _Off)')
    Gb = kb('Glow_Bulk_Door', 'glow')
    quad(Gb, dc + Vector((0, 0.045, 0)), (0, 1, 0), 0.50, 0.50, uv('glow_warm'))
    u0, v0, u1, v1 = uv('glow_warm')
    quad(Gb, Vector((dc.x, Y1 + 0.17, dc.z - 0.002)), (0, 0, -1), 0.50, 0.32, (u0, v0, u1, (v0 + v1) / 2), up=(0, -1, 0))
    part('Glow_Bulk_Door', 'static', dc, parent='Checkpoint', note='halo cards of the bulkhead: shown with the power')
    LAMPS.append(('Bulk_Door', dc + Vector((0, 0.06, -0.02)), (0, 0.6, -0.8), 'bulkhead_kpp', (0, 0, 1)))
    # the CCTV monitor's screen (lit with the power)
    Sc = kb('Screen_CCTV', 'lens:crt')
    sp = MONITOR + Vector((0, 0.153, 0.175))
    quad(Sc, sp, (0, 1, 0), 0.25, 0.19, uv('crt'))
    part('Screen_CCTV', 'static', sp, parent='Checkpoint',
         note='the CCTV monitor\'s screen: the gate camera with the power (M_Kpp_Lamp_Crt), dark glass without (_Off)')


# ================================================================ outside: bollards; signs and the panel things
def outside():
    k = KBS['Checkpoint']
    x0, x1, y0, y1 = PAD
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = Vector((sx * (x1 - 0.15), sy * (y1 - 0.15), FLOOR - 0.10))
            k.lathe(p, (0, 0, 1), [(0.0, 0.065), (0.92, 0.065), (0.935, 0.055), (0.945, 0.0)], Z_BOLLARD, 10, cap0=False)
    S = kb('Kpp_Signs', 'panel')
    box6(k, (-0.92, YF - 0.041, 2.78), (0.92, YF - 0.025, 3.10), Z_TRIMW, skip=('+y',))     # the sign plate on the front fascia
    quad(S, (0.0, YF - 0.0435, 2.94), (0, -1, 0), 1.80, 0.30, uv('sign_kpp'))
    box6(k, (X1, -1.01, 0.58), (X1 + 0.008, -0.17, 0.84), Z_STEELBLK, skip=('-x',))     # HALT plate under the pass window
    quad(S, (X1 + 0.0105, -0.59, 0.71), (1, 0, 0), 0.80, 0.22, uv('sign_halt'))
    part('Kpp_Signs', 'static', (0, 0, 0), parent='Checkpoint',
         note='KONTROLLPUNKT / CHECKPOINT on the front fascia, HALT! AUSWEIS VORZEIGEN / STOP! SHOW YOUR ID under the pass window '
              '(panel atlas)')
    Pn = kb('Kpp_Panel', 'panel')
    yc = IY1 - 0.022 - 0.0025
    quad(Pn, (-1.68, yc, 1.75), (0, -1, 0), 0.21, 0.297, uv('roster'))
    quad(Pn, (-1.42, yc, 1.62), (0, -1, 0), 0.21, 0.28, uv('phonelist'))
    quad(Pn, (-1.19, yc, 1.79), (0, -1, 0), 0.18, 0.25, uv('calendar'))
    b = KEYBOX
    quad(Pn, ((b['x0'] + b['x1']) / 2, 1.4755, HOOK_Z + 0.055), (0, -1, 0), 0.50, 0.05, uv('keytags'))
    quad(Pn, (RADIO.x, RADIO.y + 0.12 + 0.0025, RADIO.z + 0.085), (0, 1, 0), 0.33, 0.10, uv('radio'))
    Pn.disc_uv(CLOCK + Vector((0, -0.0425, 0)), Vector((0, -1, 0)), 0.135, uv('clock'), 18)
    quad(Pn, ((FAID['x0'] + FAID['x1']) / 2, FAID['y0'] - 0.0025, (FAID['z0'] + FAID['z1']) / 2), (0, -1, 0), 0.27, 0.21, uv('firstaid'))
    part('Kpp_Panel', 'static', (0, 0, 0), parent='Checkpoint',
         note='duty roster, phone list and the October calendar on the corkboard, the hook labels in the key cabinet, the radio\'s '
              'front, the clock face (stopped at 2:40), ERSTE HILFE / FIRST AID (panel atlas)')


# ================================================================ the barrier (own root, 7 m out on the road)
def barrier():
    B = kb('Barrier', 'KppYard')
    # concrete foot; the post beside the boom (+y) carrying the pivot shaft and its flange
    box6(B, (-0.375, -0.375, -0.15), (0.375, 0.375, 0.15), Z_CONC, skip=('-z',))
    box6(B, (-0.10, 0.10, 0.15), (0.10, 0.30, 1.30), Z_BARPOST, skip=('-z', '+z'))
    box6(B, (-0.12, 0.08, 1.30), (0.12, 0.32, 1.33), Z_BARPOST)
    B.cyl(Vector((0, 0.10, BOOM_PIV.z)), Vector((0, 0.052, BOOM_PIV.z)), 0.022, Z_STEELBLK, 8)
    B.lathe(Vector((0, 0.10, BOOM_PIV.z)), (0, -1, 0), [(0.0, 0.05), (0.012, 0.05)], Z_STEELBLK, 10, cap0=False, cap1=True)
    # rest post (in from the boom tip): foot, pole, the top plate, the fork; the locking tab cranked out from the top plate
    # to the post eye, so that nothing is under the eyes and the padlock's body hangs free
    rx = PADLOCK.x
    qx = REST_X
    box6(B, (qx - 0.20, -0.20, -0.15), (qx + 0.20, 0.20, 0.12), Z_CONC, skip=('-z',))
    B.cyl(Vector((qx, 0, 0.12)), Vector((qx, 0, 0.96)), 0.04, Z_BARPOST, 8)
    B.box(qx - 0.12, qx + 0.12, -0.075, 0.075, 0.96, 0.98, Z_STEELBLK)
    for sy in (-1, 1):
        B.box(qx - 0.10, qx + 0.10, sy * 0.065 - 0.008, sy * 0.065 + 0.008, 0.98, 1.21, Z_STEELBLK)
    B.box(qx + 0.10, qx + 0.116, 0.003, 0.011, 0.98, EYE.z + 0.014, Z_STEELBLK)
    B.box(qx + 0.116, rx - 0.0165, 0.003, 0.011, EYE.z - 0.014, EYE.z + 0.014, Z_STEELBLK)
    ring(B, EYE + Vector((0, 0.007, 0)), (0, 1, 0), 0.016, 0.004, Z_STEELBLK)
    socket('Spot_Padlock', PADLOCK, 'item_slot', parent='Barrier',
           note='Padlock_Barrier hangs here through the post eye and the boom eye (its origin is the hanging point; '
                'Forest_Opening.json, same place as Update 3)')
    # the boom (IX_BarrierArm_82): striped box tube, the counterweight on the short side, the hub, the boom eye, the tip
    A = kb('IX_BarrierArm_82', 'KppYard')
    pz = BOOM_PIV.z
    xm_ = (0.02 + BOOM_LEN - 0.06) / 2                          # two tube sections joined by a sleeve (packs into the atlas)
    for xa_, xb_ in ((0.02, xm_), (xm_, BOOM_LEN - 0.06)):
        VM.rbox(A, ((xa_ + xb_) / 2, 0, pz), (xb_ - xa_, 0.09, 0.11), Z_BOOM, r=0.015, ch=0.008, axis='x')
    VM.rbox(A, (xm_, 0, pz), (0.14, 0.104, 0.124), Z_STEELBLK, r=0.018, ch=0.008, axis='x')
    VM.rbox(A, (-0.37, 0, pz), (0.40, 0.14, 0.19), Z_STEELBLK, r=0.025, ch=0.012, axis='x')
    A.box(-0.17, 0.10, -0.05, 0.05, pz - 0.075, pz + 0.075, Z_BARPOST)
    A.box(rx - 0.008, rx + 0.008, -0.011, -0.003, EYE.z + 0.017, pz - 0.055, Z_STEELBLK)
    ring(A, EYE + Vector((0, -0.007, 0)), (0, 1, 0), 0.016, 0.004, Z_STEELBLK)
    A.box(BOOM_LEN - 0.06, BOOM_LEN, -0.05, 0.05, pz - 0.06, pz + 0.06, Z_RUBBER_K)
    part('IX_BarrierArm_82', 'hinge', BOOM_PIV, (0, -1, 0), (0, 80), parent='Barrier', states=['down', 'up'],
         note='barrier boom: lift by hand (+, up to 80) once Padlock_Barrier is off; the counterweight swings down beside the post '
              '(Update 3: same name, pivot and travel)')
    socket('Hand_BarrierArm', (BOOM_LEN - 0.6, 0, pz + 0.07), 'hand', parent='IX_BarrierArm_82', note='lift it here')
    socket('Audio_Barrier', BOOM_PIV, 'audio', parent='Barrier', note='boom: the bearing creaks, the counterweight thuds at the top')
    part('Barrier', 'static', (0, 0, 0), parent=None, yaw=BARRIER_PLACE[1],
         note='barrier 7 m out on the road in front of the booth (separate root: the map\'s Barrier prefab, same place)')


# ================================================================ the sliding gate (own root, beside the booth)
def box6_x(k, lo, hi, zones, skip=(), seg=3.5):
    """box6 split along x into pieces of at most `seg` metres (long rails pack badly into a small atlas); the inner end
    faces are left out"""
    x0, x1 = lo[0], hi[0]
    n = max(1, int(math_ceil((x1 - x0) / seg)))
    for i in range(n):
        a, b = x0 + (x1 - x0) * i / n, x0 + (x1 - x0) * (i + 1) / n
        sk = tuple(skip) + (('-x',) if i > 0 else ()) + (('+x',) if i < n - 1 else ())
        box6(k, (a, lo[1], lo[2]), (b, hi[1], hi[2]), zones, skip=sk)


def barbed_band(k, a, u0, u1, zb):
    """two-sided barbed-wire band (alpha texture T_Kpp_Barbed) in the plane y = a from x u0 to u1, foot at zb, 0.36 high:
    strands 0.06 / 0.18 / 0.30 above the foot; u in tiles of 0.5 m"""
    for d, s in ((-0.0006, -1), (0.0006, 1)):
        pts = [(u0, a + d, zb), (u1, a + d, zb), (u1, a + d, zb + 0.36), (u0, a + d, zb + 0.36)]
        face(k, pts, ZERO, (0, s, 0), [(u0 / 0.5, 0.0), (u1 / 0.5, 0.0), (u1 / 0.5, 1.0), (u0 / 0.5, 1.0)])


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


def gate():
    Gt = kb('Gate', 'KppYard')
    ly = LEAF_Y
    # the receiving post with its catch; the rail in its concrete strip; two guide posts with top rollers; the end stop
    box6(Gt, (-7.40, ly - 0.23, -0.15), (-6.95, ly + 0.23, 0.03), Z_CONC, skip=('-z',))
    box6(Gt, (-7.16, ly - 0.04, 0.03), (-7.08, ly + 0.04, 2.30), Z_GALV, skip=('-z',))
    for zc in (0.20, 1.97):
        for s in (-1, 1):
            Gt.box(-7.08, -6.90, ly + s * 0.040 - 0.005, ly + s * 0.040 + 0.005, zc - 0.05, zc + 0.05, Z_STEELBLK)
        Gt.box(-7.08, -7.02, ly - 0.035, ly + 0.035, zc - 0.04, zc + 0.04, Z_RUBBER_K)
    box6_x(Gt, (-6.95, ly - 0.15, -0.05), (6.66, ly + 0.15, 0.010), Z_CONC, skip=('-z', '-x', '+x', '-y', '+y'))
    box6_x(Gt, (-6.95, ly - 0.02, 0.010), (6.68, ly + 0.02, 0.045), Z_STEELBLK, skip=('-z',))
    for yp in (ly - 0.13, ly + 0.13):
        box6(Gt, (-0.36, yp - 0.12, -0.15), (0.04, yp + 0.12, 0.03), Z_CONC, skip=('-z',))
        box6(Gt, (-0.20, yp - 0.04, 0.03), (-0.12, yp + 0.04, 2.15), Z_GALV, skip=('-z',))
        s = 1 if yp > ly else -1
        rl = ly + s * 0.058                                # the roller beside the top rail
        Gt.box(-0.18, -0.14, *sorted((yp - s * 0.04, rl)), 2.06, 2.09, Z_GALV)
        Gt.cyl(Vector((-0.16, rl, 2.06)), Vector((-0.16, rl, 2.04)), 0.006, Z_STEELBLK, 6)
        Gt.lathe(Vector((-0.16, rl, 1.92)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.026), (0.12, 0.026), (0.12, 0.0)], Z_GATEROLL, 10)
    box6(Gt, (6.66, ly - 0.15, -0.15), (7.00, ly + 0.15, 0.010), Z_CONC, skip=('-z', '-x'))
    box6(Gt, (6.68, ly - 0.04, 0.010), (6.76, ly + 0.04, 0.60), Z_GALV, skip=('-z',))
    Gt.box(6.62, 6.68, ly - 0.03, ly + 0.03, 0.165, 0.225, Z_RUBBER_K)
    # fixed fence panel on the fence line (y 0) from the guide posts to the map's fence
    fa, fb = FENCE_X
    for xp in (fa, fb):
        box6(Gt, (xp - 0.15, -0.15, -0.15), (xp + 0.15, 0.15, 0.03), Z_CONC, skip=('-z',))
        Gt.cyl(Vector((xp, 0, 0.03)), Vector((xp, 0, 2.38)), 0.03, Z_GALV, 8)
    Gt.cyl(Vector((fa + 0.03, 0, 1.95)), Vector((fb - 0.03, 0, 1.95)), 0.02, Z_GALV, 6)
    Gt.cyl(Vector((fa + 0.03, 0, 0.08)), Vector((fb - 0.03, 0, 0.08)), 0.004, Z_GALV, 4)
    for xp in (fa, fb):
        Gt.box(xp - 0.01, xp + 0.01, -0.01, 0.01, 2.38, 2.42, Z_GALV)
    Fb = kb('Gate_Fence_Barbed', 'barbed')
    barbed_band(Fb, 0.0, fa, fb, 2.04)
    part('Gate_Fence_Barbed', 'static', ((fa + fb) / 2, 0, 2.22), parent='Gate',
         note='barbed wire over the fixed panel: alpha band M_Kpp_Barbed (three strands)')
    Fm = kb('Gate_Fence_Mesh', 'chainlink')
    chain_quad(Fm, 'y', 0.0, fa + 0.03, fb - 0.03, 0.06, 1.93)
    part('Gate_Fence_Mesh', 'static', ((fa + fb) / 2, 0, 1.0), parent='Gate', note='chain-link of the fixed panel (M_Kpp_ChainLink)')
    # the leaf (IX_Gate_81): frame, verticals, braces, chain-link, barbed wire on upright arms, the V wheels, the sign
    L = kb('IX_Gate_81', 'KppYard')
    lx0, lx1 = GATE_LEAF
    z0, z1 = GATE_Z
    box6_x(L, (lx0, ly - 0.03, z0), (lx1, ly + 0.03, z0 + 0.07), Z_GALV)
    box6_x(L, (lx0 + 0.06, ly - 0.03, z1 - 0.06), (lx1 - 0.06, ly + 0.03, z1), Z_GALV, skip=('-x', '+x'))
    verts = [lx0 + 0.03 + i * (lx1 - lx0 - 0.06) / 7 for i in range(8)]
    for i, xv in enumerate(verts):
        w = 0.03 if i in (0, 7) else 0.022
        box6(L, (xv - w, ly - 0.025, z0 + 0.07), (xv + w, ly + 0.025, z1 + (0.0 if i in (0, 7) else -0.06)), Z_GALV,
             skip=('-z', '+z') if i not in (0, 7) else ('-z',))
        box6(L, (xv - 0.012, ly - 0.012, z1), (xv + 0.012, ly + 0.012, z1 + 0.42), Z_GALV, skip=('-z',))
    for i in range(7):
        xa, xb = verts[i] + 0.03, verts[i + 1] - 0.03
        a_, b_ = (Vector((xa, ly, z0 + 0.08)), Vector((xb, ly, z1 - 0.07))) if i % 2 == 0 else \
            (Vector((xa, ly, z1 - 0.07)), Vector((xb, ly, z0 + 0.08)))
        L.strip([a_, b_], Vector((0, 1, 0)), 0.035, 0.03, Z_GALV)
    Lb = kb('IX_Gate_81_Barbed', 'barbed')
    barbed_band(Lb, ly, lx0, lx1, z1 + 0.06)
    for xw in (lx0 + 0.33, lx1 - 0.40):
        for s in (-1, 1):
            L.box(xw - 0.05, xw + 0.05, ly + s * 0.03 - 0.004, ly + s * 0.03 + 0.004, 0.08, z0 + 0.01, Z_STEELBLK)
        L.lathe(Vector((xw, ly - 0.022, 0.10)), (0, 1, 0), [(0.0, 0.03), (0.008, 0.055), (0.022, 0.045), (0.036, 0.055),
                                                            (0.044, 0.03)], Z_GATEROLL, 10)
    Lm = kb('IX_Gate_81_Mesh', 'chainlink')
    chain_quad(Lm, 'y', ly, lx0 + 0.06, lx1 - 0.06, z0 + 0.07, z1 - 0.06)
    sx0, sx1 = -3.95, -3.05
    L.box(sx0, sx1, ly - 0.042, ly - 0.032, 1.00, 1.60, Z_GALV)
    Sg = kb('IX_Gate_81_Sign', 'panel')
    quad(Sg, ((sx0 + sx1) / 2, ly - 0.0445, 1.30), (0, -1, 0), 0.88, 0.58, uv('sign_sperr'))
    part('IX_Gate_81', 'slide', (lx0, 0.0, 0.0), (1, 0, 0), (0, GATE_TRAVEL), unit='m', parent='Gate', states=['shut', 'open'],
         note='sliding gate leaf on a ground rail, 0.22 m inside the fence line: slides behind the fixed panel (+x), 6.6 m; heavy: '
              'two players push faster (Update 3: same name, origin, axis and travel)')
    part('IX_Gate_81_Barbed', 'static', ((lx0 + lx1) / 2, ly, z1 + 0.24), parent='IX_Gate_81',
         note='barbed wire on the leaf\'s upright arms: alpha band M_Kpp_Barbed (three strands)')
    part('IX_Gate_81_Mesh', 'static', ((lx0 + lx1) / 2, ly, (z0 + z1) / 2), parent='IX_Gate_81',
         note='chain-link infill: tiled alpha-cutout material M_Kpp_ChainLink (0.5 m per tile)')
    part('IX_Gate_81_Sign', 'static', ((sx0 + sx1) / 2, ly - 0.04, 1.30), parent='IX_Gate_81',
         note='SPERRGEBIET / RESTRICTED AREA, ZUTRITT VERBOTEN / NO ENTRY on the outer face (panel atlas)')
    socket('Hand_Gate', (lx0 + 0.25, ly - 0.10, 1.10), 'hand', parent='IX_Gate_81', note='push / pull here (the free end), outside')
    socket('Hand_Gate_2', (lx0 + 0.25, ly + 0.10, 1.10), 'hand', parent='IX_Gate_81', note='the second player, inside')
    socket('Audio_Gate', (-3.5, ly, 0.10), 'audio', parent='IX_Gate_81', note='wheels grinding on the rail, the chain-link rattles')
    socket('Audio_GateCatch', (-7.10, ly, 1.0), 'audio', parent='Gate', note='the catch clanks when the leaf closes')
    part('Gate', 'static', (0, 0, 0), parent=None, yaw=GATE_PLACE[1],
         note='sliding gate beside the booth (separate root: the map\'s Gate prefab, same place)')


# ================================================================ the barrier and the gate move to their places
def place_roots():
    for root, (pos, yaw) in (('Barrier', BARRIER_PLACE), ('Gate', GATE_PLACE)):
        M = Matrix.Translation(pos) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
        R3 = M.to_3x3()
        tree, grown = {root}, True
        while grown:
            grown = False
            for n, p in CONTRACT['parts'].items():
                if p.get('parent') in tree and n not in tree:
                    tree.add(n)
                    grown = True
        for n in tree:
            transform_kb(KBS[n], M)
            p = CONTRACT['parts'][n]
            p['pivot'] = K.r4(M @ Vector(p['pivot']))
            if p.get('axis') is not None:
                p['axis'] = K.r4(R3 @ Vector(p['axis']))
        for s in CONTRACT['sockets'].values():
            if s.get('parent') in tree:
                s['pos'] = K.r4(M @ Vector(s['pos']))
                for key in ('dir', 'facing'):
                    if s.get(key) is not None:
                        s[key] = K.r4(R3 @ Vector(s[key]))
                if s.get('eye') is not None:
                    s['eye'] = K.r4(M @ Vector(s['eye']))


# ================================================================ points, colliders, knock rays
def play_points():
    socket('Spot_KPPLog', NOTE, 'item_slot', parent='Checkpoint',
           note='Note_KPPLog (the guard book, readable kpp_log) lies here on the road-side desk (same place as Update 3)')
    for name, kind, pos, d, note in (
            ('Audio_Phone', 'audio', PHONE + Vector((0, 0, 0.08)), None, 'the phone rings (two bursts, a 70s bell); the receiver: '
                                                                         'silence, then breathing (X05)'),
            ('Audio_PhoneBell', 'audio', BELL, None, 'the bell outside rings with the phone (X05)'),
            ('Audio_Fluor', 'audio', FLUOR, None, 'the tube: hum and ticking while it flickers'),
            ('Audio_Radio', 'audio', RADIO + Vector((0, 0, 0.10)), None, 'the radio: hiss, someone counting (the guard book)'),
            ('Audio_BoothDoor', 'audio', (DOOR['x1'], Y1, 1.2), None, 'door: latch, hinges'),
            ('Audio_Roof', 'audio', (0.0, 0.0, 3.1), None, 'tin roof: rain, needles, steps'),
            ('VFX_Fluor', 'vfx', FLUOR + Vector((0, 0, -0.04)), (0, 0, -1), 'the tube flickers (light + halo + lens; Update 3 flicker: '
                                                                             'min 0.08, max 1.0, speed 5)')):
        socket(name, pos, kind, note=note, parent='Checkpoint')
        if d is not None:
            CONTRACT['sockets'][name]['dir'] = list(d)
    socket('Hide_UnderDesk', (-0.30, IY0 + 0.30, FLOOR + 0.30), 'hide', parent='Checkpoint',
           note='crouched under the front desk: not seen through the windows', pose='crouch',
           eye=K.r4((-0.30, IY0 + 0.42, FLOOR + 0.62)), facing=[0.0, 1.0, 0.0])


def static_boxes():
    """(name, parent, (x0, x1, y0, y1, z0, z1) in the booth frame, rotation xyz deg or None, False)"""
    R = 'Checkpoint'
    B = [('Pad', R, (PAD[0], PAD[1], PAD[2], PAD[3], PAD_Z0, FLOOR), None),
         ('Wall_Front_L', R, (X0, WIN_F[0], Y0, IY0, FLOOR, ZTOP_F), None),
         ('Wall_Front_R', R, (WIN_F[1], X1, Y0, IY0, FLOOR, ZTOP_F), None),
         ('Wall_Front_Low', R, (WIN_F[0], WIN_F[1], Y0, IY0, FLOOR, WZ0), None),
         ('Wall_Front_High', R, (WIN_F[0], WIN_F[1], Y0, IY0, WZ1, ZTOP_F), None),
         ('Window_Front', R, (WIN_F[0], WIN_F[1], Y0 + 0.02, IY0 - 0.02, WZ0, WZ1), None),
         ('Wall_Back_L', R, (X0, DOOR['x0'], IY1, Y1, FLOOR, ZTOP_B), None),
         ('Wall_Back_R', R, (DOOR['x1'], X1, IY1, Y1, FLOOR, ZTOP_B), None),
         ('Wall_Back_Head', R, (DOOR['x0'], DOOR['x1'], IY1, Y1, DOOR['z1'], ZTOP_B), None),
         ('Wall_Road_Low', R, (IX1, X1, IY0, IY1, FLOOR, WZ0), None),
         ('Wall_Road_F', R, (IX1, X1, IY0, WIN_R[0], WZ0, ZS), None),
         ('Wall_Road_B', R, (IX1, X1, WIN_R[1], IY1, WZ0, ZS), None),
         ('Wall_Road_High', R, (IX1, X1, WIN_R[0], WIN_R[1], WZ1, ZS), None),
         ('Window_Road_Fixed_F', R, (X1 - 0.065, X1 - 0.02, WIN_R[0], PASS[0], WZ0, WZ1), None),
         ('Window_Road_Fixed_B', R, (X1 - 0.065, X1 - 0.02, PASS[1], WIN_R[1], WZ0, WZ1), None),
         ('Wall_Left_Low', R, (X0, IX0, IY0, IY1, FLOOR, WZ0), None),
         ('Wall_Left_F', R, (X0, IX0, IY0, WIN_L[0], WZ0, ZS), None),
         ('Wall_Left_B', R, (X0, IX0, WIN_L[1], IY1, WZ0, ZS), None),
         ('Wall_Left_High', R, (X0, IX0, WIN_L[0], WIN_L[1], WZ1, ZS), None),
         ('Window_Left', R, (X0 + 0.02, IX0 - 0.02, WIN_L[0], WIN_L[1], WZ0, WZ1), None),
         ('Desk_Front', R, (DESK_F[0], DESK_F[1], DESK_F[2], DESK_F[3], FLOOR, DESK_TOP), None),
         ('Desk_Road', R, (DESK_R[0], DESK_R[1], DESK_R[2], DESK_R[3], FLOOR, DESK_TOP), None),
         ('Cabinet', R, (CAB['x0'], CAB['x1'], CAB['y0'], CAB['y1'], FLOOR, CAB['z1']), None),
         ('KeyBox', R, (KEYBOX['x0'], KEYBOX['x1'], KEYBOX['y0'], KEYBOX['y1'], KEYBOX['z0'], KEYBOX['z1']), None),
         ('Heater', R, (IX0, IX0 + 0.09, HEATER['y0'], HEATER['y1'], HEATER['z0'], HEATER['z1']), None),
         ('Door', 'IX_BoothDoor_74', (LEAF['x0'], LEAF['x1'], LEAF['y0'], LEAF['y1'], LEAF['z0'], LEAF['z1']), None),
         ('KeyBoxDoor', 'IX_KeyBoxDoor_303', (KEYBOX['x0'], KEYBOX['x1'], KEYBOX['y0'] - 0.012, KEYBOX['y0'], KEYBOX['z0'],
                                               KEYBOX['z1']), None),
         ('Sash', 'IX_BoothWindow_302', (IX1 + 0.016, IX1 + 0.042, SASH[0], SASH[1], WZ0 + 0.025, WZ1 - 0.025), None),
         ('Chair', 'Kpp_Chair', (CHAIR.x - 0.32, CHAIR.x + 0.30, CHAIR.y - 0.30, CHAIR.y + 0.30, FLOOR, FLOOR + 0.96), None)]
    # the roof sheet: a box tilted about x (the slope falls toward +y)
    yc = (YF + YB) / 2
    zc = (z_sb(yc) + z_st(yc)) / 2
    hl = (YB - YF) / 2 / CP
    B.append(('Roof', R, (-XS, XS, yc - hl, yc + hl, zc - 0.03, zc + 0.03), (-math.degrees(PITCH), 0.0, 0.0)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (PAD[1] - 0.15), sy * (PAD[3] - 0.15)
            B.append((f'Bollard_{"R" if sx > 0 else "L"}{"B" if sy > 0 else "F"}', R,
                      (x - 0.065, x + 0.065, y - 0.065, y + 0.065, FLOOR, FLOOR + 0.845), None))
    # barrier and gate: given in their own frames, moved to their places here (yaw 0)
    qx = REST_X
    bar = [('Barrier_Foot', 'Barrier', (-0.375, 0.375, -0.375, 0.375, -0.41, 0.15)),
           ('Barrier_Post', 'Barrier', (-0.12, 0.12, 0.08, 0.32, 0.15, 1.33)),
           ('Barrier_Rest', 'Barrier', (qx - 0.12, qx + 0.12, -0.075, 0.075, 0.12, 0.98)),
           ('Boom', 'IX_BarrierArm_82', (-0.57, BOOM_LEN, -0.07, 0.07, BOOM_PIV.z - 0.095, BOOM_PIV.z + 0.095))]
    ly = LEAF_Y
    gat = [('Gate_Receiver', 'Gate', (-7.40, -6.95, ly - 0.23, ly + 0.23, -0.60, 2.30)),
           ('Gate_Guide_Out', 'Gate', (-0.24, -0.08, ly - 0.21, ly - 0.05, 0.0, 2.15)),
           ('Gate_Guide_In', 'Gate', (-0.24, -0.08, ly + 0.05, ly + 0.21, 0.0, 2.15)),
           ('Gate_Stop', 'Gate', (6.62, 6.76, ly - 0.04, ly + 0.04, 0.0, 0.60)),
           ('Gate_Fence', 'Gate', (FENCE_X[0] - 0.03, FENCE_X[1] + 0.03, -0.03, 0.03, 0.0, 2.38)),
           ('Gate_Leaf', 'IX_Gate_81', (GATE_LEAF[0], GATE_LEAF[1], ly - 0.035, ly + 0.035, 0.05, GATE_Z[1] + 0.40))]
    for lst, (pos, yaw) in ((bar, BARRIER_PLACE), (gat, GATE_PLACE)):
        assert yaw == 0.0
        for name, par, (a0, a1, b0, b1, c0, c1) in lst:
            B.append((name, par, (a0 + pos.x, a1 + pos.x, b0 + pos.y, b1 + pos.y, c0 + pos.z, c1 + pos.z), None))
    return [(n, p, b, r, False) for n, p, b, r in B]


def knock_rays():
    R = []
    for i, x in enumerate((-1.97, 1.97)):
        R.append((f'Knock_Front_{i + 1}', (x, -3.0, 0.70), (0, 1, 0)))
    for i, x in enumerate((-1.2, -0.3, 1.8)):
        R.append((f'Knock_Back_{i + 1}', (x, 3.0, 1.40 if x < 0 else 1.0), (0, -1, 0)))
    for i, y in enumerate((-1.3, 0.0, 1.0)):
        R.append((f'Knock_Road_{i + 1}', (3.4, y, 1.0 if y > -0.5 else 0.55), (-1, 0, 0)))
    for i, y in enumerate((-1.0, 1.0)):
        R.append((f'Knock_Left_{i + 1}', (-3.4, y, 1.6), (1, 0, 0)))
    R += [('Knock_Roof_1', (-1.0, -0.5, 4.0), (0, 0, -1)), ('Knock_Roof_2', (1.0, 0.8, 4.0), (0, 0, -1)),
          ('Knock_Window_Front', (-0.30, -3.0, 1.95), (0, 1, 0)), ('Knock_Window_Left', (-3.4, -0.30, 1.95), (1, 0, 0)),
          ('Knock_Door', (0.75, 3.0, 1.75), (0, -1, 0))]
    return R


def build_kpp():
    shell()
    door()
    furniture()
    props()
    lamps()
    outside()
    play_points()
    part('Checkpoint', 'static', (0, 0, 0), parent=None,
         note='the booth: pad, bollards, walls, windows, roof, desk, cabinet carcasses, the key cabinet, corkboard, heater, '
              'bulkhead; prefab root (the map\'s Checkpoint prefab, same place)')
    part('Window_Glass', 'static', (0, 0, 1.8), parent='Checkpoint', note='the fixed panes (glass material)')
    barrier()
    gate()
    place_roots()
