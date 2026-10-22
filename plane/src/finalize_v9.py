"""v9 finalize: Unity textures + final materials (out/plane_v9_uv.blend -> out/plane_v9_final_v9.blend).
 - export/unity_v9/Assets/UtilityPlane/Textures:
     T_Airframe_*, T_Wing_*, T_Details_*: PS1 / PSX lo-fi (psx_tex.py variant b: 512 px, 64 colours, ordered dither,
       AO and panel lines in the colour; MaskMap R metal 0/1, G 1, B 1, A smoothness in 4 steps); no normal maps
     T_Fittings_* (2048, interior style, paint_v9.py), T_Survival_* (PSX 256), T_FogPrint_Hand / _Finger (brushes)
     everything else (cabin atlases, gauges, displays, webbing, prop discs, grain / leather detail maps) as in v8;
     T_Detail_Paint_* dropped (it only served the exterior), T_GlassFog_Mask is written by export_unity_v9.py
 - Data/atlas_texel.json: v8 entries with psx flags, + Fittings, Survival
 - Blender materials: M_Airframe / M_Wing / M_Details on the PSX maps (Closest), M_Fittings, M_Survival; every image
   re-pointed to the v9 texture folder."""
import bpy, os, sys, json, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
V8T = os.path.join(HERE, 'export', 'unity_v8', 'Assets', 'UtilityPlane', 'Textures')
V8D = os.path.join(HERE, 'export', 'unity_v8', 'Assets', 'UtilityPlane', 'Data')
OUT = os.path.join(HERE, 'export', 'unity_v9', 'Assets', 'UtilityPlane')
UT, DATA = os.path.join(OUT, 'Textures'), os.path.join(OUT, 'Data')
PSX = os.path.join(HERE, 'tex', 'psx_b')
T9 = os.path.join(HERE, 'tex', 'v9')
for d in (UT, DATA):
    os.makedirs(d, exist_ok=True)
for f in os.listdir(UT):                                        # start clean (no stale v8 normals in the package)
    os.remove(os.path.join(UT, f))
PSX_ATL = ('Airframe', 'Wing', 'Details')
for f in sorted(os.listdir(V8T)):
    if f.startswith(tuple(f'T_{a}_' for a in PSX_ATL)) or f.startswith('T_Detail_Paint_') or f.startswith('T_GlassFog'):
        continue
    shutil.copy2(os.path.join(V8T, f), os.path.join(UT, f))
for a in PSX_ATL:
    for k in ('BaseColor', 'MaskMap'):
        shutil.copy2(os.path.join(PSX, f'T_{a}_{k}.png'), os.path.join(UT, f'T_{a}_{k}.png'))
for f in ('T_Fittings_BaseColor', 'T_Fittings_MaskMap', 'T_Fittings_Normal', 'T_Survival_BaseColor', 'T_Survival_MaskMap',
          'T_FogPrint_Hand', 'T_FogPrint_Finger'):
    shutil.copy2(os.path.join(T9, 'out', f + '.png'), os.path.join(UT, f + '.png'))
print('textures', len(os.listdir(UT)), sorted(os.listdir(UT)), flush=True)

# ------------------------------------------------------------------ atlas_texel.json
tex8 = json.load(open(os.path.join(V8D, 'atlas_texel.json')))
psx_info = json.load(open(os.path.join(PSX, 'psx.json')))
A9 = json.load(open(os.path.join(T9, 'atlas9.json')))
out = []
for e in tex8:
    e = dict(e)
    if e['atlas'] in PSX_ATL:
        e.update(psx=True, pxPerMetre=round(psx_info['size'] / e['metresPerUV'], 1), detail='', detailTiling=0.0,
                 detailNormalScale=0.0)
    else:
        e['psx'] = False
    out.append(e)
f9 = A9['Fittings']
out.append(dict(atlas='Fittings', material='M_Fittings', metresPerUV=round(f9['metresPerUV'], 4),
                pxPerMetre=round(f9['pxPerMetre'], 1), areaM2=round(f9['areaM2'], 2), detail='', detailTiling=0.0,
                detailNormalScale=0.0, psx=False,
                note='the four seats share their islands (identical copies, the right ones mirrored)'))
s9 = A9['Survival']
out.append(dict(atlas='Survival', material='M_Survival', metresPerUV=round(s9['metresPerUV'], 4),
                pxPerMetre=round(s9['pxPerMetre'] * 256 / 1024, 1), areaM2=round(s9['areaM2'], 2), detail='',
                detailTiling=0.0, detailNormalScale=0.0, psx=True))
json.dump(out, open(os.path.join(DATA, 'atlas_texel.json'), 'w'), indent=1)

# ------------------------------------------------------------------ Blender materials
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v9_uv.blend'))
MAT = bpy.data.materials


def load(path, noncolor):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im


def pbr(name, bc, ms, nrm, closest=False):
    m = MAT.get(name) or MAT.new(name)
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    N.clear()
    out_n = N.new('ShaderNodeOutputMaterial')
    pr = N.new('ShaderNodeBsdfPrincipled')
    L.new(pr.outputs[0], out_n.inputs[0])
    t = N.new('ShaderNodeTexImage')
    t.image = load(bc, False)
    t.interpolation = 'Closest' if closest else 'Linear'
    L.new(t.outputs['Color'], pr.inputs['Base Color'])
    tm = N.new('ShaderNodeTexImage')
    tm.image = load(ms, True)
    tm.interpolation = 'Closest' if closest else 'Linear'
    sp = N.new('ShaderNodeSeparateColor')
    L.new(tm.outputs['Color'], sp.inputs[0])
    L.new(sp.outputs[0], pr.inputs['Metallic'])
    inv = N.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    L.new(tm.outputs['Alpha'], inv.inputs[1])
    L.new(inv.outputs[0], pr.inputs['Roughness'])
    if nrm:
        tn = N.new('ShaderNodeTexImage')
        tn.image = load(nrm, True)
        nm = N.new('ShaderNodeNormalMap')
        L.new(tn.outputs['Color'], nm.inputs['Color'])
        L.new(nm.outputs[0], pr.inputs['Normal'])
    return m


for a in PSX_ATL:
    pbr('M_' + a, os.path.join(UT, f'T_{a}_BaseColor.png'), os.path.join(UT, f'T_{a}_MaskMap.png'), None, closest=True)
pbr('M_Fittings', os.path.join(UT, 'T_Fittings_BaseColor.png'), os.path.join(UT, 'T_Fittings_MaskMap.png'),
    os.path.join(UT, 'T_Fittings_Normal.png'))
pbr('M_Survival', os.path.join(UT, 'T_Survival_BaseColor.png'), os.path.join(UT, 'T_Survival_MaskMap.png'), None,
    closest=True)
# every remaining image -> the v9 texture folder (same file names)
missing = []
for im in bpy.data.images:
    if im.source != 'FILE' or not im.filepath:
        continue
    fn = os.path.basename(bpy.path.abspath(im.filepath))
    p = os.path.join(UT, fn)
    if os.path.exists(p):
        im.filepath = p
    elif im.users:
        missing.append(fn)
for im in [im for im in bpy.data.images if im.users == 0]:
    bpy.data.images.remove(im)
print('images not in the v9 folder (still used):', missing, flush=True)
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'out', 'plane_v9_final_v9.blend'))
print('saved plane_v9_final_v9.blend', flush=True)
