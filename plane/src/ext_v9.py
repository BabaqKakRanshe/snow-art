"""v9 cabin additions on top of v8 (out/plane_v8_final_v8.blend -> out/plane_v9.blend, out/ext_v9.json).
 - 4 folding side-facing troop seats in the cargo bay (2 per side, ahead of and behind the cargo doors):
   wall-mounted back (olive canvas laced between two aluminium rails, side brackets with the hinge pin) = static;
   PaxSeat_<L1|R1|L2|R2> = the seat pan (tube frame + laced canvas + lap belt + pull tab), pivot on the hinge pin,
   rest pose = down; PaxSeat_<..>_Leg = folding U-leg, pivot on the pan's front tube.
   Fold: pan about the model Y axis by sgn * 90 deg * fold (sgn +1 left, -1 right), leg relative by -sgn * 90 * fold.
 - stowage hardware: flashlight clips on the pilot door (PilotDoor_L_Clip), flare-gun holster on the right door
   (PilotDoor_R_Holster), shovel clips on the left barrier post, jerry-can bracket on the rear bulkhead, two floor
   anchors for the ladder straps; all M_Fittings (interior style, own 2K atlas).
 - survival kit, separate models (PSX texture M_Survival): SM_Surv_Bag (+ Surv_Bag_Strap), SM_Surv_Shovel,
   SM_Surv_FlareGun, SM_Surv_FlareShell, SM_Surv_Flare, SM_Surv_Flashlight; built around their pivot (the grip),
   local -Y = forward (Unity +Z), +Z = up; shown in the scene at their stow sockets.
Every new mesh carries face attributes fz (surface zone, ZONES) and isl (island) and metric UVs (geo9)."""
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as LY
from geo9 import MB, fillet, mirror_x_mesh, TAU

bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v8_final_v8.blend'))
O, MAT = bpy.data.objects, bpy.data.materials
ROOT = O['UtilityPlane']
INFO = {}

ZONES = dict(CANVAS=1, TUBE=3, STEEL=4, RUBBER=5, WEB_GREY=6, BUCKLE=7, LATCH=8, PATCH1=9, PATCH2=10, PATCH3=11,
             PATCH4=12, BLACK=13, HOLSTER=14, BUNGEE=15, ALU_SHEET=17, DRING=18, LACE=19,
             BAG=31, BAG_REFLECT=32, BAG_LABEL=33, BAG_ZIP=34, BAG_WEB=35, SHOVEL_BLADE=36, SHOVEL_SHAFT=37,
             SHOVEL_GRIP=38, GUN_BODY=39, GUN_DARK=40, FLARE_TUBE=41, FLARE_CAP=42, FLARE_LABEL=43, FLASH_BODY=44,
             FLASH_LENS=45, FLASH_RUBBER=46, SHELL_CASE=47, SHELL_BASE=48, STRAP_ORANGE=49, ITEM_STEEL=50,
             FLASH_KNURL=51, GUN_BORE=52, CARGO_STRAP=20)
Z = type('Z', (), ZONES)
PREVIEW = {1: (0.16, 0.18, 0.09), 3: (0.75, 0.76, 0.78), 4: (0.55, 0.56, 0.58), 5: (0.03, 0.03, 0.03), 6: (0.45, 0.46, 0.46),
           7: (0.9, 0.9, 0.9), 8: (0.6, 0.6, 0.6), 13: (0.02, 0.02, 0.02), 14: (0.03, 0.03, 0.03), 15: (0.05, 0.05, 0.05),
           17: (0.7, 0.71, 0.72), 18: (0.6, 0.6, 0.6), 19: (0.12, 0.13, 0.07), 20: (0.8, 0.30, 0.03)}


def mat(name, rgb, metal=0.0, rough=0.6):
    m = MAT.get(name) or MAT.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    return m


M_FIT = mat('M_Fittings', (0.20, 0.22, 0.12))
M_SURV = mat('M_Survival', (0.8, 0.25, 0.05))
CF = bpy.data.collections.new('Fittings_v9')
bpy.context.scene.collection.children.link(CF)
CS = bpy.data.collections.new('Survival_v9')
bpy.context.scene.collection.children.link(CS)

# ================================================================== constants (left side, build frame)
FLOOR = 1.074                       # top of the floor plates (ray-cast)
XW = 0.679                          # inner wall surface, z 1.45 .. 1.80
XH, ZH, RT = 0.612, 1.49, 0.011     # hinge pin axis (|x|, z), pan tube radius
DEPTH = 0.36
XF = XH - DEPTH                     # front tube axis
SY, BR = 0.205, 0.025               # side tubes at +-SY, front corner bend radius
RODY = 0.239                        # hinge rod half length (nuts outside the brackets)
BKY, BKT = 0.232, 0.006             # side bracket plane, thickness
XR, RR = 0.650, 0.011               # back rails axis |x|, radius
ZU, ZLB = 1.765, 1.535              # upper rail, lower back rail
RAILY = 0.236
LEGY, LOFF, RL = 0.167, 0.025, 0.010
SAG = 0.015
SEATS = {'L1': (1, -1.27, 1), 'R1': (-1, -1.27, 2), 'L2': (1, 0.86, 3), 'R2': (-1, 0.86, 4)}   # sgn, yc, digit
CANVAS_T = 0.002                    # half thickness of the canvas sheets


def canvas_z(x, y):
    """seat canvas mid-surface (left seat, y relative to the seat centre): edges at the tube centres, sagging"""
    u = (x - XF) / (XH - XF)
    w = math.sin(math.pi * min(max(u, 0.0), 1.0)) ** 0.7
    return ZH + 0.002 - SAG * (1 - (y / SY) ** 2) * w


def ring_strap(mb, c, axis, r, end, width=0.010, zone=None, segs=6, start_deg=0.0):
    """lacing loop: once round a tube (axis = unit vector of the tube, centre c, radius r), then to the point `end`"""
    ax = Vector(axis).normalized()
    ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    e1 = (ref - ax * ref.dot(ax)).normalized()
    e2 = ax.cross(e1)
    pts, sides = [], []
    rr = r + 0.0015
    for i in range(segs + 1):
        a = math.radians(start_deg) + TAU * i / segs
        pts.append(Vector(c) + (e1 * math.cos(a) + e2 * math.sin(a)) * rr)
        sides.append(ax)
    pts.append(Vector(end))
    sides.append(ax)
    mb.strap(pts, sides, width, 0.0016, zone=Z.LACE if zone is None else zone, ends=False, edges=False)


# ================================================================== seat: static wall part (left, at yc)
def seat_fixed(mb, yc):
    for s in (-1, 1):
        # side bracket plate in the x-z plane (holds the hinge pin and the lower back rail end)
        out = [(XW - 0.002, ZLB + 0.022), (XR - 0.014, ZLB + 0.022), (XR - 0.016, ZLB - 0.010)]
        for i in range(9):                                     # rounded nose around the pin, over the cabin side
            a = math.radians(90 + 180 * i / 8)
            out.append((XH + 0.021 * math.cos(a), ZH + 0.021 * math.sin(a)))
        out += [(XH + 0.006, ZH - 0.035), (XW - 0.002, ZH - 0.035)]
        mb.plate(Vector((0, yc + s * BKY - BKT / 2, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)), out, BKT, zone=Z.STEEL)
        mb.lathe((XH, yc + s * BKY - 0.0065, ZH), (0, 1, 0), [(0, 0.0175), (0.013, 0.0175)], segs=12, zone=Z.STEEL)
        mb.box((XW - 0.003, yc + s * BKY, (ZH + ZLB) / 2), (0.006, 0.040, 0.13), zone=Z.STEEL)        # wall flange
        for zr in (ZH - 0.045, ZLB + 0.040):
            mb.lathe((XW - 0.006, yc + s * (BKY + 0.012), zr), (-1, 0, 0), [(0, 0.0045), (0.002, 0.0035), (0.003, 0.0)],
                     segs=8, zone=Z.STEEL, cap1=False)
    for zr in (ZU, ZLB):
        mb.tube([(XR, yc - RAILY + 0.004, zr), (XR, yc + RAILY - 0.004, zr)], RR, segs=10, zone=Z.TUBE)
    for s in (-1, 1):                                          # upper rail standoffs + end caps
        mb.box(((XR + XW) / 2 + 0.002, yc + s * (RAILY + 0.004), ZU), (XW - XR + 0.004, 0.012, 0.030), zone=Z.STEEL)
        mb.lathe((XR, yc + s * (RAILY - 0.004), ZU), (0, s, 0), [(0, 0.0135), (0.009, 0.0135)], segs=10, zone=Z.STEEL)
    # back canvas between the rails, slight belly towards the cabin, laced to both rails
    z0, z1 = ZLB + RR + 0.016, ZU - RR - 0.016
    def back_mid(sv, tv):
        bell = 0.006 * math.sin(math.pi * (tv - z0) / (z1 - z0)) * (1 - (sv / 0.198) ** 2)
        return Vector((XR - bell, yc + sv, tv))
    ys = [-0.198 + 0.396 * i / 10 for i in range(11)]
    zs = [z0 + (z1 - z0) * j / 6 for j in range(7)]
    mb.slab(back_mid, lambda s_, t_: Vector((-1, 0, 0)), ys, zs, 2 * CANVAS_T, zone=Z.CANVAS)
    for zr, zc in ((ZU, z1), (ZLB, z0)):
        for ly in [-0.16 + 0.32 * i / 4 for i in range(5)]:
            ring_strap(mb, (XR, yc + ly, zr), (0, 1, 0), RR, back_mid(ly, zc), start_deg=-90 if zr == ZU else 90)


def seat_patch(mb, yc, digit_zone):
    """seat number patch sewn on the back canvas front (visible face = its bottom face, facing -x); left side"""
    z0, z1 = ZLB + RR + 0.016, ZU - RR - 0.016
    zp = (z0 + z1) / 2 + 0.01
    bell = 0.006 * math.sin(math.pi * (zp - z0) / (z1 - z0))
    xf = XR - bell - CANVAS_T - 0.0012
    mb.plate(Vector((xf, yc - 0.036, zp - 0.036)), Vector((0, 1, 0)), Vector((0, 0, 1)),
             [(0, 0), (0.072, 0), (0.072, 0.072), (0, 0.072)], 0.0012, zone=digit_zone)


# ================================================================== seat pan (moving), left, at yc; pivot (XH, yc, ZH)
def seat_pan(mb, yc):
    path = fillet([(XH, yc - SY, ZH), (XF, yc - SY, ZH), (XF, yc + SY, ZH), (XH, yc + SY, ZH)], BR, 4)
    mb.tube(path, RT, segs=10, zone=Z.TUBE, cap0=False, cap1=False)
    mb.tube([(XH, yc - RODY, ZH), (XH, yc + RODY, ZH)], RT, segs=10, zone=Z.TUBE)               # hinge rod
    for s in (-1, 1):
        mb.lathe((XH, yc + s * (BKY + 0.0065), ZH), (0, s, 0), [(0, 0.0135), (0.009, 0.0135), (0.011, 0.0115)],
                 segs=6, zone=Z.STEEL, phase=math.pi / 6)                                         # nuts
    xa, xb = XF + RT + 0.006, XH - RT - 0.006
    ya = SY - RT - 0.006
    xs = [xa + (xb - xa) * i / 8 for i in range(9)]
    ys = [-ya + 2 * ya * j / 8 for j in range(9)]
    mb.slab(lambda s_, t_: Vector((s_, yc + t_, canvas_z(s_, t_))), lambda s_, t_: Vector((0, 0, 1)), xs, ys,
            2 * CANVAS_T, zone=Z.CANVAS)
    for s in (-1, 1):                                          # lacing round the side tubes
        for lx in [xa + 0.04 + (xb - xa - 0.08) * i / 3 for i in range(4)]:
            ring_strap(mb, (lx, yc + s * SY, ZH), (1, 0, 0), RT, (lx, yc + s * ya, canvas_z(lx, s * ya)),
                       start_deg=-90 * s)
    for xc, xe in ((XF, xa), (XH, xb)):                        # ... round the front tube and the hinge rod
        for ly in [-0.11 + 0.22 * i / 2 for i in range(3)]:
            ring_strap(mb, (xc, yc + ly, ZH), (0, 1, 0), RT, (xe, yc + ly, canvas_z(xe, ly)),
                       start_deg=0 if xc == XH else 180)
    # lap belt: two grey webbing halves anchored on the hinge rod, lying on the canvas; buckle / latch plate
    for s, ytip, kind in ((1, 0.030, 'buckle'), (-1, -0.030, 'latch')):
        y_a = s * 0.140
        pts = []
        for i in range(7):                                     # round the rod from below, over the top, to the cabin
            a = math.radians(-100 + 190 * i / 6)
            pts.append(Vector((XH + math.cos(a) * (RT + 0.0022), yc + y_a, ZH + math.sin(a) * (RT + 0.0022))))
        x_end = XH - (0.205 if kind == 'buckle' else 0.190)
        n = 8
        for i in range(1, n + 1):
            f = i / n
            x = XH - 0.02 - (XH - 0.02 - x_end) * f
            y = y_a + (ytip - y_a) * (f ** 1.3)
            pts.append(Vector((x, yc + y, canvas_z(x, y) + CANVAS_T + 0.0012)))
        mb.strap(pts, [Vector((0, 1, 0))] * len(pts), 0.046, 0.0018, zone=Z.WEB_GREY)
        d = (pts[-1] - pts[-2]).normalized()
        R = Matrix((d, Vector((0, 0, 1)).cross(d).normalized(), Vector((0, 0, 1)))).transposed()
        tip = pts[-1]
        if kind == 'buckle':
            mb.box(tip + d * 0.032 + Vector((0, 0, 0.004)), (0.070, 0.052, 0.009), rot=R, zone=Z.BUCKLE)
            mb.box(tip + d * 0.036 + Vector((0, 0, 0.0095)), (0.052, 0.044, 0.003), rot=R, zone=Z.BUCKLE)
        else:
            mb.box(tip + d * 0.026 + Vector((0, 0, 0.0015)), (0.056, 0.036, 0.003), rot=R, zone=Z.LATCH)
    # pull tab: webbing loop round the front tube, hanging in front of it
    c = Vector((XF, yc, ZH))
    pts = []
    for i in range(6):
        a = math.radians(90 + 180 * i / 5)
        pts.append(c + Vector((math.cos(a) * (RT + 0.002), 0, math.sin(a) * (RT + 0.002))))
    pts += [c + Vector((-0.008, 0, -0.030)), c + Vector((-0.006, 0, -0.052)), c + Vector((0.004, 0, -0.054)),
            c + Vector((0.006, 0, -0.032)), c + Vector((0.004, 0, -RT - 0.004))]
    mb.strap(pts, [Vector((0, 1, 0))] * len(pts), 0.024, 0.0018, zone=Z.WEB_GREY)


def seat_leg(mb, yc):
    """U leg, rest = vertical; the tubes stand LOFF inboard of the front tube axis so they fold flat under the pan"""
    xl = XF - LOFF
    ztop, zfoot = ZH - 0.014, FLOOR + 0.015
    for s in (-1, 1):
        y = yc + s * LEGY
        mb.tube([(xl, y, ztop), (xl, y, zfoot)], RL, segs=8, zone=Z.TUBE, cap0=True, cap1=False)
        mb.lathe((xl, y, zfoot), (0, 0, -1), [(0, 0.0125), (0.010, 0.0135), (0.015, 0.011)], segs=10, zone=Z.RUBBER)
        mb.lathe((XF, y - 0.012, ZH), (0, 1, 0), [(0, 0.0165), (0.024, 0.0165)], segs=10, zone=Z.STEEL)     # knuckle
        mb.box((XF - LOFF / 2 - 0.002, y, ZH - 0.017), (LOFF + 0.012, 0.020, 0.020), zone=Z.STEEL)
    mb.tube([(xl, yc - LEGY + 0.006, 1.23), (xl, yc + LEGY - 0.006, 1.23)], 0.008, segs=8, zone=Z.TUBE)


def master(fn, name):
    mb = MB()
    fn(mb, 0.0)
    ob = mb.to_object(name, CF, [M_FIT])
    me = ob.data
    bpy.data.objects.remove(ob)
    return me


ME_FIX, ME_PAN, ME_LEG = master(seat_fixed, 'm_fixed'), master(seat_pan, 'm_pan'), master(seat_leg, 'm_leg')


def instance(me_master, name, sgn, yc, pivot=None):
    """copy of a master mesh at the seat (mirrored for the right side: geometry and winding mirrored, UVs kept
    identical, so all four seats share the same atlas islands)"""
    me = me_master.copy()
    me.name = name
    M = Matrix.Translation((0.0, yc, 0.0))
    if sgn < 0:
        M = M @ Matrix.Scale(-1, 4, Vector((1, 0, 0)))
    me.transform(M)
    if sgn < 0:
        me.flip_normals()
    ob = bpy.data.objects.new(name, me)
    CF.objects.link(ob)
    if pivot is not None:
        me.transform(Matrix.Translation(-pivot))
        ob.matrix_world = Matrix.Translation(pivot)
    return ob


seat_objs = {}
statics = []
for tag, (sgn, yc, digit) in SEATS.items():
    statics.append(instance(ME_FIX, f'Fittings_{tag}', sgn, yc))
    pt = MB()
    seat_patch(pt, yc, getattr(Z, f'PATCH{digit}'))
    po = pt.to_object(f'Patch_{tag}', CF, [M_FIT])
    if sgn < 0:
        mirror_x_mesh(po.data)                   # patch: own island, kept non-mirrored so the digit reads
    statics.append(po)
    pan = instance(ME_PAN, f'PaxSeat_{tag}', sgn, yc, Vector((sgn * XH, yc, ZH)))
    leg = instance(ME_LEG, f'PaxSeat_{tag}_Leg', sgn, yc, Vector((sgn * XF, yc, ZH)))
    leg.parent = pan
    leg.matrix_parent_inverse = pan.matrix_world.inverted()
    pan.parent = ROOT
    pan.matrix_parent_inverse = ROOT.matrix_world.inverted()
    seat_objs[tag] = (pan, leg)
for me in (ME_FIX, ME_PAN, ME_LEG):
    bpy.data.meshes.remove(me)

# ================================================================== stowage hardware (world coordinates)
hw = MB()
POST_X, POST_FACE = 0.250, -1.697                              # left barrier post, bay face
SHOVEL_AX = Vector((POST_X, POST_FACE + 0.026, 0.0))
for zc in (1.60, 1.86):
    hw.box((POST_X, POST_FACE + 0.004, zc), (0.040, 0.008, 0.034), zone=Z.BLACK)            # clamp plate
    hw.box((POST_X, POST_FACE + 0.0085, zc), (0.012, 0.004, 0.020), zone=Z.BLACK)
    pts = []
    r = 0.0185
    for i in range(11):                                         # C spring round the shaft, open towards the bay
        a = math.radians(-90 - 145 + 290 * i / 10)
        pts.append(Vector((SHOVEL_AX.x + math.cos(a) * r, SHOVEL_AX.y + math.sin(a) * r, zc)))
    hw.strap(pts, [Vector((0, 0, 1))] * len(pts), 0.016, 0.0025, zone=Z.BLACK)
# jerry-can bracket on the rear bulkhead: a wall-mounted box (tray, lip, side walls, back plate) 52 mm off the floor,
# clear of the tie-down ring Socket_TieDown_13 (4.6 cm) under it, the rail and the floor/wall cove in the corner
JC = dict(x0=0.220, x1=0.580, yb=1.288, depth=0.205, z0=FLOOR + 0.052)
yf = JC['yb'] - JC['depth']
xm = (JC['x0'] + JC['x1']) / 2
ZJ = JC['z0']
hw.box((xm, (yf + JC['yb']) / 2, ZJ + 0.0025), (JC['x1'] - JC['x0'], JC['depth'], 0.005), zone=Z.ALU_SHEET)
hw.box((xm, yf + 0.003, ZJ + 0.020), (JC['x1'] - JC['x0'], 0.004, 0.036), zone=Z.ALU_SHEET)
for xs_ in (JC['x0'], JC['x1']):
    hw.box((xs_, (yf + JC['yb']) / 2, ZJ + 0.06), (0.004, JC['depth'], 0.12), zone=Z.ALU_SHEET)
hw.box((xm, JC['yb'] - 0.002, ZJ + 0.20), (JC['x1'] - JC['x0'], 0.004, 0.40), zone=Z.ALU_SHEET)
for xs_ in (JC['x0'] + 0.03, JC['x1'] - 0.03):
    for zr in (ZJ + 0.06, ZJ + 0.36):
        hw.lathe((xs_, JC['yb'] - 0.004, zr), (0, -1, 0), [(0, 0.004), (0.002, 0.003), (0.0028, 0.0)], segs=8,
                 zone=Z.STEEL, cap1=False)
zb = ZJ + 0.33
for xs_, s in ((JC['x0'], -1), (JC['x1'], 1)):
    hw.lathe((xs_ + s * 0.002, yf + 0.012, zb), (s, 0, 0), [(0, 0.006), (0.010, 0.006)], segs=8, zone=Z.STEEL)
bung = [(JC['x0'] + 0.012, yf + 0.004, zb), (JC['x0'] + 0.08, yf - 0.006, zb - 0.004), (xm, yf - 0.010, zb - 0.006),
        (JC['x1'] - 0.08, yf - 0.006, zb - 0.004), (JC['x1'] - 0.012, yf + 0.004, zb)]
hw.tube(fillet(bung, 0.03, 3), 0.0045, segs=6, zone=Z.BUNGEE)
# wall anchors for the ladder straps on the right kick panel (between seat R1 and the cargo door, and aft of it);
# the kick panel leans in: x 0.639 at z 1.15 .. 0.658 at z 1.25
LADDER_ANCHORS = [Vector((-0.6505, -1.000, 1.200)), Vector((-0.6505, 0.555, 1.200))]
kick = Euler((0.0, -math.atan2(0.019, 0.10), 0.0)).to_matrix()    # plate parallel to the kick panel (right side)
for a in LADDER_ANCHORS:
    hw.box(a + Vector((0.003, 0, 0)), (0.006, 0.050, 0.060), rot=kick, zone=Z.STEEL)
    for dz in (-0.020, 0.020):
        hw.lathe(a + Vector((0.0, 0.0, dz)), (1, 0, 0), [(0, 0.004), (0.002, 0.003), (0.003, 0.0)], segs=8,
                 zone=Z.STEEL, cap1=False)
    ring = [a + Vector((0.006 + 0.020 * math.sin(math.radians(t)), -0.016 * math.cos(math.radians(t)), -0.004))
            for t in range(0, 181, 30)]
    hw.tube(ring, 0.003, segs=6, zone=Z.DRING)
hwo = hw.to_object('Fittings_Stow', CF, [M_FIT])

# flashlight clips on the pilot door panel (child of PilotDoor_L); the light's head points aft
FL_AX = dict(x=0.640, z=1.475, y_tail=-2.880, y_head=-2.610)
cl = MB()
for yc_ in (-2.835, -2.715):
    cl.box((0.671, yc_, FL_AX['z']), (0.008, 0.030, 0.034), zone=Z.BLACK)
    cl.box((0.6635, yc_, FL_AX['z']), (0.009, 0.012, 0.016), zone=Z.BLACK)
    pts = []
    r = 0.0205
    for i in range(11):
        a = math.radians(-140 + 280 * i / 10)                  # C open towards the cabin (-x)
        pts.append(Vector((FL_AX['x'] + math.cos(a) * r, yc_, FL_AX['z'] + math.sin(a) * r)))
    cl.strap(pts, [Vector((0, 1, 0))] * len(pts), 0.014, 0.0025, zone=Z.BLACK)
clip = cl.to_object('PilotDoor_L_Clip', CF, [M_FIT])

# holster on the right door panel (child of PilotDoor_R): vertical nylon sleeve, muzzle down, grip up and aft,
# retention strap with a snap across the frame
HO = dict(x_panel=-0.677, yc=-2.842, z0=1.430, z1=1.615, hy=0.040, hx=0.024)
ho = MB()


def sleeve(s_, t_):
    z = HO['z0'] + (HO['z1'] - HO['z0']) * s_
    taper = 0.80 + 0.20 * min(1.0, s_ * 1.6)
    a = TAU * t_
    cx, cy = math.cos(a), math.sin(a)
    px = abs(cx) ** 0.4 * math.copysign(1, cx)
    py = abs(cy) ** 0.4 * math.copysign(1, cy)
    return Vector((HO['x_panel'] + HO['hx'] + px * HO['hx'] * taper, HO['yc'] + py * HO['hy'] * taper, z))


def sleeve_axis(s_):
    return Vector((HO['x_panel'] + HO['hx'], HO['yc'], HO['z0'] + (HO['z1'] - HO['z0']) * s_))


ho.grid(sleeve, [i / 6 for i in range(7)], [j / 16 for j in range(16)], zone=Z.HOLSTER, closed_t=True,
        outward=lambda p, s, t: p - sleeve_axis(s))
ho.fan(sleeve_axis(0.0) + Vector((0, 0, -0.010)), [sleeve(0.0, j / 16) for j in range(16)], Vector((0, 0, -1)),
       zone=Z.HOLSTER)
# back plate (bolted to the door panel) and the retention strap over the gun frame with a snap
ho.box((HO['x_panel'] + 0.002, HO['yc'], (HO['z0'] + HO['z1']) / 2 + 0.01), (0.004, 2 * HO['hy'] + 0.016,
       HO['z1'] - HO['z0'] + 0.04), zone=Z.HOLSTER)
zs_ = HO['z1'] + 0.028
strap_pts = [Vector((HO['x_panel'] + 0.004, HO['yc'] - HO['hy'] - 0.004, zs_)),
             Vector((HO['x_panel'] + 0.045, HO['yc'] - HO['hy'] + 0.002, zs_)),
             Vector((HO['x_panel'] + 0.052, HO['yc'], zs_)),
             Vector((HO['x_panel'] + 0.045, HO['yc'] + HO['hy'] - 0.002, zs_)),
             Vector((HO['x_panel'] + 0.004, HO['yc'] + HO['hy'] + 0.004, zs_))]
_sp = fillet(strap_pts, 0.012, 3)
ho.strap(_sp, [Vector((0, 0, 1))] * len(_sp), 0.020, 0.0025, zone=Z.HOLSTER)
ho.lathe((HO['x_panel'] + 0.0535, HO['yc'], zs_), (1, 0, 0), [(0, 0.0065), (0.003, 0.0055), (0.004, 0.0)], segs=10,
         zone=Z.STEEL, cap1=False)
holster = ho.to_object('PilotDoor_R_Holster', CF, [M_FIT])
for ob, door in ((clip, 'PilotDoor_L'), (holster, 'PilotDoor_R')):
    ob.parent = O[door]
    ob.matrix_parent_inverse = O[door].matrix_world.inverted()

# join the static cabin fittings
bpy.ops.object.select_all(action='DESELECT')
for ob in statics + [hwo]:
    ob.select_set(True)
bpy.context.view_layer.objects.active = statics[0]
bpy.ops.object.join()
fit = bpy.context.view_layer.objects.active
fit.name = fit.data.name = 'Cabin_Fittings'
fit.parent = ROOT
fit.matrix_parent_inverse = ROOT.matrix_world.inverted()


# ================================================================== survival kit (local frames: pivot = grip)
def flashlight():
    mb = MB()
    y_t = 0.135                                                 # tail at +y, lens at -y (forward)
    mb.lathe((0, y_t, 0), (0, -1, 0), [(0, 0.0), (0.001, 0.0150), (0.004, 0.0185), (0.020, 0.0185), (0.022, 0.0190)],
             segs=14, zone=Z.FLASH_BODY, cap0=False, cap1=False)
    mb.lathe((0, y_t - 0.022, 0), (0, -1, 0), [(0, 0.0190), (0.148, 0.0190)], segs=14, zone=Z.FLASH_KNURL,
             cap0=False, cap1=False)
    mb.lathe((0, y_t - 0.170, 0), (0, -1, 0), [(0, 0.0190), (0.035, 0.0262), (0.085, 0.0275), (0.092, 0.0280),
                                               (0.098, 0.0270), (0.0985, 0.0236)], segs=14, zone=Z.FLASH_BODY,
             cap0=False, cap1=False)
    mb.lathe((0, y_t - 0.2665, 0), (0, -1, 0), [(0, 0.0237), (0.0003, 0.0237)], segs=14, zone=Z.FLASH_LENS,
             cap0=False, cap1=True)
    mb.lathe((0, y_t - 0.150, 0.0185), (0, 0, 1), [(0, 0.0075), (0.004, 0.0072), (0.0065, 0.005), (0.0075, 0.0)],
             segs=10, zone=Z.FLASH_RUBBER, cap1=False)
    ring = [Vector((0.0, y_t + 0.002 + 0.008 * (1 - math.cos(math.radians(d))), 0.008 * math.sin(math.radians(d))))
            for d in range(0, 361, 45)]
    mb.tube(ring, 0.0016, segs=6, zone=Z.ITEM_STEEL, cap0=False, cap1=False)
    return mb.to_object('SM_Surv_Flashlight', CS, [M_SURV]), dict(light=[0, y_t - 0.2668, 0], length=0.27)


def flare():
    mb = MB()
    y_b = 0.055                                                 # handle bottom; burning end forward (-y)
    mb.lathe((0, y_b, 0), (0, -1, 0), [(0, 0.0), (0.0015, 0.0150), (0.004, 0.0170), (0.100, 0.0170), (0.104, 0.0186)],
             segs=12, zone=Z.FLARE_CAP, cap0=False, cap1=False)
    mb.lathe((0, y_b - 0.104, 0), (0, -1, 0), [(0, 0.0186), (0.006, 0.0176), (0.180, 0.0176)], segs=12,
             zone=Z.FLARE_TUBE, cap0=False, cap1=False)
    mb.lathe((0, y_b - 0.122, 0), (0, -1, 0), [(0, 0.0179), (0.07, 0.0179)], segs=12, zone=Z.FLARE_LABEL,
             cap0=False, cap1=False)
    mb.lathe((0, y_b - 0.284, 0), (0, -1, 0), [(0, 0.0190), (0.040, 0.0190), (0.043, 0.0165), (0.044, 0.0)],
             segs=12, zone=Z.FLARE_CAP, cap0=True, cap1=False)
    for k in range(3):
        mb.lathe((0, y_b - 0.020 - 0.025 * k, 0), (0, -1, 0), [(0, 0.0172), (0.004, 0.0182), (0.008, 0.0172)], segs=12,
                 zone=Z.FLARE_CAP, cap0=False, cap1=False)
    return mb.to_object('SM_Surv_Flare', CS, [M_SURV]), dict(flame=[0, y_b - 0.328, 0], length=0.383)


def flare_shell():
    mb = MB()
    y_b = 0.050
    mb.lathe((0, y_b, 0), (0, -1, 0), [(0, 0.0), (0.0005, 0.0150), (0.0035, 0.0155), (0.0045, 0.0140), (0.012, 0.0140)],
             segs=12, zone=Z.SHELL_BASE, cap0=False, cap1=False)
    mb.lathe((0, y_b - 0.012, 0), (0, -1, 0), [(0, 0.0134), (0.080, 0.0134), (0.090, 0.0105), (0.098, 0.004),
                                                (0.099, 0.0)], segs=12, zone=Z.SHELL_CASE, cap0=False, cap1=False)
    return mb.to_object('SM_Surv_FlareShell', CS, [M_SURV]), dict(length=0.100, calibre_mm=26.5)


def flare_gun():
    mb = MB()
    zb = 0.050                                                  # bore axis above the grip pivot
    yb0, yb1 = -0.010, -0.170
    mb.lathe((0, yb0, zb), (0, -1, 0), [(0, 0.0195), (0.140, 0.0185), (0.150, 0.0200), (0.160, 0.0200)], segs=14,
             zone=Z.GUN_BODY, cap0=True, cap1=False)
    mb.lathe((0, yb1, zb), (0, 1, 0), [(0, 0.0200), (0.0001, 0.0140)], segs=14, zone=Z.GUN_BODY, cap0=False,
             cap1=False)
    mb.lathe((0, yb1 + 0.0001, zb), (0, 1, 0), [(0, 0.0140), (0.06, 0.0140)], segs=14, zone=Z.GUN_BORE, cap0=False,
             cap1=True)
    mb.box((0, 0.020, zb - 0.002), (0.034, 0.060, 0.044), zone=Z.GUN_BODY)
    mb.box((0, 0.004, zb + 0.020), (0.028, 0.030, 0.008), zone=Z.GUN_DARK)                     # barrel latch
    mb.box((0, 0.048, zb + 0.012), (0.012, 0.018, 0.020), rot=Euler((math.radians(-25), 0, 0)).to_matrix(),
           zone=Z.GUN_DARK)                                                                    # hammer
    rk = math.radians(15)

    def grip(s_, t_):
        a = TAU * t_
        h = 0.105 * s_
        cy = 0.026 + h * math.sin(rk)
        cz = zb - 0.020 - h * math.cos(rk)
        hx, hy = 0.0165, 0.022 + 0.004 * math.sin(math.pi * s_)
        return Vector((hx * math.cos(a), cy + hy * math.sin(a) * math.cos(rk), cz + hy * math.sin(a) * math.sin(rk)))

    def grip_axis(s_):
        h = 0.105 * s_
        return Vector((0, 0.026 + h * math.sin(rk), zb - 0.020 - h * math.cos(rk)))

    mb.grid(grip, [i / 6 for i in range(7)], [j / 12 for j in range(12)], zone=Z.GUN_BODY, closed_t=True,
            outward=lambda p, s, t: p - grip_axis(s))
    mb.fan(grip_axis(1.0) + Vector((0, 0.0013, -0.005)), [grip(1.0, j / 12) for j in range(12)],
           Vector((0, math.sin(rk), -math.cos(rk))), zone=Z.GUN_BODY)
    guard = fillet([(0, 0.008, zb - 0.022), (0, -0.040, zb - 0.030), (0, -0.040, zb - 0.052), (0, 0.000, zb - 0.058),
                    (0, 0.022, zb - 0.045)], 0.010, 3)
    mb.tube(guard, 0.0035, segs=6, zone=Z.GUN_BODY)
    mb.box((0, -0.006, zb - 0.036), (0.006, 0.006, 0.022), rot=Euler((math.radians(12), 0, 0)).to_matrix(),
           zone=Z.GUN_DARK)
    return mb.to_object('SM_Surv_FlareGun', CS, [M_SURV]), dict(muzzle=[0, yb1, zb], breech=[0, yb0, zb], length=0.23)


def shovel():
    mb = MB()
    gw = 0.110                                                  # D-grip bar at the pivot; blade towards -y
    mb.tube([(-gw / 2 + 0.004, 0, 0), (gw / 2 - 0.004, 0, 0)], 0.0145, segs=10, zone=Z.SHOVEL_GRIP)
    dpath = fillet([(-gw / 2, 0.0, 0), (-gw / 2, -0.045, 0), (-0.016, -0.090, 0), (0.016, -0.090, 0), (gw / 2, -0.045, 0),
                    (gw / 2, 0.0, 0)], 0.018, 4)
    mb.tube(dpath, 0.0085, segs=8, zone=Z.SHOVEL_GRIP)
    mb.lathe((0, -0.090, 0), (0, -1, 0), [(0, 0.0185), (0.040, 0.0170)], segs=10, zone=Z.SHOVEL_GRIP, cap1=False)
    mb.tube([(0, -0.125, 0), (0, -0.600, 0)], 0.0158, segs=10, zone=Z.SHOVEL_SHAFT, cap0=False, cap1=False)
    mb.lathe((0, -0.585, 0), (0, -1, 0), [(0, 0.0175), (0.050, 0.0185), (0.060, 0.0)], segs=10, zone=Z.SHOVEL_BLADE,
             cap0=True, cap1=False)
    bw, bl, dep, y0 = 0.250, 0.290, 0.030, -0.610

    def blade(s_, t_):
        x = (t_ - 0.5) * bw
        tip = 1.0 - 0.10 * max(0.0, s_ - 0.75) / 0.25 * (abs(2 * t_ - 1) ** 2)
        return Vector((x * tip, y0 - s_ * bl, dep * (2 * t_ - 1) ** 2 - dep + 0.004 * s_))

    def blade_n(s_, t_):
        e = 1e-3
        a = blade(min(s_ + e, 1), t_) - blade(max(s_ - e, 0), t_)
        b = blade(s_, min(t_ + e, 1)) - blade(s_, max(t_ - e, 0))
        n = b.cross(a).normalized()
        return n if n.z > 0 else -n

    S = [i / 8 for i in range(9)]
    T = [j / 10 for j in range(11)]
    mb.slab(blade, blade_n, S, T, 0.0024, zone=Z.SHOVEL_BLADE)
    for tt_ in (0.0, 1.0):                                      # rolled side lips
        mb.tube([blade(s_, tt_) + Vector((0, 0, 0.002)) for s_ in S], 0.0032, segs=6, zone=Z.SHOVEL_BLADE)
    mb.box((0, y0 - 0.020, 0.008), (0.050, 0.050, 0.012), zone=Z.SHOVEL_BLADE)                # shaft socket
    return mb.to_object('SM_Surv_Shovel', CS, [M_SURV]), dict(blade_tip=[0, y0 - bl, 0], length=0.915)


def bag():
    mb = MB()
    L, W, H = 0.50, 0.28, 0.26
    zc = -0.295 + H / 2

    def body(s_, t_):
        y = (0.5 - s_) * L * 0.96
        a = TAU * t_
        e = 0.22
        cx, cz = math.cos(a), math.sin(a)
        px = abs(cx) ** e * math.copysign(1, cx)
        pz = abs(cz) ** e * math.copysign(1, cz)
        end = 1.0 - 0.06 * (abs(2 * s_ - 1) ** 6)
        return Vector((px * W / 2 * end, y, zc + pz * H / 2 * end))

    axis = lambda p, s, t: p - Vector((0, p.y, zc))
    S = [i / 10 for i in range(11)]
    T = [j / 24 for j in range(24)]
    mb.grid(body, S, T, zone=Z.BAG, closed_t=True, outward=axis)
    for s_, sgn in ((0.0, 1), (1.0, -1)):                       # domed end panels
        ring = [body(s_, j / 24) for j in range(24)]
        c = sum(ring, Vector()) / 24 + Vector((0, sgn * 0.014, 0))
        mb.fan(c, ring, Vector((0, sgn, 0)), zone=Z.BAG, smooth=True)
    for yb in (0.17, -0.17):                                    # reflective bands
        s_b = 0.5 - yb / (L * 0.96)
        mb.grid(lambda s_, t_: body(s_, t_) + (body(s_, t_) - Vector((0, body(s_, t_).y, zc))).normalized() * 0.002,
                [s_b - 0.04, s_b + 0.04], T, zone=Z.BAG_REFLECT, closed_t=True, outward=axis)
    ztop = zc + H / 2
    mb.box((0, 0, ztop + 0.001), (0.022, L * 0.86, 0.004), zone=Z.BAG_ZIP)
    mb.box((0.015, -0.16, ztop + 0.004), (0.010, 0.030, 0.005), zone=Z.ITEM_STEEL)
    mb.plate(Vector((W / 2 + 0.0004, 0.07, zc - 0.045)), Vector((0, -1, 0)), Vector((0, 0, 1)),
             [(0, 0), (0.14, 0), (0.14, 0.09), (0, 0.09)], 0.002, zone=Z.BAG_LABEL)
    for s in (-1, 1):                                           # carry handles over the top to the grip
        pts = []
        for i in range(9):
            f = i / 8
            a = math.radians(-10 + 100 * min(1.0, f * 1.25))
            x = s * (W / 2 * math.cos(a) + 0.003) * (1 - 0.9 * f ** 2)
            z = zc + (H / 2 + 0.003) * math.sin(a) + 0.034 * f ** 3
            pts.append(Vector((x, 0, z)))
        mb.strap(pts, [Vector((0, 1, 0))] * len(pts), 0.038, 0.0025, zone=Z.BAG_WEB)
    mb.lathe((0, 0.060, 0), (0, -1, 0), [(0, 0.016), (0.120, 0.016)], segs=10, zone=Z.BAG_WEB)            # grip wrap
    for s in (-1, 1):                                           # end handles
        y = s * (L * 0.48 + 0.004)
        loop = [(-0.045, y, zc + 0.03), (-0.040, y + s * 0.018, zc + 0.045), (0.0, y + s * 0.024, zc + 0.05),
                (0.040, y + s * 0.018, zc + 0.045), (0.045, y, zc + 0.03)]
        mb.strap(loop, [Vector((0, 0, 1))] * 5, 0.030, 0.0025, zone=Z.BAG_WEB)
    ob = mb.to_object('SM_Surv_Bag', CS, [M_SURV])
    sm = MB()                                                   # strap shown when secured (CargoItem.securedMarker)
    pts = []
    for j in range(25):
        p = body(0.5, j / 24)
        pts.append(p + (p - Vector((0, p.y, zc))).normalized() * 0.005)
    sm.strap(pts, [Vector((0, 1, 0))] * len(pts), 0.032, 0.002, zone=Z.STRAP_ORANGE, ends=False)
    tail = [body(0.5, 0.75) + Vector((0.0, 0, -0.005)), Vector((0.0, 0.0, -0.293)), Vector((0.0, -0.06, -0.294)),
            Vector((0.0, -0.11, -0.294))]                       # 3 mm over the bag bottom: never in the floor
    sm.strap(tail, [Vector((1, 0, 0))] * 4, 0.032, 0.002, zone=Z.STRAP_ORANGE)
    sm.box((0.0, -0.040, -0.286), (0.040, 0.045, 0.012), zone=Z.ITEM_STEEL)
    sm.box((0.0, -0.120, -0.290), (0.028, 0.020, 0.006), zone=Z.ITEM_STEEL)
    so = sm.to_object('Surv_Bag_Strap', CS, [M_SURV])
    so.parent = ob
    return ob, dict(bottom=[0, 0, -0.295], size=[W, L, H])


ITEMS = {}
for fn in (flashlight, flare, flare_shell, flare_gun, shovel, bag):
    ob, info = fn()
    ITEMS[ob.name] = info


# ================================================================== stow poses -> sockets
def basis(fwd, up):
    """rotation whose local -Y = fwd and +Z = up (items: -Y forward = Unity +Z, +Z up = Unity +Y)"""
    f = Vector(fwd).normalized()
    u = Vector(up)
    u = (u - f * u.dot(f)).normalized()
    y = -f
    x = y.cross(u)
    return Matrix((x, y, u)).transposed()


STOW = {}
STOW['Flashlight'] = dict(parent='PilotDoor_L', item='SM_Surv_Flashlight',
                          pos=Vector((FL_AX['x'], (FL_AX['y_tail'] + FL_AX['y_head']) / 2, FL_AX['z'])),
                          rot=basis((0, 1, 0), (0, 0, 1)))
STOW['FlareGun'] = dict(parent='PilotDoor_R', item='SM_Surv_FlareGun',
                        pos=Vector((HO['x_panel'] + HO['hx'], HO['yc'] + 0.044, HO['z1'] + 0.005)),
                        rot=basis((0, 0, -1), (0, -1, 0)))
STOW['Shovel'] = dict(parent='Cockpit', item='SM_Surv_Shovel', pos=Vector((SHOVEL_AX.x, SHOVEL_AX.y, 2.025)),
                      rot=basis((0, 0, -1), (0, -1, 0)))          # scoop towards the post, convex back to the bay
STOW['SurvivalBag'] = dict(parent='Cockpit', item='SM_Surv_Bag', pos=Vector((0.405, -1.14, FLOOR + 0.305)),
                           rot=basis((0, -1, 0), (0, 0, 1)))
STOW['JerryCan'] = dict(parent='Cockpit', item='SM_Kit_JerryCan',
                        pos=Vector((xm, JC['yb'] - 0.006 - 0.0945, ZJ + 0.005)), rot=basis((0, -1, 0), (0, 0, 1)))
# ladder: rear legs folded (-38 deg about its X), laid on its back (rear legs down) on the right half of the floor,
# feet forward. Stow pose = the ladder root (pivot on the ground under the platform centre) in plane space.
lad, legs = O['src_StepLadder'], O['Ladder_RearLegs']
L0 = lad.matrix_world.inverted()
piv_l = (L0 @ legs.matrix_world).translation
fold_l = Matrix.Translation(piv_l) @ Matrix.Rotation(math.radians(-38), 4, 'X') @ Matrix.Translation(-piv_l)
lad_pts = [L0 @ (lad.matrix_world @ v.co) for v in lad.data.vertices] + \
          [fold_l @ (L0 @ (legs.matrix_world @ v.co)) for v in legs.data.vertices]
ALPHA = math.atan2(0.546, 1.56)                                # stile lean from the vertical (feet -> platform front)
R_lad = Matrix.Rotation(ALPHA - math.pi / 2, 3, 'X')          # stile direction -> +y (top aft), rear legs -> down
rp = [R_lad @ p for p in lad_pts]
mn = Vector([min(p[i] for p in rp) for i in range(3)])
mx = Vector([max(p[i] for p in rp) for i in range(3)])
LAD_X1 = XF - LOFF - RL - 0.007                                # 7 mm clear of the left seats' legs
LAD_Y0 = -1.420                                                # 2 cm aft: clear of the folded R1 leg
LAD_LIFT = 0.059                                               # on battens: clear of the rails (6 mm), rings (4.6 cm)
lad_pos = Vector((LAD_X1 - mx.x, LAD_Y0 - mn.y, FLOOR - mn.z + LAD_LIFT))
STOW['Ladder'] = dict(parent='Cockpit', item='SM_StepLadder', pos=lad_pos, rot=R_lad, fold_rear_legs_deg=-38.0)
lad_box = dict(min=[round(c, 4) for c in (lad_pos + mn)], max=[round(c, 4) for c in (lad_pos + mx)])
INFO['ladder_stowed_box'] = lad_box
print('ladder stowed box', lad_box, 'size', [round(c, 3) for c in (mx - mn)], flush=True)
# straps over the stowed ladder (Stow_LadderStraps, hidden unless the ladder is stowed): floor rings x +0.42 ->
# over the ladder -> wall anchors on the right kick panel
world_lad = [lad_pos + p for p in rp]
_lt = [(lad, None), (legs, fold_l)]
_V, _F = [], []
for _o, _fm in _lt:
    _off = len(_V)
    for v in _o.data.vertices:
        q = L0 @ (_o.matrix_world @ v.co)
        if _fm is not None:
            q = _fm @ q
        _V.append(lad_pos + R_lad @ q)
    _F += [tuple(_off + i for i in p.vertices) for p in _o.data.polygons]
LBVH = BVHTree.FromPolygons(_V, _F)
st = MB()
for ring_y, anc in ((-0.80, LADDER_ANCHORS[0]), (0.50, LADDER_ANCHORS[1])):
    p_ring = Vector((0.42, ring_y, FLOOR + 0.010))
    p_anc = anc + Vector((0.016, 0.0, -0.004))
    ys_ = (ring_y + anc.y) / 2
    zh = []
    for k in range(41):
        x = lad_pos.x + mn.x + (mx.x - mn.x) * k / 40
        for dy in (-0.03, 0.0, 0.03):
            h = LBVH.ray_cast(Vector((x, ys_ + dy, 2.5)), Vector((0, 0, -1)), 2.0)
            if h[0] is not None:
                zh.append(h[0].z)
    ztop = max(zh) + 0.004
    xl, xr = lad_pos.x + mx.x + 0.004, lad_pos.x + mn.x - 0.004
    pts = [p_ring, Vector((xl, ring_y + (anc.y - ring_y) * 0.30, ztop)),
           Vector((xr, ring_y + (anc.y - ring_y) * 0.70, ztop)), p_anc]
    path = fillet(pts, 0.015, 3)
    side = []
    for i in range(len(path)):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        side.append(Vector((0, 0, 1)).cross(t).normalized() if abs(t.z) < 0.9 else Vector((0, 1, 0)))
    st.strap(path, side, 0.038, 0.002, zone=Z.CARGO_STRAP)
    mid = (pts[1] + pts[2]) / 2
    st.box(mid + Vector((0, 0, 0.008)), (0.050, 0.055, 0.014), zone=Z.STEEL)               # cam buckle on top
# two rubber battens under the ladder's support lines (rear-leg hinge line, stile feet), across the rails (6 mm) and
# between the ring rows; shown with the straps. x: from the right floor cove to the left stile
for _y0, _y1 in ((0.15, 0.65), (-1.45, -1.0)):
    _q = [v for v in _V if _y0 < v.y < _y1]
    _zt = min(v.z for v in _q)
    _yc = sum(v.y for v in _q if v.z < _zt + 0.004) / len([v for v in _q if v.z < _zt + 0.004])
    assert min(abs(_yc - ry) for ry in (-1.45, -0.80, -0.15, 0.50, 1.10)) > 0.07, ('batten over a ring row', _yc)
    _zb = FLOOR + 0.0065
    st.box((-0.175, _yc, (_zb + _zt - 0.001) / 2), (0.76, 0.06, _zt - 0.001 - _zb), zone=Z.RUBBER)
    print('ladder batten at y %.3f, %.3f .. %.3f' % (_yc, _zb, _zt - 0.001), flush=True)
straps = st.to_object('Stow_LadderStraps', CF, [M_FIT])
straps.parent = ROOT
straps.matrix_parent_inverse = ROOT.matrix_world.inverted()
bpy.context.view_layer.update()
for k, s in STOW.items():
    ob = O.get(s['item'])
    if s['item'] == 'SM_StepLadder':
        continue
    if ob is None:
        continue
    ob.matrix_world = Matrix.Translation(s['pos']) @ s['rot'].to_4x4()
    if s['parent'] != 'Cockpit':
        par = O[s['parent']]
        mw = ob.matrix_world.copy()
        ob.parent = par
        ob.matrix_parent_inverse = par.matrix_world.inverted()
        ob.matrix_world = mw
for n in ('SM_Surv_Flare', 'SM_Surv_FlareShell'):          # they ride in the bag: not shown in the cabin
    O[n].hide_render = O[n].hide_viewport = True

SOCK9 = {}


def sock(name, pos, parent='Sockets', rot=None):
    SOCK9[name] = dict(pos=[round(float(c), 5) for c in pos], parent=parent,
                       rot=[[round(float(c), 6) for c in row] for row in (rot if rot is not None else Matrix.Identity(3))])


for tag, (sgn, yc, digit) in SEATS.items():
    face = basis((-sgn, 0, 0), (0, 0, 1))
    sock(f'Socket_Seat_Pax{tag}', (sgn * 0.495, yc, 1.505), 'Sockets', face)
    sock(f'Socket_PaxEye_{tag}', (sgn * 0.475, yc, 2.295), 'Sockets', face)
    sock(f'Socket_PaxExit_{tag}', (0.0, -0.70 if yc < 0 else 0.30, FLOOR + 0.002), 'Sockets', face)
for k, s in STOW.items():
    sock(f'Socket_Stow_{k}', s['pos'], s['parent'], s['rot'])
# horror: apparition points (feet on the floor / ground, +Z Unity = where the figure looks) and window face points
gz = LY.ground_z
fwd, aft = basis((0, -1, 0), (0, 0, 1)), basis((0, 1, 0), (0, 0, 1))
sock('Socket_Scare_Bay_Aft', (0.0, 1.12, FLOOR), 'Sockets', fwd)
sock('Socket_Scare_Bay_Fwd', (0.0, -1.56, FLOOR), 'Sockets', fwd)
WIN = {'Pilot': LY.W1[0], 'Side': LY.W2[0], 'Cargo': LY.CARGO_WIN[0], 'Aft': LY.W4[0]}
for wn, poly in WIN.items():
    yc_ = sum(p[0] for p in poly) / len(poly)
    zc_ = sum(p[1] for p in poly) / len(poly)
    for sg_, sd in ((1, 'L'), (-1, 'R')):
        sock(f'Socket_Scare_Window_{wn}_{sd}', (sg_ * 1.10, yc_, zc_), 'Sockets', basis((-sg_, 0, 0), (0, 0, 1)))
sock('Socket_Scare_Windshield', (0.0, -3.62, 2.33), 'Sockets', aft)
sock('Socket_Scare_Nose', (0.0, -7.30, gz(-7.30)), 'Sockets', aft)
sock('Socket_Scare_Tail', (0.0, 6.40, gz(6.40)), 'Sockets', fwd)
for sg_, sd in ((1, 'L'), (-1, 'R')):
    sock(f'Socket_Scare_UnderWing_{sd}', (sg_ * 4.20, -2.20, gz(-2.20)), 'Sockets', basis((-sg_, 0, 0), (0, 0, 1)))
sock('Socket_Scare_Belly', (0.0, -1.20, gz(-1.20)), 'Sockets', fwd)
AUD = {'Socket_Audio_Radio': (0.0, -2.30, 2.578), 'Socket_Audio_Headset_P': (0.25, -1.775, 2.05),
       'Socket_Audio_Headset_C': (-0.25, -1.775, 2.05), 'Socket_Audio_StallHorn': (0.60, -2.62, 2.45),
       'Socket_Audio_Bay': (0.0, -0.20, 2.30), 'Socket_Audio_Roof': (0.0, -1.50, 2.80),
       'Socket_Audio_Belly': (0.0, -0.60, 0.92), 'Socket_Audio_ELT': (0.0, 2.70, 1.80),
       'Socket_Audio_Wind_L': (0.72, -2.00, 2.40), 'Socket_Audio_Wind_R': (-0.72, -2.00, 2.40),
       'Socket_Audio_FuelTank_L': (1.80, -1.95, 2.72), 'Socket_Audio_FuelTank_R': (-1.80, -1.95, 2.72)}
for k, p in AUD.items():
    sock(k, p, 'Sockets')

# ================================================================== checks
dg = bpy.context.evaluated_depsgraph_get()


def bvh(objs):
    vs, fs = [], []
    for o in objs:
        me = o.evaluated_get(dg).to_mesh()
        off = len(vs)
        vs += [o.matrix_world @ v.co for v in me.vertices]
        fs += [tuple(off + i for i in p.vertices) for p in me.polygons]
        o.evaluated_get(dg).to_mesh_clear()
    return BVHTree.FromPolygons(vs, fs)


CABIN = [o for o in O if o.type == 'MESH' and (o.name.startswith('CP_') or o.name == 'src_Fuselage')]
CAB = bvh(CABIN)
rep = {}
for tag, (pan, leg) in seat_objs.items():
    rep[tag] = dict(pan_x_cabin=len(bvh([pan]).overlap(CAB)), leg_x_cabin=len(bvh([leg]).overlap(CAB)))
rep['fittings_x_cabin'] = len(bvh([fit]).overlap(CAB))
print('CHECKS', json.dumps(rep), flush=True)
tris = {}
for ob in list(CF.objects) + list(CS.objects):
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    tris[ob.name] = len(me.loop_triangles)
    ob.evaluated_get(dg).to_mesh_clear()
print('TRIS', json.dumps(tris), flush=True)


def _js(o):
    if isinstance(o, Vector):
        return [round(c, 5) for c in o]
    if isinstance(o, Matrix):
        return [[round(c, 6) for c in row] for row in o]
    if isinstance(o, dict):
        return {k: _js(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_js(v) for v in o]
    if isinstance(o, float):
        return round(o, 5)
    return o


INFO.update(zones=ZONES, preview=PREVIEW, seats={k: dict(sgn=s, yc=y, digit=d) for k, (s, y, d) in SEATS.items()},
            seat=dict(XW=XW, XH=XH, ZH=ZH, RT=RT, DEPTH=DEPTH, XF=XF, SY=SY, LEGY=LEGY, LOFF=LOFF, FLOOR=FLOOR, XR=XR,
                      ZU=ZU, ZLB=ZLB, SAG=SAG, RODY=RODY, BKY=BKY),
            sockets=SOCK9, items=ITEMS, stow={k: dict(parent=v['parent'], item=v['item']) for k, v in STOW.items()},
            jerry=JC, holster=HO, flashlight_axis=FL_AX, ladder_anchors=LADDER_ANCHORS, shovel_axis=SHOVEL_AX,
            checks=rep, tris=tris)
json.dump(_js(INFO), open(os.path.join(HERE, 'out', 'ext_v9.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v9.blend'))
print('saved plane_v9.blend', flush=True)
