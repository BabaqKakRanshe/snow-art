"""Base yard concept (L12, 28.10.2026): the base from the map export (base_scene) + the yard brought up to the brief:
a radome on the main building, the edges closed with buildings (garage row, workshop, containers, boiler house with a
chimney), snow by plough logic (banks, end piles, tracks, paths, lee drifts, roof snow with cornices and icicles), zones
at the walls (fuel in a bund, generator soot, rubbish, storage, parking with a snowed-in car), dark masses with a few
accents, details on the main building.

python3.11 -I concept.py <out.blend> <views|-> [spp] [w h]"""
import bpy, bmesh, math, json, os, sys, random
import numpy as np
from mathutils import Vector, Matrix

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import base_scene as S
import yard as Y
from scipy import ndimage

MAP = S.MAP
GT = S.GROUND_TEX
TEX = MAP + 'textures/'
RNG = random.Random(2810)
G = None
COL = None
OBST = []          # footprints for the drifts: (u0, v0, u1, v1, height)
CLEAR = []         # rects where the yard saplings / clumps go: (u0, v0, u1, v1)
WIND = (1.0, 1.0)  # snow drifts with a south-west wind: lee sides face north-east


# ------------------------------------------------------------------ placing
def P(u, v, h=None):
    x, y = Y.uv_to_blender_xy(u, v)
    if h is None:
        h = float(G.at(u, v))
    return Vector((float(x), float(y), float(h)))


def put(ob, u, v, h=None, theta=0.0, col=None):
    ob.location = P(u, v, h)
    ob.rotation_euler = (0.0, 0.0, Y.ROTZ + math.radians(theta))
    (col or COL).objects.link(ob)
    return ob


def rect_c(u, v, su, sv, theta=0.0):
    """axis-aligned (yard) bounds of a turned rectangle"""
    c, s = abs(math.cos(math.radians(theta))), abs(math.sin(math.radians(theta)))
    hu, hv = (su * c + sv * s) / 2, (su * s + sv * c) / 2
    return (u - hu, v - hv, u + hu, v + hv)


# ------------------------------------------------------------------ materials
_mats = {}


def _base(name):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    return mat, N, L, N['Principled BSDF']


def tex_mat(name, tex, tint=(1, 1, 1), scale=2.0, rough=0.85, snow=True, metal=0.0, world=False):
    if name in _mats:
        return _mats[name]
    mat, N, L, pb = _base(name)
    pb.inputs['Roughness'].default_value = rough; pb.inputs['Metallic'].default_value = metal
    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / scale, 1 / scale, 1 / scale)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    if world:
        geo = N.new('ShaderNodeNewGeometry'); L.new(geo.outputs['Position'], mp.inputs['Vector'])
    t = N.new('ShaderNodeTexImage'); t.image = S.image(tex); t.interpolation = 'Closest'
    t.projection = 'BOX'; t.projection_blend = 0.2
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


def col_mat(name, rgb, rough=0.7, snow=True, metal=0.0, emit=None, strength=1.0):
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
    S.fog_wrap(mat, pb.outputs['BSDF'])
    _mats[name] = mat
    return mat


def stripe_mat(name, c1, c2, period=0.5, axis='Z', diag=False, rough=0.6, snow=True):
    if name in _mats:
        return _mats[name]
    mat, N, L, pb = _base(name)
    pb.inputs['Roughness'].default_value = rough
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs['Vector'])
    s = sep.outputs[axis]
    if diag:
        ad = N.new('ShaderNodeMath'); ad.operation = 'ADD'
        L.new(sep.outputs['X'], ad.inputs[0]); L.new(sep.outputs[axis], ad.inputs[1]); s = ad.outputs['Value']
    dv = N.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = period; L.new(s, dv.inputs[0])
    fr = N.new('ShaderNodeMath'); fr.operation = 'FRACT'; L.new(dv.outputs['Value'], fr.inputs[0])
    gt = N.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.5; L.new(fr.outputs['Value'], gt.inputs[0])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    L.new(gt.outputs['Value'], mx.inputs['Factor']); mx.inputs['A'].default_value = (*c1, 1); mx.inputs['B'].default_value = (*c2, 1)
    col = mx.outputs['Result']
    if snow:
        col = S.snow_mix(mat, col)
    L.new(col, pb.inputs['Base Color'])
    S.fog_wrap(mat, pb.outputs['BSDF'])
    _mats[name] = mat
    return mat


def snow_surface_mat(name='C_Snow', dirt=True, bright=1.08):
    """snow of the banks, drifts and roofs: the ground's snow texture in the terrain's own world mapping (seamless with
    it), dirtier low on the plough banks (attribute 'dirt')"""
    if name in _mats:
        return _mats[name]
    mat, N, L, pb = _base(name)
    pb.inputs['Roughness'].default_value = 0.78
    geo = N.new('ShaderNodeNewGeometry')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], sep.inputs['Vector'])
    comb = N.new('ShaderNodeCombineXYZ')
    for ax in ('X', 'Y'):
        m_ = N.new('ShaderNodeMath'); m_.operation = 'MULTIPLY'; m_.inputs[1].default_value = -0.5
        L.new(sep.outputs[ax], m_.inputs[0]); L.new(m_.outputs['Value'], comb.inputs[ax])
    t = N.new('ShaderNodeTexImage'); t.image = S.image(GT + 'T_GR_Floor_A.png'); t.interpolation = 'Closest'
    L.new(comb.outputs['Vector'], t.inputs['Vector'])
    br = N.new('ShaderNodeMix'); br.data_type = 'RGBA'; br.blend_type = 'MULTIPLY'; br.inputs['Factor'].default_value = 1.0
    L.new(t.outputs['Color'], br.inputs['A']); br.inputs['B'].default_value = (bright, bright, bright * 1.01, 1)
    col = br.outputs['Result']
    if dirt:
        td = N.new('ShaderNodeTexImage'); td.image = S.image(GT + 'T_GR_Gravel_A.png'); td.interpolation = 'Closest'
        L.new(comb.outputs['Vector'], td.inputs['Vector'])
        tdm = N.new('ShaderNodeMix'); tdm.data_type = 'RGBA'; tdm.blend_type = 'MULTIPLY'; tdm.inputs['Factor'].default_value = 1.0
        L.new(td.outputs['Color'], tdm.inputs['A']); tdm.inputs['B'].default_value = (0.82, 0.8, 0.76, 1)
        at = N.new('ShaderNodeAttribute'); at.attribute_name = 'dirt'
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        L.new(at.outputs['Fac'], mx.inputs['Factor']); L.new(col, mx.inputs['A']); L.new(tdm.outputs['Result'], mx.inputs['B'])
        col = mx.outputs['Result']
    L.new(col, pb.inputs['Base Color'])
    S.fog_wrap(mat, pb.outputs['BSDF'])
    _mats[name] = mat
    return mat


def decal_mat(name, tex, alpha=0.9, tint=(1, 1, 1)):
    """ground strips (tracks, ruts, paths): the ground layer texture in the terrain mapping, soft edges across (uv x)"""
    if name in _mats:
        return _mats[name]
    mat, N, L, pb = _base(name)
    pb.inputs['Roughness'].default_value = 0.85
    geo = N.new('ShaderNodeNewGeometry')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], sep.inputs['Vector'])
    comb = N.new('ShaderNodeCombineXYZ')
    for ax in ('X', 'Y'):
        m_ = N.new('ShaderNodeMath'); m_.operation = 'MULTIPLY'; m_.inputs[1].default_value = -0.5
        L.new(sep.outputs[ax], m_.inputs[0]); L.new(m_.outputs['Value'], comb.inputs[ax])
    t = N.new('ShaderNodeTexImage'); t.image = S.image(GT + tex); t.interpolation = 'Closest'
    L.new(comb.outputs['Vector'], t.inputs['Vector'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
    L.new(t.outputs['Color'], mx.inputs['A']); mx.inputs['B'].default_value = (*tint, 1)
    L.new(mx.outputs['Result'], pb.inputs['Base Color'])
    uv = N.new('ShaderNodeUVMap')
    su = N.new('ShaderNodeSeparateXYZ'); L.new(uv.outputs['UV'], su.inputs['Vector'])
    # alpha = alpha * smooth edge: 1 - |2x - 1| ^ 3, broken up by noise
    m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY_ADD'; m1.inputs[1].default_value = 2.0; m1.inputs[2].default_value = -1.0
    L.new(su.outputs['X'], m1.inputs[0])
    ab = N.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; L.new(m1.outputs['Value'], ab.inputs[0])
    pw = N.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 2.5; L.new(ab.outputs['Value'], pw.inputs[0])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.9
    L.new(geo.outputs['Position'], nz.inputs['Vector'])
    ad = N.new('ShaderNodeMath'); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.6; ad.inputs[2].default_value = -0.3
    L.new(nz.outputs['Fac'], ad.inputs[0])
    s1 = N.new('ShaderNodeMath'); s1.operation = 'ADD'; L.new(pw.outputs['Value'], s1.inputs[0]); L.new(ad.outputs['Value'], s1.inputs[1])
    one = N.new('ShaderNodeMath'); one.operation = 'SUBTRACT'; one.inputs[0].default_value = 1.0; L.new(s1.outputs['Value'], one.inputs[1])
    cl = N.new('ShaderNodeMath'); cl.operation = 'MULTIPLY'; cl.use_clamp = True; cl.inputs[1].default_value = alpha
    L.new(one.outputs['Value'], cl.inputs[0])
    L.new(cl.outputs['Value'], pb.inputs['Alpha'])
    S.fog_wrap(mat, pb.outputs['BSDF'])
    _mats[name] = mat
    return mat


def smoke_mat():
    if 'C_Smoke' in _mats:
        return _mats['C_Smoke']
    mat = bpy.data.materials.new('C_Smoke'); mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    for n in list(N):
        if n.type == 'BSDF_PRINCIPLED':
            N.remove(n)
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')
    vol = N.new('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (0.9, 0.9, 0.92, 1); vol.inputs['Anisotropy'].default_value = 0.3
    vol.inputs['Absorption Color'].default_value = (0.75, 0.75, 0.77, 1)
    vol.inputs['Emission Color'].default_value = (0.8, 0.81, 0.84, 1); vol.inputs['Emission Strength'].default_value = 0.1
    tc = N.new('ShaderNodeTexCoord')
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.4; nz.inputs['Detail'].default_value = 3
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
    _mats['C_Smoke'] = mat
    return mat


def mats():
    M = {}
    M['concrete'] = tex_mat('C_Concrete', TEX + 'T_Concrete_A_px.png', (0.78, 0.78, 0.76))
    M['concrete_dark'] = tex_mat('C_ConcreteDark', TEX + 'T_Concrete_A_px.png', (0.36, 0.33, 0.31))
    M['steel'] = tex_mat('C_Steel', TEX + 'T_Steel_A_px.png', (0.55, 0.56, 0.58), rough=0.55, metal=0.3)
    M['steel_dark'] = tex_mat('C_SteelDark', TEX + 'T_Steel_A_px.png', (0.22, 0.23, 0.24), rough=0.6, metal=0.3)
    M['olive'] = tex_mat('C_Olive', TEX + 'T_PaintOlive_A_px.png', (0.85, 0.9, 0.8), scale=1.5)
    M['rust'] = tex_mat('C_Rust', TEX + 'T_Base_Rust_A_px.png', (0.8, 0.75, 0.7), scale=1.5)
    M['cont_red'] = rib_mat('C_ContRed', (0.42, 0.11, 0.07))
    M['cont_blue'] = rib_mat('C_ContBlue', (0.12, 0.19, 0.28))
    M['cont_olive'] = rib_mat('C_ContOlive', (0.21, 0.24, 0.14))
    M['corr_dark'] = tex_mat('C_CorrDark', TEX + 'T_Corrugated_A.png', (0.24, 0.29, 0.26), scale=2.4)
    M['wood'] = tex_mat('C_Wood', TEX + 'T_WoodSiding_A.jpg', (0.62, 0.52, 0.42), scale=1.2)
    M['white'] = col_mat('C_White', (0.78, 0.79, 0.8), rough=0.5)
    M['red'] = col_mat('C_Red', (0.6, 0.05, 0.035), rough=0.5)
    M['yellow'] = col_mat('C_Yellow', (0.9, 0.62, 0.04), rough=0.5)
    M['black'] = col_mat('C_Black', (0.025, 0.025, 0.025), rough=0.6)
    M['orange'] = col_mat('C_Orange', (1.0, 0.33, 0.02), rough=0.45, snow=False)
    M['glass'] = col_mat('C_Glass', (0.03, 0.035, 0.04), rough=0.15, snow=False)
    M['glow'] = glow_mat()
    M['lamp'] = col_mat('C_Lamp', (0.9, 0.8, 0.6), snow=False, emit=(1.0, 0.8, 0.5), strength=25.0)
    M['redlight'] = col_mat('C_RedLight', (0.8, 0.05, 0.03), snow=False, emit=(1.0, 0.05, 0.02), strength=30.0)
    M['yb'] = stripe_mat('C_YellowBlack', (0.9, 0.62, 0.04), (0.02, 0.02, 0.02), period=0.4)
    M['rw'] = stripe_mat('C_RedWhite', (0.62, 0.05, 0.04), (0.82, 0.82, 0.82), period=1.0, axis='X')
    M['rw_band'] = stripe_mat('C_RedWhiteBand', (0.62, 0.05, 0.04), (0.82, 0.82, 0.82), period=2.0, axis='Z', snow=False)
    M['snow'] = snow_surface_mat('C_Snow', dirt=True)
    M['snow_clean'] = snow_surface_mat('C_SnowClean', dirt=False, bright=1.1)
    M['ice'] = col_mat('C_Ice', (0.72, 0.8, 0.88), rough=0.12, snow=False)
    M['soot'] = col_mat('C_Soot', (0.03, 0.028, 0.026), rough=0.9, snow=False)
    M['drum_blue'] = col_mat('C_DrumBlue', (0.07, 0.16, 0.38), rough=0.5)
    M['drum_red'] = col_mat('C_DrumRed', (0.42, 0.07, 0.04), rough=0.55)
    M['drum_green'] = col_mat('C_DrumGreen', (0.12, 0.2, 0.1), rough=0.55)
    M['bag'] = col_mat('C_Bag', (0.015, 0.015, 0.017), rough=0.3)
    M['bin'] = col_mat('C_Bin', (0.06, 0.15, 0.08), rough=0.5)
    M['sign_blue'] = col_mat('C_SignBlue', (0.03, 0.08, 0.25), rough=0.4, snow=False)
    M['letters'] = col_mat('C_Letters', (0.85, 0.85, 0.85), rough=0.4, snow=False)
    M['radome'] = radome_mat()
    M['track'] = decal_mat('C_Track', 'T_GR_Track_A.png', 0.85)
    M['ruts'] = decal_mat('C_Ruts', 'T_GR_Track_A.png', 0.8, tint=(0.78, 0.78, 0.8))
    M['packed'] = decal_mat('C_Packed', 'T_GR_Soil_A.png', 0.8)
    M['smoke'] = smoke_mat()
    return M


def glow_mat():
    mat, N, L, pb = _base('C_Glow')
    pb.inputs['Base Color'].default_value = (0.2, 0.14, 0.08, 1); pb.inputs['Roughness'].default_value = 0.2
    pb.inputs['Emission Color'].default_value = (1.0, 0.62, 0.32, 1); pb.inputs['Emission Strength'].default_value = 1.7
    pb.inputs['Alpha'].default_value = 0.6
    S.fog_wrap(mat, pb.outputs['BSDF'])
    _mats['C_Glow'] = mat
    return mat


def rib_mat(name, rgb):
    """container steel: vertical ribs every 0.3 m (local x), rust streaks, painted"""
    if name in _mats:
        return _mats[name]
    mat, N, L, pb = _base(name)
    pb.inputs['Roughness'].default_value = 0.6
    tc = N.new('ShaderNodeTexCoord')
    wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'X'; wv.inputs['Scale'].default_value = 1.0 / 0.3 / 1.0
    wv.wave_profile = 'TRI'
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.05, 1.0, 1.0)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    L.new(mp.outputs['Vector'], wv.inputs['Vector']); wv.inputs['Scale'].default_value = 1.0
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 4
    mpn = N.new('ShaderNodeMapping'); mpn.inputs['Scale'].default_value = (1.0, 1.0, 0.25)
    L.new(tc.outputs['Object'], mpn.inputs['Vector']); L.new(mpn.outputs['Vector'], nz.inputs['Vector'])
    cr = N.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.0; cr.inputs['From Max'].default_value = 1.0
    cr.inputs['To Min'].default_value = 0.8; cr.inputs['To Max'].default_value = 1.08
    L.new(wv.outputs['Fac'], cr.inputs['Value'])
    base = N.new('ShaderNodeRGB'); base.outputs[0].default_value = (*rgb, 1)
    m1 = N.new('ShaderNodeMix'); m1.data_type = 'RGBA'; m1.blend_type = 'MULTIPLY'; m1.inputs['Factor'].default_value = 1.0
    L.new(base.outputs[0], m1.inputs['A']); L.new(cr.outputs['Result'], m1.inputs['B'])
    rs = N.new('ShaderNodeMapRange'); rs.inputs['From Min'].default_value = 0.55; rs.inputs['From Max'].default_value = 0.75
    L.new(nz.outputs['Fac'], rs.inputs['Value'])
    m2 = N.new('ShaderNodeMix'); m2.data_type = 'RGBA'
    L.new(rs.outputs['Result'], m2.inputs['Factor']); L.new(m1.outputs['Result'], m2.inputs['A']); m2.inputs['B'].default_value = (0.2, 0.08, 0.04, 1)
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35
    L.new(wv.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs['Normal'], pb.inputs['Normal'])
    col = S.snow_mix(mat, m2.outputs['Result'])
    L.new(col, pb.inputs['Base Color'])
    S.fog_wrap(mat, pb.outputs['BSDF'])
    _mats[name] = mat
    return mat


def radome_mat():
    mat, N, L, pb = _base('C_Radome')
    pb.inputs['Roughness'].default_value = 0.45
    at = N.new('ShaderNodeAttribute'); at.attribute_name = 'pv'
    geo = N.new('ShaderNodeNewGeometry'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], sep.inputs['Vector'])
    ob = N.new('ShaderNodeTexCoord'); so = N.new('ShaderNodeSeparateXYZ'); L.new(ob.outputs['Object'], so.inputs['Vector'])
    grd = N.new('ShaderNodeMapRange'); grd.inputs['From Min'].default_value = -2.0; grd.inputs['From Max'].default_value = 2.5
    grd.inputs['To Min'].default_value = 0.78; grd.inputs['To Max'].default_value = 1.0
    L.new(so.outputs['Z'], grd.inputs['Value'])
    m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; L.new(at.outputs['Fac'], m1.inputs[0]); L.new(grd.outputs['Result'], m1.inputs[1])
    cr = N.new('ShaderNodeCombineColor'); L.new(m1.outputs['Value'], cr.inputs['Red']); L.new(m1.outputs['Value'], cr.inputs['Green'])
    m2 = N.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; m2.inputs[1].default_value = 1.02; L.new(m1.outputs['Value'], m2.inputs[0])
    L.new(m2.outputs['Value'], cr.inputs['Blue'])
    col = S.snow_mix(mat, cr.outputs['Color'])
    L.new(col, pb.inputs['Base Color'])
    S.fog_wrap(mat, pb.outputs['BSDF'])
    _mats['C_Radome'] = mat
    return mat


# ------------------------------------------------------------------ mesh builder
class MB:
    def __init__(self, name, mats):
        self.name, self.mats = name, list(mats)
        self.bm = bmesh.new()

    def _mi(self, faces, mi):
        for f in faces:
            f.material_index = mi

    def box(self, c, s, mi=0, rz=0.0, rx=0.0, ry=0.0):
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        M = (Matrix.Translation(Vector(c)) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(ry, 4, 'Y') @ Matrix.Rotation(rx, 4, 'X')
             @ Matrix.Diagonal((s[0], s[1], s[2], 1.0)))
        bmesh.ops.transform(self.bm, matrix=M, verts=r['verts'])
        self._mi({f for v in r['verts'] for f in v.link_faces}, mi)
        return r['verts']

    def cyl(self, c, r, h, mi=0, seg=16, axis='Z', r2=None, rz=0.0, caps=True):
        res = bmesh.ops.create_cone(self.bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r,
                                    radius2=(r if r2 is None else r2), depth=h)
        rot = {'Z': Matrix.Identity(4), 'X': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'Y': Matrix.Rotation(math.pi / 2, 4, 'X')}[axis]
        bmesh.ops.transform(self.bm, matrix=Matrix.Translation(Vector(c)) @ Matrix.Rotation(rz, 4, 'Z') @ rot, verts=res['verts'])
        self._mi({f for v in res['verts'] for f in v.link_faces}, mi)
        return res['verts']

    def rod(self, a, b, r, mi=0, seg=6):
        a, b = Vector(a), Vector(b)
        d = b - a
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=d.length)
        q = d.to_track_quat('Z', 'Y')
        bmesh.ops.transform(self.bm, matrix=Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4(), verts=res['verts'])
        self._mi({f for v in res['verts'] for f in v.link_faces}, mi)

    def sphere(self, c, r, mi=0, sub=2, sz=1.0):
        res = bmesh.ops.create_icosphere(self.bm, subdivisions=sub, radius=r)
        bmesh.ops.transform(self.bm, matrix=Matrix.Translation(Vector(c)) @ Matrix.Diagonal((1, 1, sz, 1)), verts=res['verts'])
        self._mi({f for v in res['verts'] for f in v.link_faces}, mi)

    def done(self, smooth=False):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me); self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        if smooth:
            me.shade_smooth()
        return bpy.data.objects.new(self.name, me)


# ------------------------------------------------------------------ kit meshes from the export
_kit = {}


def kit_mesh(name):
    if name in _kit:
        return _kit[name]
    m = MAPJ
    d = next(d for d in m['meshes']['list'] if d['name'] == name)
    matd = {x['name']: x for x in m['materials']}
    mats_ = {}
    for n in d.get('materials', []):
        mats_[n] = bpy.data.materials.get(n) or S.game_material(matd[n])
    me = S.load_meshes(m, {d['id']}, mats_, BLOB)[d['id']][0]
    _kit[name] = me
    return me


def kit_group(root_name, u, v, theta=0.0, h=None, only=None):
    """a placed prefab of the map (all its meshes, as composed under its root) at a new spot"""
    m = MAPJ
    r = next(r for r in m['roots'] if r['name'] == root_name)
    Ri = S.mat4(r['matrix']).inverted()
    T = Matrix.Translation(P(u, v, h)) @ Matrix.Rotation(Y.ROTZ + math.radians(theta), 4, 'Z')
    md = {d['id']: d for d in m['meshes']['list']}
    matd = {x['name']: x for x in m['materials']}
    for i in m['instances']:
        if i['root'] != r['key'] or (only and not any(i['name'].startswith(o) for o in only)):
            continue
        if i['mesh'] not in _kit:
            d = md[i['mesh']]
            mats_ = {n: (bpy.data.materials.get(n) or S.game_material(matd[n])) for n in d.get('materials', [])}
            _kit[i['mesh']] = S.load_meshes(m, {d['id']}, mats_, BLOB)[d['id']][0]
        ob = bpy.data.objects.new('G_' + i['name'], _kit[i['mesh']])
        ob.matrix_world = T @ Ri @ S.mat4(i['matrix'])
        COL.objects.link(ob)


def kit(name, u, v, theta=0.0, h=None, dz=0.0, col=None):
    me = kit_mesh(name)
    ob = bpy.data.objects.new('K_' + name, me)
    hh = (float(G.at(u, v)) if h is None else h) + dz
    put(ob, u, v, hh, theta, col)
    return ob


# ------------------------------------------------------------------ roof snow from top faces
def top_snow(ob, thick=0.28, min_up=0.9, min_h=1.2, bevel=0.1, name=None, mat=None, solid=True, cover=None):
    """snow slabs on the up-facing faces of an object (as ForestWinterStep's caps, thicker): faces with normal z > min_up
    higher than min_h over the ground"""
    me = ob.data
    Mw = Matrix.LocRotScale(ob.location, ob.rotation_euler, ob.scale)       # matrix_world is stale until a depsgraph update
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(Mw)
    bm.normal_update()
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.z < min_up or f.calc_area() < 0.02:
            kill.append(f); continue
        u, v = Y.blender_to_uv(c.x, c.y)
        if c.z - float(G.at(float(u), float(v))) < min_h:
            kill.append(f); continue
        if cover is not None:                       # only the topmost surface (no snow on floors inside)
            Hc, cu0, cv0, cst = cover
            i, j = int((float(u) - cu0) / cst), int((float(v) - cv0) / cst)
            if 0 <= j < Hc.shape[0] and 0 <= i < Hc.shape[1] and np.isfinite(Hc[j, i]) and c.z < Hc[j, i] - 0.35:
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
    if solid:
        md = so.modifiers.new('solid', 'SOLIDIFY'); md.thickness = thick; md.offset = 1.0; md.use_even_offset = True
        if bevel:
            bv = so.modifiers.new('bevel', 'BEVEL'); bv.width = bevel; bv.segments = 2; bv.limit_method = 'ANGLE'
            bv.angle_limit = math.radians(50)
    return so


def cornice(name, pts_uvh, out_uv, r=0.22, sag=0.12, icicles=True, ice_len=(0.15, 0.8), every=(0.25, 0.7)):
    """snow cornice along a roof edge (a squashed tube pushed out over the edge) + icicles hanging under it.
    pts_uvh: edge points (u, v, h top of the roof snow); out_uv: outward unit direction (yard)"""
    mb = MB(name, [MAT['snow_clean'], MAT['ice']])
    ou, ov = out_uv
    pts = [Vector(P(u, v, h)) for u, v, h in pts_uvh]
    ox, oy = Y.uv_to_blender_xy(np.array([0.0, ou]), np.array([0.0, ov]))
    outv = Vector((ox[1] - ox[0], oy[1] - oy[0], 0)).normalized()
    total = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        d = b - a; L = d.length
        n = max(1, int(L / 0.6))
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            p0 = a + d * t0 + outv * (r * 0.6) + Vector((0, 0, -sag * (0.6 + 0.4 * RNG.random())))
            p1 = a + d * t1 + outv * (r * 0.6) + Vector((0, 0, -sag * (0.6 + 0.4 * RNG.random())))
            rr = r * (0.75 + 0.5 * RNG.random())
            mb.rod(p0, p1, rr, 0, seg=8)
        if icicles:
            s = 0.0
            while s < L:
                s += every[0] + (every[1] - every[0]) * RNG.random()
                if s >= L:
                    break
                p = a + d * (s / L) + outv * (r * 0.9)
                ln = ice_len[0] + (ice_len[1] - ice_len[0]) * RNG.random() ** 2
                rad = 0.025 + 0.035 * RNG.random()
                res = bmesh.ops.create_cone(mb.bm, cap_ends=True, cap_tris=False, segments=5, radius1=0.0, radius2=rad, depth=ln)
                bmesh.ops.transform(mb.bm, matrix=Matrix.Translation(p + Vector((0, 0, -ln / 2 - r * 0.3))), verts=res['verts'])
                for f in {f for v in res['verts'] for f in v.link_faces}:
                    f.material_index = 1
        total += L
    ob = mb.done(smooth=True)
    COL.objects.link(ob)
    return ob


# ------------------------------------------------------------------ elements
def H_main():
    """heights of the main building on the yard grid (analyze_roof.py BaseMain -12 -9 20 12 0.5)"""
    return np.load(os.path.join(D, 'data', 'H_BaseMain.npy')), (-12.0, -9.0, 0.5)


def radome():
    H, (u0, v0, st) = H_main()
    pu0, pv0, pu1, pv1 = -0.4, -1.6, 6.8, 5.6
    i0, i1 = int((pu0 - u0) / st), int((pu1 - u0) / st); j0, j1 = int((pv0 - v0) / st), int((pv1 - v0) / st)
    roof = float(np.median(H[j0:j1, i0:i1]))
    cu, cv = (pu0 + pu1) / 2, (pv0 + pv1) / 2
    w, ph = pu1 - pu0, 3.0
    mb = MB('Radome_Plinth', [MAT['concrete'], MAT['steel_dark'], MAT['olive'], MAT['steel']])
    mb.box((0, 0, ph / 2), (w, w, ph), 0)
    mb.box((0, 0, ph + 0.12), (w + 0.25, w + 0.25, 0.24), 0)                        # coping
    for side in range(4):                                                          # louvre band
        a = side * math.pi / 2
        mb.box((math.cos(a) * (w / 2 + 0.02), math.sin(a) * (w / 2 + 0.02), 1.9), (0.05 if side % 2 == 0 else w * 0.8,
                                                                                    w * 0.8 if side % 2 == 0 else 0.05, 0.55), 1)
    mb.box((-1.4, w / 2 + 0.04, 1.05), (1.0, 0.08, 2.1), 2)                         # door to the roof (north)
    mb.box((-1.4, w / 2 + 0.75, 0.05), (1.6, 1.4, 0.1), 3)                          # landing grate
    for k in range(9):                                                             # ladder on the west face
        mb.box((-w / 2 - 0.25, 1.6, 0.3 + k * 0.32), (0.04, 0.5, 0.04), 3)
    for s in (-0.25, 0.25):
        mb.box((-w / 2 - 0.25, 1.6 + s, ph / 2 + 0.4), (0.05, 0.05, ph + 0.8), 3)
    ob = mb.done(); put(ob, cu, cv, roof, 0.0)
    # the radome: geodesic panels on a ring
    R = 4.0; base = roof + ph + 0.24
    mb = MB('Radome', [MAT['radome'], MAT['steel'], MAT['steel_dark'], MAT['redlight']])
    mb.cyl((0, 0, 0.2), R * 0.9, 0.4, 1, seg=32)
    res = bmesh.ops.create_icosphere(mb.bm, subdivisions=3, radius=R)
    zc = 0.4 + 0.42 * R
    bmesh.ops.translate(mb.bm, vec=Vector((0, 0, zc)), verts=res['verts'])
    kill = [v for v in res['verts'] if v.co.z < zc - 0.5 * R]
    bmesh.ops.delete(mb.bm, geom=kill, context='VERTS')
    faces = [f for f in mb.bm.faces if f.material_index == 0 and len(f.verts) == 3]
    for f in faces:
        f.material_index = 0
    ins = bmesh.ops.inset_individual(mb.bm, faces=faces, thickness=0.03, depth=0.01)
    for f in ins['faces']:
        f.material_index = 1
    mb.rod((0, 0, zc + R - 0.05), (0, 0, zc + R + 1.6), 0.025, 1)                 # lightning rod
    mb.sphere((0, 0, zc + R + 0.15), 0.13, 3, sub=1)                               # obstruction light
    ob2 = mb.done(smooth=False)
    me = ob2.data
    pv = me.attributes.new('pv', 'FLOAT', 'FACE')
    pv.data.foreach_set('value', np.array([0.9 + 0.1 * RNG.random() for _ in me.polygons], np.float32))
    put(ob2, cu, cv, base, 0.0)
    # thin snow on its crown
    s = top_snow(ob2, thick=0.07, min_up=0.93, min_h=5.0, bevel=0.0, name='Radome_crown')
    top_snow(ob, thick=0.25, min_up=0.9, min_h=5.0, bevel=0.06, name='Radome_plinth')
    print('[concept] radome on the roof at', round(roof, 2), 'top', round(base + zc + R, 2), flush=True)
    return roof


def boiler_house():
    cu, cv, su, sv, hh = -17.0, -20.0, 10.0, 7.0, 5.2
    mb = MB('BoilerHouse', [MAT['concrete_dark'], MAT['olive'], MAT['glass'], MAT['steel_dark'], MAT['concrete']])
    mb.box((0, 0, hh / 2), (su, sv, hh), 0)
    for (x, y, sx, sy) in ((0, sv / 2 - 0.12, su, 0.25), (0, -sv / 2 + 0.12, su, 0.25), (su / 2 - 0.12, 0, 0.25, sv), (-su / 2 + 0.12, 0, 0.25, sv)):
        mb.box((x, y, hh + 0.2), (sx, sy, 0.4), 4)                                   # parapet
    mb.box((-2.5, sv / 2 + 0.03, 1.25), (2.2, 0.08, 2.5), 1)                        # double door, north
    mb.box((-2.5, sv / 2 + 0.07, 1.25), (0.04, 0.04, 2.4), 3)
    mb.box((1.5, sv / 2 + 0.03, 2.4), (1.4, 0.06, 0.9), 2)                          # window
    mb.box((3.6, sv / 2 + 0.03, 2.4), (1.4, 0.06, 0.9), 2)
    mb.box((-su / 2 - 0.03, 0, 3.6), (0.06, 1.6, 0.9), 3)                           # louvre west
    mb.box((-2.5, sv / 2 + 0.5, 2.75), (2.8, 1.0, 0.12), 3)                         # door hood
    mb.box((su / 2 - 0.4, sv / 2 + 0.08, hh / 2), (0.12, 0.12, hh), 3)              # downpipe
    mb.box((-2.5, sv / 2 + 0.9, 0.08), (2.6, 1.6, 0.16), 4)                         # step
    ob = mb.done(); put(ob, cu, cv, None, 0.0)
    g0 = float(G.at(cu, cv))
    # roof snow inside the parapet (+ on it)
    mb = MB('BoilerHouse_snow', [MAT['snow_clean']])
    mb.box((0, 0, hh + 0.2), (su - 0.5, sv - 0.5, 0.42), 0)
    so = mb.done(); put(so, cu, cv, g0, 0.0)
    bv = so.modifiers.new('b', 'BEVEL'); bv.width = 0.15; bv.segments = 3
    top_snow(ob, thick=0.12, min_up=0.9, min_h=2.0, bevel=0.04, name='BoilerHouse_parapet')
    # north eave cornice + icicles over the door (warm)
    cornice('BoilerHouse_cornice', [(cu - su / 2 + 0.2, cv + sv / 2 - 0.05, g0 + hh + 0.55), (cu + su / 2 - 0.2, cv + sv / 2 - 0.05, g0 + hh + 0.55)],
            (0, 1), r=0.2, sag=0.1, ice_len=(0.1, 0.9))
    # chimney: steel stack 22 m, red / white top, guys
    ch_u, ch_v = cu + su / 2 + 1.2, cv - 1.0
    H_ = 22.0
    mb = MB('Chimney', [MAT['steel_dark'], MAT['rw_band'], MAT['soot'], MAT['concrete'], MAT['steel']])
    mb.box((0, 0, 0.25), (2.0, 2.0, 0.5), 3)
    mb.cyl((0, 0, (H_ - 4.0) / 2 + 0.5), 0.55, H_ - 4.5, 0, seg=20, r2=0.47)
    mb.cyl((0, 0, H_ - 2.0), 0.47, 3.0, 1, seg=20)
    mb.cyl((0, 0, H_ - 0.2), 0.48, 0.6, 2, seg=20)
    mb.cyl((0, 0, H_ + 0.15), 0.56, 0.12, 4, seg=20)
    mb.cyl((-0.6, 0, 4.2), 0.3, 1.4, 0, seg=12, axis='X')                            # flue from the house
    for k in range(int((H_ - 2) / 0.4)):                                            # ladder
        mb.box((0.62, 0, 1.2 + k * 0.4), (0.04, 0.45, 0.04), 4)
    for s in (-0.22, 0.22):
        mb.box((0.62, s, H_ / 2 + 0.3), (0.05, 0.05, H_ - 1.5), 4)
    gtop = 15.0
    for ang in (35.0, 160.0, 270.0):
        a = math.radians(ang)
        mb.rod((0.45 * math.cos(a), 0.45 * math.sin(a), gtop), (9.0 * math.cos(a), 9.0 * math.sin(a), 0.2), 0.012, 4, seg=4)
        mb.box((9.0 * math.cos(a), 9.0 * math.sin(a), 0.15), (0.5, 0.5, 0.3), 3)
    och = mb.done(smooth=False); put(och, ch_u, ch_v, None, 0.0)
    gch = float(G.at(ch_u, ch_v))
    # smoke: drifting north-east with the wind, rising
    sm = MAT['smoke']
    top = P(ch_u, ch_v, gch + H_ + 0.4)
    wx, wy = Y.uv_to_blender_xy(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    wdir = Vector((wx[1] - wx[0], wy[1] - wy[0], 0)).normalized()
    for k in range(9):
        t = k / 8.0
        c = top + wdir * (t * 18.0) + Vector((0, 0, 0.8 + 6.5 * math.sqrt(t)))
        r = 0.6 + 2.6 * t
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        me = bpy.data.meshes.new('Smoke%d' % k); bm.to_mesh(me); bm.free(); me.materials.append(sm)
        o = bpy.data.objects.new('Smoke%d' % k, me); o.location = c
        o.scale = (r * (1.2 + 0.3 * RNG.random()), r, r * 0.8)
        o.rotation_euler = (RNG.random(), RNG.random(), RNG.random())
        o['dens'] = 0.5 * (1.0 - 0.85 * t)
        COL.objects.link(o)
    # oil tank in a bund, south of the house
    tu, tv = cu, cv - sv / 2 - 4.6
    mb = MB('OilTank', [MAT['concrete'], MAT['drum_green'], MAT['steel'], MAT['yb']])
    for (x, y, sx, sy) in ((0, 1.6, 6.4, 0.2), (0, -1.6, 6.4, 0.2), (3.1, 0, 0.2, 3.2), (-3.1, 0, 0.2, 3.2)):
        mb.box((x, y, 0.3), (sx, sy, 0.6), 0)
    for x in (-1.3, 1.3):
        mb.box((x, 0, 0.25), (0.4, 1.4, 0.5), 0)
    mb.cyl((0, 0, 1.3), 0.82, 4.2, 1, seg=20, axis='X')
    mb.rod((1.2, 0, 2.0), (1.2, 0, 2.6), 0.06, 2)
    mb.rod((-1.6, 0.0, 2.05), (-1.6, 0.0, 2.35), 0.12, 2)
    for x, y in ((-3.6, 2.0), (3.6, 2.0)):
        mb.cyl((x, y, 0.55), 0.1, 1.1, 3, seg=10)
    ot = mb.done(); put(ot, tu, tv, None, 0.0)
    top_snow(ot, thick=0.16, min_up=0.75, min_h=0.3, bevel=0.05, name='OilTank')
    for k, (du, dv, m) in enumerate(((2.2, -0.9, 'drum_blue'), (2.3, 0.0, 'drum_blue'), (-2.3, -0.8, 'drum_red'))):
        drum(tu + du, tv + dv, m)
    OBST.extend([(cu - su / 2, cv - sv / 2, cu + su / 2, cv + sv / 2, hh), (tu - 3.2, tv - 1.7, tu + 3.2, tv + 1.7, 1.6)])
    CLEAR.extend([(cu - su / 2 - 1.5, tv - 2.5, ch_u + 2.0, cv + sv / 2 + 2.5)])
    print('[concept] boiler house + chimney', flush=True)


def drum(u, v, m, lying=False, theta=0.0, h=None):
    mb = MB('Drum', [MAT[m], MAT['steel_dark']])
    if lying:
        mb.cyl((0, 0, 0.3), 0.29, 0.88, 0, seg=14, axis='X')
        for x in (-0.3, 0.3):
            mb.cyl((x, 0, 0.3), 0.3, 0.04, 1, seg=14, axis='X')
    else:
        mb.cyl((0, 0, 0.44), 0.29, 0.88, 0, seg=14)
        for z in (0.3, 0.6):
            mb.cyl((0, 0, z), 0.3, 0.04, 1, seg=14)
    ob = mb.done(); put(ob, u, v, h, theta)
    return ob


def pallet(u, v, theta=0.0, drums=None, h=None):
    mb = MB('Pallet', [MAT['wood']])
    for y in (-0.45, 0.0, 0.45):
        mb.box((0, y, 0.06), (1.2, 0.1, 0.12), 0)
    for x in (-0.55, -0.27, 0.0, 0.27, 0.55):
        mb.box((x, 0, 0.14), (0.1, 1.0, 0.03), 0)
    ob = mb.done(); put(ob, u, v, h, theta)
    g0 = float(G.at(u, v)) if h is None else h
    if drums:
        for (du, dv), m in zip(((-0.3, -0.25), (0.3, -0.25), (-0.3, 0.27), (0.3, 0.27)), drums):
            c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
            drum(u + du * c - dv * s, v + du * s + dv * c, m, h=g0 + 0.16)
    return ob


def container(name, u, v, theta, mat, h=None, doors_out=1, snow=True):
    L_, W_, H_ = 6.06, 2.44, 2.59
    mb = MB(name, [MAT[mat], MAT['steel_dark'], MAT['rust']])
    mb.box((0, 0, H_ / 2), (L_ - 0.1, W_ - 0.1, H_ - 0.1), 0)
    for x in (-L_ / 2 + 0.08, L_ / 2 - 0.08):                                        # corner posts and rails
        for y in (-W_ / 2 + 0.08, W_ / 2 - 0.08):
            mb.box((x, y, H_ / 2), (0.16, 0.16, H_), 1)
    for z in (0.08, H_ - 0.08):
        for y in (-W_ / 2 + 0.06, W_ / 2 - 0.06):
            mb.box((0, y, z), (L_, 0.14, 0.16), 1)
    xd = doors_out * (L_ / 2 + 0.01)
    for y in (-0.6, -0.25, 0.25, 0.6):                                              # lock bars
        mb.box((xd, y, H_ / 2), (0.04, 0.05, H_ - 0.3), 1)
    mb.box((xd, 0, 0.5), (0.03, 2.2, 0.3), 2)                                       # rust at the door foot
    ob = mb.done(); put(ob, u, v, h, theta)
    if snow:
        g0 = float(G.at(u, v)) if h is None else h
        sb = MB(name + '_snow', [MAT['snow_clean']])
        sb.box((0, 0, H_ + 0.12), (L_ - 0.05, W_ - 0.05, 0.24), 0)
        so = sb.done(); put(so, u, v, g0, theta)
        bv = so.modifiers.new('b', 'BEVEL'); bv.width = 0.1; bv.segments = 3
    OBST.append(rect_c(u, v, L_, W_, theta) + (H_ if h is None else H_ + (h - float(G.at(u, v))),))
    return ob


def garage_row():
    out = []
    for u in (4.0, -10.0):
        ob = kit('Garage', u, -42.5, theta=180.0, dz=0.0)
        out.append(ob)
        OBST.append((u - 5.8, -47.0, u + 5.8, -38.0, 5.0))
        CLEAR.append((u - 7.0, -49.5, u + 7.0, -33.0))
        # snow on the roof, a cornice + icicles on the north eave (doors side)
    return out


def workshop():
    """corrugated workshop / store against the west fence, doors to the yard; a lean-to with timber beside it"""
    cu, cv, su, sv = -62.0, -6.0, 9.0, 14.0
    wall, ridge = 4.2, 5.8
    mb = MB('Workshop', [MAT['corr_dark'], MAT['steel_dark'], MAT['olive'], MAT['glass'], MAT['concrete']])
    mb.box((0, 0, wall / 2), (su, sv, wall), 0)
    bm = mb.bm                                                                      # gable roof
    hu = su / 2 + 0.35; hv = sv / 2 + 0.3
    v1 = [bm.verts.new(Vector(p)) for p in ((-hu, -hv, wall - 0.1), (0, -hv, ridge), (0, hv, ridge), (-hu, hv, wall - 0.1))]
    v2 = [bm.verts.new(Vector(p)) for p in ((0, -hv, ridge), (hu, -hv, wall - 0.1), (hu, hv, wall - 0.1), (0, hv, ridge))]
    for vs in (v1, v2):
        f = bm.faces.new(vs); f.material_index = 1
        f.normal_update()
        if f.normal.z < 0:
            f.normal_flip()
    for y in (-sv / 2, sv / 2):                                                     # gables
        g = [bm.verts.new(Vector(p)) for p in ((-su / 2, y, wall), (su / 2, y, wall), (0, y, ridge - 0.1))]
        f = bm.faces.new(g); f.material_index = 0
        f.normal_update()
        if f.normal.y * y < 0:
            f.normal_flip()
    mb.box((su / 2 + 0.04, 1.5, 1.9), (0.08, 4.6, 3.8), 2)                          # sliding door, east (yard)
    mb.box((su / 2 + 0.1, 1.5, 3.95), (0.12, 6.0, 0.12), 1)                         # door rail
    mb.box((su / 2 + 0.04, -4.2, 1.05), (0.08, 1.0, 2.1), 2)                        # personnel door
    for y in (-2.5, 5.2):
        mb.box((su / 2 + 0.04, y, 3.2), (0.06, 1.6, 0.6), 3)
    mb.box((su / 2 + 1.2, 1.5, 0.06), (2.4, 5.0, 0.12), 4)                          # apron
    ob = mb.done(); put(ob, cu, cv, None, 0.0)
    g0 = float(G.at(cu, cv))
    # snow on the two roof planes (thicker on the lee, north-east side)
    for side, th in ((-1, 0.22), (1, 0.42)):
        sb = MB('Workshop_snow%d' % side, [MAT['snow_clean']])
        ang = math.atan2(ridge - wall, hu)
        sb.box((side * hu / 2, 0, (ridge + wall) / 2 + th / 2 + 0.02), (hu / math.cos(ang) + 0.1, sv + 0.5, th), 0, ry=side * ang)
        so = sb.done(); put(so, cu, cv, g0, 0.0)
        bv = so.modifiers.new('b', 'BEVEL'); bv.width = 0.1; bv.segments = 2
    cornice('Workshop_cornice', [(cu + hu + 0.05, cv - sv / 2, g0 + wall + 0.3), (cu + hu + 0.05, cv + sv / 2, g0 + wall + 0.3)],
            (1, 0), r=0.24, sag=0.15, ice_len=(0.1, 0.7), every=(0.3, 0.9))
    # lean-to with stacked timber and pallets
    lu, lv = cu + 1.0, cv - sv / 2 - 4.5
    mb = MB('LeanTo', [MAT['wood'], MAT['corr_dark'], MAT['steel_dark']])
    for x in (-3.0, 0.0, 3.0):
        mb.box((x, 1.6, 1.4), (0.15, 0.15, 2.8), 0)
        mb.box((x, -1.6, 1.15), (0.15, 0.15, 2.3), 0)
    mb.box((0, 0, 2.6), (6.8, 3.9, 0.08), 1, rx=math.radians(-4.5))
    for k in range(4):
        mb.box((-1.4, -0.4 + k * 0.02, 0.15 + k * 0.22), (3.6, 1.8, 0.2), 0)          # planks
    for k in range(3):
        mb.box((1.9, 0.0, 0.07 + k * 0.15), (1.2, 1.0, 0.13), 0)                       # pallets
    ob2 = mb.done(); put(ob2, lu, lv, None, 0.0)
    sb = MB('LeanTo_snow', [MAT['snow_clean']])
    sb.box((0, 0, 2.82), (7.0, 4.1, 0.3), 0, rx=math.radians(-4.5))
    so = sb.done(); put(so, lu, lv, g0, 0.0)
    bv = so.modifiers.new('b', 'BEVEL'); bv.width = 0.12; bv.segments = 2
    OBST.extend([(cu - su / 2, cv - sv / 2, cu + su / 2, cv + sv / 2, ridge), (lu - 3.4, lv - 2.0, lu + 3.4, lv + 2.0, 1.2)])
    CLEAR.append((cu - su / 2 - 1.0, lv - 3.0, cu + su / 2 + 4.0, cv + sv / 2 + 1.5))


def north_storage():
    """storage against the north fence, east of the gate (left of the yard frames): containers, drums on pallets, gas
    bottles, crates, cable drums, a shovel in the drift"""
    container('Cont_N1', 4.5, 43.7, 0.0, 'cont_red', doors_out=1)
    container('Cont_N2', 11.0, 43.7, 0.0, 'cont_blue', doors_out=1)
    container('Cont_N3', 4.7, 43.7, 0.0, 'cont_olive', h=float(G.at(4.5, 43.7)) + 2.59, doors_out=1)
    pallet(16.0, 40.6, 8.0, ['drum_blue', 'drum_blue', 'drum_blue', 'drum_red'])
    pallet(17.6, 42.3, -5.0, ['drum_red', 'drum_red', 'drum_blue'])
    drum(19.2, 40.5, 'drum_blue', lying=True, theta=30.0)
    for k in range(5):                                                               # gas bottles against the fence
        mb = MB('GasBottle', [MAT['drum_green'] if k % 2 else MAT['steel'], MAT['steel_dark']])
        mb.cyl((0, 0, 0.7), 0.12, 1.4, 0, seg=10); mb.cyl((0, 0, 1.45), 0.06, 0.12, 1, seg=8)
        put(mb.done(), 21.0 + k * 0.32, 45.6, None, 0.0)
    container('Cont_N4', 27.5, 33.4, 90.0, 'cont_olive', doors_out=-1)
    container('Cont_N5', 27.5, 40.0, 90.0, 'cont_red', doors_out=-1)
    container('Cont_N6', 27.4, 40.3, 90.0, 'cont_blue', h=float(G.at(27.5, 40.0)) + 2.59, doors_out=-1)
    kit('Crates', 22.0, 37.6, theta=12.0)
    kit('Crates', 20.6, 35.1, theta=-6.0)
    kit('Crates', 23.2, 35.6, theta=80.0)
    kit('Cable_Drum', 24.0, 31.6, theta=70.0)
    mb = MB('Shovel', [MAT['wood'], MAT['steel_dark']])
    mb.box((0, 0, 0.7), (0.04, 0.04, 1.3), 0, ry=0.25); mb.box((0.17, 0, 0.05), (0.28, 0.03, 0.34), 1, ry=0.25)
    put(mb.done(), 14.6, 40.2, float(G.at(14.6, 40.2)) + 0.25, 30.0)
    OBST.extend([(15.2, 39.8, 20.0, 43.0, 1.0), (19.5, 34.0, 24.0, 38.6, 1.0)])
    CLEAR.append((0.0, 29.0, 32.0, 46.7))


def east_zone():
    """GenContainer exhaust + soot; a bund round the fuel tanks with drums and a hand pump; containers on the east fence"""
    # generator exhaust: a stack over the roof at the east end, soot on the roof and wall
    gu, gv = 35.2, 23.6
    mb = MB('GenExhaust', [MAT['steel_dark'], MAT['soot']])
    mb.cyl((2.9, -0.6, 3.4), 0.12, 1.8, 0, seg=10)
    mb.cyl((2.9, -0.6, 4.35), 0.16, 0.12, 1, seg=10)
    mb.box((2.95, -1.3, 2.6), (1.4, 0.03, 2.0), 1)                                   # soot streak on the wall
    mb.box((2.6, -0.4, 3.73), (2.6, 1.8, 0.02), 1)                                   # soot on the roof
    put(mb.done(), gu, gv, None, 180.0)
    # bund round the fuel tanks (FuelTanks keepClear 38.3..46.6, 13.1..21.7)
    bu0, bv0, bu1, bv1 = 37.6, 12.4, 47.3, 22.4
    mb = MB('FuelBund', [MAT['concrete'], MAT['yb']])
    for (x0, y0, x1, y1) in ((bu0, bv0, bu1, bv0 + 0.25), (bu0, bv1 - 0.25, bu1, bv1), (bu0, bv0, bu0 + 0.25, bv1), (bu1 - 0.25, bv0, bu1, bv1)):
        mb.box(((x0 + x1) / 2 - (bu0 + bu1) / 2, (y0 + y1) / 2 - (bv0 + bv1) / 2, 0.35), (x1 - x0, y1 - y0, 0.7), 0)
    for (x, y) in ((bu0 - 0.5, bv0 - 0.5), (bu0 - 0.5, bv1 + 0.5), (bu1 + 0.5, bv0 - 0.5)):
        mb.cyl((x - (bu0 + bu1) / 2, y - (bv0 + bv1) / 2, 0.6), 0.11, 1.2, 1, seg=10)
    put(mb.done(), (bu0 + bu1) / 2, (bv0 + bv1) / 2, None, 0.0)
    for k, (u, v, m) in enumerate(((36.4, 14.0, 'drum_red'), (36.5, 14.7, 'drum_red'), (35.9, 14.4, 'drum_blue'), (36.9, 13.4, 'drum_blue'))):
        drum(u, v, m)
    drum(35.6, 15.6, 'drum_red', lying=True, theta=70.0)
    mb = MB('HandPump', [MAT['red'], MAT['steel_dark']])
    mb.cyl((0, 0, 0.7), 0.05, 1.0, 1, seg=8); mb.box((0, 0, 1.25), (0.25, 0.15, 0.3), 0); mb.rod((0.1, 0, 1.3), (0.45, 0, 1.6), 0.02, 1)
    put(mb.done(), 36.4, 14.35, float(G.at(36.4, 14.35)) + 0.88, 0.0)
    # containers along the east fence
    container('Cont_E1', 66.6, -31.0, 90.0, 'cont_blue', doors_out=-1)
    container('Cont_E2', 66.6, -24.4, 90.0, 'cont_red', doors_out=-1)
    container('Cont_E3', 66.6, -30.8, 90.0, 'cont_olive', h=float(G.at(66.6, -31.0)) + 2.59, doors_out=-1)
    container('Cont_E4', 66.6, -38.0, 90.0, 'cont_olive', doors_out=-1)
    CLEAR.append((60.0, -42.0, 70.7, -20.0))


def rubbish():
    """rubbish corner behind the main building: a skip, wheelie bins, bags"""
    su, sv = 12.8, -11.4
    mb = MB('Skip', [MAT['cont_olive'], MAT['steel_dark'], MAT['bag']])
    bm = mb.bm
    lo, hi = (1.7, 0.85), (2.0, 1.0)
    vs = [bm.verts.new(Vector(p)) for p in ((-lo[0], -lo[1], 0.1), (lo[0], -lo[1], 0.1), (lo[0], lo[1], 0.1), (-lo[0], lo[1], 0.1),
                                            (-hi[0], -hi[1], 1.3), (hi[0], -hi[1], 1.3), (hi[0], hi[1], 1.3), (-hi[0], hi[1], 1.3))]
    for q in ((0, 3, 2, 1), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        f = bm.faces.new([vs[i] for i in q]); f.material_index = 0
    mb.box((0, 0, 1.0), (3.6, 1.7, 0.5), 2)                                          # rubbish inside
    put(mb.done(), su, sv, None, 4.0)
    for k, (du, dv) in enumerate(((2.6, 0.8), (3.4, 0.8))):
        mb = MB('WheelieBin', [MAT['bin'], MAT['black']])
        mb.box((0, 0, 0.55), (0.6, 0.7, 1.05), 0); mb.box((0, -0.05, 1.1), (0.64, 0.8, 0.06), 1)
        put(mb.done(), su + du, sv + dv, None, 6.0 * k)
    for k in range(6):
        mb = MB('Bag', [MAT['bag']])
        mb.sphere((0, 0, 0.22), 0.36, 0, sub=2, sz=0.62)
        put(mb.done(), su - 2.2 + RNG.uniform(-0.6, 0.6), sv + RNG.uniform(-0.9, 0.9), None, RNG.uniform(0, 180))
    OBST.append((su - 2.0, sv - 1.0, su + 3.8, sv + 1.2, 1.3))


def parking():
    """parking: the shift van and a car in use, an old car the plough has buried at the west corner"""
    kit('ShiftCar', -3.0, 12.7, theta=88.0)
    kit('StartCar', -24.3, 23.6, theta=2.0)
    wreck = kit('WreckCar', 7.0, 35.2, theta=-70.0, dz=-0.3)
    # the plough: the shift van with a blade, parked on the garage apron
    kit('ShiftCar', 32.6, -11.4, theta=-8.0)
    mb = MB('PloughBlade', [col_mat('C_PloughOrange', (0.85, 0.3, 0.03), rough=0.5), MAT['black'], MAT['steel_dark'], MAT['yb']])
    mb.box((0, 3.05, 0.62), (2.9, 0.12, 0.8), 0, rz=math.radians(-18), rx=math.radians(-14))
    mb.box((0, 2.98, 0.17), (2.9, 0.1, 0.16), 1, rz=math.radians(-18))
    for x in (-0.55, 0.55):
        mb.box((x, 2.55, 0.5), (0.12, 0.9, 0.12), 2)
    for x in (-1.3, 1.3):
        mb.cyl((x * math.cos(math.radians(18)), 3.0 + x * math.sin(math.radians(-18)), 1.35), 0.025, 1.3, 3, seg=6)
    put(mb.done(), 32.6, -11.4, None, -8.0)
    sb = MB('PloughBlade_snow', [MAT['snow_clean']])
    sb.box((0, 3.12, 1.06), (2.9, 0.22, 0.12), 0, rz=math.radians(-18))
    so = sb.done(); put(so, 32.6, -11.4, None, -8.0); bv = so.modifiers.new('b', 'BEVEL'); bv.width = 0.04; bv.segments = 2
    for ob in bpy.data.objects:
        if ob.name.startswith('K_ShiftCar') or ob.name.startswith('K_StartCar') or ob.name.startswith('K_WreckCar'):
            top_snow(ob, thick=0.14 if 'Wreck' not in ob.name else 0.3, min_up=0.8, min_h=0.6, bevel=0.05)
    OBST.extend([(-5.5, 11.6, -0.5, 13.8, 1.8), (-25.3, 21.2, -23.3, 26.0, 1.2), (5.0, 34.2, 9.0, 36.2, 1.1)])


def accents():
    """orange snow poles along the asphalt for the plough, yellow / black bollards at corners, the gate boom"""
    poles = [(-34.6, v) for v in np.arange(13.0, 44.0, 6.0)]
    poles += [(-25.6, v) for v in (33.0, 39.0)]
    poles += [(u, 22.4) for u in np.arange(-4.0, 30.0, 8.0)]
    poles += [(u, 13.6) for u in (-26.0, -18.0, -10.0, 22.0, 28.0)]
    poles += [(26.9, v) for v in np.arange(-8.0, 13.0, 6.0)]
    for (u, v) in poles:
        mb = MB('SnowPole', [MAT['orange'], MAT['black']])
        mb.cyl((0, 0, 0.8), 0.025, 1.6, 0, seg=6); mb.cyl((0, 0, 1.45), 0.03, 0.12, 1, seg=6)
        put(mb.done(), u, v, None, 0.0)
    for (u, v) in ((-6.6, 9.2), (19.4, 9.2), (19.4, -8.6), (-27.0, 9.0), (31.4, 22.0), (31.4, 28.0), (-8.2, 30.6)):
        mb = MB('Bollard', [MAT['yb'], MAT['steel_dark']])
        mb.cyl((0, 0, 0.5), 0.1, 1.0, 0, seg=10); mb.cyl((0, 0, 1.02), 0.11, 0.04, 1, seg=10)
        put(mb.done(), u, v, None, 0.0)
    kit_group('Barrier', -26.4, 40.5, theta=180.0, only=('Barrier', 'IX_BarrierArm', 'Beacon', 'Lens_Beacon'))   # boom over the gate road
    mb = MB('GritBin', [MAT['yellow'], MAT['steel_dark'], MAT['black']])               # grit bin by the parking
    mb.box((0, 0, 0.42), (1.3, 0.8, 0.8), 0); mb.box((0, -0.05, 0.86), (1.36, 0.9, 0.1), 0, rx=0.12)
    mb.box((0, 0.41, 0.55), (0.9, 0.02, 0.16), 2)
    put(mb.done(), -14.2, 34.7, None, -10.0)
    sb = MB('GritBin_snow', [MAT['snow_clean']]); sb.box((0, -0.05, 0.98), (1.3, 0.86, 0.14), 0, rx=0.12)
    so = sb.done(); put(so, -14.2, 34.7, None, -10.0); bv = so.modifiers.new('b', 'BEVEL'); bv.width = 0.05; bv.segments = 2
    print('[concept] accents: %d snow poles' % len(poles), flush=True)


def main_building_details(roof):
    H, (u0, v0, st) = H_main()
    g0 = float(G.at(0.0, 0.0))
    # HVAC units, vents, antennas on the main roof; a dish on the east wing
    mb = MB('RoofKit', [MAT['steel'], MAT['steel_dark'], MAT['white']])
    for (u, v) in ((-5.6, 3.6), (-3.4, 3.6)):
        mb.box((u, v, 0.65), (1.7, 1.1, 1.3), 0)
        mb.cyl((u, v, 1.33), 0.42, 0.06, 1, seg=16)
    for (u, v) in ((-6.8, 0.6), (-1.0, 4.6), (5.6, -3.6), (-4.5, -4.4)):
        mb.cyl((u, v, 0.45), 0.12, 0.9, 1, seg=10); mb.cyl((u, v, 0.95), 0.24, 0.16, 1, seg=10)
    for (u, v, hh) in ((-7.3, 5.5, 3.6), (7.0, -4.8, 3.0), (-7.3, -4.8, 2.6)):
        mb.rod((u, v, 0.2), (u, v, hh), 0.02, 1)
    ob = mb.done()
    ob.location = P(0.0, 0.0, roof); ob.rotation_euler = (0, 0, Y.ROTZ); COL.objects.link(ob)
    wing = g0 + 4.0
    mb = MB('Dish', [MAT['white'], MAT['steel_dark']])
    mb.cyl((0, 0, 0.6), 0.06, 1.2, 1, seg=8)
    res = bmesh.ops.create_cone(mb.bm, cap_ends=False, cap_tris=False, segments=20, radius1=0.08, radius2=0.75, depth=0.35)
    bmesh.ops.transform(mb.bm, matrix=Matrix.Translation(Vector((0.15, 0, 1.35))) @ Matrix.Rotation(math.radians(-65), 4, 'Y'), verts=res['verts'])
    put(mb.done(), 14.5, -2.5, wing, 210.0)
    # cable tray down the north-west corner from the roof to the ground, to the mast feeder
    mb = MB('CableTray', [MAT['steel']])
    mb.box((0, 0, (roof - g0) / 2 + 0.1), (0.35, 0.12, roof - g0 + 0.2), 0)
    put(mb.done(), -7.55, 6.25, g0, 0.0)
    # station sign over the ground-floor windows, north facade
    sign(-0.6, 6.32, g0 + 3.65)
    # porch rails at the entrance steps (under the canopy, u 5..8.5) and the west door
    mb = MB('Rails', [MAT['steel_dark']])
    for x in (-1.6, 1.6):
        for y in (0.0, 1.2):
            mb.rod((x, y, 0.0), (x, y, 1.0), 0.025, 0)
        mb.rod((x, -0.1, 1.0), (x, 1.3, 0.75), 0.025, 0)
    put(mb.done(), 6.7, 7.0, None, 0.0)
    # warm windows in groups: control room (ground floor, north) and kitchen (first floor, north)
    glow_windows()
    # lamp over the entrance
    mb = MB('EntryLamp', [MAT['steel_dark'], MAT['lamp']])
    mb.box((0, 0, 0), (0.35, 0.2, 0.2), 0); mb.box((0, 0.11, -0.05), (0.28, 0.04, 0.12), 1)
    put(mb.done(), 6.7, 6.25, g0 + 2.65, 0.0)
    lt = bpy.data.lights.new('EntryLight', 'POINT'); lt.energy = 120.0; lt.color = (1.0, 0.75, 0.45); lt.shadow_soft_size = 0.2
    lo = bpy.data.objects.new('EntryLight', lt); lo.location = P(6.7, 6.8, g0 + 2.4); COL.objects.link(lo)


def sign(u, v, h):
    w, hh = 9.4, 0.78
    mb = MB('StationSign', [MAT['sign_blue'], MAT['steel_dark']])
    mb.box((0, 0, 0), (w, 0.06, hh), 0)
    mb.box((0, -0.01, hh / 2 + 0.02), (w + 0.08, 0.08, 0.04), 1); mb.box((0, -0.01, -hh / 2 - 0.02), (w + 0.08, 0.08, 0.04), 1)
    ob = mb.done(); put(ob, u, v, h, 0.0)
    cu = bpy.data.curves.new('SignText', 'FONT'); cu.body = 'RADIOOBSERVATORIUM HOHENMOOS'
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.size = 0.5; cu.extrude = 0.01
    t = bpy.data.objects.new('SignText', cu)
    bpy.context.scene.collection.objects.link(t)
    t.location = (0, 0, 0)
    t.data.materials.append(MAT['letters'])
    # turn the text to face +v (north) and fit the width
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(t.evaluated_get(dg))
    bpy.context.scene.collection.objects.unlink(t)
    xs = [vv.co.x for vv in me.vertices]; sx = (w - 0.5) / (max(xs) - min(xs))
    me.transform(Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Diagonal((sx, sx * 0.95, 1, 1)))
    me.transform(Matrix.Rotation(math.radians(180), 4, 'Z'))
    to = bpy.data.objects.new('SignText', me)
    put(to, u, v + 0.04, h, 0.0)


def glow_windows():
    """emissive panes under the open shutters of two rooms: the control room (Leitstand) and the kitchen (Kueche)"""
    m = MAPJ
    md = {d['id']: d for d in m['meshes']['list']}
    rk = {r['key']: r for r in m['roots']}
    mb = MB('WindowGlow', [MAT['glow']])
    n = 0
    for i in m['instances']:
        nm = i['name']
        if rk[i['root']]['name'] != 'BaseMain' or not (nm.startswith('IX_Shutter_Leitstand') or nm.startswith('IX_Shutter_Kueche')):
            continue
        d = md[i['mesh']]
        Pm = np.frombuffer(BLOB, np.float32, d['v'] * 3, d['offset']).reshape(-1, 3).astype(np.float64)
        M = np.array(i['matrix']).reshape(4, 4); W = Pm @ M[:3, :3].T + M[:3, 3]
        u, v = Y.blender_to_uv(W[:, 0], W[:, 1])
        if u.max() - u.min() < 0.8:                     # the west facade ones: skip
            continue
        top = W[:, 2].min()
        ga = float(G.at(0, 0))
        u0, u1, vv = u.min() + 0.08, u.max() - 0.08, v.min() + 0.02
        h1 = top - 0.12; h0 = h1 - (1.45 if top - ga < 4.0 else 1.3)
        mb.box(((u0 + u1) / 2, vv, (h0 + h1) / 2), (u1 - u0, 0.02, h1 - h0), 0)
        n += 1
    ob = mb.done()
    ob.location = P(0, 0, 0.0); ob.rotation_euler = (0, 0, Y.ROTZ); COL.objects.link(ob)
    print('[concept] lit windows', n, flush=True)


# ------------------------------------------------------------------ snow on the ground: banks, piles, drifts
ASPH = None
CHUNKS = []
SNOWH = []


def snow_at(u, v):
    if not SNOWH:
        return 0.0
    uu, vv, h = SNOWH
    i = int(np.clip((u - uu[0]) / (uu[1] - uu[0]), 0, len(uu) - 1)); j = int(np.clip((v - vv[0]) / (vv[1] - vv[0]), 0, len(vv) - 1))
    return float(h[j, i])


def chunks():
    """lumps of packed, grey snow the plough leaves at the foot of its banks"""
    m = tex_mat('C_SnowChunk', GT + 'T_GR_Gravel_A.png', (1.05, 1.05, 1.05), scale=1.0, rough=0.8, snow=False)
    mb = MB('PloughChunks', [m])
    for (u, v, hh) in CHUNKS:
        r = 0.12 + 0.3 * RNG.random() ** 2
        x, y = Y.uv_to_blender_xy(u, v)
        z = float(G.at(u, v)) + 0.1 * r + 0.2 * hh * RNG.random()
        res = bmesh.ops.create_icosphere(mb.bm, subdivisions=1, radius=r)
        M = (Matrix.Translation(Vector((float(x), float(y), z))) @ Matrix.Rotation(RNG.random() * 6.28, 4, 'Z')
             @ Matrix.Rotation(RNG.random() * 0.8, 4, 'X') @ Matrix.Diagonal((1.0 + 0.6 * RNG.random(), 0.8 + 0.5 * RNG.random(), 0.6 + 0.3 * RNG.random(), 1)))
        bmesh.ops.transform(mb.bm, matrix=M, verts=res['verts'])
    ob = mb.done(smooth=False); COL.objects.link(ob)
    print('[concept] plough chunks', len(CHUNKS), flush=True)


def snow_field():
    """the yard snow layer on a 0.25 m grid: plough banks along the asphalt, end piles, drifts on the lee (north-east)
    sides of obstacles and the fence, nothing on the asphalt, the lane and the paths"""
    yd = json.load(open('/mnt/user-data/uploads/snow/Snow/Assets/Snow/Levels/Forest/ForestYardDress.json', encoding='utf-8'))
    st = 0.25
    u0, v0, u1, v1 = -71.5, -50.5, 71.5, 47.5
    nu, nv = int((u1 - u0) / st) + 1, int((v1 - v0) / st) + 1
    uu = u0 + np.arange(nu) * st; vv = v0 + np.arange(nv) * st
    U, V = np.meshgrid(uu, vv)
    fence = (U > -70.5) & (U < 70.5) & (V > -49.3) & (V < 46.5)
    A = np.zeros_like(U, dtype=bool)
    for a in yd['asphalt']:
        r = a['r']; A |= (U >= r[0]) & (U <= r[2]) & (V >= r[1]) & (V <= r[3])
    A |= (U + 46.0) ** 2 + (V - 14.2) ** 2 <= 10.6 ** 2                             # helipad kept clear
    # the lane to the garage row (driven, not ploughed): packed, no banks
    lane = [(21.0, -15.0), (12.0, -24.0), (5.0, -32.5), (-3.0, -35.5), (-14.0, -35.5)]
    Ldist = np.minimum(poly_dist(U, V, lane), poly_dist(U, V, LANE2))
    LANE = Ldist < 2.2
    plowed = A.copy()
    d_out = ndimage.distance_transform_edt(~A) * st
    # obstacles: main building raster + footprints
    Hm, (hu0, hv0, hst) = H_main()
    O = np.zeros_like(U)
    gi = ((U - hu0) / hst).astype(int); gj = ((V - hv0) / hst).astype(int)
    ok = (gi >= 0) & (gi < Hm.shape[1]) & (gj >= 0) & (gj < Hm.shape[0])
    hm = np.full_like(U, -np.inf); hm[ok] = Hm[gj[ok], gi[ok]]
    O = np.where(np.isfinite(hm), np.maximum(hm - 16.3, 0), 0)
    BLD = O > 0.5
    keep = {k['n']: k['r'] for k in yd['keepClear']}
    for nm, hh in (('GenContainer', 3.7), ('Trafo', 2.0), ('FuelTanks', 3.0), ('Garage', 2.2), ('LogPile', 1.4)):
        r = keep[nm]; msk = (U >= r[0]) & (U <= r[2]) & (V >= r[1]) & (V <= r[3]); O[msk] = np.maximum(O[msk], hh); BLD |= msk
    for (a0, b0, a1, b1, hh) in OBST:
        msk = (U >= a0) & (U <= a1) & (V >= b0) & (V <= b1); O[msk] = np.maximum(O[msk], hh); BLD |= msk
    # the fence: a 0.6 m wall on the yard edge (the gate and wicket open)
    FEN = ~fence & ((U > -71.3) & (U < 71.3) & (V > -50.1) & (V < 47.3))
    gate = (U > -40.6) & (U < -26.2) & (V > 44.0)
    FEN &= ~gate
    O[FEN] = 3.4
    # plough banks: a windrow 1.9 m out from the asphalt edge, broken up along its length
    rng = np.random.default_rng(2810)
    nz = ndimage.gaussian_filter(rng.standard_normal(U.shape), 14) * 9.0
    nz2 = ndimage.gaussian_filter(rng.standard_normal(U.shape), 4) * 3.0
    Hb = np.clip(0.95 + 0.45 * nz + 0.12 * nz2, 0.45, 1.6)
    rise = np.clip((d_out - 0.9) / 0.9, 0, 1); rise = rise * rise * (3 - 2 * rise)
    fall = np.exp(-np.maximum(d_out - 1.9, 0) ** 2 / 1.6)
    lump = ndimage.gaussian_filter(rng.standard_normal(U.shape), 3) * 2.2 + ndimage.gaussian_filter(rng.standard_normal(U.shape), 1.2) * 0.7
    bank = Hb * rise * fall * (1 + 0.16 * lump)
    bank[d_out < 0.9] = 0
    bank[gate | (Ldist < 3.5)] *= np.clip((Ldist[gate | (Ldist < 3.5)] - 2.0) / 1.5, 0, 1)
    gate_lane = (U > -36.0) & (U < -24.0) & (V > 40.0)
    bank[gate_lane] = 0
    # end piles where the plough turns
    piles = [(31.8, 18.0, 2.3, 3.2), (-5.0, 32.4, 2.0, 3.0), (-36.8, 39.0, 1.9, 2.6), (37.2, -7.6, 2.1, 2.8),
             (-28.5, 32.6, 1.5, 3.0), (25.8, 23.6, 1.6, 2.4), (-36.6, 20.5, 1.5, 2.4), (-23.0, 10.0, 1.3, 2.4), (7.9, 36.1, 0.9, 2.4)]
    pile = np.zeros_like(U)
    for (pu, pv, ph, pr) in piles:
        ang = np.arctan2(V - pv, U - pu)
        pr_ = pr * (1 + 0.16 * np.sin(3 * ang + pu) + 0.1 * np.sin(5 * ang + pv) + 0.06 * np.sin(8 * ang + pu * pv))
        rr = np.sqrt((U - pu) ** 2 + (V - pv) ** 2) / pr_
        pile = np.maximum(pile, ph * np.clip(1 - rr ** 2 * (1 + 0.25 * lump), 0, 1) ** 1.1 * (1 + 0.12 * nz2 + 0.1 * lump))
    pile[A] = 0
    # drifts: wind from the south-west, lee sides north-east; the drift reaches ~2.6 heights downwind
    k_max = int(10.0 / (st * math.sqrt(2)))
    Dd = np.zeros_like(U)
    for k in range(1, k_max + 1):
        Ok = np.zeros_like(O)
        Ok[k:, k:] = O[:-k, :-k]
        s = k * st * math.sqrt(2)
        f = np.clip(1 - s / (1.8 * np.maximum(Ok, 0.01)), 0, 1) ** 1.4
        Dd = np.maximum(Dd, Ok * f)
    # windward cushion (south-west faces)
    Wd = np.zeros_like(U)
    for k in range(1, int(2.5 / (st * math.sqrt(2))) + 1):
        Ok = np.zeros_like(O); Ok[:-k, :-k] = O[k:, k:]
        s = k * st * math.sqrt(2)
        Wd = np.maximum(Wd, Ok * np.clip(1 - s / (0.7 * np.maximum(Ok, 0.01)), 0, 1))
    drift = 0.28 * Dd + 0.14 * Wd
    drift = ndimage.gaussian_filter(drift, 2.0) * (1 + 0.12 * nz2) + 0.035 * np.sin((U + V) * 2.2 + 3 * nz2) * (Dd > 0.3)
    # nothing on what is ploughed, driven or walked
    pl = np.clip((d_out - 0.9) / 2.0, 0, 1)
    drift *= pl
    h = np.maximum(np.maximum(bank, pile), drift) + 0.25 * np.minimum(np.minimum(bank, pile), drift)
    h = np.where(LANE, h * np.clip((Ldist - 1.2) / 1.0, 0, 1), h)
    for path in PATHS:
        dp = poly_dist(U, V, path[1])
        h *= np.clip((dp - path[0] * 0.5) / 0.6, 0, 1)
    sh = np.ones_like(U)                                                            # shovelled in front of doors
    for (a0, b0, a1, b1) in DOORS:
        du_ = np.maximum(np.maximum(a0 - U, U - a1), 0); dv_ = np.maximum(np.maximum(b0 - V, V - b1), 0)
        sh = np.minimum(sh, np.clip(np.hypot(du_, dv_) / 1.2, 0, 1))
    h *= 0.12 + 0.88 * sh
    h[BLD] = 0
    h[~fence] = 0
    h[A] = 0
    h = ndimage.gaussian_filter(h, 0.8)
    h[~fence | A] = 0
    # dirt: plough banks are grey, more so low down near the asphalt
    streak = np.clip(0.5 + 0.35 * lump, 0, 1)
    dirt = np.clip(1.25 - d_out / 3.2, 0, 1) * np.clip(bank / np.maximum(h, 1e-3), 0, 1) * (0.55 + 0.45 * streak)
    dirt = np.maximum(dirt, np.clip(pile / np.maximum(h, 1e-3), 0, 1) * np.clip(1.1 - d_out / 7, 0, 1) * (0.35 + 0.5 * streak))
    dirt = np.clip(dirt, 0, 0.95)
    print('[concept] dirt on banks/piles: p50 %.2f p90 %.2f' % tuple(np.percentile(dirt[(bank + pile) > 0.4], [50, 90])), flush=True)
    SNOWH[:] = [uu, vv, h]
    cand = np.argwhere((bank > 0.5) & (d_out > 0.95) & (d_out < 1.45) & fence & ~BLD)
    pick = cand[rng.choice(len(cand), size=min(140, len(cand)), replace=False)] if len(cand) else cand
    CHUNKS[:] = [(float(uu[i]), float(vv[j]), float(h[j, i])) for j, i in pick]
    return uu, vv, h, dirt, LANE, lane


def poly_dist(U, V, pts):
    d = np.full(U.shape, np.inf)
    for (a, b) in zip(pts[:-1], pts[1:]):
        ax, ay = a; bx, by = b
        dx, dy = bx - ax, by - ay
        t = np.clip(((U - ax) * dx + (V - ay) * dy) / (dx * dx + dy * dy), 0, 1)
        d = np.minimum(d, np.hypot(U - (ax + t * dx), V - (ay + t * dy)))
    return d


def snow_mesh(uu, vv, h, dirt):
    U, V = np.meshgrid(uu, vv)
    nv, nu = h.shape
    on = h > 0.025
    cell = on[:-1, :-1] | on[1:, :-1] | on[:-1, 1:] | on[1:, 1:]
    idx = np.full(h.shape, -1, np.int64)
    need = np.zeros_like(on)
    need[:-1, :-1] |= cell; need[1:, :-1] |= cell; need[:-1, 1:] |= cell; need[1:, 1:] |= cell
    idx[need] = np.arange(need.sum())
    x, z = Y.uv_to_unity(U[need], V[need])
    gh = G.at_unity(x, z)
    co = np.stack([-x, -z, gh + np.maximum(h[need], 0) - 0.015], 1).astype(np.float32)
    j, i = np.nonzero(cell)
    a = idx[j, i]; b = idx[j, i + 1]; c = idx[j + 1, i + 1]; d = idx[j + 1, i]
    quads = np.stack([a, b, c, d], 1)
    me = bpy.data.meshes.new('SnowLayer')
    me.vertices.add(len(co)); me.vertices.foreach_set('co', co.ravel())
    me.loops.add(quads.size); me.loops.foreach_set('vertex_index', quads.ravel().astype(np.int32))
    me.polygons.add(len(quads)); me.polygons.foreach_set('loop_start', np.arange(0, quads.size, 4, dtype=np.int32))
    me.update(calc_edges=True)
    # winding: yard (u, v, up) is right-handed in Blender, so (+u, +v) order faces up
    at = me.attributes.new('dirt', 'FLOAT', 'POINT'); at.data.foreach_set('value', dirt[need].astype(np.float32))
    me.shade_smooth()
    me.materials.append(MAT['snow'])
    ob = bpy.data.objects.new('SnowLayer', me); COL.objects.link(ob)
    print('[concept] snow layer: %d verts, max %.2f m' % (len(co), float(h.max())), flush=True)
    return ob


def ribbon(name, pts, width, mat, lift=0.03, step=0.5, field=None):
    """a ground strip along a polyline (u, v), following the ground (and the snow layer if given)"""
    dense = []
    for (a, b) in zip(pts[:-1], pts[1:]):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        for k in range(n):
            t = k / n; dense.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    dense.append(pts[-1])
    dense = np.array(dense)
    tang = np.gradient(dense, axis=0); tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-9
    nrm = np.stack([-tang[:, 1], tang[:, 0]], 1)
    L_ = dense - nrm * width / 2; R_ = dense + nrm * width / 2
    verts, uvs = [], []
    for side, arr in ((0.0, L_), (1.0, R_)):
        x, z = Y.uv_to_unity(arr[:, 0], arr[:, 1])
        gh = G.at_unity(x, z)
        if field is not None:
            gh = gh + field(arr[:, 0], arr[:, 1])
        verts.append(np.stack([-x, -z, gh + lift], 1))
    n = len(dense)
    co = np.concatenate(verts).astype(np.float32)
    faces = [(k, k + 1, n + k + 1, n + k) for k in range(n - 1)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(co.tolist(), [], faces)
    uvl = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        for li in p.loop_indices:
            vi = me.loops[li].vertex_index
            uvl.data[li].uv = (0.0 if vi < n else 1.0, (vi % n) * step / 4.0)
    # faces must point up: flip if needed
    me.update()
    if me.polygons[0].normal.z < 0:
        me.flip_normals()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); COL.objects.link(ob)
    return ob


LANE2 = [(-27.5, 37.6), (-18.0, 38.0), (-6.0, 38.4), (4.0, 38.6), (13.0, 39.4)]     # gate road to the storage, driven

DOORS = [   # shovelled rects in front of doors (u0, v0, u1, v1)
    (-10.4, 6.0, 18.0, 9.8),                      # main building front strip to the forecourt
    (-12.0, -2.0, -8.4, 2.4),                     # west door
    (16.5, -8.5, 19.5, -4.0),                     # east wing back door
    (-21.0, -16.6, -16.5, -13.0),                 # boiler house door
    (-2.0, -38.6, 10.0, -33.8), (-16.0, -38.6, -4.0, -33.8),   # garage row fronts
    (-57.6, -8.0, -53.0, -1.0), (-57.6, -11.5, -55.0, -8.5),   # workshop doors
    (31.0, -20.4, 36.0, -18.5),                   # existing garage
]


PATHS = [   # (width, points): trodden paths between doors (u, v)
    (1.1, [(6.7, 8.6), (6.0, 12.2)]),                                                  # entrance to the forecourt
    (1.1, [(-9.6, 0.5), (-12.5, -6.0), (-14.0, -11.5), (-19.5, -15.3)]),                # west door to the boiler house
    (1.0, [(-19.5, -15.3), (-23.4, -16.8), (-24.4, -23.0), (-26.8, -28.4)]),            # boiler house to the mast
    (1.0, [(-14.0, -11.5), (-30.0, -16.5), (-45.0, -21.0), (-56.0, -25.5)]),            # to the log pile and the lean-to
    (1.0, [(-56.0, -25.5), (-58.5, -15.5)]),
    (1.0, [(17.2, -6.0), (20.5, -9.5)]),                                                # east wing back door to the apron
    (1.0, [(28.0, 22.6), (31.0, 25.0), (34.0, 25.8)]),                                  # to the generator
    (1.0, [(-6.0, 22.0), (-1.0, 33.0), (4.0, 39.0), (12.0, 40.8), (16.0, 41.2)]),       # parking to the storage
    (1.0, [(24.0, -27.0), (24.5, -33.0), (24.0, -38.5), (23.0, -44.0), (22.3, -49.0)]),   # garage to the wicket
]


def ground_marks(field_h, uu, vv, lane):
    from scipy.interpolate import RegularGridInterpolator
    fi = RegularGridInterpolator((vv, uu), field_h, bounds_error=False, fill_value=0.0)
    f = lambda u, v: fi(np.stack([v, u], 1)) * 0.0
    for k, (w, pts) in enumerate(PATHS):
        ribbon('Path%d' % k, pts, w + 0.4, MAT['track'], lift=0.025, field=None)
    for k, ln in enumerate((lane, LANE2)):
        ribbon('Lane%d' % k, ln, 4.0, MAT['packed'], lift=0.02)
        for off in (-0.8, 0.8):
            pts = offset_poly(ln, off)
            ribbon('Rut%d%+.1f' % (k, off), pts, 0.55, MAT['ruts'], lift=0.03)
    # tyre tracks: the gate road and the parking are ploughed asphalt; tracks in the snow from the apron to the garage doors
    for gu in (4.0, -10.0):
        for off in (-0.8, 0.8):
            ribbon('GarRut%d%+.1f' % (gu, off), [(gu + 1.3 + off, -35.5), (gu + 1.3 + off, -37.8)], 0.55, MAT['ruts'], lift=0.03)


def offset_poly(pts, off, wobble=0.12):
    pts = np.array(pts, float)
    dense = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(1, int(np.linalg.norm(b - a) / 1.0))
        dense += [a + (b - a) * (k + 1) / n for k in range(n)]
    pts = np.array(dense)
    t = np.gradient(pts, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True)
    n = np.stack([-t[:, 1], t[:, 0]], 1)
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    w = off + wobble * np.sin(s / 3.1 + off * 7) + 0.5 * wobble * np.sin(s / 1.3)
    return [tuple(p) for p in pts + n * w[:, None]]


def clear_saplings():
    """the yard saplings and grass clumps go where buildings, lanes and storage now stand"""
    gone = 0
    for coll in ('Trees', 'Base'):
        c = bpy.data.collections.get(coll)
        if c is None:
            continue
        for o in list(c.objects):
            if coll == 'Base' and not o.name.startswith('Grass_Clump'):
                continue
            u, v = Y.blender_to_uv(o.location.x, o.location.y) if coll == 'Trees' else Y.blender_to_uv(*o.matrix_world.translation.xy)
            for (a0, b0, a1, b1) in CLEAR:
                if a0 <= u <= a1 and b0 <= v <= b1:
                    bpy.data.objects.remove(o); gone += 1
                    break
    print('[concept] removed %d saplings / clumps' % gone, flush=True)


def existing_snow():
    """snow slabs on the existing roofs of the yard: main building, garage (and its copies), generator container, fuel tanks"""
    Hm, (hu0, hv0, hst) = H_main()
    for ob in list(bpy.data.objects):
        if ob.type != 'MESH' or ob.name.endswith('_snow'):
            continue
        nm = ob.data.name.split('.')[0]
        if nm in ('00207_BaseMain', '00504_Garage', '00482_GenContainer', '00499_FuelTanks', '00493_Trafo', '00647_Shed'):
            top_snow(ob, thick=0.3 if 'BaseMain' in nm else 0.24, min_up=0.9, min_h=1.5, bevel=0.1, name='Snow_' + ob.name,
                     cover=(Hm, hu0, hv0, hst) if 'BaseMain' in nm else None)
    g0 = float(G.at(0, 0))

    def edge_top(ua, ub, va, vb):
        i0, i1 = int((ua - hu0) / hst), int((ub - hu0) / hst); j0, j1 = int((va - hv0) / hst), int((vb - hv0) / hst)
        blk = Hm[j0:j1 + 1, i0:i1 + 1]
        return float(np.nanmax(np.where(np.isfinite(blk), blk, np.nan)))
    t_main = edge_top(-7.5, 7.0, 5.5, 5.9)
    t_wing = edge_top(7.6, 17.0, 4.4, 4.9)
    t_can = edge_top(5.3, 8.2, 7.4, 8.2)
    print('[concept] eaves: main %.2f wing %.2f canopy %.2f' % (t_main, t_wing, t_can), flush=True)
    cornice('Main_cornice_N', [(-7.6, 6.12, t_main + 0.24), (7.2, 6.12, t_main + 0.24)], (0, 1), r=0.24, sag=0.12, ice_len=(0.1, 0.6), every=(0.35, 1.0))
    cornice('Wing_cornice_N', [(7.4, 5.0, t_wing + 0.2), (17.2, 5.0, t_wing + 0.2)], (0, 1), r=0.22, sag=0.1, ice_len=(0.1, 1.0), every=(0.25, 0.7))
    cornice('Canopy_cornice', [(5.0, 8.35, t_can + 0.18), (8.5, 8.35, t_can + 0.18)], (0, 1), r=0.16, sag=0.06, ice_len=(0.15, 0.9), every=(0.18, 0.45))
    gg0 = float(G.at(31.75, -25.2))
    cornice('Garage_cornice_E', [(37.7, -29.6, gg0 + 4.9), (37.7, -20.8, gg0 + 4.9)], (1, 0), r=0.24, sag=0.14, ice_len=(0.1, 0.9), every=(0.25, 0.7))
    # garages: flat roof 4.64 m over the ground, north eave (doors) at v -20.5 (the copies 17.3 m further south)
    for gu, gv, gg in ((31.75, -20.45, float(G.at(31.75, -25.2))), (4.0, -37.75, float(G.at(4.0, -42.5))), (-10.0, -37.75, float(G.at(-10.0, -42.5)))):
        cornice('Garage_cornice%d' % gu, [(gu - 6.1, gv, gg + 4.64 + 0.26), (gu + 6.1, gv, gg + 4.64 + 0.26)], (0, 1), r=0.2, sag=0.1,
                ice_len=(0.1, 0.75), every=(0.3, 0.9))


def curbs(lane):
    """concrete kerb (Hochbord 15 x 30 cm, 18 cm over the asphalt) along the outline of the asphalt rects of
    ForestYardDress; open at the gate, the building front at the entrance, the garage door, the lane exits, the
    helipad link and where the roads run on into the service yard gravel"""
    yd = json.load(open('/mnt/user-data/uploads/snow/Snow/Assets/Snow/Levels/Forest/ForestYardDress.json', encoding='utf-8'))
    rects = [a['r'] for a in yd['asphalt']]
    keep = {k['n']: k['r'] for k in yd['keepClear']}
    grav = {g['n']: g['r'] for g in yd['gravel']}
    us = sorted({r[0] for r in rects} | {r[2] for r in rects}); vs = sorted({r[1] for r in rects} | {r[3] for r in rects})
    cov = np.zeros((len(vs) - 1, len(us) - 1), bool)
    for j in range(len(vs) - 1):
        for i in range(len(us) - 1):
            cu, cv = (us[i] + us[i + 1]) / 2, (vs[j] + vs[j + 1]) / 2
            cov[j, i] = any(r[0] <= cu <= r[2] and r[1] <= cv <= r[3] for r in rects)
    edges = []                                       # (a, b, outward normal), a and b (u, v)
    for j in range(len(vs) - 1):
        for i in range(len(us)):
            l = cov[j, i - 1] if i > 0 else False; r = cov[j, i] if i < len(us) - 1 else False
            if l != r:
                edges.append(((us[i], vs[j]), (us[i], vs[j + 1]), (1, 0) if l else (-1, 0)))
    for i in range(len(us) - 1):
        for j in range(len(vs)):
            b = cov[j - 1, i] if j > 0 else False; t = cov[j, i] if j < len(vs) - 1 else False
            if b != t:
                edges.append(((us[i], vs[j]), (us[i + 1], vs[j]), (0, 1) if b else (0, -1)))

    def inside(r, u, v):
        return r[0] <= u <= r[2] and r[1] <= v <= r[3]

    def lane_d(u, v, pts):
        return float(poly_dist(np.array([[u]]), np.array([[v]]), pts)[0, 0])
    mb = MB('Curbs', [tex_mat('C_Curb', TEX + 'T_Concrete_A_px.png', (0.82, 0.82, 0.8), scale=1.0, snow=False)])
    n = 0; total = 0.0
    for (a, b, nrm) in edges:
        L = math.hypot(b[0] - a[0], b[1] - a[1]); k = max(1, int(math.ceil(L / 1.0)))
        for s in range(k):
            t0, t1 = s / k, (s + 1) / k
            u0, v0 = a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0
            u1, v1 = a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1
            cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
            ou, ov = cu + nrm[0] * 0.6, cv + nrm[1] * 0.6           # just outside the asphalt
            if cv > 46.0 and nrm == (0, 1):                          # the gate
                continue
            if inside(keep['BaseMain'], ou, ov - 0.3) and not (5.0 <= cu <= 8.6):
                pass
            if nrm == (0, -1) and 9.0 < cv < 10.0 and 4.6 <= cu <= 9.0:  # entrance steps: ramp, no kerb
                continue
            if inside(keep['Garage'], ou, ov - 1.0) or inside((26.0, -20.6, 37.6, -19.0), ou, ov):   # garage door ramp
                continue
            if inside(grav['service yard'], ou, ov):                 # the roads run on into the gravel service yard
                continue
            if math.hypot(ou + 46.0, ov - 14.2) < 11.2:                 # helipad link meets the pad
                continue
            if min(lane_d(cu, cv, lane), lane_d(cu, cv, LANE2)) < 2.4:   # where the lanes leave the asphalt
                continue
            pu, pv = cu + nrm[0] * 0.075, cv + nrm[1] * 0.075
            g0 = float(G.at(u0 + nrm[0] * 0.075, v0 + nrm[1] * 0.075)); g1 = float(G.at(u1 + nrm[0] * 0.075, v1 + nrm[1] * 0.075))
            seg = math.hypot(u1 - u0, v1 - v0)
            x, y = Y.uv_to_blender_xy(pu, pv)
            along = (u1 - u0, v1 - v0)
            th = math.atan2(along[1], along[0])
            tilt = math.atan2(g1 - g0, seg)
            M = (Matrix.Translation(Vector((float(x), float(y), (g0 + g1) / 2 + 0.03))) @ Matrix.Rotation(Y.ROTZ + th, 4, 'Z')
                 @ Matrix.Rotation(-tilt, 4, 'Y'))
            r = bmesh.ops.create_cube(mb.bm, size=1.0)
            bmesh.ops.transform(mb.bm, matrix=M @ Matrix.Translation(Vector((0, 0, 0.03))) @ Matrix.Diagonal((seg + 0.01, 0.15, 0.30, 1.0)),
                                verts=r['verts'])
            n += 1; total += seg
    ob = mb.done(); COL.objects.link(ob)
    bv = ob.modifiers.new('b', 'BEVEL'); bv.width = 0.02; bv.segments = 1
    print('[concept] kerbs: %d pieces, %.0f m' % (n, total), flush=True)


# ------------------------------------------------------------------ main
MAT = {}
MAPJ = None
BLOB = None


def build_concept():
    global G, COL, MAT, MAPJ, BLOB
    MAPJ = json.load(open(MAP + 'map.json', encoding='utf-8'))
    BLOB = np.fromfile(MAP + MAPJ['meshes']['file'], dtype=np.uint8)
    G = Y.Ground()
    COL = bpy.data.collections.new('Concept'); bpy.context.scene.collection.children.link(COL)
    MAT = mats()
    roof = radome()
    boiler_house()
    garage_row()
    workshop()
    north_storage()
    east_zone()
    rubbish()
    parking()
    accents()
    main_building_details(roof)
    existing_snow()
    uu, vv, h, dirt, LANE, lane = snow_field()
    snow_mesh(uu, vv, h, dirt)
    chunks()
    ground_marks(h, uu, vv, lane)
    curbs(lane)
    clear_saplings()


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
    for k, (e, l, fov) in S.VIEWS.items():                    # the eye stands on the snow, not in it
        u, v = Y.unity_to_uv(e[0], e[2])
        dh = snow_at(float(u), float(v))
        if dh > 0.01 and not k.endswith('_air'):
            cams[k].location.z += dh
            print('[concept] camera %s raised %.2f m onto the snow' % (k, dh), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    S.render(cams, views, os.environ.get('OUTDIR', os.path.join(D, 'rend', 'after')))


if __name__ == '__main__':
    main()
