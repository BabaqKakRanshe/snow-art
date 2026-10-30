"""StartWache (forest_start_post 1.2, built with tools/snow_style 29.10): the guard house of the start post that replaces the
booth (concept_v3 arrive_wache + night_wache, QUESTIONS_3 #4 #9 accepted). One root in its own frame (Blender: z up, metres;
origin on the ground in the middle of the footprint; the front (the big window, to the barrier and the road coming in) = -y,
the road wall with the door = +x; Unity (x, y, z) -> (-x, z, -y), the front -> +Z). The frame and the footprint are those of
the house in forest_start_post_v1 (ForestStartDress.json places it: u -8.5, v -3.4, yaw 180).
  StartWache   3.8 x 4.0 m, rendered brick walls 0.25 on a concrete plinth (board-formwork, 0.35 high = the floor), a flat
               roof with a 0.30 overhang: white fascia and soffit, a galvanised drip edge, felt; the big window to the front and
               a small one in the road wall (white frames, galvanised sills outside, spruce sills inside); the door opening in
               the road wall for the booth's door (IX_Door of StartBooth.prefab moves here: the same leaf, its strap hinges on
               white trims like the booth's) and two concrete steps; the booth's bulkhead lamp over the door (Lamp_Booth /
               Lens_Booth / Glow_Booth / LIGHT_Booth move here) with its conduit; the booth's plate ZUFAHRT SPERRGEBIET
               (Booth_Sign) right of the big window on a galvanised backing.
               Inside: whitewashed walls over a dark green oil-paint dado, board floor, ply ceiling; a desk under the big
               window (Slot_Table_1..3: the slots of the booth) with the log book and a radio (Audio_Radio), a chair; a bunk
               with a blanket (Spot_Bunk); a cast-iron stove in the back corner on a steel plate, its pipe through the roof
               (VFX_Smoke at the cap), the fire seen through the door slot (Glow_Stove); a shelf on the back wall (Slot_Shelf),
               the jerrycan's place on the floor along the road wall (Slot_Booth_Jerrycan); a coat on a hook by the door; the
               calendar; a caged ceiling bulkhead (Lens_Wache, the warm light inside) on a conduit from the switch by the door.
Atlas Wache (1024, the shed's 51.3 px/m); the lenses, the halo card and the plate: the start panel (start_tex)."""
import math
from mathutils import Vector, Matrix
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, quad, KBS, CONTRACT
from gen_kit import Z_SLAB, Z_FLOOR, Z_TRIMW, Z_LINING, Z_TIMBER, Z_STEELBLK, Z_GALV, Z_RUSTPIPE
import start_tex as ST
import start_kit as SK

uv = ST.uv
TAU = 2 * math.pi
ROOT = 'StartWache'
BOXES = []                       # colliders: (name, parent, (x0, x1, y0, y1, z0, z1)) in the root frame

# ---------------------------------------------------------------- zones (atlas Wache)
(Z_RENDER, Z_RENDER_IN, Z_REVEAL, Z_FELT, Z_DESK, Z_BLANKET, Z_PILLOW, Z_COAT, Z_PAPER, Z_IRON, Z_RADIO, Z_BOOK, Z_CAL,
 Z_FLOORPLATE, Z_SOFFIT) = range(200, 215)
WACHE_ZONES = [Z_SLAB, Z_FLOOR, Z_TRIMW, Z_LINING, Z_TIMBER, Z_STEELBLK, Z_GALV, Z_RUSTPIPE] + list(range(200, 215))

# ---------------------------------------------------------------- the house
HX, HY, T = 1.90, 2.00, 0.25                         # outer half sizes, wall thickness
IX0, IX1, IY0, IY1 = -HX + T, HX - T, -HY + T, HY - T  # room 3.30 x 3.50
FL = 0.35                                            # floor = the plinth's top; the plinth goes 0.30 into the ground
PL0, PLO = -0.30, 0.03                               # plinth bottom, how far it stands proud of the render
ZW = 2.95                                            # the walls' top outside = the soffit
ZC = 2.65                                            # the ceiling inside (2.30 clear)
OV = 0.30
FX, FY = HX + OV, HY + OV                            # the fascia's outer faces
FT = 0.025                                           # fascia board
ZF0, ZR = 2.93, 3.17                                 # fascia bottom, roof top (felt)
WIN_F = dict(u0=-0.95, u1=0.85, z0=1.25, z1=2.35)    # the big window in the front wall (u = x)
WIN_S = dict(u0=-1.50, u1=-0.70, z0=1.35, z1=2.20)   # the small window in the road wall (u = y)
FRAME_OUT, FRAME_D, FW = 0.06, 0.07, 0.06            # window frame: from the outer face in, its depth, its width
DOOR = dict(u0=0.60, u1=1.40, z0=FL, z1=FL + (SK.DOOR['z1'] - SK.DOOR['z0']))    # the booth's opening (0.80 x 1.85), road wall
# the booth's parts move here rigidly (same walls: the door and the lamp on +x, the plate on -y)
D_DOOR = Vector((HX - SK.X1, (DOOR['u0'] + DOOR['u1']) / 2 - (SK.DOOR['y0'] + SK.DOOR['y1']) / 2, FL - SK.FLOOR))
LAMP = Vector((HX, (DOOR['u0'] + DOOR['u1']) / 2, 2.55))
D_LAMP = LAMP - SK.BULK
SIGN_C = Vector((1.375, -HY - 0.014, 1.65))
D_SIGN = SIGN_C - SK.SIGN['c']
STOVE = dict(x0=-1.55, x1=-1.05, y0=1.15, y1=1.65, h=0.74)
PIPE = Vector((-1.30, 1.40, 0.0))                    # the stove pipe's axis (x, y): through the ceiling and the roof
PIPE_TOP = 4.20
DESK = dict(x0=-1.00, x1=0.80, y0=IY0, y1=IY0 + 0.60, z=FL + 0.74)
BUNK = dict(x0=IX0, x1=IX0 + 0.80, y0=-1.05, y1=0.95, z=FL + 0.42)
SHELF = dict(x0=-0.70, x1=0.30, y0=IY1 - 0.24, y1=IY1, z=1.55)
CEIL_LAMP = Vector((0.0, -0.20, ZC))


def P3(axis, a, u, z):
    """wall coordinates -> the root frame: axis 'y' = a wall across y (u = x), 'x' = across x (u = y)"""
    return Vector((u, a, z)) if axis == 'y' else Vector((a, u, z))


def nrm(axis, s):
    return Vector((0, s, 0)) if axis == 'y' else Vector((s, 0, 0))


def wall(k, axis, a_out, a_in, out_sign, u0, u1, holes, z_out0=FL):
    """one wall: the rendered outer face (z_out0 .. ZW) and the inner face (FL .. ZC) around the openings in `holes`
    [(u0, u1, z0, z1)]; reveals of the openings (render) through the wall"""
    def cells(z_lo, z_hi, uu0, uu1):
        us = sorted({uu0, uu1} | {h[0] for h in holes} | {h[1] for h in holes})
        zs = sorted({z_lo, z_hi} | {h[2] for h in holes if z_lo < h[2] < z_hi} | {h[3] for h in holes if z_lo < h[3] < z_hi})
        out = []
        for i in range(len(us) - 1):
            for j in range(len(zs) - 1):
                cu, cz = (us[i] + us[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
                if any(h[0] < cu < h[1] and h[2] < cz < h[3] for h in holes):
                    continue
                out.append((us[i], us[i + 1], zs[j], zs[j + 1]))
        return out
    n_out = nrm(axis, out_sign)
    for (ua, ub, za, zb) in cells(z_out0, ZW, u0, u1):
        face(k, [P3(axis, a_out, ua, za), P3(axis, a_out, ub, za), P3(axis, a_out, ub, zb), P3(axis, a_out, ua, zb)], Z_RENDER, n_out)
    iu0, iu1 = (IX0, IX1) if axis == 'y' else (IY0, IY1)
    for (ua, ub, za, zb) in cells(FL, ZC, iu0, iu1):
        face(k, [P3(axis, a_in, ua, za), P3(axis, a_in, ub, za), P3(axis, a_in, ub, zb), P3(axis, a_in, ua, zb)], Z_RENDER_IN, -n_out)


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


def window(k, g, axis, out_sign, h):
    """white frame 7 cm deep 6 cm in from the outer face, a mullion and a transom (two big lights, two top lights), the
    panes to g (two faces back to back), a galvanised sill outside, a spruce sill inside, the render reveals"""
    u0, u1, z0, z1 = h
    a_out = HY * out_sign if axis == 'y' else HX * out_sign
    a_in = a_out - out_sign * T
    f_out, f_in = a_out - out_sign * FRAME_OUT, a_out - out_sign * (FRAME_OUT + FRAME_D)
    fa, fb = sorted((f_out, f_in))
    # reveals: sides and head through the wall; the sill only behind the frame (outside it the galvanised sill covers it)
    reveal(k, axis, a_out, a_in, h, sill=False)
    wbox(k, axis, u0, u1, fa, fb, z0, z0 + FW, Z_TRIMW, skip=('-z', '-u', '+u'))                       # the frame
    wbox(k, axis, u0, u1, fa, fb, z1 - FW, z1, Z_TRIMW, skip=('+z', '-u', '+u'))
    wbox(k, axis, u0, u0 + FW, fa, fb, z0 + FW, z1 - FW, Z_TRIMW, skip=('-u', '-z', '+z'))
    wbox(k, axis, u1 - FW, u1, fa, fb, z0 + FW, z1 - FW, Z_TRIMW, skip=('+u', '-z', '+z'))
    um = (u0 + u1) / 2
    zt = z1 - FW - (0.30 if z1 - z0 > 1.0 else 0.24)                                              # the transom
    bm = 0.024                                                                                     # bars a little thinner
    am0, am1 = sorted((f_out - out_sign * 0.01, f_in + out_sign * 0.01))
    wbox(k, axis, um - 0.03, um + 0.03, am0, am1, z0 + FW, z1 - FW, Z_TRIMW, skip=('-z', '+z'))
    wbox(k, axis, u0 + FW, um - 0.03, am0, am1, zt - bm, zt + bm, Z_TRIMW, skip=('-u', '+u'))
    wbox(k, axis, um + 0.03, u1 - FW, am0, am1, zt - bm, zt + bm, Z_TRIMW, skip=('-u', '+u'))
    ag = (f_out + f_in) / 2
    n = nrm(axis, 1)
    for (pa, pb, qa, qb) in ((u0 + FW, um - 0.03, z0 + FW, zt - bm), (um + 0.03, u1 - FW, z0 + FW, zt - bm),
                             (u0 + FW, um - 0.03, zt + bm, z1 - FW), (um + 0.03, u1 - FW, zt + bm, z1 - FW)):
        for d, s in ((-0.0005, -1), (0.0005, 1)):
            face(g, [P3(axis, ag + d, pa, qa), P3(axis, ag + d, pb, qa), P3(axis, ag + d, pb, qb), P3(axis, ag + d, pa, qb)], 0.0, n * s)
    # sills: galvanised outside (4 cm proud, into the side reveals), spruce inside
    so0, so1 = sorted((a_out + out_sign * 0.045, f_out))
    wbox(k, axis, u0 - 0.025, u1 + 0.025, so0, so1, z0 - 0.022, z0, Z_GALV, skip=())
    wbox(k, axis, u0 - 0.025, u1 + 0.025, a_out + out_sign * 0.035, a_out + out_sign * 0.045, z0 - 0.06, z0 - 0.022, Z_GALV)
    si0, si1 = sorted((f_in, a_in - out_sign * 0.035))
    wbox(k, axis, u0 - 0.03, u1 + 0.03, si0, si1, z0 - 0.028, z0, Z_TIMBER, skip=())


def house():
    k = kb(ROOT, 'Wache')
    g = kb('Booth_Glass', 'glass')
    # ---- plinth: board-formwork concrete, 3 cm proud of the render, 0.30 in the ground; its top ledge round the walls
    box6(k, (-HX - PLO, -HY - PLO, PL0), (HX + PLO, HY + PLO, FL), Z_SLAB, skip=('-z', '+z'))
    for lo, hi in (((-HX - PLO, -HY - PLO), (HX + PLO, -HY)), ((-HX - PLO, HY), (HX + PLO, HY + PLO)),
                   ((-HX - PLO, -HY), (-HX, HY)), ((HX, -HY), (HX + PLO, HY))):
        face(k, [(lo[0], lo[1], FL), (hi[0], lo[1], FL), (hi[0], hi[1], FL), (lo[0], hi[1], FL)], Z_SLAB, (0, 0, 1))
    # ---- floor boards, the threshold board in the door opening
    for xa, xb in ((IX0, 0.0), (0.0, IX1)):
        for ya, yb in ((IY0, 0.0), (0.0, IY1)):
            face(k, [(xa, ya, FL), (xb, ya, FL), (xb, yb, FL), (xa, yb, FL)], Z_FLOOR, (0, 0, 1))
    face(k, [(IX1, DOOR['u0'], FL), (HX, DOOR['u0'], FL), (HX, DOOR['u1'], FL), (IX1, DOOR['u1'], FL)], Z_TIMBER, (0, 0, 1))
    # ---- walls: front (the big window), back, left, road (+x: the small window, the door)
    hf = (WIN_F['u0'], WIN_F['u1'], WIN_F['z0'], WIN_F['z1'])
    hs = (WIN_S['u0'], WIN_S['u1'], WIN_S['z0'], WIN_S['z1'])
    hd = (DOOR['u0'], DOOR['u1'], DOOR['z0'], DOOR['z1'])
    wall(k, 'y', -HY, IY0, -1, -HX, HX, [hf])
    wall(k, 'y', HY, IY1, 1, -HX, HX, [])
    wall(k, 'x', -HX, IX0, -1, -HY, HY, [])
    wall(k, 'x', HX, IX1, 1, -HY, HY, [hs, hd])
    window(k, g, 'y', -1, hf)
    window(k, g, 'x', 1, hs)
    reveal(k, 'x', HX, IX1, hd, sill=False)
    # the door's lining inside (spruce casing round the opening on the inner face)
    for (ua, ub, za, zb) in ((DOOR['u0'] - 0.07, DOOR['u0'], FL, DOOR['z1'] + 0.07), (DOOR['u1'], DOOR['u1'] + 0.07, FL, DOOR['z1'] + 0.07),
                             (DOOR['u0'], DOOR['u1'], DOOR['z1'], DOOR['z1'] + 0.07)):
        wbox(k, 'x', ua, ub, IX1 - 0.02, IX1, za, zb, Z_TIMBER, skip=('+a', '-z'))
    # ---- the booth's door trims and pintles, moved with its door (white boards beside and over the hung leaf)
    for ya, yb in ((-0.45, -0.335), (0.535, 0.65)):
        box6(k, (HX, ya + D_DOOR.y, FL), (HX + 0.022, yb + D_DOOR.y, 2.04 + D_DOOR.z), Z_TRIMW, skip=('-x', '-z', '+z'))
    box6(k, (HX, -0.45 + D_DOOR.y, 2.04 + D_DOOR.z), (HX + 0.022, 0.65 + D_DOOR.y, 2.15 + D_DOOR.z), Z_TRIMW, skip=('-x',))
    for zh in (0.32, 1.90):
        k.box(HX + 0.022, HX + 0.052, 0.535 + D_DOOR.y, 0.575 + D_DOOR.y, zh + D_DOOR.z - 0.03, zh + D_DOOR.z + 0.03, Z_STEELBLK)
    # two concrete steps to the door
    yc0, yc1 = DOOR['u0'] - 0.15, DOOR['u1'] + 0.15
    box6(k, (HX + PLO, yc0, PL0), (HX + 0.32, yc1, FL - 0.02), Z_SLAB, skip=('-x', '-z'))
    box6(k, (HX + 0.32, yc0, PL0), (HX + 0.62, yc1, 0.17), Z_SLAB, skip=('-x', '-z'))
    BOXES.append(('Wache_Step_Hi', ROOT, (HX, HX + 0.32, yc0, yc1, -0.10, FL - 0.02)))
    BOXES.append(('Wache_Step_Lo', ROOT, (HX + 0.32, HX + 0.62, yc0, yc1, -0.10, 0.17)))
    roof(k)
    # ---- the booth's plate on a galvanised backing (Booth_Sign moves onto it), its lamp's conduit
    s = SK.SIGN
    k.box(SIGN_C.x - s['w'] / 2 - 0.012, SIGN_C.x + s['w'] / 2 + 0.012, -HY - 0.012, -HY, SIGN_C.z - s['h'] / 2 - 0.012,
          SIGN_C.z + s['h'] / 2 + 0.012, Z_GALV)
    K.conduit(k, [LAMP + Vector((0.012, 0.0, 0.075)), LAMP + Vector((0.012, 0.0, 0.30)), Vector((HX + 0.012, IY1 - 0.10, 2.85)),
                  Vector((HX + 0.012, IY1, 2.85))], r=0.010)
    k.box(HX, HX + 0.05, IY1 - 0.02, IY1 + 0.07, 2.80, 2.90, Z_GALV)                                  # the junction box
    interior(k)
    part('Booth_Glass', 'static', ((WIN_F['u0'] + WIN_F['u1']) / 2, -HY + FRAME_OUT + FRAME_D / 2, (WIN_F['z0'] + WIN_F['z1']) / 2),
         parent=ROOT, note='the panes of both windows (the booth\'s glass object takes this mesh; M_Start_Glass)')
    part(ROOT, 'static', (0, 0, 0), note='the guard house (root): origin = the middle of the footprint on the ground; floor 0.35 '
                                         '(the plinth\'s top), the plinth 0.30 into the ground')
    # colliders (the windows are glazed: the walls are whole except the door)
    BOXES.extend([
        ('Wache_Plinth', ROOT, (-HX - PLO, HX + PLO, -HY - PLO, HY + PLO, PL0, FL)),
        ('Wache_Front', ROOT, (-HX, HX, -HY, IY0, FL, ZW)),
        ('Wache_Back', ROOT, (-HX, HX, IY1, HY, FL, ZW)),
        ('Wache_Left', ROOT, (-HX, IX0, IY0, IY1, FL, ZW)),
        ('Wache_Road_F', ROOT, (IX1, HX, IY0, DOOR['u0'], FL, ZW)),
        ('Wache_Road_B', ROOT, (IX1, HX, DOOR['u1'], IY1, FL, ZW)),
        ('Wache_Road_Top', ROOT, (IX1, HX, DOOR['u0'], DOOR['u1'], DOOR['z1'], ZW)),
        ('Wache_Ceiling', ROOT, (-HX, HX, -HY, HY, ZC, ZR)),
        ('Wache_Roof', ROOT, (-FX, FX, -FY, FY, ZW, ZR))])


def roof(k):
    # soffit (white boards) from the walls to the fascia, the fascia, the galvanised drip edge, the felt
    for lo, hi in (((-FX + FT, -FY + FT), (FX - FT, -HY)), ((-FX + FT, HY), (FX - FT, FY - FT)),
                   ((-FX + FT, -HY), (-HX, HY)), ((HX, -HY), (FX - FT, HY))):
        face(k, [(lo[0], lo[1], ZW), (hi[0], lo[1], ZW), (hi[0], hi[1], ZW), (lo[0], hi[1], ZW)], Z_SOFFIT, (0, 0, -1))
    box6(k, (-FX, -FY, ZF0), (FX, -FY + FT, ZR), Z_TRIMW, skip=('+z',))
    box6(k, (-FX, FY - FT, ZF0), (FX, FY, ZR), Z_TRIMW, skip=('+z',))
    box6(k, (-FX, -FY + FT, ZF0), (-FX + FT, FY - FT, ZR), Z_TRIMW, skip=('+z', '-y', '+y'))
    box6(k, (FX - FT, -FY + FT, ZF0), (FX, FY - FT, ZR), Z_TRIMW, skip=('+z', '-y', '+y'))
    lip, band = 0.012, 0.07
    for (lo, hi) in (((-FX - lip, -FY - lip, ZR), (FX + lip, -FY + band, ZR + 0.012)), ((-FX - lip, FY - band, ZR), (FX + lip, FY + lip, ZR + 0.012)),
                     ((-FX - lip, -FY + band, ZR), (-FX + band, FY - band, ZR + 0.012)), ((FX - band, -FY + band, ZR), (FX + lip, FY - band, ZR + 0.012))):
        box6(k, lo, hi, Z_GALV, skip=('-z',))
    for (lo, hi) in (((-FX - lip, -FY - lip, ZR - 0.05), (FX + lip, -FY, ZR)), ((-FX - lip, FY, ZR - 0.05), (FX + lip, FY + lip, ZR)),
                     ((-FX - lip, -FY, ZR - 0.05), (-FX, FY, ZR)), ((FX, -FY, ZR - 0.05), (FX + lip, FY, ZR))):
        box6(k, lo, hi, Z_GALV, skip=('+z',))
    face(k, [(-FX + band, -FY + band, ZR + 0.004), (FX - band, -FY + band, ZR + 0.004), (FX - band, FY - band, ZR + 0.004),
             (-FX + band, FY - band, ZR + 0.004)], Z_FELT, (0, 0, 1))
    # the ceiling inside: ply sheets
    face(k, [(IX0, IY0, ZC), (IX1, IY0, ZC), (IX1, IY1, ZC), (IX0, IY1, ZC)], Z_LINING, (0, 0, -1))
    # the stove pipe through the roof: collar, the pipe, the rain cap on three legs
    p = PIPE
    k.cyl(Vector((p.x, p.y, ZR + 0.004)), Vector((p.x, p.y, ZR + 0.10)), 0.13, Z_GALV, 12, r2=0.075)
    k.cyl(Vector((p.x, p.y, ZR + 0.10)), Vector((p.x, p.y, PIPE_TOP)), 0.065, Z_RUSTPIPE, 10, caps=False)
    k.lathe(Vector((p.x, p.y, PIPE_TOP + 0.10)), (0, 0, 1), [(0.0, 0.17), (0.07, 0.02)], Z_RUSTPIPE, 10, cap0=True, cap1=False)
    for a in (0, 120, 240):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        k.box_m(Vector((p.x, p.y, PIPE_TOP + 0.05)) + d * 0.068, (0.012, 0.012, 0.10), Z_RUSTPIPE)


def interior(k):
    # ---- the desk under the big window: top, apron, four legs; the log book, the radio
    d = DESK
    box6(k, (d['x0'], d['y0'], d['z'] - 0.035), (d['x1'], d['y1'], d['z']), Z_DESK, skip=('-y',))
    box6(k, (d['x0'] + 0.04, d['y1'] - 0.065, d['z'] - 0.14), (d['x1'] - 0.04, d['y1'] - 0.045, d['z'] - 0.035), Z_TIMBER, skip=('+z',))
    for lx in (d['x0'] + 0.03, d['x1'] - 0.08):
        for ly in (d['y0'] + 0.03, d['y1'] - 0.08):
            box6(k, (lx, ly, FL), (lx + 0.05, ly + 0.05, d['z'] - 0.035), Z_TIMBER, skip=('-z', '+z'))
    box6(k, (0.48, -1.52, d['z']), (0.78, -1.31, d['z'] + 0.032), Z_BOOK, skip=('-z',))                  # the post's log book
    box6(k, (-0.95, -1.70, d['z']), (-0.66, -1.56, d['z'] + 0.17), Z_RADIO, skip=('-z',))              # the radio
    k.cyl(Vector((-0.92, -1.62, d['z'] + 0.17)), Vector((-0.86, -1.66, d['z'] + 0.52)), 0.004, Z_STEELBLK, 5)   # its aerial
    for kx in (-0.72, -0.89):
        k.cyl(Vector((kx, -1.56, d['z'] + 0.05)), Vector((kx, -1.545, d['z'] + 0.05)), 0.012, Z_STEELBLK, 8)
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
    # ---- the stove: cast iron on legs, a steel plate under it, the fire door with its slot (Glow_Stove), the pipe
    s = STOVE
    zb = FL + 0.10
    box6(k, (IX0, s['y0'] - 0.15, FL), (s['x1'] + 0.40, IY1, FL + 0.004), Z_FLOORPLATE, skip=('-z', '-x', '+y'))
    for lx in (s['x0'] + 0.03, s['x1'] - 0.07):
        for ly in (s['y0'] + 0.03, s['y1'] - 0.07):
            box6(k, (lx, ly, FL + 0.004), (lx + 0.04, ly + 0.04, zb), Z_IRON, skip=('-z', '+z'))
    box6(k, (s['x0'], s['y0'], zb), (s['x1'], s['y1'], FL + s['h']), Z_IRON)
    box6(k, (s['x0'] - 0.02, s['y0'] - 0.02, FL + s['h']), (s['x1'] + 0.02, s['y1'] + 0.02, FL + s['h'] + 0.025), Z_IRON, skip=('-z',))
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
    p = PIPE
    k.cyl(Vector((p.x, p.y, FL + s['h'] + 0.025)), Vector((p.x, p.y, ZC)), 0.06, Z_STEELBLK, 10, caps=False)
    k.cyl(Vector((p.x, p.y, ZC - 0.004)), Vector((p.x, p.y, ZC - 0.012)), 0.12, Z_GALV, 12)               # the ceiling collar
    socket('VFX_Smoke', (p.x, p.y, PIPE_TOP + 0.18), 'vfx', parent=ROOT, note='the stove\'s smoke over the pipe\'s cap')
    BOXES.append(('Wache_Stove', ROOT, (s['x0'], s['x1'], s['y0'], s['y1'], FL, FL + s['h'] + 0.025)))
    # ---- the shelf on the back wall (the funnel), its brackets
    sh = SHELF
    box6(k, (sh['x0'], sh['y0'], sh['z']), (sh['x1'], sh['y1'], sh['z'] + 0.025), Z_TIMBER, skip=('+y',))
    for bx_ in (sh['x0'] + 0.12, sh['x1'] - 0.12):
        k.box(bx_ - 0.012, bx_ + 0.012, sh['y1'] - 0.20, sh['y1'], sh['z'] - 0.14, sh['z'], Z_STEELBLK)
    socket('Slot_Shelf', ((sh['x0'] + sh['x1']) / 2, (sh['y0'] + sh['y1']) / 2, sh['z'] + 0.03), 'slot', parent=ROOT,
           note='the shelf board on the back wall (the funnel, rim down)')
    # ---- the jerrycan's place: on the floor along the road wall under the small window, by the desk
    socket('Slot_Booth_Jerrycan', (IX1 - 0.12, -1.25, FL + 0.01), 'slot', parent=ROOT,
           note='the jerrycan on the floor along the road wall (ForestItemPointsStep: yaw 90 = along the wall, as in the booth)')
    # ---- the coat on its hook by the door, the calendar 1991, the light switch and the conduit to the ceiling lamp
    hk = Vector((IX1, 0.12, 1.80))
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
    K.conduit(k, [Vector((IX1 - 0.02, sw.y, sw.z + 0.045)), Vector((IX1 - 0.02, sw.y, ZC - 0.02)), Vector((CEIL_LAMP.x + 0.06, sw.y, ZC - 0.02)),
                  Vector((CEIL_LAMP.x + 0.06, CEIL_LAMP.y, ZC - 0.02))], r=0.010)
    # ---- the caged ceiling bulkhead (the shed's): plate, housing, the dome (Lens_Wache, lit), the cage
    c = CEIL_LAMP
    k.box(c.x - 0.045, c.x + 0.045, c.y - 0.045, c.y + 0.045, c.z - 0.01, c.z, Z_STEELBLK)
    k.lathe(c - Vector((0, 0, 0.01)), (0, 0, -1), [(0.0, 0.07), (0.01, 0.085), (0.045, 0.085), (0.05, 0.072)], Z_STEELBLK, 12,
            cap0=True, cap1=False)
    L = kb('Lens_Wache', 'lens:booth')
    dome_c = c - Vector((0, 0, 0.058))
    L.disc_uv(dome_c, Vector((0, 0, -1)), 0.068, uv('l_bulk'), 12, dome=0.04)
    for a in (0, 60, 120):
        dv = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        k.tube([dome_c + dv * 0.078 * math.cos(math.radians(t)) - Vector((0, 0, 0.052 * math.sin(math.radians(t)))) for t in range(0, 181, 30)],
               0.003, Z_STEELBLK, 4, caps=False)
    part('Lens_Wache', 'static', dome_c - Vector((0, 0, 0.02)), parent=ROOT,
         note='the ceiling bulkhead\'s dome: M_Start_Lamp_Booth (lit); the light LIGHT_Wache_Inside under it')
    socket('LIGHT_Wache_Inside', dome_c - Vector((0, 0, 0.10)), 'light', parent=ROOT, note='the warm light inside (point, 2700 K)')


def build_wache():
    house()


# ---------------------------------------------------------------- the booth's parts that move into the house (Unity deltas)
def unity_vec(v):
    return [round(-float(v[0]), 4) + 0.0, round(float(v[2]), 4) + 0.0, round(-float(v[1]), 4) + 0.0]


MOVES = {   # template child -> delta in the prefab (Unity, metres)
    'IX_Door': D_DOOR, 'Hand_Door_Out': D_DOOR, 'Hand_Door_In': D_DOOR,
    'Lamp_Booth': D_LAMP, 'Lens_Booth': D_LAMP, 'Glow_Booth': D_LAMP, 'LIGHT_Booth': D_LAMP,
    'Booth_Sign': D_SIGN}
