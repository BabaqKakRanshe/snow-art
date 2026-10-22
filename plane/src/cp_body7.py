
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


# (v6: the instrument panel is built by cp_panel6.py after cp_shell.py)

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
# v7: housing open at the front behind a bezel with a window; the card is a drum (rig part Compass_Card, vertical
# axis) printed like a wet compass; lubber line and glass in the window
import panel7 as P7
bm = bmesh.new()
CZ = -0.03                     # v5: compass hangs 30 mm lower, clear of the inner skin and the windshield frame
CP7 = P7.COMPASS
ccx, ccy, ccz = CP7['cx'], CP7['cy'], CP7['cz']
by0, by1 = CP7['bezel_y']
cylinder(bm, (0, -2.64, 2.60), (0, -2.66, 2.575 + CZ), 0.006, 0.006, 8, mat=MI['src_CP_Black'])
bw_, bd_, bh_ = CP7['box']
hv = box(bm, (ccx, by0 - bd_ / 2, ccz), (bw_, bd_, bh_), mat=MI['src_CP_Black'])
_front = [f for f in {f for v in hv for f in v.link_faces} if all(abs(v.co.y - by0) < 1e-5 for v in f.verts)]
bmesh.ops.delete(bm, geom=_front, context='FACES_ONLY')
ww, wh = CP7['win_w'] / 2, CP7['win_h'] / 2
for (x0, x1, z0, z1) in ((ww, bw_ / 2, -bh_ / 2, bh_ / 2), (-bw_ / 2, -ww, -bh_ / 2, bh_ / 2),
                         (-ww, ww, wh, bh_ / 2), (-ww, ww, -bh_ / 2, -wh)):          # bezel bars around the window
    rbox(bm, (ccx + (x0 + x1) / 2, (by0 + by1) / 2, ccz + (z0 + z1) / 2), (x1 - x0, by1 - by0, z1 - z0),
         MI['src_CP_Black'], bevel=0.0006, segs=1)
box(bm, (ccx, by0 + 0.0012, ccz), (0.0012, 0.0008, CP7['h'] * 0.7), mat=MI['src_CP_Orange'])     # lubber line
rect_uv(bm, ccx + ww, ccx - ww, ccz - wh, ccz + wh, by1 - 0.0004, MI['src_CP_GaugeGlass'], 0, 1, 0, 1)
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
# v7 compass card drum (strip region COMPASS: u = (360 - beta) / 360, beta clockwise from the nose seen from above)
_reg = json.load(open(P7.ATLAS_JSON))['regions']['COMPASS']
bm = bmesh.new()
uvl, pl = bm.loops.layers.uv.verify(), plate_layer(bm)
NC_, r_, h_ = 72, CP7['r'], CP7['h']
P_ = lambda beta, z: Vector((ccx - r_ * math.sin(math.radians(beta)), ccy - r_ * math.cos(math.radians(beta)), z))
top, bot = ccz + h_ / 2, ccz - h_ / 2
Wmm, Hmm = _reg['size_mm']
for i in range(NC_):
    b0, b1 = 360.0 * i / NC_, 360.0 * (i + 1) / NC_
    vs = [bm.verts.new(P_(b0, bot)), bm.verts.new(P_(b1, bot)), bm.verts.new(P_(b1, top)), bm.verts.new(P_(b0, top))]
    f = bm.faces.new(vs)
    f.material_index = MI['src_CP_Gauges']
    f[pl] = 2
    for lp, (bb, tt) in zip(f.loops, ((b0, Hmm), (b1, Hmm), (b1, 0.0), (b0, 0.0))):
        lp[uvl].uv = P7.region_uv(_reg, (360.0 - bb) / 360.0 * Wmm, tt)
    f.normal_update()
    if f.normal.dot(f.calc_center_median() - Vector((ccx, ccy, f.calc_center_median().z))) < 0:
        f.normal_flip()
for z, sgn in ((top, 1), (bot, -1)):                      # dark caps
    c = bm.verts.new((ccx, ccy, z))
    ring = [bm.verts.new(P_(360.0 * i / NC_, z)) for i in range(NC_)]
    for i in range(NC_):
        f = bm.faces.new((c, ring[i], ring[(i + 1) % NC_]))
        f.material_index = MI['src_CP_Black']
        f[pl] = 2
        f.normal_update()
        if f.normal.z * sgn < 0:
            f.normal_flip()
mk('Compass_Card', bm, (ccx, ccy, ccz), axis='vertical',
   note='magnetic compass card (drum): rest = heading 000; Unity rotation about local Y = -heading (card stays put, '
        'the aircraft turns round it); wet-compass order: E shows left of N')
