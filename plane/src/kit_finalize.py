"""Winter kit finalize: Unity textures + final blend.
python3 kit_finalize.py
 - tex/kit1 bakes -> export/unity_kit/Assets/UtilityPlane/Textures:
     T_Kit{Covers,Props}_BaseColor (sRGB), _Normal (OpenGL), _MaskMap (R metallic, G AO, B 1, A smoothness),
     _DetailMask (1K, mask in RGB and A: where the fabric weave detail map applies - URP/Built-in read .a)
     T_Detail_Fabric_Albedo / _Normal (512, tiling plain-weave cloth, one tile = FABRIC_TILE m)
 - Data/kit_texel.json: metres per UV unit + detail tiling per atlas
 - out/kit_final_v1.blend: one material per atlas (M_KitCovers, M_KitProps), TextUV layers removed"""
import bpy, bmesh, os, sys, math, json
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex', 'kit1')
OUT = os.path.join(HERE, 'export', 'unity_kit', 'Assets', 'UtilityPlane')
UT, DATA = os.path.join(OUT, 'Textures'), os.path.join(OUT, 'Data')
for d in (UT, DATA):
    os.makedirs(d, exist_ok=True)
ATLASES = ('Covers', 'Props')
FABRIC_TILE = 0.04          # m per detail tile (32 yarns -> 1.25 mm yarn pitch, heavy coated polyester)
FABRIC_NORMAL_SCALE = 0.7


# ------------------------------------------------------------------ atlas textures
def unity_textures(a):
    bc = Image.open(os.path.join(TEX, f'T_Kit{a}_BaseColor.png')).convert('RGB')
    bc.save(os.path.join(UT, f'T_Kit{a}_BaseColor.png'), optimize=True)
    n = np.asarray(Image.open(os.path.join(TEX, f'T_Kit{a}_Normal.png'))).astype(np.float32)
    if n.max() > 255:
        n = n / 257.0
    Image.fromarray(n[..., :3].round().clip(0, 255).astype(np.uint8), 'RGB').save(
        os.path.join(UT, f'T_Kit{a}_Normal.png'), optimize=True)
    mr = Image.open(os.path.join(TEX, f'T_Kit{a}_MR.png')).convert('RGB').resize(bc.size, Image.BICUBIC)
    ao = Image.open(os.path.join(TEX, f'T_Kit{a}_AO.png')).convert('L').resize(bc.size, Image.BICUBIC)
    mr, ao = np.asarray(mr), np.asarray(ao)
    mask = np.dstack([mr[..., 0], ao, np.full_like(ao, 255), 255 - mr[..., 1]]).astype(np.uint8)
    Image.fromarray(mask, 'RGBA').save(os.path.join(UT, f'T_Kit{a}_MaskMap.png'), optimize=True)
    dm = Image.open(os.path.join(TEX, f'T_Kit{a}_DMask.png')).convert('L').resize((1024, 1024), Image.BILINEAR)
    dm = np.asarray(dm)
    Image.fromarray(np.dstack([dm, dm, dm, dm]).astype(np.uint8), 'RGBA').save(
        os.path.join(UT, f'T_Kit{a}_DetailMask.png'), optimize=True)
    print('unity textures', a, bc.size, 'detail-mask coverage', round(float((dm > 127).mean()), 3), flush=True)


def height_to_normal(h, strength):
    gy, gx = np.gradient(h)
    nx, ny = -gx * strength, gy * strength                       # OpenGL (+Y up in texture space)
    nz = np.ones_like(h)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack([(nx / L + 1) * 127.5, (ny / L + 1) * 127.5, (nz / L + 1) * 127.5]).clip(0, 255).astype(np.uint8)


def fabric_textures(res=512, yarns=32, seed=5):
    """plain weave: warp over weft on alternating crossings; yarn cross-section cos-profile; fibre noise"""
    P = res / yarns
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float64) + 0.5
    ix, iy = np.floor(xx / P), np.floor(yy / P)
    fx, fy = xx / P - ix - 0.5, yy / P - iy - 0.5                 # -0.5..0.5 inside a cell
    warp_prof = np.cos(np.pi * fx) ** 0.6                         # across the warp yarn (yarn runs along y)
    weft_prof = np.cos(np.pi * fy) ** 0.6
    par = (ix + iy) % 2                                           # 1: warp on top in this cell
    warp_h = warp_prof * (0.55 + 0.45 * np.where(par == 1, np.cos(np.pi * fy), -np.cos(np.pi * fy) * 0.6))
    weft_h = weft_prof * (0.55 + 0.45 * np.where(par == 0, np.cos(np.pi * fx), -np.cos(np.pi * fx) * 0.6))
    h = np.maximum(warp_h, weft_h)
    rng = np.random.default_rng(seed)
    fib = np.zeros((res, res))
    for f, amp in ((yarns * 4, 0.10), (yarns * 2, 0.06)):        # periodic fibre noise (tileable)
        for _ in range(8):
            kx, ky = rng.integers(-f, f + 1), rng.integers(-f, f + 1)
            fib += amp * np.sin(2 * np.pi * (kx * xx + ky * yy) / res + rng.uniform(0, 2 * np.pi))
    h = h + fib * 0.25
    h = (h - h.min()) / (h.max() - h.min())
    Image.fromarray(height_to_normal(h, 3.0), 'RGB').save(os.path.join(UT, 'T_Detail_Fabric_Normal.png'))
    alb = 128 + (h - 0.5) * 26
    Image.fromarray(alb.clip(0, 255).astype(np.uint8), 'L').convert('RGB').save(
        os.path.join(UT, 'T_Detail_Fabric_Albedo.png'))


for a in ATLASES:
    unity_textures(a)
fabric_textures()
tex = json.load(open(os.path.join(TEX, 'texel.json')))
rows = []
for a in ATLASES:
    mpu = tex[a]['metresPerUV']
    rows.append(dict(atlas='Kit' + a, material='M_Kit' + a, metresPerUV=mpu, pxPerMetre=tex[a]['pxPerMetre'],
                     areaM2=tex[a]['areaM2'], detail='Fabric', detailTiling=round(mpu / FABRIC_TILE, 2),
                     detailNormalScale=FABRIC_NORMAL_SCALE, detailMask=f'T_Kit{a}_DetailMask'))
json.dump(rows, open(os.path.join(DATA, 'kit_texel.json'), 'w'), indent=1)
print('texel', rows, flush=True)

# ------------------------------------------------------------------ final blend: one material per atlas
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'kit_src_v1.blend'))
O, MAT = bpy.data.objects, bpy.data.materials
COVERS = ['Kit_EngineCover', 'Kit_WindshieldCover', 'Kit_WingCover_L', 'Kit_WingCover_R']
KIT = [o for o in bpy.data.collections['Kit'].objects if o.type == 'MESH']


def load(path, noncolor):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im


def atlas_material(a):
    name = 'M_Kit' + a
    m = MAT.get(name) or MAT.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputMaterial')
    pr = N.new('ShaderNodeBsdfPrincipled')
    L.new(pr.outputs[0], out.inputs[0])
    bc = N.new('ShaderNodeTexImage')
    bc.image = load(os.path.join(UT, f'T_Kit{a}_BaseColor.png'), False)
    mk = N.new('ShaderNodeTexImage')
    mk.image = load(os.path.join(UT, f'T_Kit{a}_MaskMap.png'), True)
    nm = N.new('ShaderNodeTexImage')
    nm.image = load(os.path.join(UT, f'T_Kit{a}_Normal.png'), True)
    L.new(bc.outputs['Color'], pr.inputs['Base Color'])
    sep = N.new('ShaderNodeSeparateColor')
    L.new(mk.outputs['Color'], sep.inputs[0])
    L.new(sep.outputs[0], pr.inputs['Metallic'])
    inv = N.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    L.new(mk.outputs['Alpha'], inv.inputs[1])
    L.new(inv.outputs[0], pr.inputs['Roughness'])
    nmap = N.new('ShaderNodeNormalMap')
    L.new(nm.outputs['Color'], nmap.inputs['Color'])
    L.new(nmap.outputs['Normal'], pr.inputs['Normal'])
    return m


MA = {a: atlas_material(a) for a in ATLASES}
for o in KIT:
    me = o.data
    me.materials.clear()
    me.materials.append(MA['Covers' if o.name in COVERS else 'Props'])
    for p in me.polygons:
        p.material_index = 0
    for lay in [l for l in me.uv_layers if l.name != 'UVMap']:
        me.uv_layers.remove(lay)
    me.uv_layers['UVMap'].active = True
    me.uv_layers['UVMap'].active_render = True
for m in [m for m in MAT if m.name.startswith(('kit_', 'kitC_'))]:
    m.use_fake_user = False
bpy.ops.outliner.orphans_purge(do_recursive=True) if bpy.context.area else None
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'kit_final_v1.blend'))
print('saved kit_final_v1.blend', flush=True)
