"""Forest airfield, concept (after) on the scene of the 28.10 21:41 map export (af_scene.py), by the accepted answers of
docs/gdd/locations/airfield/QUESTIONS_2.md: flat wide corridor, 1:4 rounded slopes, forest 40-60 m off the slabs with a
young belt at its edge, approach funnels 150-200 m (stumps, young growth), the slabs under thin ploughed snow with two
wheel tracks, windrows ~1 m, snow poles as now, lights only at the ends (snow caps), one pale transverse stripe per end,
the hangar in a rounded hill with spruces, drifts at the facade, the south pad with fuel drums, a generator and the power
cabinet at the hut, the windsock beside the pad; the big fuel depot removed.

python3.11 -I concept.py <before.blend> <out.blend>"""
import bpy, bmesh, json, math, os, sys
import numpy as np
from mathutils import Vector, Matrix

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import af_scene as S
import ground_after as GA

RNG = np.random.default_rng(2910)
GROUND_TEX = S.GROUND_TEX
R = None          # ground result (GA.compute())


def B(ux, uz, uy=0.0):
    return Vector((-ux, -uz, uy))


def uvB(u, v, y):
    x, z = GA.to_xz(u, v)
    return B(float(x), float(z), float(y))


def gy(x, z, A=None):
    """height of the after ground at Unity (x, z)"""
    return GA.sample(R['N'] if A is None else A, R['g'], x, z)


def gy_uv(u, v):
    x, z = GA.to_xz(u, v)
    return gy(x, z)


def ddelta(x, z):
    return GA.sample(R['delta'], R['g'], x, z)


def noise1(t, seed, octaves=((70.0, 1.0), (31.0, 0.5), (13.0, 0.25))):
    """smooth noise in [0, 1] along a coordinate"""
    rs = np.random.default_rng(seed)
    acc = 0.0; tot = 0.0
    for wl, a in octaves:
        ph = rs.uniform(0, 2 * math.pi)
        acc = acc + a * np.sin(2 * math.pi * np.asarray(t) / wl + ph); tot += a
    return 0.5 + 0.5 * acc / tot


# ---------------------------------------------------------------- materials
def snow_tex_node(N, L, scale=2.0, name='T_GR_Floor_A.png'):
    geo = N.new('ShaderNodeNewGeometry')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], sep.inputs['Vector'])
    comb = N.new('ShaderNodeCombineXYZ')
    for ax in ('X', 'Y'):
        m_ = N.new('ShaderNodeMath'); m_.operation = 'MULTIPLY'; m_.inputs[1].default_value = -1.0 / scale
        L.new(sep.outputs[ax], m_.inputs[0]); L.new(m_.outputs['Value'], comb.inputs[ax])
    tx = N.new('ShaderNodeTexImage'); tx.image = S.image(GROUND_TEX + name); tx.interpolation = 'Closest'
    L.new(comb.outputs['Vector'], tx.inputs['Vector'])
    return tx.outputs['Color'], geo


def mat_snow(name='M_SnowBank', bright=1.12, dirt=(0.30, 0.29, 0.275)):
    """snow of banks, piles, caps: the ground's snow texture, a little brighter; colour attribute 'dirt' greys it"""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    pb = N['Principled BSDF']; pb.inputs['Roughness'].default_value = 0.85
    col, geo = snow_tex_node(N, L)
    k = N.new('ShaderNodeMix'); k.data_type = 'RGBA'; k.blend_type = 'MULTIPLY'; k.inputs['Factor'].default_value = 1.0
    L.new(col, k.inputs['A']); k.inputs['B'].default_value = (bright, bright, bright * 1.02, 1)
    at = N.new('ShaderNodeAttribute'); at.attribute_type = 'GEOMETRY'; at.attribute_name = 'dirt'
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    L.new(at.outputs['Fac'], mx.inputs['Factor']); L.new(k.outputs['Result'], mx.inputs['A']); mx.inputs['B'].default_value = (*dirt, 1)
    L.new(mx.outputs['Result'], pb.inputs['Base Color'])
    S.fog_wrap(mat, pb.outputs['BSDF'])
    return mat


def mat_flat(name, rgb, rough=0.8, snow=True, metal=0.0):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    pb = N['Principled BSDF']; pb.inputs['Roughness'].default_value = rough; pb.inputs['Metallic'].default_value = metal
    rgbn = N.new('ShaderNodeRGB'); rgbn.outputs[0].default_value = (*rgb, 1)
    col = rgbn.outputs[0]
    if snow:
        col = S.snow_mix(mat, col)
    L.new(col, pb.inputs['Base Color'])
    S.fog_wrap(mat, pb.outputs['BSDF'])
    return mat


def mat_grass():
    mat = bpy.data.materials.get('M_DryGrass')
    if mat:
        return mat
    mat = bpy.data.materials.new('M_DryGrass'); mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    pb = N['Principled BSDF']; pb.inputs['Roughness'].default_value = 0.9
    at = N.new('ShaderNodeAttribute'); at.attribute_type = 'GEOMETRY'; at.attribute_name = 'tint'
    L.new(at.outputs['Color'], pb.inputs['Base Color'])
    S.fog_wrap(mat, pb.outputs['BSDF'])
    return mat


def ground_material_after(old):
    """the export's paint (as before) outside the airfield; inside: snow, ploughed packed snow, a straw tint where dry grass
    shows on the slopes; mask in the colour attribute 'mask' (R plough, G track, B grass, A airfield)"""
    mat = old.copy(); mat.name = 'G_Ground_After'
    N, L = mat.node_tree.nodes, mat.node_tree.links
    pb = N['Principled BSDF']
    before = pb.inputs['Base Color'].links[0].from_socket
    snow, geo = snow_tex_node(N, L, 2.0, 'T_GR_Floor_A.png')
    pack, _ = snow_tex_node(N, L, 2.5, 'T_GR_Track_A.png')
    ruts, _ = snow_tex_node(N, L, 2.0, 'T_GR_Ruts_A.png')
    at = N.new('ShaderNodeAttribute'); at.attribute_type = 'GEOMETRY'; at.attribute_name = 'mask'
    sp = N.new('ShaderNodeSeparateColor'); L.new(at.outputs['Color'], sp.inputs['Color'])
    # large-scale brightness: wind-packed patches
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.035; nz.inputs['Detail'].default_value = 3.0
    L.new(geo.outputs['Position'], nz.inputs['Vector'])
    br = N.new('ShaderNodeMapRange'); br.inputs['From Min'].default_value = 0.3; br.inputs['From Max'].default_value = 0.7
    br.inputs['To Min'].default_value = 1.06; br.inputs['To Max'].default_value = 1.16
    L.new(nz.outputs['Fac'], br.inputs['Value'])
    s1 = N.new('ShaderNodeMix'); s1.data_type = 'RGBA'; s1.blend_type = 'MULTIPLY'; s1.inputs['Factor'].default_value = 1.0
    L.new(snow, s1.inputs['A'])
    cb = N.new('ShaderNodeCombineXYZ'); L.new(br.outputs['Result'], cb.inputs['X']); L.new(br.outputs['Result'], cb.inputs['Y']); L.new(br.outputs['Result'], cb.inputs['Z'])
    L.new(cb.outputs['Vector'], s1.inputs['B'])
    # packed: track texture brightened a bit
    p1 = N.new('ShaderNodeMix'); p1.data_type = 'RGBA'; p1.blend_type = 'MULTIPLY'; p1.inputs['Factor'].default_value = 1.0
    L.new(pack, p1.inputs['A']); p1.inputs['B'].default_value = (1.32, 1.32, 1.35, 1)
    pk = N.new('ShaderNodeMix'); pk.data_type = 'RGBA'; pk.inputs['Factor'].default_value = 0.45
    L.new(s1.outputs['Result'], pk.inputs['A']); L.new(p1.outputs['Result'], pk.inputs['B'])
    m1 = N.new('ShaderNodeMix'); m1.data_type = 'RGBA'
    L.new(sp.outputs['Red'], m1.inputs['Factor']); L.new(s1.outputs['Result'], m1.inputs['A']); L.new(pk.outputs['Result'], m1.inputs['B'])
    # tracks (G): ruts texture over the packed snow
    r1 = N.new('ShaderNodeMix'); r1.data_type = 'RGBA'; r1.blend_type = 'MULTIPLY'; r1.inputs['Factor'].default_value = 1.0
    L.new(ruts, r1.inputs['A']); r1.inputs['B'].default_value = (1.35, 1.35, 1.38, 1)
    m2 = N.new('ShaderNodeMix'); m2.data_type = 'RGBA'
    L.new(sp.outputs['Green'], m2.inputs['Factor']); L.new(m1.outputs['Result'], m2.inputs['A']); L.new(r1.outputs['Result'], m2.inputs['B'])
    # grass tint (B), broken up by fine noise
    gn = N.new('ShaderNodeTexNoise'); gn.inputs['Scale'].default_value = 0.9; gn.inputs['Detail'].default_value = 2.0
    L.new(geo.outputs['Position'], gn.inputs['Vector'])
    gr = N.new('ShaderNodeMapRange'); gr.inputs['From Min'].default_value = 0.5; gr.inputs['From Max'].default_value = 0.75
    L.new(gn.outputs['Fac'], gr.inputs['Value'])
    gm = N.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'; L.new(gr.outputs['Result'], gm.inputs[0]); L.new(sp.outputs['Blue'], gm.inputs[1])
    gm2 = N.new('ShaderNodeMath'); gm2.operation = 'MULTIPLY'; gm2.inputs[1].default_value = 0.55; L.new(gm.outputs['Value'], gm2.inputs[0])
    m3 = N.new('ShaderNodeMix'); m3.data_type = 'RGBA'
    L.new(gm2.outputs['Value'], m3.inputs['Factor']); L.new(m2.outputs['Result'], m3.inputs['A']); m3.inputs['B'].default_value = (0.47, 0.42, 0.33, 1)
    # airfield (A) vs the paint of the export
    m4 = N.new('ShaderNodeMix'); m4.data_type = 'RGBA'
    L.new(at.outputs['Alpha'], m4.inputs['Factor']); L.new(before, m4.inputs['A']); L.new(m3.outputs['Result'], m4.inputs['B'])
    L.new(m4.outputs['Result'], pb.inputs['Base Color'])
    return mat


def runway_material(mat):
    """the slabs under thin ploughed snow: snow over the atlas, less in two wheel tracks per lane, more at the edges"""
    N, L = mat.node_tree.nodes, mat.node_tree.links
    pb = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    atlas = pb.inputs['Base Color'].links[0].from_socket
    c, s = math.cos(math.radians(GA.RW['yaw'])), math.sin(math.radians(GA.RW['yaw']))
    geo = N.new('ShaderNodeNewGeometry')
    du = N.new('ShaderNodeVectorMath'); du.operation = 'DOT_PRODUCT'; du.inputs[1].default_value = (-c, s, 0.0)
    L.new(geo.outputs['Position'], du.inputs[0])
    u = N.new('ShaderNodeMath'); u.operation = 'ADD'; u.inputs[1].default_value = -(GA.RW['x'] * c - GA.RW['z'] * s)
    L.new(du.outputs['Value'], u.inputs[0])
    au = N.new('ShaderNodeMath'); au.operation = 'ABSOLUTE'; L.new(u.outputs['Value'], au.inputs[0])
    sc_ = N.new('ShaderNodeMath'); sc_.operation = 'DIVIDE'; sc_.inputs[1].default_value = 10.0; L.new(au.outputs['Value'], sc_.inputs[0])
    ramp = N.new('ShaderNodeValToRGB')
    el = ramp.color_ramp.elements
    stops = [(0.00, 0.60), (0.12, 0.52), (0.19, 0.30), (0.27, 0.32), (0.34, 0.58), (0.46, 0.62), (0.53, 0.36), (0.62, 0.38),
             (0.70, 0.66), (0.82, 0.80), (0.90, 0.95), (1.0, 0.98)]
    el[0].position, el[0].color = stops[0][0], (stops[0][1],) * 3 + (1,)
    el[1].position, el[1].color = stops[-1][0], (stops[-1][1],) * 3 + (1,)
    for p, val in stops[1:-1]:
        e = el.new(p); e.color = (val, val, val, 1)
    L.new(sc_.outputs['Value'], ramp.inputs['Fac'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.11; nz.inputs['Detail'].default_value = 4.0
    L.new(geo.outputs['Position'], nz.inputs['Vector'])
    nzr = N.new('ShaderNodeMapRange'); nzr.inputs['From Min'].default_value = 0.3; nzr.inputs['From Max'].default_value = 0.7
    nzr.inputs['To Min'].default_value = -0.22; nzr.inputs['To Max'].default_value = 0.22
    L.new(nz.outputs['Fac'], nzr.inputs['Value'])
    fine = N.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 1.6; fine.inputs['Detail'].default_value = 2.0
    L.new(geo.outputs['Position'], fine.inputs['Vector'])
    finr = N.new('ShaderNodeMapRange'); finr.inputs['From Min'].default_value = 0.35; finr.inputs['From Max'].default_value = 0.65
    finr.inputs['To Min'].default_value = -0.12; finr.inputs['To Max'].default_value = 0.12
    L.new(fine.outputs['Fac'], finr.inputs['Value'])
    sep = N.new('ShaderNodeSeparateColor'); L.new(ramp.outputs['Color'], sep.inputs['Color'])
    a1 = N.new('ShaderNodeMath'); a1.operation = 'ADD'; L.new(sep.outputs['Red'], a1.inputs[0]); L.new(nzr.outputs['Result'], a1.inputs[1])
    a2 = N.new('ShaderNodeMath'); a2.operation = 'ADD'; a2.use_clamp = True; L.new(a1.outputs['Value'], a2.inputs[0]); L.new(finr.outputs['Result'], a2.inputs[1])
    # only up-facing faces
    sn = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sn.inputs['Vector'])
    up = N.new('ShaderNodeMapRange'); up.inputs['From Min'].default_value = 0.6; up.inputs['From Max'].default_value = 0.9
    L.new(sn.outputs['Z'], up.inputs['Value'])
    k = N.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; L.new(a2.outputs['Value'], k.inputs[0]); L.new(up.outputs['Result'], k.inputs[1])
    snow, _ = snow_tex_node(N, L, 2.0, 'T_GR_Floor_A.png')
    sb = N.new('ShaderNodeMix'); sb.data_type = 'RGBA'; sb.blend_type = 'MULTIPLY'; sb.inputs['Factor'].default_value = 1.0
    L.new(snow, sb.inputs['A']); sb.inputs['B'].default_value = (1.08, 1.08, 1.11, 1)
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    L.new(k.outputs['Value'], mx.inputs['Factor']); L.new(atlas, mx.inputs['A']); L.new(sb.outputs['Result'], mx.inputs['B'])
    L.new(mx.outputs['Result'], pb.inputs['Base Color'])


# ---------------------------------------------------------------- mesh helpers
def mesh_obj(name, verts, faces, mat, coll, attrs=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    if smooth:
        me.shade_smooth()
    if mat is not None:
        me.materials.append(mat)
    for an, vals in (attrs or {}).items():
        vals = np.asarray(vals, dtype=np.float32)
        if vals.ndim == 1:
            a = me.attributes.new(an, 'FLOAT', 'POINT'); a.data.foreach_set('value', vals)
        else:
            a = me.attributes.new(an, 'FLOAT_COLOR', 'POINT'); a.data.foreach_set('color', vals.ravel())
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    return ob


def bank(name, pts_uv, width, height, inner, coll, mat, base_sink=0.15, dirt_inner=0.45, lump_seed=1):
    """a snow bank along a polyline (u, v): cross-section 13 points, inner side (sign along the left normal) steeper and
    greyed; height per point (array) and width per point"""
    P = np.asarray(pts_uv, dtype=np.float64)
    n = len(P)
    t = np.gradient(P, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True)
    nl = np.stack([-t[:, 1], t[:, 0]], 1)               # left normal in (u, v)
    hh = np.broadcast_to(np.asarray(height, dtype=np.float64), (n,))
    ww = np.broadcast_to(np.asarray(width, dtype=np.float64), (n,))
    ts = np.linspace(-1, 1, 13)
    verts, dirt = [], []
    rs = np.random.default_rng(lump_seed)
    lump = rs.uniform(-0.12, 0.12, (n, 13))
    for i in range(n):
        for j, tt in enumerate(ts):
            side = tt * inner                            # >0 toward the inner (runway) side
            sh = (np.cos(np.clip(abs(tt), 0, 1) * math.pi / 2) ** (1.6 if side > 0 else 1.0))
            off = ww[i] * 0.5 * tt
            pu, pv = P[i] + nl[i] * off
            base = float(gy_uv(pu, pv)[0]) - base_sink
            z = base + base_sink + hh[i] * sh * (1 + lump[i, j] * (0.3 < abs(tt) < 0.95)) if abs(tt) < 0.999 else base
            verts.append(uvB(pu, pv, z))
            dirt.append(min(1.0, dirt_inner * max(0.0, side) * 1.4) if side > 0.15 else 0.0)
    faces = []
    for i in range(n - 1):
        for j in range(12):
            a = i * 13 + j
            faces.append((a, a + 1, a + 14, a + 13))
    return mesh_obj(name, verts, faces, mat, coll, attrs={'dirt': np.array(dirt)})


def blob(name, center_uv, radius, height, coll, mat, seed=1, squash_v=1.0, yaw=0.0, base=None, res=(18, 9)):
    """a snow pile: a half ellipsoid with lumps, sitting on the ground"""
    rs = np.random.default_rng(seed)
    cu, cv = center_uv
    nu, nv = res
    verts, faces = [], []
    ph = rs.uniform(0, 6.28, 3)
    for j in range(nv + 1):
        el = (j / nv) * (math.pi / 2)
        for i in range(nu):
            az = 2 * math.pi * i / nu
            rr = radius * (1 + 0.12 * math.sin(3 * az + ph[0]) + 0.08 * math.sin(5 * az + ph[1]))
            du = rr * math.cos(el) * math.cos(az)
            dv = rr * math.cos(el) * math.sin(az) * squash_v
            ru = du * math.cos(yaw) - dv * math.sin(yaw); rv = du * math.sin(yaw) + dv * math.cos(yaw)
            pu, pv = cu + ru, cv + rv
            g0 = float(gy_uv(pu, pv)[0]) if base is None else base
            z = g0 - 0.1 + (height + 0.1) * math.sin(el) ** 0.8 * (1 + 0.06 * math.sin(2 * az + ph[2]))
            verts.append(uvB(pu, pv, z))
    for j in range(nv):
        for i in range(nu):
            a = j * nu + i; b = j * nu + (i + 1) % nu
            faces.append((a, b, b + nu, a + nu))
    top = len(verts)
    g0 = float(gy_uv(cu, cv)[0]) if base is None else base
    verts.append(uvB(cu, cv, g0 + height))
    for i in range(nu):
        a = nv * nu + i; b = nv * nu + (i + 1) % nu
        faces.append((a, b, top))
    return mesh_obj(name, verts, faces, mat, coll, attrs={'dirt': np.zeros(len(verts))})


# ---------------------------------------------------------------- the build
def ground_after():
    ob = bpy.data.objects['Ground']; me = ob.data
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    assert len(co) == R['N'].size, (len(co), R['N'].shape)
    co[:, 2] = R['N'].ravel()
    me.vertices.foreach_set('co', co.ravel()); me.update()
    # masks
    U, V = R['U'], R['V']
    au = np.abs(U)
    Uh, Vh = R['Uh'], R['Vh']
    ss = GA.smoothstep
    runway = (1 - ss(GA.PAVE_V1, GA.PAVE_V1 + 1.0, V)) * ss(GA.PAVE_V0 - 1.0, GA.PAVE_V0, V)
    shoulder = ss(8.0, 8.6, au) * (1 - ss(11.2, 12.0, au)) * runway
    ends_s = ss(GA.END_S + 4, GA.END_S + 10, V) * (1 - ss(GA.PAVE_V0, GA.PAVE_V0 + 1, V)) * (1 - ss(11.0, 13.0, au))
    ends_n = (1 - ss(GA.PAVE_V1 + 22, GA.PAVE_V1 + 28, V)) * ss(GA.PAVE_V1 - 1, GA.PAVE_V1, V) * (1 - ss(11.0, 13.0, au))
    w_ap = np.where(Vh < 6.0, GA.WALL[0] + np.clip(Vh, 0, None) * GA.WALL[1], 20.0)
    apron = (1 - ss(w_ap - 1.2, w_ap, np.abs(Uh))) * ss(-1.0, 0.0, Vh) * (1 - ss(36.0, 37.0, Vh))
    padm = (U < -8) * ss(-50.5, -48.5, U) * ss(GA.PAD['v0'] + 4, GA.PAD['v0'] + 8, V) * (1 - ss(GA.PAD['v1'] - 6, GA.PAD['v1'] - 2, V))
    d1 = (V > 296) * (V < 345) * (U < -8) * (U > -45) * (np.abs(V - (318 + (U + 8) * -0.25)) < 5.5)
    plough = np.clip(np.maximum.reduce([shoulder, ends_s, ends_n, apron, padm, d1.astype(float) * 0.9]), 0, 1)
    # tyre tracks on the end areas, the pad and the apron (ruts texture)
    trk = np.zeros_like(U)
    for c0 in (-3.4, -1.6, 1.6, 3.4):
        trk = np.maximum(trk, (1 - ss(0.25, 0.55, np.abs(U - c0))) * (ends_s + ends_n))
    for c0 in (-4.0, -2.2, 2.2, 4.0):
        trk = np.maximum(trk, (1 - ss(0.25, 0.55, np.abs(Uh - c0))) * apron * ss(1.0, 3.0, Vh))
    trk = np.clip(trk * 0.85, 0, 1)
    # dry grass where the snow is thin: slopes, the outer strip, the funnels
    gyy, gxx = np.gradient(R['N'], R['g']['step'])
    slope = np.hypot(gxx, gyy)
    grass = np.clip((slope - 0.08) / 0.12, 0, 1) * 0.9
    grass = np.maximum(grass, ss(26.0, 34.0, au) * (1 - ss(38.0, 40.0, au)) * 0.55)
    funnel = (ss(GA.END_S - 10, GA.END_S, -V + 2 * GA.END_S) * (V < GA.END_S)) + ((V > GA.END_N) * 1.0)
    grass = np.maximum(grass, np.clip(funnel, 0, 1) * (au < 110) * 0.7)
    grass *= (1 - plough) * (au > 13.5)
    zone = (1 - ss(150.0, 165.0, au)) * (1 - ss(GA.END_N + 175, GA.END_N + 195, V)) * ss(GA.END_S - 235, GA.END_S - 215, V)
    rgba = np.stack([plough, trk, grass, zone], -1).astype(np.float32).reshape(-1, 4)
    a = me.color_attributes.new('mask', 'FLOAT_COLOR', 'POINT'); a.data.foreach_set('color', rgba.ravel())
    old = me.materials[0]
    me.materials[0] = ground_material_after(old)
    print('[after] ground: changed', int((np.abs(R['delta']) > 0.05).sum()), 'samples, cut', float(R['delta'].min()), 'fill', float(R['delta'].max()), flush=True)


def reseat_objects():
    """everything on the ground follows the new ground (the hangar, its plane and plug stay); road meshes per vertex"""
    keep = ('BunkerHangar', 'UtilityPlane', 'AF_HangarPlug', 'PlaneTarp')
    n = 0
    for o in bpy.data.collections['Base'].objects:
        r = o.get('root', '')
        if r in keep:
            continue
        if r in ('RoadNet',):
            me = o.data
            co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
            W = np.array(o.matrix_world)
            P = co @ W[:3, :3].T + W[:3, 3]
            d = ddelta(-P[:, 0], -P[:, 1])
            co[:, 2] += d / max(1e-6, W[2, 2])
            me.vertices.foreach_set('co', co.ravel()); me.update(); n += 1
            continue
        if r in ('SE', 'Ice_SE', 'Foam_SE') or r.startswith('ForestStone') or r == 'Log_8':
            continue
        p = o.matrix_world.translation
        d = float(ddelta(-p.x, -p.y)[0])
        if abs(d) > 0.005:
            o.location.z += d; n += 1
    print('[after] re-seated', n, flush=True)


def fill_slab_gaps(coll):
    """ForestAirfield.json lost the modules at v +-335 (the numbers 17 / 35 went, nothing came in their place): a plain
    module there, copied from its neighbour 10 m inwards and moved along the profile"""
    obs = [o for o in bpy.data.collections['Base'].objects if o.get('root', '').startswith('RWY_Slab')]
    k = 0
    for v_src, v_dst in ((325.0, 335.0), (-325.0, -335.0)):
        for o in obs:
            p = o.matrix_world.translation
            u, v = GA.to_uv(-p.x, -p.y)
            if abs(float(v) - v_src) > 1.0 or abs(float(u)) > 1.0:
                continue
            c = o.copy(); coll.objects.link(c)
            x0, z0 = GA.to_xz(0.0, v_src); x1, z1 = GA.to_xz(0.0, v_dst)
            dy = float(np.interp(v_dst, R['vs'], R['y']) - np.interp(v_src, R['vs'], R['y']))
            c.location = c.location + Vector((-(float(x1) - float(x0)), -(float(z1) - float(z0)), dy))
            k += 1
    print('[after] slab gaps filled', k, flush=True)


def delete_root(name):
    k = 0
    for o in list(bpy.data.collections['Base'].objects):
        if o.get('root') == name:
            bpy.data.objects.remove(o); k += 1
    return k


def move_root(name, du_dv=None, to_uv=None, keep_rot=True):
    obs = [o for o in bpy.data.collections['Base'].objects if o.get('root') == name]
    if not obs:
        return 0
    p0 = obs[0].matrix_world.translation.copy()
    u0, v0 = GA.to_uv(-p0.x, -p0.y)
    tu, tv = to_uv
    x1, z1 = GA.to_xz(tu, tv)
    y1 = float(gy(x1, z1)[0])
    off = Vector((-float(x1), -float(z1), y1)) - Vector((p0.x, p0.y, p0.z))
    for o in obs:
        o.location += off
    return len(obs)


def copy_root(name, to_uv, coll, yaw_deg=0.0):
    obs = [o for o in bpy.data.collections['Base'].objects if o.get('root') == name]
    if not obs:
        return 0
    p0 = obs[0].matrix_world.translation.copy()
    x1, z1 = GA.to_xz(*to_uv)
    y1 = float(gy(x1, z1)[0])
    rot = Matrix.Rotation(math.radians(yaw_deg), 4, 'Z')
    for o in obs:
        c = o.copy(); coll.objects.link(c)
        rel = o.matrix_world.translation - p0
        c.matrix_world = Matrix.Translation(Vector((-float(x1), -float(z1), y1))) @ rot @ Matrix.Translation(rel) @ o.matrix_world.to_3x3().to_4x4()
    return len(obs)


# ---------------------------------------------------------------- trees
EDGE_W = lambda v: 49.0 + 18.0 * noise1(v, 11)
EDGE_E = lambda v: 49.0 + 18.0 * noise1(v, 23)


def cleared(u, v):
    """the corridor itself: no trees closer than the edge (40-58 m from the slabs)"""
    if GA.END_S - 12 <= v <= GA.END_N + 12:
        return abs(u) < (EDGE_W(v) if u < 0 else EDGE_E(v))
    return False


TREE_KINDS = ('Spruce', 'SpruceHC', 'Fir', 'Birch', 'Dead')
FEATHER = (2.5, 0.6)          # feathered edge: height allowed at the edge line, growth per metre away from it
_PH = {}


def proto_height(col):
    if col.name not in _PH:
        zs = [(o.matrix_world @ Vector(b)).z for o in col.objects for b in o.bound_box]
        _PH[col.name] = max(zs) if zs else 0.0
    return _PH[col.name]


def tree_cap(u, v, ground):
    """height a tree may have above its own ground: in the corridor's side zones a feathered edge (low at the edge line,
    growing 0.6 m per metre into the forest); beyond the ends the approach surface (1:20 from 30 m past the threshold, the
    threshold's height; CAP 793 / ICAO code 1) inside a widening funnel, the feathered edge outside it"""
    if GA.END_S <= v <= GA.END_N:
        e = EDGE_W(v) if u < 0 else EDGE_E(v)
        return FEATHER[0] + FEATHER[1] * (abs(u) - e)
    if v < GA.END_S:
        d_thr, y_thr, d_end = GA.PAVE_V0 - v, float(np.interp(GA.PAVE_V0, R['vs'], R['y'])), GA.END_S - v
    else:
        d_thr, y_thr, d_end = v - GA.PAVE_V1, float(np.interp(GA.PAVE_V1, R['vs'], R['y'])), v - GA.END_N
    surf = y_thr + 0.05 * max(d_thr - 30.0, 0.0)
    cap = surf - ground
    hw = 52.0 + 0.2 * d_end
    lat = abs(u) - hw
    length = 205.0 if v < GA.END_S else 165.0          # the clearing asked for (QUESTIONS_2 7): regrowth 1 -> 6 m over it
    if lat <= 0 and d_end < length:
        cap = min(cap, 1.0 + 5.0 * d_end / length)
    if lat > 0:
        cap = max(cap, FEATHER[0] + FEATHER[1] * lat)
    return cap


def in_funnel(u, v):
    """the approach clearings asked for (QUESTIONS_2 7): 200 m south, 165 m north, widening from the corridor"""
    if v < GA.END_S:
        d = GA.END_S - v
        return d < 205.0 and abs(u) < 52.0 + 0.2 * d + 6.0 * noise1(v, 31)
    if v > GA.END_N:
        d = v - GA.END_N
        return d < 165.0 and abs(u) < 52.0 + 0.2 * d + 6.0 * noise1(v, 37)
    return False


def edit_trees(coll_new):
    tc = bpy.data.collections['Trees']
    stump = bpy.data.collections.get('Tree_Stump')
    removed = moved = stumped = 0
    for o in list(tc.objects):
        x, z = -o.location.x, -o.location.y
        u, v = GA.to_uv(x, z)
        u, v = float(u), float(v)
        d = float(ddelta(x, z)[0])
        Uh, Vh = GA.hangar_frame(x, z)
        on_hill = abs(Uh) < 32 and -34 < Vh < 8
        if on_hill:
            if Vh > -4.0:                               # the facade, the banks, the apron: none
                bpy.data.objects.remove(o); removed += 1
                continue
            o.location.z += d; moved += 1               # the old trees on the hill stay, on the new ground
            continue
        if cleared(u, v) or abs(d) > 4.0 or in_funnel(u, v):
            col = o.instance_collection
            name = col.name[5:] if col is not None else ''
            big = name.startswith(TREE_KINDS) and proto_height(col) * o.scale.z > 8.0
            if in_funnel(u, v) and big and stump is not None and RNG.random() < 0.35:
                o.instance_collection = stump              # the clearing: stumps where the grown trees stood
                s_ = float(RNG.uniform(0.8, 1.3)); o.scale = (s_, s_, s_)
                o.location.z += d; stumped += 1
                continue
            bpy.data.objects.remove(o); removed += 1
            continue
        if abs(d) > 0.01:
            o.location.z += d; moved += 1
    print('[after] trees removed', removed, 're-seated', moved, 'stumps in the clearings', stumped, flush=True)


ADDED = []        # the trees this concept adds (for the Unity package): proto, Unity x, z, rotation (Unity, rad), width, height


def add_tree(proto, x, z, scale, coll, yaw=None, sv=None):
    col = bpy.data.collections.get('Tree_' + proto)
    if col is None:
        return None
    e = bpy.data.objects.new('T_' + proto, None)
    e.instance_type = 'COLLECTION'; e.instance_collection = col
    e.location = B(float(x), float(z), float(gy(x, z)[0]) - 0.05)
    e.rotation_euler = (0, 0, float(RNG.uniform(0, 6.283)) if yaw is None else yaw)
    e.scale = (scale, scale, scale * (sv if sv else float(RNG.uniform(0.92, 1.08))))
    coll.objects.link(e)
    ADDED.append([proto, round(float(x), 3), round(float(z), 3), round(-float(e.rotation_euler.z), 4), round(float(e.scale.x), 4), round(float(e.scale.z), 4)])
    return e


def young_growth():
    tc = bpy.data.collections['Trees']
    n = {}
    def put(proto, u, v, s):
        x, z = GA.to_xz(u, v)
        if add_tree(proto, float(x), float(z), s, tc) is not None:
            n[proto] = n.get(proto, 0) + 1
    young = [('Fir_4', 0.45, 0.95, 4), ('Fir_7', 0.45, 0.85, 3), ('Spruce_13', 0.3, 0.55, 2), ('Birch_13', 0.3, 0.5, 1),
             ('Bush_1', 0.6, 1.0, 2), ('Bush_2', 0.6, 1.0, 2)]
    wts = np.array([w[3] for w in young], float); wts /= wts.sum()
    # the forest edge: a dense hedge of young spruce (4-8 m) in two rows in front of the old forest, birch now and then
    hedge = [('Fir_4', 0.75, 1.25, 5), ('Fir_7', 0.6, 1.0, 4), ('Spruce_13', 0.3, 0.5, 2), ('Birch_13', 0.35, 0.55, 1)]
    hw_ = np.array([h[3] for h in hedge], float); hw_ /= hw_.sum()
    def hedge_at(side, u_edge, v, rows=((-1.8, 0.85), (-4.2, 0.6))):
        for off, prob in rows:
            if RNG.random() < prob:
                p, a_, b_, _ = hedge[RNG.choice(len(hedge), p=hw_)]
                put(p, side * (u_edge + off), v + RNG.uniform(-0.8, 0.8), RNG.uniform(a_, b_))
    for side in (-1, 1):
        for v in np.arange(GA.END_S - 10, GA.END_N + 10, 1.7):
            e = EDGE_W(v) if side < 0 else EDGE_E(v)
            hedge_at(side, e, v + RNG.uniform(-0.5, 0.5))
        # along the clearings' sides
        for v in np.arange(GA.END_S - 205, GA.END_S - 10, 1.9):
            d = GA.END_S - v
            hedge_at(side, 52.0 + 0.2 * d + 6.0 * noise1(v, 31), v)
        for v in np.arange(GA.END_N + 10, GA.END_N + 165, 1.9):
            d = v - GA.END_N
            hedge_at(side, 52.0 + 0.2 * d + 6.0 * noise1(v, 37), v)
    # the hangar's hill: spruces on its top and shoulders, bushes
    for k in range(14):
        Uh = RNG.uniform(-19, 19); Vh = RNG.uniform(-12, -3.0)
        c, s = math.cos(math.radians(GA.HANGAR['yaw'])), math.sin(math.radians(GA.HANGAR['yaw']))
        x = GA.HANGAR['x'] + Uh * c + Vh * s; z = GA.HANGAR['z'] - Uh * s + Vh * c
        u, v = GA.to_uv(x, z)
        r = RNG.random()
        if r < 0.45:
            put('Fir_4', float(u), float(v), RNG.uniform(0.6, 1.1))
        elif r < 0.7:
            put('Fir_7', float(u), float(v), RNG.uniform(0.5, 0.9))
        elif r < 0.85:
            put('Spruce_13', float(u), float(v), RNG.uniform(0.35, 0.6))
        else:
            put(['Bush_1', 'Bush_2'][RNG.integers(2)], float(u), float(v), RNG.uniform(0.6, 1.0))
    for k in range(6):
        side = 1 if k % 2 else -1
        Uh = side * RNG.uniform(21.5, 25.0); Vh = RNG.uniform(0.5, 4.0)
        c, s = math.cos(math.radians(GA.HANGAR['yaw'])), math.sin(math.radians(GA.HANGAR['yaw']))
        x = GA.HANGAR['x'] + Uh * c + Vh * s; z = GA.HANGAR['z'] - Uh * s + Vh * c
        u, v = GA.to_uv(x, z)
        put(['Fir_4', 'Bush_1', 'Bush_2'][k % 3], float(u), float(v), RNG.uniform(0.5, 0.8))
    print('[after] young growth', n, flush=True)


# ---------------------------------------------------------------- snow banks, piles, stripes, caps
def windrows(coll):
    mat = mat_snow()
    vs_ = np.arange(GA.END_S + 8, GA.END_N - 4, 1.0)
    gaps = {1: [(176.0, 224.0)], -1: [(GA.PAD['v0'] - 6, GA.PAD['v1'] + 8), (296.0, 342.0)]}
    k = 0
    for side in (-1, 1):
        ok = np.ones(len(vs_), bool)
        for a, b in gaps[side]:
            ok &= ~((vs_ > a) & (vs_ < b))
        # runs
        runs, cur = [], []
        for v, o in zip(vs_, ok):
            if o:
                cur.append(v)
            elif cur:
                runs.append(cur); cur = []
        if cur:
            runs.append(cur)
        for run in runs:
            if len(run) < 4:
                continue
            v = np.array(run)
            # the plough's windrows, about 1 m (QUESTIONS_2 1), lumpy, greyed on the runway side
            h = 1.0 + 0.45 * noise1(v, 50 + side, ((23.0, 1.0), (9.0, 0.6), (4.0, 0.3)))
            taper = np.minimum(1, np.minimum(v - v[0], v[-1] - v) / 5.0 + 0.25)
            w = 3.4 + 0.8 * noise1(v, 60 + side, ((17.0, 1.0), (7.0, 0.5)))
            uc = side * (13.5 + 0.3 * noise1(v, 70 + side))
            bank(f'Windrow_{side:+d}_{k}', np.stack([uc, v], 1), w, h * taper, inner=side, coll=coll, mat=mat, lump_seed=k + 3,
                 dirt_inner=0.95)
            k += 1
    # apron sides and the pad's outer edge
    c, s = math.cos(math.radians(GA.HANGAR['yaw'])), math.sin(math.radians(GA.HANGAR['yaw']))
    for sideh in (-1, 1):
        Vh = np.arange(14.0, 33.0, 1.0)
        Uh = np.full(len(Vh), sideh * 22.2)
        x = GA.HANGAR['x'] + Uh * c + Vh * s; z = GA.HANGAR['z'] - Uh * s + Vh * c
        u, v = GA.to_uv(x, z)
        h = (0.6 + 0.25 * noise1(Vh, 80 + sideh)) * np.minimum(1, np.minimum(Vh - 14, 33 - Vh) / 4 + 0.3)
        bank(f'ApronBank_{sideh:+d}', np.stack([u, v], 1), 3.2, h, inner=sideh, coll=coll, mat=mat, lump_seed=90 + sideh)
    vp = np.arange(GA.PAD['v0'] + 6, GA.PAD['v1'] - 4, 1.0)
    up = np.full(len(vp), -53.5)
    hp = (0.55 + 0.25 * noise1(vp, 95)) * np.minimum(1, np.minimum(vp - vp[0], vp[-1] - vp) / 5 + 0.3)
    bank('PadBank', np.stack([up, vp], 1), 3.4, hp, inner=-1, coll=coll, mat=mat, lump_seed=97)
    # plough dumps at the ends (beyond the threshold lights, off the axis) and a few by the apron
    piles = []
    for i, ((u, v), r, h) in enumerate(piles):
        blob(f'SnowPile_{i}', (u, v), r, h, coll, mat, seed=200 + i, squash_v=0.75, yaw=RNG.uniform(0, 3))
    print('[after] windrows', k, flush=True)


def threshold_stripes(coll):
    mat = bpy.data.materials.new('M_AF_StripeSnow'); mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    pb = N['Principled BSDF']; pb.inputs['Roughness'].default_value = 0.8
    snow, geo = snow_tex_node(N, L, 2.0)
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.3; nz.inputs['Detail'].default_value = 3.0
    L.new(geo.outputs['Position'], nz.inputs['Vector'])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.42; mr.inputs['From Max'].default_value = 0.6
    L.new(nz.outputs['Fac'], mr.inputs['Value'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    L.new(mr.outputs['Result'], mx.inputs['Factor']); mx.inputs['A'].default_value = (0.86, 0.86, 0.84, 1)
    sb = N.new('ShaderNodeMix'); sb.data_type = 'RGBA'; sb.blend_type = 'MULTIPLY'; sb.inputs['Factor'].default_value = 1.0
    L.new(snow, sb.inputs['A']); sb.inputs['B'].default_value = (1.12, 1.12, 1.15, 1)
    L.new(sb.outputs['Result'], mx.inputs['B'])
    L.new(mx.outputs['Result'], pb.inputs['Base Color'])
    S.fog_wrap(mat, pb.outputs['BSDF'])
    for name, v0, v1 in (('Stripe_S', GA.PAVE_V0 + 4.0, GA.PAVE_V0 + 6.0), ('Stripe_N', GA.PAVE_V1 - 6.0, GA.PAVE_V1 - 4.0)):
        verts, faces = [], []
        us = np.linspace(-8.4, 8.4, 15)
        for v in (v0, v1):
            for u in us:
                verts.append(uvB(u, v, slab_top(u, v) + 0.012))
        nU = len(us)
        for i in range(nU - 1):
            faces.append((i, i + 1, i + 1 + nU, i + nU))
        mesh_obj(name, verts, faces, mat, coll, smooth=False)


_SLABS = None


def slab_top(u, v):
    """top of the runway modules at (u, v): ray down onto the RWY objects"""
    global _SLABS
    dg = bpy.context.evaluated_depsgraph_get()
    p = uvB(u, v, 50.0)
    hit, loc, nrm, idx, ob, mtx = bpy.context.scene.ray_cast(dg, p, Vector((0, 0, -1)))
    if hit and ob is not None and ob.get('root', '').startswith('RWY'):
        return loc.z
    return float(gy_uv(u, v)[0]) + 0.05


def light_caps(coll):
    mat = mat_snow()
    k = 0
    for o in list(bpy.data.collections['Base'].objects):
        if o.get('root') != 'AF_ThresholdLight' or o.type != 'MESH':
            continue
        bb = [o.matrix_world @ Vector(b) for b in o.bound_box]
        top = max(b.z for b in bb); cx = sum(b.x for b in bb) / 8; cy = sum(b.y for b in bb) / 8
        if top - min(b.z for b in bb) < 0.2:
            continue
        x, z = -cx, -cy
        u, v = GA.to_uv(x, z)
        blob(f'LightCap_{k}', (float(u), float(v)), 0.17, 0.07, coll, mat, seed=300 + k, base=top - 0.01, res=(10, 4))
        blob(f'LightDrift_{k}', (float(u), float(v)), 0.75, 0.16, coll, mat, seed=400 + k, squash_v=0.8, res=(12, 4))
        k += 1
    print('[after] light caps', k, flush=True)


def light_rings(coll):
    """the threshold lights dug out (FAA AC 150/5200-30D: lights kept clear of snow): a low ring of thrown-up snow round
    each, the lens free"""
    mat = mat_snow()
    k = 0
    for o in list(bpy.data.collections['Base'].objects):
        if o.get('root') != 'AF_ThresholdLight' or o.type != 'MESH':
            continue
        bb = [o.matrix_world @ Vector(b) for b in o.bound_box]
        if max(b.z for b in bb) - min(b.z for b in bb) < 0.2:
            continue
        cx = sum(b.x for b in bb) / 8; cy = sum(b.y for b in bb) / 8
        u, v = GA.to_uv(-cx, -cy)
        th = np.linspace(0, 2 * math.pi, 21)
        pts = np.stack([float(u) + 0.8 * np.cos(th), float(v) + 0.8 * np.sin(th)], 1)
        bank(f'LightRing_{k}', pts, 0.6, 0.17, inner=1, coll=coll, mat=mat, base_sink=0.05, dirt_inner=0.0, lump_seed=700 + k)
        k += 1
    print('[after] light rings', k, flush=True)


def hangar_portal(coll):
    """BunkerHangar keeps its own facade and wing walls (the earth is fitted behind them in ground_after.py); the flood
    mast and the cabinet move out of the banks to the apron's sides"""
    c, s = math.cos(math.radians(GA.HANGAR['yaw'])), math.sin(math.radians(GA.HANGAR['yaw']))
    def hxz(Uh, Vh):
        return GA.HANGAR['x'] + Uh * c + Vh * s, GA.HANGAR['z'] - Uh * s + Vh * c
    for root, (Uh, Vh) in (('Flood_Mast', (25.5, 10.0)), ('Electrical_Cabinet', (-24.0, 9.5))):
        x, z = hxz(Uh, Vh)
        u, v = GA.to_uv(x, z)
        move_root(root, to_uv=(float(u), float(v)))


def hangar_drifts(coll):
    mat = mat_snow()
    c, s = math.cos(math.radians(GA.HANGAR['yaw'])), math.sin(math.radians(GA.HANGAR['yaw']))
    def huv(Uh, Vh):
        x = GA.HANGAR['x'] + Uh * c + Vh * s; z = GA.HANGAR['z'] - Uh * s + Vh * c
        u, v = GA.to_uv(x, z); return float(u), float(v)
    for side in (-1, 1):
        Uh = np.arange(8.6, 12.9, 0.6) * side
        pts = np.array([huv(a, 1.9) for a in Uh])
        h = 0.3 + 0.35 * (np.abs(Uh) - 8.6) / 4.3
        bank(f'HangarDrift_{side:+d}', pts, 2.6, h, inner=1, coll=coll, mat=mat, lump_seed=500 + side, dirt_inner=0.15)


# ---------------------------------------------------------------- the south pad: drums, generator, cabinet, windsock
def cylinder(name, r, h, n, mat, coll, loc, rot=(0, 0, 0), cap_mat=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=n, radius1=r, radius2=r, depth=h)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.location = loc; ob.rotation_euler = rot
    return ob


def box(name, size, mat, coll, loc, yaw=0.0):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.location = loc; ob.rotation_euler = (0, 0, yaw)
    return ob


def runway_yaw_blender():
    """Blender z-rotation that turns local +x onto the runway's +u"""
    x0, z0 = GA.to_xz(0, 0); x1, z1 = GA.to_xz(1, 0)
    d = B(float(x1), float(z1)) - B(float(x0), float(z0))
    return math.atan2(d.y, d.x)


# ---------------------------------------------------------------- the project's prefabs from the map export, placed anew
_MAPJ = None
_MESHCACHE = {}


def map_json():
    global _MAPJ
    if _MAPJ is None:
        _MAPJ = json.load(open(S.MAP + 'map.json', encoding='utf-8'))
    return _MAPJ


def place_prefab(name, uv, yaw, coll, idx=0, dz=0.0):
    """a copy of a prefab placed on the map (its parts as exported), at (u, v) on the after ground, turned to Blender yaw"""
    m = map_json()
    roots = [r for r in m['roots'] if r['name'].split(' (')[0] == name]
    if not roots:
        print('[after] no prefab', name, flush=True)
        return []
    r = roots[min(idx, len(roots) - 1)]
    Mr = S.mat4(r['matrix'])
    ins = [i for i in m['instances'] if i['root'] == r['key']]
    need = {i['mesh'] for i in ins if i['mesh'] not in _MESHCACHE}
    if need:
        matd = {d['name']: d for d in m['materials']}
        names = set()
        for d in m['meshes']['list']:
            if d['id'] in need:
                names.update(d.get('materials', []))
        mats = {}
        for n in names:
            mt = bpy.data.materials.get(n)
            mats[n] = mt if mt is not None else (S.game_material(matd[n]) if n in matd else None)
        _MESHCACHE.update({k: v[0] for k, v in S.load_meshes(m, need, mats).items()})
    x, z = GA.to_xz(*uv)
    y = float(gy(x, z)[0])
    Mn = Matrix.Translation(B(float(x), float(z), y + dz)) @ Matrix.Rotation(yaw, 4, 'Z')
    inv = Mr.inverted()
    obs = []
    for i in ins:
        me = _MESHCACHE.get(i['mesh'])
        if me is None:
            continue
        ob = bpy.data.objects.new(name + '_c', me)
        ob.matrix_world = Mn @ inv @ S.mat4(i['matrix'])
        ob['root'] = name + '_concept'
        coll.objects.link(ob); obs.append(ob)
    return obs


_DRUM = None


def drum_mesh():
    """FuelBarrel_Net fixed: the project's drum is a bare Unity cylinder (0.58 x 0.88 m); here a 200 l drum of the same
    size with two rolling hoops, the chimes and two bungs"""
    global _DRUM
    if _DRUM is not None:
        return _DRUM
    bm = bmesh.new()
    r, h, n = 0.29, 0.88, 20
    bmesh.ops.create_cone(bm, cap_ends=True, segments=n, radius1=r, radius2=r, depth=h - 0.03)
    for zc, rr, dd in ((-h / 2 + h / 3, r + 0.013, 0.04), (-h / 2 + 2 * h / 3, r + 0.013, 0.04), (h / 2 - 0.025, r + 0.006, 0.05),
                       (-h / 2 + 0.025, r + 0.006, 0.05)):
        g = bmesh.ops.create_cone(bm, cap_ends=True, segments=n, radius1=rr, radius2=rr, depth=dd)
        bmesh.ops.translate(bm, vec=(0, 0, zc), verts=g['verts'])
    for bx, by, br in ((0.16, 0.0, 0.032), (-0.14, 0.06, 0.022)):
        g = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=br, radius2=br, depth=0.03)
        bmesh.ops.translate(bm, vec=(bx, by, h / 2 - 0.01), verts=g['verts'])
    me = bpy.data.meshes.new('FuelDrum200'); bm.to_mesh(me); bm.free()
    me.shade_smooth()
    mat = bpy.data.materials.new('M_FuelDrum_Worn'); mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    pb = N['Principled BSDF']; pb.inputs['Roughness'].default_value = 0.55; pb.inputs['Metallic'].default_value = 0.2
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 9.0; nz.inputs['Detail'].default_value = 6.0
    cr = N.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].position = 0.55; cr.color_ramp.elements[0].color = (0.55, 0.12, 0.08, 1)      # M_FuelDrum red
    cr.color_ramp.elements[1].position = 0.72; cr.color_ramp.elements[1].color = (0.22, 0.10, 0.06, 1)      # rust
    L.new(nz.outputs['Fac'], cr.inputs['Fac'])
    L.new(S.snow_mix(mat, cr.outputs['Color']), pb.inputs['Base Color'])
    S.fog_wrap(mat, pb.outputs['BSDF'])
    me.materials.append(mat)
    _DRUM = me
    return me


def drum(name, coll, loc, rot=(0.0, 0.0, 0.0)):
    ob = bpy.data.objects.new(name, drum_mesh()); coll.objects.link(ob)
    ob.location = loc; ob.rotation_euler = rot
    return ob


def hangar_uv(Uh, Vh):
    c, s = math.cos(math.radians(GA.HANGAR['yaw'])), math.sin(math.radians(GA.HANGAR['yaw']))
    x = GA.HANGAR['x'] + Uh * c + Vh * s; z = GA.HANGAR['z'] - Uh * s + Vh * c
    u, v = GA.to_uv(x, z)
    return float(u), float(v)


def dress_nodes(coll):
    """the three places of the airfield, from the project's prefabs: the hangar's apron (cargo cases, ladder, crates,
    cable drum, yard lamps, the plane's fuel), the south hut (firewood, the fire barrel, the no-entry sign), the D1 gate"""
    ry = runway_yaw_blender()
    a0 = hangar_uv(0, 0); a1 = hangar_uv(1, 0)
    x0, z0 = GA.to_xz(*a0); x1, z1 = GA.to_xz(*a1)
    d = B(float(x1), float(z1)) - B(float(x0), float(z0))
    hy = math.atan2(d.y, d.x)                     # Blender angle of the facade's +U_h
    n = 0
    for name, (Uh, Vh), yaw in (('Cargo_Case1', (-12.6, 3.0), hy), ('Cargo_Case2', (-13.5, 3.3), hy + 0.2), ('Cargo_Case3', (-11.8, 3.9), hy - 0.3),
                                ('Cargo_Case4', (-12.7, 4.3), hy + 0.5), ('StepLadder', (9.4, 1.5), hy), ('Crates', (14.3, 3.4), hy),
                                ('Cable_Drum', (-22.6, 12.0), hy + 1.2), ('LightPole', (-21.8, 25.0), hy), ('LightPole', (21.8, 25.0), hy + math.pi)):
        n += len(place_prefab(name, hangar_uv(Uh, Vh), yaw, coll))
    for k, (Uh, Vh) in enumerate(((-18.6, 13.0), (-18.0, 13.7), (-18.9, 13.9), (-18.3, 14.6))):
        u, v = hangar_uv(Uh, Vh)
        x, z = GA.to_xz(u, v)
        drum(f'FuelDrum_Hangar_{k}', coll, B(float(x), float(z), float(gy(x, z)[0]) + 0.43))
    for name, uv, yaw in (('LogPile', (-25.8, -399.0), ry + math.pi / 2), ('FireBarrel', (-15.6, -392.2), 0.0),
                          ('Sign_NoEntry', (6.2, -389.5), ry + math.pi / 2), ('Sign_NoEntry', (-19.8, 321.0), ry - math.pi / 2)):
        n += len(place_prefab(name, uv, yaw, coll))
    print('[after] nodes dressed, parts', n, flush=True)


GEN_FBX = '/mnt/user-data/uploads/snow/Snow/Assets/Common/Items/Parts/Models/Item_BackupGenerator.fbx'
PARTS_TEX = '/mnt/user-data/uploads/snow/Snow/Assets/Common/Items/Parts/Textures/'


def import_generator(coll, loc, yaw):
    """Item_BackupGenerator (forest_parts) from the project's FBX, its two atlases, snow on top"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=GEN_FBX)
    new = [o for o in bpy.data.objects if o not in before]
    for im in bpy.data.images:                      # the FBX brings its own images with broken paths under the same names
        if im.name.startswith('T_Parts_') and os.path.exists(PARTS_TEX + im.name.split('.png')[0] + '.png'):
            im.filepath = PARTS_TEX + im.name.split('.png')[0] + '.png'
            im.reload()
    for o in new:
        for c in o.users_collection:
            c.objects.unlink(o)
        coll.objects.link(o)
        if o.name.upper().startswith('COL_'):
            o.hide_render = True
    for o in new:
        if o.type != 'MESH':
            continue
        for slot in o.material_slots:
            m = slot.material
            if m is None:
                continue
            tex = PARTS_TEX + ('T_Parts_Panel_BaseColor.png' if 'panel' in m.name.lower() else 'T_Parts_Parts_BaseColor.png')
            nm = bpy.data.materials.get('GEN_' + m.name)
            if nm is None:
                nm = bpy.data.materials.new('GEN_' + m.name); nm.use_nodes = True
                N, L = nm.node_tree.nodes, nm.node_tree.links
                pb = N['Principled BSDF']; pb.inputs['Roughness'].default_value = 0.75
                t = N.new('ShaderNodeTexImage'); t.image = S.image(tex); t.interpolation = 'Closest'
                L.new(S.snow_mix(nm, t.outputs['Color']), pb.inputs['Base Color'])
                S.fog_wrap(nm, pb.outputs['BSDF'])
            slot.material = nm
        print('[gen]', o.name, [sl.material.name if sl.material else None for sl in o.material_slots], flush=True)
    roots = [o for o in new if o.parent is None]
    for r in roots:
        r.location = loc
        r.rotation_euler = (r.rotation_euler.x, r.rotation_euler.y, yaw)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(b) for o in new if o.type == 'MESH' and not o.hide_render for b in o.bound_box]
    if pts:
        dz = loc.z - min(p.z for p in pts)
        for r in roots:
            r.location.z += dz
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(b) for o in new if o.type == 'MESH' and not o.hide_render for b in o.bound_box]
    size = (max(p.x for p in pts) - min(p.x for p in pts), max(p.y for p in pts) - min(p.y for p in pts), max(p.z for p in pts) - min(p.z for p in pts))
    return new, size, max(p.z for p in pts)


def south_pad(coll):
    """by the hut at the south entrance: FuelBarrel_Net drums (the project's prefab: Unity cylinder 0.58 x 0.88 m,
    M_FuelDrum red), Item_BackupGenerator (forest_parts) and a copy of the airfield's Electrical_Cabinet; the windsock
    beside the pad"""
    drum = mat_flat('M_FuelDrum', (0.55, 0.12, 0.08), 0.6)
    snow = mat_snow()
    ry = runway_yaw_blender()
    def P(u, v, dz=0.0):
        x, z = GA.to_xz(u, v)
        return B(float(x), float(z), float(gy(x, z)[0]) + dz)
    k = 0
    for (u, v) in ((-28.6, -390.4), (-29.3, -390.4), (-28.95, -389.8), (-27.9, -389.9), (-29.8, -389.7), (-28.3, -389.3)):
        globals()['drum'](f'FuelBarrel_Net_{k}', coll, P(u, v, 0.44 - 0.04))
        blob(f'DrumCap_{k}', (u, v), 0.25, 0.07, coll, snow, seed=600 + k, base=float(gy_uv(u, v)[0]) + 0.84, res=(10, 4))
        k += 1
    for j, (u, v, yaw) in enumerate([(-30.9, -391.2, 0.3), (-26.8, -391.4, 1.2)]):
        globals()['drum'](f'FuelBarrel_Net_{k}', coll, P(u, v, 0.27), rot=(math.pi / 2, 0, ry + yaw))
        k += 1
    gen, size, top = import_generator(coll, P(-27.6, -398.3), ry + math.pi / 2)
    n = copy_root('Electrical_Cabinet', (-27.2, -395.2), coll, yaw_deg=0.0)
    m = move_root('Windsock', to_uv=(-57.5, -344.0))
    print('[after] south pad: FuelBarrel_Net', k, 'generator parts', len(gen), 'size %.2f x %.2f x %.2f' % size,
          'cabinet parts', n, 'windsock parts', m, flush=True)


# ---------------------------------------------------------------- dry grass tufts
def tufts(coll):
    """dry grass in clumps where the snow is thin: the outer foot of the windrows, the slopes, the strip's outer edge,
    round the stumps of the clearings; clumps of 6-14 tufts, not a scatter"""
    U, V = R['U'], R['V']
    au = np.abs(U)
    gyy, gxx = np.gradient(R['N'], R['g']['step'])
    slope = np.hypot(gxx, gyy)
    w = ((au > 17.8) & (au < 20.5)) * 1.0
    w = w + (slope > 0.14) * 0.6 + ((au > 31) & (au < 38)) * 0.35
    fun = ((V < GA.END_S) & (V > GA.END_S - 205)) | ((V > GA.END_N) & (V < GA.END_N + 165))
    w = w + fun * (au < 90) * 0.7
    w = w * (au > 17.8)
    Uh, Vh = R['Uh'], R['Vh']
    w = w * ~((np.abs(Uh) < 23) & (Vh > -1) & (Vh < 37))
    w = w * ~((U < -8) & (U > -55) & (V > GA.PAD['v0'] - 6) & (V < GA.PAD['v1'] + 6))
    w = w * (au < 140)
    m = np.zeros_like(w); m[::4, ::4] = 1
    w = w * m
    idx = np.flatnonzero(w)
    K = min(len(idx), 1300)
    pick = RNG.choice(idx, size=K, replace=False, p=w.ravel()[idx] / w.ravel()[idx].sum())
    J, I = np.unravel_index(pick, w.shape)
    centres = list(zip(R['XX'][J, I], R['ZZ'][J, I]))
    X, Z = [], []
    for cx, cz in centres:
        for k in range(int(RNG.integers(6, 15))):
            X.append(cx + RNG.normal(0, 1.4)); Z.append(cz + RNG.normal(0, 1.4))
    verts, faces, tint = [], [], []
    nt = 0
    for x0, z0 in zip(X, Z):
        nclump = 1
        base_col = np.array([0.50, 0.43, 0.27]) * RNG.uniform(0.75, 1.15)
        for c in range(nclump):
            x = x0; z = z0
            y = float(gy(x, z)[0]) - 0.03
            nb = RNG.integers(4, 7)
            hgt = RNG.uniform(0.22, 0.55)
            for b in range(nb):
                a = RNG.uniform(0, 6.283); lean = RNG.uniform(0.05, 0.25) * hgt
                w = 0.025
                bx, bz = x + 0.04 * math.cos(a), z + 0.04 * math.sin(a)
                px, pz = -math.sin(a), math.cos(a)
                i0 = len(verts)
                verts.append(B(bx - px * w, bz - pz * w, y)); verts.append(B(bx + px * w, bz + pz * w, y))
                verts.append(B(bx + math.cos(a) * lean, bz + math.sin(a) * lean, y + hgt * RNG.uniform(0.8, 1.1)))
                faces.append((i0, i0 + 1, i0 + 2))
                col = base_col * RNG.uniform(0.85, 1.1)
                tint += [list(col * 0.7) + [1], list(col * 0.7) + [1], list(col) + [1]]
            nt += 1
    ob = mesh_obj('DryGrass', verts, faces, mat_grass(), coll, attrs={'tint': np.array(tint)}, smooth=False)
    print('[after] tufts', nt, 'blades', len(faces), flush=True)
    return ob


def main():
    global R
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    bpy.ops.wm.open_mainfile(filepath=argv[0])
    R = GA.compute()
    coll = bpy.data.collections.new('Concept'); bpy.context.scene.collection.children.link(coll)
    ground_after()
    nfd = delete_root('Fuel_Depot')
    print('[after] fuel depot parts removed', nfd, flush=True)
    reseat_objects()
    fill_slab_gaps(coll)
    edit_trees(coll)
    young_growth()
    for mat in bpy.data.materials:
        if 'af_runway' in mat.name.lower():
            runway_material(mat)
    bpy.context.view_layer.update()
    windrows(coll)
    threshold_stripes(coll)
    light_caps(coll)
    hangar_drifts(coll)
    south_pad(coll)
    hangar_portal(coll)
    dress_nodes(coll)
    tufts(coll)
    json.dump(ADDED, open(os.path.join(D, 'data', 'trees_added.json'), 'w'))
    bpy.ops.wm.save_as_mainfile(filepath=argv[1])
    print('[after] saved', argv[1], 'trees added', len(ADDED), flush=True)


if __name__ == '__main__':
    main()
