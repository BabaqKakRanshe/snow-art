"""One render per item of items.blend (Forest Update 6): python3 -I item_renders.py -- <items.blend> <out_dir> [W H]
Workbench, textures point-filtered (PSX), studio light + cavity, 3/4 view from the front left, framed on each item."""
import bpy, sys, os
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a[0]))
out = os.path.abspath(a[1])
W, H = (int(a[2]), int(a[3])) if len(a) > 3 else (960, 720)
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.render.image_settings.file_format = 'PNG'
sc.render.film_transparent = False
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'TEXTURE'
sh.show_cavity = True
sh.cavity_type = 'BOTH'
sh.show_backface_culling = False
sh.background_type = 'VIEWPORT'
sh.background_color = (0.16, 0.16, 0.17)
sc.display.render_aa = '16'
for m in bpy.data.materials:
    if m.use_nodes:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE':
                nd.interpolation = 'Closest'
cam = bpy.data.objects.new('qcam', bpy.data.cameras.new('qcam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 50
items = sorted((o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('Item_') and o.parent is None),
               key=lambda o: o.name)
# children of an item (if any) belong to it
def tree(o):
    yield o
    for c in o.children:
        yield from tree(c)
members = {o.name: set(x.name for x in tree(o)) for o in items}
for o in bpy.data.objects:
    if o.type in ('MESH', 'CURVE') and not any(o.name in s for s in members.values()):
        o.hide_render = True
done = 0
for o in items:
    for p in items:
        for n in members[p.name]:
            bpy.data.objects[n].hide_render = p != o
    vs = [x.matrix_world @ v.co for n in members[o.name] for x in [bpy.data.objects[n]] if x.type == 'MESH' for v in x.data.vertices]
    lo = Vector([min(v[i] for v in vs) for i in range(3)]); hi = Vector([max(v[i] for v in vs) for i in range(3)])
    c = (lo + hi) / 2
    r = max((hi - lo).length / 2, 0.02)
    d = Vector((-0.55, -0.85, 0.55)).normalized()
    e = c + d * r * 3.9
    cam.location = e
    cam.rotation_euler = (c - e).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_start = r * 0.05
    cam.data.clip_end = r * 20
    sc.render.filepath = os.path.join(out, o.name + '.png')
    bpy.ops.render.render(write_still=True)
    done += 1
print('rendered', done, 'items ->', out)
