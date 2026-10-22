"""Assemble final PBR materials from the baked atlases.
usage: python3 finalize_v2.py <tag>
 - opens out/plane_v2_src_<tag>.blend (output of shade_v2.py)
 - replaces the procedural src_* materials with texture materials:
     M_Airframe / M_Details / M_Cockpit   (baked atlases: BaseColor, MR, Normal, AO)
     M_Gauges (T_Gauges_BC), M_Glass, M_GaugeGlass, M_CargoNet (tiling masked webbing), M_Light_*
 - merges duplicate material slots, gives the cargo net planar UVs
 - writes UE textures to export/ue/Textures:  T_<Atlas>_BC (sRGB), T_<Atlas>_N (DirectX, G flipped), T_<Atlas>_ORM
 - saves out/plane_v2_final_<tag>.blend"""
import bpy, os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = sys.argv[1] if len(sys.argv) > 1 else 'final2'
TEX = os.path.join(HERE, 'tex', TAG)
UE_TEX = os.path.join(HERE, 'export', 'ue', 'Textures')
os.makedirs(UE_TEX, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v2_src_{TAG}.blend'))
O, MAT = bpy.data.objects, bpy.data.materials

A_MATS = ['src_Livery', 'src_Seal', 'src_Struts']
D_MATS = ['src_GearPaint', 'src_Rubber', 'src_Hub', 'src_PropBlade', 'src_Spinner', 'src_MetalDark', 'src_Antenna',
          'src_CaseGreen', 'src_CaseYellow', 'src_CaseDark', 'src_CaseTeal']
UNBAKED = ['src_Glass', 'src_CP_GaugeGlass', 'src_CP_Gauges', 'src_CP_Net', 'src_CP_Annun']
C_MATS = [m.name for m in MAT if m.name.startswith('src_CP_') and m.name not in UNBAKED] + ['src_CabinWall',
                                                                                            'src_DoorPanel']
ATLAS = {'Airframe': A_MATS, 'Details': D_MATS, 'Cockpit': C_MATS}


# ------------------------------------------------------------------ helpers
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


def tex_node(nodes, im, x, y):
    t = nodes.new('ShaderNodeTexImage')
    t.image = im
    t.location = (x, y)
    t.interpolation = 'Linear'
    return t


def atlas_material(name):
    """built from the UE textures themselves (BC / ORM / DirectX normal), so the preview checks what ships"""
    m, N, L = new_mat('M_' + name)
    out = N.new('ShaderNodeOutputMaterial')
    out.location = (500, 0)
    pr = N.new('ShaderNodeBsdfPrincipled')
    pr.location = (200, 0)
    L.new(pr.outputs[0], out.inputs[0])
    bc = tex_node(N, load(os.path.join(UE_TEX, f'T_{name}_BC.png'), False), -700, 300)
    orm = tex_node(N, load(os.path.join(UE_TEX, f'T_{name}_ORM.png'), True), -700, 0)
    nm = tex_node(N, load(os.path.join(UE_TEX, f'T_{name}_N.png'), True), -700, -300)
    sp = N.new('ShaderNodeSeparateColor')
    sp.location = (-400, 0)
    L.new(orm.outputs['Color'], sp.inputs[0])
    # DirectX -> OpenGL: invert green
    sn = N.new('ShaderNodeSeparateColor')
    sn.location = (-400, -300)
    L.new(nm.outputs['Color'], sn.inputs[0])
    inv = N.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    L.new(sn.outputs[1], inv.inputs[1])
    cn = N.new('ShaderNodeCombineColor')
    cn.location = (-200, -300)
    L.new(sn.outputs[0], cn.inputs[0])
    L.new(inv.outputs[0], cn.inputs[1])
    L.new(sn.outputs[2], cn.inputs[2])
    nmap = N.new('ShaderNodeNormalMap')
    nmap.location = (0, -300)
    nmap.uv_map = 'UVMap'
    L.new(cn.outputs[0], nmap.inputs['Color'])
    L.new(bc.outputs['Color'], pr.inputs['Base Color'])
    L.new(sp.outputs[2], pr.inputs['Metallic'])
    L.new(sp.outputs[1], pr.inputs['Roughness'])
    L.new(nmap.outputs[0], pr.inputs['Normal'])
    return m


def glass_material(name, tint, refl):
    """thin glass: transparent + glossy, Schlick fresnel on |N.I| (the Fresnel node goes to total internal
    reflection on back faces, which turned the windscreen into a mirror when seen from the cockpit)"""
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
    f.operation = 'MULTIPLY_ADD'                    # F = refl + (1 - refl) * (1 - |N.I|)^5
    L.new(pw.outputs[0], f.inputs[0])
    f.inputs[1].default_value = 1.0 - refl
    f.inputs[2].default_value = refl
    mx = N.new('ShaderNodeMixShader')
    L.new(f.outputs[0], mx.inputs[0])
    L.new(tr.outputs[0], mx.inputs[1])
    L.new(gl.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], out.inputs[0])
    return m


# ------------------------------------------------------------------ cargo net texture (tiling, one mesh cell per tile)
def make_net_texture(path, res=512):
    s = 4 * res                                     # supersample
    img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = int(s * 0.085)                              # 25 mm webbing on a ~30 cm cell -> scaled to 14 cm cell
    col = (38, 44, 34, 255)
    for c in (0, s):
        d.rectangle([c - w // 2, 0, c + w // 2, s], fill=col)
        d.rectangle([0, c - w // 2, s, c + w // 2], fill=col)
    # bar-tacks at the crossings
    t = int(w * 1.25)
    for cx in (0, s):
        for cy in (0, s):
            d.rectangle([cx - t // 2, cy - t // 2, cx + t // 2, cy + t // 2], fill=(46, 52, 42, 255))
    img = img.resize((res, res), Image.LANCZOS)
    a = np.asarray(img).astype(np.float32)
    # weave: fine diagonal stripes on the webbing
    yy, xx = np.mgrid[0:res, 0:res]
    weave = 0.85 + 0.15 * (np.sin((xx + yy) * 2 * math.pi / 3.0) > 0)
    a[..., :3] *= weave[..., None]
    Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA').save(path)
    return path


net_png = make_net_texture(os.path.join(UE_TEX, 'T_CargoNet_BCA.png'))

# ------------------------------------------------------------------ UE textures
def ue_textures(name):
    bc = Image.open(os.path.join(TEX, f'T_{name}_BaseColor.png')).convert('RGB')
    bc.save(os.path.join(UE_TEX, f'T_{name}_BC.png'), optimize=True)
    n = np.asarray(Image.open(os.path.join(TEX, f'T_{name}_Normal.png'))).astype(np.float32)
    if n.max() > 255:
        n = n / 257.0
    n = n[..., :3]
    n[..., 1] = 255.0 - n[..., 1]                   # OpenGL -> DirectX
    Image.fromarray(n.round().clip(0, 255).astype(np.uint8), 'RGB').save(os.path.join(UE_TEX, f'T_{name}_N.png'),
                                                                        optimize=True)
    mr = np.asarray(Image.open(os.path.join(TEX, f'T_{name}_MR.png')).convert('RGB'))
    ao = Image.open(os.path.join(TEX, f'T_{name}_AO.png')).convert('L')
    if ao.size != bc.size:
        ao = ao.resize(bc.size, Image.BICUBIC)
    ao = np.asarray(ao)
    orm = np.stack([ao, mr[..., 1], mr[..., 0]], -1)
    Image.fromarray(orm, 'RGB').save(os.path.join(UE_TEX, f'T_{name}_ORM.png'), optimize=True)
    print('UE textures', name, bc.size)


for atl in ATLAS:
    ue_textures(atl)
Image.open(os.path.join(HERE, 'tex', 'v2', 'T_Gauges_BC.png')).convert('RGB').save(
    os.path.join(UE_TEX, 'T_Gauges_BC.png'), optimize=True)

# ------------------------------------------------------------------ build final materials
FINAL = {}
for atl, mats in ATLAS.items():
    fm = atlas_material(atl)
    for mn in mats:
        FINAL[mn] = fm
FINAL['src_Glass'] = glass_material('M_Glass', (0.93, 0.96, 0.95, 1), 0.06)
FINAL['src_CP_GaugeGlass'] = glass_material('M_GaugeGlass', (1, 1, 1, 1), 0.03)

m, N, L = new_mat('M_Gauges')
out = N.new('ShaderNodeOutputMaterial')
pr = N.new('ShaderNodeBsdfPrincipled')
t = tex_node(N, load(os.path.join(UE_TEX, 'T_Gauges_BC.png'), False), -400, 0)
L.new(t.outputs['Color'], pr.inputs['Base Color'])
pr.inputs['Roughness'].default_value = 0.55
L.new(pr.outputs[0], out.inputs[0])
FINAL['src_CP_Gauges'] = m

m, N, L = new_mat('M_CargoNet')
out = N.new('ShaderNodeOutputMaterial')
pr = N.new('ShaderNodeBsdfPrincipled')
t = tex_node(N, load(net_png, False), -400, 0)
L.new(t.outputs['Color'], pr.inputs['Base Color'])
L.new(t.outputs['Alpha'], pr.inputs['Alpha'])
pr.inputs['Roughness'].default_value = 0.85
L.new(pr.outputs[0], out.inputs[0])
FINAL['src_CP_Net'] = m

# annunciator lamps: same atlas (UVMap); in UE the lamp index comes from LampUV.x (see ue_import_utility_plane.py)
m, N, L = new_mat('M_Annunciator')
out = N.new('ShaderNodeOutputMaterial')
pr = N.new('ShaderNodeBsdfPrincipled')
t = tex_node(N, load(os.path.join(UE_TEX, 'T_Gauges_BC.png'), False), -400, 0)
uvn = N.new('ShaderNodeUVMap')
uvn.uv_map = 'UVMap'
L.new(uvn.outputs['UV'], t.inputs['Vector'])
L.new(t.outputs['Color'], pr.inputs['Base Color'])
pr.inputs['Roughness'].default_value = 0.25
L.new(pr.outputs[0], out.inputs[0])
FINAL['src_CP_Annun'] = m

LIGHT = {'M_Light_Red': ((1.0, 0.02, 0.01, 1), 12), 'M_Light_Green': ((0.02, 1.0, 0.15, 1), 12),
         'M_Light_White': ((1.0, 1.0, 0.95, 1), 10), 'M_Light_Beacon': ((1.0, 0.08, 0.01, 1), 8),
         'M_Light_Landing': ((1.0, 0.97, 0.9, 1), 3), 'M_Light_Cabin': ((1.0, 0.85, 0.62, 1), 0.0)}
for ln, (c, s) in LIGHT.items():
    if ln not in MAT:
        continue
    mt = MAT[ln]
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

# ------------------------------------------------------------------ remap slots, merge duplicates, net UVs
for ob in O:
    if ob.type != 'MESH':
        continue
    me = ob.data
    mats = list(me.materials)
    new = []
    for mt in mats:
        new.append(FINAL.get(mt.name, mt) if mt else None)
    uniq = []
    for mt in new:
        if mt not in uniq:
            uniq.append(mt)
    remap = [uniq.index(mt) for mt in new]
    idx = [remap[p.material_index] if p.material_index < len(remap) else 0 for p in me.polygons]
    # net faces -> planar UV (x, z) with a 14 cm cell
    net_i = [i for i, mt in enumerate(mats) if mt and mt.name == 'src_CP_Net']
    if net_i and me.uv_layers:
        uv = me.uv_layers[0].data
        mw = ob.matrix_world
        for p in me.polygons:
            if p.material_index in net_i:
                for li in p.loop_indices:
                    v = mw @ me.vertices[me.loops[li].vertex_index].co
                    uv[li].uv = (v.x / 0.14, v.z / 0.14)
    me.materials.clear()
    for mt in uniq:
        me.materials.append(mt)
    for p, i in zip(me.polygons, idx):
        p.material_index = i

for mt in list(MAT):
    if mt.users == 0 or (mt.name.startswith('src_') and mt.use_fake_user):
        mt.use_fake_user = False
bpy.data.orphans_purge(do_recursive=True)
print('materials', sorted(m.name for m in MAT))


bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', f'plane_v2_final_{TAG}.blend'))
print('saved final blend')
