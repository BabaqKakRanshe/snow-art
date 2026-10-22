
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


# ------------------------------------------------------------------ yoke boots (v6: panel frame is in cp_panel6.py)
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
