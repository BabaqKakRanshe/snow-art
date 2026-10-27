"""workbench check views of a trash blend: python3 -I trash_quick.py <blend> <out_dir> [views]  (piles, clumps, <Kind>)"""
import sys, os, math
sys.path.insert(0, '/home/claude/uaz')
import bpy
from mathutils import Vector
blend, outd = sys.argv[1], sys.argv[2]
want = sys.argv[3].split(',') if len(sys.argv) > 3 else None
os.makedirs(outd, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'MATERIAL' if 'draft' in blend else 'TEXTURE'
sc.render.resolution_x, sc.render.resolution_y = 1400, 700
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
O = bpy.data.objects
KINDS = ['Paper', 'Plastic', 'Metal', 'Wood', 'Glass', 'Mixed']
groups = {'piles': [f'TrashPile_{k}' for k in KINDS], 'clumps': [f'TrashClump_{k}' for k in KINDS]}
for k in KINDS:
    groups[k] = [f'TrashPile_{k}', f'TrashClump_{k}']
for nm, names in groups.items():
    if want and nm not in want: continue
    for o in O:
        if o.type == 'MESH': o.hide_render = o.name not in names
    pts = [O[n].matrix_world @ Vector(c) for n in names for c in O[n].bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    c = (lo + hi) / 2
    r = (hi - lo).length * 0.5
    e = c + Vector((-1.0, -0.2, 0.75)).normalized() * r * 2.2
    cam.location = e
    cam.rotation_euler = (c - e).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 40
    cam.data.clip_start = 0.01
    sc.render.filepath = os.path.join(outd, nm + '.png')
    bpy.ops.render.render(write_still=True)
    print('view', nm, flush=True)
