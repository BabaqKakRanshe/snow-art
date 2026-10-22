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
    # v5 interior shell (atlas "Interior")
    'src_IN_Liner': (0.20, 0.20, 0.19), 'src_IN_Kick': (0.025, 0.026, 0.028), 'src_IN_Headliner': (0.30, 0.295, 0.28),
    'src_IN_Tread': (0.38, 0.38, 0.37), 'src_IN_Track': (0.30, 0.30, 0.31), 'src_IN_Steel': (0.45, 0.45, 0.44),
    'src_IN_Composite': (0.035, 0.037, 0.04), 'src_IN_Insul': (0.25, 0.25, 0.24), 'src_IN_Trim': (0.03, 0.03, 0.032),
    'src_IN_Seal': (0.012, 0.012, 0.012), 'src_IN_FloorPaint': (0.035, 0.036, 0.038),
    'src_IN_Vinyl': (0.045, 0.045, 0.046), 'src_IN_Hidden': (0.03, 0.03, 0.03),
    # v5 seats (atlas "Seats")
    'src_ST_Leather': (0.10, 0.07, 0.045), 'src_ST_Metal': (0.10, 0.10, 0.10), 'src_ST_Strap': (0.02, 0.025, 0.03),
    'src_ST_Chrome': (0.6, 0.6, 0.6), 'src_ST_Plastic': (0.02, 0.02, 0.022), 'src_ST_Fabric': (0.06, 0.06, 0.055),
    # v5 tiled webbing (cargo barrier nets, tie-down straps): own small texture, UV along the strap
    'src_IN_Webbing': (0.07, 0.08, 0.04),
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
    """plate 0: closed solids, recalculated; plate 1: flat plates facing the pilot (+Y);
    plate 2: open panels already oriented by their builder (v5 shell) - left alone"""
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


def head_z(y):
    """v5 headliner height at station y: 10 mm under the lining top (liner face = skin + 25 mm gap),
    15 mm under the wing centre section where the wing box dips into the cabin roof"""
    zb, zt, hw, n = station_at(y)
    return min(zt - LY.SKIN_T - 0.035, wing_lower(y) - 0.015)


def headliner_z(x, y):
    return head_z(y)


# ================================================================== instrument panel: face, sub-panel grooves, screws, knobs
bm = bmesh.new()
pz0, pz1 = LY.PANEL_Z
# v5 sub-panels (x_left, x_right, z_bottom, z_top): pilot, engine strip, centre stack, copilot; mounted flush with
# PANEL_Y on the panel frame (which sits 3 mm behind)
SUBPANELS = [(0.640, 0.162, 1.455, 2.028), (0.158, -0.640, 1.939, 2.028), (0.158, -0.218, 1.455, 1.937),
             (-0.236, -0.640, 1.455, 1.937)]
for sx0, sx1, sz0, sz1 in SUBPANELS:
    for x in (sx0 - 0.010, sx1 + 0.010):
        for z in (sz0 + 0.010, sz1 - 0.010):
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
            bm.free()
            e = bpy.data.objects.new('ATT_Roll', None)
            e.empty_display_size = 0.02
            CP.objects.link(e)
            e.location = piv
            RIG['ATT_Roll'] = dict(pivot=list(piv), parent='Cockpit', axis='gauge', note='bank (empty transform)')
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

for bone, fx_ in LY.FUEL_SELECTORS:
    bm = bmesh.new()
    piv = Vector((fx_, -2.52, zc_at(-2.52)))
    rbox(bm, piv + Vector((0, 0, -0.035)), (0.012, 0.010, 0.07), MI['src_CP_KnobRed'], bevel=0.004)
    rbox(bm, piv + Vector((0, 0, -0.072)), (0.026, 0.02, 0.018), MI['src_CP_KnobRed'], bevel=0.006, segs=2)
    mk(bone, bm, tuple(piv), axis='lateral', note='fuel selector: ON = rest (down), OFF = rotate aft 60 deg')

# compass hanging from the windshield centre post + correction card, eyeball vents, headsets
bm = bmesh.new()
CZ = -0.03                     # v5: compass hangs 30 mm lower, clear of the inner skin and the windshield frame
cylinder(bm, (0, -2.64, 2.60), (0, -2.66, 2.575 + CZ), 0.006, 0.006, 8, mat=MI['src_CP_Black'])
rbox(bm, (0, -2.665, 2.55 + CZ), (0.072, 0.060, 0.052), MI['src_CP_Black'], bevel=0.01, segs=2)
rect_uv(bm, 0.022, -0.022, 2.54 + CZ, 2.562 + CZ, -2.6345, MI['src_CP_Gauges'], 5.30 / 8, 5.70 / 8, 1 - 0.58 / 4,
        1 - 0.42 / 4)
rbox(bm, (0, -2.645, 2.506 + CZ), (0.078, 0.006, 0.03), MI['src_CP_Black'], bevel=0.002, segs=1)
rect_uv(bm, 0.035, -0.035, 2.495 + CZ, 2.518 + CZ, -2.6415, MI['src_CP_Gauges'], 6 / 4096, 506 / 4096,
        1 - 2041 / 2048, 1 - 1885 / 2048)
for sgn in (1, -1):
    c = Vector((sgn * 0.655, -2.93, 1.99))
    revolve(bm, [(-0.012, 0.0), (-0.012, 0.022), (0.0, 0.02), (0.0, 0.0)], 'Y', tuple(c), segs=16,
            mat=MI['src_CP_Metal'])
    revolve(bm, [(0.0, 0.0), (0.0, 0.015), (0.008, 0.013), (0.012, 0.006), (0.013, 0.0)], 'Y', tuple(c), segs=14,
            mat=MI['src_CP_Black'])
mk('CP_Compass_Vents', bm)

# ================================================================== v5 INTERIOR SHELL (Caravan-style lined cabin)
# Lining profile in arc-length coordinates; chamfered liner panels that follow the fuselage section and the
# wing-box headliner; window/door trims and seals; floor, seat tracks, cargo tracks, tie-downs; headliner with
# the ventilation plenum; bulkhead liners; windshield frame trims; cargo barrier with webbing nets.
# Interior atlas materials (src_IN_*), webbing on its own tiled material.
import bisect
from mathutils import geometry as mgeo

LIN = LY.SKIN_T + 0.025            # liner face inset from the outer skin (25 mm insulation gap)
FZ = LY.FLOOR_Z
BARRIER_Y = -1.72
REAR_Y = LY.REAR_BULKHEAD_Y - 0.02
Z_KICK = 1.28                      # top of the dark kick strip
PD = LY.PILOT_DOOR[0]
CD = LY.CARGO_DOOR[0]
PD_FWD = PD[0][0] - 0.035          # -3.155 footwell kick panel ends at the pilot door
PD_AFT = PD[1][0] + 0.035          # -1.945 wall liner starts aft of the pilot door
CD_FWD = CD[0][0] - 0.035          # -0.885
CD_AFT = CD[1][0] + 0.035          # 0.485
WS_AFT_Y = LY.WS_L[0][2][1]        # -2.65 windshield aft edge
WS_X = LY.WS_L[0][1][0]            # 0.655 windshield outer edge
TRACK_X = (0.42, 0.0, -0.42)
TIE_Y = (-1.45, -0.80, -0.15, 0.50, 1.10)
HX0 = 0.105                        # plenum half width (headliner panels start here)
DY = 0.005
_SEC = {}


# ------------------------------------------------------------------ lining profile (right half, inset LIN)
def _section(y):
    zb, zt, hw, ne = station_at(y)
    return (round(zb, 5), round(zt, 5), round(hw, 5), round(ne, 4))


def _curve(sec):
    """(X, Z, S) from the floor up to the roof centre, S = arc length"""
    if sec in _SEC:
        return _SEC[sec]
    zb, zt, hw, ne = sec
    zc, b, a = (zb + zt) / 2, (zt - zb) / 2 - LIN, hw - LIN
    tf = min(1.0, (zc - FZ) / b)
    X, Z = [a * (1 - tf ** ne) ** (1 / ne)], [FZ]
    N = 3000
    for k in range(N + 1):
        th = -math.pi / 2 + math.pi * k / N
        c, s_ = math.cos(th), math.sin(th)
        z = zc + b * math.copysign(abs(s_) ** (2 / ne), s_)
        if z <= Z[-1] + 1e-9:
            continue
        X.append(a * abs(c) ** (2 / ne))
        Z.append(z)
    S = [0.0]
    for k in range(1, len(X)):
        S.append(S[-1] + math.hypot(X[k] - X[k - 1], Z[k] - Z[k - 1]))
    _SEC[sec] = (X, Z, S)
    return _SEC[sec]


def _pair(y):
    f = y / DY
    i0 = math.floor(f)
    return _curve(_section(i0 * DY)), _curve(_section((i0 + 1) * DY)), f - i0


def _s_at_z(C, z):
    X, Z, S = C
    if z <= Z[0]:
        return 0.0
    if z >= Z[-1]:
        return S[-1]
    k = bisect.bisect_left(Z, z)
    dz = Z[k] - Z[k - 1]
    t = (z - Z[k - 1]) / dz if dz > 0 else 0.0
    return S[k - 1] + (S[k] - S[k - 1]) * t


def _at_s(C, s):
    X, Z, S = C
    s = min(max(s, 0.0), S[-1])
    k = min(max(1, bisect.bisect_left(S, s)), len(S) - 1)
    ds = S[k] - S[k - 1]
    t = (s - S[k - 1]) / ds if ds > 0 else 0.0
    L = ds if ds > 0 else 1.0
    return (X[k - 1] + (X[k] - X[k - 1]) * t, Z[k - 1] + (Z[k] - Z[k - 1]) * t,
            (X[k] - X[k - 1]) / L, (Z[k] - Z[k - 1]) / L)


def s_of_z(y, z):
    A, B, t = _pair(y)
    return _s_at_z(A, z) * (1 - t) + _s_at_z(B, z) * t


def wall_frame(y, s):
    """(x, z, tx, tz): lining point at arc length s and the unit tangent (pointing up the profile)"""
    A, B, t = _pair(y)
    a, b = _at_s(A, s), _at_s(B, s)
    x, z, tx, tz = [a[i] + (b[i] - a[i]) * t for i in range(4)]
    L = math.hypot(tx, tz) or 1.0
    return x, z, tx / L, tz / L


def wall_pt(side, y, s, d=0.0):
    """point on the lining surface (side +1 = left / +X), d = offset along the inward normal"""
    x, z, tx, tz = wall_frame(y, s)
    return Vector((side * (x - tz * d), y, z + tx * d))


def wall_in(side, p):
    x, z, tx, tz = wall_frame(p.y, s_of_z(p.y, p.z))
    return Vector((-side * tz, 0.0, tx))


def surf_x_any(y, z, inset):
    zb, zt, hw, ne = station_at(y)
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    a, b = hw - inset, hh - inset
    t = min(0.999999, abs(z - zc) / b)
    return a * (1 - t ** ne) ** (1 / ne)


def surf_z_top(y, x, inset):
    zb, zt, hw, ne = station_at(y)
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    a, b = hw - inset, hh - inset
    return zc + b * max(0.0, 1 - (abs(x) / a) ** ne) ** (1 / ne)


def x_floor(y):
    return surf_x_any(y, FZ, LIN)


def s_junction(y):
    """the wall liner ends 12 mm under the headliner"""
    return s_of_z(y, head_z(y) - 0.012)


# ------------------------------------------------------------------ 2D polygon helpers + chamfered panel builder
def dedupe(P, eps=1e-6):
    out = []
    for p in P:
        if not out or math.dist(p, out[-1]) > eps:
            out.append(tuple(p))
    while len(out) > 2 and math.dist(out[0], out[-1]) <= eps:
        out.pop()
    return out


def offs(P, d):
    """offset a convex(ish) polygon by d (+ = outward), either winding; collinear neighbours handled"""
    n = len(P)
    area = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))
    sg = 1 if area > 0 else -1
    lines = []
    for i in range(n):
        p, q = P[i], P[(i + 1) % n]
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        nx, ny = uy * sg, -ux * sg
        lines.append(((p[0] + nx * d, p[1] + ny * d), (ux, uy), (nx, ny)))
    out = []
    for i in range(n):
        (p1, d1, n1), (p2, d2, n2) = lines[i - 1], lines[i]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-6:
            out.append((P[i][0] + (n1[0] + n2[0]) / 2 * d, P[i][1] + (n1[1] + n2[1]) / 2 * d))
        else:
            t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
            out.append((p1[0] + d1[0] * t, p1[1] + d1[1] * t))
    return out


def densify(polys, step):
    """subdivide matching polygons edge by edge with equal counts (keeps the point correspondence)"""
    n = len(polys[0])
    out = [[] for _ in polys]
    for i in range(n):
        j = (i + 1) % n
        L = max(math.dist(P[i], P[j]) for P in polys)
        k = max(1, int(math.ceil(L / step)))
        for t in range(k):
            f = t / k
            for P, O in zip(polys, out):
                O.append((P[i][0] + (P[j][0] - P[i][0]) * f, P[i][1] + (P[j][1] - P[i][1]) * f))
    return out


def orient(f, inward, bm=None):
    """face normal towards `inward`; marks the face as pre-oriented (plate 2) so mk() keeps it"""
    f.normal_update()
    if f.normal.dot(inward) < 0:
        f.normal_flip()
    if bm is not None:
        f[plate_layer(bm)] = 2


def panel2d(bm, O, holes, mapf, inward_fn, depth=0.005, cham=0.005, mat=0, grid=0.07, back=False, step=0.035,
            back_mat=None):
    """chamfered panel from an outline O (u, v) with holes; mapf(u, v, d) -> world point, inward_fn(p) -> direction
    into the cabin. Face at depth `depth`, chamfer from the outline (depth 0). Edges are densified so the
    boundary follows curved mappings. Chamfers share the face boundary vertices (one UV island per panel);
    panels with a hole are cut in two through the hole (no hollow islands in the atlas)."""
    plate_layer(bm)                      # create the layer before holding face references
    O = dedupe(O)
    O, I = densify([O, offs(O, -cham)], step)
    HH = []
    for H in holes:
        H = dedupe(H)
        HH.append(densify([H, offs(H, cham)], step))
    Hs = [h[1] for h in HH]
    loops = [I] + Hs
    pts = [p for L in loops for p in L]
    us, vs = [p[0] for p in I], [p[1] for p in I]
    u = min(us) + grid / 2
    while u < max(us):
        v = min(vs) + grid / 2
        while v < max(vs):
            q = (u, v)
            if LY.point_in_poly(q, I) and not any(LY.point_in_poly(q, H) for H in Hs):
                if min(math.dist(q, p) for p in pts) > grid * 0.45:
                    pts.append(q)
            v += grid
        u += grid
    edges = []
    k = 0
    for L in loops:
        n = len(L)
        edges += [(k + i, k + (i + 1) % n) for i in range(n)]
        k += n
    res = mgeo.delaunay_2d_cdt([Vector(p) for p in pts], edges, [list(range(len(I)))], 1, 1e-7)
    vco, faces, orig = res[0], res[2], res[3]
    inmap = {}
    for oi, srcs in enumerate(orig):
        for s_ in srcs:
            inmap[s_] = oi
    bv = [bm.verts.new(mapf(p.x, p.y, depth)) for p in vco]
    made = []
    for fi in faces:
        c = (sum(vco[i].x for i in fi) / len(fi), sum(vco[i].y for i in fi) / len(fi))
        if any(LY.point_in_poly(c, H) for H in Hs):
            continue
        try:
            f = bm.faces.new([bv[i] for i in fi])
        except ValueError:
            continue
        f.material_index = mat
        orient(f, inward_fn(f.calc_center_median()), bm)
        made.append((f, c[0]))

    def strip(A, k0, dA):
        n = len(A)
        va = [bm.verts.new(mapf(p[0], p[1], dA)) for p in A]
        vb = [bv[inmap[k0 + i]] for i in range(n)]
        for i in range(n):
            j = (i + 1) % n
            try:
                f = bm.faces.new((va[i], va[j], vb[j], vb[i]))
            except ValueError:
                continue
            f.material_index = mat
            orient(f, inward_fn(f.calc_center_median()), bm)
            made.append((f, (A[i][0] + A[j][0]) / 2))
    strip(O, 0, 0.0)
    k = len(I)
    for H, H2 in HH:
        strip(H, k, 0.0)
        k += len(H2)
    if holes:
        uc = sum(p[0] for p in holes[0]) / len(holes[0])
        side_of = {f: (cu < uc) for f, cu in made}
        cut = set()
        for f, cu in made:
            for e in f.edges:
                lf = [g for g in e.link_faces if g in side_of]
                if len(lf) == 2 and side_of[lf[0]] != side_of[lf[1]]:
                    cut.add(e)
        if cut:
            bmesh.ops.split_edges(bm, edges=list(cut))
    if back:            # flat back for free-standing panels
        bb = [bm.verts.new(mapf(p[0], p[1], 0.0)) for p in O]
        f = bm.faces.new(bb)
        f.material_index = mat if back_mat is None else back_mat
        orient(f, -inward_fn(f.calc_center_median()), bm)


def rrect(u0, u1, v0, v1, r):
    return LY.rounded_poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], r, seg=3)


class Band:
    """wall strip between s = lo(y) and s = hi(y); panel coords (y, w) with w in metre-like units [0, H]"""

    def __init__(self, lo, hi, y0, y1):
        self.lo, self.hi = lo, hi
        self.H = sum(hi(y) - lo(y) for y in (y0, (y0 + y1) / 2, y1)) / 3

    def s(self, y, w):
        a, b = self.lo(y), self.hi(y)
        return a + (b - a) * w / self.H

    def w(self, y, s):
        a, b = self.lo(y), self.hi(y)
        return (s - a) * self.H / (b - a)


def wall_panel(bm, side, y0, y1, lo, hi, depth, cham, mat, r=0.012, wins=(), grow=0.014, grid=0.07, base_d=0.0):
    B = Band(lo, hi, y0, y1)
    if B.H < 0.008:
        return None
    holes = []
    for outline, wr in wins:
        pts = LY.rounded_poly(LY.offset_poly(outline, grow), wr + grow, seg=4)
        pts = densify([dedupe(pts)], 0.025)[0]
        holes.append([(y, B.w(y, s_of_z(y, z))) for y, z in pts])
    rr = max(cham + 0.001, min(r, B.H / 2 - 0.0005))
    panel2d(bm, rrect(y0, y1, 0.0, B.H, rr), holes,
            lambda u, v, d: wall_pt(side, u, B.s(u, v), d + base_d),
            lambda p: wall_in(side, p), depth=depth, cham=cham, mat=mat, grid=grid)
    return B


def prof_sweep(bm, path, prof, mat, up_hint=Vector((0, 0, 1)), caps=True):
    """sweep a closed 2D profile (a along tangent x up, b along up) along a polyline"""
    rings = []
    N = len(path)
    for k in range(N):
        p = Vector(path[k])
        tng = (Vector(path[min(k + 1, N - 1)]) - Vector(path[max(k - 1, 0)])).normalized()
        sv = tng.cross(up_hint).normalized()
        uv_ = sv.cross(tng).normalized()
        rings.append([p + sv * a + uv_ * b for a, b in prof])
    loft(bm, rings, True, caps, caps, mat)


def rr_prof(a0, a1, b0, b1, r, seg=2):
    """rounded rectangle profile for prof_sweep"""
    return LY.rounded_poly([(a0, b0), (a1, b0), (a1, b1), (a0, b1)], r, seg=seg)


# ------------------------------------------------------------------ wall liners (Kydex-like sidewall panels)
LINER = bmesh.new()
kick_hi = lambda y: s_of_z(y, Z_KICK)
zero = lambda y: 0.0
for side in (1, -1):
    for y0, y1, wins in ((PD_AFT, -1.20, [LY.W2]), (-1.20, CD_FWD, []), (CD_AFT, REAR_Y, [LY.W4])):
        wall_panel(LINER, side, y0, y1, kick_hi, s_junction, 0.006, 0.006, MI['src_IN_Liner'], wins=wins)
        wall_panel(LINER, side, y0, y1, zero, kick_hi, 0.014, 0.007, MI['src_IN_Kick'], r=0.010, grid=0.06)
    # strip above the cargo door (door surround .. headliner)
    wall_panel(LINER, side, CD_FWD, CD_AFT, lambda y: s_of_z(y, CD[2][1] + 0.033), s_junction, 0.006, 0.004,
               MI['src_IN_Liner'], r=0.006, grid=0.05)
    # footwell side kick panel forward of the pilot door (floor .. behind the instrument panel)
    y0, y1 = LY.FIREWALL_Y + 0.01, PD_FWD
    wall_panel(LINER, side, y0, y1, zero, lambda y: s_of_z(y, 1.62), 0.010, 0.006, MI['src_IN_Kick'], r=0.010,
               grid=0.05)
    # fresh-air outlet in the kick panel
    yc = (y0 + y1) / 2
    p = wall_pt(side, yc, s_of_z(yc, 1.32), 0.010)
    revolve(LINER, [(0.0, 0.0), (0.0, 0.028), (-side * 0.006, 0.026), (-side * 0.010, 0.016), (-side * 0.012, 0.0)],
            'X', (p.x, p.y, p.z), segs=16, mat=MI['src_IN_Trim'])
    for k in range(3):                                         # louvre vanes
        box(LINER, (p.x - side * 0.010, p.y, p.z - 0.012 + k * 0.012), (0.004, 0.036, 0.003), mat=MI['src_IN_Trim'])
    # strut-fitting cover plate on the kick strip (strut attaches outside at y ~ -1.55)
    yc = -1.55
    wall_panel(LINER, side, yc - 0.07, yc + 0.07, lambda y: s_of_z(y, 1.12), lambda y: s_of_z(y, 1.26), 0.004,
               0.002, MI['src_IN_Steel'], r=0.010, grid=0.04, base_d=0.014)
    for uu in (yc - 0.052, yc + 0.052):
        for zz in (1.14, 1.24):
            p = wall_pt(side, uu, s_of_z(uu, zz), 0.018)
            n_ = wall_in(side, p)
            cylinder(LINER, p, p + n_ * 0.003, 0.0055, 0.0042, 8, mat=MI['src_IN_Steel'])
mk('CP_Liner', LINER)


# ------------------------------------------------------------------ window and door trims (closeouts) + seals
def surround(bm, side, outline, r, grow_in, mat, lip=0.006, shallow=None, step=0.025):
    """trim ring: jamb from the inner skin at the opening to the trim face, bezel onto the liner, hidden flange.
    shallow(y, z) -> 0..1 blends to a thin frame on the inner skin where no liner borders the opening."""
    plate_layer(bm)
    base = LY.rounded_poly(outline, r, seg=4)
    gin = LY.rounded_poly(LY.offset_poly(outline, grow_in), r + grow_in, seg=4)
    glp = LY.rounded_poly(LY.offset_poly(outline, grow_in + lip), r + grow_in + lip, seg=4)
    base, gin, glp = densify([base, gin, glp], step)
    cy = sum(p[0] for p in outline) / len(outline)
    cz = sum(p[1] for p in outline) / len(outline)
    rings = []
    for (ys, zs), (yi, zi), (yl, zl) in zip(base, gin, glp):
        h = shallow(ys, zs) if shallow else 0.0
        fi = (grow_in * (1 - h) + 0.004 * h) / grow_in
        fl = ((grow_in + lip) * (1 - h) + 0.008 * h) / (grow_in + lip)
        yi, zi = ys + (yi - ys) * fi, zs + (zi - zs) * fi
        yl, zl = ys + (yl - ys) * fl, zs + (zl - zs) * fl
        di = (LIN + 0.010) * (1 - h) + (LY.SKIN_T + 0.008) * h
        dl = (LIN + 0.002) * (1 - h) + (LY.SKIN_T + 0.004) * h
        if h > 0.0:
            cap = head_z(yi) - 0.004
            zi, zl = min(zi, cap), min(zl, cap + 0.001)
        rings.append([Vector((side * surf_x_any(ys, zs, LY.SKIN_T + 0.002), ys, zs)),
                      Vector((side * surf_x_any(yi, zi, di), yi, zi)),
                      Vector((side * surf_x_any(yl, zl, dl), yl, zl)),
                      Vector((side * surf_x_any(yl, zl, dl - 0.006), yl, zl))])
    n = len(rings)
    vr = [[bm.verts.new(p) for p in r_] for r_ in rings]
    cuts = {0, n // 4, n // 2, 3 * n // 4}                 # quarter rings: no hollow islands in the atlas
    vdup = {c: [bm.verts.new(p) for p in rings[c]] for c in cuts}
    for i in range(n):
        j = (i + 1) % n
        ri = vdup[i] if i in cuts else vr[i]
        for k in range(3):
            try:
                f = bm.faces.new((ri[k], vr[j][k], vr[j][k + 1], ri[k + 1]))
            except ValueError:
                continue
            f.material_index = mat
            fc = f.calc_center_median()
            radial = Vector((0, fc.y - cy, fc.z - cz)).normalized()
            # k0: jamb, faces the opening centre; k1: bezel, faces the cabin; k2: hidden flange, faces outward
            ref = (-radial + Vector((-side * 0.3, 0, 0))) if k == 0 else (
                Vector((-side, 0, 0)) if k == 1 else radial)
            orient(f, ref, bm)


def pd_shallow(y, z):
    """pilot door: no wall liner along the top and the windshield-side slope"""
    zl = 1.95 + (2.50 - 1.95) * (y - PD[0][0]) / (PD[1][0] - PD[0][0])
    return smooth01(zl - 0.03, zl + 0.03, z)


TRIM = bmesh.new()
SEAL = bmesh.new()
for side in (1, -1):
    for w in LY.SIDE_FIXED['L']:
        surround(TRIM, side, w[0], w[1], 0.014, MI['src_IN_Trim'])
    surround(TRIM, side, PD, LY.PILOT_DOOR[1], 0.030, MI['src_IN_Trim'], lip=0.008, shallow=pd_shallow)
    surround(TRIM, side, CD, LY.CARGO_DOOR[1], 0.030, MI['src_IN_Trim'], lip=0.008)
    for outline, r in (LY.PILOT_DOOR, LY.CARGO_DOOR):
        pts = densify([LY.rounded_poly(LY.offset_poly(outline, -0.003), max(r - 0.003, 0.01), seg=4)], 0.06)[0]
        path = [Vector((side * (surf_x_any(y, z, LY.SKIN_T) - 0.009), y, z)) for y, z in pts]
        n_ = len(path)
        for q in range(4):                     # four open pieces (closed loops unwrap into hollow islands)
            i0, i1 = q * n_ // 4, (q + 1) * n_ // 4
            seg = [path[i % n_] for i in range(i0, i1 + 1)]
            sweep(SEAL, seg, 0.009, 0.007, 6, cap0=False, cap1=False, mat=MI['src_IN_Seal'])
mk('CP_Trims', TRIM)
mk('CP_DoorSeals', SEAL, smooth=60)

# ------------------------------------------------------------------ floor: cockpit plate, mats, seat tracks; cargo tread plate, tracks, tie-downs
FL = bmesh.new()
up = lambda p: Vector((0, 0, 1))
mapfl = lambda u, v, d: Vector((u, v, FZ + d))


def floor_poly(y0, y1, m=0.002, step=0.05):
    n = max(2, int(math.ceil((y1 - y0) / step)))
    ys = [y0 + (y1 - y0) * i / n for i in range(n + 1)]
    return [(x_floor(y) - m, y) for y in ys] + [(-(x_floor(y) - m), y) for y in reversed(ys)]


panel2d(FL, floor_poly(LY.FIREWALL_Y + 0.005, BARRIER_Y - 0.003), [], mapfl, up, depth=0.003, cham=0.003,
        mat=MI['src_IN_FloorPaint'], grid=0.12)
for v0, v1 in ((BARRIER_Y + 0.003, -0.203), (-0.197, REAR_Y - 0.003)):
    panel2d(FL, floor_poly(v0, v1), [], mapfl, up, depth=0.004, cham=0.003, mat=MI['src_IN_Tread'], grid=0.12)
# sub-floor (dark, closes the panel seams) and seam cover strips
panel2d(FL, floor_poly(LY.FIREWALL_Y + 0.004, REAR_Y - 0.001, m=0.001), [], mapfl, up, depth=0.0005, cham=0.001,
        mat=MI['src_IN_Hidden'], grid=0.3)
for ys_ in (BARRIER_Y, -0.20):
    hw_ = x_floor(ys_) - 0.03
    box(FL, (0.0, ys_, FZ + 0.0055), (2 * hw_, 0.028, 0.003), mat=MI['src_IN_Steel'], bevel=0.001, bevel_segs=1)
# floor edge strips along the kick panels (hide the floor/liner junction)
edge_prof = rr_prof(-0.030, 0.004, -0.002, 0.007, 0.003)
for side in (1, -1):
    for v0, v1 in ((PD_AFT, CD_FWD - 0.03), (CD_AFT + 0.03, REAR_Y - 0.004)):
        n = max(2, int((v1 - v0) / 0.05))
        ys = [v0 + (v1 - v0) * i / n for i in range(n + 1)]
        if side < 0:
            ys = ys[::-1]
        path = [Vector((side * (x_floor(y) - 0.002), y, FZ + 0.003)) for y in ys]
        prof_sweep(FL, path, edge_prof, MI['src_IN_Steel'])
# footwell mats (ribbed rubber) and heel plates
for sx in LY.SEATS_X:
    box(FL, (sx, -2.86, FZ + 0.006), (0.40, 0.46, 0.006), mat=MI['src_IN_Seal'], bevel=0.004, bevel_segs=1)
    for k in range(13):
        box(FL, (sx, -3.07 + k * 0.034, FZ + 0.0105), (0.36, 0.012, 0.003), mat=MI['src_IN_Seal'])
    box(FL, (sx, -2.98, FZ + 0.0115), (0.30, 0.10, 0.003), mat=MI['src_IN_Tread'], bevel=0.002, bevel_segs=1)
# seat tracks: I-section, 2 per seat, with end stops
for sx in LY.SEATS_X:
    for dx in (-0.15, 0.15):
        x = sx + dx
        y0, y1 = -2.66, -1.86
        box(FL, (x, (y0 + y1) / 2, FZ + 0.0045), (0.032, y1 - y0, 0.003), mat=MI['src_IN_Track'], bevel=0.001,
            bevel_segs=1)
        box(FL, (x, (y0 + y1) / 2, FZ + 0.012), (0.008, y1 - y0, 0.014), mat=MI['src_IN_Track'])
        box(FL, (x, (y0 + y1) / 2, FZ + 0.0205), (0.022, y1 - y0, 0.004), mat=MI['src_IN_Track'], bevel=0.0012,
            bevel_segs=1)
        for yy in (y0 + 0.01, y1 - 0.01):
            box(FL, (x, yy, FZ + 0.017), (0.026, 0.012, 0.012), mat=MI['src_IN_Steel'], bevel=0.002, bevel_segs=1)
# cargo L-tracks (slightly proud) + double-stud tie-down fittings with D-rings
TRACK_Y = {}
TIEDOWNS = []                                          # D-ring centres (Unity sockets Socket_TieDown_NN)
for tx in TRACK_X:
    y0, y1 = BARRIER_Y + 0.04, REAR_Y - 0.04
    while abs(tx) > 0 and x_floor(y1) - 0.06 < abs(tx):
        y1 -= 0.01
    TRACK_Y[tx] = (y0, y1)
    box(FL, (tx, (y0 + y1) / 2, FZ + 0.006), (0.034, y1 - y0, 0.004), mat=MI['src_IN_Track'], bevel=0.0015,
        bevel_segs=1)
    for ty in TIE_Y:
        if not (y0 + 0.04 < ty < y1 - 0.04):
            continue
        c = Vector((tx, ty, FZ + 0.008))
        TIEDOWNS.append((tx, ty, FZ + 0.008 + 0.026))
        box(FL, c + Vector((0, 0, 0.006)), (0.026, 0.056, 0.012), mat=MI['src_IN_Steel'], bevel=0.003, bevel_segs=1)
        ring = [c + Vector((0, 0.022 * math.cos(a_), 0.014 + 0.024 * math.sin(a_))) for a_ in
                [math.pi * i / 10 for i in range(11)]]
        sweep(FL, ring, 0.0045, 0.0045, 8, mat=MI['src_IN_Steel'], up_hint=Vector((1, 0, 0)))
        cylinder(FL, c + Vector((0.017, 0, 0.012)), c + Vector((-0.017, 0, 0.012)), 0.005, 0.005, 8,
                 mat=MI['src_IN_Steel'])
# door sills: tread-plate steps from the floor up to the sill, following the fuselage wall
for side in (1, -1):
    for outline, zs in ((PD, PD[0][1]), (CD, CD[0][1])):
        y0, y1 = outline[0][0] + 0.03, outline[1][0] - 0.03
        n = max(2, int((y1 - y0) / 0.05))
        ys = [y0 + (y1 - y0) * i / n for i in range(n + 1)]
        if side < 0:
            ys = ys[::-1]
        path = [Vector((side * (surf_x_any(y, zs, LY.SKIN_T) + 0.004), y, FZ)) for y in ys]
        prof_sweep(FL, path, rr_prof(-0.135, 0.0, -0.004, zs - FZ + 0.008, 0.004), MI['src_IN_Tread'])
mk('CP_Floor', FL)

# ------------------------------------------------------------------ headliner: panels on the wing box, plenum, vents, lights, grab handles
HL = bmesh.new()
down = lambda p: Vector((0, 0, -1))
XREF = 0.60


def head_X(v):
    """headliner half width: to the wall-liner junction (+6 mm overlap); over the pilot door (no wall liner)
    out to the inner skin"""
    xj = wall_frame(v, s_junction(v))[0] + 0.006
    xs = surf_x_any(v, head_z(v), LY.SKIN_T + 0.004)
    h = smooth01(PD_AFT + 0.02, PD_AFT - 0.02, v)
    return xj * (1 - h) + xs * h


def head_map(sg):
    def f(u, v, d):
        X = head_X(v)
        x = HX0 + (u - HX0) * (X - HX0) / (XREF - HX0)
        t = min(1.0, x / X)
        return Vector((sg * x, v, head_z(v) + 0.008 * (1 - t * t) - d))
    return f


seams = [WS_AFT_Y + 0.005, BARRIER_Y, CD_FWD, CD_AFT, REAR_Y]
for v0, v1 in zip(seams[:-1], seams[1:]):
    for sg in (1, -1):
        panel2d(HL, rrect(HX0, XREF, v0 + 0.002, v1 - 0.002, 0.010), [], head_map(sg), down, depth=0.006,
                cham=0.005, mat=MI['src_IN_Headliner'], grid=0.08)
# centre plenum (ventilation duct fed from the wing-root inlets); the overhead console sits on it in front
v0, v1 = LY.OVERHEAD['y1'], REAR_Y - 0.004
n = max(4, int((v1 - v0) / 0.05))
rings = []
for k in range(n + 1):
    y = v0 + (v1 - v0) * k / n
    zt = head_z(y) + 0.010
    zb_ = head_z(y) - 0.032
    rings.append([Vector(p) for p in ((HX0, y, zt), (HX0, y, zb_ + 0.012), (HX0 - 0.004, y, zb_ + 0.004),
                                      (HX0 - 0.012, y, zb_), (-HX0 + 0.012, y, zb_), (-HX0 + 0.004, y, zb_ + 0.004),
                                      (-HX0, y, zb_ + 0.012), (-HX0, y, zt))])
loft(HL, rings, False, False, False, mat=MI['src_IN_Headliner'])
# eyeball outlets over each cargo zone
for yv in (-1.05, 0.30):
    zc_ = head_z(yv) - 0.032
    revolve(HL, [(0.0, 0.0), (0.0, 0.030), (-0.004, 0.030), (-0.008, 0.024), (-0.008, 0.0)], 'Z', (0.0, yv, zc_),
            segs=16, mat=MI['src_IN_Trim'])
    revolve(HL, [(-0.008, 0.0), (-0.008, 0.019), (-0.016, 0.017), (-0.022, 0.010), (-0.024, 0.0)], 'Z',
            (0.0, yv, zc_), segs=14, mat=MI['src_IN_Steel'])
# grab handles: over the cargo doors (strip above the door) and on the headliner over the pilot doors
for side in (1, -1):
    yc_, L = -0.20, 0.30
    a0 = wall_pt(side, yc_ - L / 2, s_junction(yc_ - L / 2) - 0.05, 0.006)
    a1 = wall_pt(side, yc_ + L / 2, s_junction(yc_ + L / 2) - 0.05, 0.006)
    n0, n1 = wall_in(side, a0), wall_in(side, a1)
    path = [a0, a0 + n0 * 0.040 + Vector((0, 0.02, 0)), a1 + n1 * 0.040 - Vector((0, 0.02, 0)), a1]
    sweep(HL, spline(path, 4), 0.011, 0.011, 10, mat=MI['src_IN_Trim'], up_hint=Vector((0, 0, 1)))
    for p, n_ in ((a0, n0), (a1, n1)):
        cylinder(HL, p - n_ * 0.006, p + n_ * 0.012, 0.016, 0.014, 12, mat=MI['src_IN_Trim'])
    xh = side * 0.50
    ya, yb = -2.36, -2.10
    za, zb2 = head_z(ya) - 0.004, head_z(yb) - 0.004
    path = [Vector((xh, ya, za)), Vector((xh, ya + 0.02, za - 0.040)), Vector((xh, yb - 0.02, zb2 - 0.040)),
            Vector((xh, yb, zb2))]
    sweep(HL, spline(path, 4), 0.011, 0.011, 10, mat=MI['src_IN_Trim'], up_hint=Vector((1, 0, 0)))
    for p in path[0], path[-1]:
        cylinder(HL, p + Vector((0, 0, 0.008)), p - Vector((0, 0, 0.012)), 0.016, 0.014, 12, mat=MI['src_IN_Trim'])
# headliner-to-wall cove strips (wherever a wall liner meets the headliner)
for side in (1, -1):
    n = int((REAR_Y - PD_AFT) / 0.05)
    path = [wall_pt(side, y, s_junction(y) - 0.004, 0.010) for y in
            [PD_AFT + (REAR_Y - PD_AFT) * i / n for i in range(n + 1)]]
    sweep(HL, path, 0.012, 0.009, 8, mat=MI['src_IN_Trim'], up_hint=Vector((0, 0, 1)))
mk('CP_Headliner', HL, smooth=40)

# cargo courtesy lights in the plenum (lens split to Lens_CargoLight by material in the Unity export)
bm = bmesh.new()
for yl in (-0.55, 0.75):
    zc_ = head_z(yl) - 0.032
    rbox(bm, (0.0, yl, zc_ - 0.004), (0.15, 0.07, 0.008), MI['src_IN_Trim'], bevel=0.004, segs=1)
    rbox(bm, (0.0, yl, zc_ - 0.010), (0.12, 0.05, 0.006), MI['M_Light_Cabin'], bevel=0.003, segs=1)
mk('CP_CargoLight', bm)

# ------------------------------------------------------------------ windshield frame: aft header (either side of the compass), centre post cover
WF = bmesh.new()
for sg in (1, -1):
    xs_ = [sg * (0.05 + (WS_X - 0.035 - 0.05) * i / 14) for i in range(15)]
    path = [Vector((x, WS_AFT_Y + 0.004, surf_z_top(WS_AFT_Y, x, LY.SKIN_T) + 0.002)) for x in xs_]
    prof_sweep(WF, path, rr_prof(-0.017, 0.017, -0.036, 0.0, 0.007), MI['src_IN_Trim'])
ys_ = [-2.705 - 0.535 * i / 14 for i in range(15)]
path = [Vector((0.0, y, surf_z_top(y, 0.0, LY.SKIN_T) + 0.002)) for y in ys_]
prof_sweep(WF, path, rr_prof(-0.036, 0.036, -0.016, 0.0, 0.006), MI['src_IN_Trim'])
mk('CP_WindshieldFrame', WF)

# ------------------------------------------------------------------ bulkheads: firewall blanket (footwell), rear bulkhead liner
BK = bmesh.new()
yfw = LY.FIREWALL_Y + 0.012
for j in range(4):
    z0, z1 = FZ + 0.01 + j * 0.10, FZ + 0.01 + (j + 1) * 0.10
    xw = surf_x_any(yfw, z0, LIN + 0.012)
    w = 2 * xw / 10
    for i in range(10):
        rbox(BK, (-xw + (i + 0.5) * w, yfw, (z0 + z1) / 2), (w - 0.002, 0.016, 0.098), MI['src_IN_Insul'],
             bevel=0.006, segs=1)
# firewall closeout behind the blanket / panel: full lining section, dark
yfp = LY.FIREWALL_Y + 0.004
X_, Z_, S_ = _curve(_section(yfp))
half = [(x, z) for x, z in zip(X_, Z_)][::12] + [(0.0, Z_[-1])]
O = dedupe([(x, z) for x, z in half] + [(-x, z) for x, z in reversed(half)])
O = [O[i] for i in mgeo.convex_hull_2d(O)]
panel2d(BK, O, [], lambda u, v, d: Vector((u, yfp + d, v)), lambda p: Vector((0, 1, 0)), depth=0.002, cham=0.002,
        mat=MI['src_IN_Kick'], grid=0.15)
# rear bulkhead liner: lining section at REAR_Y up into the headliner, chamfered, with an access panel
X_, Z_, S_ = _curve(_section(REAR_Y))
ztop = head_z(REAR_Y) + 0.004
half = [(x, z) for x, z in zip(X_, Z_) if z <= ztop]
half = half[::max(1, len(half) // 40)] + [(max(0.0, surf_x_any(REAR_Y, ztop, LIN)), ztop)]
O = [(x, z) for x, z in half] + [(-x, z) for x, z in reversed(half)]
O = dedupe(O)
O = [O[i] for i in mgeo.convex_hull_2d(O)]
mapr = lambda u, v, d: Vector((u, REAR_Y - d, v))
panel2d(BK, O, [], mapr, lambda p: Vector((0, -1, 0)), depth=0.008, cham=0.006, mat=MI['src_IN_Liner'], grid=0.12)
panel2d(BK, rrect(-0.30, 0.30, 1.40, 2.05, 0.02), [], lambda u, v, d: Vector((u, REAR_Y - 0.008 - d, v)),
        lambda p: Vector((0, -1, 0)), depth=0.004, cham=0.003, mat=MI['src_IN_Liner'], grid=0.1)
for u in (-0.28, 0.28):
    for v in (1.42, 1.725, 2.03):
        cylinder(BK, Vector((u, REAR_Y - 0.011, v)), Vector((u, REAR_Y - 0.015, v)), 0.0065, 0.005, 10,
                 mat=MI['src_IN_Steel'])
mk('CP_Bulkheads', BK)

# ------------------------------------------------------------------ cargo barrier: two composite posts + three webbing nets
BR = bmesh.new()
NETS = bmesh.new()
uvn = NETS.loops.layers.uv.new('UVMap')
POST_X = (0.25, -0.25)
zt_ = head_z(BARRIER_Y) + 0.004
for px in POST_X:
    rbox(BR, (px, BARRIER_Y, (FZ + zt_) / 2), (0.055, 0.045, zt_ - FZ), MI['src_IN_Composite'], bevel=0.008, segs=2)
    rbox(BR, (px, BARRIER_Y, FZ + 0.03), (0.09, 0.08, 0.06), MI['src_IN_Steel'], bevel=0.006, segs=1)       # floor fitting
    rbox(BR, (px, BARRIER_Y, zt_ - 0.030), (0.08, 0.07, 0.05), MI['src_IN_Steel'], bevel=0.006, segs=1)    # roof fitting
mk('CP_Barrier', BR)


def strap(bm, a, b, w, t, normal, mat, u0=0.0):
    """flat webbing strap from a to b, width w across, thickness t along `normal`; UV u in metres"""
    d = (b - a)
    dn = d.normalized()
    side = dn.cross(normal).normalized() * (w / 2)
    nn = normal.normalized() * (t / 2)
    cs = [a - side - nn, a + side - nn, a + side + nn, a - side + nn]
    ce = [b - side - nn, b + side - nn, b + side + nn, b - side + nn]
    va = [bm.verts.new(p) for p in cs]
    vb = [bm.verts.new(p) for p in ce]
    uvl = bm.loops.layers.uv.active
    mid = (a + b) / 2
    su, nu = side.normalized(), nn.normalized()
    for i in range(4):
        j = (i + 1) % 4
        f = bm.faces.new((va[i], va[j], vb[j], vb[i]))
        f.material_index = mat
        off = f.calc_center_median() - mid
        off -= dn * off.dot(dn)
        f.normal_update()
        if f.normal.dot(off) < 0:
            f.normal_flip()
        wide = i % 2 == 0                      # faces at -nn / +nn span the strap width
        for lp in f.loops:
            q = lp.vert.co - a
            lp[uvl].uv = (u0 + q.dot(dn), (0.5 + q.dot(su) / w) if wide else (0.075 + 0.075 * q.dot(nu) / (t / 2)))


def net(bm, xa, xb, z0, z1, y, cell=0.13):
    """webbing net between the edge curves x = xa(z) .. xb(z), z0..z1, in the plane y"""
    nrm = Vector((0, 1, 0))
    W = MI['src_IN_Webbing']
    nz = max(2, round((z1 - z0) / cell))
    zs = [z0 + (z1 - z0) * k / nz for k in range(nz + 1)]
    nx = max(2, round(max(abs(xb(z) - xa(z)) for z in zs) / cell))
    P = lambda f, z, dy=0.0: Vector((xa(z) + (xb(z) - xa(z)) * f, y + dy, z))
    strap(bm, P(0, z0), P(1, z0), 0.038, 0.005, nrm, W)
    strap(bm, P(0, z1), P(1, z1), 0.038, 0.005, nrm, W)
    for f in (0.0, 1.0):
        for k in range(nz):
            strap(bm, P(f, zs[k]), P(f, zs[k + 1]), 0.038, 0.005, nrm, W, u0=zs[k] - z0)
    for i in range(1, nx):
        for k in range(nz):
            strap(bm, P(i / nx, zs[k], 0.004), P(i / nx, zs[k + 1], 0.004), 0.025, 0.003, nrm, W, u0=zs[k] - z0)
    for k in range(1, nz):
        strap(bm, P(0, zs[k], -0.004), P(1, zs[k], -0.004), 0.025, 0.003, nrm, W)


zn0, zn1 = FZ + 0.06, head_z(BARRIER_Y) - 0.05
yn = BARRIER_Y + 0.03
net(NETS, lambda z: POST_X[0] - 0.035, lambda z: POST_X[1] + 0.035, zn0, zn1, yn)
wall_x = lambda z: surf_x_any(BARRIER_Y, z, LIN) - 0.02
for side in (1, -1):
    net(NETS, lambda z, side=side: side * (abs(POST_X[0]) + 0.035), lambda z, side=side: side * wall_x(z),
        zn0, zn1, yn)
NETS.normal_update()
ob_nets = obj_from_bm('CP_BarrierNets', NETS, CP, MATS)
shade(ob_nets, 30)
STATIC.append(ob_nets.name)
# quick-release fittings where the nets attach (posts and sidewalls)
bm = bmesh.new()
for x in (POST_X[0] - 0.035, POST_X[1] + 0.035):
    for z in (zn0, 1.55, zn1):
        cylinder(bm, Vector((x, BARRIER_Y + 0.02, z)), Vector((x, BARRIER_Y + 0.05, z)), 0.012, 0.010, 10,
                 mat=MI['src_IN_Steel'])
for side in (1, -1):
    for z in (zn0, 1.55, zn1):
        xw = wall_x(z)
        cylinder(bm, Vector((side * xw, yn, z)), Vector((side * (xw + 0.026), yn, z)), 0.012, 0.012, 10,
                 mat=MI['src_IN_Steel'])
mk('CP_BarrierFittings', bm)

# ================================================================== v5 COCKPIT EQUIPMENT (Caravan-style)
# panel structure (frame, sub-panels, lower closeout, yoke boots), glareshield, pedestal (quadrant, elevator trim
# wheel, flap selector, rudder trim, fuel shutoff), yokes, rudder pedals, crew seats with 5-point harness,
# sun visors, headsets, extinguisher, door trims merged into the door objects.
# Moving parts keep their v4 names and pivots (Unity rig contract).
from mathutils.bvhtree import BVHTree

PY = LY.PANEL_Y
PHW = 0.655                                   # panel frame half width (door trim faces sit at |x| ~ 0.665)


def merge_into(target, bm, smooth=40):
    """append world-space bmesh geometry (material indices into MATS) to an existing object (door)"""
    ob = bpy.data.objects[target]
    me = ob.data
    names = [m.name for m in me.materials]
    fix_normals_keep_uv(bm)
    remap = {}
    for mi in sorted({f.material_index for f in bm.faces}):
        nm = MATS[mi].name
        if nm not in names:
            me.materials.append(MATS[mi])
            names.append(nm)
        remap[mi] = names.index(nm)
    for f in bm.faces:
        f.material_index = remap[f.material_index]
    bmesh.ops.transform(bm, matrix=ob.matrix_world.inverted(), verts=bm.verts)
    tmp = bpy.data.meshes.new('tmp_merge')
    bm.to_mesh(tmp)
    bm.free()
    bmo = bmesh.new()
    bmo.from_mesh(me)
    bmo.from_mesh(tmp)
    bmo.to_mesh(me)
    bmo.free()
    bpy.data.meshes.remove(tmp)
    shade(ob, smooth)


def skin_pt(side, y, z, d):
    """point on the fuselage inner skin at (y, z), offset d along the inward normal"""
    zb, zt, hw, ne = station_at(y)
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    a, b = hw - LY.SKIN_T, hh - LY.SKIN_T
    x = surf_x_any(y, z, LY.SKIN_T)
    gx = (x / a) ** (ne - 1) / a
    gz = (abs(z - zc) / b) ** (ne - 1) / b * (1.0 if z >= zc else -1.0)
    L = math.hypot(gx, gz)
    return Vector((side * (x - gx / L * d), y, z - gz / L * d))


def flat_strap(bm, pts, ups, w, t, mat):
    """webbing strap along pts, flat side facing ups[k] (per point); hexagonal flat section"""
    rings = []
    N = len(pts)
    for k in range(N):
        p = Vector(pts[k])
        tng = (Vector(pts[min(k + 1, N - 1)]) - Vector(pts[max(k - 1, 0)])).normalized()
        u = Vector(ups[k])
        u = (u - tng * u.dot(tng)).normalized()
        s = tng.cross(u).normalized()
        hw_, ht = w / 2, t / 2
        rings.append([p + s * hw_, p + s * hw_ * 0.86 + u * ht, p - s * hw_ * 0.86 + u * ht, p - s * hw_,
                      p - s * hw_ * 0.86 - u * ht, p + s * hw_ * 0.86 - u * ht])
    loft(bm, rings, True, True, True, mat)


def tilt_m(hinge, deg):
    return Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(deg), 4, 'X') @ Matrix.Translation(-hinge)


# v5 placards drawn into the free gauge-atlas cell 20 (gauges_tex.P20, cell pixels)
P20 = {'QUAD': (0, 0, 512, 48), 'FLAP': (0, 52, 384, 308), 'TRIM': (388, 52, 508, 92), 'FUEL': (0, 312, 256, 376),
       'DOOR': (256, 312, 512, 376), 'EXT': (0, 380, 256, 428), 'CDOOR': (256, 380, 512, 428),
       'FLOOR': (0, 432, 512, 508)}


def p20_quad(bm, key, c, r, u, w, h):
    """placard quad: centre c, r = reader's right, u = up (unit vectors), size w x h; faces r x u"""
    uvl = bm.loops.layers.uv.verify()
    pl = plate_layer(bm)
    x0, y0, x1, y1 = P20[key]
    U0, U1 = (2048 + x0 + 1) / 4096, (2048 + x1 - 1) / 4096
    V1, V0 = 1 - (1024 + y0 + 1) / 2048, 1 - (1024 + y1 - 1) / 2048
    c, r, u = Vector(c), Vector(r), Vector(u)
    vs = [bm.verts.new(p) for p in (c - r * w / 2 - u * h / 2, c + r * w / 2 - u * h / 2, c + r * w / 2 + u * h / 2,
                                    c - r * w / 2 + u * h / 2)]
    f = bm.faces.new(vs)
    f.material_index = MI['src_CP_Gauges']
    f[pl] = 2
    for lp, uv in zip(f.loops, ((U0, V0), (U1, V0), (U1, V1), (U0, V1))):
        lp[uvl].uv = uv
    f.normal_update()
    if f.normal.dot(r.cross(u)) < 0:
        f.normal_flip()


# ------------------------------------------------------------------ instrument panel: frame, sub-panels, lower closeout, yoke boots
bm = bmesh.new()
fwd_in = lambda p: Vector((0, 1, 0))
panel2d(bm, rrect(-PHW, PHW, LY.PANEL_Z[0], LY.PANEL_Z[1] + 0.006, 0.02), [],
        lambda u, v, d: Vector((u, PY - 0.025 + d, v)), fwd_in, depth=0.022, cham=0.010, mat=MI['src_CP_Panel'],
        grid=0.08, back=True, back_mat=MI['src_IN_Hidden'])
for sx0, sx1, sz0, sz1 in SUBPANELS:
    panel2d(bm, rrect(min(sx0, sx1), max(sx0, sx1), sz0, sz1, 0.008), [],
            lambda u, v, d: Vector((u, PY - 0.003 + d, v)), fwd_in, depth=0.003, cham=0.0015, mat=MI['src_CP_Panel'],
            grid=0.06)
# lower closeout under the panel (knee area ceiling) and the panel-to-pedestal fairing
rbox(bm, (0.0, PY - 0.12, LY.PANEL_Z[0] - 0.008), (2 * PHW - 0.02, 0.19, 0.014), MI['src_CP_Panel'], bevel=0.004,
     segs=1)
mk('CP_PanelFrame', bm)
for side, yx in (('P', LY.YOKE_X[0]), ('C', LY.YOKE_X[1])):
    bm = bmesh.new()                                   # rubber boot + escutcheon around the column hole
    prof = [(PY - 0.001, 0.0)] + [(PY + k * 0.006, 0.030 - k * 0.0011 + (0.004 if k % 2 else 0.0)) for k in range(9)]
    prof += [(PY + 0.050, 0.0)]
    revolve(bm, prof, 'Y', (yx, 0, LY.YOKE_Z), segs=24, mat=MI['src_CP_Rubber'])
    revolve(bm, [(PY - 0.0005, 0.0335), (PY + 0.0025, 0.0335), (PY + 0.0035, 0.031), (PY + 0.0035, 0.029),
                 (PY - 0.0005, 0.029)], 'Y', (yx, 0, LY.YOKE_Z), segs=24, mat=MI['src_CP_Chrome'])
    mk(f'CP_YokeBoot_{side}', bm)

# ------------------------------------------------------------------ glareshield: top under the windshield, padded lip, defrost vents
G_HW = 0.645
y_r = lambda x: -2.958 - 0.022 * (x / G_HW) ** 2
Y_F = -3.245
g_side = lambda y: min(G_HW, surf_x_any(y, 2.06, LY.SKIN_T + 0.008))
g_top = lambda x, y: min(2.082, surf_z_top(y, x, 0.0) - 0.021)
GL = bmesh.new()
O = [(-G_HW + 2 * G_HW * i / 24, y_r(-G_HW + 2 * G_HW * i / 24)) for i in range(25)]
O += [(g_side(y), y) for y in [y_r(G_HW) + (Y_F - y_r(G_HW)) * k / 10 for k in range(1, 11)]]
O += [(g_side(Y_F) * (1 - 2 * k / 10), Y_F) for k in range(1, 10)]
O += [(-g_side(y), y) for y in [Y_F + (y_r(G_HW) - Y_F) * k / 10 for k in range(0, 10)]]
panel2d(GL, O, [], lambda u, v, d: Vector((u, v, g_top(u, v) - 0.002 + d)), lambda p: Vector((0, 0, 1)), depth=0.002,
        cham=0.002, mat=MI['src_CP_Glare'], grid=0.06)
lip = [(0.030, 0.024), (0.0, 0.027), (-0.012, 0.023), (-0.019, 0.013), (-0.0215, 0.0), (-0.019, -0.013),
       (-0.012, -0.023), (0.0, -0.028), (0.030, -0.028)]
prof_sweep(GL, [Vector((x, y_r(x), 2.057)) for x in [-G_HW + 2 * G_HW * i / 32 for i in range(33)]], lip,
           MI['src_CP_Glare'])
fr = [Vector((x, Y_F, g_top(x, Y_F) - 0.002)) for x in [-g_side(Y_F) + 2 * g_side(Y_F) * i / 12 for i in range(13)]]
loft(GL, [fr, [p - Vector((0, 0, p.z - 2.030)) for p in fr]], False, False, False, mat=MI['src_CP_Glare'])
for sg in (1, -1):                                    # defroster outlets at the windshield base
    rbox(GL, (sg * 0.30, Y_F + 0.035, g_top(sg * 0.30, Y_F + 0.035) + 0.001), (0.22, 0.026, 0.004), MI['src_CP_Black'],
         bevel=0.0015, segs=1)
    for k in range(7):
        box(GL, (sg * 0.30 - 0.09 + k * 0.03, Y_F + 0.035, g_top(sg * 0.30, Y_F + 0.035) + 0.003),
            (0.004, 0.022, 0.002), mat=MI['src_CP_Metal'])
rbox(GL, (0.0, -2.968, 2.026), (0.56, 0.014, 0.008), MI['src_CP_Black'], bevel=0.003, segs=1)   # flood light rail
mk('CP_Glareshield', GL, smooth=50)

# ------------------------------------------------------------------ pedestal: chamfered body, quadrant with slots, trim wheel, flap selector
P = LY.PEDESTAL
py0, py1, phw = P['y0'], P['y1'], P['hw']
py, pz = LY.LEVER_PIVOT
bm = bmesh.new()
prof = [(py0, FZ), (py1 + 0.03, FZ), (py1, FZ + 0.03), (py1, P['z_top_back'] - 0.03), (py1 - 0.03, P['z_top_back']),
        (py0 + 0.04, P['z_top_front']), (py0, P['z_top_front'])]
inner = offs(prof, -0.006)
rings = [[Vector((x, y, z)) for y, z in (inner if k in (0, 3) else prof)]
         for k, x in enumerate((-phw, -phw + 0.006, phw - 0.006, phw))]
loft(bm, rings, True, True, True, mat=MI['src_CP_Panel'])
RQ = 0.075
qa = [math.radians(a) for a in range(-60, 61, 10)]
for xa, xb in ((-0.068, -0.046), (-0.034, -0.006), (0.006, 0.034), (0.046, 0.068)):
    sec = [(py + RQ * math.sin(a), pz - 0.045 + RQ * math.cos(a)) for a in qa]
    sec += [(py + RQ * math.sin(qa[-1]), pz - 0.075), (py + RQ * math.sin(qa[0]), pz - 0.075)]
    sec_i = offs(sec, -0.0015)
    loft(bm, [[Vector((x, y, z)) for y, z in (sec_i if k in (0, 3) else sec)]
              for k, x in enumerate((xa, xa + 0.0015, xb - 0.0015, xb))], True, True, True, mat=MI['src_CP_Black'])
for _, lx, _ in LY.LEVERS:                              # rubber slot seals
    for k in range(11):
        a = math.radians(-50 + k * 10)
        box(bm, (lx, py + (RQ - 0.002) * math.sin(a), pz - 0.045 + (RQ - 0.002) * math.cos(a)), (0.011, 0.012, 0.002),
            mat=MI['src_CP_Rubber'])
# friction lock (right side, near the quadrant)
revolve(bm, [(0.0, 0.0), (0.0, 0.013), (-0.004, 0.014), (-0.016, 0.013), (-0.019, 0.009), (-0.020, 0.0)], 'X',
        (-phw, -2.80, 1.33), segs=18, mat=MI['src_CP_Black'],
        radial_fn=lambda i, j, r: r * (0.93 if (i % 2 and j in (2, 3)) else 1.0))
# elevator trim wheel: axle boss + position indicator on the left side
tb, tx, ty, tz, tr = LY.TRIM_WHEEL
cylinder(bm, (phw - 0.002, ty, tz), (tx + 0.010, ty, tz), 0.012, 0.012, 14, mat=MI['src_CP_Metal'])
rbox(bm, (phw + 0.001, ty, tz + tr + 0.022), (0.003, 0.060, 0.022), MI['src_CP_Black'], bevel=0.002, segs=1)
rbox(bm, (phw + 0.0028, ty, tz + tr + 0.022), (0.0008, 0.052, 0.003), MI['src_CP_Needle'])
# flap selector housing (right side): body, lever slot, detent plate
rbox(bm, (-phw - 0.009, -2.66, 1.29), (0.018, 0.18, 0.14), MI['src_CP_Panel'], bevel=0.004, segs=1)
rbox(bm, (-phw - 0.009, -2.66, 1.3605), (0.0065, 0.13, 0.002), MI['src_CP_Rubber'])
rbox(bm, (-phw - 0.0185, -2.66, 1.30), (0.0012, 0.15, 0.10), MI['src_CP_Black'], bevel=0.0006, segs=1)
# rudder trim wheel + aileron trim knob on the aft face, under the fuel shutoff
revolve(bm, [(0.0, 0.0), (0.0, 0.030), (0.004, 0.032), (0.014, 0.032), (0.018, 0.030), (0.018, 0.0)], 'Y',
        (0.0, py1, 1.16), segs=32, mat=MI['src_CP_Black'],
        radial_fn=lambda i, j, r: r + (0.0018 if (i % 2 == 0 and j in (2, 3)) else 0.0))
rbox(bm, (0.0, py1 + 0.0195, 1.16 + 0.022), (0.003, 0.002, 0.012), MI['src_CP_Needle'])
revolve(bm, [(0.0, 0.0), (0.0, 0.014), (0.012, 0.013), (0.016, 0.009), (0.017, 0.0)], 'Y', (0.045, py1, 1.10),
        segs=14, mat=MI['src_CP_Black'])
# placards (texture slots later): power quadrant, fuel shutoff, trim
rbox(bm, (0.0, py1 + 0.001, 1.27 + 0.036), (0.07, 0.002, 0.016), MI['src_CP_Black'], bevel=0.001, segs=1)
# fire extinguisher in a floor bracket between the seats
revolve(bm, [(-2.44, 0.0), (-2.44, 0.036), (-2.43, 0.040), (-2.18, 0.040), (-2.16, 0.031), (-2.14, 0.018),
             (-2.125, 0.0)], 'Y', (0.0, 0, FZ + 0.058), segs=20, mat=MI['src_CP_KnobRed'])
rbox(bm, (0.0, -2.112, FZ + 0.09), (0.016, 0.05, 0.022), MI['src_CP_Black'], bevel=0.003, segs=1)      # head + lever
cylinder(bm, (0.0, -2.115, FZ + 0.072), (0.0, -2.08, FZ + 0.050), 0.006, 0.005, 8, mat=MI['src_CP_Black'])
for yb in (-2.40, -2.22):
    rbox(bm, (0.0, yb, FZ + 0.012), (0.095, 0.035, 0.020), MI['src_CP_Metal'], bevel=0.003, segs=1)
    flat_strap(bm, [Vector((0.044 * math.cos(a), yb, FZ + 0.058 + 0.044 * math.sin(a))) for a in
                    [math.radians(-10 + k * 20) for k in range(11)]],
               [Vector((math.cos(math.radians(-10 + k * 20)), 0, math.sin(math.radians(-10 + k * 20))))
                for k in range(11)], 0.022, 0.003, MI['src_CP_Metal'])
mk('CP_Pedestal', bm)
# power / prop / condition levers (pivots unchanged)
KNOB = {'black': 'src_CP_Black', 'blue': 'src_CP_KnobBlue', 'red': 'src_CP_KnobRed'}
for bone, lx, kc in LY.LEVERS:
    piv = Vector((lx, py, pz))
    tip = piv + Vector((0, -0.05, 0.13))
    bm = bmesh.new()
    rbox(bm, piv.lerp(tip, 0.5), (0.006, 0.012, 0.14), MI['src_CP_Metal'], bevel=0.002)
    xform_bm(bm, tilt_m(piv.lerp(tip, 0.5), 21))
    if kc == 'black':                                   # power lever: wide T handle
        rbox(bm, tip + Vector((0, 0, 0.012)), (0.066, 0.026, 0.026), MI[KNOB[kc]], bevel=0.010, segs=3)
        rbox(bm, tip + Vector((0, 0.0, 0.0255)), (0.040, 0.016, 0.002), MI['src_CP_Metal'], bevel=0.0008, segs=1)
    elif kc == 'blue':                                  # propeller: knurled knob
        knurled(bm, tip.x, tip.z + 0.015, tip.y - 0.012, 0.014, 0.024, MI[KNOB[kc]])
    else:                                               # fuel condition: red paddle
        rbox(bm, tip + Vector((0, 0, 0.014)), (0.024, 0.034, 0.032), MI[KNOB[kc]], bevel=0.008, segs=2)
    mk(bone, bm, tuple(piv), axis='lateral', note='rest = mid travel')
fb, fx, fyy, fz = LY.FLAP_LEVER
bm = bmesh.new()
piv = Vector((fx, fyy, fz))
tip = piv + Vector((-0.02, -0.02, 0.09))
cylinder(bm, piv, tip, 0.005, 0.0045, 10, mat=MI['src_CP_Metal'])
airf = airfoil_ring(0, 1, 9, 0, 0, 0.25, True)[:-1]
rings = []
for dz in (-0.007, -0.005, 0.005, 0.007):
    sc_ = 1.0 if abs(dz) < 0.006 else 0.85
    rings.append([tip + Vector((yc * 0.042 * sc_, -0.021 + xc * 0.042, 0.012 + dz)) for xc, yc in airf])
loft(bm, rings, True, True, True, mat=MI['src_CP_Needle'])
mk(fb, bm, tuple(piv), axis='lateral', note='flap detents')
bm = bmesh.new()
prof = [(tx - 0.009, 0.0), (tx - 0.009, tr - 0.004), (tx - 0.006, tr), (tx + 0.006, tr), (tx + 0.009, tr - 0.004),
        (tx + 0.009, 0.0)]
revolve(bm, prof, 'X', (0, ty, tz), segs=48, mat=MI['src_CP_Black'],
        radial_fn=lambda i, j, r: r + (0.003 if (i % 2 == 0 and j in (2, 3)) else 0.0))
box(bm, (tx + 0.0095, ty, tz + tr - 0.012), (0.002, 0.012, 0.012), mat=MI['src_CP_Needle'])
mk(tb, bm, (tx, ty, tz), axis='lateral', note='trim')
bn = LY.FUEL_SHUTOFF[0]
bm = bmesh.new()
fs = Vector((0.0, py1, 1.27))
cylinder(bm, fs + Vector((0, -0.01, 0)), fs + Vector((0, 0.018, 0)), 0.004, 0.004, 8, mat=MI['src_CP_Chrome'])
rbox(bm, fs + Vector((0, 0.025, 0)), (0.045, 0.014, 0.018), MI['src_CP_KnobRed'], bevel=0.006, segs=2)
mk(bn, bm, tuple(fs), axis='translate_aft', note='pull aft (towards the pilot) = fuel off')

# ------------------------------------------------------------------ yokes: column, collar, moulded hub, ram's horns with grips and switches
for side, yx in (('P', LY.YOKE_X[0]), ('C', LY.YOKE_X[1])):
    hub = Vector((yx, LY.YOKE_HUB_Y, LY.YOKE_Z))
    bm = bmesh.new()
    cylinder(bm, (yx, PY - 0.16, hub.z), (yx, hub.y - 0.030, hub.z), 0.0155, 0.0155, 18, mat=MI['src_CP_Chrome'])
    revolve(bm, [(hub.y - 0.052, 0.0), (hub.y - 0.052, 0.017), (hub.y - 0.046, 0.0205), (hub.y - 0.024, 0.0205),
                 (hub.y - 0.020, 0.018), (hub.y - 0.020, 0.0)], 'Y', (yx, 0, hub.z), segs=18, mat=MI['src_CP_Black'])
    mk(f'Yoke_{side}', bm, tuple(hub), axis='translate_fwd', note='pitch: push = forward, travel +-0.08 m')
    bm = bmesh.new()
    hb = bmesh.new()
    rbox(hb, hub + Vector((0, 0.004, 0.0)), (0.112, 0.036, 0.058), MI['src_CP_Black'], bevel=0.016, segs=3)
    hb = subsurf_bm(hb)
    join_bm(bm, hb)
    rbox(bm, hub + Vector((0, 0.0235, 0.002)), (0.064, 0.003, 0.030), MI['src_CP_Chrome'], bevel=0.003, segs=2)
    rbox(bm, hub + Vector((0, 0.0255, 0.002)), (0.050, 0.0012, 0.018), MI['src_CP_Black'], bevel=0.001, segs=1)
    for sg in (1, -1):
        pts = [hub + Vector((sg * 0.040, 0.006, -0.004)), hub + Vector((sg * 0.085, 0.012, -0.021)),
               hub + Vector((sg * 0.128, 0.017, -0.015)), hub + Vector((sg * 0.150, 0.020, 0.012)),
               hub + Vector((sg * 0.158, 0.021, 0.050)), hub + Vector((sg * 0.155, 0.019, 0.090)),
               hub + Vector((sg * 0.143, 0.015, 0.119)), hub + Vector((sg * 0.130, 0.011, 0.130))]
        dense = spline(pts, 5)
        N = len(dense)

        def rad(u):
            base = 0.0125 + 0.0045 * smooth01(0.30, 0.42, u) - 0.0045 * smooth01(0.90, 1.0, u)
            grip = 0.06 * max(0.0, math.sin((u - 0.45) * 2 * math.pi * 7)) if 0.45 < u < 0.88 else 0.0
            return base * (1.0 + grip)
        sweep(bm, dense, rad, lambda u: rad(u) * 0.90, 14, mat=MI['src_CP_Black'], up_hint=Vector((0, 1, 0)))
        top = pts[-2]
        if sg == 1:                                     # pilot-left horn: trim rocker, PTT, AP disconnect
            rbox(bm, top + Vector((0, 0.004, 0.016)), (0.010, 0.018, 0.008), MI['src_CP_Metal'], bevel=0.002)
            cylinder(bm, pts[-3] + Vector((-0.013, 0.0, 0.0)), pts[-3] + Vector((-0.020, 0.0, 0.0)), 0.0055, 0.005,
                     10, mat=MI['src_CP_KnobRed'])
            cylinder(bm, pts[-4] + Vector((0.0, -0.014, 0.0)), pts[-4] + Vector((0.0, -0.021, 0.0)), 0.005, 0.0045,
                     10, mat=MI['src_CP_KnobRed'])
        else:
            cylinder(bm, pts[-3] + Vector((0.013, 0.0, 0.0)), pts[-3] + Vector((0.020, 0.0, 0.0)), 0.0055, 0.005, 10,
                     mat=MI['src_CP_Metal'])
    mk(f'Yoke_{side}_Roll', bm, tuple(hub), parent=f'Yoke_{side}', axis='fwd', note='roll +-50 deg')

# ------------------------------------------------------------------ rudder pedals: torque tubes, bearing blocks, brake cylinders; pedals with toe-brake pads
hy, hz = LY.PEDAL_HINGE
bm = bmesh.new()
for sx in LY.SEATS_X:
    cylinder(bm, (sx + 0.17, hy, hz), (sx - 0.17, hy, hz), 0.012, 0.012, 12, mat=MI['src_CP_Metal'])
    for dx in (0.17, -0.17, 0.0):
        rbox(bm, (sx + dx, hy, (hz + FZ) / 2 + 0.004), (0.022, 0.034, hz - FZ + 0.026), MI['src_CP_Metal'], bevel=0.004)
    for dx in (LY.PEDAL_DX, -LY.PEDAL_DX):
        a = Vector((sx + dx + 0.022 * (1 if dx > 0 else -1), hy - 0.01, hz + 0.15))
        b = Vector((a.x, LY.FIREWALL_Y + 0.03, hz + 0.20))
        cylinder(bm, a, a.lerp(b, 0.5), 0.005, 0.005, 8, mat=MI['src_CP_Chrome'])
        cylinder(bm, a.lerp(b, 0.45), b, 0.013, 0.013, 12, mat=MI['src_CP_Metal'])
        rbox(bm, b + Vector((0, 0.004, 0)), (0.03, 0.012, 0.03), MI['src_CP_Metal'], bevel=0.003, segs=1)
mk('CP_PedalLinkage', bm)
for side, sx in (('P', LY.SEATS_X[0]), ('C', LY.SEATS_X[1])):
    for lr, dx in (('L', LY.PEDAL_DX), ('R', -LY.PEDAL_DX)):
        px = sx + dx
        bm = bmesh.new()
        box_rx(bm, (px, hy + 0.030, hz + 0.10), (0.016, 0.012, 0.21), -17.0, MI['src_CP_Metal'], bevel=0.003)
        box_rx(bm, (px, hy + 0.068, hz + 0.207), (0.088, 0.010, 0.168), -17.0, MI['src_CP_Metal'], bevel=0.004, segs=2)
        box_rx(bm, (px, hy + 0.0745, hz + 0.207), (0.080, 0.006, 0.158), -17.0, MI['src_CP_Rubber'], bevel=0.003, segs=2)
        for k in range(6):
            box_rx(bm, (px, hy + 0.0785 + 0.0 * k, hz + 0.148 + k * 0.024), (0.068, 0.004, 0.006), -17.0,
                   MI['src_CP_Rubber'], bevel=0.0012, segs=1)
        cylinder(bm, Vector((px - 0.03, hy, hz)), Vector((px + 0.03, hy, hz)), 0.015, 0.015, 14, mat=MI['src_CP_Black'])
        mk(f'Pedal{side}_{lr}', bm, (px, hy, hz), axis='lateral', note='rudder +-12 deg')

# ------------------------------------------------------------------ crew seats: frame on the tracks, sculpted cushions, back shell, headrest,
# armrest, adjust handles, inertia-reel 5-point harness (Belt_<tag>_On / _Off switchable)
SEAT_Y = -2.25
for tag, sx in (('P', LY.SEATS_X[0]), ('C', LY.SEATS_X[1])):
    sy = SEAT_Y
    inb = -1 if sx > 0 else 1
    hinge = Vector((sx, sy + 0.215, 1.425))
    TB = tilt_m(hinge, -12)
    cu = bmesh.new()                                     # seat cushion (front -> back), soft
    rings = []
    for dy, sc_w, sc_h in ((-0.235, 0.86, 0.50), (-0.228, 0.95, 0.82), (-0.205, 1.0, 1.0), (-0.10, 1.0, 1.0),
                           (0.0, 1.0, 0.97), (0.12, 1.0, 0.92), (0.18, 0.98, 0.80), (0.20, 0.95, 0.62)):
        zt = 1.335 + 0.085 * sc_h
        rings.append([Vector((sx + x, sy + dy, z)) for x, z in cushion_ring(0.23 * sc_w, 1.335, zt, 0.035 * sc_h)])
    loft(cu, rings, True, True, True, mat=MI['src_ST_Leather'])
    cu = subsurf_bm(cu)
    bk = bmesh.new()                                     # backrest (bottom -> top) with side bolsters
    rings = []
    for dz, sc_w, bol in ((0.0, 0.94, 0.03), (0.02, 1.0, 0.04), (0.18, 1.0, 0.046), (0.36, 1.0, 0.046),
                          (0.50, 0.97, 0.04), (0.57, 0.92, 0.03), (0.60, 0.80, 0.02)):
        ring = cushion_ring(0.23 * sc_w, -0.04, 0.035, bol)
        rings.append([Vector((sx + x, sy + 0.215 - y, 1.425 + dz)) for x, y in ring])
    loft(bk, rings, True, True, True, mat=MI['src_ST_Leather'])
    rbox(bk, (sx, sy + 0.215, 2.13), (0.26, 0.085, 0.16), MI['src_ST_Leather'], bevel=0.03, segs=3)   # headrest
    bk = subsurf_bm(bk)
    xform_bm(bk, TB)
    join_bm(cu, bk)
    bmesh.ops.recalc_face_normals(cu, faces=cu.faces)
    BVH = BVHTree.FromBMesh(cu)

    def on_surf(p, lift=0.004):
        q, n, i, d = BVH.find_nearest(Vector(p))
        return q + n * lift, n

    bm = cu
    hard = bmesh.new()
    for dx in (-0.08, 0.08):                             # headrest posts
        cylinder(hard, (sx + dx, sy + 0.215, 2.00), (sx + dx, sy + 0.215, 2.07), 0.0055, 0.0055, 10,
                 mat=MI['src_ST_Chrome'])
    rbox(hard, (sx, sy + 0.266, 1.425 + 0.29), (0.44, 0.022, 0.57), MI['src_ST_Plastic'], bevel=0.010, segs=2)  # back shell
    rbox(hard, (sx, sy + 0.284, 1.425 + 0.17), (0.34, 0.016, 0.22), MI['src_ST_Plastic'], bevel=0.006, segs=1)  # pocket
    rbox(hard, (sx, sy + 0.258, 1.425 + 0.625), (0.080, 0.048, 0.062), MI['src_ST_Plastic'], bevel=0.008, segs=2)  # reel
    rbox(hard, (sx, sy + 0.229, 1.425 + 0.603), (0.10, 0.012, 0.012), MI['src_ST_Metal'], bevel=0.003, segs=1)  # guide
    xform_bm(hard, TB)
    for dx in (-0.19, 0.19):                             # side rails, legs, track carriages
        sweep(hard, [Vector((sx + dx, sy - 0.23, 1.292)), Vector((sx + dx, sy + 0.19, 1.300)),
                     Vector((sx + dx, sy + 0.235, 1.36))], 0.011, 0.011, 10, mat=MI['src_ST_Metal'])
        for dy in (-0.17, 0.15):
            cx_ = sx + dx * 0.79
            rbox(hard, (cx_, sy + dy, FZ + 0.031), (0.030, 0.075, 0.020), MI['src_ST_Metal'], bevel=0.004, segs=1)
            cylinder(hard, (cx_, sy + dy, FZ + 0.04), (sx + dx, sy + dy, 1.29), 0.0105, 0.0105, 10,
                     mat=MI['src_ST_Metal'])
        cylinder(hard, (sx + dx * 0.88, sy - 0.17, 1.16), (sx + dx * 0.88, sy + 0.15, 1.16), 0.008, 0.008, 8,
                 mat=MI['src_ST_Metal'])
    for dy in (-0.17, 0.15):
        cylinder(hard, (sx - 0.19, sy + dy, 1.20), (sx + 0.19, sy + dy, 1.20), 0.008, 0.008, 8, mat=MI['src_ST_Metal'])
    rbox(hard, (sx, sy - 0.02, 1.306), (0.40, 0.42, 0.024), MI['src_ST_Plastic'], bevel=0.008, segs=1)       # seat pan
    sweep(hard, [Vector((sx - 0.12, sy - 0.24, 1.285)), Vector((sx, sy - 0.272, 1.282)),
                 Vector((sx + 0.12, sy - 0.24, 1.285))], 0.005, 0.005, 8, mat=MI['src_ST_Chrome'])            # fore/aft bar
    ob_ = -inb                                            # outboard: recline lever
    sweep(hard, [Vector((sx + ob_ * 0.205, sy + 0.12, 1.33)), Vector((sx + ob_ * 0.215, sy + 0.02, 1.335)),
                 Vector((sx + ob_ * 0.215, sy - 0.05, 1.345))], 0.006, 0.005, 8, mat=MI['src_ST_Chrome'])
    rbox(hard, (sx + ob_ * 0.215, sy - 0.065, 1.347), (0.016, 0.040, 0.018), MI['src_ST_Plastic'], bevel=0.006, segs=2)
    arm = bmesh.new()                                     # inboard armrest on a pivot bracket
    rbox(arm, (sx + inb * 0.255, sy + 0.02, 1.585), (0.058, 0.30, 0.050), MI['src_ST_Leather'], bevel=0.018, segs=3)
    arm = subsurf_bm(arm)
    join_bm(bm, arm)
    rbox(hard, (sx + inb * 0.245, sy + 0.17, 1.545), (0.020, 0.07, 0.07), MI['src_ST_Metal'], bevel=0.005, segs=1)
    cylinder(hard, (sx + inb * 0.255, sy + 0.17, 1.55), (sx + inb * 0.230, sy + 0.17, 1.55), 0.010, 0.010, 10,
             mat=MI['src_ST_Chrome'])
    join_bm(bm, hard)
    # ---- harness. On: worn (virtual occupant), Off: retracted shoulder straps + belts laid on the cushion
    W_, T_ = 0.044, 0.004
    buckle = Vector((sx, sy - 0.05, 1.505))
    bon, boff = bmesh.new(), bmesh.new()
    for sd in (-1, 1):
        reel_out = TB @ Vector((sx + sd * 0.028, sy + 0.226, 2.025))
        over = TB @ Vector((sx + sd * 0.075, sy + 0.175, 2.04))
        path = [reel_out, over, Vector((sx + sd * 0.085, -2.07, 2.02)), Vector((sx + sd * 0.080, -2.135, 1.93)),
                Vector((sx + sd * 0.062, -2.175, 1.80)), Vector((sx + sd * 0.040, -2.215, 1.66)),
                buckle + Vector((sd * 0.016, 0.006, 0.032))]
        pts = spline(path, 4)
        flat_strap(bon, pts, [Vector((0, -0.4, 1)).lerp(Vector((0, -1, 0.35)), smooth01(-2.0, -2.11, p.y)) for p in pts],
                   W_, T_, MI['src_ST_Strap'])
        lap = [Vector((sx + sd * 0.212, sy + 0.165, 1.40)), Vector((sx + sd * 0.20, sy + 0.08, 1.475)),
               Vector((sx + sd * 0.15, sy - 0.0, 1.53)), Vector((sx + sd * 0.07, sy - 0.04, 1.53)),
               buckle + Vector((sd * 0.024, 0.0, 0.0))]
        pts = spline(lap, 4)
        flat_strap(bon, pts, [Vector((0, -0.3, 1)) for p in pts], W_, T_, MI['src_ST_Strap'])
        rbox(bon, lap[0] + Vector((0, 0, -0.01)), (0.014, 0.03, 0.03), MI['src_ST_Metal'], bevel=0.003, segs=1)
        # Off: shoulder strap retracted against the backrest, tongue at the end
        a = TB @ Vector((sx + sd * 0.028, sy + 0.226, 2.025))
        offp = [on_surf(TB @ Vector((sx + sd * (0.03 + 0.012 * k), sy + 0.17 - 0.004 * k, 2.02 - 0.045 * k)))
                for k in range(5)]
        top_ = on_surf(TB @ Vector((sx + sd * 0.029, sy + 0.200, 2.04)))
        pts = [a, top_[0]] + [q for q, n in offp]
        ups = [top_[1], top_[1]] + [n for q, n in offp]
        flat_strap(boff, pts, ups, W_, T_, MI['src_ST_Strap'])
        q, n = offp[-1]
        rbox(boff, q + n * 0.004 + Vector((0, 0, -0.022)), (0.030, 0.006, 0.026), MI['src_ST_Chrome'], bevel=0.003,
             segs=1)
        # Off: lap belt lying along the cushion side bolster
        offl = [on_surf(Vector((sx + sd * 0.205, sy + 0.16 - 0.07 * k, 1.44))) for k in range(6)]
        flat_strap(boff, [lap[0]] + [q for q, n in offl], [Vector((0, 0, 1))] + [n for q, n in offl], W_, T_,
                   MI['src_ST_Strap'])
        rbox(boff, lap[0] + Vector((0, 0, -0.01)), (0.014, 0.03, 0.03), MI['src_ST_Metal'], bevel=0.003, segs=1)
    crotch = [Vector((sx, sy - 0.16, 1.42)), Vector((sx, sy - 0.12, 1.47)), buckle + Vector((0, 0.004, -0.02))]
    flat_strap(bon, spline(crotch, 4), [Vector((0, -1, 0.3))] * 9, W_, T_, MI['src_ST_Strap'])
    offc = [on_surf(Vector((sx, sy - 0.16 - 0.03 * k, 1.425 - 0.02 * k * k))) for k in range(4)]
    flat_strap(boff, [q for q, n in offc], [n for q, n in offc], W_, T_, MI['src_ST_Strap'])
    revolve(bon, [(0.0, 0.0), (0.0, 0.036), (-0.008, 0.038), (-0.013, 0.030), (-0.015, 0.0)], 'Y',
            (buckle.x, buckle.y, buckle.z + 0.012), segs=24, mat=MI['src_ST_Chrome'])
    boff_c = Vector((sx + inb * 0.215, sy - 0.20, 1.40))
    revolve(boff, [(0.0, 0.0), (0.0, 0.036), (inb * 0.008, 0.038), (inb * 0.012, 0.030), (inb * 0.014, 0.0)], 'X',
            tuple(boff_c), segs=24, mat=MI['src_ST_Chrome'])
    mk(f'Belt_{tag}_On', bon, tuple(buckle), axis='scale', note='harness buckled: scale 1 when buckled, 0 when open')
    mk(f'Belt_{tag}_Off', boff, tuple(boff_c), axis='scale', note='harness open: scale 1 when open, 0 when buckled')
    mk(f'CP_Seat_{tag}', bm, smooth=60)

# ------------------------------------------------------------------ sun visors (stowed flat under the headliner, hinge on the windshield header)
for bone, vx in LY.VISORS:
    hz_ = head_z(-2.62) - 0.009
    hinge = Vector((vx, -2.627, hz_))
    bm = bmesh.new()
    bmv = bmesh.new()
    rbox(bmv, hinge + Vector((0, 0.083, -0.007)), (0.30, 0.15, 0.010), MI['src_CP_Trim'], bevel=0.0045, segs=2)
    slope = math.atan2(head_z(-2.62) - head_z(-2.47), 0.15)
    xform_bm(bmv, Matrix.Translation(hinge) @ Matrix.Rotation(-slope, 4, 'X') @ Matrix.Translation(-hinge))
    join_bm(bm, bmv)
    cylinder(bm, hinge + Vector((0.155, 0, 0)), hinge + Vector((-0.155, 0, 0)), 0.0055, 0.0055, 10,
             mat=MI['src_CP_Metal'])
    mk(bone, bm, tuple(hinge), axis='lateral', note='visor: rest stowed, deploy = swing down 80 deg')
bm = bmesh.new()
for bone, vx in LY.VISORS:                               # hinge brackets (static)
    for dxx in (0.16, -0.16):
        rbox(bm, (vx + dxx, -2.627, head_z(-2.62) - 0.004), (0.014, 0.020, 0.016), MI['src_CP_Metal'], bevel=0.003,
             segs=1)
mk('CP_VisorMounts', bm)

# ------------------------------------------------------------------ headsets on hooks at the cargo barrier posts
bm = bmesh.new()
for px in POST_X:
    hook = Vector((px, BARRIER_Y - 0.0225, 2.16))
    cylinder(bm, hook, hook + Vector((0, -0.032, 0.008)), 0.004, 0.004, 8, mat=MI['src_CP_Chrome'])
    c = hook + Vector((0, -0.030, -0.080))
    angs = [math.radians(a) for a in range(18, 163, 9)]
    arc = [c + Vector((0.080 * math.cos(a), 0, 0.080 * math.sin(a))) for a in angs]
    flat_strap(bm, arc, [Vector((math.cos(a), 0, math.sin(a))) for a in angs], 0.030, 0.010, MI['src_CP_Headset'])
    for a in (angs[0], angs[-1]):
        sgn = 1 if math.cos(a) > 0 else -1
        e = c + Vector((0.080 * math.cos(a), 0, 0.080 * math.sin(a)))
        cylinder(bm, e, e + Vector((0, 0, -0.035)), 0.005, 0.005, 8, mat=MI['src_CP_Chrome'])          # slider
        cc = e + Vector((-sgn * 0.006, 0, -0.058))
        revolve(bm, [(0.0, 0.0), (0.0, 0.038), (-sgn * 0.010, 0.042), (-sgn * 0.030, 0.042), (-sgn * 0.036, 0.036),
                     (-sgn * 0.038, 0.0)], 'X', tuple(cc), segs=20, mat=MI['src_CP_Headset'])
        revolve(bm, [(0.0, 0.0), (0.0, 0.040), (sgn * 0.010, 0.036), (sgn * 0.013, 0.026), (sgn * 0.012, 0.0)], 'X',
                tuple(cc), segs=20, mat=MI['src_CP_Rubber'])
        if sgn > 0:                                      # mic boom
            sweep(bm, spline([cc + Vector((-0.02, -0.03, 0.0)), cc + Vector((-0.03, -0.09, -0.02)),
                              cc + Vector((-0.06, -0.14, -0.03)), cc + Vector((-0.09, -0.16, -0.035))], 4),
                  0.0035, 0.0035, 6, mat=MI['src_CP_Headset'])
            revolve(bm, [(0.0, 0.0), (0.0, 0.009), (0.02, 0.009), (0.024, 0.0)], 'Y',
                    tuple(cc + Vector((-0.09, -0.16, -0.035))), segs=10, mat=MI['src_CP_Rubber'])
        else:                                            # cable
            sweep(bm, spline([cc + Vector((0, 0, -0.04)), cc + Vector((0.01, -0.01, -0.25)),
                              cc + Vector((0.03, 0.01, -0.50)), cc + Vector((0.01, -0.03, -0.70))], 5),
                  0.0038, 0.0038, 6, mat=MI['src_CP_Headset'])
mk('CP_Headsets', bm)

# ------------------------------------------------------------------ rear bulkhead: first-aid kit and a second extinguisher (cargo zone)
bm = bmesh.new()
rbox(bm, (0.40, REAR_Y - 0.008 - 0.045, 1.86), (0.24, 0.09, 0.16), MI['src_CP_Needle'], bevel=0.012, segs=2)
rbox(bm, (0.40, REAR_Y - 0.008 - 0.0915, 1.86), (0.05, 0.002, 0.05), MI['src_CP_KnobRed'], bevel=0.001, segs=1)
rbox(bm, (0.40, REAR_Y - 0.008 - 0.0915, 1.86), (0.016, 0.0022, 0.05), MI['src_CP_Needle'])
rbox(bm, (0.40, REAR_Y - 0.008 - 0.0915, 1.86), (0.05, 0.0022, 0.016), MI['src_CP_Needle'])
for zz in (1.80, 1.92):
    rbox(bm, (0.40, REAR_Y - 0.008 - 0.004, zz), (0.27, 0.008, 0.012), MI['src_CP_Metal'], bevel=0.002, segs=1)
xe = -0.40
revolve(bm, [(1.47, 0.0), (1.47, 0.036), (1.48, 0.040), (1.73, 0.040), (1.75, 0.031), (1.77, 0.018), (1.785, 0.0)],
        'Z', (xe, REAR_Y - 0.008 - 0.048, 0.0), segs=20, mat=MI['src_CP_KnobRed'])
rbox(bm, (xe, REAR_Y - 0.008 - 0.048, 1.795), (0.022, 0.05, 0.016), MI['src_CP_Black'], bevel=0.003, segs=1)
for zz in (1.53, 1.69):
    flat_strap(bm, [Vector((xe + 0.044 * math.cos(a), REAR_Y - 0.008 - 0.048 + 0.044 * math.sin(a), zz))
                    for a in [math.radians(-180 + k * 18) for k in range(11)]],
               [Vector((math.cos(math.radians(-180 + k * 18)), math.sin(math.radians(-180 + k * 18)), 0))
                for k in range(11)], 0.022, 0.003, MI['src_CP_Metal'])
    rbox(bm, (xe, REAR_Y - 0.010, zz), (0.10, 0.006, 0.026), MI['src_CP_Metal'], bevel=0.002, segs=1)
mk('CP_RearKit', bm)

# ------------------------------------------------------------------ placards (gauge atlas cell 20)
bm = bmesh.new()
X_, Y_, Z_ = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
p20_quad(bm, 'QUAD', (0.0, -2.962, P['z_top_front'] + 0.0006), -X_, -Y_, 0.124, 0.0116)
p20_quad(bm, 'FLAP', (-phw - 0.0194, -2.66, 1.30), -Y_, Z_, 0.14, 0.0933)
p20_quad(bm, 'TRIM', (phw + 0.0027, ty, tz + tr + 0.022), Y_, Z_, 0.056, 0.0187)
p20_quad(bm, 'FUEL', (0.0, py1 + 0.0023, 1.306), -X_, Z_, 0.066, 0.0165)
p20_quad(bm, 'EXT', (-0.40, REAR_Y - 0.0090, 1.835), X_, Z_, 0.12, 0.0225)
p20_quad(bm, 'FLOOR', (0.0, REAR_Y - 0.0090, 1.24), X_, Z_, 0.44, 0.0653)
mk('CP_Placards', bm)


# ------------------------------------------------------------------ door trims (merged into the door objects)
def door_trim(door, side, outline, r, win, kind):
    bm = bmesh.new()
    inward = lambda p: Vector((-side, 0, 0))
    mapd = lambda u, v, d: skin_pt(side, u, v, 0.002 + d)
    O_ = LY.rounded_poly(LY.offset_poly(outline, -(LY.DOOR_GAP + 0.010)), max(r - 0.016, 0.02), seg=4)
    Hw = LY.rounded_poly(LY.offset_poly(win[0], 0.010), win[1] + 0.010, seg=4)
    panel2d(bm, O_, [Hw], mapd, inward, depth=0.026, cham=0.012, mat=MI['src_IN_Liner'], grid=0.06)
    surround(bm, side, win[0], win[1], 0.012, MI['src_IN_Trim'], lip=0.010)
    F = 0.028                                            # trim face depth from the inner skin
    if kind == 'pilot':
        ya, yb = -2.62, -2.14                            # armrest
        prof = [(-0.004, 1.553), (0.010, 1.560), (0.034, 1.598), (0.054, 1.640), (0.064, 1.668), (0.066, 1.682),
                (0.058, 1.694), (0.036, 1.699), (-0.004, 1.698)]
        rings = []
        for k in range(15):
            y = ya + (yb - ya) * k / 14
            e = 0.25 + 0.75 * smooth01(0.0, 0.06, min(y - ya, yb - y))
            rings.append([skin_pt(side, y, z, F + n * e) for n, z in prof])
        loft(bm, rings, True, True, True, mat=MI['src_IN_Vinyl'])
        pull = [skin_pt(side, -2.58, 1.738, F - 0.002), skin_pt(side, -2.565, 1.738, F + 0.050),
                skin_pt(side, -2.435, 1.738, F + 0.050), skin_pt(side, -2.42, 1.738, F - 0.002)]
        sweep(bm, spline(pull, 4), 0.0105, 0.0105, 12, mat=MI['src_IN_Vinyl'])
        for yy in (-2.58, -2.42):
            p0 = skin_pt(side, yy, 1.738, F - 0.004)
            cylinder(bm, p0, skin_pt(side, yy, 1.738, F + 0.008), 0.017, 0.015, 12, mat=MI['src_IN_Trim'])
        # inside opening lever in an escutcheon (forward part of the door)
        c = skin_pt(side, -2.86, 1.715, F)
        rbox(bm, c + Vector((-side * 0.002, 0, 0)), (0.006, 0.105, 0.048), MI['src_IN_Trim'], bevel=0.004, segs=2)
        lv0 = skin_pt(side, -2.895, 1.715, F + 0.010)
        lv1 = skin_pt(side, -2.810, 1.712, F + 0.016)
        sweep(bm, [lv0, lv0.lerp(lv1, 0.5), lv1], 0.0065, 0.0045, 10, mat=MI['src_IN_Steel'],
              up_hint=Vector((-side, 0, 0)))
        cylinder(bm, skin_pt(side, -2.895, 1.715, F + 0.003), lv0 + Vector((-side * 0.004, 0, 0)), 0.009, 0.009, 12,
                 mat=MI['src_IN_Steel'])
        # map pocket
        pk = [(-0.003, 1.198), (0.020, 1.200), (0.030, 1.215), (0.031, 1.380), (0.026, 1.386), (0.021, 1.380),
              (0.020, 1.222), (-0.003, 1.220)]
        rings = [[skin_pt(side, y, z, F + n) for n, z in pk] for y in [-2.84 + 0.62 * k / 8 for k in range(9)]]
        loft(bm, rings, True, True, True, mat=MI['src_IN_Kick'])
        p20_quad(bm, 'DOOR', skin_pt(side, -2.86, 1.655, F + 0.0012), Vector((0, -side, 0)), Vector((0, 0, 1)), 0.07,
                 0.0175)
    else:
        c = skin_pt(side, -0.70, 1.72, F)                # recessed handle cup + lever at the free (front) edge
        rbox(bm, c + Vector((-side * 0.002, 0, 0)), (0.006, 0.13, 0.055), MI['src_IN_Trim'], bevel=0.005, segs=2)
        lv0 = skin_pt(side, -0.745, 1.72, F + 0.010)
        lv1 = skin_pt(side, -0.655, 1.718, F + 0.016)
        sweep(bm, [lv0, lv0.lerp(lv1, 0.5), lv1], 0.0065, 0.0045, 10, mat=MI['src_IN_Steel'],
              up_hint=Vector((-side, 0, 0)))
        cylinder(bm, skin_pt(side, -0.745, 1.72, F + 0.003), lv0 + Vector((-side * 0.004, 0, 0)), 0.009, 0.009, 12,
                 mat=MI['src_IN_Steel'])
        pull = [skin_pt(side, -0.80, 1.96, F - 0.002), skin_pt(side, -0.785, 1.96, F + 0.045),
                skin_pt(side, -0.645, 1.96, F + 0.045), skin_pt(side, -0.63, 1.96, F - 0.002)]
        sweep(bm, spline(pull, 4), 0.010, 0.010, 12, mat=MI['src_IN_Vinyl'])
        for yy in (-0.80, -0.63):
            cylinder(bm, skin_pt(side, yy, 1.96, F - 0.004), skin_pt(side, yy, 1.96, F + 0.008), 0.016, 0.014, 12,
                     mat=MI['src_IN_Trim'])
        rbox(bm, skin_pt(side, -0.20, 1.40, F + 0.0015), (0.003, 0.16, 0.05), MI['src_IN_Steel'], bevel=0.002, segs=1)
        p20_quad(bm, 'CDOOR', skin_pt(side, -0.70, 1.663, F + 0.0012), Vector((0, -side, 0)), Vector((0, 0, 1)), 0.09,
                 0.0169)
    merge_into(door, bm)


for side, s_ in ((1, 'L'), (-1, 'R')):
    door_trim(f'PilotDoor_{s_}', side, PD, LY.PILOT_DOOR[1], LY.W1, 'pilot')
    door_trim(f'CargoDoor_{s_}', side, CD, LY.CARGO_DOOR[1], LY.CARGO_WIN, 'cargo')
# ================================================================== sockets + summary
SOCKETS = {'Socket_PilotEye': LY.PILOT_EYE, 'Socket_CopilotEye': LY.COPILOT_EYE}
for i, p in enumerate(sorted(TIEDOWNS, key=lambda q: (q[1], -q[0])), 1):     # front to back, left to right
    SOCKETS[f'Socket_TieDown_{i:02d}'] = tuple(round(v, 4) for v in p)
_dome = [v for v in bpy.data.objects['CP_Overhead'].data.vertices]
SOCKETS['_dome_z'] = (0.0, 0.0, round(min((bpy.data.objects['CP_Overhead'].matrix_world @ v.co).z for v in _dome), 4))
json.dump(dict(rig=RIG, static=STATIC, sockets={k: list(v) for k, v in SOCKETS.items()}),
          open(os.path.join(HERE, 'out', 'cockpit_rig.json'), 'w'), indent=1)
tris = 0
dg = bpy.context.evaluated_depsgraph_get()
per = {}
for ob in CP.objects:
    if ob.type != 'MESH':
        continue
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    tris += len(me.loop_triangles)
    per[ob.name] = len(me.loop_triangles)
    ob.evaluated_get(dg).to_mesh_clear()
for k, v in sorted(per.items(), key=lambda kv: -kv[1])[:25]:
    print(f'  {k:28s} {v}')
print('COCKPIT objects', len(CP.objects), 'tris', tris, 'moving parts', len(RIG))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v2.blend'))
print('saved')
