import bpy, sys, os, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
out = a[1]
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'; sh.show_cavity = False; sh.show_shadows = False
sh.background_type = 'VIEWPORT'; sh.background_color = (0.30, 0.34, 0.30); sh.show_backface_culling = True
sc.render.resolution_x, sc.render.resolution_y = 900, 700
for m in bpy.data.materials:
    if m.use_nodes and m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'TEX_IMAGE': nd.interpolation = 'Closest'
for name, d, dist, lens, tgt in [(n, (-0.25, -1.0, 0.25), float(dd), 35, None) for n, dd in [(x.split(':')[0], x.split(':')[1]) for x in a[2:]]]:
    o = bpy.data.objects[name]
    vs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector([min(v[i] for v in vs) for i in range(3)]); hi = Vector([max(v[i] for v in vs) for i in range(3)])
    c = (lo + hi) / 2
    cd = bpy.data.cameras.new('c_' + name); cam = bpy.data.objects.new('c_' + name, cd); sc.collection.objects.link(cam)
    cam.location = c + Vector(d).normalized() * dist
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cd.lens = lens; cd.clip_start = 0.05
    sc.camera = cam; sc.render.filepath = os.path.join(out, 'cu_' + name + '.png')
    bpy.ops.render.render(write_still=True)
