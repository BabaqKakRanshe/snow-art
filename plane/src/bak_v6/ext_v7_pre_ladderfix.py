"""v7 exterior edits on top of the v5/v6 exterior (out/plane_geo_v2.blend -> out/plane_geo_v7.blend).
Only Details-atlas parts change; the Airframe meshes stay byte-identical (their textures are the v4 bake).
 - Propeller: spinner + hub (object Propeller) and three separate blades PropBlade_1..3 (children of Propeller,
   pivot on the hub centre, local Z = blade span: pitch = rotation about the span). Blades now turn the right way
   (clockwise seen from the cockpit, leading edge first, camber forward), 18 stations, round shank, rounded tip.
 - PropBlur / PropDisc: transparent discs in the prop plane (fast-rotation look, alpha driven by the rig).
 - Wheels: tundra tyres with modelled block lugs (same outer radius 0.484 / 0.2856), dished rims, lug nuts,
   split-rim bolts, valve stem, brake disc on the inboard side; calipers added to the gear legs (static).
 - Exhaust stacks: flared PT6-style stacks with an open, thin-walled mouth (src_CowlDetails rebuilt, intake kept).
 - Antennas: swept comm blades with base plates, whips, pitot tube (src_Antennas rebuilt).
 - Lock_PilotDoor_L / _R: key lock cylinders aft of the outer door handles (NEW-05 / M2).
 - src_StepLadder (+ Ladder_RearLegs) and src_PlaneKey: separate props (exported as their own FBX, M5 / M2)."""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import *
import layout as LY

bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_geo_v2.blend'))
O, MAT = bpy.data.objects, bpy.data.materials
C_SRC = bpy.data.collections['Aircraft']
ROOT = O['UtilityPlane']

NEW_MATS = {
    'src_Brake': (0.20, 0.20, 0.20), 'src_Caliper': (0.45, 0.33, 0.10), 'src_Alu': (0.55, 0.56, 0.57),
    'src_LadderTread': (0.02, 0.02, 0.02), 'src_KeyMetal': (0.6, 0.6, 0.58), 'src_KeyFob': (0.75, 0.12, 0.03),
    'src_PropBlur': (0.02, 0.02, 0.02), 'src_PropDisc': (0.02, 0.02, 0.02),
}
M = {m.name: m for m in MAT}
for k, c in NEW_MATS.items():
    m = MAT.get(k) or MAT.new(k)
    m.diffuse_color = (*c, 1)
    M[k] = m


def remove(name):
    ob = O.get(name)
    if ob is None:
        return None, None
    par, kids = ob.parent, list(ob.children)
    me = ob.data
    bpy.data.objects.remove(ob)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)
    return par, kids


def rot_about(v, axis, ang):
    return Matrix.Rotation(ang, 3, axis) @ v


# ================================================================== PROPELLER
P_C = Vector(LY.PROP_C)
FWD = Vector((0, -1, 0))
par, _ = remove('Propeller')
bm = bmesh.new()
prof = []
L, R0, ybase = 0.46, 0.265, -4.61
for i in range(13):
    u = i / 12
    r = R0 * (1 - u ** 1.9) ** 0.72
    prof.append((ybase - u * L, r))
prof = prof[::-1]
prof.append((ybase + 0.0001, R0))
prof.append((ybase + 0.012, R0 - 0.004))                        # back plate edge
prof.append((ybase + 0.014, 0.0))
revolve(bm, prof, 'Y', (0, 0, P_C.z), segs=40, mat=0)
for k in range(12):                                             # spinner screws along the back edge
    a = 2 * math.pi * (k + 0.5) / 12
    d = Vector((math.sin(a), 0, math.cos(a)))
    p = Vector((0, ybase - 0.035, P_C.z)) + d * (R0 * 0.985)
    cylinder(bm, p - d * 0.004, p + d * 0.0025, 0.0045, 0.0045, 8, mat=1)
fix_normals(bm)
prop = obj_from_bm('Propeller', bm, C_SRC, [M['src_Spinner'], M['src_MetalDark']])
shade(prop, 50)
set_pivot(prop, tuple(P_C))
parent_keep(prop, ROOT)

# blade stations: r, chord, blade angle at rest (deg), thickness ratio
STA = [(0.170, 0.070, 62, 1.00), (0.200, 0.075, 60, 0.95), (0.240, 0.090, 56, 0.70), (0.280, 0.130, 52, 0.40),
       (0.340, 0.175, 48, 0.22), (0.420, 0.215, 42, 0.16), (0.520, 0.240, 37, 0.13), (0.640, 0.248, 32, 0.11),
       (0.760, 0.245, 28, 0.095), (0.880, 0.235, 25, 0.085), (0.980, 0.222, 23, 0.080), (1.080, 0.205, 21.5, 0.075),
       (1.160, 0.185, 20, 0.070), (1.220, 0.160, 19, 0.068), (1.270, 0.130, 18.5, 0.066), (1.300, 0.100, 18, 0.065),
       (1.315, 0.065, 18, 0.065), (1.322, 0.030, 18, 0.065)]
NP = 24


def blade_ring(ch, t, camber=0.03):
    """24 points around the section: psi 0..pi upper surface TE->LE, pi..2pi lower LE->TE; (xc, yc) chord units"""
    w = min(1.0, max(0.0, (t - 0.25) / 0.45))
    out = []
    for i in range(NP):
        psi = 2 * math.pi * i / NP
        xc = 0.5 + 0.5 * math.cos(psi)
        tt = min(t, 0.30)
        u, l = naca(camber, 0.4, tt, xc)
        xa, ya = (u if math.sin(psi) >= 0 else l)
        xe, ye = 0.5 + 0.5 * math.cos(psi), 0.5 * t * math.sin(psi)
        out.append((xa * (1 - w) + xe * w, ya * (1 - w) + ye * w))
    return out


BLADES = []
for k in range(3):
    phi = 2 * math.pi * k / 3
    d = Vector((math.sin(phi), 0, math.cos(phi)))                 # span direction
    tv = Vector((-math.cos(phi), 0, math.sin(phi)))               # direction of motion (clockwise, cockpit view)
    bm = bmesh.new()
    rings = []
    for r, ch, ang, t in STA:
        b = math.radians(ang)
        cvec = tv * math.cos(b) + FWD * math.sin(b)              # trailing edge -> leading edge
        nvec = -tv * math.sin(b) + FWD * math.cos(b)              # camber side (forward)
        c0 = P_C + d * r
        # leading edge (xc = 0) at c0 + 0.35 ch * cvec, trailing edge (xc = 1) at c0 - 0.65 ch * cvec
        rings.append([c0 + cvec * ((0.35 - xc) * ch) + nvec * (yc * ch) for xc, yc in blade_ring(ch, t)])
    loft(bm, rings, True, True, True, mat=0)
    fix_normals(bm)
    ob = obj_from_bm(f'PropBlade_{k + 1}', bm, C_SRC, [M['src_PropBlade']])
    shade(ob, 50)
    set_pivot(ob, tuple(P_C), (0.0, phi, 0.0))                    # local Z = blade span (pitch axis), local Y = prop axis
    parent_keep(ob, prop)
    BLADES.append(ob)

# sanity: leading edge of blade 1 (12 o'clock) leads the motion (towards the pilot's right = -X) and lies forward
me = BLADES[0].data
mw = BLADES[0].matrix_world
pts = [mw @ v.co for v in me.vertices]
mid = [p for p in pts if abs((p - P_C).z - 0.76) < 0.004]
le = min(mid, key=lambda p: p.x)
te = max(mid, key=lambda p: p.x)
assert le.y < te.y, ('blade twist sign', le, te)
print('blade 1 at r=0.76: LE', tuple(round(c, 3) for c in le), 'TE', tuple(round(c, 3) for c in te))

# fast-rotation discs (unbaked materials, UV 0..1 over a 2.68 m square)
for name, dy, mat in (('PropBlur', -0.012, 'src_PropBlur'), ('PropDisc', 0.012, 'src_PropDisc')):
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    RR, r0, n = 1.335, 0.25, 64
    inner = [bm.verts.new((r0 * math.sin(2 * math.pi * i / n), P_C.y + dy, P_C.z + r0 * math.cos(2 * math.pi * i / n)))
             for i in range(n)]
    mid_ = [bm.verts.new((0.8 * RR * math.sin(2 * math.pi * i / n), P_C.y + dy,
                          P_C.z + 0.8 * RR * math.cos(2 * math.pi * i / n))) for i in range(n)]
    outer = [bm.verts.new((RR * math.sin(2 * math.pi * i / n), P_C.y + dy, P_C.z + RR * math.cos(2 * math.pi * i / n)))
             for i in range(n)]
    for ra, rb in ((inner, mid_), (mid_, outer)):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
            for lp in f.loops:
                x, z = lp.vert.co.x, lp.vert.co.z - P_C.z
                lp[uvl].uv = (0.5 - x / (2 * RR), 0.5 + z / (2 * RR))
    ob = obj_from_bm(name, bm, C_SRC, [M[mat]])
    set_pivot(ob, (P_C.x, P_C.y + dy, P_C.z))
    parent_keep(ob, ROOT)


# ================================================================== WHEELS
def sector_block(bm, center, a0, a1, th0, th1, r0, r1, mat, nth=2, taper=0.0, inset_a=0.0):
    """annular-sector box around the X axis through center: axial a0..a1, angle th0..th1, radius r0..r1;
    taper / inset_a shrink the top face (angle fraction / axial metres) for a moulded-lug draft"""
    c = Vector(center)
    P = lambda a, th, r: c + Vector((a, r * math.sin(th), r * math.cos(th)))
    mid = (th0 + th1) / 2
    rings = []
    for i in range(nth + 1):
        th = th0 + (th1 - th0) * i / nth
        tht = mid + (th - mid) * (1.0 - taper)
        rings.append([P(a0, th, r0), P(a1, th, r0), P(a1 - inset_a, tht, r1), P(a0 + inset_a, tht, r1)])
    loft(bm, rings, True, True, True, mat=mat)


TYRE = [(-0.115, 0.17), (-0.15, 0.21), (-0.178, 0.27), (-0.19, 0.33), (-0.186, 0.38), (-0.168, 0.418),
        (-0.135, 0.445), (-0.085, 0.458), (-0.03, 0.462), (0.03, 0.462), (0.085, 0.458), (0.135, 0.445),
        (0.168, 0.418), (0.186, 0.38), (0.19, 0.33), (0.178, 0.27), (0.15, 0.21), (0.115, 0.17)]


def make_wheel(name, center, sgn, scale=1.0, wsc=1.0, pitches=18, lug=0.022, brake=True, segs=72):
    c = Vector(center)
    S = lambda a, r: (a * scale * wsc, r * scale)
    bm = bmesh.new()
    revolve(bm, [S(a, r) for a, r in TYRE], 'X', tuple(c), segs=segs, mat=0)
    lugh = lug                                                     # crown lugs: two staggered rows + shoulder blocks
    dth = 2 * math.pi / pitches
    for i in range(pitches):
        for row, (a0, a1, off) in enumerate(((-0.165, -0.018, 0.0), (0.018, 0.165, 0.5))):
            th = (i + off) * dth
            w = 0.60 * dth
            sector_block(bm, c, a0 * scale * wsc, a1 * scale * wsc, th - w / 2, th + w / 2, 0.440 * scale,
                         (0.462 * scale) + lugh, 0, taper=0.16, inset_a=0.008 * scale)
            # shoulder lug wrapping down the sidewall, same pitch as its crown block
            sa0, sa1 = ((-0.200, -0.148) if row == 0 else (0.148, 0.200))
            sector_block(bm, c, sa0 * scale * wsc, sa1 * scale * wsc, th - w * 0.42, th + w * 0.42, 0.400 * scale,
                         0.447 * scale + lugh * 0.5, 0, taper=0.14, inset_a=0.004 * scale)
    # sidewall protector rib
    for sg in (1, -1):
        revolve(bm, [(sg * 0.188 * scale * wsc, 0.300 * scale), (sg * 0.196 * scale * wsc, 0.305 * scale),
                     (sg * 0.196 * scale * wsc, 0.318 * scale), (sg * 0.188 * scale * wsc, 0.323 * scale)], 'X',
                tuple(c), segs=segs // 2, mat=0)
    # dished rim, both faces (outboard = +sgn side in X)
    for side in (1, -1):
        s_ = side
        rim = [(0.150, 0.0), (0.152, 0.030), (0.140, 0.052), (0.118, 0.062), (0.112, 0.110), (0.125, 0.150),
               (0.148, 0.166), (0.156, 0.176), (0.150, 0.182), (0.120, 0.174)]
        revolve(bm, [S(s_ * a, r) for a, r in rim], 'X', tuple(c), segs=32, mat=1)
        for k in range(6):                                         # lug nuts
            ang = 2 * math.pi * k / 6
            p = c + Vector((s_ * 0.118 * scale * wsc, math.sin(ang) * 0.085 * scale, math.cos(ang) * 0.085 * scale))
            cylinder(bm, p, p + Vector((s_ * 0.016 * scale, 0, 0)), 0.012 * scale, 0.011 * scale, 6, mat=1)
        for k in range(12):                                        # split-rim bolts
            ang = 2 * math.pi * (k + 0.5) / 12
            p = c + Vector((s_ * 0.120 * scale * wsc, math.sin(ang) * 0.135 * scale, math.cos(ang) * 0.135 * scale))
            cylinder(bm, p, p + Vector((s_ * 0.008 * scale, 0, 0)), 0.006 * scale, 0.006 * scale, 6, mat=1)
    # valve stem on the outboard rim face (outboard = +sgn x)
    vp = c + Vector((sgn * 0.130 * scale * wsc, 0.0, 0.158 * scale))
    cylinder(bm, vp, vp + Vector((sgn * 0.030 * scale, 0, 0.004)), 0.004 * scale, 0.0035 * scale, 8, mat=2)
    if brake:                                                      # brake disc outside the inboard rim half
        a = -sgn * 0.168
        revolve(bm, [(a - 0.004, 0.072), (a - 0.004, 0.130), (a + 0.004, 0.130), (a + 0.004, 0.072),
                     (a - 0.004, 0.072)], 'X', tuple(c), segs=40, mat=2)
        for k in range(6):
            ang = 2 * math.pi * (k + 0.5) / 6
            p = c + Vector((a, math.sin(ang) * 0.08, math.cos(ang) * 0.08))
            cylinder(bm, p - Vector((0.006, 0, 0)), p + Vector((0.006, 0, 0)), 0.006, 0.006, 6, mat=2)
    fix_normals(bm)
    # open surfaces (carcass, rim dishes): face outwards explicitly (Unity culls back faces)
    ax = Vector((1, 0, 0))
    for f in bm.faces:
        p = f.calc_center_median()
        rel = p - c
        a_ = rel.dot(ax)
        radial = (rel - ax * a_)
        rd = radial.normalized() if radial.length > 1e-6 else Vector((0, 0, 1))
        if f.material_index == 0:
            q = c + rd * 0.30 * scale
            want = p - q
        elif f.material_index == 1:
            want = ax * (1 if a_ >= 0 else -1) if abs(f.normal.dot(ax)) > 0.3 else rd
        else:
            continue
        if f.normal.dot(want) < 0:
            f.normal_flip()
    ob = obj_from_bm(name, bm, C_SRC, [M['src_Rubber'], M['src_Hub'], M['src_Brake']])
    shade(ob, 50)
    set_pivot(ob, tuple(c))
    return ob


for side, sgn in (('L', 1), ('R', -1)):
    par, _ = remove(f'Wheel_{side}')
    c = (sgn * LY.MAIN_WHEEL_C[0], LY.MAIN_WHEEL_C[1], LY.MAIN_WHEEL_C[2])
    w = make_wheel(f'Wheel_{side}', c, sgn)
    w['wscale'] = 1.0
    parent_keep(w, O[f'Gear_{side}'])
    # brake caliper on the gear leg (does not turn with the wheel): aft-lower quadrant, straddling the disc edge
    g = O[f'Gear_{side}']
    bmg = bmesh.new()
    bmg.from_mesh(g.data)
    if 'src_Caliper' not in [m.name for m in g.data.materials]:
        g.data.materials.append(M['src_Caliper'])
    mi = [m.name for m in g.data.materials].index('src_Caliper')
    inv = g.matrix_world.inverted()
    tmp = bmesh.new()
    ang = math.radians(135)
    cc = Vector(c) + Vector((-sgn * 0.168, 0.118 * math.sin(ang), 0.118 * math.cos(ang)))
    box(tmp, (0, 0, 0), (0.050, 0.062, 0.046), mat=mi, bevel=0.006, bevel_segs=2)
    box(tmp, (0.0, 0.0, -0.030), (0.030, 0.034, 0.030), mat=mi, bevel=0.004, bevel_segs=1)      # mounting lug
    for sy in (-0.02, 0.02):
        cylinder(tmp, Vector((-0.03, sy, 0.012)), Vector((0.03, sy, 0.012)), 0.005, 0.005, 6, mat=mi)
    T = Matrix.Translation(cc) @ Matrix.Rotation(-ang, 4, 'X')
    bmesh.ops.transform(tmp, matrix=inv @ T, verts=tmp.verts)
    me_t = bpy.data.meshes.new('tmp_cal')
    tmp.to_mesh(me_t)
    tmp.free()
    bmg.from_mesh(me_t)
    bpy.data.meshes.remove(me_t)
    bmg.to_mesh(g.data)
    bmg.free()

par, _ = remove('TailWheel')
tw = make_wheel('TailWheel', LY.TAIL_WHEEL_C, 1, scale=0.59, wsc=0.72, pitches=14, lug=0.012, brake=False, segs=48)
tw['wscale'] = 0.59
parent_keep(tw, O['TailWheel_Fork'])

# ================================================================== COWL DETAILS: intake (as v2) + PT6-style exhaust stacks
remove('src_CowlDetails')
bm = bmesh.new()
intake_rings = []
for y, hw, hh, z in ((-4.63, 0.19, 0.075, 1.34), (-4.58, 0.215, 0.095, 1.335), (-4.46, 0.215, 0.09, 1.31),
                     (-4.30, 0.19, 0.07, 1.24)):
    intake_rings.append([Vector((x, y, z + zz)) for x, zz in superellipse(hw, hh, 3.0, 20)])
inner = [[Vector((v.x * 0.78, -4.63, 1.34 + (v.z - 1.34) * 0.6)) for v in intake_rings[0]],
         [Vector((v.x * 0.78, -4.52, 1.34 + (v.z - 1.34) * 0.6)) for v in intake_rings[0]]]
loft(bm, [inner[1], inner[0]] + intake_rings, True, True, True)
NE = 20
_fus = O['src_Fuselage']
_dg = bpy.context.evaluated_depsgraph_get()
_fe, _finv = _fus.evaluated_get(_dg), _fus.matrix_world.inverted()


def cowl_x(y, z, sgn):
    ok, loc, n_, i_ = _fe.ray_cast(_finv @ Vector((sgn * 2.0, y, z)), (_finv.to_3x3() @ Vector((-sgn, 0, 0))).normalized())
    return (_fus.matrix_world @ loc).x if ok else None


for sgn in (1, -1):
    # short PT6 stack: the bend is mostly inside the cowl, ~0.14 m proud of the skin, mouth aft and 25 deg outboard
    path = bezier((0.50 * sgn, -4.07, 1.585), (0.69 * sgn, -4.05, 1.58), (0.725 * sgn, -3.80, 1.565), 14)
    rings = []
    for k, p in enumerate(path):
        u = k / (len(path) - 1)
        tng = path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)]
        s, up = ring_frame(p, tng)
        q = min(1.0, max(0.0, (u - 0.55) / 0.45))
        fl = 1.0 + 0.22 * q * q * (3 - 2 * q)                            # smooth trumpet flare
        a, b = 0.082 * fl, 0.060 * fl
        rings.append([p + s * (a * math.cos(t)) + up * (b * math.sin(t)) for t in (2 * PI * i / NE for i in range(NE))])
    pe, t_ = path[-1], (path[-1] - path[-2]).normalized()
    s, up = ring_frame(pe, t_)
    a_m, b_m = 0.082 * 1.22, 0.060 * 1.22
    for fac, back in ((1.02, -0.004), (0.96, -0.007), (0.94, 0.02), (0.84, 0.13)):  # rolled lip + inner wall
        cpt = pe - t_ * back
        rings.append([cpt + s * (a_m * fac * math.cos(t)) + up * (b_m * fac * math.sin(t))
                      for t in (2 * PI * i / NE for i in range(NE))])
    loft(bm, rings, True, True, True)
    # doubler flange where the stack leaves the skin (first path point outside the cowl)
    kf = next(k for k, p in enumerate(path) if (cowl_x(p.y, p.z, sgn) or 0.0) * sgn < p.x * sgn)
    fp, ft = path[kf], (path[min(kf + 1, len(path) - 1)] - path[max(kf - 1, 0)]).normalized()
    s, up = ring_frame(fp, ft)
    rings = [[fp + ft * dd + s * (0.098 * math.cos(t)) + up * (0.076 * math.sin(t)) for t in
              (2 * PI * i / NE for i in range(NE))] for dd in (-0.006, 0.003)]
    loft(bm, rings, True, True, True)
    print('exhaust', sgn, 'skin crossing at path point', kf, tuple(round(c, 3) for c in fp))
fix_normals(bm)
cowl = obj_from_bm('src_CowlDetails', bm, C_SRC, [M['src_MetalDark']])
shade(cowl, 45)
parent_keep(cowl, ROOT)

# ================================================================== ANTENNAS + PITOT
W_LE, W_CH, W_Z0, DIH = -2.55, 2.10, 2.648, math.radians(2.0)
W_M, W_P, W_T = 0.02, 0.4, 0.13


def wz(x):
    return W_Z0 + max(0.0, abs(x) - 0.76) * math.tan(DIH)


def wing_surface_z(x, xc, upper=True):
    u, l = naca(W_M, W_P, W_T, xc)
    return wz(x) + (u[1] if upper else l[1]) * W_CH


remove('src_Antennas')
bm = bmesh.new()
for x, y in ((0.28, -1.30), (-0.28, -1.30), (0.0, 3.05)):
    z = wing_surface_z(x, (y - W_LE) / W_CH, True) if abs(y) < 2 else 2.52
    base = Vector((x, y, z - 0.01))
    revolve(bm, [(0.0, 0.034), (0.006, 0.034), (0.012, 0.030), (0.045, 0.024), (0.05, 0.0)], 'Z', tuple(base), segs=14)
    tip = base + Vector((0, 0.18, 0.62))
    cylinder(bm, base + Vector((0, 0, 0.045)), tip, 0.0085, 0.003, 8)
    revolve(bm, [(-0.006, 0.0), (-0.006, 0.0055), (0.004, 0.0055), (0.006, 0.0)], 'Z', tuple(tip), segs=8)


def comm_blade(bm, y0, z0, up):
    """swept VHF blade: base plate + 9 airfoil stations, rounded tip"""
    plate = [Vector((x_, y0 + y_, z0)) for x_, y_ in superellipse(0.034, 0.135, 3.0, 20)]
    rings = [[p + Vector((0, 0, -up * 0.002)) for p in plate], [p + Vector((0, 0, up * 0.004)) for p in plate]]
    loft(bm, rings, True, True, True)
    for sy in (-0.10, -0.035, 0.035, 0.10):
        p = Vector((0, y0 + sy, z0 + up * 0.004))
        cylinder(bm, p, p + Vector((0, 0, up * 0.002)), 0.004, 0.004, 6)
    H = 0.255
    st = []
    for k in range(10):
        u = k / 9
        h = H * u
        le = y0 - 0.115 + 0.155 * u ** 0.9
        ch = 0.215 - 0.145 * u
        if k == 9:
            ch = 0.035
        st.append((h, le, ch))
    rings = []
    for h, le, ch in st:
        r2 = airfoil_ring(0, 0.999, 8, 0, 0, 0.10, True)[:-1]
        rings.append([Vector((yc * ch, le + xc * ch, z0 + up * (0.004 + h))) for xc, yc in r2])
    loft(bm, rings, True, True, True)


comm_blade(bm, 2.35, 2.585, 1)
comm_blade(bm, -1.05, 0.975, -1)
# pitot: mast under the port wing + heated tube
xp = 4.6
zl = wing_surface_z(xp, 0.2, False)
m0 = Vector((xp, W_LE + 0.25 * W_CH, zl + 0.01))
sweep(bm, [m0, m0 + Vector((0, -0.03, -0.06)), m0 + Vector((0, -0.06, -0.12))], lambda u: 0.022 - 0.008 * u,
      lambda u: 0.009 - 0.003 * u, 10)
cylinder(bm, m0 + Vector((0, 0.04, -0.12)), m0 + Vector((0, -0.40, -0.12)), 0.011, 0.011, 12)
revolve(bm, [(-0.40, 0.011), (-0.43, 0.009), (-0.445, 0.006), (-0.447, 0.0)], 'Y', tuple(m0 + Vector((0, 0, -0.12))),
        segs=12)
fix_normals(bm)
ant = obj_from_bm('src_Antennas', bm, C_SRC, [M['src_Antenna']])
shade(ant, 45)
parent_keep(ant, ROOT)


# ================================================================== LOCK CYLINDERS (outer pilot-door handles)
def skin_x(door, y, z, sgn):
    """outer skin x of the door at (y, z): ray from outside"""
    dg = bpy.context.evaluated_depsgraph_get()
    ob = door.evaluated_get(dg)
    inv = door.matrix_world.inverted()
    o_ = inv @ Vector((sgn * 1.2, y, z))
    d_ = (inv.to_3x3() @ Vector((-sgn, 0, 0))).normalized()
    ok, loc, nrm, idx = ob.ray_cast(o_, d_)
    assert ok, ('lock ray', door.name)
    return (door.matrix_world @ loc).x


LOCKS = {}
for side, sgn in (('L', 1), ('R', -1)):
    door = O[f'PilotDoor_{side}']
    y, z = -2.215, 1.70
    xs = skin_x(door, y, z, sgn)
    bm = bmesh.new()
    c0 = Vector((xs - sgn * 0.002, y, z))
    revolve(bm, [(0.0, 0.0115), (0.0022, 0.0115), (0.0032, 0.0098), (0.0032, 0.0)], 'X', tuple(c0), segs=20, mat=0)
    # keyway: dark slot in the plug face
    box(bm, c0 + Vector((0.0034, 0, 0)), (0.0012, 0.0016, 0.0105), mat=1)
    fix_normals(bm)
    if sgn < 0:                                                    # revolve 'X' faces +X: mirror the profile side
        bmesh.ops.scale(bm, vec=(-1, 1, 1), space=Matrix.Translation(-c0), verts=bm.verts)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    ob = obj_from_bm(f'Lock_PilotDoor_{side}', bm, C_SRC, [M['src_KeyMetal'], M['src_LadderTread']])
    shade(ob, 40)
    set_pivot(ob, tuple(c0 + Vector((sgn * 0.0032, 0, 0))))
    parent_keep(ob, door)
    LOCKS[side] = tuple(c0 + Vector((sgn * 0.0032, 0, 0)))
    print('lock', side, 'skin x', round(xs, 4), 'face', tuple(round(v, 4) for v in LOCKS[side]))


# ================================================================== STEP LADDER (M5): 4 treads + platform at 1.30 m
def rail(bm, p0, p1, w, d, mat):
    """rectangular tube between p0 and p1, cross-section w (x) by d (perpendicular)"""
    p0, p1 = Vector(p0), Vector(p1)
    t = (p1 - p0).normalized()
    s = Vector((1, 0, 0))
    u = t.cross(s).normalized()
    rings = []
    for p in (p0, p1):
        rings.append([p + s * (w / 2 * a) + u * (d / 2 * b) for a, b in ((1, 1), (-1, 1), (-1, -1), (1, -1))])
    loft(bm, rings, True, True, True, mat=mat)


LAD = dict(H=1.30, treads=(0.26, 0.52, 0.78, 1.04), half_w=0.36, y_front=-0.66, y_top_front=-0.18, y_top_rear=0.18,
           y_rear=0.58, rail_top=2.05)
FILL = Vector((1.55, -3.20, 0.0))                  # preview spot: in front of the left filler (ground set below)
bm = bmesh.new()
hw = LAD['half_w']
yf, ytf = LAD['y_front'], LAD['y_top_front']
for sx in (-1, 1):
    rail(bm, (sx * hw, yf, 0.0), (sx * hw, ytf, LAD['H']), 0.025, 0.055, 0)                 # front stiles
    rail(bm, (sx * hw, ytf, LAD['H']), (sx * hw, ytf + 0.02, LAD['rail_top']), 0.025, 0.03, 0)   # hand rails
    rail(bm, (sx * hw, ytf + 0.02, LAD['rail_top']), (sx * hw, LAD['y_top_rear'], LAD['rail_top'] - 0.05), 0.025,
         0.03, 0)
    rail(bm, (sx * hw, LAD['y_top_rear'], LAD['rail_top'] - 0.05), (sx * hw, LAD['y_top_rear'], LAD['H']), 0.025,
         0.03, 0)
    box(bm, (sx * hw, yf + 0.01, 0.015), (0.05, 0.08, 0.03), mat=2, bevel=0.006, bevel_segs=1)   # rubber feet
for h in LAD['treads']:
    y = yf + (ytf - yf) * h / LAD['H']
    box(bm, (0, y + 0.05, h - 0.012), (2 * hw - 0.02, 0.13, 0.024), mat=0, bevel=0.004, bevel_segs=1)
    for k in range(5):
        box(bm, (0, y + 0.0 + k * 0.025, h + 0.001), (2 * hw - 0.05, 0.008, 0.004), mat=1)
box(bm, (0, 0.0, LAD['H'] - 0.015), (2 * hw - 0.02, LAD['y_top_rear'] - ytf + 0.04, 0.03), mat=0, bevel=0.005,
    bevel_segs=1)
for k in range(13):
    box(bm, (0, ytf + 0.015 + k * 0.027, LAD['H'] + 0.0015), (2 * hw - 0.06, 0.009, 0.004), mat=1)
# safety placard band on the top tread edge
box(bm, (0, ytf - 0.003, LAD['H'] - 0.022), (2 * hw - 0.06, 0.004, 0.02), mat=3)
fix_normals(bm)
lad = obj_from_bm('src_StepLadder', bm, C_SRC, [M['src_Alu'], M['src_LadderTread'], M['src_Rubber'], M['src_KeyFob']])
shade(lad, 40)
bm = bmesh.new()
for sx in (-1, 1):
    rail(bm, (sx * hw, LAD['y_top_rear'], LAD['H'] - 0.02), (sx * (hw + 0.02), LAD['y_rear'], 0.0), 0.025, 0.045, 0)
    box(bm, (sx * (hw + 0.02), LAD['y_rear'] - 0.01, 0.015), (0.05, 0.08, 0.03), mat=1, bevel=0.006, bevel_segs=1)
for h in (0.35, 0.80):
    t_ = h / (LAD['H'] - 0.02)
    yy = LAD['y_rear'] + (LAD['y_top_rear'] - LAD['y_rear']) * t_
    box(bm, (0, yy, h), (2 * hw + 0.02, 0.02, 0.02), mat=0)
fix_normals(bm)
legs = obj_from_bm('Ladder_RearLegs', bm, C_SRC, [M['src_Alu'], M['src_Rubber']])
shade(legs, 40)
set_pivot(legs, (0.0, LAD['y_top_rear'], LAD['H'] - 0.02))
gzl = LY.ground_z(FILL.y)
lad.matrix_world = Matrix.Translation(Vector((FILL.x, FILL.y, gzl)))
legs.matrix_world = Matrix.Translation(Vector((FILL.x, FILL.y, gzl))) @ legs.matrix_world
parent_keep(legs, lad)

# ================================================================== KEY (M2): key + split ring + bright fob
bm = bmesh.new()
# bow (head) and blade in the X-Z plane, thickness along Y
bow = [(0.0, 0.0), (0.012, -0.002), (0.016, 0.006), (0.016, 0.022), (0.010, 0.030), (-0.010, 0.030),
       (-0.016, 0.022), (-0.016, 0.006), (-0.012, -0.002)]
rings = [[Vector((x, yy, z)) for x, z in bow] for yy in (-0.0012, 0.0012)]
loft(bm, rings, True, True, True, mat=0)
blade = [(-0.0045, 0.0), (0.0045, 0.0), (0.0045, -0.036), (0.002, -0.042), (-0.0045, -0.038)]
rings = [[Vector((x, yy, z)) for x, z in blade] for yy in (-0.001, 0.001)]
loft(bm, rings, True, True, True, mat=0)
sweep(bm, [Vector((0.025 * math.cos(a), 0, 0.050 + 0.025 * math.sin(a))) for a in
           (2 * math.pi * i / 16 for i in range(17))], 0.0012, 0.0012, 6, cap0=False, cap1=False, mat=0)
fob = [(-0.018, 0.074), (0.018, 0.074), (0.020, 0.13), (0.0, 0.142), (-0.020, 0.13)]
rings = [[Vector((x, yy, z)) for x, z in fob] for yy in (-0.005, 0.005)]
loft(bm, rings, True, True, True, mat=1)
fix_normals(bm)
key = obj_from_bm('src_PlaneKey', bm, C_SRC, [M['src_KeyMetal'], M['src_KeyFob']])
shade(key, 40)
key.matrix_world = Matrix.Translation(Vector((0.30, -2.95, 2.11)))         # preview: on the glareshield

for ob in (lad, key):
    parent_keep(ob, ROOT)

import json
json.dump(dict(locks=LOCKS, ladder=LAD), open(os.path.join(HERE, 'out', 'ext_v7.json'), 'w'), indent=1)
tris = 0
dg = bpy.context.evaluated_depsgraph_get()
for ob in bpy.data.objects:
    if ob.type == 'MESH':
        me = ob.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        n = len(me.loop_triangles)
        tris += n
        if ob.name in ('Propeller', 'PropBlade_1', 'Wheel_L', 'TailWheel', 'src_CowlDetails', 'src_Antennas',
                       'src_StepLadder', 'Ladder_RearLegs', 'src_PlaneKey', 'Gear_L', 'Lock_PilotDoor_L', 'PropDisc'):
            print(f'  {ob.name:18s} {n}')
        ob.evaluated_get(dg).to_mesh_clear()
print('TOTAL TRIS', tris)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'plane_geo_v7.blend'))
print('saved plane_geo_v7.blend')
