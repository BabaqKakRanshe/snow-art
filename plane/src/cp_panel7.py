
# ================================================================== v7 INSTRUMENT PANEL (spec: panel7.py, atlas regions: tex/v7/atlas7.json)
# v7 on top of v6: cabin door switches (DOORS block), radio knobs and the ALT / HDG knobs as rig parts,
# Kollsman window (hole in the ALT dial) with the pressure disc ALT_Baro behind it, heading bug HDG_Bug.
# Recessed instruments behind sub-panel holes, engine block 2 x 4, systems + map case on the copilot side,
# 4 x 3 annunciator, radio stack with per-window display quads, lightplates (switches, breakers, labels).
# Gauge-atlas UVs are written in v5 space (u = px/4096, v = 1 - py/2048); cp_tail6 remaps them once to 4096 x 4096.
import panel7 as P6

PR = P6.load_regions()
PY6 = P6.PY
assert abs(PY6 - LY.PANEL_Y) < 1e-9


def add_mat(name, col):
    if name in MI:
        return
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*col, 1.0)
    M[name] = m
    MATS.append(m)
    MI[name] = len(MATS) - 1


add_mat('src_CP_Screen', (0.010, 0.013, 0.013))      # display quads (unbaked, UV 0..1)
G_MAT = MI['src_CP_Gauges']


def circle_pts(cx, cz, r, n):
    return [(cx + r * math.cos(2 * math.pi * i / n), cz + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def rect_pts(xl, xr, zb, zt):
    return [(xr, zb), (xl, zb), (xl, zt), (xr, zt)]


def art_rect(bm, reg_name, xl, xr, zb, zt, y, s0=0.0, t0=0.0, s1=None, t1=None):
    """quad facing +Y showing (a sub-rectangle in mm of) an atlas region; xl = pilot-left edge"""
    reg = PR[reg_name]
    wm, hm = reg['size_mm']
    s1 = wm if s1 is None else s1
    t1 = hm if t1 is None else t1
    u0, v1 = P6.region_uv(reg, s0, t0)
    u1, v0 = P6.region_uv(reg, s1, t1)
    return rect_uv(bm, xl, xr, zb, zt, y, G_MAT, u0, u1, v0, v1)


def plate_uv_fn(reg_name, xl, zt):
    reg = PR[reg_name]
    return lambda x, z: P6.region_uv(reg, (xl - x) * 1000.0, (zt - z) * 1000.0)


def cap_disc(bm, cx, cz, r, y, uvf, segs=16):
    """flat disc facing +Y with planar atlas UVs (breaker caps, jack plates)"""
    uvl, pl = bm.loops.layers.uv.verify(), plate_layer(bm)
    c = bm.verts.new((cx, y, cz))
    ring = [bm.verts.new((cx + r * math.cos(2 * math.pi * i / segs), y, cz + r * math.sin(2 * math.pi * i / segs)))
            for i in range(segs)]
    for i in range(segs):
        f = bm.faces.new((c, ring[(i + 1) % segs], ring[i]))
        f.material_index = G_MAT
        f[pl] = 1
        for lp in f.loops:
            lp[uvl].uv = uvf(lp.vert.co.x, lp.vert.co.z)


def disc_with_hole(bm, center, r, y, segs, mat, uv_cell, hole):
    """flat dial facing +Y with a rectangular window (dial-normalised hole x0..x1 to the pilot's right, z0..z1),
    UVs as disc(): the whole cell maps onto the dial radius"""
    cx, cz = center
    uvl, pl = bm.loops.layers.uv.verify(), plate_layer(bm)
    outer = [bm.verts.new((cx + r * math.cos(2 * math.pi * i / segs), y, cz + r * math.sin(2 * math.pi * i / segs)))
             for i in range(segs)]
    hx0, hx1, hz0, hz1 = hole['x0'], hole['x1'], hole['z0'], hole['z1']
    corners = [(hx0, hz0), (hx1, hz0), (hx1, hz1), (hx0, hz1)]
    ring = []
    for k in range(4):                                     # 3 points per side for well-shaped triangles
        a, b = corners[k], corners[(k + 1) % 4]
        for j in range(3):
            t = j / 3
            u = a[0] + (b[0] - a[0]) * t
            v = a[1] + (b[1] - a[1]) * t
            ring.append(bm.verts.new((cx - u * r, y, cz + v * r)))   # pilot's right = -X
    edges = []
    for loop in (outer, ring):
        for i in range(len(loop)):
            edges.append(bm.edges.new((loop[i], loop[(i + 1) % len(loop)])))
    res = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges, normal=Vector((0, 1, 0)))
    faces = [f for f in res['geom'] if isinstance(f, bmesh.types.BMFace)]
    col, row = uv_cell % 8, uv_cell // 8
    keep = []
    for f in faces:
        c = f.calc_center_median()
        u_ = -(c.x - cx) / r
        v_ = (c.z - cz) / r
        if hx0 < u_ < hx1 and hz0 < v_ < hz1:              # scanfill may cover the hole: drop those faces
            bm.faces.remove(f)
            continue
        f.material_index = mat
        f[pl] = 1
        f.normal_update()
        if f.normal.y < 0:
            f.normal_flip()
        for lp in f.loops:
            dx = (lp.vert.co.x - cx) / r
            dz = (lp.vert.co.z - cz) / r
            lp[uvl].uv = ((col + 0.5 - dx * 0.5) / 8, 1 - (row + 0.5 - dz * 0.5) / 4)
        keep.append(f)
    return keep


def box_sides(bm, xl, xr, zb, zt, y0, y1, mat, back=False):
    """rectangular block between y0 (rear) and y1 (front) without its front face (and rear unless back=True)"""
    vs = box(bm, ((xl + xr) / 2, (y0 + y1) / 2, (zb + zt) / 2), (abs(xl - xr), y1 - y0, zt - zb), mat=mat)
    faces = {f for v in vs for f in v.link_faces}
    kill = [f for f in faces if all(abs(v.co.y - y1) < 2e-5 for v in f.verts) or
            (not back and all(abs(v.co.y - y0) < 2e-5 for v in f.verts))]
    bmesh.ops.delete(bm, geom=kill, context='FACES_ONLY')


def lightplate(bm, reg_name, xl, xr, zb, zt, y_back, thick, side_mat='src_CP_Black'):
    box_sides(bm, xl, xr, zb, zt, y_back, y_back + thick, MI[side_mat])
    art_rect(bm, reg_name, xl, xr, zb, zt, y_back + thick)


def radial_bar(bm, cx, cz, y, r0, r1, a_deg, w, mat, t=0.0006):
    """small bar on a knob face, from radius r0 to r1 at clock angle a (pilot view)"""
    a = math.radians(a_deg)
    d = Vector((-math.sin(a), 0, math.cos(a)))
    s = Vector((math.cos(a), 0, math.sin(a)))
    c = Vector((cx, y + t / 2, cz)) + d * (r0 + r1) / 2
    tmp = bmesh.new()
    box(tmp, (0, 0, 0), (w, t, r1 - r0), mat=mat)
    R = Matrix((s, Vector((0, 1, 0)), d)).transposed().to_4x4()
    bmesh.ops.transform(tmp, matrix=Matrix.Translation(c) @ R, verts=tmp.verts)
    join_bm(bm, tmp)


# ------------------------------------------------------------------ panel frame ring, sub-panels with holes, seam backing
bm = bmesh.new()
fwd_in = lambda p: Vector((0, 1, 0))
PHW6 = 0.655
panel2d(bm, rrect(-PHW6, PHW6, LY.PANEL_Z[0], LY.PANEL_Z[1] + 0.006, 0.02), [rrect(-0.630, 0.630, 1.467, 2.016, 0.004)],
        lambda u, v, d: Vector((u, PY6 - 0.025 + d, v)), fwd_in, depth=0.022, cham=0.010, mat=MI['src_CP_Panel'],
        grid=0.08)                                   # v6: no closed back (it would cut through the map case)
CHAM = 0.0015
HOLES = {k: [] for k in P6.SUBPANELS}


def sp_of(x):
    for k, (xl, xr, zb, zt) in P6.SUBPANELS.items():
        if xr <= x <= xl:
            return k
    raise ValueError(x)


for name, (gx, gz, D, cell, needles) in P6.GAUGES.items():
    HOLES[sp_of(gx)].append(circle_pts(gx, gz, D / 2 - CHAM, 40 if D >= P6.D6 else 32))
A = P6.ANN
HOLES['SP_C'].append(rect_pts(A['xl'] - CHAM, A['xr'] + CHAM, A['zb'] + CHAM, A['zt'] - CHAM))
RZT, RZB = max(v[0] for v in P6.RADIOS.values()), min(v[1] for v in P6.RADIOS.values())
HOLES['SP_C'].append(rect_pts(P6.RADIO_X[0] - CHAM, P6.RADIO_X[1] + CHAM, RZB + CHAM, RZT - CHAM))
GB = P6.GLOVE
HOLES['SP_R'].append(rect_pts(GB['xl'] - CHAM, GB['xr'] + CHAM, GB['zb'] + CHAM, GB['zt'] - CHAM))
for k, (xl, xr, zb, zt) in P6.SUBPANELS.items():
    panel2d(bm, rrect(xr, xl, zb, zt, 0.008), HOLES[k], lambda u, v, d: Vector((u, PY6 - P6.SP_T + d, v)), fwd_in,
            depth=P6.SP_T, cham=CHAM, mat=MI['src_CP_Panel'], grid=0.05, step=0.03)
rbox(bm, (0.0, PY6 - 0.12, LY.PANEL_Z[0] - 0.008), (2 * PHW6 - 0.02, 0.19, 0.014), MI['src_CP_Panel'], bevel=0.004,
     segs=1)
mk('CP_PanelFrame', bm)
bm = bmesh.new()                                         # dark backing behind the sub-panel seams and the radio rack
for xa, xb in ((0.046, 0.030), (-0.190, -0.206)):
    rect_uv(bm, xa, xb, 1.452, 2.030, PY6 - 0.012, MI['src_CP_Black'], 0, 1, 0, 1)
rect_uv(bm, P6.RADIO_X[0] + 0.002, P6.RADIO_X[1] - 0.002, RZB - 0.002, RZT + 0.002, PY6 - 0.032, MI['src_CP_Black'],
        0, 1, 0, 1)
mk('CP_PanelBack', bm)

# ------------------------------------------------------------------ instruments: bezel lip + bore, dial, glass; knobs, screws
bm = bmesh.new()
bmP = bmesh.new()                                         # CP_Panel: screws, knobs, plates, breakers, labels
FY = PY6 + P6.FACE_DY
for name, (gx, gz, D, cell, needles) in P6.GAUGES.items():
    R = D / 2
    Rd = R - P6.BEZEL_W[D]
    segs = 40 if D >= P6.D6 else 32
    revolve(bm, [(PY6 - 0.0032, R + 0.0015), (PY6 - 0.0032, Rd + 0.0016), (PY6 - 0.0036, Rd + 0.0006),
                 (PY6 - 0.0046, Rd), (FY, Rd)], 'Y', (gx, 0, gz), segs=segs, mat=MI['src_CP_Black'])
    if name == 'ATT':
        annulus(bm, (gx, gz), 0.024, Rd, FY + 0.004, segs=segs, mat=G_MAT, uv_cell=cell)
        box(bm, (gx, FY + 0.006, gz), (0.034, 0.002, 0.003), mat=MI['src_CP_Orange'])
        box(bm, (gx, FY + 0.006, gz - 0.004), (0.004, 0.002, 0.008), mat=MI['src_CP_Orange'])
        disc(bm, (gx, gz), Rd, FY - 0.001, segs=segs, mat=MI['src_CP_Black'])
    elif name == 'HDG':
        box(bm, (gx, FY + 0.006, gz + Rd * 0.84), (0.002, 0.002, 0.009), mat=MI['src_CP_Orange'])
        box(bm, (gx, FY + 0.006, gz), (0.025, 0.002, 0.003), mat=MI['src_CP_Orange'])
        box(bm, (gx, FY + 0.006, gz - 0.002), (0.003, 0.002, 0.019), mat=MI['src_CP_Orange'])
        disc(bm, (gx, gz), Rd, FY - 0.001, segs=segs, mat=MI['src_CP_Black'])
    elif name == 'ALT':                                  # v7: Kollsman window cut out of the dial
        disc_with_hole(bm, (gx, gz), Rd, FY, segs, G_MAT, cell, P6.BARO_WIN)
        w_ = P6.BARO_WIN                                     # window well: dark sides between dial and disc
        box_sides(bm, gx - w_['x0'] * Rd, gx - w_['x1'] * Rd, gz + w_['z0'] * Rd, gz + w_['z1'] * Rd, FY - 0.0006,
                  FY, MI['src_CP_Black'])
    else:
        disc(bm, (gx, gz), Rd, FY, segs=segs, mat=G_MAT, uv_cell=cell, uv_scale=1.0)
    disc(bm, (gx, gz), Rd + 0.0004, PY6 + P6.GLASS_DY, segs=24, mat=MI['src_CP_GaugeGlass'])
    q = 0.0415 if D >= P6.D6 else 0.0305
    for sx in (-q, q):
        for sz in (-q, q):
            screw(bmP, gx + sx, gz + sz, PY6)
    for ang in P6.GAUGE_KNOBS.get(name, []):
        a = math.radians(ang)
        rk, kr = (R + 0.006, 0.0065) if D >= P6.D6 else (R + 0.0045, 0.005)
        kx, kz = gx - math.sin(a) * rk, gz + math.cos(a) * rk
        rig_name = P6.GAUGE_KNOB_RIG.get((name, ang))
        if rig_name:                                      # v7 (M3): own part, turns about its axis
            bmk = bmesh.new()
            knurled(bmk, kx, kz, PY6, kr, 0.012, MI['src_CP_Black'])
            radial_bar(bmk, kx, kz, PY6 + 0.012, 0.0012, kr - 0.0008, 0.0, 0.0012, MI['src_CP_Needle'])
            mk(rig_name, bmk, (kx, PY6, kz), axis='gauge', note='instrument knob: free rotation about its axis')
        else:
            knurled(bmP, kx, kz, PY6, kr, 0.012, MI['src_CP_Black'])
mk('CP_Gauges', bm, smooth=60)
# v7: pressure-setting disc behind the Kollsman window (ALT dial) and heading bug on the DG card
gx, gz = P6.GAUGES['ALT'][:2]
Rd_alt = P6.GAUGES['ALT'][2] / 2 - P6.BEZEL_W[P6.GAUGES['ALT'][2]]
bm = bmesh.new()
disc(bm, (gx, gz), P6.BARO_DISC_R * Rd_alt, FY - 0.0008, segs=48, mat=G_MAT, uv_cell=P6.BARO_CELL)
mk('ALT_Baro', bm, (gx, FY - 0.0008, gz), axis='gauge',
   note='Kollsman scale disc: rest = 29.92 inHg under the index; clockwise (negative local Z) for higher settings, '
        f'{P6.BARO_DEG_PER_INHG:.0f} deg per inHg')

for name, (gx, gz, D, cell, needles) in P6.GAUGES.items():
    Rd = D / 2 - P6.BEZEL_W[D]
    k = (D / 0.086) ** 0.5
    piv = (gx, FY + 0.003, gz)
    for bone, frac, kind in needles:
        bm = bmesh.new()
        if kind in ('needle', 'needle_short'):
            ang = P6.NEEDLE_REST.get(bone, 0.0)
            w = 0.0035 if kind == 'needle' else 0.005
            needle_mesh(bm, gx, gz, FY + 0.003, Rd * frac, ang, w * k, MI['src_CP_Needle'])
            mk(bone, bm, piv, axis='gauge', note=f'needle rest {ang:.0f} deg clockwise from 12 (pilot view)')
        elif kind == 'rollcard':
            bm2 = bmesh.new()
            disc(bm2, (gx, gz), 0.036, FY + 0.001, segs=40, mat=G_MAT, uv_cell=P6.ATT_CARD_CELL)
            mk('ATT_Pitch', bm2, piv, parent='ATT_Roll', axis='translate_up', note='card offset')
            bm.free()
            e = bpy.data.objects.new('ATT_Roll', None)
            e.empty_display_size = 0.02
            CP.objects.link(e)
            e.location = piv
            RIG['ATT_Roll'] = dict(pivot=list(piv), parent='Cockpit', axis='gauge', note='bank (empty transform)')
        elif kind == 'card':
            disc(bm, (gx, gz), Rd - 0.001, FY + 0.002, segs=40, mat=G_MAT, uv_cell=cell)
            mk(bone, bm, piv, axis='gauge', note='heading card')
            bmb = bmesh.new()                                # v7: heading bug (child of the card)
            bw, r0b, r1b = 0.0055, 0.905 * Rd, 0.985 * Rd
            yb = FY + 0.0027
            pts = [(gx + bw / 2, r1b), (gx + bw / 2, r0b), (gx + bw * 0.18, r0b + 0.0022), (gx - bw * 0.18, r0b + 0.0022),
                   (gx - bw / 2, r0b), (gx - bw / 2, r1b)]
            outline = [Vector((px, yb, gz + pz)) for px, pz in pts]
            loft(bmb, [[v + Vector((0, -0.0003, 0)) for v in outline], [v + Vector((0, 0.0003, 0)) for v in outline]],
                 True, True, True, mat=MI['src_CP_Orange'])
            mk('HDG_Bug', bmb, piv, parent='HDG_Card', axis='gauge',
               note='heading bug, child of HDG_Card: rest = card heading 0; clockwise (negative local Z) = bug heading')
        elif kind == 'plane':
            box(bm, (gx, FY + 0.004, gz), (Rd * 1.5, 0.002, 0.004), mat=MI['src_CP_Needle'])
            box(bm, (gx, FY + 0.004, gz + 0.004), (0.005, 0.002, 0.010), mat=MI['src_CP_Needle'])
            cylinder(bm, (gx, FY + 0.004, gz), (gx, FY + 0.006, gz), 0.006, 0.006, 12, mat=MI['src_CP_Needle'])
            mk(bone, bm, piv, axis='gauge', note='turn rate')
        elif kind == 'ball':                     # inclinometer tube drawn in cell 4: centre 0.76 Rd up, radius 1.24 Rd
            bz = gz - 0.48 * Rd
            revolve(bm, [(FY + 0.001, 0.0), (FY + 0.002, 0.0032), (FY + 0.004, 0.004), (FY + 0.006, 0.0032),
                         (FY + 0.007, 0.0)], 'Y', (gx, 0, bz), segs=12, mat=MI['src_CP_Black'])
            mk(bone, bm, (gx, FY + 0.003, gz + 0.76 * Rd), axis='gauge', note='slip ball (pivot = tube arc centre)')
# Hobbs LCD window (display quad, UV 0..1) just above its dial
hx, hz, hD = P6.GAUGES['HOBBS'][:3]
hw = P6.HOBBS_WIN
bm = bmesh.new()
rect_uv(bm, hx + hw['dx'] + hw['w'] / 2, hx + hw['dx'] - hw['w'] / 2, hz + hw['dz'] - hw['h'] / 2,
        hz + hw['dz'] + hw['h'] / 2, FY + 0.0003, MI['src_CP_Screen'], 0.0, 1.0, 0.0, 1.0)
DISPLAYS = {'Display_Hobbs': (hx + hw['dx'], FY + 0.0003, hz + hw['dz'], hw['w'], hw['h'], 'Hobbs')}
mk('Display_Hobbs', bm)

# ------------------------------------------------------------------ annunciator: bezel with 12 lens windows, lamp quads, test button
A = P6.ANN
AW_, AH_ = (A['xl'] - A['xr']) * 1000, (A['zt'] - A['zb']) * 1000
ann_holes = []
for i in range(len(P6.ANN_LAMPS)):
    s0, t0, s1, t1 = P6.ann_lens(i)
    ann_holes.append(rect_pts(A['xl'] - s0 / 1000 - 0.0006, A['xl'] - s1 / 1000 + 0.0006, A['zt'] - t1 / 1000 + 0.0006,
                              A['zt'] - t0 / 1000 - 0.0006))
panel2d(bmP, rrect(A['xr'] - 0.002, A['xl'] + 0.002, A['zb'] - 0.002, A['zt'] + 0.002, 0.0015), ann_holes,
        lambda u, v, d: Vector((u, PY6 - 0.0015 + d, v)), fwd_in, depth=0.0035, cham=0.0006, mat=MI['src_CP_Black'],
        grid=0.03, step=0.02)
bm = bmesh.new()
uv0 = bm.loops.layers.uv.new('UVMap')
uv1 = bm.loops.layers.uv.new('LampUV')
pl = plate_layer(bm)
yl = PY6 - 0.0012
for i in range(len(P6.ANN_LAMPS)):
    s0, t0, s1, t1 = P6.ann_lens(i)
    x0, x1 = A['xl'] - s0 / 1000, A['xl'] - s1 / 1000
    z1, z0 = A['zt'] - t0 / 1000, A['zt'] - t1 / 1000
    u0, v1 = P6.region_uv(PR['ANN'], s0, t0)
    u1, v0 = P6.region_uv(PR['ANN'], s1, t1)
    vs = [bm.verts.new(p) for p in ((x0, yl, z0), (x1, yl, z0), (x1, yl, z1), (x0, yl, z1))]
    f = bm.faces.new(vs)
    f.material_index = MI['src_CP_Annun']
    f[pl] = 1
    for lp, uv in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
        lp[uv0].uv = uv
        lp[uv1].uv = (i + 0.5, 0.5)
mk('CP_Annunciator', bm)
tbx, tbz = P6.ANN_TEST_BTN
revolve(bmP, [(PY6, 0.0068), (PY6 + 0.0018, 0.0068), (PY6 + 0.0024, 0.006), (PY6 + 0.0024, 0.0053), (PY6, 0.0053)],
        'Y', (tbx, 0, tbz), segs=20, mat=MI['src_CP_Chrome'])
bm = bmesh.new()
revolve(bm, [(PY6 - 0.004, 0.0), (PY6 - 0.004, 0.0048), (PY6 + 0.0065, 0.0048), (PY6 + 0.0075, 0.0042),
             (PY6 + 0.0078, 0.0)], 'Y', (tbx, 0, tbz), segs=16, mat=MI['src_CP_KnobRed'])
mk('Btn_AnnunTest', bm, (tbx, PY6, tbz), axis='translate_fwd',
   note='push-to-test: pressed = 3 mm forward into the panel, all lamps on')

# ------------------------------------------------------------------ radio stack: bodies, face art, caps, knobs, display quads
bmR, bmF = bmesh.new(), bmesh.new()
X0, X1 = P6.RADIO_X
yF = PY6 + P6.RADIO_FACE_DY
for u, (zt, zb) in P6.RADIOS.items():
    spec = P6.RADIO_FACE[u]
    box_sides(bmR, X0, X1, zb, zt, PY6 + P6.RADIO_BODY_DY, yF, MI['src_CP_Black'])
    art_rect(bmF, 'R_' + u, X0, X1, zb, zt, yF)
    wx = lambda s: X0 - s / 1000.0
    wz = lambda t: zt - t / 1000.0
    for s0, t0, s1, t1, txt in spec['caps']:
        box_sides(bmR, wx(s0), wx(s1), wz(t1), wz(t0), yF, yF + P6.CAP_H, MI['src_CP_Black'])
        art_rect(bmF, 'R_' + u, wx(s0), wx(s1), wz(t1), wz(t0), yF + P6.CAP_H, s0, t0, s1, t1)
    for (s, t, od, idd, kind), names in zip(spec['knobs'], P6.RADIO_KNOB_NAMES[u]):      # v7 (M7): rig parts
        piv = (wx(s), yF, wz(t))
        if kind == 'conc':
            bmk = bmesh.new()
            knurled(bmk, wx(s), wz(t), yF, od / 2000, 0.0075, MI['src_CP_Black'], ridges=20)
            mk(names[0], bmk, piv, axis='gauge', note='outer concentric knob (coarse): free rotation')
            bmk = bmesh.new()
            knurled(bmk, wx(s), wz(t), yF + 0.0075, idd / 2000, 0.0085, MI['src_CP_Black'], ridges=14)
            mk(names[1], bmk, piv, axis='gauge', note='inner concentric knob (fine): free rotation; push/pull = OPEN')
        elif kind == 'pointer':
            bmk = bmesh.new()
            knurled(bmk, wx(s), wz(t), yF, od / 2000, 0.009, MI['src_CP_Black'], ridges=12)
            radial_bar(bmk, wx(s), wz(t), yF + 0.009, 0.0015, od / 2000 - 0.0008, P6.XPDR_MODES[0][1], 0.0014,
                       MI['src_CP_Needle'])
            mk(names[0], bmk, piv, axis='gauge', note='mode selector: rest OFF; detents ' +
               ', '.join(f'{m} {a - P6.XPDR_MODES[0][1]:+.0f}' for m, a in P6.XPDR_MODES) + ' deg clockwise')
        else:
            bmk = bmesh.new()
            knurled(bmk, wx(s), wz(t), yF, od / 2000, 0.008, MI['src_CP_Black'], ridges=14)
            radial_bar(bmk, wx(s), wz(t), yF + 0.008, 0.0012, od / 2000 - 0.0008, -135.0, 0.0011, MI['src_CP_Needle'])
            mk(names[0], bmk, piv, axis='gauge', note='knob: rest index at 7:30 (OFF / minimum), clockwise = up')
    for nm, (s0, t0, s1, t1) in spec['windows'].items():
        bm = bmesh.new()
        rect_uv(bm, wx(s0), wx(s1), wz(t1), wz(t0), yF + 0.0003, MI['src_CP_Screen'], 0.0, 1.0, 0.0, 1.0)
        DISPLAYS[nm] = ((wx(s0) + wx(s1)) / 2, yF + 0.0003, (wz(t0) + wz(t1)) / 2, (s1 - s0) / 1000, (t1 - t0) / 1000, u)
        mk(nm, bm)
for xa in (X0 + 0.0025, X1 - 0.0025):                     # rack rails either side of the stack
    rbox(bmR, (xa, PY6 + 0.0005, (RZT + RZB) / 2), (0.003, 0.003, RZT - RZB + 0.004), MI['src_CP_Metal'], bevel=0.0006,
         segs=1)
mk('CP_Radios', bmR)
mk('CP_RadioFaces', bmF)

# ------------------------------------------------------------------ circuit breaker lightplate
xl, xr, zb, zt = P6.CB_PLATE
lightplate(bmP, 'CB', xl, xr, zb, zt, PY6, 0.003)
yP = PY6 + 0.003
for s, t in ((4.5, 4.5), ((xl - xr) * 1000 - 4.5, 4.5), (4.5, (zt - zb) * 1000 - 4.5),
             ((xl - xr) * 1000 - 4.5, (zt - zb) * 1000 - 4.5)):
    screw(bmP, xl - s / 1000, zt - t / 1000, yP, r=0.0019)
uvf = plate_uv_fn('CB', xl, zt)
for z in P6.CB_ROWS:
    for x in P6.CB_COLS:
        revolve(bmP, [(yP, P6.CB_COLLAR_R), (yP + 0.0024, P6.CB_COLLAR_R), (yP + 0.003, P6.CB_COLLAR_R - 0.0008),
                      (yP + 0.003, P6.CB_CAP_R + 0.0004), (yP, P6.CB_CAP_R + 0.0004)], 'Y', (x, 0, z), segs=6,
                mat=MI['src_CP_Metal'], phase=math.pi / 6)
        cylinder(bmP, (x, yP + 0.002, z), (x, yP + 0.0105, z), P6.CB_CAP_R, P6.CB_CAP_R, 16, mat=MI['src_CP_Black'],
                 caps=False)
        cap_disc(bmP, x, z, P6.CB_CAP_R, yP + 0.0105, uvf)

# ------------------------------------------------------------------ switch lightplate: toggles with nut + locking ring, starter guard, rheostats
xl, xr, zb, zt = P6.SW_PLATE
lightplate(bmP, 'SW', xl, xr, zb, zt, PY6, 0.003)
for s, t in ((5, 5), ((xl - xr) * 1000 - 5, 5), (5, (zt - zb) * 1000 - 5), ((xl - xr) * 1000 - 5, (zt - zb) * 1000 - 5)):
    screw(bmP, xl - s / 1000, zt - t / 1000, yP, r=0.0021)
bmS = bmesh.new()
for bone, (x, z, lab, on, off) in P6.SWITCHES.items():
    cylinder(bmS, (x, yP, z), (x, yP + 0.0007, z), 0.0074, 0.0074, 16, mat=MI['src_CP_Metal'])        # locking ring
    revolve(bmS, [(yP + 0.0007, 0.0063), (yP + 0.0028, 0.0063), (yP + 0.0031, 0.0055), (yP + 0.0031, 0.0)], 'Y',
            (x, 0, z), segs=6, mat=MI['src_CP_Chrome'], phase=math.pi / 6)                                # hex nut
    cylinder(bmS, (x, yP + 0.0031, z), (x, yP + 0.0055, z), 0.0041, 0.0041, 12, mat=MI['src_CP_Chrome'])  # bushing
    bm = bmesh.new()
    piv = Vector((x, yP + 0.0055, z))
    tip = Vector((x, yP + 0.0235, z - 0.007))
    cylinder(bm, piv, tip, 0.0026, 0.0019, 10, mat=MI['src_CP_Chrome'])
    revolve(bm, [(-0.0035, 0.0), (-0.003, 0.0025), (0.0, 0.0036), (0.003, 0.0025), (0.0035, 0.0)], 'Y', tuple(tip),
            segs=12, mat=MI['src_CP_Chrome'])
    note = 'toggle: rest OFF (down), ON = lever up 40 deg'
    if bone.startswith(('SW_CargoDoor', 'SW_CabinDoor')):
        note = 'toggle: rest CLOSE (down), OPEN = lever up 40 deg'
    if bone == 'SW_Starter':
        note = 'momentary toggle under the flip guard: rest OFF (down), START = lever up 40 deg'
    mk(bone, bm, tuple(piv), axis='lateral', note=note)
# starter guard: red U-channel hinged above the switch (hinge bracket static)
sx, sz = P6.SWITCHES['SW_Starter'][:2]
G = P6.STARTER_GUARD
hz = sz + G['hinge_dz']
hy = yP + 0.005
rbox(bmS, (sx, yP + 0.0015, hz + 0.0015), (G['w'] + 0.006, 0.003, 0.009), MI['src_CP_Black'], bevel=0.0008, segs=1)
cylinder(bmS, (sx - G['w'] / 2 - 0.0025, hy, hz), (sx + G['w'] / 2 + 0.0025, hy, hz), 0.0022, 0.0022, 10,
         mat=MI['src_CP_Metal'])
bm = bmesh.new()
t_ = 0.0015
y_front = yP + G['d']
zb_g = hz - G['h']
for sgn in (-1, 1):                                       # side walls
    box(bm, (sx + sgn * (G['w'] / 2 - t_ / 2), (yP + 0.001 + y_front) / 2, (hz + zb_g) / 2),
        (t_, y_front - yP - 0.001, G['h']), mat=MI['src_CP_KnobRed'])
box(bm, (sx, y_front - t_ / 2, (hz + zb_g) / 2), (G['w'], t_, G['h']), mat=MI['src_CP_KnobRed'])          # front
box(bm, (sx, (hy + y_front) / 2, hz - t_ / 2 + 0.001), (G['w'], y_front - hy, t_), mat=MI['src_CP_KnobRed'])  # top
cylinder(bm, (sx - G['w'] / 2 + 0.002, hy, hz), (sx + G['w'] / 2 - 0.002, hy, hz), 0.0028, 0.0028, 10,
         mat=MI['src_CP_KnobRed'])                                                                       # knuckle
box(bm, (sx, y_front + 0.0006, zb_g + 0.004), (0.010, 0.0012, 0.004), mat=MI['src_CP_KnobRed'])           # lift tab
mk('Guard_Starter', bm, (sx, hy, hz), axis='lateral',
   note='flip guard over SW_Starter: rest closed; open = +95 deg about local X (free edge swings up, towards the pilot)')
mk('CP_Switchgear', bmS)
for bone, (x, z, lab) in P6.RHEOSTATS.items():
    bm = bmesh.new()
    knurled(bm, x, z, yP, 0.011, 0.014, MI['src_CP_Black'], ridges=20)
    radial_bar(bm, x, z, yP + 0.014, 0.0025, 0.0088, -135.0, 0.0015, MI['src_CP_Needle'])
    mk(bone, bm, (x, yP, z), axis='gauge', note='rheostat: rest OFF (index at 7:30), 0..270 deg clockwise to BRT')

# ------------------------------------------------------------------ pull knobs + bezels, label plates, headset jacks, placards
for bone, (px, pz, kind) in P6.PULLS.items():
    bm = bmesh.new()
    cylinder(bm, (px, PY6 - 0.01, pz), (px, PY6 + 0.012, pz), 0.004, 0.004, 10, mat=MI['src_CP_Chrome'])
    if kind == 'tee':
        box(bm, (px, PY6 + 0.018, pz), (0.050, 0.014, 0.016), mat=MI['src_CP_Black'], bevel=0.005, bevel_segs=2)
    else:
        knurled(bm, px, pz, PY6 + 0.012, 0.012, 0.012, MI['src_CP_Black'], ridges=20)
    mk(bone, bm, (px, PY6, pz), axis='translate_aft', note='pull towards the pilot, 0..6 cm')
    bm = bmesh.new()
    cylinder(bm, (px, PY6 - 0.001, pz), (px, PY6 + 0.003, pz), 0.009, 0.008, 16, mat=MI['src_CP_Chrome'])
    mk(f'CP_{bone}_Bezel', bm)
for k, (xl, xr, zb, zt, txt) in P6.LABELS.items():
    lightplate(bmP, k, xl, xr, zb, zt, PY6, 0.0012)
for side, (xl, xr, zb, zt) in P6.JACKS.items():
    lightplate(bmP, 'JACKS', xl, xr, zb, zt, PY6, 0.0015)
    for s, t, txt in P6.JACK_POS:
        jx, jz = xl - s / 1000, zt - t / 1000
        revolve(bmP, [(PY6 + 0.0015, 0.0047), (PY6 + 0.0032, 0.0047), (PY6 + 0.0036, 0.0040), (PY6 + 0.0036, 0.0031),
                      (PY6 + 0.0016, 0.0031)], 'Y', (jx, 0, jz), segs=16, mat=MI['src_CP_Chrome'])
for k, (xl, xr, zb, zt) in P6.PLACARDS.items():
    lightplate(bmP, k, xl, xr, zb, zt, PY6, 0.0008)
mk('CP_Panel', bmP)

# ------------------------------------------------------------------ map case (glovebox): trim ring, lined box, contents; lid = rig part
GB = P6.GLOVE
gxl, gxr, gzb, gzt = GB['xl'], GB['xr'], GB['zb'], GB['zt']
yb = PY6 - GB['depth']
bm = bmesh.new()
for (x0, x1, z0, z1) in ((gxl + 0.006, gxr - 0.006, gzt, gzt + 0.006), (gxl + 0.006, gxr - 0.006, gzb - 0.006, gzb),
                         (gxl + 0.006, gxl, gzb, gzt), (gxr, gxr - 0.006, gzb, gzt)):
    rbox(bm, ((x0 + x1) / 2, PY6 + 0.0008, (z0 + z1) / 2), (abs(x0 - x1), 0.0016, abs(z1 - z0)), MI['src_CP_Black'],
         bevel=0.0005, segs=1)
pl = plate_layer(bm)
inner = [((gxl, PY6 - 0.003, gzb), (gxr, PY6 - 0.003, gzb), (gxr, yb, gzb), (gxl, yb, gzb)),          # floor
         ((gxl, yb, gzt), (gxr, yb, gzt), (gxr, PY6 - 0.003, gzt), (gxl, PY6 - 0.003, gzt)),          # ceiling
         ((gxl, yb, gzb), (gxr, yb, gzb), (gxr, yb, gzt), (gxl, yb, gzt)),                          # back wall
         ((gxl, PY6 - 0.003, gzb), (gxl, yb, gzb), (gxl, yb, gzt), (gxl, PY6 - 0.003, gzt)),          # left
         ((gxr, yb, gzb), (gxr, PY6 - 0.003, gzb), (gxr, PY6 - 0.003, gzt), (gxr, yb, gzt))]          # right
centre = Vector(((gxl + gxr) / 2, (PY6 + yb) / 2, (gzb + gzt) / 2))
for quad in inner:
    f = bm.faces.new([bm.verts.new(p) for p in quad])
    f.material_index = MI['src_CP_Trim']
    orient(f, centre - f.calc_center_median(), bm)
# contents: POH binder (flat, right), folded chart (left), flashlight on the chart
pohx0, pohx1, pohy0, pohy1 = -0.385, -0.595, PY6 - 0.185, PY6 - 0.035
rbox(bm, ((pohx0 + pohx1) / 2, (pohy0 + pohy1) / 2, gzb + 0.012), (0.210, 0.150, 0.022), MI['src_CP_Leather'],
     bevel=0.003, segs=2)
uvl = bm.loops.layers.uv.verify()
reg = PR['POH']
corners = [(pohx0 - 0.004, pohy1 - 0.004), (pohx0 - 0.004, pohy0 + 0.004), (pohx1 + 0.004, pohy0 + 0.004),
           (pohx1 + 0.004, pohy1 - 0.004)]
# cover lies sideways: region top edge (t = 0) along the inboard edge (x0), region s along -y (towards the nose)
st = [(0.0, 0.0), (150.0, 0.0), (150.0, 210.0), (0.0, 210.0)]
f = bm.faces.new([bm.verts.new((x, y, gzb + 0.0231)) for x, y in corners])
f.material_index = G_MAT
f[pl] = 2
for lp, (s, t) in zip(f.loops, st):
    lp[uvl].uv = P6.region_uv(reg, s, t)
f.normal_update()
if f.normal.z < 0:
    f.normal_flip()
mx0, mx1, my0, my1 = -0.245, -0.378, PY6 - 0.180, PY6 - 0.040          # chart folded to 133 x 140 mm (one panel shown)
reg = PR['MAP']
zf = gzb + 0.0015
pts = [(mx0, my1, zf), (mx1, my1, zf), (mx1, my0, zf + 0.004), (mx0, my0, zf + 0.004)]
f = bm.faces.new([bm.verts.new(p) for p in pts])
f.material_index = G_MAT
f[pl] = 2
for lp, (s, t) in zip(f.loops, ((80.0, 140.0), (213.0, 140.0), (213.0, 0.0), (80.0, 0.0))):
    lp[uvl].uv = P6.region_uv(reg, s, t)
f.normal_update()
if f.normal.z < 0:
    f.normal_flip()
fa, fb_ = Vector((-0.268, PY6 - 0.070, gzb + 0.0175)), Vector((-0.352, PY6 - 0.135, gzb + 0.0175))
cylinder(bm, fa, fb_, 0.0125, 0.0125, 14, mat=MI['src_CP_Black'])
cylinder(bm, fa, fa + (fa - fb_).normalized() * 0.010, 0.0125, 0.0145, 14, mat=MI['src_CP_Chrome'])
disc_c = fa + (fa - fb_).normalized() * 0.0102
cylinder(bm, disc_c, disc_c + (fa - fb_).normalized() * 0.0005, 0.013, 0.013, 14, mat=MI['src_CP_Lens'])
mk('CP_Glovebox', bm)
bm = bmesh.new()
g = GB['lid_gap']
lxl, lxr, lzb, lzt = gxl - g, gxr + g, gzb + g, gzt - g
box(bm, ((lxl + lxr) / 2, PY6 + 0.001 - GB['lid_t'] / 2, (lzb + lzt) / 2), (lxl - lxr, GB['lid_t'], lzt - lzb),
    mat=MI['src_CP_Panel'], bevel=0.0025, bevel_segs=2)
for f in bm.faces:
    f.normal_update()
    f.material_index = MI['src_CP_Panel'] if f.normal.y > 0.9 else (MI['src_CP_Trim'] if f.normal.y < -0.9 else
                                                                     MI['src_CP_Black'])
lx_, lz_ = P6.GLOVE_LATCH
revolve(bm, [(PY6 + 0.001, 0.0085), (PY6 + 0.0022, 0.0085), (PY6 + 0.0028, 0.0078), (PY6 + 0.0028, 0.0060),
             (PY6 + 0.001, 0.0060)], 'Y', (lx_, 0, lz_), segs=20, mat=MI['src_CP_Chrome'])
revolve(bm, [(PY6 + 0.001, 0.0), (PY6 + 0.001, 0.0058), (PY6 + 0.0045, 0.0058), (PY6 + 0.005, 0.005),
             (PY6 + 0.005, 0.0)], 'Y', (lx_, 0, lz_), segs=16, mat=MI['src_CP_Black'])
pxl, pxr, pzb, pzt = P6.GLOVE_PLACARD
art_rect(bm, 'MAPCASE', pxl, pxr, pzb, pzt, PY6 + 0.0013)
mk('Glovebox_Lid', bm, ((lxl + lxr) / 2, PY6 + 0.001, lzb), axis='lateral',
   note='map case lid, hinge on its bottom edge: rest closed; open = -80 deg about local X (top edge comes towards '
        'the pilot and down)')

# display quads: centre, size and unit for export (Blender build frame)
DISPLAYS_JSON = {k: dict(centre=[round(c, 5) for c in v[:3]], size=[round(v[3], 4), round(v[4], 4)], unit=v[5])
                 for k, v in DISPLAYS.items()}
json.dump(DISPLAYS_JSON, open(os.path.join(HERE, 'out', 'displays_v7.json'), 'w'), indent=1)
print('panel v7: displays', sorted(DISPLAYS))
