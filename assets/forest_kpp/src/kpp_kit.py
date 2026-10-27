"""Checkpoint (KPP) v2 at the station road, Forest map prologue (Forest_Opening.json S6, X05; QUESTIONS_KPP.md «Решено»):
the v1 booth, barrier and gate (the Update 3 places, the generator shed's construction and finishes, the station's grey-green)
made electric, with the small things as snow_kit instances (snowkit_spec / SNOW_KIT_CONTRACT.md) instead of KPP meshes.
  booth (root Checkpoint): as v1 - pad, bollards, board-and-batten walls, the mono-pitch roof, the KONTROLLPUNKT /
  CHECKPOINT board, the ribbon window, the road-side pass window (IX_BoothWindow_302), the left window, the back door
  (IX_BoothDoor_74) now held by the electric lock (Kit_DoorLock on the leaf, Kit_DoorLock_Strike on the trim), the desks,
  drawers (IX_Drawer_75..80), the key cabinet (IX_KeyBoxDoor_303; the Schranke hook is gone), corkboard, heater, clock,
  first aid, vests, extinguisher, radio; on the desk by the pass window two CRT monitors (Kit_Monitor_CRT) and the console
  (Kit_Console_2 with two Kit_Console_Button: SCHRANKE / BARRIER, TOR / GATE); the phone is Kit_Phone (same place, the
  names Phone / Phone_Receiver / Phone_Dial kept); outside: the distribution cabinet Kit_Cabinet_Power on the back wall
  (the van's battery, two clamps, NETZ / BATTERIE), the conduit up to the roof stand Kit_RoofStand through the back eave,
  the service drop from the transformer pole (Kit_Pole_Trafo) behind the booth, the line pole Kit_Pole up the road; the
  barrier's cable in conduit (Kit_Conduit_*) on the ground to the junction box (Kit_JunctionBox) on the road-side wall;
  the barrier camera (Kit_Camera_BracketWall + Kit_Camera_Head) under the front eave.
  barrier (root Barrier, 7 m out on the road): electric - the motor cabinet with the beacon (Kit_Beacon), the white-red boom
  (IX_BarrierArm_82: same pivot, axis and 0..80 as v1), the rest post with its fork; the v1 hand barrier stays as its own
  root Barrier_Manual (its parts renamed _Manual), off the map in this file.
  gate (root Gate, beside the booth here, at the yard in the game): a solid painted sliding leaf (IX_Gate_81: same origin,
  axis and 0..6.6 m as v1) on a ground rail 0.50 m inside the wall line, the SPERRGEBIET / VIDEOÜBERWACHT plate, concrete
  end posts in the wall line (the Update 7 PO-2 runs end at them), the receiving post, the guide posts, the drive cabinet
  with its pinion on the leaf's rack, its cable in conduit up the line pole (Kit_Pole) with a junction box, the gate camera
  (Kit_Camera_BracketPole + Kit_Camera_Head) on that pole.
Frame (the Update 3 Checkpoint prefab's): x toward the road, y toward the back (the door, the station side), z up, metres;
origin = the middle of the pad on the ground; floor z = 0.15.  Unity: (x, y, z) -> (-x, z, -y), angle -> -angle.
Kit instances: KIT_INST (name -> item, parent, 4x4 in this file's world, IX ids); kpp_build places them as KIT_ empties."""
import math, os, json
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
PAD_Z0 = -0.45                                         # its sides go into the ground (v2: deeper - in the game the ground
                                                       # is 0.39 down at the front, 0.02 at the back)
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
HOOKS = [('Hauptgebaeude', -0.60), ('Garage', -0.50), ('Generator', -0.40), ('Stationsleiter', -0.30)]   # v2: no Schranke
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
Z_BARCAB, Z_GATEP = 152, 153                         # v2: the motor cabinets (light grey), the gate leaf (station green)
KPP_ZONES = [Z_SLAB, Z_FLOOR, Z_CLAD, Z_TRIMW, Z_LINING, Z_TIMBER, Z_ROOF, Z_ROOFUNDER, Z_DOOR, Z_DOORIN, Z_STEELBLK, Z_GALV,
             Z_ENAMEL_IN] + list(range(140, 154))
(Z_PHONE, Z_VEST, Z_EXTP, Z_CRT, Z_CHAIR, Z_BLACKP, Z_BELLP, Z_PAPERP, Z_MUGP, Z_FLASK, Z_BINDER, Z_RADIO, Z_CAMP,
 Z_CHROMEP, Z_FAID) = range(170, 185)
PROP_ZONES = list(range(170, 185))
FAID = dict(x0=-0.05, x1=0.25, y0=IY1 - 0.10, z0=1.38, z1=1.62)     # first-aid box under the clock

# ---------------------------------------------------------------- v2: the barrier, the gate, the hand barrier, the kit
BARRIER_MANUAL_PLACE = (Vector((3.10, -14.00, -0.3867)), 0.0)   # the v1 hand barrier: its own root, off the map, 7 m further out
WALLBOX = Vector((-1.55, -0.095, 0.95))                # barrier frame: Kit_JunctionBox on the wall's end panel (street face)
BAR2 = dict(pad=(-0.40, 0.40, -0.40, 0.50), cab=(-0.18, 0.18, 0.06, 0.38, 0.15, 1.32), rest_pad=(5.40, 5.75, -0.20, 0.20))
GATE2 = dict(ly=0.50, z=(0.12, 2.40), post_e=(-7.45, -7.15), post_w=(0.15, 0.45), post_h=2.70, rail=(-7.10, 6.80),
             drive=(-0.32, -0.02, 0.64, 0.90, 0.03, 0.42), guide_x=0.04, guide_x_out=-0.10, pole=(1.60, 2.20),
             campole=(0.95, 1.45), camcond_y=0.80)
# campole: the gate camera's own mast (Kit_Mast) inside the wall, west of the opening, clear of the parked leaf, the drive
# and the line pole; its cable along the ground at y camcond_y into the drive's base (v2.1)
# guide_x_out: the street-side guide stand sits 0.14 m further into the opening than the yard-side one, so that it clears
# the west run's start socket (U7 5649: x -0.025..0.925, y up to 0.375); the yard-side one stays clear of the drive
CAB_POS = Vector((-1.20, Y1, 0.85))                     # Kit_Cabinet_Power on the back wall outside (its origin: back middle)
RS_POS = Vector((-1.20, Y1, 1.55))                      # Kit_RoofStand on the back wall (its origin: the pipe's bottom end)
JB_POS = Vector((X1, -1.30, 0.55))                      # Kit_JunctionBox on the road-side wall (the barrier's cable)
CAMPOLE_B = Vector((1.50, -5.50, -0.386))               # v2.1: the barrier camera's own mast (Kit_Mast) between the booth
                                                        # and the barrier (ground from the game terrain: kpp2_ground.py)
CAMB_T = Vector((6.00, -9.50, 0.30))                    # it looks over the boom at the road outside, where cars stop
FLOODB_T = Vector((5.00, -8.00, 0.0))                   # the floodlight under it lights the boom and the road in front of it
POLE1 = Vector((-1.50, 9.00, -0.107))                   # Kit_Pole_Trafo behind the booth (ground from the game terrain)
POLE2 = Vector((-0.50, 45.00, -2.035))                  # Kit_Pole up the road (the line goes on toward the base)
MON_A = (Vector((1.19, -1.245, DESK_TOP)), 192.0)       # Kit_Monitor_CRT: the barrier camera
MON_B = (Vector((1.62, -1.245, DESK_TOP)), 200.0)       # the gate camera
CONSOLE = (Vector((1.66, -0.825, DESK_TOP)), -90.0)      # Kit_Console_2 on the road-side desk under the pass window
IX_IDS = {'Btn_Schranke': {'IX_ConsoleButton': 312}, 'Btn_Tor': {'IX_ConsoleButton': 313},
          'PowerCabinet': {'IX_CabinetDoor': 314, 'IX_CabinetSwitch': 315, 'IX_CabinetClamp_Pos': 316, 'IX_CabinetClamp_Neg': 317}}

# ---------------------------------------------------------------- kit instances
KIT_CONTRACT = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'snow_kit_contract.json')))
KIT_INST = {}                     # name -> dict(item, parent, M (4x4 in this file's world), ids, note)


def R_yaw_tilt(yaw=0.0, tilt=0.0):
    """the item's front (-y) turned to (sin yaw, -cos yaw) in the plan, then tipped down by tilt (deg)"""
    return Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Matrix.Rotation(math.radians(tilt), 3, 'X')


def M_of(pos, yaw=0.0, tilt=0.0, R=None, sx=1.0):
    R = R if R is not None else R_yaw_tilt(yaw, tilt)
    return Matrix.Translation(Vector(pos)) @ R.to_4x4() @ Matrix.Diagonal((sx, 1.0, 1.0, 1.0))


def kit(name, item, parent, M, note='', ids=None):
    assert item in KIT_CONTRACT['items'], item
    assert name not in KIT_INST and name not in CONTRACT['parts'], name
    KIT_INST[name] = dict(item=item, parent=parent, M=M, ids=ids if ids is not None else IX_IDS.get(name, {}), note=note)
    return M


def ksock(item, sock):
    s = KIT_CONTRACT['sockets'][sock]
    assert s['item'] == item, (item, sock)
    return s


def at_sock(name, sock):
    """world point of a kit socket of instance `name`"""
    return KIT_INST[name]['M'] @ Vector(ksock(KIT_INST[name]['item'], sock)['pos'])


def dir_sock(name, sock, key='dir'):
    return (KIT_INST[name]['M'].to_3x3() @ Vector(ksock(KIT_INST[name]['item'], sock)[key])).normalized()


def M_slot(parent_name, sock):
    """frame on a kit slot socket (pos, dir -> +z, up -> +y) of instance parent_name, in this file's world"""
    s = ksock(KIT_INST[parent_name]['item'], sock)
    z, y = Vector(s['dir']).normalized(), Vector(s['up']).normalized()
    x = y.cross(z).normalized()
    return KIT_INST[parent_name]['M'] @ Matrix.Translation(Vector(s['pos'])) @ Matrix((x, y, z)).transposed().to_4x4()


def aim(src, dst):
    """yaw, tilt that point an item's front (-y) from src to dst"""
    d = Vector(dst) - Vector(src)
    yaw = math.degrees(math.atan2(d.x, -d.y))
    tilt = math.degrees(math.atan2(-d.z, math.hypot(d.x, d.y)))
    return yaw, tilt


CR = 0.016                                              # conduit radius (Kit_Conduit_*)


def camera_on_pole(tag, pole, target):
    """Kit_Camera_BracketPole on the mast's upper side mount (on its axis), turned about it toward target; Kit_Camera_Head on
    the bracket aimed at target (pan and tilt are the head's); names CamBracket_<tag>, Cam_<tag>"""
    mb = at_sock(pole, 'Mount_Side_1')
    kit('CamBracket_' + tag, 'Kit_Camera_BracketPole', pole, M_of(mb, yaw=aim(mb, target)[0]),
        note='camera bracket on the pole: turned about the pole\'s axis toward where the camera looks')
    mh = at_sock('CamBracket_' + tag, 'Mount_Head_Pole')
    yaw, tilt = aim(mh + Vector((0, 0, 0.08)), target)
    mon = 'Monitor_' + tag
    kit('Cam_' + tag, 'Kit_Camera_Head', 'CamBracket_' + tag, M_of(mh, yaw=yaw, tilt=tilt),
        note=f'the {tag.lower()} camera: {mon} shows it (CAM_{tag})')


def flood_on_pole(name, pole, target, note):
    """Kit_Mast_Flood on the mast's lower side mount, turned about its axis toward target (its head is tipped 30 down)"""
    mb = at_sock(pole, 'Mount_Side_2')
    kit(name, 'Kit_Mast_Flood', pole, M_of(mb, yaw=aim(mb, target)[0]), note=note)


WIRE_SPANS = []                   # (instance, item, (instance a, socket a), (instance b, socket b))


def wire_span(name, item, ea, eb, parent='Checkpoint'):
    """an overhead wire as a kit model (Kit_Wire_Bare / Kit_Wire_Drop): from socket ea to socket eb, turned (yaw, pitch) and
    scaled in x by span / the model's reference span"""
    A, B = at_sock(*ea), at_sock(*eb)
    L = KIT_CONTRACT['parts'][item]['span']
    d = B - A
    R = Matrix.Rotation(math.atan2(d.y, d.x), 3, 'Z') @ Matrix.Rotation(-math.atan2(d.z, math.hypot(d.x, d.y)), 3, 'Y')
    kit(name, item, parent, M_of(A, R=R, sx=d.length / L), note=f'overhead wire {ea[0]} {ea[1]} -> {eb[0]} {eb[1]}: '
                                                                  f'{d.length:.2f} m (x scale {d.length / L:.3f})')
    WIRE_SPANS.append((name, item, ea, eb))


def conduit_run(prefix, parent, pts, normals, entry0=None, entry1=None, clamp_every=1.0, note=''):
    """a conduit of Kit_Conduit_* along the polyline pts (90-degree corners: elbows; straight pieces scaled in x);
    normals[i]: the surface the i-th segment is fixed to lies along -normals[i] (clamps' feet there; None: no clamps);
    entry0 / entry1: put a Kit_Conduit_Entry at the first / last point (the box face), pointing along the run"""
    P = [Vector(p) for p in pts]
    n = len(P) - 1
    D = [(P[i + 1] - P[i]).normalized() for i in range(n)]
    seg = []
    for i in range(n):
        a = P[i] + (D[i] * 0.10 if i > 0 else Vector((0, 0, 0)))
        b = P[i + 1] - (D[i] * 0.10 if i < n - 1 else Vector((0, 0, 0)))
        if i == 0 and entry0:
            a = a + D[i] * 0.04
        if i == n - 1 and entry1:
            b = b - D[i] * 0.04
        seg.append((a, b))
    k = 0
    for i, (a, b) in enumerate(seg):
        L = (b - a).length
        d = D[i]
        up = normals[i] if normals[i] is not None else (Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0)))
        up = Vector(up)
        y_ = up.cross(d).normalized()
        z_ = d.cross(y_).normalized()
        Rs = Matrix((d, y_, z_)).transposed()
        kit(f'{prefix}_S{i + 1}', 'Kit_Conduit_Straight', parent, M_of(a, R=Rs, sx=L), note=note or f'conduit {L:.2f} m')
        if normals[i] is not None:
            m = max(1, int(L / clamp_every))
            for j in range(m):
                t = (j + 0.5) / m
                k += 1
                kit(f'{prefix}_C{k}', 'Kit_Conduit_Clamp', parent, M_of(a.lerp(b, t), R=Rs), note='clamp')
        if i < n - 1:
            d2 = D[i + 1]
            Re = Matrix((d, d2.cross(d).normalized(), d2)).transposed()
            kit(f'{prefix}_E{i + 1}', 'Kit_Conduit_Elbow', parent, M_of(P[i + 1] - d * 0.10, R=Re), note='elbow')
    for flag, p, d, tag in ((entry0, P[0], D[0], 'In'), (entry1, P[-1], -D[-1], 'Out')):
        if flag:
            z_ = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
            y_ = z_.cross(d).normalized()
            Rg = Matrix((d, y_, d.cross(y_).normalized())).transposed()
            kit(f'{prefix}_{tag}', 'Kit_Conduit_Entry', parent, M_of(p, R=Rg), note='gland into the box')


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
    # v2: the rubber flashing where the roof stand's pipe goes through the back eave (the pipe 0.12 m off the wall)
    pc = Vector((RS_POS.x, Y1 + 0.12, 0.0))
    k.lathe(Vector((pc.x, pc.y, z_st(pc.y) - 0.004)), (0, 0, 1), [(0.0, 0.085), (0.012, 0.085), (0.075, 0.036), (0.09, 0.034)],
            Z_STEELBLK, 12, cap0=False, cap1=False)
    k.lathe(Vector((pc.x, pc.y, z_sb(pc.y) - 0.025)), (0, 0, 1), [(0.0, 0.034), (0.025, 0.05)], Z_STEELBLK, 12, cap0=False, cap1=False)
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
              'sides; v2: held shut by the electric lock (DoorLock on the leaf, DoorLockStrike on the trim) until the booth has '
              'power, then it clicks open (Update 3: same name, hinge side and travel)')
    zl = 1.22
    kit('DoorLock', 'Kit_DoorLock', 'IX_BoothDoor_74', M_of((x0 + 0.065, yb, zl), yaw=180.0),
        note='electric rim lock on the leaf\'s outer face by the latch edge (moves with the door)')
    kit('DoorLockStrike', 'Kit_DoorLock_Strike', 'Checkpoint', M_of((0.36, Y1 + 0.025, zl), yaw=180.0),
        note='its strike on the white door trim; the lamp shows the power (green: released)')
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
         note='key cabinet door: hinged at its left edge, opens into the room (+) to 120; inside the hooks Hauptgebäude, Garage, '
              'Generator with their keys and the empty Stationsleiter hook; v2: no Schranke hook (the barrier has no padlock) '
              '(Update 3: same name, pivot and travel)')
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
    part('Kpp_Props', 'static', (0, 0, 0), parent='Checkpoint',
         note='small things not in the kit yet: vests, extinguisher, binders, thermos, mug, papers, the radio and its mic, the wall '
              'clock, the first-aid box (v1 had the CCTV monitor and camera here: now Kit_Monitor_CRT / Kit_Camera_* instances)')
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
    # v2: the phone, the monitors and the console are kit instances (snow_kit)
    kit('Phone', 'Kit_Phone', 'Checkpoint', M_of(PHONE, yaw=-90.0),
        note='rotary phone (Kit_Phone) by the pass window, the dial toward the guard: X05 rings it twice; zone Phone_KPP (Update 3) '
             'is round its Phone_Receiver (the names Phone / Phone_Receiver / Phone_Dial are v1\'s)')
    kit('Monitor_Barrier', 'Kit_Monitor_CRT', 'Checkpoint', M_of(MON_A[0], yaw=MON_A[1]),
        note='CRT monitor: the barrier camera (Cam_Barrier) with the power')
    kit('Monitor_Gate', 'Kit_Monitor_CRT', 'Checkpoint', M_of(MON_B[0], yaw=MON_B[1]),
        note='CRT monitor: the gate camera (Cam_Gate) with the power')
    kit('Console', 'Kit_Console_2', 'Checkpoint', M_of(CONSOLE[0], yaw=CONSOLE[1]),
        note='the console under the pass window: SCHRANKE / BARRIER (left), TOR / GATE (right)')
    for i, (key, lab) in enumerate((('Schranke', 'Kit_Console_Label_Schranke'), ('Tor', 'Kit_Console_Label_Tor'))):
        kit('Btn_' + key, 'Kit_Console_Button', 'Console', M_slot('Console', f'Slot_Button_{i + 1}'),
            note=('raises / lowers the barrier (needs the power)' if key == 'Schranke' else 'opens / closes the base gate (needs the power)'))
        kit('Lbl_' + key, lab, 'Console', M_slot('Console', f'Slot_Label_{i + 1}'), note='its label')
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
         note='fluorescent batten under the rafters: v2 - dark without power, lights with the booth\'s power (flickers a few '
              'seconds as it strikes); v1 / Update 3 flickered from the start (Light_booth, M_Lamp_FluorFlicker)')
    tc = c + Vector((-0.58, 0, -0.038))
    G = kb('Lens_Fluor', 'lens:fluor')
    G.lathe(tc, (1, 0, 0), [(0.0, 0.0135), (1.16, 0.0135)], ZERO, 8, cap0=True, cap1=True)
    uv_cyl(G, tc, 0.0, 1.16, uv('l_fluor'), axis=(1, 0, 0))
    part('Lens_Fluor', 'static', c + Vector((0, 0, -0.038)), parent='Lamp_Fluor',
         note='the tube: M_Kpp_Lamp_Fluor (lit) / M_Kpp_Lamp_Fluor_Off')
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
         note='frosted dome of the bulkhead over the door: lit with the booth\'s power (M_Kpp_Lamp_Bulk / _Off)')
    Gb = kb('Glow_Bulk_Door', 'glow')
    quad(Gb, dc + Vector((0, 0.045, 0)), (0, 1, 0), 0.50, 0.50, uv('glow_warm'))
    u0, v0, u1, v1 = uv('glow_warm')
    quad(Gb, Vector((dc.x, Y1 + 0.17, dc.z - 0.002)), (0, 0, -1), 0.50, 0.32, (u0, v0, u1, (v0 + v1) / 2), up=(0, -1, 0))
    part('Glow_Bulk_Door', 'static', dc, parent='Checkpoint', note='halo cards of the bulkhead: shown with the power')
    LAMPS.append(('Bulk_Door', dc + Vector((0, 0.06, -0.02)), (0, 0.6, -0.8), 'bulkhead_kpp', (0, 0, 1)))


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


# ================================================================ v2: the power outside (kit instances)
def outside_kit():
    """the distribution cabinet, its conduit up to the roof stand, the barrier's cable to the junction box, the barrier
    camera, the line poles; all instances of snow_kit"""
    kit('PowerCabinet', 'Kit_Cabinet_Power', 'Checkpoint', M_of(CAB_POS, yaw=180.0),
        note='the distribution cabinet on the back wall: the van\'s battery on its shelf, both clamps on and the switch at '
             'BATTERIE give the booth power (the line from the base is dead)')
    kit('RoofStand', 'Kit_RoofStand', 'Checkpoint', M_of(RS_POS, yaw=180.0),
        note='the roof stand through the back eave: the service drop from the transformer pole ends on its spools')
    a = at_sock('PowerCabinet', 'Conduit_Top')
    b = at_sock('RoofStand', 'Conduit_Bottom_R')
    conduit_run('Cond_Cab', 'Checkpoint', [a, b], [None], entry0=True, note='conduit from the cabinet up to the roof stand')
    # the barrier's cable: from its pad along the ground, into the booth pad's road side; up from the pad into the box
    kit('JunctionBox', 'Kit_JunctionBox', 'Checkpoint', M_of(JB_POS, yaw=90.0), note='the barrier\'s cable comes in here')
    zg = BARRIER_PLACE[0].z + CR                             # the conduit lies on the ground (the barrier's level)
    p0 = Vector((BARRIER_PLACE[0].x - 0.20, BARRIER_PLACE[0].y + BAR2['pad'][3], zg))     # off the road (its edge ~2.7)
    c1 = Vector((p0.x, p0.y + 0.60, zg))
    c2 = Vector((2.00, c1.y, zg))
    p3 = Vector((2.00, PAD[2], zg))
    up = Vector((0, 0, 1))
    conduit_run('Cond_Bar', 'Checkpoint', [p0, c1, c2, p3], [up, up, up], entry0=True,
                note='the barrier\'s cable on the ground, into the booth pad\'s front')
    jb = at_sock('JunctionBox', 'Conduit_Bottom_JB')
    conduit_run('Cond_JB', 'Checkpoint', [Vector((jb.x, jb.y, FLOOR)), jb], [None], entry1=True,
                note='up from the pad into the junction box')
    # v2.1: the barrier camera on its own pole between the booth and the barrier (the eave bracket is gone); its cable out of
    # the footing in conduit along the ground into the booth pad's front, beside the barrier's
    kit('CamPole_Barrier', 'Kit_Mast', 'Checkpoint', M_of(CAMPOLE_B),
        note='the barrier camera\'s mast (4.2 m, concrete footing) between the booth and the barrier')
    camera_on_pole('Barrier', 'CamPole_Barrier', CAMB_T)
    flood_on_pole('Flood_Barrier', 'CamPole_Barrier', FLOODB_T, 'floodlight under the camera: lights the boom and the road in '
                                                               'front of it while the booth has power')
    cb = at_sock('CamPole_Barrier', 'Conduit_Base')
    conduit_run('Cond_CamBar', 'Checkpoint', [cb, Vector((cb.x, PAD[2], cb.z))], [Vector((0, 0, 1))], entry0=True,
                note='the barrier camera\'s cable out of its pole\'s footing along the ground into the booth pad\'s front')
    # the line: the transformer pole behind the booth (the drop to the roof stand), the next pole up the road
    kit('Pole_1', 'Kit_Pole_Trafo', 'Checkpoint', M_of(POLE1), note='transformer pole: the 20 kV line from the base ends here; '
                                                                    'its 0.4 kV drop goes to the roof stand')
    kit('Pole_2', 'Kit_Pole', 'Checkpoint', M_of(POLE2), note='line pole up the road; the line goes on toward the base (Unity '
                                                              'places the rest of the poles)')
    # v2.1: the overhead wires as kit models: the drop (Kit_Wire_Drop x4, Pole_1's spools -> the roof stand, paired in x) and
    # the line (Kit_Wire_Bare x3, Pole_1 -> Pole_2)
    p1 = sorted(['Wire_4_T', 'Wire_5_T', 'Wire_6_T', 'Wire_7_T'], key=lambda w: at_sock('Pole_1', w).x)
    rs = sorted(['Wire_1_R', 'Wire_2_R', 'Wire_3_R', 'Wire_4_R'], key=lambda w: at_sock('RoofStand', w).x)
    for i, (a, b) in enumerate(zip(p1, rs)):
        wire_span(f'Wire_Drop_{i + 1}', 'Kit_Wire_Drop', ('Pole_1', a), ('RoofStand', b))
    for i in (1, 2, 3):
        wire_span(f'Wire_Line_{i}', 'Kit_Wire_Bare', ('Pole_1', f'Wire_{i}_T'), ('Pole_2', f'Wire_{i}'))


# ================================================================ the barrier (own root, 7 m out on the road): v2 electric
def barrier():
    B = kb('Barrier', 'KppYard')
    x0, x1, y0, y1 = BAR2['pad']
    box6(B, (x0, y0, -0.15), (x1, y1, 0.15), Z_CONC, skip=('-z',))
    # the motor cabinet (light grey, the black cover), its service door on the inside (+y), vents, the shaft's flange
    cx0, cx1, cy0, cy1, cz0, cz1 = BAR2['cab']
    VM.rbox(B, ((cx0 + cx1) / 2, (cy0 + cy1) / 2, (cz0 + cz1) / 2), (cx1 - cx0, cy1 - cy0, cz1 - cz0), Z_BARCAB, r=0.02, ch=0.008)
    B.box(cx0 - 0.012, cx1 + 0.012, cy0 - 0.012, cy1 + 0.012, cz1, cz1 + 0.035, Z_RUBBER_K)
    B.box(cx0 + 0.035, cx1 - 0.035, cy1, cy1 + 0.004, cz0 + 0.12, cz1 - 0.12, Z_BARCAB)
    B.box(cx1 - 0.065, cx1 - 0.05, cy1 + 0.004, cy1 + 0.016, 0.70, 0.78, Z_STEELBLK)
    for zh in (cz0 + 0.20, cz1 - 0.20):
        B.cyl(Vector((cx0 + 0.03, cy1 + 0.006, zh - 0.03)), Vector((cx0 + 0.03, cy1 + 0.006, zh + 0.03)), 0.006, Z_STEELBLK, 6)
    for zv in (0.98, 1.02, 1.06):
        B.box(cx0 - 0.003, cx0, cy0 + 0.07, cy1 - 0.07, zv, zv + 0.012, Z_STEELBLK)
    B.lathe(Vector((0, cy0, BOOM_PIV.z)), (0, -1, 0), [(0.0, 0.075), (0.015, 0.075), (0.015, 0.045), (0.045, 0.035), (0.045, 0.0)],
            Z_STEELBLK, 12)
    Sv = kb('Barrier_Sticker', 'panel')
    quad(Sv, (0.0, cy0 - 0.0015, 0.72), (0, -1, 0), 0.10, 0.0875, uv('sign_volt'))
    part('Barrier_Sticker', 'static', (0.0, cy0, 0.72), parent='Barrier', note='lightning sticker on the motor cabinet (panel atlas)')
    kit('Beacon_Barrier', 'Kit_Beacon', 'Barrier', M_of((0.0, (cy0 + cy1) / 2, cz1 + 0.035)),
        note='the beacon on the cabinet: turns while the boom moves (with the power)')
    # the barrier's box on the wall (the concept): on the street face of the wall's end panel (Update 7 5852: x -3.39..-0.91,
    # its relief face at y -0.093), past its socket (x -1.375..-0.425, y +-0.375, 8 cm high); its conduit out of the pad's
    # street edge along the ground and up the panel. (The cable to the booth: Cond_Bar, from the pad's inner edge.)
    kit('JunctionBox_Wall', 'Kit_JunctionBox', 'Barrier', M_of(WALLBOX), note='the barrier\'s box on the wall\'s end panel '
                                                                              '(street side), as in the concept')
    jw = at_sock('JunctionBox_Wall', 'Conduit_Bottom_JB')
    up = Vector((0, 0, 1))
    conduit_run('Cond_BarWall', 'Barrier', [Vector((-0.30, BAR2['pad'][2], CR)), Vector((-0.30, -0.62, CR)),
                                            Vector((jw.x, -0.62, CR)), Vector((jw.x, jw.y, CR)), jw],
                [up, up, up, None], entry0=True, entry1=True,              # up the panel: no clamps (the box's knock-out stands 4 cm off it)
                note='from the cabinet along the ground and up the wall panel into its box')
    # the rest post with its fork and a rubber pad the boom lies on
    qx = REST_X
    rx0, rx1, ry0, ry1 = BAR2['rest_pad']
    box6(B, (rx0, ry0, -0.15), (rx1, ry1, 0.12), Z_CONC, skip=('-z',))
    B.cyl(Vector((qx, 0, 0.12)), Vector((qx, 0, 0.96)), 0.04, Z_BARPOST, 8)
    B.box(qx - 0.12, qx + 0.12, -0.075, 0.075, 0.96, 0.98, Z_STEELBLK)
    for sy in (-1, 1):
        B.box(qx - 0.10, qx + 0.10, sy * 0.065 - 0.008, sy * 0.065 + 0.008, 0.98, 1.21, Z_STEELBLK)
    B.box(qx - 0.08, qx + 0.08, -0.057, 0.057, 1.075, 1.095, Z_RUBBER_K)
    # the boom (IX_BarrierArm_82): white with red bands (the painter), the hub clamp on the motor's shaft, the end caps, the
    # rubber strip under it; no counterweight (springs in the cabinet)
    A = kb('IX_BarrierArm_82', 'KppYard')
    pz = BOOM_PIV.z
    xm_ = (0.12 + BOOM_LEN - 0.06) / 2
    for xa_, xb_ in ((0.12, xm_), (xm_, BOOM_LEN - 0.06)):
        VM.rbox(A, ((xa_ + xb_) / 2, 0, pz), (xb_ - xa_, 0.09, 0.11), Z_BOOM, r=0.015, ch=0.008, axis='x')
    VM.rbox(A, (xm_, 0, pz), (0.14, 0.104, 0.124), Z_STEELBLK, r=0.018, ch=0.008, axis='x')
    VM.rbox(A, (-0.04, 0, pz), (0.32, 0.12, 0.16), Z_BARCAB, r=0.02, ch=0.01, axis='x')
    A.box(-0.24, -0.20, -0.045, 0.045, pz - 0.055, pz + 0.055, Z_RUBBER_K)
    A.box(BOOM_LEN - 0.06, BOOM_LEN, -0.05, 0.05, pz - 0.06, pz + 0.06, Z_RUBBER_K)
    A.box(0.25, BOOM_LEN - 0.06, -0.03, 0.03, pz - 0.075, pz - 0.055, Z_RUBBER_K)
    part('IX_BarrierArm_82', 'hinge', BOOM_PIV, (0, -1, 0), (0, 80), parent='Barrier', states=['down', 'up'],
         note='barrier boom, v2 electric: the motor lifts it (+, to 80) in about 4 s when the console\'s SCHRANKE button is '
              'pressed with the booth powered, and lowers it the same way; no padlock, not by hand (same name, pivot, axis and '
              'travel as v1 / Update 3)')
    socket('Audio_Barrier', BOOM_PIV, 'audio', parent='Barrier', note='boom: the springs creak, it thuds on the rest\'s rubber')
    socket('Audio_BarrierMotor', ((cx0 + cx1) / 2, (cy0 + cy1) / 2, 0.85), 'audio', parent='Barrier',
           note='the motor whirs while the boom moves, a clunk at each end')
    part('Barrier', 'static', (0, 0, 0), parent=None, yaw=BARRIER_PLACE[1],
         note='electric barrier 7 m out on the road in front of the booth (separate root: the map\'s Barrier prefab, same place); '
              'the motor cabinet with the beacon, the boom, the rest post; its cable in conduit to the booth')


# ================================================================ the v1 hand barrier: its own root Barrier_Manual (off the map)
def barrier_manual():
    B = kb('Barrier_Manual', 'KppYard')
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
    socket('Spot_Padlock_Manual', PADLOCK, 'item_slot', parent='Barrier_Manual',
           note='Padlock_Barrier hangs here through the post eye and the boom eye (its origin is the hanging point; '
                'Forest_Opening.json, same place as Update 3)')
    # the boom (IX_BarrierArm_82): striped box tube, the counterweight on the short side, the hub, the boom eye, the tip
    A = kb('IX_BarrierArm_Manual_318', 'KppYard')
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
    part('IX_BarrierArm_Manual_318', 'hinge', BOOM_PIV, (0, -1, 0), (0, 80), parent='Barrier_Manual', states=['down', 'up'],
         note='barrier boom: lift by hand (+, up to 80) once Padlock_Barrier is off; the counterweight swings down beside the post '
              '(Update 3: same name, pivot and travel)')
    socket('Hand_BarrierArm_Manual', (BOOM_LEN - 0.6, 0, pz + 0.07), 'hand', parent='IX_BarrierArm_Manual_318', note='lift it here')
    socket('Audio_Barrier_Manual', BOOM_PIV, 'audio', parent='Barrier_Manual', note='boom: the bearing creaks, the counterweight thuds at the top')
    part('Barrier_Manual', 'static', (0, 0, 0), parent=None, yaw=BARRIER_MANUAL_PLACE[1],
         note='the v1 hand barrier (padlock, counterweight), kept as its own prefab Barrier_Manual: not on the map; here 7 m '
              'further out than the electric one so they do not overlap')


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
    """v2: a solid painted leaf on the ground rail 0.50 m inside the wall line, concrete end posts in the line, the receiving
    post, two guide posts with top rollers, the drive cabinet (pinion on the leaf's rack), its cable up the line pole"""
    Gt = kb('Gate', 'KppYard')
    ly = GATE2['ly']
    zb, zt = GATE2['z']
    lx0, lx1 = GATE_LEAF
    # end posts in the wall line (the Update 7 PO-2 runs end at them): concrete, a footing, a chamfered cap
    for (xa, xb) in (GATE2['post_e'], GATE2['post_w']):
        box6(Gt, (xa - 0.05, -0.20, -0.30), (xb + 0.05, 0.20, 0.02), Z_CONC, skip=('-z',))
        box6(Gt, (xa, -0.15, 0.02), (xb, 0.15, GATE2['post_h']), Z_CONC, skip=('-z', '+z'))
        prism_x(Gt, [(-0.17, GATE2['post_h']), (0.17, GATE2['post_h']), (0.17, GATE2['post_h'] + 0.03), (0.0, GATE2['post_h'] + 0.09),
                     (-0.17, GATE2['post_h'] + 0.03)], xa - 0.02, xb + 0.02, Z_CONC, Z_CONC)
    # the receiving post at the leaf's line, its catch and rubber; the rail in its concrete strip; the end stop
    box6(Gt, (-7.40, ly - 0.23, -0.15), (-6.95, ly + 0.23, 0.03), Z_CONC, skip=('-z',))
    box6(Gt, (-7.16, ly - 0.04, 0.03), (-7.08, ly + 0.04, zt + 0.05), Z_GALV, skip=('-z',))
    for zc in (0.25, zt - 0.20):
        for sgn in (-1, 1):
            Gt.box(-7.08, -6.90, ly + sgn * 0.050 - 0.005, ly + sgn * 0.050 + 0.005, zc - 0.05, zc + 0.05, Z_STEELBLK)
        Gt.box(-7.08, -7.02, ly - 0.045, ly + 0.045, zc - 0.04, zc + 0.04, Z_RUBBER_K)
    ra, rb = GATE2['rail']
    box6_x(Gt, (ra, ly - 0.10, -0.05), (rb, ly + 0.10, 0.010), Z_CONC, skip=('-z', '-x', '+x', '-y', '+y'))
    box6_x(Gt, (ra + 0.05, ly - 0.02, 0.010), (rb - 0.05, ly + 0.02, 0.045), Z_STEELBLK, skip=('-z',))
    box6(Gt, (6.66, ly - 0.15, -0.15), (7.00, ly + 0.15, 0.010), Z_CONC, skip=('-z', '-x'))
    box6(Gt, (6.68, ly - 0.04, 0.010), (6.76, ly + 0.04, 0.60), Z_GALV, skip=('-z',))
    Gt.box(6.62, 6.68, ly - 0.03, ly + 0.03, 0.165, 0.225, Z_RUBBER_K)
    # two guide posts beside the leaf's free end (past the opening), rollers at the top on both faces
    for yp, gx in ((ly - 0.13, GATE2['guide_x_out']), (ly + 0.13, GATE2['guide_x'])):
        box6(Gt, (gx - 0.16, yp - 0.12, -0.15), (gx + 0.20, yp + 0.12, 0.03), Z_CONC, skip=('-z',))
        box6(Gt, (gx - 0.04, yp - 0.04, 0.03), (gx + 0.04, yp + 0.04, zt + 0.15), Z_GALV, skip=('-z',))
        sgn = 1 if yp > ly else -1
        rl = ly + sgn * 0.068
        Gt.box(gx - 0.02, gx + 0.02, *sorted((yp - sgn * 0.04, rl)), zt + 0.06, zt + 0.09, Z_GALV)
        Gt.lathe(Vector((gx, rl, zt - 0.08)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.026), (0.13, 0.026), (0.13, 0.0)], Z_GATEROLL, 10)
    # the drive: a light grey cabinet on a concrete base inside, the pinion shaft to the leaf's rack, the release lock
    dx0, dx1, dy0, dy1, dz0, dz1 = GATE2['drive']
    box6(Gt, (dx0 - 0.04, dy0 - 0.04, -0.10), (dx1 + 0.04, dy1 + 0.04, dz0), Z_CONC, skip=('-z',))
    VM.rbox(Gt, ((dx0 + dx1) / 2, (dy0 + dy1) / 2, (dz0 + dz1) / 2), (dx1 - dx0, dy1 - dy0, dz1 - dz0), Z_BARCAB, r=0.015, ch=0.006)
    Gt.box(dx0 - 0.01, dx1 + 0.01, dy0 - 0.01, dy1 + 0.01, dz1, dz1 + 0.03, Z_RUBBER_K)
    xp = (dx0 + dx1) / 2
    Gt.cyl(Vector((xp, dy0, 0.175)), Vector((xp, ly + 0.065, 0.175)), 0.012, Z_STEELBLK, 8)
    Gt.lathe(Vector((xp, ly + 0.10, 0.175)), (0, -1, 0), [(0.0, 0.0), (0.0, 0.035), (0.03, 0.035), (0.03, 0.0)], Z_STEELBLK, 12)
    Gt.box(dx1 - 0.06, dx1 - 0.03, dy1, dy1 + 0.012, dz1 - 0.12, dz1 - 0.08, Z_STEELBLK)
    Sv = kb('Gate_Sticker', 'panel')
    quad(Sv, (xp, dy1 + 0.0015, 0.26), (0, 1, 0), 0.10, 0.0875, uv('sign_volt'))
    part('Gate_Sticker', 'static', (xp, dy1, 0.26), parent='Gate', note='lightning sticker on the drive (panel atlas)')
    # the leaf (IX_Gate_81): frame, the sheet on the outer face, inner rails and braces, the rack, wheels, barbed arms, the plate
    L = kb('IX_Gate_81', 'KppYard')
    yo, yi = ly - 0.04, ly + 0.04
    box6_x(L, (lx0, yo + 0.005, zb), (lx1, yi, zb + 0.08), Z_GATEP)
    box6_x(L, (lx0, yo + 0.005, zt - 0.08), (lx1, yi, zt), Z_GATEP)
    for xa_, xb_ in ((lx0, lx0 + 0.06), (lx1 - 0.06, lx1)):
        box6(L, (xa_, yo + 0.005, zb + 0.08), (xb_, yi, zt - 0.08), Z_GATEP, skip=('-z', '+z'))
    box6_x(L, (lx0 + 0.06, yo, zb + 0.08), (lx1 - 0.06, yo + 0.005, zt - 0.08), {'-y': Z_GATEP, '*': Z_GATEP}, skip=('+y',))
    box6_x(L, (lx0 + 0.06, yo + 0.005, 1.22), (lx1 - 0.06, yi, 1.30), Z_GATEP, skip=('-y',))
    nv = 7
    for i in range(1, nv):
        xv = lx0 + i * (lx1 - lx0) / nv
        box6(L, (xv - 0.025, yo + 0.005, zb + 0.08), (xv + 0.025, yi - 0.01, zt - 0.08), Z_GATEP, skip=('-y', '-z', '+z'))
    for i in range(nv):
        xa_, xb_ = lx0 + i * (lx1 - lx0) / nv + 0.03, lx0 + (i + 1) * (lx1 - lx0) / nv - 0.03
        a_, b_ = (Vector((xa_, ly + 0.012, zb + 0.10)), Vector((xb_, ly + 0.012, 1.20))) if i % 2 == 0 else \
            (Vector((xa_, ly + 0.012, 1.20)), Vector((xb_, ly + 0.012, zb + 0.10)))
        L.strip([a_, b_], Vector((0, 1, 0)), 0.04, 0.024, Z_GATEP)
    box6_x(L, (lx0 + 0.10, yi, zb + 0.02), (lx1 - 0.10, yi + 0.025, zb + 0.07), Z_STEELBLK, skip=('-y',))    # the rack
    for xw in (lx0 + 0.33, lx1 - 0.40):
        for sgn in (-1, 1):
            L.box(xw - 0.05, xw + 0.05, ly + sgn * 0.03 - 0.004, ly + sgn * 0.03 + 0.004, 0.08, zb + 0.01, Z_STEELBLK)
        L.lathe(Vector((xw, ly - 0.022, 0.10)), (0, 1, 0), [(0.0, 0.03), (0.008, 0.055), (0.022, 0.045), (0.036, 0.055),
                                                            (0.044, 0.03)], Z_GATEROLL, 10)
    for i in range(8):
        xv = lx0 + 0.03 + i * (lx1 - lx0 - 0.06) / 7
        box6(L, (xv - 0.012, ly - 0.012, zt), (xv + 0.012, ly + 0.012, zt + 0.42), Z_GATEP, skip=('-z',))
    Lb = kb('IX_Gate_81_Barbed', 'barbed')
    barbed_band(Lb, ly, lx0, lx1, zt + 0.04)
    Sg = kb('IX_Gate_81_Sign', 'panel')
    quad(Sg, (-3.50, yo - 0.0015, 1.45), (0, -1, 0), 0.90, 0.70, uv('sign_sperr2'))
    part('IX_Gate_81', 'slide', (lx0, 0.0, 0.0), (1, 0, 0), (0, GATE_TRAVEL), unit='m', parent='Gate', states=['shut', 'open'],
         note='sliding gate leaf, v2: solid painted sheet on a frame, on the ground rail 0.50 m inside the wall line; the drive '
              'moves it 6.6 m (+x, behind the wall) in about 12 s by one press of TOR on the KPP console (same name, origin, '
              'axis and travel as v1 / Update 3)')
    part('IX_Gate_81_Barbed', 'static', ((lx0 + lx1) / 2, ly, zt + 0.22), parent='IX_Gate_81',
         note='barbed wire on the leaf\'s upright arms: alpha band M_Kpp_Barbed (three strands)')
    part('IX_Gate_81_Sign', 'static', (-3.50, yo, 1.45), parent='IX_Gate_81',
         note='SPERRGEBIET / RESTRICTED AREA, ZUTRITT VERBOTEN / NO ENTRY, VIDEOÜBERWACHT / CCTV on the outer face (panel atlas)')
    socket('Audio_Gate', (-3.5, ly, 0.10), 'audio', parent='IX_Gate_81', note='wheels rumble on the rail, the sheet booms')
    socket('Audio_GateCatch', (-7.10, ly, 1.0), 'audio', parent='Gate', note='the catch clanks when the leaf closes')
    socket('Audio_GateMotor', (xp, (dy0 + dy1) / 2, 0.25), 'audio', parent='Gate', note='the drive hums, the pinion rattles on the '
                                                                                        'rack, a clunk at each end')
    # the line pole inside the wall with the drive's cable up it (a junction box at 3 m)
    px, py = GATE2['pole']
    kit('Pole_Gate', 'Kit_Pole', 'Gate', M_of((px, py, 0.0)), note='line pole inside the wall: the drive\'s cable goes up it to '
                                                                 'the line; Unity continues the line from here to the KPP')
    jb = Vector((px - 0.13, py, 3.0))
    kit('JunctionBox_Gate', 'Kit_JunctionBox', 'Gate', M_of(jb, yaw=-90.0), note='junction box on the pole')
    jb_bot = at_sock('JunctionBox_Gate', 'Conduit_Bottom_JB')
    jb_top = at_sock('JunctionBox_Gate', 'Conduit_Top_JB')
    xr = jb_bot.x
    gs = Vector((xp, dy1 + 0.04, CR))
    conduit_run('Cond_Gate', 'Gate', [gs, Vector((xp, py, CR)), Vector((xr, py, CR)), jb_bot],
                [Vector((0, 0, 1)), Vector((0, 0, 1)), Vector((-1, 0, 0))], entry0=True, entry1=True,
                note='the drive\'s cable along the ground and up the pole')
    conduit_run('Cond_GateUp', 'Gate', [jb_top, Vector((xr, py, 7.45)), Vector((xr - 0.25, py, 7.45))],
                [Vector((-1, 0, 0)), None], entry0=True, note='up the pole to the line')
    # v2.1: the gate camera on its own pole west of the opening (it was on the line pole); the footing's cable outlet faces
    # the gate (-y): along the ground to y camcond_y, then into the drive's base on its +x face
    CAMG_T = Vector((-4.5, -2.5, 0.0))         # the camera looks over the leaf at the opening and the road outside
    cpx, cpy = GATE2['campole']
    kit('CamPole_Gate', 'Kit_Mast', 'Gate', M_of((cpx, cpy, 0.0), yaw=180.0),
        note='the gate camera\'s mast (4.2 m, concrete footing) inside the wall, west of the opening')
    camera_on_pole('Gate', 'CamPole_Gate', CAMG_T)
    flood_on_pole('Flood_Gate', 'CamPole_Gate', Vector((-3.5, -1.0, 0.0)), 'floodlight under the camera: lights the opening and '
                                                                          'the road outside while there is power')
    cg = at_sock('CamPole_Gate', 'Conduit_Base')
    yc = GATE2['camcond_y']
    conduit_run('Cond_CamGate', 'Gate', [cg, Vector((cg.x, yc, cg.z)), Vector((dx1 + 0.04, yc, cg.z))],
                [Vector((0, 0, 1)), Vector((0, 0, 1))], entry0=True, entry1=True,
                note='the gate camera\'s cable out of its pole\'s footing along the ground into the drive\'s base')
    part('Gate', 'static', (0, 0, 0), parent=None, yaw=GATE_PLACE[1],
         note='sliding gate (separate root: the map\'s Gate prefab; beside the booth in this file, at the yard in the game, where '
              'the Update 7 walls run to its end posts)')


# ================================================================ the barrier and the gate move to their places
def inst_root(name):
    """the top part an instance hangs under (through parents that are instances or parts)"""
    while name in KIT_INST:
        name = KIT_INST[name]['parent']
    while CONTRACT['parts'][name].get('parent'):
        name = CONTRACT['parts'][name]['parent']
    return name


def place_roots():
    for root, (pos, yaw) in (('Barrier', BARRIER_PLACE), ('Gate', GATE_PLACE), ('Barrier_Manual', BARRIER_MANUAL_PLACE)):
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
        for s_ in CONTRACT['sockets'].values():
            if s_.get('parent') in tree:
                s_['pos'] = K.r4(M @ Vector(s_['pos']))
                for key in ('dir', 'facing'):
                    if s_.get(key) is not None:
                        s_[key] = K.r4(R3 @ Vector(s_[key]))
                if s_.get('eye') is not None:
                    s_['eye'] = K.r4(M @ Vector(s_['eye']))
        for n, ki in KIT_INST.items():
            if inst_root(n) == root:
                ki['M'] = M @ ki['M']


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
    # barrier, gate, the hand barrier: given in their own frames, moved to their places here (yaw 0)
    qx = REST_X
    cx0, cx1, cy0, cy1, cz0, cz1 = BAR2['cab']
    px0, px1, py0, py1 = BAR2['pad']
    rx0, rx1, ry0, ry1 = BAR2['rest_pad']
    bar = [('Barrier_Pad', 'Barrier', (px0, px1, py0, py1, -0.41, 0.15)),
           ('Barrier_Cabinet', 'Barrier', (cx0, cx1, cy0, cy1, cz0, cz1 + 0.035)),
           ('Barrier_RestFoot', 'Barrier', (rx0, rx1, ry0, ry1, -0.41, 0.12)),
           ('Barrier_Rest', 'Barrier', (qx - 0.12, qx + 0.12, -0.075, 0.075, 0.12, 0.98)),
           ('Boom', 'IX_BarrierArm_82', (-0.24, BOOM_LEN, -0.06, 0.06, BOOM_PIV.z - 0.08, BOOM_PIV.z + 0.08))]
    man = [('Manual_Foot', 'Barrier_Manual', (-0.375, 0.375, -0.375, 0.375, -0.41, 0.15)),
           ('Manual_Post', 'Barrier_Manual', (-0.12, 0.12, 0.08, 0.32, 0.15, 1.33)),
           ('Manual_Rest', 'Barrier_Manual', (qx - 0.12, qx + 0.12, -0.075, 0.075, 0.12, 0.98)),
           ('Manual_Boom', 'IX_BarrierArm_Manual_318', (-0.57, BOOM_LEN, -0.07, 0.07, BOOM_PIV.z - 0.095, BOOM_PIV.z + 0.095))]
    ly = GATE2['ly']
    zt = GATE2['z'][1]
    dx0, dx1, dy0, dy1, dz0, dz1 = GATE2['drive']
    gx, gxo = GATE2['guide_x'], GATE2['guide_x_out']
    gat = [('Gate_PostE', 'Gate', (GATE2['post_e'][0], GATE2['post_e'][1], -0.15, 0.15, -0.30, GATE2['post_h'] + 0.09)),
           ('Gate_PostW', 'Gate', (GATE2['post_w'][0], GATE2['post_w'][1], -0.15, 0.15, -0.30, GATE2['post_h'] + 0.09)),
           ('Gate_Receiver', 'Gate', (-7.40, -6.95, ly - 0.23, ly + 0.23, -0.60, zt + 0.05)),
           ('Gate_Guide_Out', 'Gate', (gxo - 0.04, gxo + 0.04, ly - 0.17, ly - 0.09, 0.0, zt + 0.15)),
           ('Gate_Guide_In', 'Gate', (gx - 0.04, gx + 0.04, ly + 0.09, ly + 0.17, 0.0, zt + 0.15)),
           ('Gate_Stop', 'Gate', (6.62, 6.76, ly - 0.04, ly + 0.04, 0.0, 0.60)),
           ('Gate_Drive', 'Gate', (dx0, dx1, dy0, dy1, -0.10, dz1 + 0.03)),
           ('Gate_Leaf', 'IX_Gate_81', (GATE_LEAF[0], GATE_LEAF[1], ly - 0.045, ly + 0.07, 0.05, zt + 0.42))]
    for lst, (pos, yaw) in ((bar, BARRIER_PLACE), (gat, GATE_PLACE), (man, BARRIER_MANUAL_PLACE)):
        assert yaw == 0.0
        for name, par, (a0, a1, b0, b1, c0, c1) in lst:
            B.append((name, par, (a0 + pos.x, a1 + pos.x, b0 + pos.y, b1 + pos.y, c0 + pos.z, c1 + pos.z), None))
    return [(n, p, b, r, False) for n, p, b, r in B]


def knock_rays():
    R = []
    for i, x in enumerate((-1.97, 1.97)):
        R.append((f'Knock_Front_{i + 1}', (x, -3.0, 0.70), (0, 1, 0)))
    for i, x in enumerate((-1.75, -0.3, 1.8)):                   # v2: -1.2 -> -1.75 (the cabinet and its conduit are at -1.2)
        R.append((f'Knock_Back_{i + 1}', (x, 3.0, 1.40 if x < 0 else 1.0), (0, -1, 0)))
    for i, y in enumerate((-0.75, 0.0, 1.0)):                    # v2: -1.3 -> -0.75 (the junction box is at -1.3)
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
    outside_kit()
    barrier()
    barrier_manual()
    gate()
    place_roots()
