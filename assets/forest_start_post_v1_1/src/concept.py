"""Start post concept (28.10.2026): the post at the ZoneGate (start_scene, map export 28.10 21:41) brought to the round-3
targets (docs/gdd/locations/start_post: concept_v3 arrive_wache + night_wache, QUESTIONS_3 all accepted):
- deep winter: the road ploughed, low dirty berms and two darker wheel tracks instead of the white road; old snow on the
  pad, drifts on the lee (north-east, +u) sides, caps on everything;
- the post on the lane: a Wachhaus of grey rendered brick (flat roof, big warm window to the barrier and the road, door
  to the road, stove pipe with smoke, lamp over the door) in place of the booth; the barrier turned (pivot at the
  house, arm over the road) and set in front of the window; zone fence plates; the RADIOOBSERVATORIUM sign on the right
  verge facing the players; the second pad lamp gone, the first one dead;
- the players' van (olive, hazard lights on) on the road where VanVehicle spawns, the red estate snowed in to the windows;
- the ground: the drop at the pad's end and the road's embankment sides softened.

python3.11 -I concept.py <out.blend> <views|-> [spp] [w h]"""
import bpy, bmesh, math, json, os, sys, random
import numpy as np
from mathutils import Vector, Matrix

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import start_scene as S
import frame as F
from scipy import ndimage

MAP = S.MAP
GT = S.GROUND_TEX
TEX = MAP + 'textures/'
OWN = os.path.join(D, 'tex') + '/'
VAN = '/mnt/user-data/uploads/snow/Snow/Assets/Van/'
RNG = random.Random(2910)
G = None            # ground heights after the terrain edit (frame.Ground with .h replaced)
COL = None
MAT = {}
MAPJ = None
CENTRE = None       # road centreline: (v array, u array)
V0, V1 = -72.0, None
SNOWH = []
ROADGRID = {}      # the road strip's grid (pkg_src/export_pkg.py bakes its texture from it)

HOUSE = dict(u=-8.5, v=-3.4, hx=1.9, hy=2.0)      # Wachhaus centre and half sizes (local x = +u, y = +v)
VANP = (1.0, -14.0)
BARRIER = (-3.15, -4.0)
SIGN = (5.1, -5.0)


# ------------------------------------------------------------------ placing
def P(u, v, h=None):
    x, y = F.uv_to_blender_xy(u, v)
    if h is None:
        h = float(G.at(u, v))
    return Vector((float(x), float(y), float(h)))


def put(ob, u, v, h=None, theta=0.0, col=None):
    ob.location = P(u, v, h)
    ob.rotation_euler = (0.0, 0.0, F.ROTZ + math.radians(theta))
    (col or COL).objects.link(ob)
    return ob


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ materials
_mats = {}


def _base(name):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    return mat, N, L, N['Principled BSDF']


def tex_mat(name, tex, tint=(1, 1, 1), scale=2.0, rough=0.85, snow=True, metal=0.0):
    if name in _mats:
        return _mats[name]
    mat, N, L, pb = _base(name)
    pb.inputs['Roughness'].default_value = rough; pb.inputs['Metallic'].default_value = metal
    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / scale, 1 / scale, 1 / scale)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    t = N.new('ShaderNodeTexImage'); t.image = S.image(tex); t.interpolation = 'Closest'
    t.projection = 'BOX'; t.projection_blend = 0.0
    L.new(mp.outputs['Vector'], t.inputs['Vector'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
    L.new(t.outputs['Color'], mx.inputs['A']); mx.inputs['B'].default_value = (*tint, 1)
    col = mx.outputs['Result']
    if snow:
        col = S.snow_mix(mat, col)
    L.new(col, pb.inputs['Base Color'])
    S.fog_wrap(mat, pb.outputs['BSDF'])
    _mats[name] = mat
    return mat


def uv_mat(name, tex, tint=(1, 1, 1), rough=0.8, snow=False, emit=None, strength=0.0, alpha=None):
    """image on the mesh's own UVs (van parts, plates)"""
    if name in _mats:
        return _mats[name]
    mat, N, L, pb = _base(name)
    pb.inputs['Roughness'].default_value = rough
    t = N.new('ShaderNodeTexImage'); t.image = S.image(tex); t.interpolation = 'Closest'
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
    L.new(t.outputs['Color'], mx.inputs['A']); mx.inputs['B'].default_value = (*tint, 1)
    col = mx.outputs['Result']
    if snow:
        col = S.snow_mix(mat, col)
    L.new(col, pb.inputs['Base Color'])
    if emit is not None:
        pb.inputs['Emission Color'].default_value = (*emit, 1); pb.inputs['Emission Strength'].default_value = strength
    if alpha is not None:
        pb.inputs['Alpha'].default_value = alpha
    S.fog_wrap(mat, pb.outputs['BSDF'])
    _mats[name] = mat
    return mat


def col_mat(name, rgb, rough=0.7, snow=True, metal=0.0, emit=None, strength=1.0, alpha=None):
    if name in _mats:
        return _mats[name]
    mat, N, L, pb = _base(name)
    pb.inputs['Roughness'].default_value = rough; pb.inputs['Metallic'].default_value = metal
    rgbn = N.new('ShaderNodeRGB'); rgbn.outputs[0].default_value = (*rgb, 1)
    col = rgbn.outputs[0]
    if snow:
        col = S.snow_mix(mat, col)
    L.new(col, pb.inputs['Base Color'])
    if emit is not None:
        pb.inputs['Emission Color'].default_value = (*emit, 1); pb.inputs['Emission Strength'].default_value = strength
    if alpha is not None:
        pb.inputs['Alpha'].default_value = alpha
    S.fog_wrap(mat, pb.outputs['BSDF'])
    _mats[name] = mat
    return mat


def planar(N, L, geo):
    """the terrain's own world mapping of the ground layers: Unity x / 2, z / 2"""
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], sep.inputs['Vector'])
    comb = N.new('ShaderNodeCombineXYZ')
    for ax in ('X', 'Y'):
        m_ = N.new('ShaderNodeMath'); m_.operation = 'MULTIPLY'; m_.inputs[1].default_value = -0.5
        L.new(sep.outputs[ax], m_.inputs[0]); L.new(m_.outputs['Value'], comb.inputs[ax])
    return comb.outputs['Vector']


def gtex(N, L, vec, name, tint=1.0):
    t = N.new('ShaderNodeTexImage'); t.image = S.image(GT + name); t.interpolation = 'Closest'
    L.new(vec, t.inputs['Vector'])
    if tint == 1.0:
        return t.outputs['Color']
    m = N.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = 'MULTIPLY'; m.inputs['Factor'].default_value = 1.0
    L.new(t.outputs['Color'], m.inputs['A']); m.inputs['B'].default_value = (tint, tint, tint, 1)
    return m.outputs['Result']


def mix_by(N, L, a, b, fac_socket):
    m = N.new('ShaderNodeMix'); m.data_type = 'RGBA'
    L.new(fac_socket, m.inputs['Factor']); L.new(a, m.inputs['A']); L.new(b, m.inputs['B'])
    return m.outputs['Result']


def road_mat():
    """the ploughed road: fresh snow (Floor), packed lane (Track), wheel tracks (Ruts over Track), plough spray (Gravel)
    by the point attributes wp, wr, wd"""
    mat, N, L, pb = _base('C_Road')
    pb.inputs['Roughness'].default_value = 0.8
    geo = N.new('ShaderNodeNewGeometry'); vec = planar(N, L, geo)
    floor = gtex(N, L, vec, 'T_GR_Floor_A.png', 1.04)
    track = gtex(N, L, vec, 'T_GR_Track_A.png', 0.98)
    ruts = gtex(N, L, vec, 'T_GR_Ruts_A.png', 1.12)
    grav = gtex(N, L, vec, 'T_GR_Gravel_A.png', 0.86)
    at = {}
    for k in ('wp', 'wr', 'wd'):
        a = N.new('ShaderNodeAttribute'); a.attribute_name = k; at[k] = a.outputs['Fac']
    col = mix_by(N, L, floor, track, at['wp'])
    col = mix_by(N, L, col, ruts, at['wr'])
    col = mix_by(N, L, col, grav, at['wd'])
    L.new(col, pb.inputs['Base Color'])
    S.fog_wrap(mat, pb.outputs['BSDF'])
    _mats['C_Road'] = mat
    return mat


def snow_surface_mat(name='C_Snow', dirt=True, bright=1.06):
    if name in _mats:
        return _mats[name]
    mat, N, L, pb = _base(name)
    pb.inputs['Roughness'].default_value = 0.78
    geo = N.new('ShaderNodeNewGeometry'); vec = planar(N, L, geo)
    col = gtex(N, L, vec, 'T_GR_Floor_A.png', bright)
    if dirt:
        d = gtex(N, L, vec, 'T_GR_Track_A.png', 1.05)
        a = N.new('ShaderNodeAttribute'); a.attribute_name = 'dirt'
        col = mix_by(N, L, col, d, a.outputs['Fac'])
    L.new(col, pb.inputs['Base Color'])
    S.fog_wrap(mat, pb.outputs['BSDF'])
    _mats[name] = mat
    return mat


def smoke_mat():
    mat = bpy.data.materials.new('C_Smoke'); mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    for n in list(N):
        if n.type == 'BSDF_PRINCIPLED':
            N.remove(n)
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')
    vol = N.new('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (0.86, 0.86, 0.88, 1); vol.inputs['Anisotropy'].default_value = 0.3
    tc = N.new('ShaderNodeTexCoord')
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.6; nz.inputs['Detail'].default_value = 3
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; L.new(tc.outputs['Object'], ln.inputs[0])
    fall = N.new('ShaderNodeMapRange'); fall.inputs['From Min'].default_value = 1.0; fall.inputs['From Max'].default_value = 0.3
    L.new(ln.outputs['Value'], fall.inputs['Value'])
    con = N.new('ShaderNodeMapRange'); con.inputs['From Min'].default_value = 0.42; con.inputs['From Max'].default_value = 0.72
    L.new(nz.outputs['Fac'], con.inputs['Value'])
    m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; L.new(con.outputs['Result'], m1.inputs[0]); L.new(fall.outputs['Result'], m1.inputs[1])
    at = N.new('ShaderNodeAttribute'); at.attribute_type = 'OBJECT'; at.attribute_name = 'dens'
    m2 = N.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; L.new(m1.outputs['Value'], m2.inputs[0]); L.new(at.outputs['Fac'], m2.inputs[1])
    L.new(m2.outputs['Value'], vol.inputs['Density'])
    L.new(vol.outputs['Volume'], out.inputs['Volume'])
    return mat


def mats():
    M = {}
    M['plaster'] = tex_mat('C_Plaster', OWN + 'T_SP_Plaster_px.png', (1.0, 1.0, 1.0), scale=4.0, rough=0.9)
    M['plinth'] = tex_mat('C_Plinth', TEX + 'T_Concrete_A_px.png', (0.55, 0.54, 0.52), scale=1.5)
    M['concrete'] = tex_mat('C_Concrete', TEX + 'T_Concrete_A_px.png', (0.78, 0.78, 0.76), scale=1.5)
    M['roofedge'] = col_mat('C_RoofEdge', (0.07, 0.07, 0.075), rough=0.6)
    M['frame'] = col_mat('C_Frame', (0.13, 0.085, 0.05), rough=0.6, snow=False)
    M['door'] = tex_mat('C_Door', TEX + 'T_WoodSiding_A.jpg', (0.40, 0.50, 0.44), scale=1.0, rough=0.7, snow=False)
    M['glass'] = col_mat('C_WinGlass', (0.05, 0.055, 0.06), rough=0.12, snow=False, alpha=0.42)
    M['glow'] = col_mat('C_WinGlow', (0.3, 0.15, 0.05), rough=0.3, snow=False, emit=(1.0, 0.52, 0.18), strength=4.0, alpha=0.62)
    M['bulb'] = col_mat('C_Bulb', (1.0, 0.85, 0.6), snow=False, emit=(1.0, 0.78, 0.45), strength=30.0)
    M['stoveglow'] = col_mat('C_StoveGlow', (0.9, 0.3, 0.05), snow=False, emit=(1.0, 0.35, 0.06), strength=12.0)
    M['iron'] = col_mat('C_Iron', (0.05, 0.05, 0.05), rough=0.5, metal=0.4, snow=False)
    M['steel'] = col_mat('C_SteelGrey', (0.30, 0.31, 0.32), rough=0.5, metal=0.3)
    M['wood'] = tex_mat('C_Wood', TEX + 'T_WoodSiding_A.jpg', (0.55, 0.45, 0.35), scale=1.0, snow=False)
    M['woodsnow'] = tex_mat('C_WoodSnow', TEX + 'T_WoodSiding_A.jpg', (0.55, 0.45, 0.35), scale=1.0, snow=True)
    M['blanket'] = col_mat('C_Blanket', (0.16, 0.18, 0.14), rough=0.9, snow=False)
    M['red'] = col_mat('C_JerryRed', (0.55, 0.06, 0.03), rough=0.5, snow=False)
    M['paper'] = col_mat('C_Paper', (0.75, 0.73, 0.66), rough=0.9, snow=False)
    M['coat'] = col_mat('C_Coat', (0.12, 0.14, 0.10), rough=0.9, snow=False)
    M['snow'] = snow_surface_mat('C_Snow', dirt=True)
    M['snow_clean'] = snow_surface_mat('C_SnowClean', dirt=False, bright=1.08)
    M['ice'] = col_mat('C_Ice', (0.72, 0.8, 0.88), rough=0.12, snow=False)
    M['soot'] = col_mat('C_Soot', (0.05, 0.045, 0.04), rough=0.9, snow=False)
    M['road'] = road_mat()
    M['plate'] = uv_mat('C_Plate', OWN + 'T_SP_Plate_px.png', rough=0.4)
    M['plateback'] = col_mat('C_PlateBack', (0.55, 0.56, 0.56), rough=0.5)
    M['smoke'] = smoke_mat()
    M['frost'] = col_mat('C_Frost', (0.78, 0.82, 0.86), rough=0.6, snow=False, alpha=0.75)
    return M


# ------------------------------------------------------------------ mesh builder
class MB:
    def __init__(self, name, mats):
        self.name, self.mats = name, list(mats)
        self.bm = bmesh.new()

    def _mi(self, faces, mi):
        for f in faces:
            f.material_index = mi

    def box(self, a, b, mi=0):
        """axis-aligned box from corner a to corner b (local x, y, z)"""
        a, b = Vector(a), Vector(b)
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        M = Matrix.Translation((a + b) / 2) @ Matrix.Diagonal((abs(b.x - a.x), abs(b.y - a.y), abs(b.z - a.z), 1.0))
        bmesh.ops.transform(self.bm, matrix=M, verts=r['verts'])
        self._mi({f for v in r['verts'] for f in v.link_faces}, mi)
        return r['verts']

    def cbox(self, c, s, mi=0, rz=0.0, rx=0.0, ry=0.0):
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        M = (Matrix.Translation(Vector(c)) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(ry, 4, 'Y') @ Matrix.Rotation(rx, 4, 'X')
             @ Matrix.Diagonal((s[0], s[1], s[2], 1.0)))
        bmesh.ops.transform(self.bm, matrix=M, verts=r['verts'])
        self._mi({f for v in r['verts'] for f in v.link_faces}, mi)
        return r['verts']

    def cyl(self, c, r, h, mi=0, seg=12, r2=None, axis='Z'):
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                                    radius2=(r if r2 is None else r2), depth=h)
        rot = {'Z': Matrix.Identity(4), 'X': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'Y': Matrix.Rotation(math.pi / 2, 4, 'X')}[axis]
        bmesh.ops.transform(self.bm, matrix=Matrix.Translation(Vector(c)) @ rot, verts=res['verts'])
        self._mi({f for v in res['verts'] for f in v.link_faces}, mi)
        return res['verts']

    def rod(self, a, b, r, mi=0, seg=6):
        a, b = Vector(a), Vector(b)
        d = b - a
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=d.length)
        q = d.to_track_quat('Z', 'Y')
        bmesh.ops.transform(self.bm, matrix=Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4(), verts=res['verts'])
        self._mi({f for v in res['verts'] for f in v.link_faces}, mi)

    def done(self, smooth=False):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me); self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        if smooth:
            me.shade_smooth()
        return bpy.data.objects.new(self.name, me)


# ------------------------------------------------------------------ the scene's objects by root
def objs_of(root):
    return [o for o in bpy.data.objects if o.get('root') == root]


def root_pos(root):
    r = next(r for r in MAPJ['roots'] if r['name'] == root and F.unity_to_uv(-r['matrix'][3], -r['matrix'][7])[0] ** 2 < 70 ** 2)
    t = r['matrix']
    return Vector((t[3], t[7], t[11]))


def move_root(root, u, v, dyaw_frame=0.0, dz=0.0):
    """move every mesh of a placed prefab: about its root, turned by dyaw (frame yaw, clockwise from +v) to (u, v)"""
    old = root_pos(root)
    ou, ov = F.blender_to_uv(old.x, old.y)
    lift = old.z - float(G0.at(float(ou), float(ov)))
    new = P(u, v, float(G.at(u, v)) + lift + dz)
    M = Matrix.Translation(new) @ Matrix.Rotation(-math.radians(dyaw_frame), 4, 'Z') @ Matrix.Translation(-old)
    for o in objs_of(root):
        o.matrix_world = M @ o.matrix_world
    return new


def remove_root(root):
    for o in objs_of(root):
        bpy.data.objects.remove(o)


# ------------------------------------------------------------------ terrain
G0 = None


def terrain():
    """soften the ground: the 1.5-2 m drop at the pad's far end, the road's steep embankment sides; fill the right
    shoulder under the sign; lower the ground 12 cm under the new road strip (it lies on top)"""
    global G
    g = json.load(open(os.path.join(D, 'data', 'ground_crop.json')))
    H = G0.h.copy()
    cz, cx = H.shape
    xs = G0.x0 + np.arange(cx) * G0.s; zs = G0.z0 + np.arange(cz) * G0.s
    X, Z = np.meshgrid(xs, zs)
    U, V = F.unity_to_uv(X, Z)
    Uc = np.interp(V, CENTRE[0], CENTRE[1])
    Sx = U - Uc
    st = G0.s

    def feather(u0, u1, v0, v1, f):
        return (smoothstep(u0 - f, u0, U) * (1 - smoothstep(u1, u1 + f, U)) * smoothstep(v0 - f, v0, V) * (1 - smoothstep(v1, v1 + f, V)))
    keep_bed = smoothstep(4.0, 5.2, np.abs(Sx))
    # 1. the pad's far end and the hollow beside the road: a long gentle fall instead of a step
    w = feather(-17.0, -4.2, -36.0, -21.0, 3.0) * keep_bed
    Hs = ndimage.gaussian_filter(H, 3.0 / st)
    H1 = H * (1 - w) + Hs * w
    # 2. the embankment sides: no sharp crease at the road edge
    w2 = (feather(3.6, 12.0, -75.0, 14.0, 2.0) + feather(-12.0, -3.6, -75.0, -24.0, 2.0) * (1 - w)) * keep_bed
    Hs2 = ndimage.gaussian_filter(H1, 1.3 / st)
    H1 = H1 * (1 - np.clip(w2, 0, 1)) + Hs2 * np.clip(w2, 0, 1)
    # 3. the right shoulder under the sign: road level - 0.15, falling 1:2 beyond u 6.6
    fill = feather(3.4, 7.4, -7.6, -2.4, 1.2)
    Hroad = np.interp(V, CENTRE[0], CENTRE[2])
    target = Hroad - 0.15 - 0.5 * np.clip(U - 6.6, 0, None)
    H1 = np.where(fill > 0, np.maximum(H1, H1 * (1 - fill) + target * fill), H1)
    dd = H1 - H
    print('[concept] terrain: max raise %.2f m, max cut %.2f m' % (dd.max(), -dd.min()), flush=True)
    # the ground helper for everything placed from now on
    G = F.Ground(); G.h = H1
    np.save(os.path.join(D, 'data', 'ground_after.npy'), H1)
    # 4. the mesh: lowered under the road strip
    low = 0.12 * (1 - smoothstep(6.2, 6.9, np.abs(Sx))) * (V >= V0 + 1) * (V <= V1 - 0.5)
    H2 = H1 - low
    me = bpy.data.objects['Ground'].data
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    assert len(co) == H2.size
    co[:, 2] = H2.ravel()
    me.vertices.foreach_set('co', co.ravel()); me.update()


def splat_after():
    """the ground layers around the post under snow: the gravel / asphalt / track strips of the old pad and its
    approach and the rock paint of its cut slopes go to snow (Floor 86 %, FloorDark 14 %)"""
    sp = np.load(os.path.join(D, 'data', 'tile_splat.npy')).astype(np.float32)
    n = sp.shape[0]
    c = (np.arange(n) + 0.5) * 600.0 / n
    X, Z = np.meshgrid(-600.0 + c, c)                       # cols x, rows z bottom-up (tile 0_2)
    U, V = F.unity_to_uv(X, Z)
    w = smoothstep(-30, -24, U) * (1 - smoothstep(12, 17, U)) * smoothstep(-52, -46, V) * (1 - smoothstep(20, 26, V))
    tgt = np.zeros(8, np.float32); tgt[0] = 0.86; tgt[1] = 0.14
    tot = sp.sum(-1, keepdims=True)
    new = sp * (1 - w[..., None]) + tgt * tot * w[..., None]
    S.splat_png(np.clip(new.round(), 0, 255).astype(np.uint8), suffix='_after')
    me = bpy.data.objects['Ground'].data
    me.materials[0] = S.ground_material('_after')
    print('[concept] ground layers: snow over %.0f m2' % (float((w > 0.5).sum()) * (600.0 / n) ** 2), flush=True)


# ------------------------------------------------------------------ the road
def centreline():
    """the road centre from the RoadNet wheel-track strips (4 strips, +-0.5..1.2 m), per metre of v"""
    global V1
    ob = next(o for o in bpy.data.objects if o.data and o.data.name.startswith('01147_ROADNET_Ruts'))
    me = ob.data
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    W = np.array(ob.matrix_world)
    co = co @ W[:3, :3].T + W[:3, 3]
    u, v = F.blender_to_uv(co[:, 0], co[:, 1])
    guess_v = [-130, -100, -80, -60, -40, -20, 0, 20, 40, 50]
    guess_u = [-6.7, -4.44, -3.39, -1.82, -0.48, 0.03, 0.0, 0.34, 1.40, 2.03]
    vs, us, hs = [], [], []
    for vv in np.arange(-90.0, 70.0, 1.0):
        gu = np.interp(vv, guess_v, guess_u)
        s = (np.abs(v - vv) < 0.75) & (np.abs(u - gu) < 2.6)
        if s.sum() < 4:
            continue
        vs.append(vv); us.append((u[s].min() + u[s].max()) / 2); hs.append(float(np.median(co[s, 2])))
    vs, us, hs = np.array(vs), ndimage.gaussian_filter1d(np.array(us), 2.0), np.array(hs)
    V1 = float(vs.max()) - 0.5
    print('[concept] road centre: v %.0f..%.0f, u at -30/0/+30: %.2f %.2f %.2f' % (vs.min(), vs.max(), *np.interp([-30, 0, 30], vs, us)), flush=True)
    return vs, us, hs


def cut_roadnet():
    """the RoadNet strips go where the new road lies (v V0..V1)"""
    n = 0
    for o in list(bpy.data.objects):
        if not (o.data and o.type == 'MESH' and o.data.name.split('.')[0] in ('01146_ROADNET_Berm', '01147_ROADNET_Ruts', '01148_ROADNET_Surface')):
            continue
        bm = bmesh.new(); bm.from_mesh(o.data)
        W = o.matrix_world
        kill = []
        for f in bm.faces:
            c = W @ f.calc_center_median()
            u, v = F.blender_to_uv(c.x, c.y)
            u, v = float(u), float(v)
            if V0 - 0.5 <= v <= V1 + 2.0 and abs(u - np.interp(v, CENTRE[0], CENTRE[1])) < 9.5:
                kill.append(f)
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        bm.to_mesh(o.data); bm.free(); n += len(kill)
    print('[concept] RoadNet faces removed:', n, flush=True)


def road():
    """the ploughed road strip: a 6 m lane (packed snow, two darker wheel tracks), a low windrow each side (0.3-0.55 m,
    dirty on the road side), a snow-filled ditch, blending into the ground 7 m out. No windrow at the gate; on the pad
    front the windrow stays (the pad is not ploughed) with a gap where the path to the door crosses it, and no ditch."""
    ss = np.arange(-7.0, 7.0001, 0.25)
    vv = np.arange(V0, V1 + 0.001, 0.4)
    nv, ns = len(vv), len(ss)
    rng = np.random.default_rng(2910)
    n1 = ndimage.gaussian_filter(rng.standard_normal((nv, ns)), (9, 2)); n1 /= n1.std() + 1e-9
    n2 = ndimage.gaussian_filter(rng.standard_normal((nv, ns)), (2.5, 1)); n2 /= n2.std() + 1e-9
    n3 = ndimage.gaussian_filter(rng.standard_normal((nv, ns)), (1.2, 0.8)); n3 /= n3.std() + 1e-9
    Sg, Vg = np.meshgrid(ss, vv)
    a = np.abs(Sg); left = Sg < 0
    uc = np.interp(vv, CENTRE[0], CENTRE[1])
    du = np.gradient(uc, vv)
    tl = np.sqrt(1 + du ** 2)
    nu_, nv_ = 1 / tl, -du / tl                         # +u side normal of the centreline
    U = uc[:, None] + Sg * nu_[:, None]; Vw = Vg + Sg * nv_[:, None]
    # lane
    h = 0.075 - 0.01 * np.minimum(a, 3.0) - 0.032 * np.exp(-((a - 0.85) / 0.24) ** 2) * (a < 2.0)
    # windrow height along the road
    Bh = 0.52 + 0.11 * n1 + 0.04 * n2
    Bh *= smoothstep(1.0, 2.8, np.abs(Vw))                              # open at the gate
    padfront = left & (Vw > -25.5) & (Vw < -1.0)
    gap = left & (np.abs(Vw + 2.5) < 1.1)
    Bh = np.where(padfront, Bh * 0.85, Bh)
    Bh = np.where(left, Bh * (0.12 + 0.88 * smoothstep(0.7, 1.4, np.abs(Vw + 2.5))), Bh)   # the door path
    rise = smoothstep(2.95, 3.6, a) ** 0.8
    fall = 1 - smoothstep(3.6, 4.85, a)
    berm = Bh * np.where(a < 3.6, rise, fall) * (1 + 0.1 * n3)
    ditch = -0.22 * np.exp(-((a - 5.35) / 0.45) ** 2) * (~padfront)
    h = h + berm + ditch
    h = h * (1 - smoothstep(6.0, 7.0, a)) + 0.02
    # weights: packed lane, wheel tracks, plough spray on the windrow's road face
    wp = 0.95 * (1 - smoothstep(2.4, 3.05, a)) * (0.9 + 0.1 * n2.clip(-1, 1))
    wr = np.clip(0.85 * np.exp(-((a - 0.85) / 0.3) ** 2) * (a < 2.0) * (0.8 + 0.2 * n3), 0, 1)
    face = smoothstep(2.85, 3.1, a) * (1 - smoothstep(3.45, 3.85, a))
    wd = np.clip(0.62 * face * (0.65 + 0.35 * n2) + 0.25 * smoothstep(2.5, 2.95, a) * (1 - smoothstep(3.0, 3.3, a)), 0, 0.85)
    wd = np.where(gap, np.maximum(wd, 0.35 * (a < 4.5) * smoothstep(2.6, 3.2, a)), wd)
    wp = np.where(gap & (a > 2.9) & (a < 4.8), np.maximum(wp, 0.5), wp)
    x, z = F.uv_to_unity(U, Vw)
    gh = G.at_unity(x, z)
    ROADGRID.update(ss=ss, vv=vv, U=U, Vw=Vw, h=h, wp=wp, wr=wr, wd=wd, x=x, z=z, gh=gh, nu=nu_, nv=nv_, uc=uc)
    co = np.stack([-x, -z, gh + h], -1).reshape(-1, 3).astype(np.float32)
    idx = np.arange(nv * ns).reshape(nv, ns)
    q = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).reshape(-1, 4)
    me = bpy.data.meshes.new('SR_Road')
    me.vertices.add(len(co)); me.vertices.foreach_set('co', co.ravel())
    me.loops.add(q.size); me.loops.foreach_set('vertex_index', q.ravel().astype(np.int32))
    me.polygons.add(len(q)); me.polygons.foreach_set('loop_start', np.arange(0, q.size, 4, dtype=np.int32))
    me.update(calc_edges=True)
    for k, arr in (('wp', wp), ('wr', wr), ('wd', wd)):
        at = me.attributes.new(k, 'FLOAT', 'POINT'); at.data.foreach_set('value', arr.ravel().astype(np.float32))
    me.shade_smooth()
    me.materials.append(MAT['road'])
    ob = bpy.data.objects.new('SR_Road', me); COL.objects.link(ob)
    if me.polygons[len(me.polygons) // 2].normal.z < 0:
        me.flip_normals()
    print('[concept] road strip: %d verts, v %.0f..%.0f' % (len(co), V0, V1), flush=True)
    return ob


def road_h(u, v):
    """height of the road strip's lane at (u, v) (for the van, the barrier)"""
    s = u - float(np.interp(v, CENTRE[0], CENTRE[1]))
    a = abs(s)
    return float(G.at(u, v)) + 0.075 - 0.01 * min(a, 3.0) - 0.032 * math.exp(-((a - 0.85) / 0.24) ** 2) * (a < 2.0) + 0.02


# ------------------------------------------------------------------ Wachhaus
def wachhaus():
    """low guard house of grey rendered brick: 3.8 x 4.0 m, walls 2.95 m, flat roof with a 0.3 m overhang; big window
    to the front (-v: the barrier and the road coming in), door and a small window to the road (+u), stove pipe at
    the back; inside a table under the window with the jerrycan, a stove with fire in its slot, a bunk, a coat"""
    hx, hy = HOUSE['hx'], HOUSE['hy']
    t = 0.25; top = 2.95; fl = 0.35
    M = MAT
    mb = MB('SP_Wachhaus', [M['plaster'], M['plinth'], M['roofedge'], M['frame'], M['door'], M['glass'], M['iron'],
                             M['wood'], M['blanket'], M['red'], M['paper'], M['coat'], M['stoveglow'], M['bulb'], M['steel']])
    PL, PN, RE, FR, DO, GL, IR, WD, BL, RD, PA, CO, SG, BU, ST = range(15)
    # front wall (-y) with the big window x -0.95..0.85, z 1.25..2.35
    wx0, wx1, wz0, wz1 = -0.95, 0.85, 1.25, 2.35
    y0, y1 = -hy, -hy + t
    mb.box((-hx, y0, 0), (wx0, y1, top), PL); mb.box((wx1, y0, 0), (hx, y1, top), PL)
    mb.box((wx0, y0, 0), (wx1, y1, wz0), PL); mb.box((wx0, y0, wz1), (wx1, y1, top), PL)
    # back wall (+y), left wall (-x)
    mb.box((-hx, hy - t, 0), (hx, hy, top), PL)
    mb.box((-hx, -hy + t, 0), (-hx + t, hy - t, top), PL)
    # road wall (+x): small window y -1.5..-0.7 (z 1.35..2.2), door y 0.55..1.45 (z fl..2.35)
    x0, x1 = hx - t, hx
    segs = [(-hy + t, -1.5, None), (-1.5, -0.7, (1.35, 2.2)), (-0.7, 0.55, None), (0.55, 1.45, (fl, 2.35)), (1.45, hy - t, None)]
    for (ya, yb, op) in segs:
        if op is None:
            mb.box((x0, ya, 0), (x1, yb, top), PL)
        else:
            mb.box((x0, ya, 0), (x1, yb, op[0]), PL); mb.box((x0, ya, op[1]), (x1, yb, top), PL)
    # plinth band, roof slab, floor
    mb.box((-hx - 0.03, -hy - 0.03, -0.3), (hx + 0.03, hy + 0.03, fl), PN)
    mb.box((-hx - 0.3, -hy - 0.3, top), (hx + 0.3, hy + 0.3, top + 0.24), RE)
    mb.box((-hx + t, -hy + t, fl - 0.08), (hx - t, hy - t, fl), WD)
    # window frames + glass + warm glow behind the big window
    def frame_y(xa, xb, za, zb, y, depth=0.08, bar=0.06, mull=True):
        mb.box((xa, y - depth / 2, za), (xb, y + depth / 2, za + bar), FR); mb.box((xa, y - depth / 2, zb - bar), (xb, y + depth / 2, zb), FR)
        mb.box((xa, y - depth / 2, za), (xa + bar, y + depth / 2, zb), FR); mb.box((xb - bar, y - depth / 2, za), (xb, y + depth / 2, zb), FR)
        if mull:
            xm = (xa + xb) / 2; mb.box((xm - bar / 2, y - depth / 2, za), (xm + bar / 2, y + depth / 2, zb), FR)
            mb.box((xa, y - depth / 2, (za + zb) / 2 + 0.12 - bar / 2), (xb, y + depth / 2, (za + zb) / 2 + 0.12 + bar / 2), FR)
        mb.box((xa, y - 0.005, za), (xb, y + 0.005, zb), GL)
    frame_y(wx0, wx1, wz0, wz1, -hy + 0.12)
    mb.box((wx0 - 0.05, -hy - 0.12, wz0 - 0.06), (wx1 + 0.05, -hy + 0.02, wz0), PN)            # sill
    def frame_x(ya, yb, za, zb, x, depth=0.08, bar=0.06):
        mb.box((x - depth / 2, ya, za), (x + depth / 2, yb, za + bar), FR); mb.box((x - depth / 2, ya, zb - bar), (x + depth / 2, yb, zb), FR)
        mb.box((x - depth / 2, ya, za), (x + depth / 2, ya + bar, zb), FR); mb.box((x - depth / 2, yb - bar, za), (x + depth / 2, yb, zb), FR)
        ym = (ya + yb) / 2; mb.box((x - depth / 2, ym - bar / 2, za), (x + depth / 2, ym + bar / 2, zb), FR)
        mb.box((x - 0.005, ya, za), (x + 0.005, yb, zb), GL)
    frame_x(-1.5, -0.7, 1.35, 2.2, hx - 0.12)
    mb.box((hx - 0.02, -1.55, 1.29), (hx + 0.12, -0.65, 1.35), PN)
    # door (closed), frame, step, handle
    mb.box((hx - 0.16, 0.55, fl), (hx - 0.1, 1.45, 2.35), DO)
    mb.box((hx - 0.1, 0.5, fl), (hx + 0.02, 0.55, 2.4), FR); mb.box((hx - 0.1, 1.45, fl), (hx + 0.02, 1.5, 2.4), FR)
    mb.box((hx - 0.1, 0.5, 2.35), (hx + 0.02, 1.5, 2.42), FR)
    mb.box((hx - 0.08, 0.62, 1.25), (hx - 0.02, 0.72, 1.29), IR)
    mb.box((hx, 0.4, -0.1), (hx + 0.55, 1.6, fl - 0.02), PN)
    # lamp over the door: bracket, shade, bulb
    lz = 2.62
    mb.box((hx, 0.97, lz - 0.02), (hx + 0.32, 1.03, lz + 0.02), IR)
    mb.cyl((hx + 0.32, 1.0, lz - 0.06), 0.13, 0.1, IR, seg=10, r2=0.05)
    mb.cyl((hx + 0.32, 1.0, lz - 0.14), 0.05, 0.06, BU, seg=8)
    # stove pipe through the roof (back left), cap
    px, py = -1.3, 1.35
    mb.cyl((px, py, top + 0.6), 0.075, 1.2, IR, seg=10)
    mb.cyl((px, py, top + 1.27), 0.16, 0.1, IR, seg=10, r2=0.02)
    # inside: stove with the fire slot, pipe to the ceiling
    mb.box((-1.6, 0.95, fl), (-1.05, 1.6, fl + 0.72), IR)
    mb.box((-1.04, 1.12, fl + 0.22), (-1.03, 1.45, fl + 0.3), SG)
    mb.cyl((px, py, (fl + 0.72 + top) / 2), 0.065, top - fl - 0.72, IR, seg=8)
    # table under the window with the jerrycan, the log book, a radio; a chair
    tz = fl + 0.74
    mb.box((-0.95, -hy + t, tz - 0.04), (0.75, -hy + t + 0.65, tz), WD)
    for (lx, ly) in ((-0.9, -hy + t + 0.05), (0.7, -hy + t + 0.05), (-0.9, -hy + t + 0.6), (0.7, -hy + t + 0.6)):
        mb.box((lx - 0.03, ly - 0.03, fl), (lx + 0.03, ly + 0.03, tz - 0.04), WD)
    mb.box((0.1, -hy + t + 0.12, tz), (0.45, -hy + t + 0.3, tz + 0.47), RD)            # jerrycan
    mb.box((0.17, -hy + t + 0.18, tz + 0.47), (0.38, -hy + t + 0.24, tz + 0.52), RD)
    mb.box((-0.7, -hy + t + 0.15, tz), (-0.4, -hy + t + 0.38, tz + 0.04), PA)          # log book
    mb.box((-0.25, -hy + t + 0.08, tz), (-0.02, -hy + t + 0.2, tz + 0.14), IR)         # radio
    mb.box((-0.35, -hy + t + 0.75, fl), (0.05, -hy + t + 1.15, fl + 0.45), WD)          # chair
    mb.box((-0.35, -hy + t + 1.1, fl + 0.45), (0.05, -hy + t + 1.15, fl + 0.95), WD)
    # bunk along the left wall, blanket; coat on the hook by the door; calendar
    mb.box((-hx + t, -0.95, fl), (-hx + t + 0.8, 0.95, fl + 0.45), WD)
    mb.box((-hx + t + 0.02, -0.9, fl + 0.45), (-hx + t + 0.78, 0.9, fl + 0.55), BL)
    mb.box((hx - t - 0.12, 1.55, 1.0), (hx - t - 0.02, 1.7, 1.9), CO)
    mb.box((-0.5, hy - t - 0.01, 1.4), (-0.1, hy - t, 1.95), PA)
    # ceiling bulb
    mb.cyl((0.0, -0.2, top - 0.12), 0.05, 0.08, BU, seg=8)
    ob = mb.done()
    put(ob, HOUSE['u'], HOUSE['v'], float(G.at(HOUSE['u'], HOUSE['v'])) - 0.02, 0.0)
    # warm glow just inside the big window (reads warm in daylight, the inside shows through)
    gm = bpy.data.meshes.new('SP_WinGlow')
    gy = -hy + 0.2
    gm.from_pydata([(wx0 + 0.03, gy, wz0 + 0.03), (wx1 - 0.03, gy, wz0 + 0.03), (wx1 - 0.03, gy, wz1 - 0.03), (wx0 + 0.03, gy, wz1 - 0.03),
                    (hx - 0.2, -1.47, 1.38), (hx - 0.2, -0.73, 1.38), (hx - 0.2, -0.73, 2.17), (hx - 0.2, -1.47, 2.17)], [], [(0, 1, 2, 3), (4, 5, 6, 7)])
    gm.materials.append(M['glow'])
    go = bpy.data.objects.new('SP_WinGlow', gm); go.parent = ob; COL.objects.link(go)
    # lights: inside (warm), over the door (warm)
    li = bpy.data.lights.new('SP_InsideLight', 'POINT'); li.energy = 140; li.color = (1.0, 0.66, 0.36); li.shadow_soft_size = 0.15
    lo = bpy.data.objects.new('SP_InsideLight', li); lo.parent = ob; lo.location = (0.0, -0.2, top - 0.3); COL.objects.link(lo)
    ld = bpy.data.lights.new('SP_DoorLight', 'POINT'); ld.energy = 25; ld.color = (1.0, 0.72, 0.42); ld.shadow_soft_size = 0.05
    lo2 = bpy.data.objects.new('SP_DoorLight', ld); lo2.parent = ob; lo2.location = (hx + 0.32, 1.0, lz - 0.25); COL.objects.link(lo2)
    sl = bpy.data.lights.new('SP_StoveLight', 'POINT'); sl.energy = 6; sl.color = (1.0, 0.4, 0.1); sl.shadow_soft_size = 0.05
    lo3 = bpy.data.objects.new('SP_StoveLight', sl); lo3.parent = ob; lo3.location = (-0.95, 1.28, fl + 0.3); COL.objects.link(lo3)
    # roof snow: a 0.32 m cushion, a cornice with icicles on the front and the road side
    roof = float(G.at(HOUSE['u'], HOUSE['v'])) - 0.02 + top + 0.24
    rs = MB('SP_RoofSnow', [M['snow_clean'], M['soot']])
    res = bmesh.ops.create_cube(rs.bm, size=1.0)
    bmesh.ops.transform(rs.bm, matrix=Matrix.Translation((0, 0, 0.16)) @ Matrix.Diagonal((2 * hx + 0.5, 2 * hy + 0.5, 0.32, 1)), verts=res['verts'])
    ro = rs.done()
    put(ro, HOUSE['u'], HOUSE['v'], roof, 0.0)
    bv = ro.modifiers.new('b', 'BEVEL'); bv.width = 0.14; bv.segments = 3
    pipe_u, pipe_v = HOUSE['u'] + px, HOUSE['v'] + py
    cornice('SP_Cornice_F', [(HOUSE['u'] - hx - 0.3, HOUSE['v'] - hy - 0.3, roof + 0.22), (HOUSE['u'] + hx + 0.3, HOUSE['v'] - hy - 0.3, roof + 0.22)],
            (0, -1), r=0.17, sag=0.08, ice_len=(0.1, 0.55), every=(0.22, 0.55))
    cornice('SP_Cornice_R', [(HOUSE['u'] + hx + 0.3, HOUSE['v'] - hy - 0.3, roof + 0.22), (HOUSE['u'] + hx + 0.3, HOUSE['v'] + hy + 0.3, roof + 0.22)],
            (1, 0), r=0.24, sag=0.12, ice_len=(0.15, 0.8), every=(0.2, 0.5), skip=(HOUSE['v'] + 0.5, HOUSE['v'] + 1.5))
    smoke(P(pipe_u, pipe_v, roof - 0.24 + 1.33))
    print('[concept] Wachhaus at u %.1f v %.1f, roof %.2f' % (HOUSE['u'], HOUSE['v'], roof), flush=True)
    return ob


def cornice(name, pts_uvh, out_uv, r=0.22, sag=0.12, icicles=True, ice_len=(0.15, 0.8), every=(0.25, 0.7), skip=None):
    mb = MB(name, [MAT['snow_clean'], MAT['ice']])
    ou, ov = out_uv
    pts = [P(u, v, h) for u, v, h in pts_uvh]
    ox, oy = F.uv_to_blender_xy(np.array([0.0, ou]), np.array([0.0, ov]))
    outv = Vector((ox[1] - ox[0], oy[1] - oy[0], 0)).normalized()
    for (a, b), (pa, pb) in zip(zip(pts[:-1], pts[1:]), zip(pts_uvh[:-1], pts_uvh[1:])):
        d = b - a; Ln = d.length
        n = max(1, int(Ln / 0.6))
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            p0 = a + d * t0 + outv * (r * 0.6) + Vector((0, 0, -sag * (0.6 + 0.4 * RNG.random())))
            p1 = a + d * t1 + outv * (r * 0.6) + Vector((0, 0, -sag * (0.6 + 0.4 * RNG.random())))
            mb.rod(p0, p1, r * (0.75 + 0.5 * RNG.random()), 0, seg=8)
        if icicles:
            s = 0.0
            while s < Ln:
                s += every[0] + (every[1] - every[0]) * RNG.random()
                if s >= Ln:
                    break
                if skip is not None:
                    vv = pa[1] + (pb[1] - pa[1]) * s / Ln
                    if skip[0] <= vv <= skip[1]:
                        continue
                p = a + d * (s / Ln) + outv * (r * 0.9)
                ln = ice_len[0] + (ice_len[1] - ice_len[0]) * RNG.random() ** 2
                rad = 0.025 + 0.03 * RNG.random()
                res = bmesh.ops.create_cone(mb.bm, cap_ends=True, cap_tris=False, segments=5, radius1=0.0, radius2=rad, depth=ln)
                bmesh.ops.transform(mb.bm, matrix=Matrix.Translation(p + Vector((0, 0, -ln / 2 - r * 0.3))), verts=res['verts'])
                for f in {f for v in res['verts'] for f in v.link_faces}:
                    f.material_index = 1
    ob = mb.done(smooth=True)
    COL.objects.link(ob)
    return ob


def smoke(p0):
    """stove smoke: a few soft volumes leaning north-east (+u) with the wind"""
    du = F.uv_to_blender_xy(1.0, 0.0); d0 = F.uv_to_blender_xy(0.0, 0.0)
    wind = Vector((float(du[0] - d0[0]), float(du[1] - d0[1]), 0)).normalized()
    for k, (dist, rise, r, dens) in enumerate(((0.2, 0.3, 0.25, 6.0), (0.7, 0.75, 0.42, 3.5), (1.6, 1.25, 0.68, 1.8), (2.9, 1.7, 0.98, 0.8), (4.6, 2.0, 1.3, 0.35))):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        me = bpy.data.meshes.new('SP_Smoke%d' % k); bm.to_mesh(me); bm.free(); me.materials.append(MAT['smoke'])
        o = bpy.data.objects.new('SP_Smoke%d' % k, me)
        o.location = p0 + wind * dist + Vector((0, 0, rise)); o.scale = (r * 1.4, r, r * 0.9)
        o.rotation_euler = (RNG.random(), RNG.random(), RNG.random())
        o['dens'] = dens
        COL.objects.link(o)


# ------------------------------------------------------------------ the van
def van():
    """the players' van (Van.fbx of VanVehicle) where ForestOpening spawns it: frame (1, -14), nose into the zone (-v);
    olive body (QUESTIONS_3 11: VanOld paint), hazard lights on, roof snow only"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=VAN + 'Models/Van.fbx')
    new = [o for o in bpy.data.objects if o not in before]
    for im in bpy.data.images:
        if '/Van/Models/' in im.filepath:
            im.filepath = VAN + 'Textures/' + os.path.basename(im.filepath)
    tex = {'M_Van_Body': 'T_VanOld_Body_BaseColor.png', 'M_Van_Cabin': 'T_Van_Cabin_BaseColor.png', 'M_Van_Mech': 'T_Van_Mech_BaseColor.png',
           'M_Van_Props': 'T_Van_Props_BaseColor.png', 'M_Van_Seats': 'T_Van_Seats_BaseColor.png', 'M_Van_Trim': 'T_Van_Mech_BaseColor.png'}
    plain = {'M_Van_Wheel': (0.03, 0.03, 0.03), 'M_PSX_Glass_Cab': None, 'M_PSX_Glass_Room': None}
    cache = {}

    def remap(m):
        n = m.name.split('.')[0]
        if n in cache:
            return cache[n]
        if n in tex:
            r = uv_mat('V_' + n, VAN + 'Textures/' + tex[n], rough=0.75)
        elif n == 'M_Van_Snow':
            r = MAT['snow_clean']
        elif n.startswith('M_PSX_Glass'):
            r = col_mat('V_Glass', (0.035, 0.04, 0.045), rough=0.1, snow=False)
        elif n == 'M_Van_Lens_Amber':
            r = col_mat('V_Hazard', (1.0, 0.55, 0.08), snow=False, emit=(1.0, 0.5, 0.05), strength=14.0)
        elif n.startswith('M_Van_Lens'):
            r = uv_mat('V_Lens', VAN + 'Textures/T_Van_Lens_BaseColor.png', rough=0.3)
        elif n == 'M_Van_Wheel':
            r = col_mat('V_Rubber', (0.03, 0.03, 0.03), rough=0.9, snow=False)
        else:
            r = col_mat('V_Dark', (0.06, 0.06, 0.06), rough=0.7, snow=False)
        cache[n] = r
        return r
    root = bpy.data.objects.new('SP_Van', None)
    COL.objects.link(root)
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        COL.objects.link(o)
        if o.type == 'MESH':
            for s in o.material_slots:
                if s.material:
                    s.material = remap(s.material)
            if o.name.split('.')[0] in ('Snow_Head_L', 'Snow_Head_R', 'Snow_Fog_L', 'Snow_Fog_R', 'Snow_Spot_L', 'Snow_Spot_R', 'Snow_Bumper'):
                o.hide_render = True
        if o.parent is None:
            o.parent = root
    u, v = VANP
    root.location = P(u, v, road_h(u, v))
    root.rotation_euler = (0, 0, F.ROTZ)
    print('[concept] van: %d objects' % len(new), flush=True)


# ------------------------------------------------------------------ snow on the pad
OBST = []       # (u0, v0, u1, v1, height) obstacles for the drifts


def poly_dist(U, V, pts):
    d = np.full(U.shape, np.inf)
    for (a, b) in zip(pts[:-1], pts[1:]):
        ax, ay = a; bx, by = b
        dx, dy = bx - ax, by - ay
        t = np.clip(((U - ax) * dx + (V - ay) * dy) / (dx * dx + dy * dy), 0, 1)
        d = np.minimum(d, np.hypot(U - (ax + t * dx), V - (ay + t * dy)))
    return d


PATH = [(-2.4, -2.5), (-4.6, -2.45), (-6.0, -2.4), (-6.5, -2.4)]          # road -> house door (trodden through the windrow)


def snow_field():
    """old snow on the pad and behind the post (0.32 m), drifts on the lee (+u) sides of the house, the car, the blocks;
    the estate snowed in to the windows; a low ridge along the zone fence; the path to the door trodden down, the door
    shovelled clear; nothing on the road (the road strip has its own windrows)"""
    st = 0.25
    u0, v0, u1, v1 = -34.0, -48.0, 16.0, 9.0
    uu = np.arange(u0, u1 + 1e-6, st); vv = np.arange(v0, v1 + 1e-6, st)
    U, V = np.meshgrid(uu, vv)
    Uc = np.interp(V, CENTRE[0], CENTRE[1]); Sx = U - Uc
    rng = np.random.default_rng(2911)
    n1 = ndimage.gaussian_filter(rng.standard_normal(U.shape), 8); n1 /= n1.std()
    n2 = ndimage.gaussian_filter(rng.standard_normal(U.shape), 2.5); n2 /= n2.std()
    # fence line (inside face v_f - 0.25)
    vf = np.where(U < 0, -(np.abs(U) - 4.7) * (3.0 / 59.3), (U - 4.7) * (2.0 / 59.3))
    inside = V < vf - 0.15
    # blanket: left of the road from the windrow's foot, inside the fence; a little less down the hollow
    blanket = 0.32 * smoothstep(4.4, 5.8, -Sx) * smoothstep(-0.05, 0.35, vf - V) * (1 + 0.08 * n1)
    blanket *= 1 - 0.25 * smoothstep(-26, -32, V)
    blanket *= 1 - smoothstep(-31.0, -34.0, U)
    # obstacles
    O = np.zeros_like(U)
    for (a0, b0, a1, b1, hh) in OBST:
        m = (U >= a0) & (U <= a1) & (V >= b0) & (V <= b1); O[m] = np.maximum(O[m], hh)
    BLD = O > 0
    # lee drifts (+u): the drift reaches ~2.2 heights downwind; a cushion on the windward side
    k_max = int(8.0 / st)
    Dd = np.zeros_like(U)
    for k in range(1, k_max + 1):
        Ok = np.zeros_like(O); Ok[:, k:] = O[:, :-k]
        s = k * st
        Dd = np.maximum(Dd, Ok * np.clip(1 - s / (2.2 * np.maximum(Ok, 0.01)), 0, 1) ** 1.3)
    Wd = np.zeros_like(U)
    for k in range(1, int(2.0 / st) + 1):
        Ok = np.zeros_like(O); Ok[:, :-k] = O[:, k:]
        s = k * st
        Wd = np.maximum(Wd, Ok * np.clip(1 - s / (0.6 * np.maximum(Ok, 0.01)), 0, 1))
    drift = ndimage.gaussian_filter(0.30 * Dd + 0.12 * Wd, 1.6) * (1 + 0.12 * n2)
    # the estate: snowed in to the windows (0.68 m), more on the lee side
    cu0, cv0, cu1, cv1 = CAR
    dcar = np.hypot(np.maximum(np.maximum(cu0 - U, U - cu1), 0), np.maximum(np.maximum(cv0 - V, V - cv1), 0))
    lee = smoothstep(cu0, cu1 + 1.0, U)
    mound = (0.66 + 0.2 * lee) * np.clip(1 - (dcar / (1.3 + 1.2 * lee)) ** 1.6, 0, 1) * (1 + 0.06 * n2)
    # zone fence: a low ridge on both faces
    dfen = np.abs(V - vf) * (np.abs(U) > 4.4)
    ridge = 0.34 * np.exp(-(dfen / 0.7) ** 2) * (1 + 0.25 * n1) * (np.abs(U) > 4.6)
    gate_r = 0.22 * np.exp(-(np.abs(V) / 0.5) ** 2) * (np.abs(U) < 4.6) * smoothstep(2.7, 3.4, np.abs(U))
    h = np.maximum.reduce([blanket + drift * 0.85, mound, ridge, gate_r]) + 0.2 * np.minimum(blanket, drift)
    # off the road: the lane is ploughed (the strip carries the windrows)
    h *= smoothstep(3.3, 4.6, np.abs(Sx))
    # the path to the door trodden down, the door's front shovelled
    dp = poly_dist(U, V, PATH)
    h *= 0.2 + 0.8 * smoothstep(0.45, 0.95, dp)
    du_ = np.maximum(np.maximum(-6.6 - U, U - (-5.0)), 0); dv_ = np.maximum(np.maximum(-3.3 - V, V - (-1.5)), 0)
    h *= 0.25 + 0.75 * smoothstep(0.0, 0.8, np.hypot(du_, dv_))
    h[BLD] = 0.0
    h = ndimage.gaussian_filter(h, 0.7)
    h[BLD] = 0.0
    dirt = np.clip(0.55 * (1 - smoothstep(0.35, 0.9, dp)) * (h > 0.02), 0, 0.6)
    SNOWH[:] = [uu, vv, h]
    print('[concept] snow field: max %.2f m, blanket %.2f m' % (h.max(), float(np.median(blanket[blanket > 0.2]))), flush=True)
    return uu, vv, h, dirt


def snow_at(u, v):
    if not SNOWH:
        return 0.0
    uu, vv, h = SNOWH
    i = int(np.clip(round((u - uu[0]) / (uu[1] - uu[0])), 0, len(uu) - 1)); j = int(np.clip(round((v - vv[0]) / (vv[1] - vv[0])), 0, len(vv) - 1))
    return float(h[j, i])


def snow_mesh(uu, vv, h, dirt):
    U, V = np.meshgrid(uu, vv)
    on = h > 0.025
    cell = on[:-1, :-1] | on[1:, :-1] | on[:-1, 1:] | on[1:, 1:]
    idx = np.full(h.shape, -1, np.int64)
    need = np.zeros_like(on)
    need[:-1, :-1] |= cell; need[1:, :-1] |= cell; need[:-1, 1:] |= cell; need[1:, 1:] |= cell
    idx[need] = np.arange(need.sum())
    x, z = F.uv_to_unity(U[need], V[need])
    gh = G.at_unity(x, z)
    co = np.stack([-x, -z, gh + np.maximum(h[need], 0) - 0.015], 1).astype(np.float32)
    j, i = np.nonzero(cell)
    q = np.stack([idx[j, i], idx[j, i + 1], idx[j + 1, i + 1], idx[j + 1, i]], 1)
    me = bpy.data.meshes.new('SP_SnowLayer')
    me.vertices.add(len(co)); me.vertices.foreach_set('co', co.ravel())
    me.loops.add(q.size); me.loops.foreach_set('vertex_index', q.ravel().astype(np.int32))
    me.polygons.add(len(q)); me.polygons.foreach_set('loop_start', np.arange(0, q.size, 4, dtype=np.int32))
    me.update(calc_edges=True)
    at = me.attributes.new('dirt', 'FLOAT', 'POINT'); at.data.foreach_set('value', dirt[need].astype(np.float32))
    me.shade_smooth()
    me.materials.append(MAT['snow'])
    ob = bpy.data.objects.new('SP_SnowLayer', me); COL.objects.link(ob)
    print('[concept] snow layer: %d verts' % len(co), flush=True)


def top_snow(ob, thick=0.2, min_up=0.85, min_h=0.5, bevel=0.06, name=None, mat=None):
    """snow slabs on the up-facing faces of an object"""
    me = ob.data
    Mw = ob.matrix_world.copy()
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(Mw)
    bm.normal_update()
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.z < min_up or f.calc_area() < 0.01:
            kill.append(f); continue
        u, v = F.blender_to_uv(c.x, c.y)
        if c.z - float(G.at(float(u), float(v))) - snow_at(float(u), float(v)) < min_h:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    if not bm.faces:
        bm.free(); return None
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)
    for v in bm.verts:
        v.co.z += 0.01
    sm = bpy.data.meshes.new((name or ob.name) + '_snow'); bm.to_mesh(sm); bm.free()
    sm.materials.append(mat or MAT['snow_clean'])
    so = bpy.data.objects.new((name or ob.name) + '_snow', sm)
    COL.objects.link(so)
    md = so.modifiers.new('solid', 'SOLIDIFY'); md.thickness = thick; md.offset = 1.0; md.use_even_offset = True
    if bevel:
        bv = so.modifiers.new('bevel', 'BEVEL'); bv.width = bevel; bv.segments = 2; bv.limit_method = 'ANGLE'
        bv.angle_limit = math.radians(50)
    return so


# ------------------------------------------------------------------ the post's other pieces
CAR = None


def post_pieces():
    """barrier turned and set before the window; the sign to the right verge facing the players; the tripod to the
    gate; the second pad lamp gone; the crates off the house corner; fence plates"""
    global CAR
    # the booth goes (the Wachhaus stands in its place)
    remove_root('StartBooth')
    remove_root('LightPole (1)')
    # barrier: pivot at the house side, arm over the road (raised, as decided 26.10), in front of the window
    move_root('Barrier_Manual', BARRIER[0], BARRIER[1], 180.0, dz=road_h(*BARRIER) - float(G.at(*BARRIER)) - 0.04)
    # the sign: right verge inside the gate, its face to the players (ForestStartDress 'moves')
    move_root('Sign_Observatory', SIGN[0], SIGN[1], 180.0 - 10.4)
    # the cold tripod light by the gate post, out of the house's way
    move_root('StartLamp', -4.9, -0.9, 0.0)
    move_root('Crates', -12.5, -6.4, 0.0)
    # the estate's box for the snow
    c = [o for o in objs_of('StartCar') if o.type == 'MESH']
    pts = np.array([o.matrix_world @ Vector(b) for o in c for b in o.bound_box])
    cu, cv = F.blender_to_uv(pts[:, 0], pts[:, 1])
    CAR = (float(cu.min()), float(cv.min()), float(cu.max()), float(cv.max()))
    # obstacles for the drifts
    OBST.extend([(HOUSE['u'] - HOUSE['hx'], HOUSE['v'] - HOUSE['hy'], HOUSE['u'] + HOUSE['hx'], HOUSE['v'] + HOUSE['hy'], 3.0)])
    for root, hh in (('RoadBlock_Jersey', 0.9), ('Crates', 1.1), ('FireBarrel', 0.9), ('StartTyres', 0.55), ('StartTyres (1)', 0.55), ('StartTrash', 0.65)):
        for o in objs_of(root):
            if o.type != 'MESH':
                continue
            b = np.array([o.matrix_world @ Vector(x) for x in o.bound_box])
            ou, ov = F.blender_to_uv(b[:, 0], b[:, 1])
            OBST.append((float(ou.min()), float(ov.min()), float(ou.max()), float(ov.max()), hh))
    OBST.append((CAR[0], CAR[1], CAR[2], CAR[3], 1.2))
    # zone fence plates (SPERRGEBIET), 1.5 m up on the inside face, every ~30 m
    for u in (-13.6, -43.9, 13.6, 43.9):
        vf = -(abs(u) - 4.7) * (3.0 / 59.3) if u < 0 else (u - 4.7) * (2.0 / 59.3)
        plate(u, vf - 0.07, 1.45)


def plate(u, v, up):
    w, hh = 0.62, 0.37
    me = bpy.data.meshes.new('SP_Plate')
    me.from_pydata([(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, hh), (-w / 2, 0, hh), (-w / 2, 0.01, 0), (w / 2, 0.01, 0), (w / 2, 0.01, hh), (-w / 2, 0.01, hh)],
                   [], [(0, 1, 2, 3), (5, 4, 7, 6)])
    uvl = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        for li in p.loop_indices:
            vi = me.loops[li].vertex_index
            uvl.data[li].uv = ((0.0 if vi in (0, 3, 4, 7) else 1.0), (0.0 if vi in (0, 1, 4, 5) else 1.0))
    me.materials.append(MAT['plate']); me.materials.append(MAT['plateback'])
    me.polygons[1].material_index = 1
    ob = bpy.data.objects.new('SP_Plate', me)
    put(ob, u, v, float(G.at(u, v)) + up, 0.0)
    # the face (local -y) must look to -v: local y = +v in the frame, so it does


def caps():
    """snow caps on what stands outside: blocks, crates, tyres, trash, signs, the gate's rails, the estate (thick), lamps"""
    n = 0
    for o in list(bpy.data.objects):
        if o.type != 'MESH' or o.name.endswith('_snow'):
            continue
        r = o.get('root', '')
        if r in ('RoadBlock_Jersey', 'Crates', 'StartTrash', 'StartTyres', 'StartTyres (1)'):
            top_snow(o, thick=0.16, min_up=0.75, min_h=0.25); n += 1
        elif r in ('Sign_Observatory', 'Sign_Halt', 'Sign_NoEntry', 'StartLamp', 'LightPole'):
            top_snow(o, thick=0.08, min_up=0.85, min_h=1.0, bevel=0.03); n += 1
        elif r == 'ZoneGate':
            top_snow(o, thick=0.06, min_up=0.85, min_h=0.8, bevel=0.02); n += 1
        elif r == 'StartCar' and o.data.name.split('.')[0].endswith('StartCar'):
            top_snow(o, thick=0.3, min_up=0.7, min_h=0.55, bevel=0.12); n += 1
    print('[concept] caps on %d objects' % n, flush=True)
    # the estate's glass frosted
    for o in objs_of('StartCar'):
        if o.type == 'MESH' and 'Glass' in o.name:
            for s in o.material_slots:
                s.material = MAT['frost']


# ------------------------------------------------------------------ main
def build_concept():
    global G, G0, COL, MAT, MAPJ, CENTRE
    MAPJ = json.load(open(MAP + 'map.json', encoding='utf-8'))
    G0 = F.Ground()
    G = G0
    COL = bpy.data.collections.new('Concept'); bpy.context.scene.collection.children.link(COL)
    MAT = mats()
    CENTRE = centreline()
    terrain()
    splat_after()
    cut_roadnet()
    road()
    post_pieces()
    wachhaus()
    van()
    uu, vv, h, dirt = snow_field()
    snow_mesh(uu, vv, h, dirt)
    bpy.context.view_layer.update()
    caps()


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    out = argv[0]; views = argv[1].split(',') if len(argv) > 1 and argv[1] != '-' else []
    spp = int(argv[2]) if len(argv) > 2 else 16
    res = (int(argv[3]), int(argv[4])) if len(argv) > 4 else (1280, 720)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene['fog_k'] = 1.0
    S.build()
    S.world_overcast()
    cams = S.cameras()
    S.setup_render(spp, res)
    build_concept()
    for k, (e, l, fov) in S.VIEWS.items():                    # the eye stands on the snow / the new ground
        u, v = F.unity_to_uv(e[0], e[2])
        dh = snow_at(float(u), float(v)) + float(G.at(float(u), float(v))) - float(G0.at(float(u), float(v)))
        if abs(dh) > 0.01 and not k.endswith('_air'):
            cams[k].location.z += dh
            print('[concept] camera %s moved %.2f m with the snow / ground' % (k, dh), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    S.render(cams, views, os.environ.get('OUTDIR', os.path.join(D, 'rend', 'after')))


if __name__ == '__main__':
    main()
