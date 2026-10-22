"""Build the utility aircraft geometry. Output: out/plane_geo.blend
Axes: Blender Z up, nose toward -Y, port (left) side = +X. Units: meters. Ground at Z=0."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(__file__))
from lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
sc = reset_scene()
C_SRC = coll('Aircraft')

# ------------------------------------------------------------------ materials (placeholders; shade.py builds nodes)
MAT_COLORS = {
    'src_Livery': (0.45, 0.04, 0.035), 'src_Struts': (0.03, 0.03, 0.03), 'src_InteriorA': (0.12, 0.13, 0.11),
    'src_GearPaint': (0.03, 0.03, 0.03), 'src_Rubber': (0.015, 0.015, 0.015), 'src_Hub': (0.06, 0.06, 0.06),
    'src_PropBlade': (0.02, 0.02, 0.02), 'src_Spinner': (0.02, 0.18, 0.13), 'src_MetalDark': (0.05, 0.05, 0.05),
    'src_InteriorD': (0.12, 0.13, 0.11), 'src_CaseGreen': (0.10, 0.16, 0.06), 'src_CaseYellow': (0.55, 0.36, 0.05),
    'src_CaseDark': (0.03, 0.04, 0.045), 'src_CaseTeal': (0.03, 0.08, 0.08), 'src_Antenna': (0.02, 0.02, 0.02),
    'M_Lights': (1.0, 0.02, 0.01),
}
M = {}
for k, c in MAT_COLORS.items():
    m = bpy.data.materials.new(k)
    m.diffuse_color = (*c, 1)
    M[k] = m

root = empty('UtilityPlane', C_SRC, size=1.0, kind='ARROWS')

# ================================================================== FUSELAGE
# (y, z_bottom, z_top, half_width, superellipse exponent)
ST = [
    (-4.62, 1.46, 2.10, 0.34, 3.0),
    (-4.55, 1.30, 2.16, 0.48, 3.6),
    (-4.40, 1.18, 2.20, 0.58, 4.5),
    (-4.00, 1.08, 2.24, 0.65, 5.5),
    (-3.35, 1.00, 2.28, 0.70, 6.0),
    (-3.25, 0.99, 2.33, 0.71, 6.5),
    (-2.90, 0.97, 2.50, 0.73, 7.0),
    (-2.58, 0.96, 2.66, 0.74, 7.0),
    (-1.00, 0.96, 2.66, 0.74, 7.0),
    (-0.90, 0.96, 2.66, 0.74, 7.0),
    (0.50, 0.96, 2.66, 0.74, 7.0),
    (0.60, 0.96, 2.66, 0.74, 7.0),
    (1.10, 0.97, 2.66, 0.74, 7.0),
]
_a = (1.50, 1.05, 2.645, 0.715, 6.5)
_b = (5.05, 2.14, 2.38, 0.08, 3.5)
for _y in (1.50, 2.3, 3.1, 3.9, 4.6, 5.05):
    _t = (_y - _a[0]) / (_b[0] - _a[0])
    ST.append(tuple([_y] + [_a[i] + (_b[i] - _a[i]) * _t for i in range(1, 5)]))
NR = 40


def fus_ring(st):
    y, zb, zt, hw, n = st
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    return [Vector((x, y, zc + z)) for x, z in superellipse(hw, hh, n, NR)]


bm = bmesh.new()
loft(bm, [fus_ring(s) for s in ST], closed=True, cap0=True, cap1=True, mat=0)
fix_normals(bm)
fus = obj_from_bm('src_Fuselage', bm, C_SRC, [M['src_Livery'], M['src_InteriorA']])

# --- cargo door opening (port side, +X): boolean pocket then remove the pocket back wall
DOOR_Y0, DOOR_Y1, DOOR_Z0, DOOR_Z1 = -0.85, 0.45, 1.10, 2.44
POCKET_X = 0.62
bm = bmesh.new()
box(bm, ((POCKET_X + 1.2) / 2, (DOOR_Y0 + DOOR_Y1) / 2, (DOOR_Z0 + DOOR_Z1) / 2),
    (1.2 - POCKET_X, DOOR_Y1 - DOOR_Y0, DOOR_Z1 - DOOR_Z0), mat=0, bevel=0.07, bevel_segs=3)
# only keep the bevel on the Y/Z corners: flatten X of verts so the inner wall is planar
for v in bm.verts:
    v.co.x = POCKET_X if v.co.x < (POCKET_X + 1.2) / 2 else 1.2
fix_normals(bm)
cutter = obj_from_bm('cutter', bm, C_SRC)
mod = fus.modifiers.new('door', 'BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.solver = 'EXACT'
mod.object = cutter
dg = bpy.context.evaluated_depsgraph_get()
me_new = bpy.data.meshes.new_from_object(fus.evaluated_get(dg))
fus.modifiers.clear()
old = fus.data
fus.data = me_new
me_new.name = 'src_Fuselage'
bpy.data.meshes.remove(old)
bpy.data.objects.remove(cutter)
fus.data.materials.clear()
fus.data.materials.append(M['src_Livery'])
fus.data.materials.append(M['src_InteriorA'])

bm = bmesh.new()
bm.from_mesh(fus.data)
kill = []
for f in bm.faces:
    c = f.calc_center_median()
    inside_door = (DOOR_Y0 - 0.01 < c.y < DOOR_Y1 + 0.01) and (DOOR_Z0 - 0.01 < c.z < DOOR_Z1 + 0.01)
    if inside_door and abs(c.x - POCKET_X) < 0.003 and f.normal.x > 0.9:
        kill.append(f)
    elif inside_door and POCKET_X - 0.01 < c.x < 0.735 and abs(f.normal.x) < 0.5:
        f.material_index = 1  # jamb
    else:
        f.material_index = 0
bmesh.ops.delete(bm, geom=kill, context='FACES')
bm.to_mesh(fus.data)
bm.free()
shade(fus, 42)
print('fuselage faces', len(fus.data.polygons))

# ================================================================== WING (box to 72 % chord) + trailing pieces
W_LE, W_CH = -2.55, 2.10
W_Z0, DIH = 2.648, math.radians(2.0)
W_M, W_P, W_T = 0.02, 0.4, 0.13
H_BOX, H_CS = 0.715, 0.73


def wz(x):
    return W_Z0 + max(0.0, abs(x) - 0.76) * math.tan(DIH)


def wing_ring(x, a, b, n, front, scale_t=1.0, chord=W_CH, le=W_LE):
    ring2 = airfoil_ring(a, b, n, W_M, W_P, W_T * scale_t, front)
    z0 = wz(x)
    return [Vector((x, le + xc * chord, z0 + yc * chord)) for xc, yc in ring2]


def wing_surface_z(x, xc, upper=True):
    u, l = naca(W_M, W_P, W_T, xc)
    return wz(x) + (u[1] if upper else l[1]) * W_CH


NB = 14
xs_box = [-7.0, -6.82, -5.3, -3.86, -2.3, -0.76, 0.0, 0.76, 2.3, 3.86, 5.3, 6.82, 7.0]
rings = [wing_ring(-7.07, 0, H_BOX, NB, True, 0.55, W_CH * 0.97, W_LE + 0.03)]
rings += [wing_ring(x, 0, H_BOX, NB, True) for x in xs_box]
rings += [wing_ring(7.07, 0, H_BOX, NB, True, 0.55, W_CH * 0.97, W_LE + 0.03)]
bm = bmesh.new()
loft(bm, rings, True, True, True)
fix_normals(bm)
wing = obj_from_bm('src_Wing', bm, C_SRC, [M['src_Livery']])
shade(wing, 35)


def te_piece(name, x0, x1, n=6, extra=()):
    bm = bmesh.new()
    xs = [x0] + list(extra) + [x1]
    if x0 < 0 < x1 and 0 not in xs:
        xs = [x0, 0.0, x1]
    loft(bm, [wing_ring(x, H_CS, 1.0, n, False) for x in xs], True, True, True)
    fix_normals(bm)
    ob = obj_from_bm(name, bm, C_SRC, [M['src_Livery']])
    shade(ob, 35)
    return ob


te_center = te_piece('src_WingTE_Center', -0.76, 0.76)
te_tipL = te_piece('src_WingTE_TipL', 6.84, 7.0)
te_tipR = te_piece('src_WingTE_TipR', -7.0, -6.84)
cs = {}
for side, sgn in (('L', 1), ('R', -1)):
    for nm, a, b in (('Flap', 0.80, 3.84), ('Aileron', 3.88, 6.80)):
        x0, x1 = sorted((sgn * a, sgn * b))
        ob = te_piece(f'{nm}_{side}', x0, x1)
        hx = sgn * a
        hinge_xc = H_CS
        u, l = naca(W_M, W_P, W_T, hinge_xc)
        pivot = (hx, W_LE + hinge_xc * W_CH, wz(hx) + (u[1] + l[1]) / 2 * W_CH)
        set_pivot(ob, pivot, (0, -sgn * DIH, 0))
        cs[f'{nm}_{side}'] = ob

# ================================================================== STRUTS
bm = bmesh.new()
for sgn in (1, -1):
    xw = 3.4 * sgn
    yw = -1.75
    zw = wing_surface_z(xw, (yw - W_LE) / W_CH, upper=False) + 0.01
    p0 = Vector((0.70 * sgn, -1.55, 1.10))
    p1 = Vector((xw, yw, zw))
    path = [p0.lerp(p1, t) for t in (0, 0.04, 0.5, 0.96, 1)]
    sweep(bm, path, lambda u: 0.075 if u in (0, 1) else 0.065, lambda u: 0.03 if u in (0, 1) else 0.022, 12)
    # end fittings
    box(bm, p0 + Vector((0.02 * sgn, 0, 0.0)), (0.08, 0.12, 0.08), bevel=0.01, bevel_segs=1)
    box(bm, p1 + Vector((0, 0, 0.02)), (0.1, 0.14, 0.05), bevel=0.01, bevel_segs=1)
fix_normals(bm)
struts = obj_from_bm('src_Struts', bm, C_SRC, [M['src_Struts']])
shade(struts, 40)

# ================================================================== TAIL
# Fin + rudder: full chord at root/tip, split at hinge y=4.60
FIN = [  # (z, le_y, te_y)
    (2.36, 3.22, 5.08),
    (2.60, 3.47, 5.07),
    (3.82, 4.12, 4.98),
]
HINGE_Y = 4.60
FIN_T = 0.11


def fin_ring(z, le, te, a, b, n, front, tscale=1.0):
    ch = te - le
    ring2 = airfoil_ring(a, b, n, 0, 0, FIN_T * tscale, front)
    return [Vector((yc * ch, le + xc * ch, z)) for xc, yc in ring2]


bm = bmesh.new()
rings = []
for z, le, te in FIN:
    h = (HINGE_Y - 0.012 - le) / (te - le)
    rings.append(fin_ring(z, le, te, 0, h, 12, True))
# rounded top
z, le, te = 3.90, 4.26, 4.98
h = (HINGE_Y - 0.012 - le) / (te - le)
rings.append(fin_ring(z, le, te, 0, h, 12, True, 0.6))
loft(bm, rings, True, True, True)
fix_normals(bm)
fin = obj_from_bm('src_Fin', bm, C_SRC, [M['src_Livery']])
shade(fin, 35)

bm = bmesh.new()
rings = []
for z, le, te in [(2.44, 3.30, 5.08), (3.82, 4.12, 4.98), (3.895, 4.26, 4.97)]:
    h = (HINGE_Y + 0.004 - le) / (te - le)
    rings.append(fin_ring(z, le, te, h, 1.0, 6, False, 1.0 if z < 3.85 else 0.6))
loft(bm, rings, True, True, True)
fix_normals(bm)
rudder = obj_from_bm('Rudder', bm, C_SRC, [M['src_Livery']])
shade(rudder, 35)
set_pivot(rudder, (0, HINGE_Y, 2.44))

# Horizontal stabilizer + elevators (hinge y = 4.74)
STAB_Z, E_HINGE = 2.06, 4.74
STAB_T = 0.10


def stab_ring(x, le, te, a, b, n, front, tscale=1.0):
    ch = te - le
    ring2 = airfoil_ring(a, b, n, 0, 0, STAB_T * tscale, front)
    return [Vector((x, le + xc * ch, STAB_Z + yc * ch)) for xc, yc in ring2]


def stab_chord(x):
    ax = abs(x)
    le = 3.95 + (4.17 - 3.95) * ax / 2.5
    te = 5.08 + (4.95 - 5.08) * ax / 2.5
    return le, te


bm = bmesh.new()
rings = []
xs = [-2.56, -2.5, -1.2, 0.0, 1.2, 2.5, 2.56]
for x in xs:
    le, te = stab_chord(min(abs(x), 2.5))
    if abs(x) > 2.5:
        le += 0.05
        te -= 0.03
    h = (E_HINGE - 0.012 - le) / (te - le)
    rings.append(stab_ring(x, le, te, 0, h, 12, True, 0.6 if abs(x) > 2.5 else 1.0))
loft(bm, rings, True, True, True)
fix_normals(bm)
stab = obj_from_bm('src_Stabilizer', bm, C_SRC, [M['src_Livery']])
shade(stab, 35)

for side, sgn in (('L', 1), ('R', -1)):
    bm = bmesh.new()
    rings = []
    for x in (0.17, 1.3, 2.5, 2.555):
        le, te = stab_chord(min(x, 2.5))
        if x > 2.5:
            le += 0.05
            te -= 0.03
        h = (E_HINGE + 0.004 - le) / (te - le)
        r = stab_ring(sgn * x, le, te, h, 1.0, 6, False, 0.6 if x > 2.5 else 1.0)
        rings.append(r)
    if sgn < 0:
        rings = rings[::-1]
    loft(bm, rings, True, True, True)
    fix_normals(bm)
    ob = obj_from_bm(f'Elevator_{side}', bm, C_SRC, [M['src_Livery']])
    shade(ob, 35)
    set_pivot(ob, (sgn * 1.35, E_HINGE, STAB_Z))
    cs[f'Elevator_{side}'] = ob

# ================================================================== COWL DETAILS: intake + exhausts
bm = bmesh.new()
intake_rings = []
for y, hw, hh, z in ((-4.63, 0.19, 0.075, 1.43), (-4.58, 0.215, 0.095, 1.425), (-4.46, 0.215, 0.09, 1.40),
                     (-4.30, 0.19, 0.07, 1.33)):
    intake_rings.append([Vector((x, y, z + zz)) for x, zz in superellipse(hw, hh, 3.0, 20)])
# inner duct going back into the cowl (reverse direction) -> hollow look
inner = [[Vector((v.x * 0.78, -4.63, 1.43 + (v.z - 1.43) * 0.6)) for v in intake_rings[0]],
         [Vector((v.x * 0.78, -4.52, 1.43 + (v.z - 1.43) * 0.6)) for v in intake_rings[0]]]
loft(bm, [inner[1], inner[0]] + intake_rings, True, True, True)
fix_normals(bm)
# exhaust stacks
for sgn in (1, -1):
    path = bezier((0.46 * sgn, -4.12, 1.70), (0.74 * sgn, -4.10, 1.70), (0.80 * sgn, -3.80, 1.66), 7)
    t = (path[-1] - path[-2]).normalized()
    rings_r = [0.078] * len(path)
    rings = []
    for k, p in enumerate(path):
        tng = (path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)])
        s, u = ring_frame(p, tng)
        rings.append([p + s * (0.085 * math.cos(a)) + u * (0.07 * math.sin(a)) for a in
                      (2 * PI * i / 14 for i in range(14))])
    pe = path[-1]
    s, u = ring_frame(pe, t)
    for fac, back in ((0.8, 0.0), (0.8, 0.12)):
        c = pe - t * back
        rings.append([c + s * (0.085 * fac * math.cos(a)) + u * (0.07 * fac * math.sin(a)) for a in
                      (2 * PI * i / 14 for i in range(14))])
    loft(bm, rings, True, True, True)
fix_normals(bm)
cowl_det = obj_from_bm('src_CowlDetails', bm, C_SRC, [M['src_MetalDark']])
shade(cowl_det, 45)

# ================================================================== PROPELLER (blades + spinner + hub)
P_C = Vector((0, -4.74, 1.79))  # prop disc center
bm = bmesh.new()
# spinner (revolve around Y). a = y coordinate, r = radius
prof = []
L, R0, ybase = 0.46, 0.265, -4.61
for i in range(11):
    u = i / 10
    r = R0 * (1 - u ** 1.9) ** 0.72
    prof.append((ybase - u * L, r))
prof = prof[::-1]  # tip -> base
prof.append((ybase + 0.0001, 0.0))  # back plate
revolve(bm, [(a, r) for a, r in prof], 'Y', (0, 0, P_C.z), segs=28, mat=1)
# blades
B_ST = [  # (r, chord, twist deg, thickness ratio)
    (0.14, 0.085, 62, 0.55), (0.24, 0.13, 55, 0.30), (0.40, 0.21, 44, 0.14), (0.62, 0.235, 33, 0.10),
    (0.85, 0.22, 26, 0.085), (1.05, 0.19, 21, 0.075), (1.20, 0.155, 18, 0.07), (1.29, 0.10, 16, 0.07),
    (1.32, 0.05, 16, 0.06)]
for k in range(3):
    phi = 2 * PI * k / 3
    d = Vector((math.sin(phi), 0, math.cos(phi)))
    tv = Vector((math.cos(phi), 0, -math.sin(phi)))
    av = Vector((0, -1, 0))
    rings = []
    for r, ch, tw, th in B_ST:
        b = math.radians(tw)
        cvec = tv * math.cos(b) + av * math.sin(b)
        nvec = -tv * math.sin(b) + av * math.cos(b)
        ring2 = airfoil_ring(0, 1, 9, 0.04 if th < 0.3 else 0.0, 0.4, th, True)[:-1]
        c0 = P_C + d * r
        rings.append([c0 + cvec * ((0.35 - xc) * ch) + nvec * (yc * ch) for xc, yc in ring2])
    loft(bm, rings, True, True, True, mat=0)
fix_normals(bm)
prop = obj_from_bm('Propeller', bm, C_SRC, [M['src_PropBlade'], M['src_Spinner']])
shade(prop, 50)
set_pivot(prop, tuple(P_C))

# ================================================================== LANDING GEAR
WHEEL_R_MAIN, WHEEL_C_MAIN = 0.462, (1.25, -2.85, 0.48)
TYRE = [(-0.115, 0.17), (-0.15, 0.21), (-0.178, 0.27), (-0.19, 0.33), (-0.185, 0.38), (-0.165, 0.425),
        (-0.13, 0.452), (-0.08, 0.46), (-0.03, 0.462), (0.03, 0.462), (0.08, 0.46), (0.13, 0.452),
        (0.165, 0.425), (0.185, 0.38), (0.19, 0.33), (0.178, 0.27), (0.15, 0.21), (0.115, 0.17)]
HUB = [(0.155, 0.0), (0.155, 0.04), (0.145, 0.055), (0.13, 0.10), (0.122, 0.16), (0.117, 0.176),
       (-0.117, 0.176), (-0.122, 0.16), (-0.13, 0.10), (-0.14, 0.055), (-0.15, 0.04), (-0.15, 0.0)]


def tyre_mod(scale_lug):
    def f(i, j, r):
        a = TYRE_S[j][0]
        if r < 0.40 * TYRE_S_SCALE:
            return r
        left = a < 0
        raised = ((i + (0 if left else 2)) // 2) % 2 == 0
        if r > 0.445 * TYRE_S_SCALE:
            return r + (scale_lug if raised else 0.0)
        return r + (scale_lug * 0.5 if raised else 0.0)
    return f


def make_wheel(name, center, scale=1.0, width_scale=1.0, segs=96, lug=0.022):
    global TYRE_S, TYRE_S_SCALE
    TYRE_S = [(a * scale * width_scale, r * scale) for a, r in TYRE]
    TYRE_S_SCALE = scale
    bm = bmesh.new()
    revolve(bm, TYRE_S, 'X', center, segs=segs, mat=0, radial_fn=tyre_mod(lug))
    hub = [(a * scale * width_scale, r * scale) for a, r in HUB]
    revolve(bm, hub, 'X', center, segs=24, mat=1)
    # hub bolts (6)
    for i in range(6):
        ang = 2 * PI * i / 6
        for sgn in (1, -1):
            p = Vector(center) + Vector((sgn * 0.148 * scale * width_scale, math.sin(ang) * 0.075 * scale,
                                         math.cos(ang) * 0.075 * scale))
            cylinder(bm, p, p + Vector((sgn * 0.018 * scale, 0, 0)), 0.013 * scale, 0.011 * scale, 6, mat=1)
    fix_normals(bm)
    ob = obj_from_bm(name, bm, C_SRC, [M['src_Rubber'], M['src_Hub']])
    shade(ob, 50)
    set_pivot(ob, center)
    return ob


wheel_L = make_wheel('Wheel_L', WHEEL_C_MAIN)
wheel_R = make_wheel('Wheel_R', (-WHEEL_C_MAIN[0], WHEEL_C_MAIN[1], WHEEL_C_MAIN[2]))
TW_C = (0.0, 2.06, 0.285)
tailwheel = make_wheel('TailWheel', TW_C, scale=0.59, width_scale=0.72, segs=48, lug=0.01)

# main gear legs (static)
bm = bmesh.new()
for sgn in (1, -1):
    ax = Vector((1.03 * sgn, -2.85, 0.48))
    for yy in (-3.18, -2.52):
        top = Vector((0.46 * sgn, yy, 1.03))
        sweep(bm, [top, top.lerp(ax, 0.5), ax], lambda u: 0.05 - 0.012 * u, lambda u: 0.036 - 0.008 * u, 10)
    # oleo / shock leg from fuselage side to axle
    top = Vector((0.66 * sgn, -2.85, 1.15))
    cylinder(bm, top, top.lerp(ax, 0.55), 0.05, 0.05, 12)
    cylinder(bm, top.lerp(ax, 0.5), ax, 0.035, 0.035, 12)
    # axle hub block
    box(bm, ax + Vector((0.02 * sgn, 0, 0)), (0.12, 0.16, 0.14), bevel=0.02, bevel_segs=2)
    cylinder(bm, ax, Vector(WHEEL_C_MAIN) * Vector((sgn, 1, 1)) - Vector((0.10 * sgn, 0, 0)), 0.035, 0.035, 10)
    # brake caliper
    box(bm, ax + Vector((0.07 * sgn, 0.14, -0.05)), (0.05, 0.10, 0.08), bevel=0.01, bevel_segs=1)
# tail gear spring leg
top = Vector((0, 1.55, 1.10))
bot = Vector((0, 1.93, 0.70))
sweep(bm, [top, top.lerp(bot, 0.5), bot], lambda u: 0.055 - 0.015 * u, lambda u: 0.022, 10, up_hint=Vector((0, 1, 0)))
box(bm, bot + Vector((0, 0.01, -0.02)), (0.08, 0.08, 0.06), bevel=0.01, bevel_segs=1)
fix_normals(bm)
gear = obj_from_bm('src_GearLegs', bm, C_SRC, [M['src_GearPaint']])
shade(gear, 45)

# tail wheel fork (steerable)
bm = bmesh.new()
FK = Vector((0, 1.945, 0.63))
cylinder(bm, FK + Vector((0, 0, 0.05)), FK + Vector((0, 0, -0.07)), 0.032, 0.032, 12)
box(bm, FK + Vector((0, 0.01, -0.085)), (0.24, 0.07, 0.045), bevel=0.012, bevel_segs=2)
for sgn in (1, -1):
    a0 = FK + Vector((0.105 * sgn, 0.01, -0.085))
    a1 = Vector((0.105 * sgn, TW_C[1], TW_C[2]))
    sweep(bm, [a0, a0.lerp(a1, 0.5), a1], 0.022, 0.012, 8, up_hint=Vector((0, 1, 0)))
cylinder(bm, Vector((-0.11, TW_C[1], TW_C[2])), Vector((0.11, TW_C[1], TW_C[2])), 0.018, 0.018, 8)
fix_normals(bm)
fork = obj_from_bm('TailWheel_Fork', bm, C_SRC, [M['src_GearPaint']])
shade(fork, 45)
set_pivot(fork, tuple(FK))

# ================================================================== CARGO DOOR (fits the opening, hinged at rear edge)
# sample fuselage cross-section polygon on +X side to follow the skin exactly
ring = superellipse(0.74, (2.66 - 0.96) / 2, 7.0, NR)
zc_f = (2.66 + 0.96) / 2
side_pts = sorted([(zc_f + z, x) for x, z in ring if x > 0.2], key=lambda p: p[0])


def skin_x(z):
    for (z0, x0), (z1, x1) in zip(side_pts[:-1], side_pts[1:]):
        if z0 <= z <= z1:
            return x0 + (x1 - x0) * (z - z0) / (z1 - z0)
    return side_pts[-1][1]


G = 0.008
dy0, dy1, dz0, dz1 = DOOR_Y0 + G, DOOR_Y1 - G, DOOR_Z0 + G, DOOR_Z1 - G
zs = sorted(set([dz0, dz1] + [z for z, x in side_pts if dz0 < z < dz1]))
ys = [dy0 + (dy1 - dy0) * i / 6 for i in range(7)]
bm = bmesh.new()
grid = [[bm.verts.new((skin_x(z) + 0.004, y, z)) for z in zs] for y in ys]
outer = []
for i in range(len(ys) - 1):
    for j in range(len(zs) - 1):
        outer.append(bm.faces.new([grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]))
bm.normal_update()
if outer[0].normal.x < 0:
    for f in outer:
        f.normal_flip()
res = bmesh.ops.solidify(bm, geom=outer, thickness=0.035)
for f in bm.faces:
    f.material_index = 0 if (f in outer) else 1
# round the corners a little by beveling the 4 outer-corner vertical/horizontal edges is overkill: keep square
fix_normals(bm)
door = obj_from_bm('CargoDoor', bm, C_SRC, [M['src_Livery'], M['src_InteriorA']])
shade(door, 40)
# handle
bm = bmesh.new()
bm.from_mesh(door.data)
hp = Vector((skin_x(1.75) + 0.02, dy0 + 0.12, 1.75))
box(bm, hp, (0.035, 0.16, 0.03), mat=1, bevel=0.008, bevel_segs=1)
bm.to_mesh(door.data)
bm.free()
set_pivot(door, (0.752, DOOR_Y1, 1.77))

# ================================================================== CARGO BAY INTERIOR + CASES
IY0, IY1, IX, IZ0, IZ1 = -1.55, 1.20, 0.69, 1.07, 2.58
bm = bmesh.new()
v = lambda x, y, z: bm.verts.new((x, y, z))
quads = [
    [(-IX, IY0, IZ0), (IX, IY0, IZ0), (IX, IY1, IZ0), (-IX, IY1, IZ0)],      # floor (normal +Z)
    [(-IX, IY0, IZ1), (-IX, IY1, IZ1), (IX, IY1, IZ1), (IX, IY0, IZ1)],      # ceiling (normal -Z)
    [(-IX, IY0, IZ0), (-IX, IY1, IZ0), (-IX, IY1, IZ1), (-IX, IY0, IZ1)],    # starboard wall (normal +X)
    [(-IX, IY0, IZ0), (-IX, IY0, IZ1), (IX, IY0, IZ1), (IX, IY0, IZ0)],      # front bulkhead (normal +Y)
    [(-IX, IY1, IZ0), (IX, IY1, IZ0), (IX, IY1, IZ1), (-IX, IY1, IZ1)],      # rear bulkhead (normal -Y)
]
for q in quads:
    f = bm.faces.new([v(*p) for p in q])
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
# subdivide for AO resolution
bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
# floor rails / tie-down strips
for yy in (-1.2, -0.4, 0.4):
    pass
bm.normal_update()
# make sure normals point inward (toward the cabin center)
cen = Vector((0, (IY0 + IY1) / 2, (IZ0 + IZ1) / 2))
for f in bm.faces:
    if (cen - f.calc_center_median()).dot(f.normal) < 0:
        f.normal_flip()
for yy in (-1.25, -0.2, 0.85):  # wall ribs on starboard wall & ceiling frames
    box(bm, (-IX + 0.02, yy, (IZ0 + IZ1) / 2), (0.04, 0.06, IZ1 - IZ0 - 0.02))
    box(bm, (0, yy, IZ1 - 0.02), (2 * IX - 0.02, 0.06, 0.04))
for xx in (-0.35, 0.35):  # floor rails
    box(bm, (xx, (IY0 + IY1) / 2, IZ0 + 0.01), (0.05, IY1 - IY0 - 0.02, 0.02))
interior = obj_from_bm('src_Interior', bm, C_SRC, [M['src_InteriorD']])
shade(interior, 30)


def case(name, center, size, mat, handle=True):
    bm = bmesh.new()
    box(bm, center, size, mat=0, bevel=0.03, bevel_segs=2)
    cx, cy, cz = center
    sx, sy, sz = size
    # lid seam rib
    box(bm, (cx, cy, cz + sz * 0.18), (sx + 0.012, sy + 0.012, 0.025), mat=0, bevel=0.006, bevel_segs=1)
    # latches on +X face
    for k in (-0.3, 0.3):
        box(bm, (cx + sx / 2 + 0.008, cy + k * sy, cz + sz * 0.18), (0.02, 0.06, 0.07), mat=1, bevel=0.005,
            bevel_segs=1)
    if handle:
        hz = cz + sz / 2
        path = [Vector((cx, cy - 0.09, hz - 0.005)), Vector((cx, cy - 0.08, hz + 0.035)),
                Vector((cx, cy + 0.08, hz + 0.035)), Vector((cx, cy + 0.09, hz - 0.005))]
        sweep(bm, path, 0.012, 0.012, 6, mat=1, up_hint=Vector((1, 0, 0)))
    fix_normals(bm)
    ob = obj_from_bm(name, bm, C_SRC, [M[mat], M['src_MetalDark']])
    shade(ob, 40)
    return ob


fz = IZ0 + 0.02
cases = [
    case('src_Case1', (0.12, -0.50, fz + 0.21), (0.62, 0.56, 0.42), 'src_CaseTeal'),
    case('src_Case2', (0.14, 0.12, fz + 0.18), (0.66, 0.62, 0.36), 'src_CaseYellow'),
    case('src_Case3', (0.12, -0.48, fz + 0.42 + 0.17), (0.52, 0.46, 0.34), 'src_CaseGreen'),
    case('src_Case4', (0.10, 0.10, fz + 0.36 + 0.15), (0.48, 0.44, 0.30), 'src_CaseDark'),
    case('src_Case5', (-0.46, -0.20, fz + 0.30), (0.40, 0.70, 0.60), 'src_CaseGreen'),
    case('src_Case6', (0.08, -0.05, fz + 0.36 + 0.30 + 0.12), (0.40, 0.36, 0.24), 'src_CaseGreen'),
]

# ================================================================== ANTENNAS, PITOT
bm = bmesh.new()
whips = [(0.28, -1.30), (-0.28, -1.30), (0.0, 3.05)]
for x, y in whips:
    if abs(y) < 2:
        z = wing_surface_z(x, (y - W_LE) / W_CH, True)
    else:
        z = 2.52
    base = Vector((x, y, z - 0.01))
    cylinder(bm, base, base + Vector((0, 0, 0.045)), 0.03, 0.026, 10)
    tip = base + Vector((0, 0.18, 0.62))
    cylinder(bm, base + Vector((0, 0, 0.04)), tip, 0.009, 0.0035, 6)
# blade antenna on tail cone and belly
for (y, z, up) in ((2.35, 2.585, 1), (0.9, 0.975, -1)):
    le0, le1 = Vector((0, y - 0.12, z)), Vector((0, y + 0.02, z + up * 0.24))
    te0, te1 = Vector((0, y + 0.12, z)), Vector((0, y + 0.08, z + up * 0.24))
    rings = []
    for a, b in ((le0, te0), (le1, te1)):
        ch = (b - a).length
        r2 = airfoil_ring(0, 0.999, 6, 0, 0, 0.14, True)[:-1]
        rings.append([a + Vector((yc * ch, xc * ch, 0)) for xc, yc in r2])
    loft(bm, rings, True, True, True)
# pitot under port wing
xp = 4.6
zl = wing_surface_z(xp, 0.2, False)
m0 = Vector((xp, W_LE + 0.25 * W_CH, zl + 0.01))
cylinder(bm, m0, m0 + Vector((0, -0.05, -0.12)), 0.018, 0.012, 8)
cylinder(bm, m0 + Vector((0, 0.05, -0.12)), m0 + Vector((0, -0.45, -0.12)), 0.011, 0.011, 8)
fix_normals(bm)
ant = obj_from_bm('src_Antennas', bm, C_SRC, [M['src_Antenna']])
shade(ant, 45)

# ================================================================== NAV LIGHTS
bm = bmesh.new()


def lens(center, length, radius, axis='Y'):
    prof = []
    for i in range(7):
        u = i / 6
        prof.append((-length / 2 + u * length, radius * math.sin(PI * (0.08 + 0.92 * u) ** 0.8)))
    prof = [(-length / 2, 0.0)] + prof + [(length / 2, 0.0)]
    revolve(bm, prof, axis, center, segs=12)


tipz = wz(7.07)
lens((7.07, W_LE + 0.25, tipz), 0.16, 0.035)
lens((-7.07, W_LE + 0.25, tipz), 0.16, 0.035)
lens((0, 4.40, 3.915), 0.14, 0.03)
lens((2.57, 4.30, STAB_Z), 0.12, 0.025)
lens((-2.57, 4.30, STAB_Z), 0.12, 0.025)
lens((0, 1.65, 0.955), 0.12, 0.04)  # belly beacon
fix_normals(bm)
lights = obj_from_bm('src_NavLights', bm, C_SRC, [M['M_Lights']])
shade(lights, 60)

# ================================================================== HIERARCHY
static = [fus, wing, te_center, te_tipL, te_tipR, struts, fin, stab, cowl_det, gear, interior, ant, lights] + cases
for ob in static + [prop, wheel_L, wheel_R, rudder, door] + list(cs.values()):
    parent_keep(ob, root)
parent_keep(fork, root)
parent_keep(tailwheel, fork)
com = empty('CenterOfMass', C_SRC, loc=(0, -1.95, 1.75), size=0.25, kind='SPHERE')
parent_keep(com, root)

tris = 0
dg = bpy.context.evaluated_depsgraph_get()
for ob in bpy.data.objects:
    if ob.type == 'MESH':
        me = ob.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        ob.evaluated_get(dg).to_mesh_clear()
print('TOTAL TRIS', tris)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'plane_geo.blend'))
print('saved')
