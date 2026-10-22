"""(v2 detail) Cockpit for the FP sim: floor, bulkheads, instrument panel + gauges (UV-mapped to T_Gauges),
radios, switches, yokes, pedals, pedestal/levers, trim wheel, seats, compass.
Moving parts are separate objects named after their UE bone, pivots on their real axes (Blender build frame).
Reads out/plane_geo_v2.blend, writes out/plane_v2.blend (+ out/cockpit_rig.json)."""
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import *
import layout as LY

bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_geo_v2.blend'))
CP = coll('Cockpit')
COLORS = {
    'src_CP_Panel': (0.022, 0.023, 0.025), 'src_CP_Metal': (0.10, 0.10, 0.10), 'src_CP_Black': (0.008, 0.008, 0.008),
    'src_CP_Seat': (0.11, 0.085, 0.055), 'src_CP_Floor': (0.03, 0.03, 0.03), 'src_CP_Needle': (0.9, 0.9, 0.88),
    'src_CP_GaugeGlass': (0.6, 0.6, 0.6), 'src_CP_KnobRed': (0.6, 0.04, 0.03), 'src_CP_KnobBlue': (0.03, 0.12, 0.5),
    'src_CP_Orange': (0.9, 0.35, 0.02), 'src_CP_Bulkhead': (0.07, 0.075, 0.07),
    'src_CP_Leather': (0.10, 0.07, 0.045), 'src_CP_Strap': (0.02, 0.025, 0.03), 'src_CP_Rubber': (0.012, 0.012, 0.012),
    'src_CP_Chrome': (0.6, 0.6, 0.6), 'src_CP_Trim': (0.13, 0.13, 0.125), 'src_CP_Net': (0.03, 0.03, 0.03),
    'src_CP_Lens': (0.8, 0.8, 0.75), 'src_CP_Headset': (0.02, 0.02, 0.022), 'src_CP_Glare': (0.016, 0.016, 0.017),
    'src_CP_Annun': (0.08, 0.06, 0.03), 'M_Light_Cabin': (1.0, 0.85, 0.62),
}
M = {}
for k, c in COLORS.items():
    m = bpy.data.materials.get(k) or bpy.data.materials.new(k)
    m.diffuse_color = (*c, 1)
    M[k] = m
gauge_img = bpy.data.images.load(os.path.join(HERE, 'tex', 'v2', 'T_Gauges_BC.png'), check_existing=True)
MG = bpy.data.materials.get('src_CP_Gauges') or bpy.data.materials.new('src_CP_Gauges')
MG.diffuse_color = (0.2, 0.2, 0.2, 1)
MG['image'] = gauge_img.name
M['src_CP_Gauges'] = MG
M['src_CP_Annun']['image'] = gauge_img.name          # lamps sample the same atlas (blockout preview)
MATS = list(M.values())
MI = {m.name: i for i, m in enumerate(MATS)}

RIG = {}          # bone -> dict(pivot, parent, axis_blender, note)
STATIC = []       # static cockpit objects


def mk(name, bm, pivot=None, parent='Cockpit', axis='', note='', smooth=35):
    fix_normals_keep_uv(bm)
    ob = obj_from_bm(name, bm, CP, MATS)
    shade(ob, smooth)
    if pivot is None:
        STATIC.append(ob.name)
    else:
        set_pivot(ob, pivot)
        RIG[name] = dict(pivot=list(pivot), parent=parent, axis=axis, note=note)
    return ob


def plate_layer(bm):
    return bm.faces.layers.int.get('plate') or bm.faces.layers.int.new('plate')


def fix_normals_keep_uv(bm):
    lay = plate_layer(bm)
    solid = [f for f in bm.faces if f[lay] == 0]
    bmesh.ops.recalc_face_normals(bm, faces=solid)
    for f in bm.faces:
        if f[lay] == 1:
            f.normal_update()
            if f.normal.y < 0:
                f.normal_flip()


def box_rx(bm, center, size, rx, mat, bevel=0.0, segs=1):
    tmp = bmesh.new()
    box(tmp, (0, 0, 0), size, mat=mat, bevel=bevel, bevel_segs=segs)
    T = Matrix.Translation(Vector(center)) @ Matrix.Rotation(math.radians(rx), 4, 'X')
    bmesh.ops.transform(tmp, matrix=T, verts=tmp.verts)
    me = bpy.data.meshes.new('tmp')
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def disc(bm, center, r, y, segs=32, mat=0, uv_cell=None, uv_scale=1.0, facing=+1):
    """flat disc in the X-Z plane at depth y, facing +Y (towards the pilot). Optional UV to atlas cell."""
    uvl, pl = bm.loops.layers.uv.verify(), plate_layer(bm)
    cx, cz = center
    c = bm.verts.new((cx, y, cz))
    ring = [bm.verts.new((cx + r * math.cos(2 * PI * i / segs), y, cz + r * math.sin(2 * PI * i / segs)))
            for i in range(segs)]
    faces = []
    for i in range(segs):
        f = bm.faces.new((c, ring[(i + 1) % segs], ring[i]))
        f.material_index = mat
        f[pl] = 1
        faces.append(f)
    if uv_cell is not None:
        col, row = uv_cell % 8, uv_cell // 8
        for f in faces:
            for lp in f.loops:
                dx = (lp.vert.co.x - cx) / r
                dz = (lp.vert.co.z - cz) / r
                # pilot looks towards -Y: his right is -X
                u = (col + 0.5 - dx * 0.5 * uv_scale) / 8
                v = 1 - (row + 0.5 - dz * 0.5 * uv_scale) / 4
                lp[uvl].uv = (u, v)
    return faces


def annulus(bm, center, r0, r1, y, segs=32, mat=0, uv_cell=None):
    cx, cz = center
    uvl, pl = bm.loops.layers.uv.verify(), plate_layer(bm)
    inner = [bm.verts.new((cx + r0 * math.cos(2 * PI * i / segs), y, cz + r0 * math.sin(2 * PI * i / segs)))
             for i in range(segs)]
    outer = [bm.verts.new((cx + r1 * math.cos(2 * PI * i / segs), y, cz + r1 * math.sin(2 * PI * i / segs)))
             for i in range(segs)]
    for i in range(segs):
        j = (i + 1) % segs
        f = bm.faces.new((inner[i], outer[i], outer[j], inner[j]))
        f.material_index = mat
        f[pl] = 1
        if uv_cell is not None:
            col, row = uv_cell % 8, uv_cell // 8
            for lp in f.loops:
                dx = (lp.vert.co.x - cx) / r1
                dz = (lp.vert.co.z - cz) / r1
                lp[uvl].uv = ((col + 0.5 - dx * 0.5) / 8, 1 - (row + 0.5 - dz * 0.5) / 4)


def rect_uv(bm, x0, x1, z0, z1, y, mat, u0, u1, v0, v1):
    """rectangle facing +Y; x0 is the pilot-left edge (larger X)."""
    uvl, pl = bm.loops.layers.uv.verify(), plate_layer(bm)
    vs = [bm.verts.new(p) for p in ((x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1))]
    f = bm.faces.new(vs)
    f.material_index = mat
    f[pl] = 1
    for lp, uv in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
        lp[uvl].uv = uv
    f.normal_update()
    if f.normal.y < 0:
        f.normal_flip()
    return f


def needle_mesh(bm, cx, cz, y, length, angle_deg, width, mat, tail=0.18):
    """flat needle in the X-Z plane; angle clockwise from 12 o'clock as seen by the pilot (right = -X)."""
    a = math.radians(angle_deg)
    d = Vector((-math.sin(a), 0, math.cos(a)))
    s = Vector((math.cos(a), 0, math.sin(a)))
    base = Vector((cx, y, cz))
    pl = plate_layer(bm)
    pts = [base - d * length * tail + s * width * 0.5, base + d * length * 0.92 + s * width * 0.25,
           base + d * length, base + d * length * 0.92 - s * width * 0.25, base - d * length * tail - s * width * 0.5]
    vs = [bm.verts.new(p) for p in pts]
    f = bm.faces.new(vs)
    f.material_index = mat
    f[pl] = 1
    cylinder(bm, base + Vector((0, 0.0005, 0)), base + Vector((0, 0.003, 0)), width * 0.9, width * 0.9, 12, mat=MI['src_CP_Black'])



# ================================================================== extra helpers
def ribbon(bm, path, width, thick, mat, up_hint=Vector((0, 1, 0))):
    sweep(bm, [Vector(p) for p in path], width / 2, thick / 2, 6, mat=mat, up_hint=up_hint)


def knurled(bm, x, z, y0, r, length, mat, ridges=18, axis_y=True):
    """knob along +Y (towards the pilot) with knurled rim"""
    prof = [(y0, 0.0), (y0, r * 0.95), (y0 + length * 0.1, r), (y0 + length * 0.85, r), (y0 + length, r * 0.8),
            (y0 + length, 0.0)]
    revolve(bm, prof, 'Y', (x, 0, z), segs=ridges * 2, mat=mat,
            radial_fn=lambda i, j, rr: rr * (1.0 if (i % 2 == 0 or j in (0, 5)) else 0.93))


def screw(bm, x, z, y, r=0.0022, mat=None):
    revolve(bm, [(y, 0.0), (y, r), (y + r * 0.35, r * 0.85), (y + r * 0.55, 0.0)], 'Y', (x, 0, z), segs=8,
            mat=MI['src_CP_Metal'] if mat is None else mat)


def rbox(bm, center, size, mat, bevel=0.004, segs=2):
    box(bm, center, size, mat=mat, bevel=bevel, bevel_segs=segs)


def join_bm(dst, src):
    me = bpy.data.meshes.new('tmp')
    src.to_mesh(me)
    src.free()
    dst.from_mesh(me)
    bpy.data.meshes.remove(me)


def xform_bm(bm, M):
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)


def station_at(y):
    st = LY.fuselage_stations()
    for a, b in zip(st[:-1], st[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0])
            return [a[i] + (b[i] - a[i]) * t for i in range(1, 5)]
    raise ValueError(y)


def inner_ring(y, inset=0.034, n_pts=48):
    zb, zt, hw, n = station_at(y)
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    return [(x, zc + z) for x, z in superellipse(hw - inset, hh - inset, n, n_pts)]


# ================================================================== floor, rails, mats, D-rings, bulkheads
bm = bmesh.new()
box(bm, (0, (LY.FIREWALL_Y + LY.REAR_BULKHEAD_Y) / 2, LY.FLOOR_Z - 0.01), (1.32, LY.REAR_BULKHEAD_Y - LY.FIREWALL_Y, 0.02),
    mat=MI['src_CP_Floor'])
for sx in LY.SEATS_X:
    for dx in (-0.16, 0.16):
        box(bm, (sx + dx, -2.22, LY.FLOOR_Z + 0.008), (0.03, 0.9, 0.016), mat=MI['src_CP_Metal'])
        for k in range(8):                                        # seat-rail adjustment holes as tiny pegs
            box(bm, (sx + dx, -2.60 + k * 0.1, LY.FLOOR_Z + 0.017), (0.012, 0.012, 0.003), mat=MI['src_CP_Black'])
    box(bm, (sx, -2.86, LY.FLOOR_Z + 0.003), (0.40, 0.42, 0.006), mat=MI['src_CP_Rubber'], bevel=0.004)  # footwell mat
for xx in (-0.35, 0.35):
    box(bm, (xx, -0.25, LY.FLOOR_Z + 0.008), (0.05, 2.9, 0.016), mat=MI['src_CP_Metal'])
    for yy in (-1.3, -0.7, -0.1, 0.5, 1.1):                     # tie-down D-rings
        path = [Vector((xx - 0.018, yy, LY.FLOOR_Z + 0.017)), Vector((xx - 0.018, yy, LY.FLOOR_Z + 0.04)),
                Vector((xx + 0.018, yy, LY.FLOOR_Z + 0.04)), Vector((xx + 0.018, yy, LY.FLOOR_Z + 0.017))]
        sweep(bm, path, 0.004, 0.004, 6, mat=MI['src_CP_Chrome'], up_hint=Vector((0, 1, 0)))
mk('CP_Floor', bm)


def bulkhead(y, z_max=None, inset=0.034, thick=0.02):
    ring = inner_ring(y, inset)
    if z_max is not None:
        ring = [(x, min(z, z_max)) for x, z in ring]
    bm = bmesh.new()
    for dy in (-thick / 2, thick / 2):
        vs = [bm.verts.new((x, y + dy, z)) for x, z in ring]
        bm.faces.new(vs).material_index = MI['src_CP_Bulkhead']
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


bm = bulkhead(LY.FIREWALL_Y, z_max=2.06)
join_bm(bm, bulkhead(LY.REAR_BULKHEAD_Y))
mk('CP_Bulkheads', bm)

# headliner: follows the wing centre-section underside (the wing box forms the cabin roof), ribs aft of it
W_LE, W_CH, W_Z0 = -2.55, 2.10, 2.648


def wing_lower(y):
    xc = (y - W_LE) / W_CH
    if xc <= 0.0 or xc >= 1.0:
        return 9.0
    return W_Z0 + naca(0.02, 0.4, 0.13, xc)[1][1] * W_CH


def shell_top(x, y):
    zb, zt, hw, n = station_at(y)
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    hw, hh = hw - 0.034, hh - 0.034
    t = min(1.0, abs(x) / hw)
    return zc + hh * (1 - t ** n) ** (1 / n)


def headliner_z(x, y):
    return min(shell_top(x, y) - 0.004, wing_lower(y) - 0.012)


bm = bmesh.new()
YS = [-2.645 + k * 0.08 for k in range(29)] + [-0.40]
XS = [-0.66 + k * 0.066 for k in range(21)]
grid = [[bm.verts.new((x, y, headliner_z(x, y))) for x in XS] for y in YS]
for i in range(len(YS) - 1):
    for j in range(len(XS) - 1):
        f = bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
        f.material_index = MI['src_CP_Trim']
for yy in (-2.10, -1.55, -1.00):                      # trim seams / lights on the headliner
    box(bm, (0, yy, headliner_z(0, yy) - 0.003), (1.2, 0.02, 0.006), mat=MI['src_CP_Black'])
for yy in (-1.30,):
    box(bm, (0, yy, headliner_z(0, yy) - 0.006), (0.22, 0.06, 0.012), mat=MI['src_CP_Lens'], bevel=0.004)
for yy in (-0.25, 0.35, 0.95):
    ring = [(x, z) for x, z in inner_ring(yy, 0.036, 64) if z > 2.0]
    ring.sort(key=lambda p: p[0])
    ribbon(bm, [(x, yy, z - 0.004) for x, z in ring], 0.045, 0.012, MI['src_CP_Trim'], up_hint=Vector((0, 0, 1)))
box(bm, (0, 0.35, 2.605), (0.22, 0.06, 0.012), mat=MI['src_CP_Lens'], bevel=0.004)
mk('CP_Headliner', bm, smooth=40)

# ================================================================== glareshield (lofted, padded lip that follows a curved plan)
bm = bmesh.new()
g = LY.GLARE
rings = []
for i in range(13):
    x = -g['hw'] + 2 * g['hw'] * i / 12
    yr = -2.975 - 0.022 * (x / g['hw']) ** 2
    yf = -3.255
    prof = [(yf, 2.020), (yf, 2.074), (yf + 0.08, 2.079), (yr - 0.03, 2.079)]
    for k in range(9):
        a = math.radians(90 - k * 22.5)
        prof.append((yr + 0.022 * math.cos(a), 2.054 + 0.022 * math.sin(a)))
    prof += [(yr - 0.03, 2.028), (yf + 0.05, 2.020)]
    rings.append([Vector((x, y, z)) for y, z in prof])
loft(bm, rings, True, True, True, mat=MI['src_CP_Glare'])
mk('CP_Glareshield', bm, smooth=50)

# ================================================================== instrument panel: face, sub-panel grooves, screws, knobs
bm = bmesh.new()
pz0, pz1 = LY.PANEL_Z
box(bm, (0, LY.PANEL_Y - 0.015, (pz0 + pz1) / 2), (LY.PANEL_HW * 2, 0.03, pz1 - pz0), mat=MI['src_CP_Panel'],
    bevel=0.006, bevel_segs=1)
box(bm, (0, LY.PANEL_Y - 0.10, pz0 - 0.02), (LY.PANEL_HW * 2, 0.20, 0.04), mat=MI['src_CP_Panel'], bevel=0.008)
GY = LY.PANEL_Y + 0.0008
for x0, x1, z0, z1 in ((0.160, 0.160, 1.46, 1.94), (-0.228, -0.228, 1.46, 1.94), (0.64, -0.64, 1.465, 1.465),
                       (0.160, -0.64, 1.94, 1.94)):
    if x0 == x1:
        box(bm, (x0, GY, (z0 + z1) / 2), (0.003, 0.0016, z1 - z0), mat=MI['src_CP_Black'])
    else:
        box(bm, ((x0 + x1) / 2, GY, z0), (abs(x1 - x0), 0.0016, 0.003), mat=MI['src_CP_Black'])
for sx0, sx1, sz0, sz1 in ((0.64, 0.17, 1.475, 2.01), (0.15, -0.218, 1.475, 1.935), (-0.238, -0.64, 1.475, 1.935)):
    for x in (sx0 - 0.012, sx1 + 0.012):
        for z in (sz0 + 0.012, sz1 - 0.012):
            screw(bm, x, z, LY.PANEL_Y)
# instrument screws + knobs
for name, (gx, gz, dia, cell, needles) in LY.GAUGES.items():
    R = dia / 2
    if dia >= LY.G6 or name in ('CLOCK', 'AMP', 'OAT'):
        for a in (45, 135, 225, 315):
            screw(bm, gx + math.cos(math.radians(a)) * R * 1.2, gz + math.sin(math.radians(a)) * R * 1.2, LY.PANEL_Y)
    for ang, rf in LY.GAUGE_KNOBS.get(name, []):
        a = math.radians(ang)
        kx, kz = gx - math.sin(a) * R * 1.02 * rf, gz + math.cos(a) * R * 1.02 * rf
        knurled(bm, kx, kz, LY.PANEL_Y, 0.0068, 0.014, MI['src_CP_Black'])
# annunciator panel + test button
ax, az, aw, ah, acell = LY.ANNUNCIATOR
box(bm, (ax, LY.PANEL_Y + 0.004, az), (aw + 0.008, 0.008, ah + 0.008), mat=MI['src_CP_Black'], bevel=0.002)


def placard(bm, idx, x_left, z_c, w=0.05, h=0.008, y=None):
    """small label from the placard region of T_Gauges (16 slots, 512x80 px each)"""
    y = LY.PANEL_Y + 0.0006 if y is None else y
    col, row = idx % 8, idx // 8
    u0, u1 = (col * 512 + 6) / 4096, (col * 512 + 506) / 4096
    v1, v0 = 1 - (1700 + row * 90) / 2048, 1 - (1780 + row * 90) / 2048
    rect_uv(bm, x_left, x_left - w, z_c - h / 2, z_c + h / 2, y, MI['src_CP_Gauges'], u0, u1, v0, v1)


placard(bm, 4, 0.555, 1.908, 0.045)          # PANEL LT
placard(bm, 5, 0.615, 1.908, 0.045)          # FLOOD LT
placard(bm, 0, 0.140, 1.448, 0.05)           # CABIN HEAT
placard(bm, 1, 0.070, 1.448, 0.05)           # DEFROST
placard(bm, 2, 0.545, 1.448, 0.05)           # PARK BRAKE
# circuit breakers with label strip
for i in range(3):
    for j in range(8):
        bx, bz = -0.26 - j * 0.045, 1.66 - i * 0.05
        cylinder(bm, (bx, LY.PANEL_Y, bz), (bx, LY.PANEL_Y + 0.006, bz), 0.0075, 0.0075, 12, mat=MI['src_CP_Black'])
        cylinder(bm, (bx, LY.PANEL_Y + 0.006, bz), (bx, LY.PANEL_Y + 0.014, bz), 0.0055, 0.005, 10,
                 mat=MI['src_CP_Black'])
# one label strip under each breaker row; texture columns are 125 px apart (= 45 mm breaker pitch)
PXM = 125 / 0.045
for i in range(3):
    zc = 1.66 - i * 0.05 - 0.0165
    hz = 15 / PXM
    xa, xb = -0.26 + 0.45 * 0.045, -0.26 - 7.45 * 0.045
    ua, ub = 1024 + 60 - 0.45 * 125, 1024 + 60 + 7.45 * 125
    vc = 1885 + 26 + i * 50
    rect_uv(bm, xa, xb, zc - hz, zc + hz, LY.PANEL_Y + 0.0005, MI['src_CP_Gauges'],
            ua / 4096, ub / 4096, 1 - (vc + 15) / 2048, 1 - (vc - 15) / 2048)
mk('CP_Panel', bm)

# annunciator lamps (v4): one quad per lamp, own material, lamp index in the second UV set (LampUV.x = i + 0.5)
bm = bmesh.new()
uv0 = bm.loops.layers.uv.new('UVMap')
uv1 = bm.loops.layers.uv.new('LampUV')
pl = plate_layer(bm)
ax, az, aw, ah, acell = LY.ANNUNCIATOR
col, row = acell % 8, acell // 8
HFR = 0.44                                   # annunciator image height / cell (gauges_tex.cell_annunciator)
yl = LY.PANEL_Y + 0.0083
for i in range(len(LY.ANNUN_LAMPS)):
    c, r = i % 4, i // 4
    x0 = ax + aw / 2 - c * aw / 4                # pilot-left edge (larger X) = texture left
    x1 = x0 - aw / 4
    z1 = az + ah / 2 - r * ah / 3
    z0 = z1 - ah / 3
    u0, u1 = (col + c / 4) / 8, (col + (c + 1) / 4) / 8
    v1, v0 = 1 - (row + r * HFR / 3) / 4, 1 - (row + (r + 1) * HFR / 3) / 4
    vs = [bm.verts.new(p) for p in ((x0, yl, z0), (x1, yl, z0), (x1, yl, z1), (x0, yl, z1))]
    f = bm.faces.new(vs)
    f.material_index = MI['src_CP_Annun']
    f[pl] = 1
    for lp, uv in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
        lp[uv0].uv = uv
        lp[uv1].uv = (i + 0.5, 0.5)
mk('CP_Annunciator', bm)
bm = bmesh.new()
tb = (ax - aw / 2 - 0.015, LY.PANEL_Y, az)
cylinder(bm, tb, (tb[0], LY.PANEL_Y + 0.008, tb[2]), 0.005, 0.005, 12, mat=MI['src_CP_KnobRed'])
mk(LY.ANNUN_TEST, bm, tb, axis='translate_fwd', note='push-to-test: pressed = 3 mm forward into the panel, all lamps on')

# ================================================================== gauges (bezels, faces, glass) + moving parts
bm = bmesh.new()
fy = LY.PANEL_Y + 0.003
for name, (gx, gz, dia, cell, needles) in LY.GAUGES.items():
    R = dia / 2
    prof = [(fy - 0.002, R - 0.004), (fy + 0.006, R - 0.003), (fy + 0.0095, R - 0.0012), (fy + 0.0085, R + 0.0008),
            (LY.PANEL_Y + 0.001, R + 0.002), (LY.PANEL_Y, R + 0.0035)]
    revolve(bm, prof, 'Y', (gx, 0, gz), segs=36, mat=MI['src_CP_Black'])
    if name == 'ATT':
        annulus(bm, (gx, gz), 0.027, R - 0.004, fy + 0.004, mat=MI['src_CP_Gauges'], uv_cell=cell)
        box(bm, (gx, fy + 0.006, gz), (0.036, 0.002, 0.003), mat=MI['src_CP_Orange'])
        box(bm, (gx, fy + 0.006, gz - 0.004), (0.004, 0.002, 0.008), mat=MI['src_CP_Orange'])
        disc(bm, (gx, gz), R - 0.004, fy - 0.001, mat=MI['src_CP_Black'])
    elif name == 'HDG':
        box(bm, (gx, fy + 0.006, gz + R * 0.83), (0.002, 0.002, 0.010), mat=MI['src_CP_Orange'])
        box(bm, (gx, fy + 0.006, gz), (0.026, 0.002, 0.003), mat=MI['src_CP_Orange'])
        box(bm, (gx, fy + 0.006, gz - 0.002), (0.003, 0.002, 0.020), mat=MI['src_CP_Orange'])
        disc(bm, (gx, gz), R - 0.004, fy - 0.001, mat=MI['src_CP_Black'])
    else:
        disc(bm, (gx, gz), R - 0.004, fy, mat=MI['src_CP_Gauges'], uv_cell=cell, uv_scale=1.0)
    disc(bm, (gx, gz), R - 0.003, fy + 0.0085, segs=24, mat=MI['src_CP_GaugeGlass'])
mk('CP_Gauges', bm, smooth=60)

for name, (gx, gz, dia, cell, needles) in LY.GAUGES.items():
    R = dia / 2 - 0.004
    for bone, frac, kind in needles:
        bm = bmesh.new()
        piv = (gx, fy + 0.003, gz)
        if kind in ('needle', 'needle_short'):
            ang = LY.NEEDLE_REST.get(bone, 0.0)
            w = 0.0035 if kind == 'needle' else 0.005
            needle_mesh(bm, gx, gz, fy + 0.003, R * frac, ang, w * (dia / LY.G6) ** 0.5, MI['src_CP_Needle'])
            mk(bone, bm, piv, axis='gauge', note=f'needle rest {ang:.0f} deg clockwise from 12 (pilot view)')
        elif kind == 'rollcard':
            bm2 = bmesh.new()
            disc(bm2, (gx, gz), 0.040, fy + 0.001, segs=40, mat=MI['src_CP_Gauges'], uv_cell=LY.ATT_CARD_CELL)
            mk('ATT_Pitch', bm2, piv, parent='ATT_Roll', axis='translate_up', note='card offset')
            bm.verts.new(piv)
            mk('ATT_Roll', bm, piv, axis='gauge', note='bank')
        elif kind == 'card':
            disc(bm, (gx, gz), R - 0.001, fy + 0.002, segs=40, mat=MI['src_CP_Gauges'], uv_cell=cell)
            mk(bone, bm, piv, axis='gauge', note='heading card')
        elif kind == 'plane':
            box(bm, (gx, fy + 0.004, gz), (R * 1.5, 0.002, 0.004), mat=MI['src_CP_Needle'])
            box(bm, (gx, fy + 0.004, gz + 0.004), (0.005, 0.002, 0.010), mat=MI['src_CP_Needle'])
            cylinder(bm, (gx, fy + 0.004, gz), (gx, fy + 0.006, gz), 0.006, 0.006, 12, mat=MI['src_CP_Needle'])
            mk(bone, bm, piv, axis='gauge', note='turn rate')
        elif kind == 'ball':
            arc_c = (gx, gz + 0.062 * dia / LY.G6)
            bz = gz - 0.022 * dia / LY.G6
            revolve(bm, [(fy + 0.001, 0.0), (fy + 0.002, 0.0035), (fy + 0.0045, 0.0045), (fy + 0.007, 0.0035),
                         (fy + 0.008, 0.0)], 'Y', (gx, 0, bz), segs=12, mat=MI['src_CP_Black'])
            mk(bone, bm, (arc_c[0], fy + 0.003, arc_c[1]), axis='gauge', note='slip ball')

# ================================================================== radio stack with knobs and buttons
bm = bmesh.new()
for name, (rx, rz, rw, rh, cell) in LY.RADIOS.items():
    box(bm, (rx, LY.PANEL_Y + 0.006, rz), (rw, 0.012, rh), mat=MI['src_CP_Black'], bevel=0.003)
    col, row = cell % 8, cell // 8
    frac = rh / rw
    rect_uv(bm, rx + rw / 2 - 0.002, rx - rw / 2 + 0.002, rz - rh / 2 + 0.002, rz + rh / 2 - 0.002,
            LY.PANEL_Y + 0.0125, MI['src_CP_Gauges'], col / 8, (col + 1) / 8, 1 - (row + frac) / 4, 1 - row / 4)
    y0 = LY.PANEL_Y + 0.012
    if name == 'GPSCOM':
        for kx in (rx + rw / 2 - 0.016, rx - rw / 2 + 0.016):
            kz = rz - rh / 2 + 0.016
            knurled(bm, kx, kz, y0, 0.0105, 0.009, MI['src_CP_Black'])
            knurled(bm, kx, kz, y0 + 0.009, 0.0065, 0.010, MI['src_CP_Black'])
        for i in range(5):
            bx = rx + rw / 2 - (0.30 + i * 0.105) * rw
            box(bm, (bx, y0 + 0.002, rz - rh / 2 + 0.011 * 0.6), (0.012, 0.004, 0.006), mat=MI['src_CP_Metal'],
                bevel=0.0012, bevel_segs=1)
        for i in range(2):
            knurled(bm, rx + rw / 2 - 0.016, rz + rh / 2 - 0.020 - i * 0.02, y0, 0.005, 0.007, MI['src_CP_Black'])
    elif name == 'AUDIO':
        for i in range(6):
            bx = rx + rw / 2 - (0.08 + i * 0.15 + 0.055) * rw
            box(bm, (bx, y0 + 0.002, rz), (0.016, 0.004, 0.018), mat=MI['src_CP_Metal'], bevel=0.0015, bevel_segs=1)
    elif name == 'XPDR':
        knurled(bm, rx - rw / 2 + 0.016, rz, y0, 0.0085, 0.012, MI['src_CP_Black'])
        for i in range(4):
            box(bm, (rx + rw / 2 - 0.020 - i * 0.014, y0 + 0.002, rz - 0.012), (0.010, 0.004, 0.007),
                mat=MI['src_CP_Metal'], bevel=0.001, bevel_segs=1)
    elif name == 'AP':
        for i in range(7):
            bx = rx + rw / 2 - (0.50 + i * 0.07 + 0.0275) * rw
            box(bm, (bx, y0 + 0.002, rz), (0.0085, 0.004, 0.016), mat=MI['src_CP_Metal'], bevel=0.001, bevel_segs=1)
mk('CP_Radios', bm)

# ================================================================== switches (hex nut + lever + ball), starter guard, labels
bm = bmesh.new()
rect_uv(bm, 0.64, 0.17, LY.SWITCH_Z - 0.036, LY.SWITCH_Z - 0.018, LY.PANEL_Y + 0.0005, MI['src_CP_Gauges'],
        0.0, 1.0, 1 - (3 * 512 + 160) / 2048, 1 - (3 * 512) / 2048)
for bone, sx in LY.SWITCHES:
    box(bm, (sx, LY.PANEL_Y + 0.0012, LY.SWITCH_Z), (0.024, 0.0024, 0.034), mat=MI['src_CP_Metal'], bevel=0.0015,
        bevel_segs=1)
    cylinder(bm, (sx, LY.PANEL_Y + 0.002, LY.SWITCH_Z), (sx, LY.PANEL_Y + 0.006, LY.SWITCH_Z), 0.0055, 0.0055, 6,
             mat=MI['src_CP_Chrome'])
sxs = dict(LY.SWITCHES)['SW_Starter']
box(bm, (sxs, LY.PANEL_Y + 0.013, LY.SWITCH_Z + 0.004), (0.020, 0.022, 0.030), mat=MI['src_CP_KnobRed'],
    bevel=0.003, bevel_segs=2)
for bone, ax_, az_, pslot in LY.AUX_SWITCHES:
    box(bm, (ax_, LY.PANEL_Y + 0.0012, az_), (0.024, 0.0024, 0.034), mat=MI['src_CP_Metal'], bevel=0.0015,
        bevel_segs=1)
    cylinder(bm, (ax_, LY.PANEL_Y + 0.002, az_), (ax_, LY.PANEL_Y + 0.006, az_), 0.0055, 0.0055, 6,
             mat=MI['src_CP_Chrome'])
    placard(bm, pslot, ax_ + 0.026, az_ - 0.026, 0.052)
mk('CP_Switchgear', bm)
for bone, ax_, az_, pslot in LY.AUX_SWITCHES:
    bm = bmesh.new()
    piv = Vector((ax_, LY.PANEL_Y + 0.006, az_))
    tip = Vector((ax_, LY.PANEL_Y + 0.024, az_ - 0.007))
    cylinder(bm, piv, tip, 0.0026, 0.0019, 8, mat=MI['src_CP_Chrome'])
    revolve(bm, [(-0.0035, 0.0), (-0.003, 0.0025), (0.0, 0.0036), (0.003, 0.0025), (0.0035, 0.0)], 'Y', tuple(tip),
            segs=10, mat=MI['src_CP_Chrome'])
    mk(bone, bm, tuple(piv), axis='lateral', note='toggle: rest OFF/CLOSE (down), ON/OPEN = lever up 40 deg')
for bone, sx in LY.SWITCHES:
    bm = bmesh.new()
    piv = Vector((sx, LY.PANEL_Y + 0.006, LY.SWITCH_Z))
    tip = Vector((sx, LY.PANEL_Y + 0.024, LY.SWITCH_Z - 0.007))
    cylinder(bm, piv, tip, 0.0026, 0.0019, 8, mat=MI['src_CP_Chrome'])
    revolve(bm, [(-0.0035, 0.0), (-0.003, 0.0025), (0.0, 0.0036), (0.003, 0.0025), (0.0035, 0.0)], 'Y', tuple(tip),
            segs=10, mat=MI['src_CP_Chrome'])
    mk(bone, bm, tuple(piv), axis='lateral', note='toggle: rest OFF (down), ON = lever up 40 deg')

# rheostats, pull knobs, fuel shutoff
for bone, rx, rz in LY.RHEOSTATS:
    bm = bmesh.new()
    knurled(bm, rx, rz, LY.PANEL_Y, 0.011, 0.014, MI['src_CP_Black'])
    box(bm, (rx, LY.PANEL_Y + 0.0145, rz + 0.007), (0.0015, 0.001, 0.006), mat=MI['src_CP_Needle'])
    mk(bone, bm, (rx, LY.PANEL_Y, rz), axis='gauge', note='rheostat 0..270 deg clockwise')
for bone, px, pz, kind in LY.PULL_KNOBS:
    bm = bmesh.new()
    y_face = LY.PANEL_Y
    cylinder(bm, (px, y_face - 0.01, pz), (px, y_face + 0.012, pz), 0.004, 0.004, 8, mat=MI['src_CP_Chrome'])
    if kind == 2:   # park brake T-handle
        box(bm, (px, y_face + 0.018, pz), (0.050, 0.014, 0.016), mat=MI['src_CP_Black'], bevel=0.005, bevel_segs=2)
    else:
        knurled(bm, px, pz, y_face + 0.012, 0.012, 0.012, MI['src_CP_Black'])
    mk(bone, bm, (px, y_face, pz), axis='translate_aft', note='pull towards the pilot, 0..6 cm')
    bm = bmesh.new()
    cylinder(bm, (px, y_face - 0.001, pz), (px, y_face + 0.003, pz), 0.009, 0.008, 12, mat=MI['src_CP_Chrome'])
    mk(f'CP_{bone}_Bezel', bm)

# ================================================================== yokes (ram-horn), column boots
for side, yx in (('P', LY.YOKE_X[0]), ('C', LY.YOKE_X[1])):
    hub = Vector((yx, LY.YOKE_HUB_Y, LY.YOKE_Z))
    bm = bmesh.new()                                     # static boot around the column hole
    prof = []
    for k in range(9):
        prof.append((LY.PANEL_Y + k * 0.006, 0.030 - k * 0.0012 + (0.004 if k % 2 else 0.0)))
    revolve(bm, [(LY.PANEL_Y - 0.001, 0.0)] + prof + [(LY.PANEL_Y + 0.048, 0.0)], 'Y', (yx, 0, LY.YOKE_Z), segs=20,
            mat=MI['src_CP_Rubber'])
    mk(f'CP_YokeBoot_{side}', bm)
    bm = bmesh.new()
    rbox(bm, (yx, (LY.PANEL_Y - 0.14 + hub.y - 0.02) / 2, LY.YOKE_Z), (0.030, hub.y - 0.02 - LY.PANEL_Y + 0.14, 0.030),
         MI['src_CP_Metal'], bevel=0.008, segs=2)
    mk(f'Yoke_{side}', bm, tuple(hub), axis='translate_fwd', note='pitch: push = forward, travel +-0.08 m')
    bm = bmesh.new()
    rbox(bm, hub + Vector((0, 0.005, 0.0)), (0.105, 0.036, 0.055), MI['src_CP_Black'], bevel=0.014, segs=3)
    rbox(bm, hub + Vector((0, 0.024, 0)), (0.06, 0.003, 0.026), MI['src_CP_Chrome'], bevel=0.002, segs=1)
    for sg in (1, -1):
        pts = [hub + Vector((sg * 0.045, 0.008, -0.005)), hub + Vector((sg * 0.095, 0.014, -0.022)),
               hub + Vector((sg * 0.135, 0.018, -0.012)), hub + Vector((sg * 0.152, 0.020, 0.02)),
               hub + Vector((sg * 0.156, 0.020, 0.06)), hub + Vector((sg * 0.152, 0.018, 0.10)),
               hub + Vector((sg * 0.140, 0.014, 0.125))]
        dense = []
        for a, b in zip(pts[:-1], pts[1:]):
            for t in range(4):
                dense.append(a.lerp(b, t / 4))
        dense.append(pts[-1])
        N = len(dense)
        rad = lambda u: (0.012 + 0.006 * min(1, max(0, (u - 0.35) / 0.2))) * (
            1.0 + (0.08 * math.sin(u * 60) if 0.45 < u < 0.92 else 0.0))
        sweep(bm, dense, rad, lambda u: rad(u) * 0.92, 12, mat=MI['src_CP_Black'], up_hint=Vector((0, 1, 0)))
        top = pts[-1]
        if sg == 1:                                       # pilot-left grip: trim rocker, PTT, AP disconnect
            rbox(bm, top + Vector((0, 0.004, 0.012)), (0.010, 0.018, 0.008), MI['src_CP_Metal'], bevel=0.002)
            cylinder(bm, pts[-2] + Vector((-0.012, 0.0, 0.0)), pts[-2] + Vector((-0.020, 0.0, 0.0)), 0.0055, 0.005, 10,
                     mat=MI['src_CP_KnobRed'])
            cylinder(bm, pts[-3] + Vector((0.0, -0.012, 0.0)), pts[-3] + Vector((0.0, -0.020, 0.0)), 0.005, 0.0045,
                     10, mat=MI['src_CP_KnobRed'])
        else:
            cylinder(bm, pts[-2] + Vector((0.012, 0.0, 0.0)), pts[-2] + Vector((0.020, 0.0, 0.0)), 0.0055, 0.005, 10,
                     mat=MI['src_CP_Metal'])
    mk(f'Yoke_{side}_Roll', bm, tuple(hub), parent=f'Yoke_{side}', axis='fwd', note='roll +-50 deg')

# ================================================================== rudder pedals with toe brakes, torque tubes, brake cylinders
bm = bmesh.new()
hy, hz = LY.PEDAL_HINGE
for sx in LY.SEATS_X:
    cylinder(bm, (sx + 0.16, hy, hz), (sx - 0.16, hy, hz), 0.012, 0.012, 10, mat=MI['src_CP_Metal'])
    for dx in (0.16, -0.16):
        rbox(bm, (sx + dx, hy, (hz + LY.FLOOR_Z) / 2), (0.02, 0.03, hz - LY.FLOOR_Z + 0.02), MI['src_CP_Metal'],
             bevel=0.003)
    for dx in (LY.PEDAL_DX, -LY.PEDAL_DX):
        cylinder(bm, (sx + dx, hy - 0.03, hz + 0.12), (sx + dx, LY.FIREWALL_Y + 0.01, hz + 0.16), 0.011, 0.011, 10,
                 mat=MI['src_CP_Metal'])
        box(bm, (sx + dx, -2.95, LY.FLOOR_Z + 0.009), (0.11, 0.13, 0.006), mat=MI['src_CP_Metal'], bevel=0.003)
mk('CP_PedalLinkage', bm)
for side, sx in (('P', LY.SEATS_X[0]), ('C', LY.SEATS_X[1])):
    for lr, dx in (('L', LY.PEDAL_DX), ('R', -LY.PEDAL_DX)):
        px = sx + dx
        bm = bmesh.new()
        box_rx(bm, (px, hy + 0.03, hz + 0.10), (0.018, 0.012, 0.21), -17.0, MI['src_CP_Metal'], bevel=0.003)
        box_rx(bm, (px, hy + 0.075, hz + 0.21), (0.082, 0.012, 0.16), -17.0, MI['src_CP_Black'], bevel=0.005, segs=2)
        for k in range(4):
            box_rx(bm, (px, hy + 0.083 + 0.0 * k, hz + 0.155 + k * 0.035), (0.07, 0.006, 0.006), -17.0,
                   MI['src_CP_Metal'])
        cylinder(bm, Vector((px - 0.03, hy, hz)), Vector((px + 0.03, hy, hz)), 0.014, 0.014, 12, mat=MI['src_CP_Black'])
        mk(f'Pedal{side}_{lr}', bm, (px, hy, hz), axis='lateral', note='rudder +-12 deg')

# ================================================================== pedestal: body, quadrant, levers, friction, flap, trim, shutoff
P = LY.PEDESTAL
bm = bmesh.new()
pts = [(P['hw'], P['y0'], LY.FLOOR_Z), (-P['hw'], P['y0'], LY.FLOOR_Z), (-P['hw'], P['y1'], LY.FLOOR_Z),
       (P['hw'], P['y1'], LY.FLOOR_Z), (P['hw'], P['y0'], P['z_top_front']), (-P['hw'], P['y0'], P['z_top_front']),
       (-P['hw'], P['y1'], P['z_top_back']), (P['hw'], P['y1'], P['z_top_back'])]
vs = [bm.verts.new(p) for p in pts]
for q in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
    bm.faces.new([vs[i] for i in q]).material_index = MI['src_CP_Panel']
py, pz = LY.LEVER_PIVOT
rings = []                                              # curved quadrant cover over the lever slots
for x in (-0.066, 0.066):
    ring = []
    for k in range(9):
        a = math.radians(-60 + k * 15)
        ring.append(Vector((x, py + 0.075 * math.sin(a), pz - 0.045 + 0.075 * math.cos(a))))
    ring += [Vector((x, py + 0.075 * math.sin(math.radians(60)), pz - 0.06)),
             Vector((x, py - 0.075 * math.sin(math.radians(60)), pz - 0.06))]
    rings.append(ring)
loft(bm, rings, True, True, True, mat=MI['src_CP_Black'])
for _, x, _ in LY.LEVERS:
    for k in range(9):
        a = math.radians(-50 + k * 12.5)
        box(bm, (x, py + 0.0752 * math.sin(a), pz - 0.045 + 0.0752 * math.cos(a)), (0.007, 0.012, 0.002),
            mat=MI['src_CP_Rubber'])
cylinder(bm, (-P['hw'], -2.76, 1.30), (-P['hw'] - 0.02, -2.76, 1.30), 0.012, 0.012, 16, mat=MI['src_CP_Black'])
box(bm, (0.078, -2.72, 1.24), (0.012, 0.19, 0.09), mat=MI['src_CP_Black'])
rbox(bm, (0.0, -2.30, 1.12), (0.02, 0.02, 0.10), MI['src_CP_Metal'])          # extinguisher bracket
revolve(bm, [(-2.44, 0.0), (-2.44, 0.036), (-2.43, 0.040), (-2.18, 0.040), (-2.16, 0.030), (-2.14, 0.018),
             (-2.12, 0.0)], 'Y', (0.0, 0, 1.13), segs=16, mat=MI['src_CP_KnobRed'])
rbox(bm, (0.0, -2.115, 1.165), (0.014, 0.05, 0.02), MI['src_CP_Black'], bevel=0.003)
mk('CP_Pedestal', bm)
KNOB = {'black': 'src_CP_Black', 'blue': 'src_CP_KnobBlue', 'red': 'src_CP_KnobRed'}
for bone, lx, kc in LY.LEVERS:
    piv = Vector((lx, py, pz))
    tip = piv + Vector((0, -0.05, 0.13))
    bm = bmesh.new()
    rbox(bm, piv.lerp(tip, 0.5), (0.006, 0.012, 0.14), MI['src_CP_Metal'], bevel=0.002)
    xform = Matrix.Translation(piv.lerp(tip, 0.5)) @ Matrix.Rotation(math.radians(21), 4, 'X') @ \
        Matrix.Translation(-piv.lerp(tip, 0.5))
    bmesh.ops.transform(bm, matrix=xform, verts=bm.verts)
    if kc == 'black':
        rbox(bm, tip + Vector((0, 0, 0.012)), (0.062, 0.024, 0.026), MI[KNOB[kc]], bevel=0.009, segs=3)
    elif kc == 'blue':
        knurled(bm, tip.x, tip.z + 0.015, tip.y - 0.012, 0.014, 0.024, MI[KNOB[kc]])
    else:
        rbox(bm, tip + Vector((0, 0, 0.014)), (0.024, 0.032, 0.03), MI[KNOB[kc]], bevel=0.007, segs=2)
    mk(bone, bm, tuple(piv), axis='lateral', note='rest = mid travel')
fb, fx, fyy, fz = LY.FLAP_LEVER
bm = bmesh.new()
piv = Vector((fx, fyy, fz))
tip = piv + Vector((-0.02, -0.02, 0.09))
cylinder(bm, piv, tip, 0.005, 0.005, 8, mat=MI['src_CP_Metal'])
airf = airfoil_ring(0, 1, 7, 0, 0, 0.25, True)[:-1]
rings = []
for dz in (-0.006, 0.006):
    rings.append([tip + Vector((0.0, -0.02 + xc * 0.04, 0.012 + dz)) + Vector((yc * 0.04, 0, 0)) for xc, yc in airf])
loft(bm, rings, True, True, True, mat=MI['src_CP_Needle'])
mk(fb, bm, tuple(piv), axis='lateral', note='flap detents')
tb, tx, ty, tz, tr = LY.TRIM_WHEEL
bm = bmesh.new()
prof = [(tx - 0.009, 0.0), (tx - 0.009, tr - 0.004), (tx - 0.006, tr), (tx + 0.006, tr), (tx + 0.009, tr - 0.004),
        (tx + 0.009, 0.0)]
revolve(bm, prof, 'X', (0, ty, tz), segs=48, mat=MI['src_CP_Black'],
        radial_fn=lambda i, j, r: r + (0.003 if (i % 2 == 0 and j in (2, 3)) else 0.0))
box(bm, (tx + 0.0095, ty, tz + tr - 0.012), (0.002, 0.012, 0.012), mat=MI['src_CP_Needle'])
mk(tb, bm, (tx, ty, tz), axis='lateral', note='trim')
bn, bx_, bz_ = LY.FUEL_SHUTOFF
bm = bmesh.new()
cylinder(bm, (bx_, P['y0'] - 0.01, bz_), (bx_, P['y0'] + 0.018, bz_), 0.004, 0.004, 8, mat=MI['src_CP_Chrome'])
rbox(bm, (bx_, P['y0'] + 0.024, bz_), (0.045, 0.014, 0.018), MI['src_CP_KnobRed'], bevel=0.006, segs=2)
mk(bn, bm, (bx_, P['y0'], bz_), axis='translate_aft', note='pull = fuel off')

# ================================================================== seats: sculpted cushions, bolsters, frame, armrest, harness
def subsurf_bm(src, levels=1):
    """Catmull-Clark via a temporary Subsurf modifier; keeps material_index and face int layers"""
    me = bpy.data.meshes.new('tmp_ss')
    src.to_mesh(me)
    ob = bpy.data.objects.new('tmp_ss', me)
    bpy.context.scene.collection.objects.link(ob)
    md = ob.modifiers.new('ss', 'SUBSURF')
    md.levels = md.render_levels = levels
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    out = bmesh.new()
    out.from_mesh(ev.to_mesh())
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    src.free()
    return out


def spline(pts, n=5):
    """Catmull-Rom densify a polyline (keeps the end points)"""
    P = [Vector(p) for p in pts]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    out.append(P[-2])
    return out


def smooth01(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def cushion_ring(hw, zb, zt, bol, n=28, r=0.03):
    top = lambda x: zt + bol * smooth01(0.12, 0.20, abs(x))
    pts = []
    for i in range(n // 4 + 1):
        pts.append((-hw + r + (2 * hw - 2 * r) * i / (n // 4), zb))
    for i in range(1, 4):
        a = -math.pi / 2 + math.pi / 2 * i / 4
        pts.append((hw - r + r * math.cos(a), zb + r + r * math.sin(a)))
    pts.append((hw, top(hw) - r))
    for i in range(1, 4):
        a = math.pi / 2 * i / 4
        pts.append((hw - r + r * math.cos(a), top(hw) - r + r * math.sin(a)))
    for i in range(n // 2 + 1):
        x = hw - r - (2 * hw - 2 * r) * i / (n // 2)
        pts.append((x, top(x)))
    for i in range(1, 4):
        a = math.pi / 2 + math.pi / 2 * i / 4
        pts.append((-hw + r + r * math.cos(a), top(-hw) - r + r * math.sin(a)))
    pts.append((-hw, zb + r))
    for i in range(1, 4):
        a = math.pi + math.pi / 2 * i / 4
        pts.append((-hw + r + r * math.cos(a), zb + r + r * math.sin(a)))
    return pts


SEAT = {}
for tag, sx in (('P', LY.SEATS_X[0]), ('C', LY.SEATS_X[1])):
    sy = -2.25
    bm = bmesh.new()
    rings = []                                             # seat cushion: loft front -> back
    for dy, sc_w, sc_h in ((-0.235, 0.88, 0.55), (-0.225, 0.96, 0.85), (-0.20, 1.0, 1.0), (0.0, 1.0, 0.96),
                           (0.17, 1.0, 0.9), (0.20, 0.97, 0.7)):
        hw, zb = 0.23 * sc_w, 1.335
        zt = zb + 0.085 * sc_h
        rings.append([Vector((sx + x, sy + dy, z)) for x, z in cushion_ring(hw, zb, zt, 0.035 * sc_h)])
    loft(bm, rings, True, True, True, mat=MI['src_CP_Leather'])
    bm = subsurf_bm(bm)                                    # soft upholstery instead of faceted lofts
    # backrest: loft bottom -> top in (x, y) then tilt aft about the hinge
    rings = []
    for dz, sc_w in ((0.0, 0.94), (0.02, 1.0), (0.30, 1.0), (0.52, 0.96), (0.58, 0.9), (0.60, 0.75)):
        ring = cushion_ring(0.23 * sc_w, -0.04, 0.035, 0.04)
        rings.append([Vector((sx + x, sy + 0.215 - (y - 0.0), 1.425 + dz)) for x, y in ring])
    bmb = bmesh.new()
    loft(bmb, rings, True, True, True, mat=MI['src_CP_Leather'])
    rbox(bmb, (sx, sy + 0.215, 2.10), (0.26, 0.085, 0.16), MI['src_CP_Leather'], bevel=0.03, segs=3)   # headrest
    bmb = subsurf_bm(bmb)
    for dx in (-0.08, 0.08):
        cylinder(bmb, (sx + dx, sy + 0.215, 2.02), (sx + dx, sy + 0.215, 2.035), 0.006, 0.006, 8,
                 mat=MI['src_CP_Chrome'])
    hinge = Vector((sx, sy + 0.215, 1.425))
    xform_bm(bmb, Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(-12), 4, 'X') @ Matrix.Translation(-hinge))
    join_bm(bm, bmb)
    # frame
    for dx in (-0.2, 0.2):
        sweep(bm, [Vector((sx + dx, sy - 0.22, 1.30)), Vector((sx + dx, sy + 0.20, 1.30)),
                   Vector((sx + dx, sy + 0.24, 1.36))], 0.011, 0.011, 8, mat=MI['src_CP_Metal'])
        for dy in (-0.18, 0.16):
            cylinder(bm, (sx + dx * 0.8, sy + dy, LY.FLOOR_Z + 0.02), (sx + dx, sy + dy, 1.30), 0.010, 0.010, 8,
                     mat=MI['src_CP_Metal'])
    rbox(bm, (sx, sy, 1.31), (0.40, 0.40, 0.03), MI['src_CP_Metal'], bevel=0.006)
    sweep(bm, [Vector((sx - 0.12, sy - 0.24, 1.29)), Vector((sx, sy - 0.27, 1.285)), Vector((sx + 0.12, sy - 0.24, 1.29))],
          0.005, 0.005, 8, mat=MI['src_CP_Metal'])                           # fore/aft adjust bar
    inboard = -1 if sx > 0 else 1
    rbox(bm, (sx + inboard * 0.255, sy + 0.02, 1.585), (0.055, 0.30, 0.05), MI['src_CP_Leather'], bevel=0.018, segs=3)
    cylinder(bm, (sx + inboard * 0.255, sy + 0.16, 1.58), (sx + inboard * 0.235, sy + 0.2, 1.50), 0.008, 0.008, 8,
             mat=MI['src_CP_Metal'])
    # harness (shoulder straps over the back, lap belts to a rotary buckle)
    tilt = lambda p: (Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(-12), 4, 'X') @
                      Matrix.Translation(-hinge)) @ Vector(p)
    buckle = Vector((sx, sy - 0.075, 1.465))
    # v4: harness as two switchable parts (SYS-02 / ALERT-01): Belt_<tag>_On (buckled) and Belt_<tag>_Off (open,
    # straps hanging at the backrest sides, lap belts over the cushion sides). Show one, scale the other to 0.
    bon, boff = bmesh.new(), bmesh.new()
    inb = -1 if sx > 0 else 1                                  # inboard direction (towards the aisle)
    for dx in (-0.075, 0.075):
        path = [tilt((sx + dx * 1.3, sy + 0.30, 2.00)), tilt((sx + dx * 1.2, sy + 0.23, 2.027)),
                tilt((sx + dx, sy + 0.165, 2.0)), tilt((sx + dx * 0.9, sy + 0.165, 1.80)),
                tilt((sx + dx * 0.6, sy + 0.165, 1.60)), buckle + Vector((dx * 0.35, 0.012, 0.03))]
        ribbon(bon, spline(path), 0.042, 0.004, MI['src_CP_Strap'], up_hint=Vector((0, 1, 0)))
        path = [Vector((sx + dx * 2.9, sy + 0.16, 1.43)), Vector((sx + dx * 2.6, sy + 0.05, 1.45)),
                Vector((sx + dx * 1.6, sy - 0.04, 1.458)), buckle + Vector((dx * 0.4, 0.004, 0.0))]
        ribbon(bon, spline(path), 0.042, 0.004, MI['src_CP_Strap'], up_hint=Vector((0, 0, 1)))
        # open: shoulder strap hangs down the backrest side, lap belt lies along the cushion side
        path = [tilt((sx + dx * 1.3, sy + 0.30, 2.00)), tilt((sx + dx * 1.2, sy + 0.23, 2.027)),
                tilt((sx + dx * 2.0, sy + 0.15, 1.99)), tilt((sx + dx * 2.6, sy + 0.128, 1.80)),
                tilt((sx + dx * 2.75, sy + 0.124, 1.60)), tilt((sx + dx * 2.8, sy + 0.118, 1.48))]
        ribbon(boff, spline(path), 0.042, 0.004, MI['src_CP_Strap'], up_hint=Vector((0, 1, 0)))
        sd = 1 if dx > 0 else -1
        path = [Vector((sx + sd * 0.2175, sy + 0.16, 1.43)), Vector((sx + sd * 0.240, sy + 0.08, 1.44)),
                Vector((sx + sd * 0.244, sy - 0.02, 1.43)), Vector((sx + sd * 0.242, sy - 0.11, 1.40))]
        ribbon(boff, spline(path), 0.042, 0.004, MI['src_CP_Strap'], up_hint=Vector((1, 0, 0)))
    revolve(bon, [(buckle.y - 0.004, 0.0), (buckle.y - 0.004, 0.034), (buckle.y - 0.012, 0.036),
                  (buckle.y - 0.016, 0.028), (buckle.y - 0.017, 0.0)], 'Y', (sx, 0, buckle.z + 0.01), segs=20,
            mat=MI['src_CP_Chrome'])
    boff_c = Vector((sx + inb * 0.250, sy - 0.13, 1.40))       # buckle hanging on the inboard lap belt
    revolve(boff, [(inb * 0.0, 0.0), (inb * 0.0, 0.034), (inb * 0.008, 0.036), (inb * 0.012, 0.028),
                   (inb * 0.013, 0.0)], 'X', tuple(boff_c), segs=20, mat=MI['src_CP_Chrome'])
    mk(f'Belt_{tag}_On', bon, tuple(buckle), axis='scale', note='harness buckled: scale 1 when buckled, 0 when open')
    mk(f'Belt_{tag}_Off', boff, tuple(boff_c), axis='scale', note='harness open: scale 1 when open, 0 when buckled')
    mk(f'CP_Seat_{tag}', bm, smooth=60)

# ================================================================== overhead console: fuel selectors, dome lights, vents
O_ = LY.OVERHEAD
bm = bmesh.new()
rings = []
for k in range(7):
    y = O_['y0'] + (O_['y1'] - O_['y0']) * k / 6
    zt = headliner_z(0, y) + 0.004
    zb_ = zt - O_['depth']
    hw = O_['hw']
    rings.append([Vector(p) for p in ((hw, y, zb_ + 0.01), (hw - 0.01, y, zb_), (-hw + 0.01, y, zb_), (-hw, y, zb_ + 0.01),
                                       (-hw, y, zt), (hw, y, zt))])
loft(bm, rings, True, True, True, mat=MI['src_CP_Trim'])
zc_at = lambda y: headliner_z(0, y) + 0.004 - O_['depth']
for x in (0.085, -0.085):
    revolve(bm, [(-0.012, 0.0), (-0.012, 0.022), (-0.006, 0.02), (0.0, 0.0)], 'Z', (x, -2.29, zc_at(-2.29)), segs=16,
            mat=MI['M_Light_Cabin'])
    revolve(bm, [(0.0, 0.0), (0.0, 0.017), (-0.004, 0.017), (-0.012, 0.012), (-0.016, 0.0)], 'Z',
            (x * 1.2, -2.40, zc_at(-2.40)), segs=14, mat=MI['src_CP_Metal'])
pl = plate_layer(bm)
uvl = bm.loops.layers.uv.verify()
zp = zc_at(-2.52) - 0.0006
vsq = [bm.verts.new(p) for p in ((0.09, -2.56, zp), (-0.09, -2.56, zp), (-0.09, -2.48, zp), (0.09, -2.48, zp))]
f = bm.faces.new(vsq)
f.material_index = MI['src_CP_Gauges']
f[pl] = 2
# seen from below by a pilot facing -Y: pilot-left (+X) must map to the left of the placard
for lp, uv in zip(f.loops, (((512 + 6) / 4096, 1 - 2041 / 2048), ((512 + 506) / 4096, 1 - 2041 / 2048),
                            ((512 + 506) / 4096, 1 - 1885 / 2048), ((512 + 6) / 4096, 1 - 1885 / 2048))):
    lp[uvl].uv = uv
mk('CP_Overhead', bm)

# cargo-bay dome light (v4): metal base + emissive lens in the cabin roof aft of the wing
bm = bmesh.new()
cy_ = LY.CARGO_LIGHT_Y
cz_ = headliner_z(0.0, cy_)
revolve(bm, [(0.0, 0.0), (0.0, 0.05), (-0.008, 0.05), (-0.010, 0.045), (-0.010, 0.0)], 'Z', (0.0, cy_, cz_), segs=20,
        mat=MI['src_CP_Metal'])
revolve(bm, [(-0.010, 0.0), (-0.010, 0.036), (-0.020, 0.030), (-0.026, 0.0)], 'Z', (0.0, cy_, cz_), segs=20,
        mat=MI['M_Light_Cabin'])
mk('CP_CargoLight', bm)
for bone, fx_ in LY.FUEL_SELECTORS:
    bm = bmesh.new()
    piv = Vector((fx_, -2.52, zc_at(-2.52)))
    rbox(bm, piv + Vector((0, 0, -0.035)), (0.012, 0.010, 0.07), MI['src_CP_KnobRed'], bevel=0.004)
    rbox(bm, piv + Vector((0, 0, -0.072)), (0.026, 0.02, 0.018), MI['src_CP_KnobRed'], bevel=0.006, segs=2)
    mk(bone, bm, tuple(piv), axis='lateral', note='fuel selector: ON = rest (down), OFF = rotate aft 60 deg')

# sun visors (stowed flat under the headliner)
for bone, vx in LY.VISORS:
    bm = bmesh.new()
    hinge = Vector((vx, -2.635, headliner_z(vx, -2.635) - 0.008))
    bmv = bmesh.new()
    rbox(bmv, hinge + Vector((0, 0.08, -0.006)), (0.30, 0.15, 0.008), MI['src_CP_Trim'], bevel=0.004)
    slope = math.atan2(headliner_z(vx, -2.635) - headliner_z(vx, -2.48), 0.155)
    xform_bm(bmv, Matrix.Translation(hinge) @ Matrix.Rotation(-slope, 4, 'X') @ Matrix.Translation(-hinge))
    join_bm(bm, bmv)
    cylinder(bm, hinge + Vector((0.15, 0, 0)), hinge + Vector((-0.15, 0, 0)), 0.005, 0.005, 8, mat=MI['src_CP_Metal'])
    mk(bone, bm, tuple(hinge), axis='lateral', note='visor: rest stowed, deploy = swing down 80 deg')

# compass hanging from the windshield centre post + correction card, eyeball vents, headsets
bm = bmesh.new()
cylinder(bm, (0, -2.64, 2.63), (0, -2.66, 2.575), 0.006, 0.006, 8, mat=MI['src_CP_Black'])
rbox(bm, (0, -2.665, 2.55), (0.072, 0.060, 0.052), MI['src_CP_Black'], bevel=0.01, segs=2)
rect_uv(bm, 0.022, -0.022, 2.54, 2.562, -2.6345, MI['src_CP_Gauges'], 5.30 / 8, 5.70 / 8, 1 - 0.58 / 4, 1 - 0.42 / 4)
rbox(bm, (0, -2.645, 2.506), (0.078, 0.006, 0.03), MI['src_CP_Black'], bevel=0.002, segs=1)
rect_uv(bm, 0.035, -0.035, 2.495, 2.518, -2.6415, MI['src_CP_Gauges'], 6 / 4096, 506 / 4096, 1 - 2041 / 2048,
        1 - 1885 / 2048)
for sgn in (1, -1):
    c = Vector((sgn * 0.655, -2.93, 1.99))
    revolve(bm, [(-0.012, 0.0), (-0.012, 0.022), (0.0, 0.02), (0.0, 0.0)], 'Y', tuple(c), segs=16,
            mat=MI['src_CP_Metal'])
    revolve(bm, [(0.0, 0.0), (0.0, 0.015), (0.008, 0.013), (0.012, 0.006), (0.013, 0.0)], 'Y', tuple(c), segs=14,
            mat=MI['src_CP_Black'])
mk('CP_Compass_Vents', bm)
bm = bmesh.new()
for sgn in (1, -1):
    hook = Vector((sgn * 0.675, -1.93, 2.24))
    cylinder(bm, hook, hook + Vector((-sgn * 0.04, 0, 0.0)), 0.004, 0.004, 8, mat=MI['src_CP_Chrome'])
    c = hook + Vector((-sgn * 0.03, 0, -0.085))
    arc_pts = [c + Vector((0, 0.085 * math.cos(math.radians(a)), 0.085 * math.sin(math.radians(a))))
               for a in range(15, 170, 15)]
    ribbon(bm, arc_pts, 0.01, 0.03, MI['src_CP_Headset'], up_hint=Vector((1, 0, 0)))
    for a in (15, 165):
        p = c + Vector((0, 0.085 * math.cos(math.radians(a)), 0.085 * math.sin(math.radians(a)) - 0.035))
        cylinder(bm, p + Vector((-0.02, 0, 0)), p + Vector((0.02, 0, 0)), 0.042, 0.04, 16, mat=MI['src_CP_Headset'])
    pm = c + Vector((0, 0.085 * math.cos(math.radians(15)), -0.03))
    sweep(bm, [pm, pm + Vector((0, -0.05, -0.04)), pm + Vector((0, -0.12, -0.05)), pm + Vector((0, -0.15, -0.03))],
          0.0035, 0.0035, 6, mat=MI['src_CP_Headset'])
    pc = c + Vector((0, 0.085 * math.cos(math.radians(165)), -0.07))
    sweep(bm, [pc, pc + Vector((0, 0.02, -0.25)), pc + Vector((-sgn * 0.02, 0.05, -0.55)),
               pc + Vector((-sgn * 0.05, -0.02, -0.72))], 0.004, 0.004, 6, mat=MI['src_CP_Headset'])
mk('CP_Headsets', bm)

# cargo net behind the seats (masked material)
bm = bmesh.new()
ring = [(x, z) for x, z in inner_ring(-1.66, 0.04, 64)]
vs = [bm.verts.new((x, -1.66, max(z, LY.FLOOR_Z + 0.03))) for x, z in ring]
f = bm.faces.new(vs)
f.material_index = MI['src_CP_Net']
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bmesh.ops.triangulate(bm, faces=bm.faces)
for sgn in (1, -1):
    ribbon(bm, [(sgn * 0.02, -1.66, LY.FLOOR_Z + 0.03), (sgn * 0.02, -1.66, 2.60)], 0.03, 0.004,
           MI['src_CP_Strap'], up_hint=Vector((0, 1, 0)))
mk('CP_CargoNet', bm)

# ================================================================== sockets + summary
SOCKETS = {'Socket_PilotEye': LY.PILOT_EYE, 'Socket_CopilotEye': LY.COPILOT_EYE}
json.dump(dict(rig=RIG, static=STATIC, sockets={k: list(v) for k, v in SOCKETS.items()}),
          open(os.path.join(HERE, 'out', 'cockpit_rig.json'), 'w'), indent=1)
tris = 0
dg = bpy.context.evaluated_depsgraph_get()
for ob in CP.objects:
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    tris += len(me.loop_triangles)
    ob.evaluated_get(dg).to_mesh_clear()
print('COCKPIT objects', len(CP.objects), 'tris', tris, 'moving parts', len(RIG))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v2.blend'))
print('saved')
