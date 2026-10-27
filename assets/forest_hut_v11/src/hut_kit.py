"""Forester's hut (FORSTHÜTTE) in the generator shed's style, for the Forest map's prologue (Forest_Opening.json S2):
the same place, size, door, lantern and item spots as the Update 3 hut (TowerHut), rebuilt with the shed's
construction and finishes:
  outside: board-and-batten in a dark stain with white trims (corner boards, door and window trims, barge boards,
  fascia), a galvanised corrugated roof with a ridge cap and rust runs, stone piers, a stepping stone at the door;
  the plank door outside the wall on strap hinges (IX_HutDoor_1, opens outward; v1.1: opening 1.00 x 1.915 m, fits
  under the porch of forest_hut_yard), the window (white frame with glazing
  bars, timber reveals and sill; board shutter and turn-button inside), the storm lantern on its iron bracket right of
  the door, antlers on the gable, the stove pipe with a rain cap; the woodpile under the left eave, a rain barrel, the
  chopping block with the axe, a bench, a ladder;
  inside: the shed's birch-ply lining, a board floor, open spruce rafters, ties, purlins and the roof's underside, a
  cast-iron box stove on galvanised heat shields (door, flue damper, the kettle), the bunk with mattress, blanket and
  pillow, the table under the window, a stool, two shelves on iron brackets, coat hooks with a jacket, boots, the area
  map and the October calendar on the back wall, a hanging oil lamp (off);
  the hunting stand (Hochsitz, 11 m away) and the FORSTHÜTTE sign: separate roots at their Update 3 places.
Frame (the TowerHut prefab's): x to the right seen from the door side, y into the hut (door -> back wall), z up,
metres; origin = the middle of the footprint on the ground; floor z = 0.33.  Unity: (x, y, z) -> (-x, z, -y),
angle -> -angle.  Faces carry a float 'zone' (atlases Hut: the hut and the sign; HutStand: the hunting stand; HutProps:
the small things) or explicit 'PSX' UVs (panel: map, calendar, sign face; lenses; glow cards; glass)."""
import math
import bmesh
import numpy as np
from mathutils import Vector, Matrix
import van3_mech as VM
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, prism_x, prism_y, wall_grid, quad, transform_kb, rot_about, KBS, CONTRACT, LAMPS
from gen_kit import Z_CLAD, Z_TRIMW, Z_LINING, Z_TIMBER, Z_ROOF, Z_ROOFUNDER, Z_DOOR, Z_DOORIN, Z_STEELBLK, Z_GALV, Z_RUSTPIPE
from van2_kit import ZERO
import hut_tex as HT

uv = HT.uv
TAU = 2 * math.pi

# ---------------------------------------------------------------- dimensions (the Update 3 hut's)
FLOOR = 0.33
X0, X1, Y0, Y1 = -1.34, 1.34, -1.20, 1.20             # outer faces of the cladding (sides x, gables y)
T = 0.12                                              # wall: cladding, studs, ply
IX0, IX1, IY0, IY1 = X0 + T, X1 - T, Y0 + T, Y1 - T   # inner faces (room 2.44 x 2.16)
ZB = 0.18                                             # bottom of the cladding (covers the sill beam)
ZE = 2.33                                             # wall top / rafter seat at the outer face
PITCH = math.radians(35.0)
TP, CP, SP = math.tan(PITCH), math.cos(PITCH), math.sin(PITCH)
OV_E, OV_F, OV_B = 0.30, 0.36, 0.26                   # overhangs: eaves (sides), verge front / back
RAFT_D, RAFT_W, PURL, SHEET = 0.12, 0.05, 0.04, 0.025
XE = X1 + OV_E                                        # eave edge (|x|)
YF, YK = Y0 - OV_F, Y1 + OV_B                         # verge edges (front, back)
RAFTERS = [-1.17, -0.585, 0.0, 0.585, 1.17]           # rafter pairs along y (+ verge rafters at the edges)
TIES = [-0.55, 0.55]
PURLINS = [0.22, 0.64, 1.06, 1.48]                    # |x| of the purlins on each slope
# v1.1: the opening 1.00 x 1.915 (1.0: 0.80 x 1.85, x -0.78..0.02, top 2.18), hinges on the left as before. The porch of
# forest_hut_yard (deck 0.32, wall plate 2.36..2.48, rafters at x -1.20 / -0.40 / 0.40 / 1.20 falling 0.20 per metre out)
# sets the height: the leaf swinging out to 105 deg passes under the rafter at x -0.40 about 1 m out, where its bottom is at
# 2.275, and at full open its free edge stops beside the rafter at x -1.20; the middle sits 3 cm right of the 1.0 door's
# (-0.38) to keep that edge clear.
DOOR = dict(x0=-0.85, x1=0.15, z0=FLOOR, z1=2.245)    # opening in the front wall (the leaf overlaps 2 cm at the sides)
LEAF_ZL, LEAF_ZH = FLOOR, DOOR['z1'] + 0.015           # the leaf: 1 cm over the porch deck, 1.5 cm over the head
BENCH_C = Vector((1.52, 0.0, 0.0))                    # the bench, along the right wall under the window (1.0: by the door,
#                                                       now the porch's place)
ANTLER_C, ANTLER_S = Vector((0.0, Y0 - 0.02, 2.80)), 0.85   # the antlers' shield (1.0: x -0.38, z 2.62, size 1: the porch
#                                                       roof of forest_hut_yard now meets the gable there)
CHOP_C = Vector((-2.15, -1.90, 0.0))                  # the chopping block off the porch's front-left corner (1.0: -1.10, -2.55,
#                                                       where the porch's left post stands)
WIN = dict(y0=-0.30, y1=0.30, z0=1.28, z1=1.78)       # opening in the right wall
STOVE = dict(x0=0.74, x1=1.14, y0=0.56, y1=0.96, z0=0.40, z1=0.97)
FLUE = Vector((0.94, 0.76, 0.0))
FLUE_R, FLUE_TOP = 0.06, 3.72
TABLE = dict(x0=0.56, x1=1.20, y0=-0.80, y1=0.20, top=1.08)       # 0.36 m clear of the stove's door
MUG, CANDLE = Vector((0.66, -0.56, 1.08)), Vector((1.08, 0.02, 1.08))
SHELF = dict(x0=-1.21, x1=-0.91, y0=-0.82, y1=0.22, tops=(1.092, 1.643))
BUNK = dict(x0=-1.20, x1=0.60, y0=0.38, y1=1.06, base=0.62, top=0.75)
LANTERN = Vector((0.40, Y0 - 0.26, 1.90))             # globe centre (the light)
HOOK_Z = 2.10
LADDER_Y = -0.80                                      # the roof ladder on the right side
HS_PLACE = (Vector((11.0401, 2.473, 0.5053)), -102.374)    # Hochsitz root in the hut frame (Update 3 layout)
SIGN_PLACE = (Vector((1.60, -3.20, 0.0669)), 0.0)      # sign root
HS_BAKE_DZ = -2.6                                     # the stand is baked 2.6 m lower (position bake range +-4 m)
# items the prologue spawns here (Forest_Opening.json, in this frame): keep their places free
SPOTS = {'Jerrycan': (-0.99, -0.52, FLOOR), 'Funnel': (-1.05, -0.05, SHELF['tops'][0]),
         'Flashlight': (0.90, -0.24, TABLE['top']), 'Note': (0.88, 0.10, TABLE['top'])}

# ---------------------------------------------------------------- zones: Hut atlas (the shed's ids where the look is
# the shed's) and HutProps atlas
Z_STONE, Z_FLOORB, Z_STOVE, Z_FURN, Z_MATTRESS, Z_BLANKET, Z_LOGEND, Z_BARK, Z_WEATHERED, Z_STAVES, Z_WATER, Z_SIGN, \
    Z_PILLOW, Z_LOG = range(100, 114)
HUT_ZONES = [Z_CLAD, Z_TRIMW, Z_LINING, Z_TIMBER, Z_ROOF, Z_ROOFUNDER, Z_DOOR, Z_DOORIN, Z_STEELBLK, Z_GALV, Z_RUSTPIPE] + \
    list(range(100, 114))
# HutStand atlas: the hunting stand (its own atlas: a separate prefab 11 m away)
Z_HS_BOARD, Z_HS_LOG, Z_HS_WOOD, Z_HS_ROOF, Z_HS_STONE, Z_HS_END = range(114, 120)
STAND_ZONES = list(range(114, 120))
# HutProps atlas
Z_ENAMELW, Z_TIN, Z_GLASSJ, Z_CARDBOARD, Z_RUBBER, Z_JACKET, Z_ROPE, Z_ANTLER, Z_AXEHEAD, Z_HANDLE, Z_LANTERN, \
    Z_BRASS, Z_CANDLE, Z_BOTTLE, Z_SHIELD, Z_WIREP = range(120, 136)
PROP_ZONES = list(range(120, 136))


def z_rb(x):
    """rafter bottom line (= gable top edge) at |x|"""
    return ZE + (X1 - abs(x)) * TP


def z_rt(x):
    return z_rb(x) + RAFT_D / CP


def z_sb(x):
    return z_rb(x) + (RAFT_D + PURL) / CP


def z_st(x):
    return z_sb(x) + SHEET / CP


# ---------------------------------------------------------------- helpers
def rock(k, c, size, zone, seed, n=22):
    """low-poly field stone: convex hull of jittered points in an ellipsoid (flat-ish top)"""
    rng = np.random.default_rng(seed)
    pts = []
    for _ in range(n):
        v = rng.normal(size=3)
        v /= np.linalg.norm(v) + 1e-9
        v *= 0.80 + 0.20 * rng.random()
        v[2] = max(v[2], -0.85) if v[2] < 0 else min(v[2], 0.78)
        pts.append(Vector(c) + Vector((v[0] * size[0] / 2, v[1] * size[1] / 2, v[2] * size[2] / 2)))
    tmp = bmesh.new()
    vs = [tmp.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(tmp, input=vs)
    for f in list(tmp.faces):
        face(k, [Vector(v.co) for v in f.verts], zone, f.normal)
    tmp.free()


def log(k, a, b, r, zone_side, zone_end, seg=8):
    """round log a -> b: bark side, end-grain caps"""
    a, b = Vector(a), Vector(b)
    k.cyl(a, b, r, zone_side, seg, caps=False)
    for p, d in ((a, a - b), (b, b - a)):
        ring, _ = k.ring_pts(p, d, r, seg)
        face(k, ring, zone_end, d)


def uv_cyl(k, c, h0, h1, rect, axis=(0, 0, 1)):
    """cylindrical UVs for every face of k (lens lathes): u round the axis, v along it from h0 to h1; the lens tiles are
    uniform across u, so the seam needs no care (u is kept inside the rect)"""
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


def plank(k, a, b, w, t, up, zone):
    """board from a to b (centre line), width w across, thickness t along `up`"""
    k.strip([Vector(a), Vector(b)], Vector(up), w, t, zone)


# ================================================================ the hut shell
def shell():
    k = kb('TowerHut', 'Hut')
    wz = dict(out=Z_CLAD, reveal=Z_TIMBER, end=Z_CLAD, top=Z_TIMBER, **{'in': Z_LINING})
    # stone piers under the sill, a flat stepping stone at the door, the underside of the floor
    for i, (x, y) in enumerate(((X0 + 0.14, Y0 + 0.14), (X1 - 0.14, Y0 + 0.14), (X0 + 0.14, Y1 - 0.14), (X1 - 0.14, Y1 - 0.14),
                                (X0 + 0.14, 0.0), (X1 - 0.14, 0.0))):
        rock(k, (x, y, -0.03), (0.46, 0.44, 0.44), Z_STONE, 11 + i)
    rock(k, (-0.38, Y0 - 0.30, 0.03), (0.78, 0.46, 0.26), Z_STONE, 31)
    box6(k, (X0 + 0.01, Y0 + 0.01, ZB), (X1 - 0.01, Y1 - 0.01, FLOOR - 0.03), Z_TIMBER, skip=('+z',))   # sill / joists
    # floor boards (along y)
    face(k, [(IX0, IY0, FLOOR), (IX1, IY0, FLOOR), (IX1, IY1, FLOOR), (IX0, IY1, FLOOR)], Z_FLOORB, (0, 0, 1))
    # walls: front gable wall with the door, back gable wall, right wall with the window, left wall
    wall_grid(k, 'y', Y0, IY0, [X0, DOOR['x0'], DOOR['x1'], X1], [ZB, FLOOR, DOOR['z1'], ZE], {(1, 1)}, -1, wz,
              ends=True, top=False)
    wall_grid(k, 'y', IY1, Y1, [X0, X1], [ZB, ZE], set(), 1, wz, ends=True, top=False)
    wall_grid(k, 'x', IX1, X1, [IY0, WIN['y0'], WIN['y1'], IY1], [ZB, WIN['z0'], WIN['z1'], ZE], {(1, 1)}, 1, wz,
              ends=False, top=True)
    wall_grid(k, 'x', X0, IX0, [IY0, IY1], [ZB, ZE], set(), -1, wz, ends=False, top=True)
    # gables above the wall top (cladding outside, ply inside, timber under the verge rafters)
    tri = [(X0, ZE), (X1, ZE), (0.0, z_rb(0))]
    prism_y(k, tri, Y0, IY0, Z_CLAD, Z_LINING, [None, Z_TIMBER, Z_TIMBER])
    prism_y(k, tri, IY1, Y1, Z_LINING, Z_CLAD, [None, Z_TIMBER, Z_TIMBER])
    # white trims: corner boards, door jambs and head, window frame outside and its sill, the inside sill
    cb, ct = 0.14, 0.025
    for sx in (-1, 1):
        for sy in (-1, 1):
            xo, yo = (X1 if sx > 0 else X0), (Y1 if sy > 0 else Y0)
            xa, xb = sorted((xo, xo - sx * cb))
            ya, yb = sorted((yo, yo + sy * ct))
            box6(k, (xa, ya, ZB), (xb, yb, ZE), Z_TRIMW, skip=('-z',))
            xa, xb = sorted((xo, xo + sx * ct))
            ya, yb = sorted((yo + sy * ct, yo - sy * (cb - ct)))
            box6(k, (xa, ya, ZB), (xb, yb, ZE), Z_TRIMW, skip=('-z',))
    for xa, xb in ((DOOR['x0'] - 0.16, DOOR['x0'] - 0.03), (DOOR['x1'] + 0.03, DOOR['x1'] + 0.16)):
        box6(k, (xa, Y0 - 0.025, FLOOR - 0.02), (xb, Y0, DOOR['z1'] + 0.03), Z_TRIMW, skip=('+y', '-z'))
    box6(k, (DOOR['x0'] - 0.16, Y0 - 0.025, DOOR['z1'] + 0.03), (DOOR['x1'] + 0.16, Y0, DOOR['z1'] + 0.17), Z_TRIMW,
         skip=('+y',))
    y0, y1, w0, w1 = WIN['y0'], WIN['y1'], WIN['z0'], WIN['z1']
    for lo, hi in (((X1, y0 - 0.07, w1), (X1 + 0.022, y1 + 0.07, w1 + 0.07)),
                   ((X1, y0 - 0.07, w0), (X1 + 0.022, y0, w1)), ((X1, y1, w0), (X1 + 0.022, y1 + 0.07, w1))):
        box6(k, lo, hi, Z_TRIMW, skip=('-x',))
    box6(k, (X1, y0 - 0.09, w0 - 0.035), (X1 + 0.06, y1 + 0.09, w0), Z_TRIMW, skip=('-x',))           # outside sill
    box6(k, (IX1 - 0.05, y0 - 0.03, w0 - 0.03), (IX1, y1 + 0.03, w0), Z_TIMBER, skip=('+x',))          # inside sill
    roof(k)
    return k


def roof(k):
    """rafters (pairs, verge rafters at the edges), ridge board, purlins along y, ties across the room, blocking over
    the side walls; the corrugated sheet on both slopes (top / underside), its edges, the ridge cap, barge boards,
    fascia"""
    for yr in RAFTERS + [YF + RAFT_W / 2, YK - RAFT_W / 2]:
        for s in (1, -1):
            xa, xb = 0.015, XE
            poly = [(s * xa, z_rb(xa)), (s * xb, z_rb(xb)), (s * xb, z_rt(xb)), (s * xa, z_rt(xa))]
            if s < 0:
                poly = list(reversed(poly))
            prism_y(k, poly, yr - RAFT_W / 2, yr + RAFT_W / 2, Z_TIMBER, Z_TIMBER)
    box6(k, (-0.015, YF, z_rb(0) - 0.03), (0.015, YK, z_rt(0) + 0.01), Z_TIMBER)                       # ridge board
    for s in (1, -1):
        for xp in PURLINS:
            w = 0.025
            x0_, x1_ = s * (xp - w), s * (xp + w)
            poly = [(x0_, z_rt(x0_)), (x1_, z_rt(x1_)), (x1_, z_rt(x1_) + PURL / CP), (x0_, z_rt(x0_) + PURL / CP)]
            if s < 0:
                poly = list(reversed(poly))
            prism_y(k, poly, YF, YK, Z_TIMBER, Z_TIMBER)
    for yt in TIES:                                                     # ceiling ties beside two rafter pairs
        box6(k, (IX0, yt - 0.025, ZE), (IX1, yt + 0.025, ZE + 0.14), Z_TIMBER, skip=('-x', '+x'))
    ys = RAFTERS
    for s in (1, -1):                                                   # blocking between the rafters over the walls
        xa, xb = (IX1, X1) if s > 0 else (X0, IX0)
        for ya, yb in zip(ys[:-1], ys[1:]):
            box6(k, (xa, ya + RAFT_W / 2, ZE), (xb, yb - RAFT_W / 2, ZE + 0.15),
                 {('+x' if s > 0 else '-x'): Z_CLAD, '*': Z_TIMBER}, skip=('-y', '+y', '-z'))
    for s in (1, -1):                                                   # sheets
        xs = [0.0, s * XE]
        top = [Vector((xs[0], YF, z_st(0))), Vector((xs[0], YK, z_st(0))), Vector((xs[1], YK, z_st(XE))), Vector((xs[1], YF, z_st(XE)))]
        bot = [Vector((xs[0], YF, z_sb(0))), Vector((xs[0], YK, z_sb(0))), Vector((xs[1], YK, z_sb(XE))), Vector((xs[1], YF, z_sb(XE)))]
        nrm = Vector((s * SP, 0, CP))
        face(k, top, Z_ROOF, nrm)
        face(k, bot, Z_ROOFUNDER, -nrm)
        face(k, [top[3], top[2], bot[2], bot[3]], Z_GALV, (s, 0, 0))                          # eave edge
        for yv, i0, i1 in ((YF, 0, 3), (YK, 1, 2)):
            face(k, [top[i0], top[i1], bot[i1], bot[i0]], Z_GALV, (0, 1 if yv > 0 else -1, 0))
    for s in (1, -1):                                                   # ridge cap
        x0_, x1_ = 0.0, s * 0.15
        pts = [Vector((x0_, YF - 0.02, z_st(0) + 0.025)), Vector((x0_, YK + 0.02, z_st(0) + 0.025)),
               Vector((x1_, YK + 0.02, z_st(0.15) + 0.006)), Vector((x1_, YF - 0.02, z_st(0.15) + 0.006))]
        face(k, pts, Z_GALV, (s * SP, 0, CP))
        face(k, [p - Vector((0, 0, 0.004)) for p in pts], Z_GALV, (-s * SP, 0, -CP))
        face(k, [pts[3], pts[2], pts[2] - Vector((0, 0, 0.004)), pts[3] - Vector((0, 0, 0.004))], Z_GALV, (s, 0, 0))
    for yv, sgn in ((YF, -1), (YK, 1)):                                 # barge boards (white)
        ya, yb = sorted((yv, yv + sgn * 0.025))
        for s in (1, -1):
            xa, xb = 0.0, s * (XE + 0.025)
            poly = [(xa, z_st(0) + 0.02 - 0.20), (xb, z_st(XE + 0.025) + 0.02 - 0.20), (xb, z_st(XE + 0.025) + 0.02),
                    (xa, z_st(0) + 0.02)]
            if s < 0:
                poly = list(reversed(poly))
            prism_y(k, poly, ya, yb, Z_TRIMW, Z_TRIMW)
    for s in (1, -1):                                                   # fascia along the eaves
        xa, xb = sorted((s * XE, s * (XE + 0.025)))
        box6(k, (xa, YF, z_rb(XE) - 0.03), (xb, YK, z_st(XE)), Z_TRIMW, skip=('-y', '+y'))


# ================================================================ door, window, shutter
def door():
    """plank door outside the front wall on two strap hinges, white frame and Z brace outside, raw boards inside;
    opens outward (IX_HutDoor_1, the Update 3 name)"""
    D = kb('IX_HutDoor_1', 'Hut')
    xa, xb = DOOR['x0'] - 0.02, DOOR['x1'] + 0.02
    zl, zh = LEAF_ZL, LEAF_ZH
    box6(D, (xa, Y0 - 0.05, zl), (xb, Y0, zh), {'-y': Z_DOOR, '*': Z_DOORIN})
    yf0, yf1, w = Y0 - 0.07, Y0 - 0.05, 0.10
    for lo, hi in (((xa, yf0, zh - w), (xb, yf1, zh)), ((xa, yf0, zl), (xb, yf1, zl + w)),
                   ((xa, yf0, zl + w), (xa + w, yf1, zh - w)), ((xb - w, yf0, zl + w), (xb, yf1, zh - w))):
        box6(D, lo, hi, Z_TRIMW, skip=('+y',))
    D.strip([Vector((xa + w + 0.03, Y0 - 0.059, zl + w + 0.04)), Vector((xb - w - 0.03, Y0 - 0.059, zh - w - 0.04))],
            Vector((0, -1, 0)), 0.10, 0.018, Z_TRIMW)                   # brace: hinge side low -> latch side high
    piv = Vector((xa - 0.012, Y0 - 0.07, 0.0))
    for zc in (zl + 0.16, zh - 0.16):                                   # strap hinges + knuckles; pintles on the jamb
        box6(D, (xa - 0.005, Y0 - 0.076, zc - 0.022), (xa + 0.46, Y0 - 0.07, zc + 0.022), Z_STEELBLK, skip=('+y',))
        D.cyl(piv + Vector((0, 0, zc - 0.035)), piv + Vector((0, 0, zc + 0.035)), 0.011, Z_STEELBLK, 8)
        KBS['TowerHut'].box(piv.x - 0.045, piv.x - 0.012, Y0 - 0.03, Y0 - 0.025 + 0.0, zc - 0.045, zc + 0.045, Z_STEELBLK)
    # handles: iron D pull outside by the latch edge, a wooden one inside; turn-button inside on the jamb
    dx = xb - 0.09
    D.tube([Vector((dx, Y0 - 0.07, 1.02)), Vector((dx, Y0 - 0.115, 1.02)), Vector((dx, Y0 - 0.115, 1.20)), Vector((dx, Y0 - 0.07, 1.20))],
           0.010, Z_STEELBLK, 6, caps=False)
    box6(D, (dx - 0.02, Y0, 1.03), (dx + 0.02, Y0 + 0.035, 1.19), Z_TIMBER, skip=('-y',))
    part('IX_HutDoor_1', 'hinge', (piv.x, piv.y, (zl + zh) / 2), (0, 0, -1), (0, 105), parent='TowerHut',
         states=['shut', 'open'], note='plank door, opening 1.00 x 1.915 m, opens outward (+) over the porch deck (left of its '
                                       'bench); open at the start of the prologue (the hut is empty, the lantern burns); same '
                                       'name, hinge side and range as the Update 3 hut')
    socket('Hand_Door_Out', (dx, Y0 - 0.125, 1.11), 'hand', parent='IX_HutDoor_1', note='iron pull outside')
    socket('Hand_Door_In', (dx, Y0 + 0.04, 1.11), 'hand', parent='IX_HutDoor_1', note='wooden handle inside')
    k = KBS['TowerHut']
    tb = Vector((DOOR['x1'] + 0.05, IY0 + 0.0, 1.11))                   # turn-button on the inside jamb (decor)
    k.box(tb.x - 0.012, tb.x + 0.012, IY0, IY0 + 0.012, tb.z - 0.03, tb.z + 0.03, Z_TIMBER)
    k.box(tb.x - 0.012, tb.x + 0.012, IY0 + 0.012, IY0 + 0.026, tb.z - 0.075, tb.z + 0.075, Z_TIMBER)


def window():
    """the shed's window in the right wall: white frame with glazing bars, pane; board shutter inside hinged at the
    window's front edge, folded open on the wall toward the door; turn-button behind the back edge"""
    k = KBS['TowerHut']
    y0, y1, z0, z1 = WIN['y0'], WIN['y1'], WIN['z0'], WIN['z1']
    fw = 0.045
    xa, xb = IX1 + 0.02, X1 - 0.02
    for lo, hi, sk in (((xa, y0, z0), (xb, y1, z0 + fw), '-z'), ((xa, y0, z1 - fw), (xb, y1, z1), '+z'),
                       ((xa, y0, z0 + fw), (xb, y0 + fw, z1 - fw), '-y'), ((xa, y1 - fw, z0 + fw), (xb, y1, z1 - fw), '+y')):
        box6(k, lo, hi, Z_TRIMW, skip=(sk,))
    ym, zm = (y0 + y1) / 2, (z0 + z1) / 2
    xg = (xa + xb) / 2
    box6(k, (xg - 0.015, ym - 0.015, z0 + fw), (xg + 0.015, ym + 0.015, z1 - fw), Z_TRIMW, skip=('-z', '+z'))
    box6(k, (xg - 0.012, y0 + fw, zm - 0.015), (xg + 0.012, y1 - fw, zm + 0.015), Z_TRIMW, skip=('-y', '+y'))
    g = kb('Window_Glass', 'glass')
    for xx, n in ((xg - 0.0005, (-1, 0, 0)), (xg + 0.0005, (1, 0, 0))):
        face(g, [Vector((xx, y0 + fw, z0 + fw)), Vector((xx, y1 - fw, z0 + fw)), Vector((xx, y1 - fw, z1 - fw)),
                 Vector((xx, y0 + fw, z1 - fw))], ZERO, n)
    part('Window_Glass', 'static', (xg, ym, zm), parent='TowerHut', note='window pane (glass material, both faces)')
    S = kb('Window_Shutter', 'Hut')
    sy0, sy1, sz0, sz1 = y0 - 0.03, y1 + 0.03, z0 + 0.002, z1 + 0.03
    xw, xr = IX1 - 0.005, IX1 - 0.035                                   # closed: wall side / room side
    box6(S, (xr, sy0, sz0), (xw, sy1, sz1), Z_DOORIN)
    for zc in (sz0 + 0.10, sz1 - 0.10):
        box6(S, (xr - 0.02, sy0 + 0.03, zc - 0.035), (xr, sy1 - 0.03, zc + 0.035), Z_TIMBER, skip=('+x',))
    S.cyl(Vector((xr, sy1 - 0.06, (sz0 + sz1) / 2)), Vector((xr - 0.03, sy1 - 0.06, (sz0 + sz1) / 2)), 0.012, Z_TIMBER, 8)
    piv = Vector((xr, sy0, (sz0 + sz1) / 2))
    for zc in (sz0 + 0.08, sz1 - 0.08):
        S.cyl(piv + Vector((0, 0, zc - piv.z - 0.03)), piv + Vector((0, 0, zc - piv.z + 0.03)), 0.008, Z_STEELBLK, 6)
    transform_kb(S, rot_about(piv, (0, 0, 1), 180.0))                   # -> open, flat on the wall toward the door
    part('Window_Shutter', 'hinge', piv, (0, 0, -1), (0, 180), parent='TowerHut', states=['open (on the wall)', 'closed'],
         note='inside board shutter: 0 = folded open on the wall toward the door, 180 = over the window; Window_Latch holds it')
    socket('Hand_Window_Shutter', piv + Vector((-0.04, -0.60, 0.0)), 'hand', parent='Window_Shutter')
    L = kb('Window_Latch', 'Hut')
    lp = Vector((xr, sy1 + 0.05, z0 + 0.25))
    box6(k, (lp.x, lp.y - 0.012, lp.z - 0.02), (IX1, lp.y + 0.012, lp.z + 0.02), Z_TIMBER, skip=('+x',))
    L.box(lp.x - 0.016, lp.x - 0.001, lp.y - 0.012, lp.y + 0.012, lp.z - 0.08, lp.z + 0.08, Z_TIMBER)
    L.cyl(lp + Vector((-0.015, 0, 0)), lp + Vector((-0.02, 0, 0)), 0.006, Z_STEELBLK, 6)
    part('Window_Latch', 'hinge', lp, (1, 0, 0), (0, 90), parent='TowerHut', states=['free', 'holding the shutter'],
         note='turn-button on the wall behind the window: 90 = across the closed shutter edge')
    socket('Hand_Window_Latch', lp + Vector((-0.02, 0, 0.04)), 'hand', parent='Window_Latch')


# ================================================================ stove and flue
def stove():
    """cast-iron box stove in the back-right corner on short legs, galvanised heat shields on the walls and the floor,
    the flue up through the roof with a collar and a rain cap; door (Stove_Door), flue damper (Stove_Damper)"""
    k = kb('TowerHut', 'Hut')
    s = STOVE
    VM.rbox(k, ((s['x0'] + s['x1']) / 2, (s['y0'] + s['y1']) / 2, (s['z0'] + s['z1']) / 2),
            (s['x1'] - s['x0'], s['y1'] - s['y0'], s['z1'] - s['z0']), Z_STOVE, r=0.012, ch=0.006)
    k.box(s['x0'] - 0.015, s['x1'] + 0.015, s['y0'] - 0.015, s['y1'] + 0.015, s['z1'] - 0.004, s['z1'] + 0.018, Z_STOVE)   # top plate
    for xx in (s['x0'] + 0.05, s['x1'] - 0.05):
        for yy in (s['y0'] + 0.05, s['y1'] - 0.05):
            k.cyl((xx, yy, FLOOR + 0.003), (xx, yy, s['z0'] + 0.01), 0.018, Z_STOVE, 6, r2=0.026)
    k.lathe(Vector((FLUE.x, FLUE.y, s['z1'] + 0.018)), (0, 0, 1), [(0.0, 0.08), (0.03, 0.075), (0.05, FLUE_R + 0.008)], Z_STOVE, 10,
            cap0=False, cap1=False)                                     # flue spigot
    for lo, hi, sk in (((s['x0'] - 0.16, IY1 - 0.012, s['z0']), (IX1, IY1 - 0.004, 1.45), '+y'),          # heat shields
                       ((IX1 - 0.012, s['y0'] - 0.16, s['z0']), (IX1 - 0.004, IY1 - 0.012, 1.45), '+x')):
        box6(k, lo, hi, Z_GALV, skip=(sk,))
    box6(k, (s['x0'] - 0.10, s['y0'] - 0.20, FLOOR), (IX1 - 0.004, IY1 - 0.004, FLOOR + 0.003), Z_GALV, skip=('-z',))
    k.cyl(Vector((FLUE.x, FLUE.y, s['z1'] + 0.06)), Vector((FLUE.x, FLUE.y, FLUE_TOP)), FLUE_R, Z_RUSTPIPE, 10, caps=False)
    zr = z_st(FLUE.x)                                                    # collar on the roof, rain cap
    k.lathe(Vector((FLUE.x, FLUE.y, zr - 0.02)), (0, 0, 1), [(0.0, 0.16), (0.10, FLUE_R + 0.012), (0.14, FLUE_R + 0.008)], Z_GALV, 10,
            cap0=False, cap1=False)
    k.lathe(Vector((FLUE.x, FLUE.y, FLUE_TOP + 0.05)), (0, 0, 1), [(0.0, 0.14), (0.07, 0.01)], Z_GALV, 10, cap0=True, cap1=False)
    for a in (0, 120, 240):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        k.box_m(Vector((FLUE.x, FLUE.y, FLUE_TOP + 0.03)) + d * (FLUE_R + 0.004), (0.006, 0.006, 0.07), Z_GALV)
    # door on the front face (hinge at its left edge), the firebox behind it, an ash slot under it
    Dd = kb('Stove_Door', 'Hut')
    dx0, dx1, dz0, dz1 = s['x0'] + 0.06, s['x1'] - 0.06, s['z0'] + 0.13, s['z0'] + 0.40
    yd = s['y0'] - 0.002
    Dd.box(dx0, dx1, yd - 0.014, yd, dz0, dz1, Z_STOVE)
    Dd.box(dx0 + 0.03, dx1 - 0.03, yd - 0.020, yd - 0.014, dz0 + 0.03, dz1 - 0.03, Z_STOVE)
    for i in range(3):                                                  # draught slots
        zz = dz0 + 0.06 + i * 0.03
        Dd.box(dx0 + 0.10, dx1 - 0.10, yd - 0.022, yd - 0.019, zz, zz + 0.012, Z_STEELBLK)
    Dd.cyl(Vector((dx1 - 0.03, yd - 0.022, (dz0 + dz1) / 2)), Vector((dx1 - 0.03, yd - 0.07, (dz0 + dz1) / 2)), 0.007, Z_STEELBLK, 6)
    Dd.cyl(Vector((dx1 - 0.03, yd - 0.07, (dz0 + dz1) / 2 - 0.03)), Vector((dx1 - 0.03, yd - 0.07, (dz0 + dz1) / 2 + 0.03)), 0.008,
           Z_STEELBLK, 6)
    pd = Vector((dx0 - 0.010, yd - 0.008, (dz0 + dz1) / 2))
    for zc in (dz0 + 0.04, dz1 - 0.04):
        k.cyl(Vector((pd.x, pd.y, zc - 0.02)), Vector((pd.x, pd.y, zc + 0.02)), 0.008, Z_STOVE, 6)
    part('Stove_Door', 'hinge', pd, (0, 0, -1), (0, 110), parent='TowerHut', states=['shut', 'open'],
         note='fire door: open (+) to lay wood and light it (Slot_Stove_Fire); fire glow through the slots when lit')
    socket('Hand_Stove_Door', Vector((dx1 - 0.03, yd - 0.08, (dz0 + dz1) / 2)), 'hand', parent='Stove_Door')
    socket('Slot_Stove_Fire', Vector(((s['x0'] + s['x1']) / 2, (s['y0'] + s['y1']) / 2, s['z0'] + 0.18)), 'item_slot', parent='TowerHut',
           note='firewood and kindling go in here (door open)')
    k.box(dx0 + 0.02, dx1 - 0.02, yd - 0.004, yd, s['z0'] + 0.03, s['z0'] + 0.09, Z_STEELBLK)          # ash slot
    Dm = kb('Stove_Damper', 'Hut')                                      # damper handle on the flue
    zd = 1.42
    Dm.cyl(Vector((FLUE.x - FLUE_R - 0.004, FLUE.y, zd)), Vector((FLUE.x - FLUE_R - 0.07, FLUE.y, zd)), 0.006, Z_STEELBLK, 6)
    Dm.box(FLUE.x - FLUE_R - 0.10, FLUE.x - FLUE_R - 0.06, FLUE.y - 0.003, FLUE.y + 0.003, zd - 0.022, zd + 0.022, Z_STEELBLK)
    part('Stove_Damper', 'hinge', (FLUE.x, FLUE.y, zd), (-1, 0, 0), (0, 90), parent='TowerHut', states=['open', 'shut'],
         note='flue damper: 0 = open (the flat grip upright, in line with the pipe), 90 = shut (grip across: the fire '
              'chokes, smoke comes into the room)')
    socket('Hand_Stove_Damper', (FLUE.x - FLUE_R - 0.085, FLUE.y, zd), 'hand', parent='Stove_Damper')


# ================================================================ furniture
def furniture():
    k = kb('TowerHut', 'Hut')
    # bunk: four posts, rails, board base, mattress, blanket folded over the foot, pillow at the left end
    b = BUNK
    for xx in (b['x0'] + 0.03, b['x1'] - 0.03):
        for yy in (b['y0'] + 0.03, b['y1'] - 0.03):
            box6(k, (xx - 0.03, yy - 0.03, FLOOR), (xx + 0.03, yy + 0.03, 0.70), Z_FURN, skip=('-z',))
    for yy in (b['y0'], b['y1'] - 0.025):                               # side rails between the posts
        box6(k, (b['x0'] + 0.06, yy, 0.50), (b['x1'] - 0.06, yy + 0.025, 0.63), Z_FURN)
    for xx in (b['x0'] + 0.01, b['x1'] - 0.035):                        # end rails between the posts
        box6(k, (xx, b['y0'] + 0.06, 0.50), (xx + 0.025, b['y1'] - 0.06, 0.63), Z_FURN)
    k.box(b['x0'] + 0.06, b['x1'] - 0.06, b['y0'] + 0.025, b['y1'] - 0.025, 0.600, 0.620, Z_FURN)   # boards inside the frame
    VM.rbox(k, ((b['x0'] + b['x1']) / 2, (b['y0'] + b['y1']) / 2, (b['base'] + b['top']) / 2),
            (b['x1'] - b['x0'] - 0.10, b['y1'] - b['y0'] - 0.07, b['top'] - b['base']), Z_MATTRESS, r=0.03, ch=0.02, axis='x')
    bx0 = -0.30                                                          # blanket from here to the foot, over the front edge
    VM.rbox(k, ((bx0 + b['x1'] - 0.03) / 2, (b['y0'] + b['y1']) / 2 - 0.01, b['top'] + 0.018),
            (b['x1'] - 0.03 - bx0, b['y1'] - b['y0'] - 0.03, 0.036), Z_BLANKET, r=0.012, ch=0.008, axis='x')
    k.box(bx0 + 0.03, b['x1'] - 0.06, b['y0'] - 0.012, b['y0'] + 0.002, 0.56, b['top'] + 0.03, Z_BLANKET)   # hanging over the edge
    VM.rbox(k, (b['x0'] + 0.26, (b['y0'] + b['y1']) / 2, b['top'] + 0.05), (0.32, 0.50, 0.10), Z_PILLOW, r=0.04, ch=0.03, axis='y')
    # table under the window: top, apron, four legs, a drawer front
    t = TABLE
    VM.rbox(k, ((t['x0'] + t['x1']) / 2, (t['y0'] + t['y1']) / 2, t['top'] - 0.02), (t['x1'] - t['x0'], t['y1'] - t['y0'], 0.04),
            Z_FURN, r=0.01, ch=0.006)
    for xx in (t['x0'] + 0.04, t['x1'] - 0.04):
        for yy in (t['y0'] + 0.04, t['y1'] - 0.04):
            box6(k, (xx - 0.025, yy - 0.025, FLOOR), (xx + 0.025, yy + 0.025, t['top'] - 0.04), Z_FURN, skip=('-z', '+z'))
    for lo, hi in (((t['x0'] + 0.065, t['y0'] + 0.03, t['top'] - 0.14), (t['x1'] - 0.065, t['y0'] + 0.05, t['top'] - 0.04)),
                   ((t['x0'] + 0.065, t['y1'] - 0.05, t['top'] - 0.14), (t['x1'] - 0.065, t['y1'] - 0.03, t['top'] - 0.04)),
                   ((t['x0'] + 0.03, t['y0'] + 0.065, t['top'] - 0.14), (t['x0'] + 0.05, t['y1'] - 0.065, t['top'] - 0.04))):
        box6(k, lo, hi, Z_FURN, skip=('+z',))
    k.box(t['x0'] + 0.025, t['x0'] + 0.03, -0.48, -0.12, t['top'] - 0.13, t['top'] - 0.05, Z_FURN)         # drawer front
    k.cyl(Vector((t['x0'] + 0.025, -0.30, t['top'] - 0.09)), Vector((t['x0'] + 0.005, -0.30, t['top'] - 0.09)), 0.012, Z_FURN, 6)
    # stool
    sc = Vector((0.30, -0.10, 0.0))
    k.lathe(Vector((sc.x, sc.y, 0.755)), (0, 0, 1), [(0.0, 0.155), (0.035, 0.16), (0.045, 0.15)], Z_FURN, 10, cap0=True, cap1=True)
    for a in (90, 210, 330):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        k.cyl(sc + d * 0.15 + Vector((0, 0, FLOOR)), sc + d * 0.09 + Vector((0, 0, 0.76)), 0.018, Z_FURN, 6)
    # two shelves on iron brackets (left wall); the lower one carries the funnel spot, the jerrycan stands under it
    sh = SHELF
    for top in sh['tops']:
        box6(k, (sh['x0'], sh['y0'], top - 0.025), (sh['x1'], sh['y1'], top), Z_TIMBER, skip=('-x',))
        for yb in (sh['y0'] + 0.12, sh['y1'] - 0.12):
            k.box(IX0, IX0 + 0.004, yb - 0.012, yb + 0.012, top - 0.25, top - 0.025, Z_STEELBLK)
            k.strip([Vector((IX0 + 0.004, yb, top - 0.24)), Vector((sh['x1'] - 0.03, yb, top - 0.03))], Vector((0, 1, 0)), 0.006, 0.02,
                    Z_STEELBLK)
            k.box(IX0 + 0.004, sh['x1'] - 0.02, yb - 0.010, yb + 0.010, top - 0.035, top - 0.025, Z_STEELBLK)
    # coat hooks on the front wall inside, right of the door
    k.box(0.28, 0.98, IY0, IY0 + 0.02, 1.70, 1.80, Z_TIMBER)
    for xx in (0.38, 0.62, 0.86):
        k.tube([Vector((xx, IY0 + 0.02, 1.75)), Vector((xx, IY0 + 0.07, 1.75)), Vector((xx, IY0 + 0.085, 1.79))], 0.006, Z_STEELBLK, 5)


# ================================================================ small things (HutProps atlas)
def props_inside():
    P = kb('Hut_Props', 'HutProps')
    # lower shelf: two tins and a jar; upper shelf: the olive box, a bottle, a tin, a coil of rope (the funnel spot free)
    lo, up = SHELF['tops']
    for y, h in ((-0.70, 0.11), (-0.58, 0.11)):
        P.lathe(Vector((-1.08, y, lo)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.042), (h, 0.042), (h, 0.0)], Z_TIN, 10)
    P.lathe(Vector((-1.06, 0.14, lo)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.045), (0.12, 0.045), (0.13, 0.035), (0.15, 0.036), (0.15, 0.0)],
            Z_GLASSJ, 10)
    VM.rbox(P, (-1.07, -0.62, up + 0.075), (0.24, 0.30, 0.15), Z_CARDBOARD, r=0.006, ch=0.004)
    P.lathe(Vector((-1.10, -0.30, up)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.035), (0.17, 0.035), (0.21, 0.013), (0.25, 0.013), (0.25, 0.0)],
            Z_BOTTLE, 8)
    P.lathe(Vector((-1.05, -0.15, up)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.05), (0.09, 0.05), (0.09, 0.0)], Z_TIN, 10)
    for i in range(3):                                                  # rope coil lying flat
        P.lathe(Vector((-1.05, 0.08, up + 0.012 + i * 0.022)), (0, 0, 1), [(0.0, 0.10), (0.02, 0.10)], Z_ROPE, 12, cap0=False, cap1=False)
        P.lathe(Vector((-1.05, 0.08, up + 0.012 + i * 0.022)), (0, 0, 1), [(0.0, 0.07), (0.02, 0.07)], Z_ROPE, 12, cap0=False, cap1=False)
    # table: candle in an enamel holder, a mug (the flashlight and the note are the prologue's items)
    P.lathe(CANDLE, (0, 0, 1), [(0.0, 0.06), (0.012, 0.06), (0.014, 0.018), (0.04, 0.016)], Z_ENAMELW, 10)
    P.cyl(CANDLE + Vector((0, 0, 0.04)), CANDLE + Vector((0, 0, 0.11)), 0.011, Z_CANDLE, 8)
    P.lathe(MUG, (0, 0, 1), [(0.0, 0.0), (0.0, 0.040), (0.09, 0.042), (0.09, 0.0)], Z_ENAMELW, 10)
    P.tube([MUG + Vector((0.04, 0, 0.07)), MUG + Vector((0.075, 0, 0.06)), MUG + Vector((0.075, 0, 0.03)), MUG + Vector((0.04, 0, 0.02))],
           0.006, Z_ENAMELW, 5, caps=False)
    # jacket on a hook (orange forestry jacket), a hat; boots by the door
    jx, jy = 0.62, IY0 + 0.075
    VM.rbox(P, (jx, jy, 1.31), (0.40, 0.09, 0.44), Z_JACKET, r=0.035, ch=0.02, axis='z')            # body
    P.loft([[Vector((jx + u * w, jy + v * d, z)) for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            for z, w, d in ((1.53, 0.20, 0.045), (1.62, 0.18, 0.042), (1.70, 0.09, 0.035), (1.75, 0.05, 0.025))],
           [Z_JACKET] * 3, cap1=Z_JACKET)                                                         # shoulders up to the hook
    for sx in (-1, 1):                                                                           # sleeves, cuffs turned in
        P.strip([Vector((jx + sx * 0.185, jy + 0.012, 1.62)), Vector((jx + sx * 0.215, jy + 0.022, 1.38)),
                 Vector((jx + sx * 0.20, jy + 0.03, 1.13))], Vector((0, 1, 0)), 0.085, 0.075, Z_JACKET)
    VM.rbox(P, (jx, jy + 0.04, 1.66), (0.22, 0.05, 0.10), Z_JACKET, r=0.025, ch=0.015, axis='y')  # hood folded at the collar
    P.lathe(Vector((0.38, IY0 + 0.145, 1.69)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.13), (0.015, 0.13), (0.02, 0.085), (0.10, 0.08), (0.11, 0.0)],
            Z_JACKET, 10)
    for bx in (0.22, 0.36):
        VM.rbox(P, (bx, -0.80, FLOOR + 0.20), (0.10, 0.13, 0.30), Z_RUBBER, r=0.03, ch=0.02)
        VM.rbox(P, (bx, -0.86, FLOOR + 0.045), (0.105, 0.28, 0.09), Z_RUBBER, r=0.03, ch=0.02, axis='y')
    # kettle on the stove (an item, its own object), firewood by the stove
    kk = kb('Kettle', 'HutProps')
    kc = Vector((1.00, 0.80, STOVE['z1'] + 0.018))
    kk.lathe(kc, (0, 0, 1), [(0.0, 0.0), (0.0, 0.09), (0.03, 0.10), (0.10, 0.095), (0.14, 0.06), (0.15, 0.025), (0.165, 0.025),
                             (0.17, 0.0)], Z_ENAMELW, 12)
    kk.tube([kc + Vector((-0.08, 0, 0.06)), kc + Vector((-0.15, 0, 0.11)), kc + Vector((-0.17, 0, 0.14))], 0.016, Z_ENAMELW, 6)
    kk.tube([kc + Vector((-0.05, 0, 0.15)), kc + Vector((-0.03, 0, 0.24)), kc + Vector((0.03, 0, 0.24)), kc + Vector((0.05, 0, 0.15))],
            0.004, Z_WIREP, 5, caps=False)
    part('Kettle', 'item', kc, (0, 0, 1), parent='TowerHut', states=['on the stove', 'carried'],
         note='enamel kettle (1.5 l): fill at the rain barrel, boil on the stove')
    socket('Hand_Kettle', kc + Vector((0, 0, 0.24)), 'hand', parent='Kettle')
    k = KBS['TowerHut']
    for x_, z_ in ((0.30, 0.045), (0.40, 0.045), (0.50, 0.045), (0.35, 0.13), (0.45, 0.13)):    # firewood under the bunk's foot
        log(k, (x_, 0.50, FLOOR + z_), (x_, 0.94, FLOOR + z_), 0.044, Z_BARK, Z_LOGEND, 7)


def map_and_calendar():
    S = kb('Hut_Panel', 'panel')
    quad(S, ((-0.70 + 0.48) / 2, IY1 - 0.003, (1.54 + 2.30) / 2), (0, -1, 0), 1.18, 0.76, uv('map'))
    quad(S, (-1.00, IY1 - 0.003, 1.80), (0, -1, 0), 0.26, 0.36, uv('calendar'))
    part('Hut_Panel', 'static', (0, IY1, 1.9), parent='TowerHut',
         note='area map with the observatory circled (back wall over the bunk) and the October calendar, days crossed '
              'out to the 16th (panel atlas)')
    k = KBS['TowerHut']
    for x, z in ((-0.68, 2.28), (0.46, 2.28), (-0.68, 1.56), (0.46, 1.56), (-1.00, 1.985)):     # drawing pins / nail
        k.cyl(Vector((x + 0.0, IY1 - 0.004, z)), Vector((x, IY1 - 0.012, z)), 0.007, Z_STEELBLK, 6)


# ================================================================ lamps: the storm lantern outside, the oil lamp inside
def lantern():
    """storm lantern hanging from an iron bracket right of the door: bail, cap, chimney tubes, wire guard, globe, tank"""
    k = KBS['TowerHut']
    c = LANTERN
    bx = c.x
    k.box(bx - 0.03, bx + 0.03, Y0 - 0.008, Y0, HOOK_Z - 0.07, HOOK_Z + 0.05, Z_STEELBLK)                  # wall plate
    k.strip([Vector((bx, Y0 - 0.008, HOOK_Z)), Vector((bx, c.y + 0.0, HOOK_Z))], Vector((0, 0, 1)), 0.012, 0.012, Z_STEELBLK)
    k.strip([Vector((bx, Y0 - 0.008, HOOK_Z - 0.06)), Vector((bx, c.y + 0.10, HOOK_Z))], Vector((1, 0, 0)), 0.010, 0.010, Z_STEELBLK)
    k.tube([Vector((bx, c.y, HOOK_Z)), Vector((bx, c.y, HOOK_Z - 0.025)), Vector((bx, c.y + 0.012, HOOK_Z - 0.035))], 0.004, Z_STEELBLK, 5)
    P = kb('Lantern', 'HutProps')
    top = HOOK_Z - 0.035
    P.tube([Vector((bx - 0.075, c.y, c.z + 0.05)), Vector((bx - 0.06, c.y, top - 0.03)), Vector((bx, c.y, top)),
            Vector((bx + 0.06, c.y, top - 0.03)), Vector((bx + 0.075, c.y, c.z + 0.05))], 0.003, Z_WIREP, 4, caps=False)
    P.lathe(Vector((bx, c.y, c.z + 0.07)), (0, 0, 1), [(0.0, 0.055), (0.025, 0.05), (0.05, 0.02), (0.07, 0.015)], Z_LANTERN, 10)   # cap
    P.lathe(Vector((bx, c.y, c.z - 0.08)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.07), (0.045, 0.075), (0.06, 0.05), (0.07, 0.042)], Z_LANTERN, 12)  # tank
    for sx in (-1, 1):                                                  # the side tubes (air) and the frame
        P.cyl(Vector((bx + sx * 0.07, c.y, c.z - 0.02)), Vector((bx + sx * 0.055, c.y, c.z + 0.08)), 0.008, Z_LANTERN, 6)
    for a in range(0, 360, 90):                                          # wire guard over the globe
        d = Vector((math.cos(math.radians(a + 45)), math.sin(math.radians(a + 45)), 0))
        P.cyl(Vector((bx, c.y, c.z)) + d * 0.052 + Vector((0, 0, -0.055)), Vector((bx, c.y, c.z)) + d * 0.052 + Vector((0, 0, 0.065)), 0.0025,
              Z_WIREP, 4)
    part('Lantern', 'static', (bx, c.y, top), parent='TowerHut',
         note='storm lantern (kerosene) on its hook right of the door: burns at the start (seen from the car between the trees, '
              '92 m); goes out for good when Jerrycan_Hut is picked up (X01)')
    G = kb('Lens_Lantern', 'lens:lantern')
    g0 = Vector((bx, c.y, c.z - 0.055))
    G.lathe(g0, (0, 0, 1), [(0.0, 0.03), (0.03, 0.048), (0.07, 0.048), (0.11, 0.032), (0.12, 0.028)], ZERO, 12, cap0=False, cap1=False)
    uv_cyl(G, g0, 0.0, 0.12, uv('l_lantern'))
    part('Lens_Lantern', 'static', (bx, c.y, c.z), parent='Lantern',
         note='glass globe of the storm lantern: M_Hut_Lamp_Lantern while it burns, M_Hut_Lamp_Lantern_Off after X01')
    Gw = kb('Glow_Lantern', 'glow')
    for a in (0, 60, 120):
        n = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        quad(Gw, c, n, 0.56, 0.56, uv('glow'))
        quad(Gw, c, -n, 0.56, 0.56, uv('glow'))
    part('Glow_Lantern', 'static', c, parent='Lantern',
         note='halo cards round the flame (three crossed quads): additive, unlit, no shadows (as M_Glow_Lantern in U3); '
              'hidden when the lantern goes out (X01)')
    LAMPS.append(('Lantern', c, (0, 0, -1), 'stormlantern', (0, -1, 0)))
    # the oil lamp inside, hanging from the ridge board on a chain; off at the start
    O = kb('Lamp_Oil', 'HutProps')
    oc = Vector((0.0, 0.0, 2.36))
    O.lathe(oc + Vector((0, 0, -0.12)), (0, 0, 1), [(0.0, 0.0), (0.0, 0.05), (0.03, 0.065), (0.06, 0.06), (0.08, 0.025), (0.09, 0.02)],
            Z_BRASS, 12)                                                # font
    O.lathe(oc + Vector((0, 0, 0.12)), (0, 0, 1), [(0.0, 0.16), (0.02, 0.15), (0.07, 0.04), (0.08, 0.02)], Z_ENAMELW, 14, cap0=False)  # shade
    for a in (0, 120, 240):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        O.cyl(oc + d * 0.15 + Vector((0, 0, 0.12)), oc + Vector((0, 0, 0.30)), 0.0025, Z_BRASS, 4)
    O.cyl(oc + Vector((0, 0, 0.30)), Vector((0, 0, z_rb(0) - 0.03)), 0.004, Z_BRASS, 4)
    part('Lamp_Oil', 'static', oc, parent='TowerHut', note='kerosene lamp under the ridge, off at the start (LIGHT_OilLamp, group hut)')
    G2 = kb('Lens_OilLamp', 'lens:oillamp')
    G2.lathe(oc + Vector((0, 0, -0.03)), (0, 0, 1), [(0.0, 0.022), (0.04, 0.036), (0.08, 0.022), (0.13, 0.02)], ZERO, 10, cap0=False, cap1=False)
    uv_cyl(G2, oc + Vector((0, 0, -0.03)), 0.0, 0.13, uv('l_oillamp'))
    part('Lens_OilLamp', 'static', oc, parent='Lamp_Oil', note='glass chimney of the oil lamp (glows with LIGHT_OilLamp)')
    LAMPS.append(('OilLamp', oc + Vector((0, 0, 0.02)), (0, 0, -1), 'oillamp', (0, -1, 0)))


# ================================================================ outside things
def outside():
    k = KBS['TowerHut']
    # woodpile under the left eave: split logs along x, end grain out, bark on top; two bearer poles; loose logs on top
    wx0, wx1, wy0, wy1, wz1 = X0 - 0.46, X0 - 0.04, -0.95, 0.55, 1.08
    log(k, (wx0 + 0.02, wy0 + 0.05, 0.06), (wx0 + 0.02, wy1 - 0.05, 0.06), 0.05, Z_BARK, Z_LOGEND, 7)
    log(k, (wx1 - 0.06, wy0 + 0.05, 0.06), (wx1 - 0.06, wy1 - 0.05, 0.06), 0.05, Z_BARK, Z_LOGEND, 7)
    box6(k, (wx0, wy0, 0.10), (wx1, wy1, wz1), {'-x': Z_LOGEND, '+x': Z_LOGEND, '*': Z_BARK}, skip=('-z', '+x'))
    for i, (y, z) in enumerate(((-0.6, wz1 + 0.05), (-0.25, wz1 + 0.05), (0.15, wz1 + 0.05), (-0.42, wz1 + 0.14))):
        log(k, (wx0 + 0.02, y, z), (wx1 - 0.02, y + 0.03 * (i % 2), z), 0.05, Z_BARK, Z_LOGEND, 7)
    for y in (wy0 - 0.03, wy1 + 0.03):                                  # end stakes
        log(k, (wx0 + 0.05, y, -0.15), (wx0 + 0.05, y, wz1 + 0.10), 0.035, Z_BARK, Z_LOGEND, 6)
    # rain barrel at the back-left corner on two stones, under the eave
    bc = Vector((-1.66, 1.40, 0.10))
    rock(k, (bc.x - 0.12, bc.y, 0.03), (0.24, 0.42, 0.16), Z_STONE, 41)
    rock(k, (bc.x + 0.12, bc.y, 0.03), (0.24, 0.42, 0.16), Z_STONE, 42)
    k.lathe(bc, (0, 0, 1), [(0.0, 0.0), (0.0, 0.25), (0.35, 0.29), (0.70, 0.25), (0.70, 0.235)], Z_STAVES, 14, cap0=True, cap1=False)
    k.lathe(bc + Vector((0, 0, 0.70)), (0, 0, -1), [(0.0, 0.235), (0.05, 0.24), (0.66, 0.235)], Z_STAVES, 14, cap0=False, cap1=False)
    for zh in (0.06, 0.24, 0.46, 0.64):
        rr = 0.25 + 0.04 * math.sin(math.pi * zh / 0.70)
        k.lathe(bc + Vector((0, 0, zh)), (0, 0, 1), [(0.0, rr + 0.004), (0.03, rr + 0.004)], Z_STEELBLK, 14, cap0=False, cap1=False)
    k.lathe(bc + Vector((0, 0, 0.62)), (0, 0, 1), [(0.0, 0.245), (0.0, 0.0)], Z_WATER, 14, cap0=False, cap1=False)
    socket('Pour_Barrel', bc + Vector((0, 0, 0.66)), 'pour', parent='TowerHut', note='rain water: fill the kettle or a can here')
    # chopping block with the axe in it, chips, two split logs: at the front-left corner, clear of the porch (forest_hut_yard)
    cb = CHOP_C
    log(k, cb + Vector((0, 0, -0.02)), cb + Vector((0, 0, 0.45)), 0.22, Z_BARK, Z_LOGEND, 10)
    A = kb('Axe', 'HutProps')
    ap = cb + Vector((0.04, -0.02, 0.45))
    R = VM.frame_R(Vector((0.15, 0.55, 0.82)).normalized(), Vector((1, 0, 0)))
    A.box_m(ap + R @ Vector((0, 0, 0.03)), (0.11, 0.022, 0.10), Z_AXEHEAD, R)
    A.box_m(ap + R @ Vector((0, 0, 0.09)), (0.05, 0.034, 0.04), Z_AXEHEAD, R)
    A.cyl(ap + R @ Vector((0, 0, 0.08)), ap + R @ Vector((0, 0, 0.72)), 0.017, Z_HANDLE, 6)
    part('Axe', 'item', ap, (0, 0, 1), parent='TowerHut', states=['in the block', 'carried'],
         note='axe stuck in the chopping block: pull it out (hold), split wood with it; no weapon use')
    socket('Hand_Axe', ap + R @ Vector((0, 0, 0.62)), 'hand', parent='Axe')
    for i, (p, q) in enumerate((((-0.42, 0.22), (-0.30, 0.55)), ((-0.40, -0.25), (-0.20, -0.57)))):   # on the far side
        log(k, cb + Vector((p[0], p[1], 0.06)), cb + Vector((q[0], q[1], 0.06)), 0.06, Z_BARK, Z_LOGEND, 6)
    rng = np.random.default_rng(5)
    for i in range(14):                                                  # wood chips (none toward the porch)
        d = Vector((rng.normal() * 0.35, rng.normal() * 0.30, 0.004))
        if cb.x + d.x > -1.45:
            d.x = -abs(d.x)
        p = cb + d
        a = rng.random() * math.pi
        R2 = VM.frame_R(Vector((math.cos(a), math.sin(a), 0)), Vector((0, 0, 1)))
        k.box_m(p, (0.06 + 0.04 * rng.random(), 0.025, 0.008), Z_LOGEND, R2)
    # bench: a weathered board on two stumps, along the right wall under the window (the porch has its own by the door)
    for yy in (-0.29, 0.29):
        log(k, (BENCH_C.x, yy, 0.0), (BENCH_C.x, yy, 0.40), 0.10, Z_BARK, Z_LOGEND, 8)
    VM.rbox(k, (BENCH_C.x, BENCH_C.y, 0.42), (0.26, 0.86, 0.045), Z_WEATHERED, r=0.006, ch=0.004)
    # roof ladder on the right side, resting on the eave edge of the roof sheet (by the stove pipe's slope), 0.8 m above it
    E = Vector((XE, LADDER_Y, z_st(XE)))
    dv = Vector((-math.cos(math.radians(75)), 0.0, math.sin(math.radians(75))))
    C = E + Vector((dv.z, 0.0, -dv.x)) * 0.03
    la, lb = C - dv * (C.z / dv.z), C + dv * 0.80
    side = Vector((0, 1, 0))
    for s_ in (-1, 1):
        k.strip([la + side * s_ * 0.19, lb + side * s_ * 0.19], dv.cross(side).normalized(), 0.05, 0.03, Z_WEATHERED)
    L_ = (lb - la).length
    for i in range(1, int(L_ / 0.28) + 1):
        p = la + dv * (i * 0.28)
        k.cyl(p - side * 0.19, p + side * 0.19, 0.016, Z_WEATHERED, 6)
    socket('Ladder_Roof_Bottom', la, 'climb', parent='TowerHut', note='roof ladder foot (right side, by the window)')
    socket('Ladder_Roof_Top', C, 'climb', parent='TowerHut', note='step onto the roof here (the stove pipe, snow)')
    # antlers on a small shield on the front gable: v1.1 under the ridge, 0.85 of the 1.0 size, clear of the porch roof
    # (forest_hut_yard: its sheet meets the gable at 2.62) and of the purlins in the verge overhang
    an = kb('Hut_Props', 'HutProps')
    ac, sa = ANTLER_C, ANTLER_S
    VM.rbox(an, ac + Vector((0, 0.008, 0)), (0.20 * sa, 0.018, 0.24 * sa), Z_SHIELD, r=0.02 * sa, ch=0.006, axis='y')
    for s in (-1, 1):
        base = ac + Vector((s * 0.03, -0.02, 0.06)) * sa
        beam = [base] + [base + Vector(d) * sa for d in ((s * 0.10, -0.06, 0.10), (s * 0.20, -0.08, 0.22), (s * 0.22, -0.06, 0.36))]
        an.tube(beam, 0.012 * sa, Z_ANTLER, 5)
        for t, d in ((1, (s * 0.07, -0.08, 0.04)), (2, (s * -0.02, -0.06, 0.10)), (3, (s * 0.06, -0.02, 0.08))):
            an.tube([beam[t], beam[t] + Vector(d) * sa], 0.007 * sa, Z_ANTLER, 4)
    part('Hut_Props', 'static', (0, 0, 0), parent='TowerHut',
         note='small things: tins, jar, box, bottle, rope (shelves), candle, mug (table), jacket and hat (hooks), boots, antlers')


# ================================================================ the FORSTHÜTTE sign and the hunting stand
def sign():
    """sign board on two posts at the path, its text from the panel atlas; built in its own frame, then placed (the
    object keeps the yaw as its rotation: hut_build turns the mesh back)"""
    S = kb('Sign_Forsthuette', 'Hut')
    for xx in (-0.44, 0.44):
        log(S, (xx, 0.02, -0.30), (xx, 0.02, 1.80), 0.045, Z_LOG, Z_LOGEND, 7)
    VM.rbox(S, (0.0, 0.0, 1.55), (1.06, 0.035, 0.34), Z_SIGN, r=0.01, ch=0.006, axis='y')
    S.box(-0.55, 0.55, -0.02, 0.03, 1.73, 1.76, Z_WEATHERED)                       # little roof board
    Tq = kb('Sign_Forsthuette_Text', 'panel')
    quad(Tq, (0.0, -0.019, 1.55), (0, -1, 0), 1.00, 0.28, uv('sign'))
    pos, yaw = SIGN_PLACE
    M = Matrix.Translation(pos) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
    transform_kb(S, M)
    transform_kb(Tq, M)
    part('Sign_Forsthuette', 'static', pos, parent=None, yaw=yaw,
         note='FORSTHÜTTE / FORESTER\'S HUT sign at the path (separate root: the map\'s Sign_Forsthuette prefab, same place)')
    part('Sign_Forsthuette_Text', 'static', M @ Vector((0, -0.019, 1.55)), parent='Sign_Forsthuette', yaw=yaw,
         note='sign face (panel atlas)')


HS = dict(zp=3.80, cz0=3.84, slot=(0.95, 1.35), door=(0.32, 1.60), rz0=5.65, rz1=6.00, ry0=-1.10, ry1=1.30)


def hs_roof_z(y):
    return HS['rz0'] + (HS['rz1'] - HS['rz0']) * (y - HS['ry0']) / (HS['ry1'] - HS['ry0'])


def hochsitz():
    """hunting stand (Kanzel): four peeled poles splayed on stones, X braces, platform at 3.8 m, a closed boarded cabin
    with a viewing slot on three sides and the door on the ladder side (-y), a board roof under tar paper rising to the
    view side (+y), the ladder; built in its own frame, then placed (the object keeps the yaw as its rotation)"""
    H = kb('Hochsitz', 'Hut')
    zp, cz0 = HS['zp'], HS['cz0']
    s0, s1 = cz0 + HS['slot'][0], cz0 + HS['slot'][1]
    for sx in (-1, 1):                                                  # legs, up to the roof as the corner posts
        for sy in (-1, 1):
            a = Vector((sx * 1.27, sy * 1.27, -0.20))
            b = Vector((sx * 0.935, sy * 0.935, hs_roof_z(sy * 0.935) - 0.01))
            log(H, a, b, 0.075, Z_HS_LOG, Z_HS_END, 8)
    for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):                   # X braces on each side
        for zz0, zz1 in ((0.40, 3.40), (3.40, 0.40)):
            def pt(t, z):
                f = (z + 0.20) / (hs_roof_z(0.0) + 0.20)
                r = 1.27 - (1.27 - 0.935) * f
                return Vector((sx * r if sx else t * r, sy * r if sy else t * r, z))
            H.cyl(pt(-1, zz0), pt(1, zz1), 0.04, Z_HS_WOOD, 6)
    for sx in (-1, 1):                                                  # ring beam, platform
        H.box(-1.02, 1.02, sx * 0.96 - 0.04, sx * 0.96 + 0.04, zp - 0.12, zp - 0.02, Z_HS_WOOD)
        H.box(sx * 0.96 - 0.04, sx * 0.96 + 0.04, -1.02, 1.02, zp - 0.22, zp - 0.12, Z_HS_WOOD)    # carries the x beams
    H.box(-1.00, 1.00, -1.00, 1.00, zp - 0.02, cz0, Z_HS_WOOD)
    # side walls (x): below the slot, the post beside the slot at the door end, above the slot to the roof
    for sx in (-1, 1):
        xa, xb = sorted((sx * 0.92, sx * 0.95))
        H.box(xa, xb, -0.95, 0.95, cz0, s0, Z_HS_BOARD)
        H.box(xa, xb, -0.95, -0.60, s0, s1, Z_HS_BOARD)
        prism_x(H, [(-0.95, s1), (0.95, s1), (0.95, hs_roof_z(0.95)), (-0.95, hs_roof_z(-0.95))], xa, xb, Z_HS_BOARD, Z_HS_BOARD,
                [Z_HS_BOARD] * 4)
    # view wall (+y): below and above the slot
    H.box(-0.92, 0.92, 0.92, 0.95, cz0, s0, Z_HS_BOARD)
    H.box(-0.92, 0.92, 0.92, 0.95, s1, hs_roof_z(0.95), Z_HS_BOARD)
    # door wall (-y): beside the door, the lintel
    dw, dh = HS['door']
    for xa, xb in ((-0.92, -dw), (dw, 0.92)):
        H.box(xa, xb, -0.95, -0.92, cz0, hs_roof_z(-0.95), Z_HS_BOARD)
    H.box(-dw, dw, -0.95, -0.92, cz0 + dh, hs_roof_z(-0.95), Z_HS_BOARD)
    H.box(-0.90, 0.90, 0.62, 0.92, cz0 + 0.42, cz0 + 0.46, Z_HS_WOOD)                       # bench along the view wall
    for xx in (-0.70, 0.70):
        H.box(xx - 0.02, xx + 0.02, 0.70, 0.86, cz0, cz0 + 0.42, Z_HS_WOOD)
    H.box(-0.92, 0.92, 0.80, 0.92, s0 - 0.03, s0, Z_HS_WOOD)                                # rest board under the slot
    poly = [(HS['ry0'], HS['rz0']), (HS['ry1'], HS['rz1']), (HS['ry1'], HS['rz1'] + 0.05), (HS['ry0'], HS['rz0'] + 0.05)]
    prism_x(H, poly, -1.10, 1.10, Z_HS_WOOD, Z_HS_WOOD, [Z_HS_WOOD, Z_HS_WOOD, Z_HS_ROOF, Z_HS_WOOD])
    la, lb = Vector((0.0, -2.62, -0.05)), Vector((0.0, -0.98, cz0))
    dv = (lb - la).normalized()
    side = Vector((1, 0, 0))
    for sgn in (-1, 1):
        H.strip([la + side * sgn * 0.23, lb + side * sgn * 0.23 + dv * 0.25], dv.cross(side).normalized(), 0.06, 0.05, Z_HS_LOG)
    for i in range(1, 14):
        p = la + (lb - la) * (i / 14.0)
        H.cyl(p - side * 0.23, p + side * 0.23, 0.02, Z_HS_WOOD, 6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            rock(H, (sx * 1.27, sy * 1.27, -0.06), (0.36, 0.36, 0.26), Z_HS_STONE, 61 + sx + 2 * sy)
    pos, yaw = HS_PLACE
    M = Matrix.Translation(pos) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
    transform_kb(H, M)
    R3 = Matrix.Rotation(math.radians(yaw), 3, 'Z')
    part('Hochsitz', 'static', pos, parent=None, yaw=yaw,
         note='hunting stand 11 m behind the hut (separate root: the map\'s Hochsitz prefab, same place); platform at 3.8 m, '
              'closed cabin with a viewing slot on three sides, the door and the ladder on its -y side')
    socket('Hide_Hochsitz', M @ Vector((0.0, 0.30, cz0 + 0.30)), 'hide', parent='Hochsitz',
           note='crouched in the cabin under the slot: not seen from the ground', pose='crouch',
           eye=K.r4(M @ Vector((0.0, 0.20, cz0 + 0.75))), facing=K.r4(R3 @ Vector((0, -1, 0))))
    socket('Seat_Hochsitz', M @ Vector((0.0, 0.74, cz0 + 0.46)), 'seat', parent='Hochsitz',
           note='bench under the slot: seated eye at the slot (looks out over +y and the sides)',
           eye=K.r4(M @ Vector((0.0, 0.72, cz0 + 1.18))), facing=K.r4(R3 @ Vector((0, 1, 0))))
    socket('Ladder_Hochsitz_Bottom', M @ la, 'climb', parent='Hochsitz', note='ladder foot')
    socket('Ladder_Hochsitz_Top', M @ lb, 'climb', parent='Hochsitz', note='ladder top at the cabin door')
    return M


# ================================================================ points, colliders, knock rays
def play_points():
    for name, (x, y, z) in SPOTS.items():
        socket('Spot_' + name, (x, y, z), 'item_slot', parent='TowerHut',
               note=f'{name}_Hut spawns here (Forest_Opening.json items, same place as in Update 3)')
    for name, kind, pos, d, note in (
            ('Audio_Lantern', 'audio', LANTERN, None, 'lantern: hiss of the flame, the bail creaking in the wind'),
            ('Audio_Stove', 'audio', (0.94, 0.76, 0.70), None, 'stove: crackling, ticking iron as it heats and cools'),
            ('Audio_Roof', 'audio', (0.0, 0.0, 3.1), None, 'tin roof: rain, needles and cones, branches scraping, steps up there'),
            ('Audio_Door', 'audio', (DOOR['x0'], Y0 - 0.05, 1.2), None, 'door: hinges creaking, slamming in the wind'),
            ('Audio_Window', 'audio', (X1, 0.0, 1.5), None, 'window: wind at the frame, tapping on the glass'),
            ('VFX_Chimney', 'vfx', (FLUE.x, FLUE.y, FLUE_TOP + 0.10), (0, 0, 1), 'smoke from the stove pipe while the stove burns'),
            ('VFX_StoveGlow', 'vfx', (0.94, 0.53, 0.66), (0, -1, 0), 'fire glow through the door slots (and the open door)'),
            ('VFX_LanternMoths', 'vfx', LANTERN + Vector((0, -0.10, 0.05)), None, 'moths round the lantern (warm nights)')):
        socket(name, pos, kind, note=note, parent='TowerHut')
        if d is not None:
            CONTRACT['sockets'][name]['dir'] = list(d)
    socket('Hide_Woodpile', (X0 - 0.55, 0.85, 0.30), 'hide', parent='TowerHut',
           note='crouched behind the woodpile at the back corner: not seen from the path', pose='crouch',
           eye=K.r4((X0 - 0.55, 0.80, 0.86)), facing=[0.0, -1.0, 0.0])


def static_boxes():
    """(name, parent, (x0, x1, y0, y1, z0, z1), rotation xyz deg or None, local) - local = in the parent's own frame"""
    R = 'TowerHut'
    w, d = WIN, DOOR
    B = [('Floor', R, (X0, X1, Y0, Y1, 0.0, FLOOR), None, False),
         ('Wall_L', R, (X0, IX0, Y0, Y1, FLOOR, ZE), None, False),
         ('Wall_B', R, (X0, X1, IY1, Y1, FLOOR, ZE), None, False),
         ('Wall_R_F', R, (IX1, X1, Y0, w['y0'], FLOOR, ZE), None, False),
         ('Wall_R_B', R, (IX1, X1, w['y1'], Y1, FLOOR, ZE), None, False),
         ('Wall_R_Low', R, (IX1, X1, w['y0'], w['y1'], FLOOR, w['z0']), None, False),
         ('Wall_R_High', R, (IX1, X1, w['y0'], w['y1'], w['z1'], ZE), None, False),
         ('Window', R, (IX1, X1, w['y0'], w['y1'], w['z0'], w['z1']), None, False),
         ('Wall_F_L', R, (X0, d['x0'], Y0, IY0, FLOOR, ZE), None, False),
         ('Wall_F_R', R, (d['x1'], X1, Y0, IY0, FLOOR, ZE), None, False),
         ('Wall_F_Head', R, (d['x0'], d['x1'], Y0, IY0, d['z1'], ZE), None, False),
         ('Gable_F', R, (-0.70, 0.70, Y0, IY0, ZE, ZE + 0.50), None, False),
         ('Gable_B', R, (-0.70, 0.70, IY1, Y1, ZE, ZE + 0.50), None, False),
         ('Stove', R, (STOVE['x0'], STOVE['x1'], STOVE['y0'], STOVE['y1'], FLOOR, STOVE['z1'] + 0.02), None, False),
         ('Flue', R, (FLUE.x - FLUE_R, FLUE.x + FLUE_R, FLUE.y - FLUE_R, FLUE.y + FLUE_R, STOVE['z1'], FLUE_TOP), None, False),
         ('Table', R, (TABLE['x0'], TABLE['x1'], TABLE['y0'], TABLE['y1'], FLOOR, TABLE['top']), None, False),
         ('Bunk', R, (BUNK['x0'], BUNK['x1'], BUNK['y0'], BUNK['y1'], FLOOR, BUNK['top']), None, False),
         ('Stool', R, (0.14, 0.46, -0.26, 0.06, FLOOR, 0.80), None, False),
         ('Shelf_Low', R, (SHELF['x0'], SHELF['x1'], SHELF['y0'], SHELF['y1'], SHELF['tops'][0] - 0.025, SHELF['tops'][0]), None, False),
         ('Shelf_Up', R, (SHELF['x0'], SHELF['x1'], SHELF['y0'], SHELF['y1'], SHELF['tops'][1] - 0.025, SHELF['tops'][1]), None, False),
         ('Woodpile', R, (X0 - 0.46, X0 - 0.04, -0.95, 0.55, 0.0, 1.20), None, False),
         ('Barrel', R, (-1.95, -1.37, 1.11, 1.69, 0.0, 0.80), None, False),
         ('Block', R, (CHOP_C.x - 0.22, CHOP_C.x + 0.22, CHOP_C.y - 0.22, CHOP_C.y + 0.22, 0.0, 0.45), None, False),
         ('Bench', R, (BENCH_C.x - 0.13, BENCH_C.x + 0.13, BENCH_C.y - 0.43, BENCH_C.y + 0.43, 0.0, 0.445), None, False),
         ('Step', R, (-0.77, 0.01, Y0 - 0.53, Y0 - 0.07, 0.0, 0.16), None, False),
         ('Door', 'IX_HutDoor_1', (DOOR['x0'] - 0.02, DOOR['x1'] + 0.02, Y0 - 0.07, Y0, LEAF_ZL, LEAF_ZH), None, False),
         ('Shutter', 'Window_Shutter', (IX1 - 0.065, IX1 - 0.035, WIN['y0'] - 0.69, WIN['y0'] - 0.03, WIN['z0'], WIN['z1'] + 0.03), None, False)]
    for s, nm in ((1, 'Roof_R'), (-1, 'Roof_L')):                       # the slopes: boxes tilted about y
        cx = s * XE / 2
        B.append((nm, R, (cx - XE / 2 / CP, cx + XE / 2 / CP, YF, YK, z_st(XE / 2) - 0.04, z_st(XE / 2)), (0.0, s * math.degrees(PITCH), 0.0), False))
    B.append(('Ladder', R, (X1 + 0.32, X1 + 0.93, LADDER_Y - 0.22, LADDER_Y + 0.22, 0.0, 2.20), None, False))
    # stand and sign: in their own frames (local = True: centre and size in the parent's own axes)
    zp, cz0 = HS['zp'], HS['cz0']
    zr = hs_roof_z(0.95)
    dw, dh = HS['door']
    B += [('HS_Platform', 'Hochsitz', (-1.00, 1.00, -1.00, 1.00, zp - 0.12, cz0), None, True),
          ('HS_Wall_L', 'Hochsitz', (-0.95, -0.92, -0.95, 0.95, cz0, zr), None, True),
          ('HS_Wall_R', 'Hochsitz', (0.92, 0.95, -0.95, 0.95, cz0, zr), None, True),
          ('HS_Wall_View', 'Hochsitz', (-0.92, 0.92, 0.92, 0.95, cz0, zr), None, True),
          ('HS_Wall_Door_L', 'Hochsitz', (-0.92, -dw, -0.95, -0.92, cz0, zr), None, True),
          ('HS_Wall_Door_R', 'Hochsitz', (dw, 0.92, -0.95, -0.92, cz0, zr), None, True),
          ('HS_Lintel', 'Hochsitz', (-dw, dw, -0.95, -0.92, cz0 + dh, zr), None, True),
          ('HS_Roof', 'Hochsitz', (-1.10, 1.10, -1.10, 1.30, HS['rz0'], HS['rz1'] + 0.05), None, True),
          ('HS_Bench', 'Hochsitz', (-0.90, 0.90, 0.62, 0.92, cz0, cz0 + 0.46), None, True)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            B.append((f'HS_Leg_{"R" if sx > 0 else "L"}{"B" if sy > 0 else "F"}', 'Hochsitz',
                      (sx * 1.10 - 0.08, sx * 1.10 + 0.08, sy * 1.10 - 0.08, sy * 1.10 + 0.08, -0.20, zp - 0.12), None, True))
    B += [('Sign_Board', 'Sign_Forsthuette', (-0.53, 0.53, -0.02, 0.02, 1.38, 1.76), None, True),
          ('Sign_Post_L', 'Sign_Forsthuette', (-0.49, -0.39, -0.03, 0.07, 0.0, 1.38), None, True),
          ('Sign_Post_R', 'Sign_Forsthuette', (0.39, 0.49, -0.03, 0.07, 0.0, 1.38), None, True)]
    return B


def knock_rays():
    R = []
    for i, (x, z) in enumerate(((0.90, 1.30), (1.15, 0.75))):
        R.append((f'Knock_WallF_{i + 1}', (x, -2.2, z), (0, 1, 0)))
    for i, x in enumerate((-0.80, 0.0, 0.80)):
        R.append((f'Knock_WallB_{i + 1}', (x, 2.2, 1.30), (0, -1, 0)))
    for i, y in enumerate((-0.45, 0.75)):
        R.append((f'Knock_WallR_{i + 1}', (2.4, y, 1.20), (-1, 0, 0)))
    for i, y in enumerate((-0.80, 0.20, 0.90)):
        R.append((f'Knock_WallL_{i + 1}', (-2.6, y, 1.60 if abs(y) < 0.6 else 1.20), (1, 0, 0)))
    R += [('Knock_Door', (-0.38, -2.2, 1.40), (0, 1, 0)), ('Knock_Window', (2.4, 0.12, 1.40), (-1, 0, 0)),
          ('Knock_Roof_L', (-0.7, 0.0, 4.2), (0, 0, -1)), ('Knock_Roof_R', (0.5, -0.4, 4.2), (0, 0, -1))]
    return R


def build_hut():
    shell()
    door()
    window()
    stove()
    furniture()
    props_inside()
    map_and_calendar()
    lantern()
    outside()
    sign()
    hochsitz()
    play_points()
    part('TowerHut', 'static', (0, 0, 0), parent=None,
         note='the hut: piers, sill, floor, walls with the door and window openings, gables, roof, trims, stove and flue, '
              'furniture, the woodpile, barrel, chopping block, bench, ladder; prefab root (the map\'s TowerHut prefab, same place)')
