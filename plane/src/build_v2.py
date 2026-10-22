"""v2 (UE5.6 FP-sim): solid fuselage with real openings, doors, glass, split gear. Output: out/plane_geo_v2.blend
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
    'src_CabinWall': (0.09, 0.095, 0.09), 'src_Seal': (0.012, 0.012, 0.012), 'src_Glass': (0.6, 0.7, 0.75),
    'src_DoorPanel': (0.10, 0.105, 0.10),
    'M_Light_Red': (1.0, 0.02, 0.01), 'M_Light_Green': (0.02, 1.0, 0.1), 'M_Light_White': (1.0, 1.0, 0.95),
    'M_Light_Beacon': (1.0, 0.05, 0.0), 'M_Light_Landing': (1.0, 0.97, 0.9),
}
M = {}
for k, c in MAT_COLORS.items():
    m = bpy.data.materials.new(k)
    m.diffuse_color = (*c, 1)
    M[k] = m

root = empty('UtilityPlane', C_SRC, size=1.0, kind='ARROWS')

# ================================================================== FUSELAGE: solid shell with real openings
import layout as LY
from mathutils.bvhtree import BVHTree
from mathutils import geometry as mgeo
ST = LY.fuselage_stations()
NR = 40


def fus_ring(st):
    y, zb, zt, hw, n = st
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    return [Vector((x, y, zc + z)) for x, z in superellipse(hw, hh, n, NR)]


def apply_modifiers(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me_new = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me_new
    bpy.data.meshes.remove(old)
    me_new.name = ob.name
    return ob


def boolean(ob, cutter, op):
    md = ob.modifiers.new('bool', 'BOOLEAN')
    md.operation = op
    md.solver = 'EXACT'
    md.material_mode = 'TRANSFER'
    md.object = cutter
    apply_modifiers(ob)
    bpy.data.objects.remove(cutter)


def side_prism(bm, outline, r, side, x_in=0.66, x_out=1.10, mat=0):
    pts = LY.rounded_poly(outline, r)
    sg = 1 if side == 'L' else -1
    loft(bm, [[Vector((sg * x_in, y, z)) for y, z in pts], [Vector((sg * x_out, y, z)) for y, z in pts]],
         True, True, True, mat)


def top_prism(bm, outline, r, z0=1.95, z1=3.0, mat=0):
    pts = LY.rounded_poly(outline, r)
    loft(bm, [[Vector((x, y, z0)) for x, y in pts], [Vector((x, y, z1)) for x, y in pts]], True, True, True, mat)


bm = bmesh.new()
loft(bm, [fus_ring(s) for s in ST], closed=True, cap0=True, cap1=True, mat=0)
fix_normals(bm)
BM_OUT = bm.copy()
BVH_OUT = BVHTree.FromBMesh(BM_OUT)
fus = obj_from_bm('src_Fuselage', bm, C_SRC, [M['src_Livery'], M['src_CabinWall'], M['src_Seal']])
sol = fus.modifiers.new('solid', 'SOLIDIFY')
sol.thickness = LY.SKIN_T
sol.offset = -1.0
sol.use_even_offset = True
sol.material_offset = 1
apply_modifiers(fus)
FUS_SOLID = fus.data.copy()

bm = bmesh.new()
for side in ('L', 'R'):
    side_prism(bm, *LY.PILOT_DOOR, side)
    for w in LY.SIDE_FIXED[side]:
        side_prism(bm, *w, side)
side_prism(bm, *LY.CARGO_DOOR, 'L')
side_prism(bm, *LY.CARGO_DOOR, 'R')
top_prism(bm, *LY.WS_L)
top_prism(bm, *LY.WS_R)
fix_normals(bm)
boolean(fus, obj_from_bm('cutter', bm, C_SRC, [M['src_Seal']]), 'DIFFERENCE')

# drop the inner skin outside the cabin (behind firewall / aft of rear bulkhead / under the floor)
bm = bmesh.new()
bm.from_mesh(fus.data)
kill = [f for f in bm.faces if f.material_index == 1 and (
    f.calc_center_median().y < LY.FIREWALL_Y - 0.01 or f.calc_center_median().y > LY.REAR_BULKHEAD_Y + 0.01
    or f.calc_center_median().z < LY.FLOOR_Z - 0.02)]
bmesh.ops.delete(bm, geom=kill, context='FACES')
n_inner = sum(1 for f in bm.faces if f.material_index == 1)
assert n_inner > 200, f'inner skin lost in boolean ({n_inner} faces)'
bm.to_mesh(fus.data)
bm.free()
shade(fus, 40)
print('fuselage faces', len(fus.data.polygons))


def glass_patch(bm, outline, r, proj, inset=0.015, spacing=0.14, grow=0.012, mat=0):
    pts = LY.rounded_poly(LY.offset_poly(outline, grow), r + grow, seg=3)
    us, vs = [p[0] for p in pts], [p[1] for p in pts]
    inner = []
    u = min(us) + spacing / 2
    while u < max(us):
        v = min(vs) + spacing / 2
        while v < max(vs):
            if LY.point_in_poly((u, v), pts) and min(math.dist((u, v), p) for p in pts) > spacing * 0.45:
                inner.append((u, v))
            v += spacing
        u += spacing
    allp = pts + inner
    nb = len(pts)
    res = mgeo.delaunay_2d_cdt([Vector(p) for p in allp], [(i, (i + 1) % nb) for i in range(nb)],
                               [list(range(nb))], 1, 1e-7)
    vco, faces = res[0], res[2]
    bvs = []
    for p in vco:
        o, d = proj(p)
        loc, nrm, _, _ = BVH_OUT.ray_cast(o, d)
        if loc is None:
            loc, nrm = o + d * 0.5, -d
        bvs.append(bm.verts.new(loc - nrm * inset))
    for f in faces:
        try:
            bm.faces.new([bvs[i] for i in f]).material_index = mat
        except ValueError:
            pass


PROJ = {'L': lambda p: (Vector((1.6, p[0], p[1])), Vector((-1, 0, 0))),
        'R': lambda p: (Vector((-1.6, p[0], p[1])), Vector((1, 0, 0))),
        'T': lambda p: (Vector((p[0], p[1], 3.6)), Vector((0, 0, -1)))}

bm = bmesh.new()
for side in ('L', 'R'):
    for w in LY.SIDE_FIXED[side]:
        glass_patch(bm, *w, PROJ[side])
glass_patch(bm, *LY.WS_L, PROJ['T'], spacing=0.07)
glass_patch(bm, *LY.WS_R, PROJ['T'], spacing=0.07)
bm.normal_update()
glass = obj_from_bm('src_GlassFixed', bm, C_SRC, [M['src_Glass']])
shade(glass, 60)


def door(name, outline, r, side, pivot, windows=()):
    me = FUS_SOLID.copy()
    me.materials[1] = M['src_DoorPanel']
    ob = bpy.data.objects.new(name, me)
    C_SRC.objects.link(ob)
    bmc = bmesh.new()
    side_prism(bmc, LY.offset_poly(outline, -LY.DOOR_GAP), max(r - LY.DOOR_GAP, 0.01), side)
    fix_normals(bmc)
    boolean(ob, obj_from_bm('cut', bmc, C_SRC, [M['src_Seal']]), 'INTERSECT')
    for w, wr in windows:
        bmc = bmesh.new()
        side_prism(bmc, w, wr, side)
        fix_normals(bmc)
        boolean(ob, obj_from_bm('cutw', bmc, C_SRC, [M['src_Seal']]), 'DIFFERENCE')
    if M['src_Glass'].name not in [m.name for m in ob.data.materials]:
        ob.data.materials.append(M['src_Glass'])
    gi = [m.name for m in ob.data.materials].index('src_Glass')
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for w, wr in windows:
        glass_patch(bm, w, wr, PROJ[side], mat=gi)
    sg = 1 if side == 'L' else -1
    di = [m.name for m in ob.data.materials].index('src_DoorPanel')
    return ob, bm, sg, di


def finish_door(ob, bm, pivot):
    bm.normal_update()
    bm.to_mesh(ob.data)
    bm.free()
    shade(ob, 40)
    set_pivot(ob, pivot)
    return ob


doors = {}
for side in ('L', 'R'):
    ob, bm, sg, di = door(f'PilotDoor_{side}', *LY.PILOT_DOOR, side, None, [LY.W1])
    # outside grab handle (v5: the inside armrest / handle are part of the door trim, cp_equip.py)
    box(bm, (sg * 0.752, -2.32, 1.70), (0.022, 0.12, 0.022), mat=0, bevel=0.006, bevel_segs=1)
    doors[side] = finish_door(ob, bm, (sg * 0.745, LY.PILOT_DOOR_HINGE_Y, 1.60))
cargo_doors = {}
for side in ('L', 'R'):                       # hinge on the aft edge, handles at the free (front) edge
    ob, bm, sg, di = door(f'CargoDoor_{side}', *LY.CARGO_DOOR, side, None, [LY.CARGO_WIN])
    box(bm, (sg * 0.752, -0.70, 1.75), (0.022, 0.16, 0.03), mat=0, bevel=0.006, bevel_segs=1)
    hx, hy, hz = LY.CARGO_DOOR_HINGE
    cargo_doors[side] = finish_door(ob, bm, (sg * hx, hy, hz))

# ================================================================== WING (box to 72 % chord) + trailing pieces
W_LE, W_CH = -2.55, 2.10
W_Z0, DIH = 2.648, math.radians(2.0)
W_M, W_P, W_T = 0.02, 0.4, 0.13
H_BOX, H_CS = 0.715, 0.73


def wz(x):
    return W_Z0 + max(0.0, abs(x) - 0.76) * math.tan(DIH)


CUFF_X = 3.9


def cuffed(xc, yc, k=1.0):
    if xc >= 0.22:
        return xc, yc
    f = (1 - xc / 0.22) ** 2
    return xc - 0.028 * f * k, yc - 0.020 * f * k


def wing_ring(x, a, b, n, front, scale_t=1.0, chord=W_CH, le=W_LE, cuff=None, droop=0.0):
    ring2 = airfoil_ring(a, b, n, W_M, W_P, W_T * scale_t, front)
    if cuff is None:
        cuff = abs(x) >= CUFF_X
    if cuff:
        ring2 = [cuffed(xc, yc) for xc, yc in ring2]
    z0 = wz(x) - droop
    return [Vector((x, le + xc * chord, z0 + yc * chord)) for xc, yc in ring2]


def wing_surface_z(x, xc, upper=True):
    u, l = naca(W_M, W_P, W_T, xc)
    return wz(x) + (u[1] if upper else l[1]) * W_CH


NB = 14
xs_box = [-7.0, -6.82, -5.3, -3.905, -3.895, -2.3, -0.76, 0.0, 0.76, 2.3, 3.895, 3.905, 5.3, 6.82, 7.0]
rings = [wing_ring(-7.10, 0, H_BOX, NB, True, 0.45, W_CH * 0.95, W_LE + 0.05, droop=0.05)]
rings += [wing_ring(-7.05, 0, H_BOX, NB, True, 0.75, W_CH * 0.985, W_LE + 0.015, droop=0.025)]
rings += [wing_ring(x, 0, H_BOX, NB, True, cuff=abs(x) > 3.9) for x in xs_box]
rings += [wing_ring(7.05, 0, H_BOX, NB, True, 0.75, W_CH * 0.985, W_LE + 0.015, droop=0.025)]
rings += [wing_ring(7.10, 0, H_BOX, NB, True, 0.45, W_CH * 0.95, W_LE + 0.05, droop=0.05)]
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


def add_wicks(ob, xs, y_te, zf, dy=0.13):
    if 'src_Antenna' not in [m.name for m in ob.data.materials]:
        ob.data.materials.append(M['src_Antenna'])
    mi = [m.name for m in ob.data.materials].index('src_Antenna')
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for xx in xs:
        z = zf(xx)
        cylinder(bm, Vector((xx, y_te - 0.03, z)), Vector((xx, y_te + dy, z - 0.004)), 0.004, 0.0015, 6, mat=mi)
    bm.to_mesh(ob.data)
    bm.free()


te_center = te_piece('src_WingTE_Center', -0.76, 0.76)
te_tipL = te_piece('src_WingTE_TipL', 6.84, 7.0)
te_tipR = te_piece('src_WingTE_TipR', -7.0, -6.84)
cs = {}
for side, sgn in (('L', 1), ('R', -1)):
    for nm, a, b in (('Flap', 0.80, 3.84), ('Aileron', 3.88, 6.80)):
        x0, x1 = sorted((sgn * a, sgn * b))
        ob = te_piece(f'{nm}_{side}', x0, x1)
        if nm == 'Aileron':
            add_wicks(ob, [sgn * 4.6, sgn * 5.6, sgn * 6.5], W_LE + W_CH, lambda xx: wz(xx))
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
bmr = bmesh.new()
bmr.from_mesh(rudder.data)
box(bmr, (0.012, 4.96, 2.62), (0.012, 0.05, 0.028), mat=0, bevel=0.003, bevel_segs=1)          # trim tab horn
cylinder(bmr, Vector((0.012, 4.94, 2.62)), Vector((0.02, 4.72, 2.63)), 0.004, 0.004, 6, mat=0)
bmr.to_mesh(rudder.data)
bmr.free()
add_wicks(rudder, [0.0], 5.07, lambda xx: 3.5)
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
    if side == 'L':
        bme = bmesh.new()
        bme.from_mesh(ob.data)
        box(bme, (0.95, 4.93, STAB_Z - 0.018), (0.012, 0.05, 0.025), mat=0, bevel=0.003, bevel_segs=1)
        cylinder(bme, Vector((0.95, 4.91, STAB_Z - 0.02)), Vector((0.95, 4.72, STAB_Z - 0.03)), 0.004, 0.004, 6, mat=0)
        bme.to_mesh(ob.data)
        bme.free()
    add_wicks(ob, [sgn * 2.1], stab_chord(2.1)[1], lambda xx: STAB_Z)
    shade(ob, 35)
    set_pivot(ob, (sgn * 1.35, E_HINGE, STAB_Z))
    cs[f'Elevator_{side}'] = ob

# ================================================================== COWL DETAILS: intake + exhausts
bm = bmesh.new()
intake_rings = []
for y, hw, hh, z in ((-4.63, 0.19, 0.075, 1.34), (-4.58, 0.215, 0.095, 1.335), (-4.46, 0.215, 0.09, 1.31),
                     (-4.30, 0.19, 0.07, 1.24)):
    intake_rings.append([Vector((x, y, z + zz)) for x, zz in superellipse(hw, hh, 3.0, 20)])
# inner duct going back into the cowl (reverse direction) -> hollow look
inner = [[Vector((v.x * 0.78, -4.63, 1.34 + (v.z - 1.34) * 0.6)) for v in intake_rings[0]],
         [Vector((v.x * 0.78, -4.52, 1.34 + (v.z - 1.34) * 0.6)) for v in intake_rings[0]]]
loft(bm, [inner[1], inner[0]] + intake_rings, True, True, True)
fix_normals(bm)
# exhaust stacks
for sgn in (1, -1):
    path = bezier((0.46 * sgn, -4.12, 1.60), (0.72 * sgn, -4.10, 1.60), (0.78 * sgn, -3.80, 1.56), 7)
    t = (path[-1] - path[-2]).normalized()
    rings_r = [0.078] * len(path)
    rings = []
    for k, p in enumerate(path):
        tng = (path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)])
        s, u = ring_frame(p, tng)
        rings.append([p + s * (0.10 * math.cos(a)) + u * (0.082 * math.sin(a)) for a in
                      (2 * PI * i / 14 for i in range(14))])
    pe = path[-1]
    s, u = ring_frame(pe, t)
    for fac, back in ((0.8, 0.0), (0.8, 0.12)):
        c = pe - t * back
        rings.append([c + s * (0.10 * fac * math.cos(a)) + u * (0.082 * fac * math.sin(a)) for a in
                      (2 * PI * i / 14 for i in range(14))])
    loft(bm, rings, True, True, True)
fix_normals(bm)
cowl_det = obj_from_bm('src_CowlDetails', bm, C_SRC, [M['src_MetalDark']])
shade(cowl_det, 45)

# ================================================================== PROPELLER (blades + spinner + hub)
P_C = Vector(LY.PROP_C)  # prop disc center
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
WHEEL_R_MAIN, WHEEL_C_MAIN = 0.462, LY.MAIN_WHEEL_C          # v5: legs 0.12 m longer (tail-down stance)
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
    if scale > 0.9:
        side_in = -1 if center[0] > 0 else 1
        c0 = Vector(center) + Vector((side_in * 0.125, 0, 0))
        revolve(bm, [(side_in * 0.0, 0.0), (0.0, 0.135), (side_in * 0.008, 0.135), (side_in * 0.008, 0.0)], 'X',
                tuple(c0), segs=24, mat=1)
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
TW_C = LY.TAIL_WHEEL_C                                       # v5: aft, under the rudder post
tailwheel = make_wheel('TailWheel', TW_C, scale=0.59, width_scale=0.72, segs=48, lug=0.01)

# main gear legs: one object per side, pivot on the fuselage hinge line (spring-steel swing = suspension)
gear_legs = {}
for side, sgn in (('L', 1), ('R', -1)):
    bm = bmesh.new()
    ax = Vector((1.03 * sgn, -2.85, WHEEL_C_MAIN[2]))
    for yy in (-3.18, -2.52):
        top = Vector((0.46 * sgn, yy, 1.03))
        sweep(bm, [top, top.lerp(ax, 0.5), ax], lambda u: 0.05 - 0.012 * u, lambda u: 0.036 - 0.008 * u, 10)
    box(bm, ax + Vector((0.02 * sgn, 0, 0)), (0.12, 0.16, 0.14), bevel=0.02, bevel_segs=2)
    cylinder(bm, ax, Vector(WHEEL_C_MAIN) * Vector((sgn, 1, 1)) - Vector((0.10 * sgn, 0, 0)), 0.035, 0.035, 10)
    box(bm, ax + Vector((0.07 * sgn, 0.14, -0.05)), (0.05, 0.10, 0.08), bevel=0.01, bevel_segs=1)
    top_r = Vector((0.46 * sgn, -2.52, 1.03))
    st = top_r.lerp(ax, 0.55)
    sweep(bm, [st, st + Vector((0.05 * sgn, 0.06, 0.0)), st + Vector((0.07 * sgn, 0.11, -0.01))], 0.012, 0.012, 8)
    box(bm, st + Vector((0.08 * sgn, 0.13, -0.005)), (0.12, 0.09, 0.012), bevel=0.004, bevel_segs=1)
    bl = [top_r + Vector((0, 0.03, 0.0)), top_r.lerp(ax, 0.5) + Vector((0, 0.035, 0.0)),
          ax + Vector((0.05 * sgn, 0.10, 0.02))]
    sweep(bm, bl, 0.005, 0.005, 6)
    # v5 boarding step on the aft blade (pilot door is 1.2 m above the ground in the tail-down stance)
    sp = top_r.lerp(ax, 0.80)
    cylinder(bm, sp, sp + Vector((0.035 * sgn, 0.13, -0.015)), 0.011, 0.011, 8)
    st_c = sp + Vector((0.045 * sgn, 0.17, -0.02))
    box(bm, st_c, (0.13, 0.10, 0.012), bevel=0.004, bevel_segs=1)
    for k in range(4):                                              # anti-slip ribs
        box(bm, st_c + Vector((0, -0.036 + k * 0.024, 0.008)), (0.12, 0.006, 0.004))
    box(bm, st_c + Vector((0, 0.052, -0.012)), (0.13, 0.006, 0.03), bevel=0.002, bevel_segs=1)
    fix_normals(bm)
    ob = obj_from_bm(f'Gear_{side}', bm, C_SRC, [M['src_GearPaint']])
    shade(ob, 45)
    set_pivot(ob, (0.46 * sgn, -2.85, LY.MAIN_LEG_TOP_Z))
    gear_legs[side] = ob
# tail gear (v5): leaf spring from a bracket under the tail cone, aft to the castoring head (TailGear pivot = root)
bm = bmesh.new()
SM = Vector(LY.TAIL_SPRING_MOUNT)
FP = Vector(LY.TAIL_FORK_PIVOT)
# mounting bracket bolted to the tail-cone bottom (two lugs + saddle)
zb_m = LY.ST_TAIL_A[1] + (SM.y - LY.ST_TAIL_A[0]) / (LY.ST_TAIL_B[0] - LY.ST_TAIL_A[0]) * (LY.ST_TAIL_B[1] - LY.ST_TAIL_A[1])
box(bm, (0, SM.y - 0.02, (zb_m + SM.z) / 2 + 0.01), (0.10, 0.16, zb_m - SM.z + 0.03), bevel=0.008, bevel_segs=2)
for sx in (0.045, -0.045):
    cylinder(bm, Vector((sx - 0.012, SM.y - 0.06, SM.z + 0.012)), Vector((sx + 0.012, SM.y - 0.06, SM.z + 0.012)),
             0.009, 0.009, 8)
# leaf: tapered flat bar, slight downward bow
path = [SM + Vector((0, -0.05, 0.0)), SM.lerp(FP, 0.33) + Vector((0, 0, -0.012)),
        SM.lerp(FP, 0.66) + Vector((0, 0, -0.010)), FP + Vector((0, -0.03, 0.0))]
sweep(bm, path, lambda u: 0.032 - 0.010 * u, lambda u: 0.011 - 0.003 * u, 8, up_hint=Vector((0, 0, 1)))
# secondary short leaf
sweep(bm, [SM + Vector((0, -0.03, -0.012)), SM.lerp(FP, 0.45) + Vector((0, 0, -0.024))], 0.028, 0.006, 8,
      up_hint=Vector((0, 0, 1)))
cylinder(bm, FP + Vector((0, 0, -0.045)), FP + Vector((0, 0, 0.045)), 0.034, 0.034, 14)     # pivot housing
box(bm, FP + Vector((0, -0.035, 0.0)), (0.05, 0.05, 0.05), bevel=0.006, bevel_segs=1)
fix_normals(bm)
tailgear = obj_from_bm('TailGear', bm, C_SRC, [M['src_GearPaint']])
shade(tailgear, 45)
set_pivot(tailgear, tuple(SM))

# tail wheel fork (castoring + steerable), pivot on the vertical axis through the head
bm = bmesh.new()
cylinder(bm, FP + Vector((0, 0, -0.07)), FP + Vector((0, 0, -0.035)), 0.030, 0.030, 14)
box(bm, FP + Vector((0, 0.03, -0.075)), (0.24, 0.09, 0.03), bevel=0.01, bevel_segs=2)
for sgn in (1, -1):
    a0 = FP + Vector((0.105 * sgn, 0.04, -0.08))
    a1 = Vector((0.105 * sgn, TW_C[1], TW_C[2]))
    sweep(bm, [a0, a0.lerp(a1, 0.5) + Vector((0, 0.01, 0)), a1], 0.022, 0.011, 8, up_hint=Vector((0, 1, 0)))
    box(bm, (0.105 * sgn, TW_C[1], TW_C[2]), (0.026, 0.05, 0.05), bevel=0.008, bevel_segs=1)
cylinder(bm, Vector((-0.12, TW_C[1], TW_C[2])), Vector((0.12, TW_C[1], TW_C[2])), 0.016, 0.016, 8)
# steering arm with two spring eyes (cables to the rudder horn are not modelled)
box(bm, FP + Vector((0, -0.05, -0.052)), (0.16, 0.025, 0.012), bevel=0.004, bevel_segs=1)
for sgn in (1, -1):
    cylinder(bm, FP + Vector((0.075 * sgn, -0.05, -0.062)), FP + Vector((0.075 * sgn, -0.05, -0.042)), 0.009, 0.009, 8)
fix_normals(bm)
fork = obj_from_bm('TailWheel_Fork', bm, C_SRC, [M['src_GearPaint']])
shade(fork, 45)
set_pivot(fork, tuple(FP))

# ================================================================== CARGO (cases on the cabin floor)
IZ0 = LY.FLOOR_Z


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
for (y, z, up) in ((2.35, 2.585, 1), (-1.05, 0.975, -1)):
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

# ================================================================== DETAILS (static): wing, fuselage, tail
bm = bmesh.new()
# vortex generators: counter-rotating pairs along the upper surface at 11 % chord
k = 0
for sgn in (1, -1):
    x = 0.95
    while x < 6.75:
        xx = sgn * x
        xc = 0.11
        if abs(xx) >= CUFF_X:
            xc2, _ = cuffed(xc, 0)
        else:
            xc2 = xc
        y = W_LE + xc2 * W_CH
        z = wing_surface_z(xx, xc, True) - 0.002
        ang = math.radians(16 if k % 2 == 0 else -16)
        d = Vector((math.sin(ang), math.cos(ang), 0))
        n = Vector((math.cos(ang), -math.sin(ang), 0)) * 0.001
        base = Vector((xx, y, z))
        pts = [base, base + d * 0.035, base + d * 0.035 + Vector((0, 0, 0.018))]
        vs = [bm.verts.new(p + n) for p in pts] + [bm.verts.new(p - n) for p in pts]
        for f in ((0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)):
            bm.faces.new([vs[i] for i in f])
        k += 1
        x += 0.105
    # stall strip on the inboard leading edge
    sweep(bm, [Vector((sgn * x0, W_LE - 0.004, wz(x0) - 0.008)) for x0 in (1.05, 1.25, 1.45)], 0.007, 0.007, 3)
    # flap-track / hinge fairings (canoes) under the wing
    for xt in (1.25, 2.45, 3.65, 4.85, 6.05):
        xs_ = sgn * xt
        zl = wing_surface_z(xs_, 0.55, False)
        prof = []
        for i in range(9):
            u = i / 8
            prof.append((W_LE + W_CH * (0.62 + 0.42 * u), 0.045 * math.sin(math.pi * u) ** 0.6))
        revolve(bm, prof, 'Y', (xs_, 0, zl - 0.01), segs=10)
    # tie-down ring at the strut fitting
    tr_c = Vector((sgn * 3.2, -1.62, wing_surface_z(sgn * 3.2, (-1.62 - W_LE) / W_CH, False) - 0.03))
    sweep(bm, [tr_c + Vector((0, 0.025 * math.cos(a), 0.025 * math.sin(a))) for a in
               [2 * math.pi * i / 12 for i in range(13)]], 0.005, 0.005, 6, cap0=False, cap1=False)
    # jury strut
    p0 = Vector((0.70 * sgn, -1.55, 1.10))
    p1 = Vector((3.4 * sgn, -1.75, wing_surface_z(3.4 * sgn, (-1.75 - W_LE) / W_CH, False)))
    j0 = p0.lerp(p1, 0.55)
    j1 = Vector((j0.x, j0.y + 0.05, wing_surface_z(j0.x, (j0.y + 0.05 - W_LE) / W_CH, False) + 0.01))
    cylinder(bm, j0, j1, 0.013, 0.013, 8)
    # strut grab handle
    g0, g1 = p0.lerp(p1, 0.18), p0.lerp(p1, 0.30)
    sweep(bm, [g0, g0 + Vector((0, -0.07, 0.0)), g1 + Vector((0, -0.07, 0.0)), g1], 0.009, 0.009, 8)
fix_normals(bm)
wdet = obj_from_bm('src_WingDetails', bm, C_SRC, [M['src_Struts']])
shade(wdet, 45)

# hinged fuel filler caps (SYS-02 "лючок заправки"): hinge on the aft edge, opens nose-up about the lateral axis
fuel_caps = {}
for sgn, s_ in ((1, 'L'), (-1, 'R')):
    xf = sgn * 1.55
    yc = W_LE + 0.25 * W_CH
    zc = wing_surface_z(xf, 0.25, True)
    bm = bmesh.new()
    cylinder(bm, Vector((xf, yc, zc + 0.002)), Vector((xf, yc, zc + 0.012)), 0.045, 0.042, 20)
    box(bm, (xf, yc, zc + 0.018), (0.06, 0.012, 0.01), bevel=0.003, bevel_segs=1)
    cylinder(bm, Vector((xf - 0.02, yc + 0.047, zc + 0.006)), Vector((xf + 0.02, yc + 0.047, zc + 0.006)), 0.005,
             0.005, 8)
    fix_normals(bm)
    ob = obj_from_bm(f'FuelCap_{s_}', bm, C_SRC, [M['src_Struts']])
    shade(ob, 45)
    set_pivot(ob, (xf, yc + 0.047, zc + 0.006))
    fuel_caps[s_] = ob

bm = bmesh.new()
# door hinges (pilot doors: front edge; cargo: rear edge)
for sgn in (1, -1):
    for zz in (1.35, 2.00):
        p = Vector((sgn * 0.748, LY.PILOT_DOOR_HINGE_Y - 0.01, zz))
        cylinder(bm, p + Vector((0, 0, -0.035)), p + Vector((0, 0, 0.035)), 0.011, 0.011, 10)
        box(bm, p + Vector((0, 0.03, 0)), (0.006, 0.05, 0.05), bevel=0.002, bevel_segs=1)
for sgn in (1, -1):
    for zz in (1.35, 2.20):
        p = Vector((sgn * 0.750, 0.462, zz))
        cylinder(bm, p + Vector((0, 0, -0.04)), p + Vector((0, 0, 0.04)), 0.012, 0.012, 10)
    # step under each cargo door
    st = [Vector((sgn * x_, y_, z_)) for x_, y_, z_ in ((0.55, -0.45, 0.99), (0.78, -0.45, 0.86), (0.80, -0.30, 0.84),
                                                        (0.80, -0.10, 0.84), (0.78, 0.05, 0.86), (0.55, 0.05, 0.99))]
    sweep(bm, st, 0.014, 0.014, 8)
    box(bm, (sgn * 0.80, -0.20, 0.846), (0.07, 0.30, 0.01), bevel=0.003, bevel_segs=1)
    # fuel filler flange + dark neck under the hinged cap (cap itself = FuelCap_L/R)
    xf = sgn * 1.55
    yc = W_LE + 0.25 * W_CH
    zc = wing_surface_z(xf, 0.25, True)
    cylinder(bm, Vector((xf, yc, zc - 0.006)), Vector((xf, yc, zc + 0.002)), 0.050, 0.048, 20)
# GPS puck + comm blade on the cabin roof aft of the wing
revolve(bm, [(2.66, 0.0), (2.66, 0.055), (2.675, 0.05), (2.685, 0.03), (2.688, 0.0)], 'Z', (0, 0.25, 0), segs=20)
for sgn in (1, -1):
    cylinder(bm, Vector((sgn * 0.738, 2.30, 1.72)), Vector((sgn * 0.745, 2.30, 1.72)), 0.014, 0.014, 12)  # static ports
# inertial separator bypass door + oil drain under the cowl
box(bm, (0, -4.05, 1.045), (0.16, 0.12, 0.012), bevel=0.003, bevel_segs=1)
cylinder(bm, Vector((0.08, -3.7, 1.03)), Vector((0.08, -3.7, 0.99)), 0.008, 0.006, 8)
# tail tie-down ring + bumper
tz = 2.14 - 0.07
sweep(bm, [Vector((0, 4.45 + 0.03 * math.cos(a), tz - 0.04 + 0.03 * math.sin(a))) for a in
           [2 * math.pi * i / 12 for i in range(13)]], 0.006, 0.006, 6, cap0=False, cap1=False)
box(bm, (0, 4.45, tz - 0.005), (0.03, 0.08, 0.03), bevel=0.005, bevel_segs=1)
fix_normals(bm)
fdet = obj_from_bm('src_FuseDetails', bm, C_SRC, [M['src_MetalDark']])
shade(fdet, 45)

# dorsal fin fillet (livery material, joins the fin leading edge)
bm = bmesh.new()
rings = []
for y, h in ((2.35, 0.004), (2.70, 0.03), (3.00, 0.07), (3.25, 0.13), (3.45, 0.24)):
    zt_ = 2.645 - (y - 1.5) * 0.0746 - 0.012
    w = 0.05 * (1 - (y - 2.35) / 1.4) + 0.012
    rings.append([Vector((w, y, zt_ - 0.02)), Vector((w * 0.6, y, zt_ + h * 0.5)), Vector((0.004, y, zt_ + h)),
                  Vector((-0.004, y, zt_ + h)), Vector((-w * 0.6, y, zt_ + h * 0.5)), Vector((-w, y, zt_ - 0.02))])
loft(bm, rings, True, True, True)
fix_normals(bm)
dorsal = obj_from_bm('src_Dorsal', bm, C_SRC, [M['src_Livery']])
shade(dorsal, 40)

# ================================================================== LIGHTS: red left, green right, white tail + strobes, red beacons
bm = bmesh.new()


def lens(center, length, radius, axis='Y', mat=0):
    prof = []
    for i in range(7):
        u = i / 6
        prof.append((-length / 2 + u * length, radius * math.sin(PI * (0.08 + 0.92 * u) ** 0.8)))
    prof = [(-length / 2, 0.0)] + prof + [(length / 2, 0.0)]
    revolve(bm, prof, axis, center, segs=12, mat=mat)


tipz = wz(7.07)
LIGHT_POS = {
    'Nav_L': (7.07, W_LE + 0.25, tipz), 'Nav_R': (-7.07, W_LE + 0.25, tipz),
    'Strobe_L': (7.075, W_LE + 0.47, tipz), 'Strobe_R': (-7.075, W_LE + 0.47, tipz),
    'Nav_Tail': (0.0, 5.10, 2.26), 'Beacon_Top': (0.0, 4.40, 3.915), 'Beacon_Bottom': (0.0, 1.65, 0.955),
}
lens(LIGHT_POS['Nav_L'], 0.16, 0.035, mat=0)
lens(LIGHT_POS['Nav_R'], 0.16, 0.035, mat=1)
lens(LIGHT_POS['Strobe_L'], 0.10, 0.025, mat=2)
lens(LIGHT_POS['Strobe_R'], 0.10, 0.025, mat=2)
lens(LIGHT_POS['Nav_Tail'], 0.08, 0.03, mat=2)
lens(LIGHT_POS['Beacon_Top'], 0.14, 0.03, mat=3)
lens(LIGHT_POS['Beacon_Bottom'], 0.12, 0.04, mat=3)
lens((2.30, W_LE - 0.012, wz(2.30) - 0.012), 0.03, 0.055, mat=4)
fix_normals(bm)
lights = obj_from_bm('src_Lights', bm, C_SRC, [M['M_Light_Red'], M['M_Light_Green'], M['M_Light_White'],
                                               M['M_Light_Beacon'], M['M_Light_Landing']])
shade(lights, 60)
import json
LIGHT_POS['Landing'] = (2.30, W_LE - 0.02, wz(2.30) - 0.012)
json.dump({k: list(v) for k, v in LIGHT_POS.items()}, open(os.path.join(HERE, 'out', 'light_pos.json'), 'w'))

# ================================================================== HIERARCHY (Blender preview; rig_ue.py builds the UE skeleton)
static = [fus, glass, wing, te_center, te_tipL, te_tipR, struts, fin, stab, cowl_det, ant, lights, wdet, fdet,
          dorsal] + cases
for ob in static + [prop, wheel_L, wheel_R, rudder, cargo_doors['L'], cargo_doors['R'], doors['L'], doors['R'],
                    fuel_caps['L'], fuel_caps['R'], gear_legs['L'], gear_legs['R'],
                    tailgear] + list(cs.values()):
    parent_keep(ob, root)
parent_keep(wheel_L, gear_legs['L'])
parent_keep(wheel_R, gear_legs['R'])
parent_keep(fork, tailgear)
parent_keep(tailwheel, fork)

tris = 0
dg = bpy.context.evaluated_depsgraph_get()
for ob in bpy.data.objects:
    if ob.type == 'MESH':
        me = ob.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        ob.evaluated_get(dg).to_mesh_clear()
print('TOTAL TRIS', tris)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'plane_geo_v2.blend'))
print('saved')
