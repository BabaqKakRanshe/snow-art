"""Workbench render of B_Skull from an FBX (front 3/4 and top) to check geometry. -- <fbx> <out_prefix>"""
import bpy, sys, math, mathutils
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=a[0])
ob = bpy.data.objects['B_Skull']
for o in list(bpy.data.objects):
    if o is not ob: bpy.data.objects.remove(o, do_unlink=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'SINGLE'
sc.render.resolution_x, sc.render.resolution_y = 600, 450
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_end = 2000
ws = [ob.matrix_world @ v.co for v in ob.data.vertices]
lo = mathutils.Vector([min(w[i] for w in ws) for i in range(3)]); hi = mathutils.Vector([max(w[i] for w in ws) for i in range(3)])
c = (lo + hi) / 2; R = (hi - lo).length * 1.1
print('bbox', tuple(round(x, 1) for x in lo), tuple(round(x, 1) for x in hi))
for name, d in (('a', mathutils.Vector((0.5, -1.0, 0.2))), ('b', mathutils.Vector((0.5, 1.0, 0.2))), ('c', mathutils.Vector((-1.0, 0.3, 0.3)))):
    cam.location = c + d.normalized() * R
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f'{a[1]}_{name}.png'
    bpy.ops.render.render(write_still=True)
print('tris', sum(len(p.vertices) - 2 for p in ob.data.polygons))
