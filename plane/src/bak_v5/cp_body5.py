
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
