"""Generator container kit: the generator shed's interior (gen_set, gen_room) moved into two 20 ft ISO containers that
stand side by side on concrete pads with the shared long walls cut out (one room 5.80 x 4.69 m, 2.34 m clear).
This module builds the container around that interior and holds the table that moves the shed's groups in:
  shell: corner castings, corner posts, side / end rails, door headers and sills, corrugated side and front walls,
  roofs with the joint flashing, the underside, concrete pads, the steel step at the doors;
  the south box's cargo doors (Door_R active, Door_L passive; four locking bars with handles turning cams in keepers,
  hinges; the padlock through the catch of Door_R_Bar_2, a barrel bolt inside); the north box's doors welded shut
  with two intake louvres; the window in the south wall (security grille outside); the radiator outlet louvre in the south box's front end (six blades on one lever); the exhaust through the
  front end and the stack with its rain flap; the service mast with the LINE and feeder drops;
  inside: the generator shed's own finishes - birch-ply lining on every wall (and over the rear frame round the
  doorway), the concrete floor with the shed's chequer covers over the cable trench and the copper fuel lines on
  clips, spruce joists across both boxes on the shed's rafter spacing with blocking along the long walls and the
  corrugated roof's underside between them, plank-lined door leaves, the shed's window (white frame, glazing bars,
  timber sill and reveals, board shutter), conduits, light switch, outlet, the extinguisher bracket, three caged
  bulkheads, the barn light over the doors; bilingual signs (German / English); snow on the roofs and the drift at
  the doors; audio / VFX / hide points, collider boxes, knock rays.
Frame: x east (the radiator louvre end), y north, z up, metres; ground z = 0 under the pads, floor z = 0.31;
origin = the middle of the twin footprint.  Unity: (x, y, z) -> (-y, z, x)."""
import math
import numpy as np
from mathutils import Vector, Matrix
import van3_mech as VM
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, prism_y, quad, conduit, transform_kb, rot_about, KBS, CONTRACT, LAMPS
from gen_kit import (Z_SLAB, Z_TIMBER, Z_DOORIN, Z_STEELBLK, Z_GALV, Z_RUSTPIPE, Z_CHEQUER, Z_INSUL, Z_WIRE, Z_ENAMEL,
                     Z_ENAMEL_IN, Z_SNOW, Z_BRASSP, Z_STEELP, Z_LINING, Z_FLOOR, Z_ROOFUNDER, Z_TRIMW)
import cont_tex as CT
from van2_kit import ZERO

uv = CT.uv
TAU = 2 * math.pi
XO, YO = 3.029, 2.438                  # outer end faces (castings) / outer long faces (castings)
ZB, ZT = 0.15, 2.741                   # bottom / top of the boxes (on 0.15 m pads)
FC, CI = 0.31, 2.675                   # floor top / the roof's underside (the top of the room, open as in the shed)
XI, YI = 2.90, 2.345                   # inner lining faces
XR, XRI = -2.97, -2.82                 # door end: frame outer face (= the leaves' inner face) / frame inner face
XF = XO - 0.15                         # front corner posts, inner face
XF_BOX = 2.84                          # room face of the ply boxing over the front posts and top castings (6 cm proud)
CAST = (0.178, 0.162, 0.118)
RPW, FPW = 0.14, 0.15                  # rear / front corner post width (y)
REC = 0.004                            # rails, sills and headers sit 4 mm inside the castings' planes
HDR_Z0 = 2.58                          # door header underside
ROOF_Z = 2.731
BOXES_Y = {'S': (-YO, 0.0), 'N': (0.0, YO)}
CR = dict(pitch=0.278, crest=0.072, slope=0.068, depth=0.036)            # side / front wall corrugation
LEAF = dict(z0=0.275, z1=2.615, fw=0.06, pitch=0.444, crest=0.20, slope=0.03)
XL_O, XL_C, XL_V = -2.998, -2.994, -2.976                               # leaf frame face / rib crest / rib valley
BAR_X, BAR_R, HANDLE_Z, HANDLE_L = -3.013, 0.0135, 1.30, 0.31
WIN = dict(x0=-0.40, x1=0.20, z0=1.51, z1=2.01)
LOUV = dict(y0=-1.515, y1=-0.515, z0=0.71, z1=1.61)
INTAKES = [dict(y0=0.39, y1=0.82, z0=2.00, z1=2.45), dict(y0=1.62, y1=2.05, z0=2.00, z1=2.45)]
EXH_Y, EXH_Z = -0.895, 2.16
STACK_X, STACK_TOP = 3.38, 3.60
MAST_X = -1.20
SW_Y = 0.30                            # light switch and outlet: west wall of the north box
XB = XR + 0.02                         # room face of the planks lining the door leaves
PLY = 0.012                            # ply over the rear frame's room faces round the doorway
JOIST_X = [-2.34, -1.56, -0.78, 0.0, 0.78, 1.56, 2.34]                 # the shed's rafter spacing
JOIST_W, JOIST_D = 0.05, 0.12          # spruce joists across both boxes, right under the roof
ZJ = CI - JOIST_D                      # their underside (2.555: 2.245 m clear)
CZ = ZJ - 0.014                        # conduit runs under the joists / the blocking (clamps clear)
LEAVES = {   # moving leaves of the south box: (y hinge edge, y free edge, pivot (x, y), axis z sign, (bar 1 y, bar 2 y))
    'Door_R': (-2.430, -1.222, (-3.015, -2.455), 1, (-2.10, -1.57)),
    'Door_L': (-0.008, -1.216, (-3.015, -0.004), -1, (-0.338, -0.868)),
}
STATIC_LEAVES = [(0.008, 1.216, (0.338, 0.868), [INTAKES[0]]), (2.430, 1.222, (2.10, 1.57), [INTAKES[1]])]
HINGE_Z = (0.55, 1.10, 1.80, 2.35)
PADS = [(-2.94, -2.357, 0.42, 0.40), (-2.94, 0.0, 0.42, 0.56), (-2.94, 2.357, 0.42, 0.40),
        (2.94, -2.357, 0.42, 0.40), (2.94, 0.0, 0.42, 0.56), (2.94, 2.357, 0.42, 0.40)]
STEP = (-3.42, -3.08, -2.05, -0.39, 0.16)
LAMP_C = {'Bulk_Genset': Vector((JOIST_X[2], -1.00, ZJ)), 'Bulk_Ceiling': Vector((JOIST_X[4], 1.10, ZJ))}   # under joists

# ---------------------------------------------------------------- zones (one building atlas, as the shed's)
Z_SEAL = 79
(Z_CPAINT_S, Z_CPAINT_N, Z_CROOF, Z_CCAST, Z_CINPAINT, Z_UNDER) = range(80, 86)
INSIDE_ZONES = (Z_LINING, Z_FLOOR, Z_ROOFUNDER, Z_TRIMW, Z_DOORIN, Z_TIMBER)        # always the shed's inside painter
SHARED_ZONES = (Z_STEELBLK, Z_GALV, Z_CHEQUER, Z_INSUL, Z_WIRE, Z_RUSTPIPE)          # inside painter inside the room

# ---------------------------------------------------------------- moving the shed's interior in (translations)
G_GEN = Vector((0.62, -0.765, 0.21))     # genset (+ the petrol drum): radiator end at the louvre, duct to the front wall
G_S = Vector((0.0, -0.765, 0.21))        # switchboard, mat, logbook: on the south wall
G_N = Vector((0.62, 0.765, 0.21))        # day tank, diesel drums on the pallet, drum pump: on the north wall
G_W = Vector((-0.62, 0.0, 0.21))         # shelf and its goods: on the west wall of the north box
G_EXT = Vector((-0.62, 1.85, 0.21))      # extinguisher: west wall of the north box, by the doorway
TOP_GROUP = {'Genset': G_GEN, 'Drum_3': G_GEN, 'Switchboard': G_S, 'Mat': G_S, 'Logbook': G_S, 'DayTank': G_N,
             'Pallet': G_N, 'Extinguisher': G_EXT}
for _n in ('Shelf', 'EngineOil', 'Coolant', 'FuelFilter_Spare', 'Funnel', 'Toolbox', 'JumperCables', 'BungWrench'):
    TOP_GROUP[_n] = G_W
SOCKET_GROUP = {'Slot_Extinguisher': G_EXT, 'Nail_Logbook': G_S}
NAIL_GROUP = G_S                         # the logbook nail that gen_room puts into the shed mesh
# fuel lines in the container frame (copper on floor clips, as in the shed): feed from the valve down the north wall,
# across the floor, under the skid to the water separator; return from the leak-off back the same way to the tank top
FEED_C = [(0.18, 2.125, 1.42), (0.18, 2.125, 1.31), (0.18, 2.305, 1.23), (0.18, 2.305, 0.325), (0.18, -0.30, 0.325),
          (1.87, -0.30, 0.325), (1.87, -1.515, 0.325)]
RET_C = [(1.94, -1.535, 0.325), (1.94, -0.27, 0.325), (0.15, -0.27, 0.325), (0.15, 2.32, 0.325), (0.15, 2.32, 2.01),
         (-0.08, 2.245, 2.01), (-0.08, 2.245, 1.93)]


def fuel_routes_shed():
    """FEED_C / RET_C in the day tank's own (shed) frame: the lines are part of the DayTank mesh, which moves by G_N"""
    f = lambda pts: [tuple(Vector(p) - G_N) for p in pts]
    return f(FEED_C), f(RET_C)


def group_of(C, name):
    """translation of a shed part / socket into the container: by the top-level item it hangs from"""
    if name in SOCKET_GROUP:
        return SOCKET_GROUP[name]
    p = C['parts'].get(name) or C['sockets'].get(name)
    seen = 0
    n = name
    while p is not None and p.get('parent') not in (None, 'Shed', 'GenContainer') and seen < 20:
        n = p['parent']
        p = C['parts'].get(n)
        seen += 1
    if n not in TOP_GROUP:
        raise KeyError(f'{name}: no group for top-level item {n}')
    return TOP_GROUP[n]


# ---------------------------------------------------------------- geometry helpers
def corr_profile(s0, s1, pitch, crest, slope, phase=0.0, cuts=()):
    """breakpoints [(s, d)] of a trapezoidal corrugation clipped to s0..s1 (d = 0 crest, 1 valley)"""
    valley = pitch - crest - 2 * slope
    seq = [(0.0, 0.0), (crest, 0.0), (crest + slope, 1.0), (crest + slope + valley, 1.0)]
    pts = []
    k = math.floor((s0 - phase) / pitch) - 1
    while phase + k * pitch <= s1 + pitch:
        pts += [(phase + k * pitch + a, d) for a, d in seq]
        k += 1

    def d_at(s):
        for (sa, da), (sb, db) in zip(pts[:-1], pts[1:]):
            if sa - 1e-9 <= s <= sb + 1e-9:
                return da if sb - sa < 1e-9 else da + (db - da) * (s - sa) / (sb - sa)
        raise ValueError(s)

    ss = sorted(set([s0, s1] + [s for s, d in pts if s0 < s < s1] + [c for c in cuts if s0 < c < s1]))
    out = []
    for s in ss:
        if out and s - out[-1][0] < 1e-6:
            continue
        out.append((s, d_at(s)))
    return out


def _subtract(span, cuts):
    res = [span]
    for c0, c1 in cuts:
        nxt = []
        for a, b in res:
            if c1 <= a or c0 >= b:
                nxt.append((a, b))
                continue
            if c0 > a:
                nxt.append((a, c0))
            if c1 < b:
                nxt.append((c1, b))
        res = nxt
    return [(a, b) for a, b in res if b - a > 1e-6]


def _split(a, b, step=1.0):
    n = max(1, int(math.ceil((b - a) / step - 1e-6)))
    return [(a + (b - a) * i / n, a + (b - a) * (i + 1) / n) for i in range(n)]


def _grid(vals, step):
    vals = sorted(vals)
    out = []
    for a, b in zip(vals[:-1], vals[1:]):
        out += [p for p, q in _split(a, b, step)]
    return out + [vals[-1]]


def corrugated(k, axis, a_out, out_sign, depth, u0, u1, z0, z1, pitch, crest, slope, zone, along='u', phase=0.0,
               holes=(), step=1.0):
    """corrugated sheet, outer face only: axis 'y' = side wall (normal along y, u = x), 'x' = front wall / door leaf
    (u = y); crests at a_out, valleys `depth` further in; the profile runs along u (vertical ribs) or z (horizontal
    ribs); holes = [(u0, u1, z0, z1)]"""
    if along == 'u':
        s0, s1, t0, t1 = u0, u1, z0, z1
        hs = [(h[0], h[1], h[2], h[3]) for h in holes]
    else:
        s0, s1, t0, t1 = z0, z1, u0, u1
        hs = [(h[2], h[3], h[0], h[1]) for h in holes]
    prof = corr_profile(s0, s1, pitch, crest, slope, phase, [c for h in hs for c in (h[0], h[1])])
    nrm = Vector((out_sign, 0, 0)) if axis == 'x' else Vector((0, out_sign, 0))

    def P(s, d, t):
        u, z = (s, t) if along == 'u' else (t, s)
        a = a_out - out_sign * d * depth
        return Vector((a, u, z)) if axis == 'x' else Vector((u, a, z))

    for (sa, da), (sb, db) in zip(prof[:-1], prof[1:]):
        sm = (sa + sb) / 2
        for ta, tb in _subtract((t0, t1), [(h[2], h[3]) for h in hs if h[0] < sm < h[1]]):
            for tc, td in _split(ta, tb, step):
                face(k, [P(sa, da, tc), P(sb, db, tc), P(sb, db, td), P(sa, da, td)], zone, nrm)


def flat_wall(k, axis, a, n_sign, u0, u1, z0, z1, zone_fn, holes=(), step=1.0, zcuts=()):
    """single-sided flat wall at axis = a facing n_sign ('x': u = y, 'y': u = x), cells around the holes
    [(u0, u1, z0, z1)]; zone_fn(z_mid) -> zone"""
    us = {u0, u1} | {c for h in holes for c in (h[0], h[1]) if u0 < c < u1}
    zs = {z0, z1} | {c for h in holes for c in (h[2], h[3]) if z0 < c < z1} | {c for c in zcuts if z0 < c < z1}
    us, zs = _grid(us, step), _grid(zs, step)
    nrm = Vector((n_sign, 0, 0)) if axis == 'x' else Vector((0, n_sign, 0))
    P = (lambda u, z: Vector((a, u, z))) if axis == 'x' else (lambda u, z: Vector((u, a, z)))
    for i in range(len(us) - 1):
        for j in range(len(zs) - 1):
            um, zm = (us[i] + us[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
            if any(h[0] < um < h[1] and h[2] < zm < h[3] for h in holes):
                continue
            face(k, [P(us[i], zs[j]), P(us[i + 1], zs[j]), P(us[i + 1], zs[j + 1]), P(us[i], zs[j + 1])], zone_fn(zm), nrm)


def flat_h(k, z, n_sign, x0, x1, y0, y1, zone, step=1.0, xcuts=(), ycuts=()):
    xs = _grid({x0, x1} | {c for c in xcuts if x0 < c < x1}, step)
    ys = _grid({y0, y1} | {c for c in ycuts if y0 < c < y1}, step)
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            face(k, [Vector((xs[i], ys[j], z)), Vector((xs[i + 1], ys[j], z)), Vector((xs[i + 1], ys[j + 1], z)),
                     Vector((xs[i], ys[j + 1], z))], zone, (0, 0, n_sign))


def sleeve(k, axis, a0, a1, u0, u1, z0, z1, zone, bottom=True):
    """the reveal faces of an opening (u0..u1, z0..z1) through a wall between a0 and a1 along the axis"""
    P = (lambda a, u, z: Vector((a, u, z))) if axis == 'x' else (lambda a, u, z: Vector((u, a, z)))
    ua = Vector((0, 1, 0)) if axis == 'x' else Vector((1, 0, 0))
    face(k, [P(a0, u0, z0), P(a1, u0, z0), P(a1, u0, z1), P(a0, u0, z1)], zone, ua)
    face(k, [P(a0, u1, z0), P(a1, u1, z0), P(a1, u1, z1), P(a0, u1, z1)], zone, -ua)
    if bottom:
        face(k, [P(a0, u0, z0), P(a1, u0, z0), P(a1, u1, z0), P(a0, u1, z0)], zone, (0, 0, 1))
    face(k, [P(a0, u0, z1), P(a1, u0, z1), P(a1, u1, z1), P(a0, u1, z1)], zone, (0, 0, -1))


def flange(k, axis, a_face, out_sign, u0, u1, z0, z1, w, t, zone, sides='tblr'):
    """a flat frame of width w and thickness t around an opening, standing on a wall face (normal out_sign)"""
    a0, a1 = sorted((a_face, a_face + out_sign * t))
    back = (('-x' if out_sign > 0 else '+x') if axis == 'x' else ('-y' if out_sign > 0 else '+y'),)

    def B(ua, ub, za, zb):
        lo = (a0, ua, za) if axis == 'x' else (ua, a0, za)
        hi = (a1, ub, zb) if axis == 'x' else (ub, a1, zb)
        box6(k, lo, hi, zone, skip=back)
    if 't' in sides:
        B(u0 - w, u1 + w, z1, z1 + w)
    if 'b' in sides:
        B(u0 - w, u1 + w, z0 - w, z0)
    if 'l' in sides:
        B(u0 - w, u0, z0, z1)
    if 'r' in sides:
        B(u1, u1 + w, z0, z1)


# ================================================================ the boxes
def structure():
    k = kb('GenContainer', 'Cont')
    for nm, (ya, yb) in BOXES_Y.items():
        zp = Z_CPAINT_S if nm == 'S' else Z_CPAINT_N
        so = -1 if nm == 'S' else 1
        yo = ya if nm == 'S' else yb                       # the outer long face
        yj = yb if nm == 'S' else ya                       # the joint
        js = '+y' if nm == 'S' else '-y'                   # faces lying on the joint plane stay out
        for x0, x1 in ((-XO, -XO + CAST[0]), (XO - CAST[0], XO)):                  # corner castings
            for y0, y1 in ((ya, ya + CAST[1]), (yb - CAST[1], yb)):
                for z0, z1 in ((ZB, ZB + CAST[2]), (ZT - CAST[2], ZT)):
                    box6(k, (x0, y0, z0), (x1, y1, z1), Z_CCAST, skip=(js,) if yj in (y0, y1) else ())
        r0, r1 = sorted((yo - so * REC, yo - so * 0.09))                           # side rails (outer long side)
        box6(k, (XR, r0, ZB + 0.01), (XF, r1, FC), zp, skip=('-x', '+x'))
        box6(k, (XR, r0, ZT - 0.10), (XF, r1, ZT - REC), zp, skip=('-x', '+x'))
        for p0, p1 in ((ya, ya + FPW), (yb - FPW, yb)):                           # front corner posts
            box6(k, (XF, p0, ZB + CAST[2]), (XO, p1, ZT - CAST[2]), zp,
                 skip=('-z', '+z') + ((js,) if yj in (p0, p1) else ()))
        box6(k, (XO - 0.10, ya + FPW, ZB + 0.01), (XO - REC, yb - FPW, FC), zp, skip=('-y', '+y'))     # front sill
        box6(k, (XO - 0.10, ya + FPW, ZT - 0.10), (XO - REC, yb - FPW, ZT - REC), zp, skip=('-y', '+y'))
        for p0, p1 in ((ya, ya + RPW), (yb - RPW, yb)):                           # rear corner posts (room faces: ply)
            box6(k, (XR, p0, ZB + CAST[2]), (XRI, p1, ZT - CAST[2]), zp,
                 skip=('-z', '+z', '+x') + ((js,) if yj in (p0, p1) else ()))
        box6(k, (XR, ya + RPW, ZB + 0.01), (XRI, yb - RPW, FC), zp,                                 # door sill (the north
             skip=('-y', '+y') + (('+z',) if nm == 'N' else ()))                                     # box's: under the floor)
        box6(k, (XR, ya + RPW, HDR_Z0), (XRI, yb - RPW, ZT - REC), zp,                              # door header (room
             skip=('-y', '+y', '+x') + (('-z',) if nm == 'N' else ()))                               # face: ply / timber)
        # corrugated side wall (the window in the south one) and front wall (the radiator louvre in the south one)
        holes = [(WIN['x0'], WIN['x1'], WIN['z0'], WIN['z1'])] if nm == 'S' else []
        corrugated(k, 'y', yo - so * 0.008, so, CR['depth'], XRI, XF, FC, ZT - 0.10, CR['pitch'], CR['crest'],
                   CR['slope'], zp, phase=XRI + 0.03, holes=holes)
        holes = [(LOUV['y0'], LOUV['y1'], LOUV['z0'], LOUV['z1'])] if nm == 'S' else []
        corrugated(k, 'x', XO - 0.008, 1, CR['depth'], ya + FPW, yb - FPW, FC, ZT - 0.10, CR['pitch'], CR['crest'],
                   CR['slope'], zp, phase=ya + FPW + 0.04, holes=holes)
        # roof panel between the rails and headers (the corrugation is painted)
        y0r, y1r = sorted((yo - so * 0.09, yj))
        flat_h(k, ROOF_Z, 1, XRI, XO - 0.10, y0r, y1r, Z_CROOF, step=1.0)       # (edges: the headers' and rails' faces)
    # joint flashing over the two inner top rails, the underside
    box6(k, (XR, -0.09, ROOF_Z), (XO - 0.10, 0.09, 2.745), Z_GALV, skip=('-z',))
    flat_h(k, ZB + 0.03, -1, XR, XF, -YO + REC, YO - REC, Z_UNDER, step=1.5)
    # pads under the castings, the step at the doors
    for x, y, sx, sy in PADS:
        box6(k, (x - sx / 2, y - sy / 2, 0.0), (x + sx / 2, y + sy / 2, ZB - 0.001), Z_SLAB, skip=('-z',))
    x0, x1, y0, y1, h = STEP
    box6(k, (x0, y0, 0.0), (x1, y1, h - 0.006), Z_STEELBLK, skip=('-z',))
    box6(k, (x0 - 0.005, y0 - 0.005, h - 0.006), (x1 + 0.005, y1 + 0.005, h), Z_CHEQUER, skip=('-z',))
    return k


def interior_shell():
    """the generator shed's inside fitted into the twin box: birch-ply lining on every wall and over the rear frame's
    room faces round the doorway, the shed's concrete floor, spruce joists across both boxes on the shed's rafter
    spacing right under the corrugated roof's underside, blocking between them along the long walls (the joint between
    the boxes stays hidden above)"""
    ki = kb('GenContainer_In', 'Cont')
    lz = lambda zm: Z_LINING
    # floor: concrete over both boxes (the doorway threshold is the rear frame's sill); in the north box it runs on to
    # the lining over the welded doors' sill
    flat_h(ki, FC, 1, XRI, XI, -YI, YI, Z_FLOOR, step=1.0)
    flat_h(ki, FC, 1, -XI, XRI, RPW, YI, Z_FLOOR, step=1.0)
    # walls: south (window), north, front (louvre; the boxed joint posts), west of the north box (two intakes)
    flat_wall(ki, 'y', -YI, 1, XRI + PLY, XI, FC, CI, lz, holes=[(WIN['x0'], WIN['x1'], WIN['z0'], WIN['z1'])])
    flat_wall(ki, 'y', YI, -1, XRI + PLY, XI, FC, CI, lz)
    yc = CAST[1] + 0.01                                                   # past the castings (0.162; the posts' 0.15)
    flat_wall(ki, 'x', XI, -1, -YI, -yc, FC, CI, lz, holes=[(LOUV['y0'], LOUV['y1'], LOUV['z0'], LOUV['z1'])])
    flat_wall(ki, 'x', XI, -1, yc, YI, FC, CI, lz)
    # ply boxing over the front corner posts and top castings, which stand 2-5 cm proud of the front lining: at the
    # joint and in both outer corners
    box6(ki, (XF_BOX, -yc, FC), (XI, yc, CI), Z_LINING, skip=('+x', '-z', '+z'))
    box6(ki, (XF_BOX, YO - yc, FC), (XI, YI, CI), Z_LINING, skip=('+x', '+y', '-z', '+z'))
    box6(ki, (XF_BOX, -YI, FC), (XI, -YO + yc, CI), Z_LINING, skip=('+x', '-y', '-z', '+z'))
    flat_wall(ki, 'x', -XI, 1, RPW + PLY, YO - RPW - PLY, FC, HDR_Z0, lz,
              holes=[(h['y0'], h['y1'], h['z0'], h['z1']) for h in INTAKES])
    # ply over the rear frame's room faces (the corner post by the south wall, the joint posts, the header over the
    # doorway); in the north box over the posts' corners, a timber ledger over its header
    yp = -YO + RPW
    box6(ki, (XRI, -YI, FC), (XRI + PLY, yp, CI), Z_LINING, skip=('-x', '-y', '-z', '+z'))
    box6(ki, (XRI, -RPW, FC), (XRI + PLY, RPW, CI), Z_LINING, skip=('-x', '+y', '-z', '+z'))
    box6(ki, (XRI, yp, HDR_Z0), (XRI + PLY, -RPW, CI), Z_LINING, skip=('-x', '-y', '+y', '+z'))
    box6(ki, (-XI, RPW, FC), (XRI + PLY, RPW + PLY, CI), Z_LINING, skip=('-x', '-y', '-z', '+z'))
    box6(ki, (-XI, YO - RPW - PLY, FC), (XRI + PLY, YI, CI), Z_LINING, skip=('-x', '+y', '-z', '+z'))
    box6(ki, (-XI, RPW + PLY, HDR_Z0), (XRI + PLY, YO - RPW - PLY, CI), Z_TIMBER, skip=('-x', '-y', '+y', '+z'))
    # the roof's underside over the room, the joists right under it, blocking between them along the long walls
    flat_h(ki, CI, -1, XRI + PLY, XI, -YI, YI, Z_ROOFUNDER, step=1.0)
    for xj in JOIST_X:
        box6(ki, (xj - JOIST_W / 2, -YI, ZJ), (xj + JOIST_W / 2, YI, CI), Z_TIMBER, skip=('-y', '+y', '+z'))
    for s in (-1, 1):
        ya, yb = (YI - 0.05, YI) if s > 0 else (-YI, -YI + 0.05)
        for xa, xb in zip(JOIST_X[:-1], JOIST_X[1:]):
            box6(ki, (xa + JOIST_W / 2, ya, ZJ), (xb - JOIST_W / 2, yb, CI), Z_TIMBER,
                 skip=('-x', '+x', '+z', '+y' if s > 0 else '-y'))
    return ki


# ================================================================ doors
def leaf_mesh(k, ya, yb, zone, holes=(), inner=True, boards=None):
    """a door leaf (closed) between ya and yb: room side flat (painted; left out where the lining hides it) with the
    shed's plank lining over the doorway part (boards = (y0, y1, z0, z1)), outside a frame and a panel with five
    horizontal ribs"""
    z0, z1, fw = LEAF['z0'], LEAF['z1'], LEAF['fw']
    if inner:
        flat_wall(k, 'x', XR, 1, ya, yb, z0, z1, lambda z: Z_CINPAINT, holes=list(holes) + ([boards] if boards else []))
        if boards:
            box6(k, (XR, boards[0], boards[2]), (XB, boards[1], boards[3]), Z_DOORIN, skip=('-x',))
    face(k, [(XL_O, ya, z0), (XR, ya, z0), (XR, ya, z1), (XL_O, ya, z1)], zone, (0, -1, 0))
    face(k, [(XL_O, yb, z0), (XR, yb, z0), (XR, yb, z1), (XL_O, yb, z1)], zone, (0, 1, 0))
    face(k, [(XL_O, ya, z0), (XR, ya, z0), (XR, yb, z0), (XL_O, yb, z0)], zone, (0, 0, -1))
    face(k, [(XL_O, ya, z1), (XR, ya, z1), (XR, yb, z1), (XL_O, yb, z1)], zone, (0, 0, 1))
    pa, pb, qa, qb = ya + fw, yb - fw, z0 + fw, z1 - fw
    for u0, u1, w0, w1 in ((ya, yb, z0, qa), (ya, yb, qb, z1), (ya, pa, qa, qb), (pb, yb, qa, qb)):
        face(k, [(XL_O, u0, w0), (XL_O, u1, w0), (XL_O, u1, w1), (XL_O, u0, w1)], zone, (-1, 0, 0))
    face(k, [(XL_O, pa, qa), (XL_V, pa, qa), (XL_V, pb, qa), (XL_O, pb, qa)], zone, (0, 0, 1))
    face(k, [(XL_O, pa, qb), (XL_V, pa, qb), (XL_V, pb, qb), (XL_O, pb, qb)], zone, (0, 0, -1))
    face(k, [(XL_O, pa, qa), (XL_V, pa, qa), (XL_V, pa, qb), (XL_O, pa, qb)], zone, (0, 1, 0))
    face(k, [(XL_O, pb, qa), (XL_V, pb, qa), (XL_V, pb, qb), (XL_O, pb, qb)], zone, (0, -1, 0))
    corrugated(k, 'x', XL_C, -1, XL_V - XL_C, pa, pb, qa, qb, LEAF['pitch'], LEAF['crest'], LEAF['slope'], zone,
               along='z', phase=qa, holes=holes)
    for h in holes:                                                     # through the leaf to its room side
        sleeve(k, 'x', XL_O, XR, h[0], h[1], h[2], h[3], Z_GALV)


def leaf_hardware(k, y_hinge, s, piv, bars, zone, hinge_z=HINGE_Z, hd=-1):
    """hinge straps and knuckles, bar guides and the handle catches on a leaf (s = +1: the leaf runs to +y; hd: the
    handles point -y or +y)"""
    for zc in hinge_z:
        ya, yb = sorted((y_hinge, y_hinge + s * 0.17))
        box6(k, (XL_O - 0.008, ya, zc - 0.03), (XL_O, yb, zc + 0.03), zone, skip=('+x',))
        ya, yb = sorted((y_hinge, piv[1]))
        box6(k, (piv[0], ya - 0.006, zc - 0.03), (XL_O - 0.008, yb + 0.006, zc + 0.03), zone)
        k.cyl((piv[0], piv[1], zc - 0.035), (piv[0], piv[1], zc + 0.035), 0.013, zone, 8)
    for yb_ in bars:
        for zc in (0.55, 2.35):                                         # guides the bar turns in
            box6(k, (BAR_X - 0.02, yb_ - 0.022, zc - 0.025), (XL_O, yb_ + 0.022, zc + 0.025), Z_GALV, skip=('+x',))
        ye = yb_ + hd * HANDLE_L                                         # catch at the handle's end
        box6(k, (-3.046, ye - 0.024, HANDLE_Z - 0.045), (XL_O, ye + 0.024, HANDLE_Z - 0.032), Z_GALV, skip=('+x',))
        box6(k, (-3.046, ye - 0.024, HANDLE_Z + 0.032), (XL_O, ye + 0.024, HANDLE_Z + 0.045), Z_GALV, skip=('+x',))
        box6(k, (-3.050, ye - 0.024, HANDLE_Z - 0.045), (-3.046, ye + 0.024, HANDLE_Z + 0.045), Z_GALV)


def bar_mesh(k, y, hd=-1):
    """locking bar: rod with cams at both ends and the handle at HANDLE_Z (pointing hd * y when locked)"""
    k.cyl((BAR_X, y, 0.212), (BAR_X, y, 2.678), BAR_R, Z_GALV, 8)
    for zc in (0.228, 2.662):
        k.box_m((BAR_X, y + 0.016, zc), (0.022, 0.032, 0.026), Z_GALV)
    k.box_m((BAR_X - 0.012, y, HANDLE_Z), (0.034, 0.036, 0.05), Z_GALV)
    k.box_m((BAR_X - 0.026, y + hd * (HANDLE_L / 2 + 0.01), HANDLE_Z), (0.012, HANDLE_L - 0.02, 0.034), Z_GALV)
    yg = y + hd * (HANDLE_L - 0.01)
    k.cyl((BAR_X - 0.036, yg, HANDLE_Z - 0.028), (BAR_X - 0.036, yg, HANDLE_Z + 0.028), 0.010, Z_STEELBLK, 6)


def keepers(k, y):
    for z0, z1 in ((0.205, 0.252), (2.638, 2.685)):
        box6(k, (-3.034, y - 0.03, z0), (XR, y + 0.048, z1), Z_GALV, skip=('+x',))


def doors():
    k = KBS['GenContainer']
    planks = {'Door_R': (-YO + RPW + 0.008, LEAVES['Door_R'][1] - 0.006), 'Door_L': (LEAVES['Door_L'][1] + 0.006, -RPW - 0.008)}
    for name, (yh, yf, piv, sg, bars) in LEAVES.items():
        D = kb(name, 'Cont')
        ya, yb = sorted((yh, yf))
        leaf_mesh(D, ya, yb, Z_CPAINT_S, boards=planks[name] + (FC + 0.01, HDR_Z0 - 0.01))   # planks fill the doorway
        s = 1 if yf > yh else -1
        leaf_hardware(D, yh, s, piv, bars, Z_CPAINT_S)
        for zc in HINGE_Z:                     # lugs and pins on the corner posts, in the sector the leaf never sweeps
            if name == 'Door_R':               # along +x from the pin, then onto the post's side
                box6(k, (piv[0], piv[1] - 0.006, zc + 0.037), (XR - 0.005, piv[1] + 0.006, zc + 0.062), Z_CPAINT_S)
                box6(k, (-2.995, piv[1] + 0.006, zc + 0.037), (XR, -YO + 0.001, zc + 0.062), Z_CPAINT_S, skip=('+x', '+y'))
            else:                              # beside the leaf's hinge edge, straight onto the joint posts
                box6(k, (piv[0], piv[1], zc + 0.037), (XR, piv[1] + 0.010, zc + 0.062), Z_CPAINT_S, skip=('+x',))
            k.cyl((piv[0], piv[1], zc - 0.04), (piv[0], piv[1], zc + 0.07), 0.006, Z_STEELBLK, 6)
        for i, yb_ in enumerate(bars):
            bn = f'{name}_Bar_{i + 1}'
            B = kb(bn, 'Cont')
            bar_mesh(B, yb_)
            keepers(k, yb_)
            part(bn, 'hinge', (BAR_X, yb_, HANDLE_Z), (0, 0, -1), (0, 90), parent=name, states=['locked', 'turned out'],
                 note='locking bar: lift the handle out of its catch and swing it out (+, up to 90): the cams at both ends '
                      'turn out of the keepers on the sill and the header; all of a leaf\'s bars out = the leaf is free')
            socket('Hand_' + bn, (BAR_X - 0.036, yb_ - HANDLE_L + 0.01, HANDLE_Z), 'hand', parent=bn)
        pz = (LEAF['z0'] + LEAF['z1']) / 2
        part(name, 'hinge', (piv[0], piv[1], pz), (0, 0, sg), (0, 240 if name == 'Door_R' else 160), parent='GenContainer',
             states=['shut', 'open'],
             note=('active leaf: Padlock off, both bars turned out (Door_R_Bar_1, _2), Door_Bolt drawn inside; swings out '
                   'and folds back against the south wall (240)' if name == 'Door_R' else
                   'passive leaf: opens after Door_R, both its bars turned out; stops against the welded doors of the north '
                   'box (160)'))
        # inside: a D pull on each leaf's planks
        yd = -1.42 if name == 'Door_R' else -1.02
        D.tube([Vector((XB, yd, 0.95)), Vector((XB + 0.045, yd, 0.95)), Vector((XB + 0.045, yd, 1.17)), Vector((XB, yd, 1.17))],
               0.010, Z_STEELBLK, 6, caps=False)
        socket('Hand_' + name + '_In', (XB + 0.05, yd, 1.06), 'hand', parent=name)
        socket('Hand_' + name + '_Out', (BAR_X - 0.04, bars[1] - HANDLE_L + 0.01, HANDLE_Z + 0.08), 'hand', parent=name,
               note='pull the leaf open by its inner bar handle once the bars are out')
    kR, kL = KBS['Door_R'], KBS['Door_L']
    # padlock through the catch of Door_R_Bar_2 (the inner bar of the active leaf)
    ye = LEAVES['Door_R'][4][1] - HANDLE_L
    Pd = kb('Padlock', 'Props')
    pc = Vector((-3.040, ye, HANDLE_Z - 0.085))
    VM.rbox(Pd, pc, (0.022, 0.05, 0.045), Z_BRASSP, r=0.006, ch=0.003)
    Pd.tube([pc + Vector((0, -0.016, 0.022)), pc + Vector((0, -0.016, 0.06)), pc + Vector((0, -0.008, 0.07)),
             pc + Vector((0, 0.008, 0.07)), pc + Vector((0, 0.016, 0.06)), pc + Vector((0, 0.016, 0.022))], 0.0042,
            Z_STEELP, 6, caps=False)
    part('Padlock', 'item', pc + Vector((0, 0, 0.065)), (0, 0, 1), parent='Door_R', states=['locked', 'open', 'off'],
         note='brass padlock through the catch of Door_R_Bar_2: while it is on, that handle cannot leave its catch; '
              'Door_Key opens it, then it lifts off')
    socket('Hand_Padlock', pc, 'hand', parent='Padlock')
    socket('Slot_Padlock', pc + Vector((0, 0, 0.05)), 'item_slot', parent='Door_R', note='the padlock shackle goes through here')
    # barrel bolt inside (on the planks): on Door_R by the meeting edge, shoots into a keeper on Door_L
    bb = Vector((XB + 0.012, -1.235, 1.30))
    for y0 in (-1.33, -1.27):
        kR.box(XB, XB + 0.022, y0, y0 + 0.02, 1.283, 1.317, Z_STEELBLK)
    kL.box(XB, XB + 0.022, -1.20, -1.17, 1.283, 1.317, Z_STEELBLK)
    B = kb('Door_Bolt', 'Cont')
    B.cyl(bb - Vector((0, 0.12, 0)), bb, 0.0065, Z_STEELBLK, 6)
    B.cyl(bb - Vector((0, 0.07, 0)), bb - Vector((-0.03, 0.07, 0)), 0.006, Z_STEELBLK, 6)
    part('Door_Bolt', 'slide', bb, (0, 1, 0), (0, 0.06), unit='m', parent='Door_R', states=['drawn', 'shot'],
         note='barrel bolt on the planks inside the active leaf: shoot it (+0.06) into the keeper on Door_L to lock the doors '
              'from inside (the locking bars are outside: shut from outside = locked in)')
    socket('Hand_Door_Bolt', bb + Vector((0.03, -0.07, 0)), 'hand', parent='Door_Bolt')
    # the key on a hook on the south side wall, round the corner from the doors
    hook = Vector((-2.70, -YO + 0.008, 1.95))
    k.box(hook.x - 0.015, hook.x + 0.015, hook.y - 0.004, hook.y, hook.z - 0.03, hook.z + 0.03, Z_STEELBLK)
    k.tube([hook + Vector((0, -0.004, 0)), hook + Vector((0, -0.03, 0)), hook + Vector((0, -0.038, 0.012))], 0.0028, Z_STEELBLK, 5)
    Ky = kb('Door_Key', 'Props')
    kc = hook + Vector((0, -0.024, -0.012))
    Ky.lathe(kc, (0, 1, 0), [(-0.002, 0.011), (0.002, 0.011)], Z_BRASSP, 8)
    Ky.box(kc.x - 0.003, kc.x + 0.003, kc.y - 0.0015, kc.y + 0.0015, kc.z - 0.055, kc.z - 0.011, Z_BRASSP)
    Ky.box(kc.x, kc.x + 0.008, kc.y - 0.0015, kc.y + 0.0015, kc.z - 0.05, kc.z - 0.04, Z_BRASSP)
    part('Door_Key', 'item', kc, (0, 1, 0), parent='GenContainer',
         note='padlock key on a hook on the south side wall by the door end, outside (find it with a torch)')
    socket('Hook_Key', hook + Vector((0, -0.03, 0.004)), 'item_slot', parent='GenContainer', note='the key hangs here')
    # the north box: doors welded shut (static), bars wired, two intake louvres cut in
    for yh, yf, bars, holes in STATIC_LEAVES:
        ya, yb = sorted((yh, yf))
        hs = [(h['y0'], h['y1'], h['z0'], h['z1']) for h in holes]
        leaf_mesh(k, ya, yb, Z_CPAINT_N, hs, inner=False)                # behind the lining
        s = 1 if yf > yh else -1
        piv = (-3.015, 2.455) if yh > 1 else (-3.015, 0.016)
        hz_ = tuple(z - 0.08 for z in HINGE_Z) if yh < 1 else HINGE_Z
        leaf_hardware(k, yh, s, piv, bars, Z_CPAINT_N, hinge_z=hz_, hd=1)
        for zc in hz_:
            ya_, yb_ = sorted((piv[1] - 0.014 * s, piv[1] + 0.03 * s))
            box6(k, (-3.03, ya_, zc - 0.062), (XR, yb_, zc - 0.037), Z_CPAINT_N, skip=('+x',))
            k.cyl((piv[0], piv[1], zc - 0.07), (piv[0], piv[1], zc + 0.04), 0.006, Z_STEELBLK, 6)
        for yb_ in bars:
            bar_mesh(k, yb_, hd=1)
            keepers(k, yb_)
        for h in holes:
            intake_louvre(k, h)


def intake_louvre(k, h):
    a, b, zl, zh = h['y0'], h['y1'], h['z0'], h['z1']
    ki = KBS['GenContainer_In']
    flange(k, 'x', XL_O, -1, a, b, zl, zh, 0.03, 0.010, Z_GALV)
    sleeve(k, 'x', XR, -XI, a, b, zl, zh, Z_GALV)
    for i in range(4):
        zc = zl + 0.06 + i * 0.11
        R = VM.frame_R(Vector((0, 1, 0)), Vector((math.sin(math.radians(45)), 0, math.cos(math.radians(45)))))
        k.box_m(Vector((-2.94, (a + b) / 2, zc)), (b - a, 0.12, 0.006), Z_GALV, R)
    face(ki, [Vector((-XI + 0.006, a, zl)), Vector((-XI + 0.006, b, zl)), Vector((-XI + 0.006, b, zh)), Vector((-XI + 0.006, a, zh))],
         Z_STEELBLK, (1, 0, 0))                                          # mesh behind the blades


# ================================================================ window
def window():
    """the shed's window in the south wall: timber reveals and sill inside, the white frame with glazing bars round the
    pane in the opening; the container's security grille outside; the board shutter and the turn-button inside"""
    k, ki = KBS['GenContainer'], KBS['GenContainer_In']
    x0, x1, z0, z1 = WIN['x0'], WIN['x1'], WIN['z0'], WIN['z1']
    sleeve(ki, 'y', -YO + 0.008, -YI, x0, x1, z0, z1, Z_TIMBER)
    flange(k, 'y', -YO + 0.008, -1, x0, x1, z0, z1, 0.05, 0.006, Z_CPAINT_S)
    box6(ki, (x0 - 0.03, -YI, z0 - 0.03), (x1 + 0.03, -YI + 0.05, z0), Z_TIMBER, skip=('-y',))        # inside sill
    fw = 0.045                                                            # frame and glazing bars (white), the pane
    ya, yb = -2.42, -2.36
    for lo, hi, sk in (((x0, ya, z0), (x1, yb, z0 + fw), '-z'), ((x0, ya, z1 - fw), (x1, yb, z1), '+z'),
                       ((x0, ya, z0 + fw), (x0 + fw, yb, z1 - fw), '-x'), ((x1 - fw, ya, z0 + fw), (x1, yb, z1 - fw), '+x')):
        box6(ki, lo, hi, Z_TRIMW, skip=(sk,))                              # (the face on the reveal left out)
    xm, zm = (x0 + x1) / 2, (z0 + z1) / 2
    yg = (ya + yb) / 2
    box6(ki, (xm - 0.015, yg - 0.015, z0 + fw), (xm + 0.015, yg + 0.015, z1 - fw), Z_TRIMW, skip=('-z', '+z'))
    box6(ki, (x0 + fw, yg - 0.012, zm - 0.015), (x1 - fw, yg + 0.012, zm + 0.015), Z_TRIMW, skip=('-x', '+x'))
    g = kb('Window_Glass', 'glass')
    for yy, n in ((yg - 0.0005, (0, -1, 0)), (yg + 0.0005, (0, 1, 0))):
        face(g, [Vector((x0 + fw, yy, z0 + fw)), Vector((x1 - fw, yy, z0 + fw)), Vector((x1 - fw, yy, z1 - fw)),
                 Vector((x0 + fw, yy, z1 - fw))], ZERO, n)
    part('Window_Glass', 'static', (xm, yg, zm), parent='GenContainer', note='window pane (glass material, both faces)')
    # security grille outside: flat frame, four bars, a cross flat
    yb0, yb1 = -2.458, -2.444
    for lo, hi in (((x0 - 0.05, yb0, z1 + 0.02), (x1 + 0.05, yb1, z1 + 0.05)), ((x0 - 0.05, yb0, z0 - 0.05), (x1 + 0.05, yb1, z0 - 0.02)),
                   ((x0 - 0.05, yb0, z0 - 0.02), (x0 - 0.02, yb1, z1 + 0.02)), ((x1 + 0.02, yb0, z0 - 0.02), (x1 + 0.05, yb1, z1 + 0.02)),
                   ((x0 - 0.02, yb0 + 0.002, zm - 0.015), (x1 + 0.02, yb1 - 0.003, zm + 0.015))):
        box6(k, lo, hi, Z_STEELBLK)                                       # (the cross flat clear of the bars' facets)
    for i in range(4):
        xb = x0 + 0.12 * (i + 1)
        k.cyl((xb, (yb0 + yb1) / 2, z0 - 0.02), (xb, (yb0 + yb1) / 2, z1 + 0.02), 0.008, Z_STEELBLK, 6)
    for xx in (x0 - 0.035, x1 + 0.035):                                   # lugs to the flange
        for zz in (z0 - 0.035, z1 + 0.035):
            k.box(xx - 0.01, xx + 0.01, yb1, -2.436, zz - 0.01, zz + 0.01, Z_STEELBLK)
    # board shutter inside, hinged at the window's east edge; modelled open (folded flat east of the window)
    S = kb('Window_Shutter', 'Cont')
    sx0, sx1, sz0, sz1 = x0 - 0.03, x1 + 0.03, z0 + 0.002, z1 + 0.03
    yw, yr = -YI + 0.005, -YI + 0.035                                     # closed: wall side / room side (as the shed's)
    box6(S, (sx0, yw, sz0), (sx1, yr, sz1), Z_DOORIN)
    for zc in (sz0 + 0.10, sz1 - 0.10):
        box6(S, (sx0 + 0.03, yr, zc - 0.035), (sx1 - 0.03, yr + 0.02, zc + 0.035), Z_TIMBER, skip=('-y',))
    S.cyl(Vector((sx0 + 0.06, yr + 0.02, (sz0 + sz1) / 2)), Vector((sx0 + 0.06, yr + 0.05, (sz0 + sz1) / 2)), 0.012, Z_TIMBER, 8)
    piv = Vector((sx1, yr, (sz0 + sz1) / 2))
    for zc in (sz0 + 0.08, sz1 - 0.08):
        S.cyl(piv + Vector((0, 0, zc - piv.z - 0.03)), piv + Vector((0, 0, zc - piv.z + 0.03)), 0.008, Z_STEELBLK, 6)
    transform_kb(S, rot_about(piv, (0, 0, 1), 180.0))
    part('Window_Shutter', 'hinge', piv, (0, 0, 1), (0, 180), parent='GenContainer', states=['open (on the wall)', 'closed'],
         note='inside board shutter: 0 = folded open on the wall east of the window, 180 = over the window; Window_Latch '
              'holds it shut')
    socket('Hand_Window_Shutter', piv + Vector((0.60, 0.04, 0.0)), 'hand', parent='Window_Shutter')
    L = kb('Window_Latch', 'Cont')
    lp = Vector((x0 - 0.08, yr, 1.76))
    box6(ki, (lp.x - 0.012, -YI, lp.z - 0.02), (lp.x + 0.012, lp.y, lp.z + 0.02), Z_TIMBER, skip=('-y',))
    L.box(lp.x - 0.012, lp.x + 0.012, lp.y + 0.001, lp.y + 0.016, lp.z - 0.08, lp.z + 0.08, Z_TIMBER)
    L.cyl(lp + Vector((0, 0.015, 0)), lp + Vector((0, 0.02, 0)), 0.006, Z_STEELBLK, 6)
    part('Window_Latch', 'hinge', lp, (0, -1, 0), (0, 90), parent='GenContainer', states=['free', 'holding the shutter'],
         note='turn-button on the wall west of the window: 90 = across the closed shutter edge (+ = clockwise seen from the room)')
    socket('Hand_Window_Latch', lp + Vector((0, 0.02, 0.04)), 'hand', parent='Window_Latch')


# ================================================================ radiator louvre, exhaust and stack
BLADE_P = 0.144                        # six 16 cm blades at 10 deg: the stack clears the opening by a centimetre
BLADE_Z = [(LOUV['z0'] + LOUV['z1']) / 2 + (i - 2.5) * BLADE_P for i in range(6)]
BLADE_X = (XI + XO - 0.008) / 2
LEVER_P = Vector((XI - 0.04, LOUV['y1'] + 0.10, 1.31))


def louvres():
    k, ki = KBS['GenContainer'], KBS['GenContainer_In']
    y0, y1, z0, z1 = LOUV['y0'], LOUV['y1'], LOUV['z0'], LOUV['z1']
    sleeve(ki, 'x', XI, XO - 0.008, y0, y1, z0, z1, Z_TIMBER)          # timber reveals, as the shed's
    f = 0.04
    for lo, hi in (((XI - f, y0 - f, z1), (XI, y1 + f, z1 + f)), ((XI - f, y0 - f, z0 - f), (XI, y1 + f, z0)),
                   ((XI - f, y0 - f, z0), (XI, y0, z1)), ((XI - f, y1, z0), (XI, y1 + f, z1))):
        box6(ki, lo, hi, Z_STEELBLK, skip=('+x',))
    flange(k, 'x', XO - 0.008, 1, y0, y1, z0, z1, 0.05, 0.006, Z_GALV)
    c0 = Vector((math.sin(math.radians(10)), 0, math.cos(math.radians(10))))
    for i, zc in enumerate(BLADE_Z):
        name = f'Louvre_Blade_{i + 1}'
        b = kb(name, 'Cont')
        piv = Vector((BLADE_X, (y0 + y1) / 2, zc))
        b.box_m(piv, (y1 - y0 - 0.02, 0.16, 0.008), Z_GALV, VM.frame_R(Vector((0, 1, 0)), c0))
        b.cyl(Vector((BLADE_X, y0 - 0.005, zc)), Vector((BLADE_X, y1 + 0.005, zc)), 0.006, Z_STEELBLK, 6)
        part(name, 'hinge', piv, (0, 1, 0), (0, 75), parent='GenContainer', states=['shut', 'open'],
             links={'from': 'Louvre_Lever', 'ratio': 1.0},
             note='radiator outlet louvre blade: follows Louvre_Lever 1:1 (linkage hidden in the frame)')
    p = LEVER_P                                                           # lever on a quadrant plate north of the louvre
    qy = p.y + 0.025
    poly = ([(XI, p.z + 0.04)] + [(p.x - 0.33 * math.sin(math.radians(a)), p.z - 0.33 * math.cos(math.radians(a)))
                                  for a in range(85, -1, -5)] + [(XI, p.z - 0.36)])
    area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    if area < 0:
        poly = list(reversed(poly))
    prism_y(ki, poly, qy, qy + 0.006, Z_STEELBLK, Z_STEELBLK, [Z_STEELBLK] * len(poly))
    ki.cyl(p + Vector((0, 0.02, 0)), p + Vector((0, 0.04, 0)), 0.014, Z_STEELBLK, 8)
    L = kb('Louvre_Lever', 'Cont')
    L.box_m(p + Vector((0, 0, -0.15)), (0.03, 0.01, 0.30), Z_STEELBLK)
    L.cyl(p + Vector((0, -0.005, -0.305)), p + Vector((0, -0.005, -0.18)), 0.016, Z_TIMBER, 8)
    L.cyl(p - Vector((0, 0.01, 0)), p + Vector((0, 0.02, 0)), 0.012, Z_STEELBLK, 8)
    part('Louvre_Lever', 'hinge', p, (0, 1, 0), (0, 75), parent='GenContainer', states=['shut', 'open'],
         note='louvre operator: pull the handle towards the room (0 shut .. 75 open); the six blades follow; '
              'running with it shut overheats the engine (TEMP lamp)')
    socket('Hand_Louvre_Lever', p + Vector((0, -0.005, -0.25)), 'hand', parent='Louvre_Lever')
    # exhaust: thimble plates, collar inside, pipe outside, stand-offs, the stack, the rain flap
    ey, ez = EXH_Y, EXH_Z
    ki.box(XI - 0.004, XI, ey - 0.13, ey + 0.13, ez - 0.13, ez + 0.13, Z_GALV)
    k.box(XO - 0.008, XO - 0.004, ey - 0.13, ey + 0.13, ez - 0.13, ez + 0.13, Z_GALV)
    ki.lathe(Vector((XI - 0.03, ey, ez)), (1, 0, 0), [(0.0, 0.052), (0.03, 0.052)], Z_GALV, 10, cap0=True, cap1=False)
    sx = STACK_X
    k.tube([Vector((XO - 0.02, ey, ez)), Vector((sx - 0.07, ey, ez)), Vector((sx - 0.02, ey, ez + 0.02)),
            Vector((sx, ey, ez + 0.07)), Vector((sx, ey, STACK_TOP))], 0.04, Z_RUSTPIPE, 10, caps=False)
    k.lathe(Vector((sx, ey, STACK_TOP)), (0, 0, 1), [(0.0, 0.04), (0.0, 0.035)], Z_RUSTPIPE, 10, cap0=False, cap1=True)
    for zc in (2.45, 2.69):
        k.box(XO - 0.004, sx - 0.045, ey - 0.015, ey + 0.015, zc - 0.004, zc + 0.004, Z_STEELBLK)
        k.lathe(Vector((sx, ey, zc - 0.012)), (0, 0, 1), [(0.0, 0.047), (0.024, 0.047)], Z_STEELBLK, 10, cap0=False, cap1=False)
    F = kb('Exhaust_Flap', 'Cont')
    fp = Vector((sx, ey + 0.048, STACK_TOP + 0.006))
    F.lathe(Vector((sx, ey, STACK_TOP + 0.0005)), (0, 0, 1), [(0.0, 0.05), (0.006, 0.05), (0.008, 0.0)], Z_RUSTPIPE, 10, cap0=True)
    k.box(sx - 0.012, sx + 0.012, ey + 0.036, ey + 0.05, STACK_TOP - 0.02, STACK_TOP + 0.004, Z_RUSTPIPE)
    F.cyl(fp + Vector((-0.02, 0, 0)), fp + Vector((0.02, 0, 0)), 0.006, Z_RUSTPIPE, 6)
    part('Exhaust_Flap', 'hinge', fp, (-1, 0, 0), (0, 70), parent='GenContainer', states=['shut', 'lifted'],
         note='rain flap on the stack: the exhaust lifts it while the engine runs (flutter 20..60 with the beat), '
              'drops shut when it stops')


# ================================================================ mast, conduits, switch, outlet, floor covers
def services():
    k, ki = KBS['GenContainer'], KBS['GenContainer_In']
    mx, yo = MAST_X, -YO - 0.04
    # service entrance: LB fitting through the south wall above the board, the mast up past the roof, weatherhead,
    # spool rack, drip loops and the two drops (LINE in, feeder out)
    zl = 2.31
    ki.cyl(Vector((mx, -YI + 0.02, zl)), Vector((mx, -YI - 0.01, zl)), 0.02, Z_GALV, 8)
    k.cyl(Vector((mx, -YO + 0.03, zl)), Vector((mx, yo, zl)), 0.02, Z_GALV, 8)
    k.box(mx - 0.035, mx + 0.035, yo - 0.03, yo + 0.03, zl - 0.04, zl + 0.04, Z_GALV)
    k.cyl(Vector((mx, yo, zl + 0.04)), Vector((mx, yo, 3.22)), 0.024, Z_GALV, 8)
    k.lathe(Vector((mx, yo, 3.22)), (0, 0, 1), [(0.0, 0.028), (0.02, 0.05), (0.045, 0.05), (0.06, 0.0)], Z_STEELBLK, 10, cap0=True)
    for zc in (2.05, 2.55):                                                # straps to the wall / top rail
        k.box(mx - 0.02, mx + 0.02, -YO - 0.07, -YO + 0.008, zc - 0.01, zc + 0.01, Z_GALV)
    rack_x = mx + 0.30
    k.box(mx, rack_x + 0.02, yo - 0.012, yo + 0.012, 2.98, 3.00, Z_STEELBLK)
    k.box(rack_x - 0.02, rack_x + 0.02, yo - 0.015, yo + 0.015, 2.70, 2.98, Z_STEELBLK)
    spools = []
    for zc in (2.73, 2.81, 2.89, 2.97):
        k.box(rack_x - 0.012, rack_x + 0.012, yo - 0.06, yo - 0.015, zc - 0.006, zc + 0.006, Z_STEELBLK)
        c = Vector((rack_x, yo - 0.075, zc))
        k.lathe(c - Vector((0, 0, 0.025)), (0, 0, 1), [(0.0, 0.022), (0.008, 0.026), (0.018, 0.016), (0.032, 0.016),
                                                        (0.042, 0.026), (0.05, 0.022)], Z_INSUL, 10)
        spools.append(c)
    wh = Vector((mx, yo, 3.26))
    for i, c in enumerate(spools):
        a = wh + Vector((0.01 * (i - 1.5), -0.03, 0.0))
        k.tube([a, a + Vector((0.02, -0.04, -0.10)), (a + c) / 2 + Vector((0.04, -0.03, -0.12)), c + Vector((-0.03, -0.01, 0.02)),
                c + Vector((0, 0, 0))], 0.006, Z_WIRE, 5, caps=True)
    drop_end = {}
    for name, (i0, i1) in (('LINE', (0, 1)), ('FEED', (2, 3))):
        for i in (i0, i1):
            c = spools[i]
            e = c + Vector((0.10 + 0.05 * i, -0.75, 0.05))
            k.tube([c + Vector((0.01, -0.02, 0)), c + Vector((0.05, -0.30, 0.02)), e], 0.006, Z_WIRE, 5)
        drop_end[name] = spools[i1] + Vector((0.10 + 0.05 * i1, -0.75, 0.05))
    socket('Line_In', drop_end['LINE'], 'item_slot', parent='GenContainer', dir=(0, -1, 0),
           note='LINE (grid) drop: continue the overhead line from here (rope / line renderer); feeds the board via Board_Brk_Line')
    socket('Feed_Out', drop_end['FEED'], 'item_slot', parent='GenContainer', dir=(0, -1, 0),
           note='feeder to the base: the eight circuits leave here (draw the cable to the base poles)')
    # conduits inside (on the ply, under the blocking and the joists): board -> mast; board -> board lamp; board -> the
    # south ceiling lamp -> the north one; board -> up the doorway's ply -> along the header (T-box: out to the barn
    # light) -> over the joint posts -> the north box's ledger -> switch -> outlet
    yi = -YI + 0.025
    conduit(ki, [Vector((mx, yi, 2.21)), Vector((mx, yi, zl)), Vector((mx, -YI - 0.005, zl))], r=0.02)
    conduit(ki, [Vector((-1.45, yi, 2.21)), Vector((-1.45, yi, 2.37))])
    lg, lc = LAMP_C['Bulk_Genset'], LAMP_C['Bulk_Ceiling']
    conduit(ki, [Vector((-1.62, yi, 2.21)), Vector((-1.62, yi, CZ)), Vector((lg.x, yi, CZ)), Vector((lg.x, lg.y - 0.05, CZ))])
    across = [Vector((lg.x, lg.y + 0.05, CZ)), Vector((lg.x, 0.40, CZ)), Vector((lc.x, 0.40, CZ)), Vector((lc.x, lc.y - 0.05, CZ))]
    conduit(ki, across, clamps=99.0)                                       # clipped to the joists only
    for p_ in ([Vector((lg.x, yy, CZ)) for yy in (-0.55, -0.05)] + [Vector((JOIST_X[3], 0.40, CZ))] +
               [Vector((lc.x, yy, CZ)) for yy in (0.72,)]):
        d_ = Vector((1, 0, 0)) if abs(p_.y - 0.40) < 1e-6 else Vector((0, 1, 0))
        ki.box_m(p_, (0.026, 0.028, 0.026) if d_.x else (0.028, 0.026, 0.026), Z_GALV)             # saddle clamps
    xh, xw, hz = XRI + PLY + 0.025, -XI + 0.025, 2.62
    conduit(ki, [Vector((-1.78, yi, 2.21)), Vector((-1.78, yi, CZ)), Vector((xh, yi, CZ)), Vector((xh, yi, hz)), Vector((xh, SW_Y, hz)),
                 Vector((xh, SW_Y, 2.555)), Vector((xw, SW_Y, 2.555)), Vector((xw, SW_Y, 1.655))])
    conduit(ki, [Vector((xw, SW_Y, 1.565)), Vector((xw, SW_Y, 0.72))])
    ki.box(xh - 0.03, xh + 0.03, -1.25, -1.19, hz - 0.03, hz + 0.03, Z_GALV)        # T-box, conduit out to the barn light
    conduit(ki, [Vector((xh, -1.22, hz)), Vector((XR - 0.01, -1.22, hz))])
    # light switch and the outlet under it (west wall of the north box, just north of the doorway)
    sw = Vector((-XI, SW_Y, 1.61))
    box6(ki, (-XI, SW_Y - 0.04, 1.565), (-XI + 0.045, SW_Y + 0.04, 1.655), Z_GALV, skip=('-x',))
    S = kb('Light_Switch', 'Cont')
    sp = sw + Vector((0.045, 0, 0))
    S.cyl(sp, sp + Vector((0.025, 0, -0.012)), 0.005, Z_STEELBLK, 6, r2=0.0035)
    part('Light_Switch', 'hinge', sp, (0, -1, 0), (0, 50), parent='GenContainer', states=['off (down)', 'on (up)'],
         note='container lights (three bulkheads) on the CONTAINER circuit (Board_MCB_8): up = on (+50)')
    socket('Hand_Light_Switch', sp + Vector((0.025, 0, 0)), 'hand', parent='Light_Switch')
    box6(ki, (-XI, SW_Y - 0.045, 0.60), (-XI + 0.05, SW_Y + 0.045, 0.72), Z_GALV, skip=('-x',))
    socket('Outlet_Wall', (-XI + 0.052, SW_Y, 0.66), 'item_slot', parent='GenContainer', dir=(1, 0, 0),
           note='230 V outlet on the CONTAINER circuit: plugs go here (inspection lamp, charger)')
    # floor: the shed's chequer covers over the cable trench genset -> board (flush), the conduit up to the board; the
    # fuel lines run on clips over the concrete (gen_room.day_tank)
    box6(ki, (0.35, -YI + 0.06, FC), (0.59, -1.385, FC + 0.006), Z_CHEQUER, skip=('-z',))
    box6(ki, (-1.57, -YI + 0.06, FC), (0.35, -YI + 0.30, FC + 0.006), Z_CHEQUER, skip=('-z', '+x'))
    conduit(ki, [Vector((-1.45, -YI + 0.04, FC + 0.006)), Vector((-1.45, -YI + 0.04, 1.11))], r=0.022, clamps=0.35)
    # extinguisher bracket (west wall of the north box)
    ey = G_EXT.y - 1.30
    ki.box(-XI, -XI + 0.012, ey - 0.03, ey + 0.03, 1.16, 1.46, Z_STEELBLK)
    ki.box(-XI, -XI + 0.10, ey - 0.06, ey + 0.06, 0.90, 0.91, Z_STEELBLK)


# ================================================================ lamps, signs
def bulkhead(ki, name, c, n):
    """caged bulkhead on a face (normal n): base plate, dome housing, frosted lens, three cage bars"""
    n = Vector(n)
    u = Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))
    v = n.cross(u)
    ki.box_m(c + n * 0.005, (0.09 if abs(n.x) < 0.5 else 0.01, 0.09 if abs(n.y) < 0.5 else 0.01, 0.09 if abs(n.z) < 0.5 else 0.01),
             Z_STEELBLK)
    ki.lathe(c + n * 0.01, n, [(0.0, 0.07), (0.01, 0.085), (0.045, 0.085), (0.05, 0.072)], Z_STEELBLK, 12, cap0=True, cap1=False)
    L = kb('Lens_' + name, 'lens:bulk')
    dome_c = c + n * 0.058
    L.disc_uv(dome_c, n, 0.068, uv('l_bulk'), 12, dome=0.04)
    for a in (0, 60, 120):
        d = u * math.cos(math.radians(a)) + v * math.sin(math.radians(a))
        pts = [dome_c + d * 0.078 * math.cos(math.radians(t)) + n * 0.052 * math.sin(math.radians(t)) for t in range(0, 181, 30)]
        ki.tube(pts, 0.003, Z_STEELBLK, 4, caps=False)
    up = (0, 1, 0) if abs(n.z) > 0.5 else (0, 0, 1)
    LAMPS.append((name, dome_c + n * 0.03, tuple(n), 'bulkhead', up))
    part('Lens_' + name, 'static', dome_c + n * 0.02, parent='GenContainer', note='frosted dome of a caged bulkhead (lights up with LIGHT_' + name + ')')


def lamps():
    k, ki = KBS['GenContainer'], KBS['GenContainer_In']
    for name, c in LAMP_C.items():
        bulkhead(ki, name, c, (0, 0, -1))
    bulkhead(ki, 'Bulk_Board', Vector((-1.45, -YI, 2.43)), (0, 1, 0))
    # barn light over the doors, on the door header
    wp = Vector((XR, -1.22, 2.68))
    k.box(wp.x - 0.012, wp.x, wp.y - 0.05, wp.y + 0.05, wp.z - 0.045, wp.z + 0.045, Z_ENAMEL)
    arm = [wp + Vector((-0.012, 0, 0)), wp + Vector((-0.12, 0, 0.02)), wp + Vector((-0.24, 0, 0.09)),
           wp + Vector((-0.33, 0, 0.13)), wp + Vector((-0.38, 0, 0.11)), wp + Vector((-0.40, 0, 0.085))]
    k.tube(arm, 0.013, Z_ENAMEL, 6)
    sc = wp + Vector((-0.40, 0, 0.085))
    k.lathe(sc, (0, 0, -1), [(0.0, 0.03), (0.02, 0.05), (0.06, 0.11), (0.095, 0.165), (0.10, 0.17)], Z_ENAMEL, 14,
            cap0=True, cap1=False)
    k.lathe(sc - Vector((0, 0, 0.002)), (0, 0, -1), [(0.095, 0.162), (0.06, 0.106), (0.02, 0.046), (0.0, 0.026)], Z_ENAMEL_IN, 14,
            cap0=False, cap1=True)
    k.cyl(sc - Vector((0, 0, 0.004)), sc - Vector((0, 0, 0.045)), 0.022, Z_STEELBLK, 8)
    L = kb('Lens_Ext_Door', 'lens:ext')
    bulb_c = sc - Vector((0, 0, 0.045))
    L.disc_uv(bulb_c, Vector((0, 0, -1)), 0.03, uv('l_ext'), 10, dome=0.045)
    LAMPS.append(('Ext_Door', bulb_c - Vector((0, 0, 0.03)), (0, 0, -1), 'barnlight', (-1, 0, 0)))
    part('Lens_Ext_Door', 'static', bulb_c - Vector((0, 0, 0.02)), parent='GenContainer', note='bulb under the barn-light shade over the doors')


def signs():
    S = kb('Cont_Signs', 'panel')
    box6(KBS['GenContainer'], (1.20 - 0.555, -YO + 0.004, 1.795), (1.20 + 0.555, -YO + 0.008, 2.105), Z_STEELBLK, skip=('+y',))
    quad(S, (1.20, -YO + 0.002, 1.95), (0, -1, 0), 1.10, 0.30, uv('csign_gen'))
    quad(S, (XI - 0.003, LEVER_P.y + 0.07, 1.71), (-1, 0, 0), 0.32, 0.10, uv('csign_louvre'))
    quad(S, (2.17, YI - 0.003, 1.99), (0, -1, 0), 0.20, 0.20, uv('csign_flame'))
    part('Cont_Signs', 'static', (0, 0, 0), parent='GenContainer',
         note='STROMERZEUGER / GENERATOR plate on the south wall; inside: the louvre and no-flames signs (panel atlas)')
    yR = sum(LEAVES['Door_R'][4]) / 2
    D = kb('Door_R_Sign', 'panel')
    box6(KBS['Door_R'], (XL_O - 0.001, yR - 0.215, 1.865), (XL_C, yR + 0.215, 2.035), Z_STEELBLK, skip=('+x',))
    quad(D, (XL_O - 0.003, yR, 1.95), (-1, 0, 0), 0.42, 0.164, uv('csign_gen_door'))
    part('Door_R_Sign', 'static', (XL_O - 0.003, yR, 1.95), parent='Door_R', note='STROMERZEUGER / GENERATOR on the active leaf')
    yL = sum(LEAVES['Door_L'][4]) / 2
    D = kb('Door_L_Sign', 'panel')
    for zc, w_, h_ in ((1.70, 0.20, 0.25), (2.20, 0.24, 0.10)):
        box6(KBS['Door_L'], (XL_O - 0.001, yL - w_ / 2 - 0.005, zc - h_ / 2 - 0.005), (XL_C, yL + w_ / 2 + 0.005, zc + h_ / 2 + 0.005),
             Z_STEELBLK, skip=('+x',))
    quad(D, (XL_O - 0.003, yL, 1.70), (-1, 0, 0), 0.20, 0.25, uv('csign_danger'))
    quad(D, (XL_O - 0.003, yL, 2.20), (-1, 0, 0), 0.24, 0.10, uv('csign_noentry'))
    part('Door_L_Sign', 'static', (XL_O - 0.003, yL, 1.70), parent='Door_L',
         note='VORSICHT 400 V / DANGER 400 V and ZUTRITT VERBOTEN / NO ENTRY on the passive leaf')


# ================================================================ snow (optional, starts hidden)
SNOW_Z = 2.747


def snow():
    from noise import fbm
    k = kb('Snow_Roof', 'Snow')
    nx, ny = 18, 14
    xs = np.linspace(-2.98, 2.98, nx + 1)
    ys = np.linspace(-2.40, 2.40, ny + 1)
    T, Bt = [], []
    for y in ys:
        rt, rb = [], []
        for x in xs:
            p = np.array([[x, y, 0.0]], np.float32)
            edge = min((2.98 - abs(x)) / 0.30, (2.40 - abs(y)) / 0.30, 1.0)
            melt = 1.0 - 0.65 * math.exp(-((x - 3.0) ** 2 + (y - EXH_Y) ** 2) / 0.45 ** 2)
            th = 0.15 * (0.75 + 0.5 * float(fbm(p, 1.4, 2, seed=93)[0])) * max(0.12, edge) ** 0.5 * melt
            rb.append(Vector((x, y, SNOW_Z)))
            rt.append(Vector((x, y, SNOW_Z + max(0.01, th))))
        T.append(rt)
        Bt.append(rb)
    for j in range(ny):
        for i in range(nx):
            face(k, [T[j][i], T[j][i + 1], T[j + 1][i + 1], T[j + 1][i]], Z_SNOW, (0, 0, 1))
    for j in range(ny):
        for i, sg in ((0, -1), (nx, 1)):
            face(k, [Bt[j][i], Bt[j + 1][i], T[j + 1][i], T[j][i]], Z_SNOW, (sg, 0, 0))
    for i in range(nx):
        for j, sg in ((0, -1), (ny, 1)):
            face(k, [Bt[j][i], Bt[j][i + 1], T[j][i + 1], T[j][i]], Z_SNOW, (0, sg, 0))
    part('Snow_Roof', 'static', (0, 0, SNOW_Z), parent='GenContainer', blendshape='Clear', default='hidden',
         states=['0 none', '1 full (~15 cm)'],
         note='snow on the two roofs: blend shape Clear (100 = no snow: the mesh sinks onto the roof, hide the renderer '
              'there); thin round the stack, slides off in chunks (VFX) when the exhaust warms it')
    d = kb('Snow_DoorDrift', 'Snow')
    x0, x1 = -3.88, -3.032
    xs = np.linspace(x0, x1, 10)
    ys = np.linspace(-2.40, 2.40, 25)
    G = []
    for x in xs:
        row = []
        for y in ys:
            u = (x - x0) / (x1 - x0)
            v = abs(y) / 2.40
            p = np.array([[x, y, 0.0]], np.float32)
            h = 0.70 * u ** 1.4 * max(0.0, 1 - v ** 4) ** 0.6 * (0.8 + 0.4 * float(fbm(p, 2.2, 2, seed=94)[0]))
            row.append(Vector((x, y, max(0.006, h))))
        G.append(row)
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            face(d, [G[i][j], G[i + 1][j], G[i + 1][j + 1], G[i][j + 1]], Z_SNOW, (0, 0, 1))
    for j in range(len(ys) - 1):
        a, b = G[-1][j], G[-1][j + 1]
        face(d, [Vector((a.x, a.y, 0.0)), Vector((b.x, b.y, 0.0)), b, a], Z_SNOW, (1, 0, 0))
    part('Snow_DoorDrift', 'static', (x0 + 0.40, 0.0, 0.0), parent='GenContainer', blendshape='Clear', default='hidden',
         states=['0 none', '1 drift up to 0.7 m'],
         note='drift against the doors outside (both boxes): blend shape Clear (100 = dug out, the mesh sinks under the '
              'ground: hide it); the leaves (bottom edge 0.275 m up) clear it only from Clear 61, below that they jam - '
              'dig with the van\'s shovel')


# ================================================================ points, colliders, knock rays
def play_points():
    for name, kind, pos, d, note in (
            ('Audio_Exhaust', 'audio', (STACK_X, EXH_Y, STACK_TOP), None, 'exhaust beat at the stack (outside), the flap rattling'),
            ('Audio_Louvre', 'audio', (XI, -1.015, 1.16), None, 'louvre blades rattling in the wind / in the fan blast'),
            ('Audio_Door', 'audio', (XR, -1.22, 1.30), None, 'cargo doors: the bars and cams, hinges groaning, the padlock, wind'),
            ('Audio_Roof', 'audio', (0.0, 0.0, 3.0), None, 'steel roof: ticks and booms in the cold, snow sliding, footsteps up there'),
            ('Audio_Wind', 'audio', (-2.95, 1.22, 2.22), None, 'wind through the two intake louvres in the north box\'s doors'),
            ('VFX_Exhaust', 'vfx', (STACK_X, EXH_Y, STACK_TOP + 0.03), (0, 0, 1),
             'exhaust: a black puff on starting, grey smoke under load, thin haze idling'),
            ('VFX_LouvreHeat', 'vfx', (XO + 0.05, -1.015, 1.16), (1, 0, 0),
             'warm air from the radiator through the open louvre: steam in the frost, melts the snow below'),
            ('VFX_DoorSnow', 'vfx', (XRI + 0.05, -1.22, FC + 0.05), (1, 0, 0), 'snow blowing in at the doors\' gaps'),
            ('Heat_Louvre', 'heat', (XO + 0.20, -1.015, 1.16), None, 'warm spot outside the louvre while the set runs')):
        socket(name, pos, kind, note=note, parent='GenContainer')
        if d is not None:
            CONTRACT['sockets'][name]['dir'] = list(d)
    s2 = 1 / math.sqrt(2)
    for name, pose, hip, eye, facing, note in (
            ('Hide_UnderWindow', 'crouch', (-0.10, -2.035, FC + 0.30), (-0.10, -1.975, FC + 0.86), (0, 1, 0),
             'crouched under the window: not seen from outside through the glass'),
            ('Hide_ShelfCorner', 'crouch', (-2.55, 2.00, FC + 0.30), (-2.50, 1.95, FC + 0.86), (s2, -s2, 0),
             'crouched in the north-west corner behind the shelf: not seen from the doorway')):
        socket(name, hip, 'hide', note=note, parent='GenContainer')
        CONTRACT['sockets'][name].update(pose=pose, eye=K.r4(eye), facing=list(facing))


def static_boxes_shell():
    """(name, parent, (x0, x1, y0, y1, z0, z1), rotation or None) in the container frame"""
    R = 'GenContainer'
    B = [(f'Pad_{i + 1}', R, (x - sx / 2, x + sx / 2, y - sy / 2, y + sy / 2, 0.0, ZB), None) for i, (x, y, sx, sy) in enumerate(PADS)]
    w = WIN
    B += [('Floor', R, (-XO, XO, -YO, YO, ZB, FC), None),
          ('Roof', R, (-XO, XO, -YO, YO, ZJ, ZT), None),                     # (from the joists' underside)
          ('Wall_S_W', R, (XRI, w['x0'], -YO, -YI, FC, CI), None),
          ('Wall_S_E', R, (w['x1'], XO, -YO, -YI, FC, CI), None),
          ('Wall_S_Low', R, (w['x0'], w['x1'], -YO, -YI, FC, w['z0']), None),
          ('Wall_S_High', R, (w['x0'], w['x1'], -YO, -YI, w['z1'], CI), None),
          ('Window', R, (w['x0'], w['x1'], -YO, -YI, w['z0'], w['z1']), None),
          ('Wall_N', R, (-XO, XO, YI, YO, FC, CI), None),
          ('Wall_E_N', R, (XI, XO, -CAST[1], YO, FC, CI), None),
          ('Wall_E_S1', R, (XI, XO, -YO, LOUV['y0'], FC, CI), None),
          ('Wall_E_S2', R, (XI, XO, LOUV['y1'], -CAST[1], FC, CI), None),
          ('Wall_E_Low', R, (XI, XO, LOUV['y0'], LOUV['y1'], FC, LOUV['z0']), None),
          ('Wall_E_High', R, (XI, XO, LOUV['y0'], LOUV['y1'], LOUV['z1'], CI), None),
          ('Louvre', R, (XI, XO, LOUV['y0'], LOUV['y1'], LOUV['z0'], LOUV['z1']), None),
          ('Wall_W_N', R, (-XO, -XI, 0.0, YO, FC, CI), None),
          ('Post_W_S', R, (XR, XRI + PLY, -YO, -YO + RPW, FC, CI), None),
          ('Post_W_J', R, (XR, XRI + PLY, -RPW, RPW + PLY, FC, CI), None),
          ('Post_W_N', R, (XR, XRI + PLY, YO - RPW - PLY, YO, FC, CI), None),
          ('Header_W', R, (XR, XRI + PLY, -YO, 0.0, HDR_Z0, CI), None),
          ('Ledger_W_N', R, (-XI, XRI + PLY, RPW + PLY, YO - RPW - PLY, HDR_Z0, CI), None),
          ('Post_J_E', R, (XF_BOX, XI, -CAST[1] - 0.01, CAST[1] + 0.01, FC, CI), None),
          ('Post_E_N', R, (XF_BOX, XI, YO - CAST[1] - 0.01, YI, FC, CI), None),
          ('Post_E_S', R, (XF_BOX, XI, -YI, -YO + CAST[1] + 0.01, FC, CI), None),
          ('Stack', R, (STACK_X - 0.045, STACK_X + 0.045, EXH_Y - 0.045, EXH_Y + 0.045, EXH_Z - 0.05, STACK_TOP), None),
          ('StackPipe', R, (XO, STACK_X, EXH_Y - 0.045, EXH_Y + 0.045, EXH_Z - 0.045, EXH_Z + 0.045), None),
          ('Step', R, (STEP[0], STEP[1], STEP[2], STEP[3], 0.0, STEP[4]), None),
          ('Door_R', 'Door_R', (XL_O, XR, -2.430, -1.222, LEAF['z0'], LEAF['z1']), None),
          ('Door_L', 'Door_L', (XL_O, XR, -1.216, -0.008, LEAF['z0'], LEAF['z1']), None),
          ('Shutter', 'Window_Shutter', (w['x1'] + 0.03, w['x1'] + 0.69, -YI + 0.035, -YI + 0.065, w['z0'], w['z1'] + 0.03), None)]
    return B


def knock_rays():
    R = []
    for i, x in enumerate((-2.3, -0.9, 1.0, 2.2)):
        R.append((f'Knock_WallS_{i + 1}', (x, -3.2, 1.20), (0, 1, 0)))
    for i, x in enumerate((-2.0, -0.7, 0.9, 2.2)):
        R.append((f'Knock_WallN_{i + 1}', (x, 3.2, 1.20), (0, -1, 0)))
    for i, y in enumerate((-1.95, 0.6, 1.8)):
        R.append((f'Knock_WallE_{i + 1}', (3.9, y, 1.30), (-1, 0, 0)))
    R += [('Knock_Louvre', (3.9, -1.0, 1.05), (-1, 0, 0)),
          ('Knock_WallW_1', (-3.9, 0.60, 1.45), (1, 0, 0)), ('Knock_WallW_2', (-3.9, 1.80, 1.45), (1, 0, 0)),
          ('Knock_Door_R', (-3.9, -1.80, 1.70), (1, 0, 0)), ('Knock_Door_L', (-3.9, -0.60, 1.05), (1, 0, 0)),
          ('Knock_Window', (-0.10, -3.2, 1.62), (0, 1, 0))]
    for i, (x, y) in enumerate(((-1.5, 1.2), (1.5, 1.2), (-1.5, -1.2), (1.5, -1.2))):
        R.append((f'Knock_Roof_{i + 1}', (x, y, 4.2), (0, 0, -1)))
    return R


def build_container():
    structure()
    interior_shell()
    doors()
    window()
    louvres()
    services()
    lamps()
    signs()
    snow()
    play_points()
    part('GenContainer', 'static', (0, 0, 0), parent=None,
         note='the twin container (castings, posts, rails, corrugated walls, roofs, the welded doors of the north box, pads, '
              'step, mast, stack); prefab root')
    part('GenContainer_In', 'static', (0, 0, FC), parent='GenContainer',
         note='inside of the container, finished as the generator shed: ply lining, concrete floor, spruce joists and '
              'blocking under the roof\'s underside, chequer covers, the window, conduits, lamps')
