"""Workbench previews of the kit row: python3 -I kit_preview.py -- <fences.blend> <out_dir> [TEXTURE|MATERIAL]"""
import bpy, sys, os, math, json
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
out = a[1]; os.makedirs(out, exist_ok=True)
ctype = a[2] if len(a) > 2 else 'TEXTURE'
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'; sh.color_type = ctype; sh.show_cavity = False; sh.show_shadows = True; sh.shadow_intensity = 0.45
sh.background_type = 'VIEWPORT'; sh.background_color = (0.20, 0.22, 0.18); sh.show_backface_culling = True
sc.render.resolution_x, sc.render.resolution_y = 1200, 700
sc.display.light_direction = (0.45, -0.35, 0.82)
for m in bpy.data.materials:
    if m.use_nodes and m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE': nd.interpolation = 'Closest'
# ground
me = bpy.data.meshes.new('G'); me.from_pydata([(-5, -30, 0), (150, -30, 0), (150, 30, 0), (-5, 30, 0)], [], [(0, 1, 2, 3)])
g = bpy.data.objects.new('G', me); sc.collection.objects.link(g)
gm = bpy.data.materials.new('G'); gm.diffuse_color = (0.20, 0.22, 0.18, 1); me.materials.append(gm)
def box_of(names):
    vs = []
    for n in names:
        o = bpy.data.objects[n]
        vs += [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector([min(v[i] for v in vs) for i in range(3)]); hi = Vector([max(v[i] for v in vs) for i in range(3)])
    return lo, hi
def shot(name, names, d=(-0.35, -1.0, 0.45), lens=35, scale=1.0):
    lo, hi = box_of(names)
    c = (lo + hi) / 2; r = (hi - lo).length / 2
    cd = bpy.data.cameras.new(name); cam = bpy.data.objects.new(name, cd); sc.collection.objects.link(cam)
    dv = Vector(d).normalized()
    cd.lens = lens
    cam.location = c + dv * r * 2.0 * scale
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cd.clip_start = 0.05; cd.clip_end = 500
    sc.camera = cam; sc.render.filepath = os.path.join(out, name + '.png')
    bpy.ops.render.render(write_still=True)
G = {'po2': ['ConcreteFence', 'ConcreteFence_b', 'ConcreteFence_Broken', 'ConcreteFence_Sign'],
     'po2b': ['ConcreteFence_Plain', 'ConcreteFence_Socket', 'ConcreteFence_Wicket'],
     'chain': ['ChainFence', 'ChainFence_Torn', 'WireCoil'],
     'blocks': ['RoadBlock_FBS', 'RoadBlock_Jersey', 'RoadBlock_Jersey_Striped', 'RoadBlock_Cube', 'TankTooth', 'TankTooth_b'],
     'props': ['Hedgehog', 'WireBarricade', 'Abatis', 'Abatis_b'],
     'signs': ['Sign_Halt', 'Sign_NoEntry']}
for k, v in G.items():
    shot(k, v, scale=0.75 if k in ('po2', 'chain', 'props') else 0.9)
shot('po2_back', G['po2'], d=(0.35, 1.0, 0.45), scale=0.75)
print('done')
