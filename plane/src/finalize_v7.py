"""v7 finalize: Unity textures + final materials.
usage: python3 finalize_v7.py <tag> [airframe_tag=final4]
 - opens out/plane_v7_src_<tag>.blend (output of shade_v7.py)
 - writes Unity textures to export/unity_v7/Assets/UtilityPlane/Textures:
     T_<Atlas>_BaseColor (sRGB), T_<Atlas>_Normal (OpenGL, as baked),
     T_<Atlas>_MaskMap (linear: R metallic, G ambient occlusion, B 1 = detail mask, A smoothness) - v7: one packed
     map instead of _MetallicSmoothness + _AO; URP Lit reads it as Metallic (R, A) and Occlusion (G), HDRP as Mask Map
     for Airframe (v4 bake reused), Cockpit, Details (v7 bake), Interior, Floor, Seats (v6 bake)
     T_PropBlur / T_PropDisc (RGBA, fast-rotation discs)
     T_Gauges_BC / T_Gauges_Emission, T_Webbing_BaseColor / T_Webbing_Normal (tiling),
     T_Detail_Grain_Albedo / _Normal and T_Detail_Leather_Albedo / _Normal (URP detail maps)
 - Data/atlas_texel.json: metres per UV unit per atlas (detail-map tiling)
 - replaces the procedural src_* materials: M_<Atlas>, M_Gauges, M_Annunciator, M_Webbing, M_Glass, M_GaugeGlass,
   M_Screen, M_Light_*, M_PropBlur, M_PropDisc; merges duplicate slots; saves out/plane_v7_final_<tag>.blend"""
import bpy, bmesh, os, sys, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = sys.argv[1] if len(sys.argv) > 1 else 'v7'
A_TAG = sys.argv[2] if len(sys.argv) > 2 else 'final4'
TEX = os.path.join(HERE, 'tex', TAG)
OUT = os.path.join(HERE, 'export', 'unity_v7', 'Assets', 'UtilityPlane')
UT, DATA = os.path.join(OUT, 'Textures'), os.path.join(OUT, 'Data')
for d in (UT, DATA):
    os.makedirs(d, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v7_src_{TAG}.blend'))
O, MAT = bpy.data.objects, bpy.data.materials

A_MATS = ['src_Livery', 'src_Seal', 'src_Struts']
D_MATS = ['src_GearPaint', 'src_Rubber', 'src_Hub', 'src_PropBlade', 'src_Spinner', 'src_MetalDark', 'src_Antenna',
          'src_CaseGreen', 'src_CaseYellow', 'src_CaseDark', 'src_CaseTeal',
          'src_Brake', 'src_Caliper', 'src_Alu', 'src_LadderTread', 'src_KeyMetal', 'src_KeyFob']
UNBAKED = ['src_Glass', 'src_CP_GaugeGlass', 'src_CP_Gauges', 'src_CP_Net', 'src_CP_Annun', 'src_IN_Webbing',
           'src_CP_Screen', 'src_PropBlur', 'src_PropDisc']
I_MATS = ['src_IN_Liner', 'src_IN_Headliner', 'src_IN_Insul', 'src_IN_Composite', 'src_IN_Vinyl', 'src_IN_Hidden',
          'src_CabinWall', 'src_DoorPanel']
F_MATS = ['src_IN_Tread', 'src_IN_FloorPaint', 'src_IN_Track', 'src_IN_Kick', 'src_IN_Steel', 'src_IN_Trim',
          'src_IN_Seal']
S_MATS = [m.name for m in MAT if m.name.startswith('src_ST_')]
C_MATS = [m.name for m in MAT if m.name.startswith('src_CP_') and m.name not in UNBAKED]
ATLAS = {'Airframe': A_MATS, 'Cockpit': C_MATS, 'Interior': I_MATS, 'Floor': F_MATS, 'Seats': S_MATS,
         'Details': D_MATS}
SRC_TEX = {a: os.path.join(HERE, 'tex', A_TAG if a == 'Airframe' else ('v6' if a in ('Interior', 'Floor', 'Seats')
                                                                       else TAG)) for a in ATLAS}


# ------------------------------------------------------------------ Unity textures from the bakes
def unity_textures(name):
    src = SRC_TEX[name]
    bc = Image.open(os.path.join(src, f'T_{name}_BaseColor.png')).convert('RGB')
    bc.save(os.path.join(UT, f'T_{name}_BaseColor.png'), optimize=True)
    n = np.asarray(Image.open(os.path.join(src, f'T_{name}_Normal.png'))).astype(np.float32)
    if n.max() > 255:
        n = n / 257.0
    Image.fromarray(n[..., :3].round().clip(0, 255).astype(np.uint8), 'RGB').save(
        os.path.join(UT, f'T_{name}_Normal.png'), optimize=True)
    mr = Image.open(os.path.join(src, f'T_{name}_MR.png')).convert('RGB')
    if mr.size != bc.size:
        mr = mr.resize(bc.size, Image.BICUBIC)
    mr = np.asarray(mr)
    ao = Image.open(os.path.join(src, f'T_{name}_AO.png')).convert('L')
    if ao.size != bc.size:
        ao = ao.resize(bc.size, Image.BICUBIC)
    ao = np.asarray(ao)
    mask = np.dstack([mr[..., 0], ao, np.full_like(ao, 255), 255 - mr[..., 1]]).astype(np.uint8)
    Image.fromarray(mask, 'RGBA').save(os.path.join(UT, f'T_{name}_MaskMap.png'), optimize=True)
    print('unity textures', name, bc.size, flush=True)


for atl in ATLAS:
    unity_textures(atl)
for f in ('T_Gauges_BC.png', 'T_Gauges_Emission.png', 'T_Displays_Emission.png'):
    Image.open(os.path.join(HERE, 'tex', 'v7', f)).convert('RGB').save(os.path.join(UT, f), optimize=True)


# ------------------------------------------------------------------ v7 fast-rotation discs (UV 0..1 over 2.67 m)
def prop_textures(res=512, rr=1.335):
    yy, xx = (np.mgrid[0:res, 0:res] + 0.5) / res
    dx, dz = (0.5 - xx) * 2 * rr, (0.5 - yy) * 2 * rr          # u = 0.5 - x / 2rr, v = 0.5 + z / 2rr (image rows down)
    r = np.sqrt(dx * dx + dz * dz)
    th = np.arctan2(dx, dz)                                      # angle from 12 o'clock
    rng = np.random.default_rng(3)
    streak = np.interp(r, np.linspace(0, rr, 400), 1.0 + 0.12 * rng.standard_normal(400))
    inside = (r > 0.27) & (r < 1.322)
    tip = (r > 1.20) & (r < 1.322)
    chord = np.interp(r, [0.17, 0.34, 0.52, 0.76, 0.98, 1.16, 1.27, 1.32], [0.07, 0.175, 0.24, 0.245, 0.222, 0.185, 0.13, 0.03])
    cover = np.clip(3 * chord / (2 * np.pi * np.maximum(r, 0.05)), 0, 1)
    rgb = np.zeros((res, res, 3))
    rgb[...] = (14, 14, 15)
    rgb[tip] = (205, 150, 20)
    # disc: averaged look (coverage x visibility), tip ring brighter
    a = np.where(inside, np.clip(cover * 1.25, 0.05, 0.32) * streak, 0.0)
    a = np.where(tip, np.maximum(a, 0.30), a)
    edge = np.clip((1.322 - r) / 0.01, 0, 1) * np.clip((r - 0.27) / 0.02, 0, 1)
    disc = np.dstack([rgb, np.clip(a * edge, 0, 1) * 255]).clip(0, 255).astype(np.uint8)
    Image.fromarray(disc, 'RGBA').save(os.path.join(UT, 'T_PropDisc.png'), optimize=True)
    # blur: three smeared blades, sharp leading edge, long trailing smear (clockwise rotation in the pilot view)
    blades = np.zeros_like(r)
    for k in range(3):
        rel = np.mod(th - 2 * np.pi * k / 3 + np.pi, 2 * np.pi) - np.pi      # 0 at blade k
        width = np.maximum(chord / np.maximum(r, 0.05), 0.02)
        lead = np.exp(-np.maximum(rel, 0) ** 2 / (2 * (0.35 * width) ** 2))
        trail = np.exp(-np.maximum(-rel, 0) / (1.6 * width + 0.25))
        blades = np.maximum(blades, np.where(rel >= 0, lead, trail))
    a = np.where(inside, blades * 0.75 * streak, 0.0) * edge
    blur = np.dstack([rgb, np.clip(a, 0, 1) * 255]).clip(0, 255).astype(np.uint8)
    Image.fromarray(blur, 'RGBA').save(os.path.join(UT, 'T_PropBlur.png'), optimize=True)


prop_textures()


# ------------------------------------------------------------------ tiling textures: webbing, detail grain
def height_to_normal(h, strength):
    gy, gx = np.gradient(h)
    nx, ny = -gx * strength, gy * strength                     # OpenGL (+Y up in texture space)
    nz = np.ones_like(h)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack([(nx / L + 1) * 127.5, (ny / L + 1) * 127.5, (nz / L + 1) * 127.5]).clip(0, 255).astype(np.uint8)


def tile_noise(res, freqs, seed):
    """sum of random periodic sinusoids -> seamless noise in [0, 1]"""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:res, 0:res] / res
    h = np.zeros((res, res))
    for f, amp in freqs:
        for _ in range(6):
            kx, ky = rng.integers(-f, f + 1), rng.integers(-f, f + 1)
            if kx == 0 and ky == 0:
                continue
            h += amp * np.sin(2 * np.pi * (kx * xx + ky * yy) + rng.uniform(0, 2 * np.pi))
    h -= h.min()
    return h / max(h.max(), 1e-9)


def webbing_textures(res_u=512, res_v=128):
    """one tile = 0.10 m of strap (u) x full strap width (v); nylon twill, edge binding, olive drab"""
    yy, xx = np.mgrid[0:res_v, 0:res_u].astype(np.float32)
    twill = 0.5 + 0.5 * np.sin(2 * np.pi * (xx / res_u * 48 + yy / res_v * 6))
    yarn = 0.5 + 0.5 * np.sin(2 * np.pi * yy / res_v * 22)
    edge = np.clip(1.0 - np.minimum(yy, res_v - 1 - yy) / (res_v * 0.08), 0, 1)
    h = 0.55 * twill + 0.25 * yarn - 0.6 * edge
    base = np.array([62, 66, 40], np.float32)
    col = base[None, None, :] * (0.82 + 0.25 * twill[..., None]) * (1.0 - 0.25 * edge[..., None])
    Image.fromarray(col.clip(0, 255).astype(np.uint8), 'RGB').save(os.path.join(UT, 'T_Webbing_BaseColor.png'))
    Image.fromarray(height_to_normal(h, 1.5), 'RGB').save(os.path.join(UT, 'T_Webbing_Normal.png'))


def detail_textures(res=512):
    peb = tile_noise(res, [(24, 1.0), (48, 0.6), (96, 0.35)], 7)
    Image.fromarray(height_to_normal(peb, 2.0), 'RGB').save(os.path.join(UT, 'T_Detail_Grain_Normal.png'))
    alb = 128 + (peb - 0.5) * 18
    Image.fromarray(alb.clip(0, 255).astype(np.uint8), 'L').convert('RGB').save(
        os.path.join(UT, 'T_Detail_Grain_Albedo.png'))
    lea = tile_noise(res, [(16, 1.0), (40, 0.7), (80, 0.45), (140, 0.25)], 11)
    cell = np.abs(np.sin(lea * 9.0))                          # leather: cell-like creases
    h = 0.6 * lea + 0.4 * cell
    Image.fromarray(height_to_normal(h, 2.5), 'RGB').save(os.path.join(UT, 'T_Detail_Leather_Normal.png'))
    alb = 128 + (h - 0.5) * 22
    Image.fromarray(alb.clip(0, 255).astype(np.uint8), 'L').convert('RGB').save(
        os.path.join(UT, 'T_Detail_Leather_Albedo.png'))


webbing_textures()
detail_textures()


# ------------------------------------------------------------------ metres per UV unit, per atlas (URP detail tiling)
HIDDEN = ('src_CabinWall', 'src_DoorPanel', 'src_IN_Hidden')
DETAIL = {'Cockpit': ('Grain', 0.06, 0.4), 'Interior': ('Grain', 0.06, 0.6), 'Floor': ('Grain', 0.06, 0.3),
          'Seats': ('Leather', 0.08, 0.8)}


def texel_stats():
    rows = []
    for atl, mats in ATLAS.items():
        a3 = a2 = 0.0
        for ob in O:
            if ob.type != 'MESH' or not ob.data.uv_layers:
                continue
            names = [m.name if m else '' for m in ob.data.materials]
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            bm.transform(ob.matrix_world)
            uvl = bm.loops.layers.uv[0]
            for f in bm.faces:
                n = names[f.material_index] if f.material_index < len(names) else ''
                if n in mats and n not in HIDDEN:
                    a3 += f.calc_area()
                    uv = [l[uvl].uv for l in f.loops]
                    a2 += abs(sum(uv[i].x * uv[(i + 1) % len(uv)].y - uv[(i + 1) % len(uv)].x * uv[i].y
                                  for i in range(len(uv)))) / 2
            bm.free()
        if a2 <= 0:
            continue
        mpu = math.sqrt(a3 / a2)
        res = Image.open(os.path.join(UT, f'T_{atl}_BaseColor.png')).size[0]
        row = dict(atlas=atl, material='M_' + atl, metresPerUV=round(mpu, 4), pxPerMetre=round(res / mpu, 1),
                   areaM2=round(a3, 2), detail='', detailTiling=0.0, detailNormalScale=0.0)
        if atl in DETAIL:
            d, tile, ns = DETAIL[atl]
            row.update(detail=d, detailTiling=round(mpu / tile, 2), detailNormalScale=ns)
        rows.append(row)
    return rows


TEXEL = texel_stats()
json.dump(TEXEL, open(os.path.join(DATA, 'atlas_texel.json'), 'w'), indent=1)
print('texel', TEXEL, flush=True)


# ------------------------------------------------------------------ materials
def load(path, noncolor):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im


def new_mat(name):
    old = MAT.get(name)
    if old:
        old.name = name + '_old'
    m = MAT.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, m.node_tree.nodes, m.node_tree.links


def tex_node(N, im, x, y, vec=None, L=None):
    t = N.new('ShaderNodeTexImage')
    t.image = im
    t.location = (x, y)
    if vec is not None:
        L.new(vec, t.inputs['Vector'])
    return t


def pbr_material(name, bc_path, ms_path, n_path, tiling=None):
    m, N, L = new_mat(name)
    out = N.new('ShaderNodeOutputMaterial')
    out.location = (500, 0)
    pr = N.new('ShaderNodeBsdfPrincipled')
    pr.location = (200, 0)
    L.new(pr.outputs[0], out.inputs[0])
    vec = None
    if tiling:
        tc = N.new('ShaderNodeTexCoord')
        mp = N.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (tiling[0], tiling[1], 1.0)
        L.new(tc.outputs['UV'], mp.inputs['Vector'])
        vec = mp.outputs['Vector']
    bc = tex_node(N, load(bc_path, False), -700, 300, vec, L)
    L.new(bc.outputs['Color'], pr.inputs['Base Color'])
    if ms_path:
        ms = tex_node(N, load(ms_path, True), -700, 0, vec, L)
        sp = N.new('ShaderNodeSeparateColor')
        L.new(ms.outputs['Color'], sp.inputs[0])
        L.new(sp.outputs[0], pr.inputs['Metallic'])
        inv = N.new('ShaderNodeMath')
        inv.operation = 'SUBTRACT'
        inv.inputs[0].default_value = 1.0
        L.new(ms.outputs['Alpha'], inv.inputs[1])
        L.new(inv.outputs[0], pr.inputs['Roughness'])
    else:
        pr.inputs['Roughness'].default_value = 0.8
    nt = tex_node(N, load(n_path, True), -700, -300, vec, L)
    nm = N.new('ShaderNodeNormalMap')
    L.new(nt.outputs['Color'], nm.inputs['Color'])
    L.new(nm.outputs[0], pr.inputs['Normal'])
    return m, pr


def glass_material(name, tint, refl):
    m, N, L = new_mat(name)
    out = N.new('ShaderNodeOutputMaterial')
    tr = N.new('ShaderNodeBsdfTransparent')
    tr.inputs['Color'].default_value = tint
    gl = N.new('ShaderNodeBsdfGlossy')
    gl.inputs['Roughness'].default_value = 0.03
    geo = N.new('ShaderNodeNewGeometry')
    dot = N.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    L.new(geo.outputs['Normal'], dot.inputs[0])
    L.new(geo.outputs['Incoming'], dot.inputs[1])
    ab = N.new('ShaderNodeMath')
    ab.operation = 'ABSOLUTE'
    L.new(dot.outputs['Value'], ab.inputs[0])
    om = N.new('ShaderNodeMath')
    om.operation = 'SUBTRACT'
    om.inputs[0].default_value = 1.0
    L.new(ab.outputs[0], om.inputs[1])
    pw = N.new('ShaderNodeMath')
    pw.operation = 'POWER'
    L.new(om.outputs[0], pw.inputs[0])
    pw.inputs[1].default_value = 5.0
    f = N.new('ShaderNodeMath')
    f.operation = 'MULTIPLY_ADD'
    L.new(pw.outputs[0], f.inputs[0])
    f.inputs[1].default_value = 1.0 - refl
    f.inputs[2].default_value = refl
    mx = N.new('ShaderNodeMixShader')
    L.new(f.outputs[0], mx.inputs[0])
    L.new(tr.outputs[0], mx.inputs[1])
    L.new(gl.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], out.inputs[0])
    return m


FINAL = {}
for atl, mats in ATLAS.items():
    fm, _ = pbr_material('M_' + atl, os.path.join(UT, f'T_{atl}_BaseColor.png'),
                         os.path.join(UT, f'T_{atl}_MaskMap.png'), os.path.join(UT, f'T_{atl}_Normal.png'))
    for mn in mats:
        FINAL[mn] = fm
FINAL['src_Glass'] = glass_material('M_Glass', (0.93, 0.96, 0.95, 1), 0.06)
FINAL['src_CP_GaugeGlass'] = glass_material('M_GaugeGlass', (1, 1, 1, 1), 0.008)   # v6: readable dials
wm, _ = pbr_material('M_Webbing', os.path.join(UT, 'T_Webbing_BaseColor.png'), None,
                     os.path.join(UT, 'T_Webbing_Normal.png'), tiling=(10.0, 1.0))
FINAL['src_IN_Webbing'] = wm
FINAL['src_CP_Net'] = wm                                    # legacy net material, if any object still uses it
for key, mname in (('src_CP_Gauges', 'M_Gauges'), ('src_CP_Annun', 'M_Annunciator')):
    m, N, L = new_mat(mname)
    out = N.new('ShaderNodeOutputMaterial')
    pr = N.new('ShaderNodeBsdfPrincipled')
    t = tex_node(N, load(os.path.join(UT, 'T_Gauges_BC.png'), False), -400, 0)
    L.new(t.outputs['Color'], pr.inputs['Base Color'])           # v6: the atlas already holds the unlit lens look
    e = tex_node(N, load(os.path.join(UT, 'T_Gauges_Emission.png' if key == 'src_CP_Gauges' else
                                      'T_Displays_Emission.png'), False), -400, -300)
    L.new(e.outputs['Color'], pr.inputs['Emission Color'])
    pr.inputs['Emission Strength'].default_value = 0.0          # night previews: raise (panel lights)
    pr.inputs['Roughness'].default_value = 0.7 if key == 'src_CP_Gauges' else 0.25   # v6: matte print
    L.new(pr.outputs[0], out.inputs[0])
    FINAL[key] = m

for key, mname, tex in (('src_PropBlur', 'M_PropBlur', 'T_PropBlur'), ('src_PropDisc', 'M_PropDisc', 'T_PropDisc')):
    m, N, L = new_mat(mname)                                    # v7 fast-rotation discs (alpha from the texture)
    out = N.new('ShaderNodeOutputMaterial')
    pr = N.new('ShaderNodeBsdfPrincipled')
    t = tex_node(N, load(os.path.join(UT, tex + '.png'), False), -400, 0)
    L.new(t.outputs['Color'], pr.inputs['Base Color'])
    L.new(t.outputs['Alpha'], pr.inputs['Alpha'])
    pr.inputs['Roughness'].default_value = 0.6
    L.new(pr.outputs[0], out.inputs[0])
    FINAL[key] = m

m, N, L = new_mat('M_Screen')                                   # v6 display quads (UV 0..1): dark LCD
out = N.new('ShaderNodeOutputMaterial')
pr = N.new('ShaderNodeBsdfPrincipled')
pr.inputs['Base Color'].default_value = (0.010, 0.013, 0.013, 1)
pr.inputs['Roughness'].default_value = 0.2
pr.inputs['Emission Color'].default_value = (0.05, 0.12, 0.10, 1)
pr.inputs['Emission Strength'].default_value = 0.0
L.new(pr.outputs[0], out.inputs[0])
FINAL['src_CP_Screen'] = m

LIGHT = {'M_Light_Red': ((1.0, 0.02, 0.01, 1), 12), 'M_Light_Green': ((0.02, 1.0, 0.15, 1), 12),
         'M_Light_White': ((1.0, 1.0, 0.95, 1), 10), 'M_Light_Beacon': ((1.0, 0.08, 0.01, 1), 8),
         'M_Light_Landing': ((1.0, 0.97, 0.9, 1), 3), 'M_Light_Cabin': ((1.0, 0.85, 0.62, 1), 0.0)}
for ln, (c, s) in LIGHT.items():
    if ln not in MAT:
        continue
    mt = MAT[ln]
    mt.use_nodes = True
    mt.node_tree.nodes.clear()
    N, L = mt.node_tree.nodes, mt.node_tree.links
    out = N.new('ShaderNodeOutputMaterial')
    pr = N.new('ShaderNodeBsdfPrincipled')
    pr.inputs['Base Color'].default_value = (c[0] * 0.3, c[1] * 0.3, c[2] * 0.3, 1)
    pr.inputs['Roughness'].default_value = 0.1
    pr.inputs['Emission Color'].default_value = c
    pr.inputs['Emission Strength'].default_value = s
    pr.inputs['Coat Weight'].default_value = 1.0
    L.new(pr.outputs[0], out.inputs[0])

# ------------------------------------------------------------------ remap slots, merge duplicates
for ob in O:
    if ob.type != 'MESH':
        continue
    me = ob.data
    mats = list(me.materials)
    new = [FINAL.get(mt.name, mt) if mt else None for mt in mats]
    uniq = []
    for p in me.polygons:                                   # keep only materials that faces use
        mt = new[p.material_index] if p.material_index < len(new) else None
        if mt not in uniq:
            uniq.append(mt)
    idx = [uniq.index(new[p.material_index]) if p.material_index < len(new) else 0 for p in me.polygons]
    me.materials.clear()
    for mt in uniq:
        me.materials.append(mt)
    for p, i in zip(me.polygons, idx):
        p.material_index = i

for mt in list(MAT):
    if mt.name.startswith('src_') and mt.use_fake_user:
        mt.use_fake_user = False
bpy.data.orphans_purge(do_recursive=True)
print('materials', sorted(m.name for m in MAT), flush=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v7_final_{TAG}.blend'))
print('saved final blend')
