"""Cockpit blockout for the FP sim: floor, bulkheads, instrument panel + gauges (UV-mapped to T_Gauges),
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
    solid = [f for f in bm.faces if not f[lay]]
    bmesh.ops.recalc_face_normals(bm, faces=solid)
    for f in bm.faces:
        if f[lay]:
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


# ================================================================== floor, bulkheads
bm = bmesh.new()
box(bm, (0, (LY.FIREWALL_Y + LY.REAR_BULKHEAD_Y) / 2, LY.FLOOR_Z - 0.01), (1.32, LY.REAR_BULKHEAD_Y - LY.FIREWALL_Y, 0.02),
    mat=MI['src_CP_Floor'])
for sx in LY.SEATS_X:                                  # seat rails
    for dx in (-0.16, 0.16):
        box(bm, (sx + dx, -2.10 + LY.SEAT_DY, LY.FLOOR_Z + 0.008), (0.03, 0.9, 0.016), mat=MI['src_CP_Metal'])
for xx in (-0.35, 0.35):                               # cargo rails
    box(bm, (xx, 0.0, LY.FLOOR_Z + 0.008), (0.05, 2.4, 0.016), mat=MI['src_CP_Metal'])
mk('CP_Structure', bm)


def station_at(y):
    st = LY.fuselage_stations()
    for a, b in zip(st[:-1], st[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0])
            return [a[i] + (b[i] - a[i]) * t for i in range(1, 5)]
    raise ValueError(y)


def bulkhead(y, z_max=None, inset=0.034, thick=0.02):
    zb, zt, hw, n = station_at(y)
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    ring = [(x, zc + z) for x, z in superellipse(hw - inset, hh - inset, n, 48)]
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
bm2 = bulkhead(LY.REAR_BULKHEAD_Y)
me = bpy.data.meshes.new('tmp')
bm2.to_mesh(me)
bm.from_mesh(me)
bpy.data.meshes.remove(me)
bm2.free()
mk('CP_Bulkheads', bm)

# ================================================================== instrument panel + glareshield
bm = bmesh.new()
pz0, pz1 = LY.PANEL_Z
box(bm, (0, LY.PANEL_Y - 0.015, (pz0 + pz1) / 2), (LY.PANEL_HW * 2, 0.03, pz1 - pz0), mat=MI['src_CP_Panel'],
    bevel=0.006, bevel_segs=1)
g = LY.GLARE
box(bm, (0, (g['y0'] + g['y1']) / 2, (g['z0'] + g['z1']) / 2), (g['hw'] * 2, g['y1'] - g['y0'], g['z1'] - g['z0']),
    mat=MI['src_CP_Black'], bevel=0.015, bevel_segs=2)
# lower panel "knee" cover over the pedestal area
box(bm, (0, LY.PANEL_Y - 0.10, pz0 - 0.02), (LY.PANEL_HW * 2, 0.20, 0.04), mat=MI['src_CP_Panel'], bevel=0.008)
# compass on the glareshield
box(bm, (0, -3.14, g['z1'] + 0.035), (0.075, 0.06, 0.06), mat=MI['src_CP_Black'], bevel=0.008, bevel_segs=2)
rect_uv(bm, 0.025, -0.025, g['z1'] + 0.02, g['z1'] + 0.05, -3.109, MI['src_CP_Gauges'],
        5.30 / 8, 5.70 / 8, 1 - 0.62 / 4, 1 - 0.38 / 4)
mk('CP_Panel', bm)

# ================================================================== gauges
bm = bmesh.new()
fy = LY.PANEL_Y + 0.003          # face depth (towards pilot is +Y)
for name, (gx, gz, dia, cell, needles) in LY.GAUGES.items():
    R = dia / 2
    # bezel ring (revolve profile around the gauge axis, along Y)
    prof = [(fy - 0.002, R - 0.004), (fy + 0.006, R - 0.003), (fy + 0.009, R - 0.001), (fy + 0.008, R),
            (LY.PANEL_Y, R + 0.002)]
    revolve(bm, [(y, r) for y, r in prof], 'Y', (gx, 0, gz), segs=32, mat=MI['src_CP_Black'])
    if name == 'ATT':
        annulus(bm, (gx, gz), 0.027, R - 0.004, fy + 0.004, mat=MI['src_CP_Gauges'], uv_cell=cell)
        # miniature airplane (fixed)
        box(bm, (gx, fy + 0.006, gz), (0.036, 0.002, 0.003), mat=MI['src_CP_Orange'])
        box(bm, (gx, fy + 0.006, gz - 0.004), (0.004, 0.002, 0.008), mat=MI['src_CP_Orange'])
        disc(bm, (gx, gz), R - 0.004, fy - 0.001, mat=MI['src_CP_Black'])
    elif name == 'HDG':
        # lubber line + airplane silhouette (fixed overlay); card is a moving part
        box(bm, (gx, fy + 0.006, gz + R * 0.83), (0.002, 0.002, 0.010), mat=MI['src_CP_Orange'])
        box(bm, (gx, fy + 0.006, gz), (0.026, 0.002, 0.003), mat=MI['src_CP_Orange'])
        box(bm, (gx, fy + 0.006, gz - 0.002), (0.003, 0.002, 0.020), mat=MI['src_CP_Orange'])
        disc(bm, (gx, gz), R - 0.004, fy - 0.001, mat=MI['src_CP_Black'])
    else:
        disc(bm, (gx, gz), R - 0.004, fy, mat=MI['src_CP_Gauges'], uv_cell=cell, uv_scale=1.0)
    # cover glass
    disc(bm, (gx, gz), R - 0.003, fy + 0.0085, segs=24, mat=MI['src_CP_GaugeGlass'])
mk('CP_Gauges', bm, smooth=60)

# moving gauge parts
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
            # ATT: roll bone (rotation) -> pitch bone (vertical translation) carrying the sky/ground card
            bm2 = bmesh.new()
            disc(bm2, (gx, gz), 0.040, fy + 0.001, segs=40, mat=MI['src_CP_Gauges'], uv_cell=LY.ATT_CARD_CELL)
            mk('ATT_Pitch', bm2, piv, parent='ATT_Roll', axis='translate_up',
               note='card offset: +6 mm per +10 deg pitch (nose up = card moves down)')
            bm.verts.new(piv)  # empty placeholder mesh for the roll bone
            mk('ATT_Roll', bm, piv, axis='gauge', note='bank angle, card rotates opposite to the aircraft roll')
        elif kind == 'card':
            disc(bm, (gx, gz), R - 0.001, fy + 0.002, segs=40, mat=MI['src_CP_Gauges'], uv_cell=cell)
            mk(bone, bm, piv, axis='gauge', note='heading card: rotate by -heading')
        elif kind == 'plane':
            box(bm, (gx, fy + 0.004, gz), (R * 1.5, 0.002, 0.004), mat=MI['src_CP_Needle'])
            box(bm, (gx, fy + 0.004, gz + 0.004), (0.005, 0.002, 0.010), mat=MI['src_CP_Needle'])
            cylinder(bm, (gx, fy + 0.004, gz), (gx, fy + 0.006, gz), 0.006, 0.006, 12, mat=MI['src_CP_Needle'])
            mk(bone, bm, piv, axis='gauge', note='turn rate: standard rate = 20 deg')
        elif kind == 'ball':
            arc_c = (gx, gz + 0.062 * dia / LY.G6)          # tube arc centre above the gauge centre
            bz = gz - 0.022 * dia / LY.G6
            revolve(bm, [(fy + 0.001, 0.0), (fy + 0.002, 0.0035), (fy + 0.0045, 0.0045), (fy + 0.007, 0.0035),
                         (fy + 0.008, 0.0)], 'Y', (gx, 0, bz), segs=12, mat=MI['src_CP_Black'])
            mk(bone, bm, (arc_c[0], fy + 0.003, arc_c[1]), axis='gauge',
               note='slip ball: rotates about the tube arc centre, +-15 deg = full deflection')
        else:
            raise ValueError(kind)

# ================================================================== radios
bm = bmesh.new()
for name, (rx, rz, rw, rh, cell) in LY.RADIOS.items():
    box(bm, (rx, LY.PANEL_Y + 0.006, rz), (rw, 0.012, rh), mat=MI['src_CP_Black'], bevel=0.003)
    col, row = cell % 8, cell // 8
    frac = rh / rw
    rect_uv(bm, rx + rw / 2 - 0.002, rx - rw / 2 + 0.002, rz - rh / 2 + 0.002, rz + rh / 2 - 0.002,
            LY.PANEL_Y + 0.0125, MI['src_CP_Gauges'], col / 8, (col + 1) / 8, 1 - (row + frac) / 4, 1 - row / 4)
    # knobs
    for kx in (rx + rw / 2 - 0.018, rx - rw / 2 + 0.018):
        if name == 'GPSCOM':
            cylinder(bm, (kx, LY.PANEL_Y + 0.012, rz - rh / 2 + 0.018), (kx, LY.PANEL_Y + 0.030, rz - rh / 2 + 0.018),
                     0.009, 0.008, 16, mat=MI['src_CP_Black'])
mk('CP_Radios', bm)

# ================================================================== switches + labels + breakers
bm = bmesh.new()
rect_uv(bm, 0.64, 0.17, LY.SWITCH_Z - 0.036, LY.SWITCH_Z - 0.018, LY.PANEL_Y + 0.0005, MI['src_CP_Gauges'],
        0.0, 1.0, 1 - (3 * 512 + 160) / 2048, 1 - (3 * 512) / 2048)
for bone, sx in LY.SWITCHES:
    box(bm, (sx, LY.PANEL_Y + 0.002, LY.SWITCH_Z), (0.022, 0.004, 0.030), mat=MI['src_CP_Metal'], bevel=0.002)
for i in range(3):                                   # circuit breakers, copilot lower panel
    for j in range(8):
        bx, bz = -0.22 - j * 0.045, 1.64 - i * 0.045
        cylinder(bm, (bx, LY.PANEL_Y, bz), (bx, LY.PANEL_Y + 0.012, bz), 0.0065, 0.0055, 10, mat=MI['src_CP_Black'])
mk('CP_Switchgear', bm)
for bone, sx in LY.SWITCHES:
    bm = bmesh.new()
    piv = (sx, LY.PANEL_Y + 0.004, LY.SWITCH_Z)
    tip = Vector((sx, LY.PANEL_Y + 0.020, LY.SWITCH_Z - 0.006))       # rest = down (OFF), lever leans down
    cylinder(bm, Vector(piv), tip, 0.0028, 0.0022, 8, mat=MI['src_CP_Metal'])
    revolve(bm, [(0.0, 0.0), (0.0, 0.0035), (0.004, 0.0035), (0.004, 0.0)], 'Y', tuple(tip), segs=8,
            mat=MI['src_CP_Metal'])
    mk(bone, bm, piv, axis='lateral', note='toggle: rest = OFF (down); ON = +40 deg (lever up)')

# ================================================================== yokes
for side, yx in (('P', LY.YOKE_X[0]), ('C', LY.YOKE_X[1])):
    hub = Vector((yx, LY.YOKE_HUB_Y, LY.YOKE_Z))
    bm = bmesh.new()
    cylinder(bm, Vector((yx, LY.PANEL_Y - 0.14, LY.YOKE_Z)), hub - Vector((0, 0.015, 0)), 0.016, 0.016, 12,
             mat=MI['src_CP_Metal'])
    mk(f'Yoke_{side}', bm, tuple(hub), axis='translate_fwd', note='pitch: push = forward, travel +-0.08 m')
    bm = bmesh.new()
    box(bm, hub, (0.07, 0.04, 0.06), mat=MI['src_CP_Black'], bevel=0.012, bevel_segs=2)
    for sg in (1, -1):
        path = [hub + Vector((sg * 0.02, 0.01, 0.0)), hub + Vector((sg * 0.10, 0.018, -0.008)),
                hub + Vector((sg * 0.145, 0.02, 0.02)), hub + Vector((sg * 0.155, 0.02, 0.09)),
                hub + Vector((sg * 0.150, 0.018, 0.115))]
        sweep(bm, path, 0.015, 0.015, 10, mat=MI['src_CP_Black'], up_hint=Vector((0, 1, 0)))
    cylinder(bm, hub + Vector((0.152, 0.018, 0.118)), hub + Vector((0.152, 0.018, 0.128)), 0.007, 0.007, 10,
             mat=MI['src_CP_KnobRed'])                                   # PTT button, pilot-left grip
    mk(f'Yoke_{side}_Roll', bm, tuple(hub), parent=f'Yoke_{side}', axis='fwd',
       note='roll: yoke rotation +-50 deg about the column axis')

# ================================================================== rudder pedals
for side, sx in (('P', LY.SEATS_X[0]), ('C', LY.SEATS_X[1])):
    for lr, dx in (('L', LY.PEDAL_DX), ('R', -LY.PEDAL_DX)):      # pilot-left pedal is at larger X
        px = sx + dx
        hy, hz = LY.PEDAL_HINGE
        bm = bmesh.new()
        top = Vector((px, hy + 0.06, hz + 0.20))
        cylinder(bm, Vector((px, hy, hz)), top, 0.010, 0.010, 8, mat=MI['src_CP_Metal'])
        box_rx(bm, (px, hy + 0.068, hz + 0.21), (0.075, 0.016, 0.15), -17.0, MI['src_CP_Metal'], bevel=0.004)
        cylinder(bm, Vector((px - 0.03, hy, hz)), Vector((px + 0.03, hy, hz)), 0.012, 0.012, 10, mat=MI['src_CP_Black'])
        mk(f'Pedal{side}_{lr}', bm, (px, hy, hz), axis='lateral',
           note='rudder: left pedal forward for left yaw; +-12 deg')

# ================================================================== pedestal, levers, flap lever, trim wheel
P = LY.PEDESTAL
bm = bmesh.new()
pts = [(P['hw'], P['y0'], LY.FLOOR_Z), (-P['hw'], P['y0'], LY.FLOOR_Z), (-P['hw'], P['y1'], LY.FLOOR_Z),
       (P['hw'], P['y1'], LY.FLOOR_Z), (P['hw'], P['y0'], P['z_top_front']), (-P['hw'], P['y0'], P['z_top_front']),
       (-P['hw'], P['y1'], P['z_top_back']), (P['hw'], P['y1'], P['z_top_back'])]
vs = [bm.verts.new(p) for p in pts]
for q in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
    bm.faces.new([vs[i] for i in q]).material_index = MI['src_CP_Panel']
for x, _, _ in [(l[1], 0, 0) for l in LY.LEVERS]:             # lever slots (dark strips on the top)
    box(bm, (x, LY.LEVER_PIVOT[0], LY.LEVER_PIVOT[1] + 0.004), (0.008, 0.16, 0.004), mat=MI['src_CP_Black'])
box(bm, (0.078, -2.72, 1.24), (0.012, 0.19, 0.09), mat=MI['src_CP_Black'])      # trim wheel housing
mk('CP_Pedestal', bm)
KNOB = {'black': 'src_CP_Black', 'blue': 'src_CP_KnobBlue', 'red': 'src_CP_KnobRed'}
for bone, lx, kc in LY.LEVERS:
    py, pz = LY.LEVER_PIVOT
    piv = Vector((lx, py, pz))
    tip = piv + Vector((0, -0.05, 0.13))        # rest pose: mid travel, leaning forward
    bm = bmesh.new()
    cylinder(bm, piv, tip, 0.006, 0.005, 8, mat=MI['src_CP_Metal'])
    if kc == 'black':
        box(bm, tip + Vector((0, 0, 0.012)), (0.06, 0.022, 0.024), mat=MI[KNOB[kc]], bevel=0.006, bevel_segs=2)
    elif kc == 'blue':
        cylinder(bm, tip, tip + Vector((0, 0, 0.03)), 0.014, 0.014, 16, mat=MI[KNOB[kc]])
    else:
        box(bm, tip + Vector((0, 0, 0.014)), (0.022, 0.03, 0.028), mat=MI[KNOB[kc]], bevel=0.005, bevel_segs=2)
    mk(bone, bm, tuple(piv), axis='lateral', note='rest = mid travel; +-25 deg (forward = more)')
fb, fx, fyy, fz = LY.FLAP_LEVER
bm = bmesh.new()
piv = Vector((fx, fyy, fz))
tip = piv + Vector((-0.02, -0.02, 0.09))
cylinder(bm, piv, tip, 0.005, 0.005, 8, mat=MI['src_CP_Metal'])
box(bm, tip + Vector((0, 0, 0.01)), (0.035, 0.02, 0.012), mat=MI['src_CP_Needle'], bevel=0.004)
mk(fb, bm, tuple(piv), axis='lateral', note='flap detents 0/10/20/35 = 0/-12/-24/-36 deg')
tb, tx, ty, tz, tr = LY.TRIM_WHEEL
bm = bmesh.new()
prof = [(tx - 0.009, 0.0), (tx - 0.009, tr - 0.004), (tx - 0.006, tr), (tx + 0.006, tr), (tx + 0.009, tr - 0.004),
        (tx + 0.009, 0.0)]
revolve(bm, prof, 'X', (0, ty, tz), segs=36, mat=MI['src_CP_Black'],
        radial_fn=lambda i, j, r: r + (0.003 if (i % 2 == 0 and j in (2, 3)) else 0.0))
mk(tb, bm, (tx, ty, tz), axis='lateral', note='elevator trim wheel, +-360 deg')

# ================================================================== seats
for sx in LY.SEATS_X:
    bm = bmesh.new()
    box(bm, (sx, -2.13 + LY.SEAT_DY, 1.30), (0.44, 0.44, 0.05), mat=MI['src_CP_Metal'])                       # pan
    for dx in (-0.16, 0.16):
        for dy in (-0.18, 0.18):
            box(bm, (sx + dx, -2.13 + LY.SEAT_DY + dy, 1.18), (0.03, 0.03, 0.22), mat=MI['src_CP_Metal'])  # legs
    box(bm, (sx, -2.15 + LY.SEAT_DY, 1.37), (0.46, 0.46, 0.10), mat=MI['src_CP_Seat'], bevel=0.035, bevel_segs=3)   # cushion
    box_rx(bm, (sx, -1.86 + LY.SEAT_DY, 1.72), (0.46, 0.10, 0.62), -12.0, MI['src_CP_Seat'], bevel=0.035, segs=3)    # back
    box_rx(bm, (sx, -1.80 + LY.SEAT_DY, 2.12), (0.26, 0.09, 0.17), -12.0, MI['src_CP_Seat'], bevel=0.03, segs=3)     # headrest
    for dx in (-0.08, 0.08):
        box_rx(bm, (sx + dx, -1.81 + LY.SEAT_DY, 2.02), (0.012, 0.012, 0.08), -12.0, MI['src_CP_Metal'])
    mk(f'CP_Seat_{"P" if sx > 0 else "C"}', bm)

# ================================================================== sockets (as zero-weight bones, recorded here)
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
