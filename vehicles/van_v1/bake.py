"""Livery bake like the plane: procedural paint (red, white band, mottling, faded roof, road grime, dirt runs,
AO and edge wear) baked to a UV atlas, then the PSX step (512 px, 64 colours, Bayer 4x4) and point filtering."""
import os, math
import numpy as np
import bpy
from PIL import Image
import vb as B

BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0


def separate_by_material(ob):
    B.select_only(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='MATERIAL')
    bpy.ops.object.mode_set(mode='OBJECT')
    parts = [o for o in bpy.context.selected_objects]
    out = {}
    for o in parts:
        mats = [s.material.name for s in o.material_slots if s.material]
        used = set(p.material_index for p in o.data.polygons)
        names = [o.material_slots[i].material.name for i in used if o.material_slots[i].material]
        out[names[0] if names else o.name] = o
    return out


def unwrap(ob, margin=0.004):
    B.select_only(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(58), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def paint_material(name, img):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputMaterial')
    em = N.new('ShaderNodeEmission')
    L.new(em.outputs[0], out.inputs[0])
    tc = N.new('ShaderNodeTexCoord')
    sx = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sx.inputs[0])

    def math_(op, a=None, b=None, va=None, vb=None):
        n = N.new('ShaderNodeMath'); n.operation = op
        if a is not None: L.new(a, n.inputs[0])
        if va is not None: n.inputs[0].default_value = va
        if b is not None: L.new(b, n.inputs[1])
        if vb is not None: n.inputs[1].default_value = vb
        return n.outputs[0]

    def mix(fac, c1, c2, facv=None):
        n = N.new('ShaderNodeMix'); n.data_type = 'RGBA'
        if fac is not None: L.new(fac, n.inputs['Factor'])
        else: n.inputs['Factor'].default_value = facv
        if isinstance(c1, tuple): n.inputs[6].default_value = (*c1, 1)
        else: L.new(c1, n.inputs[6])
        if isinstance(c2, tuple): n.inputs[7].default_value = (*c2, 1)
        else: L.new(c2, n.inputs[7])
        return n.outputs[2]

    def noise(scale, detail=3, stretch=(1, 1, 1)):
        mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = stretch
        L.new(tc.outputs['Object'], mp.inputs['Vector'])
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale
        nz.inputs['Detail'].default_value = detail
        L.new(mp.outputs['Vector'], nz.inputs['Vector'])
        return nz.outputs['Fac']

    z = sx.outputs['Z']
    # band
    band = math_('MULTIPLY', math_('GREATER_THAN', z, vb=1.56), math_('LESS_THAN', z, vb=1.72))
    c = mix(band, (0.30, 0.020, 0.013), (0.60, 0.60, 0.56))
    # mottling
    mot = math_('ADD', math_('MULTIPLY', noise(1.6, 4), vb=0.22), vb=0.89)
    mm = N.new('ShaderNodeMix'); mm.data_type = 'RGBA'; mm.blend_type = 'MULTIPLY'; mm.inputs['Factor'].default_value = 1
    L.new(c, mm.inputs[6]); cm = N.new('ShaderNodeCombineColor')
    L.new(mot, cm.inputs[0]); L.new(mot, cm.inputs[1]); L.new(mot, cm.inputs[2]); L.new(cm.outputs[0], mm.inputs[7])
    c = mm.outputs[2]
    # sun-faded roof
    fade = math_('MULTIPLY', math_('MAXIMUM', math_('SUBTRACT', z, vb=2.45), vb=0.0), vb=1.0)
    c = mix(math_('MINIMUM', fade, vb=0.35), c, (0.40, 0.20, 0.17))
    # dirt runs below the windows (noise stretched along z)
    runs = math_('GREATER_THAN', noise(9.0, 2, (6.0, 6.0, 0.35)), vb=0.62)
    below = math_('LESS_THAN', z, vb=1.86)
    c = mix(math_('MULTIPLY', math_('MULTIPLY', runs, below), vb=0.35), c, (0.06, 0.05, 0.04))
    # road grime low on the body
    low = math_('SUBTRACT', math_('MULTIPLY', z, vb=-1.0), vb=-1.40)           # 1.40 - z
    gr = math_('MINIMUM', math_('MAXIMUM', math_('DIVIDE', low, vb=0.48), vb=0.0), vb=1.0)
    grn = math_('MULTIPLY', gr, math_('ADD', math_('MULTIPLY', noise(5.0, 3), vb=0.5), vb=0.55))
    c = mix(math_('MINIMUM', grn, vb=0.85), c, (0.07, 0.06, 0.05))
    # rust spots near the bottom edge
    rust = math_('MULTIPLY', math_('GREATER_THAN', noise(14.0, 2), vb=0.70), math_('LESS_THAN', z, vb=1.12))
    c = mix(math_('MULTIPLY', rust, vb=0.8), c, (0.16, 0.06, 0.02))
    # edge wear (convex edges lighter)
    gm = N.new('ShaderNodeNewGeometry')
    ew = N.new('ShaderNodeMapRange'); ew.inputs['From Min'].default_value = 0.53; ew.inputs['From Max'].default_value = 0.62
    L.new(gm.outputs['Pointiness'], ew.inputs['Value'])
    c = mix(math_('MULTIPLY', ew.outputs[0], vb=0.45), c, (0.36, 0.30, 0.27))
    # AO into the colour, as on the plane: x (0.25 + 0.75 AO)
    ao = N.new('ShaderNodeAmbientOcclusion'); ao.samples = 16; ao.inputs['Distance'].default_value = 0.25
    aof = math_('ADD', math_('MULTIPLY', ao.outputs['AO'], vb=0.75), vb=0.25)
    ma = N.new('ShaderNodeMix'); ma.data_type = 'RGBA'; ma.blend_type = 'MULTIPLY'; ma.inputs['Factor'].default_value = 1
    L.new(c, ma.inputs[6]); cm2 = N.new('ShaderNodeCombineColor')
    L.new(aof, cm2.inputs[0]); L.new(aof, cm2.inputs[1]); L.new(aof, cm2.inputs[2]); L.new(cm2.outputs[0], ma.inputs[7])
    L.new(ma.outputs[2], em.inputs['Color'])
    ti = N.new('ShaderNodeTexImage'); ti.image = img
    N.active = ti
    ti.select = True
    return m


def psx_quantize(src, dst, size=512, ncol=64, amp=1 / 24):
    im = Image.open(src).convert('RGB')
    if im.size[0] != size:
        im = im.resize((size, size), Image.BOX)
    a = np.asarray(im, np.float32) / 255.0
    H, W, _ = a.shape
    x = a.reshape(-1, 3)
    rng = np.random.default_rng(0)
    smp = x[rng.choice(len(x), min(len(x), 20000), replace=False)]
    c = smp[rng.choice(len(smp), ncol, replace=False)].copy()
    for _ in range(16):
        lab = ((smp[:, None, :] - c[None]) ** 2).sum(-1).argmin(1)
        for j in range(ncol):
            msk = lab == j
            if msk.any():
                c[j] = smp[msk].mean(0)
    th = np.tile(BAYER4, (H // 4 + 1, W // 4 + 1))[:H, :W, None]
    d = np.clip(a + (th - 0.5) * amp * 2, 0, 1).reshape(-1, 3)
    out = np.empty_like(d)
    for i in range(0, len(d), 65536):
        out[i:i + 65536] = c[((d[i:i + 65536, None, :] - c[None]) ** 2).sum(-1).argmin(1)]
    Image.fromarray((out.reshape(H, W, 3) * 255 + 0.5).astype(np.uint8)).save(dst)


def bake_livery(ob, name, size=1024, spp=16, final=512):
    """bake the procedural livery of a paint-only object into a PSX texture; returns the new material"""
    unwrap(ob)
    img = bpy.data.images.new(name + '_bake', size, size, alpha=False)
    m = paint_material(name + '_bakemat', img)
    ob.data.materials.clear()
    ob.data.materials.append(m)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = spp
    sc.cycles.bake_type = 'EMIT'
    sc.render.bake.margin = 6
    B.select_only(ob)
    bpy.ops.object.bake(type='EMIT')
    raw = os.path.join(B.HERE, 'tex', f'T_{name}_raw.png')
    img.filepath_raw = raw
    img.file_format = 'PNG'
    img.save()
    dst = os.path.join(B.HERE, 'tex', f'T_{name}_BaseColor.png')
    psx_quantize(raw, dst, final)
    fm = B.tex_uv('M_' + name, dst, 0.5)
    ob.data.materials.clear()
    ob.data.materials.append(fm)
    return fm
