"""workbench check views of a rocks blend: python3 -I rocks_quick.py <blend> <out_dir> [views]  (stones, boulders, cliffs, ...)"""
import sys, os, math, json
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
sh.show_cavity = False
sc.render.resolution_x, sc.render.resolution_y = 1400, 700
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
O = bpy.data.objects
def bbox(names):
    pts = [O[n].matrix_world @ Vector(c) for n in names for c in O[n].bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi
groups = {'stones': [o.name for o in O if o.name.startswith('ForestStone')],
          'boulders': [o.name for o in O if o.name.startswith('ForestBoulder')],
          'cliffs': [o.name for o in O if o.name.startswith('ForestCliff')]}
for o in O:
    if o.type == 'MESH' and not o.name.startswith('COL'):
        groups[o.name] = [o.name]
views = {}
for g, names in groups.items():
    if not names: continue
    lo, hi = bbox(names)
    c = (lo + hi) / 2
    span = max(hi.x - lo.x, (hi.z - lo.z) * 2.0, 0.6)
    views[g] = (c + Vector((span * 0.30, -span * 0.95, span * 0.38)), c, 40)
    views[g + '_back'] = (c + Vector((-span * 0.35, span * 0.95, span * 0.32)), c, 40)
SHOW = {}
for g, names in groups.items():
    SHOW[g] = SHOW[g + '_back'] = set(names)
for nm, (e, t, lens) in views.items():
    if want and nm not in want: continue
    for o in O:
        if o.type == 'MESH':
            o.hide_render = o.name not in SHOW[nm]
    cam.location = e
    cam.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.02
    sc.render.filepath = os.path.join(outd, nm + '.png')
    bpy.ops.render.render(write_still=True)
    print('view', nm, flush=True)
