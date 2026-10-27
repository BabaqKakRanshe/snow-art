"""Forest hut yard (forest_hut_yard 1.0, built locally with tools/snow_style 26.10): the forester's hut's yard and pointers -
six prefabs, each in its own frame (Blender: z up, the front -y, metres; origin on the ground, z = 0; Unity (x, y, z) ->
(-x, z, -y), the front -> +Z). Shed style (snow_style.json): dark stained boards with white trims like the hut.
  HutOuthouse  Plumpsklo 1.2 x 1.2 m, 2.2 m high: dark stained board-and-batten, white corner boards, a mono-pitch
               corrugated roof high at the door; IX_Door on the front (hinge at its left edge, 100 deg out) with the heart
               (painted, the vent); inside a bench with the hole; it stands on four stones
  HutFeeder    Futterraufe / Kirrung by the Hochsitz: four posts, a V hay rack with hay, a trough, a board gable roof
  HutPolter    a timber stack by the road: 15 spruce logs 4 m on two sleepers, the number 317 sprayed red on the road ends
  HutSign      the pointer at the trail head: a post with an arrow board FORSTHÜTTE 100 m / FORESTER'S HUT (panel atlas) and a
               battery lantern with yellow glass on a hook (Lamp_Lant, Lens_Lant, Glow_Lant, LIGHT_Lant: the trail light)
  HutPorch     a lean-to porch for the hut's door: deck at the hut's floor, one step, two posts, a corrugated roof, a bench;
               origin = the middle of the hut's front on the ground, its back (+y) against the facade
  HutMap       the forester's folded map for his table (panel atlas): antenna No. 1 circled, a place in the woods crossed out
Each root's parts / sockets are given in its own frame (the contract); in the .blend the roots stand apart (DISPLAY)."""
import math
from mathutils import Vector, Matrix
import bmesh
import van3_mech as VM
import gen_kit as K
from gen_kit import kb, part, socket, box6, face, prism_x, prism_y, wall_grid, quad, KBS, CONTRACT, LAMPS
from gen_kit import Z_SLAB, Z_TRIMW, Z_TIMBER, Z_ROOF, Z_ROOFUNDER, Z_STEELBLK
from van2_kit import ZERO
import yard_tex as YT

uv = YT.uv
TAU = 2 * math.pi
ROOTS = ['HutOuthouse', 'HutFeeder', 'HutPolter', 'HutSign', 'HutPorch', 'HutMap', 'RouteSign']
DISPLAY = {'HutSign': Vector((-8.0, 0.0, 0.0)), 'HutOuthouse': Vector((-5.5, 0.0, 0.0)), 'HutFeeder': Vector((-2.6, 0.0, 0.0)),
           'HutPorch': Vector((1.0, 0.8, 0.0)), 'HutPolter': Vector((6.6, 0.0, 0.0)), 'HutMap': Vector((10.0, 0.0, 0.0)),
           'RouteSign': Vector((-11.0, 0.0, 0.0))}
ROOT_OF = {}
BOXES = []                       # colliders: (name, parent, (x0, x1, y0, y1, z0, z1), rot_xyz_deg or None) in the root frame

# ---------------------------------------------------------------- zones (YardWood: the wooden things; YardProps: the sign)
(Z_DARK, Z_ODOOR, Z_ODOORIN, Z_ILIN, Z_SEATB, Z_GREY, Z_BARK, Z_END, Z_HAY, Z_STONE) = range(150, 160)
WOOD_ZONES = [Z_SLAB, Z_TRIMW, Z_TIMBER, Z_ROOF, Z_ROOFUNDER, Z_STEELBLK] + list(range(150, 160))
(Z_SPOST, Z_SBOARD, Z_LMETAL, Z_LWIRE) = range(170, 174)
PROP_ZONES = list(range(170, 174)) + [Z_STEELBLK]


def reg(name, atlas, root):
    ROOT_OF[name] = root
    return kb(name, atlas)


def hsh(i, s=0):
    x = math.sin(i * 12.9898 + s * 78.233) * 43758.5453
    return x - math.floor(x)


# ================================================================ HutOuthouse
O = dict(X0=-0.6, X1=0.6, Y0=-0.6, Y1=0.6, T=0.045, FLOOR=0.16)
OX0, OX1, OY0, OY1, OT, OFL = O['X0'], O['X1'], O['Y0'], O['Y1'], O['T'], O['FLOOR']
OIX0, OIX1, OIY0, OIY1 = OX0 + OT, OX1 - OT, OY0 + OT, OY1 - OT
OPITCH = math.radians(10.0)                          # mono-pitch, high at the door (front, -y)
OTP, OCP, OSP = math.tan(OPITCH), math.cos(OPITCH), math.sin(OPITCH)
OZF = 2.12                                           # rafter bottom over the front outer face
OOV_F, OOV_B, OOV_S = 0.22, 0.16, 0.12
OYF, OYB, OXS = OY0 - OOV_F, OY1 + OOV_B, OX1 + OOV_S
ORD, ORW, OPU, OSH = 0.08, 0.045, 0.03, 0.02
ODOOR = dict(x0=-0.33, x1=0.33, z1=1.92)             # the opening in the front wall
OLEAF = dict(x0=-0.35, x1=0.35, y0=OY0 - 0.046, y1=OY0 - 0.004, z0=OFL + 0.012, z1=1.94)
ODOOR_PIV = Vector((-0.36, OY0 - 0.052, 1.05))
HEART = Vector((0.0, OY0 - 0.046, 1.50))             # the heart cut in the leaf (painted; the vent)
BENCH = dict(y0=OY1 - OT - 0.50, z=0.46)


def oz_rb(y):
    return OZF - (y - OY0) * OTP


def oz_rt(y):
    return oz_rb(y) + ORD / OCP


def oz_sb(y):
    return oz_rb(y) + (ORD + OPU) / OCP


def oz_st(y):
    return oz_sb(y) + OSH / OCP


OZS = oz_rb(OIY1)
OZTOP_F, OZTOP_B = OZF, oz_rb(OIY1)


def outhouse_shell():
    k = reg('HutOuthouse', 'YardWood', 'HutOuthouse')
    wz = dict(out=Z_DARK, reveal=Z_TIMBER, end=Z_DARK, top=Z_TIMBER, **{'in': Z_ILIN})
    for sx in (-1, 1):                                                # four field stones under the sill
        for sy in (-1, 1):
            c = Vector((sx * (OX1 - 0.10), sy * (OY1 - 0.10), 0.0))
            k.box(c.x - 0.13, c.x + 0.13, c.y - 0.13, c.y + 0.13, -0.10, 0.08, Z_STONE)
    box6(k, (OX0, OY0, 0.08), (OX1, OY1, OFL), Z_TIMBER, skip=('+z',))                  # the sill frame
    face(k, [(OIX0, OIY0, OFL), (OIX1, OIY0, OFL), (OIX1, OIY1, OFL), (OIX0, OIY1, OFL)], Z_ILIN, (0, 0, 1))
    face(k, [(ODOOR['x0'], OY0, OFL), (ODOOR['x1'], OY0, OFL), (ODOOR['x1'], OIY0, OFL), (ODOOR['x0'], OIY0, OFL)], Z_TIMBER, (0, 0, 1))
    wall_grid(k, 'y', OY0, OIY0, [OX0, ODOOR['x0'], ODOOR['x1'], OX1], [OFL, ODOOR['z1'], OZTOP_F], {(1, 0)}, -1, wz)
    wall_grid(k, 'y', OIY1, OY1, [OX0, OX1], [OFL, OZTOP_B], set(), 1, wz)
    wall_grid(k, 'x', OIX1, OX1, [OIY0, OIY1], [OFL, OZS], set(), 1, wz, ends=False, top=False)
    wall_grid(k, 'x', OX0, OIX0, [OIY0, OIY1], [OFL, OZS], set(), -1, wz, ends=False, top=False)
    poly = [(OIY0, OZS), (OIY1, OZS), (OIY1, oz_sb(OIY1) - 0.002), (OIY0, oz_sb(OIY0) - 0.002)]
    prism_x(k, poly, OIX1, OX1, Z_ILIN, Z_DARK, [None, None, None, None])
    prism_x(k, poly, OX0, OIX0, Z_DARK, Z_ILIN, [None, None, None, None])
    for (ya, yb), zt, e_ya, e_yb in (((OY0, OIY0), OZTOP_F, Z_DARK, Z_ILIN), ((OIY1, OY1), OZTOP_B, Z_ILIN, Z_DARK)):
        poly = [(ya, zt), (yb, zt), (yb, oz_sb(yb) - 0.002), (ya, oz_sb(ya) - 0.002)]
        prism_x(k, poly, OX0, OX1, Z_DARK, Z_DARK, [None, e_yb, None, e_ya])
    cb, ct = 0.10, 0.02                                               # white corner boards
    for sx in (-1, 1):
        for sy in (-1, 1):
            xo, yo = (OX1 if sx > 0 else OX0), (OY1 if sy > 0 else OY0)
            ztop = oz_sb(yo) - 0.002
            xa, xb = sorted((xo, xo - sx * cb))
            ya, yb = sorted((yo, yo + sy * ct))
            box6(k, (xa, ya, OFL), (xb, yb, ztop), Z_TRIMW, skip=('-z', '+z', '+y' if sy < 0 else '-y'))
            xa, xb = sorted((xo, xo + sx * ct))
            ya, yb = sorted((yo + sy * ct, yo - sy * (cb - ct)))
            box6(k, (xa, ya, OFL), (xb, yb, ztop), Z_TRIMW, skip=('-z', '+z', '+x' if sx < 0 else '-x'))
    for xa, xb in ((-0.45, -0.37), (0.37, 0.45)):                     # white door trims and the head
        box6(k, (xa, OY0 - 0.02, OFL), (xb, OY0, 1.96), Z_TRIMW, skip=('+y', '-z', '+z'))
    box6(k, (-0.45, OY0 - 0.02, 1.96), (0.45, OY0, 2.05), Z_TRIMW, skip=('+y',))
    for zh in (0.40, 1.82):                                           # hinge pintles on the left trim
        k.box(-0.40, -0.37, OY0 - 0.06, OY0 - 0.02, zh - 0.03, zh + 0.03, Z_STEELBLK)
    # the roof: two rafters, purlins, the corrugated sheet, fascia boards
    for xr in (OX0 + 0.03, OX1 - 0.03):
        poly = [(OYF, oz_rb(OYF)), (OYB, oz_rb(OYB)), (OYB, oz_rt(OYB)), (OYF, oz_rt(OYF))]
        prism_x(k, poly, xr - ORW / 2, xr + ORW / 2, Z_TIMBER, Z_TIMBER, [Z_TIMBER, None, None, None])
    for yp in (-0.72, -0.25, 0.22, 0.66):
        w = 0.02
        poly = [(yp - w, oz_rt(yp - w)), (yp + w, oz_rt(yp + w)), (yp + w, oz_sb(yp + w) - 0.001), (yp - w, oz_sb(yp - w) - 0.001)]
        prism_x(k, poly, -OXS, OXS, None, None, [None, Z_TIMBER, None, Z_TIMBER])
    top = [Vector((-OXS, OYF, oz_st(OYF))), Vector((OXS, OYF, oz_st(OYF))), Vector((OXS, OYB, oz_st(OYB))), Vector((-OXS, OYB, oz_st(OYB)))]
    bot = [Vector((-OXS, OYF, oz_sb(OYF))), Vector((OXS, OYF, oz_sb(OYF))), Vector((OXS, OYB, oz_sb(OYB))), Vector((-OXS, OYB, oz_sb(OYB)))]
    nrm = Vector((0, OSP, OCP))
    face(k, top, Z_ROOF, nrm)
    face(k, bot, Z_ROOFUNDER, -nrm)
    box6(k, (-OXS, OYF - 0.02, oz_rb(OYF) - 0.03), (OXS, OYF, oz_st(OYF) + 0.02), Z_TRIMW, skip=('+y', '-x', '+x'))
    box6(k, (-OXS, OYB, oz_rb(OYB) - 0.03), (OXS, OYB + 0.02, oz_st(OYB) + 0.02), Z_TRIMW, skip=('-y', '-x', '+x'))
    # inside: the bench with the hole across the back, its front board; a hook with an old newspaper (painted) on the left wall
    by0 = BENCH['y0']
    box6(k, (OIX0, by0, BENCH['z'] - 0.03), (OIX1, OIY1, BENCH['z']), Z_SEATB, skip=('-x', '+x', '+y'))
    box6(k, (OIX0, by0, OFL), (OIX1, by0 + 0.025, BENCH['z'] - 0.03), Z_ILIN, skip=('-x', '+x', '-z', '+z'))
    k.cyl(Vector((OIX0, -0.20, 1.30)), Vector((OIX0 + 0.06, -0.20, 1.30)), 0.006, Z_STEELBLK, 5)
    part('HutOuthouse', 'static', (0, 0, 0), note='the outhouse (root): origin = the middle of its footprint on the ground; it '
                                                   'stands on four stones, the floor at 0.16')
    socket('Slot_OutBench', (0.30, by0 + 0.25, BENCH['z']), 'slot', parent='HutOuthouse', note='the bench top beside the hole')
    socket('Spot_Hole', (0.0, by0 + 0.25, BENCH['z']), 'item_slot', parent='HutOuthouse', note='the hole (dark, painted)')
    BOXES.extend([
        ('Out_Front_L', 'HutOuthouse', (OX0, ODOOR['x0'], OY0, OIY0, 0.08, OZTOP_F), None),
        ('Out_Front_R', 'HutOuthouse', (ODOOR['x1'], OX1, OY0, OIY0, 0.08, OZTOP_F), None),
        ('Out_Front_Top', 'HutOuthouse', (ODOOR['x0'], ODOOR['x1'], OY0, OIY0, ODOOR['z1'], OZTOP_F), None),
        ('Out_Back', 'HutOuthouse', (OX0, OX1, OIY1, OY1, 0.08, OZTOP_B), None),
        ('Out_Left', 'HutOuthouse', (OX0, OIX0, OIY0, OIY1, 0.08, OZS), None),
        ('Out_Right', 'HutOuthouse', (OIX1, OX1, OIY0, OIY1, 0.08, OZS), None),
        ('Out_Roof', 'HutOuthouse', (-OXS, OXS, OYF, OYB, oz_rb(0.0) - 0.02, oz_st(0.0) + 0.02), (math.degrees(OPITCH), 0.0, 0.0)),
        ('Out_Floor', 'HutOuthouse', (OX0, OX1, OY0, OY1, -0.10, OFL), None),
        ('Out_Bench', 'HutOuthouse', (OIX0, OIX1, by0, OIY1, OFL, BENCH['z']), None)])


def outhouse_door():
    D = reg('IX_Door', 'YardWood', 'HutOuthouse')
    L = OLEAF
    x0, x1, y0, y1, zl, zh = L['x0'], L['x1'], L['y0'], L['y1'], L['z0'], L['z1']
    box6(D, (x0, y0, zl), (x1, y1, zh), {'-y': Z_ODOOR, '+y': Z_ODOORIN, '*': Z_ODOOR})
    for z0_ in (0.30, 1.78):                                          # ledges and the brace inside (the outside stays flat, heart)
        box6(D, (x0 + 0.03, y1, z0_), (x1 - 0.03, y1 + 0.02, z0_ + 0.09), Z_ODOORIN, skip=('-y',))
    D.strip([Vector((x0 + 0.12, y1 + 0.009, 0.42)), Vector((x1 - 0.10, y1 + 0.009, 1.72))], Vector((0, 1, 0)), 0.08, 0.016, Z_ODOORIN)
    for zh_ in (0.40, 1.82):                                          # strap hinges outside to the knuckles on the pivot line
        D.box(ODOOR_PIV.x + 0.006, x0 + 0.40, y0 - 0.006, y0, zh_ - 0.02, zh_ + 0.02, Z_STEELBLK)
        D.cyl(Vector((ODOOR_PIV.x, ODOOR_PIV.y, zh_ - 0.03)), Vector((ODOOR_PIV.x, ODOOR_PIV.y, zh_ + 0.03)), 0.010, Z_STEELBLK, 8)
    hx, hz = x1 - 0.07, 1.00                                          # a wooden turn-button handle outside, a hook-and-eye inside
    D.box(hx - 0.015, hx + 0.015, y0 - 0.03, y0, hz - 0.06, hz + 0.06, Z_TIMBER)
    D.box(hx - 0.004, hx + 0.004, y1, y1 + 0.03, hz - 0.004, hz + 0.004, Z_STEELBLK)
    part('IX_Door', 'hinge', ODOOR_PIV, (0, 0, -1), (0, 100), parent='HutOuthouse', states=['shut', 'open'],
         note='the outhouse door on the front, hung outside on strap hinges at its left (-x) edge; opens outward (+) to 100 deg; '
              'the heart cut in it is painted (dark, the vent)')
    socket('Hand_Door_Out', (hx, y0 - 0.08, hz), 'hand', parent='IX_Door', note='turn button outside')
    socket('Hand_Door_In', (hx, y1 + 0.06, hz), 'hand', parent='IX_Door', note='hook and eye inside')
    BOXES.append(('Out_Door', 'IX_Door', (x0, x1, y0, y1, zl, zh), None))


# ================================================================ HutFeeder (Futterraufe with a trough)
FW, FD = 0.80, 0.42                                  # half length (x), half depth (y) of the posts
F_EAVE, F_RIDGE = 1.62, 2.02


def build_feeder():
    k = reg('HutFeeder', 'YardWood', 'HutFeeder')
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.box(sx * FW - 0.05, sx * FW + 0.05, sy * FD - 0.05, sy * FD + 0.05, -0.25, F_EAVE + 0.02, Z_TIMBER)
    # the trough: a board box on two cross bearers
    for sx in (-1, 1):
        k.box(sx * FW - 0.06, sx * FW + 0.06, -FD - 0.05, FD + 0.05, 0.50, 0.56, Z_GREY)
    box6(k, (-FW + 0.06, -0.30, 0.56), (FW - 0.06, 0.30, 0.78), Z_GREY, skip=('+z',))
    face(k, [(-FW + 0.08, -0.28, 0.60), (FW - 0.08, -0.28, 0.60), (FW - 0.08, 0.28, 0.60), (-FW + 0.08, 0.28, 0.60)], Z_HAY, (0, 0, 1))
    for sy in (-1, 1):                                                # the trough's inner walls
        face(k, [(-FW + 0.08, sy * 0.28, 0.60), (FW - 0.08, sy * 0.28, 0.60), (FW - 0.08, sy * 0.28, 0.78), (-FW + 0.08, sy * 0.28, 0.78)],
             Z_GREY, (0, -sy, 0))
    # the V hay rack: slats from the trough edge up to the top rails, hay in the V
    for sy in (-1, 1):
        k.box(-FW + 0.05, FW - 0.05, sy * FD - 0.03, sy * FD + 0.03, 1.48, 1.54, Z_TIMBER)
        for i in range(9):
            x = -FW + 0.12 + i * (2 * FW - 0.24) / 8
            a, b = Vector((x, sy * 0.06, 0.80)), Vector((x, sy * (FD - 0.02), 1.50))
            k.strip([a, b], Vector((1, 0, 0)), 0.028, 0.022, Z_GREY)
    poly =[(-0.05, 0.86), (0.05, 0.86), (0.30, 1.30), (0.18, 1.42), (-0.20, 1.40), (-0.30, 1.28)]
    prism_x(k, poly, -FW + 0.10, FW - 0.10, Z_HAY, Z_HAY, [Z_HAY] * len(poly))
    # the gable roof of boards (ridge along x), a ridge board
    run = FD + 0.18
    for sy in (-1, 1):
        a = Vector((0, 0, F_RIDGE))
        b = Vector((0, sy * run, F_EAVE - 0.05))
        mid = (a + b) / 2
        d = (b - a).normalized()
        R = Matrix((Vector((1, 0, 0)), d, Vector((1, 0, 0)).cross(d) * (1 if sy > 0 else -1))).transposed()
        VM.obox(k, mid, (2 * FW + 0.30, (b - a).length, 0.025), Z_GREY, R)
        for sx in (-1, 1):                                            # rafters on the posts
            VM.obox(k, Vector((sx * FW, mid.y, mid.z - 0.04)), (0.05, (b - a).length, 0.06), Z_TIMBER, R)
    k.box(-FW - 0.15, FW + 0.15, -0.03, 0.03, F_RIDGE - 0.01, F_RIDGE + 0.05, Z_GREY)
    part('HutFeeder', 'static', (0, 0, 0), note='the game feeder (root): origin = the middle between its posts on the ground')
    socket('Slot_Trough', (0.0, 0.0, 0.62), 'slot', parent='HutFeeder', note='the trough floor (salt, maize)')
    BOXES.extend([('Feeder_Body', 'HutFeeder', (-FW - 0.06, FW + 0.06, -FD - 0.06, FD + 0.06, 0.0, 1.55), None),
                  ('Feeder_Roof', 'HutFeeder', (-FW - 0.15, FW + 0.15, -run, run, F_EAVE - 0.08, F_RIDGE + 0.05), None)])


# ================================================================ HutPolter (timber stack)
P_LEN = 4.0
LOGS = []                                            # (x_shift, y, z, r) centres in the y-z plane, logs along x


def _polter_layout():
    rows = [(6, 0.0), (5, 1.0), (4, 2.0)]
    LOGS.clear()
    i = 0
    for n, lev in rows:
        r0 = 0.17
        w = n * 2 * r0
        for j in range(n):
            r = r0 * (0.86 + 0.26 * hsh(i, 11))
            y = -w / 2 + r0 + j * 2 * r0
            z = 0.12 + r0 + lev * (2 * r0 * 0.87)
            LOGS.append((0.10 * (hsh(i, 12) - 0.5), y, z, r))
            i += 1


def build_polter():
    _polter_layout()
    k = reg('HutPolter', 'YardWood', 'HutPolter')
    seg = 10
    for sx in (-1, 1):                                                # two sleeper logs across, sunk a little
        k.cyl(Vector((sx * 1.3, -1.25, 0.06)), Vector((sx * 1.3, 1.25, 0.06)), 0.10, Z_BARK, 8, caps=False)
        for sy in (-1, 1):
            c = Vector((sx * 1.3, sy * 1.25, 0.06))
            pts = [c + Vector((math.cos(a) * 0.10, 0, math.sin(a) * 0.10)) for a in (TAU * t / 8 for t in range(8))]
            face(k, pts, Z_END, (0, sy, 0))
    for (dx, y, z, r) in LOGS:
        a, b = Vector((-P_LEN / 2 + dx, y, z)), Vector((P_LEN / 2 + dx, y, z))
        k.cyl(a, b, r, Z_BARK, seg, caps=False)
        for c, s in ((a, -1), (b, 1)):
            pts = [c + Vector((0, math.cos(t) * r, math.sin(t) * r)) for t in (TAU * i / seg for i in range(seg))]
            face(k, pts, Z_END, (s, 0, 0))
    # two stakes at the road end, holding the stack
    for sy in (-1.15, 1.15):
        k.box(-P_LEN / 2 - 0.12, -P_LEN / 2 - 0.04, sy - 0.04, sy + 0.04, -0.3, 1.1, Z_TIMBER)
    part('HutPolter', 'static', (0, 0, 0), note='the timber stack (root): origin = its middle on the ground; logs along x, the road '
                                                 'end (-x) carries the sprayed number 317')
    BOXES.append(('Polter', 'HutPolter', (-P_LEN / 2 - 0.12, P_LEN / 2 + 0.06, -1.20, 1.20, 0.0, 1.35), None))


# ================================================================ HutSign (pointer + battery lantern = the trail light)
S_POST_TOP = 2.25
S_BOARD = dict(x0=-0.10, x1=0.86, z0=1.60, z1=1.82, y0=-0.085, y1=-0.055)
LANT_C = Vector((0.0, -0.30, 1.98))                  # the lantern hangs from the bracket in front of the post


def build_sign():
    k = reg('HutSign', 'YardProps', 'HutSign')
    k.box(-0.045, 0.045, -0.045, 0.045, -0.30, S_POST_TOP, Z_SPOST)
    k.box(-0.06, 0.06, -0.06, 0.06, S_POST_TOP, S_POST_TOP + 0.025, Z_SPOST)                    # a cap board
    b = S_BOARD
    tip = b['x1'] + 0.12
    poly = [(b['x0'], b['z0']), (b['x1'], b['z0']), (tip, (b['z0'] + b['z1']) / 2), (b['x1'], b['z1']), (b['x0'], b['z1'])]
    prism_y(k, poly, b['y0'], b['y1'], Z_SBOARD, Z_SBOARD, [Z_SBOARD] * len(poly))
    for zz in (b['z0'] + 0.05, b['z1'] - 0.05):                        # two coach screws through to the post
        k.cyl(Vector((0.0, b['y0'] - 0.004, zz)), Vector((0.0, b['y0'], zz)), 0.010, Z_STEELBLK, 6)
    Sg = reg('Sign_Board', 'panel', 'HutSign')
    w = b['x1'] - b['x0'] - 0.04
    quad(Sg, Vector(((b['x0'] + b['x1']) / 2 + 0.01, b['y0'] - 0.0008, (b['z0'] + b['z1']) / 2)), (0, -1, 0), w, b['z1'] - b['z0'] - 0.03,
         uv('sign'))
    part('Sign_Board', 'static', ((b['x0'] + b['x1']) / 2, b['y0'], (b['z0'] + b['z1']) / 2), parent='HutSign',
         note='FORSTHÜTTE 100 m / FORESTER\'S HUT on the arrow board (panel atlas; German first, English under it)')
    # the lantern bracket: an L of flat steel from the post over the front, a hook
    k.box(-0.012, 0.012, -0.30, -0.045, 2.10, 2.13, Z_LWIRE)
    k.box(-0.012, 0.012, -0.065, -0.045, 1.95, 2.13, Z_LWIRE)
    k.cyl(Vector((0.0, LANT_C.y, 2.10)), Vector((0.0, LANT_C.y, LANT_C.z + 0.13)), 0.004, Z_LWIRE, 5)
    L = reg('Lamp_Lant', 'YardProps', 'HutSign')                       # battery lantern: base, yellow globe, cap, bail
    c = LANT_C
    L.cyl(c + Vector((0, 0, -0.10)), c + Vector((0, 0, -0.06)), 0.060, Z_LMETAL, 12)
    L.cyl(c + Vector((0, 0, 0.06)), c + Vector((0, 0, 0.09)), 0.052, Z_LMETAL, 12, r2=0.025)
    for a in (0, 120, 240):                                           # three wire guards round the globe
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        L.cyl(c + d * 0.050 + Vector((0, 0, -0.06)), c + d * 0.046 + Vector((0, 0, 0.06)), 0.003, Z_LWIRE, 4)
    L.tube([c + Vector((-0.05, 0, 0.09)), c + Vector((-0.04, 0, 0.13)), c + Vector((0, 0, 0.14)), c + Vector((0.04, 0, 0.13)),
            c + Vector((0.05, 0, 0.09))], 0.004, Z_LWIRE, 4, caps=False)
    part('Lamp_Lant', 'static', c, parent='HutSign', note='the battery lantern on its hook (yellow glass): its own part; the lens and '
                                                          'the halo are its children; the light LIGHT_Lant')
    Ln = reg('Lens_Lant', 'lens:lant', 'HutSign')
    Ln.lathe(c, (0, 0, 1), [(-0.06, 0.042), (-0.02, 0.050), (0.02, 0.050), (0.06, 0.040)], ZERO, 12, cap0=False, cap1=False)
    lathe_uv(Ln, c, -0.06, 0.06, uv('l_lant'), (0, 0, 1))
    part('Lens_Lant', 'static', c, parent='Lamp_Lant', note='the yellow glass globe: M_Yard_Lamp_Lant (lit) / M_Yard_Lamp_Lant_Off')
    Gw = reg('Glow_Lant', 'glow', 'HutSign')
    quad(Gw, c + Vector((0, -0.07, 0)), (0, -1, 0), 0.55, 0.55, uv('glow_warm'))
    quad(Gw, c + Vector((0.07, 0, 0)), (1, 0, 0), 0.55, 0.55, uv('glow_warm'))
    part('Glow_Lant', 'static', c, parent='Lamp_Lant', note='halo cards: additive, unlit; shown when the lantern is on')
    LAMPS.append(('Lant', c + Vector((0, 0, -0.01)), (0, 0, -1), 'lantern', (0, -1, 0)))
    part('HutSign', 'static', (0, 0, 0), note='the trail-head pointer (root): origin = the post\'s foot on the ground (sunk 0.30); the '
                                               'arrow points +x (to the trail), the text faces -y (the road)')
    BOXES.extend([('Sign_Post', 'HutSign', (-0.05, 0.05, -0.05, 0.05, 0.0, S_POST_TOP + 0.03), None),
                  ('Sign_Board', 'HutSign', (b['x0'], tip, b['y0'], b['y1'], b['z0'], b['z1']), None)])


def build_route_sign():
    """the station pointer at the road's forks (user 27.10, QUESTIONS_6 §7a 7): the trail-head pointer's post and arrow board
    without the lantern, OBSERVATORIUM over OBSERVATORY (German first); the arrow points +x along the road to the station"""
    k = reg('RouteSign', 'YardProps', 'RouteSign')
    k.box(-0.045, 0.045, -0.045, 0.045, -0.30, S_POST_TOP, Z_SPOST)
    k.box(-0.06, 0.06, -0.06, 0.06, S_POST_TOP, S_POST_TOP + 0.025, Z_SPOST)
    b = S_BOARD
    tip = b['x1'] + 0.12
    poly = [(b['x0'], b['z0']), (b['x1'], b['z0']), (tip, (b['z0'] + b['z1']) / 2), (b['x1'], b['z1']), (b['x0'], b['z1'])]
    prism_y(k, poly, b['y0'], b['y1'], Z_SBOARD, Z_SBOARD, [Z_SBOARD] * len(poly))
    for zz in (b['z0'] + 0.05, b['z1'] - 0.05):
        k.cyl(Vector((0.0, b['y0'] - 0.004, zz)), Vector((0.0, b['y0'], zz)), 0.010, Z_STEELBLK, 6)
    Sg = reg('Route_Board', 'panel', 'RouteSign')
    w = b['x1'] - b['x0'] - 0.04
    quad(Sg, Vector(((b['x0'] + b['x1']) / 2 + 0.01, b['y0'] - 0.0008, (b['z0'] + b['z1']) / 2)), (0, -1, 0), w, b['z1'] - b['z0'] - 0.03,
         uv('route'))
    part('Route_Board', 'static', ((b['x0'] + b['x1']) / 2, b['y0'], (b['z0'] + b['z1']) / 2), parent='RouteSign',
         note='OBSERVATORIUM / OBSERVATORY on the arrow board (panel atlas; German first, English under it)')
    part('RouteSign', 'static', (0, 0, 0), note='the station pointer at a fork (root): origin = the foot of the post on the ground (sunk '
                                                 '0.30); the arrow points +x (along the road to the station), the text faces -y (the road)')
    BOXES.extend([('Route_Post', 'RouteSign', (-0.05, 0.05, -0.05, 0.05, 0.0, S_POST_TOP + 0.03), None),
                  ('Route_BoardBox', 'RouteSign', (b['x0'], tip, b['y0'], b['y1'], b['z0'], b['z1']), None)])


def lathe_uv(k, c, h0, h1, rect, axis):
    """cylindrical UVs on every face of k (lens lathes)"""
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


# ================================================================ HutPorch (lean-to at the hut's door)
PW, PD = 1.20, 1.25                                  # half width (x), depth (y, toward -y from the facade)
P_DECK, P_WALL_Z, P_FRONT_Z = 0.32, 2.42, 2.12
DOOR_X = -0.38                                       # the hut door's middle (hut 1.0: hinges at -0.812, 0.86 wide)


def build_porch():
    k = reg('HutPorch', 'YardWood', 'HutPorch')
    for sx in (-1, 0, 1):                                             # stones and short posts under the deck
        for sy in (-0.10, -PD + 0.10):
            x = sx * (PW - 0.10)
            k.box(x - 0.12, x + 0.12, sy - 0.12, sy + 0.12, -0.10, 0.06, Z_STONE)
            k.box(x - 0.05, x + 0.05, sy - 0.05, sy + 0.05, 0.06, P_DECK - 0.03, Z_TIMBER)
    box6(k, (-PW, -PD, P_DECK - 0.12), (PW, 0.0, P_DECK - 0.03), Z_TIMBER, skip=('+y', '+z', '-z'))   # rim joists
    face(k, [(-PW, -PD, P_DECK), (PW, -PD, P_DECK), (PW, 0.0, P_DECK), (-PW, 0.0, P_DECK)], Z_GREY, (0, 0, 1))
    box6(k, (-PW, -PD, P_DECK - 0.03), (PW, 0.0, P_DECK), Z_GREY, skip=('+z', '+y'))
    box6(k, (DOOR_X - 0.50, -PD - 0.28, 0.12), (DOOR_X + 0.50, -PD, 0.16), Z_GREY)                    # the step, at the door
    for sx in (-1, 1):
        k.box(DOOR_X + sx * 0.45 - 0.03, DOOR_X + sx * 0.45 + 0.03, -PD - 0.26, -PD - 0.02, 0.0, 0.12, Z_TIMBER)
    for sx in (-1, 1):                                                # two posts, knee braces, the front beam
        x = sx * (PW - 0.06)
        k.box(x - 0.05, x + 0.05, -PD + 0.01, -PD + 0.11, P_DECK, P_FRONT_Z, Z_TIMBER)
        k.strip([Vector((x, -PD + 0.06, P_FRONT_Z - 0.40)), Vector((x - sx * 0.35, -PD + 0.06, P_FRONT_Z - 0.05))], Vector((0, 1, 0)),
                0.06, 0.06, Z_TIMBER)
    k.box(-PW - 0.10, PW + 0.10, -PD + 0.01, -PD + 0.11, P_FRONT_Z, P_FRONT_Z + 0.12, Z_TIMBER)
    k.box(-PW - 0.10, PW + 0.10, -0.06, 0.0, P_WALL_Z - 0.06, P_WALL_Z + 0.06, Z_TIMBER)                # the wall plate
    # the roof: rafters from the wall plate over the beam, the corrugated sheet, fascia
    yf = -PD - 0.30
    slope = (P_WALL_Z + 0.06 - (P_FRONT_Z + 0.12)) / (PD - 0.06)
    zr = lambda y: P_WALL_Z + 0.06 + slope * y                        # rafter bottom (y negative = out)
    for xr in (-PW, -0.40, 0.40, PW):
        poly = [(yf, zr(yf)), (0.0, zr(0.0)), (0.0, zr(0.0) + 0.09), (yf, zr(yf) + 0.09)]
        prism_x(k, poly, xr - 0.025, xr + 0.025, Z_TIMBER, Z_TIMBER, [Z_TIMBER, None, None, None])
    zt = lambda y: zr(y) + 0.09 + 0.03
    nrm = Vector((0, -slope, 1)).normalized()
    top = [Vector((-PW - 0.15, yf, zt(yf) + 0.02)), Vector((PW + 0.15, yf, zt(yf) + 0.02)), Vector((PW + 0.15, 0.0, zt(0.0) + 0.02)),
           Vector((-PW - 0.15, 0.0, zt(0.0) + 0.02))]
    bot = [p - Vector((0, 0, 0.02)) for p in top]
    face(k, top, Z_ROOF, nrm)
    face(k, bot, Z_ROOFUNDER, -nrm)
    box6(k, (-PW - 0.15, yf - 0.02, zr(yf) - 0.02), (PW + 0.15, yf, zt(yf) + 0.04), Z_TRIMW, skip=('+y',))
    # the bench on the right side, along y (the open hut door swings out on the left)
    bx0, bx1 = PW - 0.42, PW - 0.08
    box6(k, (bx0, -PD + 0.20, P_DECK + 0.42), (bx1, -0.20, P_DECK + 0.46), Z_GREY)
    for yy in (-PD + 0.28, -0.28):
        k.box(bx0 + 0.04, bx1 - 0.04, yy - 0.03, yy + 0.03, P_DECK, P_DECK + 0.42, Z_GREY)
    part('HutPorch', 'static', (0, 0, 0), note='the lean-to porch (root): origin = the middle of the hut\'s front on the ground; its '
                                                'back (+y, y = 0) goes against the facade; deck at 0.32 (the hut floor), the step at the '
                                                'door (x -0.38), a bench on the right')
    socket('Slot_PorchBench', ((bx0 + bx1) / 2, -PD / 2, P_DECK + 0.46), 'slot', parent='HutPorch', note='the bench top (a player waits here)')
    BOXES.extend([('Porch_Deck', 'HutPorch', (-PW, PW, -PD, 0.0, 0.0, P_DECK), None),
                  ('Porch_Step', 'HutPorch', (DOOR_X - 0.50, DOOR_X + 0.50, -PD - 0.28, -PD, 0.0, 0.16), None),
                  ('Porch_Post_L', 'HutPorch', (-PW + 0.01, -PW + 0.11, -PD + 0.01, -PD + 0.11, P_DECK, P_FRONT_Z), None),
                  ('Porch_Post_R', 'HutPorch', (PW - 0.11, PW - 0.01, -PD + 0.01, -PD + 0.11, P_DECK, P_FRONT_Z), None),
                  ('Porch_Bench', 'HutPorch', (bx0, bx1, -PD + 0.20, -0.20, P_DECK, P_DECK + 0.46), None),
                  ('Porch_Roof', 'HutPorch', (-PW - 0.15, PW + 0.15, yf, 0.0, P_FRONT_Z + 0.10, P_WALL_Z + 0.25), None)])


# ================================================================ HutMap (folded paper on the table)
MAP_W, MAP_H = 0.42, 0.30


def build_map():
    k = reg('HutMap', 'panel', 'HutMap')
    u0, v0, u1, v1 = uv('map')
    cols = 3
    for i in range(cols):                                             # three panels of the fold, the middle one lifted a little
        xc = -MAP_W / 2 + (i + 0.5) * MAP_W / cols
        ua, ub = u0 + (u1 - u0) * i / cols, u0 + (u1 - u0) * (i + 1) / cols
        quad(k, Vector((xc, 0.0, 0.003 if i == 1 else 0.0015)), (0, 0, 1), MAP_W / cols, MAP_H, (ua, v0, ub, v1), up=(0, 1, 0))
    part('HutMap', 'static', (0, 0, 0), note='the forester\'s map (root, panel atlas): origin = its middle on the table top; antenna '
                                              'No. 1 circled, a place in the woods crossed out (the cave hook)')
    BOXES.append(('Map', 'HutMap', (-MAP_W / 2, MAP_W / 2, -MAP_H / 2, MAP_H / 2, 0.0, 0.008), None))


def build_yard():
    outhouse_shell()
    outhouse_door()
    build_feeder()
    build_polter()
    build_sign()
    build_route_sign()
    build_porch()
    build_map()
