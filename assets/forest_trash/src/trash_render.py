"""Cycles previews of out/trash.blend: each kind - the pile on the forest floor and its clump next to it.
python3 -I trash_render.py <kinds|all> [spp] -> rend/trash/<kind>.png"""
import sys, os, math
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector, Matrix
import psxlib as P

HERE = P.HERE
OUT = os.path.join(HERE, 'rend', 'trash')
os.makedirs(OUT, exist_ok=True)
KINDS = ['Paper', 'Plastic', 'Metal', 'Wood', 'Glass', 'Mixed']
want = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] != 'all' else None
spp = int(sys.argv[2]) if len(sys.argv) > 2 else 24
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'out', 'trash.blend'))
sc = bpy.context.scene
for m in bpy.data.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
O = bpy.data.objects
gme = bpy.data.meshes.new('Ground')
gme.from_pydata([(-40, -40, -0.002), (40, -40, -0.002), (40, 40, -0.002), (-40, 40, -0.002)], [], [(0, 1, 2, 3)])
gob = bpy.data.objects.new('Ground', gme)
gm = bpy.data.materials.new('M_ground')
gm.use_nodes = True
pb = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
pb.inputs['Base Color'].default_value = (0.050, 0.044, 0.032, 1)
pb.inputs['Roughness'].default_value = 0.95
gme.materials.append(gm)
sc.collection.objects.link(gob)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
P.world((0.55, 0.61, 0.70), 0.9)
P.sun(3.0, (48, 0, 30))
P.setup_cycles((1000, 700), spp)
sc.cycles.max_bounces = 4
for i, k in enumerate(KINDS):
    if want and k not in want:
        continue
    pile, clump = O[f'TrashPile_{k}'], O[f'TrashClump_{k}']
    for o in O:
        if o.type == 'MESH' and o.name.startswith('Trash'):
            o.hide_render = o not in (pile, clump)
    base = pile.matrix_world.translation.copy()
    zc = clump.location.z
    clump.location = base + Vector((1.0, -0.55, zc))
    clump.rotation_euler = (0, 0, math.radians(-25))
    bpy.context.view_layer.update()
    c = base + Vector((0.45, -0.25, 0.12))
    e = c + Vector((-0.55, -1.0, 0.85)).normalized() * 2.3
    cam.location = e
    cam.rotation_euler = (c - e).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 38
    cam.data.clip_start = 0.02
    P.render(os.path.join(OUT, k.lower() + '.png'))
    print('rendered', k, flush=True)
